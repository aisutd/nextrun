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
from fastapi.responses import FileResponse, Response
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
MAX_SECONDS = float(os.environ.get("NEXTRUN_MAX_SECONDS", 40))  # analyze the first 40 seconds by default
TARGET_FPS = float(os.environ.get("NEXTRUN_TARGET_FPS", 15))  # analyse ~15 frames/s (every 2nd frame of a 30 fps clip)
MAX_IMGSZ = int(os.environ.get("NEXTRUN_MAX_IMGSZ", 1280))  # ball/rim model input long side; 4K frames are shrunk to this
PLAYER_IMGSZ = int(os.environ.get("NEXTRUN_PLAYER_IMGSZ", 1920))  # preserve detail for distant players in wide outdoor footage
COURTS = Literal["highschool", "fiba", "nba", "ncaa"]
SCORING = Literal["standard", "3x3"]  # standard: 2 inside the arc / 3 outside; 3x3: 1 / 2
Status = Literal["queued", "detecting", "calibrating", "analyzing", "rendering", "done", "failed", "cancelled"]

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


class _Cancelled(Exception):
    """The user pressed Stop: the worker unwinds and deletes the game."""


def _cancelled(d: Path) -> bool:
    return (d / "cancel").exists()


def _check_cancel(d: Path) -> None:
    if _cancelled(d):
        raise _Cancelled


def _set_status(d: Path, **kw) -> GameStatus:
    if _cancelled(d):  # a progress write racing a Stop must not flip the game back to running
        kw["status"] = "cancelled"
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
    _check_cancel(d)
    _set_status(d, status="analyzing", progress=0.75)
    analysis, ids, frames = pipeline.analyze(str(d), cfg)
    _check_cancel(d)
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
    except _Cancelled:
        shutil.rmtree(d, ignore_errors=True)
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
    cfg.max_frames = max(1, int(MAX_SECONDS * fps / cfg.stride)) if MAX_SECONDS > 0 else None
    if MAX_SECONDS > 0:
        log.info("analysing the first %.0f s of the video (%d frames at stride %d)", MAX_SECONDS, cfg.max_frames, cfg.stride)
    else:
        log.info("analysing the full video (%d fps sampling, stride %d)", TARGET_FPS, cfg.stride)
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
        _check_cancel(d)
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
        _check_cancel(d)
        _set_status(d, status="detecting")
        try:
            pipeline.detect(video, str(d), cfg, progress=False, on_frame=on_frame)
        except _Cancelled:
            raise
        except Exception as e:  # noqa: BLE001
            if cfg.models.device != "mps":
                raise
            log.warning("game %s: Apple GPU failed (%s); retrying on the CPU", game_id, e)
            cfg.models.device = "cpu"
            seen.update(players=0, ball=0, rim=0)
            pipeline.detect(video, str(d), cfg, progress=False, on_frame=on_frame)
        _check_cancel(d)
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
    except _Cancelled:
        log.info("game %s: stopped by the user", game_id)
        shutil.rmtree(d, ignore_errors=True)
    except Exception as e:  # noqa: BLE001
        if _cancelled(d):
            shutil.rmtree(d, ignore_errors=True)
            return
        log.exception("game %s failed", game_id)
        _set_status(d, status="failed", error=str(e))


# --- routes ------------------------------------------------------------------------------------------
@app.get("/venues")
def venues() -> list[str]:
    """Saved camera profiles (data/venues/*.json)."""
    return list_venues()


@app.get("/metrics")
def model_metrics() -> dict:
    """Accuracy of every model (precision / recall / F1, mAP@0.5 and @0.5:0.95, IoU rule, false positive / negative
    reductions vs the previous version), from the recorded test-set evaluations in backend/eval/."""
    from nextrun_cv import model_metrics as mm

    try:
        return mm.report()
    except FileNotFoundError as e:
        raise HTTPException(404, f"evaluation results missing: {e.filename}")


@app.get("/metrics/benchmark")
def metrics_benchmark() -> dict:
    """Latest inference-speed measurement on this machine (and whether one is running)."""
    from nextrun_cv import model_metrics as mm

    return mm.benchmark_state()


