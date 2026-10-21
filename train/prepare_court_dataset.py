"""Build the court-keypoint training set from the public "basketball-court-detection-2" dataset
(850 NBA broadcast frames, 48 keypoints, CC BY 4.0; Hugging Face mirror
koppolusameer/basketball-keypoint-detection-yolov8) and convert it to our landmark schema
(nextrun_cv.court.template.keypoint_order()).

Per image:
  1. map the dataset's keypoints to named court landmarks (NBA dimensions),
  2. fit a court->image homography with RANSAC and drop mislabeled keypoints (outliers),
  3. if the fit is solid, "densify": project every other landmark that lands inside the frame and
     near the labeled area (fills in unlabeled / occluded points, adds center-circle points),
  4. write YOLO-pose labels with short file names (Windows path limits).

  python train/prepare_court_dataset.py --out data/court_kp
  python train/train_court_keypoints.py --data data/court_kp/court.yaml

To add your own courts later: label frames in the same schema (or with the manual clicker) and drop
them into data/court_kp/{train,val}/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nextrun_cv.config import CourtSpec  # noqa: E402
from nextrun_cv.court import template  # noqa: E402

HF_REPO = "koppolusameer/basketball-keypoint-detection-yolov8"

# dataset keypoint index -> our landmark name. Derived from the dataset's flip_idx plus visual checks,
# then verified by homography residuals (median 2-4 px on 1920x1080). Indices not listed are unused.
_RIGHT = {
    35: "base_top", 36: "c3_base_top", 38: "paint_base_top", 39: "paint_base_bot", 41: "c3_base_bot",
    42: "base_bot", 34: "backboard", 32: "c3_arc_top", 33: "c3_arc_bot", 29: "paint_ft_top",
    30: "ft_center", 31: "paint_ft_bot", 26: "hash_top", 27: "arc_top", 28: "hash_bot",
}
_LEFT = {35: 0, 36: 1, 38: 3, 39: 4, 41: 6, 42: 7, 34: 8, 32: 9, 33: 11, 29: 12, 30: 13, 31: 14, 26: 16, 27: 17, 28: 18}
SRC_MAP = {i: "R_" + n for i, n in _RIGHT.items()}
SRC_MAP.update({_LEFT[i]: "L_" + n for i, n in _RIGHT.items()})
SRC_MAP.update({20: "mid_top", 22: "center", 24: "mid_bot"})

SPEC = CourtSpec.preset("nba")
# the dataset's "backboard" point is annotated ~1.29 m from the baseline (measured from the fits)
SPEC.backboard_from_baseline = 1.29


def _long(p: Path) -> str:
    """Windows extended-length path (dataset file names are ~120 chars)."""
    s = str(p.resolve())
    return "\\\\?\\" + s if os.name == "nt" and not s.startswith("\\\\?\\") else s


def download(dst: Path) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(HF_REPO, repo_type="dataset", local_dir=_long(dst), token=False, max_workers=16))


def _read_label(path: str) -> tuple[np.ndarray, np.ndarray] | None:
    rows = [list(map(float, r.split())) for r in open(path) if r.strip()]
    if not rows:
        return None
    rows.sort(key=lambda r: -int((np.array(r[5:]).reshape(-1, 3)[:, 2] > 0).sum()))
    r = rows[0]
    return np.array(r[1:5]), np.array(r[5:]).reshape(-1, 3)


def convert(kp: np.ndarray, w: int, h: int, densify: bool = True) -> tuple[dict[str, tuple[float, float]], dict]:
    """Dataset keypoints (normalized) -> {landmark: (u, v) px}, cleaned and optionally densified."""
    lm = template.landmarks(SPEC)
    names = [SRC_MAP[i] for i in SRC_MAP if kp[i, 2] > 0]
    img = np.array([kp[i, :2] * [w, h] for i in SRC_MAP if kp[i, 2] > 0], np.float32)
    info = {"labeled": len(names), "inliers": 0, "added": 0}
    if len(names) < 4:
        return {}, info
    court = np.array([lm[n] for n in names], np.float32)
    thr = 0.007 * np.hypot(w, h)
    H, mask = cv2.findHomography(court, img, cv2.RANSAC, thr)
    if H is None:
        return {}, info
    inl = mask.ravel().astype(bool)
    proj = cv2.perspectiveTransform(court[None], H)[0]
    err = np.linalg.norm(proj - img, axis=1)
    inl &= err < thr
    out = {n: (float(u), float(v)) for n, (u, v), k in zip(names, img, inl) if k and 0 <= u < w and 0 <= v < h}
    info["inliers"] = int(inl.sum())
    if inl.sum() < 4:
        return {}, info
    rms = float(np.sqrt(np.mean(err[inl] ** 2)))
    info["rms"] = rms
    if densify and inl.sum() >= 8 and rms < 0.003 * np.hypot(w, h):
        lab_court = court[inl]
        margin = 0.01 * w
        for n in template.keypoint_order():
            if n in out or n not in lm:
                continue
            c = np.array(lm[n], np.float64)
            if np.min(np.linalg.norm(lab_court - c, axis=1)) > 8.0:  # don't extrapolate far from labels
                continue
            q = H @ np.array([c[0], c[1], 1.0])
            if q[2] <= 0:
                continue
            u, v = q[:2] / q[2]
            if margin <= u < w - margin and margin <= v < h - margin:
                out[n] = (float(u), float(v))
                info["added"] += 1
    return out, info


def write_yaml(path: Path, root: Path) -> None:
    names = template.keypoint_order()
    lines = [
        f"path: {root.resolve().as_posix()}",
        "train: train/images",
        "val: val/images",
        "test: test/images",
        f"kpt_shape: [{len(names)}, 3]",
        f"flip_idx: {template.keypoint_flip_idx()}",
        "names:",
        "  0: court",
        "# keypoint order:",
        *[f"#  {i}: {n}" for i, n in enumerate(names)],
    ]
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/court_hf", help="download / existing copy of the HF dataset")
    ap.add_argument("--out", default="data/court_kp")
    ap.add_argument("--no-densify", action="store_true")
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    if not (raw / "data.yaml").exists():
        print(f"downloading {HF_REPO} -> {raw}")
        download(raw)
    names = template.keypoint_order()
    stats = {"images": 0, "dropped": 0, "labeled": 0, "inliers": 0, "added": 0}
    name_map = {}
    for split_src, split in (("train", "train"), ("valid", "val"), ("test", "test")):
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        files = sorted(os.listdir(_long(raw / split_src / "images")))
        for i, f in enumerate(files):
            stem = f.rsplit(".", 1)[0]
            lab = _read_label(_long(raw / split_src / "labels" / f"{stem}.txt"))
            img_path = _long(raw / split_src / "images" / f)
            im = cv2.imdecode(np.fromfile(img_path, np.uint8), cv2.IMREAD_COLOR)
            if lab is None or im is None:
                stats["dropped"] += 1
                continue
            h, w = im.shape[:2]
            pts, info = convert(lab[1], w, h, densify=not a.no_densify)
            if len(pts) < 4:
                stats["dropped"] += 1
                continue
            for k in ("labeled", "inliers", "added"):
                stats[k] += info[k]
            uv = np.array(list(pts.values()))
            x0, y0 = np.maximum(uv.min(0) - 0.02 * w, 0)
            x1, y1 = np.minimum(uv.max(0) + 0.02 * w, [w - 1, h - 1])
            kp = []
            for n in names:
                if n in pts:
                    kp += [pts[n][0] / w, pts[n][1] / h, 2]
                else:
                    kp += [0, 0, 0]
            short = f"{split}_{i:04d}"
            shutil.copyfile(img_path, out / split / "images" / f"{short}.jpg")
            row = [0, (x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h] + kp
            (out / split / "labels" / f"{short}.txt").write_text(" ".join(f"{v:.6g}" for v in row) + "\n")
            name_map[short] = f
            stats["images"] += 1
    (out / "source_names.json").write_text(json.dumps(name_map, indent=0))
    write_yaml(out / "court.yaml", out)
    (out / "README.txt").write_text(
        "Converted from basketball-court-detection-2 (Roboflow Universe, CC BY 4.0) via the Hugging Face\n"
        f"mirror {HF_REPO}. Labels remapped to nextrun_cv court landmarks, RANSAC-cleaned, densified.\n"
    )
    print(json.dumps(stats, indent=1))
    print(f"wrote {out / 'court.yaml'}")


if __name__ == "__main__":
    main()
