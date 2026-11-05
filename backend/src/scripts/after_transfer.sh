#!/usr/bin/env bash
# Wait for data.zip to finish arriving, unpack it, then run HANDOFF.md steps 2-4 (baseline eval, train, eval).
# Builds a Linux venv (.venv-linux, via uv) while the transfer is still running.
#
#   setsid nohup bash src/scripts/after_transfer.sh > results/logs/after_transfer.log 2>&1 &
#   tail -f results/logs/after_transfer.log
#
# Runs three trainings at once across both GPUs (see step 4). Training is resumable with --resume (HANDOFF.md).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ZIP="${ZIP:-$REPO/data.zip}"
STABLE_SECS="${STABLE_SECS:-120}"   # size must not change for this long before we try to open the zip
VENV="$REPO/.venv-linux"
LOGS="$REPO/results/logs"
cd "$REPO"
mkdir -p "$LOGS"
log() { echo "[$(date '+%F %T')] $*"; }

# --- 1. environment (in the background, overlaps with the transfer) -------------------------------------
setup_env() {
  if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$PATH"
  [ -x "$VENV/bin/python" ] || uv venv --python 3.11 "$VENV"
  VIRTUAL_ENV="$VENV" uv pip install -e ".[detect,train,dev]"
  "$VENV/bin/python" -c "import torch, ultralytics; assert torch.cuda.is_available(); print('torch', torch.__version__, 'gpus', torch.cuda.device_count(), 'ultralytics', ultralytics.__version__)"
}
log "setting up $VENV"
setup_env > "$LOGS/env_setup.log" 2>&1 &
ENV_PID=$!

# --- 2. wait for the zip ---------------------------------------------------------------------------------
log "waiting for $ZIP to finish (stable for ${STABLE_SECS}s and readable)"
while true; do
  if [ -f "$ZIP" ]; then
    s1=$(stat -c %s "$ZIP"); sleep "$STABLE_SECS"; s2=$(stat -c %s "$ZIP")
    if [ "$s1" = "$s2" ]; then
      if unzip -l "$ZIP" >/dev/null 2>&1; then break; fi  # central directory is written last: readable = complete
      log "size stable at $s2 bytes but zip not readable yet; still waiting"
    else
      log "still arriving: $((s2 / 1024 / 1024)) MiB"
    fi
  else
    sleep 30
  fi
done
log "transfer complete: $(du -h "$ZIP" | cut -f1)"

# --- 3. unpack -------------------------------------------------------------------------------------------
# entries may be "data/court24/..." or "court24/..."; land them under data/ either way
if unzip -Z1 "$ZIP" | grep -qv '^data/'; then DEST="$REPO/data"; else DEST="$REPO"; fi
log "extracting into $DEST"
unzip -q -o "$ZIP" -d "$DEST"   # non-zero exit (CRC error etc.) stops the script via set -e
for d in court24 ball_rim; do
  y="$REPO/data/$d/data.yaml"
  [ -f "$y" ] || { log "missing $y after extraction; zip layout:"; unzip -Z1 "$ZIP" | head -40; exit 1; }
  # builders write an absolute path from the machine that made the dataset; point it here
  sed -i "s|^path:.*|path: $REPO/data/$d|" "$y"
done
log "datasets ready: $(ls data)"

log "waiting for environment setup"
wait "$ENV_PID" || { log "env setup failed, see $LOGS/env_setup.log"; exit 1; }
tail -1 "$LOGS/env_setup.log"
PY="$VENV/bin/python"

# --- 4. baseline eval, train, eval (HANDOFF.md steps 2-4) -------------------------------------------------
# 48 cores / 500 GB RAM: images cached in RAM, 12 loader workers per run. Three runs at once:
#   GPU 0: court_yolo26m alone (85% of memory), then court_yolo26l
#   GPU 1: ball_yolo26m + court_finetune side by side (40% each), then ball_yolo26l
"$PY" src/scripts/eval_court.py --data data/court24 --split test --device 0 > results/court_current_test.txt 2>&1 &
"$PY" src/scripts/eval_ball_rim.py --data data/ball_rim --split test --device 1 > results/ball_current_test.txt 2>&1 &
wait
log "baseline scores written: results/court_current_test.txt, results/ball_current_test.txt"

TRAIN="$PY src/scripts/train.py"
FAST="--workers 12 --cache ram --no-install"
eval_court() { "$PY" src/scripts/eval_court.py --data data/court24 --split test --device "$2" --weights results/runs/court/$1/weights/best.pt > results/$1_test.txt 2>&1; }
eval_ball() { "$PY" src/scripts/eval_ball_rim.py --data data/ball_rim --split test --device "$2" --weights results/runs/ball/$1/weights/best.pt > results/$1_test.txt 2>&1; }

court_m() { set -e
  $TRAIN court --data data/court24/data.yaml --model yolo26m-pose.pt --imgsz 1280 --epochs 200 --batch 0.85 --device 0 $FAST --name court_yolo26m
  eval_court court_yolo26m 0
  $TRAIN court --data data/court24/data.yaml --model yolo26l-pose.pt --imgsz 1280 --epochs 200 --batch 0.85 --device 0 $FAST --name court_yolo26l
  eval_court court_yolo26l 0
}
ball_m() { set -e
  $TRAIN ball --data data/ball_rim/data.yaml --model yolo26m.pt --imgsz 1024 --epochs 120 --batch 0.4 --device 1 $FAST --name ball_yolo26m
  eval_ball ball_yolo26m 1
  $TRAIN ball --data data/ball_rim/data.yaml --model yolo26l.pt --imgsz 1024 --epochs 120 --batch 0.4 --device 1 $FAST --name ball_yolo26l
  eval_ball ball_yolo26l 1
}
court_ft() { set -e
  sleep 180  # let ball_m size its batch first so the two runs don't both claim the same free memory
  $TRAIN court --data data/court24/data.yaml --model weights/court/archive/court_yolo11s_original.pt --imgsz 1280 --epochs 100 --batch 0.4 --device 1 $FAST --name court_finetune
  eval_court court_finetune 1
}
log "training: court_yolo26m->court_yolo26l on GPU 0, ball_yolo26m->ball_yolo26l + court_finetune on GPU 1 (logs in $LOGS)"
court_m  > "$LOGS/court_m.log"  2>&1 & P0=$!
ball_m   > "$LOGS/ball_m.log"   2>&1 & P1=$!
court_ft > "$LOGS/court_ft.log" 2>&1 & P2=$!
rc=0
wait $P0 || { rc=1; log "court_m chain failed, see $LOGS/court_m.log"; }
wait $P1 || { rc=1; log "ball_m chain failed, see $LOGS/ball_m.log"; }
wait $P2 || { rc=1; log "court_ft failed, see $LOGS/court_ft.log"; }
log "done (rc=$rc). Scores in results/*_test.txt. Next: install rules in HANDOFF.md step 5."
exit $rc
