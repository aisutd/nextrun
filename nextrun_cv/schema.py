"""Core per-frame data model shared by detection, court, identity, events and viz stages."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

# COCO-17 keypoint indices produced by YOLO pose models
KP_NOSE = 0
KP_L_SHOULDER, KP_R_SHOULDER = 5, 6
KP_L_WRIST, KP_R_WRIST = 9, 10
KP_L_HIP, KP_R_HIP = 11, 12
KP_L_ANKLE, KP_R_ANKLE = 15, 16
KP_MIN_CONF = 0.3


@dataclass
class PlayerObs:
    track_id: int
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (image px)
    conf: float = 1.0
    keypoints: np.ndarray | None = None  # (17, 3): x, y, conf
    court_xy: tuple[float, float] | None = None  # feet position in court meters

    @property
    def height(self) -> float:
        return max(1.0, self.bbox[3] - self.bbox[1])

    @property
    def center(self) -> tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)

    @property
    def feet(self) -> tuple[float, float]:
        """Ground contact point: ankle midpoint if visible, else bbox bottom-center."""
        kp = self.keypoints
        if kp is not None:
            ank = kp[[KP_L_ANKLE, KP_R_ANKLE]]
            ok = ank[:, 2] > KP_MIN_CONF
            if ok.any():
                return (float(ank[ok, 0].mean()), float(max(ank[ok, 1].max(), self.bbox[3] - 0.02 * self.height)))
        return ((self.bbox[0] + self.bbox[2]) / 2, self.bbox[3])

    def hands(self) -> list[tuple[float, float]]:
        """Visible wrist positions; falls back to the upper-middle of the bbox."""
        out = []
        if self.keypoints is not None:
            for k in (KP_L_WRIST, KP_R_WRIST):
                x, y, c = self.keypoints[k]
                if c > KP_MIN_CONF:
                    out.append((float(x), float(y)))
        if not out:
            x1, y1, x2, y2 = self.bbox
            out.append(((x1 + x2) / 2, y1 + 0.45 * (y2 - y1)))
        return out

    def highest_hand_y(self) -> float:
        return min(y for _, y in self.hands())


@dataclass
class BallObs:
    xy: tuple[float, float]
    radius: float = 6.0
    conf: float = 1.0
    interpolated: bool = False


@dataclass
class RimObs:
    bbox: tuple[float, float, float, float]
    conf: float = 1.0

    @property
    def width(self) -> float:
        return max(1.0, self.bbox[2] - self.bbox[0])

    @property
    def center(self) -> tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)


@dataclass
class FrameState:
    idx: int
    t: float  # seconds
    players: list[PlayerObs] = field(default_factory=list)
    ball: BallObs | None = None
    ball_candidates: list[BallObs] = field(default_factory=list)  # raw detections before tracking
    rims: list[RimObs] = field(default_factory=list)

    def player(self, track_id: int) -> PlayerObs | None:
        for p in self.players:
            if p.track_id == track_id:
                return p
        return None


@dataclass
class Event:
    type: str  # possession_gain, dribble, pass, shot, rebound, steal, turnover, assist, block
    frame: int
    t: float
    player: str | None = None  # resolved player id (name) or "track:<id>"
    team: str | None = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def frames_to_records(frames: list[FrameState]) -> list[dict]:
    """Flatten frames into JSON-serialisable dicts (keypoints -> lists)."""
    out = []
    for f in frames:
        out.append(
            {
                "idx": f.idx,
                "t": f.t,
                "players": [
                    {
                        "track_id": p.track_id,
                        "bbox": list(p.bbox),
                        "conf": p.conf,
                        "keypoints": None if p.keypoints is None else np.round(p.keypoints, 2).tolist(),
                        "court_xy": p.court_xy,
                    }
                    for p in f.players
                ],
                "ball": None if f.ball is None else asdict(f.ball),
                "ball_candidates": [asdict(b) for b in f.ball_candidates],
                "rims": [asdict(r) for r in f.rims],
            }
        )
    return out


def frames_from_records(recs: list[dict]) -> list[FrameState]:
    frames = []
    for r in recs:
        frames.append(
            FrameState(
                idx=r["idx"],
                t=r["t"],
                players=[
                    PlayerObs(
                        track_id=p["track_id"],
                        bbox=tuple(p["bbox"]),
                        conf=p["conf"],
                        keypoints=None if p["keypoints"] is None else np.asarray(p["keypoints"], dtype=float),
                        court_xy=None if p.get("court_xy") is None else tuple(p["court_xy"]),
                    )
                    for p in r["players"]
                ],
                ball=None if r["ball"] is None else BallObs(**{**r["ball"], "xy": tuple(r["ball"]["xy"])}),
                ball_candidates=[BallObs(**{**b, "xy": tuple(b["xy"])}) for b in r.get("ball_candidates", [])],
                rims=[RimObs(bbox=tuple(x["bbox"]), conf=x["conf"]) for x in r["rims"]],
            )
        )
    return frames
