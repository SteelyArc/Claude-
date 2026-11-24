"""Historical geometry for the Partitions of Poland-Lithuania (1772 / 1793 / 1795).

All coordinates are (lon, lat). Borders are APPROXIMATE reconstructions: outer
frontiers are traced through towns documented on each side of the line, and
partition lines follow the rivers named in the treaties, snapped to Natural
Earth river geometry where available (Daugava/Dvina, Dnieper, Vistula, Bug,
Neman). Expect +/- 10-40 km error. Maps must be labelled "approximate borders".
"""
import json, os
from functools import lru_cache
from shapely.geometry import shape, Polygon, Point, LineString, MultiPolygon
from shapely.ops import linemerge, substring, unary_union

GEO = os.environ.get("GEO_DIR", os.path.join(os.path.dirname(__file__), "..", "assets", "geo"))


@lru_cache(None)
def land():
    d = json.load(open(os.path.join(GEO, "ne_10m_land.geojson")))
    clip = Polygon([(0, 36), (50, 36), (50, 66), (0, 66)])
    return unary_union([shape(f["geometry"]).intersection(clip) for f in d["features"]
                        if shape(f["geometry"]).intersects(clip)])


@lru_cache(None)
def lakes():
    d = json.load(open(os.path.join(GEO, "ne_10m_lakes.geojson")))
    clip = Polygon([(0, 36), (50, 36), (50, 66), (0, 66)])
    return unary_union([shape(f["geometry"]) for f in d["features"] if shape(f["geometry"]).intersects(clip)])


@lru_cache(None)
def rivers():
    d = json.load(open(os.path.join(GEO, "ne_10m_rivers_lake_centerlines.geojson")))
    clip = Polygon([(0, 36), (50, 36), (50, 66), (0, 66)])
    out = {}
    for f in d["features"]:
        n = f["properties"].get("name")
        g = shape(f["geometry"])
        if n and g.intersects(clip):
            out.setdefault(n, []).append(g)
    res = {}
    for n, gs in out.items():
        lines = []
        for g in gs:
            lines += list(g.geoms) if g.geom_type == "MultiLineString" else [g]
        res[n] = linemerge(lines)
    # Dnieper is split under two spellings in Natural Earth
    if "Dnepre" in res and "Dnipro" in res:
        a, b = res.pop("Dnepre"), res.pop("Dnipro")
        la = list(a.geoms) if a.geom_type.startswith("Multi") else [a]
        lb = list(b.geoms) if b.geom_type.startswith("Multi") else [b]
        res["Dnieper"] = linemerge(la + lb)
    return res


def river_seg(name, a, b):
    """Coordinates of river `name` between the points nearest to a and b, ordered a->b."""
    g = rivers()[name]
    parts = list(g.geoms) if g.geom_type == "MultiLineString" else [g]
    pa, pb = Point(a), Point(b)
    line = min(parts, key=lambda p: p.distance(pa) + p.distance(pb))
    da, db = line.project(pa), line.project(pb)
    seg = substring(line, min(da, db), max(da, db))
    c = list(seg.coords)
    return c if da <= db else c[::-1]


