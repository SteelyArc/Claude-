"""Animierte historische Karten.

Historische Genauigkeit:
- Grenzen stammen ausschließlich aus dem Datensatz „historical-basemaps“
  (A. Ourednik, GPL-3.0) in einem fest verankerten Versionsstand. Es gibt ihn
  für bestimmte Stichjahre (z. B. 1914, 1920, 1938, 1945). Zwischenstände
  werden NICHT erfunden: Ein Grenzwechsel blendet von einem Stichjahr zum
  nächsten über und die Karte nennt immer den Stand, den sie zeigt.
- Grenzen, die der Datensatz selbst als „ungefähr“ einstuft
  (BORDERPRECISION = 1), werden zurückhaltender gezeichnet.
- Küsten, Flüsse, Seen und Ortskoordinaten: Natural Earth (gemeinfrei).

Technik: Geometrien werden einmal pro Szene in eine flächentreue
Azimutalprojektion (Lambert) umgerechnet und als Cairo-Pfade vorbereitet;
jedes Einzelbild setzt nur noch Kamera (Mittelpunkt, Maßstab) und zeichnet –
kantengeglättet und subpixelgenau.
"""

from __future__ import annotations

import csv
import difflib
import json
import math
import threading
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import cairo
from PIL import Image

from . import texte

DATEN = Path(__file__).resolve().parent.parent / "daten" / "karten"
HIST_ORDNER = DATEN / "historisch"

# Fest verankerter Versionsstand der Datenquellen (Reproduzierbarkeit)
HIST_VERSION = "4b5039e50d8d2464b065bd76ad6086cd4597108d"
HIST_URL = "https://raw.githubusercontent.com/aourednik/historical-basemaps/{v}/geojson/world_{j}.geojson"

STICHJAHRE = [
    -123000, -10000, -8000, -5000, -4000, -3000, -2000, -1500, -1000, -700, -500, -400, -323, -300,
    -200, -100, -1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1279, 1300, 1400,
    1492, 1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1878, 1880, 1900, 1914, 1920, 1930,
    1938, 1945, 1960, 1994, 2000, 2010,
]

ERDRADIUS = 6371.0

# --- Farbwelt (dunkler, edler Dokumentarstil) -------------------------------
MEER_OBEN = (0.067, 0.106, 0.133)
MEER_UNTEN = (0.098, 0.153, 0.188)
LAND = (0.205, 0.207, 0.180)
GEBIETSTOENE = [
    (0.290, 0.278, 0.239), (0.318, 0.302, 0.259), (0.275, 0.267, 0.231),
    (0.302, 0.290, 0.247), (0.337, 0.318, 0.282), (0.282, 0.275, 0.243),
]
GRENZE = (0.84, 0.80, 0.70)
FLUSS = (0.17, 0.28, 0.35)
ORTE_AB_KM = 2600  # Ortsnamen erst unterhalb dieser sichtbaren Kartenbreite

FARBEN = {
    "rot": (0.69, 0.20, 0.17),
    "dunkelrot": (0.50, 0.11, 0.10),
    "gold": (0.80, 0.63, 0.25),
    "gelb": (0.85, 0.74, 0.32),
    "blau": (0.25, 0.45, 0.70),
    "hellblau": (0.45, 0.65, 0.85),
    "gruen": (0.33, 0.52, 0.32),
    "grün": (0.33, 0.52, 0.32),
    "orange": (0.82, 0.47, 0.18),
    "violett": (0.45, 0.30, 0.58),
    "grau": (0.55, 0.55, 0.52),
    "weiss": (0.90, 0.88, 0.82),
    "weiß": (0.90, 0.88, 0.82),
}

