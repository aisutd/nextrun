"""Ball/rim models on your own (unlabelled) footage: in how many sampled frames does each model find the ball
and the rim? Catches models that score well on labelled sets but miss small, distant balls on real cameras.

  python src/scripts/check_ball_footage.py VIDEO [VIDEO ...] --weights weights/ball_hoop/ball_pseudo.pt weights/ball_hoop/ball_yolo26l.pt

Frames are sampled evenly from each video and run at native resolution (as the pipeline does, capped at 1920).
In 3x3 / pickup footage the ball is in play in most frames, so a higher "ball found" rate is better as long as
the boxes are real: --save writes the frames where the models disagree, to look at.
A "ball" at the same spot in >= 40 % of a video's sampled frames is a static object (a spare ball by the court,
a light), not the ball in play: "ball_found" ignores those spots ("ball_found_all" counts them).
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
    stats = {w: {"frames": 0, "ball": 0, "ball_all": 0, "rim": 0, "ball_conf": []} for w in a.weights}
    n_saved = 0
    for video in a.videos:
        balls = {w: [] for w in a.weights}  # per sampled frame: [(conf, cell)] of ball boxes
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
                fh, fw = frame.shape[:2]
                balls[w].append([(c, (round((x1 + x2) / 2 / fw * 50), round((y1 + y2) / 2 / fh * 50)))
                                 for (x1, y1, x2, y2), k, c in zip(r.boxes.xyxy.tolist(), cls, conf) if k == 0])
                s = stats[w]
                s["frames"] += 1
                s["ball_all"] += ball >= a.conf
                s["rim"] += any(k == 1 and c >= a.conf for k, c in zip(cls, conf))
                found[w] = (ball >= a.conf, r)
            if a.save and len({f for f, _ in found.values()}) > 1:
                Path(a.save).mkdir(parents=True, exist_ok=True)
                for j, (w, (_, r)) in enumerate(found.items()):
                    cv2.imwrite(str(Path(a.save) / f"{Path(video).stem}_{i:06d}_model{j}.jpg"), r.plot())
                n_saved += 1
        for w, frames in balls.items():  # drop static spots (cells on a 50 x 50 grid), then count
            seen: dict[tuple, int] = {}
            for fr in frames:
                for cell in {c for _, c in fr}:
                    seen[cell] = seen.get(cell, 0) + 1
            static = {c for c, k in seen.items() if k >= 0.4 * len(frames)}
            for fr in frames:
                top = max((c for c, cell in fr if cell not in static), default=0.0)
                stats[w]["ball"] += top >= a.conf
                stats[w]["ball_conf"].append(top)
    report = {}
    for w, s in stats.items():
        report[w] = {"frames": s["frames"], "ball_found": s["ball"], "ball_found_all": s["ball_all"], "rim_found": s["rim"],
                     "ball_conf_median": round(float(np.median(s["ball_conf"])), 3) if s["ball_conf"] else 0.0}
        print(f"{w}: ball found {s['ball']}/{s['frames']} ({s['ball_all']} incl. static spots), rim found {s['rim']}/{s['frames']}, "
              f"median top ball confidence {report[w]['ball_conf_median']}")
    if a.save:
        print(f"{n_saved} disagreements saved to {a.save}")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
