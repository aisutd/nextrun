"""Last-resort court estimate when no model or line search found the court.

From the scene alone: players' feet show where the floor is and how big a metre is (people are ~1.8 m tall), the
rim shows which end the hoop is, and the way the players spread shows whether the camera looks along the length
or across the width of the court. That fixes a rough ground-plane mapping (an affine view with the usual ~25
degree camera tilt). It is an estimate to draw and adjust, not a measurement: conf is deliberately low."""
from __future__ import annotations

import numpy as np

from ..config import CourtSpec
from ..schema import FrameState
from .base import CourtCalib, CourtNotFound

TILT = 0.45  # how much the ground is foreshortened along the viewing direction (sin of ~25 deg elevation)


def estimate_from_scene(frames: list[FrameState], spec: CourtSpec, size: tuple[int, int]) -> CourtCalib:
    feet = np.array([p.feet for f in frames for p in f.players], float)
    heights = [p.height for f in frames for p in f.players]
    if len(feet) < 8:
        raise CourtNotFound("scene estimate: too few players seen")
    ppm = float(np.median(heights)) / 1.8  # image pixels per metre across the floor at player depth
    c = np.median(feet, axis=0)
    lo, hi = np.percentile(feet, [5, 95], axis=0)
    ex, ey = hi - lo
    length_horizontal = ex >= ey / TILT  # court length runs left-right in the image (sideline camera)
    rims = [r for f in frames[:1] for r in f.rims]
    rim = max(rims, key=lambda r: r.conf).center if rims else None
    half = spec.length / 4  # centre of the half court the players are in, in metres from centre court
    if length_horizontal:
        right = True if rim is None else rim[0] >= c[0]  # hoop on the right of the players -> right-hand basket
        s = 1.0 if right else -1.0
        A = np.array([[ppm, 0.0], [0.0, ppm * TILT]])  # court (x, y) metres -> image offset (px)
        origin = c - A @ np.array([s * half, 0.0])
    else:
        far = True if rim is None else rim[1] <= c[1]  # hoop further from the camera than the players
        s = 1.0 if far else -1.0
        A = np.array([[0.0, ppm], [-ppm * TILT, 0.0]])  # court x runs away from the camera, court y runs rightwards
        origin = c - A @ np.array([s * half, 0.0])
    H_c2i = np.array([[A[0, 0], A[0, 1], origin[0]], [A[1, 0], A[1, 1], origin[1]], [0.0, 0.0, 1.0]])
    calib = CourtCalib(H=np.linalg.inv(H_c2i), spec=spec, method="estimate", conf=0.15, correspondences={})
    calib.image_size = size
    return calib
