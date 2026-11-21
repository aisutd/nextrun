"""Offline tracklet stitching: join a track that ends to one that starts shortly after when it is the same player.

The online tracker (BoT-SORT) loses a player behind others or in a crowd and gives them a new id when they
reappear (most SportsMOT id changes are this kind: gap ~0.5 s). Afterwards the whole clip is known, so every track
end is matched to every later track start in one assignment:

  feasible  0 < gap <= max_gap_s, start within reach of the end (court metres when both are on a calibrated court,
            else image distance in player heights: r0 + vmax * gap, from the end position moved on by its velocity),
            and torso colours alike (same team)
  cost      distance / reach + colour difference + gap / max_gap_s
  solve     Hungarian on ends x starts; each end gets at most one successor and each start one predecessor, so the
            chains are time-ordered and never two places at once

Swaps (two ids trading players while crossing) are left to the tracker."""
from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..config import StitchConfig
from .appearance import body_distance
from ..schema import FrameState


@dataclass
class _Ends:
    t0: float
    t1: float
    court0: np.ndarray | None  # first / last court position (m)
    court1: np.ndarray | None
    vcourt: np.ndarray  # velocity at the end (m/s)
    img0: np.ndarray  # first / last feet in the image
    img1: np.ndarray
    vimg: np.ndarray
    h: float  # player height in the image (px)
    n: int


def _conflict(a: int, b: int, names: dict[int, str], teams: dict[int, str]) -> bool:
    """Two tracks the person told apart: both named and named differently, or put on different teams. A track with
    no name / team can join either."""
    if a in names and b in names and names[a] != names[b]:
        return True
    return bool(teams.get(a) and teams.get(b) and teams[a] != teams[b])


def _velocity(pts: list[tuple[float, np.ndarray]], vmax: float) -> np.ndarray:
    if len(pts) < 2 or pts[-1][0] - pts[0][0] <= 0:
        return np.zeros(2)
    v = (pts[-1][1] - pts[0][1]) / (pts[-1][0] - pts[0][0])
    s = float(np.hypot(*v))
    return v * (vmax / s) if s > vmax else v


def _ends(obs: list[tuple[float, tuple, tuple | None, float]], cfg: StitchConfig) -> _Ends:
    """obs: time-ordered (t, feet, court_xy, height) of one track."""
    t0, t1 = obs[0][0], obs[-1][0]
    tail = [o for o in obs if o[0] >= t1 - cfg.velocity_s]
    court = [(o[0], np.asarray(o[2], float)) for o in obs if o[2] is not None]
    ctail = [c for c in court if c[0] >= t1 - cfg.velocity_s]
    return _Ends(
        t0, t1,
        court[0][1] if court and court[0][0] - t0 <= cfg.velocity_s else None,
        court[-1][1] if court and t1 - court[-1][0] <= cfg.velocity_s else None,
        _velocity(ctail, cfg.vmax_mps),
        np.asarray(obs[0][1], float), np.asarray(obs[-1][1], float),
        _velocity([(o[0], np.asarray(o[1], float)) for o in tail], cfg.vmax_hps * float(np.median([o[3] for o in tail]))),
        float(np.median([o[3] for o in obs])), len(obs),
    )


