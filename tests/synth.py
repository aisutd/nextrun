"""Synthetic game builder: scripted players + ball positions -> FrameStates, for testing events.

Image geometry (1280x720): one rim at x 900-940, y 200-215. Players stand with feet at y=600
(bbox height 180). `CALIB` maps image -> court so that a player's feet at u=920 are under the right
hoop and each pixel left of that is 2 cm farther away (u < 582 is beyond the FIBA 3PT arc)."""
from __future__ import annotations

import numpy as np

from nextrun_cv.config import CourtSpec
from nextrun_cv.court.base import CourtCalib
from nextrun_cv.identity.tagging import Identities
from nextrun_cv.schema import BallObs, FrameState, PlayerObs, RimObs

FPS = 30.0
RIM = RimObs((900.0, 200.0, 940.0, 215.0))
HAND_Y = 600 - 180 + 0.45 * 180  # fallback hand position used when no keypoints (=501)
SPEC = CourtSpec()
HOOP_X = SPEC.length / 2 - SPEC.hoop_from_baseline


def make_calib() -> CourtCalib:
    s = 0.02
    H = np.array([[s, 0, HOOP_X - 920 * s], [0, 0.05, -600 * 0.05], [0, 0, 1]], float)
    return CourtCalib(H, "synthetic", 1.0, SPEC, (1280, 720))


def player(tid: int, u: float) -> PlayerObs:
    return PlayerObs(tid, (u - 30, 420.0, u + 30, 600.0), 0.9, None)


def arc(p0, p1, n: int, apex_y: float) -> list[tuple[float, float]]:
    """n points of a parabola from p0 to p1 peaking at apex_y (image y, smaller = higher)."""
    out = []
    for k in range(1, n + 1):
        w = k / n
        x = p0[0] + (p1[0] - p0[0]) * w
        base = p0[1] + (p1[1] - p0[1]) * w
        lift = 4 * w * (1 - w) * (min(p0[1], p1[1]) - apex_y)
        out.append((x, base - lift))
    return out


class Game:
    def __init__(self, positions: dict[int, float]):
        self.positions = dict(positions)  # track_id -> u
        self.frames: list[FrameState] = []

    def _frame(self, ball_xy):
        i = len(self.frames)
        f = FrameState(i, i / FPS, [player(t, u) for t, u in self.positions.items()], None, [], [RIM])
        if ball_xy is not None:
            f.ball = BallObs(ball_xy, 6.0, 0.9)
            f.ball_candidates = [f.ball]
        self.frames.append(f)
        return f

    def hold(self, tid: int, n: int, dribble_every: int = 0) -> "Game":
        u = self.positions[tid]
        for k in range(n):
            y = HAND_Y
            if dribble_every:
                ph = (k % dribble_every) / dribble_every
                y = HAND_Y + (590 - HAND_Y) * (1 - abs(2 * ph - 1))  # down to the floor and back
            self._frame((u, y))
        return self

    def fly(self, pts) -> "Game":
        for p in pts:
            self._frame(p)
        return self

    def move(self, tid: int, u: float) -> "Game":
        self.positions[tid] = u
        return self


def shot_path(u_from: float, made: bool) -> list[tuple[float, float]]:
    rim_c = ((RIM.bbox[0] + RIM.bbox[2]) / 2, RIM.bbox[1] - 15)
    up = arc((u_from, HAND_Y - 20), rim_c, 22, apex_y=90)
    if made:
        down = [(rim_c[0], rim_c[1] + 12 * k) for k in range(1, 26)]  # through the net to the floor
    else:
        down = arc(rim_c, (1120, HAND_Y), 14, apex_y=100)  # rattles out to the right
    return up + down


def ids_red_blue() -> Identities:
    return Identities({1: "A1", 2: "A2", 3: "B1"}, {"A1": "Red", "A2": "Red", "B1": "Blue"})
