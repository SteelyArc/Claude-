"""CONCEPT 12 - Blueprint.
The state as a piece of engineering: a cyanotype drafting sheet with grid, title block, compass rose, scale bar and
dimension lines. Borders are drafted in white technical pen; the Commonwealth is a solid-hatched 'structure'.
Each partition is drafted as a demolition: the annexed section is cut along a red-pencil line, labelled with a
callout ('SECTION A - to PRUSSIA') and slid out of the plan. The 1791 Constitution appears as a revision stamp
('REV. 3 MAY 1791'), and the alternate timeline re-drafts the 1791 outline in dashed red pencil, marked HYPOTHETICAL."""
import cv2
from styles_common import *

BLUE = '#0f3e7a'; LINE = '#e8f1ff'; PENCIL = '#ff5a4a'
MONO = 'CourierPrime-Regular.ttf'; SANS = 'SourceSans3-SemiBold.ttf'
BOUNDS = (ll(14.2, 52)[0], ll(24, 46.2)[1], ll(34.2, 52)[0], ll(24, 58.8)[1])
M0 = fit_matrix(BOUNDS, 60, 360, 960, 1080, pad=0.02)
LETTER = 'ABCDEFGH'
TO = dict(prussia='PRUSSIA', russia='RUSSIA', habsburg='AUSTRIA')


def _sheet():
    n = noise_tex(H, W, 7, seed=141, base=3)
    blot = np.clip(noise_tex(H, W, 4, seed=142, base=2), -2, 2) * 0.05
    img = np.stack([np.full((H, W), v, np.float32) for v in (0.06, 0.24, 0.48)], -1) * (1 + n[..., None] * 0.05 + blot[..., None])
    for x in range(0, W, 30): img[:, x:x + 1] += 0.035 * (2.5 if x % 150 == 0 else 1)
    for y in range(0, H, 30): img[y:y + 1] += 0.035 * (2.5 if y % 150 == 0 else 1)
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
SHEET = _sheet()


def pen(col=LINE, w=2.0, a=1.0, dash=None): return stroke(rgb(col, a), w, dash=dash, cap=skia.Paint.kButt_Cap)


def drafted(c, p, k, col=LINE, w=2.0, a=1.0, dash=None):
    if k <= 0: return
    s = pen(col, w, a, dash)
    if k < 1:
        te = skia.TrimPathEffect.Make(0, max(0.001, k))
        if te: s.setPathEffect(skia.PathEffect.MakeCompose(skia.DashPathEffect.Make(dash, 0), te) if dash else te)
    c.drawPath(p, s)


def hatch45(c, p, col, a, gap=12):
    if a <= 0: return
    c.save(); c.clipPath(p, doAntiAlias=True); b = p.getBounds(); hp = skia.Path()
    for x in np.arange(b.left() - b.height(), b.right(), gap): hp.moveTo(x, b.bottom()); hp.lineTo(x + b.height(), b.top())
    c.drawPath(hp, pen(col, 1.1, a)); c.restore()


def mono(c, s, x, y, size, a, col=LINE, align='c', sp=2, f=MONO, reveal=1.0):
    if a > 0: text(c, s, x, y, font(f, size), rgb(col, a), align=align, spacing=sp, reveal=reveal, rise=0, stagger=0.9)


def callout(c, x0, y0, x1, y1, label, k, col=PENCIL):
    if k <= 0: return
    fn = font(SANS, 26); tw = text_width(label, fn, 1)
    right = x1 >= x0
    if right and x1 + 90 + tw > W - 60: right = False; x1 = x0 - (x1 - x0)
    if not right and x1 - 90 - tw < 60: right = True; x1 = x0 + abs(x1 - x0)
    c.drawCircle(x0, y0, 6, fill(rgb(col, k)))
    p = skia.Path(); p.moveTo(x0, y0); p.lineTo(x1, y1); p.lineTo(x1 + (80 if right else -80), y1)
    drafted(c, p, k, col, 2.2)
    mono(c, label, x1 + (90 if right else -90), y1 + 9, 26, seg(k, 0.6, 1.0), col, 'l' if right else 'r', 1, SANS)


def compass(c, x, y, r, a):
    if a <= 0: return
    c.drawCircle(x, y, r, pen(LINE, 1.6, a)); c.drawCircle(x, y, r * 0.8, pen(LINE, 1.0, a))
    for ang, L_ in ((0, 1.0), (90, 0.6), (180, 0.6), (270, 0.6), (45, 0.35), (135, 0.35), (225, 0.35), (315, 0.35)):
        th = np.radians(ang - 90); p = skia.Path(); p.moveTo(x + np.cos(th) * r * L_, y + np.sin(th) * r * L_)
        p.lineTo(x + np.cos(th + 1.4) * 9, y + np.sin(th + 1.4) * 9); p.lineTo(x, y); p.close(); c.drawPath(p, fill(rgb(LINE, a * 0.9)))
    mono(c, 'N', x, y - r - 12, 26, a, sp=0, f=SANS)