def stitch_tracks(frames: list[FrameState], track_emb: dict[int, np.ndarray], cfg: StitchConfig,
                  names: dict[int, str] | None = None, teams: dict[int, str] | None = None,
                  reid: dict[int, np.ndarray] | None = None) -> dict[int, int]:
    """Re-label joined tracks in `frames` (in place; merged colour embeddings in `track_emb`) -> {old id: new id}.
    names / teams: the person's tags (track id -> name they typed / team); two tracks named differently or put on
    different teams never end up in one chain.
    reid: OSNet fingerprints per track (identity.reid). When both tracks have one it decides instead of torso colour:
    a join between two different-looking people is refused (torso colour alone let ~1 in 4 short-gap joins go to the
    wrong player in tests on real games)."""
    names, teams, reid = names or {}, teams or {}, reid or {}
    obs: dict[int, list] = defaultdict(list)
    for f in frames:
        for p in f.players:
            if p.track_id is not None:
                obs[p.track_id].append((f.t, p.feet, p.court_xy, p.height))
    tids = sorted(obs)
    ends = {t: _ends(obs[t], cfg) for t in tids}
    by_start = sorted(tids, key=lambda t: ends[t].t0)
    starts = [ends[t].t0 for t in by_start]
    cost: dict[tuple[int, int], float] = {}
    for a in tids:
        A = ends[a]
        for b in by_start[bisect.bisect_right(starts, A.t1) : bisect.bisect_right(starts, A.t1 + cfg.max_gap_s)]:
            B = ends[b]
            gap = B.t0 - A.t1
            if _conflict(a, b, names, teams):
                continue
            lead = min(gap, cfg.velocity_s)  # don't extrapolate a run across the whole gap
            if A.court1 is not None and B.court0 is not None:
                d = float(np.hypot(*(B.court0 - (A.court1 + A.vcourt * lead))))
                reach = cfg.r0_m + cfg.vmax_mps * gap
            else:
                h = max(A.h, 1.0)
                d = float(np.hypot(*(B.img0 - (A.img1 + A.vimg * lead)))) / h
                reach = cfg.r0_h + cfg.vmax_hps * gap
            if d > reach:
                continue
            app = 0.0
            if a in reid and b in reid:
                d_id = 1.0 - float(reid[a] @ reid[b])
                if d_id > cfg.stitch_max_reid:
                    continue
                app = cfg.max_color_dist * d_id / cfg.stitch_max_reid
            elif a in track_emb and b in track_emb:
                app = 1.0 - float(track_emb[a] @ track_emb[b])
                if app > cfg.max_color_dist:
                    continue
            cost[a, b] = d / reach + cfg.w_color * app / cfg.max_color_dist + gap / cfg.max_gap_s
    rows = sorted({a for a, _ in cost})
    cols = sorted({b for _, b in cost})
    big = 1e6
    C = np.full((len(rows), len(cols)), big)
    ri, ci = {t: i for i, t in enumerate(rows)}, {t: j for j, t in enumerate(cols)}
    for (a, b), c in cost.items():
        C[ri[a], ci[b]] = c
    nxt = {}
    if cost:
        for i, j in zip(*linear_sum_assignment(C)):
            if C[i, j] < big:
                nxt[rows[i]] = cols[j]
    # A track with no colour sample (always overlapping someone) passes the colour test with anyone, so a chain could
    # walk green -> (unknown) -> pink. Check every link against the chain's last known colour and cut it there.
    heads = [t for t in tids if t not in set(nxt.values())]
    while heads:  # a cut makes the rest of the chain a new head, checked in turn
        t = heads.pop()
        ref, c = track_emb.get(t), t
        while c in nxt:
            n_ = nxt[c]
            e = track_emb.get(n_)
            if ref is not None and e is not None and 1.0 - float(ref @ e) > cfg.max_color_dist:
                del nxt[c]
                heads.append(n_)
                break
            if e is not None:
                ref = e
            c = n_
    has_prev = set(nxt.values())
    relabel = {}
    for t in tids:
        if t in has_prev:
            continue
        chain, c = [t], t
        while c in nxt:
            c = nxt[c]
            chain.append(c)
        for c in chain[1:]:
            relabel[c] = t
        embs = [(track_emb[c], ends[c].n) for c in chain if c in track_emb]
        if len(chain) > 1 and embs:
            m = sum(e * n for e, n in embs)
            track_emb[t] = m / max(np.linalg.norm(m), 1e-9)
    for c in relabel:
        track_emb.pop(c, None)
    for f in frames:
        for p in f.players:
            if p.track_id in relabel:
                p.track_id = relabel[p.track_id]
    return relabel


