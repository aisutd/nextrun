"""Merge ball / rim detection datasets into one 2-class set (0 ball, 1 rim) for the ball+rim model.

  python src/scripts/build_ball_rim_dataset.py --out data/ball_rim \
      --roboflow WORKSPACE/PROJECT[/VERSION] ...   # Roboflow Universe detection sets; needs ROBOFLOW_API_KEY
      --yolo-dir PATH ...                           # local YOLO detection exports (data.yaml + splits)
      --hf suggested | OWNER/REPO ...               # public Hugging Face mirrors (COCO), no key needed
      --coco-dir PATH ...                           # local COCO exports (*/_annotations.coco.json)

Class names are mapped by meaning (basketball / sports ball -> ball; rim / hoop / basket -> rim); other
classes (players, backboards, 'made'...) are dropped, and the mapping is printed for review. Rim boxes are
made to cover rim + net (datasets.rim_with_net) for sets that box only the ring, in scene proportions
(exports stretched to squares are measured on their balls, which are round). Sets that label only one of
ball / rim are skipped unless --allow-partial. Images whose
labels end up empty are kept as background only if --keep-empty (useful negatives, e.g. crowds).
Splits are by source image / video clip (datasets.source_group), never by Roboflow's own split, so
augmented copies of one photo can't leak into test. Hugging Face / COCO sets split by clip alone (not
source + clip) and skip frames another set already added: mirrors of related Roboflow projects share
game clips.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT  # noqa: E402
from nextrun_cv.datasets import (  # noqa: E402
    YoloWriter, ball_rim_class, hf_dataset_download, rim_with_net, iter_coco_export, iter_yolo_export, read_data_yaml,
    roboflow_download, source_group, split_for,
)

# Roboflow Universe sets with both ball and rim labels (checked Oct 2026, all CC BY 4.0; verify before shipping).
# Not listed: mirrors already in HF_SUGGESTED, ball-only / rim-only sets (they'd teach "that rim is background").
SUGGESTED = [
    "computer-vision-d5fjh/basketball-detection-dn6fg",            # ~4.9k images: ball, basket, person
    "rohit-krishnan-xr6xf/basketball_and_hoops",                   # ~2.9k: basketball, rim, players
    "eagle-eye/basketball-1zhpe",                                  # ~2.6k: basketball, sports ball, rim
    "personal-project-effcw/basketball-hoop-ball-and-player-5axdt",  # ~1.3k: ball, hoop, court areas
    "ball101/rim-detection",                                       # ~1.3k: basketball, rim, people
    "basketball-yolo-dataset/basketball-yolo-dataset",             # ~0.3k: ball, hoop, player
]
# Hugging Face mirrors of Roboflow Universe sets (all CC BY 4.0), downloadable without any key:
HF_SUGGESTED = [
    "koppolusameer/basketball-coco-player-detection",  # basketball-player-detection-2: ~2.4k NBA frames, ball + rim
    "koppolusameer/basketball-coco-20260416",          # basketball-player-detection-3: ~650 NBA frames, ball + rim
    "koppolusameer/basketball-coco-2025-04-02",        # basketball-players: ~1.2k broadcast frames, Ball + Hoop
]


def frame_stretch(records) -> float:
    """How much an export stretched its frames vertically (e.g. 16:9 -> 640x640 gives 1.78), measured on the
    balls, which are round: median ball pixel height / width. 1.0 if there are too few balls to tell."""
    r = sorted(h * ih / (w * iw) for _, iw, ih, boxes in records for c, x, y, w, h in boxes if c == 0 and w > 0)
    return float(r[len(r) // 2]) if len(r) >= 20 else 1.0


def write_records(writer: YoloWriter, records, source: str, keep_empty: bool, seen: set[str], by_clip: bool) -> None:
    """records: (image, width, height, [(class, x, y, w, h)]). Rim boxes -> rim + net in scene proportions;
    frames already added (Roboflow augmentations, mirrors of related projects) are skipped."""
    stretch = frame_stretch(records)
    dup = 0
    for img, iw, ih, boxes in records:
        frame = img.name.split(".rf.")[0]
        if frame in seen:
            dup += 1
            continue
        lines = []
        for c, x, y, w, h in boxes:
            if c == 1:
                x, y, w, h = rim_with_net(x, y, w, h, iw / ih * stretch)
            lines.append(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
        if lines or keep_empty:
            seen.add(frame)
            group = source_group(img.name)
            writer.add(source, group, img.name, img, lines, split=split_for(group) if by_clip else None)
    print(f"  {source}: frame stretch {stretch:.2f}, {dup} duplicate frames skipped")


def check_classes(source: str, names: list[str], allow_partial: bool) -> bool:
    mapped = {n: ball_rim_class(n) for n in names}
    print(f"{source}: " + ", ".join(f"{n}->{['ball', 'rim'][c] if c is not None else 'drop'}" for n, c in mapped.items()))
    have = set(mapped.values()) - {None}
    if have == {0, 1} or (have and allow_partial):
        return True
    print(f"  {source}: skipped (labels {sorted(['ball', 'rim'][c] for c in have) or 'neither'}, need ball and rim)")
    return False


def add_detection_set(writer: YoloWriter, root: Path, source: str, keep_empty: bool, seen: set[str],
                      allow_partial: bool = False) -> None:
    from PIL import Image

    names = read_data_yaml(root).get("names", {})
    names = dict(enumerate(names)) if isinstance(names, list) else {int(k): v for k, v in names.items()}
    if not check_classes(source, [names[i] for i in sorted(names)], allow_partial):
        return
    remap = {i: ball_rim_class(n) for i, n in names.items()}
    records = []
    for _, img, lbl in iter_yolo_export(root):
        boxes = []
        for row in (lbl.read_text().split("\n") if lbl.exists() else []):
            parts = row.split()
            if len(parts) < 5 or remap.get(int(parts[0])) is None:
                continue
            v = list(map(float, parts[1:]))
            if len(v) > 4:  # polygon label -> bounding box
                xs, ys = v[0::2], v[1::2]
                v = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)]
            boxes.append((remap[int(parts[0])], *v))
        with Image.open(img) as im:
            records.append((img, *im.size, boxes))
    write_records(writer, records, source, keep_empty, seen, by_clip=False)


def add_coco_set(writer: YoloWriter, root: Path, source: str, keep_empty: bool, seen: set[str],
                 allow_partial: bool = False) -> None:
    records = list(iter_coco_export(root))
    if not check_classes(source, sorted({b[0] for *_, boxes in records for b in boxes}), allow_partial):
        return
    records = [(img, iw, ih, [(ball_rim_class(b[0]), *b[1:]) for b in boxes if ball_rim_class(b[0]) is not None])
               for img, iw, ih, boxes in records]
    write_records(writer, records, source, keep_empty, seen, by_clip=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "ball_rim"))
    ap.add_argument("--roboflow", nargs="*", default=[], help="WORKSPACE/PROJECT[/VERSION]; 'suggested' = built-in list")
    ap.add_argument("--yolo-dir", nargs="*", default=[])
    ap.add_argument("--hf", nargs="*", default=[], help="OWNER/REPO (COCO); 'suggested' = built-in list")
    ap.add_argument("--coco-dir", nargs="*", default=[])
    ap.add_argument("--keep-empty", action="store_true")
    ap.add_argument("--allow-partial", action="store_true", help="keep sets that label only ball or only rim")
    a = ap.parse_args()

    slugs = [s for r in a.roboflow for s in (SUGGESTED if r == "suggested" else [r])]
    writer = YoloWriter(Path(a.out))
    seen: set[str] = set()
    for slug in slugs:
        try:
            root = roboflow_download(slug, "yolov8", REPO_ROOT / "data" / "raw" / "roboflow")
        except Exception as e:  # one dead/private project shouldn't stop the build
            print(f"{slug}: download failed: {e}")
            continue
        add_detection_set(writer, root, "rf_" + slug.split("/")[1], a.keep_empty, seen, a.allow_partial)
    for d in a.yolo_dir:
        add_detection_set(writer, Path(d), "local_" + Path(d).name, a.keep_empty, seen, a.allow_partial)
    for repo in [r for h in a.hf for r in (HF_SUGGESTED if h == "suggested" else [h])]:
        root = hf_dataset_download(repo, REPO_ROOT / "data" / "raw" / "hf")
        add_coco_set(writer, root, "hf_" + repo.split("/")[1], a.keep_empty, seen, a.allow_partial)
    for d in a.coco_dir:
        add_coco_set(writer, Path(d), "local_" + Path(d).name, a.keep_empty, seen, a.allow_partial)
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
