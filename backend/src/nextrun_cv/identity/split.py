"""Split tracks whose id jumped from one player to another (the tracker swaps ids when two players cross).

A track's torso colour over time should stay the same. When the samples before some point are one colour and the
samples after it are clearly another (and each side is consistent on its own), the track is cut there and the part
after gets a new id; each part is checked again, so a track that swapped twice is cut twice."""
from __future__ import annotations

import numpy as np

from ..schema import FrameState


def _median(x: np.ndarray) -> np.ndarray:
    m = np.median(x, axis=0)
    return m / max(np.linalg.norm(m), 1e-9)


def _best_cut(E: np.ndarray, min_side: int, split_dist: float, max_spread: float) -> int | None:
    """Index k so that E[:k] and E[k:] are two different, internally consistent colours; None if there is none."""
    best, best_d = None, split_dist
    for k in range(min_side, len(E) - min_side + 1):
        a, b = _median(E[:k]), _median(E[k:])
        d = 1.0 - float(a @ b)
        if d <= best_d:
            continue
        # each side has to agree with itself (a few odd samples from a blurred or half-hidden torso are fine)
        sa, sb = 1.0 - E[:k] @ a, 1.0 - E[k:] @ b
        if np.median(sa) > max_spread or np.median(sb) > max_spread:
            continue
        best, best_d = k, d
    return best


def split_swapped_tracks(frames: list[FrameState], samples: dict, track_emb: dict[int, np.ndarray],
                         min_side: int = 4, split_dist: float = 0.45, max_spread: float = 0.25) -> dict[int, int]:
    """Cut tracks at colour changes (in place: frames get new track ids, track_emb gets the parts' colours).
    samples: {track id: [(source frame idx, embedding), ...]} in time order. Returns {new id: original id}."""
    next_id = max([p.track_id for f in frames for p in f.players if p.track_id is not None] + [0]) + 1
    cuts: dict[int, list[tuple[int, int]]] = {}  # original id -> [(first source frame of a part, new id)]
    new_from: dict[int, int] = {}
    for tid, ss in samples.items():
        if len(ss) < 2 * min_side:
            continue
        ss = sorted(ss, key=lambda s: s[0])
        parts = [(np.array([s[0] for s in ss]), np.array([s[1] for s in ss], float))]
        done = []
        while parts:
            idx, E = parts.pop()
            k = _best_cut(E, min_side, split_dist, max_spread)
            if k is None:
                done.append((idx, E))
            else:
                parts += [(idx[:k], E[:k]), (idx[k:], E[k:])]
        if len(done) < 2:
            continue
        done.sort(key=lambda d: d[0][0])
        cuts[tid] = []
        for j, (idx, E) in enumerate(done):
            nid = tid if j == 0 else next_id
            if j:
                next_id += 1
                new_from[nid] = tid
                # the cut lies between the last sample of the previous part and the first of this one
                prev_last = done[j - 1][0][-1]
                cuts[tid].append(((int(prev_last) + int(idx[0])) // 2 + 1, nid))
            track_emb[nid] = _median(E)
    if not cuts:
        return {}
    for f in frames:
        for p in f.players:
            cs = cuts.get(p.track_id)
            if cs:
                for start, nid in cs:  # cuts are in time order: the last one at or before this frame wins
                    if f.idx >= start:
                        p.track_id = nid
    return new_from
