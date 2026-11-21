"""Shared story beats + verified geometry for the six v3 style samples (concepts 5-10).
Every sample tells the same 10.5 s beat so the styles can be compared directly:
  0.0-2.0  hook title          2.0-3.2  the Commonwealth c.1770 (documented)
  3.2-4.4  1772 First Partition  4.4-5.6  1793 Second   5.6-6.8  1795 Third (state gone)
  6.8-8.0  'what if' pivot     8.0-10.5 the 1791 state survives (hypothetical)"""
from core import *
from shapely.geometry import box as _box
from shapely.ops import transform as _tr

DUR = 10.5
S73, S91, S93, S95 = (L['stages'][k] for k in ('1773', '1791', '1793', '1795'))
PRE72 = S73['plt_pre72'].buffer(800).buffer(-800)
PLT91 = S91['plt'].buffer(800).buffer(-800)
_ext = _tr(lambda x, y, z=None: FWD.transform(x, y), _box(37.0, 48.0, 62.0, 67.0).segmentize(0.25))
RUSSIA = S73['russia'].union(_ext.difference(S73['sweden'].buffer(2e3)).difference(S73['ottoman'].buffer(2e3))).buffer(0)
NEIGH = dict(prussia=S73['prussia'], russia=RUSSIA, habsburg=S73['habsburg'], ottoman=S73['ottoman'], sweden=S73['sweden'],
             hre=S73['hre'], saxony=S73['saxony'], other=S73['other'])
# annexed pieces per partition, with the annexing power
PIECES = [('1772', 'prussia', S73['loss72_pru']), ('1772', 'russia', S73['loss72_rus']), ('1772', 'habsburg', S73['loss72_aut']),
          ('1793', 'prussia', S93['gain93_pru']), ('1793', 'russia', S93['gain93_rus']),
          ('1795', 'prussia', S95['gain95_pru']), ('1795', 'russia', S95['gain95_rus'].union(S95['gain95_rus_courland'])),
          ('1795', 'habsburg', S95['gain95_aut'])]
BEAT = {'1772': (3.2, 4.4), '1793': (4.4, 5.6), '1795': (5.6, 6.8)}
YEAR_LABEL = {'1772': 'FIRST PARTITION', '1793': 'SECOND PARTITION', '1795': 'THIRD PARTITION'}


def piece_k(year, t, lag=0.0):
    """0..1 progress of an annexation (staggered by power)."""
    a, b = BEAT[year]
    return ease(seg(t, a + 0.1 + lag, a + 0.85 + lag))


def lag_of(power): return {'prussia': 0.0, 'russia': 0.12, 'habsburg': 0.24}[power]


def phase(t):
    """which beat: hook / c1770 / 1772 / 1793 / 1795 / pivot / alt"""
    for name, a, b in (('hook', 0, 2.0), ('c1770', 2.0, 3.2), ('1772', 3.2, 4.4), ('1793', 4.4, 5.6),
                       ('1795', 5.6, 6.8), ('pivot', 6.8, 8.0)):
        if t < b: return name
    return 'alt'


def year_at(t):
    return {'hook': None, 'c1770': '1770', '1772': '1772', '1793': '1793', '1795': '1795', 'pivot': '1791', 'alt': '1791'}[phase(t)]


def status_at(t):
    return 'HYPOTHETICAL' if t >= 8.0 else 'DOCUMENTED HISTORY'


def surviving(t):
    """Commonwealth territory still left at time t (documented sequence)."""
    g = PRE72
    for year, power, geom in PIECES:
        if piece_k(year, t, lag_of(power)) >= 1: g = g.difference(geom.buffer(1500))
    return g


def fit_matrix(bounds, x, y, w, h, pad=0.04):
    """world LAEA bounds -> screen rect (north up)."""
    x0, y0, x1, y1 = bounds
    s = min(w / (x1 - x0), h / (y1 - y0)) * (1 - pad)
    M = skia.Matrix(); M.setTranslate(x + w / 2, y + h / 2); M.preScale(s, -s); M.preTranslate(-(x0 + x1) / 2, -(y0 + y1) / 2)
    return M


VIEW = (ll(13.0, 46.6)[0], ll(20.0, 46.0)[1], ll(35.5, 50.0)[0], ll(24.0, 58.4)[1])   # framing of the Commonwealth + neighbours


def rough_circle(cx, cy, r, seed=0, amp=0.09, n=140):
    """organic, noisy-edged disc (ink / watercolour bloom mask)."""
    p = skia.Path(); rs = np.random.default_rng(seed); ph = rs.uniform(0, 6.28, 5)
    for i in range(n + 1):
        th = i / n * 2 * np.pi
        rr = r * (1 + amp * (np.sin(3 * th + ph[0]) * 0.5 + np.sin(7 * th + ph[1]) * 0.3 + np.sin(13 * th + ph[2]) * 0.2))
        (p.moveTo if i == 0 else p.lineTo)(cx + rr * np.cos(th), cy + rr * np.sin(th))
    p.close(); return p


def noise_tex(h, w, octaves=6, seed=1, base=3):
    import cv2
    rng = np.random.default_rng(seed); acc = np.zeros((h, w), np.float32); amp = 1.0
    for o in range(octaves):
        s = base * 2 ** o
        acc += cv2.resize(rng.normal(0, 1, (max(2, s * h // w), s)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC) * amp; amp *= 0.6
    return (acc - acc.mean()) / (acc.std() + 1e-9)


def bloom_origin(piece, power):
    """point on the piece nearest the annexing power: annexation spreads from there."""
    from shapely.ops import nearest_points
    return nearest_points(piece, NEIGH[power].centroid)[0].coords[0]


def piece_radius(piece, o):
    x0, y0, x1, y1 = piece.bounds
    return max(np.hypot(x - o[0], y - o[1]) for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)))


ORIG = [(y, pw, g, bloom_origin(g, pw)) for y, pw, g in PIECES]
ORIG = [(y, pw, g, o, piece_radius(g, o)) for y, pw, g, o in ORIG]
RIVERS = [r for r in L['rivers'] if r['rank'] is not None and r['rank'] <= 6]
