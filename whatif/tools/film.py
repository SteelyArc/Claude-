"""FILM - What if Poland-Lithuania had never been partitioned?  (Concept 1: Night Atlas)

One persistent atlas world; everything is keyed to word timestamps of the untouched narration (tools/cues.py).
See storyboard/STORYBOARD.md for the shot list."""
import os, sys, pickle, numpy as np, skia, cv2
from shapely.geometry import Point
from core import *
from cues import cue
import concept1_atlas as A1

DUR = 300.0
PAL = A1.PAL
GOLD_C = '#c98a2c'; CRIMSON = '#b42d3c'
S91 = L['stages']['1791']; S73 = L['stages']['1773']
PLT91 = A1.PLT91
MODERN = pickle.load(open(f'{ROOT}/data/modern_countries.pkl', 'rb'))
C = cue


# ================================================================ timing helpers
def keyed(t, keys, fn=ease):
    """interpolate scalar keys [(t, v), ...] with easing between consecutive keys; holds at the ends."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1: return v0 + (v1 - v0) * fn(seg(t, t0, t1))
    return keys[-1][1]


def win(t, t0, t1, fi=0.5, fo=0.5):
    """visibility window with fade in/out."""
    return seg(t, t0, t0 + fi) * (1 - seg(t, t1 - fo, t1))


# ================================================================ camera
CAM_KEYS = [
    (0.0, (24.8, 51.9, .56, -10, .58, 300)), (4.6, (24.6, 52.6, .60, -2, .30, 60)), (6.2, (24.6, 52.6, .62, -1, .28, 60)),
    (9.4, (22.6, 52.6, .80, 0, .35, 80)), (11.2, (21.3, 52.3, 1.0, 4, .44, 130)), (13.0, (21.3, 52.3, 1.05, 5, .44, 130)),
    (16.2, (22.8, 54.0, .47, 0, .24, 30)), (21.7, (24.4, 53.0, .52, -2, .28, 40)), (23.4, (24.6, 52.6, .60, 0, .22, 40)),
    (26.9, (24.6, 52.6, .63, 0, .22, 40)), (29.4, (24.4, 52.4, .67, -9, .42, 90)), (34.2, (24.6, 52.6, .62, 0, .30, 60)),
    (38.1, (25.0, 52.2, .58, 0, .25, 50)), (45.0, (26.6, 51.6, .70, 6, .46, 130)), (50.9, (23.4, 52.5, .66, -4, .40, 100)),
    (57.4, (24.6, 52.6, .55, 0, .20, 30)), (63.2, (24.6, 52.4, .60, 0, .22, 40)), (67.0, (24.6, 52.4, .62, 0, .26, 50)),
    (70.5, (21.6, 52.0, 1.0, -3, .50, 170)), (87.8, (22.6, 52.3, .78, 0, .40, 100)), (93.0, (24.8, 52.4, .60, 0, .25, 40)),
    (96.0, (27.0, 52.0, .67, 5, .40, 100)), (104.4, (24.6, 52.6, .62, 0, .25, 50)), (116.0, (24.6, 52.6, .60, 0, .25, 50)),
    (118.8, (24.6, 52.6, .57, 0, .30, 60)), (121.3, (23.4, 52.4, .70, -3, .42, 90)), (127.4, (27.6, 52.0, .74, 4, .46, 110)),
    (131.2, (21.0, 52.5, .56, -3, .35, 80)), (136.0, (27.4, 53.0, .60, 3, .36, 80)), (144.2, (24.6, 52.6, .62, 0, .30, 60)),
    (154.3, (24.6, 52.6, .60, 0, .30, 60)), (160.2, (24.6, 52.6, .54, -6, .56, 260)), (163.4, (24.6, 52.6, .62, 0, .02, 40)),
    (171.2, (23.6, 52.5, .66, 0, .05, 40)), (181.9, (24.6, 52.6, .60, 0, .14, 40)), (194.0, (23.6, 52.4, .53, 0, .20, 40)),
    (199.8, (21.6, 52.7, .78, -3, .40, 100)), (203.5, (25.2, 54.6, 1.05, 4, .50, 150)), (206.8, (22.4, 52.0, .47, 0, .25, 40)),
    (219.5, (24.0, 52.0, .50, 0, .25, 40)), (231.3, (24.6, 52.6, .52, 0, .22, 40)), (239.5, (19.8, 53.0, .70, -4, .40, 100)),
    (245.5, (23.0, 52.5, .50, 0, .52, 280)), (247.8, (23.0, 52.5, .47, 0, .30, 80)), (256.7, (23.0, 52.5, .45, 0, .30, 80)),
    (264.7, (24.6, 52.6, .58, 0, .25, 50)), (280.3, (19.5, 51.6, .46, 0, .22, 40)), (289.2, (22.2, 52.0, .52, -3, .40, 120)),
    (293.0, (22.2, 52.0, .50, -8, .60, 320)), (300.0, (22.2, 52.0, .47, -10, .66, 340)),
]
_CK = [(t, (*ll(a, b), z, r, ti, oy)) for t, (a, b, z, r, ti, oy) in CAM_KEYS]


def camera(t):
    if t <= _CK[0][0]: v = _CK[0][1]; k = 0
    else:
        for (t0, v0), (t1, v1) in zip(_CK, _CK[1:]):
            if t <= t1: break
        e = ease(seg(t, t0, t1))
        v = [lerp(a, b, e) for a, b in zip(v0, v1)]
        v[2] = float(np.exp(lerp(np.log(v0[2]), np.log(v1[2]), e)))
    c = Cam(v[0], v[1], v[2], v[3], v[4], v[5])
    c.cx += 2600 * np.sin(t * 0.71 + 1.3) + 1400 * np.sin(t * 1.37); c.cy += 2200 * np.sin(t * 0.53 + 0.4)
    c.rot += 0.18 * np.sin(t * 0.61 + 2.0)
    return c


# ================================================================ status & grade
def status(t):
    """(kind, label) of the persistent status chip, or None."""
    if t < C('imagine') - 0.2: return None
    if t < C('in our timeline') - 0.2: return ('hyp', 'HYPOTHETICAL')
    if t < C('imagine a different') - 0.2: return ('doc', 'DOCUMENTED HISTORY')
    if t < C('first world war') - 0.6: return ('hyp', 'HYPOTHETICAL')
    if t < C('what we do know') - 0.2: return ('hyp', 'OPEN QUESTIONS')
    if t < C('imagine looking') - 0.2: return ('doc', 'DOCUMENTED HISTORY')
    if t < C('what if poland', 290): return ('hyp', 'HYPOTHETICAL · ILLUSTRATIVE')
    return None


def goldness(t):
    """0 = documented crimson Commonwealth, 1 = hypothetical gold."""
    return keyed(t, [(0, 0), (C('imagine') + 0.2, 0), (C('imagine') + 1.2, 1), (C('in our timeline') - 0.1, 1), (C('in our timeline') + 0.8, 0),
                     (C('imagine a different') + 1.6, 0), (C('may constitution') + 0.6, 1), (C('what we do know') - 0.2, 1),
                     (C('what we do know') + 1.2, 0), (C('imagine looking') + 3.6, 0), (C('still there') + 0.8, 1)])


# ================================================================ partition plates: k tracks (0 = Commonwealth, 1 = annexed)
G = L['gains']
PIECES = {  # name: (geom, power, direction)
    '72p': (L['loss72']['pru'], 'prussia', A1.W_), '72r': (L['loss72']['rus'], 'russia', A1.E_), '72a': (L['loss72']['aut'], 'habsburg', A1.S_),
    '93p': (G['93_pru'], 'prussia', A1.W_), '93r': (G['93_rus'], 'russia', A1.E_),
    '95p': (G['95_pru'], 'prussia', A1.W_), '95r': (G['95_rus'], 'russia', A1.E_), '95c': (G['95_rus_courland'], 'russia', A1.N_), '95a': (G['95_aut'], 'habsburg', A1.S_),
}


def _k72():
    t_cut = C('imagine') + 0.5
    return [(0, 0), (t_cut, 0), (t_cut + 0.01, 1, 'cut'),
            (C('once one') - 1.6, 1), (C('once one') + 0.6, 0, 'rev'),
            (C('opportunities') - 0.4, 0), (C('opportunities') + 1.6, 1, 'annex')]


def _k93(o=0.0):
    a = C('in our timeline') + 0.3 + o
    return [(0, 0), (a, 0), (a + 1.2, 1, 'annex'), (C('alternative world') + o * 0.5, 1), (C('1791') + 0.2 + o * 0.5, 0, 'rev'),
            (C('second partition') - 0.3 + o, 0), (C('second partition') + 1.2 + o, 1, 'annex'),
            (C('imagine a different') + 0.8, 1), (C('imagine a different') + 2.6, 0, 'rev'),
            (C('second partition never') + 0.2 + o, 0), (C('second partition never') + 1.4 + o, 0, 'fail'),
            (C('what we do know') + 0.4 + o, 0), (C('what we do know') + 1.8 + o, 1, 'annex'),
            (C('imagine looking') + 0.2, 1), (C('imagine looking') + 1.6, 0, 'cut')]


def _k95(o=0.0):
    a = C('in our timeline') + 1.0 + o
    return [(0, 0), (a, 0), (a + 1.1, 1, 'annex'), (C('alternative world') + 0.4 + o * 0.5, 1), (C('1791') + 0.2, 0, 'rev'),
            (C('third partition') - 0.3 + o, 0), (C('third partition') + 1.2 + o, 1, 'annex'),
            (C('imagine a different') + 0.6, 1), (C('imagine a different') + 2.4, 0, 'rev'),
            (C('no third') + 0.1 + o, 0), (C('no third') + 1.3 + o, 0, 'fail'),
            (C('what we do know') + 1.0 + o, 0), (C('what we do know') + 2.4 + o, 1, 'annex'),
            (C('imagine looking') + 0.2, 1), (C('imagine looking') + 1.6, 0, 'cut')]


KT = {'72p': _k72(), '72r': _k72(), '72a': _k72(), '93p': _k93(), '93r': _k93(0.12),
      '95p': _k95(), '95r': _k95(0.1), '95c': _k95(0.1), '95a': _k95(0.2)}


def emphasis(name, t):
    """1 while an annexation is happening and ~3 s after; then 0 (the land simply belongs to the neighbour).
    Kept on during the documented recap, where the partitions are the subject."""
    if C('what we do know') <= t < C('imagine looking') + 0.2: return 1.0
    tend = None
    for a, b in zip(KT[name], KT[name][1:]):
        kind = b[2] if len(b) > 2 else None
        if b[0] <= t and kind in ('annex', 'cut') and b[1] == 1: tend = b[0]
    if tend is None: return 1.0
    return 1 - seg(t, tend + 2.6, tend + 3.8)


def plate_state(name, t):
    """(k, h, kind): annexation level, lift height 0..1, transition kind."""
    ks = KT[name]
    if t <= ks[0][0]: return ks[0][1], 0.0, None
    for a, b in zip(ks, ks[1:]):
        if t <= b[0]:
            kind = b[2] if len(b) > 2 else None
            p = seg(t, a[0], b[0])
            if kind == 'cut': return (a[1] if p < 1 else b[1]), 0.0, kind
            if kind == 'fail': return 0.0, float(np.sin(np.pi * p) * 0.7), kind
            if a[1] == b[1]: return a[1], 0.0, kind
            return lerp(a[1], b[1], ease(p)), float(np.sin(np.pi * p)), kind
    return ks[-1][1], 0.0, None


# ================================================================ images: 2.5D plates
class Pic:
    def __init__(self, fname, depth=None, max_side=1800):
        im = load_rgb(f'assets/images/{fname}', max_side).astype(np.float32) / 255
        self.im = im; self.h, self.w = im.shape[:2]
        if depth and os.path.exists(f'{ROOT}/data/depth/{depth}.npy'):
            d = np.load(f'{ROOT}/data/depth/{depth}.npy').astype(np.float32)
            self.d = cv2.GaussianBlur(cv2.resize(d, (self.w, self.h)), (0, 0), 3)
        else:
            self.d = None
        lab = cv2.cvtColor(np.clip(im, 0, 1), cv2.COLOR_RGB2LAB)
        l8 = np.clip(lab[..., 0] * 2.55, 0, 255).astype(np.uint8)
        lab[..., 0] = lab[..., 0] * 0.6 + cv2.createCLAHE(1.5, (8, 8)).apply(l8).astype(np.float32) / 2.55 * 0.4
        self.im = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB), 0, 1).astype(np.float32)

    def shoot(self, w, h, fx, fy, fz, par, dolly):
        """fx, fy: focus point (0..1 of image); fz: zoom (1 = fit cover); par: parallax px; dolly: near magnification."""
        cover = max(w / self.w, h / self.h) * fz
        xs = (np.arange(w, dtype=np.float32) - w / 2) / cover; ys = (np.arange(h, dtype=np.float32) - h / 2) / cover
        U, V = np.meshgrid(xs, ys)
        cx = np.clip(fx * self.w, w / 2 / cover, self.w - w / 2 / cover); cy = np.clip(fy * self.h, h / 2 / cover, self.h - h / 2 / cover)
        u = (U + cx).astype(np.float32); v = (V + cy).astype(np.float32)
        if self.d is not None:
            for _ in range(2):
                d = cv2.remap(self.d, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                k = 1 / (1 + dolly * d)
                u = (cx + U * k - par * (d - 0.5)).astype(np.float32); v = (cy + V * k).astype(np.float32)
        img = cv2.remap(self.im, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        lum = img.mean(axis=2, keepdims=True)   # atlas grade: cool shadows, warm highlights, soft shoulder
        img = img * (1 - lum) * 0.95 + img * lum * np.array([1.05, 0.99, 0.9], np.float32) + np.array([0.01, 0.025, 0.04], np.float32) * (1 - lum) ** 3
        return np.clip(img * 1.12 / (1 + img * 0.12), 0, 1)


_PICS = {}
PIC_DEF = {'const': ('constitution_1791.jpg', 'constitution_1791'), 'king': ('stanislaw.png', 'stanislaw'),
           'elect': ('bellotto_election.jpg', 'bellotto_election'), 'cath': ('catherine.jpg', 'catherine'),
           'fred': ('frederick.jpg', 'frederick'), 'mt': ('maria_theresa.jpg', 'maria_theresa'),
           'napo': ('napoleon_premier_consul_LOC.jpg', 'napoleon_premier_consul_LOC'), 'plan': ('LOC_Plan_de_Varsovie_RizziZannoni_atlas.jpg', None),
           'cake': ('kings_cake.jpg', None), 'matejko': ('LOC_Stanislaus_Augustus_to_church_Constitution_1791.jpg', None),
           'fw2': ('LOC_Friedrich_Wilhelm_II_Tardieu_after_Bornet.jpg', None), 'fr2': ('Ketterlinus_Francis_II_1792_NGA.jpg', None),
           'kosc': ('LOC_Kosciuszko_picture.jpg', None), 'rizzi': ('LOC_RizziZannoni_1772_Carte_de_la_Pologne_general.jpg', None),
           'lotter': ('Lotter_1778_Magnus_Ducatus_Lithuaniae_LOC.jpg', None), 'sayer': ('sayer_map.jpg', None)}


def pic(k):
    if k not in _PICS: _PICS[k] = Pic(*PIC_DEF[k])
    return _PICS[k]


def plate(c, t, key, t0, t1, x, y, w, h, title, credit, focus=(0.5, 0.4), z=(1.0, 1.12), par=(30, -30), dolly=(0.0, 0.12), ts=38):
    """framed painting floating above the atlas: rises in, slow 2.5D push, fades out. (x, y) = top-left."""
    a = win(t, t0, t1, 0.7, 0.6)
    if a <= 0: return
    k = seg(t, t0, t1); e = ease(k); rise = (1 - eout(seg(t, t0, t0 + 0.9))) * 46
    img = pic(key).shoot(int(w), int(h), focus[0], focus[1], lerp(*z, e), lerp(*par, e), lerp(*dolly, e))
    si = to_image((img * 255).astype(np.uint8))
    c.save(); c.translate(x + w / 2, y + h / 2 + rise); sc = 0.96 + 0.04 * eout(seg(t, t0, t0 + 1.0)); c.scale(sc, sc)
    c.rotate(0.6 * np.sin(t * 0.4 + x))
    sh = skia.Paint(Color4f=rgb('#000000', 0.7 * a), AntiAlias=True); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 28))
    c.drawRect(skia.Rect(-w / 2 + 6, -h / 2 + 24, w / 2 + 18, h / 2 + 40), sh)
    c.drawRect(skia.Rect(-w / 2 - 14, -h / 2 - 14, w / 2 + 14, h / 2 + 14), fill(rgb('#0b0f14', 0.94 * a)))
    p = skia.Paint(); p.setAlphaf(a); c.drawImageRect(si, skia.Rect(-w / 2, -h / 2, w / 2, h / 2), SAMP, p)
    c.drawRect(skia.Rect(-w / 2 - 7, -h / 2 - 7, w / 2 + 7, h / 2 + 7), stroke(rgb('#e6c27d', 0.85 * a), 1.3))
    gl = skia.Paint(); gl.setBlendMode(skia.BlendMode.kScreen); gx = lerp(-w, w, (t * 0.12 + x / 997) % 1.0)   # slow glass sheen
    gl.setShader(lin_grad((gx - 160, -h / 2), (gx + 160, h / 2), [rgb('#ffffff', 0), rgb('#ffffff', 0.06 * a), rgb('#ffffff', 0)], [0, .5, 1]))
    c.drawRect(skia.Rect(-w / 2, -h / 2, w / 2, h / 2), gl)
    yy = h / 2 + 14 + ts
    text(c, title, -w / 2, yy, font('CG-SemiBold.ttf', ts), rgb('#f6ecd9', a), align='l', reveal=seg(t, t0 + 0.3, t0 + 1.3), shadow=rgb('#000000', 0.9 * a))
    for i, ln in enumerate(credit.split(' | ')):
        text(c, ln, -w / 2, yy + ts * 0.9 + i * 28, font('SourceSans3-Regular.ttf', 23 if ts >= 34 else 20), rgb('#cfc4b0', 0.9 * a), align='l', shadow=rgb('#000000', 0.9 * a))
    c.restore()


# ================================================================ typographic devices
def status_chip(c, t):
    st = status(t)
    if st is None: return
    kind, s = st
    # fade on change
    a = 1.0
    for ch in (C('imagine'), C('in our timeline'), C('imagine a different'), C('first world war') - 0.4, C('what we do know'), C('imagine looking')):
        a = min(a, 0.25 + 0.75 * clamp(abs(t - (ch - 0.2)) / 0.35))
    f = font('SourceSans3-SemiBold.ttf', 24); w = text_width(s, f, 4) + 44
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(92, 262, w, 44), 22, 22)
    if kind == 'doc':
        c.drawRRect(r, fill(rgb('#0c1218', 0.72 * a))); c.drawRRect(r, stroke(rgb('#dfe6ea', 0.75 * a), 1.6))
        c.drawCircle(92 + 22, 284, 5, fill(rgb('#dfe6ea', a))); text(c, s, 92 + 36, 292, f, rgb('#e8eef2', a), align='l', spacing=4)
    else:
        c.drawRRect(r, fill(rgb('#2a1d08', 0.8 * a))); c.drawRRect(r, stroke(rgb('#f0cd86', a), 2, dash=[10, 7]))
        c.drawCircle(92 + 22, 284, 5, stroke(rgb('#ffd98f', a), 2)); text(c, s, 92 + 36, 292, f, rgb('#ffd98f', a), align='l', spacing=4)


def card(c, t, t0, t1, kicker, lines, sub=None, y=420, kind='doc', size=66, x=None):
    a = win(t, t0, t1, 0.5, 0.5)
    if a <= 0: return
    hyp = kind == 'hyp'
    kc = rgb('#ffd98f' if hyp else '#e6c27d', a)
    left = x is not None
    X = x if left else W / 2
    al = 'l' if left else 'c'
    text(c, kicker, X, y, font('SourceSans3-SemiBold.ttf', 27), kc, align=al, spacing=7, reveal=seg(t, t0, t0 + 0.7), shadow=rgb('#000000', 0.9 * a))
    rl = 240 * eout(seg(t, t0 + 0.1, t0 + 0.8))
    if left: c.drawLine(X, y + 18, X + rl * 1.6, y + 18, stroke(kc, 1.6))
    else: c.drawLine(W / 2 - rl, y + 18, W / 2 + rl, y + 18, stroke(kc, 1.6))
    for i, ln in enumerate(lines):
        if hyp: A1.gold_text(c, ln, X if not left else X + text_width(ln, font('CG-SemiBold.ttf', size), 0.5) / 2, y + 26 + (i + 1) * size * 1.02,
                             font('CG-SemiBold.ttf', size), a, seg(t, t0 + 0.15 + i * 0.12, t0 + 1.1 + i * 0.12), 0.5, seg(t, t0 + 0.6, t0 + 2.2))
        else: text(c, ln, X, y + 26 + (i + 1) * size * 1.02, font('CG-SemiBold.ttf', size), rgb('#fbf3e3', a), align=al, spacing=0.5,
                   reveal=seg(t, t0 + 0.15 + i * 0.12, t0 + 1.1 + i * 0.12), shadow=rgb('#000000', 0.9 * a))
    if sub:
        yy = y + 26 + len(lines) * size * 1.02 + 52
        for i, ln in enumerate(sub.split(' | ')):
            text(c, ln, X, yy + i * 44, font('CG-MediumItalic.ttf', 40), rgb('#eadfc8', a), align=al, reveal=seg(t, t0 + 0.5, t0 + 1.5), shadow=rgb('#000000', 0.9 * a))


YEARS = None


def _years():
    y = [(C('in our timeline') + 1.6, '1795', 'THIRD PARTITION', 'doc'), (C('alternative world'), '1793', '', 'doc'),
         (C('alternative world') + 0.9, '1792', '', 'doc'), (C('1791') - 0.3, '1791', 'CONSTITUTION OF 3 MAY', 'doc'),
         (C('once one') - 1.4, '1770', 'BEFORE THE PARTITIONS', 'doc'), (C('dangerously weak') - 0.6, None, '', 'doc'),
         (C('opportunities') - 0.5, '1772', 'FIRST PARTITION', 'doc'), (C('then came') + 0.6, None, '', 'doc'),
         (C('intervened') - 0.3, '1792', 'RUSSIAN INTERVENTION', 'doc'), (C('targovica') - 0.3, None, '', 'doc'),
         (C('in 1793'), '1793', 'SECOND PARTITION', 'doc'), (C('third partition') - 0.6, '1795', 'THIRD PARTITION', 'doc'),
         (C('imagine a different') + 0.8, '1791', 'IF THE REFORMS HAD HELD', 'hyp'), (C('stronger army') - 0.8, None, '', 'hyp'),
         (C('crisis') - 0.2, '1792', 'THE CRISIS PASSES', 'hyp'), (C('second partition never') - 0.4, '1793', 'NO SECOND PARTITION', 'hyp'),
         (C('1795 arrives'), '1795', 'NO THIRD PARTITION', 'hyp'), (C('remains on the map') - 0.3, None, '', 'hyp'),
         (C('19th century'), '1800s', 'A SURVIVING COMMONWEALTH', 'hyp'), (C('enormous') - 0.4, None, '', 'hyp'),
         (C('what we do know') + 0.2, '1795', 'THE PARTITIONS COMPLETED', 'doc'), (C('political weakness') - 0.3, None, '', 'doc')]
    return y


def year_counter(c, t):
    global YEARS
    if YEARS is None: YEARS = _years()
    cur = None
    for i, e in enumerate(YEARS):
        if t >= e[0]: cur = i
    if cur is None: return
    ts, yv, sub, kind = YEARS[cur]
    prev = YEARS[cur - 1] if cur > 0 else None
    k = eout(seg(t, ts, ts + 0.45), 4)
    f = font('Cinzel-Bold.ttf', 140); y = 1330
    if yv is None:   # fade out previous
        if prev is None or prev[1] is None: return
        a = 1 - seg(t, ts, ts + 0.5)
        if a <= 0: return
        ts, yv, sub, kind = prev; k = 1.0; prev = None
    else:
        a = 1.0
        if prev is not None and prev[1] is None: prev = None
    hyp = kind == 'hyp'
    c.save(); c.clipRect(skia.Rect(0, y - 140, W, y + 34))
    if prev is not None and k < 1:
        text(c, prev[1], W / 2, y - 150 * k, f, rgb('#f3ead8', a * (1 - k)), spacing=14)
    if hyp: A1.gold_text(c, yv, W / 2, y + 150 * (1 - k), f, a, 1.0, 14, seg(t, ts + 0.3, ts + 1.6))
    else: text(c, yv, W / 2, y + 150 * (1 - k), f, rgb('#f3ead8', a), spacing=14)
    c.restore()
    if sub:
        rule = 150 * eout(seg(t, ts + 0.1, ts + 0.7)); rc = rgb('#ffd98f' if hyp else '#c9d3da', 0.7 * a)
        c.drawLine(W / 2 - 230 - rule, y + 52, W / 2 - 230, y + 52, stroke(rc, 1.4)); c.drawLine(W / 2 + 230, y + 52, W / 2 + 230 + rule, y + 52, stroke(rc, 1.4))
        text(c, sub, W / 2, y + 66, font('SourceSans3-SemiBold.ttf', 30), rgb('#ffd98f' if hyp else '#d3dce2', a * k), spacing=8, reveal=k)


def wlabel(c, cam, lon, lat, s, f, col, a, spacing=4, reveal=1.0, dy=0, glow=None):
    if a <= 0: return
    x, y = cam.pt(*ll(lon, lat))
    text(c, s, x, y + dy, f, skia.Color4f(col.fR, col.fG, col.fB, col.fA * a), spacing=spacing, reveal=reveal, shadow=rgb('#000000', 0.9 * a), glow=glow)


def warrow(c, M, pts, k, col, w=7, a=1.0):
    """curved campaign arrow in world coords (schematic)."""
    if k <= 0 or a <= 0: return
    P = [M.mapXY(*ll(*q)) for q in pts]
    p = skia.Path(); p.moveTo(P[0]); p.quadTo(P[1], P[2])
    meas = skia.PathMeasure(p, False); Ln = meas.getLength()
    sp = skia.Path(); meas.getSegment(0, Ln * k, sp, True)
    cc = skia.Color4f(col.fR, col.fG, col.fB, a)
    c.drawPath(sp, stroke(skia.Color4f(col.fR, col.fG, col.fB, 0.35 * a), w * 3, glow=8)); c.drawPath(sp, stroke(cc, w, cap=skia.Paint.kButt_Cap))
    pos, tan = meas.getPosTan(Ln * k)
    c.save(); c.translate(pos.x(), pos.y()); c.rotate(np.degrees(np.arctan2(tan.y(), tan.x())))
    hp = skia.Path(); hp.moveTo(24, 0); hp.lineTo(-10, -17); hp.lineTo(-4, 0); hp.lineTo(-10, 17); hp.close(); c.drawPath(hp, fill(cc)); c.restore()


def wline(c, M, a_ll, b_ll, k, col, w=2.0, bend=0.18, a=1.0, dash=None):
    if k <= 0 or a <= 0: return
    A = M.mapXY(*ll(*a_ll)); B = M.mapXY(*ll(*b_ll))
    mx, my = (A.x() + B.x()) / 2, (A.y() + B.y()) / 2; dx, dy = B.x() - A.x(), B.y() - A.y()
    p = skia.Path(); p.moveTo(A); p.quadTo(mx - dy * bend, my + dx * bend, B.x(), B.y())
    meas = skia.PathMeasure(p, False); sp = skia.Path(); meas.getSegment(0, meas.getLength() * k, sp, True)
    c.drawPath(sp, stroke(skia.Color4f(col.fR, col.fG, col.fB, 0.4 * a), w * 4, glow=6))
    c.drawPath(sp, stroke(skia.Color4f(col.fR, col.fG, col.fB, a), w, dash=dash))


# ================================================================ geography of labels
PEOPLES = [('Polish', 19.6, 51.0), ('Lithuanian', 23.6, 55.4), ('Ruthenian', 27.6, 50.6), ('Jewish', 26.7, 51.75),
           ('German', 18.4, 53.7), ('Armenian', 26.3, 48.9), ('Tatar', 25.9, 54.0), ('Latvian', 26.8, 56.2)]
CAPITALS = [('Berlin', 'l'), ('Vienna', 'l'), ('St Petersburg', 'r'), ('Moscow', 'r')]
REGION = [('Kraków', 'l'), ('Lwów', 'r'), ('Gdańsk', 'l'), ('Vilnius', 'r'), ('Grodno', 'r')]


# ================================================================ the frame
def scene(c, t, f):
    cam = camera(t); M = cam.matrix(); POST_STATE['dof'] = cam.tilt * 1.3
    gd = goldness(t)
    c.clear(skia.Color4f(0.02, 0.035, 0.055, 1))
    # ---------------- world layer (relief, neighbours) with focus falloff
    c.saveLayer()
    c.save(); c.concat(M); c.drawRect(skia.Rect(-6e6, -6e6, 6e6, 6e6), fill(skia.Color4f(0.018, 0.035, 0.058, 1)))
    c.translate(A1.X0, A1.Y1); c.scale(A1.RES, -A1.RES); c.drawImage(A1.relief(), 0, 0, SAMP); c.restore()
    ra = 0.5 * seg(t, 2.0, 3.4)
    for r in A1.RIVERS:
        p = tpath(path(r['geom']), M); c.drawPath(p, stroke(rgb('#5fb3d9', ra * 0.35), 4, glow=4)); c.drawPath(p, stroke(rgb('#9bd6ef', ra), 1.1))
    modern = win(t, C('borders of modern') - 0.3, C('cannot know') + 1.2, 1.0, 1.4) + win(t, C('imagine looking') - 0.2, DUR + 5, 1.6, 0.1)
    neigh = (0.30 + 0.10 * seg(t, 3.0, 4.0)) * (1 - 0.55 * clamp(modern))
    for k in ('hre', 'saxony', 'sweden', 'denmark', 'other', 'venice', 'ragusa'):
        g = S73.get(k)
        if g is not None and not g.is_empty: A1.glass(c, tpath(path(g), M), PAL['other'], 0.10 * (1 - modern), 0.25 * (1 - modern), '#8d98a0', 0.8)
    # neighbours light up on their names (Imagine..., neighbouring monarchies, balance)
    hl = {'russia': win(t, C('russia prussia and austria') - 0.1, C('in our timeline'), 0.3, 1.0) + win(t, C('russia increasingly') - 0.2, C('then came'), 0.4, 0.8)
                    + win(t, C('threat') - 0.3, C('crisis'), 0.4, 0.8) + win(t, C('limit russian') - 0.2, C('prevent prussia'), 0.4, 0.6),
          'prussia': win(t, C('prussia', 18.9) - 0.1, C('in our timeline'), 0.3, 1.0) + win(t, C('prussia and austria', 60) - 0.2, C('then came'), 0.4, 0.8)
                     + win(t, C('prevent prussia') - 0.2, C('radically different'), 0.4, 0.6),
          'habsburg': win(t, C('austria', 19.5) - 0.1, C('in our timeline'), 0.3, 1.0) + win(t, C('prussia and austria', 60) + 0.4, C('then came'), 0.4, 0.8)}
    nb = win(t, C('neighboring monarchies') - 0.2, C('then came'), 0.5, 0.8) + win(t, C('balance') - 0.2, C('limit russian'), 0.5, 0.6) + win(t, C('alarmed') - 0.2, C('intervened') + 1, 0.4, 0.8)
    for k, ec in (('ottoman', '#9a8b7e'), ('habsburg', '#d6b48a'), ('russia', '#a9bf8f'), ('prussia', '#9ab8d8')):
        g = A1.RUSSIA_DISP if k == 'russia' else S91[k]
        h_ = clamp(hl.get(k, 0) + nb * (k != 'ottoman'))
        A1.glass(c, tpath(path(g), M), PAL[k], neigh * (1 + 0.9 * h_), 0.5 + 0.5 * h_, ec, 1 + 1.4 * h_)
    if modern > 0:   # modern borders (Natural Earth), hairlines
        for nm, g in MODERN.items():
            c.drawPath(tpath(outline(g), M), stroke(rgb('#c9d6e2', 0.55 * clamp(modern)), 1.1))
    fx, fy = cam.pt(cam.cx, cam.cy); rr = 950 * cam.zoom / 0.6
    fm = skia.Paint(); fm.setBlendMode(skia.BlendMode.kDstIn)
    fm.setShader(rad_grad(fx, fy, rr, [rgb('#000000', 1), rgb('#000000', 0.92), rgb('#000000', 0)], [0, .55, 1])); c.drawPaint(fm)
    c.restore()
    # ---------------- the Commonwealth + plates
    base_col = lerpc((0.706, 0.176, 0.235), (0.788, 0.541, 0.173), gd)
    base_hex = '#%02x%02x%02x' % tuple(int(v * 255) for v in base_col)
    vis = 1.0 - win(t, C('imagine') + 0.1, C('imagine') + 0.9, 0.4, 0.4) * 0.8      # dissolve at the hook->imagine cut
    vis *= 1 - 0.75 * win(t, C('first world war') - 0.2, C('one possible path') + 1.5, 1.0, 1.5)   # questions: map recedes
    vis *= 1 - win(t, C('imagine looking') + 0.3, C('still there') - 0.1, 0.9, 0.7)
    ca = 0.66 * seg(t, 1.2, 2.8) * vis * lerp(1.0, 0.70, gd) * (1 - 0.35 * seg(t, C('imagine looking'), C('imagine looking') + 1))
    states = {n: plate_state(n, t) for n in PIECES}
    c.save()
    for n, (g, pw, d) in PIECES.items():
        k, h, kind = states[n]
        if k > 0 or h > 0: c.clipPath(tpath(path(g), M), skia.ClipOp.kDifference, True)
    A1.glass(c, tpath(path(L['plt_pre72']), M), base_hex, ca)
    A1.glass(c, tpath(path(L['courland']), M), base_hex, ca * 0.5)
    if gd > 0.01:   # warm inner light in the hypothetical
        wx, wy = cam.pt(*CITIES['Warsaw'])
        sp_ = skia.Paint(); sp_.setBlendMode(skia.BlendMode.kScreen)
        sp_.setShader(rad_grad(wx, wy, 700, [rgb('#ffd27a', 0.26 * gd * vis), rgb('#ffb347', 0.07 * gd * vis), rgb('#ff9a3c', 0)], [0, .5, 1]))
        c.clipPath(tpath(path(L['plt_pre72']), M), skia.ClipOp.kIntersect, True); c.drawPaint(sp_)
    c.restore()
    for n, (g, pw, d) in PIECES.items():
        k, h, kind = states[n]
        if k <= 0 and h <= 0: continue
        tc = rgb(PAL[pw])
        col = lerpc(base_col, (tc.fR, tc.fG, tc.fB), ease(seg(k, 0.25, 0.8)) if kind != 'fail' else 0.0)
        hexcol = '#%02x%02x%02x' % tuple(int(v * 255) for v in col)
        bp = tpath(path(g), M)
        if h > 0.01:
            c.drawPath(bp, fill(rgb('#000000', 0.45 * h * vis)))
            pp = tpath(path(g), A1.piece_matrix(M, g, d, h))
            sh_ = skia.Paint(Color4f=rgb('#000000', 0.65 * h * vis), AntiAlias=True); sh_.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 + 16 * h))
            c.save(); c.translate(10 * h, 22 * h); c.drawPath(pp, sh_); c.restore()
            c.drawPath(pp, fill(rgb('#0b0f14', 0.55 * vis)))
            A1.glass(c, pp, hexcol, 0.88 * vis)
            edge = '#ffe9b0' if kind == 'fail' else '#fff0cf'
            c.drawPath(pp, stroke(rgb(edge, 0.85 * h * vis), 2.0)); c.drawPath(pp, stroke(rgb('#ffcf7a', 0.45 * h * vis), 10, glow=10))
            if kind == 'fail' and h > 0.3:
                c.drawPath(bp, stroke(rgb('#ffe2a0', 0.8 * h * vis), 3, glow=3))
        else:
            e = emphasis(n, t)
            if e > 0: A1.glass(c, bp, hexcol, 0.80 * vis * e * (1 if gd < 0.5 else 0.6), 0.9 * vis * e, hexcol, 1.4)
            if e < 1 and not n.startswith('72'):   # 1772 gains already belong to the neighbours' 1791 outline
                ec = {'prussia': '#9ab8d8', 'russia': '#a9bf8f', 'habsburg': '#d6b48a'}[pw]
                A1.glass(c, bp, PAL[pw], 0.40 * vis * (1 - e), 0.5 * vis * (1 - e), ec, 1)
    # ---------------- outlines
    trace_k = eout(seg(t, 0.6, 3.0), 2) * (1 - seg(t, C('imagine'), C('imagine') + 0.6))
    A1.trace(c, tpath(outline(L['plt_pre72']), M), trace_k, w=3.0)
    k72 = states['72p'][0]; k93 = states['93p'][0]; k95 = states['95p'][0]
    gone = clamp(k95)
    cur = L['plt_pre72'] if k72 < 0.5 else (L['plt1773'] if k93 < 0.5 else L['rump1793'])
    if t > C('imagine') + 0.6 and gone < 1 and gd < 0.5:
        c.drawPath(tpath(outline(cur), M), stroke(rgb('#ffe6b0', 0.8 * (1 - gone) * vis), 2.0))
    if gone > 0 and gd < 0.5:
        c.drawPath(tpath(outline(L['plt_pre72'] if t < C('dangerously weak') else L['plt1773']), M), stroke(rgb('#e9d7b0', 0.5 * gone * vis), 1.8, dash=[8, 9]))
    if gd > 0.01:
        p = tpath(outline(PLT91), M)
        c.drawPath(p, stroke(rgb('#ffcf7a', 0.32 * gd * vis), 16, glow=14)); c.drawPath(p, stroke(rgb('#ffe6b0', gd * vis), 2.6, dash=[14, 8]))
    # re-ignition from Warsaw (hypothetical turn)
    ig = seg(t, C('may constitution') - 0.2, C('may constitution') + 1.6)
    if 0 < ig < 1:
        fr = path_nocache(Point(CITIES['Warsaw']).buffer(1_300_000 * eout(ig, 2), 96).boundary.intersection(PLT91.buffer(20e3)))
        fr = skia.Path(fr); fr.transform(M)
        c.drawPath(fr, stroke(rgb('#fff3d0', 0.9 * (1 - ig)), 3)); c.drawPath(fr, stroke(rgb('#ffbf5e', 0.7 * (1 - ig)), 16, glow=14))
    # ---------------- world overlays
    world_overlays(c, t, cam, M)
    # ---------------- clouds (hook descent; rise at 'remains on the map'; ending)
    cl = 1 - eout(seg(t, 0.0, 2.9), 1.6)
    cl = max(cl, 0.55 * win(t, C('remains on the map') - 0.4, C('19th century') + 0.4, 1.0, 1.2), 0.6 * win(t, C('cannot know') - 0.2, C('one possible path') + 1.0, 1.4, 1.4),
             keyed(t, [(0, 0), (C('a different world') - 0.5, 0), (C('what if poland', 290), 0.85), (DUR, 0.95)]))
    if cl > 0.01:
        ck = (t % 40) / 40
        for layer, (sc_, sp_, alpha) in enumerate(((1.0, 1.0, 0.95), (1.7, 1.6, 0.85))):
            grow = 1 + (sp_ * 2.6) * (eout(seg(t, 0, 2.9), 2) if t < 3 else 0.4 + 0.3 * np.sin(t * 0.05 + layer))
            c.save(); c.translate(W / 2, H * 0.55); c.scale(grow * sc_, grow * sc_)
            c.rotate(-8 + 4 * ck + layer * 25); c.translate(-W * 1.2 + 140 * (t % 30), -H * 0.9)
            p = skia.Paint(); p.setAlphaf(alpha * cl); c.drawImageRect(A1.CLOUD, skia.Rect(0, 0, W * 2.4, H * 1.8), SAMP, p); c.restore()
    # atmosphere
    hz = skia.Paint(); hz.setShader(lin_grad((0, 0), (0, 640), [rgb('#0a1219', 1.0), rgb('#0b1620', 0.6), rgb('#0b1620', 0.0)], [0, .45, 1]))
    c.drawRect(skia.Rect(0, 0, W, 640), hz)
    bb = skia.Paint(); bb.setShader(lin_grad((0, 1060), (0, 1620), [rgb('#05090d', 0.0), rgb('#05090d', 0.9 * seg(t, 3.5, 4.3))]))
    c.drawRect(skia.Rect(0, 1060, W, H), bb)
    # ---------------- screen overlays
    screen_overlays(c, t, cam)
    status_chip(c, t)
    year_counter(c, t)
    if t < 0.45: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', 1 - t / 0.45)))
    if t > DUR - 1.4: c.drawRect(skia.Rect(0, 0, W, H), fill(rgb('#000000', seg(t, DUR - 1.4, DUR - 0.1))))


def world_overlays(c, t, cam, M):
    sc = font('CormorantSC-SemiBold.ttf', 34)
    # neighbour names
    la = seg(t, 2.9, 3.8) * (1 - 0.6 * goldness(t)) * (1 - win(t, C('russia prussia and austria') - 0.4, C('in our timeline') + 0.4, 0.4, 0.6)) * (1 - win(t, C('first world war') - 0.2, C('what we do know'), 0.8, 0.8)) * (1 - seg(t, C('imagine looking') - 0.2, C('imagine looking') + 0.8))
    wlabel(c, cam, 16.6, 53.0, 'PRUSSIA', sc, rgb('#cfe0f2'), la, 8)
    wlabel(c, cam, 32.6, 56.6, 'RUSSIAN EMPIRE', sc, rgb('#d8e8c6'), la, 6)
    wlabel(c, cam, 19.5, 48.0, 'HABSBURG MONARCHY', sc, rgb('#f0d7b4'), la, 5)
    wlabel(c, cam, 18.3, 56.4, 'Baltic Sea', font('CG-MediumItalic.ttf', 40), rgb('#86b0c9'), la, 4)
    # hypothetical intro: the three powers named
    for nm, lon, lat, w0 in (('RUSSIA', 31.5, 54.5, 'russia prussia and austria'), ('PRUSSIA', 15.6, 53.1, 'prussia'), ('AUSTRIA', 21.0, 48.6, 'austria')):
        t0 = C(w0, 18.0)
        a = win(t, t0 - 0.1, C('in our timeline') + 0.2, 0.3, 0.6)
        wlabel(c, cam, lon, lat, nm, font('Cinzel-Bold.ttf', 46), rgb('#fff1dc'), a, 6, reveal=seg(t, t0 - 0.1, t0 + 0.5), glow=rgb('#ffb347', 0.25 * a))
    # Commonwealth name
    pla = win(t, 3.1, C('imagine') + 0.2, 0.9, 0.5) + win(t, C('once one') - 0.2, C('peoples') - 0.4, 0.8, 0.6)
    big = font('Cinzel-Bold.ttf', 31)
    wlabel(c, cam, 27.4, 51.3, 'POLISH–LITHUANIAN', big, rgb('#fff1dc'), pla, 7)
    wlabel(c, cam, 27.4, 51.3, 'COMMONWEALTH', big, rgb('#fff1dc'), pla, 9, dy=38)
    # Warsaw spotlight (Imagine ... Warsaw ... capitals)
    wa = win(t, C('warsaw') - 0.4, C('russia prussia and austria') + 0.4, 0.5, 0.7)
    if wa > 0:
        wx, wy = cam.pt(*CITIES['Warsaw'])
        for i in range(3):
            ring = ((t - C('warsaw')) * 0.5 + i / 3) % 1.0
            c.drawCircle(wx, wy, 14 + 120 * ring, stroke(rgb('#ffd590', 0.6 * wa * (1 - ring)), 2.2))
        c.drawCircle(wx, wy, 16, stroke(rgb('#ffcf7a', 0.6 * wa), 12, glow=12))
        wlabel(c, cam, 21.01, 52.23, 'WARSAW', font('Cinzel-Bold.ttf', 54), rgb('#fff1dc'), wa, 8, dy=-46, reveal=seg(t, C('warsaw') - 0.3, C('warsaw') + 0.6), glow=rgb('#ffb347', 0.35 * wa))
    capa = win(t, C('great political capitals') - 0.2, C('russia prussia and austria') - 0.2, 0.6, 0.6)
    for nm, side in CAPITALS:
        if capa > 0:
            A1.city(c, cam, nm, capa, t, side, C('great political capitals'))
            wline(c, M, (21.01, 52.23), [k for k in [(13.405, 52.52), (16.373, 48.208), (30.316, 59.939), (37.618, 55.756)]][[n for n, _ in CAPITALS].index(nm)],
                  seg(t, C('great political capitals'), C('great political capitals') + 1.4), rgb('#ffd98f'), 1.6, 0.12, capa * 0.7, dash=[8, 6])
    # cities: core set during documented & hypothetical map scenes
    ca = win(t, 1.9, C('imagine') + 0.4, 0.6, 0.4) + win(t, C('dangerously weak'), C('then came'), 0.8, 0.8) + win(t, C('alarmed'), C('imagine a different') + 3, 0.6, 0.8)
    ca += win(t, C('important nobles') - 0.3, C('threat'), 0.5, 0.6) + win(t, C('19th century') + 0.5, C('trade') - 0.3, 0.8, 0.8)
    ca = clamp(ca)
    if ca > 0:
        A1.city(c, cam, 'Warsaw', ca, t, 'r', 0)
        for nm, side in REGION: A1.city(c, cam, nm, ca * 0.9, t, side, 0.7)
    # area label (largest state)
    # peoples (documented) and (hypothetical) communities
    pa = win(t, C('peoples') - 0.2, C('dangerously weak') - 0.2, 0.4, 0.7)
    for i, (nm, lon, lat) in enumerate(PEOPLES):
        k = seg(t, C('peoples') + i * 0.28, C('peoples') + i * 0.28 + 0.6)
        wlabel(c, cam, lon, lat, nm, font('CG-MediumItalic.ttf', 40), rgb('#fff1dc'), pa * k, 1, reveal=k)
    seq = [('Polish', 'polish'), ('Lithuanian', 'lithuanian'), ('Ruthenian', 'ruthenian'), ('Jewish', 'jewish'), ('Armenian', 'other communities'), ('Tatar', 'other communities'), ('German', 'other communities'), ('Latvian', 'other communities')]
    ha = win(t, C('polish lithuanian ruthenian') - 0.3, C('bridge') - 0.3, 0.3, 0.8)
    pos = {n: (lo, la_) for n, lo, la_ in PEOPLES}
    for i, (nm, w0) in enumerate(seq):
        t0 = C(w0, 170) + (i - 4) * 0.15 * (i >= 4)
        k = seg(t, t0 - 0.1, t0 + 0.5)
        wlabel(c, cam, *pos[nm], nm, font('CG-MediumItalic.ttf', 42), rgb('#ffe3ad'), ha * k, 1, reveal=k, glow=rgb('#ffb347', 0.2 * ha * k))
    na = win(t, C('greatest challenge') - 0.2, C('bridge') - 0.3, 0.6, 0.8)
    if na > 0:   # weave: communities linked into one network (share power)
        names = [n for n, _ in seq]
        for i in range(len(names)):
            for j in (i + 1, i + 3):
                if j < len(names):
                    kk = seg(t, C('share power') - 2.0 + i * 0.25, C('share power') + i * 0.25)
                    wline(c, M, pos[names[i]], pos[names[j % len(names)]], kk, rgb('#ffcf7a'), 1.4, 0.15, na * 0.8)
    # Crown / Grand Duchy (documented names of the two parts; no internal line drawn)
    fa = win(t, C('enormous') - 0.3, C('polish lithuanian ruthenian'), 0.6, 0.8)
    wlabel(c, cam, 21.2, 50.7, 'CROWN OF POLAND', font('Cinzel-Bold.ttf', 34), rgb('#ffe3ad'), fa, 6, reveal=seg(t, C('federation') - 0.3, C('federation') + 0.5))
    wlabel(c, cam, 26.6, 54.4, 'GRAND DUCHY OF LITHUANIA', font('Cinzel-Bold.ttf', 30), rgb('#ffe3ad'), fa, 5, reveal=seg(t, C('federation'), C('federation') + 0.8))
    # distance rings (enormous territory)
    ra = win(t, C('enormous') - 0.2, C('polish lithuanian ruthenian') - 0.2, 0.6, 0.6)
    if ra > 0:
        wx, wy = CITIES['Warsaw']
        for i, km in enumerate((300, 600, 900)):
            k = seg(t, C('enormous') + i * 0.3, C('enormous') + i * 0.3 + 0.9)
            p = skia.Path(); p.addCircle(wx, wy, km * 1000 * eout(k)); p.transform(M)
            c.drawPath(p, stroke(rgb('#ffe3ad', 0.6 * ra), 1.4, dash=[6, 8]))
            x, y = cam.pt(wx + km * 1000 * eout(k) * 0.7071, wy - km * 1000 * eout(k) * 0.7071)
            text(c, f'{km} km', x + 8, y + 8, font('SourceSans3-SemiBold.ttf', 24), rgb('#ffe3ad', ra * k), align='l', spacing=2, shadow=rgb('#000000', 0.9))
    # 1792 invasion arrows (documented, schematic) and the hypothetical stopped arrows
    ia = win(t, C('intervened') - 0.2, C('reforms were defeated') + 1.0, 0.3, 0.8)
    warrow(c, M, [(32.0, 49.0), (29.0, 49.2), (25.6, 50.4)], seg(t, C('intervened'), C('intervened') + 1.6), rgb('#ff5a4e'), 7, ia)
    warrow(c, M, [(31.6, 55.8), (29.0, 55.6), (25.8, 54.6)], seg(t, C('intervened') + 0.3, C('intervened') + 1.9), rgb('#ff5a4e'), 7, ia)
    wlabel(c, cam, 30.6, 51.4, 'Russian army, May 1792', font('CG-MediumItalic.ttf', 32), rgb('#ffc9c2'), ia, 0.5)
    wlabel(c, cam, 30.6, 51.4, '(routes schematic)', font('SourceSans3-Regular.ttf', 22), rgb('#ffc9c2'), ia * 0.8, 1, dy=30)
    sa = win(t, C('far more costly') - 0.6, C('crisis') + 1.6, 0.3, 0.8)
    if sa > 0:
        for pts, o in (([(32.0, 49.0), (30.6, 49.3), (29.4, 49.9)], 0), ([(31.6, 55.8), (30.4, 55.7), (29.4, 55.3)], 0.3)):
            k = seg(t, C('far more costly') - 0.6 + o, C('far more costly') + 0.6 + o)
            warrow(c, M, pts, k, rgb('#ff5a4e'), 6, sa * 0.85)
            if k >= 1:
                x, y = cam.pt(*ll(*pts[-1])); rr_ = seg(t, C('far more costly') + 0.6 + o, C('far more costly') + 1.6 + o)
                c.drawCircle(x, y, 26 + 40 * rr_, stroke(rgb('#ffd27a', sa * (1 - rr_)), 3))
        c.drawPath(tpath(outline(PLT91), M), stroke(rgb('#ffe2a0', 0.35 * sa * (0.6 + 0.4 * np.sin(t * 6))), 7, glow=6))
    # army markers along the eastern frontier (hypothetical)
    am = win(t, C('stronger army') - 0.2, C('important nobles') + 1.6, 0.4, 0.8)
    if am > 0:
        b = PLT91.boundary
        for i in range(26):
            pt = b.interpolate(0.42 + i * 0.012, normalized=True)
            k = seg(t, C('stronger army') + i * 0.04, C('stronger army') + i * 0.04 + 0.4)
            x, y = cam.pt(pt.x, pt.y)
            pth = skia.Path(); pth.moveTo(x - 9, y + 4); pth.lineTo(x, y - 6); pth.lineTo(x + 9, y + 4)
            c.drawPath(pth, stroke(rgb('#ffe3ad', am * k), 3.2))
    # nobles network converging on Warsaw (hypothetical)
    nn = win(t, C('important nobles') - 0.2, C('diplomatic') + 1.2, 0.4, 0.8)
    for i, nm in enumerate(('Vilnius', 'Kraków', 'Lwów', 'Gdańsk', 'Grodno')):
        lon_lat = {'Vilnius': (25.28, 54.687), 'Kraków': (19.945, 50.065), 'Lwów': (24.031, 49.842), 'Gdańsk': (18.646, 54.352), 'Grodno': (23.829, 53.678)}[nm]
        wline(c, M, lon_lat, (21.01, 52.23), seg(t, C('important nobles') + i * 0.15, C('important nobles') + i * 0.15 + 0.9), rgb('#ffcf7a'), 2.0, 0.1, nn)
    # diplomatic arcs westward (hypothetical)
    da = win(t, C('diplomatic') - 0.2, C('threat'), 0.4, 0.8)
    for i, dst in enumerate(((5.0, 52.5), (7.0, 49.0), (9.5, 55.0))):
        wline(c, M, (21.01, 52.23), dst, seg(t, C('diplomatic') + i * 0.25, C('diplomatic') + i * 0.25 + 1.2), rgb('#ffd98f'), 2.0, -0.12, da, dash=[10, 7])
    wlabel(c, cam, 10.0, 51.8, 'European powers', font('CG-MediumItalic.ttf', 36), rgb('#ffe3ad'), da * seg(t, C('diplomatic') + 0.6, C('diplomatic') + 1.4), 0.5)
    # bridge: west -> east flow (hypothetical)
    ba = win(t, C('bridge') - 0.3, C('trade') + 0.4, 0.5, 0.8)
    if ba > 0:
        for j, lat in enumerate((50.2, 51.4, 52.6, 53.8, 55.0)):
            for i in range(14):
                u = ((t * 0.12 + i / 14 + j * 0.13) % 1.0)
                lon = lerp(10.0, 36.0, u)
                x, y = cam.pt(*ll(lon, lat + 0.35 * np.sin(u * 6 + j)))
                c.drawCircle(x, y, 3.2, stroke(rgb('#ffe3ad', ba * 0.9 * np.sin(np.pi * u)), 3, glow=3))
        wlabel(c, cam, 12.0, 53.5, 'WEST', font('Cinzel-Bold.ttf', 36), rgb('#ffe3ad'), ba, 8)
        wlabel(c, cam, 35.5, 53.5, 'EAST', font('Cinzel-Bold.ttf', 36), rgb('#ffe3ad'), ba, 8)
    # documented notes for trade / education / industry
    na = win(t, C('trade') - 0.2, C('stand still') - 0.3, 0.4, 0.6)
    for (lon, lat, s1, s2), w0 in (((18.65, 54.35, 'Gdańsk', 'Baltic grain port'), 'trade'), ((19.94, 50.06, 'Kraków Academy', 'founded 1364'), 'education'),
                                   ((25.28, 54.69, 'Vilnius University', 'founded 1579'), 'education')):
        k = seg(t, C(w0, 195) - 0.1, C(w0, 195) + 0.6)
        wlabel(c, cam, lon, lat, s1, font('CG-SemiBold.ttf', 34), rgb('#fff1dc'), na * k, 0.5, dy=-34, reveal=k)
        wlabel(c, cam, lon, lat, s2, font('SourceSans3-Regular.ttf', 24), rgb('#d9d2c2'), na * k, 1, dy=-6)
    # Prussia's real gains (our history) vs restrained (hypothetical)
    pr = win(t, C('prevent prussia') - 0.2, C('radically different') + 0.6, 0.5, 0.7)
    if pr > 0:
        rec = 1 - seg(t, C('prevent prussia') + 2.6, C('prevent prussia') + 4.6)
        for g in (L['loss72']['pru'], G['93_pru'], G['95_pru']):
            p = tpath(path(g), M)
            c.save(); c.clipPath(p, doAntiAlias=True)
            hp = skia.Paint(Color4f=rgb('#7fb0e0', 0.55 * pr * rec), StrokeWidth=2, Style=skia.Paint.kStroke_Style, AntiAlias=True)
            bx = c.getLocalClipBounds()
            for xx in np.arange(bx.left() - bx.height(), bx.right(), 16): c.drawLine(xx, bx.bottom(), xx + bx.height(), bx.top(), hp)
            c.restore(); c.drawPath(p, stroke(rgb('#9ec8f0', 0.8 * pr * rec), 1.6))
        wlabel(c, cam, 19.0, 53.6, 'Prussian gains 1772–1795', font('CG-SemiBold.ttf', 32), rgb('#d6e8fb'), pr * rec, 0.5)
        wlabel(c, cam, 19.0, 53.6, 'in our history', font('SourceSans3-SemiBold.ttf', 23), rgb('#d6e8fb'), pr * rec, 3, dy=30)
    # balance of power ring (hypothetical)
    bl = win(t, C('balance') - 0.2, C('limit russian') + 0.4, 0.5, 0.6)
    if bl > 0:
        for nm, lon, lat in (('Russia', 31.0, 55.0), ('Prussia', 16.0, 53.0), ('Austria', 18.5, 48.4)):
            wline(c, M, (24.6, 52.6), (lon, lat), seg(t, C('balance'), C('balance') + 1.0), rgb('#ffcf7a'), 2.2, 0.0, bl)
            wlabel(c, cam, lon, lat, nm.upper(), font('Cinzel-Bold.ttf', 36), rgb('#fff1dc'), bl, 6)
    # 'Europe today' (documented) + illustrative overlay of 1791 borders (hypothetical)
    ea = win(t, C('imagine looking') + 0.2, C('what if poland', 290), 0.8, 0.8)
    wlabel(c, cam, 13.0, 47.0, 'EUROPE TODAY', font('Cinzel-Bold.ttf', 34), rgb('#dfe9f2'), ea, 8)
    for nm, lon, lat in (('Poland', 19.2, 52.1), ('Lithuania', 23.9, 55.3), ('Belarus', 28.0, 53.5), ('Ukraine', 30.5, 49.2), ('Latvia', 25.4, 56.85), ('Germany', 10.5, 51.0)):
        wlabel(c, cam, lon, lat, nm, font('SourceSans3-Regular.ttf', 24), rgb('#c9d6e2'), ea * (1 - 0.4 * goldness(t)), 2)
    # modern borders label during the questions
    mq = win(t, C('borders of modern') + 0.2, C('cannot know') + 0.8, 0.6, 0.8)
    wlabel(c, cam, 30.5, 46.6, 'present-day borders', font('SourceSans3-SemiBold.ttf', 24), rgb('#c9d6e2'), mq, 3)


def screen_overlays(c, t, cam):
    # ---- hook title
    ha = seg(t, 0.35, 0.9) * (1 - seg(t, C('imagine') - 0.4, C('imagine') + 0.3))
    if ha > 0:
        yb = 360
        A1.gold_text(c, 'WHAT IF', W / 2, yb, font('Cinzel-Bold.ttf', 136), ha, seg(t, 0.2, 1.0), 18, seg(t, 1.0, 2.6))
        text(c, 'POLAND–LITHUANIA', W / 2, yb + 110, font('Cinzel-Bold.ttf', 76), rgb('#fff6e6', ha), spacing=6, reveal=seg(t, 0.6, 1.6), shadow=rgb('#000000', 0.9))
        text(c, 'had never been partitioned?', W / 2, yb + 184, font('CG-MediumItalic.ttf', 62), rgb('#eadfc8', ha), spacing=1, reveal=seg(t, 1.6, C('partitioned') + 0.5), shadow=rgb('#000000', 0.9))
        text(c, 'The empire that could have survived', W / 2, 1520, font('CG-MediumItalic.ttf', 46), rgb('#ffe3ad', ha), spacing=1, reveal=seg(t, C('empire') - 0.3, C('empire') + 1.0), shadow=rgb('#000000', 0.9))
    # ---- Imagine...
    card(c, t, C('imagine') + 0.3, C('warsaw') - 0.3, 'IMAGINE', ['Never erased', 'from the map'], None, 400, 'hyp', 76)
    card(c, t, C('great political capitals') - 0.1, C('russia prussia and austria') - 0.2, 'IMAGINE', ['Warsaw, a great', 'European capital'], None, 400, 'hyp', 70)
    # ---- in our timeline
    card(c, t, C('in our timeline'), C('different turn') - 0.3, 'IN OUR TIMELINE', ['It', 'disappeared'], 'at the end of | the 18th century', 400, 'doc', 80, x=92)
    plate(c, t, 'cake', C('in our timeline') + 0.4, C('different turn') - 0.2, 640, 380, 320, 487, 'The Twelfth Cake, 1773',
          'Le Mire after Moreau | satire of the First Partition', focus=(0.5, 0.45), z=(1.0, 1.12))
    card(c, t, C('different turn') - 0.4, C('alternative world') - 0.2, 'BUT', ['What if history', 'took another turn?'], None, 400, 'hyp', 74)
    card(c, t, C('alternative world') - 0.1, C('once one') - 1.0, 'RETURN TO', ['1791'], None, 400, 'doc', 96)
    card(c, t, C('once one') + 0.2, C('peoples') - 0.3, 'IN 1770', ['c. 730,000 km²'], 'one of the largest states in Europe', 400, 'doc', 84)
    # ---- weakness / liberum veto
    plate(c, t, 'elect', C('dangerously weak') - 0.4, C('powerful nobles') + 0.2, 92, 420, 896, 560, 'Royal election at Wola, 1764',
          'Bernardo Bellotto, painted 1778 · Royal Castle, Warsaw | Kings were elected by the nobility', focus=(0.5, 0.55), z=(1.05, 1.25), par=(40, -40), dolly=(0, 0.1))
    card(c, t, C('powerful nobles') - 0.1, C('neighboring monarchies') + 0.6, 'LIBERUM VETO', ['One deputy could', 'block the Sejm'], 'and paralyse every reform', 400, 'doc', 72)
    plate(c, t, 'cath', C('russia increasingly') - 0.3, C('prussia and austria', 60) + 0.2, 500, 410, 460, 600, 'Catherine II of Russia',
          'after Alexander Roslin, 1780s · Kunsthistorisches Museum, Vienna', focus=(0.5, 0.35), z=(1.0, 1.15), par=(25, -25), dolly=(0, 0.1))
    plate(c, t, 'fred', C('prussia and austria', 60) - 0.2, C('opportunities') + 1.6, 92, 420, 400, 540, 'Frederick II of Prussia', 'Johann Georg Ziesenis, 1763 | Sanssouci, Potsdam', focus=(0.5, 0.3), z=(1.0, 1.12))
    plate(c, t, 'mt', C('prussia and austria', 60) + 0.3, C('opportunities') + 1.6, 588, 420, 400, 540, 'Maria Theresa of Austria', 'Martin van Meytens, 1759 | Academy of Fine Arts, Vienna', focus=(0.5, 0.3), z=(1.0, 1.12))
    # ---- constitution
    card(c, t, C('then came') + 0.2, C('3rd') - 0.2, '', ['A moment that could', 'have changed everything'], None, 420, 'doc', 64)
    plate(c, t, 'const', C('3rd') - 0.3, C('first modern') + 0.3, 92, 380, 896, 640, 'The Constitution of 3 May 1791',
          'Kazimierz Wojniakowski, painted 1806 · National Museum, Warsaw', focus=(0.5, 0.55), z=(1.05, 1.35), par=(-60, 60), dolly=(0.0, 0.18))
    plate(c, t, 'matejko', C('first modern') - 0.2, C('strengthen') - 0.1, 92, 380, 896, 556, 'The king swears the Constitution, 3 May 1791',
          'after Jan Matejko, painted 1891 · Library of Congress', focus=(0.5, 0.5), z=(1.05, 1.22), par=(0, 0), dolly=(0, 0))
    card(c, t, C('new constitution') + 0.4, C('strengthen') - 0.1, '3 MAY 1791', [], 'One of the first modern written | constitutions in Europe', 1290, 'doc', 60)
    for i, (w0, s) in enumerate((('strengthen', 'A stronger central government'), ('limit', 'Liberum veto abolished'), ('reform the', 'Separation of powers'), ('collapse', 'Hereditary throne, to end royal elections'))):
        a = win(t, C(w0) - 0.2, C('brief moment') + 0.2, 0.4, 0.5)
        y = 430 + i * 92
        if a > 0:
            c.drawCircle(110, y - 14, 7, fill(rgb('#e6c27d', a)))
            text(c, s, 136, y, font('CG-SemiBold.ttf', 50), rgb('#fbf3e3', a), align='l', reveal=seg(t, C(w0) - 0.2, C(w0) + 0.6), shadow=rgb('#000000', 0.9))
    plate(c, t, 'king', C('brief moment') - 0.3, C('alarmed') + 0.4, 270, 390, 540, 760, 'Stanisław August, King of Poland',
          'Marcello Bacciarelli, 1764 · Royal Castle, Warsaw', focus=(0.47, 0.22), z=(1.0, 1.3), par=(30, -30), dolly=(0, 0.12))
    # ---- intervention
    card(c, t, C('targovica') - 0.4, C('in 1793') - 0.1, 'APRIL–MAY 1792', ['Targowica', 'Confederation'], 'Magnates opposed to the reforms | turned to Catherine II', 400, 'doc', 76)
    plate(c, t, 'cath', C('in 1793') - 0.2, C('two years later') + 0.1, 130, 380, 330, 420, 'Catherine II', 'Russia', focus=(0.5, 0.3), z=(1.0, 1.1), ts=32)
    plate(c, t, 'fw2', C('in 1793') + 0.3, C('two years later') + 0.1, 620, 380, 330, 420, 'Frederick William II', 'Prussia · engraving after Bornet', focus=(0.5, 0.33), z=(1.0, 1.1), ts=32)
    for i, (k_, nm, sub) in enumerate((('cath', 'Catherine II', 'Russia'), ('fw2', 'Frederick William II', 'Prussia'), ('fr2', 'Francis II', 'Austria · Ketterlinus, 1792'))):
        plate(c, t, k_, C('two years later') + 0.2 + i * 0.35, C('third partition') + 0.5, 92 + i * 312, 380, 270, 360, nm, sub.split(' · ')[0], focus=(0.5, 0.32), z=(1.0, 1.08), ts=26)
    card(c, t, C('commonwealth disappeared') - 0.2, C('imagine a different') - 0.3, '1795', ['The Commonwealth', 'disappeared'], None, 400, 'doc', 80)
    # ---- alternative
    card(c, t, C('imagine a different') - 0.1, C('move') - 0.2, 'BUT NOW', ['Imagine a', 'different outcome'], None, 400, 'hyp', 78)
    card(c, t, C('move') - 0.3, C('threat') - 0.3, 'IN THIS ALTERNATE TIMELINE', ['The reformers', 'move faster'], 'A stronger army · loyal nobles | diplomatic backing', 400, 'hyp', 74)
    plate(c, t, 'kosc', C('stronger army') - 0.3, C('important nobles') + 0.3, 600, 640, 340, 400, 'Tadeusz Kościuszko',
          'fought for the Commonwealth in 1792 and 1794 | engraving c. 1820 · Library of Congress', focus=(0.5, 0.4), z=(1.0, 1.1))
    for i, (w0, s) in enumerate((('military preparation', 'Military preparation'), ('political', 'Political unity'), ('international', 'International pressure'))):
        a = win(t, C(w0, 136) - 0.2, C('crisis') - 0.2, 0.3, 0.5)
        if a > 0: A1.gold_text(c, s, W / 2, 470 + i * 84, font('CG-SemiBold.ttf', 62), a, seg(t, C(w0, 136) - 0.2, C(w0, 136) + 0.6), 0.5, seg(t, C(w0, 136), C(w0, 136) + 1.5))
    card(c, t, C('crisis') + 0.2, C('second partition never') - 0.4, 'IN THIS ALTERNATE 1792', ['The new system', 'holds'], None, 400, 'hyp', 76)
    rem = win(t, C('remains on the map') - 0.3, C('19th century') + 0.2, 0.5, 0.6)
    if rem > 0:
        A1.gold_text(c, 'STILL ON', W / 2, 470, font('Cinzel-Bold.ttf', 110), rem, seg(t, C('remains on the map') - 0.3, C('remains on the map') + 0.5), 12, seg(t, C('remains on the map'), C('remains on the map') + 1.8))
        A1.gold_text(c, 'THE MAP', W / 2, 590, font('Cinzel-Bold.ttf', 110), rem, seg(t, C('remains on the map') - 0.1, C('remains on the map') + 0.7), 12, seg(t, C('remains on the map') + 0.2, C('remains on the map') + 2.0))
    # ---- 19th century
    plate(c, t, 'rizzi', C('19th century') - 0.2, C('constitutional monarchy') - 0.2, 92, 380, 896, 560, 'Carte de la Pologne, 1772',
          'Giovanni Antonio Rizzi-Zannoni · Library of Congress', focus=(0.5, 0.5), z=(1.05, 1.3), par=(0, 0), dolly=(0, 0))
    plate(c, t, 'lotter', C('federation') - 0.3, C('enormous') - 0.2, 320, 670, 440, 384, 'Grand Duchy of Lithuania, c. 1778',
          'Tobias Conrad Lotter, Augsburg · Library of Congress', focus=(0.5, 0.5), z=(1.0, 1.2), par=(0, 0), dolly=(0, 0))
    card(c, t, C('constitutional monarchy') - 0.3, C('enormous') - 0.3, 'IN THE 19TH CENTURY', ['A constitutional', 'monarchy?'], 'or a federation with a stronger parliament', 400, 'hyp', 72)
    card(c, t, C('enormous') - 0.2, C('polish lithuanian ruthenian') - 0.3, '', ['Hard to govern'], 'more than 1,000 km from west to east', 420, 'hyp', 76)
    card(c, t, C('recognition') - 1.2, C('greatest challenge') - 0.2, 'MANY PEOPLES', ['Rights and', 'recognition'], None, 400, 'hyp', 74)
    card(c, t, C('greatest challenge') - 0.1, C('bridge') - 0.3, 'THE GREATEST CHALLENGE', ['Sharing power'], 'between different peoples', 400, 'hyp', 80)
    card(c, t, C('bridge') - 0.2, C('trade') - 0.2, 'A BRIDGE', ['Between West', 'and East'], None, 400, 'hyp', 78)
    card(c, t, C('trade') - 0.2, C('vilnius') - 0.6, '', ['Trade · Education', 'Industry'], None, 400, 'hyp', 70)
    plate(c, t, 'plan', C('warsaw', 201) - 0.8, C('vilnius') + 0.7, 92, 360, 896, 590, 'Plan de Varsovie, 1772',
          'Rizzi-Zannoni atlas of Poland · Library of Congress', focus=(0.5, 0.5), z=(1.1, 1.45), par=(0, 0), dolly=(0, 0))
    # ---- Europe would not stand still
    card(c, t, C('stand still') - 0.4, C('napoleon') - 0.1, '', ['Europe would not', 'stand still'], None, 420, 'hyp', 76)
    plate(c, t, 'napo', C('napoleon') - 0.3, C('revolutions') + 0.2, 530, 400, 430, 620, 'Napoleon Bonaparte',
          'as First Consul, print c. 1800 | Library of Congress', focus=(0.5, 0.3), z=(1.0, 1.2), par=(20, -20), dolly=(0, 0.1))
    card(c, t, C('napoleon') + 0.2, C('revolutions') - 0.2, 'STILL', ['Napoleon', 'rises'], None, 430, 'hyp', 74, x=92)
    for i, s in enumerate(('Revolutions', 'Nationalism', 'New conflicts')):
        w0 = ('revolutions', 'nationalism', 'new conflicts')[i]
        a = win(t, C(w0, 214) - 0.2, C('neutral') - 0.6, 0.3, 0.5)
        if a > 0: text(c, s, W / 2, 480 + i * 92, font('Cinzel-Bold.ttf', 66), rgb('#fff1dc', a), spacing=4, reveal=seg(t, C(w0, 214) - 0.2, C(w0, 214) + 0.5), shadow=rgb('#000000', 0.9))
    for i, (w0, s) in enumerate((('neutral', 'Neutral'), ('alliances', 'Alliances'), ('major power', 'A great power'))):
        a = win(t, C(w0, 220) - 0.2, C('balance') - 0.4, 0.3, 0.5)
        if a > 0:
            y = 460 + i * 100
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(220, y - 66, 640, 88), 8, 8)
            c.drawRRect(r, fill(rgb('#1b1406', 0.75 * a))); c.drawRRect(r, stroke(rgb('#f0cd86', a), 1.6, dash=[10, 7]))
            A1.gold_text(c, s, W / 2, y, font('CG-SemiBold.ttf', 56), a, seg(t, C(w0, 220) - 0.2, C(w0, 220) + 0.5), 0.5, seg(t, C(w0, 220), C(w0, 220) + 1.4))
    card(c, t, C('limit russian') - 0.2, C('prevent prussia') - 0.3, 'PERHAPS', ['Less Russian', 'influence'], 'in Central Europe', 400, 'hyp', 76)
    card(c, t, C('radically different') - 0.5, C('first world war') - 0.4, '', ['A radically', 'different map'], None, 420, 'hyp', 76)
    # ---- questions
    for i, (w0, lines, nxt) in enumerate((('first world war', ['Would the', 'First World War', 'still happen?'], 'germany and russia'),
                                          ('germany and russia', ['Would Germany', 'and Russia develop', 'the same way?'], 'borders of modern'),
                                          ('borders of modern', ['Would modern', 'Eastern Europe’s borders', 'ever exist?'], 'cannot know'))):
        a = win(t, C(w0) - 0.5, C(nxt) - 0.3, 0.4, 0.5)
        for j, ln in enumerate(lines):
            if a > 0: text(c, ln, W / 2, 520 + j * 96, font('CG-SemiBold.ttf', 84 if j == 1 else 64), rgb('#fff1dc', a), spacing=0.5,
                           reveal=seg(t, C(w0) - 0.5 + j * 0.15, C(w0) + 0.4 + j * 0.15), shadow=rgb('#000000', 0.95))
    cq = win(t, C('cannot know') - 0.2, C('what we do know') - 0.3, 0.4, 0.6)
    if cq > 0:
        A1.gold_text(c, 'We cannot know', W / 2, 560, font('CG-SemiBold.ttf', 96), cq, seg(t, C('cannot know') - 0.2, C('cannot know') + 0.6), 1, seg(t, C('cannot know'), C('cannot know') + 2.0))
        fk = seg(t, C('one possible path') - 1.4, C('one possible path') + 1.0)   # the fork
        if fk > 0:
            p = skia.Path(); p.moveTo(W / 2, 700); p.lineTo(W / 2, 860)
            q = skia.Path(); q.moveTo(W / 2, 860); q.lineTo(W / 2, 1060)
            r = skia.Path(); r.moveTo(W / 2, 860); r.cubicTo(W / 2, 940, W / 2 + 220, 920, W / 2 + 240, 1060)
            for pp, col, dsh in ((p, '#fff1dc', None), (q, '#fff1dc', None), (r, '#ffcf7a', [12, 9])):
                sp = stroke(rgb(col, cq), 3.2, dash=dsh)
                if fk < 1: sp.setPathEffect(skia.PathEffect.MakeCompose(skia.DashPathEffect.Make(dsh, 0), skia.TrimPathEffect.Make(0, max(fk, 1e-3))) if dsh else skia.TrimPathEffect.Make(0, max(fk, 1e-3)))
                c.drawPath(pp, sp)
            text(c, 'what happened', W / 2 - 24, 1040, font('SourceSans3-SemiBold.ttf', 26), rgb('#fff1dc', cq * seg(fk, 0.6, 1)), align='r', spacing=3)
            text(c, 'one possible path', W / 2 + 270, 1040, font('SourceSans3-SemiBold.ttf', 26), rgb('#ffd98f', cq * seg(fk, 0.6, 1)), align='l', spacing=3)
    # ---- what we do know
    card(c, t, C('what we do know') - 0.1, C('lacked a future') - 1.0, 'WHAT WE DO KNOW', ['It did not lack', 'a future'], None, 400, 'doc', 76)
    plate(c, t, 'sayer', C('lacked a future') - 1.2, C('political weakness') - 0.2, 92, 380, 896, 660, 'The Kingdom of Poland with its dismembered provinces',
          'Robert Sayer, London, 1787', focus=(0.5, 0.5), z=(1.05, 1.3), par=(0, 0), dolly=(0, 0))
    for i, (w0, s) in enumerate((('political weakness', 'Political weakness'), ('foreign intervention', 'Foreign intervention'), ('ambitions', 'Imperial ambition'))):
        a = win(t, C(w0) - 0.2, C('imagine looking') - 0.4, 0.3, 0.6)
        if a > 0: text(c, s, W / 2, 470 + i * 96, font('Cinzel-Bold.ttf', 62), rgb('#fff1dc', a), spacing=3, reveal=seg(t, C(w0) - 0.2, C(w0) + 0.5), shadow=rgb('#000000', 0.95))
    # ---- Europe today
    card(c, t, C('still there') - 0.4, C('age of partitions') - 0.2, 'ILLUSTRATION · 1791 BORDERS', ['Still there'], None, 400, 'hyp', 96)
    card(c, t, C('age of partitions') - 0.2, C('a different central') - 0.2, '', ['It survived the', 'Age of Partitions'], None, 400, 'hyp', 74)
    card(c, t, C('a different central') - 0.1, C('a different world') - 0.2, '', ['A different', 'Central Europe'], None, 400, 'hyp', 80)
    dw = win(t, C('a different world') - 0.1, C('what if poland', 290) - 0.2, 0.4, 0.5)
    if dw > 0: A1.gold_text(c, 'A different world', W / 2, 520, font('CG-SemiBold.ttf', 96), dw, seg(t, C('a different world') - 0.1, C('a different world') + 0.7), 1, seg(t, C('a different world'), C('a different world') + 2))
    # ---- closing title
    t0 = C('what if poland', 290); ca = win(t, t0 - 0.2, DUR + 2, 0.6, 0.1)
    if ca > 0:
        A1.gold_text(c, 'WHAT IF', W / 2, 640, font('Cinzel-Bold.ttf', 136), ca, seg(t, t0 - 0.2, t0 + 0.6), 18, seg(t, t0 + 0.4, t0 + 2.4))
        text(c, 'POLAND–LITHUANIA', W / 2, 750, font('Cinzel-Bold.ttf', 76), rgb('#fff6e6', ca), spacing=6, reveal=seg(t, t0 + 0.2, t0 + 1.2), shadow=rgb('#000000', 0.9))
        text(c, 'had never been partitioned?', W / 2, 824, font('CG-MediumItalic.ttf', 62), rgb('#eadfc8', ca), spacing=1, reveal=seg(t, t0 + 0.8, t0 + 2.0), shadow=rgb('#000000', 0.9))
        q = C('completely different place') - 2.4
        text(c, 'Would Europe be a completely different place?', W / 2, 1000, font('CG-MediumItalic.ttf', 44), rgb('#ffe3ad', ca), reveal=seg(t, q, q + 1.4), shadow=rgb('#000000', 0.9))


POST = Post(grain=0.02, vignette=0.55, bloom=0.5, halation=0.35, ca=0.0016, shoulder=0.15, seed=21)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--t0', type=float, default=0); ap.add_argument('--t1', type=float, default=DUR)
    ap.add_argument('--out', default=f'{ROOT}/render/film_video.mp4'); ap.add_argument('--mb', type=int, default=4); ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    render(scene, DUR, a.out, POST, frames=list(range(int(round(a.t0 * FPS)), int(round(a.t1 * FPS)))), mb=a.mb, workers=a.workers, scene_mod='film')
