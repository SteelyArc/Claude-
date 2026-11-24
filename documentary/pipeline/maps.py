"""Six map design styles for the partition maps. Renders 1920x1080 frames."""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, FancyBboxPatch
from matplotlib import font_manager as fm, patheffects as pe
from scipy.ndimage import gaussian_filter
import pyproj
from shapely.ops import transform, unary_union
from shapely.geometry import Point, box

sys.path.insert(0, os.path.dirname(__file__))
import geom

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
for f in os.listdir(FONTS):
    fm.fontManager.addfont(os.path.join(FONTS, f))

T = pyproj.Transformer.from_crs("EPSG:4326", "+proj=lcc +lat_1=49 +lat_2=56 +lat_0=52 +lon_0=24 +units=km", always_xy=True)
P = lambda g: transform(lambda x, y, z=None: T.transform(x, y), g)
pt = lambda lon, lat: T.transform(lon, lat)

# frame extent in projected km (16:9)
CX, CY = pt(23.6, 52.3)
HALF_W = 1000
HALF_H = HALF_W * 9 / 16
EXT = (CX - HALF_W, CX + HALF_W, CY - HALF_H, CY + HALF_H)


def poly_path(g):
    verts, codes = [], []
    polys = list(g.geoms) if hasattr(g, "geoms") else [g]
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            verts += c.tolist(); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    return Path(verts, codes) if verts else None


def fill(ax, g, **kw):
    p = poly_path(g)
    if p is not None:
        ax.add_patch(PathPatch(p, **kw))


def lines(ax, g, **kw):
    gs = list(g.geoms) if hasattr(g, "geoms") else [g]
    for l in gs:
        if l.geom_type in ("Polygon",):
            for r in [l.exterior] + list(l.interiors):
                x, y = r.xy; ax.plot(x, y, **kw)
        elif l.geom_type == "LineString":
            x, y = l.xy; ax.plot(x, y, **kw)
        elif hasattr(l, "geoms"):
            lines(ax, l, **kw)


def noise(h, w, scales=(2, 8, 32), seed=0):
    rng = np.random.default_rng(seed)
    n = sum(gaussian_filter(rng.standard_normal((h, w)), s) * s for s in scales)
    return (n - n.min()) / (n.max() - n.min())


def drop_slivers(g, min_km2=60):
    if g.geom_type == "MultiPolygon":
        return unary_union([p.buffer(-2).buffer(2) for p in g.geoms if p.area >= min_km2])
    return g.buffer(-2).buffer(2) if g.geom_type == "Polygon" else g


STAGE_TXT = {
    "pre": ("c. 1770", "BEFORE THE PARTITIONS", "The Polish–Lithuanian Commonwealth, about 733,000 km²"),
    "1772": ("1772", "THE FIRST PARTITION", "The Commonwealth loses about 30% of its territory"),
    "1793": ("1793", "THE SECOND PARTITION", "Russia and Prussia annex further territory; Austria takes no part"),
    "1795": ("1795", "THE THIRD PARTITION", "The Commonwealth disappears from the map"),
}

_cache = {}
def data():
    if "d" in _cache:
        return _cache["d"]
    g = geom.build()
    view = box(0, 36, 50, 66)
    L = geom.land().intersection(view)
    riv = {n: geom.rivers()[n] for n in ["Vistula", "Bug", "Neman", "Daugava", "Dnieper", "Dniester", "Oder", "Warta", "Pripyat", "Neris", "Southern Bug", "Prut", "Danube"] if n in geom.rivers()}
    d = dict(land=P(L.simplify(0.01)), lakes=P(geom.lakes().intersection(view)),
             rivers={k: P(v.intersection(view)) for k, v in riv.items()},
             **{k: drop_slivers(P(v.simplify(0.005)).buffer(0)) for k, v in g.items()})
    _cache["d"] = d
    return d


def stage_regions(d, stage):
    """Return dict power -> (geometry already lost before this stage, newly lost at this stage)."""
    if stage == "pre":
        return dict(pol=unary_union([d["plc"]]), new={}, old={})
    if stage == "1772":
        return dict(pol=d["pol72"], new=dict(russia=d["r72"], prussia=d["p72"], austria=d["a72"]), old={})
    if stage == "1793":
        return dict(pol=d["pol93"], new=dict(russia=d["r93"], prussia=d["p93"]),
                    old=dict(russia=d["r72"], prussia=d["p72"], austria=d["a72"]))
    if stage == "1795":
        return dict(pol=None, new=dict(russia=unary_union([d["r95"], d["courland"]]), prussia=d["p95"], austria=d["a95"]),
                    old=dict(russia=unary_union([d["r72"], d["r93"]]), prussia=unary_union([d["p72"], d["p93"]]), austria=d["a72"]))


