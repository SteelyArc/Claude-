"""Premium historical-atlas renderer (Skia) for a 1080x1920 vertical frame.

World coordinates: LAEA metres (see prep_layers.py). A Camera maps world -> screen.
Everything is drawn as vectors each frame, so camera moves stay razor sharp.
"""
import os, pickle, math, functools
import numpy as np
import skia
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, box

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1920
TO_XY = Transformer.from_crs('EPSG:4326', '+proj=laea +lat_0=52 +lon_0=24 +datum=WGS84 +units=m', always_xy=True)

# ------------------------------------------------------------------ palette
def C(hexs, a=1.0):
    hexs = hexs.lstrip('#'); r, g, b = (int(hexs[i:i + 2], 16) for i in (0, 2, 4))
    return skia.Color4f(r / 255, g / 255, b / 255, a)

PAL = {
    'paper': '#EFE5CF', 'paper_dark': '#D9C9A6', 'ink': '#3B2E22', 'ink_soft': '#6B5843',
    'sea': '#C3CEC8', 'sea_line': '#7D9692', 'river': '#7F9AA2', 'lake': '#BFCBC6',
    'neutral': '#E4D9C0', 'neutral2': '#DCD0B5', 'venice': '#C3B4C6', 'venice_edge': '#7E6886', 'ragusa': '#D3C2A6',
    'plt': '#DDB86F', 'plt_edge': '#9C7426',
    'russia': '#A5B28C', 'russia_edge': '#5C6E45',
    'prussia': '#8FA2B6', 'prussia_edge': '#46607A',
    'austria': '#C6A59A', 'austria_edge': '#8A5546',
    'ottoman': '#D8CBA8', 'ottoman_edge': '#9A8A63',
    'gold': '#8A6A2E', 'accent': '#7A3B2E',
}

def lighten(hexs, f):
    c = C(hexs); p = C(PAL['paper'])
    return skia.Color4f(c.fR + (p.fR - c.fR) * f, c.fG + (p.fG - c.fG) * f, c.fB + (p.fB - c.fB) * f, 1)

def darken(hexs, f):
    c = C(hexs); return skia.Color4f(c.fR * (1 - f), c.fG * (1 - f), c.fB * (1 - f), 1)

# ------------------------------------------------------------------ fonts
FONTS = os.path.join(ROOT, 'assets', 'fonts')

@functools.lru_cache(None)
def typeface(name, wght=None):
    tf = skia.Typeface.MakeFromFile(os.path.join(FONTS, name))
    if wght is not None:
        try:
            coord = skia.FontArguments.VariationPosition.Coordinate(skia.FourByteTag('wght'), float(wght))
            pos = skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates([coord]))
            args = skia.FontArguments(); args.setVariationDesignPosition(pos)
            tf = tf.makeClone(args)
        except Exception:
            pass
    return tf

def font(kind, size):
    spec = {'serif': ('CormorantGaramond[wght].ttf', 600), 'serif_light': ('CormorantGaramond[wght].ttf', 450),
            'serif_bold': ('CormorantGaramond[wght].ttf', 700), 'italic': ('CormorantGaramond-Italic[wght].ttf', 500),
            'caps': ('Cinzel[wght].ttf', 500), 'caps_bold': ('Cinzel[wght].ttf', 700),
            'body': ('EBGaramond[wght].ttf', 500), 'body_italic': ('EBGaramond-Italic[wght].ttf', 450)}[kind]
    f = skia.Font(typeface(*spec), size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    return f

def text_width(s, f, tracking=0.0):
    return f.measureText(s) + tracking * f.getSize() * max(len(s) - 1, 0)

def draw_text(cv, s, x, y, f, color, align='left', tracking=0.0, halo=None, halo_w=6, alpha=1.0, shadow=False):
    """Draw text with optional letter tracking (em fraction) and parchment halo."""
    w = text_width(s, f, tracking)
    x0 = x - (w / 2 if align == 'center' else w if align == 'right' else 0)
    def run(paint):
        if tracking == 0:
            cv.drawString(s, x0, y, f, paint); return
        cx = x0
        for ch in s:
            cv.drawString(ch, cx, y, f, paint); cx += f.measureText(ch) + tracking * f.getSize()
    if shadow:
        p = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.12, 0.08, 0.04, 0.45 * alpha),
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
        cv.save(); cv.translate(0, 3); run(p); cv.restore()
    if halo is not None:
        hc = halo if isinstance(halo, skia.Color4f) else C(halo)
        run(skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=halo_w, StrokeJoin=skia.Paint.kRound_Join,
                       Color4f=skia.Color4f(hc.fR, hc.fG, hc.fB, hc.fA * alpha * 0.9)))
    col = color if isinstance(color, skia.Color4f) else C(color)
    run(skia.Paint(AntiAlias=True, Color4f=skia.Color4f(col.fR, col.fG, col.fB, col.fA * alpha)))
    return w

