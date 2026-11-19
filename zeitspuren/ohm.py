"""Tagesgenaue Detailgrenzen aus OpenHistoricalMap (OHM, CC0).

Für die Staaten in ``daten/karten/ohm/staaten.json`` ersetzen die OHM-Flächen
im Zeitraum ihrer Gültigkeit die gröberen CShapes-Flächen. Nachbarn aus
CShapes werden an den OHM-Flächen beschnitten, damit sich nichts überlagert.

Offene Grenzen (z. B. Polens Ostgrenze 1920): OHM lässt die Grenze bewusst
offen, wo sie historisch nicht feststand. Der festgelegte Teil wird mit der
Verbindungslinie seiner Endpunkte geschlossen; was darüber hinaus bis zur
späteren Ausdehnung ('huelle') reicht, wird als *umkämpft* gekennzeichnet –
ohne eine erfundene Grenzlinie zu zeichnen.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.ops import polygonize, unary_union

ORDNER = Path(__file__).resolve().parent.parent / "daten" / "karten" / "ohm"


@lru_cache(maxsize=1)
def _staaten() -> list[dict]:
    return json.loads((ORDNER / "staaten.json").read_text(encoding="utf-8"))["staaten"]


@lru_cache(maxsize=1)
def zonen_konfig() -> dict:
    return json.loads((ORDNER / "zonen.json").read_text(encoding="utf-8"))["zonen"]


@lru_cache(maxsize=64)
def _datei(nummer: str) -> dict:
    return json.loads((ORDNER / f"{nummer}.geojson").read_text(encoding="utf-8"))


VEREINFACHUNG = 0.003  # Grad ≈ 0,2–0,3 km: unterhalb eines Bildpunkts bei Kartenbreiten ≥ 300 km


@lru_cache(maxsize=64)
def _form(nummer: str):
    return shape(_datei(nummer)["geometry"]).simplify(VEREINFACHUNG, preserve_topology=True)


def _gueltig(version: dict, tag: str) -> bool:
    return version["von"] <= tag < version["bis"]


def staaten_am(tag: str) -> list[dict]:
    """Liste der OHM-Staaten an einem Tag: name, anzeigename, form, ersetzt, umkaempft(form, text)."""
    ergebnis = []
    for staat in _staaten():
        for v in staat["versionen"]:
            if not _gueltig(v, tag):
                continue
            eintrag = {"name": v.get("anzeigename", staat["name"]), "ersetzt": staat["ersetzt"],
                       "datei": v["datei"], "umkaempft": None, "warnung": v.get("warnung")}
            if v.get("datei_flaeche"):
                eintrag["form"] = _form(v["datei_flaeche"])
                eintrag["offen_ohne_zone"] = True
            elif v.get("offen"):
                huelle = _form(v["huelle"])
                eintrag["form"] = huelle
                eintrag["offen"] = v
            else:
                eintrag["form"] = _form(v["datei"])
            ergebnis.append(eintrag)
            break
    # Offene Staaten: Hülle um die anderen OHM-Staaten verkleinern, umkämpften Teil bestimmen
    feste = unary_union([e["form"] for e in ergebnis if not e.get("offen") and not e.get("offen_ohne_zone")])
    for e in ergebnis:
        if e.get("offen_ohne_zone"):
            e["form"] = e["form"].difference(feste)
    for e in ergebnis:
        if not e.get("offen"):
            continue
        v = e["offen"]
        flaeche = e["form"].difference(feste)
        enden = _datei(v["datei"])["properties"].get("offene_enden") or []
        festgelegt = _festgelegter_teil(flaeche, enden)
        if festgelegt is not None:
            umk = flaeche.difference(festgelegt.buffer(0))
            umk = _nur_grosse_teile(umk, 0.02)
            if not umk.is_empty:
                # Äußere Kante der Zone (ohne die Hilfssehne zum festen Gebiet) und Verlaufsrichtung
                kante = umk.boundary.difference(festgelegt.buffer(0.02))
                from shapely.ops import nearest_points
                kern = festgelegt.representative_point()
                start = nearest_points(umk, kern)[0]
                ende = max((Point(c) for g in getattr(umk, "geoms", [umk]) for c in g.exterior.coords),
                           key=lambda q: q.distance(kern))
                e["umkaempft"] = (umk, v.get("umkaempft", "Disputed|"), kante,
                                  (start.x, start.y), (ende.x, ende.y))
        e["form"] = flaeche
    return ergebnis


def _festgelegter_teil(flaeche, enden):
    """Teilt die Fläche entlang der (leicht verlängerten) Sehne zwischen den Endpunkten der
    offenen Grenzlinie. Festgelegt ist das Teilstück, an dessen Rand die belegte Grenze verläuft."""
    from shapely.geometry import Point
    from shapely.ops import split
    if len(enden) != 1 or len(enden[0]) < 3:
        return None
    (ax, ay), (bx, by), mitte = enden[0][0], enden[0][1], enden[0][2]
    dx, dy = bx - ax, by - ay
    laenge = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / laenge * 0.3, dy / laenge * 0.3
    sehne = LineString([(ax - ux, ay - uy), (bx + ux, by + uy)])
    teile = []
    for g in getattr(flaeche, "geoms", [flaeche]):
        teile.extend(getattr(split(g, sehne), "geoms", []))
    if len(teile) < 2:
        return None
    p = Point(mitte)
    teile.sort(key=lambda t: t.distance(p))
    return teile[0]


def _nur_grosse_teile(form, mindestflaeche):
    teile = [g for g in getattr(form, "geoms", [form]) if g.area >= mindestflaeche]
    return unary_union(teile) if teile else Polygon()


def warnungen_am(tag: str) -> list[str]:
    return [e["warnung"] for e in staaten_am(tag) if e.get("warnung")]


def gilt_am(tag: str) -> bool:
    return bool(staaten_am(tag))


def zone(schluessel: str):
    k = zonen_konfig()[schluessel]
    if "teile" in k:
        form = unary_union([_form(n) for n in k["teile"]])
    else:
        vorher, nachher = (_form(n) for n in k["differenz"])
        form = vorher.difference(nachher)
        if "nur_um" in k:
            form = form.intersection(box(*k["nur_um"]))
        form = _nur_grosse_teile(form, 0.01)
    return form, k


def als_polygone(form) -> list:
    """Shapely-Form → Liste von Polygonen (Ringe aus (lon, lat)), wie im Kartenmodul üblich."""
    polys = []
    for g in getattr(form, "geoms", [form]):
        if isinstance(g, (Polygon,)) and not g.is_empty:
            polys.append([list(g.exterior.coords)] + [list(r.coords) for r in g.interiors])
        elif isinstance(g, MultiPolygon):
            polys.extend(als_polygone(g))
    return polys


def kombinieren(cshapes_liste: list[dict], tag: str) -> tuple[list[dict], list[tuple]]:
    """CShapes-Gebiete und OHM-Staaten zusammenführen. Gibt (Gebiete, umkämpfte Flächen) zurück."""
    ohm = staaten_am(tag)
    if not ohm:
        return cshapes_liste, []
    ersetzt = {n for e in ohm for n in e["ersetzt"]}
    ohm_union = unary_union([e["form"] for e in ohm])
    umk_union = unary_union([e["umkaempft"][0] for e in ohm if e["umkaempft"]]) if any(
        e["umkaempft"] for e in ohm) else Polygon()
    abzug = unary_union([ohm_union, umk_union]).buffer(0)
    rahmen = abzug.envelope.buffer(3)
    neu = []
    for g in cshapes_liste:
        if g["name"] in ersetzt:
            continue
        polys = [Polygon(p[0], p[1:]) for p in g["polygone"] if len(p[0]) >= 4]
        form = unary_union([p.buffer(0) for p in polys]) if polys else Polygon()
        if form.intersects(rahmen):
            form = form.difference(abzug).simplify(VEREINFACHUNG, preserve_topology=True)
            form = _nur_grosse_teile(form, 0.002)
            if form.is_empty:
                continue
            g = dict(g, polygone=als_polygone(form))
        neu.append(g)
    for e in ohm:
        if e["form"].is_empty:
            continue
        neu.append({"name": e["name"], "genauigkeit": 3, "status": "ohm", "polygone": als_polygone(e["form"]),
                    "ohm": e["datei"]})
    umkaempft = []
    for e in ohm:
        if e["umkaempft"]:
            umk, text, kante, start, ende = e["umkaempft"]
            linien = [list(g.coords) for g in getattr(kante, "geoms", [kante]) if not g.is_empty and g.length > 0]
            umkaempft.append((als_polygone(umk), text, linien, start, ende))
    return neu, umkaempft
