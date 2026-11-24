"""All geometry for the video, in lon/lat (shapely). Built from CShapes 2.0 + a few hand cuts."""
import os, pickle
from shapely.geometry import Polygon, box, LineString
from shapely.ops import unary_union
from geo import snapshot

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '..', 'cshapes', 'pieces.pkl')
BBOX = (8.5, 38.5, 37, 64.5)


def clean(g, simp=0.012, r=0.02):
    if g is None or g.is_empty:
        return g
    g = g.buffer(0).simplify(simp)
    g = g.buffer(r, join_style=1).buffer(-r, join_style=1)
    # drop slivers
    if g.geom_type == 'MultiPolygon':
        g = unary_union([p for p in g.geoms if p.area > 0.0015])
    return g


def build():
    B = box(*BBOX)
    def snap(d):
        return {k: v.intersection(B) for k, v in snapshot(d, BBOX).items()}
    s14 = snap('1914-06-01')
    s18 = snap('1918-12-01')
    s19a = snap('1919-08-01')
    s19b = snap('1920-01-01')
    s20 = snap('1920-12-01')
    s21 = snap('1921-06-01')
    s38a = snap('1938-06-01')
    s38 = snap('1938-12-01')

    land = unary_union([unary_union(list(s.values())) for s in (s14, s21, s38)])

    P18, P19a, P19b, P20, P21 = (s['Poland'] for s in (s18, s19a, s19b, s20, s21))
    G14 = s14['Germany (Prussia)']
    AH14 = s14['Austria-Hungary']
    R14 = s14['Russia (Soviet Union)']

    # Polish Upper Silesia (to Poland 1922) — hand cut of the 1921 Polish shape inside 1914 Germany
    silesia = P21.intersection(G14).intersection(box(17.95, 49.8, 19.7, 50.95))
    # Pomerelia / "corridor" vs Posen province: cut line across the former Prussian part
    north_cut = Polygon([(14, 53.32), (17.6, 53.32), (18.15, 53.2), (18.45, 53.02), (19.3, 52.98),
                         (20.5, 53.05), (20.5, 56), (14, 56)])
    prussian = P19a.difference(P18)
    corridor = prussian.intersection(north_cut).difference(silesia)
    posen = prussian.difference(north_cut).difference(silesia)
    galicia = P19b.difference(P19a)
    san = Polygon([(17, 48), (21.9, 48), (22.3, 49.25), (22.65, 49.6), (22.55, 50.3), (22.2, 51.0), (17, 51.0)])
    galicia_w = galicia.intersection(san)
    galicia_e = galicia.difference(san)
    P18 = unary_union([P18, galicia_w])
    wilno = P20.difference(P19b)
    riga = P21.difference(P20)
    danzig = s19a['Danzig']

    cz = s38a['Czechoslovakia']
    zaolzie = cz.intersection(Polygon([(18.2, 49.97), (18.62, 50.02), (18.88, 49.78), (18.86, 49.5),
                                       (18.55, 49.47), (18.28, 49.6)]))

    # Partition of the (interwar) Polish lands in 1914
    plands = unary_union([P21, danzig, zaolzie])
    part_prussia = plands.intersection(G14)
    part_austria = plands.intersection(AH14)
    part_russia = plands.difference(part_prussia).difference(part_austria)

    # Plebiscite areas 1920 in East Prussia (Allenstein + Marienwerder), stayed German
    G20 = s19a['Germany (Prussia)']
    pleb = G20.intersection(Polygon([(18.75, 53.35), (18.8, 54.0), (19.9, 54.08), (21.4, 54.22),
                                     (22.9, 54.05), (22.9, 53.2), (18.75, 53.2)]))

    # Regency Kingdom of Poland (1916-18), ~ German/Austrian-occupied Congress Poland
    regency = P18.difference(galicia_w)

    out = dict(land=land, s14=s14, s18=s18, s19a=s19a, s20=s20, s21=s21, s38a=s38a, s38=s38,
               P18=P18, posen=posen, corridor=corridor, galicia_e=galicia_e, galicia_w=galicia_w, wilno=wilno, riga=riga,
               silesia=silesia, danzig=danzig, zaolzie=zaolzie, part_prussia=part_prussia,
               part_austria=part_austria, part_russia=part_russia, pleb=pleb, regency=regency,
               G14=G14, AH14=AH14, R14=R14)
    return out


def pieces():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    d = build()
    pickle.dump(d, open(CACHE, 'wb'))
    return d


if __name__ == '__main__':
    d = pieces()
    for k, v in d.items():
        if hasattr(v, 'area'):
            print(k, round(v.area, 3))


# ---------------------------------------------------------------- 18th-century partitions (hand-built treaty lines)
def side(line, far_pts):
    """polygon from a polyline closed through far points (lon/lat)."""
    return Polygon(list(line) + list(far_pts)).buffer(0)


