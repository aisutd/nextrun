"""Training-data tooling: group splits, class remapping, homography-projected court labels, dataset merge."""
import importlib.util
from pathlib import Path

import cv2
import numpy as np

from nextrun_cv.config import REPO_ROOT, CourtSpec
from nextrun_cv.court import template
from nextrun_cv.court.keypoints import keypoints_for_court, load_keypoint_config
from nextrun_cv.datasets import (
    ball_rim_class, camera_shift, pose_label, project_keypoints, rim_with_net, source_group, split_for,
)


def _script(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "src" / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_source_group_keeps_clips_and_augmentations_together():
    a = source_group("celtics-knicks-q1_mp4-0012_jpg.rf.abc123.jpg")
    b = source_group("celtics-knicks-q1_mp4-0450_jpg.rf.zzz999.jpg")
    assert a == b == "celtics-knicks-q1"
    assert source_group("IMG_0042_jpg.rf.x.jpg") == source_group("IMG_0042_jpg.rf.y.jpg") == "IMG_0042"
    # frames exported as an image sequence share their clip
    assert source_group("knicks-game-4-q2-07_01-06_53-0157_png.rf.a.jpg") == "knicks-game-4-q2-07_01-06_53"
    assert source_group("knicks-game-4-q2-07_01-06_53-0158_png.rf.b.jpg") == "knicks-game-4-q2-07_01-06_53"
    assert split_for("rf_x/celtics") == split_for("rf_x/celtics")  # deterministic
    splits = [split_for(f"src/{i}") for i in range(2000)]
    assert 0.07 < splits.count("test") / 2000 < 0.13 and 0.07 < splits.count("val") / 2000 < 0.13


def test_ball_rim_class_names():
    assert [ball_rim_class(n) for n in ("Basketball", "sports ball", "ball", "Rim", "hoop", "basket")] == [0, 0, 0, 1, 1, 1]
    assert [ball_rim_class(n) for n in ("player", "backboard", "made", "basketball-player")] == [None] * 4


def test_projected_court_labels_roundtrip():
    spec = CourtSpec.preset("nba")
    kp = keypoints_for_court(load_keypoint_config(REPO_ROOT / "models" / "court_keypoints.json"), spec)
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
    mod.add_detection_set(w, src, "local_export", False, set())
    labels = sorted((tmp_path / "out").glob("*/labels/*.txt"))
    assert len(labels) == 3 and len({p.parent.parent.name for p in labels}) == 1  # one clip -> one split
    rows = [r.split() for r in labels[0].read_text().splitlines()]
    assert [r[0] for r in rows] == ["0", "1"]  # player dropped, ball -> 0, hoop polygon -> rim box
    assert np.allclose(list(map(float, rows[1][1:])), [0.2, 0.3, 0.2, 0.2])


def test_rim_with_net_extends_ring_only_boxes():
    # 1920x1080: ring 100x35 px at top=500 px -> 100x100 px square, same top edge
    x, y, w, h = rim_with_net(0.5, 517.5 / 1080, 100 / 1920, 35 / 1080, 1920 / 1080)
    assert np.isclose(w * 1920, 100) and np.isclose(h * 1080, 100) and np.isclose((y - h / 2) * 1080, 500)
    # already rim + net: unchanged; 16:9 squashed to a square image: same decision in scene space
    assert rim_with_net(0.5, 0.5, 0.05, 0.09, 16 / 9) == (0.5, 0.5, 0.05, 0.09)
    _, _, _, h = rim_with_net(0.5, 0.5, 0.05, 0.03, 16 / 9)
    assert np.isclose(h, 0.05 * 16 / 9)


def test_ball_rim_coco_merge_dedupes_and_splits_by_clip(tmp_path):
    import json

    def export(root, names):
        (root / "train").mkdir(parents=True)
        imgs = [{"id": i, "file_name": f"game-1-q1-05_13-05_09-{i:04d}_png.rf.{root.name}{i}.jpg", "width": 64, "height": 36}
                for i in range(3)]
        for im in imgs:
            cv2.imwrite(str(root / "train" / im["file_name"]), np.zeros((36, 64, 3), np.uint8))
        anns = [{"id": 3 * i + k, "image_id": i, "category_id": k, "bbox": b}
                for i in range(3) for k, b in enumerate([[10, 10, 4, 4], [30, 5, 8, 2], [0, 0, 10, 30]])]
        cats = [{"id": k, "name": n} for k, n in enumerate(names)]
        (root / "train" / "_annotations.coco.json").write_text(json.dumps({"images": imgs, "annotations": anns, "categories": cats}))

    export(tmp_path / "a", ["ball", "rim", "player"])
    export(tmp_path / "b", ["Ball", "Hoop", "Ref"])  # same frames again (mirror of a related project)
    mod = _script("build_ball_rim_dataset")
    from nextrun_cv.datasets import YoloWriter

    w, seen = YoloWriter(tmp_path / "out"), set()
    mod.add_coco_set(w, tmp_path / "a", "a", False, seen)
    mod.add_coco_set(w, tmp_path / "b", "b", False, seen)
    labels = sorted((tmp_path / "out").glob("*/labels/*.txt"))
    assert len(labels) == 3 and len({p.parent.parent.name for p in labels}) == 1  # deduped; one clip -> one split
    ball, rim = [list(map(float, r.split())) for r in labels[0].read_text().splitlines()]
    assert ball[0] == 0 and np.allclose(ball[1:], [12 / 64, 12 / 36, 4 / 64, 4 / 36])
    assert rim[0] == 1 and np.isclose(rim[4] * 36, 8) and np.isclose((rim[2] - rim[4] / 2) * 36, 5)  # ring -> rim + net


def test_camera_shift_recovers_a_nudged_camera():
    rng = np.random.default_rng(0)
    ref = cv2.GaussianBlur((rng.random((720, 1280, 3)) * 255).astype(np.uint8), (5, 5), 0)
    M = np.array([[1.0, 0.0, 12.0], [0.0, 1.0, -7.0], [0.0, 0.0, 1.0]])
    moved = cv2.warpPerspective(ref, M, (1280, 720))
    H, inliers = camera_shift(ref, moved)
    p = cv2.perspectiveTransform(np.array([[[400.0, 300.0], [900.0, 500.0]]]), H)[0]
    assert inliers > 100 and np.allclose(p, [[412, 293], [912, 493]], atol=1.0)


def test_frame_stretch_measured_on_round_balls():
    mod = _script("build_ball_rim_dataset")
    # 16:9 frames squashed to 640x640: a round ball w px wide is 1.78 w px tall
    recs = [(None, 640, 640, [(0, 0.5, 0.5, 0.02, 0.02 * 16 / 9)])] * 25
    assert np.isclose(mod.frame_stretch(recs), 16 / 9)
    assert mod.frame_stretch(recs[:5]) == 1.0  # too few balls to tell
