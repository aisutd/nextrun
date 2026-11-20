# Model evaluation results

Test-set results for every model the pipeline uses, copied from the `model_merge` branch (`results/`), where they
were produced on 2x RTX 6000 Ada with `src/scripts/eval_*.py` and Ultralytics `val`. `nextrun_cv.model_metrics`
reads these files and serves them at `GET /metrics` (the app's Model metrics screen). Inference speed on the machine
running the API is measured live by `POST /metrics/benchmark`.

| File | Source on model_merge | What |
|---|---|---|
| `ball_current_test.txt` | `results/ball_pseudo_test.txt` | installed ball + rim model (`ball_pseudo`), 8 labelled test sets |
| `ball_baseline_test.txt` | `results/ball_baseline_test.txt` | original YOLOv8n ball + rim model |
| `ball_current_train.csv` | `results/runs/ball/ball_pseudo/results.csv` | training curve (validation split) |
| `court_current_*test.txt` | `results/court_synth_*test.txt` | installed court model (`court_synth`): real, synthetic and handheld views |
| `court_baseline_test.txt` | `results/court_baseline_test.txt` | original YOLO11s court model |
| `court_current_train.csv` | `results/runs/court/court_synth/results.csv` | training curve (validation split) |
| `tracking_current.json` | `results/tracking_sportsmot_swB_A_noreid.json` | players: tuned tracker + court fusion + stitching, SportsMOT basketball val |
| `tracking_baseline.json` | `results/tracking_sportsmot.json` | players: first version (raw tracker) |
| `events_current.json` | `results/events_clips_v4c.json` | end-to-end events, 543 labelled NBA clips, current pipeline |
| `events_baseline.json` | `results/events_clips.json` | same clips, first pipeline version |

To refresh: re-run the evaluations and copy the new files over these names.
