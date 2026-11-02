"""Player-tracking accuracy on SportsMOT basketball sequences (MOT17 layout; CC BY-NC 4.0, non-commercial).

  # data/raw/sportsmot/{basketball.txt, val/<seq>/{img1/*.jpg, gt/gt.txt, seqinfo.ini}}
  #   (val.tar and splits_txt/basketball.txt from huggingface MCG-NJU/SportsMOT)
  python src/scripts/eval_tracking.py --split val          # -> results/tracking_sportsmot.json

Each basketball sequence is turned into an mp4 and run through the pipeline's detect + calibrate stages, then
fusion (which drops people off the court: referees on the sideline, the crowd). SportsMOT labels only the
players on the court, so both the raw tracks and the fused ones are scored. Metrics (IoU >= 0.5):
  MOTA  = 1 - (FN + FP + IDSW) / GT boxes
  IDF1  = identity F1 after the best one-to-one GT-id <-> track-id assignment over the whole sequence
          (punishes a player changing id, e.g. after an overlap or leaving and coming back)
  IDSW  = times a GT player's matched track id changes
"stitched" adds identity.stitch (lost tracks joined to the track that picks the player up again) after fusion.
Court placement (how well the court is known in every frame): the share of labelled players whose feet land on
the court (within 1 m of the lines), with one calibration for the clip ("static") vs the court track ("track").
"""
from __future__ import annotations

import argparse
import configparser
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from nextrun_cv import fusion  # noqa: E402
from nextrun_cv.config import Config, CourtSpec  # noqa: E402
from nextrun_cv.identity.stitch import stitch_tracks  # noqa: E402
from nextrun_cv.pipeline import calibrate, detect, load_court, load_frames  # noqa: E402



