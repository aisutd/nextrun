# NextRun

NextRun is a computer-vision-driven statistics tracker and community platform for recreational pickup basketball. Players and clubs can upload game footage, automatically track performance metrics, and maintain collectible player cards that evolve through games and challenges.

**Tech:** Python · FastAPI · PyTorch / Ultralytics YOLO · OpenCV · scikit-learn · PostgreSQL · React Native

## What it tracks

Headline stats per player: **points, rebounds, assists**. The supporting stats come from the same events:
FGM/FGA, 2PT/3PT, offensive/defensive rebounds, steals, turnovers, passes, dribbles, possession time.

## How it works

Three models, run as one unit (`nextrun_cv.integration.NextRun`):

| Model | File | Gives us |
|---|---|---|
| Player pose + tracking | `models/yolo11m-pose.pt` + BoT-SORT (auto-downloaded) | who is where, hands, feet |
| Ball + rim | `models/ball_hoop_model.pt` (YOLOv8n) | ball path, rim position |
| Court keypoints | `models/court_model.pt` (YOLO11s-pose, 24 points) | image ↔ court position in feet |

### How the models work together (`nextrun_cv/fusion.py`)
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
On 116 broadcast test frames the court model found a court in 69; the rim check confirmed 53 and rejected
16 bad fits (which would otherwise have put fans on the court and given wrong 2PT/3PT calls).

```python
from nextrun_cv.integration import NextRun
nr = NextRun()
nr.analyze_image(img)        # one image: court + players (zone, court_xy) + ball holder + baskets, as JSON
nr.calibrate(first_frames)   # video: calibrate once (fixed camera) ...
f = nr.process(frame, i, t)  # ... then every frame is detected and fused
```

### Video pipeline
```
video ─► detect (NextRun, GPU, once) ─► calibrate court (checked by rims) ─► tag players ─► fuse + analyze ─► box score
```

- **Points:** shot = ball leaves a player's hands and rises toward the rim; made = it passes through the rim;
  2 or 3 from the shooter's feet, measured to the basket the ball went to. Shots within 1.5 ft of the line are flagged `three_close`.
- **Rebounds:** first player to gain possession after a missed shot (offensive if same team as the shooter).
- **Assists:** pass to a player who scores within 3 s with at most 2 dribbles.

Every threshold lives in `nextrun_cv/config.py`.

## Repo layout

```
backend/        FastAPI app (upload game → stats)
nextrun_cv/     the CV pipeline
  detect/         players.py, ball_hoop.py, ball_track.py
  court/          keypoints.py (court model), lines.py, manual.py, template.py (court geometry, 3PT)
  identity/       tagging, jersey colour re-linking, team clustering
  events/         possession, ball flights, analyzer.py (shots, rebounds, assists, ...)
  stats/          boxscore.py
  viz/            annotated video, shot chart, pass network
  integration.py  NextRun: all three models as one unit
  fusion.py       geometry between models (rim <-> court, feet -> court, ball -> holder)
  pipeline.py     stages: detect / calibrate / analyze / render
models/         ball_hoop_model.pt, court_model.pt (yolo11m-pose.pt downloads here on first run)
configs/        court_keypoints.json (court model geometry), botsort_reid.yaml (tracker)
notebooks/      NextRun_Pipeline.ipynb (Colab, GPU, run top to bottom)
scripts/        train_ball_hoop.py, score_events.py (precision/recall vs hand labels)
docs/           court_detection.md (court model data, accuracy, limits)
tests/          synthetic games for every event type + API (no GPU needed)
```

## Run it

**Colab (GPU):** open `notebooks/NextRun_Pipeline.ipynb`, run top to bottom.

**API:**
```bash
pip install -e ".[detect,api]"
uvicorn backend.app:app --reload               # docs at http://localhost:8000/docs
# or: docker compose up --build
```
| Endpoint | Does |
|---|---|
| `POST /frames/analyze` (image) | one frame through all models: positions, zones, ball holder, baskets |
| `POST /games` (video file, `court`) | upload; processing starts in the background |
| `GET /games/{id}` | status: queued → detecting → calibrating → analyzing → done |
| `GET /games/{id}/tagging-frame` | frame with tracker ids, to know who is who |
| `PUT /games/{id}/tags` `{"3": {"name": "Tushaar", "team": "Red"}}` | name players, re-run stats |
| `GET /games/{id}/stats` | box score per player + team (PTS, REB, AST first) |
| `GET /games/{id}/events` | event log |

**CLI:**
```bash
python -m nextrun_cv detect game.mp4 -o outputs/game1          # GPU-heavy, once
# look at outputs/game1/tagging_frame.jpg, write outputs/game1/tags.json
python -m nextrun_cv calibrate game.mp4 -o outputs/game1 [--court-points points.json]
python -m nextrun_cv analyze -o outputs/game1                  # re-run after changing tags/config
python -m nextrun_cv render game.mp4 -o outputs/game1          # annotated.mp4
```
Outputs: `boxscore.csv`, `team_totals.csv`, `events.json`, `shot_chart.png`, `pass_network.png`, `annotated.mp4`.

## Development
```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows (.venv/bin on macOS/Linux)
pytest
```

## Known limits / next steps
- Fixed cameras only; a panning camera needs per-frame court calibration.
- Court model is trained on high-school gyms (corner + sideline views); other angles or outdoor courts may
  need more labelled frames (see `docs/court_detection.md`). Manual clicks are the fallback.
- Event rules are heuristic v1: label a few clips and tune `Config` with `scripts/score_events.py`.
- Ball model is YOLOv8n; retraining at `imgsz=1280` (`scripts/train_ball_hoop.py`) should help with small balls.
- Not detected yet: blocks, free throws, fouls.
