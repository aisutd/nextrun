"""Method A — manual calibration: the user marks >= 4 known court landmarks once per camera setup.
Most reliable option for a fixed camera; also the fallback when the automatic methods fail.

Ways to provide the points:
  * JSON file  {"R_base_top": [u, v], "R_paint_ft_top": [u, v], ...}
  * Colab:     `colab_click_landmarks(frame, names)` (click in the browser)
  * Desktop:   `cv2_click_landmarks(frame, names)` (OpenCV window)
Use `landmark_reference_image(spec)` to see where each named landmark is on the court."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import cv2
import numpy as np

from ..config import CourtSpec
from . import template
from .base import CourtCalib, CourtEstimator, CourtNotFound, homography_from_landmarks

# Landmarks that are usually visible from a sideline/baseline-corner camera filming one half court
DEFAULT_HALF_COURT_POINTS = ["R_base_top", "R_base_bot", "R_paint_ft_top", "R_paint_ft_bot", "R_arc_top", "mid_top", "mid_bot"]


class ManualCourtEstimator(CourtEstimator):
    name = "manual"

    def __init__(self, spec: CourtSpec, pairs: dict[str, tuple[float, float]] | str | Path):
        super().__init__(spec)
        if isinstance(pairs, (str, Path)):
            pairs = {k: tuple(v) for k, v in json.loads(Path(pairs).read_text()).items()}
        self.pairs = pairs

    def estimate(self, frame: np.ndarray | None = None) -> CourtCalib:
        if not self.pairs:
            raise CourtNotFound("manual: no landmark points provided")
        calib = homography_from_landmarks(self.pairs, self.spec, self.name)
        if frame is not None:
            calib.image_size = (frame.shape[1], frame.shape[0])
        return calib


def landmark_reference_image(spec: CourtSpec, px_per_m: int = 30) -> np.ndarray:
    """Top-down court diagram with every landmark labelled — shows users what to click."""
    pad = 40
    w = int(spec.length * px_per_m) + 2 * pad
    h = int(spec.width * px_per_m) + 2 * pad
    img = np.full((h, w, 3), (60, 110, 170), np.uint8)

    def to_px(p):
        return int(pad + (p[0] + spec.length / 2) * px_per_m), int(pad + (p[1] + spec.width / 2) * px_per_m)

    for pl in template.polylines(spec):
        cv2.polylines(img, [np.array([to_px(p) for p in pl], np.int32)], False, (255, 255, 255), 2)
    for name, p in template.landmarks(spec).items():
        u, v = to_px(p)
        cv2.circle(img, (u, v), 5, (0, 0, 255), -1)
        cv2.putText(img, name, (u + 4, v - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1, cv2.LINE_AA)
    return img


def cv2_click_landmarks(frame: np.ndarray, names: list[str] = DEFAULT_HALF_COURT_POINTS) -> dict[str, tuple[float, float]]:
    """Desktop: click each landmark in order; press 's' to skip one that isn't visible, 'q' to finish."""
    pairs: dict[str, tuple[float, float]] = {}
    i = 0
    win = "mark court landmarks"
    disp = frame.copy()

    def on_mouse(event, x, y, *_):
        nonlocal i
        if event == cv2.EVENT_LBUTTONDOWN and i < len(names):
            pairs[names[i]] = (float(x), float(y))
            cv2.circle(disp, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(disp, names[i], (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            i += 1

    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)
    while i < len(names):
        view = disp.copy()
        cv2.putText(view, f"click: {names[i]}  (s=skip, q=done)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(win, view)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("s"):
            i += 1
        elif k == ord("q"):
            break
    cv2.destroyWindow(win)
    return pairs


_COLAB_JS = """
async function clickPoints(dataUrl, names, w, h) {
  const div = document.createElement('div');
  const label = document.createElement('div');
  label.style = 'font: 16px sans-serif; margin: 6px 0; color: #0a0';
  const skip = document.createElement('button'); skip.textContent = 'Skip (not visible)';
  const done = document.createElement('button'); done.textContent = 'Done';
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h; canvas.style = 'max-width: 100%; cursor: crosshair';
  div.append(label, skip, done, canvas);
  document.querySelector('#output-area').appendChild(div);
  const ctx = canvas.getContext('2d');
  const img = new Image();
  await new Promise(r => { img.onload = r; img.src = dataUrl; });
  ctx.drawImage(img, 0, 0);
  const out = {}; let i = 0;
  const show = () => { label.textContent = i < names.length ? 'Click: ' + names[i] : 'All done'; };
  show();
  return await new Promise(resolve => {
    canvas.onclick = e => {
      if (i >= names.length) return;
      const r = canvas.getBoundingClientRect();
      const x = (e.clientX - r.left) * w / r.width, y = (e.clientY - r.top) * h / r.height;
      out[names[i]] = [x, y];
      ctx.fillStyle = 'red'; ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill();
      ctx.fillStyle = 'yellow'; ctx.font = '14px sans-serif'; ctx.fillText(names[i], x + 6, y - 6);
      i++; show(); if (i >= names.length) { div.remove(); resolve(out); }
    };
    skip.onclick = () => { i++; show(); if (i >= names.length) { div.remove(); resolve(out); } };
    done.onclick = () => { div.remove(); resolve(out); };
  });
}
"""


def colab_click_landmarks(frame: np.ndarray, names: list[str] = DEFAULT_HALF_COURT_POINTS) -> dict[str, tuple[float, float]]:
    """Google Colab: shows the frame in the cell output; click landmarks in the requested order."""
    from google.colab import output  # type: ignore
    from IPython.display import Javascript, display

    ok, buf = cv2.imencode(".jpg", frame)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    display(Javascript(_COLAB_JS))
    res = output.eval_js(f"clickPoints({json.dumps(data_url)}, {json.dumps(names)}, {frame.shape[1]}, {frame.shape[0]})")
    return {k: (float(v[0]), float(v[1])) for k, v in res.items()}