@app.post("/metrics/benchmark", status_code=202)
def metrics_benchmark_start() -> dict:
    """Time every active model on a real frame on this machine, in the background; poll GET /metrics/benchmark."""
    from nextrun_cv import model_metrics as mm

    return mm.start_benchmark(DATA_DIR, _models_lock)


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


# --- live camera ---------------------------------------------------------------------------------------
# The app streams camera frames one at a time (send the next once the last answer is back). Tracks persist
# between frames so IDs stay stable; the court is calibrated from the live feed and re-tried until it sticks.
LIVE_IMGSZ = int(os.environ.get("NEXTRUN_LIVE_IMGSZ", 960))
LIVE_CALIB_EVERY = 30  # frames between court attempts while uncalibrated
_live = {"nr": None, "frame": 0, "t0": 0.0, "last_calib": -LIVE_CALIB_EVERY, "fps": 0.0, "record": False, "times": []}
# Phones (Expo Go) cannot record video while grabbing frames, so a live session can keep its frames here instead;
# POST /live/save turns them into a video and runs the full upload pipeline on it.
LIVE_DIR = DATA_DIR.parent / "live"


class _LiveIds:
    """Stable player ids for a live feed. Frames arrive only a few times a second, which the video tracker
    (built for every-frame input) handles badly - it drops players until they match twice. Here every
    detection is kept and gets the id of the nearest recent player (distance in body heights)."""

    MAX_DIST = 1.2  # body heights a player can move between two live frames
    MAX_AGE = 20  # frames a lost id is remembered

    def __init__(self) -> None:
        self.tracks: dict[int, tuple[float, float, float, int]] = {}  # id -> cx, cy, h, last frame
        self.next_id = 1

    def assign(self, boxes: list[tuple[float, float, float, float]], confs: list[float], idx: int) -> list[int]:
        self.tracks = {k: v for k, v in self.tracks.items() if idx - v[3] <= self.MAX_AGE}
        pairs = []
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            cx, cy, h = (x1 + x2) / 2, (y1 + y2) / 2, max(1.0, y2 - y1)
            for k, (tx, ty, th, _) in self.tracks.items():
                d = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5 / max(h, th)
                if d < self.MAX_DIST:
                    pairs.append((d, i, k))
        ids: dict[int, int] = {}
        used: set[int] = set()
        for d, i, k in sorted(pairs):
            if i not in ids and k not in used:
                ids[i] = k
                used.add(k)
        out = []
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            if i not in ids:
                ids[i] = self.next_id
                self.next_id += 1
            self.tracks[ids[i]] = ((x1 + x2) / 2, (y1 + y2) / 2, max(1.0, y2 - y1), idx)
            out.append(ids[i])
        return out


_live_ids = _LiveIds()

# Live game events: every live frame is kept, and a background thread re-runs the same offline analysis the
# uploads use (ball tracking, court fusion, possession, shots / makes, rebounds, assists) over the session so
# far, about once a second. Each /live/frame answer carries the latest result.
LIVE_MAX_FRAMES = int(os.environ.get("NEXTRUN_LIVE_MAX_FRAMES", 6000))  # ~15 min at 6-7 frames/s
LIVE_ANALYZE_EVERY = 1.0  # seconds between event passes
_live_buf: list = []  # raw FrameStates (before fusion), in order
_live_events = {"session": 0, "result": None, "busy": False, "last": 0.0}
_live_buf_lock = threading.Lock()

STAT_KEYS = ["PTS", "REB", "AST", "FGM", "FGA", "3PM", "3PA", "OREB", "DREB", "STL", "TOV", "PASS", "TOUCH"]


