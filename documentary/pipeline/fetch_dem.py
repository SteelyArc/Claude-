"""Download AWS Terrain Tiles (terrarium) and build the two DEM mosaics used by maps2.py."""
import math, subprocess, os, numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(__file__), "..", "assets", "dem"); os.makedirs(D, exist_ok=True)
def build(name, z, lon0, lon1, lat0, lat1):
    tx = lambda lon: (lon + 180) / 360 * 2 ** z
    ty = lambda lat: (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * 2 ** z
    x0, x1, y0, y1 = int(tx(lon0)), int(tx(lon1)), int(ty(lat1)), int(ty(lat0))
    mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            f = os.path.join(D, f"{z}_{x}_{y}.png")
            if not os.path.exists(f):
                subprocess.run(["curl", "-s", "-m", "60", "-o", f, f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"])
            a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
            mos[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    np.save(os.path.join(D, name + ".npy"), mos); open(os.path.join(D, name + ".txt"), "w").write(f"{z} {x0} {y0}")
build("mosaic", 6, 4, 44, 40, 63)
build("world_z4", 4, -40, 90, 10, 80)