# ------------------------------------------------------------------ geometry -> skia paths
def _ring(path, coords):
    it = iter(coords); x, y = next(it); path.moveTo(x, y)
    for x, y in it: path.lineTo(x, y)
    path.close()

def to_path(g):
    p = skia.Path(); p.setFillType(skia.PathFillType.kEvenOdd)
    if g is None or g.is_empty: return p
    for poly in getattr(g, 'geoms', [g]):
        if poly.geom_type == 'Polygon':
            _ring(p, poly.exterior.coords)
            for r in poly.interiors: _ring(p, r.coords)
        elif poly.geom_type in ('LineString', 'LinearRing'):
            cs = list(poly.coords); p.moveTo(*cs[0]); [p.lineTo(*c) for c in cs[1:]]
        elif poly.geom_type == 'MultiLineString' or poly.geom_type == 'GeometryCollection':
            for sub in poly.geoms:
                q = to_path(sub); p.addPath(q)
    return p

@functools.lru_cache(None)
def layers():
    L = pickle.load(open(os.path.join(ROOT, 'data', 'layers.pkl'), 'rb'))
    cache = os.path.join(ROOT, 'data', 'coast_ripples.pkl')
    if os.path.exists(cache):
        L['ripples'] = pickle.load(open(cache, 'rb'))
    else:
        land = L['land'].simplify(1500)
        rip = [(d, land.buffer(d * 1000, 8).boundary.simplify(600)) for d in (5, 11, 18, 27, 38)]
        pickle.dump(rip, open(cache, 'wb')); L['ripples'] = rip
    return L

class PathCache(dict):
    def get_path(self, key, geom):
        if key not in self: self[key] = to_path(geom)
        return self[key]
    def get_ext(self, key, geom):
        k = key + '__ext'
        if k not in self:
            from shapely.geometry import Polygon as _P
            from shapely.ops import unary_union as _u
            polys = [_P(q.exterior) for q in getattr(geom, 'geoms', [geom]) if q.geom_type == 'Polygon' and q.area > 4e8]
            self[k] = to_path(_u(polys) if polys else geom)
        return self[k]
PATHS = PathCache()

def xy(lon, lat):
    return TO_XY.transform(lon, lat)

# ------------------------------------------------------------------ camera
class Camera:
    def __init__(self, cx, cy, scale, rot=0.0):
        self.cx, self.cy, self.scale, self.rot = cx, cy, scale, rot   # scale = px per km
    @classmethod
    def lonlat(cls, lon, lat, scale, rot=0.0, dy_px=0):
        x, y = xy(lon, lat); cam = cls(x, y, scale, rot); cam.cy += dy_px / scale * 1000; return cam
    def apply(self, cv):
        cv.translate(W / 2, H / 2); cv.rotate(self.rot); s = self.scale / 1000.0
        cv.scale(s, -s); cv.translate(-self.cx, -self.cy)
    def to_screen(self, x, y):
        s = self.scale / 1000.0; dx, dy = (x - self.cx) * s, -(y - self.cy) * s
        a = math.radians(self.rot); return (W / 2 + dx * math.cos(a) - dy * math.sin(a), H / 2 + dx * math.sin(a) + dy * math.cos(a))
    def px(self, n):  # n screen pixels expressed in world units
        return n * 1000.0 / self.scale
    @staticmethod
    def lerp(a, b, t):
        # zoom interpolated in log space for perceptually even camera moves
        ls = math.log(a.scale) + (math.log(b.scale) - math.log(a.scale)) * t
        return Camera(a.cx + (b.cx - a.cx) * t, a.cy + (b.cy - a.cy) * t, math.exp(ls), a.rot + (b.rot - a.rot) * t)

