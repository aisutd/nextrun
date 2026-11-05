"""Ball + rim detection (weights/ball_hoop/, active one in weights/active.json; classes ball/rim).

With `hint` (the players found in the same frame) the model runs on the play area cut out of the full-resolution
frame instead of the whole frame shrunk to the model size: in a wide 4K shot that is 2-3x more pixels on the ball for
the same compute. Every `ball_full_every` frames the whole frame is used so rims outside the crop are not lost."""
from __future__ import annotations

import numpy as np

from ..config import ModelConfig
from ..schema import BallObs, RimObs


class BallHoopDetector:
    def __init__(self, cfg: ModelConfig):
        from ultralytics import YOLO

        self.cfg = cfg
        self.model = YOLO(cfg.ball_hoop_weights)
        self._half = cfg.use_half()
        names = {int(k): str(v).lower() for k, v in self.model.names.items()}
        inv = {v: k for k, v in names.items()}
        self.ball_cls = inv.get("ball", inv.get("basketball", 0))
        self.rim_cls = inv.get("rim", inv.get("hoop", 1))
        self._rims: list[tuple] = []  # rim boxes from the latest frame that had any
        self._n = 0  # frames since the last full-frame pass

    # ------------------------------------------------------------------------------------------------------------
    def region(self, hint, shape) -> tuple[int, int, int, int] | None:
        """Play-area crop (x1, y1, x2, y2) for this frame, or None = use the whole frame."""
        c = self.cfg
        if not c.ball_crop or not hint or not self._rims or self._n >= c.ball_full_every:
            return None
        H, W = shape[:2]
        boxes = list(hint) + list(self._rims)
        x1, y1 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x2, y2 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        hs = float(np.median([b[3] - b[1] for b in hint]))
        mx = max(0.15 * (x2 - x1), 1.5 * hs)
        x1, x2 = max(0, x1 - mx), min(W, x2 + mx)
        y1, y2 = max(0, y1 - 2.0 * hs), min(H, y2 + 0.5 * hs)  # headroom: shots peak well above the rim
        if x2 - x1 < 32 or y2 - y1 < 32 or (x2 - x1) * (y2 - y1) > c.ball_crop_max_share * W * H:
            return None
        return int(x1), int(y1), int(np.ceil(x2)), int(np.ceil(y2))

    def detect(self, frame: np.ndarray, hint=None) -> tuple[list[BallObs], list[RimObs]]:
        """hint: bounding boxes of the players in this frame (enables the play-area crop)."""
        box = self.region(hint, frame.shape)
        if box is None:
            self._n = 0
            return self._run(frame, 0, 0, self.cfg.input_size(frame.shape, self.cfg.ball_max_imgsz))
        self._n += 1
        x1, y1, x2, y2 = box
        crop = np.ascontiguousarray(frame[y1:y2, x1:x2])
        long = max(crop.shape[:2]) // 32 * 32
        imgsz = int(np.clip(long, self.cfg.ball_crop_min, self.cfg.ball_max_imgsz))
        return self._run(crop, x1, y1, self.cfg.imgsz or imgsz)

    def _run(self, img: np.ndarray, ox: int, oy: int, imgsz: int) -> tuple[list[BallObs], list[RimObs]]:
        res = self.model.predict(
            img,
            conf=min(self.cfg.ball_conf, self.cfg.rim_conf),
            imgsz=imgsz,
            device=self.cfg.device,
            half=self._half,
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
                cx, cy = (b[0] + b[2]) / 2 + ox, (b[1] + b[3]) / 2 + oy
                balls.append(BallObs((float(cx), float(cy)), float(max(b[2] - b[0], b[3] - b[1]) / 2), float(s)))
            elif c == self.rim_cls and s >= self.cfg.rim_conf:
                rims.append(RimObs((float(b[0] + ox), float(b[1] + oy), float(b[2] + ox), float(b[3] + oy)), float(s)))
        if rims:
            self._rims = [r.bbox for r in rims]
        return balls, rims
