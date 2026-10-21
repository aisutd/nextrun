"""Court geometry in meters: named landmarks (used for homography correspondences and as the
court-keypoint model's label order), polylines (drawing / line matching) and 3PT classification.

Frame: origin at center court, +x toward the right basket, +y across the court."""
from __future__ import annotations

import math

import numpy as np

from ..config import CourtSpec


def hoop_positions(spec: CourtSpec) -> list[tuple[float, float]]:
    hx = spec.length / 2 - spec.hoop_from_baseline
    return [(-hx, 0.0), (hx, 0.0)]


def _half_landmarks(spec: CourtSpec, side: int) -> dict[str, tuple[float, float]]:
    """side = +1 for the right half, -1 for the left half."""
    L2, W2, pw2 = spec.length / 2, spec.width / 2, spec.paint_width / 2
    hx = L2 - spec.hoop_from_baseline
    yc = W2 - spec.corner_three_offset
    R = spec.three_pt_radius
    c3x = hx - math.sqrt(max(R * R - yc * yc, 0.0))
    ftx = L2 - spec.ft_line_from_baseline
    p = "R_" if side > 0 else "L_"
    pts = {
        "base_top": (L2, -W2),
        "base_bot": (L2, W2),
        "paint_base_top": (L2, -pw2),
        "paint_base_bot": (L2, pw2),
        "paint_ft_top": (ftx, -pw2),
        "paint_ft_bot": (ftx, pw2),
        "c3_base_top": (L2, -yc),
        "c3_base_bot": (L2, yc),
        "c3_arc_top": (c3x, -yc),
        "c3_arc_bot": (c3x, yc),
        "arc_top": (hx - R, 0.0),
        "ft_center": (ftx, 0.0),
        "backboard": (L2 - spec.backboard_from_baseline, 0.0),
    }
    if spec.sideline_hash_from_baseline is not None:
        pts["hash_top"] = (L2 - spec.sideline_hash_from_baseline, -W2)
        pts["hash_bot"] = (L2 - spec.sideline_hash_from_baseline, W2)
    return {p + k: (side * x, y) for k, (x, y) in pts.items()}


def landmarks(spec: CourtSpec) -> dict[str, tuple[float, float]]:
    W2 = spec.width / 2
    out: dict[str, tuple[float, float]] = {}
    out.update(_half_landmarks(spec, -1))
    out.update(_half_landmarks(spec, +1))
    out.update(
        {
            "mid_top": (0.0, -W2),
            "mid_bot": (0.0, W2),
            "center_top": (0.0, -spec.center_circle_radius),
            "center": (0.0, 0.0),
            "center_bot": (0.0, spec.center_circle_radius),
        }
    )
    return out


_HALF_KP = [
    "base_top", "c3_base_top", "paint_base_top", "paint_base_bot", "c3_base_bot", "base_bot", "backboard",
    "c3_arc_top", "c3_arc_bot", "paint_ft_top", "ft_center", "paint_ft_bot", "hash_top", "arc_top", "hash_bot",
]
KEYPOINT_NAMES = (
    ["L_" + n for n in _HALF_KP] + ["R_" + n for n in _HALF_KP]
    + ["mid_top", "center_top", "center", "center_bot", "mid_bot"]
)


def keypoint_order() -> list[str]:
    """Fixed label order for the court-keypoint pose model. Independent of the court spec: landmarks
    a court doesn't have (e.g. hash marks on a FIBA court) are simply skipped when solving."""
    return list(KEYPOINT_NAMES)


def keypoint_flip_idx() -> list[int]:
    """Horizontal image flip mirrors court x: swap L_* and R_* landmarks."""
    names = keypoint_order()
    idx = {n: i for i, n in enumerate(names)}
    out = []
    for n in names:
        if n.startswith("L_"):
            out.append(idx["R_" + n[2:]])
        elif n.startswith("R_"):
            out.append(idx["L_" + n[2:]])
        else:
            out.append(idx[n])
    return out


def _arc(cx, cy, r, a0, a1, n=48):
    a = np.linspace(a0, a1, n)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)


def polylines(spec: CourtSpec) -> list[np.ndarray]:
    """All painted court lines as (N, 2) arrays in meters."""
    L2, W2, pw2 = spec.length / 2, spec.width / 2, spec.paint_width / 2
    lines = [
        np.array([[-L2, -W2], [L2, -W2], [L2, W2], [-L2, W2], [-L2, -W2]]),
        np.array([[0, -W2], [0, W2]]),
        _arc(0, 0, spec.center_circle_radius, 0, 2 * math.pi),
    ]
    for side in (-1, 1):
        hx = L2 - spec.hoop_from_baseline
        ftx = L2 - spec.ft_line_from_baseline
        yc = W2 - spec.corner_three_offset
        R = spec.three_pt_radius
        c3x = hx - math.sqrt(max(R * R - yc * yc, 0.0))
        lines.append(np.array([[L2, -pw2], [ftx, -pw2], [ftx, pw2], [L2, pw2]]) * [side, 1])
        lines.append(_arc(side * ftx, 0, spec.center_circle_radius, 0, 2 * math.pi))  # free-throw circle
        ang = math.asin(min(yc / R, 1.0))
        arc = _arc(0, 0, R, math.pi - ang, math.pi + ang, 64)  # opens toward center court
        arc[:, 0] += hx
        lines.append(np.vstack([[[L2, -yc]], arc[::-1], [[L2, yc]]]) * [side, 1])
    return lines


def sample_line_points(spec: CourtSpec, step: float = 0.25) -> np.ndarray:
    """Dense points along all court lines (for chamfer-style alignment scoring)."""
    pts = []
    for pl in polylines(spec):
        for a, b in zip(pl[:-1], pl[1:]):
            n = max(2, int(np.linalg.norm(b - a) / step))
            pts.append(np.linspace(a, b, n))
    return np.vstack(pts)


def court_polygon(spec: CourtSpec, margin: float = 1.0) -> np.ndarray:
    L2, W2 = spec.length / 2 + margin, spec.width / 2 + margin
    return np.array([[-L2, -W2], [L2, -W2], [L2, W2], [-L2, W2]], float)


def nearest_hoop(xy, spec: CourtSpec) -> tuple[int, float]:
    """(hoop index 0=left/1=right, distance in meters)."""
    hs = hoop_positions(spec)
    d = [math.hypot(xy[0] - h[0], xy[1] - h[1]) for h in hs]
    i = int(np.argmin(d))
    return i, d[i]


def is_three(xy, spec: CourtSpec, hoop: int | None = None) -> bool:
    """True if a shot from court position `xy` (shooter's feet) is a three-pointer.
    Beyond the arc OR in the corner beyond the straight corner line."""
    hs = hoop_positions(spec)
    if hoop is None:
        hoop, _ = nearest_hoop(xy, spec)
    hx, hy = hs[hoop]
    d = math.hypot(xy[0] - hx, xy[1] - hy)
    yc = spec.width / 2 - spec.corner_three_offset
    return d >= spec.three_pt_radius or abs(xy[1]) >= yc
