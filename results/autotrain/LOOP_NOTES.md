# Overnight loop notes (2026-10-29)

Goal: best court and ball/rim models installed in models/ by ~08:00 CDT. autotrain.py runs the search;
these notes record what was checked and changed.

## 00:16 — first check

- Running: ball_yolo26m (GPU 1, ep 37/120), court_yolo26l (GPU 1, ep 84/200), ball_yolo26s (GPU 0, ep 28/80),
  ball_yolo26l (GPU 0, ep 10/80). Scored: court_yolo26m, court_finetune.
- Both court candidates were blocked by the install rule only on the TrackID3x3 drone test set.

## Drone court investigation

- Ground truth is fine: drew the drone test labels on frames 300 / 18300, every point sits on the painted lines.
- The models simply don't generalise to the high drone view: court_yolo26m detects 2/42 frames, the current
  model "finds" 22/42 but with a 71 ft median error, i.e. a wrong court. The old rule (found rate >= current)
  therefore rewarded wrong courts and blocked a model that is 0.2 ft on NBA and 0.15 ft on outdoor.
- Only one drone flight (1-1.mov) exists and it is the test set, so no drone training data without
  changing what the test means (left for the user to decide).

## Changes (nothing committed)

- eval_court.py: also reports `usable` / `good_rate` = images whose own median error is <= 3 ft (`--good-ft`).
- autotrain.py:
  - court install rule compares usable rate instead of found rate (median error rule unchanged);
  - court ranking = mean median error capped at 30 ft + 30 ft x (1 - mean usable rate), so a wrong drone court
    doesn't decide the ranking (before, the ranking preferred court_finetune over court_yolo26m);
  - old court reports and the current model rescored with the new metric;
  - new candidate court_yolo26m_aug: harder warps (perspective 0.0015, degrees 10, scale 0.7) aimed at the drone view;
  - deadline: nothing starts after 06:45, new runs get a train.py `--hours` budget when their estimated time
    would overrun it, and at 07:30 unfinished runs are scored as they stand and the winners installed;
  - refinement no longer waits for every candidate of its task to finish (it would never have started).
- train.py: `--aug KEY=VALUE` overrides an augmentation setting.
- state.json backed up to state.before_loop.json; manager restarted (training runs untouched).

Rescored (usable rate per test source; NBA / drone / outdoor):

| model | usable | median ft | passes rule |
|---|---|---|---|
| current models/court_model.pt | 0.02 / 0.00 / 0.00 | 6.56 / 71.2 / 19.2 | — |
| court_yolo26m | 0.99 / 0.00 / 1.00 | 0.21 / 48.3 / 0.15 | yes |
| court_finetune | 0.99 / 0.00 / 1.00 | 0.53 / 77.0 / 0.35 | no (drone median 77 > 71) |

## 01:05–01:56 — synthetic + real data for community camera views

User asked for models that work from any community camera (drone, phone on the ground, sideline, partial
court), then player tracking through overlaps / exits, and box-score stats (points, rebounds, assists).

- New `src/scripts/synth_court.py`: exact-label synthetic court images. Two modes:
  rendered courts (FIBA / NBA / HS, random surfaces, neighbouring courts, hoops, people, poles, skyline) and
  real court24 train frames re-projected to new cameras. Cameras: 40 % ground/handheld 0.2-2 m (incl. portrait,
  wide lenses, partial views >= 4 keypoints), 25 % raised 2.5-8 m, 35 % drone 8-35 m. Labels follow the real
  sets' conventions (handedness + view direction d_x > d_y, which holds for 1023/1024 real labels).
  - data/court24s = court24 + 3600 synthetic train images (val/test unchanged).
  - data/court_synth_test = 480 held-out synthetic views (rewarps from court24 *test* images; drone never used).
- New candidate `court_synth`: court_yolo26m fine-tuned on court24s, lr0 0.002, harder warps, 80 epochs.
  court_yolo26m_aug skipped (superseded).
