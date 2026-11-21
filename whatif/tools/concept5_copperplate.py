"""CONCEPT 5 - Copperplate.
An 18th-century hand-engraved, hand-coloured map comes alive under a rostrum camera: laid paper with chain lines,
engraved water-lines around every coast, ruled sea hatching, borders as dotted engraved lines with the period
practice of 'outline colouring' (a watercolour band painted just inside each border). Annexations bloom in
as wet watercolour from the annexing side; a quill re-engraves the 1791 border in the alternate timeline."""
import cv2
from styles_common import *

PAPER_C = np.array([0.925, 0.886, 0.800], np.float32); INK = rgb('#2b2118'); SEPIA = rgb('#5a4330')
WASH = dict(plt='#c23b3b', prussia='#3f74b8', russia='#5d9448', habsburg='#d39a2f', ottoman='#9a7a5a', sweden='#8a8aa8',
            hre='#a89a80', saxony='#a89a80', other='#a89a80')
GOLD = rgb('#b8862b')


def _paper():
    n = noise_tex(H, W, 7, seed=8, base=2); fine = cv2.GaussianBlur(np.random.default_rng(3).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)
    chain = 0.012 * np.exp(-((np.arange(W) % 96 - 48) / 2.0) ** 2)[None, :]                       # chain lines
    laid = 0.006 * (np.sin(np.arange(H) * 2 * np.pi / 3.2)[:, None])                                  # laid lines
    v = 1 + n * 0.035 + fine * 0.02 - chain + laid
    fox = np.clip(noise_tex(H, W, 5, seed=21, base=4) - 2.0, 0, None) * 0.08                           # foxing spots
    img = PAPER_C[None, None] * v[..., None] - fox[..., None] * np.array([0.1, 0.35, 0.6], np.float32)
    yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
    img *= (1 - 0.25 * np.clip(r - 0.3, 0, 1) ** 1.5)[..., None]
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
PAPER = _paper()


def cam(t):
    A = Cam(*ll(21.2, 52.3), zoom=1.35, rot=-4, tilt=0.18, oy=120)
    B = Cam(*ll(24.4, 52.3), zoom=0.66, rot=0, tilt=0.06, oy=40)
    C_ = Cam(*ll(24.2, 52.6), zoom=0.72, rot=1.5, tilt=0.12, oy=40)
    if t < 3.0: return Cam.blend(A, B, ease(seg(t, 0.3, 3.0)))
    return Cam.blend(B, C_, ease(seg(t, 6.6, 10.5)))


def wash_band(c, p, col, a, width=26, blur=6):
    """period outline colouring: watercolour band inside the border."""
    if a <= 0: return
    c.save(); c.clipPath(p, doAntiAlias=True)
    q = stroke(rgb(col, 0.55 * a), width * 2); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    q.setBlendMode(skia.BlendMode.kMultiply); c.drawPath(p, q)
    c.drawPath(p, fill(rgb(col, 0.10 * a)))
    c.restore()


def engraved_border(c, p, a, w=1.6, k=1.0):
    if a <= 0 or k <= 0: return
    q = skia.Path(p)
    if k < 1:
        te = skia.TrimPathEffect.Make(0, k)
        if te: s_ = stroke(skia.Color4f(INK.fR, INK.fG, INK.fB, a), w); s_.setPathEffect(te); c.drawPath(q, s_)
        return
    c.drawPath(q, stroke(skia.Color4f(INK.fR, INK.fG, INK.fB, 0.85 * a), w))
    c.drawPath(q, stroke(skia.Color4f(INK.fR, INK.fG, INK.fB, 0.6 * a), w * 1.6, dash=[1.2, 5.5]))


def water_lines(c, M, land_p, z):
    # concentric engraved lines around coasts, then ruled hatching in the open sea
    for d, al in ((17, 0.28), (9, 0.5)):
        c.drawPath(land_p, stroke(rgb('#2b2118', al), 2 * d + 1.1))
        c.drawPath(land_p, stroke(rgb('#ecdfc8'), 2 * d - 1.1))
    c.drawPath(land_p, fill(rgb('#ecdfc8')))


