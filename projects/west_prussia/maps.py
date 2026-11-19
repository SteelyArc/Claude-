"""Map scenes for 'West Prussia – A Region Shaped by History'.

Each scene is draw(canvas, t, frame) with t in [0,1] = scene progress; t=1 is the final state used for
Phase 2 previews. Geometry comes from territories.T() (OHM, CC0) and base.atlas(year) (Natural Earth + OHM delta).
Set env DEBUG_SAFE=1 to overlay the TikTok safe zones.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from functools import lru_cache
from shapely.geometry import LineString, box
from shapely.ops import unary_union
from engine.geo import project, project_pt, ne_clip
from engine.render import (Camera, lerp_cam, ease, seg, shared_border, city, region_label, water_label,
                           title_block, legend, caption, finish, PALETTE, STYLE, draw_text, font, W, H, hexc,
                           Layout, place_city, reserve_region, debug_safe, graticule_geoms, draw_graticule)
from projects.west_prussia.territories import T
from projects.west_prussia.base import atlas
import skia

DEBUG = os.environ.get("DEBUG_SAFE") == "1"

@lru_cache(None)
def G(name, clip=None):
    """Projected territory geometry (optionally clipped to a lon/lat box to speed up huge polygons)."""
    g = T(name)
    if clip:
        g = g.intersection(box(*clip))
    return project(g.buffer(0))

@lru_cache(None)
def NE_COUNTRY(a3, clip=(2, 42, 34, 60)):
    return project(unary_union([g for g, p in ne_clip("ne_10m_admin_0_countries", clip, lambda p: p.get("ADM0_A3") == a3)]))

@lru_cache(None)
def GRAT():
    return graticule_geoms(project_pt, (0, 40), (40, 64), 1.0)

def P(lon, lat):
    return project_pt(lon, lat)

def cam_at(lon, lat, span_km, rot=0.0):
    x, y = P(lon, lat)
    return Camera(x, y, span_km * 1000, rot)

CITY = {
    "Danzig": (18.6466, 54.3520), "Thorn": (18.6050, 53.0100), "Elbing": (19.4044, 54.1561),
    "Marienwerder": (18.9286, 53.7286), "Marienburg": (19.0280, 54.0359), "Culm": (18.4300, 53.3486),
    "Graudenz": (18.7536, 53.4837), "Gdynia": (18.5305, 54.5189), "Königsberg": (20.5108, 54.7104),
    "Stuhm": (19.0244, 53.9089), "Rosenberg": (19.3350, 53.7180), "Frauenburg": (19.6830, 54.3570),
    "Bromberg": (18.0084, 53.1235), "Konitz": (17.5667, 53.6974), "Warsaw": (21.0122, 52.2297),
    "Berlin": (13.405, 52.52), "Vienna": (16.3738, 48.2082), "Stettin": (14.5528, 53.4285),
    "Lemberg": (24.03, 49.84), "Vilnius": (25.2797, 54.6872), "Kraków": (19.945, 50.0647),
    "Riga": (24.1052, 56.9496), "Posen": (16.9252, 52.4064), "Breslau": (17.0385, 51.1079),
    "Deutsch Krone": (16.4644, 53.2731),
}
def C(n):
    return P(*CITY[n])

def start(canvas, a, cam, grat=1.0):
    a.base(canvas, cam)
    draw_graticule(a, canvas, cam, GRAT(), grat)

def end(canvas, frame):
    finish(canvas, frame)
    if DEBUG:
        debug_safe(canvas)

def regions(canvas, cam, L, items):
    """items: (lon, lat, lines, alpha, size, kw) – reserved in the layout, then drawn."""
    for lon, lat, lines, al, size, kw in items:
        reserve_region(L, cam, P(lon, lat), lines, size, kw.get("tracking", 0.12), kw.get("kind", "caps"))
    for lon, lat, lines, al, size, kw in items:
        if kw.get("water"):
            water_label(canvas, cam, P(lon, lat), lines, al, size, kw.get("tracking", 0.28))
        else:
            region_label(canvas, cam, P(lon, lat), lines, al, size, kw.get("color"), kw.get("tracking", 0.12),
                         kw.get("kind", "caps"))

# ----------------------------------------------------------------------------- 1466
def map_1466(canvas, t=1.0, frame=0):
    a = atlas(1466)
    cam = lerp_cam(cam_at(19.1, 54.1, 470), cam_at(19.05, 53.95, 390), ease(seg(t, 0, 1), "sine"))
    start(canvas, a, cam)
    rp = G("royal_prussia_1466"); order = G("order_1466"); warm = G("warmia")
    rp_core = rp.difference(warm.buffer(200))
    a.fill(canvas, cam, "order1466", order, PALETTE["order"], ease(seg(t, 0.0, 0.25)))
    a.fill(canvas, cam, "rp1466", rp_core, PALETTE["poland"], ease(seg(t, 0.35, 0.6)),
           reveal=((C("Thorn")), ease(seg(t, 0.35, 0.65), "out")))
    a.fill(canvas, cam, "warm", warm, PALETTE["warmia"], ease(seg(t, 0.45, 0.7)),
           hatch={"step": 15, "w": 1.6, "alpha": 0.35, "color": "#9A5A48"})
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "o1466", order.boundary, 1.0, ease(seg(t, 0, 0.2)), 1.6, STYLE["ink_soft"])
    a.border(canvas, cam, "rp-order", shared_border(rp, order), ease(seg(t, 0.25, 0.6), "inout"), 1.0, 3.6, nib=True)
    a.border(canvas, cam, "rpo", rp.boundary, 1.0, ease(seg(t, 0.55, 0.75)), 2.0)
    k = ease(seg(t, 0.6, 0.85)); L = Layout("1466")
    regions(canvas, cam, L, [
        (17.75, 53.92, ["ROYAL", "PRUSSIA"], k, 40, {}),
        (17.75, 53.66, ["(Polish Crown)"], k, 28, {"kind": "serif_italic", "tracking": 0.02}),
        (20.55, 53.68, ["TEUTONIC", "ORDER"], ease(seg(t, 0.1, 0.3)), 40, {}),
        (20.55, 53.43, ["(fief of the Polish Crown)"], k, 28, {"kind": "serif_italic", "tracking": 0.02}),
        (20.28, 54.08, ["Warmia"], k, 30, {"kind": "serif_italic", "tracking": 0.05}),
        (17.15, 54.42, ["DUCHY OF", "POMERANIA"], 0.7, 26, {}),
        (19.05, 52.75, ["KINGDOM OF POLAND"], 0.75, 30, {}),
        (18.2, 55.0, ["BALTIC SEA"], 1.0, 44, {"water": True}),
    ])
    kc = ease(seg(t, 0.2, 0.4))
    for n, side in [("Danzig", "left"), ("Elbing", "right"), ("Marienburg", "left"), ("Thorn", "left"),
                    ("Marienwerder", "right"), ("Königsberg", "left"), ("Culm", "left")]:
        place_city(canvas, cam, L, C(n), n, kc, 34, side)
    title_block(canvas, "1466", "SECOND PEACE OF THORN", ease(seg(t, 0.0, 0.2)), sub="19 October 1466")
    legend(canvas, [(PALETTE["poland"], "Royal Prussia", False), (PALETTE["order"], "Teutonic Order", False),
                    (PALETTE["warmia"], "Bishopric of Warmia", "#9A5A48")], ease(seg(t, 0.7, 0.9)), cols=2)
    caption(canvas, ["Marienwerder remained with the Order"], ease(seg(t, 0.75, 0.95)), y=1530)
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1772
CL = (2, 40, 40, 63)
def map_1772(canvas, t=1.0, frame=0):
    a = atlas(1772)
    cam = cam_at(23.3, 52.2, 1450)
    start(canvas, a, cam)
    a.fill(canvas, cam, "prussia1744", G("prussia_1744", CL), PALETTE["prussia"], 0.5, band=False)
    a.fill(canvas, cam, "russia1743", G("russia_1743", (2, 40, 40, 59.9)), PALETTE["russia"], 0.45, band=False)
    a.fill(canvas, cam, "plc1773", G("plc_1773", CL), PALETTE["poland"], 0.9)
    shares = [("prus", "prussian_share_1772", "#93A8BF", 0.15),
              ("rus", "russian_share_1772", PALETTE["russia"], 0.4),
              ("aus", "austrian_share_1772", PALETTE["austria"], 0.65)]
    for key, name, col, t0 in shares:
        a.fill(canvas, cam, key, G(name, CL), col, ease(seg(t, t0, t0 + 0.2)))
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "plc1686b", G("plc_1686", CL).boundary, 1.0, 1.0, 2.2, STYLE["ink_soft"], dash=(9, 6))
    a.border(canvas, cam, "plc1773b", G("plc_1773", CL).boundary, ease(seg(t, 0.1, 0.8)), 1.0, 2.6)
    L = Layout("1772")
    regions(canvas, cam, L, [
        (24.6, 53.0, ["POLAND-", "LITHUANIA"], 1.0, 38, {}),
        (31.2, 54.6, ["RUSSIAN", "EMPIRE"], 0.85, 26, {}),
        (24.3, 49.35, ["to AUSTRIA"], ease(seg(t, 0.75, 0.9)), 28, {}),
        (16.6, 53.55, ["KINGDOM OF", "PRUSSIA"], 0.85, 26, {}),
        (19.6, 48.45, ["HABSBURG", "MONARCHY"], 0.7, 24, {}),
        (18.6, 56.3, ["BALTIC SEA"], 1.0, 40, {"water": True}),
    ])
    place_city(canvas, cam, L, C("Warsaw"), "Warsaw", 1.0, 32, "right", capital=True)
    place_city(canvas, cam, L, C("Danzig"), "Danzig", 1.0, 32, "left", ring=(17, True))
    place_city(canvas, cam, L, C("Thorn"), "Thorn", 1.0, 32, "left", ring=(17, True))
    place_city(canvas, cam, L, C("Königsberg"), "Königsberg", 1.0, 30, "right")
    place_city(canvas, cam, L, C("Vilnius"), "Vilnius", 1.0, 30, "right")
    place_city(canvas, cam, L, P(28.78, 55.49), "Polotsk", 1.0, 28, "right")
    place_city(canvas, cam, L, C("Lemberg"), "Lemberg", 1.0, 30, "left")
    title_block(canvas, "1772", "FIRST PARTITION OF POLAND", 1.0, sub="by Prussia, Russia and Austria")
    legend(canvas, [("#93A8BF", "Annexed by Prussia", False), (PALETTE["russia"], "Annexed by Russia", False),
                    (PALETTE["austria"], "Annexed by Austria", False), (PALETTE["poland"], "Remaining Poland-Lithuania", False)],
           ease(seg(t, 0.85, 1)), cols=2)
    caption(canvas, ["Ringed: Danzig and Thorn remained Polish"], 1.0, y=1530)
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1773 / 1793 (regional)
RC = (10, 49.0, 28, 58)
REG_CAM = (18.55, 53.7, 395)

def map_1773(canvas, t=1.0, frame=0):
    a = atlas(1773)
    cam = cam_at(*REG_CAM)
    start(canvas, a, cam)
    wp = G("west_prussia_1773"); ep = G("east_prussia_1773", RC); netze = G("netze_1773")
    pl = G("plc_1773", RC); pom = G("prussia_1744", RC)
    a.fill(canvas, cam, "pl73", pl, PALETTE["poland"], 0.85)
    a.fill(canvas, cam, "pom44", pom.difference(ep.buffer(100)).difference(wp.buffer(50)).difference(netze.buffer(50)),
           PALETTE["prussia"], 0.45, band=False)
    a.fill(canvas, cam, "ep73", ep.difference(wp.buffer(50)), PALETTE["prussia"], 0.55, band=False)
    a.fill(canvas, cam, "netze", netze.difference(wp.buffer(50)), PALETTE["prussia"], 0.55, band=False,
           hatch={"step": 14, "w": 1.5, "alpha": 0.35, "color": "#4E5E70"})
    a.fill(canvas, cam, "wp73", wp, "#93A8BF", ease(seg(t, 0.2, 0.6)),
           reveal=(C("Marienwerder"), ease(seg(t, 0.2, 0.65), "out")))
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "ep73b", ep.boundary, 1.0, 0.8, 1.8, STYLE["ink_soft"])
    a.border(canvas, cam, "netb", netze.boundary, 1.0, 0.8, 1.8, STYLE["ink_soft"], dash=(8, 6))
    a.border(canvas, cam, "wp73b", wp.boundary, ease(seg(t, 0.1, 0.7)), 1.0, 3.2, nib=True)
    L = Layout("1773")
    regions(canvas, cam, L, [
        (17.75, 54.05, ["WEST", "PRUSSIA"], ease(seg(t, 0.55, 0.75)), 44, {}),
        (20.35, 54.0, ["EAST", "PRUSSIA"], 0.85, 34, {}),
        (17.25, 53.02, ["Netze District"], 0.85, 30, {"kind": "serif_italic", "tracking": 0.03}),
        (19.6, 52.85, ["POLAND-LITHUANIA"], 0.85, 30, {}),
        (16.6, 54.32, ["POMERANIA"], 0.7, 26, {}),
        (17.6, 54.9, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    place_city(canvas, cam, L, C("Danzig"), "Danzig", 1.0, 34, "left", ring=(18, True), sub="remained Polish")
    place_city(canvas, cam, L, C("Thorn"), "Thorn", 1.0, 34, "left", ring=(18, True), sub="remained Polish")
    for n, side in [("Elbing", "right"), ("Marienwerder", "right"), ("Marienburg", "left"), ("Königsberg", "left"),
                    ("Bromberg", "left")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 32, side)
    title_block(canvas, "1773", "PROVINCE OF WEST PRUSSIA", 1.0, sub="formed from the land annexed in 1772")
    legend(canvas, [("#93A8BF", "West Prussia (1773)", False), (PALETTE["poland"], "Poland-Lithuania", False),
                    ("#D3DAE2", "Other Prussian lands", False), ("#D3DAE2", "Netze District", "#4E5E70")], 1.0)
    end(canvas, frame)

def map_1793(canvas, t=1.0, frame=0):
    a = atlas(1793)
    cam = cam_at(*REG_CAM)
    start(canvas, a, cam)
    wp93 = G("west_prussia_1793"); wp73 = G("west_prussia_1773"); pr93 = G("prussia_1793", RC)
    pl93 = G("plc_1793", RC)
    gain = wp93.difference(wp73.buffer(1500)).buffer(-800).buffer(800)
    a.fill(canvas, cam, "pl93", pl93, PALETTE["poland"], 0.85)
    a.fill(canvas, cam, "pr93", pr93.difference(wp93.buffer(100)), PALETTE["prussia"], 0.5, band=False)
    a.fill(canvas, cam, "wp93", wp93.difference(gain), "#93A8BF", 1.0)
    a.fill(canvas, cam, "gain93", gain, "#6F89A6", ease(seg(t, 0.3, 0.7)),
           reveal=(C("Danzig"), ease(seg(t, 0.3, 0.75), "out")))
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "wp93b", wp93.boundary, 1.0, 1.0, 3.0)
    a.border(canvas, cam, "gainb", gain.boundary, ease(seg(t, 0.3, 0.75)), 1.0, 3.4, "#8A3B2E", nib=True)
    L = Layout("1793")
    regions(canvas, cam, L, [
        (17.75, 54.05, ["WEST", "PRUSSIA"], 1.0, 44, {}),
        (20.35, 54.0, ["EAST", "PRUSSIA"], 0.85, 34, {}),
        (17.4, 52.72, ["SOUTH PRUSSIA"], 0.8, 28, {}),
        (16.6, 54.32, ["POMERANIA"], 0.7, 26, {}),
        (20.2, 52.85, ["POLAND"], 0.85, 32, {}),
        (17.6, 54.9, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    place_city(canvas, cam, L, C("Danzig"), "Danzig", 1.0, 36, "left", capital=True, sub="incorporated 1793")
    place_city(canvas, cam, L, C("Thorn"), "Thorn", 1.0, 36, "left", capital=True, sub="incorporated 1793")
    for n, side in [("Elbing", "right"), ("Marienwerder", "right"), ("Königsberg", "left")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 32, side)
    title_block(canvas, "1793", ["DANZIG AND THORN", "INCORPORATED"], 1.0, sub="Second Partition of Poland")
    legend(canvas, [("#93A8BF", "West Prussia", False), ("#6F89A6", "Added in 1793", False),
                    ("#D3DAE2", "Other Prussian lands", False), (PALETTE["poland"], "Poland (1793)", False)], 1.0)
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1919/1920
VC = (10, 49.0, 28, 58)
def map_1919(canvas, t=1.0, frame=0):
    a = atlas(1920)
    cam = cam_at(*REG_CAM)
    start(canvas, a, cam)
    de = G("reich_1920_12", VC); pl = G("poland_1924", VC); fc = G("free_city"); pleb = G("plebiscite_area_marienwerder")
    wp = G("west_prussia_1909")
    a.fill(canvas, cam, "de20", de.difference(pleb.buffer(100)), PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "pl20", pl, PALETTE["poland"], ease(seg(t, 0.2, 0.5)),
           reveal=(C("Thorn"), ease(seg(t, 0.2, 0.55), "out")))
    a.fill(canvas, cam, "fc20", fc, PALETTE["freecity"], ease(seg(t, 0.5, 0.7)))
    a.fill(canvas, cam, "pleb20", pleb, PALETTE["plebiscite"], ease(seg(t, 0.65, 0.85)),
           hatch={"step": 13, "w": 1.8, "alpha": 0.5, "color": "#8C6A2C"})
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "wp09", wp.boundary, 1.0, 0.9, 2.4, "#6B4A2E", dash=(12, 8), halo=False)
    a.border(canvas, cam, "pl-de", pl.boundary.intersection(cam.view_box(1.6)), ease(seg(t, 0.15, 0.5)), 1.0, 3.2, nib=True)
    a.border(canvas, cam, "fcb", fc.boundary, ease(seg(t, 0.5, 0.65)), 1.0, 3.0)
    a.border(canvas, cam, "plebb", pleb.boundary, 1.0, ease(seg(t, 0.65, 0.8)), 2.2, "#8C6A2C")
    L = Layout("1919")
    regions(canvas, cam, L, [
        (18.05, 53.62, ["POLISH", "CORRIDOR"], ease(seg(t, 0.4, 0.6)), 38, {}),
        (16.6, 54.2, ["GERMANY"], 0.9, 34, {}),
        (20.4, 54.05, ["EAST", "PRUSSIA"], 0.9, 32, {}),
        (19.6, 52.82, ["POLAND"], 0.9, 34, {}),
        (19.05, 54.72, ["FREE CITY", "OF DANZIG"], ease(seg(t, 0.55, 0.75)), 28, {}),
        (17.55, 54.9, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    for n, side in [("Danzig", "left"), ("Thorn", "left"), ("Elbing", "right"), ("Marienwerder", "right"),
                    ("Bromberg", "left"), ("Gdynia", "left")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 32, side)
    title_block(canvas, "1919", "TREATY OF VERSAILLES", 1.0, sub="signed 28 June 1919 · in force 10 January 1920")
    legend(canvas, [(PALETTE["germany"], "Germany", False), (PALETTE["poland"], "Poland", False),
                    (PALETTE["freecity"], "Free City of Danzig", False), (PALETTE["plebiscite"], "Plebiscite area", "#8C6A2C")], 1.0)
    caption(canvas, ["Dashed: Province of West Prussia before 1919"], 1.0, y=1530)
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1920 plebiscite
KREISE = [("kreis_marienwerder_1818", "Marienwerder"), ("kreis_stuhm_1818", "Stuhm"),
          ("kreis_rosenberg_1818", "Rosenberg"), ("kreis_marienburg_1818", "Marienburg")]
def map_plebiscite(canvas, t=1.0, frame=0):
    a = atlas(1920)
    cam = cam_at(19.12, 53.84, 178)
    start(canvas, a, cam)
    pleb = G("plebiscite_area_marienwerder"); pl = G("poland_1924", VC); fc = G("free_city")
    de = G("reich_1920_12", VC)
    a.fill(canvas, cam, "pl20", pl, PALETTE["poland"], 0.85)
    a.fill(canvas, cam, "fc20", fc, PALETTE["freecity"], 0.85)
    a.fill(canvas, cam, "de20b", de.difference(pleb.buffer(100)), PALETTE["germany"], 0.7)
    a.fill(canvas, cam, "pleb", pleb, PALETTE["plebiscite"], 1.0,
           hatch={"step": 15, "w": 1.6, "alpha": 0.28, "color": "#8C6A2C"})
    a.water(canvas, cam); a.coast(canvas, cam)
    parts = []
    for k, n in KREISE:
        g = G(k).intersection(pleb.buffer(50))
        parts.append((n, g))
        a.border(canvas, cam, "kb" + k, g.boundary, 1.0, 0.8, 1.7, "#7A5A24", dash=(7, 6), halo=False)
    a.border(canvas, cam, "plebb2", pleb.boundary, ease(seg(t, 0.0, 0.6)), 1.0, 3.6, "#6E4F1E", nib=True)
    a.border(canvas, cam, "pl-b", pl.boundary.intersection(cam.view_box(1.6)), 1.0, 1.0, 2.6)
    a.border(canvas, cam, "fc-b", fc.boundary, 1.0, 1.0, 2.6)
    from engine.geo import _TR
    inv = lambda x, y: _TR.transform(x, y, direction="INVERSE")
    L = Layout("pleb")
    items = []
    for n, g in parts:
        rp = max(getattr(g, "geoms", [g]), key=lambda q: q.area).representative_point()
        lon, lat = inv(rp.x, rp.y)
        manual = {"Marienwerder": (18.97, 53.635), "Rosenberg": (19.45, 53.71)}   # clear of marker/each other
        if n in manual:
            lon, lat = manual[n]
        items.append((lon, lat, [n.upper()], 0.95, 26, {"color": "#5A4218"}))
    items += [(18.42, 53.72, ["POLAND"], 0.9, 34, {}), (19.9, 53.98, ["EAST", "PRUSSIA"], 0.9, 30, {}),
              (18.95, 54.55, ["FREE CITY", "OF DANZIG"], 0.85, 26, {})]
    regions(canvas, cam, L, items)
    city(canvas, cam, C("Marienwerder"), "", 1.0)
    for n, side in [("Graudenz", "left"), ("Elbing", "right"), ("Danzig", "left")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 30, side)
    caption(canvas, ["Dashed: voting districts – Marienwerder (east of the Vistula),", "Stuhm, Rosenberg, Marienburg (east of the Nogat)"],
            1.0, y=1272, size=28)
    title_block(canvas, "11 JULY 1920", "MARIENWERDER PLEBISCITE", 1.0, date_size=118)
    k = ease(seg(t, 0.55, 0.95), "out")
    x0, y0, wbar, hbar = 76, 1400, 780, 44
    bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc(STYLE["halo"], 0.88))
    canvas.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(52, 1338, 836, 212), 14, 14), bg)
    draw_text(canvas, "Valid votes: 104,941", x0, 1380, font("sans", 30), STYLE["ink"], 1.0, 0, "left")
    pde = 96923 / 104941
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(hexc("#8FA2B8")); canvas.drawRect(skia.Rect.MakeXYWH(x0, y0, wbar * pde * k, hbar), p)
    p.setColor4f(hexc("#D29A8B")); canvas.drawRect(skia.Rect.MakeXYWH(x0 + wbar * pde * k, y0, wbar * (1 - pde) * k, hbar), p)
    s = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6); s.setColor4f(hexc(STYLE["ink"], 0.8))
    canvas.drawRect(skia.Rect.MakeXYWH(x0, y0, wbar, hbar), s)
    draw_text(canvas, "East Prussia (Germany)  96,923 · 92.4 %", x0, 1488, font("sans", 30), STYLE["ink"], k, 0, "left")
    draw_text(canvas, "Poland  8,018 · 7.6 %", x0, 1528, font("sans", 30), "#8A3B2E", k, 0, "left")
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1939
def map_1939(canvas, t=1.0, frame=0):
    a = atlas(1939)
    cam = cam_at(18.75, 53.55, 470)
    start(canvas, a, cam)
    de = G("reich_1939_03", VC); pl = G("poland_1938", VC); fc = G("free_city"); rg = G("reichsgau_dwp")
    a.fill(canvas, cam, "de39", de, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "pl39", pl, PALETTE["poland"], 0.85)
    a.fill(canvas, cam, "fc39", fc, PALETTE["freecity"], 0.9)
    a.fill(canvas, cam, "rg39", G("annexed_1939"), "#C9A49A", ease(seg(t, 0.55, 0.85)), band=False,
           hatch={"step": 12, "w": 2.0, "alpha": 0.5, "color": "#5E2A22"})
    a.water(canvas, cam); a.coast(canvas, cam)
    a.border(canvas, cam, "pl38b", pl.boundary.intersection(cam.view_box(1.6)), 1.0, 1.0, 2.6)
    a.border(canvas, cam, "fc39b", fc.boundary, 1.0, 1.0, 2.6)
    a.border(canvas, cam, "rg39b", rg.boundary, ease(seg(t, 0.55, 0.9)), 1.0, 2.6, "#5E2A22", dash=(12, 7))
    arrows = [("a4", [(17.05, 53.78), (17.65, 53.62), (18.3, 53.47)]),
              ("a3w", [(19.45, 53.68), (19.1, 53.56), (18.88, 53.49)]),
              ("a3s", [(20.45, 53.42), (20.45, 53.1), (20.6, 52.78)])]
    for i, (k, pts) in enumerate(arrows):
        a.path_line(canvas, cam, k, LineString([P(*p) for p in pts]), ease(seg(t, 0.1 + i * 0.1, 0.5 + i * 0.1)),
                    "#5E2A22", 6.0, 0.85, dash=None, arrow=True)
    L = Layout("1939")
    regions(canvas, cam, L, [
        (16.95, 54.12, ["GERMAN", "REICH"], 0.9, 32, {}),
        (20.55, 54.12, ["EAST", "PRUSSIA"], 0.9, 32, {}),
        (19.4, 52.6, ["POLAND"], 0.9, 36, {}),
        (17.55, 54.95, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    for n, side in [("Danzig", "right"), ("Gdynia", "left"), ("Thorn", "left"), ("Bromberg", "left"), ("Graudenz", "right")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 30, side)
    title_block(canvas, "SEPTEMBER 1939", "INVASION AND ANNEXATION", 1.0, date_size=104)
    legend(canvas, [(PALETTE["germany"], "German Reich", False), (PALETTE["poland"], "Poland", False),
                    (PALETTE["freecity"], "Free City of Danzig", False), ("#C9A49A", "Annexed 1939", "#5E2A22")], 1.0)
    caption(canvas, ["Dashed: Reichsgau Danzig-West Prussia · arrows schematic", "Annexation not recognised under international law"], 1.0, y=1526, size=26)
    end(canvas, frame)

# ----------------------------------------------------------------------------- 1945
WC = (2, 42, 34, 60)
def map_1945(canvas, t=1.0, frame=0):
    a = atlas(1945)
    cam = cam_at(16.9, 52.9, 860)
    start(canvas, a, cam, 0.8)
    pl = G("poland_1945", WC); old_de = G("reich_1936", WC); fc = G("free_city")
    de_now = NE_COUNTRY("DEU"); su = G("soviet_1945")
    ceded = unary_union([pl.intersection(old_de), fc]).buffer(-500).buffer(500)
    a.fill(canvas, cam, "de45", de_now, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "pl45", pl, PALETTE["poland"], 0.9)
    a.fill(canvas, cam, "ceded", ceded, PALETTE["poland"], ease(seg(t, 0.3, 0.7)), band=False,
           hatch={"step": 13, "w": 1.6, "alpha": 0.45, "color": "#8A3B2E"})
    a.fill(canvas, cam, "su45", su, PALETTE["soviet"], 0.9)
    a.water(canvas, cam); a.coast(canvas, cam)
    on = shared_border(pl, de_now, 3000)
    a.border(canvas, cam, "odern", on, ease(seg(t, 0.1, 0.6)), 1.0, 4.4, "#8A3B2E", nib=True)
    a.border(canvas, cam, "wp-old", G("west_prussia_1909").boundary, 1.0, 0.9, 2.2, "#3A2F24", dash=(10, 7), halo=False)
    L = Layout("1945")
    regions(canvas, cam, L, [
        (19.6, 52.0, ["POLAND"], 0.9, 40, {}),
        (13.1, 51.75, ["GERMANY"], 0.9, 32, {}),
        (13.1, 51.4, ["(Allied occupation)"], 0.9, 26, {"kind": "serif_italic", "tracking": 0.02}),
        (21.55, 55.05, ["SOVIET", "UNION"], 0.9, 26, {}),
        (13.0, 53.75, ["ODER–NEISSE", "LINE"], ease(seg(t, 0.4, 0.7)), 26, {"color": "#8A3B2E"}),
        (17.2, 55.45, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    place_city(canvas, cam, L, C("Danzig"), "Gdańsk", 1.0, 30, "left", sub="(Danzig)")
    place_city(canvas, cam, L, C("Stettin"), "Szczecin", 1.0, 28, "right", sub="(Stettin)")
    place_city(canvas, cam, L, C("Berlin"), "Berlin", 1.0, 30, "left")
    place_city(canvas, cam, L, C("Warsaw"), "Warsaw", 1.0, 30, "right", capital=True)
    place_city(canvas, cam, L, C("Breslau"), "Wrocław", 1.0, 28, "right", sub="(Breslau)")
    title_block(canvas, "1945", "THE END OF GERMAN RULE", 1.0, sub="Potsdam Agreement, 2 August 1945")
    legend(canvas, [(PALETTE["poland"], "Poland", False), (PALETTE["poland"], "Polish administration", "#8A3B2E"),
                    (PALETTE["germany"], "Germany", False), (PALETTE["soviet"], "Soviet Union", False)], 1.0)
    caption(canvas, ["Hatched: pending a final peace settlement (border confirmed 1990)"], 1.0, y=1530, size=27)
    end(canvas, frame)

# ----------------------------------------------------------------------------- today
def map_today(canvas, t=1.0, frame=0):
    a = atlas(2025)
    cam = cam_at(17.2, 52.95, 800)
    start(canvas, a, cam, 0.8)
    pl = G("poland_today", WC); de = NE_COUNTRY("DEU")
    ru = G("soviet_kaliningrad"); lt = G("lithuania_today", WC)
    a.fill(canvas, cam, "plt", pl, PALETTE["poland"], 0.9)
    a.fill(canvas, cam, "det", de, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "rut", ru, PALETTE["soviet"], 0.9)
    a.fill(canvas, cam, "ltt", lt, PALETTE["lithuania"], 0.8)
    wp = G("west_prussia_1909")
    a.fill(canvas, cam, "wpt", wp, "#E6C98C", ease(seg(t, 0.4, 0.8)), band=False,
           hatch={"step": 12, "w": 1.4, "alpha": 0.35, "color": "#6B4A2E"})
    a.water(canvas, cam); a.coast(canvas, cam)
    for k in ("pomorskie_1999", "kujpom_1999", "warmaz_1999", "zachpom_1999"):
        a.border(canvas, cam, "vb" + k, G(k).boundary, 1.0, 0.55, 1.2, STYLE["ink_soft"], dash=(5, 5), halo=False)
    a.border(canvas, cam, "plb", pl.boundary.intersection(cam.view_box(1.6)), 1.0, 1.0, 2.8)
    a.border(canvas, cam, "wptb", wp.boundary, ease(seg(t, 0.2, 0.7)), 1.0, 3.0, "#6B4A2E", dash=(12, 7), nib=True)
    L = Layout("today")
    regions(canvas, cam, L, [
        (19.8, 51.95, ["POLAND"], 0.9, 42, {}),
        (13.4, 51.75, ["GERMANY"], 0.9, 34, {}),
        (21.45, 54.95, ["RUSSIA"], 0.85, 24, {}),
        (17.2, 55.45, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    for n, nm, side in [("Danzig", "Gdańsk", "left"), ("Thorn", "Toruń", "right"), ("Elbing", "Elbląg", "right"),
                        ("Marienwerder", "Kwidzyn", "right"), ("Warsaw", "Warsaw", "right"), ("Berlin", "Berlin", "left")]:
        place_city(canvas, cam, L, C(n), nm, 1.0, 30, side, capital=n in ("Warsaw", "Berlin"))
    title_block(canvas, "TODAY", "WEST PRUSSIA ON TODAY'S MAP", 1.0, date_size=120)
    legend(canvas, [("#E6C98C", "Former West Prussia", "#6B4A2E"), (PALETTE["poland"], "Poland", False),
                    (PALETTE["germany"], "Germany", False), (PALETTE["soviet"], "Russia", False)], 1.0)
    caption(canvas, ["The former province lies entirely within Poland"], 1.0, y=1530)
    end(canvas, frame)

MAPS = {"01_1466": map_1466, "02_1772": map_1772, "03_1773": map_1773, "04_1793": map_1793,
        "05_1919": map_1919, "06_1920_plebiscite": map_plebiscite, "07_1939": map_1939,
        "08_1945": map_1945, "09_today": map_today}
