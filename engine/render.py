"""Schritt 3: Clips nach Plan rendern (9:16, Gesichtsverfolgung, Hook-Box, Wort-Untertitel im Opus-Stil).

Plan (JSON):
{
  "job": "...", "konto": "stubenbuddy", "quelle": ".../source.mp4", "transkript": ".../transcript.json",
  "stil": { ...ueberschreibt Kontoeinstellungen... },
  "clips": [ {"nr":1, "start":12.3, "ende":48.0, "titel":"...", "hook":"...", "intro_wort":null,
               "schluesselwoerter":["..."], "score":87, "noten":{"hook":"A","flow":"A-","value":"B","trend":"B"},
               "grund":"..."} ]
}
"""
import argparse
import math
import os
import re
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import resolve, relative, DIRS, HERE, ffmpeg_bin, is_mac, log, read_json, safe_filename, set_status, write_json

OUT_W, OUT_H = 1080, 1920
FONT_DIR = os.path.join(HERE, "fonts")
MODEL_DIR = os.path.join(HERE, "models")

DEFAULT_STYLE = {
    "layout": "fuellen",            # fuellen | anpassen
    "fps": 25,
    "untertitel": True,
    "untertitel_stil": "opus_klassik",  # opus_klassik | karaoke | box
    "untertitel_woerter": 2,
    "untertitel_max_zeichen": 16,
    "untertitel_groesse": 0.11,      # Anteil der Bildbreite
    "untertitel_hoehe": 0.805,       # Mittelpunkt, Anteil der Bildhoehe
    "untertitel_farbe": "#FFFFFF",
    "akzent_farbe": "#FFD60A",
    "schluesselwoerter_faerben": False,
    "grossbuchstaben": True,
    "pop_animation": True,
    "hook": True,
    "hook_schreibweise": "gross",     # gross | normal
    "hook_dauer": 3.0,
    "hook_groesse": 0.052,
    "intro_wort": False,
    "qualitaet": "hoch",
}


# ---------------------------------------------------------------- Hilfen

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(name, size, variation=None):
    path = os.path.join(FONT_DIR, name)
    f = ImageFont.truetype(path, size)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    return f


def probe(src):
    cap = cv2.VideoCapture(src)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return w, h, fps, (n / fps if fps else 0)


def read_frames(src, start, dur, w, h, fps, scale=None):
    """Liefert Frames (RGB, numpy) eines Abschnitts via ffmpeg-Pipe."""
    vf = f"fps={fps}"
    ow, oh = w, h
    if scale:
        ow, oh = scale
        vf += f",scale={ow}:{oh}"
    cmd = [ffmpeg_bin(), "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
           "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=ow * oh * 3 * 4)
    size = ow * oh * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(oh, ow, 3)
    finally:
        p.stdout.close()
        p.wait()


# ---------------------------------------------------------------- Gesichtsverfolgung

class FaceFinder:
    def __init__(self, w, h):
        self.det = None
        model = os.path.join(MODEL_DIR, "face_detection_yunet_2023mar.onnx")
        if os.path.exists(model) and hasattr(cv2, "FaceDetectorYN"):
            try:
                self.det = cv2.FaceDetectorYN.create(model, "", (w, h), 0.6, 0.3, 50)
            except Exception:
                self.det = None
        self.haar = None
        if self.det is None:
            self.haar = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))

    def faces(self, img_rgb):
        if self.det is not None:
            bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            _, f = self.det.detect(bgr)
            if f is None:
                return []
            return [(float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[14])) for x in f]
        g = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        r = self.haar.detectMultiScale(g, 1.15, 5, minSize=(30, 30))
        return [(float(x), float(y), float(ww), float(hh), 0.7) for (x, y, ww, hh) in r]


