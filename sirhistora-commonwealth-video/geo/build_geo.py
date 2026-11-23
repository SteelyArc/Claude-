import json,math
from shapely.geometry import shape,box,Polygon,MultiPolygon,mapping
from shapely.ops import unary_union,transform
from shapely.validation import make_valid
# Lambert conformal conic
lat1,lat2,lat0,lon0=math.radians(46),math.radians(58),math.radians(52),math.radians(26)
n=math.log(math.cos(lat1)/math.cos(lat2))/math.log(math.tan(math.pi/4+lat2/2)/math.tan(math.pi/4+lat1/2))
F=math.cos(lat1)*math.tan(math.pi/4+lat1/2)**n/n
rho0=F/math.tan(math.pi/4+lat0/2)**n
def P(lon,lat):
    rho=F/math.tan(math.pi/4+math.radians(lat)/2)**n
    th=n*(math.radians(lon)-lon0)
    return rho*math.sin(th),rho0-rho*math.cos(th)
# fit bounds
corners=[P(lo,la) for lo in (9,26,45) for la in (40.5,63)]
xs=[c[0] for c in corners];ys=[c[1] for c in corners]
W,H=3200,3600
sc=min(W/(max(xs)-min(xs)),H/(max(ys)-min(ys)))
cx=(max(xs)+min(xs))/2;cy=(max(ys)+min(ys))/2
def toPx(lon,lat):
    x,y=P(lon,lat);return W/2+(x-cx)*sc, H/2-(y-cy)*sc
CLIP=box(-6,33,62,70)
LANDRAW=None
def prep(g,tol=0.012):
    g=make_valid(g).intersection(CLIP)
    if LANDRAW is not None:
        import shapely
        g=make_valid(g.buffer(0.04).buffer(-0.04))
        g=shapely.set_precision(g,0.0005)
        try: g=g.intersection(LANDRAW)
        except Exception: g=g.buffer(0).intersection(LANDRAW.buffer(0))
    return g.simplify(tol,preserve_topology=True)
def path(g):
    if g.is_empty:return ''
    def tp(x,y,z=None):
        return toPx(x,y)
    gp=transform(lambda x,y,z=None:tuple(zip(*[toPx(a,b) for a,b in zip(x,y)])) ,g)
    out=[]
    polys=[gp] if gp.geom_type=='Polygon' else [p for p in getattr(gp,'geoms',[]) if p.geom_type=='Polygon']
    for p in polys:
        if p.area<40:continue
        for ring in [p.exterior,*p.interiors]:
            c=list(ring.coords)
            out.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in c)+'Z')
    return ''.join(out)
def load(y):
    d=json.load(open(f'w{y}.json'));m={}
    for f in d['features']:
        if f['geometry']:
            k=str(f['properties'].get('NAME'))
            g=make_valid(shape(f['geometry']))
            m[k]=unary_union([m[k],g]) if k in m else g
    return m
D={y:load(y) for y in (1400,1500,1600,1650,1700,1783,1800)}
countries=json.load(open('countries-10m.geojson'))
modern={f['properties']['name']:make_valid(shape(f['geometry'])) for f in countries['features']}
land=prep(unary_union([make_valid(shape(f['geometry'])) for f in json.load(open('land-10m.geojson'))['features']]),0.01)
L={}
L['land']=land
import shapely
LANDRAW=shapely.set_precision(make_valid(land.buffer(0)),0.0005)
pl=D[1400]['Poland-Lithuania']
polk=pl.intersection(unary_union([modern['Poland'],box(22,47.8,26.6,50.6)]))
L['pol1385']=prep(polk);L['lit1385']=prep(pl.difference(polk).buffer(0))
L['union1385']=prep(pl)
for k,src in [('teut1400',(1400,'Teutonic Knights')),('hun1400',(1400,'Kingdom of Hungary')),('nov1400',(1400,'Novgorod')),('mol1400',(1400,'Moldova')),
 ('plc1600',(1600,'Poland-Lithuania')),('mus1600',(1600,'Tsardom of Muscovy')),('swe1600',(1600,'Sweden')),('ott1600',(1600,'Ottoman Empire')),('cri1600',(1600,'Crimean Khanate')),('hre1600',(1600,'Holy Roman Empire')),('pru1600',(1600,'Prussia')),
 ('plc1650',(1650,'Polish–Lithuanian Commonwealth')),('mus1650',(1650,'Tsardom of Muscovy')),('swe1650',(1650,'Sweden')),('ott1650',(1650,'Ottoman Empire')),('pru1650',(1650,'Prussia')),('hre1650',(1650,'Holy Roman Empire')),
 ('plc1700',(1700,'Polish–Lithuanian Commonwealth')),('mus1700',(1700,'Tsardom of Muscovy')),('swe1700',(1700,'Sweden')),('ott1700',(1700,'Ottoman Empire')),('pru1700',(1700,'Prussia')),('aus1700',(1700,'Austrian Empire')),('hre1700',(1700,'Holy Roman Empire')),
 ('pol1783',(1783,'Poland')),('rus1783',(1783,'Russian Empire')),('pru1783',(1783,'Prussia')),('aus1783',(1783,'Austrian Empire')),('ott1783',(1783,'Ottoman Empire')),('swe1783',(1783,'Sweden')),('sax1783',(1783,'Saxony')),
 ('rus1800',(1800,'Russian Empire')),('pru1800',(1800,'Prussia')),('aus1800',(1800,'Austrian Empire')),('ott1800',(1800,'Ottoman Empire')),('swe1800',(1800,'Sweden'))]:
    y,nm=src
    if nm in D[y]: L[k]=prep(D[y][nm])
    else: print('missing',k)
