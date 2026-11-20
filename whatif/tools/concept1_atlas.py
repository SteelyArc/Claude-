"""CONCEPT 1 - Cinematic Historical Atlas ("Night Atlas").
Dark relief map from real elevation data, territories as luminous tinted glass, borders traced by light,
a 2.5D perspective camera. Sample: hook -> 1772 Commonwealth -> 1772/1793/1795 partitions -> hypothetical survival."""
import sys, numpy as np, skia, cv2
from core import *

D = np.load(f'{ROOT}/data/relief.npz')
X0, Y0, X1, Y1, RES = D['extent']
sh = D['shade'].astype(np.float32) / 255; land = D['land'].astype(np.float32) / 255; hgt = D['height'].astype(np.float32) / 255
# colour the relief: midnight sea, graphite land with warm highlights on ridges
sea = np.array([0.035, 0.065, 0.095], np.float32)
low = np.array([0.105, 0.115, 0.125], np.float32); high = np.array([0.20, 0.19, 0.17], np.float32)
base = low[None, None] * (1 - hgt[..., None]) + high[None, None] * hgt[..., None]
lit = base * (0.45 + 1.25 * sh[..., None])
# coastal glow (engraved-light coastline)
edge = cv2.GaussianBlur(land, (0, 0), 3.0); coast = np.clip((edge - 0.02) * 4, 0, 1) * (1 - land)
seacol = sea[None, None] + coast[..., None] * np.array([0.05, 0.11, 0.15], np.float32)
img = lit * land[..., None] + seacol * (1 - land[..., None])
RELIEF = to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))

S73, S91, S93, S95 = (L['stages'][k] for k in ('1773', '1791', '1793', '1795'))
PLT91 = S91['plt'].buffer(800).buffer(-800)
PAL = dict(plt='#b8323f', prussia='#4f7aa6', russia='#6f8a52', habsburg='#b07a3c', ottoman='#7a6250', other='#4a4a4a', gold='#f0cd86')
GOLD = rgb(PAL['gold']); IVORY = rgb('#f3ead8'); DIM = rgb('#9fb0bd')

CAM_HOOK = Cam(*ll(21.5, 52.0), zoom=1.45, rot=-16, tilt=0.62, oy=260)
CAM_WIDE = Cam(*ll(24.6, 52.6), zoom=0.60, rot=-2, tilt=0.30, oy=60)
CAM_PART = Cam(*ll(24.4, 52.4), zoom=0.66, rot=0, tilt=0.22, oy=40)
CAM_END = Cam(*ll(24.0, 52.6), zoom=0.72, rot=0, tilt=0.38, oy=80)


def camera(t):
    if t < 3.8: return Cam.blend(CAM_HOOK, CAM_WIDE, eexp(seg(t, 0, 3.8)) * 0.85 + ease(seg(t, 0, 3.8)) * 0.15)
    if t < 8.6: return Cam.blend(CAM_WIDE, CAM_PART, ease(seg(t, 3.8, 8.6)))
    return Cam.blend(CAM_PART, CAM_END, ease(seg(t, 8.6, 12.0)))


def glass(c, M, g, col, a, edge_a=0.0, edge_col=None, edge_w=1.4):
    if g is None or g.is_empty or a <= 0: return
    p = tpath(path(g), M)
    f = fill(rgb(col, a)); f.setBlendMode(skia.BlendMode.kScreen); c.drawPath(p, f)
    f2 = fill(rgb(col, a * 0.55)); f2.setBlendMode(skia.BlendMode.kMultiply); c.drawPath(p, f2)
    if edge_a > 0:
        c.drawPath(p, stroke(rgb(edge_col or col, edge_a), edge_w))


