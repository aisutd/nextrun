"""The court for a whole clip: one image -> court homography per frame, for fixed and moving cameras.

    video ──► camera motion (frame-to-frame homography of the background, players masked out)
      │            │
      │            ├─ the frame never shifts by more than CameraConfig.moving_px -> fixed camera:
      │            │     one calibration for the clip (court.auto.calibrate_court, rims checked), used everywhere
      │            │
      │            └─ moving camera (pans, zooms, a handheld phone, a drone), split at cuts (motion lost):
      ▼                 court model on keyframes (every keyframe_s), each fit checked against that frame's rims
    keyframe fits ──► carried to every frame of its shot through the camera motion
                      ──► each frame takes the weighted median of the fits within window_s (wrong fits, e.g.
                          the two baskets swapped, are outvoted by their neighbours; 180-degree readings are
                          made consistent across the shot first)
                      ──► CourtTrack: frame idx -> CourtCalib (conf drops where the fits disagree or are far)

Everything downstream (fusion, events, overlay) asks `court.at(frame_idx)`; a plain CourtCalib answers the same
call with itself, so a fixed camera and the live API are unchanged.
"""
from __future__ import annotations

import bisect
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .. import fusion
from ..config import Config, CourtSpec
from ..schema import BallObs, FrameState, PlayerObs, RimObs
from .base import CourtCalib, CourtNotFound

log = logging.getLogger(__name__)

ROT = np.diag([-1.0, -1.0, 1.0])  # the court turned 180 degrees about center court


@dataclass
class CourtTrack:
    spec: CourtSpec
    calibs: dict[int, CourtCalib] = field(default_factory=dict)  # video frame idx -> court for that frame
    moving: bool = False
    method: str = "static"
    checks: dict = field(default_factory=dict)

    def __post_init__(self):
        self._keys = sorted(self.calibs)

    @classmethod
    def static(cls, calib: CourtCalib) -> "CourtTrack":
        return cls(calib.spec, {0: calib}, False, calib.method, dict(calib.checks))

    def at(self, idx: int) -> CourtCalib | None:
        """The court for frame `idx` (nearest calibrated frame; a fixed camera has one for all)."""
        if not self._keys:
            return None
        if not self.moving:
            return self.calibs[self._keys[0]]
        i = bisect.bisect_left(self._keys, idx)
        near = [k for k in self._keys[max(0, i - 1): i + 1]]
        k = min(near, key=lambda k: abs(k - idx))
        return self.calibs[k] if abs(k - idx) <= 2 else None  # beyond a couple of frames: not calibrated

    @property
    def conf(self) -> float:
        """Median per-frame confidence."""
        return float(np.median([c.conf for c in self.calibs.values()])) if self.calibs else 0.0

    def usable_share(self, min_conf: float) -> float:
        return float(np.mean([c.conf >= min_conf for c in self.calibs.values()])) if self.calibs else 0.0

    def best(self) -> CourtCalib | None:
        return max(self.calibs.values(), key=lambda c: c.conf, default=None)

    def to_dict(self) -> dict:
        return {"moving": self.moving, "method": self.method, "spec": self.spec.__dict__, "checks": self.checks,
                "frames": {str(k): {"H": c.H.tolist(), "conf": c.conf} for k, c in self.calibs.items()},
                "image_size": next(iter(self.calibs.values())).image_size if self.calibs else None,
                "static_calib": self.calibs[self._keys[0]].to_dict() if self.calibs and not self.moving else None}

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict()))

    @classmethod
    def load(cls, path: str | Path) -> "CourtTrack":
        d = json.loads(Path(path).read_text())
        spec = CourtSpec(**d["spec"])
        if d.get("static_calib"):
            c = d["static_calib"]
            calib = CourtCalib(np.asarray(c["H"], float), c["method"], c["conf"], spec,
                               tuple(c["image_size"]) if c.get("image_size") else None,
                               {k: tuple(v) for k, v in c.get("correspondences", {}).items()}, c.get("checks", {}))
            return cls.static(calib)
        size = tuple(d["image_size"]) if d.get("image_size") else None
        calibs = {int(k): CourtCalib(np.asarray(v["H"], float), d["method"], v["conf"], spec, size)
                  for k, v in d["frames"].items()}
        return cls(spec, calibs, d["moving"], d["method"], d.get("checks", {}))


# --- camera motion -------------------------------------------------------------------------------------
def _gray(img: np.ndarray, width: int) -> tuple[np.ndarray, float]:
    s = min(1.0, width / img.shape[1])
    g = cv2.cvtColor(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img,
                     cv2.COLOR_BGR2GRAY)
    return g, s


