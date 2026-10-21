# NextRun

## Description

NextRun is a computer-vision-driven statistics tracker and community platform for recreational pickup basketball. Players and clubs can upload game footage, automatically track performance metrics, and maintain collectible player cards that evolve through games and challenges.

## Planned Technologies

- Python, JavaScript/TypeScript, and PostgreSQL
- React Native
- FastAPI
- PyTorch, Ultralytics YOLO, OpenCV, and scikit-learn

## Docker Setup

Make sure Docker Desktop is installed and running.

```bash
docker compose up -d
docker compose down
docker compose ps
```

This is a generic starter configuration. The team can add project-specific dependencies and startup commands later.

## Computer-vision pipeline (`nextrun_cv`)

Combines the team's models into one stat-tracking pipeline for **fixed-camera pickup games**:

| Piece | Source | Used for |
|---|---|---|
| Player detection + pose + tracking | YOLO11-pose + Ultralytics BoT-SORT (ReID), replaces the TrackID3x3 notebook (`notebooks/NextRun_BodyDetection.ipynb`) | who is where, hands (possession), feet (court position) |
| Ball + rim detection | `models/ball_hoop_model.pt` (YOLOv8n, classes `ball`, `rim`) | ball trajectory, shots, makes |
| Court calibration | `nextrun_cv/court/` — 3 methods: **keypoint model** (`models/court_keypoints.pt`, YOLO11n-pose, 35 court landmarks), **line registration**, **manual clicks** (auto fallback chain) | court coordinates, 2PT vs 3PT, shot chart, off-court filtering |
| Identity | tag track IDs once → names/teams; jersey-colour re-linking + team clustering | per-player stats |
| Events | possession, dribbles, passes, shots, make/miss, 3PT, dunks, rebounds (O/D), steals, turnovers, assists, ball arcs | box score |

### Quick start (Colab, GPU)
Open `notebooks/NextRun_Pipeline.ipynb` in Colab and run top to bottom.

### CLI
```bash
pip install -e ".[detect]"            # ultralytics etc.
python -m nextrun_cv detect game.mp4 -o outputs/game1          # GPU-heavy, once
# look at outputs/game1/tagging_frame.jpg, write outputs/game1/tags.json:
#   {"3": {"name": "Tushaar", "team": "Red"}, "7": {"name": "Juan", "team": "Blue"}}
python -m nextrun_cv calibrate game.mp4 -o outputs/game1 [--court-points points.json] [--court nba]
python -m nextrun_cv analyze -o outputs/game1                  # cheap; re-run after changing tags/config
python -m nextrun_cv render game.mp4 -o outputs/game1          # annotated.mp4
```
Outputs: `boxscore.csv`, `team_totals.csv`, `events.json`, `flights.json` (ball arcs), `shot_chart.png`,
`pass_network.png`, `possession.png`, `annotated.mp4`.

### Layout
```
nextrun_cv/
  detect/    players.py (pose+BoT-SORT), ball_hoop.py, ball_track.py (Kalman + gap fill, stable rims)
  court/     template.py (geometry, 3PT), manual.py, lines.py, keypoints.py, auto.py
  identity/  appearance.py, teams.py, tagging.py
  events/    possession.py, flight.py (arcs), analyzer.py (all event rules)
  stats/     boxscore.py
  viz/       overlay.py (annotated video), charts.py
  pipeline.py, cli.py, config.py (every threshold)
train/       train_ball_hoop.py, prepare_court_dataset.py, train_court_keypoints.py, eval_court_keypoints.py
eval/        score.py (precision/recall vs hand labels)
tests/       synthetic games covering every event type (no GPU needed)
```

### Court-keypoint model
Trained on the public **basketball-court-detection-2** dataset (850 NBA broadcast frames, CC BY 4.0, via the
Hugging Face mirror `koppolusameer/basketball-keypoint-detection-yolov8`). `prepare_court_dataset.py` maps its
48 keypoints to our named landmarks, drops mislabeled points with RANSAC, and fills in unlabeled visible
landmarks from each image's homography. At inference the visible keypoints → RANSAC homography → line
refinement; a left/right-half mix-up is detected from the homography's orientation and fixed.
```bash
pip install -e ".[train]"
python train/prepare_court_dataset.py --out data/court_kp
python train/train_court_keypoints.py            # copies best.pt to models/court_keypoints.pt
python train/eval_court_keypoints.py --split test
```
The training data is NBA arenas; for gyms/outdoor courts, fine-tune with frames from your own camera
(`--model models/court_keypoints.pt`). Manual clicking remains the most reliable option for a fixed camera.

### Development
```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows (use .venv/bin on macOS/Linux)
pytest
```

### Known limits / next steps
- Event rules are heuristic v1; tune thresholds in `Config` against labelled clips (`eval/score.py`).
- Blocks, free throws, fouls not detected yet.
- Court-keypoint model has only seen NBA broadcast footage; expect weaker results on pickup courts until fine-tuned.
- The ball model is YOLOv8n; retraining at `imgsz=1280` (`train/train_ball_hoop.py`) should help with small balls.
- Moving/panning cameras need per-frame calibration (not supported yet).
