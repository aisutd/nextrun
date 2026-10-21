from nextrun_cv.config import Config
from nextrun_cv.events.analyzer import GameAnalyzer
from nextrun_cv.stats.boxscore import box_score

from synth import FPS, HAND_Y, SPEC, Game, arc, ids_red_blue, make_calib, shot_path


def _run(game: Game):
    ids = ids_red_blue()
    a = GameAnalyzer(Config(court=SPEC), FPS, ids, make_calib()).analyze(game.frames)
    return a, box_score(a, ids).set_index("player")


def test_dribble_pass_made_two_with_assist():
    g = Game({1: 400, 2: 700, 3: 1000})
    g.hold(1, 40, dribble_every=10)  # A1 dribbles 4 times
    g.fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=400))  # pass A1 -> A2
    g.hold(2, 10)
    g.move(3, 900).fly(shot_path(700, made=True))  # A2 shoots from 4.4 m, B1 grabs it under the net
    g.hold(3, 10)
    a, bs = _run(g)

    passes = a.by_type("pass")
    assert [(e.player, e.data["to"]) for e in passes] == [("A1", "A2")]
    assert passes[0].data["distance_m"] > 0
    shots = a.by_type("shot")
    assert len(shots) == 1
    s = shots[0].data
    assert s["made"] and s["points"] == 2 and s["three"] is False and not s["dunk"]
    assert 4.0 < s["distance_m"] < 5.0
    assert [e.player for e in a.by_type("assist")] == ["A1"]
    assert a.by_type("rebound") == []  # made shot: no rebound
    assert bs.loc["A2", "PTS"] == 2 and bs.loc["A2", "FGM"] == 1 and bs.loc["A2", "FGA"] == 1
    assert bs.loc["A1", "AST"] == 1 and bs.loc["A1", "PASS"] == 1
    assert 3 <= bs.loc["A1", "DRIB"] <= 4
    assert len(a.flights) >= 2 and a.flights[0].arc is not None


def test_three_pointer_from_deep():
    g = Game({1: 450, 3: 900})
    g.hold(1, 10).fly(shot_path(450, made=True)).hold(3, 5)
    a, bs = _run(g)
    s = a.by_type("shot")[0].data
    assert s["made"] and s["three"] and s["points"] == 3
    assert bs.loc["A1", "3PM"] == 1 and bs.loc["A1", "PTS"] == 3


def test_miss_then_defensive_rebound():
    g = Game({1: 700, 3: 1120})
    g.hold(1, 10).fly(shot_path(700, made=False)).hold(3, 10)
    a, bs = _run(g)
    s = a.by_type("shot")[0].data
    assert not s["made"] and s["points"] == 0
    rb = a.by_type("rebound")
    assert len(rb) == 1 and rb[0].player == "B1" and rb[0].data["offensive"] is False
    assert bs.loc["B1", "DREB"] == 1 and bs.loc["A1", "FGA"] == 1


def test_miss_then_offensive_rebound():
    g = Game({1: 700, 2: 1120})
    g.hold(1, 10).fly(shot_path(700, made=False)).hold(2, 10)
    a, _ = _run(g)
    rb = a.by_type("rebound")
    assert len(rb) == 1 and rb[0].player == "A2" and rb[0].data["offensive"] is True


def test_intercepted_pass_is_steal_and_turnover():
    g = Game({1: 400, 3: 700})
    g.hold(1, 10).fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=420)).hold(3, 10)
    a, bs = _run(g)
    assert [e.player for e in a.by_type("turnover")] == ["A1"]
    assert [e.player for e in a.by_type("steal")] == ["B1"]
    assert a.by_type("pass") == []
    assert bs.loc["A1", "TOV"] == 1 and bs.loc["B1", "STL"] == 1


def test_no_assist_when_receiver_holds_too_long():
    g = Game({1: 400, 2: 700, 3: 900})
    g.hold(1, 5).fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=400))
    g.hold(2, int(4 * FPS))  # > 3 s assist window
    g.fly(shot_path(700, made=True)).hold(3, 5)
    a, _ = _run(g)
    assert a.by_type("shot")[0].data["made"]
    assert a.by_type("assist") == []


def test_dunk():
    rim_c = (920.0, 185.0)
    g = Game({1: 880, 3: 1000})
    # dunker's hands get up to the rim: hold ball right at the rim, then slam it through
    g.hold(1, 8)
    for f in g.frames[-3:]:
        f.ball.xy = (900.0, 240.0)
        f.players[0].bbox = (850.0, 230.0, 910.0, 600.0)
    g.fly([(rim_c[0], rim_c[1] + 12 * k) for k in range(1, 25)]).hold(3, 5)
    a, bs = _run(g)
    shots = a.by_type("shot")
    assert len(shots) == 1 and shots[0].data["made"] and shots[0].data["dunk"]
    assert shots[0].data["points"] == 2 and bs.loc["A1", "DUNK"] == 1