# ---------------------------------------------------------------------------
# Outer frontier of the Commonwealth c. 1764-1772 (excluding the Duchy of Courland)
# ---------------------------------------------------------------------------
def _plc_outline():
    west_and_south = [
        (17.55, 55.10),                 # at sea, off the Leba (Pomerelia / Lauenburg line)
        (17.55, 54.78), (17.62, 54.35), (17.55, 54.05),   # Lebork & Bytow were Brandenburg fiefs
        (17.15, 53.85), (16.85, 53.62), (16.50, 53.48), (16.25, 53.30),  # Czluchow, Walcz Polish
        (16.05, 53.10), (15.85, 52.95), (15.55, 52.75), (15.40, 52.62),  # Drezdenko, Skwierzyna Polish
        (15.45, 52.38), (15.65, 52.18), (15.95, 52.02), (16.15, 51.83),  # Miedzyrzecz, Babimost, Wschowa
        (16.55, 51.70), (16.85, 51.55), (17.30, 51.48), (17.70, 51.35),  # Leszno, Rawicz, Ostrzeszow
        (18.05, 51.18), (18.35, 51.05), (18.65, 50.88), (18.85, 50.62),  # Wielun, Krzepice
        (19.05, 50.45), (19.12, 50.30), (19.10, 50.05), (19.05, 49.85),  # Siewierz, Bedzin; Przemsza line
        (19.00, 49.60), (19.20, 49.40), (19.65, 49.38), (19.95, 49.25),  # Zywiec; Orava; Tatras
        (20.35, 49.30), (20.75, 49.37), (21.25, 49.42), (21.80, 49.35),  # Carpathian crest
        (22.40, 49.10), (22.85, 48.95), (23.35, 48.80), (23.85, 48.52),
        (24.30, 48.22), (24.70, 47.95), (24.95, 47.95), (25.20, 48.22),  # Pokuttya / Cheremosh
        (25.55, 48.42), (25.78, 48.60),                                    # Sniatyn -> Dniester
        (26.30, 48.55), (26.80, 48.45), (27.50, 48.47), (27.80, 48.45),  # Dniester (Moldavia)
        (28.28, 48.24), (28.80, 47.95), (29.15, 47.55), (29.40, 47.45),  # Yampil, Rybnytsia, Yahorlyk mouth
        (29.70, 47.75), (30.20, 47.90), (30.85, 48.05),                    # Kodyma -> S. Bug (Ottoman Yedisan)
        (31.30, 48.50), (31.80, 48.90), (32.20, 49.15), (32.45, 49.30),  # New Serbia frontier / Tiasmyn
        (32.10, 49.45), (31.50, 49.75), (31.00, 50.05),                    # Dnieper: Cherkasy, Kaniv (Polish)
        (30.40, 50.10), (30.10, 50.32), (30.20, 50.65), (30.50, 50.85),  # around the Russian Kiev enclave
        (30.50, 51.20), (30.60, 51.60), (30.75, 51.90),                    # Dnieper northward
        (31.20, 52.00), (31.75, 52.20), (31.75, 52.80), (32.20, 53.20),  # Gomel, Chechersk Lithuanian
        (32.30, 53.60), (32.00, 54.10), (31.40, 54.50), (31.00, 54.75),  # Krichev, Mstsislaw; Smolensk Russian
        (31.20, 55.10), (31.25, 55.60), (31.05, 55.95), (30.40, 56.15),  # Velizh Lithuanian
        (29.90, 56.20), (29.20, 56.30), (28.70, 56.45), (28.25, 56.70),  # Nevel, Sebezh Polish; Opochka Russian
        (27.95, 56.95), (27.65, 57.25), (27.20, 57.28), (26.70, 57.15),  # Polish Livonia (Inflanty)
        (26.20, 56.85), (25.80, 56.64),                                    # Aiviekste -> Daugava
    ]
    dvina_courland = river_seg("Daugava", (25.75, 56.62), (26.40, 55.88))   # Selonia (Courland) south bank
    courland_border = [
        (26.20, 55.80), (25.80, 56.00), (25.00, 56.15), (24.20, 56.25),
        (23.50, 56.30), (22.60, 56.35), (21.80, 56.22), (21.20, 56.07), (20.80, 56.05),  # Sventoji
    ]
    samogitia_prussia = [
        (20.85, 55.75), (21.22, 55.74), (21.60, 55.55), (21.90, 55.30),  # Memel (Klaipeda) Prussian
        (22.30, 55.15), (22.60, 55.07), (22.85, 54.92), (22.85, 54.60),  # Smalininkai; Jurbarkas Lithuanian
        (22.75, 54.40), (22.55, 54.10), (22.40, 53.75), (22.10, 53.55),  # Vistytis, Filipow; Lyck Prussian
        (21.70, 53.45), (21.20, 53.35), (20.65, 53.22), (20.20, 53.24),  # Kolno, Myszyniec, Chorzele; Soldau
        (19.85, 53.40), (19.55, 53.50), (19.30, 53.55), (19.05, 53.62),  # Lubawa Polish; Ilawa Prussian
        (18.85, 53.68), (18.88, 53.95),                                    # Vistula opposite Kwidzyn
        (19.20, 53.92), (19.50, 53.96), (19.70, 54.02),                    # Malbork, Elblag Polish
        (19.90, 53.98), (20.15, 53.80), (20.40, 53.60), (20.75, 53.62),  # Warmia (Prince-Bishopric)
        (21.10, 53.80), (21.22, 54.05), (20.90, 54.20), (20.40, 54.30),  # Olsztyn, Reszel, Lidzbark
        (20.10, 54.42), (20.10, 54.75), (18.90, 54.95), (17.55, 55.10),  # Braniewo; out to sea
    ]
    ring = west_and_south + dvina_courland + courland_border + samogitia_prussia
    return Polygon(ring).buffer(0)


