"""NextRun: the three models as one unit.

    nr = NextRun()                          # loads pose+tracking, ball/rim and court models once
    calib = nr.calibrate(first_frames)      # court model, checked against the rim model
    f = nr.process(frame, idx, t)           # players + ball + rims, fused through the court geometry
    nr.describe(f)                          # JSON: court positions, 2PT/3PT zones, ball holder, baskets

Every frame runs the player tracker and the ball/rim detector; once a court calibration is known, the
fusion geometry (nextrun_cv/fusion.py) ties them together. The video pipeline (pipeline.detect) uses
`detect` per frame and applies the same fusion offline in `analyze`, so tags and thresholds can change
without re-running the models.
"""
from __future__ import annotations

import logging

import numpy as np

from . import fusion
from .config import Config
from .court.auto import calibrate_court
from .court.base import CourtCalib, CourtNotFound
from .schema import FrameState

log = logging.getLogger(__name__)


class NextRun:
    def __init__(self, cfg: Config | None = None, calib: CourtCalib | None = None):
        from .detect.ball_hoop import BallHoopDetector
        from .detect.players import PlayerTracker

        self.cfg = cfg or Config()
        self.players = PlayerTracker(self.cfg.models)
        self.ball_hoop = BallHoopDetector(self.cfg.models)
        self.calib = calib

    # --- raw model outputs ---------------------------------------------------------------------------
    def detect(self, img: np.ndarray, idx: int = 0, t: float = 0.0) -> FrameState:
        """Run the player tracker (state persists across calls) and the ball/rim detector on one frame."""
        players = self.players.update(img)
        balls, rims = self.ball_hoop.detect(img)
        ball = max(balls, key=lambda b: b.conf) if balls else None
        return FrameState(idx, t, players, ball, balls, rims)

    # --- court ---------------------------------------------------------------------------------------
    def calibrate(self, imgs: list[np.ndarray], frames: list[FrameState] | None = None, manual_points=None) -> CourtCalib:
        """Calibrate the (fixed) camera from a few frames. Rims and player boxes from `frames` (detected
        on the same images if not given) validate candidates and keep people out of the line search."""
        if frames is None:
            frames = [FrameState(i, 0.0, [], None, [], self.ball_hoop.detect(img)[1]) for i, img in enumerate(imgs)]
        rims = [f.rims for f in frames]
        all_rims = [r for rs in rims for r in rs]
        rim_xy = max(all_rims, key=lambda r: r.conf).center if all_rims else None
        ignore = [[p.bbox for p in f.players] for f in frames]
        self.calib = calibrate_court(imgs, self.cfg, manual_points, ignore, rim_xy, rims)
        return self.calib

    # --- all together --------------------------------------------------------------------------------
    def process(self, img: np.ndarray, idx: int = 0, t: float = 0.0) -> FrameState:
        """detect + fuse: players get court positions and off-court people are dropped (if the court is known)."""
        f = self.detect(img, idx, t)
        fusion.fuse([f], self.calib, self.cfg)
        return f

    def describe(self, f: FrameState) -> dict:
        return fusion.describe(f, self.calib, self.cfg)

    def reset(self) -> None:
        """Start over: new video or unrelated images (clears tracks and the court calibration)."""
        self.players.reset()
        self.calib = None

    def analyze_image(self, img: np.ndarray) -> dict:
        """One still image end to end: calibrate on it, run every model, return the fused scene."""
        self.reset()
        f = self.detect(img)
        try:
            self.calibrate([img], [f])
        except CourtNotFound as e:
            log.info("no court in image: %s", e)
            self.calib = None
        fusion.fuse([f], self.calib, self.cfg)
        return self.describe(f)
