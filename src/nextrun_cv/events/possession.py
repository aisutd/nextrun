"""Who holds the ball, frame by frame, as possession segments.

Gain: ball within `gain_dist` (x bbox height) of a player's hand for `gain_frames` consecutive frames.
Hold: ball stays inside the holder's bbox expanded by `control_expand` (covers dribbles at the feet).
Lose: ball outside the control zone for `lose_frames` consecutive frames -> release at the first
such frame. While the ball is unseen, possession is kept (usually it's hidden by the holder's body)
for up to one second."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..config import PossessionConfig
from ..schema import FrameState, PlayerObs


@dataclass
class Segment:
    player: str
    start: int  # index into frames of the first controlled frame
    end: int  # index into frames of the last controlled frame (release)
    track_ids: set[int] = field(default_factory=set)


def hand_distance(ball_xy, p: PlayerObs) -> float:
    return min(np.hypot(ball_xy[0] - x, ball_xy[1] - y) for x, y in p.hands()) / p.height


def in_control(ball_xy, p: PlayerObs, expand: float) -> bool:
    x1, y1, x2, y2 = p.bbox
    w, h = x2 - x1, y2 - y1
    return x1 - expand * w <= ball_xy[0] <= x2 + expand * w and y1 - expand * h <= ball_xy[1] <= y2 + 0.1 * h


def compute_possession(
    frames: list[FrameState], key: Callable[[int], str], cfg: PossessionConfig, fps: float
) -> list[Segment]:
    """key: maps track_id -> player identity, so a tracker ID switch on the same person isn't a pass."""
    segs: list[Segment] = []
    holder: Segment | None = None
    cand, cand_start, cand_n = None, 0, 0
    out_n, out_start, unseen = 0, 0, 0
    max_unseen = int(fps)

    for i, f in enumerate(frames):
        ball = f.ball
        if ball is None:
            unseen += 1
            if holder is not None and unseen > max_unseen:
                holder.end = i - unseen
                segs.append(holder)
                holder = None
            cand, cand_n = None, 0
            continue
        unseen = 0
        by_key: dict[str, PlayerObs] = {}
        for p in f.players:
            k = key(p.track_id)
            # several tracks can resolve to one identity in a frame only through tracker glitches;
            # keep the one closest to the ball
            if k not in by_key or hand_distance(ball.xy, p) < hand_distance(ball.xy, by_key[k]):
                by_key[k] = p

        near_key, near_d = None, cfg.gain_dist
        for k, p in by_key.items():
            d = hand_distance(ball.xy, p)
            if d < near_d:
                near_key, near_d = k, d

        if holder is not None:
            hp = by_key.get(holder.player)
            controlled = hp is not None and (in_control(ball.xy, hp, cfg.control_expand) or hand_distance(ball.xy, hp) < cfg.gain_dist)
            if controlled and (near_key in (None, holder.player) or hand_distance(ball.xy, hp) <= near_d * 1.2):
                holder.end = i
                holder.track_ids.add(hp.track_id)
                out_n, cand, cand_n = 0, None, 0
                continue
            if out_n == 0:
                out_start = i
            out_n += 1
            if out_n >= cfg.lose_frames:
                holder.end = max(holder.start, out_start - 1)
                segs.append(holder)
                holder, out_n = None, 0

        # candidate for a new possession (also while the old holder is losing it: hand-offs / steals)
        if near_key is not None and (holder is None or near_key != holder.player):
            if near_key == cand:
                cand_n += 1
            else:
                cand, cand_start, cand_n = near_key, i, 1
            if cand_n >= cfg.gain_frames:
                if holder is not None:
                    holder.end = max(holder.start, cand_start - 1)
                    segs.append(holder)
                holder = Segment(cand, cand_start, i, {by_key[cand].track_id})
                cand, cand_n, out_n = None, 0, 0
        else:
            cand, cand_n = None, 0

    if holder is not None:
        segs.append(holder)
    return segs


def holder_per_frame(segs: list[Segment], n: int) -> list[str | None]:
    out: list[str | None] = [None] * n
    for s in segs:
        for i in range(s.start, s.end + 1):
            out[i] = s.player
    return out
