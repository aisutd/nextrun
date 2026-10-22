"""Method B — classical line-based court registration (no training data needed).

1. Extract painted-line pixels (white top-hat on lightness, optionally masking out players).
2. Hough -> merge segments into infinite lines -> split into two direction families.
3. Hypothesise: 2 lines from each family form a quadrilateral that must be the image of a
   rectangle formed by 2 court x-lines (baseline / free-throw line / half-court line) and 2 court
   y-lines (sideline / corner-three line / paint side). Every pairing yields a homography.
4. Score each hypothesis by how well the projected template lines land on detected line pixels
   (chamfer on a distance transform), keep the best, then refine all 8 DOF with Powell.

Also usable as a *refiner* for a rough calibration from the manual or keypoint methods:
`LineCourtEstimator(spec).refine(frame, calib)`."""
from __future__ import annotations

import itertools

import cv2
import numpy as np
from scipy.optimize import minimize

from ..config import CourtSpec, FusionConfig
from . import template
from .base import CourtCalib, CourtEstimator, CourtNotFound


def line_mask(frame: np.ndarray, ignore_boxes=None, tophat_px: int | None = None) -> np.ndarray:
    """Binary mask of thin bright structures (painted lines)."""
    h, w = frame.shape[:2]
    k = tophat_px or max(9, int(round(w / 100)) | 1)
    L = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)[:, :, 0]
    th = cv2.morphologyEx(L, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    _, m = cv2.threshold(th, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    for x1, y1, x2, y2 in ignore_boxes or []:
        m[max(0, int(y1)) : int(y2), max(0, int(x1)) : int(x2)] = 0
    return m


MIN_SPREAD = 0.01  # (std_u / w) * (std_v / h) of visible template points for a real (non-collapsed) court


def _spread_factor(u, v, valid, w, h) -> np.ndarray:
    """(B,) in [0, 1]: penalize solutions that shrink the court onto a few bright pixels. A degenerate
    homography can pile every template point onto one painted line and look perfectly aligned."""
    n = np.maximum(valid.sum(1), 1)
    uu, vv = np.where(valid, np.nan_to_num(u), 0.0), np.where(valid, np.nan_to_num(v), 0.0)
    su = np.sqrt(np.maximum((uu**2).sum(1) / n - (uu.sum(1) / n) ** 2, 0)) / w
    sv = np.sqrt(np.maximum((vv**2).sum(1) / n - (vv.sum(1) / n) ** 2, 0)) / h
    return np.minimum(1.0, su * sv / MIN_SPREAD)


def detect_lines(mask: np.ndarray, max_lines: int = 12) -> list[np.ndarray]:
    """Infinite lines as homogeneous (a, b, c) with a^2+b^2=1, strongest first."""
    h, w = mask.shape
    segs = cv2.HoughLinesP(mask, 1, np.pi / 360, threshold=60, minLineLength=w // 20, maxLineGap=w // 80)
    if segs is None:
        return []
    lines: list[tuple[np.ndarray, float]] = []
    for x1, y1, x2, y2 in segs.reshape(-1, 4).astype(float):  # (N,1,4) in OpenCV 4, (N,4) in 5
        l = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
        l /= np.hypot(l[0], l[1])
        if l[2] > 0:
            l = -l
        ln = float(np.hypot(x2 - x1, y2 - y1))
        for i, (m, tot) in enumerate(lines):  # merge near-duplicates (same angle & offset)
            if abs(np.dot(m[:2], l[:2])) > np.cos(np.deg2rad(2.0)) and abs(abs(m[2]) - abs(l[2])) < 0.01 * w:
                s = np.sign(np.dot(m[:2], l[:2]))
                merged = (m * tot + s * l * ln) / (tot + ln)
                merged /= np.hypot(merged[0], merged[1])
                lines[i] = (merged, tot + ln)
                break
        else:
            lines.append((l, ln))
    lines.sort(key=lambda x: -x[1])
    return [l for l, _ in lines[:max_lines]]


def split_families(lines: list[np.ndarray]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Two direction families by k-means on doubled angle (direction is sign-agnostic)."""
    if len(lines) < 4:
        return [], []
    ang = np.array([np.arctan2(l[1], l[0]) for l in lines])
    feats = np.stack([np.cos(2 * ang), np.sin(2 * ang)], 1).astype(np.float32)
    _, lab, _ = cv2.kmeans(feats, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-3), 5, cv2.KMEANS_PP_CENTERS)
    lab = lab.ravel()
    return [l for l, k in zip(lines, lab) if k == 0], [l for l, k in zip(lines, lab) if k == 1]


def _sort_family(fam: list[np.ndarray], center: np.ndarray) -> list[np.ndarray]:
    n = np.mean([l[:2] * np.sign(np.dot(l[:2], fam[0][:2])) for l in fam], axis=0)
    d = np.array([-n[1], n[0]])  # probe direction across the family
    probe = np.cross([*center, 1.0], [*(center + d), 1.0])
    keys = []
    for l in fam:
        p = np.cross(l, probe)
        keys.append(np.dot(p[:2] / p[2] - center, d) if abs(p[2]) > 1e-9 else 1e9)
    return [fam[i] for i in np.argsort(keys)]


def _intersect(l1, l2):
    p = np.cross(l1, l2)
    return None if abs(p[2]) < 1e-9 else p[:2] / p[2]


class LineCourtEstimator(CourtEstimator):
    name = "lines"

    def __init__(self, spec: CourtSpec, per_family: int = 5, tau_px: float = 8.0):
        super().__init__(spec)
        self.per_family = per_family
        self.tau = tau_px
        self.tpl_pts = template.sample_line_points(spec, step=0.2)
        L2, W2 = spec.length / 2, spec.width / 2
        ftx = L2 - spec.ft_line_from_baseline
        yc = W2 - spec.corner_three_offset
        pw2 = spec.paint_width / 2
        self.x_lines = sorted({-L2, -ftx, 0.0, ftx, L2})
        self.y_lines = sorted({-W2, -yc, -pw2, pw2, yc, W2})
        self.ignore_boxes = None
        self.rims = None  # list[RimObs]: constrain the search (floor below rims, rim above its hoop)

    # ---- scoring ----------------------------------------------------------------------------
    def _score_batch(self, Hc2i: np.ndarray, dt: np.ndarray) -> np.ndarray:
        h, w = dt.shape
        P = np.hstack([self.tpl_pts, np.ones((len(self.tpl_pts), 1))])
        q = np.einsum("bij,nj->bni", Hc2i, P)
        z = q[..., 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u, v = q[..., 0] / z, q[..., 1] / z
        valid = (z > 0) & (u >= 0) & (u < w - 1) & (v >= 0) & (v < h - 1)
        ui = np.clip(np.nan_to_num(u), 0, w - 1).astype(int)
        vi = np.clip(np.nan_to_num(v), 0, h - 1).astype(int)
        d = np.minimum(dt[vi, ui], self.tau)
        good = (1 - d / self.tau) * valid
        bad = (d >= self.tau) & valid
        return (good.sum(1) - 0.5 * bad.sum(1)) * _spread_factor(u, v, valid, w, h)

    def _cost(self, params: np.ndarray, dt: np.ndarray) -> float:
        H = np.append(params, 1.0).reshape(3, 3)
        return -float(self._score_batch(H[None], dt)[0])

    # ---- hypotheses -------------------------------------------------------------------------
    def _hypotheses(self, fa, fb, w, h):
        center = np.array([w / 2, h / 2])
        fa = _sort_family(fa[: self.per_family], center)
        fb = _sort_family(fb[: self.per_family], center)
        tx = list(itertools.combinations(self.x_lines, 2))
        ty = list(itertools.combinations(self.y_lines, 2))
        out = []
        for a1, a2 in itertools.combinations(range(len(fa)), 2):
            for b1, b2 in itertools.combinations(range(len(fb)), 2):
                img = [_intersect(fa[a], fb[b]) for a in (a1, a2) for b in (b1, b2)]
                if any(p is None or np.abs(p).max() > 4 * max(w, h) for p in img):
                    continue
                img = np.float32(img)
                for swap in (False, True):
                    for (x1, x2), (y1, y2) in itertools.product(tx, ty):
                        for rx, ry in itertools.product((False, True), repeat=2):
                            xs = (x2, x1) if rx else (x1, x2)
                            ys = (y2, y1) if ry else (y1, y2)
                            if swap:  # family A <-> court y-lines
                                court = [(xs[j], ys[i]) for i in range(2) for j in range(2)]
                            else:
                                court = [(xs[i], ys[j]) for i in range(2) for j in range(2)]
                            out.append((np.float32(court), img))
        return out

    def estimate(self, frame: np.ndarray, init: CourtCalib | None = None) -> CourtCalib:
        h, w = frame.shape[:2]
        mask = line_mask(frame, self.ignore_boxes)
        if self.rims:  # the floor is below the rims: drop sky, walls, building edges
            mask[: int(min(r.center[1] for r in self.rims)), :] = 0
        dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 3)
        if init is not None:
            cands = [init.H_inv]
        else:
            fa, fb = split_families(detect_lines(mask))
            if len(fa) < 2 or len(fb) < 2:
                raise CourtNotFound("lines: fewer than 2 lines in each direction")
            Hs = []
            for court, img in self._hypotheses(fa, fb, w, h):
                H = cv2.getPerspectiveTransform(court, img)
                if H is not None and np.isfinite(H).all():
                    Hs.append(H / H[2, 2])
            if not Hs:
                raise CourtNotFound("lines: no valid hypotheses")
            Hs = np.array(Hs)
            scores = np.concatenate([self._score_batch(Hs[i : i + 512], dt) for i in range(0, len(Hs), 512)])
            top = list(Hs[np.argsort(-scores)[:40]])
            agreeing = [H for H in top if self._rims_agree(H)]
            cands = (agreeing or top)[:5]
        best_H, best_cost, best_agrees = None, np.inf, False
        for H0 in cands:
            H0 = H0 / H0[2, 2]
            res = minimize(self._cost, H0.ravel()[:8], args=(dt,), method="Powell", options={"maxiter": 3000, "xtol": 1e-4})
            H = np.append(res.x, 1.0).reshape(3, 3)
            agrees = self._rims_agree(H)
            if (agrees, -res.fun) > (best_agrees, -best_cost):  # a fit the rims agree with beats a better-aligned one
                best_H, best_cost, best_agrees = H, res.fun, agrees
        if best_H is None or -best_cost <= 0:
            raise CourtNotFound("lines: no hypothesis aligned with the painted lines")
        conf = self._confidence(best_H, dt)
        Hi2c = np.linalg.inv(best_H)
        return CourtCalib(Hi2c / Hi2c[2, 2], self.name, conf, self.spec, (w, h))

    def _rims_agree(self, Hc2i: np.ndarray) -> bool:
        """Detected rims sit above their hoop's floor point under this court->image homography."""
        if not self.rims:
            return False
        from .. import fusion

        try:
            Hi2c = np.linalg.inv(Hc2i)
        except np.linalg.LinAlgError:
            return False
        calib = CourtCalib(Hi2c / Hi2c[2, 2], self.name, 1.0, self.spec)
        return any(fusion.check_rim(calib, r, FusionConfig()).ok for r in self.rims)

    def _confidence(self, Hc2i: np.ndarray, dt: np.ndarray) -> float:
        """Fraction of visible projected template points within 3 px of a detected line pixel."""
        h, w = dt.shape
        P = np.hstack([self.tpl_pts, np.ones((len(self.tpl_pts), 1))])
        q = P @ Hc2i.T
        z = q[:, 2]
        u, v = q[:, 0] / z, q[:, 1] / z
        valid = (z > 0) & (u >= 0) & (u < w - 1) & (v >= 0) & (v < h - 1)
        if valid.sum() < 30:
            return 0.0
        d = dt[v[valid].astype(int), u[valid].astype(int)]
        return float((d < 3).mean() * _spread_factor(u[None], v[None], valid[None], w, h)[0])

    def refine(self, frame: np.ndarray, calib: CourtCalib) -> CourtCalib:
        """Polish an existing calibration (e.g. from 4 rough manual clicks) against painted lines."""
        dt = cv2.distanceTransform(255 - line_mask(frame, self.ignore_boxes), cv2.DIST_L2, 3)
        before = self._confidence(calib.H_inv / calib.H_inv[2, 2], dt)
        try:
            out = self.estimate(frame, init=calib)
        except CourtNotFound:
            return calib
        if out.conf <= before:
            return calib
        out.method = f"{calib.method}+lines"
        out.correspondences = calib.correspondences
        return out
