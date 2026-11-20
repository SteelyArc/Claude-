"""FINAL VERSION: full-length documentary (narration 0–526 s).
All scenes are driven by the absolute narration clock `a` (film time T = a + LEAD).
A compositor blends neighbouring scenes through designed transitions; subtitles and finishing are applied once on top."""
import math, json, skia, numpy as np
import scenes as S
from scenes import *          # helpers: draw_map, world_label, world_city, card, date_card, title_card, top_haze, portrait, triptych …
import subtitles

LEAD = 1.0
END_A = 529.0                 # narration ends 526.0; hold the end card

# ------------------------------------------------------------------ word clock helper (medium transcript)
_WORDS = subtitles.words()
def wt(word, near):
    """start time of the occurrence of `word` closest to `near` (narration seconds)."""
    best = None
    for w in _WORDS:
        if w['w'].strip('.,;:?!').lower() == word.lower():
            if best is None or abs(w['s'] - near) < abs(best - near): best = w['s']
    return best if best is not None else near

PORTRAITS['repnin']['dates'] = 'In Warsaw 1763 – 1768'
PORTRAITS['henry'] = dict(file='henry.jpg', face=(0.50, 0.19), zoom=1.0, name='Prince Henry', role='PRINCE OF PRUSSIA',
                          dates="Frederick's brother", power='prussia', key='In St Petersburg 1770 – 71',
                          credit='Johann Heinrich Wilhelm Tischbein · 1769')
PORTRAITS['kaunitz'] = dict(file='kaunitz.jpg', face=(0.53, 0.36), zoom=1.0, name='Kaunitz', role='HABSBURG STATE CHANCELLOR',
                            dates='Wenzel Anton von Kaunitz', power='austria', key='Habsburg Monarchy', credit='Jean-Étienne Liotard')

# ------------------------------------------------------------------ shared visual building blocks
def map_frame(c, a, cam, st, labels=None, haze=True):
    bg(c); draw_map(c, cam, a, st)
    if labels: labels(cam)
    if haze: horizon_haze(c, cam)

def base_state(**kw):
    st = dict(neutral=1, neighbours=0.75, powsolid=0.0, powP=0.8, powR=0.8, powA=0.8, plc=1, courland=1, plc_border=1, plc_border_w=2.4,
              gdl=0.5, rivers=0.8)
    st.update(kw); return st

def post_state(**kw):
    st = base_state(gainP1=1, gainP2=1, gainP3=1, gainR=1, gainA=1, cutP=1, cutR=1, cutA=1, plc_border=0, ghost=0.6, post_border=1, gdl=0.0)
    st.update(kw); return st

def kicker(c, a, a0, top, big, sub=None, y=300, size=96, alpha=1.0, dark=False, a1=None):
    """Elegant date/title introduction (kicker line, large serif title, rule, italic subtitle)."""
    al = alpha * ramp(a, a0, a0 + 0.3) * (1 - (ramp(a, a1 - 0.6, a1) if a1 else 0))
    if al <= 0: return
    ink = C(246, 236, 214) if dark else C(*PAL['ink'])
    sub_c = C(222, 206, 176) if dark else C(*PAL['ink'])
    gold = (190, 152, 90) if dark else PAL['gold']
    halo = None if dark else C(*PAL['paper'], 190)
    if top:
        draw_text(c, top, W / 2, y - size * 0.95, font(SC, 36), C(214, 190, 146) if dark else C(*PAL['ink']), tracking=0.42, alpha=al,
                  reveal=ramp(a, a0, a0 + 1.0), stagger=0.7, rise=8, halo=halo, halo_w=6)
    draw_text(c, big, W / 2, y, font(SERIF, size), ink, tracking=0.02, alpha=al, reveal=ramp(a, a0 + 0.15, a0 + 1.4), stagger=0.6, rise=size * 0.2,
              halo=halo, halo_w=8, shadow=(C(0, 0, 0, 150) if dark else C(60, 40, 15, 60), 12, 0, 5))
    rule(c, W / 2, y + size * 0.36, 440, ramp(a, a0 + 0.4, a0 + 1.6), color=gold, alpha=al)
    if sub:
        draw_text(c, sub, W / 2, y + size * 0.36 + 56, font(SERIF_I, 42), sub_c, alpha=al, reveal=ramp(a, a0 + 0.8, a0 + 2.0), stagger=0.5,
                  halo=halo, halo_w=6)

def chips(c, a, items, y=1240, dark=False, alpha=1.0, size=40):
    """Keyword chips revealed at word times: items = [(text, t_in)], laid out centred on one or two rows."""
    f = font(BODY_SB, size)
    rows = [[]]; widths = [0]
    for txt, t0 in items:
        w = text_width(txt, f) + 52
        if widths[-1] + w > W - 120 and rows[-1]: rows.append([]); widths.append(0)
        rows[-1].append((txt, t0, w)); widths[-1] += w + 18
    for r, row in enumerate(rows):
        x = W / 2 - (widths[r] - 18) / 2; yy = y + r * (size + 42)
        for txt, t0, w in row:
            k = ease_out_back(ramp(a, t0, t0 + 0.45, lambda v: v), 1.2) * alpha
            if k > 0:
                rr = skia.RRect.MakeRectXY(skia.Rect(x, yy - size * 0.95, x + w, yy + size * 0.5), 12, 12)
                bp = skia.Paint(AntiAlias=True, Color=C(30, 21, 13) if dark else C(246, 239, 222)); bp.setAlphaf(0.88 * clamp(k))
                sp = skia.Paint(AntiAlias=True, Color=C(*PAL['gold']), Style=skia.Paint.kStroke_Style, StrokeWidth=1.4); sp.setAlphaf(clamp(k))
                c.save(); c.translate(x + w / 2, yy); c.scale(lerp(0.85, 1, clamp(k)), lerp(0.85, 1, clamp(k))); c.translate(-(x + w / 2), -yy)
                sh = skia.Paint(AntiAlias=True, Color=C(0, 0, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)); sh.setAlphaf(0.25 * clamp(k))
                c.drawRRect(rr.makeOffset(0, 6) if hasattr(rr, 'makeOffset') else rr, sh)
                c.drawRRect(rr, bp); c.drawRRect(rr, sp)
                draw_text(c, txt, x + w / 2, yy, f, C(246, 236, 214) if dark else C(*PAL['ink']), alpha=clamp(k))
                c.restore()
            x += w + 18

def painting(c, a, file, keys, credit, title=None, a_in=None, frame=True, tone=(18, 13, 9)):
    """Authentic painting / print presented in 2.5D: slight perspective tilt, slow camera path over details,
    soft shadow, gilt hairline frame, moving sheen.  keys: [(a, cx, cy, zoom, tilt, rot)] in image-normalised coords,
    zoom = multiple of 'fit width'."""
    dark_backdrop(c, a, tone=tone, glow=(60, 44, 28), gy=0.45)
    img = load_image(file); iw, ih = img.width(), img.height()
    def kf(x):
        if x <= keys[0][0]: return keys[0][1:]
        for k0, k1 in zip(keys, keys[1:]):
            if x <= k1[0]:
                e = ease_in_out_sine((x - k0[0]) / (k1[0] - k0[0])); return tuple(lerp(p, q, e) for p, q in zip(k0[1:], k1[1:]))
        return keys[-1][1:]
    cx, cy, z, tilt, rot = kf(a)
    s = W / iw * z * (1 + 0.006 * math.sin(a * 0.6))
    m = skia.Matrix(); m.setTranslate(-cx * iw, -cy * ih); m.postScale(s, s); m.postRotate(rot)
    th = math.radians(tilt); P_ = skia.Matrix.MakeAll(1, 0, 0, 0, math.cos(th), 0, 0, -math.sin(th) / 1700, 1)
    m.postConcat(P_); m.postTranslate(W / 2, H * 0.44)
    rect = skia.Path(); rect.addRect(skia.Rect(0, 0, iw, ih)); rect.transform(m)
    sp = skia.Paint(AntiAlias=True, Color=C(0, 0, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 36)); sp.setAlphaf(0.75)
    c.save(); c.translate(14, 26); c.drawPath(rect, sp); c.restore()
    c.save(); c.concat(m)
    c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), skia.Paint())
    c.restore()
    if frame:
        fp = skia.Paint(AntiAlias=True, Color=C(176, 140, 74), Style=skia.Paint.kStroke_Style, StrokeWidth=2.0); fp.setAlphaf(0.8)
        c.drawPath(rect, fp)
    x = lerp(-700, W + 700, ((a * 0.09) % 1.0))
    g = skia.GradientShader.MakeLinear([(x - 320, 0), (x + 320, 520)], [C(255, 246, 225, 0), C(255, 246, 225, 26), C(255, 246, 225, 0)])
    c.save(); c.clipPath(rect, skia.ClipOp.kIntersect, True); c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kScreen)); c.restore()
    # bottom shade for typography
    bot = skia.GradientShader.MakeLinear([(0, 1040), (0, 1330)], [C(*tone, 0), C(*tone, 235)])
    c.drawRect(skia.Rect(0, 1040, W, H), skia.Paint(Shader=bot))
    top = skia.GradientShader.MakeLinear([(0, 0), (0, 470)], [C(*tone, 230), C(*tone, 0)])
    c.drawRect(skia.Rect(0, 0, W, 470), skia.Paint(Shader=top))
    if credit:
        ca = ramp(a, (a_in or keys[0][0]) + 1.0, (a_in or keys[0][0]) + 2.2)
        if title:
            draw_text(c, title, W / 2, 1300, font(SERIF_I, 40), C(240, 228, 204), alpha=ca, reveal=ca, stagger=0.5, rise=6)
        draw_text(c, credit, W / 2, 1300 + (48 if title else 0), font(BODY, 27), C(206, 190, 160), alpha=ca)
    return m

