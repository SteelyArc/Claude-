"""Map designs M7-M12: terrain relief, field notebook, orbital globe, extruded blocks,
dot matrix, and the 1794 campaign map. Reuses geometry from geom.py / maps.py."""
import os, sys, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.patches import FancyArrowPatch, Rectangle, Polygon as MPoly
from scipy.ndimage import map_coordinates, gaussian_filter
import pyproj
from shapely.ops import transform, unary_union
from shapely.geometry import Point, box, Polygon
from shapely import prepared

sys.path.insert(0, os.path.dirname(__file__))
import geom, maps
from maps import fill, lines, poly_path, noise, stage_regions, POWER_NAME, LABEL_AT, AREAS, STAGE_TXT

ROOT = maps.ROOT
DEM_DIR = os.path.join(ROOT, "assets", "dem")
W, H = 1920, 1080


# ---------------------------------------------------------------- frame helpers
class Frame:
    def __init__(self, proj, center, half_w):
        self.T = pyproj.Transformer.from_crs("EPSG:4326", proj, always_xy=True)
        self.Ti = pyproj.Transformer.from_crs(proj, "EPSG:4326", always_xy=True)
        cx, cy = self.T.transform(*center)
        hh = half_w * 9 / 16
        self.ext = (cx - half_w, cx + half_w, cy - hh, cy + hh)

    def P(self, g):
        return transform(lambda x, y, z=None: self.T.transform(x, y), g)

    def pt(self, lon, lat):
        return self.T.transform(lon, lat)

    def fig(self, bg):
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(self.ext[0], self.ext[1]); ax.set_ylim(self.ext[2], self.ext[3])
        ax.set_aspect("equal"); ax.axis("off"); fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
        return fig, ax

    def img(self, ax, arr, z=1, alpha=None):
        ax.imshow(arr, extent=self.ext, zorder=z, interpolation="bicubic", alpha=alpha)

    def grid_lonlat(self, w=960, h=540):
        xs = np.linspace(self.ext[0], self.ext[1], w); ys = np.linspace(self.ext[3], self.ext[2], h)
        X, Y = np.meshgrid(xs, ys)
        lon, lat = self.Ti.transform(X, Y)
        return np.asarray(lon), np.asarray(lat), (self.ext[1] - self.ext[0]) / w * 1000