# Regionen: (Länge min, Breite min, Länge max, Breite max)
REGIONEN = {
    "welt": (-170, -55, 180, 75),
    "europa": (-11, 35, 40, 70),
    "mitteleuropa": (3, 44.5, 25, 56),
    "westeuropa": (-10, 42, 15, 59),
    "osteuropa": (14, 42, 45, 62),
    "nordeuropa": (-5, 54, 32, 71.5),
    "skandinavien": (4, 54, 32, 71.5),
    "suedeuropa": (-10, 35, 30, 47),
    "südeuropa": (-10, 35, 30, 47),
    "balkan": (13, 39, 30, 47.5),
    "mittelmeer": (-6, 30, 36, 46.5),
    "ostsee": (9, 53, 31, 66),
    "deutschland": (5.5, 47, 15.5, 55.2),
    "oesterreich": (9.5, 46.3, 17.2, 49.1),
    "österreich": (9.5, 46.3, 17.2, 49.1),
    "schweiz": (5.9, 45.8, 10.5, 47.9),
    "frankreich": (-5, 42, 8.5, 51.2),
    "italien": (6.5, 36.5, 18.6, 47.1),
    "polen": (14, 49, 24.2, 55),
    "benelux": (2.5, 49.4, 7.3, 53.6),
    "britische inseln": (-11, 49.8, 2, 61),
    "grossbritannien": (-8, 49.8, 2, 59),
    "großbritannien": (-8, 49.8, 2, 59),
    "iberische halbinsel": (-9.6, 35.9, 3.4, 43.9),
    "spanien": (-9.6, 35.9, 3.4, 43.9),
    "ukraine": (22, 44, 40.5, 52.5),
    "russland": (27, 41, 60, 70),
    "nordafrika": (-17, 15, 35, 38),
    "afrika": (-20, -36, 52, 38),
    "naher osten": (25, 12, 63, 42),
    "nahost": (25, 12, 63, 42),
    "asien": (25, -10, 150, 60),
    "ostasien": (95, 15, 150, 50),
    "nordamerika": (-170, 10, -50, 75),
    "usa": (-125, 24, -66, 50),
    "suedamerika": (-82, -56, -34, 13),
    "südamerika": (-82, -56, -34, 13),
    "pazifik": (100, -45, 200, 45),
}


class KartenFehler(ValueError):
    pass


# --- Daten laden -------------------------------------------------------------

_ladesperre = threading.Lock()


def stichjahr_pruefen(jahr: int) -> None:
    if jahr not in STICHJAHRE:
        naechste = sorted(STICHJAHRE, key=lambda j: abs(j - jahr))[:3]
        raise KartenFehler(
            f"Für das Jahr {jahr} gibt es keinen geprüften Grenzdatensatz. Verfügbare Stichjahre in der Nähe: "
            f"{', '.join(map(str, sorted(naechste)))}. (Zwischenstände werden nicht erfunden.)")


def _datei_hist(jahr: int) -> Path:
    name = f"bc{-jahr}" if jahr < 0 else str(jahr)
    return HIST_ORDNER / f"world_{name}.geojson"


@lru_cache(maxsize=16)
def historisch(jahr: int) -> list[dict]:
    stichjahr_pruefen(jahr)
    datei = _datei_hist(jahr)
    with _ladesperre:
        if not datei.exists():
            HIST_ORDNER.mkdir(parents=True, exist_ok=True)
            name = datei.stem.replace("world_", "")
            url = HIST_URL.format(v=HIST_VERSION, j=name)
            try:
                with urllib.request.urlopen(url, timeout=60) as antwort:
                    inhalt = antwort.read()
            except Exception as fehler:  # noqa: BLE001
                raise KartenFehler(f"Kartendaten für {jahr} konnten nicht geladen werden: {fehler}") from None
            datei.write_bytes(inhalt)
    roh = json.loads(datei.read_text(encoding="utf-8"))
    gebiete = []
    for f in roh["features"]:
        p = f.get("properties") or {}
        name = p.get("NAME")
        if not name or not f.get("geometry"):
            continue
        gebiete.append({
            "name": name,
            "genauigkeit": int(p.get("BORDERPRECISION") or 1),
            "teil_von": p.get("PARTOF") or p.get("SUBJECTO") or "",
            "polygone": _polygone(f["geometry"]),
        })
    return gebiete


def _polygone(geometrie: dict) -> list[list[list[tuple[float, float]]]]:
    if geometrie["type"] == "Polygon":
        return [geometrie["coordinates"]]
    if geometrie["type"] == "MultiPolygon":
        return geometrie["coordinates"]
    return []


@lru_cache(maxsize=4)
def natural_earth(art: str) -> list:
    datei = {"land": "ne_50m_land.geojson", "fluesse": "ne_50m_rivers.geojson",
             "seen": "ne_50m_lakes.geojson"}[art]
    roh = json.loads((DATEN / datei).read_text(encoding="utf-8"))
    teile = []
    for f in roh["features"]:
        g = f.get("geometry")
        if not g:
            continue
        if art == "fluesse":
            rang = (f.get("properties") or {}).get("scalerank", 0)
            linien = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
            teile.extend((rang, l) for l in linien)
        else:
            teile.extend(_polygone(g))
    return teile


