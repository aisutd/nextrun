"""Training-data tooling shared by scripts/build_court_dataset.py and scripts/build_ball_rim_dataset.py.

- Roboflow Universe downloads (needs ROBOFLOW_API_KEY; free account).
- Group-aware splits: frames from the same video / game clip / Roboflow source image always land in the
  same split, so near-duplicates never straddle train and test (this inflated earlier court scores).
- Court labels from a homography: any calibrated image (fixed-camera venue, landmark-labelled broadcast
  frame) becomes a 24-keypoint training sample for the court model.
- Class remapping for ball / rim datasets that name things differently (basketball, sports ball, hoop...).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

import cv2
import numpy as np

SPLITS = ("train", "val", "test")
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


# --- splits --------------------------------------------------------------------------------------------
def source_group(filename: str) -> str:
    """Group key for a frame: Roboflow augmentations/exports of one source image and frames of one video
    clip share a key. 'clip-a_mp4-0012_jpg.rf.abc.jpg' -> 'clip-a'."""
    base = Path(filename).name.split(".rf.")[0]
    base = re.split(r"_(?:mp4|mov|avi|mkv)-\d+", base, flags=re.I)[0]
    return re.sub(r"_(?:jpg|jpeg|png)$", "", base, flags=re.I)


def split_for(group: str, val: float = 0.1, test: float = 0.1) -> str:
    """Deterministic split from a hash of the group key."""
    r = int(hashlib.md5(group.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if r < test else "val" if r < test + val else "train"


# --- YOLO label io -------------------------------------------------------------------------------------
def pose_label(kps: np.ndarray, w: int, h: int, pad: float = 0.02) -> str | None:
    """kps (K, 3) pixel x, y, visibility -> one YOLO-pose label line (class 0 = court), or None if fewer
    than 4 keypoints are visible. The box is the visible keypoints' extent, padded and clipped."""
    vis = kps[:, 2] > 0
    if vis.sum() < 4:
        return None
    x1, y1 = kps[vis, 0].min(), kps[vis, 1].min()
    x2, y2 = kps[vis, 0].max(), kps[vis, 1].max()
    px, py = pad * w, pad * h
    x1, y1, x2, y2 = max(0, x1 - px), max(0, y1 - py), min(w, x2 + px), min(h, y2 + py)
    vals = [(x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h]
    for x, y, v in kps:
        vals += [x / w, y / h, 2] if v > 0 else [0, 0, 0]
    return "0 " + " ".join(f"{v:.6f}" if isinstance(v, float) else str(v) for v in vals)


def project_keypoints(H_court_to_img: np.ndarray, court_pts: dict[int, tuple[float, float]], n: int,
                      w: int, h: int) -> np.ndarray:
    """Project court keypoints into an image -> (n, 3) [x, y, visible]. Points behind the camera or outside
    the frame are invisible. (Occlusion by players is not modelled; YOLO-pose tolerates it.)"""
    out = np.zeros((n, 3))
    ids = sorted(court_pts)
    P = np.c_[np.array([court_pts[i] for i in ids], float), np.ones(len(ids))] @ H_court_to_img.T
    # a homography's overall sign is arbitrary: "in front of the camera" = same sign as a floor point we
    # know is visible (bottom-center of the image)
    g = np.linalg.inv(H_court_to_img) @ [w / 2, h - 1, 1.0]
    front = np.sign((H_court_to_img @ (g / g[2]))[2]) or 1.0
    for i, (x, y, z) in zip(ids, P * front):
        if z <= 1e-9:
            continue
        u, v = x / z, y / z
        if 0 <= u < w and 0 <= v < h:
            out[i] = (u, v, 2)
    return out


class YoloWriter:
    """Writes images + labels into out/{split}/{images,labels} and keeps per-source counts."""

    def __init__(self, out: Path):
        self.out = Path(out)
        self.counts: dict[str, dict[str, int]] = {}
        for s in SPLITS:
            (self.out / s / "images").mkdir(parents=True, exist_ok=True)
            (self.out / s / "labels").mkdir(parents=True, exist_ok=True)

    def add(self, source: str, group: str, name: str, image, label_lines: list[str], split: str | None = None) -> str:
        """image: a path to copy or an ndarray to encode. Returns the split used."""
        split = split or split_for(f"{source}/{group}")
        stem = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{source}__{Path(name).stem}")[:180]
        img_dst = self.out / split / "images" / f"{stem}.jpg"
        if isinstance(image, np.ndarray):
            cv2.imwrite(str(img_dst), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        elif Path(image).suffix.lower() in (".jpg", ".jpeg"):
            shutil.copyfile(image, img_dst)
        else:
            cv2.imwrite(str(img_dst), cv2.imread(str(image)))
        (self.out / split / "labels" / f"{stem}.txt").write_text("\n".join(label_lines) + ("\n" if label_lines else ""))
        c = self.counts.setdefault(source, {s: 0 for s in SPLITS})
        c[split] += 1
        return split

    def write_lists(self) -> None:
        """Per-source image lists (out/lists/<source>_<split>.txt) for per-domain evaluation."""
        d = self.out / "lists"
        d.mkdir(exist_ok=True)
        for s in SPLITS:
            by_src: dict[str, list[str]] = {}
            for p in sorted((self.out / s / "images").glob("*.jpg")):
                by_src.setdefault(p.name.split("__")[0], []).append(str(p.resolve()))
            for src, paths in by_src.items():
                (d / f"{src}_{s}.txt").write_text("\n".join(paths) + "\n")
        (self.out / "sources.json").write_text(json.dumps(self.counts, indent=2))


def iter_yolo_export(root: Path):
    """(split_name, image_path, label_path) for a YOLO export (train/valid/test with images/ + labels/)."""
    for split_dir in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        img_dir = split_dir / "images"
        if not img_dir.is_dir():
            continue
        for img in sorted(img_dir.iterdir()):
            if img.suffix.lower() in IMG_EXT:
                yield split_dir.name, img, split_dir / "labels" / f"{img.stem}.txt"


def read_data_yaml(root: Path) -> dict:
    import yaml  # ships with ultralytics

    p = next((q for q in (Path(root) / "data.yaml", Path(root) / "court.yaml") if q.exists()), None)
    return yaml.safe_load(p.read_text()) if p else {}


# --- class remapping (ball / rim) ------------------------------------------------------------------------
BALL_NAMES = {"ball", "basketball", "basket ball", "basket-ball", "sports ball", "sports-ball", "sportsball", "bball"}
RIM_NAMES = {"rim", "hoop", "basket", "basketball hoop", "basketball-hoop", "ring", "rim-net", "hoop-rim"}


def ball_rim_class(name: str) -> int | None:
    """Dataset class name -> 0 ball / 1 rim / None (dropped: players, backboards, 'made', ...)."""
    n = re.sub(r"[_]+", " ", str(name).strip().lower())
    if n in BALL_NAMES:
        return 0
    if n in RIM_NAMES:
        return 1
    return None


# --- Roboflow Universe ---------------------------------------------------------------------------------
def roboflow_download(slug: str, fmt: str, dest: Path, api_key: str | None = None) -> Path:
    """slug 'workspace/project' (latest version) or 'workspace/project/3' -> extracted export dir."""
    api_key = api_key or os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        raise RuntimeError("set ROBOFLOW_API_KEY (free at app.roboflow.com -> Settings -> API keys)")
    parts = slug.strip("/").split("/")
    ws, project = parts[0], parts[1]
    if len(parts) > 2:
        version = parts[2]
    else:
        info = _get_json(f"https://api.roboflow.com/{ws}/{project}?api_key={api_key}")
        version = max(int(str(v["id"]).rsplit("/", 1)[-1]) for v in info["versions"])
    out = Path(dest) / f"{ws}__{project}__v{version}"
    if out.exists() and any(out.iterdir()):
        return out
    meta = _get_json(f"https://api.roboflow.com/{ws}/{project}/{version}/{fmt}?api_key={api_key}")
    link = meta["export"]["link"]
    out.mkdir(parents=True, exist_ok=True)
    zpath = out.with_suffix(".zip")
    urllib.request.urlretrieve(link, zpath)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(out)
    zpath.unlink()
    return out


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())
