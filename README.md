# NextRun

NextRun is a computer-vision-driven statistics tracker and community platform for recreational pickup basketball. Players and clubs can upload game footage, automatically track performance metrics, and maintain collectible player cards that evolve through games and challenges.

**Tech:** Python · FastAPI · PyTorch / Ultralytics YOLO26 · OpenCV · scikit-learn · PostgreSQL · React Native

Goal: community footage from any camera (fixed, drone, phone on the ground, partial court) → player tracking → box score.

## What it tracks

Headline stats per player: **points, rebounds, assists**. The supporting stats come from the same events:
FGM/FGA, 2PT/3PT, offensive/defensive rebounds, steals, turnovers, passes, dribbles, possession time.

## Architecture

Three neural models plus geometry, run as one unit (`nextrun_cv.integration.NextRun`):

| Model | Weights (installed) | Architecture | Input size | Output |
|---|---|---|---|---|
| Players: pose + tracking | `weights/players/yolo26m-pose.pt` (pretrained COCO, auto-download) + BoT-SORT | YOLO26m-pose, 17 COCO keypoints | frame long side, ≤ 3840 | who is where, hands, feet, track id |
| Ball + rim | `weights/ball_hoop/ball_pseudo.pt` | YOLO26l detector, 2 classes (`ball`, `rim`; rim box = rim + net) | trained 1024, run at ≤ 1920 (`ModelConfig.ball_max_imgsz`) | ball path, rim position |
| Court keypoints | `weights/court/court_synth.pt` | YOLO26m-pose, 1 class `court`, 24 keypoints (`weights/court/court_keypoints.json`) | 1280 | image ↔ court position (feet / metres) |

```
video ─► camera motion ─► fixed camera?  yes ─► one court fit for the clip (rims check it)
             │                            no  ─► court model on keyframes, carried through the camera motion,
             │                                   median of neighbouring fits per frame   (court/track.py)
             ▼
         detect (GPU, once): players (pose + BoT-SORT) · ball + rim
             ▼
         tracklet stitching (identity/stitch.py) ─► tag players / team colours ─► fuse ─► events ─► box score
```

### How the models work together (`src/nextrun_cv/fusion.py`)
```
 court model ── homography (floor pixels <-> court feet)
     │   ▲
     │   └── rim model: a real rim sits straight above its hoop's floor point.
     │       Agree -> court fit accepted + we know which basket each rim is.
     │       Disagree -> fit rejected, next calibration method tried.
     ▼
 pose model ── feet -> court position: on/off court, 2PT / 3PT zone, distance to the line
     ▲
     └────── ball model: ball at a player's hand -> who has it -> possession, passes, shots
```

Key pieces:

- **Court estimator** (`court/keypoints.py`, `KeypointCourtEstimator`): fits a homography to the predicted
  keypoints (RANSAC). One-basket views are ambiguous by 180°, so it also tries folding mixed predictions onto one
  half (`fold_to_one_half`) and enforces the labelling convention (view direction d_x > d_y), refitting with the
  180° partner ids when it's broken.
- **Court track** (`court/track.py`): background frame-to-frame homography (players masked out) decides fixed vs
  moving camera (`CameraConfig.moving_px`). Moving cameras get keyframe fits every `keyframe_s`, each checked
  against that frame's rims, carried to every frame and smoothed by a weighted median within `window_s`.
- **Tracker**: BoT-SORT, `weights/players/botsort_reid.yaml` (fixed camera) or `weights/players/botsort_reid_moving.yaml`
  (camera-motion compensation, `match_thresh 0.9`, `track_buffer 150`, built-in ReID off: it caused more switches
  on uniforms). Tuned on SportsMOT basketball val (`results/tracker_sweep/`).
- **Tracklet stitching** (`identity/stitch.py`): offline Hungarian matching of track ends to later track starts
  (gap, reach in court metres, torso colour), so a player lost behind others keeps one id.
