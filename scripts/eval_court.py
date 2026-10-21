"""Court model accuracy per source/domain on a court24 dataset (scripts/build_court_dataset.py).

  python scripts/eval_court.py --data data/court24 --split test [--weights models/court_model.pt] [--court nba]

For each image: run the court model (KeypointCourtEstimator, incl. RANSAC + left/right fix) and map every
labelled keypoint through the predicted homography; error = distance to that keypoint's true court position.
Reports per source: court found rate and median / mean / p90 mapping error in feet (same metric as
docs/court_detection.md). `--court` sets the court geometry; by default it is inferred from the source name
(nba_* -> nba, venue_* -> the venue's court, otherwise highschool).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT, CourtSpec, ModelConfig  # noqa: E402
from nextrun_cv.court.base import CourtNotFound  # noqa: E402
from nextrun_cv.court.keypoints import KeypointCourtEstimator, keypoints_for_court, load_keypoint_config  # noqa: E402
from nextrun_cv.court.venues import load_venue  # noqa: E402

FT = 0.3048


def court_for_source(src: str, override: str | None) -> CourtSpec:
    if override:
        return CourtSpec.preset(override)
    if src.startswith("nba"):
        return CourtSpec.preset("nba")
    if src.startswith("venue_"):
        return load_venue(src[len("venue_"):])[0]
    return CourtSpec.preset("highschool")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(REPO_ROOT / "data" / "court24"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--weights", default=ModelConfig().court_keypoint_weights)
    ap.add_argument("--court", choices=["nba", "fiba", "ncaa", "highschool"])
    ap.add_argument("--device")
    ap.add_argument("--max-per-source", type=int)
    a = ap.parse_args()

    kp_cfg = load_keypoint_config(ModelConfig().court_keypoint_config)
    imgs = sorted((Path(a.data) / a.split / "images").glob("*.jpg"))
    by_src: dict[str, list[Path]] = defaultdict(list)
    for p in imgs:
        by_src[p.name.split("__")[0]].append(p)

    estimators: dict[str, KeypointCourtEstimator] = {}
    report = {}
    for src, paths in sorted(by_src.items()):
        spec = court_for_source(src, a.court)
        if spec.name not in estimators:
            estimators[spec.name] = KeypointCourtEstimator(spec, a.weights, ModelConfig().court_keypoint_config, a.device)
        est = estimators[spec.name]
        truth = keypoints_for_court(kp_cfg, spec)
        found, errs = 0, []
        for p in paths[: a.max_per_source]:
            im = cv2.imread(str(p))
            h, w = im.shape[:2]
            lab = np.array((p.parent.parent / "labels" / f"{p.stem}.txt").read_text().split()[5:], float).reshape(-1, 3)
            try:
                calib = est.estimate(im)
            except CourtNotFound:
                continue
            found += 1
            ids = [i for i, (x, y, v) in enumerate(lab) if v > 0 and i in truth]
            pred = calib.image_to_court([(lab[i, 0] * w, lab[i, 1] * h) for i in ids])
            errs += [float(np.hypot(*(pq - np.array(truth[i])))) / FT for i, pq in zip(ids, pred)]
        n = len(paths[: a.max_per_source])
        e = np.array(errs) if errs else np.array([np.nan])
        report[src] = {"court": spec.name, "images": n, "found": found, "found_rate": round(found / max(n, 1), 3),
                       "err_ft_median": round(float(np.nanmedian(e)), 2), "err_ft_mean": round(float(np.nanmean(e)), 2),
                       "err_ft_p90": round(float(np.nanpercentile(e, 90)), 2)}
        print(f"{src:36s} {spec.name:10s} found {found}/{n}  error ft median {report[src]['err_ft_median']}"
              f"  mean {report[src]['err_ft_mean']}  p90 {report[src]['err_ft_p90']}")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
