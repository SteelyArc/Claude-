"""Frame compositor for the TikTok video (1080x1920, 30 fps)."""
import json, math, os, sys, subprocess
import numpy as np
import cairo
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from shapely.ops import unary_union

import paper as P
from script import SCENES
from data import pieces, clean

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
BUILD = os.path.join(ROOT, 'build')
FONTS = os.path.join(ROOT, 'fonts')
FW, FH, FPS = 1080, 1920, 30
FOCUS = (540, 900)          # where the camera target sits on screen

D = pieces()
GEOMS = {k: v for k, v in D.items() if hasattr(v, 'area')}
GEOMS['lithuania'] = D['s21']['Lithuania']
GEOMS['kresy'] = D['riga']
GEOMS['P18'] = D['P18']
from data import partitions
PT = partitions()
GEOMS.update(PT)
GEOMS['parts72'] = unary_union([PT['rus72'], PT['pru72'], PT['aus72']])
GEOMS['parts93'] = unary_union([PT['rus93'], PT['pru93']])
GEOMS['parts95'] = unary_union([PT['rus95'], PT['pru95'], PT['aus95']])
for k in list(GEOMS):
    GEOMS[k] = clean(GEOMS[k])


def _lab_pt(g):
    big = max(P.polys(g), key=lambda p: p.area)
    c = big.representative_point()
    cc = big.centroid
    return (cc.x, cc.y) if big.contains(cc) else (c.x, c.y)


def _plab(key, name, year, size=24):
    size = int(size * 1.45)
    x, y = _lab_pt(PT[key])
    return (name + '\n' + year, x, y, size)


# ---------------------------------------------------------------- fonts
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var:
        f.set_variation_by_name(var)
    return f


_F = {}


def F(kind, size):
    key = (kind, size)
    if key not in _F:
        _F[key] = {
            'title': lambda: font('AbrilFatface-Regular.ttf', size),
            'black': lambda: font('ArchivoBlack-Regular.ttf', size),
            'osw': lambda: font('Oswald[wght].ttf', size, 'Bold'),
            'oswm': lambda: font('Oswald[wght].ttf', size, 'Medium'),
            'serif': lambda: font('Lora[wght].ttf', size, 'Bold'),
            'serifr': lambda: font('Lora[wght].ttf', size, 'Medium'),
            'type': lambda: font('SpecialElite-Regular.ttf', size),
        }[kind]()
    return _F[key]


# ---------------------------------------------------------------- data for overlays
CITIES = {
    'Warsaw': (21.01, 52.23, True), 'Kraków': (19.94, 50.06, False), 'Lwów': (24.03, 49.84, False),
    'Wilno': (25.28, 54.69, False), 'Poznań': (16.93, 52.41, False), 'Gdańsk': (18.65, 54.35, False),
    'Katowice': (19.02, 50.26, False), 'Kyiv': (30.52, 50.45, False), 'Lublin': (22.57, 51.25, False),
    'Kaunas': (23.9, 54.9, False), 'Gdynia': (18.53, 54.52, False), 'Cieszyn': (18.63, 49.75, False),
}
CITY_LABEL = {'Gdańsk': 'Gdańsk (Danzig)', 'Wilno': 'Wilno (Vilnius)', 'Lwów': 'Lwów (Lviv)'}

COL = dict(ink=(0.17, 0.12, 0.08), cream=(0.96, 0.93, 0.85), pol=(0.78, 0.27, 0.22),
           sov=(0.36, 0.16, 0.15), ger=(0.31, 0.36, 0.43), rus=(0.42, 0.48, 0.31), pl_arrow=(0.97, 0.94, 0.88))

ARROWS = {
    'ww1_a': ('rus', [(23.6, 53.4), (22.6, 53.75), (21.2, 53.95)]),
    'ww1_b': ('rus', [(25.6, 50.4), (24.6, 49.95), (23.2, 49.85)]),
    'ww1_c': ('ger', [(17.6, 51.3), (18.9, 51.75), (20.4, 52.05)]),
    'ww1_push1': ('ger', [(20.2, 53.2), (21.6, 52.7), (23.6, 52.55), (25.3, 52.75)]),
    'ww1_push2': ('ger', [(21.0, 49.75), (22.6, 50.4), (24.1, 51.0), (25.3, 51.35)]),
    'to_kyiv': ('pl', [(23.8, 51.0), (26.0, 50.55), (28.4, 50.3), (30.25, 50.45)]),
    'red1': ('sov', [(29.6, 55.0), (27.6, 54.3), (25.2, 53.7), (22.8, 53.05), (21.35, 52.5)]),
    'red3': ('sov', [(29.0, 52.6), (26.5, 52.45), (24.0, 52.25), (21.75, 52.15)]),
    'red2': ('sov', [(30.2, 50.2), (28.0, 50.0), (26.0, 49.95), (24.35, 49.9)]),
    'pl1': ('pl', [(22.2, 51.3), (23.0, 52.1), (24.0, 52.85), (25.3, 53.5)]),
    'pl2': ('pl', [(21.3, 52.5), (22.6, 53.1), (24.2, 53.6), (26.0, 54.0)]),
    'pl3': ('pl', [(23.4, 50.9), (25.2, 51.1), (27.2, 51.4)]),
}
FRONTS = {
    'front1915': [(24.1, 56.95), (25.9, 56.0), (26.6, 55.4), (26.6, 54.6), (26.0, 53.8), (25.9, 53.0),
                  (26.0, 52.2), (25.7, 51.4), (25.9, 50.5), (25.5, 49.6), (25.8, 48.6), (26.1, 48.2)],
}
TAGS = {
    'pleb': ('Plebiscite, July 1920:\n~97% voted for Germany', (20.8, 53.75)),
    'cieszyn': ('Cieszyn split\nalong the Olza river', (18.4, 49.45)),
    'belarus': ('BELARUS — split', (27.3, 53.4)),
    'ukraine': ('UKRAINE — split', (27.6, 50.4)),
}
_NEIGH18 = [('PRUSSIA', 13.6, 52.4, 28), ('RUSSIA', 33.6, 55.2, 32), ('AUSTRIA', 16.6, 48.0, 28),
            ('OTTOMAN EMPIRE', 29.0, 46.4, 24), ('Baltic Sea', 18.0, 55.9, -28)]
