"""Phase 3 animation preview: narration 117.8 s – 151.0 s (Treaty of Versailles → Polish Corridor → Free City).

Shots (narration time T, seconds):
  117.8–124.6  Archival photo: Clemenceau, Wilson, Lloyd George leaving Versailles, 28 June 1919 (LoC) – 2.5D parallax
  123.4–124.6  ink transition → map
  123.4–136.4  Map: new Polish border drawn, Corridor recoloured, separation of East Prussia
  135.6–136.4  ink transition → document
  135.6–142.0  Document: Treaty of Versailles (US Senate print 1919, LoC), Sec. XI 'Free City of Danzig', Art. 100
  141.2–142.0  ink transition → map
  141.2–151.0  Map: Free City of Danzig, then pull-back to the plebiscite area
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, skia
from PIL import Image
from engine.render import (W, H, new_surface, ease, seg, lerp_cam, finish, title_block, caption, PALETTE, STYLE,
                           shared_border, region_label, water_label, Layout, place_city, reserve_region, draw_text,
                           font, hexc, draw_graticule)
from engine.shots import PhotoShot, DocumentShot, ink_mask, ink_blend
from engine.depth import depth_map
from projects.west_prussia.maps import G, P, C, D, cam_at, GRAT, VC, regions
from projects.west_prussia.base import atlas

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T0, T1 = 117.8, 151.0
FPS = 30

_cache = {}
def assets():
    if not _cache:
        Image.MAX_IMAGE_PIXELS = None
        ph = np.asarray(Image.open(os.path.join(ROOT, "assets/images/loc/versailles_leaving_1919_left.png")).convert("RGB"))
        d = depth_map(ph, os.path.join(ROOT, "cache/depth_versailles.npy"))
        _cache["photo"] = PhotoShot(ph, d, box_w=900, center_y=968)
        pg = np.asarray(Image.open(os.path.join(ROOT, "assets/images/loc/treaty1919_p0177.png")).convert("RGB"))
        _cache["doc"] = DocumentShot(pg)
    return _cache

# ------------------------------------------------------------------------------------------- shots
def shot_photo(canvas, T, frame):
    a = assets()
    t = T - T0
    a["photo"].draw(canvas, t, 124.6 - T0, zoom=(1.0, 1.17), focus=((0.5, 0.55), (0.42, 0.52)),
                    par=((-10, 2), (10, -3)),
                    caption=["Clemenceau, Wilson and Lloyd George leaving the", "Palace of Versailles after the signing, 28 June 1919"],
                    credit="KEYSTONE VIEW CO. STEREOGRAPH · LIBRARY OF CONGRESS")
    k = ease(seg(T, 118.5, 119.6), "out")
    title_block(canvas, "1919", "TREATY OF VERSAILLES", k, y=330, light=True, rise=(1 - k) * 18)
    finish(canvas, frame, paper=False, vignette=0.38, grain_alpha=0.14)

def _map_base(canvas, cam, T):
    a = atlas(1920)
    a.base(canvas, cam)
    draw_graticule(a, canvas, cam, GRAT(), 1.0)
    return a

def shot_map_corridor(canvas, T, frame):
    cam = lerp_cam(cam_at(18.7, 53.9, 540), cam_at(18.5, 53.72, 400), ease(seg(T, 123.4, 136.4), "sine"))
    a = _map_base(canvas, cam, T)
    de20 = G("reich_1920_12", VC); pl = G("poland_1920", VC); fc = G("free_city"); wp = G("west_prussia_1909")
    old_de = G("reich_1890", VC)
    transferred = D("transferred1920", lambda: pl.intersection(old_de).buffer(-300).buffer(300))
    pl_core = D("plcore1920", lambda: pl.difference(old_de.buffer(300)))
    new_border = D("plnew1920", lambda: pl.boundary.intersection(old_de.buffer(2000)))
    k = ease(seg(T, 124.8, 129.4), "inout")          # corridor recolour
    a.fill(canvas, cam, "de20", de20, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "fc_as_de", fc, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "plcore", pl_core, PALETTE["poland"], 0.9)
    kr = ease(seg(T, 124.8, 129.8), "out")
    if kr < 1:   # German colour retreats exactly where the Polish colour spreads
        a.fill(canvas, cam, "tr_de", transferred, PALETTE["germany"], 0.9, band=False,
               reveal=(C("Thorn"), kr) if kr > 0 else None, reveal_out=True)
    if kr > 0:
        a.fill(canvas, cam, "tr_pl", transferred, PALETTE["poland"], 0.9, reveal=(C("Thorn"), kr) if kr < 1 else None)
    a.water(canvas, cam, flow=(T - T0) * 0.25); a.coast(canvas, cam)
    a.border(canvas, cam, "wp09", wp.boundary, 1.0, 0.9 * (1 - 0.4 * k), 2.4, "#6B4A2E", dash=(12, 8), halo=False)
    a.border(canvas, cam, "pl-new", new_border,
             ease(seg(T, 124.2, 129.0), "inout"), 1.0, 3.4, nib=True)
    # separation of East Prussia (134.9 s): pulse along the corridor
    pulse = math.sin(math.pi * seg(T, 134.6, 136.4)) if 134.6 < T < 136.4 else 0.0
    if pulse > 0:
        a.border(canvas, cam, "corr-pulse", G("pomorskie_1920").boundary, 1.0, 0.55 * pulse, 6.0, "#B4533F", halo=False)
    L = Layout("seq_corr")
    kl = ease(seg(T, 129.0, 130.2))
    ks = 0.85 + 0.15 * pulse
    regions(canvas, cam, L, [
        (16.65, 54.18, ["GERMANY"], ks, 34 + 4 * pulse, {}),
        (20.45, 54.05, ["EAST", "PRUSSIA"], ks, 32 + 4 * pulse, {}),
        (19.6, 52.82, ["POLAND"], 0.9, 34, {}),
        (18.05, 53.58, ["POLISH", "CORRIDOR"], kl, 38, {}),
        (17.6, 54.92, ["BALTIC SEA"], 1.0, 42, {"water": True}),
    ])
    kc = ease(seg(T, 124.0, 125.4))
    for n, side in [("Danzig", "left"), ("Thorn", "left"), ("Bromberg", "left"), ("Elbing", "right"), ("Gdynia", "left")]:
        place_city(canvas, cam, L, C(n), n, kc, 32, side)
    kt = ease(seg(T, 129.1, 130.0))
    title_block(canvas, "1919", "TREATY OF VERSAILLES", 1.0, title_alpha=1 - kt,
                sub="signed 28 June 1919 · in force 10 January 1920", sub_alpha=1 - kt)
    if kt > 0:
        draw_text(canvas, "THE POLISH CORRIDOR", W / 2, 330 + 42 + 66, font("caps", 50), STYLE["ink"], kt, 0.14,
                  halo=STYLE["halo"], halo_w=9)
        draw_text(canvas, "Poland gains access to the Baltic Sea", W / 2, 330 + 42 + 66 + 66, font("serif_italic", 36),
                  STYLE["ink_soft"], kt, 0.0, halo=STYLE["halo"], halo_w=7)
    finish(canvas, frame)

def shot_document(canvas, T, frame):
    a = assets()
    t = T - 135.6
    marks = [(930, 575, 1232, 616), (752, 675, 1436, 717), (929, 775, 1259, 815)]
    a["doc"].draw(canvas, t, 142.0 - 135.6, roi=(640, 520, 1560, 900), enter=1.0, zoom_full_w=0.80, roi_fill=0.92,
                  rot=(-2.2, -0.5), mark=marks, mark_t=(0.50, 0.75),
                  caption=["Treaty of Versailles, Section XI:", "the Free City of Danzig (Art. 100)"],
                  credit="TREATY OF PEACE WITH GERMANY, U.S. SENATE PRINT 1919 · LIBRARY OF CONGRESS")
    finish(canvas, frame, paper=False, vignette=0.25, grain_alpha=0.12)

def shot_map_danzig(canvas, T, frame):
    k_out = ease(seg(T, 148.2, 150.9), "inout")
    cam = lerp_cam(lerp_cam(cam_at(18.85, 54.22, 215), cam_at(18.8, 54.2, 190), ease(seg(T, 141.2, 148.2), "sine")),
                   cam_at(18.85, 53.95, 330), k_out)
    a = _map_base(canvas, cam, T)
    de20 = G("reich_1920_12", VC); pl = G("poland_1920", VC); fc = G("free_city"); pleb = G("plebiscite_area_marienwerder")
    k = ease(seg(T, 141.8, 143.6), "inout")
    a.fill(canvas, cam, "de20", de20, PALETTE["germany"], 0.9)
    a.fill(canvas, cam, "pl24", pl, PALETTE["poland"], 0.9)
    a.fill(canvas, cam, "fc_de", fc, PALETTE["germany"], 0.9 * (1 - k), band=False)
    a.fill(canvas, cam, "fc", fc, PALETTE["freecity"], 0.95 * k, reveal=(C("Danzig"), ease(seg(T, 141.8, 143.9), "out")))
    kp = ease(seg(T, 148.6, 150.2))
    a.fill(canvas, cam, "pleb", pleb, PALETTE["plebiscite"], kp, hatch={"step": 13, "w": 1.8, "alpha": 0.5, "color": "#8C6A2C"})
    a.water(canvas, cam, flow=(T - T0) * 0.25); a.coast(canvas, cam)
    a.border(canvas, cam, "pl-b", D("plb1920", lambda: pl.boundary), 1.0, 1.0, 2.8)
    a.border(canvas, cam, "fc-b", fc.boundary, ease(seg(T, 141.6, 144.2), "inout"), 1.0, 3.4, "#4F6B3A", nib=True)
    a.border(canvas, cam, "pleb-b", pleb.boundary, ease(seg(T, 148.6, 150.4)), kp, 2.4, "#8C6A2C")
    L = Layout("seq_danzig")
    regions(canvas, cam, L, [
        (18.62, 54.13, ["FREE CITY", "OF DANZIG"], ease(seg(T, 142.6, 143.8)) * (1 - 0.45 * k_out), 34 - 6 * k_out, {"color": "#33452A"}),
        (18.05, 53.98, ["POLAND"], 0.85, 30, {}),
        (19.55, 54.32, ["GERMANY"], 0.85, 28, {}),
        (19.25, 53.83, ["PLEBISCITE", "AREA"], kp, 28, {"color": "#6E4F1E"}),
    ])
    for n, side in [("Danzig", "left"), ("Gdynia", "left"), ("Elbing", "right"), ("Marienwerder", "right")]:
        place_city(canvas, cam, L, C(n), n, 1.0, 32, side)
    ka = ease(seg(T, 141.4, 142.4)) * (1 - ease(seg(T, 148.0, 148.8)))
    title_block(canvas, None, "FREE CITY OF DANZIG", ka, y=300, sub="under the protection of the League of Nations")
    kb = ease(seg(T, 148.6, 149.6))
    title_block(canvas, None, "OTHER AREAS DISPUTED", kb, y=300, sub="plebiscites to follow in 1920")
    # facts in the caption zone
    k1 = ease(seg(T, 143.6, 144.4)) * (1 - ease(seg(T, 148.0, 148.8)))
    k2 = ease(seg(T, 146.3, 147.1)) * (1 - ease(seg(T, 148.0, 148.8)))
    bg = skia.Paint(AntiAlias=True); bg.setColor4f(hexc(STYLE["halo"], 0.85 * max(k1, k2)))
    if max(k1, k2) > 0:
        canvas.drawRoundRect(skia.Rect.MakeXYWH(120, 1360, 700, 150), 14, 14, bg)
        draw_text(canvas, "No longer part of Germany", 470, 1420, font("sans", 38), STYLE["ink"], k1, 0.0)
        draw_text(canvas, "Not incorporated into Poland", 470, 1478, font("sans", 38), "#8A3B2E", k2, 0.0)
    finish(canvas, frame)

# ------------------------------------------------------------------------------------------- timeline
SHOTS = [  # (start, end, fn)
    (117.8, 124.6, shot_photo),
    (123.4, 136.4, shot_map_corridor),
    (135.6, 142.0, shot_document),
    (141.2, 151.0, shot_map_danzig),
]
TRANS = [  # (start, end, seed) – ink wipe from the earlier shot to the later one
    (123.4, 124.6, 3), (135.6, 136.4, 7), (141.2, 142.0, 9),
]

_surf = {}
def _render_shot(fn, T, frame):
    s = _surf.setdefault(fn.__name__, new_surface())
    c = s.getCanvas(); c.clear(skia.ColorBLACK)
    fn(c, T, frame)
    return s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)

def frame_at(i):
    T = T0 + i / FPS
    active = [(a, b, fn) for a, b, fn in SHOTS if a <= T < b + 1e-9]
    if len(active) == 1:
        out = _render_shot(active[0][2], T, i)
    else:
        A, B = active[0], active[1]
        tr = [x for x in TRANS if x[0] <= T <= x[1]]
        a0, a1, seed = tr[0] if tr else (B[0], A[1], 1)
        m = ink_mask(seg(T, a0, a1), seed)[..., None]
        fa = _render_shot(A[2], T, i).astype(np.float32)
        fb = _render_shot(B[2], T, i).astype(np.float32)
        out = ink_blend(fa, fb, m).clip(0, 255).astype(np.uint8); out[..., 3] = 255
    # global fade in/out for the preview
    g = min(1.0, (T - T0) / 0.6, (T1 - T) / 0.8)
    if g < 1:
        out = (out.astype(np.float32) * max(0.0, g)).astype(np.uint8)
        out[..., 3] = 255
    return out

def n_frames():
    return int(round((T1 - T0) * FPS))

if __name__ == "__main__":
    # stills for review: python seq_versailles.py 118.4 126 ...
    for x in sys.argv[1:]:
        T = float(x)
        arr = frame_at(int(round((T - T0) * FPS)))
        Image.fromarray(arr[..., :3]).save(os.path.join(ROOT, f"build/seq_{T:06.2f}.png"))
        print("still", T)
