# Anleitung für Claude: Clip-Studio einrichten

Der Nutzer hat dir den Link zu diesem Projekt geschickt und möchte das Clip-Studio bei sich haben. Du richtest alles ein. Der Nutzer soll so wenig wie möglich selbst tun und nichts verstehen müssen.

**Ziel am Ende:**
1. Auf seinem Mac liegt `~/Downloads/Clip-Tool` und läuft.
2. Er hat ein eigenes Artefakt „Clip-Studio“ in seinem Claude.
3. Der Skill „clip-studio“ ist bei ihm gespeichert, damit jeder neue Chat weiß, was „Clips machen“ heißt.
4. Optional: iPhone-Steuerung für TikTok Studio und ein Nachtlauf.

Alles läuft auf seinem Mac und in seinem eigenen Claude. Es entstehen keine Kosten außer seinem normalen Claude-Abo.

## So arbeitest du

- Deutsch, du-Form. Vor jedem Schritt ein Satz, was jetzt passiert. Keine Fachbegriffe ohne Erklärung.
- Frag nur, was du nicht selbst herausfinden kannst. Gib bei Entscheidungen eine klare Empfehlung.
- Lege eine Aufgabenliste an, damit der Nutzer den Fortschritt sieht.
- Lies dieses Dokument einmal ganz, bevor du anfängst. Quelle für alle Dateien: https://github.com/dk512dd-wq/clip-studio

## Schritt 0: Voraussetzungen prüfen

- **Mac mit macOS 14 oder neuer.** Apple-Chip (M1 oder neuer) empfohlen. Intel geht, ist aber langsamer. Windows geht nicht.
- **Claude-Desktop-App auf dem Mac, dieser Chat mit dem Mac verbunden.** Prüfe, ob Geräte-Werkzeuge da sind (`get_device_info`, `device_bash`, `device_commit_files`). Wenn nicht: Sag dem Nutzer, er soll diesen Chat in der Claude-Desktop-App auf dem Mac öffnen und dort eine Nachricht schicken.
- **Ordner Downloads verbunden.** Sonst mit `device_request_folder_access` für `~/Downloads` anfragen.
- **Rund 5 GB frei** (Programme 2 GB, Platz für Folgen und Clips). Mit `df -h` im Geräte-Shell grob prüfen.

## Schritt 1: Kurz fragen, wie er es nutzen will

Eine Frage-Runde (AskUserQuestion), zwei Fragen:
1. „Was soll das Clip-Studio für dich machen?“ Optionen: „Clips schneiden“ (Empfehlung für den Start), „Clips schneiden und auf dem iPhone in TikTok Studio einplanen“.
2. „Soll ich neue Folgen nachts automatisch clippen?“ Optionen: „Ja, nachts“ (Empfehlung), „Nein, nur wenn ich es sage“.

Kontoname, Look und Posting-Zeiten fragt das Clip-Studio selbst in seiner Einrichtung ab.

## Schritt 2: Clip-Tool auf den Mac

1. Projekt in deine Arbeitsumgebung holen: `git clone --depth 1 https://github.com/dk512dd-wq/clip-studio` (klappt das nicht, die Dateien einzeln über `https://raw.githubusercontent.com/dk512dd-wq/clip-studio/main/<pfad>` laden).
2. Die Datei `mac/Clip-Tool installieren.command` mit `device_commit_files` nach `~/Downloads/Clip-Tool/Clip-Tool installieren.command` legen. Danach im Geräte-Shell ausführbar machen: `chmod +x "$HOME/mnt/Downloads/Clip-Tool/"*.command`.
3. Starten. Weg A (bevorzugt, wenn Computer-Use da ist): Zugriff auf den Finder anfragen, dann Finder › Gehe zu › Downloads, Ordner Clip-Tool aufklappen, Datei markieren, Ablage › Öffnen. Weg B: Den Nutzer bitten, in Downloads › Clip-Tool die Datei doppelzuklicken. Falls macOS die Datei blockiert: Rechtsklick › Öffnen › Öffnen.
4. Das Skript lädt alles von GitHub, richtet Python, Whisper und ffmpeg ein und lädt das Sprachmodell (rund 1,6 GB). Dauer 5 bis 20 Minuten. Fortschritt in `logs/install.log`. Fertig, wenn dort `INSTALLATION FERTIG` steht. Bei Fehlern das Log lesen und gezielt helfen.
5. Danach `Clip-Tool starten.command` genauso öffnen. Das Terminal-Fenster bleibt offen. Prüfen: `status/_runner.json` existiert und `zustand` ist `wartet`.

