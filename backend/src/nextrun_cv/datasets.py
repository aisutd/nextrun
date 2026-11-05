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
    base = re.sub(r"_(?:jpg|jpeg|png)$", "", base, flags=re.I)
    # frames exported as an image sequence: 'game-4-q2-07_01-06_53-0157' -> 'game-4-q2-07_01-06_53'
    clip = re.sub(r"-\d{3,}$", "", base)
    return clip if len(clip) >= 12 else base


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


def camera_shift(ref: np.ndarray, img: np.ndarray, width: int = 1280) -> tuple[np.ndarray | None, int]:
    """Homography ref -> img pixels from background features (ORB + RANSAC), for a fixed camera that may have
    been nudged between recordings. Returns (H or None, inlier count)."""
    s = width / ref.shape[1]
    gray = [cv2.cvtColor(cv2.resize(im, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY) for im in (ref, img)]
    orb = cv2.ORB_create(4000)
    (k1, d1), (k2, d2) = (orb.detectAndCompute(g, None) for g in gray)
    if d1 is None or d2 is None:
        return None, 0
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    if len(m) < 20:
        return None, 0
    H, inl = cv2.findHomography(np.float32([k1[x.queryIdx].pt for x in m]), np.float32([k2[x.trainIdx].pt for x in m]),
                                cv2.RANSAC, 3)
    if H is None:
        return None, 0
    S = np.diag([s, s, 1.0])
    return np.linalg.inv(S) @ H @ S, int(inl.sum())


def white_line_mask(frame: np.ndarray) -> np.ndarray:
    """Court paint lines: bright, unsaturated pixels, blurred so ECC has a gradient to follow."""
    hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
    m = ((hls[..., 1] > 160) & (hls[..., 2] < 90)).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 2)


def render_court_lines(H_court_to_img: np.ndarray, spec, shape: tuple[int, int], thick: int = 3) -> np.ndarray:
    """Court template lines drawn through a homography (court meters -> pixels), blurred like white_line_mask."""
    from .court import template

    h, w = shape
    m = np.zeros(shape, np.float32)
    # a homography's sign is arbitrary: points in front of the camera share the sign of the image center's floor point
    g = np.linalg.inv(H_court_to_img) @ [w / 2, h / 2, 1.0]
    front = np.sign((H_court_to_img @ (g / g[2]))[2]) or 1.0
    for pl in template.polylines(spec):
        P = np.c_[pl, np.ones(len(pl))] @ H_court_to_img.T * front
        ok = P[:, 2] > 1e-9
        uv = P[:, :2] / np.where(ok, P[:, 2], 1)[:, None]
        ok &= (np.abs(uv) < 4 * max(w, h)).all(1)
        for a, b, oa, ob in zip(uv[:-1], uv[1:], ok[:-1], ok[1:]):
            if oa and ob:
                cv2.line(m, tuple(map(int, a)), tuple(map(int, b)), 1.0, thick)
    return cv2.GaussianBlur(m, (0, 0), 2)


def refine_to_court_lines(H_court_to_img: np.ndarray, frame: np.ndarray, spec, width: int = 1280,
                          band_px: int = 15) -> tuple[np.ndarray, float]:
    """Snap a roughly right court homography onto the frame's painted lines: ECC (homography motion) between the
    rendered template lines and the white-line mask, looking only within band_px of the template lines (so sky,
    buildings and neighbouring courts don't pull it away). Returns (court -> image H, ECC correlation; 0 if it
    failed, in which case H is returned unchanged)."""
    s = width / frame.shape[1]
    S = np.diag([s, s, 1.0])
    small = cv2.resize(frame, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    mask = white_line_mask(small)
    tmpl = render_court_lines(S @ H_court_to_img, spec, mask.shape)
    band = cv2.dilate((tmpl > 0.05).astype(np.uint8), np.ones((2 * band_px + 1, 2 * band_px + 1), np.uint8))
    try:
        cc, warp = cv2.findTransformECC(tmpl, mask, np.eye(3, dtype=np.float32), cv2.MOTION_HOMOGRAPHY,
                                        (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), band * 255, 5)
    except cv2.error:
        return H_court_to_img, 0.0
    return np.linalg.inv(S) @ warp.astype(float) @ S @ H_court_to_img, float(cc)


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


def iter_coco_export(root: Path):
    """(image_path, width, height, [(class_name, x, y, w, h normalized center box)]) for a COCO export
    (train/valid/test, each with _annotations.coco.json next to its images)."""
    for ann in sorted(Path(root).glob("*/_annotations.coco.json")):
        d = json.loads(ann.read_text())
        cats = {c["id"]: c["name"] for c in d["categories"]}
        boxes: dict[int, list] = {}
        for a in d["annotations"]:
            boxes.setdefault(a["image_id"], []).append(a)
        for im in d["images"]:
            p = ann.parent / im["file_name"]
            if not p.exists():
                continue
            w, h = im["width"], im["height"]
            yield p, w, h, [(cats[a["category_id"]], (a["bbox"][0] + a["bbox"][2] / 2) / w, (a["bbox"][1] + a["bbox"][3] / 2) / h,
                       a["bbox"][2] / w, a["bbox"][3] / h) for a in boxes.get(im["id"], [])]


def hf_dataset_download(repo: str, dest: Path) -> Path:
    """Public Hugging Face dataset repo -> local snapshot (anonymous; no token needed)."""
    from huggingface_hub import snapshot_download

    out = Path(dest) / repo.replace("/", "__")
    snapshot_download(repo, repo_type="dataset", token=False, local_dir=out, max_workers=16)
    return out


def read_data_yaml(root: Path) -> dict:
    import yaml  # ships with ultralytics

    p = next((q for q in (Path(root) / "data.yaml", Path(root) / "court.yaml") if q.exists()), None)
    return yaml.safe_load(p.read_text()) if p else {}


# --- class remapping (ball / rim) ------------------------------------------------------------------------
BALL_NAMES = {"ball", "basketball", "basket ball", "basket-ball", "sports ball", "sports-ball", "sportsball", "bball"}
RIM_NAMES = {"rim", "hoop", "basket", "basketball hoop", "basketball-hoop", "ring", "rim-net", "hoop-rim"}


def rim_with_net(x: float, y: float, w: float, h: float, aspect: float) -> tuple[float, float, float, float]:
    """Rim box in our convention: rim ring + net (as tall as wide in the scene, what the pipeline's rim
    thresholds and the original ball/rim model use). Ring-only boxes (scene h/w < 0.6) keep their top
    edge and are extended down to a square. Normalized center boxes in and out; aspect = scene width /
    height (image width / height unless the export stretched the frames, e.g. 16:9 squashed to 576x576)."""
    if h / w >= 0.6 * aspect:
        return x, y, w, h
    top = y - h / 2
    h = min(w * aspect, 1.0 - top)
    return x, top + h / 2, w, h


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
