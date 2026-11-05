from nextrun_cv.config import Config
from nextrun_cv.events.analyzer import GameAnalyzer
from nextrun_cv.stats.boxscore import box_score

from synth import FPS, HAND_Y, RIM, SPEC, Game, arc, ids_red_blue, make_calib, shot_path


def _run(game: Game, cfg: Config | None = None):
    ids = ids_red_blue()
    a = GameAnalyzer(cfg or Config(court=SPEC), game.fps, ids, make_calib()).analyze(game.frames)
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


def test_ball_dropping_through_the_rim_box_off_centre_is_a_miss():
    # off the front rim and down just inside the box edge (the old centre-line rule called this a make)
    rim_c = ((RIM.bbox[0] + RIM.bbox[2]) / 2, RIM.bbox[1] - 15)
    up = arc((700, HAND_Y - 20), rim_c, 22, apex_y=90)
    down = [(rim_c[0] + 0.45 * RIM.width, rim_c[1] + 12 * k) for k in range(1, 26)]
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(up + down).hold(3, 10)
    a, _ = _run(g)
    shots = a.by_type("shot")
    assert len(shots) == 1 and not shots[0].data["made"]


def test_inbound_lob_through_the_rim_area_after_a_make_is_not_a_shot():
    g = Game({1: 700, 3: 1000, 4: 600})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 15)  # B1 takes it out under the basket
    g.fly(arc((1000, HAND_Y), (600, HAND_Y), 30, apex_y=150)).hold(4, 10)  # lob over the rim to B2
    ids = ids_red_blue()
    ids.track_to_player[4] = "B2"
    ids.player_team["B2"] = "Blue"
    a = GameAnalyzer(Config(court=SPEC), FPS, ids, make_calib()).analyze(g.frames)
    assert [e.data["made"] for e in a.by_type("shot")] == [True]
    assert [(e.player, e.data["to"]) for e in a.by_type("pass")] == [("B1", "B2")]


def test_rebound_goes_to_the_team_that_controls_the_ball():
    # A2 gets a hand on the miss for a moment, then B1 secures it: a defensive rebound for B1
    g = Game({1: 700, 2: 1120, 3: 1100})
    g.hold(1, 10).fly(shot_path(700, made=False)).hold(2, 3)
    g.fly(arc((1120, HAND_Y), (1100, HAND_Y), 6, apex_y=450)).hold(3, 40)
    a, _ = _run(g)
    rb = a.by_type("rebound")
    assert len(rb) == 1 and rb[0].player == "B1" and rb[0].data["offensive"] is False


# --- baskets the detector only half sees (the ball is small and the net / crowd hides it) ------------------------------
def _steep_in(u_from=700, apex_y=60):
    """Shot arriving the way real ones do: a high arc, then a near-vertical drop onto the middle of the rim."""
    up = arc((u_from, HAND_Y - 20), (920, 100), 20, apex_y=apex_y)
    return up + [(920.0, 100 + 14 * k) for k in range(1, 8)]  # last point y=198, just above the rim plane


def test_make_with_ball_lost_in_the_net_still_counts():
    # 0.37 s unseen between above-the-rim and below it (old rule needed <= 0.2 s) -> used to be logged as a miss
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 10).blank(190, 300, x_near=920)
    a, bs = _run(g)
    s = a.by_type("shot")[0].data
    assert s["made"] and s["points"] == 2 and "net" in s["reason"] and 0.5 < s["confidence"] < 0.9
    assert bs.loc["A1", "PTS"] == 2 and a.by_type("rebound") == []


def test_make_where_the_ball_vanishes_into_the_net():
    # arrives centred and falling, then is never seen again until the defender has it straight under the hoop
    g = Game({1: 700, 3: 960})
    g.hold(1, 10).fly(_steep_in()).gap(20).hold(3, 10)  # 0.67 s unseen: past the 0.5 s limit
    a, bs = _run(g)
    s = a.by_type("shot")[0].data
    assert s["made"] and "vanished" in s["reason"]
    assert bs.loc["A1", "PTS"] == 2 and bs.loc["A1", "FGM"] == 1 and a.by_type("rebound") == []


def test_ball_hidden_but_raw_detection_in_the_net_is_used():
    from nextrun_cv.schema import BallObs

    def game(with_candidates: bool) -> Game:
        g = Game({1: 700, 3: 1120})  # defender far away: only the faint detection under the rim can show it went in
        g.hold(1, 10).fly(_steep_in()).gap(20).hold(3, 10)
        if with_candidates:  # the tracker has no ball for 0.67 s, but the detector saw something faint under the rim
            g.frames[10 + len(_steep_in()) + 10].ball_candidates = [BallObs((921.0, 260.0), 6.0, 0.3)]
            g.frames[10 + len(_steep_in()) + 11].ball_candidates = [BallObs((921.0, 330.0), 6.0, 0.3)]
        return g

    assert not _run(game(False))[0].by_type("shot")[0].data["made"]  # control: nothing under the rim -> a miss
    assert _run(game(True))[0].by_type("shot")[0].data["made"]


def test_rim_out_that_bounces_back_up_is_still_a_miss():
    up = _steep_in()
    bounce = [(940.0 + 6 * k, 198 - 14 * k) for k in range(1, 8)]  # off the rim, back up and away
    g = Game({1: 700, 3: 1120})
    g.hold(1, 10).fly(up + bounce + arc((1010, 100), (1120, HAND_Y), 14, apex_y=60)).hold(3, 10)
    a, bs = _run(g)
    s = a.by_type("shot")[0].data
    assert not s["made"] and s["points"] == 0 and bs.loc["A1", "PTS"] == 0
    assert len(a.by_type("rebound")) == 1


