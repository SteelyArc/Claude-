"""CONCEPT 4 - Alternate History / The Two Timelines.
Split screen, broadcast data-journalism look: flat vector maps on graphite, crisp hairlines, sans typography.
TOP = our history (cool, labelled DOCUMENTED). BOTTOM = alternate timeline (warm gold, dashed, labelled HYPOTHETICAL).
Sample: one 1791 map splits into two futures -> 1792 / 1793 / 1795 diverge -> the hypothetical takes over the frame."""
import numpy as np, skia
from shapely.geometry import Point
from core import *

S91 = L['stages']['1791']
PLT91 = S91['plt'].buffer(800).buffer(-800)
BG = rgb('#0d0e11'); LAND = rgb('#1d2025'); EDGE = rgb('#3a3e45')
COL = dict(prussia='#5d87b5', russia='#7d9a5c', habsburg='#bf8a48', ottoman='#6b5f55')
GOLD = rgb('#e8b54f'); COOL = rgb('#d7dde4')
SANS, SANSB = 'SourceSans3-Regular.ttf', 'SourceSans3-SemiBold.ttf'
SPLIT = 960      # seam y when fully split

# terrain relief under the flat graphic maps (soft-light), and Russia continued east of the 42E data window
_D = np.load(f'{ROOT}/data/relief.npz'); RX0, RY0, RX1, RY1, RRES = _D['extent']
_sh = _D['shade'].astype(np.float32) / 255; _ld = _D['land'].astype(np.float32) / 255
_rgba = np.dstack([_sh, _sh, _sh, np.ones_like(_sh)]) * (_ld[..., None] * 0.9)
RELIEF = skia.Image.fromarray((np.clip(_rgba, 0, 1) * 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
del _D, _sh, _ld, _rgba
from shapely.geometry import box as _box
from shapely.ops import transform as _tr
_ext = _tr(lambda x, y, z=None: FWD.transform(x, y), _box(37.0, 48.0, 62.0, 67.0).segmentize(0.25))
RUSSIA_DISP = S91['russia'].union(_ext.difference(S91['sweden'].buffer(2e3)).difference(S91['ottoman'].buffer(2e3))).buffer(0)


def panel_cam(cy_screen, zoom=0.64):
    c0 = ll(25.3, 52.4)
    return Cam(c0[0], c0[1], zoom, 0, 0, oy=cy_screen - H / 2)


def flatmap(c, M, a=1.0, desat=0.0, cam=None):
    c.saveLayer()
    c.drawPath(tpath(path(L['land']), M), fill(LAND))
    c.save(); c.concat(M); c.translate(RX0, RY1); c.scale(RRES, -RRES)
    rp = skia.Paint(); rp.setBlendMode(skia.BlendMode.kSoftLight); rp.setAlphaf(0.85)
    c.drawImage(RELIEF, 0, 0, SAMP, rp); c.restore()
    for k in ('hre', 'saxony', 'sweden', 'denmark', 'other', 'venice', 'ragusa'):
        g = S91.get(k)
        if g is not None and not g.is_empty: c.drawPath(tpath(path(g), M), stroke(EDGE, 1.0))
    for k in ('ottoman', 'habsburg', 'russia', 'prussia'):
        p = tpath(path(RUSSIA_DISP if k == 'russia' else S91[k]), M); col = rgb(COL[k])
        col = lerpc((col.fR, col.fG, col.fB), (0.5, 0.52, 0.55), desat)
        c.drawPath(p, fill(skia.Color4f(*col, 0.13 * a))); c.drawPath(p, stroke(skia.Color4f(*col, 0.5 * a), 1.2))
    if cam is not None:   # focus falloff: the world fades to graphite away from the Commonwealth
        fx, fy = cam.pt(*ll(25.0, 52.6)); rr = 1000 * cam.zoom / 0.6
        fm = skia.Paint(); fm.setBlendMode(skia.BlendMode.kDstIn)
        fm.setShader(rad_grad(fx, fy, rr, [rgb('#000000', 1), rgb('#000000', 0.9), rgb('#000000', 0)], [0, .55, 1])); c.drawPaint(fm)
    c.restore()


def spread_geom(g, origin, k):
    if k >= 1: return g
    return Point(origin).buffer(1_400_000 * eout(k, 2), 96).intersection(g)


def gpath(g, M):
    p = path_nocache(g) if g is not None else skia.Path(); p = skia.Path(p); p.transform(M); return p


def arrow(c, M, pts, k, col, w=7):
    """curved campaign arrow (schematic) drawn with trim + head."""
    if k <= 0: return
    P = [M.mapXY(*ll(*q)) for q in pts]
    p = skia.Path(); p.moveTo(P[0]); p.quadTo(P[1], P[2])
    meas = skia.PathMeasure(p, False); L_ = meas.getLength()
    seg_ = skia.Path(); meas.getSegment(0, L_ * k, seg_, True)
    c.drawPath(seg_, stroke(skia.Color4f(col.fR, col.fG, col.fB, 0.35), w * 3, glow=8))
    c.drawPath(seg_, stroke(col, w, cap=skia.Paint.kButt_Cap))
    for j in range(7):   # flowing particles along the drawn part
        u = ((j / 7) + 0.0) % 1.0 * k
        pp_, _t = meas.getPosTan(L_ * u)
        c.drawCircle(pp_.x(), pp_.y(), 5, stroke(skia.Color4f(1, 0.85, 0.75, col.fA * 0.5), 3, glow=4))
    pos, tan = meas.getPosTan(L_ * k)
    ang = np.degrees(np.arctan2(tan.y(), tan.x()))
    c.save(); c.translate(pos.x(), pos.y()); c.rotate(ang)
    hp = skia.Path(); hp.moveTo(22, 0); hp.lineTo(-10, -16); hp.lineTo(-4, 0); hp.lineTo(-10, 16); hp.close()
    c.drawPath(hp, fill(col)); c.restore()


def pill(c, x, y, s, kind, a, size=24):
    if a <= 0: return
    f = font(SANSB, size); w = text_width(s, f, 4) + 34
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y - size - 6, w, size + 18), 6, 6)
    if kind == 'doc':
        c.drawRRect(r, fill(rgb('#d7dde4', 0.95 * a))); text(c, s, x + 17, y, f, rgb('#0d0e11', a), align='l', spacing=4)
    else:
        c.drawRRect(r, fill(rgb('#2a2010', 0.9 * a))); c.drawRRect(r, stroke(rgb('#e8b54f', a), 2, dash=[8, 5]))
        text(c, s, x + 17, y, f, rgb('#ffd27a', a), align='l', spacing=4)
    return w


