"""CONCEPT 3 - The Animated Timeline.
Editorial 'gallery wall' look: bone-white ground, black ink, one crimson accent; Swiss grid typography.
The camera glides down a 2.5D timeline; documents and paintings slide in as physical cards; mini-maps
show the territory at each date. At 1791 the line forks: solid black = our history, dashed gold = hypothetical."""
import numpy as np, skia
from core import *

BG = rgb('#efede8'); INK = rgb('#15151a'); GREY = rgb('#6e6c68'); RED = rgb('#b3202f'); GOLD = rgb('#b07d22')
SANS, SANSB = 'SourceSans3-Regular.ttf', 'SourceSans3-SemiBold.ttf'
LX = 130
FORK_Y, RX, AX = 1900, 270, 640    # fork position; branch column x for real / alternate

# ---------------- images as skia images (downscaled)
IMG = {k: to_image(load_rgb(f'assets/images/{f}', 900)) for k, f in
       {'cake': 'kings_cake.jpg', 'const': 'constitution_1791.jpg', 'cath': 'catherine.jpg'}.items()}

# mini-map frame: bounds of the pre-1772 Commonwealth
_b = L['plt_pre72'].bounds
MM = dict(x0=_b[0] - 40e3, x1=_b[2] + 40e3, y0=_b[1] - 40e3, y1=_b[3] + 40e3)


def minimap(c, x, y, w, layers, a=1.0, ghost=True):
    """layers: list of (geom, colour, alpha, dashed)."""
    s = w / (MM['x1'] - MM['x0']); h = (MM['y1'] - MM['y0']) * s
    M = skia.Matrix(); M.setTranslate(x, y); M.preScale(s, -s); M.preTranslate(-MM['x0'], -MM['y1'])
    if ghost:
        c.drawPath(tpath(path(L['plt_pre72']), M), fill(rgb('#d9d5cc', a)))
    for g, col, al, dashed in layers:
        if g is None or g.is_empty: continue
        p = tpath(path(g), M)
        if al > 0: c.drawPath(p, fill(skia.Color4f(col.fR, col.fG, col.fB, al * a)))
        c.drawPath(p, stroke(skia.Color4f(col.fR, col.fG, col.fB, a), 2.2, dash=[9, 6] if dashed else None))
    return h


def card(c, img, x, y, w, rot, a, caption=None, k=1.0):
    """a physical print with shadow; slides/settles in with k."""
    if a <= 0: return
    h = w * img.height() / img.width()
    c.save(); c.translate(x + (1 - k) * 260, y); c.rotate(rot * (0.4 + 0.6 * k) + (1 - k) * 8)
    sh = skia.Paint(Color4f=rgb('#000000', 0.28 * a), AntiAlias=True); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    c.drawRect(skia.Rect(-w / 2 + 10, -h / 2 + 22, w / 2 + 10, h / 2 + 28), sh)
    c.drawRect(skia.Rect(-w / 2 - 12, -h / 2 - 12, w / 2 + 12, h / 2 + 12), fill(rgb('#fbfaf6', a)))
    p = skia.Paint(); p.setAlphaf(a)
    c.drawImageRect(img, skia.Rect(-w / 2, -h / 2, w / 2, h / 2), SAMP, p)
    if caption:
        text(c, caption, -w / 2, h / 2 + 44, font(SANS, 22), rgb('#55534e', a), align='l', spacing=0.3)
    c.restore()


def node(c, x, y, a, col=INK, hollow=False):
    if a <= 0: return
    c.drawCircle(x, y, 15 * eout(a), fill(BG))
    if hollow: c.drawCircle(x, y, 11 * eout(a), stroke(skia.Color4f(col.fR, col.fG, col.fB, a), 3, dash=[5, 4]))
    else:
        c.drawCircle(x, y, 11 * eout(a), fill(skia.Color4f(col.fR, col.fG, col.fB, a)))


def entry(c, x, y, year, title, body, a, col=INK, hyp=False):
    if a <= 0: return
    yc = skia.Color4f(col.fR, col.fG, col.fB, a)
    text(c, year, x, y + 30, font('CG-SemiBold.ttf', 124), yc, align='l', spacing=1, reveal=a)
    text(c, title.upper(), x + 4, y + 84, font(SANSB, 33), rgb('#15151a', a), align='l', spacing=4, reveal=a)
    for i, ln in enumerate(body):
        text(c, ln, x + 4, y + 132 + i * 44, font('CG-MediumItalic.ttf', 40), rgb('#4a4843', a), align='l', reveal=a)
    if hyp:
        f = font(SANSB, 21); w = text_width('HYPOTHETICAL', f, 4) + 26
        r = skia.Rect.MakeXYWH(x + 4, y - 90, w, 34)
        c.drawRect(r, stroke(rgb('#b07d22', a), 1.6, dash=[6, 4])); text(c, 'HYPOTHETICAL', x + 17, y - 66, f, rgb('#8a5f12', a), align='l', spacing=4)


