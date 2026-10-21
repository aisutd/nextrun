"""Train the court-keypoint pose model used by court method C (nextrun_cv/court/keypoints.py).

Dataset: YOLO pose format, ONE object per image (class 0 = "court") whose keypoints follow
`template.keypoint_order()` exactly; invisible landmarks get visibility 0.

  # 1. public NBA court dataset, converted to our schema
  python train/prepare_court_dataset.py --out data/court_kp
  # 2. train (GPU/Colab: --model yolo11s-pose.pt --imgsz 960 --epochs 150)
  python train/train_court_keypoints.py --data data/court_kp/court.yaml
  # best weights are copied to models/court_keypoints.pt

Fine-tuning on your own courts: add ~50-200 labeled frames to data/court_kp/train (same schema) and
re-run step 2 starting from --model models/court_keypoints.pt. `--write-yaml` writes an empty dataset
YAML for a fresh labeling project.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.court import template  # noqa: E402


def write_yaml(path: str, root: str) -> None:
    names = template.keypoint_order()
    lines = [
        f"path: {root}",
        "train: train/images",
        "val: val/images",
        f"kpt_shape: [{len(names)}, 3]",
        f"flip_idx: {template.keypoint_flip_idx()}",
        "names:",
        "  0: court",
        "# keypoint order:",
        *[f"#  {i}: {n}" for i, n in enumerate(names)],
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")
    print(f"wrote {path} ({len(names)} keypoints)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-yaml")
    ap.add_argument("--root", default="data/court")
    ap.add_argument("--data", default=str(ROOT / "data" / "court_kp" / "court.yaml"))
    ap.add_argument("--model", default="yolo11n-pose.pt")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--time", type=float, default=None, help="training budget in hours (overrides epochs)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None)
    ap.add_argument("--name", default="court_kp")
    ap.add_argument("--out", default=str(ROOT / "models" / "court_keypoints.pt"))
    a = ap.parse_args()
    if a.write_yaml:
        write_yaml(a.write_yaml, a.root)
        return
    from ultralytics import YOLO

    model = YOLO(a.model)
    # No mosaic: the model must see whole courts to learn the global layout. Strong color jitter because
    # the public data is NBA hardwood and our footage is gyms / outdoor courts.
    model.train(
        data=a.data, imgsz=a.imgsz, epochs=a.epochs, time=a.time, batch=a.batch, device=a.device,
        project=str(ROOT / "runs"), name=a.name, exist_ok=True, patience=40,
        mosaic=0.0, fliplr=0.5, degrees=3, translate=0.1, scale=0.35, perspective=0.0005,
        hsv_h=0.05, hsv_s=0.7, hsv_v=0.5, erasing=0.0, close_mosaic=0,
    )
    best = Path(model.trainer.best)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(best, a.out)
    print(f"copied {best} -> {a.out}")


if __name__ == "__main__":
    main()
