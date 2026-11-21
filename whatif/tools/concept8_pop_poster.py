"""CONCEPT 8 - Pop Poster.
Loud, flat, graphic and built for the scroll: a screen-printed poster look with a cream stock, flat inks, heavy black
key-lines, hard offset shadows with halftone dots and slight print mis-registration. Kinetic type slams in on the
beat with overshoot; the camera 'punches' on every date; a rotating sunburst drives the hook. Each annexed piece
pops off the Commonwealth with a bounce and flips to the annexing power's ink, its name slammed beside it."""
import cv2
from styles_common import *

CREAM = '#f3e9d2'; BLACK = '#141414'
INK = dict(plt='#e2332f', prussia='#2d5fa8', russia='#2e8b57', habsburg='#f2b41f', ottoman='#8a6a52', sweden='#8fa7c4',
           hre='#d8c9a6', saxony='#d8c9a6', other='#d8c9a6', sea='#7fc4c9')
BOUNDS = (ll(14.0, 52)[0], ll(24, 45.6)[1], ll(34.8, 52)[0], ll(24, 59.2)[1])
M0 = fit_matrix(BOUNDS, 30, 360, 1020, 1160, pad=-0.02)


def back_out(x, s=2.2):
    x = clamp(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


def _halftone(step=11):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = ((xx + yy) / np.sqrt(2)) % step - step / 2; v = ((xx - yy) / np.sqrt(2)) % step - step / 2
    d = np.sqrt(u ** 2 + v ** 2); dot = (d < step * 0.34).astype(np.float32)
    dot = cv2.GaussianBlur(dot, (0, 0), 0.6)
    a = (dot * 255).astype(np.uint8); z = np.zeros_like(a)
    return skia.Image.fromarray(np.dstack([z, z, z, a]), colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
DOTS = _halftone()


def _stock():
    n = noise_tex(H, W, 6, seed=88, base=3); v = np.clip(1 + n * 0.025, 0.9, 1.05)
    c_ = rgb(CREAM); img = np.dstack([v * c_.fR, v * c_.fG, v * c_.fB])
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
STOCK = _stock()


def punch(t):
    """camera punch-in on each beat (overshoot), slow drift otherwise."""
    s = 1.0
    for b in (2.0, 3.2, 4.4, 5.6, 8.0):
        k = seg(t, b, b + 0.45); s *= 1 + 0.06 * np.sin(np.pi * k) * (1 - k) * 2.2
    return s * (1 + 0.03 * seg(t, 0, DUR))


def shape(c, p, col, off=9, key=5.0, dots=True, mis=2.5):
    sh = skia.Path(p); sh.offset(off, off)
    c.drawPath(sh, fill(rgb(BLACK)))
    if dots:
        c.save(); c.clipPath(sh, doAntiAlias=True); c.restore()
    q = skia.Path(p); q.offset(-mis, mis * 0.4)                         # mis-registered colour plate
    c.drawPath(q, fill(rgb(col) if isinstance(col, str) else col))
    c.drawPath(p, stroke(rgb(BLACK), key))


def slam(c, s, x, y, size, k, col=BLACK, fnt='SourceSans3-SemiBold.ttf', sp=2, rot=0, box=None, shadow=True):
    if k <= 0: return
    sc = back_out(k) if k < 1 else 1.0
    f = font(fnt, size); w = text_width(s, f, sp)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc)
    if box:
        r = skia.Rect.MakeXYWH(-w / 2 - size * 0.35, -size * 0.92, w + size * 0.7, size * 1.25)
        c.drawRect(r.makeOffset(8, 8), fill(rgb(BLACK, min(1, k * 3)))); c.drawRect(r, fill(rgb(box, min(1, k * 3)))); c.drawRect(r, stroke(rgb(BLACK, min(1, k * 3)), 4))
    elif shadow:
        text(c, s, 6, 6, f, rgb(BLACK, min(1, k * 3)), spacing=sp)
    text(c, s, 0, 0, f, rgb(col, min(1, k * 3)) if isinstance(col, str) else col, spacing=sp)
    c.restore()


def sunburst(c, cx, cy, a, t, col='#f2b41f'):
    if a <= 0: return
    p = skia.Path(); n = 24
    for i in range(n):
        th0 = (i / n) * 2 * np.pi + t * 0.25; th1 = th0 + np.pi / n
        p.moveTo(cx, cy); p.lineTo(cx + 2400 * np.cos(th0), cy + 2400 * np.sin(th0)); p.lineTo(cx + 2400 * np.cos(th1), cy + 2400 * np.sin(th1)); p.close()
    c.drawPath(p, fill(rgb(col, a)))


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(STOCK, 0, 0)
    s = punch(t); cx, cy = W / 2, 940
    Ms = skia.Matrix(); Ms.setScaleTranslate(s, s, cx * (1 - s), cy * (1 - s)); M = skia.Matrix.Concat(Ms, M0)
    hook = t < 2.2
    sunburst(c, W / 2, 900, 0.55 * (1 - seg(t, 1.8, 2.3)), t)
    # sea panel
    land = tpath(path(L['land']), M)
    rect = skia.Rect.MakeXYWH(60, 380, 960, 1110)
    ma = seg(t, 1.6, 2.2) if t < 2.2 else 1.0
    if ma > 0:
        sc = back_out(ma); c.save(); c.translate(W / 2, 935); c.scale(sc, sc); c.translate(-W / 2, -935)
        c.drawRect(rect.makeOffset(12, 12), fill(rgb(BLACK))); c.drawRect(rect, fill(rgb(INK['sea'])))
        c.save(); c.clipRect(rect)
        for nm in ('sweden', 'hre', 'saxony', 'other', 'ottoman', 'habsburg', 'russia', 'prussia'):
            shape(c, tpath(path(NEIGH[nm]), M), INK[nm], off=0, key=3.0, mis=0)
        alt = t >= 7.4
        if not alt:
            if t < 6.6: shape(c, tpath(path(PRE72), M), INK['plt'], off=0, key=4.0, mis=1.5)
            for i, (yr, pw, g, o, rad) in enumerate(ORIG):
                k = piece_k(yr, t, lag_of(pw))
                if k <= 0: continue
                p = tpath(path(g), M); px, py = M.mapXY(g.centroid.x, g.centroid.y).x(), M.mapXY(g.centroid.x, g.centroid.y).y()
                pop = np.sin(np.pi * clamp(k * 1.25)) * (k < 0.8)
                col = INK['plt'] if k < 0.45 else INK[pw]
                m = skia.Matrix(); m.setTranslate(px - 10 * pop, py - 22 * pop); m.preScale(1 + 0.22 * pop, 1 + 0.22 * pop); m.preTranslate(-px, -py)
                shape(c, tpath(p, m), col, off=4 + 14 * pop, key=4.0, mis=1.5 * (k < 1))
        else:
            for i, (yr, pw, g, o, rad) in enumerate(ORIG):
                if yr == '1772': shape(c, tpath(path(g), M), INK[pw], off=0, key=3.0, mis=0)
            k = seg(t, 8.0, 8.7); p = tpath(path(PLT91), M)
            wx, wy = M.mapXY(*CITIES['Warsaw']).x(), M.mapXY(*CITIES['Warsaw']).y(); sc2 = back_out(k) if k > 0 else 0
            if sc2 > 0:
                m = skia.Matrix(); m.setTranslate(wx, wy); m.preScale(sc2, sc2); m.preTranslate(-wx, -wy)
                shape(c, tpath(p, m), INK['plt'], off=14 * k, key=5.0, mis=2)
                if k >= 1:
                    c.drawPath(p, stroke(rgb('#f2b41f'), 7, dash=[22, 14]))
        c.restore()
        c.drawRect(rect, stroke(rgb(BLACK), 7))
        c.restore()
    def at(lon, lat): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y()
    # annexer names slam in during their beat
    for yr in ('1772', '1793', '1795'):
        a0, b0 = BEAT[yr]
        for j, (pw, lon, lat, nm) in enumerate((('prussia', 17.5, 53.2, 'PRUSSIA'), ('russia', 29.5, 54.4, 'RUSSIA'), ('habsburg', 21.5, 48.6, 'AUSTRIA'))):
            if yr == '1793' and pw == 'habsburg': continue
            k = seg(t, a0 + 0.15 + lag_of(pw), a0 + 0.5 + lag_of(pw)) * (1 - seg(t, b0 - 0.15, b0))
            slam(c, nm, *at(lon, lat), 44, k, '#ffffff', 'SourceSans3-SemiBold.ttf', 3, rot=-4 + j * 3, box=INK[pw])
    if 2.0 < t < 5.8 or t > 9.0:
        k = seg(t, 2.1, 2.5) * (1 - seg(t, 5.4, 5.8)) if t < 7 else seg(t, 9.0, 9.4)
        slam(c, 'POLAND–LITHUANIA', *at(23.6, 52.4), 48, k, BLACK, 'SourceSans3-SemiBold.ttf', 2, rot=-5, box='#ffffff')
    # hook type
    if t < 2.3:
        a = 1 - seg(t, 1.9, 2.3)
        slam(c, 'WHAT', W / 2 - 110, 560, 190, seg(t, 0.05, 0.35) * a, BLACK, 'SourceSans3-SemiBold.ttf', -4, -6)
        slam(c, 'IF', W / 2 + 255, 560, 190, seg(t, 0.25, 0.55) * a, '#e2332f', 'SourceSans3-SemiBold.ttf', -4, 6)
        slam(c, 'POLAND–LITHUANIA', W / 2, 760, 92, seg(t, 0.55, 0.85) * a, '#ffffff', 'SourceSans3-SemiBold.ttf', 1, -3, box='#e2332f')
        slam(c, 'HAD NEVER BEEN', W / 2, 920, 84, seg(t, 0.85, 1.15) * a, BLACK, 'SourceSans3-SemiBold.ttf', 2, 2)
        slam(c, 'PARTITIONED?', W / 2, 1030, 116, seg(t, 1.05, 1.35) * a, '#2d5fa8', 'SourceSans3-SemiBold.ttf', 0, -2)
    yr = year_at(t)
    if yr and 2.0 < t < 7.0:
        for b in (2.0, 3.2, 4.4, 5.6):
            if b <= t < b + 1.2:
                k = seg(t, b, b + 0.35) * (1 - seg(t, 6.6, 7.0))
                slam(c, yr, W / 2, 1700, 190, k, '#f2b41f', 'SourceSans3-SemiBold.ttf', -2, -3)
                slam(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1790, 46, seg(t, b + 0.15, b + 0.45) * (1 - seg(t, 6.6, 7.0)), '#ffffff', 'SourceSans3-SemiBold.ttf', 4, 2, box=BLACK)
    if 6.6 < t < 8.2:
        a = 1 - seg(t, 7.9, 8.2)
        c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#141414', 0.82 * seg(t, 6.6, 6.9) * a)))
        sunburst(c, W / 2, 900, 0.18 * seg(t, 6.7, 7.0) * a, t, '#e2332f')
        slam(c, 'BUT WHAT IF', W / 2, 800, 120, seg(t, 6.8, 7.1) * a, '#ffffff', 'SourceSans3-SemiBold.ttf', 0, -3, shadow=False)
        slam(c, 'THE 1791 REFORMS', W / 2, 920, 80, seg(t, 7.0, 7.3) * a, '#f2b41f', 'SourceSans3-SemiBold.ttf', 1, 2, shadow=False)
        slam(c, 'HAD SURVIVED?', W / 2, 1030, 100, seg(t, 7.2, 7.5) * a, '#ffffff', 'SourceSans3-SemiBold.ttf', 0, -2, shadow=False)
    if t > 9.0:
        slam(c, 'STILL', W / 2, 1640, 130, seg(t, 9.0, 9.3), BLACK, 'SourceSans3-SemiBold.ttf', -2, -4)
        slam(c, 'ON THE MAP', W / 2, 1770, 96, seg(t, 9.2, 9.5), '#ffffff', 'SourceSans3-SemiBold.ttf', 1, 3, box='#e2332f')
        slam(c, '1791 BORDERS', W / 2, 1865, 40, seg(t, 9.4, 9.7), BLACK, 'SourceSans3-SemiBold.ttf', 6, 0, shadow=False)
    hyp = t >= 7.9; k = seg(t, 2.0, 2.3) * (1 - seg(t, 6.6, 6.8)) if not hyp else seg(t, 8.0, 8.3)
    slam(c, 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY', 70 + (150 if hyp else 225), 200, 32, k, BLACK, 'SourceSans3-SemiBold.ttf', 4, 0,
         box='#f2b41f' if hyp else '#ffffff')
    # halftone texture over the whole poster (subtle)
    c.drawImage(DOTS, 0, 0, SAMP, skia.Paint(Alphaf=0.05))


POST = Post(grain=0.012, vignette=0.12, bloom=0.0, ca=0.0, shoulder=0.0, seed=81)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.3, 2.8, 3.7, 5.0, 7.3, 9.9], POST, f'{ROOT}/render/c8t'); sheet(fs, f'{ROOT}/render/c8_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept8_pop_poster.mp4', POST, stills=(1.3, 2.8, 3.7, 5.0, 7.3, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=6, workers=2, scene_mod='concept8_pop_poster')
