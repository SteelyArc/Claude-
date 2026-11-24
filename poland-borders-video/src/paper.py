"""Paper-relief map rendering: layered paper sheets with soft shadows, bevels and fibre texture."""
import math, os
import numpy as np
import cairo
from PIL import Image, ImageFilter, ImageChops
from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'build')
os.makedirs(OUT, exist_ok=True)

COSF = math.cos(math.radians(52))
LON0, LAT0 = 22.0, 52.0
# master canvas extent (lon/lat) and resolution (pixels per projected unit = per degree of latitude)
EXT = (9.0, 39.5, 36.5, 63.5)
PPU = 200
MX0 = (EXT[0] - LON0) * COSF
MY0 = -(EXT[3] - LAT0)
MW = int(round(((EXT[2] - LON0) * COSF - MX0) * PPU))
MH = int(round((-(EXT[1] - LAT0) - MY0) * PPU))


def proj(lon, lat):
    """lon/lat -> projected units (x right, y down)."""
    return (lon - LON0) * COSF, -(lat - LAT0)


def to_master_px(lon, lat):
    x, y = proj(lon, lat)
    return (x - MX0) * PPU, (y - MY0) * PPU


def geom_px(g):
    """lon/lat shapely geometry -> master pixel coordinates."""
    g = affinity.affine_transform(g, [COSF * PPU, 0, 0, -PPU, (-LON0 * COSF - MX0) * PPU, (LAT0 - MY0) * PPU])
    return g


def hexc(h, a=1.0):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)


