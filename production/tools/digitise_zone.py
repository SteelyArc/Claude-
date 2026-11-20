"""Digitise a single-colour zone from the georeferenced atlas reference into a lon/lat polygon.
usage: digitise_zone.py R,G,B out_name [x0,y0,x1,y1 pixel window]"""
import sys, json, numpy as np
sys.path.insert(0, 'tools')
from georef_overlay import CP, feats
from PIL import Image, ImageFilter
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
col = tuple(int(v) for v in sys.argv[1].split(',')); out = sys.argv[2]
win = [int(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
im = np.array(Image.open('research/diagnostics/ref_rozbiory3.png').convert('RGB')).astype(int)
m = (np.abs(im - np.array(col)).sum(-1) < 10)
if win: w = np.zeros_like(m); w[win[1]:win[3], win[0]:win[2]] = 1; m &= w.astype(bool)
mm = Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(11))
a = np.array(mm).astype(float) / 255
cs = plt.contour(a, levels=[0.5]); polys = []
for path in cs.get_paths():
    for ring in path.to_polygons():
        if len(ring) > 20: polys.append(Polygon(ring).buffer(0))
big = max(polys, key=lambda p: p.area)
P = np.array([v[0] for v in CP.values()], float); L = np.array([v[1] for v in CP.values()])
inv, *_ = np.linalg.lstsq(feats(P[:, 0], P[:, 1]), L, rcond=None)
xy = np.array(big.exterior.coords); ll = feats(xy[:, 0], xy[:, 1]) @ inv
poly = Polygon(ll).buffer(0)
json.dump({'type': 'Feature', 'properties': {'source': 'digitised from Rzeczpospolita_Rozbiory_3.png (Commons, Halibutt)', 'colour': col},
           'geometry': mapping(poly)}, open(f'data/geo/{out}.geojson', 'w'))
print(out, 'bounds', [round(v, 2) for v in poly.bounds])
