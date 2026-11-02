"""Synthetic court-keypoint images for camera views the real sets lack: drones, ground-level phones, stands.

  python src/scripts/synth_court.py --out data/court24s --base data/court24 --render 2500 --rewarp 2000
  python src/scripts/synth_court.py --out data/court_synth_test --render 300 --test --seed 99   # held-out views

Two generators, both labelled exactly (the court is a plane, so a homography carries every keypoint):
- render: courts drawn from scratch (FIBA / NBA / high school) on random surface colours, often with
  neighbouring courts, plus hoops, people, poles and a skyline, seen by a random camera.
- rewarp: real labelled training images (--base train split) re-projected to a new camera. Content above the
  floor (players, stands) gets smeared, but the court surface, lines and lighting stay real.
Cameras: 40 % ground / handheld (0.2-2 m), 25 % raised (2.5-8 m), 35 % drone (8-35 m); positions all around
and inside the court, 45-110 deg lenses, some portrait frames, partial views down to 4 keypoints.
Labels follow the real sets' conventions: same handedness as the top-down template, and of the two
180-degree-symmetric labellings the one where the camera looks along +x more than +y (d_x > d_y), which
holds for every real training image.

With --base, out/ also gets the base set's images (symlinked) and a data.yaml with its val/test splits, so
it trains like court24 with the synthetic images added to train. Without --base (--test), everything goes in
test/ as sources synth_<court>_<camera> / synthwarp_<source>_<camera>, which eval_court.py scores with the right court geometry.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import CourtSpec  # noqa: E402
from nextrun_cv.court import template  # noqa: E402
from nextrun_cv.court.keypoints import keypoints_for_court, load_keypoint_config, orientation_sign  # noqa: E402
from nextrun_cv.court.venues import load_venue  # noqa: E402
from nextrun_cv.datasets import pose_label  # noqa: E402

KP = load_keypoint_config(ROOT.parent / "weights" / "court" / "court_keypoints.json")
N_KP = 24
PPM = 40  # render texture pixels per meter

# (court floor, paint, surround) BGR; outdoor community courts first
PALETTES = [((70, 140, 40), (60, 60, 190), (60, 60, 170)),      # green / red (the drone court)
            ((150, 100, 40), (60, 120, 50), (70, 140, 60)),     # blue / green
            ((80, 140, 60), (80, 140, 60), (90, 90, 90)),       # green on asphalt
            ((120, 120, 120), (120, 120, 120), (100, 100, 100)),  # plain asphalt
            ((110, 160, 210), (60, 100, 170), (90, 110, 130)),  # wood gym
            ((80, 120, 200), (50, 80, 180), (60, 60, 60)),      # orange / red
            ((140, 80, 60), (60, 60, 160), (70, 70, 70)),       # navy / red
            ((170, 170, 170), (150, 110, 70), (130, 130, 130))]  # concrete


def spec_by_name(name: str) -> CourtSpec:
    return CourtSpec.preset({"hs": "highschool"}.get(name, name))


# --- camera -------------------------------------------------------------------------------------------------
def sample_camera(rng: np.random.Generator, spec: CourtSpec, kind: str | None = None):
    """-> (P 3x4 world->image, w, h, kind). World frame: court meters, z up. Pixels follow the court
    frame's handedness (checked by the caller)."""
    L2, W2 = spec.length / 2, spec.width / 2
    kind = kind or rng.choice(["ground", "raised", "drone"], p=[0.4, 0.25, 0.35])
    portrait = kind == "ground" and rng.random() < 0.2
    w, h = (1080, 1920) if portrait else (1920, 1080)
    if kind == "ground":
        z = rng.uniform(0.2, 2.0)
        r = rng.uniform(-0.3, 1.0)  # <0: standing inside the court
    elif kind == "raised":
        z = rng.uniform(2.5, 8.0)
        r = rng.uniform(0.0, 1.0)
    else:
        z = rng.uniform(8.0, 35.0)
        r = rng.uniform(-0.5, 1.2)
    a = rng.uniform(0, 2 * math.pi)
    # position: on a rounded rectangle around the court, r = 0 at the lines, 1 = ~12 m out
    cx = math.cos(a) * (L2 + 12 * r) if abs(math.cos(a)) > 1e-3 else 0.0
    cy = math.sin(a) * (W2 + 12 * r)
    # look at a point on the court, biased to the half the camera faces / is near
    tx = rng.uniform(-L2, L2) * 0.8
    ty = rng.uniform(-W2, W2) * 0.7
    if kind == "ground" and rng.random() < 0.5:  # phone filming the near basket's half court
        tx = math.copysign(rng.uniform(0.3, 0.9) * L2, cx if abs(cx) > 1 else rng.uniform(-1, 1))
    C, T = np.array([cx, cy, z]), np.array([tx, ty, 0.0])
    if kind == "ground":
        T[2] = rng.uniform(0.0, 1.5)  # ground cameras look roughly level
    f = T - C
    if np.linalg.norm(f[:2]) < 1.0:
        f[:2] += rng.normal(size=2)
    f /= np.linalg.norm(f)
    x = np.cross(f, [0, 0, 1.0])
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0, 0])
    x /= np.linalg.norm(x)
    y = np.cross(f, x)
    roll = rng.normal(0, 0.04 if kind != "drone" else 0.02)
    x, y = math.cos(roll) * x + math.sin(roll) * y, -math.sin(roll) * x + math.cos(roll) * y
    R = np.stack([x, y, f])
    fov = math.radians(rng.uniform(45, 110) if kind == "ground" else rng.uniform(45, 90))
    fx = (max(w, h) / 2) / math.tan(fov / 2)
    K = np.array([[fx, 0, w / 2], [0, fx, h / 2], [0, 0, 1.0]])
    P = K @ np.c_[R, -R @ C]
    return P, w, h, kind