def label(c, M, lon, lat, s, size, a, col=SEPIA, sp=8, rot=0, f='CormorantSC-SemiBold.ttf', reveal=1.0):
    if a <= 0: return
    x, y = M.mapXY(*ll(lon, lat)).x(), M.mapXY(*ll(lon, lat)).y()
    c.save(); c.translate(x, y); c.rotate(rot)
    text(c, s, 0, 0, font(f, size), skia.Color4f(col.fR, col.fG, col.fB, a), spacing=sp, reveal=reveal, rise=6)
    c.restore()


def cartouche(c, cx, cy, w, h, a, k=1.0):
    if a <= 0: return
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), 10, 10)
    c.drawRRect(r, fill(rgb('#efe3c9', 0.93 * a)))
    for inset, wd in ((0, 2.4), (9, 0.9)):
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2 + inset, cy - h / 2 + inset, w - 2 * inset, h - 2 * inset), 10, 10)
        p = skia.Path(); p.addRRect(rr)
        s_ = stroke(skia.Color4f(INK.fR, INK.fG, INK.fB, a), wd)
        te = skia.TrimPathEffect.Make(0, max(0.001, min(k, 1.0))) if k < 1 else None
        if te: s_.setPathEffect(te)
        c.drawPath(p, s_)
    # corner flourishes
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = cx + sx * (w / 2 - 22), cy + sy * (h / 2 - 22); p = skia.Path()
        p.moveTo(x, y + sy * 14); p.cubicTo(x - sx * 30, y + sy * 10, x - sx * 10, y - sy * 30, x + sx * 14, y)
        c.drawPath(p, stroke(skia.Color4f(INK.fR, INK.fG, INK.fB, a * k), 1.3)); c.drawCircle(x, y, 3.2, fill(skia.Color4f(INK.fR, INK.fG, INK.fB, a * k)))


def stamp(c, s, x, y, col, a, dashed=False):
    if a <= 0: return
    f = font('SourceSans3-SemiBold.ttf', 30); w = text_width(s, f, 4) + 44
    r = skia.Rect.MakeXYWH(x, y, w, 54)
    c.drawRect(r, fill(rgb('#efe3c9', 0.85 * a)))
    c.drawRect(r, stroke(skia.Color4f(col.fR, col.fG, col.fB, a), 2.0, dash=[8, 5] if dashed else None))
    text(c, s, x + w / 2, y + 38, f, skia.Color4f(col.fR, col.fG, col.fB, a), spacing=4)


def quill(c, x, y, a):
    if a <= 0: return
    c.save(); c.translate(x, y); c.rotate(-38)
    p = skia.Path(); p.moveTo(0, 0); p.cubicTo(14, -60, 30, -220, 22, -330); p.cubicTo(5, -230, -8, -90, 0, 0)
    c.drawPath(p, fill(rgb('#f4eee2', 0.92 * a))); c.drawPath(p, stroke(rgb('#5b4a3a', 0.7 * a), 1.4))
    sp = skia.Path(); sp.moveTo(2, -10); sp.cubicTo(12, -100, 22, -220, 22, -328)
    c.drawPath(sp, stroke(rgb('#7a6550', 0.8 * a), 1.2))
    sh = skia.Paint(Color4f=rgb('#000000', 0.18 * a), AntiAlias=True); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    c.restore()


