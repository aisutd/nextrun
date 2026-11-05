"""Court training frames from the other TrackID3x3 drone flights (2-1 ... 6-1), labelled from the 1-1 calibration.

  python src/scripts/build_drone_extra.py --out data/court_drone_extra data/raw/trackid3x3/videos/drone/{2,3,4,5,6}-1.mov

The venue points (data/venues/trackid3x3_drone.json) were picked on frame 300 of 1-1.mov. Each other flight is
registered to that frame: the flight's frame with the most background-feature inliers (camera_shift) gives a
first homography, snapped onto the painted lines (refine_to_court_lines); from there the camera is followed
frame to frame like build_court_dataset.py does for moving cameras. Flights that don't register (another court)
are skipped. 1-1 itself stays the unseen drone test set; these frames go to train/ as venue_trackid3x3_droneX.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_court_dataset import labels_from_homography  # noqa: E402
from nextrun_cv.court.base import homography_from_landmarks  # noqa: E402
from nextrun_cv.court.venues import load_venue  # noqa: E402
from nextrun_cv.datasets import camera_shift, refine_to_court_lines  # noqa: E402

VENUE = "trackid3x3_drone"


def read(cap, i):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read()
    return f if ok else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="data/court_drone_extra")
    ap.add_argument("--ref", default="data/raw/trackid3x3/videos/drone/1-1.mov")
    ap.add_argument("--ref-frame", type=int, default=300)
    ap.add_argument("--every", type=int, default=90)
    ap.add_argument("--min-ecc", type=float, default=0.5)
    a = ap.parse_args()
    out = Path(a.out)
    for sub in ("images", "labels"):
        (out / "train" / sub).mkdir(parents=True, exist_ok=True)
    ref = read(cv2.VideoCapture(a.ref), a.ref_frame)
    rh, rw = ref.shape[:2]
    spec, pts = load_venue(VENUE, (rw, rh))
    H_ref = np.linalg.inv(homography_from_landmarks(pts, spec, "venue", ransac_px=6).H)  # court -> ref image

    for video in a.videos:
        cap = cv2.VideoCapture(video)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        best = (0, None, None)
        for i in range(0, n, max(n // 40, 1)):  # find the frame that looks most like the reference view
            f = read(cap, i)
            if f is None or f.shape != ref.shape:
                continue
            Hs, inl = camera_shift(ref, f)
            if Hs is not None and inl > best[0]:
                best = (inl, i, Hs)
        inl, start, Hs = best
        if start is None or inl < 100:
            print(f"{video}: doesn't register to the reference ({inl} inliers), skipped")
            continue
        H, cc = refine_to_court_lines(Hs @ H_ref, read(cap, start), spec)
        if cc < a.min_ecc:
            print(f"{video}: court lines not found at frame {start} (ECC {cc:.2f}), skipped")
            continue
        added = skipped = 0
        stem = Path(video).stem
        # follow the camera forward from the registered frame, then backward from it
        for order in (range(start, n, a.every), range(start - a.every, -1, -a.every)):
            Hc, prev = H, read(cap, start)
            for i in order:
                frame = read(cap, i)
                if frame is None:
                    break
                if i != start:
                    Hm, _ = camera_shift(prev, frame)
                    H_new, cc = refine_to_court_lines(Hm @ Hc if Hm is not None else Hc, frame, spec)
                    prev = frame
                    if cc < a.min_ecc:
                        skipped += 1
                        continue
                    Hc = H_new
                h, w = frame.shape[:2]
                line = labels_from_homography(np.linalg.inv(Hc), spec, w, h)
                if line is None:
                    skipped += 1
                    continue
                if max(w, h) > 1920:
                    s = 1920 / max(w, h)
                    frame = cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
                name = f"venue_{VENUE}X__{stem}_{i:06d}"
                cv2.imwrite(str(out / "train" / "images" / f"{name}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                (out / "train" / "labels" / f"{name}.txt").write_text(line + "\n")
                added += 1
        print(f"{video}: registered at frame {start} ({inl} inliers, ECC {cc:.2f}); {added} frames, {skipped} skipped")


if __name__ == "__main__":
    main()