def floor_h(P: np.ndarray) -> np.ndarray:
    """Court (x, y) -> image homography of a camera matrix."""
    return P[:, [0, 1, 3]]


def mirror_y(P: np.ndarray) -> np.ndarray:
    return P @ np.diag([1.0, -1.0, 1.0, 1.0])


def canonical_camera(P: np.ndarray, w: int, h: int) -> np.ndarray | None:
    """Fix handedness and the 180-degree labelling choice; None if the court isn't in a usable view."""
    Hc = floor_h(P)
    try:
        Hi = np.linalg.inv(Hc)
    except np.linalg.LinAlgError:
        return None
    if orientation_sign(Hi, (w / 2, h * 0.8)) < 0:
        P = mirror_y(P)
        Hc = floor_h(P)
        Hi = np.linalg.inv(Hc)
    # viewing direction on the floor, as the real-set check computed it: floor under the frame center minus
    # floor under the bottom edge (or the camera's forward axis if the center is above the horizon)
    a, b = Hi @ [w / 2, h - 1, 1.0], Hi @ [w / 2, h / 2, 1.0]
    if a[2] * b[2] > 0:
        d = b[:2] / b[2] - a[:2] / a[2]
    else:
        fwd = np.linalg.inv(P[:, :3]) @ [w / 2, h / 2, 1.0]
        d = fwd[:2]
    if d[0] <= d[1]:  # rotate the world 180 degrees about center court (same picture, other labelling)
        P = P @ np.diag([-1.0, -1.0, 1.0, 1.0])
    return P


def front_mask(P: np.ndarray, w: int, h: int) -> np.ndarray:
    """Pixels that see the floor in front of the camera (below the horizon)."""
    Hi = np.linalg.inv(floor_h(P))
    C = -np.linalg.inv(P[:, :3]) @ P[:, 3]
    u, v = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    q = Hi[2, 0] * u + Hi[2, 1] * v + Hi[2, 2]
    # floor point seen at the bottom-center pixel is in front when the camera is above the floor
    ref = Hi @ [w / 2, h - 1, 1.0]
    ok_sign = np.sign(ref[2]) if C[2] > 0 else 0
    return (np.sign(q) == ok_sign) & (np.abs(q) > 1e-7)


