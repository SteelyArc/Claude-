"""Reusable geodata helpers: fetch OpenHistoricalMap relations and Natural Earth layers,
assemble polygons, project to a metric CRS. Cached on disk under data/geo/."""
import json, os, time, urllib.parse, urllib.request
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, LineString
from shapely.ops import linemerge, polygonize, unary_union, transform
from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.path.join(ROOT, "data", "geo")
OVERPASS = "https://overpass-api.openhistoricalmap.org/api/interpreter"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
UA = "HistoricalDocumentaryResearch/0.1"

def _get(url, data=None, timeout=240):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def ohm_relation(rid, retries=4):
    """Return (shapely geometry in WGS84, tags) for an OHM boundary relation (cached)."""
    path = os.path.join(GEO, "ohm", f"{rid}.geojson")
    if os.path.exists(path):
        f = json.load(open(path))
        return shape(f["geometry"]), f["properties"]
    rawp = os.path.join(GEO, "ohm", "raw", f"{rid}.json")
    if os.path.exists(rawp):
        d = json.load(open(rawp))
    else:
        q = f"[out:json][timeout:200];rel({rid});out geom;"
        for i in range(retries):
            try:
                d = json.loads(_get(OVERPASS, urllib.parse.urlencode({"data": q}).encode())); break
            except Exception as e:
                print("  overpass retry", rid, e); time.sleep(10 * (i + 1))
        else:
            raise RuntimeError(f"relation {rid} failed")
        os.makedirs(os.path.dirname(rawp), exist_ok=True); json.dump(d, open(rawp, "w"))
    rel = [e for e in d["elements"] if e["type"] == "relation"][0]
    outer, inner = [], []
    for m in rel.get("members", []):
        if m["type"] != "way" or "geometry" not in m:
            continue
        ls = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        (inner if m.get("role") == "inner" else outer).append(ls)
    def faces(lines):
        # node the network first (ways may cross or touch mid-segment), then polygonize
        return unary_union(list(polygonize(unary_union(lines)))) if lines else None
    def open_ends(lines):
        import collections
        c = collections.Counter()
        for l in lines:
            for pt in (l.coords[0], l.coords[-1]):
                c[(round(pt[0], 7), round(pt[1], 7))] += 1
        return [k for k, v in c.items() if v % 2]
    o = faces(outer)
    i = faces(inner)
    geom = o.difference(i) if i is not None and not i.is_empty else o
    geom = geom.buffer(0)
    tags = dict(rel.get("tags", {}))
    oe = open_ends(outer)
    if oe:
        tags["_open_ends"] = oe  # ring gaps in the source data: geometry incomplete there
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"type": "Feature", "properties": tags, "geometry": mapping(geom)}, open(path, "w"))
    return geom, tags

def natural_earth(name):
    path = os.path.join(GEO, "ne", f"{name}.geojson")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(_get(NE_BASE + f"{name}.geojson"))
    return json.load(open(path))

def ne_clip(name, bbox, filt=None):
    """Natural Earth features clipped to bbox (lon/lat) → list of (geom, props)."""
    from shapely.geometry import box
    b = box(*bbox); out = []
    for f in natural_earth(name)["features"]:
        if filt and not filt(f["properties"]):
            continue
        g = shape(f["geometry"])
        if g.intersects(b):
            out.append((g.intersection(b), f["properties"]))
    return out

# Lambert Azimuthal Equal Area centred on the lower Vistula: undistorted for this region.
_TR = Transformer.from_crs("EPSG:4326", "+proj=laea +lat_0=53.8 +lon_0=18.8 +x_0=0 +y_0=0 +ellps=GRS80 +units=m", always_xy=True)
def project(geom):
    return transform(_TR.transform, geom)
def project_pt(lon, lat):
    return _TR.transform(lon, lat)
