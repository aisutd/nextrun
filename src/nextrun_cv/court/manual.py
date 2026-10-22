"""Method A — manual calibration: the user marks >= 4 known court landmarks once per camera setup.
Most reliable option for a fixed camera; also the fallback when the automatic methods fail.

Ways to provide the points:
  * JSON file  {"R_base_top": [u, v], "R_paint_ft_top": [u, v], ...}
  * Desktop:   `cv2_click_landmarks(frame, names)` (OpenCV window)
Use `landmark_reference_image(spec)` to see where each named landmark is on the court."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from ..config import CourtSpec
from . import template
from .base import CourtCalib, CourtEstimator, CourtNotFound, homography_from_landmarks

# Landmarks that are usually visible from a sideline/baseline-corner camera filming one half court
DEFAULT_HALF_COURT_POINTS = ["R_base_top", "R_base_bot", "R_paint_ft_top", "R_paint_ft_bot", "R_arc_top", "mid_top", "mid_bot"]


class ManualCourtEstimator(CourtEstimator):
    name = "manual"

    def __init__(self, spec: CourtSpec, pairs: dict[str, tuple[float, float]] | str | Path):
        super().__init__(spec)
        if isinstance(pairs, (str, Path)):
            pairs = {k: tuple(v) for k, v in json.loads(Path(pairs).read_text()).items()}
        self.pairs = pairs

    def estimate(self, frame: np.ndarray | None = None) -> CourtCalib:
        if not self.pairs:
            raise CourtNotFound("manual: no landmark points provided")
        calib = homography_from_landmarks(self.pairs, self.spec, self.name)
        if frame is not None:
            calib.image_size = (frame.shape[1], frame.shape[0])
        return calib


def landmark_reference_image(spec: CourtSpec, px_per_m: int = 30) -> np.ndarray:
    """Top-down court diagram with every landmark labelled — shows users what to click."""
    pad = 40
    w = int(spec.length * px_per_m) + 2 * pad
    h = int(spec.width * px_per_m) + 2 * pad
    img = np.full((h, w, 3), (60, 110, 170), np.uint8)

    def to_px(p):
        return int(pad + (p[0] + spec.length / 2) * px_per_m), int(pad + (p[1] + spec.width / 2) * px_per_m)

    for pl in template.polylines(spec):
        cv2.polylines(img, [np.array([to_px(p) for p in pl], np.int32)], False, (255, 255, 255), 2)
    for name, p in template.landmarks(spec).items():
        u, v = to_px(p)
        cv2.circle(img, (u, v), 5, (0, 0, 255), -1)
        cv2.putText(img, name, (u + 4, v - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1, cv2.LINE_AA)
    return img


def cv2_click_landmarks(frame: np.ndarray, names: list[str] = DEFAULT_HALF_COURT_POINTS) -> dict[str, tuple[float, float]]:
    """Desktop: click each landmark in order; press 's' to skip one that isn't visible, 'q' to finish."""
    pairs: dict[str, tuple[float, float]] = {}
    i = 0
    win = "mark court landmarks"
    disp = frame.copy()

    def on_mouse(event, x, y, *_):
        nonlocal i
        if event == cv2.EVENT_LBUTTONDOWN and i < len(names):
            pairs[names[i]] = (float(x), float(y))
            cv2.circle(disp, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(disp, names[i], (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            i += 1

    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)
    while i < len(names):
        view = disp.copy()
        cv2.putText(view, f"click: {names[i]}  (s=skip, q=done)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(win, view)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("s"):
            i += 1
        elif k == ord("q"):
            break
    cv2.destroyWindow(win)
    return pairs