def keypoints_in_view(P: np.ndarray, spec: CourtSpec, w: int, h: int, keep=None) -> np.ndarray:
    court = keypoints_for_court(KP, spec)
    out = np.zeros((N_KP, 3))
    for i, (x, y) in court.items():
        p = P @ [x, y, 0.0, 1.0]
        if p[2] <= 1e-6:
            continue
        u, v = p[0] / p[2], p[1] / p[2]
        if 0 <= u < w and 0 <= v < h and (keep is None or keep(u, v)):
            out[i] = (u, v, 2)
    return out


def project(P: np.ndarray, X) -> tuple[float, float] | None:
    p = P @ np.r_[X, 1.0]
    return (p[0] / p[2], p[1] / p[2]) if p[2] > 1e-3 else None


# --- render -------------------------------------------------------------------------------------------------
def court_texture(rng: np.random.Generator, spec: CourtSpec):
    """Top-down texture of the court and surroundings -> (image, texture->court affine 3x3)."""
    L, W = spec.length, spec.width
    ext_x, ext_y = L / 2 + rng.uniform(10, 40), W / 2 + rng.uniform(8, 30)
    tw, th = int(2 * ext_x * PPM), int(2 * ext_y * PPM)
    floor, paint, surround = (np.array(c, float) for c in PALETTES[rng.integers(len(PALETTES))])
    jit = lambda c: np.clip(c * rng.uniform(0.75, 1.25) + rng.normal(0, 10, 3), 0, 255)  # noqa: E731
    floor, paint, surround = jit(floor), jit(paint), jit(surround)
    img = np.empty((th, tw, 3), np.float32)
    img[:] = surround
    A = np.array([[PPM, 0, ext_x * PPM], [0, PPM, ext_y * PPM], [0, 0, 1.0]])  # court m -> texture px
    line_col = (255, 255, 255) if rng.random() < 0.85 else (80, 220, 240)
    lw = _th(1, int(rng.uniform(0.04, 0.08) * PPM))
    # neighbouring courts (same style) along x and/or y, like a park or a school yard
    offsets = [(0.0, 0.0)]
    if rng.random() < 0.6:
        gx, gy = L + rng.uniform(1.5, 6), W + rng.uniform(1.5, 6)
        for ox in (-gx, gx) if rng.random() < 0.5 else ():
            offsets.append((ox, 0.0))
        for oy in (-gy, gy) if rng.random() < 0.6 else ():
            offsets.append((0.0, oy))
    for ox, oy in offsets:
        def px(pts):
            return (np.c_[np.asarray(pts) + [ox, oy], np.ones(len(pts))] @ A.T)[:, :2].astype(np.int32)
        cv2.fillPoly(img, [px(template.court_polygon(spec, margin=rng.uniform(0, 1.5)))], floor.tolist())
        for side in (-1, 1):
            ftx = L / 2 - spec.ft_line_from_baseline
            pw2 = spec.paint_width / 2
            cv2.fillPoly(img, [px(np.array([[L / 2, -pw2], [ftx, -pw2], [ftx, pw2], [L / 2, pw2]]) * [side, 1])], paint.tolist())
        fade = rng.uniform(0.5, 1.0)
        col = (np.array(line_col) * fade + floor * (1 - fade)).tolist()
        for pl in template.polylines(spec):
            cv2.polylines(img, [px(pl)], False, col, lw, cv2.LINE_AA)
    # wear: blotches and noise
    for _ in range(rng.integers(0, 30)):
        c = (int(rng.uniform(0, tw)), int(rng.uniform(0, th)))
        cv2.circle(img, c, int(rng.uniform(5, 4 * PPM)), (img[c[1], c[0]] * rng.uniform(0.8, 1.15)).tolist(), -1)
    img += rng.normal(0, rng.uniform(2, 10), img.shape).astype(np.float32)
    img = cv2.GaussianBlur(np.clip(img, 0, 255), (0, 0), rng.uniform(0.3, 1.2))
    return img.astype(np.uint8), A, offsets


