#!/bin/bash
# Beendet ein laufendes Clip-Tool und startet es frisch (zum Beispiel nach einem Update).
BASE="$HOME/Downloads/Clip-Tool"
PID=$("$HOME/ClipTool/venv/bin/python" -c "import json;print(json.load(open('$BASE/status/_runner.json')).get('pid',''))" 2>/dev/null)
if [ -n "$PID" ] && ps -p "$PID" -o command= 2>/dev/null | grep -q "runner.py"; then
  kill "$PID" 2>/dev/null && echo "Altes Clip-Tool beendet (PID $PID)."
  sleep 2
fi
open -a Terminal "$BASE/Clip-Tool starten.command"
echo "Clip-Tool laeuft im neuen Fenster. Dieses Fenster kann zu."
