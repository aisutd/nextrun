#!/usr/bin/env python3
"""NextRun: one command to run everything.   python run.py [--weights PATH_TO_nextrun-model_merge.zip_OR_FOLDER]

Installs the backend (Python venv) and the app (npm) on first run, then starts
  backend  http://localhost:8000   (FastAPI + the YOLO models)
  app      http://localhost:8081   (React Native / Expo, web)
Open the app, go to the Camera tab -> Upload -> Choose video.  Ctrl+C stops both."""
import json, os, shutil, subprocess, sys, time, venv, webbrowser, zipfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
BE, APP, VENV = ROOT / "backend", ROOT / "app", ROOT / ".venv"
WIN = os.name == "nt"
PY = VENV / ("Scripts/python.exe" if WIN else "bin/python")
NPM, NPX = ("npm.cmd", "npx.cmd") if WIN else ("npm", "npx")


def run(cmd, cwd=None, **kw):
    print("  $", " ".join(map(str, cmd)))
    subprocess.check_call(list(map(str, cmd)), cwd=cwd, **kw)


def missing_weights():
    act = json.loads((BE / "weights/active.json").read_text())
    return [w for w in act.values() if not (BE / "weights" / w).exists() and not w.startswith("players/")]


def install_weights(src: Path):
    print(f"Copying model weights from {src}")
    if src.is_dir():
        w = src / "weights" if (src / "weights").is_dir() else src
        shutil.copytree(w, BE / "weights", dirs_exist_ok=True)
        return
    with zipfile.ZipFile(src) as z:
        for n in z.namelist():
            if "/weights/" in n and not n.endswith("/"):
                dst = BE / "weights" / n.split("/weights/", 1)[1]
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as a, open(dst, "wb") as b:
                    shutil.copyfileobj(a, b)


def find_weights():
    for base in (ROOT, ROOT.parent, Path.home() / "Downloads", Path.home() / "Desktop"):
        for name in ("nextrun-model_merge.zip", "nextrun-model_merge"):
            if (base / name).exists():
                return base / name


def main():
    args = sys.argv[1:]
    if "--weights" in args:
        install_weights(Path(args[args.index("--weights") + 1]).expanduser())
    if missing_weights():
        found = find_weights()
        if found:
            install_weights(found)
    if missing_weights():
        sys.exit("Model weights are missing: " + ", ".join(missing_weights()) +
                 "\nRun:  python run.py --weights path/to/nextrun-model_merge.zip   (your original models zip)")

    if not PY.exists():
        print("Creating Python environment…")
        venv.create(VENV, with_pip=True)
    if not (VENV / ".installed").exists():
        print("Installing backend (first run downloads PyTorch, a few minutes)…")
        run([PY, "-m", "pip", "install", "-q", "-e", f"{BE}[detect,api]"])
        (VENV / ".installed").write_text("ok")
    if subprocess.call([str(PY), "-c", "import imageio_ffmpeg"], stderr=subprocess.DEVNULL) != 0:
        run([PY, "-m", "pip", "install", "-q", "imageio-ffmpeg"])  # bundled ffmpeg, so the result video plays in browsers
    if not (APP / "node_modules").exists():
        print("Installing app…")
        run([NPM, "install"], cwd=APP)
    if not (APP / "node_modules/expo-video").exists():
        run([NPX, "expo", "install", "expo-video"], cwd=APP)

    env = {**os.environ, "NEXTRUN_DATA": str(BE / "results/games")}
    api = subprocess.Popen([str(PY), "-m", "uvicorn", "nextrun_cv.api:app", "--host", "0.0.0.0", "--port", "8000"], cwd=BE, env=env)
    app = subprocess.Popen([NPX, "expo", "start", "--web", "--port", "8081"], cwd=APP,
                           env={**env, "EXPO_PUBLIC_API_URL": "http://localhost:8000", "CI": "0"})
    time.sleep(8)
    webbrowser.open("http://localhost:8081")
    print("\nNextRun is running: app http://localhost:8081 · API docs http://localhost:8000/docs · Ctrl+C to stop\n")
    try:
        api.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (api, app):
            p.terminate()


if __name__ == "__main__":
    main()