def _live_analysis(frames: list, calib, cfg: Config) -> dict:
    """The upload pipeline's event pass (minus identity tagging) over the live frames so far."""
    from nextrun_cv import fusion
    from nextrun_cv.detect.ball_track import drop_implausible_rims, track_ball
    from nextrun_cv.events.analyzer import GameAnalyzer
    from nextrun_cv.stats.boxscore import box_score

    if len(frames) < 4:
        return None
    span = frames[-1].t - frames[0].t
    fps = (len(frames) - 1) / span if span > 0 else 6.0
    drop_implausible_rims(frames)
    track_ball(frames, cfg.ball)
    fusion.fuse(frames, calib, cfg)
    analysis = GameAnalyzer(cfg, fps, None, calib).analyze(frames)
    ev = [e for e in analysis.events if e.type != "dribble"]
    shots = [e for e in ev if e.type == "shot"]
    bs = box_score(analysis)
    players = []
    for r in bs.to_dict("records"):
        if not (r["FGA"] or r["REB"] or r["AST"] or r["TOUCH"]):
            continue
        name = str(r["player"])
        players.append({"player": name, "track_id": int(name.split(":")[1]) if name.startswith("track:") else None,
                        **{k: int(r[k]) for k in STAT_KEYS}})
    players.sort(key=lambda r: (-r["PTS"], -r["REB"], -r["AST"], -r["TOUCH"]))

    def feed(e) -> dict:
        d = {"type": e.type, "t": round(float(e.t), 1), "player": e.player}
        if e.type == "shot":
            d.update(made=bool(e.data.get("made")), three=bool(e.data.get("three")),
                     points=int(e.data.get("points", 0)) if e.data.get("made") else 0, dunk=bool(e.data.get("dunk")))
        elif e.type == "rebound":
            d["offensive"] = bool(e.data.get("offensive"))
        elif e.type == "assist":
            d["to"] = e.data.get("scorer") or e.data.get("to")
        return d

    made = [e for e in shots if e.data.get("made")]
    return {
        "frames": len(frames),
        "fps": round(fps, 1),
        "totals": {
            "points": int(sum(e.data.get("points", 2) for e in made)),
            "shots": len(shots),
            "makes": len(made),
            "misses": len(shots) - len(made),
            "threes": sum(1 for e in made if e.data.get("three")),
            "rebounds": sum(1 for e in ev if e.type == "rebound"),
            "assists": sum(1 for e in ev if e.type == "assist"),
            "possessions": sum(1 for e in ev if e.type == "possession_gain"),
            "passes": sum(1 for e in ev if e.type == "pass"),
            "steals": sum(1 for e in ev if e.type == "steal"),
            "turnovers": sum(1 for e in ev if e.type == "turnover"),
        },
        "players": players[:12],
        "events": [feed(e) for e in ev if e.type in ("shot", "rebound", "assist", "steal", "turnover")][-12:][::-1],
    }


def _live_analyze_bg(session: int) -> None:
    import copy

    try:
        with _live_buf_lock:
            frames = copy.deepcopy(_live_buf)
        nr = _live["nr"]
        calib = nr.calib if nr is not None else None
        out = _live_analysis(frames, calib, nr.cfg if nr is not None else Config())
        if session == _live_events["session"] and out is not None:
            _live_events["result"] = out
    except Exception:  # noqa: BLE001  (a failed pass just keeps the previous numbers)
        log.exception("live event analysis failed")
    finally:
        _live_events["busy"] = False


def _live_kick_analysis() -> None:
    now = time.monotonic()
    if _live_events["busy"] or now - _live_events["last"] < LIVE_ANALYZE_EVERY:
        return
    _live_events.update(busy=True, last=now)
    threading.Thread(target=_live_analyze_bg, args=(_live_events["session"],), daemon=True).start()


