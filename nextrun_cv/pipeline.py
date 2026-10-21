"""End-to-end pipeline, split into resumable stages that write to one output directory:

  detect    video -> tracks.json.gz (players+pose, ball, rims), appearance.json, tagging_frame.jpg
  calibrate video -> court.json   (keypoints / lines / manual)
  [user writes tags.json from tagging_frame.jpg]
  analyze   -> identities.json, events.json, flights.json, boxscore.csv, team_totals.csv, charts
  render    -> annotated.mp4

Detection is the only GPU-heavy stage; re-running analyze with new tags or thresholds is cheap."""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path

import cv2
import numpy as np

from . import fusion
from .config import Config
from .court.auto import calibrate_court
from .court.base import CourtCalib
from .detect.ball_track import stabilize_rims, track_ball
from .events.analyzer import GameAnalysis, GameAnalyzer
from .identity.appearance import AppearanceBank
from .identity.tagging import Identities, best_tagging_frame, load_tags, resolve_identities, tagging_sheet
from .schema import FrameState, frames_from_records, frames_to_records
from .stats.boxscore import box_score, team_totals
from .video import iter_frames, probe, read_frame

log = logging.getLogger(__name__)


def _out(out_dir) -> Path:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_frames(frames: list[FrameState], path: Path) -> None:
    with gzip.open(path, "wt") as fh:
        json.dump(frames_to_records(frames), fh)


def load_frames(path: Path) -> list[FrameState]:
    with gzip.open(path, "rt") as fh:
        return frames_from_records(json.load(fh))


# ---------------------------------------------------------------------------------------------------
def detect(video: str, out_dir: str, cfg: Config | None = None, progress: bool = True) -> list[FrameState]:
    from .integration import NextRun

    cfg = cfg or Config()
    out = _out(out_dir)
    info = probe(video)
    models = NextRun(cfg)
    bank = AppearanceBank(cfg.teams.sample_every)
    frames: list[FrameState] = []
    total = info.n_frames // cfg.stride if cfg.max_frames is None else cfg.max_frames
    for n, (idx, img) in enumerate(iter_frames(video, cfg.stride, max_frames=cfg.max_frames)):
        f = models.detect(img, idx, idx / info.fps)
        f.ball = None  # chosen by the ball tracker below, from all candidates over time
        frames.append(f)
        bank.add(idx, img, f.players)
        if progress and n % 100 == 0:
            log.info("detect %d/%d frames", n, total)
    track_ball(frames, cfg.ball)
    stabilize_rims(frames)
    save_frames(frames, out / "tracks.json.gz")
    (out / "appearance.json").write_text(json.dumps(bank.to_dict()))
    (out / "video.json").write_text(json.dumps({**info.__dict__, "stride": cfg.stride}))
    k = best_tagging_frame(frames)
    cv2.imwrite(str(out / "tagging_frame.jpg"), tagging_sheet(read_frame(video, frames[k].idx), frames[k]))
    log.info("detect done: %d frames, tagging frame %d", len(frames), frames[k].idx if frames else -1)
    return frames


def calibrate(video: str, out_dir: str, cfg: Config | None = None, manual_points=None) -> CourtCalib:
    cfg = cfg or Config()
    out = _out(out_dir)
    tracks = out / "tracks.json.gz"
    frames = load_frames(tracks) if tracks.exists() else []
    n = min(cfg.court_calib_frames, max(1, len(frames))) if frames else cfg.court_calib_frames
    picks = [frames[i] for i in np.linspace(0, len(frames) - 1, n).astype(int)] if frames else []
    imgs = [read_frame(video, f.idx) for f in picks] if picks else [read_frame(video, 0)]
    ignore = [[p.bbox for p in f.players] for f in picks] if picks else None
    rims = frames[0].rims if frames else []
    rim_xy = max(rims, key=lambda r: r.conf).center if rims else None
    rims_per_frame = [f.rims for f in picks] if picks else None
    calib = calibrate_court(imgs, cfg, manual_points, ignore, rim_xy, rims_per_frame)
    calib.save(out / "court.json")
    return calib


def analyze(out_dir: str, cfg: Config | None = None, tags=None) -> tuple[GameAnalysis, Identities, list[FrameState]]:
    cfg = cfg or Config()
    out = _out(out_dir)
    frames = load_frames(out / "tracks.json.gz")
    vinfo = json.loads((out / "video.json").read_text())
    fps = vinfo["fps"] / vinfo.get("stride", 1)
    emb = {int(k): np.asarray(v) for k, v in json.loads((out / "appearance.json").read_text()).items()}
    calib = CourtCalib.load(out / "court.json") if (out / "court.json").exists() else None
    if calib is not None:
        calib.spec = cfg.court
    report = fusion.fuse(frames, calib, cfg)
    log.info("fusion: %s", report)
    tags = load_tags(tags if tags is not None else (out / "tags.json" if (out / "tags.json").exists() else None))
    ids = resolve_identities(frames, emb, tags, cfg.teams.n_teams, fps=fps)
    analysis = GameAnalyzer(cfg, fps, ids, calib).analyze(frames)

    (out / "identities.json").write_text(json.dumps(ids.to_dict(), indent=2))
    (out / "events.json").write_text(json.dumps([e.to_dict() for e in analysis.events], indent=2, default=float))
    (out / "flights.json").write_text(json.dumps([f.to_dict() for f in analysis.flights], default=float))
    bs = box_score(analysis, ids)
    bs.to_csv(out / "boxscore.csv", index=False)
    team_totals(bs).to_csv(out / "team_totals.csv", index=False)

    from .viz import charts

    if calib is not None:
        charts.shot_chart(analysis, cfg.court, str(out / "shot_chart.png"))
    charts.pass_network(analysis, str(out / "pass_network.png"), cfg.court if calib else None)
    charts.possession_timeline(analysis, fps, str(out / "possession.png"), ids.player_team)
    return analysis, ids, frames


def render(video: str, out_dir: str, cfg: Config | None = None, analysis=None, ids=None, frames=None) -> Path:
    from .viz.overlay import render as _render

    cfg = cfg or Config()
    out = _out(out_dir)
    if analysis is None:
        analysis, ids, frames = analyze(out_dir, cfg)
    vinfo = json.loads((out / "video.json").read_text())
    calib = CourtCalib.load(out / "court.json") if (out / "court.json").exists() else None
    path = out / "annotated.mp4"
    _render(video, str(path), frames, analysis, ids, calib, vinfo["fps"], vinfo.get("stride", 1))
    return path


def run(video: str, out_dir: str, cfg: Config | None = None, tags=None, manual_points=None, render_video: bool = True):
    cfg = cfg or Config()
    detect(video, out_dir, cfg)
    try:
        calibrate(video, out_dir, cfg, manual_points)
    except Exception as e:  # stats still work without a court (no 3PT / shot chart)
        log.warning("court calibration failed, continuing without court mapping: %s", e)
    analysis, ids, frames = analyze(out_dir, cfg, tags)
    if render_video:
        render(video, out_dir, cfg, analysis, ids, frames)
    return analysis, ids