- Real handheld data: EPFL SportCenter (two moving phones, amateur gym game, per-frame homography; research use
  only). New `src/scripts/build_sportcenter.py` -> data/court_sportcenter (test 492 / train 653, dataset's own
  split). Gym court measured from its template: 24.12 x 13.36 m, FIBA markings, arc hits the sidelines.
  Kept as a *test* (licence + it's our only real handheld test); not trained on.
- autotrain: court candidates are also scored on the synthetic views and SportCenter (reported, not part of the
  install rule); scoring falls back to the other GPU, then CPU, on OOM (an early ball check hit CUDA OOM).

Baselines (usable = per-image median error <= 3 ft):

| model | SportCenter handheld | synth drone | synth ground | synth raised |
|---|---|---|---|---|
| current court model | 0/492 (found 16) | 0/196 | 0/173 | 0/111 |
| court_yolo26m | 0/492 (found 6) | 2/196 | 1/173 | 11/111 |

So no court model works from handheld/ground/drone views yet; that is what court_synth targets.

- Tracking ground truth: TrackID3x3 Google Drive (CC BY 4.0) has boxes + identities for all 6 players in every
  frame (indoor / outdoor / drone). Listing the folder to fetch only the annotations.

## 02:20–02:30

- ball_yolo26s scored: test ball mAP50 0.911 / rim 0.897 (current 0.428 / 0.703) but footage ball 48/149 vs 99/149.
  Looked at the disagreement frames: in the indoor clips the current model's confident "ball" is a static object
  at the left frame edge, in nearly every frame (spare ball / fixture), not the ball in play. Both models find the
  real ball at lower confidence. check_ball_footage.py now ignores spots seen in >= 40 % of a video's sampled
  frames ("ball_found"; "ball_found_all" keeps the old count). Current model: 65/149 (was 99), ball_yolo26s 48/149
  either way. So the gap is real but smaller: the ball is ~10 px in 4K wide shots and the s model trains at 1024.
  The queued refinement ball_yolo26s_hires1280 targets exactly that; MAX_PER_GPU 2 -> 3 so it can start on GPU 0
  now (otherwise it would never get a slot before the deadline). Ball models rescored with the new footage count.
- Drone: the TrackID3x3 Drive has 5 more drone flights (2-1 ... 6-1). New `src/scripts/build_drone_extra.py`
  registers a flight to the hand-calibrated 1-1 frame 300 and follows the camera. 2-1 worked (same court complex,
  378 frames, labels checked visually); 3-1 ... 6-1 didn't register / snap (other courts or views: would need
  hand-picked points like 1-1). 2-1 frames added to data/court24s train (court_synth). Note: the 1-1 drone test
  is now "same venue, different flight", an easier test than before.
