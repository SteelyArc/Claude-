"""Build all cartographic layers in a Lambert azimuthal equal-area projection (km units).
Sources: OpenHistoricalMap (CC0), RISTAT 1897 districts (Kessler & Markevich, CC0), Natural Earth (PD)."""
import json, pickle, numpy as np, shapely
from shapely.geometry import shape, box, Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge
from pyproj import Transformer, Geod
import build_geo
D='/home/user/Claude-/partition1772/data/'
geod=Geod(ellps='WGS84'); AREA=lambda g: abs(geod.geometry_area_perimeter(g)[0])/1e6
TR=Transformer.from_crs(4326,'+proj=laea +lat_0=52 +lon_0=22 +units=km +ellps=WGS84',always_xy=True)
def proj(g): return shapely.transform(g, lambda c: np.column_stack(TR.transform(c[:,0],c[:,1])))
def pt(lon,lat): x,y=TR.transform(lon,lat); return (x,y)
BB=box(-25,30,75,75)
BBL=box(-40,20,80,78)
land=unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(D+'ne_10m_land.geojson'))['features'] if shape(f['geometry']).intersects(BBL)]).intersection(BBL)
lakes=unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(D+'ne_10m_lakes.geojson'))['features'] if shape(f['geometry']).intersects(BBL)])
land=unary_union(shapely.make_valid(land)); landmask=land.difference(lakes)
R={}
for id,n in [(2961392,'plc_pre'),(2692511,'plc_post'),(2748498,'prussia_pre'),(2748497,'prussia_post'),(2851879,'russia_pre'),(2851992,'russia_post'),
             (2748048,'galicia'),(2748039,'netze'),(2964455,'hungary'),(2830395,'bohemia'),(2830883,'austrian_circle'),(2746687,'ottoman'),(2849499,'crimea'),(2851880,'sweden'),(2830353,'hre'),(2696443,'warmia'),(2696308,'gdl'),(2878295,'transylvania'),(2747562,'banat'),(2746839,'banat_mf')]:
    try: R[n]=build_geo.rel(id)[0].intersection(BB)
    except FileNotFoundError: pass
F=json.load(open(D+'ristat/distr1897.geojson'))['features']
VM=unary_union([shape(f['geometry']).buffer(0) for f in F if f['properties']['prov_ENG'] in('Vitebsk governorate','Mogilev governorate')])
courland_gub=unary_union([shape(f['geometry']).buffer(0) for f in F if 'Kurland' in str(f['properties']['prov_ENG'])])
# --- correction: OHM places the Nevel/Sebezh/Velizh districts (and edge strips) in Russia before 1772.
corr=VM.intersection(R['russia_pre']).buffer(0)
corr=unary_union([p for p in getattr(corr,'geoms',[corr]) if AREA(p)>30])
plc_pre=unary_union([R['plc_pre'],corr]).buffer(0.002).buffer(-0.002)
russia_pre=R['russia_pre'].difference(corr)
courland=plc_pre.intersection(courland_gub.buffer(0.02)).buffer(0)
courland=unary_union([p for p in getattr(courland,'geoms',[courland]) if AREA(p)>200])
plc_post=R['plc_post']
gain_P=plc_pre.intersection(R['prussia_post']); gain_A=plc_pre.intersection(R['galicia'])
gain_R=plc_pre.difference(plc_post).difference(gain_P).difference(gain_A)
gain_R=unary_union([p for p in getattr(gain_R,'geoms',[gain_R]) if AREA(p)>100 and p.representative_point().x>25.5])
habsburg=unary_union([R['bohemia'],R['austrian_circle'],R['hungary'],R['transylvania'],R['banat'],R['banat_mf']]).difference(plc_pre)
L={}
def clip(g): return g.intersection(landmask).buffer(0)
L['plc_pre']=clip(plc_pre); L['plc_post']=clip(plc_post); L['courland']=clip(courland)
L['plc_pre_core']=clip(plc_pre.difference(courland)); L['plc_post_core']=clip(plc_post.difference(courland))
L['plc_rem']=clip(plc_pre.difference(courland).difference(gain_P).difference(gain_R).difference(gain_A)); L['gain_P']=clip(gain_P); L['gain_R']=clip(gain_R); L['gain_A']=clip(gain_A)
L['warmia']=clip(gain_P.intersection(R['warmia'])); L['netze']=clip(gain_P.intersection(R['netze']))
L['royal_prussia']=clip(gain_P.difference(R['warmia']).difference(R['netze']))
L['prussia_pre']=clip(R['prussia_pre'].difference(plc_pre)); L['russia_pre']=clip(russia_pre.difference(plc_pre))
L['habsburg']=clip(habsburg); L['ottoman']=clip(R['ottoman'].union(R['crimea']).difference(plc_pre))
L['sweden']=clip(R['sweden']); L['hre_other']=clip(R['hre'].difference(habsburg).difference(R['prussia_pre']))
L['gdl_pre']=clip(R['gdl'].union(corr).difference(courland))
L['land']=land; L['lakes']=lakes
print('Areas (km2, land-clipped):')
for k in ['plc_pre','plc_pre_core','courland','plc_post','gain_P','gain_R','gain_A','royal_prussia','warmia','netze','gdl_pre']: print(f'  {k:14s} {AREA(L[k]):9.0f}')
print('  correction added to Commonwealth', AREA(corr))
# new borders cut in 1772 = parts of post boundary not on pre boundary
def cutline(gain):
    l=plc_post.boundary.intersection(gain.buffer(0.01)); l=l.difference(plc_pre.boundary.buffer(0.02))
    parts=[g for g in getattr(l,'geoms',[l]) if g.geom_type in('LineString','MultiLineString')]
    u=unary_union(parts)
    return linemerge(u) if u.geom_type=='MultiLineString' else u
