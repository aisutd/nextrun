"""Train (or fine-tune) the court or ball+rim model and install the result into models/.

  python src/scripts/train.py court --data data/court24/data.yaml                 # from models/court_model.pt
  python src/scripts/train.py ball  --data data/ball_rim/data.yaml --model yolo11s.pt
  python src/scripts/train.py court --data ... --epochs 1 --fraction 0.05 --no-install   # smoke test (CPU)
  python src/scripts/train.py court --name court_v2 --resume                  # continue after stopping (Ctrl+C)

Defaults fine-tune from the current model when its classes/keypoints match, so the team's existing
training isn't thrown away. The previous weights are kept as models/<name>.prev.pt. GPU strongly
recommended (full sequence: HANDOFF.md).
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
    ap.add_argument("--data", help="dataset yaml (not needed with --resume)")
    ap.add_argument("--model", help="start weights (default: current court model / yolo11s.pt for ball)")
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--hours", type=float, help="time budget; overrides --epochs (LR schedule fits the budget)")
    ap.add_argument("--batch", type=int, default=-1, help="-1 = auto (fits GPU memory)")
    ap.add_argument("--fraction", type=float, default=1.0, help="train on a fraction of the data (smoke tests)")
    ap.add_argument("--device")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--name")
    ap.add_argument("--no-install", action="store_true", help="don't copy best.pt into models/")
    ap.add_argument("--resume", action="store_true", help="continue the run --name from its last.pt (after a pause)")
    a = ap.parse_args()

    from ultralytics import YOLO

    installed, start, imgsz, epochs = TASKS[a.task]
    start = a.model or str(REPO_ROOT / start if start.startswith("models/") else start)
    if a.resume:  # continue a paused / stopped run from its last epoch (same settings, same run folder)
        last = REPO_ROOT / "results" / "runs" / a.task / (a.name or a.task) / "weights" / "last.pt"
        res = YOLO(str(last)).train(resume=True)
        print(f"best weights: {Path(res.save_dir) / 'weights' / 'best.pt'}")
        return
    model = YOLO(start)
    # sports footage: allow scale/translation, keep colours mostly real (jerseys / court paint matter)
    aug = dict(degrees=0.0, hsv_h=0.01, scale=0.5, translate=0.1, fliplr=0.5)
    if a.task == "court":
        # fixed-camera sources repeat one view for thousands of frames: warp it into new camera positions
        # (the keypoints move with the image) so the model doesn't memorize single viewpoints
        aug.update(degrees=5.0, perspective=0.0005, translate=0.2, mosaic=0.5)
    res = model.train(
        data=a.data, imgsz=a.imgsz or imgsz, epochs=a.epochs or epochs, time=a.hours, batch=a.batch,
        fraction=a.fraction, device=a.device, workers=a.workers, project=str(REPO_ROOT / "results" / "runs" / a.task),
        name=a.name or a.task, exist_ok=True, patience=30, cos_lr=True, close_mosaic=10, **aug,
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
