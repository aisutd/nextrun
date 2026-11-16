"""Unattended model search: train candidates on both GPUs, score them, refine the best, install the winners.

  setsid nohup .venv-linux/bin/python -u src/scripts/autotrain.py > results/autotrain/autotrain.log 2>&1 &

Safe to stop and start again: finished runs and scores are kept, interrupted runs continue from last.pt, and a
training run already in progress (started by hand or by after_transfer.sh) is adopted rather than restarted.

1. Candidates (CANDIDATES) run whenever a GPU has room (at most 2 runs per GPU).
2. Each finished run is scored on the test split (eval_court.py / eval_ball_rim.py; ball models also on our own
   footage with check_ball_footage.py), same as the active models (weights/active.json).
3. Refinement: the best run per task is trained again from its own weights at a higher resolution, then with a
   longer low-LR polish; a round is kept only if it beats its parent. Up to MAX_REFINE rounds per task.
4. Install rules (HANDOFF.md step 5) pick the winner per task; it's saved as weights/<kind>/<run>.pt and made
   active in weights/active.json, the full pipeline runs on the outdoor clip, and results/autotrain/SUMMARY.md is written.
Nothing is committed or pushed.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv-linux" / "bin" / "python")
OUT = REPO / "results" / "autotrain"
STATE = OUT / "state.json"
RUNS = REPO / "results" / "runs"
DATA = {"court": "data/court24", "ball": "data/ball_rim"}
sys.path.insert(0, str(REPO / "src"))
from nextrun_cv.config import active_weights, install_weights  # noqa: E402

KIND = {"court": "court", "ball": "ball_hoop"}  # task -> weights/ folder
INSTALLED = {t: Path(active_weights(k)) for t, k in KIND.items()}  # the active models when autotrain starts
FOOTAGE = ["data/raw/trackid3x3/videos/outdoor/IMG_0105.MOV", "data/raw/trackid3x3/videos/outdoor/IMG_0110.MOV",
           "data/raw/trackid3x3/videos/indoor/basket_S3T2_pre.mp4", "data/raw/trackid3x3/videos/indoor/basket_S5T4_post.mp4",
           "data/raw/trackid3x3/videos/drone/1-1.mov"]
MIN_TEST_IMAGES = 5     # court test sources smaller than this are reported but don't decide anything
MAX_REFINE = 2
# everything must be scored and installed by FINAL_AT: new runs get a time budget that ends by STOP_LAUNCH_AT
# (train.py --hours fits the LR schedule to it), nothing starts after it, and at FINAL_AT the winners are installed
STOP_LAUNCH_AT = datetime(2026, 10, 29, 6, 45)
FINAL_AT = datetime(2026, 10, 29, 7, 30)
MIN_RUN_H = 1.0         # don't start a run that would get less than this
COURT_CAP_FT = 30.0     # a court that far off is simply wrong: rank it as wrong, not by how wrong
MAX_PER_GPU = 3         # slots: a half-GPU run takes 1, a whole-GPU run 2 (a 48 GB GPU fits a whole + a half run)
MIN_FREE_GB = 18
POLL_S = 60
LAUNCH_GAP_S = 300      # let a new run size its batch before another starts on the same GPU

# name: (task, start weights, imgsz, epochs)
CANDIDATES = {
    "court_yolo26m": ("court", "yolo26m-pose.pt", 1280, 200),
    "ball_yolo26m": ("ball", "yolo26m.pt", 1024, 120),
    "court_finetune": ("court", "weights/court/archive/court_yolo11s_original.pt", 1280, 100),
    "ball_yolo26s": ("ball", "yolo26s.pt", 1024, 80),
    "court_yolo26l": ("court", "yolo26l-pose.pt", 1280, 200),
    "ball_yolo26l": ("ball", "yolo26l.pt", 1024, 80),
    "court_yolo26m_aug": ("court", "yolo26m-pose.pt", 1280, 200),
    # court_yolo26m fine-tuned with synthetic drone / ground-level / raised views (src/scripts/synth_court.py)
    "court_synth": ("court", "weights/court/court_yolo26m.pt", 1280, 80),
    # ball_yolo26l fine-tuned with pseudo-labelled frames of our own footage (src/scripts/pseudo_label_ball.py)
    "ball_pseudo": ("ball", "weights/ball_hoop/ball_yolo26l.pt", 1024, 40),
}
# extra train.py args per candidate. court_yolo26m_aug: harder camera warps, aimed at the unseen drone viewpoint
HARD_WARPS = ["--aug", "perspective=0.0015", "--aug", "degrees=10", "--aug", "scale=0.7"]
EXTRA = {"court_yolo26m_aug": HARD_WARPS, "court_synth": ["--lr0", "0.002", *HARD_WARPS], "ball_pseudo": ["--lr0", "0.002"]}
DATA_OF = {"court_synth": "data/court24s", "ball_pseudo": "data/ball_rim_pl"}  # candidates trained on another set than DATA[task]
SYNTH_TEST = "data/court_synth_test"        # held-out synthetic views: reported, not used by the install rule
HANDHELD_TEST = "data/court_sportcenter"    # real moving phones at an amateur game (build_sportcenter.py): reported


def log(msg: str) -> None:
    print(f"[{time.strftime('%F %T')}] {msg}", flush=True)


def load_state() -> dict:
    s = json.loads(STATE.read_text()) if STATE.exists() else {"jobs": {}, "refine": {"court": 0, "ball": 0}, "baseline": {}, "finalized": False}
    for n, (t, m, i, e) in CANDIDATES.items():  # candidates added since the state was written are queued too
        if n not in s["jobs"]:
            s["jobs"][n] = {"task": t, "model": m, "imgsz": i, "epochs": e, "status": "queued", **({"extra": EXTRA[n]} if n in EXTRA else {}),
                            **({"data": DATA_OF[n]} if n in DATA_OF else {})}
    return s


def save_state(s: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1))
    tmp.replace(STATE)


def run_dir(name: str, task: str) -> Path:
    return RUNS / task / name


def train_finished(name: str, task: str) -> bool:
    """Ultralytics strips the optimizer and sets epoch=-1 in last.pt when a run completes (or stops early)."""
    last = run_dir(name, task) / "weights" / "last.pt"
    if not last.exists():
        return False
    import torch
    return torch.load(last, map_location="cpu", weights_only=False).get("epoch", 0) == -1


def sec_per_epoch(name: str, task: str) -> float | None:
    """Mean wall time per epoch of a run so far (results.csv 'time' is cumulative seconds)."""
    try:
        rows = (run_dir(name, task) / "results.csv").read_text().strip().splitlines()[1:]
        return float(rows[-1].split(",")[1]) / len(rows)
    except (OSError, IndexError, ValueError, ZeroDivisionError):
        return None


def running_pid(name: str) -> int | None:
    """The main train.py process for this run, whoever started it (lowest pid: data-loader workers come later)."""
    for p in sorted((p for p in Path("/proc").iterdir() if p.name.isdigit()), key=lambda p: int(p.name)):
        if p.name.isdigit():
            try:
                cmd = (p / "cmdline").read_bytes().split(b"\0")
            except OSError:
                continue
            if b"src/scripts/train.py" in cmd and b"--name" in cmd and cmd[cmd.index(b"--name") + 1].decode() == name:
                return int(p.name)
    return None


def gpu_free_gb() -> list[float]:
    out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], text=True)
    return [int(x) / 1024 for x in out.split()]


def json_tail(text: str) -> dict:
    for line in reversed(text.splitlines()):
        if line.startswith("{"):
            return json.loads(line.replace("NaN", "null"))
    raise ValueError("no JSON report in output")


# --- scoring ----------------------------------------------------------------------------------------------
def score_court(weights: str, device: str, tag: str, data: str = DATA["court"]) -> dict:
    p = subprocess.run([PY, "src/scripts/eval_court.py", "--data", data, "--split", "test", "--device", device,
                        "--weights", weights], cwd=REPO, capture_output=True, text=True)
    (REPO / "results" / f"{tag}_test.txt").write_text(p.stdout + p.stderr)
    return json_tail(p.stdout)


def score_ball(weights: str, device: str, tag: str) -> dict:
    p = subprocess.run([PY, "src/scripts/eval_ball_rim.py", "--data", DATA["ball"], "--split", "test", "--device", device,
                        "--weights", weights], cwd=REPO, capture_output=True, text=True)
    (REPO / "results" / f"{tag}_test.txt").write_text(p.stdout + p.stderr)
    rep = {"test": json_tail(p.stdout)}
    vids = [v for v in FOOTAGE if (REPO / v).exists()]
    if vids:
        f = subprocess.run([PY, "src/scripts/check_ball_footage.py", *vids, "--weights", weights, "--frames", "30"],
                           cwd=REPO, capture_output=True, text=True,  # no --device option: pin it to the same device
                           env={**os.environ, "CUDA_VISIBLE_DEVICES": "" if device == "cpu" else device})
        rep["footage"] = json_tail(f.stdout)[weights]
    return rep


def court_sources(rep: dict) -> dict:
    return {k: v for k, v in rep.items() if v["images"] >= MIN_TEST_IMAGES}


def court_summary(rep: dict) -> dict:
    src = court_sources(rep)
    med = [v["err_ft_median"] if v["err_ft_median"] is not None else 999.0 for v in src.values()]
    return {"mean_median_ft": round(sum(med) / len(med), 2), "min_found": min(v["found_rate"] for v in src.values()),
            "mean_capped_ft": round(sum(min(m, COURT_CAP_FT) for m in med) / len(med), 2),
            "usable": {k: v["good_rate"] for k, v in src.items()}}


def court_beats(cand: dict, base: dict) -> bool:
    """HANDOFF.md rule: on every test source, found rate >= current - 2 % and median error <= current.
    "Found" counts usable courts only (per-image median error <= 3 ft): the current model "finds" half the drone
    frames but tens of feet off, and matching that would reward wrong courts. For the same reason the median
    error is only compared where the current model is usable on >= 10 % of the images."""
    for k, b in court_sources(base).items():
        c = cand.get(k)
        if c is None or c["good_rate"] < b["good_rate"] - 0.02:
            return False
        # median error only where the current model works (else its "error" is that of a wrong court)
        if b["good_rate"] >= 0.1 and (c["err_ft_median"] is None or c["err_ft_median"] > b["err_ft_median"]):
            return False
    return True


def ball_summary(rep: dict) -> dict:
    t = rep["test"]
    ball = [v.get("ball", {}).get("mAP50", 0.0) for v in t.values()]
    rim = [v["rim"]["mAP50"] for v in t.values() if "rim" in v]
    s = {"ball_map50": round(sum(ball) / len(ball), 3), "rim_map50": round(sum(rim) / len(rim), 3) if rim else 0.0}
    if "footage" in rep:
        fr = rep["footage"]
        s.update(footage_ball=f"{fr['ball_found']}/{fr['frames']}", footage_rim=f"{fr['rim_found']}/{fr['frames']}",
                 footage_ball_rate=fr["ball_found"] / max(fr["frames"], 1), footage_rim_rate=fr["rim_found"] / max(fr["frames"], 1))
    return s


def ball_beats(cand: dict, base: dict) -> bool:
    """HANDOFF.md rule: ball mAP50 up, rim mAP50 down by at most 0.01, ball/rim found in as many footage frames."""
    ok = cand["ball_map50"] > base["ball_map50"] and cand["rim_map50"] >= base["rim_map50"] - 0.01
    if "footage_ball_rate" in base:
        ok = ok and cand.get("footage_ball_rate", 0) >= base["footage_ball_rate"] and cand.get("footage_rim_rate", 0) >= base["footage_rim_rate"]
    return ok


def rank_key(task: str, summ: dict) -> float:
    """Lower is better."""
    if task == "court":  # unusable courts cost like the capped error
        return summ["mean_capped_ft"] + COURT_CAP_FT * (1 - sum(summ["usable"].values()) / len(summ["usable"]))
    return -(summ["ball_map50"] + 0.5 * summ.get("footage_ball_rate", 0.0))


def score(task: str, weights: str, device: str, tag: str) -> dict:
    # GPUs full of training runs can make scoring run out of memory: try the other GPU, then the CPU
    for dev in dict.fromkeys([device, "0" if device == "1" else "1", "cpu"]):
        try:
            rep = score_court(weights, dev, tag) if task == "court" else score_ball(weights, dev, tag)
            break
        except ValueError:
            log(f"scoring {tag} on device {dev} failed (see results/{tag}_test.txt), retrying")
    else:
        raise ValueError(f"scoring {tag} failed on every device")
    out = {"report": rep, "summary": court_summary(rep) if task == "court" else ball_summary(rep)}
    if task == "court" and (REPO / SYNTH_TEST).exists():
        try:
            out["synth"] = synth_summary(score_court(weights, dev, f"{tag}_synth", SYNTH_TEST))
        except ValueError:
            pass
    if task == "court" and (REPO / HANDHELD_TEST).exists():
        try:
            r = score_court(weights, dev, f"{tag}_handheld", HANDHELD_TEST)["sportcenter"]
            out["handheld"] = {"usable": r["good_rate"], "found": r["found_rate"], "median_ft": r["err_ft_median"]}
            # the ranking (not the install rule) counts the real handheld test like another test source
            summ, k = out["summary"], len(out["summary"]["usable"])
            med = r["err_ft_median"] if r["err_ft_median"] is not None else 999.0
            summ["mean_capped_ft"] = round((summ["mean_capped_ft"] * k + min(med, COURT_CAP_FT)) / (k + 1), 2)
            summ["usable"]["handheld_sportcenter"] = r["good_rate"]
        except (ValueError, KeyError):
            pass
    return out


def synth_summary(rep: dict) -> dict:
    """Usable rate per camera kind on the synthetic test views (sources end in _ground / _raised / _drone)."""
    by: dict[str, list[int]] = {}
    for k, v in rep.items():
        g = by.setdefault(k.rsplit("_", 1)[1], [0, 0])
        g[0] += v["good"]
        g[1] += v["images"]
    return {k: round(a / b, 3) for k, (a, b) in sorted(by.items())}


# --- jobs -------------------------------------------------------------------------------------------------
def launch(name: str, job: dict, gpu: int, shared: bool) -> int:
    rd = run_dir(name, job["task"])
    cmd = [PY, "src/scripts/train.py", job["task"], "--name", name, "--device", str(gpu), "--no-install"]
    if (rd / "weights" / "last.pt").exists():
        cmd.append("--resume")
    else:
        cmd += ["--data", f"{job.get('data', DATA[job['task']])}/data.yaml", "--model", job["model"], "--imgsz", str(job["imgsz"]),
                "--epochs", str(job["epochs"]), "--batch", "0.8" if shared else "0.45", "--workers", "12", "--cache", "ram"]
        cmd += job.get("extra", [])
        hours = (STOP_LAUNCH_AT - datetime.now()).total_seconds() / 3600
        if hours < job.get("est_hours", 99):  # fit the LR schedule to the time that's left
            cmd += ["--hours", f"{hours:.2f}"]
    logf = open(OUT / f"{name}.log", "a")
    p = subprocess.Popen(cmd, cwd=REPO, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    log(f"started {name} on GPU {gpu}: {' '.join(cmd[2:])}")
    return p.pid


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # reap our own children so they don't linger as zombies
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    try:
        return "zombie" not in Path(f"/proc/{pid}/status").read_text().lower()
    except OSError:
        return False


def gpu_of(pid: int) -> int | None:
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        return int(cmd[cmd.index(b"--device") + 1])
    except (OSError, ValueError, IndexError):
        return None


def slots_of(pid: int) -> int:
    """GPU share a run holds: 2 (whole GPU) if it sized its batch for most of the memory, else 1.
    Free memory alone can't tell: validation empties the CUDA cache, so a busy GPU briefly looks empty."""
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        batch = float(cmd[cmd.index(b"--batch") + 1]) if b"--batch" in cmd else 0.45  # --resume keeps its batch
    except (OSError, ValueError, IndexError):
        return 1
    return 2 if batch >= 0.6 or batch == -1 else 1


