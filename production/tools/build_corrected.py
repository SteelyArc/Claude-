"""Build corrected 1793 polygons: split OHM rump by the digitised 1793 Russian line."""
import json, numpy as np
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import split, unary_union
from pyproj import Geod
geod = Geod(ellps='WGS84')
def G(n): return shape(json.load(open(f'data/geo/{n}.geojson'))['geometry'])
def area(g): return abs(geod.geometry_area_perimeter(g)[0]) / 1e6
def save(name, g, props): json.dump({'type':'Feature','properties':props,'geometry':mapping(g)}, open(f'data/geo/{name}.geojson','w'))
c = np.array(LineString(G('line_1793_russia_raw')).coords)
# extend ends outward so the line fully cuts the polygon
n0 = c[0] + (c[0]-c[5]) / np.linalg.norm(c[0]-c[5]) * 0.6; n1 = c[-1] + (c[-1]-c[-6]) / np.linalg.norm(c[-1]-c[-6]) * 0.6
cut = LineString(np.vstack([n0, c, n1]))
rump_ohm = G(2692510); pre = G(2692511); rus93_ohm = G(2890609); pru93 = G(2748500); pru91 = G(2830452)
parts = split(rump_ohm, cut).geoms
west = [p for p in parts if p.centroid.x < 26.5 or p.representative_point().x < 26.0]
east = [p for p in parts if p not in west]
rump = unary_union(west); extra_rus = unary_union(east)
rus93 = unary_union([rus93_ohm, extra_rus, pre.difference(rump).difference(pru93).buffer(0.002)]).buffer(0)
# Courland: part of rump north of the Dvina / west of Lithuania – OHM includes it in the Commonwealth polygon
courland_box = shape({'type':'Polygon','coordinates':[[[20.9,55.95],[27.0,55.95],[27.0,57.9],[20.9,57.9],[20.9,55.95]]]})
courland = rump.intersection(courland_box)
props = {'source':'OpenHistoricalMap (CC0) corrected with 1793 line digitised from atlas reference; see research/BORDER_VERIFICATION.md'}
save('plt_1793_rump_corrected', rump, props); save('russia_1793_corrected', rus93, props); save('russia_gain_1793', extra_rus.union(pre.difference(rump).difference(pru93)).intersection(pre).buffer(0), props)
print(f"pre-1793 Commonwealth (OHM, incl. Courland): {area(pre):,.0f} km2")
print(f"  of which Courland approx:                    {area(pre.intersection(courland_box)):,.0f} km2")
print(f"Prussian gain 1793:   {area(pre.intersection(pru93)):,.0f} km2  (published 58,000-58,400)")
rg = pre.difference(rump).difference(pru93)
print(f"Russian gain 1793:    {area(rg):,.0f} km2  (published 228,600 Roos / ~250,000 Jedruch)")
print(f"Rump 1793 (corrected) {area(rump):,.0f} km2 ; excl. Courland {area(rump)-area(courland):,.0f} km2 (published ~215,000 Davies)")