L['cut_P']=cutline(gain_P); L['cut_R']=cutline(gain_R); L['cut_A']=cutline(gain_A).reverse()
L['gdl_line']=L['gdl_pre'].boundary.intersection(L['plc_pre_core'].buffer(-0.03))
for k in ['cut_P','cut_R','cut_A']:
    g=L[k]; print(k, g.geom_type, [round(x.length,2) for x in getattr(g,'geoms',[g])][:12])
# rivers
RV={}
def addriv(f,key,names):
    for ft in json.load(open(D+f))['features']:
        p=ft['properties']; n=p.get('name_en') or p.get('name')
        for canon,al in names.items():
            if n in al: RV.setdefault(canon,[]).append(shape(ft['geometry']).intersection(BB))
names={'Vistula':['Vistula'],'Oder':['Oder'],'Neman':['Nemunas'],'Western Dvina':['Zapadnaya Dvina','Daugava'],'Dnieper':['Dnieper','Dnepre'],
 'Dniester':['Dniester'],'Western Bug':['Bug','Zakhidnyy Buh'],'San':['San'],'Narew':['Narew'],'Noteć':['Noteć'],'Warta':['Warta'],'Pripyat':['Pripyat','Prypiat'],
 'Berezina':['Berezina'],'Drut':['Drut'],'Sozh':['Sozh'],'Southern Bug':['Southern Bug'],'Prut':['Prut'],'Danube':['Danube'],'Elbe':['Elbe'],'Pilica':['Pilica'],
 'Wieprz':['Wieprz'],'Dunajec':['Dunajec'],'Horyn':['Horyn'],'Sluch':['Sluch'],'Styr':['Styr'],'Desna':['Desna'],'Vilija':['Vilija'],'Bzura':['Bzura'],'Drwęca':['Drwęca'],'Łyna':['Łyna'],'Velikaya':['Velikaya'],'Teteriv':['Teteriv'],'Ros':['Ros'],'Venta':['Venta'],'Gauja':['Gauja'],'Ptsich':['Ptsich'],'Iput':['Iput'],'Narva':['Narva'],'Neva':['Neva'],'Tisa':['Tisa'],'Morava':['Morava'],'Vah':['Váh'],'Siret':['Siret'],'Mukhavets':['Mukhavyets'],'Shchara':['Ščara']}
addriv('ne_10m_rivers_lake_centerlines.geojson','',names); addriv('ne_10m_rivers_europe.geojson','',names)
def lm(u):
    u=unary_union(u); return linemerge(u) if u.geom_type=='MultiLineString' else u
L['rivers']={k:lm(v) for k,v in RV.items()}
from shapely.geometry import Polygon as _Poly, MultiPolygon as _MP
def clean(g):
    if g.geom_type not in ('Polygon','MultiPolygon'): return g
    out=[]
    for p in getattr(g,'geoms',[g]):
        if p.geom_type!='Polygon' or AREA(p)<15: continue
        out.append(_Poly(p.exterior.coords,[i.coords for i in p.interiors if AREA(_Poly(i.coords))>150]))
    return unary_union(out) if out else g
for k in list(L):
    if k not in ('rivers','land','lakes'): L[k]=clean(L[k])
P={k:proj(v) for k,v in L.items() if k!='rivers'}; P['rivers']={k:proj(v) for k,v in L['rivers'].items()}
cities={'Warsaw':(21.012,52.230),'Kraków':(19.937,50.062),'Vilnius':(25.280,54.687),'Danzig':(18.646,54.352),'Thorn':(18.598,53.013),'Königsberg':(20.511,54.710),
 'Berlin':(13.405,52.520),'Vienna':(16.373,48.208),'St Petersburg':(30.316,59.939),'Moscow':(37.618,55.756),'Riga':(24.106,56.949),'Lemberg':(24.031,49.842),
 'Polotsk':(28.787,55.486),'Vitebsk':(30.204,55.184),'Mogilev':(30.330,53.900),'Mstislavl':(31.722,54.019),'Dünaburg':(26.536,55.874),'Elbing':(19.404,54.156),
 'Marienburg':(19.028,54.039),'Bromberg':(18.008,53.123),'Frauenburg':(19.678,54.358),'Poznań':(16.925,52.406),'Lublin':(22.568,51.246),'Kamieniec':(26.585,48.679),
 'Kiev':(30.523,50.450),'Smolensk':(32.045,54.782),'Minsk':(27.567,53.900),'Grodno':(23.829,53.677),'Brest':(23.686,52.097),'Lutsk':(25.325,50.747),'Zamość':(23.252,50.723),
 'Breslau':(17.038,51.108),'Stettin':(14.553,53.428),'Mitau':(23.722,56.651),'Istanbul':(28.979,41.008),'Stockholm':(18.068,59.329),'Prague':(14.421,50.088),'Buda':(19.040,47.498),
 'Bełz':(24.013,50.381),'Halicz':(24.721,49.125),'Przemyśl':(22.768,49.784),'Tarnów':(20.986,50.012),'Wieliczka':(20.065,49.987),'Rzeszów':(22.004,50.041),'Podgórze':(19.958,50.042),'Gomel':(30.990,52.430),'Orsha':(30.420,54.510),'Nevel':(29.92,56.02),'Velizh':(31.1,55.6),'Sebezh':(28.49,56.29)}
P['cities']={k:pt(*v) for k,v in cities.items()}
P['meta']={'proj':'+proj=laea +lat_0=52 +lon_0=22 +units=km'}
pickle.dump(P,open(D+'layers.pkl','wb'))
# graticule for atlas feel
