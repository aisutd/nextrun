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
        self._half = cfg.use_half()

    def update(self, frame: np.ndarray) -> list[PlayerObs]:
        res = self.model.track(
            frame,
            persist=True,
            tracker=self.cfg.tracker_cfg,
            classes=[0],
            conf=self.cfg.player_conf,
            imgsz=self.cfg.input_size(frame.shape),
            device=self.cfg.device,
            iou=self.cfg.player_iou,
            max_det=self.cfg.player_max_det,
            agnostic_nms=True,
            half=self._half,
            verbose=False,
        )[0]
        boxes = res.boxes
        if boxes is None or boxes.id is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.int().cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        kps = res.keypoints.data.cpu().numpy() if res.keypoints is not None else None
        H = frame.shape[0]
        out = [
            PlayerObs(
                track_id=int(ids[i]),
                bbox=tuple(float(v) for v in xyxy[i]),
                conf=float(confs[i]),
                keypoints=None if kps is None else kps[i].astype(float),
            )
            for i in range(len(ids))
            if xyxy[i][3] - xyxy[i][1] >= self.cfg.player_min_height * H  # tiny boxes: crowd, noise
        ]
        return dedupe_players(out, self.cfg.player_dedupe_iou)

    def reset(self) -> None:
        """Forget tracks (next frame is from a different video / unrelated image)."""
        self.model.predictor = None


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def dedupe_players(players: list[PlayerObs], thr: float = 0.75) -> list[PlayerObs]:
    """One box per body: when two tracks sit on (almost) the same box, keep the more confident one."""
    keep: list[PlayerObs] = []
    for p in sorted(players, key=lambda q: -q.conf):
        if all(_iou(p.bbox, k.bbox) < thr for k in keep):
            keep.append(p)
    return keep
