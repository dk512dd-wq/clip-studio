"""Gemeinsame Helfer fuer das Clip-Tool: Pfade, ffmpeg, Logging, Status."""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CLIPTOOL_BASE") or os.path.dirname(HERE)  # .../Clip-Tool
DIRS = {
    "queue": os.path.join(BASE, "jobs", "warteschlange"),
    "running": os.path.join(BASE, "jobs", "laeuft"),
    "done": os.path.join(BASE, "jobs", "fertig"),
    "failed": os.path.join(BASE, "jobs", "fehler"),
    "status": os.path.join(BASE, "status"),
    "sources": os.path.join(BASE, "quellen"),
    "output": os.path.join(BASE, "clips"),
    "logs": os.path.join(BASE, "logs"),
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)


def ffmpeg_bin():
    env = os.environ.get("FFMPEG")
    if env and os.path.exists(env):
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError("ffmpeg nicht gefunden")


VERSION = "1.0.0"


def resolve(path):
    """Relative Pfade gelten ab dem Clip-Tool-Ordner."""
    if not path:
        return path
    path = os.path.expanduser(path)
    return path if os.path.isabs(path) else os.path.join(BASE, path)


def relative(path):
    """Absoluten Pfad im Clip-Tool-Ordner als relativen Pfad zurueckgeben."""
    try:
        r = os.path.relpath(path, BASE)
        return path if r.startswith("..") else r
    except Exception:
        return path


def log(msg, logfile=None):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg)
    # Kindprozesse des Runners schreiben stdout ohnehin ins Log: dann nicht doppelt
    if not (logfile and os.environ.get("CLIPTOOL_CHILD") == "1"):
        print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def set_status(job_id, **fields):
    path = os.path.join(DIRS["status"], f"{job_id}.json")
    data = read_json(path, {}) or {}
    data.update(fields)
    data["aktualisiert"] = time.strftime("%Y-%m-%d %H:%M:%S")
    write_json(path, data)
    return data


def run(cmd, logfile=None, check=True):
    log("$ " + " ".join(str(c) for c in cmd)[:400], logfile)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(p.stdout[-6000:] + "\n")
    if check and p.returncode != 0:
        raise RuntimeError(f"Befehl fehlgeschlagen ({p.returncode}): {p.stdout[-800:]}")
    return p


def safe_filename(title, maxlen=110):
    t = title.strip()
    for ch in [":", "?", "/", "\\", "*", "\"", "<", ">", "|"]:
        t = t.replace(ch, "_")
    t = " ".join(t.split())
    return t[:maxlen].rstrip(" .")


def is_mac():
    return sys.platform == "darwin"
