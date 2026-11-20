"""CONCEPT 1 (v2) - Cinematic Historical Atlas ("Night Atlas").

Dark relief map from real elevation data (340 m/px, multi-scale shading), engraved bathymetry lines, glowing rivers,
territories as luminous glass plates. The camera descends through cloud, then tilts and settles; partitions are shown
as plates that physically lift out of the map, drift towards the annexing power, change colour and drop back.
Real motion blur (6 sub-frames, 180-degree shutter), tilt-shift depth of field, halation and film grain."""
import sys, os, numpy as np, skia, cv2
from core import *

# ---------------------------------------------------------------- relief raster (pre-coloured once)
_RGB = f'{ROOT}/data/relief_hi_rgb.npy'
X0, Y0, X1, Y1, RES = -1500e3, -1650e3, 1700e3, 1350e3, 340.0


def _build_relief():
    """colour the relief once (float work), cache as uint8 RGBA .npy (memory-mapped by every render worker)."""
    D = np.load(f'{ROOT}/data/relief_hi.npz')
    assert tuple(D['extent']) == (X0, Y0, X1, Y1, RES)
    out = np.lib.format.open_memmap(_RGB + '.tmp', mode='w+', dtype=np.uint8, shape=D['land'].shape + (4,))
    for r0 in range(0, out.shape[0], 1024):   # in strips to bound memory
        sl = slice(r0, r0 + 1024)
        sh = D['shade'][sl].astype(np.float32) / 255; land = D['land'][sl].astype(np.float32) / 255
        hgt = D['height'][sl].astype(np.float32) / 255; sd = D['seadist'][sl].astype(np.float32)
        lowc = np.array([0.095, 0.105, 0.115], np.float32); highc = np.array([0.23, 0.205, 0.175], np.float32)
        base = lowc + (highc - lowc) * np.sqrt(hgt)[..., None]
        lit = base * (0.42 + 1.30 * sh[..., None]) + np.array([0.03, 0.022, 0.012], np.float32) * np.clip(sh - 0.6, 0, 1)[..., None] * 3
        deep = np.array([0.018, 0.035, 0.058], np.float32); shallow = np.array([0.05, 0.10, 0.135], np.float32)
        dk = np.exp(-sd / 38.0)[..., None]
        ripple = (np.cos(sd * 2 * np.pi / 7.5) * 0.5 + 0.5) ** 10 * np.exp(-sd / 30.0) * (sd > 0.6)
        seacol = deep + (shallow - deep) * dk + ripple[..., None] * np.array([0.05, 0.09, 0.11], np.float32)
        img = lit * land[..., None] + seacol * (1 - land[..., None])
        out[sl, :, :3] = (np.clip(img, 0, 1) * 255).astype(np.uint8); out[sl, :, 3] = 255
    out.flush(); del out; os.replace(_RGB + '.tmp', _RGB)


_RELIEF = None


def relief():
    global _RELIEF
    if _RELIEF is None:
        if not os.path.exists(_RGB): _build_relief()
        _RELIEF = skia.Image.fromarray(np.load(_RGB, mmap_mode='r'), colorType=skia.kRGBA_8888_ColorType)
    return _RELIEF

