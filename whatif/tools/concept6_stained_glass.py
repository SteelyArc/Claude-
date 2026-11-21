"""CONCEPT 6 - Stained Glass.
The map is a backlit lancet window in a dark stone nave: every state is cut into shards of tinted glass held by
lead cames (the real borders are the lead lines). Light streams through as volumetric shafts. Annexations re-glaze
the window shard by shard from the annexing side; when the state is gone the light dies; in the alternate timeline
the window relights with the 1791 Commonwealth glowing in crimson and gold."""
import cv2
from shapely.geometry import MultiPoint, Polygon, box
from shapely.ops import voronoi_diagram, unary_union
from styles_common import *

WX0, WX1, WY0, WY1 = 80, 1000, 250, 1500      # window rect (arch on top)
GLASS = dict(plt='#c0182c', prussia='#2456a8', russia='#2f7d3a', habsburg='#d48a12', ottoman='#7a3d8c', sweden='#3b6f96',
             hre='#8c6a3a', saxony='#8c6a3a', other='#6a5a48', sea='#122a5a', gold='#f2b632')

def window_path():
    p = skia.Path(); cx = (WX0 + WX1) / 2; ay = WY0 + 330
    p.moveTo(WX0, WY1); p.lineTo(WX0, ay)
    p.cubicTo(WX0, WY0 + 140, cx - 160, WY0 + 10, cx, WY0 - 40)
    p.cubicTo(cx + 160, WY0 + 10, WX1, WY0 + 140, WX1, ay); p.lineTo(WX1, WY1); p.close(); return p
WIN = window_path()

BOUNDS = (ll(14.6, 52)[0], ll(24, 44.6)[1], ll(33.6, 52)[0], ll(24, 60.6)[1])
M0 = fit_matrix(BOUNDS, WX0, WY0 - 60, WX1 - WX0, WY1 - WY0 + 60, pad=-0.08)   # overfill: window crops it
inv = skia.Matrix(); M0.invert(inv)
def W2S(x, y): p = M0.mapXY(x, y); return p.x(), p.y()
_a, _b = inv.mapXY(WX0 - 40, WY1 + 40), inv.mapXY(WX1 + 40, WY0 - 80)
FRAME = box(_a.x(), _a.y(), _b.x(), _b.y())

rng = np.random.default_rng(5)
pts = np.c_[rng.uniform(FRAME.bounds[0], FRAME.bounds[2], 260), rng.uniform(FRAME.bounds[1], FRAME.bounds[3], 260)]
CELLS = [g.intersection(FRAME) for g in voronoi_diagram(MultiPoint([tuple(p) for p in pts]), envelope=FRAME).geoms]

def shards(geom, minarea=4e8):
    out = []
    g = geom.intersection(FRAME)
    for cell in CELLS:
        s = cell.intersection(g)
        if not s.is_empty and s.area > minarea: out.append(s.buffer(0))
    return out

LANDG = L['land'].intersection(FRAME)
SEA = shards(FRAME.difference(LANDG))
NB = {k: shards(v.difference(PRE72.buffer(2e3))) for k, v in NEIGH.items()}
PIECE_SH = []
for i, (yr, pw, g, o, rad) in enumerate(ORIG):
    for s in shards(g, 1e8):
        d = Point_d = np.hypot(s.centroid.x - o[0], s.centroid.y - o[1]) / max(rad, 1)
        PIECE_SH.append((yr, pw, s, min(d, 1.0)))
REST = shards(PRE72.difference(unary_union([g for _, _, g in PIECES]).buffer(1e3)), 1e8)
ALT = shards(PLT91, 1e8)

def jitter(hexc, seed, amt=0.10):
    r = np.random.default_rng(seed).uniform(-amt, amt, 3); c = rgb(hexc)
    return np.clip(np.array([c.fR, c.fG, c.fB]) * (1 + r[0]) + r[1:2] * 0.3, 0, 1)

def _tex():
    n = noise_tex(H, W, 7, seed=12, base=3); streak = cv2.GaussianBlur(np.random.default_rng(2).normal(0, 1, (H, W)).astype(np.float32), (0, 0), sigmaX=1.2, sigmaY=14)
    v = np.clip(0.78 + n * 0.10 + streak * 0.35, 0.45, 1.1)
    bub = (np.random.default_rng(4).random((H, W)) > 0.9993).astype(np.float32); bub = cv2.GaussianBlur(bub, (0, 0), 2.0) * 25
    v = np.clip(v + bub * 0.4, 0, 1.4) / 1.4
    return to_image((np.dstack([v, v, v]) * 255).astype(np.uint8))
TEX = _tex()

