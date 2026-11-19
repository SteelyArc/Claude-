# ZEITSPUREN – Hinweise für Claude

Dieses Repository ist das Videoproduktionssystem des Geschichtskanals ZEITSPUREN
(historische Dokumentationen, 9:16, 1080×1920, für TikTok).

Die Person, die es bedient, programmiert nicht und arbeitet meist über Claude Code
auf dem Android-Handy. Antworte auf Deutsch, einfach und ohne Fachjargon.

## Typische Aufträge und was zu tun ist

**„Erstelle das Video für Projekt X“ / „Mach das Video X“**
1. `git pull` auf dem aktuellen Branch (neu hochgeladene Dateien holen). Liegt das
   Projekt nur auf `main`, vorher `git fetch origin main` und die Projektdateien von
   dort übernehmen (`git checkout origin/main -- projekte/X`).
2. **Immer zuerst prüfen:** `python3 -m zeitspuren X --pruefen`. Meldet das Programm
   eine Abweichung von der Kanalvorgabe (Länge ≠ 5 min, zu wenige Bilder), die
   Person **vor dem Erstellen** in einfachen Worten darauf hinweisen und fragen, wie
   sie vorgehen möchte (neue Aufnahme, mehr Bilder oder bewusst trotzdem erstellen).
   Nur nach ausdrücklicher Zustimmung mit `--bestaetigt` rendern.
3. Erst eine schnelle Vorschau, wenn die Person das möchte:
   `python3 -m zeitspuren X --vorschau`
4. Endfassung: `python3 -m zeitspuren X` (Dauer ≈ 3–4 × Videolänge, bei 5 min also
   rund 15–20 min; im Hintergrund laufen lassen und Fortschritt melden).
5. Die Datei `projekte/X/ausgabe/X.mp4` mit dem SendUserFile-Werkzeug übergeben
   und die Ausgabe des Programms kurz zusammenfassen (Bildreihenfolge, Hinweise).
6. Die erzeugte `projekte/X/ausgabe/zeitplan_verwendet.txt` committen und pushen;
   MP4-Dateien werden nicht committet (siehe .gitignore).

**„Lege ein neues Projekt X an“**
Ordner `projekte/X/` anlegen, `projekte/_vorlage/projekt.txt` hineinkopieren,
committen, pushen und erklären, wie Bilder und Audio über die GitHub-Webseite
hochgeladen werden (siehe README, Abschnitt „Material hochladen“).

**„Bild 3 soll früher/später kommen“, „Karte langsamer“ usw.**
`projekte/X/zeitplan.txt` anlegen oder anpassen (Format siehe README) – als
Vorlage dient `ausgabe/zeitplan_verwendet.txt`. Danach neu rendern.

## Unverrückbare Regeln des Kanals
- **Ziel-Länge jeder Dokumentation: ca. 5 Minuten (300 s).** Die Sprecheraufnahme
  soll möglichst genau 5 Minuten lang sein (Standard-Toleranz ± 10 s, Einstellungen
  `ziel_laenge` / `laenge_toleranz`). Weicht sie ab, die Person darauf hinweisen,
  **bevor** ein Video erstellt wird – niemals die Laufzeit durch Dehnen/Stauchen der
  Stimme, lange Standbilder oder Stille „passend machen“.
- Die Bilder müssen die gesamte Erzählung tragen: kein Bild länger als
  `bilddauer_max` (Standard 12 s). Für 5 Minuten braucht es mindestens 25, besser
  etwa 35–40 Bilder; fehlen Bilder, darauf hinweisen statt zu strecken.
- Bildwechsel sollen zum gesprochenen Inhalt passen (Zeitplan bzw. ab Etappe 2
  automatisch per Spracherkennung).
- Bild und Ton müssen exakt synchron und gleich lang sein (prüft das Programm am Ende).
- Niemals Bilder erzeugen, erfinden, KI-generieren, retuschieren oder inhaltlich
  verändern. Erlaubt: Ausschnitt, Zoom, Schwenk, dezente Farbkorrektur.
- Die Sprecherstimme nie beschleunigen, verlangsamen, in der Tonhöhe ändern oder
  komprimieren – nur eine gleichbleibende Lautstärkeanpassung.
- Keine hektischen Schnitte oder Effekte; ruhiger TV-Dokumentationsstil.
- Für Tests nur eindeutig als „TESTBILD“ beschriftete synthetische Muster
  verwenden und diese nicht ins Repository übernehmen.

## Technik
- Einstieg: `zeitspuren/__main__.py`. Module: `audio.py` (Analyse, Lautheit),
  `bilder.py` (Bildplatten, Kamerafahrten), `zeitplan.py`, `render.py`
  (Einzelbilder in Python mit Subpixel-Transformation → FFmpeg/libx264).
- Benötigt: Python 3.10+, Pillow, ffmpeg/ffprobe ≥ 6.
- Ausbaustufen: Etappe 2 = automatische Bildwechsel per Spracherkennung (Whisper),
  Etappe 3 = eingebrannte Untertitel, Titelkarte, Jahreszahlen, Quellenangaben.
