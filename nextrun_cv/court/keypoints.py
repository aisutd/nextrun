"""Method C — learned court keypoints (Rishabh's court-detection model, PR #2).

YOLO11s-pose, one "court" instance with 24 keypoints, trained on high-school gym footage from corner and
sideline cameras. Weights: models/court_model.pt. Keypoint court positions + 3PT geometry:
configs/court_keypoints.json (feet, measured from the training labels). Visible keypoints -> RANSAC
homography -> court meters in the pipeline frame (origin center court, +x toward the right basket).

Keypoint ids (left basket / right basket):
  0/5 baseline corners (far/near)       10/15     2/3 paint corners on baseline   12/13
  1/4 corner-3 line meets baseline      11/14     6/7 free-throw line ends        16/17
  18/19/20 3PT arc far wing/top/near    21/22/23  8/9 half-court line at far/near sideline
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from ..config import CourtSpec
from . import template
from .base import CourtCalib, CourtEstimator, CourtNotFound

FT = 0.3048

# keypoint id -> template landmark name, where one exists (used for drawing / diagnostics only)
_NAMES = {
    0: "L_base_top", 1: "L_c3_base_top", 2: "L_paint_base_top", 3: "L_paint_base_bot", 4: "L_c3_base_bot",
    5: "L_base_bot", 6: "L_paint_ft_top", 7: "L_paint_ft_bot", 8: "mid_top", 9: "mid_bot", 19: "L_arc_top",
    10: "R_base_top", 11: "R_c3_base_top", 12: "R_paint_base_top", 13: "R_paint_base_bot", 14: "R_c3_base_bot",
    15: "R_base_bot", 16: "R_paint_ft_top", 17: "R_paint_ft_bot", 22: "R_arc_top",
}


def orientation_sign(H: np.ndarray, uv: tuple[float, float]) -> float:
    """Sign of det(d court / d image) at `uv`. A camera above the floor always sees the court with the
    same handedness as the top-down template (x right, y toward the near sideline), so a negative sign
    means left/right keypoints were swapped (a mirror solution)."""
    u, v = uv
    p = np.array([[u, v, 1.0], [u + 1, v, 1.0], [u, v + 1, 1.0]]) @ H.T
    p = p[:, :2] / p[:, 2:3]
    return float(np.sign(np.linalg.det(np.stack([p[1] - p[0], p[2] - p[0]]))))


def load_keypoint_config(path: str | Path) -> dict:
    """court_keypoints.json -> {'court_m': {id: (x, y) meters}, 'use_ids', 'flip_idx', 'length_m', 'width_m'}.
    The file's frame is feet with x across the court (0 = far sideline) and y along it (0 = left baseline)."""
    cfg = json.loads(Path(path).read_text())
    L, W = cfg["court_length_ft"], cfg["court_width_ft"]
    court_m = {int(k): ((v[1] - L / 2) * FT, (v[0] - W / 2) * FT) for k, v in cfg["keypoints_ft"].items() if v is not None}
    return {
        "court_m": court_m,
        "use_ids": [int(i) for i in cfg["use_ids"]],
        "flip_idx": [int(i) for i in cfg["flip_idx"]],
        "length_m": L * FT,
        "width_m": W * FT,
    }


ARC_IDS = {18: 0, 19: 0, 20: 0, 21: 1, 22: 1, 23: 1}  # 3PT-arc keypoints -> hoop index (0 left, 1 right)


def ideal_keypoints(spec: CourtSpec) -> dict[int, tuple[float, float]]:
    """Where the 24 keypoints are by definition on a court of this spec (meters, pipeline frame).
    Arc keypoints are not included: their position along the arc is a labelling convention."""
    L2, W2, pw2 = spec.length / 2, spec.width / 2, spec.paint_width / 2
    yc = W2 - spec.corner_three_offset
    ftx = L2 - spec.ft_line_from_baseline
    left = {0: (-L2, -W2), 1: (-L2, -yc), 2: (-L2, -pw2), 3: (-L2, pw2), 4: (-L2, yc), 5: (-L2, W2),
            6: (-ftx, -pw2), 7: (-ftx, pw2)}
    out = dict(left)
    out.update({i + 10: (-x, y) for i, (x, y) in left.items()})
    out.update({8: (0.0, -W2), 9: (0.0, W2)})
    return out