def _live_detect(nr, img: np.ndarray, idx: int, t: float):
    """Players (pose model, plain detection + live ids), then the ball/rim detector."""
    from nextrun_cv.detect.players import dedupe_players
    from nextrun_cv.schema import FrameState, PlayerObs

    m = nr.cfg.models
    res = nr.players.model.predict(img, classes=[0], conf=m.player_conf, imgsz=m.input_size(img.shape), device=m.device,
                                   iou=m.player_iou, max_det=m.player_max_det, agnostic_nms=True,
                                   half=nr.players._half, verbose=False)[0]
    players = []
    if res.boxes is not None and len(res.boxes):
        xyxy = res.boxes.xyxy.cpu().numpy()
        confs = res.boxes.conf.cpu().numpy()
        kps = res.keypoints.data.cpu().numpy() if res.keypoints is not None else None
        keep = [i for i in range(len(xyxy)) if xyxy[i][3] - xyxy[i][1] >= m.player_min_height * img.shape[0]]
        players = [PlayerObs(track_id=-1, bbox=tuple(float(v) for v in xyxy[i]), conf=float(confs[i]),
                             keypoints=None if kps is None else kps[i].astype(float)) for i in keep]
        players = dedupe_players(players, m.player_dedupe_iou)
        for p, k in zip(players, _live_ids.assign([p.bbox for p in players], [p.conf for p in players], idx)):
            p.track_id = k
    balls, rims = nr.ball_hoop.detect(img, [p.bbox for p in players])
    ball = max(balls, key=lambda b: b.conf) if balls else None
    return FrameState(idx, t, players, ball, balls, rims)


def _live_models():
    if _live["nr"] is None:
        from nextrun_cv.integration import NextRun

        cfg = Config()
        cfg.models.device = _best_device()
        cfg.models.max_imgsz = cfg.models.ball_max_imgsz = LIVE_IMGSZ
        _live["nr"] = NextRun(cfg)
    return _live["nr"]


@app.post("/live/start")
def live_start(record: bool = False) -> dict:
    """New live session: forget tracks and the court calibration (loads the models on first use).
    `record=true` keeps every frame so the session can be saved as a game afterwards (POST /live/save)."""
    with _models_lock:
        shutil.rmtree(LIVE_DIR, ignore_errors=True)
        if record:
            LIVE_DIR.mkdir(parents=True, exist_ok=True)
        _live_models().reset()
        _live_ids.__init__()
        with _live_buf_lock:
            _live_buf.clear()
        _live_events.update(session=_live_events["session"] + 1, result=None, last=0.0)
        _live.update(frame=0, t0=time.monotonic(), last_calib=-LIVE_CALIB_EVERY, fps=0.0, record=record, times=[])
    return {"ok": True, "device": _live["nr"].cfg.models.device or "auto"}


