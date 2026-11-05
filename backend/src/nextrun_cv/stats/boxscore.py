"""Aggregate events into per-player and per-team box scores."""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from ..events.analyzer import GameAnalysis
from ..identity.tagging import Identities

HEADLINE = ["PTS", "REB", "AST"]  # the stats NextRun tracks first; everything after supports / explains them
COLUMNS = [
    "player", "team", *HEADLINE, "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "2PM", "2PA", "DUNK",
    "OREB", "DREB", "STL", "TOV", "PASS", "DRIB", "TOUCH", "POSS_S", "AIRBALL",
]


def box_score(analysis: GameAnalysis, ids: Identities | None = None) -> pd.DataFrame:
    ids = ids or Identities()
    rows: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    teams: dict[str, str | None] = {}

    for e in analysis.events:
        if e.player is None:
            continue
        r = rows[e.player]
        teams.setdefault(e.player, e.team or ids.player_team.get(e.player))
        if e.type == "shot":
            r["FGA"] += 1
            three = bool(e.data.get("three"))
            r["3PA" if three else "2PA"] += 1
            if e.data.get("airball"):
                r["AIRBALL"] += 1
            if e.data.get("made"):
                r["FGM"] += 1
                r["3PM" if three else "2PM"] += 1
                r["PTS"] += e.data.get("points", 2)
                if e.data.get("dunk"):
                    r["DUNK"] += 1
        elif e.type == "assist":
            r["AST"] += 1
        elif e.type == "rebound":
            r["OREB" if e.data.get("offensive") else "DREB"] += 1
            r["REB"] += 1
        elif e.type == "steal":
            r["STL"] += 1
        elif e.type == "turnover":
            r["TOV"] += 1
        elif e.type == "pass":
            r["PASS"] += 1
        elif e.type == "dribble":
            r["DRIB"] += 1
        elif e.type == "possession_gain":
            r["TOUCH"] += 1
            r["POSS_S"] += e.data.get("duration_s", 0.0)

    for p in ids.player_team:  # tagged players with no events still get a row
        rows[p]
        teams.setdefault(p, ids.player_team.get(p))

    recs = []
    for p, r in rows.items():
        rec = {c: r.get(c, 0) for c in COLUMNS[2:]}
        rec["FG%"] = round(r["FGM"] / r["FGA"], 3) if r["FGA"] else None
        rec["3P%"] = round(r["3PM"] / r["3PA"], 3) if r["3PA"] else None
        rec["POSS_S"] = round(r["POSS_S"], 1)
        recs.append({"player": p, "team": teams.get(p), **rec})
    df = pd.DataFrame(recs, columns=COLUMNS)
    int_cols = [c for c in COLUMNS[2:] if c not in ("FG%", "3P%", "POSS_S")]
    df[int_cols] = df[int_cols].fillna(0).astype(int)
    return df.sort_values(["team", "PTS"], ascending=[True, False], na_position="last").reset_index(drop=True)


def team_totals(df: pd.DataFrame) -> pd.DataFrame:
    num = [c for c in COLUMNS[2:] if c not in ("FG%", "3P%")]
    t = df.groupby(df["team"].fillna("?"))[num].sum().reset_index()
    t["FG%"] = (t["FGM"] / t["FGA"]).where(t["FGA"] > 0).round(3)
    t["3P%"] = (t["3PM"] / t["3PA"]).where(t["3PA"] > 0).round(3)
    return t
