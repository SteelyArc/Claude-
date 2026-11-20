"""Pre-render the static cartographic base (relief, land, engraved water, graticule) as large rasters.
Two levels: 'lo' (Europe scale) and 'hi' (Commonwealth detail). Output: PNG + json extents."""
import json, math, pickle, glob, numpy as np, skia
from PIL import Image
from scipy import ndimage
from pyproj import Transformer
import shapely
D = '/home/user/Claude-/partition1772/data/'
INV = Transformer.from_crs('+proj=laea +lat_0=52 +lon_0=22 +units=km +ellps=WGS84', 4326, always_xy=True)
FWD = Transformer.from_crs(4326, '+proj=laea +lat_0=52 +lon_0=22 +units=km +ellps=WGS84', always_xy=True)
L = pickle.load(open(D + 'layers.pkl', 'rb'))

LEVELS = {'lo': dict(x0=-3600, x1=3600, y0=-2700, y1=3300, res=0.95),
          'hi': dict(x0=-1000, x1=1250, y0=-800, y1=1150, res=0.25)}

# ---------------- palette (linear-ish sRGB 0..1)
PAPER = np.array([0.937, 0.905, 0.835])   # warm ivory
LAND = np.array([0.925, 0.889, 0.806], np.float32)
SEA = np.array([0.776, 0.812, 0.792])      # muted grey-green blue
SEA_DEEP = np.array([0.722, 0.769, 0.757], np.float32)
INK = np.array([0.30, 0.25, 0.19], np.float32)

DEMDIR = {5: 'dem5/5_*.png', 7: 'dem/7_*.png', 8: 'dem8/8_*.png'}
COVER = {8: (9.2, 38.8, 43.8, 61.3), 7: (4.2, 43.8, 41.2, 62.8), 5: (-180, 180, -85, 85)}

def dem_multi(levels):
    """Sample the finest DEM level covering each point (falls back to coarser zoom levels)."""
    S = [(z, dem_sampler(z)) for z in levels]
    def sample(lon, lat):
        out = np.zeros(lon.shape, np.float32); done = np.zeros(lon.shape, bool)
        for z, f in S:
            w0, w1, s0, s1 = COVER[z]
            m = (~done) & (lon > w0) & (lon < w1) & (lat > s0) & (lat < s1)
            if m.any(): out[m] = f(lon[m], lat[m]); done |= m
        return out
    return sample

