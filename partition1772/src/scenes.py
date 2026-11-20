"""Preview scenes. Each scene: duration + render(canvas, t). Timings keyed to narration word timestamps
(audio time 'a' = narration clock; scene clock t is offset by the scene's lead-in)."""
import math, skia, numpy as np
from shapely.geometry import LineString
from engine import *

BASE = None; FIN = None
def init():
    global BASE, FIN
    if BASE is None: BASE = Base(); FIN = Finish()

# ==================================================================== shared map drawing
FIELDS = {}
def field(key, geom_name, seeds, res=2.5, amp=0.10, seed=3):
    if key not in FIELDS: FIELDS[key] = RevealField(LAYERS[geom_name], seeds=seeds, res=res, noise_amp=amp, seed=seed)
    return FIELDS[key]

def bg(c):
    c.clear(C(*PAL['paper']))

def world_label(c, cam, wx, wy, text, size, t, **kw):
    p = cam.to_screen(wx, wy); map_label(c, p.x(), p.y(), text, size=size, t=t, **kw)

def world_city(c, cam, name, t, label=True, size=32, dx=14, dy=-12, align='left', capital=False, pulse=None, sub=None, color=PAL['ink'], alpha=1.0):
    p = cam.to_screen(*city(name)); x, y = p.x(), p.y()
    city_marker(c, x, y, t, capital=capital, pulse_t=pulse, color=color, alpha=alpha)
    if label and t > 0.15:
        lt = clamp((t - 0.15) / 0.85)
        draw_text(c, name, x + dx, y + dy, font(SERIF, size), C(*color), align=align, tracking=0.02, alpha=alpha,
                  halo=C(*PAL['paper'], 225), halo_w=size * 0.2, reveal=lt, stagger=0.5, rise=5,
                  shadow=(C(40, 25, 10, 50), 5, 0, 2))
        if sub:
            draw_text(c, sub, x + dx, y + dy + size * 0.95, font(BODY_I, size * 0.72), C(*color), align=align, alpha=alpha,
                      halo=C(*PAL['paper'], 225), halo_w=size * 0.16, reveal=clamp(lt * 1.3 - 0.3), stagger=0.4)

