"""Train (or fine-tune) the court or ball+rim model and install the result into models/.

  python scripts/train.py court --data data/court24/data.yaml                 # from models/court_model.pt
  python scripts/train.py ball  --data data/ball_rim/data.yaml --model yolo11s.pt
  python scripts/train.py court --data ... --epochs 1 --fraction 0.05 --no-install   # smoke test (CPU)

Defaults fine-tune from the current model when its classes/keypoints match, so the team's existing
training isn't thrown away. The previous weights are kept as models/<name>.prev.pt. GPU strongly
recommended (Colab: notebooks/NextRun_Train.ipynb).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT, ModelConfig  # noqa: E402

TASKS = {
    #        installed weights                                default start   imgsz  epochs
    "court": (Path(ModelConfig().court_keypoint_weights), "models/court_model.pt", 1280, 150),
    "ball": (Path(ModelConfig().ball_hoop_weights), "yolo11s.pt", 1280, 120),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", choices=sorted(TASKS))
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", help="start weights (default: current court model / yolo11s.pt for ball)")
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--batch", type=int, default=-1, help="-1 = auto (fits GPU memory)")
    ap.add_argument("--fraction", type=float, default=1.0, help="train on a fraction of the data (smoke tests)")
    ap.add_argument("--device")
    ap.add_argument("--name")
    ap.add_argument("--no-install", action="store_true", help="don't copy best.pt into models/")
    a = ap.parse_args()

    from ultralytics import YOLO

    installed, start, imgsz, epochs = TASKS[a.task]
    start = a.model or str(REPO_ROOT / start if start.startswith("models/") else start)
    model = YOLO(start)
    res = model.train(
        data=a.data, imgsz=a.imgsz or imgsz, epochs=a.epochs or epochs, batch=a.batch, fraction=a.fraction,
        device=a.device, project=str(REPO_ROOT / "runs" / a.task), name=a.name or a.task, exist_ok=True,
        patience=30, cos_lr=True, close_mosaic=10,
        # sports footage: allow scale/translation, keep colours mostly real (jerseys / court paint matter)
        degrees=0.0, hsv_h=0.01, scale=0.5, translate=0.1, fliplr=0.5,
    )
    best = Path(res.save_dir) / "weights" / "best.pt"
    print(f"best weights: {best}")
    if not a.no_install and best.exists():
        if installed.exists():
            shutil.copyfile(installed, installed.with_suffix(".prev.pt"))
        shutil.copyfile(best, installed)
        print(f"installed -> {installed} (previous kept as {installed.with_suffix('.prev.pt').name})")


if __name__ == "__main__":
    main()
