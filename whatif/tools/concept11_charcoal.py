"""CONCEPT 11 - Charcoal Sketchbook.
A historian's sketchbook drawn live: toned paper with tooth, charcoal lines sketched in several restless passes,
smudged shadows, and the period draughtsman's red chalk (sanguine) for the Commonwealth. Each power's land is
hatched by hand at its own angle, so the map stays readable almost in monochrome. In 1795 the red chalk is
rubbed out with an eraser; in the alternate timeline it is drawn back in, with white-chalk highlights."""
import cv2
from styles_common import *

BOUNDS = (ll(14.2, 52)[0], ll(24, 45.8)[1], ll(34.2, 52)[0], ll(24, 59.0)[1])
M0 = fit_matrix(BOUNDS, 40, 330, 1000, 1220, pad=0.0)
CHAR = '#24221f'; SANG = '#a8432c'; CHALK = '#f6f1e6'
ANG = dict(prussia=45, russia=-45, habsburg=0, ottoman=90)
HAND = 'Caveat[wght].ttf'


def _paper():
    n = noise_tex(H, W, 7, seed=121, base=3)
    tooth = cv2.GaussianBlur(np.random.default_rng(1).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.9)
    v = 1 + n * 0.03 + tooth * 0.045
    img = np.array([0.80, 0.78, 0.735], np.float32)[None, None] * v[..., None]
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
PAPER = _paper()
TOOTH = cv2.GaussianBlur(np.random.default_rng(2).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.8)
_t = np.clip(0.5 + TOOTH * 0.5, 0, 1)
GRAIN = skia.Image.fromarray(np.dstack([np.zeros((H, W, 3), np.uint8), ((1 - _t) * 255).astype(np.uint8)]), colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


def sketch(c, p, col, k=1.0, w=2.6, passes=3, a=0.75, seed=0, wob=1.0):
    """restless multi-pass charcoal line, drawn on with k."""
    if k <= 0: return
    for i in range(passes):
        s = stroke(rgb(col, a * (1 - i * 0.22)), w * (1 - i * 0.2))
        de = skia.DiscretePathEffect.Make(16 + i * 5, (1.4 + i * 0.9) * wob, seed * 7 + i)
        q = skia.Path(p); q.offset((i - 1) * 1.3, (i % 2) * 1.1)
        if k < 1:
            te = skia.TrimPathEffect.Make(0, max(0.001, min(1, k * (1 + i * 0.05))))
            s.setPathEffect(skia.PathEffect.MakeCompose(de, te) if te else de)
        else: s.setPathEffect(de)
        c.drawPath(q, s)


def hatch(c, p, ang, col, k, a=0.55, gap=15, seed=0):
    if k <= 0: return
    c.save(); c.clipPath(p, doAntiAlias=True)
    b = p.getBounds(); cx, cy = b.centerX(), b.centerY(); R = max(b.width(), b.height())
    c.translate(cx, cy); c.rotate(ang)
    hp = skia.Path(); n = int(R / gap) + 2
    for i in range(-n, n):
        if (i + n) / (2 * n) > k: break
        y = i * gap + np.random.default_rng(abs(i * 31 + seed) + 1).uniform(-2, 2); hp.moveTo(-R, y); hp.lineTo(R, y + np.random.default_rng(abs(i) + 7).uniform(-6, 6))
    s = stroke(rgb(col, a), 2.2); s.setPathEffect(skia.DiscretePathEffect.Make(20, 1.6, seed)); c.drawPath(hp, s)
    c.restore()


def smudge(c, p, col, a, blur=24):
    if a <= 0: return
    q = fill(rgb(col, a)); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur)); q.setBlendMode(skia.BlendMode.kMultiply)
    c.save(); c.clipPath(p, doAntiAlias=True); c.drawPath(p, q); c.restore()


def hand(c, s, x, y, size, col, a, reveal=1.0, rot=0):
    if a <= 0: return
    c.save(); c.translate(x, y); c.rotate(rot)
    text(c, s, 0, 0, font(HAND, size), rgb(col, a), reveal=reveal, rise=0, stagger=0.85)
    c.restore()


