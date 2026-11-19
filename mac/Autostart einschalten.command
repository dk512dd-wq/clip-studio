#!/bin/bash
# Startet das Clip-Tool nach jedem Neustart des Macs automatisch im Terminal.
# Rueckgaengig: 'Autostart ausschalten.command' doppelklicken.
BASE="$HOME/Downloads/Clip-Tool"
PLIST="$HOME/Library/LaunchAgents/de.clipstudio.runner.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>de.clipstudio.runner</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-a</string>
    <string>Terminal</string>
    <string>$BASE/Clip-Tool starten.command</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "Autostart ist an. Das Clip-Tool startet ab jetzt nach jedem Neustart von selbst."
