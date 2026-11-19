"""Das Drehbuch (Datei ``drehbuch.txt``) beschreibt jede Szene des Films.

Beispiel::

    # Zeit   Art        Quelle
    0:00     foto       01_berlin_1938.jpg
             ort: Berlin
             zeit: Herbst 1938
             quelle: Bundesarchiv, Bild 183-…

    0:11     karte      1938
             wechsel: 1945
             wechsel_bei: 0:21
             ausschnitt: Europa
             fahrt: Danzig 900
             hervorheben: Germany=rot:Deutsches Reich; Poland=gold:Polen
             hervorheben_danach: Poland=gold:Polen
             orte: Berlin, Danzig, Warschau
             titel: Der Weg in den Krieg

    0:27     dokument   04_vertrag.jpg
    0:36     film       05_wochenschau.mp4
             ab: 1:12

Die Zeit ist immer der Zeitpunkt in der Sprecheraufnahme, ab dem die Szene
zu sehen ist. Ab Etappe 2 schlägt das System diese Zeitpunkte anhand der
Spracherkennung selbst vor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import karten
from .bilder import BEWEGUNGEN, BILD_ENDUNGEN, DARSTELLUNGEN
from .film import FILM_ENDUNGEN
from .zeitplan import ZeitplanFehler, zeit_lesen

ARTEN = ("foto", "dokument", "karte", "film")

SCHLUESSEL = {
    "foto": {"ort", "zeit", "quelle", "bewegung", "darstellung"},
    "dokument": {"ort", "zeit", "quelle", "bewegung", "darstellung"},
    "film": {"ort", "zeit", "quelle", "ab", "darstellung"},
    "karte_bild": {"ort", "zeit", "quelle", "bewegung", "darstellung"},
    "karte": {"wechsel", "wechsel_bei", "ausschnitt", "fahrt", "fahrt_von", "fahrt_bis", "hervorheben",
              "hervorheben_danach", "nachbarn", "orte", "titel", "jahreszahl", "zonen", "zonen_danach",
              "vermerke", "vermerke_ab"},
}

_KOPF = re.compile(r"^(\d[\d:.,]*)\s+(\w+)\s*(.*)$")
_OPTION = re.compile(r"^([\wäöüß]+)\s*:\s*(.*)$")


class DrehbuchFehler(ZeitplanFehler):
    pass


@dataclass
class DSzene:
    zeit: float
    art: str
    quelle: str
    zeile: int
    optionen: dict = field(default_factory=dict)
    pfad: Path | None = None  # Datei bei foto/dokument/film/Kartenbild

    @property
    def ist_datenkarte(self) -> bool:
        return self.art == "karte" and self.pfad is None

    @property
    def anzeigename(self) -> str:
        if self.pfad is not None:
            return self.pfad.name
        stand = self.quelle + (f"→{self.optionen['wechsel']}" if "wechsel" in self.optionen else "")
        return f"Karte {stand}"


def _ohne_kommentar(zeile: str) -> str:
    # '#' leitet nur dann einen Kommentar ein, wenn davor nichts oder ein Leerzeichen steht
    return re.sub(r"(^|\s)#.*$", "", zeile).rstrip()


def lesen(datei: Path, projektordner: Path) -> list[DSzene]:
    dateien = {p.name.lower(): p for p in _dateien(projektordner)}
    szenen: list[DSzene] = []
    for nr, roh in enumerate(datei.read_text(encoding="utf-8-sig").splitlines(), 1):
        zeile = _ohne_kommentar(roh)
        if not zeile.strip():
            continue
        kopf = _KOPF.match(zeile.strip()) if not zeile[:1].isspace() else None
        if kopf:
            zeit = zeit_lesen(kopf.group(1))
            art = kopf.group(2).lower()
            quelle = kopf.group(3).strip()
            if art not in ARTEN:
                raise DrehbuchFehler(f"drehbuch.txt Zeile {nr}: Unbekannte Szenenart '{art}'. "
                                     f"Möglich: {', '.join(ARTEN)}.")
            if not quelle:
                raise DrehbuchFehler(f"drehbuch.txt Zeile {nr}: Nach '{art}' fehlt die Datei bzw. das Kartenjahr.")
            sz = DSzene(zeit, art, quelle, nr)
            if art != "karte" or not re.fullmatch(r"-?\d+|\d{4}-\d{2}-\d{2}", quelle):
                pfad = dateien.get(quelle.lower())
                if pfad is None:
                    raise DrehbuchFehler(f"drehbuch.txt Zeile {nr}: Datei '{quelle}' gibt es in diesem Projekt nicht.")
                sz.pfad = pfad
            szenen.append(sz)
            continue
        opt = _OPTION.match(zeile.strip())
        if not opt or not szenen:
            raise DrehbuchFehler(f"drehbuch.txt Zeile {nr}: Unverständlich: '{zeile.strip()}'. "
                                 f"Erwartet: 'ZEIT ART QUELLE' oder eingerückt 'name: wert'.")
        sz = szenen[-1]
        schluessel = opt.group(1).lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        gruppe = "karte_bild" if sz.art == "karte" and sz.pfad is not None else sz.art
        if schluessel not in SCHLUESSEL[gruppe]:
            raise DrehbuchFehler(f"drehbuch.txt Zeile {nr}: '{schluessel}' passt nicht zu '{sz.art}'. "
                                 f"Möglich: {', '.join(sorted(SCHLUESSEL[gruppe]))}.")
        sz.optionen[schluessel] = opt.group(2).strip()

    if not szenen:
        raise DrehbuchFehler("drehbuch.txt enthält keine Szenen.")
    szenen.sort(key=lambda s: s.zeit)
    szenen[0].zeit = 0.0
    for a, b in zip(szenen, szenen[1:]):
        if abs(a.zeit - b.zeit) < 1e-6:
            raise DrehbuchFehler(f"drehbuch.txt: Zwei Szenen beginnen gleichzeitig ({a.zeile} und {b.zeile}).")
    return szenen


def _dateien(projektordner: Path) -> list[Path]:
    endungen = BILD_ENDUNGEN | FILM_ENDUNGEN
    ordner = [projektordner, projektordner / "bilder", projektordner / "filme", projektordner / "karten"]
    return [p for o in ordner if o.is_dir() for p in o.iterdir()
            if p.is_file() and p.suffix.lower() in endungen and not p.name.startswith(".")]


def hervorhebungen(text: str, stand: "karten.Stand") -> list[karten.Hervorhebung]:
    """'Poland=rot:Poland; Germany (Prussia)=blau:German Reich' → Liste.
    Namen werden gegen die Daten des Kartenstands geprüft; Beschriftung auf Englisch."""
    liste = []
    for teil in (t.strip() for t in text.split(";")):
        if not teil:
            continue
        if "=" not in teil:
            raise karten.KartenFehler(f"Hervorhebung '{teil}': Format 'Gebiet=Farbe' oder 'Gebiet=Farbe:Beschriftung'.")
        name, rest = (t.strip() for t in teil.split("=", 1))
        farbe, _, beschriftung = rest.partition(":")
        name = karten.gebiet_pruefen(stand, name)
        liste.append(karten.Hervorhebung(name, karten.farbe_lesen(farbe), beschriftung.strip() or name))
    return liste


def nachbarn(text: str, stand: "karten.Stand", streng: bool = True) -> list[tuple[str, str]]:
    """'Russia (Soviet Union)=Soviet Union; Lithuania' → [(Datenname, Beschriftung)].
    Nicht streng: Namen, die es in diesem Stand nicht gibt, werden übersprungen."""
    liste = []
    for teil in (t.strip() for t in text.split(";")):
        if not teil:
            continue
        name, _, text_ = (t.strip() for t in teil.partition("="))
        try:
            name = karten.gebiet_pruefen(stand, name)
        except karten.KartenFehler:
            if streng:
                raise
            continue
        liste.append((name, text_ or name))
    return liste


def datenwarnungen(szenen: list[DSzene]) -> list[str]:
    """Warnungen zu Kartenständen aus Näherungsdaten (vor 1886)."""
    warnungen = []
    for sz in szenen:
        if not sz.ist_datenkarte:
            continue
        for text in [sz.quelle] + ([sz.optionen["wechsel"]] if "wechsel" in sz.optionen else []):
            try:
                w = karten.daten_warnung(karten.stand_lesen(text))
            except karten.KartenFehler:
                continue
            if w:
                warnungen.append(f"Zeile {sz.zeile}: {w}")
    return warnungen


def pruefen(szenen: list[DSzene]) -> list[str]:
    """Prüft alle Szenen gegen Dateien und Kartendaten. Gibt Fehlermeldungen zurück."""
    fehler = []
    for sz in szenen:
        o = sz.optionen
        ort = f"Zeile {sz.zeile} ({sz.anzeigename})"
        try:
            if sz.art in ("foto", "dokument", "karte") and sz.pfad is not None:
                if sz.pfad.suffix.lower() not in BILD_ENDUNGEN:
                    fehler.append(f"{ort}: '{sz.pfad.name}' ist kein Bild.")
            if sz.art == "film" and sz.pfad.suffix.lower() not in FILM_ENDUNGEN:
                fehler.append(f"{ort}: '{sz.pfad.name}' ist kein Film.")
            if "bewegung" in o and o["bewegung"] not in BEWEGUNGEN:
                fehler.append(f"{ort}: Bewegung '{o['bewegung']}' unbekannt.")
            if "darstellung" in o and o["darstellung"] not in DARSTELLUNGEN:
                fehler.append(f"{ort}: Darstellung '{o['darstellung']}' unbekannt.")
            if "ab" in o:
                zeit_lesen(o["ab"])
            if sz.ist_datenkarte:
                st1 = karten.stand_lesen(sz.quelle)
                hervorhebungen(o.get("hervorheben", ""), st1)
                staende = [st1]
                if "wechsel" in o:
                    st2 = karten.stand_lesen(o["wechsel"])
                    staende.append(st2)
                    hervorhebungen(o.get("hervorheben_danach", o.get("hervorheben", "")), st2)
                if "nachbarn" in o:
                    gefunden = [n for st in staende for n in nachbarn(o["nachbarn"], st, streng=False)]
                    for teil in (t.split("=")[0].strip() for t in o["nachbarn"].split(";") if t.strip()):
                        if not any(n[0].lower() == teil.lower() for n in gefunden):
                            karten.gebiet_pruefen(staende[0], teil)  # löst Fehlermeldung mit Vorschlägen aus
                for schl in ("wechsel_bei", "fahrt_von", "fahrt_bis"):
                    if schl in o:
                        zeit_lesen(o[schl])
                karten._ausschnitt_geo(o.get("ausschnitt", "Europa"), 9 / 16)
                if "fahrt" in o:
                    karten._ausschnitt_geo(o["fahrt"], 9 / 16)
                for name in orte_liste(o.get("orte", "")):
                    karten.ort_finden(name)
                zonen_liste(o.get("zonen", ""))
                zonen_liste(o.get("zonen_danach", ""))
                vermerke_liste(o.get("vermerke", ""))
        except (karten.KartenFehler, ZeitplanFehler, ValueError) as f:
            fehler.append(f"{ort}: {f}")
    return fehler


def _liste(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def orte_liste(text: str) -> list[str]:
    # Koordinatenangaben 'Name@52.5,13.4' enthalten selbst Kommas → vorher schützen
    geschuetzt = re.sub(r"@(-?[\d.]+),\s*(-?[\d.]+)", r"@\1|\2", text)
    return [t.replace("|", ",") for t in _liste(geschuetzt)]


def schnittanalyse(szenen: list[DSzene]) -> list[str]:
    """Hinweise gegen monotone Bildfolgen."""
    hinweise = []
    art_von = ["foto" if s.art == "dokument" else s.art for s in szenen]
    anzahl = {a: sum(1 for s in szenen if s.art == a) for a in ARTEN}
    laengste, aktuell = 1, 1
    for a, b in zip(art_von, art_von[1:]):
        aktuell = aktuell + 1 if a == b else 1
        laengste = max(laengste, aktuell)
    woerter = {"foto": ("Foto", "Fotos"), "dokument": ("Dokument", "Dokumente"),
               "karte": ("Karte", "Karten"), "film": ("Archivfilm", "Archivfilme")}
    zusammen = ", ".join(f"{n} {woerter[a][n != 1]}" for a, n in anzahl.items() if n)
    hinweise.append(f"Schnitt: {zusammen}; längste Folge gleicher Art: {laengste}.")
    if anzahl["karte"] == 0:
        hinweise.append("Keine Karte im Film – für geografische Abschnitte eine animierte Karte einplanen.")
    if laengste >= 6:
        hinweise.append(f"{laengste} Fotos/Dokumente folgen direkt aufeinander – wirkt schnell wie eine "
                        f"Diashow. Eine Karte, ein Dokument oder Archivfilm dazwischen lockert auf.")
    return hinweise


def zonen_liste(text: str) -> list[str]:
    """'allenstein; marienwerder' → Schlüssel (geprüft gegen daten/karten/ohm/zonen.json)."""
    from . import ohm
    liste = [t.strip().lower() for t in text.split(";") if t.strip()]
    for z in liste:
        if z not in ohm.zonen_konfig():
            raise karten.KartenFehler(f"Zone '{z}' unbekannt. Vorhanden: {', '.join(sorted(ohm.zonen_konfig()))}.")
    return liste


def vermerke_liste(text: str) -> list[tuple[str, float, float]]:
    """'Polish Corridor@53.85,17.95; Battle of Warsaw|Aug 1920@Warsaw' → (Text, Breite, Länge).
    Ein '|' im Text erzeugt einen Zeilenumbruch."""
    liste = []
    for teil in (t.strip() for t in text.split(";")):
        if not teil:
            continue
        if "@" not in teil:
            raise karten.KartenFehler(f"Vermerk '{teil}': Format 'Text@Ort' oder 'Text@Breite,Länge'.")
        text_, ort = teil.rsplit("@", 1)
        _, lat, lon = karten.ort_finden(ort if "," not in ort else f"x@{ort}")
        liste.append((text_.strip(), lat, lon))
    return liste
