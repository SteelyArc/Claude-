"""Shared motion engine for the 'What if Poland-Lithuania had never been partitioned?' documentary.

World space: Lambert azimuthal equal-area, centre 24E 52N, metres (same as the verified layers in data/layers.pkl).
Screen: 1080 x 1920, 30 fps. The camera supports pan, log-space zoom, roll and a true perspective tilt.
"""
import math, os, pickle, subprocess, functools
import numpy as np, skia, cv2
from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30
FWD = Transformer.from_crs(4326, '+proj=laea +lat_0=52 +lon_0=24 +datum=WGS84 +units=m', always_xy=True)
L = pickle.load(open(f'{ROOT}/data/layers.pkl', 'rb'))

# TikTok-safe frame: keep text inside these bounds (top bar, right action rail, bottom caption/UI)
SAFE = dict(x0=90, x1=960, y0=230, y1=1480)


def ll(lon, lat):
    return FWD.transform(lon, lat)


CITIES = {k: ll(*v) for k, v in {
    'Warsaw': (21.012, 52.230), 'Vilnius': (25.280, 54.687), 'Kraków': (19.945, 50.065), 'Gdańsk': (18.646, 54.352),
    'Lwów': (24.031, 49.842), 'Riga': (24.105, 56.950), 'Kyiv': (30.523, 50.450), 'Berlin': (13.405, 52.520),
    'Vienna': (16.373, 48.208), 'St Petersburg': (30.316, 59.939), 'Königsberg': (20.511, 54.707),
    'Grodno': (23.829, 53.678), 'Minsk': (27.559, 53.900), 'Poznań': (16.925, 52.406), 'Moscow': (37.618, 55.756)}.items()}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def ease(x):                      # cubic in-out
    x = clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def eout(x, p=3):                 # ease-out
    return 1 - (1 - clamp(x)) ** p


def eexp(x):                      # expo in-out: cinematic camera moves
    x = clamp(x)
    if x in (0, 1): return x
    return 2 ** (20 * x - 10) / 2 if x < .5 else (2 - 2 ** (-20 * x + 10)) / 2


def lerp(a, b, t):
    return a + (b - a) * t


