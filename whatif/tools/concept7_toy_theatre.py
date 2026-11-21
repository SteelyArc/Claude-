"""CONCEPT 7 - Paper Toy Theatre.
A hand-made stop-motion paper theatre: the map is built from layered, hand-torn coloured card with real cast
shadows, framed by a cut-paper proscenium and curtains. It animates 'on twos' (12 drawings per second) with a
gentle paper boil. Annexed land is literally torn out of the Commonwealth and carried off by the neighbour;
a paper curtain closes on 1795 and reopens on the alternate timeline, where the 1791 state is stitched in gold."""
import cv2
from shapely.ops import unary_union
from styles_common import *

STAGE = (70, 330, 940, 1140)            # x, y, w, h of the stage opening
BOUNDS = (ll(14.0, 52)[0], ll(24, 45.8)[1], ll(34.5, 52)[0], ll(24, 59.4)[1])
M0 = fit_matrix(BOUNDS, *STAGE, pad=-0.05)
CARD = dict(plt='#c8343c', prussia='#3e6fb0', russia='#5e9a4c', habsburg='#e0a23a', ottoman='#a0785a', sweden='#7f93b0',
            hre='#b9a98a', saxony='#b9a98a', other='#b9a98a', sea='#24506e', back='#173a52')


def _fibre():
    n = noise_tex(H, W, 7, seed=77, base=3)
    fib = cv2.GaussianBlur(np.random.default_rng(5).normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=0.6, sigmaY=2.5)
    v = np.clip(0.93 + n * 0.035 + fib * 0.05, 0.75, 1.0)
    return to_image((np.dstack([v, v, v]) * 255).astype(np.uint8))
FIBRE = _fibre()


def tq(t): return np.floor(t * 12) / 12          # animate on twos


def boil(t, i, amp=1.4):
    r = np.random.default_rng(int(t * 12) * 131 + i); return r.uniform(-amp, amp, 2)


def card(c, p, col, t, i, lift=0.0, edge=True):
    """a torn paper card: white torn core showing at the edge, colour on top, cast shadow."""
    j = boil(t, i); q = skia.Path(p); q.offset(*j)
    sh = fill(rgb('#000000', 0.32 + 0.12 * lift)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5 + 14 * lift))
    s = skia.Path(q); s.offset(4 + 14 * lift, 7 + 22 * lift); c.drawPath(s, sh)
    torn = skia.DiscretePathEffect.Make(9, 2.2, i)
    if edge:
        e = fill(rgb('#f4efe4')); e.setPathEffect(torn); c.drawPath(q, e)
        e2 = stroke(rgb('#f4efe4'), 3.5); e2.setPathEffect(torn); c.drawPath(q, e2)
    top = fill(rgb(col) if isinstance(col, str) else col); top.setPathEffect(skia.DiscretePathEffect.Make(7, 1.4, i + 9))
    c.drawPath(q, top)


def peel_matrix(g, o, power, k):
    """carry a torn-out piece off toward the annexing power."""
    cx, cy = g.centroid.x, g.centroid.y; tx, ty = NEIGH[power].centroid.x, NEIGH[power].centroid.y
    d = np.hypot(tx - cx, ty - cy) + 1; ux, uy = (tx - cx) / d, (ty - cy) / d
    lift = np.sin(np.pi * min(k, 1)) ; m = skia.Matrix()
    px, py = M0.mapXY(cx, cy).x(), M0.mapXY(cx, cy).y()
    m.setTranslate(px + ux * 900 * k ** 2, py - uy * 900 * k ** 2 - 60 * lift)
    m.preRotate(-30 * k * np.sign(ux + 0.01)); m.preScale(1 + 0.18 * lift, 1 + 0.18 * lift); m.preTranslate(-px, -py)
    return skia.Matrix.Concat(m, M0), lift


def curtain(c, k, t):
    """paper stage curtains: k=0 open, 1 closed."""
    if k <= 0.001: return
    x0, y0, w, h = STAGE
    for side in (-1, 1):
        cw = w / 2 * k + 40
        for s in range(9):
            xx = (x0 + (s / 9) * cw) if side < 0 else (x0 + w - (s + 1) / 9 * cw)
            p = skia.Path(); p.addRect(skia.Rect.MakeXYWH(xx, y0 - 20, cw / 9 + 2, h + 40))
            col = rgb('#8e1a22') if s % 2 else rgb('#a6232b')
            card(c, p, col, t, 900 + s + (side > 0) * 20, 0.2, edge=False)


