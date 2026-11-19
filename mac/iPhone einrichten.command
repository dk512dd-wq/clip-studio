#!/bin/bash
# Richtet die iPhone-Steuerung ein (Open iPhone Use, github.com/semsturgut/open-iphone-use).
# Einfach doppelklicken. Kann gefahrlos mehrmals gestartet werden.
main() {
BASE="$HOME/Downloads/Clip-Tool"
mkdir -p "$BASE/logs"
LOG="$BASE/logs/iphone-setup.log"
STATUS="$BASE/logs/iphone-status.txt"
exec > >(tee "$LOG") 2>&1
echo "== iPhone-Steuerung einrichten $(date)"
sw_vers 2>/dev/null | head -2; uname -m

echo "== Schritt 1: Xcode"
if ! ls -d /Applications/Xcode*.app >/dev/null 2>&1; then
  echo "Xcode fehlt. Ich oeffne den App Store. Dort auf 'Laden' tippen (rund 10 GB, dauert eine Weile)."
  echo "Danach Xcode einmal oeffnen, Zusatzkomponenten installieren lassen und dieses Skript nochmal starten."
  open "macappstore://apps.apple.com/app/xcode/id497799835"
  echo "SCHRITT=xcode_fehlt" > "$STATUS"
  exit 0
fi
if ! /usr/bin/xcodebuild -version >/dev/null 2>&1; then
  echo "Xcode ist da, aber noch nicht fertig eingerichtet. Ich oeffne Xcode."
  echo "Bitte Lizenz bestaetigen und Zusatzkomponenten installieren lassen. Danach dieses Skript nochmal starten."
  open -a Xcode
  echo "SCHRITT=xcode_einrichten" > "$STATUS"
  exit 0
fi
/usr/bin/xcodebuild -version | head -2

echo "== Schritt 2: Open iPhone Use"
OIU="$HOME/.local/share/open-iphone-use/runtime/venv/bin/open-iphone-use"
if [ ! -x "$OIU" ]; then
  export OIU_PYTHON=/nonexistent/python3
  curl -fsSL https://raw.githubusercontent.com/semsturgut/open-iphone-use/main/install.sh | bash -s -- --no-agents
fi
if [ ! -x "$OIU" ]; then echo "INSTALLATION FEHLGESCHLAGEN"; echo "SCHRITT=oiu_fehler" > "$STATUS"; exit 1; fi

echo "== Schritt 3: Anpassungen fuer neue Macs"
bash "$BASE/iPhone starten.command" --nur-anpassen

echo "== Schritt 4: In Claude Desktop eintragen"
R="$HOME/.local/share/open-iphone-use/runtime/venv"
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
"$R/bin/python" - "$CFG" "$OIU" <<'EOF'
import json, sys, os, shutil, time
cfg, exe = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(cfg):
    shutil.copy2(cfg, cfg + '.backup-' + time.strftime('%Y%m%d-%H%M%S'))
    txt = open(cfg).read().strip()
    data = json.loads(txt) if txt else {}
data.setdefault('mcpServers', {})['open-iphone-use'] = {'command': exe, 'args': ['mcp']}
os.makedirs(os.path.dirname(cfg), exist_ok=True)
with open(cfg, 'w') as f: json.dump(data, f, indent=2)
print('eingetragen in', cfg)
EOF

echo "== Schritt 5: Server starten und iPhone suchen"
bash "$BASE/iPhone starten.command"
echo ""
echo "Wenn oben kein iPhone steht: iPhone per Kabel anschliessen, entsperren, 'Diesem Computer vertrauen' tippen."
echo "Entwicklermodus: iPhone > Einstellungen > Datenschutz & Sicherheit > Entwicklermodus > an (iPhone startet neu)."
echo "Danach 'iPhone starten.command' doppelklicken."
echo "FERTIG"
}
main "$@"
exit 0
