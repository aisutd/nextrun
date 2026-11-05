"""Offline ball tracking and rim stabilisation over a whole clip.

The detector gives 0..n ball candidates per frame (false positives: heads, shoes, other balls).
A constant-velocity Kalman filter picks the candidate consistent with the trajectory, then short
gaps (occlusion by players / net) are filled by linear interpolation."""
from __future__ import annotations

import cv2
import numpy as np

from ..config import BallTrackConfig
from ..schema import BallObs, FrameState, RimObs


class _KF:
    """2D constant-velocity Kalman filter, state [x, y, vx, vy], dt = 1 frame."""

    def __init__(self, xy, q: float, r: float):
        self.x = np.array([xy[0], xy[1], 0.0, 0.0])
        self.P = np.diag([r * r, r * r, 400.0, 400.0])
        self.F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], float)
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], float)
        self.Q = np.eye(4) * q * q
        self.R = np.eye(2) * r * r

    def predict(self) -> np.ndarray:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:2]

    def update(self, z) -> None:
        y = np.asarray(z, float) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P


def _inside(xy, box, grow: float = 0.0) -> bool:
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    return x1 - grow * w <= xy[0] <= x2 + grow * w and y1 - grow * h <= xy[1] <= y2 + grow * h


def _play_region(frames: list[FrameState], hm: float):
    """Convex area where play can happen: all player boxes (+25 %, plus headroom for shots in the air) and the rims.
    A 'ball' outside it is a bystander's ball, a bag, a sign..."""
    pts = [c for f in frames for p in f.players for c in ((p.bbox[0], p.bbox[1]), (p.bbox[2], p.bbox[1]), (p.bbox[0], p.bbox[3]), (p.bbox[2], p.bbox[3]))]
    if len(pts) < 16:
        return None
    pts += [c for f in frames for r in f.rims if r.conf >= 0.4 for c in ((r.bbox[0], r.bbox[1]), (r.bbox[2], r.bbox[3]))]
    pts = np.asarray(pts, np.float32)
    grown = (pts - pts.mean(0)) * 1.25 + pts.mean(0)
    up = grown.copy()
    up[:, 1] -= 2.0 * hm
    return cv2.convexHull(np.vstack([grown, up]).astype(np.float32))


