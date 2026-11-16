"""Annotated video, broadcast style: full-body player squares (+ skeleton), team-coloured rings and name tags, glowing
ball trail, flight arcs, rims, estimated/fitted court lines, team scoreboard and a minimap. No text captions on the video."""
from __future__ import annotations

import bisect
import hashlib
from dataclasses import replace

import cv2
import numpy as np

from ..config import BallTrackConfig, CourtSpec, FusionConfig
from ..court import template
from ..court.base import CourtCalib
from ..detect.ball_track import smooth_ball_display
from ..events.analyzer import GameAnalysis
from ..identity.tagging import Identities
from ..schema import FrameState
from ..video import iter_frames, make_writer

PALETTE = [(60, 76, 231), (219, 152, 52), (113, 204, 46), (15, 196, 241), (182, 89, 155), (34, 126, 230)]
NAMED = {  # BGR; teams are often named after jersey colours
    "red": (60, 60, 230), "blue": (220, 120, 40), "green": (80, 180, 60), "yellow": (40, 220, 240),
    "white": (245, 245, 245), "black": (40, 40, 40), "orange": (30, 140, 255), "purple": (170, 60, 140),
    "gray": (150, 150, 150), "grey": (150, 150, 150), "pink": (180, 120, 255), "navy": (110, 40, 20),
}


TEAM_AB = {"a": (238, 211, 34), "b": (60, 146, 251)}  # BGR of the app's Team A cyan / Team B orange


def team_color(team: str | None) -> tuple[int, int, int]:
    if team is None:
        return (200, 200, 200)
    if team.lower() in TEAM_AB:
        return TEAM_AB[team.lower()]
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


FONT = cv2.FONT_HERSHEY_DUPLEX


def _lerp(a, b, w):
    return tuple((1 - w) * x + w * y for x, y in zip(a, b))


def _interp(frames: list[FrameState], k: int, idx: int) -> FrameState:
    """The analysed frame k, moved to source frame idx (between frames k and k+1): boxes and ball glide instead of jumping."""
    f0 = frames[k]
    if k + 1 >= len(frames) or idx <= f0.idx:
        return f0
    f1 = frames[k + 1]
    w = (idx - f0.idx) / max(1, f1.idx - f0.idx)
    nxt = {p.track_id: p for p in f1.players}
    players = []
    for p in f0.players:
        q = nxt.get(p.track_id)
        if q is None:
            players.append(p)
            continue
        cxy = _lerp(p.court_xy, q.court_xy, w) if p.court_xy is not None and q.court_xy is not None else p.court_xy
        players.append(replace(p, bbox=_lerp(p.bbox, q.bbox, w), court_xy=cxy))
    ball = f0.ball
    if f0.ball is not None and f1.ball is not None:
        ball = replace(f0.ball, xy=_lerp(f0.ball.xy, f1.ball.xy, w), radius=(1 - w) * f0.ball.radius + w * f1.ball.radius)
    return replace(f0, idx=idx, t=f0.t + w * (f1.t - f0.t), players=players, ball=ball)


def _fg(bg) -> tuple[int, int, int]:
    return (25, 25, 25) if 0.114 * bg[0] + 0.587 * bg[1] + 0.299 * bg[2] > 150 else (255, 255, 255)


def _box(img, x1, y1, x2, y2, bg, alpha=0.85, round_=True) -> None:
    """Translucent (rounded) rectangle, blended only inside its own region."""
    H, W = img.shape[:2]
    x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(W, int(x2)), min(H, int(y2))
    if x2 <= x1 or y2 <= y1:
        return
    roi = img[y1:y2, x1:x2]
    ov = roi.copy()
    h, w = y2 - y1, x2 - x1
    r = min(h // 2, 14) if round_ else 0
    if r:
        cv2.rectangle(ov, (r, 0), (w - r, h), bg, -1)
        cv2.rectangle(ov, (0, r), (w, h - r), bg, -1)
        for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
            cv2.circle(ov, (cx, cy), r, bg, -1, cv2.LINE_AA)
    else:
        ov[:] = bg
    roi[:] = cv2.addWeighted(ov, alpha, roi, 1 - alpha, 0)


def _pill(img, text, x, y, bg, scale, th, m, fg=None, pad=6, alpha=0.88):
    """Rounded tag with its top-left at (x, y); returns its bottom-right corner."""
    s, tk, p = scale * m, max(1, int(round(th * m))), int(pad * m)
    (tw, tt), base = cv2.getTextSize(text, FONT, s, tk)
    x2, y2 = x + tw + 2 * p, y + tt + base + 2 * p
    _box(img, x, y, x2, y2, bg, alpha)
    cv2.putText(img, text, (int(x + p), int(y + p + tt)), FONT, s, fg or _fg(bg), tk, cv2.LINE_AA)
    return x2, y2


# COCO-17 skeleton (pairs of keypoint indices)
SKELETON = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]