def card(c, x, y, w, h, alpha=1.0, r=14):
    """Frosted parchment card with soft shadow (for legends / statistics)."""
    if alpha <= 0: return
    rr = skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + h), r, r)
    sp = skia.Paint(AntiAlias=True, Color=C(40, 25, 10), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    sp.setAlphaf(0.30 * alpha); c.drawRRect(rr.makeOffset(0, 10) if hasattr(rr, 'makeOffset') else rr, sp)
    p = skia.Paint(AntiAlias=True, Color=C(244, 237, 220)); p.setAlphaf(0.93 * alpha); c.drawRRect(rr, p)
    b = skia.Paint(AntiAlias=True, Color=C(*PAL['gold']), Style=skia.Paint.kStroke_Style, StrokeWidth=1.4); b.setAlphaf(0.8 * alpha)
    c.drawRRect(rr, b)
    inner = skia.RRect.MakeRectXY(skia.Rect(x + 7, y + 7, x + w - 7, y + h - 7), r - 4, r - 4)
    b.setStrokeWidth(0.8); b.setAlphaf(0.45 * alpha); c.drawRRect(inner, b)

def date_card(c, t, top, big, sub=None, y=330, size=150, alpha=1.0):
    """Cinematic date introduction: small-caps kicker, large numerals revealed by a rising mask, expanding rules."""
    if alpha <= 0: return
    if top:
        draw_text(c, top, W / 2, y - size * 0.78, font(SC, 40), C(*PAL['ink']), tracking=0.45, alpha=alpha,
                  reveal=ramp(t, 0.0, 0.9), stagger=0.7, rise=10, halo=C(*PAL['paper'], 160), halo_w=6)
    rule(c, W / 2, y - size * 0.62, 420, ramp(t, 0.2, 1.4), alpha=alpha)
    # numerals: rise through a mask line
    k = ease_out_expo(ramp(t, 0.25, 1.6, lambda v: v))
    c.save(); c.clipRect(skia.Rect(0, y - size * 0.95, W, y + size * 0.18))
    draw_text(c, big, W / 2, y + (1 - k) * size * 0.9, font(CAPS, size), C(*PAL['ink']), tracking=0.06 + 0.10 * (1 - k), alpha=alpha,
              shadow=(C(60, 40, 15, 70), 10, 0, 6))
    c.restore()
    rule(c, W / 2, y + size * 0.3, 420, ramp(t, 0.6, 1.8), alpha=alpha)
    if sub:
        draw_text(c, sub, W / 2, y + size * 0.3 + 62, font(SERIF_I, 46), C(*PAL['ink']), alpha=alpha, reveal=ramp(t, 0.9, 2.0), stagger=0.5, rise=8,
                  halo=C(*PAL['paper'], 160), halo_w=6)

def title_card(c, t, l1, l2, y=300, alpha=1.0):
    if alpha <= 0: return
    draw_text(c, l1, W / 2, y, font(CAPS_B, 68), C(*PAL['ink']), tracking=0.14, alpha=alpha, reveal=ramp(t, 0, 1.2), stagger=0.9, rise=14,
              halo=C(*PAL['paper'], 170), halo_w=8, shadow=(C(60, 40, 15, 60), 10, 0, 5))
    rule(c, W / 2, y + 36, 520, ramp(t, 0.5, 1.7), alpha=alpha)
    draw_text(c, l2, W / 2, y + 100, font(SERIF_I, 54), C(*PAL['ink']), alpha=alpha, reveal=ramp(t, 0.9, 2.1), stagger=0.6, rise=8,
              halo=C(*PAL['paper'], 170), halo_w=7)

def legend(c, items, t, y=1330, alpha=1.0):
    """items: list of (colour, label, hatch?) – compact key, revealed item by item."""
    if alpha <= 0 or t <= 0: return
    n = len(items); h = 64 + 58 * n; x = 70; w = 600
    card(c, x, y, w, h, alpha * ramp(t, 0, 0.5))
    for i, (col, lab, hatched) in enumerate(items):
        it = ramp(t, 0.25 + i * 0.25, 0.9 + i * 0.25)
        if it <= 0: continue
        yy = y + 44 + i * 58
        sw = skia.Rect(x + 34, yy - 18, x + 34 + 54 * ease_out_cubic(it), yy + 16)
        p = skia.Paint(AntiAlias=True, Color=C(*col)); p.setAlphaf(0.85 * alpha); c.drawRect(sw, p)
        if hatched:
            hp = skia.Paint(AntiAlias=True); hp.setShader(hatch_shader(tuple(int(v * .7) for v in col), spacing=7, width=1.4, alpha=0.9))
            hp.setAlphaf(alpha); c.drawRect(sw, hp)
        bp = skia.Paint(AntiAlias=True, Color=C(*PAL['ink']), Style=skia.Paint.kStroke_Style, StrokeWidth=1); bp.setAlphaf(0.6 * alpha * it); c.drawRect(sw, bp)
        draw_text(c, lab, x + 108, yy + 10, font(BODY, 34), C(*PAL['ink']), align='left', alpha=alpha, reveal=it, stagger=0.5, rise=4)

# ------------------------------------------------------------------ the 1772 map in all its states
def draw_map(c, cam, a, st):
    """st: dict of layer intensities / progress values (0..1)."""
    BASE.draw(c, cam)
    # neutral tint on all land (states not otherwise coloured)
    if st.get('neutral', 0) > 0:
        fill_territory(c, cam, layer_path('land', 1.5), PAL['neutral'], 0.22 * st['neutral'], inner_glow=0)
    for n in ('ottoman', 'sweden', 'hre_other'):
        if st.get('neighbours', 0) > 0:
            fill_territory(c, cam, layer_path(n), PAL['neutral'], 0.30 * st['neighbours'], inner_glow=0.6, glow_w=8)
    # the three powers (home territories)
    for key, lay, col, seeds in (('P', 'prussia_pre', 'prussia', [city('Berlin'), city('Königsberg')]),
                                 ('R', 'russia_pre', 'russia', [city('St Petersburg'), city('Moscow')]),
                                 ('A', 'habsburg', 'austria', [city('Vienna')])):
        v = st.get('pow' + key, 0); rv = st.get('powrev' + key, 1)
        if v <= 0: continue
        solid = st.get('powsolid', 1.0)
        if rv < 1:
            f = field('pow' + key, lay, seeds, res=6, amp=0.12, seed=sum(map(ord, key)))
            f.draw_masked(c, cam, layer_path(lay, 0.6), PAL[col], 0.50 * v * lerp(0.4, 1, solid), rv, edge_color=tuple(int(x * .7) for x in PAL[col]))
        else:
            # atlas style: light wash + strong coloured band inside the frontier
            fill_territory(c, cam, layer_path(lay, 0.6), PAL[col], 0.50 * v * lerp(0.4, 1, solid), inner_glow=lerp(2.2, 0.9, solid), glow_w=lerp(26, 12, solid))
            stroke_world(c, cam, layer_path(lay, 0.6), tuple(int(x * .6) for x in PAL[col]), 1.6, alpha=0.7 * v * (1 - solid))
    # Commonwealth
    if st.get('plc_base', 0) > 0:
        fill_territory(c, cam, layer_path('plc_pre_core'), PAL['plc'], 0.28 * st['plc_base'], inner_glow=0.5, glow_w=10)
    v = st.get('plc', 0)
    if v > 0:
        core = st.get('plc_layer', 'plc_pre_core')
        rv = st.get('plcrev', 1)
        if rv < 1:
            f = field('plc', 'plc_pre_core', [city('Warsaw')], res=3, amp=0.14, seed=5)
            f.draw_masked(c, cam, layer_path(core), PAL['plc'], 0.62 * v, rv, edge_color=(150, 112, 52))
        else:
            fill_territory(c, cam, layer_path(core), PAL['plc'], 0.62 * v, inner_glow=1.0, glow_w=14)
        if st.get('courland', 0) > 0:
            fill_territory(c, cam, layer_path('courland'), PAL['plc'], 0.34 * v * st['courland'], inner_glow=0.4, hatch=0.55 * st['courland'], glow_w=8)
    # partition acquisitions (hatched, stronger)
    for key, lay, col, seeds in (('P1', 'royal_prussia', 'prussia', [city('Königsberg'), city('Stettin')]),
                                 ('P2', 'warmia', 'prussia', [city('Königsberg')]),
                                 ('P3', 'netze', 'prussia', [city('Stettin'), city('Berlin')]),
                                 ('R', 'gain_R', 'russia', [city('Smolensk'), (640, 560)]),
                                 ('A', 'gain_A', 'austria', [(-180, -330), (60, -350), (300, -420)])):
        g = st.get('gain' + key, 0)
        if g <= 0: continue
        alpha = st.get('gainA' + key, 1.0)
        f = field('gain' + key, lay, seeds, res=1.5 if key.startswith('P') else 2.5, amp=0.12, seed=len(key) * 7 + ord(key[0]))
        if g < 1:
            f.draw_masked(c, cam, layer_path(lay, 0.15), PAL[col], 0.72 * alpha, g, edge_color=tuple(int(x * .7) for x in PAL[col]),
                          blend=skia.BlendMode.kSrcOver)
        else:
            fill_territory(c, cam, layer_path(lay, 0.15), PAL[col], 0.72 * alpha, inner_glow=0.8, glow_w=12, blend=skia.BlendMode.kSrcOver,
                           hatch=0.30 * alpha * st.get('hatch', 1.0))
    # internal Crown / Lithuania boundary
    if st.get('gdl', 0) > 0:
        draw_border(c, cam, layer_path('gdl_line'), PAL['ink'], 1.6, t=st.get('gdl_t', 1), alpha=0.55 * st['gdl'], pen=False, double=False, glow=0, dash=[10, 7])
    # rivers
    if st.get('rivers', 0) > 0:
        draw_rivers(c, cam, t_draw=st.get('rivers_t', 1), alpha=0.75 * st['rivers'], flow_t=a, highlight=st.get('rv_hl'), hl_amount=st.get('rv_hl_a', 0),
                    zoom_w=clamp(0.75 + 0.25 * cam.scale, 0.8, 1.6))
    # Commonwealth border (pre-1772)
    if st.get('plc_border', 0) > 0:
        bt = st.get('plc_border_t', 1)
        draw_border(c, cam, layer_path('plc_pre', 0.3), PAL['ink'], st.get('plc_border_w', 2.6), t=bt, alpha=st['plc_border'],
                    glow=0.22, dash=st.get('plc_border_dash'))
    if st.get('ghost', 0) > 0:
        draw_border(c, cam, layer_path('plc_pre', 0.3), (110, 80, 50), 2.0, alpha=0.75 * st['ghost'], pen=False, glow=0, dash=[14, 10], double=False)
    if st.get('post_border', 0) > 0:
        draw_border(c, cam, layer_path('plc_rem', 0.3), PAL['ink'], 3.2, t=st.get('post_border_t', 1), alpha=st['post_border'], glow=0.35)
    # partition lines (new borders of 1772)
    for key, col in (('P', 'prussia'), ('R', 'russia'), ('A', 'austria')):
        v = st.get('cut' + key, 0)
        if v > 0:
            draw_border(c, cam, layer_path('cut_' + key, 0.2), tuple(int(x * .62) for x in PAL[col]), st.get('cut_w', 3.4), t=v,
                        alpha=st.get('cutA' + key, 1.0), glow=0.45)

# ==================================================================== S1 — opening map
class S1:
    lead = 1.0; a0 = 0.0; a1 = 31.95; tail = 0.8
    dur = lead + (a1 - a0) + tail
    def render(self, c, t):
        a = t - self.lead + self.a0
        bg(c)
        europe = Cam(-40, 200, 0.31, rot=-4, tilt=24, oy=80)
        europe2 = Cam(40, 210, 0.35, rot=-2, tilt=20, oy=70)
        plc = Cam(170, 175, 0.66, rot=0, tilt=0, oy=40)
        plc2 = Cam(180, 170, 0.69, rot=0, tilt=0, oy=40)
        wide = Cam(110, 300, 0.56, rot=0, tilt=4, oy=40)
        cam = cam_path([(-1, europe, None), (15.8, europe2, ease_in_out_sine), (21.0, plc, ease_in_out_quint), (28.4, plc2, ease_in_out_sine),
                        (31.0, wide, ease_in_out_quint), (33.0, Cam(105, 305, 0.565, tilt=4, oy=40), ease_in_out_sine)], a)
        cam = drift(cam, a, amp=5)
        powers = 1 - 0.45 * ramp(a, 17.0, 21.0)
        st = dict(neutral=1, neighbours=ramp(a, -1, 2) * (1 - 0.3 * ramp(a, 17, 21)),
                  powP=ramp(a, 8.8, 9.6, lambda v: v) and powers, powrevP=ramp(a, 8.8, 11.2, ease_in_out_sine),
                  powR=ramp(a, 10.1, 10.9, lambda v: v) and powers, powrevR=ramp(a, 10.1, 12.8, ease_in_out_sine),
                  powA=ramp(a, 11.4, 12.2, lambda v: v) and powers, powrevA=ramp(a, 11.4, 13.6, ease_in_out_sine),
                  plc=ramp(a, 17.4, 17.6, lambda v: v) if a < 17.4 else 1, plcrev=ramp(a, 17.4, 22.0, ease_in_out_sine),
                  courland=ramp(a, 23.0, 25.0), plc_base=ramp(a, 6.0, 7.5), powsolid=1 - ramp(a, 17.0, 21.0),
                  plc_border=ramp(a, 5.6, 6.0), plc_border_t=ramp(a, 5.8, 8.6, ease_in_out_sine) if a < 17 else ramp(a, 5.8, 8.6),
                  plc_border_w=lerp(1.8, 2.8, ramp(a, 16, 21)),
                  gdl=ramp(a, 22.6, 23.2), gdl_t=ramp(a, 22.6, 25.0),
                  rivers=ramp(a, 18.5, 20.5), rivers_t=ramp(a, 18.5, 23.5, ease_in_out_sine))
        if a < 17.4: st['plc'] = 0
        draw_map(c, cam, a, st)
        horizon_haze(c, cam)
        # foreshadow: the three future losses glimmer as dotted outlines
        fs = window(a, 24.4, 28.6, 0.8, 1.2)
        if fs > 0:
            for lay, col in (('gain_P', 'prussia'), ('gain_R', 'russia'), ('gain_A', 'austria')):
                stroke_world(c, cam, layer_path(lay, 0.6), tuple(int(x * .7) for x in PAL[col]), 2.2, alpha=0.8 * fs, dash=[2, 7], phase=-a * 14)
        # power labels (Europe view)
        lab_a = 1 - ramp(a, 16.0, 17.6)
        world_label(c, cam, -760, 170, 'KINGDOM OF PRUSSIA', 42, ramp(a, 9.0, 10.4), alpha=lab_a, tracking=0.16, color=(40, 56, 78))
        world_label(c, cam, 1150, 700, 'RUSSIAN EMPIRE', 50, ramp(a, 10.2, 11.6), alpha=lab_a, tracking=0.2, color=(96, 40, 28))
        world_label(c, cam, -420, -600, 'HABSBURG MONARCHY', 42, ramp(a, 11.5, 12.9), alpha=lab_a, tracking=0.16, color=(102, 66, 16))
        world_label(c, cam, 170, 110, 'POLAND–LITHUANIA', 34, ramp(a, 6.3, 7.8), alpha=(1 - ramp(a, 8.2, 8.9)), tracking=0.2, color=(110, 80, 40))
        # Commonwealth: cartouche title in the upper negative space (vertical composition)
        ca = ramp(a, 21.4, 21.6, lambda v: v) * (1 - ramp(a, 28.6, 29.6))
        if ca > 0:
            draw_text(c, 'POLISH–LITHUANIAN', W / 2, 250, font(CAPS_B, 60), C(*PAL['ink']), tracking=0.12, alpha=ca, reveal=ramp(a, 21.4, 22.8), stagger=0.9, rise=12,
                      halo=C(*PAL['paper'], 190), halo_w=9, shadow=(C(60, 40, 15, 60), 10, 0, 5))
            draw_text(c, 'COMMONWEALTH', W / 2, 330, font(CAPS_B, 60), C(*PAL['ink']), tracking=0.22, alpha=ca, reveal=ramp(a, 21.7, 23.1), stagger=0.9, rise=12,
                      halo=C(*PAL['paper'], 190), halo_w=9, shadow=(C(60, 40, 15, 60), 10, 0, 5))
            rule(c, W / 2, 372, 520, ramp(a, 22.2, 23.6), alpha=ca)
            draw_text(c, 'on the eve of the partition, 1772', W / 2, 428, font(SERIF_I, 40), C(*PAL['ink']), alpha=ca, reveal=ramp(a, 22.8, 24.2), stagger=0.5,
                      halo=C(*PAL['paper'], 190), halo_w=7)
        lab2 = ramp(a, 23.0, 24.4) * (1 - ramp(a, 29.0, 30.0))
        sub_col = (92, 66, 34)
        world_label(c, cam, 30, -75, 'KINGDOM OF POLAND', 34, lab2, tracking=0.2, color=sub_col)
        world_label(c, cam, 480, 220, 'GRAND DUCHY', 34, ramp(a, 23.4, 24.8) * (1 - ramp(a, 29.0, 30.0)), tracking=0.2, color=sub_col)
        world_label(c, cam, 480, 175, 'OF LITHUANIA', 34, ramp(a, 23.6, 25.0) * (1 - ramp(a, 29.0, 30.0)), tracking=0.2, color=sub_col)
        world_label(c, cam, 60, 585, 'Duchy of Courland', 28, ramp(a, 24.0, 25.4) * (1 - ramp(a, 29.0, 30.0)), fontname=SERIF_I, tracking=0.02, color=sub_col,
                    sub='Polish fief', sub_size=23)
        # cities
        for i, (n, cap, dx, dy, al) in enumerate((('Warsaw', True, 18, -14, 'left'), ('Kraków', False, -16, 34, 'right'), ('Vilnius', False, -16, -12, 'right'))):
            world_city(c, cam, n, ramp(a, 25.9 + i * 0.5, 26.9 + i * 0.5), capital=cap, dx=dx, dy=dy, align=al, size=34)
        # the agreement: diplomatic lines from Berlin and Vienna converge on St Petersburg
        da = ramp(a, 29.4, 31.6, ease_in_out_sine)
        if da > 0:
            sp = cam.to_screen(*city('St Petersburg'))
            for src in ('Berlin', 'Vienna'):
                s0 = cam.to_screen(*city(src))
                ctrl = ((s0.x() + sp.x()) / 2 - 120, (s0.y() + sp.y()) / 2 - 40)
                path = skia.Path(); path.moveTo(s0.x(), s0.y()); path.quadTo(ctrl[0], ctrl[1], sp.x(), sp.y())
                seg, tip = partial_path(path, da)
                p = skia.Paint(AntiAlias=True, Color=C(150, 112, 52), Style=skia.Paint.kStroke_Style, StrokeWidth=3.4,
                               PathEffect=skia.DashPathEffect.Make([10, 6], -a * 30)); c.drawPath(seg, p)
                world_city(c, cam, src, ramp(a, 29.0, 29.9), size=32, dx=-16 if src == 'Berlin' else 16, dy=-14 if src == 'Berlin' else 34, align='right' if src == 'Berlin' else 'left', color=(90, 60, 30))
                if tip:
                    gp = skia.Paint(AntiAlias=True, Color=C(255, 230, 170), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
                    c.drawCircle(tip.x(), tip.y(), 12, gp)
            world_city(c, cam, 'St Petersburg', ramp(a, 31.0, 31.9), pulse=ramp(a, 31.3, 32.8, lambda v: v), size=34, dx=18, dy=-14, align='left', color=(90, 40, 25))
        # date intro & title
        date_card(c, a + 0.2, 'SUMMER', '1772', None, y=420, size=170, alpha=1 - ramp(a, 6.6, 8.0))
        title_card(c, a - 13.6, 'THE FIRST PARTITION', 'of Poland–Lithuania', y=300, alpha=ramp(a, 13.6, 13.7, lambda v: v) * (1 - ramp(a, 19.6, 21.0)))
        FIN.apply(c, t, cam)
        # fade from black
        fade(c, 1 - ramp(t, 0.0, 1.4))
        fade(c, ramp(t, self.dur - 0.5, self.dur))

def top_haze(c, k, y1=420):
    if k <= 0: return
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, y1)], [C(*PAL['paper'], 235), C(*PAL['paper'], 200), C(*PAL['paper'], 0)], [0, 0.55, 1])
    p = skia.Paint(Shader=sh); p.setAlphaf(k); c.drawRect(skia.Rect(0, 0, W, y1), p)

