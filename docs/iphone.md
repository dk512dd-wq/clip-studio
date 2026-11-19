# iPhone: einrichten und Clips in TikTok Studio einplanen

Dieses Dokument ist für Claude. Es beschreibt, wie das iPhone per Kabel vom Mac aus gesteuert wird und wie fertige Clips in TikTok Studio eingeplant werden. Grundlage ist Open iPhone Use (github.com/semsturgut/open-iphone-use). Für Details zur Programmierschnittstelle dort die README lesen.

## Teil A: Einmalige Einrichtung

Erkläre dem Nutzer jeden Schritt in einem Satz. Er muss nur tippen, was nur er tippen kann.

1. **Was der Nutzer selbst macht:**
   - iPhone per Kabel an den Mac, entsperren, „Diesem Computer vertrauen“ tippen.
   - Entwicklermodus: iPhone › Einstellungen › Datenschutz & Sicherheit › Entwicklermodus › an. Das iPhone startet neu, danach „Aktivieren“ bestätigen und Code eingeben.
   - Für die Sitzungen: Automatische Sperre auf „Nie“ (Einstellungen › Anzeige & Helligkeit), Fokus „Nicht stören“ an, Lautstärke leise. Den Code kann nur der Nutzer eingeben.
2. **Skript starten:** `~/Downloads/Clip-Tool/iPhone einrichten.command` öffnen (Finder: Ordner Downloads › Clip-Tool, Datei markieren, Ablage › Öffnen). Ablauf und Ergebnis stehen in `logs/iphone-setup.log` und `logs/iphone-status.txt`.
   - `SCHRITT=xcode_fehlt`: Das Skript hat den App Store mit Xcode geöffnet. Der Nutzer tippt auf „Laden“ (rund 10 GB). Danach Xcode einmal öffnen, Zusatzkomponenten installieren lassen, Skript erneut starten.
   - `SCHRITT=xcode_einrichten`: Xcode ist da, aber nicht fertig eingerichtet. Xcode öffnen, Lizenz bestätigen, Skript erneut starten.
   - `SCHRITT=server_laeuft`: fertig. Unter „Geraete“ steht das iPhone mit seiner ID.
3. Das Skript macht zwei kleine Anpassungen an Open iPhone Use, die auf aktuellen Macs nötig sind:
   - Bildstrom: `_broadcast_frame` nimmt beliebige Argumente an. Ohne das bleibt das Bild schwarz.
   - Neue Aktion `drag` (x1, y1, x2, y2, duration). Damit lassen sich Drehräder präzise bewegen.
   Nach einem Update von Open iPhone Use einfach „iPhone starten.command“ öffnen, das prüft und erneuert beides.

Hinweis: Die Apple-Funktion iPhone-Synchronisierung ist in der EU gesperrt. Deshalb läuft die Steuerung über Open iPhone Use.

## Teil B: Steuern

Vor jeder Sitzung: iPhone per Kabel anschließen, entsperren, `iPhone starten.command` öffnen. Ergebnis in `logs/iphone-status.txt`.

Zwei Wege, je nachdem was in der Sitzung verfügbar ist:

1. **Werkzeuge von Open iPhone Use** (über die Claude-Desktop-App, falls in der Werkzeugliste vorhanden). Dann diese nutzen.
2. **Eingebauter Browser der Claude-App** auf `http://127.0.0.1:27893`. Die Seite zeigt das iPhone-Bild. Gesteuert wird per JavaScript im Seitenkontext über die HTTP-Schnittstelle:
   - `GET /api/devices` listet die Geräte.
   - `GET /api/devices/<id>/snapshot` liefert den aktuellen Stand samt Frame-ID, `GET /api/devices/<id>/frame` das Bild.
   - `POST /api/devices/<id>/action` mit `{"operation": ..., "arguments": {"expectedFrameID": ..., ...}}`.
   - Operationen: `ensure_session`, `pointer_tap` (x, y als Anteile 0 bis 1), `type_text`, `send_key` (zum Beispiel `home`, `volume_down`), `scroll`, `swipe`, `drag` (x1, y1, x2, y2 als Anteile, duration in Sekunden).
   - JavaScript-Aufrufe über 45 Sekunden brechen ab. Längere Abläufe als Promise im Hintergrund starten, Ergebnis in eine Variable schreiben und abfragen.
   - Nach jeder Aktion das neue Bild ansehen und prüfen, bevor die nächste kommt.

