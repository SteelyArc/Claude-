"""PHASE 4 — full documentary, synchronised to the complete, unaltered narration (418.93 s).
Shots are keyed to word timestamps from research/transcript_words.json (times below = narration seconds).

usage: film.py render [workers]   -> previews/final/chunks/*.mp4 + video.mp4
       film.py stills t1 t2 ...   -> QC stills
"""
import sys, os, glob, re, subprocess, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preview_phase3 as P
from map_stages import *
from fx import *
import numpy as np
from multiprocessing import Pool

FPS = 30
END = 419.5                          # narration 418.93 s + short tail
N = int(round(END * FPS))
ARC = os.path.join(ROOT, 'assets', 'archive')

def commons_name(title):
    fn = re.sub(r'[^A-Za-z0-9._-]+', '_', title)[:80]
    return fn.rsplit('.', 1)[0]

def asset(*cands):
    """First existing file among candidates (Commons-title prefixes or exact names)."""
    for c in cands:
        exact = os.path.join(ARC, c)
        if os.path.exists(exact) and os.path.getsize(exact) > 1000: return load_image(exact)
        m = [f for f in glob.glob(os.path.join(ARC, commons_name(c)[:45] + '*')) if os.path.getsize(f) > 1000]
        if m: return load_image(sorted(m)[0])
    return None

A = {
    'lotter': lambda: asset('Lotter_1778_Magnus_Ducatus_Lithuaniae_LOC.jpg'),
    'bellotto': lambda: asset('Bernardo Bellotto - View of Warsaw from the Royal Castle - Google Art Project.jpg'),
    'manuscript': lambda: asset('Konstytucja 3 maja rekopis 1.jpg'),
    'matejko_const': lambda: asset('Jan Matejko - Konstytucja 3 maja 1791.jpg'),
    'oath': lambda: asset('Michał Stachowicz - Tadeusz Kościuszko’s Oath on the Kraków Main Square.jpg'),
    'raclawice': lambda: asset('Jan Matejko - Kościuszko at Racławice - MNK II-a-151 - National Museum Kraków.jpg'),
    'maciejowice': lambda: asset('Plersch Kościuszko in the battle of Maciejowice.jpg'),
    'kosciuszko': lambda: asset('Tadeusz Kościuszko (1793, Joseph Grassi).jpg', 'LOC_Kosciuszko_picture.jpg'),
    'laurie': lambda: asset('1794 Laurie and Whittle Map of Poland and Lithuania after Second Partition - Geographicus - Poland-lauriewhittle-1794.jpg'),
    'cary': lambda: asset('A new map of Poland, and the Grand Duchy of Lithuania, shewing their dismemberments and divisions between Austria (IA dr a-new-map-of-poland-and-the-grand-duchy-of-lithuania-shewing-their-dismem-00644021).jpg'),
    'grodno_map': lambda: asset('LOC_Grodno_Governorate_map_c1800.jpg'),
    'catherine': lambda: asset('LOC_Catherine_II_Townley_picture.jpg'),
    'king': lambda: asset('LOC_Stanislaus_II_Augustus_Fogg_after_Bacciarelli_picture.jpg'),
}
def img(k): return A[k]()
def kosc_is_painting():
    return any(os.path.getsize(f) > 1000 for f in glob.glob(os.path.join(ARC, commons_name('Tadeusz Kościuszko (1793, Joseph Grassi).jpg')[:45] + '*')))

SRC_MAP = 'Borders: OpenHistoricalMap (CC0), verified against atlas reference · Physical: Natural Earth'
def arr(s):
    im = s.makeImageSnapshot(); a = im.toarray()
    if im.colorType() == skia.kBGRA_8888_ColorType: a = a[..., [2, 1, 0, 3]]
    return np.ascontiguousarray(a[..., :3])
def pulse(a, t0, t1):  # 0 -> 1 -> 0 envelope
    return eseg(a, t0, t0 + 0.8) * (1 - eseg(a, t1 - 0.8, t1))

# =============================================================== generic shot builders
def doc(a, im, t0, t1, focus, z1, caption_text, heading=None, sub=None, desat=0.0, bright=1.0, card=None, kw=None):
    s = new_surface(); cv = s.getCanvas(); dark_desk(cv)
    if im is not None:
        document(cv, im, seg(a, t0, t1), focus=focus, zoom0=1.0, zoom1=z1, tilt0=0.33, settle=(0.0, 0.45), sweep=(0.2, 0.7),
                 desat=desat, bright=bright, cy_frac=0.55)
    al = eseg(a, t0 + 0.3, t0 + 1.2)
    if heading:
        draw_text(cv, heading, W / 2, 250, font('caps', 44), '#E7D3A2', align='center', tracking=0.3, alpha=al, shadow=True)
    if sub:
        draw_text(cv, sub, W / 2, 325, font('serif_bold', 58), '#F4EAD2', align='center', alpha=al, shadow=True)
    if card: date_card(cv, *card[:3], seg(a, card[3], card[3] + 0.8), y=300)
    if kw: dark_band(cv, kw[2] - 120, kw[2] + 90, 0.7 * eseg(a, kw[1], kw[1] + 0.8)); keyword(cv, kw[0], seg(a, kw[1], kw[1] + 0.8), kw[2])
    caption(cv, caption_text, alpha=0.95 * al, y=1585, dark=True)
    vignette(cv, 0.5); film_grain(cv, int(a * FPS), 0.05); return s

