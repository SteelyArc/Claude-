"""Map states (keyframes). Each state = stack of paper sheets rendered to a master image."""
import os, sys
from shapely.ops import unary_union
from shapely.geometry import box
from data import pieces, clean
import paper as P
from paper import Sheet, geom_px

D = pieces()

C = dict(
    sea='#557f8c', sea1='#618d99', sea2='#6f9ba5', sea3='#80a9b0', sea4='#95b9bb',
    GER='#cdc5b3', RUS='#c4cca7', AUH='#e2cc9a', LIT='#b5c7a3', LAT='#d4cba4', EST='#c9c0a6',
    CZE='#dbbfa4', ROM='#e3d6ad', HUN='#cfbd9c', AUT='#d8c9b3', YUG='#d7d0b8', BUL='#d2c8a8',
    SCA='#dcd5c3', DAN='#eadfc6', other='#dad2bf', contested='#d2c6ad',
    POL='#c64639', POLnew='#d4584a',
    pRUS='#8c9f74', pGER='#7c8aa0', pAUH='#cf9f45',
)

NAMEMAP = {
    'Germany (Prussia)': 'GER', 'Russia (Soviet Union)': 'RUS', 'Austria-Hungary': 'AUH', 'Lithuania': 'LIT',
    'Latvia': 'LAT', 'Estonia': 'EST', 'Czechoslovakia': 'CZE', 'Rumania': 'ROM', 'Hungary': 'HUN',
    'Austria': 'AUT', 'Yugoslavia': 'YUG', 'Bulgaria': 'BUL', 'Sweden': 'SCA', 'Norway': 'SCA',
    'Denmark': 'SCA', 'Finland': 'SCA', 'Danzig': 'DAN', 'Poland': 'POL',
}

LAND = clean(D['land'], 0.01, 0.03)
LANDPX = geom_px(LAND)


def sea_sheets():
    out = []
    for dist, col in ((95, 'sea1'), (62, 'sea2'), (36, 'sea3'), (15, 'sea4')):
        g = LANDPX.buffer(dist, quad_segs=12).simplify(3)
        out.append(Sheet(g, C[col], level=0.45, rim=True))
    return out


def countries(snapname, overrides=None, drop=()):
    """Base country sheets from a CShapes snapshot. overrides: name->geom."""
    s = dict(D[snapname])
    s.update(overrides or {})
    sheets = []
    covered = []
    for name, g in s.items():
        if name in drop or g is None or g.is_empty:
            continue
        key = NAMEMAP.get(name, 'other')
        g = clean(g).intersection(LAND)
        covered.append(g)
        sheets.append(Sheet(geom_px(g), C[key], level=1))
    # contested / unclaimed land
    rest = LAND.difference(unary_union(covered)).buffer(-0.01).buffer(0.01)
    rest = unary_union([p for p in P.polys(rest) if p.area > 0.02]) if not rest.is_empty else rest
    if not rest.is_empty:
        sheets.insert(0, Sheet(geom_px(rest), C['contested'], level=1, hatch=True))
    return sheets


def U(*names, extra=()):
    return unary_union([D[n] for n in names] + list(extra))


def raised(g, col, level=2.0):
    return Sheet(geom_px(clean(g).intersection(LAND)), C.get(col, col), level=level)


# Polish territory at successive dates
POL_1918 = D['P18']
POL_POSEN = U('P18', 'posen')
POL_GAL = U('P18', 'posen', 'galicia_e')
POL_VERS = U('P18', 'posen', 'galicia_e', 'corridor')
POL_WIL = U('P18', 'posen', 'galicia_e', 'corridor', 'wilno')
POL_RIGA = U('P18', 'posen', 'galicia_e', 'corridor', 'wilno', 'riga')
POL_1922 = U('P18', 'posen', 'galicia_e', 'corridor', 'wilno', 'riga', 'silesia')
POL_1938 = U('P18', 'posen', 'galicia_e', 'corridor', 'wilno', 'riga', 'silesia', 'zaolzie')

G14 = D['s14']['Germany (Prussia)']
G20 = D['s19a']['Germany (Prussia)']
G20S = unary_union([G20, D['silesia']])   # Germany still holding Upper Silesia
G38 = D['s38']['Germany (Prussia)']


