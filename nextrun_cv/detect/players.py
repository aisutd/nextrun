"""Player detection + tracking with a YOLO pose model and Ultralytics' built-in BoT-SORT.

Replaces the TrackID3x3 / YOLOX notebook setup (repo clone + sed patches) with a single
`ultralytics` dependency. Pose keypoints are kept because the event logic uses wrists (possession,
shooting) and ankles (feet position for court mapping)."""
from __future__ import annotations

import numpy as np

from ..config import ModelConfig
from ..schema import PlayerObs


class PlayerTracker:
    def __init__(self, cfg: ModelConfig):
        from ultralytics import YOLO  # lazy: heavy import, not needed for offline analysis/tests

        self.cfg = cfg
        self.model = YOLO(cfg.player_weights)

    def update(self, frame: np.ndarray) -> list[PlayerObs]:
        res = self.model.track(
            frame,
            persist=True,
            tracker=self.cfg.tracker_cfg,
            classes=[0],
            conf=self.cfg.player_conf,
            imgsz=self.cfg.imgsz,
            device=self.cfg.device,
            verbose=False,
        )[0]
        boxes = res.boxes
        if boxes is None or boxes.id is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.int().cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        kps = res.keypoints.data.cpu().numpy() if res.keypoints is not None else None
        return [
            PlayerObs(
                track_id=int(ids[i]),
                bbox=tuple(float(v) for v in xyxy[i]),
                conf=float(confs[i]),
                keypoints=None if kps is None else kps[i].astype(float),
            )
            for i in range(len(ids))
        ]

    def reset(self) -> None:
        """Forget tracks (next frame is from a different video / unrelated image)."""
        self.model.predictor = None
