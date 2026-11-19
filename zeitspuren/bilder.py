"""Bildaufbereitung und Kamerabewegung.

Grundsatz: Das historische Bild selbst wird nie inhaltlich verändert.
Erlaubt sind nur Ausschnitt, Zoom, Schwenk und (später, im Gesamtlook)
eine dezente Farbkorrektur. Querformatige Bilder werden vollständig
gezeigt; dahinter liegt optional eine stark unscharfe, abgedunkelte Kopie
als ruhiger Hintergrund – das Original im Vordergrund bleibt unangetastet.

Für ruckelfreie Bewegungen wird jedes Einzelbild per Subpixel-Transformation
aus einer hochaufgelösten „Bildplatte“ berechnet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

Image.MAX_IMAGE_PIXELS = 400_000_000  # große Archivscans zulassen

BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}

# Die Bildplatte ist um diesen Faktor größer als das Ausgabebild, damit beim
# Hineinzoomen keine Schärfe verloren geht.
PLATTE_FAKTOR = 1.12

# Bewegungsgeschwindigkeit je Stil: (Zoom pro Sekunde, Schwenk pro Sekunde
# als Anteil der Bildbreite)
TEMPO = {
    "ruhig": (0.005, 0.012),
    "normal": (0.008, 0.018),
    "lebendig": (0.011, 0.025),
}
ZOOM_MIN, ZOOM_MAX = 0.025, 0.12

BEWEGUNGEN = {
    "zoom-rein", "zoom-raus", "schwenk-links", "schwenk-rechts",
    "schwenk-hoch", "schwenk-runter", "still",
}
DARSTELLUNGEN = {"ganz", "eingepasst"}


class BildFehler(RuntimeError):
    pass


def _natuerlich(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def finden(projektordner: Path) -> list[Path]:
    # Bilder dürfen im Unterordner 'bilder' oder direkt im Projektordner liegen.
    ordner = [projektordner / "bilder", projektordner]
    dateien = [
        p for o in ordner if o.is_dir() for p in o.iterdir()
        if p.is_file() and p.suffix.lower() in BILD_ENDUNGEN and not p.name.startswith(".")
    ]
    if not dateien:
        raise BildFehler(f"Im Projekt '{projektordner.name}' wurden keine Bilder gefunden.")
    doppelt = {p.name.lower() for p in dateien if sum(q.name.lower() == p.name.lower() for q in dateien) > 1}
    if doppelt:
        raise BildFehler(f"Bildnamen doppelt vorhanden: {', '.join(sorted(doppelt))}.")
    return sorted(dateien, key=lambda p: _natuerlich(p.name))


def oeffnen(pfad: Path) -> Image.Image:
    try:
        bild = Image.open(pfad)
        bild = ImageOps.exif_transpose(bild)  # Handyfotos richtig drehen
    except Exception as fehler:  # noqa: BLE001
        raise BildFehler(f"Bild '{pfad.name}' kann nicht geöffnet werden: {fehler}") from None

    if bild.mode in ("RGBA", "LA", "PA") or (bild.mode == "P" and "transparency" in bild.info):
        bild = bild.convert("RGBA")
        hinten = Image.new("RGBA", bild.size, (0, 0, 0, 255))
        bild = Image.alpha_composite(hinten, bild)
    if bild.mode in ("I;16", "I;16B", "I;16L", "I"):
        bild = bild.point(lambda v: v * (1 / 256)).convert("L")
    return bild.convert("RGB")


@dataclass
class Kamerafahrt:
    """Ausschnitt-Rechtecke (Mittelpunkt x, y und Breite) in Plattenkoordinaten."""

    start: tuple[float, float, float]
    ende: tuple[float, float, float]

    def an(self, p: float) -> tuple[float, float, float]:
        return tuple(a + (b - a) * p for a, b in zip(self.start, self.ende))


@dataclass
class Szene:
    pfad: Path
    beginn: float  # Sekunde im fertigen Video, ab der das Bild (voll) zu sehen ist
    darstellung: str = ""  # ganz | eingepasst | "" (automatisch)
    bewegung: str = ""  # siehe BEWEGUNGEN, "" = automatisch
    # wird beim Vorbereiten gefüllt:
    platte: Image.Image | None = field(default=None, repr=False)
    fahrt: Kamerafahrt | None = None
    sichtbar_von: float = 0.0
    sichtbar_bis: float = 0.0
    hinweis: str = ""


def _darstellung_waehlen(breite: int, hoehe: int, ziel_seitenv: float) -> str:
    # Bilder, die nahe am Hochformat 9:16 liegen (bis etwa 3:4), füllen das
    # ganze Bild; der verlorene Rand ist dann klein. Alles Breitere wird
    # vollständig gezeigt.
    return "ganz" if breite / hoehe <= ziel_seitenv * 1.4 else "eingepasst"


def platte_bauen(bild: Image.Image, darstellung: str, aus_b: int, aus_h: int, hintergrund: str) -> Image.Image:
    pb, ph = round(aus_b * PLATTE_FAKTOR), round(aus_h * PLATTE_FAKTOR)
    b, h = bild.size

    if darstellung == "ganz":
        k = max(pb / b, ph / h)
        return bild.resize((max(pb, round(b * k)), max(ph, round(h * k))), Image.LANCZOS)

    # eingepasst: vollständiges Bild auf ruhigem Hintergrund
    if hintergrund == "schwarz":
        flaeche = Image.new("RGB", (pb, ph), (8, 8, 8))
    else:
        k = max(pb / b, ph / h) / 10  # klein rechnen = schnell und weich
        klein = bild.resize((max(1, round(b * k)), max(1, round(h * k))), Image.BILINEAR)
        klein = klein.filter(ImageFilter.GaussianBlur(radius=max(2.0, klein.width / 40)))
        flaeche = ImageOps.fit(klein, (pb // 4, ph // 4), Image.BILINEAR).resize((pb, ph), Image.BICUBIC)
        flaeche = flaeche.filter(ImageFilter.GaussianBlur(radius=6))
        flaeche = ImageEnhance.Color(flaeche).enhance(0.6)
        flaeche = ImageEnhance.Brightness(flaeche).enhance(0.38)

    k = min(pb / b, ph / h)
    vorne = bild.resize((round(b * k), round(h * k)), Image.LANCZOS)
    flaeche.paste(vorne, ((pb - vorne.width) // 2, (ph - vorne.height) // 2))
    return flaeche


def fahrt_planen(platte: Image.Image, bewegung: str, dauer: float, tempo: str,
                 aus_b: int, aus_h: int) -> Kamerafahrt:
    pb, ph = platte.size
    seitenv = aus_b / aus_h
    # größter Ausschnitt im Zielformat, der in die Platte passt
    basis_b = min(pb, ph * seitenv)
    mx, my = pb / 2, ph / 2
    zoom_rate, schwenk_rate = TEMPO[tempo]
    zoom = min(max(zoom_rate * dauer, ZOOM_MIN), ZOOM_MAX)

    if bewegung == "still":
        return Kamerafahrt((mx, my, basis_b), (mx, my, basis_b))
    if bewegung == "zoom-rein":
        return Kamerafahrt((mx, my, basis_b), (mx, my, basis_b / (1 + zoom)))
    if bewegung == "zoom-raus":
        return Kamerafahrt((mx, my, basis_b / (1 + zoom)), (mx, my, basis_b))

    # Schwenks: Ausschnitt fährt über das Bild. Ist kaum Platz vorhanden,
    # wird leicht hineingezoomt, um Spielraum zu gewinnen.
    waagrecht = bewegung in ("schwenk-links", "schwenk-rechts")
    breite = basis_b
    for _ in range(2):
        hoehe = breite / seitenv
        platz = (pb - breite) if waagrecht else (ph - hoehe)
        wunsch = schwenk_rate * dauer * breite
        if platz >= min(wunsch, 0.04 * breite):
            break
        breite = basis_b / (1 + zoom)
    hoehe = breite / seitenv
    platz = (pb - breite) if waagrecht else (ph - hoehe)
    weg = max(0.0, min(platz, schwenk_rate * dauer * breite))
    if bewegung in ("schwenk-rechts", "schwenk-runter"):
        a, b_ = -weg / 2, weg / 2
    else:
        a, b_ = weg / 2, -weg / 2
    if waagrecht:
        return Kamerafahrt((mx + a, my, breite), (mx + b_, my, breite))
    return Kamerafahrt((mx, my + a, breite), (mx, my + b_, breite))


def bewegung_automatisch(index: int, pfad: Path, platte: Image.Image, darstellung: str,
                         aus_b: int, aus_h: int) -> str:
    name = pfad.stem.lower()
    if any(w in name for w in ("karte", "map", "plan")):
        return "zoom-rein"  # Karten: langsam auf das Geschehen zu
    pb, ph = platte.size
    seitenv = aus_b / aus_h
    if darstellung == "ganz":
        basis_b = min(pb, ph * seitenv)
        if (pb - basis_b) / basis_b > 0.15:
            return "schwenk-rechts" if index % 2 == 0 else "schwenk-links"
        if (ph - basis_b / seitenv) / (basis_b / seitenv) > 0.15:
            return "schwenk-runter"
    return "zoom-rein" if index % 2 == 0 else "zoom-raus"


def einzelbild(szene: Szene, t: float, aus_b: int, aus_h: int) -> Image.Image:
    """Berechnet den sichtbaren Ausschnitt einer Szene zum Zeitpunkt t."""
    spanne = max(szene.sichtbar_bis - szene.sichtbar_von, 1e-6)
    p = min(max((t - szene.sichtbar_von) / spanne, 0.0), 1.0)
    cx, cy, breite = szene.fahrt.an(p)
    hoehe = breite * aus_h / aus_b
    s = breite / aus_b
    return szene.platte.transform(
        (aus_b, aus_h), Image.AFFINE,
        (s, 0.0, cx - breite / 2, 0.0, s, cy - hoehe / 2),
        resample=Image.BICUBIC,
    )
