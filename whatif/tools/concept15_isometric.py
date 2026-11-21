"""CONCEPT 15 - Isometric Diorama.
A clean modern 3D explainer: the map tilts from flat into an isometric diorama where every state is an extruded slab
with soft contact shadows and pastel materials. Annexed sections physically lift out of the Commonwealth, glide to
the annexing power and drop into its slab (taking its colour); in 1795 the last block sinks away. In the alternate
timeline the 1791 Commonwealth rises back up as a single slab topped with a dashed gold 'hypothetical' outline."""
from styles_common import *

BOUNDS = (ll(14.0, 52)[0], ll(24, 45.8)[1], ll(34.6, 52)[0], ll(24, 59.0)[1])
FIT = fit_matrix(BOUNDS, 40, 380, 1000, 1000, pad=0.08)
COL = dict(land='#e9e6df', plt='#e4505c', prussia='#5b8fd6', russia='#6cbf8a', habsburg='#f1b84f', ottoman='#b9a2cf', sweden='#a9c1dc', sea='#cfe3ee')
HGT = dict(land=6, prussia=16, russia=16, habsburg=16, ottoman=12, sweden=12, plt=34)


def shade(hexc, k):
    c = rgb(hexc); return skia.Color4f(c.fR * k, c.fG * k, c.fB * k, 1)


def iso(t):
    """camera: flat top-down -> isometric, with a slow orbit."""
    k = ease(seg(t, 0.6, 2.4))
    squash = lerp(1.0, 0.56, k); rot = lerp(0, -34, k) + 4 * seg(t, 2.4, DUR)
    m = skia.Matrix(); m.setTranslate(W / 2, 930); m.preScale(1.0 + 0.10 * k, squash * (1.0 + 0.10 * k)); m.preRotate(rot); m.preTranslate(-W / 2, -880)
    return skia.Matrix.Concat(m, FIT), k


def slab(c, p, col, h, lift=0.0, alpha=1.0, steps=None):
    """extruded block: contact shadow, side wall (stacked), lit top face."""
    if h <= 0.2 and lift <= 0: return
    sh = fill(rgb('#1a2230', (0.18 + 0.10 * min(lift / 60, 1)) * alpha)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 + lift * 0.35))
    q = skia.Path(p); q.offset(4 + lift * 0.4, 6 + lift * 0.2); c.drawPath(q, sh)
    n = steps or max(2, int(h / 2))
    for i in range(n, 0, -1):
        dy = -(lift + h * (i - 1) / n); q = skia.Path(p); q.offset(0, dy)
        k = 0.62 + 0.18 * (1 - i / n)
        c.drawPath(q, fill(skia.Color4f(*[getattr(shade(col, k), a) for a in ('fR', 'fG', 'fB')], alpha)))
    top = skia.Path(p); top.offset(0, -(lift + h))
    c.drawPath(top, fill(skia.Color4f(*[getattr(rgb(col), a) for a in ('fR', 'fG', 'fB')], alpha)))
    c.drawPath(top, stroke(rgb('#ffffff', 0.55 * alpha), 1.4))
    return top