def inset_portrait(c, a, key, a0, a1, x=560, y=250, w=440, h=520):
    """Cameo card over a map: a portrait in a gilt frame slides in, with name and role."""
    P = PORTRAITS[key]; img = load_image(P['file'])
    k = ease_out_expo(ramp(a, a0, a0 + 0.9, lambda v: v)) * (1 - ramp(a, a1 - 0.5, a1))
    if k <= 0: return
    ox = (1 - k) * 220
    rr = skia.RRect.MakeRectXY(skia.Rect(x + ox, y, x + ox + w, y + h), 12, 12)
    sh = skia.Paint(AntiAlias=True, Color=C(30, 18, 8), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)); sh.setAlphaf(0.45 * k)
    c.drawRRect(rr.makeOffset(10, 18) if hasattr(rr, 'makeOffset') else rr, sh)
    c.save(); c.clipRRect(rr, True)
    iw, ih = img.width(), img.height(); fx, fy = P['face']
    s = w * 1.6 / iw * (1.02 + 0.03 * ramp(a, a0, a1, lambda v: v))
    m = skia.Matrix(); m.setScaleTranslate(s, s, x + ox + w / 2 - fx * iw * s, y + h * 0.36 - fy * ih * s)
    c.save(); c.concat(m); p = skia.Paint(); p.setAlphaf(k); c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p); c.restore()
    g = skia.GradientShader.MakeLinear([(0, y + h * 0.55), (0, y + h)], [C(18, 13, 9, 0), C(18, 13, 9, 245)])
    c.drawRect(skia.Rect(x + ox, y, x + ox + w, y + h), skia.Paint(Shader=g))
    c.restore()
    fp = skia.Paint(AntiAlias=True, Color=C(*PAL['gold']), Style=skia.Paint.kStroke_Style, StrokeWidth=2.2); fp.setAlphaf(k); c.drawRRect(rr, fp)
    cx = x + ox + w / 2
    draw_text(c, P['role'], cx, y + h - 112, font(SC, 22), C(214, 190, 146), tracking=0.25, alpha=k)
    draw_text(c, P['name'], cx, y + h - 62, font(SERIF, 48), C(246, 236, 214), alpha=k)
    draw_text(c, P['dates'] if key != 'kaunitz' else P['dates'], cx, y + h - 26, font(BODY_I, 25), C(214, 196, 160), alpha=k)