LABELS = {
    'empires': [('GERMAN EMPIRE', 14.6, 52.3, 34), ('RUSSIAN EMPIRE', 27.5, 53.4, 38), ('AUSTRIA-HUNGARY', 19.0, 47.7, 34),
                ('Baltic Sea', 17.6, 55.5, -30), ('SWEDEN', 14.6, 58.0, 24)],
    'plc': [('POLISH–\nLITHUANIAN\nCOMMONWEALTH', 24.6, 53.1, 34)] + _NEIGH18,
    'p72': [('POLAND–\nLITHUANIA', 24.0, 53.0, 30), _plab('rus72', 'RUSSIA', '1772'), _plab('pru72', 'PRUSSIA', '1772', 20),
            _plab('aus72', 'AUSTRIA', '1772')] + _NEIGH18,
    'p93': [('POLAND', 22.0, 52.6, 28), _plab('rus72', 'RUSSIA', '1772'), _plab('pru72', 'PRUSSIA', '1772', 20),
            _plab('aus72', 'AUSTRIA', '1772'), _plab('rus93', 'RUSSIA', '1793', 28), _plab('pru93', 'PRUSSIA', '1793')] + _NEIGH18,
    'p95': [_plab('rus72', 'RUSSIA', '1772'), _plab('pru72', 'PRUSSIA', '1772', 20), _plab('aus72', 'AUSTRIA', '1772'),
            _plab('rus93', 'RUSSIA', '1793', 28), _plab('pru93', 'PRUSSIA', '1793'), _plab('rus95', 'RUSSIA', '1795', 26),
            _plab('pru95', 'PRUSSIA', '1795', 22), _plab('aus95', 'AUSTRIA', '1795', 20)] + _NEIGH18,
    'partitions': [('RUSSIAN\nPARTITION', 22.6, 52.7, 30), ('PRUSSIAN\nPARTITION', 17.3, 52.75, 26),
                   ('AUSTRIAN PARTITION', 22.3, 49.6, 26), ('GERMAN EMPIRE', 13.8, 51.6, 26),
                   ('RUSSIAN EMPIRE', 28.3, 54.2, 28), ('AUSTRIA-HUNGARY', 18.6, 47.6, 26), ('Baltic Sea', 17.6, 55.5, -28)],
    'regency': [('KINGDOM OF\nPOLAND', 20.6, 52.1, 34), ('GERMAN EMPIRE', 14.6, 52.3, 30), ('RUSSIAN EMPIRE', 27.5, 53.4, 32),
                ('AUSTRIA-HUNGARY', 19.0, 47.7, 30), ('Baltic Sea', 17.6, 55.5, -28)],
    '1918': [('POLAND', 21.1, 51.6, 46), ('GERMANY', 14.6, 52.3, 34), ('LITHUANIA', 24.6, 55.3, 26),
             ('CZECHO-\nSLOVAKIA', 16.4, 49.6, 24), ('SOVIET RUSSIA', 30.0, 54.5, 30), ('ROMANIA', 25.5, 46.5, 28),
             ('HUNGARY', 20.0, 47.2, 26), ('Baltic Sea', 17.6, 55.5, -28)],
    'versailles_pre': [('POLAND', 20.2, 52.2, 46), ('GERMANY', 14.6, 52.3, 34), ('LITHUANIA', 24.0, 55.5, 26),
                       ('Baltic Sea', 17.2, 55.4, -28)],
    'versailles': [('POLAND', 20.2, 52.2, 46), ('GERMANY', 14.6, 52.3, 34), ('EAST\nPRUSSIA', 21.0, 54.35, 26),
                   ('LITHUANIA', 24.0, 55.5, 26), ('Baltic Sea', 17.2, 55.4, -28), ('"Polish Corridor"', 17.75, 53.75, -22)],
    'war': [('POLAND', 20.4, 52.0, 46), ('SOVIET RUSSIA', 31.0, 54.6, 34), ('LITHUANIA', 24.0, 55.5, 26),
            ('ROMANIA', 26.5, 46.8, 28), ('GERMANY', 14.6, 52.3, 30), ('EAST\nPRUSSIA', 21.0, 54.35, 24),
            ('Belarus', 27.8, 53.3, -26), ('Ukraine', 30.5, 49.4, -26)],
    'wilno': [('POLAND', 22.4, 52.9, 40), ('LITHUANIA', 23.4, 55.45, 28), ('LATVIA', 25.4, 56.6, 28),
              ('EAST PRUSSIA', 21.0, 54.35, 22), ('SOVIET RUSSIA', 28.6, 55.0, 28), ('"Central Lithuania"', 25.9, 54.1, -20)],
    'riga': [('POLAND', 21.6, 52.0, 44), ('SOVIET RUSSIA', 29.6, 53.8, 32), ('LITHUANIA', 23.4, 55.45, 26),
             ('LATVIA', 25.4, 56.6, 26), ('ROMANIA', 26.5, 47.0, 26), ('EAST PRUSSIA', 21.0, 54.35, 22)],
    'silesia': [('GERMANY', 17.3, 50.85, 30), ('POLAND', 20.0, 50.75, 34), ('CZECHOSLOVAKIA', 18.0, 49.45, 24),
                ('Upper Silesia', 18.55, 50.55, -24)],
    'final': [('POLAND', 21.6, 52.2, 54), ('GERMANY', 14.6, 52.3, 32), ('EAST PRUSSIA', 21.0, 54.35, 22),
              ('LITHUANIA', 23.6, 55.45, 24), ('LATVIA', 25.6, 56.6, 24), ('USSR', 29.8, 53.5, 36),
              ('CZECHOSLOVAKIA', 16.9, 49.5, 24), ('ROMANIA', 26.5, 47.0, 26), ('HUNGARY', 19.5, 47.2, 24),
              ('Baltic Sea', 17.4, 55.5, -28), ('AUSTRIA', 14.6, 47.6, 22)],
    'anschluss': [('POLAND', 21.6, 52.2, 54), ('GERMANY', 14.6, 52.3, 32), ('EAST PRUSSIA', 21.0, 54.35, 22),
                  ('LITHUANIA', 23.6, 55.45, 24), ('USSR', 29.8, 53.5, 36), ('CZECHOSLOVAKIA', 16.9, 49.5, 24),
                  ('ROMANIA', 26.5, 47.0, 26), ('HUNGARY', 19.5, 47.2, 24), ('Baltic Sea', 17.4, 55.5, -28),
                  ('(former Austria)', 14.6, 47.6, -22)],
    '1938': [('POLAND', 21.6, 52.2, 54), ('GERMANY', 14.6, 52.3, 32), ('CZECHO-SLOVAKIA', 18.8, 48.75, 22),
             ('HUNGARY', 19.5, 47.2, 24), ('USSR', 29.8, 53.5, 36), ('LITHUANIA', 23.6, 55.45, 24),
             ('ROMANIA', 26.5, 47.0, 26), ('Zaolzie', 18.05, 49.72, -24), ('EAST PRUSSIA', 21.0, 54.35, 22)],
    'final38': [('POLAND', 21.6, 52.2, 54), ('GERMANY', 14.6, 52.3, 32), ('EAST PRUSSIA', 21.0, 54.35, 22),
                ('LITHUANIA', 23.6, 55.45, 24), ('LATVIA', 25.6, 56.6, 24), ('USSR', 29.8, 53.5, 36),
                ('CZECHO-SLOVAKIA', 18.8, 48.75, 22), ('ROMANIA', 26.5, 47.0, 26), ('HUNGARY', 19.5, 47.2, 24),
                ('Baltic Sea', 17.4, 55.5, -28)],
}


