"""Core rendering engine: camera, cartographic layers, motion primitives, typography, finishing.
All drawing via skia (CPU raster). World units = km in LAEA(52N, 22E)."""
import math, json, pickle, functools, numpy as np, skia
from PIL import Image
from scipy import ndimage
import shapely, shapely.geometry.polygon
from shapely.geometry import Point

W, H, FPS = 1080, 1920, 30
ROOT = '/home/user/Claude-/partition1772/'
D = ROOT + 'data/'
FONTS = ROOT + 'assets/fonts/'
Image.MAX_IMAGE_PIXELS = None

# ------------------------------------------------------------------ palette
def C(r, g, b, a=255): return skia.Color(int(r), int(g), int(b), int(a))
PAL = {
    'plc': (214, 186, 124),      # muted golden beige
    'prussia': (98, 124, 152),   # desaturated blue
    'russia': (168, 88, 66),     # muted terracotta
    'austria': (186, 128, 42),   # soft ochre (deeper, more orange than the Commonwealth beige)
    'neutral': (186, 192, 170),  # pale grey-green
    'ink': (58, 44, 30),
    'paper': (239, 231, 213),
    'gold': (176, 140, 74),
    'water_ink': (88, 112, 120),
}

# ------------------------------------------------------------------ easing
def clamp(x, a=0., b=1.): return a if x < a else b if x > b else x
def lerp(a, b, t): return a + (b - a) * t
def smooth(t): t = clamp(t); return t * t * (3 - 2 * t)
def smoother(t): t = clamp(t); return t * t * t * (t * (t * 6 - 15) + 10)
def ease_out_cubic(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in_cubic(t): t = clamp(t); return t ** 3
def ease_out_expo(t): t = clamp(t); return 1 if t >= 1 else 1 - 2 ** (-10 * t)
def ease_in_out_sine(t): t = clamp(t); return -(math.cos(math.pi * t) - 1) / 2
def ease_out_back(t, s=1.4): t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1
def ease_in_out_quint(t):
    t = clamp(t); return 16 * t ** 5 if t < .5 else 1 - (-2 * t + 2) ** 5 / 2
def ramp(t, a, b, f=smoother):
    """0 before a, 1 after b, eased in between."""
    if b <= a: return 1.0 if t >= a else 0.0
    return f(clamp((t - a) / (b - a)))
def window(t, a, b, fi=0.6, fo=0.6):
    return ramp(t, a, a + fi) * (1 - ramp(t, b - fo, b))

# ------------------------------------------------------------------ fonts
@functools.lru_cache(None)
def tf(name): return skia.Typeface.MakeFromFile(FONTS + name)
@functools.lru_cache(None)
def font(name, size):
    f = skia.Font(tf(name), size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kSubpixelAntiAlias); return f

SERIF = 'CG-SemiBold.ttf'; SERIF_M = 'CG-Medium.ttf'; SERIF_B = 'CG-Bold.ttf'; SERIF_I = 'CG-MediumItalic.ttf'
SC = 'CormorantSC-SemiBold.ttf'; SC_M = 'CormorantSC-Medium.ttf'
BODY = 'EBG-Medium.ttf'; BODY_I = 'EBG-Italic.ttf'; BODY_SB = 'EBG-SemiBold.ttf'
CAPS = 'Cinzel-Medium.ttf'; CAPS_B = 'Cinzel-Bold.ttf'

def text_width(s, f, tracking=0.0):
    if not s: return 0
    ws = f.getWidths(f.textToGlyphs(s))
    return sum(ws) + tracking * f.getSize() * (len(s) - 1)

def draw_text(c, s, x, y, f, color, align='center', tracking=0.0, alpha=1.0, halo=None, halo_w=0,
              reveal=1.0, stagger=0.6, rise=0.0, shadow=None):
    """Glyph-by-glyph text with tracking, per-letter staggered reveal (fade + rise), optional halo/shadow."""
    if alpha <= 0.003 or not s: return
    gl = f.textToGlyphs(s); ws = f.getWidths(gl)
    tw = sum(ws) + tracking * f.getSize() * (len(s) - 1)
    x0 = x - tw / 2 if align == 'center' else x - tw if align == 'right' else x
    n = len(s); xs = []; cx = x0
    for i in range(n):
        xs.append(cx); cx += ws[i] + tracking * f.getSize()
    def letters(paint_fn):
        for i, ch in enumerate(s):
            if ch == ' ': continue
            if reveal >= 1: a, dy = 1.0, 0.0
            else:
                st = (i / max(1, n - 1)) * stagger
                lt = clamp((reveal * (1 + stagger) - st) / 1.0)
                a = ease_out_cubic(lt); dy = (1 - a) * rise
            if a <= 0: continue
            paint_fn(ch, xs[i], y + dy, a)
    if shadow:
        sp = skia.Paint(AntiAlias=True, Color=shadow[0], MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow[1]))
        def fs(ch, px, py, a):
            sp.setAlphaf(clamp(a * alpha * skia.Color4f(shadow[0]).fA)); c.drawString(ch, px + shadow[2], py + shadow[3], f, sp)
        letters(fs)
    if halo is not None and halo_w > 0:
        hp = skia.Paint(AntiAlias=True, Color=halo, Style=skia.Paint.kStroke_Style, StrokeWidth=halo_w, StrokeJoin=skia.Paint.kRound_Join)
        base_a = skia.Color4f(halo).fA
        def fh(ch, px, py, a):
            hp.setAlphaf(clamp(a * alpha * base_a)); c.drawString(ch, px, py, f, hp)
        letters(fh)
    p = skia.Paint(AntiAlias=True, Color=color); ca = skia.Color4f(color).fA
    def ff(ch, px, py, a):
        p.setAlphaf(clamp(a * alpha * ca)); c.drawString(ch, px, py, f, p)
    letters(ff)
    return tw

