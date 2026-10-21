"""FastAPI backend end to end: upload -> background processing -> tag -> stats. The GPU detection stage
is replaced by synthetic tracks; calibration and analysis run for real."""
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from nextrun_cv import pipeline  # noqa: E402

from synth import FPS, HAND_Y, Game, arc, make_calib, shot_path  # noqa: E402


def _fake_detect(video, out_dir, cfg, progress=True):
    g = Game({1: 400, 2: 700, 3: 900})
    g.hold(1, 20, dribble_every=10).fly(arc((400, HAND_Y), (700, HAND_Y), 14, apex_y=400))
    g.hold(2, 10).fly(shot_path(700, made=True)).hold(3, 10)
    for f in g.frames:
        f.ball_candidates = []
    out = Path(out_dir)
    pipeline.save_frames(g.frames, out / "tracks.json.gz")
    (out / "video.json").write_text(json.dumps({"fps": FPS, "stride": 1, "width": 1280, "height": 720}))
    (out / "appearance.json").write_text("{}")
    (out / "tagging_frame.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    return g.frames


def _fake_calibrate(video, out_dir, cfg, manual_points=None, venue=None):
    calib = make_calib()
    calib.save(Path(out_dir) / "court.json")
    return calib


@pytest.fixture
def client(tmp_path, monkeypatch):
    from backend import app as api

    monkeypatch.setattr(api, "DATA_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "detect", _fake_detect)
    monkeypatch.setattr(pipeline, "calibrate", _fake_calibrate)
    return TestClient(api.app)


def test_upload_tag_and_stats(client):
    r = client.post("/games", files={"video": ("game.mp4", b"not really a video")}, data={"court": "fiba"})
    assert r.status_code == 202
    gid = r.json()["id"]

    s = client.get(f"/games/{gid}").json()  # TestClient runs background tasks before returning
    assert s["status"] == "done" and s["court_calibrated"], s
    assert client.get(f"/games/{gid}/tagging-frame").status_code == 200

    tags = {"1": {"name": "A1", "team": "Red"}, "2": {"name": "A2", "team": "Red"}, "3": {"name": "B1", "team": "Blue"}}
    stats = client.put(f"/games/{gid}/tags", json=tags).json()
    assert stats["headline"] == ["PTS", "REB", "AST"]
    players = {p["player"]: p for p in stats["players"]}
    assert players["A2"]["PTS"] == 2 and players["A1"]["AST"] == 1
    assert client.get(f"/games/{gid}/stats").json() == stats

    events = client.get(f"/games/{gid}/events").json()
    shot = next(e for e in events if e["type"] == "shot")
    assert shot["data"]["made"] and shot["data"]["three_line_m"] < 0


def test_unknown_game_404(client):
    assert client.get("/games/nope").status_code == 404


def test_analyze_frame(client, monkeypatch):
    import cv2
    import numpy as np

    from backend import app as api

    class FakeNextRun:
        def analyze_image(self, img):
            return {"players": [], "shape": list(img.shape)}

    monkeypatch.setattr(api, "_models", FakeNextRun())
    ok, jpg = cv2.imencode(".jpg", np.zeros((72, 128, 3), np.uint8))
    r = client.post("/frames/analyze", files={"image": ("f.jpg", jpg.tobytes())})
    assert r.status_code == 200 and r.json()["shape"] == [72, 128, 3]
    assert client.post("/frames/analyze", files={"image": ("f.jpg", b"nope")}).status_code == 400


def test_venues(client):
    assert "trackid3x3_outdoor" in client.get("/venues").json()
    r = client.post("/games", files={"video": ("g.mp4", b"x")}, data={"venue": "trackid3x3_outdoor"})
    assert r.status_code == 202 and r.json()["court"] == "fiba" and r.json()["venue"] == "trackid3x3_outdoor"
    assert client.post("/games", files={"video": ("g.mp4", b"x")}, data={"venue": "nope"}).status_code == 404

