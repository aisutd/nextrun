"""Ball+rim model accuracy per source/domain on a ball_rim dataset (src/scripts/build_ball_rim_dataset.py).

  python src/scripts/eval_ball_rim.py --data data/ball_rim [--weights models/ball_hoop_model.pt] [--split test]

Per source: precision, recall and mAP50 for ball and rim separately (ball recall is what limits shots,
makes and rebounds). Uses the per-source image lists the builder writes to data/ball_rim/lists/.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT, ModelConfig  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(REPO_ROOT / "data" / "ball_rim"))
    ap.add_argument("--weights", default=ModelConfig().ball_hoop_weights)
    ap.add_argument("--split", default="test")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--device")
    a = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(a.weights)
    if {int(k): str(v).lower() for k, v in model.names.items()} != {0: "ball", 1: "rim"}:
        raise SystemExit(f"{a.weights}: classes {model.names}, expected {{0: ball, 1: rim}}")
    report = {}
    for lst in sorted((Path(a.data).resolve() / "lists").glob(f"*_{a.split}.txt")):
        src = lst.name[: -len(f"_{a.split}.txt")]
        with tempfile.TemporaryDirectory() as td:
            y = Path(td) / "data.yaml"
            y.write_text(f"train: {lst.as_posix()}\nval: {lst.as_posix()}\nnames:\n  0: ball\n  1: rim\n")
            m = model.val(data=str(y), split="val", imgsz=a.imgsz, device=a.device, plots=False, verbose=False)
        row = {"images": sum(1 for _ in lst.open())}
        for i, name in ((0, "ball"), (1, "rim")):
            if i in m.box.ap_class_index:
                j = list(m.box.ap_class_index).index(i)
                p, r, ap50, _ = m.box.class_result(j)
                row[name] = {"P": round(float(p), 3), "R": round(float(r), 3), "mAP50": round(float(ap50), 3)}
        report[src] = row
        print(f"{src:40s} {row}")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
