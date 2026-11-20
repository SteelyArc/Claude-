"""CONCEPT 2 - Living History / Cinematic 2.5D.
Genuine paintings re-photographed by a virtual camera: per-pixel depth (Depth Anything V2) drives true parallax,
dolly and rack focus; volumetric light, dust in depth of field, candle flicker, warm/teal grade.
Sample: Wojniakowski's 'Constitution of 3 May 1791' (1806) -> light-burn transition -> Bacciarelli's Stanislaw August (1764)."""
import sys, numpy as np, skia, cv2
from core import *

rng = np.random.default_rng(7)


class Plate:
    """A painting + depth map prepared for 2.5D re-projection."""

    def __init__(self, name, ext, scale):
        im = load_rgb(f'assets/images/{name}.{ext}').astype(np.float32) / 255
        d = np.load(f'{ROOT}/data/depth/{name}.npy').astype(np.float32)
        d = cv2.resize(d, (im.shape[1], im.shape[0]))
        if scale != 1:
            im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
            d = cv2.resize(d, (im.shape[1], im.shape[0]))
        self.im = im; self.d = cv2.GaussianBlur(d, (0, 0), 3)
        self.blur = cv2.GaussianBlur(im, (0, 0), 9)
        self.h, self.w = d.shape

    def shoot(self, cx, cy, zoom, par_x, par_y, dolly, focus=None, fstop=0.0):
        """cx, cy: source point at screen centre; zoom: screen px per source px;
        par_x/y: parallax shift in source px for depth=1 relative to depth=0; dolly: extra magnification of near layers."""
        xs = (np.arange(W, dtype=np.float32) - W / 2) / zoom
        ys = (np.arange(H, dtype=np.float32) - H / 2) / zoom
        U, V = np.meshgrid(xs, ys)
        u, v = U + cx, V + cy
        for _ in range(2):          # fixed-point refine depth at the displaced position
            d = cv2.remap(self.d, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            k = 1 / (1 + dolly * d)
            u = cx + U * k - par_x * (d - 0.5)
            v = cy + V * k - par_y * (d - 0.5)
        col = cv2.remap(self.im, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if focus is not None and fstop > 0:
            b = cv2.remap(self.blur, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            coc = np.clip(np.abs(d - focus) * fstop, 0, 1)[..., None]
            col = col * (1 - coc) + b * coc
        return col, d


A = Plate('constitution_1791', 'jpg', 1.75)       # 1920x1336 -> 3360x2338
B = Plate('stanislaw', 'png', 1.0)                 # 1755x2510

# dust motes: x, y in screen, z depth 0..1, phase
N = 220
MOTES = np.column_stack([rng.uniform(-200, W + 200, N), rng.uniform(-200, H + 200, N), rng.uniform(0, 1, N),
                         rng.uniform(0, 6.28, N), rng.uniform(0.4, 1.0, N)]).astype(np.float32)


def grade(img, warm=1.0):
    """filmic: lift shadows into teal, push highlights to amber, soft shoulder."""
    lum = img.mean(axis=2, keepdims=True)
    sh = np.array([0.02, 0.05, 0.07], np.float32); hi = np.array([1.06, 0.98, 0.86], np.float32)
    img = img * (1 - lum) * (0.92 + 0.0) + img * lum * lerp(1.0, hi, warm) + sh * (1 - lum) ** 3 * 0.8
    img = img / (1 + img * 0.18)
    return np.clip(img * 1.32 + 0.015, 0, 1)


def rays(c, t, cx, cy, ang, a, n=7, spread=0.5, length=2600):
    """volumetric light shafts fanning from a window point (screen space)."""
    for i in range(n):
        th = ang + (i - n / 2) * spread / n + 0.03 * np.sin(t * 0.6 + i * 1.7)
        w = 40 + 70 * ((i * 37) % 5) / 5
        inten = a * (0.5 + 0.5 * np.sin(t * 0.9 + i * 2.3)) * (0.35 + 0.65 * ((i * 53) % 7) / 7)
        p = skia.Paint(AntiAlias=True); p.setBlendMode(skia.BlendMode.kScreen)
        dx, dy = np.cos(th), np.sin(th)
        p.setShader(lin_grad((cx, cy), (cx + dx * length, cy + dy * length), [rgb('#ffd9a0', inten), rgb('#ffd9a0', inten * 0.4), rgb('#ffd9a0', 0)], [0, .45, 1]))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
        nx, ny = -dy, dx
        pth = skia.Path(); pth.moveTo(cx + nx * w * 0.3, cy + ny * w * 0.3); pth.lineTo(cx + dx * length + nx * w * 2.2, cy + dy * length + ny * w * 2.2)
        pth.lineTo(cx + dx * length - nx * w * 2.2, cy + dy * length - ny * w * 2.2); pth.lineTo(cx - nx * w * 0.3, cy - ny * w * 0.3); pth.close()
        c.drawPath(pth, p)


def motes(c, t, par, focus_z=0.5, a=1.0, warm='#ffe6c0'):
    for x, y, z, ph, s in MOTES:
        px = (x + par * (z - 0.5) * 1.2 + 25 * np.sin(t * 0.35 * s + ph)) % (W + 400) - 200
        py = (y - t * (12 + 30 * z) + 18 * np.cos(t * 0.27 + ph)) % (H + 400) - 200
        r = 1.2 + 5.5 * z ** 2
        blur = 0.3 + abs(z - focus_z) * 14
        al = a * (0.22 + 0.55 * s) * (0.6 + 0.4 * np.sin(t * 2 * s + ph)) * (1 - 0.5 * abs(z - focus_z))
        p = skia.Paint(Color4f=rgb(warm, al), AntiAlias=True); p.setBlendMode(skia.BlendMode.kScreen)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        c.drawCircle(float(px), float(py), r, p)


def tag(c, x, y, s, a, kind='doc'):
    f = font('SourceSans3-SemiBold.ttf', 23); w = text_width(s, f, 4) + 40
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y - 30, w, 42), 4, 4)
    if kind == 'doc':
        c.drawRRect(r, fill(rgb('#10100e', 0.55 * a))); c.drawRRect(r, stroke(rgb('#efe6d2', 0.8 * a), 1.4))
        text(c, s, x + 20, y - 1, f, rgb('#efe6d2', a), align='l', spacing=4)
    else:
        c.drawRRect(r, stroke(rgb('#ffcf7a', a), 1.8, dash=[8, 6])); text(c, s, x + 20, y - 1, f, rgb('#ffcf7a', a), align='l', spacing=4)


def lower_third(c, t, t0, kicker, title, sub, credit, a_out=1.0):
    k = seg(t, t0, t0 + 1.2); a = k * a_out
    if a <= 0: return
    x = 92
    # gold rule draws in
    c.drawLine(x, 1180, x + 520 * eout(seg(t, t0, t0 + 0.9)), 1180, stroke(rgb('#e6c27d', 0.9 * a), 2.2))
    text(c, kicker, x, 1150, font('SourceSans3-SemiBold.ttf', 27), rgb('#e6c27d', a), align='l', spacing=7, reveal=seg(t, t0, t0 + 0.8))
    for i, ln in enumerate(title):
        text(c, ln, x, 1262 + i * 80, font('CG-SemiBold.ttf', 84), rgb('#fbf3e3', a), align='l', spacing=0.5,
             reveal=seg(t, t0 + 0.15 + i * 0.15, t0 + 1.25 + i * 0.15), shadow=rgb('#000000', 0.7))
    yy = 1262 + len(title) * 80 - 18
    text(c, sub, x, yy + 26, font('CG-MediumItalic.ttf', 40), rgb('#e9dcc4', a), align='l', reveal=seg(t, t0 + 0.5, t0 + 1.6), shadow=rgb('#000000', 0.7))
    for i, ln in enumerate(credit.split(' | ')):
        text(c, ln, x, max(1470, yy + 82) + i * 32, font('SourceSans3-Regular.ttf', 25), rgb('#cfc4b0', 0.85 * a), align='l', spacing=0.6)


def scene(c, t, f):
    # ---------------- shot A: the Senate hall, 3 May 1791 (0 - 5.6 s)
    if t < 5.9:
        k = ease(seg(t, 0, 5.9))
        img, d = A.shoot(cx=lerp(1280, 1980, k), cy=lerp(1250, 1180, k), zoom=lerp(0.92, 1.02, k),
                         par_x=lerp(-130, 130, k), par_y=lerp(30, -20, k), dolly=lerp(0.05, 0.22, k), focus=0.85, fstop=lerp(1.1, 0.7, k))
        flick = 1 + 0.025 * np.sin(t * 13.0) * np.sin(t * 7.3 + 1)
        img = grade(img * flick, 1.0)
        c.drawImage(to_image((img * 255).astype(np.uint8)), 0, 0)
        rays(c, t, lerp(250, 120, k), -120, 1.15, 0.16, n=8, spread=0.7)
        motes(c, t, lerp(-260, 260, k), focus_z=0.8)
        # a soft vignette top/bottom for type
        g = skia.Paint(); g.setShader(lin_grad((0, 950), (0, H), [rgb('#0b0806', 0), rgb('#0b0806', 0.88)])); c.drawRect(skia.Rect(0, 950, W, H), g)
        lower_third(c, t, 1.2, 'WARSAW · 3 MAY 1791', ['The Constitution', 'of 3 May'], 'One of the first modern written constitutions in Europe',
                    'Kazimierz Wojniakowski, Passing of the Constitution of 3 May 1791 | (painted 1806) · National Museum, Warsaw', 1 - seg(t, 4.9, 5.4))
        tag(c, 92, 300, 'DOCUMENTED HISTORY', seg(t, 1.0, 1.6) * (1 - seg(t, 4.9, 5.4)))
    # ---------------- shot B: the king (5.0 - 11 s)
    if t >= 5.0:
        k = seg(t, 5.0, 11.0); e = ease(k)
        img, d = B.shoot(cx=lerp(880, 835, e), cy=lerp(1180, 700, e), zoom=lerp(0.80, 1.45, e),
                         par_x=lerp(60, -50, e), par_y=lerp(-25, 15, e), dolly=lerp(0.0, 0.15, e), focus=lerp(0.35, 0.72, eout(seg(t, 5.4, 7.4))), fstop=0.9)
        img = grade(img, 0.9)
        # rim light from the right, breathing
        if True:
            pass
        imgB = to_image((img * 255).astype(np.uint8))
        a = seg(t, 5.0, 5.9)
        p = skia.Paint(); p.setAlphaf(a)
        c.drawImage(imgB, 0, 0, SAMP, p)
        rays(c, t, W + 120, -60, 2.05, 0.12 * a, n=6, spread=0.5)
        motes(c, t, lerp(140, -140, e), focus_z=0.9, a=0.7 * a)
        g = skia.Paint(); g.setShader(lin_grad((0, 820), (0, 1250), [rgb('#0b0806', 0), rgb('#0b0806', 0.93)])); c.drawRect(skia.Rect(0, 820, W, H), g)
        lower_third(c, t, 6.6, 'KING OF POLAND · GRAND DUKE OF LITHUANIA', ['Stanisław August'], 'The last king of the Commonwealth, 1764–1795',
                    'Marcello Bacciarelli, Stanisław August in Coronation Robes | (1764) · Royal Castle, Warsaw')
        tag(c, 92, 300, 'DOCUMENTED HISTORY', seg(t, 6.4, 7.0))
    # ---------------- transition: light burn (warm flare sweeps, exposure blooms)
    tb = seg(t, 4.75, 5.95)
    if 0 < tb < 1:
        a = np.sin(tb * np.pi)
        p = skia.Paint(); p.setBlendMode(skia.BlendMode.kScreen)
        x = lerp(-300, W + 300, ease(tb))
        p.setShader(rad_grad(x, H * 0.42, 1300, [rgb('#fff1d6', 0.95 * a), rgb('#ffb45e', 0.55 * a), rgb('#ff8a3d', 0)], [0, .35, 1]))
        c.drawRect(skia.Rect(0, 0, W, H), p)
    if t < 0.5: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.5)))
    if t > 10.6: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', seg(t, 10.6, 11.0))))


if __name__ == '__main__':
    out = f'{ROOT}/previews/concepts/concept2_living_history.mp4'
    render(scene, 11.0, out, Post(grain=0.045, vignette=0.6, bloom=0.35, seed=3), stills=(2.6, 4.6, 5.3, 7.8, 9.8),
           still_dir=f'{ROOT}/previews/concepts')