_dem = {}
def dem_at(lon, lat, name="mosaic"):
    if name not in _dem:
        _dem[name] = (np.load(os.path.join(DEM_DIR, name + ".npy")),
                      *map(int, open(os.path.join(DEM_DIR, name + ".txt")).read().split()))
    m, z, x0, y0 = _dem[name]
    ok = np.isfinite(lon) & np.isfinite(lat)
    lon = np.where(ok, lon, 0); lat = np.clip(np.where(ok, lat, 0), -85, 85)
    tx = ((lon + 180) / 360 * 2 ** z - x0) * 256
    r = np.radians(lat)
    ty = ((1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * 2 ** z - y0) * 256
    e = map_coordinates(m, [ty, tx], order=1, mode="nearest")
    return np.where(ok, e, np.nan)


def hillshade(e, cell_m, az=315, alt=40, exag=6.0):
    e = np.nan_to_num(e)
    gy, gx = np.gradient(e * exag, cell_m)
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, b = np.radians(az), np.radians(alt)
    hs = np.sin(b) * np.sin(slope) + np.cos(b) * np.cos(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1)


def ramp(v, stops):
    xs = [s[0] for s in stops]; cs = np.array([s[1] for s in stops], float) / 255
    return np.stack([np.interp(v, xs, cs[:, i]) for i in range(3)], -1)


def proj_geoms(F):
    g = geom.build()
    return {k: maps.drop_slivers(F.P(v.simplify(0.005)).buffer(0)) for k, v in g.items()}


def regions(Gp, stage):
    return stage_regions(Gp, stage)


def caption(fig, txt, color, font="Inter", size=11):
    fig.text(0.985, 0.018, txt, color=color, fontsize=size, family=font, ha="right", va="bottom", alpha=0.85, zorder=200)


def lab(ax, x, y, s, color, size, font, halo=None, hw=4, **kw):
    fx = [pe.withStroke(linewidth=hw, foreground=halo)] if halo else None
    ax.text(x, y, s, color=color, fontsize=size, family=font, path_effects=fx, zorder=60, **kw)


def city_pt(F, ax, name, color, size, font, halo=None, dot=4.5, dx=10, dy=6, **kw):
    x, y = F.pt(*geom.CITIES[name]); ax.plot([x], [y], "o", ms=dot, color=color, mec=halo or color, zorder=60)
    lab(ax, x + dx, y + dy, name, color, size, font, halo, **kw)


LCC = "+proj=lcc +lat_1=49 +lat_2=56 +lat_0=52 +lon_0=24 +units=km"
COL = dict(russia="#4f8f5e", prussia="#3f6fa8", austria="#d39a2c", pol="#b8322f")


# ------------------------------------------------------------- M7 Terrain Relief
def m7_terrain(stage, out):
    F = Frame(LCC, (23.6, 52.3), 1000); Gp = proj_geoms(F); R = regions(Gp, stage)
    lon, lat, cell = F.grid_lonlat()
    e = dem_at(lon, lat)
    hs = hillshade(e, cell, exag=9)
    land = ramp(np.clip(e, 0, 3000), [(0, (120, 140, 96)), (150, (150, 160, 110)), (400, (176, 166, 120)),
                                      (900, (168, 140, 100)), (1800, (150, 130, 115)), (3000, (235, 235, 235))])
    sea = ramp(np.clip(-e, 0, 300), [(0, (92, 132, 160)), (60, (60, 100, 135)), (300, (40, 72, 105))])
    rgb = np.where((e > 0)[..., None], land * (0.45 + 0.75 * hs[..., None]), sea)
    fig, ax = F.fig("#284660"); F.img(ax, np.clip(rgb, 0, 1))
    for k, g in R["old"].items():
        fill(ax, g, fc=COL[k], ec="none", alpha=0.25, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g, fc=COL[k], ec="none", alpha=0.55, zorder=5)
        lines(ax, g, color="#101010", lw=2.6, alpha=0.6, zorder=6); lines(ax, g, color="#f2efe6", lw=1.1, zorder=6)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc=COL["pol"], ec="none", alpha=0.42, zorder=5)
        lines(ax, R["pol"], color="#101010", lw=3, alpha=0.6, zorder=6); lines(ax, R["pol"], color="#ffd9d4", lw=1.3, zorder=6)
    for k, gr in maps.data()["rivers"].items():
        lines(ax, F.P(transform(lambda x, y, z=None: maps.T.transform(x, y, direction="INVERSE"), gr)), color="#3d6f95", lw=1.0, alpha=0.8, zorder=7)
    for c in ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Kyiv", "Riga", "Königsberg", "Poznań", "Berlin", "Vienna"]:
        city_pt(F, ax, c, "#ffffff", 13, "EB Garamond", halo="#1a1a1a", weight="semibold")
    for k, (lo, la) in LABEL_AT.get(stage, {}).items():
        x, y = F.pt(lo, la); lab(ax, x, y, POWER_NAME[k].upper(), "#ffffff", 16, "Cinzel", "#151515", 4, ha="center", weight="bold")
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.04, 0.9, tt.title(), family="Cinzel", fontsize=36, color="#ffffff", weight="bold",
             path_effects=[pe.withStroke(linewidth=6, foreground="#00000088")])
    fig.text(0.04, 0.86, yr + " · " + sub, family="EB Garamond", fontsize=20, color="#f0ece0", style="italic",
             path_effects=[pe.withStroke(linewidth=4, foreground="#00000066")])
    caption(fig, "Borders approximate · terrain: Mapzen/AWS Terrain Tiles", "#f0f0f0")
    fig.savefig(out, dpi=100); plt.close(fig)


