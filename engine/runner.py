"""Job-Runner: laeuft im Terminal und arbeitet Auftraege aus jobs/warteschlange ab.

Auftrag (JSON-Datei):
  {"typ": "vorbereiten", "job": "2026-11-20-rekruten-tag30", "url": "https://youtube.com/...", "konto": "stubenbuddy"}
  {"typ": "rendern", "job": "...", "plan": "/Users/.../Clip-Tool/plaene/<job>.json"}
  {"typ": "fotos", "job": "...", "album": "Clip-Studio Konto", "dateien": ["clips/konto/Folge/Titel.mp4", ...]}
Nur diese drei Typen werden ausgefuehrt. Es werden keine beliebigen Befehle angenommen.
"""
import glob
import os
import shutil
import subprocess
import sys
import time

from common import DIRS, HERE, VERSION, log, read_json, resolve, set_status, write_json

PY = sys.executable
RUNNER_LOG = os.path.join(DIRS["logs"], "runner.log")


def heartbeat(state):
    write_json(os.path.join(DIRS["status"], "_runner.json"),
               {"zustand": state, "zeit": time.strftime("%Y-%m-%d %H:%M:%S"), "unix": int(time.time()),
                "pid": os.getpid(), "version": VERSION})


def handle(path):
    name = os.path.basename(path)
    job = read_json(path)
    run_path = os.path.join(DIRS["running"], name)
    shutil.move(path, run_path)
    if not job or job.get("typ") not in ("vorbereiten", "rendern", "fotos"):
        log(f"Unbekannter Auftrag {name}", RUNNER_LOG)
        shutil.move(run_path, os.path.join(DIRS["failed"], name))
        return
    jid = job.get("job") or os.path.splitext(name)[0]
    logfile = os.path.join(DIRS["logs"], f"{jid}.log")
    heartbeat(f"arbeitet: {jid} ({job['typ']})")
    if job["typ"] == "vorbereiten":
        cmd = [PY, os.path.join(HERE, "prepare.py"), "--job", jid]
        if job.get("url"):
            cmd += ["--url", job["url"]]
        if job.get("datei"):
            cmd += ["--file", resolve(job["datei"])]
        if job.get("sprache"):
            cmd += ["--sprache", job["sprache"]]
        set_status(jid, typ="vorbereiten", konto=job.get("konto"), url=job.get("url"), schritt="start", fortschritt=1)
    elif job["typ"] == "rendern":
        cmd = [PY, os.path.join(HERE, "render.py"), "--plan", resolve(job["plan"])]
        set_status(jid, typ="rendern", schritt="start", fortschritt=60)
    else:
        # Clips in die Fotos-App importieren (fuer iCloud-Fotos aufs iPhone)
        dateien = [resolve(d) for d in job.get("dateien", []) if os.path.exists(resolve(d))]
        album = str(job.get("album") or "Clip-Studio")[:80]
        script = (
            'on run argv\n'
            '  set albumName to item 1 of argv\n'
            '  set fileList to {}\n'
            '  repeat with i from 2 to count of argv\n'
            '    set end of fileList to (POSIX file (item i of argv)) as alias\n'
            '  end repeat\n'
            '  tell application "Photos"\n'
            '    if not (exists album albumName) then make new album named albumName\n'
            '    import fileList into album albumName skip check duplicates true\n'
            '  end tell\n'
            'end run')
        cmd = ["/usr/bin/osascript", "-e", script, album] + dateien
        set_status(jid, typ="fotos", schritt="import", anzahl=len(dateien), album=album)
    log(f"Starte {name}", RUNNER_LOG)
    with open(logfile, "a", encoding="utf-8") as lf:
        p = subprocess.run(cmd, cwd=HERE, stdout=lf, stderr=subprocess.STDOUT,
                           env=dict(os.environ, CLIPTOOL_CHILD="1"))
    if p.returncode == 0:
        shutil.move(run_path, os.path.join(DIRS["done"], name))
        log(f"Fertig {name}", RUNNER_LOG)
    else:
        shutil.move(run_path, os.path.join(DIRS["failed"], name))
        set_status(jid, schritt="fehler", fehlercode=p.returncode)
        log(f"Fehler {name} (Code {p.returncode})", RUNNER_LOG)
        return
    if job["typ"] == "fotos":
        set_status(jid, schritt="fotos_fertig")


def main():
    # Nur ein Runner gleichzeitig
    import fcntl
    lock = open(os.path.join(DIRS["status"], "_runner.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Clip-Tool laeuft schon in einem anderen Fenster. Dieses Fenster kann zu.")
        return
    log(f"Clip-Tool Runner {VERSION} gestartet", RUNNER_LOG)
    # Auftraege, die beim letzten Mal mitten drin abgebrochen sind, zurueck in die Warteschlange
    for f in glob.glob(os.path.join(DIRS["running"], "*.json")):
        shutil.move(f, os.path.join(DIRS["queue"], os.path.basename(f)))
    while True:
        heartbeat("wartet")
        jobs = sorted(glob.glob(os.path.join(DIRS["queue"], "*.json")), key=os.path.getmtime)
        if jobs:
            try:
                handle(jobs[0])
            except Exception as e:
                log(f"Runner-Fehler: {e}", RUNNER_LOG)
                time.sleep(5)
        else:
            time.sleep(5)


if __name__ == "__main__":
    main()