# ---------------------------------------------------------------- clouds (procedural, world-space RGBA)
def _clouds(n=1536, seed=4):
    rng = np.random.default_rng(seed); acc = np.zeros((n, n), np.float32); amp = 1.0
    for o in range(7):
        s = 4 * 2 ** o
        acc += cv2.resize(rng.normal(0, 1, (s, s)).astype(np.float32), (n, n), interpolation=cv2.INTER_CUBIC) * amp; amp *= 0.55
    acc = (acc - acc.mean()) / acc.std()
    a = np.clip((acc + 0.35) * 0.75, 0, 1) ** 1.1
    shade = np.clip(0.75 + (acc - np.roll(np.roll(acc, 9, 0), 9, 1)) * 0.35, 0.45, 1.1)
    rgb_ = np.stack([shade * 0.86, shade * 0.89, shade * 0.95], -1)
    out = np.dstack([np.clip(rgb_ * a[..., None], 0, 1), a])          # premultiplied
    return skia.Image.fromarray((out * 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
CLOUD = _clouds()

S73, S91 = L['stages']['1773'], L['stages']['1791']
PLT91 = S91['plt'].buffer(800).buffer(-800)
# display-only: OHM's Russia is clipped at the 42E working window; the empire continued far to the east
from shapely.geometry import box as _box
from shapely.ops import transform as _tr
_ext = _tr(lambda x, y, z=None: FWD.transform(x, y), _box(37.0, 48.0, 62.0, 67.0).segmentize(0.25))
RUSSIA_DISP = S73['russia'].union(_ext.difference(S73['sweden'].buffer(2e3)).difference(S73['ottoman'].buffer(2e3))).buffer(0)
PAL = dict(plt='#b42d3c', prussia='#4f7fb0', russia='#6f9150', habsburg='#c08440', ottoman='#7a6250', other='#4a4a4a', gold='#f0cd86', alt='#c98a2c')
GOLD = rgb(PAL['gold']); IVORY = rgb('#f3ead8')
RIVERS = [r for r in L['rivers'] if r['rank'] is not None and r['rank'] <= 6]

# ---------------------------------------------------------------- camera
CAM_HIGH = Cam(*ll(24.8, 51.9), zoom=0.56, rot=-10, tilt=0.58, oy=300)
CAM_WIDE = Cam(*ll(24.6, 52.6), zoom=0.60, rot=-2, tilt=0.30, oy=60)
CAM_PART = Cam(*ll(24.4, 52.4), zoom=0.67, rot=0, tilt=0.22, oy=40)
CAM_END = Cam(*ll(24.0, 52.6), zoom=0.74, rot=1.5, tilt=0.40, oy=90)


def camera(t):
    if t < 4.0: c = Cam.blend(CAM_HIGH, CAM_WIDE, ease(seg(t, 0, 4.0)) * 0.6 + eexp(seg(t, 0, 4.0)) * 0.4)
    elif t < 8.8: c = Cam.blend(CAM_WIDE, CAM_PART, ease(seg(t, 4.0, 8.8)))
    else: c = Cam.blend(CAM_PART, CAM_END, ease(seg(t, 8.8, 12.0)))
    # subtle 'operated' camera: low-frequency drift, never jitter
    c.cx += 2600 * np.sin(t * 0.71 + 1.3) + 1400 * np.sin(t * 1.37); c.cy += 2200 * np.sin(t * 0.53 + 0.4)
    c.rot += 0.18 * np.sin(t * 0.61 + 2.0)
    return c


# ---------------------------------------------------------------- drawing helpers
def colA(col, a):
    return skia.Color4f(col.fR, col.fG, col.fB, col.fA * a)


def glass(c, p, col, a, edge_a=0.0, edge_col=None, edge_w=1.4):
    """luminous tinted glass: screen + multiply passes so the relief reads through."""
    if a <= 0: return
    f = fill(rgb(col, a)); f.setBlendMode(skia.BlendMode.kScreen); c.drawPath(p, f)
    f2 = fill(rgb(col, a * 0.55)); f2.setBlendMode(skia.BlendMode.kMultiply); c.drawPath(p, f2)
    if edge_a > 0: c.drawPath(p, stroke(rgb(edge_col or col, edge_a), edge_w))


def trace(c, p, k, w=3.0):
    if k <= 0: return
    eff = skia.TrimPathEffect.Make(0, k) if k < 1 else None
    for wid, col, gl in ((w * 6, rgb('#ffb85a', 0.35), 14), (w * 2.2, rgb('#ffd890', 0.6), 4), (w, GOLD, 0)):
        sp = stroke(col, wid, glow=gl)
        if eff: sp.setPathEffect(eff)
        c.drawPath(p, sp)
    if 0 < k < 1:   # the travelling light at the pen tip
        meas = skia.PathMeasure(p, False)
        # find tip on the longest contour
        best = None
        while True:
            L_ = meas.getLength()
            if best is None or L_ > best[0]: best = (L_, meas.getPosTan(L_ * k)[0])
            if not meas.nextContour(): break
        x, y = best[1].x(), best[1].y()
        g = skia.Paint(AntiAlias=True); g.setShader(rad_grad(x, y, 70, [rgb('#fff4d6', 0.95), rgb('#ffbf5e', 0.35), rgb('#ff9a3c', 0)], [0, .25, 1]))
        g.setBlendMode(skia.BlendMode.kScreen); c.drawCircle(x, y, 70, g)


def piece_matrix(M, g, dirv, h):
    """matrix lifting a territory plate: drift towards annexer + slight scale-up about its centroid."""
    cx, cy = g.centroid.x, g.centroid.y
    mm = skia.Matrix(); mm.setTranslate(cx + dirv[0] * 55e3 * h, cy + dirv[1] * 55e3 * h)
    mm.preScale(1 + 0.035 * h, 1 + 0.035 * h); mm.preTranslate(-cx, -cy)
    return skia.Matrix.Concat(M, mm)


def label(c, cam, lon, lat, s, f, col, a=1.0, spacing=6, reveal=1.0, dy=0):
    if a <= 0: return
    x, y = cam.pt(*ll(lon, lat))
    text(c, s, x, y + dy, f, colA(col, a), spacing=spacing, reveal=reveal, shadow=rgb('#000000', 0.85 * a))


def city(c, cam, name, a, t, side='r', t0=0):
    if a <= 0: return
    x, y = cam.pt(*CITIES[name])
    ring = (t - t0) % 2.4 / 2.4
    c.drawCircle(x, y, 6 + 26 * ring, stroke(rgb('#ffe2a8', 0.5 * a * (1 - ring)), 1.6))
    c.drawCircle(x, y, 10, stroke(rgb('#ffd590', 0.45 * a), 7, glow=7))
    c.drawCircle(x, y, 4.2, fill(rgb('#fff6e2', a)))
    text(c, name, x + (17 if side == 'r' else -17), y + 10, font('CG-SemiBold.ttf', 32), rgb('#f7eedc', a),
         align='l' if side == 'r' else 'r', spacing=1, shadow=rgb('#000000', 0.95 * a))


def gold_text(c, s, x, y, f, a, reveal, spacing, sweep):
    """metallic gold type: vertical gradient fill, warm glow, travelling specular highlight."""
    if a <= 0: return
    w = text_width(s, f, spacing); top = y - f.getSize() * 0.75
    text(c, s, x, y, f, rgb('#ffb347', 0.0), spacing=spacing, reveal=reveal, glow=rgb('#ff9f3a', 0.55 * a), shadow=rgb('#000000', 0.9 * a))
    c.saveLayer()
    text(c, s, x, y, f, rgb('#ffffff', a), spacing=spacing, reveal=reveal)
    p = skia.Paint(); p.setBlendMode(skia.BlendMode.kSrcIn)
    p.setShader(lin_grad((0, top), (0, y + 6), [rgb('#fff1c9'), rgb('#f2c46e'), rgb('#a8722a'), rgb('#f5d088'), rgb('#8a5a1e')], [0, .35, .55, .75, 1]))
    c.drawRect(skia.Rect(x - w, top - 20, x + w, y + 30), p)
    sx = lerp(x - w * 0.9, x + w * 0.9, sweep)
    q = skia.Paint(); q.setBlendMode(skia.BlendMode.kSrcATop)
    q.setShader(lin_grad((sx - 90, top), (sx + 90, y), [rgb('#ffffff', 0), rgb('#ffffff', 0.85), rgb('#ffffff', 0)], [0, .5, 1]))
    c.drawRect(skia.Rect(x - w, top - 20, x + w, y + 30), q)
    c.restore()


def chip(c, y, s, kind, a):
    if a <= 0: return
    f = font('SourceSans3-SemiBold.ttf', 25)
    w = text_width(s, f, 4) + 56
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W / 2 - w / 2, y - 34, w, 50), 25, 25)
    if kind == 'doc':
        c.drawRRect(r, fill(rgb('#0c1218', 0.72 * a))); c.drawRRect(r, stroke(rgb('#dfe6ea', 0.7 * a), 1.6))
        text(c, s, W / 2, y, f, rgb('#e8eef2', a), spacing=4)
    else:
        c.drawRRect(r, fill(rgb('#2a1d08', 0.8 * a))); c.drawRRect(r, stroke(rgb(PAL['gold'], a), 2, dash=[10, 7]))
        text(c, s, W / 2, y, f, rgb('#ffd98f', a), spacing=4)


