"""Liest die Projekteinstellungen aus der Datei ``projekt.txt``.

Die Datei ist bewusst einfach gehalten: eine Einstellung pro Zeile im Format
``name: wert``. Alles hinter einem ``#`` ist ein Kommentar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class EinstellungsFehler(ValueError):
    pass


@dataclass
class Einstellungen:
    titel: str = ""
    # Bildlook: original | warm | schwarzweiss
    farbe: str = "original"
    # Filmkorn: aus | leicht
    filmkorn: str = "leicht"
    # Dezente Randabdunklung
    vignette: bool = True
    # Hintergrund hinter querformatigen Bildern: unschaerfe | schwarz
    hintergrund: str = "unschaerfe"
    # Dauer einer Überblendung in Sekunden
    ueberblendung: float = 1.2
    # Kamerabewegung: ruhig | normal | lebendig
    bewegung: str = "normal"
    # Stille vor dem ersten Wort und Nachlauf nach dem letzten Wort (Sekunden)
    vorlauf: float = 0.6
    nachlauf: float = 2.0
    # Mindestdauer pro Bild in Sekunden (Warnung, falls unterschritten)
    bilddauer_min: float = 4.0


_JA = {"ja", "an", "ein", "true", "1", "yes"}
_NEIN = {"nein", "aus", "false", "0", "no"}

_ERLAUBT = {
    "farbe": {"original", "warm", "schwarzweiss"},
    "filmkorn": {"aus", "leicht"},
    "hintergrund": {"unschaerfe", "schwarz"},
    "bewegung": {"ruhig", "normal", "lebendig"},
}


def _normalisieren(text: str) -> str:
    text = text.strip().lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("-", ""), (" ", "")):
        text = text.replace(alt, neu)
    return text


def laden(projektordner: Path) -> Einstellungen:
    e = Einstellungen()
    datei = projektordner / "projekt.txt"
    if not datei.exists():
        return e

    for nr, zeile in enumerate(datei.read_text(encoding="utf-8-sig").splitlines(), 1):
        zeile = zeile.split("#", 1)[0].strip()
        if not zeile:
            continue
        if ":" not in zeile:
            raise EinstellungsFehler(f"projekt.txt Zeile {nr}: Doppelpunkt fehlt ('{zeile}').")
        name, wert = (t.strip() for t in zeile.split(":", 1))
        name = _normalisieren(name)
        if not hasattr(e, name):
            raise EinstellungsFehler(f"projekt.txt Zeile {nr}: Unbekannte Einstellung '{name}'.")

        aktuell = getattr(e, name)
        if isinstance(aktuell, bool):
            w = _normalisieren(wert)
            if w in _JA:
                setattr(e, name, True)
            elif w in _NEIN:
                setattr(e, name, False)
            else:
                raise EinstellungsFehler(f"projekt.txt Zeile {nr}: '{name}' muss 'ja' oder 'nein' sein.")
        elif isinstance(aktuell, float):
            try:
                setattr(e, name, float(wert.replace(",", ".")))
            except ValueError:
                raise EinstellungsFehler(f"projekt.txt Zeile {nr}: '{name}' muss eine Zahl sein.") from None
        elif name in _ERLAUBT:
            w = _normalisieren(wert)
            if w not in _ERLAUBT[name]:
                moeglich = " | ".join(sorted(_ERLAUBT[name]))
                raise EinstellungsFehler(f"projekt.txt Zeile {nr}: '{name}' erlaubt nur: {moeglich}.")
            setattr(e, name, w)
        else:
            setattr(e, name, wert)

    if not 0.4 <= e.ueberblendung <= 3.0:
        raise EinstellungsFehler("projekt.txt: 'ueberblendung' muss zwischen 0.4 und 3.0 Sekunden liegen.")
    if e.vorlauf < 0 or e.nachlauf < 0.5:
        raise EinstellungsFehler("projekt.txt: 'vorlauf' muss ≥ 0 und 'nachlauf' ≥ 0.5 Sekunden sein.")
    return e
