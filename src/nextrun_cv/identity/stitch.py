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
                  names: dict[int, str] | None = None) -> dict[int, int]:
    """Re-label joined tracks in `frames` (in place; merged colour embeddings in `track_emb`) -> {old id: new id}.
    names: user tags (track id -> player); a tagged track is only joined onto a track with the same name, so two
    differently tagged tracks never end up in one chain."""
    names = names or {}
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
            if b in names and names.get(a) != names[b]:
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
            if a in track_emb and b in track_emb:
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
