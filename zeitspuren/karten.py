"""Animierte historische Karten im hellen Atlas-Stil (englische Beschriftung).

Historische Genauigkeit
-----------------------
- **Ab 1886: CShapes 2.0** (Schvitz, Girardin, Rüegger, Weidmann u. a.,
  ETH Zürich / Universität Konstanz; GPL ≥ 2). Wissenschaftlich begutachteter
  Datensatz aller Staatsgrenzen mit **tagesgenauen** Gültigkeitszeiträumen.
  Ein Kartenstand ist ein Datum (``1920`` = 1. Juli 1920, oder genau
  ``1920-03-01``); gezeigt wird exakt die an diesem Tag gültige Grenzziehung.
- **Vor 1886** gibt es keinen gleichwertigen Datensatz. Dann wird
  „historical-basemaps“ (A. Ourednik, GPL-3.0) für feste Stichjahre benutzt –
  mit nachweislichen Ungenauigkeiten. Das Programm warnt dann ausdrücklich
  (``daten_warnung``) und rendert nur nach Bestätigung.
- Es werden nie Grenzverläufe erfunden, interpoliert oder heutige Grenzen
  ersatzweise gezeigt. Jede Karte nennt Quelle und Stand.
- Küsten, Flüsse, Seen und Ortskoordinaten: Natural Earth (gemeinfrei).

Gestaltung (Vorbild: europäische Atlanten des 19. Jahrhunderts)
----------------------------------------------------------------
Helles Atlasblau mit Wasserlinien an den Küsten, Pastell-Flächenfarben
(Nachbarn nie gleichfarbig), farbiges Grenzkolorit an der Innenseite der
Grenzen, klare dunkle Grenzlinien, Gradnetz, gerahmte Titelkartusche.
Das besprochene Gebiet wird kräftig hervorgehoben, Nachbarn werden fast weiß.
Grenzwechsel: neue Grenze zeichnet sich ein, frühere Grenze bleibt rot
gestrichelt, abgetretene Gebiete werden rot schraffiert (mit Legende).
Beschriftungen werden kollisionsfrei gesetzt.
"""

from __future__ import annotations

import csv
import datetime as dt
import difflib
import json
import lzma
import math
import re
import threading
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import cairo
import numpy as np
from PIL import Image

from . import ohm, texte

DATEN = Path(__file__).resolve().parent.parent / "daten" / "karten"
HIST_ORDNER = DATEN / "historisch"
CSHAPES_DATEI = DATEN / "cshapes" / "cshapes_2_gw.topojson.xz"

# Fest verankerte Versionsstände der Datenquellen (Reproduzierbarkeit)
HIST_VERSION = "4b5039e50d8d2464b065bd76ad6086cd4597108d"
HIST_URL = "https://raw.githubusercontent.com/aourednik/historical-basemaps/{v}/geojson/world_{j}.geojson"
CSHAPES_VERSION = "cran/cshapes 54840534d9a82cfd01caf1021f85933e701e8318 (CShapes 2.0)"
CSHAPES_VON, CSHAPES_BIS = dt.date(1886, 1, 1), dt.date(2019, 12, 31)

STICHJAHRE_HB = [
    -123000, -10000, -8000, -5000, -4000, -3000, -2000, -1500, -1000, -700, -500, -400, -323, -300,
    -200, -100, -1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1279, 1300, 1400,
    1492, 1500, 1530, 1600, 1650, 1700, 1715, 1783, 1800, 1815, 1878, 1880,
]

ERDRADIUS = 6371.0
ORTE_AB_KM = 2600       # Ortsnamen erst unterhalb dieser sichtbaren Kartenbreite
NACHBARN_AB_KM = 3200   # Nachbarnamen erst unterhalb dieser Kartenbreite

# --- Farbwelt: heller Atlas des 19. Jahrhunderts -----------------------------
PAPIER = (0.965, 0.945, 0.890)        # Land ohne Staatszugehörigkeit / Grundton
ZURUECK = (0.955, 0.948, 0.925)       # Zielton für zurückgenommene Nachbarn (fast weiß)
MEER = (0.745, 0.870, 0.910)          # klares, helles Atlasblau
WASSERLINIE = (0.560, 0.735, 0.800)
KUESTE = (0.27, 0.42, 0.50)
FLUSS = (0.42, 0.62, 0.74)
GRADNETZ = (0.40, 0.52, 0.58)
GRENZE = (0.20, 0.17, 0.15)
TINTE = (0.204, 0.157, 0.118)
ALTE_GRENZE = (0.62, 0.17, 0.13)
UMKAEMPFT = (0.40, 0.27, 0.18)        # Schraffur umkämpfter Gebiete (Sepia)
ZONE = (0.36, 0.20, 0.38)             # Abstimmungsgebiete (Pflaume)

PASTELL = {
    "rosa": (0.949, 0.800, 0.765),
    "gelb": (0.957, 0.898, 0.640),
    "gruen": (0.800, 0.890, 0.710),
    "blau": (0.770, 0.835, 0.925),
    "violett": (0.860, 0.800, 0.910),
    "orange": (0.965, 0.835, 0.670),
    "tuerkis": (0.760, 0.890, 0.860),
    "sand": (0.910, 0.860, 0.760),
}
PASTELL_REIHE = list(PASTELL)

# Klassische Atlasfarben großer Mächte – einheitliche Farben über alle Szenen
STAMMFARBEN = [
    (("prussia", "german", "brandenburg"), "blau"),
    (("russia", "soviet", "ussr"), "gruen"),
    (("austria", "habsburg", "hungar"), "gelb"),
    (("poland", "polish"), "rosa"),
    (("france", "french"), "orange"),
    (("united kingdom", "britain", "england"), "rosa"),
    (("ottoman", "turkey"), "violett"),
    (("sweden", "swedish"), "tuerkis"),
    (("italy", "sardinia", "italian"), "tuerkis"),
    (("spain", "spanish"), "violett"),
]

FARBEN = {
    "rot": (0.80, 0.36, 0.29),
    "dunkelrot": (0.64, 0.21, 0.17),
    "gold": (0.90, 0.69, 0.27),
    "gelb": (0.93, 0.80, 0.33),
    "blau": (0.36, 0.53, 0.76),
    "hellblau": (0.52, 0.70, 0.86),
    "gruen": (0.45, 0.65, 0.40),
    "grün": (0.45, 0.65, 0.40),
    "orange": (0.91, 0.58, 0.27),
    "violett": (0.58, 0.43, 0.69),
    "grau": (0.58, 0.56, 0.52),
}

