"""End-to-end pipeline, split into resumable stages that write to one output directory:

  detect    video -> tracks.json.gz (players+pose, ball, rims), appearance.json, tagging_frame.jpg
  calibrate video -> court_track.json (+ court.json)   the court per frame: one fit for a fixed camera, keypoint
                                                       fits linked by camera motion for a moving one (court/track.py)
  [user writes tags.json from tagging_frame.jpg]
  analyze   -> identities.json, events.json, flights.json, boxscore.csv, team_totals.csv, charts
  render    -> annotated.mp4

Detection is the only GPU-heavy stage; re-running analyze with new tags or thresholds is cheap."""
from __future__ import annotations

import copy
import gzip
import json
import re
import logging
from pathlib import Path

import cv2
import numpy as np

from . import fusion
from .config import Config
from .court.auto import calibrate_court, detect_court_type
from .config import CourtSpec
from .court.base import CourtCalib, CourtNotFound
from .court.track import CameraMotion, CourtTrack, camera_moves, stabilize_view, track_court
from .court.venues import apply_venue, load_venue
from .detect.ball_track import drop_implausible_rims, stabilize_rims, stabilize_rims_moving, track_ball
from .events.analyzer import GameAnalysis, GameAnalyzer
from .events.overrides import apply_overrides, load_overrides
from .identity.appearance import AppearanceBank
from .identity.split import split_swapped_tracks
from .identity.stitch import cover_tracks, stitch_tracks
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
def detect(video: str, out_dir: str, cfg: Config | None = None, progress: bool = True, on_frame=None) -> list[FrameState]:
    """on_frame(n, total, img, frame_state): called after every processed frame (the API uses it for live progress)."""
    from .integration import NextRun

    cfg = copy.deepcopy(cfg or Config())
    out = _out(out_dir)
    info = probe(video)
    moving = camera_moves(video, cfg)
    if moving:  # the tracker has to compensate camera motion, or a pan reads as every player jumping
        cfg.models.tracker_cfg = cfg.models.tracker_moving_cfg
        cfg.models.ball_crop = False  # rims move in the image: the play-area crop is for fixed cameras
    log.info("camera: %s", "moving" if moving else "fixed")
    models = NextRun(cfg)
    motion = CameraMotion(cfg.camera.motion_width) if moving else None
    bank = AppearanceBank(cfg.teams.sample_every)
    frames: list[FrameState] = []
    total = max(1, -(-info.n_frames // cfg.stride))  # frames the sampler will actually visit
    if cfg.max_frames is not None:
        total = min(total, cfg.max_frames)
    for n, (idx, img) in enumerate(iter_frames(video, cfg.stride, max_frames=cfg.max_frames)):
        f = models.detect(img, idx, idx / info.fps)
        f.ball = None  # chosen by the ball tracker below, from all candidates over time
        frames.append(f)
        if on_frame is not None:
            on_frame(n, total, img, f)
        bank.add(idx, img, f.players)
        if motion is not None:
            motion.add(idx, img, [p.bbox for p in f.players])
        if progress and n % 100 == 0:
            log.info("detect %d/%d frames", n, total)
    drop_implausible_rims(frames)
    track_ball(frames, cfg.ball)
    if motion is not None:
        stabilize_rims_moving(frames, motion.seg, motion.M, (info.width, info.height))
        motion.save(out / "camera_motion.json")
    else:
        stabilize_rims(frames)
    save_frames(frames, out / "tracks.json.gz")
    (out / "appearance.json").write_text(json.dumps(bank.to_dict()))
    (out / "video.json").write_text(json.dumps({**info.__dict__, "stride": cfg.stride, "moving_camera": moving}))
    k = best_tagging_frame(frames)
    cv2.imwrite(str(out / "tagging_frame.jpg"), tagging_sheet(read_frame(video, frames[k].idx), frames[k]))
    log.info("detect done: %d frames, tagging frame %d", len(frames), frames[k].idx if frames else -1)
    return frames


def calibrate(video: str, out_dir: str, cfg: Config | None = None, manual_points=None, venue: str | None = None) -> CourtTrack:
    """The court for every frame -> court_track.json (court.json keeps the single best fit).
    venue: a saved camera profile (venues/<name>.json); sets the court type and the manual points (fixed camera)."""
    cfg = cfg or Config()
    out = _out(out_dir)
    if venue is not None:
        info = probe(video)
        apply_venue(cfg, venue)
        manual_points = load_venue(venue, (info.width, info.height))[1]
    tracks = out / "tracks.json.gz"
    frames = load_frames(tracks) if tracks.exists() else []
    vjson = out / "video.json"
    moving = json.loads(vjson.read_text()).get("moving_camera") if vjson.exists() and cfg.camera.mode == "auto" else None
    if moving is None:
        moving = camera_moves(video, cfg)
    n = min(cfg.court_calib_frames, max(1, len(frames))) if frames else cfg.court_calib_frames
    picks = [frames[i] for i in np.linspace(0, len(frames) - 1, n).astype(int)] if frames else []
    imgs = [read_frame(video, f.idx) for f in picks] if picks else [read_frame(video, 0)]
    ignore = [[p.bbox for p in f.players] for f in picks] if picks else None
    rims = frames[0].rims if frames else []
    rim_xy = max(rims, key=lambda r: r.conf).center if rims else None
    rims_per_frame = [f.rims for f in picks] if picks else None
    if cfg.court_autodetect and venue is None and manual_points is None and cfg.court_method in ("auto", "keypoints"):
        try:  # which court type is this (a venue profile or manual points already say)? decides the line geometry
            name, _ = detect_court_type(imgs, cfg, ignore)
            if name != cfg.court.name:
                log.info("court type: using %s (was %s)", name, cfg.court.name)
                cfg.court = CourtSpec.preset(name)
        except (CourtNotFound, FileNotFoundError) as e:
            log.warning("court type not detected (%s); keeping %s", e, cfg.court.name)
    if moving and frames and manual_points is None and cfg.court_method in ("auto", "keypoints"):
        try:
            mpath = out / "camera_motion.json"
            track = track_court(video, frames, cfg, CameraMotion.load(mpath) if mpath.exists() else None)
        except CourtNotFound as e:
            log.warning("moving camera: court track failed (%s); falling back to one calibration", e)
        else:
            if track.usable_share(cfg.fusion.min_court_conf) > 0:
                track.save(out / "court_track.json")
                track.best().save(out / "court.json")
                return track
            log.warning("moving camera: no frame got a usable court; falling back to one calibration")
    try:
        calib = calibrate_court(imgs, cfg, manual_points, ignore, rim_xy, rims_per_frame)
    except CourtNotFound as e:
        if not frames:
            raise
        log.warning("court calibration failed (%s); estimating the court from the scene", e)
        from .court.scene import estimate_from_scene

        calib = estimate_from_scene(frames, cfg.court, (imgs[0].shape[1], imgs[0].shape[0]))
    calib.save(out / "court.json")
    track = CourtTrack.static(calib)
    track.save(out / "court_track.json")
    return track


def load_court(out: Path, spec) -> CourtTrack | None:
    """court_track.json (or an older run's court.json), with the court geometry set to `spec`."""
    if (out / "court_track.json").exists():
        track = CourtTrack.load(out / "court_track.json")
    elif (out / "court.json").exists():
        track = CourtTrack.static(CourtCalib.load(out / "court.json"))
    else:
        return None
    track.spec = spec
    for c in track.calibs.values():
        c.spec = spec
    return track


def _color_samples(out: Path, vinfo: dict, frames: list[FrameState]) -> dict:
    """{track id: [(source frame, torso colour)]} for the swap splitter; made once per game, then cached."""
    path = out / "appearance_samples.json.gz"
    if path.exists():
        with gzip.open(path, "rt") as fh:
            return {int(k): v for k, v in json.load(fh).items()}
    video = out / "video.mp4" if (out / "video.mp4").exists() else Path(vinfo.get("path", ""))
    if not video.exists():
        return {}
    from .identity.appearance import sample_track_colors

    samples = sample_track_colors(str(video), frames)
    with gzip.open(path, "wt") as fh:
        json.dump({str(k): v for k, v in samples.items()}, fh)
    return samples


def _body_by_track(out: Path, vinfo: dict, frames: list[FrameState]) -> dict[int, np.ndarray]:
    """Average whole-body colour signature per current track id (needs >= 2 clean looks). The per-detection samples
    are made once per game and cached; they are keyed by frame + box, so they survive tracks being split or joined."""
    from .identity.appearance import body_key, sample_body_signatures

    path = out / "appearance_body.json.gz"
    if path.exists():
        with gzip.open(path, "rt") as fh:
            sig = json.load(fh)
    else:
        video = out / "video.mp4" if (out / "video.mp4").exists() else Path(vinfo.get("path", ""))
        if not video.exists():
            return {}
        sig = sample_body_signatures(str(video), frames)
        with gzip.open(path, "wt") as fh:
            json.dump(sig, fh)
    per: dict[int, list] = {}
    for f in frames:
        for p in f.players:
            v = sig.get(body_key(f.idx, p.bbox))
            if v is not None and p.track_id is not None:
                per.setdefault(p.track_id, []).append(v)
    return {t: np.mean(np.asarray(v, np.float32), 0) for t, v in per.items() if len(v) >= 2}


def _reid_by_track(out: Path, vinfo: dict, frames: list[FrameState]) -> dict[int, np.ndarray]:
    """Average OSNet fingerprint per current track id (>= 3 clean crops). Per-detection fingerprints are made once per
    game and cached (keyed by frame + box, so they survive tracks being split or joined). Empty without the weights."""
    from .identity import reid
    from .identity.appearance import body_key

    if not reid.available():
        return {}
    path = out / "appearance_reid.npz"
    if path.exists():
        z = np.load(path)
        sig = dict(zip(z["keys"].tolist(), z["emb"]))
    else:
        video = out / "video.mp4" if (out / "video.mp4").exists() else Path(vinfo.get("path", ""))
        if not video.exists():
            return {}
        sig = reid.sample_fingerprints(str(video), frames)
        np.savez_compressed(path, keys=np.array(list(sig), dtype=str), emb=np.array(list(sig.values()), np.float16).reshape(-1, 512))
    per: dict[int, list] = {}
    for f in frames:
        for p in f.players:
            v = sig.get(body_key(f.idx, p.bbox))
            if v is not None and p.track_id is not None:
                per.setdefault(p.track_id, []).append(np.asarray(v, np.float32))
    out_: dict[int, np.ndarray] = {}
    for t, v in per.items():
        if len(v) >= 3:
            m = np.mean(v, 0)
            out_[t] = m / max(np.linalg.norm(m), 1e-9)
    return out_


_AUTO_NAME = re.compile(r"^\s*player\s*\d+\s*$", re.I)  # "Player 53": the app's default label, not a real name


def _tag_constraints(tags: dict) -> tuple[dict[int, str], dict[int, str]]:
    """Which tracks the person told apart: names they typed themselves, and teams. The team picker saves every
    track with its default "Player N" label; those labels say nothing about who is who, so they do not stop two
    pieces of one player from being joined."""
    names = {t: v["name"].strip() for t, v in tags.items() if v.get("name") and not _AUTO_NAME.match(v["name"])}
    teams = {t: v["team"] for t, v in tags.items() if v.get("team")}
    return names, teams


def _merge_tags(tags: dict, joined: dict[int, int]) -> dict:
    """Tags after tracks were joined: a chain keeps a typed name over a default label, and its earliest tag otherwise."""
    out: dict = {}
    for t in sorted(tags):
        k = joined.get(t, t)
        v = tags[t]
        if k not in out or (_AUTO_NAME.match(out[k].get("name") or "player 0") and not _AUTO_NAME.match(v.get("name") or "player 0")):
            out[k] = v
    return out


def identify(out: Path, cfg: Config, tags=None):
    """Who is who, without events: (identities, frames, court, fps, embeddings, view, view_court). frames are fused
    with the court (off-court people dropped when the court is reliable) and lost tracks are stitched."""
    frames = load_frames(out / "tracks.json.gz")
    vinfo = json.loads((out / "video.json").read_text())
    fps = vinfo["fps"] / vinfo.get("stride", 1)
    emb = {int(k): np.asarray(v) for k, v in json.loads((out / "appearance.json").read_text()).items()}
    # re-run the (cheap, offline) ball / rim clean-up on the stored detections, so improvements apply to old uploads
    n_rims = drop_implausible_rims(frames)
    if n_rims:
        log.info("rims: dropped %d impossible rim boxes", n_rims)
    track_ball(frames, cfg.ball)
    # a tracker id that jumped to another player mid-clip is cut into one track per player (by torso colour over time)
    samples = _color_samples(out, vinfo, frames)
    if samples:
        split = split_swapped_tracks(frames, samples, emb)
        if split:
            log.info("identity: split %d swapped track(s): %s", len(split), split)
    calib = load_court(out, cfg.court)
    report = fusion.fuse(frames, calib, cfg)
    log.info("fusion: %s", report)
    tags = load_tags(tags if tags is not None else (out / "tags.json" if (out / "tags.json").exists() else None))
    if cfg.stitch.enabled:  # join lost tracks to the track that picks the player up again (tags follow the join)
        joined = stitch_tracks(frames, emb, cfg.stitch, *_tag_constraints(tags), reid=_reid_by_track(out, vinfo, frames))
        tags = _merge_tags(tags, joined)
        log.info("stitch: %d tracks joined to earlier ones", len(joined))
        if cfg.stitch.cover:  # then one id per real person over the whole clip (never joins people seen together)
            joined = cover_tracks(frames, emb, cfg.stitch, *_tag_constraints(tags), body=_body_by_track(out, vinfo, frames),
                                  reid=_reid_by_track(out, vinfo, frames))
            tags = _merge_tags(tags, joined)
            log.info("identity: %d more tracks joined across the clip", len(joined))
    # moving camera: identities and events work in a stabilized view (camera motion undone, court.track.stabilize_view)
    view, view_court = frames, calib
    if vinfo.get("moving_camera") and (out / "camera_motion.json").exists():
        view, view_court = stabilize_view(frames, calib, CameraMotion.load(out / "camera_motion.json"))
    ids = resolve_identities(view, emb, tags, cfg.teams.n_teams, fps=fps, max_other_share=cfg.teams.max_other_share)
    return ids, frames, calib, fps, emb, view, view_court


def run_analysis(out: Path, cfg: Config, tags=None) -> tuple[GameAnalysis, Identities, list[FrameState], object]:
    """Events from a detect + calibrate output dir, without writing anything (analyze() saves them)."""
    ids, frames, calib, fps, _emb, view, view_court = identify(out, cfg, tags)
    analysis = GameAnalyzer(cfg, fps, ids, view_court).analyze(view)
    overrides = load_overrides(out / "overrides.json")  # the person's corrections ("count this basket", "not a basket")
    if overrides:
        apply_overrides(analysis, overrides, ids, cfg)
    return analysis, ids, frames, calib


def analyze(out_dir: str, cfg: Config | None = None, tags=None) -> tuple[GameAnalysis, Identities, list[FrameState]]:
    cfg = cfg or Config()
    out = _out(out_dir)
    analysis, ids, frames, calib = run_analysis(out, cfg, tags)
    vinfo = json.loads((out / "video.json").read_text())
    fps = vinfo["fps"] / vinfo.get("stride", 1)
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
    calib = load_court(out, cfg.court)
    path = out / "annotated.mp4"
    mpath = out / "camera_motion.json"
    motion = CameraMotion.load(mpath) if vinfo.get("moving_camera") and mpath.exists() else None
    _render(video, str(path), frames, analysis, ids, calib, vinfo["fps"], vinfo.get("stride", 1), motion=motion)
    return path


def run(video: str, out_dir: str, cfg: Config | None = None, tags=None, manual_points=None, render_video: bool = True,
        venue: str | None = None):
    cfg = cfg or Config()
    if venue is not None:
        apply_venue(cfg, venue)
    detect(video, out_dir, cfg)
    try:
        calibrate(video, out_dir, cfg, manual_points, venue)
    except Exception as e:  # stats still work without a court (no 3PT / shot chart)
        log.warning("court calibration failed, continuing without court mapping: %s", e)
    analysis, ids, frames = analyze(out_dir, cfg, tags)
    if render_video:
        render(video, out_dir, cfg, analysis, ids, frames)
    return analysis, ids
