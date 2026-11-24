"""TikTok profile pictures (1080x1080, circle-safe), in the film's historical-atlas style."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skia
import atlas as A
from atlas import C, PAL, layers, PATHS, Camera, fill, stroke, ribbon, hatch, xy, parchment
from map_stages import POW, lighten, darken

S = 1080; R = S / 2
OUT = os.path.join(A.ROOT, 'branding')

def gold_ring(cv, r, w, alpha=1.0):
    gold = skia.GradientShader.MakeSweep(R, R, [C('#8A6A2E'), C('#EBD291'), C('#7A5A22'), C('#F2DC9C'), C('#8A6A2E')])
    cv.drawCircle(R, R, r, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=w, Shader=gold, Alphaf=alpha))

def map_layer(cv, cam_center, scale):
    """Render the 1795 division map with the 1772 Commonwealth outline into a 1080 square (camera in px/km)."""
    L = layers(); st = L['stages']['1795']; g = L['gains']; l72 = L['loss72']
    x, y = xy(*cam_center); s = scale / 1000.0
    cv.save(); cv.translate(R, R); cv.scale(s, -s); cv.translate(-x, -y)
    cam = Camera(x, y, scale)
    fill(cv, PATHS.get_path('worldbox', A.box(-3e6, -3e6, 3e6, 3e6)), PAL['sea'])
    for i, (d, gg) in enumerate(L['ripples']):
        stroke(cv, cam, PATHS.get_path(f'rip{d}', gg), PAL['sea_line'], 1.4, 0.4 - i * 0.06)
    fill(cv, PATHS.get_path('land', L['land']), PAL['paper'])
    for k in ('other', 'hre', 'saxony', 'sweden', 'denmark', 'ottoman'):
        if k in st: fill(cv, PATHS.get_path('p_' + k, st[k]), PAL['neutral'], 0.9)
    for k, pw in (('russia95', 'russia'), ('prussia95', 'prussia')):
        p = PATHS.get_path('p_' + k, st[k]); fill(cv, p, PAL[POW[pw][0]]); ribbon(cv, cam, PATHS.get_ext('p_' + k, st[k]), PAL[POW[pw][1]], 20, 0.5)
    p = PATHS.get_path('p_h', L['stages']['1793']['habsburg']); fill(cv, p, PAL['austria']); ribbon(cv, cam, PATHS.get_ext('p_h', L['stages']['1793']['habsburg']), PAL['austria_edge'], 20, 0.5)
    tones = {'72': -0.1, '93': 0.22, '95': 0.45}
    for key, geom, pw, yr in [('l72pru', l72['pru'], 'prussia', '72'), ('l72rus', l72['rus'], 'russia', '72'), ('l72aut', l72['aut'], 'habsburg', '72'),
                              ('g93_pru', g['93_pru'], 'prussia', '93'), ('g93_rus', g['93_rus'], 'russia', '93'),
                              ('g95_pru', g['95_pru'], 'prussia', '95'), ('g95_rus', g['95_rus'], 'russia', '95'),
                              ('g95_rus_courland', g['95_rus_courland'], 'russia', '95'), ('g95_aut', g['95_aut'], 'habsburg', '95')]:
        col = darken(PAL[POW[pw][0]], 0.1) if yr == '72' else lighten(PAL[POW[pw][0]], tones[yr])
        fill(cv, PATHS.get_path(key, geom), col); stroke(cv, cam, PATHS.get_path(key, geom), PAL['ink'], 1.2, 0.3, dash=[5, 6])
    stroke(cv, cam, PATHS.get_path('land', L['land']), '#5E716E', 1.6, 0.8)
    # glowing gold outline of the 1772 Commonwealth
    o = PATHS.get_path('plt_pre72', L['plt_pre72'])
    cv.drawPath(o, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=cam.px(16), StrokeJoin=skia.Paint.kRound_Join,
                              Color4f=skia.Color4f(0.95, 0.78, 0.36, 0.55), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10, False)))
    stroke(cv, cam, o, PAL['plt_edge'], 5.0, 1.0); stroke(cv, cam, o, '#F6E3AE', 1.8, 0.95)
    cv.restore()

def variant_map():
    s = skia.Surface(S, S); cv = s.getCanvas()
    map_layer(cv, (24.0, 52.6), 0.74)
    cv.drawImage(parchment(seed=4, w=S + 240, h=S + 240), -120, -120, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kMultiply, Alphaf=0.45))
    sh = skia.GradientShader.MakeRadial(skia.Point(R, R), R, [skia.Color4f(0, 0, 0, 0), skia.Color4f(0.16, 0.1, 0.05, 0.55)], [0.62, 1.0])
    cv.drawRect(skia.Rect(0, 0, S, S), skia.Paint(Shader=sh))
    gold_ring(cv, R - 26, 16); gold_ring(cv, R - 48, 3, 0.8)
    return s

def variant_silhouette():
    s = skia.Surface(S, S); cv = s.getCanvas()
    sh = skia.GradientShader.MakeRadial(skia.Point(R, R * 0.9), R * 1.1, [C('#2E2418'), C('#15100B')])
    cv.drawRect(skia.Rect(0, 0, S, S), skia.Paint(Shader=sh))
    L = layers(); g = L['gains']; l72 = L['loss72']
    x, y = xy(24.2, 52.75); scale = 0.60; sc = scale / 1000.0; cam = Camera(x, y, scale)
    cv.save(); cv.translate(R, R + 10); cv.scale(sc, -sc); cv.translate(-x, -y)
    # faint engraved land and coastline for context
    land = PATHS.get_path('land', L['land'])
    fill(cv, land, skia.Color4f(0.27, 0.21, 0.14, 1))
    for i, (d, gg) in enumerate(L['ripples'][:3]):
        stroke(cv, cam, PATHS.get_path(f'rip{d}', gg), '#D9B86A', 1.6, 0.16 - i * 0.04)
    stroke(cv, cam, land, '#D9B86A', 1.6, 0.35)
    # the 1772 Commonwealth: gold with shading
    o = PATHS.get_path('plt_pre72', L['plt_pre72'])
    cv.drawPath(o, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0, 0, 0, 0.6), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18, False)))
    b = o.computeTightBounds()
    gold = skia.GradientShader.MakeLinear([skia.Point(b.left(), b.bottom()), skia.Point(b.right(), b.top())],
                                          [C('#F3DC98'), C('#D4AE5C'), C('#A8813A')], [0, 0.55, 1])
    cv.drawPath(o, skia.Paint(AntiAlias=True, Shader=gold))
    # partition lines engraved into the gold: 1772 / 1793 / 1795 shares
    for key, geom in [('l72pru', l72['pru']), ('l72rus', l72['rus']), ('l72aut', l72['aut']), ('g93_pru', g['93_pru']), ('g93_rus', g['93_rus']),
                      ('g95_pru', g['95_pru']), ('g95_rus', g['95_rus']), ('g95_rus_courland', g['95_rus_courland']), ('g95_aut', g['95_aut'])]:
        stroke(cv, cam, PATHS.get_path(key, geom), '#4A3518', 3.4, 0.9)
    stroke(cv, cam, o, '#5A4018', 4.0, 1.0)
    cv.restore()
    gold_ring(cv, R - 26, 16); gold_ring(cv, R - 48, 3, 0.8)
    cv.drawImage(parchment(seed=9, w=S + 240, h=S + 240), -120, -120, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kOverlay, Alphaf=0.22))
    return s

def variant_compass():
    s = skia.Surface(S, S); cv = s.getCanvas()
    sh = skia.GradientShader.MakeRadial(skia.Point(R, R * 0.9), R * 1.1, [C('#2E2418'), C('#15100B')])
    cv.drawRect(skia.Rect(0, 0, S, S), skia.Paint(Shader=sh))
    gold = C('#D9B86A')
    # engraved meridians / parallels (globe)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.2, Color4f=skia.Color4f(gold.fR, gold.fG, gold.fB, 0.33))
    gr = 330
    cv.drawCircle(R, R, gr, p)
    for k in range(1, 6):
        w = gr * math.cos(math.radians(k * 15)) if False else gr * (1 - k / 6)
        cv.drawOval(skia.Rect(R - w, R - gr, R + w, R + gr), p)
    for k in range(-4, 5):
        yy = R + gr * k / 5; hw = math.sqrt(max(gr * gr - (yy - R) ** 2, 0))
        cv.drawLine(R - hw, yy, R + hw, yy, p)
    # compass rose
    def star(n, r1, r2, rot, col, a):
        path = skia.Path()
        for i in range(2 * n):
            ang = math.radians(rot + i * 180 / n); r = r1 if i % 2 == 0 else r2
            pt = (R + r * math.sin(ang), R - r * math.cos(ang))
            path.moveTo(*pt) if i == 0 else path.lineTo(*pt)
        path.close()
        cv.drawPath(path, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(col.fR, col.fG, col.fB, a)))
    star(8, 300, 60, 22.5, C('#9C7B3A'), 0.85)
    star(4, 420, 70, 0, C('#E8CC84'), 1.0)
    # half-shading of the main points (engraved look)
    for i in range(4):
        ang = math.radians(i * 90); path = skia.Path()
        path.moveTo(R, R); path.lineTo(R + 420 * math.sin(ang), R - 420 * math.cos(ang))
        a2 = math.radians(i * 90 + 45); path.lineTo(R + 70 * math.sin(a2), R - 70 * math.cos(a2)); path.close()
        cv.drawPath(path, skia.Paint(AntiAlias=True, Color4f=skia.Color4f(0.45, 0.33, 0.13, 0.8)))
    cv.drawCircle(R, R, 46, skia.Paint(AntiAlias=True, Color4f=C('#15100B')))
    cv.drawCircle(R, R, 46, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color4f=gold))
    cv.drawCircle(R, R, 14, skia.Paint(AntiAlias=True, Color4f=gold))
    f = A.font('caps_bold', 54)
    A.draw_text(cv, 'N', R, R - 438, f, '#F2DC9C', align='center')
    cv.drawImage(parchment(seed=9, w=S + 240, h=S + 240), -120, -120, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kOverlay, Alphaf=0.25))
    gold_ring(cv, R - 26, 16); gold_ring(cv, R - 48, 3, 0.8)
    return s

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (('profile_A_commonwealth_gold.png', variant_silhouette), ('profile_B_compass_rose.png', variant_compass)):
        surf = fn(); surf.makeImageSnapshot().save(os.path.join(OUT, name), skia.kPNG); print('saved', name)