def _courland():
    dvina = river_seg("Daugava", (24.05, 57.03), (26.40, 55.88))
    border = [(26.20, 55.80), (25.80, 56.00), (25.00, 56.15), (24.20, 56.25),
              (23.50, 56.30), (22.60, 56.35), (21.80, 56.22), (21.20, 56.07), (20.80, 56.05)]
    sea = [(20.5, 56.0), (20.6, 57.9), (22.7, 57.9), (23.5, 57.3), (24.05, 57.2)]
    return Polygon(dvina + border + sea).buffer(0)


# ---------------------------------------------------------------------------
# Partition cut-lines
# ---------------------------------------------------------------------------
def _cut_1772_russia():
    # Daugava (Dvina) from the Courland frontier up to the mouth of the Ula,
    # overland to the Drut, down the Drut to Rogachev, then down the Dnieper.
    dv = river_seg("Daugava", (25.72, 56.62), (29.25, 55.20))
    drut = [(29.15, 54.95), (29.20, 54.70), (29.55, 54.45), (29.70, 54.20),
            (29.72, 53.95), (29.82, 53.60), (29.92, 53.32), (30.05, 53.13)]
    dn = river_seg("Dnieper", (30.05, 53.13), (30.80, 51.85))
    close = [(31.6, 51.70), (34, 51.7), (34, 58.5), (25.0, 58.5), (25.0, 56.9)]
    return Polygon(dv + drut + dn + close).buffer(0)


def _cut_1772_prussia():
    # Royal Prussia (minus Gdansk & Torun), Warmia, and the Notec (Netze) district.
    line = [(15.30, 52.70), (16.17, 52.86), (16.56, 52.86), (16.75, 52.98), (17.20, 53.00),
            (17.60, 53.05), (17.95, 52.95), (18.05, 52.72), (18.40, 52.68), (18.62, 52.92),
            (18.75, 53.04), (19.00, 53.10), (19.25, 53.14), (19.50, 53.18), (19.80, 53.20), (20.30, 53.22)]
    close = [(21.5, 53.5), (21.5, 55.5), (15.0, 55.5)]
    return Polygon(line + close).buffer(0)


def _cut_1772_austria():
    vis = river_seg("Vistula", (19.15, 50.00), (21.86, 50.80))
    east = [(22.20, 50.86), (22.65, 50.95), (23.15, 50.98), (23.60, 50.92), (24.05, 50.80),
            (24.40, 50.55), (24.80, 50.25), (25.15, 50.10), (25.60, 49.95), (25.98, 49.72),
            (26.08, 49.35), (26.12, 48.95), (26.30, 48.58), (26.4, 48.0)]
    close = [(18.5, 47.5), (18.5, 50.0)]
    return Polygon(vis + east + close).buffer(0)


GDANSK = Point(18.65, 54.35).buffer(0.17)
TORUN = Point(18.60, 53.01).buffer(0.10)


def _cut_1793_russia():
    line = [(27.45, 56.2), (27.45, 55.79), (27.00, 55.30), (26.75, 54.85), (26.60, 54.30),
            (26.55, 53.80), (26.60, 53.20), (26.30, 52.60), (26.10, 52.12), (26.25, 51.60),
            (26.30, 51.10), (26.35, 50.60), (26.20, 50.20), (26.05, 49.80), (26.1, 47.5)]
    close = [(34, 47.5), (34, 56.2)]
    return Polygon(line + close).buffer(0)


def _cut_1793_prussia():
    line = [(18.9, 50.2), (19.30, 50.50), (19.55, 50.90), (19.90, 51.30), (20.25, 51.75),
            (20.45, 52.10), (20.40, 52.50), (20.30, 52.90), (20.18, 53.30)]
    close = [(20.2, 55.5), (14.5, 55.5), (14.5, 50.2)]
    return Polygon(line + close).buffer(0)