# ------------------------------------------------------------- M8 Field Notebook
def crumple(h, w, seed=7):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    f = np.zeros((h, w), np.float32)
    for _ in range(26):  # random creases: ridges along random lines
        a = rng.uniform(0, np.pi); c = rng.uniform(-w, w)
        d = (x * np.cos(a) + y * np.sin(a) - c - w / 2)
        f += rng.uniform(0.3, 1) * np.sign(d) * np.exp(-np.abs(d) / rng.uniform(40, 180))
    f += gaussian_filter(rng.standard_normal((h, w)), 12) * 3
    gy, gx = np.gradient(gaussian_filter(f, 1.5))
    return np.clip(1.0 + (gx - gy) * 3.5, 0.7, 1.12)


def m8_notebook(stage, out):
    F = Frame(LCC, (22.3, 52.8), 950); Gp = proj_geoms(F); R = regions(Gp, stage)
    D = maps.data()
    fig, ax = F.fig("#efe9dc")
    fill(ax, box(*[F.ext[i] for i in (0, 2, 1, 3)]), fc="#cfd8d6", ec="none", zorder=1)
    shade = gaussian_filter(crumple(540, 960), 2.5)
    landp = F.P(transform(lambda x, y, z=None: maps.T.transform(x, y, direction="INVERSE"), D["land"]))
    fill(ax, landp, fc="#e2dccd", ec="#8a8478", lw=0.8, zorder=2)
    for k, g in R["old"].items():
        fill(ax, g, fc=COL[k], ec="none", alpha=0.18, zorder=3)
    rng = np.random.default_rng(1)
    hl = dict(russia="#5fd08a", prussia="#5aa8ff", austria="#ffd23c")
    for k, g in R["new"].items():  # highlighter: translucent, slightly offset double pass
        for dx, dy in [(0, 0), (6, -4)]:
            fill(ax, transform(lambda x, y, z=None: (x + dx, y + dy), g), fc=hl[k], ec="none", alpha=0.38, zorder=4)
    if R["pol"] is not None:
        lines(ax, R["pol"].simplify(4), color="#c0262d", lw=3.2, alpha=0.9, zorder=6, solid_capstyle="round")
    lines(ax, Gp["plc"].simplify(4), color="#2b2b2b", lw=1.4, ls=(0, (5, 4)), alpha=0.7, zorder=6)
    for c in ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Poznań", "Königsberg", "Riga"]:
        city_pt(F, ax, c, "#2a2a2a", 21, "Caveat", dot=5)
    names = dict(russia="Russia", prussia="Prussia", austria="Austria")
    for k, (lo, la) in LABEL_AT.get(stage, {}).items():
        x, y = F.pt(lo, la); lab(ax, x, y, names[k], "#1d1d1d", 30, "Permanent Marker", ha="center")
    if stage == "1772":  # true annotation: Gdańsk & Toruń remain Polish until 1793
        gx, gy = F.pt(18.65, 54.35)
        ax.add_patch(matplotlib.patches.Ellipse((gx, gy), 120, 85, angle=-12, fill=False, ec="#c0262d", lw=3, zorder=8))
        ax.annotate("", xy=(gx - 45, gy + 30), xytext=(gx - 300, gy - 110), zorder=8,
                    arrowprops=dict(arrowstyle="-|>", color="#c0262d", lw=2.5, connectionstyle="arc3,rad=-0.3", mutation_scale=22))
        lab(ax, gx - 420, gy - 170, "Gdańsk & Toruń stay\nPolish until 1793!", "#c0262d", 28, "Caveat", weight="bold", ha="center")
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.045, 0.86, yr, family="Permanent Marker", fontsize=70, color="#c0262d", zorder=100)
    fig.text(0.045, 0.81, tt.title(), family="Caveat", fontsize=38, color="#222", zorder=100, weight="bold")
    # tape strips
    for (x, y, a) in [(0.02, 0.95, 18), (0.93, 0.07, -22)]:
        fig.patches.append(Rectangle((x, y), 0.08, 0.03, angle=a, transform=fig.transFigure, fc="#f3e7a8", ec="none", alpha=0.75, zorder=150))
    ov = np.zeros((540, 960, 4)); dark = np.clip(1 - shade, 0, 1); lite = np.clip(shade - 1, 0, 1)
    ov[..., 3] = np.clip(dark * 1.6, 0, 0.45); F.img(ax, ov, z=90)
    ov2 = np.ones((540, 960, 4)); ov2[..., 3] = np.clip(lite * 2.5, 0, 0.35); F.img(ax, ov2, z=91)
    caption(fig, "Borders approximate", "#555", "Caveat", 18)
    fig.savefig(out, dpi=100); plt.close(fig)


