"""CONCEPT 14 - Neon.
A night-time neon sign on a rain-damp brick wall: every border is a hand-bent glass tube with a hot core, coloured
glow and light spill onto the bricks, and buzzes on with real flicker. Annexed sections short out and die in red,
then relight in the annexing power's colour; in 1795 the whole red tube sparks out. The title signs use a neon
display face; the alternate timeline powers the 1791 outline back on in red with a segmented gold 'hypothetical' tube."""
import cv2
from styles_common import *

BOUNDS = (ll(14.4, 52)[0], ll(24, 46.2)[1], ll(34.0, 52)[0], ll(24, 58.8)[1])
M0 = fit_matrix(BOUNDS, 50, 360, 980, 1150, pad=0.02)
NEON = dict(plt='#ff2d55', prussia='#3d8bff', russia='#28f5a0', habsburg='#ffb020', gold='#ffd54a', white='#f4f4ff')
DISP = 'Monoton-Regular.ttf'


def _wall():
    rng = np.random.default_rng(181); n = noise_tex(H, W, 6, seed=182, base=3)
    img = np.zeros((H, W, 3), np.float32); bh, bw = 54, 150
    for r in range(H // bh + 1):
        off = (r % 2) * bw // 2
        for cidx in range(-1, W // bw + 2):
            x0 = cidx * bw + off; y0 = r * bh; tone = rng.uniform(0.75, 1.15)
            img[y0 + 4:y0 + bh - 2, max(0, x0 + 4):max(0, x0 + bw - 2)] = np.array([0.085, 0.060, 0.058]) * tone
    img += np.array([0.03, 0.03, 0.035]) * (img.sum(-1, keepdims=True) == 0)
    img *= (1 + n[..., None] * 0.25)
    wet = np.clip(noise_tex(H, W, 5, seed=183, base=2), 0, None)[..., None] * 0.02
    return to_image((np.clip(img + wet, 0, 1) * 255).astype(np.uint8))
WALL = _wall()


def flick(t, t_on, seed, dur=0.5):
    """neon ignition: stutters, then steady (with a faint hum)."""
    if t < t_on: return 0.0
    if t > t_on + dur: return 0.94 + 0.06 * np.sin(t * 91 + seed)
    r = np.random.default_rng(int((t - t_on) * 30) * 7 + seed).random()
    return float(r > 0.45) * (0.4 + 0.6 * (t - t_on) / dur)


def die(t, t_off, seed, dur=0.35):
    if t < t_off: return 1.0
    if t > t_off + dur: return 0.0
    r = np.random.default_rng(int((t - t_off) * 30) * 13 + seed).random()
    return float(r > 0.35 + (t - t_off) / dur * 0.6)


def tube(c, p, col, b, w=4.0, dash=None):
    if b <= 0.01: return
    cc = rgb(col)
    for wd, blur, a in ((w * 7, 34, 0.30), (w * 3, 10, 0.55), (w * 1.6, 3, 0.85)):
        s = stroke(skia.Color4f(cc.fR, cc.fG, cc.fB, a * b), wd, dash=dash); s.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        s.setBlendMode(skia.BlendMode.kPlus); c.drawPath(p, s)
    core = stroke(skia.Color4f(min(1, cc.fR * 0.4 + 0.65), min(1, cc.fG * 0.4 + 0.65), min(1, cc.fB * 0.4 + 0.65), b), w * 0.8, dash=dash)
    c.drawPath(p, core)


def dead_tube(c, p, w=4.0, dash=None):
    c.drawPath(p, stroke(rgb('#3a3036', 0.9), w * 1.2, dash=dash)); c.drawPath(p, stroke(rgb('#7a6a74', 0.35), 1.0, dash=dash))


def spill(c, p, col, b):
    if b <= 0.01: return
    q = fill(rgb(col, 0.10 * b)); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40)); q.setBlendMode(skia.BlendMode.kPlus); c.drawPath(p, q)


