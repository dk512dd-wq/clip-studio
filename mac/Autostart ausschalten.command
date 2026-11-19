#!/bin/bash
# Schaltet den Autostart des Clip-Tools wieder aus.
PLIST="$HOME/Library/LaunchAgents/de.clipstudio.runner.plist"
launchctl unload "$PLIST" 2>/dev/null
mv "$PLIST" "$HOME/Downloads/Clip-Tool/logs/autostart-aus.plist" 2>/dev/null
echo "Autostart ist aus."
