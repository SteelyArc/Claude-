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
              "hervorheben_danach", "orte", "titel", "jahreszahl"},
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
            if art != "karte" or not re.fullmatch(r"-?\d+", quelle):
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


def hervorhebungen(text: str, jahr: int) -> list[karten.Hervorhebung]:
    """'Germany=rot:Deutsches Reich; Poland=gold' → Liste (Namen werden gegen die Daten geprüft)."""
    liste = []
    for teil in (t.strip() for t in text.split(";")):
        if not teil:
            continue
        if "=" not in teil:
            raise karten.KartenFehler(f"Hervorhebung '{teil}': Format 'Gebiet=Farbe' oder 'Gebiet=Farbe:Beschriftung'.")
        name, rest = (t.strip() for t in teil.split("=", 1))
        farbe, _, beschriftung = rest.partition(":")
        liste.append(karten.Hervorhebung(karten.gebiet_pruefen(jahr, name), karten.farbe_lesen(farbe),
                                         beschriftung.strip()))
    return liste


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
                jahr = int(sz.quelle)
                karten.stichjahr_pruefen(jahr)
                hervorhebungen(o.get("hervorheben", ""), jahr)
                if "wechsel" in o:
                    jahr2 = int(o["wechsel"])
                    karten.stichjahr_pruefen(jahr2)
                    hervorhebungen(o.get("hervorheben_danach", o.get("hervorheben", "")), jahr2)
                for schl in ("wechsel_bei", "fahrt_von", "fahrt_bis"):
                    if schl in o:
                        zeit_lesen(o[schl])
                karten._ausschnitt_geo(o.get("ausschnitt", "Europa"), 9 / 16)
                if "fahrt" in o:
                    karten._ausschnitt_geo(o["fahrt"], 9 / 16)
                for name in orte_liste(o.get("orte", "")):
                    karten.ort_finden(name)
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
