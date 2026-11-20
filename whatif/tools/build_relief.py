"""Pre-render a hill-shade + land mask raster in the project projection (LAEA 24E 52N, metres).
DEM: Terrarium tiles z8 (AWS Terrain Tiles; inherited from the 1772 project). Land mask: Natural Earth via layers.pkl.
Output: data/relief.npz with shade (uint8), land (uint8), extent (x0, y0, x1, y1, res)."""
import glob, pickle, numpy as np, skia
from PIL import Image
from scipy import ndimage
from pyproj import Transformer
import sys
RES = float(sys.argv[1]) if len(sys.argv) > 1 else 650.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'data/relief.npz'
X0, X1, Y0, Y1 = -1500e3, 1700e3, -1650e3, 1350e3
INV = Transformer.from_crs('+proj=laea +lat_0=52 +lon_0=24 +datum=WGS84 +units=m', 4326, always_xy=True)
tiles = {}
for f in glob.glob('data/dem8/8_*.png'):
    _, x, y = f.split('/')[-1][:-4].split('_'); tiles[(int(x), int(y))] = f
xs = sorted({k[0] for k in tiles}); ys = sorted({k[1] for k in tiles})
M = np.zeros(((ys[-1] - ys[0] + 1) * 256, (xs[-1] - xs[0] + 1) * 256), np.float32)
for (x, y), f in tiles.items():
    a = np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
    M[(y - ys[0]) * 256:(y - ys[0] + 1) * 256, (x - xs[0]) * 256:(x - xs[0] + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
w, h = int((X1 - X0) / RES), int((Y1 - Y0) / RES)
gx, gy = np.meshgrid(X0 + (np.arange(w) + .5) * RES, Y1 - (np.arange(h) + .5) * RES)
lon, lat = INV.transform(gx, gy)
n = 256
px = (lon + 180) / 360 * n * 256 - xs[0] * 256
r = np.radians(np.clip(lat, -85, 85))
py = (1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * n * 256 - ys[0] * 256
z = ndimage.map_coordinates(M, [py, px], order=1, mode='nearest').reshape(h, w)
inside = (px >= 0) & (py >= 0) & (px < M.shape[1] - 1) & (py < M.shape[0] - 1)
z = np.where(inside.reshape(h, w), np.maximum(z, 0), 0)
z = ndimage.gaussian_filter(z, 0.8)
dzdy, dzdx = np.gradient(z, RES)
ex = 9.0
nx, ny = -dzdx * ex, dzdy * ex          # image rows go south; flip y so +ny is north
nz = np.ones_like(z)
nl = np.sqrt(nx ** 2 + ny ** 2 + 1)
az, alt = np.radians(315), np.radians(38)
lx, ly, lz = np.cos(alt) * np.cos(np.pi / 2 - az), np.cos(alt) * np.sin(np.pi / 2 - az), np.sin(alt)
shade = (nx * lx + ny * ly + nz * lz) / nl
flat = lz
s_local = np.clip(0.5 + (shade - flat) * 1.6, 0, 1)
# broad-scale shading (landform), computed on a smoothed surface -> 'ambient' depth
zb = ndimage.gaussian_filter(z, 6)
gy2, gx2 = np.gradient(zb, RES); nb = np.sqrt((gx2 * 14) ** 2 + (gy2 * 14) ** 2 + 1)
s_broad = np.clip(0.5 + (((-gx2 * 14) * lx + (gy2 * 14) * ly + lz) / nb - lz) * 2.2, 0, 1)
s = np.clip(0.62 * s_local + 0.38 * s_broad, 0, 1)
# land mask
L = pickle.load(open('data/layers.pkl', 'rb'))
arr = np.zeros((h, w, 4), np.uint8); surf = skia.Surface(arr)
with surf as c:
    c.translate(-X0 / RES, Y1 / RES); c.scale(1 / RES, -1 / RES)
    p = skia.Path()
    for poly in getattr(L['land'], 'geoms', [L['land']]):
        for ring in [poly.exterior, *poly.interiors]:
            q = np.asarray(ring.coords); p.moveTo(*q[0]); [p.lineTo(*v) for v in q[1:]]; p.close()
    p.setFillType(skia.PathFillType.kEvenOdd)
    c.drawPath(p, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
land = arr[..., 3]
height = np.clip(z / 2500, 0, 1)
import cv2
sea = (land < 128).astype(np.uint8)
dist = cv2.distanceTransform(sea, cv2.DIST_L2, 5) * RES / 1000.0   # km from coast
np.savez_compressed(OUT, shade=(s * 255).astype(np.uint8), land=land, height=(height * 255).astype(np.uint8),
                    seadist=np.clip(dist, 0, 255).astype(np.uint8),
                    extent=np.array([X0, Y0, X1, Y1, RES]))
Image.fromarray((s * 255).astype(np.uint8)).resize((w // 4, h // 4)).save(OUT.replace('.npz', '_preview.png'))
print(w, h, 'done')
