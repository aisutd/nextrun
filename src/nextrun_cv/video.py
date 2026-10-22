"""Thin OpenCV video reader/writer helpers."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path: str
    fps: float
    width: int
    height: int
    n_frames: int


def probe(path: str | Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video {path}")
    info = VideoInfo(
        str(path),
        cap.get(cv2.CAP_PROP_FPS) or 30.0,
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    )
    cap.release()
    return info


def iter_frames(
    path: str | Path, stride: int = 1, start: int = 0, max_frames: int | None = None
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR frame). frame_index is the index in the source video."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video {path}")
    if start:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    idx, emitted = start, 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if (idx - start) % stride == 0:
                yield idx, frame
                emitted += 1
                if max_frames is not None and emitted >= max_frames:
                    break
            idx += 1
    finally:
        cap.release()


def read_frame(path: str | Path, index: int) -> np.ndarray:
    for _, f in iter_frames(path, start=index, max_frames=1):
        return f
    raise IndexError(f"frame {index} not in {path}")


def sample_frames(path: str | Path, n: int) -> list[tuple[int, np.ndarray]]:
    """n frames spread evenly across the video (used for court calibration and tagging)."""
    info = probe(path)
    total = max(1, info.n_frames)
    idxs = sorted({int(i) for i in np.linspace(0, total - 1, n)})
    return [(i, read_frame(path, i)) for i in idxs]


class VideoWriter:
    def __init__(self, path: str | Path, fps: float, size: tuple[int, int]):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
        if not self._w.isOpened():
            raise RuntimeError(f"cannot open writer for {path}")

    def write(self, frame: np.ndarray) -> None:
        self._w.write(frame)

    def close(self) -> None:
        self._w.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
