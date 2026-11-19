#!/bin/bash
# Startet das Clip-Tool. Das Fenster offen lassen, solange geclippt wird.
BASE="$HOME/Downloads/Clip-Tool"
VENV="$HOME/ClipTool/venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Das Clip-Tool ist noch nicht installiert. Bitte zuerst 'Clip-Tool installieren.command' doppelklicken."
  exit 1
fi
export PATH="$VENV/bin:$PATH"
export FFMPEG=$("$VENV/bin/python" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
cd "$BASE/engine" || exit 1
echo "Clip-Tool laeuft. Dieses Fenster offen lassen."
# caffeinate haelt den Mac wach, solange das Clip-Tool laeuft
exec caffeinate -is "$VENV/bin/python" runner.py
