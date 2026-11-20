"""Assemble OpenHistoricalMap relations into polygons and derive the 1772 partition shares."""
import json, glob, os
from shapely.geometry import LineString, Polygon, MultiPolygon, mapping, shape
from shapely.ops import polygonize, unary_union, linemerge
from pyproj import Geod
D=os.path.dirname(__file__)+'/../data/'
geod=Geod(ellps='WGS84')
def rel(id):
    d=json.load(open(D+f'ohm_{id}.json'))
    r=[e for e in d['elements'] if e['type']=='relation'][0]
    lines=[]
    for m in r['members']:
        if m['type']=='way' and 'geometry' in m and m.get('role') in ('outer','inner',''):
            lines.append(LineString([(p['lon'],p['lat']) for p in m['geometry']]))
    polys=list(polygonize(unary_union(lines)))
    # even-odd: keep polygons by containment parity
    outers=[]
    for p in polys:
        depth=sum(1 for q in polys if q is not p and q.contains(p.representative_point()))
        if depth%2==0: outers.append(p)
    g=unary_union(outers)
    g=unary_union([p for p in polys if sum(1 for q in polys if q is not p and q.contains(p.representative_point()))%2==0 ])
    return g, r['tags']
def area(g): return abs(geod.geometry_area_perimeter(g)[0])/1e6
if __name__=='__main__':
    out={}
    for id,name in [(2961392,'plc_pre'),(2692511,'plc_post'),(2696308,'gdl'),(2696309,'crown'),
                     (2748498,'prussia_pre'),(2748497,'prussia_post'),(2851879,'russia_pre'),(2851992,'russia_post'),
                     (2748048,'galicia'),(2748039,'netze'),(2964455,'hungary'),(2830395,'bohemia'),(2830883,'austrian_circle'),
                     (2746687,'ottoman'),(2849499,'crimea'),(2851880,'sweden'),(2830353,'hre')]:
        g,t=rel(id); out[name]=g
        print(f"{name:16s} valid={g.is_valid} area={area(g):10.0f} km2  bounds={tuple(round(x,1) for x in g.bounds)}")
    pre,post=out['plc_pre'],out['plc_post']
    lost=pre.difference(post)
    pr=pre.intersection(out['prussia_post']); ru=pre.intersection(out['russia_post']); au=pre.intersection(out['galicia'])
    for n,g in [('lost',lost),('to Prussia',pr),('to Russia',ru),('to Austria',au)]:
        print(f"{n:12s} {area(g):9.0f} km2")
    resid=lost.difference(unary_union([pr,ru,au]))
    print('unassigned lost area', area(resid))
    gain_outside=post.difference(pre); print('post outside pre', area(gain_outside))
    json.dump({k:mapping(v) for k,v in out.items()}, open(D+'polys.json','w'))