def eraser(c, p, k):
    """rub out inside p with wide zig-zag strokes (returns as clip)."""
    b = p.getBounds(); e = skia.Path(); n = 16
    for i in range(n + 1):
        if i / n > k: break
        y = b.top() + i / n * b.height(); e.moveTo(b.left() - 40, y); e.lineTo(b.right() + 40, y + 50)
    return e


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(PAPER, 0, 0)
    drift = skia.Matrix(); s = 1.0 + 0.04 * ease(seg(t, 0, DUR)); drift.setScaleTranslate(s, s, W / 2 * (1 - s), 900 * (1 - s))
    M = skia.Matrix.Concat(drift, M0)
    # sketching the base map (coast, then neighbours)
    land = tpath(path(L['land']), M)
    smudge(c, land, '#6f6a62', 0.0)
    sketch(c, land, CHAR, ease(seg(t, 0.0, 2.2)), 2.4, 2, 0.6, 1)
    for i, nm in enumerate(('prussia', 'russia', 'habsburg', 'ottoman')):
        sketch(c, tpath(path(NEIGH[nm]), M), CHAR, ease(seg(t, 0.4 + i * 0.15, 2.4 + i * 0.15)), 1.8, 2, 0.45, 10 + i)
    alt = t >= 7.4
    pre = tpath(path(PRE72), M); p91 = tpath(path(PLT91), M)
    if not alt:
        ka = ease(seg(t, 1.8, 2.8))
        c.save()
        if t > 5.6:   # eraser rubbing the sanguine out after 1795
            c.clipPath(eraser(c, pre, ease(seg(t, 6.0, 6.8))), skia.ClipOp.kDifference, True) if False else None
        er = ease(seg(t, 6.1, 6.9))
        sm = fill(rgb(SANG, 0.34 * ka * (1 - er))); sm.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)); sm.setBlendMode(skia.BlendMode.kMultiply)
        c.save(); c.clipPath(pre, doAntiAlias=True); c.drawPath(pre, sm); c.restore()
        hatch(c, pre, -20, SANG, ka * (1 - er), 0.35, 20, 3)
        sketch(c, pre, SANG, ka * (1 - er), 3.2, 3, 0.9, 5)
        if 0 < er < 1:    # eraser smear
            e = eraser(c, pre, er); es = stroke(rgb('#d8d4cb', 0.55), 70); es.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
            c.save(); c.clipPath(pre, doAntiAlias=True); c.drawPath(e, es); c.restore()
        c.restore()
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            p = tpath(path(g), M)
            c.save(); c.clipPath(p, doAntiAlias=True); c.drawPath(p, fill(rgb('#cdcac2', 0.75 * min(1, k * 2)))); c.restore()   # rub the red out
            smudge(c, p, '#5a564f', 0.25 * k)
            hatch(c, p, ANG[pw], CHAR, k, 0.6, 13, i)
            sketch(c, p, CHAR, k, 2.4, 2, 0.8, 30 + i)
    else:
        k = ease(seg(t, 8.0, 9.4))
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            a_ = 1.0 if yr == '1772' else 1 - ease(seg(t, 7.9, 8.6))
            if a_ > 0:
                p = tpath(path(g), M); smudge(c, p, '#5a564f', 0.25 * a_); hatch(c, p, ANG[pw], CHAR, 1, 0.6 * a_, 13, i); sketch(c, p, CHAR, 1, 2.4, 2, 0.8 * a_, 30 + i)
        sm = fill(rgb(SANG, 0.38 * k)); sm.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)); sm.setBlendMode(skia.BlendMode.kMultiply)
        c.save(); c.clipPath(p91, doAntiAlias=True); c.drawPath(p91, sm); c.restore()
        hatch(c, p91, -20, SANG, k, 0.35, 20, 3)
        sketch(c, p91, SANG, k, 3.4, 3, 0.95, 5)
        ch = stroke(rgb(CHALK, 0.9 * seg(t, 9.0, 9.6)), 3.0, dash=[18, 12]); ch.setPathEffect(skia.PathEffect.MakeCompose(skia.DashPathEffect.Make([18, 12], 0), skia.DiscretePathEffect.Make(12, 1.2, 4)))
        q = skia.Path(p91); q.offset(-3, -3); c.drawPath(q, ch)
    # charcoal grain over the drawing
    c.drawImage(GRAIN, 0, 0, SAMP, skia.Paint(Alphaf=0.10))
    def at(lon, lat): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y()
    la = seg(t, 1.8, 2.6)
    hand(c, 'Prussia', *at(15.2, 53.6), 54, CHAR, la, seg(t, 1.8, 2.6), -6)
    hand(c, 'Russia', *at(31.2, 55.6), 58, CHAR, la, seg(t, 1.9, 2.7), -4)
    hand(c, 'Habsburg lands', *at(18.6, 47.6), 50, CHAR, la, seg(t, 2.0, 2.8), 3)
    na = seg(t, 2.2, 2.9) * (1 - seg(t, 6.2, 6.7)) if not alt else seg(t, 9.0, 9.6)
    hand(c, 'Poland–Lithuania', *at(23.8, 52.6), 62, '#7a2a1a', na, 1.0, -8)
    # notes in the margin
    if t < 2.4:
        a = 1 - seg(t, 2.0, 2.4)
        hand(c, 'What if', W / 2, 250, 150, CHAR, a, seg(t, 0.1, 0.8), -3)
        hand(c, 'Poland–Lithuania had never', W / 2, 1640, 72, CHAR, a, seg(t, 0.5, 1.3), -2)
        hand(c, 'been partitioned?', W / 2, 1730, 72, '#7a2a1a', a, seg(t, 0.8, 1.6), -2)
        ul = skia.Path(); ul.moveTo(280, 1760); ul.cubicTo(450, 1748, 650, 1772, 820, 1752); sketch(c, ul, '#7a2a1a', seg(t, 1.4, 1.9) * a, 3, 2, 0.8, 9)
    yr = year_at(t)
    if yr and 2.0 < t < 7.2:
        a = seg(t, 2.0, 2.3) * (1 - seg(t, 6.9, 7.2))
        b = {'1770': 2.0, '1772': 3.2, '1793': 4.4, '1795': 5.6}[yr]
        hand(c, f'c. {yr}' if yr == '1770' else yr, W / 2, 1660, 150, CHAR, a, seg(t, b, b + 0.4), -2)
        hand(c, YEAR_LABEL.get(yr, 'before the partitions').lower(), W / 2, 1750, 64, '#7a2a1a', a, seg(t, b + 0.2, b + 0.7), -2)
        circ = skia.Path(); circ.addOval(skia.Rect.MakeXYWH(W / 2 - 200, 1540, 400, 170)); sketch(c, circ, CHAR, seg(t, b + 0.1, b + 0.6) * a, 2.4, 2, 0.6, 50 + int(b * 10))
    if 6.9 < t < 8.4:
        a = seg(t, 6.9, 7.1) * (1 - seg(t, 8.1, 8.4))
        hand(c, 'But what if the reforms', W / 2, 1640, 78, CHAR, a, seg(t, 6.9, 7.6), -2)
        hand(c, 'of 1791 had survived?', W / 2, 1735, 78, '#7a2a1a', a, seg(t, 7.2, 7.9), -2)
    if t > 9.0:
        a = seg(t, 9.0, 9.3)
        hand(c, 'still on the map', W / 2, 1660, 110, '#7a2a1a', a, seg(t, 9.0, 9.8), -3)
        hand(c, '(the 1791 borders)', W / 2, 1745, 58, CHAR, a, seg(t, 9.4, 10.1), -2)
    hyp = t >= 7.9; a = seg(t, 2.0, 2.3) * (1 - seg(t, 7.3, 7.6)) if not hyp else seg(t, 7.9, 8.2)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 28); w = text_width(s, fn, 4) + 44
        r = skia.Rect.MakeXYWH(70, 130, w, 52); bx = skia.Path(); bx.addRect(r)
        sketch(c, bx, '#7a2a1a' if hyp else CHAR, 1.0, 2.2, 2, a * 0.9, 77)
        text(c, s, 70 + w / 2, 165, fn, rgb('#7a2a1a' if hyp else CHAR, a), spacing=4)


POST = Post(grain=0.03, vignette=0.38, bloom=0.0, ca=0.0, shoulder=0.0, seed=131)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.2, 2.9, 4.2, 6.5, 7.6, 9.9], POST, f'{ROOT}/render/c11t'); sheet(fs, f'{ROOT}/render/c11_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept11_charcoal.mp4', POST, stills=(1.2, 2.9, 4.2, 6.5, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=4, workers=2, scene_mod='concept11_charcoal')
