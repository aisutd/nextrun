"""Model metrics for the app: accuracy from the recorded test-set evaluations in backend/eval/ (see its README),
plus inference speed measured live on the machine running the API.

Per model: precision / recall / F1, mAP@0.5 and mAP@0.5:0.95 (mean AP over IoU thresholds 0.5 to 0.95) where the
evaluation has them, the IoU rule a detection had to meet, and how much the current model cut false positives,
false negatives and lost data compared with the version it replaced.
"""
from __future__ import annotations

import ast
import csv
import json
import re
import statistics
import threading
import time
from pathlib import Path

import numpy as np

from .config import REPO_ROOT, Config

EVAL_DIR = REPO_ROOT / "eval"


# --- small helpers -----------------------------------------------------------------------------------------
def f1(p: float | None, r: float | None) -> float | None:
    if p is None or r is None or p + r == 0:
        return None if p is None or r is None else 0.0
    return 2 * p * r / (p + r)


def change(before: float | None, after: float | None) -> float | None:
    """Relative change after vs before: -0.42 = 42 % fewer."""
    if before is None or after is None or before == 0:
        return None
    return (after - before) / before


def _r(x: float | None, n: int = 3) -> float | None:
    return None if x is None else round(float(x), n)


def _read(name: str) -> str:
    return (EVAL_DIR / name).read_text()


def _weighted(rows: list[dict], key: str, weight: str = "images") -> float | None:
    rows = [r for r in rows if r.get(key) is not None]
    total = sum(r[weight] for r in rows)
    return sum(r[key] * r[weight] for r in rows) / total if total else None


# --- parsers -------------------------------------------------------------------------------------------------
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse_yolo_val(text: str) -> dict:
    """Ultralytics `val` logs, one block per test set: the 'all' row (P, R, mAP50, mAP50-95), the speed line, and
    the per-set summary dict (per-class P / R / mAP50) that follows it."""
    text = _ANSI.sub("", text)
    sets, speeds, block = [], [], {}
    for line in text.splitlines():
        m = re.match(r"\s+all\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", line)
        if m:
            block = {"images": int(m[1]), "instances": int(m[2]), "P": float(m[3]), "R": float(m[4]),
                     "mAP50": float(m[5]), "mAP50_95": float(m[6])}
            continue
        m = re.match(r"Speed: ([\d.]+)ms preprocess, ([\d.]+)ms inference, [\d.]+ms loss, ([\d.]+)ms postprocess", line)
        if m:
            speeds.append({"pre": float(m[1]), "inference": float(m[2]), "post": float(m[3])})
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)\s+(\{.*\})\s*$", line)
        if m and not line.lstrip().startswith("{"):
            per_class = ast.literal_eval(m[2])
            sets.append({"name": m[1], **block, "classes": {k: v for k, v in per_class.items() if isinstance(v, dict)},
                         "images": per_class.get("images", block.get("images"))})
            block = {}
    if not sets:  # only the final json line (older reports)
        last = next((l for l in reversed(text.splitlines()) if l.startswith("{")), None)
        if last:
            for name, v in json.loads(last).items():
                sets.append({"name": name, "images": v["images"], "classes": {k: c for k, c in v.items() if isinstance(c, dict)}})
    return {"sets": sets, "speeds": speeds}


def parse_court_test(text: str) -> list[dict]:
    """eval_court.py report: the json line (found / usable rates and mapping error in feet, per test set)."""
    last = next((l for l in reversed(text.splitlines()) if l.startswith("{")), None)
    if last:
        return [{"name": k, **v} for k, v in json.loads(last).items()]
    rows = []  # older reports: text rows only
    for line in text.splitlines():
        m = re.match(r"(\S+)\s+(\S+)\s+found (\d+)/(\d+)", line)
        if m:
            found, n = int(m[3]), int(m[4])
            rows.append({"name": m[1], "court": m[2], "images": n, "found": found, "found_rate": found / n if n else 0,
                         "good": 0, "good_rate": 0.0})
    return rows