def scene(c, t, f):
    POST_STATE['dof'] = 0.35
    c.drawImage(PAPER, 0, 0)
    M = cam(t).matrix(); z = cam(t).zoom
    land = tpath(path(L['land']), M)
    # sea: ruled hatching, clipped to the sea
    c.save(); c.clipPath(land, skia.ClipOp.kDifference, True)
    hp = skia.Path()
    for y in range(-200, H + 200, 7): hp.moveTo(-50, y); hp.lineTo(W + 50, y + 18)
    c.drawPath(hp, stroke(rgb('#3a2e22', 0.30), 0.9))
    c.restore()
    water_lines(c, M, land, z)
    c.save(); c.clipPath(land, doAntiAlias=True)
    c.drawImage(PAPER, 0, 0, SAMP, skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=0.0))
    # rivers
    for r_ in RIVERS: c.drawPath(tpath(path(r_['geom']), M), stroke(rgb('#3a2e22', 0.55), 1.1 if r_['rank'] > 4 else 1.6))
    alt = t >= 7.6
    # neighbours (outline colouring)
    for nm in ('prussia', 'russia', 'habsburg', 'ottoman', 'sweden', 'hre', 'saxony'):
        p = tpath(path(NEIGH[nm]), M); wash_band(c, p, WASH[nm], 0.75); engraved_border(c, p, 0.8, 1.3)
    # Commonwealth
    cw_a = 1 - seg(t, 6.2, 6.8) * (t < 7.6)
    g = PLT91 if alt else PRE72
    p = tpath(path(g), M)
    if alt:
        k = ease(seg(t, 8.0, 9.6))
        wash_band(c, p, WASH['plt'], k, 30); wash_band(c, p, '#c99a3a', k * 0.6, 12, 3)
        te = skia.TrimPathEffect.Make(0, max(0.001, k)) if k < 1 else None
        s_ = stroke(GOLD, 3.2, dash=[14, 8]);
        if te: s_.setPathEffect(skia.PathEffect.MakeCompose(skia.DashPathEffect.Make([14, 8], 0), te))
        c.drawPath(p, s_)
    else:
        wash_band(c, p, WASH['plt'], cw_a, 30); engraved_border(c, p, cw_a, 1.8)
    # annexation: watercolour bloom spreading from the annexing side
    if not alt:
        for i, (yr, pw, geom, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            pp = tpath(path(geom), M); ox, oy = M.mapXY(*o).x(), M.mapXY(*o).y()
            R = rad * z / 1000 * 1.25 * eout(k, 2)
            c.save(); c.clipPath(pp, doAntiAlias=True)
            blob = rough_circle(ox, oy, R, seed=i * 7, amp=0.16)
            c.drawPath(blob, fill(rgb('#ecdfc8')))                # lift the old colour first (clean wash)
            q = fill(rgb(WASH[pw], 0.42)); q.setBlendMode(skia.BlendMode.kMultiply); c.drawPath(blob, q)
            e = stroke(rgb(WASH[pw], 0.55 * (1 - 0.6 * k)), 7); e.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 3))
            c.drawPath(blob, e)                                    # wet edge
            c.restore()
            if k > 0.95: engraved_border(c, pp, 0.8, 1.4)
    c.restore()
    land_s = stroke(rgb('#2b2118', 0.9), 1.6); c.drawPath(land, land_s)
    # labels
    la = seg(t, 1.6, 2.4)
    label(c, M, 15.2, 53.4, 'PRUSSIA', 30, la * 0.9, rot=-4)
    label(c, M, 31.2, 55.6, 'RUSSIAN EMPIRE', 32, la * 0.9, rot=-6)
    label(c, M, 19.0, 48.0, 'HABSBURG MONARCHY', 28, la * 0.9, rot=3)
    label(c, M, 18.4, 56.2, 'BALTIC SEA', 26, la * 0.7, col=rgb('#3a2e22'), sp=12, f='CormorantSC-Medium.ttf')
    nm_a = seg(t, 2.0, 2.8) * (1 - seg(t, 6.0, 6.6)) if not alt else seg(t, 9.0, 9.8)
    label(c, M, 23.4, 52.4, 'POLISH–LITHUANIAN', 40, nm_a, col=rgb('#4a1d18'), sp=7, rot=-8, f='CormorantSC-SemiBold.ttf')
    label(c, M, 24.4, 51.6, 'COMMONWEALTH', 40, nm_a, col=rgb('#4a1d18'), sp=10, rot=-8, f='CormorantSC-SemiBold.ttf')
    # strike-through when the state disappears
    if 6.0 < t < 7.6:
        k = ease(seg(t, 6.0, 6.5)); a = 1 - seg(t, 7.0, 7.5)
        x0, y0 = M.mapXY(*ll(19.6, 53.0)).x(), M.mapXY(*ll(19.6, 53.0)).y(); x1, y1 = M.mapXY(*ll(28.6, 51.3)).x(), M.mapXY(*ll(28.6, 51.3)).y()
        c.drawLine(x0, y0, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, stroke(rgb('#2b2118', 0.85 * a), 4))
    # quill drawing the 1791 border
    if 7.9 < t < 9.8:
        k = ease(seg(t, 8.0, 9.6)); meas = skia.PathMeasure(p, False); L_ = meas.getLength()
        pos = meas.getPosTan(L_ * k)
        if pos: quill(c, pos[0].x(), pos[0].y(), seg(t, 7.9, 8.2) * (1 - seg(t, 9.5, 9.8)))
    # titling
    if t < 2.4:
        a = seg(t, 0.15, 0.6) * (1 - seg(t, 1.9, 2.4))
        cartouche(c, W / 2, 430, 860, 330, a, ease(seg(t, 0.1, 1.1)))
        text(c, 'WHAT IF', W / 2, 395, font('CormorantSC-SemiBold.ttf', 120), rgb('#2b2118', a), spacing=14, reveal=seg(t, 0.3, 1.1))
        text(c, 'Poland–Lithuania had never', W / 2, 468, font('CormorantGaramond-Italic[wght].ttf', 58), rgb('#4a1d18', a), reveal=seg(t, 0.6, 1.4))
        text(c, 'been partitioned?', W / 2, 532, font('CormorantGaramond-Italic[wght].ttf', 58), rgb('#4a1d18', a), reveal=seg(t, 0.8, 1.6))
    yr = year_at(t)
    if yr and t < 7.2:
        a = seg(t, 2.0, 2.4) * (1 - seg(t, 6.9, 7.2))
        cartouche(c, W / 2, 1560, 560, 200, a)
        text(c, yr, W / 2, 1585, font('EBG-Medium.ttf', 104), rgb('#2b2118', a), spacing=6)
        sub = YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS')
        text(c, sub, W / 2, 1630, font('CormorantSC-SemiBold.ttf', 30), rgb('#4a1d18', a), spacing=8)
    if 6.9 < t < 8.4:
        a = seg(t, 7.0, 7.4) * (1 - seg(t, 8.0, 8.4))
        text(c, 'But what if the reforms', W / 2, 1520, font('CormorantGaramond-Italic[wght].ttf', 66), rgb('#2b2118', a), reveal=seg(t, 7.0, 7.6))
        text(c, 'of 1791 had survived?', W / 2, 1600, font('CormorantGaramond-Italic[wght].ttf', 66), rgb('#2b2118', a), reveal=seg(t, 7.2, 7.8))
    if t > 9.0:
        a = seg(t, 9.0, 9.5)
        cartouche(c, W / 2, 1560, 640, 200, a)
        text(c, '1791 borders', W / 2, 1560, font('EBG-Medium.ttf', 70), rgb('#2b2118', a), reveal=seg(t, 9.0, 9.6))
        text(c, 'STILL ON THE MAP', W / 2, 1615, font('CormorantSC-SemiBold.ttf', 32), rgb('#8a5a14', a), spacing=8)
    # status
    sa = seg(t, 2.0, 2.4)
    if t < 7.9: stamp(c, 'DOCUMENTED HISTORY', 70, 150, rgb('#2b2118'), sa * (1 - seg(t, 7.4, 7.8)))
    else: stamp(c, 'HYPOTHETICAL', 70, 150, rgb('#9a2a1a'), seg(t, 7.9, 8.3), dashed=True)


POST = Post(grain=0.03, vignette=0.42, bloom=0.0, ca=0.0008, shoulder=0.0, seed=31)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [0.9, 2.8, 4.2, 6.3, 7.5, 9.9], POST, f'{ROOT}/render/c5t'); sheet(fs, f'{ROOT}/render/c5_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept5_copperplate.mp4', POST, stills=(0.9, 2.8, 4.2, 6.3, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=8, workers=3, scene_mod='concept5_copperplate')