Was du nie tust: den Gerätecode eingeben, Einstellungen außerhalb der Aufgabe ändern, Nachrichten schreiben, andere Apps bedienen. Nur TikTok Studio und das, was der Nutzer verlangt hat.

## Teil C: Clips aufs iPhone bringen

**Weg 1: AirDrop** (wenn der Nutzer dabei ist)
Finder › Ordner mit den Clips › Dateien markieren › Ablage › Teilen › AirDrop › iPhone wählen. Das Teilen-Fenster braucht die Bildschirmsteuerung. Auf dem iPhone landen die Videos in der Fotos-App.

**Weg 2: Fotos-Mediathek mit iCloud** (für Nachtläufe)
Voraussetzung: iCloud-Fotos ist auf Mac und iPhone mit derselben Apple-ID an. Dann einen Job `fotos` anlegen:
```json
{"typ": "fotos", "job": "2026-11-20-folge-12-fotos", "album": "Clip-Studio Mein Konto", "dateien": ["clips/mein-konto/Folge 12/Titel.mp4"]}
```
Beim ersten Mal fragt macOS, ob das Terminal die Fotos-App steuern darf. Das bestätigt der Nutzer einmal. Danach im iPhone-Bild prüfen, ob die Videos angekommen sind, bevor eingeplant wird.

## Teil D: In TikTok Studio einplanen

Einplanen veröffentlicht später öffentlich. Plane nur, wenn der Nutzer das in diesem Chat verlangt hat oder es ausdrücklich für den Nachtlauf freigegeben hat und deine eigenen Regeln das zulassen. Im Zweifel alles vorbereiten und kurz fragen.

**Uhrzeiten** aus `einstellungen/<konto>.posten`: `pro_tag` Posts gleichmäßig zwischen `von` und `bis` Uhr. Beispiel 4 pro Tag von 10 bis 20 Uhr: 10:00, 13:20, 16:40, 20:00. Erster freier Slot nach dem letzten bereits geplanten Clip dieses Kontos (Feld `geplant_fuer` in der Datenbank). Die besten Scores zuerst.

**Beschreibung**: `posten.vorlage` mit `{titel}` und `{hashtags}` ersetzt.

**Ablauf pro Clip** (die App ändert sich gelegentlich, deshalb jedes Bild ansehen):
1. TikTok Studio öffnen. Oben prüfen, ob das richtige Konto aktiv ist. Konto wechseln über den Kontonamen oben.
2. Hochladen (Plus) › Video aus der Galerie wählen. Im Raster stehen die neuesten Videos meist am Ende. Position vom Ende her zählen und am Vorschaubild prüfen, dass es der richtige Clip ist.
3. Weiter bis zur Beschreibung. Beschreibung tippen. Bei deutscher Tastatur kam das Zeichen `#` über `type_text` nur richtig an, wenn der Backslash `\` gesendet wurde. Immer im Bild prüfen, was angekommen ist.
4. „Planen“ einschalten und Datum und Uhrzeit setzen. Die Drehräder mit `drag` bewegen:
   - Eine Zeile entspricht etwa 0,0456 der Bildhöhe.
   - Höchstens 7 Zeilen pro Zug, Dauer 1,4 Sekunden. Schnellere Züge verstellen das Rad.
   - Züge nicht am Bildrand starten. Für Züge nach oben bei etwa y 0,76 beginnen, nach unten bei etwa y 0,61.
   - Nach jedem Zug den angezeigten Wert im Bild lesen und nachkorrigieren.
5. Vor dem Bestätigen Datum, Uhrzeit, Konto und Beschreibung im Bild prüfen. Dann planen.
6. Im Clip-Studio den Clip auf `eingeplant` setzen, `geplant_fuer` als ISO-Zeit.

Richtwert: rund 1 bis 2 Minuten pro Clip. 50 Clips also gut eine Stunde.

## Teil E: Probleme

| Problem | Lösung |
|---|---|
| Bild schwarz, Server-Log mit `TypeError` bei `_broadcast_frame` | „iPhone starten.command“ öffnen |
| Kein Gerät gelistet | Kabel prüfen, iPhone entsperren, „Vertrauen“ bestätigen, Entwicklermodus an |
| Kabel kurz gezogen | „iPhone starten.command“ öffnen, dann weiter, wo du warst. Entwürfe in TikTok Studio bleiben meist erhalten |
| iPhone gesperrt | Nutzer bitten zu entsperren. Code nie selbst eingeben |
| Drehrad springt falsch | Langsamer ziehen (1,4 s), kleinere Züge, nach jedem Zug prüfen |