def leader(c, x, y, s, a, col='#1d2433', up=120, side=1):
    if a <= 0: return
    c.drawCircle(x, y, 5, fill(rgb(col, a)))
    c.drawLine(x, y, x, y - up * a, stroke(rgb(col, 0.8 * a), 1.8))
    fn = font('SourceSans3-SemiBold.ttf', 30); w = text_width(s, fn, 3) + 30
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - up - 50, w, 46), 23, 23)
    sh = fill(rgb('#1a2230', 0.15 * a)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)); c.drawRRect(r, sh)
    c.drawRRect(r, fill(rgb('#ffffff', 0.96 * a))); text(c, s, x, y - up - 18, fn, rgb(col, a), spacing=3)


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=lin_grad((0, 0), (0, H), [rgb('#f4f6f8'), rgb('#dde6ee')])))
    M, k3 = iso(t)
    hk = k3   # extrusion grows as the camera tilts
    # sea plate
    sea = skia.Path(); sea.addRect(skia.Rect.MakeLTRB(BOUNDS[0] - 4e5, BOUNDS[1] - 4e5, BOUNDS[2] + 4e5, BOUNDS[3] + 4e5)); sea = tpath(sea, M)
    bh = 26 * hk; base = skia.Path(sea); base.offset(0, bh)
    slab(c, base, '#a9c6d8', bh, steps=8)
    c.save(); c.clipPath(sea, doAntiAlias=True)
    slab(c, tpath(path(L['land']), M), COL['land'], HGT['land'] * hk, steps=3)
    for nm in ('sweden', 'ottoman', 'habsburg', 'russia', 'prussia'):
        slab(c, tpath(path(NEIGH[nm]), M), COL[nm], HGT[nm] * hk, steps=6)
    alt = t >= 7.4
    tops = {}
    if not alt:
        sink = ease(seg(t, 6.2, 6.9))
        # Commonwealth: the pieces not yet taken
        c.saveLayer(None, None)
        slab(c, tpath(path(PRE72), M), COL['plt'], HGT['plt'] * hk * (1 - sink), steps=12)
        for yr, pw, g, o, rad in ORIG:   # punch out pieces that have started to move
            if piece_k(yr, t, lag_of(pw)) > 0:
                q = tpath(path(g.buffer(2e3)), M)
                for dy in np.linspace(0, -(HGT['plt'] * hk + 2), 10):
                    qq = skia.Path(q); qq.offset(0, dy); c.drawPath(qq, skia.Paint(BlendMode=skia.BlendMode.kClear, AntiAlias=True))
        c.restore()
        # re-draw the land/neighbour floor under the punched holes is implicit (layer was transparent)
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            lift = 110 * np.sin(np.pi * clamp(k)) ; settle = k >= 1
            h = lerp(HGT['plt'], HGT[pw], ease(seg(k, 0.5, 1.0))) * hk
            col_k = ease(seg(k, 0.35, 0.75))
            cc = rgb(COL['plt']); cp = rgb(COL[pw])
            col = '#%02x%02x%02x' % tuple(int(255 * lerp(a, b, col_k)) for a, b in ((cc.fR, cp.fR), (cc.fG, cp.fG), (cc.fB, cp.fB)))
            tops[i] = slab(c, tpath(path(g), M), col, h, lift, steps=8)
    else:
        k = ease(seg(t, 8.0, 9.2))
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            down = 0.0 if yr == '1772' else ease(seg(t, 7.8, 8.4))
            if down < 1: slab(c, tpath(path(g), M), COL[pw], HGT[pw] * (1 - down), steps=6)
        top = slab(c, tpath(path(PLT91), M), COL['plt'], HGT['plt'] * k + 0.01, 30 * np.sin(np.pi * k) * (k < 1), steps=14)
        if top is not None and k > 0.95:
            c.drawPath(top, stroke(rgb('#f2b632', seg(t, 9.0, 9.4)), 5, dash=[18, 10]))
    c.restore()
    def at(lon, lat, h=0): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y() - h
    la = seg(t, 2.2, 2.7)
    leader(c, *at(16.2, 53.0, HGT['prussia']), 'PRUSSIA', la, '#2f5f9e', 90)
    leader(c, *at(31.5, 55.0, HGT['russia']), 'RUSSIA', la, '#2c7a4c', 90)
    leader(c, *at(19.5, 48.2, HGT['habsburg']), 'AUSTRIA', la, '#9a6a10', 80)
    na = seg(t, 2.4, 2.9) * (1 - seg(t, 5.6, 6.0)) if not alt else seg(t, 9.0, 9.4)
    leader(c, *at(25.2, 52.2, HGT['plt']), 'POLAND–LITHUANIA', na, '#a3202c', 150)
    # type
    if t < 2.4:
        a = seg(t, 0.05, 0.4) * (1 - seg(t, 2.0, 2.4))
        text(c, 'WHAT IF', W / 2, 300, font('SourceSans3-SemiBold.ttf', 140), rgb('#1d2433', a), spacing=10, reveal=seg(t, 0.1, 0.8))
        text(c, 'POLAND–LITHUANIA HAD NEVER', W / 2, 1640, font('SourceSans3-SemiBold.ttf', 50), rgb('#1d2433', a), spacing=4, reveal=seg(t, 0.4, 1.1))
        text(c, 'BEEN PARTITIONED?', W / 2, 1710, font('SourceSans3-SemiBold.ttf', 50), rgb('#e4505c', a), spacing=4, reveal=seg(t, 0.6, 1.3))
    yr = year_at(t)
    if yr and 2.0 < t < 6.9:
        a = seg(t, 2.0, 2.4) * (1 - seg(t, 6.5, 6.85))
        text(c, yr, W / 2, 1700, font('SourceSans3-Regular.ttf', 180), rgb('#1d2433', a), spacing=10)
        text(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1780, font('SourceSans3-SemiBold.ttf', 36), rgb('#e4505c', a), spacing=10)
    if 6.9 < t < 8.4:
        a = seg(t, 6.9, 7.2) * (1 - seg(t, 8.1, 8.4))
        text(c, 'But what if the reforms', W / 2, 1660, font('SourceSans3-Regular.ttf', 64), rgb('#1d2433', a), reveal=seg(t, 6.9, 7.5))
        text(c, 'of 1791 had survived?', W / 2, 1740, font('SourceSans3-SemiBold.ttf', 64), rgb('#e4505c', a), reveal=seg(t, 7.1, 7.7))
    if t > 9.0:
        a = seg(t, 9.0, 9.4)
        text(c, 'STILL ON THE MAP', W / 2, 1690, font('SourceSans3-SemiBold.ttf', 92), rgb('#1d2433', a), spacing=8, reveal=seg(t, 9.0, 9.7))
        text(c, 'the Commonwealth in its 1791 borders', W / 2, 1760, font('SourceSans3-Regular.ttf', 40), rgb('#8a6a10', a))
    hyp = t >= 7.9; a = seg(t, 2.0, 2.3) * (1 - seg(t, 7.3, 7.6)) if not hyp else seg(t, 7.9, 8.2)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 28); w = text_width(s, fn, 4) + 48
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, 130, w, 54), 27, 27)
        c.drawRRect(r, fill(rgb('#f2b632' if hyp else '#1d2433', a)))
        text(c, s, 70 + w / 2, 167, fn, rgb('#1d2433' if hyp else '#ffffff', a), spacing=4)


POST = Post(grain=0.012, vignette=0.18, bloom=0.0, ca=0.0, shoulder=0.0, seed=201)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.0, 2.9, 3.6, 5.0, 7.6, 9.9], POST, f'{ROOT}/render/c15t'); sheet(fs, f'{ROOT}/render/c15_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept15_isometric.mp4', POST, stills=(1.0, 2.9, 3.6, 5.0, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=6, workers=2, scene_mod='concept15_isometric')