def horizon_haze(c, cam):
    """Atmospheric perspective for tilted shots: distant map dissolves into warm parchment mist."""
    k = clamp(cam.tilt / 30.0)
    if k <= 0.01: return
    y1 = 260 + 520 * k
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, y1)], [C(*PAL['paper'], 255), C(*PAL['paper'], 235), C(*PAL['paper'], 0)], [0, 0.35, 1])
    p = skia.Paint(Shader=sh); p.setAlphaf(k); c.drawRect(skia.Rect(0, 0, W, y1), p)

def fade(c, k, color=(14, 10, 7)):
    if k <= 0: return
    p = skia.Paint(Color=C(*color)); p.setAlphaf(clamp(k)); c.drawRect(skia.Rect(0, 0, W, H), p)

# ==================================================================== S2 — the three rulers
PORTRAITS = {
    'catherine': dict(file='catherine.jpg', face=(0.50, 0.30), name='Catherine II', role='EMPRESS OF RUSSIA', dates='Reigned 1762 – 1796',
                      power='russia', key='Russian Empire', credit='After Alexander Roslin · 1780s · Kunsthistorisches Museum, Vienna'),
    'frederick': dict(file='frederick.jpg', face=(0.505, 0.235), name='Frederick II', role='KING OF PRUSSIA', dates='Reigned 1740 – 1786',
                      power='prussia', key='Kingdom of Prussia', credit='Johann Georg Ziesenis · 1763 · Sanssouci Palace, Potsdam'),
    'maria': dict(file='maria_theresa.jpg', face=(0.548, 0.28), name='Maria Theresa', role='HABSBURG MONARCH', dates='Reigned 1740 – 1780',
                  note='Co-ruler with her son Joseph II from 1765', power='austria', key='Habsburg Monarchy',
                  credit='Martin van Meytens · 1759 · Academy of Fine Arts, Vienna'),
}

