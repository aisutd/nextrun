"""Static charts: shot chart, pass network, possession timeline."""
from __future__ import annotations

from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..config import CourtSpec  # noqa: E402
from ..court import template  # noqa: E402
from ..events.analyzer import GameAnalysis  # noqa: E402


def _court(ax, spec: CourtSpec):
    for pl in template.polylines(spec):
        ax.plot(pl[:, 0], pl[:, 1], color="#555", lw=1)
    for hx, hy in template.hoop_positions(spec):
        ax.add_patch(plt.Circle((hx, hy), 0.23, fill=False, color="#e67e22", lw=2))
    ax.set_aspect("equal")
    ax.set_xlim(-spec.length / 2 - 1, spec.length / 2 + 1)
    ax.set_ylim(spec.width / 2 + 1, -spec.width / 2 - 1)
    ax.axis("off")


def shot_chart(analysis: GameAnalysis, spec: CourtSpec, path: str, player: str | None = None) -> None:
    fig, ax = plt.subplots(figsize=(12, 6.8))
    _court(ax, spec)
    for e in analysis.by_type("shot"):
        if player and e.player != player:
            continue
        xy = e.data.get("shot_xy")
        if xy is None:
            continue
        if e.data["made"]:
            ax.scatter(*xy, s=90, marker="o", facecolors="#2ecc71", edgecolors="k", zorder=3)
        else:
            ax.scatter(*xy, s=90, marker="x", color="#e74c3c", zorder=3)
        ax.annotate(e.player, xy, fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_title(f"Shot chart{' - ' + player if player else ''}  (o made, x missed)")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def pass_network(analysis: GameAnalysis, path: str, spec: CourtSpec | None = None) -> None:
    passes = Counter((e.player, e.data.get("to")) for e in analysis.by_type("pass"))
    pos: dict[str, list] = defaultdict(list)
    for e in analysis.by_type("pass"):
        if e.data.get("from_xy"):
            pos[e.player].append(e.data["from_xy"])
        if e.data.get("to_xy"):
            pos[e.data["to"]].append(e.data["to_xy"])
    players = sorted({p for pair in passes for p in pair if p})
    if not players:
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    if spec is not None and pos:
        _court(ax, spec)
        xy = {p: np.mean(pos[p], axis=0) if pos[p] else np.zeros(2) for p in players}
    else:
        ang = np.linspace(0, 2 * np.pi, len(players), endpoint=False)
        xy = {p: np.array([np.cos(a), np.sin(a)]) for p, a in zip(players, ang)}
        ax.axis("off")
    mx = max(passes.values())
    for (a, b), n in passes.items():
        if a in xy and b in xy:
            ax.annotate("", xy[b], xy[a], arrowprops=dict(arrowstyle="->", lw=1 + 4 * n / mx, color="#3498db", alpha=0.7))
    for p in players:
        ax.scatter(*xy[p], s=400, color="#34495e", zorder=3)
        ax.annotate(p, xy[p], ha="center", va="center", color="w", fontsize=8, zorder=4)
    ax.set_title("Pass network (arrow width = passes)")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def possession_timeline(analysis: GameAnalysis, fps: float, path: str, team_of: dict[str, str] | None = None) -> None:
    team_of = team_of or {}
    players = sorted({s.player for s in analysis.segments})
    if not players:
        return
    fig, ax = plt.subplots(figsize=(14, 0.4 * len(players) + 1.5))
    teams = sorted({t for t in team_of.values()})
    cmap = {t: c for t, c in zip(teams, ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f"])}
    for s in analysis.segments:
        y = players.index(s.player)
        ax.barh(y, (s.end - s.start + 1) / fps, left=s.start / fps, color=cmap.get(team_of.get(s.player), "#95a5a6"))
    for e in analysis.by_type("shot"):
        if e.player in players:
            ax.scatter(e.t, players.index(e.player), marker="*" if e.data["made"] else "x", color="k", zorder=3)
    ax.set_yticks(range(len(players)), players)
    ax.set_xlabel("time (s)")
    ax.set_title("Ball possession (* made shot, x miss)")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
