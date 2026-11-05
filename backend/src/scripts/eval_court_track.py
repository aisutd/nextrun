"""Court accuracy through a whole moving-camera video, against the labelled frames of the court test set.

  python src/scripts/eval_court_track.py                       # TrackID3x3 drone flight 1-1 (42 labelled frames)
  python src/scripts/eval_court_track.py --video ... --source venue_trackid3x3_drone --stride 5

Compares, at every labelled frame (same metric as eval_court.py: per-image median error in feet, usable <= 3 ft):
  static    one calibration for the whole video (the pipeline's fixed-camera path: best of 10 frames)
  per_frame the court model on that frame alone
  track     court.track.track_court: keypoint fits on keyframes, linked by camera motion
"""
from __future__ import annotations

import argparse
import logging
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "scripts"))

from eval_court import court_for_source  # noqa: E402
from nextrun_cv.config import Config  # noqa: E402
from nextrun_cv.court.auto import calibrate_court  # noqa: E402
from nextrun_cv.court.base import CourtNotFound  # noqa: E402
from nextrun_cv.court.keypoints import FT, KeypointCourtEstimator, keypoints_for_court, load_keypoint_config  # noqa: E402
from nextrun_cv.court.track import track_court  # noqa: E402
from nextrun_cv.schema import FrameState  # noqa: E402
from nextrun_cv.video import probe, read_frame  # noqa: E402


def errors(calib, lab: np.ndarray, truth: dict, w: int, h: int) -> float | None:
    if calib is None:
        return None
    ids = [i for i, (x, y, v) in enumerate(lab) if v > 0 and i in truth]
    pred = calib.image_to_court([(lab[i, 0] * w, lab[i, 1] * h) for i in ids])
    e = [float(np.hypot(*(p - np.array(truth[i])))) / FT for i, p in zip(ids, pred)]
    return float(np.median(e)) if e else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(ROOT / "data/raw/trackid3x3/videos/drone/1-1.mov"))
    ap.add_argument("--source", default="venue_trackid3x3_drone")
    ap.add_argument("--data", default=str(ROOT / "data/court24/test"))
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--keyframe-s", type=float, default=1.0)
    ap.add_argument("--good-ft", type=float, default=3.0)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = Config()
    cfg.court = court_for_source(a.source, None)
    cfg.stride = a.stride
    cfg.camera.keyframe_s = a.keyframe_s
    info = probe(a.video)
    stem = Path(a.video).stem
    labelled = {}
    for p in sorted((Path(a.data) / "images").glob(f"{a.source}__{stem}_*.jpg")):
        idx = int(p.stem.rsplit("_", 1)[1])
        labelled[idx] = np.array((Path(a.data) / "labels" / f"{p.stem}.txt").read_text().split()[5:], float).reshape(-1, 3)
    print(f"{len(labelled)} labelled frames in {stem}")
    truth = keypoints_for_court(load_keypoint_config(cfg.models.court_keypoint_config), cfg.court)
    w, h = info.width, info.height

    frames = [FrameState(i, i / info.fps) for i in range(0, info.n_frames, a.stride)]
    track = track_court(a.video, frames, cfg)
    picks = np.linspace(0, info.n_frames - 30, cfg.court_calib_frames).astype(int)  # last frames may not decode
    try:
        static = calibrate_court([read_frame(a.video, int(i)) for i in picks], cfg)
    except CourtNotFound:
        static = None
    est = KeypointCourtEstimator(cfg.court, cfg.models.court_keypoint_weights, cfg.models.court_keypoint_config)

    rows = {}
    for idx, lab in labelled.items():
        try:
            single = est.estimate(read_frame(a.video, idx))
        except CourtNotFound:
            single = None
        rows[idx] = {"static": errors(static, lab, truth, w, h), "per_frame": errors(single, lab, truth, w, h),
                     "track": errors(track.at(idx), lab, truth, w, h),
                     "track_conf": track.at(idx).conf if track.at(idx) is not None else None}
    summary = {}
    for k in ("static", "per_frame", "track"):
        e = [r[k] for r in rows.values()]
        ok = [x for x in e if x is not None]
        summary[k] = {"usable": sum(x <= a.good_ft for x in ok), "of": len(e),
                      "median_ft": float(np.median(ok)) if ok else None}
    summary["track_checks"] = track.checks
    out = ROOT / f"results/court_track_{stem}.json"
    out.write_text(json.dumps({"summary": summary, "frames": rows}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
