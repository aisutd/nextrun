"""Training-data tooling: group splits, class remapping, homography-projected court labels, dataset merge."""
import importlib.util
from pathlib import Path

import cv2
import numpy as np

from nextrun_cv.config import REPO_ROOT, CourtSpec
from nextrun_cv.court import template
from nextrun_cv.court.keypoints import keypoints_for_court, load_keypoint_config
from nextrun_cv.datasets import ball_rim_class, pose_label, project_keypoints, source_group, split_for


def _script(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_source_group_keeps_clips_and_augmentations_together():
    a = source_group("celtics-knicks-q1_mp4-0012_jpg.rf.abc123.jpg")
    b = source_group("celtics-knicks-q1_mp4-0450_jpg.rf.zzz999.jpg")
    assert a == b == "celtics-knicks-q1"
    assert source_group("IMG_0042_jpg.rf.x.jpg") == source_group("IMG_0042_jpg.rf.y.jpg") == "IMG_0042"
    assert split_for("rf_x/celtics") == split_for("rf_x/celtics")  # deterministic
    splits = [split_for(f"src/{i}") for i in range(2000)]
    assert 0.07 < splits.count("test") / 2000 < 0.13 and 0.07 < splits.count("val") / 2000 < 0.13


def test_ball_rim_class_names():
    assert [ball_rim_class(n) for n in ("Basketball", "sports ball", "ball", "Rim", "hoop", "basket")] == [0, 0, 0, 1, 1, 1]
    assert [ball_rim_class(n) for n in ("player", "backboard", "made", "basketball-player")] == [None] * 4


def test_projected_court_labels_roundtrip():
    spec = CourtSpec.preset("nba")
    kp = keypoints_for_court(load_keypoint_config(REPO_ROOT / "configs" / "court_keypoints.json"), spec)
    lm = template.landmarks(spec)
    names = ["R_base_top", "R_base_bot", "mid_top", "mid_bot"]
    img = np.float32([[1180, 300], [1250, 690], [80, 330], [10, 700]])
    Hc2i = cv2.getPerspectiveTransform(np.float32([lm[n] for n in names]), img)
    kps = project_keypoints(Hc2i, kp, 24, 1280, 720)
    vis = kps[:, 2] > 0
    assert vis[[10, 12, 13, 15, 16, 17, 22]].all() and not vis[[0, 2, 5]].any()  # right half in view, left not
    line = pose_label(kps, 1280, 720).split()
    assert line[0] == "0" and len(line) == 5 + 24 * 3
    back = np.array(line[5:], float).reshape(-1, 3)
    assert np.allclose(back[vis, :2] * [1280, 720], kps[vis, :2], atol=0.01)
    assert pose_label(np.zeros((24, 3)), 1280, 720) is None


def test_ball_rim_merge(tmp_path):
    src = tmp_path / "export"
    (src / "train" / "images").mkdir(parents=True)
    (src / "train" / "labels").mkdir(parents=True)
    (src / "data.yaml").write_text("names: ['player', 'Basketball', 'Hoop']\n")
    for i in range(3):
        cv2.imwrite(str(src / "train" / "images" / f"clip_mp4-{i:04d}_jpg.rf.{i}.jpg"), np.zeros((32, 32, 3), np.uint8))
        (src / "train" / "labels" / f"clip_mp4-{i:04d}_jpg.rf.{i}.txt").write_text(
            "0 0.5 0.5 0.2 0.4\n1 0.3 0.3 0.05 0.05\n2 0.1 0.2 0.3 0.2 0.3 0.4 0.1 0.4\n")
    mod = _script("build_ball_rim_dataset")
    from nextrun_cv.datasets import YoloWriter

    w = YoloWriter(tmp_path / "out")
    mod.add_detection_set(w, src, "local_export", keep_empty=False)
    labels = sorted((tmp_path / "out").glob("*/labels/*.txt"))
    assert len(labels) == 3 and len({p.parent.parent.name for p in labels}) == 1  # one clip -> one split
    rows = [r.split() for r in labels[0].read_text().splitlines()]
    assert [r[0] for r in rows] == ["0", "1"]  # player dropped, ball -> 0, hoop polygon -> rim box
    assert np.allclose(list(map(float, rows[1][1:])), [0.2, 0.3, 0.2, 0.2])
