# ZEITSPUREN – Videoproduktion

Automatische Herstellung hochwertiger historischer Dokumentationsvideos im
Hochformat (1080 × 1920, 9:16) für TikTok – aus **Ihren** historischen Fotos,
Dokumenten, Archivfilmen, **animierten historischen Karten** und einer fertigen
Sprecheraufnahme. Keine Diashow, sondern ein abwechslungsreicher Schnitt im
Stil hochwertiger TV-Geschichtsdokumentationen.

**Kanalvorgabe:** Jede Dokumentation dauert **ca. 5 Minuten**. Die
Sprecheraufnahme sollte also möglichst genau 5:00 Minuten lang sein, und es
werden etwa **35–40 Bilder** benötigt (mindestens 25).

Sie brauchen keine Programmierkenntnisse. Die Bedienung läuft über Claude Code
(z. B. auf dem Android-Handy): Sie laden das Material hoch und schreiben Claude
einen Satz wie *„Erstelle das Video für Projekt mauerfall“*.

---

## So funktioniert es (in einfachen Worten)

1. **Die Sprecheraufnahme wird vermessen.** Das System misst die genaue Länge und
   die Lautstärke. Die Lautstärke wird – falls nötig – gleichmäßig auf das bei
   TikTok übliche Niveau gebracht. Die Stimme wird **nicht** schneller, langsamer
   oder anders klingend gemacht.
2. **Die Bilder werden zeitlich angeordnet.** Die Reihenfolge ergibt sich aus der
   Nummer am Anfang des Dateinamens (`01_…`, `02_…`). Ohne weitere Angaben wird die
   Erzählzeit gleichmäßig auf die Bilder verteilt. Mit einer Datei `zeitplan.txt`
   bestimmen Sie die genauen Wechselzeitpunkte (siehe unten). In Etappe 2 erkennt
   das System die Satzanfänge selbst und setzt die Bildwechsel automatisch dorthin.
3. **Jedes Bild bekommt eine ruhige Kamerafahrt** – langsames Hinein- oder
   Herauszoomen oder ein sanfter Schwenk. Die Geschwindigkeit ist bei allen Bildern
   gleich, dadurch wirkt der Film aus einem Guss und nicht wie eine Diashow.
4. **Weiche Überblendungen** (standardmäßig 1,2 Sekunden) verbinden die Bilder.
   Der Film beginnt mit einer Aufblende aus Schwarz und endet mit einer Abblende.
5. **Hochformat-Bilder** füllen das ganze Bild. **Querformat-Bilder und Karten**
   werden immer vollständig gezeigt; dahinter liegt eine stark unscharfe, dunkle
   Kopie desselben Bildes als ruhiger Hintergrund. Das Originalbild selbst wird
   **niemals** verändert, ergänzt oder neu erzeugt.
6. **Export** als MP4 (H.264, 1080 × 1920, 30 Bilder/s, AAC-Ton 48 kHz). Am Ende
   prüft das System automatisch, dass Bild und Ton exakt gleich lang sind.

---

## Die vier Szenenarten

| Art | Was zu sehen ist | Woher das Material kommt |
|---|---|---|
| **foto** | Originalfoto mit langsamer Kamerafahrt, optional Ortsmarke („BERLIN · Herbst 1938“) und Bildquelle | Ihre Archivfotos |
| **dokument** | Urkunde, Brief, Zeitungsseite – vollständig gezeigt, langsames Heranfahren | Ihre Scans |
| **film** | Echter Archivfilm (z. B. Wochenschau) in Originalgeschwindigkeit, ohne Originalton | Ihre Filmdateien (`.mp4`, `.mov` …) |
| **karte** | **Animierte historische Karte**: Länder farbig hervorgehoben, Kamerafahrt auf Städte/Regionen, animierter Grenzwechsel, Ortsnamen und Jahreszahl elegant eingeblendet | Geprüfte historische Grenzdaten (siehe unten) – oder Ihre eingescannte Originalkarte |

### Wie genau sind die animierten Karten?
- Die Grenzen stammen aus dem wissenschaftlich dokumentierten Datensatz
  **historical-basemaps** (fest verankerter Versionsstand) für **Stichjahre**,
  z. B. 1815, 1878, 1900, **1914, 1920, 1930, 1938, 1945**, 1960, 1994 und viele
  frühere Epochen. Küsten, Flüsse und Orte stammen aus **Natural Earth**.
