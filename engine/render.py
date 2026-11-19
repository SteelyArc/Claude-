"""Atlas-style vertical map renderer (skia). Reusable across documentaries.

Coordinates: geometries are projected metres (see engine.geo.project). A Camera maps metres → pixels.
Every drawing primitive takes animation parameters (0..1) so the same scene renders stills and animation.
"""
import math, os
import numpy as np
import skia
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, GeometryCollection, box
from shapely.ops import linemerge, unary_union

W, H = 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")

# ---------------------------------------------------------------- style
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return skia.Color4f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

STYLE = {
    "paper": "#EFE6D2", "sea": "#C4D3CF", "sea_line": "#6E8E92", "coast": "#4E5753",
    "river": "#6F97A1", "lake": "#C4D3CF", "ink": "#3A2F24", "ink_soft": "#6B5A45",
    "label": "#3A2F24", "water_label": "#4A6A70", "halo": "#F3EBD9",
}
PALETTE = {  # muted atlas pastels
    "order": "#D8C69C", "poland": "#E5BCAF", "prussia": "#AFC1D4", "freecity": "#BCD0AB",
    "russia": "#CDC2D8", "austria": "#E5D49A", "neutral": "#E4DAC3", "plebiscite": "#E9C98A",
    "germany": "#AFC1D4", "soviet": "#CDC2D8", "lithuania": "#D9CDB0", "warmia": "#E8C9B4",
}

# ---------------------------------------------------------------- fonts
_tf_cache = {}
def typeface(file, wght=None):
    key = (file, wght)
    if key not in _tf_cache:
        tf = skia.Typeface.MakeFromFile(os.path.join(FONTS, file))
        if wght is not None:
            C = skia.FontArguments.VariationPosition.Coordinate
            pos = skia.FontArguments.VariationPosition(
                skia.FontArguments.VariationPosition.Coordinates([C(0x77676874, float(wght))]))
            fa = skia.FontArguments(); fa.setVariationDesignPosition(pos)
            tf = tf.makeClone(fa)
        _tf_cache[key] = tf
    return _tf_cache[key]

def font(kind, size):
    f = {
        "display": ("CormorantGaramond[wght].ttf", 600),
        "display_bold": ("CormorantGaramond[wght].ttf", 700),
        "serif": ("EBGaramond[wght].ttf", 500),
        "serif_italic": ("EBGaramond-Italic[wght].ttf", 500),
        "caps": ("Cinzel[wght].ttf", 600),
        "caps_light": ("Cinzel[wght].ttf", 500),
        "sans": ("AlegreyaSans-Medium.ttf", None),
        "sans_regular": ("AlegreyaSans-Regular.ttf", None),
        "sans_italic": ("AlegreyaSans-Italic.ttf", None),
        "sc": ("AlegreyaSansSC-Medium.ttf", None),
        "sc_bold": ("AlegreyaSansSC-Bold.ttf", None),
    }[kind]
    ft = skia.Font(typeface(*f), size)
    ft.setSubpixel(True); ft.setEdging(skia.Font.Edging.kAntiAlias)
    return ft

def text_width(txt, ft, tracking=0.0):
    if not txt:
        return 0.0
    ws = ft.getWidths(ft.textToGlyphs(txt))
    return sum(ws) + tracking * ft.getSize() * (len(txt) - 1)

def draw_text(canvas, txt, x, y, ft, color, alpha=1.0, tracking=0.0, align="center",
              halo=None, halo_w=0.0, rise=0.0):
    """Draw text with optional letter-spacing (em units) and a soft halo. y = baseline."""
    if alpha <= 0.003 or not txt:
        return
    w = text_width(txt, ft, tracking)
    x0 = x - w / 2 if align == "center" else (x - w if align == "right" else x)
    y = y + rise
    glyphs = ft.textToGlyphs(txt)
    ws = ft.getWidths(glyphs)
    pos, cx = [], x0
    for wi in ws:
        pos.append(skia.Point(cx, y)); cx += wi + tracking * ft.getSize()
    blob = skia.TextBlob.MakeFromPosText(txt, pos, ft) if hasattr(skia.TextBlob, "MakeFromPosText") else None
    if blob is None:
        b = skia.TextBlobBuilder(); b.allocRunPos(ft, glyphs, pos); blob = b.make()
    if halo:
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=halo_w,
                       StrokeJoin=skia.Paint.kRound_Join)
        c = hexc(halo, alpha * 0.92); p.setColor4f(c)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.2))
        canvas.drawTextBlob(blob, 0, 0, p)
    p = skia.Paint(AntiAlias=True); p.setColor4f(hexc(color, alpha))
    canvas.drawTextBlob(blob, 0, 0, p)

