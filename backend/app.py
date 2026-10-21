"""NextRun FastAPI backend: upload a game video, run the CV pipeline in the background, then tag players
and read back the box score (PTS / REB / AST first).

  uvicorn backend.app:app --reload          # http://localhost:8000/docs

Each game lives in $NEXTRUN_DATA/<game_id>/ (default outputs/) with the pipeline's files plus
status.json, so state survives restarts. Processing runs in-process (BackgroundTasks); swap in a
real queue (Celery / RQ / Cloud Run jobs) once uploads need a GPU worker.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from nextrun_cv import pipeline
from nextrun_cv.config import REPO_ROOT, Config, CourtSpec
from nextrun_cv.court.venues import list_venues, load_venue
from nextrun_cv.stats.boxscore import HEADLINE, team_totals

log = logging.getLogger("nextrun.api")
DATA_DIR = Path(os.environ.get("NEXTRUN_DATA", REPO_ROOT / "outputs"))
COURTS = Literal["highschool", "fiba", "nba", "ncaa"]
Status = Literal["queued", "detecting", "calibrating", "analyzing", "done", "failed"]

app = FastAPI(title="NextRun", description="Basketball stat tracking from game video")
_models = None  # integration.NextRun, loaded on first /frames/analyze
_models_lock = threading.Lock()


class GameStatus(BaseModel):
    id: str
    status: Status
    court: str = "highschool"
    venue: str | None = None
    court_calibrated: bool = False
    error: str | None = None


class Tag(BaseModel):
    name: str
    team: str | None = None


# --- storage -----------------------------------------------------------------------------------------
def _dir(game_id: str) -> Path:
    d = DATA_DIR / game_id
    if not d.is_dir() or not (d / "status.json").exists():
        raise HTTPException(404, f"game {game_id} not found")
    return d


def _status(d: Path) -> GameStatus:
    return GameStatus.model_validate_json((d / "status.json").read_text())


def _set_status(d: Path, **kw) -> GameStatus:
    s = _status(d).model_copy(update=kw)
    (d / "status.json").write_text(s.model_dump_json())
    return s


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


# --- processing --------------------------------------------------------------------------------------
def process_game(game_id: str) -> None:
    """detect -> calibrate (optional: stats still work without a court, minus 2PT/3PT) -> analyze."""
    d = DATA_DIR / game_id
    cfg = Config.load(d / "config.json")
    video = str(d / "video.mp4")
    try:
        _set_status(d, status="detecting")
        pipeline.detect(video, str(d), cfg, progress=False)
        _set_status(d, status="calibrating")
        try:
            pipeline.calibrate(video, str(d), cfg, venue=_status(d).venue)
            _set_status(d, court_calibrated=True)
        except Exception as e:  # noqa: BLE001
            log.warning("game %s: court calibration failed: %s", game_id, e)
        _set_status(d, status="analyzing")
        pipeline.analyze(str(d), cfg)
        _set_status(d, status="done")
    except Exception as e:  # noqa: BLE001
        log.exception("game %s failed", game_id)
        _set_status(d, status="failed", error=str(e))


# --- routes ------------------------------------------------------------------------------------------
@app.get("/venues")
def venues() -> list[str]:
    """Saved camera profiles (venues/*.json)."""
    return list_venues()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/frames/analyze")
def analyze_frame(image: UploadFile = File(...)):
    """One still image through all three models together: court (checked against the rims), players placed
    on the court with 2PT / 3PT zones, who holds the ball, which basket each rim is."""
    global _models
    img = cv2.imdecode(np.frombuffer(image.file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "not an image")
    with _models_lock:  # one set of models, one request at a time
        if _models is None:
            from nextrun_cv.integration import NextRun

            _models = NextRun()
        return _models.analyze_image(img)


@app.post("/games", response_model=GameStatus, status_code=202)
def create_game(
    background: BackgroundTasks,
    video: UploadFile = File(...),
    court: COURTS = Form("highschool"),
    venue: str | None = Form(None),
):
    """Upload a fixed-camera game video. Processing starts in the background; poll GET /games/{id}.
    `venue`: a saved camera profile (GET /venues) - sets the court type and skips court detection."""
    if venue is not None:
        if venue not in list_venues():
            raise HTTPException(404, f"unknown venue {venue!r}")
        court = load_venue(venue)[0].name
    game_id = uuid.uuid4().hex[:12]
    d = DATA_DIR / game_id
    d.mkdir(parents=True)
    with open(d / "video.mp4", "wb") as fh:
        while chunk := video.file.read(1 << 20):
            fh.write(chunk)
    Config(court=CourtSpec.preset(court)).save(d / "config.json")
    s = GameStatus(id=game_id, status="queued", court=court, venue=venue)
    (d / "status.json").write_text(s.model_dump_json())
    background.add_task(process_game, game_id)
    return s


@app.get("/games/{game_id}", response_model=GameStatus)
def get_game(game_id: str):
    return _status(_dir(game_id))


@app.get("/games/{game_id}/tagging-frame")
def tagging_frame(game_id: str):
    """Frame with tracker ids drawn on it: use it to fill in PUT /games/{id}/tags."""
    p = _dir(game_id) / "tagging_frame.jpg"
    if not p.exists():
        raise HTTPException(409, "detection has not finished yet")
    return FileResponse(p, media_type="image/jpeg")


@app.put("/games/{game_id}/tags")
def set_tags(game_id: str, tags: dict[str, Tag]):
    """{track_id: {name, team}} -> re-runs analysis (cheap, no re-detection) and returns the new stats."""
    d = _dir(game_id)
    if not (d / "tracks.json.gz").exists():
        raise HTTPException(409, "detection has not finished yet")
    (d / "tags.json").write_text(json.dumps({k: v.model_dump() for k, v in tags.items()}, indent=2))
    pipeline.analyze(str(d), Config.load(d / "config.json"))
    return get_stats(game_id)


@app.get("/games/{game_id}/stats")
def get_stats(game_id: str):
    """Per-player and per-team box score. `players[*]` leads with PTS / REB / AST."""
    d = _dir(game_id)
    if not (d / "boxscore.csv").exists():
        raise HTTPException(409, f"stats not ready (status: {_status(d).status})")
    bs = pd.read_csv(d / "boxscore.csv")
    return {"headline": HEADLINE, "players": _records(bs), "teams": _records(team_totals(bs))}


@app.get("/games/{game_id}/events")
def get_events(game_id: str, include_dribbles: bool = False):
    """Timestamped event log (shots, rebounds, assists, passes, steals, turnovers...)."""
    p = _dir(game_id) / "events.json"
    if not p.exists():
        raise HTTPException(409, "events not ready")
    events = json.loads(p.read_text())
    return [e for e in events if include_dribbles or e["type"] != "dribble"]
