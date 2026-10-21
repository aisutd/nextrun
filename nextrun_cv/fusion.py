"""Model fusion: the geometry that lets the three models check and inform each other.

    court model ── homography H (floor pixels <-> court meters)
        │   ▲
        │   └── rim model: a detected rim must sit straight above the floor point under its hoop.
        │       Agreement validates H (bad fits are rejected) and says which basket a rim is.
        ▼
    pose model ── feet -> court position (on/off court, 2PT/3PT zone, distance to the line)
        ▲
        └────── ball model: ball near a player's hand -> who holds it

Everything here is pure geometry on FrameState / CourtCalib, so it runs the same live (per frame, in
integration.NextRun) and offline (pipeline.analyze on saved tracks).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config, CourtSpec, FusionConfig, PossessionConfig
from .court import template
from .court.base import CourtCalib
from .events.possession import hand_distance
from .schema import FrameState, PlayerObs, RimObs


# --- court <-> rim -------------------------------------------------------------------------------------
@dataclass
class RimCheck:
    hoop: int  # 0 = left basket, 1 = right basket (court frame)
    offset: float  # horizontal rim offset from the hoop's floor point, in rim widths
    height: float  # rim height above the hoop's floor point, in rim widths
    ok: bool


def check_rim(calib: CourtCalib, rim: RimObs, cfg: FusionConfig) -> RimCheck:
    """Compare a detected rim with the floor point under each hoop (projected by the court fit) and keep
    the best-matching hoop."""
    floor = calib.court_to_image(template.hoop_positions(calib.spec))
    best = None
    for hoop, (u, v) in enumerate(floor):
        offset = abs(rim.center[0] - u) / rim.width
        height = (v - rim.center[1]) / rim.width
        if best is None or offset < best.offset:
            lo, hi = cfg.rim_height_range
            best = RimCheck(hoop, float(offset), float(height), bool(offset <= cfg.rim_max_offset and lo <= height <= hi))
    return best


def hoop_for_rim(calib: CourtCalib | None, rim: RimObs, cfg: FusionConfig) -> int | None:
    """Which basket (0 left / 1 right) a detected rim is, or None if the court fit can't tell."""
    if calib is None or calib.conf < cfg.min_court_conf:
        return None
    c = check_rim(calib, rim, cfg)
    return c.hoop if c.ok else None


def validate_court(calib: CourtCalib, rims_per_frame: list[list[RimObs]], cfg: FusionConfig) -> CourtCalib:
    """Cross-check a court calibration against the rim detector. Confidence is scaled by the share of rim
    observations that agree, so a fit no rim agrees with drops below `min_court_conf` (unused).
    No rims seen -> unchanged."""
    checks = [check_rim(calib, r, cfg) for rims in rims_per_frame for r in rims]
    if not checks:
        calib.checks["rims"] = {"checked": 0}
        return calib
    agree = float(np.mean([c.ok for c in checks]))
    calib.checks["rims"] = {
        "checked": len(checks),
        "agree": agree,
        "median_offset": float(np.median([c.offset for c in checks])),
        "median_height": float(np.median([c.height for c in checks])),
        "conf_before": calib.conf,
    }
    calib.conf = float(calib.conf * (0.25 + 0.75 * agree))
    return calib


# --- court <-> players ---------------------------------------------------------------------------------
def court_usable(calib: CourtCalib | None, cfg: FusionConfig) -> bool:
    return calib is not None and calib.conf >= cfg.min_court_conf


def annotate_players(frames: list[FrameState], calib: CourtCalib) -> None:
    """Set each player's court position from their feet (in place)."""
    for f in frames:
        if f.players:
            for p, xy in zip(f.players, calib.image_to_court([p.feet for p in f.players])):
                p.court_xy = (float(xy[0]), float(xy[1]))


def on_court(xy, spec: CourtSpec, margin: float, play_area=None) -> bool:
    if play_area is not None:
        x0, x1, y0, y1 = play_area
        return x0 - margin <= xy[0] <= x1 + margin and y0 - margin <= xy[1] <= y1 + margin
    return abs(xy[0]) <= spec.length / 2 + margin and abs(xy[1]) <= spec.width / 2 + margin


def drop_off_court(frames: list[FrameState], calib: CourtCalib, margin: float, play_area=None) -> int:
    """Remove people standing off the court (spectators, benches, next game). Returns how many."""
    n = 0
    for f in frames:
        if f.players:
            keep = [p for p, xy in zip(f.players, calib.image_to_court([p.feet for p in f.players]))
                    if on_court(xy, calib.spec, margin, play_area)]
            n += len(f.players) - len(keep)
            f.players = keep
    return n


def zone(xy, spec: CourtSpec, close_margin: float) -> tuple[str, float]:
    """('2PT' | '3PT' | 'CLOSE', signed distance to the 3PT line in meters) for a court position."""
    d = template.three_line_distance(xy, spec)
    return ("CLOSE" if abs(d) < close_margin else "3PT" if d > 0 else "2PT"), d


# --- ball <-> players ----------------------------------------------------------------------------------
def ball_holder(f: FrameState, cfg: PossessionConfig) -> PlayerObs | None:
    """Single-frame guess at who holds the ball: nearest hand within `gain_dist` body heights. The event
    analyzer uses the temporal version (events.possession) for stats."""
    if f.ball is None or not f.players:
        return None
    p = min(f.players, key=lambda p: hand_distance(f.ball.xy, p))
    return p if hand_distance(f.ball.xy, p) <= cfg.gain_dist else None


# --- everything ----------------------------------------------------------------------------------------
def fuse(frames: list[FrameState], calib: CourtCalib | None, cfg: Config) -> dict:
    """Apply all court-dependent geometry to tracked frames (in place). Returns a small report."""
    if not court_usable(calib, cfg.fusion):
        return {"court": False}
    dropped = drop_off_court(frames, calib, cfg.fusion.off_court_margin_m, cfg.fusion.play_area)
    annotate_players(frames, calib)
    return {"court": True, "court_conf": calib.conf, "off_court_dropped": dropped}


def describe(f: FrameState, calib: CourtCalib | None, cfg: Config) -> dict:
    """JSON-ready view of one fused frame: where everyone is, who has the ball, which basket is which."""
    usable = court_usable(calib, cfg.fusion)
    holder = ball_holder(f, cfg.possession)
    players = []
    for p in f.players:
        d = {"track_id": p.track_id, "bbox": [round(v, 1) for v in p.bbox], "has_ball": p is holder}
        if usable and p.court_xy is not None:
            z, dist = zone(p.court_xy, cfg.court, cfg.events.three_close_margin_m)
            d.update(court_xy=[round(v, 2) for v in p.court_xy], zone=z, three_line_m=round(dist, 2))
        players.append(d)
    rims = []
    for r in f.rims:
        d = {"bbox": [round(v, 1) for v in r.bbox], "conf": round(r.conf, 2)}
        if usable:
            c = check_rim(calib, r, cfg.fusion)
            d.update(hoop=c.hoop if c.ok else None, agrees_with_court=c.ok)
        rims.append(d)
    return {
        "frame": f.idx,
        "t": round(f.t, 3),
        "court": None if calib is None else {"method": calib.method, "conf": round(calib.conf, 2),
                                             "usable": usable, "checks": calib.checks},
        "players": players,
        "ball": None if f.ball is None else {"xy": [round(v, 1) for v in f.ball.xy],
                                             "holder": None if holder is None else holder.track_id},
        "rims": rims,
    }