def best_training_row(csv_text: str, kind: str) -> dict:
    """The validation metrics of the epoch Ultralytics kept as best.pt (fitness = 0.1 mAP50 + 0.9 mAP50-95)."""
    rows = [{k.strip(): v for k, v in r.items()} for r in csv.DictReader(csv_text.splitlines())]
    suffix = "(P)" if kind == "pose" else "(B)"

    def g(r, name):
        return float(r[f"metrics/{name}{suffix}"])

    best = max(rows, key=lambda r: 0.1 * g(r, "mAP50") + 0.9 * g(r, "mAP50-95"))
    return {"epoch": int(float(best["epoch"])), "P": g(best, "precision"), "R": g(best, "recall"),
            "mAP50": g(best, "mAP50"), "mAP50_95": g(best, "mAP50-95"), "epochs": len(rows)}


# --- report per model ----------------------------------------------------------------------------------------
def _ball_report() -> dict:
    cur = parse_yolo_val(_read("ball_current_test.txt"))
    base = parse_yolo_val(_read("ball_baseline_test.txt"))
    sets = cur["sets"]
    images = sum(s["images"] for s in sets)
    overall = {k: _weighted(sets, k) for k in ("P", "R", "mAP50", "mAP50_95")}

    def per_class(report, cls):
        rows = [{"images": s["images"], **s["classes"][cls]} for s in report["sets"] if cls in s["classes"]]
        p, r, m = (_weighted(rows, k) for k in ("P", "R", "mAP50"))
        return {"P": p, "R": r, "mAP50": m, "F1": f1(p, r)}

    classes = {c: per_class(cur, c) for c in ("ball", "rim")}
    before = {c: per_class(base, c) for c in ("ball", "rim")}
    speed = cur["speeds"]
    train = best_training_row(_read("ball_current_train.csv"), "detect")
    # our own wide 4K footage (149 sampled frames, check_ball_footage.py), from the team's README on model_merge
    footage = {"frames": 149, "ball_found": 100, "ball_found_before": 65, "rim_found": 149, "rim_found_before": 149}
    return {
        "key": "ball_hoop",
        "name": "Ball + rim detector",
        "weights": "ball_hoop/ball_pseudo.pt (YOLO26l, 1024 px)",
        "dataset": f"{len(sets)} labelled test sets, {images:,} images (Roboflow + Hugging Face), plus 149 frames of our own footage",
        "iou_rule": "A detection counts at IoU ≥ 0.5 (mAP@0.5); mAP@0.5:0.95 averages AP over IoU 0.5 to 0.95.",
        "headline": {"precision": overall["P"], "recall": overall["R"], "f1": f1(overall["P"], overall["R"]),
                     "map50": overall["mAP50"], "map50_95": overall["mAP50_95"]},
        "classes": [{"name": c, "precision": v["P"], "recall": v["R"], "f1": v["F1"], "map50": v["mAP50"],
                     "before": {"precision": before[c]["P"], "recall": before[c]["R"], "map50": before[c]["mAP50"]}}
                    for c, v in classes.items()],
        "validation": {"epoch": train["epoch"], "precision": train["P"], "recall": train["R"], "f1": f1(train["P"], train["R"]),
                       "map50": train["mAP50"], "map50_95": train["mAP50_95"]},
        "improvements": [
            {"label": "Missed balls on our footage", "before": footage["frames"] - footage["ball_found_before"],
             "after": footage["frames"] - footage["ball_found"],
             "change": change(footage["frames"] - footage["ball_found_before"], footage["frames"] - footage["ball_found"]),
             "kind": "false negatives"},
            {"label": "Missed-ball rate, test sets", "before": 1 - before["ball"]["R"], "after": 1 - classes["ball"]["R"],
             "change": change(1 - before["ball"]["R"], 1 - classes["ball"]["R"]), "kind": "false negatives", "ratio": True},
            {"label": "False-ball rate, test sets", "before": 1 - before["ball"]["P"], "after": 1 - classes["ball"]["P"],
             "change": change(1 - before["ball"]["P"], 1 - classes["ball"]["P"]), "kind": "false positives", "ratio": True},
        ],
        "baseline": "original YOLOv8n ball + rim model",
        "gpu_speed": {"device": "NVIDIA RTX 6000 Ada", "inference_ms": statistics.median(s["inference"] for s in speed),
                      "total_ms": statistics.median(s["pre"] + s["inference"] + s["post"] for s in speed)} if speed else None,
        "sets": [{"name": s["name"], "images": s["images"], "precision": s.get("P"), "recall": s.get("R"),
                  "map50": s.get("mAP50"), "map50_95": s.get("mAP50_95")} for s in sets],
    }