AREAS = {  # commonly cited figures (km2, population) for on-screen use; rounded
    "1772": {"russia": "≈92,000 km²", "prussia": "≈36,000 km²", "austria": "≈83,000 km²"},
    "1793": {"russia": "≈250,000 km²", "prussia": "≈58,000 km²"},
    "1795": {"russia": "≈120,000 km²", "prussia": "≈55,000 km²", "austria": "≈47,000 km²"},
}
POWER_NAME = {"russia": "Russian Empire", "prussia": "Kingdom of Prussia", "austria": "Habsburg Monarchy"}
LABEL_AT = {  # lon/lat label anchors for new gains per stage
    "1772": {"russia": (29.6, 55.1), "prussia": (18.9, 53.65), "austria": (23.2, 49.7)},
    "1793": {"russia": (28.3, 52.0), "prussia": (18.0, 52.3)},
    "1795": {"russia": (25.6, 54.0), "prussia": (21.9, 53.2), "austria": (21.4, 51.0)},
}
CITY_SHOW = ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Kyiv", "Riga", "Königsberg", "Poznań", "Smolensk", "Berlin", "Vienna"]


def fief(ax, d, stage, color, alpha=0.5):
    """Duchy of Courland: a fief of the Commonwealth until annexed by Russia in 1795."""
    if stage == "1795":
        return
    old = plt.rcParams["hatch.color"]; plt.rcParams["hatch.color"] = color
    fill(ax, d["courland"], fc="none", ec=color, lw=0.8, hatch="//", alpha=alpha, zorder=4)
    plt.rcParams["hatch.color"] = old


def new_fig(bg):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3])
    ax.set_aspect("equal"); ax.axis("off"); fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    return fig, ax


def bg_image(ax, rgb_a, rgb_b, seed=0, strength=1.0, scales=(2, 8, 40)):
    n = noise(540, 960, scales, seed) * strength
    img = np.asarray(rgb_a)[None, None, :] * (1 - n[..., None]) + np.asarray(rgb_b)[None, None, :] * n[..., None]
    ax.imshow(img, extent=EXT, zorder=0, interpolation="bicubic")


def vignette(ax, strength=0.6, color=(0, 0, 0)):
    y, x = np.mgrid[-1:1:540j, -1:1:960j]
    r = np.clip((np.sqrt((x * 0.9) ** 2 + (y * 1.1) ** 2) - 0.55) / 0.9, 0, 1) ** 1.6 * strength
    img = np.zeros((540, 960, 4)); img[..., :3] = color; img[..., 3] = r
    ax.imshow(img, extent=EXT, zorder=50, interpolation="bicubic")


def city(ax, name, color, size=15, font="EB Garamond", dot=5, zorder=40, halo=None, dx=12, dy=8, **kw):
    x, y = pt(*geom.CITIES[name])
    ax.plot([x], [y], "o", ms=dot, color=color, zorder=zorder, mec=halo or color)
    fx = [pe.withStroke(linewidth=3, foreground=halo)] if halo else None
    ax.text(x + dx, y + dy, name, color=color, fontsize=size, family=font, zorder=zorder, path_effects=fx, **kw)


def rivers(ax, d, color, lw=1.0, alpha=0.7, z=8):
    for k, g in d["rivers"].items():
        lines(ax, g, color=color, lw=lw * (1.4 if k in ("Vistula", "Dnieper", "Daugava", "Neman") else 0.9), alpha=alpha, zorder=z, solid_capstyle="round")


def title(ax, fig, text, sub, color, font, size=40, subsize=18, x=0.04, y=0.90, subcolor=None, ha="left", subfont=None):
    fig.text(x, y, text, color=color, fontsize=size, family=font, ha=ha, va="bottom", zorder=100)
    fig.text(x, y - 0.012, sub, color=subcolor or color, fontsize=subsize, family=subfont or font, ha=ha, va="top", zorder=100)


def note(fig, color, font="Inter", txt="Borders approximate · reconstructed from treaty lines and rivers"):
    fig.text(0.985, 0.018, txt, color=color, fontsize=11, family=font, ha="right", va="bottom", alpha=0.8)