def keypoints_for_court(kp: dict, spec: CourtSpec, measured_on: CourtSpec | None = None) -> dict[int, tuple[float, float]]:
    """Court positions of the keypoints on `spec`. The config's positions were measured on a high-school
    court and include small labelling offsets (e.g. annotators clicking a line's outer edge); those offsets
    are kept and the court geometry is swapped, so the same model maps NBA / FIBA / high-school courts.
    Arc keypoints keep their measured angle around the hoop and radial offset from the line."""
    measured_on = measured_on or CourtSpec.preset("highschool")
    meas = kp["court_m"]
    ideal_src, ideal_dst = ideal_keypoints(measured_on), ideal_keypoints(spec)
    hoops_src, hoops_dst = template.hoop_positions(measured_on), template.hoop_positions(spec)
    out = {}
    for i, (x, y) in meas.items():
        if i in ARC_IDS:
            hx, hy = hoops_src[ARC_IDS[i]]
            r, a = np.hypot(x - hx, y - hy), np.arctan2(y - hy, x - hx)
            r += spec.three_pt_radius - measured_on.three_pt_radius
            gx, gy = hoops_dst[ARC_IDS[i]]
            out[i] = (float(gx + r * np.cos(a)), float(gy + r * np.sin(a)))
        elif i in ideal_dst:
            out[i] = (x + ideal_dst[i][0] - ideal_src[i][0], y + ideal_dst[i][1] - ideal_src[i][1])
    return out


class KeypointCourtEstimator(CourtEstimator):
    name = "keypoints"

    def __init__(self, spec: CourtSpec, weights: str, config: str, device: str | None = None, kp_conf: float = 0.5):
        super().__init__(spec)
        if not Path(weights).exists():
            raise CourtNotFound(f"keypoints: weights not found at {weights}")
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.device = device
        self.kp_conf = kp_conf
        self.kp = load_keypoint_config(config)
        self.kp["court_m"] = keypoints_for_court(self.kp, spec)

    def detect(self, frame: np.ndarray) -> dict[int, tuple[float, float]]:
        """{keypoint id: (u, v)} for confidently detected, in-frame keypoints."""
        res = self.model.predict(frame, conf=0.25, device=self.device, verbose=False)[0]
        if res.keypoints is None or res.boxes is None or len(res.boxes) == 0:
            raise CourtNotFound("keypoints: no court instance detected")
        best = int(res.boxes.conf.argmax())
        kps = res.keypoints.data[best].cpu().numpy()
        h, w = frame.shape[:2]
        return {
            i: (float(x), float(y))
            for i, (x, y, c) in enumerate(kps)
            if i in self.kp["use_ids"] and i in self.kp["court_m"] and c >= self.kp_conf and 0 <= x < w and 0 <= y < h
        }

    def _fit(self, pairs: dict[int, tuple[float, float]]) -> CourtCalib:
        if len(pairs) < 4:
            raise CourtNotFound(f"keypoints: need >= 4 court keypoints, got {len(pairs)}")
        ids = list(pairs)
        img = np.float32([pairs[i] for i in ids])
        court = np.float32([self.kp["court_m"][i] for i in ids])
        H, mask = cv2.findHomography(img, court, cv2.RANSAC, 1.5 * FT)
        if H is None:
            raise CourtNotFound("keypoints: degenerate keypoint configuration")
        inl = mask.ravel().astype(bool)
        proj = cv2.perspectiveTransform(img[inl].reshape(-1, 1, 2), H).reshape(-1, 2)
        err = float(np.linalg.norm(proj - court[inl], axis=1).mean())
        corr = {_NAMES.get(i, f"kp{i}"): pairs[i] for i, k in zip(ids, inl) if k}
        return CourtCalib(H, self.name, float(inl.mean() * np.exp(-err)), self.spec, correspondences=corr)

    def estimate(self, frame: np.ndarray, pairs: dict[int, tuple[float, float]] | None = None) -> CourtCalib:
        pairs = self.detect(frame) if pairs is None else pairs
        h, w = frame.shape[:2]
        calib = self._fit(pairs)
        if orientation_sign(calib.H, (w / 2, h / 2)) < 0:
            # model confused which half it is looking at: relabel left <-> right and refit
            flip = self.kp["flip_idx"]
            calib = self._fit({flip[i]: uv for i, uv in pairs.items() if flip[i] in self.kp["court_m"]})
        calib.image_size = (w, h)
        return calib
