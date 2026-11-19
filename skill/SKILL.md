---
name: clip-studio
description: Clip-Studio bedienen. YouTube-Folgen auf dem eigenen Mac zu TikTok-Clips schneiden, jeden Clip mit Virality-Score bewerten und auf Wunsch per iPhone in TikTok Studio einplanen. Nutzen bei „Clips machen“, „Clip-Studio“, „Automatik einrichten“, „iPhone einrichten“, „Clips einplanen“.
---

# Clip-Studio

Ein Clipper wie Opus Clip, der auf dem Mac des Nutzers läuft und von dir gesteuert wird.

- **Clip-Studio**: Artefakt des Nutzers mit dem Titel „Clip-Studio“. Darin Konten, Einstellungen, Aufträge und fertige Clips (Artefakt-Datenbank).
- **Clip-Tool**: Ordner `~/Downloads/Clip-Tool` auf dem Mac. Ein Terminal-Fenster „Clip-Tool starten“ arbeitet Job-Dateien ab: herunterladen, transkribieren, schneiden.
- **Du**: liest die Transkripte, suchst die besten Momente, bewertest jeden Clip und pflegst das Studio.
- Optional **iPhone** per Kabel über Open iPhone Use, um Clips in TikTok Studio einzuplanen.

Details bei Bedarf mit WebFetch lesen:
- Clippen, Bewertung, Formate: https://raw.githubusercontent.com/dk512dd-wq/clip-studio/main/docs/clippen.md
- iPhone und TikTok Studio: https://raw.githubusercontent.com/dk512dd-wq/clip-studio/main/docs/iphone.md
- Installation: https://raw.githubusercontent.com/dk512dd-wq/clip-studio/main/ANLEITUNG-FUER-CLAUDE.md

## Regeln

- Sprich Deutsch und duze. Kurze Zwischenstände, nur melden, wenn etwas ansteht.
- Nichts veröffentlichen oder verschicken ohne Auftrag des Nutzers. Einplanen in TikTok Studio ist Veröffentlichen.
- Am Mac nur im Ordner `Clip-Tool` arbeiten. Programme nur über die mitgelieferten `.command`-Dateien starten.
- Werkzeuge: `device_bash` (Pfad `$HOME/mnt/Downloads/Clip-Tool`), `device_stage_files` und `device_commit_files` (Pfad `~/Downloads/Clip-Tool`), Computer-Use für den Finder, Artefakt-Werkzeuge (`list_artifacts`, `db_*`, `publish_files`). Fehlen die Geräte-Werkzeuge, bitte den Nutzer, diesen Chat in der Claude-Desktop-App auf dem Mac zu öffnen.

## „Clips machen“

1. **Studio finden:** `list_artifacts` mit `query` „Clip-Studio“, eigenes Artefakt nehmen, Slug merken.
2. **Lesen:** `system/konten`, `einstellungen/<konto>`, `db_query` auf `auftraege` mit `status == neu`. Gibt es keine, kurz sagen und fertig.
3. **Mac prüfen:** `status/_runner.json` lesen. Feld `unix` älter als 60 Sekunden heißt, der Runner läuft nicht. Dann „Clip-Tool starten.command“ im Finder öffnen (Downloads › Clip-Tool, Datei markieren, Ablage › Öffnen) oder den Nutzer um einen Doppelklick bitten.
4. **Pro Auftrag vorbereiten:** Job-ID `JJJJ-MM-TT-<kurzname>`. Datei `jobs/warteschlange/<job>.json` mit `{"typ":"vorbereiten","job":...,"url":...,"konto":...,"sprache":"de"}` schreiben. Auftrag in der Datenbank auf `laeuft` setzen (`schritt`, `fortschritt`). `status/<job>.json` abfragen, bis `schritt` = `bereit_fuer_auswahl`. Bei `fehler` das Log `logs/<job>.log` lesen.
5. **Auswählen und bewerten:** `quellen/<job>/transcript.txt` ganz lesen. Momente nach den Einstellungen wählen, Grenzen über die Wort-Zeiten in `transcript.json` setzen, jeden Clip einzeln bewerten: Score 0 bis 100 und Noten für Hook, Flow, Value, Trend, dazu zwei bis drei Sätze Begründung. Nichts unter `mindest_score`. Keine Überschneidungen. Regeln im Detail: docs/clippen.md.
6. **Plan schreiben:** `plaene/<job>.json` mit `job`, `konto`, `folge`, `stil` (Block aus den Einstellungen unverändert), `korrekturen` für verhörte Wörter, `clips`. Dann Job `{"typ":"rendern","job":...,"plan":"plaene/<job>.json"}`.
7. **Warten:** bis `status/<job>.json` `fertig` meldet. Ergebnis in `clips/<konto>/<folge>/clips.json`.
8. **Ins Studio:** Vorschaubilder `_vorschau/NN.jpg` per `device_stage_files` holen und mit `publish_files` (mode `patch`) als `vorschau/<job>-NN.jpg` ins Artefakt laden. Dann per `db_write` pro Clip `clips/<job>-NN` anlegen (`status` `neu`), Auftrag auf `fertig`, `system/status` auf `{zuletzt, text: "bereit"}`.
9. **Melden:** Anzahl Clips, Score-Spanne, Ordner. Ein Satz zum stärksten Clip.

## „Clips einplanen“ (iPhone)

Nur wenn `automatik.iphone` an ist oder der Nutzer es jetzt verlangt. Ablauf in docs/iphone.md Teil C und D: Clips aufs iPhone bringen, pro Clip in TikTok Studio mit Beschreibung und Uhrzeit planen, im Studio auf `eingeplant` setzen mit `geplant_fuer`.

## „iPhone einrichten“

docs/iphone.md Teil A. Kurz: „iPhone einrichten.command“ öffnen, Xcode über den App Store, Entwicklermodus am iPhone, danach „iPhone starten.command“.

## „Automatik einrichten“

1. Einstellungen aller Konten lesen (`automatik.nachtlauf`, `uhrzeit`, `iphone`).
2. Für den Nachtlauf eine geplante Aufgabe anlegen, die auf dem Mac läuft (requires_local_device), täglich zur Startzeit in der Zeitzone des Nutzers. Text der Aufgabe: „Nutze den Skill clip-studio. Arbeite alle neuen Aufträge im Clip-Studio ab (Clips machen). Melde kurz das Ergebnis.“ Wenn der Nutzer das Einplanen ausdrücklich für die Nacht freigibt, ergänze: „Plane danach die neuen Clips in TikTok Studio ein, wie in docs/iphone.md beschrieben.“
3. Optional „Autostart einschalten.command“ öffnen, damit das Clip-Tool nach einem Neustart von selbst läuft.
4. Dem Nutzer sagen, was nachts passiert und was dafür an sein muss: Mac an, Claude-App offen, beim Einplanen das iPhone am Kabel und entsperrt.
