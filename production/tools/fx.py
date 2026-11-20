"""Cinematic helpers: archival images, 2.5D parallax portraits, medallions, document animation, wipes."""
import os, math, functools
import numpy as np
import skia
from atlas import W, H, C, PAL, font, draw_text, text_width, ease, parchment, ROOT

SAMP = skia.SamplingOptions(skia.CubicResampler.Mitchell())

@functools.lru_cache(None)
def load_image(path):
    return skia.Image.open(path)

def clamp01(x): return min(max(x, 0.0), 1.0)
def seg(t, a, b): return clamp01((t - a) / (b - a)) if b > a else float(t >= a)
def eseg(t, a, b): return ease(seg(t, a, b))

# ------------------------------------------------------------------ backgrounds
def dark_desk(cv, t=0.0):
    """Warm, dim parchment 'desk' used behind documents."""
    cv.drawColor(C('#2B2118'))
    p = skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=0.0)
    img = parchment(seed=11)
    cv.drawImage(img, -120, -120, skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(Alphaf=0.22))
    sh = skia.GradientShader.MakeRadial(skia.Point(W * 0.5, H * 0.42), H * 0.75,
                                        [skia.Color4f(0.55, 0.38, 0.2, 0.25), skia.Color4f(0, 0, 0, 0.75)], [0, 1])
    cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))

# ------------------------------------------------------------------ document animation
def document(cv, img, t, focus=(0.5, 0.5), zoom0=1.0, zoom1=1.0, tilt0=0.32, settle=(0.0, 0.45), sweep=(0.15, 0.6), width_frac=0.92, desat=0.0, bright=1.0, cy_frac=0.53):
    """Paper document lifting from a perspective tilt to flat, then a slow push towards `focus`.
    t: 0..1 progress of the shot."""
    iw, ih = img.width(), img.height()
    k = 1 - eseg(t, *settle); tilt = tilt0 * k
    z = zoom0 + (zoom1 - zoom0) * ease(t)
    pw = W * width_frac * z; ph = pw * ih / iw
    fx, fy = focus
    cx = W / 2 - (fx - 0.5) * pw * ease(t) * (1 - 1 / max(z, 1e-3)) * 1.0
    cy = H * cy_frac - (fy - 0.5) * ph * ease(t) * (1 - 1 / max(z, 1e-3)) * 1.0
    # trapezoid: top edge recedes (rotation about the horizontal axis)
    shrink = 0.22 * tilt; lift = 140 * tilt
    tl = (cx - pw / 2 * (1 - shrink), cy - ph / 2 + ph * 0.18 * tilt + lift); tr = (cx + pw / 2 * (1 - shrink), tl[1])
    bl = (cx - pw / 2, cy + ph / 2 + lift * 0.4); br = (cx + pw / 2, bl[1])
    m = skia.Matrix(); m.setPolyToPoly([skia.Point(0, 0), skia.Point(iw, 0), skia.Point(iw, ih), skia.Point(0, ih)],
                                       [skia.Point(*tl), skia.Point(*tr), skia.Point(*br), skia.Point(*bl)])
    # soft drop shadow
    shadow = skia.Path(); shadow.moveTo(*tl); shadow.lineTo(*tr); shadow.lineTo(*br); shadow.lineTo(*bl); shadow.close()
    cv.save(); cv.translate(0, 26 + 30 * tilt)
    cv.drawPath(shadow, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.55),
                                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
    cv.restore()
    cv.save(); cv.concat(m)
    cv.drawImage(img, 0, 0, SAMP, skia.Paint(AntiAlias=True, ColorFilter=_cf(desat, bright)))
    # light sweep across the paper
    s = seg(t, *sweep)
    if 0 < s < 1:
        x = -0.4 * iw + 1.8 * iw * s
        sh = skia.GradientShader.MakeLinear([skia.Point(x - iw * 0.25, 0), skia.Point(x + iw * 0.25, ih * 0.4)],
                                            [skia.Color4f(1, 0.95, 0.8, 0), skia.Color4f(1, 0.95, 0.8, 0.28), skia.Color4f(1, 0.95, 0.8, 0)], [0, 0.5, 1])
        cv.drawRect(skia.Rect(0, 0, iw, ih), skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kScreen))
    # darker edges / age
    sh2 = skia.GradientShader.MakeRadial(skia.Point(iw / 2, ih / 2), max(iw, ih) * 0.75,
                                         [skia.Color4f(0, 0, 0, 0), skia.Color4f(0.2, 0.12, 0.05, 0.35)], [0.6, 1])
    cv.drawRect(skia.Rect(0, 0, iw, ih), skia.Paint(Shader=sh2))
    cv.restore()

