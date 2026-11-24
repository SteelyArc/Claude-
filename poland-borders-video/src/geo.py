import json, pickle, os
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
HERE=os.path.dirname(os.path.abspath(__file__))
CS=os.path.join(HERE,'..','cshapes','gw.topojson')
CACHE=os.path.join(HERE,'..','cshapes','decoded.pkl')

def _decode():
    t=json.load(open(CS))
    tr=t.get('transform')
    arcs=[]
    for a in t['arcs']:
        if tr:
            x=y=0; pts=[]
            for dx,dy in a:
                x+=dx;y+=dy
                pts.append((x*tr['scale'][0]+tr['translate'][0], y*tr['scale'][1]+tr['translate'][1]))
        else: pts=[tuple(p[:2]) for p in a]
        arcs.append(pts)
    def ring(ix):
        out=[]
        for i in ix:
            pts=arcs[i] if i>=0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out
    feats=[]
    for g in list(t['objects'].values())[0]['geometries']:
        if g['type']=='Polygon': polys=[g['arcs']]
        elif g['type']=='MultiPolygon': polys=g['arcs']
        else: continue
        ps=[]
        for p in polys:
            rs=[ring(r) for r in p]
            ps.append(Polygon(rs[0],rs[1:]).buffer(0))
        feats.append((g['properties'],unary_union(ps)))
    return feats

def feats():
    if os.path.exists(CACHE): return pickle.load(open(CACHE,'rb'))
    f=_decode(); pickle.dump(f,open(CACHE,'wb')); return f

def snapshot(date, bbox=(5,40,45,62)):
    from shapely.geometry import box
    B=box(*bbox); out={}
    for p,g in feats():
        if p['start']<=date<=p['end'] and g.intersects(B):
            out.setdefault(p['country_name'],[]).append(g)
    return {k:unary_union(v) for k,v in out.items()}
