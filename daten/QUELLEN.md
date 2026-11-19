# Datenquellen und Lizenzen

## Detailgrenzen 1918–1939 (Mitteleuropa) – `karten/ohm/`
- **OpenHistoricalMap** (Lizenz: CC0), abgerufen über die Overpass-API mit
  `werkzeuge/ohm_holen.py`; jede Datei speichert Relation, Version und Zeitstempel.
- Tagesgenaue Fassungen für Deutsches Reich, Polen, Danzig, Litauen, Memelland,
  Tschechoslowakei, Teschener Schlesien; Zuordnung in `ohm/staaten.json`. Innerhalb
  ihrer Gültigkeit ersetzen sie die gröberen CShapes-Flächen.
- **Grenzen der Quelle:** Die Ereignisse sind belegt (z. B. FRUS, Versailler Vertrag),
  die Linienführung trägt in OHM den Vermerk „needs source for boundary lines“.
  Deshalb geprüft:
  - 42 belegte Ortszuordnungen (u. a. Kattowitz/Königshütte/Tarnowitz bis Juni 1922
    deutsch, danach polnisch; Gleiwitz/Beuthen/Oppeln deutsch; Korridor mit Gdingen,
    Putzig, Hela polnisch; Stolp, Lauenburg, Bütow deutsch; Allenstein, Marienwerder,
    Elbing deutsch; Soldau polnisch; Danzig/Zoppot Freie Stadt) – alle bestanden.
  - Abstimmungsgebiete 1920 = Versailler Vertrag Art. 94/96 (Kreise) – Abweichung 0,0 km².
- **Bewusst offen:** Polens Ostgrenze 1920 (polnisch-sowjetischer Krieg) ist in OHM
  nicht geschlossen. Das Programm zeigt dort keine Grenzlinie, sondern ein
  auslaufendes, schraffiertes umkämpftes Gebiet; die äußere Kante ist nur gepunktet
  und als „Riga line of 1921“ beschriftet.
- **1939–1945** (geprüft an 23 belegten Orten): Deutsches Reich vor/nach 26.10.1939,
  Generalgouvernement, Sowjetunion, Litauen, Polen ab 02.08.1945, Reichsgau Danzig-Westpreußen,
  Provinz Westpreußen 1909–1919. OHM zählt das Generalgouvernement zum Reichsgebiet; es war
  besetzt, nicht annektiert – es wird abgezogen und separat gezeigt (`minus` in staaten.json).
- **Nicht erfasst:** Mittellitauen (Okt. 1920 – Apr. 1922) – das Programm warnt; das
  oberschlesische Abstimmungsgebiet selbst (nur als Provinz beschriftet).
- Abstimmungsergebnisse: Allenstein 11.07.1920 97,9 % für Deutschland; Marienwerder
  11.07.1920 92,4 %; Oberschlesien 20.03.1921 59,6 % Deutschland, 40,4 % Polen.

## Staatsgrenzen ab 1886 (Hauptquelle) – `karten/cshapes/`
- **CShapes 2.0** – N. B. Weidmann, G. Schvitz, L. Girardin u. a. (ETH Zürich /
  Universität Konstanz). Schvitz et al. (2022), „Mapping the International System,
  1886–2019: The CShapes 2.0 Dataset“, *Journal of Conflict Resolution* 66(1).
- Lizenz: GPL ≥ 2 · Bezug: CRAN-Paket `cshapes` 2.0, GitHub-Spiegel `cran/cshapes`,
  Stand `54840534d9a82cfd01caf1021f85933e701e8318`, Datei `cshapes_2_gw.topojson.xz`
- Jede Grenzziehung hat exakte Gültigkeitsdaten (Beginn/Ende). Ein Kartenstand
  „1920“ bedeutet den 1. Juli 1920; genaue Tage sind möglich (`1920-10-07`).
- **Grobe Linien (Weltdatensatz):** z. B. Ost-Oberschlesien bereits ab 1919 polnisch,
  Tarnowitz nach 1922 deutsch, Memel 1914 russisch. Für Mitteleuropa 1918–1939
  daher OpenHistoricalMap (oben) vorrangig.
- Kodierungsregeln laut CShapes (Gleditsch-Ward-Staatensystem): Annexionen und
  Besetzungen im Zweiten Weltkrieg sind teils nicht als Grenzänderung erfasst
  (z. B. bleibt Österreich 1938–1945 eigenständig). Für solche Ereignisse eine
  Originalkarte verwenden oder das im Text klarstellen.

## Historische Grenzen vor 1886 (nur mit Warnung) – `karten/historisch/`
- **historical-basemaps** von André Ourednik und Mitwirkenden,
  https://github.com/aourednik/historical-basemaps
- Lizenz: GNU GPL v3.0
- Fest verankerter Versionsstand: `4b5039e50d8d2464b065bd76ad6086cd4597108d`
  (fehlende Stichjahre lädt das Programm automatisch genau aus diesem Stand nach)
- Verfügbare Stichjahre (Auszug ab 1700): 1700, 1715, 1783, 1800, 1815, 1878, 1880,
  1900, 1914, 1920, 1930, 1938, 1945, 1960, 1994, 2000, 2010 – dazu frühere Epochen
  bis 123000 v. Chr. (vollständige Liste: `zeitspuren/karten.py`, `STICHJAHRE`).
- Das Feld `BORDERPRECISION` (1 = ungefähr, 2 = mäßig genau, 3 = völkerrechtlich
  festgelegt) wird ausgewertet: ungefähre Grenzen werden gestrichelt und blasser
  gezeichnet.
- **Nachgewiesene Fehler (Stichproben):** 1783 Thorn und Krakau falsch zugeordnet
  (beide bis 1793/1795 polnisch); 1920 Straßburg bei Deutschland, Kattowitz bereits
  polnisch; 1945 Straßburg in deutscher Besatzungszone. Deshalb wird dieser Datensatz
  ab 1886 nicht mehr verwendet und davor nur mit ausdrücklicher Warnung.
- **Wichtig:** Der Datensatz ist eine Weltkarte im Überblicksmaßstab. Für
  Grenzverläufe im Detail (einzelne Landkreise, Flussabschnitte) ist er nicht
  gedacht; die Kamera sollte nicht näher als ca. 300 km Bildbreite heranfahren.
  Zwischen den Stichjahren werden keine Grenzen erfunden.

## Küsten, Seen, Flüsse, Orte – `karten/ne_*.geojson`, `karten/orte.csv`
- **Natural Earth** (1:50 Mio. bzw. 1:10 Mio. für Orte), https://www.naturalearthdata.com
- Lizenz: gemeinfrei (public domain)
- Versionsstand: nvkelso/natural-earth-vector `ca96624a56bd078437bca8184e78163e5039ad19`
- `orte.csv` ist ein kompakter Auszug aus `ne_10m_populated_places` (Name, deutscher
  Name, Land, Koordinaten, Einwohner) – enthält z. B. Danzig, Breslau, Königsberg
  über die deutschen Namensfelder.

## Schriften – `schriften/`
- **Cormorant Garamond** (Christian Thalmann, Catharsis Fonts) – SIL Open Font License 1.1
- **Source Sans 3** (Adobe) – SIL Open Font License 1.1
- Lizenztext: `schriften/OFL.txt`

## Empfohlene Quellenangabe im Video bzw. in der Videobeschreibung
„Map data: CShapes 2.0 (ETH Zurich), Natural Earth“ – ggf. zusätzlich
„historical-basemaps (A. Ourednik, GPL-3.0)“.
Die Karten blenden diese Angabe automatisch klein ein.