# ------------------------------------------------------------------ 2.5D parallax portrait
def parallax_portrait(cv, img, t, face=(0.5, 0.32), push=(1.0, 1.09), depth=0.045, desat=0.0, drift=(0, -40), tint=0.0):
    """Painting as layered planes: blurred backdrop, painting plane, and a feathered foreground
    plane around the sitter that scales faster -> gentle depth without inventing image content."""
    iw, ih = img.width(), img.height(); te = ease(t)
    # backdrop: same painting, enlarged & blurred & darkened (fills 9:16 frame)
    bs = max(W / iw, H / ih) * 1.25 * (1 + 0.04 * te)
    cv.save(); cv.translate(W / 2 + drift[0] * 0.3 * te, H / 2 + drift[1] * 0.3 * te); cv.scale(bs, bs); cv.translate(-iw / 2, -ih / 2)
    cv.drawImage(img, 0, 0, SAMP, skia.Paint(ImageFilter=skia.ImageFilters.Blur(28 / bs, 28 / bs), ColorFilter=_cf(desat, 0.55, tint)))
    cv.restore()
    # painting plane: fit width with margin, sitter's face kept in upper third
    base = (W * 1.06) / iw
    def plane(scale_mul, alpha_mask=None):
        s = base * scale_mul
        fx, fy = face[0] * iw, face[1] * ih
        cv.save(); cv.translate(W / 2 + (fx - iw / 2) * s + drift[0] * te, H * 0.36 + drift[1] * te); cv.scale(s, s); cv.translate(-fx, -fy)
        paint = skia.Paint(AntiAlias=True, ColorFilter=_cf(desat, 1.0, tint))
        if alpha_mask is not None:
            cv.saveLayer(skia.Rect(0, 0, iw, ih), None)
            cv.drawImage(img, 0, 0, SAMP, paint)
            cv.drawPaint(skia.Paint(Shader=alpha_mask(iw, ih, fx, fy), BlendMode=skia.BlendMode.kDstIn))
            cv.restore()
        else:
            cv.drawImage(img, 0, 0, SAMP, paint)
        cv.restore()
    z = push[0] + (push[1] - push[0]) * te
    # frame shadow for the painting plane
    plane(z)
    def mask(iw, ih, fx, fy):
        r = min(iw, ih) * 0.33
        return skia.GradientShader.MakeRadial(skia.Point(fx, fy + ih * 0.06), r, [skia.Color4f(0, 0, 0, 1), skia.Color4f(0, 0, 0, 0)], [0.35, 1.0])
    plane(z * (1 + depth * te), mask)
    # soft edge so the painting melts into the backdrop
    top = H * 0.36 - face[1] * ih * base * z; bot = top + ih * base * z
    for y0, y1, inv in ((top - 2, top + 160, False), (bot - 160, bot + 2, True)):
        cols = [skia.Color4f(0.1, 0.07, 0.04, 0.85), skia.Color4f(0.1, 0.07, 0.04, 0)]
        if inv: cols = cols[::-1]
        cv.drawRect(skia.Rect(0, y0, W, y1), skia.Paint(Shader=skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)], cols)))

def _cf(desat, bright, tint=0.0):
    if tint:
        k = tint; base = [[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]]
        ident = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        m = []
        for i in range(3):
            m += [(base[i][j] * 0.92 * k + ident[i][j] * (1 - k)) * bright for j in range(3)] + [0, 0]
        return skia.ColorFilters.Matrix(m + [0, 0, 0, 1, 0])
    d = desat; s = 1 - d
    lum = (0.299, 0.587, 0.114)
    m = []
    for i in range(3):
        row = [lum[j] * d + (s if i == j else 0) for j in range(3)]
        m += [v * bright for v in row] + [0, 0]
    m += [0, 0, 0, 1, 0]
    return skia.ColorFilters.Matrix(m)

def dust(cv, t, seed=3, n=60, alpha=0.35):
    rng = np.random.default_rng(seed); P = rng.random((n, 4))
    for x, y, sz, sp in P:
        yy = (y * H - t * 60 * (0.5 + sp)) % H; xx = (x * W + 20 * math.sin(t * 0.7 + sp * 6)) % W
        cv.drawCircle(xx, yy, 0.8 + sz * 2.2, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 0.93, 0.78, alpha * (0.3 + 0.7 * sz)),
                                                         MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.2)))

