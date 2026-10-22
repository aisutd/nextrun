"""Build one court-keypoint training set in the court model's 24-point format from every source available.

  python src/scripts/build_court_dataset.py --out data/court24 \
      --roboflow WORKSPACE/PROJECT[/VERSION] ...        # 24-point YOLO-pose sets (Rishabh's); ROBOFLOW_API_KEY
      --yolo-dir PATH ...                                # same, from a local export
      --nba-hf                                           # public NBA broadcast set (850 frames, CC BY 4.0, Hugging Face)
      --landmarks-dir PATH --landmarks-court nba         # any set labelled with template landmarks
      --venue trackid3x3_outdoor 'data/videos/outdoor*.mp4' --every 30   # calibrated fixed camera(s)

Every non-24-point source is converted the same way: fit the image->court homography, then project the
24 keypoints (positions for that court type, court.keypoints.keypoints_for_court). Splits are by group
(video / game clip / source image) so near-identical frames never straddle train and test.
Writes out/data.yaml, out/sources.json (counts per source and split) and out/lists/ (per-source image lists
for per-domain evaluation).
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT, CourtSpec  # noqa: E402
from nextrun_cv.court import template  # noqa: E402
from nextrun_cv.court.base import CourtNotFound, homography_from_landmarks  # noqa: E402
from nextrun_cv.court.keypoints import keypoints_for_court, load_keypoint_config  # noqa: E402
from nextrun_cv.court.venues import load_venue  # noqa: E402
from nextrun_cv.datasets import (  # noqa: E402
    YoloWriter, camera_shift, iter_yolo_export, refine_to_court_lines, pose_label, project_keypoints, read_data_yaml, roboflow_download, source_group,
)

KP_CONFIG = REPO_ROOT / "models" / "court_keypoints.json"
N_KP = 24


def labels_from_homography(H_img_to_court: np.ndarray, spec: CourtSpec, w: int, h: int) -> str | None:
    kp = load_keypoint_config(KP_CONFIG)
    court = keypoints_for_court(kp, spec)
    return pose_label(project_keypoints(np.linalg.inv(H_img_to_court), court, N_KP, w, h), w, h)


def add_yolo24(writer: YoloWriter, root: Path, source: str) -> None:
    meta = read_data_yaml(root)
    if list(meta.get("kpt_shape", [])) != [N_KP, 3]:
        raise SystemExit(f"{root}: kpt_shape {meta.get('kpt_shape')} is not [24, 3] (court-model format)")
    for _, img, lbl in iter_yolo_export(root):
        if lbl.exists():
            writer.add(source, source_group(img.name), img.name, img, lbl.read_text().strip().splitlines())


def landmark_names(root: Path) -> list[str]:
    """Keypoint order of a template-landmark set, from the '#  i: name' comments in its yaml."""
    import re

    text = next(p for p in (root / "court.yaml", root / "data.yaml") if p.exists()).read_text()
    names = dict((int(i), n) for i, n in re.findall(r"#\s*(\d+):\s*(\S+)", text))
    return [names[i] for i in range(len(names))]


def add_landmark_set(writer: YoloWriter, root: Path, spec: CourtSpec, source: str) -> None:
    import json

    names = landmark_names(root)
    original = {}
    if (root / "source_names.json").exists():  # original clip names -> group by game clip
        original = json.loads((root / "source_names.json").read_text())
    valid = set(template.landmarks(spec))
    skipped = 0
    for _, img, lbl in iter_yolo_export(root):
        if not lbl.exists():
            continue
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        vals = np.array(lbl.read_text().split()[5:], float).reshape(-1, 3)
        pairs = {n: (x * w, y * h) for n, (x, y, v) in zip(names, vals) if v > 0 and n in valid}
        try:
            H = homography_from_landmarks(pairs, spec, "label", ransac_px=0.3).H
        except (CourtNotFound, ValueError):
            skipped += 1
            continue
        line = labels_from_homography(H, spec, w, h)
        if line is None:
            skipped += 1
            continue
        group = source_group(original.get(img.stem, img.name))
        writer.add(source, group, img.name, img, [line])
    print(f"{source}: skipped {skipped} images without a usable homography")


# basketball-court-detection-2 (Roboflow Universe, CC BY 4.0), Hugging Face mirror; 48 keypoints per frame.
NBA_HF_REPO = "koppolusameer/basketball-keypoint-detection-yolov8"
# dataset keypoint index -> template landmark (from the dataset's flip_idx + visual checks; verified by
# homography residuals of 2-4 px on 1920x1080). Unlisted indices are unused.
_NBA_RIGHT = {
    35: "base_top", 36: "c3_base_top", 38: "paint_base_top", 39: "paint_base_bot", 41: "c3_base_bot",
    42: "base_bot", 34: "backboard", 32: "c3_arc_top", 33: "c3_arc_bot", 29: "paint_ft_top",
    30: "ft_center", 31: "paint_ft_bot", 26: "hash_top", 27: "arc_top", 28: "hash_bot",
}
_NBA_LEFT = {35: 0, 36: 1, 38: 3, 39: 4, 41: 6, 42: 7, 34: 8, 32: 9, 33: 11, 29: 12, 30: 13, 31: 14, 26: 16, 27: 17, 28: 18}
NBA_MAP = {i: "R_" + n for i, n in _NBA_RIGHT.items()}
NBA_MAP.update({_NBA_LEFT[i]: "L_" + n for i, n in _NBA_RIGHT.items()})
NBA_MAP.update({20: "mid_top", 22: "center", 24: "mid_bot"})


def add_nba_hf(writer: YoloWriter, raw: Path) -> None:
    from huggingface_hub import snapshot_download

    root = Path(snapshot_download(NBA_HF_REPO, repo_type="dataset", local_dir=str(raw / "nba_court_hf"), token=False))
    spec = CourtSpec.preset("nba")
    spec.backboard_from_baseline = 1.29  # where this dataset's annotators put the "backboard" point
    skipped = 0
    for _, img, lbl in iter_yolo_export(root):
        rows = [list(map(float, r.split())) for r in (lbl.read_text().splitlines() if lbl.exists() else []) if r.strip()]
        if not rows:
            skipped += 1
            continue
        kp = np.array(max(rows, key=lambda r: sum(v > 0 for v in r[7::3]))[5:]).reshape(-1, 3)
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        pairs = {NBA_MAP[i]: tuple(kp[i, :2] * [w, h]) for i in NBA_MAP if i < len(kp) and kp[i, 2] > 0}
        try:
            H = homography_from_landmarks(pairs, spec, "label", ransac_px=0.3).H  # RANSAC drops mislabels
        except (CourtNotFound, ValueError):
            skipped += 1
            continue
        line = labels_from_homography(H, CourtSpec.preset("nba"), w, h)
        if line is None:
            skipped += 1
            continue
        writer.add("nba_hf", source_group(img.name), img.name, im, [line])
    print(f"nba_hf: skipped {skipped} images without a usable homography")


def add_venue_video(writer: YoloWriter, venue: str, videos: list[str], every: int, source: str,
                    ref_frame: int = 0, split: str | None = None, min_ecc: float = 0.5) -> None:
    """Frames of a calibrated camera's videos, labelled through the venue's homography. The venue points were
    picked on `ref_frame` of the first video; every other video is registered to it (camera_shift), so a camera
    nudged between recordings still gets correct labels.
    Moving cameras (venue "fixed_camera": false, e.g. a hovering drone) are followed frame to frame: background
    features give each sampled frame's motion, then the homography is snapped onto the painted court lines
    (refine_to_court_lines) so errors don't accumulate; frames where the snap fails (ECC < min_ecc) are skipped."""
    import json

    from nextrun_cv.court.venues import venue_path

    moving = not json.loads(venue_path(venue).read_text()).get("fixed_camera", True)
    ref = None
    for video in videos:
        cap = cv2.VideoCapture(video)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        spec, pts = load_venue(venue, (w, h))
        start = ref_frame if ref is None else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        ok, first = cap.read()
        if not ok:
            print(f"{video}: unreadable, skipped")
            continue
        H_c2i = np.linalg.inv(homography_from_landmarks(pts, spec, "venue", ransac_px=6).H)
        if ref is None:
            ref, shift = first, 0.0
        else:
            Hs, inliers = camera_shift(ref, first)
            if Hs is None or inliers < 100 or ref.shape != first.shape:
                print(f"{video}: can't register to the reference video ({inliers} inliers), skipped")
                continue
            names = list(pts)
            moved = cv2.perspectiveTransform(np.array([[pts[k] for k in names]], float), Hs)[0]
            shift = float(np.median(np.hypot(*(moved - np.array([pts[k] for k in names])).T)))
            H_c2i = Hs @ H_c2i
        if moving:
            H_c2i, cc = refine_to_court_lines(H_c2i, first, spec)
            if cc < min_ecc:
                print(f"{video}: court lines not found on the first frame (ECC {cc:.2f}), skipped")
                continue
        # one camera = one group would put the whole venue in a single split; use ~1-minute blocks instead
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        added = skipped = 0
        prev = first
        for i in range(start, n, every):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok:
                break
            if moving and i != start:
                Hs, _ = camera_shift(prev, frame)
                H_new, cc = refine_to_court_lines(Hs @ H_c2i if Hs is not None else H_c2i, frame, spec)
                prev = frame
                if cc < min_ecc:
                    skipped += 1
                    continue
                H_c2i = H_new
            line = labels_from_homography(np.linalg.inv(H_c2i), spec, w, h)
            if line is None:
                skipped += 1
                continue
            if max(w, h) > 1920:  # keep the dataset light; the model trains at <= 1280 anyway
                s = 1920 / max(w, h)
                frame = cv2.resize(frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            block = int(i / fps // 60)
            writer.add(source, f"{Path(video).stem}_min{block}", f"{Path(video).stem}_{i:06d}", frame, [line], split)
            added += 1
        print(f"{source} {Path(video).name}: {added} frames ({skipped} skipped), camera shift {shift:.1f} px")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "court24"))
    ap.add_argument("--roboflow", nargs="*", default=[], help="WORKSPACE/PROJECT[/VERSION] (24-point sets)")
    ap.add_argument("--yolo-dir", nargs="*", default=[], help="local 24-point YOLO-pose exports")
    ap.add_argument("--nba-hf", action="store_true", help="public NBA broadcast court set (Hugging Face)")
    ap.add_argument("--landmarks-dir", nargs="*", default=[], help="template-landmark labelled sets")
    ap.add_argument("--landmarks-court", default="nba", choices=["nba", "fiba", "ncaa", "highschool"])
    ap.add_argument("--venue", nargs=2, action="append", default=[], metavar=("NAME", "VIDEOS"),
                    help="venue profile + comma-separated video paths / globs (first video = the one the points were picked on)")
    ap.add_argument("--venue-ref-frame", nargs=2, action="append", default=[], metavar=("NAME", "FRAME"),
                    help="frame of the venue's first video the points were picked on (default 0)")
    ap.add_argument("--test-venue", nargs="*", default=[], help="venues used only as test images (unseen-court check)")
    ap.add_argument("--every", type=int, default=30, help="venue videos: one frame every N")
    a = ap.parse_args()

    out = Path(a.out)
    writer = YoloWriter(out)
    for slug in a.roboflow:
        root = roboflow_download(slug, "yolov8", REPO_ROOT / "data" / "raw" / "roboflow")
        add_yolo24(writer, root, "rf_" + slug.split("/")[1])
    for d in a.yolo_dir:
        add_yolo24(writer, Path(d), "local_" + Path(d).name)
    if a.nba_hf:
        add_nba_hf(writer, REPO_ROOT / "data" / "raw")
    for d in a.landmarks_dir:
        add_landmark_set(writer, Path(d), CourtSpec.preset(a.landmarks_court), f"{a.landmarks_court}_" + Path(d).name)
    for name, videos in a.venue:
        paths = []
        for part in videos.split(","):
            paths += [q for q in (sorted(glob.glob(part)) if any(c in part for c in "*?[") else [part]) if q not in paths]
        ref_frame = dict((n, int(f)) for n, f in a.venue_ref_frame).get(name, 0)
        add_venue_video(writer, name, paths, a.every, "venue_" + name, ref_frame,
                        "test" if name in a.test_venue else None)
    writer.write_lists()

    kp = load_keypoint_config(KP_CONFIG)
    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\n"
        f"kpt_shape: [{N_KP}, 3]\nflip_idx: {kp['flip_idx']}\nnames:\n  0: court\n"
    )
    for src, c in writer.counts.items():
        print(f"{src:40s} " + "  ".join(f"{s}={n}" for s, n in c.items()))


if __name__ == "__main__":
    main()