def ease(t):  # smooth cinematic ease-in-out
    t = min(max(t, 0.0), 1.0); return t * t * t * (t * (6 * t - 15) + 10)

# ------------------------------------------------------------------ textures
@functools.lru_cache(None)
def parchment(seed=7, w=W + 240, h=H + 240):
    rng = np.random.default_rng(seed)
    def noise(scale):
        sm = rng.random((h // scale + 2, w // scale + 2)).astype(np.float32)
        img = skia.Image.fromarray((sm * 255).astype(np.uint8), colorType=skia.kGray_8_ColorType)
        surf = skia.Surface(w, h); c = surf.getCanvas()
        c.drawImageRect(img, skia.Rect(0, 0, w, h), skia.SamplingOptions(skia.FilterMode.kLinear))
        return surf.makeImageSnapshot().toarray()[..., 0].astype(np.float32) / 255
    n = 0.45 * noise(240) + 0.3 * noise(90) + 0.17 * noise(28) + 0.08 * noise(6)
    fib = rng.random((h, w)).astype(np.float32)
    v = (n - 0.5) * 0.10 + (fib - 0.5) * 0.035
    base = np.array([239, 229, 207], np.float32) / 255
    stain = np.array([0.93, 0.88, 0.80], np.float32)
    rgb = np.clip(base[None, None, :] * (1 + v[..., None]) * (1 - 0.06 * (n[..., None] > 0.62) * (1 - stain)), 0, 1)
    a = np.dstack([rgb, np.ones((h, w, 1), np.float32)])
    return skia.Image.fromarray((a * 255).astype(np.uint8), colorType=skia.kRGBA_8888_ColorType)

@functools.lru_cache(None)
def grain(seed):
    rng = np.random.default_rng(seed); g = (rng.normal(0.5, 0.18, (H // 2, W // 2)).clip(0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([g, g, g, np.full_like(g, 255)])
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)

# ------------------------------------------------------------------ drawing primitives (world space)
def fill(cv, path, color, alpha=1.0):
    col = color if isinstance(color, skia.Color4f) else C(color)
    cv.drawPath(path, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(col.fR, col.fG, col.fB, col.fA * alpha)))

def ribbon(cv, cam, path, color, width_px=16, alpha=0.55, blur_px=5):
    """Hand-coloured atlas edge: a soft band of darker tint inside the polygon edge."""
    if alpha <= 0: return
    col = color if isinstance(color, skia.Color4f) else C(color)
    cv.save(); cv.clipPath(path, skia.ClipOp.kIntersect, True)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.px(width_px), StrokeJoin=skia.Paint.kRound_Join,
                   Color4f=skia.Color4f(col.fR, col.fG, col.fB, alpha),
                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur_px, False))
    cv.drawPath(path, p); cv.restore()

def stroke(cv, cam, path, color, width_px=1.4, alpha=1.0, dash=None, cap=skia.Paint.kRound_Cap):
    col = color if isinstance(color, skia.Color4f) else C(color)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.px(width_px), StrokeJoin=skia.Paint.kRound_Join,
                   StrokeCap=cap, Color4f=skia.Color4f(col.fR, col.fG, col.fB, col.fA * alpha))
    if dash: p.setPathEffect(skia.DashPathEffect.Make([cam.px(d) for d in dash], 0))
    cv.drawPath(path, p)

def hatch(cv, cam, path, color, spacing_px=11, width_px=1.3, alpha=0.5, angle=45, phase=0.0, reveal=1.0):
    """Diagonal engraving hatch clipped to the polygon (screen-space spacing). reveal sweeps it in."""
    if alpha <= 0 or reveal <= 0: return
    col = color if isinstance(color, skia.Color4f) else C(color)
    b = path.computeTightBounds()
    cv.save(); cv.clipPath(path, skia.ClipOp.kIntersect, True)
    sp = cam.px(spacing_px); diag = math.hypot(b.width(), b.height())
    cxw, cyw = b.centerX(), b.centerY(); a = math.radians(angle)
    hp = skia.Path(); n = int(diag / sp) + 2
    ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    for i in range(-n // 2 - 1, n // 2 + 1):
        if (i + n / 2) / n > reveal: continue
        ox, oy = cxw + nx * (i * sp + phase * sp), cyw + ny * (i * sp + phase * sp)
        hp.moveTo(ox - ux * diag, oy - uy * diag); hp.lineTo(ox + ux * diag, oy + uy * diag)
    cv.drawPath(hp, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.px(width_px),
                               Color4f=skia.Color4f(col.fR, col.fG, col.fB, alpha)))
    cv.restore()