def polys(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for p in g.geoms:
            out += polys(p)
        return out
    return []


def path_geom(ctx, g):
    for p in polys(g):
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            ctx.move_to(*cs[0])
            for c in cs[1:]:
                ctx.line_to(*c)
            ctx.close_path()


def mask_of(g, w=MW, h=MH):
    """Rasterise pixel-space geometry into an L image (anti-aliased)."""
    surf = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
    ctx = cairo.Context(surf)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    path_geom(ctx, g)
    ctx.set_source_rgba(0, 0, 0, 1)
    ctx.fill()
    surf.flush()
    stride = surf.get_stride()
    a = np.ndarray((h, stride), dtype=np.uint8, buffer=surf.get_data())[:, :w].copy()
    return Image.fromarray(a, 'L')


def shift(img, dx, dy):
    return ImageChops.offset(img, int(dx), int(dy))


def solid(color, size):
    r, g, b, _ = hexc(color)
    return Image.new('RGBA', size, (int(r * 255), int(g * 255), int(b * 255), 255))


def scale_alpha(m, f):
    return m.point(lambda v: int(v * f))


class Sheet:
    """A paper layer to stack."""
    def __init__(self, geom_px, color, level=1, rim=True, hatch=False, alpha=1.0):
        self.g, self.color, self.level, self.rim, self.hatch, self.alpha = geom_px, color, level, rim, hatch, alpha


_TEX = {}


def texture(size, seed=7):
    """multiplicative paper fibre texture as float32 array HxW."""
    key = (size, seed)
    if key in _TEX:
        return _TEX[key]
    w, h = size
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for div, amp in ((64, 0.035), (16, 0.025), (4, 0.02), (1, 0.03)):
        sw, sh = max(2, w // div), max(2, h // div)
        n = Image.fromarray((rng.random((sh, sw)) * 255).astype(np.uint8), 'L')
        n = n.resize((w, h), Image.BICUBIC)
        if div == 1:
            n = n.filter(ImageFilter.GaussianBlur(0.6))
        acc += (np.asarray(n, np.float32) / 255 - 0.5) * 2 * amp
    # fibres: short streaks
    fib = Image.new('L', (w, h), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(fib)
    for _ in range(int(w * h / 3500)):
        x, y = rng.random() * w, rng.random() * h
        a = rng.random() * math.pi
        L = 6 + rng.random() * 22
        d.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], fill=int(40 + rng.random() * 60), width=1)
    fib = fib.filter(ImageFilter.GaussianBlur(0.7))
    acc += np.asarray(fib, np.float32) / 255 * 0.06
    _TEX[key] = 1.0 + acc
    return _TEX[key]


def compose(sheets, base_color, size=(MW, MH), sh_scale=1.0, tex=True):
    """Render a stack of sheets into an RGBA image."""
    W, H = size
    canvas = solid(base_color, size)
    black = Image.new('RGBA', size, (20, 14, 8, 255))
    white = Image.new('RGBA', size, (255, 250, 238, 255))
    for s in sheets:
        m = mask_of(s.g, W, H)
        if s.alpha < 1:
            m = scale_alpha(m, s.alpha)
        lv = s.level
        # drop shadow (ambient + key)
        for (off, blur, op) in ((3 * lv, 5 * lv, 0.30), (7 * lv, 16 * lv, 0.22)):
            sm = shift(m, off * 0.6 * sh_scale, off * sh_scale).filter(ImageFilter.GaussianBlur(blur * sh_scale))
            canvas.paste(black, (0, 0), scale_alpha(sm, op))
        thick = int(round(2 + (lv - 1) * 4)) if lv >= 1 else 1
        if thick > 0:
            r, g, b, _ = hexc(s.color)
            edge = '#%02x%02x%02x' % (int(r * 150), int(g * 150), int(b * 150))
            for t in range(thick, 0, -1):
                canvas.paste(solid(edge, size), (0, 0), shift(m, 0, t))
        canvas.paste(solid(s.color, size), (0, 0), m)
        if s.hatch:
            hl = hatch_layer(size, s.color)
            canvas.paste(hl, (0, 0), ImageChops.multiply(m, hl.getchannel('A')))
        if s.rim:
            hi = ImageChops.subtract(m, shift(m, 2, 3))
            lo = ImageChops.subtract(m, shift(m, -2, -3))
            canvas.paste(white, (0, 0), scale_alpha(hi.filter(ImageFilter.GaussianBlur(0.8)), 0.55))
            canvas.paste(black, (0, 0), scale_alpha(lo.filter(ImageFilter.GaussianBlur(0.8)), 0.35))
    if tex:
        arr = np.asarray(canvas.convert('RGB'), np.float32) * texture(size)[..., None]
        canvas = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return canvas


def hatch_layer(size, color, spacing=14):
    W, H = size
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    r, g, b, _ = hexc(color)
    ctx.set_source_rgba(r * 0.75, g * 0.75, b * 0.75, 0.55)
    ctx.set_line_width(2.2)
    for x in range(-H, W, spacing):
        ctx.move_to(x, 0)
        ctx.line_to(x + H, H)
    ctx.stroke()
    return cairo_to_pil(surf)


def cairo_to_pil(surf):
    surf.flush()
    w, h = surf.get_width(), surf.get_height()
    a = np.ndarray((h, surf.get_stride() // 4, 4), np.uint8, buffer=surf.get_data())[:, :w, :]
    # BGRA premultiplied -> RGBA straight
    b, g, r, al = [a[..., i].astype(np.float32) for i in range(4)]
    nz = np.maximum(al, 1) / 255
    rgba = np.stack([r / nz, g / nz, b / nz, al], -1)
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')


# ---------- relief ---------------------------------------------------------
RANGES = {
    'carpathians': [(17.2, 48.55), (18.3, 49.05), (19.3, 49.35), (20.1, 49.22), (21.3, 49.35), (22.6, 49.05),
                    (23.6, 48.65), (24.6, 48.15), (25.3, 47.6), (25.75, 46.9), (26.0, 46.1), (25.6, 45.55),
                    (24.6, 45.45), (23.4, 45.4), (22.5, 45.25), (22.2, 44.8)],
    'apuseni': [(22.2, 46.9), (22.8, 46.5), (23.1, 46.2)],
    'sudetes': [(15.0, 50.85), (15.8, 50.75), (16.5, 50.45), (17.3, 50.2)],
    'ore': [(12.2, 50.3), (13.3, 50.55), (14.2, 50.8)],
    'bohemian': [(12.6, 49.8), (13.5, 49.0), (14.5, 48.7)],
    'alps': [(9.0, 46.6), (10.5, 46.6), (12.0, 47.0), (13.5, 47.2), (15.0, 47.5), (16.0, 47.8)],
    'dinaric': [(14.5, 45.6), (16.0, 44.5), (17.5, 43.6), (19.0, 42.8), (20.0, 42.2)],
    'balkan': [(22.4, 43.6), (23.7, 42.9), (25.5, 42.75), (27.0, 42.8)],
    'scand': [(12.0, 61.5), (13.2, 63.5)],
    'crimea': [(33.8, 44.6), (34.8, 44.85)],
}
RANGE_W = {'carpathians': 0.85, 'alps': 1.3, 'dinaric': 0.9, 'balkan': 0.6, 'sudetes': 0.45, 'ore': 0.4,
           'bohemian': 0.45, 'apuseni': 0.5, 'scand': 0.9, 'crimea': 0.25}


def _wobble(n, rng, octaves=((0.15, 0.35), (0.5, 0.2), (1.3, 0.12))):
    t = np.arange(n, dtype=np.float32)
    out = np.zeros(n, np.float32)
    for freq, amp in octaves:
        out += amp * np.sin(t * freq * 0.2 + rng.random() * 6.28)
    return out


def relief_sheets(land_px):
    from shapely.geometry import Point
    sheets = []
    rng = np.random.default_rng(3)
    for k, pts in RANGES.items():
        line = geom_px(LineString(pts))
        base_r = RANGE_W[k] * PPU * 0.30
        n = max(4, int(line.length / (base_r * 0.25)))
        wob = _wobble(n, rng)
        perp = _wobble(n, rng, ((0.25, 0.25), (0.8, 0.1)))
        for i, f in enumerate((1.0, 0.72, 0.48, 0.27, 0.12)):
            wob = 0.6 * wob + 0.4 * _wobble(n, rng, ((0.4, 0.4), (1.1, 0.25), (2.5, 0.12)))
            circles = []
            for j in range(n):
                d = j / (n - 1) * line.length
                p = line.interpolate(d)
                p2 = line.interpolate(min(line.length, d + 1))
                dx, dy = p2.x - p.x, p2.y - p.y
                L = math.hypot(dx, dy) or 1
                nx, ny = -dy / L, dx / L
                taper = min(1.0, 0.35 + 1.3 * min(d, line.length - d) / line.length * 2)
                r = base_r * f * taper * (1 + wob[j] * (0.6 + i * 0.25))
                if r < 3:
                    continue
                off = perp[j] * base_r * (0.6 + 0.3 * i)
                circles.append(Point(p.x + nx * off, p.y + ny * off).buffer(r, quad_segs=10))
            if not circles:
                continue
            g = unary_union(circles).buffer(4).buffer(-4).simplify(1.5).intersection(land_px)
            sheets.append((g, i))
    return sheets


def overlay_relief(canvas, land_px, size=(MW, MH)):
    W, H = size
    black = Image.new('RGBA', size, (30, 20, 10, 255))
    white = Image.new('RGBA', size, (255, 248, 230, 255))
    for g, i in relief_sheets(land_px):
        if g.is_empty:
            continue
        m = mask_of(g, W, H)
        sm = shift(m, 2, 4).filter(ImageFilter.GaussianBlur(4))
        canvas.paste(black, (0, 0), scale_alpha(ImageChops.subtract(sm, m), 0.30))
        canvas.paste(white, (0, 0), scale_alpha(m, 0.09))
        hi = ImageChops.subtract(m, shift(m, 2, 3))
        lo = ImageChops.subtract(m, shift(m, -1, -2))
        canvas.paste(white, (0, 0), scale_alpha(hi, 0.55))
        canvas.paste(black, (0, 0), scale_alpha(lo, 0.18))
    return canvas


RIVERS = {
    'vistula': [(18.98, 49.67), (19.4, 49.98), (19.94, 50.05), (20.6, 50.2), (21.2, 50.35), (21.75, 50.68),
                (21.85, 51.0), (21.85, 51.56), (21.6, 51.85), (21.25, 52.05), (21.02, 52.25), (20.6, 52.4),
                (20.2, 52.42), (19.7, 52.55), (19.05, 52.66), (18.6, 53.01), (18.4, 53.18), (18.75, 53.48),
                (18.85, 53.8), (18.95, 54.15), (18.95, 54.36)],
    'oder': [(17.9, 49.8), (18.2, 50.05), (17.9, 50.66), (17.4, 50.9), (17.03, 51.11), (16.2, 51.6),
             (15.6, 51.95), (14.65, 52.35), (14.4, 52.6), (14.15, 53.0), (14.3, 53.43), (14.4, 53.75)],
    'dnieper': [(31.0, 54.8), (30.3, 54.0), (30.3, 53.2), (30.4, 52.5), (30.35, 51.6), (30.5, 50.45),
                (31.4, 49.7), (32.1, 49.35), (33.0, 49.05), (34.6, 48.5), (35.1, 47.85), (34.4, 47.4),
                (33.3, 46.75), (32.6, 46.6)],
    'neman': [(26.7, 53.6), (25.8, 53.7), (24.6, 53.9), (23.97, 54.2), (24.0, 54.6), (23.9, 54.9),
              (23.0, 55.05), (22.2, 55.08), (21.3, 55.27)],
    'bug': [(24.6, 49.85), (24.3, 50.5), (24.05, 50.85), (23.65, 51.55), (23.6, 52.1), (22.8, 52.5),
            (22.0, 52.6), (21.4, 52.5), (21.0, 52.42)],
    'san': [(22.65, 49.05), (22.5, 49.4), (22.78, 49.8), (22.6, 50.3), (22.0, 50.6), (21.85, 50.68)],
    'danube': [(9.0, 48.1), (11.4, 48.75), (13.5, 48.55), (16.4, 48.2), (17.1, 48.1), (18.8, 47.8),
               (19.05, 47.5), (18.9, 46.0), (19.9, 45.2), (20.5, 44.8), (22.5, 44.6), (22.7, 43.8),
               (24.5, 43.7), (26.0, 43.95), (27.9, 44.1), (28.2, 45.4), (29.7, 45.2)],
    'dniester': [(23.0, 49.4), (24.7, 49.0), (26.0, 48.6), (27.5, 48.4), (28.8, 47.5), (29.6, 46.8),
                 (30.2, 46.3)],
    'elbe': [(14.2, 50.6), (13.8, 51.05), (12.6, 51.9), (11.7, 52.6), (10.6, 53.4), (9.9, 53.55),
             (8.9, 53.9)],
}


def overlay_rivers(canvas, land_px, size=(MW, MH), color='#7fa8b0'):
    W, H = size
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k, pts in RIVERS.items():
        ls = geom_px(LineString(pts)).intersection(land_px.buffer(-2))
        for part in (ls.geoms if hasattr(ls, 'geoms') else [ls]):
            if part.is_empty or part.geom_type != 'LineString':
                continue
            cs = list(part.coords)
            for wdt, col in ((7, (0.25, 0.2, 0.12, 0.25)), (5, hexc(color)), (1.6, (0.85, 0.93, 0.93, 0.7))):
                ctx.set_line_width(wdt)
                ctx.set_source_rgba(*col)
                ctx.move_to(*cs[0])
                # smooth with quadratic midpoints
                for a, b in zip(cs[1:-1], cs[2:]):
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    ctx.curve_to(a[0], a[1], a[0], a[1], mx, my)
                ctx.line_to(*cs[-1])
                ctx.stroke()
    riv = cairo_to_pil(surf)
    canvas.alpha_composite(riv)
    return canvas
