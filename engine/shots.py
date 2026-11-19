"""Reusable non-map shots: archival photo with 2.5D parallax, document on a desk, ink transitions.

Every shot renders into a skia canvas (1080×1920) for a local time t (seconds) so the timeline can
mix shots. Photographs are only moved/scaled and parallax-warped by a few pixels – never retouched.
"""
import math, os
import numpy as np, cv2, skia
from engine.render import W, H, hexc, STYLE, draw_text, font, fit_font, ease, seg, paper_texture

def np_to_image(arr):
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)

# ------------------------------------------------------------------------------------------- photo
class PhotoShot:
    """Mounted archival photo: content push-in/pan inside a fixed frame, depth-driven micro-parallax,
    blurred backdrop of the same photo, caption + credit beneath."""
    def __init__(self, img_rgb, depth, box_w=1000, center_y=930, work_px=1700):
        h, w = img_rgb.shape[:2]
        s = work_px / max(h, w)
        self.src = cv2.resize(img_rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        self.depth = cv2.resize(depth, (self.src.shape[1], self.src.shape[0]), interpolation=cv2.INTER_LINEAR)
        self.sh, self.sw = self.src.shape[:2]
        self.box_w = box_w
        self.box_h = int(round(box_w * h / w))
        self.cx, self.cy = W // 2, center_y
        # backdrop: photo scaled to cover, heavily blurred, darkened warm
        cover = max(W / w, H / h) * 1.15
        bd = cv2.resize(img_rgb, (int(w * cover), int(h * cover)), interpolation=cv2.INTER_AREA)
        bd = cv2.GaussianBlur(bd, (0, 0), 38).astype(np.float32)
        tint = np.array([0.62, 0.55, 0.46], np.float32)
        bd = np.clip(bd * tint * 0.75, 0, 255).astype(np.uint8)
        self.backdrop = bd
        yy, xx = np.mgrid[0:self.box_h, 0:self.box_w].astype(np.float32)
        self.grid = (xx, yy)

    def frame(self, zoom, focus, par):
        """zoom ≥1 within the frame, focus = (fx, fy) normalised centre, par = (px, py) parallax in output px."""
        xx, yy = self.grid
        sc = self.sw / self.box_w / zoom
        fx = focus[0] * self.sw; fy = focus[1] * self.sh
        # keep the view inside the image
        half_w = self.box_w * sc / 2; half_h = self.box_h * sc / 2
        fx = min(max(fx, half_w), self.sw - half_w); fy = min(max(fy, half_h), self.sh - half_h)
        mx = fx + (xx - self.box_w / 2) * sc
        my = fy + (yy - self.box_h / 2) * sc
        d = cv2.remap(self.depth, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mx = mx - (d - 0.5) * par[0] * sc
        my = my - (d - 0.5) * par[1] * sc
        out = cv2.remap(self.src, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        return out

    def draw(self, canvas, t, dur, zoom=(1.0, 1.16), focus=((0.5, 0.5), (0.5, 0.5)), par=((-6, 0), (6, -2)),
             caption=None, credit=None, alpha=1.0):
        k = ease(t / dur, "sine")
        z = zoom[0] + (zoom[1] - zoom[0]) * k
        f = (focus[0][0] + (focus[1][0] - focus[0][0]) * k, focus[0][1] + (focus[1][1] - focus[0][1]) * k)
        p = (par[0][0] + (par[1][0] - par[0][0]) * k, par[0][1] + (par[1][1] - par[0][1]) * k)
        # backdrop drifts slowly
        bh, bw = self.backdrop.shape[:2]
        ox = int((bw - W) / 2 + (k - 0.5) * 40); oy = int((bh - H) / 2)
        canvas.drawImage(np_to_image(self.backdrop[oy:oy + H, ox:ox + W]), 0, 0)
        img = np_to_image(self.frame(z, f, p))
        x0, y0 = self.cx - self.box_w / 2, self.cy - self.box_h / 2
        sh = skia.Paint(AntiAlias=True); sh.setColor(skia.Color(0, 0, 0, 150))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
        canvas.drawRect(skia.Rect.MakeXYWH(x0 + 6, y0 + 16, self.box_w, self.box_h), sh)
        mount = skia.Paint(AntiAlias=True); mount.setColor4f(hexc("#EDE3CC"))
        canvas.drawRect(skia.Rect.MakeXYWH(x0 - 12, y0 - 12, self.box_w + 24, self.box_h + 24), mount)
        canvas.drawImage(img, x0, y0, skia.SamplingOptions(skia.FilterMode.kLinear))
        # inner vignette on the print
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial(skia.Point(self.cx, self.cy), self.box_w * 0.78,
                    [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(30, 20, 10, 110)], [0, 0.6, 1]))
        canvas.save(); canvas.clipRect(skia.Rect.MakeXYWH(x0, y0, self.box_w, self.box_h)); canvas.drawPaint(v); canvas.restore()
        cy = y0 + self.box_h + 58
        if caption:
            for i, ln in enumerate(caption):
                draw_text(canvas, ln, W / 2, cy + i * 40, fit_font("serif_italic", 33, ln, self.box_w), "#F1E7D2", alpha)
        if credit:
            draw_text(canvas, credit, W / 2, cy + len(caption or []) * 40 + 4, fit_font("sans", 25, credit, self.box_w, 0.04), "#CDBFA4", alpha * 0.9, 0.04)

# ------------------------------------------------------------------------------------------- document
class DocumentShot:
    """A scanned page lying on a parchment desk. Camera glides from the whole page to a region of interest;
    a translucent amber marker sweeps over the region (coordinates from the scan's ALTO OCR)."""
    def __init__(self, img_rgb, page_px_w=None):
        self.page = np_to_image(img_rgb)
        self.pw, self.ph = img_rgb.shape[1], img_rgb.shape[0]
        rng = np.random.default_rng(11)
        # darker desk: parchment texture tinted
        self.desk = paper_texture(seed=21)

    def draw(self, canvas, t, dur, roi, enter=0.8, zoom_full_w=0.84, roi_fill=0.88, rot=(-2.4, -0.6),
             mark=None, mark_t=(0.45, 0.8), caption=None, credit=None):
        """roi = (x0, y0, x1, y1) page px; mark = list of rects (page px) to highlight."""
        canvas.clear(hexc("#B9A27C").toColor())
        p = skia.Paint(); p.setBlendMode(skia.BlendMode.kMultiply); p.setAlphaf(1.0)
        canvas.drawImage(self.desk, 0, 0, skia.SamplingOptions(), p)
        k_in = ease(seg(t, 0, enter), "out")
        k = ease(seg(t, enter * 0.5, dur - 0.3), "sine")
        # camera: page scale and centre (page px) interpolated full-page → ROI
        rcx, rcy = (roi[0] + roi[2]) / 2, (roi[1] + roi[3]) / 2
        z_full = zoom_full_w * W / self.pw
        z_roi = roi_fill * W / (roi[2] - roi[0])
        z = math.exp(math.log(z_full) + (math.log(z_roi) - math.log(z_full)) * k)
        cx = self.pw / 2 + (rcx - self.pw / 2) * k
        cy = self.ph / 2 + (rcy - self.ph / 2) * k
        r = rot[0] + (rot[1] - rot[0]) * k
        slide = (1 - k_in) * 900
        canvas.save()
        canvas.translate(W / 2, H / 2 + slide - 40)
        canvas.rotate(r)
        canvas.scale(z, z)
        canvas.translate(-cx, -cy)
        sh = skia.Paint(AntiAlias=True); sh.setColor(skia.Color(40, 25, 10, 170))
        sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30 / z))
        canvas.drawRect(skia.Rect.MakeXYWH(14 / z, 26 / z, self.pw, self.ph), sh)
        canvas.drawImageRect(self.page, skia.Rect.MakeWH(self.pw, self.ph),
                             skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        if mark:
            km = ease(seg(t / dur, *mark_t), "inout")
            mp = skia.Paint(AntiAlias=True); mp.setColor4f(hexc("#E8B44A", 0.42))
            mp.setBlendMode(skia.BlendMode.kMultiply)
            n = len(mark)
            for i, (x0, y0, x1, y1) in enumerate(mark):
                ki = min(1.0, max(0.0, km * n - i))
                if ki > 0:
                    canvas.drawRoundRect(skia.Rect.MakeLTRB(x0 - 14, y0 - 8, x0 - 14 + (x1 - x0 + 28) * ki, y1 + 8), 6, 6, mp)
        canvas.restore()
        # light falloff on the desk
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.45), H * 0.75,
                    [skia.Color(255, 240, 210, 40), skia.Color(0, 0, 0, 0), skia.Color(30, 18, 6, 150)], [0, 0.5, 1]))
        canvas.drawPaint(v)
        if caption:
            bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc("#2B2117", 0.82))
            canvas.drawRoundRect(skia.Rect.MakeXYWH(70, 1400, W - 140 - 80, 44 * len(caption) + 70), 14, 14, bg)
            for i, ln in enumerate(caption):
                draw_text(canvas, ln, 500, 1452 + i * 44, fit_font("serif_italic", 34, ln, 800), "#F1E7D2", 1.0)
            if credit:
                draw_text(canvas, credit, 500, 1452 + len(caption) * 44 + 6, fit_font("sans", 25, credit, 800, 0.03), "#D8CBB0", 0.95, 0.03)

