"""(Re)train the ball/rim detector. The current models/ball_hoop_model.pt is YOLOv8n trained at a
small input size; balls in wide pickup-game shots are often < 15 px, so a larger input size and a
bigger model usually improve ball recall substantially.

data.yaml (YOLO detect format, e.g. exported from Roboflow) must use names: {0: ball, 1: rim}.

  python scripts/train_ball_hoop.py --data /content/data.yaml --model yolo11s.pt --imgsz 1280 --epochs 100
"""
import argparse

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="yolo11s.pt", help="start from COCO weights or models/ball_hoop_model.pt to fine-tune")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--project", default="runs/ball_hoop")
    a = ap.parse_args()
    model = YOLO(a.model)
    model.train(data=a.data, imgsz=a.imgsz, epochs=a.epochs, batch=a.batch, project=a.project,
                mosaic=1.0, scale=0.5, fliplr=0.5, close_mosaic=10, patience=30)
    metrics = model.val()
    print(metrics.results_dict)
    print("copy best.pt to models/ball_hoop_model.pt when it beats the current model on your val clips")


if __name__ == "__main__":
    main()