# ---------------------------------------------------------------------------
# STYLE 1 — Cartographer's Atlas (parchment, watercolour, engraved coastlines)
# ---------------------------------------------------------------------------
def style_atlas(stage, out):
    d = data(); R = stage_regions(d, stage)
    fig, ax = new_fig("#e9dcbc")
    bg_image(ax, (0.80, 0.82, 0.76), (0.66, 0.70, 0.64), seed=3, scales=(1, 6, 60))
    # sea water-lines: concentric offsets of the coast
    for i, off in enumerate([5, 12, 21]):
        lines(ax, d["land"].buffer(off).boundary, color="#4f5a52", lw=0.6, alpha=0.4 - i * 0.1, zorder=2)
    fill(ax, d["land"], fc="#efe3c4", ec="#4a3b26", lw=1.1, zorder=3)
    fief(ax, d, stage, "#a4413b")
    col = dict(russia="#7f9a6a", prussia="#6f8fae", austria="#d0a24a")
    for k, g in R["old"].items():
        fill(ax, g, fc=col[k], ec="none", alpha=0.35, zorder=4, hatch="////")
    for k, g in R["new"].items():
        for w, a in [(0, 0.55), (-6, 0.25), (-14, 0.15)]:
            fill(ax, g.buffer(w), fc=col[k], ec="none", alpha=a, zorder=5)
        lines(ax, g, color=col[k], lw=2.2, alpha=0.9, zorder=6)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#c9706a", ec="none", alpha=0.28, zorder=5)
        fill(ax, R["pol"].buffer(-8), fc="none", ec="#a4413b", lw=1.0, alpha=0.6, zorder=6)
    lines(ax, d["plc"], color="#7a2a24", lw=2.4, ls=(0, (6, 3)), zorder=7)
    fill(ax, d["lakes"], fc="#c9c2a5", ec="#6b5a3e", lw=0.5, zorder=8)
    rivers(ax, d, "#5c7181", lw=0.9, alpha=0.75)
    for c in CITY_SHOW:
        city(ax, c, "#2b2116", size=14, font="EB Garamond", dot=4)
    for k, (lon, lat) in LABEL_AT.get(stage, {}).items():
        x, y = pt(lon, lat)
        ax.text(x, y, POWER_NAME[k].upper(), color="#2b2116", fontsize=15, family="Cinzel", ha="center", alpha=0.85, zorder=30)
    # cartouche
    fig.patches.append(FancyBboxPatch((0.03, 0.78), 0.33, 0.17, boxstyle="round,pad=0.008", transform=fig.transFigure,
                                      fc="#f3e9cf", ec="#4a3b26", lw=1.6, zorder=90))
    fig.text(0.195, 0.905, "THE FIRST PARTITION", family="Cinzel", fontsize=28, color="#3a2a18", ha="center", va="center", zorder=100)
    fig.text(0.195, 0.85, "of the Polish–Lithuanian Commonwealth · 1772", family="EB Garamond", fontsize=17, style="italic", color="#3a2a18", ha="center", va="center", zorder=100)
    fig.text(0.195, 0.805, "Russia  ·  Prussia  ·  Austria", family="EB Garamond", fontsize=15, color="#5a4630", ha="center", va="center", zorder=100)
    # compass rose
    cx, cy = EXT[1] - 150, EXT[3] - 150
    for ang, ln in [(90, 80), (270, 50), (0, 50), (180, 50)]:
        a = np.radians(ang); ax.plot([cx, cx + ln * np.cos(a)], [cy, cy + ln * np.sin(a)], color="#3a2a18", lw=1.6, zorder=60)
    ax.text(cx, cy + 95, "N", family="Cinzel", fontsize=18, ha="center", color="#3a2a18", zorder=60)
    ax.add_patch(plt.Circle((cx, cy), 30, fill=False, ec="#3a2a18", lw=1.0, zorder=60))
    vignette(ax, 0.45, (0.25, 0.17, 0.08))
    note(fig, "#3a2a18", "EB Garamond")
    fig.savefig(out, dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------
# STYLE 2 — Dark Command (modern documentary, glowing borders)
# ---------------------------------------------------------------------------
def glow(ax, g, color, z, widths=(14, 8, 4, 1.6), alphas=(0.06, 0.12, 0.25, 1.0)):
    for w, a in zip(widths, alphas):
        lines(ax, g, color=color, lw=w, alpha=a, zorder=z, solid_joinstyle="round")


def style_dark(stage, out):
    d = data(); R = stage_regions(d, stage)
    fig, ax = new_fig("#0b0f14")
    bg_image(ax, (0.035, 0.05, 0.07), (0.07, 0.09, 0.12), seed=5, strength=0.8)
    fill(ax, d["land"], fc="#1a1f26", ec="#2c3540", lw=0.8, zorder=3)
    fief(ax, d, stage, "#ff5a5a")
    rivers(ax, d, "#2f5d78", lw=0.9, alpha=0.8)
    fill(ax, d["lakes"], fc="#0f1820", ec="none", zorder=8)
    col = dict(russia="#4fae7c", prussia="#4c8fe0", austria="#e0b040")
    for k, g in R["old"].items():
        fill(ax, g, fc=col[k], ec="none", alpha=0.12, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g, fc=col[k], ec="none", alpha=0.38, zorder=5)
        glow(ax, g, col[k], 6)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#d23a3a", ec="none", alpha=0.30, zorder=5)
        glow(ax, R["pol"], "#ff5a5a", 7)
    lines(ax, d["plc"], color="#ffffff", lw=1.0, alpha=0.35, ls=(0, (4, 4)), zorder=7)
    for c in CITY_SHOW:
        city(ax, c, "#c9d2dc", size=12, font="Inter", dot=3.5)
    for k, (lon, lat) in LABEL_AT.get(stage, {}).items():
        x, y = pt(lon, lat)
        ax.text(x, y, POWER_NAME[k].upper(), color=col[k], fontsize=15, family="Oswald", ha="center", zorder=30, weight="bold")
        ax.text(x, y - 38, AREAS[stage][k], color="#e6edf3", fontsize=13, family="Inter", ha="center", zorder=30)
    yr, tt, sub = STAGE_TXT[stage]
    fig.text(0.04, 0.905, yr, family="Oswald", fontsize=64, color="#ffffff", weight="bold")
    fig.text(0.04, 0.875, tt, family="Oswald", fontsize=22, color="#ff6b6b")
    fig.text(0.04, 0.845, sub, family="Inter", fontsize=15, color="#aab6c2")
    y0 = 0.16
    for i, (k, c) in enumerate([("pol", "#ff5a5a"), ("russia", col["russia"]), ("prussia", col["prussia"]), ("austria", col["austria"])]):
        fig.patches.append(Rectangle((0.04, y0 - i * 0.032), 0.014, 0.018, transform=fig.transFigure, fc=c, ec="none"))
        fig.text(0.06, y0 - i * 0.032 + 0.002, "Polish–Lithuanian Commonwealth" if k == "pol" else POWER_NAME[k], family="Inter", fontsize=13, color="#d0d8e0")
    vignette(ax, 0.7)
    note(fig, "#7d8b99")
    fig.savefig(out, dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------
# STYLE 3 — Copperplate Engraving (monochrome, hatch patterns per power)
# ---------------------------------------------------------------------------
def style_engraving(stage, out):
    d = data(); R = stage_regions(d, stage)
    ink = "#2a1f14"
    fig, ax = new_fig("#f2ead8")
    bg_image(ax, (0.90, 0.87, 0.79), (0.84, 0.80, 0.70), seed=9, strength=0.9, scales=(1, 4, 20))
    for i, off in enumerate(range(4, 40, 6)):
        lines(ax, d["land"].buffer(off).boundary, color=ink, lw=0.4, alpha=max(0.04, 0.42 - i * 0.07), zorder=2)
    fill(ax, d["land"], fc="#f4eddc", ec=ink, lw=1.2, zorder=3)
    fief(ax, d, stage, ink)
    plt.rcParams["hatch.color"] = ink
    plt.rcParams["hatch.linewidth"] = 0.7
    hat = dict(russia="\\\\\\\\", prussia="||||", austria="....")
    for k, g in R["old"].items():
        fill(ax, g, fc="none", ec=ink, lw=0.6, hatch=hat[k], alpha=0.35, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g, fc="none", ec=ink, lw=1.6, hatch=hat[k], alpha=0.95, zorder=5)
    lines(ax, d["plc"], color=ink, lw=3.0, zorder=7)
    lines(ax, d["plc"], color="#f4eddc", lw=1.2, zorder=7)
    rivers(ax, d, ink, lw=0.8, alpha=0.8)
    for c in CITY_SHOW:
        city(ax, c, ink, size=14, font="EB Garamond", dot=4, halo="#f4eddc", style="italic")
    for k, (lon, lat) in LABEL_AT.get(stage, {}).items():
        x, y = pt(lon, lat)
        ax.text(x, y, POWER_NAME[k], color=ink, fontsize=17, family="EB Garamond", ha="center", zorder=30,
                path_effects=[pe.withStroke(linewidth=5, foreground="#f4eddc")])
    fig.patches.append(FancyBboxPatch((0.33, 0.885), 0.34, 0.09, boxstyle="round,pad=0.006", transform=fig.transFigure,
                                      fc="#f4eddc", ec=ink, lw=1.4, zorder=90))
    fig.text(0.5, 0.935, "Tabula Divisionis Poloniae", zorder=100, family="UnifrakturMaguntia", fontsize=36, color=ink, ha="center")
    fig.text(0.5, 0.905, "The First Partition, MDCCLXXII", zorder=100, family="EB Garamond", fontsize=18, style="italic", color=ink, ha="center")
    # double neat-line border
    for inset, lw in [(0.012, 2.4), (0.02, 0.8)]:
        fig.patches.append(Rectangle((inset, inset * 16 / 9), 1 - 2 * inset, 1 - 2 * inset * 16 / 9, transform=fig.transFigure, fill=False, ec=ink, lw=lw))
    # legend
    lx, ly = 0.045, 0.2
    for i, k in enumerate(["russia", "prussia", "austria"]):
        fig.patches.append(Rectangle((lx, ly - i * 0.045), 0.03, 0.03, transform=fig.transFigure, fill=False, ec=ink, hatch=hat[k], lw=1))
        fig.text(lx + 0.04, ly - i * 0.045 + 0.008, "To the " + POWER_NAME[k], family="EB Garamond", fontsize=15, color=ink)
    note(fig, ink, "EB Garamond")
    fig.savefig(out, dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------
# STYLE 4 — Spotlight (Commonwealth lit, everything else in shadow)
# ---------------------------------------------------------------------------
def style_spotlight(stage, out):
    d = data(); R = stage_regions(d, stage)
    fig, ax = new_fig("#08080a")
    fill(ax, d["land"], fc="#15151a", ec="#25252c", lw=0.6, zorder=3)
    fief(ax, d, stage, "#9b1c1c")
    col = dict(russia="#5d7a64", prussia="#5a6f8c", austria="#9c8250")
    # soft light pool centred on what remains
    lit = R["pol"] if R["pol"] is not None else d["plc"]
    litb = lit.simplify(5)
    for w in range(300, 0, -12):
        fill(ax, litb.buffer(w), fc="#d8b98a", ec="none", alpha=0.016, zorder=4)
    for k, g in R["old"].items():
        fill(ax, g, fc=col[k], ec="none", alpha=0.25, zorder=5)
    for k, g in R["new"].items():
        fill(ax, g, fc=col[k], ec="#0a0a0c", lw=0.8, alpha=0.85, zorder=5)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#efe2c8", ec="none", zorder=6)
        fill(ax, R["pol"], fc="none", ec="#9b1c1c", lw=3.0, zorder=7)
    rivers(ax, d, "#7f8fa0", lw=0.8, alpha=0.35, z=9)
    for c in ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Poznań"]:
        x, y = pt(*geom.CITIES[c])
        inside = R["pol"] is not None and R["pol"].contains(Point(x, y))
        city(ax, c, "#3a2a1c" if inside else "#b8b0a0", size=14, font="Cormorant Garamond", dot=4, weight="bold")
    for k, (lon, lat) in LABEL_AT.get(stage, {}).items():
        x, y = pt(lon, lat)
        ax.text(x, y, POWER_NAME[k], color="#ece4d4", fontsize=17, family="Cormorant Garamond", ha="center", zorder=30, weight="bold",
                path_effects=[pe.withStroke(linewidth=4, foreground="#0a0a0c")])
    fig.text(0.5, 0.92, "WHAT REMAINED", family="Cinzel", fontsize=34, color="#efe2c8", ha="center")
    fig.text(0.5, 0.885, "The Commonwealth after the First Partition, 1772", family="Cormorant Garamond", fontsize=20, color="#b9a98c", ha="center", style="italic")
    vignette(ax, 0.85)
    note(fig, "#77706a", "Cormorant Garamond")
    fig.savefig(out, dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------
# STYLE 5 — Clean Infographic (light, flat, data-forward)
# ---------------------------------------------------------------------------
def style_flat(stage, out):
    d = data(); R = stage_regions(d, stage)
    fig, ax = new_fig("#e8edf1")
    fill(ax, d["land"], fc="#f7f7f5", ec="#c9d0d6", lw=0.8, zorder=3)
    fief(ax, d, stage, "#d64545")
    col = dict(russia="#3f9e72", prussia="#3b6fb6", austria="#e3a72f")
    for k, g in R["old"].items():
        fill(ax, g, fc=col[k], ec="white", lw=1, alpha=0.3, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g, fc=col[k], ec="white", lw=1.5, zorder=5)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#d64545", ec="white", lw=1.5, zorder=5)
    fill(ax, d["lakes"], fc="#e8edf1", ec="none", zorder=8)
    rivers(ax, d, "#a9c1d6", lw=0.9, alpha=0.9)
    for c in ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Kyiv", "Berlin", "Vienna", "Königsberg", "Riga"]:
        city(ax, c, "#1f2933", size=12, font="Inter", dot=3.5, halo="white")
    # side panel with numbers
    fig.patches.append(Rectangle((0.0, 0.0), 0.27, 1.0, transform=fig.transFigure, fc="#ffffff", ec="none", zorder=80, alpha=0.96))
    fig.text(0.03, 0.88, "1772", family="Inter", fontsize=60, weight="bold", color="#1f2933", zorder=90)
    fig.text(0.03, 0.845, "First Partition", family="Inter", fontsize=22, color="#52606d", zorder=90)
    rows = [("russia", "Russia", "≈92,000 km²", "≈1.3 million people"),
            ("prussia", "Prussia", "≈36,000 km²", "≈580,000 people"),
            ("austria", "Austria", "≈83,000 km²", "≈2.65 million people")]
    for i, (k, n, a, p) in enumerate(rows):
        y = 0.7 - i * 0.14
        fig.patches.append(Rectangle((0.03, y - 0.005), 0.008, 0.075, transform=fig.transFigure, fc=col[k], ec="none", zorder=90))
        fig.text(0.05, y + 0.045, n, family="Inter", fontsize=20, weight="bold", color="#1f2933", zorder=90)
        fig.text(0.05, y + 0.015, a, family="Inter", fontsize=17, color="#323f4b", zorder=90)
        fig.text(0.05, y - 0.012, p, family="Inter", fontsize=13, color="#7b8794", zorder=90)
    fig.text(0.03, 0.22, "≈30%", family="Inter", fontsize=48, weight="bold", color="#d64545", zorder=90)
    fig.text(0.03, 0.18, "of the Commonwealth's territory lost", family="Inter", fontsize=14, color="#52606d", zorder=90)
    fig.text(0.03, 0.04, "Figures: commonly cited estimates, rounded.", family="Inter", fontsize=10, color="#9aa5b1", zorder=90)
    note(fig, "#7b8794")
    fig.savefig(out, dpi=100); plt.close(fig)


# ---------------------------------------------------------------------------
# STYLE 6 — Cinematic 3D Table (tilted relief map, depth of field)
# ---------------------------------------------------------------------------
def style_3d(stage, out, tmp="/tmp/_flat3d.png"):
    from PIL import Image, ImageFilter, ImageDraw, ImageFont
    d = data(); R = stage_regions(d, stage)
    fig, ax = new_fig("#1c2a33")
    bg_image(ax, (0.10, 0.16, 0.20), (0.16, 0.24, 0.29), seed=11)
    # pseudo-relief: shade land with noise to read as terrain
    fill(ax, d["land"].buffer(4), fc="#0e1418", ec="none", alpha=0.6, zorder=2)
    fill(ax, d["land"], fc="#b9b196", ec="#5a5440", lw=0.8, zorder=3)
    fief(ax, d, stage, "#c94a4a")
    col = dict(russia="#6f9a72", prussia="#5f86b5", austria="#d4a64e")
    for k, g in R["old"].items():
        fill(ax, g, fc=col[k], ec="none", alpha=0.45, zorder=4)
    for k, g in R["new"].items():
        fill(ax, g.buffer(-3), fc="#000000", ec="none", alpha=0.35, zorder=4)
        fill(ax, g, fc=col[k], ec="#2a2a2a", lw=1.2, alpha=0.92, zorder=5)
    if R["pol"] is not None:
        fill(ax, R["pol"], fc="#c94a4a", ec="#5a1515", lw=1.5, zorder=6)
    rivers(ax, d, "#3d6f8f", lw=1.2, alpha=0.9)
    for c in ["Warsaw", "Kraków", "Vilnius", "Gdańsk", "Lwów", "Minsk", "Kyiv", "Berlin", "Vienna", "Riga"]:
        city(ax, c, "#ffffff", size=15, font="Oswald", dot=5, halo="#1b1b1b")
    for k, (lon, lat) in LABEL_AT.get(stage, {}).items():
        x, y = pt(lon, lat)
        ax.text(x, y, POWER_NAME[k].upper(), color="#ffffff", fontsize=19, family="Oswald", ha="center", zorder=30, weight="bold",
                path_effects=[pe.withStroke(linewidth=4, foreground="#111")])
    fig.savefig(tmp, dpi=100); plt.close(fig)
    flat = Image.open(tmp).convert("RGB")
    W, H = flat.size
    # texture overlay
    n = (noise(H // 2, W // 2, (1, 3, 12), 21) * 255).astype(np.uint8)
    tex = Image.fromarray(n).resize((W, H)).convert("RGB")
    flat = Image.blend(flat, tex, 0.08)
    # perspective: map top edge shrinks -> tilted table
    big = flat.resize((int(W * 1.35), int(H * 1.35)), Image.LANCZOS)
    bw, bh = big.size
    def coeffs(pa, pb):
        A = []
        for (x, y), (u, v) in zip(pa, pb):
            A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        A = np.array(A, float); B = np.array(pb, float).reshape(8)
        return np.linalg.solve(A, B).tolist()
    dst = [(W * 0.18, H * 0.02), (W * 0.82, H * 0.02), (W * 1.10, H * 1.05), (-W * 0.10, H * 1.05)]
    src = [(0, 0), (bw, 0), (bw, bh), (0, bh)]
    tilted = big.transform((W, H), Image.PERSPECTIVE, coeffs(dst, src), Image.BICUBIC)
    # depth of field: blur top, keep bottom sharp
    blur = tilted.filter(ImageFilter.GaussianBlur(5))
    mask = Image.fromarray((np.clip(1 - np.linspace(0, 1, H) * 2.2, 0, 1)[:, None] * 255 * np.ones((1, W))).astype(np.uint8))
    img = Image.composite(blur, tilted, mask)
    # haze + vignette + warm key light
    y, x = np.mgrid[0:H, 0:W]
    haze = np.clip(1 - y / (H * 0.55), 0, 1)[..., None] * np.array([150, 170, 185]) * 0.45
    vig = np.clip((np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H * 0.6) / (H * 0.7)) ** 2) - 0.5) / 0.8, 0, 1)[..., None]
    arr = np.asarray(img).astype(float)
    arr = arr * (1 - 0.45 * np.clip(1 - y / (H * 0.55), 0, 1)[..., None]) + haze
    arr = arr * (1 - 0.75 * vig)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(os.path.join(FONTS, "Oswald.ttf"), 76); f1.set_variation_by_name("Bold")
    f2 = ImageFont.truetype(os.path.join(FONTS, "Inter.ttf"), 26)
    dr.text((80, 70), "1772", font=f1, fill=(255, 255, 255))
    dr.text((84, 170), "THE FIRST PARTITION", font=f2, fill=(255, 205, 160))
    f3 = ImageFont.truetype(os.path.join(FONTS, "Inter.ttf"), 15)
    dr.text((W - 20, H - 20), "Borders approximate · reconstructed from treaty lines and rivers", font=f3, fill=(170, 180, 190), anchor="rb")
    img.save(out)


STYLES = {
    "M1_cartographers_atlas": style_atlas,
    "M2_dark_command": style_dark,
    "M3_copperplate_engraving": style_engraving,
    "M4_spotlight": style_spotlight,
    "M5_clean_infographic": style_flat,
    "M6_cinematic_3d_table": style_3d,
}

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "output", "design_options", "maps")
    stage = sys.argv[2] if len(sys.argv) > 2 else "1772"
    only = sys.argv[3:] or list(STYLES)
    os.makedirs(outdir, exist_ok=True)
    for name in only:
        STYLES[name](stage, os.path.join(outdir, f"{name}_{stage}.png"))
        print("wrote", name)
