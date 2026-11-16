"""Court-type detection: painted lines of a synthetic gym are rendered for a known court type and camera; the
keypoints the court model would report are simulated, and detect_court_type must name the type that was drawn."""
import cv2
import numpy as np
import pytest

from nextrun_cv.config import Config, CourtSpec
from nextrun_cv.court import template
from nextrun_cv.court.base import CourtEstimator
from nextrun_cv.court.keypoints import KeypointCourtEstimator, keypoints_for_court, load_keypoint_config
from nextrun_cv.court.auto import detect_court_type

KP_CONFIG = "weights/court/court_keypoints.json"
W, H = 1280, 720


def _camera(spec: CourtSpec) -> np.ndarray:
    """court meters -> image px for a camera framing the whole court from one sideline."""
    L2, W2 = spec.length / 2, spec.width / 2
    court = np.float32([[-L2, -W2], [L2, -W2], [L2, W2], [-L2, W2]])
    img = np.float32([[260, 200], [1020, 200], [1220, 640], [60, 640]])
    return cv2.getPerspectiveTransform(court, img)


def _render(spec: CourtSpec, Hc2i: np.ndarray) -> np.ndarray:
    frame = np.full((H, W, 3), (70, 120, 170), np.uint8)  # wood floor
    for pl in template.polylines(spec):
        uv = cv2.perspectiveTransform(pl.reshape(-1, 1, 2).astype(np.float32), Hc2i).reshape(-1, 2)
        cv2.polylines(frame, [uv.astype(np.int32)], False, (245, 245, 245), 4, cv2.LINE_AA)
    return frame


def _estimator(requested: str, true_spec: CourtSpec, Hc2i: np.ndarray, noise_px: float, seed: int = 0):
    spec = CourtSpec.preset(requested)
    est = KeypointCourtEstimator.__new__(KeypointCourtEstimator)
    CourtEstimator.__init__(est, spec)
    est.model, est.device, est.kp_conf = None, None, 0.5
    est.kp = load_keypoint_config(KP_CONFIG)
    est._kp_measured = est.kp["court_m"]
    est.kp["court_m"] = keypoints_for_court(est.kp, spec)
    # what the court model reports: every keypoint of the TRUE court, projected through the camera, with jitter
    truth = keypoints_for_court({**est.kp, "court_m": est._kp_measured}, true_spec)
    rng = np.random.default_rng(seed)
    ids = [i for i in est.kp["use_ids"] if i in truth]
    uv = cv2.perspectiveTransform(np.float32([truth[i] for i in ids]).reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    pairs = {i: tuple(p + rng.normal(0, noise_px, 2)) for i, p in zip(ids, uv)}
    est.detect_all = lambda frames: [pairs for _ in frames]
    return est


@pytest.mark.parametrize("truth,asked", [("nba", "highschool"), ("highschool", "nba"), ("ncaa", "highschool"), ("fiba", "nba")])
def test_detects_the_court_type_in_the_video(truth, asked):
    spec = CourtSpec.preset(truth)
    Hc2i = _camera(spec)
    frames = [_render(spec, Hc2i)] * 3
    cfg = Config(court=CourtSpec.preset(asked))
    name, scores = detect_court_type(frames, cfg, estimator=_estimator(asked, spec, Hc2i, noise_px=1.5))
    assert name == truth, scores


def test_keeps_the_requested_type_when_it_is_right():
    spec = CourtSpec.preset("highschool")
    Hc2i = _camera(spec)
    cfg = Config(court=spec)
    name, scores = detect_court_type([_render(spec, Hc2i)] * 3, cfg, estimator=_estimator("highschool", spec, Hc2i, 1.5))
    assert name == "highschool" and scores["highschool"] >= max(scores.values()) - 0.05


def _mean_err_px(spec, H_a, H_b) -> float:
    pts = template.sample_line_points(spec, step=1.0).astype(np.float32).reshape(-1, 1, 2)
    a = cv2.perspectiveTransform(pts, H_a).reshape(-1, 2)
    b = cv2.perspectiveTransform(pts, H_b).reshape(-1, 2)
    return float(np.linalg.norm(a - b, axis=1).mean())


def test_line_polish_pulls_a_slightly_off_court_onto_the_painted_lines_but_not_far():
    from nextrun_cv.court.base import CourtCalib
    from nextrun_cv.court.lines import LineCourtEstimator, line_dt

    spec = CourtSpec.preset("nba")
    Hc2i = _camera(spec)
    dt = line_dt([_render(spec, Hc2i)])
    shift = np.array([[1, 0, 7], [0, 1, -5], [0, 0, 1]], float)  # lines drawn ~9 px off
    off = CourtCalib(np.linalg.inv(shift @ Hc2i), "keypoints", 0.5, spec, (W, H))
    est = LineCourtEstimator(spec)
    before = _mean_err_px(spec, np.linalg.inv(off.H), Hc2i)
    fixed = est.refine(None, off, dt=dt, max_shift=0.03)
    after = _mean_err_px(spec, np.linalg.inv(fixed.H), Hc2i)
    assert before > 6 and after < 3.0 and after < before / 2, (before, after)
    # a "polish" that would move the lines by more than max_shift is refused
    assert est.refine(None, off, dt=dt, max_shift=0.001).H is off.H
