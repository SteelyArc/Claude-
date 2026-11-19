"""WEST PRUSSIA – A REGION SHAPED BY HISTORY: full film timeline (1080×1920, 30 fps).

Master clock = narration time T (s). Narration 0–325.88 s, end-card tail to T_END.
Shot list (start, end, fn) + transitions; frame_at(i) renders frame i. Word timings: research/narration_transcript.json.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, skia, cv2
from PIL import Image
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from engine.render import (W, H, new_surface, ease, seg, lerp_cam, finish, title_block, caption, legend, PALETTE, STYLE,
                           region_label, water_label, Layout, place_city, city, draw_text, font, fit_font, hexc,
                           draw_graticule, shared_border)
from engine.shots import PhotoShot, DocumentShot, ink_mask, ink_blend
from engine.depth import depth_map
from engine.geo import project, project_pt, ne_clip
from projects.west_prussia import maps as M
from projects.west_prussia.maps import G, P, C, D, cam_at, GRAT, VC, WC, RC, regions, NE_COUNTRY
from projects.west_prussia.base import atlas
from projects.west_prussia import seq_versailles as SV

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FPS = 30
NARR_END = 325.878
T_END = 329.4                 # 3.5 s end-card tail (approved)
IMG = os.path.join(ROOT, "assets/images/loc")

# ------------------------------------------------------------------------------------------- assets
_A = {}
def photo(name, box_w=900, center_y=968):
    key = (name, box_w, center_y)
    if key not in _A:
        Image.MAX_IMAGE_PIXELS = None
        a = np.asarray(Image.open(os.path.join(IMG, name + ".png")).convert("RGB"))
        base = name.replace("_crop", "")
        d = depth_map(a, os.path.join(ROOT, f"cache/depth_{base}.npy"))
        _A[key] = PhotoShot(a, d, box_w=box_w, center_y=center_y)
    return _A[key]

def document(name):
    if name not in _A:
        Image.MAX_IMAGE_PIXELS = None
        _A[name] = DocumentShot(np.asarray(Image.open(os.path.join(IMG, name + ".png")).convert("RGB")))
    return _A[name]

def warm():
    for n in ("marienburg_east_c1895_crop", "danzig_langer_markt_c1895_crop", "danzig_great_bridge_c1895_crop",
              "danzig_marienkirche_c1900_crop", "danzig_krantor_c1895_crop", "gdynia_pilsudski_1935_39_crop"):
        photo(n)
    photo("danzig_kaiser_flags_1920_crop", box_w=760, center_y=960)
    document("treaty1919_p0175")
    SV.assets()

def base_map(canvas, year, cam, grat=1.0):
    a = atlas(year)
    a.base(canvas, cam)
    draw_graticule(a, canvas, cam, GRAT(), grat)
    return a

def castle(canvas, cam, xy, alpha, size=16):
    """Small crenellated keep marker (castle of the Order)."""
    if alpha <= 0.01:
        return
    x, y = cam.px(*xy)
    s = size
    p = skia.Path()
    p.moveTo(x - s, y + s * 0.8); p.lineTo(x - s, y - s * 0.4)
    for i in range(4):
        x0 = x - s + i * s / 2
        p.lineTo(x0, y - s * 0.9); p.lineTo(x0 + s / 4, y - s * 0.9); p.lineTo(x0 + s / 4, y - s * 0.4); p.lineTo(x0 + s / 2, y - s * 0.4)
    p.lineTo(x + s, y + s * 0.8); p.close()
    h = skia.Paint(AntiAlias=True); h.setColor4f(hexc(STYLE["halo"], 0.9 * alpha))
    h.setStyle(skia.Paint.kStroke_Style); h.setStrokeWidth(6); canvas.drawPath(p, h)
    f = skia.Paint(AntiAlias=True); f.setColor4f(hexc("#6B4A2E", alpha)); canvas.drawPath(p, f)

def glow(canvas, cam, xy, radius_px, color, alpha):
    if alpha <= 0.01:
        return
    x, y = cam.px(*xy)
    c = hexc(color)
    g = skia.Paint(AntiAlias=True)
    g.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), radius_px,
                [skia.Color4f(c.fR, c.fG, c.fB, 0.55 * alpha).toColor(), skia.Color4f(c.fR, c.fG, c.fB, 0).toColor()], None))
    g.setBlendMode(skia.BlendMode.kMultiply)
    canvas.drawCircle(x, y, radius_px, g)

def info_box(canvas, lines, alpha, y=1372, colors=None, size=34):
    """Fact panel in the caption zone (auto-fit, safe-zone width)."""
    if alpha <= 0.01:
        return
    n = len(lines)
    bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc(STYLE["halo"], 0.86 * alpha))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(70, y, 860, 34 + n * size * 1.32), 14, 14, bg)
    for i, ln in enumerate(lines):
        col = (colors[i] if colors else STYLE["ink"])
        draw_text(canvas, ln, 500, y + 22 + size * 0.95 + i * size * 1.32, fit_font("sans", size, ln, 800), col, alpha)

def dark_info(canvas, lines, alpha, y=1372, size=34, colors=None):
    if alpha <= 0.01:
        return
    n = len(lines)
    bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc("#1E1813", 0.78 * alpha))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(70, y, 860, 34 + n * size * 1.32), 14, 14, bg)
    for i, ln in enumerate(lines):
        draw_text(canvas, ln, 500, y + 22 + size * 0.95 + i * size * 1.32, fit_font("sans", size, ln, 800),
                  (colors[i] if colors else "#EFE4CF"), alpha)

# ------------------------------------------------------------------------------------------- S1 intro (0–21)
def s_intro(c, T, f):
    k = ease(seg(T, 0.0, 13.5), "sine")
    cam = lerp_cam(cam_at(19.6, 55.2, 1500), cam_at(18.55, 53.78, 430), k)
    a = base_map(c, 1900, cam)
    wp = G("west_prussia_1909")
    a.fill(c, cam, "wp_intro", wp, "#93A8BF", 0.85 * ease(seg(T, 6.0, 10.0)), reveal=(C("Marienwerder"), ease(seg(T, 6.0, 10.5), "out")))
    a.water(c, cam, flow=T * 0.3); a.coast(c, cam)
    a.border(c, cam, "wp_intro_b", wp.boundary, ease(seg(T, 4.0, 10.0), "inout"), 1.0, 3.2, nib=True)
    # ghost borders of other eras (12.6 'competing powers', 14.0 'changing borders')
    for i, (key, geom) in enumerate((("g1466", D("sb_rp_order_p", lambda: shared_border(G("royal_prussia_1466"), G("order_1466")))),
                                     ("g1773", G("west_prussia_1773").boundary), ("g1920", G("poland_1920", VC).boundary),
                                     ("g1945", G("poland_1945", WC).boundary))):
        t0 = 12.4 + i * 1.4
        al = math.sin(math.pi * seg(T, t0, t0 + 3.2)) * 0.75
        if al > 0:
            a.border(c, cam, key, geom, 1.0, al, 2.0, "#8A3B2E", dash=(8, 6), halo=False)
    L = Layout("intro")
    kl = ease(seg(T, 2.3, 3.5))
    regions(c, cam, L, [(18.4, 54.95, ["BALTIC SEA"], kl, 46, {"water": True}),
                        (18.85, 53.32, ["Vistula River"], ease(seg(T, 3.5, 4.8)) * ease(seg(T, 8, 9.5)), 30, {"water": True, "tracking": 0.05}),
                        (17.9, 53.95, ["WEST", "PRUSSIA"], ease(seg(T, 9.0, 10.5)), 42, {})])
    for i, (n, side) in enumerate((("Danzig", "left"), ("Elbing", "right"), ("Marienwerder", "right"), ("Thorn", "left"))):
        place_city(c, cam, L, C(n), n, ease(seg(T, 7.0 + i * 0.6, 7.8 + i * 0.6)), 34, side)
    ka = ease(seg(T, 0.4, 1.8)) * (1 - ease(seg(T, 5.6, 6.8)))
    title_block(c, None, "WEST PRUSSIA", ka, y=300, sub="A Region Shaped by History")
    kb = ease(seg(T, 13.0, 14.0)) * (1 - ease(seg(T, 19.5, 20.6)))
    caption(c, ["Faint red lines: borders of 1466, 1773, 1920 and 1945"], kb, y=1500, size=28)
    finish(c, f)

# ------------------------------------------------------------------------------------------- S2 Teutonic Order (20.4–42)
ORDER_CASTLES = ["Marienburg", "Thorn", "Elbing", "Königsberg", "Marienwerder", "Culm", "Graudenz", "Danzig"]
def s_teutonic(c, T, f):
    cam = lerp_cam(cam_at(19.6, 54.15, 560), cam_at(19.4, 54.05, 470), ease(seg(T, 20.4, 42.0), "sine"))
    a = base_map(c, 1440, cam)
    order = G("order_1435")
    a.fill(c, cam, "ord1435", order, PALETTE["order"], ease(seg(T, 24.0, 28.0)),
           reveal=(C("Marienburg"), ease(seg(T, 24.0, 29.0), "out")))
    a.water(c, cam); a.coast(c, cam)
    a.border(c, cam, "ord1435b", order.boundary, ease(seg(T, 24.5, 29.5), "inout"), 1.0, 2.6, nib=True)
    # trade routes (schematic): Hanseatic sea lane and the Vistula
    routes = [("rt_sea_w", [(14.2, 54.75), (16.0, 55.0), (17.6, 54.95), (18.68, 54.42)]),
              ("rt_sea_e", [(18.75, 54.45), (19.6, 54.75), (20.5, 55.2), (21.2, 56.2), (22.5, 57.2)]),
              ("rt_vist", [(18.6, 53.01), (18.75, 53.45), (18.86, 53.76), (18.8, 54.08), (18.68, 54.33)]),
              ("rt_kbg", [(18.75, 54.4), (19.45, 54.48), (19.9, 54.62), (20.5, 54.71)])]
    for i, (k, pts) in enumerate(routes):
        a.path_line(c, cam, k, D(k, lambda pts=pts: LineString([P(*p) for p in pts])), ease(seg(T, 34.5 + i * 0.5, 37.2 + i * 0.5)),
                    "#7A4E2D", 4.0, 0.85, dash=(12, 9), arrow=True)
    for i, n in enumerate(ORDER_CASTLES):
        castle(c, cam, C(n), ease(seg(T, 29.6 + i * 0.18, 30.2 + i * 0.18)), 15)
    L = Layout("teutonic")
    kp = ease(seg(T, 37.8, 39.0))
    regions(c, cam, L, [(20.6, 53.85, ["STATE OF THE", "TEUTONIC ORDER"], ease(seg(T, 25.0, 26.5)), 34, {}),
                        (20.6, 53.55, ["(c. 1440)"], ease(seg(T, 25.0, 26.5)), 28, {"kind": "serif_italic", "tracking": 0.02}),
                        (19.2, 52.75, ["KINGDOM OF POLAND"], kp, 30, {}),
                        (22.4, 54.35, ["GRAND DUCHY", "OF LITHUANIA"], kp, 24, {}),
                        (17.2, 55.15, ["BALTIC SEA"], 1.0, 42, {"water": True})])
    for n, side in (("Danzig", "left"), ("Marienburg", "left"), ("Königsberg", "left"), ("Thorn", "left")):
        place_city(c, cam, L, C(n), n, ease(seg(T, 30.0, 31.0)), 30, side)
    kt = ease(seg(T, 23.8, 25.0))
    title_block(c, None, "THE TEUTONIC ORDER", kt, y=300, sub="castles, towns and trade on the Baltic")
    caption(c, ["Dashed lines: trade routes (schematic)"], ease(seg(T, 35.0, 36.0)), y=1500, size=28)
    finish(c, f)

def s_marienburg(c, T, f):
    photo("marienburg_east_c1895_crop").draw(c, T - 31.0, 4.4, zoom=(1.0, 1.15), focus=((0.5, 0.5), (0.6, 0.42)),
        par=((-8, 0), (8, -2)), caption=["Marienburg, seat of the Grand Masters of the Teutonic Order"],
        credit="PHOTOCHROM PRINT C. 1890–1900 · LIBRARY OF CONGRESS")
    title_block(c, None, "MARIENBURG CASTLE", ease(seg(T, 31.4, 32.2)), y=300, light=True)
    finish(c, f, paper=False, vignette=0.38, grain_alpha=0.14)

# ------------------------------------------------------------------------------------------- generic wrappers for maps.py scenes
def wrap(fn, t0, t1):
    def g(c, T, f):
        fn(c, seg(T, t0, t1), f)
    g.__name__ = f"{fn.__name__}_{t0}"
    return g

# ------------------------------------------------------------------------------------------- S6 19th century (84.8–103.1)
def s_province(c, T, f):
    cam = lerp_cam(cam_at(18.6, 53.75, 420), cam_at(18.7, 53.9, 330), ease(seg(T, 84.0, 90.0), "sine"))
    a = base_map(c, 1890, cam)
    wp = G("west_prussia_1878"); rbd = G("rb_danzig_1882"); rbm = G("rb_marienwerder_1909")
    a.fill(c, cam, "de78", D("de78", lambda: G("reich_1890", (10, 49, 28, 58)).difference(wp.buffer(100))), PALETTE["prussia"], 0.45, band=False)
    a.fill(c, cam, "wp78", wp, "#93A8BF", 0.9)
    a.fill(c, cam, "ru14", D("ru14c", lambda: G("russia_1914", (10, 49, 30, 58))), PALETTE["russia"], 0.6, band=False)
    a.water(c, cam, flow=T * 0.35); a.coast(c, cam)
    a.border(c, cam, "rbb", D("rb_shared", lambda: shared_border(rbd, rbm, 800)), ease(seg(T, 85.0, 87.5)), 0.8, 1.8,
             STYLE["ink_soft"], dash=(8, 6), halo=False)
    a.border(c, cam, "wp78b", wp.boundary, 1.0, 1.0, 3.0)
    L = Layout("province")
    regions(c, cam, L, [(18.1, 54.25, ["District", "Danzig"], 0.9, 26, {"kind": "serif_italic", "tracking": 0.02}),
                        (18.25, 53.45, ["District", "Marienwerder"], 0.9, 26, {"kind": "serif_italic", "tracking": 0.02}),
                        (20.35, 54.05, ["EAST", "PRUSSIA"], 0.85, 30, {}),
                        (19.8, 52.9, ["RUSSIAN EMPIRE"], 0.8, 26, {}),
                        (17.4, 54.95, ["BALTIC SEA"], 1.0, 42, {"water": True})])
    for n, side in (("Danzig", "left"), ("Elbing", "right"), ("Marienwerder", "right"), ("Thorn", "left"), ("Graudenz", "left")):
        place_city(c, cam, L, C(n), n, 1.0, 32, side, capital=n == "Danzig")
    title_block(c, None, ["WEST PRUSSIA UNDER", "PRUSSIAN RULE"], ease(seg(T, 84.6, 85.6)), y=280,
                sub="Province of West Prussia, borders 1878–1919")
    finish(c, f)

def mk_photo(name, t0, dur, cap, credit, zoom=(1.0, 1.14), focus=((0.5, 0.5), (0.5, 0.45)), par=((-8, 0), (8, -2)),
             title=None, desat=None, box_w=900, center_y=968):
    def g(c, T, f):
        photo(name, box_w, center_y).draw(c, T - t0, dur, zoom=zoom, focus=focus, par=par, caption=cap, credit=credit)
        if title:
            title_block(c, None, title, ease(seg(T, t0 + 0.4, t0 + 1.2)), y=300, light=True)
        finish(c, f, paper=False, vignette=0.38, grain_alpha=0.14)
    g.__name__ = "photo_" + name + str(t0)
    g.desat = desat
    return g

# ------------------------------------------------------------------------------------------- S7a 1918 (103.1–118.4)
def s_1918(c, T, f):
    cam = lerp_cam(cam_at(19.3, 52.9, 900), cam_at(19.0, 52.7, 760), ease(seg(T, 103.0, 118.4), "sine"))
    a = base_map(c, 1914, cam, 0.8)
    de = G("reich_1890", (2, 42, 34, 60)); ru = D("ru14w", lambda: G("russia_1914", (10, 44, 34, 60))); ah = G("austria_hungary_1908", (2, 42, 34, 60))
    collapse = ease(seg(T, 106.9, 108.6))
    a.fill(c, cam, "de14", de, PALETTE["germany"], 0.9 * (1 - 0.45 * collapse))
    a.fill(c, cam, "ru14w", ru, PALETTE["russia"], 0.75 * (1 - 0.45 * collapse), band=False)
    a.fill(c, cam, "ah14", ah, PALETTE["austria"], 0.7 * (1 - 0.45 * collapse), band=False)
    a.water(c, cam); a.coast(c, cam)
    a.border(c, cam, "de14b", de.boundary, 1.0, 1.0 - 0.6 * collapse, 2.6, dash=(10, 6) if collapse > 0.5 else None)
    a.border(c, cam, "wp14b", G("west_prussia_1909").boundary, 1.0, 0.9, 2.2, "#3A2F24", dash=(10, 7), halo=False)
    kp = ease(seg(T, 109.3, 111.5))
    glow(c, cam, C("Warsaw"), 330 * kp + 1, PALETTE["poland"], kp)
    L = Layout("1918")
    regions(c, cam, L, [(15.6, 52.3, ["GERMAN", "EMPIRE"], 0.85, 28, {}), (23.2, 53.9, ["RUSSIAN", "EMPIRE"], 0.85 * (1 - kp), 24, {}),
                        (20.2, 50.25, ["AUSTRIA-", "HUNGARY"], 0.85, 24, {}), (17.2, 55.5, ["BALTIC SEA"], 1.0, 40, {"water": True}),
                        (21.2, 52.75, ["POLAND"], kp, 44, {"color": "#7A2E22"})])
    place_city(c, cam, L, C("Warsaw"), "Warsaw", 1.0, 30, "below", capital=True)
    place_city(c, cam, L, C("Danzig"), "Danzig", 1.0, 30, "left")
    title_block(c, "1918", "THE FIRST WORLD WAR ENDS", ease(seg(T, 104.0, 105.2)), y=330,
                sub="the German Empire collapses (November 1918)", sub_alpha=ease(seg(T, 106.9, 107.8)))
    info_box(c, ["Poland independent again: 11 November 1918"], ease(seg(T, 109.4, 110.4)))
    info_box(c, ["Its borders: not yet decided"], ease(seg(T, 113.9, 114.8)), y=1462, colors=["#8A3B2E"])
    caption(c, ["Dashed: Province of West Prussia"], 1.0, y=1555, size=24)
    finish(c, f)

# ------------------------------------------------------------------------------------------- S8 1922 division (158.6–166.4)
def s_1922(c, T, f):
    cam = cam_at(*M.REG_CAM)
    a = base_map(c, 1922, cam)
    wp = G("west_prussia_1909")
    a.fill(c, cam, "pl22", G("poland_1920", VC), PALETTE["poland"], 0.9)
    a.fill(c, cam, "fc22", G("free_city"), PALETTE["freecity"], 0.95)
    a.fill(c, cam, "ep22", G("east_prussia_1922"), PALETTE["germany"], 0.55, band=False)
    a.fill(c, cam, "de22", D("de22", lambda: G("reich_1920_12", VC).difference(G("east_prussia_1922").buffer(100))), PALETTE["germany"], 0.55, band=False)
    a.fill(c, cam, "rbw", G("rb_westpreussen_1922"), "#93A8BF", 0.95)
    a.fill(c, cam, "gm22", G("grenzmark_1922"), "#93A8BF", 0.95, hatch={"step": 13, "w": 1.6, "alpha": 0.35, "color": "#4E5E70"})
    a.water(c, cam); a.coast(c, cam)
    k = ease(seg(T, 159.0, 162.0))
    a.border(c, cam, "wp22b", wp.boundary, 1.0, 1.0 - 0.6 * k, 3.2 - 1.2 * k, "#3A2F24", dash=(12, 8) if k > 0.3 else None)
    L = Layout("1922")
    regions(c, cam, L, [(18.1, 53.6, ["POLAND"], 0.9, 34, {}), (19.25, 54.65, ["FREE CITY", "OF DANZIG"], 0.9, 24, {}),
                        (19.75, 53.75, ["WEST PRUSSIA", "DISTRICT"], ease(seg(T, 162.0, 163.0)), 24, {}),
                        (16.65, 53.75, ["POSEN–", "WEST PRUSSIA"], ease(seg(T, 162.6, 163.6)), 24, {}),
                        (17.55, 54.9, ["BALTIC SEA"], 1.0, 42, {"water": True})])
    for n, side in (("Danzig", "left"), ("Marienwerder", "right"), ("Thorn", "left"), ("Elbing", "right")):
        place_city(c, cam, L, C(n), n, 1.0, 30, side)
    title_block(c, "1922", "THE PROVINCE IS DISSOLVED", ease(seg(T, 158.8, 159.8)), y=330,
                sub="its territory divided four ways")
    legend(c, [(PALETTE["poland"], "Poland", False), (PALETTE["freecity"], "Free City of Danzig", False),
               ("#93A8BF", "To East Prussia (Germany)", False), ("#93A8BF", "To Posen–West Prussia", "#4E5E70")],
           ease(seg(T, 161.0, 162.4)))
    finish(c, f)

# ------------------------------------------------------------------------------------------- S8b treaty map + new border (166.0–179.6)
def s_treatymap(c, T, f):
    document("treaty1919_p0175").draw(c, T - 166.0, 8.4, roi=(3000, 120, 4600, 760), enter=1.0, zoom_full_w=0.98, roi_fill=0.9,
        rot=(-1.6, -0.4), mark=None, caption=["Treaty of Versailles, Map No. 3:", "the new boundaries around Danzig"],
        credit="TREATY OF PEACE WITH GERMANY, U.S. SENATE PRINT 1919 · LIBRARY OF CONGRESS")
    finish(c, f, paper=False, vignette=0.25, grain_alpha=0.12)

def s_newborder(c, T, f):
    cam = lerp_cam(cam_at(18.8, 53.75, 260), cam_at(18.9, 53.7, 220), ease(seg(T, 173.6, 179.8), "sine"))
    a = base_map(c, 1922, cam)
    a.fill(c, cam, "pl22", G("poland_1920", VC), PALETTE["poland"], 0.9)
    a.fill(c, cam, "fc22", G("free_city"), PALETTE["freecity"], 0.95)
    a.fill(c, cam, "de22b", G("reich_1920_12", VC), PALETTE["germany"], 0.8)
    a.water(c, cam); a.coast(c, cam)
    bd = D("pl_de_border", lambda: shared_border(G("poland_1920", VC), G("reich_1920_12", VC), 1500))
    pulse = 0.5 + 0.5 * math.sin((T - 174.4) * 3.0)
    a.border(c, cam, "plde_b", bd, ease(seg(T, 173.8, 176.5)), 1.0, 3.6, "#8A3B2E", nib=True)
    a.border(c, cam, "plde_g", bd, 1.0, 0.25 * ease(seg(T, 176.5, 177.5)) * pulse, 12.0, "#B4533F", halo=False)
    L = Layout("newborder")
    regions(c, cam, L, [(18.35, 53.55, ["POLAND"], 0.9, 32, {}), (19.45, 53.95, ["GERMANY", "(EAST PRUSSIA)"], 0.9, 26, {})])
    for n, side in (("Marienwerder", "right"), ("Graudenz", "left"), ("Danzig", "left")):
        place_city(c, cam, L, C(n), n, 1.0, 30, side)
    title_block(c, None, "NEW INTERNATIONAL BORDERS", ease(seg(T, 173.8, 174.8)), y=300,
                sub="roads, railways and families divided")
    finish(c, f)

# ------------------------------------------------------------------------------------------- S9 interwar (179.6–200.1)
def s_interwar(c, T, f, phase=1):
    k2 = ease(seg(T, 194.8, 200.4), "sine")
    cam = lerp_cam(cam_at(18.6, 53.65, 470), cam_at(18.55, 53.9, 330), k2) if phase == 2 else cam_at(18.6, 53.65, 470)
    a = base_map(c, 1930, cam)
    a.fill(c, cam, "de30", G("reich_1936", VC), PALETTE["germany"], 0.9)
    a.fill(c, cam, "pl30", G("poland_1924", VC), PALETTE["poland"], 0.9)
    a.fill(c, cam, "fc30", G("free_city"), PALETTE["freecity"], 0.95)
    a.water(c, cam); a.coast(c, cam)
    a.border(c, cam, "pl30b", D("pl30b", lambda: G("poland_1924", VC).boundary), 1.0, 1.0, 2.6)
    a.border(c, cam, "fc30b", G("free_city").boundary, 1.0, 1.0, 2.6)
    L = Layout(f"interwar{phase}")
    items = [(16.7, 54.15, ["GERMANY"], 0.9, 32, {}), (20.45, 54.1, ["EAST", "PRUSSIA"], 0.9, 30, {}),
             (19.4, 52.8, ["POLAND"], 0.9, 34, {}), (18.05, 53.6, ["POLISH", "CORRIDOR"], 0.9, 30, {}),
             (17.5, 54.92, ["BALTIC SEA"], 1.0, 40, {"water": True})]
    if phase == 2:
        coal = D("coal", lambda: LineString([P(*p) for p in [(18.9, 50.6), (18.6, 51.6), (18.25, 52.5), (18.0, 53.12), (18.2, 53.8), (18.53, 54.5)]]))
        a.path_line(c, cam, "coal", coal, ease(seg(T, 195.4, 198.8)), "#5A4A3A", 4.5, 0.85, dash=(14, 8), arrow=True)
    regions(c, cam, L, items)
    place_city(c, cam, L, C("Gdynia"), "Gdynia", 1.0, 34 if phase == 2 else 30, "left", capital=True)
    place_city(c, cam, L, C("Danzig"), "Danzig", 1.0, 32, "right")
    for n, side in (("Thorn", "left"), ("Bromberg", "left")):
        place_city(c, cam, L, C(n), n, 1.0, 28, side)
    if phase == 1:
        title_block(c, "1920–1939", "BETWEEN THE WARS", ease(seg(T, 179.8, 180.8)), y=330, date_size=120,
                    sub="German–Polish relations remain tense")
    else:
        title_block(c, None, "GDYNIA", ease(seg(T, 195.0, 196.0)), y=300, sub="Poland's own port on the Baltic")
        info_box(c, ["Gdynia: town rights 1926", "by 1933 more trade than Danzig", "Coal Trunk Line to Silesia (1933)"],
                 ease(seg(T, 196.0, 197.0)), size=32)
    finish(c, f)

# ------------------------------------------------------------------------------------------- S11 memorial (211.4–231.0)
SITES = {"Stutthof": (19.152, 54.33), "Piaśnica": (18.08, 54.63)}
def s_memorial(c, T, f):
    cam = lerp_cam(cam_at(18.7, 54.05, 300), cam_at(18.65, 54.2, 230), ease(seg(T, 211.0, 231.0), "sine"))
    a = base_map(c, 1940, cam, 0.6)
    a.fill(c, cam, "rg_m", G("reichsgau_dwp"), "#B9A9A2", 0.8, band=False)
    a.water(c, cam); a.coast(c, cam)
    a.border(c, cam, "rg_mb", G("reichsgau_dwp").boundary, 1.0, 0.8, 2.2, "#5E2A22", dash=(10, 7))
    L = Layout("memorial")
    regions(c, cam, L, [(18.2, 53.75, ["OCCUPIED", "POMERANIA"], 0.75, 26, {"color": "#4A3A30"})])
    place_city(c, cam, L, C("Danzig"), "Danzig", 1.0, 30, "below")
    for i, (n, t0) in enumerate((("Piaśnica", 214.2), ("Stutthof", 223.9))):
        k = ease(seg(T, t0, t0 + 1.2))
        if k > 0:
            x, y = cam.px(*P(*SITES[n]))
            p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3); p.setColor4f(hexc("#5E2A22", k))
            c.drawCircle(x, y, 13, p)
            q = skia.Paint(AntiAlias=True); q.setColor4f(hexc("#5E2A22", k)); c.drawCircle(x, y, 5, q)
            draw_text(c, n, x + (24 if n == "Stutthof" else -24), y + 11, font("sans", 32), "#3A1E18", k, 0,
                      "left" if n == "Stutthof" else "right", halo=STYLE["halo"], halo_w=8)
    title_block(c, None, ["OCCUPATION AND", "PERSECUTION"], ease(seg(T, 211.4, 212.4)), y=280, sub="1939–1945")
    dark_info(c, ["Intelligenzaktion 1939–40: Polish teachers,", "priests, officials murdered – in Pomerania",
                  "about 23,000 victims (estimate)"], ease(seg(T, 213.4, 214.4)) * (1 - ease(seg(T, 219.0, 219.6))), size=31)
    dark_info(c, ["Piaśnica: 12,000–14,000 murdered (estimates)", "Jewish communities of Danzig and the region",
                  "destroyed in the Holocaust"], ease(seg(T, 219.5, 220.4)) * (1 - ease(seg(T, 223.6, 224.2))), size=31)
    dark_info(c, ["Stutthof camp (from 2 September 1939):", "about 63,000–65,000 prisoners died"],
              ease(seg(T, 224.0, 225.0)), size=33)
    finish(c, f, vignette=0.45)

# ------------------------------------------------------------------------------------------- S12 1945 front & flight (231–244.6)
def s_1945front(c, T, f):
    cam = lerp_cam(cam_at(19.0, 54.0, 520), cam_at(19.1, 54.1, 440), ease(seg(T, 231.0, 244.6), "sine"))
    a = base_map(c, 1945, cam, 0.8)
    a.fill(c, cam, "de44", G("reich_1939_10", (10, 49, 28, 58)), PALETTE["germany"], 0.75)
    a.water(c, cam); a.coast(c, cam)
    soviet = [("sv1", [(22.0, 53.3), (21.0, 53.6), (20.1, 54.05), (19.55, 54.3)], 235.9, "Jan 1945"),
              ("sv2", [(17.6, 52.8), (17.1, 53.4), (16.6, 54.1)], 236.8, "Feb–Mar 1945"),
              ("sv3", [(18.2, 53.4), (18.4, 53.9), (18.6, 54.28)], 237.6, "Danzig falls 30 Mar 1945")]
    for k, pts, t0, lab in soviet:
        a.path_line(c, cam, k, D(k, lambda pts=pts: LineString([P(*p) for p in pts])), ease(seg(T, t0, t0 + 2.6)),
                    "#8A3B2E", 7.0, 0.9, dash=None, arrow=True)
    flight = [("fl1", [(20.2, 54.45), (19.9, 54.38), (19.6, 54.4), (19.3, 54.36), (18.9, 54.37)]),
              ("fl2", [(18.65, 54.45), (17.5, 54.95), (15.5, 54.7), (14.2, 54.3)])]
    for i, (k, pts) in enumerate(flight):
        a.path_line(c, cam, k, D(k, lambda pts=pts: LineString([P(*p) for p in pts])), ease(seg(T, 238.8 + i * 1.2, 241.4 + i * 1.2)),
                    "#3E5C7A", 5.0, 0.95, dash=(10, 7), arrow=True)
    L = Layout("1945front")
    regions(c, cam, L, [(17.4, 55.1, ["BALTIC SEA"], 1.0, 40, {"water": True})])
    for n, side in (("Danzig", "left"), ("Elbing", "right"), ("Königsberg", "left")):
        place_city(c, cam, L, C(n), n, 1.0, 30, side)
    title_block(c, "1945", "THE END OF THE WAR", ease(seg(T, 231.2, 232.2)), y=330, sub="Soviet offensive and civilian flight")
    legend(c, [("#8A3B2E", "Soviet advance (schematic)", False), ("#3E5C7A", "Flight over the frozen lagoon / by sea", False)],
           ease(seg(T, 236.0, 237.0)), cols=1)
    finish(c, f)

# ------------------------------------------------------------------------------------------- S12 population movements (253–268)
def s_moves(c, T, f):
    cam = cam_at(19.9, 52.6, 1150)
    a = base_map(c, 1946, cam, 0.7)
    pl45 = G("poland_1945", WC); pl38 = G("poland_1938", (10, 44, 34, 60))
    lost = D("lost_east", lambda: pl38.difference(pl45.buffer(2000)).buffer(-1500).buffer(1500))
    a.fill(c, cam, "de45m", NE_COUNTRY("DEU"), PALETTE["germany"], 0.85)
    a.fill(c, cam, "pl45m", pl45, PALETTE["poland"], 0.9)
    a.fill(c, cam, "lost", lost, PALETTE["soviet"], 0.85 * ease(seg(T, 260.8, 262.0)),
           hatch={"step": 13, "w": 1.6, "alpha": 0.4, "color": "#4A3A5A"})
    a.fill(c, cam, "su45m", G("soviet_1945"), PALETTE["soviet"], 0.85)
    a.water(c, cam); a.coast(c, cam)
    a.border(c, cam, "wp_m", G("west_prussia_1909").boundary, 1.0, 0.8, 2.0, "#3A2F24", dash=(9, 6), halo=False)
    expel = [("ex1", [(18.6, 54.0), (16.0, 53.9), (13.6, 53.4)]), ("ex2", [(20.0, 53.9), (17.5, 53.3), (14.2, 52.6)]),
             ("ex3", [(17.0, 51.2), (15.5, 51.4), (13.9, 51.6)])]
    for i, (k, pts) in enumerate(expel):
        a.path_line(c, cam, k, D(k, lambda pts=pts: LineString([P(*p) for p in pts])), ease(seg(T, 253.6 + i * 0.5, 256.6 + i * 0.5)),
                    "#3E5C7A", 7.0, 0.9, dash=None, arrow=True)
    arrive = [("ar1", [(25.3, 54.5), (22.5, 54.0), (19.5, 54.0)]), ("ar2", [(24.0, 49.9), (21.0, 51.0), (17.8, 51.5)]),
              ("ar3", [(24.5, 51.5), (21.5, 52.6), (18.8, 53.5)])]
    for i, (k, pts) in enumerate(arrive):
        a.path_line(c, cam, k, D(k, lambda pts=pts: LineString([P(*p) for p in pts])), ease(seg(T, 254.8 + i * 0.5, 257.8 + i * 0.5)),
                    "#9A3A2A", 7.0, 0.9, dash=None, arrow=True)
    L = Layout("moves")
    regions(c, cam, L, [(19.6, 52.3, ["POLAND"], 0.85, 36, {}), (14.4, 51.1, ["GERMANY"], 0.85, 28, {}),
                        (24.6, 51.75, ["TO THE", "USSR"], ease(seg(T, 261.0, 262.0)), 22, {"color": "#4A3A5A"}),
                        (17.0, 55.6, ["BALTIC SEA"], 1.0, 40, {"water": True})])
    place_city(c, cam, L, P(24.03, 49.84), "Lwów", ease(seg(T, 255.0, 256.0)), 28, "right")
    place_city(c, cam, L, P(25.28, 54.69), "Wilno", ease(seg(T, 255.0, 256.0)), 28, "right")
    place_city(c, cam, L, C("Danzig"), "Gdańsk", 1.0, 30, "left")
    title_block(c, None, "THE POST-WAR TRANSFORMATION", ease(seg(T, 253.2, 254.2)), y=300, sub="1945–1950")
    legend(c, [("#3E5C7A", "Germans expelled/displaced (1945–47)", False),
               ("#9A3A2A", "Poles resettled, many from the east (1944–46)", False)], ease(seg(T, 254.0, 255.0)), cols=1)
    caption(c, ["Movements took place in several waves, not all at once"], ease(seg(T, 257.0, 258.0)), y=1530, size=27)
    finish(c, f)

# ------------------------------------------------------------------------------------------- S13 today drift + ghosts (305–329.4)
def s_today_drift(c, T, f):
    k = ease(seg(T, 304.6, 329.4), "sine")
    cam = lerp_cam(cam_at(17.2, 52.95, 800), cam_at(18.75, 53.75, 360), k)
    a = base_map(c, 2025, cam, 0.8)
    pl = G("poland_today", WC)
    a.fill(c, cam, "plt", pl, PALETTE["poland"], 0.9)
    a.fill(c, cam, "det", NE_COUNTRY("DEU"), PALETTE["germany"], 0.9)
    a.fill(c, cam, "rut", G("soviet_kaliningrad"), PALETTE["soviet"], 0.9)
    wp = G("west_prussia_1909")
    a.fill(c, cam, "wpt", wp, "#E6C98C", 1.0 - 0.6 * ease(seg(T, 318.0, 322.0)), band=False,
           hatch={"step": 12, "w": 1.4, "alpha": 0.35, "color": "#6B4A2E"})
    a.water(c, cam, flow=T * 0.25); a.coast(c, cam)
    for kk in ("pomorskie_1999", "kujpom_1999", "warmaz_1999", "zachpom_1999"):
        a.border(c, cam, "vb" + kk, G(kk).boundary, 1.0, 0.5, 1.2, STYLE["ink_soft"], dash=(5, 5), halo=False)
    a.border(c, cam, "plb", D("pltb", lambda: pl.boundary), 1.0, 1.0, 2.8)
    a.border(c, cam, "wptb", wp.boundary, 1.0, 1.0 - 0.5 * ease(seg(T, 318.0, 322.0)), 3.0, "#6B4A2E", dash=(12, 7))
    ghosts = [("g1466", D("sb_rp_order_p", lambda: shared_border(G("royal_prussia_1466"), G("order_1466")))),
              ("g1773", G("west_prussia_1773").boundary), ("g1920", G("poland_1920", VC).boundary),
              ("g1939", G("reichsgau_dwp").boundary)]
    for i, (key, geom) in enumerate(ghosts):
        t0 = 305.9 + i * 1.3
        al = math.sin(math.pi * seg(T, t0, t0 + 3.4)) * 0.7
        if al > 0:
            a.border(c, cam, key, geom, 1.0, al, 2.0, "#8A3B2E", dash=(8, 6), halo=False)
    L = Layout("drift")
    ke = 1 - ease(seg(T, 319.5, 321.0))
    regions(c, cam, L, [(19.8, 51.95, ["POLAND"], 0.9 * ke, 42, {}), (13.4, 51.75, ["GERMANY"], 0.9 * ke, 34, {}),
                        (17.2, 55.45, ["BALTIC SEA"], ke, 42, {"water": True})])
    for n, nm, side in (("Danzig", "Gdańsk", "left"), ("Thorn", "Toruń", "right"), ("Elbing", "Elbląg", "right"),
                        ("Marienwerder", "Kwidzyn", "right"), ("Marienburg", "Malbork", "left")):
        place_city(c, cam, L, C(n), nm, ke, 30, side)
    kc = ease(seg(T, 305.9, 306.8)) * ke
    caption(c, ["Faint red lines: borders of 1466, 1773, 1920 and 1939"], kc, y=1500, size=27)
    # final titles (320.5 'traces …')
    kf = ease(seg(T, 320.4, 322.4))
    if kf > 0:
        v = skia.Paint()
        pc = hexc("#EFE6D2")
        v.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 500), skia.Point(0, 1100)],
                    [skia.Color4f(pc.fR, pc.fG, pc.fB, 0).toColor(), skia.Color4f(pc.fR, pc.fG, pc.fB, 0.72 * kf).toColor(),
                     skia.Color4f(pc.fR, pc.fG, pc.fB, 0.72 * kf).toColor(), skia.Color4f(pc.fR, pc.fG, pc.fB, 0).toColor()],
                    [0.0, 0.3, 0.7, 1.0]))
        c.drawRect(skia.Rect.MakeXYWH(0, 500, W, 600), v)
        draw_text(c, "WEST PRUSSIA", W / 2, 760, font("display_bold", 116), STYLE["ink"], kf, 0.08, halo=STYLE["halo"], halo_w=10,
                  rise=(1 - kf) * 16)
        p = skia.Paint(AntiAlias=True, StrokeWidth=2); p.setColor4f(hexc(STYLE["ink"], 0.75 * kf))
        c.drawLine(W / 2 - 250, 812, W / 2 + 250, 812, p)
        draw_text(c, "A REGION SHAPED BY HISTORY", W / 2, 880, font("caps", 46), STYLE["ink"], kf, 0.12, halo=STYLE["halo"], halo_w=8)
        kb = ease(seg(T, 323.4, 325.0))
        draw_text(c, "HISTORY THAT REMAINS", W / 2, 1000, font("caps_light", 34), "#6B4A2E", kb, 0.3, halo=STYLE["halo"], halo_w=6)
    if T < 304.6:
        pass
    finish(c, f)

def s_today(c, T, f):
    M.map_today(c, seg(T, 294.0, 305.0), f)

# ------------------------------------------------------------------------------------------- shot list
P_LM = mk_photo("danzig_langer_markt_c1895_crop", 89.0, 5.8, ["Danzig: the Langer Markt and Town Hall"],
                "PHOTOCHROM PRINT C. 1890–1900 · LIBRARY OF CONGRESS", focus=((0.5, 0.55), (0.32, 0.4)))
P_GB = mk_photo("danzig_great_bridge_c1895_crop", 94.0, 4.9, ["Danzig: ships on the Motława waterfront"],
                "PHOTOCHROM PRINT C. 1890–1900 · LIBRARY OF CONGRESS", focus=((0.45, 0.6), (0.6, 0.55)), par=((10, 0), (-8, -2)))
P_MK = mk_photo("danzig_marienkirche_c1900_crop", 98.2, 5.4, ["Danzig: St Mary's Church"],
                "PHOTOCHROM PRINT C. 1890–1906 · LIBRARY OF CONGRESS", focus=((0.5, 0.5), (0.4, 0.4)), desat=(99.8, 103.0, 0.6))
P_KF = mk_photo("danzig_kaiser_flags_1920_crop", 184.8, 5.0, ["Danzig, 1920: a street vendor selling", "German imperial flags"],
                "AMERICAN RED CROSS PHOTOGRAPH · LIBRARY OF CONGRESS", focus=((0.5, 0.5), (0.5, 0.45)), box_w=760, center_y=960)
P_PI = mk_photo("gdynia_pilsudski_1935_39_crop", 189.0, 6.2, ["Gdynia: the Polish liner Piłsudski in port (1935–39)"],
                "LIBRARY OF CONGRESS", focus=((0.5, 0.5), (0.55, 0.5)), par=((-10, 0), (8, -2)))
P_KR = mk_photo("danzig_krantor_c1895_crop", 266.8, 16.6, ["Danzig before the war: the Crane Gate on the Motława"],
                "PHOTOCHROM PRINT C. 1890–1900 · LIBRARY OF CONGRESS", zoom=(1.0, 1.22), focus=((0.5, 0.5), (0.72, 0.42)),
                par=((-10, 1), (10, -3)), desat=(268.8, 283.0, 0.75))
P_MK2 = mk_photo("danzig_marienkirche_c1900_crop", 283.0, 12.0, ["Cities, churches and landscapes remained"],
                 "ST MARY'S CHURCH, DANZIG · PHOTOCHROM C. 1890–1906 · LIBRARY OF CONGRESS", zoom=(1.05, 1.25),
                 focus=((0.45, 0.45), (0.35, 0.3)), desat=(289.9, 294.5, 0.5))

def s_kr_overlay(c, T, f):
    P_KR(c, T, f)
    k = ease(seg(T, 268.8, 269.8)) * (1 - ease(seg(T, 275.2, 275.9)))
    dark_info(c, ["For those who had lived there: the loss of home"], k, y=230, size=32)
    k2 = ease(seg(T, 275.8, 276.8))
    dark_info(c, ["For those arriving: a new life in a", "place transformed by war"], k2, y=230, size=32)

def s_mk2_overlay(c, T, f):
    P_MK2(c, T, f)
    k = ease(seg(T, 283.8, 284.8))
    title_block(c, None, "WEST PRUSSIA NO LONGER EXISTED", k, y=300, light=True)

s_kr_overlay.desat = P_KR.desat
s_mk2_overlay.desat = P_MK2.desat

SHOTS = [
    (0.0, 21.6, s_intro),
    (20.4, 32.0, s_teutonic),
    (31.0, 35.4, s_marienburg),
    (34.4, 42.6, s_teutonic),
    (41.4, 58.6, wrap(M.map_1466, 39.6, 58.0)),
    (57.4, 69.6, wrap(M.map_1772, 58.5, 70.5)),
    (68.6, 76.6, wrap(M.map_1773, 68.4, 76.0)),
    (75.8, 85.6, wrap(M.map_1793, 74.5, 82.0)),
    (84.4, 89.9, s_province),
    (89.0, 94.9, P_LM),
    (94.0, 99.1, P_GB),
    (98.2, 104.0, P_MK),
    (103.0, 118.6, s_1918),
    (117.8, 124.6, SV.shot_photo),
    (123.4, 136.4, SV.shot_map_corridor),
    (135.6, 142.0, SV.shot_document),
    (141.2, 151.4, SV.shot_map_danzig),
    (150.6, 159.6, wrap(M.map_plebiscite, 150.5, 157.0)),
    (158.6, 166.8, s_1922),
    (166.0, 174.4, s_treatymap),
    (173.6, 180.4, s_newborder),
    (179.6, 185.6, lambda c, T, f: s_interwar(c, T, f, 1)),
    (184.8, 189.8, P_KF),
    (189.0, 195.6, P_PI),
    (194.8, 200.8, lambda c, T, f: s_interwar(c, T, f, 2)),
    (200.0, 212.0, wrap(M.map_1939, 199.5, 210.5)),
    (211.2, 231.6, s_memorial),
    (230.8, 245.0, s_1945front),
    (244.2, 253.8, wrap(M.map_1945, 243.5, 251.0)),
    (253.0, 267.6, s_moves),
    (266.8, 283.8, s_kr_overlay),
    (283.0, 295.4, s_mk2_overlay),
    (294.6, 305.4, s_today),
    (304.6, T_END, s_today_drift),
]
for i, (a, b, fn) in enumerate(SHOTS):        # unique names for surfaces
    if fn.__name__ == "<lambda>":
        fn.__name__ = f"lambda_{i}"

# transition style per boundary: 'ink' (map↔photo/doc, era change) or 'fade' (similar maps / photo→photo)
def trans_style(prev_fn, next_fn):
    pn, nn = prev_fn.__name__, next_fn.__name__
    if pn.startswith("photo") and nn.startswith("photo"):
        return "fade"
    if any(x in pn for x in ("map_1773", "map_1793")) and any(x in nn for x in ("map_1793",)):
        return "fade"
    if "s_teutonic" in pn and "s_teutonic" in nn:
        return "fade"
    return "ink"

# colour grade (darker, desaturated) for 1939–1945
def grade_amount(T):
    if T < 194.0: return 0.0
    if T < 202.0: return 0.35 * seg(T, 194.0, 202.0)
    if T < 211.0: return 0.35 + 0.15 * seg(T, 202.0, 211.0)
    if T < 231.0: return 0.5
    if T < 246.0: return 0.5 - 0.2 * seg(T, 231.0, 246.0)
    if T < 270.0: return 0.3 - 0.15 * seg(T, 246.0, 270.0)
    if T < 296.0: return 0.15 - 0.15 * seg(T, 270.0, 296.0)
    return 0.0

def grade(arr, g, extra_desat=0.0):
    if g <= 0.001 and extra_desat <= 0.001:
        return arr
    x = arr[..., :3].astype(np.float32)
    lum = (x * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    s = min(1.0, g * 1.1 + extra_desat)
    x = x * (1 - s) + lum * s
    x = x * (1 - 0.35 * g) + np.array([18, 14, 10], np.float32) * 0.35 * g
    out = arr.copy(); out[..., :3] = np.clip(x, 0, 255).astype(np.uint8)
    return out

_surf = {}
def render_shot(fn, T, frame):
    s = _surf.setdefault(fn.__name__, new_surface())
    c = s.getCanvas(); c.clear(skia.ColorBLACK)
    fn(c, T, frame)
    arr = s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    d = getattr(fn, "desat", None)
    if d:
        arr = grade(arr, 0.0, d[2] * ease(seg(T, d[0], d[1])))
    return arr

def frame_at(i):
    T = i / FPS
    act = [(a, b, fn) for a, b, fn in SHOTS if a <= T < b]
    if not act:
        act = [SHOTS[-1]]
    if len(act) == 1:
        out = render_shot(act[0][2], T, i)
    else:
        (a0, b0, f0), (a1, b1, f1) = act[0], act[-1]
        prog = seg(T, a1, b0)
        fa = render_shot(f0, T, i).astype(np.float32); fb = render_shot(f1, T, i).astype(np.float32)
        if trans_style(f0, f1) == "fade":
            m = ease(prog, "sine")
            out = fa * (1 - m) + fb * m
        else:
            out = ink_blend(fa, fb, ink_mask(prog, seed=int(a1 * 7) % 97)[..., None])
        out = out.clip(0, 255).astype(np.uint8); out[..., 3] = 255
    out = grade(out, grade_amount(T))
    g = min(1.0, T / 0.5, (T_END - T) / 1.2)
    if g < 1:
        out = out.copy(); out[..., :3] = (out[..., :3].astype(np.float32) * max(0.0, g)).astype(np.uint8)
    return out

def n_frames():
    return int(round(T_END * FPS))

if __name__ == "__main__":
    warm()
    for x in sys.argv[1:]:
        T = float(x)
        arr = frame_at(int(round(T * FPS)))
        Image.fromarray(arr[..., :3]).save(os.path.join(ROOT, f"build/film_{T:06.2f}.png"))
        print("still", T, flush=True)