def painting(a, im, t0, t1, p0, p1, z0, z1, caption_text, card=None, kws=(), desat=0.0, bright=1.0, tint=0.0):
    s = new_surface(); cv = s.getCanvas(); cv.drawColor(C('#1E1610'))
    if im is not None:
        painting_shot(cv, im, seg(a, t0, t1), p0, p1, z0, z1, desat=desat, bright=bright, tint=tint)
    dust(cv, a, alpha=0.25)
    if card: date_card(cv, *card[:3], seg(a, card[3], card[3] + 0.8), y=330)
    for text, tk, y in kws:
        dark_band(cv, y - 120, y + 90, 0.7 * eseg(a, tk, tk + 0.8)); keyword(cv, text, seg(a, tk, tk + 0.8), y)
    caption(cv, caption_text, alpha=0.9 * eseg(a, t0 + 0.4, t0 + 1.2), y=1585, dark=True)
    vignette(cv, 0.55); film_grain(cv, int(a * FPS), 0.05); return s

def portrait(a, im, t0, t1, face, name, sub, caption_text, cards=(), tint=0.9, push=(1.0, 1.10)):
    s = new_surface(); cv = s.getCanvas(); cv.drawColor(C('#1E1610'))
    if im is not None:
        parallax_portrait(cv, im, seg(a, t0, t1), face=face, push=push, depth=0.04, tint=tint)
    dust(cv, a, alpha=0.28)
    name_card(cv, name, sub, seg(a, t0 + 0.3, t0 + 1.3), y=1345)
    for i, (top, main, sb, tin, tout) in enumerate(cards):
        al = eseg(a, tin, tin + 0.8) * (1 - eseg(a, tout - 0.5, tout))
        if al > 0: date_card(cv, top, main, sb, seg(a, tin, tin + 0.8), alpha=al, y=420)
    caption(cv, caption_text, alpha=0.85 * eseg(a, t0 + 0.6, t0 + 1.4), y=1585, dark=True)
    vignette(cv, 0.5); film_grain(cv, int(a * FPS), 0.05); return s

def mapframe(a, cam, draw, labels, title=None, legend_items=None, extra=None, src=SRC_MAP, tex=0.5, sepia=0.0):
    s = new_surface(); cv = s.getCanvas()
    draw_base(cv, cam); draw(cv, cam); draw_physical_overlay(cv, cam); coast_line(cv, cam)
    draw_paper_texture(cv, alpha=tex)
    if labels: labels(cv, cam)
    if extra: extra(cv, cam)
    if sepia > 0:
        cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=skia.Color4f(0.45, 0.33, 0.2, 0.35 * sepia), BlendMode=skia.BlendMode.kMultiply))
    vignette(cv, 0.42)
    if title: title_block(cv, *title[:3], alpha=title[3] if len(title) > 3 else 1.0)
    if legend_items: legend(cv, legend_items[0], alpha=legend_items[1])
    source_line(cv, src); plate_frame(cv); film_grain(cv, int(a * FPS), 0.05)
    return s

def campath(a, keys):
    if a <= keys[0][0]: return keys[0][1]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if a <= t1: return Camera.lerp(c0, c1, ease(seg(a, t0, t1)))
    return keys[-1][1]

ACQ = lambda pw, f=0.25: lighten(PAL[POW[pw][0]], f)

# =============================================================== SCENE 1 — introduction
def s1_open(a):
    s = doc(a, img('lotter'), 0.0, 6.2, (0.16, 0.16), 1.6, 'T. C. Lotter, Magnus Ducatus Lithuaniae, Augsburg, c. 1778 · Library of Congress')
    cv = s.getCanvas(); al = eseg(a, 0.3, 1.4) * (1 - eseg(a, 5.0, 5.8))
    dark_band(cv, 120, 520, 0.6 * al)
    draw_text(cv, 'THE PARTITIONS OF', W / 2, 270, font('caps', 46), '#E7D3A2', align='center', tracking=0.3, alpha=al, shadow=True)
    draw_text(cv, 'Poland–Lithuania', W / 2, 372, font('serif_bold', 96), '#F4EAD2', align='center', alpha=al, shadow=True)
    draw_text(cv, '1793 · 1795', W / 2, 446, font('caps', 40), '#E2CD9C', align='center', tracking=0.4, alpha=al, shadow=True)
    return s

