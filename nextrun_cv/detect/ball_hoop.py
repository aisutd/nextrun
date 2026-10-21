"""Ball + rim detection using the team's YOLOv8n model (models/ball_hoop_model.pt, classes ball/rim)."""
from __future__ import annotations

import numpy as np

from ..config import ModelConfig
from ..schema import BallObs, RimObs


class BallHoopDetector:
    def __init__(self, cfg: ModelConfig):
        from ultralytics import YOLO

        self.cfg = cfg
        self.model = YOLO(cfg.ball_hoop_weights)
        names = {int(k): str(v).lower() for k, v in self.model.names.items()}
        inv = {v: k for k, v in names.items()}
        self.ball_cls = inv.get("ball", inv.get("basketball", 0))
        self.rim_cls = inv.get("rim", inv.get("hoop", 1))

    def detect(self, frame: np.ndarray) -> tuple[list[BallObs], list[RimObs]]:
        res = self.model.predict(
            frame,
            conf=min(self.cfg.ball_conf, self.cfg.rim_conf),
            imgsz=self.cfg.imgsz,
            device=self.cfg.device,
            verbose=False,
        )[0]
        balls: list[BallObs] = []
        rims: list[RimObs] = []
        if res.boxes is None:
            return balls, rims
        xyxy = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.int().cpu().numpy()
        conf = res.boxes.conf.cpu().numpy()
        for b, c, s in zip(xyxy, cls, conf):
            if c == self.ball_cls and s >= self.cfg.ball_conf:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                balls.append(BallObs((float(cx), float(cy)), float(max(b[2] - b[0], b[3] - b[1]) / 2), float(s)))
            elif c == self.rim_cls and s >= self.cfg.rim_conf:
                rims.append(RimObs(tuple(float(v) for v in b), float(s)))
        return balls, rims
