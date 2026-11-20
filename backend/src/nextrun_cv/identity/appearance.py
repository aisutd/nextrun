"""Cheap appearance embeddings (torso colour histograms) for team clustering and re-linking tracks."""
from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np

from ..schema import KP_L_HIP, KP_L_SHOULDER, KP_MIN_CONF, KP_R_HIP, KP_R_SHOULDER, PlayerObs

H_BINS, S_BINS, V_BINS = 16, 4, 4


def torso_crop(frame: np.ndarray, p: PlayerObs) -> np.ndarray | None:
    x1, y1, x2, y2 = p.bbox
    h, w = frame.shape[:2]
    kp = p.keypoints
    if kp is not None and (kp[[KP_L_SHOULDER, KP_R_SHOULDER, KP_L_HIP, KP_R_HIP], 2] > KP_MIN_CONF).all():
        pts = kp[[KP_L_SHOULDER, KP_R_SHOULDER, KP_L_HIP, KP_R_HIP], :2]
        tx1, ty1 = pts.min(0)
        tx2, ty2 = pts.max(0)
        pad = 0.1 * (tx2 - tx1)
        tx1, tx2 = tx1 + pad, tx2 - pad
    else:
        bw, bh = x2 - x1, y2 - y1
        tx1, tx2, ty1, ty2 = x1 + 0.25 * bw, x2 - 0.25 * bw, y1 + 0.2 * bh, y1 + 0.5 * bh
    tx1, ty1 = max(0, int(tx1)), max(0, int(ty1))
    tx2, ty2 = min(w, int(tx2)), min(h, int(ty2))
    if tx2 - tx1 < 4 or ty2 - ty1 < 4:
        return None
    return frame[ty1:ty2, tx1:tx2]


def color_embedding(crop: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [H_BINS, S_BINS, V_BINS], [0, 180, 0, 256, 0, 256]).ravel()
    hist = np.sqrt(hist / max(hist.sum(), 1.0))  # Hellinger: robust to a few dominant bins
    return hist / max(np.linalg.norm(hist), 1e-9)


class AppearanceBank:
    """Accumulates embeddings per track while frames stream by."""

    def __init__(self, sample_every: int = 5):
        self.sample_every = sample_every
        self.samples: dict[int, list[np.ndarray]] = defaultdict(list)

    def add(self, frame_idx: int, frame: np.ndarray, players: list[PlayerObs]) -> None:
        if frame_idx % self.sample_every:
            return
        # skip players overlapping others: their crop mixes two jerseys
        for p in players:
            if any(q is not p and _iou(p.bbox, q.bbox) > 0.2 for q in players):
                continue
            crop = torso_crop(frame, p)
            if crop is not None:
                self.samples[p.track_id].append(color_embedding(crop))

    def track_embeddings(self) -> dict[int, np.ndarray]:
        out = {}
        for tid, embs in self.samples.items():
            m = np.median(np.stack(embs), axis=0)
            out[tid] = m / max(np.linalg.norm(m), 1e-9)
        return out

    def to_dict(self) -> dict:
        return {str(k): v.tolist() for k, v in self.track_embeddings().items()}


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def sample_track_colors(video: str, frames, every: int = 3) -> dict[int, list[tuple[int, list[float]]]]:
    """Torso colour of every clearly visible player over time: {track id: [(source frame, embedding), ...]}, from every
    `every`-th analysed frame. Used to catch a tracker id that jumps from one player to another mid-clip."""
    want = {f.idx: f for f in frames[::max(1, every)]}
    if not want:
        return {}
    out: dict[int, list] = defaultdict(list)
    cap = cv2.VideoCapture(str(video))
    last = max(want)
    i = 0
    try:
        while i <= last:
            if i in want:
                ok, img = cap.read()
                if not ok:
                    break
                ps = want[i].players
                for p in ps:
                    if any(q is not p and _iou(p.bbox, q.bbox) > 0.1 for q in ps):
                        continue  # overlapping: the crop would mix two jerseys
                    crop = torso_crop(img, p)
                    if crop is not None:
                        out[p.track_id].append((i, color_embedding(crop).round(4).tolist()))
            elif not cap.grab():
                break
            i += 1
    finally:
        cap.release()
    return dict(out)


# --- whole-body signature for joining pieces of one player (identity.stitch.cover_tracks) ----------------------
BODY_BINS = (12, 3, 3)  # hue x saturation x value: low-saturation bins keep greys, blacks and whites apart


def _region_hist(img: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray | None:
    h, w = img.shape[:2]
    x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2))
    if x2 - x1 < 3 or y2 - y1 < 3:
        return None
    hsv = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, list(BODY_BINS), [0, 180, 0, 256, 0, 256]).ravel()
    s = hist.sum()
    return hist / s if s > 0 else None


def body_signature(img: np.ndarray, bbox) -> np.ndarray | None:
    """Colour histograms of the upper body (shirt) and lower body (shorts / pants), side by side, each summing to 1."""
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    if bh < 24:
        return None
    up = _region_hist(img, x1 + 0.22 * bw, y1 + 0.18 * bh, x2 - 0.22 * bw, y1 + 0.5 * bh)
    lo = _region_hist(img, x1 + 0.25 * bw, y1 + 0.55 * bh, x2 - 0.25 * bw, y1 + 0.85 * bh)
    if up is None or lo is None:
        return None
    return np.concatenate([up, lo]).astype(np.float32)


def body_key(idx: int, bbox) -> str:
    """Stable key for one detection (track ids change when tracks are split or joined; frame + box do not)."""
    return f"{idx}:{int(round(bbox[0]))}:{int(round(bbox[1]))}"


def sample_body_signatures(video: str, frames, every: int = 2) -> dict[str, list[float]]:
    """{body_key: signature} for every player standing clear of others, from every `every`-th analysed frame."""
    want = {f.idx: f for f in frames[::max(1, every)]}
    out: dict[str, list[float]] = {}
    if not want:
        return out
    cap = cv2.VideoCapture(str(video))
    last, i = max(want), 0
    try:
        while i <= last:
            if i in want:
                ok, img = cap.read()
                if not ok:
                    break
                ps = want[i].players
                for p in ps:
                    if any(q is not p and _iou(p.bbox, q.bbox) > 0.02 for q in ps):
                        continue  # touching someone: the crop would mix two people's clothes
                    sig = body_signature(img, p.bbox)
                    if sig is not None:
                        out[body_key(i, p.bbox)] = sig.round(4).tolist()
            elif not cap.grab():
                break
            i += 1
    finally:
        cap.release()
    return out


def body_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Hellinger distance (0 same .. 1 nothing in common), averaged over upper and lower body."""
    n = len(a) // 2
    d = [np.sqrt(max(0.0, 1.0 - float(np.sum(np.sqrt(a[s] * b[s]))))) for s in (slice(0, n), slice(n, None))]
    return float(np.mean(d))