REGIONEN = {
    "welt": (-170, -55, 180, 75), "world": (-170, -55, 180, 75),
    "europa": (-11, 35, 40, 70), "europe": (-11, 35, 40, 70),
    "mitteleuropa": (3, 44.5, 25, 56), "central europe": (3, 44.5, 25, 56),
    "westeuropa": (-10, 42, 15, 59), "western europe": (-10, 42, 15, 59),
    "osteuropa": (14, 42, 45, 62), "eastern europe": (14, 42, 45, 62),
    "nordeuropa": (-5, 54, 32, 71.5), "skandinavien": (4, 54, 32, 71.5), "scandinavia": (4, 54, 32, 71.5),
    "suedeuropa": (-10, 35, 30, 47), "südeuropa": (-10, 35, 30, 47),
    "balkan": (13, 39, 30, 47.5), "balkans": (13, 39, 30, 47.5),
    "mittelmeer": (-6, 30, 36, 46.5), "mediterranean": (-6, 30, 36, 46.5),
    "ostsee": (9, 53, 31, 66), "baltic": (9, 53, 31, 66),
    "deutschland": (5.5, 47, 15.5, 55.2), "germany": (5.5, 47, 15.5, 55.2),
    "oesterreich": (9.5, 46.3, 17.2, 49.1), "österreich": (9.5, 46.3, 17.2, 49.1),
    "schweiz": (5.9, 45.8, 10.5, 47.9),
    "frankreich": (-5, 42, 8.5, 51.2), "france": (-5, 42, 8.5, 51.2),
    "italien": (6.5, 36.5, 18.6, 47.1), "italy": (6.5, 36.5, 18.6, 47.1),
    "polen": (14, 49, 24.2, 55), "poland": (14, 49, 24.2, 55),
    "benelux": (2.5, 49.4, 7.3, 53.6),
    "britische inseln": (-11, 49.8, 2, 61), "british isles": (-11, 49.8, 2, 61),
    "iberische halbinsel": (-9.6, 35.9, 3.4, 43.9), "iberia": (-9.6, 35.9, 3.4, 43.9),
    "ukraine": (22, 44, 40.5, 52.5),
    "russland": (27, 41, 60, 70), "russia": (27, 41, 60, 70),
    "nordafrika": (-17, 15, 35, 38), "north africa": (-17, 15, 35, 38),
    "afrika": (-20, -36, 52, 38), "africa": (-20, -36, 52, 38),
    "naher osten": (25, 12, 63, 42), "nahost": (25, 12, 63, 42), "middle east": (25, 12, 63, 42),
    "asien": (25, -10, 150, 60), "asia": (25, -10, 150, 60),
    "ostasien": (95, 15, 150, 50), "east asia": (95, 15, 150, 50),
    "nordamerika": (-170, 10, -50, 75), "north america": (-170, 10, -50, 75),
    "usa": (-125, 24, -66, 50),
    "suedamerika": (-82, -56, -34, 13), "südamerika": (-82, -56, -34, 13), "south america": (-82, -56, -34, 13),
}

MONATE = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


class KartenFehler(ValueError):
    pass


# --- Kartenstand: welches Datum, welche Quelle -------------------------------

@dataclass(frozen=True)
class Stand:
    text: str          # wie im Drehbuch geschrieben
    quelle: str        # "cshapes" oder "hb"
    datum: dt.date | None
    jahr: int

    @property
    def anzeige(self) -> str:
        return str(self.jahr) if self.jahr > 0 else f"{-self.jahr} BC"

    @property
    def stand_englisch(self) -> str:
        if self.quelle == "cshapes":
            d = self.datum
            return f"Borders as of {d.day} {MONATE[d.month - 1]} {d.year}"
        return f"Borders c. {self.anzeige}"

    @property
    def quellenangabe(self) -> str:
        if self.quelle == "cshapes":
            if ohm.gilt_am(self.datum.isoformat()):
                return "OpenHistoricalMap · CShapes 2.0"
            return "CShapes 2.0 (ETH Zurich)"
        return "historical-basemaps (A. Ourednik), approximate"


def stand_lesen(text: str) -> Stand:
    """'1920' → 1. Juli 1920 (CShapes); '1920-03-01' → genaues Datum; vor 1886 → Stichjahr."""
    text = str(text).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        datum = dt.date(int(m[1]), int(m[2]), int(m[3]))
        if not CSHAPES_VON <= datum <= CSHAPES_BIS:
            raise KartenFehler(f"Datum {text}: genaue Daten gibt es nur von 1886 bis 2019.")
        return Stand(text, "cshapes", datum, datum.year)
    if not re.fullmatch(r"-?\d+", text):
        raise KartenFehler(f"'{text}' ist kein Kartenstand (Beispiele: 1920 oder 1920-03-01).")
    jahr = int(text)
    if CSHAPES_VON.year <= jahr <= CSHAPES_BIS.year:
        return Stand(text, "cshapes", dt.date(jahr, 7, 1), jahr)
    if jahr not in STICHJAHRE_HB:
        naechste = sorted(STICHJAHRE_HB, key=lambda j: abs(j - jahr))[:3]
        raise KartenFehler(
            f"Für {jahr} gibt es keinen Grenzdatensatz. Genaue Daten (CShapes) beginnen 1886; davor gibt es "
            f"nur Näherungsdaten für Stichjahre (in der Nähe: {', '.join(map(str, sorted(naechste)))}). "
            f"Zwischenstände werden nicht erfunden – alternativ eine eingescannte Originalkarte verwenden.")
    return Stand(text, "hb", None, jahr)


def daten_warnung(stand: Stand) -> str | None:
    if stand.quelle == "cshapes":
        w = ohm.warnungen_am(stand.datum.isoformat())
        return " ".join(w) if w else None
    if stand.quelle == "hb":
        return (f"Kartenstand {stand.anzeige} stammt aus Näherungsdaten (historical-basemaps). Stichproben "
                f"zeigen dort Fehler (z. B. 1783: Thorn und Krakau falsch zugeordnet). Nur nach Prüfung "
                f"verwenden – genauer ist eine eingescannte Originalkarte.")
    return None


# --- Daten laden --------------------------------------------------------------

_ladesperre = threading.Lock()


@lru_cache(maxsize=1)
def _cshapes_roh() -> tuple[list, list]:
    roh = json.loads(lzma.open(CSHAPES_DATEI).read())
    return roh["arcs"], roh["objects"]["cshapes_2_gw"]["geometries"]


