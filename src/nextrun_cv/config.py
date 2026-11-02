"""Pipeline configuration. Every threshold used by the event logic lives here so it can be tuned
per-venue / per-camera without touching code. Distances in image space are expressed relative to the
player's bounding-box height so they stay roughly scale-invariant across camera distances."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/nextrun_cv/config.py -> repo
# weights/<kind>/<run>.pt, one folder per model kind (players, ball_hoop, court); weights/active.json names the
# file the pipeline uses for each kind. Install a newly trained model with install_weights().
WEIGHTS_DIR = REPO_ROOT / "weights"
ACTIVE_WEIGHTS = WEIGHTS_DIR / "active.json"
_DEFAULT_ACTIVE = {"players": "players/yolo26m-pose.pt", "ball_hoop": "ball_hoop/ball_pseudo.pt",
                   "court": "court/court_synth.pt"}


def active_weights(kind: str) -> str:
    """Path of the weights the pipeline uses for `kind` ("players", "ball_hoop" or "court")."""
    try:
        active = json.loads(ACTIVE_WEIGHTS.read_text())
    except (OSError, ValueError):
        active = {}
    return str(WEIGHTS_DIR / active.get(kind, _DEFAULT_ACTIVE[kind]))


def install_weights(kind: str, src: str | Path, name: str) -> Path:
    """Save `src` as weights/<kind>/<name>.pt and make it the active model for `kind`. The previously active
    file stays where it is, so switching back is a one-line change in weights/active.json."""
    dst = WEIGHTS_DIR / kind / f"{name}.pt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).resolve() != dst.resolve():
        shutil.copyfile(src, dst)
    try:
        active = json.loads(ACTIVE_WEIGHTS.read_text())
    except (OSError, ValueError):
        active = dict(_DEFAULT_ACTIVE)
    active[kind] = dst.relative_to(WEIGHTS_DIR).as_posix()
    ACTIVE_WEIGHTS.write_text(json.dumps(active, indent=2) + "\n")
    return dst


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
    # defaults come from weights/active.json
    ball_hoop_weights: str = field(default_factory=lambda: active_weights("ball_hoop"))
    # pose model: person boxes + 17 COCO keypoints (pretrained; auto-downloaded on first use)
    player_weights: str = field(default_factory=lambda: active_weights("players"))
    court_keypoint_weights: str = field(default_factory=lambda: active_weights("court"))
    court_keypoint_config: str = str(WEIGHTS_DIR / "court" / "court_keypoints.json")
    tracker_cfg: str = str(WEIGHTS_DIR / "players" / "botsort_reid.yaml")
    # used instead when the camera moves (court.track.camera_moves): same tracker plus camera-motion compensation
    tracker_moving_cfg: str = str(WEIGHTS_DIR / "players" / "botsort_reid_moving.yaml")
    device: str | None = None  # None -> ultralytics picks cuda if available
    player_conf: float = 0.35
    ball_conf: float = 0.25
    rim_conf: float = 0.35
    # model input size. None = the frame's own long side (capped at max_imgsz): players and the ball are
    # small in wide fixed-camera shots, and downscaling a 4K frame to 1280 loses most of them
    imgsz: int | None = None
    max_imgsz: int = 3840
    # the ball/rim model is trained at 1024 and judged (check_ball_footage.py) at <= 1920; at 3840 it sees
    # objects at scales it never trained on (e.g. a frame-sized false "rim" on the outdoor clip)
    ball_max_imgsz: int = 1920

    def input_size(self, frame_shape, cap: int | None = None) -> int:
        if self.imgsz:
            return self.imgsz
        return min(cap or self.max_imgsz, max(frame_shape[:2]) // 32 * 32)


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
    # a make crosses the rim plane downward near the rim's middle. Rim boxes usually include the net, so the
    # plane is just below the box top, not its centre (a ball off the front rim drops through the box too).
    make_plane: float = 0.1  # rim plane below the box top, in rim widths (capped at half the box height)
    make_center_tol: float = 0.25  # |x - rim centre| at the crossing, in rim widths
    shot_min_rise_frac: float = 0.15  # ball must rise this fraction of shooter bbox height after release
    airball_max_rim_dist: float = 4.0  # flight peaking above rim within this many rim widths -> attempt
    assist_window_s: float = 3.0
    assist_max_dribbles: int = 2
    dunk_release_rim_dist: float = 1.5  # release within this many rim widths of the rim
    dribble_min_amp: float = 0.15  # bounce amplitude as fraction of holder bbox height
    rebound_window_s: float = 6.0
    # after a make the other team inbounds under that basket: a flight through the same rim this soon after is
    # the inbound pass, not a shot
    after_make_dead_s: float = 5.0
    # the rebounding team is the one holding the ball longest this long after the first touch (the first touch in
    # a crowded paint is often a wrong attribution or a tip); 0 = the first toucher's team
    rebound_control_s: float = 3.0
    # shot position: the shooter's feet in the frame they are lowest in the image this long before release (on the
    # floor; at release a jump shooter is in the air and the raised feet map to the wrong court spot)
    shot_pos_lookback_s: float = 1.0
    three_close_margin_m: float = 0.46  # within 1.5 ft of the 3PT line ~ court-mapping error: flag as uncertain


@dataclass
class FusionConfig:
    """Geometry that ties the models together (see nextrun_cv/fusion.py)."""

    min_court_conf: float = 0.35  # below this a court calibration is not used for positions / 2PT-3PT
    # a detected rim must sit straight above the floor point under its hoop (projected by the court fit):
    rim_max_offset: float = 1.0  # max horizontal offset, in rim widths
    rim_height_range: tuple[float, float] = (2.5, 7.5)  # rim height above that point, in rim widths (3.05 m ~ 6.7)
    off_court_margin_m: float = 1.0  # people further outside the court than this are dropped
    # playing area [x_min, x_max, y_min, y_max] in court meters (venue profiles set it, e.g. a 3x3 half
    # court); None = the whole court
    play_area: list[float] | None = None


@dataclass
class CameraConfig:
    """Fixed vs moving camera (see court/track.py)."""

    mode: str = "auto"  # auto | static | moving
    moving_px: float = 0.01  # moving when frames ~0.5 s apart shift by more than this share of the frame width
    drift_px: float = 0.02  # ... or when the view drifts this far from the first frame over the clip
    keyframe_s: float = 0.2  # moving camera: run the court model every this many seconds
    window_s: float = 1.0  # each frame combines the court fits within this many seconds
    spread_m: float = 1.0  # per-frame confidence decays with the fits' disagreement in meters (exp(-d / spread_m))
    motion_width: int = 640  # frames are downscaled to this width to measure camera motion


@dataclass
class TeamConfig:
    n_teams: int = 2
    sample_every: int = 5  # sample torso colors every N frames per track
    max_other_share: float = 0.0  # >0: a small extra colour cluster (referees) gets no team (identity.teams)


@dataclass
class StitchConfig:
    """Joining a lost track to the track that picks the same player up again (identity.stitch)."""

    enabled: bool = True
    max_gap_s: float = 10.0  # longer gaps are joined on colour alone (the reach covers the court): re-entries on a pan
    velocity_s: float = 0.5  # end velocity measured over (and extrapolated for at most) this long
    vmax_mps: float = 7.0  # reach on the court: r0_m + vmax_mps * gap
    r0_m: float = 1.0
    vmax_hps: float = 3.0  # reach in the image without a court, in player heights per second
    r0_h: float = 1.0
    max_color_dist: float = 0.5  # 1 - cosine similarity of torso colour embeddings
    w_color: float = 1.0


@dataclass
class Config:
    # high-school court matches the court-keypoint model's geometry (84 x 50 ft, 19'9" arc)
    court: CourtSpec = field(default_factory=lambda: CourtSpec.preset("highschool"))
    models: ModelConfig = field(default_factory=ModelConfig)
    ball: BallTrackConfig = field(default_factory=BallTrackConfig)
    possession: PossessionConfig = field(default_factory=PossessionConfig)
    events: EventConfig = field(default_factory=EventConfig)
    teams: TeamConfig = field(default_factory=TeamConfig)
    stitch: StitchConfig = field(default_factory=StitchConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
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
