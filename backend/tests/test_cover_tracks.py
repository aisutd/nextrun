"""One id per real person: join pieces of a player, never two people seen together, respect the person's tags."""
import numpy as np

from nextrun_cv.config import StitchConfig
from nextrun_cv.identity.stitch import cover_tracks
from nextrun_cv.pipeline import _merge_tags, _tag_constraints
from nextrun_cv.schema import FrameState, PlayerObs

RED = np.r_[np.eye(36)[0], np.eye(36)[9]].astype(np.float32)  # same outfit -> body distance 0
BLUE = np.r_[np.eye(36)[20], np.eye(36)[30]].astype(np.float32)  # different outfit -> body distance 1


def _clip(pieces, n=60):
    """pieces: {track id: (first frame, last frame, x)}; one player box per frame while the piece is visible."""
    frames = []
    for i in range(n):
        ps = [PlayerObs(track_id=t, bbox=(x, 300, x + 40, 400), conf=0.9) for t, (a, b, x) in pieces.items() if a <= i <= b]
        frames.append(FrameState(i, i / 10, ps, None, [], []))
    return frames


def test_joins_pieces_of_the_same_outfit_and_keeps_the_other_player():
    frames = _clip({1: (0, 20, 100), 2: (0, 59, 600), 3: (35, 59, 120)})  # 3 = player 1 again after leaving
    out = cover_tracks(frames, {}, StitchConfig(), body={1: RED, 2: BLUE, 3: RED})
    assert out == {3: 1}
    assert {p.track_id for f in frames for p in f.players} == {1, 2}


def test_never_joins_people_seen_at_the_same_time():
    frames = _clip({1: (0, 30, 100), 3: (25, 59, 300), 4: (0, 59, 600)})  # 1 and 3 overlap: two people
    assert cover_tracks(frames, {}, StitchConfig(), body={1: RED, 3: RED, 4: BLUE}) == {}


def test_different_outfits_stay_apart():
    frames = _clip({1: (0, 20, 100), 2: (0, 59, 600), 3: (35, 59, 120)})
    assert cover_tracks(frames, {}, StitchConfig(), body={1: RED, 2: BLUE, 3: BLUE}) == {}


def test_teams_the_person_chose_are_respected():
    frames = _clip({1: (0, 20, 100), 2: (0, 59, 600), 3: (35, 59, 120)})
    assert cover_tracks(frames, {}, StitchConfig(), teams={1: "A", 3: "B"}, body={1: RED, 2: BLUE, 3: RED}) == {}


def test_default_player_labels_do_not_block_joins_but_typed_names_do():
    tags = {1: {"name": "Player 1", "team": "A"}, 3: {"name": "Player 3", "team": "A"}, 7: {"name": "Shiva", "team": "B"}}
    names, teams = _tag_constraints(tags)
    assert names == {7: "Shiva"} and teams == {1: "A", 3: "A", 7: "B"}
    assert _merge_tags(tags, {3: 1})[1]["name"] == "Player 1"
