"""Score pipeline output against hand-labelled ground truth.

Ground truth (eval/labels/<clip>.json):
{
  "fps": 30,
  "events": [
    {"type": "shot", "t": 12.4, "player": "Tushaar", "made": true, "three": false},
    {"type": "pass", "t": 10.1, "player": "Juan", "to": "Tushaar"},
    {"type": "rebound", "t": 20.0, "player": "Juan"},
    {"type": "dribble", "t": 3.2, "player": "Juan"}
  ]
}
Label with any video player that shows timestamps; ±tolerance seconds is allowed when matching.

Usage: python eval/score.py outputs/game1/events.json eval/labels/game1.json [--tol 0.5]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

TYPES = ["shot", "pass", "dribble", "rebound", "assist", "steal", "turnover"]


def match(pred: list[dict], gt: list[dict], tol: float, use_player: bool = True):
    """Greedy one-to-one matching by time within tolerance (same type, optionally same player)."""
    used = set()
    pairs = []
    for g in sorted(gt, key=lambda e: e["t"]):
        best, best_dt = None, tol
        for i, p in enumerate(pred):
            if i in used or p["type"] != g["type"]:
                continue
            if use_player and g.get("player") and p.get("player") != g["player"]:
                continue
            dt = abs(p["t"] - g["t"])
            if dt <= best_dt:
                best, best_dt = i, dt
        if best is not None:
            used.add(best)
            pairs.append((pred[best], g))
    return pairs


def score(pred: list[dict], gt: list[dict], tol: float = 0.5) -> dict:
    out = {}
    for use_player in (False, True):
        key = "with_player" if use_player else "event_only"
        res = {}
        for t in TYPES:
            p = [e for e in pred if e["type"] == t]
            g = [e for e in gt if e["type"] == t]
            if not p and not g:
                continue
            m = match(p, g, tol, use_player)
            prec = len(m) / len(p) if p else None
            rec = len(m) / len(g) if g else None
            res[t] = {"pred": len(p), "gt": len(g), "matched": len(m), "precision": prec, "recall": rec}
            if t == "shot" and m:
                res[t]["make_acc"] = sum(pp["data"]["made"] == gg.get("made") for pp, gg in m if "made" in gg) / max(1, sum("made" in gg for _, gg in m))
                with3 = [(pp, gg) for pp, gg in m if "three" in gg and pp["data"].get("three") is not None]
                if with3:
                    res[t]["three_acc"] = sum(pp["data"]["three"] == gg["three"] for pp, gg in with3) / len(with3)
        out[key] = res
    out["boxscore_abs_error"] = _box_error(pred, gt)
    return out


def _box_error(pred, gt) -> dict:
    def pts(evts, made_key):
        d = defaultdict(int)
        for e in evts:
            if e["type"] == "shot" and made_key(e):
                d[e["player"]] += 3 if (e.get("three") or e.get("data", {}).get("three")) else 2
        return d

    p = pts(pred, lambda e: e["data"]["made"])
    g = pts(gt, lambda e: e.get("made"))
    return {pl: p.get(pl, 0) - g.get(pl, 0) for pl in set(p) | set(g)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pred")
    ap.add_argument("gt")
    ap.add_argument("--tol", type=float, default=0.5)
    a = ap.parse_args()
    pred = json.load(open(a.pred))
    gt = json.load(open(a.gt))["events"]
    print(json.dumps(score(pred, gt, a.tol), indent=2))


if __name__ == "__main__":
    main()
