# Clippen: Ablauf, Bewertung, Formate

Dieses Dokument beschreibt für Claude, wie aus einem YouTube-Link fertige Clips werden. Kurzfassung steht im Skill. Hier stehen die Details.

## Bausteine

| Teil | Wo | Aufgabe |
|---|---|---|
| Clip-Studio | Artefakt in Claude, Titel „Clip-Studio“ | Einstellungen pro Konto, Aufträge, fertige Clips. Daten in der Artefakt-Datenbank |
| Clip-Tool | `~/Downloads/Clip-Tool` auf dem Mac | Engine (Python), Runner, Quellen, fertige Clips, Logs |
| Runner | Terminal-Fenster „Clip-Tool starten“ | Arbeitet Job-Dateien aus `jobs/warteschlange` ab |
| Claude | Chat | Liest Transkripte, wählt Momente, bewertet, schreibt Pläne, pflegt das Studio |

Pfade im Shell-Werkzeug des Geräts (device_bash): `$HOME/mnt/Downloads/Clip-Tool`.
Pfade für Datei-Werkzeuge (device_stage_files, device_commit_files): `~/Downloads/Clip-Tool`.
In Job- und Plan-Dateien immer **relative Pfade** ab `Clip-Tool` verwenden, zum Beispiel `quellen/<job>/source.mp4`.

## Datenbank des Clip-Studios

Lesen mit db_get, db_list, db_query. Schreiben mit db_write (bei vorhandenen Dokumenten immer `ifVersion` aus dem letzten Lesen).

| Pfad | Inhalt |
|---|---|
| `system/konten` | `{liste: [{id, name}]}` |
| `system/status` | `{zuletzt: ISO-Zeit, text: "bereit"}` Zeigt oben im Studio den Mac-Status |
| `einstellungen/<konto-id>` | `{konto, name, auswahl{...}, stil{...}, posten{...}, automatik{...}, aktualisiert}` |
| `auftraege/<id>` | `{konto, url, folge, anzahl, hinweis, status: neu, laeuft, fertig, fehler, schritt, fortschritt 0 bis 100, clips_anzahl, fehler, erstellt}` |
| `clips/<job>-<nr>` | `{auftrag, konto, folge, nr, titel, hook, score, noten{hook, flow, value, trend}, grund, start, ende, dauer, datei, vorschau, status: neu, eingeplant, gepostet, verworfen, geplant_fuer, erstellt}` |

`einstellungen.stil` hat genau die Schlüssel, die `render.py` versteht. Den Block unverändert in den Plan übernehmen.

`auswahl` enthält: `clips_pro_folge`, `laenge_min`, `laenge_max` (Sekunden), `mindest_score`, `genre`, `momente` (Liste), `bevorzugt`, `ausschliessen`, `hinweis`.
`posten` enthält: `hashtags`, `vorlage` (`{titel} {hashtags}`), `pro_tag`, `von`, `bis` (Stunden).
`automatik` enthält: `nachtlauf`, `uhrzeit`, `iphone`.

## Job-Dateien

Job-Dateien als JSON nach `jobs/warteschlange/<name>.json` schreiben. Der Runner nimmt nur diese drei Typen:

```json
{"typ": "vorbereiten", "job": "2026-11-20-folge-12", "url": "https://www.youtube.com/watch?v=...", "konto": "mein-konto", "sprache": "de"}
{"typ": "rendern", "job": "2026-11-20-folge-12", "plan": "plaene/2026-11-20-folge-12.json"}
{"typ": "fotos", "job": "2026-11-20-folge-12-fotos", "album": "Clip-Studio Mein Konto", "dateien": ["clips/mein-konto/Folge 12/Titel.mp4"]}
```

Job-ID: `JJJJ-MM-TT-<kurzname>`, nur Kleinbuchstaben, Ziffern und Bindestriche.
`url` darf auch `ytsearch1:<Suchbegriff>` sein, dann nimmt yt-dlp den ersten Treffer.

