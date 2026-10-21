"""Venue profiles: calibrate a fixed camera once, reuse it for every game filmed from it.

venues/<name>.json
    {"court": "fiba", "image_size": [3840, 2160], "points": {"R_base_top": [988, 1224], ...}, "notes": "..."}

`points` are template landmarks (see court/template.py) clicked on one frame. They are rescaled to the
video's resolution, so a profile made on a 4K frame also works on a 1080p export of the same camera.
The rim check (fusion.validate_court) still runs on every game, so a camera that was bumped is caught.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import REPO_ROOT, CourtSpec

VENUES_DIR = REPO_ROOT / "venues"


def venue_path(name: str) -> Path:
    p = Path(name)
    return p if p.suffix == ".json" else VENUES_DIR / f"{name}.json"


def list_venues() -> list[str]:
    return sorted(p.stem for p in VENUES_DIR.glob("*.json"))


def save_venue(name: str, points: dict, court: str, image_size: tuple[int, int], notes: str = "") -> Path:
    CourtSpec.preset(court)  # validate the name
    p = venue_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"court": court, "image_size": list(image_size),
            "points": {k: [float(u), float(v)] for k, (u, v) in points.items()}, "notes": notes}
    p.write_text(json.dumps(data, indent=2))
    return p


def load_venue(name: str, image_size: tuple[int, int] | None = None) -> tuple[CourtSpec, dict[str, tuple[float, float]]]:
    """(court spec, landmark points scaled to `image_size` (w, h))."""
    p = venue_path(name)
    if not p.exists():
        raise FileNotFoundError(f"venue {name!r} not found ({p}); known: {list_venues()}")
    d = json.loads(p.read_text())
    sx = sy = 1.0
    if image_size is not None:
        w0, h0 = d["image_size"]
        sx, sy = image_size[0] / w0, image_size[1] / h0
    pts = {k: (u * sx, v * sy) for k, (u, v) in d["points"].items()}
    return CourtSpec.preset(d["court"]), pts
