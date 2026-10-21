import cv2
import numpy as np
import pytest

from nextrun_cv.config import REPO_ROOT, Config, CourtSpec
from nextrun_cv.court import template
from nextrun_cv.court.auto import calibrate_court
from nextrun_cv.court.base import CourtCalib, homography_from_landmarks
from nextrun_cv.court.keypoints import load_keypoint_config
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


@pytest.mark.parametrize(
    "xy,dist",
    [
        ((12.8 - 1.6 - 6.02 - 1.0, 0.0), 1.0),  # 1 m beyond the top of the arc
        ((12.8 - 1.0, 6.0), -0.02),  # behind the hoop line: straight corner line, just inside
        ((12.8 - 0.5, 7.0), 0.98),  # deep corner
    ],
)
def test_three_line_distance_highschool(xy, dist):
    hs = CourtSpec.preset("highschool")
    assert template.three_line_distance(xy, hs) == pytest.approx(dist, abs=0.01)
    assert template.is_three(xy, hs) is (dist >= 0)


def test_presets_corner_line_meets_arc():
    for name in ("fiba", "nba", "ncaa", "highschool"):
        s = CourtSpec.preset(name)
        assert s.width / 2 - s.corner_three_offset <= s.three_pt_radius


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
    cfg = Config(court=SPEC)
    cfg.court_method = "lines"
    calib = calibrate_court([frame], cfg)
    assert calib.conf > 0.5
    assert _court_error(calib, Hc2i) < 0.5


KP_CONFIG = REPO_ROOT / "configs" / "court_keypoints.json"


def test_keypoint_config_matches_highschool_court():
    """The court-keypoint model's measured geometry must agree with the highschool preset the pipeline
    uses for 3PT calls."""
    hs = CourtSpec.preset("highschool")
    kp = load_keypoint_config(KP_CONFIG)
    assert np.isclose(kp["length_m"], hs.length, atol=0.05) and np.isclose(kp["width_m"], hs.width, atol=0.05)
    lm = template.landmarks(hs)
    for i, name in [(2, "L_paint_base_top"), (7, "L_paint_ft_bot"), (13, "R_paint_base_bot"), (16, "R_paint_ft_top")]:
        assert np.allclose(kp["court_m"][i], lm[name], atol=0.05), name
    f = kp["flip_idx"]
    assert [f[i] for i in f] == list(range(len(f)))


def _keypoint_estimator(spec):
    from nextrun_cv.court.keypoints import KeypointCourtEstimator

    est = object.__new__(KeypointCourtEstimator)  # skip weight loading
    est.spec, est.kp = spec, load_keypoint_config(KP_CONFIG)
    return est


def test_keypoint_estimator_maps_court_and_fixes_left_right_swap():
    from nextrun_cv.court.keypoints import orientation_sign

    spec = CourtSpec.preset("highschool")
    est = _keypoint_estimator(spec)
    lm = template.landmarks(spec)
    names = ["R_base_top", "R_base_bot", "mid_top", "mid_bot"]
    img = np.float32([[1180, 300], [1250, 690], [80, 330], [10, 700]])
    Hc2i = cv2.getPerspectiveTransform(np.float32([lm[n] for n in names]), img)
    ids = [10, 12, 13, 15, 16, 17, 22, 8]  # right half + half-court line
    court = np.float32([est.kp["court_m"][i] for i in ids])
    pts = cv2.perspectiveTransform(court.reshape(-1, 1, 2), Hc2i).reshape(-1, 2)
    frame = np.zeros((720, 1280, 3), np.uint8)
    flip = est.kp["flip_idx"]
    for labels in (ids, [flip[i] for i in ids]):  # correct, and as if the model swapped halves
        calib = est.estimate(frame, {i: tuple(map(float, p)) for i, p in zip(labels, pts)})
        assert orientation_sign(calib.H, (640, 360)) > 0
        assert calib.conf > 0.9
        assert np.allclose(calib.image_to_court(pts), court, atol=0.05)
        # a player at the top of the right arc, 1 m further out, is a three
        x3 = calib.court_to_image([[spec.length / 2 - spec.hoop_from_baseline - spec.three_pt_radius - 1, 0]])
        assert template.is_three(calib.image_to_court(x3)[0], spec)


def test_keypoints_follow_court_type():
    from nextrun_cv.court.keypoints import keypoints_for_court

    kp = load_keypoint_config(KP_CONFIG)
    hs = keypoints_for_court(kp, CourtSpec.preset("highschool"))
    assert all(np.allclose(hs[i], kp["court_m"][i]) for i in hs)  # measured court: unchanged
    nba = CourtSpec.preset("nba")
    k = keypoints_for_court(kp, nba)
    lm = template.landmarks(nba)
    assert np.allclose(k[12], lm["R_paint_base_top"], atol=0.05)  # 16 ft NBA paint, not 12 ft
    hx = nba.length / 2 - nba.hoop_from_baseline
    assert abs(np.hypot(k[22][0] - hx, k[22][1]) - nba.three_pt_radius) < 0.15  # on the NBA arc


def test_venue_profile_roundtrip(tmp_path):
    from nextrun_cv.court.venues import load_venue, save_venue

    p = save_venue(str(tmp_path / "gym.json"), {"R_base_top": (100, 200)}, "nba", (3840, 2160))
    spec, pts = load_venue(str(p), (1920, 1080))
    assert spec.name == "nba" and pts["R_base_top"] == (50, 100)

