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

from ..config import Config
from ..court import template
from ..court.base import CourtCalib
from ..identity.tagging import Identities
from ..schema import Event, FrameState, RimObs
from .flight import Flight, build_flight, fit_arc
from .possession import Segment, compute_possession

RIM_DIAMETER_M = 0.457


@dataclass
class GameAnalysis:
    events: list[Event] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    flights: list[Flight] = field(default_factory=list)
    holder: list[str | None] = field(default_factory=list)

    def by_type(self, t: str) -> list[Event]:
        return [e for e in self.events if e.type == t]


class GameAnalyzer:
    def __init__(self, cfg: Config, fps: float, ids: Identities | None = None, calib: CourtCalib | None = None):
        self.cfg = cfg
        self.fps = fps
        self.ids = ids or Identities()
        self.calib = calib

    # ---------------------------------------------------------------------------------------------
    def analyze(self, frames: list[FrameState]) -> GameAnalysis:
        out = GameAnalysis()
        if not frames:
            return out
        self._annotate_court_positions(frames)
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
            if shot is not None:
                ev = Event("shot", frames[s.end].idx, frames[s.end].t, s.player, team, shot)
                ev.data["flight"] = len(out.flights) - 1
                out.events.append(ev)
                pass_ev = last_pass_to.get(si)
                if (
                    shot["made"]
                    and pass_ev is not None
                    and frames[s.end].t - frames[s.start].t <= self.cfg.events.assist_window_s
                    and dribbles_in.get(si, 0) <= self.cfg.events.assist_max_dribbles
                ):
                    out.events.append(Event("assist", pass_ev.frame, pass_ev.t, pass_ev.player, pass_ev.team,
                                            {"to": s.player, "shot_frame": ev.frame}))
                if not shot["made"] and nxt is not None:
                    self._rebound(out, frames, nxt, ev)
                continue
            if nxt is not None:
                self._transition(out, frames, s, nxt, flight, si, last_pass_to)
        out.events.sort(key=lambda e: (e.frame, e.type))
        return out

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

    def _rebound(self, out, frames, nxt: Segment, miss: Event) -> None:
        if frames[nxt.start].t - miss.t > self.cfg.events.rebound_window_s:
            return
        team = self.ids.player_team.get(nxt.player)
        offensive = team is not None and team == miss.team
        out.events.append(Event("rebound", frames[nxt.start].idx, frames[nxt.start].t, nxt.player, team,
                                {"offensive": offensive, "shot_frame": miss.frame}))

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

        made, make_frame = self._made(frames, fl, rim, zone_hit)
        if zone_hit is not None:  # arc of the shot itself: release -> rim (not the fall through the net)
            fl.arc = fit_arc(fl.points[: zone_hit + 3]) or fl.arc
        rel_d = np.hypot(release_xy[0] - rim.center[0], release_xy[1] - rim.center[1]) / rim.width
        # dunk: released at the rim with the shooter's hands (or raised-arm bbox top) up at rim height
        reach_y = shooter.bbox[1] if shooter else rim.bbox[1]
        if shooter is not None and shooter.keypoints is not None:
            reach_y = min(reach_y, shooter.highest_hand_y())
        dunk = made and rel_d <= ec.dunk_release_rim_dist and reach_y <= rim.bbox[3] + 0.5 * rim.width
        court_xy = shooter.court_xy if shooter is not None else None
        three, dist_m, line_m = None, None, None
        if court_xy is not None:
            hoop, dist_m = template.nearest_hoop(court_xy, self.cfg.court)
            three = template.is_three(court_xy, self.cfg.court, hoop) and not dunk
            line_m = template.three_line_distance(court_xy, self.cfg.court, hoop)
        points = (3 if three else 2) if made else 0
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
            "distance_m": dist_m,
            "three_line_m": line_m,  # + outside / - inside the 3PT line
            "three_close": line_m is not None and not dunk and abs(line_m) < ec.three_close_margin_m,
            "make_frame": make_frame,
            "rim": list(rim.bbox),
            "arc_apex_above_rim_m": apex_above_rim_m,
            "airtime_s": fl.duration,
        }

    def _made(self, frames, fl: Flight, rim: RimObs, zone_hit: int | None) -> tuple[bool, int | None]:
        """Ball crosses the rim's center line downward, horizontally inside the rim, having been
        above the rim shortly before. Looks a bit past the flight end (the catch under the basket
        can start a possession while the ball is still in the net)."""
        if zone_hit is None:
            return False, None
        rx1, ry1, rx2, ry2 = rim.bbox
        cy, w = (ry1 + ry2) / 2, rim.width
        i0 = fl.start + max(0, zone_hit - 2)
        i1 = min(len(frames) - 1, fl.end + int(0.5 * self.fps), i0 + int(self.cfg.events.make_window_s * self.fps))
        seq = [(i, frames[i].ball.xy) for i in range(i0, i1 + 1) if frames[i].ball is not None]
        last_above = None
        for (ia, a), (ib, b) in zip(seq, seq[1:]):
            if a[1] < ry1:
                last_above = ia
            if a[1] <= cy < b[1] and last_above is not None and ia - last_above <= self.fps:
                x = a[0] + (b[0] - a[0]) * (cy - a[1]) / max(b[1] - a[1], 1e-6)
                if rx1 - 0.15 * w <= x <= rx2 + 0.15 * w:
                    return True, frames[ib].idx
        return False, None

    def _pass_geometry(self, frames, s: Segment, nxt: Segment) -> dict:
        a = next((p for p in frames[s.end].players if self.ids.player(p.track_id) == s.player), None)
        b = next((p for p in frames[nxt.start].players if self.ids.player(p.track_id) == nxt.player), None)
        if a is None or b is None or a.court_xy is None or b.court_xy is None:
            return {}
        return {"from_xy": a.court_xy, "to_xy": b.court_xy,
                "distance_m": float(np.hypot(a.court_xy[0] - b.court_xy[0], a.court_xy[1] - b.court_xy[1]))}

    def _annotate_court_positions(self, frames: list[FrameState]) -> None:
        if self.calib is None:
            return
        for f in frames:
            if not f.players:
                continue
            feet = self.calib.image_to_court([p.feet for p in f.players])
            for p, xy in zip(f.players, feet):
                p.court_xy = (float(xy[0]), float(xy[1]))