# ---------------------------------------------------------------- timeline
def ease(u):
    u = min(1, max(0, u))
    return u * u * (3 - 2 * u)


def build_timeline():
    meta = json.load(open(os.path.join(BUILD, 'vo', 'meta.json')))
    durs = {(m['scene'], m['line']): m['dur'] for m in meta}
    t = 1.2
    TL = dict(scenes=[], lines=[], trans=[], labels=[], vo=[])
    for si, sc in enumerate(SCENES):
        s0 = t
        t += 0.35
        scn = dict(i=si, start=s0, cities=[], arrows=[], pulses=[], fronts=[], tags=[], bursts=[], stats=[],
                   darken=None, endcard=None)
        if si == 0:
            TL['trans'].append(dict(t=0, dur=0, kind='set', to=sc['state']))
        for li, (cap, evs) in enumerate(sc['lines']):
            d = durs[(si, li)]
            ls, le = t, t + d
            TL['lines'].append(dict(start=ls, end=le, text=cap))
            TL['vo'].append(dict(t=ls, path=[m['path'] for m in meta if m['scene'] == si and m['line'] == li][0]))
            ai = 0
            for ev in evs:
                k = ev[0]
                if k == 'fade':
                    TL['trans'].append(dict(t=ls + ev[2], dur=ev[3], kind='fade', to=ev[1]))
                elif k == 'drop':
                    TL['trans'].append(dict(t=ls + ev[3], dur=1.5, kind='drop', piece=ev[1], to=ev[2]))
                elif k == 'dropfade':
                    TL['trans'].append(dict(t=ls + ev[3], dur=1.8, kind='dropfade', piece=ev[1], to=ev[2]))
                elif k == 'labels':
                    TL['labels'].append((ls - 0.2, ev[1]))
                elif k == 'city':
                    scn['cities'].append((ls + 0.25 + 0.25 * len([c for c in scn['cities'] if c[0] > ls]), ev[1]))
                elif k == 'arrow':
                    scn['arrows'].append((ls + 0.2 + 0.45 * ai, ev[1]))
                    ai += 1
                elif k == 'pulse':
                    scn['pulses'].append((ls, le + 0.8, ev[1]))
                elif k == 'front':
                    scn['fronts'].append((ls + ev[2], ev[1]))
                elif k == 'tag':
                    scn['tags'].append((ls + 0.4, ev[1]))
                elif k == 'burst':
                    scn['bursts'].append((ls + 0.1, ev[1]))
                elif k == 'stat':
                    scn['stats'].append((ls + 0.3, le + 1.5, ev[1]))
                elif k == 'darken':
                    scn['darken'] = ls + ev[1]
                elif k == 'endcard':
                    scn['endcard'] = ls
            t = le + 0.42
        t += 0.35
        if si == len(SCENES) - 1:
            t += 3.0
        scn['end'] = t
        TL['scenes'].append(scn)
    TL['total'] = t
    TL['trans'].sort(key=lambda x: x['t'])
    return TL


