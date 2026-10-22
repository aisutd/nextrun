"""Annotated video: players (team colours + names), holder highlight, ball trail, flight arcs,
rims, running score, event captions and a top-down court minimap."""
from __future__ import annotations

import hashlib

import cv2
import numpy as np

from ..config import CourtSpec
from ..court import template
from ..court.base import CourtCalib
from ..events.analyzer import GameAnalysis
from ..identity.tagging import Identities
from ..schema import FrameState
from ..video import VideoWriter, iter_frames

PALETTE = [(60, 76, 231), (219, 152, 52), (113, 204, 46), (15, 196, 241), (182, 89, 155), (34, 126, 230)]
CAPTION = {
    "shot": lambda e: f"{e.player}: {'MAKES' if e.data['made'] else 'misses'} "
    f"{'DUNK' if e.data.get('dunk') else ('3PT' if e.data.get('three') else '2PT')}",
    "assist": lambda e: f"assist {e.player} -> {e.data.get('to')}",
    "rebound": lambda e: f"{'off' if e.data.get('offensive') else 'def'} rebound {e.player}",
    "steal": lambda e: f"STEAL {e.player}",
    "turnover": lambda e: f"turnover {e.player}",
    "pass": lambda e: f"pass {e.player} -> {e.data.get('to')}",
}


NAMED = {  # BGR; teams are often named after jersey colours
    "red": (60, 60, 230), "blue": (220, 120, 40), "green": (80, 180, 60), "yellow": (40, 220, 240),
    "white": (245, 245, 245), "black": (40, 40, 40), "orange": (30, 140, 255), "purple": (170, 60, 140),
    "gray": (150, 150, 150), "grey": (150, 150, 150), "pink": (180, 120, 255), "navy": (110, 40, 20),
}


def team_color(team: str | None) -> tuple[int, int, int]:
    if team is None:
        return (200, 200, 200)
    if team.lower() in NAMED:
        return NAMED[team.lower()]
    return PALETTE[int(hashlib.md5(team.encode()).hexdigest(), 16) % len(PALETTE)]


def _minimap(spec: CourtSpec, f: FrameState, ids: Identities, holder: str | None, scale: int = 9) -> np.ndarray:
    pad = 8
    w, h = int(spec.length * scale) + 2 * pad, int(spec.width * scale) + 2 * pad
    img = np.full((h, w, 3), (40, 90, 150), np.uint8)

    def px(p):
        return int(pad + (p[0] + spec.length / 2) * scale), int(pad + (p[1] + spec.width / 2) * scale)

    for pl in template.polylines(spec):
        cv2.polylines(img, [np.array([px(p) for p in pl], np.int32)], False, (230, 230, 230), 1, cv2.LINE_AA)
    for p in f.players:
        if p.court_xy is None:
            continue
        name = ids.player(p.track_id)
        c = px(p.court_xy)
        cv2.circle(img, c, 5, team_color(ids.player_team.get(name)), -1)
        if name == holder:
            cv2.circle(img, c, 8, (0, 165, 255), 2)
    return img