def neon_text(c, s, x, y, size, col, b, f=DISP, sp=4):
    if b <= 0.01: return
    fn = font(f, size); cc = rgb(col)
    for blur, a in ((26, 0.55), (8, 0.8)):
        q = skia.Paint(Color4f=skia.Color4f(cc.fR, cc.fG, cc.fB, a * b), AntiAlias=True); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur)); q.setBlendMode(skia.BlendMode.kPlus)
        w = text_width(s, fn, sp); cx = x - w / 2
        for ch in s: c.drawString(ch, cx, y, fn, q); cx += fn.measureText(ch) + sp
    text(c, s, x, y, fn, skia.Color4f(min(1, cc.fR * 0.35 + 0.7), min(1, cc.fG * 0.35 + 0.7), min(1, cc.fB * 0.35 + 0.7), b), spacing=sp)


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawImage(WALL, 0, 0)
    M = M0
    land = tpath(path(L['land']), M)
    # coast as a dim white tube, neighbours in their colours
    tube(c, land, NEON['white'], 0.22 * flick(t, 1.0, 3, 0.6), 2.0)
    c.saveLayer(None, None)
    for i, nm in enumerate(('prussia', 'russia', 'habsburg')):
        p = tpath(path(NEIGH[nm]), M); b = flick(t, 1.6 + 0.12 * i, 10 + i)
        spill(c, p, NEON[nm], b * 0.6); tube(c, p, NEON[nm], b * 0.75, 3.2)
    cx_, cy_ = M.mapXY(*ll(24, 52)).x(), M.mapXY(*ll(24, 52)).y()
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=rad_grad(cx_, cy_, 820, [rgb('#000000', 1.0), rgb('#000000', 1.0), rgb('#000000', 0.0)], [0, 0.62, 1]), BlendMode=skia.BlendMode.kDstIn))
    c.restore()
    alt = t >= 7.4
    pre = tpath(path(PRE72), M)
    if not alt:
        b = flick(t, 0.5, 1, 0.8) * die(t, 6.3, 5, 0.45)
        if b < 0.05: dead_tube(c, pre, 5)
        spill(c, pre, NEON['plt'], b); tube(c, pre, NEON['plt'], b, 5)
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            a0 = BEAT[yr][0] + 0.15 + lag_of(pw)
            if t < a0: continue
            p = tpath(path(g), M)
            # the red section shorts out (sparks), then the power's tube buzzes on around it
            k = flick(t, a0 + 0.35, 40 + i, 0.4)
            c.save(); c.clipPath(p, doAntiAlias=True); c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#000000', 0.55 * min(1, (t - a0) * 3)))); c.restore()
            spill(c, p, NEON[pw], k); tube(c, p, NEON[pw], k, 3.4)
            if t < a0 + 0.35:   # sparks
                rs = np.random.default_rng(int(t * 30) + i)
                px, py = M.mapXY(g.centroid.x, g.centroid.y).x(), M.mapXY(g.centroid.x, g.centroid.y).y()
                for _ in range(10):
                    ang = rs.uniform(0, 6.28); L_ = rs.uniform(10, 60)
                    c.drawLine(px, py, px + np.cos(ang) * L_, py + np.sin(ang) * L_, stroke(rgb('#fff2c0', 0.9), 2))
    else:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            b = 1.0 if yr == '1772' else die(t, 7.9, 60 + i, 0.4)
            p = tpath(path(g), M)
            if b > 0: spill(c, p, NEON[pw], b); tube(c, p, NEON[pw], b, 3.4)
        p = tpath(path(PLT91), M); b = flick(t, 8.1, 7, 0.7)
        if b < 0.05: dead_tube(c, p, 5)
        spill(c, p, NEON['plt'], b * 1.3); tube(c, p, NEON['plt'], b, 5)
        g2 = skia.Path(p); g2.offset(0, 0)
        tube(c, g2, NEON['gold'], flick(t, 8.9, 9, 0.5) * 0.9, 2.2, dash=[18, 14])
    def at(lon, lat): q = M.mapXY(*ll(lon, lat)); return q.x(), q.y()
    for nm, lon, lat, col, t_on in (('PRUSSIA', 15.4, 53.5, 'prussia', 1.8), ('RUSSIA', 31.0, 55.5, 'russia', 1.9), ('AUSTRIA', 19.4, 47.6, 'habsburg', 2.0)):
        neon_text(c, nm, *at(lon, lat), 34, NEON[col], flick(t, t_on, len(nm)), 'SourceSans3-SemiBold.ttf', 6)
    nb = flick(t, 2.2, 77) * die(t, 6.2, 78) if not alt else flick(t, 9.2, 79)
    neon_text(c, 'POLAND–LITHUANIA', *at(23.8, 52.4), 40, NEON['plt'], nb, 'SourceSans3-SemiBold.ttf', 5)
    # signs
    if t < 2.4:
        b = flick(t, 0.05, 101, 0.6) * (1 - seg(t, 2.0, 2.4))
        neon_text(c, 'WHAT IF', W / 2, 1620, 130, NEON['plt'], b, DISP, 10)
        neon_text(c, 'POLAND–LITHUANIA HAD NEVER', W / 2, 1715, 40, NEON['white'], flick(t, 0.6, 102, 0.4) * (1 - seg(t, 2.0, 2.4)), 'SourceSans3-SemiBold.ttf', 6)
        neon_text(c, 'BEEN PARTITIONED?', W / 2, 1780, 40, NEON['gold'], flick(t, 0.9, 103, 0.4) * (1 - seg(t, 2.0, 2.4)), 'SourceSans3-SemiBold.ttf', 6)
    yr = year_at(t)
    if yr and 2.0 < t < 6.9:
        b0 = {'1770': 2.0, '1772': 3.2, '1793': 4.4, '1795': 5.6}[yr]
        b = flick(t, b0, int(yr), 0.35) * (1 - seg(t, 6.5, 6.85))
        neon_text(c, yr, W / 2, 1680, 150, NEON['white'], b, DISP, 8)
        neon_text(c, YEAR_LABEL.get(yr, 'BEFORE THE PARTITIONS'), W / 2, 1770, 38, NEON['plt'], b, 'SourceSans3-SemiBold.ttf', 8)
    if 6.9 < t < 8.4:
        b = flick(t, 6.95, 201, 0.4) * (1 - seg(t, 8.1, 8.4))
        neon_text(c, 'BUT WHAT IF', W / 2, 1640, 96, NEON['gold'], b, DISP, 6)
        neon_text(c, 'THE REFORMS OF 1791 HAD SURVIVED?', W / 2, 1730, 38, NEON['white'], flick(t, 7.2, 202, 0.4) * (1 - seg(t, 8.1, 8.4)), 'SourceSans3-SemiBold.ttf', 4)
    if t > 9.0:
        neon_text(c, 'STILL ON THE MAP', W / 2, 1660, 74, NEON['plt'], flick(t, 9.0, 301, 0.5), DISP, 4)
        neon_text(c, 'THE COMMONWEALTH · 1791 BORDERS', W / 2, 1750, 34, NEON['gold'], flick(t, 9.4, 302, 0.4), 'SourceSans3-SemiBold.ttf', 5)
    hyp = t >= 7.9
    b = (flick(t, 2.0, 401, 0.3) * die(t, 7.3, 402, 0.2)) if not hyp else flick(t, 7.95, 403, 0.4)
    neon_text(c, 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY', 90 + (150 if hyp else 230), 210, 32, NEON['gold'] if hyp else NEON['white'], b, 'SourceSans3-SemiBold.ttf', 6)


POST = Post(grain=0.03, vignette=0.55, bloom=0.85, halation=0.25, ca=0.0022, shoulder=0.25, seed=191)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [1.5, 2.9, 3.6, 5.2, 7.6, 9.9], POST, f'{ROOT}/render/c14t'); sheet(fs, f'{ROOT}/render/c14_sheet.jpg', 3, 360)
    else:
        render(scene, DUR, f'{ROOT}/previews/concepts/concept14_neon.mp4', POST, stills=(1.5, 2.9, 3.6, 5.2, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=4, workers=2, scene_mod='concept14_neon')