def portrait(c, key, lt, dur, alpha=1.0, exit_t=0.0):
    """Cinematic portrait: emerges from darkness in a growing pool of light, slow push toward the face,
    feathered into the archival dark, typographic title block. lt = local time since start."""
    P = PORTRAITS[key]; img = load_image(P['file'])
    iw, ih = img.width(), img.height()
    emerge = ramp(lt, 0.0, 2.2, ease_out_cubic)
    push = ramp(lt, 0, dur + 1.5, lambda v: v)
    fx, fy = P['face']
    # framing: face sits at (540, 560); scale so image width ≈ 1.25 W, growing slowly
    s = (W * 1.22 / iw) * (1.0 + 0.10 * push + 0.05 * (1 - emerge))
    ox = W / 2 - fx * iw * s + 18 * math.sin(lt * 0.25)
    oy = 600 - fy * ih * s - 30 * push - 40 * exit_t
    c.saveLayer(None, None)
    m = skia.Matrix(); m.setScaleTranslate(s, s, ox, oy)
    c.save(); c.concat(m)
    p = skia.Paint(); p.setAlphaf(alpha)
    # exposure: start underexposed & warm, rise to normal
    ex = lerp(0.25, 1.0, emerge)
    p.setColorFilter(skia.ColorFilters.Matrix([ex * 1.02, 0, 0, 0, 0, 0, ex, 0, 0, 0, 0, 0, ex * 0.94, 0, 0, 0, 0, 0, 1, 0]))
    c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
    c.restore()
    # light pool mask (DstIn): radial from the face, radius grows
    rad = lerp(260, 1500, emerge)
    sh = skia.GradientShader.MakeRadial((W / 2, 560), rad, [C(0, 0, 0, 255), C(0, 0, 0, 255), C(0, 0, 0, 0)], [0, 0.45, 1.0])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kDstIn))
    # top feather (no hard image edge)
    sh3 = skia.GradientShader.MakeLinear([(0, max(0, oy)), (0, max(0, oy) + 260)], [C(0, 0, 0, 0), C(0, 0, 0, 255)])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh3, BlendMode=skia.BlendMode.kDstIn))
    # bottom feather into darkness (room for typography)
    sh2 = skia.GradientShader.MakeLinear([(0, 1050), (0, 1360)], [C(0, 0, 0, 255), C(0, 0, 0, 0)])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh2, BlendMode=skia.BlendMode.kDstIn))
    c.restore()
    # warm rim light sweeping once across the portrait
    sw = ramp(lt, 0.6, 3.2, ease_in_out_sine)
    if 0 < sw < 1:
        x = lerp(-400, W + 400, sw)
        g = skia.GradientShader.MakeLinear([(x - 260, 0), (x + 260, 300)], [C(255, 230, 190, 0), C(255, 232, 196, 46), C(255, 230, 190, 0)])
        c.drawRect(skia.Rect(0, 0, W, 1300), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kScreen))
    # typography block
    tb = alpha * (1 - exit_t)
    ty = 1325
    col = PAL[P['power']]
    draw_text(c, P['role'], W / 2, ty - 92, font(SC, 36), C(214, 190, 146), tracking=0.42, alpha=tb, reveal=ramp(lt, 0.9, 2.0), stagger=0.8, rise=8)
    draw_text(c, P['name'], W / 2, ty, font(SERIF, 104), C(246, 236, 214), tracking=0.03, alpha=tb, reveal=ramp(lt, 1.1, 2.5), stagger=0.7, rise=22,
              shadow=(C(0, 0, 0, 160), 14, 0, 6))
    rule(c, W / 2, ty + 42, 440, ramp(lt, 1.6, 3.0), color=(190, 152, 90), alpha=tb)
    draw_text(c, P['dates'], W / 2, ty + 100, font(BODY, 38), C(222, 206, 176), tracking=0.06, alpha=tb, reveal=ramp(lt, 2.0, 3.2), stagger=0.5)
    if P.get('note'):
        draw_text(c, P['note'], W / 2, ty + 152, font(BODY_I, 32), C(200, 182, 150), alpha=tb, reveal=ramp(lt, 2.6, 3.8), stagger=0.5)
    # colour key: links the person to the territorial colour used on every map
    kt = ramp(lt, 2.3, 3.4)
    if kt > 0:
        ky = ty + (205 if P.get('note') else 160)
        kw = text_width(P['key'], font(SC_M, 30), 0.2) + 60
        x0 = W / 2 - kw / 2
        p = skia.Paint(AntiAlias=True, Color=C(*col)); p.setAlphaf(tb * kt)
        c.drawRect(skia.Rect(x0, ky - 20, x0 + 34 * ease_out_cubic(kt), ky + 6), p)
        draw_text(c, P['key'], x0 + 50, ky + 4, font(SC_M, 30), C(214, 196, 160), align='left', tracking=0.2, alpha=tb * kt)
    # credit (authentic source)
    draw_text(c, P['credit'], W / 2, 1150, font(BODY_I, 23), C(220, 205, 180), align='center', alpha=0.7 * tb * ramp(lt, 3.0, 4.0))

