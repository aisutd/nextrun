import numpy as np

from nextrun_cv.config import BallTrackConfig, Config
from nextrun_cv.detect.ball_track import stabilize_rims, track_ball
from nextrun_cv.identity.appearance import color_embedding
from nextrun_cv.identity.tagging import resolve_identities
from nextrun_cv.identity.teams import assign_teams
from nextrun_cv.schema import BallObs, FrameState, PlayerObs, RimObs, frames_from_records, frames_to_records


def _frames_with_ball(path, drop=(), outliers=None):
    frames = []
    for i, xy in enumerate(path):
        f = FrameState(i, i / 30)
        if i not in drop:
            f.ball_candidates.append(BallObs(xy, 6, 0.8))
        if outliers and i in outliers:
            f.ball_candidates.append(BallObs(outliers[i], 6, 0.9))
        frames.append(f)
    return frames


def test_ball_track_rejects_outliers_and_interpolates():
    path = [(100 + 10 * i, 300 + 2 * i) for i in range(40)]
    frames = _frames_with_ball(path, drop={10, 11, 12, 13}, outliers={20: (900, 50), 25: (20, 700)})
    track_ball(frames, BallTrackConfig())
    for i, f in enumerate(frames):
        assert f.ball is not None
        assert np.hypot(f.ball.xy[0] - path[i][0], f.ball.xy[1] - path[i][1]) < 3, i
    assert all(frames[i].ball.interpolated for i in (10, 11, 12, 13))


def test_ball_track_long_gap_not_filled():
    path = [(100 + 5 * i, 300) for i in range(40)]
    frames = _frames_with_ball(path, drop=set(range(10, 30)))
    track_ball(frames, BallTrackConfig(max_gap_frames=8))
    assert all(frames[i].ball is None for i in range(10, 30))


def test_stabilize_rims_fills_occluded_frames():
    frames = [FrameState(i, i / 30, rims=[RimObs((900 + (i % 3), 200, 940, 215), 0.9)] if i % 4 else []) for i in range(40)]
    frames.append(FrameState(40, 40 / 30, rims=[RimObs((100, 100, 120, 110), 0.4)]))  # one-off false positive
    stable = stabilize_rims(frames)
    assert len(stable) == 1
    assert all(len(f.rims) == 1 for f in frames)


def _crop(bgr):
    return np.full((40, 20, 3), bgr, np.uint8) + np.random.default_rng(sum(bgr)).integers(0, 15, (40, 20, 3), dtype=np.uint8)


def test_team_clustering_by_jersey_color():
    emb = {1: color_embedding(_crop((0, 0, 200))), 2: color_embedding(_crop((10, 10, 190))),
           3: color_embedding(_crop((200, 50, 0))), 4: color_embedding(_crop((190, 60, 10)))}
    t = assign_teams(emb, 2)
    assert t[1] == t[2] and t[3] == t[4] and t[1] != t[3]
    seeded = assign_teams(emb, 2, {"Red": [emb[1]], "Blue": [emb[3]]})
    assert seeded == {1: "Red", 2: "Red", 3: "Blue", 4: "Blue"}


def test_relink_broken_track_to_tagged_player():
    red, blue = color_embedding(_crop((0, 0, 200))), color_embedding(_crop((200, 50, 0)))
    frames = []
    for i in range(60):
        ps = [PlayerObs(2, (600, 420, 660, 600))]  # blue player, always visible
        if i < 25:
            ps.append(PlayerObs(1, (300 + i, 420, 360 + i, 600)))  # red player ...
        elif i >= 30:
            ps.append(PlayerObs(7, (330 + i, 420, 390 + i, 600)))  # ... re-appears with a new ID
        frames.append(FrameState(i, i / 30, ps))
    ids = resolve_identities(frames, {1: red, 2: blue, 7: red}, {1: {"name": "Tushaar", "team": "Red"}, 2: {"name": "Juan", "team": "Blue"}})
    assert ids.player(7) == "Tushaar"
    assert ids.team(7) == "Red"


def test_frame_records_roundtrip():
    f = FrameState(3, 0.1, [PlayerObs(1, (1, 2, 3, 4), 0.5, np.zeros((17, 3)))], BallObs((5, 6)), [BallObs((5, 6))], [RimObs((1, 1, 2, 2))])
    g = frames_from_records(frames_to_records([f]))[0]
    assert g.players[0].bbox == (1, 2, 3, 4) and g.ball.xy == (5, 6) and g.players[0].keypoints.shape == (17, 3)


def test_config_roundtrip(tmp_path):
    c = Config()
    c.events.assist_window_s = 2.5
    c.save(tmp_path / "c.json")
    assert Config.load(tmp_path / "c.json").events.assist_window_s == 2.5