def _court_report() -> dict:
    real = parse_court_test(_read("court_current_test.txt"))
    synth = parse_court_test(_read("court_current_synth_test.txt"))
    hand = parse_court_test(_read("court_current_handheld_test.txt"))
    base = {r["name"]: r for r in parse_court_test(_read("court_baseline_test.txt"))}
    train = best_training_row(_read("court_current_train.csv"), "pose")
    box = best_training_row(_read("court_current_train.csv"), "detect")

    def rate(rows, key):
        n = sum(r["images"] for r in rows)
        return sum(r[key] for r in rows) / n if n else None

    real_imgs = sum(r["images"] for r in real)
    usable, found = rate(real, "good"), rate(real, "found")
    lost_before = sum(r["images"] - base[r["name"]]["found"] for r in real if r["name"] in base)
    lost_after = sum(r["images"] - r["found"] for r in real if r["name"] in base)
    n_shared = sum(r["images"] for r in real if r["name"] in base)
    return {
        "key": "court",
        "name": "Court keypoint model",
        "weights": "court/court_synth.pt (YOLO26m-pose, 24 keypoints, 1280 px)",
        "dataset": f"{real_imgs} real test frames (NBA broadcast, drone, outdoor, indoor), {sum(r['images'] for r in synth)} "
                   f"synthetic camera views, {sum(r['images'] for r in hand)} handheld phone frames",
        "iou_rule": "Keypoints are scored with OKS (keypoint IoU) for mAP; on the test frames a court counts as "
                    "usable when its median mapping error is ≤ 3 ft.",
        "headline": {"precision": train["P"], "recall": train["R"], "f1": f1(train["P"], train["R"]),
                     "map50": train["mAP50"], "map50_95": train["mAP50_95"]},
        "headline_note": f"Keypoint precision / recall / mAP on the validation split (best epoch {train['epoch']}); "
                         f"box mAP@0.5:0.95 {box['mAP50_95']:.3f}.",
        "court": {"found_rate": found, "usable_rate": usable,
                  "median_error_ft": statistics.median(r["err_ft_median"] for r in real if r.get("err_ft_median") is not None),
                  "synthetic_usable_rate": rate(synth, "good"), "handheld_usable_rate": rate(hand, "good")},
        "improvements": [
            {"label": "Test frames with no court found", "before": lost_before, "after": lost_after,
             "change": change(lost_before, lost_after), "kind": "false negatives / data loss", "of": n_shared},
        ],
        "baseline": "original YOLO11s court model",
        "sets": [{"name": r["name"], "images": r["images"], "found_rate": r["found_rate"], "usable_rate": r.get("good_rate"),
                  "median_error_ft": r.get("err_ft_median")} for r in real + synth + hand],
    }


