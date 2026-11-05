import numpy as np

from nextrun_cv.config import CourtSpec
from nextrun_cv.court.base import CourtCalib
from nextrun_cv.court.track import ROT, CameraMotion, CourtTrack, _combine, _grid, stabilize_view
from nextrun_cv.detect.ball_track import stabilize_rims_moving
from nextrun_cv.schema import BallObs, FrameState, PlayerObs, RimObs

SPEC = CourtSpec.preset("nba")
W, H = 1280, 720


def camera(pan_px: float = 0.0) -> np.ndarray:
    """Image -> court homography of a raised sideline camera, panned by `pan_px` pixels."""
    court_to_img = np.array([[40.0, 8.0, 640.0], [0.0, -25.0, 420.0], [0.0, 0.012, 1.0]])
    shift = np.array([[1.0, 0.0, -pan_px], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    return np.linalg.inv(shift @ court_to_img)


def test_static_track_returns_its_one_calibration_for_every_frame():
    c = CourtCalib(camera(), "keypoints", 0.9, SPEC)
    t = CourtTrack.static(c)
    assert t.at(0) is c and t.at(12345) is c and not t.moving


def test_moving_track_has_no_court_far_from_calibrated_frames():
    t = CourtTrack(SPEC, {10: CourtCalib(camera(), "k", 0.9, SPEC), 20: CourtCalib(camera(5), "k", 0.9, SPEC)}, True)
    assert t.at(11).H is t.calibs[10].H and t.at(19).H is t.calibs[20].H
    assert t.at(15) is None


def test_combine_outvotes_a_wrong_fit():
    grid = _grid(W, H)
    good = camera()
    cands = [(good, 0.9), (good, 0.8), (ROT @ good, 0.7)]  # one fit with the baskets swapped
    Hc, spread = _combine(cands, grid, SPEC)
    p = np.c_[grid, np.ones(len(grid))]
    a, b = p @ Hc.T, p @ good.T
    assert np.allclose(a[:, :2] / a[:, 2:], b[:, :2] / b[:, 2:], atol=0.05)


def motion_for(pans: list[float]) -> CameraMotion:
    m = CameraMotion()
    m.idx = list(range(len(pans)))
    m.seg = [0] * len(pans)
    m.M = [np.array([[1.0, 0.0, -p], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]) for p in pans]  # first frame -> frame i
    return m


def test_stabilize_view_keeps_court_positions_and_fixes_the_rim():
    pans = [0.0, 30.0, 60.0]
    motion = motion_for(pans)
    rim_world = (900.0, 200.0, 950.0, 240.0)  # rim box in the first frame
    frames, calibs = [], {}
    for i, p in enumerate(pans):
        rim = RimObs((rim_world[0] - p, rim_world[1], rim_world[2] - p, rim_world[3]))
        pl = PlayerObs(1, (500.0 - p, 300.0, 540.0, 400.0))
        frames.append(FrameState(i, i / 30, [pl], BallObs((700.0 - p, 250.0)), [], [rim]))
        calibs[i] = CourtCalib(camera(p), "k", 0.9, SPEC)
    court = CourtTrack(SPEC, calibs, True)
    view, vcourt = stabilize_view(frames, court, motion)
    for f, v in zip(frames, view):
        assert np.allclose(v.rims[0].bbox, rim_world)
        assert np.allclose(v.ball.xy, (700.0, 250.0))
        # the same feet land on the same court spot in both coordinate systems
        a = court.at(f.idx).image_to_court([f.players[0].feet])[0]
        b = vcourt.at(v.idx).image_to_court([v.players[0].feet])[0]
        assert np.allclose(a, b, atol=1e-6)


def test_stabilize_rims_moving_follows_the_camera_and_fills_gaps():
    pans = [float(3 * i) for i in range(40)]
    motion = motion_for(pans)
    frames = []
    for i, p in enumerate(pans):
        rims = [] if 15 <= i < 25 else [RimObs((900.0 - p, 200.0, 950.0 - p, 240.0), 0.8)]  # ball in front of it
        frames.append(FrameState(i, i / 30, rims=rims))
    stabilize_rims_moving(frames, motion.seg, motion.M, (W, H))
    for i, (f, p) in enumerate(zip(frames, pans)):
        assert len(f.rims) == 1
        assert np.allclose(f.rims[0].bbox, (900.0 - p, 200.0, 950.0 - p, 240.0), atol=1e-3)