- **Events** (`events/analyzer.py`):
  - **Points:** shot = ball leaves a player's hands and rises toward the rim; made = it passes the rim plane near the
    top of the rim box (boxes include the net); 2 or 3 from the shooter's feet, measured to the basket the ball
    went to. Shots within 1.5 ft of the line are flagged `three_close`.
  - **Rebounds:** the team that controls the ball after a missed shot (offensive if same team as the shooter).
  - **Assists:** pass to a player who scores within 3 s with at most 2 dribbles.

Every threshold lives in `src/nextrun_cv/config.py`.

```python
from nextrun_cv.integration import NextRun
nr = NextRun()
nr.analyze_image(img)        # one image: court + players (zone, court_xy) + ball holder + baskets, as JSON
nr.calibrate(first_frames)   # video: calibrate once (fixed camera) ...
f = nr.process(frame, i, t)  # ... then every frame is detected and fused
```

## Models and saved weights

All weights live in `weights/`, one folder per kind of model:

```
weights/
  active.json            which file the pipeline uses for each kind (edit to switch models)
  players/               body detection + pose: yolo26m-pose.pt (stock, auto-downloads), BoT-SORT tracker configs
  ball_hoop/             ball + rim detectors: <run>.pt for every GPU run
  court/                 court keypoint models: <run>.pt for every GPU run, court_keypoints.json, README.md (keypoint layout)
  */archive/             superseded CPU-era weights (local only, not in git)
  pretrained/            stock Ultralytics starting points for training (local only, downloaded on demand)
```

Active models (`weights/active.json`): players `players/yolo26m-pose.pt`, ball + rim `ball_hoop/ball_pseudo.pt`,
court `court/court_synth.pt`. Each run's training config (`args.yaml`) and per-epoch metrics (`results.csv`,
`results.png`) are in `results/runs/<task>/<run>/`. `train.py` saves every new run to `weights/<kind>/<run>.pt` and
makes it active unless `--no-install`; `nextrun_cv.config.install_weights()` does the same for any file.

Train any of them with `src/scripts/train.py` (see `HANDOFF.md`); `src/scripts/autotrain.py` ran the overnight
search on 2x RTX 6000 Ada (scheduler, scoring, install rule; summary in `results/autotrain/SUMMARY.md`, full notes in
`results/autotrain/LOOP_NOTES.md`).

### Court keypoint models (24 keypoints, `weights/court/`)

Datasets: `data/court24` = HS gyms (Roboflow) + NBA broadcast (850 frames, HF) + TrackID3x3 outdoor + indoor,
auto-labelled through each venue's homography; the TrackID3x3 drone flight 1-1 is test-only.
`data/court24s` = court24 + 3,600 synthetic views (`src/scripts/synth_court.py`: rendered FIBA/NBA/HS courts and
real frames re-projected to ground / raised / drone cameras, exact labels) + 378 frames from drone flight 2-1
(`src/scripts/build_drone_extra.py`).

Scored with `src/scripts/eval_court.py`. **Usable** = images whose median mapping error is ≤ 3 ft (a "found" court
can be the wrong court, so found rate alone misleads). Reports: `results/court_<run>_test.txt`,
`_synth_test.txt` (synthetic views), `_handheld_test.txt` (EPFL SportCenter phones, real handheld, test-only).

| Run | Architecture | Init → data | imgsz | Usable NBA / drone / outdoor | Synthetic views usable (drone / raised / ground) | Real handheld usable |
|---|---|---|---|---|---|---|
| `archive/court_yolo11s_original` | YOLO11s-pose | HS gyms | 640 | 0.02 / 0 / 0 | 0 / 0 / 0 | 0 |
| `archive/`: `court_kp`, `court_nba_outdoor`, `court_v2`, `court24_cpu` | YOLO11n/s-pose | laptop CPU experiments | 640 | — (superseded) | — | — |
| `court_finetune` | YOLO11s-pose | previous model → court24 | 1280 | 0.99 / 0 / 1.00 | 0.02 / 0.06 / 0 | 0 |
| `court_yolo26m` | YOLO26m-pose | COCO → court24 | 1280 | 0.99 / 0 / 1.00 | 0.01 / 0.10 / 0.01 | 0 |
| `court_yolo26m_hires1536` | YOLO26m-pose | court_yolo26m → court24 | 1536 | 0.99 / 0 / 1.00 | 0.02 / 0.12 / 0.01 | 0 |
| `court_yolo26l` | YOLO26l-pose | COCO → court24 | 1280 | 1.00 / 0 / 1.00 | 0.02 / 0.08 / 0 | 0 |
| `court_yolo26l_polish` | YOLO26l-pose | court_yolo26l → court24 | 1280 | 0.99 / 0 / 1.00 | 0.02 / 0.10 / 0.01 | 0 |
| **`court_synth` (installed)** | **YOLO26m-pose** | **court_yolo26m → court24s, lr0 0.002, harder warps** | **1280** | **0.99 / 1.00 / 1.00** | **0.64 / 0.51 / 0.21** | **0.06** |