def _players_report() -> dict:
    cur = json.loads(_read("tracking_current.json"))["summary"]
    base = json.loads(_read("tracking_baseline.json"))["summary"]["raw"]
    now = cur["stitched"]
    det = cur["fused"]  # detection after court fusion (stitching only relabels ids)
    rows = [("False positives (extra boxes)", "fp", "false positives"),
            ("False negatives (missed players)", "fn", "false negatives"),
            ("ID switches", "idsw", "tracking errors"),
            ("Track ids for 150 real players", "pred_ids", "fragmented tracks")]
    return {
        "key": "players",
        "name": "Player detection + tracking",
        "weights": "players/yolo26m-pose.pt (stock YOLO26m-pose, 17 body keypoints) + BoT-SORT",
        "dataset": f"SportsMOT basketball val: {now['sequences']} sequences, {now['gt_boxes']:,} labelled player boxes, "
                   f"{now['gt_ids']} players",
        "iou_rule": "A predicted box matches a labelled player at IoU ≥ 0.5.",
        "headline": {"precision": det["precision"], "recall": det["recall"], "f1": f1(det["precision"], det["recall"]),
                     "map50": None, "map50_95": None},
        "headline_note": "Stock COCO model, not fine-tuned, so there is no mAP on our data; precision / recall are "
                         "box matches on SportsMOT.",
        "tracking": {"mota": now["mota"], "idf1": now["idf1_mean"], "id_switches": now["idsw"],
                     "track_ids": now["pred_ids"], "true_ids": now["gt_ids"],
                     "tp": det["tp"], "fp": det["fp"], "fn": det["fn"]},
        "improvements": [{"label": label, "before": base[k], "after": (now if k in ("idsw", "pred_ids") else det)[k],
                          "change": change(base[k], (now if k in ("idsw", "pred_ids") else det)[k]), "kind": kind}
                         for label, k, kind in rows],
        "baseline": "first version (raw tracker, no court fusion)",
    }


def _events_report() -> dict:
    cur = json.loads(_read("events_current.json"))
    base = json.loads(_read("events_baseline.json"))
    names = {"shot": "Shot", "made": "Made shot", "shot3": "3PT attempt", "made3": "Made 3", "assist": "Assist",
             "oreb": "Offensive rebound"}
    events = []
    for k, label in names.items():
        c, b = cur["clip_presence"].get(k), base["clip_presence"].get(k)
        if not c:
            continue
        events.append({"name": label, "precision": c["precision"], "recall": c["recall"], "f1": f1(c["precision"], c["recall"]),
                       "fp": c.get("fp", 0), "fn": c.get("fn", 0), "exact_count": cur["exact_count_rate"].get(k),
                       "before": {"precision": b["precision"], "recall": b["recall"], "fp": b.get("fp", 0), "fn": b.get("fn", 0)} if b else None})
    tot = lambda d, key: sum(d["clip_presence"][k].get(key, 0) for k in names if k in d["clip_presence"])
    tp, fp, fn = tot(cur, "tp"), tot(cur, "fp"), tot(cur, "fn")
    return {
        "key": "events",
        "name": "Game events (end to end)",
        "weights": "all models together: shots, makes, 3s, assists, rebounds",
        "dataset": f"{cur['clips']} labelled NBA clips",
        "iou_rule": "Scored per clip: an event counts when the clip has it in both the labels and the prediction.",
        "headline": {"precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1),
                     "f1": f1(tp / max(tp + fp, 1), tp / max(tp + fn, 1)), "map50": None, "map50_95": None},
        "headline_note": "Pooled over all event types.",
        "events": events,
        "improvements": [
            {"label": "Missed events (false negatives)", "before": tot(base, "fn"), "after": fn,
             "change": change(tot(base, "fn"), fn), "kind": "false negatives"},
            {"label": "Wrong events (false positives)", "before": tot(base, "fp"), "after": fp,
             "change": change(tot(base, "fp"), fp), "kind": "false positives"},
        ],
        "baseline": "first pipeline version",
    }


