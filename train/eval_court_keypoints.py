"""Evaluate the court-keypoint model end to end: for each labeled test image, calibrate with the model
(KeypointCourtEstimator, incl. RANSAC + mirror fix) and measure how far the predicted homography puts
the ground-truth landmarks, in meters on the court.

  python train/eval_court_keypoints.py --data data/court_kp --split test [--weights models/court_keypoints.pt]
"""
import argparse
import glob
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import CourtSpec  # noqa: E402
from nextrun_cv.court import template  # noqa: E402
from nextrun_cv.court.base import CourtNotFound  # noqa: E402
from nextrun_cv.court.keypoints import KeypointCourtEstimator  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "court_kp"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--weights", default=str(ROOT / "models" / "court_keypoints.pt"))
    ap.add_argument("--court", default="nba")
    ap.add_argument("--device", default=None)
    ap.add_argument("--kp-conf", type=float, default=0.5)
    a = ap.parse_args()
    spec = CourtSpec.preset(a.court)
    est = KeypointCourtEstimator(spec, a.weights, a.device, a.kp_conf)
    lm = template.landmarks(spec)
    names = template.keypoint_order()
    errs, fails, n_kp = [], 0, []
    labels = sorted(glob.glob(f"{a.data}/{a.split}/labels/*.txt"))
    for lab in labels:
        img = cv2.imread(lab.replace("labels", "images")[:-4] + ".jpg")
        h, w = img.shape[:2]
        kp = np.array(open(lab).read().split(), float)[5:].reshape(-1, 3)
        gt = [(n, (x * w, y * h)) for n, (x, y, v) in zip(names, kp) if v > 0 and n in lm]
        try:
            calib = est.estimate(img)
        except CourtNotFound:
            fails += 1
            continue
        n_kp.append(len(calib.correspondences or {}))
        pred = calib.image_to_court(np.array([uv for _, uv in gt], float))
        e = np.linalg.norm(pred - np.array([lm[n] for n, _ in gt]), axis=1)
        errs.append(float(np.median(e)))
    errs = np.array(errs)
    res = {
        "images": len(labels),
        "calibrated": int(len(errs)),
        "failed": fails,
        "median_landmark_error_m": float(np.median(errs)) if len(errs) else None,
        "p90_image_error_m": float(np.percentile(errs, 90)) if len(errs) else None,
        "frac_images_under_0.5m": float((errs < 0.5).mean()) if len(errs) else None,
        "frac_images_under_1m": float((errs < 1.0).mean()) if len(errs) else None,
        "mean_keypoints_used": float(np.mean(n_kp)) if n_kp else None,
    }
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