def track_centers(src, start, dur, w, h, sample_fps=4):
    """Horizontale Bildmitte (Quell-Pixel) pro Abtastzeit; geglaettet, mit Schnitt-Erkennung."""
    sw = 640
    sh = int(round(h * sw / w / 2) * 2)
    ff = FaceFinder(sw, sh)
    scale = w / sw
    times, raw = [], []
    prev_small = None
    cuts = []
    for i, fr in enumerate(read_frames(src, start, dur, w, h, sample_fps, scale=(sw, sh))):
        t = i / sample_fps
        small = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY), (64, 36))
        if prev_small is not None and float(np.mean(np.abs(small.astype(np.int16) - prev_small))) > 28:
            cuts.append(t)
        prev_small = small.astype(np.int16)
        fs = ff.faces(fr)
        cx = None
        if fs:
            # groesstes Gesicht, bei aehnlicher Groesse das naeher an der bisherigen Position
            fs.sort(key=lambda f: f[2] * f[3] * f[4], reverse=True)
            best = fs[0]
            if raw and raw[-1] is not None and len(fs) > 1:
                last = raw[-1]
                cands = [f for f in fs if f[2] * f[3] > 0.6 * best[2] * best[3]]
                best = min(cands, key=lambda f: abs((f[0] + f[2] / 2) * scale - last))
            cx = (best[0] + best[2] / 2) * scale
        times.append(t)
        raw.append(cx)
    if not times:
        return np.array([0.0]), np.array([w / 2])
    # Luecken fuellen
    filled = []
    last = None
    for c in raw:
        if c is not None:
            last = c
        filled.append(last)
    first = next((c for c in filled if c is not None), w / 2)
    filled = [first if c is None else c for c in filled]
    # Glaetten mit Totzone, Spruenge bei Schnitten sofort
    out = []
    cur = filled[0]
    cut_set = set(round(c, 2) for c in cuts)
    for t, c in zip(times, filled):
        if round(t, 2) in cut_set:
            cur = c
        elif abs(c - cur) > w * 0.04:
            cur = cur + (c - cur) * 0.35
        out.append(cur)
    return np.array(times), np.array(out)


# ---------------------------------------------------------------- Untertitel

PUNCT_END = re.compile(r"[.!?;:]$")


def chunk_words(words, max_words, max_chars):
    chunks, cur = [], []
    for i, w in enumerate(words):
        txt = w["w"].strip()
        if not txt:
            continue
        gap = (w["s"] - cur[-1]["e"]) if cur else 0
        length = sum(len(x["w"]) + 1 for x in cur) + len(txt)
        if cur and (len(cur) >= max_words or length > max_chars or gap > 0.6):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if PUNCT_END.search(txt):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        s = c[0]["s"]
        e = c[-1]["e"]
        nxt = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else e + 0.4
        e = min(max(e, s + 0.25), nxt) if nxt > s else e
        if nxt - e < 0.35:
            e = nxt
        out.append({"s": s, "e": e, "words": c})
    return out


def clean_word(t):
    return re.sub(r"[\"„“”‚‘’«»]", "", t)


def render_caption(text_words, style, highlight=set(), active=None):
    """Untertitel als RGBA-Bild. Stile: opus_klassik (weiss, Kontur, Schatten),
    karaoke (wie klassik, aktives Wort in Akzentfarbe), box (Text auf Akzent-Box)."""
    stil = style.get("untertitel_stil", "opus_klassik")
    size = int(OUT_W * style["untertitel_groesse"])
    f = font("BebasNeue-Regular.ttf", size)
    words = [clean_word(w) for w in text_words]
    words = [w.upper() if style["grossbuchstaben"] else w for w in words]
    words = [re.sub(r"[,.;:]+$", "", w) for w in words]
    text = " ".join(words).strip()
    if not text:
        return None
    maxw = int(OUT_W * 0.88)
    while True:
        bbox = f.getbbox(text, stroke_width=6)
        if bbox[2] - bbox[0] <= maxw or size < 40:
            break
        size = int(size * 0.92)
        f = font("BebasNeue-Regular.ttf", size)
    pad = 30 if stil != "box" else int(size * 0.32)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    base = hex_rgb(style["untertitel_farbe"])
    accent = hex_rgb(style["akzent_farbe"])
    space = f.getlength(" ")
    if stil == "box":
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius=int(size * 0.22), fill=accent + (255,))
        x = pad - bbox[0]
        for w in words:
            d.text((x, pad - bbox[1]), w, font=f, fill=(12, 12, 12, 255))
            x += f.getlength(w) + space
        return np.array(img)
    # weicher Schatten
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - bbox[0] + 4, pad - bbox[1] + 6), text, font=f, fill=(0, 0, 0, 170),
                            stroke_width=8, stroke_fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(sh)
    d = ImageDraw.Draw(img)
    x = pad - bbox[0]
    for j, w in enumerate(words):
        hit = style["schluesselwoerter_faerben"] and w.lower().strip(",.!?") in highlight
        col = accent if (hit or (stil == "karaoke" and active == j)) else base
        d.text((x, pad - bbox[1]), w, font=f, fill=col + (255,), stroke_width=5, stroke_fill=(0, 0, 0, 255))
        x += f.getlength(w) + space
    return np.array(img)


