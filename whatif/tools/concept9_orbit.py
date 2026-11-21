"""CONCEPT 9 - Orbit.
A space-documentary look: the story is told on a real orthographic globe seen from orbit, with a thin atmosphere,
sunlit/night shading, a star field and a restrained HUD (coordinates, leader lines, telemetry-style type).
The hook dives from a full Earth down onto Central Europe; partitions spread across the curved surface as luminous
fills; the alternate timeline lights up the 1791 state and the camera pulls back to orbit to show it on the planet."""
import json, cv2
from pyproj import Transformer
from shapely.geometry import shape as _shape
from shapely.ops import unary_union
from styles_common import *

INV = Transformer.from_crs('+proj=laea +lat_0=52 +lon_0=24 +datum=WGS84 +units=m', 4326, always_xy=True)
D2R = np.pi / 180


def rings_ll(g, tol=None, inv=True):
    """polygon rings as lon/lat arrays."""
    out = []
    if g.is_empty: return out
    if tol: g = g.simplify(tol)
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon': continue
        for r in [p.exterior, *p.interiors]:
            xy = np.asarray(r.coords)
            if inv: lon, lat = INV.transform(xy[:, 0], xy[:, 1]); out.append(np.c_[lon, lat])
            else: out.append(xy[:, :2])
    return out


_ne = json.load(open(f'{ROOT}/data/ne/ne_10m_admin_0_countries.geojson'))
WORLD = unary_union([_shape(f['geometry']).simplify(0.08) for f in _ne['features']]).buffer(0)
WORLD_R = rings_ll(WORLD, None, inv=False)
R_ = {k: rings_ll(v, 4e3) for k, v in NEIGH.items() if k in ('prussia', 'russia', 'habsburg', 'ottoman', 'sweden')}
R_PRE = rings_ll(PRE72, 3e3); R_91 = rings_ll(PLT91, 3e3)
R_PC = [(yr, pw, rings_ll(g, 3e3), INV.transform(*o)) for yr, pw, g, o, rad in ORIG]
COL = dict(plt='#ff3b4e', prussia='#4f8cff', russia='#3fd28a', habsburg='#ffb43a', ottoman='#b78cff', sweden='#8fb8ff')

rng = np.random.default_rng(3)
STARS = np.c_[rng.uniform(0, W, 900), rng.uniform(0, H, 900), rng.uniform(0.2, 1.0, 900) ** 3]


def view(t):
    """centre lon/lat, globe radius px, screen centre y."""
    k1 = eexp(seg(t, 0.2, 2.3))
    lon = lerp(-5.0, 24.0, ease(seg(t, 0.0, 2.3))); lat = lerp(32.0, 51.6, ease(seg(t, 0.0, 2.3)))
    R = np.exp(lerp(np.log(430), np.log(4300), k1))
    k2 = ease(seg(t, 9.2, 10.5)); R = np.exp(lerp(np.log(R), np.log(2100), k2)); lat = lerp(lat, 44.0, k2)
    cy = lerp(980, 940, k1) + 520 * k2
    R *= 1 + 0.03 * seg(t, 2.3, 9.2)
    return lon + 0.25 * seg(t, 2.3, 9.2), lat, R, cy


def proj(ll_, lon0, lat0, R, cy):
    lon, lat = ll_[:, 0] * D2R, ll_[:, 1] * D2R; l0, p0 = lon0 * D2R, lat0 * D2R
    cosc = np.sin(p0) * np.sin(lat) + np.cos(p0) * np.cos(lat) * np.cos(lon - l0)
    x = np.cos(lat) * np.sin(lon - l0); y = np.cos(p0) * np.sin(lat) - np.sin(p0) * np.cos(lat) * np.cos(lon - l0)
    back = cosc < 0
    if back.any():   # fold the far side onto the limb
        n = np.hypot(x, y) + 1e-9; x = np.where(back, x / n, x); y = np.where(back, y / n, y)
    return np.c_[W / 2 + x * R, cy - y * R], (~back).any()


def ppath(rings, v):
    p = skia.Path(); p.setFillType(skia.PathFillType.kEvenOdd); any_ = False
    for r in rings:
        xy, vis = proj(r, *v)
        if not vis: continue
        if (xy[:, 0].max() < -200) or (xy[:, 0].min() > W + 200) or (xy[:, 1].max() < -200) or (xy[:, 1].min() > H + 200): continue
        any_ = True; p.addPoly([skia.Point(*q) for q in xy], True)
    return p if any_ else None


def glow_fill(c, p, col, a, blur=0):
    if p is None or a <= 0: return
    c.drawPath(p, fill(rgb(col, a)))


