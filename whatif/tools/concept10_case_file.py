"""CONCEPT 10 - The Case File.
A true-crime 'evidence board': cork, push-pins, prints of the genuine portraits and the 1773 satirical print,
a plain map print-out in the middle, marker ink and red string. Each partition is 'solved' on the board: red string
runs from the ruler who signed it to the land that was taken, and the piece is hatched in marker. The ruler on the
string is always the one actually reigning (Frederick II -> Frederick William II; Maria Theresa with Joseph II ->
Francis II; Catherine II throughout). In the alternate timeline the strings are cut, and the 1791 state is
outlined in highlighter under a 'HYPOTHETICAL' note."""
import cv2
from styles_common import *

BW, BH = 1500, 2700
MAP_R = (320, 1000, 860, 860)                   # map print-out on the board (x, y, w, h)
BOUNDS = (ll(14.2, 52)[0], ll(24, 46.0)[1], ll(34.0, 52)[0], ll(24, 58.8)[1])
MM = fit_matrix(BOUNDS, *MAP_R, pad=0.0)
MARK = dict(prussia='#1f4fb8', russia='#1d8a3c', habsburg='#e07b00')

def _img(f, w=560):
    return to_image(load_rgb(f'assets/images/{f}', w))
PH = {k: _img(f) for k, f in dict(fr2='frederick.jpg', cath='catherine.jpg', mt='maria_theresa.jpg', fw2='LOC_Friedrich_Wilhelm_II_Tardieu_after_Bornet.jpg',
                                   fr='Ketterlinus_Francis_II_1792_NGA.jpg', cake='kings_cake.jpg', const='constitution_1791.jpg').items()}
# (key, x, y, width, rot, caption, credit)
ITEMS = [('fr2', 250, 560, 290, -4, 'Frederick II', 'King of Prussia · 1772'),
         ('cake', 750, 520, 330, 2, 'The Troelfth Cake, 1773', 'satire of the First Partition'),
         ('cath', 1250, 560, 290, 3, 'Catherine II', 'Empress of Russia · 1772–95'),
         ('mt', 260, 2180, 280, 3, 'Maria Theresa', 'with Joseph II · 1772'),
         ('fw2', 750, 2230, 280, -2, 'Frederick William II', 'King of Prussia · 1793–95'),
         ('fr', 1240, 2180, 280, -3, 'Francis II', 'Emperor · 1795')]
POS = {k: (x, y) for k, x, y, *_ in ITEMS}
# which ruler signed for which power in which partition (documented)
RULER = {('1772', 'prussia'): 'fr2', ('1772', 'russia'): 'cath', ('1772', 'habsburg'): 'mt',
         ('1793', 'prussia'): 'fw2', ('1793', 'russia'): 'cath',
         ('1795', 'prussia'): 'fw2', ('1795', 'russia'): 'cath', ('1795', 'habsburg'): 'fr'}


