"""Turns per-frame tracking into basketball events.

possession segments ──► dribbles inside each segment
        │
        └─ gaps between segments = ball flights ──► shot attempt? (rim zone / airball rule)
                                                     ├─ yes: make/miss, 2PT/3PT, dunk, then rebound
                                                     └─ no : pass (same team) | steal + turnover
made shot after a pass within the assist window ──► assist
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks

from .. import fusion
from ..config import Config
from ..court import template
from ..court.base import CourtCalib
from ..identity.tagging import Identities
from ..schema import Event, FrameState, RimObs
from .flight import Flight, build_flight, fit_arc
from .possession import Segment, compute_possession

RIM_DIAMETER_M = 0.457


@dataclass
class Verdict:
    """Was the ball scored? `reason` says why (shown in the app's scoring log), `conf` how sure (0..1)."""

    made: bool
    frame: int | None = None  # index into the frames list of the sighting that confirmed it
    reason: str = ""
    conf: float = 0.0


@dataclass
class GameAnalysis:
    events: list[Event] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    flights: list[Flight] = field(default_factory=list)
    holder: list[str | None] = field(default_factory=list)

    def by_type(self, t: str) -> list[Event]:
        return [e for e in self.events if e.type == t]


def _reach_w(pts: np.ndarray, rim: RimObs) -> float:
    """Closest the ball's path (the polyline through its sightings) gets to the rim opening, in rim widths."""
    w = rim.width
    q = np.array([rim.center[0], rim.bbox[1] + 0.1 * w])
    a, b = pts[:-1], pts[1:]
    ab = b - a
    L2 = np.maximum((ab**2).sum(1), 1e-9)
    u = np.clip(((q - a) * ab).sum(1) / L2, 0.0, 1.0)
    return float(np.hypot(*(a + ab * u[:, None] - q).T).min() / w)


class GameAnalyzer:
    def __init__(self, cfg: Config, fps: float, ids: Identities | None = None, calib: CourtCalib | None = None):
        self.cfg = cfg
        self.fps = fps
        self.ids = ids or Identities()
        self.calib = calib
        self._last_make = None

    # ---------------------------------------------------------------------------------------------
    def analyze(self, frames: list[FrameState]) -> GameAnalysis:
        out = GameAnalysis()
        if not frames:
            return out
        if self.calib is not None:  # a CourtCalib, or a CourtTrack with a court per frame
            fusion.annotate_players([f for f in frames if fusion.frame_court(self.calib, f.idx, self.cfg.fusion)],
                                    self.calib)
        segs = compute_possession(frames, lambda tid: self.ids.player(tid), self.cfg.possession, self.fps)
        out.segments = segs
        out.holder = [None] * len(frames)
        for s in segs:
            for i in range(s.start, s.end + 1):
                out.holder[i] = s.player

        dribbles_in: dict[int, int] = {}
        for si, s in enumerate(segs):
            team = self.ids.player_team.get(s.player)
            out.events.append(Event("possession_gain", frames[s.start].idx, frames[s.start].t, s.player, team,
                                    {"duration_s": frames[s.end].t - frames[s.start].t}))
            dr = self._dribbles(frames, s)
            dribbles_in[si] = len(dr)
            for i in dr:
                out.events.append(Event("dribble", frames[i].idx, frames[i].t, s.player, team))

        last_pass_to: dict[int, Event] = {}  # segment index -> pass that started it
        self._last_make = None  # (t, rim box) of the latest made shot
        for si, s in enumerate(segs):
            nxt = segs[si + 1] if si + 1 < len(segs) else None
            f_end = nxt.start - 1 if nxt else len(frames) - 1
            if f_end <= s.end:
                # immediate hand-over (no visible free flight)
                if nxt is not None:
                    self._transition(out, frames, s, nxt, None, si, last_pass_to)
                continue
            flight = build_flight(frames, s.end + 1, f_end)
            out.flights.append(flight)
            shot = self._shot(frames, s, flight)
            team = self.ids.player_team.get(s.player)
            if shot is not None and self._doubtful_miss(shot):
                probe = Event("shot", frames[s.end].idx, frames[s.end].t, s.player, team, shot)
                if nxt is None or not self._plausible_rebound(frames, nxt, probe):
                    shot = None  # an airball / near-miss nobody rebounds by the basket: it was a pass
            if shot is not None:
                ev = Event("shot", frames[s.end].idx, frames[s.end].t, s.player, team, shot)
                ev.data["flight"] = len(out.flights) - 1
                ev.data["seg"] = si
                out.events.append(ev)
                if shot["made"]:
                    self._last_make = (ev.t, shot["rim"])
                    self._assist(out, frames, segs, si, ev, last_pass_to, dribbles_in)
                if not shot["made"] and nxt is not None:
                    self._rebound(out, frames, segs[si + 1:], ev)
                continue
            if nxt is not None:
                self._transition(out, frames, s, nxt, flight, si, last_pass_to)
        if self.cfg.events.recover_makes:
            self._recover_makes(out, frames, segs, last_pass_to, dribbles_in)
        out.events.sort(key=lambda e: (e.frame, e.type))
        return out

    def _assist(self, out, frames, segs, si, shot_ev: Event, last_pass_to, dribbles_in) -> None:
        s = segs[si]
        pass_ev = last_pass_to.get(si)
        if (
            pass_ev is not None
            and frames[s.end].t - frames[s.start].t <= self.cfg.events.assist_window_s
            and dribbles_in.get(si, 0) <= self.cfg.events.assist_max_dribbles
        ):
            out.events.append(Event("assist", pass_ev.frame, pass_ev.t, pass_ev.player, pass_ev.team,
                                    {"to": s.player, "shot_frame": shot_ev.frame}))

    # ---------------------------------------------------------------------------------------------
    def _transition(self, out, frames, s: Segment, nxt: Segment, flight: Flight | None, si, last_pass_to) -> None:
        if nxt.player == s.player:
            return
        t_a = self.ids.player_team.get(s.player)
        t_b = self.ids.player_team.get(nxt.player)
        data = {"to": nxt.player, "receive_frame": frames[nxt.start].idx}
        if flight is not None:
            data["flight"] = len(out.flights) - 1
            data["airtime_s"] = flight.duration
            data.update(self._pass_geometry(frames, s, nxt))
        if t_a is not None and t_b is not None and t_a != t_b:
            out.events.append(Event("turnover", frames[s.end].idx, frames[s.end].t, s.player, t_a, {"to": nxt.player}))
            out.events.append(Event("steal", frames[nxt.start].idx, frames[nxt.start].t, nxt.player, t_b, {"from": s.player}))
        else:
            if t_a is None or t_b is None:
                data["team_unknown"] = True
            ev = Event("pass", frames[s.end].idx, frames[s.end].t, s.player, t_a, data)
            out.events.append(ev)
            last_pass_to[si + 1] = ev

    def _rebound(self, out, frames, after: list[Segment], miss: Event) -> None:
        nxt = after[0]
        t0 = frames[nxt.start].t
        if t0 - miss.t > self.cfg.events.rebound_window_s:
            return
        if not self._plausible_rebound(frames, nxt, miss):
            return
        team = self.ids.player_team.get(nxt.player)
        held: dict[str, float] = {}
        for s in after:
            if frames[s.start].t > t0 + self.cfg.events.rebound_control_s:
                break
            tm = self.ids.player_team.get(s.player)
            if tm is not None:
                held[tm] = held.get(tm, 0.0) + frames[s.end].t - frames[s.start].t + 1 / self.fps
        if held and max(held, key=held.get) != team:
            team = max(held, key=held.get)
            nxt = next(s for s in after if self.ids.player_team.get(s.player) == team)
        offensive = team is not None and team == miss.team
        out.events.append(Event("rebound", frames[nxt.start].idx, frames[nxt.start].t, nxt.player, team,
                                {"offensive": offensive, "shot_frame": miss.frame}))

    def _doubtful_miss(self, shot: dict) -> bool:
        """A miss we are not sure was thrown at the rim: an airball, or a path that only just reached it."""
        return not shot["made"] and (shot["airball"] or shot["rim_reach_w"] > self.cfg.events.shot_sure_reach_w)

    def _plausible_rebound(self, frames, nxt: Segment, miss: Event) -> bool:
        """The first touch after a miss is a rebound only if it comes soon after the ball reached the rim and the\n        player is by the basket; otherwise the shot was probably a pass flying near the hoop."""
        ec = self.cfg.events
        rim = miss.data.get("rim")
        if rim is None:
            return False
        rim_t = miss.data.get("rim_t")
        t0 = frames[nxt.start].t
        if rim_t is not None and not (-0.3 <= t0 - rim_t <= ec.rebound_after_rim_s):
            return False
        p = next((p for p in frames[nxt.start].players if self.ids.player(p.track_id) == nxt.player), None)
        if p is None:
            return False
        w = max(1.0, rim[2] - rim[0])
        return abs(p.center[0] - (rim[0] + rim[2]) / 2) <= ec.rebound_max_rim_dist * w

    # ---------------------------------------------------------------------------------------------
    def _dribbles(self, frames: list[FrameState], s: Segment) -> list[int]:
        """Frame indices of bounces: local maxima of ball image-y near the floor with enough amplitude."""
        idx, ys, floor_y, h = [], [], [], []
        for i in range(s.start, s.end + 1):
            f = frames[i]
            if f.ball is None:
                continue
            p = next((p for p in f.players if self.ids.player(p.track_id) == s.player), None)
            if p is None:
                continue
            idx.append(i)
            ys.append(f.ball.xy[1])
            floor_y.append(p.bbox[1] + 0.6 * p.height)
            h.append(p.height)
        if len(ys) < 5:
            return []
        ys = np.asarray(ys)
        prom = self.cfg.events.dribble_min_amp * float(np.median(h))
        peaks, _ = find_peaks(ys, prominence=prom)
        return [idx[k] for k in peaks if ys[k] >= floor_y[k]]

    def _shot(self, frames: list[FrameState], s: Segment, fl: Flight) -> dict | None:
        """Classify a flight as a shot attempt; returns shot data (made, points, ...) or None."""
        rims = frames[s.end].rims or frames[min(fl.end, len(frames) - 1)].rims
        if not rims or len(fl.points) < 2:
            return None
        shooter = next((p for p in frames[s.end].players if self.ids.player(p.track_id) == s.player), None)
        sh_h = shooter.height if shooter else 100.0
        pts = np.array([[p[2], p[3]] for p in fl.points])
        release_xy = (frames[s.end].ball.xy if frames[s.end].ball else tuple(pts[0]))
        ec = self.cfg.events
        rim, zone_hit = None, None
        for r in rims:
            rx1, ry1, rx2, ry2 = r.bbox
            cx, w = (rx1 + rx2) / 2, r.width
            inz = (np.abs(pts[:, 0] - cx) <= ec.rim_zone_w * w) & (pts[:, 1] >= ry1 - ec.rim_zone_h * w) & (pts[:, 1] <= ry2 + 0.5 * w)
            if inz.any():
                rim, zone_hit = r, int(np.argmax(inz))
                break
        rose = release_xy[1] - pts[:, 1].min() >= ec.shot_min_rise_frac * sh_h
        if rim is None:
            # airball: rose clearly and peaked above / near a rim
            for r in rims:
                apex = pts[np.argmin(pts[:, 1])]
                if rose and apex[1] < r.bbox[1] and abs(apex[0] - r.center[0]) < ec.airball_max_rim_dist * r.width:
                    rim = r
                    break
            if rim is None:
                return None
        elif not rose and np.hypot(release_xy[0] - rim.center[0], release_xy[1] - rim.center[1]) > ec.dunk_release_rim_dist * rim.width:
            return None  # entered rim zone without rising: a pass under the basket, not a shot

        reach = _reach_w(pts, rim)
        if zone_hit is not None and reach > ec.shot_reach_w:
            return None  # crossed the rim area in the picture without being thrown at the rim: a pass
        if self._last_make is not None and frames[s.end].t - self._last_make[0] < ec.after_make_dead_s:
            mx1, _, mx2, _ = self._last_make[1]
            if abs((mx1 + mx2) / 2 - rim.center[0]) < 2 * rim.width:
                return None  # inbound pass under the basket that was just scored on
        verdict = self._made(frames, fl, rim, zone_hit)
        if not verdict.made and zone_hit is not None and self._pass_like(pts, fl, rim):
            return None  # flew past the hoop without ever being shot at it: a pass (or a steal), not a miss
        made, make_frame = verdict.made, (frames[verdict.frame].idx if verdict.frame is not None else None)
        if zone_hit is not None:  # arc of the shot itself: release -> rim (not the fall through the net)
            fl.arc = fit_arc(fl.points[: zone_hit + 3]) or fl.arc
        rel_d = np.hypot(release_xy[0] - rim.center[0], release_xy[1] - rim.center[1]) / rim.width
        # dunk: released at the rim with the shooter's hands (or raised-arm bbox top) up at rim height
        reach_y = shooter.bbox[1] if shooter else rim.bbox[1]
        if shooter is not None and shooter.keypoints is not None:
            reach_y = min(reach_y, shooter.highest_hand_y())
        dunk = made and rel_d <= ec.dunk_release_rim_dist and reach_y <= rim.bbox[3] + 0.5 * rim.width
        court_xy, three, dist_m, line_m, hoop = self._position(frames, s, rim, bool(dunk), shooter is not None)
        inside_pts, outside_pts = ec.point_values()
        if not made and dist_m is not None and dist_m > ec.shot_max_dist_m:
            return None  # thrown from far beyond any shooting range: a pass
        points = (outside_pts if three else inside_pts) if made else 0
        apex_above_rim_m = None
        if fl.arc is not None:
            apex_above_rim_m = (rim.center[1] - fl.arc.apex_xy[1]) / rim.width * RIM_DIAMETER_M
        return {
            "made": made,
            "points": points,
            "three": three,
            "dunk": bool(dunk),
            "airball": zone_hit is None,
            "shot_xy": court_xy,
            "hoop": hoop,
            "distance_m": dist_m,
            "three_line_m": line_m,  # + outside / - inside the 3PT line
            "three_close": line_m is not None and not dunk and abs(line_m) < ec.three_close_margin_m,
            "make_frame": make_frame,
            "rim": list(rim.bbox),
            "rim_reach_w": round(reach, 2),
            "arc_apex_above_rim_m": apex_above_rim_m,
            "airtime_s": fl.duration,
            "rim_t": self._rim_time(fl, pts, zone_hit),
            "reason": verdict.reason,
            "confidence": round(verdict.conf, 2),
        }

    def _rim_time(self, fl: Flight, pts: np.ndarray, zone_hit: int | None) -> float:
        """When the ball got to the rim (an airball: when it peaked)."""
        k = zone_hit if zone_hit is not None else int(np.argmin(pts[:, 1]))
        return float(fl.points[min(k, len(fl.points) - 1)][1])

    def _pass_like(self, pts: np.ndarray, fl: Flight, rim: RimObs) -> bool:
        """A flight that reached the rim zone but was not a shot: the ball never rose up to rim level, or it sailed on\n        past the hoop in the same direction at the same speed (a shot that misses bounces off the rim, backboard or\n        net and changes direction)."""
        ec = self.cfg.events
        w = rim.width
        if pts[:, 1].min() > rim.bbox[1] + ec.miss_min_apex_w * w:
            return True
        # a lob sails OVER the hoop: at rim height or higher it is a full rim width to one side, then a full width to the
        # other. A shot comes down onto the rim and a miss bounces off it, so it never swings wide on both sides.
        lat = (pts[:, 0] - rim.center[0]) / w
        up = pts[:, 1] <= rim.bbox[1] + 0.5 * w
        sides = np.sign(lat[up & (np.abs(lat) >= 0.9)])
        if len(sides) >= 2 and sides[0] != sides[-1] and _reach_w(pts, rim) >= 0.75:  # ...and never touches the rim
            return True
        t = np.array([p[1] for p in fl.points], float)
        d = np.hypot(pts[:, 0] - rim.center[0], pts[:, 1] - rim.center[1])
        c = int(np.argmin(d))
        a, b = max(0, c - 2), min(len(pts) - 1, c + 2)
        if c - a < 1 or b - c < 2:  # not enough of the flight after the rim to tell: keep it as a shot
            return False
        v_in = (pts[c] - pts[a]) / max(t[c] - t[a], 1e-6)
        v_out = (pts[b] - pts[c]) / max(t[b] - t[c], 1e-6)
        n_in, n_out = float(np.hypot(*v_in)), float(np.hypot(*v_out))
        if n_in < 1e-6 or n_out < 1e-6:
            return False
        cos = float(v_in @ v_out) / (n_in * n_out)
        r = ec.pass_through_speed_ratio
        return cos > ec.pass_through_cos and r < n_out / n_in < 1 / r

    def _position(self, frames, s: Segment, rim: RimObs, dunk: bool, has_shooter: bool = True):
        """(court_xy, outside-the-arc, distance_m, three_line_m, hoop) for a shot by segment `s` at `rim`."""
        court_xy, feet = self._shot_position(frames, s) if has_shooter else (None, None)
        three, dist_m, line_m, hoop = None, None, None, None
        court = self.calib.at(frames[s.end].idx) if self.calib is not None else None
        hoop = fusion.hoop_for_rim(court, rim, self.cfg.fusion)  # the basket the ball went to
        if court_xy is not None:
            if hoop is None:
                hoop, _ = template.nearest_hoop(court_xy, self.cfg.court)
            hx, hy = template.hoop_positions(self.cfg.court)[hoop]
            dist_m = float(np.hypot(court_xy[0] - hx, court_xy[1] - hy))
            line_m = template.three_line_distance(court_xy, self.cfg.court, hoop)
            if feet:  # both feet must be behind the line: judge by the foot that is closer to the basket
                line_m = min([line_m] + [template.three_line_distance(f, self.cfg.court, hoop) for f in feet])
            # outside the line by a clear margin = three; on the line or inside = two
            three = line_m >= self.cfg.events.three_line_margin_m and not dunk
        return court_xy, three, dist_m, line_m, hoop

    def _shot_position(self, frames, s: Segment):
        """(court position, [court position of each visible ankle]) the shot was taken from: the shooter's feet when
        they were last on the floor."""
        i0 = max(s.start, s.end - int(self.cfg.events.shot_pos_lookback_s * self.fps))
        cands = [(f, p) for f in frames[i0 : s.end + 1] for p in f.players
                 if self.ids.player(p.track_id) == s.player and p.court_xy is not None]
        if not cands:
            return None, None
        f, p = max(cands, key=lambda fp: fp[1].bbox[3])
        feet = None
        court = self.calib.at(f.idx) if self.calib is not None else None
        if court is not None and p.keypoints is not None:
            try:
                ank = np.asarray(p.keypoints)[[15, 16]]  # COCO left / right ankle
                ank = ank[ank[:, 2] > 0.4]
                if len(ank):
                    feet = [(float(x), float(y)) for x, y in court.image_to_court([tuple(a[:2]) for a in ank])]
            except Exception:  # noqa: BLE001  (fall back to the feet midpoint)
                feet = None
        return p.court_xy, feet

    def _made(self, frames, fl: Flight, rim: RimObs, zone_hit: int | None) -> Verdict:
        """Did this flight go through the rim? Looks a bit past the flight end (the catch under the basket can start a
        possession while the ball is still in the net)."""
        if zone_hit is None:
            return Verdict(False, None, "airball")
        ec = self.cfg.events
        i0 = fl.start + max(0, zone_hit - 2)
        i1 = min(len(frames) - 1, fl.end + int(0.5 * self.fps), i0 + int(ec.make_window_s * self.fps))
        return self._judge(self._ball_seq(frames, i0, i1, rim), rim)

    def _net_candidate(self, f: FrameState, rim: RimObs):
        """When the tracker has no ball (hidden by the net / rim), the best raw ball detection right at the basket."""
        ec = self.cfg.events
        cx, w = rim.center[0], rim.width
        best = None
        for b in f.ball_candidates:
            if b.conf < ec.net_candidate_conf:
                continue
            if abs(b.xy[0] - cx) <= 1.2 * w and rim.bbox[1] - 1.0 * w <= b.xy[1] <= rim.bbox[3] + 3.0 * w:
                if best is None or b.conf > best.conf:
                    best = b
        return best.xy if best is not None else None

    def _ball_seq(self, frames, i0: int, i1: int, rim: RimObs) -> list[tuple[int, tuple[float, float]]]:
        seq = []
        for i in range(max(0, i0), i1 + 1):
            f = frames[i]
            p = f.ball.xy if f.ball is not None else self._net_candidate(f, rim)
            if p is not None:
                seq.append((i, p))
        return seq

    def _judge(self, seq, rim: RimObs) -> Verdict:
        """Made basket or not, from the ball sightings `seq` = [(frame-list index, (x, y))] around one visit to a rim.

        1. The ball is seen above the rim plane and then below it, near the rim's middle. Up to `make_gap_s` may pass
           unseen in between (it is hidden in the net); after a long gap the ball must come out straight under the net.
        2. The ball arrives centred and falling, vanishes into the net, and is next seen straight under it, never having
           bounced back above the rim (a rim-out comes back up and out)."""
        ec = self.cfg.events
        rx1, ry1, rx2, ry2 = rim.bbox
        w = rim.width
        cx = (rx1 + rx2) / 2
        cy = ry1 + min(ec.make_plane * w, 0.5 * (ry2 - ry1))
        short = int(0.2 * self.fps)
        long_ = max(short, int(round(ec.make_gap_s * self.fps)))
        for (ia, a), (ib, b) in zip(seq, seq[1:]):
            if a[1] <= cy < b[1] and ib - ia <= long_:
                x = a[0] + (b[0] - a[0]) * (cy - a[1]) / max(b[1] - a[1], 1e-6)
                if abs(x - cx) > ec.make_center_tol * w:
                    continue
                if ib - ia <= short:
                    return Verdict(True, ib, "ball seen dropping through the hoop", 0.9)
                if b[1] >= ry2 - 0.2 * w and abs(b[0] - cx) <= ec.make_reappear_w * w:
                    return Verdict(True, ib, "ball dropped into the net and came out underneath", 0.75)
        # 2. arrives centred and falling, then vanishes into the net
        last = None
        for k, (_, p) in enumerate(seq):
            if p[1] < cy and abs(p[0] - cx) <= 1.5 * w and p[1] >= ry1 - 2.5 * w:
                last = k
        if last is None:
            return Verdict(False, None, "ball never got to the rim")
        pts = [p for _, p in seq[max(0, last - 3): last + 1] if p[1] < cy]
        if len(pts) < 2 or pts[-1][1] <= pts[0][1]:
            return Verdict(False, None, "ball was not falling into the rim")
        ys, xs = np.array([p[1] for p in pts]), np.array([p[0] for p in pts])
        x_cross = float(np.polyval(np.polyfit(ys, xs, 1), cy)) if np.ptp(ys) > 1e-6 else float(xs[-1])
        if abs(x_cross - cx) > ec.make_vanish_tol * w:
            return Verdict(False, None, "ball came in off-centre (rim-out)")
        i_last = seq[last][0]
        post = seq[last + 1:]
        for i, p in post:
            if i - i_last > int(round(ec.make_bounce_s * self.fps)):
                break
            if p[1] < cy:
                return Verdict(False, None, "ball bounced back out of the rim")
        if not post:
            return Verdict(False, None, "ball never seen after reaching the rim")
        i1, p1 = post[0]
        if p1[1] >= cy and abs(p1[0] - cx) <= ec.make_reappear_w * w:
            return Verdict(True, i1, "ball vanished into the net and dropped straight out", 0.6)
        return Verdict(False, None, "ball left the rim sideways")

    # ---------------------------------------------------------------------------------------------
    def _recover_makes(self, out: GameAnalysis, frames, segs, last_pass_to, dribbles_in) -> None:
        """Watch each rim directly: a ball that goes down through it is a basket even if the possession logic never
        produced a shot for it. A shot we scored as a miss that the rim watch scores as a make is corrected; a basket
        with no shot at all is credited to the last player who had the ball."""
        ec = self.cfg.events
        hold = int(1.0 * self.fps)
        visits: list[tuple[int, int, RimObs]] = []  # (first, last frame index in the rim zone, rim)
        cur = None
        for i, f in enumerate(frames):
            hit = None
            if f.ball is not None:
                for r in f.rims:
                    cx, w = r.center[0], r.width
                    if (abs(f.ball.xy[0] - cx) <= ec.rim_zone_w * w and r.bbox[1] - ec.rim_zone_h * w <= f.ball.xy[1] <= r.bbox[3] + 0.5 * w):
                        hit = r
                        break
            if hit is None:
                continue
            same = cur is not None and i - cur[1] <= hold and abs(hit.center[0] - cur[2].center[0]) < 2 * hit.width
            if same:
                cur[1] = i
            else:
                if cur is not None:
                    visits.append((cur[0], cur[1], cur[2]))
                cur = [i, i, hit]
        if cur is not None:
            visits.append((cur[0], cur[1], cur[2]))

        for first, last, rim in visits:
            i1 = min(len(frames) - 1, last + int(0.5 * self.fps), first + int(ec.make_window_s * self.fps) + (last - first))
            v = self._judge(self._ball_seq(frames, first - 2, i1, rim), rim)
            if not v.made or v.frame is None:
                continue
            t_make = frames[v.frame].t
            made_before = [e for e in out.events if e.type == "shot" and e.data.get("made")]
            if any(abs(t_make - e.t) < ec.after_make_dead_s and abs(e.data["rim"][0] + e.data["rim"][2] - 2 * rim.center[0]) < 4 * rim.width
                   for e in made_before):
                continue  # already scored, or the inbound / dribble right after it
            reason = v.reason + " (found by watching the rim)"
            cover = None  # a shot the possession logic already made of it (and called a miss)
            for e in out.events:
                if e.type == "shot" and -0.5 <= t_make - e.t <= 3.5:
                    cover = e
            if cover is not None:
                d = cover.data
                if d.get("made"):
                    continue
                inside_pts, outside_pts = ec.point_values()
                d.update(made=True, points=outside_pts if d.get("three") else inside_pts, make_frame=frames[v.frame].idx,
                         reason=reason, confidence=round(min(v.conf, 0.7), 2), recovered=True)
                out.events = [e for e in out.events if not (e.type == "rebound" and e.data.get("shot_frame") == cover.frame)]
                if cover.data.get("seg") is not None:
                    self._assist(out, frames, segs, cover.data["seg"], cover, last_pass_to, dribbles_in)
                continue
            si = None
            for k, s in enumerate(segs):
                if s.end <= v.frame and t_make - frames[s.end].t <= ec.recover_max_holder_gap_s:
                    si = k
            s = segs[si] if si is not None else None
            inside_pts, outside_pts = ec.point_values()
            data = {"made": True, "points": inside_pts, "three": None, "dunk": False, "airball": False, "shot_xy": None, "hoop": None,
                    "distance_m": None, "three_line_m": None, "three_close": False, "make_frame": frames[v.frame].idx,
                    "rim": list(rim.bbox), "arc_apex_above_rim_m": None, "airtime_s": None, "reason": reason,
                    "confidence": round(min(v.conf, 0.7), 2), "recovered": True, "seg": si}
            if s is not None:
                court_xy, three, dist_m, line_m, hoop = self._position(frames, s, rim, False)
                data.update(shot_xy=court_xy, three=three, hoop=hoop, distance_m=dist_m, three_line_m=line_m,
                            three_close=line_m is not None and abs(line_m) < ec.three_close_margin_m,
                            points=outside_pts if three else inside_pts)
                ev = Event("shot", frames[s.end].idx, frames[s.end].t, s.player, self.ids.player_team.get(s.player), data)
            else:  # nobody seen holding the ball: the basket counts for the score once someone is picked in the app
                ev = Event("shot", frames[v.frame].idx, frames[v.frame].t, None, None, data)
            out.events.append(ev)
            if si is not None:
                self._assist(out, frames, segs, si, ev, last_pass_to, dribbles_in)

    def _pass_geometry(self, frames, s: Segment, nxt: Segment) -> dict:
        a = next((p for p in frames[s.end].players if self.ids.player(p.track_id) == s.player), None)
        b = next((p for p in frames[nxt.start].players if self.ids.player(p.track_id) == nxt.player), None)
        if a is None or b is None or a.court_xy is None or b.court_xy is None:
            return {}
        return {"from_xy": a.court_xy, "to_xy": b.court_xy,
                "distance_m": float(np.hypot(a.court_xy[0] - b.court_xy[0], a.court_xy[1] - b.court_xy[1]))}
