"""Command line: python -m nextrun_cv <stage> ...

  python -m nextrun_cv run game.mp4 -o outputs/game1 --tags tags.json --court-points points.json
  python -m nextrun_cv detect game.mp4 -o outputs/game1
  python -m nextrun_cv calibrate game.mp4 -o outputs/game1 --court-method lines
  python -m nextrun_cv run game.mp4 -o outputs/game2 --venue trackid3x3_outdoor   # saved camera profile
  python -m nextrun_cv analyze -o outputs/game1 --tags outputs/game1/tags.json
  python -m nextrun_cv render game.mp4 -o outputs/game1
"""
from __future__ import annotations

import argparse
import logging

from . import pipeline
from .config import Config, CourtSpec
from .court.venues import apply_venue


def _cfg(a) -> Config:
    cfg = Config.load(a.config) if a.config else Config()
    if a.venue:
        apply_venue(cfg, a.venue)
    if a.court:
        cfg.court = CourtSpec.preset(a.court)
    if a.court_method:
        cfg.court_method = a.court_method
    if a.stride:
        cfg.stride = a.stride
    if a.max_frames:
        cfg.max_frames = a.max_frames
    if a.device:
        cfg.models.device = a.device
    return cfg


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="nextrun_cv", description="NextRun basketball stat tracking")
    ap.add_argument("stage", choices=["run", "detect", "calibrate", "analyze", "render"])
    ap.add_argument("video", nargs="?")
    ap.add_argument("-o", "--out", required=True, help="output directory")
    ap.add_argument("--config", help="config JSON (see Config.save)")
    ap.add_argument("--tags", help="tags.json: {track_id: {name, team}}")
    ap.add_argument("--court", choices=["fiba", "nba", "ncaa", "highschool"])
    ap.add_argument("--court-method", choices=["auto", "keypoints", "lines", "manual"])
    ap.add_argument("--court-points", help="JSON {landmark: [u, v]} for manual calibration")
    ap.add_argument("--venue", help="saved camera profile in venues/ (court type + calibration points)")
    ap.add_argument("--stride", type=int)
    ap.add_argument("--max-frames", type=int)
    ap.add_argument("--device")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = _cfg(a)
    if a.stage in ("run", "detect", "calibrate", "render") and not a.video:
        ap.error(f"{a.stage} needs a video path")
    if a.stage == "run":
        pipeline.run(a.video, a.out, cfg, a.tags, a.court_points, not a.no_render, a.venue)
    elif a.stage == "detect":
        pipeline.detect(a.video, a.out, cfg)
    elif a.stage == "calibrate":
        c = pipeline.calibrate(a.video, a.out, cfg, a.court_points, a.venue)
        print(f"court: method={c.method} conf={c.conf:.2f}")
    elif a.stage == "analyze":
        pipeline.analyze(a.out, cfg, a.tags)
    elif a.stage == "render":
        print(pipeline.render(a.video, a.out, cfg))


if __name__ == "__main__":
    main()
