"""Person re-identification: a 512-number "who is this" fingerprint per player crop, from OSNet (osnet.py) trained
to tell people apart across cameras and lighting. Two crops of one person land close together (cosine distance
near 0), different people far apart, much more reliably than clothing colour alone."""
from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np

from ..config import REPO_ROOT

WEIGHTS = REPO_ROOT / "weights" / "reid" / "osnet_x1_0_msmt17.pt"
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)
_model = None
_lock = threading.Lock()


def available() -> bool:
    return WEIGHTS.exists()


def _load(device: str | None):
    global _model
    with _lock:
        if _model is None:
            import torch

            from .osnet import osnet_x1_0

            sd = torch.load(WEIGHTS, map_location="cpu", weights_only=True)  # plain tensors only: no code in the file runs
            sd = sd.get("state_dict", sd)
            sd = {k[7:] if k.startswith("module.") else k: v for k, v in sd.items() if not k.endswith(("classifier.weight", "classifier.bias"))}
            m = osnet_x1_0(num_classes=1, pretrained=False, loss="softmax")
            m.load_state_dict(sd, strict=False)
            dev = device or ("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
            _model = (m.eval().to(dev), dev)
    return _model


def embed(crops: list[np.ndarray], device: str | None = None, batch: int = 64) -> np.ndarray:
    """BGR person crops -> (N, 512) unit-length fingerprints."""
    import torch

    if not crops:
        return np.zeros((0, 512), np.float32)
    model, dev = _load(device)
    out = []
    for i in range(0, len(crops), batch):
        x = np.stack([(cv2.resize(c, (128, 256))[..., ::-1].astype(np.float32) / 255 - _MEAN) / _STD for c in crops[i : i + batch]])
        with torch.no_grad():
            f = model(torch.from_numpy(x.transpose(0, 3, 1, 2)).contiguous().to(dev)).float().cpu().numpy()
        out.append(f / np.maximum(np.linalg.norm(f, axis=1, keepdims=True), 1e-9))
    return np.concatenate(out)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance between two (averaged, re-normalised) fingerprints: 0 same .. 2 opposite."""
    return 1.0 - float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-9))


def sample_fingerprints(video: str, frames, every: int = 2) -> dict[str, np.ndarray]:
    """{body_key: fingerprint} for players standing clear of everyone (no box overlap and a body-width apart, so a
    crop never catches part of someone else), from every `every`-th analysed frame."""
    from .appearance import body_key

    want = {f.idx: f for f in frames[::max(1, every)]}
    keys, crops = [], []
    if not want:
        return {}
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
                    x1, y1, x2, y2 = p.bbox
                    w = x2 - x1
                    if y2 - y1 < 48:
                        continue
                    if any(q is not p and q.bbox[0] < x2 + 0.5 * w and x1 - 0.5 * w < q.bbox[2] and q.bbox[1] < y2 and y1 < q.bbox[3]
                           for q in ps):
                        continue  # someone within half a body-width: their arm or shirt would be in the crop
                    c = img[max(0, int(y1)):int(y2), max(0, int(x1)):int(x2)]
                    if c.size:
                        keys.append(body_key(i, p.bbox))
                        crops.append(c)
            elif not cap.grab():
                break
            i += 1
    finally:
        cap.release()
    emb = embed(crops)
    return dict(zip(keys, emb))