# ------------------------------------------------------------------ medallion cameo
def medallion(cv, img, cx, cy, r, face=(0.5, 0.3), zoom=2.4, alpha=1.0, name=None, sub=None, label_side='below', tint=False):
    if alpha <= 0: return
    rx, ry = r * 0.82, r
    oval = skia.Rect(cx - rx, cy - ry, cx + rx, cy + ry)
    cv.saveLayerAlpha(None, int(255 * alpha))
    cv.drawOval(oval.makeOutset(10, 10), skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.45),
                                                    MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)))
    cv.save(); p = skia.Path(); p.addOval(oval); cv.clipPath(p, skia.ClipOp.kIntersect, True)
    if img is not None:
        iw, ih = img.width(), img.height(); s = (2 * ry) / ih * zoom
        cv.translate(cx, cy); cv.scale(s, s); cv.translate(-face[0] * iw, -face[1] * ih)
        cv.drawImage(img, 0, 0, SAMP, skia.Paint(ColorFilter=_cf(0, 1.0, 0.9 if tint else 0)))
    else:  # no authentic portrait available: plain engraved-paper roundel with the name only
        cv.drawOval(oval, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(skia.Point(cx, cy - ry * 0.3), ry * 1.3,
                    [C('#F3E8CC'), C('#D6C29A')])))
        draw_text(cv, (name or '').split()[0][:1] + (' ' + (name or '').split()[-1] if name and len(name.split()) > 1 else ''), cx, cy + 14, font('serif_bold', 44), PAL['gold'], align='center')
    cv.restore()
    gold = skia.GradientShader.MakeSweep(cx, cy, [C('#8A6A2E'), C('#E9CF8A'), C('#7A5A22'), C('#F2DC9C'), C('#8A6A2E')])
    cv.drawOval(oval.makeOutset(4, 4), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, Shader=gold))
    cv.drawOval(oval.makeOutset(11, 11), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Shader=gold))
    if name:
        y = cy + ry + 48
        draw_text(cv, name, cx, y, font('serif_bold', 31), PAL['ink'], align='center', halo=PAL['paper'], halo_w=8)
        if sub: draw_text(cv, sub, cx, y + 31, font('italic', 25), PAL['ink_soft'], align='center', halo=PAL['paper'], halo_w=7)
    cv.restore()

# ------------------------------------------------------------------ cards
def name_card(cv, name, sub, t_in, alpha=1.0, y=1330):
    a = alpha * eseg(t_in, 0, 1)
    if a <= 0: return
    slide = (1 - eseg(t_in, 0, 1)) * 30
    g = C(PAL['gold'])
    cv.save(); cv.translate(0, slide)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y - 110), skia.Point(0, y + 120)],
                                        [skia.Color4f(0.08, 0.05, 0.03, 0), skia.Color4f(0.08, 0.05, 0.03, 0.72 * a), skia.Color4f(0.08, 0.05, 0.03, 0)], [0, 0.5, 1])
    cv.drawRect(skia.Rect(0, y - 110, W, y + 120), skia.Paint(Shader=sh))
    w = text_width(name, font('serif_bold', 62)) * eseg(t_in, 0.1, 1)
    lp = skia.Paint(AntiAlias=True, StrokeWidth=1.6, Color4f=skia.Color4f(0.85, 0.72, 0.45, 0.9 * a))
    cv.drawLine(W / 2 - w / 2, y - 62, W / 2 + w / 2, y - 62, lp)
    draw_text(cv, name, W / 2, y, font('serif_bold', 62), '#F4EAD2', align='center', alpha=a, shadow=True)
    draw_text(cv, sub, W / 2, y + 50, font('italic', 34), '#E2CD9C', align='center', alpha=a)
    cv.restore()

def date_card(cv, top, main, sub, t_in, alpha=1.0, y=470, dark=True):
    a = alpha * eseg(t_in, 0, 1)
    if a <= 0: return
    col_main = '#F4EAD2' if dark else PAL['ink']; col_sub = '#E2CD9C' if dark else PAL['gold']
    if dark:
        sh = skia.GradientShader.MakeLinear([skia.Point(0, y - 170), skia.Point(0, y + 140)],
             [skia.Color4f(0.08, 0.05, 0.03, 0), skia.Color4f(0.08, 0.05, 0.03, 0.78 * a), skia.Color4f(0.08, 0.05, 0.03, 0)], [0, 0.5, 1])
        cv.drawRect(skia.Rect(0, y - 170, W, y + 140), skia.Paint(Shader=sh))
    draw_text(cv, top, W / 2, y - 64, font('caps', 30), col_sub, align='center', tracking=0.4, alpha=a)
    draw_text(cv, main, W / 2, y + 10, font('serif_bold', 70), col_main, align='center', alpha=a, shadow=dark)
    if sub: draw_text(cv, sub, W / 2, y + 62, font('italic', 34), col_sub, align='center', alpha=a)

def caption(cv, text, alpha=1.0, y=1560, dark=False):
    if alpha <= 0: return
    f = font('body_italic', 27); w = text_width(text, f) + 50
    r = skia.RRect.MakeRectXY(skia.Rect(W / 2 - w / 2, y - 38, W / 2 + w / 2, y + 16), 8, 8)
    cv.drawRRect(r, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.1, 0.07, 0.04, 0.55 * alpha) if dark else skia.Color4f(0.96, 0.93, 0.85, 0.85 * alpha)))
    draw_text(cv, text, W / 2, y - 3, f, '#EADBB8' if dark else PAL['ink_soft'], align='center', alpha=alpha)

