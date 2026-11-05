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
    tracker_cfg: str = str(WEIGHTS_DIR / "players" / "botsort_fixed.yaml")
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
    # Wide 4K footage: the ball is a few pixels once the whole frame is shrunk to the model size (the footage check
    # found only 100/149 balls). So the ball/rim model looks at the play area (players + rims + headroom) cut out of
    # the full-resolution frame: same compute, ~2-3x the pixels on the ball. A full-frame pass every
    # `ball_full_every` frames keeps the rims up to date. Fixed cameras only (the pipeline turns it off for pans).
    ball_crop: bool = True
    ball_crop_min: int = 640  # a small play area is upscaled to at least this long side
    ball_crop_max_share: float = 0.7  # play area bigger than this share of the frame: just use the whole frame
    ball_full_every: int = 15

    # player detection clean-up (detect/players.py)
    player_iou: float = 0.6  # NMS overlap: two boxes overlapping more than this are the same person
    player_max_det: int = 40
    player_min_height: float = 0.04  # people shorter than this share of the frame height are crowd / noise
    player_dedupe_iou: float = 0.75  # two tracks on one body: keep the more confident box

    def use_half(self) -> bool:
        """Half precision is ~2x faster on an NVIDIA GPU with no real accuracy loss; the CPU and mps need float32."""
        try:
            import torch

            if self.device is None:
                return bool(torch.cuda.is_available())
        except Exception:  # noqa: BLE001
            return False
        return str(self.device).startswith("cuda") or str(self.device).isdigit()

    def input_size(self, frame_shape, cap: int | None = None) -> int:
        if self.imgsz:
            return self.imgsz
        return min(cap or self.max_imgsz, max(frame_shape[:2]) // 32 * 32)


@dataclass
class BallTrackConfig:
    max_gap_frames: int = 8  # linearly interpolate ball through occlusions up to this many frames
    max_jump_px_per_frame: float = 120.0  # (legacy) fixed-pixel gate; the tracker now scales its gate with player height
    max_jump_heights: float = 0.8  # ball may move at most this many player-heights between analysed frames (a hard pass is ~0.4)
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
    # --- shot or pass? A shot is thrown AT the rim: the ball's path has to come within `shot_reach_w` rim widths of the
    # rim (a lob that merely crosses the rim area in the image, or flies past it, is a pass). A "miss" whose path only
    # just reaches the rim (> `shot_sure_reach_w`) or an airball counts only if the next touch looks like a rebound.
    shot_reach_w: float = 1.3
    shot_sure_reach_w: float = 0.8
    shot_max_dist_m: float = 14.0  # nobody shoots from further than this from the basket (when the court is known)
    shot_min_rise_frac: float = 0.15  # ball must rise this fraction of shooter bbox height after release
    airball_max_rim_dist: float = 4.0  # flight peaking above rim within this many rim widths -> attempt
    assist_window_s: float = 3.0
    assist_max_dribbles: int = 2
    dunk_release_rim_dist: float = 1.5  # release within this many rim widths of the rim
    dribble_min_amp: float = 0.15  # bounce amplitude as fraction of holder bbox height
    rebound_window_s: float = 6.0
    # --- a rebound only follows a real missed shot (a pass that happens to fly near the hoop is just a pass) ------
    # a missed shot's ball got up to the rim: its highest point is at most this many rim widths below the rim top
    miss_min_apex_w: float = 0.5
    # a flight that carries on past the rim in the same direction at the same speed is a pass, not a bounce off it
    pass_through_cos: float = 0.97
    pass_through_speed_ratio: float = 0.8  # speed after / before the rim within [r, 1/r] counts as "the same speed"
    # the first touch must come soon after the ball reached the rim, and close to the basket
    rebound_after_rim_s: float = 3.0
    rebound_max_rim_dist: float = 8.0  # horizontal distance rebounder <-> rim, in rim widths (a player is ~4 wide)
    # after a make the other team inbounds under that basket: a flight through the same rim this soon after is
    # the inbound pass, not a shot
    after_make_dead_s: float = 5.0
    # the rebounding team is the one holding the ball longest this long after the first touch (the first touch in
    # a crowded paint is often a wrong attribution or a tip); 0 = the first toucher's team
    rebound_control_s: float = 3.0
    # shot position: the shooter's feet in the frame they are lowest in the image this long before release (on the
    # floor; at release a jump shooter is in the air and the raised feet map to the wrong court spot)
    shot_pos_lookback_s: float = 1.0
    # A shot is a three only when the shooter's feet are clearly behind the 3PT line, by at least this much: standing
    # on the line is a two, and the court mapping is off by ~0.3 m. Inside the line it is a two.
    three_line_margin_m: float = 0.3
    three_close_margin_m: float = 0.46  # within 1.5 ft of the 3PT line ~ court-mapping error: flag as uncertain
    # --- made-basket evidence (events/analyzer.py: _judge) -----------------------------------------------------
    # The ball is small and the net/crowd hides it, so "seen above AND below the rim within 0.2 s" misses real
    # baskets. A make is accepted on any of: (1) the ball seen above then below the rim plane with up to
    # `make_gap_s` unseen in between, (2) a ball that arrives centred and falling, vanishes into the net and is next
    # seen straight under it, never bouncing back out.
    make_gap_s: float = 0.5  # longest unseen stretch (hidden in the net) between the above-rim and below-rim sightings
    make_vanish_tol: float = 0.35  # extrapolated crossing x vs rim centre for a ball that vanishes in the net (rim widths)
    make_reappear_w: float = 2.0  # after vanishing, the next sighting must be below the rim within this many rim widths
    make_bounce_s: float = 0.6  # a ball seen back above the rim plane this soon after arriving is a rim-out
    net_candidate_conf: float = 0.15  # raw detections this confident near the net stand in for a lost tracked ball
    # a basket the possession logic never turned into a shot (shooter not seen holding the ball, flight too short...)
    # is still found by watching the rim itself, and credited to the last player who had the ball
    recover_makes: bool = True
    recover_max_holder_gap_s: float = 4.0  # the credited player must have held the ball at most this long before
    # scoring system: "standard" = 2 inside the arc / 3 outside (5v5), "3x3" = 1 inside / 2 outside
    scoring: str = "standard"

    def point_values(self) -> tuple[int, int]:
        """(inside the arc, outside the arc)"""
        return (1, 2) if self.scoring == "3x3" else (2, 3)


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
    # Work out which court type the video shows (high school / FIBA / NBA / NCAA) by how well each one's painted
    # lines land on the lines in the frames, instead of trusting the type that was asked for. The other type is
    # only taken when it fits clearly better; not used with a venue profile or manual court points.
    court_autodetect: bool = True
    court_type_margin: float = 0.05  # line-fit score (share of line points on paint) the winner must lead by
    court_type_min_fit: float = 0.3  # ... and at least this much of the lines must be matched
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