# ---------------------------------------------------------------- camera
def cam_at(TL, t):
    scs = TL['scenes']
    i = max(j for j, s in enumerate(scs) if s['start'] <= t or j == 0)
    s = scs[i]
    sc = SCENES[i]
    u = (t - s['start']) / (s['end'] - s['start'])
    a, b = sc['cam'], sc['cam2']

    def mix(a, b, k):
        ax, ay = P.proj(a[0], a[1])
        bx, by = P.proj(b[0], b[1])
        w = 0.82 * math.exp(math.log(a[2]) * (1 - k) + math.log(b[2]) * k)
        return ax + (bx - ax) * k, ay + (by - ay) * k, w
    cur = mix(a, b, ease(u) * 0.85 + u * 0.15)
    if i > 0:
        pa, pb = SCENES[i - 1]['cam'], SCENES[i - 1]['cam2']
        prev = mix(pa, pb, 1.0)
        k = ease((t - s['start']) / 1.4)
        if k < 1:
            # interpolate in (x,y,log w)
            cur = (prev[0] + (cur[0] - prev[0]) * k, prev[1] + (cur[1] - prev[1]) * k,
                   math.exp(math.log(prev[2]) * (1 - k) + math.log(cur[2]) * k))
    return cur  # projected x, y, width units


class View:
    def __init__(self, cam):
        self.cx, self.cy, self.w = cam
        self.s = FW / self.w  # px per unit

    def px(self, lon, lat):
        x, y = P.proj(lon, lat)
        return (x - self.cx) * self.s + FOCUS[0], (y - self.cy) * self.s + FOCUS[1]

    def master_box(self):
        # frame (0,0)-(FW,FH) -> projected -> master px
        x0 = self.cx - FOCUS[0] / self.s
        y0 = self.cy - FOCUS[1] / self.s
        x1 = x0 + FW / self.s
        y1 = y0 + FH / self.s
        return ((x0 - P.MX0) * P.PPU, (y0 - P.MY0) * P.PPU, (x1 - P.MX0) * P.PPU, (y1 - P.MY0) * P.PPU)

    def geom(self, g):
        from shapely import affinity
        # lon/lat -> frame px
        a = P.COSF * self.s
        return affinity.affine_transform(g, [a, 0, 0, -self.s, (-P.LON0 * P.COSF - self.cx) * self.s + FOCUS[0],
                                             (P.LAT0 - self.cy) * self.s + FOCUS[1]])


_MASTERS = {}


def master(name):
    if name not in _MASTERS:
        if len(_MASTERS) > 4:
            _MASTERS.pop(next(iter(_MASTERS)))
        _MASTERS[name] = Image.open(os.path.join(BUILD, f'master_{name}.png')).convert('RGB')
    return _MASTERS[name]


def view_img(name, view):
    return master(name).resize((FW, FH), Image.BICUBIC, box=view.master_box(), reducing_gap=None)


# ---------------------------------------------------------------- base map with transitions
def mask_frame(g):
    return P.mask_of(g, FW, FH)


def base_frame(TL, t, view):
    state = None
    active = None
    for tr in TL['trans']:
        if tr['t'] <= t:
            if tr['kind'] == 'set':
                state = tr['to']
                continue
            if t < tr['t'] + tr['dur']:
                active = (tr, state)
            state = tr['to']
    if active is None:
        return view_img(state, view), []
    tr, before = active
    u = (t - tr['t']) / tr['dur']
    A = view_img(before, view)
    B = view_img(tr['to'], view)
    sfx = []
    if tr['kind'] == 'fade':
        return Image.blend(A, B, ease(u)), sfx
    # drop / dropfade
    g = view.geom(GEOMS[tr['piece']])
    m = mask_frame(g)
    if tr['kind'] == 'dropfade':
        under = Image.blend(A, B, ease(min(1, u * 1.6)))
        under.paste(A, (0, 0), m) if u < 0.62 else None
        base = under
        pu = max(0.0, (u - 0.25) / 0.75)
    else:
        base = A.copy()
        pu = u
    if pu <= 0:
        return base, sfx
    # piece animation: falls from above, lands with small bounce
    if pu < 0.7:
        k = pu / 0.7
        h = (1 - k) ** 2 * 110
    else:
        k = (pu - 0.7) / 0.3
        h = math.sin(k * math.pi) * 9 * (1 - k)
    alpha = min(1.0, pu * 3.0)
    sc = 1 + h / 900
    if pu >= 0.7:
        base.paste(B, (0, 0), m)   # piece now in place; fill hole
    cx, cy = g.centroid.x, g.centroid.y
    # transformed piece
    piece = B.copy()
    piece.putalpha(m)
    # affine: output -> input mapping for scale about centroid then lift
    inv = 1 / sc
    piece_t = piece.transform((FW, FH), Image.AFFINE,
                              (inv, 0, cx - cx * inv, 0, inv, cy - cy * inv + h * inv), resample=Image.BILINEAR)
    pm = piece_t.getchannel('A')
    if pu < 0.7:
        base.paste(A, (0, 0), m)
    # shadow on the ground
    sh = m.filter(ImageFilter.GaussianBlur(6 + h * 0.25))
    sh = ImageChops.offset(sh, int(4 + h * 0.25), int(8 + h * 0.45))
    sh = sh.point(lambda v: int(v * (0.55 - min(0.25, h / 400)) * alpha))
    base.paste((25, 15, 8), (0, 0), sh)
    pm = pm.point(lambda v: int(v * alpha))
    base.paste(piece_t.convert('RGB'), (0, 0), pm)
    # landing flash
    if pu > 0.7:
        fl = (1 - (pu - 0.7) / 0.3) * 0.28
        base.paste((255, 245, 220), (0, 0), m.point(lambda v: int(v * fl)))
    return base, sfx