def base(snap, pol=None, over=None, drop=()):
    over = dict(over or {})
    sh = countries(snap, over, drop=tuple(drop) + ('Poland',))
    return sh


PT = None


def build_states():
    global PT
    from data import partitions
    PT = partitions()
    S = {}
    sea = sea_sheets()
    neutral = [Sheet(LANDPX, '#d8cfba', level=1)]
    S['plc'] = sea + neutral + [raised(PT['plc'], 'POL')]
    p72 = [raised(PT['rus72'], '#6f8458', 1.8), raised(PT['pru72'], '#56688a', 1.8), raised(PT['aus72'], '#b9862c', 1.8)]
    S['p72'] = sea + neutral + [raised(PT['rem72'], 'POL')] + p72
    p93 = [raised(PT['rus93'], '#93a676', 1.8), raised(PT['pru93'], '#7d8fae', 1.8)]
    S['p93'] = sea + neutral + [raised(PT['rem93'], 'POL')] + p72 + p93
    p95 = [raised(PT['rus95'], '#b8c79c', 1.8), raised(PT['pru95'], '#a9b6cc', 1.8), raised(PT['aus95'], '#e0b866', 1.8)]
    S['p95'] = sea + neutral + p72 + p93 + p95
    lit18 = D['s18']['Lithuania']
    # 1914: three empires
    S['empires'] = sea + countries('s14')
    S['partitions'] = S['empires'] + [raised(D['part_russia'], 'pRUS', 1.8), raised(D['part_prussia'], 'pGER', 1.8),
                                      raised(D['part_austria'], 'pAUH', 1.8)]
    # Regency kingdom 1916 (shown as a pale raised sheet over the occupied zone)
    S['regency'] = S['empires'] + [raised(D['regency'], '#e9dcc0', 1.6)]
    # Nov 1918 — independence: small core
    b18 = base('s18', over={'Germany (Prussia)': G14, 'Lithuania': lit18})
    S['1918'] = sea + b18 + [raised(POL_1918, 'POL')]
    # + Greater Poland uprising
    b = base('s18', over={'Germany (Prussia)': G14.difference(D['posen']), 'Lithuania': lit18})
    S['posen'] = sea + b + [raised(POL_POSEN, 'POL')]
    # + Eastern Galicia (Lwow)
    S['galicia'] = sea + b + [raised(POL_GAL, 'POL')]
    # Versailles: corridor + Free City of Danzig
    bv = base('s19a', over={'Germany (Prussia)': G20S, 'Lithuania': lit18})
    S['versailles'] = sea + bv + [raised(POL_VERS, 'POL')]
    S['pleb'] = S['versailles']
    # Oct 1920 Wilno
    bw = base('s20', over={'Germany (Prussia)': G20S})
    S['wilno'] = sea + bw + [raised(POL_WIL, 'POL')]
    # Riga 1921
    br = base('s21', over={'Germany (Prussia)': G20S})
    S['riga'] = sea + br + [raised(POL_RIGA, 'POL')]
    # Upper Silesia 1922
    b22 = base('s21', over={'Germany (Prussia)': G20})
    S['1922'] = sea + b22 + [raised(POL_1922, 'POL')]
    # 1938: Anschluss (March)
    ba = base('s21', over={'Germany (Prussia)': unary_union([G20, D['s21']['Austria']])}, drop=('Austria',))
    S['anschluss'] = sea + ba + [raised(POL_1922, 'POL')]
    # Oct-Nov 1938: Munich, Zaolzie, Vienna award
    cz38 = D['s38']['Czechoslovakia'].difference(D['zaolzie'])
    b38 = base('s38', over={'Czechoslovakia': cz38})
    S['1938'] = sea + b38 + [raised(POL_1938, 'POL')]
    return S


def render_state(name, sheets):
    path = os.path.join(P.OUT, f'master_{name}.png')
    if os.path.exists(path):
        return path
    img = P.compose(sheets, C['sea'])
    img = P.overlay_rivers(img, LANDPX)
    img = P.overlay_relief(img, LANDPX)
    img.convert('RGB').save(path)
    return path


if __name__ == '__main__':
    import time
    S = build_states()
    names = sys.argv[1:] or list(S)
    for n in names:
        t = time.time()
        render_state(n, S[n])
        print(n, round(time.time() - t, 1), 's', flush=True)
