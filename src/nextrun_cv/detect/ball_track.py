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


def track_ball(frames: list[FrameState], cfg: BallTrackConfig) -> None:
    """Sets `frame.ball` on every frame (None where the ball is unknown). In place."""
    kf: _KF | None = None
    missed = 0
    for f in frames:
        f.ball = None
        cands = f.ball_candidates
        if kf is None:
            if cands:
                best = max(cands, key=lambda b: b.conf)
                kf = _KF(best.xy, cfg.process_noise, cfg.measurement_noise)
                f.ball = BallObs(best.xy, best.radius, best.conf)
                missed = 0
            continue
        pred = kf.predict()
        gate = cfg.max_jump_px_per_frame * (1 + missed)
        best, best_d = None, gate
        for b in cands:
            d = float(np.hypot(b.xy[0] - pred[0], b.xy[1] - pred[1]))
            # prefer confident detections: discount distance by confidence
            score = d * (1.5 - b.conf)
            if d < gate and score < best_d:
                best, best_d = b, score
        if best is not None:
            kf.update(best.xy)
            f.ball = BallObs(best.xy, best.radius, best.conf)
            missed = 0
        else:
            missed += 1
            if missed > cfg.max_gap_frames * 2:
                kf = None  # lost: re-acquire from the most confident detection
                if cands:
                    best = max(cands, key=lambda b: b.conf)
                    kf = _KF(best.xy, cfg.process_noise, cfg.measurement_noise)
                    f.ball = BallObs(best.xy, best.radius, best.conf)
                    missed = 0
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