def title_block(c, t, a):
    x, y, w, h = 60, 1470, 960, 330
    r = skia.Rect.MakeXYWH(x, y, w, h); c.drawRect(r, pen(LINE, 2.5, a))
    for yy in (y + 120, y + 230): c.drawLine(x, yy, x + w, yy, pen(LINE, 1.4, a))
    c.drawLine(x + 640, y + 120, x + 640, y + h, pen(LINE, 1.4, a))
    return x, y, w, h


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(SHEET, 0, 0)
    drift = skia.Matrix(); s = 1.0 + 0.035 * ease(seg(t, 0, DUR)); drift.setScaleTranslate(s, s, W / 2 * (1 - s), 900 * (1 - s))
    M = skia.Matrix.Concat(drift, M0)
    # sheet frame
    c.drawRect(skia.Rect.MakeXYWH(30, 100, W - 60, H - 140), pen(LINE, 3, 0.8)); c.drawRect(skia.Rect.MakeXYWH(42, 112, W - 84, H - 164), pen(LINE, 1, 0.5))
    land = tpath(path(L['land']), M)
    c.save(); c.clipRect(skia.Rect.MakeXYWH(42, 300, W - 84, 1160))
    drafted(c, land, ease(seg(t, 0.0, 2.0)), LINE, 1.4, 0.55)
    for i, nm in enumerate(('prussia', 'russia', 'habsburg', 'ottoman')):
        drafted(c, tpath(path(NEIGH[nm]), M), ease(seg(t, 0.4 + 0.1 * i, 2.2 + 0.1 * i)), LINE, 1.3, 0.6, [10, 6])
    alt = t >= 7.4
    pre = tpath(path(PRE72), M); p91 = tpath(path(PLT91), M)
    if not alt:
        ka = ease(seg(t, 1.6, 2.8)); gone = seg(t, 6.3, 6.9)
        hatch45(c, pre, LINE, 0.30 * seg(t, 2.2, 2.8) * (1 - gone))
        drafted(c, pre, ka, LINE, 3.6, 1 - gone)
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            p = tpath(path(g), M)
            cut = seg(k, 0.0, 0.45); slide = ease(seg(k, 0.45, 1.0))
            # cut line in red pencil, then the section slides out toward the annexer
            drafted(c, p, cut, PENCIL, 3.2, 1 - slide * 0.6, [14, 7])
            c.save(); c.clipPath(p, doAntiAlias=True); c.drawPath(p, fill(rgb(BLUE, 0.85 * slide))); c.restore()
            cx, cy = M.mapXY(g.centroid.x, g.centroid.y).x(), M.mapXY(g.centroid.x, g.centroid.y).y()
            tx, ty = M.mapXY(NEIGH[pw].centroid.x, NEIGH[pw].centroid.y).x(), M.mapXY(NEIGH[pw].centroid.x, NEIGH[pw].centroid.y).y()
            d = np.hypot(tx - cx, ty - cy) + 1; m = skia.Matrix(); m.setTranslate((tx - cx) / d * 70 * slide, (ty - cy) / d * 70 * slide)
            q = tpath(p, m); hatch45(c, q, PENCIL, 0.5 * slide); c.drawPath(q, pen(PENCIL, 2.4, slide))
    else:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            if yr == '1772':
                p = tpath(path(g), M); hatch45(c, p, PENCIL, 0.35); c.drawPath(p, pen(PENCIL, 2.0, 0.8))
        k = ease(seg(t, 8.0, 9.4))
        hatch45(c, p91, LINE, 0.30 * k)
        drafted(c, p91, k, PENCIL, 4.0, 1.0, [20, 10])
    c.restore()
    # callouts per partition
    def at(lon, lat): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y()
    j = 0
    for i, (yr, pw, g, o, rad) in enumerate(ORIG):
        a0, b0 = BEAT[yr]; k = seg(t, a0 + 0.3 + lag_of(pw), a0 + 0.8 + lag_of(pw)) * (1 - seg(t, b0 - 0.1, b0 + 0.1))
        if k <= 0: continue
        cx, cy = M.mapXY(*g.representative_point().coords[0]).x(), M.mapXY(*g.representative_point().coords[0]).y()
        side = 1 if pw == 'russia' else -1 if pw == 'prussia' else 1
        callout(c, cx, cy, cx + side * 110, cy - 90 - 60 * (pw == 'habsburg') + 140 * (pw == 'habsburg'), f'{yr} · TO {TO[pw]}', k)
    la = seg(t, 1.8, 2.5)
    for nm, lon, lat in (('PRUSSIA', 15.3, 53.5), ('RUSSIAN EMPIRE', 32.6, 56.6), ('HABSBURG MONARCHY', 18.8, 47.5)):
        mono(c, nm, *at(lon, lat), 24, la * 0.85, sp=5, f=SANS)
    na = seg(t, 2.2, 2.8) * (1 - seg(t, 6.2, 6.8)) if not alt else seg(t, 9.0, 9.6)
    mono(c, 'POLISH–LITHUANIAN COMMONWEALTH', *at(23.8, 52.4), 26, na, sp=3, f=SANS)
    compass(c, 940, 420, 58, seg(t, 0.6, 1.4))
    # scale bar (true scale at map centre)
    _c = ll(24, 52); z = M.mapXY(_c[0], _c[1]).x() - M.mapXY(_c[0] - 300e3, _c[1]).x()
    sa = seg(t, 1.0, 1.8)
    for i in range(3):
        r = skia.Rect.MakeXYWH(90 + i * z / 3, 1410, z / 3, 12); c.drawRect(r, fill(rgb(LINE, sa * (0.9 if i % 2 == 0 else 0.0)))); c.drawRect(r, pen(LINE, 1.4, sa))
    mono(c, '0', 90, 1398, 20, sa); mono(c, '300 km', 90 + z, 1398, 20, sa)
    # title block
    x, y, w, h = title_block(c, t, seg(t, 0.2, 0.8))
    if t < 2.3:
        a = 1 - seg(t, 2.0, 2.3)
        mono(c, 'WHAT IF', W / 2, y + 92, 84, a, sp=14, f=SANS, reveal=seg(t, 0.2, 0.9))
        mono(c, 'POLAND–LITHUANIA HAD NEVER', x + 320, y + 190, 32, a, sp=3, reveal=seg(t, 0.5, 1.2))
        mono(c, 'BEEN PARTITIONED?', x + 320, y + 290, 40, a, PENCIL, sp=3, f=SANS, reveal=seg(t, 0.7, 1.4))
    yr = year_at(t)
    if 2.3 <= t < 7.2:
        a = seg(t, 2.3, 2.6) * (1 - seg(t, 6.9, 7.2))
        mono(c, 'DRAWING: THE COMMONWEALTH', W / 2, y + 80, 44, a, sp=4, f=SANS)
        mono(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), x + 320, y + 190, 32, a, PENCIL if yr != '1770' else LINE, sp=3, f=SANS)
        mono(c, 'STATUS: DOCUMENTED', x + 320, y + 290, 28, a, sp=3)
        mono(c, yr or '', x + 800, y + 210, 70, a, sp=4, f=SANS)
        mono(c, 'SHEET 1/2', x + 800, y + 300, 22, a, sp=2)
    if 6.9 < t < 8.3:
        a = seg(t, 6.9, 7.2) * (1 - seg(t, 8.0, 8.3))
        mono(c, 'REVISION?', W / 2, y + 80, 54, a, PENCIL, sp=8, f=SANS, reveal=seg(t, 6.9, 7.4))
        mono(c, 'WHAT IF THE REFORMS OF', x + 320, y + 190, 30, a, sp=2, reveal=seg(t, 7.0, 7.6))
        mono(c, '1791 HAD SURVIVED?', x + 320, y + 290, 34, a, PENCIL, sp=2, f=SANS, reveal=seg(t, 7.2, 7.8))
    if t > 8.3:
        a = seg(t, 8.3, 8.6)
        mono(c, 'REV. 3 MAY 1791', W / 2, y + 80, 52, a, PENCIL, sp=6, f=SANS)
        mono(c, 'STILL ON THE MAP', x + 320, y + 190, 36, a, sp=4, f=SANS, reveal=seg(t, 8.8, 9.6))
        mono(c, 'STATUS: HYPOTHETICAL', x + 320, y + 290, 28, a, PENCIL, sp=3)
        mono(c, '1791', x + 800, y + 210, 70, a, PENCIL, sp=4, f=SANS)
        mono(c, 'SHEET 2/2', x + 800, y + 300, 22, a, sp=2)
    # revision stamp
    if t > 8.3:
        k = seg(t, 8.3, 8.6); sc = 1 + 0.5 * (1 - eout(k, 3))
        c.save(); c.translate(290, 560); c.rotate(-10); c.scale(sc, sc)
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-170, -60, 340, 120), 10, 10); c.drawRRect(r, pen(PENCIL, 4, k))
        mono(c, 'HYPOTHETICAL', 0, -6, 38, k, PENCIL, sp=4, f=SANS); mono(c, 'REV. 3 MAY 1791', 0, 34, 24, k, PENCIL, sp=3)
        c.restore()
    hyp = t >= 7.9; a = seg(t, 2.0, 2.3) * (1 - seg(t, 7.3, 7.6)) if not hyp else seg(t, 7.9, 8.2)
    if a > 0:
        s_ = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font(SANS, 28); w_ = text_width(s_, fn, 4) + 44
        r = skia.Rect.MakeXYWH(70, 150, w_, 52); c.drawRect(r, fill(rgb(BLUE, 0.8 * a))); c.drawRect(r, pen(PENCIL if hyp else LINE, 2, a, [8, 5] if hyp else None))
        text(c, s_, 70 + w_ / 2, 185, fn, rgb(PENCIL if hyp else LINE, a), spacing=4)


POST = Post(grain=0.025, vignette=0.40, bloom=0.25, halation=0.0, ca=0.0010, shoulder=0.05, seed=151)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.2, 2.9, 3.9, 5.3, 7.5, 9.9], POST, f'{ROOT}/render/c12t'); sheet(fs, f'{ROOT}/render/c12_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept12_blueprint.mp4', POST, stills=(1.2, 2.9, 3.9, 5.3, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=6, workers=2, scene_mod='concept12_blueprint')