def triptych(c, lt, focus=None, focus_t=0.0):
    order = ['frederick', 'catherine', 'maria']
    pw = W / 3
    for i, k in enumerate(order):
        P = PORTRAITS[k]; img = load_image(P['file'])
        e = ease_out_expo(ramp(lt, 0.1 + i * 0.18, 1.3 + i * 0.18, lambda v: v))
        if e <= 0: continue
        x0 = i * pw
        c.save(); c.clipRect(skia.Rect(x0 + 3, 160, x0 + pw - 3, 1260))
        iw, ih = img.width(), img.height(); fx, fy = P['face']
        s = (pw * 2.3 / iw) * (1.06 - 0.04 * ramp(lt, 0, 6, lambda v: v))
        ox = x0 + pw / 2 - fx * iw * s; oy = 560 - fy * ih * s + (1 - e) * 500 * (1 if i % 2 else -1)
        m = skia.Matrix(); m.setScaleTranslate(s, s, ox, oy); c.save(); c.concat(m)
        dim = 1.0
        if focus is not None: dim = lerp(1.0, 1.0 if k == focus else 0.38, focus_t)
        p = skia.Paint(); p.setAlphaf(e)
        p.setColorFilter(skia.ColorFilters.Matrix([dim, 0, 0, 0, 0, 0, dim, 0, 0, 0, 0, 0, dim, 0, 0, 0, 0, 0, 1, 0]))
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
        c.restore()
        sh2 = skia.GradientShader.MakeLinear([(0, 900), (0, 1260)], [C(14, 10, 7, 0), C(14, 10, 7, 255)])
        c.drawRect(skia.Rect(x0, 160, x0 + pw, 1260), skia.Paint(Shader=sh2))
        c.restore()
        col = PAL[P['power']]
        bp = skia.Paint(AntiAlias=True, Color=C(*col)); bp.setAlphaf(e)
        c.drawRect(skia.Rect(x0 + 18, 1262, x0 + 18 + (pw - 36) * e, 1270), bp)
        na = e * (lerp(1, 1 if k == focus else 0.45, focus_t) if focus else 1)
        draw_text(c, P['name'], x0 + pw / 2, 1330, font(SERIF, 44), C(240, 228, 204), alpha=na, reveal=ramp(lt, 0.6 + i * .2, 1.6 + i * .2))
        draw_text(c, P['key'].upper(), x0 + pw / 2, 1378, font(SC_M, 22), C(*[min(255, int(v * 1.35)) for v in col]), tracking=0.18, alpha=na,
                  reveal=ramp(lt, 0.8 + i * .2, 1.8 + i * .2))
    draw_text(c, 'THE THREE POWERS', W / 2, 120, font(CAPS, 40), C(214, 190, 146), tracking=0.32, reveal=ramp(lt, 0.3, 1.5), stagger=0.8, rise=8)

class S2:
    # narration: Catherine 168.40–173.50, Frederick 173.50–181.50 | Maria Theresa 248.50–260.60
    segs = [(168.40, 181.50), (248.50, 261.05)]
    lead = 0.5; tail = 1.0
    dur = lead + sum(b - a for a, b in segs) + tail
    def render(self, c, t):
        a = t - self.lead        # concatenated narration clock (0 = 168.40)
        def at(x):               # absolute narration time -> local concatenated clock
            if x <= 181.5: return x - 168.40
            return 13.10 + (x - 248.50)
        dark_backdrop(c, t, gx=0.5, gy=0.32)
        # warm moving light beams behind the portrait (depth layer)
        for k in range(3):
            x = W * (0.2 + 0.3 * k) + 80 * math.sin(t * 0.13 + k)
            sh = skia.GradientShader.MakeRadial((x, 300 + 60 * k), 520, [C(120, 86, 50, 40), C(0, 0, 0, 0)])
            c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kScreen))
        tc, tf_, tm, tt = at(168.40), at(173.50), at(248.50), at(258.0)
        # Catherine
        if a < tf_ + 1.0:
            x = ramp(a, tf_ - 0.3, tf_ + 0.9)
            portrait(c, 'catherine', a - tc + 0.3, tf_ - tc, alpha=1 - x, exit_t=x)
        if tf_ - 0.3 < a < tm + 1.0:
            x = ramp(a, tm - 0.3, tm + 0.9)
            portrait(c, 'frederick', a - tf_ + 0.3, tm - tf_, alpha=ramp(a, tf_ - 0.3, tf_ + 0.6) * (1 - x), exit_t=x)
        if tm - 0.3 < a < tt + 1.2:
            x = ramp(a, tt - 0.2, tt + 1.0)
            portrait(c, 'maria', a - tm + 0.3, tt - tm, alpha=ramp(a, tm - 0.3, tm + 0.6) * (1 - x), exit_t=x)
        if a > tt - 0.2:
            triptych(c, a - tt + 0.2, focus='frederick', focus_t=ramp(a, at(259.2), at(259.9)))
        FIN.apply(c, t, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)
        fade(c, 1 - ramp(t, 0, 0.8))
        fade(c, ramp(t, self.dur - 0.6, self.dur))

# ==================================================================== S3 — the document scene (engraving of 1773)
CAKE = dict(file='kings_cake.jpg', w=1313, h=2000,
            figs=[('Catherine II', 'Russia', (253, 1020), (-1, 1)), ('Stanisław August', 'King of Poland', (467, 833), (-1, -1)),
                  ('Joseph II', 'Habsburg co-ruler', (940, 905), (1, -1)), ('Frederick II', 'Prussia', (1093, 905), (1, 1))])