C1A = Camera.lonlat(24.0, 52.55, 0.70); C1B = Camera.lonlat(24.0, 52.55, 0.79); C1W = Camera.lonlat(21.2, 52.3, 1.25)
def s1_map(a):
    cam = campath(a, [(5.0, C1A), (14.0, C1B), (43.0, Camera.lonlat(24.3, 52.6, 0.82)), (48.9, C1W)])
    st = layers()['stages']['1773']
    def ex(cv, cam):
        glow(cv, cam, '1773_russia', st['russia'], PAL['russia_edge'], pulse(a, 25.9, 31.0))
        glow(cv, cam, '1773_prussia', st['prussia'], PAL['prussia_edge'], pulse(a, 26.6, 31.5))
        glow(cv, cam, '1773_habsburg', st['habsburg'], PAL['austria_edge'], pulse(a, 32.6, 37.8))
        if a > 44.5:
            dark_band(cv, 820, 1100, 0.55 * eseg(a, 45.3, 46.2)); keyword(cv, 'THE 1790s', seg(a, 45.8, 46.6), 990, size=92)
    tl = eseg(a, 6.0, 7.2) * (1 - eseg(a, 43.0, 44.0))
    return mapframe(a, cam, lambda cv, cam: stage_1773(cv, cam, {'loss': eseg(a, 5.6, 9.5)}),
                    lambda cv, cam: labels_1773(cv, cam, al=eseg(a, 7.5, 9.0) * (1 - 0.6 * eseg(a, 43.5, 45))),
                    title=('1773', 'After the First Partition', 'The Commonwealth and its three neighbours', tl),
                    legend_items=([('Polish–Lithuanian Commonwealth', PAL['plt'], False), ('Duchy of Courland (Polish fief)', PAL['plt'], True),
                                   ('Lost in 1772 (hatched)', PAL['paper_dark'], C(PAL['ink_soft'])), ('Commonwealth before 1772', PAL['paper'], False)],
                                  eseg(a, 10.0, 11.0) * (1 - eseg(a, 42.0, 43.0))), extra=ex)

# =============================================================== SCENE 2 — political crisis
def s2_warsaw(a):
    return painting(a, img('bellotto'), 48.9, 70.6, (0.22, 0.55), (0.62, 0.5), 1.0, 1.12,
                    'Bernardo Bellotto, View of Warsaw from the Royal Castle, 1773',
                    kws=(('A WEAK GOVERNMENT', 53.9, 760), ('FOREIGN INFLUENCE', 56.6, 870), ('THE CALL FOR REFORM', 61.6, 980)))

def s2_manuscript(a):
    return doc(a, img('manuscript'), 70.0, 81.2, (0.5, 0.22), 1.45, 'Manuscript of the Government Act of 3 May 1791 · Wikimedia Commons (CC0)',
               card=('THE CONSTITUTION', '3 May 1791', 'adopted by the Great Sejm in Warsaw', 72.0))

def s2_matejko(a):
    return painting(a, img('matejko_const'), 80.7, 96.8, (0.3, 0.5), (0.62, 0.45), 1.0, 1.12,
                    'Jan Matejko, The Constitution of 3 May 1791 (painted 1891)')

C2 = Camera.lonlat(23.6, 52.6, 0.80); C2E = Camera.lonlat(25.6, 52.4, 0.92)
def s2_map(a, phase):
    st = layers()['stages']['1791']
    def ex(cv, cam):
        if phase == 2:
            glow(cv, cam, '1791_russia', st['russia'], PAL['russia_edge'], pulse(a, 111.3, 118.0))
            if a > 117.6: event_marker(cv, cam, 23.88, 51.05, '', 'Battle of Dubienka', '18 July 1792', 'right', alpha=eseg(a, 117.8, 118.6), battle=True)
            al = eseg(a, 111.6, 112.4) * (1 - eseg(a, 123.2, 124.0))
            if al > 0: caption(cv, '18 May 1792 · Russian armies cross the frontier', alpha=al, y=430)
    cam = C2 if phase == 1 else campath(a, [(111.0, C2), (116.0, C2E)])
    return mapframe(a, cam, stage_1791, lambda cv, cam: labels_1791(cv, cam, al=1.0), extra=ex,
                    title=('1791 – 1792', 'Reform and Reaction', 'The Constitution and the Russian intervention'))