def _mask(shape, boxes, s: float) -> np.ndarray:
    """Background only: people move on their own, so their pixels say nothing about the camera."""
    m = np.full(shape, 255, np.uint8)
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(m, (int(x1 * s) - 4, int(y1 * s) - 4), (int(x2 * s) + 4, int(y2 * s) + 4), 0, -1)
    return m


def frame_motion(prev: np.ndarray, cur: np.ndarray, mask: np.ndarray | None, s: float,
                 min_inliers: int = 40) -> np.ndarray | None:
    """Homography prev -> cur (full-resolution pixels) from tracked corners, or None (a cut, a blur, a blank)."""
    p0 = cv2.goodFeaturesToTrack(prev, 600, 0.01, 8, mask=mask)
    if p0 is None or len(p0) < min_inliers:
        return None
    p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, winSize=(21, 21), maxLevel=3)
    ok = st.ravel() == 1
    if ok.sum() < min_inliers:
        return None
    H, inl = cv2.findHomography(p0[ok], p1[ok], cv2.RANSAC, 2.0)
    if H is None or inl.sum() < min_inliers:
        return None
    S = np.diag([s, s, 1.0])
    return np.linalg.inv(S) @ H @ S


def corner_shift(M: np.ndarray, w: int, h: int) -> float:
    """Largest displacement of the frame corners under M, in pixels."""
    c = np.float32([[0, 0], [w, 0], [0, h], [w, h]]).reshape(-1, 1, 2)
    return float(np.abs(cv2.perspectiveTransform(c, M) - c).reshape(-1, 2).max())


def camera_moves(video: str, cfg: Config, n_pairs: int = 8) -> bool:
    """Quick check before tracking (the tracker needs to know), on a handful of frames: does the view shift
    between frames ~0.5 s apart (a pan, a handheld phone), or drift away from the first frame over the clip
    (a hovering drone, a camera knocked mid-game)?"""
    from ..datasets import camera_shift

    if cfg.camera.mode != "auto":
        return cfg.camera.mode == "moving"
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    gap = max(1, int(round((cap.get(cv2.CAP_PROP_FPS) or 30) / 2)))

    def read(i):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        return f if ok else None

    first = read(0)
    shifts, drift = [], 0.0
    for i in np.linspace(0, max(n - gap - 1, 0), n_pairs).astype(int):
        a, b = read(i), read(i + gap)
        if a is None or b is None:
            continue
        (ga, s), (gb, _) = _gray(a, cfg.camera.motion_width), _gray(b, cfg.camera.motion_width)
        M = frame_motion(ga, gb, None, s)
        shifts.append(corner_shift(M, a.shape[1], a.shape[0]) / a.shape[1] if M is not None else 1.0)
        if first is not None and i > 0:
            D, _ = camera_shift(first, a, cfg.camera.motion_width)
            drift = max(drift, corner_shift(D, a.shape[1], a.shape[0]) / a.shape[1] if D is not None else 1.0)
    cap.release()
    return bool(shifts) and (float(np.median(shifts)) > cfg.camera.moving_px or drift > cfg.camera.drift_px)


class CameraMotion:
    """Frame-to-frame camera motion through a clip. Per frame: the shot it belongs to (a new shot starts where the
    motion is lost: a cut, a blur) and the homography from that shot's first frame to it. Measured once, during
    detection (pipeline.detect), and used for the rims (ball_track.stabilize_rims_moving) and the court track."""

    def __init__(self, width: int = 640):
        self.width = width
        self.idx: list[int] = []
        self.seg: list[int] = []
        self.M: list[np.ndarray] = []
        self._prev = None

    def add(self, idx: int, img: np.ndarray, boxes) -> None:
        """Next frame, with the boxes of the people in it (masked out: they move on their own)."""
        g, s = _gray(img, self.width)
        if self._prev is None:
            seg, cum = 0, np.eye(3)
        else:
            pg, ps, pboxes = self._prev
            m = frame_motion(pg, g, _mask(pg.shape, pboxes, ps), s)
            seg, cum = (self.seg[-1] + 1, np.eye(3)) if m is None else (self.seg[-1], m @ self.M[-1])
        self.idx.append(idx)
        self.seg.append(seg)
        self.M.append(cum)
        self._prev = (g, s, list(boxes))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"idx": self.idx, "seg": self.seg, "M": [m.round(6).tolist() for m in self.M]}))

    @classmethod
    def load(cls, path: str | Path) -> "CameraMotion":
        d = json.loads(Path(path).read_text())
        m = cls()
        m.idx, m.seg, m.M = d["idx"], d["seg"], [np.asarray(x, float) for x in d["M"]]
        return m


