"""Scoring corrections and the scoring log, through the real analyze stage (what the API routes call)."""
import json
from pathlib import Path

import pandas as pd

from nextrun_cv import pipeline
from nextrun_cv.config import Config
from nextrun_cv.events import overrides as ov
from nextrun_cv.stats.cards import build_summary

from synth import FPS, HAND_Y, SPEC, Game, arc, make_calib, shot_path

TAGS = {"1": {"name": "A1", "team": "Red"}, "2": {"name": "A2", "team": "Red"}, "3": {"name": "B1", "team": "Blue"}}


def _steep_in(u_from=700):
    return arc((u_from, HAND_Y - 20), (920, 100), 20, apex_y=60) + [(920.0, 100 + 14 * k) for k in range(1, 8)]


def _game_dir(tmp_path: Path, game: Game, scoring="standard") -> tuple[Path, Config]:
    cfg = Config(court=SPEC)
    cfg.events.scoring = scoring
    pipeline.save_frames(game.frames, tmp_path / "tracks.json.gz")
    (tmp_path / "video.json").write_text(json.dumps({"fps": FPS, "stride": 1, "width": 1280, "height": 720}))
    (tmp_path / "appearance.json").write_text("{}")
    (tmp_path / "tags.json").write_text(json.dumps(TAGS))
    make_calib().save(tmp_path / "court.json")
    return tmp_path, cfg


def _summary(d: Path, cfg: Config) -> dict:
    pipeline.analyze(str(d), cfg)
    events = json.loads((d / "events.json").read_text())
    return build_summary(pd.read_csv(d / "boxscore.csv"), events, cfg.events.scoring)


def _pts(sm, name):
    return next(p["PTS"] for p in sm["players"] if p["player"] == name)


def _missed_game():
    """The ball is seen coming back up off the rim (a pop-up from the net, say), so the AI logs a miss and B1 'rebounds'."""
    bounce = [(940.0 + 6 * k, 198 - 14 * k) for k in range(1, 8)]
    g = Game({1: 700, 3: 1000})
    return g.hold(1, 10).fly(_steep_in() + bounce + arc((1010, 100), (1000, HAND_Y), 14, apex_y=60)).hold(3, 10)


def test_scoring_log_and_running_score(tmp_path):
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 10)
    d, cfg = _game_dir(tmp_path, g)
    sm = _summary(d, cfg)
    assert [(l["player"], l["made"], l["points"], l["score"]) for l in sm["log"]] == [("A1", True, 2, {"Red": 2})]
    assert sm["log"][0]["reason"] and sm["log"][0]["confidence"] >= 0.9 and not sm["log"][0]["uncertain"]
    assert {t["team"]: t["PTS"] for t in sm["teams"]} == {"Red": 2, "Blue": 0} and sm["scoring"] == "standard"


def test_count_a_basket_the_ai_called_a_miss_and_undo_it(tmp_path):
    d, cfg = _game_dir(tmp_path, _missed_game())
    sm = _summary(d, cfg)
    miss = sm["log"][0]
    assert not miss["made"] and _pts(sm, "A1") == 0 and any(p["REB"] for p in sm["players"])  # B1 'rebounded' it

    ov.save_overrides(d / "overrides.json", ov.upsert([], {"type": "shot", "frame": miss["frame"], "made": True}))
    sm = _summary(d, cfg)
    assert sm["log"][0]["made"] and sm["log"][0]["manual"] and sm["log"][0]["points"] == 2
    assert _pts(sm, "A1") == 2 and sum(p["REB"] for p in sm["players"]) == 0  # the phantom rebound is gone
    assert {t["team"]: t["PTS"] for t in sm["teams"]}["Red"] == 2

    ov.save_overrides(d / "overrides.json", ov.remove(ov.load_overrides(d / "overrides.json"), "shot", miss["frame"]))
    assert _pts(_summary(d, cfg), "A1") == 0


def test_remove_a_wrong_basket_and_change_points_and_player(tmp_path):
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 10)
    d, cfg = _game_dir(tmp_path, g)
    frame = _summary(d, cfg)["log"][0]["frame"]
    ov.save_overrides(d / "overrides.json", [{"type": "shot", "frame": frame, "made": False}])
    sm = _summary(d, cfg)
    assert _pts(sm, "A1") == 0 and not sm["log"][0]["made"]
    ov.save_overrides(d / "overrides.json", [{"type": "shot", "frame": frame, "points": 3, "player": "B1"}])
    sm = _summary(d, cfg)
    assert _pts(sm, "B1") == 3 and _pts(sm, "A1") == 0 and {t["team"]: t["PTS"] for t in sm["teams"]}["Blue"] == 3


def test_add_a_basket_the_ai_never_saw(tmp_path):
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).hold(3, 10)  # no shot at all
    d, cfg = _game_dir(tmp_path, g)
    assert _summary(d, cfg)["log"] == []
    ov.save_overrides(d / "overrides.json", [{"type": "add", "frame": 12, "t": 0.4, "player": "B1", "points": 2}])
    sm = _summary(d, cfg)
    assert _pts(sm, "B1") == 2 and sm["log"][0]["manual"] and sm["log"][0]["score"] == {"Blue": 2}


def test_unassigned_basket_counts_once_a_player_is_picked(tmp_path):
    g = Game({3: 960})
    g.fly(_steep_in()[10:]).hold(3, 10)  # shooter never seen
    d, cfg = _game_dir(tmp_path, g)
    sm = _summary(d, cfg)
    b = sm["log"][0]
    assert b["made"] and b["player"] is None and b["uncertain"] and sm["unassigned_pts"] == 2
    ov.save_overrides(d / "overrides.json", [{"type": "shot", "frame": b["frame"], "player": "A2"}])
    sm = _summary(d, cfg)
    assert _pts(sm, "A2") == 2 and sm["unassigned_pts"] == 0


def test_3x3_scoring_mode(tmp_path):
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 10)
    d, cfg = _game_dir(tmp_path, g, scoring="3x3")
    sm = _summary(d, cfg)
    assert _pts(sm, "A1") == 1 and sm["scoring"] == "3x3"