def _topo_ring(arcs: list, indizes: list[int]) -> list:
    punkte: list = []
    for i in indizes:
        bogen = arcs[i] if i >= 0 else arcs[~i][::-1]
        punkte.extend(bogen if not punkte else bogen[1:])
    return punkte


@lru_cache(maxsize=16)
def gebiete(stand: Stand) -> list[dict]:
    if stand.quelle == "cshapes":
        arcs, geos = _cshapes_roh()
        tag = stand.datum.isoformat()
        liste = []
        for g in geos:
            p = g["properties"]
            if not (p["start"] <= tag <= p["end"]):
                continue
            ringe = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
            polygone = [[_topo_ring(arcs, ring) for ring in poly] for poly in ringe]
            liste.append({"name": p["country_name"], "genauigkeit": 3 if p.get("b_def") else 1,
                          "status": p.get("status", ""), "polygone": polygone})
        # Detailgrenzen (OpenHistoricalMap) ersetzen, wo vorhanden, die gröberen CShapes-Flächen
        liste, umkaempft = ohm.kombinieren(liste, tag)
        for polys, text, kante, start, ende in umkaempft:
            liste.append({"name": "__umkaempft__", "umkaempft": True, "text": text, "genauigkeit": 1,
                          "status": "", "polygone": polys, "kante": kante, "start": start, "ende": ende})
        return liste
    return _historisch(stand.jahr)


def _datei_hist(jahr: int) -> Path:
    name = f"bc{-jahr}" if jahr < 0 else str(jahr)
    return HIST_ORDNER / f"world_{name}.geojson"


@lru_cache(maxsize=16)
def _historisch(jahr: int) -> list[dict]:
    datei = _datei_hist(jahr)
    with _ladesperre:
        if not datei.exists():
            HIST_ORDNER.mkdir(parents=True, exist_ok=True)
            url = HIST_URL.format(v=HIST_VERSION, j=datei.stem.replace("world_", ""))
            try:
                with urllib.request.urlopen(url, timeout=60) as antwort:
                    datei.write_bytes(antwort.read())
            except Exception as fehler:  # noqa: BLE001
                raise KartenFehler(f"Kartendaten für {jahr} konnten nicht geladen werden: {fehler}") from None
    roh = json.loads(datei.read_text(encoding="utf-8"))
    liste = []
    for f in roh["features"]:
        p = f.get("properties") or {}
        if not p.get("NAME") or not f.get("geometry"):
            continue
        liste.append({"name": p["NAME"], "genauigkeit": int(p.get("BORDERPRECISION") or 1),
                      "status": "", "polygone": _polygone(f["geometry"])})
    return liste


def _polygone(geometrie: dict) -> list:
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
    verzeichnis: dict[str, tuple[str, float, float]] = {}
    with open(DATEN / "orte.csv", encoding="utf-8") as fh:
        for z in csv.DictReader(fh):
            eintrag = (z["name"], float(z["breite"]), float(z["laenge"]))
            for n in (z["name"], z["name_ascii"], z["name_de"]):
                if n and _schluessel(n) not in verzeichnis:
                    verzeichnis[_schluessel(n)] = eintrag
    return verzeichnis


def ort_finden(angabe: str) -> tuple[str, float, float]:
    """'Warsaw', 'Danzig@54.35,18.65' oder '54.35,18.65' → (Anzeigename, Breite, Länge).

    Angezeigt wird der Name genau so, wie er im Drehbuch steht (englisch, ggf.
    historische Form wie 'Danzig' oder 'Königsberg')."""
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
    return angabe, treffer[1], treffer[2]


def gebiet_namen(stand: Stand) -> list[str]:
    return sorted({g["name"] for g in gebiete(stand)})


def gebiet_pruefen(stand: Stand, name: str) -> str:
    namen = gebiet_namen(stand)
    if name in namen:
        return name
    klein = {n.lower(): n for n in namen}
    if name.lower() in klein:
        return klein[name.lower()]
    vorschlaege = difflib.get_close_matches(name, namen, n=4, cutoff=0.5)
    vorschlaege += [n for n in namen if name.lower() in n.lower() and n not in vorschlaege][:3]
    tipp = f" Namen im Datensatz für {stand.text}: {', '.join(vorschlaege)}." if vorschlaege else ""
    raise KartenFehler(f"Gebiet '{name}' gibt es im Kartenstand {stand.text} nicht.{tipp}")


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


# --- Szene ----------------------------------------------------------------------

@dataclass
class Hervorhebung:
    name: str
    farbe: tuple[float, float, float]
    beschriftung: str = ""


@dataclass
class Kartenstand:
    stand: Stand
    hervorhebungen: list[Hervorhebung] = field(default_factory=list)
    nachbarn: list[tuple[str, str]] = field(default_factory=list)  # (Datenname, Beschriftung)
    zonen: list[str] = field(default_factory=list)                    # Schlüssel aus ohm/zonen.json
    vermerke: list[tuple[str, float, float]] = field(default_factory=list)  # (Text, Breite, Länge)


