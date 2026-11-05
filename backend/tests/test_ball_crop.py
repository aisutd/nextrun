"""The ball/rim detector's play-area crop: boxes must map back to full-frame coordinates (no real model needed)."""
import sys
import types

import numpy as np

from nextrun_cv.config import ModelConfig


class _Boxes:
    def __init__(self, rows):
        a = np.array(rows, float).reshape(-1, 6)
        self.xyxy, self.conf, self.cls = _T(a[:, :4]), _T(a[:, 4]), _T(a[:, 5])


class _T:
    def __init__(self, a):
        self.a = a

    def cpu(self):
        return self

    def numpy(self):
        return self.a

    def int(self):
        return _T(self.a.astype(int))


class _FakeYOLO:
    """Finds the 'ball' at crop-pixel (50, 60) and the 'rim' at (100,20)-(140,40) in whatever image it is given."""
    names = {0: "ball", 1: "rim"}
    calls: list = []

    def __init__(self, *_a, **_k):
        pass

    def predict(self, img, imgsz=None, **_k):
        _FakeYOLO.calls.append((img.shape[:2], imgsz))
        r = types.SimpleNamespace()
        r.boxes = _Boxes([[44, 54, 56, 66, 0.9, 0], [100, 20, 140, 40, 0.9, 1]])
        return [r]


def _detector(monkeypatch, **cfg):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeYOLO))
    from nextrun_cv.detect.ball_hoop import BallHoopDetector

    _FakeYOLO.calls = []
    return BallHoopDetector(ModelConfig(device="cpu", **cfg))


def test_full_frame_first_then_crop_with_coordinates_mapped_back(monkeypatch):
    d = _detector(monkeypatch)
    frame = np.zeros((2160, 3840, 3), np.uint8)
    hint = [(1500, 900, 1560, 1080), (1700, 920, 1760, 1100)]
    balls, rims = d.detect(frame, hint)  # no rim known yet: whole frame
    assert _FakeYOLO.calls[-1][0] == (2160, 3840) and balls[0].xy == (50, 60)
    d._rims = [(1800, 700, 1840, 720)]  # (the stand-in model puts its rim in the corner; use a realistic one)
    balls, rims = d.detect(frame, hint)  # rim known: the play area only
    (h, w), imgsz = _FakeYOLO.calls[-1]
    assert h < 2160 and w < 3840 and w * h < 0.7 * 3840 * 2160 and 640 <= imgsz <= 1920
    x0 = balls[0].xy[0] - 50
    y0 = balls[0].xy[1] - 60
    assert x0 > 0 and y0 >= 0  # offset of the crop in the frame
    assert rims[0].bbox == (100 + x0, 20 + y0, 140 + x0, 40 + y0)


def test_full_frame_pass_every_n_frames_and_when_crop_disabled(monkeypatch):
    d = _detector(monkeypatch, ball_full_every=3)
    frame = np.zeros((1080, 1920, 3), np.uint8)
    hint = [(900, 500, 940, 620)]
    shapes = [(d.detect(frame, hint), _FakeYOLO.calls[-1][0])[1] for _ in range(6)]
    assert shapes[0] == (1080, 1920) and shapes[1] != (1080, 1920) and shapes[4] == (1080, 1920)
    d2 = _detector(monkeypatch, ball_crop=False)
    for _ in range(3):
        d2.detect(frame, hint)
    assert all(c[0] == (1080, 1920) for c in _FakeYOLO.calls)


def test_no_players_means_whole_frame(monkeypatch):
    d = _detector(monkeypatch)
    frame = np.zeros((1080, 1920, 3), np.uint8)
    d.detect(frame, [(900, 500, 940, 620)])
    d.detect(frame, [])
    assert _FakeYOLO.calls[-1][0] == (1080, 1920)