def cover_tracks(frames: list[FrameState], track_emb: dict[int, np.ndarray], cfg: StitchConfig,
                 names: dict[int, str] | None = None, teams: dict[int, str] | None = None,
                 body: dict[int, np.ndarray] | None = None, reid: dict[int, np.ndarray] | None = None) -> dict[int, int]:
    """Second, whole-clip pass after stitch_tracks: one id per real person.

    stitch_tracks only joins short, well-predicted gaps, so a player who leaves the frame, hides behind others for a
    while or is broken up by a camera pan comes back as a new "player". Here every track is a node and an edge a -> b
    means b starts after a ends (never on screen together, so possibly the same person). Picking edges is a minimum
    path cover: every chain is one person. A join needs evidence: the same person by re-identification (`reid`:
    OSNet fingerprints, close enough and clearly the best match on both sides, so look-alike teammates are left
    apart rather than guessed), else the same clothes (`body`: colour of upper and lower body), else a short gap the
    player could physically cover (off by default). Joins are scored (court reach, clothes, gap
    length) and taken cheapest first, loosening a cost limit step by step but never past the evidence rules, and
    stopping once there are no more people than were ever on screen at once. Two tracks seen at the same time are
    never joined, so nobody seen is lost: the result keeps at least as many people as were ever visible together.
    names / teams: the person's tags, as in stitch_tracks. Relabels `frames` in place and merges `track_emb`;
    returns {old id: new id}."""
    names, teams, body, reid = names or {}, teams or {}, body or {}, reid or {}
    obs: dict[int, list] = defaultdict(list)
    per_frame = []
    for f in frames:
        per_frame.append(len(f.players))
        for p in f.players:
            if p.track_id is not None:
                obs[p.track_id].append((f.t, p.feet, p.court_xy, p.height))
    tids = sorted(obs)
    if len(tids) < 2:
        return {}
    target = max(per_frame) if per_frame else len(tids)  # most people ever on screen at once
    if len(tids) <= target:
        return {}
    ends = {t: _ends(obs[t], cfg) for t in tids}
    edges: dict[tuple[int, int], float] = {}
    ident: dict[tuple[int, int], float] = {}  # re-id distance of each candidate join
    for a in tids:
        A = ends[a]
        for b in tids:
            B = ends[b]
            gap = B.t0 - A.t1
            if gap <= 0:  # overlapping (or simultaneous) tracks are two people
                continue
            if _conflict(a, b, names, teams):
                continue
            pos, reachable = 0.0, None
            if A.court1 is not None and B.court0 is not None:
                reach = cfg.r0_m + cfg.vmax_mps * gap
                d = float(np.hypot(*(B.court0 - A.court1)))
                if d > reach:  # cannot get there in time
                    continue
                pos, reachable = d / reach, True
            if a in reid and b in reid:  # re-identification decides when both pieces have clean crops
                d_id = 1.0 - float(reid[a] @ reid[b])
                if d_id > cfg.cover_max_reid:
                    continue
                clothes = cfg.cover_max_body * d_id / cfg.cover_max_reid
                ident[a, b] = d_id
            elif a in body and b in body:  # clothes decide: same outfit at any gap, a different one never
                clothes = body_distance(body[a], body[b])
                if clothes > cfg.cover_max_body:
                    continue
            elif gap <= cfg.cover_blind_gap_s and reachable:  # no clean look at one of them: only an obvious hand-off
                clothes = cfg.cover_max_body
            else:
                continue
            edges[a, b] = pos + cfg.cover_w_color * clothes / cfg.cover_max_body + min(gap, cfg.cover_gap_s) / cfg.cover_gap_s
    # look-alikes (teammates in the same kit): keep a re-id join only when it is clearly the best for both pieces
    if ident and cfg.cover_reid_margin > 0:
        out_of: dict[int, list[tuple[int, float]]] = defaultdict(list)
        into: dict[int, list[tuple[int, float]]] = defaultdict(list)
        for (a, b), d in ident.items():
            out_of[a].append((b, d))
            into[b].append((a, d))
        for (a, b), d in ident.items():
            rivals = [x for b2, x in out_of[a] if b2 != b] + [x for a2, x in into[b] if a2 != a]
            if any(x < d + cfg.cover_reid_margin for x in rivals):
                edges.pop((a, b), None)
    if not edges:
        return {}
    rows = sorted({a for a, _ in edges})
    cols = sorted({b for _, b in edges})
    ri, ci = {t: i for i, t in enumerate(rows)}, {t: j for j, t in enumerate(cols)}
    base = np.full((len(rows), len(cols)), np.inf)
    for (a, b), c in edges.items():
        base[ri[a], ci[b]] = c

    def solve(limit: float) -> dict[int, int]:
        """Cheapest set of joins each costing <= limit (an end may also stay unjoined at cost `limit`)."""
        n, m = len(rows), len(cols)
        C = np.full((n + m, m + n), 0.0)
        C[:n, :m] = np.where(base <= limit, base, 1e9)
        C[:n, m:] = np.where(np.eye(n) > 0, limit, 1e9)  # end i stays unjoined
        C[n:, :m] = np.where(np.eye(m) > 0, limit, 1e9)  # start j stays unjoined
        r, c = linear_sum_assignment(C)
        return {rows[i]: cols[j] for i, j in zip(r, c) if i < n and j < m and C[i, j] < 1e8}

    nxt: dict[int, int] = {}
    for limit in cfg.cover_limits:
        nxt = solve(limit)
        if len(tids) - len(nxt) <= target:
            break
    has_prev = set(nxt.values())
    relabel = {}
    for t in tids:
        if t in has_prev:
            continue
        chain, c = [t], t
        while c in nxt:
            c = nxt[c]
            chain.append(c)
        for c in chain[1:]:
            relabel[c] = t
        embs = [(track_emb[c], ends[c].n) for c in chain if c in track_emb]
        if len(chain) > 1 and embs:
            m_ = sum(e * n for e, n in embs)
            track_emb[t] = m_ / max(np.linalg.norm(m_), 1e-9)
    for c in relabel:
        track_emb.pop(c, None)
    for f in frames:
        for p in f.players:
            if p.track_id in relabel:
                p.track_id = relabel[p.track_id]
    return relabel
