"""Manual corrections to the AI's scoring, kept per game in overrides.json so they survive re-analysis.

  {"type": "shot", "frame": 412, "made": true, "points": 2, "player": "Player 3"}   fix a shot the AI saw
  {"type": "add",  "frame": 530, "t": 17.6, "player": "Player 3", "points": 2}      a basket the AI never saw

A shot is identified by its release frame (stable while the detection stays the same). Every field except
`type` and `frame` is optional; a corrected shot is marked manual with confidence 1."""
from __future__ import annotations

import json
from pathlib import Path

from ..config import Config
from ..identity.tagging import Identities
from ..schema import Event

from .analyzer import GameAnalysis


def load_overrides(path: Path) -> list[dict]:
    try:
        d = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return []
    return d if isinstance(d, list) else []


def save_overrides(path: Path, items: list[dict]) -> None:
    Path(path).write_text(json.dumps(items, indent=2))


def upsert(items: list[dict], new: dict) -> list[dict]:
    """Newest correction for a (type, frame) wins."""
    return [o for o in items if (o.get("type"), o.get("frame")) != (new.get("type"), new.get("frame"))] + [new]


def remove(items: list[dict], kind: str, frame: int) -> list[dict]:
    return [o for o in items if (o.get("type"), o.get("frame")) != (kind, frame)]


def apply_overrides(analysis: GameAnalysis, overrides: list[dict], ids: Identities, cfg: Config) -> None:
    """Edits `analysis.events` in place."""
    inside_pts, outside_pts = cfg.events.point_values()
    for o in overrides:
        kind = o.get("type")
        if kind == "add":
            player = o.get("player")
            pts = int(o.get("points") or inside_pts)
            analysis.events.append(Event(
                "shot", int(o["frame"]), float(o.get("t", 0.0)), player, ids.player_team.get(player) if player else None,
                {"made": True, "points": pts, "three": pts == outside_pts, "dunk": False, "airball": False, "shot_xy": None,
                 "hoop": None, "distance_m": None, "three_line_m": None, "three_close": False, "make_frame": None,
                 "rim": None, "arc_apex_above_rim_m": None, "airtime_s": None, "reason": "added by you",
                 "confidence": 1.0, "manual": True}))
            continue
        if kind != "shot":
            continue
        ev = next((e for e in analysis.events if e.type == "shot" and e.frame == o.get("frame") and not e.data.get("manual")), None)
        if ev is None:
            continue
        d = ev.data
        if o.get("player"):
            ev.player = o["player"]
            ev.team = ids.player_team.get(o["player"])
        was = bool(d.get("made"))
        if o.get("made") is not None:
            d["made"] = bool(o["made"])
        if d["made"]:
            if o.get("points") is not None:
                d["points"] = int(o["points"])
            elif not was:
                d["points"] = outside_pts if d.get("three") else inside_pts
        else:
            d["points"] = 0
        d.update(manual=True, reason="corrected by you", confidence=1.0)
        if d["made"] and not was:  # a miss turned into a make: no rebound came off it
            analysis.events = [e for e in analysis.events if not (e.type == "rebound" and e.data.get("shot_frame") == ev.frame)]
        if was and not d["made"]:  # a make turned into a miss: no assist
            analysis.events = [e for e in analysis.events if not (e.type == "assist" and e.data.get("shot_frame") == ev.frame)]
    analysis.events.sort(key=lambda e: (e.frame, e.type))