# ---------------------------------------------------------------- vector overlays
def cairo_surface():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, FW, FH)
    ctx = cairo.Context(surf)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    return surf, ctx


def catmull(pts, n=24):
    pts = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
                                    (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(2)))
    out.append(pts[-2])
    return out


def draw_arrow(ctx, pts_px, prog, kind, scale=1.0):
    pts = catmull(pts_px)
    # cumulative length
    L = [0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = L[-1] * prog
    if total < 8:
        return
    sel = [p for p, l in zip(pts, L) if l <= total]
    # interpolate final
    for i in range(1, len(L)):
        if L[i] > total:
            f = (total - L[i - 1]) / (L[i] - L[i - 1])
            a, b = pts[i - 1], pts[i]
            sel.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            break
    if len(sel) < 2:
        return
    w_tail, w_body = 6 * scale, 17 * scale
    head_len, head_w = 44 * scale, 34 * scale
    # trim body for head
    tip = sel[-1]
    # find point head_len back
    acc = 0
    base_i = len(sel) - 1
    for i in range(len(sel) - 1, 0, -1):
        acc += math.hypot(sel[i][0] - sel[i - 1][0], sel[i][1] - sel[i - 1][1])
        if acc >= head_len:
            base_i = i - 1
            break
    else:
        base_i = 0
    body = sel[:base_i + 1]
    hb = body[-1]
    dx, dy = tip[0] - hb[0], tip[1] - hb[1]
    dl = math.hypot(dx, dy) or 1
    nx, ny = -dy / dl, dx / dl
    left, right = [], []
    n = len(body)
    for i, p in enumerate(body):
        if i < n - 1:
            q = body[i + 1]
            ddx, ddy = q[0] - p[0], q[1] - p[1]
        else:
            ddx, ddy = dx, dy
        l = math.hypot(ddx, ddy) or 1
        px_, py_ = -ddy / l, ddx / l
        w = w_tail + (w_body - w_tail) * (i / max(1, n - 1)) ** 0.6
        left.append((p[0] + px_ * w / 2, p[1] + py_ * w / 2))
        right.append((p[0] - px_ * w / 2, p[1] - py_ * w / 2))
    poly = left + [(hb[0] + nx * head_w / 2, hb[1] + ny * head_w / 2), tip,
                   (hb[0] - nx * head_w / 2, hb[1] - ny * head_w / 2)] + right[::-1]
    fill = {'pl': COL['pl_arrow'], 'sov': COL['sov'], 'ger': COL['ger'], 'rus': COL['rus']}[kind]
    edge = {'pl': COL['pol'], 'sov': (0.2, 0.08, 0.07), 'ger': (0.18, 0.2, 0.25), 'rus': (0.24, 0.28, 0.17)}[kind]
    ctx.new_path()
    ctx.move_to(*poly[0])
    for p in poly[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*fill, 1)
    ctx.fill_preserve()
    ctx.set_line_width(4 * scale)
    ctx.set_source_rgba(*edge, 1)
    ctx.stroke()
    # highlight fold line down the middle
    ctx.new_path()
    ctx.move_to(*body[0])
    for p in body[1:]:
        ctx.line_to(*p)
    ctx.line_to(*tip)
    ctx.set_line_width(1.6 * scale)
    ctx.set_source_rgba(1, 1, 1, 0.35 if kind != 'pl' else 0.0)
    ctx.stroke()


def path_poly(ctx, g):
    P.path_geom(ctx, g)


def rounded_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def text_size(draw, txt, f, spacing=4):
    b = draw.multiline_textbbox((0, 0), txt, font=f, spacing=spacing, align='center')
    return b[2] - b[0], b[3] - b[1], b


def paper_tag(obj_draw, ctx, x, y, txt, f, alpha=1.0, color=(0.97, 0.94, 0.86), ink=(43, 33, 24), pad=(16, 10),
              anchor='mm', spacing=4, rot=0):
    w, h, b = text_size(obj_draw, txt, f, spacing)
    W, H = w + pad[0] * 2, h + pad[1] * 2
    if anchor == 'mm':
        x0, y0 = x - W / 2, y - H / 2
    elif anchor == 'lm':
        x0, y0 = x, y - H / 2
    else:
        x0, y0 = x - W / 2, y
    ctx.save()
    rounded_rect(ctx, x0, y0, W, H, 6)
    ctx.set_source_rgba(*color, alpha)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.45, 0.36, 0.25, 0.5 * alpha)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()
    obj_draw.multiline_text((x0 + pad[0] - b[0], y0 + pad[1] - b[1]), txt, font=f, fill=ink + (int(255 * alpha),),
                            spacing=spacing, align='center')
    return x0, y0, W, H