Fortschritt steht in `status/<job>.json`, Feld `schritt`:
`download` → `ton` → `transkript` → `bereit_fuer_auswahl` → `rendern` → `fertig`. Bei Problemen `fehler`, Details in `logs/<job>.log`.
Lebenszeichen des Runners: `status/_runner.json`, Feld `unix`. Älter als 60 Sekunden heißt: Runner läuft nicht.

Ergebnis der Vorbereitung in `quellen/<job>/`:
`source.mp4`, `info.json` (Titel, Kanal, Dauer, URL), `transcript.txt` (lesbar, Zeilen `[h:mm:ss-h:mm:ss] Text`), `transcript.json` (Segmente mit Wort-Zeitstempeln), `energy.json` (Lautstärke pro Sekunde in dB).

Dauer als Richtwert auf Apple Silicon: Download wenige Sekunden bis Minuten, Transkript rund 6 Sekunden pro Minute Video, Rendern rund 7 Sekunden pro Clip.

## Momente finden

1. `transcript.txt` komplett lesen. Bei langen Folgen in Abschnitten lesen, aber alles lesen.
2. Kandidaten sammeln, die für sich allein funktionieren. Gesucht wird, was in den Einstellungen unter `momente` steht:
   - **Hook-Momente:** Ein Satz, der in den ersten 3 Sekunden neugierig macht.
   - **Emotionen:** Lachen, Wut, Angst, Stolz, Erleichterung.
   - **Starke Meinungen:** klare, steile Aussagen.
   - **Enthüllungen:** „Das wusste ich nicht“-Momente, Fakten mit Überraschung.
   - **Konflikte:** Streit, Ansage, Reibung zwischen Personen.
   - **Zitierfähige Sätze:** kurze Sätze, die man teilen will.
   - **Story-Höhepunkte:** Wendung oder Auflösung einer kleinen Geschichte.
   - **Humor:** Pointe, trockener Kommentar, Situationskomik.
3. `energy.json` hilft: laute Stellen (Lachen, Rufen) sind oft gute Momente.
4. `bevorzugt` nach oben gewichten, alles aus `ausschliessen` weglassen (auch Intro, Abspann, Werbung, Kanal-Aufrufe zum Abonnieren). `hinweis` aus den Einstellungen und aus dem Auftrag beachten.

## Grenzen setzen

- Länge zwischen `laenge_min` und `laenge_max`.
- Start an einem Satzanfang, Ende nach einem abgeschlossenen Gedanken. Kein Clip endet mitten im Satz.
- Die genauen Zeiten aus den Wort-Zeitstempeln in `transcript.json` nehmen: Start etwa 0,2 Sekunden vor dem ersten Wort, Ende etwa 0,3 Sekunden nach dem letzten Wort.
- Clips überschneiden sich nicht. Bei Überschneidung gewinnt der höhere Score.
- Lieber weniger, dafür starke Clips. Alles unter `mindest_score` fällt raus, auch wenn dann weniger als `clips_pro_folge` übrig bleiben. Dann im Auftrag vermerken, warum.

Kurzes Python im Geräte-Shell zum Nachschlagen der Wort-Zeiten:

```bash
cd "$HOME/mnt/Downloads/Clip-Tool/quellen/<job>" && python3 - <<'EOF'
import json
W=[w for s in json.load(open('transcript.json'))['segmente'] for w in s['words']]
for a,b in [(120,140),(300,320)]:
    print(f"--- {a}-{b}: "+" ".join(f"{w['w']}@{w['s']:.2f}" for w in W if a<=w['s']<=b))
EOF
```

## Bewertung (Virality-Score)

Jeder Clip wird einzeln bewertet. Score 0 bis 100 plus vier Noten (A+, A, A-, B+, B, B-, C+, C).

| Note | Frage |
|---|---|
| Hook | Fesseln die ersten 3 Sekunden? Gibt es sofort Spannung oder eine Frage? |
| Flow | Läuft der Clip ohne Leerlauf durch und endet sauber? |
| Value | Lernt man etwas, fühlt man etwas, lacht man? |
| Trend | Passt das Thema zu dem, was gerade geteilt und kommentiert wird? |