# ------------------------------------------------------------------ transitions (numpy, RGB uint8)
@functools.lru_cache(None)
def _wipe_noise(seed=5):
    rng = np.random.default_rng(seed)
    def up(a, sz):
        im = skia.Image.fromarray((a * 255).astype(np.uint8), colorType=skia.kGray_8_ColorType)
        s = skia.Surface(W, H); s.getCanvas().drawImageRect(im, skia.Rect(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear))
        return s.makeImageSnapshot().toarray()[..., 0].astype(np.float32) / 255
    n = 0.6 * up(rng.random((24, 14)), 0) + 0.3 * up(rng.random((90, 52)), 0) + 0.1 * up(rng.random((400, 230)), 0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    diag = (xx / W * 0.35 + yy / H * 0.65)
    return (diag * 0.72 + n * 0.28).astype(np.float32)

def deckle_wipe(a, b, p):
    """Torn/burnt-paper wipe from frame a to frame b; p in 0..1."""
    if p <= 0: return a
    if p >= 1: return b
    f = _wipe_noise(); edge = -0.08 + p * 1.16
    m = np.clip((edge - f) / 0.035, 0, 1)[..., None]
    band = np.clip(1 - np.abs(edge - f - 0.02) / 0.03, 0, 1)[..., None]
    out = a.astype(np.float32) * (1 - m) + b.astype(np.float32) * m
    burn = np.array([60, 36, 18], np.float32)
    out = out * (1 - 0.75 * band) + burn * 0.75 * band
    glow = np.clip(1 - np.abs(edge - f - 0.045) / 0.012, 0, 1)[..., None]
    out = out + np.array([255, 190, 110], np.float32) * 0.35 * glow
    return np.clip(out, 0, 255).astype(np.uint8)

def crossfade(a, b, p):
    p = ease(p); return (a.astype(np.float32) * (1 - p) + b.astype(np.float32) * p).astype(np.uint8)

# ------------------------------------------------------------------ painting pan (landscape canvases in a 9:16 frame)
def painting_shot(cv, img, t, p0=(0.3, 0.5), p1=(0.7, 0.5), z0=1.0, z1=1.12, depth=0.025, tint=0.0, desat=0.0, bright=1.0):
    """Fill the frame height with the canvas and travel from focus p0 to p1 (normalised image coords).
    A feathered copy around the current focus scales slightly faster -> gentle 2.5D depth."""
    iw, ih = img.width(), img.height(); te = ease(t)
    z = z0 + (z1 - z0) * te
    s = max(H / ih, W / iw) * z
    fx = (p0[0] + (p1[0] - p0[0]) * te) * iw; fy = (p0[1] + (p1[1] - p0[1]) * te) * ih
    # clamp so the canvas always covers the frame
    fx = min(max(fx, W / 2 / s), iw - W / 2 / s); fy = min(max(fy, H / 2 / s), ih - H / 2 / s)
    cf = _cf(desat, bright, tint)
    def plane(sc, mask=False):
        cv.save(); cv.translate(W / 2, H / 2); cv.scale(sc, sc); cv.translate(-fx, -fy)
        if mask:
            cv.saveLayer(skia.Rect(0, 0, iw, ih), None)
            cv.drawImage(img, 0, 0, SAMP, skia.Paint(ColorFilter=cf))
            r = min(W, H) * 0.42 / sc
            cv.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(skia.Point(fx, fy), r, [skia.Color4f(0, 0, 0, 1), skia.Color4f(0, 0, 0, 0)], [0.3, 1.0]),
                                    BlendMode=skia.BlendMode.kDstIn))
            cv.restore()
        else:
            cv.drawImage(img, 0, 0, SAMP, skia.Paint(ColorFilter=cf))
        cv.restore()
    plane(s)
    if depth: plane(s * (1 + depth * te), True)

def dark_band(cv, y0, y1, a=0.75):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)],
                                        [skia.Color4f(0.08, 0.05, 0.03, 0), skia.Color4f(0.08, 0.05, 0.03, a), skia.Color4f(0.08, 0.05, 0.03, 0)], [0, 0.5, 1])
    cv.drawRect(skia.Rect(0, y0, W, y1), skia.Paint(Shader=sh))

def keyword(cv, text, t_in, y, alpha=1.0, size=58, dark=True):
    a = alpha * eseg(t_in, 0, 1)
    if a <= 0: return
    cv.save(); cv.translate(0, (1 - eseg(t_in, 0, 1)) * 24)
    draw_text(cv, text, W / 2, y, font('caps', size * 0.62), '#EAD7A8' if dark else PAL['gold'], align='center', tracking=0.3, alpha=a, shadow=dark)
    cv.restore()