# ---------------------------------------------------------------- geometry → paths
def geom_path(g, tol=0.0):
    path = skia.Path(); path.setFillType(skia.PathFillType.kEvenOdd)
    if g is None or g.is_empty:
        return path
    if tol:
        g = g.simplify(tol, preserve_topology=True)
    def ring(coords, close):
        coords = list(coords)
        if len(coords) < 2:
            return
        path.moveTo(*coords[0])
        for c in coords[1:]:
            path.lineTo(c[0], c[1])
        if close:
            path.close()
    def add(geom):
        if isinstance(geom, Polygon):
            ring(geom.exterior.coords, True)
            for i in geom.interiors:
                ring(i.coords, True)
        elif isinstance(geom, LineString):
            ring(geom.coords, False)
        elif hasattr(geom, "geoms"):
            for gg in geom.geoms:
                add(gg)
    add(g)
    return path

def shared_border(a, b, tol=400.0):
    """Line(s) where territories a and b meet (projected metres), merged and ordered north→south."""
    line = a.boundary.intersection(b.buffer(tol))
    lines = [l for l in getattr(line, "geoms", [line]) if isinstance(l, LineString) and l.length > tol]
    if not lines:
        return LineString()
    m = linemerge(unary_union(lines))
    parts = list(getattr(m, "geoms", [m]))
    out = []
    for l in parts:
        c = list(l.coords)
        if c[0][1] < c[-1][1]:
            c.reverse()
        out.append(LineString(c))
    out.sort(key=lambda l: -l.coords[0][1])
    return MultiLineString(out) if len(out) > 1 else out[0]

# ---------------------------------------------------------------- camera
class Camera:
    def __init__(self, cx, cy, span_w, rot=0.0):
        """span_w = metres visible across the 1080 px width."""
        self.cx, self.cy, self.s, self.rot = cx, cy, W / span_w, rot
    def matrix(self):
        m = skia.Matrix()
        m.setTranslate(W / 2, H / 2)
        m.preRotate(self.rot)
        m.preScale(self.s, -self.s)
        m.preTranslate(-self.cx, -self.cy)
        return m
    def px(self, x, y):
        return self.matrix().mapXY(x, y)
    def m(self, pixels):  # pixel length → metres
        return pixels / self.s
    def view_box(self, margin=1.3):
        hw, hh = W / self.s / 2 * margin, H / self.s / 2 * margin
        r = math.hypot(hw, hh)
        return box(self.cx - r, self.cy - r, self.cx + r, self.cy + r)

def lerp_cam(a, b, t):
    """Interpolate cameras with log-scale zoom (perceptually even)."""
    c = Camera(0, 0, 1)
    c.cx = a.cx + (b.cx - a.cx) * t; c.cy = a.cy + (b.cy - a.cy) * t
    c.s = math.exp(math.log(a.s) + (math.log(b.s) - math.log(a.s)) * t)
    c.rot = a.rot + (b.rot - a.rot) * t
    return c

def ease(t, kind="inout"):
    t = max(0.0, min(1.0, t))
    if kind == "inout":
        return t * t * (3 - 2 * t) if t < 1 else 1.0
    if kind == "sine":
        return 0.5 - 0.5 * math.cos(math.pi * t)
    if kind == "out":
        return 1 - (1 - t) ** 3
    if kind == "in":
        return t ** 3
    if kind == "expo":
        return 1 - 2 ** (-10 * t) if t < 1 else 1.0
    return t

def seg(t, a, b):
    """Local progress of t within [a,b]."""
    return 0.0 if t <= a else 1.0 if t >= b else (t - a) / (b - a)

