"""CONCEPT 13 - Cross-Stitch.
The map is embroidered in an embroidery hoop: linen cloth, one cross-stitch per cell in cotton thread with real
sheen and shadow. Partitions are unpicked and re-stitched stitch by stitch in the annexing power's thread,
spreading from its side. The alternate timeline re-stitches the 1791 Commonwealth in crimson from Warsaw outward,
edged with a gold back-stitch that marks it as hypothetical. Titles are stitched lettering on a fabric label."""
import cv2
from styles_common import *

CS = 15                                    # stitch cell (px)
HX, HY, HR = W / 2, 860, 500               # hoop centre / radius
BOUNDS = (ll(14.6, 52)[0], ll(24, 46.4)[1], ll(33.6, 52)[0], ll(24, 58.6)[1])
M0 = fit_matrix(BOUNDS, HX - HR, HY - HR, 2 * HR, 2 * HR, pad=-0.04)
THREAD = dict(sea=None, land='#d9ccb0', plt='#b3192b', prussia='#2a5aa0', russia='#3c7d3a', habsburg='#d39a2a', ottoman='#8b6f9a',
              sweden='#7fa0c0', gold='#e6b84a')
NX, NY = int(2 * HR / CS) + 1, int(2 * HR / CS) + 1
X0, Y0 = HX - HR, HY - HR


def raster(g, ss=4):
    """fraction of each stitch cell covered by geometry g (screen space)."""
    img = np.zeros((NY * ss, NX * ss), np.uint8)
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon': continue
        for i, ring in enumerate([p.exterior, *p.interiors]):
            xy = np.asarray(ring.coords)[:, :2]
            pts = np.array([[M0.mapXY(x, y).x(), M0.mapXY(x, y).y()] for x, y in xy])
            pts = ((pts - [X0, Y0]) / CS * ss).astype(np.int32)
            cv2.fillPoly(img, [pts], 0 if i else 1)
    return cv2.resize(img.astype(np.float32), (NX, NY), interpolation=cv2.INTER_AREA)


yy, xx = np.mgrid[0:NY, 0:NX]
CX, CY = X0 + (xx + 0.5) * CS, Y0 + (yy + 0.5) * CS
INHOOP = np.hypot(CX - HX, CY - HY) < HR - 10
LAND = raster(L['land']) > 0.5
BASE = np.where(LAND, 1, 0)                 # 0 sea, 1 other land, then state codes
CODES = ['sea', 'land', 'prussia', 'russia', 'habsburg', 'ottoman', 'sweden', 'plt']
for code, g in (('sweden', NEIGH['sweden']), ('ottoman', NEIGH['ottoman']), ('habsburg', NEIGH['habsburg']), ('russia', NEIGH['russia']),
                ('prussia', NEIGH['prussia']), ('plt', PRE72)):
    BASE = np.where(raster(g) > 0.5, CODES.index(code), BASE)
PIECE = np.full((NY, NX), -1)
for i, (yr, pw, g, o, rad) in enumerate(ORIG):
    PIECE = np.where((raster(g) > 0.5) & (BASE == CODES.index('plt')), i, PIECE)
IN91 = raster(PLT91) > 0.5
# per-cell flip times
TFLIP = np.full((NY, NX), 99.0)
for i, (yr, pw, g, o, rad) in enumerate(ORIG):
    m = PIECE == i
    if not m.any(): continue
    ox, oy = M0.mapXY(*o).x(), M0.mapXY(*o).y(); d = np.hypot(CX - ox, CY - oy)
    d = d / max(d[m].max(), 1)
    TFLIP = np.where(m, BEAT[yr][0] + 0.12 + lag_of(pw) + d * 0.7, TFLIP)
WX, WY = M0.mapXY(*CITIES['Warsaw']).x(), M0.mapXY(*CITIES['Warsaw']).y()
DW = np.hypot(CX - WX, CY - WY); DW = DW / DW[IN91].max()
DSEW = np.hypot(CX - HX, CY - HY) / HR + np.random.default_rng(1).uniform(0, 0.08, (NY, NX))   # initial sewing order


def _linen():
    n = noise_tex(H, W, 6, seed=161, base=3)
    wx = 0.5 + 0.5 * np.sin(np.arange(W) * 2 * np.pi / 5.0)[None, :]; wy = 0.5 + 0.5 * np.sin(np.arange(H) * 2 * np.pi / 5.0)[:, None]
    weave = (wx * 0.5 + wy * 0.5) * 0.07
    slub = cv2.GaussianBlur(np.random.default_rng(3).normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=6, sigmaY=0.6) * 0.04
    v = 0.84 + n * 0.02 + weave + slub
    img = np.dstack([v * 0.97, v * 0.93, v * 0.84])
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
LINEN = _linen()