# ------------------------------------------------------------------------------------------- transitions
_noise = {}
def ink_mask(progress, seed=5, softness=0.16, direction=(0.35, 1.0)):
    """Organic ink-bleed wipe: smooth large-scale noise + directional gradient thresholded by progress → alpha [0..1]."""
    key = (seed, direction)
    if key not in _noise:
        rng = np.random.default_rng(seed)
        h, w = H // 8, W // 8
        acc = np.zeros((h, w), np.float32)
        for oc, amp in ((2, 0.65), (5, 0.35)):
            n = rng.random((oc + 3, max(2, int(oc * w / h)) + 3)).astype(np.float32)
            acc += amp * cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        g = (xx / w * direction[0] + yy / h * direction[1]) / (direction[0] + direction[1])
        f = 0.62 * g + 0.38 * acc
        f = cv2.GaussianBlur(f, (0, 0), 2.0)
        f = (f - f.min()) / (f.max() - f.min())
        _noise[key] = cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC)
    f = _noise[key]
    p = progress * (1 + 2 * softness) - softness
    m = np.clip((p - f) / softness + 0.5, 0, 1)
    return m * m * (3 - 2 * m)

def ink_blend(fa, fb, m, rim=0.30):
    """Composite two RGBA frames with mask m (H,W,1) and a faint dark ink rim along the moving edge."""
    edge = 4 * m * (1 - m)
    out = fa * (1 - m) + fb * m
    out[..., :3] *= (1 - rim * edge)
    return out
