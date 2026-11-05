"""NextRun FastAPI backend: upload a game video, run the CV pipeline in the background, then tag players
and read back the box score (PTS / REB / AST first).

  uvicorn nextrun_cv.api:app --reload          # http://localhost:8000/docs

Each game lives in $NEXTRUN_DATA/<game_id>/ (default results/games/) with the pipeline's files plus
status.json, so state survives restarts. Processing runs in-process (BackgroundTasks); swap in a
real queue (Celery / RQ / Cloud Run jobs) once uploads need a GPU worker.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from nextrun_cv import pipeline
from nextrun_cv.config import REPO_ROOT, Config, CourtSpec
from nextrun_cv.court.venues import apply_venue, list_venues, load_venue
from nextrun_cv.stats.boxscore import HEADLINE, team_totals
from nextrun_cv.court.manual import paint_landmarks
from nextrun_cv.events import overrides as ov
from nextrun_cv.stats.cards import build_summary
from nextrun_cv.video import ffmpeg_exe, probe, read_frame

log = logging.getLogger("nextrun.api")
DATA_DIR = Path(os.environ.get("NEXTRUN_DATA", REPO_ROOT / "results" / "games"))
# Speed / accuracy trade-off for uploads (override with env vars):
MAX_SECONDS = float(os.environ.get("NEXTRUN_MAX_SECONDS", 40))  # only the first N seconds of a video are analysed
TARGET_FPS = float(os.environ.get("NEXTRUN_TARGET_FPS", 15))  # analyse ~15 frames/s (every 2nd frame of a 30 fps clip)
MAX_IMGSZ = int(os.environ.get("NEXTRUN_MAX_IMGSZ", 1280))  # ball/rim model input long side; 4K frames are shrunk to this
PLAYER_IMGSZ = int(os.environ.get("NEXTRUN_PLAYER_IMGSZ", 960))  # players are big, so the pose model can run smaller (faster)
COURTS = Literal["highschool", "fiba", "nba", "ncaa"]
SCORING = Literal["standard", "3x3"]  # standard: 2 inside the arc / 3 outside; 3x3: 1 / 2
Status = Literal["queued", "detecting", "calibrating", "analyzing", "rendering", "done", "failed"]

app = FastAPI(title="NextRun", description="Basketball stat tracking from game video")
# the Expo app (web build / dev server) calls this API from another origin
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_models = None  # integration.NextRun, loaded on first /frames/analyze
_models_lock = threading.Lock()


class GameStatus(BaseModel):
    id: str
    status: Status
    court: str = "highschool"
    venue: str | None = None
    court_calibrated: bool = False
    error: str | None = None
    # live progress for the app: what each model has found so far
    progress: float = 0.0  # 0..1 over the whole job
    frames_done: int = 0
    frames_total: int = 0
    max_players: int = 0  # most players seen in one frame (player pose + tracking model)
    ball_frames: int = 0  # frames where the ball/rim model found a ball
    rim_frames: int = 0  # frames where it found a rim
    court_conf: float | None = None  # court keypoint model confidence once calibrated
    has_video: bool = False  # annotated video is ready (GET /games/{id}/video)
    render_error: str | None = None
    court_method: str | None = None  # keypoints / lines / manual / estimate
    video_version: float = 0.0  # changes whenever the annotated video is rewritten (cache-buster for the app)
    name: str = ""  # original file name


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
    tmp = d / "status.json.tmp"
    tmp.write_text(s.model_dump_json())
    os.replace(tmp, d / "status.json")
    return s


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


# --- processing --------------------------------------------------------------------------------------
def _preview(d: Path, img: np.ndarray, f) -> None:
    """Latest detection frame (players, ball candidates, rims drawn on it) -> preview.jpg for the app."""
    img = img.copy()
    for p in f.players:
        x1, y1, x2, y2 = map(int, p.bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), (60, 76, 231), 2)
    for r in f.rims:
        x1, y1, x2, y2 = map(int, r.bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 140, 255), 3)
    for b in f.ball_candidates:
        cv2.circle(img, tuple(map(int, b.xy)), max(5, int(b.radius)), (0, 255, 255), 2)
    scale = 640 / max(img.shape[:2])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if ok:
        (d / "preview.tmp").write_bytes(jpg.tobytes())
        os.replace(d / "preview.tmp", d / "preview.jpg")


def _ffmpeg() -> str | None:
    """System ffmpeg, else the one bundled with the imageio-ffmpeg package."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def _web_video(src: Path, dst: Path) -> Path:
    """OpenCV writes mp4v, which browsers will not play: re-encode to H.264."""
    exe = _ffmpeg()
    if exe is None:
        raise RuntimeError("ffmpeg not found (pip install imageio-ffmpeg)")
    r = subprocess.run([exe, "-y", "-i", str(src), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)], capture_output=True)
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError("video re-encode failed: " + r.stderr.decode(errors="ignore")[-300:])
    return dst


