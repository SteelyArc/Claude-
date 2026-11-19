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


# --- Karten im hellen Atlas-Stil (englische Beschriftung) ---------------------
# Dunkle Tinte mit hellem Papier-Lichthof: auf dem Smartphone gut lesbar,
# ohne dunkle Schatten.

TINTE = (52, 40, 30)
PAPIER = (246, 240, 225)


def _atlas_text(d: ImageDraw.ImageDraw, xy, text, font, fill, sperrung: float, halo: float,
                halo_farbe=PAPIER + (235,)) -> None:
    """Gesperrter Text mit Lichthof: erst alle Lichthöfe, dann die Schrift."""
    for durchgang in (0, 1):
        x, y = xy
        for z in text:
            if durchgang == 0:
                d.text((x, y), z, font=font, fill=halo_farbe, stroke_width=round(halo),
                       stroke_fill=halo_farbe, features=MERKMALE)
            else:
                d.text((x, y), z, font=font, fill=fill, features=MERKMALE)
            x += font.getlength(z, features=MERKMALE) + sperrung


def _weicher_hof(ebene: Image.Image, staerke: float) -> Image.Image:
    """Zusätzlicher, sehr weicher heller Hof unter dem Lichthof."""
    alpha = ebene.getchannel("A")
    hof = Image.new("RGBA", ebene.size, PAPIER + (0,))
    hof.putalpha(alpha.filter(ImageFilter.GaussianBlur(staerke)).point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(hof, ebene)


def jahreszahl(text: str, unterzeile: str, breite: int, hoehe: int) -> tuple[Image.Image, int, int]:
    """Große Jahreszahl (Atlas-Stil) mit feiner Linie und Unterzeile in Kapitälchen."""
    s = hoehe / 1920
    f_jahr = schrift(SERIF, round(150 * s))
    f_unter = schrift(SANS_FETT, round(26 * s))
    sperr = 10 * s
    w, h = breite, round(300 * s)
    ebene, d = _leinwand(w, h)
    tb = _sperrsatz_breite(text, f_jahr, sperr)
    _atlas_text(d, ((w - tb) / 2, round(20 * s)), text, f_jahr, TINTE + (255,), sperr, 7 * s)
    ly = round(205 * s)
    d.rectangle([w / 2 - 46 * s, ly, w / 2 + 46 * s, ly + max(2, round(2.5 * s))], fill=TINTE + (200,))
    if unterzeile:
        u = unterzeile.upper()
        ub = _sperrsatz_breite(u, f_unter, 4 * s)
        _atlas_text(d, ((w - ub) / 2, ly + round(18 * s)), u, f_unter, TINTE + (225,), 4 * s, 5 * s)
    return _weicher_hof(ebene, 14 * s), 0, round(hoehe * 0.06)


def kartentitel(text: str, breite: int, hoehe: int) -> tuple[Image.Image, int, int]:
    s = hoehe / 1920
    f = schrift(SERIF_KURSIV, round(64 * s))
    woerter, zeilen, aktuell = text.split(), [], ""
    for wort in woerter:
        probe = (aktuell + " " + wort).strip()
        if f.getlength(probe) > breite * 0.82 and aktuell:
            zeilen.append(aktuell)
            aktuell = wort
        else:
            aktuell = probe
    zeilen.append(aktuell)
    zeilen_h = round(72 * s)
    ebene, d = _leinwand(breite, zeilen_h * len(zeilen) + round(36 * s))
    for i, z in enumerate(zeilen):
        _atlas_text(d, ((breite - f.getlength(z, features=MERKMALE)) / 2, round(12 * s) + i * zeilen_h), z, f,
                    TINTE + (255,), 0, 6 * s)
    return _weicher_hof(ebene, 14 * s), 0, round(hoehe * 0.235)


def quellenzeile(text: str, breite: int, hoehe: int, y_anteil: float = 0.03) -> tuple[Image.Image, int, int]:
    """Sehr kleine, zurückhaltende Quellenangabe."""
    s = hoehe / 1920
    f = schrift(SANS, round(21 * s))
    ebene, d = _leinwand(breite, round(44 * s))
    tb = f.getlength(text)
    _atlas_text(d, ((breite - tb) / 2, round(8 * s)), text, f, TINTE + (190,), 0, 4 * s)
    return ebene, 0, round(hoehe * y_anteil)


def legende(alt: str, neu: str, breite: int, hoehe: int, farbe_alt=(140, 45, 35)) -> tuple[Image.Image, int, int]:
    """Kleine Legende: gestrichelt = frühere Grenze, durchgezogen = neue Grenze."""
    s = hoehe / 1920
    f = schrift(SANS_FETT, round(24 * s))
    sperr = 2.5 * s
    a_t, n_t = alt.upper(), neu.upper()
    muster = 46 * s
    luecke = 14 * s
    abstand = 44 * s
    b = muster + luecke + _sperrsatz_breite(a_t, f, sperr) + abstand + muster + luecke + _sperrsatz_breite(n_t, f, sperr)
    h = round(56 * s)
    ebene, d = _leinwand(breite, h)
    x = (breite - b) / 2
    ym = h / 2
    # Hintergrundband für Ruhe und Lesbarkeit
    d.rounded_rectangle([x - 22 * s, 4 * s, x + b + 22 * s, h - 4 * s], radius=round(10 * s), fill=PAPIER + (215,))
    strich = 0.0
    while strich < muster:
        d.line([(x + strich, ym), (x + min(strich + 9 * s, muster), ym)], fill=farbe_alt + (255,), width=max(2, round(3.5 * s)))
        strich += 15 * s
    x += muster + luecke
    asc = f.getmetrics()[0]
    _atlas_text(d, (x, ym - asc * 0.62), a_t, f, TINTE + (235,), sperr, 0, PAPIER + (0,))
    x += _sperrsatz_breite(a_t, f, sperr) + abstand
    d.line([(x, ym), (x + muster, ym)], fill=TINTE + (255,), width=max(3, round(4.5 * s)))
    x += muster + luecke
    _atlas_text(d, (x, ym - asc * 0.62), n_t, f, TINTE + (235,), sperr, 0, PAPIER + (0,))
    return ebene, 0, round(hoehe * 0.205)


def kartusche(jahr: str, unterzeile: str, titel: str, legende_alt_neu: tuple[str, str] | None,
              quelle: str, breite: int, hoehe: int, teil: str = "ganz",
              legendenplatz: bool = False) -> tuple[Image.Image, int, int]:
    """Gerahmter Titelkasten im Stil historischer Atlanten (vgl. 'EUROPA – Politische
    Übersicht'): Jahreszahl, Stand, Titel, ggf. Legende alte/neue Grenze, Quelle."""
    s = hoehe / 1920
    f_jahr = schrift(SERIF, round(118 * s))
    f_unter = schrift(SANS_FETT, round(23 * s))
    f_titel = schrift(SERIF_KURSIV, round(50 * s))
    f_leg = schrift(SANS_FETT, round(22 * s))
    f_quelle = schrift(SANS, round(18 * s))
    b = round(breite * 0.80)
    innen = round(34 * s)
    # Titel umbrechen
    zeilen, aktuell = [], ""
    for wort in titel.split():
        probe = (aktuell + " " + wort).strip()
        if f_titel.getlength(probe) > b - 2 * innen and aktuell:
            zeilen.append(aktuell)
            aktuell = wort
        else:
            aktuell = probe
    if aktuell:
        zeilen.append(aktuell)
    h = round(30 * s) + round(122 * s) + round(40 * s) + len(zeilen) * round(58 * s) \
        + (round(52 * s) if (legende_alt_neu or legendenplatz) else 0) + round(44 * s)
    ebene, d = _leinwand(b, h)
    # Kasten mit doppelter Rahmenlinie ('rahmen' = nur Kasten, 'inhalt' = nur Schrift)
    if teil in ("ganz", "rahmen"):
        d.rectangle([0, 0, b - 1, h - 1], fill=PAPIER + (238,))
        rand = max(2, round(2.2 * s))
        d.rectangle([round(6 * s), round(6 * s), b - 1 - round(6 * s), h - 1 - round(6 * s)], outline=TINTE + (230,),
                    width=rand)
        d.rectangle([round(12 * s), round(12 * s), b - 1 - round(12 * s), h - 1 - round(12 * s)],
                    outline=TINTE + (150,), width=max(1, round(1 * s)))
    if teil == "rahmen":
        return ebene, (breite - b) // 2, round(hoehe * 0.045)
    y = round(26 * s)
    sperr = 8 * s
    tb = _sperrsatz_breite(jahr, f_jahr, sperr)
    _zeichne_gesperrt(d, ((b - tb) / 2, y), jahr, f_jahr, TINTE + (255,), sperr)
    y += round(126 * s)
    u = unterzeile.upper()
    ub = _sperrsatz_breite(u, f_unter, 4 * s)
    _zeichne_gesperrt(d, ((b - ub) / 2, y), u, f_unter, TINTE + (210,), 4 * s)
    y += round(40 * s)
    for z in zeilen:
        d.text(((b - f_titel.getlength(z, features=MERKMALE)) / 2, y), z, font=f_titel, fill=TINTE + (255,),
               features=MERKMALE)
        y += round(58 * s)
    if legende_alt_neu:
        alt, neu = (t.upper() for t in legende_alt_neu)
        muster, luecke, abstand = 42 * s, 12 * s, 36 * s
        gesamt = 2 * (muster + luecke) + abstand + _sperrsatz_breite(alt, f_leg, 2 * s) + _sperrsatz_breite(neu, f_leg, 2 * s)
        x = (b - gesamt) / 2
        ym = y + round(20 * s)
        st = 0.0
        while st < muster:
            d.line([(x + st, ym), (x + min(st + 9 * s, muster), ym)], fill=(140, 45, 35, 255), width=max(2, round(3.5 * s)))
            st += 15 * s
        x += muster + luecke
        asc = f_leg.getmetrics()[0]
        _zeichne_gesperrt(d, (x, ym - asc * 0.6), alt, f_leg, TINTE + (235,), 2 * s)
        x += _sperrsatz_breite(alt, f_leg, 2 * s) + abstand
        d.line([(x, ym), (x + muster, ym)], fill=TINTE + (255,), width=max(3, round(5 * s)))
        x += muster + luecke
        _zeichne_gesperrt(d, (x, ym - asc * 0.6), neu, f_leg, TINTE + (235,), 2 * s)
        y += round(52 * s)
    elif legendenplatz:
        y += round(52 * s)
    qb = f_quelle.getlength(quelle)
    d.text(((b - qb) / 2, y + round(6 * s)), quelle, font=f_quelle, fill=TINTE + (165,))
    return ebene, (breite - b) // 2, round(hoehe * 0.045)


@lru_cache(maxsize=512)
def kartenbeschriftung(text: str, art: str, hoehe: int, farbe: tuple = TINTE) -> Image.Image:
    """Beschriftung auf der Karte: 'ort' (Serif), 'land' (gesperrte Versalien),
    'nachbar' (kleiner, zurückhaltend)."""
    s = hoehe / 1920
    if art in ("land", "nachbar"):
        f = schrift(SERIF, round((40 if art == "land" else 30) * s))
        sperr = (7 if art == "land" else 5) * s
        text = text.upper()
    else:
        f = schrift(SERIF, round(44 * s))
        sperr = 0.4 * s
    pad = round(16 * s)
    tb = _sperrsatz_breite(text, f, sperr)
    asc, desc = f.getmetrics()
    ebene, d = _leinwand(round(tb) + 2 * pad, asc + desc + 2 * pad)
    alpha = 255 if art != "nachbar" else 170
    _atlas_text(d, (pad, pad), text, f, tuple(farbe) + (alpha,), sperr, (5 if art != "nachbar" else 4) * s)
    return ebene
