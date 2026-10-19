"""NextRun court detection.

Image -> 24 court keypoints (YOLO11s-pose) -> homography -> court position in feet -> 2PT / 3PT.
Court frame (feet): x across the court (0 = far sideline, 50 = near sideline),
                    y along the court (0 = left baseline, 84 = right baseline).
"""
import json
import numpy as np
import cv2
from ultralytics import YOLO


class CourtDetector:
    def __init__(self, weights='weights/court_model.pt', config='court_config.json', conf_th=0.5):
        self.model = YOLO(weights)
        cfg = json.load(open(config))
        self.L, self.W = cfg['court_length_ft'], cfg['court_width_ft']
        self.kp_ft = {int(k): v for k, v in cfg['keypoints_ft'].items() if v is not None}
        self.use_ids = cfg['use_ids']
        tp = cfg['three_point']
        self.cx, self.cy = tp['center']
        self.R = tp['radius']
        self.xc1, self.xc2 = tp['corner_x']
        self.margin = cfg['margin_ft']
        self.conf_th = conf_th

    def keypoints(self, frame):
        """(xy [24 x 2] pixels, confidence [24]) of the best court detection, or (None, None)."""
        r = self.model.predict(frame, conf=0.25, verbose=False)[0]
        if r.keypoints is None or len(r.boxes) == 0:
            return None, None
        b = int(r.boxes.conf.argmax())
        return r.keypoints.xy[b].cpu().numpy(), r.keypoints.conf[b].cpu().numpy()

    def homography(self, frame):
        """3x3 matrix mapping image pixels -> court feet, or None if the court isn't found."""
        xy, kc = self.keypoints(frame)
        if xy is None:
            return None
        ids = [i for i in self.use_ids if i in self.kp_ft and kc[i] > self.conf_th]
        if len(ids) < 4:
            return None
        H, _ = cv2.findHomography(np.float32([xy[i] for i in ids]),
                                  np.float32([self.kp_ft[i] for i in ids]), cv2.RANSAC, 1.5)
        return H

    @staticmethod
    def to_court(H, points_px):
        """Image pixels [(x, y), ...] -> court feet [(x_ft, y_ft), ...]."""
        pts = np.float32(points_px).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, H).reshape(-1, 2)

    def _join_y(self, xc):
        return self.cy + np.sqrt(max(self.R ** 2 - (xc - self.cx) ** 2, 0.0))

    def distance_to_three_point_line(self, x_ft, y_ft):
        """Signed distance (ft) to the nearer basket's 3-point line: + outside (3PT), - inside (2PT)."""
        y = y_ft if y_ft <= self.L / 2 else self.L - y_ft
        xc = self.xc1 if x_ft < self.cx else self.xc2
        if y < self._join_y(xc):                       # corner: straight line
            return max(self.xc1 - x_ft, x_ft - self.xc2)
        return float(np.hypot(x_ft - self.cx, y - self.cy) - self.R)

    def shot_zone(self, x_ft, y_ft):
        """'2PT', '3PT', or 'CLOSE' (within margin_ft of the line, too close to call)."""
        d = self.distance_to_three_point_line(x_ft, y_ft)
        if abs(d) < self.margin:
            return 'CLOSE'
        return '3PT' if d > 0 else '2PT'

    def three_point_lines_ft(self, n=100):
        """Both 3-point lines as polylines in court feet: [left, right]."""
        y1, y2 = self._join_y(self.xc1), self._join_y(self.xc2)
        a1 = np.arctan2(y1 - self.cy, self.xc1 - self.cx)
        a2 = np.arctan2(y2 - self.cy, self.xc2 - self.cx)
        arc = [(self.cx + self.R * np.cos(a), self.cy + self.R * np.sin(a)) for a in np.linspace(a1, a2, n)]
        left = np.array([(self.xc1, 0.0)] + arc + [(self.xc2, 0.0)], float)
        right = left.copy()
        right[:, 1] = self.L - right[:, 1]
        return [left, right]

    def draw_three_point_lines(self, frame, H, color=(0, 215, 255), thickness=3):
        """Draw both 3-point lines onto the camera image (in place)."""
        h, w = frame.shape[:2]
        Hinv = np.linalg.inv(H)
        ref = self.to_court(H, [(w / 2, h - 1)])[0]                   # a floor point surely in view
        ref_sign = np.sign((Hinv @ [ref[0], ref[1], 1.0])[2])
        for line in self.three_point_lines_ft():
            P = np.c_[line, np.ones(len(line))] @ Hinv.T
            ok = np.sign(P[:, 2]) == ref_sign                        # drop points "behind" the camera
            px = P[:, :2] / P[:, 2:3]
            run = []
            for p, good in zip(px, ok):
                if good and np.all(np.abs(p) < 1e5):
                    run.append(p)
                else:
                    if len(run) > 1:
                        cv2.polylines(frame, [np.int32(run)], False, color, thickness)
                    run = []
            if len(run) > 1:
                cv2.polylines(frame, [np.int32(run)], False, color, thickness)
        return frame
