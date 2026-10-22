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
| Player pose + tracking | `models/yolo26m-pose.pt` + BoT-SORT (auto-downloaded) | who is where, hands, feet |
| Ball + rim | `models/ball_hoop_model.pt` (YOLOv8n) | ball path, rim position |
| Court keypoints | `models/court_model.pt` (YOLO11s-pose, 24 points) | image ↔ court position in feet |

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

Every threshold lives in `src/nextrun_cv/config.py`.

## Repo layout

```
src/
  nextrun_cv/       the CV pipeline (pip install -e . installs it)
    detect/           players.py, ball_hoop.py, ball_track.py
    court/            keypoints.py (court model), lines.py, manual.py, template.py (court geometry, 3PT), venues.py
    identity/         tagging, jersey colour re-linking, team clustering
    events/           possession, ball flights, analyzer.py (shots, rebounds, assists, ...)
    stats/            boxscore.py
    viz/              annotated video, shot chart, pass network
    integration.py    NextRun: all three models as one unit
    fusion.py         geometry between models (rim <-> court, feet -> court, ball -> holder)
    pipeline.py       stages: detect / calibrate / analyze / render
    api.py            FastAPI app (upload game -> stats)
    datasets.py       training-data tooling (downloads, group splits, homography-projected labels)
  scripts/          build_court_dataset.py, build_ball_rim_dataset.py, train.py, eval_court.py,
                    eval_ball_rim.py, score_events.py (event precision/recall vs hand labels)
  notebooks/        NextRun_Pipeline.ipynb (run a game), NextRun_Train.ipynb (retrain models): Colab, GPU
models/           ball_hoop_model.pt, court_model.pt, court_keypoints.json (court model geometry),
                  botsort_reid.yaml (tracker), README.md (court model notes); yolo26m-pose.pt downloads here
data/             venues/ (saved camera calibrations, tracked); datasets, raw downloads, videos (local only)
tests/            synthetic games for every event type + API + dataset tooling (no GPU needed)
results/          eval reports (tracked); runs/ (training runs) and games/ (processed games) stay local
```

## Run it

**Colab (GPU):** open `src/notebooks/NextRun_Pipeline.ipynb`, run top to bottom.

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

## Venues (one calibration per camera)
Cameras are fixed, so each gym / court is calibrated once and saved in `data/venues/<name>.json`: court type,
~6 clicked court landmarks, and optionally the playing area (e.g. a 3x3 half court) so spectators are
dropped. Every game from that camera then uses `--venue <name>`; the rim check still runs each game and
flags a camera that moved. Click points with `nextrun_cv.court.manual.colab_click_landmarks` (notebook)
and save with `nextrun_cv.court.venues.save_venue`.

## Improving the models
`src/notebooks/NextRun_Train.ipynb` (Colab GPU) rebuilds both datasets, scores the current model on every
domain, trains, scores again on the same test images and installs only if the new model is better
everywhere. Datasets:

| Model | Sources | Builder |
|---|---|---|
| Court (24 keypoints) | Rishabh's HS gym sets (Roboflow) · NBA broadcast (850 frames, HF, CC BY 4.0) · calibrated venue videos, auto-labelled through their homography: [TrackID3x3](https://github.com/open-starlab/TrackID3x3) outdoor (12 recordings) and indoor gym (42 clips); its drone footage (a different outdoor court) is held out as an unseen-court test | `src/scripts/build_court_dataset.py` |
| Ball + rim | 6 Roboflow Universe sets that label both ball and rim (`--roboflow suggested`) · 3 more via Hugging Face mirrors (`--hf suggested`, no key) · your labelled frames; ~10.8k unique frames, all CC BY 4.0 | `src/scripts/build_ball_rim_dataset.py` |

Splits are by video / game clip so near-duplicate frames can't inflate test scores. Downloading from
Roboflow needs a free `ROBOFLOW_API_KEY`.

Data details that matter:
- **Rim boxes = rim + net.** The pipeline's rim thresholds assume it; sets that box only the ring are extended
  down to a square (in scene proportions: exports stretched to 640x640 are measured on their round balls).
- **Fixed cameras move a little between recordings** (10-23 px on the outdoor 4K camera); each video is
  registered to the reference video before labelling. **Moving cameras** (venue `"fixed_camera": false`,
  e.g. the drone) are followed frame by frame and snapped onto the painted lines, so labels don't drift.
- **Fixed-camera test frames mostly measure memorisation** (same view as training); the drone court,
  never trained on, is the honest check for a new outdoor court.
- Court training warps frames into new viewpoints (perspective / rotation augmentation) so a few fixed
  cameras don't teach single views. Pause any training with Ctrl+C and continue with `--resume`.

Current court model, measured with `src/scripts/eval_court.py` (median position error):

| Domain | Found | Error |
|---|---|---|
| High-school gyms, corner + sideline (Rishabh's test set) | 96/97 | ~1.5 ft |
| NBA broadcast (test clips) | 63/94 | 6.6 ft |
| TrackID3x3 outdoor 3x3 half court | 28/30 | 18.6 ft — wrong; rejected by the rim check, use the venue profile |

## Development
```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows (.venv/bin on macOS/Linux)
pytest
```

## Known limits / next steps
- Fixed cameras only; a panning camera needs per-frame court calibration.
- Court model is trained on high-school gyms (corner + sideline views); retrain with the notebook above to
  cover broadcast / outdoor / half courts. Until then, venue profiles cover any fixed camera.
- Event rules are heuristic v1: label a few clips and tune `Config` with `src/scripts/score_events.py`.
- Ball model is YOLOv8n trained 25 epochs at 640 px; retrain (notebook) at 1280 px with the merged datasets.
- Tracker IDs fragment (e.g. 16 IDs for 6 players in 20 s of 3x3); tagging + jersey-colour re-linking merge them.
- Not detected yet: blocks, free throws, fouls.