# ---------------------------------------------------------------- textures
_tex = {}
def paper_texture(seed=7, w=W, h=H):
    """Procedural paper: low-frequency mottling, fibres, fine grain, warm vignette → RGBA image for Multiply."""
    key = ("paper", seed, w, h)
    if key in _tex:
        return _tex[key]
    rng = np.random.default_rng(seed)
    def smooth_noise(scale):
        sh = (h // scale + 3, w // scale + 3)
        n = rng.random(sh).astype(np.float32)
        from PIL import Image
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((w + 3 * scale, h + 3 * scale), Image.BICUBIC)
        return np.asarray(im, dtype=np.float32)[:h, :w] / 255.0
    mott = 0.55 * smooth_noise(240) + 0.3 * smooth_noise(90) + 0.15 * smooth_noise(30)
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    fib = np.zeros((h, w), np.float32)
    for _ in range(900):  # fibres
        x, y = rng.integers(0, w), rng.integers(0, h)
        L = rng.integers(8, 40); ang = rng.random() * math.pi
        xs = (x + np.cos(ang) * np.arange(L)).astype(int) % w
        ys = (y + np.sin(ang) * np.arange(L)).astype(int) % h
        fib[ys, xs] += rng.random() * 0.6
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = ((xx / w - 0.5) ** 2 * 1.6 + (yy / h - 0.5) ** 2 * 1.0)
    lum = 1.0 - 0.045 * (mott - 0.5) * 2 - 0.012 * grain - 0.035 * fib - 0.10 * vig
    lum = np.clip(lum, 0.55, 1.0)
    rgb = np.stack([lum, lum * 0.985 + 0.01, lum * 0.95 + 0.03], -1)
    rgba = np.dstack([np.clip(rgb, 0, 1), np.ones((h, w), np.float32)])
    img = skia.Image.fromarray((rgba * 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType)
    _tex[key] = img
    return img

def grain_frames(n=6, seed=3, strength=10):
    key = ("grain", n, seed, strength)
    if key not in _tex:
        rng = np.random.default_rng(seed); out = []
        for _ in range(n):
            g = rng.normal(128, strength, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
            a = np.full_like(g, 255)
            rgba = np.dstack([g, g, g, a])
            out.append(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType))
        _tex[key] = out
    return _tex[key]

# ---------------------------------------------------------------- the map layer stack
class AtlasMap:
    """Holds projected base layers and territories; draw(canvas, cam, state) renders a frame."""
    def __init__(self, land, lakes, rivers, coast_lines=None):
        self.land, self.lakes, self.rivers = land, lakes, rivers  # projected shapely
        self._path_cache = {}
        self._ripples = {}

    def path(self, key, geom, tol):
        if tol > 0:   # quantise so continuous zooms reuse cached paths (steps of 2^(1/3))
            tol = 2 ** (math.floor(math.log2(tol) * 3) / 3)
        k = (key, round(tol, 2))
        if k not in self._path_cache:
            self._path_cache[k] = geom_path(geom, tol)
        return self._path_cache[k]

    def ripple_lines(self, cam, n=4):
        """Classic engraved coastal water-lines (offsets of the coast, in sea)."""
        k = round(cam.s, 7)
        key = round(math.log(cam.s) * 4)  # quantised zoom level
        if key not in self._ripples:
            tol = cam.m(1.5)
            land = self.land.simplify(cam.m(3), preserve_topology=True)
            paths = []
            for i in range(n):
                d = cam.m(7 + i * i * 5 + i * 7)
                b = land.buffer(d, resolution=6)
                paths.append(geom_path(b.boundary, tol))
            self._ripples[key] = paths
        return self._ripples[key]

    def base(self, canvas, cam, sea_alpha=1.0):
        canvas.clear(hexc(STYLE["paper"]).toColor())
        tol = cam.m(0.6)
        land = self.path("land", self.land, tol)
        canvas.save(); canvas.concat(cam.matrix())
        p = skia.Paint(AntiAlias=True); p.setColor4f(hexc(STYLE["sea"]))
        canvas.drawPaint(p)
        # ripple lines in the sea
        canvas.save(); canvas.clipPath(land, skia.ClipOp.kDifference, True)
        for i, rp in enumerate(self.ripple_lines(cam, 5)):
            q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(1.3))
            q.setColor4f(hexc(STYLE["sea_line"], 0.42 * (1 - i / 6)))
            canvas.drawPath(rp, q)
        canvas.restore()
        p.setColor4f(hexc(STYLE["paper"])); canvas.drawPath(land, p)
        canvas.restore()

    def fill(self, canvas, cam, key, geom, color, alpha=1.0, band=True, reveal=None, hatch=None, reveal_out=False):
        """Territory wash. reveal=(origin_xy, progress) for an ink-spread reveal from a point."""
        if alpha <= 0.003 or geom is None or geom.is_empty:
            return
        tol = cam.m(0.6)
        path = self.path(key, geom, tol)
        land = self.path("land", self.land, tol)
        canvas.save(); canvas.concat(cam.matrix())
        canvas.clipPath(land, skia.ClipOp.kIntersect, True)
        layer_paint = skia.Paint(); layer_paint.setAlphaf(alpha)
        layer_paint.setBlendMode(skia.BlendMode.kMultiply)
        canvas.saveLayer(None, layer_paint)
        p = skia.Paint(AntiAlias=True); p.setColor4f(hexc(color, 0.95))
        canvas.drawPath(path, p)
        if band:  # darker inner band along the border (classic atlas edge tint)
            canvas.save(); canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(22),
                           StrokeJoin=skia.Paint.kRound_Join)
            q.setColor4f(hexc(color, 0.9))
            q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, cam.m(3)))
            canvas.drawPath(path, q)
            canvas.restore()
        if hatch:
            canvas.save(); canvas.clipPath(path, skia.ClipOp.kIntersect, True)
            b = geom.bounds; step = cam.m(hatch.get("step", 16))
            q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(hatch.get("w", 2.2)))
            q.setColor4f(hexc(hatch.get("color", STYLE["ink"]), hatch.get("alpha", 0.55)))
            span = (b[2] - b[0]) + (b[3] - b[1])
            k = b[0] - (b[3] - b[1])
            while k < b[2]:
                canvas.drawLine(k, b[1], k + (b[3] - b[1]), b[3], q); k += step
            canvas.restore()
        if reveal is not None:
            (ox, oy), prog = reveal
            bb = geom.bounds
            R = max(math.hypot(bb[0] - ox, bb[1] - oy), math.hypot(bb[2] - ox, bb[3] - oy),
                    math.hypot(bb[0] - ox, bb[3] - oy), math.hypot(bb[2] - ox, bb[1] - oy)) * 1.05
            r = max(1.0, R * prog)
            mask = skia.Paint(AntiAlias=True)
            mask.setShader(skia.GradientShader.MakeRadial(
                skia.Point(ox, oy), r, [skia.Color(0, 0, 0, 255), skia.Color(0, 0, 0, 255), skia.Color(0, 0, 0, 0)],
                [0.0, 0.82, 1.0]))
            mask.setBlendMode(skia.BlendMode.kDstOut if reveal_out else skia.BlendMode.kDstIn)
            canvas.drawPaint(mask)
        canvas.restore()  # layer
        canvas.restore()

    def water(self, canvas, cam, river_names_major=(), alpha=1.0, flow=None):
        tol = cam.m(0.6)
        canvas.save(); canvas.concat(cam.matrix())
        p = skia.Paint(AntiAlias=True); p.setColor4f(hexc(STYLE["lake"], alpha))
        canvas.drawPath(self.path("lakes", self.lakes, tol), p)
        for name, geom, major in self.rivers:
            q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                           StrokeWidth=cam.m(4.2 if major else 2.2), StrokeCap=skia.Paint.kRound_Cap,
                           StrokeJoin=skia.Paint.kRound_Join)
            q.setColor4f(hexc(STYLE["river"], alpha * (1 if major else 0.8)))
            path = self.path("river:" + name, geom, tol)
            canvas.drawPath(path, q)
            if flow is not None and major:  # animated flow highlights along the river
                f = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(2.2),
                               StrokeCap=skia.Paint.kRound_Cap)
                f.setColor4f(hexc("#E9F2F1", 0.75 * alpha))
                on, off = cam.m(14), cam.m(46)
                f.setPathEffect(skia.DashPathEffect.Make([on, off], -flow * (on + off) * 3))
                canvas.drawPath(path, f)
        canvas.restore()

    def coast(self, canvas, cam, alpha=1.0):
        tol = cam.m(0.6)
        canvas.save(); canvas.concat(cam.matrix())
        q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(1.6),
                       StrokeJoin=skia.Paint.kRound_Join)
        q.setColor4f(hexc(STYLE["coast"], 0.85 * alpha))
        canvas.drawPath(self.path("land", self.land, tol), q)
        canvas.restore()

    def border(self, canvas, cam, key, geom, progress=1.0, alpha=1.0, width=2.6, color=None,
               dash=None, halo=True, nib=False):
        """Ink border, animated with a trim effect (progress 0→1 draws the line)."""
        if alpha <= 0.003 or progress <= 0.0 or geom is None or geom.is_empty:
            return
        tol = cam.m(0.6)
        path = self.path(key, geom, tol)
        canvas.save(); canvas.concat(cam.matrix())
        trim = skia.TrimPathEffect.Make(0.0, min(1.0, progress)) if progress < 1.0 else None
        if halo:
            h = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(width * 3.2),
                           StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
            h.setColor4f(hexc(STYLE["halo"], 0.55 * alpha))
            if trim: h.setPathEffect(trim)
            canvas.drawPath(path, h)
        q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(width),
                       StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
        q.setColor4f(hexc(color or STYLE["ink"], 0.9 * alpha))
        eff = trim
        if dash:
            d = skia.DashPathEffect.Make([cam.m(dash[0]), cam.m(dash[1])], 0)
            eff = skia.PathEffect.MakeCompose(d, trim) if trim else d
        if eff: q.setPathEffect(eff)
        canvas.drawPath(path, q)
        if nib and progress < 1.0:  # glowing pen nib at the drawing head
            meas = skia.PathMeasure(path, False)
            lens = []
            while True:
                lens.append(meas.getLength())
                if not meas.nextContour():
                    break
            L = sum(lens) * progress
            meas = skia.PathMeasure(path, False)
            for ln in lens:
                if L <= ln:
                    pos, _ = meas.getPosTan(L)
                    g = skia.Paint(AntiAlias=True)
                    g.setShader(skia.GradientShader.MakeRadial(pos, cam.m(16),
                                [skia.Color(255, 244, 214, 200), skia.Color(255, 244, 214, 0)], None))
                    canvas.drawCircle(pos, cam.m(16), g)
                    d = skia.Paint(AntiAlias=True); d.setColor4f(hexc(STYLE["ink"], alpha))
                    canvas.drawCircle(pos, cam.m(3.2), d)
                    break
                L -= ln
                meas.nextContour()
        canvas.restore()

    def path_line(self, canvas, cam, key, geom, progress=1.0, color="#7A4E2D", width=3.0, alpha=1.0,
                  dash=(10, 9), arrow=False):
        """Routes / movements: dashed line drawn on, optional arrow head at the end."""
        if progress <= 0 or alpha <= 0.003:
            return
        tol = cam.m(0.6)
        path = self.path(key, geom, tol)
        canvas.save(); canvas.concat(cam.matrix())
        q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(width),
                       StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
        q.setColor4f(hexc(color, alpha))
        trim = skia.TrimPathEffect.Make(0.0, progress) if progress < 1.0 else None
        d = skia.DashPathEffect.Make([cam.m(dash[0]), cam.m(dash[1])], 0) if dash else None
        eff = skia.PathEffect.MakeCompose(d, trim) if (d and trim) else (d or trim)
        if eff: q.setPathEffect(eff)
        canvas.drawPath(path, q)
        if arrow:
            c = skia.PathMeasure(path, False)
            if c.getLength() > 0:
                L = c.getLength() * min(1.0, progress)
                pos, tan = c.getPosTan(max(0.01, L))
                a = math.atan2(tan.y(), tan.x()); s = cam.m(26)
                tri = skia.Path()
                tri.moveTo(pos.x() + math.cos(a) * s, pos.y() + math.sin(a) * s)
                tri.lineTo(pos.x() + math.cos(a + 2.5) * s * 0.8, pos.y() + math.sin(a + 2.5) * s * 0.8)
                tri.lineTo(pos.x() + math.cos(a - 2.5) * s * 0.8, pos.y() + math.sin(a - 2.5) * s * 0.8)
                tri.close()
                f = skia.Paint(AntiAlias=True); f.setColor4f(hexc(color, alpha))
                canvas.drawPath(tri, f)
        canvas.restore()