def _schluessel(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return "".join(z for z in text if z.isalnum())


@lru_cache(maxsize=1)
def _orte() -> dict[str, tuple[str, float, float]]:
    """Ortsverzeichnis: Schlüssel → (Anzeigename deutsch, Breite, Länge). Größte Orte haben Vorrang."""
    verzeichnis: dict[str, tuple[str, float, float]] = {}
    with open(DATEN / "orte.csv", encoding="utf-8") as fh:
        for z in csv.DictReader(fh):
            eintrag = (z["name_de"] or z["name"], float(z["breite"]), float(z["laenge"]))
            for n in (z["name_de"], z["name"], z["name_ascii"]):
                if n and _schluessel(n) not in verzeichnis:
                    verzeichnis[_schluessel(n)] = eintrag
    return verzeichnis


def ort_finden(angabe: str) -> tuple[str, float, float]:
    """'Danzig', 'Danzig@54.35,18.65' oder '54.35,18.65' → (Name, Breite, Länge)."""
    angabe = angabe.strip()
    if "@" in angabe:
        name, koord = angabe.split("@", 1)
        b, l = (float(v) for v in koord.replace(" ", "").split(","))
        return name.strip(), b, l
    teile = angabe.replace(" ", "").split(",")
    if len(teile) == 2:
        try:
            return "", float(teile[0]), float(teile[1])
        except ValueError:
            pass
    treffer = _orte().get(_schluessel(angabe))
    if not treffer:
        vorschlaege = difflib.get_close_matches(_schluessel(angabe), list(_orte()), n=3, cutoff=0.75)
        tipp = f" Meinten Sie: {', '.join(_orte()[v][0] for v in vorschlaege)}?" if vorschlaege else ""
        raise KartenFehler(f"Ort '{angabe}' nicht im Ortsverzeichnis.{tipp} "
                           f"Alternativ Koordinaten angeben, z. B. '{angabe}@52.52,13.40'.")
    # Anzeigename so, wie im Drehbuch geschrieben (z. B. historischer Name)
    return angabe, treffer[1], treffer[2]


def gebiet_namen(jahr: int) -> list[str]:
    return sorted({g["name"] for g in historisch(jahr)})


def gebiet_pruefen(jahr: int, name: str) -> str:
    namen = gebiet_namen(jahr)
    if name in namen:
        return name
    klein = {n.lower(): n for n in namen}
    if name.lower() in klein:
        return klein[name.lower()]
    vorschlaege = difflib.get_close_matches(name, namen, n=4, cutoff=0.5)
    tipp = f" Ähnliche Namen im Datensatz {jahr}: {', '.join(vorschlaege)}." if vorschlaege else ""
    raise KartenFehler(f"Gebiet '{name}' gibt es im Kartenstand {jahr} nicht.{tipp}")


# --- Projektion ---------------------------------------------------------------

@dataclass(frozen=True)
class Projektion:
    lon0: float
    lat0: float

    def __call__(self, lon: float, lat: float) -> tuple[float, float] | None:
        """Lambert flächentreu azimutal, Ergebnis in km. None nahe dem Gegenpunkt."""
        l0, p0 = math.radians(self.lon0), math.radians(self.lat0)
        l, p = math.radians(lon), math.radians(lat)
        cosc = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0)
        if cosc < -0.97:
            return None
        k = math.sqrt(2 / (1 + cosc))
        x = ERDRADIUS * k * math.cos(p) * math.sin(l - l0)
        y = ERDRADIUS * k * (math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0))
        return x, y


def _ausschnitt_geo(angabe: str, seitenv: float) -> tuple[float, float, float]:
    """Region oder 'Ort [Breite_km]' → (Länge, Breite, sichtbare Breite in km)."""
    angabe = angabe.strip()
    schl = angabe.lower()
    if schl in REGIONEN:
        lo1, la1, lo2, la2 = REGIONEN[schl]
        lon0, lat0 = (lo1 + lo2) / 2, (la1 + la2) / 2
        proj = Projektion(lon0, lat0)
        xs, ys = [], []
        for i in range(21):
            for j in range(21):
                pt = proj(lo1 + (lo2 - lo1) * i / 20, la1 + (la2 - la1) * j / 20)
                if pt:
                    xs.append(pt[0])
                    ys.append(pt[1])
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        # Mittelpunkt zurückrechnen (näherungsweise genügt hier)
        lat_c = lat0 + cy / 111.2
        lon_c = lon0 + cx / (111.2 * max(0.2, math.cos(math.radians(lat_c))))
        return lon_c, lat_c, max(w, h * seitenv) * 1.06
    teile = angabe.rsplit(" ", 1)
    breite_km = 600.0
    if len(teile) == 2:
        try:
            breite_km = float(teile[1].lower().replace("km", ""))
            angabe = teile[0]
        except ValueError:
            pass
    _, lat, lon = ort_finden(angabe)
    return lon, lat, breite_km