def _player_box(img, p, col, t, holder: bool) -> None:
    """The full-body detection square: thin outline + heavy corner brackets in the team colour (orange for the ball
    holder), and the pose skeleton when the pose model saw the joints."""
    x1, y1, x2, y2 = map(int, p.bbox)
    cv2.rectangle(img, (x1, y1), (x2, y2), col, t(1), cv2.LINE_AA)
    bc = (0, 165, 255) if holder else col
    L = max(t(8), int(min(x2 - x1, y2 - y1) * 0.22))
    th = t(3) if holder else t(2)
    for cx, cy, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        cv2.line(img, (cx, cy), (cx + dx * L, cy), bc, th, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (cx, cy + dy * L), bc, th, cv2.LINE_AA)
    kp = p.keypoints
    if kp is not None:
        for a, b in SKELETON:
            if kp[a][2] > 0.4 and kp[b][2] > 0.4:
                cv2.line(img, (int(kp[a][0]), int(kp[a][1])), (int(kp[b][0]), int(kp[b][1])), (255, 255, 255), t(1), cv2.LINE_AA)


def _scoreboard(img, f, score: dict, reb: dict, ast: dict, ids, m: float, flash: dict | None = None) -> None:
    """Team score card: one row per team with points, rebounds and assists so far. `flash` = {(team, stat): 0..1}
    briefly highlights a number that just changed."""
    t = lambda v: int(round(v * m))  # noqa: E731
    teams = sorted({tm for tm in (set(score) | set(reb) | set(ast) | set(ids.player_team.values())) if tm and tm != "?"}) or ["A", "B"]
    flash = flash or {}
    w, h = t(360), t(52) + t(20) + t(40) * len(teams)
    x0, y0 = t(14), t(14)
    _box(img, x0, y0, x0 + w, y0 + h, (22, 18, 16), 0.82)
    cv2.circle(img, (x0 + t(20), y0 + t(24)), t(6), (60, 60, 235), -1, cv2.LINE_AA)
    cv2.putText(img, "LIVE  " + f"{int(f.t // 60)}:{int(f.t % 60):02d}", (x0 + t(36), y0 + t(31)), FONT, 0.6 * m, (235, 235, 235), t(1), cv2.LINE_AA)
    cv2.putText(img, "NEXTRUN", (x0 + w - t(112), y0 + t(31)), FONT, 0.6 * m, (0, 165, 255), t(1), cv2.LINE_AA)
    # column headers
    cols = [("PTS", x0 + w - t(150)), ("REB", x0 + w - t(92)), ("AST", x0 + w - t(40))]
    y = y0 + t(52)
    for name, cx in cols:
        (tw, _), _ = cv2.getTextSize(name, FONT, 0.42 * m, t(1))
        cv2.putText(img, name, (cx - tw // 2, y + t(12)), FONT, 0.42 * m, (160, 160, 160), t(1), cv2.LINE_AA)
    y += t(20)
    for tm in teams:
        col = team_color(tm)
        cv2.rectangle(img, (x0 + t(14), y + t(4)), (x0 + t(22), y + t(34)), col, -1)
        cv2.putText(img, f"Team {tm}", (x0 + t(34), y + t(28)), FONT, 0.75 * m, (255, 255, 255), t(1), cv2.LINE_AA)
        for (name, cx), val, big in zip(cols, (score.get(tm, 0), reb.get(tm, 0), ast.get(tm, 0)), (True, False, False)):
            sc = str(val)
            fs, th = (1.2, 2) if big else (0.8, 1)
            (tw, tt), _ = cv2.getTextSize(sc, FONT, fs * m, t(th))
            a = flash.get((tm, name), 0.0)
            if a > 0:  # glow behind a number that just went up
                _box(img, cx - tw // 2 - t(8), y + t(2), cx + tw // 2 + t(8), y + t(36), (0, 165, 255), 0.25 + 0.5 * a)
            cv2.putText(img, sc, (cx - tw // 2, y + t(19) + tt // 2), FONT, fs * m, (255, 255, 255), t(th), cv2.LINE_AA)
        y += t(40)


def _event_timeline(events, fps: float) -> list[tuple[int, str, object]]:
    """(source frame, kind, event) for everything the video counts, in order: a basket counts when the ball goes
    through the hoop, a rebound when it is secured, an assist together with the basket it set up."""
    out = []
    for e in events:
        if e.type == "shot" and e.data.get("made"):
            out.append((int(e.data.get("make_frame") or e.frame), "score", e))
        elif e.type == "rebound":
            out.append((int(e.frame), "rebound", e))
        elif e.type == "assist":
            out.append((int(e.data.get("make_frame") or e.data.get("shot_frame") or e.frame), "assist", e))
    out.sort(key=lambda x: (x[0], x[1] != "score"))
    return out


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
    motion=None,
) -> None:
    """Every source frame of the analysed part is written (smooth playback at the video's own frame rate);
    detections exist for every `stride`-th frame and are interpolated in between. Output is capped at 1280 px.
    motion: court.track.CameraMotion for a moving camera (the analysis' ball arcs are in its stabilized view)."""
    if not frames:
        return
    # draw a smoothed ball (steady position and size); the analysis keeps working on the raw track
    sm = smooth_ball_display(frames, BallTrackConfig())
    frames = [replace(f, ball=replace(f.ball, xy=s_[0], radius=s_[1])) if s_ is not None and f.ball is not None else f
              for f, s_ in zip(frames, sm)]
    idxs = [f.idx for f in frames]
    hs = [p.height for f_ in frames for p in f_.players]
    hm = float(np.median(hs)) if hs else 100.0  # typical player height in px: sets how far a real ball can move per frame
    motion_at = dict(zip(motion.idx, motion.M)) if motion is not None else {}
    flights_at: dict[int, int] = {}
    for fi, fl in enumerate(analysis.flights):
        for k in range(fl.start, fl.end + 1):
            flights_at[k] = fi
    timeline = _event_timeline(analysis.events, fps)
    score: dict[str, int] = {}
    reb: dict[str, int] = {}
    ast: dict[str, int] = {}
    ev_ptr = 0
    show = max(1, round(2.2 * fps))  # how long a REBOUND / ASSIST call stays on screen (source frames)
    calls: list[tuple[int, str, str | None, str | None, str | None]] = []  # (frame, label, player, team, detail)
    changed: dict[tuple[str, str], int] = {}  # (team, stat) -> source frame it last went up
    writer = None
    try:
        for idx, img in iter_frames(video_path, stride=1, max_frames=idxs[-1] + 1):
            k = bisect.bisect_right(idxs, idx) - 1
            if k < 0:
                continue
            fk = frames[k]
            f = _interp(frames, k, idx)
            H0, W0 = img.shape[:2]
            m = max(1.0, max(H0, W0) / 1280)  # sizes below are for a 1280 px frame; scale them up for bigger frames
            t = lambda v: max(1, int(round(v * m)))  # noqa: E731
            if writer is None:
                size = (int(W0 / m) // 2 * 2, int(H0 / m) // 2 * 2)
                writer = make_writer(out_path, fps, size)
            # events up to now -> running team points, rebounds and assists
            while ev_ptr < len(timeline) and timeline[ev_ptr][0] <= idx:
                at, kind, e = timeline[ev_ptr]
                tm = e.team or ids.player_team.get(e.player) or "?"
                if kind == "score":
                    score[tm] = score.get(tm, 0) + int(e.data.get("points", 2))
                    changed[(tm, "PTS")] = at
                elif kind == "rebound":
                    reb[tm] = reb.get(tm, 0) + 1
                    changed[(tm, "REB")] = at
                    calls.append((at, "OFF. REBOUND" if e.data.get("offensive") else "REBOUND", e.player, tm, None))
                elif kind == "assist":
                    ast[tm] = ast.get(tm, 0) + 1
                    changed[(tm, "AST")] = at
                    calls.append((at, "ASSIST", e.player, tm, e.data.get("to")))
                ev_ptr += 1
            calls = [c for c in calls if idx - c[0] <= show]
            callout = {c[2]: c for c in calls if c[2]}  # player -> their latest call, shown over their head
            holder = analysis.holder[k] if k < len(analysis.holder) else None
            court = calib.at(fk.idx) if calib is not None else None
            if court is not None:  # always draw the best court we have; an estimate is tagged as one below
                lines = draw_court(img, court, (255, 215, 70), thick=t(3), show_points=False, label=False)
                img = cv2.addWeighted(lines, 0.6, img, 0.4, 0)
            for r in f.rims:
                x1, y1, x2, y2 = map(int, r.bbox)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 140, 255), t(3), cv2.LINE_AA)
                _pill(img, f"RIM {r.conf:.0%}", x1, max(0, y1 - t(26)), (0, 100, 210), 0.48, 1, m, pad=4)
            # players: ring under the feet in the team colour, name tag with running points
            for p in f.players:
                name = ids.player(p.track_id)
                if name in ids.excluded:
                    continue  # marked as not playing in the team picker
                col = team_color(ids.player_team.get(name))
                x1, y1, x2, y2 = map(int, p.bbox)
                _player_box(img, p, col, t, name == holder)
                cx, rw = int((x1 + x2) / 2), max(t(10), int((x2 - x1) * 0.55))
                cv2.ellipse(img, (cx, y2), (rw, max(t(4), rw // 3)), 0, 0, 360, col, t(3), cv2.LINE_AA)
                if name == holder:
                    cv2.ellipse(img, (cx, y2), (rw + t(6), max(t(5), rw // 3 + t(3))), 0, 0, 360, (0, 165, 255), t(2), cv2.LINE_AA)
                label = name or "?"
                _pill(img, label, x1, max(0, y1 - t(30)), col, 0.5, 1, m, pad=4)
                c = callout.get(name)
                if c is not None:  # "REBOUND" / "ASSIST" over the player who just made the play, with a pop-in
                    age = (idx - c[0]) / show
                    sc = 0.62 * (1.25 - 0.25 * min(1.0, age * 6))
                    _pill(img, c[1], x1, max(0, y1 - t(64)), (0, 165, 255), sc, 2, m, fg=(255, 255, 255), pad=5, alpha=0.95)
                    cv2.ellipse(img, (cx, y2), (rw + t(10), max(t(6), rw // 3 + t(6))), 0, 0, 360, (0, 165, 255), t(3), cv2.LINE_AA)
            # ball: fading trail (thicker and brighter towards the ball) and a soft glow
            tr = []  # newest sightings of the current unbroken stretch: a gap or a jump ends the trail
            for j in range(k, max(0, k - trail) - 1, -1):
                b_ = frames[j].ball
                if b_ is None or (tr and np.hypot(b_.xy[0] - tr[-1][0], b_.xy[1] - tr[-1][1]) > 0.9 * hm):
                    break
                tr.append(b_.xy)
            tr.reverse()
            if f.ball is not None and idx > fk.idx and (not tr or np.hypot(f.ball.xy[0] - tr[-1][0], f.ball.xy[1] - tr[-1][1]) <= 0.9 * hm):
                tr.append(f.ball.xy)
            for i, (a_, b_) in enumerate(zip(tr, tr[1:])):
                fr_ = (i + 1) / max(1, len(tr) - 1)
                col = (int(40 + 0 * fr_), int(120 + 135 * fr_), 255)
                cv2.line(img, tuple(map(int, a_)), tuple(map(int, b_)), col, max(1, int(t(1) + fr_ * t(5))), cv2.LINE_AA)
            if f.ball is not None:
                bx, by = map(int, f.ball.xy)
                br = max(t(5), int(f.ball.radius))
                gx1, gy1, gx2, gy2 = max(0, bx - br * 2 - 2), max(0, by - br * 2 - 2), min(W0, bx + br * 2 + 3), min(H0, by + br * 2 + 3)
                if gx2 > gx1 and gy2 > gy1:
                    roi = img[gy1:gy2, gx1:gx2]
                    glow = roi.copy()
                    cv2.circle(glow, (bx - gx1, by - gy1), br * 2, (0, 190, 255), -1, cv2.LINE_AA)
                    cv2.addWeighted(glow, 0.3, roi, 0.7, 0, roi)
                cv2.circle(img, (bx, by), br, (0, 255, 255), t(2), cv2.LINE_AA)
            elif f.ball_candidates:
                # Keep the raw ball detector visible when the temporal tracker cannot join a sighting
                # to the current flight. The lower confidence mark helps distinguish it from a track.
                candidate = max(f.ball_candidates, key=lambda b: b.conf)
                bx, by = map(int, candidate.xy)
                br = max(t(7), int(candidate.radius))
                cv2.circle(img, (bx, by), br, (0, 255, 255), t(2), cv2.LINE_AA)
                _pill(img, f"BALL? {candidate.conf:.0%}", bx + br, max(0, by - br - t(24)), (0, 135, 185), 0.42, 1, m, pad=3)
            # flight arc: fitted curve for the whole flight
            fi = flights_at.get(k)
            if fi is not None and analysis.flights[fi].arc is not None:
                fl = analysis.flights[fi]
                ts = np.linspace(fl.points[0][1], fl.points[-1][1], 40)
                curve = fl.arc.eval(ts)
                if fk.idx in motion_at:  # stabilized view -> this frame
                    curve = cv2.perspectiveTransform(curve.reshape(-1, 1, 2).astype(np.float64), motion_at[fk.idx]).reshape(-1, 2)
                cv2.polylines(img, [curve.astype(np.int32)], False, (255, 255, 120), t(2), cv2.LINE_AA)
            flash = {k_: 1.0 - (idx - at) / show for k_, at in changed.items() if idx - at <= show}
            _scoreboard(img, f, score, reb, ast, ids, m, flash)
            # play-by-play feed under the score card: the latest rebound / assist calls
            event_y = t(14) + t(52) + t(20) + t(40) * max(2, len({tm for tm in (set(score) | set(reb) | set(ast) | set(ids.player_team.values())) if tm and tm != "?"})) + t(10)
            for at, label, player, team, detail in calls[-3:]:
                text = f"{label}  {player or 'Player'}" + (f"  >  {detail}" if detail else "")
                _, event_y = _pill(img, text, t(14), event_y, team_color(team), 0.55, 1, m, pad=7)
                event_y += t(6)
            if calib is not None:
                mm = _minimap(calib.spec, f, ids, holder, scale=max(1, int(round(9 * m))))
                mh, mw = mm.shape[:2]
                if mh < H0 and mw < W0:
                    pad = t(10)
                    roi = img[H0 - mh - pad : H0 - pad, W0 - mw - pad : W0 - pad]
                    cv2.addWeighted(mm, 0.85, roi, 0.15, 0, roi)
            if m > 1.0:
                img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            writer.write(img)
    finally:
        if writer is not None:
            writer.close()


def draw_court(frame: np.ndarray, calib: CourtCalib, color=(0, 0, 255), thick: int = 2, show_points: bool = True, label: bool = True) -> np.ndarray:
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
                cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), color, thick, cv2.LINE_AA)
    for name, p in (calib.correspondences.items() if show_points else []):
        cv2.circle(img, tuple(map(int, p)), 6, (0, 255, 0), 2)
    if label:
        cv2.putText(img, f"court: {calib.method} conf={calib.conf:.2f}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return img