def arrow(c, cam, pts, t, col, width=7, alpha=1.0, head=26, dashed=False, a=0.0):
    """Animated motion-path arrow in world coords (smooth curve through pts), drawn progressively with an arrowhead."""
    if t <= 0 or alpha <= 0: return
    sp = [cam.to_screen(*p) for p in pts]
    path = skia.Path(); path.moveTo(sp[0].x(), sp[0].y())
    if len(sp) == 2: path.lineTo(sp[1].x(), sp[1].y())
    else:
        for i in range(1, len(sp) - 1):
            mx = (sp[i].x() + sp[i + 1].x()) / 2; my = (sp[i].y() + sp[i + 1].y()) / 2
            path.quadTo(sp[i].x(), sp[i].y(), mx if i < len(sp) - 2 else sp[-1].x(), my if i < len(sp) - 2 else sp[-1].y())
    seg, tip = partial_path(path, t)
    g = skia.Paint(AntiAlias=True, Color=C(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=width * 2.6, StrokeCap=skia.Paint.kRound_Cap,
                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, width)); g.setAlphaf(0.35 * alpha); c.drawPath(seg, g)
    p = skia.Paint(AntiAlias=True, Color=C(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=width, StrokeCap=skia.Paint.kRound_Cap)
    if dashed: p.setPathEffect(skia.DashPathEffect.Make([width * 2.6, width * 1.6], -a * 60))
    p.setAlphaf(alpha); c.drawPath(seg, p)
    meas = skia.PathMeasure(seg, False); L = meas.getLength()
    if L > 10:
        pos = meas.getPosTan(L); pt, tg = pos if isinstance(pos, tuple) else (None, None)
        if pt is not None:
            ang = math.atan2(tg.y(), tg.x())
            hp = skia.Path(); hx, hy = pt.x(), pt.y()
            hp.moveTo(hx + math.cos(ang) * head * 0.5, hy + math.sin(ang) * head * 0.5)
            hp.lineTo(hx + math.cos(ang + 2.5) * head, hy + math.sin(ang + 2.5) * head)
            hp.lineTo(hx + math.cos(ang - 2.5) * head, hy + math.sin(ang - 2.5) * head); hp.close()
            ap = skia.Paint(AntiAlias=True, Color=C(*col)); ap.setAlphaf(alpha); c.drawPath(hp, ap)

def ripples(c, cam, wx, wy, a, a0, a1, col, n=3, rmax=260):
    if not (a0 < a < a1): return
    p = cam.to_screen(wx, wy); k = window(a, a0, a1, 0.6, 0.8)
    for i in range(n):
        ph = ((a - a0) * 0.45 + i / n) % 1.0
        rp = skia.Paint(AntiAlias=True, Color=C(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=3 * (1 - ph) + 0.6)
        rp.setAlphaf(k * (1 - ph) * 0.8); c.drawCircle(p.x(), p.y(), 18 + rmax * ease_out_cubic(ph), rp)

def timeline_bar(c, a, a0, items, y=1250, x0=110, x1=970, alpha=1.0, dark=False):
    """Horizontal animated timeline: items = [(label, frac, t_in, highlight)]."""
    k = ramp(a, a0, a0 + 1.0) * alpha
    if k <= 0: return
    ink = (246, 236, 214) if dark else PAL['ink']
    p = skia.Paint(AntiAlias=True, Color=C(*ink), StrokeWidth=3); p.setAlphaf(k)
    c.drawLine(x0, y, lerp(x0, x1, ease_in_out_sine(ramp(a, a0, a0 + 1.2))), y, p)
    for lab, fr, t0, hl in items:
        kk = ramp(a, t0, t0 + 0.5) * alpha
        if kk <= 0: continue
        x = lerp(x0, x1, fr); col = (168, 60, 40) if hl else ink
        dp = skia.Paint(AntiAlias=True, Color=C(*col)); dp.setAlphaf(kk); c.drawCircle(x, y, 9 + 5 * ease_out_back(kk), dp)
        draw_text(c, lab, x, y - 30, font(SERIF, 40), C(*col), alpha=kk, reveal=kk, halo=None if dark else C(*PAL['paper'], 200), halo_w=6)

def map_label_dark_bg(c, x, y, text, size=40, alpha=1.0):
    draw_text(c, text, x, y, font(SERIF, size), C(246, 236, 214), alpha=alpha)

# ==================================================================== chapter scenes (a = narration seconds)
class Sc:
    def __init__(self, a0, a1, fn, trans='fade', td=0.8):
        self.a0, self.a1, self.fn, self.trans, self.td = a0, a1, fn, trans, td

# --- 1. opening hook + Commonwealth (existing, clocked by film time)
def sc_open(c, a): S.SCENES['S1'].render(c, a + 1.0)

# --- 2. three questions over the 1772 satirical print
def sc_questions(c, a):
    painting(c, a, 'europe_july1772.png', [(31.6, 0.50, 0.50, 1.05, 10, -2), (38.5, 0.42, 0.52, 1.6, 4, 0), (45.8, 0.62, 0.47, 1.75, 2, 1)],
             'British satirical print, 1772', title='“Picture of Europe for July 1772”', a_in=31.6)
    q = [('How had Poland–Lithuania', 'become so vulnerable?', wt('how', 32.4), wt('why', 35.7)),
         ('Why could it not stop', 'foreign interference?', wt('why', 35.7), wt('what', 39.9)),
         ('Why would rival powers', 'cooperate?', wt('what', 39.9), 45.9)]
    for l1, l2, t0, t1 in q:
        k = window(a, t0, t1, 0.4, 0.4)
        if k <= 0: continue
        draw_text(c, l1, W / 2, 250, font(SERIF, 64), C(246, 236, 214), alpha=k, reveal=ramp(a, t0, t0 + 0.8), stagger=0.6, rise=12,
                  shadow=(C(0, 0, 0, 180), 14, 0, 6))
        draw_text(c, l2, W / 2, 330, font(SERIF_I, 64), C(226, 196, 140), alpha=k, reveal=ramp(a, t0 + 0.25, t0 + 1.1), stagger=0.6, rise=12,
                  shadow=(C(0, 0, 0, 180), 14, 0, 6))
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

# --- 3. rewind: 1772 -> 1569
def sc_rewind(c, a):
    a0 = 45.75
    dark_backdrop(c, a, tone=(22, 16, 11), glow=(70, 50, 32), gy=0.45)
    k = ease_in_out_quint(ramp(a, a0 + 0.8, wt('century', 50.2) + 0.3, lambda v: v))
    year = int(round(lerp(1772, 1569, k)))
    # scrolling timeline ticks (motion blur by multiple faint copies)
    for sh in (0.0, 0.004, 0.008):
        kk = clamp(k - sh)
        off = kk * 2030 * 3.0
        for yr in range(1550, 1800, 10):
            x = W / 2 + (yr - 1772) * 3.0 + off
            if -50 < x < W + 50:
                big = yr % 50 == 0
                p = skia.Paint(AntiAlias=True, Color=C(214, 190, 146), StrokeWidth=2.5 if big else 1.2); p.setAlphaf((0.8 if big else 0.4) * (1 - sh * 80))
                c.drawLine(x, 1060, x, 1060 - (60 if big else 26), p)
                if big and sh == 0:
                    draw_text(c, str(yr), x, 1110, font(BODY, 30), C(214, 190, 146), alpha=0.7)
    p = skia.Paint(AntiAlias=True, Color=C(214, 190, 146), StrokeWidth=1.5); c.drawLine(0, 1060, W, 1060, p)
    pp = skia.Paint(AntiAlias=True, Color=C(200, 80, 50)); c.drawCircle(W / 2, 1060, 10, pp)
    draw_text(c, str(year), W / 2, 820, font(CAPS, 230), C(246, 236, 214), tracking=0.04, shadow=(C(0, 0, 0, 200), 18, 0, 8))
    draw_text(c, 'MORE THAN A CENTURY EARLIER', W / 2, 520, font(SC, 38), C(214, 190, 146), tracking=0.4, reveal=ramp(a, wt('back', 49.5), wt('back', 49.5) + 1.0),
              alpha=1 - ramp(a, 50.9, 51.4))
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.2)

# --- 4. Union of Lublin 1569
def sc_union(c, a):
    tU = wt('Lublin', 55.0)
    cam = cam_path([(51.0, Cam(260, 160, 0.55, tilt=14, oy=60), None), (58.0, Cam(250, 140, 0.60, tilt=8, oy=40), ease_in_out_sine),
                    (wt('enormous', 63.5), Cam(250, 140, 0.60, tilt=8, oy=40), None), (67.5, Cam(150, 200, 0.40, rot=-2, tilt=20, oy=60), ease_in_out_quint),
                    (78.6, Cam(170, 190, 0.44, rot=-1, tilt=16, oy=60), ease_in_out_sine)], a)
    cam = drift(cam, a, amp=4)
    bg(c); BASE.draw(c, cam)
    fill_territory(c, cam, layer_path('land', 1.5), PAL['neutral'], 0.22, inner_glow=0)
    for n in ('ottoman', 'sweden', 'hre_other', 'venice'):
        fill_territory(c, cam, layer_path(n), PAL['neutral'], 0.22, inner_glow=0.5, glow_w=8)
    # the two halves glide together and lock at "Union of Lublin"
    j = ease_out_cubic(ramp(a, 51.4, tU, lambda v: v))
    sep = (1 - j) * 140
    for lay, col, dx, lab in (('crown1569', PAL['plc'], -sep, 0), ('gdl1569', (226, 200, 140), sep, 1)):
        m = skia.Matrix(); m.setTranslate(dx, dx * 0.15)
        p = skia.Path(layer_path(lay, 0.4)); p.transform(m)
        if sep > 1:
            sp = skia.Path(p); sp.transform(cam.matrix())
            sh = skia.Paint(AntiAlias=True, Color=C(40, 24, 10), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)); sh.setAlphaf(0.4 * (1 - j))
            c.save(); c.translate(8, 18); c.drawPath(sp, sh); c.restore()
        fill_territory(c, cam, p, col, 0.68 * ramp(a, 51.2, 52.4), inner_glow=1.0, glow_w=14, blend=skia.BlendMode.kSrcOver if sep > 1 else skia.BlendMode.kMultiply,
                       hatch=0.25 if lab else 0)
        draw_border(c, cam, p, PAL['ink'], 2.2, alpha=ramp(a, 51.2, 52.4), glow=0.2)
    flash = window(a, tU - 0.05, tU + 0.9, 0.08, 0.8)
    if flash > 0:
        fp = skia.Path(layer_path('plc1569', 0.5)); fp.transform(cam.matrix())
        g = skia.Paint(AntiAlias=True, Color=C(255, 236, 190), Style=skia.Paint.kStroke_Style, StrokeWidth=10, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        g.setAlphaf(flash); c.drawPath(fp, g)
    draw_rivers(c, cam, alpha=0.5, flow_t=a, zoom_w=1.0)
    horizon_haze(c, cam)
    kicker(c, a, tU - 0.6, 'THE UNION OF LUBLIN', '1569', 'one Commonwealth from two states', y=330, size=120, a1=66.8)
    world_city(c, cam, 'Lublin_c', ramp(a, tU, tU + 0.8), label=False, pulse=ramp(a, tU, tU + 1.6, lambda v: v))
    pl = cam.to_screen(*city('Lublin_c'))
    draw_text(c, 'Lublin', pl.x() + 18, pl.y() - 12, font(SERIF, 34), C(*PAL['ink']), align='left', halo=C(*PAL['paper'], 220), halo_w=6,
              reveal=ramp(a, tU + 0.2, tU + 1.0), alpha=1 - ramp(a, 66, 67))
    t1 = wt('Kingdom', 59.0); t2 = wt('Grand', 59.8)
    world_label(c, cam, -60, -170, 'KINGDOM OF POLAND', 38, ramp(a, t1, t1 + 1.2) * (1 - ramp(a, 77, 78.4)), tracking=0.2, color=(92, 66, 34))
    world_label(c, cam, 420, 360, 'GRAND DUCHY', 36, ramp(a, t2, t2 + 1.2) * (1 - ramp(a, 77, 78.4)), tracking=0.2, color=(92, 66, 34))
    world_label(c, cam, 420, 312, 'OF LITHUANIA', 36, ramp(a, t2 + 0.2, t2 + 1.4) * (1 - ramp(a, 77, 78.4)), tracking=0.2, color=(92, 66, 34))
    chips(c, a, [('one elected king', wt('elected', 60.8)), ('one parliament', wt('parliament', 61.9))], y=1240, alpha=1 - ramp(a, 66.2, 67.0))
    # population: words appear as the narrator names them
    pa = 1 - ramp(a, 77.6, 78.4)
    chips(c, a, [('Poles', wt('Poles', 68.6)), ('Lithuanians', wt('Lithuanians', 69.3)), ('Ruthenians', wt('Ruthenians', 70.3)),
                 ('Jews', wt('Jews', 71.2)), ('Germans', wt('Germans', 71.8)), ('and many others', wt('many', 72.6))], y=1170, alpha=pa, size=38)
    FIN.apply(c, a + 200, cam)

# --- 5. political system: election, Sejm, liberum veto
def sc_election(c, a):
    painting(c, a, 'norblin_election.jpg', [(78.3, 0.50, 0.50, 1.25, 8, -1), (86.6, 0.55, 0.55, 1.9, 2, 0)],
             'Attributed to Jean-Pierre Norblin · c. 1790 · Wawel Castle', title='The election field at Wola (election of 1697)', a_in=78.3)
    kicker(c, a, wt('king', 82.5), 'AN ELECTED MONARCHY', 'The king was elected', 'by the nobility', y=300, size=72, dark=True)
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

def sc_sejm(c, a):
    painting(c, a, 'sejm_1698.png', [(86.2, 0.5, 0.48, 1.0, 6, 0), (97.8, 0.5, 0.42, 1.35, 2, 0)],
             'English engraving, 1698 · National Library of Poland', title='The Sejm in session', a_in=86.2)
    kicker(c, a, 86.4, 'THE SEJM', 'National parliament', None, y=300, size=72, dark=True)
    chips(c, a, [('noble privileges', wt('privileges', 89.6)), ('“Golden Liberty”', wt('freedoms', 91.3))], y=1210, dark=True)
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

_SEATS = None
def seats():
    global _SEATS
    if _SEATS is None:
        out = []; rng = np.random.default_rng(3)
        for r, n in enumerate((14, 18, 22, 26, 30)):
            R = 230 + r * 62
            for i in range(n):
                th = math.pi * (0.06 + 0.88 * i / (n - 1))
                out.append((W / 2 - R * math.cos(th), 1020 - R * math.sin(th), rng.random()))
        _SEATS = out
    return _SEATS

def sc_veto(c, a):
    tV = wt('liberum', 99.6); tD = wt('single', 102.4); tE = wt('end', 107.5)
    bg(c)
    c.drawColor(C(236, 228, 210))
    sh = skia.GradientShader.MakeRadial((W / 2, 760), 900, [C(250, 244, 230), C(226, 214, 190)])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))
    kicker(c, a, tV - 0.3, 'ONE VOICE AGAINST ALL', 'Liberum veto', '“Nie pozwalam!” – “I do not allow!”', y=300, size=96)
    st = seats(); veto_i = 47
    dis = ramp(a, tE - 0.4, tE + 1.4, ease_in_out_sine)
    for i, (x, y, r) in enumerate(st):
        appear = ramp(a, 97.6 + r * 1.2, 98.4 + r * 1.2)
        if appear <= 0: continue
        vx, vy = x, y
        if dis > 0 and i != veto_i:
            ang = math.atan2(y - 1020, x - W / 2) + (r - 0.5) * 0.8
            vx += math.cos(ang) * 260 * dis * (0.5 + r); vy += math.sin(ang) * 260 * dis * (0.5 + r)
        is_v = i == veto_i and a > tD
        col = (168, 50, 34) if is_v else (78, 60, 40)
        p = skia.Paint(AntiAlias=True, Color=C(*col)); p.setAlphaf(appear * (1 - 0.85 * dis * (i != veto_i)))
        c.drawCircle(vx, vy, 15 if is_v else 12, p)
        if is_v:
            for kk in range(2):
                ph = ((a - tD) * 0.8 + kk * 0.5) % 1
                rp = skia.Paint(AntiAlias=True, Color=C(*col), Style=skia.Paint.kStroke_Style, StrokeWidth=3); rp.setAlphaf((1 - ph) * 0.9)
                c.drawCircle(vx, vy, 18 + 70 * ph, rp)
    # throne / marshal's table
    tp = skia.Paint(AntiAlias=True, Color=C(*PAL['gold'])); c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(W / 2 - 70, 990, W / 2 + 70, 1030), 6, 6), tp)
    # the resolution bar fills… and breaks
    fill = ramp(a, 98.6, tD, lambda v: v)
    bx0, bx1, by = 190, 890, 1070
    pb = skia.Paint(AntiAlias=True, Color=C(*PAL['ink']), Style=skia.Paint.kStroke_Style, StrokeWidth=2); c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx0, by, bx1, by + 36), 8, 8), pb)
    brk = ramp(a, tD + 0.2, tD + 0.6)
    fc = tuple(int(lerp(p, q, brk)) for p, q in zip((120, 140, 90), (168, 50, 34)))
    pf = skia.Paint(AntiAlias=True, Color=C(*fc)); c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(bx0 + 4, by + 4, bx0 + 4 + (bx1 - bx0 - 8) * fill * (1 - 0.5 * brk), by + 32), 6, 6), pf)
    draw_text(c, 'Resolution' if brk < 0.5 else 'Session dissolved', W / 2, by + 86, font(SC, 36), C(*fc), tracking=0.25)
    chips(c, a, [('sessions disrupted', wt('disrupted', 116.4)), ('reforms blocked', wt('reforms', 117.1)), ('decisions delayed', wt('delayed', 118.8))], y=1240)
    FIN.apply(c, a + 300, None, vignette=0.5, grain=1.0, light=0.6, dust=0.6)