# ---------------- camera path through the timeline (world y at screen y=760)
KEYS = [(0.0, 120), (2.9, 330), (3.9, 1340), (5.3, 1420), (6.3, 2120), (7.4, 2260), (8.5, 2820), (9.7, 2900), (11.5, 2700)]


def cam_y(t):
    for (t0, y0), (t1, y1) in zip(KEYS, KEYS[1:]):
        if t <= t1: return lerp(y0, y1, eexp(seg(t, t0, t1)) * 0.7 + ease(seg(t, t0, t1)) * 0.3)
    return KEYS[-1][1]


def vis(y_world, cy, t_in, t):
    """appearance factor once the camera reaches an element"""
    return seg(t, t_in, t_in + 0.9)


def scene(c, t, f):
    c.clear(BG.toColor())
    cy = cam_y(t)
    zoom = lerp(1.0, 0.74, ease(seg(t, 9.7, 11.3)))
    # giant background year (parallax at 0.35), outline type
    big = '1772' if t < 3.6 else '1791' if t < 6.2 else '1793' if t < 8.0 else '1795'
    ka = seg(t, {'1772': 0, '1791': 3.3, '1793': 6.2, '1795': 8.0}[big], {'1772': 0, '1791': 3.3, '1793': 6.2, '1795': 8.0}[big] + 0.6)
    bf = font('CG-Bold.ttf', 470)
    p = stroke(rgb('#d8d4cb', ka * (1 - seg(t, 9.4, 10.0))), 2.0)
    w = text_width(big, bf, -6); xx = W / 2 - w / 2 + 30
    for ch in big:
        c.drawString(ch, xx, 1050 - (cy % 300) * 0.12, bf, p); xx += bf.measureText(ch) - 6
    # perspective world layer
    c.save()
    P = skia.Matrix()
    P.setPolyToPoly([skia.Point(0, 0), skia.Point(W, 0), skia.Point(W, H), skia.Point(0, H)],
                    [skia.Point(70, 60), skia.Point(W - 30, 30), skia.Point(W + 20, H + 30), skia.Point(-40, H + 10)])
    c.concat(P)
    c.translate(W / 2, 760); c.scale(zoom, zoom); c.translate(-W / 2, -cy)
    # main line, drawn as the camera travels
    head = cy + 760 / zoom + 200
    c.drawLine(LX, -600, LX, min(FORK_Y, head), stroke(INK, 4))
    if head > FORK_Y:
        k = clamp((head - FORK_Y) / 1700)
        # real branch: continues straight down
        c.drawLine(LX, FORK_Y, LX, FORK_Y + 1700 * k, stroke(INK, 4))
        # alternate branch: curves right, dashed gold
        br = skia.Path(); br.moveTo(LX, FORK_Y); br.cubicTo(LX, FORK_Y + 180, AX - 60, FORK_Y + 120, AX - 60, FORK_Y + 340)
        br.lineTo(AX - 60, FORK_Y + 1700)
        sp = stroke(GOLD, 4, dash=[16, 11])
        if k < 1: sp.setPathEffect(skia.PathEffect.MakeCompose(skia.DashPathEffect.Make([16, 11], 0), skia.TrimPathEffect.Make(0, max(k, 1e-3))))
        c.drawPath(br, sp)
        la = seg(t, 5.9, 6.6)
        text(c, 'OUR TIMELINE', LX + 26, FORK_Y + 200, font(SANSB, 28), rgb('#15151a', la), align='l', spacing=5)
        text(c, 'ALTERNATE TIMELINE', AX - 150, FORK_Y + 120, font(SANSB, 28), rgb('#8a5f12', la), align='l', spacing=5)
    # ---- 1772
    a = vis(0, cy, 0.2, t)
    node(c, LX, 0, a, RED)
    entry(c, LX + 50, 0, '1772', 'First Partition', ['Russia, Prussia and Austria', 'annex about 30% of the land'], a)
    mk = seg(t, 1.3, 2.5)
    minimap(c, LX + 50, 250, 470, [(L['plt_pre72'], RED, 0.18 * (1 - mk), False), (L['plt1773'], RED, 0.85, False)] if mk > 0 else
            [(L['plt_pre72'], RED, 0.85, False)], a)
    card(c, IMG['cake'], 820, 560, 290, 4, seg(t, 0.9, 1.7), 'Le Mire after Moreau, 1773', eout(seg(t, 0.9, 1.8)))
    # ---- 1791
    a = vis(0, cy, 3.6, t)
    node(c, LX, 1150, a, RED)
    entry(c, LX + 50, 1150, '1791', 'Constitution of 3 May', ['The Commonwealth adopts', 'a modern written constitution'], a)
    card(c, IMG['const'], 590, 1580, 600, -2.0, seg(t, 4.0, 4.7), 'Wojniakowski, Passing of the Constitution of 3 May, 1806', eout(seg(t, 4.0, 4.9)))
    # fork marker
    fa = seg(t, 5.6, 6.2)
    if fa > 0:
        c.drawCircle(LX, FORK_Y, 24, stroke(rgb('#b07d22', fa), 3))
        text(c, 'Here the timelines split', LX + 44, FORK_Y + 14, font('CG-MediumItalic.ttf', 48), rgb('#15151a', fa), align='l', reveal=fa)
    # ---- real branch
    for yy, yr, ti, body, tin, mm in [(2300, '1792', 'Russia invades', ['The reforms', 'are defeated'], 6.4, None),
                                      (2800, '1793', 'Second Partition', ['Russia and', 'Prussia annex'], 7.6, L['rump1793']),
                                      (3350, '1795', 'Third Partition', ['The state', 'disappears'], 8.8, 'none')]:
        a = vis(0, cy, tin, t)
        node(c, LX, yy, a, INK)
        entry(c, LX + 44, yy - 120, yr, ti, body, a)
        if mm is not None:
            minimap(c, LX + 50, yy + 50, 300, [] if mm == 'none' else [(mm, RED, 0.85, False)], a)
    # ---- alternate branch
    for yy, yr, ti, body, tin, al in [(2300, '1792', 'Reforms hold', ['Intervention', 'fails'], 6.8, 0.3),
                                      (3350, '1795', 'No partition', ['The Commonwealth', 'endures'], 9.1, 0.55)]:
        a = vis(0, cy, tin, t)
        node(c, AX - 60, yy, a, GOLD, hollow=True)
        entry(c, AX - 16, yy - 120, yr, ti, body, a, GOLD, hyp=True)
        if al: minimap(c, AX - 10, yy + 50, 300, [(L['plt1773'], GOLD, al, True)], a)
    c.restore()
    # header (fixed, TikTok-safe) on a soft backing so scrolling content passes beneath
    hb = skia.Paint(); hb.setShader(lin_grad((0, 250), (0, 420), [BG, skia.Color4f(BG.fR, BG.fG, BG.fB, 0)])); c.drawRect(skia.Rect(0, 0, W, 420), hb)
    ha = seg(t, 0.0, 0.6)
    text(c, 'POLAND–LITHUANIA', 92, 290, font(SANSB, 34), rgb('#15151a', ha), align='l', spacing=9)
    c.drawLine(92, 312, 92 + 300 * eout(seg(t, 0.2, 1.0)), 312, stroke(RED, 3))
    yr = '1772' if t < 3.3 else '1791' if t < 6.2 else '1793 / 1795'
    text(c, yr, 988, 290, font(SANS, 34), rgb('#6e6c68', ha), align='r', spacing=4)
    # legend at the end
    la = seg(t, 9.9, 10.6)
    if la > 0:
        y = 1440
        c.drawLine(92, y, 170, y, stroke(rgb('#15151a', la), 4)); text(c, 'Documented history', 190, y + 10, font(SANS, 30), rgb('#15151a', la), align='l')
        sp = stroke(rgb('#b07d22', la), 4, dash=[14, 9]); c.drawLine(92, y + 52, 170, y + 52, sp)
        text(c, 'Hypothetical: what might have been', 190, y + 62, font(SANS, 30), rgb('#8a5f12', la), align='l')
    if t < 0.3: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.3)))


if __name__ == '__main__':
    out = f'{ROOT}/previews/concepts/concept3_animated_timeline.mp4'
    render(scene, 11.5, out, Post(grain=0.022, vignette=0.22, bloom=0.0, seed=5), stills=(2.4, 5.0, 6.5, 9.4, 11.3),
           still_dir=f'{ROOT}/previews/concepts')
