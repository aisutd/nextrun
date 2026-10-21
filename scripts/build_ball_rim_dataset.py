"""Merge ball / rim detection datasets into one 2-class set (0 ball, 1 rim) for the ball+rim model.

  python scripts/build_ball_rim_dataset.py --out data/ball_rim \
      --roboflow WORKSPACE/PROJECT[/VERSION] ...   # Roboflow Universe detection sets; needs ROBOFLOW_API_KEY
      --yolo-dir PATH ...                           # local YOLO detection exports (data.yaml + splits)

Class names are mapped by meaning (basketball / sports ball -> ball; rim / hoop / basket -> rim); other
classes (players, backboards, 'made'...) are dropped, and the mapping is printed for review. Images whose
labels end up empty are kept as background only if --keep-empty (useful negatives, e.g. crowds).
Splits are by source image / video clip (datasets.source_group), never by Roboflow's own split, so
augmented copies of one photo can't leak into test.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT  # noqa: E402
from nextrun_cv.datasets import (  # noqa: E402
    YoloWriter, ball_rim_class, iter_yolo_export, read_data_yaml, roboflow_download, source_group,
)

# Starting list (Roboflow Universe, checked Oct 2026; verify licenses on each page before shipping a model):
SUGGESTED = [
    "ball101/rim-detection",                                   # ~1.3k rims, CC BY 4.0
    "computer-vision-d5fjh/basketball-detection-dn6fg",       # ~4.9k images: people, ball, hoop
    "eagle-eye/basketball-1zhpe",                             # basketball, sports ball, rim
    "personal-project-effcw/basketball-hoop-ball-and-player-5axdt",
    "basketball-yolo-dataset/basketball-yolo-dataset",
]


def add_detection_set(writer: YoloWriter, root: Path, source: str, keep_empty: bool) -> None:
    names = read_data_yaml(root).get("names", {})
    names = dict(enumerate(names)) if isinstance(names, list) else {int(k): v for k, v in names.items()}
    remap = {i: ball_rim_class(n) for i, n in names.items()}
    print(f"{source}: " + ", ".join(f"{n}->{['ball', 'rim'][c] if c is not None else 'drop'}" for n, c in
                                    ((names[i], remap[i]) for i in sorted(names))))
    if not any(c is not None for c in remap.values()):
        print(f"  {source}: no ball/rim classes, skipped")
        return
    for _, img, lbl in iter_yolo_export(root):
        lines = []
        for row in (lbl.read_text().split("\n") if lbl.exists() else []):
            parts = row.split()
            if len(parts) < 5:
                continue
            c = remap.get(int(parts[0]))
            if c is None:
                continue
            if len(parts) > 5:  # polygon label -> bounding box
                xs, ys = map(float, parts[1::2]), map(float, parts[2::2])
                xs, ys = list(xs), list(ys)
                x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
                parts = [str(c), f"{(x1 + x2) / 2:.6f}", f"{(y1 + y2) / 2:.6f}", f"{x2 - x1:.6f}", f"{y2 - y1:.6f}"]
            lines.append(" ".join([str(c)] + parts[1:5]))
        if lines or keep_empty:
            writer.add(source, source_group(img.name), img.name, img, lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "ball_rim"))
    ap.add_argument("--roboflow", nargs="*", default=[], help="WORKSPACE/PROJECT[/VERSION]; 'suggested' = built-in list")
    ap.add_argument("--yolo-dir", nargs="*", default=[])
    ap.add_argument("--keep-empty", action="store_true")
    a = ap.parse_args()

    slugs = [s for r in a.roboflow for s in (SUGGESTED if r == "suggested" else [r])]
    writer = YoloWriter(Path(a.out))
    for slug in slugs:
        try:
            root = roboflow_download(slug, "yolov8", REPO_ROOT / "data" / "raw" / "roboflow")
        except Exception as e:  # one dead/private project shouldn't stop the build
            print(f"{slug}: download failed: {e}")
            continue
        add_detection_set(writer, root, "rf_" + slug.split("/")[1], a.keep_empty)
    for d in a.yolo_dir:
        add_detection_set(writer, Path(d), "local_" + Path(d).name, a.keep_empty)
    writer.write_lists()
    out = Path(a.out)
    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\n"
        "names:\n  0: ball\n  1: rim\n"
    )
    for src, c in writer.counts.items():
        print(f"{src:40s} " + "  ".join(f"{s}={n}" for s, n in c.items()))


if __name__ == "__main__":
    main()