def hud(c, s, x, y, size, a, col='#cfe6ff', align='l', sp=3, f='SourceSans3-Regular.ttf'):
    if a > 0: text(c, s, x, y, font(f, size), rgb(col, a), align=align, spacing=sp)


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#02040a')))
    v = view(t); lon0, lat0, R, cy = v
    for x, y, b in STARS: c.drawCircle(x, y, 0.6 + 1.4 * b, fill(rgb('#dfe8ff', 0.25 + 0.7 * b)))
    # atmosphere
    c.drawCircle(W / 2, cy, R * 1.06, skia.Paint(Shader=rad_grad(W / 2, cy, R * 1.06, [rgb('#4aa0ff', 0.0), rgb('#4aa0ff', 0.0), rgb('#6cc0ff', 0.55), rgb('#4aa0ff', 0.0)], [0, 0.90, 0.945, 1.0]), AntiAlias=True))
    # ocean
    c.drawCircle(W / 2, cy, R, skia.Paint(Shader=rad_grad(W / 2 - R * 0.3, cy - R * 0.35, R * 1.5, [rgb('#1a4f86'), rgb('#0c2b52'), rgb('#040d1c')], [0, 0.55, 1]), AntiAlias=True))
    disc = skia.Path(); disc.addCircle(W / 2, cy, R)
    c.save(); c.clipPath(disc, doAntiAlias=True)
    land = ppath(WORLD_R, v)
    if land:
        c.drawPath(land, fill(rgb('#33402f'))); c.drawPath(land, stroke(rgb('#8fb0c8', 0.35), 1.2))
    # political layers
    za = seg(t, 1.6, 2.4)
    alt = t >= 7.4
    wx0, wy0 = proj(np.array([[24.0, 52.0]]), *v)[0][0]; fr = R * 0.16
    for nm, rings in R_.items():
        p = ppath(rings, v)
        if p:
            q = skia.Paint(Shader=rad_grad(wx0, wy0, fr, [rgb(COL[nm], 0.30 * za), rgb(COL[nm], 0.22 * za), rgb(COL[nm], 0.0)], [0, 0.6, 1]), AntiAlias=True)
            c.drawPath(p, q)
            q = skia.Paint(Shader=rad_grad(wx0, wy0, fr, [rgb(COL[nm], 0.65 * za), rgb(COL[nm], 0.5 * za), rgb(COL[nm], 0.0)], [0, 0.6, 1]), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6)
            c.drawPath(p, q)
    if not alt:
        p = ppath(R_PRE, v); ca = za * (1 - seg(t, 6.3, 6.9))
        if p:
            glow_fill(c, p, COL['plt'], 0.42 * ca)
            q = stroke(rgb(COL['plt'], 0.9 * ca), 7, glow=10); c.drawPath(p, q); c.drawPath(p, stroke(rgb('#ffd6dc', ca), 2.2))
        for i, (yr, pw, rings, o) in enumerate(R_PC):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            p = ppath(rings, v)
            if p is None: continue
            oxy, _ = proj(np.array([o]), *v)
            c.save(); c.clipPath(p, doAntiAlias=True)
            rr = R * 0.3 * eout(k, 2)
            c.drawCircle(*oxy[0], rr, fill(rgb('#05070c', 0.75)))
            c.drawCircle(*oxy[0], rr, fill(rgb(COL[pw], 0.55)))
            c.drawCircle(*oxy[0], rr, stroke(rgb('#ffffff', 0.9 * (1 - k)), 5, glow=6))
            c.restore()
            c.drawPath(p, stroke(rgb(COL[pw], 0.9), 2.0))
    else:
        k = ease(seg(t, 8.0, 9.0))
        for i, (yr, pw, rings, o) in enumerate(R_PC):
            a_ = 1.0 if yr == '1772' else 1 - k
            p = ppath(rings, v)
            if p and a_ > 0: glow_fill(c, p, COL[pw], 0.45 * a_); c.drawPath(p, stroke(rgb(COL[pw], 0.9 * a_), 2.0))
        p = ppath(R_91, v)
        if p:
            glow_fill(c, p, '#ffcf5a', 0.10 * k); glow_fill(c, p, COL['plt'], 0.40 * k)
            c.drawPath(p, stroke(rgb('#ffcf5a', 0.8 * k), 8, glow=14)); c.drawPath(p, stroke(rgb('#fff1c4', k), 2.4, dash=[14, 9]))
    # sunlight shading + night side
    c.drawCircle(W / 2, cy, R, skia.Paint(Shader=rad_grad(W / 2 - R * 0.45, cy - R * 0.5, R * 2.1, [rgb('#ffffff', 0.10), rgb('#000000', 0.0), rgb('#000000', 0.55)], [0, 0.45, 1]), AntiAlias=True))
    c.restore()
    # HUD
    hz = seg(t, 2.2, 2.7)
    wx, wy = proj(np.array([[21.012, 52.23]]), *v)[0][0]
    if hz > 0 and t < 9.6:
        a = hz * (1 - seg(t, 9.2, 9.6)); c.drawCircle(wx, wy, 10, stroke(rgb('#cfe6ff', a), 2)); c.drawCircle(wx, wy, 3, fill(rgb('#ffffff', a)))
        c.drawLine(wx + 10, wy - 10, wx + 90, wy - 90, stroke(rgb('#cfe6ff', 0.8 * a), 1.5)); c.drawLine(wx + 90, wy - 90, wx + 260, wy - 90, stroke(rgb('#cfe6ff', 0.8 * a), 1.5))
        hud(c, 'WARSAW', wx + 100, wy - 102, 30, a, '#ffffff', sp=5, f='SourceSans3-SemiBold.ttf')
        hud(c, '52.23° N  21.01° E', wx + 100, wy - 62, 22, a * 0.8, sp=2)
    # top HUD bar
    ha = seg(t, 0.2, 0.8)
    c.drawLine(70, 250, W - 70, 250, stroke(rgb('#cfe6ff', 0.25 * ha), 1))
    hud(c, f'LAT {lat0:05.2f}°   LON {lon0:05.2f}°   ALT {int(42000 / (R / 430)):,} KM'.replace(',', ' '), 70, 236, 22, 0.75 * ha, sp=3)
    yr = year_at(t)
    hud(c, yr or '', W - 70, 236, 26, ha * (yr is not None), '#ffffff', 'r', 4, 'SourceSans3-SemiBold.ttf')
    # status chip
    hyp = t >= 7.9; a = seg(t, 2.0, 2.4) * (1 - seg(t, 7.3, 7.7)) if not hyp else seg(t, 7.9, 8.3)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 28); w = text_width(s, fn, 5) + 46
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, 140, w, 52), 6, 6)
        c.drawRRect(rr, fill(rgb('#02040a', 0.6 * a))); c.drawRRect(rr, stroke(rgb('#ffcf5a' if hyp else '#cfe6ff', a), 1.6, dash=[8, 5] if hyp else None))
        text(c, s, 70 + w / 2, 175, fn, rgb('#ffcf5a' if hyp else '#cfe6ff', a), spacing=5)
    # titles
    sh = rgb('#000000', 0.9)
    if t < 2.4:
        a = seg(t, 0.1, 0.5) * (1 - seg(t, 1.9, 2.4))
        text(c, 'WHAT IF', W / 2, 1600, font('SourceSans3-SemiBold.ttf', 128), rgb('#ffffff', a), spacing=26, reveal=seg(t, 0.2, 0.9), shadow=sh)
        text(c, 'POLAND–LITHUANIA HAD NEVER', W / 2, 1680, font('SourceSans3-Regular.ttf', 44), rgb('#cfe6ff', a), spacing=6, reveal=seg(t, 0.5, 1.2), shadow=sh)
        text(c, 'BEEN PARTITIONED?', W / 2, 1740, font('SourceSans3-Regular.ttf', 44), rgb('#cfe6ff', a), spacing=6, reveal=seg(t, 0.7, 1.4), shadow=sh)
    if yr and 2.0 < t < 7.0:
        a = seg(t, 2.1, 2.5) * (1 - seg(t, 6.6, 7.0))
        text(c, yr, W / 2, 1640, font('SourceSans3-SemiBold.ttf', 150), rgb('#ffffff', a), spacing=14, shadow=sh)
        text(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1712, font('SourceSans3-Regular.ttf', 34), rgb('#cfe6ff', a), spacing=10, shadow=sh)
    if 6.9 < t < 8.4:
        a = seg(t, 7.0, 7.3) * (1 - seg(t, 8.1, 8.4))
        text(c, 'BUT WHAT IF THE REFORMS', W / 2, 1620, font('SourceSans3-Regular.ttf', 52), rgb('#ffffff', a), spacing=6, reveal=seg(t, 7.0, 7.6), shadow=sh)
        text(c, 'OF 1791 HAD SURVIVED?', W / 2, 1690, font('SourceSans3-SemiBold.ttf', 52), rgb('#ffcf5a', a), spacing=6, reveal=seg(t, 7.2, 7.8), shadow=sh)
    if t > 8.9:
        a = seg(t, 8.9, 9.4)
        text(c, 'STILL ON THE MAP', W / 2, 420, font('SourceSans3-SemiBold.ttf', 84), rgb('#ffffff', a), spacing=12, reveal=seg(t, 8.9, 9.6), shadow=sh)
        text(c, 'THE COMMONWEALTH · 1791 BORDERS', W / 2, 480, font('SourceSans3-Regular.ttf', 30), rgb('#ffcf5a', a), spacing=6, shadow=sh)


POST = Post(grain=0.02, vignette=0.45, bloom=0.55, halation=0.15, ca=0.0016, shoulder=0.12, seed=91)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [0.4, 1.4, 2.8, 4.2, 6.0, 7.5, 8.8, 10.3], POST, f'{ROOT}/render/c9t'); sheet(fs, f'{ROOT}/render/c9_sheet.jpg', 4, 300)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept9_orbit.mp4', POST, stills=(0.4, 1.4, 2.8, 4.2, 6.0, 10.3),
               still_dir=f'{ROOT}/previews/concepts', mb=8, workers=2, scene_mod='concept9_orbit')