def refine(s: dict, task: str) -> None:
    """Queue the next refinement round for a task once nothing for it is queued and no refinement is running
    (other candidates may still be training: waiting for all of them would leave no time to refine)."""
    jobs = s["jobs"]
    if any(j["task"] == task and (j["status"] == "queued" or (j["status"] == "running" and j.get("parent")))
           for j in jobs.values()):
        return
    if s["refine"][task] >= MAX_REFINE:
        return
    scored = {n: j for n, j in jobs.items() if j["task"] == task and j["status"] == "scored"}
    if not scored:
        return
    best = min(scored, key=lambda n: rank_key(task, scored[n]["summary"]))
    parent = jobs[best]
    if parent.get("parent") and rank_key(task, parent["summary"]) >= rank_key(task, jobs[parent["parent"]]["summary"]):
        s["refine"][task] = MAX_REFINE  # last refinement didn't help: stop
        log(f"{task}: refinement stopped, {best} did not beat {parent['parent']}")
        return
    r = s["refine"][task] = s["refine"][task] + 1
    weights = str(run_dir(best, task) / "weights" / "best.pt")
    if r == 1:  # same model, from its own weights, at a higher resolution
        imgsz = parent["imgsz"] + 256
        new = {"task": task, "model": weights, "imgsz": imgsz, "epochs": 80, "status": "queued", "parent": best}
        name = f"{best}_hires{imgsz}"
        spe = sec_per_epoch(best, task)
        if spe:  # pixels grow with imgsz^2
            new["est_hours"] = round(spe * (imgsz / parent["imgsz"]) ** 2 * 80 / 3600, 2)
    else:  # long low-LR polish at the best resolution
        new = {"task": task, "model": weights, "imgsz": parent["imgsz"], "epochs": 60, "status": "queued", "parent": best,
               "extra": ["--lr0", "0.001"]}
        name = f"{best}_polish"
        spe = sec_per_epoch(best, task)
        if spe:
            new["est_hours"] = round(spe * 60 / 3600, 2)
    jobs[name] = new
    log(f"{task}: refinement round {r}: {name} (from {best}, {rank_key(task, parent['summary']):.3f})")