def lighten(hexc, k):
    c = rgb(hexc); return skia.Color4f(min(1, c.fR + (1 - c.fR) * k), min(1, c.fG + (1 - c.fG) * k), min(1, c.fB + (1 - c.fB) * k), 1)


def stitches(c, cells, col):
    if not len(cells): return
    p = skia.Path(); m = 2.2
    for (y, x) in cells:
        x0, y0 = X0 + x * CS, Y0 + y * CS
        p.moveTo(x0 + m, y0 + m); p.lineTo(x0 + CS - m, y0 + CS - m)
        p.moveTo(x0 + CS - m, y0 + m); p.lineTo(x0 + m, y0 + CS - m)
    sh = skia.Path(p); sh.offset(1.2, 1.8); c.drawPath(sh, stroke(rgb('#000000', 0.30), 4.6))
    c.drawPath(p, stroke(rgb(col), 4.4))
    hl = skia.Path(p); hl.offset(-0.7, -0.9); c.drawPath(hl, stroke(lighten(col, 0.45), 1.3))


def stitched_text(c, s, x, y, size, col, a, f='EBG-SemiBold.ttf', sp=2):
    if a <= 0: return
    fn = font(f, size); w = text_width(s, fn, sp); x0 = x - w / 2
    tb = skia.TextBlob.MakeFromString(s, fn)
    pth = skia.Path()
    cx = x0
    for ch in s:
        g = fn.getPath(fn.textToGlyphs(ch)[0]) if ch != ' ' else None
        if g: g.offset(cx, y); pth.addPath(g)
        cx += fn.measureText(ch) + sp
    c.drawPath(pth, fill(rgb(col, a * 0.95)))
    q = stroke(lighten(col, 0.5), 1.6, dash=[6, 4]); q.setAlphaf(a * 0.8); c.drawPath(pth, q)