def spread(c, M, g, col, k, origin, a=0.62):
    """ink/light spread of a territory from an origin point (world), with a glowing front."""
    if k <= 0: return
    ox, oy = origin; R = 1_400_000 * eout(k, 2)
    circ = skia.Path(); circ.addCircle(ox, oy, R); circ.transform(M)
    p = tpath(path(g), M)
    c.save(); c.clipPath(circ, doAntiAlias=True)
    glass(c, M, g, col, a, 0.9, col, 1.6)
    c.restore()
    if k < 1:
        front = skia.Path(); front.addCircle(ox, oy, R); front.transform(M)
        c.save(); c.clipPath(p, doAntiAlias=True)
        c.drawPath(front, stroke(rgb('#ffe9b8', 0.9 * (1 - k)), 10, glow=14))
        c.drawPath(front, stroke(rgb('#fff6e0', 0.8 * (1 - k)), 2.2))
        c.restore()


def trace(c, M, g, k, col=GOLD, w=3.0, glow=True):
    """border drawn by a moving light (trim path)."""
    if k <= 0: return
    p = tpath(outline(g), M)
    if glow:
        gp = stroke(rgb('#ffcf7a', 0.55), w * 5, glow=10)
        if k < 1: gp.setPathEffect(skia.TrimPathEffect.Make(0, k))
        c.drawPath(p, gp)
    sp = stroke(col, w)
    if k < 1: sp.setPathEffect(skia.TrimPathEffect.Make(0, k))
    c.drawPath(p, sp)


def label(c, cam, lon, lat, s, f, col, a=1.0, spacing=6, reveal=1.0, dy=0):
    x, y = cam.pt(*ll(lon, lat))
    text(c, s, x, y + dy, f, rgb_a(col, a), spacing=spacing, reveal=reveal, shadow=rgb('#000000', 0.8 * a))


def rgb_a(col, a):
    return skia.Color4f(col.fR, col.fG, col.fB, col.fA * a)


def city(c, cam, name, a, side='r'):
    x, y = cam.pt(*CITIES[name])
    c.drawCircle(x, y, 9, stroke(rgb('#ffe2a8', 0.5 * a), 6, glow=6))
    c.drawCircle(x, y, 4.2, fill(rgb('#fff4dc', a)))
    f = font('CG-SemiBold.ttf', 30)
    text(c, name, x + (16 if side == 'r' else -16), y + 10, f, rgb('#f6ecd9', a), align='l' if side == 'r' else 'r',
         spacing=1, shadow=rgb('#000000', 0.9 * a))


def chip(c, y, s, kind, a):
    """status chip: DOCUMENTED (ivory) vs HYPOTHETICAL (gold, dashed frame)."""
    if a <= 0: return
    f = font('SourceSans3-SemiBold.ttf', 25)
    w = text_width(s, f, 4) + 56
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W / 2 - w / 2, y - 34, w, 50), 25, 25)
    if kind == 'doc':
        c.drawRRect(r, fill(rgb('#0c1218', 0.72 * a))); c.drawRRect(r, stroke(rgb('#dfe6ea', 0.7 * a), 1.6))
        text(c, s, W / 2, y, f, rgb('#e8eef2', a), spacing=4)
    else:
        c.drawRRect(r, fill(rgb('#2a1d08', 0.78 * a))); c.drawRRect(r, stroke(rgb(PAL['gold'], a), 2, dash=[10, 7]))
        text(c, s, W / 2, y, f, rgb('#ffd98f', a), spacing=4)