def proscenium(c, t):
    x0, y0, w, h = STAGE
    p = skia.Path(); p.addRect(skia.Rect.MakeWH(W, H))
    hole = skia.Path(); hole.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, w, h), 30, 30))
    c.save(); c.clipPath(hole, skia.ClipOp.kDifference, True)
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#2b1a14')))
    # layered cut-paper arch + pelmet scallops
    for i, (inset, col) in enumerate(((0, '#5a2a1e'), (16, '#c79a45'), (26, '#6e2f22'))):
        q = skia.Path(); q.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0 - 40 + inset, y0 - 40 + inset, w + 80 - 2 * inset, h + 80 - 2 * inset), 40, 40))
        card(c, q, col, t, 950 + i, 0.05, edge=i == 1)
    c.restore()
    for k_ in range(11):
        x = x0 + k_ * w / 10; q = skia.Path(); q.addCircle(x, y0 - 4, 46)
        card(c, q, '#7a2028' if k_ % 2 else '#8e2830', t, 980 + k_, 0.1, edge=False)
    q = skia.Path(); q.addRect(skia.Rect.MakeXYWH(x0 - 60, y0 - 120, w + 120, 100)); card(c, q, '#7a2028', t, 999, 0.15)
    q = skia.Path(); q.addRect(skia.Rect.MakeXYWH(x0 - 60, y0 + h + 12, w + 120, 70)); card(c, q, '#4a2a1c', t, 998, 0.1)


def tag(c, s, x, y, col, a, t, i, size=30, rot=-2.5, fnt='SourceSans3-SemiBold.ttf', ink='#1d1d1d', sp=3):
    if a <= 0: return
    f = font(fnt, size); w = text_width(s, f, sp) + size * 1.4; h = size * 1.75
    c.save(); c.translate(x, y); c.rotate(rot + boil(t, i, 0.6)[0]); c.translate(-w / 2, -h / 2)
    p = skia.Path(); p.addRect(skia.Rect.MakeWH(w, h)); card(c, p, col, t, i, 0.1)
    text(c, s, w / 2, h * 0.68, f, rgb(ink, a), spacing=sp)
    c.restore()