# ---------------------------------------------------------------- markers, labels, chrome
def city(canvas, cam, xy, name, alpha=1.0, size=36, side="right", capital=False, sub=None, dx=0, dy=0,
         ring=None):
    if alpha <= 0.003:
        return
    x, y = cam.px(*xy)
    p = skia.Paint(AntiAlias=True)
    r = 9 if capital else 7
    p.setColor4f(hexc(STYLE["halo"], alpha * 0.9)); canvas.drawCircle(x, y, r + 3.5, p)
    p.setColor4f(hexc(STYLE["ink"], alpha)); canvas.drawCircle(x, y, r, p)
    p.setColor4f(hexc(STYLE["paper"], alpha)); canvas.drawCircle(x, y, r - 2.6, p)
    p.setColor4f(hexc(STYLE["ink"], alpha)); canvas.drawCircle(x, y, 2.6 if not capital else 3.4, p)
    if ring is not None:  # outlined ring for special status (e.g. "not annexed"), ring = (radius, dashed)
        q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.0)
        q.setColor4f(hexc("#8A3B2E", alpha))
        if ring[1]: q.setPathEffect(skia.DashPathEffect.Make([7, 6], 0))
        canvas.drawCircle(x, y, ring[0], q)
    ft = font("sans", size)
    off = 18 + (ring[0] - 8 if ring else 0)
    tx = x + off + dx if side == "right" else x - off + dx if side == "left" else x + dx
    al = "left" if side == "right" else "right" if side == "left" else "center"
    ty = y + size * 0.34 + dy if side in ("left", "right") else (y - 22 + dy if side == "above" else y + size + 14 + dy)
    draw_text(canvas, name, tx, ty, ft, STYLE["label"], alpha, 0.01, al, halo=STYLE["halo"], halo_w=8)
    if sub:
        draw_text(canvas, sub, tx, ty + size * 0.95, font("sans_italic", size * 0.72), STYLE["ink_soft"], alpha,
                  0.0, al, halo=STYLE["halo"], halo_w=6)

