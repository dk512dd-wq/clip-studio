# Clip-Studio

> **Für Claude:** Der Nutzer möchte das Clip-Studio installieren. Lies und befolge [ANLEITUNG-FUER-CLAUDE.md](https://raw.githubusercontent.com/dk512dd-wq/clip-studio/main/ANLEITUNG-FUER-CLAUDE.md). Arbeite Schritt für Schritt und frag nur, was du nicht selbst herausfinden kannst.

Dein eigener Clipper wie Opus Clip. Läuft auf deinem Mac, gesteuert von deinem Claude.

- Aus einer YouTube-Folge werden fertige Hochkant-Clips: 1080 × 1920, Hook-Titel oben, Untertitel Wort für Wort, Gesicht immer in der Mitte.
- Claude liest das ganze Transkript, sucht die stärksten Momente und bewertet jeden Clip mit einem Virality-Score und Noten für Hook, Flow, Value und Trend.
- Feste Einstellungen pro Konto im Clip-Studio. Einmal einrichten, danach nur noch Links einfügen.
- Optional: Claude plant die Clips per iPhone direkt in TikTok Studio ein. Auf Wunsch jede Nacht von selbst.

## So installierst du es

1. Öffne die Claude-Desktop-App auf deinem Mac und starte einen neuen Chat.
2. Schick diesen Link mit dem Satz „Installier mir das Clip-Studio“.
3. Claude führt dich durch alles. Du tippst nur dort, wo es nur du kannst, zum Beispiel beim App Store oder am iPhone.

## Was du brauchst

- Mac mit macOS 14 oder neuer, am besten mit Apple-Chip
- Claude-Abo mit Desktop-App
- Rund 5 GB freien Speicher
- Für das iPhone-Einplanen: iPhone mit Kabel, Xcode (kostenlos im App Store)

## Danach

Link ins Clip-Studio einfügen und Claude schreiben: „Clips machen“. Die fertigen Clips liegen in Downloads › Clip-Tool › clips und stehen im Clip-Studio mit Score und Begründung.

Es nutzt dein eigenes Claude und deinen eigenen Mac. Es fallen keine weiteren Kosten an.

## Inhalt

| Ordner | Inhalt |
|---|---|
| `engine/` | Schnitt-Engine in Python (Download, Transkript, Gesichtsverfolgung, Untertitel, Export) |
| `mac/` | Startdateien zum Doppelklicken: Installieren, Starten, iPhone, Autostart |
| `studio/` | Das Clip-Studio als Seite für Claude |
| `skill/` | Skill für Claude: „Clips machen“, „Clips einplanen“, „Automatik einrichten“ |
| `docs/` | Details für Claude: Clippen und Bewertung, iPhone und TikTok Studio |

Nutze nur Videos, an denen du die Rechte hast oder für die du eine Erlaubnis hast.

Lizenzen: siehe `LICENSE` und `DRITTANBIETER.md`.
