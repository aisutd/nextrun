"""Cross-model geometry: rims validate the court fit, players get court positions, ball gets a holder."""
from nextrun_cv import fusion
from nextrun_cv.config import Config
from nextrun_cv.schema import BallObs, FrameState, RimObs

from synth import HAND_Y, SPEC, make_calib, player

CFG = Config(court=SPEC)
# the right hoop's floor point is at image (920, 600); a rim 40 px wide, ~5.5 rim widths above it
GOOD_RIM = RimObs((900.0, 372.5, 940.0, 387.5))
SHIFTED_RIM = RimObs((1100.0, 372.5, 1140.0, 387.5))  # 4.5 rim widths to the side of any hoop


def test_rim_check_finds_the_basket():
    c = fusion.check_rim(make_calib(), GOOD_RIM, CFG.fusion)
    assert c.ok and c.hoop == 1 and c.offset < 0.1 and 5 < c.height < 6
    assert not fusion.check_rim(make_calib(), SHIFTED_RIM, CFG.fusion).ok
    assert fusion.hoop_for_rim(make_calib(), GOOD_RIM, CFG.fusion) == 1
    assert fusion.hoop_for_rim(make_calib(), SHIFTED_RIM, CFG.fusion) is None
    assert fusion.hoop_for_rim(None, GOOD_RIM, CFG.fusion) is None


def test_rims_validate_court_fit():
    ok = fusion.validate_court(make_calib(), [[GOOD_RIM]] * 3, CFG.fusion)
    assert ok.conf == 1.0 and ok.checks["rims"]["agree"] == 1.0
    bad = fusion.validate_court(make_calib(), [[SHIFTED_RIM]] * 3, CFG.fusion)
    assert bad.conf < CFG.fusion.min_court_conf and not fusion.court_usable(bad, CFG.fusion)
    none = fusion.validate_court(make_calib(), [[]], CFG.fusion)
    assert none.conf == 1.0 and none.checks["rims"]["checked"] == 0


def test_fuse_positions_players_and_drops_off_court():
    # u=920 under the right hoop; u=-1000 is ~38 m away from it, far off a 28 m court
    f = FrameState(0, 0.0, [player(1, 920), player(2, 500), player(9, -1000)], None, [], [GOOD_RIM])
    report = fusion.fuse([f], make_calib(), CFG)
    assert report["court"] and report["off_court_dropped"] == 1
    assert [p.track_id for p in f.players] == [1, 2]
    assert abs(f.players[0].court_xy[0] - (SPEC.length / 2 - SPEC.hoop_from_baseline)) < 0.01

    f.ball = BallObs((500.0, HAND_Y))
    scene = fusion.describe(f, make_calib(), CFG)
    by_id = {p["track_id"]: p for p in scene["players"]}
    assert by_id[1]["zone"] == "2PT" and by_id[2]["zone"] == "3PT"  # 8.4 m out vs a 6.75 m arc
    assert scene["ball"]["holder"] == 2 and by_id[2]["has_ball"]
    assert scene["rims"][0]["hoop"] == 1 and scene["rims"][0]["agrees_with_court"]


def test_no_court_means_no_positions():
    f = FrameState(0, 0.0, [player(1, 920)], None, [], [])
    assert fusion.fuse([f], None, CFG) == {"court": False}
    assert f.players[0].court_xy is None
    assert "zone" not in fusion.describe(f, None, CFG)["players"][0]
