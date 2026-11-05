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
    path: str | Path, stride: int = 1, start: int = 0, max_frames: int | None = None, prefetch: int = 6
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR frame). frame_index is the index in the source video.

    Frames between the strided ones are only `grab`bed (decoded, but not colour-converted / copied), and decoding
    runs in a background thread so the models never wait for the next frame (prefetch = frames kept ready)."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"cannot open video {path}")
    if start:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    stride = max(1, stride)
    if prefetch <= 0 or max_frames == 1:
        yield from _read(cap, stride, start, max_frames, None)
        return
    import queue
    import threading

    q: queue.Queue = queue.Queue(maxsize=prefetch)
    stop = threading.Event()
    done = object()

    def worker() -> None:
        try:
            for item in _read(cap, stride, start, max_frames, stop):
                while not stop.is_set():
                    try:
                        q.put(item, timeout=0.2)
                        break
                    except queue.Full:
                        continue
                if stop.is_set():
                    return
        except Exception as e:  # noqa: BLE001  (re-raised in the consumer)
            q.put(e)
        finally:
            q.put(done)

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    try:
        while True:
            item = q.get()
            if item is done:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        stop.set()
        th.join(timeout=2)
        cap.release()


def _read(cap, stride: int, start: int, max_frames: int | None, stop) -> Iterator[tuple[int, np.ndarray]]:
    idx, emitted = start, 0
    try:
        while stop is None or not stop.is_set():
            if (idx - start) % stride == 0:
                ok, frame = cap.read()
                if not ok:
                    break
                yield idx, frame
                emitted += 1
                if max_frames is not None and emitted >= max_frames:
                    break
            elif not cap.grab():
                break
            idx += 1
    finally:
        if stop is None:
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


def ffmpeg_exe() -> str | None:
    """System ffmpeg, else the one bundled with the imageio-ffmpeg package."""
    import shutil

    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


class FFmpegWriter:
    """Browser-playable H.264 written in one pass: frames are piped to ffmpeg."""

    def __init__(self, path: str | Path, fps: float, size: tuple[int, int], exe: str):
        import subprocess

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._size = size
        self._p = subprocess.Popen(
            [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size[0]}x{size[1]}", "-r", f"{fps:.3f}",
             "-i", "-", "-an", "-c:v", "libx264", "-preset", "superfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE,
        )

    def write(self, frame: np.ndarray) -> None:
        if (frame.shape[1], frame.shape[0]) != self._size:
            frame = cv2.resize(frame, self._size)
        self._p.stdin.write(np.ascontiguousarray(frame).tobytes())

    def close(self) -> None:
        self._p.stdin.close()
        if self._p.wait() != 0:
            raise RuntimeError("ffmpeg failed while writing the video")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def make_writer(path: str | Path, fps: float, size: tuple[int, int]):
    exe = ffmpeg_exe()
    return FFmpegWriter(path, fps, size, exe) if exe else VideoWriter(path, fps, size)


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