def dem_sampler(z=7):
    tiles = {}
    for f in glob.glob(D + DEMDIR[z]):
        _, x, y = f.split('/')[-1][:-4].split('_'); tiles[(int(x), int(y))] = f
    xs = sorted({k[0] for k in tiles}); ys = sorted({k[1] for k in tiles})
    W = (xs[-1] - xs[0] + 1) * 256; H = (ys[-1] - ys[0] + 1) * 256
    M = np.zeros((H, W), np.float32)
    for (x, y), f in tiles.items():
        a = np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
        M[(y - ys[0]) * 256:(y - ys[0] + 1) * 256, (x - xs[0]) * 256:(x - xs[0] + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    def sample(lon, lat):
        n = 2 ** z
        px = (lon + 180) / 360 * n * 256 - xs[0] * 256
        r = np.radians(np.clip(lat, -85, 85))
        py = (1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * n * 256 - ys[0] * 256
        return ndimage.map_coordinates(M, [py, px], order=1, mode='nearest')
    return sample

def to_path(g, sx, sy, x0, y1):
    p = skia.Path()
    def ring(c):
        c = np.asarray(c)
        p.moveTo((c[0, 0] - x0) * sx, (y1 - c[0, 1]) * sy)
        for x, y in c[1:]:
            p.lineTo((x - x0) * sx, (y1 - y) * sy)
        p.close()
    for poly in getattr(g, 'geoms', [g]):
        if poly.geom_type != 'Polygon': continue
        ring(poly.exterior.coords)
        for i in poly.interiors: ring(i.coords)
    p.setFillType(skia.PathFillType.kEvenOdd)
    return p

def raster_mask(g, W, H, ext):
    s = skia.Surface(W, H); c = s.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    pt = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    c.drawPath(to_path(g, 1 / ext['res'], 1 / ext['res'], ext['x0'], ext['y1']), pt)
    return s.makeImageSnapshot().toarray()[..., 3].astype(np.float32) / 255

def fbm(H, W, scale, octaves=5, seed=1):
    rng = np.random.default_rng(seed); out = np.zeros((H, W), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(scale / 2 ** o))
        h, w = H // s + 2, W // s + 2
        n = rng.random((h, w)).astype(np.float32)
        n = ndimage.zoom(n, (H / (h - 1) * 1.0, W / (w - 1) * 1.0), order=3)[:H, :W]
        out += amp * n; tot += amp; amp *= 0.5
    return out / tot

def build(level):
    e = LEVELS[level]; res = e['res']
    W = int((e['x1'] - e['x0']) / res); H = int((e['y1'] - e['y0']) / res)
    print(level, W, H)
    xs = e['x0'] + (np.arange(W) + .5) * res; ys = e['y1'] - (np.arange(H) + .5) * res
    land = raster_mask(L['land'], W, H, e)
    lakes = raster_mask(L['lakes'], W, H, e)
    landonly = np.clip(land - lakes, 0, 1).astype(np.float32); del land, lakes
    dist = ndimage.distance_transform_edt(landonly < 0.5).astype(np.float32) * res   # km from land (global)
    # world-space paper mottling at quarter resolution (continuous across strips)
    mq = fbm(H // 4 + 1, W // 4 + 1, (220 if level == 'hi' else 90) // 4, 5, seed=7)
    samp = dem_multi([8, 7, 5] if level == 'hi' else [7, 5])
    out = np.zeros((H, W, 3), np.uint8)
    S, PAD = 640, 24
    ex = 2.6 if level == 'hi' else 1.7
    az, alt = math.radians(315), math.radians(42)
    step = 2 if level == 'hi' else 5
    for r0 in range(0, H, S):
        a0, a1 = max(0, r0 - PAD), min(H, r0 + S + PAD)
        X, Y = np.meshgrid(xs, ys[a0:a1]); lon, lat = INV.transform(X, Y)
        lo_ = landonly[a0:a1]
        dem = samp(lon.astype(np.float64), lat.astype(np.float64))
        dem = np.where(lo_ > 0.5, np.maximum(dem, 0), 0).astype(np.float32)
        sm = ndimage.gaussian_filter(dem, 1.1 if level == 'hi' else 1.4)
        gy, gx = np.gradient(sm, res * 1000); gx *= ex; gy *= ex
        slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
        shade = np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)
        rel = (shade - np.sin(alt)).astype(np.float32)
        hnorm = np.clip(sm / 1800, 0, 1).astype(np.float32)[..., None]
        low = np.array([0.918, 0.893, 0.808], np.float32); up = np.array([0.905, 0.850, 0.760], np.float32)
        col = low * (1 - hnorm) + up * hnorm
        col = col * (1 + 0.75 * np.clip(rel, -0.6, 0.4)[..., None]) - 0.015 * np.clip(-rel, 0, 1)[..., None]
        mott = ndimage.zoom(mq, 4, order=1)[a0:a1, :W][..., None] if False else ndimage.map_coordinates(
            mq, np.meshgrid(np.arange(a0, a1) / 4.0, np.arange(W) / 4.0, indexing='ij'), order=1).astype(np.float32)[..., None]
        col = col * (0.965 + 0.06 * mott)
        water = 1 - lo_
        d_ = dist[a0:a1]
        deep = np.clip(d_ / 260, 0, 1)[..., None]
        sea = SEA * (1 - deep) + SEA_DEEP * deep
        sea = sea * (0.975 + 0.05 * mott)
        lines = np.zeros(d_.shape, np.float32)
        lw = max(res, 0.55 if level == 'hi' else 1.1)
        for i, d in enumerate([2.2, 5.5, 9.5, 15, 22, 31]):
            dd = d * (1.0 if level == 'hi' else 2.0)
            lines = np.maximum(lines, np.exp(-((d_ - dd) / lw) ** 2) * (0.55 - i * 0.075))
        lines *= (water > 0.5)
        sea = sea * (1 - 0.30 * lines[..., None]) + np.array([0.35, 0.42, 0.42], np.float32) * 0.30 * lines[..., None]
        img = col * lo_[..., None] + sea * water[..., None]
        edge = np.abs(ndimage.sobel(lo_, 0)) + np.abs(ndimage.sobel(lo_, 1))
        edge = np.clip(edge / 2.0, 0, 1)
        if level == 'hi': edge = ndimage.gaussian_filter(edge, 0.6)
        img = img * (1 - 0.55 * edge[..., None]) + INK * 0.55 * edge[..., None]
        def gl(v):
            dg = np.abs(((v + step / 2) % step) - step / 2)
            return np.exp(-(dg * (111 / res) / (0.7 if level == 'hi' else 0.6)) ** 2)
        g = (np.maximum(gl(lon), gl(lat)) * 0.16).astype(np.float32)
        img = img * (1 - g[..., None]) + np.array([0.45, 0.38, 0.30], np.float32) * g[..., None]
        k0 = r0 - a0; k1 = k0 + min(S, H - r0)
        out[r0:r0 + (k1 - k0)] = (np.clip(img[k0:k1], 0, 1) * 255).astype(np.uint8)
        print(level, 'rows', r0, flush=True)
    Image.fromarray(out).save(D + f'base_{level}.png', optimize=False, compress_level=1)
    json.dump(e | {'W': W, 'H': H}, open(D + f'base_{level}.json', 'w'))

if __name__ == '__main__':
    import sys
    for lv in (sys.argv[1:] or ['lo', 'hi']): build(lv)