def _finish(d: Path, cfg: Config, video: str, game_id: str) -> None:
    """analyze -> render -> web video -> done (first processing, and again after a court correction)."""
    _set_status(d, status="analyzing", progress=0.75)
    analysis, ids, frames = pipeline.analyze(str(d), cfg)
    _set_status(d, status="rendering", progress=0.85, has_video=False, render_error=None)
    try:  # the annotated video is the showpiece, but stats stand without it
        (d / "annotated_web.mp4").unlink(missing_ok=True)
        raw = pipeline.render(video, str(d), cfg, analysis, ids, frames)
        if ffmpeg_exe() is None:  # no ffmpeg: the renderer wrote mp4v, which browsers cannot play
            _web_video(raw, d / "annotated_web.mp4")
        _set_status(d, has_video=True, video_version=time.time())
    except Exception as e:  # noqa: BLE001
        log.warning("game %s: render failed: %s", game_id, e)
        _set_status(d, render_error=str(e)[:300])
    _set_status(d, status="done", progress=1.0)


def recalibrate_game(game_id: str, points: list[tuple[float, float]]) -> None:
    """The person tapped the 4 corners of the key: exact court from those + line alignment, then redo events + video."""
    d = DATA_DIR / game_id
    try:
        cfg = Config.load(d / "config.json")
        video = str(d / "video.mp4")
        info = probe(video)
        px = [(x * info.width, y * info.height) for x, y in points]
        frames = pipeline.load_frames(d / "tracks.json.gz")
        rims = frames[0].rims if frames else []
        rim_xy = max(rims, key=lambda r: r.conf).center if rims else None
        pairs = paint_landmarks(px, cfg.court, rim_xy)
        track = pipeline.calibrate(video, str(d), cfg, manual_points=pairs)
        _set_status(d, court_calibrated=True, court_conf=float(track.best().conf), court_method=track.best().method)
        _finish(d, cfg, video, game_id)
    except Exception as e:  # noqa: BLE001
        log.exception("game %s: court correction failed", game_id)
        _set_status(d, status="failed", error=f"court correction failed: {e}")


def _best_device() -> str | None:
    """NEXTRUN_DEVICE, else Apple-silicon GPU (mps) when present; None lets ultralytics use CUDA or the CPU."""
    if os.environ.get("NEXTRUN_DEVICE"):
        return os.environ["NEXTRUN_DEVICE"]
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:  # noqa: BLE001
        pass
    return None


def _fast_config(cfg: Config, video: str) -> None:
    try:
        fps = probe(video).fps
    except Exception:  # noqa: BLE001  (unreadable video: the pipeline reports the real error)
        return
    cfg.stride = max(1, round(fps / TARGET_FPS))
    cfg.max_frames = max(1, int(MAX_SECONDS * fps / cfg.stride))
    log.info("analysing the first %.0f s of the video (%d frames at stride %d)", MAX_SECONDS, cfg.max_frames, cfg.stride)
    cfg.models.max_imgsz, cfg.models.ball_max_imgsz = PLAYER_IMGSZ, MAX_IMGSZ
    cfg.court_calib_frames = min(cfg.court_calib_frames, 6)
    cfg.models.device = _best_device()