def _stone():
    n = noise_tex(H, W, 7, seed=40, base=3)
    img = np.array([0.09, 0.085, 0.08], np.float32)[None, None] * (1 + n[..., None] * 0.18)
    for y in range(0, H, 120): img[y:y + 3] *= 0.55                                  # ashlar courses
    for r in range(0, H // 120 + 1):
        for x in range((r % 2) * 110, W, 220): img[r * 120:(r + 1) * 120, x:x + 3] *= 0.6
    return to_image((np.clip(img, 0, 1) * 255).astype(np.uint8))
STONE = _stone()

def light(t):
    """backlight intensity over the beat."""
    return (0.25 + 0.75 * ease(seg(t, 0.4, 2.2))) * (1 - 0.82 * ease(seg(t, 6.4, 7.2))) + 0.82 * ease(seg(t, 7.9, 9.0)) * (t > 7.2)

def draw_shard(c, M, g, col, lv, seed, flash=0.0):
    p = tpath(path(g), M); jc = jitter('#000000', 0) if col is None else col
    k = lv * (0.85 + 0.3 * np.random.default_rng(seed).random())
    c.drawPath(p, fill(skia.Color4f(*(np.clip(jc * k + flash, 0, 1)), 1.0)))
    return p

def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(STONE, 0, 0)
    lv = light(t)
    push = 1 + 0.05 * ease(seg(t, 0, DUR)); M = skia.Matrix(); M.setScaleTranslate(push, push, W / 2 * (1 - push), 880 * (1 - push))
    M = skia.Matrix.Concat(M, M0)
    wp = tpath(WIN, skia.Matrix.Concat(skia.Matrix.Translate(W / 2 * (1 - push), 880 * (1 - push)), skia.Matrix.Scale(push, push)))
    # window recess shadow + frame
    sh = fill(rgb('#000000', 0.8)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)); c.drawPath(wp, sh)
    c.save(); c.clipPath(wp, doAntiAlias=True)
    lead = []
    for i, g in enumerate(SEA): lead.append(draw_shard(c, M, g, jitter(GLASS['sea'], i, 0.15), lv * 0.8, i))
    for nm, sl in NB.items():
        for i, g in enumerate(sl): lead.append(draw_shard(c, M, g, jitter(GLASS[nm], i + 50, 0.12), lv * 0.85, i + 50))
    alt = t >= 7.2
    if not alt:
        for i, g in enumerate(REST): lead.append(draw_shard(c, M, g, jitter(GLASS['plt'], i + 300), lv, i + 300))
        for i, (yr, pw, g, d) in enumerate(PIECE_SH):
            a0, _ = BEAT[yr]; ts = a0 + 0.15 + lag_of(pw) + d * 0.75        # shard re-glazed at ts
            k = seg(t, ts, ts + 0.12)
            col = jitter(GLASS['plt'], i + 400) * (1 - k) + jitter(GLASS[pw], i + 400) * k
            fl = 0.55 * np.exp(-max(0.0, t - ts) * 9) * (t >= ts)
            lead.append(draw_shard(c, M, g, col, lv, i + 400, fl))
    else:
        kk = ease(seg(t, 7.9, 9.2))
        for i, (yr, pw, g, d) in enumerate(PIECE_SH):   # 1772 losses are documented and stay with the powers
            if yr == '1772': lead.append(draw_shard(c, M, g, jitter(GLASS[pw], i + 400), lv * 0.85, i + 400))
        for i, g in enumerate(ALT):
            d = np.hypot(g.centroid.x - CITIES['Warsaw'][0], g.centroid.y - CITIES['Warsaw'][1]) / 7e5
            k = seg(kk, d * 0.6, d * 0.6 + 0.35)
            col = jitter(GLASS['russia'] if i % 3 else GLASS['habsburg'], i) * 0.0 + jitter(GLASS['plt'], i + 700) * (0.25 + 0.75 * k) + jitter(GLASS['gold'], i) * 0.35 * k * (i % 4 == 0)
            lead.append(draw_shard(c, M, g, col, lv, i + 700, 0.4 * np.exp(-max(0, kk - d * 0.6) * 12) * (kk > d * 0.6)))
    # glass texture
    c.drawImage(TEX, 0, 0, SAMP, skia.Paint(BlendMode=skia.BlendMode.kMultiply))
    # inner glow (backlight hot spot)
    gp = skia.Paint(Shader=rad_grad(W / 2, 760, 900, [rgb('#fff3d0', 0.30 * lv), rgb('#fff3d0', 0.0)]), BlendMode=skia.BlendMode.kPlus)
    c.drawRect(skia.Rect.MakeWH(W, H), gp)
    # lead cames
    for p in lead:
        c.drawPath(p, stroke(rgb('#141416'), 7.5)); c.drawPath(p, stroke(rgb('#5a5a60', 0.5), 1.4))
    # the political borders as heavier lead
    for g in [*NEIGH.values(), PLT91 if alt else PRE72]:
        c.drawPath(tpath(path(g), M), stroke(rgb('#0c0c0e'), 12))
    if alt:   # hypothetical: gilded dashed came
        c.drawPath(tpath(path(PLT91), M), stroke(rgb('#f6cf6a', 0.9 * seg(t, 8.6, 9.4)), 3.2, dash=[16, 10]))
    c.restore()
    # stone frame / mullion moulding
    c.drawPath(wp, stroke(rgb('#2a2622'), 26)); c.drawPath(wp, stroke(rgb('#4a443c', 0.8), 4))
    # shafts of light falling into the nave
    if lv > 0.05:
        for i, (x, w_, a) in enumerate(((330, 160, 0.10), (560, 220, 0.13), (780, 140, 0.08))):
            p = skia.Path(); p.moveTo(x, 700); p.lineTo(x + w_, 700); p.lineTo(x + w_ + 420, H + 100); p.lineTo(x + 160, H + 100); p.close()
            q = skia.Paint(Shader=lin_grad((x, 700), (x + 260, H), [rgb('#ffe9b8', a * lv * (0.85 + 0.15 * np.sin(t * 1.3 + i))), rgb('#ffe9b8', 0.0)]),
                           BlendMode=skia.BlendMode.kPlus, AntiAlias=True)
            q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40)); c.drawPath(p, q)
    # dust motes in the shafts
    r = np.random.default_rng(9); P = r.random((70, 3))
    for x, y, s in P:
        yy = (y * H + t * 30 * (0.5 + s)) % H; xx = 300 + x * 700 + np.sin(t + s * 9) * 12
        c.drawCircle(xx, yy, 1.2 + s * 1.8, fill(rgb('#fff2cc', 0.35 * lv * s)))
    # text
    shadow = rgb('#000000', 0.9)
    if t < 2.3:
        a = seg(t, 0.1, 0.5) * (1 - seg(t, 1.9, 2.3))
        bg = fill(rgb('#000000', 0.55 * a)); bg.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60)); c.drawRect(skia.Rect.MakeXYWH(60, 620, 960, 440), bg)
        text(c, 'WHAT IF', W / 2, 780, font('Cinzel-Bold.ttf', 132), rgb('#ffe3a0', a), spacing=12, reveal=seg(t, 0.2, 1.0), glow=rgb('#ffb030', 0.6 * a), shadow=shadow)
        text(c, 'POLAND–LITHUANIA', W / 2, 880, font('Cinzel-Bold.ttf', 70), rgb('#fff4dc', a), spacing=5, reveal=seg(t, 0.5, 1.3), shadow=shadow)
        text(c, 'had never been partitioned?', W / 2, 960, font('CG-MediumItalic.ttf', 60), rgb('#f2e2c4', a), reveal=seg(t, 0.8, 1.6), shadow=shadow)
    yr = year_at(t)
    if yr and t < 7.2:
        a = seg(t, 2.0, 2.4) * (1 - seg(t, 6.9, 7.2))
        text(c, yr, W / 2, 1650, font('Cinzel-Bold.ttf', 120), rgb('#f6d58a', a), spacing=10, glow=rgb('#ffb030', 0.45 * a), shadow=shadow)
        text(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1712, font('Cinzel-Bold.ttf', 32), rgb('#e8dcc4', a), spacing=8)
    if 6.9 < t < 8.5:
        a = seg(t, 7.0, 7.4) * (1 - seg(t, 8.1, 8.5))
        text(c, 'But what if the reforms', W / 2, 860, font('CG-MediumItalic.ttf', 72), rgb('#f2e2c4', a), reveal=seg(t, 7.0, 7.6), shadow=shadow)
        text(c, 'of 1791 had survived?', W / 2, 950, font('CG-MediumItalic.ttf', 72), rgb('#f2e2c4', a), reveal=seg(t, 7.2, 7.8), shadow=shadow)
    if t > 9.0:
        a = seg(t, 9.0, 9.5)
        text(c, 'STILL ON THE MAP', W / 2, 1650, font('Cinzel-Bold.ttf', 76), rgb('#f6d58a', a), spacing=8, reveal=seg(t, 9.0, 9.6), glow=rgb('#ffb030', 0.5 * a), shadow=shadow)
        text(c, 'the Commonwealth in its 1791 borders', W / 2, 1720, font('CG-MediumItalic.ttf', 44), rgb('#e8dcc4', a), shadow=shadow)
    # status chip
    hyp = t >= 7.9; a = seg(t, 2.0, 2.4) * (1 - seg(t, 7.3, 7.7)) if not hyp else seg(t, 7.9, 8.3)
    if a > 0:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fnt = font('SourceSans3-SemiBold.ttf', 30); w = text_width(s, fnt, 4) + 48
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(70, 120, w, 54), 27, 27)
        c.drawRRect(rr, fill(rgb('#000000', 0.6 * a)))
        c.drawRRect(rr, stroke(rgb('#f2b632' if hyp else '#e8dcc4', a), 2, dash=[8, 5] if hyp else None))
        text(c, s, 70 + w / 2, 157, fnt, rgb('#f6d58a' if hyp else '#e8dcc4', a), spacing=4)


POST = Post(grain=0.025, vignette=0.55, bloom=0.75, halation=0.4, ca=0.0018, shoulder=0.2, seed=61)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [0.9, 2.8, 4.2, 6.0, 7.5, 9.9], POST, f'{ROOT}/render/c6t'); sheet(fs, f'{ROOT}/render/c6_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept6_stained_glass.mp4', POST, stills=(0.9, 2.8, 4.2, 6.0, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=8, workers=3, scene_mod='concept6_stained_glass')