def year_counter(c, t):
    """Large year numeral with mechanical roll between values."""
    keys = [(4.2, '1772'), (6.15, '1793'), (7.55, '1795'), (9.2, '1791')]
    cur = None
    for i, (ts, yv) in enumerate(keys):
        if t >= ts: cur = i
    if cur is None: return
    a = seg(t, 4.0, 4.5) * (1 - seg(t, 10.9, 11.4))
    ts, yv = keys[cur]
    k = eout(seg(t, ts, ts + 0.45))
    prev = keys[cur - 1][1] if cur > 0 else None
    f = font('Cinzel-Bold.ttf', 132)
    y = 1330
    c.save(); c.clipRect(skia.Rect(0, y - 130, W, y + 30))
    hyp = yv == '1791' and t >= 9.2
    col = rgb('#ffd98f') if hyp else IVORY
    if prev and k < 1:
        text(c, prev, W / 2, y - 140 * k, f, rgb_a(IVORY, a * (1 - k)), spacing=14)
    text(c, yv, W / 2, y + 140 * (1 - k), f, rgb_a(col, a), spacing=14, glow=rgb('#ffcf7a', 0.35 * a) if hyp else None)
    c.restore()
    sub = {'1772': 'FIRST PARTITION', '1793': 'SECOND PARTITION', '1795': 'THIRD PARTITION', '1791': 'IF THE REFORMS HAD HELD'}[yv]
    text(c, sub, W / 2, y + 62, font('SourceSans3-SemiBold.ttf', 30), rgb_a(rgb('#c9d3da') if not hyp else rgb('#ffd98f'), a * k), spacing=9)
    chip(c, y + 138, 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY', 'hyp' if hyp else 'doc', a * k)


O_W, O_E, O_S, O_N = ll(13, 53), ll(36, 54), ll(21, 46.5), ll(30, 58)
LOSSES = [(L['loss72']['pru'], O_W, 4.3, 5.4), (L['loss72']['rus'], O_E, 4.5, 5.7), (L['loss72']['aut'], O_S, 4.7, 5.8),
          (L['gains']['93_pru'], O_W, 6.2, 7.2), (L['gains']['93_rus'], O_E, 6.2, 7.3), (L['gains']['95_pru'], O_W, 7.6, 8.5),
          (L['gains']['95_rus'], O_E, 7.6, 8.6), (L['gains']['95_rus_courland'], O_N, 7.6, 8.6), (L['gains']['95_aut'], O_S, 7.7, 8.6)]


def lost_part(g, o, k, M):
    if k >= 1: return tpath(path(g), M)
    from shapely.geometry import Point
    part = Point(o).buffer(1_400_000 * eout(k, 2), 96).intersection(g)
    p = path_nocache(part); p.transform(M); return p


def scene(c, t, f):
    cam = camera(t); M = cam.matrix()
    c.clear(skia.Color4f(0.02, 0.04, 0.06, 1))
    # relief base (sea-coloured world plane under it so the raster edge never shows)
    c.save(); c.concat(M); c.drawRect(skia.Rect(-6e6, -6e6, 6e6, 6e6), fill(skia.Color4f(0.035, 0.065, 0.095, 1))); c.restore()
    c.save(); c.concat(M); c.translate(X0, Y1); c.scale(RES, -RES)
    c.drawImage(RELIEF, 0, 0, SAMP); c.restore()
    alt = seg(t, 8.9, 9.9)       # alternate timeline blend
    neigh = (0.30 + 0.10 * seg(t, 3.0, 4.0)) * (1 - 0.5 * alt)
    for k in ('hre', 'saxony', 'sweden', 'denmark', 'other', 'venice', 'ragusa'):
        glass(c, M, S73.get(k), PAL['other'], 0.10, 0.25, '#8d98a0', 0.8)
    glass(c, M, S73['ottoman'], PAL['ottoman'], neigh, 0.5, '#9a8b7e', 1)
    glass(c, M, S91['habsburg'], PAL['habsburg'], neigh, 0.5, '#d6b48a', 1)
    glass(c, M, S73['russia'], PAL['russia'], neigh, 0.5, '#a9bf8f', 1)
    glass(c, M, S73['prussia'], PAL['prussia'], neigh, 0.5, '#9ab8d8', 1)
    # the Commonwealth (pre-1772) lit from within
    ca = (0.62 * seg(t, 1.0, 2.6)) * (1 - alt)
    c.save()
    for g, o, a, b in LOSSES:
        k = seg(t, a, b)
        if k > 0: c.clipPath(lost_part(g, o, k, M), skia.ClipOp.kDifference, True)
    glass(c, M, L['plt_pre72'], PAL['plt'], ca)
    glass(c, M, L['courland'], '#c96a52', ca * 0.6)
    c.restore()
    # partitions (documented)
    pk = 1 - alt
    if pk > 0:
        o_w, o_e, o_s = ll(13, 53), ll(36, 54), ll(21, 46.5)
        for g, col, o, a, b in [(L['loss72']['pru'], PAL['prussia'], o_w, 4.3, 5.4), (L['loss72']['rus'], PAL['russia'], o_e, 4.5, 5.7),
                                (L['loss72']['aut'], PAL['habsburg'], o_s, 4.7, 5.8),
                                (L['gains']['93_pru'], PAL['prussia'], o_w, 6.2, 7.2), (L['gains']['93_rus'], PAL['russia'], o_e, 6.2, 7.3),
                                (L['gains']['95_pru'], PAL['prussia'], o_w, 7.6, 8.5), (L['gains']['95_rus'], PAL['russia'], o_e, 7.6, 8.6),
                                (L['gains']['95_rus_courland'], PAL['russia'], ll(30, 58), 7.6, 8.6), (L['gains']['95_aut'], PAL['habsburg'], o_s, 7.7, 8.6)]:
            c.save(); spread(c, M, g, col, seg(t, a, b) * 1.0, o, a=0.80 * pk); c.restore()
    # Commonwealth border traced in light, then ghost after 1795
    gone = seg(t, 8.2, 8.8)
    trace(c, M, L['plt_pre72'], eout(seg(t, 0.0, 2.2), 2) * (1 - seg(t, 4.0, 4.6)), w=3.2)
    if 4.0 < t < 9.2:
        cur = L['plt1773'] if t < 6.2 else L['rump1793'] if t < 7.6 else None
        if cur is not None: trace(c, M, cur, 1.0, w=2.6)
    if gone > 0 and alt < 1:
        c.drawPath(tpath(outline(L['plt_pre72']), M), stroke(rgb('#e9d7b0', 0.55 * gone * (1 - alt)), 1.8, dash=[8, 9]))
    # hypothetical survival: the 1791 Commonwealth re-ignites from Warsaw
    if alt > 0:
        g91 = PLT91
        spread(c, M, g91, '#d4a24a', seg(t, 8.9, 10.2), CITIES['Warsaw'], a=0.62)
        spread(c, M, S91['courland'], '#d4a24a', seg(t, 9.3, 10.4), CITIES['Warsaw'], a=0.35)
        p = tpath(outline(g91), M)
        c.drawPath(p, stroke(rgb('#ffcf7a', 0.5 * alt), 14, glow=12))
        c.drawPath(p, stroke(rgb('#ffe6b0', alt), 2.6, dash=[14, 8]))
    # map labels
    la = seg(t, 2.6, 3.6) * (1 - 0.6 * alt)
    sc = font('CormorantSC-SemiBold.ttf', 34)
    label(c, cam, 16.6, 53.0, 'PRUSSIA', sc, rgb('#cfe0f2'), la, 8)
    label(c, cam, 32.6, 56.6, 'RUSSIAN EMPIRE', sc, rgb('#d8e8c6'), la, 6)
    label(c, cam, 19.5, 48.0, 'HABSBURG MONARCHY', sc, rgb('#f0d7b4'), la * (1 - seg(t, 3.8, 4.2)), 5)
    label(c, cam, 29.0, 46.4, 'OTTOMAN EMPIRE', sc, rgb('#e2d2c4'), la * 0.8 * (1 - seg(t, 3.8, 4.2)), 5)
    label(c, cam, 18.3, 56.4, 'Baltic Sea', font('CG-MediumItalic.ttf', 38), rgb('#7fa6bf'), la, 4)
    pla = seg(t, 3.0, 3.9) * (1 - seg(t, 5.9, 6.3))
    big = font('Cinzel-Bold.ttf', 31)
    label(c, cam, 27.4, 51.3, 'POLISH–LITHUANIAN', big, rgb('#fff1dc'), pla, 7, reveal=seg(t, 3.0, 4.0))
    label(c, cam, 27.4, 51.3, 'COMMONWEALTH', big, rgb('#fff1dc'), pla, 9, reveal=seg(t, 3.15, 4.1), dy=38)
    for nm, side, a0 in [('Warsaw', 'r', 1.2), ('Vilnius', 'r', 2.8), ('Kraków', 'l', 3.0), ('Gdańsk', 'l', 3.1)]:
        city(c, cam, nm, seg(t, a0, a0 + 0.6) * (1 - 0.0 * alt), side)
    # hook titles
    ha = seg(t, 0.15, 0.6) * (1 - seg(t, 3.1, 3.7))
    if ha > 0:
        yb = 360 - 60 * eout(seg(t, 3.1, 3.7))
        text(c, 'WHAT IF', W / 2, yb, font('Cinzel-Bold.ttf', 132), rgb('#ffe0a3', ha), spacing=18, reveal=seg(t, 0.1, 0.9),
             glow=rgb('#ffb347', 0.45 * ha), shadow=rgb('#000000', 0.8))
        text(c, 'POLAND–LITHUANIA', W / 2, yb + 108, font('Cinzel-Bold.ttf', 74), rgb('#fff6e6', ha), spacing=6,
             reveal=seg(t, 0.5, 1.5), shadow=rgb('#000000', 0.8))
        text(c, 'had never been partitioned?', W / 2, yb + 180, font('CG-MediumItalic.ttf', 60), rgb('#e9dcc4', ha), spacing=1,
             reveal=seg(t, 1.0, 2.0), shadow=rgb('#000000', 0.8))
    hz = skia.Paint(); hz.setShader(lin_grad((0, 0), (0, 520), [rgb('#05090d', 0.95), rgb('#05090d', 0.0)]))
    c.drawRect(skia.Rect(0, 0, W, 520), hz)
    bb = skia.Paint(); bb.setShader(lin_grad((0, 1080), (0, 1600), [rgb('#05090d', 0.0), rgb('#05090d', 0.88 * seg(t, 3.4, 4.2))]))
    c.drawRect(skia.Rect(0, 1080, W, H), bb)
    year_counter(c, t)
    # end card
    ea = seg(t, 10.0, 10.6)
    if ea > 0:
        text(c, 'WHAT IF IT HAD SURVIVED?', W / 2, 420, font('Cinzel-Bold.ttf', 64), rgb('#ffe0a3', ea), spacing=6,
             reveal=seg(t, 10.0, 11.0), glow=rgb('#ffb347', 0.35 * ea), shadow=rgb('#000000', 0.8))
        text(c, 'Commonwealth borders of 1791, kept intact', W / 2, 482, font('CG-MediumItalic.ttf', 38), rgb('#e9dcc4', ea),
             reveal=seg(t, 10.3, 11.2), shadow=rgb('#000000', 0.8))
    # light sweep on hook
    if t < 2.4:
        k = seg(t, 0.3, 2.4); x = lerp(-400, W + 400, ease(k))
        sp = skia.Paint(AntiAlias=True)
        sp.setShader(lin_grad((x - 260, 0), (x + 260, 0), [skia.Color4f(1, .85, .6, 0), skia.Color4f(1, .85, .6, .10), skia.Color4f(1, .85, .6, 0)], [0, .5, 1]))
        sp.setBlendMode(skia.BlendMode.kScreen); c.drawRect(skia.Rect(0, 0, W, H), sp)
    # fade in from black
    if t < 0.35: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.35)))


if __name__ == '__main__':
    out = f'{ROOT}/previews/concepts/concept1_cinematic_atlas.mp4'
    frames = None
    if len(sys.argv) > 1:
        frames = [int(float(x) * FPS) for x in sys.argv[1:]]; out = f'{ROOT}/previews/concepts/_test1.mp4'
    render(scene, 11.5, out, Post(grain=0.03, vignette=0.55, bloom=0.55), stills=(1.6, 3.9, 5.6, 7.0, 8.5, 11.0),
           still_dir=f'{ROOT}/previews/concepts', frames=frames)