def lerpc(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def rgb(h, a=1.0):
    h = h.lstrip('#')
    return skia.Color4f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


# ---------------------------------------------------------------- geometry -> skia paths (cached, world metres)
@functools.lru_cache(maxsize=None)
def _path_cached(key):
    g = _GEOMS[key]
    p = skia.Path(); p.setFillType(skia.PathFillType.kEvenOdd)
    def ring(c, close=True):
        c = np.asarray(c)
        if len(c) < 2: return
        p.moveTo(*c[0, :2]); [p.lineTo(*v[:2]) for v in c[1:]]
        if close: p.close()
    def walk(g):
        t = g.geom_type
        if t == 'Polygon':
            ring(g.exterior.coords); [ring(i.coords) for i in g.interiors]
        elif t in ('MultiPolygon', 'GeometryCollection', 'MultiLineString'):
            [walk(x) for x in g.geoms]
        elif t == 'LineString':
            ring(g.coords, False)
    walk(g)
    return p


_GEOMS = {}


def path_nocache(g):
    _GEOMS[-1] = g
    p = _path_cached.__wrapped__(-1); return p


def path(g):
    k = id(g); _GEOMS[k] = g
    return _path_cached(k)


def outline(g):
    """Boundary rings only (for stroking without the land-sea fill)."""
    return path(g.boundary)


# ---------------------------------------------------------------- camera
class Cam:
    """cx, cy: world centre (m). zoom: screen px per km. rot: roll (deg). tilt: 0..1 perspective (top recedes)."""

    def __init__(self, cx=0, cy=0, zoom=0.7, rot=0, tilt=0, oy=0):
        self.cx, self.cy, self.zoom, self.rot, self.tilt, self.oy = cx, cy, zoom, rot, tilt, oy

    @staticmethod
    def blend(a, b, t):
        z = math.exp(lerp(math.log(a.zoom), math.log(b.zoom), t))
        # keep the path straight in screen space by interpolating centre with zoom-weighted factor
        return Cam(lerp(a.cx, b.cx, t), lerp(a.cy, b.cy, t), z, lerp(a.rot, b.rot, t), lerp(a.tilt, b.tilt, t), lerp(a.oy, b.oy, t))

    def matrix(self):
        s = self.zoom / 1000.0
        m = skia.Matrix()
        m.setTranslate(W / 2, H / 2 + self.oy)
        m.preRotate(self.rot)
        m.preScale(s, -s)
        m.preTranslate(-self.cx, -self.cy)
        if self.tilt > 1e-4:
            k = self.tilt
            src = [skia.Point(0, 0), skia.Point(W, 0), skia.Point(W, H), skia.Point(0, H)]
            dx, dy = W * 0.34 * k, H * 0.10 * k
            dst = [skia.Point(dx, dy), skia.Point(W - dx, dy), skia.Point(W + W * 0.10 * k, H + H * 0.04 * k),
                   skia.Point(-W * 0.10 * k, H + H * 0.04 * k)]
            P = skia.Matrix(); P.setPolyToPoly(src, dst)
            m = skia.Matrix.Concat(P, m)
        return m

    def pt(self, x, y):
        p = self.matrix().mapXY(x, y)
        return p.x(), p.y()


def tpath(p, M):
    q = skia.Path(p); q.transform(M); return q


# ---------------------------------------------------------------- paints & text
def fill(c, aa=True):
    return skia.Paint(Color4f=c, AntiAlias=aa, Style=skia.Paint.kFill_Style)


def stroke(c, w, dash=None, glow=0, cap=skia.Paint.kRound_Cap):
    p = skia.Paint(Color4f=c, AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=cap,
                   StrokeJoin=skia.Paint.kRound_Join)
    if dash: p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    if glow: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow))
    return p


@functools.lru_cache(maxsize=None)
def tf(name):
    return skia.Typeface.MakeFromFile(f'{ROOT}/assets/fonts/{name}')


@functools.lru_cache(maxsize=None)
def font(name, size):
    f = skia.Font(tf(name), size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    return f


def text_width(s, f, spacing=0):
    return sum(f.measureText(ch) for ch in s) + spacing * max(len(s) - 1, 0)


def text(c, s, x, y, f, color, align='c', spacing=0, reveal=1.0, rise=18, shadow=None, glow=None, stagger=0.6):
    """Draw text with tracking. reveal 0..1 animates letters in sequence (fade + rise + de-blur)."""
    w = text_width(s, f, spacing)
    x0 = x - w / 2 if align == 'c' else x - w if align == 'r' else x
    n = max(len(s), 1)
    cx = x0
    for i, ch in enumerate(s):
        a0 = i / n * stagger
        k = eout(seg(reveal, a0, a0 + (1 - stagger))) if reveal < 1 else 1.0
        if k > 0 and ch != ' ':
            dy = (1 - k) * rise
            if glow:
                gp = skia.Paint(Color4f=glow, AntiAlias=True)
                gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, f.getSize() * 0.22))
                gp.setAlphaf(glow.fA * k)
                c.drawString(ch, cx, y + dy, f, gp)
            if shadow:
                sp = skia.Paint(Color4f=shadow, AntiAlias=True)
                sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(2, f.getSize() * 0.08)))
                sp.setAlphaf(shadow.fA * k)
                c.drawString(ch, cx + 2, y + dy + 4, f, sp)
            p = skia.Paint(Color4f=color, AntiAlias=True); p.setAlphaf(color.fA * k)
            if k < 1:
                p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, (1 - k) * 6 + 0.01))
            c.drawString(ch, cx, y + dy, f, p)
        cx += f.measureText(ch) + spacing
    return w


# ---------------------------------------------------------------- image helpers
def to_image(arr):
    """numpy HxWx3/4 uint8 RGB(A) -> skia.Image"""
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