def scene(c, T, f):
    t = tq(T)
    POST_STATE['dof'] = 0.0
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb(CARD['back'])))
    x0, y0, w, h = STAGE
    c.save(); _cp = skia.Path(); _cp.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0, w, h), 30, 30)); c.clipPath(_cp, doAntiAlias=True)
    # sea: layered wave strips
    for k_ in range(14):
        p = skia.Path(); yy = y0 + k_ * 90 + 20
        p.moveTo(x0 - 50, yy)
        for xx in range(x0 - 50, x0 + w + 100, 60): p.quadTo(xx + 30, yy - 16 + 8 * np.sin(t * 2 + k_), xx + 60, yy)
        p.lineTo(x0 + w + 100, yy + 120); p.lineTo(x0 - 50, yy + 120); p.close()
        c.drawPath(p, fill(rgb('#24506e') if k_ % 2 else rgb('#2b5c7c')))
    M = M0
    alt = t >= 7.6
    for i, nm in enumerate(('sweden', 'hre', 'saxony', 'other', 'ottoman', 'habsburg', 'russia', 'prussia')):
        card(c, tpath(path(NEIGH[nm]), M), CARD[nm], t, i)
    if not alt:
        # pieces already taken: power-coloured card flat on the table
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            if piece_k(yr, t, lag_of(pw)) > 0: card(c, tpath(path(g), M), CARD[pw], t, 40 + i)
        # remaining Commonwealth card (cut around the pieces that have been torn out)
        c.save()
        for yr, pw, g, o, rad in ORIG:
            if piece_k(yr, t, lag_of(pw)) > 0: c.clipPath(tpath(path(g.buffer(-500)), M), skia.ClipOp.kDifference, True)
        if t < 6.7: card(c, tpath(path(PRE72), M), CARD['plt'], t, 30)
        c.restore()
        # pieces being torn out and carried away
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if 0 < k < 1:
                Mp, lift = peel_matrix(g, o, pw, k)
                card(c, tpath(path(g), Mp), CARD['plt'], t, 60 + i, lift)
    else:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            if yr == '1772': card(c, tpath(path(g), M), CARD[pw], t, 40 + i)
        k = eout(seg(t, 8.3, 9.0))
        m = skia.Matrix(); cx, cy = M.mapXY(*CITIES['Warsaw']).x(), M.mapXY(*CITIES['Warsaw']).y()
        m.setTranslate(cx, cy - 300 * (1 - k)); m.preScale(0.6 + 0.4 * k, 0.6 + 0.4 * k); m.preTranslate(-cx, -cy)
        p = tpath(tpath(path(PLT91), M), m)
        card(c, p, CARD['plt'], t, 31, lift=1 - k)
        if k > 0.99:   # hypothetical: gold stitching along the border
            st = stroke(rgb('#f2c14e', seg(t, 9.0, 9.4)), 3.4, dash=[12, 9]); c.drawPath(p, st)
    # labels on paper tapes
    la = seg(t, 2.0, 2.5)
    def at(lon, lat): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y()
    for nm, lon, lat, rot in (('PRUSSIA', 15.6, 53.6, -4), ('RUSSIA', 31.5, 55.0, 3), ('AUSTRIA', 20.0, 47.6, -2)):
        tag(c, nm, *at(lon, lat), '#f4efe4', la, t, 200 + len(nm), 30, rot, sp=4)
    if (t < 6.0) or t > 9.1:
        a = la * (1 - seg(t, 5.6, 6.0)) if t < 7 else seg(t, 9.1, 9.5)
        tag(c, 'POLAND–LITHUANIA', *at(24.0, 52.2), '#fff6e0', a, t, 250, 36, -6, 'EBG-SemiBold.ttf', '#7a141c', 2)
    curtain(c, ease(seg(T, 6.8, 7.5)) * (1 - ease(seg(T, 7.8, 8.5))), t)
    c.restore()
    proscenium(c, t)
    # titles
    if T < 2.3:
        a = seg(T, 0.0, 0.3) * (1 - seg(T, 1.9, 2.3))
        c.drawRect(skia.Rect.MakeXYWH(x0, y0, w, h), fill(rgb('#000000', 0.35 * a)))
        tag(c, 'WHAT IF', W / 2, 640, '#f4efe4', a * seg(t, 0.1, 0.4), t, 300, 110, -3, 'EBG-SemiBold.ttf', '#7a141c', 6)
        tag(c, 'POLAND–LITHUANIA', W / 2, 800, '#c8343c', a * seg(t, 0.4, 0.7), t, 301, 62, 2, 'EBG-SemiBold.ttf', '#fff6e0', 3)
        tag(c, 'had never been partitioned?', W / 2, 920, '#f4efe4', a * seg(t, 0.7, 1.0), t, 302, 48, -1.5, 'EBG-Italic.ttf', '#1d1d1d', 0)
    yr = year_at(t)
    if yr and t < 6.9:
        a = seg(t, 2.0, 2.3)
        tag(c, yr, W / 2, 1600, '#f4efe4', a, t, 400 + int(yr), 96, -2, 'EBG-SemiBold.ttf', '#1d1d1d', 4)
        tag(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1735, '#c8343c', a, t, 420, 32, 1.5, 'SourceSans3-SemiBold.ttf', '#fff6e0', 5)
    if 7.0 < t < 8.5:
        a = seg(t, 7.0, 7.2) * (1 - seg(t, 8.2, 8.5))
        tag(c, 'But what if the reforms', W / 2, 790, '#f4efe4', a, t, 500, 56, -2, 'EBG-Italic.ttf', '#1d1d1d', 0)
        tag(c, 'of 1791 had survived?', W / 2, 900, '#f4efe4', a * seg(t, 7.2, 7.4), t, 501, 56, 1.5, 'EBG-Italic.ttf', '#1d1d1d', 0)
    if t > 9.0:
        a = seg(t, 9.0, 9.3)
        tag(c, 'STILL ON THE MAP', W / 2, 1600, '#f2c14e', a, t, 600, 72, -2, 'EBG-SemiBold.ttf', '#4a1010', 4)
        tag(c, 'the 1791 Commonwealth', W / 2, 1730, '#f4efe4', a * seg(t, 9.2, 9.5), t, 601, 40, 1.5, 'EBG-Italic.ttf', '#1d1d1d', 0)
    hyp = t >= 7.9
    a = seg(t, 2.0, 2.3) * (1 - seg(t, 7.3, 7.6)) if not hyp else seg(t, 7.9, 8.2)
    tag(c, 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY', 260 if not hyp else 210, 190, '#f2c14e' if hyp else '#f4efe4', a, t, 700 + hyp, 30, -3, ink='#1d1d1d')
    # paper fibre over everything
    c.drawImage(FIBRE, 0, 0, SAMP, skia.Paint(BlendMode=skia.BlendMode.kMultiply))


POST = Post(grain=0.015, vignette=0.40, bloom=0.0, ca=0.0, shoulder=0.0, seed=71)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.2, 2.8, 4.0, 5.2, 7.2, 9.9], POST, f'{ROOT}/render/c7t'); sheet(fs, f'{ROOT}/render/c7_sheet.jpg', 3, 360)
    else:   # stop-motion: no motion blur
        render(scene, DUR, f'{ROOT}/previews/concepts/concept7_toy_theatre.mp4', POST, stills=(1.2, 2.8, 4.0, 5.2, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=1, workers=2, scene_mod='concept7_toy_theatre')
