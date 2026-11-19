"""Zeitliche Anordnung der Bilder.

Zwei Wege:
1. Ohne Datei ``zeitplan.txt``: Die Bilder werden gleichmäßig über die
   gesamte Erzählung verteilt (Reihenfolge = Dateiname).
2. Mit ``zeitplan.txt``: Für jedes Bild steht dort, ab welcher Sekunde der
   Sprecheraufnahme es erscheinen soll. Beispielzeile::

       0:12.5   03_karte_europa.jpg   eingepasst   zoom-rein

   Darstellung und Bewegung sind optional.

In Etappe 2 erzeugt das System diesen Zeitplan automatisch aus der
Spracherkennung, sodass die Bildwechsel an den Satzanfängen liegen.
"""

from __future__ import annotations

from pathlib import Path

from .bilder import BEWEGUNGEN, DARSTELLUNGEN, Szene


class ZeitplanFehler(ValueError):
    pass


def zeit_lesen(text: str) -> float:
    text = text.strip().replace(",", ".")
    try:
        if ":" in text:
            teile = text.split(":")
            sek = 0.0
            for t in teile:
                sek = sek * 60 + float(t)
            return sek
        return float(text)
    except ValueError:
        raise ZeitplanFehler(f"'{text}' ist keine gültige Zeitangabe (Beispiel: 1:23.5).") from None


def zeit_schreiben(sek: float) -> str:
    m, s = divmod(max(sek, 0.0), 60)
    return f"{int(m)}:{s:04.1f}"


def gleichmaessig(bilder: list[Path], sprechdauer: float) -> list[tuple[float, Path, str, str]]:
    n = len(bilder)
    return [(i * sprechdauer / n, p, "", "") for i, p in enumerate(bilder)]


def aus_datei(datei: Path, bilder: list[Path]) -> list[tuple[float, Path, str, str]]:
    nach_name = {p.name.lower(): p for p in bilder}
    eintraege = []
    for nr, zeile in enumerate(datei.read_text(encoding="utf-8-sig").splitlines(), 1):
        zeile = zeile.split("#", 1)[0].strip()
        if not zeile:
            continue
        teile = zeile.split()
        if len(teile) < 2:
            raise ZeitplanFehler(f"zeitplan.txt Zeile {nr}: Zeit und Bildname erforderlich.")
        zeit = zeit_lesen(teile[0])
        name = teile[1].lower()
        if name not in nach_name:
            raise ZeitplanFehler(f"zeitplan.txt Zeile {nr}: Bild '{teile[1]}' gibt es in diesem Projekt nicht.")
        darstellung = bewegung = ""
        for extra in (t.lower() for t in teile[2:]):
            if extra in DARSTELLUNGEN:
                darstellung = extra
            elif extra in BEWEGUNGEN:
                bewegung = extra
            else:
                moeglich = ", ".join(sorted(DARSTELLUNGEN | BEWEGUNGEN))
                raise ZeitplanFehler(f"zeitplan.txt Zeile {nr}: '{extra}' unbekannt. Möglich: {moeglich}.")
        eintraege.append((zeit, nach_name[name], darstellung, bewegung))

    if not eintraege:
        raise ZeitplanFehler("zeitplan.txt enthält keine Einträge.")
    eintraege.sort(key=lambda e: e[0])
    if eintraege[0][0] > 0.01:
        eintraege[0] = (0.0,) + eintraege[0][1:]  # das erste Bild steht immer am Anfang
    return eintraege


def szenen_bilden(eintraege, sprechdauer: float, vorlauf: float, nachlauf: float,
                  ueberblendung: float, bilddauer_min: float, bilddauer_max: float
                  ) -> tuple[list[Szene], float, list[str], list[str]]:
    """Legt fest, wann jedes Bild sichtbar ist (inklusive Überblendungen).

    Rückgabe: Szenen, Gesamtlänge, Hinweise, zu lange Standbilder.
    """
    warnungen: list[str] = []
    zu_lang: list[str] = []
    gesamt = vorlauf + sprechdauer + nachlauf
    szenen = [Szene(pfad=p, beginn=vorlauf + t if i else 0.0, darstellung=d, bewegung=b)
              for i, (t, p, d, b) in enumerate(eintraege)]

    for i, sz in enumerate(szenen):
        ende = szenen[i + 1].beginn if i + 1 < len(szenen) else gesamt
        dauer = ende - sz.beginn
        if dauer < 1.5 * ueberblendung:
            raise ZeitplanFehler(
                f"Bild '{sz.pfad.name}' wäre nur {dauer:.1f} s zu sehen – zu kurz für einen ruhigen Wechsel."
            )
        if dauer < bilddauer_min:
            warnungen.append(f"Bild '{sz.pfad.name}' steht nur {dauer:.1f} s (empfohlen ≥ {bilddauer_min:.0f} s).")
        # Das letzte Bild trägt den Ausklang (Nachlauf) mit – der zählt nicht.
        standzeit = dauer - (nachlauf if i == len(szenen) - 1 else 0.0)
        if standzeit > bilddauer_max:
            zu_lang.append(f"'{sz.pfad.name}' stünde {standzeit:.1f} s (höchstens {bilddauer_max:.0f} s)")

    halb = ueberblendung / 2
    for i, sz in enumerate(szenen):
        sz.sichtbar_von = 0.0 if i == 0 else sz.beginn - halb
        sz.sichtbar_bis = gesamt if i == len(szenen) - 1 else szenen[i + 1].beginn + halb
    return szenen, gesamt, warnungen, zu_lang