def test_ball_lost_then_found_far_from_the_basket_is_a_miss():
    g = Game({1: 700, 3: 1120})
    g.hold(1, 10).fly(_steep_in()).gap(20).hold(3, 10)  # defender is 5 rim-widths away when the ball shows up again
    a, bs = _run(g)
    assert not a.by_type("shot")[0].data["made"] and bs.loc["A1", "PTS"] == 0


def test_basket_with_no_shooter_seen_is_still_counted_for_the_team_score():
    # the clip starts with the ball already in the air (shooter out of frame / never seen holding it)
    g = Game({3: 960})
    g.fly(_steep_in()[10:]).hold(3, 10)
    a, bs = _run(g)
    shots = a.by_type("shot")
    assert len(shots) == 1 and shots[0].data["made"] and shots[0].player is None
    assert shots[0].data["recovered"] and shots[0].data["points"] == 2


def test_a_made_shot_is_never_counted_twice():
    g = Game({1: 400, 2: 700, 3: 960})
    g.hold(1, 20, dribble_every=10).fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=400)).hold(2, 10)
    g.fly(_steep_in()).hold(3, 15)
    a, bs = _run(g)
    assert len(a.by_type("shot")) == 1 and bs["PTS"].sum() == 2 and bs.loc["A1", "AST"] == 1


def test_3x3_scoring_is_one_inside_two_outside():
    cfg = Config(court=SPEC)
    cfg.events.scoring = "3x3"
    g = Game({1: 700, 3: 1000})
    g.hold(1, 10).fly(shot_path(700, made=True)).hold(3, 10)
    _, bs = _run(g, cfg)
    assert bs.loc["A1", "PTS"] == 1
    g = Game({1: 450, 3: 900})
    g.hold(1, 10).fly(shot_path(450, made=True)).hold(3, 5)
    _, bs = _run(g, cfg)
    assert bs.loc["A1", "PTS"] == 2 and bs.loc["A1", "3PM"] == 1


def test_works_at_the_apps_frame_rate_too():
    g = Game({1: 700, 3: 960}, fps=15.0)
    g.hold(1, 6).fly(_steep_in()[::2]).hold(3, 6)
    a, bs = _run(g)
    assert a.by_type("shot")[0].data["made"] and bs.loc["A1", "PTS"] == 2


# --- a pass is a pass, never a miss + rebound ----------------------------------------------------------------------
def test_lob_pass_over_the_rim_area_is_a_pass_not_a_miss_and_rebound():
    g = Game({1: 1000, 2: 600})
    g.hold(1, 10).fly(arc((1000, HAND_Y), (600, HAND_Y), 30, apex_y=150)).hold(2, 10)
    a, bs = _run(g)
    assert a.by_type("shot") == [] and a.by_type("rebound") == []
    assert [(e.player, e.data["to"]) for e in a.by_type("pass")] == [("A1", "A2")]


def test_low_pass_near_the_hoop_is_a_pass():
    g = Game({1: 700, 2: 1120})
    g.hold(1, 10).fly(arc((700, HAND_Y), (1120, HAND_Y), 20, apex_y=300)).hold(2, 10)
    a, _ = _run(g)
    assert a.by_type("shot") == [] and a.by_type("rebound") == []
    assert len(a.by_type("pass")) == 1


def test_no_rebound_when_the_first_touch_is_far_from_the_basket_and_late():
    g = Game({1: 700, 3: 100})  # B1 picks the ball up at the other end, long after the miss
    g.hold(1, 10).fly(shot_path(700, made=False)).hold(3, 10)
    a, _ = _run(g)
    assert len(a.by_type("shot")) == 1 and a.by_type("rebound") == []


def _shot_from_distance(d_m: float):
    u = 920 - d_m / 0.02  # the synthetic camera: 0.02 m per pixel along the court, hoop at u = 920
    g = Game({1: u, 3: 900})
    g.hold(1, 10).fly(shot_path(u, made=True)).hold(3, 5)
    a, _ = _run(g)
    return a.by_type("shot")[0].data


def test_inside_the_arc_is_two_and_clearly_outside_is_three():
    assert _shot_from_distance(4.0)["points"] == 2
    assert _shot_from_distance(6.0)["points"] == 2
    assert _shot_from_distance(7.6)["points"] == 3


def test_standing_on_the_line_is_a_two():
    # the arc is 6.75 m from the hoop: 10 cm outside is inside the court-mapping error, so it counts as a two
    s = _shot_from_distance(6.85)
    assert s["three"] is False and s["points"] == 2


def test_high_arcing_pass_over_the_rim_area_is_a_pass_even_when_caught_near_the_basket():
    g = Game({1: 1000, 2: 840})
    g.hold(1, 10).fly(arc((1000, HAND_Y), (840, HAND_Y), 24, apex_y=120)).hold(2, 10)
    a, bs = _run(g)
    assert a.by_type("shot") == [] and a.by_type("rebound") == []
    assert [(e.player, e.data["to"]) for e in a.by_type("pass")] == [("A1", "A2")]


def test_a_real_miss_is_still_a_miss_with_a_rebound():
    g = Game({1: 700, 2: 1000})
    g.hold(1, 10).fly(shot_path(700, made=False)).hold(2, 10)
    a, _ = _run(g)
    shots, rebs = a.by_type("shot"), a.by_type("rebound")
    assert len(shots) == 1 and not shots[0].data["made"] and shots[0].data["rim_reach_w"] <= 1.3
    assert len(rebs) == 1