def region_label(canvas, cam, xy, lines, alpha=1.0, size=40, color=None, tracking=0.12, kind="caps",
                 rise=0.0, line_gap=1.12):
    if alpha <= 0.003:
        return
    x, y = cam.px(*xy)
    ft = font(kind, size)
    n = len(lines)
    for i, ln in enumerate(lines):
        yy = y + (i - (n - 1) / 2) * size * line_gap + size * 0.35
        draw_text(canvas, ln, x, yy, ft, color or STYLE["label"], alpha, tracking, "center",
                  halo=STYLE["halo"], halo_w=7, rise=rise)

def water_label(canvas, cam, xy, lines, alpha=1.0, size=44, tracking=0.28):
    region_label(canvas, cam, xy, lines, alpha, size, STYLE["water_label"], tracking, "serif_italic")

def title_block(canvas, date, title, alpha=1.0, y=330, sub=None, date_size=150, rise=0.0, light=False,
                title_alpha=None, sub_alpha=None):
    """Top title zone (y 220–560): big date, ornament rule, chapter title. light=True for dark backgrounds."""
    if alpha <= 0.003:
        return
    ink = "#F3EAD7" if light else STYLE["ink"]
    halo = None if light else STYLE["halo"]
    soft = "#D9CBB0" if light else STYLE["ink_soft"]
    ta = alpha if title_alpha is None else title_alpha
    sa = alpha if sub_alpha is None else sub_alpha
    if date:
        draw_text(canvas, date, W / 2, y, font("display_bold", date_size), ink, alpha, 0.04, halo=halo,
                  halo_w=10, rise=rise)
    ry = y + 42
    p = skia.Paint(AntiAlias=True, StrokeWidth=2); p.setColor4f(hexc(ink, 0.75 * alpha))
    canvas.drawLine(W / 2 - 250, ry, W / 2 - 22, ry, p); canvas.drawLine(W / 2 + 22, ry, W / 2 + 250, ry, p)
    d = skia.Path(); d.moveTo(W / 2, ry - 9); d.lineTo(W / 2 + 9, ry); d.lineTo(W / 2, ry + 9); d.lineTo(W / 2 - 9, ry); d.close()
    q = skia.Paint(AntiAlias=True); q.setColor4f(hexc(ink, 0.85 * alpha)); canvas.drawPath(d, q)
    yy = ry + 66
    for ln in title if isinstance(title, (list, tuple)) else [title]:
        draw_text(canvas, ln, W / 2, yy, font("caps", 50), ink, ta, 0.14, halo=halo, halo_w=9)
        yy += 62
    if sub:
        draw_text(canvas, sub, W / 2, yy + 4, font("serif_italic", 36), soft, sa, 0.0, halo=halo, halo_w=7)

