"""Court calibration entry point: picks a method or runs the fallback chain
keypoints -> lines -> manual, refining with line alignment where possible."""
from __future__ import annotations

import logging

import numpy as np

from ..config import Config
from .base import CourtCalib, CourtNotFound, canonicalize
from .lines import LineCourtEstimator
from .manual import ManualCourtEstimator

log = logging.getLogger(__name__)

MIN_CONF = 0.35


def calibrate_court(
    frames: list[np.ndarray],
    cfg: Config,
    manual_points: dict | str | None = None,
    ignore_boxes_per_frame: list[list] | None = None,
    rim_xy: tuple[float, float] | None = None,
) -> CourtCalib:
    """frames: a handful of frames from the (fixed) camera. Returns the best calibration found."""
    method = cfg.court_method
    spec = cfg.court
    tried: list[str] = []

    def manual():
        if manual_points is None:
            raise CourtNotFound("manual: no points given (pass --court-points or click them in the notebook)")
        calib = ManualCourtEstimator(spec, manual_points).estimate(frames[0])
        return LineCourtEstimator(spec).refine(frames[0], calib)

    def keypoints():
        from .keypoints import KeypointCourtEstimator

        est = KeypointCourtEstimator(
            spec, cfg.models.court_keypoint_weights, cfg.models.court_keypoint_config, cfg.models.device
        )
        calib = est.estimate_many(frames)
        return LineCourtEstimator(spec).refine(frames[0], calib)

    def lines():
        est = LineCourtEstimator(spec)
        best = None
        for i, f in enumerate(frames[:3]):  # line search is the slow one; a few frames suffice
            est.ignore_boxes = ignore_boxes_per_frame[i] if ignore_boxes_per_frame else None
            try:
                c = est.estimate(f)
            except CourtNotFound as e:
                tried.append(str(e))
                continue
            if best is None or c.conf > best.conf:
                best = c
        if best is None:
            raise CourtNotFound("lines: failed on all frames")
        return best

    # user-provided points are the most trustworthy signal, so they go first when present
    auto_chain = [manual, keypoints, lines] if manual_points is not None else [keypoints, lines]
    chain = {"manual": [manual], "keypoints": [keypoints], "lines": [lines], "auto": auto_chain}[method]
    best: CourtCalib | None = None
    for fn in chain:
        try:
            calib = fn()
        except CourtNotFound as e:
            tried.append(str(e))
            continue
        log.info("court calibration via %s: conf=%.2f", calib.method, calib.conf)
        if best is None or calib.conf > best.conf:
            best = calib
        if calib.conf >= MIN_CONF:
            break
    if best is None:
        raise CourtNotFound("court calibration failed: " + " | ".join(tried))
    h, w = frames[0].shape[:2]
    best = canonicalize(best, rim_xy if rim_xy is not None else (w / 2, h / 2))
    if best.conf < MIN_CONF:
        log.warning("low-confidence court calibration (%s, conf=%.2f); consider manual points", best.method, best.conf)
    return best