def _static_cells(frames: list[FrameState], cell: float) -> dict:
    """Where 'ball' detections show up, per grid cell: the positions seen there. A spare ball on the sideline, a logo
    or a pole top shows up again and again at the same spot."""
    cells: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for f in frames:
        for c in {(int(b.xy[0] // cell), int(b.xy[1] // cell), b.xy) for b in f.ball_candidates}:
            cells.setdefault(c[:2], []).append(c[2])
    return cells


def _is_static(xy, cells: dict, cell: float, n_frames: int) -> bool:
    """Seen in a good share of the frames around here AND those sightings hardly move (a game ball that passes
    through the neighbourhood moves on; a fixture does not)."""
    cx, cy = int(xy[0] // cell), int(xy[1] // cell)
    near = [p for i in (-1, 0, 1) for j in (-1, 0, 1) for p in cells.get((cx + i, cy + j), ())]
    if len(near) < max(8, 0.15 * n_frames):
        return False
    return float(np.ptp(np.asarray(near, float), axis=0).max()) < 0.5 * cell


def _radius_band(frames: list[FrameState]) -> tuple[float, float]:
    """Plausible ball radius in this clip: the median radius of the confident detections, 0.4x..2.5x (perspective
    makes the ball bigger near the camera, motion blur stretches it). Open-ended when there is too little to judge."""
    rs = [b.radius for f in frames for b in f.ball_candidates if b.conf >= 0.5]
    if len(rs) < 10:
        return 0.0, float("inf")
    med = float(np.median(rs))
    return 0.4 * med, 2.5 * med


def track_ball(frames: list[FrameState], cfg: BallTrackConfig) -> None:
    """Sets `frame.ball` on every frame (None where the ball is unknown). In place.

    Offline: every candidate of every frame is a node; the best single path through them wins (dynamic programming).
    A node earns its confidence; a jump costs more the bigger it is relative to the player height (so it works at any
    resolution); skipping frames costs a little; restarting after a loss costs more. A false 'ball' for a second would
    have to be both confident and coherent, and it still loses to the real path. Candidates outside the play area,
    or sitting still away from every player, are dropped before the search."""
    for f in frames:
        f.ball = None
    if not frames:
        return
    hs = [p.height for f in frames for p in f.players]
    hm = float(np.median(hs)) if hs else 100.0
    gate = cfg.max_jump_heights * hm
    region = _play_region(frames, hm)
    cell = max(8.0, 0.35 * hm)
    static = _static_cells(frames, cell)
    r_lo, r_hi = _radius_band(frames)
    cands: list[tuple[int, BallObs]] = []
    held_at: list[bool] = []
    for t, f in enumerate(frames):
        for b in f.ball_candidates:
            if not r_lo <= b.radius <= r_hi:  # a head / shoe / logo is a different size from the ball
                continue
            held = any(_inside(b.xy, p.bbox, 0.25) for p in f.players)
            if not held:
                if region is not None and cv2.pointPolygonTest(region, (float(b.xy[0]), float(b.xy[1])), False) < 0:
                    continue
                if _is_static(b.xy, static, cell, len(frames)):
                    continue
            cands.append((t, b))
            held_at.append(held)
    if not cands:
        return
    G = cfg.max_gap_frames + 1  # largest frame step linked by an edge
    R, R0, SKIP = 1.5, 0.8, 0.15
    by_t: dict[int, list[int]] = {}
    for i, (t, _) in enumerate(cands):
        by_t.setdefault(t, []).append(i)
    n = len(cands)
    dp, prev = [0.0] * n, [-1] * n
    best_before, best_cur, cur_t = (-1e9, -1), (-1e9, -1), -1
    for i, (t, b) in enumerate(cands):
        if t != cur_t:
            if best_cur[0] > best_before[0]:
                best_before = best_cur
            best_cur, cur_t = (-1e9, -1), t
        val, pv = -R0, -1  # start a new segment
        if best_before[1] >= 0 and best_before[0] - R > val:  # ...or restart after a loss
            val, pv = best_before[0] - R, best_before[1]
        for tt in range(max(0, t - G), t):
            for j in by_t.get(tt, ()):
                k = t - tt
                d = float(np.hypot(b.xy[0] - cands[j][1].xy[0], b.xy[1] - cands[j][1].xy[1]))
                if d > gate * k:
                    continue
                v = dp[j] - (2.0 * (d / (gate * k)) ** 2 + SKIP * (k - 1))
                if v > val:
                    val, pv = v, j
        dp[i], prev[i] = 2.0 * b.conf + val, pv
        if dp[i] > best_cur[0]:
            best_cur = (dp[i], i)
    i = int(np.argmax(dp))
    path = []
    while i >= 0:
        path.append(i)
        i = prev[i]
    path.reverse()
    # drop lone, weak nodes (a one-frame glitch that the search had to bridge)
    segs: list[list[int]] = []
    for i in path:
        if segs and cands[i][0] - cands[segs[-1][-1]][0] <= G and prev[i] == segs[-1][-1]:
            segs[-1].append(i)
        else:
            segs.append([i])
    for sg in segs:
        mc = float(np.mean([cands[i][1].conf for i in sg]))
        if (len(sg) == 1 and mc < 0.6) or (len(sg) == 2 and mc < 0.4):
            continue
        xy = np.array([cands[i][1].xy for i in sg])
        if len(sg) >= 3 and float(np.ptp(xy, axis=0).max()) < 0.25 * hm and not any(held_at[i] for i in sg):
            continue  # a 'ball' that sits still away from every player is a fixture (pole top, sign), not the game ball
        for i in sg:
            t, b = cands[i]
            frames[t].ball = BallObs(b.xy, b.radius, b.conf)
    interpolate_gaps(frames, cfg.max_gap_frames)


def interpolate_gaps(frames: list[FrameState], max_gap: int) -> None:
    known = [i for i, f in enumerate(frames) if f.ball is not None]
    for a, b in zip(known, known[1:]):
        gap = b - a - 1
        if gap <= 0 or gap > max_gap:
            continue
        pa, pb = np.array(frames[a].ball.xy), np.array(frames[b].ball.xy)
        ra, rb = frames[a].ball.radius, frames[b].ball.radius
        for k in range(1, gap + 1):
            w = k / (gap + 1)
            xy = (1 - w) * pa + w * pb
            frames[a + k].ball = BallObs((float(xy[0]), float(xy[1])), (1 - w) * ra + w * rb, 0.0, interpolated=True)


def smooth_ball_display(frames: list[FrameState], cfg: BallTrackConfig) -> list[tuple[tuple[float, float], float] | None]:
    """Per frame, the ball's position and radius for DRAWING: a Rauch-Tung-Striebel smoother over each unbroken run of
    sightings (constant-velocity model, interpolated guesses trusted less) and a steady radius. The detector's raw
    boxes jitter by a few pixels and its size flickers frame to frame, which makes a drawn ball shake. Events keep
    using the raw track (frame.ball), so smoothing can't blur a bounce or a rim crossing."""
    out: list[tuple[tuple[float, float], float] | None] = [None] * len(frames)
    i, n = 0, len(frames)
    while i < n:
        if frames[i].ball is None:
            i += 1
            continue
        j = i
        while j + 1 < n and frames[j + 1].ball is not None:
            j += 1
        run = [frames[k].ball for k in range(i, j + 1)]
        xs = _rts([b.xy for b in run], [b.interpolated for b in run])
        rs = np.array([b.radius for b in run], float)
        k = 5  # median over +-5 frames, then a short average: the size changes slowly, detections flicker
        med = np.array([np.median(rs[max(0, a - k) : a + k + 1]) for a in range(len(rs))])
        rad = np.convolve(np.pad(med, 2, mode="edge"), np.ones(5) / 5, mode="valid")
        for a, k_ in enumerate(range(i, j + 1)):
            out[k_] = ((float(xs[a][0]), float(xs[a][1])), float(rad[a]))
        i = j + 1
    return out


def _rts(pts, guessed, accel: float = 5.0, r: float = 4.0) -> np.ndarray:
    """Constant-velocity Rauch-Tung-Striebel smoother; `accel` (px/frame^2, white-noise acceleration) and `r` (px)
    were tuned on simulated arcs and dribbles: ~1/3 less jitter while bounce peaks move by only a few pixels."""
    n = len(pts)
    if n < 3:
        return np.asarray(pts, float)
    F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], float)
    G = np.array([[0.5, 0], [0, 0.5], [1, 0], [0, 1]])
    Q = G @ G.T * accel**2
    x = np.array([pts[0][0], pts[0][1], 0.0, 0.0])
    P = np.diag([r * r, r * r, 100.0, 100.0])
    xf, Pf, xp, Pp = [], [], [], []
    for a in range(n):
        if a:
            x, P = F @ x, F @ P @ F.T + Q
        xp.append(x.copy())
        Pp.append(P.copy())
        R = np.eye(2) * (r * (4.0 if guessed[a] else 1.0)) ** 2  # interpolated guesses count for less
        K = P @ H.T @ np.linalg.inv(H @ P @ H.T + R)
        x = x + K @ (np.asarray(pts[a], float) - H @ x)
        P = (np.eye(4) - K @ H) @ P
        xf.append(x.copy())
        Pf.append(P.copy())
    xs = [xf[-1]]
    for a in range(n - 2, -1, -1):
        C = Pf[a] @ F.T @ np.linalg.inv(Pp[a + 1])
        xs.append(xf[a] + C @ (xs[-1] - xp[a + 1]))
    return np.array([v[:2] for v in reversed(xs)])


def _warp_box(box, H: np.ndarray) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    p = cv2.perspectiveTransform(np.float32([[x1, y1], [x2, y1], [x1, y2], [x2, y2]]).reshape(-1, 1, 2), H).reshape(-1, 2)
    return float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()), float(p[:, 1].max())


def stabilize_rims_moving(frames: list[FrameState], segments: list[int], motion: list[np.ndarray],
                          size: tuple[int, int], min_support: float = 0.05) -> None:
    """Moving camera: the rims are still fixed in the world. Undo the camera motion (court.track.CameraMotion:
    per frame, the shot it belongs to and the homography from the shot's first frame), stabilize each shot's rims
    there like a fixed camera, and carry them back into every frame (dropping the ones out of view)."""
    w, h = size
    for sg in sorted(set(segments)):
        ks = [k for k, s in enumerate(segments) if s == sg]
        ref = [FrameState(frames[k].idx, frames[k].t,
                          rims=[RimObs(_warp_box(r.bbox, np.linalg.inv(motion[k])), r.conf) for r in frames[k].rims])
               for k in ks]
        stable = stabilize_rims(ref, min_support)
        for k in ks:
            rims = [RimObs(_warp_box(r.bbox, motion[k]), r.conf) for r in stable]
            frames[k].rims = [r for r in rims if 0 <= r.center[0] < w and 0 <= r.center[1] < h]


def stabilize_rims(frames: list[FrameState], min_support: float = 0.05) -> list[RimObs]:
    """Fixed camera => rims don't move. Cluster all rim detections, keep clusters seen in at least
    `min_support` of frames, and assign their median boxes to every frame (so rims stay known while
    the ball or a player occludes them). Returns the stable rims."""
    dets = [r for f in frames for r in f.rims]
    if not dets:
        return []
    clusters: list[list[RimObs]] = []
    for r in sorted(dets, key=lambda r: -r.conf):
        cx, cy = r.center
        for c in clusters:
            mx, my = np.median([x.center for x in c], axis=0)
            if np.hypot(cx - mx, cy - my) < 1.5 * np.median([x.width for x in c]):
                c.append(r)
                break
        else:
            clusters.append([r])
    stable = []
    for c in clusters:
        if len(c) >= max(3, min_support * len(frames)):
            box = np.median([x.bbox for x in c], axis=0)
            stable.append(RimObs(tuple(float(v) for v in box), float(np.mean([x.conf for x in c]))))
    for f in frames:
        f.rims = list(stable)
    return stable