def load_rgb(rel, max_side=None):
    im = cv2.cvtColor(cv2.imread(f'{ROOT}/{rel}', cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    if max_side and max(im.shape[:2]) > max_side:
        s = max_side / max(im.shape[:2]); im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return im


SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


# ---------------------------------------------------------------- post-processing (v2)
POST_STATE = {}          # per-frame hints a scene may set (e.g. depth-of-field strength)


class Post:
    """Filmic finishing: halation/bloom, tilt-shift DOF, lens chromatic aberration, vignette,
    full-resolution luminance grain (also dithers 8-bit output against banding), gentle tone shoulder."""

    def __init__(self, grain=0.035, vignette=0.45, bloom=0.0, seed=1, warm=None, halation=0.0, ca=0.0, shoulder=0.0):
        rng = np.random.default_rng(seed)
        self.noise = [cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.55) * 1.6 for _ in range(6)]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.60)) ** 2)
        self.vig = (1 - vignette * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
        self.grain, self.bloom, self.halation, self.ca, self.shoulder = grain, bloom, halation, ca, shoulder
        self.ymask = (yy[:, :1] / H).astype(np.float32)

    def __call__(self, img, f):
        if img.dtype == np.uint8:
            img = img[..., :3].astype(np.float32) / 255.0
        dof = POST_STATE.get('dof', 0.0)
        if dof > 0.01:   # tilt-shift: far (top) of a tilted map softens, a little at the bottom too
            b1 = cv2.GaussianBlur(img, (0, 0), 2.2 * dof + 0.01); b2 = cv2.GaussianBlur(img, (0, 0), 6.0 * dof + 0.01)
            top = np.clip((0.38 - self.ymask) / 0.38, 0, 1); bot = np.clip((self.ymask - 0.86) / 0.14, 0, 1) * 0.6
            m = np.clip(top + bot, 0, 1)[..., None]
            img = img * (1 - m) + (b1 * (1 - m) + b2 * m) * m
        if self.bloom > 0 or self.halation > 0:
            small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            hi = np.clip(small - 0.52, 0, 1) * 2.2
            b = cv2.GaussianBlur(hi, (0, 0), 7) * 0.8 + cv2.GaussianBlur(hi, (0, 0), 22) * 0.7 + cv2.GaussianBlur(hi, (0, 0), 60) * 0.4
            b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
            if self.halation > 0:
                b = b * (1 - self.halation) + b * np.array([1.25, 0.72, 0.45], np.float32) * self.halation
            img = 1 - (1 - img) * (1 - np.clip(b * max(self.bloom, self.halation), 0, 1))
        if self.ca > 0:   # radial lateral chromatic aberration
            for ch, k in ((0, 1 + self.ca), (2, 1 - self.ca)):
                M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, k)
                img[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if self.shoulder > 0:
            img = img * (1 + self.shoulder) / (1 + self.shoulder * img)
        img *= self.vig
        n = self.noise[f % 6][..., None]
        lum = img.mean(axis=2, keepdims=True)
        img = img + n * (self.grain * (0.30 + 0.70 * (1 - np.abs(lum - 0.45) * 1.8).clip(0, 1)) + 1.2 / 255)
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- writer
X264 = ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'film', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS)]


class Writer:
    def __init__(self, out, audio=None, crf=16, t0=0.0, dur=None):
        cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
        if audio:
            cmd += ['-ss', str(t0)] + (['-t', str(dur)] if dur else []) + ['-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest']
        cmd += X264 + ['-crf', str(crf), '-movflags', '+faststart', out]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, rgb):
        self.p.stdin.write(np.ascontiguousarray(rgb).tobytes())

    def close(self):
        self.p.stdin.close(); self.p.wait()


def new_canvas():
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    return arr, surf