## Schritt 3: Clip-Studio anlegen (Artefakt)

1. `list_types` aufrufen (Pflicht vor einem neuen Artefakt). Das Clip-Studio ist eine eigene Seite, kein Typ.
2. Mit `publish_files` aus dem Ordner `studio/` hochladen, Titel „Clip-Studio“, Icon „video“:
   `index.html`, `logo.svg`, `logo-klein.svg`, `topo.jpg`, `fonts/D-DIN.woff2`, `fonts/D-DIN-Bold.woff2`, `fonts/D-DINCondensed-Bold.woff2`, `fonts/D-DIN-OFL.txt`.
   Ohne `publish_files`: Sag dem Nutzer, dass das Studio nur in einer Claude-Umgebung mit Artefakt-Werkzeugen angelegt werden kann.
3. `declare_capabilities` mit `{"db": {}, "user": {}}`.
4. `db_write`: `system/status` = `{"zuletzt": <jetzt als ISO-Zeit>, "text": "bereit"}`.
5. Dem Nutzer sagen: „Öffne das Clip-Studio. Es führt dich in vier kurzen Schritten durch die Einrichtung.“ Warte, bis er fertig ist (prüfe `system/konten`). Übernimm danach seine Antworten aus Schritt 1 in `einstellungen/<konto>.automatik` (`nachtlauf`, `iphone`), falls er sie dort anders gesetzt hat, frag kurz nach.

## Schritt 4: Skill speichern

Lies `skill/SKILL.md` aus dem Projekt und schlag ihn mit `propose_skills` vor (`kind` „new“, `name` „clip-studio“, `skillMd` = kompletter Dateiinhalt, `description` aus der Kopfzeile). Der Nutzer tippt auf Speichern. Gibt es `propose_skills` nicht, erkläre in zwei Sätzen, wie er den Skill unter Einstellungen › Fähigkeiten aus der Datei `skill/SKILL.md` hochlädt.

## Schritt 5: iPhone (nur wenn gewünscht)

Folge `docs/iphone.md` Teil A. Kurz:
1. `mac/iPhone einrichten.command` und `mac/iPhone starten.command` liegen nach Schritt 2 schon in `~/Downloads/Clip-Tool`. Sonst wie in Schritt 2 hinlegen.
2. Nutzer: iPhone per Kabel anschließen, entsperren, „Vertrauen“ tippen, Entwicklermodus einschalten.
3. „iPhone einrichten.command“ öffnen. Fehlt Xcode, öffnet das Skript den App Store. Der Nutzer tippt auf „Laden“. Danach Xcode einmal öffnen und das Skript erneut starten.
4. Prüfen: `logs/iphone-status.txt` zeigt `SCHRITT=server_laeuft` und das iPhone unter „Geraete“.
5. Einmal testen: im eingebauten Browser `http://127.0.0.1:27893` öffnen und ein Bild vom iPhone holen.
6. Den Nutzer fragen, wie die Clips aufs iPhone kommen sollen: „AirDrop, wenn ich dabei bin“ oder „iCloud-Fotos, auch nachts“ (Empfehlung bei Nachtlauf).

## Schritt 6: Automatik (nur wenn gewünscht)

Im Skill unter „Automatik einrichten“ beschrieben: geplante Aufgabe für den Nachtlauf, optional „Autostart einschalten.command“. Sag dem Nutzer, welche Einstellung die Aufgabe beim Freigeben bekommen hat.

## Schritt 7: Testlauf

Bitte den Nutzer, im Clip-Studio unter „Neue Folge“ einen kurzen YouTube-Link (5 bis 15 Minuten) einzufügen. Dann den Ablauf „Clips machen“ aus dem Skill durchführen. Schick ihm einen fertigen Clip zum Anschauen.

## Abschluss

Drei kurze Sätze: was jetzt läuft, wie er es nutzt („Link ins Clip-Studio, dann ‚Clips machen‘“), was an sein muss. Keine langen Listen.
