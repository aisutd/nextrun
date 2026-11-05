"""Clip-level box-score accuracy on the rkun0117/basketball-events set (543 NBA broadcast clips, ~7 s each,
4 games from 2015-16; research use only). Each clip lists the play-by-play events that happen in it: shots
(2-pt / 3-pt, make / miss), assists, offensive rebounds and blocks. There are no timestamps inside the clip and
no defensive rebounds, so scoring is per clip: counts of each event, and points.

  # download: data/raw/hf_events/rkun/clips/<game>/{<game>_clipNNN.mp4, <game>_annotations.json}
  python src/scripts/eval_events_clips.py --run --gpus 0 1 --jobs 3   # pipeline on every clip (no render)
  python src/scripts/eval_events_clips.py                              # score -> results/events_clips.json
  python src/scripts/eval_events_clips.py --replay _v3 --tag _v4       # analyze stage only, on _v3's detections

Player attribution is not scored: the labels name jersey colour + number, and the pipeline has no tags here.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / "data/raw/hf_events/rkun/clips"
OUT = ROOT / "results/events_clips"


def gt_clips() -> list[dict]:
    clips = []
    for f in sorted(glob.glob(str(CLIPS / "*/*_annotations.json"))):
        d = json.loads(Path(f).read_text())
        for c in d["clips"]:
            clips.append({"game": d["game_id"], "file": str(Path(f).parent / c["clip_file"]), "events": c["events"]})
    return clips


def run(clips: list[dict], gpus: list[str], jobs: int) -> None:
    def one(i_c):
        i, c = i_c
        out = OUT / Path(c["file"]).stem
        if (out / "events.json").exists():
            return
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpus[i % len(gpus)], "PYTHONPATH": str(ROOT / "src")}
        r = subprocess.run([sys.executable, "-m", "nextrun_cv", "run", c["file"], "-o", str(out), "--court", "nba",
                            "--no-render"], env=env, capture_output=True, text=True)
        (out / "log.txt").parent.mkdir(parents=True, exist_ok=True)
        (out / "log.txt").write_text(r.stdout + r.stderr)
        print(f"{i + 1}/{len(clips)} {out.name}: exit {r.returncode}", flush=True)

    with ThreadPoolExecutor(len(gpus) * jobs) as ex:
        list(ex.map(one, enumerate(clips)))


def _replay_one(args) -> None:
    src, dst, overrides = args
    import logging

    from nextrun_cv.config import Config, CourtSpec
    from nextrun_cv.pipeline import run_analysis

    logging.disable(logging.WARNING)
    cfg = Config()
    cfg.court = CourtSpec.preset("nba")
    for k, v in overrides:
        sect, key = k.split(".")
        obj = getattr(cfg, sect)
        old = getattr(obj, key)
        setattr(obj, key, (v.lower() in ("1", "true")) if isinstance(old, bool) else type(old)(v))
    analysis, *_ = run_analysis(src, cfg)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "events.json").write_text(json.dumps([e.to_dict() for e in analysis.events], indent=2, default=float))


def replay(clips: list[dict], src_tag: str, workers: int, overrides: list[tuple[str, str]] = ()) -> None:
    """Re-run only the analyze stage (events) on another run's detections + court: fast event-logic iteration."""
    sys.path.insert(0, str(ROOT / "src"))
    src = Path(str(ROOT / "results/events_clips") + src_tag)
    jobs = [(src / Path(c["file"]).stem, OUT / Path(c["file"]).stem, list(overrides)) for c in clips]
    with ProcessPoolExecutor(workers) as ex:
        list(ex.map(_replay_one, [j for j in jobs if (j[0] / "tracks.json.gz").exists()]))


def counts_gt(events: list[dict]) -> Counter:
    c = Counter()
    for e in events:
        if e["event"] == "shot":
            three = e["shot_type"].startswith("3")
            made = e["result"] == "make"
            c["shot"] += 1
            c["shot3"] += three
            c["made"] += made
            c["made3"] += made and three
            c["points"] += (3 if three else 2) * made
        elif e["event"] == "rebound":
            c["oreb"] += 1
        else:
            c[e["event"]] += 1
    return c


def counts_pred(events: list[dict]) -> Counter:
    c = Counter()
    for e in events:
        d = e.get("data", {})
        if e["type"] == "shot":
            c["shot"] += 1
            c["shot3"] += bool(d.get("three"))
            c["made"] += bool(d.get("made"))
            c["made3"] += bool(d.get("made")) and bool(d.get("three"))
            c["points"] += int(d.get("points") or 0)
        elif e["type"] == "rebound":
            c["oreb" if d.get("offensive") else "dreb"] += 1
        elif e["type"] in ("assist", "block"):
            c[e["type"]] += 1
    return c


def score(clips: list[dict]) -> dict:
    keys = ["shot", "made", "shot3", "made3", "points", "assist", "oreb"]
    tot_g, tot_p, exact, n = Counter(), Counter(), Counter(), 0
    det = {k: Counter() for k in keys}  # clip-level presence: tp / fp / fn
    made_conf = Counter()  # clips with exactly one GT shot and one predicted shot: (gt made, pred made)
    for c in clips:
        f = OUT / Path(c["file"]).stem / "events.json"
        if not f.exists():
            continue
        n += 1
        g, p = counts_gt(c["events"]), counts_pred(json.loads(f.read_text()))
        tot_g.update(g)
        tot_p.update(p)
        for k in keys:
            exact[k] += g[k] == p[k]
            det[k]["tp" if g[k] and p[k] else "fn" if g[k] else "fp" if p[k] else "tn"] += 1
        if g["shot"] == 1 and p["shot"] == 1:
            made_conf[(bool(g["made"]), bool(p["made"]))] += 1
    res = {"clips": n, "totals_gt": dict(tot_g), "totals_pred": dict(tot_p),
           "exact_count_rate": {k: exact[k] / max(n, 1) for k in keys}, "clip_presence": {}}
    for k in keys:
        d = det[k]
        res["clip_presence"][k] = {**d, "precision": d["tp"] / max(d["tp"] + d["fp"], 1),
                                   "recall": d["tp"] / max(d["tp"] + d["fn"], 1)}
    res["made_given_one_shot"] = {f"gt_{'make' if a else 'miss'}_pred_{'make' if b else 'miss'}": v
                                  for (a, b), v in sorted(made_conf.items())}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--gpus", nargs="+", default=["0", "1"])
    ap.add_argument("--jobs", type=int, default=3, help="pipeline processes per GPU")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--replay", metavar="FROM_TAG", help="analyze stage only, on the detections of run FROM_TAG")
    ap.add_argument("--workers", type=int, default=32, help="processes for --replay")
    ap.add_argument("--set", nargs="*", default=[], metavar="SECTION.KEY=VALUE", help="config overrides for --replay")
    ap.add_argument("--tag", default="", help="suffix for the output dir / results file (compare pipeline versions)")
    a = ap.parse_args()
    global OUT
    OUT = Path(str(OUT) + a.tag)
    clips = gt_clips()[: a.limit]
    if a.run:
        run(clips, a.gpus, a.jobs)
    elif a.replay is not None:
        replay(clips, a.replay, a.workers, [kv.split("=", 1) for kv in a.set])
    res = score(clips)
    (ROOT / f"results/events_clips{a.tag}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