# ------------------------------------------------------------------ geometry -> skia paths
LAYERS = pickle.load(open(D + 'layers.pkl', 'rb'))

def geom_path(g, simplify=0.25):
    p = skia.Path()
    if g is None or g.is_empty: return p
    if simplify: g = g.simplify(simplify, preserve_topology=True)
    def ring(cs, close=True):
        cs = np.asarray(cs)
        if len(cs) < 2: return
        p.moveTo(float(cs[0, 0]), float(cs[0, 1]))
        for x, y in cs[1:]: p.lineTo(float(x), float(y))
        if close: p.close()
    for part in getattr(g, 'geoms', [g]):
        t = part.geom_type
        if t == 'Polygon':
            part = shapely.geometry.polygon.orient(part, 1.0)
            ring(part.exterior.coords)
            for i in part.interiors: ring(i.coords)
        elif t == 'LineString': ring(part.coords, False)
        elif t in ('MultiPolygon', 'MultiLineString', 'GeometryCollection'):
            q = geom_path(part, 0); p.addPath(q)
    p.setFillType(skia.PathFillType.kWinding)
    return p

@functools.lru_cache(None)
def layer_path(name, simplify=0.25):
    return geom_path(LAYERS[name], simplify)

@functools.lru_cache(None)
def river_path(name):
    return geom_path(LAYERS['rivers'][name], 0.3)

def city(name): return LAYERS['cities'][name]

# ------------------------------------------------------------------ camera
class Cam:
    def __init__(self, cx, cy, scale, rot=0.0, tilt=0.0, ox=0.0, oy=0.0):
        self.cx, self.cy, self.scale, self.rot, self.tilt = cx, cy, scale, rot, tilt
        self.ox, self.oy = ox, oy   # screen-space offset of the focus point from centre

    def matrix(self, depth=1.0):
        """world -> screen. depth>1 = layer closer to viewer (parallax amplification)."""
        m = skia.Matrix()
        m.setTranslate(-self.cx, -self.cy)
        s = self.scale * depth
        m.postScale(s, -s)
        m.postRotate(self.rot)
        if abs(self.tilt) > 1e-4:
            th = math.radians(self.tilt); f = 1700.0
            P = skia.Matrix.MakeAll(1, 0, 0, 0, math.cos(th), 0, 0, -math.sin(th) / f, 1)
            m.postConcat(P)
        m.postTranslate(W / 2 + self.ox, H / 2 + self.oy)
        return m

    def to_screen(self, x, y, depth=1.0):
        return self.matrix(depth).mapXY(x, y)

