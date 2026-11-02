"""EPFL SportCenter (two moving smartphones at an amateur game) -> court-keypoint test / train images.

  python src/scripts/build_sportcenter.py --src data/raw/sportcenter/sportcenter_camerapose_dataset \
      --out data/court_sportcenter --every 40

Dataset: https://www.epfl.ch/labs/cvlab/data/sportcenter-dataset/ ("free of use for research purposes",
Citraro et al. 2020). Every image comes with Hr, a world -> image homography (world: meters, origin center
court, x across, y along the court). The gym court is short and narrow (24.12 x 13.36 m, FIBA markings),
measured from the dataset's rectified_template.png; its 3PT arc runs into the sidelines, so the corner-3 and
arc-wing keypoints (1, 4, 11, 14, 18, 20, 21, 23) don't exist and are left unlabelled.
The dataset's own split is kept: "testing" sequences -> test/, "training" sequences -> train/ (only use those
for training if the licence allows it for your purpose). Source name: sportcenter (eval_court.py knows the court).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import CourtSpec  # noqa: E402
from nextrun_cv.court.keypoints import keypoints_for_court, load_keypoint_config, orientation_sign  # noqa: E402
from nextrun_cv.datasets import pose_label, project_keypoints  # noqa: E402

SPEC = CourtSpec("sportcenter", length=24.12, width=13.36, three_pt_radius=6.75, corner_three_offset=0.0,
                 hoop_from_baseline=1.575, paint_width=4.85, ft_line_from_baseline=5.82)
MISSING = {1, 4, 11, 14, 18, 20, 21, 23}
TRAIN = ["seq_9841", "seq_9842", "seq_9843", "seq_9849", "seq_9850", "seq_171305", "seq_171931", "seq_172146",
         "seq_172444", "seq_173321", "seq_173510", "seq_173833"]
TEST = ["seq_9844", "seq_9847", "seq_9851", "seq_9852", "seq_9853", "seq_9845", "seq_9854", "seq_9855", "seq_9856",
        "seq_9857", "seq_172318", "seq_172647", "seq_172730", "seq_173742", "seq_174006", "seq_174210"]
N_KP = 24


def court_to_image(Hr: np.ndarray, w: int, h: int) -> np.ndarray:
    """Our court frame (x along, y across) -> image, following the real sets' labelling conventions:
    template handedness, and of the two 180-degree-symmetric labellings the one with view direction d_x > d_y."""
    H = Hr @ np.array([[0, 1.0, 0], [1.0, 0, 0], [0, 0, 1]])  # (x_ours, y_ours) = (y_world, x_world)
    if orientation_sign(np.linalg.inv(H), (w / 2, h / 2)) < 0:
        H = H @ np.diag([1.0, -1.0, 1.0])
    Hi = np.linalg.inv(H)
    a, b = Hi @ [w / 2, h - 1, 1.0], Hi @ [w / 2, h / 2, 1.0]
    d = b[:2] / b[2] - a[:2] / a[2]
    if d[0] <= d[1]:
        H = H @ np.diag([-1.0, -1.0, 1.0])
    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/sportcenter/sportcenter_camerapose_dataset")
    ap.add_argument("--out", default="data/court_sportcenter")
    ap.add_argument("--every", type=int, default=40, help="take every Nth frame of each sequence")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    court = {i: p for i, p in keypoints_for_court(load_keypoint_config(ROOT.parent / "weights" / "court" / "court_keypoints.json"), SPEC).items()
             if i not in MISSING}
    for split, seqs in (("test", TEST), ("train", TRAIN)):
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        n = 0
        for seq in seqs:
            poses = json.loads((src / seq / "poses.json").read_text())
            for name in sorted(poses)[:: a.every]:
                im = cv2.imread(str(src / seq / "images_orig_blurred" / name))
                if im is None:
                    continue
                h, w = im.shape[:2]
                H = court_to_image(np.array(poses[name]["Hr"], float), w, h)
                label = pose_label(project_keypoints(H, court, N_KP, w, h), w, h)
                if label is None:
                    continue
                stem = f"sportcenter__{seq[4:]}_{Path(name).stem.split('_')[-1]}"
                cv2.imwrite(str(out / split / "images" / f"{stem}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
                (out / split / "labels" / f"{stem}.txt").write_text(label + "\n")
                n += 1
        print(f"{split}: {n} images")
    (out / "data.yaml").write_text(f"path: {out.resolve()}\ntrain: train/images\nval: test/images\ntest: test/images\n"
                                   "kpt_shape: [24, 3]\nflip_idx: [10, 11, 12, 13, 14, 15, 16, 17, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, "
                                   "21, 22, 23, 18, 19, 20]\nnames:\n  0: court\n")


if __name__ == "__main__":
    main()