def render(
    video_path: str,
    out_path: str,
    frames: list[FrameState],
    analysis: GameAnalysis,
    ids: Identities,
    calib: CourtCalib | None,
    fps: float,
    stride: int = 1,
    trail: int = 20,
    caption_s: float = 2.0,
) -> None:
    by_idx = {f.idx: k for k, f in enumerate(frames)}
    flights_at: dict[int, int] = {}
    for fi, fl in enumerate(analysis.flights):
        for k in range(fl.start, fl.end + 1):
            flights_at[k] = fi
    events = sorted(analysis.events, key=lambda e: e.frame)
    score: dict[str, int] = {}
    ev_ptr = 0
    writer = None
    try:
        for idx, img in iter_frames(video_path, stride=stride):
            k = by_idx.get(idx)
            if k is None:
                continue
            f = frames[k]
            if writer is None:
                writer = VideoWriter(out_path, fps / stride, (img.shape[1], img.shape[0]))
            holder = analysis.holder[k] if k < len(analysis.holder) else None
            for r in f.rims:
                x1, y1, x2, y2 = map(int, r.bbox)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 140, 255), 2)
            for p in f.players:
                name = ids.player(p.track_id)
                col = team_color(ids.player_team.get(name))
                x1, y1, x2, y2 = map(int, p.bbox)
                cv2.rectangle(img, (x1, y1), (x2, y2), col, 3 if name == holder else 2)
                cv2.putText(img, name or "?", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
                if name == holder:
                    cv2.ellipse(img, (int((x1 + x2) / 2), y2), (int((x2 - x1) * 0.6), 8), 0, 0, 360, (0, 165, 255), 2)
            # ball trail
            pts = [frames[j].ball.xy for j in range(max(0, k - trail), k + 1) if frames[j].ball is not None]
            for a, b in zip(pts, pts[1:]):
                cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), (0, 200, 255), 2, cv2.LINE_AA)
            if f.ball is not None:
                cv2.circle(img, tuple(map(int, f.ball.xy)), max(4, int(f.ball.radius)), (0, 255, 255) if not f.ball.interpolated else (0, 120, 255), 2)
            # flight arc: fitted curve for the whole flight
            fi = flights_at.get(k)
            if fi is not None and analysis.flights[fi].arc is not None:
                fl = analysis.flights[fi]
                ts = np.linspace(fl.points[0][1], fl.points[-1][1], 40)
                curve = fl.arc.eval(ts).astype(np.int32)
                cv2.polylines(img, [curve], False, (255, 255, 255), 1, cv2.LINE_AA)
            # events -> score + captions
            while ev_ptr < len(events) and events[ev_ptr].frame <= f.idx:
                e = events[ev_ptr]
                if e.type == "shot" and e.data.get("made"):
                    score[e.team or "?"] = score.get(e.team or "?", 0) + int(e.data.get("points", 2))
                ev_ptr += 1
            recent = [e for e in events[:ev_ptr] if e.type in CAPTION and f.t - e.t <= caption_s][-3:]
            for j, e in enumerate(recent):
                cv2.putText(img, CAPTION[e.type](e), (20, img.shape[0] - 30 - 32 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5, cv2.LINE_AA)
                cv2.putText(img, CAPTION[e.type](e), (20, img.shape[0] - 30 - 32 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
            sb = "   ".join(f"{t}: {s}" for t, s in sorted(score.items())) or "0 - 0"
            cv2.rectangle(img, (10, 10), (30 + 14 * len(sb), 48), (0, 0, 0), -1)
            cv2.putText(img, sb, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            if calib is not None:
                mm = _minimap(calib.spec, f, ids, holder)
                mh, mw = mm.shape[:2]
                if mh < img.shape[0] and mw < img.shape[1]:
                    roi = img[img.shape[0] - mh - 10 : img.shape[0] - 10, img.shape[1] - mw - 10 : img.shape[1] - 10]
                    cv2.addWeighted(mm, 0.85, roi, 0.15, 0, roi)
            writer.write(img)
    finally:
        if writer is not None:
            writer.close()


def draw_court(frame: np.ndarray, calib: CourtCalib, color=(0, 0, 255)) -> np.ndarray:
    """Project the court template onto a frame — eyeball check that calibration is right."""
    img = frame.copy()
    h, w = img.shape[:2]
    Hc2i = calib.H_inv
    # a homography's overall sign is arbitrary: "in front of the camera" = same sign as a visible floor point
    ref = calib.image_to_court([(w / 2, h - 1)])[0]
    front = np.sign((Hc2i @ [ref[0], ref[1], 1.0])[2]) or 1.0
    for pl in template.polylines(calib.spec):
        P = np.hstack([pl, np.ones((len(pl), 1))]) @ Hc2i.T * front
        ok = P[:, 2] > 1e-6  # in front of the camera
        uv = P[:, :2] / np.where(ok, P[:, 2], 1)[:, None]
        ok &= (np.abs(uv) < 4 * max(w, h)).all(1)
        for a, b, oa, ob in zip(uv[:-1], uv[1:], ok[:-1], ok[1:]):
            if oa and ob:
                cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), color, 2, cv2.LINE_AA)
    for name, p in calib.correspondences.items():
        cv2.circle(img, tuple(map(int, p)), 6, (0, 255, 0), 2)
    cv2.putText(img, f"court: {calib.method} conf={calib.conf:.2f}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return img
