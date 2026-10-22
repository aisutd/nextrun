"""Ball/rim models on your own (unlabelled) footage: in how many sampled frames does each model find the ball
and the rim? Catches models that score well on labelled sets but miss small, distant balls on real cameras.

  python src/scripts/check_ball_footage.py VIDEO [VIDEO ...] --weights models/ball_hoop_model.pt runs/.../best.pt

Frames are sampled evenly from each video and run at native resolution (as the pipeline does, capped at 1920).
In 3x3 / pickup footage the ball is in play in most frames, so a higher "ball found" rate is better as long as
the boxes are real: --save writes the frames where the models disagree, to look at.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--weights", nargs="+", required=True)
    ap.add_argument("--frames", type=int, default=15, help="frames sampled per video")
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--max-imgsz", type=int, default=1920)
    ap.add_argument("--save", help="folder for frames where the models disagree on the ball")
    a = ap.parse_args()

    from ultralytics import YOLO

    models = {w: YOLO(w) for w in a.weights}
    stats = {w: {"frames": 0, "ball": 0, "rim": 0, "ball_conf": []} for w in a.weights}
    n_saved = 0
    for video in a.videos:
        cap = cv2.VideoCapture(video)
        for i in np.linspace(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1, a.frames).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok:
                continue
            imgsz = min(a.max_imgsz, max(frame.shape[:2]) // 32 * 32)
            found = {}
            for w, m in models.items():
                r = m(frame, imgsz=imgsz, conf=0.05, verbose=False)[0]
                cls, conf = r.boxes.cls.tolist(), r.boxes.conf.tolist()
                ball = max((c for k, c in zip(cls, conf) if k == 0), default=0.0)
                s = stats[w]
                s["frames"] += 1
                s["ball"] += ball >= a.conf
                s["rim"] += any(k == 1 and c >= a.conf for k, c in zip(cls, conf))
                s["ball_conf"].append(ball)
                found[w] = (ball >= a.conf, r)
            if a.save and len({f for f, _ in found.values()}) > 1:
                Path(a.save).mkdir(parents=True, exist_ok=True)
                for j, (w, (_, r)) in enumerate(found.items()):
                    cv2.imwrite(str(Path(a.save) / f"{Path(video).stem}_{i:06d}_model{j}.jpg"), r.plot())
                n_saved += 1
    report = {}
    for w, s in stats.items():
        report[w] = {"frames": s["frames"], "ball_found": s["ball"], "rim_found": s["rim"],
                     "ball_conf_median": round(float(np.median(s["ball_conf"])), 3) if s["ball_conf"] else 0.0}
        print(f"{w}: ball found {s['ball']}/{s['frames']}, rim found {s['rim']}/{s['frames']}, "
              f"median top ball confidence {report[w]['ball_conf_median']}")
    if a.save:
        print(f"{n_saved} disagreements saved to {a.save}")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