def wrap_caption(text, maxc=28):
    words = text.split()
    chunks, cur = [], []
    # build chunks of up to 2 lines each ~maxc chars
    lines, line = [], ''
    for w in words:
        if len(line) + len(w) + 1 > maxc and line:
            lines.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    if line:
        lines.append(line)
    for i in range(0, len(lines), 2):
        chunks.append('\n'.join(lines[i:i + 2]))
    return chunks


# ---------------------------------------------------------------- frame
TEX = None


def grain():
    global TEX
    if TEX is None:
        TEX = P.texture((FW, FH), seed=11)
    return TEX


def vignette():
    yy, xx = np.mgrid[0:FH, 0:FW].astype(np.float32)
    d = np.sqrt(((xx - FW / 2) / (FW * 0.75)) ** 2 + ((yy - FH / 2) / (FH * 0.7)) ** 2)
    return np.clip(1 - 0.38 * np.clip(d - 0.45, 0, 1) ** 1.4, 0, 1)


VIG = None


def label_alpha(TL, t):
    """returns list of (key, alpha) for the label sets visible at t"""
    evs = sorted(TL['labels'])
    cur, prev, tch = None, None, -10
    for te, k in evs:
        if te <= t:
            if k != cur:
                prev, cur, tch = cur, k, te
    a = ease((t - tch) / 0.6)
    out = []
    if cur:
        out.append((cur, a))
    if prev and a < 1:
        out.append((prev, 1 - a))
    return out