O_W, O_E, O_S, O_N = ll(13, 53), ll(36, 54), ll(21, 46.5), ll(30, 58)
TOP_EVENTS = [(L['gains']['93_pru'], 'prussia', O_W, 4.4, 5.5), (L['gains']['93_rus'], 'russia', O_E, 4.4, 5.6),
              (L['gains']['95_pru'], 'prussia', O_W, 6.6, 7.6), (L['gains']['95_rus'], 'russia', O_E, 6.6, 7.7),
              (L['gains']['95_rus_courland'], 'russia', O_N, 6.6, 7.7), (L['gains']['95_aut'], 'habsburg', O_S, 6.7, 7.7)]
YEARS = [(0.0, '1791'), (2.6, '1792'), (4.4, '1793'), (6.6, '1795')]
CAPS = {  # (top documented caption, bottom hypothetical caption)
    '1791': ('Constitution of 3 May', 'Constitution of 3 May'),
    '1792': ('Russia invades', 'The invasion is held back'),
    '1793': ('Second Partition', 'No second partition'),
    '1795': ('Third Partition: the state disappears', 'No third partition'),
}


def scene(c, t, f):
    c.clear(BG.toColor())
    sp = ease(seg(t, 0.6, 1.6))                # 0 = one full map, 1 = split
    take = ease(seg(t, 8.8, 10.2))             # bottom takes over the frame
    yr = [y for (ts, y) in YEARS if t >= ts][-1]
    # panel geometry
    top_c = lerp(H / 2, 500, sp) - 600 * take
    bot_c = lerp(H / 2, 1430, sp) - lerp(0, 1430 - 900, take)
    seam = lerp(H / 2, SPLIT, sp) - 980 * take
    zb = lerp(0.88, 0.58, sp) + 0.26 * take
    # ---------------- top panel: our history
    c.save(); c.clipRect(skia.Rect(0, 0, W, seam - 2))
    cam = panel_cam(top_c, lerp(0.88, 0.58, sp)); M = cam.matrix()
    flatmap(c, M, desat=0.35 * sp, cam=cam)
    c.save()
    for g, k_, o, a, b in TOP_EVENTS:
        k = seg(t, a, b)
        if k > 0: c.clipPath(gpath(spread_geom(g, o, k), M), skia.ClipOp.kDifference, True)
    pp = tpath(path(PLT91), M)
    c.drawPath(pp, fill(rgb('#c9d1db', 0.30))); c.restore()
    for g, k_, o, a, b in TOP_EVENTS:
        k = seg(t, a, b)
        if k > 0:
            gp = gpath(spread_geom(g, o, k), M); col = rgb(COL[k_])
            c.drawPath(gp, fill(skia.Color4f(col.fR, col.fG, col.fB, 0.85))); c.drawPath(gp, stroke(rgb('#0d0e11', 0.8), 1.2))
    gone = seg(t, 7.4, 8.0)
    cur = PLT91 if t < 4.4 else L['rump1793']
    if gone < 1:
        c.drawPath(tpath(path(cur), M), stroke(rgb('#ffffff', 0.95 * (1 - gone)), 2.4))
    if t > 7.4:
        c.drawPath(pp, stroke(rgb('#ffffff', 0.45 * gone), 1.6, dash=[6, 7]))
    af = 1 - seg(t, 4.2, 4.8)
    if af > 0:
        arrow(c, M, [(31.6, 49.3), (28.5, 49.4), (25.2, 50.5)], seg(t, 2.7, 3.7), rgb('#ff5a4e', af))
        arrow(c, M, [(31.0, 55.6), (28.5, 55.4), (26.0, 54.5)], seg(t, 2.9, 3.9), rgb('#ff5a4e', af))
    c.restore()
    # ---------------- bottom panel: alternate timeline
    c.save(); c.clipRect(skia.Rect(0, seam + 2 if sp > 0 else 0, W, H))
    cam = panel_cam(bot_c, zb); M = cam.matrix()
    flatmap(c, M, a=lerp(1, 0.8, sp), cam=cam)
    pp = tpath(path(PLT91), M)
    glow = 0.5 + 0.5 * np.sin(t * 2.4)
    c.drawPath(pp, fill(skia.Color4f(*lerpc((0.79, 0.82, 0.86), (0.91, 0.71, 0.31), sp), lerp(0.30, 0.34, sp))))
    if sp > 0:
        c.drawPath(pp, stroke(rgb('#ffcf6a', 0.35 * sp * (0.6 + 0.4 * glow)), 12, glow=10))
        c.drawPath(pp, stroke(rgb('#ffe2a0', sp), 2.6, dash=[14, 8]))
    else:
        c.drawPath(pp, stroke(rgb('#ffffff', 0.95), 2.4))
    # 1792 (hypothetical): arrows stop at the frontier
    for pts, t0 in [([(31.6, 49.3), (30.0, 49.4), (28.9, 50.0)], 2.7), ([(31.0, 55.6), (30.0, 55.5), (29.2, 55.2)], 2.9)]:
        k = seg(t, t0, t0 + 0.9); fade = 1 - seg(t, 4.2, 4.8)
        if k > 0 and fade > 0:
            arrow(c, M, pts, k, rgb('#ff5a4e', 0.75 * fade), w=6)
            if k >= 1:
                x, y = M.mapXY(*ll(*pts[-1])).x(), M.mapXY(*ll(*pts[-1])).y()
                c.drawCircle(x, y, 28 + 30 * seg(t, t0 + 0.9, t0 + 1.6), stroke(rgb('#ffd27a', fade * (1 - seg(t, t0 + 0.9, t0 + 1.6))), 3))
    c.restore()
    if 0 < take < 1:
        wy = seam
        lw = skia.Paint(); lw.setBlendMode(skia.BlendMode.kScreen)
        lw.setShader(lin_grad((0, wy - 220), (0, wy + 40), [rgb('#ffd27a', 0), rgb('#ffe7b8', 0.55 * np.sin(np.pi * take)), rgb('#ffd27a', 0)], [0, .8, 1]))
        c.drawRect(skia.Rect(0, wy - 220, W, wy + 40), lw)
    # ---------------- seam with year
    if sp > 0 and take < 1:
        a = sp * (1 - take)
        g = skia.Paint(); g.setShader(lin_grad((0, seam), (W, seam), [rgb('#d7dde4', 0), rgb('#ffffff', a), rgb('#e8b54f', a), rgb('#e8b54f', 0)], [0, .3, .7, 1]))
        g.setStrokeWidth(2.5); g.setStyle(skia.Paint.kStroke_Style); c.drawLine(0, seam, W, seam, g)
        gg = skia.Paint(); gg.setShader(lin_grad((0, seam), (W, seam), [rgb('#9fb6d6', 0), rgb('#cfe0ff', 0.5 * a), rgb('#ffcf7a', 0.5 * a), rgb('#ffcf7a', 0)], [0, .3, .7, 1]))
        gg.setStrokeWidth(18); gg.setStyle(skia.Paint.kStroke_Style); gg.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12)); gg.setBlendMode(skia.BlendMode.kScreen)
        c.drawLine(0, seam, W, seam, gg)
        fl = skia.Paint(); fl.setBlendMode(skia.BlendMode.kScreen)
        fl.setShader(rad_grad(W / 2, seam, 260, [rgb('#ffffff', 0.35 * a), rgb('#ffe2a8', 0.10 * a), rgb('#ffe2a8', 0)], [0, .3, 1])); c.drawCircle(W / 2, seam, 260, fl)
        f = font('Cinzel-Bold.ttf', 70); w = text_width(yr, f, 10) + 60
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W / 2 - w / 2, seam - 52, w, 104), 52, 52)
        c.drawRRect(r, fill(rgb('#0d0e11', 0.96 * a))); c.drawRRect(r, stroke(rgb('#ffffff', 0.6 * a), 1.5))
        ys = [ts for ts, y in YEARS if y == yr][0]; kk = eout(seg(t, ys, ys + 0.4))
        c.save(); c.clipRRect(r)
        text(c, yr, W / 2, seam + 26 + (1 - kk) * 70, f, rgb('#ffffff', a), spacing=10)
        c.restore()
    # ---------------- headers & captions (safe area) on soft dark backings
    if sp > 0:
        for y0, ba in ((300 - 600 * take - 70, 1.0), (1080 - 70, 1 - take)):
            bk = skia.Paint(); bk.setShader(lin_grad((0, y0 - 110), (0, y0 + 210), [rgb('#0d0e11', 0), rgb('#0d0e11', 0.72 * sp * ba), rgb('#0d0e11', 0)], [0, .4, 1]))
            c.drawRect(skia.Rect(0, y0 - 110, W, y0 + 210), bk)
    ha = seg(t, 1.3, 1.9)
    if ha > 0:
        ty = 300 - 600 * take
        pill(c, 92, ty, 'OUR HISTORY · DOCUMENTED', 'doc', ha * (1 - take))
        top_cap, bot_cap = CAPS[yr]
        ys = [ts for ts, y in YEARS if y == yr][0]; kc = seg(t, ys + 0.1, ys + 0.8)
        text(c, top_cap, 92, ty + 70, font(SANSB, 46), rgb('#ffffff', ha * (1 - take)), align='l', reveal=kc if yr != '1791' else ha)
        by = lerp(1080, 490, take)
        pill(c, 92, by, 'ALTERNATE TIMELINE · HYPOTHETICAL', 'hyp', ha)
        if take < 1:
            text(c, bot_cap, 92, by + 70, font(SANSB, 46), rgb('#ffd27a', ha * (1 - take)), align='l', reveal=kc if yr != '1791' else ha)
    # hook text over the single map
    k0 = seg(t, 0.0, 0.3) * (1 - seg(t, 0.55, 0.9))
    if k0 > 0:
        text(c, 'ONE STATE.', W / 2, 520, font('Cinzel-Bold.ttf', 96), rgb('#ffffff', k0), spacing=8, reveal=seg(t, 0, 0.4))
    k1 = seg(t, 0.75, 1.1) * (1 - seg(t, 1.5, 1.9))
    if k1 > 0:
        text(c, 'TWO FUTURES.', W / 2, SPLIT + 26, font('Cinzel-Bold.ttf', 96), rgb('#ffd27a', k1), spacing=8, reveal=seg(t, 0.75, 1.2),
             shadow=rgb('#000000', 0.9))
    # light scan line that cuts the map
    if 0.45 < t < 1.25:
        k = seg(t, 0.45, 1.25); x = lerp(-200, W + 200, ease(k))
        p = skia.Paint(); p.setShader(lin_grad((x - 300, 0), (x + 40, 0), [rgb('#ffffff', 0), rgb('#ffffff', 0.95)]))
        p.setStrokeWidth(4); p.setStyle(skia.Paint.kStroke_Style); c.drawLine(0, H / 2, x, H / 2, p)
        c.drawCircle(x, H / 2, 10, stroke(rgb('#ffe9b0', 0.9), 8, glow=10))
    # end title
    ea = seg(t, 9.7, 10.4)
    if ea > 0:
        text(c, 'POLAND–LITHUANIA', W / 2, 330 - 0, font('Cinzel-Bold.ttf', 74), rgb('#ffffff', ea), spacing=6, reveal=seg(t, 9.7, 10.5))
        text(c, 'still on the map', W / 2, 398, font('CG-MediumItalic.ttf', 54), rgb('#ffd27a', ea), reveal=seg(t, 9.9, 10.8))
        bk = skia.Paint(); bk.setShader(lin_grad((0, 1300), (0, 1520), [rgb('#0d0e11', 0), rgb('#0d0e11', 0.9 * ea)])); c.drawRect(skia.Rect(0, 1300, W, H), bk)
        text(c, 'Borders of 1791 shown unchanged: a thought experiment, not a forecast', W / 2, 1450,
             font(SANS, 27), rgb('#d9cfbf', ea), reveal=seg(t, 10.1, 11.0))
    if t < 0.2: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.2)))


POST = Post(grain=0.02, vignette=0.4, bloom=0.3, halation=0.25, ca=0.0014, shoulder=0.1, seed=9)

if __name__ == '__main__':
    out = f'{ROOT}/previews/concepts/concept4_two_timelines.mp4'
    render(scene, 11.5, out, POST, stills=(0.4, 1.0, 3.6, 5.6, 8.2, 11.2), still_dir=f'{ROOT}/previews/concepts',
           mb=12, workers=4, scene_mod='concept4_two_timelines')
