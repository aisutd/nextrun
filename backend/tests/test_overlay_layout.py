"""The score card and minimap go to the corners with the least action, per video."""
from nextrun_cv.schema import FrameState, PlayerObs
from nextrun_cv.viz.overlay import _overlaps_players, plan_layout


def _frames(boxes, n=20):
    return [FrameState(i, i / 10, [PlayerObs(track_id=k, bbox=b, conf=0.9) for k, b in enumerate(boxes)], None, [], [])
            for i in range(n)]


def test_default_layout_when_the_corners_are_empty():
    frames = _frames([(600, 300, 680, 500)])  # one player mid-frame
    assert plan_layout(frames, 1280, 720, (300, 150), (220, 120), 10) == {"card": "tl", "minimap": "br"}


def test_card_and_minimap_avoid_crowded_corners():
    crowd = [(20 + 60 * i, 20, 70 + 60 * i, 200) for i in range(4)]  # players along the top left
    crowd += [(1000 + 50 * i, 520, 1040 + 50 * i, 700) for i in range(4)]  # and the bottom right
    out = plan_layout(_frames(crowd), 1280, 720, (300, 150), (220, 120), 10)
    assert out["card"] not in ("tl", "br") and out["minimap"] not in ("tl", "br")
    assert out["card"] != out["minimap"]


def test_overlap_check_counts_the_name_tag_above_a_player():
    p = PlayerObs(track_id=1, bbox=(100, 200, 150, 300), conf=0.9)
    assert _overlaps_players((90, 150, 300, 190), [p])  # the tag zone above the head
    assert not _overlaps_players((400, 400, 500, 500), [p])
