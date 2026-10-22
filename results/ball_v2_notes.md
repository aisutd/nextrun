# Ball/rim v2 (CPU, 2 epochs @ 640 px) — not installed

Fine-tuned from models/ball_hoop_model.pt on data/ball_rim (8.4k train frames, 9 sets), 2 epochs on CPU
(the run was cut short by the time budget and a low-memory stop). Weights: results/runs/ball/ball_v2/weights/best.pt (local).

Labelled test split (results/ball_v2_test.txt vs results/ball_baseline_test.txt, eval at 1280 px):
ball mAP50 up on 6 of 8 sets (phone/gym 0.62 -> 0.85, NBA player-detection 0.34 -> 0.65, 3x3 broadcast 0.01 -> 0.09);
rim mAP50 down on basketball_and_hoops (0.41 -> 0.19, augmented stock photos) and flat elsewhere.

Our footage (TrackID3x3 outdoor + indoor, 60 frames at native resolution, conf 0.3):
frames with a ball found: old 46/60, new 24/60; rim found 60/60 for both. Median top ball confidence
0.62 (old) vs 0.27 (new), and new false positives (a box on a player's shorts next to the ball, one on a building).

Decision: keep the current ball model. The new data is fine; the training was too short and at too low a
resolution for small, distant balls. Next: src/notebooks/NextRun_Train.ipynb on a GPU at 1280 px, ~100 epochs.
