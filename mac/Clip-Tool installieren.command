#!/bin/bash
# Clip-Studio: Installation und Update fuer den Mac. Einfach doppelklicken.
# Laedt die neueste Version von GitHub, richtet Python, Whisper und ffmpeg ein.
# Deine Clips, Auftraege und Einstellungen bleiben bei einem Update erhalten.
main() {
REPO="dk512dd-wq/clip-studio"
BRANCH="main"
BASE="$HOME/Downloads/Clip-Tool"
APP="$HOME/ClipTool"
mkdir -p "$BASE/logs"
exec > >(tee "$BASE/logs/install.log") 2>&1
echo "== Clip-Studio Installation $(date)"
sw_vers 2>/dev/null | head -2; ARCH=$(uname -m); echo "Prozessor: $ARCH"

echo "== Programmdateien laden"
TMP=$(mktemp -d)
if curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" -o "$TMP/cs.tgz" && tar xzf "$TMP/cs.tgz" -C "$TMP"; then
  SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
  mkdir -p "$BASE/engine"
  cp -R "$SRC/engine/." "$BASE/engine/"
  for f in "$SRC/mac/"*.command; do cp "$f" "$BASE/"; done
  chmod +x "$BASE/"*.command
  echo "Programmdateien aktuell"
elif [ -f "$BASE/engine/runner.py" ]; then
  echo "GitHub nicht erreichbar. Ich nutze die vorhandenen Dateien."
else
  echo "FEHLER: Programmdateien konnten nicht geladen werden. Internet pruefen und nochmal starten."
  exit 1
fi
mkdir -p "$BASE"/{jobs/warteschlange,jobs/laeuft,jobs/fertig,jobs/fehler,status,quellen,clips,plaene}

echo "== uv (Python-Verwaltung)"
UV=""
for c in "$HOME/.local/share/open-iphone-use/runtime/uv/uv" "$APP/uv/uv" "$(command -v uv 2>/dev/null)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then UV="$c"; break; fi
done
if [ -z "$UV" ]; then
  mkdir -p "$APP/uv"
  curl -fLsS https://astral.sh/uv/install.sh -o "$TMP/uv-install.sh"
  UV_INSTALL_DIR="$APP/uv" UV_NO_MODIFY_PATH=1 sh "$TMP/uv-install.sh"
  UV="$APP/uv/uv"
fi
echo "uv: $UV"
export UV_PYTHON_INSTALL_DIR="$APP/python"

echo "== Python 3.12 und Umgebung"
"$UV" python install 3.12
"$UV" venv --python 3.12 "$APP/venv" --allow-existing
PY="$APP/venv/bin/python"

echo "== Pakete"
if [ "$ARCH" = "arm64" ]; then WHISPER="mlx-whisper"; else WHISPER="faster-whisper"; fi
"$UV" pip install --python "$PY" --upgrade "yt-dlp[default]" deno "$WHISPER" opencv-python-headless pillow numpy imageio-ffmpeg huggingface_hub

echo "== ffmpeg"
FF=$("$PY" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
echo "ffmpeg: $FF"
"$FF" -hide_banner -encoders 2>/dev/null | grep -E "h264_videotoolbox|libx264" || true

echo "== Sprachmodell vorladen (einmalig, ca. 1,6 GB)"
if [ "$ARCH" = "arm64" ]; then
  "$PY" -c "from huggingface_hub import snapshot_download; print('Modell:', snapshot_download('mlx-community/whisper-large-v3-turbo'))"
else
  echo "Intel-Mac: Das Modell laedt beim ersten Auftrag."
fi

echo "== Selbsttest"
cd "$BASE/engine" && "$PY" -c "import cv2, PIL, numpy, yt_dlp; print('OK', cv2.__version__, yt_dlp.version.__version__)"
"$APP/venv/bin/deno" --version 2>/dev/null | head -1 || echo "deno fehlt"
echo "INSTALLATION FERTIG $(date)"
echo ""
echo "Naechster Schritt: In Downloads > Clip-Tool die Datei 'Clip-Tool starten.command' doppelklicken."
}
main "$@"
exit 0
