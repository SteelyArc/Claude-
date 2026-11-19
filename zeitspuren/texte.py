"""Elegante Texteinblendungen im Stil hochwertiger TV-Dokumentationen.

Alle Größen sind relativ zur Bildhöhe angegeben, damit Vorschau und
Endfassung identisch aussehen. Die Einblendungen liegen im oberen Bilddrittel,
weil TikTok unten und rechts eigene Bedienelemente einblendet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCHRIFTEN = Path(__file__).resolve().parent.parent / "daten" / "schriften"

SERIF = "CormorantGaramond-SemiBold.ttf"
SERIF_MITTEL = "CormorantGaramond-Medium.ttf"
SERIF_KURSIV = "CormorantGaramond-MediumItalic.ttf"
SANS = "SourceSans3-Regular.ttf"
SANS_FETT = "SourceSans3-SemiBold.ttf"

PAPIERWEISS = (243, 236, 222)
GOLD = (201, 168, 92)

# Sicherer Bereich: linker Rand und Höhe der Einblendungen (Anteil der Bildmaße)
RAND_X = 0.075
OBEN_Y = 0.105


@lru_cache(maxsize=64)
def schrift(datei: str, groesse: int) -> ImageFont.FreeTypeFont:
    pfad = SCHRIFTEN / datei
    try:
        return ImageFont.truetype(str(pfad), groesse)
    except OSError:
        ersatz = "DejaVuSerif.ttf" if "Cormorant" in datei else "DejaVuSans.ttf"
        return ImageFont.truetype(ersatz, groesse)


def _sperrsatz_breite(text: str, font, sperrung: float) -> float:
    if not text:
        return 0.0
    return sum(font.getlength(z, features=MERKMALE) for z in text) + sperrung * (len(text) - 1)


MERKMALE = ["lnum", "kern"]  # Versalziffern: 1938 statt Mediävalziffern


def _zeichne_gesperrt(d: ImageDraw.ImageDraw, xy, text, font, fill, sperrung: float) -> None:
    x, y = xy
    for z in text:
        d.text((x, y), z, font=font, fill=fill, features=MERKMALE)
        x += font.getlength(z, features=MERKMALE) + sperrung


def _mit_schatten(ebene: Image.Image, staerke: float) -> Image.Image:
    """Weicher dunkler Schatten unter Text – für Lesbarkeit auf hellen Fotos."""
    alpha = ebene.getchannel("A")
    schatten = Image.new("RGBA", ebene.size, (0, 0, 0, 0))
    schatten.putalpha(alpha.filter(ImageFilter.GaussianBlur(staerke)).point(lambda v: int(v * 0.75)))
    return Image.alpha_composite(schatten, ebene)


@dataclass
class Einblendung:
    """Ein vorgerendertes, transparentes Textbild mit Zeitsteuerung."""

    bild: Image.Image  # RGBA
    x: int
    y: int
    von: float  # Videozeit in Sekunden
    bis: float
    ein: float = 0.9  # Einblenddauer
    aus: float = 0.7  # Ausblenddauer

    def staerke(self, t: float) -> float:
        if t <= self.von or t >= self.bis:
            return 0.0
        a = min(1.0, (t - self.von) / self.ein, (self.bis - t) / self.aus)
        return 0.5 - 0.5 * math.cos(math.pi * max(0.0, a))

    def auftragen(self, ziel: Image.Image, t: float) -> None:
        a = self.staerke(t)
        if a <= 0.003:
            return
        bild = self.bild
        if a < 0.997:
            bild = bild.copy()
            bild.putalpha(bild.getchannel("A").point(lambda v: int(v * a)))
        ziel.paste(bild, (self.x, self.y), bild)


def _leinwand(b: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    ebene = Image.new("RGBA", (b, h), (0, 0, 0, 0))
    return ebene, ImageDraw.Draw(ebene)


def ortsmarke(ort: str, zeit: str, quelle: str, breite: int, hoehe: int) -> tuple[Image.Image, int, int]:
    """Bauchbinde oben links: goldene Linie, ORT in Kapitälchen, Zeit kursiv,
    darunter klein die Bildquelle."""
    s = hoehe / 1920
    f_ort = schrift(SANS_FETT, round(34 * s))
    f_zeit = schrift(SERIF_KURSIV, round(54 * s))
    f_quelle = schrift(SANS, round(22 * s))
    sperr = 7 * s
    ort_t = ort.upper()

    pad = round(24 * s)
    linie_b = round(64 * s)
    w = round(breite * (1 - 2 * RAND_X)) + 2 * pad
    zeilen_h = round(16 * s) + (round(46 * s) if ort else 0) + (round(66 * s) if zeit else 0) \
        + (round(34 * s) if quelle else 0)
    ebene, d = _leinwand(w, zeilen_h + 2 * pad)

    y = pad
    d.rectangle([pad, y, pad + linie_b, y + max(2, round(3 * s))], fill=GOLD + (255,))
    y += round(16 * s)
    if ort:
        _zeichne_gesperrt(d, (pad, y), ort_t, f_ort, PAPIERWEISS + (255,), sperr)
        y += round(46 * s)
    if zeit:
        d.text((pad, y - round(6 * s)), zeit, font=f_zeit, fill=PAPIERWEISS + (255,), features=MERKMALE)
        y += round(66 * s)
    if quelle:
        d.text((pad, y), quelle, font=f_quelle, fill=PAPIERWEISS + (175,))

    ebene = _mit_schatten(ebene, 7 * s)
    return ebene, round(breite * RAND_X) - pad, round(hoehe * OBEN_Y) - pad


def jahreszahl(text: str, unterzeile: str, breite: int, hoehe: int) -> tuple[Image.Image, int, int]:
    """Große, zentrierte Jahreszahl mit feiner Linie und Unterzeile (für Karten)."""
    s = hoehe / 1920
    f_jahr = schrift(SERIF, round(150 * s))
    f_unter = schrift(SANS, round(25 * s))
    sperr = 10 * s
    w, h = breite, round(300 * s)
    ebene, d = _leinwand(w, h)
    tb = _sperrsatz_breite(text, f_jahr, sperr)
    _zeichne_gesperrt(d, ((w - tb) / 2, round(20 * s)), text, f_jahr, PAPIERWEISS + (255,), sperr)
    ly = round(205 * s)
    d.rectangle([w / 2 - 40 * s, ly, w / 2 + 40 * s, ly + max(2, round(3 * s))], fill=GOLD + (255,))
    if unterzeile:
        ub = _sperrsatz_breite(unterzeile.upper(), f_unter, 4 * s)
        _zeichne_gesperrt(d, ((w - ub) / 2, ly + round(20 * s)), unterzeile.upper(), f_unter,
                          PAPIERWEISS + (190,), 4 * s)
    ebene = _mit_schatten(ebene, 9 * s)
    return ebene, 0, round(hoehe * 0.075)


def kartentitel(text: str, breite: int, hoehe: int) -> tuple[Image.Image, int, int]:
    s = hoehe / 1920
    f = schrift(SERIF_MITTEL, round(62 * s))
    w = breite
    # Zeilenumbruch bei langen Titeln
    woerter, zeilen, aktuell = text.split(), [], ""
    for wort in woerter:
        probe = (aktuell + " " + wort).strip()
        if f.getlength(probe) > breite * 0.84 and aktuell:
            zeilen.append(aktuell)
            aktuell = wort
        else:
            aktuell = probe
    zeilen.append(aktuell)
    zeilen_h = round(70 * s)
    ebene, d = _leinwand(w, zeilen_h * len(zeilen) + round(30 * s))
    for i, z in enumerate(zeilen):
        d.text(((w - f.getlength(z)) / 2, round(10 * s) + i * zeilen_h), z, font=f, fill=PAPIERWEISS + (255,))
    ebene = _mit_schatten(ebene, 8 * s)
    return ebene, 0, round(hoehe * 0.245)


def quellenzeile(text: str, breite: int, hoehe: int, y_anteil: float = 0.035) -> tuple[Image.Image, int, int]:
    """Sehr kleine, zurückhaltende Quellenangabe (z. B. für Kartendaten)."""
    s = hoehe / 1920
    f = schrift(SANS, round(20 * s))
    w, h = breite, round(40 * s)
    ebene, d = _leinwand(w, h)
    tb = f.getlength(text)
    d.text(((w - tb) / 2, round(8 * s)), text, font=f, fill=PAPIERWEISS + (150,))
    ebene = _mit_schatten(ebene, 4 * s)
    return ebene, 0, round(hoehe * y_anteil)


@lru_cache(maxsize=512)
def kartenbeschriftung(text: str, art: str, hoehe: int, farbe: tuple = PAPIERWEISS) -> Image.Image:
    """Beschriftung auf der Karte: 'ort' (Serif) oder 'land' (gesperrte Versalien)."""
    s = hoehe / 1920
    if art == "land":
        f = schrift(SANS_FETT, round(30 * s))
        sperr = 6 * s
        text = text.upper()
    else:
        f = schrift(SERIF, round(46 * s))
        sperr = 0.5 * s
    pad = round(14 * s)
    tb = _sperrsatz_breite(text, f, sperr)
    asc, desc = f.getmetrics()
    ebene, d = _leinwand(round(tb) + 2 * pad, asc + desc + 2 * pad)
    _zeichne_gesperrt(d, (pad, pad), text, f, tuple(farbe) + (255,), sperr)
    return _mit_schatten(ebene, 5 * s)
