"""Court keypoint detection -> homography -> court position (ft) -> 2PT / 3PT.
Model: YOLO11n-pose, 13 court keypoints (high-school half court). Usage at the bottom."""
import numpy as np, cv2
from ultralytics import YOLO

# Court positions (ft) of the reliable keypoints, measured from the dataset labels.
# x = along the baseline (0-50), y = from the baseline toward half court.
COURT_FT = {3: (19, 0), 4: (31, 0), 5: (31, 19), 6: (19, 19),
            7: (6.8, 1.4), 8: (9.1, 16.8), 9: (24.5, 25.2), 10: (39.9, 19.7), 11: (47.7, 6.6)}
USE_IDS = list(COURT_FT)              # IDs 0, 1, 2, 12 (corners/sideline) are unreliable, skipped
ARC_IDS = [7, 8, 9, 10, 11]           # points on the 3-point line
MARGIN_FT = 1.5                       # mapping error; closer than this to the line = "CLOSE"

# 3-point arc fitted through the arc keypoints
_p = np.array([COURT_FT[i] for i in ARC_IDS], float)
_cx, _cy, _c = np.linalg.lstsq(np.c_[2 * _p, np.ones(len(_p))], (_p ** 2).sum(1), rcond=None)[0]
ARC_CENTER, ARC_RADIUS = (float(_cx), float(_cy)), float(np.sqrt(_c + _cx ** 2 + _cy ** 2))


class CourtDetector:
    def __init__(self, weights='last.pt', conf_th=0.5):
        self.model = YOLO(weights)
        self.conf_th = conf_th

    def homography(self, frame):
        """Return H mapping image pixels -> court feet, or None if the court isn't found."""
        r = self.model.predict(frame, conf=0.25, verbose=False)[0]
        if r.keypoints is None or len(r.boxes) == 0:
            return None
        b = int(r.boxes.conf.argmax())
        xy, kc = r.keypoints.xy[b].cpu().numpy(), r.keypoints.conf[b].cpu().numpy()
        ids = [i for i in USE_IDS if kc[i] > self.conf_th]
        if len(ids) < 4:
            return None
        H, _ = cv2.findHomography(np.float32([xy[i] for i in ids]),
                                  np.float32([COURT_FT[i] for i in ids]), cv2.RANSAC, 1.5)
        return H

    @staticmethod
    def to_court(H, points_px):
        """Image pixels [(x, y), ...] -> court feet [(x_ft, y_ft), ...]."""
        pts = np.float32(points_px).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, H).reshape(-1, 2)

    @staticmethod
    def shot_zone(x_ft, y_ft):
        """Court position (ft) -> '2PT', '3PT' or 'CLOSE'."""
        d = np.hypot(x_ft - ARC_CENTER[0], y_ft - ARC_CENTER[1]) - ARC_RADIUS
        if abs(d) < MARGIN_FT:
            return 'CLOSE'
        return '3PT' if d > 0 else '2PT'


if __name__ == '__main__':
    # Example: classify where a player is standing (feet = bottom-center of their box)
    det = CourtDetector('last.pt')
    frame = cv2.imread('example.jpg')
    H = det.homography(frame)
    if H is not None:
        x_ft, y_ft = det.to_court(H, [(640, 500)])[0]          # replace with a player's foot pixel
        print(f"Court position: ({x_ft:.1f}, {y_ft:.1f}) ft ->", det.shot_zone(x_ft, y_ft))