def frame(scene, f, mb=1, shutter=0.5):
    """Render frame f with temporal motion blur: mb sub-frames spread over the shutter (0.5 = 180 degrees)."""
    acc = None
    for i in range(mb):
        tt = f / FPS + (((i + 0.5) / mb - 0.5) * shutter / FPS if mb > 1 else 0.0)
        arr, surf = new_canvas()
        with surf as c:
            scene(c, tt, f)
        x = arr[..., :3].astype(np.float32)
        acc = x if acc is None else acc + x
    return acc / (255.0 * mb)


def _render_chunk(args):
    scene_mod, fr, out, post, mb, still_f, still_dir, name = args
    import importlib, sys as _s
    cv2.setNumThreads(1)
    if os.path.dirname(os.path.abspath(__file__)) not in _s.path: _s.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    mod = importlib.import_module(scene_mod)
    w = Writer(out)
    for f in fr:
        img = post(frame(mod.scene, f, mb), f)
        w.write(img)
        if f in still_f and still_dir:
            cv2.imwrite(f'{still_dir}/{name}_{still_f[f]:05.2f}s.jpg', cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
        if f % 30 == 0: print(f'  {name} frame {f}', flush=True)
    w.close()


def render(scene, dur, out, post, audio=None, stills=(), still_dir=None, frames=None, mb=1, workers=1, scene_mod=None):
    """Render scene to MP4 (optionally in parallel chunks, concatenated losslessly at the end)."""
    n = int(round(dur * FPS))
    still_f = {int(round(s * FPS)): s for s in stills}
    name = os.path.basename(out)[:-4]
    allf = list(frames or range(n))
    if workers > 1 and scene_mod:
        import multiprocessing as mp, tempfile
        k = (len(allf) + workers - 1) // workers
        tmp = tempfile.mkdtemp(dir=os.path.dirname(out))
        parts = [(scene_mod, allf[i * k:(i + 1) * k], f'{tmp}/p{i}.mp4', post, mb, still_f, still_dir, name) for i in range(workers)]
        with mp.get_context('spawn').Pool(workers) as pool:   # spawn: fork deadlocks with OpenCV/Skia threads
            for _ in pool.imap_unordered(_render_chunk, parts): pass
        lst = f'{tmp}/list.txt'; open(lst, 'w').write(''.join(f"file '{p[2]}'\n" for p in parts))
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', out], check=True)
        import shutil; shutil.rmtree(tmp)
        return
    w = Writer(out, audio)
    for f in allf:
        img = post(frame(scene, f, mb), f)
        w.write(img)
        if f in still_f and still_dir:
            cv2.imwrite(f'{still_dir}/{name}_{still_f[f]:05.2f}s.jpg', cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
        if f % 30 == 0: print(f'  {name} {f}/{n}', flush=True)
    w.close()


def test_frames(scene, times, post, prefix, mb=1):
    """Render individual frames to PNG for checking (no video)."""
    outs = []
    for tt in times:
        f = int(round(tt * FPS))
        img = post(frame(lambda c, t_, f_: scene(c, t_ - f / FPS + tt, f_), f, mb), f)
        o = f'{prefix}_{tt:05.2f}.png'; cv2.imwrite(o, cv2.cvtColor(img, cv2.COLOR_RGB2BGR)); outs.append(o)
    return outs


def sheet(files, out, cols=3, w=360):
    ims = [cv2.imread(f) for f in files]
    ims = [cv2.resize(i, (w, int(i.shape[0] * w / i.shape[1]))) for i in ims]
    h = ims[0].shape[0]; rows = (len(ims) + cols - 1) // cols
    S = np.full((rows * h, cols * w, 3), 20, np.uint8)
    for i, im in enumerate(ims):
        S[(i // cols) * h:(i // cols) * h + h, (i % cols) * w:(i % cols) * w + w] = im
    cv2.imwrite(out, S, [cv2.IMWRITE_JPEG_QUALITY, 88])


def lin_grad(p0, p1, colors, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], [c.toColor() for c in colors], pos)


def rad_grad(cx, cy, r, colors, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, [c.toColor() for c in colors], pos)