def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (n,4), b: (m,4) xyxy."""
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda r: (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])  # noqa: E731
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def mot_metrics(gt: dict[int, list], pred: dict[int, list], thr: float = 0.5) -> dict:
    """gt / pred: frame -> [(id, xyxy)]."""
    frames = sorted(set(gt) | set(pred))
    n_gt = sum(len(gt.get(f, [])) for f in frames)
    n_pr = sum(len(pred.get(f, [])) for f in frames)
    tp = fp = fn = idsw = 0
    last = {}  # gt id -> last matched pred id
    pair_frames = defaultdict(int)  # (gt id, pred id) -> frames overlapping at IoU >= thr
    gt_ids, pr_ids = set(), set()
    for f in frames:
        g, p = gt.get(f, []), pred.get(f, [])
        gt_ids |= {i for i, _ in g}
        pr_ids |= {i for i, _ in p}
        m = iou_matrix(np.array([b for _, b in g]).reshape(-1, 4), np.array([b for _, b in p]).reshape(-1, 4))
        for gi, pi in zip(*np.nonzero(m >= thr)):
            pair_frames[(g[gi][0], p[pi][0])] += 1
        # CLEAR-MOT: keep last frame's pairs when still valid, then Hungarian on the rest
        cost = 1 - m
        for gi, (gid, _) in enumerate(g):
            for pi, (pid, _) in enumerate(p):
                if last.get(gid) == pid and m[gi, pi] >= thr:
                    cost[gi, pi] = -1.0
        matched = 0
        if m.size:
            for gi, pi in zip(*linear_sum_assignment(cost)):
                if m[gi, pi] < thr:
                    continue
                matched += 1
                gid, pid = g[gi][0], p[pi][0]
                if gid in last and last[gid] != pid:
                    idsw += 1
                last[gid] = pid
        tp += matched
        fp += len(p) - matched
        fn += len(g) - matched
    # IDF1: one-to-one id assignment maximising frames in agreement
    gl, pl = sorted(gt_ids), sorted(pr_ids)
    w = np.zeros((len(gl), len(pl)))
    gi_, pi_ = {g: i for i, g in enumerate(gl)}, {p: i for i, p in enumerate(pl)}
    for (g, p), c in pair_frames.items():
        w[gi_[g], pi_[p]] = c
    idtp = w[linear_sum_assignment(-w)].sum() if w.size else 0.0
    return {"gt_boxes": n_gt, "pred_boxes": n_pr, "gt_ids": len(gl), "pred_ids": len(pl), "tp": tp, "fp": fp, "fn": fn,
            "idsw": idsw, "mota": 1 - (fn + fp + idsw) / max(n_gt, 1), "idf1": 2 * idtp / max(n_gt + n_pr, 1),
            "recall": tp / max(n_gt, 1), "precision": tp / max(n_pr, 1)}


def load_gt(seq: Path) -> dict[int, list]:
    gt = defaultdict(list)
    for line in (seq / "gt" / "gt.txt").read_text().splitlines():
        f, i, x, y, w, h = map(float, line.split(",")[:6])
        gt[int(f)].append((int(i), (x, y, x + w, y + h)))
    return gt


def to_video(seq: Path, dst: Path) -> None:
    ini = configparser.ConfigParser()
    ini.read(seq / "seqinfo.ini")
    s = ini["Sequence"]
    imgs = sorted((seq / s.get("imDir", "img1")).glob("*.jpg"))
    first = cv2.imread(str(imgs[0]))
    vw = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), float(s.get("frameRate", 25)),
                         (first.shape[1], first.shape[0]))
    for p in imgs:
        vw.write(cv2.imread(str(p)))
    vw.release()


def on_court_share(gt: dict[int, list], court, spec) -> float:
    """Share of labelled players (feet = bottom centre of the box) the court puts on the court (1 m margin)."""
    n = ok = 0
    for f, boxes in gt.items():
        c = court.at(f - 1) if court is not None else None
        n += len(boxes)
        if c is None or not boxes:
            continue
        xy = c.image_to_court([((b[0] + b[2]) / 2, b[3]) for _, b in boxes])
        ok += int(((np.abs(xy[:, 0]) <= spec.length / 2 + 1) & (np.abs(xy[:, 1]) <= spec.width / 2 + 1)).sum())
    return ok / max(n, 1)


def tracks(frames, idx_offset: int = 1) -> dict[int, list]:
    out = defaultdict(list)
    for f in frames:
        out[f.idx + idx_offset] = [(p.track_id, tuple(p.bbox)) for p in f.players if p.track_id is not None]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="val")
    ap.add_argument("--root", default=str(ROOT / "data/raw/sportsmot"))
    ap.add_argument("--work", default=str(ROOT / "results/tracking_sportsmot"))
    ap.add_argument("--device")
    ap.add_argument("--tag", default="", help="suffix for the results file / work dir")
    ap.add_argument("--tracker", help="tracker yaml for moving cameras (all SportsMOT sequences pan)")
    ap.add_argument("--reuse", metavar="WORK_TAG", help="score the saved detections + court of run WORK_TAG (no detect)")
    ap.add_argument("--resume", action="store_true", help="reuse this run's saved detections where they exist")
    ap.add_argument("--set", nargs="*", default=[], metavar="SECTION.KEY=VALUE", help="config overrides")
    a = ap.parse_args()
    root, work = Path(a.root), Path(a.work + a.tag)
    names = set((root / "basketball.txt").read_text().split())
    seqs = sorted(p for p in (root / a.split).iterdir() if p.name in names)
    print(f"{len(seqs)} basketball sequences in {a.split}")
    res = {}
    for seq in seqs:
        out = work / seq.name
        vid = out / "video.mp4"
        if not a.reuse and not vid.exists():
            out.mkdir(parents=True, exist_ok=True)
            to_video(seq, vid)
        cfg = Config()
        cfg.court = CourtSpec.preset("nba")  # SportsMOT basketball is NBA broadcast
        if a.device:
            cfg.models.device = a.device
        if a.tracker:
            cfg.models.tracker_moving_cfg = a.tracker
        for kv in a.set:
            k, v = kv.split("=", 1)
            obj = getattr(cfg, k.split(".")[0])
            key = k.split(".")[1]
            old = getattr(obj, key)
            setattr(obj, key, (v.lower() in ("1", "true")) if isinstance(old, bool) else type(old)(v))
        gt = load_gt(seq)
        if a.reuse or (a.resume and (out / "court_track.json").exists()):
            src = Path(a.work + (a.reuse or a.tag)) / seq.name
            frames = load_frames(src / "tracks.json.gz")
            calib, static = load_court(src, cfg.court), None
        else:
            src = out
            frames = detect(str(vid), str(out), cfg, progress=False)
            scfg = copy.deepcopy(cfg)
            scfg.camera.mode = "static"
            try:
                static = calibrate(str(vid), str(out), scfg)
                static = static if static.conf >= cfg.fusion.min_court_conf else None
            except Exception:
                static = None
            calib = calibrate(str(vid), str(out), cfg)
        raw = mot_metrics(gt, tracks(frames))
        place = {"static": on_court_share(gt, static, cfg.court), "track": on_court_share(gt, calib, cfg.court)}
        rep = fusion.fuse(frames, calib, cfg)
        fused = mot_metrics(gt, tracks(frames)) if rep.get("court") else None
        emb = {int(k): np.asarray(v) for k, v in json.loads((src / "appearance.json").read_text()).items()}
        stitch_tracks(frames, emb, cfg.stitch)
        stitched = mot_metrics(gt, tracks(frames))
        res[seq.name] = {"raw": raw, "fused": fused, "stitched": stitched, "court_conf": rep.get("court_conf"),
                         "on_court": place, "court_frames": rep.get("court_frames"), "moving": calib.moving}
        f = fused or raw
        print(f"{seq.name}: players on court static {place['static']:.2f} track {place['track']:.2f} | raw IDF1 {raw['idf1']:.3f} MOTA {raw['mota']:.3f} IDSW {raw['idsw']} | fused "
              + (f"IDF1 {f['idf1']:.3f} MOTA {f['mota']:.3f} IDSW {f['idsw']}" if fused else "no court")
              + f" | stitched IDF1 {stitched['idf1']:.3f} IDSW {stitched['idsw']} ids {stitched['pred_ids']}", flush=True)
    summary = {}
    for kind in ("raw", "fused", "stitched"):
        rows = [r[kind] for r in res.values() if r[kind]]
        if not rows:
            continue
        s = {k: sum(r[k] for r in rows) for k in ("gt_boxes", "pred_boxes", "tp", "fp", "fn", "idsw", "gt_ids", "pred_ids")}
        s.update(sequences=len(rows), mota=1 - (s["fn"] + s["fp"] + s["idsw"]) / s["gt_boxes"],
                 idf1_mean=float(np.mean([r["idf1"] for r in rows])), recall=s["tp"] / s["gt_boxes"],
                 precision=s["tp"] / max(s["pred_boxes"], 1))
        summary[kind] = s
    summary["on_court"] = {k: float(np.mean([r["on_court"][k] for r in res.values()])) for k in ("static", "track")}
    (ROOT / f"results/tracking_sportsmot{a.tag}.json").write_text(json.dumps({"summary": summary, "sequences": res}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
