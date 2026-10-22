# NextRun — handoff: where we are, what's next

Branch: `model_merge` (github.com/aisutd/nextrun). Pick up on a machine with an NVIDIA GPU and continue from
"Next steps". Everything below is reproducible from this repo + public data; nothing local is required.

## Where we are

**Repo layout:** `src/` (package `nextrun_cv`, `scripts/`) · `models/` (weights + configs) ·
`data/` (datasets, local only; `data/venues/` tracked) · `tests/` (48 passing) · `results/` (eval reports).

**Models installed in `models/`** (the pipeline uses these):

| Model | Weights | Status |
|---|---|---|
| Players (pose + tracking) | `yolo26m-pose.pt` (pretrained, auto-download) | done: drop-in, same 17 keypoints, ~2.5x faster than YOLO11m-pose |
| Court (24 keypoints) | `court_model.pt` (YOLO11s-pose) | **to retrain on GPU** |
| Ball + rim | `ball_hoop_model.pt` (YOLOv8n) | **to retrain on GPU** |

**Datasets (built by scripts, not stored in git):**

- Court, `data/court24` (`src/scripts/build_court_dataset.py`):
  - NBA broadcast, 850 frames (Hugging Face).
  - TrackID3x3 outdoor 3x3: 12 recordings of one fixed camera, re-registered per recording.
  - TrackID3x3 indoor gym: 42 clips.
  - TrackID3x3 **drone** court: test-only. A court and viewpoint never trained on; the key generalisation check.
  - Calibrations are in `data/venues/` (outdoor, indoor, drone).
- Ball/rim, `data/ball_rim` (`src/scripts/build_ball_rim_dataset.py`):
  - 6 Roboflow + 3 Hugging Face sets labelling both ball and rim.
  - ~10.8k unique frames (8.4k train / 1.4k val / 1.0k test), all CC BY 4.0.
  - Rim boxes = rim + net.

**Current models on those test sets** (`results/*_baseline_test.txt`):

| Court source | Found | Median error |
|---|---|---|
| NBA | 63/94 | 6.6 ft |
| Outdoor fixed camera | 9/22 | 19.2 ft |
| Drone court (unseen) | 22/42 | 73.8 ft |

Ball/rim: rim mAP50 0.96–0.99 on game footage. Ball mAP50 0.01–0.79 depending on the set; it is weakest on
non-broadcast and 3x3 footage.

**CPU-only experiments (this laptop, no GPU):**

- Court fine-tune at 640 px reached NBA 93/94 at 0.9 ft. Outdoor and the drone court were not solved.
- Ball YOLOv8n, 2 epochs: better on labelled sets, worse on our own footage (`results/ball_v2_notes.md`).
  Not installed.
- Conclusion: the bigger models need a GPU.

## Targets ("good")

- **Court:**
  - median error ≤ 1.5 ft (the pipeline flags 3PT calls within 1.5 ft of the line);
  - court found in ≥ 90 % of frames;
  - p90 error ≤ 3 ft;
  - **including the drone court**.
- **Ball:**
  - found in ≥ 90 % of frames of our footage (`src/scripts/check_ball_footage.py`);
  - mAP50 ≥ 0.8 on the test sets.
- **Rim:** mAP50 ≥ 0.95.
- **End to end:** shots / makes ≥ 90 % precision and recall; points / rebounds / assists within ±2 per player
  against a hand-labelled clip (`src/scripts/score_events.py`).

## Next steps (GPU machine)