plc1700=make_valid(D[1700]['Polish–Lithuanian Commonwealth']);pol83=make_valid(D[1783]['Poland'])
L['p1_ru']=prep(plc1700.intersection(D[1783]['Russian Empire']))
L['p1_pr']=prep(plc1700.intersection(D[1783]['Prussia']))
L['p1_au']=prep(plc1700.intersection(D[1783]['Austrian Empire']))
ru93=Polygon([(27.6,57.5),(27.2,56.0),(26.6,55.0),(25.9,53.6),(26.1,52.0),(26.4,50.5),(26.3,48.3),(40,45),(40,60)])
pr93=Polygon([(10,56),(18.6,55.2),(19.4,54.1),(20.3,53.2),(20.6,52.3),(20.4,51.6),(19.6,51.0),(19.2,50.4),(10,50)])
L['p2_ru']=prep(pol83.intersection(ru93));L['p2_pr']=prep(pol83.intersection(pr93))
pol93=pol83.difference(ru93).difference(pr93)
L['pol1793']=prep(pol93)
au95=Polygon([(18.8,50.0),(19.3,50.95),(20.5,51.35),(21.6,51.95),(22.5,52.25),(23.5,52.05),(24.3,51.4),(24.3,49.8),(18.8,49.5)])
L['p3_ru']=prep(pol93.intersection(D[1800]['Russian Empire']).difference(au95))
L['p3_pr']=prep(pol93.intersection(D[1800]['Prussia']).difference(au95))
L['p3_au']=prep(pol93.intersection(au95))
plc1650=make_valid(D[1650]['Polish–Lithuanian Commonwealth'])
het=Polygon([(29.0,48.6),(28.6,50.2),(29.6,51.5),(31.2,52.3),(33.8,52.6),(35.2,51.0),(35.0,48.8),(33.5,47.8),(31.0,47.6)])
L['hetman']=prep(plc1650.intersection(het))
L['andrus']=prep(plc1650.difference(plc1700).buffer(0))
L['zapo']=prep(Polygon([(33.0,48.6),(35.8,48.6),(36.4,47.2),(34.5,46.6),(32.6,47.2)]))
pts={'krakow':(19.94,50.06),'warsaw':(21.01,52.23),'vilnius':(25.28,54.69),'kyiv':(30.52,50.45),'moscow':(37.62,55.75),'lublin':(22.57,51.25),'gdansk':(18.65,54.35),'riga':(24.1,56.95),'lviv':(24.03,49.84),'minsk':(27.56,53.9),'smolensk':(32.05,54.78),'vienna':(16.37,48.21),'stockholm':(18.07,59.33),'berlin':(13.4,52.52),'istanbul':(28.97,41.0),'poznan':(16.93,52.41),'konigsberg':(20.51,54.71),'grunwald':(20.12,53.48),'khotyn':(26.49,48.5),'poltava':(34.55,49.59),'pereiaslav':(31.45,50.07),'dresden':(13.74,51.05),'raclawice':(20.1,50.33),'maciejowice':(21.56,51.69),'sich':(34.6,47.6),'czestochowa':(19.12,50.81),'budapest':(19.04,47.5),'petersburg':(30.3,59.94),'narva':(28.19,59.38),'krewo':(26.29,54.31),'andrusovo':(32.2,54.6),'zborov':(25.15,49.66),'berestechko':(25.12,50.36),'kircholm':(24.29,56.85),'klushino':(34.9,55.5),'kokenhausen':(25.43,56.64),'cecora':(27.6,47.3),'grodno':(23.83,53.68),'plc_center':(25.5,52.8),'chernihiv':(31.3,51.5),'kamianets':(26.58,48.68),'torun':(18.6,53.0),'bucharest':(26.1,44.43),'hungary_c':(19.5,47.3),'muscovy_c':(38.5,55.0),'swe_c':(15.5,61.0),'ott_c':(30.0,44.8),'lit_c':(27.5,53.8),'pol_c':(19.3,51.5),'teut_c':(19.8,54.0),'hre_c':(12.0,50.5),'pru_c':(15.0,52.8),'aus_c':(18.0,48.8),'cri_c':(34.5,45.9),'stettin':(14.55,53.43),'ott_lab':(25.0,43.0),'prussia_lab':(15.4,53.7),'austria_lab':(17.8,48.4),'cossack_lab':(32.4,49.9),'crimea_lab':(34.6,45.4),'saxony_lab':(13.2,51.0),'tag_pl':(19.6,52.2),'tag_lt':(24.0,55.3),'tag_lv':(25.6,56.9),'tag_ee':(26.4,58.3),'tag_by':(27.8,53.3),'tag_ua':(28.4,49.9),'tag_ru':(32.4,54.3),'muscovy_lab':(37.0,57.0),'swe_lab':(16.0,60.6),'lublin2':(22.57,51.25),'budapest2':(19.04,47.5),'baltic':(19.0,56.5),'smolensk2':(32.05,54.78)}
out={'W':W,'H':H,'layers':{k:path(v) for k,v in L.items()},'pts':{k:[round(c,1) for c in toPx(*v)] for k,v in pts.items()}}
for k,v in out['layers'].items(): print(k,len(v))
json.dump(out,open('geo_out.json','w'))