# ------------------------------------------------------------------ base map
def draw_base(cv, cam, t=0.0):
    L = layers()
    # sea everywhere, then engraved coastal ripples, then land
    cv.save(); cam.apply(cv)
    fill(cv, PATHS.get_path('worldbox', box(-3e6, -3e6, 3e6, 3e6)), PAL['sea'])
    for i, (d, g) in enumerate(L['ripples']):
        stroke(cv, cam, PATHS.get_path(f'rip{d}', g), PAL['sea_line'], width_px=1.0, alpha=0.42 - i * 0.07)
    land = PATHS.get_path('land', L['land'])
    fill(cv, land, PAL['paper'])
    cv.restore()

def draw_paper_texture(cv, t=0.0, alpha=0.55, drift=(0, 0)):
    img = parchment()
    p = skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=alpha)
    cv.drawImage(img, -120 + drift[0], -120 + drift[1], skia.SamplingOptions(skia.FilterMode.kLinear), p)

def draw_physical_overlay(cv, cam):
    L = layers(); cv.save(); cam.apply(cv)
    fill(cv, PATHS.get_path('lakes', L['lakes']), PAL['lake'])
    stroke(cv, cam, PATHS.get_path('lakes', L['lakes']), PAL['sea_line'], 0.8, 0.6)
    for r in L['rivers']:
        w = {0: 2.2, 1: 2.2, 2: 2.0, 3: 1.8, 4: 1.6, 5: 1.4, 6: 1.2, 7: 1.0, 8: 0.9}.get(r['rank'], 0.9)
        stroke(cv, cam, PATHS.get_path('riv' + str(id(r['geom'])), r['geom']), PAL['river'], w, 0.85)
    cv.restore()

def minor_state_labels(cv, cam, alpha=0.9):
    """Small labels for minor states on the Adriatic, visible in the lower-left of wide frames."""
    x, y = cam.to_screen(*xy(16.55, 43.75))
    if -200 < x < W + 200 and -200 < y < H + 200:
        cv.save(); cv.translate(x, y); cv.rotate(46)
        draw_text(cv, 'VENICE', 0, 0, font('caps', 17), C(PAL['venice_edge']), align='center', tracking=0.25, alpha=alpha,
                  halo=skia.Color4f(0.95, 0.91, 0.82, 0.4), halo_w=4)
        cv.restore()

def coast_line(cv, cam):
    L = layers(); cv.save(); cam.apply(cv)
    stroke(cv, cam, PATHS.get_path('land', L['land']), '#5E716E', 1.1, 0.85)
    cv.restore()
    minor_state_labels(cv, cam)

def vignette(cv, strength=0.55):
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.46), H * 0.72,
                                        [skia.Color4f(0, 0, 0, 0), skia.Color4f(0.18, 0.11, 0.05, strength)], [0.55, 1.0])
    cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))
    # warm light from upper left
    sh2 = skia.GradientShader.MakeRadial(skia.Point(W * 0.25, H * 0.18), H * 0.8,
                                         [skia.Color4f(1, 0.93, 0.78, 0.16), skia.Color4f(1, 0.93, 0.78, 0)], [0, 1])
    cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh2, BlendMode=skia.BlendMode.kScreen))

def film_grain(cv, frame=0, alpha=0.06):
    cv.drawImageRect(grain(frame % 8), skia.Rect(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear),
                     skia.Paint(BlendMode=skia.BlendMode.kOverlay, Alphaf=alpha))

