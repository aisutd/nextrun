"""Pipeline configuration. Every threshold used by the event logic lives here so it can be tuned
per-venue / per-camera without touching code. Distances in image space are expressed relative to the
player's bounding-box height so they stay roughly scale-invariant across camera distances."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CourtSpec:
    """Court dimensions in meters. Court coordinate frame: origin at center court, +x toward the
    right basket along the length, +y across the width."""

    name: str = "fiba"
    length: float = 28.0
    width: float = 15.0
    three_pt_radius: float = 6.75
    corner_three_offset: float = 0.9  # distance of corner-three straight line from the sideline
    hoop_from_baseline: float = 1.575  # baseline to rim center
    paint_width: float = 4.9
    ft_line_from_baseline: float = 5.8
    rim_height: float = 3.05
    center_circle_radius: float = 1.8
    backboard_from_baseline: float = 1.2  # baseline to backboard face (court-keypoint landmark)
    # sideline hash marks (NBA/NCAA coaching-box line, 28 ft from the baseline); None = court has none
    sideline_hash_from_baseline: float | None = None

    @staticmethod
    def preset(name: str) -> "CourtSpec":
        presets = {
            "fiba": CourtSpec(),
            "nba": CourtSpec("nba", 28.65, 15.24, 7.24, 0.91, 1.6, 4.88, 5.79, 3.05, 1.83, 1.22, 8.53),
            # NFHS: 19'9" arc; corner line is effectively where the arc meets 1.6 m from the sideline
            "highschool": CourtSpec("highschool", 25.6, 15.24, 6.02, 1.6, 1.6, 3.66, 5.79, 3.05, 1.83, 1.22),
            "ncaa": CourtSpec("ncaa", 28.65, 15.24, 6.75, 1.02, 1.6, 3.66, 5.79, 3.05, 1.83, 1.22, 8.53),
        }
        if name not in presets:
            raise ValueError(f"unknown court preset {name!r}; choose from {sorted(presets)}")
        return presets[name]


@dataclass
class ModelConfig:
    ball_hoop_weights: str = str(REPO_ROOT / "models" / "ball_hoop_model.pt")
    # pose model: person boxes + 17 COCO keypoints (auto-downloaded on first use)
    player_weights: str = str(REPO_ROOT / "models" / "yolo11m-pose.pt")
    court_keypoint_weights: str = str(REPO_ROOT / "models" / "court_model.pt")
    court_keypoint_config: str = str(REPO_ROOT / "configs" / "court_keypoints.json")
    tracker_cfg: str = str(REPO_ROOT / "configs" / "botsort_reid.yaml")
    device: str | None = None  # None -> ultralytics picks cuda if available
    player_conf: float = 0.35
    ball_conf: float = 0.25
    rim_conf: float = 0.35
    # model input size. None = the frame's own long side (capped at max_imgsz): players and the ball are
    # small in wide fixed-camera shots, and downscaling a 4K frame to 1280 loses most of them
    imgsz: int | None = None
    max_imgsz: int = 3840

    def input_size(self, frame_shape) -> int:
        if self.imgsz:
            return self.imgsz
        return min(self.max_imgsz, max(frame_shape[:2]) // 32 * 32)


@dataclass
class BallTrackConfig:
    max_gap_frames: int = 8  # linearly interpolate ball through occlusions up to this many frames
    max_jump_px_per_frame: float = 120.0  # reject detections implausibly far from the prediction
    process_noise: float = 4.0
    measurement_noise: float = 6.0


@dataclass
class PossessionConfig:
    gain_dist: float = 0.30  # ball-to-wrist distance (x bbox height) to start possession
    control_expand: float = 0.25  # bbox expansion (fraction) defining the "control zone" while holding
    gain_frames: int = 3  # consecutive frames near a player to grant possession
    lose_frames: int = 4  # consecutive frames outside control zone to drop possession


@dataclass
class EventConfig:
    rim_zone_w: float = 1.5  # rim-zone half-width in rim widths
    rim_zone_h: float = 3.0  # rim-zone height above the rim in rim widths
    make_window_s: float = 2.0  # time after reaching rim zone to observe the ball pass through
    shot_min_rise_frac: float = 0.15  # ball must rise this fraction of shooter bbox height after release
    airball_max_rim_dist: float = 4.0  # flight peaking above rim within this many rim widths -> attempt
    assist_window_s: float = 3.0
    assist_max_dribbles: int = 2
    dunk_release_rim_dist: float = 1.5  # release within this many rim widths of the rim
    dribble_min_amp: float = 0.15  # bounce amplitude as fraction of holder bbox height
    rebound_window_s: float = 6.0
    three_close_margin_m: float = 0.46  # within 1.5 ft of the 3PT line ~ court-mapping error: flag as uncertain


@dataclass
class FusionConfig:
    """Geometry that ties the models together (see nextrun_cv/fusion.py)."""

    min_court_conf: float = 0.35  # below this a court calibration is not used for positions / 2PT-3PT
    # a detected rim must sit straight above the floor point under its hoop (projected by the court fit):
    rim_max_offset: float = 1.0  # max horizontal offset, in rim widths
    rim_height_range: tuple[float, float] = (2.5, 7.5)  # rim height above that point, in rim widths (3.05 m ~ 6.7)
    off_court_margin_m: float = 1.0  # people further outside the court than this are dropped


@dataclass
class TeamConfig:
    n_teams: int = 2
    sample_every: int = 5  # sample torso colors every N frames per track


@dataclass
class Config:
    # high-school court matches the court-keypoint model's geometry (84 x 50 ft, 19'9" arc)
    court: CourtSpec = field(default_factory=lambda: CourtSpec.preset("highschool"))
    models: ModelConfig = field(default_factory=ModelConfig)
    ball: BallTrackConfig = field(default_factory=BallTrackConfig)
    possession: PossessionConfig = field(default_factory=PossessionConfig)
    events: EventConfig = field(default_factory=EventConfig)
    teams: TeamConfig = field(default_factory=TeamConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    court_method: str = "auto"  # auto | keypoints | lines | manual
    court_calib_frames: int = 10
    stride: int = 1  # process every Nth frame
    max_frames: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        return _from_dict(cls, d)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        return cls.from_dict(json.loads(Path(path).read_text()))


def _from_dict(cls, d: dict):
    kwargs = {}
    for f in fields(cls):
        if f.name not in d:
            continue
        v = d[f.name]
        default = f.default_factory() if callable(f.default_factory) else None  # type: ignore[misc]
        if is_dataclass(default) and isinstance(v, dict):
            v = _from_dict(type(default), v)
        kwargs[f.name] = v
    return cls(**kwargs)