def s2_catherine(a):
    return portrait(a, img('catherine'), 102.2, 111.6, (0.5, 0.33), 'Catherine II', 'Empress of Russia, 1762–1796',
                    'Mezzotint by Charles Townley after Edmund Cunningham · Library of Congress',
                    cards=(('CONFEDERATION OF TARGOWICA', '1792', 'signed in St Petersburg, 27 April', 105.3, 111.2),))

def s2_king(a):
    return portrait(a, img('king'), 123.8, 131.9, tuple(P.FACE['king'][:2]), 'Stanisław August Poniatowski', 'King of Poland and Grand Duke of Lithuania, 1764–1795',
                    'Engraving by A. Fogg after Marcello Bacciarelli · Library of Congress',
                    cards=(('24 JULY 1792', 'The King joins Targowica', None, 125.6, 131.6),))

def s2_overturned(a):
    return doc(a, img('manuscript'), 131.4, 137.9, (0.5, 0.35), 1.25, 'Manuscript of the Government Act of 3 May 1791 · Wikimedia Commons (CC0)',
               desat=eseg(a, 131.4, 134.0) * 0.85, bright=1 - 0.35 * eseg(a, 131.4, 135.0), kw=('THE CONSTITUTION IS OVERTURNED', 131.6, 980))

# =============================================================== SCENE 3 — the Second Partition
def monarch_card(a, t0, items, year, title, sub, note=None):
    s = new_surface(); cv = s.getCanvas()
    cam = Camera.lonlat(23.6, 52.6, 0.80)
    draw_base(cv, cam); stage_1791(cv, cam); draw_physical_overlay(cv, cam); coast_line(cv, cam); draw_paper_texture(cv, alpha=0.5)
    cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color4f=skia.Color4f(0.94, 0.9, 0.8, 0.72)))
    vignette(cv, 0.42); title_block(cv, year, title, sub, alpha=eseg(a, t0, t0 + 0.9))
    for k, x, y, r, nm, sb, tin, grey in items:
        al = eseg(a, tin, tin + 0.8)
        fc = P.FACE.get(k, (0.5, 0.3, 3.0))
        if grey:
            cv.saveLayerAlpha(None, int(255 * (0.55 + 0.45 * (1 - eseg(a, tin + 0.8, tin + 1.6)))))
        medallion(cv, P.img(k), x, y - 20 * (1 - al), r, face=fc[:2], zoom=fc[2], alpha=al, name=nm, sub=sb, tint=True)
        if grey: cv.restore()
    if note:
        al = eseg(a, note[1], note[1] + 0.8)
        caption(cv, note[0], alpha=al, y=note[2])
    source_line(cv, 'Portraits: Library of Congress; National Gallery of Art (CC0)'); plate_frame(cv); film_grain(cv, int(a * FPS), 0.05)
    return s

def s3_monarchs(a):
    return monarch_card(a, 137.4, [('catherine', 300, 760, 190, 'Catherine II', 'Empress of Russia', 139.3, False),
                                   ('fw2', 780, 760, 190, 'Frederick William II', 'King of Prussia', 139.9, False),
                                   ('francis', 540, 1240, 120, 'Francis II', 'Holy Roman Emperor · Habsburg Monarchy', 146.0, True)],
                        '1793', 'The Second Partition', 'Russia and Prussia', note=('Austria did not take part in the Second Partition', 146.4, 1560))

C3 = Camera.lonlat(23.8, 52.5, 0.80); C3P = Camera.lonlat(18.4, 53.1, 1.45); C3E = Camera.lonlat(27.3, 52.4, 1.0); C3G = Camera.lonlat(23.9, 53.5, 1.7)
def s3_map(a):
    cam = campath(a, [(148.4, C3), (152.6, C3), (155.4, C3P), (159.4, C3P), (162.6, C3E), (169.5, C3E), (173.5, C3), (185.4, C3), (189.5, C3G)])
    def ex(cv, cam):
        for c, tw in (('Gdańsk', 157.12), ('Toruń', 157.78)):
            if tw - 0.3 < a < tw + 1.6:
                x, y = cam.to_screen(*xy(*CITIES[c])); p = seg(a, tw, tw + 1.3); acc = C(PAL['accent'])
                cv.drawCircle(x, y, 14 + 46 * p, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3,
                                                         Color4f=skia.Color4f(acc.fR, acc.fG, acc.fB, 0.85 * (1 - p))))
        al = eseg(a, 169.0, 169.8) * (1 - eseg(a, 184.4, 185.2))
        if al > 0: caption(cv, 'The Commonwealth loses more than half of its remaining territory', alpha=al, y=430)
        if a > 185.6:
            event_marker(cv, cam, *CITIES['Grodno'], '', 'Grodno Sejm', '17 June – 23 November 1793', 'right', alpha=eseg(a, 185.8, 186.6), pulse=seg(a, 191.0, 192.4) if a < 192.4 else 0)
            al2 = eseg(a, 190.9, 191.7)
            if al2 > 0: caption(cv, 'Treaties ratified: with Russia 22 July · with Prussia 25 September 1793', alpha=al2, y=430)
    return mapframe(a, cam, lambda cv, cam: stage_1793(cv, cam, {'pru': eseg(a, 152.9, 156.2), 'rus': eseg(a, 160.9, 164.6)}),
                    lambda cv, cam: labels_1793(cv, cam, al=eseg(a, 156.0, 157.0) if a < 185.4 else 1 - 0.7 * eseg(a, 185.4, 186.4)),
                    title=('1793', 'The Second Partition', 'Russia and Prussia annex; Austria does not take part', 1 - eseg(a, 185.4, 186.2)),
                    legend_items=([('Remaining Commonwealth', PAL['plt'], False), ('Annexed by Russia, 1793', ACQ('russia'), True),
                                   ('Annexed by Prussia, 1793', ACQ('prussia'), True)], eseg(a, 165.0, 166.0) * (1 - eseg(a, 184.6, 185.4))), extra=ex)