def build_partitions(land):
    import json
    from shapely.geometry import shape, Point
    d = json.load(open(os.path.join(HERE, '..', 'data', 'world_1700.geojson')))
    plc = unary_union([shape(f['geometry']).buffer(0) for f in d['features']
                       if f['properties']['NAME'] == 'Polish–Lithuanian Commonwealth'])
    podolia = Polygon([(25.9, 49.4), (26.15, 48.5), (27.0, 48.4), (28.0, 48.1), (28.9, 47.7), (29.6, 47.95),
                       (30.0, 48.6), (29.6, 49.4), (27.5, 49.7)])
    warmia = Polygon([(19.55, 54.42), (20.9, 54.45), (21.05, 53.9), (20.6, 53.5), (19.9, 53.7), (19.55, 54.2)])
    danzig = Point(18.65, 54.33).buffer(0.25)
    plc = unary_union([plc, podolia, warmia, danzig]).buffer(0.05).buffer(-0.05).intersection(land)

    # --- 1772
    rus72_line = [(24.9, 58.0), (25.0, 56.5), (25.6, 56.3), (26.5, 55.9), (27.2, 55.8), (27.9, 55.62), (28.5, 55.5),
                  (28.8, 55.45), (29.0, 55.15), (29.15, 54.7), (29.4, 54.35), (29.8, 53.9), (30.0, 53.4),
                  (30.15, 52.9), (30.4, 52.3), (30.6, 51.6), (31.0, 51.0)]
    rus72 = plc.intersection(side(rus72_line, [(36, 51), (36, 58)]))
    pru72_line = [(15.5, 52.7), (16.2, 52.88), (17.0, 53.0), (17.6, 53.1), (18.0, 53.12), (18.55, 53.05),
                  (19.0, 53.15), (19.45, 53.25), (19.9, 53.35), (20.6, 53.3), (21.5, 53.4)]
    pru72 = plc.intersection(side(pru72_line, [(21.5, 55.2), (15.5, 55.2)])).difference(danzig).difference(
        Point(18.6, 53.01).buffer(0.08))
    aus72_line = [(18.5, 50.05), (19.3, 49.97), (19.94, 50.04), (20.6, 50.2), (21.2, 50.35), (21.8, 50.68),
                  (22.6, 50.78), (23.3, 50.8), (24.1, 50.65), (25.0, 50.25), (25.8, 49.85), (26.0, 49.4),
                  (26.15, 48.9), (26.3, 48.3)]
    aus72 = plc.intersection(side(aus72_line, [(26.3, 47.5), (18.5, 47.5)])).difference(rus72)
    rem72 = plc.difference(unary_union([rus72, pru72, aus72]))

    # --- 1793
    rus93_line = [(25.0, 58.0), (25.2, 56.6), (26.3, 56.1), (27.45, 55.8), (27.0, 55.2), (26.85, 54.6),
                  (26.75, 54.0), (26.7, 53.45), (26.4, 52.8), (26.1, 52.1), (26.5, 51.2), (26.7, 50.5),
                  (26.3, 49.9), (26.05, 49.45), (26.2, 48.3)]
    rus93 = rem72.intersection(side(rus93_line, [(26.2, 45.5), (36, 45.5), (36, 58)]))
    pru93_line = [(20.4, 53.4), (20.3, 53.2), (20.35, 52.75), (20.3, 52.2), (20.2, 51.75), (19.7, 51.2),
                  (19.3, 50.9), (19.0, 50.5), (18.6, 50.2)]
    pru93 = rem72.intersection(side(pru93_line, [(14, 50.2), (14, 55), (20.4, 55)]))
    rem93 = rem72.difference(unary_union([rus93, pru93]))

    # --- 1795
    aus95_line = [(18.8, 50.2), (19.4, 50.35), (19.8, 50.65), (20.2, 50.9), (20.6, 51.2), (21.0, 51.6),
                  (21.45, 51.87), (21.25, 52.08), (21.6, 52.2), (22.3, 52.3), (22.9, 52.3), (23.6, 52.1),
                  (23.65, 51.55), (24.05, 50.85), (24.2, 50.3)]
    aus95 = rem93.intersection(side(aus95_line, [(24.2, 49), (18.8, 49)]))
    rus95_line = [(24.2, 50.3), (24.05, 50.85), (23.65, 51.55), (23.6, 52.1), (23.45, 52.4), (23.6, 52.9),
                  (23.9, 53.5), (23.83, 53.68), (23.9, 54.1), (23.97, 54.6), (23.9, 54.9), (23.0, 55.05),
                  (22.2, 55.08), (21.3, 55.27), (21.0, 55.4)]
    rus95 = rem93.intersection(side([(24.4, 49.0)] + rus95_line, [(21.0, 58.5), (36, 58.5), (36, 49.0)]))
    pru95 = rem93.difference(unary_union([aus95, rus95]))
    return dict(plc=plc, rus72=rus72, pru72=pru72, aus72=aus72, rem72=rem72, rus93=rus93, pru93=pru93,
                rem93=rem93, aus95=aus95, rus95=rus95, pru95=pru95)


def partitions():
    c = os.path.join(HERE, '..', 'cshapes', 'partitions.pkl')
    if os.path.exists(c):
        return pickle.load(open(c, 'rb'))
    d = build_partitions(clean(pieces()['land'], 0.01, 0.03))
    pickle.dump(d, open(c, 'wb'))
    return d