# ------------------------------------------------------------------ cartographic symbols
def city(cv, cam, lon, lat, name, kind='town', dx=14, dy=8, align='left', size=30, alpha=1.0, color=None, sub=None):
    x, y = cam.to_screen(*xy(lon, lat))
    ink = C(color or PAL['ink'])
    if kind == 'capital':
        cv.drawCircle(x, y, 9, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.94, 0.9, 0.81, alpha)))
        cv.drawCircle(x, y, 9, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.2, Color4f=skia.Color4f(ink.fR, ink.fG, ink.fB, alpha)))
        cv.drawCircle(x, y, 4.2, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(ink.fR, ink.fG, ink.fB, alpha)))
    else:
        cv.drawCircle(x, y, 6.5, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.94, 0.9, 0.81, alpha)))
        cv.drawCircle(x, y, 6.5, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.0, Color4f=skia.Color4f(ink.fR, ink.fG, ink.fB, alpha)))
    if name:
        f = font('serif_bold' if kind == 'capital' else 'serif', size)
        tx = x + (dx if align == 'left' else -dx if align == 'right' else 0)
        draw_text(cv, name, tx, y + dy, f, ink, align=align, halo=PAL['paper'], halo_w=7, alpha=alpha)
        if sub:
            draw_text(cv, sub, tx, y + dy + size * 0.9, font('italic', size * 0.78), PAL['ink_soft'], align=align, halo=PAL['paper'], halo_w=6, alpha=alpha)
    return x, y

def region_label(cv, cam, lon, lat, text, color, size=34, tracking=0.22, alpha=0.85, lines=None, rot=0):
    x, y = cam.to_screen(*xy(lon, lat)); f = font('caps', size)
    rows = lines or [text]
    cv.save(); cv.translate(x, y); cv.rotate(rot)
    for i, r in enumerate(rows):
        draw_text(cv, r, 0, (i - (len(rows) - 1) / 2) * size * 1.25 + size * 0.35, f, color, align='center', tracking=tracking,
                  halo=skia.Color4f(0.95, 0.91, 0.82, 0.30), halo_w=4, alpha=alpha)
    cv.restore()

def water_label(cv, cam, lon, lat, text, size=34, rot=0, alpha=0.8, tracking=0.25):
    x, y = cam.to_screen(*xy(lon, lat)); cv.save(); cv.translate(x, y); cv.rotate(rot)
    draw_text(cv, text, 0, 0, font('italic', size), '#4F6966', align='center', tracking=tracking, alpha=alpha); cv.restore()

def event_marker(cv, cam, lon, lat, num, label, date, side='right', alpha=1.0, pulse=0.0, battle=False):
    x, y = cam.to_screen(*xy(lon, lat)); acc = C(PAL['accent'])
    if pulse > 0:
        r = 14 + 40 * pulse
        cv.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.5,
                                          Color4f=skia.Color4f(acc.fR, acc.fG, acc.fB, (1 - pulse) * 0.8 * alpha)))
    cv.drawCircle(x, y, 17, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.97, 0.94, 0.86, alpha)))
    cv.drawCircle(x, y, 17, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.6, Color4f=skia.Color4f(acc.fR, acc.fG, acc.fB, alpha)))
    if battle:  # crossed sabres glyph (simple, cartographic)
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.6, StrokeCap=skia.Paint.kRound_Cap, Color4f=skia.Color4f(acc.fR, acc.fG, acc.fB, alpha))
        cv.drawLine(x - 8, y - 8, x + 8, y + 8, p); cv.drawLine(x + 8, y - 8, x - 8, y + 8, p)
    else:
        draw_text(cv, str(num), x, y + 8.5, font('serif_bold', 25), acc, align='center', alpha=alpha)
    f1, f2 = font('serif_bold', 31), font('italic', 26)
    al = 'left' if side == 'right' else 'right'; tx = x + (28 if side == 'right' else -28)
    draw_text(cv, label, tx, y + 2, f1, PAL['ink'], align=al, halo=PAL['paper'], halo_w=7, alpha=alpha)
    draw_text(cv, date, tx, y + 29, f2, acc, align=al, halo=PAL['paper'], halo_w=6, alpha=alpha)