def s3_laurie(a):
    im = img('laurie') or img('lotter')
    cap = ('Laurie & Whittle, London, 1794: Poland and Lithuania after the Second Partition' if img('laurie') is not None
           else 'T. C. Lotter, Magnus Ducatus Lithuaniae, Augsburg, c. 1778 · Library of Congress')
    return doc(a, im, 196.0, 206.6, (0.55, 0.5), 1.5, cap, kw=('SOVEREIGNTY LOST', 199.3, 330))

# =============================================================== SCENE 4/5 — the Kościuszko Uprising
def s4_title(a):
    s = new_surface(); cv = s.getCanvas(); dark_desk(cv)
    keyword(cv, 'OPEN REBELLION', seg(a, 207.0, 207.9), 780, size=70)
    draw_text(cv, '1794', W / 2, 960, font('serif_bold', 190), '#F4EAD2', align='center', alpha=eseg(a, 208.2, 209.2), shadow=True)
    vignette(cv, 0.5); film_grain(cv, int(a * FPS), 0.05); return s

def s4_kosciuszko(a):
    painted = kosc_is_painting()
    return portrait(a, img('kosciuszko'), 212.3, 222.5, (0.5, 0.3) if painted else (0.5, 0.36), 'Tadeusz Kościuszko', '1746–1817 · veteran of the American War of Independence',
                    'Josef Grassi, Portrait of Tadeusz Kościuszko, 1792–93' if painted else 'Engraving, c. 1820 · Library of Congress',
                    tint=0.0 if painted else 0.9)

C4K = Camera.lonlat(20.2, 50.4, 1.85); C4 = Camera.lonlat(22.6, 52.2, 1.12)
def s4_map(a, upto, pulse_i, cam_keys, sepia=0.0, cap=None):
    cam = campath(a, cam_keys)
    pi, pt = pulse_i if pulse_i else (None, 0)
    def lab(cv, cam):
        labels_1794(cv, cam, al=1.0, upto=upto(a), pulse_idx=pi, pulse=seg(a, pt, pt + 1.3) if pi is not None and a < pt + 1.3 else 0)
    st = layers()['stages']['1793']
    def ex(cv, cam):
        glow(cv, cam, '1793_russia', st['russia'], PAL['russia_edge'], pulse(a, 253.3, 259.0))
        glow(cv, cam, '1793_prussia', st['prussia'], PAL['prussia_edge'], pulse(a, 253.9, 259.5))
        if cap:
            al = eseg(a, cap[1], cap[1] + 0.8) * (1 - eseg(a, cap[2] - 0.6, cap[2]))
            if al > 0: caption(cv, cap[0], alpha=al, y=430)
    return mapframe(a, cam, stage_1794, lab, extra=ex, sepia=sepia,
                    title=('1794', 'The Kościuszko Uprising', 'Documented events — dates and places only'),
                    src='Event sites: Wikipedia / OpenHistoricalMap coordinates · no troop movements are shown')

def s4_map_krakow(a):
    return s4_map(a, lambda a: 1, (0, 223.6), [(222.0, Camera.lonlat(21.0, 51.0, 1.3)), (224.5, C4K)])
def s4_map_raclawice(a):
    return s4_map(a, lambda a: 2, (1, 237.5), [(236.8, C4K), (240.2, Camera.lonlat(20.4, 50.5, 2.0))])
def s4_map_campaign(a):
    up = lambda a: 2 + (a > 250.4) + (a > 251.8) + (a > 254.0)
    pi = (2, 250.6) if a < 251.8 else (3, 252.0) if a < 254.0 else (4, 254.2)
    return s4_map(a, up, pi, [(249.5, C4K), (253.0, C4)], cap=('Siege of Warsaw · 13 July – 6 September 1794', 257.2, 263.8))