`court_synth` median error: NBA 0.33 ft, drone 0.30 ft, outdoor 0.25 ft (p90 ≤ 0.81 ft). On the drone video, the
per-frame court track is usable on 42/42 frames at 0.38 ft (one static fit: 12/42 at 5.3 ft;
`results/court_track_1-1.json`). Weak spot: handheld indoor gyms with multi-sport floor markings (6 %).

### Ball + rim detectors (`weights/ball_hoop/`)

Dataset: `data/ball_rim` = 6 Roboflow + 3 Hugging Face sets labelling both ball and rim, ~10.8k frames, CC BY 4.0.
`data/ball_rim_pl` = ball_rim + 509 pseudo-labelled frames from our own wide TrackID3x3 footage, x3
(`src/scripts/pseudo_label_ball.py`; the 5 footage-check videos excluded).

Scored on the test split (mAP50) and on our footage with `src/scripts/check_ball_footage.py` (149 sampled frames
from 5 TrackID3x3 videos; static spots such as a spare ball by the court are not counted). Reports:
`results/ball_<run>_test.txt`.

| Run | Architecture | Init → data | imgsz | Ball mAP50 | Rim mAP50 | Footage ball | Footage rim |
|---|---|---|---|---|---|---|---|
| `archive/ball_hoop_yolov8n_original` | YOLOv8n | — | 640 | 0.428 | 0.703 | 65/149 | 149/149 |
| `archive/`: `ball_v2`, `ball_rim_cpu` | YOLOv8n | laptop CPU experiments (`results/ball_v2_notes.md`) | 640–960 | — | — | worse on footage | — |
| `ball_yolo26s` | YOLO26s | COCO → ball_rim | 1024 | 0.911 | 0.897 | 48/149 | 147/149 |
| `ball_yolo26s_hires1280` | YOLO26s | ball_yolo26s → ball_rim | 1280 | 0.869 | 0.881 | 39/149 | 86/149 |
| `ball_yolo26m` | YOLO26m | COCO → ball_rim | 1024 | 0.921 | 0.855 | 66/149 | 120/149 |
| `ball_yolo26l` | YOLO26l | COCO → ball_rim | 1024 | 0.900 | 0.876 | 61/149 | 147/149 |
| **`ball_pseudo` (installed)** | **YOLO26l** | **ball_yolo26l → ball_rim_pl, lr0 0.002** | **1024** | **0.918** | **0.837** | **100/149** | **149/149** |

Lesson: the YOLO26 models were ~2x better on labelled sets but missed obvious balls on our wide 4K footage;
pseudo-labelling our own footage closed that gap. Run the ball model at ≤ 1920 px: at native 4K it reports
frame-sized false rims.

### Players + tracking

Pretrained `weights/players/yolo26m-pose.pt` (no fine-tune; drop-in for YOLO11m-pose, ~2.5x faster). Scored on SportsMOT basketball
val (15 sequences, `src/scripts/eval_tracking.py`, `results/tracking_sportsmot*.json`):