@app.post("/live/frame")
def live_frame(image: UploadFile = File(...)) -> dict:
    """One camera frame through every model: players (tracked, with pose keypoints), ball, rims, court,
    2PT / 3PT zones and who has the ball once the court is known."""
    from nextrun_cv import fusion
    from nextrun_cv.court.base import CourtNotFound

    raw = image.file.read()
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "not an image")
    with _models_lock:
        nr = _live_models()
        start = time.monotonic()
        idx = _live["frame"]
        if _live["record"] and len(_live["times"]) < LIVE_MAX_FRAMES:
            (LIVE_DIR / f"{len(_live['times']):06d}.jpg").write_bytes(raw)
            _live["times"].append(start - _live["t0"])
        f = _live_detect(nr, img, idx, start - _live["t0"])
        import copy

        with _live_buf_lock:
            _live_buf.append(copy.deepcopy(f))
            del _live_buf[:-LIVE_MAX_FRAMES]
        if nr.calib is None and idx - _live["last_calib"] >= LIVE_CALIB_EVERY:
            _live["last_calib"] = idx
            try:
                nr.calibrate([img], [f])
            except CourtNotFound:
                nr.calib = None
            except Exception as e:  # noqa: BLE001  (calibration is best effort while live)
                log.warning("live court calibration failed: %s", e)
                nr.calib = None
        fusion.fuse([f], nr.calib, nr.cfg)
        out = nr.describe(f)
        kps = {p.track_id: p.keypoints for p in f.players if p.keypoints is not None}
        for p in out["players"]:
            k = kps.get(p["track_id"])
            if k is not None:
                p["keypoints"] = [[round(float(x), 1), round(float(y), 1), round(float(c), 2)] for x, y, c in k]
        out["ball_candidates"] = [{"xy": [round(v, 1) for v in b.xy], "r": round(float(b.radius), 1),
                                   "conf": round(float(b.conf), 2)} for b in f.ball_candidates]
        if f.ball is not None and out["ball"] is not None:
            out["ball"]["r"] = round(float(f.ball.radius), 1)
            out["ball"]["conf"] = round(float(f.ball.conf), 2)
        ms = (time.monotonic() - start) * 1000
        _live["fps"] = 0.8 * _live["fps"] + 0.2 * (1000 / max(ms, 1)) if idx else 1000 / max(ms, 1)
        _live["frame"] = idx + 1
        out.update(width=img.shape[1], height=img.shape[0], ms=round(ms), model_fps=round(_live["fps"], 1),
                   game=_live_events["result"])
    _live_kick_analysis()
    return out


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
    webm = (video.filename or "").lower().endswith(".webm") or "webm" in (video.content_type or "")
    raw = d / ("upload.webm" if webm else "video.mp4")
    with open(raw, "wb") as fh:
        while chunk := video.file.read(1 << 20):
            fh.write(chunk)
    if webm:  # live recordings from the browser: no reliable fps/duration in the header, so remux to a 30 fps mp4
        exe = _ffmpeg()
        if exe is None:
            raise HTTPException(500, "ffmpeg not found (pip install imageio-ffmpeg)")
        r = subprocess.run([exe, "-y", "-i", str(raw), "-r", "30", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", str(d / "video.mp4")],
                           capture_output=True)
        if r.returncode != 0:
            raise HTTPException(400, "could not read the recording: " + r.stderr.decode(errors="ignore")[-200:])
        raw.unlink(missing_ok=True)
    return _queue_game(d, background, court, venue, scoring, video.filename or "")


def _queue_game(d: Path, background: BackgroundTasks, court: str, venue: str | None, scoring: str, name: str) -> GameStatus:
    """d holds video.mp4: write its config + status and start processing in the background."""
    cfg = Config(court=CourtSpec.preset(court))
    if venue is not None:
        apply_venue(cfg, venue)
    cfg.events.scoring = scoring
    cfg.save(d / "config.json")
    s = GameStatus(id=d.name, status="queued", court=court, venue=venue, name=name)
    (d / "status.json").write_text(s.model_dump_json())
    background.add_task(process_game, d.name)
    return s


@app.post("/live/save", response_model=GameStatus, status_code=202)
def live_save(background: BackgroundTasks, court: COURTS = Form("highschool"), scoring: SCORING = Form("standard")):
    """End a recorded live session (POST /live/start?record=true): its frames become a video at the rate they
    were captured, which then goes through the same full analysis as an upload. Poll GET /games/{id}."""
    with _models_lock:
        times, _live["record"], _live["times"] = list(_live["times"]), False, []
    frames = sorted(LIVE_DIR.glob("*.jpg"))[: len(times)] if LIVE_DIR.is_dir() else []
    if len(frames) < 8:
        shutil.rmtree(LIVE_DIR, ignore_errors=True)
        raise HTTPException(400, "the live session was too short to save (record for a few seconds)")
    span = times[len(frames) - 1] - times[0]
    fps = min(30.0, max(1.0, (len(frames) - 1) / span)) if span > 0 else 5.0
    first = cv2.imread(str(frames[0]))
    h, w = (first.shape[0] // 2) * 2, (first.shape[1] // 2) * 2
    game_id = uuid.uuid4().hex[:12]
    d = DATA_DIR / game_id
    d.mkdir(parents=True)
    out = cv2.VideoWriter(str(d / "video.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        img = cv2.imread(str(f))
        if img is None:
            continue
        if img.shape[:2] != (h, w):  # the phone was turned mid-session: fit it to the first frame's size
            img = cv2.resize(img, (w, h))
        out.write(img)
    out.release()
    shutil.rmtree(LIVE_DIR, ignore_errors=True)
    name = f"live-{time.strftime('%Y-%m-%d-%H-%M-%S')}.mp4"
    return _queue_game(d, background, court, None, scoring, name)


@app.get("/games", response_model=list[GameStatus])
def list_games() -> list[GameStatus]:
    """Past uploads, newest first (results are kept on disk, so they survive restarts)."""
    dirs = [p for p in DATA_DIR.glob("*") if (p / "status.json").exists()] if DATA_DIR.is_dir() else []
    dirs.sort(key=lambda p: (p / "status.json").stat().st_mtime, reverse=True)
    return [s for s in (_status(p) for p in dirs[:30]) if s.status != "cancelled"]


@app.get("/games/{game_id}", response_model=GameStatus)
def get_game(game_id: str):
    return _status(_dir(game_id))


@app.post("/games/{game_id}/cancel", status_code=204)
def cancel_game(game_id: str) -> None:
    """Stop an upload that is still processing and throw it away (for when the wrong video was picked).
    The worker notices at the next frame or stage and deletes the folder; a finished game is deleted now."""
    d = _dir(game_id)
    if _status(d).status in ("done", "failed", "cancelled"):
        shutil.rmtree(d, ignore_errors=True)
        return
    (d / "cancel").touch()
    _set_status(d, status="cancelled")


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


def _team_selection_frame(game_id: str, time_s: float):
    """Return the nearest analyzed frame with normalized player boxes for the team picker."""
    d = _dir(game_id)
    tracks = d / "tracks.json.gz"
    if not tracks.exists():
        raise HTTPException(409, "video analysis is not finished yet")
    frames = pipeline.load_frames(tracks)
    if not frames:
        raise HTTPException(409, "no analyzed frames are available")
    # A single sampled frame can miss a player due to blur or occlusion. Pick the clearest frame
    # near the requested time, then union real tracked identities from nearby samples so a brief
    # missed detection doesn't make a player impossible to assign.
    target = max(0.0, time_s)
    nearby = [f for f in frames if abs(f.t - target) <= 2.0]
    frame = max(nearby or frames, key=lambda f: (len(f.players), -abs(f.t - target)))
    info = json.loads((d / "video.json").read_text())
    width, height = int(info["width"]), int(info["height"])
    spans = {}
    for f in frames:
        for p in f.players:
            spans[p.track_id] = spans.get(p.track_id, 0) + 1
    # Use the closest box for each identity within half a second of the displayed image.
    # Track IDs are global, so selecting these still tags the same player for scoring.
    observed = {}
    for candidate in frames:
        if abs(candidate.t - frame.t) > 0.5:
            continue
        for p in candidate.players:
            old = observed.get(p.track_id)
            if old is None or abs(candidate.t - frame.t) < abs(old[0] - frame.t):
                observed[p.track_id] = (candidate.t, p)
    players = [
        {"track_id": p.track_id, "name": f"Player {p.track_id}", "frames_seen": spans.get(p.track_id, 1),
         "bbox": [p.bbox[0] / width, p.bbox[1] / height, p.bbox[2] / width, p.bbox[3] / height]}
        for _, p in observed.values()
    ]
    return d, frame, (width, height), players


@app.get("/games/{game_id}/team-selection")
def team_selection(game_id: str, time_s: float = 0.0):
    d, frame, (width, height), players = _team_selection_frame(game_id, time_s)
    info = json.loads((d / "video.json").read_text())
    duration_s = info["n_frames"] / max(1.0, info["fps"])
    return {"time_s": frame.t, "duration_s": duration_s, "width": width, "height": height,
            "players": players}


@app.get("/games/{game_id}/team-selection/frame")
def team_selection_frame(game_id: str, time_s: float = 0.0):
    d, frame, (width, height), players = _team_selection_frame(game_id, time_s)
    img = read_frame(str(d / "video.mp4"), frame.idx)
    scale = min(1.0, 1600 / max(img.shape[:2]))
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    for player in players:
        x1, y1, x2, y2 = player["bbox"]
        x1, x2 = round(x1 * img.shape[1]), round(x2 * img.shape[1])
        y1, y2 = round(y1 * img.shape[0]), round(y2 * img.shape[0])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 255), max(2, round(img.shape[1] / 800)))
        cv2.rectangle(img, (x1, max(0, y1 - 34)), (x1 + 94, y1), (8, 15, 28), -1)
        cv2.putText(img, f"ID {player['track_id']}", (x1 + 5, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX,
                    max(0.55, img.shape[1] / 2200), (255, 255, 255), 2, cv2.LINE_AA)
    ok, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise HTTPException(500, "could not render the selected frame")
    return Response(encoded.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


def _team_roster(game_id: str) -> tuple[Path, list[dict]]:
    """Every person tracked anywhere in the analysed video (not just one frame), grouped into identities the same way
    the stats are (lost tracks stitched, re-linked by appearance), with whether they were on the court, the current
    team (a saved choice, else the jersey-colour guess) and the frame with their clearest full-body box."""
    from nextrun_cv import fusion

    d = _dir(game_id)
    if not (d / "tracks.json.gz").exists():
        raise HTTPException(409, "video analysis is not finished yet")
    cfg = Config.load(d / "config.json")
    tags = json.loads((d / "tags.json").read_text()) if (d / "tags.json").exists() else {}
    ids, frames, calib, _fps, _emb, _view, _vc = pipeline.identify(d, cfg)
    if tags:
        # saved picks cover every track of every player; a track they don't name means the tracking was improved since
        # (e.g. a swapped id got split), so the old picks no longer line up: start again from the colour guesses
        tracks_now = {p.track_id for f in frames for p in f.players}
        if any(str(t) not in tags for t in tracks_now if sum(1 for f in frames for p in f.players if p.track_id == t) >= 5):
            tags = {}
            ids, frames, calib, _fps, _emb, _view, _vc = pipeline.identify(d, cfg, tags={})
    info = json.loads((d / "video.json").read_text())
    W, H = int(info["width"]), int(info["height"])
    groups: dict[str, dict] = {}
    for f in frames:
        for p in f.players:
            name = ids.player(p.track_id)
            g = groups.setdefault(name, {"tracks": set(), "n": 0, "on": 0, "mapped": 0, "best": None, "first_t": f.t})
            g["tracks"].add(p.track_id)
            g["n"] += 1
            if p.court_xy is not None:
                g["mapped"] += 1
                g["on"] += fusion.on_court(p.court_xy, calib.spec if calib is not None else cfg.court, 0.5, cfg.fusion.play_area)
            # clearest view: a tall, confident box that is not cut off by the frame edge
            x1, y1, x2, y2 = p.bbox
            edge = x1 <= 2 or y1 <= 2 or x2 >= W - 2 or y2 >= H - 2
            score = p.height * p.conf * (0.5 if edge else 1.0)
            if g["best"] is None or score > g["best"][0]:
                g["best"] = (score, f.idx, p.track_id, p.bbox)
    min_n = max(5, int(0.02 * len(frames)))
    out = []
    for name, g in groups.items():
        if g["n"] < min_n:
            continue  # a flicker of a detection, not a person
        on_court = g["on"] / g["mapped"] >= 0.5 if g["mapped"] >= 5 else None
        tag = next((tags[str(t)] for t in sorted(g["tracks"]) if str(t) in tags), None)
        if tag is not None:
            team, saved = tag.get("team"), True
        else:
            team, saved = (ids.player_team.get(name) if on_court is not False else None), False
        _, fidx, tid, bbox = g["best"]
        out.append({"key": min(g["tracks"]), "name": name, "track_ids": sorted(g["tracks"]), "frames_seen": g["n"],
                    "seen_s": round(g["n"] / max(1e-6, _fps), 1), "first_s": round(g["first_t"], 1),
                    "on_court": on_court, "team": team, "saved": saved,
                    "thumb_frame": fidx, "thumb_bbox": [round(v, 1) for v in bbox]})
    out.sort(key=lambda r: (r["on_court"] is False, -r["frames_seen"]))
    return d, out


@app.get("/games/{game_id}/team-roster")
def team_roster(game_id: str):
    """Players for the team picker: everyone seen in the video, on-court people first."""
    d, players = _team_roster(game_id)
    return {"players": players, "has_court": (d / "court_track.json").exists() or (d / "court.json").exists()}


@app.get("/games/{game_id}/team-roster/thumb")
def team_roster_thumb(game_id: str, frame: int, x1: float, y1: float, x2: float, y2: float):
    """A cut-out of one player (their clearest frame) for the team picker card."""
    d = _dir(game_id)
    cache = d / "thumbs" / f"{frame}_{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}.jpg"
    if not cache.exists():
        try:
            img = read_frame(str(d / "video.mp4"), int(frame))
        except Exception as e:  # noqa: BLE001
            raise HTTPException(409, f"cannot read the video: {e}")
        h, w = img.shape[:2]
        bw, bh = x2 - x1, y2 - y1
        # a little context around the box, as a 3:4 portrait
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        ch = bh * 1.25
        cw = max(bw * 1.4, ch * 0.75)
        a, b = int(max(0, cx - cw / 2)), int(max(0, cy - ch / 2))
        c, e_ = int(min(w, cx + cw / 2)), int(min(h, cy + ch / 2))
        if c <= a or e_ <= b:
            raise HTTPException(422, "empty crop")
        crop = img[b:e_, a:c]
        s_ = 320 / crop.shape[0]
        crop = cv2.resize(crop, None, fx=s_, fy=s_, interpolation=cv2.INTER_AREA if s_ < 1 else cv2.INTER_CUBIC)
        cache.parent.mkdir(exist_ok=True)
        cv2.imwrite(str(cache), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return FileResponse(cache, media_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})


@app.get("/games/{game_id}/roster")
def get_roster(game_id: str):
    """Tracked people with their current names and auto/manual team guesses for the upload editor."""
    d = _dir(game_id)
    tracks = d / "tracks.json.gz"
    if not tracks.exists():
        raise HTTPException(409, "detection has not finished yet")
    from nextrun_cv.identity.tagging import track_spans

    identities = json.loads((d / "identities.json").read_text()) if (d / "identities.json").exists() else {}
    tags = json.loads((d / "tags.json").read_text()) if (d / "tags.json").exists() else {}
    names = identities.get("track_to_player", {})
    player_teams = identities.get("player_team", {})
    frames = pipeline.load_frames(tracks)
    spans = track_spans(frames)
    players = []
    for track_id, span in sorted(spans.items(), key=lambda item: (item[1].start, item[0])):
        if span.n < 5:
            continue
        tag = tags.get(str(track_id), {})
        name = tag.get("name") or names.get(str(track_id)) or f"Player {track_id}"
        players.append({
            "track_id": track_id,
            "name": name,
            "team": tag.get("team") if "team" in tag else player_teams.get(name),
            "frames_seen": span.n,
            "tagged": bool(tag),
        })
    return {"players": players}


def _render_tagged_game(game_id: str, cfg: Config, analysis, ids, frames) -> None:
    """Refresh the annotated video after team/player tags change, without running any detection models again."""
    d = DATA_DIR / game_id
    video = str(d / "video.mp4")
    try:
        (d / "annotated_web.mp4").unlink(missing_ok=True)
        raw = pipeline.render(video, str(d), cfg, analysis, ids, frames)
        if ffmpeg_exe() is None:
            _web_video(raw, d / "annotated_web.mp4")
        _set_status(d, status="done", progress=1.0, has_video=True, render_error=None, video_version=time.time())
    except Exception as e:  # noqa: BLE001
        log.warning("game %s: render after roster update failed: %s", game_id, e)
        _set_status(d, status="done", progress=1.0, has_video=False, render_error=str(e)[:300])


@app.put("/games/{game_id}/tags")
def set_tags(game_id: str, tags: dict[str, Tag], background: BackgroundTasks):
    """{track_id: {name, team}} -> re-runs analysis (cheap, no re-detection) and returns the new stats."""
    d = _dir(game_id)
    if not (d / "tracks.json.gz").exists():
        raise HTTPException(409, "detection has not finished yet")
    (d / "tags.json").write_text(json.dumps({k: v.model_dump() for k, v in tags.items()}, indent=2))
    cfg = Config.load(d / "config.json")
    analysis, ids, frames = pipeline.analyze(str(d), cfg)
    _set_status(d, status="rendering", progress=0.95, has_video=False, render_error=None)
    background.add_task(_render_tagged_game, game_id, cfg, analysis, ids, frames)
    return get_summary(game_id)


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