def process_game(game_id: str) -> None:
    """detect -> calibrate (optional: stats still work without a court, minus 2PT/3PT) -> analyze -> render."""
    d = DATA_DIR / game_id
    cfg = Config.load(d / "config.json")
    video = str(d / "video.mp4")
    _fast_config(cfg, video)
    cfg.save(d / "config.json")
    seen = {"players": 0, "ball": 0, "rim": 0}

    last = {"t": 0.0}

    def on_frame(n: int, total: int, img, f) -> None:
        seen["players"] = max(seen["players"], len(f.players))
        seen["ball"] += bool(f.ball_candidates)
        seen["rim"] += bool(f.rims)
        now = time.monotonic()  # the app polls a few times a second: writing status + preview every frame is wasted time
        if now - last["t"] < 0.4 and n + 1 < total:
            return
        last["t"] = now
        _set_status(d, frames_done=n + 1, frames_total=max(total, n + 1), progress=0.6 * (n + 1) / max(total, n + 1),
                    max_players=seen["players"], ball_frames=seen["ball"], rim_frames=seen["rim"])
        _preview(d, img, f)

    try:
        _set_status(d, status="detecting")
        try:
            pipeline.detect(video, str(d), cfg, progress=False, on_frame=on_frame)
        except Exception as e:  # noqa: BLE001
            if cfg.models.device != "mps":
                raise
            log.warning("game %s: Apple GPU failed (%s); retrying on the CPU", game_id, e)
            cfg.models.device = "cpu"
            seen.update(players=0, ball=0, rim=0)
            pipeline.detect(video, str(d), cfg, progress=False, on_frame=on_frame)
        _set_status(d, status="calibrating", progress=0.62, max_players=seen["players"], ball_frames=seen["ball"], rim_frames=seen["rim"])
        try:
            track = pipeline.calibrate(video, str(d), cfg, venue=_status(d).venue)
            conf = None
            try:
                conf = float(track.best().conf)
            except Exception:  # noqa: BLE001
                pass
            _set_status(d, court_calibrated=True, court_conf=conf, court_method=track.best().method, court=cfg.court.name)
            cfg.save(d / "config.json")  # the court type the video turned out to show
        except Exception as e:  # noqa: BLE001
            log.warning("game %s: court calibration failed: %s", game_id, e)
        _finish(d, cfg, video, game_id)
    except Exception as e:  # noqa: BLE001
        log.exception("game %s failed", game_id)
        _set_status(d, status="failed", error=str(e))


# --- routes ------------------------------------------------------------------------------------------
@app.get("/venues")
def venues() -> list[str]:
    """Saved camera profiles (data/venues/*.json)."""
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
    scoring: SCORING = Form("standard"),
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
    cfg = Config(court=CourtSpec.preset(court))
    if venue is not None:
        apply_venue(cfg, venue)
    cfg.events.scoring = scoring
    cfg.save(d / "config.json")
    s = GameStatus(id=game_id, status="queued", court=court, venue=venue, name=video.filename or "")
    (d / "status.json").write_text(s.model_dump_json())
    background.add_task(process_game, game_id)
    return s


@app.get("/games", response_model=list[GameStatus])
def list_games() -> list[GameStatus]:
    """Past uploads, newest first (results are kept on disk, so they survive restarts)."""
    dirs = [p for p in DATA_DIR.glob("*") if (p / "status.json").exists()] if DATA_DIR.is_dir() else []
    dirs.sort(key=lambda p: (p / "status.json").stat().st_mtime, reverse=True)
    return [_status(p) for p in dirs[:30]]


