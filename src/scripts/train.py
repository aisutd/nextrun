"""Train (or fine-tune) the court or ball+rim model, save it in weights/ and make it the active model.

  python src/scripts/train.py court --data data/court24/data.yaml --name court_x   # from the active court model
  python src/scripts/train.py ball  --data data/ball_rim/data.yaml --model yolo26l.pt --name ball_x
  python src/scripts/train.py court --data ... --epochs 1 --fraction 0.05 --no-install   # smoke test (CPU)
  python src/scripts/train.py court --name court_x --resume                   # continue after stopping (Ctrl+C)

The run's best.pt is saved as weights/<court|ball_hoop>/<name>.pt and, unless --no-install, made the active
model in weights/active.json (the previous one stays in its folder). Training curves and the full run stay in
results/runs/<task>/<name>/. Pretrained starting points given by bare name (yolo26m-pose.pt) are kept in
weights/pretrained/ and downloaded there on first use. GPU strongly recommended (full sequence: HANDOFF.md).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT, WEIGHTS_DIR, active_weights, install_weights  # noqa: E402

TASKS = {
    #        weights/ kind   default start                imgsz  epochs
    "court": ("court", active_weights("court"), 1280, 150),
    "ball": ("ball_hoop", "yolo26l.pt", 1024, 120),
}


def resolve_start(model: str) -> str:
    """A bare pretrained name (yolo26m-pose.pt) lives in weights/pretrained/ (Ultralytics downloads it there)."""
    p = Path(model)
    if p.exists() or len(p.parts) > 1:
        return model
    return str(WEIGHTS_DIR / "pretrained" / p.name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", choices=sorted(TASKS))
    ap.add_argument("--data", help="dataset yaml (not needed with --resume)")
    ap.add_argument("--model", help="start weights (default: active court model / yolo26l.pt for ball)")
    ap.add_argument("--imgsz", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--hours", type=float, help="time budget; overrides --epochs (LR schedule fits the budget)")
    ap.add_argument("--batch", type=float, default=-1, help="-1 = auto (60%% of GPU memory); 0-1 = auto at that fraction")
    ap.add_argument("--lr0", type=float, help="initial learning rate (lower for polishing trained weights)")
    ap.add_argument("--cache", choices=["ram", "disk"], help="cache decoded images (faster epochs)")
    ap.add_argument("--fraction", type=float, default=1.0, help="train on a fraction of the data (smoke tests)")
    ap.add_argument("--device")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--name")
    ap.add_argument("--no-install", action="store_true", help="save best.pt in weights/ but don't make it the active model")
    ap.add_argument("--aug", action="append", default=[], metavar="KEY=VALUE",
                    help="override an augmentation setting, e.g. --aug perspective=0.0015 (repeatable)")
    ap.add_argument("--resume", action="store_true", help="continue the run --name from its last.pt (after a pause)")
    a = ap.parse_args()

    from ultralytics import YOLO

    kind, start, imgsz, epochs = TASKS[a.task]
    start = resolve_start(a.model or start)
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
    aug.update({k: float(v) for k, v in (kv.split("=", 1) for kv in a.aug)})
    res = model.train(
        data=a.data, imgsz=a.imgsz or imgsz, epochs=a.epochs or epochs, time=a.hours,
        batch=int(a.batch) if a.batch >= 1 or a.batch == -1 else a.batch, cache=a.cache or False,
        **({"lr0": a.lr0} if a.lr0 else {}),
        fraction=a.fraction, device=a.device, workers=a.workers, project=str(REPO_ROOT / "results" / "runs" / a.task),
        name=a.name or a.task, exist_ok=True, patience=30, cos_lr=True, close_mosaic=10, **aug,
    )
    best = Path(res.save_dir) / "weights" / "best.pt"
    print(f"best weights: {best}")
    if best.exists():
        name = a.name or a.task
        if a.no_install:
            dst = WEIGHTS_DIR / kind / f"{name}.pt"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(best, dst)
            print(f"saved -> {dst} (not active; see weights/active.json)")
        else:
            print(f"installed -> {install_weights(kind, best, name)} (active in weights/active.json)")


if __name__ == "__main__":
    main()