Richtwerte für den Score: 90 und mehr nur für echte Ausnahmen. 80 bis 89 stark. 70 bis 79 solide. Darunter nur, wenn der Nutzer es ausdrücklich will.
Die Begründung (`grund`) hat zwei bis drei kurze Sätze: Was passiert, warum es wirkt, was eine Schwäche ist.

## Titel und Hook

- `titel`: Kurz, neugierig, ehrlich, höchstens rund 50 Zeichen. Wird auch Dateiname.
- `hook`: Text in der weißen Box oben. Meist gleich dem Titel, darf zugespitzter sein. Höchstens 3 Zeilen im Bild.
- Schreibweise kommt aus `stil.hook_schreibweise` (gross oder normal). Den Text normal schreiben, das Großschreiben macht die Engine.
- Keine Ausrufezeichen, keine Emojis, keine falschen Versprechen.

## Korrekturen

Whisper verhört sich bei Fachwörtern und Namen. Im Plan unter `korrekturen` ein Wörterbuch anlegen: `{"falsch": "richtig"}`. Gilt Wort für Wort, Satzzeichen bleiben. Pro Clip geht auch `clips[].korrekturen`.

## Plan-Datei

Nach `plaene/<job>.json` schreiben (über device_bash mit Heredoc oder device_commit_files):

```json
{
  "job": "2026-11-20-folge-12",
  "konto": "mein-konto",
  "folge": "Folge 12",
  "stil": { "...": "Block aus einstellungen/<konto>.stil" },
  "korrekturen": {"Turnikey": "Tourniquet"},
  "clips": [
    {"nr": 1, "start": 132.2, "ende": 205.4, "titel": "Wer nicht hilft, macht sich strafbar",
     "hook": "Wer nicht hilft, macht sich strafbar", "score": 88,
     "noten": {"hook": "A", "flow": "A-", "value": "A", "trend": "B+"},
     "grund": "Zwei bis drei Sätze."}
  ]
}
```

`quelle`, `transkript` und `ausgabe` dürfen fehlen. Standard: `quellen/<job>/source.mp4`, `quellen/<job>/transcript.json`, `clips/<konto>/<folge>/`.
Optional pro Clip: `intro_wort` (ein Wort fürs große Intro, nur wenn `stil.intro_wort` an ist), `schluesselwoerter` (Liste, für eingefärbte Wörter).

Danach den Job `rendern` anlegen. Ergebnis: `clips/<konto>/<folge>/<Titel>.mp4`, Vorschaubilder in `_vorschau/NN.jpg`, Übersicht `clips.json` (Felder `datei` und `vorschau` relativ zu `Clip-Tool`).

## Ins Clip-Studio eintragen

1. Vorschaubilder holen: device_stage_files mit den Pfaden `~/Downloads/Clip-Tool/clips/<konto>/<folge>/_vorschau/NN.jpg`.
2. Im Container in einen Ordner kopieren und mit publish_files ins Artefakt laden: `as` = `vorschau/<job>-NN.jpg`, `mode` = `patch`, `base_version` aus get_artifact. Vorher list_files aufrufen, falls das verlangt wird.
3. db_write: pro Clip `clips/<job>-NN` mit allen Feldern, `vorschau` = `vorschau/<job>-NN.jpg`, `status` = `neu`. Dann den Auftrag auf `fertig` setzen (`clips_anzahl`, `schritt` mit einem kurzen Satz) und `system/status` aktualisieren.
4. Kurz melden: Anzahl Clips, Score-Spanne, Ordner.

## Typische Fehler

| Meldung im Log | Lösung |
|---|---|
| `No such file or directory: 'ffmpeg'` | Runner über „Clip-Tool starten.command“ starten, das setzt den ffmpeg-Pfad |
| yt-dlp: „Sign in to confirm“ oder 403 | Später nochmal versuchen. Alternativ das Video als Datei in `quellen` legen und Job mit `"datei": "quellen/<name>.mp4"` statt `url` |
| Runner-Lebenszeichen alt | „Clip-Tool starten.command“ öffnen |
| `Encoder-Fehler` | Mit `"qualitaet": "mittel"` erneut rendern |