# --- 6. foreign influence
def sc_influence(c, a):
    cam = drift(cam_path([(119.6, Cam(140, 300, 0.50, tilt=10, oy=40), None), (138.6, Cam(200, 330, 0.56, tilt=8, oy=40), ease_in_out_sine)], a), a, amp=4)
    rus = ramp(a, wt('Russia', 128.6), wt('Russia', 128.6) + 1.2)
    st = base_state(powsolid=0.3 + 0.4 * rus, powR=0.8 + 0.2 * rus, powP=0.8 - 0.3 * rus, powA=0.8 - 0.3 * rus, rivers=0.5)
    map_frame(c, a, cam, st)
    w = city('Warsaw')
    for src, col, t0, d in (('Berlin', PAL['prussia'], 120.6, (0, 1)), ('Vienna', PAL['austria'], 121.0, (0, -1)), ('St Petersburg', PAL['russia'], 121.4, (1, 0))):
        s_ = city(src); mid = ((s_[0] + w[0]) / 2 + 120 * d[1], (s_[1] + w[1]) / 2 + 120 * d[0])
        fade_o = 1 - 0.7 * rus if src != 'St Petersburg' else 1
        arrow(c, cam, [s_, mid, (w[0] + (s_[0] - w[0]) * 0.08, w[1] + (s_[1] - w[1]) * 0.08)], ramp(a, t0, t0 + 1.8, ease_in_out_sine),
              tuple(int(v * .8) for v in col), width=6 + 5 * rus * (src == 'St Petersburg'), alpha=fade_o, dashed=True, a=a)
        world_city(c, cam, src, ramp(a, t0 - 0.3, t0 + 0.5), size=30, dx=16, align='left', color=(70, 50, 30))
    world_city(c, cam, 'Warsaw', ramp(a, 120.2, 121.0), capital=True, size=34, pulse=ramp(a, 121.5, 123.0, lambda v: v))
    kicker(c, a, 120.3, 'THE 18TH CENTURY', 'Foreign interference', None, y=300, size=80, a1=128.4)
    kicker(c, a, wt('Russia', 128.6), 'ABOVE ALL', 'Russian influence', 'armies and diplomats', y=300, size=80, a1=138.4)
    FIN.apply(c, a + 400, cam)

# --- 7. succession: Augustus III, election 1764, Stanisław August
def sc_augustus(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    portrait(c, 'augustus3', a - 138.2, 6.2, alpha=1.0, exit_t=ramp(a, 144.0, 145.0))
    kicker(c, a, 138.6, None, '1763', None, y=170, size=64, dark=True)
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)

def sc_bellotto(c, a):
    painting(c, a, 'bellotto_election.jpg', [(144.4, 0.5, 0.5, 1.0, 8, -1), (148.6, 0.52, 0.55, 1.7, 3, 0), (152.8, 0.40, 0.58, 2.3, 1, 0)],
             'Bernardo Bellotto · 1778 · Royal Castle, Warsaw', title='The election of Stanisław August, 1764', a_in=144.4)
    kicker(c, a, wt('support', 147.4), 'WITH RUSSIAN SUPPORT', 'Elected king, 1764', None, y=300, size=76, dark=True)
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

def sc_stanislaw(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    portrait(c, 'stanislaw', a - 152.6, 15.0)
    chips(c, a, [('administration', wt('administrative', 156.4)), ('economy', wt('economic', 157.5)), ('education', wt('educational', 158.6))],
          y=200, dark=True, alpha=1 - ramp(a, 167.2, 168.0), size=36)
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)

# --- 8. Catherine & Frederick
def sc_cath_fred(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    tf = 173.55
    if a < tf + 1.0:
        x = ramp(a, tf - 0.3, tf + 0.9); portrait(c, 'catherine', a - 167.9, tf - 167.9, alpha=1 - x, exit_t=x)
    if a > tf - 0.3:
        portrait(c, 'frederick', a - tf + 0.3, 8.5, alpha=ramp(a, tf - 0.3, tf + 0.6))
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)

# --- 9. 1767: Repnin
def sc_1767(c, a):
    cam = drift(cam_path([(181.6, Cam(60, 80, 0.9, tilt=12, oy=40), None), (194.4, Cam(-30, 40, 1.35, tilt=8, oy=20), ease_in_out_sine)], a), a, amp=4)
    st = base_state(powsolid=0.3, rivers=0.6)
    map_frame(c, a, cam, st)
    w = city('Warsaw')
    for i, src in enumerate(((500, 380), (560, 160), (420, 520))):
        arrow(c, cam, [src, ((src[0] + w[0]) / 2, (src[1] + w[1]) / 2 + 40), (w[0] + 25, w[1] + 8)], ramp(a, 183.0 + i * 0.4, 185.4 + i * 0.4, ease_in_out_sine),
              tuple(int(v * .8) for v in PAL['russia']), width=8, dashed=False, a=a)
    world_city(c, cam, 'Warsaw', ramp(a, 182.2, 183.0), capital=True, size=36, pulse=ramp(a, 184.4, 186.0, lambda v: v))
    kicker(c, a, wt('1767', 182.2), 'RUSSIAN PRESSURE ON THE SEJM', '1767', None, y=330, size=130)
    chips(c, a, [('rights for religious dissenters', wt('dissenters', 190.0)), ('the old system preserved', wt('maintained', 191.0))], y=1220)
    FIN.apply(c, a + 500, cam)