class S3:
    a0, a1 = 304.30, 315.35
    lead = 0.6; tail = 0.5
    dur = lead + (a1 - a0) + tail
    def render(self, c, t):
        a = t - self.lead + self.a0
        dark_backdrop(c, t, tone=(20, 15, 11), glow=(64, 46, 30), gy=0.5)
        img = load_image(CAKE['file'])
        iw, ih = img.width(), img.height(); k = iw / CAKE['w']
        # document camera keyframes in image pixel space: (centre x, centre y, px->screen scale, tilt, rot)
        keys = [(304.0, (656, 1000, 0.62, 24, -5)), (306.6, (656, 1050, 0.78, 10, -2)),
                (309.2, (680, 1000, 1.25, 4, 0)), (311.6, (860, 1300, 1.85, 2, 1)), (315.4, (700, 1080, 0.98, 6, -1))]
        def kf(x):
            if x <= keys[0][0]: return keys[0][1]
            for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
                if x <= t1:
                    e = ease_in_out_sine((x - t0) / (t1 - t0)); return tuple(lerp(p, q, e) for p, q in zip(v0, v1))
            return keys[-1][1]
        cx, cy, s, tilt, rot = kf(a)
        s *= 1 + 0.01 * math.sin(a * 0.7)
        m = skia.Matrix(); m.setTranslate(-cx * k, -cy * k); m.postScale(s / k, s / k); m.postRotate(rot)
        th = math.radians(tilt); P = skia.Matrix.MakeAll(1, 0, 0, 0, math.cos(th), 0, 0, -math.sin(th) / 1600, 1)
        m.postConcat(P); m.postTranslate(W / 2, H * 0.47)
        # paper shadow + sheet
        sheet = skia.Path(); sheet.addRect(skia.Rect(-30 * k, -30 * k, iw + 30 * k, ih + 30 * k)); sheet.transform(m)
        sp = skia.Paint(AntiAlias=True, Color=C(0, 0, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40)); sp.setAlphaf(0.7)
        c.save(); c.translate(18, 30); c.drawPath(sheet, sp); c.restore()
        pp = skia.Paint(AntiAlias=True, Color=C(236, 228, 210)); c.drawPath(sheet, pp)
        c.save(); c.concat(m)
        ip = skia.Paint(BlendMode=skia.BlendMode.kMultiply)
        appear = ramp(t, 0.0, 1.6)
        ip.setAlphaf(appear)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), ip)
        c.restore()
        # moving specular sheen on the paper
        sw = (a - 304.0) / 11.0
        x = lerp(-600, W + 600, sw)
        g = skia.GradientShader.MakeLinear([(x - 300, 0), (x + 300, 500)], [C(255, 246, 225, 0), C(255, 246, 225, 34), C(255, 246, 225, 0)])
        c.save(); c.clipPath(sheet, skia.ClipOp.kIntersect, True)
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kScreen))
        # focus pool: darken outside current point of interest
        c.restore()
        # figure annotations (leader lines from the engraving to clean labels)
        for i, (name, sub, (px, py), (dx, dy)) in enumerate(CAKE['figs']):
            lt = window(a, 307.4 + i * 0.55, 311.0, 0.9, 0.6)
            if lt <= 0: continue
            q = m.mapXY(px * k, py * k)
            if not (40 < q.x() < W - 40 and 420 < q.y() < 1420): continue
            sx = 1 if q.x() < W / 2 else -1
            leader_label(c, q.x(), q.y(), name, sx * 90, dy * 150 - 40, lt, size=38, color=(246, 236, 214), fontname=SERIF, sub=sub)
            hp = skia.Paint(AntiAlias=True, Color=C(255, 236, 196), Style=skia.Paint.kStroke_Style, StrokeWidth=2); hp.setAlphaf(0.8 * lt)
            c.drawCircle(q.x(), q.y(), 10 + 4 * math.sin(a * 3), hp)
        # date card (top) & caption (bottom)
        top_a = 1 - ramp(a, 313.8, 314.8)
        c.save()
        shade = skia.GradientShader.MakeLinear([(0, 0), (0, 520)], [C(14, 10, 7, 235), C(14, 10, 7, 0)])
        c.drawRect(skia.Rect(0, 0, W, 520), skia.Paint(Shader=shade))
        c.restore()
        draw_text(c, 'ST PETERSBURG', W / 2, 190, font(SC, 38), C(214, 190, 146), tracking=0.45, reveal=ramp(a, 304.4, 305.6), stagger=0.7, rise=8, alpha=top_a)
        rule(c, W / 2, 222, 380, ramp(a, 304.7, 306.0), color=(190, 152, 90), alpha=top_a)
        draw_text(c, '5 August 1772', W / 2, 310, font(SERIF, 92), C(246, 236, 214), reveal=ramp(a, 304.8, 306.4), stagger=0.6, rise=18, alpha=top_a,
                  shadow=(C(0, 0, 0, 170), 12, 0, 5))
        draw_text(c, 'Partition conventions signed by Russia, Prussia and Austria', W / 2, 372, font(BODY_I, 31), C(222, 206, 176), alpha=top_a,
                  reveal=ramp(a, 306.2, 307.6), stagger=0.4)
        bot = skia.GradientShader.MakeLinear([(0, 1300), (0, 1700)], [C(14, 10, 7, 0), C(14, 10, 7, 235)])
        c.drawRect(skia.Rect(0, 1300, W, H), skia.Paint(Shader=bot))
        cap_a = ramp(a, 311.8, 313.0)
        draw_text(c, '“The Troelfth Cake” · Le Gâteau des Rois', W / 2, 1478, font(SERIF_I, 40), C(240, 228, 204), reveal=cap_a, stagger=0.5, rise=6)
        draw_text(c, 'Engraving by Noël Le Mire after Jean-Michel Moreau, 1773', W / 2, 1528, font(BODY, 27), C(206, 190, 160), alpha=cap_a)
        FIN.apply(c, t, None, vignette=0.7, grain=0.8, light=0.5, dust=1.0)
        fade(c, 1 - ramp(t, 0, 0.7))
        fade(c, ramp(t, self.dur - 0.55, self.dur), color=PAL['paper'])

# ==================================================================== S4 — the partition map
def bar_card(c, t, y=1300, alpha=1.0, title='TERRITORY TAKEN IN 1772'):
    """Animated comparison of the three shares (published figures)."""
    if t <= 0 or alpha <= 0: return
    rows = [('Russia', 92000, 'russia', '≈ 92,000 km²'), ('Austria', 83000, 'austria', '≈ 83,000 km²'), ('Prussia', 36000, 'prussia', '≈ 36,000 km²')]
    x, w, h = 60, 960, 300
    card(c, x, y, w, h, alpha * ramp(t, 0, 0.5))
    draw_text(c, title, x + w / 2, y + 58, font(SC, 32), C(*PAL['ink']), tracking=0.3, alpha=alpha, reveal=ramp(t, 0.1, 0.9))
    for i, (n, v, col, lab) in enumerate(rows):
        bt = ramp(t, 0.4 + i * 0.22, 1.6 + i * 0.22, ease_out_cubic)
        yy = y + 112 + i * 62
        draw_text(c, n, x + 40, yy + 12, font(SERIF, 38), C(*PAL['ink']), align='left', alpha=alpha * clamp(bt * 3))
        bw = 470 * v / 92000 * bt
        p = skia.Paint(AntiAlias=True, Color=C(*PAL[col])); p.setAlphaf(0.9 * alpha)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x + 200, yy - 16, x + 200 + bw, yy + 16), 3, 3), p)
        hp = skia.Paint(AntiAlias=True); hp.setShader(hatch_shader(tuple(int(q * .7) for q in PAL[col]), spacing=7, width=1.3, alpha=0.8)); hp.setAlphaf(alpha)
        c.drawRect(skia.Rect(x + 200, yy - 16, x + 200 + bw, yy + 16), hp)
        draw_text(c, lab, x + 214 + bw, yy + 11, font(BODY, 30), C(*PAL['ink']), align='left', alpha=alpha * ramp(t, 1.2 + i * .22, 1.8 + i * .22))
    draw_text(c, 'Commonly cited estimates', x + w - 30, y + h - 18, font(BODY_I, 22), C(110, 90, 66), align='right', alpha=alpha * ramp(t, 1.5, 2.2))