# ------------------------------------------------------------- M9 Orbital Globe
def m9_globe(stage, out):
    proj = "+proj=ortho +lat_0=0 +lon_0=24 +units=km"
    F = Frame(proj, (24, 57.5), 2700)
    Gp = proj_geoms(F); R = regions(Gp, stage)
    lon, lat, cell = F.grid_lonlat()
    xs = np.linspace(F.ext[0], F.ext[1], 960); ys = np.linspace(F.ext[3], F.ext[2], 540)
    X, Y = np.meshgrid(xs, ys); r = np.hypot(X, Y) / 6371
    on = r < 1
    e = np.nan_to_num(dem_at(np.where(on, lon, 0), np.where(on, lat, 0), "world_z4"), nan=-200.0)
    hs = hillshade(gaussian_filter(np.nan_to_num(e), 0.8), cell, az=300, alt=35, exag=10)
    hs = np.where(r > 0.97, 0.75, hs)
    land = ramp(np.clip(e, 0, 3000), [(0, (40, 58, 34)), (300, (64, 70, 44)), (1000, (92, 82, 62)), (2500, (170, 165, 160))])
    sea = ramp(np.clip(-e, 0, 3000), [(0, (22, 48, 74)), (200, (16, 38, 66)), (3000, (12, 30, 58))])
    rgb = np.where((e > 0)[..., None], land * (0.35 + 0.9 * hs[..., None]), sea)
    limb = np.clip(1 - r, 0, 1) ** 0.2
    rgb = rgb * (0.6 + 0.4 * limb[..., None])
    atm = (np.exp(-np.abs(r - 1) * 45) + np.where(r < 1, np.exp(-(1 - r) * 12) * 0.35, 0))[..., None] * np.array([0.35, 0.6, 1.0])
    space = np.zeros_like(rgb)
    img = np.where(on[..., None], rgb, space) + atm * (0.9 if True else 0)
    fig, ax = F.fig("#000000"); F.img(ax, np.clip(img, 0, 1))
    gl = dict(russia="#55e08f", prussia="#5aa9ff", austria="#ffc94a")
    for k, g in R["old"].items():
        fill(ax, g, fc=gl[k], ec="none", alpha=0.12, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g, fc=gl[k], ec="none", alpha=0.3, zorder=5)
        maps.glow(ax, g, gl[k], 6, widths=(10, 5, 2.5, 1.0))
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#ff4a4a", ec="none", alpha=0.28, zorder=5); maps.glow(ax, R["pol"], "#ff6a6a", 7, widths=(10, 5, 2.5, 1.0))
    for c in ["Warsaw", "Vilnius", "Kraków", "Berlin", "Vienna", "Kyiv"]:
        city_pt(F, ax, c, "#e8f0ff", 12, "Inter", dot=3, halo="#000000", hw=3)
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.05, 0.12, tt, family="Oswald", fontsize=34, color="#ffffff", zorder=100)
    fig.text(0.05, 0.085, yr, family="Inter", fontsize=20, color="#9fc4ff", zorder=100)
    caption(fig, "Borders approximate · terrain: Mapzen/AWS Terrain Tiles", "#7d8ea8")
    fig.savefig(out, dpi=100); plt.close(fig)