- Tracking ground truth: not in the public Drive folder (only the authors' tracker outputs); the hand-labelled
  boxes probably need a request to the authors. Tracking evaluation postponed.

## 02:49

- court_synth started 02:28 on GPU 0 (data/court24s incl. all 378 drone-2-1 frames), time budget 4.3 h -> ~06:45.
- court_yolo26l finished: usable NBA 1.00 / outdoor 1.00 / drone 0 (finds no drone court at all). It failed the
  install rule only because "no drone median" counted as worse than the current model's 71 ft (wrong-court) median.
  Fix: median error is compared only where the current model is usable on >= 10 % of images; the usable-rate check
  still covers every source. All three court models now pass.
- Ranking now also counts the real handheld SportCenter test (usable rate + capped median) like another source;
  the install rule is unchanged (the synthetic test stays report-only: it shares the generator with court_synth).
  All of them: handheld usable 0.0 so far.
- court refinement court_yolo26m_hires1536 took the GPU 1 slot (~1 h); the ball refinement starts after it.

## 03:34–03:50 — court_synth early check, estimator fix

- court_synth epoch 13 (of ~51 in its 4.3 h budget), raw eval: drone 42/42 usable at 1.05 ft (was 0/42), synthetic
  views usable drone 49/196, raised 24/111, ground 5/173 (court_yolo26m: 2, 11, 1), but outdoor fell to 9/22 at
  56 ft. Cause (debugged on frames): on the single-basket 3x3 view the model labels some points as their 180-degree
  partners (3 for 12, 7 for 16, 20 for 21, ...): which basket it faces is ambiguous from one half.
- Fix in the pipeline's KeypointCourtEstimator (src/nextrun_cv/court/keypoints.py), helps every court model:
  1. fold_to_one_half: when a prediction mixes both halves, also fit with the minority half moved to its
     partners; keep the more consistent fit (higher fit confidence);
  2. views_along_convention: after fitting, if the camera's floor view direction breaks the labelling
     convention (d_x > d_y), the baskets are swapped: refit with the 180-degree partner ids.
  court_synth epoch 13 after the fix: NBA 93/94 (0.88 ft), drone 42/42 (1.08 ft), outdoor 22/22 (1.47 ft).
  court_yolo26m / current model unchanged (no regressions). Unit tests added (tests/test_court.py); suite: 49 pass,
  1 fail = test_lines_auto_from_scratch, which fails the same way without this change (pre-existing, line method).
- Baseline + all court models rescored with the fixed estimator.
- Real handheld SportCenter: still 0/492 usable for every model, court_synth included (detection confidence
  0.06-0.16, keypoints pulled onto other sports' lines: the gym has basketball + volleyball/handball markings in
  several colours, close-up views). Next round: synthetic multi-sport line clutter, and/or train on the SportCenter
  train split if its research-only licence is acceptable.

## 04:32–04:45 — ball footage gap, pseudo-labels

- ball_yolo26l (early-stopped ep 58): test ball 0.900 / rim 0.876, footage ball 61/149, rim 147/149 (current 65 / 149).
- ball_yolo26m (early-stopped ep 100): test ball 0.921 / rim 0.855, footage ball 66/149 (passes), rim 120/149 (fails).
- Looked at the 22 frames where the current model finds a moving ball and ball_yolo26l doesn't: ~19 are real balls
  (clear balls on grass, balls in hands; ball_yolo26l gives them 0.00-0.26), 2-3 are wall spots. So the new models
  have a genuine domain gap on wide community footage despite ~2x better labelled-test scores.
- New `src/scripts/pseudo_label_ball.py`: frames from every TrackID3x3 video except the 5 footage-check videos,
  labelled with ball/rim boxes >= 0.5 from the current model + ball_yolo26l (merged, static spots dropped, only
  frames with a confident ball). 509 frames, x3 oversampled -> data/ball_rim_pl (ball_rim + 1527 pseudo).
- New candidate ball_pseudo: ball_yolo26l fine-tuned on ball_rim_pl, lr0 0.002, time budget to 06:45.
- court_yolo26m_hires1536 scored (no better than its parent); last court refinement court_yolo26l_polish running.

## 05:13 — mid-training checks

- ball_pseudo (started 04:45, epoch 4): footage ball 95/149, rim 149/149 (current 65 / 149, ball_yolo26l 61 / 147).
- court_synth epoch 34: NBA 93/94 at 0.52 ft, drone 42/42 at 0.45 ft, outdoor 22/22 at 0.47 ft, real handheld
  SportCenter 15/492 usable (median 10.5 ft; every other model 0/492).
- Both end ~06:45 and are scored automatically; finalize/install at 07:30.

## 06:45–07:05 — finalized, installed, verified

- autotrain finished everything early and finalized at 06:49 (results/autotrain/SUMMARY.md):
  - court: **court_synth installed** -> models/court_model.pt (old one kept as court_model.prev.pt).
    Usable: NBA 93/94, drone 42/42, outdoor 22/22 (median errors 0.2-0.5 ft); synthetic views drone 64 %,
    raised 51 %, ground 21 %; real handheld SportCenter 6.3 % (31/492, median 7.5 ft). Current model was 2 % / 0 / 0.
  - ball: **ball_pseudo installed** -> models/ball_hoop_model.pt (old kept as ball_hoop_model.prev.pt).
    Test ball mAP50 0.918 (was 0.428), rim 0.837 (was 0.703), footage ball 100/149 (was 65), rim 149/149.
- Verified: installed files are byte-identical to the runs' best.pt (md5); full pipeline on the outdoor clip exits 0.
- Found and fixed in the pipeline: the ball detector ran at the frame's native size (3840 on 4K). The new ball
  model (trained at 1024, judged at <= 1920) then reports a frame-sized false "rim", which halved the rim check's
  agreement with the court calibration (court conf 0.62 -> 0.39). New ModelConfig.ball_max_imgsz = 1920
  (players keep native size). After: rim agreement 10/10, court conf 0.62. Tests: 49 pass, 1 pre-existing failure.
- Not done / next:
  - Stats accuracy (points / rebounds / assists) can't be measured: there are no labelled events
    (src/scripts/score_events.py expects labels/<clip>.json). Label one or two clips to get real numbers.
  - Tracking ID-switch evaluation: TrackID3x3's ground-truth boxes aren't in its public Drive (only the authors'
    tracker outputs); ask the authors, or use SportsMOT / TeamTrack basketball.
  - Handheld indoor gyms with multi-sport markings are still weak (6 %): next round, synthetic multi-sport line
    clutter, and/or SportCenter train split if its research-only licence is OK.
  - Drone flights 3-1 ... 6-1 need hand-picked calibration points (other courts) to become training data.
- Nothing committed.