class S4:
    a0, a1 = 315.35, 372.25
    lead = 0.0; tail = 0.0
    dur = a1 - a0
    def cam(self, a):
        overview = Cam(185, 205, 0.70)
        rp = Cam(-235, 200, 2.25, rot=0, tilt=12, oy=-40)
        rp2 = Cam(-250, 175, 2.05, rot=0, tilt=10, oy=-60)
        link = Cam(-270, 200, 1.02, tilt=6, oy=-120)
        ru = Cam(470, 300, 1.42, rot=0, tilt=10, oy=-90)
        ru2 = Cam(330, 250, 0.98, tilt=6, oy=-120)
        au = Cam(80, -290, 1.62, tilt=10, oy=-130)
        au2 = Cam(40, -260, 1.48, tilt=8, oy=-110)
        end = Cam(185, 160, 0.66, tilt=4)
        keys = [(315.35, overview, None), (317.3, overview, None), (319.4, rp, ease_in_out_quint), (324.8, rp2, ease_in_out_sine),
                (328.2, rp2, None), (331.6, link, ease_in_out_quint), (340.8, Cam(-260, 210, 1.08, tilt=7, oy=-120), ease_in_out_sine),
                (343.4, ru, ease_in_out_quint), (348.6, Cam(500, 300, 1.52, tilt=11, oy=-90), ease_in_out_sine), (351.8, ru2, ease_in_out_quint),
                (357.6, Cam(320, 210, 0.92, tilt=5, oy=-120), ease_in_out_sine),
                (360.4, au, ease_in_out_quint), (366.0, au2, ease_in_out_sine), (371.0, Cam(60, -200, 1.15, tilt=6, oy=-60), ease_in_out_sine),
                (372.25, Cam(70, -150, 1.0, tilt=5, oy=-40), ease_in_out_sine)]
        return drift(cam_path(keys, a), a, amp=4)

    def state(self, a):
        return dict(neutral=1, neighbours=0.75, powsolid=0.0, powP=lerp(0.8, 1.0, window(a, 328.6, 341.2, 1.2, 1.2)), powR=0.8, powA=0.8,
                    plc=1, courland=1, plc_border=1, plc_border_w=2.4,
                    gainP1=ramp(a, 318.9, 322.4, ease_in_out_sine), gainP2=ramp(a, 319.6, 322.6, ease_in_out_sine),
                    gainP3=ramp(a, 325.5, 328.4, ease_in_out_sine),
                    gainR=ramp(a, 342.8, 347.8, ease_in_out_sine), gainA=ramp(a, 359.6, 364.0, ease_in_out_sine),
                    cutP=ramp(a, 318.3, 322.0, ease_in_out_sine) if a < 325.4 else 1, cutR=ramp(a, 341.9, 345.9, ease_in_out_sine),
                    cutA=ramp(a, 359.3, 362.9, ease_in_out_sine),
                    gdl=0.6, rivers=1, rv_hl=['Vistula'] if a < 342 else ['Western Dvina', 'Drut', 'Dnieper'] if a < 358 else ['Vistula', 'San'],
                    rv_hl_a=window(a, 338.2, 341.6, 0.6, 0.8) if a < 342 else window(a, 343.6, 351.4, 0.8, 1.0) if a < 358 else 0)

    def render(self, c, t):
        a = t + self.a0
        bg(c); cam = self.cam(a)
        draw_map(c, cam, a, self.state(a))
        sc = cam.scale
        # --- Prussia
        world_label(c, cam, -300, 225, 'ROYAL PRUSSIA', 46, window(a, 319.0, 328.4, 1.3, 0.8), tracking=0.2, color=(40, 56, 78))
        world_label(c, cam, -95, 210, 'WARMIA', 34, window(a, 320.0, 328.4, 1.1, 0.8), tracking=0.22, color=(40, 56, 78))
        world_city(c, cam, 'Danzig', window(a, 321.7, 329.0, 0.9, 0.8), pulse=ramp(a, 321.9, 323.6, lambda v: v), sub='remained Polish', dx=-18, dy=-14, align='right', size=36)
        world_city(c, cam, 'Thorn', window(a, 322.2, 329.0, 0.9, 0.8), pulse=ramp(a, 322.4, 324.1, lambda v: v), sub='remained Polish', dx=18, dy=-6, size=36)
        world_label(c, cam, -345, 110, 'NETZE DISTRICT', 38, window(a, 325.8, 331.0, 1.2, 0.8), tracking=0.18, color=(40, 56, 78),
                    sub='northern Greater Poland', sub_size=27)
        # Brandenburg <-> East Prussia connection
        lk = window(a, 332.2, 340.9, 0.6, 0.9)
        world_label(c, cam, -600, 0, 'BRANDENBURG', 40, ramp(a, 333.5, 334.6) * lk, tracking=0.2, color=(40, 56, 78))
        world_label(c, cam, 110, 245, 'EAST PRUSSIA', 40, ramp(a, 334.4, 335.5) * lk, tracking=0.2, color=(40, 56, 78))
        ct = ramp(a, 332.3, 335.4, ease_in_out_sine)
        if ct > 0 and lk > 0:
            pts = [city('Berlin'), (-420, 150), (-270, 170), (-160, 240), city('Königsberg')]
            path = skia.Path(); s0 = cam.to_screen(*pts[0]); path.moveTo(s0.x(), s0.y())
            for i in range(1, len(pts) - 1, 1):
                p1 = cam.to_screen(*pts[i]); p2 = cam.to_screen(*pts[i + 1]) if i + 1 < len(pts) else p1
                path.quadTo(p1.x(), p1.y(), (p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            e = cam.to_screen(*pts[-1]); path.lineTo(e.x(), e.y())
            seg, tip = partial_path(path, ct)
            gp = skia.Paint(AntiAlias=True, Color=C(70, 96, 128), Style=skia.Paint.kStroke_Style, StrokeWidth=16,
                            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8), StrokeCap=skia.Paint.kRound_Cap); gp.setAlphaf(0.45 * lk)
            c.drawPath(seg, gp)
            lp = skia.Paint(AntiAlias=True, Color=C(40, 60, 90), Style=skia.Paint.kStroke_Style, StrokeWidth=4, StrokeCap=skia.Paint.kRound_Cap,
                            PathEffect=skia.DashPathEffect.Make([18, 10], -a * 40)); lp.setAlphaf(lk)
            c.drawPath(seg, lp)
            world_city(c, cam, 'Berlin', ramp(a, 332.0, 333.0) * lk, dx=-16, align='right', size=32)
            world_city(c, cam, 'Königsberg', ramp(a, 334.4, 335.4) * lk, size=32)
        vl = window(a, 338.4, 341.4, 0.7, 0.7)
        world_label(c, cam, -175, 30, 'Vistula', 36, vl, fontname=SERIF_I, tracking=0.12, color=(40, 80, 104))
        world_label(c, cam, -300, 420, 'Baltic Sea', 44, vl, fontname=SERIF_I, tracking=0.2, color=(50, 84, 100), halo=False)
        # --- Russia
        rl = window(a, 344.6, 358.4, 1.0, 1.0)
        world_label(c, cam, 360, 520, 'POLISH LIVONIA', 38, ramp(a, 344.7, 346.0) * rl, tracking=0.18, color=(96, 40, 28))
        for i, (n, dx, dy, al) in enumerate((('Dünaburg', -16, -12, 'right'), ('Polotsk', -16, 26, 'right'), ('Vitebsk', 16, -12, 'left'),
                                             ('Mogilev', -16, 8, 'right'), ('Mstislavl', 16, 30, 'left'))):
            world_city(c, cam, n, ramp(a, 345.0 + i * 0.35, 346.2 + i * 0.35) * rl, dx=dx, dy=dy, align=al, size=31, color=(70, 36, 24))
        rv = window(a, 343.8, 351.4, 0.8, 0.8)
        world_label(c, cam, 330, 450, 'Dvina', 32, rv, fontname=SERIF_I, tracking=0.1, color=(40, 80, 104))
        world_label(c, cam, 455, 170, 'Drut', 30, rv, fontname=SERIF_I, tracking=0.1, color=(40, 80, 104))
        world_label(c, cam, 590, 15, 'Dnieper', 32, rv, fontname=SERIF_I, tracking=0.1, color=(40, 80, 104))
        bar_card(c, a - 349.0, y=1290, alpha=1 - ramp(a, 357.6, 358.6))
        # --- Austria
        al = window(a, 363.6, 372.25, 1.2, 0.01)
        world_label(c, cam, 110, -300, 'GALICIA', 58, al, tracking=0.32, color=(102, 66, 16))
        world_label(c, cam, 110, -342, '', 10, 0)
        sub_a = ramp(a, 364.6, 366.0)
        p = cam.to_screen(110, -300)
        draw_text(c, 'later the Kingdom of Galicia and Lodomeria', p.x(), p.y() + 48, font(BODY_I, 28), C(102, 66, 16), alpha=sub_a * al,
                  halo=C(*PAL['paper'], 220), halo_w=5, reveal=sub_a, stagger=0.4)
        world_city(c, cam, 'Lemberg', ramp(a, 362.6, 363.8) * window(a, 360, 372.25, 1, 0.01), sub='Lviv', size=34, color=(80, 50, 14))
        world_city(c, cam, 'Kraków', ramp(a, 360.6, 361.8) * window(a, 360, 372.25, 1, 0.01), sub='remained Polish', dx=-18, dy=-16, align='right', size=34)
        world_city(c, cam, 'Wieliczka', ramp(a, 368.8, 369.8), sub='salt mines', dx=16, dy=40, size=30, color=(80, 50, 14))
        # legend once all three are visible
        FIN.apply(c, t + 40, cam)
        fade(c, 1 - ramp(t, 0, 0.6), color=PAL['paper'])

# ==================================================================== S5 — before / after
class S5:
    a0, a1 = 372.25, 388.0
    lead = 0.0; tail = 1.6
    dur = (a1 - a0) + tail
    def render(self, c, t):
        a = t + self.a0
        bg(c)
        keys = [(372.25, Cam(70, -150, 1.0, tilt=5, oy=-40), None), (376.8, Cam(120, 150, 0.40, rot=-2, tilt=24, oy=-60), ease_in_out_quint),
                (379.6, Cam(140, 170, 0.43, rot=-1, tilt=20, oy=-60), ease_in_out_sine),
                (382.2, Cam(185, 150, 0.64, tilt=0, oy=-170), ease_in_out_quint), (388.0, Cam(150, 130, 0.72, tilt=0, oy=-170), ease_in_out_sine),
                (390.0, Cam(140, 125, 0.74, tilt=0, oy=-170), ease_in_out_sine)]
        cam = drift(cam_path(keys, a), a, amp=4)
        bp = ramp(a, 373.2, 376.6)            # balance-of-power wide view: powers re-intensify
        sep = ramp(a, 380.2, 383.4, ease_in_out_sine)   # before -> after
        st = dict(neutral=1, neighbours=0.75, powsolid=0.6 * bp * (1 - sep), powP=0.8 + 0.2 * bp, powR=0.8 + 0.2 * bp, powA=0.8 + 0.2 * bp,
                  plc=1, courland=1, plc_border=1 - sep, plc_border_w=2.4,
                  gainP1=1, gainP2=1, gainP3=1, gainR=1, gainA=1, gdl=0.6 * (1 - sep), rivers=1 - 0.4 * bp,
                  cutP=1, cutR=1, cutA=1, ghost=sep, post_border=sep, post_border_t=1)
        # the "before" flash: briefly show the unpartitioned Commonwealth, then the losses fall away
        before = window(a, 379.9, 381.9, 0.5, 0.7)
        for k in ('P1', 'P2', 'P3', 'R', 'A'): st['gainA' + k] = 1 - before
        st['cutA' + 'P'] = st['cutA' + 'R'] = st['cutA' + 'A'] = 1 - before
        draw_map(c, cam, a, st)
        if before > 0:
            fill_territory(c, cam, layer_path('plc_pre_core'), PAL['plc'], 0.55 * before, inner_glow=0.5)
        # labels
        world_label(c, cam, -560, 30, 'PRUSSIA', 44, window(a, 374.0, 380.0, 1.0, 0.8), tracking=0.25, color=(40, 56, 78))
        world_label(c, cam, 1000, 520, 'RUSSIA', 50, window(a, 374.4, 380.0, 1.0, 0.8), tracking=0.25, color=(96, 40, 28))
        world_label(c, cam, -330, -560, 'AUSTRIA', 44, window(a, 374.8, 380.0, 1.0, 0.8), tracking=0.25, color=(102, 66, 16))
        top_haze(c, ramp(a, 379.6, 380.4) * (1 - ramp(a, 388.6, 389.4)))
        # year counter
        yr_a = ramp(a, 379.8, 380.5) * (1 - ramp(a, 388.6, 389.4))
        y = 255
        c.save(); c.clipRect(skia.Rect(0, y - 120, W, y + 30))
        k = ease_in_out_quint(ramp(a, 381.8, 382.8, lambda v: v))
        draw_text(c, '1771', W / 2, y - 130 * k, font(CAPS, 120), C(*PAL['ink']), tracking=0.08, alpha=yr_a, shadow=(C(60, 40, 15, 60), 10, 0, 5))
        draw_text(c, '1773', W / 2, y + 130 * (1 - k), font(CAPS, 120), C(*PAL['ink']), tracking=0.08, alpha=yr_a, shadow=(C(60, 40, 15, 60), 10, 0, 5))
        c.restore()
        draw_text(c, 'BEFORE' if k < .5 else 'AFTER THE FIRST PARTITION', W / 2, y + 66, font(SC, 34), C(*PAL['ink']), tracking=0.35, alpha=yr_a,
                  halo=C(*PAL['paper'], 170), halo_w=6)
        # proportional bar: the Commonwealth's territory split
        bt = ramp(a, 382.6, 384.6)
        if bt > 0:
            x0, y0, wbar = 90, 1330, 900
            ca = 1 - ramp(a, 388.8, 389.6)
            card(c, 60, 1250, 960, 260, alpha=ca * ramp(a, 382.4, 383.0))
            draw_text(c, 'TERRITORY OF THE COMMONWEALTH, 1772', W / 2, 1300, font(SC, 28), C(*PAL['ink']), tracking=0.22, alpha=ca, reveal=ramp(a, 382.6, 383.4))
            tot = 733000.0
            segs = [('plc', 522000), ('russia', 92000), ('austria', 83000), ('prussia', 36000)]
            xx = x0
            for i, (col, v) in enumerate(segs):
                st_ = ramp(a, 382.8 + i * 0.25, 383.8 + i * 0.25, ease_out_cubic)
                wv = wbar * v / tot
                pnt = skia.Paint(AntiAlias=True, Color=C(*PAL[col])); pnt.setAlphaf(ca * (0.85 if col != 'plc' else 0.75))
                off = 0 if col == 'plc' else 14 * ramp(a, 384.0, 385.0, ease_out_back)
                c.drawRect(skia.Rect(xx + off, y0, xx + off + wv * st_, y0 + 44), pnt)
                if col != 'plc':
                    hp = skia.Paint(AntiAlias=True); hp.setShader(hatch_shader(tuple(int(q * .7) for q in PAL[col]), spacing=7, width=1.3, alpha=0.8)); hp.setAlphaf(ca)
                    c.drawRect(skia.Rect(xx + off, y0, xx + off + wv * st_, y0 + 44), hp)
                xx += wv
            ta = ramp(a, 384.2, 385.4) * ca
            draw_text(c, 'remained', x0 + 6, y0 + 88, font(BODY_I, 30), C(*PAL['ink']), align='left', alpha=ta)
            draw_text(c, 'lost: almost one third', x0 + wbar, y0 + 88, font(BODY_I, 30), C(*PAL['ink']), align='right', alpha=ta)
            draw_text(c, '≈ 211,000 km² · c. 4–5 million people', W / 2, y0 + 150, font(BODY_SB, 33), C(*PAL['ink']), alpha=ramp(a, 384.8, 386.0) * ca,
                      reveal=ramp(a, 384.8, 386.0), stagger=0.4)
        # it did not disappear
        world_label(c, cam, 30, 60, 'POLISH–LITHUANIAN', 44, window(a, 385.9, 390.0, 1.2, 0.8), tracking=0.2)
        world_label(c, cam, 30, 60 - 72, 'COMMONWEALTH', 44, window(a, 386.1, 390.0, 1.2, 0.8), tracking=0.2)
        FIN.apply(c, t + 100, cam)
        fade(c, ramp(t, self.dur - 1.2, self.dur))

SCENES = {'S1': S1(), 'S2': S2(), 'S3': S3(), 'S4': S4(), 'S5': S5()}