- **Zwischenstände werden nicht erfunden.** Ein Grenzwechsel blendet von einem
  Stichjahr zum nächsten über (z. B. 1938 → 1945). Die Karte zeigt immer klein
  an, welchen Stand sie darstellt.
- Ländernamen werden gegen die Daten des jeweiligen Jahres geprüft. Ein Name,
  den es im Datensatz nicht gibt, wird abgelehnt statt geraten.
- Grenzen, die der Datensatz selbst als „ungefähr“ einstuft, werden gestrichelt
  und blasser gezeichnet.
- Für sehr kleinräumige Ereignisse (einzelne Städte, Frontverläufe einzelner
  Tage) reicht die Genauigkeit eines Weltdatensatzes nicht – dafür eignet sich
  eine eingescannte Originalkarte als Szene „karte“ mit Dateinamen.

Details und Lizenzen: [`daten/QUELLEN.md`](daten/QUELLEN.md)

### Das Drehbuch
Welche Szene wann zu sehen ist, steht in der Datei `drehbuch.txt` im
Projektordner. **Sie müssen sie nicht selbst schreiben:** Claude erstellt sie
aus dem Inhalt Ihrer Erzählung, sodass Karten genau dann erscheinen, wenn
geografische Veränderungen erklärt werden, und Fotos zu den jeweiligen
Ereignissen passen. Ein kommentiertes Beispiel liegt in
`projekte/_vorlage/drehbuch_beispiel.txt`.

Vor dem Erstellen prüft das System das Drehbuch: Dateien vorhanden, Kartenjahre
verfügbar, Ländernamen im Datensatz, Orte im Ortsverzeichnis – und es meldet,
wenn zu viele Fotos hintereinander folgen (Diashow-Gefahr) oder keine Karte
vorkommt.

Ohne `drehbuch.txt` arbeitet das System wie bisher (Fotos gleichmäßig verteilt
oder nach `zeitplan.txt`).

---

## Ein neues Video herstellen – Schritt für Schritt

### Schritt 1: Projekt anlegen lassen
Schreiben Sie Claude: *„Lege ein neues Projekt **mauerfall** an.“*
(Nur Kleinbuchstaben, Ziffern und Unterstriche, keine Leerzeichen.)

### Schritt 2: Material hochladen (am Handy über den Browser)
1. Öffnen Sie im Browser die Seite Ihres Repositorys auf github.com.
2. Wählen Sie oben den Branch, den Claude Ihnen nennt.
3. Tippen Sie auf den Ordner **projekte** und dann auf Ihr Projekt, z. B. **mauerfall**.
4. Tippen Sie auf **Add file → Upload files** (am Handy ggf. über das „…“-Menü
   oder die „Desktop-Ansicht“ des Browsers).
5. Wählen Sie die Sprecheraufnahme und alle Bilder aus und tippen Sie auf
   **Commit changes**.

**Benennung der Dateien:**

| Datei | Beispiel | Hinweis |
|---|---|---|
| Sprecheraufnahme | `sprecher.mp3` | auch `.wav`, `.m4a` möglich |
| Bilder | `01_berlin_1961.jpg`, `02_karte_teilung.png`, … | Nummer = Reihenfolge; für 5 Minuten ca. 35–40 Bilder |
| Karten (Scans) | `05_karte_europa_1945.jpg` | Wörter *karte*, *map* oder *plan* im Namen → langsamer Zoom aufs Geschehen |
| Dokumente | `07_vertrag_1939.jpg` | |
| Archivfilme | `09_wochenschau.mp4` | Originalgeschwindigkeit, Originalton wird nicht verwendet |

**Bitte zu jedem Foto, Dokument und Film die Quelle notieren** (z. B. in einer
Datei `quellen.txt` im Projektordner: `01_berlin.jpg = Bundesarchiv, Bild 183-…`).
Claude übernimmt sie als dezente Quellenangabe ins Video.

Tipp: Bilder möglichst in hoher Auflösung verwenden (mindestens etwa 1500 Pixel
an der längeren Seite). Zu kleine Bilder meldet das System.

### Schritt 3: Video erstellen lassen
Schreiben Sie Claude: *„Erstelle das Video für Projekt mauerfall.“*

Claude prüft zuerst das Material, **bevor** gerechnet wird:
- Ist die Sprecheraufnahme deutlich kürzer oder länger als 5 Minuten
  (mehr als ± 10 Sekunden), sagt Claude Ihnen Bescheid und fragt, wie Sie
  vorgehen möchten. Die Stimme wird niemals schneller oder langsamer gemacht,
  um die Länge zu erreichen.