| Version | MOTA | IDF1 | ID switches | Predicted ids (GT 150) |
|---|---|---|---|---|
| first version, raw tracker | 0.351 | 0.357 | 1064 | 2045 |
| tuned tracker (sweep B) + court fusion | 0.556 | 0.422 | 717 | 1038 |
| **+ tracklet stitching (current)** | **0.557** | **0.518** | **591** | **434** |

Remaining id switches are mostly teammates swapping: same-team players can't be told apart by torso colour or
ImageNet features (AUC ~0.55); that needs jersey numbers or a sports-trained ReID model.

## End-to-end results (events)

543 labelled NBA clips (`data/raw/hf_events/rkun`, clip-level shots / makes / assists / OREB; research use only),
`src/scripts/eval_events_clips.py`, `results/events_clips_<tag>.json`. Clip-level presence, current pipeline (`v4c`)
vs the first version:

| Event | Precision | Recall | Exact count per clip | First version: P / R |
|---|---|---|---|---|
| Shot | 1.00 | 0.95 | 70 % | 1.00 / 0.86 |
| Made shot | 0.83 | 0.82 | 83 % | 0.65 / 0.52 |
| 3PT attempt | 0.73 | 0.58 | 81 % | 0.48 / 0.21 |
| Made 3 | 0.62 | 0.57 | 93 % | 0.50 / 0.20 |
| Points | — | — | 79 % | 57 % exact |
| Assist | 0.58 | 0.29 | 74 % | 0.38 / 0.16 |
| Offensive rebound | 0.36 | 0.54 | 72 % | 0.26 / 0.55 |

Totals over all clips (truth → predicted): points 567 → 557, makes 259 → 256, shots 601 → 666.

## Repo layout

```
src/
  nextrun_cv/       the CV pipeline (pip install -e . installs it)
    detect/           players.py, ball_hoop.py, ball_track.py
    court/            keypoints.py (court model), track.py (per-frame court for moving cameras), lines.py,
                      manual.py, template.py (court geometry, 3PT), venues.py
    identity/         tagging, stitch.py (tracklet stitching), jersey colour re-linking, team clustering
    events/           possession, ball flights, analyzer.py (shots, rebounds, assists, ...)
    stats/            boxscore.py
    viz/              annotated video, shot chart, pass network
    integration.py    NextRun: all three models as one unit
    fusion.py         geometry between models (rim <-> court, feet -> court, ball -> holder)
    pipeline.py       stages: detect / calibrate / analyze / render
    api.py            FastAPI app (upload game -> stats)
    datasets.py       training-data tooling (downloads, group splits, homography-projected labels)
  scripts/          datasets: build_court_dataset.py, build_ball_rim_dataset.py, synth_court.py, build_drone_extra.py,
                    build_sportcenter.py, pseudo_label_ball.py, get_trackid3x3.py
                    training: train.py, autotrain.py
                    eval: eval_court.py, eval_court_track.py, eval_ball_rim.py, check_ball_footage.py,
                    eval_tracking.py, eval_events_clips.py, score_events.py
weights/          players/, ball_hoop/, court/ (weights + their configs), active.json (models in use)
data/             venues/ (saved camera calibrations, tracked); datasets, raw downloads, videos (local only)
tests/            synthetic games for every event type + API + dataset tooling + court tracking (no GPU needed)
results/          eval reports; runs/<task>/<run>/ (args.yaml, results.csv); autotrain/ (search summary + notes);
                  training logs, per-clip eval outputs and processed games stay local
```

## Run it

**API:**
```bash
pip install -e ".[detect,api]"
uvicorn nextrun_cv.api:app --reload               # docs at http://localhost:8000/docs
# or: docker compose up --build
```
| Endpoint | Does |
|---|---|
| `POST /frames/analyze` (image) | one frame through all models: positions, zones, ball holder, baskets |
| `GET /venues` | saved camera profiles |
| `POST /games` (video file, `court` or `venue`) | upload; processing starts in the background |
| `GET /games/{id}` | status: queued → detecting → calibrating → analyzing → done |
| `GET /games/{id}/tagging-frame` | frame with tracker ids, to know who is who |
| `PUT /games/{id}/tags` `{"3": {"name": "Tushaar", "team": "Red"}}` | name players, re-run stats |
| `GET /games/{id}/stats` | box score per player + team (PTS, REB, AST first) |
| `GET /games/{id}/events` | event log |

