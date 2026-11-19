"""Lädt ausgewählte Grenz-Relationen aus OpenHistoricalMap (CC0) als GeoJSON.

Aufruf:  python3 werkzeuge/ohm_holen.py 2855670 2741459 ...
Jede Relation wird mit Versionsnummer und Zeitstempel gespeichert
(daten/karten/ohm/<id>.geojson), damit der Stand nachvollziehbar bleibt.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import MultiLineString, mapping
from shapely.ops import linemerge, polygonize, unary_union

ZIEL = Path(__file__).resolve().parent.parent / "daten" / "karten" / "ohm"
API = "https://overpass-api.openhistoricalmap.org/api/interpreter"


def abfragen(q: str) -> dict:
    daten = urllib.parse.urlencode({"data": q}).encode()
    anfrage = urllib.request.Request(API, data=daten, headers={"User-Agent": "zeitspuren-karten/1.0"})
    with urllib.request.urlopen(anfrage, timeout=300) as antwort:
        return json.load(antwort)


def offene_enden(rel: dict) -> list:
    """Endpunkte nicht geschlossener Grenzlinien (z. B. bewusst offene Ostgrenze Polens 1920)."""
    linien = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel.get("members", [])
              if m["type"] == "way" and "geometry" in m and m.get("role") != "inner"]
    if not linien:
        return []
    zug = linemerge(MultiLineString(linien))
    # Endpunkte jedes offenen Linienzugs plus ein Punkt in seiner Mitte (zeigt, auf welcher
    # Seite der Sehne die festgelegte Grenze verläuft)
    return [[list(g.coords[0]), list(g.coords[-1]), list(g.interpolate(0.5, normalized=True).coords[0])]
            for g in getattr(zug, "geoms", [zug]) if not g.is_ring]


def flaeche(rel: dict):
    aussen, innen = [], []
    for m in rel.get("members", []):
        if m["type"] != "way" or "geometry" not in m:
            continue
        linie = [(p["lon"], p["lat"]) for p in m["geometry"]]
        (innen if m.get("role") == "inner" else aussen).append(linie)
    form = unary_union(list(polygonize(MultiLineString(aussen))))
    if innen:
        form = form.difference(unary_union(list(polygonize(MultiLineString(innen)))))
    return form


def main(ids):
    ZIEL.mkdir(parents=True, exist_ok=True)
    q = f"[out:json][timeout:280];relation(id:{','.join(ids)});out meta geom;"
    for rel in abfragen(q)["elements"]:
        form = flaeche(rel)
        t = rel["tags"]
        eintrag = {
            "type": "Feature",
            "properties": {
                "ohm_relation": rel["id"], "ohm_version": rel.get("version"), "ohm_timestamp": rel.get("timestamp"),
                "name": t.get("name:en") or t.get("name"), "start_date": t.get("start_date"),
                "end_date": t.get("end_date"), "start_event": t.get("start_event"), "end_event": t.get("end_event"),
                "fixme": t.get("fixme"), "source": t.get("source"),
                "flaeche_gueltig": form.is_valid, "teile": 0 if form.is_empty else len(getattr(form, "geoms", [form])),
                "offene_enden": offene_enden(rel),
            },
            "geometry": mapping(form),
        }
        datei = ZIEL / f"{rel['id']}.geojson"
        datei.write_text(json.dumps(eintrag, ensure_ascii=False), encoding="utf-8")
        p = eintrag["properties"]
        print(f"{rel['id']} v{p['ohm_version']}  {p['name']}  {p['start_date']} → {p['end_date']}  "
              f"Teile={p['teile']} gültig={p['flaeche_gueltig']}  {datei.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1:])
