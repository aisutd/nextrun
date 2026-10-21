"""analyze + render stages end to end on synthetic tracks (detection stage needs ultralytics/GPU)."""
import json

import cv2
import numpy as np
import pandas as pd

from nextrun_cv import pipeline
from nextrun_cv.config import Config
from nextrun_cv.video import probe

from synth import FPS, HAND_Y, Game, arc, make_calib, shot_path


def test_analyze_and_render(tmp_path):
    g = Game({1: 400, 2: 700, 3: 900})
    g.hold(1, 20, dribble_every=10).fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=400))
    g.hold(2, 10).fly(shot_path(700, made=True)).hold(3, 10)
    frames = g.frames
    for f in frames:
        f.ball_candidates = []

    out = tmp_path / "game"
    out.mkdir()
    video = tmp_path / "game.mp4"
    w = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (1280, 720))
    for _ in frames:
        w.write(np.full((720, 1280, 3), 90, np.uint8))
    w.release()

    pipeline.save_frames(frames, out / "tracks.json.gz")
    (out / "video.json").write_text(json.dumps({"fps": FPS, "stride": 1, "width": 1280, "height": 720}))
    (out / "appearance.json").write_text(json.dumps({}))
    make_calib().save(out / "court.json")
    (out / "tags.json").write_text(json.dumps({"1": {"name": "A1", "team": "Red"}, "2": {"name": "A2", "team": "Red"},
                                               "3": {"name": "B1", "team": "Blue"}}))

    analysis, ids, frames2 = pipeline.analyze(str(out), Config())
    bs = pd.read_csv(out / "boxscore.csv").set_index("player")
    assert bs.loc["A2", "PTS"] == 2 and bs.loc["A1", "AST"] == 1
    for name in ("events.json", "flights.json", "team_totals.csv", "identities.json", "shot_chart.png", "pass_network.png", "possession.png"):
        assert (out / name).exists(), name

    path = pipeline.render(str(video), str(out), Config(), analysis, ids, frames2)
    info = probe(path)
    assert info.n_frames == len(frames)
