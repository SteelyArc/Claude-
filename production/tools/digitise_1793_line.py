"""Digitise the 1793 Russian partition line from the georeferenced atlas reference
(boundary between the 1793-Russian and 1795-Russian colours) and build corrected polygons."""
import json, numpy as np, sys
sys.path.insert(0, 'tools')
from georef_overlay import CP, feats
from PIL import Image, ImageFilter
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import split, unary_union
from pyproj import Geod
im = np.array(Image.open('research/diagnostics/ref_rozbiory3.png').convert('RGB')).astype(int)
def near(c, tol=10): return (np.abs(im - np.array(c)).sum(-1) < tol)
grey = near((198,173,169)); pink = near((232,184,179))
# close small gaps from rivers/labels
g = Image.fromarray((grey*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
pk = Image.fromarray((pink*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
G = np.array(g) > 0; PK = np.array(pk) > 0
# boundary pixels: grey pixel with pink within 8 px to the west
H, W = G.shape; pts = []
for y in range(H):
    xs = np.where(G[y])[0]
    for x in xs:
        if x > 8 and PK[y, x-8:x].any() and not G[y, x-1]:
            pts.append((x, y))
pts = np.array(pts); print('boundary pixels', len(pts), 'y-range', pts[:,1].min(), pts[:,1].max())
# keep the main north-south line: for each y take the west-most boundary pixel with x in plausible band
line = []
for y in range(pts[:,1].min(), pts[:,1].max()+1, 3):
    s = pts[(pts[:,1] >= y) & (pts[:,1] < y+3)]
    s = s[(s[:,0] > 850) & (s[:,0] < 1000)]
    if len(s): line.append((s[:,0].min(), y + 1))
line = np.array(line, float)
# smooth lightly
k = 5; sm = np.convolve(line[:,0], np.ones(k)/k, mode='same'); sm[:k] = line[:k,0]; sm[-k:] = line[-k:,0]; line[:,0] = sm
# inverse transform pixel -> lon/lat
P = np.array([v[0] for v in CP.values()], float); L = np.array([v[1] for v in CP.values()])
inv, *_ = np.linalg.lstsq(feats(P[:,0], P[:,1]), L, rcond=None)
ll = feats(line[:,0], line[:,1]) @ inv
print('line from', ll[0].round(2), 'to', ll[-1].round(2), 'points', len(ll))
json.dump({'type':'Feature','properties':{'name':'Russian partition line 1793 (digitised from atlas reference)',
           'source':'Rzeczpospolita_Rozbiory_3.png (Wikimedia Commons, Halibutt) georeferenced by 22 control points'},
           'geometry':mapping(LineString(ll))}, open('data/geo/line_1793_russia_raw.geojson','w'))