**CLI:**
```bash
python -m nextrun_cv detect game.mp4 -o results/games/game1          # GPU-heavy, once
# look at results/games/game1/tagging_frame.jpg, write results/games/game1/tags.json
python -m nextrun_cv calibrate game.mp4 -o results/games/game1 [--court-points points.json]
python -m nextrun_cv analyze -o results/games/game1                  # re-run after changing tags/config
python -m nextrun_cv render game.mp4 -o results/games/game1          # annotated.mp4
python -m nextrun_cv run game.mp4 -o results/games/game2 --venue trackid3x3_outdoor   # known camera: no calibration step
```
Outputs: `boxscore.csv`, `team_totals.csv`, `events.json`, `shot_chart.png`, `pass_network.png`, `annotated.mp4`.

To use a different saved model, point `ModelConfig` at it, e.g.
`ModelConfig(court_keypoint_weights="weights/court/court_yolo26m.pt")`, or change `weights/active.json`.

## Venues (one calibration per fixed camera)
A fixed camera can be calibrated once and saved in `data/venues/<name>.json`: court type, ~6 clicked court
landmarks, and optionally the playing area (e.g. a 3x3 half court) so spectators are dropped. Every game from that
camera then uses `--venue <name>`; the rim check still runs each game and flags a camera that moved. Click points with
`nextrun_cv.court.manual.cv2_click_landmarks` (OpenCV window) and save with `nextrun_cv.court.venues.save_venue`.
Moving cameras (venue `"fixed_camera": false`, drones, phones) are calibrated per frame automatically.

## Improving the models
Training needs an NVIDIA GPU; the full sequence (download data, build datasets, score, train, score again on the
same test images, install only if better) is in `HANDOFF.md`. Splits are by video / game clip so near-duplicate
frames can't inflate test scores. Downloading from Roboflow needs a free `ROBOFLOW_API_KEY`.

Data details that matter:
- **Rim boxes = rim + net.** The pipeline's rim thresholds assume it; sets that box only the ring are extended
  down to a square.
- **Fixed cameras move a little between recordings** (10-23 px on the outdoor 4K camera); each video is
  registered to the reference video before labelling. Moving cameras are followed frame by frame and snapped onto
  the painted lines, so labels don't drift.
- **Fixed-camera test frames mostly measure memorisation**; the drone court and the SportCenter handheld set are
  the honest checks for new viewpoints.
- Synthetic court labels must follow the real sets' convention (handedness + view direction d_x > d_y).
- Look at footage, not just mAP: the labelled ball sets rewarded models that failed on our own videos.

**What goes to GitHub:** code, docs, eval reports and the trained weights in `weights/` (~490 MB, every file
< 100 MB). Never datasets (`data/` except `data/venues/`), videos, `data.zip`, training logs, per-clip eval outputs,
stock pretrained weights or the `archive/` folders: `.gitignore` keeps them local.

Licences: SportCenter (EPFL) and the NBA event clips are research-only and used as test sets only;
SportsMOT is CC BY-NC; the training sets are CC BY 4.0.

## Development
```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # Windows: .venv\Scripts\pip
pytest      # 58 pass; test_lines_auto_from_scratch is a known failure (line-based calibration fallback)
```

## Known limits / next steps
- Handheld indoor gyms with multi-sport markings: court usable on only 6 % of frames. Next: synthetic multi-sport
  line clutter, or train on the SportCenter split if its licence allows.
- Assists (recall 0.29) and offensive rebounds (precision 0.36) are the weakest stats.
- Same-team ID switches: need jersey-number reading or a sports ReID model.
- No labelled pickup-game events yet: stats accuracy on community footage is unmeasured
  (`src/scripts/score_events.py` expects `labels/<clip>.json`).
- Drone flights 3-1 … 6-1 (other courts) need hand-picked calibration points to become training data.
- Not detected yet: blocks, free throws, fouls.