def sc_repnin(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    portrait(c, 'repnin', a - 193.7, 12.0)
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)

# --- 10. Confederation of Bar
def sc_bar(c, a):
    cam = drift(cam_path([(205.6, Cam(200, -150, 0.95, tilt=14, oy=40), None), (218.0, Cam(260, -220, 1.25, tilt=10, oy=20), ease_in_out_sine),
                          (224.0, Cam(150, 0, 0.66, tilt=6, oy=40), ease_in_out_quint), (238.4, Cam(180, 20, 0.70, tilt=6, oy=40), ease_in_out_sine)], a), a, amp=4)
    st = base_state(powsolid=0.2, rivers=0.6)
    map_frame(c, a, cam, st)
    ripples(c, cam, *city('Bar'), a, 207.6, 231.0, (150, 40, 30), n=3, rmax=320)
    world_city(c, cam, 'Bar', ramp(a, 207.0, 208.0), size=40, pulse=ramp(a, 208.0, 209.6, lambda v: v), color=(110, 30, 20))
    kicker(c, a, wt('1768', 206.6), 'THE CONFEDERATION OF BAR', '1768', None, y=330, size=130, a1=223.4)
    chips(c, a, [('the Catholic faith', wt('Catholic', 214.6)), ('traditional liberties', wt('traditional', 216.0)), ('independence', wt('independence', 217.6))],
          y=1220, alpha=1 - ramp(a, 222.6, 223.4))
    tl = wt('War', 225.5)
    timeline_bar(c, a, tl - 0.4, [('1768', 0.0, tl - 0.2, False), ('1772', 1.0, wt('1772', 228.4), True)], y=330, x0=170, x1=910,
                 alpha=1 - ramp(a, 237.6, 238.4))
    draw_text(c, 'War of the Bar Confederation', W / 2, 420, font(SERIF_I, 44), C(*PAL['ink']), reveal=ramp(a, tl, tl + 1.2), alpha=1 - ramp(a, 237.6, 238.4),
              halo=C(*PAL['paper'], 200), halo_w=7)
    tr = wt('intervened', 233.6)
    for i, (src, dst) in enumerate((((720, 420), (330, 230)), ((760, 120), (300, 20)), ((700, -150), (300, -220)), ((640, 300), (60, 120)))):
        arrow(c, cam, [src, ((src[0] + dst[0]) / 2, (src[1] + dst[1]) / 2 + 50), dst], ramp(a, tr - 0.8 + i * 0.3, tr + 1.4 + i * 0.3, ease_in_out_sine),
              tuple(int(v * .78) for v in PAL['russia']), width=8, a=a)
    FIN.apply(c, a + 600, cam)

# --- 11. Russo-Turkish war
def sc_turkey(c, a):
    cam = drift(cam_path([(237.6, Cam(350, -350, 0.62, tilt=16, oy=40), None), (248.8, Cam(330, -460, 0.80, tilt=12, oy=20), ease_in_out_sine)], a), a, amp=4)
    st = base_state(powsolid=0.4, rivers=0.6)
    map_frame(c, a, cam, st, haze=True)
    ot = ramp(a, 238.4, 239.6)
    fill_territory(c, cam, layer_path('ottoman'), (120, 128, 96), 0.2 * ot, inner_glow=1.6, glow_w=24)
    world_label(c, cam, 380, -900, 'OTTOMAN EMPIRE', 46, ramp(a, 239.0, 240.4), tracking=0.22, color=(60, 66, 44))
    kicker(c, a, 238.4, 'AT THE SAME TIME', 'Russo-Turkish War', '1768 – 1774', y=330, size=86)
    for i, (src, dst) in enumerate((((700, -250), (380, -620)), ((820, -330), (560, -640)))):
        arrow(c, cam, [src, ((src[0] + dst[0]) / 2 + 40, (src[1] + dst[1]) / 2), dst], ramp(a, 240.4 + i * 0.4, 243.0 + i * 0.4, ease_in_out_sine),
              tuple(int(v * .78) for v in PAL['russia']), width=10, a=a)
    tv = wt('victories', 245.4)
    world_city(c, cam, 'Larga', ramp(a, tv - 0.3, tv + 0.5), size=32, dx=-16, align='right', sub='1770', color=(110, 30, 20), pulse=ramp(a, tv, tv + 1.5, lambda v: v))
    world_city(c, cam, 'Kagul', ramp(a, tv, tv + 0.8), size=32, dx=16, sub='1770', color=(110, 30, 20), pulse=ramp(a, tv + 0.3, tv + 1.8, lambda v: v))
    FIN.apply(c, a + 700, cam)

# --- 12. Maria Theresa + the three powers
def sc_maria(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    tt = 257.2
    if a < tt + 1.2:
        x = ramp(a, tt - 0.2, tt + 1.0); portrait(c, 'maria', a - 248.2, tt - 248.2, alpha=1 - x, exit_t=x)
    if a > tt - 0.2:
        triptych(c, a - tt + 0.2, focus='frederick', focus_t=ramp(a, wt('Frederick', 259.4), wt('Frederick', 259.4) + 0.7))
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.4)

# --- 13. Frederick's plan
def sc_plan(c, a):
    cam = drift(cam_path([(260.6, Cam(150, -150, 0.42, tilt=16, oy=60), None), (265.6, Cam(150, -150, 0.45, tilt=14, oy=60), ease_in_out_sine),
                          (268.0, Cam(-330, 180, 1.05, tilt=10, oy=-40), ease_in_out_quint), (281.6, Cam(-300, 190, 1.1, tilt=8, oy=-40), ease_in_out_sine),
                          (284.0, Cam(185, 180, 0.66, tilt=4, oy=40), ease_in_out_quint), (288.0, Cam(185, 180, 0.68, tilt=4, oy=40), ease_in_out_sine)], a), a, amp=4)
    pr = window(a, 266.2, 282.2, 1.0, 1.0)
    st = base_state(powsolid=0.3 + 0.5 * pr, powP=0.8 + 0.2 * pr, powR=0.8 - 0.3 * pr, powA=0.8 - 0.3 * pr, rivers=0.6)
    map_frame(c, a, cam, st)
    # Austria vs Russia: a war Frederick wanted to avoid
    cf = window(a, 261.4, 266.6, 0.6, 0.8)
    if cf > 0:
        arrow(c, cam, [city('Vienna'), (100, -520), (330, -560)], ramp(a, 261.6, 263.4, ease_in_out_sine), tuple(int(v * .8) for v in PAL['austria']), width=9, alpha=cf)
        arrow(c, cam, [(820, -250), (650, -480), (420, -560)], ramp(a, 261.9, 263.7, ease_in_out_sine), tuple(int(v * .8) for v in PAL['russia']), width=9, alpha=cf)
        p = cam.to_screen(375, -560)
        for k in range(3):
            ph = ((a - 263.6) * 1.2 + k / 3) % 1
            rp = skia.Paint(AntiAlias=True, Color=C(200, 60, 30), Style=skia.Paint.kStroke_Style, StrokeWidth=3); rp.setAlphaf(cf * (1 - ph) * (a > 263.6))
            c.drawCircle(p.x(), p.y(), 14 + 80 * ph, rp)
        draw_text(c, 'a wider war?', p.x(), p.y() + 90, font(SERIF_I, 44), C(120, 30, 20), alpha=cf * ramp(a, 263.8, 264.6), halo=C(*PAL['paper'], 220), halo_w=7)
    # the gap: Royal Prussia separates Brandenburg from East Prussia
    gp = window(a, 266.6, 282.0, 0.8, 0.8)
    if gp > 0:
        world_label(c, cam, -600, 0, 'BRANDENBURG', 42, ramp(a, wt('Brandenburg', 267.8), wt('Brandenburg', 267.8) + 1.0) * gp, tracking=0.2, color=(40, 56, 78))
        world_label(c, cam, 110, 250, 'EAST PRUSSIA', 42, ramp(a, wt('Prussia', 271.4), wt('Prussia', 271.4) + 1.0) * gp, tracking=0.2, color=(40, 56, 78))
        rp = skia.Path(layer_path('royal_prussia', 0.3)); rp.addPath(layer_path('netze', 0.3))
        pul = 0.5 + 0.5 * math.sin(a * 3.2)
        stroke_world(c, cam, rp, (150, 50, 30), 3.2, alpha=gp * ramp(a, 268.8, 269.8) * (0.55 + 0.45 * pul), dash=[12, 8], phase=-a * 30)
        world_label(c, cam, -260, 160, 'ROYAL PRUSSIA', 38, ramp(a, 269.4, 270.6) * gp, tracking=0.18, color=(120, 40, 24), sub='still Polish', sub_size=28)
        arrow(c, cam, [city('Berlin'), (-420, 230), (-250, 280), city('Königsberg')], ramp(a, 270.0, 272.4, ease_in_out_sine), (70, 96, 128), width=7, alpha=gp, dashed=True, a=a)
    inset_portrait(c, a, 'henry', 272.0, 281.6, x=620, y=330, w=380, h=460)
    # the idea becomes a plan: the three future shares appear as dotted outlines
    fs = ramp(a, wt('partitioning', 283.0), wt('partitioning', 283.0) + 1.2)
    if fs > 0:
        for lay, col in (('gain_P', 'prussia'), ('gain_R', 'russia'), ('gain_A', 'austria')):
            stroke_world(c, cam, layer_path(lay, 0.5), tuple(int(x * .65) for x in PAL[col]), 3.0, alpha=fs, dash=[3, 8], phase=-a * 16)
    FIN.apply(c, a + 800, cam)