def _clean(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def report() -> dict:
    """Accuracy for every model, from backend/eval/."""
    return _clean({"models": [_players_report(), _ball_report(), _court_report(), _events_report()],
                   "source": "backend/eval (test-set runs from the model_merge branch)"})


# --- live inference benchmark ---------------------------------------------------------------------------------
_bench: dict = {"result": None, "running": False, "error": None}
_bench_lock = threading.Lock()


def _sample_frame(data_dir: Path) -> tuple[np.ndarray, str]:
    import cv2

    def uploaded(v: Path) -> bool:  # prefer real game footage over low-res phone live sessions
        try:
            return not json.loads((v.parent / "status.json").read_text()).get("name", "").startswith("live-")
        except Exception:  # noqa: BLE001
            return False

    videos = sorted(data_dir.glob("*/video.mp4"), key=lambda p: (uploaded(p), p.stat().st_mtime), reverse=True)
    for v in videos[:5]:
        cap = cv2.VideoCapture(str(v))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
        ok, img = cap.read()
        cap.release()
        if ok:
            return img, f"a frame from game {v.parent.name}"
    return np.full((1080, 1920, 3), 90, np.uint8), "a blank 1080p frame (no game videos yet)"


def run_benchmark(data_dir: Path, runs: int = 10) -> dict:
    """Time each active model on one real frame at the sizes the pipeline uses (after 2 warm-up runs)."""
    from ultralytics import YOLO

    from .api import LIVE_IMGSZ, MAX_IMGSZ, PLAYER_IMGSZ, _best_device

    cfg = Config()
    device = _best_device()
    img, frame_src = _sample_frame(data_dir)
    models = [("players", "Player detection + pose", cfg.models.player_weights, [PLAYER_IMGSZ, LIVE_IMGSZ], {"classes": [0]}),
              ("ball_hoop", "Ball + rim detector", cfg.models.ball_hoop_weights, [MAX_IMGSZ, LIVE_IMGSZ], {}),
              ("court", "Court keypoints", cfg.models.court_keypoint_weights, [1280], {})]
    out = []
    for key, name, weights, sizes, kw in models:
        model = YOLO(weights)
        for imgsz in sizes:
            for _ in range(2):
                model.predict(img, imgsz=imgsz, device=device, verbose=False, **kw)
            ms = []
            for _ in range(runs):
                t = time.perf_counter()
                model.predict(img, imgsz=imgsz, device=device, verbose=False, **kw)
                ms.append((time.perf_counter() - t) * 1000)
            ms.sort()
            out.append({"key": key, "name": name, "imgsz": imgsz, "use": "upload" if imgsz != LIVE_IMGSZ else "live",
                        "mean_ms": statistics.mean(ms), "p50_ms": ms[len(ms) // 2],
                        "p95_ms": ms[min(len(ms) - 1, int(round(0.95 * (len(ms) - 1))))],
                        "fps": 1000 / statistics.mean(ms)})
    live = [r for r in out if r["use"] == "live" or r["key"] == "court"]
    return _clean({"device": device or "cpu", "frame": frame_src, "frame_size": [int(img.shape[1]), int(img.shape[0])],
                   "runs": runs, "models": out, "measured_at": time.strftime("%Y-%m-%d %H:%M"),
                   "live_frame_ms": sum(r["p50_ms"] for r in live if r["key"] != "court")})


def benchmark_state() -> dict:
    return {k: _bench[k] for k in ("result", "running", "error")}


def start_benchmark(data_dir: Path, lock: threading.Lock) -> dict:
    """Run the benchmark in the background (model loading + timing takes a while); poll benchmark_state()."""
    with _bench_lock:
        if _bench["running"]:
            return benchmark_state()
        _bench.update(running=True, error=None)

    def work():
        try:
            with lock:  # do not compete with a live session or upload for the GPU while timing
                _bench["result"] = run_benchmark(data_dir)
        except Exception as e:  # noqa: BLE001
            _bench["error"] = str(e)
        finally:
            _bench["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return benchmark_state()