@app.get("/games/{game_id}", response_model=GameStatus)
def get_game(game_id: str):
    return _status(_dir(game_id))


@app.get("/games/{game_id}/preview")
def preview(game_id: str):
    """Latest frame the detection models have processed, with their boxes drawn on it (live while detecting)."""
    p = _dir(game_id) / "preview.jpg"
    if not p.exists():
        raise HTTPException(404, "no preview yet")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/games/{game_id}/video")
def annotated_video(game_id: str):
    """The finished video with every model's output drawn on it (players, ball trail, rims, court, score, minimap)."""
    d = _dir(game_id)
    for name in ("annotated_web.mp4", "annotated.mp4"):
        if (d / name).exists() and _status(d).has_video:
            return FileResponse(d / name, media_type="video/mp4")
    raise HTTPException(409, f"video not ready (status: {_status(d).status})")


class CourtPoints(BaseModel):
    # 4 taps on the painted key, as 0..1 fractions of the frame (x across, y down), going once around it
    points: list[tuple[float, float]]


@app.get("/games/{game_id}/frame")
def first_frame(game_id: str):
    """A still from the video (max 1280 px wide) for tapping court points on."""
    d = _dir(game_id)
    p = d / "first_frame.jpg"
    if not p.exists():
        try:
            img = read_frame(d / "video.mp4", 0)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(409, f"cannot read the video: {e}")
        s_ = 1280 / max(img.shape[:2])
        if s_ < 1:
            img = cv2.resize(img, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return FileResponse(p, media_type="image/jpeg")


@app.post("/games/{game_id}/court", response_model=GameStatus, status_code=202)
def set_court(game_id: str, body: CourtPoints, bg: BackgroundTasks) -> GameStatus:
    """Tap the 4 corners of the key (baseline corner, other baseline corner, free-throw corner beside it, last corner):
    recalibrates the court exactly, then re-runs events and re-renders the video."""
    d = _dir(game_id)
    if not (d / "tracks.json.gz").exists() or _status(d).status not in ("done", "failed"):
        raise HTTPException(409, "wait until processing has finished")
    if len(body.points) != 4 or any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in body.points):
        raise HTTPException(422, "send 4 points as fractions of the frame (0..1)")
    s = _set_status(d, status="calibrating", progress=0.62, error=None, has_video=False)
    bg.add_task(recalibrate_game, game_id, body.points)
    return s


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


@app.get("/games/{game_id}/summary")
def get_summary(game_id: str):
    """Everything the results screen shows: team totals, and a card per player (points, rebounds, assists, rating,
    rank, level, badges, shot log), best first."""
    d = _dir(game_id)
    if not (d / "boxscore.csv").exists():
        raise HTTPException(409, f"stats not ready (status: {_status(d).status})")
    events = json.loads((d / "events.json").read_text()) if (d / "events.json").exists() else []
    out = build_summary(pd.read_csv(d / "boxscore.csv"), events, Config.load(d / "config.json").events.scoring)
    out["charts"] = [n for n in ("shot_chart", "pass_network", "possession") if (d / f"{n}.png").exists()]
    return out



# --- scoring corrections -----------------------------------------------------------------------------------
class ShotFix(BaseModel):
    made: bool | None = None  # True = count it, False = not a basket
    points: int | None = Field(None, ge=1, le=3)
    player: str | None = None  # who to credit (a name from the box score)


class BasketAdd(BaseModel):
    t: float = Field(ge=0)  # seconds into the video
    player: str
    points: int | None = Field(None, ge=1, le=3)


class ScoringMode(BaseModel):
    mode: SCORING


def _reanalyze(game_id: str) -> dict:
    """Corrections change events only: redo the (cheap) analysis, not the detection or the annotated video."""
    d = _dir(game_id)
    if not (d / "tracks.json.gz").exists() or _status(d).status not in ("done", "failed"):
        raise HTTPException(409, "wait until processing has finished")
    pipeline.analyze(str(d), Config.load(d / "config.json"))
    return get_summary(game_id)