def cam_lerp(a, b, t):
    # interpolate zoom in log space for perceptually uniform zooms
    s = math.exp(lerp(math.log(a.scale), math.log(b.scale), t))
    # keep the path natural: centre moves proportional to zoom change (van Wijk-lite)
    return Cam(lerp(a.cx, b.cx, t), lerp(a.cy, b.cy, t), s, lerp(a.rot, b.rot, t), lerp(a.tilt, b.tilt, t),
               lerp(a.ox, b.ox, t), lerp(a.oy, b.oy, t))

def cam_path(keys, t):
    """keys: list of (time, Cam, ease_fn). Piecewise interpolation with per-segment easing."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, c0, _), (t1, c1, e) in zip(keys, keys[1:]):
        if t <= t1:
            return cam_lerp(c0, c1, (e or ease_in_out_sine)((t - t0) / (t1 - t0)))
    return keys[-1][1]

def drift(cam, t, amp=6.0, speed=0.05, zoom=0.012):
    """Subtle continuous 'handheld crane' motion so no frame is ever static."""
    c = Cam(cam.cx, cam.cy, cam.scale, cam.rot, cam.tilt, cam.ox, cam.oy)
    c.cx += amp / c.scale * math.sin(t * speed * 2 * math.pi)
    c.cy += amp / c.scale * 0.6 * math.cos(t * speed * 1.3 * 2 * math.pi)
    c.scale *= 1 + zoom * math.sin(t * speed * 0.7 * 2 * math.pi)
    return c

# ------------------------------------------------------------------ base raster
class Base:
    def __init__(self):
        self.lv = {}
        for k in ('lo', 'hi'):
            e = json.load(open(D + f'base_{k}.json'))
            arr = np.asarray(Image.open(D + f'base_{k}.png').convert('RGBA'))
            img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).withDefaultMipmaps()
            self.lv[k] = (e, img)

    def draw(self, c, cam, alpha=1.0, depth=1.0):
        m = cam.matrix(depth)
        samp = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
        ppk = cam.scale * depth      # px per km
        # level blend: hi when >~1.6 px/km and viewport inside hi extent
        e_hi = self.lv['hi'][0]
        inv = skia.Matrix(); m.invert(inv)
        corners = [inv.mapXY(x, y) for x, y in ((0, 0), (W, 0), (0, H), (W, H))]
        inside = all(e_hi['x0'] + 5 < p.x() < e_hi['x1'] - 5 and e_hi['y0'] + 5 < p.y() < e_hi['y1'] - 5 for p in corners)
        a_hi = smooth((ppk - 1.1) / 0.6) if inside else 0.0
        for k, a in (('lo', 1.0), ('hi', a_hi)):
            if a <= 0.001: continue
            e, img = self.lv[k]
            c.save(); c.concat(m)
            r = e['res']
            c.translate(e['x0'], e['y1']); c.scale(r, -r)
            p = skia.Paint(); p.setAlphaf(alpha * a)
            c.drawImage(img, 0, 0, samp, p)
            c.restore()

# ------------------------------------------------------------------ reveal fields (organic ink-spread masks)
class RevealField:
    """Precomputed scalar field in world space: arrival time 0..1 of an ink front spreading from seeds,
    perturbed by fractal noise so the edge looks like ink soaking into paper."""
    def __init__(self, geom, seeds=None, res=2.0, noise_amp=0.10, seed=3, mode='seed', line=None):
        x0, y0, x1, y1 = geom.bounds; pad = 40
        self.x0, self.y1, self.res = x0 - pad, y1 + pad, res
        w = int((x1 - x0 + 2 * pad) / res); h = int((y1 - y0 + 2 * pad) / res)
        xs = self.x0 + (np.arange(w) + .5) * res; ys = self.y1 - (np.arange(h) + .5) * res
        X, Y = np.meshgrid(xs, ys)
        if mode == 'seed':
            d = np.full((h, w), np.inf)
            for sx, sy in seeds: d = np.minimum(d, np.hypot(X - sx, Y - sy))
        else:   # distance from a line (e.g. the new border): spread inward from the cut
            mask = np.zeros((h, w), bool)
            pts = shapely.get_coordinates(line.segmentize(res))
            ix = ((pts[:, 0] - self.x0) / res).astype(int); iy = ((self.y1 - pts[:, 1]) / res).astype(int)
            ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h); mask[iy[ok], ix[ok]] = True
            d = ndimage.distance_transform_edt(~mask) * res
        rng = np.random.default_rng(seed)
        n = np.zeros((h, w))
        for o, sc in enumerate([140, 60, 24, 9]):
            g = rng.standard_normal((h // max(1, int(sc / res)) + 3, w // max(1, int(sc / res)) + 3))
            g = ndimage.zoom(g, (h / (g.shape[0] - 2), w / (g.shape[1] - 2)), order=3)[:h, :w]
            n += g * 0.5 ** o
        n /= np.abs(n).max() + 1e-6
        d = d / (np.percentile(d[np.isfinite(d)], 99.5) + 1e-6)
        self.f = np.clip(d + noise_amp * n, 0, 1.2).astype(np.float32)
        self.w, self.h = w, h

    def mask_image(self, t, soft=0.06):
        """Alpha mask for progress t (0..1). Returns skia image (A8 as RGBA)."""
        tt = t * (1.2 + soft) - soft
        a = np.clip((tt - self.f) / soft + 1, 0, 1)
        a = a * a * (3 - 2 * a)
        return a

    def edge_band(self, t, width=0.018, soft=0.06):
        tt = t * (1.2 + soft) - soft
        return np.exp(-((self.f - tt + soft * .5) / width) ** 2) * (t < 0.999)

    def draw_masked(self, c, cam, path, color, alpha, t, edge_color=None, depth=1.0, soft=0.06, blend=skia.BlendMode.kMultiply):
        if t <= 0 or alpha <= 0: return
        m = cam.matrix(depth)
        a = self.mask_image(t, soft) if t < 1 else None
        c.saveLayer(None, skia.Paint(BlendMode=blend))
        c.save(); c.concat(m)
        p = skia.Paint(AntiAlias=True, Color=C(*color)); p.setAlphaf(alpha)
        c.drawPath(path, p)
        if a is not None and edge_color is not None:
            band = self.edge_band(t, soft=soft)
            img = _alpha_img(np.clip(band, 0, 1) * a.max())
            c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
            self._draw_alpha_as_color(c, img, edge_color, alpha * 0.45)
            c.restore()
        if a is not None:
            img = _alpha_img(a)
            c.translate(self.x0, self.y1); c.scale(self.res, -self.res)
            mp = skia.Paint(BlendMode=skia.BlendMode.kDstIn)
            c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), mp)
        c.restore(); c.restore()

    def _draw_alpha_as_color(self, c, img, color, alpha):
        c.save(); c.translate(self.x0, self.y1); c.scale(self.res, -self.res)
        p = skia.Paint(ColorFilter=skia.ColorFilters.Blend(C(*color), skia.BlendMode.kSrcIn)); p.setAlphaf(alpha)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
        c.restore()

def _alpha_img(a):
    rgba = np.zeros(a.shape + (4,), np.uint8); v = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    rgba[..., 0] = v; rgba[..., 1] = v; rgba[..., 2] = v; rgba[..., 3] = v
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)

# ------------------------------------------------------------------ territory styling
_hatch_cache = {}
def hatch_shader(color, spacing=9, width=1.6, angle=45, alpha=0.55, offset=(0, 0)):
    key = (color, spacing, width, angle, alpha)
    if key not in _hatch_cache:
        n = spacing * 8
        s = skia.Surface(n, n); cc = s.getCanvas(); cc.clear(skia.ColorTRANSPARENT)
        p = skia.Paint(AntiAlias=True, Color=C(*color), StrokeWidth=width, Style=skia.Paint.kStroke_Style); p.setAlphaf(alpha)
        for k in range(-n, 2 * n, spacing):
            cc.drawLine(k, -2, k + n + 4, n + 2, p) if angle == 45 else cc.drawLine(k, n + 2, k + n + 4, -2, p)
        _hatch_cache[key] = s.makeImageSnapshot()
    m = skia.Matrix(); m.setTranslate(offset[0] % (spacing * 8), offset[1] % (spacing * 8))
    return _hatch_cache[key].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear), m)

def fill_territory(c, cam, path, color, alpha=0.5, inner_glow=1.0, blend=skia.BlendMode.kMultiply, hatch=0.0, depth=1.0, glow_w=16):
    if alpha <= 0.002: return
    m = cam.matrix(depth)
    c.saveLayer(None, skia.Paint(BlendMode=blend))
    c.save(); c.concat(m)
    p = skia.Paint(AntiAlias=True, Color=C(*color)); p.setAlphaf(alpha)
    c.drawPath(path, p)
    c.restore()
    if inner_glow > 0:
        sp = skia.Path(path); sp.transform(m)
        c.save(); c.clipPath(sp, skia.ClipOp.kIntersect, True)
        g = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=glow_w * 2,
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow_w * 0.45))
        g.setAlphaf(clamp(alpha * 1.3 * inner_glow))
        c.drawPath(sp, g); c.restore()
    if hatch > 0:
        sp = skia.Path(path); sp.transform(m)
        o = m.mapXY(0, 0)
        hp = skia.Paint(AntiAlias=True); hp.setShader(hatch_shader(tuple(int(v * 0.75) for v in color), offset=(o.x(), o.y())))
        hp.setAlphaf(hatch)
        c.drawPath(sp, hp)
    c.restore()

def stroke_world(c, cam, path, color, width_px, alpha=1.0, dash=None, phase=0.0, glow=0.0, depth=1.0, cap=skia.Paint.kRound_Cap):
    if alpha <= 0.002: return
    m = cam.matrix(depth)
    sp = skia.Path(path); sp.transform(m)
    if glow > 0:
        g = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=width_px * 4,
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, width_px * 2.2), StrokeCap=cap)
        g.setAlphaf(alpha * glow); c.drawPath(sp, g)
    p = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=width_px,
                   StrokeJoin=skia.Paint.kRound_Join, StrokeCap=cap)
    p.setAlphaf(alpha)
    if dash: p.setPathEffect(skia.DashPathEffect.Make(dash, phase))
    c.drawPath(sp, p)

def partial_path(path, t, m=None):
    """Return the first fraction t (0..1) of a (multi-contour) path, plus the pen-tip point."""
    if m is not None:
        path = skia.Path(path); path.transform(m)
    meas = skia.PathMeasure(path, False)
    conts = []
    while True:
        L = meas.getLength()
        if L > 0: conts.append(L)
        if not meas.nextContour(): break
    total = sum(conts); target = total * clamp(t)
    out = skia.Path(); tip = None
    meas = skia.PathMeasure(path, False); acc = 0; i = 0
    while True:
        L = meas.getLength()
        if L > 0:
            if acc + L <= target:
                meas.getSegment(0, L, out, True); acc += L
            else:
                rem = target - acc
                if rem > 0:
                    meas.getSegment(0, rem, out, True)
                    pos = meas.getPosTan(rem)
                    tip = pos[0] if isinstance(pos, tuple) else None
                break
        if not meas.nextContour(): break
    return out, tip

def draw_border(c, cam, path, color, width_px, t=1.0, alpha=1.0, pen=True, double=True, glow=0.25, depth=1.0, dash=None):
    """Animated border: progressive draw along its real geographic path with a glowing pen tip."""
    if alpha <= 0.002 or t <= 0: return
    m = cam.matrix(depth)
    seg, tip = partial_path(path, t, m) if t < 1 else (skia.Path(path), None)
    if t >= 1: seg.transform(m)
    if double:
        hp = skia.Paint(AntiAlias=True, Color=C(*PAL['paper']), Style=skia.Paint.kStroke_Style, StrokeWidth=width_px + 3.0,
                        StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
        hp.setAlphaf(alpha * 0.55); c.drawPath(seg, hp)
    if glow > 0:
        g = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=width_px * 5,
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, width_px * 2.5), StrokeCap=skia.Paint.kRound_Cap)
        g.setAlphaf(alpha * glow); c.drawPath(seg, g)
    p = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=width_px,
                   StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
    p.setAlphaf(alpha)
    if dash: p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    c.drawPath(seg, p)
    if pen and tip is not None and t < 1:
        x, y = tip.x(), tip.y()
        for r, a in ((26, 0.18), (12, 0.35)):
            gp = skia.Paint(AntiAlias=True, Color=C(255, 236, 190), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r * 0.6))
            gp.setAlphaf(alpha * a); c.drawCircle(x, y, r, gp)
        dp = skia.Paint(AntiAlias=True, Color=C(*color)); dp.setAlphaf(alpha); c.drawCircle(x, y, width_px * 1.4, dp)

# ------------------------------------------------------------------ rivers
RIVER_W = {'Vistula': 2.4, 'Dnieper': 2.6, 'Western Dvina': 2.2, 'Neman': 2.0, 'Oder': 2.0, 'Dniester': 2.0, 'Danube': 2.6,
           'Western Bug': 1.7, 'San': 1.5, 'Narew': 1.4, 'Noteć': 1.3, 'Warta': 1.6, 'Pripyat': 1.8, 'Berezina': 1.5,
           'Drut': 1.3, 'Sozh': 1.4, 'Southern Bug': 1.6, 'Prut': 1.4, 'Elbe': 1.8, 'Pilica': 1.2, 'Wieprz': 1.1, 'Dunajec': 1.1,
           'Horyn': 1.2, 'Sluch': 1.1, 'Styr': 1.1, 'Desna': 1.6, 'Vilija': 1.3, 'Bzura': 1.0, 'Drwęca': 1.0, 'Łyna': 1.0,
           'Velikaya': 1.2, 'Teteriv': 1.0, 'Ros': 1.0, 'Venta': 1.2, 'Gauja': 1.1, 'Ptsich': 1.0, 'Iput': 1.0, 'Narva': 1.3,
           'Neva': 1.6, 'Tisa': 1.6, 'Morava': 1.2, 'Vah': 1.2, 'Siret': 1.3, 'Mukhavets': 1.0, 'Shchara': 1.0}
RIVER_COL = (96, 124, 134)

def draw_rivers(c, cam, t_draw=1.0, alpha=1.0, names=None, flow_t=0.0, highlight=None, hl_amount=0.0, zoom_w=1.0):
    names = names or list(RIVER_W)
    for n in names:
        if n not in LAYERS['rivers']: continue
        w = RIVER_W.get(n, 1.0) * zoom_w
        hl = hl_amount if (highlight and n in highlight) else 0.0
        path = river_path(n)
        col = tuple(int(lerp(a, b, hl)) for a, b in zip(RIVER_COL, (40, 92, 120)))
        draw_border(c, cam, path, col, w * (1 + 0.8 * hl), t=t_draw, alpha=alpha * (0.85 + 0.15 * hl), pen=False, double=False, glow=0.15 + 0.6 * hl)
        if flow_t is not None and alpha > 0.05 and t_draw >= 1:
            # flowing light: travelling dashes along the river (very subtle; stronger when highlighted)
            stroke_world(c, cam, path, (232, 244, 246), max(0.8, w * 0.55), alpha=alpha * (0.22 + 0.5 * hl),
                         dash=[6, 34], phase=-flow_t * 40)

# ------------------------------------------------------------------ markers & labels
def city_marker(c, x, y, t, color=PAL['ink'], r=7.0, pulse_t=None, capital=False, alpha=1.0):
    if t <= 0 or alpha <= 0: return
    s = ease_out_back(clamp(t * 1.5))
    a = clamp(t * 3) * alpha
    sh = skia.Paint(AntiAlias=True, Color=C(30, 20, 10), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
    sh.setAlphaf(0.35 * a); c.drawCircle(x + 1.5, y + 2.5, r * s * 1.2, sh)
    p = skia.Paint(AntiAlias=True, Color=C(*PAL['paper'])); p.setAlphaf(a); c.drawCircle(x, y, r * s * 1.25, p)
    p2 = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=2.2); p2.setAlphaf(a)
    c.drawCircle(x, y, r * s, p2)
    p3 = skia.Paint(AntiAlias=True, Color=C(*color)); p3.setAlphaf(a); c.drawCircle(x, y, r * s * (0.55 if capital else 0.42), p3)
    if capital:
        c.drawCircle(x, y, r * s * 1.6, p2)
    if pulse_t is not None and 0 < pulse_t < 1:
        rp = skia.Paint(AntiAlias=True, Color=C(*color), Style=skia.Paint.kStroke_Style, StrokeWidth=2.0)
        rp.setAlphaf(alpha * (1 - pulse_t) * 0.8); c.drawCircle(x, y, r * (1.5 + 5 * ease_out_cubic(pulse_t)), rp)

def map_label(c, x, y, s, size=44, t=1.0, color=PAL['ink'], fontname=SC, tracking=0.18, alpha=1.0, align='center', halo=True, sub=None, sub_size=None):
    if t <= 0 or alpha <= 0: return
    f = font(fontname, size)
    draw_text(c, s, x, y, f, C(*color), align=align, tracking=tracking, alpha=alpha,
              halo=C(*PAL['paper'], 210) if halo else None, halo_w=size * 0.16, reveal=t, stagger=0.8, rise=size * 0.18,
              shadow=(C(40, 25, 10, 60), 6, 0, 3) if halo else None)
    if sub:
        fs = font(BODY_I, sub_size or size * 0.55)
        draw_text(c, sub, x if align == 'center' else x, y + size * 0.82, fs, C(*color), align=align, tracking=0.02,
                  alpha=alpha * ramp(t, 0.3, 1), halo=C(*PAL['paper'], 200), halo_w=size * 0.12, reveal=clamp(t * 1.3 - 0.3), stagger=0.4)

def leader_label(c, x, y, s, dx, dy, t, size=34, color=PAL['ink'], fontname=SERIF, sub=None):
    """Label connected to a point by an animated leader line."""
    if t <= 0: return
    lt = ease_out_cubic(clamp(t * 1.6))
    ex, ey = x + dx * lt, y + dy * lt
    p = skia.Paint(AntiAlias=True, Color=C(*color), StrokeWidth=1.6); p.setAlphaf(0.85)
    c.drawLine(x, y, ex, ey, p)
    align = 'left' if dx >= 0 else 'right'
    tx = ex + (10 if dx >= 0 else -10)
    draw_text(c, s, tx, ey + size * 0.33, font(fontname, size), C(*color), align=align, tracking=0.03,
              halo=C(*PAL['paper'], 220), halo_w=size * 0.17, reveal=clamp(t * 1.4 - 0.35), stagger=0.6, rise=6)
    if sub:
        draw_text(c, sub, tx, ey + size * 0.33 + size * 0.95, font(BODY_I, size * 0.7), C(*color), align=align,
                  halo=C(*PAL['paper'], 220), halo_w=size * 0.14, reveal=clamp(t * 1.4 - 0.55), stagger=0.4)

# ------------------------------------------------------------------ finishing (screen-space)
class Finish:
    def __init__(self, seed=11):
        rng = np.random.default_rng(seed)
        # paper grain: multi-scale noise, warm, used with multiply/overlay
        g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
        g = ndimage.gaussian_filter(g, 0.6)
        fib = ndimage.gaussian_filter(rng.standard_normal((H // 2, W // 2)), (0.5, 6)) * 2.5
        big = ndimage.zoom(rng.standard_normal((12, 8)), (H / 2 / 12, W / 2 / 8), order=3)[:H // 2, :W // 2]
        v = 0.5 + 0.06 * g + 0.035 * fib + 0.05 * big
        v = ndimage.zoom(v, 2, order=1)
        rgba = np.zeros((H, W, 4), np.uint8)
        for i, k in enumerate((1.0, 0.98, 0.94)): rgba[..., i] = np.clip(v * 255 * k + (1 - k) * 60, 0, 255)
        rgba[..., 3] = 255
        self.grain = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)
        # film grain frames (animated, very fine)
        self.film = []
        for i in range(8):
            n = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
            n = (np.clip(0.5 + 0.18 * n, 0, 1) * 255).astype(np.uint8)
            a = np.stack([n, n, n, np.full_like(n, 255)], -1)
            self.film.append(skia.Image.fromarray(np.ascontiguousarray(a), colorType=skia.kRGBA_8888_ColorType))
        # dust particles at three depths
        self.dust = rng.random((70, 5))

    def apply(self, c, t, cam=None, vignette=0.55, grain=1.0, light=1.0, dust=1.0, warm=1.0):
        # paper grain (overlay)
        p = skia.Paint(BlendMode=skia.BlendMode.kOverlay); p.setAlphaf(0.38 * grain)
        c.drawImage(self.grain, 0, 0, skia.SamplingOptions(), p)
        # animated fine film grain
        fi = self.film[int(t * 24) % len(self.film)]
        p2 = skia.Paint(BlendMode=skia.BlendMode.kOverlay); p2.setAlphaf(0.035 * grain)
        c.drawImageRect(fi, skia.Rect(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p2)
        # soft key light from upper-left, slowly breathing
        if light > 0:
            lx = W * (0.18 + 0.05 * math.sin(t * 0.21)); ly = H * (0.12 + 0.03 * math.cos(t * 0.17))
            sh = skia.GradientShader.MakeRadial((lx, ly), H * 0.95, [C(255, 244, 222, 70), C(255, 240, 210, 0)])
            lp = skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kScreen); lp.setAlphaf(0.6 * light)
            c.drawRect(skia.Rect(0, 0, W, H), lp)
        # vignette
        if vignette > 0:
            vs = skia.GradientShader.MakeRadial((W / 2, H * 0.47), H * 0.78, [C(0, 0, 0, 0), C(0, 0, 0, 0), C(38, 24, 12, 255)], [0, 0.55, 1.0])
            vp = skia.Paint(Shader=vs, BlendMode=skia.BlendMode.kMultiply); vp.setAlphaf(vignette)
            c.drawRect(skia.Rect(0, 0, W, H), vp)
        # floating dust with depth parallax
        if dust > 0:
            for i, (x, y, z, ph, s) in enumerate(self.dust):
                depth = 0.3 + z
                px = (x * W + t * 9 * depth + (cam.cx * cam.scale * 0.04 * depth if cam else 0)) % W
                py = (y * H - t * 14 * depth + 30 * math.sin(t * 0.3 + ph * 6)) % H
                r = 1.0 + 2.6 * z * s
                a = (0.06 + 0.16 * z) * (0.5 + 0.5 * math.sin(t * 0.8 + ph * 9)) * dust
                dp = skia.Paint(AntiAlias=True, Color=C(255, 246, 225), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 0.8 + 2.5 * z))
                dp.setAlphaf(a); c.drawCircle(px, py, r, dp)

# ------------------------------------------------------------------ helpers for images (portraits / documents)
@functools.lru_cache(None)
def load_image(name, maxdim=2600):
    im = Image.open(ROOT + 'assets/raw/' + name).convert('RGBA')
    if max(im.size) > maxdim: im.thumbnail((maxdim, maxdim), Image.LANCZOS)
    return skia.Image.fromarray(np.asarray(im), colorType=skia.kRGBA_8888_ColorType).withDefaultMipmaps()

def dark_backdrop(c, t, tone=(24, 18, 13), glow=(70, 50, 32), gx=0.5, gy=0.4, radius=1.1):
    c.drawColor(C(*tone))
    sh = skia.GradientShader.MakeRadial((W * gx, H * gy), H * 0.6 * radius, [C(*glow), C(*tone)])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))

def rule(c, x, y, w, t, color=PAL['gold'], th=1.6, alpha=1.0, diamond=True):
    if t <= 0: return
    e = ease_out_expo(t); half = w / 2 * e
    p = skia.Paint(AntiAlias=True, Color=C(*color), StrokeWidth=th); p.setAlphaf(alpha)
    c.drawLine(x - half, y, x + half, y, p)
    if diamond:
        s = 5 * ease_out_back(clamp(t * 2 - 0.4))
        if s > 0:
            path = skia.Path(); path.moveTo(x, y - s); path.lineTo(x + s, y); path.lineTo(x, y + s); path.lineTo(x - s, y); path.close()
            dp = skia.Paint(AntiAlias=True, Color=C(*color)); dp.setAlphaf(alpha); c.drawPath(path, dp)
