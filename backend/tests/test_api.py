"""FastAPI backend end to end: upload -> background processing -> tag -> stats. The GPU detection stage
is replaced by synthetic tracks; calibration and analysis run for real."""
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from nextrun_cv import pipeline  # noqa: E402

from synth import FPS, HAND_Y, Game, arc, make_calib, shot_path  # noqa: E402


def _fake_detect(video, out_dir, cfg, progress=True, on_frame=None):
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
    from nextrun_cv import api

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


def test_preview_and_video_not_ready(client):
    gid = client.post("/games", files={"video": ("game.mp4", b"x")}).json()["id"]
    s = client.get(f"/games/{gid}").json()
    assert s["status"] == "done" and s["progress"] == 1.0 and not s["has_video"]  # fake video: render is skipped, stats stand
    assert client.get(f"/games/{gid}/video").status_code == 409
    assert client.get(f"/games/{gid}/preview").status_code == 404


def test_unknown_game_404(client):
    assert client.get("/games/nope").status_code == 404


def test_analyze_frame(client, monkeypatch):
    import cv2
    import numpy as np

    from nextrun_cv import api

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



def test_court_points_validated(client):
    gid = client.post("/games", files={"video": ("game.mp4", b"x")}).json()["id"]
    assert client.post(f"/games/{gid}/court", json={"points": [[0.1, 0.1]]}).status_code in (409, 422)


def _tagged_game(client) -> str:
    gid = client.post("/games", files={"video": ("game.mp4", b"x")}, data={"court": "fiba"}).json()["id"]
    tags = {"1": {"name": "A1", "team": "Red"}, "2": {"name": "A2", "team": "Red"}, "3": {"name": "B1", "team": "Blue"}}
    client.put(f"/games/{gid}/tags", json=tags)
    return gid


def _pts(summary, name):
    return next(p["PTS"] for p in summary["players"] if p["player"] == name)


def test_summary_has_scoring_log_with_running_score(client):
    gid = _tagged_game(client)
    sm = client.get(f"/games/{gid}/summary").json()
    assert sm["scoring"] == "standard" and sm["unassigned_pts"] == 0
    assert [(l["player"], l["made"], l["points"], l["score"]) for l in sm["log"]] == [("A2", True, 2, {"Red": 2})]


def test_fix_shot_add_basket_and_undo(client):
    gid = _tagged_game(client)
    frame = client.get(f"/games/{gid}/summary").json()["log"][0]["frame"]

    sm = client.post(f"/games/{gid}/shots/{frame}", json={"made": False}).json()  # "not a basket"
    assert _pts(sm, "A2") == 0 and sm["log"][0]["manual"] and not sm["log"][0]["made"]

    sm = client.post(f"/games/{gid}/baskets", json={"t": 1.0, "player": "B1", "points": 3}).json()  # one the AI never saw
    assert _pts(sm, "B1") == 3 and {t["team"]: t["PTS"] for t in sm["teams"]}["Blue"] == 3

    sm = client.delete(f"/games/{gid}/corrections/shot/{frame}").json()  # undo -> the AI's own call is back
    assert _pts(sm, "A2") == 2 and _pts(sm, "B1") == 3
    assert client.post(f"/games/{gid}/shots/{frame}", json={"points": 9}).status_code == 422


def test_switch_to_3x3_scoring(client):
    gid = _tagged_game(client)
    sm = client.put(f"/games/{gid}/scoring", json={"mode": "3x3"}).json()
    assert sm["scoring"] == "3x3" and _pts(sm, "A2") == 1
    assert client.put(f"/games/{gid}/scoring", json={"mode": "4x4"}).status_code == 422
    gid2 = client.post("/games", files={"video": ("g.mp4", b"x")}, data={"scoring": "3x3"}).json()["id"]
    assert client.get(f"/games/{gid2}").json()["status"] == "done"
