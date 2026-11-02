# Autotrain summary

Generated 2026-10-29 06:47:49. Scores are on the test splits; court error is in feet (lower is better), ball/rim are mAP50 (higher is better).

## court

- current model: `{'mean_median_ft': 32.33, 'min_found': 0.409, 'mean_capped_ft': 21.43, 'usable': {'nba_court_kp': 0.021, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 0.0, 'handheld_sportcenter': 0.0}}`
- court_synth **(installed)** (passes install rule): `{'mean_median_ft': 0.29, 'min_found': 1.0, 'mean_capped_ft': 2.1, 'usable': {'nba_court_kp': 0.989, 'venue_trackid3x3_drone': 1.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.063}}` synthetic views usable: `{'drone': 0.643, 'ground': 0.208, 'raised': 0.505}` handheld (SportCenter): `{'usable': 0.063, 'found': 0.179, 'median_ft': 7.54}`
- court_yolo26l (passes install rule): `{'mean_median_ft': 333.13, 'min_found': 0.0, 'mean_capped_ft': 11.15, 'usable': {'nba_court_kp': 1.0, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.0}}` synthetic views usable: `{'drone': 0.015, 'ground': 0.0, 'raised': 0.081}` handheld (SportCenter): `{'usable': 0.0, 'found': 0.057, 'median_ft': 14.2}`
- court_yolo26l_polish (passes install rule): `{'mean_median_ft': 333.15, 'min_found': 0.0, 'mean_capped_ft': 11.71, 'usable': {'nba_court_kp': 0.989, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.0}}` synthetic views usable: `{'drone': 0.02, 'ground': 0.006, 'raised': 0.099}` handheld (SportCenter): `{'usable': 0.0, 'found': 0.087, 'median_ft': 16.39}`
- court_yolo26m (passes install rule): `{'mean_median_ft': 16.23, 'min_found': 0.048, 'mean_capped_ft': 15.09, 'usable': {'nba_court_kp': 0.989, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.0}}` synthetic views usable: `{'drone': 0.01, 'ground': 0.006, 'raised': 0.099}` handheld (SportCenter): `{'usable': 0.0, 'found': 0.012, 'median_ft': 30.13}`
- court_yolo26m_hires1536 (passes install rule): `{'mean_median_ft': 333.14, 'min_found': 0.0, 'mean_capped_ft': 15.11, 'usable': {'nba_court_kp': 0.989, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.0}}` synthetic views usable: `{'drone': 0.02, 'ground': 0.012, 'raised': 0.117}` handheld (SportCenter): `{'usable': 0.0, 'found': 0.018, 'median_ft': 32.66}`
- court_finetune (passes install rule): `{'mean_median_ft': 12.71, 'min_found': 0.429, 'mean_capped_ft': 15.22, 'usable': {'nba_court_kp': 0.989, 'venue_trackid3x3_drone': 0.0, 'venue_trackid3x3_outdoor': 1.0, 'handheld_sportcenter': 0.0}}` synthetic views usable: `{'drone': 0.015, 'ground': 0.0, 'raised': 0.063}` handheld (SportCenter): `{'usable': 0.0, 'found': 0.024, 'median_ft': 37.42}`

Installed court_synth -> models/court_model.pt (previous kept as court_model.prev.pt).

## ball

- current model: `{'ball_map50': 0.428, 'rim_map50': 0.703, 'footage_ball': '65/149', 'footage_rim': '149/149', 'footage_ball_rate': 0.436241610738255, 'footage_rim_rate': 1.0}`
- ball_pseudo **(installed)** (passes install rule): `{'ball_map50': 0.918, 'rim_map50': 0.837, 'footage_ball': '100/149', 'footage_rim': '149/149', 'footage_ball_rate': 0.6711409395973155, 'footage_rim_rate': 1.0}`
- ball_yolo26m: `{'ball_map50': 0.921, 'rim_map50': 0.855, 'footage_ball': '66/149', 'footage_rim': '120/149', 'footage_ball_rate': 0.4429530201342282, 'footage_rim_rate': 0.8053691275167785}`
- ball_yolo26l: `{'ball_map50': 0.9, 'rim_map50': 0.876, 'footage_ball': '61/149', 'footage_rim': '147/149', 'footage_ball_rate': 0.40939597315436244, 'footage_rim_rate': 0.9865771812080537}`
- ball_yolo26s: `{'ball_map50': 0.911, 'rim_map50': 0.897, 'footage_ball': '48/149', 'footage_rim': '147/149', 'footage_ball_rate': 0.3221476510067114, 'footage_rim_rate': 0.9865771812080537}`
- ball_yolo26s_hires1280: `{'ball_map50': 0.869, 'rim_map50': 0.881, 'footage_ball': '39/149', 'footage_rim': '86/149', 'footage_ball_rate': 0.26174496644295303, 'footage_rim_rate': 0.5771812080536913}`

Installed ball_pseudo -> models/ball_hoop_model.pt (previous kept as ball_hoop_model.prev.pt).

## Full pipeline

`nextrun_cv run` on outdoor_0025_0045.mp4: exit 0, output in results/games/outdoor, log in results/autotrain/pipeline_outdoor.log.

## After finalize (manual, 07:05)

Pipeline fix: the ball/rim model now runs at most at 1920 px (`ModelConfig.ball_max_imgsz`), the resolution it was
judged at. At native 3840 the new model added a frame-sized false rim on the outdoor clip. Pipeline rerun:
rim/court agreement 10/10, court conf 0.62. Details in LOOP_NOTES.md.
