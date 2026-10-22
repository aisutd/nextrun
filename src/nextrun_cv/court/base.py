"""Court calibration result + estimator interface shared by all court-detection methods."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..config import CourtSpec
from . import template


class CourtNotFound(RuntimeError):
    """Raised by an estimator that cannot produce a calibration (missing weights, too few lines...)."""


@dataclass
class CourtCalib:
    H: np.ndarray  # 3x3 homography: image px -> court meters
    method: str
    conf: float
    spec: CourtSpec = field(default_factory=CourtSpec)
    image_size: tuple[int, int] | None = None  # (w, h)
    correspondences: dict[str, tuple[float, float]] = field(default_factory=dict)  # landmark -> image px
    checks: dict = field(default_factory=dict)  # cross-model checks (fusion.validate_court), e.g. rim agreement

    @property
    def H_inv(self) -> np.ndarray:
        return np.linalg.inv(self.H)

    def image_to_court(self, pts) -> np.ndarray:
        pts = np.asarray(pts, float).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, self.H).reshape(-1, 2)

    def court_to_image(self, pts) -> np.ndarray:
        pts = np.asarray(pts, float).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, self.H_inv).reshape(-1, 2)

    def on_court(self, img_pt, margin: float = 1.0) -> bool:
        x, y = self.image_to_court([img_pt])[0]
        return abs(x) <= self.spec.length / 2 + margin and abs(y) <= self.spec.width / 2 + margin

    def reprojection_error(self) -> float:
        """Mean error in meters of the landmark correspondences under H (lower = better fit)."""
        if not self.correspondences:
            return float("nan")
        lm = template.landmarks(self.spec)
        names = [n for n in self.correspondences if n in lm]
        img = np.array([self.correspondences[n] for n in names])
        court = np.array([lm[n] for n in names])
        return float(np.linalg.norm(self.image_to_court(img) - court, axis=1).mean())

    def to_dict(self) -> dict:
        return {
            "H": self.H.tolist(),
            "method": self.method,
            "conf": self.conf,
            "spec": self.spec.__dict__,
            "image_size": self.image_size,
            "correspondences": self.correspondences,
            "checks": self.checks,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "CourtCalib":
        d = json.loads(Path(path).read_text())
        return cls(
            H=np.asarray(d["H"], float),
            method=d["method"],
            conf=d["conf"],
            spec=CourtSpec(**d["spec"]),
            image_size=tuple(d["image_size"]) if d.get("image_size") else None,
            correspondences={k: tuple(v) for k, v in d.get("correspondences", {}).items()},
            checks=d.get("checks", {}),
        )


def homography_from_landmarks(
    pairs: dict[str, tuple[float, float]], spec: CourtSpec, method: str, ransac_px: float = 0.3
) -> CourtCalib:
    """Fit image->court homography from {landmark_name: (u, v)} correspondences (>= 4)."""
    lm = template.landmarks(spec)
    unknown = [n for n in pairs if n not in lm]
    if unknown:
        raise ValueError(f"unknown landmarks {unknown}; valid: {sorted(lm)}")
    if len(pairs) < 4:
        raise CourtNotFound(f"need >= 4 landmarks, got {len(pairs)}")
    pairs = {n: (float(u), float(v)) for n, (u, v) in pairs.items()}
    names = list(pairs)
    img = np.array([pairs[n] for n in names], float)
    court = np.array([lm[n] for n in names], float)
    if len(pairs) == 4:
        H, _ = cv2.findHomography(img, court, 0)
        inl = np.ones(4, bool)
    else:
        H, mask = cv2.findHomography(img, court, cv2.RANSAC, ransac_px)
        inl = mask.ravel().astype(bool) if mask is not None else np.zeros(len(names), bool)
    if H is None:
        raise CourtNotFound("degenerate landmark configuration (collinear points?)")
    calib = CourtCalib(H, method, float(inl.mean()), spec, correspondences={n: pairs[n] for n, k in zip(names, inl) if k})
    err = calib.reprojection_error()
    calib.conf = float(inl.mean() * np.exp(-err))  # 1.0 for a perfect fit, decays with meters of error
    return calib


def canonicalize(calib: CourtCalib, anchor_img_pt) -> CourtCalib:
    """A court is symmetric under 180-degree rotation, so line-based methods can't tell which basket
    they see. Rotate the solution so `anchor_img_pt` (the detected rim, or the image center) lands on
    the +x half. Stats are unaffected; it keeps shot charts consistent. Manual calibrations are named
    explicitly by the user and are left alone."""
    if calib.correspondences and calib.method.startswith("manual"):
        return calib
    x, _ = calib.image_to_court([anchor_img_pt])[0]
    if x < 0:
        calib.H = np.diag([-1.0, -1.0, 1.0]) @ calib.H
    return calib


class CourtEstimator(ABC):
    name = "base"

    def __init__(self, spec: CourtSpec):
        self.spec = spec

    @abstractmethod
    def estimate(self, frame: np.ndarray) -> CourtCalib:
        """Calibrate from a single frame. Raise CourtNotFound if impossible."""

    def estimate_many(self, frames: list[np.ndarray]) -> CourtCalib:
        """Fixed camera: calibrate several frames and keep the most confident result."""
        best, errors = None, []
        for f in frames:
            try:
                c = self.estimate(f)
            except CourtNotFound as e:
                errors.append(str(e))
                continue
            if best is None or c.conf > best.conf:
                best = c
        if best is None:
            raise CourtNotFound(f"{self.name}: no frame calibrated ({errors[:3]})")
        return best