def _weich(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


def _mischen(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _kraeftiger(farbe, faktor=0.72):
    """Dunklere, sattere Fassung eines Tons (für das Grenzkolorit)."""
    return tuple(max(0.0, c * faktor - 0.04) for c in farbe)


def _stammfarbe(name: str) -> str | None:
    n = name.lower()
    for woerter, farbe in STAMMFARBEN:
        if any(w in n for w in woerter):
            return farbe
    return None


class _Belegung:
    """Merkt sich belegte Bildbereiche, damit sich Beschriftungen nie überlagern."""

    def __init__(self, breite: int, hoehe: int, rand: float):
        self.rechtecke: list[tuple[float, float, float, float]] = []
        self.b, self.h, self.rand = breite, hoehe, rand

    def frei(self, x, y, w, h) -> bool:
        if x < self.rand or y < self.rand or x + w > self.b - self.rand or y + h > self.h - self.rand:
            return False
        return all(x + w <= a or a + c <= x or y + h <= b_ or b_ + d <= y for a, b_, c, d in self.rechtecke)

    def belegen(self, x, y, w, h) -> None:
        self.rechtecke.append((x, y, w, h))


class Kartenszene:
    """Rendert eine animierte Karte für das Zeitintervall [von, bis] (Videozeit)."""

    WECHSEL_DAUER = 3.2

    def __init__(self, staende: list[Kartenstand], wechsel_bei: float | None,
                 ausschnitt: str, fahrt_ziel: str | None, fahrt_von: float | None, fahrt_bis: float | None,
                 orte: list[str], titel: str, jahr_text: str | None,
                 von: float, bis: float, breite: int, hoehe: int, vermerke_ab: float | None = None):
        self.staende = staende
        self.von, self.bis = von, bis
        self.breite, self.hoehe = breite, hoehe
        self.titel = titel
        self.jahr_text = jahr_text
        self.vermerke_ab = vermerke_ab
        seitenv = breite / hoehe

        start = _ausschnitt_geo(ausschnitt, seitenv)
        ziel = _ausschnitt_geo(fahrt_ziel, seitenv) if fahrt_ziel else None
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
            self.kamera_ziel = (sx, sy, start[2] / 1.07)
        dauer = bis - von
        self.fahrt_von = fahrt_von if fahrt_von is not None else von + 0.12 * dauer
        self.fahrt_bis = fahrt_bis if fahrt_bis is not None else bis - 0.12 * dauer
        if not ziel:
            self.fahrt_von, self.fahrt_bis = von, bis
        if self.fahrt_bis - self.fahrt_von < 1.0:
            self.fahrt_bis = self.fahrt_von + 1.0
        self.wechsel_bei = wechsel_bei if wechsel_bei is not None else (von + bis) / 2

        bx = [sx, self.kamera_ziel[0]]
        by = [sy, self.kamera_ziel[1]]
        wmax = max(start[2], self.kamera_ziel[2])
        self._szenenrahmen = (min(bx) - wmax * 0.6, max(bx) + wmax * 0.6,
                              min(by) - wmax / seitenv * 0.6, max(by) + wmax / seitenv * 0.6)

        self._kontext = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 1, 1))
        self.pfad_land = [self._flaechen_pfad([poly]) for poly in natural_earth("land")]
        self.pfad_seen = [self._flaechen_pfad([poly]) for poly in natural_earth("seen")]
        self.pfad_fluesse = [self._linien_pfad([l]) for rang, l in natural_earth("fluesse") if rang <= 6]
        self.pfad_gradnetz = self._gradnetz()
        self.ebenen = [self._stand_vorbereiten(s) for s in staende]
        self._farben_verteilen()
        self.orte = []
        for angabe in orte:
            name, lat, lon = ort_finden(angabe)
            pt = self.proj(lon, lat)
            if pt:
                self.orte.append((name or angabe, pt))
        self._schraffur_muster = self._schraffur(hoehe / 1920)
        self._schraffur_umkaempft = self._schraffur(hoehe / 1920, UMKAEMPFT, steigend=False, abstand=13)
        self._einblendungen = self._texte_vorbereiten()

    # -- Geometrie -------------------------------------------------------------
    def _neue_box(self):
        self._box = [math.inf, -math.inf, math.inf, -math.inf]

    def _punkte(self, ctx, linie, schliessen: bool) -> float:
        """Zeichnet eine Linie in den Pfad; gibt ihre Länge in km zurück."""
        erster, laenge, vorher = True, 0.0, None
        box = self._box
        for lon, lat, *_ in linie:
            pt = self.proj(lon, lat)
            if pt is None:
                erster, vorher = True, None
                continue
            x, y = pt
            if x < box[0]: box[0] = x
            if x > box[1]: box[1] = x
            if y < box[2]: box[2] = y
            if y > box[3]: box[3] = y
            if erster:
                ctx.move_to(x, -y)
                erster = False
            else:
                ctx.line_to(x, -y)
                laenge += math.hypot(x - vorher[0], y - vorher[1])
            vorher = (x, y)
        if schliessen and not erster:
            ctx.close_path()
        return laenge

    def _sichtbar(self, ring) -> bool:
        pt = self.proj(ring[0][0], ring[0][1])
        return pt is not None and math.hypot(*pt) < 9000

    def _flaechen_pfad(self, polygone, mit_laenge: bool = False):
        ctx = self._kontext
        ctx.new_path()
        self._neue_box()
        laenge = 0.0
        for poly in polygone:
            if not poly or not self._sichtbar(poly[0]):
                continue
            for ring in poly:
                laenge = max(laenge, self._punkte(ctx, ring, True))
        teil = (ctx.copy_path(), tuple(self._box))
        return (teil, laenge) if mit_laenge else teil

    def _linien_pfad(self, linien):
        ctx = self._kontext
        ctx.new_path()
        self._neue_box()
        for linie in linien:
            if linie and self._sichtbar(linie):
                self._punkte(ctx, linie, False)
        return ctx.copy_path(), tuple(self._box)

    def _gradnetz(self):
        linien = []
        for lon in range(-180, 181, 5):
            linien.append([(lon, lat / 2) for lat in range(-160, 161)])
        for lat in range(-80, 81, 5):
            linien.append([(lon / 2, lat) for lon in range(-360, 361)])
        return [self._linien_pfad([l]) for l in linien]

    def _stand_vorbereiten(self, kst: Kartenstand) -> dict:
        liste = gebiete(kst.stand)
        laender = []
        umkaempft = []
        for g in liste:
            if g.get("umkaempft"):
                teil = self._flaechen_pfad(g["polygone"])
                umkaempft.append({"teil": teil, "text": g["text"], "mitte": self._beschriftungspunkt(g["polygone"]),
                                  "kante": self._linien_pfad(g["kante"]),
                                  "start": self.proj(*g["start"]), "ende": self.proj(*g["ende"])})
                continue
            teil = self._flaechen_pfad(g["polygone"])
            laender.append({"name": g["name"], "teil": teil, "genau": g["genauigkeit"] >= 2})
        hervor = []
        for h in kst.hervorhebungen:
            polys = [p for g in liste if g["name"] == h.name for p in g["polygone"]]
            teil, laenge = self._flaechen_pfad(polys, mit_laenge=True)
            hervor.append({"h": h, "teil": teil, "laenge": laenge, "mitte": self._beschriftungspunkt(polys)})
        nachbarn = []
        for name, text in kst.nachbarn:
            polys = [p for g in liste if g["name"] == name for p in g["polygone"]]
            if polys:
                teil = self._flaechen_pfad(polys)
                nachbarn.append((text, self._beschriftungspunkt(polys), teil[1]))
        zonen = []
        for schl in kst.zonen:
            form, k = ohm.zone(schl)
            polys = ohm.als_polygone(form)
            zonen.append({"teil": self._flaechen_pfad(polys), "k": k, "mitte": self._beschriftungspunkt(polys)})
        vermerke = []
        for text, lat, lon in kst.vermerke:
            pt = self.proj(lon, lat)
            if pt:
                vermerke.append((text, pt))
        return {"laender": laender, "hervor": hervor, "nachbarn": nachbarn, "umkaempft": umkaempft,
                "zonen": zonen, "vermerke": vermerke}

    def _farben_verteilen(self) -> None:
        """Pastellfarben so verteilen, dass Nachbarn nie dieselbe Farbe haben.
        Große Mächte behalten (wenn möglich) ihre klassische Atlasfarbe."""
        alle: dict[str, list] = {}
        for ebene in self.ebenen:
            for land in ebene["laender"]:
                alle.setdefault(land["name"], []).append(land)
        namen = [n for n, ls in alle.items() if any(self._im_rahmen(l["teil"][1]) for l in ls)]
        nachbarschaft = self._nachbarschaft(namen)
        farbe: dict[str, str] = {}
        reihenfolge = sorted(namen, key=lambda n: (_stammfarbe(n) is None, -len(nachbarschaft.get(n, ()))))
        for n in reihenfolge:
            belegt = {farbe[m] for m in nachbarschaft.get(n, ()) if m in farbe}
            wunsch = _stammfarbe(n)
            if wunsch and wunsch not in belegt:
                farbe[n] = wunsch
                continue
            start = sum(map(ord, n)) % len(PASTELL_REIHE)
            for k in range(len(PASTELL_REIHE)):
                kandidat = PASTELL_REIHE[(start + k) % len(PASTELL_REIHE)]
                if kandidat not in belegt:
                    farbe[n] = kandidat
                    break
            else:
                farbe[n] = PASTELL_REIHE[start]
        for ebene in self.ebenen:
            for land in ebene["laender"]:
                land["farbe"] = PASTELL[farbe.get(land["name"], "sand")]

    def _im_rahmen(self, box) -> bool:
        r = self._szenenrahmen
        return not (box[1] < r[0] or box[0] > r[1] or box[3] < r[2] or box[2] > r[3])

    def _nachbarschaft(self, namen) -> dict[str, set]:
        """Ermittelt benachbarte Gebiete über ein kleines Rasterbild des Szenenrahmens."""
        r = self._szenenrahmen
        b = 700
        h = max(50, round(b * (r[3] - r[2]) / (r[1] - r[0])))
        flaeche = cairo.ImageSurface(cairo.FORMAT_RGB24, b, h)
        ctx = cairo.Context(flaeche)
        ctx.set_antialias(cairo.ANTIALIAS_NONE)
        s = b / (r[1] - r[0])
        matrix = cairo.Matrix(s, 0, 0, s, -r[0] * s, r[3] * s)
        nachbarschaft: dict[str, set] = {n: set() for n in namen}
        for ebene in self.ebenen:
            ctx.set_source_rgb(0, 0, 0)
            ctx.paint()
            ids = {}
            for i, land in enumerate(ebene["laender"], 1):
                if land["name"] not in nachbarschaft:
                    continue
                ids[i] = land["name"]
                ctx.new_path()
                ctx.save()
                ctx.set_matrix(matrix)
                ctx.append_path(land["teil"][0])
                ctx.restore()
                ctx.set_source_rgb(((i >> 16) & 255) / 255, ((i >> 8) & 255) / 255, (i & 255) / 255)
                ctx.fill()
            flaeche.flush()
            a = np.frombuffer(flaeche.get_data(), dtype=np.uint32).reshape(h, flaeche.get_stride() // 4)[:, :b]
            a = a & 0xFFFFFF
            for x, y in ((a[:, :-2], a[:, 2:]), (a[:-2, :], a[2:, :])):
                maske = (x != y) & (x != 0) & (y != 0)
                for p, q in set(zip(x[maske].tolist(), y[maske].tolist())):
                    if p in ids and q in ids and ids[p] != ids[q]:
                        nachbarschaft[ids[p]].add(ids[q])
                        nachbarschaft[ids[q]].add(ids[p])
        return nachbarschaft

    def _beschriftungspunkt(self, polys):
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
            if a != 0 and abs(a) > beste_flaeche:
                beste_flaeche = abs(a)
                bestes = (cx / (3 * a), cy / (3 * a))
        return bestes

    @staticmethod
    def _schraffur(px: float, farbe=ALTE_GRENZE, steigend: bool = True, abstand: float = 16):
        """Diagonale Schraffur (rot: abgetretene Gebiete; braun, fallend: umkämpfte Gebiete)."""
        n = max(8, round(abstand * px))
        kachel = cairo.ImageSurface(cairo.FORMAT_ARGB32, n, n)
        c = cairo.Context(kachel)
        c.set_source_rgba(*farbe, 0.9)
        c.set_line_width(max(1.2, 2.4 * px))
        for versatz in (-n, 0, n):
            if steigend:
                c.move_to(versatz, n)
                c.line_to(versatz + n, 0)
            else:
                c.move_to(versatz, 0)
                c.line_to(versatz + n, n)
        c.stroke()
        muster = cairo.SurfacePattern(kachel)
        muster.set_extend(cairo.EXTEND_REPEAT)
        return muster

    # -- Texte -----------------------------------------------------------------
    def _texte_vorbereiten(self) -> list:
        """Titelkartusche (Jahr, Stand, Titel, Legende, Quelle). Bei einem Grenzwechsel
        wird die Kartusche des neuen Stands weich eingeblendet."""
        W, H = self.breite, self.hoehe
        quellen = " / ".join(dict.fromkeys(s.stand.quellenangabe for s in self.staende))
        quelle = f"Map data: {quellen} · Natural Earth"
        if len(self.staende) == 1:
            st = self.staende[0].stand
            b, x, y = texte.kartusche(self.jahr_text or st.anzeige, st.stand_englisch, self.titel, None, quelle, W, H)
            return [texte.Einblendung(b, x, y, self.von + 0.5, self.bis - 0.4, ein=1.2)]
        alt, neu = self.staende[0].stand, self.staende[1].stand
        legende = (f"Border {alt.anzeige}", f"Border {neu.anzeige}")
        # Rahmen bleibt stehen; der Inhalt wechselt nacheinander (kein Überlagern)
        r, rx, ry = texte.kartusche(neu.anzeige, "", self.titel, legende, quelle, W, H, teil="rahmen")
        b1, x1, y1 = texte.kartusche(alt.anzeige, alt.stand_englisch, self.titel, None, quelle, W, H,
                                     teil="inhalt", legendenplatz=True)
        b2, x2, y2 = texte.kartusche(neu.anzeige, neu.stand_englisch, self.titel, legende, quelle, W, H,
                                     teil="inhalt")
        # Die Jahreszahl wechselt, BEVOR sich der neue Stand einzeichnet – so ist jede
        # sichtbare Fläche stets dem angezeigten Jahr zugeordnet.
        m = self.wechsel_bei - self.WECHSEL_DAUER / 2
        return [texte.Einblendung(r, rx, ry, self.von + 0.5, self.bis - 0.4, ein=1.2),
                texte.Einblendung(b1, x1, y1, self.von + 0.5, m - 0.1, ein=1.2, aus=0.5),
                texte.Einblendung(b2, x2, y2, m - 0.15, self.bis - 0.4, ein=0.5)]

    # -- Kamera ----------------------------------------------------------------
    def kamera(self, t: float) -> tuple[float, float, float]:
        p = _weich((t - self.fahrt_von) / max(self.fahrt_bis - self.fahrt_von, 1e-6))
        (x0, y0, w0), (x1, y1, w1) = self.kamera_start, self.kamera_ziel
        w = math.exp(math.log(w0) + (math.log(w1) - math.log(w0)) * p)
        q = (w0 - w) / (w0 - w1) if abs(w1 - w0) > 1e-6 else p
        return x0 + (x1 - x0) * q, y0 + (y1 - y0) * q, w

    # -- Zeichnen --------------------------------------------------------------
    def bild(self, t: float) -> Image.Image:
        W, H = self.breite, self.hoehe
        flaeche = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
        ctx = cairo.Context(flaeche)
        cx, cy, wkm = self.kamera(t)
        s = W / wkm
        matrix = cairo.Matrix(s, 0, 0, s, W / 2 - cx * s, H / 2 + cy * s)
        px = H / 1920

        halb_b, halb_h = wkm / 2 * 1.1, wkm * H / W / 2 * 1.1
        sicht = (cx - halb_b, cx + halb_b, cy - halb_h, cy + halb_h)

        def zu_sehen(box) -> bool:
            return not (box[1] < sicht[0] or box[0] > sicht[1] or box[3] < sicht[2] or box[2] > sicht[3])

        def pfad(*teile) -> bool:
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

        def bildpunkt(kx, ky):
            return W / 2 + (kx - cx) * s, H / 2 - (ky - cy) * s

        umk_kanten = [u["kante"] for e in self.ebenen for u in e["umkaempft"]]

        def radieren(breite_px=6):
            """Entfernt an der äußeren Kante umkämpfter Gebiete die Grenzlinien – 1920 gab es dort keine Grenze."""
            if umk_kanten and pfad(*umk_kanten):
                ctx.save()
                ctx.set_operator(cairo.OPERATOR_CLEAR)
                ctx.set_line_width(breite_px * px)
                ctx.stroke()
                ctx.restore()

        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)

        # Meer mit Wasserlinien entlang der Küste (klassischer Kupferstich-Effekt)
        ctx.set_source_rgb(*MEER)
        ctx.paint()
        land_sichtbar = pfad(*self.pfad_land)
        if land_sichtbar:
            for breite_px in (30, 19, 10):
                ctx.set_source_rgba(*WASSERLINIE, 0.8)
                ctx.set_line_width(breite_px * px)
                ctx.stroke_preserve()
                ctx.set_source_rgb(*MEER)
                ctx.set_line_width((breite_px - 2.2) * px)
                ctx.stroke_preserve()
            ctx.set_source_rgb(*PAPIER)
            ctx.fill()

        # Zeitablauf
        einblenden = _weich((t - self.von - 0.3) / 1.4)       # Flächen und Grenzen erscheinen
        hervor_ein = _weich((t - self.von - 1.0) / 1.8)        # Hervorhebung erscheint
        if len(self.ebenen) == 1:
            anteile = [1.0]
            w_fort = 0.0
        else:
            w0 = self.wechsel_bei - self.WECHSEL_DAUER / 2 + 0.5
            a = _weich((t - w0) / self.WECHSEL_DAUER)
            anteile = [1.0 - a, a]
            w_fort = min(1.0, max(0.0, (t - w0) / (self.WECHSEL_DAUER + 1.2)))

        hat_fokus = any(e["hervor"] for e in self.ebenen)
        zurueck = 0.7 * hervor_ein if hat_fokus else 0.0
        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        for ebene, anteil in zip(self.ebenen, anteile):
            if anteil <= 0.002:
                continue
            ctx.push_group()
            # 1) Flächen in Pastell – Nachbarn treten zurück, sobald hervorgehoben wird
            for land in ebene["laender"]:
                if pfad(land["teil"]):
                    ctx.set_source_rgb(*_mischen(land["farbe"], ZURUECK, zurueck))
                    ctx.fill()
            # 2) Grenzkolorit: kräftigerer Farbstreifen an der Innenseite der Grenze
            for land in ebene["laender"]:
                if pfad(land["teil"]):
                    ctx.save()
                    ctx.clip_preserve()
                    ctx.set_source_rgba(*_kraeftiger(land["farbe"]), 0.6 * (1 - 0.75 * zurueck))
                    ctx.set_line_width(12 * px)
                    ctx.stroke()
                    ctx.restore()
            # 3) Grenzlinien – deutlich sichtbar
            genaue = [l["teil"] for l in ebene["laender"] if l["genau"]]
            ungefaehre = [l["teil"] for l in ebene["laender"] if not l["genau"]]
            ctx.set_source_rgba(*GRENZE, 0.9)
            ctx.set_line_width(2.0 * px)
            if pfad(*genaue):
                ctx.stroke()
            ctx.set_dash([6 * px, 4 * px])
            if pfad(*ungefaehre):
                ctx.stroke()
            ctx.set_dash([])
            radieren()
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(anteil * einblenden)

        # Gradnetz, Seen, Flüsse, Küstenlinie
        if pfad(*self.pfad_gradnetz):
            ctx.set_source_rgba(*GRADNETZ, 0.22)
            ctx.set_line_width(1.0 * px)
            ctx.stroke()
        if pfad(*self.pfad_seen):
            ctx.set_source_rgb(*MEER)
            ctx.fill_preserve()
            ctx.set_source_rgba(*KUESTE, 0.8)
            ctx.set_line_width(1.0 * px)
            ctx.stroke()
        if pfad(*self.pfad_fluesse):
            ctx.set_source_rgba(*FLUSS, 0.9)
            ctx.set_line_width(1.4 * px)
            ctx.stroke()
        if land_sichtbar and pfad(*self.pfad_land):
            ctx.set_source_rgba(*KUESTE, 0.9)
            ctx.set_line_width(1.3 * px)
            ctx.stroke()

        # Hervorhebungen
        ctx.push_group()
        for i, (ebene, anteil) in enumerate(zip(self.ebenen, anteile)):
            if anteil <= 0.002 or not ebene["hervor"]:
                continue
            for hv in ebene["hervor"]:
                if not pfad(hv["teil"]):
                    continue
                farbe = hv["h"].farbe
                ctx.set_source_rgba(*farbe, 0.62 * hervor_ein * anteil)
                ctx.fill_preserve()
                ctx.save()
                ctx.clip_preserve()
                ctx.set_source_rgba(*_kraeftiger(farbe, 0.8), 0.75 * hervor_ein * anteil)
                ctx.set_line_width(22 * px)
                ctx.stroke_preserve()
                ctx.restore()
                # kräftige Grenzlinie – zeichnet sich bei Szenenbeginn bzw. Wechsel sichtbar ein
                fortschritt = hervor_ein if (i == 0 or len(self.ebenen) == 1) else w_fort
                laenge_px = max(hv["laenge"] * s, 1.0)
                ctx.set_source_rgba(*_kraeftiger(farbe, 0.42), 0.95 * min(1.0, anteil * 1.6))
                ctx.set_line_width(4.2 * px)
                ctx.set_dash([max(0.01, fortschritt * laenge_px), laenge_px + 10])
                ctx.stroke()
                ctx.set_dash([])
        radieren(26)
        ctx.pop_group_to_source()
        ctx.paint()

        # Umkämpfte Gebiete: keine Grenzlinie, Farbe des Nachbarstaats läuft aus, Sepia-Schraffur
        for ebene, anteil in zip(self.ebenen, anteile):
            st = anteil * einblenden
            if st <= 0.002:
                continue
            for u in ebene["umkaempft"]:
                if not u["start"] or not u["ende"]:
                    continue
                x0, y0 = bildpunkt(*u["start"])
                x1, y1 = bildpunkt(*u["ende"])
                # vom festen Gebiet aus zunehmend zurückgenommen und schraffiert – keine Grenzlinie
                aufhellen = cairo.LinearGradient(x0, y0, x1, y1)
                aufhellen.add_color_stop_rgba(0, *ZURUECK, 0.0)
                aufhellen.add_color_stop_rgba(0.22, *ZURUECK, 0.62 * st)
                aufhellen.add_color_stop_rgba(1, *ZURUECK, 0.86 * st)
                maske = cairo.LinearGradient(x0, y0, x1, y1)
                maske.add_color_stop_rgba(0, 0, 0, 0, 0.0)
                maske.add_color_stop_rgba(0.2, 0, 0, 0, 0.5 * st)
                maske.add_color_stop_rgba(1, 0, 0, 0, 0.6 * st)
                if not pfad(u["teil"]):
                    continue
                ctx.save()
                ctx.clip()
                ctx.set_source(aufhellen)
                ctx.paint()
                ctx.set_source(self._schraffur_umkaempft)
                ctx.mask(maske)
                ctx.restore()
                # äußere Kante nur gepunktet: die erst 1921 in Riga festgelegte Linie
                if pfad(u["kante"]):
                    ctx.set_source_rgba(*UMKAEMPFT, 0.85 * st)
                    ctx.set_line_width(2.6 * px)
                    ctx.set_dash([0.1, 7 * px])
                    ctx.stroke()
                    ctx.set_dash([])


        # Abgetretene Gebiete (früher Teil der Hervorhebung, jetzt nicht mehr): rot schraffiert
        if len(self.ebenen) > 1 and anteile[1] > 0.002 and self.ebenen[0]["hervor"]:
            alt = [hv["teil"] for hv in self.ebenen[0]["hervor"]]
            neu = [hv["teil"] for hv in self.ebenen[1]["hervor"]]
            if pfad(*alt):
                ctx.save()
                ctx.clip()  # nur innerhalb der früheren Fläche …
                if neu and pfad(*neu):
                    # … und außerhalb der neuen (Gegenfläche über einen großen Rahmen)
                    ctx.rectangle(-10, -10, W + 20, H + 20)
                    ctx.clip()
                ctx.set_source(self._schraffur_muster)
                ctx.paint_with_alpha(0.8 * _weich(anteile[1] * 1.2))
                ctx.restore()

        # Frühere Grenze nach dem Wechsel: rot gestrichelt sichtbar lassen
        if len(self.ebenen) > 1 and anteile[1] > 0.002:
            for hv in self.ebenen[0]["hervor"]:
                if pfad(hv["teil"]):
                    ctx.set_source_rgba(*ALTE_GRENZE, 0.95 * _weich(anteile[1] * 1.3))
                    ctx.set_line_width(3.2 * px)
                    ctx.set_dash([11 * px, 7 * px])
                    ctx.stroke()
                    ctx.set_dash([])

        # Historische Zonen (Abstimmungsgebiete, Übergaben)
        zonen_ein = _weich((t - self.von - 2.0) / 1.5)
        for ebene, anteil in zip(self.ebenen, anteile):
            st = anteil * zonen_ein
            if st <= 0.002:
                continue
            for z in ebene["zonen"]:
                if not pfad(z["teil"]):
                    continue
                if z["k"].get("stil") == "uebergabe":
                    ctx.save()
                    ctx.clip_preserve()
                    ctx.set_source(self._schraffur_muster)
                    ctx.paint_with_alpha(0.75 * st)
                    ctx.restore()
                    farbe_linie = ALTE_GRENZE
                else:
                    ctx.set_source_rgba(*ZONE, 0.10 * st)
                    ctx.fill_preserve()
                    farbe_linie = ZONE
                ctx.set_source_rgba(*farbe_linie, 0.95 * st)
                ctx.set_line_width(3.0 * px)
                ctx.set_dash([12 * px, 6 * px])
                ctx.stroke()
                ctx.set_dash([])

        # --- Beschriftung: kollisionsfrei, nach Wichtigkeit -----------------------
        belegung = _Belegung(W, H, 24 * px)
        for e in self._einblendungen:  # Kartusche freihalten
            if e.staerke(t) > 0.01:
                belegung.belegen(e.x, e.y, e.bild.width, e.bild.height)
        sprites = []  # (Sprite, x, y, alpha)

        # 1) Orte: Punkt + Name (rechts, sonst links)
        nah = _weich((ORTE_AB_KM - wkm) / (0.35 * ORTE_AB_KM))
        punkte = []
        for i, (name, (ox, oy)) in enumerate(self.orte):
            a = min(nah, _weich((t - self.von - 1.6 - 0.5 * i) / 0.9))
            if a <= 0:
                continue
            x, y = bildpunkt(ox, oy)
            if not (30 * px < x < W - 30 * px and 30 * px < y < H - 30 * px):
                continue
            spr = texte.kartenbeschriftung(name, "ort", H)
            for lx in (x + 8 * px, x - 8 * px - spr.width):
                ly = y - spr.height / 2 - 2 * px
                if belegung.frei(lx + 10 * px, ly + 10 * px, spr.width - 20 * px, spr.height - 20 * px):
                    belegung.belegen(lx + 10 * px, ly + 10 * px, spr.width - 20 * px, spr.height - 20 * px)
                    belegung.belegen(x - 10 * px, y - 10 * px, 20 * px, 20 * px)
                    punkte.append((x, y, a))
                    sprites.append((spr, lx, ly, a))
                    break

        def setzen(spr, mx, my, st, versaetze=(0, 0.9, -0.9)):
            kandidaten = [(0, dy) for dy in versaetze] + [(dx, dy) for dx in (-0.45, 0.45) for dy in (0, 1.0, -1.0)]
            for dx, dy in kandidaten:
                lx = mx - spr.width / 2 + dx * spr.width
                ly = my - spr.height / 2 + dy * spr.height
                rand = 12 * px
                if belegung.frei(lx + rand, ly + rand, spr.width - 2 * rand, spr.height - 2 * rand):
                    belegung.belegen(lx + rand, ly + rand, spr.width - 2 * rand, spr.height - 2 * rand)
                    sprites.append((spr, lx, ly, st))
                    return True
            return False

        # 2a) Umkämpfte Gebiete (wichtiger als Ländernamen)
        for ebene, anteil in zip(self.ebenen, anteile):
            st = anteil * einblenden
            if st > 0.01:
                for u in ebene["umkaempft"]:
                    if u["mitte"] is None:
                        continue
                    titel, _, unter = u["text"].partition("|")
                    spr = texte.zonenbeschriftung(titel, unter, H, tuple(int(c * 255) for c in UMKAEMPFT))
                    setzen(spr, *bildpunkt(*u["mitte"]), st, (0, 1.0, -1.0, 2.0, -2.0))

        # 2) Hervorgehobene Gebiete: Name im Gebiet, notfalls leicht versetzt.
        #    Gleichnamige Beschriftung in beiden Ständen nur einmal (vom überwiegenden Stand).
        reihenfolge = sorted(range(len(self.ebenen)), key=lambda k: -anteile[k])
        gesetzt = set()
        for k in reihenfolge:
            ebene, anteil = self.ebenen[k], anteile[k]
            for hv in ebene["hervor"]:
                h, mitte = hv["h"], hv["mitte"]
                gleich_in_allen = all(any(x["h"].beschriftung == h.beschriftung for x in e["hervor"])
                                      for e in self.ebenen)
                st = (1.0 if gleich_in_allen else anteil) * hervor_ein
                if not h.beschriftung or mitte is None or st <= 0.01 or h.beschriftung in gesetzt:
                    continue
                gesetzt.add(h.beschriftung)
                spr = texte.kartenbeschriftung(h.beschriftung, "land", H,
                                               tuple(int(c * 255) for c in _kraeftiger(h.farbe, 0.4)))
                mx, my = bildpunkt(*mitte)
                for dy in (0, 0.9, -0.9, 1.8, -1.8):
                    lx, ly = mx - spr.width / 2, my - spr.height / 2 + dy * spr.height
                    if belegung.frei(lx + 12 * px, ly + 12 * px, spr.width - 24 * px, spr.height - 24 * px):
                        belegung.belegen(lx + 12 * px, ly + 12 * px, spr.width - 24 * px, spr.height - 24 * px)
                        sprites.append((spr, lx, ly, st))
                        break

        # 3) Zonen, umkämpfte Gebiete und Vermerke
        for ebene, anteil in zip(self.ebenen, anteile):
            st = anteil * zonen_ein
            if st > 0.01:
                for z in ebene["zonen"]:
                    if z["mitte"] is None:
                        continue
                    farbe = tuple(int(c * 255) for c in (ALTE_GRENZE if z["k"].get("stil") == "uebergabe" else ZONE))
                    spr = texte.zonenbeschriftung(z["k"]["titel"], z["k"].get("unterzeile", ""), H, farbe)
                    setzen(spr, *bildpunkt(*z["mitte"]), st, (0, 1.0, -1.0, 1.8))
        vermerk_ein = einblenden * hervor_ein
        if self.vermerke_ab is not None:  # erst ab dem passenden Satz der Erzählung
            vermerk_ein *= _weich((t - self.vermerke_ab) / 1.0)
        for text, (vx, vy) in self.ebenen[0]["vermerke"]:  # Vermerke gelten für die ganze Szene
            if vermerk_ein > 0.01:
                setzen(texte.vermerk(text, H), *bildpunkt(vx, vy), vermerk_ein)

        # 4) Nachbarn: zurückhaltend, nur wenn nah genug und das Gebiet groß genug ist
        nachbar_nah = _weich((NACHBARN_AB_KM - wkm) / (0.3 * NACHBARN_AB_KM))
        for ebene, anteil in zip(self.ebenen, anteile):
            st = anteil * einblenden * nachbar_nah
            if st <= 0.01:
                continue
            for text, mitte, box in ebene["nachbarn"]:
                if mitte is None:
                    continue
                spr = texte.kartenbeschriftung(text, "nachbar", H)
                if (box[1] - box[0]) * s < spr.width * 0.9:
                    continue  # Gebiet zu klein für eine lesbare Beschriftung
                mx, my = bildpunkt(*mitte)
                lx, ly = mx - spr.width / 2, my - spr.height / 2
                if belegung.frei(lx + 12 * px, ly + 12 * px, spr.width - 24 * px, spr.height - 24 * px):
                    belegung.belegen(lx + 12 * px, ly + 12 * px, spr.width - 24 * px, spr.height - 24 * px)
                    sprites.append((spr, lx, ly, st))

        for x, y, a in punkte:
            ctx.arc(x, y, 9.5 * px, 0, 2 * math.pi)
            ctx.set_source_rgba(*PAPIER, 0.9 * a)
            ctx.fill()
            ctx.arc(x, y, 6.5 * px, 0, 2 * math.pi)
            ctx.set_source_rgba(*TINTE, a)
            ctx.set_line_width(2.2 * px)
            ctx.stroke()
            ctx.arc(x, y, 2.6 * px, 0, 2 * math.pi)
            ctx.fill()

        flaeche.flush()
        bild = Image.frombuffer("RGB", (W, H), bytes(flaeche.get_data()), "raw", "BGRX", flaeche.get_stride(), 1)
        for spr, x, y, a in sprites:
            self._kleben(bild, spr, x, y, a)
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
