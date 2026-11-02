"""Pseudo-labelled ball/rim frames from our own (unlabelled) footage, to close the gap between the labelled
ball/rim sets (mostly broadcast / close views) and wide community-court cameras.

  python src/scripts/pseudo_label_ball.py --out data/ball_rim_pl --base data/ball_rim \
      --weights weights/ball_hoop/archive/ball_hoop_yolov8n_original.pt weights/ball_hoop/ball_yolo26l.pt

Frames are sampled from every TrackID3x3 video except the ones check_ball_footage.py / autotrain.py use to
judge ball models (EXCLUDE), so that check stays independent. Each model runs at the pipeline's resolution
(native, capped at 1920); boxes with confidence >= --conf from any model are merged (same-class boxes
overlapping by IoU > 0.5 count once). Spots seen in >= 40 % of a video's sampled frames are static objects
(spare balls, fixtures) and are dropped. Only frames with a confident ball are kept: a frame whose ball every
model missed would teach "no ball here". Frames are saved at <= 1920 px wide.

With --base, out/ gets the base set's images (symlinked) and a data.yaml with its val/test splits.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT  # noqa: E402

EXCLUDE = {"IMG_0105", "IMG_0110", "basket_S3T2_pre", "basket_S5T4_post", "1-1"}
VIDEOS = "data/raw/trackid3x3/videos"


def iou(a, b) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", help="labelled ball/rim set to link in (its val/test are used as is)")
    ap.add_argument("--weights", nargs="+", required=True)
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--per-video", type=int, default=40, help="frames sampled per long outdoor/drone video")
    ap.add_argument("--per-clip", type=int, default=12, help="frames sampled per short indoor clip")
    a = ap.parse_args()
    from ultralytics import YOLO

    models = [YOLO(w) for w in a.weights]
    out = Path(a.out)
    for s in ("train", "val", "test"):
        for sub in ("images", "labels"):
            (out / s / sub).mkdir(parents=True, exist_ok=True)
    vids = sorted(glob.glob(f"{REPO_ROOT / VIDEOS}/*/*"))
    vids = [v for v in vids if Path(v).stem not in EXCLUDE and Path(v).suffix.lower() in (".mov", ".mp4")]
    kept = 0
    for v in vids:
        cap = cv2.VideoCapture(v)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        k = a.per_clip if "/indoor/" in v else a.per_video
        frames = []  # (index, frame, [(cls, conf, box)])
        for i in np.linspace(n * 0.02, n * 0.98, k).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, f = cap.read()
            if not ok:
                continue
            h, w = f.shape[:2]
            boxes = []
            for m in models:
                r = m(f, imgsz=min(1920, max(h, w) // 32 * 32), conf=a.conf, verbose=False)[0]
                for b, c, p in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
                    if not any(int(c) == bc and iou(b, bb) > 0.5 for bc, _, bb in boxes):
                        boxes.append((int(c), p, b))
            frames.append((int(i), f, boxes))
        seen: dict[tuple, int] = {}
        for _, f, boxes in frames:
            h, w = f.shape[:2]
            for cell in {(round((b[0] + b[2]) / 2 / w * 50), round((b[1] + b[3]) / 2 / h * 50)) for c, _, b in boxes if c == 0}:
                seen[cell] = seen.get(cell, 0) + 1
        static = {c for c, s in seen.items() if s >= 0.4 * max(len(frames), 1)}
        added = 0
        for i, f, boxes in frames:
            h, w = f.shape[:2]
            keep = [(c, b) for c, _, b in boxes
                    if c == 1 or (round((b[0] + b[2]) / 2 / w * 50), round((b[1] + b[3]) / 2 / h * 50)) not in static]
            if not any(c == 0 for c, _ in keep):
                continue
            lines = [f"{c} {(b[0] + b[2]) / 2 / w:.6f} {(b[1] + b[3]) / 2 / h:.6f} {(b[2] - b[0]) / w:.6f} {(b[3] - b[1]) / h:.6f}"
                     for c, b in keep]
            if w > 1920:
                f = cv2.resize(f, (1920, int(h * 1920 / w)), interpolation=cv2.INTER_AREA)
            name = f"pl_{Path(v).parent.name}_{Path(v).stem}_{i:06d}"
            cv2.imwrite(str(out / "train" / "images" / f"{name}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 92])
            (out / "train" / "labels" / f"{name}.txt").write_text("\n".join(lines) + "\n")
            added += 1
        kept += added
        print(f"{Path(v).name}: {added}/{len(frames)} frames kept, {len(static)} static spots", flush=True)
    print(f"pseudo-labelled frames: {kept}")
    if a.base:
        base = Path(a.base).resolve()
        for s in ("train", "val", "test"):
            for sub in ("images", "labels"):
                for p in (base / s / sub).iterdir():
                    dst = out / s / sub / p.name
                    if not dst.exists():
                        dst.symlink_to(p)
        (out / "data.yaml").write_text((base / "data.yaml").read_text().replace(f"path: {base}", f"path: {out.resolve()}"))


if __name__ == "__main__":
    main()