def render_hook(text, style):
    upper = style["hook_schreibweise"] == "gross"
    t = text.upper() if upper else text
    size = int(OUT_W * style["hook_groesse"])
    f = font("Montserrat.ttf", size, "ExtraBold" if upper else "SemiBold")
    maxw = int(OUT_W * 0.80)
    # Zeilenumbruch
    words, lines, cur = t.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.getlength(test) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    while len(lines) > 3 and size > 30:
        size = int(size * 0.9)
        return render_hook(text, dict(style, hook_groesse=size / OUT_W))
    lh = int(size * 1.22)
    widths = [f.getlength(l) for l in lines]
    padx, pady = int(OUT_W * 0.035), int(OUT_W * 0.026)
    bw = int(max(widths) + padx * 2)
    bh = int(lh * len(lines) + pady * 2 - (lh - size) * 0.6)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=int(OUT_W * 0.016), fill=(255, 255, 255, 250))
    y = pady - int(size * 0.12)
    for l, lw in zip(lines, widths):
        d.text(((bw - lw) / 2, y), l, font=f, fill=(15, 15, 15, 255))
        y += lh
    return np.array(img)


def render_intro_word(word):
    word = clean_word(word).upper()
    size = int(OUT_W * 0.42)
    f = font("BebasNeue-Regular.ttf", size)
    bbox = f.getbbox(word)
    target = OUT_W * 1.08
    size = int(size * target / max(1, bbox[2] - bbox[0]))
    size = min(size, int(OUT_W * 0.6))
    f = font("BebasNeue-Regular.ttf", size)
    bbox = f.getbbox(word)
    img = Image.new("RGBA", (bbox[2] - bbox[0] + 40, bbox[3] - bbox[1] + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - bbox[0] + 6, 20 - bbox[1] + 8), word, font=f, fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).text((20 - bbox[0], 20 - bbox[1]), word, font=f, fill=(255, 255, 255, 255))
    return np.array(img)


