"""CONCEPT 16 - Silent Newsreel.
The story as a restored 1920s silent-film newsreel: black-and-white (warm silver toning), 4:3 projected frame
inside the vertical canvas with soft gate edges, film grain, dust, scratches, gate weave and exposure flicker.
Art Deco intertitle cards carry the words between shots; the map is an animated period-style 'map shot' with
iris transitions. Annexed land is shaded in by animated hatch patterns (one per power, with a legend), so the
story reads without colour. The alternate timeline is introduced by its own intertitle marked HYPOTHETICAL."""
import cv2
from styles_common import *

FX, FY, FW, FH = 16, 560, 1048, 786          # projected 4:3 frame on the vertical canvas
BOUNDS = (ll(14.0, 52)[0], ll(24, 46.6)[1], ll(34.6, 52)[0], ll(24, 58.4)[1])
M0 = fit_matrix(BOUNDS, FX, FY, FW, FH, pad=-0.12)
DECO = 'Limelight-Regular.ttf'
PAT = dict(prussia=('lines', 45), russia=('lines', -45), habsburg=('dots', 0))
# shot list: intertitles between the map shots (map times keep the shared beat)
CARDS = [(0.0, 1.7, ['WHAT IF', 'Poland–Lithuania', 'had never been partitioned?']),
         (6.75, 8.0, ['BUT WHAT IF', 'the reforms of 1791', 'had survived?'])]


def card_at(t):
    for a, b, lines in CARDS:
        if a <= t < b: return a, b, lines
    return None


rng = np.random.default_rng(211)
GR = [cv2.GaussianBlur(rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.8) for _ in range(8)]


def deco_frame(c, x, y, w, h, a):
    for inset, wd in ((0, 4), (16, 1.5), (26, 1.0)):
        c.drawRect(skia.Rect.MakeXYWH(x + inset, y + inset, w - 2 * inset, h - 2 * inset), stroke(rgb('#e8e0cc', a), wd))
    for sx in (0, 1):
        for sy in (0, 1):
            cx, cy = x + (w if sx else 0), y + (h if sy else 0); dx, dy = (-1 if sx else 1), (-1 if sy else 1)
            for r_ in (40, 60, 80):
                p = skia.Path(); p.addArc(skia.Rect.MakeXYWH(cx - r_, cy - r_, 2 * r_, 2 * r_), 0 if (sx == 0 and sy == 0) else 90 if (sx and not sy) else 180 if (sx and sy) else 270, 90)
                c.drawPath(p, stroke(rgb('#e8e0cc', a * 0.8), 1.4))
    for i in range(7):   # sunburst fan at top
        th = np.radians(200 + i * 20); c.drawLine(x + w / 2, y + 60, x + w / 2 + np.cos(th) * 110, y + 60 + np.sin(th) * 50, stroke(rgb('#e8e0cc', a * 0.8), 1.4))