# --- combining keyframe fits ---------------------------------------------------------------------------
def _grid(w: int, h: int) -> np.ndarray:
    """Image points the fits are compared on: the lower 3/4 of the frame, where the floor is."""
    xs, ys = np.linspace(0.05 * w, 0.95 * w, 6), np.linspace(0.25 * h, 0.95 * h, 5)
    return np.array([(x, y) for y in ys for x in xs], np.float64)


def _project(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Image -> court; points at or behind the horizon come back as nan."""
    P = np.c_[pts, np.ones(len(pts))] @ H.T
    out = P[:, :2] / P[:, 2:3]
    ref = P[-3, 2]  # sign of the bottom-centre grid point, which is on the floor in front of the camera
    out[np.sign(P[:, 2]) != np.sign(ref)] = np.nan
    return out


def _dist(Ha: np.ndarray, Hb: np.ndarray, grid: np.ndarray, spec: CourtSpec) -> float:
    a, b = _project(Ha, grid), _project(Hb, grid)
    lim = np.array([spec.length / 2 + 6, spec.width / 2 + 6])
    ok = np.isfinite(a).all(1) & np.isfinite(b).all(1) & (np.abs(a) <= lim).all(1)
    return float(np.median(np.linalg.norm(a[ok] - b[ok], axis=1))) if ok.sum() >= 4 else float("inf")


def _combine(cands: list[tuple[np.ndarray, float]], grid: np.ndarray, spec: CourtSpec) -> tuple[np.ndarray, float] | None:
    """Weighted median of the court position of every grid point over the candidate fits, refit to one
    homography. Returns (H, spread in meters) or None."""
    P = np.stack([_project(H, grid) for H, _ in cands])  # (k, n, 2)
    w = np.array([wt for _, wt in cands])
    lim = np.array([spec.length / 2 + 6, spec.width / 2 + 6])
    med = np.full((len(grid), 2), np.nan)
    for j in range(len(grid)):
        ok = np.isfinite(P[:, j]).all(1) & (np.abs(P[:, j]) <= lim).all(1)
        if w[ok].sum() < 0.5 * w.sum():
            continue
        for d in range(2):
            v, ww = P[ok, j, d], w[ok]
            o = np.argsort(v)
            c = np.cumsum(ww[o])
            med[j, d] = v[o][np.searchsorted(c, c[-1] / 2)]
    ok = np.isfinite(med).all(1)
    if ok.sum() < 6:
        return None
    H, _ = cv2.findHomography(grid[ok], med[ok], 0)
    if H is None:
        return None
    dev = np.linalg.norm(P[:, ok] - med[ok][None], axis=2)  # (k, n_ok)
    spread = float(np.nansum(np.nanmedian(dev, axis=1) * w) / w.sum())
    return H, spread


def track_court(video: str, frames: list[FrameState], cfg: Config, motion: CameraMotion | None = None) -> CourtTrack:
    """Court for every tracked frame of a moving-camera clip (see module docstring). motion: from detection
    (measured here when not given)."""
    from ..video import iter_frames
    from .keypoints import KeypointCourtEstimator

    cc = cfg.camera
    est = KeypointCourtEstimator(cfg.court, cfg.models.court_keypoint_weights, cfg.models.court_keypoint_config,
                                 cfg.models.device)
    by_idx = {f.idx: f for f in frames}
    fps = (frames[-1].idx - frames[0].idx) / max(frames[-1].t - frames[0].t, 1e-6) if len(frames) > 1 else 30.0
    every = max(1, int(round(cc.keyframe_s * fps / max(cfg.stride, 1))))
    if motion is not None and motion.idx != [f.idx for f in frames]:
        motion = None  # from another run's frames
    measure = motion is None
    if measure:
        motion = CameraMotion(cc.motion_width)

    # 1) one pass over the video: camera motion (unless given) + court fits on keyframes
    fits: dict[int, CourtCalib] = {}
    size, t = None, -1
    for n, (idx, img) in enumerate(iter_frames(video, cfg.stride, max_frames=cfg.max_frames)):
        if idx not in by_idx:
            continue
        t += 1
        size = (img.shape[1], img.shape[0])
        if measure:
            motion.add(idx, img, [p.bbox for p in by_idx[idx].players])
        if n % every == 0:
            try:
                c = est.estimate(img)
            except CourtNotFound:
                continue
            if by_idx[idx].rims:
                c = fusion.validate_court(c, [by_idx[idx].rims], cfg.fusion)
            fits[t] = c
    if size is None:
        raise CourtNotFound("track: no frames")
    seg, M, pos_idx = motion.seg, motion.M, motion.idx
    w, h = size
    grid = _grid(w, h)
    spec = cfg.court

    # 2) per shot: make the 180-degree readings agree, then combine nearby fits for every frame
    calibs: dict[int, CourtCalib] = {}
    flips = 0
    for sg in sorted(set(seg)):
        ks = [k for k in fits if seg[k] == sg and fits[k].conf > 0.05]
        if not ks:
            continue
        # each fit as a court map of the shot's first frame: G = H_k @ M_k
        G = {k: fits[k].H @ M[k] for k in ks}
        ref = max(ks, key=lambda k: fits[k].conf)
        same = {k: _dist(G[k], G[ref], grid, spec) <= _dist(ROT @ G[k], G[ref], grid, spec) for k in ks}
        w_same = sum(fits[k].conf for k in ks if same[k])
        w_flip = sum(fits[k].conf for k in ks if not same[k])
        keep_same = w_same >= w_flip
        for k in ks:
            if same[k] != keep_same:
                G[k] = ROT @ G[k]
                flips += 1
        win = max(1, int(round(cc.window_s * fps / max(cfg.stride, 1))))
        for t in [i for i in range(len(seg)) if seg[i] == sg]:
            near = [k for k in ks if abs(k - t) <= win] or [min(ks, key=lambda k: abs(k - t))]
            Minv = np.linalg.inv(M[t])
            tau = max(win / 2, 1)
            cands = [(G[k] @ Minv, fits[k].conf * np.exp(-abs(k - t) / tau)) for k in near]
            r = _combine(cands, grid, spec)
            if r is None:
                continue
            H, spread = r
            gap_s = min(abs(k - t) for k in near) * max(cfg.stride, 1) / fps
            wsum = sum(wt for _, wt in cands)
            fit_conf = sum(fits[k].conf * wt for k, (_, wt) in zip(near, cands)) / max(wsum, 1e-9)
            conf = float(fit_conf * np.exp(-spread / cc.spread_m) * np.exp(-max(gap_s - cc.window_s, 0) / 2.0))
            calibs[pos_idx[t]] = CourtCalib(H, "keypoints+motion", conf, spec, size)
    checks = {"keyframes": len(fits), "keyframes_ok": sum(c.conf >= cfg.fusion.min_court_conf for c in fits.values()),
              "shots": len(set(seg)), "flipped": flips, "frames": len(pos_idx), "frames_calibrated": len(calibs)}
    track = CourtTrack(spec, calibs, True, "keypoints+motion", checks)
    checks["usable_share"] = track.usable_share(cfg.fusion.min_court_conf)
    log.info("court track (moving camera): %s, median conf %.2f", checks, track.conf)
    return track


# --- a stabilized view for the event logic ---------------------------------------------------------------
def _warp_pts(pts, H: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(np.asarray(pts, np.float64).reshape(-1, 1, 2), H).reshape(-1, 2)


def _warp_box(box, H: np.ndarray) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    p = _warp_pts([[x1, y1], [x2, y1], [x1, y2], [x2, y2]], H)
    return float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()), float(p[:, 1].max())


def stabilize_view(frames: list[FrameState], court: CourtTrack | CourtCalib | None, motion: CameraMotion
                   ) -> tuple[list[FrameState], CourtTrack | CourtCalib | None]:
    """Moving camera -> the same scene as a fixed camera would see it: every frame's players, ball and rims are
    mapped into its shot's first frame (camera motion undone), and the court of each frame is re-expressed in
    those coordinates (H_t @ M_t). The event logic (ball arcs, ball through the rim, hands near the ball) can then
    compare positions across frames as it does for a fixed camera. Returns copies; the input stays in image
    coordinates for drawing."""
    at = dict(zip(motion.idx, range(len(motion.idx))))
    out = []
    for f in frames:
        k = at.get(f.idx)
        if k is None:
            out.append(f)
            continue
        Minv = np.linalg.inv(motion.M[k])
        players = []
        for p in f.players:
            kp = None
            if p.keypoints is not None:
                kp = np.asarray(p.keypoints, float).copy()
                kp[:, :2] = _warp_pts(kp[:, :2], Minv)
            players.append(PlayerObs(p.track_id, _warp_box(p.bbox, Minv), p.conf, kp, p.court_xy))
        ball = None
        if f.ball is not None:
            ball = BallObs(tuple(float(v) for v in _warp_pts([f.ball.xy], Minv)[0]), f.ball.radius, f.ball.conf,
                           f.ball.interpolated)
        rims = [RimObs(_warp_box(r.bbox, Minv), r.conf) for r in f.rims]
        out.append(FrameState(f.idx, f.t, players, ball, [], rims))
    if court is None or not isinstance(court, CourtTrack) or not court.moving:
        return out, court
    calibs = {}
    for idx, c in court.calibs.items():
        k = at.get(idx)
        if k is not None:
            calibs[idx] = CourtCalib(c.H @ motion.M[k], c.method, c.conf, c.spec, c.image_size)
    return out, CourtTrack(court.spec, calibs, True, court.method, court.checks)