def legend(canvas, items, alpha=1.0, y=1418, cols=2):
    """Bottom caption zone legend. items: [(color_or_None, label, hatch_bool)]."""
    if alpha <= 0.003:
        return
    ft = font("sans", 31)
    colw = (W - 140) / cols
    rows = math.ceil(len(items) / cols)
    bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc(STYLE["halo"], 0.78 * alpha))
    canvas.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(52, y - 40, W - 104 - 90, rows * 50 + 30), 14, 14), bg)
    for i, (col, label, hatch) in enumerate(items):
        cx = 76 + (i % cols) * (colw - 40); cy = y + (i // cols) * 50
        r = skia.Rect.MakeXYWH(cx, cy - 22, 40, 28)
        p = skia.Paint(AntiAlias=True)
        if col:
            p.setColor4f(hexc(col, alpha)); canvas.drawRect(r, p)
        if hatch:
            canvas.save(); canvas.clipRect(r)
            q = skia.Paint(AntiAlias=True, StrokeWidth=2.2); q.setColor4f(hexc(hatch if isinstance(hatch, str) else STYLE["ink"], 0.7 * alpha))
            for k in range(-30, 50, 9):
                canvas.drawLine(cx + k, cy + 6, cx + k + 28, cy - 22, q)
            canvas.restore()
        s = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.5)
        s.setColor4f(hexc(STYLE["ink"], 0.7 * alpha)); canvas.drawRect(r, s)
        draw_text(canvas, label, cx + 54, cy, ft, STYLE["ink"], alpha, 0.0, "left")