def composite(frame, rgba, cx, cy, alpha=1.0, scale=1.0):
    """Legt ein RGBA-Bild zentriert auf (cx, cy) ins Frame (in-place)."""
    if rgba is None or alpha <= 0:
        return
    if abs(scale - 1.0) > 0.01:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sub = rgba[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    a = (sub[:, :, 3:4].astype(np.float32) / 255.0) * alpha
    region = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (sub[:, :, :3] * a + region * (1 - a)).astype(np.uint8)


# ---------------------------------------------------------------- Rendern

_ENCODERS = None


def has_encoder(name):
    global _ENCODERS
    if _ENCODERS is None:
        try:
            _ENCODERS = subprocess.run([ffmpeg_bin(), "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        except Exception:
            _ENCODERS = ""
    return name in _ENCODERS


def encoder_args(quality):
    if is_mac() and os.environ.get("CLIPTOOL_X264") != "1" and has_encoder("h264_videotoolbox"):
        br = {"maximal": "16M", "hoch": "12M", "mittel": "8M"}.get(quality, "10M")
        return ["-c:v", "h264_videotoolbox", "-b:v", br, "-profile:v", "high", "-allow_sw", "1"]
    crf = {"maximal": "16", "hoch": "18", "mittel": "21"}.get(quality, "20")
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-profile:v", "high"]


def words_in(transcript, start, end):
    out = []
    for s in transcript.get("segmente", []):
        if s["e"] < start - 1 or s["s"] > end + 1:
            continue
        for w in s.get("words", []):
            if w["s"] >= start - 0.05 and w["e"] <= end + 0.3:
                out.append({"w": w["w"], "s": w["s"] - start, "e": w["e"] - start})
    return out


def render_clip(src, clip, transcript, style, out_path, logfile=None, thumb_path=None):
    w, h, sfps, _ = probe(src)
    fps = style["fps"]
    start, end = float(clip["start"]), float(clip["ende"])
    dur = end - start
    t0 = time.time()
    # Zuschnitt vorbereiten
    vertical = w / h <= 9 / 16 + 0.01
    crop_w = int(round(h * 9 / 16 / 2) * 2)
    if style["layout"] == "fuellen" and not vertical:
        tt, cc = track_centers(src, start, dur, w, h)
    else:
        tt, cc = np.array([0.0]), np.array([w / 2])
    # Overlays vorbereiten
    hook_img = render_hook(clip.get("hook") or clip.get("titel", ""), style) if style["hook"] and (clip.get("hook") or clip.get("titel")) else None
    intro_img = render_intro_word(clip["intro_wort"]) if style["intro_wort"] and clip.get("intro_wort") else None
    highlight = set(k.lower() for k in clip.get("schluesselwoerter", []))
    words = words_in(transcript, start, end)
    fixes = {k.lower(): v for k, v in (style.get("korrekturen") or {}).items()}
    fixes.update({k.lower(): v for k, v in (clip.get("korrekturen") or {}).items()})
    if fixes:
        for wd in words:
            m = re.match(r"^(.*?)([,.;:!?]*)$", wd["w"])
            core, tail = m.group(1), m.group(2)
            if core.lower() in fixes:
                wd["w"] = fixes[core.lower()] + tail
    chunks = chunk_words(words, style["untertitel_woerter"], style["untertitel_max_zeichen"]) if style["untertitel"] else []
    karaoke = style.get("untertitel_stil") == "karaoke"
    if karaoke:
        cap_imgs = [[render_caption([x["w"] for x in c["words"]], style, highlight, active=j)
                     for j in range(len(c["words"]))] for c in chunks]
    else:
        cap_imgs = [render_caption([x["w"] for x in c["words"]], style, highlight) for c in chunks]
    # Encoder
    cmd = [ffmpeg_bin(), "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-r", str(fps), "-i", "-",
           "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
           "-map", "0:v", "-map", "1:a?", *encoder_args(style["qualitaet"]),
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", out_path]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    blur_bg = None
    hook_y = int(OUT_H * 0.06)
    n = 0
    for i, fr in enumerate(read_frames(src, start, dur, w, h, fps)):
        t = i / fps
        if style["layout"] == "fuellen" and not vertical:
            cx = float(np.interp(t, tt, cc))
            x0 = int(min(max(cx - crop_w / 2, 0), w - crop_w))
            out = cv2.resize(fr[:, x0:x0 + crop_w], (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
        else:
            # Anpassen: Video in voller Breite, Hintergrund unscharf
            s = OUT_W / w
            fg = cv2.resize(fr, (OUT_W, int(h * s)), interpolation=cv2.INTER_AREA)
            bgc = cv2.resize(fr, (int(w * OUT_H / h), OUT_H))
            bx = (bgc.shape[1] - OUT_W) // 2
            out = cv2.GaussianBlur(np.ascontiguousarray(bgc[:, bx:bx + OUT_W]), (0, 0), 25)
            out = (out * 0.6).astype(np.uint8)
            y0 = (OUT_H - fg.shape[0]) // 2
            out[y0:y0 + fg.shape[0]] = fg
        out = np.ascontiguousarray(out)
        if intro_img is not None and t < 0.9:
            a = 1.0 if t < 0.6 else max(0.0, 1 - (t - 0.6) / 0.3)
            composite(out, intro_img, OUT_W / 2, OUT_H * 0.42, a)
        if hook_img is not None and t < style["hook_dauer"] + 0.5:
            a = 1.0 if t < style["hook_dauer"] else max(0.0, 1 - (t - style["hook_dauer"]) / 0.5)
            composite(out, hook_img, OUT_W / 2, hook_y + hook_img.shape[0] / 2, a)
        for c, img in zip(chunks, cap_imgs):
            if karaoke and c["s"] <= t < c["e"]:
                j = 0
                for jj, wd in enumerate(c["words"]):
                    if t >= wd["s"]:
                        j = jj
                img = img[j]
            if c["s"] <= t < c["e"] and img is not None:
                k = t - c["s"]
                sc = 1.0
                if style["pop_animation"] and k < 0.12:
                    sc = 0.82 + 0.18 * (k / 0.12) + 0.04 * math.sin(math.pi * k / 0.12)
                composite(out, img, OUT_W / 2, OUT_H * style["untertitel_hoehe"], 1.0, sc)
                break
        if thumb_path and i == int(fps * 1.2):
            try:
                small = cv2.resize(out, (270, 480), interpolation=cv2.INTER_AREA)
                cv2.imwrite(thumb_path, cv2.cvtColor(small, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 70])
            except Exception:
                pass
        enc.stdin.write(out.tobytes())
        n += 1
    enc.stdin.close()
    err = enc.stderr.read().decode(errors="ignore")
    enc.wait()
    if enc.returncode != 0:
        raise RuntimeError("Encoder-Fehler: " + err[-500:])
    log(f"Clip {clip.get('nr')} fertig: {n} Frames in {time.time() - t0:.1f}s -> {os.path.basename(out_path)}", logfile)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--nur", type=int, nargs="*")
    a = ap.parse_args()
    plan = read_json(resolve(a.plan))
    job = plan.get("job", "test")
    logfile = os.path.join(DIRS["logs"], f"{job}.log")
    style = dict(DEFAULT_STYLE)
    style.update(plan.get("stil", {}))
    if plan.get("korrekturen"):
        style["korrekturen"] = plan["korrekturen"]
    quelle = resolve(plan.get("quelle") or os.path.join("quellen", job, "source.mp4"))
    transcript = read_json(resolve(plan.get("transkript") or os.path.join("quellen", job, "transcript.json")), {"segmente": []})
    outdir = resolve(plan.get("ausgabe")) if plan.get("ausgabe") else os.path.join(DIRS["output"], plan.get("konto", "allgemein"), safe_filename(plan.get("folge", job)))
    os.makedirs(outdir, exist_ok=True)
    clips = plan["clips"]
    if a.nur:
        clips = [c for c in clips if c.get("nr") in a.nur]
    results = []
    for i, c in enumerate(clips):
        set_status(job, schritt="rendern", fortschritt=60 + int(40 * i / max(1, len(clips))),
                   info=f"Clip {i + 1} von {len(clips)}")
        name = safe_filename(c.get("titel") or f"Clip {c.get('nr')}") + ".mp4"
        out = os.path.join(outdir, name)
        vdir = os.path.join(outdir, "_vorschau")
        os.makedirs(vdir, exist_ok=True)
        thumb = os.path.join(vdir, f"{int(c.get('nr', i + 1)):02d}.jpg")
        try:
            render_clip(quelle, c, transcript, style, out, logfile, thumb)
            results.append({**c, "datei": relative(out), "vorschau": relative(thumb), "ok": True})
        except Exception as e:
            import traceback
            log(f"Fehler bei Clip {c.get('nr')}: {e}\n{traceback.format_exc()}", logfile)
            results.append({**c, "ok": False, "fehler": str(e)})
    write_json(os.path.join(outdir, "clips.json"), {"job": job, "konto": plan.get("konto"), "folge": plan.get("folge"), "clips": results})
    set_status(job, schritt="fertig", fortschritt=100, ausgabe=relative(outdir),
               ok=sum(1 for r in results if r["ok"]), fehler=sum(1 for r in results if not r["ok"]))


if __name__ == "__main__":
    main()
