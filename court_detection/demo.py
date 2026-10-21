"""Demo:  python demo.py --source game.mp4 --output out.mp4     (or --source frame.jpg)"""
import argparse
import cv2
import numpy as np
from ultralytics import YOLO
from court_detector import CourtDetector

COLORS = {'2PT': (214, 120, 42), '3PT': (52, 104, 235), 'CLOSE': (160, 160, 160)}   # blue, orange, gray
YELLOW, WHITE = (0, 215, 255), (255, 255, 255)


def minimap(det, players, scale=6, m=10):
    W, L = det.W, det.L
    img = np.full((int(W * scale) + 2 * m, int(L * scale) + 2 * m, 3), (80, 140, 190), np.uint8)
    P = lambda x, y: (int(m + y * scale), int(m + x * scale))
    cv2.rectangle(img, P(0, 0), P(W, L), WHITE, 2)
    cv2.line(img, P(0, L / 2), P(W, L / 2), WHITE, 2)
    for y0, y1 in [(0, 19), (L, L - 19)]:
        cv2.rectangle(img, P(19, y0), P(31, y1), WHITE, 2)
    for line in det.three_point_lines_ft():
        cv2.polylines(img, [np.int32([P(x, y) for x, y in line])], False, YELLOW, 2)
    for (x, y), z in players:
        cv2.circle(img, P(x, y), 6, COLORS[z], -1)
    return img


def annotate(frame, det, H, person_model):
    out, players = frame.copy(), []
    if H is not None:
        det.draw_three_point_lines(out, H)
        boxes = person_model.predict(frame, classes=[0], conf=0.4, verbose=False)[0].boxes.xyxy.cpu().numpy()
        for b in boxes:
            x, y = det.to_court(H, [((b[0] + b[2]) / 2, b[3])])[0]       # feet = bottom-center of the box
            if not (0 <= x <= det.W and 0 <= y <= det.L):
                continue                                                 # off the court (bench, fans)
            z = det.shot_zone(x, y)
            players.append(((x, y), z))
            c = COLORS[z]
            cv2.rectangle(out, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), c, 2)
            cv2.putText(out, z, (int(b[0]), int(b[1]) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, 2)
    mm = minimap(det, players)
    h, w = out.shape[:2]
    s = min(0.35 * w / mm.shape[1], 1.0)
    mm = cv2.resize(mm, (int(mm.shape[1] * s), int(mm.shape[0] * s)))
    out[h - mm.shape[0] - 10:h - 10, w - mm.shape[1] - 10:w - 10] = mm
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--output', default='demo_out')
    ap.add_argument('--weights', default='weights/court_model.pt')
    ap.add_argument('--config', default='court_config.json')
    ap.add_argument('--every', type=int, default=5, help='re-detect the court every N video frames')
    a = ap.parse_args()

    det, person = CourtDetector(a.weights, a.config), YOLO('yolo11n.pt')
    if a.source.lower().endswith(('.jpg', '.jpeg', '.png')):
        frame = cv2.imread(a.source)
        out = annotate(frame, det, det.homography(frame), person)
        path = a.output if a.output.lower().endswith(('.jpg', '.png')) else a.output + '.jpg'
        cv2.imwrite(path, out)
        print('Saved', path)
        return

    cap = cv2.VideoCapture(a.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    path = a.output if a.output.endswith('.mp4') else a.output + '.mp4'
    writer, H, n = None, None, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if n % a.every == 0:
            H_new = det.homography(frame)
            if H_new is not None:
                H = H_new
        out = annotate(frame, det, H, person)
        if writer is None:
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (out.shape[1], out.shape[0]))
        writer.write(out)
        n += 1
    cap.release()
    if writer:
        writer.release()
    print(f'Saved {path} ({n} frames)')


if __name__ == '__main__':
    main()