def sky_background(rng: np.random.Generator, w: int, h: int) -> np.ndarray:
    top, bot = rng.uniform(150, 255, 3), rng.uniform(120, 240, 3)
    t = np.linspace(0, 1, h)[:, None, None]
    bg = (top * (1 - t) + bot * t) * np.ones((1, w, 1))
    for _ in range(rng.integers(3, 25)):  # buildings / trees / walls
        x0, x1 = sorted(rng.integers(0, w, 2))
        y0 = int(rng.uniform(0.1, 0.9) * h)
        cv2.rectangle(bg, (int(x0), y0), (int(x1), h), rng.uniform(30, 220, 3).tolist(), -1)
    return bg.astype(np.uint8)


def draw_scene_3d(rng: np.random.Generator, im: np.ndarray, P: np.ndarray, spec: CourtSpec, offsets) -> None:
    """Hoops, poles, fence and people, drawn far-to-near."""
    L2, W2 = spec.length / 2, spec.width / 2
    C = -np.linalg.inv(P[:, :3]) @ P[:, 3]
    items = []
    for ox, oy in offsets:
        for side in (-1, 1):
            bx = side * (L2 - spec.backboard_from_baseline) + ox
            items.append(("hoop", np.array([bx, oy]), side))
    for _ in range(rng.integers(0, 6)):  # light poles
        items.append(("pole", np.array([rng.uniform(-L2 - 8, L2 + 8), rng.choice([-1, 1]) * (W2 + rng.uniform(1, 6))]), 0))
    for _ in range(rng.integers(0, 14)):  # people, mostly on the main court
        items.append(("person", np.array([rng.uniform(-L2 - 2, L2 + 2), rng.uniform(-W2 - 2, W2 + 2)]), 0))
    items.sort(key=lambda it: -np.linalg.norm(it[1] - C[:2]))
    for kind, (x, y), side in items:
        if kind == "hoop":
            pole_x = x + side * rng.uniform(0.8, 1.6)
            a, b = project(P, [pole_x, y, 0]), project(P, [pole_x, y, 3.3])
            board = [project(P, [x, y + dy, z]) for dy, z in ((-0.9, 2.9), (0.9, 2.9), (0.9, 3.95), (-0.9, 3.95))]
            rim = [project(P, [x - side * (0.15 + 0.23 * (1 + math.cos(t))), y + 0.23 * math.sin(t), 3.05])
                   for t in np.linspace(0, 2 * math.pi, 16)]
            if a and b:
                cv2.line(im, tuple(map(int, a)), tuple(map(int, b)), rng.uniform(40, 200, 3).tolist(), _th(1, int(_scale(P, [pole_x, y, 1.5]) * 0.15)))
            if all(board):
                cv2.fillPoly(im, [np.int32(board)], rng.uniform(170, 255, 3).tolist())
                cv2.polylines(im, [np.int32(board)], True, (40, 40, 40), 1)
            if all(rim):
                cv2.polylines(im, [np.int32(rim)], True, (30, 90, 230), _th(1, int(_scale(P, [x, y, 3.05]) * 0.03)))
        elif kind == "pole":
            a, b = project(P, [x, y, 0]), project(P, [x, y, rng.uniform(6, 12)])
            if a and b:
                cv2.line(im, tuple(map(int, a)), tuple(map(int, b)), rng.uniform(150, 255, 3).tolist(), _th(1, int(_scale(P, [x, y, 2]) * 0.2)))
        else:
            ht = rng.uniform(1.6, 2.0)
            feet, head = project(P, [x, y, 0]), project(P, [x, y, ht])
            if feet and head:
                s = _scale(P, [x, y, ht / 2])
                col = rng.uniform(10, 240, 3).tolist()
                cv2.line(im, tuple(map(int, feet)), tuple(map(int, head)), col, _th(2, int(s * 0.4)))
                cv2.circle(im, tuple(map(int, head)), _th(1, int(s * 0.12)), (60, 90, 140), -1)