```bash
git clone -b model_merge https://github.com/aisutd/nextrun.git && cd nextrun
python -m venv .venv && . .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[detect,train,dev]" gdown
pytest -q                                              # 48 tests, no GPU needed
export ROBOFLOW_API_KEY=...                            # free key, app.roboflow.com -> Settings -> API keys

# 1. data (~20 GB of video, then ~5 GB of frames)
python src/scripts/get_trackid3x3.py
T=data/raw/trackid3x3/videos
python src/scripts/build_court_dataset.py --out data/court24 --nba-hf \
  --venue trackid3x3_outdoor "$T/outdoor/IMG_0114.MOV,$T/outdoor/*.MOV" --venue-ref-frame trackid3x3_outdoor 900 \
  --venue trackid3x3_indoor "$T/indoor/*.mp4" \
  --venue trackid3x3_drone $T/drone/1-1.mov --venue-ref-frame trackid3x3_drone 300 --test-venue trackid3x3_drone \
  --every 300
python src/scripts/build_ball_rim_dataset.py --out data/ball_rim --roboflow suggested --hf suggested

# 2. score the current models (same test images as the new ones)
python src/scripts/eval_court.py --data data/court24 --split test | tee results/court_current_test.txt
python src/scripts/eval_ball_rim.py --data data/ball_rim --split test | tee results/ball_current_test.txt

# 3. train (resumable: re-run with  --name <run> --resume  after any stop)
python src/scripts/train.py court --data data/court24/data.yaml --model yolo26m-pose.pt --imgsz 1280 --epochs 200 --workers 4 --no-install --name court_yolo26m
python src/scripts/train.py court --data data/court24/data.yaml --model models/court_model.pt --imgsz 1280 --epochs 100 --workers 4 --no-install --name court_finetune
python src/scripts/train.py ball  --data data/ball_rim/data.yaml --model yolo26m.pt --imgsz 1024 --epochs 120 --workers 4 --no-install --name ball_yolo26m

# 4. score the new models
for r in court_yolo26m court_finetune; do
  python src/scripts/eval_court.py --data data/court24 --split test --weights results/runs/court/$r/weights/best.pt | tee results/${r}_test.txt
done
python src/scripts/eval_ball_rim.py --data data/ball_rim --split test --weights results/runs/ball/ball_yolo26m/weights/best.pt | tee results/ball_yolo26m_test.txt
python src/scripts/check_ball_footage.py $T/outdoor/IMG_0105.MOV $T/outdoor/IMG_0110.MOV $T/indoor/basket_S3T2_pre.mp4 $T/indoor/basket_S5T4_post.mp4 \
  --weights models/ball_hoop_model.pt results/runs/ball/ball_yolo26m/weights/best.pt --save results/ball_disagreements | tee results/ball_footage.txt
```

**5. Install rules** (copy `best.pt` over the file in `models/`; keep the old one as `*.prev.pt`):

- **Court:** a candidate must find the court at least as often (−2 % tolerance) and be at least as accurate as
  the current model on **every** test source, the drone court included. Among the candidates that pass, the
  lowest mean median error wins.
- **Ball:**
  - mean ball mAP50 goes up;
  - rim mAP50 doesn't drop by more than 0.01;
  - **and** ball / rim are found in at least as many frames of our own footage (look at `results/ball_disagreements`).

**6. Then:**

- Run the full pipeline on the outdoor clip:
  `python -m nextrun_cv run data/videos/outdoor_0025_0045.mp4 -o results/games/outdoor --venue trackid3x3_outdoor`
- Write `results/REPORT.md`: methodology, datasets, models, evaluation, results. Describe the current state
  only; don't narrate the history.
- Commit the reports and push. Commit installed weights too: `models/*.pt` are tracked, `yolo*.pt` downloads
  are not.

## Later (more accuracy)

- Hand-label one game clip (shots, makes, rebounds, assists) → measure the box score with `score_events.py`;
  tune `src/nextrun_cv/config.py`.
- Calibrate the other 5 TrackID3x3 drone flights the same way as `data/venues/trackid3x3_drone.json`.
  The builder follows moving cameras.
- Auto-label ball positions on TrackID3x3 footage (confident detections + track interpolation, spot-checked)
  for in-domain ball data.
- Rishabh's high-school court sets (Roboflow `workspace/project/version`) → `--roboflow` in the court build, so
  that domain is trained and measured.