# ------------------------------------------------------------------ frame furniture
def title_block(cv, year, title, subtitle=None, alpha=1.0, y0=190):
    gold = C(PAL['gold'])
    # top shade so the title reads over the map
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, y0 + 260)],
                                        [skia.Color4f(0.94, 0.9, 0.8, 0.94 * alpha), skia.Color4f(0.94, 0.9, 0.8, 0)], [0.55, 1.0])
    cv.drawRect(skia.Rect(0, 0, W, y0 + 260), skia.Paint(Shader=sh))
    draw_text(cv, year, W / 2, y0, font('caps', 40), gold, align='center', tracking=0.45, alpha=alpha)
    lp = skia.Paint(AntiAlias=True, StrokeWidth=1.6, Color4f=skia.Color4f(gold.fR, gold.fG, gold.fB, 0.8 * alpha))
    tw = text_width(year, font('caps', 40), 0.45)
    cv.drawLine(W / 2 - tw / 2 - 120, y0 - 13, W / 2 - tw / 2 - 26, y0 - 13, lp)
    cv.drawLine(W / 2 + tw / 2 + 26, y0 - 13, W / 2 + tw / 2 + 120, y0 - 13, lp)
    draw_text(cv, title, W / 2, y0 + 82, font('serif_bold', 74), PAL['ink'], align='center', alpha=alpha, shadow=False)
    if subtitle:
        draw_text(cv, subtitle, W / 2, y0 + 134, font('italic', 38), PAL['ink_soft'], align='center', alpha=alpha)

def legend(cv, items, x=70, y=1385, alpha=1.0, title=None):
    """items: list of (label, fill_hex, hatch_bool). Card sits above the TikTok caption safe zone."""
    rowh = 52; hh = (50 if title else 0); h = 34 + rowh * len(items) + hh; w = 620
    card = skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + h), 14, 14)
    cv.drawRRect(card, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.12, 0.08, 0.04, 0.22 * alpha),
                                  MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
    cv.drawRRect(card, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.96, 0.93, 0.85, 0.93 * alpha)))
    g = C(PAL['gold'])
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x + 7, y + 7, x + w - 7, y + h - 7), 10, 10),
                 skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.3, Color4f=skia.Color4f(g.fR, g.fG, g.fB, 0.7 * alpha)))
    yy = y + 30
    if title:
        draw_text(cv, title, x + 32, yy + 18, font('caps', 24), PAL['gold'], tracking=0.25, alpha=alpha); yy += hh
    for lab, col, hat in items:
        r = skia.Rect(x + 32, yy, x + 92, yy + 34)
        cc = col if isinstance(col, skia.Color4f) else C(col)
        cv.drawRect(r, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(cc.fR, cc.fG, cc.fB, alpha)))
        if hat:
            cv.save(); cv.clipRect(r)
            hc = hat if isinstance(hat, skia.Color4f) else skia.Color4f(cc.fR * .55, cc.fG * .55, cc.fB * .55, 1)
            p = skia.Paint(AntiAlias=True, StrokeWidth=1.4, Color4f=skia.Color4f(hc.fR, hc.fG, hc.fB, 0.6 * alpha))
            for k in range(-4, 12): cv.drawLine(r.left() + k * 9, r.bottom(), r.left() + k * 9 + 34, r.top(), p)
            cv.restore()
        cv.drawRect(r, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.3, Color4f=C(PAL['ink'], 0.7 * alpha)))
        draw_text(cv, lab, x + 110, yy + 27, font('serif', 31), PAL['ink'], alpha=alpha)
        yy += rowh

def source_line(cv, text, alpha=0.8):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, H - 120), skia.Point(0, H)], [skia.Color4f(0.94, 0.9, 0.8, 0), skia.Color4f(0.94, 0.9, 0.8, 0.85)], [0, 1])
    cv.drawRect(skia.Rect(0, H - 120, W, H), skia.Paint(Shader=sh))
    draw_text(cv, text, W / 2, H - 30, font('body_italic', 19), PAL['ink_soft'], align='center', alpha=alpha)

def plate_frame(cv, alpha=1.0):
    g = C(PAL['gold'])
    for inset, wdt in ((26, 2.0), (34, 0.9)):
        cv.drawRect(skia.Rect(inset, inset, W - inset, H - inset),
                    skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=wdt, Color4f=skia.Color4f(g.fR, g.fG, g.fB, 0.55 * alpha)))

def new_surface():
    return skia.Surface(W, H)

def save_png(surface, path):
    surface.makeImageSnapshot().save(path, skia.kPNG)