def s4_map_fall(a):
    up = lambda a: 6 + (a > 272.4)
    return s4_map(a, up, (6, 272.6), [(270.5, C4), (274.0, Camera.lonlat(21.4, 52.0, 1.5))], sepia=eseg(a, 274.0, 279.5),
                  cap=('Warsaw capitulates · 5 November 1794', 275.8, 280.2))

def s4_oath(a):
    return painting(a, img('oath'), 227.4, 237.3, (0.5, 0.55), (0.42, 0.5), 1.0, 1.15,
                    'Michał Stachowicz, Kościuszko’s Oath on the Kraków Market Square (1797)',
                    card=('KRAKÓW', '24 March 1794', 'the Act of Uprising is proclaimed', 227.6))
def s4_raclawice(a):
    return painting(a, img('raclawice'), 240.2, 250.0, (0.25, 0.5), (0.6, 0.5), 1.0, 1.1,
                    'Jan Matejko, Kościuszko at Racławice (painted 1888)',
                    card=('RACŁAWICE', '4 April 1794', 'victory over Russian troops', 240.6))
def s4_maciejowice(a):
    return painting(a, img('maciejowice'), 263.8, 271.0, (0.4, 0.5), (0.55, 0.5), 1.0, 1.1,
                    'Jan Bogumił Plersch, Kościuszko in the Battle of Maciejowice',
                    card=('MACIEJOWICE', '10 October 1794', 'Kościuszko is wounded and captured', 264.2), desat=0.2)

# =============================================================== SCENE 6 — the Third Partition (+7: abdication)
def s6_trio(a):
    return monarch_card(a, 280.0, [('catherine', 820, 820, 165, 'Catherine II', 'Russia', 283.3, False),
                                   ('fw2', 260, 820, 165, 'Frederick William II', 'Prussia', 284.0, False),
                                   ('francis', 540, 1220, 165, 'Francis II', 'Austria', 284.6, False)],
                        '1795', 'The Third Partition', 'Russia · Prussia · Austria',
                        note=('Treaties of 3 January and 24 October 1795', 285.2, 1585))

def s6_doc(a):
    cary = img('cary')
    if cary is not None:
        P.IMG['doc'] = os.path.basename(glob.glob(os.path.join(ARC, commons_name('A new map of Poland, and the Grand Duchy')[:40] + '*'))[0])
        P.DOC_FOCUS = (0.5, 0.45); P.DOC_ZOOM = 1.5
        P.DOC_CAPTION = 'John Cary, A New Map of Poland … shewing their dismemberments, London, 1799'
    else:
        P.DOC_FOCUS = (0.55, 0.6); P.DOC_ZOOM = 1.6  # Lotter again, different detail than the opening
    return P.shot_document(a, int(a * FPS))

# =============================================================== SCENE 8 — conclusion
CF0 = Camera.lonlat(24.0, 52.7, 0.80); CF1 = Camera.lonlat(24.0, 52.7, 0.86)
def final_map(a, params, title, cam, extra=None, legend_al=0.0):
    return mapframe(a, cam, lambda cv, cam: stage_final(cv, cam, params), lambda cv, cam: labels_final(cv, cam, al=1.0), extra=extra,
                    title=title, legend_items=([('Russia', lifted_tone('russia', '93'), False), ('Prussia', lifted_tone('prussia', '93'), False),
                                                ('Austria', lifted_tone('habsburg', '93'), False), ('Commonwealth in 1772 (outline)', PAL['plt'], False)], legend_al))

def s8_people(a):
    def ex(cv, cam):
        al = eseg(a, 334.2, 335.0) * (1 - eseg(a, 346.2, 347.0))
        if al > 0: caption(cv, 'Poles and Lithuanians now live under Russian, Prussian and Austrian rule', alpha=al, y=430)
    return final_map(a, {}, ('1795', 'Divided, not Erased', 'The people of the former Commonwealth'), campath(a, [(329.7, CF0), (347.5, CF1)]),
                     extra=ex, legend_al=eseg(a, 331.0, 332.0))

def s8_grodno(a):
    return doc(a, img('grodno_map'), 347.0, 360.0, (0.5, 0.5), 1.5, 'Grodno Governorate: Russian provincial map, early 19th century · Library of Congress',
               kw=('NEW LAWS · NEW ADMINISTRATIONS', 352.0, 330))

def s8_memory(a):
    return painting(a, img('bellotto'), 359.5, 371.5, (0.62, 0.5), (0.35, 0.52), 1.12, 1.0,
                    'Bernardo Bellotto, View of Warsaw from the Royal Castle, 1773', desat=0.55, bright=0.85,
                    kws=(('THE MEMORY ENDURES', 366.0, 980),))

