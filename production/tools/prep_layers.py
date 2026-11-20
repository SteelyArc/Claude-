"""Prepare projected map layers for every historical stage -> data/layers.pkl

Political geometry: OpenHistoricalMap (CC0) relations, with the 1793 Russian line corrected
(see research/BORDER_VERIFICATION.md). Physical geometry: Natural Earth 10m (public domain).
Projection: Lambert Azimuthal Equal-Area centred on 24E 52N (metres).
"""
import json, pickle
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union, transform
from pyproj import Transformer

T = Transformer.from_crs('EPSG:4326', '+proj=laea +lat_0=52 +lon_0=24 +datum=WGS84 +units=m', always_xy=True)
EXT = box(5, 41, 42, 62)  # lon/lat working window


def G(n):
    return shape(json.load(open(f'data/geo/{n}.geojson'))['geometry']).buffer(0)


def P(g, simp=350):
    g = g.intersection(EXT)
    g = transform(T.transform, g)
    return g.simplify(simp, preserve_topology=True).buffer(0) if g.geom_type.endswith('Polygon') else g.simplify(simp)


def ne(name):
    return json.load(open(f'data/ne/{name}.geojson'))['features']


# ---------------- physical ----------------
land = unary_union([shape(f['geometry']).buffer(0) for f in ne('ne_10m_land') if shape(f['geometry']).intersects(EXT)])
lakes = unary_union([shape(f['geometry']).buffer(0) for f in ne('ne_10m_lakes')
                     if shape(f['geometry']).intersects(EXT) and f['properties'].get('scalerank', 9) <= 8])
rivers = []
for f in ne('ne_10m_rivers_lake_centerlines'):
    g = shape(f['geometry']); pr = f['properties']
    if g.intersects(EXT) and pr.get('scalerank', 99) <= 8 and pr.get('featurecla', '').startswith('River'):
        rivers.append({'name': pr.get('name_en') or pr.get('name'), 'rank': pr.get('scalerank'), 'geom': P(g, 250)})
countries = {f['properties']['ADMIN']: shape(f['geometry']).buffer(0) for f in ne('ne_10m_admin_0_countries')
             if f['properties']['ADMIN'] in ('Latvia', 'Czechia', 'Lithuania', 'Croatia')}

# ---------------- political building blocks ----------------
PLT72 = G(2692511)                      # Commonwealth after 1st partition (1773-1793), incl. Courland
RUMP93 = G('plt_1793_rump_corrected')   # after 2nd partition (corrected eastern line)
COURLAND = PLT72.intersection(countries['Latvia'].buffer(0.02))
PRU72, PRU93, PRU95 = G(2748497), G(2748500), G(2748626)
RUS72, RUS92, RUS93, RUS95 = G(2851992), G(2851944), G('russia_1793_corrected'), G(2693946)
GAL72, GAL86, WGAL = G(2748048), G(2748049), G(2748050)
HUN, AUSTRIAN_CIRCLE, MORSIL = G(2829140), G(2830882), G(2747800)
BOHEMIA_MORAVIA = countries['Czechia'].buffer(0.01)
HRE = G(2815272); SAXONY = G(2806956)
OTT74, OTT92 = G(2746686), G(2746685)
OTT_PRE74 = G(2746687)                 # Ottoman Empire 1718-1774 incl. vassal Crimean Khanate (situation in 1773)
BUKOVINA = G(2746380)                  # Moldavian (Ottoman vassal) until Habsburg occupation 1774/75
TRANSYLVANIA, BANAT, BANAT_MF = G(2878295), G(2747562), G(2746839)
# Habsburg Croatia-Slavonia + Military Frontier: modern Croatia north of Venetian Dalmatia, minus Venetian Istria
# (approximation for orientation only; see research/BORDER_VERIFICATION.md)
CROATIA_HAB = countries['Croatia'].intersection(box(13.9, 44.55, 19.5, 46.6)).buffer(0)
SWE, DEN = G(2851880), G(2696595)
HABS_CORE = unary_union([HUN, AUSTRIAN_CIRCLE, MORSIL, BOHEMIA_MORAVIA, TRANSYLVANIA, BANAT, BANAT_MF, CROATIA_HAB]).buffer(0)
# Backa/Syrmia (Habsburg; between Danube and Sava) is missing from OHM's Hungary: fill the unassigned land there,
# bounded by the Ottoman frontier
_bs = land.intersection(box(18.8, 44.75, 20.6, 46.3)).difference(unary_union([HABS_CORE, OTT92, OTT_PRE74.intersection(box(18.8, 41, 23, 44.95))]))
HABS_CORE = unary_union([HABS_CORE, _bs]).buffer(0)
# 1772 gains = (power after 1772) - (power before 1772)
PRU44, RUS43 = G(2748498), G(2851879)
L72_PRU = PRU72.difference(PRU44).intersection(box(14, 51, 24, 56)).buffer(0)
# OHM's pre/post-1772 Russian polygons disagree with the atlas by 20-40 km -> use the digitised atlas zone,
# snapped to the verified 1773 Commonwealth border
L72_RUS = G('ref_russia_gain_1772').buffer(0.03).difference(PLT72).buffer(-0.01).buffer(0.01)
L72_AUT = GAL72.buffer(0)
PLT_PRE72 = unary_union([PLT72, L72_PRU, L72_RUS, L72_AUT]).buffer(0)