def _cork():
    n = noise_tex(BH // 2, BW // 2, 7, seed=101, base=3)
    rng = np.random.default_rng(7); spk = cv2.GaussianBlur((rng.random((BH // 2, BW // 2)) > 0.985).astype(np.float32), (0, 0), 0.8)
    v = 1 + n * 0.10 - spk * 0.9 + cv2.GaussianBlur(rng.normal(0, 1, (BH // 2, BW // 2)).astype(np.float32), (0, 0), 0.7) * 0.07
    base = np.array([0.62, 0.45, 0.30], np.float32)
    img = np.clip(base[None, None] * v[..., None], 0, 1)
    img = cv2.resize(img, (BW + 400, BH + 400), interpolation=cv2.INTER_CUBIC)
    return to_image((img * 255).astype(np.uint8))
CORK = _cork()


def cam(t):
    keys = [(0.0, 750, 470, 1.32, -1.5), (1.9, 750, 520, 1.25, -1.0), (2.7, 750, 1390, 0.70, 0.0), (6.6, 760, 1390, 0.73, 0.6),
            (7.5, 750, 1420, 1.02, -0.8), (10.5, 760, 1420, 1.07, -0.3)]
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t <= t1:
            k = eexp(seg(t, t0, t1)) if t1 - t0 < 1.5 else ease(seg(t, t0, t1))
            v = [lerp(x, y, k) for x, y in zip(a, b)]
            v[2] = np.exp(lerp(np.log(a[2]), np.log(b[2]), k)); break
    hx = 6 * np.sin(t * 1.7) + 3 * np.sin(t * 3.1); hy = 5 * np.sin(t * 1.3 + 1)          # handheld
    m = skia.Matrix(); m.setTranslate(W / 2 + hx, H / 2 + hy); m.preRotate(v[3] + 0.3 * np.sin(t * 0.9)); m.preScale(v[2], v[2]); m.preTranslate(-v[0], -v[1])
    return m


def shadowed(c, r, blur=10, off=(6, 10), a=0.45):
    sh = fill(rgb('#000000', a)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur)); c.drawRect(r.makeOffset(*off), sh)


def pin(c, x, y, col='#d42a2a', s=1.0):
    sh = fill(rgb('#000000', 0.4)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4)); c.drawCircle(x + 6, y + 9, 13 * s, sh)
    c.drawCircle(x, y, 13 * s, skia.Paint(Shader=rad_grad(x - 4, y - 5, 16 * s, [rgb('#ffffff', 0.9), rgb(col), rgb(col).makeOpaque() if False else rgb('#5a0a0a')], [0, 0.35, 1]), AntiAlias=True))


def polaroid(c, key, x, y, w, rot, cap, sub, a=1.0, k=1.0):
    if a <= 0: return
    img = PH[key]; ih = w * img.height() / img.width(); ih = min(ih, w * 1.25)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(0.85 + 0.15 * k, 0.85 + 0.15 * k)
    r = skia.Rect.MakeXYWH(-w / 2 - 18, -ih / 2 - 18, w + 36, ih + 110)
    shadowed(c, r); c.drawRect(r, fill(rgb('#f5f2ea')))
    c.save(); c.clipRect(skia.Rect.MakeXYWH(-w / 2, -ih / 2, w, ih))
    sc = w / img.width(); c.drawImageRect(img, skia.Rect.MakeXYWH(-w / 2, -ih / 2, w, img.height() * sc), SAMP); c.restore()
    text(c, cap, 0, ih / 2 + 46, font('EBG-SemiBold.ttf', 30), rgb('#1a1a1a'))
    text(c, sub, 0, ih / 2 + 80, font('SourceSans3-Regular.ttf', 20), rgb('#555555'), spacing=1)
    c.restore()
    pin(c, x + np.sin(np.radians(rot)) * (ih / 2), y - ih / 2 - 4)


def index_card(c, x, y, w, h, rot, lines, a=1.0, col='#fbfaf4', ruled=True):
    if a <= 0: return
    c.save(); c.translate(x, y); c.rotate(rot)
    r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h); shadowed(c, r, 8, (4, 8), 0.4 * a); c.drawRect(r, fill(rgb(col, a)))
    if ruled:
        c.drawLine(-w / 2, -h / 2 + 52, w / 2, -h / 2 + 52, stroke(rgb('#d04040', 0.6 * a), 1.5))
        for yy in np.arange(-h / 2 + 90, h / 2, 38): c.drawLine(-w / 2, yy, w / 2, yy, stroke(rgb('#7fa0d0', 0.35 * a), 1))
    for s, yy, sz, fn, cl in lines: text(c, s, 0, yy, font(fn, sz), rgb(cl, a))
    c.restore()


def stamp(c, s, x, y, size, rot, a, col='#c42020'):
    if a <= 0: return
    sc = 1 + 0.6 * (1 - eout(clamp(a * 1.5), 3))
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc)
    f = font('SourceSans3-SemiBold.ttf', size); w = text_width(s, f, 6) + size * 0.8
    r = skia.Rect.MakeXYWH(-w / 2, -size * 0.95, w, size * 1.3)
    p = stroke(rgb(col, 0.85 * min(1, a * 1.5)), 5); p.setPathEffect(skia.DiscretePathEffect.Make(4, 1.2, 3)); c.drawRect(r, p)
    tp = rgb(col, 0.85 * min(1, a * 1.5)); text(c, s, 0, 0, f, tp, spacing=6)
    c.restore()


def string(c, p0, p1, k, a=1.0, sag=60):
    if k <= 0 or a <= 0: return
    path_ = skia.Path(); path_.moveTo(*p0)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + sag
    path_.quadTo(mx, my, *p1)
    s = stroke(rgb('#b0141c', a), 3.4); te = skia.TrimPathEffect.Make(0, max(0.001, k)) if k < 1 else None
    if te: s.setPathEffect(te)
    sh = stroke(rgb('#000000', 0.3 * a), 3.4); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 3))
    q = skia.Path(path_); q.offset(4, 8)
    if te: sh.setPathEffect(te)
    c.drawPath(q, sh); c.drawPath(path_, s)


def hatch(c, p, col, k, seed):
    """marker hatching inside a piece, drawn on progressively."""
    if k <= 0: return
    c.save(); c.clipPath(p, doAntiAlias=True)
    b = p.getBounds(); hp = skia.Path(); n = 0
    for x in np.arange(b.left() - b.height(), b.right(), 13):
        hp.moveTo(x, b.bottom()); hp.lineTo(x + b.height(), b.top()); n += 1
    s = stroke(rgb(col, 0.55), 5); s.setBlendMode(skia.BlendMode.kMultiply)
    meas_k = k
    s.setPathEffect(skia.DiscretePathEffect.Make(18, 1.5, seed))
    c.save(); c.clipRect(skia.Rect.MakeLTRB(b.left(), b.top(), b.left() + (b.width() + 20) * meas_k, b.bottom())); c.drawPath(hp, s); c.restore()
    c.restore()
    o = stroke(rgb(col, 0.9), 4.5); o.setPathEffect(skia.DiscretePathEffect.Make(14, 1.2, seed + 1))
    te = skia.TrimPathEffect.Make(0, max(0.001, min(1, k * 1.4)))
    if k * 1.4 < 1 and te: o.setPathEffect(skia.PathEffect.MakeCompose(te, skia.DiscretePathEffect.Make(14, 1.2, seed + 1)))
    c.drawPath(p, o)


def map_print(c, t):
    x, y, w, h = MAP_R; r = skia.Rect.MakeXYWH(x - 30, y - 30, w + 60, h + 110)
    shadowed(c, r, 14, (8, 14), 0.5); c.drawRect(r, fill(rgb('#f4f3ef')))
    c.save(); c.clipRect(skia.Rect.MakeXYWH(x, y, w, h))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), fill(rgb('#d9e2e8')))
    c.drawPath(tpath(path(L['land']), MM), fill(rgb('#f1efe8')))
    for nm, g in NEIGH.items(): c.drawPath(tpath(path(g), MM), stroke(rgb('#7a7a7a'), 1.4))
    alt = t >= 7.4
    c.drawPath(tpath(path(PLT91 if alt else PRE72), MM), fill(rgb('#e4dccb')))
    c.drawPath(tpath(path(PLT91 if alt else PRE72), MM), stroke(rgb('#333333'), 2.4))
    for lon, lat, s in ((15.4, 53.3, 'PRUSSIA'), (31.5, 55.2, 'RUSSIA'), (19.6, 48.0, 'HABSBURG MONARCHY')):
        q = MM.mapXY(*ll(lon, lat)); text(c, s, q.x(), q.y(), font('SourceSans3-SemiBold.ttf', 20), rgb('#555555'), spacing=4)
    q = MM.mapXY(*ll(24.0, 52.3)); text(c, 'POLAND–LITHUANIA', q.x(), q.y(), font('SourceSans3-SemiBold.ttf', 24), rgb('#222222'), spacing=3)
    if not alt:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            hatch(c, tpath(path(g), MM), MARK[pw], piece_k(yr, t, lag_of(pw)), i * 5 + 1)
    else:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            if yr == '1772': hatch(c, tpath(path(g), MM), MARK[pw], 1.0, i * 5 + 1)
        k = ease(seg(t, 8.1, 9.3)); p = tpath(path(PLT91), MM)
        hl = stroke(rgb('#ffe100', 0.55), 22); hl.setBlendMode(skia.BlendMode.kMultiply)
        te = skia.TrimPathEffect.Make(0, max(0.001, k)) if k < 1 else None
        if te: hl.setPathEffect(te)
        c.drawPath(p, hl)
    c.restore()
    text(c, 'Central Europe, c. 1770 — borders from historical map data', x + w / 2, y + h + 52, font('SourceSans3-Regular.ttf', 20), rgb('#666666'))
    for px, py in ((x - 10, y - 10), (x + w + 10, y - 10)): pin(c, px, py, '#e8e8e8', 0.9)


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#2a1c12')))
    M = cam(t); c.save(); c.concat(M)
    c.drawImage(CORK, -200, -200)
    map_print(c, t)
    for key, x, y, w, rot, cap, sub in ITEMS:
        polaroid(c, key, x, y, w, rot, cap, sub)
    # title card
    index_card(c, 750, 150, 760, 150, -1, [('CASE: A STATE THAT VANISHED', -12, 40, 'SourceSans3-SemiBold.ttf', '#1a1a1a'),
                                         ('Poland–Lithuania, 1772–1795', 38, 30, 'EBG-Italic.ttf', '#333333')])
    # year card between top row and map
    yr = year_at(t)
    if yr and 2.0 < t < 7.3:
        index_card(c, 750, 880, 420, 140, 1.5, [(yr, 30, 86, 'EBG-SemiBold.ttf', '#1a1a1a')], ruled=False)
        b = {'1770': 2.0, '1772': 3.2, '1793': 4.4, '1795': 5.6}[yr]
        if yr != '1770': stamp(c, YEAR_LABEL[yr], 750, 965, 34, -5, seg(t, b + 0.05, b + 0.3))
    # strings: ruler -> annexed piece
    alt = t >= 7.4
    cut = seg(t, 7.0, 7.4)
    for i, (yr_, pw, g, o, rad) in enumerate(ORIG):
        k = seg(t, BEAT[yr_][0] + lag_of(pw), BEAT[yr_][0] + 0.6 + lag_of(pw))
        if k <= 0 or alt: continue
        r = RULER[(yr_, pw)]; x0, y0 = POS[r]; x0 += 0; y0 -= 150 if y0 < 1000 else -160 + 300
        if POS[r][1] > 1500: y0 = POS[r][1] - 190
        q = MM.mapXY(*g.representative_point().coords[0])
        string(c, (x0, y0), (q.x(), q.y()), k, 1 - cut, sag=40)
        if k >= 1: pin(c, q.x(), q.y(), '#d42a2a', 0.7)
    # alternate timeline: sticky note + constitution print pinned over the map
    if t > 7.6:
        k = eout(seg(t, 7.6, 8.1), 3)
        polaroid(c, 'const', 1080 + 200 * (1 - k), 1120, 300, 5, 'Constitution of 3 May 1791', 'Wojniakowski, 1806', k, k)
        if t > 8.4:
            a = seg(t, 8.4, 8.7)
            c.save(); c.translate(430, 1150); c.rotate(-6); c.scale(0.9 + 0.1 * a, 0.9 + 0.1 * a)
            r = skia.Rect.MakeXYWH(-150, -110, 300, 220); shadowed(c, r, 10, (5, 10), 0.4 * a); c.drawRect(r, fill(rgb('#ffe45c', a)))
            text(c, 'HYPOTHETICAL', 0, -30, font('SourceSans3-SemiBold.ttf', 34), rgb('#1a1a1a', a), spacing=3)
            text(c, '1791 reforms survive', 0, 20, font('EBG-Italic.ttf', 30), rgb('#1a1a1a', a))
            text(c, '→ no partitions?', 0, 62, font('EBG-Italic.ttf', 30), rgb('#1a1a1a', a))
            c.restore()
    c.restore()
    # screen-space overlays: hook + pivot + status
    sh = rgb('#000000', 0.9)
    if t < 2.3:
        a = seg(t, 0.1, 0.4) * (1 - seg(t, 1.9, 2.3))
        bg = fill(rgb('#000000', 0.55 * a)); bg.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50)); c.drawRect(skia.Rect.MakeXYWH(40, 1240, 1000, 420), bg)
        text(c, 'WHAT IF', W / 2, 1390, font('SourceSans3-SemiBold.ttf', 140), rgb('#ffffff', a), spacing=8, reveal=seg(t, 0.15, 0.8), shadow=sh)
        text(c, 'POLAND–LITHUANIA HAD NEVER', W / 2, 1480, font('SourceSans3-SemiBold.ttf', 50), rgb('#ffffff', a), spacing=3, reveal=seg(t, 0.4, 1.1), shadow=sh)
        text(c, 'BEEN PARTITIONED?', W / 2, 1550, font('SourceSans3-SemiBold.ttf', 50), rgb('#ff4a4a', a), spacing=3, reveal=seg(t, 0.6, 1.3), shadow=sh)
    if 6.9 < t < 8.3:
        a = seg(t, 6.9, 7.2) * (1 - seg(t, 8.0, 8.3))
        bg = fill(rgb('#000000', 0.6 * a)); bg.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50)); c.drawRect(skia.Rect.MakeXYWH(40, 1500, 1000, 260), bg)
        text(c, 'But what if the reforms', W / 2, 1610, font('EBG-Italic.ttf', 66), rgb('#ffffff', a), reveal=seg(t, 6.9, 7.5), shadow=sh)
        text(c, 'of 1791 had survived?', W / 2, 1690, font('EBG-Italic.ttf', 66), rgb('#ffffff', a), reveal=seg(t, 7.1, 7.7), shadow=sh)
    if t > 9.2:
        a = seg(t, 9.2, 9.6)
        bg = fill(rgb('#000000', 0.6 * a)); bg.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50)); c.drawRect(skia.Rect.MakeXYWH(40, 1560, 1000, 240), bg)
        text(c, 'CASE REOPENED', W / 2, 1680, font('SourceSans3-SemiBold.ttf', 88), rgb('#ffe45c', a), spacing=6, reveal=seg(t, 9.2, 9.8), shadow=sh)
        text(c, 'the Commonwealth in its 1791 borders', W / 2, 1740, font('EBG-Italic.ttf', 40), rgb('#ffffff', a), shadow=sh)
    hyp = t >= 7.9; a = seg(t, 2.0, 2.4) * (1 - seg(t, 7.3, 7.7)) if not hyp else seg(t, 7.9, 8.3)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 30); w = text_width(s, fn, 4) + 46
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, 190, w, 54), 4, 4)
        c.drawRRect(rr, fill(rgb('#ffe45c' if hyp else '#f5f2ea', 0.95 * a))); c.drawRRect(rr, stroke(rgb('#1a1a1a', a), 2, dash=[8, 5] if hyp else None))
        text(c, s, 70 + w / 2, 227, fn, rgb("#1a1a1a", a), spacing=4)


POST = Post(grain=0.03, vignette=0.6, bloom=0.15, halation=0.1, ca=0.0012, shoulder=0.1, seed=111, warm=None)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.0, 3.0, 4.2, 5.4, 6.6, 9.9], POST, f'{ROOT}/render/c10t'); sheet(fs, f'{ROOT}/render/c10_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept10_case_file.mp4', POST, stills=(1.0, 3.0, 4.2, 5.4, 6.6, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=8, workers=2, scene_mod='concept10_case_file')
