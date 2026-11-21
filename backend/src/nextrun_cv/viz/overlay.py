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


def _minimap(spec: CourtSpec, f: FrameState, ids: Identities, holder: str | None, scale: float = 9) -> np.ndarray:
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
        r = max(2, int(round(scale * 0.55)))  # dots shrink with the map
        cv2.circle(img, c, r, team_color(ids.player_team.get(name)), -1, cv2.LINE_AA)
        if name == holder:
            cv2.circle(img, c, r + 3, (0, 165, 255), 2, cv2.LINE_AA)
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
    hm_ = float(np.median([p.height for p in f0.players])) if f0.players else 100.0
    if f0.ball is not None and f1.ball is not None and np.hypot(f1.ball.xy[0] - f0.ball.xy[0], f1.ball.xy[1] - f0.ball.xy[1]) <= 0.9 * hm_:
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


def _pill_size(text, scale, th, m, pad=6):
    s, tk, p = scale * m, max(1, int(round(th * m))), int(pad * m)
    (tw, tt), base = cv2.getTextSize(text, FONT, s, tk)
    return tw + 2 * p, tt + base + 2 * p


def _place(x, y, w, h, taken: list, W: int, step: int) -> tuple[int, int]:
    """Top-left for a w x h tag wanted at (x, y), moved up past tags already placed so none overlap."""
    x = int(min(max(0, x), max(0, W - w)))
    for _ in range(12):
        if not any(x < a2 and a1 < x + w and y < b2 and b1 < y + h for a1, b1, a2, b2 in taken):
            break
        y -= h + step
    y = max(0, int(y))
    taken.append((x, y, x + w, y + h))
    return x, y


# COCO-17 skeleton (pairs of keypoint indices)
SKELETON = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]


def _player_box(img, p, col, t, holder: bool) -> None:
    """Corner brackets around the player in the team colour (orange for the ball holder). No full outline or pose
    skeleton: on a crowded court they turn into a tangle of lines."""
    x1, y1, x2, y2 = map(int, p.bbox)
    bc = (0, 165, 255) if holder else col
    L = max(t(8), int(min(x2 - x1, y2 - y1) * 0.22))
    th = t(3) if holder else t(2)
    for cx, cy, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        cv2.line(img, (cx, cy), (cx + dx * L, cy), bc, th, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (cx, cy + dy * L), bc, th, cv2.LINE_AA)


def _teams(score: dict, reb: dict, ast: dict, ids) -> list[str]:
    return sorted({tm for tm in (set(score) | set(reb) | set(ast) | set(ids.player_team.values())) if tm and tm != "?"}) or ["A", "B"]


def _scoreboard_size(n_teams: int, m: float) -> tuple[int, int]:
    t = lambda v: int(round(v * m))  # noqa: E731
    return t(360), t(52) + t(20) + t(40) * max(2, n_teams)


def _scoreboard(img, f, score: dict, reb: dict, ast: dict, ids, m: float, flash: dict | None = None,
                x0: int | None = None, y0: int | None = None) -> None:
    """Team score card with its top-left at (x0, y0): one row per team with points, rebounds and assists so far.
    `flash` = {(team, stat): 0..1} briefly highlights a number that just changed."""
    t = lambda v: int(round(v * m))  # noqa: E731
    teams = _teams(score, reb, ast, ids)
    flash = flash or {}
    w, h = t(360), t(52) + t(20) + t(40) * len(teams)
    x0 = t(14) if x0 is None else x0
    y0 = t(14) if y0 is None else y0
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


# --- where the score card and minimap go ---------------------------------------------------------------------
CORNERS = ("tl", "tr", "bl", "br")


def _corner_rect(corner: str, w: int, h: int, W: int, H: int, pad: int) -> tuple[int, int, int, int]:
    x1 = pad if corner[1] == "l" else W - pad - w
    y1 = pad if corner[0] == "t" else H - pad - h
    return x1, y1, x1 + w, y1 + h