def caption(canvas, lines, alpha=1.0, y=1500, size=30):
    for i, ln in enumerate(lines):
        draw_text(canvas, ln, W / 2, y + i * size * 1.3, font("sans_italic", size), STYLE["ink_soft"], alpha, 0.0,
                  halo=STYLE["halo"], halo_w=6)

def finish(canvas, grain_i=None, paper=True, vignette=0.32, grain_alpha=0.10):
    if paper:
        p = skia.Paint(); p.setBlendMode(skia.BlendMode.kMultiply)
        canvas.drawImage(paper_texture(), 0, 0, skia.SamplingOptions(), p)
    if vignette:
        v = skia.Paint()
        v.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), H * 0.72,
                    [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 0), skia.Color(40, 28, 14, int(255 * vignette))],
                    [0.0, 0.55, 1.0]))
        canvas.drawPaint(v)
    if grain_i is not None:
        g = grain_frames()[grain_i % len(grain_frames())]
        p = skia.Paint(); p.setBlendMode(skia.BlendMode.kOverlay); p.setAlphaf(grain_alpha)
        canvas.drawImageRect(g, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)

def new_surface():
    return skia.Surface(W, H)

def save_png(surface, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    surface.makeImageSnapshot().save(path, skia.kPNG)

def frame_bytes(surface):
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).tobytes()

# ---------------------------------------------------------------- label layout (collision avoidance)
SAFE = (60, 590, 930, 1372)   # x0, y0, x1, y1 – TikTok-safe map label zone