# ------------------------------------------------------------- M10 Extruded Blocks
def m10_blocks(stage, out):
    F = Frame(LCC, (23.6, 52.0), 1000); Gp = proj_geoms(F); R = regions(Gp, stage)
    D = maps.data()
    # oblique "tilt": squash y and lift each piece by a height (screen-space extrusion)
    sq = 0.62
    tilt = lambda g, h=0: transform(lambda x, y, z=None: (x, (y - F.ext[2]) * sq + F.ext[2] + 120 + h), g)
    fig, ax = F.fig("#1d2329")
    yy = np.linspace(0, 1, 540)[:, None] * np.ones((1, 960))
    F.img(ax, np.stack([0.11 + 0.08 * yy, 0.13 + 0.09 * yy, 0.16 + 0.1 * yy], -1)[::-1], z=0)
    landp = F.P(transform(lambda x, y, z=None: maps.T.transform(x, y, direction="INVERSE"), D["land"])).simplify(3)
    fill(ax, tilt(landp), fc="#3a434c", ec="#4d5761", lw=0.6, zorder=2)
    def slab(g, color, h, z):
        g = g.simplify(3)
        for i in range(0, int(h), 3):  # side walls
            fill(ax, tilt(g, i), fc=np.array(matplotlib.colors.to_rgb(color)) * 0.55, ec="none", zorder=z)
        fill(ax, tilt(g, h).buffer(14), fc="#000000", ec="none", alpha=0.0, zorder=z)
        fill(ax, tilt(g, h), fc=color, ec="#ffffff", lw=0.8, zorder=z + 0.5)
    order = sorted(list(R["old"].items()), key=lambda kv: -kv[1].centroid.y)
    for k, g in order:
        slab(g, matplotlib.colors.to_hex(np.array(matplotlib.colors.to_rgb(COL[k])) * 0.75), 8, 3)
    if R["pol"] is not None:
        slab(R["pol"], "#c8423e", 16, 4)
    newo = sorted(list(R["new"].items()), key=lambda kv: -kv[1].centroid.y)
    for k, g in newo:  # newly taken land rises off the board
        slab(g, COL[k], 70, 5)
    for k, (lo, la) in LABEL_AT.get(stage, {}).items():
        x, y = F.pt(lo, la); tx, ty = tilt(Point(x, y), 70).coords[0]
        lab(ax, tx, ty, POWER_NAME[k].upper(), "#ffffff", 16, "Oswald", "#111", 4, ha="center")
        lab(ax, tx, ty - 34, AREAS[stage][k], "#ffffff", 13, "Inter", "#111", 3, ha="center")
    for c in ["Warsaw", "Vilnius", "Kraków"]:
        x, y = F.pt(*geom.CITIES[c]); tx, ty = tilt(Point(x, y), 16).coords[0]
        ax.plot([tx], [ty], "o", color="#fff", ms=4, zorder=20); lab(ax, tx + 10, ty + 6, c, "#fff", 12, "Inter", "#111", 3)
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.04, 0.9, yr, family="Oswald", fontsize=60, color="#ffffff", weight="bold", zorder=100)
    fig.text(0.04, 0.86, tt, family="Oswald", fontsize=22, color="#ff7a6e", zorder=100)
    fig.text(0.04, 0.83, "Each newly annexed territory rises off the board", family="Inter", fontsize=14, color="#aeb8c2", zorder=100)
    caption(fig, "Borders approximate", "#8592a0")
    fig.savefig(out, dpi=100); plt.close(fig)