def _occupancy(frames: list[FrameState], W: int, H: int, cell: int) -> np.ndarray:
    """Integral image of how often each cell holds a player (with the name tag above them), the ball or a hoop,
    averaged over the clip: overlays should sit where the action is not."""
    gw, gh = -(-W // cell), -(-H // cell)
    occ = np.zeros((gh, gw), np.float32)
    step = max(1, len(frames) // 400)
    n = 0

    def add(x1, y1, x2, y2, wgt):
        c1, r1 = max(0, int(x1 // cell)), max(0, int(y1 // cell))
        c2, r2 = min(gw, int(x2 // cell) + 1), min(gh, int(y2 // cell) + 1)
        if c2 > c1 and r2 > r1:
            occ[r1:r2, c1:c2] += wgt

    for f in frames[::step]:
        n += 1
        for p in f.players:
            x1, y1, x2, y2 = p.bbox
            add(x1, y1 - 0.3 * (y2 - y1), x2, y2 + 0.1 * (y2 - y1), 1.0)  # name tag above, foot ring below
        for r in f.rims:  # shots end here: never cover a hoop
            x1, y1, x2, y2 = r.bbox
            add(x1 - (x2 - x1), y1 - (x2 - x1), x2 + (x2 - x1), y2 + 2 * (x2 - x1), 3.0)
        if f.ball is not None:
            bx, by = f.ball.xy
            add(bx - 3 * f.ball.radius, by - 3 * f.ball.radius, bx + 3 * f.ball.radius, by + 3 * f.ball.radius, 2.0)
    occ /= max(1, n)
    return np.pad(occ.cumsum(0).cumsum(1), ((1, 0), (1, 0)))


def _busy(integral: np.ndarray, rect, cell: int) -> float:
    x1, y1, x2, y2 = (int(v // cell) for v in rect)
    gh, gw = integral.shape[0] - 1, integral.shape[1] - 1
    x1, x2, y1, y2 = max(0, x1), min(gw, x2 + 1), max(0, y1), min(gh, y2 + 1)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return float(integral[y2, x2] - integral[y1, x2] - integral[y2, x1] + integral[y1, x1])


def plan_layout(frames: list[FrameState], W: int, H: int, card: tuple[int, int], minimap: tuple[int, int] | None,
                pad: int) -> dict[str, str]:
    """Pick a corner for the score card (with the play-by-play feed under / over it) and one for the minimap, so
    they cover the fewest players, hoops and ball positions over the whole video. Default: card top-left, minimap
    bottom-right, kept unless another layout is clearly emptier."""
    cell = max(8, min(W, H) // 48)
    integral = _occupancy(frames, W, H, cell)
    options = [(c, None) for c in CORNERS] if minimap is None else [(a, b) for a in CORNERS for b in CORNERS if a != b]
    best, best_cost = ("tl", None if minimap is None else "br"), None
    for a, b in options:
        cost = _busy(integral, _corner_rect(a, *card, W, H, pad), cell)
        if b is not None:
            cost += _busy(integral, _corner_rect(b, *minimap, W, H, pad), cell)
        cost += 0.02 * ((a != "tl") + (b is not None and b != "br"))  # small nudge towards the familiar layout
        if best_cost is None or cost < best_cost:
            best, best_cost = (a, b), cost
    return {"card": best[0], "minimap": best[1]}


def _overlaps_players(rect, players) -> bool:
    x1, y1, x2, y2 = rect
    for p in players:
        a1, b1, a2, b2 = p.bbox
        b1 -= 0.3 * (b2 - b1)
        if a1 < x2 and x1 < a2 and b1 < y2 and y1 < b2:
            return True
    return False


def _see_through(img, rect, before: np.ndarray, alpha: float) -> None:
    """Fade what was just drawn in rect back towards `before` (the frame there before drawing)."""
    x1, y1, x2, y2 = rect
    roi = img[y1:y2, x1:x2]
    roi[:] = cv2.addWeighted(roi, alpha, before, 1 - alpha, 0)


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
    shot_flights = {e.data.get("flight") for e in analysis.events if e.type == "shot"}  # only shots get an arc
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
                # overlays scale with the output's shape: a portrait phone clip gets a smaller card than 16:9 footage
                ui = m * 0.85 * min(1.0, max(0.72, min(size[0] / 1280, size[1] / 720)))  # floor keeps text readable
                u = lambda v: max(1, int(round(v * ui)))  # noqa: E731
                pad = u(12)
                n_teams = len(_teams({}, {}, {}, ids))
                card_w, card_h = _scoreboard_size(n_teams, ui)
                feed_h = 3 * (_pill_size("REBOUND  Player 10", 0.55, 1, ui, pad=7)[1] + u(6)) + u(10)
                mm_scale = 9 * ui
                mm_size = None
                if calib is not None:
                    mm_size = (int(calib.spec.length * mm_scale) + 16, int(calib.spec.width * mm_scale) + 16)
                    if mm_size[0] >= W0 * 0.45 or mm_size[1] >= H0 * 0.45:  # keep the minimap under ~45 % of the frame
                        shrink = min(0.45 * W0 / mm_size[0], 0.45 * H0 / mm_size[1])
                        mm_scale *= shrink
                        mm_size = (int(calib.spec.length * mm_scale) + 16, int(calib.spec.width * mm_scale) + 16)
                layout = plan_layout(frames, W0, H0, (card_w, card_h + feed_h), mm_size, pad)
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
            for r in f.rims:  # the hoop: a clean ring on the rim, no detector box or confidence
                x1, y1, x2, y2 = r.bbox
                rw_ = (x2 - x1) / 2
                cv2.ellipse(img, (int((x1 + x2) / 2), int(y1 + 0.15 * rw_ * 2)), (int(rw_), max(2, int(rw_ * 0.35))), 0, 0, 360,
                            (0, 140, 255), t(2), cv2.LINE_AA)
            # players: ring under the feet in the team colour, name tag with running points
            tags = []
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
                c = callout.get(name)
                if c is not None:  # orange ring for the player who just made the play
                    cv2.ellipse(img, (cx, y2), (rw + t(10), max(t(6), rw // 3 + t(6))), 0, 0, 360, (0, 165, 255), t(3), cv2.LINE_AA)
                tags.append((y2, cx, y1, name or "?", col, c))
            taken: list = []
            for _, cx, y1, label, col, c in sorted(tags, key=lambda q: -q[0]):  # nearest to the camera first
                w_, h_ = _pill_size(label, 0.5, 1, m, pad=4)
                x_, y_ = _place(cx - w_ // 2, y1 - h_ - t(6), w_, h_, taken, W0, t(3))
                _pill(img, label, x_, y_, col, 0.5, 1, m, pad=4)
                if c is not None:  # "REBOUND" / "ASSIST" over the player who just made the play, with a pop-in
                    age = (idx - c[0]) / show
                    sc = 0.62 * (1.25 - 0.25 * min(1.0, age * 6))
                    cw, ch = _pill_size(c[1], sc, 2, m, pad=5)
                    x_, y_ = _place(cx - cw // 2, y_ - ch - t(4), cw, ch, taken, W0, t(3))
                    _pill(img, c[1], x_, y_, (0, 165, 255), sc, 2, m, fg=(255, 255, 255), pad=5, alpha=0.95)
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
            # flight arc: fitted curve for the whole flight
            fi = flights_at.get(k)
            if fi is not None and fi in shot_flights and analysis.flights[fi].arc is not None:
                fl = analysis.flights[fi]
                ts = np.linspace(fl.points[0][1], fl.points[-1][1], 40)
                curve = fl.arc.eval(ts)
                if fk.idx in motion_at:  # stabilized view -> this frame
                    curve = cv2.perspectiveTransform(curve.reshape(-1, 1, 2).astype(np.float64), motion_at[fk.idx]).reshape(-1, 2)
                cv2.polylines(img, [curve.astype(np.int32)], False, (255, 255, 120), t(2), cv2.LINE_AA)
            flash = {k_: 1.0 - (idx - at) / show for k_, at in changed.items() if idx - at <= show}
            # score card in the emptiest corner for this video; see-through while a player is underneath it
            cw_, ch_ = _scoreboard_size(len(_teams(score, reb, ast, ids)), ui)
            cx1, cy1, cx2, cy2 = _corner_rect(layout["card"], cw_, ch_, W0, H0, pad)
            before = img[cy1:cy2, cx1:cx2].copy()
            _scoreboard(img, f, score, reb, ast, ids, ui, flash, cx1, cy1)
            if _overlaps_players((cx1, cy1, cx2, cy2), f.players):
                _see_through(img, (cx1, cy1, cx2, cy2), before, 0.45)
            # play-by-play feed next to the card (under it at the top, over it at the bottom): latest rebound / assist calls
            top, left = layout["card"][0] == "t", layout["card"][1] == "l"
            ey = cy2 + u(10) if top else cy1 - u(10)
            for at, label, player, team, detail in calls[-3:]:
                text = f"{label}  {player or 'Player'}" + (f"  >  {detail}" if detail else "")
                pw, ph = _pill_size(text, 0.55, 1, ui, pad=7)
                px_ = cx1 if left else cx2 - pw
                py_ = ey if top else ey - ph
                _pill(img, text, px_, py_, team_color(team), 0.55, 1, ui, pad=7)
                ey = py_ + ph + u(6) if top else py_ - u(6)
            if calib is not None and layout["minimap"] is not None:
                mm = _minimap(calib.spec, f, ids, holder, scale=mm_scale)
                mh, mw = mm.shape[:2]
                if mh < H0 and mw < W0:
                    mx1, my1, mx2, my2 = _corner_rect(layout["minimap"], mw, mh, W0, H0, pad)
                    roi = img[my1:my2, mx1:mx2]
                    a = 0.4 if _overlaps_players((mx1, my1, mx2, my2), f.players) else 0.85
                    cv2.addWeighted(mm, a, roi, 1 - a, 0, roi)
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