# --- 14. agreement & occupation
def sc_occupy(c, a):
    cam = drift(cam_path([(287.4, Cam(185, 180, 0.68, tilt=4, oy=40), None), (304.8, Cam(175, 175, 0.72, tilt=8, oy=40), ease_in_out_sine)], a), a, amp=4)
    occ = ramp(a, 297.6, 301.5, ease_in_out_sine)
    st = base_state(powsolid=0.2, gainP1=occ, gainP2=occ, gainP3=occ, gainR=occ, gainA=occ, hatch=1.0, rivers=0.6)
    for k in ('P1', 'P2', 'P3', 'R', 'A'): st['gainA' + k] = 0.55
    map_frame(c, a, cam, st)
    fs = 1 - occ
    for lay, col in (('gain_P', 'prussia'), ('gain_R', 'russia'), ('gain_A', 'austria')):
        stroke_world(c, cam, layer_path(lay, 0.5), tuple(int(x * .65) for x in PAL[col]), 3.0, alpha=fs * ramp(a, 287.4, 288.0), dash=[3, 8], phase=-a * 16)
    kicker(c, a, wt('1772', 288.6), 'THE THREE POWERS AGREE', '1772', None, y=330, size=130, a1=297.2)
    chips(c, a, [('Russia', wt('Russia', 292.0)), ('Prussia', wt('Prussia', 292.6)), ('Austria', wt('Austria', 293.2))], y=1225, alpha=1 - ramp(a, 296.8, 297.4))
    inset_portrait(c, a, 'kaunitz', 289.2, 296.8, x=600, y=470, w=400, h=480)
    ta = wt('armies', 297.6)
    arrow(c, cam, [(-480, 330), (-380, 260), (-290, 200)], ramp(a, ta, ta + 2.0, ease_in_out_sine), tuple(int(v * .7) for v in PAL['prussia']), width=10, a=a)
    arrow(c, cam, [(-20, 330), (-90, 260), (-190, 210)], ramp(a, ta + 0.2, ta + 2.2, ease_in_out_sine), tuple(int(v * .7) for v in PAL['prussia']), width=10, a=a)
    arrow(c, cam, [(820, 420), (680, 380), (520, 330)], ramp(a, ta + 0.4, ta + 2.4, ease_in_out_sine), tuple(int(v * .7) for v in PAL['russia']), width=12, a=a)
    arrow(c, cam, [(820, 120), (700, 140), (570, 170)], ramp(a, ta + 0.6, ta + 2.6, ease_in_out_sine), tuple(int(v * .7) for v in PAL['russia']), width=12, a=a)
    arrow(c, cam, [(-60, -560), (-20, -420), (40, -300)], ramp(a, ta + 0.8, ta + 2.8, ease_in_out_sine), tuple(int(v * .7) for v in PAL['austria']), width=12, a=a)
    arrow(c, cam, [(250, -560), (220, -440), (180, -310)], ramp(a, ta + 1.0, ta + 3.0, ease_in_out_sine), tuple(int(v * .7) for v in PAL['austria']), width=12, a=a)
    kicker(c, a, ta, 'OCCUPATION', 'Armies move in', None, y=330, size=86, a1=305.0)
    FIN.apply(c, a + 900, cam)

# --- 15-17. existing preview scenes
def sc_doc(c, a): S.SCENES['S3'].render(c, a - 304.30 + 0.6)
def sc_partition(c, a): S.SCENES['S4'].render(c, a - 315.35)
def sc_beforeafter(c, a): S.SCENES['S5'].render(c, a - 372.25)

# --- 18. the king, the Partition Sejm, Rejtan, ratification
def sc_king(c, a):
    dark_backdrop(c, a, gx=0.5, gy=0.32)
    portrait(c, 'stanislaw_dark', a - 387.9, 8.5)
    FIN.apply(c, a, None, vignette=0.8, grain=0.9, light=0.3, dust=1.2)

def sc_demand(c, a):
    dark_backdrop(c, a, tone=(20, 15, 11), glow=(66, 48, 30), gy=0.45)
    t0 = 396.3
    cx, cy = W / 2, 820
    k = ease_out_back(ramp(a, t0, t0 + 0.8, lambda v: v))
    sp = skia.Paint(AntiAlias=True, Color=C(*PAL['plc'])); sp.setAlphaf(clamp(k))
    c.drawCircle(cx, cy, 120 * clamp(k), sp)
    draw_text(c, 'SEJM', cx, cy + 22, font(CAPS_B, 60), C(40, 28, 16), alpha=clamp(k))
    for i, (col, lab) in enumerate((('prussia', 'Prussia'), ('russia', 'Russia'), ('austria', 'Austria'))):
        ang = -math.pi / 2 + (i - 1) * 2.0
        px, py = cx + math.cos(ang) * 360, cy + math.sin(ang) * 360 + 60
        kk = ramp(a, t0 + 0.4 + i * 0.25, t0 + 1.2 + i * 0.25)
        pp = skia.Paint(AntiAlias=True, Color=C(*PAL[col])); pp.setAlphaf(kk); c.drawCircle(px, py, 70 * kk, pp)
        draw_text(c, lab, px, py + 120, font(SERIF, 40), C(246, 236, 214), alpha=kk)
        lt = ramp(a, t0 + 1.0 + i * 0.25, t0 + 2.4 + i * 0.25, ease_in_out_sine)
        lp = skia.Paint(AntiAlias=True, Color=C(*PAL[col]), StrokeWidth=5, PathEffect=skia.DashPathEffect.Make([14, 9], -a * 40)); lp.setAlphaf(kk)
        c.drawLine(px + (cx - px) * 0.2, py + (cy - py) * 0.2, lerp(px, cx, 0.2 + 0.5 * lt), lerp(py, cy, 0.2 + 0.5 * lt), lp)
    kicker(c, a, t0, 'THE PARTITIONING POWERS DEMAND', 'Formal approval', None, y=330, size=80, dark=True)
    FIN.apply(c, a, None, vignette=0.75, grain=0.9, light=0.4, dust=1.2)

def sc_rejtan(c, a):
    tR = wt('Rejtan', 413.6)
    painting(c, a, 'matejko_reytan.jpg', [(401.6, 0.45, 0.50, 1.05, 8, -1), (409.0, 0.40, 0.48, 1.9, 3, 0), (tR, 0.80, 0.62, 2.6, 1, 0), (420.6, 0.84, 0.64, 2.9, 0, 0)],
             'Jan Matejko · 1866 · Royal Castle, Warsaw — painted nearly a century later', title='Rejtan – The Fall of Poland', a_in=401.6)
    kicker(c, a, wt('1773', 403.6), 'WARSAW', 'The Partition Sejm, 1773', None, y=300, size=76, dark=True, a1=tR - 0.2)
    kicker(c, a, tR, 'AN ACT OF PROTEST', 'Tadeusz Rejtan', None, y=300, size=86, dark=True)
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

