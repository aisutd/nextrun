# Court Detection (NextRun)

Finds basketball court keypoints in a camera frame, maps image pixels to real court
positions in feet (homography), draws the 3-point lines, and classifies positions as 2PT / 3PT.

## Files
| File | What it is |
|---|---|
| `weights/court_model.pt` | YOLO11s-pose model, 24 court keypoints |
| `court_config.json` | Court position (ft) of each keypoint, 3-point line geometry |
| `court_detector.py` | `CourtDetector` class: keypoints, homography, court position, 2PT/3PT |
| `demo.py` | Runs everything on an image or video and draws the result |

## Install
    pip install -r requirements.txt

## Use in code
    from court_detector import CourtDetector
    det = CourtDetector('weights/court_model.pt', 'court_config.json')
    H = det.homography(frame)                    # None if the court isn't found
    x_ft, y_ft = det.to_court(H, [(px, py)])[0]  # e.g. a player's feet or the ball
    det.shot_zone(x_ft, y_ft)                    # '2PT', '3PT' or 'CLOSE'
    det.draw_three_point_lines(frame, H)

## Demo
    python demo.py --source game.mp4 --output out.mp4
    python demo.py --source frame.jpg --output out.jpg

## Court coordinates
x = across the court (0 = far sideline, 50 = near sideline), y = along the court
(0 = left baseline, 84 = right baseline). High-school court, 84 x 50 ft.
Positions in `court_config.json` were measured from the training labels, using the paint (12 ft wide, free-throw line at 19 ft) as reference.

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
See RESULTS section below (filled in after evaluation).

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