class Layout:
    """Registers occupied rectangles; city labels choose the first free side. Decisions are cached by name
    so an animated scene keeps labels stable (compute once with the final camera)."""
    _sides = {}
    def __init__(self, scope="", safe=SAFE):
        self.rects, self.safe, self.scope = [], safe, scope
    def add(self, l, t, r, b, pad=6):
        self.rects.append((l - pad, t - pad, r + pad, b + pad))
    def overlap(self, l, t, r, b):
        s = self.safe
        out = max(0, s[0] - l) + max(0, r - s[2]) + max(0, b - s[3])
        area = sum(max(0, min(r, R[2]) - max(l, R[0])) * max(0, min(b, R[3]) - max(t, R[1])) for R in self.rects)
        return area + out * 400
    def free(self, l, t, r, b):
        s = self.safe
        if l < s[0] or r > s[2] or t < s[1] - 40 or b > s[3]:
            return False
        return not any(l < R[2] and r > R[0] and t < R[3] and b > R[1] for R in self.rects)

def _label_rect(x, y, name, size, side, sub, ring):
    ft = font("sans", size)
    w = text_width(name, ft, 0.01)
    if sub:
        w = max(w, text_width(sub, font("sans_italic", size * 0.72)))
    h = size * (1.0 + (0.95 if sub else 0))
    off = 18 + (ring[0] - 8 if ring else 0)
    if side == "right":
        return (x + off, y - size * 0.62, x + off + w, y - size * 0.62 + h)
    if side == "left":
        return (x - off - w, y - size * 0.62, x - off, y - size * 0.62 + h)
    if side == "above":
        return (x - w / 2, y - 22 - size * 0.95, x + w / 2, y - 22 - size * 0.95 + h)
    return (x - w / 2, y + 14, x + w / 2, y + 14 + h)

def place_city(canvas, cam, layout, xy, name, alpha=1.0, size=34, prefer="right", **kw):
    key = (layout.scope, name)
    x, y = cam.px(*xy)
    if key not in Layout._sides:
        order = [prefer] + [s for s in ("right", "left", "above", "below") if s != prefer]
        side, best = prefer, None
        for s in order:
            r = _label_rect(x, y, name, size, s, kw.get("sub"), kw.get("ring"))
            if layout.free(*r):
                side = s; break
            ov = layout.overlap(*r)
            if best is None or ov < best:
                best, side = ov, s
        Layout._sides[key] = side
    side = Layout._sides[key]
    layout.add(*_label_rect(x, y, name, size, side, kw.get("sub"), kw.get("ring")))
    city(canvas, cam, xy, name, alpha, size, side, **kw)

def reserve_region(layout, cam, xy, lines, size, tracking=0.12, kind="caps", line_gap=1.12):
    x, y = cam.px(*xy)
    ft = font(kind, size)
    w = max(text_width(l, ft, tracking) for l in lines)
    h = size * line_gap * len(lines)
    layout.add(x - w / 2, y - h / 2, x + w / 2, y + h / 2)

def debug_safe(canvas):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3)
    p.setColor(skia.Color(255, 0, 0, 160))
    canvas.drawRect(skia.Rect.MakeLTRB(*SAFE), p)
    p.setColor(skia.Color(255, 0, 255, 120))
    canvas.drawRect(skia.Rect.MakeLTRB(0, 0, W, 200), p); canvas.drawRect(skia.Rect.MakeLTRB(0, 1560, W, H), p)
    canvas.drawRect(skia.Rect.MakeLTRB(940, 0, W, H), p)

def graticule_geoms(project_fn, lon_range=(0, 40), lat_range=(44, 62), step=1.0):
    from shapely.geometry import LineString
    lines = []
    lo = lon_range[0]
    while lo <= lon_range[1]:
        lines.append(LineString([project_fn(lo, la / 4) for la in range(int(lat_range[0] * 4), int(lat_range[1] * 4) + 1)]))
        lo += step
    la = lat_range[0]
    while la <= lat_range[1]:
        lines.append(LineString([project_fn(l / 4, la) for l in range(int(lon_range[0] * 4), int(lon_range[1] * 4) + 1)]))
        la += step
    return MultiLineString(lines)

def draw_graticule(atlas_map, canvas, cam, geom, alpha=1.0):
    canvas.save(); canvas.concat(cam.matrix())
    q = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.m(1.0))
    q.setColor4f(hexc("#5E5040", 0.16 * alpha))
    canvas.drawPath(atlas_map.path("graticule", geom, cam.m(0.8)), q)
    canvas.restore()