def sc_ratify(c, a):
    cam = drift(cam_path([(419.6, Cam(185, 160, 0.66, tilt=6, oy=40), None), (430.8, Cam(175, 150, 0.72, tilt=4, oy=40), ease_in_out_sine)], a), a, amp=4)
    ink = ramp(a, wt('ratified', 422.6), wt('ratified', 422.6) + 2.4, ease_in_out_sine)
    st = post_state(post_border_t=1, post_border=1, ghost=0.8)
    map_frame(c, a, cam, st)
    if ink > 0:
        draw_border(c, cam, layer_path('plc_rem', 0.3), (40, 26, 14), 5.0, t=ink, alpha=1.0, glow=0.5)
    kicker(c, a, 420.2, 'THE SEJM RATIFIES THE TREATIES', '30 September 1773', None, y=330, size=86)
    seal = ease_out_back(ramp(a, 426.0, 426.7, lambda v: v), 1.6)
    if seal > 0:
        x, y = W / 2, 1180
        sp = skia.Paint(AntiAlias=True, Color=C(150, 36, 26)); sp.setAlphaf(clamp(seal))
        c.save(); c.translate(x, y); c.scale(lerp(1.6, 1.0, clamp(seal)), lerp(1.6, 1.0, clamp(seal)))
        sh = skia.Paint(AntiAlias=True, Color=C(0, 0, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12)); sh.setAlphaf(0.35 * clamp(seal))
        c.drawCircle(4, 10, 92, sh); c.drawCircle(0, 0, 92, sp)
        rp = skia.Paint(AntiAlias=True, Color=C(220, 140, 110), Style=skia.Paint.kStroke_Style, StrokeWidth=2); rp.setAlphaf(clamp(seal)); c.drawCircle(0, 0, 76, rp)
        draw_text(c, 'RATIFIED', 0, 12, font(CAPS_B, 32), C(250, 220, 200), tracking=0.1, alpha=clamp(seal))
        c.restore()
    FIN.apply(c, a + 1000, cam)

# --- 19. consequences for the annexed lands
def sc_people(c, a):
    tb = wt('borders', 448.9)
    cam = drift(cam_path([(430.4, Cam(185, 170, 0.68, tilt=6, oy=40), None), (444.6, Cam(150, 120, 0.74, tilt=6, oy=40), ease_in_out_sine),
                          (446.8, Cam(-140, -210, 3.0, tilt=12, oy=-60), ease_in_out_quint), (450.0, Cam(-145, -215, 3.2, tilt=10, oy=-60), ease_in_out_sine),
                          (452.2, Cam(-250, 160, 1.15, tilt=8, oy=-40), ease_in_out_quint), (457.6, Cam(-250, 160, 1.2, tilt=8, oy=-40), ease_in_out_sine),
                          (459.6, Cam(80, -270, 1.4, tilt=10, oy=-80), ease_in_out_quint), (463.0, Cam(70, -270, 1.45, tilt=10, oy=-80), ease_in_out_sine),
                          (465.2, Cam(470, 300, 1.3, tilt=10, oy=-80), ease_in_out_quint), (470.6, Cam(480, 300, 1.35, tilt=10, oy=-80), ease_in_out_sine)], a), a, amp=4)
    st = post_state(ghost=0.35, rv_hl=['Vistula'], rv_hl_a=window(a, 446.4, 450.6, 0.6, 0.6))
    map_frame(c, a, cam, st)
    chips(c, a, [('new rulers', wt('rulers', 436.6)), ('new administrations', wt('administrations', 437.6)), ('new legal systems', wt('legal', 438.8))],
          y=1200, alpha=1 - ramp(a, 439.9, 440.4))
    chips(c, a, [('taxes', wt('Taxes', 440.4)), ('military service', wt('military', 441.2)), ('institutions', wt('institutions', 443.2))],
          y=1200, alpha=1 - ramp(a, 444.4, 444.9))
    bd = window(a, 446.4, 451.2, 0.6, 0.6)
    if bd > 0:
        world_city(c, cam, 'Kraków', bd, size=40, dx=-18, dy=-20, align='right', sub='remained Polish')
        world_label(c, cam, -125, -245, 'Austrian from 1772', 34, bd, fontname=SERIF_I, tracking=0.02, color=(102, 66, 16))
        world_label(c, cam, -160, -192, 'Vistula', 32, bd, fontname=SERIF_I, tracking=0.1, color=(40, 80, 104))
    tP = wt('Prussian', 450.6); tA = wt('Austrian', 458.2); tRu = wt('Russian', 463.6)
    world_label(c, cam, -280, 230, 'WEST PRUSSIA', 50, window(a, tP + 0.6, 458.4, 1.0, 0.6), tracking=0.22, color=(40, 56, 78), sub='Prussian province from 1773', sub_size=30)
    world_label(c, cam, 110, -300, 'GALICIA AND LODOMERIA', 44, window(a, tA + 0.8, 464.4, 1.0, 0.6), tracking=0.16, color=(102, 66, 16), sub='Habsburg kingdom from 1772', sub_size=30)
    world_label(c, cam, 520, 400, 'PSKOV AND MOGILEV', 42, window(a, tRu + 0.8, 470.6, 1.0, 0.01), tracking=0.16, color=(96, 40, 28))
    world_label(c, cam, 520, 355, 'GOVERNORATES', 42, window(a, tRu + 1.0, 470.6, 1.0, 0.01), tracking=0.16, color=(96, 40, 28), sub='Russian provinces from 1772', sub_size=30)
    kicker(c, a, 431.0, 'FOR THE PEOPLE OF THE ANNEXED LANDS', 'Immediate change', None, y=330, size=80, a1=444.8)
    FIN.apply(c, a + 1100, cam)

# --- 20. aftermath & warning
def sc_warning(c, a):
    cam = drift(cam_path([(470.0, Cam(480, 300, 1.35, tilt=10, oy=-80), None), (473.6, Cam(150, 120, 0.72, tilt=4, oy=40), ease_in_out_quint),
                          (493.8, Cam(130, 100, 0.80, tilt=4, oy=40), ease_in_out_sine)], a), a, amp=4)
    st = post_state(ghost=0.5, powsolid=0.2)
    map_frame(c, a, cam, st)
    rem = ramp(a, 474.2, 475.4)
    if rem > 0:
        stroke_world(c, cam, layer_path('plc_rem', 0.3), (255, 226, 160), 8, alpha=0.5 * rem * (0.6 + 0.4 * math.sin(a * 2.5)), glow=1.0)
    world_label(c, cam, 30, 60, 'POLISH–LITHUANIAN', 44, window(a, 474.4, 482.0, 1.0, 0.8), tracking=0.2)
    world_label(c, cam, 30, -12, 'COMMONWEALTH', 44, window(a, 474.6, 482.0, 1.0, 0.8), tracking=0.2)
    chips(c, a, [('fundamental reforms needed', wt('fundamental', 479.0))], y=1220, alpha=1 - ramp(a, 481.8, 482.4))
    tw = wt('warning', 484.4)
    kicker(c, a, wt('experience', 482.6), 'THE EXPERIENCE OF 1772', 'A warning', 'independence lost piece by piece', y=330, size=110)
    # echo of the opening: the lost pieces lift away again (piece by piece)
    if a > 488.5:
        for i, (lay, col, cut, t0) in enumerate(HOOK_PIECES):
            sep = ease_out_cubic(ramp(a, 489.6 + i * 0.5, 491.0 + i * 0.5, lambda v: v))
            if sep <= 0: continue
            cx_, cy_, d = S._centroid(lay)
            wm = skia.Matrix(); wm.setTranslate(d[0] * 45 * sep, d[1] * 45 * sep)
            p = skia.Path(layer_path(lay, 0.3)); p.transform(wm); sp_ = skia.Path(p); sp_.transform(cam.matrix())
            sh = skia.Paint(AntiAlias=True, Color=C(40, 24, 10), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)); sh.setAlphaf(0.4 * sep)
            c.save(); c.translate(10 * sep, 20 * sep); c.drawPath(sp_, sh); c.restore()
            fp = skia.Paint(AntiAlias=True, Color=C(*PAL[col])); fp.setAlphaf(0.85); c.drawPath(sp_, fp)
    FIN.apply(c, a + 1200, cam)

# --- 21. Constitution of 3 May 1791
def sc_constitution(c, a):
    painting(c, a, 'constitution_1791.jpg', [(493.2, 0.5, 0.5, 1.05, 8, -1), (500.0, 0.45, 0.45, 1.7, 3, 0), (507.6, 0.55, 0.42, 2.2, 1, 0)],
             'Kazimierz Wojniakowski · 1806 · National Museum, Warsaw', title='Passing of the Constitution of 3 May 1791', a_in=493.2)
    kicker(c, a, wt('3rd', 499.4) - 0.6, 'THE GREAT REFORM', '3 May 1791', 'the Constitution', y=300, size=96, dark=True)
    FIN.apply(c, a, None, vignette=0.7, grain=0.8, light=0.4, dust=1.0)

