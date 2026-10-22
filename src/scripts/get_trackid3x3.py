"""Download the TrackID3x3 videos (public Google Drive; github.com/open-starlab/TrackID3x3) used to build the court set.

  python src/scripts/get_trackid3x3.py                  # outdoor (12 x ~1.3 GB) + indoor (42 small clips) + drone 1-1
  python src/scripts/get_trackid3x3.py --only IMG_0105 IMG_0110   # just these outdoor recordings

Files land in data/raw/trackid3x3/videos/{outdoor,indoor,drone}; existing files are skipped.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nextrun_cv.config import REPO_ROOT  # noqa: E402

OUTDOOR = {"IMG_0104": "1B4WgkrIrPaIe-kIRd5Kq8XouUmezolL_", "IMG_0105": "1JmRa6HJp-06pyxHp11G0YOb05tf1wtcC",
           "IMG_0106": "1TGBRoqUcUqZUL33tI1up9OobLtOCQNhw", "IMG_0107": "12Ge8yz1W2BKnrxpX-TM1_ZttArVLnMc0",
           "IMG_0108": "13j5W53tJqPYpTKSFI_zyi3LMqZVy-EFH", "IMG_0109": "134s82zCspw8zdSYBa21__fHLnIXSialZ",
           "IMG_0110": "1H93_doyUuuXQg1SWR-g5FQRXjjUf5bSu", "IMG_0111": "1FJeSP6gSITTjyA6IPJWKlfVDu4RlOWfF",
           "IMG_0112": "1Oc1YlDw4eUfXV-iga4Z_dbkGhVZ-67Pp", "IMG_0113": "1gL63ham7IZM6SLGVTCu-wcJwc3weJ9eL",
           "IMG_0114": "13sIrq7X5xn2Fp-_kQS_mRpI7NoH5PD6M", "IMG_0115": "1e3-gRZ4luCu_2XwiZpuHQpGUHqtostB1"}
INDOOR_FOLDER = "1q0L_Mmf5cwb-Yv51NTjgQcF12Is0fYCB"
DRONE = {"1-1": "1Xd5dcy3N5SyvdQ887lownjvL38fLl5JD"}


def gdown(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "gdown", "-q", *args], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "raw" / "trackid3x3" / "videos"))
    ap.add_argument("--only", nargs="*", help="outdoor recordings to fetch (default: all, plus indoor and drone)")
    a = ap.parse_args()
    out = Path(a.out)
    for sub in ("outdoor", "drone"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for name, fid in OUTDOOR.items():
        if (a.only is None or name in a.only) and not (out / "outdoor" / f"{name}.MOV").exists():
            gdown([fid, "-O", str(out / "outdoor" / f"{name}.MOV")])
            print("outdoor", name)
    if a.only is None:
        for name, fid in DRONE.items():
            if not (out / "drone" / f"{name}.mov").exists():
                gdown([fid, "-O", str(out / "drone" / f"{name}.mov")])
                print("drone", name)
    if not (out / "indoor").is_dir():
        gdown(["--folder", INDOOR_FOLDER, "-O", str(out / "indoor")])
        print("indoor clips")


if __name__ == "__main__":
    main()
