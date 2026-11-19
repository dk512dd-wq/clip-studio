"""Schritt 1: Folge laden, Ton extrahieren, Transkript mit Wort-Zeitstempeln und Lautstaerke-Kurve erstellen.

Ergebnis in quellen/<job_id>/:
  source.mp4, info.json, audio.wav, transcript.json, transcript.txt, energy.json
"""
import argparse
import json
import os
import re
import sys
import wave

import numpy as np

from common import DIRS, ffmpeg_bin, log, read_json, relative, resolve, run, set_status, write_json


def download(url, outdir, logfile):
    target = os.path.join(outdir, "source.mp4")
    if os.path.exists(target) and os.path.getsize(target) > 1_000_000:
        info = read_json(os.path.join(outdir, "info.json"), {}) or {}
        if not info.get("dauer"):
            try:
                import yt_dlp  # noqa
                with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as y:
                    r = y.extract_info(url, download=False)
                e = (r.get("entries") or [r])[0] if r.get("entries") is not None else r
                write_json(os.path.join(outdir, "info.json"), {
                    "titel": e.get("title"), "kanal": e.get("channel") or e.get("uploader"),
                    "dauer": e.get("duration"), "url": e.get("url") if str(e.get("url", "")).startswith("http") else e.get("webpage_url", url)})
            except Exception as ex:
                log(f"Info nicht nachgeladen: {ex}", logfile)
        return target
    import yt_dlp  # noqa
    if url.startswith("ytsearch"):
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as y:
            r = y.extract_info(url, download=False)
        e = (r.get("entries") or [None])[0]
        if not e:
            raise RuntimeError("Suche ohne Treffer: " + url)
        url = e.get("url") or e.get("webpage_url") or url
        log(f"Suche aufgeloest: {e.get('title')} -> {url}", logfile)
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--newline",
           "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
           "--merge-output-format", "mp4", "--ffmpeg-location", ffmpeg_bin(),
           "--write-info-json", "-o", os.path.join(outdir, "source.%(ext)s"), url]
    run(cmd, logfile)
    if not os.path.exists(target):
        cands = [f for f in os.listdir(outdir) if f.startswith("source.") and f.endswith((".mp4", ".mkv", ".webm"))]
        if not cands:
            raise RuntimeError("Download fehlgeschlagen, keine Videodatei gefunden")
        src = os.path.join(outdir, cands[0])
        run([ffmpeg_bin(), "-y", "-i", src, "-c", "copy", target], logfile)
    info_path = os.path.join(outdir, "source.info.json")
    info = read_json(info_path, {}) or {}
    write_json(os.path.join(outdir, "info.json"), {
        "titel": info.get("title"), "kanal": info.get("channel") or info.get("uploader"),
        "dauer": info.get("duration"), "url": info.get("webpage_url") or url, "upload": info.get("upload_date"),
        "beschreibung": (info.get("description") or "")[:2000],
    })
    if os.path.exists(info_path):
        os.remove(info_path)
    return target


def extract_audio(src, outdir, logfile):
    wav = os.path.join(outdir, "audio.wav")
    if not os.path.exists(wav):
        run([ffmpeg_bin(), "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav], logfile)
    return wav


def energy_curve(wav):
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    n = len(data) // sr
    vals = []
    for i in range(n):
        seg = data[i * sr:(i + 1) * sr]
        rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        vals.append(round(20 * np.log10(rms), 1))
    return vals


def transcribe(wav, language, logfile, model_hint=None):
    """mlx-whisper auf Apple Silicon, sonst faster-whisper."""
    words_out = []
    segs_out = []
    try:
        import mlx_whisper
        repo = model_hint or "mlx-community/whisper-large-v3-turbo"
        log(f"Transkribiere mit mlx-whisper ({repo})", logfile)
        with wave.open(wav, "rb") as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        res = mlx_whisper.transcribe(audio, path_or_hf_repo=repo, language=language,
                                     word_timestamps=True, condition_on_previous_text=False, verbose=False)
        for s in res.get("segments", []):
            ws = [{"w": x["word"].strip(), "s": round(float(x["start"]), 3), "e": round(float(x["end"]), 3)}
                  for x in s.get("words", []) if x.get("word", "").strip()]
            segs_out.append({"s": round(float(s["start"]), 2), "e": round(float(s["end"]), 2),
                             "text": s.get("text", "").strip(), "words": ws})
    except ImportError:
        from faster_whisper import WhisperModel
        name = model_hint or "large-v3-turbo"
        log(f"Transkribiere mit faster-whisper ({name})", logfile)
        model = WhisperModel(name, compute_type="int8")
        segments, _ = model.transcribe(wav, language=language, word_timestamps=True, vad_filter=True)
        for s in segments:
            ws = [{"w": x.word.strip(), "s": round(x.start, 3), "e": round(x.end, 3)} for x in (s.words or []) if x.word.strip()]
            segs_out.append({"s": round(s.start, 2), "e": round(s.end, 2), "text": s.text.strip(), "words": ws})
    for s in segs_out:
        words_out.extend(s["words"])
    return segs_out


def fmt(t):
    t = int(t)
    return f"{t // 3600:d}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def write_readable(segs, path):
    with open(path, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"[{fmt(s['s'])}-{fmt(s['e'])}] {s['text']}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--url")
    ap.add_argument("--file")
    ap.add_argument("--sprache", default="de")
    ap.add_argument("--modell")
    a = ap.parse_args()
    outdir = os.path.join(DIRS["sources"], a.job)
    os.makedirs(outdir, exist_ok=True)
    logfile = os.path.join(DIRS["logs"], f"{a.job}.log")
    set_status(a.job, schritt="download", fortschritt=5)
    if a.file:
        src = os.path.join(outdir, "source.mp4")
        if not os.path.exists(src):
            run([ffmpeg_bin(), "-y", "-i", a.file, "-c", "copy", src], logfile)
        write_json(os.path.join(outdir, "info.json"), {"titel": os.path.basename(a.file), "datei": a.file})
    else:
        src = download(a.url, outdir, logfile)
    set_status(a.job, schritt="ton", fortschritt=30)
    wav = extract_audio(src, outdir, logfile)
    write_json(os.path.join(outdir, "energy.json"), energy_curve(wav))
    set_status(a.job, schritt="transkript", fortschritt=40)
    tpath = os.path.join(outdir, "transcript.json")
    if not os.path.exists(tpath):
        segs = transcribe(wav, a.sprache, logfile, a.modell)
        write_json(tpath, {"sprache": a.sprache, "segmente": segs})
        write_readable(segs, os.path.join(outdir, "transcript.txt"))
    set_status(a.job, schritt="bereit_fuer_auswahl", fortschritt=60,
               transkript=relative(tpath), quelle=relative(src),
               transkript_text=relative(os.path.join(outdir, "transcript.txt")))
    log("Vorbereitung fertig", logfile)


if __name__ == "__main__":
    main()
