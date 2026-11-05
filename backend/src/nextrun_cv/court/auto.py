"""Court calibration entry point: picks a method or runs the fallback chain
keypoints -> lines -> manual, refining with line alignment where possible. Each candidate is checked
against the rim detector (fusion.validate_court) before it is accepted."""
from __future__ import annotations

import copy
import logging

import numpy as np

from .. import fusion
from ..config import Config, CourtSpec
from ..schema import RimObs
from .base import CourtCalib, CourtNotFound, canonicalize
from .lines import LineCourtEstimator, line_dt
from .manual import ManualCourtEstimator

log = logging.getLogger(__name__)

COURT_TYPES = ("highschool", "fiba", "nba", "ncaa")
MAX_SHIFT = 0.03  # a line refinement may move the court lines by at most this share of the frame width


def detect_court_type(
    frames: list[np.ndarray],
    cfg: Config,
    ignore_boxes_per_frame: list[list] | None = None,
    estimator=None,
) -> tuple[str, dict[str, float]]:
    """Which court type is in the video: the court model's keypoints are read against every type's geometry, each
    fit is polished onto the painted lines, and the type whose lines land on the most line pixels wins (players are
    masked out, and the lines of several frames are combined). Returns (type, {type: line-fit score 0..1}).
    The requested type (cfg.court) is kept unless another one leads by cfg.court_type_margin."""
    from .keypoints import KeypointCourtEstimator

    requested = cfg.court.name
    est = estimator or KeypointCourtEstimator(
        cfg.court, cfg.models.court_keypoint_weights, cfg.models.court_keypoint_config, cfg.models.device
    )
    pairs = est.detect_all(frames)
    if not any(p is not None and len(p) >= 4 for p in pairs):
        raise CourtNotFound("court type: the court model found no court in the frames")
    dt = line_dt(frames, ignore_boxes_per_frame)
    scores: dict[str, float] = {}
    for name in COURT_TYPES:
        spec = CourtSpec.preset(name)
        try:
            calib = est.with_spec(spec).estimate_many(frames, pairs)
        except CourtNotFound:
            continue
        lines = LineCourtEstimator(spec)
        calib = lines.refine(None, calib, dt=dt, max_shift=MAX_SHIFT)
        scores[name] = round(lines._confidence(calib.H_inv / calib.H_inv[2, 2], dt), 4)
    if not scores:
        raise CourtNotFound("court type: no court type could be fitted")
    best = max(scores, key=scores.get)
    keep = requested if requested in scores else None
    if keep is None or (best != keep and scores[best] >= scores[keep] + cfg.court_type_margin and scores[best] >= cfg.court_type_min_fit):
        chosen = best
    else:
        chosen = keep
    log.info("court type: %s (asked for %s) line fit %s", chosen, requested, scores)
    return chosen, scores

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
            raise CourtNotFound("manual: no points given (pass --court-points or --venue)")
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
        # Snap the keypoint fit onto the painted lines (lines of several frames combined, players masked out), but only
        # by a bounded amount: a polish that drags the court onto other lines is rejected. Whichever the rims agree
        # with more wins; on a tie the better-aligned one does.
        lines_est = LineCourtEstimator(spec)
        dt = line_dt(frames, ignore_boxes_per_frame)
        refined = lines_est.refine(None, copy.deepcopy(calib), dt=dt, max_shift=MAX_SHIFT)
        cands = [canonicalize(c, anchor) for c in (calib, refined)]

        def key(c):
            return (
                round(fusion.validate_court(copy.deepcopy(c), rims_per_frame, cfg.fusion).conf, 2),
                lines_est._confidence(c.H_inv / c.H_inv[2, 2], dt),
            )

        return max(cands, key=key)

    def lines():
        est = LineCourtEstimator(spec)
        best = None
        for i, f in enumerate(frames[:3]):  # line search is the slow one; a few frames suffice
            est.ignore_boxes = ignore_boxes_per_frame[i] if ignore_boxes_per_frame else None
            est.rims = rims_per_frame[i] if rims_per_frame and i < len(rims_per_frame) else None
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
