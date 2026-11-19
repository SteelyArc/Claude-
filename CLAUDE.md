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
4. Endfassung: `python3 -m zeitspuren X` (Dauer ≈ 2 × Videolänge, bei 5 min also
   rund 10 min; im Hintergrund laufen lassen und Fortschritt melden).
5. Die Datei `projekte/X/ausgabe/X.mp4` mit dem SendUserFile-Werkzeug übergeben
   und die Ausgabe des Programms kurz zusammenfassen (Bildreihenfolge, Hinweise).
6. Die erzeugte `projekte/X/ausgabe/zeitplan_verwendet.txt` committen und pushen;
   MP4-Dateien werden nicht committet (siehe .gitignore).

**Drehbuch schreiben (Normalfall für jedes neue Video)**
Ziel ist eine Doku im TV-Stil, keine Diashow. Claude schreibt `projekte/X/drehbuch.txt`
(Format: `projekte/_vorlage/drehbuch_beispiel.txt`, Docstring in `zeitspuren/drehbuch.py`):
1. Inhalt der Erzählung erfassen – Sprechertext/Manuskript, ab Etappe 2 das
   Transkript mit Zeitstempeln. Ohne Zeitstempel die Person nach dem Manuskript
   fragen und Zeitpunkte nicht raten, sondern als Vorschlag kennzeichnen.
2. Szenen dem Inhalt zuordnen: Ereignis/Person → passendes Foto; Vertrag, Brief,
   Zeitung → `dokument`; Bewegung, Massen, Kampf → `film` (falls vorhanden);
   **jede Erklärung geografischer Veränderungen → `karte`** genau ab diesem Satz,
   Grenzwechsel (`wechsel_bei`) auf den Satz legen, in dem die Veränderung genannt wird.
3. Abwechslung: höchstens 4–5 Fotos/Dokumente hintereinander, für 5 Minuten
   typischerweise 3–6 Kartenszenen (je 12–25 s). Schnittanalyse des Programms beachten.
4. Ortsmarken (`ort`, `zeit`) und `quelle` bei Fotos/Dokumenten/Filmen eintragen –
   Quellen nur aus Angaben der Person (z. B. `quellen.txt`), nie erfinden.
5. `python3 -m zeitspuren X --pruefen` – meldet falsche Ländernamen mit Vorschlägen
   aus dem Datensatz, fehlende Orte, nicht vorhandene Kartenjahre.

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
- **Karten sind vollständig ENGLISCH beschriftet** (Titel, Länder, Orte, Legende),
  heller Atlas-Stil des 19. Jahrhunderts (Vorbild: klassischer Europa-Atlas und
  moderne „Partitions of Poland“-Karte). Fotos/Dokumente/Ton bleiben davon unberührt.
- **Kartendaten:** Mitteleuropa 1918–1939 vorrangig OpenHistoricalMap (`daten/karten/ohm`,
  geprüft, siehe QUELLEN.md; neue Relationen nur mit `werkzeuge/ohm_holen.py` laden und
  vor Verwendung an belegten Orten prüfen); sonst ab 1886 CShapes 2.0 (tagesgenau); vor 1886 nur
  historical-basemaps mit Warnung (nachweislich fehlerhaft, z. B. Teilungen Polens)
  → die Person vorher fragen, besser Originalkarte. 1772/1793 gibt es in keinem
  verfügbaren Datensatz.
- **Karten:** Grenzen nur aus den Daten (`daten/karten`). Niemals Grenzverläufe, Zwischenstände oder Gebiete selbst zeichnen
  oder „ungefähr passend“ ein anderes Jahr ausgeben, ohne dass die Karte den
  tatsächlichen Stand nennt (macht das Programm automatisch). Passt kein Stichjahr
  zum erzählten Ereignis, der Person sagen und eine eingescannte Originalkarte
  vorschlagen. Gebietsnamen müssen exakt im Datensatz des Jahres stehen (`--pruefen`).
- Archivfilme laufen in Originalgeschwindigkeit; ihr Originalton wird nicht verwendet.
- Für Tests nur eindeutig als „TESTBILD“ beschriftete synthetische Muster
  verwenden und diese nicht ins Repository übernehmen.

## Technik
- MCP-Server **claude-video-vision** (npm, MIT, Version fest 1.4.0, in `.mcp.json`):
  lässt Claude Videos ansehen (Einzelbilder per FFmpeg, Ton per Whisper/Gemini/OpenAI).
  Gut zur Kontrolle fertiger ZEITSPUREN-Videos. Vor der ersten Nutzung `video_setup`
  bzw. `video_configure` aufrufen; Ton nur dann an Google/OpenAI senden, wenn die Person
  das ausdrücklich will (Standard: keine Übertragung).
- Einstieg: `zeitspuren/__main__.py`. Module: `audio.py` (Analyse, Lautheit),
  `bilder.py` (Bildplatten, Kamerafahrten), `zeitplan.py`, `render.py`
  (Einzelbilder in Python mit Subpixel-Transformation → FFmpeg/libx264),
  `drehbuch.py` (Format, Prüfung, Schnittanalyse), `karten.py` (animierte Karten,
  Cairo, Lambert-Projektion), `film.py` (Archivfilm), `texte.py` (Einblendungen).
- Ohne `drehbuch.txt` läuft exakt der Etappe-1-Weg (Regressionstest: Vorschau-MD5
  eines Testprojekts vor/nach Änderungen vergleichen).
- Benötigt: Python 3.10+, Pillow, pycairo, shapely, numpy, ffmpeg/ffprobe ≥ 6.
- Karten-Drehbuch zusätzlich: `zonen`/`zonen_danach` (Schlüssel aus `daten/karten/ohm/zonen.json`,
  z. B. allenstein, marienwerder, upper-silesia-1920, upper-silesia, east-upper-silesia) und
  `vermerke` (`Text@Ort` oder `Text@Breite,Länge`, `|` = Zeilenumbruch).
  **In jeder neuen Sitzung zuerst:** `pip install -r requirements.txt`.
- Kartendaten: `daten/karten` (Quellen/Lizenzen in `daten/QUELLEN.md`). Fehlende
  Stichjahre lädt `karten.py` aus dem gepinnten GitHub-Stand nach → danach committen.
- Ausbaustufen: Etappe 2 = automatische Bildwechsel per Spracherkennung (Whisper),
  Etappe 3 = eingebrannte Untertitel, Titelkarte, Jahreszahlen, Quellenangaben.
