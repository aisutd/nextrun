import cv2
import numpy as np
import pytest

from nextrun_cv.config import Config, CourtSpec
from nextrun_cv.court import template
from nextrun_cv.court.auto import calibrate_court
from nextrun_cv.court.base import CourtCalib, homography_from_landmarks
from nextrun_cv.court.lines import LineCourtEstimator

SPEC = CourtSpec()


@pytest.mark.parametrize(
    "xy,three",
    [
        ((12.425 - 6.0, 0.0), False),  # top of key, inside arc
        ((12.425 - 7.0, 0.0), True),  # beyond arc
        ((13.5, 6.7), True),  # corner three (beyond corner line, < 6.75 m from hoop)
        ((13.5, 6.4), False),  # corner, inside line
        ((-12.425 + 7.0, 1.0), True),  # left basket
        ((12.425, 0.5), False),  # layup
    ],
)
def test_is_three(xy, three):
    assert template.is_three(xy, SPEC) is three


def test_presets_corner_line_meets_arc():
    for name in ("fiba", "nba", "ncaa", "highschool"):
        s = CourtSpec.preset(name)
        assert s.width / 2 - s.corner_three_offset <= s.three_pt_radius


def test_keypoint_flip_idx_is_involution():
    f = template.keypoint_flip_idx()
    assert [f[i] for i in f] == list(range(len(f)))


def _camera_H() -> np.ndarray:
    """A plausible court->image homography: elevated camera behind the left sideline looking at
    the right half court."""
    lm = template.landmarks(SPEC)
    names = ["R_base_top", "R_base_bot", "mid_top", "mid_bot"]
    img = np.float32([[1180, 300], [1250, 690], [80, 330], [10, 700]])
    return cv2.getPerspectiveTransform(np.float32([lm[n] for n in names]), img)


