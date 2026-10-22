"""Player tagging ("define who is playing") and identity resolution.

Workflow: run detection once -> `tagging_sheet()` renders a frame with track IDs -> the user writes
tags.json mapping track IDs to names/teams:

    {"3": {"name": "Tushaar", "team": "Red"}, "7": {"name": "Juan", "team": "Blue"}}

Trackers break identities on long occlusions, so `resolve_identities()` re-links later untagged
tracks to tagged players using appearance similarity + spatio-temporal continuity, while never
assigning one identity to two tracks visible at the same time."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..schema import FrameState
from .teams import assign_teams


def load_tags(path_or_dict) -> dict[int, dict]:
    if path_or_dict is None:
        return {}
    d = path_or_dict if isinstance(path_or_dict, dict) else json.loads(Path(path_or_dict).read_text())
    return {int(k): dict(v) for k, v in d.items()}


@dataclass
class TrackSpan:
    tid: int
    start: int
    end: int
    first_xy: tuple[float, float]
    last_xy: tuple[float, float]
    n: int
    height: float


def track_spans(frames: list[FrameState]) -> dict[int, TrackSpan]:
    spans: dict[int, TrackSpan] = {}
    for f in frames:
        for p in f.players:
            s = spans.get(p.track_id)
            if s is None:
                spans[p.track_id] = TrackSpan(p.track_id, f.idx, f.idx, p.feet, p.feet, 1, p.height)
            else:
                s.end, s.last_xy, s.n = f.idx, p.feet, s.n + 1
                s.height = 0.9 * s.height + 0.1 * p.height
    return spans


def best_tagging_frame(frames: list[FrameState], min_players: int = 2) -> int:
    """Index (into frames) of an early frame showing the most separated players."""
    best, best_score = 0, -1.0
    for i, f in enumerate(frames[: max(1, len(frames) // 4)]):
        if len(f.players) < min_players:
            continue
        score = len(f.players) * min(p.conf for p in f.players)
        if score > best_score:
            best, best_score = i, score
    return best


def tagging_sheet(frame: np.ndarray, state: FrameState) -> np.ndarray:
    """Frame with big track-ID labels, for the user to write tags.json from."""
    img = frame.copy()
    for p in state.players:
        x1, y1, x2, y2 = map(int, p.bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        label = str(p.track_id)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw + 8, y1), (0, 0, 0), -1)
        cv2.putText(img, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    return img


@dataclass
class Identities:
    track_to_player: dict[int, str] = field(default_factory=dict)
    player_team: dict[str, str] = field(default_factory=dict)

    def player(self, tid: int | None) -> str | None:
        if tid is None:
            return None
        return self.track_to_player.get(tid, f"track:{tid}")

    def team(self, tid: int | None) -> str | None:
        p = self.player(tid)
        return None if p is None else self.player_team.get(p)

    def to_dict(self) -> dict:
        return {"track_to_player": {str(k): v for k, v in self.track_to_player.items()}, "player_team": self.player_team}


def resolve_identities(
    frames: list[FrameState],
    track_emb: dict[int, np.ndarray],
    tags: dict[int, dict],
    n_teams: int = 2,
    min_track_frames: int = 5,
    link_threshold: float = 0.6,  # 0.7*colour_similarity + 0.3*continuity must exceed this
    fps: float = 30.0,
) -> Identities:
    spans = {t: s for t, s in track_spans(frames).items() if s.n >= min_track_frames or t in tags}
    ids = Identities()

    # 1) user tags
    members: dict[str, list[int]] = {}
    for tid, tag in tags.items():
        name = tag.get("name") or f"player{tid}"
        ids.track_to_player[tid] = name
        members.setdefault(name, []).append(tid)
        if tag.get("team"):
            ids.player_team[name] = str(tag["team"])

    # 2) re-link untagged tracks to tagged identities (in time order)
    if members:
        for tid in sorted((t for t in spans if t not in ids.track_to_player), key=lambda t: spans[t].start):
            s = spans[tid]
            emb = track_emb.get(tid)
            best, best_score = None, -1.0
            for name, tids in members.items():
                if any(_overlaps(spans[t], s) for t in tids if t in spans):
                    continue  # identity visible elsewhere at the same time
                prev = max((spans[t] for t in tids if t in spans and spans[t].end < s.start), key=lambda x: x.end, default=None)
                sims = [float(emb @ track_emb[t]) for t in tids if emb is not None and t in track_emb]
                sim = max(sims) if sims else 0.0
                cont = 0.0
                if prev is not None:
                    gap_s = (s.start - prev.end) / fps
                    dist = np.hypot(s.first_xy[0] - prev.last_xy[0], s.first_xy[1] - prev.last_xy[1]) / max(prev.height, 1.0)
                    cont = float(np.exp(-gap_s / 2.0) * np.exp(-dist / 1.5))  # 1 = picked up right where it left
                score = 0.7 * sim + 0.3 * cont
                if score > best_score:
                    best, best_score = name, score
            if best is not None and best_score >= link_threshold:
                ids.track_to_player[tid] = best
                members[best].append(tid)

    # 3) teams for everyone: seed clustering with tagged teams if available
    seeds: dict[str, list[np.ndarray]] = {}
    for tid, name in ids.track_to_player.items():
        team = ids.player_team.get(name)
        if team and tid in track_emb:
            seeds.setdefault(team, []).append(track_emb[tid])
    team_of_track = assign_teams({t: e for t, e in track_emb.items() if t in spans}, n_teams, seeds or None)
    for tid in spans:
        name = ids.player(tid)
        if name not in ids.player_team and tid in team_of_track:
            # majority vote across this identity's tracks
            votes = [team_of_track[t] for t, n in ids.track_to_player.items() if n == name and t in team_of_track] or [team_of_track[tid]]
            ids.player_team[name] = max(set(votes), key=votes.count)
    return ids


def _overlaps(a: TrackSpan, b: TrackSpan) -> bool:
    return a.start <= b.end and b.start <= a.end
