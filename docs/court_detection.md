# Court Detection (NextRun)

Finds basketball court keypoints in a camera frame, maps image pixels to real court
positions in feet (homography), draws the 3-point lines, and classifies positions as 2PT / 3PT.

> Merged into the main pipeline on `model_merge`: weights are `models/court_model.pt`, keypoint
> positions are `configs/court_keypoints.json`, and the detector lives in `nextrun_cv/court/keypoints.py`
> (court feet are converted to the pipeline's meters, origin at center court). Original standalone
> code + demo: `court-detection` branch / PR #2.

## Use in code
    from nextrun_cv.config import Config
    from nextrun_cv.court import template
    from nextrun_cv.court.keypoints import KeypointCourtEstimator
    cfg = Config()                                  # highschool court by default
    est = KeypointCourtEstimator(cfg.court, cfg.models.court_keypoint_weights, cfg.models.court_keypoint_config)
    calib = est.estimate(frame)                     # raises CourtNotFound if the court isn't found
    x_m, y_m = calib.image_to_court([(px, py)])[0]  # e.g. a player's feet
    template.three_line_distance((x_m, y_m), cfg.court)   # + outside (3PT) / - inside (2PT), meters

## Court coordinates
In `configs/court_keypoints.json`: x = across the court (0 = far sideline, 50 = near sideline), y = along the court
(0 = left baseline, 84 = right baseline). High-school court, 84 x 50 ft.
Positions were measured from the training labels, using the paint (12 ft wide, free-throw line at 19 ft) as reference.

## Keypoints (24)
| IDs | Left basket | IDs | Right basket |
|---|---|---|---|
| 0 / 5 | baseline corners (far / near) | 10 / 15 | same |
| 1 / 4 | corner-3 line meets baseline (far / near) | 11 / 14 | same |
| 2 / 3 | paint corners on baseline (far / near) | 12 / 13 | same |
| 6 / 7 | free-throw line ends (far / near) | 16 / 17 | same |
| 18 / 19 / 20 | 3-point arc: far wing / top / near wing | 21 / 22 / 23 | same |
| 8 / 9 | half-court line at far / near sideline | | |

## Accuracy
See Results below.

## Limitations
- Trained on high-school gym footage from two camera setups (elevated corner view, elevated sideline view). New camera angles may need more training data.
- Classifies **positions**, not shots: scoring a shot needs ball/hoop detection and player tracking.
- Feet = bottom of the person box; a jumping player's position is off while in the air.

## Data
- Roboflow basketball court keypoints dataset (forked; see the Roboflow project page for its license)
- "HS Basketball - Court Keypoints" by Ethan Liu, Roboflow Universe, CC BY 4.0

## Results (held-out test images)
| Test set | Court found | Pose mAP50 | Pose mAP50-95 | Mapping error, median (mean) |
|---|---|---|---|---|
| Corner view, 11 images | 10/11 | 0.995 | 0.90 | 1.27 ft (1.28 ft) |
| Side view, several gyms, 86 images | 86/86 | 0.995 | 0.91 | 1.45 ft (3.41 ft) |

- Mapping error = distance between where a labeled court point lands after the homography and its true court position.
- Side view: most frames are about 1.5 ft accurate; a few frames have large errors, which raises the mean.
- `CLOSE` = within 1.5 ft of the 3-point line, roughly the mapping error, so too close to call.
- Earlier single-view models failed on the camera angle they were not trained on. Training on both views fixed that.
