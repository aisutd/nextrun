"""Method C — learned court keypoints. A YOLO pose model whose single "court" instance has one
keypoint per named landmark (order = template.keypoint_order()). Visible keypoints become homography
correspondences (RANSAC). Weights go to models/court_keypoints.pt; train with
train/prepare_court_dataset.py + train/train_court_keypoints.py (public NBA court dataset, optionally
fine-tuned on frames from your own courts)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import CourtSpec
from . import template
from .base import CourtCalib, CourtEstimator, CourtNotFound, homography_from_landmarks


def _mirror_name(n: str) -> str:
    if n.startswith("L_"):
        return "R_" + n[2:]
    if n.startswith("R_"):
        return "L_" + n[2:]
    return n


def orientation_sign(H: np.ndarray, uv: tuple[float, float]) -> float:
    """Sign of det(d court / d image) at `uv`. A camera above the floor always sees the court with the
    same handedness as the top-down template (x right, y toward the near sideline), so a negative sign
    means left/right landmarks were swapped (a mirror solution)."""
    u, v = uv
    p = np.array([[u, v, 1.0], [u + 1, v, 1.0], [u, v + 1, 1.0]]) @ H.T
    p = p[:, :2] / p[:, 2:3]
    return float(np.sign(np.linalg.det(np.stack([p[1] - p[0], p[2] - p[0]]))))


class KeypointCourtEstimator(CourtEstimator):
    name = "keypoints"

    def __init__(self, spec: CourtSpec, weights: str, device: str | None = None, kp_conf: float = 0.5):
        super().__init__(spec)
        if not Path(weights).exists():
            raise CourtNotFound(f"keypoints: weights not found at {weights} (train with train/train_court_keypoints.py)")
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.device = device
        self.kp_conf = kp_conf
        self.names = template.keypoint_order()
        self.valid = set(template.landmarks(spec))  # e.g. FIBA courts have no sideline hash marks

    def detect(self, frame: np.ndarray) -> dict[str, tuple[float, float]]:
        """{landmark: (u, v)} for confidently detected, in-frame keypoints."""
        res = self.model.predict(frame, device=self.device, verbose=False)[0]
        if res.keypoints is None or len(res.keypoints.data) == 0:
            raise CourtNotFound("keypoints: no court instance detected")
        best = int(res.boxes.conf.argmax()) if res.boxes is not None and len(res.boxes) else 0
        kps = res.keypoints.data[best].cpu().numpy()
        if len(kps) != len(self.names):
            raise CourtNotFound(f"keypoints: model has {len(kps)} keypoints, template expects {len(self.names)}")
        h, w = frame.shape[:2]
        return {
            n: (float(x), float(y))
            for n, (x, y, c) in zip(self.names, kps)
            if n in self.valid and c >= self.kp_conf and 0 <= x < w and 0 <= y < h
        }

    def estimate(self, frame: np.ndarray) -> CourtCalib:
        pairs = self.detect(frame)
        h, w = frame.shape[:2]
        calib = homography_from_landmarks(pairs, self.spec, self.name, ransac_px=0.5)
        if orientation_sign(calib.H, (w / 2, h / 2)) < 0:
            # model confused which half it is looking at (common for one-basket fixed cameras)
            mirrored = {_mirror_name(n): uv for n, uv in pairs.items() if _mirror_name(n) in self.valid}
            calib = homography_from_landmarks(mirrored, self.spec, self.name, ransac_px=0.5)
        calib.image_size = (w, h)
        return calib