# --- Szene --------------------------------------------------------------------

@dataclass
class Hervorhebung:
    name: str
    farbe: tuple[float, float, float]
    beschriftung: str = ""


@dataclass
class Kartenstand:
    jahr: int
    hervorhebungen: list[Hervorhebung] = field(default_factory=list)


def _weich(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)  # „smootherstep“: sanft anfahren und bremsen


class Kartenszene:
    """Rendert eine animierte Karte für das Zeitintervall [von, bis] (Videozeit)."""

    def __init__(self, staende: list[Kartenstand], wechsel_bei: float | None,
                 ausschnitt: str, fahrt_ziel: str | None, fahrt_von: float | None, fahrt_bis: float | None,
                 orte: list[str], titel: str, jahr_text: str | None,
                 von: float, bis: float, breite: int, hoehe: int):
        self.staende = staende
        self.von, self.bis = von, bis
        self.breite, self.hoehe = breite, hoehe
        self.titel = titel
        self.jahr_text = jahr_text
        seitenv = breite / hoehe

        start = _ausschnitt_geo(ausschnitt, seitenv)
        ziel = _ausschnitt_geo(fahrt_ziel, seitenv) if fahrt_ziel else None

        # Projektionsmitte zwischen Start und Ziel – bleibt in der Szene fest
        if ziel:
            lon0, lat0 = (start[0] + ziel[0]) / 2, (start[1] + ziel[1]) / 2
        else:
            lon0, lat0 = start[0], start[1]
        self.proj = Projektion(lon0, lat0)
        sx, sy = self.proj(start[0], start[1])
        self.kamera_start = (sx, sy, start[2])
        if ziel:
            zx, zy = self.proj(ziel[0], ziel[1])
            self.kamera_ziel = (zx, zy, ziel[2])
        else:  # ohne Fahrt: ganz langsames Hineinzoomen
            self.kamera_ziel = (sx, sy, start[2] / 1.06)
        dauer = bis - von
        self.fahrt_von = fahrt_von if fahrt_von is not None else von + 0.12 * dauer
        self.fahrt_bis = fahrt_bis if fahrt_bis is not None else bis - 0.12 * dauer
        if not ziel:
            self.fahrt_von, self.fahrt_bis = von, bis
        if self.fahrt_bis - self.fahrt_von < 1.0:
            self.fahrt_bis = self.fahrt_von + 1.0

        self.wechsel_bei = wechsel_bei if wechsel_bei is not None else (von + bis) / 2
        self.wechsel_dauer = 2.6 if len(staende) > 1 else 0.0

        # Geometrien vorbereiten
        self._kontext = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 1, 1))
        self.pfad_land = [self._flaechen_pfad([poly]) for poly in natural_earth("land")]
        self.pfad_seen = [self._flaechen_pfad([poly]) for poly in natural_earth("seen")]
        self.pfad_fluesse = [self._linien_pfad([l]) for rang, l in natural_earth("fluesse") if rang <= 7]
        self.ebenen = [self._stand_vorbereiten(s) for s in staende]
        self.orte = []
        for angabe in orte:
            name, lat, lon = ort_finden(angabe)
            pt = self.proj(lon, lat)
            if pt:
                self.orte.append((name or angabe, pt))
        self._einblendungen = self._texte_vorbereiten()

    # -- Pfade --
    def _ring(self, ctx, ring) -> bool:
        erster = True
        box = self._box
        for lon, lat, *_ in ring:
            pt = self.proj(lon, lat)
            if pt is None:
                erster = True
                continue
            x, y = pt
            if x < box[0]: box[0] = x
            if x > box[1]: box[1] = x
            if y < box[2]: box[2] = y
            if y > box[3]: box[3] = y
            if erster:
                ctx.move_to(pt[0], -pt[1])
                erster = False
            else:
                ctx.line_to(pt[0], -pt[1])
        if not erster:
            ctx.close_path()
        return not erster

    def _sichtbar(self, ring) -> bool:
        # Nur Gebiete, die nicht auf der Rückseite des Globus liegen
        lon, lat = ring[0][0], ring[0][1]
        pt = self.proj(lon, lat)
        return pt is not None and math.hypot(*pt) < 9000

    def _flaechen_pfad(self, polygone):
        """Cairo-Pfad (km-Koordinaten) und Begrenzungsrechteck (x0, x1, y0, y1)."""
        ctx = self._kontext
        ctx.new_path()
        self._box = [math.inf, -math.inf, math.inf, -math.inf]
        for poly in polygone:
            if not poly or not any(self._sichtbar(r) for r in poly[:1]):
                continue
            for ring in poly:
                self._ring(ctx, ring)
        return ctx.copy_path(), tuple(self._box)

    def _linien_pfad(self, linien):
        ctx = self._kontext
        ctx.new_path()
        self._box = [math.inf, -math.inf, math.inf, -math.inf]
        for linie in linien:
            if not linie or not self._sichtbar(linie):
                continue
            self._ring_offen(ctx, linie)
        return ctx.copy_path(), tuple(self._box)

    def _ring_offen(self, ctx, linie) -> None:
        erster = True
        box = self._box
        for lon, lat, *_ in linie:
            pt = self.proj(lon, lat)
            if pt is None:
                erster = True
                continue
            x, y = pt
            box[0], box[1] = min(box[0], x), max(box[1], x)
            box[2], box[3] = min(box[2], y), max(box[3], y)
            (ctx.move_to if erster else ctx.line_to)(x, -y)
            erster = False

    def _stand_vorbereiten(self, stand: Kartenstand) -> dict:
        gebiete = historisch(stand.jahr)
        flaechen = []  # (Farbe, Pfad)
        grenzen_genau, grenzen_ungefaehr = [], []
        for i, g in enumerate(gebiete):
            pfad = self._flaechen_pfad(g["polygone"])
            ton = GEBIETSTOENE[sum(map(ord, g["name"])) % len(GEBIETSTOENE)]
            flaechen.append((ton, pfad))
            (grenzen_genau if g["genauigkeit"] >= 2 else grenzen_ungefaehr).append(pfad)
        hervor = []
        for h in stand.hervorhebungen:
            polys = [p for g in gebiete if g["name"] == h.name for p in g["polygone"]]
            pfad = self._flaechen_pfad(polys)
            mitte = self._beschriftungspunkt(polys)
            hervor.append((h, pfad, mitte))
        return {"flaechen": flaechen, "genau": grenzen_genau, "ungefaehr": grenzen_ungefaehr,
                "hervor": hervor}

    def _beschriftungspunkt(self, polys):
        """Schwerpunkt der größten Teilfläche (in km)."""
        bestes, beste_flaeche = None, 0.0
        for poly in polys:
            pts = [self.proj(lon, lat) for lon, lat, *_ in poly[0]]
            pts = [p for p in pts if p]
            if len(pts) < 3:
                continue
            a = cx = cy = 0.0
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                k = x1 * y2 - x2 * y1
                a += k
                cx += (x1 + x2) * k
                cy += (y1 + y2) * k
            if abs(a) > beste_flaeche and a != 0:
                beste_flaeche = abs(a)
                bestes = (cx / (3 * a), cy / (3 * a))
        return bestes

    def _texte_vorbereiten(self) -> list:
        W, H = self.breite, self.hoehe
        t = []
        quelle_jahre = " → ".join(str(s.jahr) for s in self.staende)
        q_bild, qx, qy = texte.quellenzeile(
            f"Grenzen: Stand {quelle_jahre} · historical-basemaps · Natural Earth", W, H, y_anteil=0.035)
        t.append(texte.Einblendung(q_bild, qx, qy, self.von + 0.5, self.bis - 0.4))
        if self.titel:
            b, x, y = texte.kartentitel(self.titel, W, H)
            t.append(texte.Einblendung(b, x, y, self.von + 1.0, self.bis - 0.6, ein=1.2))
        # Jahreszahl(en): zeigt standardmäßig den tatsächlichen Kartenstand
        if len(self.staende) == 1:
            text = self.jahr_text or str(self.staende[0].jahr)
            unter = "" if not self.jahr_text or self.jahr_text == str(self.staende[0].jahr) \
                else f"Grenzen von {self.staende[0].jahr}"
            b, x, y = texte.jahreszahl(text, unter, W, H)
            t.append(texte.Einblendung(b, x, y, self.von + 0.6, self.bis - 0.5, ein=1.2))
        else:
            mitte = self.wechsel_bei
            for i, s in enumerate(self.staende):
                b, x, y = texte.jahreszahl(str(s.jahr), "", W, H)
                von = self.von + 0.6 if i == 0 else mitte
                bis = mitte + 0.4 if i == 0 else self.bis - 0.5
                t.append(texte.Einblendung(b, x, y, von, bis, ein=1.0, aus=1.0))
        return t

    # -- Kamera --
    def kamera(self, t: float) -> tuple[float, float, float]:
        p = _weich((t - self.fahrt_von) / max(self.fahrt_bis - self.fahrt_von, 1e-6))
        if self.kamera_ziel == self.kamera_start:
            p = 0.0
        (x0, y0, w0), (x1, y1, w1) = self.kamera_start, self.kamera_ziel
        # Zoom logarithmisch (gleichmäßig empfundene Geschwindigkeit)
        w = math.exp(math.log(w0) + (math.log(w1) - math.log(w0)) * p)
        # Mittelpunkt so führen, dass er mit dem Zoom „mitwandert“
        if abs(w1 - w0) > 1e-6:
            q = (w0 - w) / (w0 - w1)
        else:
            q = p
        return x0 + (x1 - x0) * q, y0 + (y1 - y0) * q, w

    # -- Zeichnen --
    def bild(self, t: float) -> Image.Image:
        W, H = self.breite, self.hoehe
        flaeche = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        ctx = cairo.Context(flaeche)
        cx, cy, wkm = self.kamera(t)
        s = W / wkm
        matrix = cairo.Matrix(s, 0, 0, s, W / 2 - cx * s, H / 2 + cy * s)
        px = H / 1920  # Linienstärken relativ zur Bildhöhe

        # sichtbares Rechteck in km (mit Rand für Linienbreiten und Leuchten)
        halb_b, halb_h = wkm / 2 * 1.08, wkm * H / W / 2 * 1.08
        sicht = (cx - halb_b, cx + halb_b, cy - halb_h, cy + halb_h)

        def zu_sehen(box) -> bool:
            return not (box[1] < sicht[0] or box[0] > sicht[1] or box[3] < sicht[2] or box[2] > sicht[3])

        def pfad(*teile):
            """Hängt alle sichtbaren Teile an einen gemeinsamen Pfad. False = nichts sichtbar."""
            ctx.new_path()
            ctx.save()
            ctx.set_matrix(matrix)
            gefunden = False
            for p, box in teile:
                if zu_sehen(box):
                    ctx.append_path(p)
                    gefunden = True
            ctx.restore()
            return gefunden

        verlauf = cairo.LinearGradient(0, 0, 0, H)
        verlauf.add_color_stop_rgb(0, *MEER_OBEN)
        verlauf.add_color_stop_rgb(1, *MEER_UNTEN)
        ctx.set_source(verlauf)
        ctx.paint()

        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        pfad(*self.pfad_land)
        ctx.set_source_rgb(*LAND)
        ctx.fill()

        # Grenzstände (bei Wechsel weich überblendet)
        if len(self.ebenen) == 1:
            anteile = [1.0]
        else:
            a = _weich((t - (self.wechsel_bei - self.wechsel_dauer / 2)) / self.wechsel_dauer)
            anteile = [1.0 - a, a]
        hervor_ein = _weich((t - self.von - 0.8) / 1.6)

        for ebene, anteil in zip(self.ebenen, anteile):
            if anteil <= 0.002:
                continue
            ctx.push_group()
            for ton, p in ebene["flaechen"]:
                if pfad(p):
                    ctx.set_source_rgb(*ton)
                    ctx.fill()
            for h, p, _ in ebene["hervor"]:
                if not pfad(p):
                    continue
                r, g, b = h.farbe
                ctx.set_source_rgba(r, g, b, 0.62 * hervor_ein)
                ctx.fill()
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.set_source_rgba(*GRENZE, 0.42)
            ctx.set_line_width(1.3 * px)
            ctx.set_dash([])
            if pfad(*ebene["genau"]):  # alle Grenzen in einem Zug
                ctx.stroke()
            ctx.set_source_rgba(*GRENZE, 0.22)
            ctx.set_dash([5 * px, 4 * px])
            if pfad(*ebene["ungefaehr"]):
                ctx.stroke()
            ctx.set_dash([])
            # Leuchtende Kontur der hervorgehobenen Gebiete
            for h, p, _ in ebene["hervor"]:
                r, g, b = (min(1.0, c * 1.35 + 0.08) for c in h.farbe)
                if not pfad(p):
                    continue
                for breite_px, alpha in ((11, 0.10), (6, 0.18), (2.4, 0.95)):
                    pfad(p)
                    ctx.set_source_rgba(r, g, b, alpha * hervor_ein)
                    ctx.set_line_width(breite_px * px)
                    ctx.stroke()
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(anteil)

        if pfad(*self.pfad_seen):
            ctx.set_source_rgb(*MEER_UNTEN)
            ctx.fill()
        if pfad(*self.pfad_fluesse):
            ctx.set_source_rgba(*FLUSS, 0.85)
            ctx.set_line_width(1.1 * px)
            ctx.stroke()

        # Ortspunkte
        orte_px = []
        # Ortsnamen erst, wenn die Kamera nah genug ist (sonst überlagern sie sich)
        nah = _weich((ORTE_AB_KM - wkm) / (0.35 * ORTE_AB_KM))
        for i, (name, (ox, oy)) in enumerate(self.orte):
            a = min(nah, _weich((t - self.von - 1.2 - 0.45 * i) / 0.8))
            if a <= 0:
                continue
            x, y = W / 2 + (ox - cx) * s, H / 2 - (oy - cy) * s
            if not (-50 < x < W + 50 and -50 < y < H + 50):
                continue
            ctx.arc(x, y, 9 * px, 0, 2 * math.pi)
            ctx.set_source_rgba(0.95, 0.91, 0.82, 0.25 * a)
            ctx.fill()
            ctx.arc(x, y, 5 * px, 0, 2 * math.pi)
            ctx.set_source_rgba(0.95, 0.91, 0.82, a)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.1, 0.1, 0.1, 0.8 * a)
            ctx.set_line_width(1.5 * px)
            ctx.stroke()
            orte_px.append((name, x, y, a))

        flaeche.flush()
        bild = Image.frombuffer("RGB", (W, H), bytes(flaeche.get_data()), "raw", "BGRX", flaeche.get_stride(), 1)

        # Beschriftungen der hervorgehobenen Gebiete
        for ebene, anteil in zip(self.ebenen, anteile):
            for h, _, mitte in ebene["hervor"]:
                if not h.beschriftung or mitte is None or anteil * hervor_ein <= 0.01:
                    continue
                spr = texte.kartenbeschriftung(h.beschriftung, "land", H)
                x = W / 2 + (mitte[0] - cx) * s - spr.width / 2
                y = H / 2 - (mitte[1] - cy) * s - spr.height / 2
                # einem Ortsnamen in der Nähe ausweichen
                for _, ox, oy, _a in orte_px:
                    if abs(oy - (y + spr.height / 2)) < spr.height * 1.1 and x - 40 * px < ox < x + spr.width + 200 * px:
                        y = oy + spr.height * 0.9
                self._kleben(bild, spr, x, y, anteil * hervor_ein)
        for name, x, y, a in orte_px:
            spr = texte.kartenbeschriftung(name, "ort", H)
            self._kleben(bild, spr, x + 12 * px, y - spr.height / 2 - 2 * px, a)

        for e in self._einblendungen:
            e.auftragen(bild, t)
        return bild

    @staticmethod
    def _kleben(bild: Image.Image, sprite: Image.Image, x: float, y: float, alpha: float) -> None:
        if alpha < 0.997:
            sprite = sprite.copy()
            sprite.putalpha(sprite.getchannel("A").point(lambda v: int(v * alpha)))
        bild.paste(sprite, (round(x), round(y)), sprite)


def farbe_lesen(text: str) -> tuple[float, float, float]:
    t = text.strip().lower()
    if t in FARBEN:
        return FARBEN[t]
    if t.startswith("#") and len(t) == 7:
        return tuple(int(t[i:i + 2], 16) / 255 for i in (1, 3, 5))
    raise KartenFehler(f"Farbe '{text}' unbekannt. Möglich: {', '.join(sorted(FARBEN))} oder #RRGGBB.")
