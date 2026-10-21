"""Court calibration entry point: picks a method or runs the fallback chain
keypoints -> lines -> manual, refining with line alignment where possible. Each candidate is checked
against the rim detector (fusion.validate_court) before it is accepted."""
from __future__ import annotations

import copy
import logging

import numpy as np

from .. import fusion
from ..config import Config
from ..schema import RimObs
from .base import CourtCalib, CourtNotFound, canonicalize
from .lines import LineCourtEstimator
from .manual import ManualCourtEstimator

log = logging.getLogger(__name__)

def calibrate_court(
    frames: list[np.ndarray],
    cfg: Config,
    manual_points: dict | str | None = None,
    ignore_boxes_per_frame: list[list] | None = None,
    rim_xy: tuple[float, float] | None = None,
    rims_per_frame: list[list[RimObs]] | None = None,
) -> CourtCalib:
    """frames: a handful of frames from the (fixed) camera. rims_per_frame: rim detections to validate
    candidates against. Returns the best calibration found."""
    min_conf = cfg.fusion.min_court_conf
    h, w = frames[0].shape[:2]
    anchor = rim_xy if rim_xy is not None else (w / 2, h / 2)
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
        if not rims_per_frame:
            return calib  # the court model's own fit (its reported accuracy is without refinement)
        # line refinement can drag a good fit onto the wrong lines: keep whichever the rims agree with more
        refined = LineCourtEstimator(spec).refine(frames[0], copy.deepcopy(calib))
        cands = [canonicalize(c, anchor) for c in (calib, refined)]
        return max(cands, key=lambda c: fusion.validate_court(copy.deepcopy(c), rims_per_frame, cfg.fusion).conf)

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
        calib = canonicalize(calib, anchor)
        if rims_per_frame:
            calib = fusion.validate_court(calib, rims_per_frame, cfg.fusion)
        log.info("court calibration via %s: conf=%.2f checks=%s", calib.method, calib.conf, calib.checks)
        if best is None or calib.conf > best.conf:
            best = calib
        if calib.conf >= min_conf:
            break
    if best is None:
        raise CourtNotFound("court calibration failed: " + " | ".join(tried))
    if best.conf < min_conf:
        log.warning("low-confidence court calibration (%s, conf=%.2f); consider manual points", best.method, best.conf)
    return best