def render_frame(TL, fi):
    global VIG
    t = fi / FPS
    view = View(cam_at(TL, t))
    img, _ = base_frame(TL, t, view)
    si = max(j for j, s in enumerate(TL['scenes']) if s['start'] <= t or j == 0)
    scn = TL['scenes'][si]
    s_end = scn['end']
    fade_out = 1 - ease((t - (s_end - 0.45)) / 0.45) if si < len(SCENES) - 1 else 1.0

    # --- printed layer (no shadow): country labels, pulses, fronts
    psurf, pctx = cairo_surface()
    print_img = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    pd = ImageDraw.Draw(print_img)
    for key, a in label_alpha(TL, t):
        for (txt, lon, lat, size) in LABELS[key]:
            x, y = view.px(lon, lat)
            if not (-200 < x < FW + 200 and -100 < y < FH + 100):
                continue
            ital = size < 0
            sz = abs(size)
            sz = int(sz * min(1.35, max(0.92, 9.0 / view.w)))
            f = F('serifr' if ital else 'serif', sz)
            if not ital:
                txt2 = ' '.join(txt)  # letter spacing
                txt2 = txt2.replace(' \n ', '\n')
            else:
                txt2 = txt
            w, h, b = text_size(pd, txt2, f)
            ink = (54, 40, 28) if not ital else (60, 70, 78)
            if '\n17' in txt or txt.startswith('POL') or txt.startswith('KINGDOM'):
                ink = (255, 246, 232)
            ox, oy = x - w / 2 - b[0], y - h / 2 - b[1]
            emb = (255, 250, 238, int(110 * a)) if ink[0] < 200 else (90, 20, 15, int(150 * a))
            pd.multiline_text((ox + 1.5, oy + 1.5), txt2, font=f, fill=emb, spacing=2, align='center')
            pd.multiline_text((ox, oy), txt2, font=f, fill=ink + (int(225 * a),), spacing=2, align='center')
    for (t0, t1, key) in scn['pulses']:
        if t0 <= t <= t1:
            a = ease((t - t0) / 0.4) * (1 - ease((t - (t1 - 0.5)) / 0.5))
            g = view.geom(GEOMS[key])
            pctx.new_path()
            path_poly(pctx, g)
            pulse = 0.5 + 0.5 * math.sin((t - t0) * 5)
            pctx.set_source_rgba(1, 0.97, 0.85, (0.10 + 0.12 * pulse) * a)
            pctx.fill_preserve()
            pctx.set_line_width(9)
            pctx.set_source_rgba(0.2, 0.12, 0.06, 0.35 * a)
            pctx.stroke_preserve()
            pctx.set_line_width(4.5)
            pctx.set_dash([16, 11], -(t - t0) * 60)
            pctx.set_source_rgba(1, 0.97, 0.88, 0.95 * a)
            pctx.stroke()
            pctx.set_dash([])
    for (t0, key) in scn['fronts']:
        if t >= t0:
            prog = ease((t - t0) / 1.6)
            pts = catmull([view.px(*p) for p in FRONTS[key]])
            n = max(2, int(len(pts) * prog))
            pctx.new_path()
            pctx.move_to(*pts[0])
            for p in pts[1:n]:
                pctx.line_to(*p)
            pctx.set_line_width(7)
            pctx.set_source_rgba(0.15, 0.1, 0.08, 0.9 * fade_out)
            pctx.set_dash([22, 10])
            pctx.stroke()
            pctx.set_dash([])
            if prog > 0.5:
                x, y = pts[len(pts) // 2]
                lab_a = ease((prog - 0.5) * 3) * fade_out
                pd.text((x + 22, y - 20), 'FRONT LINE\n1915', font=F('osw', 30), fill=(40, 28, 20, int(230 * lab_a)),
                        spacing=0)
    pimg = P.cairo_to_pil(psurf)
    img = img.convert('RGBA')
    img.alpha_composite(pimg)
    img.alpha_composite(print_img)

    # --- object layer with drop shadows: arrows, pins, tags, stats, UI
    osurf, octx = cairo_surface()
    obj_txt = Image.new('RGBA', (FW, FH), (0, 0, 0, 0))
    od = ImageDraw.Draw(obj_txt)
    for (t0, key) in scn['arrows']:
        if t >= t0:
            kind, pts = ARROWS[key]
            prog = ease((t - t0) / 1.5)
            octx.push_group()
            draw_arrow(octx, [view.px(*p) for p in pts], prog, kind, scale=min(1.15, max(0.75, 10.0 / view.w)))
            octx.pop_group_to_source()
            octx.paint_with_alpha(fade_out)
    # bursts
    for (t0, name) in scn['bursts']:
        if t >= t0:
            x, y = view.px(*CITIES[name][:2])
            k = (t - t0)
            for r_i in range(3):
                kk = (k * 0.9 + r_i * 0.33) % 1.0
                octx.arc(x, y, 30 + kk * 140, 0, 2 * math.pi)
                octx.set_line_width(6 * (1 - kk))
                octx.set_source_rgba(1, 0.95, 0.8, (1 - kk) * 0.9 * fade_out)
                octx.stroke()
            # star
            a = ease(k / 0.4) * fade_out
            sp = 1 + 0.08 * math.sin(k * 6)
            octx.save()
            octx.translate(x, y)
            octx.rotate(k * 0.3)
            for i in range(16):
                ang = i * math.pi / 8
                r = (58 if i % 2 == 0 else 26) * sp
                octx.line_to(math.cos(ang) * r, math.sin(ang) * r)
            octx.close_path()
            octx.set_source_rgba(0.97, 0.94, 0.86, a)
            octx.fill_preserve()
            octx.set_source_rgba(*COL['pol'], a)
            octx.set_line_width(4)
            octx.stroke()
            octx.restore()
            if k > 0.5:
                aa = ease((k - 0.5) / 0.4) * fade_out
                paper_tag(od, octx, x, y + 120, 'BATTLE OF WARSAW\nAugust 1920', F('osw', 34), alpha=aa,
                          color=(0.78, 0.27, 0.22), ink=(255, 246, 232))
    # cities
    for (t0, name) in scn['cities']:
        if t < t0:
            continue
        lon, lat, cap = CITIES[name]
        x, y = view.px(lon, lat)
        k = ease((t - t0) / 0.45) * fade_out
        pop = 1 + 0.35 * math.sin(min(1, (t - t0) / 0.45) * math.pi)
        r = (13 if cap else 10) * pop
        octx.arc(x, y, r, 0, 2 * math.pi)
        octx.set_source_rgba(0.97, 0.94, 0.86, k)
        octx.fill_preserve()
        octx.set_source_rgba(*COL['ink'], k)
        octx.set_line_width(3.5)
        octx.stroke()
        octx.arc(x, y, r * 0.45, 0, 2 * math.pi)
        octx.set_source_rgba(*(COL['pol'] if cap else COL['ink']), k)
        octx.fill()
        lab = CITY_LABEL.get(name, name)
        side = 'lm'
        tx = x + r + 10
        fsz = 34 if cap else 30
        w, h, _ = text_size(od, lab, F('osw', fsz))
        if tx + w + 30 > FW - 20:
            tx = x - r - 10 - w - 32
        paper_tag(od, octx, tx, y, lab, F('osw', fsz), alpha=k, anchor='lm', pad=(14, 6))
    # tags
    for (t0, key) in scn['tags']:
        if t >= t0:
            txt, (lon, lat) = TAGS[key]
            x, y = view.px(lon, lat)
            k = ease((t - t0) / 0.5) * fade_out
            paper_tag(od, octx, x, y - (1 - k) * 30, txt, F('oswm', 32), alpha=k, color=(0.99, 0.96, 0.78))
    # stats
    for (t0, t1, txt) in scn['stats']:
        if t0 <= t <= t1 + 0.5:
            parts = txt.split('|')
            for i, ptxt in enumerate(parts):
                k = ease((t - t0 - i * 0.5) / 0.5) * (1 - ease((t - t1) / 0.5))
                if k <= 0:
                    continue
                y = 1170 + i * 112 + (1 - k) * 40
                paper_tag(od, octx, FW / 2, y, ptxt, F('black', 56), alpha=k,
                          color=(0.78, 0.27, 0.22) if i == 0 else (0.97, 0.94, 0.86),
                          ink=(255, 246, 232) if i == 0 else (43, 33, 24), pad=(28, 14))

    # --- UI: year badge / title
    if si == 0 and t < scn['end'] - 0.3:
        a = ease((t - 0.2) / 0.7) * (1 - ease((t - (scn['end'] - 0.8)) / 0.5))
        yoff = (1 - ease((t - 0.2) / 0.7)) * -60
        octx.save()
        rounded_rect(octx, 70, 190 + yoff, FW - 140, 300, 14)
        octx.set_source_rgba(0.97, 0.94, 0.86, a)
        octx.fill()
        rounded_rect(octx, 90, 210 + yoff, FW - 180, 260, 8)
        octx.set_source_rgba(*COL['pol'], 0.9 * a)
        octx.set_line_width(3)
        octx.stroke()
        octx.restore()
        f1, f2, f3 = F('osw', 40), F('title', 92), F('osw', 46)
        for txt, f, y, ink in (("THE MAKING OF", f1, 245, (43, 33, 24)), ("POLAND'S BORDERS", f2, 300, (198, 70, 57)),
                               ("1914  –  1938", f3, 410, (43, 33, 24))):
            w, h, b = text_size(od, txt, f)
            od.text((FW / 2 - w / 2 - b[0], y + yoff - b[1]), txt, font=f, fill=ink + (int(255 * a),))
    elif si > 0:
        sc = SCENES[si]
        k = ease((t - scn['start']) / 0.5)
        prev_year = SCENES[si - 1]['year'] if si > 1 else None
        changed = prev_year != sc['year'] or SCENES[si - 1]['sub'] != sc['sub']
        a = 1.0 if not changed or k >= 1 else k
        yoff = 0 if not changed else (1 - k) * -40
        fy, fs = F('title', 96), F('osw', 38)
        yr = sc['year']
        w, h, b = text_size(od, yr, fy)
        ws = text_size(od, sc['sub'].upper(), fs)[0] if sc['sub'] else 0
        W = max(w + 80, ws + 70, 420)
        x0 = FW / 2 - W / 2
        y0 = 200 + yoff
        octx.save()
        rounded_rect(octx, x0, y0, W, 190 if sc['sub'] else 140, 12)
        octx.set_source_rgba(0.97, 0.94, 0.86, a)
        octx.fill()
        octx.restore()
        od.text((FW / 2 - w / 2 - b[0], y0 + 18 - b[1]), yr, font=fy, fill=(198, 70, 57, int(255 * a)))
        if sc['sub']:
            sub = sc['sub'].upper()
            w2, h2, b2 = text_size(od, sub, fs)
            octx.rectangle(x0 + 30, y0 + 128, W - 60, 2)
            octx.set_source_rgba(0.45, 0.36, 0.25, 0.6 * a)
            octx.fill()
            od.text((FW / 2 - w2 / 2 - b2[0], y0 + 138 - b2[1]), sub, font=fs, fill=(43, 33, 24, int(255 * a)))

    # --- captions
    for ln in TL['lines']:
        if ln['start'] - 0.05 <= t <= ln['end'] + 0.3:
            chunks = wrap_caption(ln['text'])
            tot = sum(len(c) for c in chunks)
            acc = ln['start']
            for c in chunks:
                d = (ln['end'] - ln['start']) * len(c) / tot
                if acc <= t < acc + d or (c == chunks[-1] and t >= acc):
                    k = ease((t - acc) / 0.15)
                    f = F('black', 56)
                    w, h, b = text_size(od, c, f, spacing=10)
                    y = 1470 - h / 2
                    octx.save()
                    rounded_rect(octx, FW / 2 - w / 2 - 30, y - 22 + (1 - k) * 10, w + 60, h + 44, 10)
                    octx.set_source_rgba(0.97, 0.94, 0.86, 0.96)
                    octx.fill()
                    octx.restore()
                    od.multiline_text((FW / 2 - w / 2 - b[0], y - b[1] + (1 - k) * 10), c, font=f,
                                      fill=(43, 33, 24, 255), spacing=10, align='center')
                    break
                acc += d
            break

    # --- endcard
    if scn['endcard'] and t >= scn['endcard'] - 0.2:
        k = ease((t - scn['endcard'] + 0.2) / 0.6)
        octx.save()
        rounded_rect(octx, 110, 760 - (1 - k) * 60, FW - 220, 330, 16)
        octx.set_source_rgba(*COL['pol'], k)
        octx.fill()
        octx.restore()
        for txt, f, y in (("FOLLOW FOR", F('osw', 56), 795), ("PART 2", F('title', 128), 860),
                          ("1939 – 1945", F('osw', 50), 1010)):
            w, h, b = text_size(od, txt, f)
            od.text((FW / 2 - w / 2 - b[0], y - (1 - k) * 60 - b[1]), txt, font=f, fill=(255, 246, 232, int(255 * k)))

    oimg = P.cairo_to_pil(osurf)
    oimg.alpha_composite(obj_txt)
    al = oimg.getchannel('A')
    sh = ImageChops.offset(al.filter(ImageFilter.GaussianBlur(7)), 5, 9).point(lambda v: int(v * 0.45))

    # darken (outro)
    if scn['darken'] and t >= scn['darken']:
        k = ease((t - scn['darken']) / 2.5)
        dk = Image.new('RGBA', (FW, FH), (25, 8, 6, int(150 * k)))
        img.alpha_composite(dk)

    img.paste((20, 12, 6), (0, 0), sh)
    img.alpha_composite(oimg)

    # global grain + vignette
    if VIG is None:
        VIG = vignette()
    arr = np.asarray(img.convert('RGB'), np.float32)
    arr *= (VIG * (0.6 + 0.4 * grain()))[..., None] if False else (VIG * grain())[..., None]
    # fade from/to black at start/end
    k = min(ease(t / 0.6), 1 - ease((t - (TL['total'] - 0.6)) / 0.6))
    arr *= k
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')


def render_range(a, b, out):
    TL = build_timeline()
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{FW}x{FH}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(a, b):
        p.stdin.write(render_frame(TL, fi).tobytes())
        if fi % 150 == 0:
            print(out, fi, flush=True)
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    TL = build_timeline()
    if sys.argv[1] == 'info':
        print('total', TL['total'], 'frames', int(TL['total'] * FPS))
        for s in TL['scenes']:
            print(SCENES[s['i']]['id'], round(s['start'], 2), round(s['end'], 2))
    elif sys.argv[1] == 'still':
        for ts in sys.argv[2:]:
            render_frame(TL, int(float(ts) * FPS)).save(os.path.join(BUILD, f'still_{ts}.png'))
    elif sys.argv[1] == 'range':
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
