"""Base geography (projected) for the West Prussia maps, with period-correct Vistula delta."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from functools import lru_cache
from shapely.geometry import LineString, box, shape
from shapely.ops import unary_union
from engine.geo import ne_clip, project, GEO
from engine.render import AtlasMap

BBOX = (2.0, 38.0, 40.0, 64.0)  # lon/lat working extent
MAJOR = {"Vistula", "Oder", "Neman", "Daugava", "Bug", "Warta", "Elbe"}
MINOR = {"Narew", "Noteć", "Drwęca", "Pilica", "San", "Łyna", "Wkra", "Gwda", "Wieprz", "Bzura",
         "Luzicka Nisa", "Spree", "Prosna", "Zakhidnyy Buh", "Pripyat", "Mukhavyets", "Neris"}
DELTA_NAMES = {"Wisła", "Nogat", "Szkarpawa", "Wisła Królewiecka", "Przekop Wisły", "Martwa Wisła",
               "Tote Weichsel", "Tote (Danziger) Weichsel", "Wisła Śmiała", "Stary Nogat"}

def _year(s, default):
    try:
        return int(str(s)[:4])
    except Exception:
        return default

@lru_cache(None)
def delta_rivers(year):
    d = json.load(open(os.path.join(GEO, "ohm", "raw", "delta_waterways_ohm.json")))
    out = []
    for e in d["elements"]:
        t = e.get("tags", {}); n = t.get("name")
        if t.get("waterway") != "river" or n not in DELTA_NAMES:
            continue
        if not (_year(t.get("start_date"), -9999) <= year < _year(t.get("end_date"), 99999)):
            continue
        if n == "Stary Nogat":
            continue
        out.append(LineString([(p["lon"], p["lat"]) for p in e["geometry"]]))
    return unary_union(out)

@lru_cache(None)
def atlas(year):
    land = unary_union([g for g, p in ne_clip("ne_10m_land", BBOX)])
    lakes = unary_union([g for g, p in ne_clip("ne_10m_lakes", BBOX)] + [g for g, p in ne_clip("ne_10m_lakes_europe", BBOX)])
    rivers = []
    for layer in ("ne_10m_rivers_lake_centerlines", "ne_10m_rivers_europe"):
        for g, p in ne_clip(layer, BBOX):
            n = p.get("name") or ""
            if n in MAJOR or n in MINOR:
                if n == "Vistula":   # NE has the modern (1895) mouth; cut it and use OHM's dated delta
                    g = g.intersection(box(14, 40, 30, 54.02))
                rivers.append((n, g, n in MAJOR))
    rivers.append(("VistulaDelta", delta_rivers(year), True))
    merged = {}
    for n, g, m in rivers:
        if n in merged:
            merged[n] = (unary_union([merged[n][0], g]), m)
        else:
            merged[n] = (g, m)
    rivers_p = [(n, project(g), m) for n, (g, m) in merged.items() if not g.is_empty]
    return AtlasMap(project(land), project(lakes), rivers_p)