@app.post("/games/{game_id}/shots/{frame}")
def fix_shot(game_id: str, frame: int, body: ShotFix):
    """Correct one shot the AI logged: count a missed basket (made=true), remove a wrong one (made=false), change the
    points, or credit another player. `frame` is the shot's `frame` in the summary's scoring log."""
    d = _dir(game_id)
    items = ov.load_overrides(d / "overrides.json")
    prev = next((o for o in items if o.get("type") == "shot" and o.get("frame") == frame), {})
    new = {**prev, "type": "shot", "frame": frame, **body.model_dump(exclude_none=True)}
    ov.save_overrides(d / "overrides.json", ov.upsert(items, new))
    return _reanalyze(game_id)


@app.post("/games/{game_id}/baskets")
def add_basket(game_id: str, body: BasketAdd):
    """A basket the AI never saw at all: credit `player` with it at time `t`."""
    d = _dir(game_id)
    fps = json.loads((d / "video.json").read_text())["fps"] if (d / "video.json").exists() else 30.0
    frame = int(round(body.t * fps))
    new = {"type": "add", "frame": frame, "t": body.t, "player": body.player,
           **({"points": body.points} if body.points else {})}
    ov.save_overrides(d / "overrides.json", ov.upsert(ov.load_overrides(d / "overrides.json"), new))
    return _reanalyze(game_id)


@app.delete("/games/{game_id}/corrections/{kind}/{frame}")
def undo_correction(game_id: str, kind: Literal["shot", "add"], frame: int):
    """Undo a correction (kind 'shot' = a fixed shot, 'add' = a basket you added)."""
    d = _dir(game_id)
    ov.save_overrides(d / "overrides.json", ov.remove(ov.load_overrides(d / "overrides.json"), kind, frame))
    return _reanalyze(game_id)


@app.put("/games/{game_id}/scoring")
def set_scoring(game_id: str, body: ScoringMode):
    """Switch between standard (2 / 3) and 3x3 (1 / 2) scoring and recount."""
    d = _dir(game_id)
    cfg = Config.load(d / "config.json")
    cfg.events.scoring = body.mode
    cfg.save(d / "config.json")
    return _reanalyze(game_id)

@app.get("/games/{game_id}/chart/{name}")
def chart(game_id: str, name: str):
    if name not in ("shot_chart", "pass_network", "possession"):
        raise HTTPException(404, "unknown chart")
    p = _dir(game_id) / f"{name}.png"
    if not p.exists():
        raise HTTPException(404, "chart not available for this game")
    return FileResponse(p, media_type="image/png")


@app.get("/leaderboard")
def leaderboard():
    """Players you have named (tagged) summed over all processed games, best rating first."""
    rows: dict[str, dict] = {}
    for p in DATA_DIR.glob("*/boxscore.csv") if DATA_DIR.is_dir() else []:
        for r in build_summary(pd.read_csv(p), [])["players"]:
            if r["player"].startswith("Player ") or r["player"].startswith("track:"):
                continue  # default names are per game; only named players carry over
            agg = rows.setdefault(r["player"], {"player": r["player"], "games": 0, "PTS": 0, "REB": 0, "AST": 0, "RATING": 0.0})
            agg["games"] += 1
            for k in ("PTS", "REB", "AST", "RATING"):
                agg[k] += r[k]
    return sorted(rows.values(), key=lambda r: -r["RATING"])


@app.get("/games/{game_id}/events")
def get_events(game_id: str, include_dribbles: bool = False):
    """Timestamped event log (shots, rebounds, assists, passes, steals, turnovers...)."""
    p = _dir(game_id) / "events.json"
    if not p.exists():
        raise HTTPException(409, "events not ready")
    events = json.loads(p.read_text())
    return [e for e in events if include_dribbles or e["type"] != "dribble"]