def finalize(s: dict) -> None:
    lines = ["# Autotrain summary", "", f"Generated {time.strftime('%F %T')}. Scores are on the test splits; "
             "court error is in feet (lower is better), ball/rim are mAP50 (higher is better).", ""]
    for task in ("court", "ball"):
        base = s["baseline"][task]
        scored = {n: j for n, j in s["jobs"].items() if j["task"] == task and j["status"] == "scored"}
        passing = [n for n in scored if (court_beats(scored[n]["report"], base["report"]) if task == "court"
                                         else ball_beats(scored[n]["summary"], base["summary"]))]
        winner = min(passing, key=lambda n: rank_key(task, scored[n]["summary"])) if passing else None
        lines += [f"## {task}", "", f"- current model: `{base['summary']}`"]
        for n in sorted(scored, key=lambda n: rank_key(task, scored[n]["summary"])):
            synth = f" synthetic views usable: `{scored[n]['synth']}`" if "synth" in scored[n] else ""
            synth += f" handheld (SportCenter): `{scored[n]['handheld']}`" if "handheld" in scored[n] else ""
            lines.append(f"- {n}{' **(installed)**' if n == winner else ''}{' (passes install rule)' if n in passing else ''}: `{scored[n]['summary']}`{synth}")
        for n, j in s["jobs"].items():
            if j["task"] == task and j["status"] == "failed":
                lines.append(f"- {n}: FAILED (see results/autotrain/{n}.log)")
        if winner:
            dst = install_weights(KIND[task], run_dir(winner, task) / "weights" / "best.pt", winner)
            lines.append(f"\nInstalled {winner} -> {dst.relative_to(REPO)} (active in weights/active.json; "
                         f"previous: {INSTALLED[task].relative_to(REPO)}).")
            log(f"{task}: installed {winner}")
        else:
            lines.append("\nNo candidate passed the install rule; current model kept.")
        lines.append("")
    clip = REPO / "data" / "videos" / "outdoor_0025_0045.mp4"
    if clip.exists():
        p = subprocess.run([PY, "-m", "nextrun_cv", "run", str(clip), "-o", "results/games/outdoor", "--venue",
                            "trackid3x3_outdoor", "--device", "0"], cwd=REPO, capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": str(REPO / "src")})
        (OUT / "pipeline_outdoor.log").write_text(p.stdout + p.stderr)
        lines += ["## Full pipeline", "", f"`nextrun_cv run` on {clip.name}: exit {p.returncode}, output in results/games/outdoor, "
                  "log in results/autotrain/pipeline_outdoor.log.", ""]
    (OUT / "SUMMARY.md").write_text("\n".join(lines))
    s["finalized"] = True
    log("finalized: results/autotrain/SUMMARY.md")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = load_state()
    pids: dict[str, int] = {}
    last_launch: dict[int, float] = {}
    log("autotrain started")
    while not s["finalized"]:
        # baselines: the active models (once; GPU 1 has the most room early on)
        for task in ("court", "ball"):
            if task not in s["baseline"]:
                log(f"scoring current {task} model")
                s["baseline"][task] = score(task, str(INSTALLED[task]), "1", f"{task}_current")
                log(f"current {task}: {s['baseline'][task]['summary']}")
                save_state(s)

        # ball footage counts from before static spots were excluded: score again (a minute or two per model)
        if "ball_found_all" not in s["baseline"]["ball"]["report"].get("footage", {"ball_found_all": 0}):
            log("rescoring current ball model (static spots excluded on footage)")
            s["baseline"]["ball"] = score("ball", str(INSTALLED["ball"]), "0", "ball_current")
            log(f"current ball: {s['baseline']['ball']['summary']}")
            save_state(s)
        for name, job in s["jobs"].items():
            if job["task"] == "ball" and job["status"] == "scored" and "ball_found_all" not in job["report"].get("footage", {"ball_found_all": 0}):
                log(f"rescoring {name} (static spots excluded on footage)")
                job.update(score("ball", str(run_dir(name, "ball") / "weights" / "best.pt"), "0", name))
                log(f"{name}: {job['summary']}")
                save_state(s)

        # court reports from before the usable-rate metric: score again (seconds per model)
        if "good_rate" not in next(iter(s["baseline"]["court"]["report"].values())):
            log("rescoring current court model (usable rate)")
            s["baseline"]["court"] = score("court", str(INSTALLED["court"]), "1", "court_current")
            save_state(s)
        for name, job in s["jobs"].items():
            if job["task"] == "court" and job["status"] == "scored" and ("good_rate" not in next(iter(job["report"].values()))
                                                                          or "handheld_sportcenter" not in job["summary"]["usable"]):
                log(f"rescoring {name} (usable rate)")
                job.update(score("court", str(run_dir(name, "court") / "weights" / "best.pt"), "1", name))
                log(f"{name}: {job['summary']}")
                save_state(s)

        for name, job in s["jobs"].items():
            if job["status"] in ("queued", "running"):
                pid = pids.get(name) or running_pid(name)
                if pid and pid_alive(pid):
                    if job["status"] != "running":
                        log(f"adopted running {name} (pid {pid})")
                    job["status"], pids[name] = "running", pid
                    continue
                pids.pop(name, None)
                if job["status"] == "running":  # it just exited
                    if train_finished(name, job["task"]):
                        job["status"] = "trained"
                    else:
                        job["tries"] = job.get("tries", 0) + 1
                        job["status"] = "failed" if job["tries"] >= 3 else "queued"
                        log(f"{name} stopped before finishing (try {job['tries']}); {job['status']}")
                elif train_finished(name, job["task"]):
                    job["status"] = "trained"
            if job["status"] == "trained":
                gpu = "1" if len([p for p in pids.values() if gpu_of(p) == 1]) <= len([p for p in pids.values() if gpu_of(p) == 0]) else "0"
                log(f"scoring {name}")
                try:
                    job.update(score(job["task"], str(run_dir(name, job["task"]) / "weights" / "best.pt"), gpu, name))
                    job["status"] = "scored"
                    log(f"{name}: {job['summary']}")
                except Exception as e:  # noqa: BLE001
                    job["status"] = "failed"
                    log(f"{name}: scoring failed: {e}")
            save_state(s)

        for task in ("court", "ball"):
            refine(s, task)

        # start queued jobs where there's room (court first: it has the most to gain)
        free = gpu_free_gb()
        per_gpu = [0] * len(free)
        for p in pids.values():
            g = gpu_of(p)
            if g is not None:
                per_gpu[g] += slots_of(p)
        hours_left = (STOP_LAUNCH_AT - datetime.now()).total_seconds() / 3600
        for name, job in sorted(s["jobs"].items(), key=lambda kv: kv[1]["task"] != "court"):
            if job["status"] != "queued":
                continue
            if hours_left < MIN_RUN_H and not (run_dir(name, job["task"]) / "weights" / "last.pt").exists():
                job["status"] = "skipped"
                log(f"{name}: skipped, only {hours_left:.1f} h left before {STOP_LAUNCH_AT:%H:%M}")
                continue
            options = [g for g in range(len(free)) if per_gpu[g] < MAX_PER_GPU and free[g] >= MIN_FREE_GB
                       and time.time() - last_launch.get(g, 0) > LAUNCH_GAP_S]
            if not options:
                break
            g = max(options, key=lambda g: free[g])
            pids[name] = launch(name, job, g, shared=per_gpu[g] > 0)
            job["status"] = "running"
            per_gpu[g] += 2 if per_gpu[g] else 1
            last_launch[g] = time.time()
        save_state(s)

        if datetime.now() >= FINAL_AT:  # deadline: score what the unfinished runs have so far, then install
            for name, job in s["jobs"].items():
                if job["status"] == "running" and (run_dir(name, job["task"]) / "weights" / "best.pt").exists():
                    log(f"deadline: scoring {name} as it stands (still training)")
                    try:
                        job.update(score(job["task"], str(run_dir(name, job["task"]) / "weights" / "best.pt"), "0", name))
                        job["status"], job["partial"] = "scored", True
                        log(f"{name}: {job['summary']}")
                    except Exception as e:  # noqa: BLE001
                        log(f"{name}: scoring failed: {e}")
            finalize(s)
            save_state(s)
            break
        if all(j["status"] in ("scored", "failed", "skipped") for j in s["jobs"].values()) and all(
                s["refine"][t] >= MAX_REFINE or not any(j["task"] == t and j["status"] == "scored" for j in s["jobs"].values())
                for t in ("court", "ball")):
            finalize(s)
            save_state(s)
            break
        time.sleep(POLL_S)
    log("autotrain done")


if __name__ == "__main__":
    sys.exit(main())