def _cut_1795_austria():
    pilica = [(19.40, 50.45), (19.82, 50.63), (19.88, 51.08), (19.88, 51.35), (20.00, 51.53),
              (20.25, 51.62), (20.58, 51.62), (20.90, 51.70), (21.19, 51.80)]
    vis = river_seg("Vistula", (21.20, 51.83), (21.10, 52.15))
    link = [(21.40, 52.35), (21.75, 52.58)]
    bug = river_seg("Bug", (21.85, 52.62), (24.10, 50.55))
    close = [(24.5, 50.3), (24.5, 47.5), (18.5, 47.5), (18.5, 50.3)]
    return Polygon(pilica + vis + link + bug + close).buffer(0)


def _cut_1795_prussia():
    line = [(23.25, 51.0), (23.25, 52.28), (23.50, 52.80), (23.70, 53.30)]
    nem = river_seg("Neman", (23.83, 53.68), (22.55, 55.08))
    close = [(22.3, 55.6), (14.5, 55.6), (14.5, 51.0)]
    return Polygon(line + nem + close).buffer(0)


@lru_cache(None)
def build():
    L = land()
    plc = _plc_outline().intersection(L)
    cour = _courland().intersection(L).difference(plc)
    r72 = plc.intersection(_cut_1772_russia())
    p72 = plc.intersection(_cut_1772_prussia()).difference(GDANSK).difference(TORUN).difference(r72)
    a72 = plc.intersection(_cut_1772_austria()).difference(r72).difference(p72)
    pol72 = plc.difference(unary_union([r72, p72, a72]))
    r93 = pol72.intersection(_cut_1793_russia())
    p93 = pol72.intersection(unary_union([_cut_1793_prussia(), GDANSK, TORUN])).difference(r93)
    pol93 = pol72.difference(unary_union([r93, p93]))
    a95 = pol93.intersection(_cut_1795_austria())
    p95 = pol93.difference(a95).intersection(_cut_1795_prussia())
    r95 = pol93.difference(unary_union([a95, p95]))
    return dict(plc=plc, courland=cour, r72=r72, p72=p72, a72=a72, pol72=pol72,
                r93=r93, p93=p93, pol93=pol93, r95=r95, p95=p95, a95=a95)


CITIES = {
    "Warsaw": (21.01, 52.23), "Kraków": (19.94, 50.06), "Vilnius": (25.28, 54.69),
    "Gdańsk": (18.65, 54.35), "Toruń": (18.60, 53.01), "Poznań": (16.93, 52.41),
    "Lwów": (24.03, 49.84), "Minsk": (27.56, 53.90), "Kyiv": (30.52, 50.45),
    "Riga": (24.10, 56.95), "Königsberg": (20.51, 54.71), "Berlin": (13.40, 52.52),
    "Vienna": (16.37, 48.21), "Smolensk": (32.05, 54.78), "Grodno": (23.83, 53.68),
    "Polotsk": (28.80, 55.49), "Mogilev": (30.33, 53.90), "Lublin": (22.57, 51.25),
}

if __name__ == "__main__":
    import pyproj
    from shapely.ops import transform
    g = build()
    geod = pyproj.Geod(ellps="WGS84")
    area = {k: abs(geod.geometry_area_perimeter(v)[0]) / 1e6 for k, v in g.items()}
    for k, v in area.items():
        print(f"{k:9s} {v:10,.0f} km2")
    tot = area["plc"]
    for k in ["r72", "p72", "a72", "r93", "p93", "r95", "p95", "a95"]:
        print(k, f"{100*area[k]/tot:.1f}% of 1772 area")
    tests = {"Gdańsk": "p93", "Toruń": "p93", "Kraków": "a95", "Lwów": "a72", "Warsaw": "p95",
             "Vilnius": "r95", "Minsk": "r93", "Polotsk": "r72", "Mogilev": "r72", "Poznań": "p93",
             "Grodno": "r95", "Lublin": "a95"}
    for c, exp in tests.items():
        got = [k for k in ["r72", "p72", "a72", "r93", "p93", "r95", "p95", "a95"] if g[k].buffer(0.05).contains(Point(CITIES[c]))]
        print(("OK  " if got == [exp] else "FAIL"), c, "expected", exp, "got", got)