def test_manual_homography_roundtrip(tmp_path):
    Hc2i = _camera_H()
    lm = template.landmarks(SPEC)
    names = ["R_base_top", "R_base_bot", "R_paint_ft_top", "R_paint_ft_bot", "R_arc_top", "mid_top"]
    pts = cv2.perspectiveTransform(np.float32([lm[n] for n in names]).reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    calib = homography_from_landmarks({n: tuple(p) for n, p in zip(names, pts)}, SPEC, "manual")
    assert calib.reprojection_error() < 0.02
    assert calib.conf > 0.95
    back = calib.court_to_image(calib.image_to_court(pts))
    assert np.allclose(back, pts, atol=0.5)
    calib.save(tmp_path / "c.json")
    c2 = CourtCalib.load(tmp_path / "c.json")
    assert np.allclose(c2.H, calib.H)


def _render_court(Hc2i: np.ndarray, size=(1280, 720)) -> np.ndarray:
    rng = np.random.default_rng(0)
    img = np.full((size[1], size[0], 3), (70, 110, 160), np.uint8)
    img = cv2.add(img, rng.integers(0, 20, img.shape, dtype=np.uint8))
    for pl in template.polylines(SPEC):
        p = cv2.perspectiveTransform(pl.reshape(-1, 1, 2).astype(np.float64), Hc2i).reshape(-1, 2)
        cv2.polylines(img, [p.astype(np.int32)], False, (235, 235, 235), 4, cv2.LINE_AA)
    return img


def _court_error(calib: CourtCalib, Hc2i: np.ndarray) -> float:
    """Mean error (m) over the visible half court."""
    grid = np.array([(x, y) for x in np.linspace(1, 13, 7) for y in np.linspace(-7, 7, 7)], float)
    img = cv2.perspectiveTransform(grid.reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    return float(np.linalg.norm(calib.image_to_court(img) - grid, axis=1).mean())


def test_lines_refines_rough_manual_clicks():
    Hc2i = _camera_H()
    frame = _render_court(Hc2i)
    lm = template.landmarks(SPEC)
    names = ["R_base_top", "R_base_bot", "R_paint_ft_top", "R_paint_ft_bot", "mid_top", "mid_bot"]
    exact = cv2.perspectiveTransform(np.float32([lm[n] for n in names]).reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    noisy = exact + np.random.default_rng(1).normal(0, 6, exact.shape)  # sloppy clicks
    rough = homography_from_landmarks({n: tuple(p) for n, p in zip(names, noisy)}, SPEC, "manual")
    refined = LineCourtEstimator(SPEC).refine(frame, rough)
    assert _court_error(refined, Hc2i) <= _court_error(rough, Hc2i) + 1e-6
    assert _court_error(refined, Hc2i) < 0.3


@pytest.mark.slow
def test_lines_auto_from_scratch():
    Hc2i = _camera_H()
    frame = _render_court(Hc2i)
    cfg = Config()
    cfg.court_method = "lines"
    calib = calibrate_court([frame], cfg)
    assert calib.conf > 0.5
    assert _court_error(calib, Hc2i) < 0.5


def _mirror_estimator(spec):
    from nextrun_cv.court.keypoints import KeypointCourtEstimator

    est = object.__new__(KeypointCourtEstimator)  # skip weight loading
    est.spec, est.names, est.valid = spec, template.keypoint_order(), set(template.landmarks(spec))
    return est


def test_keypoint_estimator_fixes_left_right_swap():
    from nextrun_cv.court.keypoints import _mirror_name, orientation_sign

    Hc2i = _camera_H()
    lm = template.landmarks(SPEC)
    names = ["R_base_top", "R_base_bot", "R_paint_base_top", "R_paint_ft_top", "R_paint_ft_bot", "R_arc_top", "mid_top"]
    pts = cv2.perspectiveTransform(np.float32([lm[n] for n in names]).reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    est = _mirror_estimator(SPEC)
    frame = np.zeros((720, 1280, 3), np.uint8)
    for labels in (names, [_mirror_name(n) for n in names]):  # correct, and as if the model swapped halves
        est.detect = lambda f, labels=labels: {n: tuple(map(float, p)) for n, p in zip(labels, pts)}
        calib = est.estimate(frame)
        assert orientation_sign(calib.H, (640, 360)) > 0
        assert np.allclose(calib.image_to_court(pts[:1])[0], lm["R_base_top"], atol=0.05)


def test_prepare_court_dataset_cleans_and_densifies():
    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "train" / "prepare_court_dataset.py"
    spec_ = importlib.util.spec_from_file_location("prep", p)
    prep = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(prep)
    lm = template.landmarks(prep.SPEC)
    names = ["R_base_top", "R_base_bot", "mid_top", "mid_bot"]
    img = np.float32([[1700, 300], [1850, 1000], [100, 330], [20, 1050]])
    H = cv2.getPerspectiveTransform(np.float32([lm[n] for n in names]), img)
    kp = np.zeros((48, 3))
    src_idx = {v: k for k, v in prep.SRC_MAP.items()}
    labeled = ["R_base_top", "R_paint_base_top", "R_paint_base_bot", "R_paint_ft_top", "R_paint_ft_bot",
               "R_ft_center", "R_arc_top", "R_c3_arc_top", "mid_top", "center"]
    for n in labeled:
        u, v = cv2.perspectiveTransform(np.float32([[lm[n]]]), H)[0, 0]
        kp[src_idx[n]] = [u / 1920, v / 1080, 2]
    kp[src_idx["R_hash_top"]] = [0.1, 0.9, 2]  # mislabeled point
    out, info = prep.convert(kp, 1920, 1080)
    assert "R_hash_top" not in out or abs(out["R_hash_top"][1] - 0.9 * 1080) > 50  # outlier dropped/replaced
    assert info["inliers"] == len(labeled)
    assert info["added"] > 0 and "center_top" in out
    u, v = cv2.perspectiveTransform(np.float32([[lm["center_top"]]]), H)[0, 0]
    assert np.allclose(out["center_top"], (u, v), atol=1.0)