# 1793 gains
G93_PRU = PRU93.difference(PRU72).intersection(PLT72.buffer(0.05)).buffer(0)
G93_RUS = PLT72.difference(RUMP93).difference(G93_PRU).buffer(0)
# 1795 gains
G95_PRU = PRU95.difference(PRU93).intersection(RUMP93.buffer(0.05)).buffer(0)
G95_AUT = WGAL.intersection(RUMP93.buffer(0.05)).buffer(0)
G95_RUS = RUMP93.difference(G95_PRU).difference(G95_AUT).buffer(0)
G95_RUS_COURLAND = G95_RUS.intersection(COURLAND.buffer(0.01))
G95_RUS_MAIN = G95_RUS.difference(COURLAND)

stages = {}
common = {'sweden': P(SWE), 'denmark': P(DEN), 'saxony': P(SAXONY), 'hre': P(HRE)}
stages['1773'] = dict(common, plt=P(PLT72.difference(COURLAND)), courland=P(COURLAND), prussia=P(PRU72), russia=P(RUS72),
                      habsburg=P(unary_union([HABS_CORE, GAL72])), ottoman=P(unary_union([OTT_PRE74, BUKOVINA]).difference(GAL72).difference(HABS_CORE).difference(RUS72)),
                      loss72_pru=P(L72_PRU), loss72_aut=P(L72_AUT), loss72_rus=P(L72_RUS), plt_pre72=P(PLT_PRE72))
stages['1791'] = dict(common, plt=P(PLT72.difference(COURLAND)), courland=P(COURLAND), prussia=P(PRU72), russia=P(RUS92),
                      habsburg=P(unary_union([HABS_CORE, GAL86])), ottoman=P(OTT92.difference(GAL86).difference(HABS_CORE).difference(RUS92)))
stages['1793'] = dict(stages['1791'], plt=P(RUMP93.difference(COURLAND)), courland=P(COURLAND.intersection(RUMP93)),
                      prussia=P(PRU93), russia=P(RUS93), gain93_pru=P(G93_PRU), gain93_rus=P(G93_RUS), plt_prev=P(PLT72))
stages['1795'] = dict(stages['1793'], plt=P(RUMP93.difference(COURLAND)),
                      gain95_pru=P(G95_PRU), gain95_aut=P(G95_AUT), gain95_rus=P(G95_RUS_MAIN), gain95_rus_courland=P(G95_RUS_COURLAND),
                      prussia95=P(PRU95), russia95=P(RUS95), galicia95=P(unary_union([GAL86, WGAL])))
# land belonging to none of the mapped powers (Venice, Ragusa, Italian states ...) -> neutral 'other states'
for _st in stages.values():
    _pol = unary_union([v for k, v in _st.items() if k in ('plt', 'courland', 'prussia', 'russia', 'habsburg', 'ottoman', 'hre', 'saxony', 'sweden', 'denmark')])
    _st['other'] = P(land, 300).difference(_pol.buffer(800)).buffer(0)
    _rag = _st['other'].intersection(P(box(17.35, 42.45, 18.47, 42.98)))          # Republic of Ragusa (Dubrovnik)
    _ven = _st['other'].intersection(P(box(13.3, 42.0, 19.5, 46.0))).difference(_rag)  # Venetian Istria, Dalmatia, Albania
    _st['ragusa'] = _rag.buffer(0); _st['venice'] = _ven.buffer(0)
    _st['other'] = _st['other'].difference(P(box(13.3, 42.0, 19.5, 46.0))).buffer(0)
layers = {'land': P(land, 300), 'lakes': P(lakes, 200), 'rivers': rivers, 'stages': stages,
          'gains': {'93_pru': P(G93_PRU), '93_rus': P(G93_RUS), '95_pru': P(G95_PRU), '95_aut': P(G95_AUT),
                    '95_rus': P(G95_RUS_MAIN), '95_rus_courland': P(G95_RUS_COURLAND)},
          'plt1773': P(PLT72), 'plt_pre72': P(PLT_PRE72), 'loss72': {'pru': P(L72_PRU), 'rus': P(L72_RUS), 'aut': P(L72_AUT)}, 'rump1793': P(RUMP93), 'courland': P(COURLAND)}
pickle.dump(layers, open('data/layers.pkl', 'wb'))

from pyproj import Geod
geod = Geod(ellps='WGS84')
for k, g in [('72 Prussia', L72_PRU), ('72 Russia', L72_RUS), ('72 Austria', L72_AUT), ('93 Prussia', G93_PRU), ('93 Russia', G93_RUS), ('95 Prussia', G95_PRU), ('95 Austria', G95_AUT),
             ('95 Russia (excl. Courland)', G95_RUS_MAIN), ('95 Russia: Courland', G95_RUS_COURLAND)]:
    print(f'{k:28s} {abs(geod.geometry_area_perimeter(g)[0])/1e6:10,.0f} km2')