def s8_uprisings(a):
    return painting(a, img('oath'), 371.0, 379.8, (0.42, 0.5), (0.55, 0.52), 1.08, 1.0,
                    'Michał Stachowicz, Kościuszko’s Oath on the Kraków Market Square (1797)', desat=0.45, bright=0.9,
                    kws=(('1830–31 · 1863–64', 371.8, 900), ('UPRISINGS CONTINUE', 372.6, 1000)))

def s8_lithuania(a):
    return doc(a, img('lotter'), 379.3, 386.6, (0.45, 0.62), 1.8, 'T. C. Lotter, Magnus Ducatus Lithuaniae, Augsburg, c. 1778 · Library of Congress',
               kw=('LITHUANIAN IDENTITY ENDURES', 379.6, 330))

def s8_three(a):
    p = {'plt_base': 1.0, 'y72': eseg(a, 386.8, 387.8), 'y93': eseg(a, 388.2, 389.2), 'y95': eseg(a, 389.6, 390.6),
         'outline': 1.0 - eseg(a, 407.2, 409.5)}
    def ex(cv, cam):
        hl = eseg(a, 394.6, 395.5)
        if a > 393.4:
            rail = eseg(a, 393.4, 394.2) * (1 - eseg(a, 403.8, 404.6))
            sh = skia.GradientShader.MakeLinear([skia.Point(0, 1180), skia.Point(0, H)],
                                                [skia.Color4f(0.94, 0.9, 0.8, 0), skia.Color4f(0.94, 0.9, 0.8, 0.82 * rail)], [0, 0.45])
            cv.drawRect(skia.Rect(0, 1180, W, H), skia.Paint(Shader=sh))
            for k, x, nm, tin in (('fw2', 230, 'Frederick William II', 393.5), ('francis', 540, 'Francis II', 393.8), ('catherine', 850, 'Catherine II', 394.1)):
                fc = P.FACE.get(k, (0.5, 0.3, 3.0))
                medallion(cv, P.img(k), x, 1395, 100, face=fc[:2], zoom=fc[2], alpha=eseg(a, tin, tin + 0.8) * (1 - eseg(a, 403.8, 404.6)), name=nm, sub=None, tint=True)
        for i, (yr, t) in enumerate((('1772', 386.8), ('1793', 388.2), ('1795', 389.6))):
            al = eseg(a, t, t + 0.5) * (1 - eseg(a, 392.6, 393.3))
            if al > 0: draw_text(cv, yr, W / 2 + (i - 1) * 260, 470, font('serif_bold', 72), PAL['accent'], align='center', alpha=al, halo=PAL['paper'], halo_w=10)
        if a > 404.6:
            al = eseg(a, 404.8, 405.8)
            dark_band(cv, 820, 1100, 0.45 * al); keyword(cv, 'VANISHED FROM THE MAP', seg(a, 406.8, 407.8), 960, size=70)
    return final_map(a, p, ('1772 · 1793 · 1795', 'Three Partitions', 'One state divided between three empires', eseg(a, 386.2, 387.2)),
                     campath(a, [(386.0, CF0), (404.6, CF1)]), extra=ex)

def s8_end(a):
    s = new_surface(); cv = s.getCanvas()
    cv.drawColor(C(PAL['paper'])); draw_paper_texture(cv, alpha=0.6)
    al = eseg(a, 409.6, 411.0)
    draw_text(cv, 'BUT THE IDEA OF INDEPENDENCE', W / 2, 720, font('caps', 34), PAL['gold'], align='center', tracking=0.2, alpha=al)
    draw_text(cv, 'SURVIVED', W / 2, 775, font('caps', 34), PAL['gold'], align='center', tracking=0.2, alpha=al)
    draw_text(cv, 'Poland–Lithuania', W / 2, 900, font('serif_bold', 100), PAL['ink'], align='center', alpha=eseg(a, 411.2, 412.4))
    draw_text(cv, '1772 · 1793 · 1795', W / 2, 990, font('caps', 42), PAL['gold'], align='center', tracking=0.4, alpha=eseg(a, 412.0, 413.2))
    cr = eseg(a, 414.0, 415.2)
    for i, line in enumerate(('Maps: OpenHistoricalMap (CC0), corrected against atlas reference · Natural Earth',
                              'Images: Library of Congress · Wikimedia Commons · National Gallery of Art (CC0)',
                              'Narration: ElevenLabs · Original score composed for this film')):
        draw_text(cv, line, W / 2, 1390 + i * 40, font('body_italic', 24), PAL['ink_soft'], align='center', alpha=cr * 0.9)
    vignette(cv, 0.4); plate_frame(cv, alpha=al); film_grain(cv, int(a * FPS), 0.05)
    return s

