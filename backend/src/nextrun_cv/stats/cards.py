"""Player cards for the app: per-player points and other stats, a single rating, rank, level and badges, plus each
player's shot log. Built from the box score and the event list of one game."""
from __future__ import annotations

import pandas as pd


def rating(r) -> float:
    """One number for 'how much did this player help': scoring, rebounds, assists and steals count, turnovers and
    missed shots cost."""
    return round(
        r["PTS"] + 1.2 * r["REB"] + 1.5 * r["AST"] + 2.0 * r["STL"] - 1.5 * r["TOV"] + 0.5 * r["FGM"]
        - 0.5 * (r["FGA"] - r["FGM"]) + 1.0 * r["3PM"] + 0.05 * r["TOUCH"], 1)


BADGES = [  # (stat, minimum, label): the leader in each stat wins the badge
    ("PTS", 1, "TOP SCORER"), ("REB", 1, "GLASS CLEANER"), ("AST", 1, "PLAYMAKER"),
    ("STL", 1, "LOCKDOWN"), ("3PM", 1, "SHARPSHOOTER"),
]


def scoring_log(events: list[dict]) -> list[dict]:
    """Every shot in game order with the running team score after it: the app's scoring log. `uncertain` marks the
    ones worth a second look (low confidence, a made basket with nobody credited, a three on the line)."""
    score: dict[str, int] = {}
    log = []
    for e in sorted((e for e in events if e["type"] == "shot"), key=lambda e: (e["t"], e["frame"])):
        d = e["data"]
        made, pts, team = bool(d.get("made")), int(d.get("points") or 0), e.get("team")
        if made and team:
            score[team] = score.get(team, 0) + pts
        conf = d.get("confidence")
        log.append({
            "frame": e["frame"], "t": round(e["t"], 1), "player": e.get("player"), "team": team, "made": made, "points": pts,
            "three": bool(d.get("three")), "reason": d.get("reason") or "", "confidence": conf,
            "manual": bool(d.get("manual")), "recovered": bool(d.get("recovered")),
            "uncertain": (not d.get("manual")) and ((made and conf is not None and conf < 0.8) or (made and not e.get("player")) or bool(d.get("three_close"))),
            "score": dict(score) if made else None,
        })
    return log


def build_summary(bs: pd.DataFrame, events: list[dict], scoring: str = "standard") -> dict:
    log = scoring_log(events)
    if bs.empty:
        return {"teams": [], "players": [], "mvp": None, "log": log, "scoring": scoring, "unassigned_pts": 0}
    df = bs.copy()
    df["RATING"] = df.apply(rating, axis=1)
    active = df[(df[["PTS", "REB", "AST", "STL", "TOV", "FGA", "PASS", "TOUCH"]].sum(axis=1) > 0)]
    df = active if not active.empty else df
    df = df.sort_values("RATING", ascending=False).reset_index(drop=True)
    shots: dict[str, list] = {}
    for e in events:
        if e["type"] == "shot" and e.get("player"):
            shots.setdefault(e["player"], []).append(
                {"t": round(e["t"], 1), "made": bool(e["data"].get("made")), "three": bool(e["data"].get("three")), "points": int(e["data"].get("points", 0))})
    leaders = {}
    for stat, minimum, label in BADGES:
        top = df[stat].max()
        if top >= minimum:
            for name in df.loc[df[stat] == top, "player"]:
                leaders.setdefault(name, []).append(label)
    players = []
    for i, r in df.iterrows():
        d = {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
        d.update(rank=i + 1, xp=int(round(max(0.0, r["RATING"]) * 10)), badges=leaders.get(r["player"], []), shots=shots.get(r["player"], []))
        d["level"] = 1 + d["xp"] // 50
        if i == 0 and r["RATING"] > 0:
            d["badges"] = ["MVP"] + d["badges"]
        players.append(d)
    teams = (df.assign(team=df["team"].fillna("?")).groupby("team")[["PTS", "REB", "AST", "STL", "TOV", "FGM", "FGA", "3PM", "3PA"]].sum().reset_index())
    unassigned = sum(int(e["data"].get("points") or 0) for e in events
                     if e["type"] == "shot" and not e.get("player") and e["data"].get("made"))
    return {"teams": teams.to_dict("records"), "players": players, "mvp": players[0]["player"] if players and players[0]["RATING"] > 0 else None,
            "log": log, "scoring": scoring, "unassigned_pts": unassigned}
