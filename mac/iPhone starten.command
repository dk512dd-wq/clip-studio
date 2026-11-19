#!/bin/bash
# Startet die iPhone-Steuerung neu und zeigt, welche iPhones verbunden sind.
# Vorher: iPhone per Kabel an den Mac und entsperren.
main() {
BASE="$HOME/Downloads/Clip-Tool"
mkdir -p "$BASE/logs"
STATUS="$BASE/logs/iphone-status.txt"
R="$HOME/.local/share/open-iphone-use/runtime/venv"
OIU="$R/bin/open-iphone-use"
if [ ! -x "$OIU" ]; then echo "Open iPhone Use fehlt. Bitte zuerst 'iPhone einrichten.command' starten."; echo "SCHRITT=oiu_fehlt" > "$STATUS"; exit 1; fi
S=$(ls -d "$R"/lib/python3*/site-packages/oiu | head -1)
[ -f "$S/core.py.orig" ] || cp "$S/core.py" "$S/core.py.orig"
[ -f "$S/coredevice.py.orig" ] || cp "$S/coredevice.py" "$S/coredevice.py.orig"
# Zwei kleine Anpassungen: Bildstrom fuer neue pymobiledevice3-Versionen und eine Zieh-Geste fuer Drehraeder
"$R/bin/python" - "$S" <<'EOF'
import os, re, sys
s = sys.argv[1]
core, cd = os.path.join(s, 'core.py'), os.path.join(s, 'coredevice.py')
c, d = open(core).read(), open(cd).read()
done = []
if '"drag"' not in c and '"advance_feed"}' in c:
    c = c.replace('"advance_feed"}', '"advance_feed", "drag"}', 1); done.append('drag-aktion')
if "operation == 'drag'" not in d and "        if operation in ('swipe', 'advance_feed'):\n" in d:
    d = d.replace("        if operation in ('swipe', 'advance_feed'):\n",
                  "        if operation == 'drag':\n"
                  "            await connection.drag(units(float(args['x1'])), units(float(args['y1'])), units(float(args['x2'])), units(float(args['y2'])), float(args.get('duration', .8)))\n"
                  "            return 'Dragged'\n"
                  "        if operation in ('swipe', 'advance_feed'):\n", 1); done.append('drag-geste')
d2 = re.sub(r"def _broadcast_frame\(self, bgra\):\n(\s+)super\(\)\._broadcast_frame\(bgra\)",
            r"def _broadcast_frame(self, *args, **kwargs):\n\1super()._broadcast_frame(*args, **kwargs)", d)
if d2 != d: d = d2; done.append('bildstrom')
open(core, 'w').write(c); open(cd, 'w').write(d)
print('Anpassungen:', ', '.join(done) if done else 'schon aktuell')
print('Pruefung:', '"drag"' in c, "operation == 'drag'" in d, '_broadcast_frame(self, bgra)' not in d)
EOF
if [ "$1" = "--nur-anpassen" ]; then exit 0; fi
"$OIU" stop >/dev/null 2>&1; sleep 2
"$OIU" serve; sleep 10
{
  echo "SCHRITT=server_laeuft"
  echo "ZEIT=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "== Geraete"; "$OIU" devices 2>&1
  echo "== Kandidaten"; "$OIU" candidates 2>&1
} > "$STATUS"
cat "$STATUS"
echo ""
echo "Steuerung im Browser: http://127.0.0.1:27893"
echo "FERTIG"
}
main "$@"
exit 0