# =============================================================== timeline: (start, shot_fn, transition-in kind, transition duration)
TIMELINE = [
    (0.0, s1_open, None, 0),
    (5.2, s1_map, 'deckle', 1.0),
    (48.9, s2_warsaw, 'fade', 0.9),
    (70.0, s2_manuscript, 'deckle', 0.9),
    (80.7, s2_matejko, 'fade', 0.8),
    (96.3, lambda a: s2_map(a, 1), 'fade', 0.8),
    (102.2, s2_catherine, 'deckle', 0.9),
    (111.0, lambda a: s2_map(a, 2), 'fade', 0.8),
    (123.8, s2_king, 'deckle', 0.9),
    (131.4, s2_overturned, 'fade', 0.8),
    (137.4, s3_monarchs, 'deckle', 1.0),
    (148.4, s3_map, 'fade', 0.9),
    (196.0, s3_laurie, 'deckle', 1.0),
    (206.1, s4_title, 'fade', 0.8),
    (212.3, s4_kosciuszko, 'fade', 0.8),
    (222.0, s4_map_krakow, 'deckle', 0.9),
    (227.4, s4_oath, 'fade', 0.8),
    (236.8, s4_map_raclawice, 'fade', 0.7),
    (240.2, s4_raclawice, 'fade', 0.7),
    (249.5, s4_map_campaign, 'fade', 0.8),
    (263.8, s4_maciejowice, 'deckle', 0.9),
    (270.5, s4_map_fall, 'fade', 0.8),
    (280.0, s6_trio, 'deckle', 1.0),
    (287.3, s6_doc, 'fade', 0.8),
    (291.3, lambda a: P.shot_map1795(a, int(a * FPS)), 'deckle', 0.9),
    (313.3, lambda a: P.shot_portrait(a, int(a * FPS)), 'deckle', 1.0),
    (322.6, lambda a: P.shot_final(a, int(a * FPS)), 'fade', 0.8),
    (329.7, s8_people, 'fade', 0.6),
    (347.0, s8_grodno, 'deckle', 0.9),
    (359.5, s8_memory, 'fade', 0.9),
    (371.0, s8_uprisings, 'fade', 0.8),
    (379.3, s8_lithuania, 'fade', 0.8),
    (386.0, s8_three, 'deckle', 1.0),
    (409.0, s8_end, 'fade', 1.4),
]

def frame(fi):
    a = fi / FPS
    idx = max(i for i, sh in enumerate(TIMELINE) if sh[0] <= a)
    start, fn, kind, d = TIMELINE[idx]
    # transition INTO this shot: window [start, start + d]
    if kind and a < start + d and idx > 0:
        p = seg(a, start, start + d)
        prev = arr(TIMELINE[idx - 1][1](a)); cur = arr(fn(a))
        out = deckle_wipe(prev, cur, p) if kind == 'deckle' else crossfade(prev, cur, p)
    else:
        out = arr(fn(a))
    fade = seg(a, END - 0.8, END)
    if a < 0.6: out = (out * eseg(a, 0, 0.6)).astype(np.uint8)
    return (out * (1 - fade)).astype(np.uint8) if fade > 0 else out

def render_chunk(args):
    k, lo, hi, out = args
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(lo, hi):
        p.stdin.write(frame(fi).tobytes())
        if (fi - lo) % 300 == 0: print(f'chunk {k}: {fi - lo}/{hi - lo}  {time.time() - t0:.0f}s', flush=True)
    p.stdin.close(); p.wait(); return out

if __name__ == '__main__':
    outdir = os.path.join(ROOT, 'previews', 'final'); tmp = os.path.join(outdir, 'chunks'); os.makedirs(tmp, exist_ok=True)
    if sys.argv[1] == 'stills':
        from PIL import Image
        for t in [float(x) for x in sys.argv[2:]]:
            Image.fromarray(frame(int(round(t * FPS)))).save(os.path.join(tmp, f'still_{t:06.1f}.png')); print('still', t, flush=True)
        sys.exit()
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    nchunks = 16; bounds = [round(N * i / nchunks) for i in range(nchunks + 1)]
    jobs = [(i, bounds[i], bounds[i + 1], os.path.join(tmp, f'c{i:02d}.mp4')) for i in range(nchunks)]
    with Pool(nw) as pool: outs = pool.map(render_chunk, jobs, chunksize=1)
    open(os.path.join(tmp, 'list.txt'), 'w').write(''.join(f"file '{o}'\n" for o in outs))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'list.txt'), '-c', 'copy', os.path.join(tmp, 'video.mp4')], check=True)
    print('video done', N, 'frames')