def _th(lo: int, v: int) -> int:
    """Line thickness: at least lo, capped (cv2 rejects huge values when a pole is right at the lens)."""
    return int(min(max(lo, v), 60))


def _scale(P: np.ndarray, X) -> float:
    """Pixels per meter at world point X."""
    a, b = project(P, X), project(P, np.asarray(X, float) + [0, 0, 1.0])
    return float(np.hypot(a[0] - b[0], a[1] - b[1])) if a and b else 0.0


def photometric(rng: np.random.Generator, im: np.ndarray) -> np.ndarray:
    im = im.astype(np.float32)
    for _ in range(rng.integers(0, 4)):  # shadows
        pts = rng.uniform(0, 1, (4, 2)) * [im.shape[1], im.shape[0]]
        m = np.zeros(im.shape[:2], np.float32)
        cv2.fillPoly(m, [np.int32(pts)], 1.0)
        im *= 1 - cv2.GaussianBlur(m, (0, 0), 25)[..., None] * rng.uniform(0.2, 0.5)
    im = im * rng.uniform(0.6, 1.3) + rng.uniform(-25, 25)
    if rng.random() < 0.3:
        im = cv2.GaussianBlur(im, (0, 0), rng.uniform(0.5, 2.0))
    im += rng.normal(0, rng.uniform(0, 8), im.shape)
    ok, buf = cv2.imencode(".jpg", np.clip(im, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, int(rng.uniform(55, 95))])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def render_one(seed: int, kind: str | None = None):
    rng = np.random.default_rng(seed)
    cname = rng.choice(["fiba", "nba", "hs"], p=[0.5, 0.25, 0.25])
    spec = spec_by_name(cname)
    for _ in range(50):
        P, w, h, k = sample_camera(rng, spec, kind)
        P = canonical_camera(P, w, h)
        if P is None:
            continue
        kps = keypoints_in_view(P, spec, w, h)
        if (kps[:, 2] > 0).sum() >= 4:
            break
    else:
        return None
    tex, A, offsets = court_texture(rng, spec)
    M = floor_h(P) @ np.linalg.inv(A)  # texture px -> image px
    im = cv2.warpPerspective(tex, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mask = front_mask(P, w, h)
    # far floor dissolves into haze near the horizon instead of aliasing
    im = np.where(mask[..., None], im, sky_background(rng, w, h))
    draw_scene_3d(rng, im, P, spec, offsets)
    label = pose_label(kps, w, h)
    return (photometric(rng, im), label, cname, k) if label else None


# --- rewarp -------------------------------------------------------------------------------------------------
def source_spec(name: str) -> CourtSpec:
    if name.startswith("nba"):
        return CourtSpec.preset("nba")
    if name.startswith("venue_"):
        return load_venue(name[len("venue_"):])[0]
    return CourtSpec.preset("highschool")


def rewarp_one(seed: int, img_path: str):
    rng = np.random.default_rng(seed)
    src = Path(img_path).name.split("__")[0]
    spec = source_spec(src)
    im0 = cv2.imread(img_path)
    h0, w0 = im0.shape[:2]
    lab = np.array(Path(img_path.replace("/images/", "/labels/")).with_suffix(".txt").read_text().split()[5:], float).reshape(-1, 3)
    court = keypoints_for_court(KP, spec)
    ids = [i for i in range(N_KP) if lab[i, 2] > 0 and i in court]
    if len(ids) < 5:
        return None
    Hs, _ = cv2.findHomography(np.float32([court[i] for i in ids]), np.float32([lab[i, :2] * [w0, h0] for i in ids]), cv2.RANSAC, 4)
    if Hs is None:
        return None
    Hs_inv = np.linalg.inv(Hs)

    def in_source(u, v, Hn_inv):
        c = Hn_inv @ [u, v, 1.0]
        p = Hs @ (c / c[2])
        return p[2] != 0 and 0 <= p[0] / p[2] < w0 and 0 <= p[1] / p[2] < h0

    for _ in range(60):
        P, w, h, k = sample_camera(rng, spec)
        P = canonical_camera(P, w, h)
        if P is None:
            continue
        Hn = floor_h(P)
        Hn_inv = np.linalg.inv(Hn)
        kps = keypoints_in_view(P, spec, w, h, keep=lambda u, v: in_source(u, v, Hn_inv))
        if (kps[:, 2] > 0).sum() < 4:
            continue
        M = Hn @ Hs_inv  # source px -> new px
        valid = cv2.warpPerspective(np.full((h0, w0), 255, np.uint8), M, (w, h), flags=cv2.INTER_NEAREST) > 0
        valid &= front_mask(P, w, h)
        if valid.mean() < 0.35:
            continue
        im = cv2.warpPerspective(im0, M, (w, h), flags=cv2.INTER_LINEAR)
        im = np.where(valid[..., None], im, sky_background(rng, w, h))
        label = pose_label(kps, w, h)
        if label:
            return photometric(rng, im), label, src, k
    return None


# --- main ---------------------------------------------------------------------------------------------------
def _job(args):
    mode, seed, extra = args
    try:
        return mode, seed, render_one(seed, extra) if mode == "render" else rewarp_one(seed, extra)
    except Exception as e:  # noqa: BLE001
        print(f"{mode} {seed}: {e}", file=sys.stderr)
        return mode, seed, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", help="real court24 set: its train images are rewarped and its splits linked in")
    ap.add_argument("--render", type=int, default=0)
    ap.add_argument("--rewarp", type=int, default=0)
    ap.add_argument("--kind", choices=["ground", "raised", "drone"], help="render only this camera kind")
    ap.add_argument("--test", action="store_true", help="write everything to test/ (held-out evaluation set); "
                    "rewarps then come from the base set's test split and the base set is not linked in")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 8))
    a = ap.parse_args()
    out = Path(a.out)
    split = "test" if a.test else "train"
    for s in ("train", "val", "test"):
        (out / s / "images").mkdir(parents=True, exist_ok=True)
        (out / s / "labels").mkdir(parents=True, exist_ok=True)

    jobs = [("render", a.seed * 1_000_000 + i, a.kind) for i in range(a.render)]
    if a.rewarp:
        base_imgs = sorted(str(p) for p in (Path(a.base) / split / "images").glob("*.jpg")
                           if not p.name.startswith("venue_trackid3x3_drone"))  # the drone set stays unseen
        rng = np.random.default_rng(a.seed)
        jobs += [("rewarp", a.seed * 1_000_000 + 500_000 + i, base_imgs[rng.integers(len(base_imgs))]) for i in range(a.rewarp)]
    counts: dict[str, int] = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for mode, seed, res in ex.map(_job, jobs, chunksize=4):
            if res is None:
                continue
            im, label, src, kind = res
            # synth_<court>_<camera> / synthwarp_<real source>_<camera>: eval_court.py reads the court type from it
            source = f"synth_{src}_{kind}" if mode == "render" else f"synthwarp_{src}_{kind}"
            name = f"{source}__{seed}"
            cv2.imwrite(str(out / split / "images" / f"{name}.jpg"), im)
            (out / split / "labels" / f"{name}.txt").write_text(label + "\n")
            counts[source] = counts.get(source, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"{k:28s} {v}")

    if a.base and not a.test:  # link the real set in, so out/ is court24 + synthetic train images
        base = Path(a.base).resolve()
        for s in ("train", "val", "test"):
            for sub in ("images", "labels"):
                for p in (base / s / sub).iterdir():
                    dst = out / s / sub / p.name
                    if not dst.exists():
                        dst.symlink_to(p)
        yaml = (base / "data.yaml").read_text().replace(f"path: {base}", f"path: {out.resolve()}")
        (out / "data.yaml").write_text(yaml)


if __name__ == "__main__":
    main()
