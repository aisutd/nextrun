"""Ball free-flight segments (between release and the next possession) and their arcs.

In image space a thrown ball is well approximated by x(t) linear, y(t) quadratic (gravity), so each
flight gets a least-squares fit; the fit drives arc overlays and arc stats (apex, airtime)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..schema import FrameState


@dataclass
class Arc:
    t0: float
    coef_x: list[float]  # x(t) = a*dt + b      (dt = t - t0)
    coef_y: list[float]  # y(t) = a*dt^2 + b*dt + c
    rmse_px: float
    apex_xy: tuple[float, float]
    apex_t: float

    def eval(self, t) -> np.ndarray:
        dt = np.asarray(t, float) - self.t0
        return np.stack([np.polyval(self.coef_x, dt), np.polyval(self.coef_y, dt)], -1)


@dataclass
class Flight:
    start: int  # frames-list index of first free frame (after release)
    end: int  # frames-list index of last free frame
    points: list[tuple[int, float, float, float]] = field(default_factory=list)  # (frame idx, t, x, y)
    arc: Arc | None = None

    @property
    def duration(self) -> float:
        return self.points[-1][1] - self.points[0][1] if len(self.points) > 1 else 0.0

    def to_dict(self) -> dict:
        d = {"start": self.start, "end": self.end, "points": self.points, "duration_s": self.duration}
        if self.arc is not None:
            d["arc"] = {
                "t0": self.arc.t0,
                "coef_x": self.arc.coef_x,
                "coef_y": self.arc.coef_y,
                "rmse_px": self.arc.rmse_px,
                "apex_xy": self.arc.apex_xy,
                "apex_t": self.arc.apex_t,
            }
        return d


def build_flight(frames: list[FrameState], start: int, end: int) -> Flight:
    fl = Flight(start, end)
    for f in frames[start : end + 1]:
        if f.ball is not None:
            fl.points.append((f.idx, f.t, f.ball.xy[0], f.ball.xy[1]))
    fl.arc = fit_arc(fl.points)
    return fl


def fit_arc(points) -> Arc | None:
    real = [p for p in points]
    if len(real) < 4:
        return None
    P = np.asarray(real, float)
    t0 = P[0, 1]
    dt = P[:, 1] - t0
    if dt[-1] - dt[0] <= 0:
        return None
    cx = np.polyfit(dt, P[:, 2], 1)
    cy = np.polyfit(dt, P[:, 3], 2)
    res = np.hypot(np.polyval(cx, dt) - P[:, 2], np.polyval(cy, dt) - P[:, 3])
    if cy[0] > 0:  # opening upward in image coords = ball decelerates while rising (normal throw)
        ta = float(np.clip(-cy[1] / (2 * cy[0]), dt[0], dt[-1]))
    else:
        ta = float(dt[np.argmin(P[:, 3])])
    apex = (float(np.polyval(cx, ta)), float(np.polyval(cy, ta)))
    return Arc(float(t0), cx.tolist(), cy.tolist(), float(np.sqrt((res**2).mean())), apex, float(t0 + ta))