def label_patch(c, x, y, w, h, a):
    if a <= 0: return
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), 14, 14)
    sh = fill(rgb('#000000', 0.25 * a)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)); c.drawRRect(r.makeOffset(3, 6) if hasattr(r, 'makeOffset') else r, sh)
    c.drawRRect(r, fill(rgb('#f4ecdc', a)))
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - w / 2 + 10, y - h / 2 + 10, w - 20, h - 20), 8, 8)
    c.drawRRect(rr, stroke(rgb('#b3192b', a), 2.4, dash=[9, 6]))


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(LINEN, 0, 0)
    # outside the hoop: darker, slightly wrinkled cloth
    hoop = skia.Path(); hoop.addCircle(HX, HY, HR)
    c.save(); c.clipPath(hoop, skia.ClipOp.kDifference, True); c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#3a2a1a', 0.35))); c.restore()
    c.save(); c.clipPath(hoop, doAntiAlias=True)
    sew = ease(seg(t, 0.0, 1.9))
    alt = t >= 7.4
    groups = {}
    shown = INHOOP & (DSEW <= sew * 1.12)
    code = BASE.copy()
    # current thread per cell
    for i in range(len(ORIG)):
        pw = ORIG[i][1]
        m = (PIECE == i) & (t >= TFLIP)
        code = np.where(m, CODES.index(pw), code)
    unpick = (PIECE >= 0) & (np.abs(t - TFLIP) < 0.03)
    gone = seg(t, 6.6, 7.2)
    if alt:
        k = ease(seg(t, 8.0, 9.3))
        back = IN91 & (DW <= k * 1.05)
        code = np.where(back, CODES.index('plt'), code)
        unpick |= IN91 & (np.abs(DW - k) < 0.02) & (k < 1)
    for ci, nm in enumerate(CODES):
        if THREAD.get(nm) is None: continue
        m = shown & (code == ci) & ~unpick
        if nm == 'plt' and not alt: m &= True
        if nm == 'land': m &= (np.random.default_rng(0).random((NY, NX)) < 1.0)
        cells = np.argwhere(m)
        col = THREAD[nm]
        if nm == 'land': col = '#e2d6bc'
        stitches(c, cells, col)
    # sea: a few running-stitch waves
    wa = seg(t, 0.8, 1.8)
    for j in range(9):
        p = skia.Path(); y0 = HY - HR + 60 + j * 110
        p.moveTo(HX - HR, y0)
        for x in range(int(HX - HR), int(HX + HR), 40): p.quadTo(x + 20, y0 - 10, x + 40, y0)
        c.save(); sea = np.argwhere(~LAND); c.restore()
        q = stroke(rgb('#5a86b8', 0.0 * wa), 2.2, dash=[10, 8]); c.drawPath(p, q)
    if alt:   # gold back-stitch around the hypothetical state
        p = tpath(path(PLT91), M0); a = seg(t, 9.0, 9.6)
        q = stroke(rgb(THREAD['gold'], a), 4.2, dash=[11, 5]); c.drawPath(p, q)
        q2 = stroke(lighten(THREAD['gold'], 0.6), 1.2, dash=[11, 5]); q2.setAlphaf(a); c.drawPath(p, q2)
    # the needle travelling with the current unpicking
    act = np.argwhere(unpick & shown)
    if len(act):
        y, x = act[len(act) // 2]; nx_, ny_ = X0 + x * CS + 8, Y0 + y * CS + 8
        p = skia.Path(); p.moveTo(nx_, ny_); p.lineTo(nx_ + 150, ny_ - 150)
        c.drawPath(p, stroke(rgb('#c9ccd2'), 4.0)); c.drawPath(p, stroke(rgb('#ffffff', 0.8), 1.2))
        thr = skia.Path(); thr.moveTo(nx_ + 140, ny_ - 140); thr.cubicTo(nx_ + 220, ny_ - 60, nx_ + 260, ny_ + 40, nx_ + 330, ny_ - 20)
        c.drawPath(thr, stroke(rgb('#b3192b'), 2.6))
    c.restore()
    # wooden hoop
    for r_, w_, col in ((HR + 16, 26, '#a8794a'), (HR + 16, 3, '#d9b48a'), (HR + 4, 3, '#6b4a2b')):
        c.drawCircle(HX, HY, r_, stroke(rgb(col), w_))
    c.drawRect(skia.Rect.MakeXYWH(HX - 34, HY - HR - 70, 68, 52), fill(rgb('#8f6a44'))); c.drawCircle(HX, HY - HR - 44, 14, fill(rgb('#c0c4cc')))
    # titles on a stitched fabric label
    if t < 2.3:
        a = seg(t, 0.1, 0.4) * (1 - seg(t, 2.0, 2.3))
        label_patch(c, W / 2, 1600, 960, 330, a)
        stitched_text(c, 'WHAT IF', W / 2, 1560, 104, '#b3192b', a * seg(t, 0.2, 0.6), sp=10)
        stitched_text(c, 'Poland–Lithuania had never', W / 2, 1640, 52, '#2b2b2b', a * seg(t, 0.5, 0.9), 'EBG-Italic.ttf', 1)
        stitched_text(c, 'been partitioned?', W / 2, 1706, 52, '#2b2b2b', a * seg(t, 0.7, 1.1), 'EBG-Italic.ttf', 1)
    yr = year_at(t)
    if yr and 2.0 < t < 7.2:
        a = seg(t, 2.0, 2.3) * (1 - seg(t, 6.9, 7.2))
        label_patch(c, W / 2, 1590, 640, 240, a)
        stitched_text(c, yr, W / 2, 1600, 110, '#2b2b2b', a, sp=8)
        stitched_text(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1664, 32, '#b3192b', a, 'SourceSans3-SemiBold.ttf', 5)
    if 6.9 < t < 8.4:
        a = seg(t, 6.9, 7.2) * (1 - seg(t, 8.1, 8.4))
        label_patch(c, W / 2, 1590, 960, 240, a)
        stitched_text(c, 'But what if the reforms', W / 2, 1580, 62, '#2b2b2b', a, 'EBG-Italic.ttf', 1)
        stitched_text(c, 'of 1791 had survived?', W / 2, 1655, 62, '#b3192b', a, 'EBG-Italic.ttf', 1)
    if t > 9.0:
        a = seg(t, 9.0, 9.4)
        label_patch(c, W / 2, 1590, 900, 240, a)
        stitched_text(c, 'STILL ON THE MAP', W / 2, 1600, 76, '#b3192b', a, sp=6)
        stitched_text(c, 'the Commonwealth in its 1791 borders', W / 2, 1664, 38, '#2b2b2b', a, 'EBG-Italic.ttf', 0)
    hyp = t >= 7.9; a = seg(t, 2.0, 2.3) * (1 - seg(t, 7.3, 7.6)) if not hyp else seg(t, 7.9, 8.2)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 28); w = text_width(s, fn, 4) + 48
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, 150, w, 54), 10, 10)
        c.drawRRect(r, fill(rgb('#f4ecdc', a))); c.drawRRect(r, stroke(rgb('#e6b84a' if hyp else '#2b2b2b', a), 2.4, dash=[8, 5]))
        text(c, s, 70 + w / 2, 186, fn, rgb('#8a5a00' if hyp else '#2b2b2b', a), spacing=4)


POST = Post(grain=0.02, vignette=0.42, bloom=0.0, ca=0.0, shoulder=0.0, seed=171)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.0, 2.9, 3.8, 5.0, 7.6, 9.9], POST, f'{ROOT}/render/c13t'); sheet(fs, f'{ROOT}/render/c13_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept13_cross_stitch.mp4', POST, stills=(1.0, 2.9, 3.8, 5.0, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=3, workers=2, scene_mod='concept13_cross_stitch')
