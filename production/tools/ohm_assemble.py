"""Assemble OpenHistoricalMap relations (Overpass `out geom`) into shapely polygons -> GeoJSON."""
import json, sys, glob, os
from shapely.geometry import LineString, Polygon, MultiPolygon, mapping
from shapely.ops import linemerge, polygonize, unary_union

def assemble(path):
    d = json.load(open(path)); rel = d['elements'][0]
    outer, inner = [], []
    for m in rel['members']:
        if m['type'] != 'way' or 'geometry' not in m: continue
        ls = LineString([(p['lon'], p['lat']) for p in m['geometry']])
        (inner if m['role'] == 'inner' else outer).append(ls)
    po = list(polygonize(unary_union(outer)))
    pi = list(polygonize(unary_union(inner))) if inner else []
    # polygonize on noded outers yields faces; keep faces not covered by inner rings
    geom = unary_union(po)
    if pi: geom = geom.difference(unary_union(pi))
    return rel['tags'], geom.buffer(0)

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.json'))):
        tags, g = assemble(f); rid = os.path.basename(f)[:-5]
        json.dump({'type': 'Feature', 'properties': {**tags, 'ohm_relation': int(rid)}, 'geometry': mapping(g)},
                  open(os.path.join(dst, rid + '.geojson'), 'w'))
        print(rid, tags.get('name:en', tags.get('name')), tags.get('start_date'), tags.get('end_date'), g.geom_type, round(g.area, 2))