# ------------------------------------------------------------- M11 Dot Matrix
def m11_dots(stage, out):
    F = Frame(LCC, (23.6, 52.3), 1000); Gp = proj_geoms(F); R = regions(Gp, stage)
    D = maps.data()
    landp = prepared.prep(F.P(transform(lambda x, y, z=None: maps.T.transform(x, y, direction="INVERSE"), D["land"])).buffer(0))
    fig, ax = F.fig("#0d1b2a")
    step = 16
    xs = np.arange(F.ext[0], F.ext[1], step); ys = np.arange(F.ext[2], F.ext[3], step * 0.866)
    pts = [(x + (step / 2 if j % 2 else 0), y) for j, y in enumerate(ys) for x in xs]
    layers = [("pol", R["pol"], "#ff5c5c", 1.0)] if R["pol"] is not None else []
    layers += [(k, g, {"russia": "#3ddc97", "prussia": "#4ea8ff", "austria": "#ffc145"}[k], 1.0) for k, g in R["new"].items()]
    layers += [(k, g, {"russia": "#3ddc97", "prussia": "#4ea8ff", "austria": "#ffc145"}[k], 0.4) for k, g in R["old"].items()]
    preps = [(prepared.prep(g), c, a) for _, g, c, a in layers]
    cols, sizes, xy = [], [], []
    for p in pts:
        P_ = Point(p)
        if not landp.contains(P_):
            continue
        c, a, s = (0.30, 0.38, 0.48), 0.55, 9
        for pg, cc, aa in preps:
            if pg.contains(P_):
                c = matplotlib.colors.to_rgb(cc); a = aa; s = 30 if aa == 1.0 else 18; break
        xy.append(p); cols.append((*c, a)); sizes.append(s)
    xy = np.array(xy); ax.scatter(xy[:, 0], xy[:, 1], s=sizes, c=cols, linewidths=0, zorder=3)
    for c in ["Warsaw", "Vilnius", "Kraków", "Gdańsk", "Lwów", "Minsk", "Berlin", "Vienna", "Kyiv"]:
        city_pt(F, ax, c, "#ffffff", 12, "Inter", halo="#0d1b2a", hw=4, dot=4)
    for k, (lo, la) in LABEL_AT.get(stage, {}).items():
        x, y = F.pt(lo, la); lab(ax, x, y, POWER_NAME[k].upper(), "#ffffff", 15, "Inter", "#0d1b2a", 5, ha="center", weight="bold")
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.04, 0.905, yr, family="Inter", fontsize=60, color="#ffffff", weight="bold", zorder=100)
    fig.text(0.04, 0.865, tt, family="Inter", fontsize=20, color="#ff5c5c", weight="bold", zorder=100)
    fig.text(0.04, 0.835, "1 dot ≈ 220 km²", family="Inter", fontsize=13, color="#7f93a8", zorder=100)
    caption(fig, "Borders approximate", "#6b7f94")
    fig.savefig(out, dpi=100); plt.close(fig)


# ------------------------------------------------------------- M12 Campaign Map 1794
EVENTS_1794 = [  # (lon, lat, label, date, kind) — documented events of the Kościuszko Uprising
    (19.94, 50.06, "Kraków", "24 Mar · Act of Insurrection", "start"),
    (20.23, 50.32, "Racławice", "4 Apr · Polish victory", "win"),
    (21.01, 52.23, "Warsaw", "17–18 Apr · rising; siege Jul–Sep", "city"),
    (25.28, 54.69, "Vilnius", "22–23 Apr · rising", "city"),
    (19.82, 50.63, "Szczekociny", "6 Jun · defeat", "loss"),
    (21.56, 51.69, "Maciejowice", "10 Oct · defeat; Kościuszko captured", "loss"),
    (21.06, 52.25, "Praga", "4 Nov · stormed by Suvorov", "loss"),
]