YEARS = [(4.3, '1772', 'FIRST PARTITION'), (6.2, '1793', 'SECOND PARTITION'), (7.6, '1795', 'THIRD PARTITION'),
         (9.3, '1791', 'IF THE REFORMS HAD HELD')]


def year_counter(c, t):
    cur = None
    for i, (ts, *_r) in enumerate(YEARS):
        if t >= ts: cur = i
    if cur is None: return
    a = seg(t, 4.1, 4.6) * (1 - seg(t, 10.9, 11.4))
    ts, yv, sub = YEARS[cur]
    k = eout(seg(t, ts, ts + 0.5), 4)
    prev = YEARS[cur - 1][1] if cur > 0 else None
    hyp = yv == '1791'
    f = font('Cinzel-Bold.ttf', 140); y = 1330
    c.save(); c.clipRect(skia.Rect(0, y - 140, W, y + 34))
    if prev and k < 1:
        text(c, prev, W / 2, y - 150 * k, f, colA(IVORY, a * (1 - k)), spacing=14)
    if hyp: gold_text(c, yv, W / 2, y + 150 * (1 - k), f, a, 1.0, 14, seg(t, ts + 0.3, ts + 1.6))
    else: text(c, yv, W / 2, y + 150 * (1 - k), f, colA(IVORY, a), spacing=14)
    c.restore()
    rule = 150 * eout(seg(t, ts + 0.1, ts + 0.7))
    rc = rgb('#ffd98f' if hyp else '#c9d3da', 0.7 * a)
    c.drawLine(W / 2 - 230 - rule, y + 52, W / 2 - 230, y + 52, stroke(rc, 1.4)); c.drawLine(W / 2 + 230, y + 52, W / 2 + 230 + rule, y + 52, stroke(rc, 1.4))
    text(c, sub, W / 2, y + 62, font('SourceSans3-SemiBold.ttf', 31), rgb('#ffd98f' if hyp else '#d3dce2', a * k), spacing=9, reveal=k)
    chip(c, y + 140, 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY', 'hyp' if hyp else 'doc', a * k)


W_, E_, S_, N_ = (-0.97, 0.25), (0.98, 0.18), (0.1, -0.99), (0.4, 0.9)
LOSSES = [(L['loss72']['pru'], 'prussia', W_, 4.4, 5.9), (L['loss72']['rus'], 'russia', E_, 4.6, 6.1), (L['loss72']['aut'], 'habsburg', S_, 4.8, 6.2),
          (L['gains']['93_pru'], 'prussia', W_, 6.25, 7.6), (L['gains']['93_rus'], 'russia', E_, 6.35, 7.7),
          (L['gains']['95_pru'], 'prussia', W_, 7.65, 8.9), (L['gains']['95_rus'], 'russia', E_, 7.75, 9.0),
          (L['gains']['95_rus_courland'], 'russia', N_, 7.75, 9.0), (L['gains']['95_aut'], 'habsburg', S_, 7.85, 9.0)]


def scene(c, t, f):
    cam = camera(t); M = cam.matrix()
    POST_STATE['dof'] = cam.tilt * 1.3
    c.clear(skia.Color4f(0.02, 0.035, 0.055, 1))
    c.saveLayer()   # map world layer, faded out by a focus falloff around the Commonwealth
    c.save(); c.concat(M); c.drawRect(skia.Rect(-6e6, -6e6, 6e6, 6e6), fill(skia.Color4f(0.018, 0.035, 0.058, 1)))
    c.translate(X0, Y1); c.scale(RES, -RES); c.drawImage(relief(), 0, 0, SAMP); c.restore()
    # rivers: thin cold light, flowing in
    ra = 0.55 * seg(t, 2.0, 3.4)
    if ra > 0:
        for r in RIVERS:
            p = tpath(path(r['geom']), M)
            c.drawPath(p, stroke(rgb('#5fb3d9', ra * 0.35), 4, glow=4)); c.drawPath(p, stroke(rgb('#9bd6ef', ra), 1.1))
    alt = seg(t, 9.0, 10.0)
    neigh = (0.30 + 0.10 * seg(t, 3.0, 4.0)) * (1 - 0.45 * alt)
    for k in ('hre', 'saxony', 'sweden', 'denmark', 'other', 'venice', 'ragusa'):
        g = S73.get(k)
        if g is not None and not g.is_empty: glass(c, tpath(path(g), M), PAL['other'], 0.10, 0.25, '#8d98a0', 0.8)
    for k, ec in (('ottoman', '#9a8b7e'), ('russia', '#a9bf8f'), ('prussia', '#9ab8d8')):
        glass(c, tpath(path(RUSSIA_DISP if k == 'russia' else S73[k]), M), PAL[k], neigh, 0.5, ec, 1)
    glass(c, tpath(path(S91['habsburg']), M), PAL['habsburg'], neigh, 0.5, '#d6b48a', 1)
    fx, fy = cam.pt(*ll(25.0, 52.6)); rr = 900 * cam.zoom / 0.6
    fm = skia.Paint(); fm.setBlendMode(skia.BlendMode.kDstIn)
    fm.setShader(rad_grad(fx, fy, rr, [rgb('#000000', 1), rgb('#000000', 0.92), rgb('#000000', 0)], [0, .55, 1])); c.drawPaint(fm)
    c.restore()
    # ---- the Commonwealth, with lifted plates cut out of it
    ca = 0.66 * seg(t, 1.2, 2.8) * (1 - alt)
    active = [(g, pw, d, seg(t, a, b)) for g, pw, d, a, b in LOSSES if seg(t, a, b) > 0]
    c.save()
    for g, pw, d, k in active:
        c.clipPath(tpath(path(g), M), skia.ClipOp.kDifference, True)
    glass(c, tpath(path(L['plt_pre72']), M), PAL['plt'], ca)
    glass(c, tpath(path(L['courland']), M), '#c96a52', ca * 0.6)
    c.restore()
    # ---- partitions: plates lift, drift towards the annexing power, change colour, settle
    pk = 1 - alt
    for g, pw, d, k in active:
        h = np.sin(np.pi * clamp(k / 0.85)) if k < 0.85 else 0.0
        pc, tc = rgb(PAL['plt']), rgb(PAL[pw])
        col = lerpc((pc.fR, pc.fG, pc.fB), (tc.fR, tc.fG, tc.fB), ease(seg(k, 0.25, 0.8)))
        hexcol = '#%02x%02x%02x' % tuple(int(v * 255) for v in col)
        base_p = tpath(path(g), M)
        if h > 0.01:   # the hole: shadowed void where the plate was
            c.drawPath(base_p, fill(rgb('#000000', 0.45 * h * pk)))
            Mp = piece_matrix(M, g, d, h)
            pp = tpath(path(g), Mp)
            sh_ = skia.Paint(Color4f=rgb('#000000', 0.65 * h * pk), AntiAlias=True)
            sh_.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 + 16 * h))
            c.save(); c.translate(10 * h, 22 * h); c.drawPath(pp, sh_); c.restore()
            c.drawPath(pp, fill(rgb('#0b0f14', 0.55 * pk)))
            glass(c, pp, hexcol, 0.88 * pk, 0.0)
            c.drawPath(pp, stroke(rgb('#fff0cf', 0.85 * h * pk), 2.0))
            c.drawPath(pp, stroke(rgb('#ffcf7a', 0.45 * h * pk), 10, glow=10))
        else:
            glass(c, base_p, hexcol, 0.80 * pk, 0.9 * pk, hexcol, 1.4)
    # ---- borders: light-traced 1772 outline, then current outline, then dashed ghost
    trace(c, tpath(outline(L['plt_pre72']), M), eout(seg(t, 0.6, 3.0), 2) * (1 - seg(t, 4.1, 4.7)), w=3.0)
    if 4.1 < t < 9.3:
        cur = L['plt1773'] if t < 6.25 else L['rump1793'] if t < 7.65 else None
        if cur is not None: c.drawPath(tpath(outline(cur), M), stroke(rgb('#ffe6b0', 0.85 * (1 - alt)), 2.2))
    gone = seg(t, 8.6, 9.1)
    if gone > 0 and alt < 1:
        c.drawPath(tpath(outline(L['plt_pre72']), M), stroke(rgb('#e9d7b0', 0.55 * gone * (1 - alt)), 1.8, dash=[8, 9]))
    # ---- hypothetical survival: 1791 state re-ignites from Warsaw
    if alt > 0:
        from shapely.geometry import Point
        k = seg(t, 9.0, 10.3)
        g = PLT91 if k >= 1 else Point(CITIES['Warsaw']).buffer(1_300_000 * eout(k, 2), 96).intersection(PLT91)
        gp = path_nocache(g); gp = skia.Path(gp); gp.transform(M)
        glass(c, gp, PAL['alt'], 0.58)
        c.save(); c.clipPath(gp, doAntiAlias=True)
        sp_ = skia.Paint(); sp_.setBlendMode(skia.BlendMode.kScreen); wx, wy = cam.pt(*CITIES['Warsaw'])
        sp_.setShader(rad_grad(wx, wy, 700, [rgb('#ffd27a', 0.30 * alt), rgb('#ffb347', 0.08 * alt), rgb('#ff9a3c', 0)], [0, .5, 1])); c.drawPaint(sp_); c.restore()
        c.drawPath(gp, stroke(rgb('#ffcf7a', 0.35 * alt), 18, glow=16))
        p = tpath(outline(PLT91), M)
        c.drawPath(p, stroke(rgb('#ffe6b0', alt), 2.6, dash=[14, 8]))
        if k < 1:
            from shapely.geometry import Point as P_
            fr = path_nocache(P_(CITIES['Warsaw']).buffer(1_300_000 * eout(k, 2), 96).boundary.intersection(PLT91.buffer(20e3)))
            fr = skia.Path(fr); fr.transform(M)
            c.drawPath(fr, stroke(rgb('#fff3d0', 0.9 * (1 - k)), 3)); c.drawPath(fr, stroke(rgb('#ffbf5e', 0.7 * (1 - k)), 16, glow=14))
    # ---- map labels
    la = seg(t, 2.9, 3.8) * (1 - 0.6 * alt)
    sc = font('CormorantSC-SemiBold.ttf', 34)
    label(c, cam, 16.6, 53.0, 'PRUSSIA', sc, rgb('#cfe0f2'), la, 8)
    label(c, cam, 32.6, 56.6, 'RUSSIAN EMPIRE', sc, rgb('#d8e8c6'), la, 6)
    label(c, cam, 19.5, 48.0, 'HABSBURG MONARCHY', sc, rgb('#f0d7b4'), la * (1 - seg(t, 3.9, 4.3)), 5)
    label(c, cam, 29.0, 46.4, 'OTTOMAN EMPIRE', sc, rgb('#e2d2c4'), la * 0.8 * (1 - seg(t, 3.9, 4.3)), 5)
    label(c, cam, 18.3, 56.4, 'Baltic Sea', font('CG-MediumItalic.ttf', 40), rgb('#86b0c9'), la, 4)
    pla = seg(t, 3.1, 4.0) * (1 - seg(t, 6.0, 6.4))
    big = font('Cinzel-Bold.ttf', 31)
    label(c, cam, 27.4, 51.3, 'POLISH–LITHUANIAN', big, rgb('#fff1dc'), pla, 7, reveal=seg(t, 3.1, 4.1))
    label(c, cam, 27.4, 51.3, 'COMMONWEALTH', big, rgb('#fff1dc'), pla, 9, reveal=seg(t, 3.25, 4.2), dy=38)
    for nm, side, a0 in [('Warsaw', 'r', 1.9), ('Vilnius', 'r', 3.0), ('Kraków', 'l', 3.2), ('Gdańsk', 'l', 3.3)]:
        city(c, cam, nm, seg(t, a0, a0 + 0.6), t, side, a0)
    # ---- clouds: the camera descends through them during the hook
    ck = seg(t, 0.0, 2.9)
    if ck < 1:
        for layer, (sc_, sp_, alpha) in enumerate(((1.0, 1.0, 0.95), (1.7, 1.6, 0.85))):
            grow = 1 + (sp_ * 2.6) * eout(ck, 2)
            ca_ = alpha * (1 - eout(ck, 1.6))
            c.save(); c.translate(W / 2, H * 0.55); c.scale(grow * sc_, grow * sc_)
            c.rotate(-8 + 4 * ck + layer * 25); c.translate(-W * 1.2 + 140 * t, -H * 0.9)
            p = skia.Paint(); p.setAlphaf(ca_)
            c.drawImageRect(CLOUD, skia.Rect(0, 0, W * 2.4, H * 1.8), SAMP, p); c.restore()
    # atmosphere: horizon haze (top) and floor shade (bottom)
    hz = skia.Paint(); hz.setShader(lin_grad((0, 0), (0, 640), [rgb('#0a1219', 1.0), rgb('#0b1620', 0.6), rgb('#0b1620', 0.0)], [0, .45, 1]))
    c.drawRect(skia.Rect(0, 0, W, 640), hz)
    bb = skia.Paint(); bb.setShader(lin_grad((0, 1060), (0, 1620), [rgb('#05090d', 0.0), rgb('#05090d', 0.9 * seg(t, 3.5, 4.3))]))
    c.drawRect(skia.Rect(0, 1060, W, H), bb)
    # ---- hook titles
    ha = seg(t, 0.35, 0.9) * (1 - seg(t, 3.2, 3.8))
    if ha > 0:
        yb = 360 - 70 * eout(seg(t, 3.2, 3.8))
        gold_text(c, 'WHAT IF', W / 2, yb, font('Cinzel-Bold.ttf', 136), ha, seg(t, 0.3, 1.2), 18, seg(t, 1.0, 2.6))
        text(c, 'POLAND–LITHUANIA', W / 2, yb + 110, font('Cinzel-Bold.ttf', 76), rgb('#fff6e6', ha), spacing=6,
             reveal=seg(t, 0.8, 1.8), shadow=rgb('#000000', 0.9))
        text(c, 'had never been partitioned?', W / 2, yb + 184, font('CG-MediumItalic.ttf', 62), rgb('#eadfc8', ha), spacing=1,
             reveal=seg(t, 1.3, 2.3), shadow=rgb('#000000', 0.9))
    year_counter(c, t)
    ea = seg(t, 10.1, 10.7)
    if ea > 0:
        gold_text(c, 'WHAT IF IT HAD SURVIVED?', W / 2, 420, font('Cinzel-Bold.ttf', 62), ea, seg(t, 10.1, 11.0), 5, seg(t, 10.6, 11.5))
        text(c, 'Commonwealth borders of 1791, kept intact', W / 2, 484, font('CG-MediumItalic.ttf', 40), rgb('#eadfc8', ea),
             reveal=seg(t, 10.4, 11.3), shadow=rgb('#000000', 0.9))
    if t < 0.45: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.45)))


POST = Post(grain=0.028, vignette=0.55, bloom=0.5, halation=0.35, ca=0.0016, shoulder=0.15, seed=11)

if __name__ == '__main__':
    out = f'{ROOT}/previews/concepts/concept1_cinematic_atlas.mp4'
    render(scene, 11.6, out, POST, stills=(1.4, 3.9, 5.2, 6.9, 8.3, 9.7, 11.2), still_dir=f'{ROOT}/previews/concepts',
           mb=6, workers=4, scene_mod='concept1_atlas')