def patterned(c, p, kind, ang, k, a=1.0):
    if k <= 0: return
    c.save(); c.clipPath(p, doAntiAlias=True)
    b = p.getBounds(); c.translate(b.centerX(), b.centerY()); c.rotate(ang); R = max(b.width(), b.height())
    if kind == 'lines':
        hp = skia.Path()
        for y in np.arange(-R, R, 11): hp.moveTo(-R, y); hp.lineTo(R, y)
        c.drawPath(hp, stroke(rgb('#1a1a1a', 0.85 * a), 3.2))
    else:
        for y in np.arange(-R, R, 16):
            for x in np.arange(-R + (y // 16 % 2) * 8, R, 16): c.drawCircle(x, y, 3.6, fill(rgb('#1a1a1a', 0.85 * a)))
    c.restore()


def map_shot(c, t):
    c.drawRect(skia.Rect.MakeXYWH(FX, FY, FW, FH), fill(rgb('#9a9a96')))
    land = tpath(path(L['land']), M0)
    c.drawPath(land, fill(rgb('#e6e3da'))); c.drawPath(land, stroke(rgb('#2a2a2a'), 2.0))
    for nm in ('prussia', 'russia', 'habsburg', 'ottoman', 'sweden'):
        c.drawPath(tpath(path(NEIGH[nm]), M0), stroke(rgb('#2a2a2a'), 1.6))
    alt = t >= 8.0
    if not alt:
        pre = tpath(path(PRE72), M0); a = 1 - seg(t, 6.2, 6.7)
        c.drawPath(pre, fill(rgb('#ffffff', 0.9 * a))); c.drawPath(pre, stroke(rgb('#0a0a0a', a), 4.5))
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            k = piece_k(yr, t, lag_of(pw))
            if k <= 0: continue
            p = tpath(path(g), M0); ox, oy = M0.mapXY(*o).x(), M0.mapXY(*o).y()
            c.save(); c.clipPath(rough_circle(ox, oy, rad * abs(M0.getScaleX()) * 1.3 * k + 1, i, 0.02), doAntiAlias=True)
            c.drawPath(p, fill(rgb('#d4d0c6'))); patterned(c, p, *PAT[pw], 1.0)
            c.restore(); c.drawPath(p, stroke(rgb('#0a0a0a'), 2.2))
    else:
        for i, (yr, pw, g, o, rad) in enumerate(ORIG):
            if yr == '1772':
                p = tpath(path(g), M0); c.drawPath(p, fill(rgb('#d4d0c6'))); patterned(c, p, *PAT[pw], 1.0); c.drawPath(p, stroke(rgb('#0a0a0a'), 2.2))
        p = tpath(path(PLT91), M0); k = ease(seg(t, 8.1, 9.0))
        wx, wy = M0.mapXY(*CITIES['Warsaw']).x(), M0.mapXY(*CITIES['Warsaw']).y()
        c.save(); c.clipPath(rough_circle(wx, wy, 900 * k, 3, 0.02), doAntiAlias=True)
        c.drawPath(p, fill(rgb('#ffffff', 0.95))); c.restore()
        c.drawPath(p, stroke(rgb('#0a0a0a', k), 4.5, dash=[18, 10]))
    def at(lon, lat): q = M0.mapXY(*ll(lon, lat)); return q.x(), q.y()
    for nm, lon, lat in (('PRUSSIA', 16.0, 53.4), ('RUSSIA', 31.0, 55.4), ('AUSTRIA', 21.4, 48.3)):
        text(c, nm, *at(lon, lat), font(DECO, 30), rgb('#111111'), spacing=4)
    na = (1 - seg(t, 5.5, 5.9)) if t < 8 else seg(t, 9.0, 9.4)
    text(c, 'POLAND–LITHUANIA', *at(24.2, 52.3), font(DECO, 34), rgb('#111111', na), spacing=3)
    # legend + year plate inside the shot
    lx, ly = FX + FW - 330, FY + FH - 150
    c.drawRect(skia.Rect.MakeXYWH(lx, ly, 300, 120), fill(rgb('#efece4', 0.92))); c.drawRect(skia.Rect.MakeXYWH(lx, ly, 300, 120), stroke(rgb('#111111'), 2))
    for j, (pw, nm) in enumerate((('prussia', 'Prussia'), ('russia', 'Russia'), ('habsburg', 'Austria'))):
        r = skia.Path(); r.addRect(skia.Rect.MakeXYWH(lx + 16, ly + 12 + j * 34, 44, 26)); c.drawPath(r, fill(rgb('#d4d0c6'))); patterned(c, r, *PAT[pw], 1.0); c.drawPath(r, stroke(rgb('#111111'), 1.5))
        text(c, nm, lx + 76, ly + 33 + j * 34, font('EBG-SemiBold.ttf', 26), rgb('#111111'), align='l')


def intertitle(c, lines, a):
    c.drawRect(skia.Rect.MakeXYWH(FX, FY, FW, FH), fill(rgb('#0c0c0c')))
    deco_frame(c, FX + 40, FY + 40, FW - 80, FH - 80, a)
    y = FY + FH / 2 - 70
    text(c, lines[0], W / 2, y, font(DECO, 104), rgb('#efe8d6', a), spacing=8); y += 110
    text(c, lines[1], W / 2, y, font('EBG-Italic.ttf', 58), rgb('#efe8d6', a)); y += 70
    text(c, lines[2], W / 2, y, font('EBG-Italic.ttf', 58), rgb('#efe8d6', a))


def scene(c, t, f):
    POST_STATE['dof'] = 0.0
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#060606')))
    # gate weave + exposure flicker
    r = np.random.default_rng(f); wx, wy = r.normal(0, 1.4), r.normal(0, 1.8)
    c.save(); c.translate(wx, wy)
    cd = card_at(t)
    if cd:
        a0, b0, lines = cd; intertitle(c, lines, seg(t, a0, a0 + 0.25) * (1 - seg(t, b0 - 0.2, b0)))
    else:
        map_shot(c, t)
        # iris in/out around shot changes
        for a0, b0 in ((1.7, 2.2),):
            if a0 <= t < b0:
                k = ease(seg(t, a0, b0)); ir = skia.Path(); ir.addCircle(W / 2, FY + FH / 2, 30 + 700 * k)
                c.save(); c.clipPath(ir, skia.ClipOp.kDifference, True); c.drawRect(skia.Rect.MakeXYWH(FX, FY, FW, FH), fill(rgb('#000000'))); c.restore()
        if 6.4 < t < 6.75:
            k = ease(seg(t, 6.4, 6.75)); ir = skia.Path(); ir.addCircle(W / 2, FY + FH / 2, 730 * (1 - k) + 1)
            c.save(); c.clipPath(ir, skia.ClipOp.kDifference, True); c.drawRect(skia.Rect.MakeXYWH(FX, FY, FW, FH), fill(rgb('#000000'))); c.restore()
    c.restore()
    # gate: soft rounded projection edge
    gate = skia.Path(); gate.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(FX, FY, FW, FH), 26, 26))
    c.save(); c.clipPath(gate, skia.ClipOp.kDifference, True); c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#060606'))); c.restore()
    e = stroke(rgb('#060606'), 40); e.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18)); c.drawPath(gate, e)
    # dust and scratches
    for _ in range(r.integers(2, 7)):
        x, y = r.uniform(FX, FX + FW), r.uniform(FY, FY + FH); s_ = r.uniform(1.5, 5)
        c.drawCircle(x, y, s_, fill(rgb('#000000' if r.random() < 0.6 else '#ffffff', r.uniform(0.4, 0.9))))
    if r.random() < 0.5:
        x = r.uniform(FX + 50, FX + FW - 50); c.drawLine(x, FY, x + r.normal(0, 6), FY + FH, stroke(rgb('#ffffff', r.uniform(0.15, 0.4)), r.uniform(0.8, 2)))
    # captions outside the projected frame (modern, for the phone): status + subtitles
    hyp = t >= 8.0
    sa = 1.0 if t > 1.8 else 0.0
    if sa:
        s = 'HYPOTHETICAL' if hyp else 'DOCUMENTED HISTORY'; fn = font('SourceSans3-SemiBold.ttf', 30); w = text_width(s, fn, 5) + 48
        rr = skia.Rect.MakeXYWH(W / 2 - w / 2, 170, w, 56)
        c.drawRect(rr, stroke(rgb('#efe8d6'), 2, dash=[8, 5] if hyp else None)); text(c, s, W / 2, 208, fn, rgb('#efe8d6'), spacing=5)
    yr = year_at(t)
    if yr and not card_at(t) and t > 1.9:
        text(c, yr, W / 2, FY - 150, font(DECO, 150), rgb('#efe8d6'), spacing=10)
    sub = None
    if 2.0 < t < 6.75: sub = YEAR_LABEL.get(year_at(t), 'Before the partitions, c. 1770').title() if year_at(t) != '1770' else 'Before the partitions, c. 1770'
    if t > 9.0: sub = 'Still on the map – the 1791 borders'
    if sub: text(c, sub, W / 2, FY + FH + 120, font('EBG-Italic.ttf', 64), rgb('#efe8d6'))
    # flicker
    fl = 0.07 * r.random()
    c.drawRect(skia.Rect.MakeWH(W, H), fill(rgb('#000000', fl)))



class SilverPost(Post):
    def __call__(self, img, f):
        out = super().__call__(img, f).astype(np.float32) / 255
        y = out @ np.array([0.30, 0.59, 0.11], np.float32)
        y = np.clip((y - 0.04) * 1.12, 0, 1) ** 1.05
        tone = np.stack([y * 1.0, y * 0.96, y * 0.88], -1)   # warm silver toning
        return (np.clip(tone, 0, 1) * 255 + 0.5).astype(np.uint8)


POST = SilverPost(grain=0.07, vignette=0.55, bloom=0.2, ca=0.0, shoulder=0.0, seed=221)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fs = test_frames(scene, [0.9, 2.9, 4.0, 5.3, 7.3, 9.9], POST, f'{ROOT}/render/c16t'); sheet(fs, f'{ROOT}/render/c16_sheet.jpg', 3, 360)
    else:   # 18 fps-feel: no motion blur
        render(scene, DUR, f'{ROOT}/previews/concepts/concept16_silent_film.mp4', POST, stills=(0.9, 2.9, 4.0, 5.3, 7.3, 9.9),
               still_dir=f'{ROOT}/previews/concepts', mb=1, workers=2, scene_mod='concept16_silent_film')
