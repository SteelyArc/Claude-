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

LEVELS = {'lo': dict(x0=-3600, x1=3600, y0=-2700, y1=3300, res=1.25),
          'hi': dict(x0=-1000, x1=1250, y0=-800, y1=1150, res=0.3)}

# ---------------- palette (linear-ish sRGB 0..1)
PAPER = np.array([0.937, 0.905, 0.835])   # warm ivory
LAND = np.array([0.925, 0.889, 0.806])
SEA = np.array([0.776, 0.812, 0.792])      # muted grey-green blue
SEA_DEEP = np.array([0.722, 0.769, 0.757])
INK = np.array([0.30, 0.25, 0.19])

def dem_sampler(z=7):
    tiles = {}
    for f in glob.glob(D + ('dem/7_*.png' if z == 7 else 'dem5/5_*.png')):
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
    landonly = np.clip(land - lakes, 0, 1)
    # DEM in blocks
    samp = dem_sampler(7 if level == 'hi' else 5); dem = np.zeros((H, W), np.float32)
    for r0 in range(0, H, 512):
        X, Y = np.meshgrid(xs, ys[r0:r0 + 512]); lon, lat = INV.transform(X, Y)
        dem[r0:r0 + 512] = samp(lon, lat)
    dem = np.where(landonly > 0.5, np.maximum(dem, 0), 0)
    sm = ndimage.gaussian_filter(dem, 1.2 if level == 'hi' else 1.8)
    gy, gx = np.gradient(sm, res * 1000)
    ex = 2.6 if level == 'hi' else 1.7
    gx *= ex; gy *= ex
    az, alt = math.radians(315), math.radians(42)
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    shade = np.clip(shade, 0, 1)
    flat = np.sin(alt)
    rel = (shade - flat)  # >0 lit, <0 shadow
    # land colour: parchment, lowlands slightly greener, uplands warmer
    hnorm = np.clip(sm / 1800, 0, 1)[..., None]
    low = np.array([0.918, 0.893, 0.808]); up = np.array([0.905, 0.850, 0.760])
    col = low * (1 - hnorm) + up * hnorm
    col = col * (1 + 0.75 * np.clip(rel, -0.6, 0.4)[..., None]) - 0.015 * np.clip(-rel, 0, 1)[..., None]
    # world-space paper mottling
    mott = fbm(H, W, 220 if level == 'hi' else 90, 5, seed=7)[..., None]
    col = col * (0.965 + 0.06 * mott)
    # sea + engraved coastal lines
    water = 1 - landonly
    dist = ndimage.distance_transform_edt(water > 0.5) * res  # km from land
    sea = SEA[None, None] * np.ones((H, W, 1))
    deep = np.clip(dist / 260, 0, 1)[..., None]
    sea = sea * (1 - deep) + SEA_DEEP * deep
    sea = sea * (0.975 + 0.05 * mott)
    lines = np.zeros((H, W), np.float32)
    lw = max(res, 0.55 if level == 'hi' else 1.1)
    for i, d in enumerate([2.2, 5.5, 9.5, 15, 22, 31]):
        dd = d * (1.0 if level == 'hi' else 2.0)
        a = np.exp(-((dist - dd) / lw) ** 2) * (0.55 - i * 0.075)
        lines = np.maximum(lines, a)
    lines *= (water > 0.5)
    sea = sea * (1 - 0.30 * lines[..., None]) + np.array([0.35, 0.42, 0.42]) * 0.30 * lines[..., None]
    img = col * landonly[..., None] + sea * water[..., None]
    # coastline ink (soft dark edge)
    edge = np.abs(ndimage.sobel(landonly, 0)) + np.abs(ndimage.sobel(landonly, 1))
    edge = np.clip(edge / 2.0, 0, 1)
    if level == 'hi': edge = ndimage.gaussian_filter(edge, 0.6)
    img = img * (1 - 0.55 * edge[..., None]) + INK * 0.55 * edge[..., None]
    # graticule every 2 degrees (hi) / 5 degrees (lo)
    X, Y = np.meshgrid(xs[::4], ys[::4]); lon, lat = INV.transform(X, Y)
    lon = ndimage.zoom(lon, (H / lon.shape[0], W / lon.shape[1]), order=1)[:H, :W]
    lat = ndimage.zoom(lat, (H / lat.shape[0], W / lat.shape[1]), order=1)[:H, :W]
    step = 2 if level == 'hi' else 5
    def gl(v):
        d = np.abs(((v + step / 2) % step) - step / 2)
        pxdeg = 111 / res
        return np.exp(-(d * pxdeg / (0.7 if level == 'hi' else 0.6)) ** 2)
    g = np.maximum(gl(lon), gl(lat)) * 0.16
    img = img * (1 - g[..., None]) + np.array([0.45, 0.38, 0.30]) * g[..., None]
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(out).save(D + f'base_{level}.png', optimize=False, compress_level=1)
    np.save(D + f'landmask_{level}.npy', (landonly * 255).astype(np.uint8))
    json.dump(e | {'W': W, 'H': H}, open(D + f'base_{level}.json', 'w'))

if __name__ == '__main__':
    import sys
    for lv in (sys.argv[1:] or ['lo', 'hi']): build(lv)