# --- 22. further partitions (timeline; no unverified 1793 geometry is drawn)
def sc_further(c, a):
    cam = drift(cam_path([(506.8, Cam(170, 150, 0.62, tilt=6, oy=40), None), (517.6, Cam(160, 140, 0.66, tilt=6, oy=40), ease_in_out_sine)], a), a, amp=4)
    t93 = wt('1793', 514.6); t95 = wt('1795', 515.8)
    st = post_state(ghost=0.4, powsolid=0.3 + 0.4 * ramp(a, 507.6, 509.0), powP=0.95, powR=0.95, powA=0.95)
    gone = ramp(a, t93, t93 + 0.6) * 0.45 + ramp(a, t95, t95 + 1.2) * 0.55
    st['plc'] = 1 - gone; st['courland'] = 1 - gone; st['post_border'] = 1 - gone
    map_frame(c, a, cam, st)
    for i, (src, col) in enumerate((('Berlin', 'prussia'), ('St Petersburg', 'russia'), ('Vienna', 'austria'))):
        s_ = city(src); w_ = city('Warsaw')
        arrow(c, cam, [s_, ((s_[0] + w_[0]) / 2, (s_[1] + w_[1]) / 2), (w_[0] + (s_[0] - w_[0]) * 0.15, w_[1] + (s_[1] - w_[1]) * 0.15)],
              ramp(a, 508.2 + i * 0.3, 510.4 + i * 0.3, ease_in_out_sine), tuple(int(v * .75) for v in PAL[col]), width=9, alpha=1 - ramp(a, 516.4, 517.2), a=a)
    timeline_bar(c, a, 512.4, [('1772', 0.0, 512.6, False), ('1793', 0.5, t93, True), ('1795', 1.0, t95, True)], y=340, x0=150, x1=930)
    draw_text(c, 'Second Partition', W * 0.5, 420, font(SERIF_I, 36), C(120, 30, 20), alpha=ramp(a, t93, t93 + 0.6) * (1 - ramp(a, t95 - 0.1, t95 + 0.3)),
              halo=C(*PAL['paper'], 200), halo_w=6)
    draw_text(c, 'Third Partition – the Commonwealth disappears from the map', W * 0.5, 420, font(SERIF_I, 34), C(120, 30, 20),
              alpha=ramp(a, t95 + 0.2, t95 + 0.9), halo=C(*PAL['paper'], 200), halo_w=6, reveal=ramp(a, t95 + 0.2, t95 + 1.4), stagger=0.4)
    FIN.apply(c, a + 1300, cam)

# --- 23. finale
def sc_final(c, a):
    cam = drift(cam_path([(517.0, Cam(160, 140, 0.66, tilt=6, oy=40), None), (529.0, Cam(150, 200, 0.42, rot=-2, tilt=20, oy=60), ease_in_out_sine)], a), a, amp=4)
    back = ramp(a, 517.4, 519.0)
    st = post_state(ghost=0.4 * back, powsolid=0.2)
    st['plc'] = back; st['courland'] = back; st['post_border'] = back
    map_frame(c, a, cam, st)
    kicker(c, a, wt('end', 521.6) - 1.6, 'NOT THE END', 'of Poland–Lithuania', None, y=330, size=84, a1=wt('beginning', 523.6))
    kicker(c, a, wt('beginning', 523.6), 'IT WAS THE BEGINNING', 'of the final struggle', 'for its survival', y=330, size=84)
    end = ramp(a, 526.2, 527.2)
    if end > 0:
        p = skia.Paint(Color=C(18, 13, 9)); p.setAlphaf(end * 0.9); c.drawRect(skia.Rect(0, 0, W, H), p)
        draw_text(c, 'THE FIRST PARTITION', W / 2, 840, font(CAPS_B, 74), C(246, 236, 214), tracking=0.1, alpha=end, reveal=end, stagger=0.8, rise=10)
        rule(c, W / 2, 884, 520, ramp(a, 526.6, 527.6), color=(190, 152, 90))
        draw_text(c, 'of Poland–Lithuania · 1772', W / 2, 950, font(SERIF_I, 50), C(226, 206, 170), alpha=ramp(a, 526.8, 527.6))
        cr = ramp(a, 527.2, 528.0)
        draw_text(c, 'Maps: OpenHistoricalMap (CC0), RISTAT 1897 districts (CC0), Natural Earth', W / 2, 1180, font(BODY, 24), C(190, 174, 146), alpha=cr)
        draw_text(c, 'Paintings and prints: public-domain originals via Wikimedia Commons', W / 2, 1214, font(BODY, 24), C(190, 174, 146), alpha=cr)
    FIN.apply(c, a + 1400, cam, vignette=0.6)

# ==================================================================== timeline
SCENES = [
    Sc(-1.0, 32.15, sc_open),
    Sc(32.15, 45.75, sc_questions, 'dip', 0.9),
    Sc(45.75, 51.15, sc_rewind, 'fade', 0.6),
    Sc(51.15, 78.35, sc_union, 'paper', 0.9),
    Sc(78.35, 86.35, sc_election, 'dip', 0.9),
    Sc(86.35, 97.70, sc_sejm, 'fade', 0.8),
    Sc(97.70, 119.95, sc_veto, 'paper', 0.8),
    Sc(119.95, 138.30, sc_influence, 'paper', 0.8),
    Sc(138.30, 144.50, sc_augustus, 'dip', 0.9),
    Sc(144.50, 152.70, sc_bellotto, 'fade', 0.8),
    Sc(152.70, 168.00, sc_stanislaw, 'fade', 0.8),
    Sc(168.00, 181.80, sc_cath_fred, 'fade', 0.8),
    Sc(181.80, 193.80, sc_1767, 'paper', 0.9),
    Sc(193.80, 205.90, sc_repnin, 'dip', 0.9),
    Sc(205.90, 237.90, sc_bar, 'paper', 0.9),
    Sc(237.90, 248.40, sc_turkey, 'fade', 0.9),
    Sc(248.40, 260.95, sc_maria, 'dip', 0.9),
    Sc(260.95, 287.65, sc_plan, 'paper', 0.9),
    Sc(287.65, 304.20, sc_occupy, 'fade', 0.8),
    Sc(304.20, 315.35, sc_doc, 'dip', 0.9),
    Sc(315.35, 372.25, sc_partition, 'paper', 0.9),
    Sc(372.25, 387.90, sc_beforeafter, 'cut', 0.0),
    Sc(387.90, 396.30, sc_king, 'dip', 0.9),
    Sc(396.30, 401.70, sc_demand, 'fade', 0.7),
    Sc(401.70, 419.90, sc_rejtan, 'fade', 0.8),
    Sc(419.90, 430.60, sc_ratify, 'paper', 0.9),
    Sc(430.60, 470.30, sc_people, 'fade', 0.8),
    Sc(470.30, 493.40, sc_warning, 'cut', 0.0),
    Sc(493.40, 507.00, sc_constitution, 'dip', 0.9),
    Sc(507.00, 517.20, sc_further, 'paper', 0.9),
    Sc(517.20, END_A, sc_final, 'cut', 0.0),
]
DUR = END_A + LEAD

_s1 = _s2 = None
def render_frame(c, T):
    """Film compositor: T = film seconds."""
    global _s1, _s2
    a = T - LEAD
    idx = max(i for i, s in enumerate(SCENES) if s.a0 <= a or i == 0)
    sc = SCENES[idx]
    # transition with previous / next scene
    pair = None
    if idx > 0 and sc.trans != 'cut' and a < sc.a0 + sc.td / 2:
        pair = (SCENES[idx - 1], sc, sc.trans, sc.td, sc.a0)
    elif idx + 1 < len(SCENES) and SCENES[idx + 1].trans != 'cut' and a > sc.a1 - SCENES[idx + 1].td / 2:
        n = SCENES[idx + 1]; pair = (sc, n, n.trans, n.td, n.a0)
    if pair is None:
        sc.fn(c, a)
    else:
        A, B, kind, td, b = pair
        k = smoother((a - (b - td / 2)) / td)
        if _s1 is None: _s1 = skia.Surface(W, H); _s2 = skia.Surface(W, H)
        if kind in ('dip', 'paper'):
            col = (14, 10, 7) if kind == 'dip' else PAL['paper']
            if k < 0.5:
                A.fn(c, a); fade(c, k * 2, color=col)
            else:
                B.fn(c, a); fade(c, (1 - k) * 2, color=col)
        else:
            c1 = _s1.getCanvas(); A.fn(c1, a)
            c2 = _s2.getCanvas(); B.fn(c2, a)
            c.drawImage(_s1.makeImageSnapshot(), 0, 0)
            p = skia.Paint(); p.setAlphaf(k); c.drawImage(_s2.makeImageSnapshot(), 0, 0, skia.SamplingOptions(), p)
    subtitles.draw_sub(c, a)
    # global head/tail
    if T > DUR - 1.0: fade(c, ramp(T, DUR - 1.0, DUR))

def setup():
    S.init()
    S.FILM_MODE = True
    import scenes
    # in the film, subtitles are drawn once by the compositor; disable per-scene drawing
    scenes.draw_sub = lambda *a, **k: None
    global FIN, BASE
    FIN = S.FIN; BASE = S.BASE