def m12_campaign(out, stage="1794"):
    F = Frame(LCC, (21.25, 51.3), 420); Gp = proj_geoms(F)
    lon, lat, cell = F.grid_lonlat()
    e = dem_at(lon, lat); hs = hillshade(e, cell, exag=5)
    base = ramp(np.clip(e, 0, 1500), [(0, (226, 216, 190)), (300, (214, 200, 170)), (1500, (180, 160, 130))])
    rgb = np.where((e > 0)[..., None], base * (0.7 + 0.4 * hs[..., None]), np.array([0.70, 0.76, 0.76]))
    fig, ax = F.fig("#ddd3b8"); F.img(ax, np.clip(rgb, 0, 1))
    fill(ax, Gp["pol93"], fc="#b8322f", ec="#7d1b18", lw=2.2, alpha=0.18, zorder=4)
    for k, g, c in [("r", unary_union([Gp["r72"], Gp["r93"]]), "#4f8f5e"), ("p", unary_union([Gp["p72"], Gp["p93"]]), "#3f6fa8"), ("a", Gp["a72"], "#d39a2c")]:
        fill(ax, g, fc=c, ec="none", alpha=0.22, zorder=4)
    for k, gr in maps.data()["rivers"].items():
        lines(ax, F.P(transform(lambda x, y, z=None: maps.T.transform(x, y, direction="INVERSE"), gr)), color="#5b7d93", lw=1.4, alpha=0.8, zorder=5)
    def arrow(pts, color, lw=9, label=None, lpos=None):
        P = [F.pt(*p) for p in pts]
        xs, ys = zip(*P)
        ax.plot(xs[:-1] + (xs[-1],), ys, color=color, lw=lw, alpha=0.85, zorder=9, solid_capstyle="round")
        ax.add_patch(FancyArrowPatch(P[-2], P[-1], arrowstyle="-|>", mutation_scale=48, color=color, lw=0, zorder=10))
        if label:
            x, y = F.pt(*lpos); lab(ax, x, y, label, color, 19, "EB Garamond", "#efe7d2", 5, weight="bold", style="italic")
    arrow([(19.94, 50.06), (20.05, 50.2), (20.20, 50.30)], "#a3241f", label="Kościuszko, Apr", lpos=(20.4, 50.08))
    arrow([(18.6, 50.75), (19.3, 50.72), (19.75, 50.64)], "#2f5f9e", label="Prussian army, Jun", lpos=(18.35, 50.85))
    arrow([(19.85, 50.55), (19.95, 50.3), (19.97, 50.12)], "#2f5f9e", label="Prussians take\nKraków, 15 Jun", lpos=(18.45, 50.12))
    arrow([(23.65, 52.08), (22.8, 52.15), (21.8, 52.22), (21.12, 52.25)], "#3c7a4e", label="Suvorov via Brest, Sep–Nov", lpos=(22.3, 52.35))
    sym = dict(start=("*", "#a3241f", 20), win=("X", "#a3241f", 15), loss=("X", "#1f1f1f", 15), city=("o", "#3a2a1a", 8))
    for lo, la, name, date, kind in EVENTS_1794:
        x, y = F.pt(lo, la); m, c, s = sym[kind]
        ax.plot([x], [y], m, color=c, ms=s, mec="#efe7d2", mew=1.5, zorder=12)
        off = {"Praga": (14, -2), "Warsaw": (-14, 14), "Szczekociny": (-14, 10), "Kraków": (-12, -26)}.get(name, (14, 6))
        ha = "right" if off[0] < 0 else "left"
        lab(ax, x + off[0], y + off[1], name, "#1f1a14", 22, "EB Garamond", "#efe7d2", 4, weight="bold", ha=ha)
        lab(ax, x + off[0], y + off[1] - 19, date, "#3d3328", 16, "EB Garamond", "#efe7d2", 3, ha=ha, style="italic")
    fig.text(0.04, 0.9, "The Kościuszko Uprising", family="Cinzel", fontsize=34, color="#2a1f14", weight="bold", zorder=100,
             path_effects=[pe.withStroke(linewidth=6, foreground="#efe7d2")])
    fig.text(0.04, 0.865, "March – November 1794", family="EB Garamond", fontsize=20, color="#3d3328", style="italic", zorder=100,
             path_effects=[pe.withStroke(linewidth=4, foreground="#efe7d2")])
    # legend
    lx, ly = 0.04, 0.2
    for i, (m, c, t) in enumerate([("*", "#a3241f", "Insurrection proclaimed"), ("X", "#a3241f", "Polish victory"), ("X", "#1f1f1f", "Polish defeat")]):
        fig.text(lx + 0.022, ly - i * 0.035, t, family="EB Garamond", fontsize=15, color="#2a1f14", zorder=100)
        fig.lines.append(matplotlib.lines.Line2D([lx + 0.008], [ly - i * 0.035 + 0.008], marker=m, color=c, ms=12, transform=fig.transFigure, zorder=100))
    caption(fig, "Army routes schematic · borders approximate (state of 1793)", "#3d3328", "EB Garamond", 13)
    fig.savefig(out, dpi=100); plt.close(fig)


STYLES2 = {
    "M7_terrain_relief": m7_terrain,
    "M8_field_notebook": m8_notebook,
    "M9_orbital_globe": m9_globe,
    "M10_extruded_blocks": m10_blocks,
    "M11_dot_matrix": m11_dots,
}

if __name__ == "__main__":
    outdir = os.path.join(ROOT, "output", "design_options", "maps")
    only = sys.argv[1:] or list(STYLES2) + ["M12_campaign_1794"]
    for n in only:
        if n == "M12_campaign_1794":
            m12_campaign(os.path.join(outdir, "M12_campaign_1794.png"))
        else:
            STYLES2[n]("1772", os.path.join(outdir, f"{n}_1772.png"))
        print("wrote", n, flush=True)