- Sind zu wenige Bilder vorhanden (ein Bild würde länger als 12 Sekunden
  stehen), erfahren Sie, wie viele Bilder noch fehlen. Das Video wird nicht
  durch lange Standbilder künstlich gestreckt.

Ein 5-Minuten-Video braucht in der Endfassung etwa 10 Minuten Rechenzeit.
Für einen schnellen ersten Eindruck: *„Erstelle eine Vorschau für mauerfall.“*

Claude schickt Ihnen die fertige MP4-Datei direkt in den Chat. Von dort können Sie
sie aufs Handy laden und bei TikTok hochladen.

### Schritt 4: Feinschliff (optional)
Sagen Sie Claude in eigenen Worten, was Sie ändern möchten, z. B.
*„Die Karte soll erst bei 0:24 kommen“* oder *„Bild 3 bitte ganz zeigen, nicht
abgeschnitten“*. Claude passt den Zeitplan an und erstellt das Video neu.

---

## Einstellungen (Datei `projekt.txt` im Projektordner)

| Einstellung | Möglichkeiten | Standard |
|---|---|---|
| `farbe` | `original`, `warm` (leicht wärmer), `schwarzweiss` | `original` |
| `filmkorn` | `leicht`, `aus` | `leicht` |
| `vignette` | `ja`, `nein` (dezent abgedunkelte Ränder) | `ja` |
| `hintergrund` | `unschaerfe`, `schwarz` (hinter Querformaten) | `unschaerfe` |
| `bewegung` | `ruhig`, `normal`, `lebendig` | `normal` |
| `ueberblendung` | Sekunden, 0.4 bis 3.0 | `1.2` |
| `ziel_laenge` | Ziel-Länge der Sprecheraufnahme, z. B. `5:00` | `5:00` |
| `laenge_toleranz` | erlaubte Abweichung in Sekunden | `10` |
| `bilddauer_max` | längste Standzeit eines Bildes in Sekunden | `12` |
| `vorlauf` / `nachlauf` | Sekunden Stille vor dem ersten bzw. nach dem letzten Wort | `0.6` / `2.0` |

## Genaue Bildwechsel (Datei `zeitplan.txt`, optional)

Eine Zeile pro Bild: **Zeitpunkt in der Sprecheraufnahme**, **Dateiname** und
optional Darstellung und Bewegung.

```
0:00     01_berlin_1961.jpg
0:07.5   02_karte_teilung.png      eingepasst   zoom-rein
0:15     03_mauerbau.jpg           ganz         schwenk-rechts
```

- Darstellung: `ganz` (füllt das Bild, Ränder werden abgeschnitten) oder
  `eingepasst` (vollständiges Bild).
- Bewegung: `zoom-rein`, `zoom-raus`, `schwenk-links`, `schwenk-rechts`,
  `schwenk-hoch`, `schwenk-runter`, `still`.

Nach jedem Durchlauf legt das System die tatsächlich verwendete Anordnung in
`ausgabe/zeitplan_verwendet.txt` ab – eine gute Vorlage zum Anpassen.

---

## Ausbaustufen
- [x] **Etappe 1:** Tonanalyse, Bildanordnung, Kamerafahrten, Überblendungen,
  Doku-Look, Export 1080 × 1920
- [x] **Erweiterung Doku-Stil:** animierte historische Karten, Dokumente,
  Archivfilme, elegante Einblendungen, Drehbuch mit Prüfung und Schnittanalyse
- [ ] **Etappe 2:** Spracherkennung mit Zeitstempeln → Claude legt Szenenwechsel
  und Kartenanimationen exakt auf die passenden Sätze
- [ ] **Etappe 3:** Elegante eingebrannte Untertitel, Titelkarte, Jahreszahlen,
  Quellenangaben, Logo
- [ ] **Etappe 4:** Komfortfunktionen (z. B. automatische Kapitel, Musikbett)

## Technischer Anhang (für Fachleute)
`python3 -m zeitspuren <projekt> [--vorschau]` – benötigt Python ≥ 3.10, Pillow
und ffmpeg/ffprobe ≥ 6. Einzelbilder werden in Python per Subpixel-Affintransformation
aus einer 1,12-fach überabgetasteten Bildplatte berechnet (ruckelfreie Zooms) und
roh an libx264 (CRF 18, preset fast, BT.709) übergeben.
