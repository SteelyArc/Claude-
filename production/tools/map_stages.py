"""Historical map stages. Each draw_* function takes a Camera and animation parameters (0..1),
so the same code renders the approval stills and the animated sequences."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlas import *

POW = {'plt': ('plt', 'plt_edge'), 'russia': ('russia', 'russia_edge'), 'prussia': ('prussia', 'prussia_edge'),
       'habsburg': ('austria', 'austria_edge'), 'ottoman': ('ottoman', 'ottoman_edge')}

CITIES = {  # lon, lat  (coordinates checked against Wikipedia/OHM, see research/BORDER_VERIFICATION.md)
    'Warsaw': (21.01, 52.23), 'Kraków': (19.94, 50.06), 'Gdańsk': (18.65, 54.35), 'Toruń': (18.60, 53.01),
    'Poznań': (16.93, 52.41), 'Wilno': (25.28, 54.69), 'Grodno': (23.83, 53.68), 'Lwów': (24.03, 49.84),
    'Kiev': (30.52, 50.45), 'Minsk': (27.56, 53.90), 'Riga': (24.10, 56.95), 'Königsberg': (20.51, 54.71),
    'Mitau': (23.72, 56.65), 'Lublin': (22.57, 51.25), 'Brest-Litovsk': (23.69, 52.10), 'Pinsk': (26.10, 52.11),
    'Kamieniec': (26.58, 48.68), 'Berlin': (13.40, 52.52), 'Vienna': (16.37, 48.21), 'Białystok': (23.16, 53.13),
    'Breslau': (17.04, 51.11), 'Racławice': (20.232, 50.330), 'Maciejowice': (21.550, 51.683),
    'Szczekociny': (19.825, 50.628), 'Praga': (21.051, 52.252), 'Smolensk': (32.05, 54.78), 'Elbing': (19.40, 54.16),
}

def _poly(cv, cam, key, geom, kind, alpha=1.0, ribbon_a=0.5):
    if geom is None or geom.is_empty or alpha <= 0: return
    f, e = POW[kind]; p = PATHS.get_path(key, geom)
    fill(cv, p, PAL[f], alpha); ribbon(cv, cam, PATHS.get_ext(key, geom), PAL[e], 18, ribbon_a * alpha)

def _neutral(cv, cam, st, tag):
    for k in ('hre', 'saxony', 'sweden', 'denmark'):
        p = PATHS.get_path(f'{tag}_{k}', st[k]); fill(cv, p, PAL['neutral'], 0.9)
        stroke(cv, cam, p, PAL['ink_soft'], 0.9, 0.45)

def _borders(cv, cam, geoms, width=1.5, alpha=0.85):
    for key, g in geoms:
        stroke(cv, cam, PATHS.get_path(key, g), PAL['ink'], width, alpha)

def base_and_politics(cv, cam, stage_fn, frame=0, tex_alpha=0.55):
    draw_base(cv, cam)
    stage_fn(cv, cam)
    draw_physical_overlay(cv, cam); coast_line(cv, cam)
    draw_paper_texture(cv, alpha=tex_alpha)

# --------------------------------------------------------------------------- stage 1: 1773
def stage_1773(cv, cam, a=None):
    a = a or {}; L = layers(); st = L['stages']['1773']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1773')
    for k in ('ottoman', 'habsburg', 'russia', 'prussia'): _poly(cv, cam, f'1773_{k}', st[k], k)
    # 1772 losses: tinted with the annexing power + hatch
    for k, pw in (('loss72_pru', 'prussia'), ('loss72_rus', 'russia'), ('loss72_aut', 'habsburg')):
        pth = PATHS.get_path('1773_' + k, st[k]); f, e = POW[pw]
        hatch(cv, cam, pth, PAL[e], 12, 1.4, 0.45 * a.get('loss', 1))
    _poly(cv, cam, '1773_plt', st['plt'], 'plt', ribbon_a=0.7)
    _poly(cv, cam, '1773_courland', st['courland'], 'plt', ribbon_a=0.4)
    hatch(cv, cam, PATHS.get_path('1773_courland', st['courland']), PAL['plt_edge'], 9, 1.0, 0.35, angle=-45)
    _borders(cv, cam, [('1773_prussia', st['prussia']), ('1773_russia', st['russia']), ('1773_habsburg', st['habsburg']), ('1773_plt', st['plt'])])
    stroke(cv, cam, PATHS.get_path('plt_pre72', L['plt_pre72']), PAL['plt_edge'], 2.4, 0.85 * a.get('loss', 1), dash=[10, 7])
    cv.restore()

def labels_1773(cv, cam, al=1.0):
    region_label(cv, cam, 25.0, 52.75, '', darken(PAL['plt_edge'], .2), 29, lines=['POLISH–LITHUANIAN', 'COMMONWEALTH'], alpha=al)
    region_label(cv, cam, 31.4, 55.9, '', darken(PAL['russia_edge'], .25), 30, lines=['RUSSIAN', 'EMPIRE'], alpha=al)
    region_label(cv, cam, 15.6, 53.75, '', darken(PAL['prussia_edge'], .25), 22, lines=['KINGDOM', 'OF PRUSSIA'], alpha=al)
    region_label(cv, cam, 21.5, 48.0, '', darken(PAL['austria_edge'], .1), 26, lines=['HABSBURG', 'MONARCHY'], alpha=al)
    region_label(cv, cam, 30.5, 46.6, '', darken(PAL['ottoman_edge'], .2), 22, lines=['OTTOMAN EMPIRE'], alpha=al * .8)
    region_label(cv, cam, 22.6, 56.35, '', darken(PAL['plt_edge'], .2), 17, lines=['DUCHY OF', 'COURLAND'], alpha=al * .95)
    water_label(cv, cam, 18.3, 56.4, 'Baltic Sea', 36, rot=-28, alpha=al * .85)
    for n, k, dx, al_ in (('Warsaw', 'capital', 16, 'left'), ('Kraków', 'town', 14, 'left'), ('Wilno', 'town', 14, 'left'),
                          ('Gdańsk', 'town', 14, 'right'), ('Königsberg', 'town', 14, 'left'), ('Lwów', 'town', 14, 'left'),
                          ('Kiev', 'town', 14, 'left'), ('Riga', 'town', 14, 'right'), ('Berlin', 'capital', 16, 'left'),
                          ('Vienna', 'capital', 16, 'left'), ('Poznań', 'town', 14, 'right'), ('Grodno', 'town', 14, 'left')):
        city(cv, cam, *CITIES[n], n, k, dx=dx, align=al_, size=30, alpha=al)
    region_label(cv, cam, 29.3, 55.35, '', darken(PAL['russia_edge'], .3), 16, lines=['TO RUSSIA', '1772'], alpha=al * .95)
    region_label(cv, cam, 19.0, 53.55, '', darken(PAL['prussia_edge'], .35), 15, lines=['TO PRUSSIA', '1772'], alpha=al * .95)
    region_label(cv, cam, 23.0, 49.35, '', darken(PAL['austria_edge'], .3), 16, lines=['TO AUSTRIA 1772'], alpha=al * .95)

# --------------------------------------------------------------------------- stage 2: 1791-92
def stage_1791(cv, cam, a=None):
    L = layers(); st = L['stages']['1791']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1791')
    for k in ('ottoman', 'habsburg', 'russia', 'prussia'): _poly(cv, cam, f'1791_{k}', st[k], k)
    _poly(cv, cam, '1791_plt', st['plt'], 'plt', ribbon_a=0.7)
    _poly(cv, cam, '1791_courland', st['courland'], 'plt', ribbon_a=0.4)
    hatch(cv, cam, PATHS.get_path('1791_courland', st['courland']), PAL['plt_edge'], 9, 1.0, 0.35, angle=-45)
    _borders(cv, cam, [('1791_prussia', st['prussia']), ('1791_russia', st['russia']), ('1791_habsburg', st['habsburg']), ('1791_plt', st['plt'])])
    cv.restore()

def labels_1791(cv, cam, al=1.0):
    region_label(cv, cam, 24.9, 53.2, '', PAL['plt_edge'], 28, lines=['POLISH–LITHUANIAN', 'COMMONWEALTH'], alpha=al)
    region_label(cv, cam, 32.6, 55.6, '', darken(PAL['russia_edge'], .1), 30, lines=['RUSSIAN', 'EMPIRE'], alpha=al)
    region_label(cv, cam, 15.4, 53.7, '', darken(PAL['prussia_edge'], .1), 26, lines=['KINGDOM', 'OF PRUSSIA'], alpha=al)
    region_label(cv, cam, 21.4, 48.1, '', darken(PAL['austria_edge'], .1), 24, lines=['HABSBURG', 'MONARCHY'], alpha=al)
    water_label(cv, cam, 18.3, 56.4, 'Baltic Sea', 34, rot=-28, alpha=al * .85)
    for n, k, al_ in (('Kraków', 'town', 'left'), ('Wilno', 'town', 'left'), ('Gdańsk', 'town', 'right'), ('Grodno', 'town', 'left'),
                      ('Kiev', 'town', 'left'), ('Lwów', 'town', 'left'), ('Berlin', 'capital', 'left'), ('Vienna', 'capital', 'left')):
        city(cv, cam, *CITIES[n], n, k, align=al_, size=28, alpha=al)
    event_marker(cv, cam, *CITIES['Warsaw'], 1, 'Warsaw', 'Constitution of 3 May 1791', 'right', alpha=al)

# --------------------------------------------------------------------------- stage 3: 1793
def stage_1793(cv, cam, a=None):
    a = a or {}; L = layers(); st = L['stages']['1793']; g = L['gains']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1793')
    for k in ('ottoman', 'habsburg'): _poly(cv, cam, f'1793_{k}', st[k], k)
    # powers before the partition, then the 1793 gains layered on top with animated reveal
    _poly(cv, cam, '1791_russia', L['stages']['1791']['russia'], 'russia')
    _poly(cv, cam, '1791_prussia', L['stages']['1791']['prussia'], 'prussia')
    _poly(cv, cam, '1773_plt_all', L['plt1773'], 'plt', ribbon_a=0.0)
    rv_r, rv_p = a.get('rus', 1.0), a.get('pru', 1.0)
    for gk, pw, rv in (('93_rus', 'russia', rv_r), ('93_pru', 'prussia', rv_p)):
        pth = PATHS.get_path('g' + gk, g[gk]); f, e = POW[pw]
        fill(cv, pth, lighten(PAL[f], 0.25), rv); ribbon(cv, cam, pth, PAL[e], 14, 0.35 * rv)
        hatch(cv, cam, pth, PAL[e], 12, 1.3, 0.42 * rv, reveal=rv)
    _poly(cv, cam, '1793_plt', st['plt'], 'plt', ribbon_a=0.7)
    _poly(cv, cam, '1793_courland', st['courland'], 'plt', ribbon_a=0.4)
    hatch(cv, cam, PATHS.get_path('1793_courland', st['courland']), PAL['plt_edge'], 9, 1.0, 0.35, angle=-45)
    _borders(cv, cam, [('1793_plt', st['plt']), ('1791_russia', L['stages']['1791']['russia']), ('1791_prussia', L['stages']['1791']['prussia']), ('1793_habsburg', st['habsburg'])])
    stroke(cv, cam, PATHS.get_path('1773_plt_all', L['plt1773']), PAL['plt_edge'], 2.4, 0.8, dash=[10, 7])
    cv.restore()

def labels_1793(cv, cam, al=1.0):
    region_label(cv, cam, 22.6, 52.75, '', PAL['plt_edge'], 26, lines=['POLAND–', 'LITHUANIA'], alpha=al)
    region_label(cv, cam, 28.2, 51.2, '', darken(PAL['russia_edge'], .2), 23, lines=['TO RUSSIA', '1793'], alpha=al)
    region_label(cv, cam, 18.1, 52.1, '', darken(PAL['prussia_edge'], .2), 21, lines=['TO PRUSSIA', '1793'], alpha=al)
    region_label(cv, cam, 16.95, 51.75, '', darken(PAL['prussia_edge'], .25), 16, lines=['GREATER POLAND'], alpha=al * .9)
    region_label(cv, cam, 32.6, 55.6, '', darken(PAL['russia_edge'], .1), 28, lines=['RUSSIAN', 'EMPIRE'], alpha=al)
    region_label(cv, cam, 15.0, 53.9, '', darken(PAL['prussia_edge'], .1), 24, lines=['KINGDOM', 'OF PRUSSIA'], alpha=al)
    region_label(cv, cam, 21.4, 48.1, '', darken(PAL['austria_edge'], .1), 22, lines=['HABSBURG MONARCHY'], alpha=al * .8)
    water_label(cv, cam, 18.3, 56.4, 'Baltic Sea', 34, rot=-28, alpha=al * .85)
    city(cv, cam, *CITIES['Gdańsk'], 'Gdańsk', 'town', align='right', size=29, alpha=al, sub='(Danzig)')
    city(cv, cam, *CITIES['Toruń'], 'Toruń', 'town', align='right', size=29, alpha=al, sub='(Thorn)')
    city(cv, cam, *CITIES['Poznań'], 'Poznań', 'town', align='right', size=29, alpha=al, sub='(Posen)')
    for n, k, al_ in (('Warsaw', 'capital', 'left'), ('Kraków', 'town', 'left'), ('Wilno', 'town', 'left'),
                      ('Minsk', 'town', 'left'), ('Kiev', 'town', 'left'), ('Pinsk', 'town', 'left')):
        city(cv, cam, *CITIES[n], n, k, align=al_, size=28, alpha=al)
    event_marker(cv, cam, *CITIES['Grodno'], 1, 'Grodno Sejm', 'June–November 1793', 'right', alpha=al)

# --------------------------------------------------------------------------- stage 4: 1794
UPRISING = [  # documented events only; no troop routes are drawn
    ('Kraków', 'Act of Uprising', '24 March 1794', 'left', False),
    ('Racławice', 'Battle of Racławice', '4 April 1794', 'right', True),
    ('Warsaw', 'Warsaw rises', '17–18 April 1794', 'left', False),
    ('Wilno', 'Wilno rises', '22–23 April 1794', 'right', False),
    ('Szczekociny', 'Battle of Szczekociny', '6 June 1794', 'left', True),
    ('Maciejowice', 'Battle of Maciejowice', '10 October 1794', 'right', True),
    ('Praga', 'Storming of Praga', '4 November 1794', 'right', True),
]

def stage_1794(cv, cam, a=None):
    L = layers(); st = L['stages']['1793']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1793')
    for k in ('ottoman', 'habsburg', 'russia', 'prussia'): _poly(cv, cam, f'1793_{k}', st[k], k)
    _poly(cv, cam, '1793_plt', st['plt'], 'plt', ribbon_a=0.7)
    _poly(cv, cam, '1793_courland', st['courland'], 'plt', ribbon_a=0.4)
    hatch(cv, cam, PATHS.get_path('1793_courland', st['courland']), PAL['plt_edge'], 9, 1.0, 0.35, angle=-45)
    _borders(cv, cam, [('1793_plt', st['plt']), ('1793_russia', st['russia']), ('1793_prussia', st['prussia']), ('1793_habsburg', st['habsburg'])])
    cv.restore()

def labels_1794(cv, cam, al=1.0, upto=99, pulse_idx=None, pulse=0.0):
    region_label(cv, cam, 24.9, 52.95, '', PAL['plt_edge'], 22, lines=['POLAND–LITHUANIA'], alpha=al * .7)
    region_label(cv, cam, 27.6, 51.3, '', darken(PAL['russia_edge'], .1), 24, lines=['RUSSIAN', 'EMPIRE'], alpha=al * .8)
    region_label(cv, cam, 17.6, 52.7, '', darken(PAL['prussia_edge'], .1), 22, lines=['KINGDOM', 'OF PRUSSIA'], alpha=al * .8)
    region_label(cv, cam, 22.6, 49.55, '', darken(PAL['austria_edge'], .1), 18, lines=['HABSBURG MONARCHY'], alpha=al * .75)
    for i, (c, lab, d, side, battle) in enumerate(UPRISING):
        if i < upto:
            event_marker(cv, cam, *CITIES[c], i + 1, lab, d, side, alpha=al, battle=battle, pulse=pulse if i == pulse_idx else 0)

# --------------------------------------------------------------------------- stage 5: 1795
def stage_1795(cv, cam, a=None):
    a = a or {}; L = layers(); st = L['stages']['1795']; g = L['gains']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1795')
    for k in ('ottoman', 'habsburg', 'russia', 'prussia'): _poly(cv, cam, f'1793_{k}', L['stages']['1793'][k], k)
    _poly(cv, cam, '1793_plt', st['plt'], 'plt', ribbon_a=0.7)
    _poly(cv, cam, '1793_courland', L['stages']['1793']['courland'], 'plt', ribbon_a=0.4)
    for gk, pw, key in (('95_rus', 'russia', 'rus'), ('95_rus_courland', 'russia', 'rus'), ('95_pru', 'prussia', 'pru'), ('95_aut', 'habsburg', 'aut')):
        rv = a.get(key, 1.0)
        if rv <= 0: continue
        pth = PATHS.get_path('g' + gk, g[gk]); f, e = POW[pw]
        fill(cv, pth, lighten(PAL[f], 0.28), rv); ribbon(cv, cam, pth, PAL[e], 14, 0.4 * rv)
        hatch(cv, cam, pth, PAL[e], 10, 1.2, 0.38 * rv, angle=-45, reveal=rv)
    _borders(cv, cam, [('1793_russia', L['stages']['1793']['russia']), ('1793_prussia', L['stages']['1793']['prussia']), ('1793_habsburg', L['stages']['1793']['habsburg'])])
    for gk in ('95_rus', '95_rus_courland', '95_pru', '95_aut'):
        stroke(cv, cam, PATHS.get_path('g' + gk, g[gk]), PAL['ink'], 1.6, 0.85)
    cv.restore()

def labels_1795(cv, cam, al=1.0):
    region_label(cv, cam, 25.6, 54.0, '', darken(PAL['russia_edge'], .25), 22, lines=['TO RUSSIA'], alpha=al)
    region_label(cv, cam, 21.6, 53.55, '', darken(PAL['prussia_edge'], .3), 19, lines=['NEW EAST', 'PRUSSIA'], alpha=al)
    region_label(cv, cam, 21.4, 50.75, '', darken(PAL['austria_edge'], .3), 19, lines=['WEST', 'GALICIA'], alpha=al)
    region_label(cv, cam, 23.0, 56.6, '', darken(PAL['russia_edge'], .25), 16, lines=['COURLAND'], alpha=al * .9)
    region_label(cv, cam, 29.6, 51.0, '', darken(PAL['russia_edge'], .25), 26, lines=['RUSSIAN', 'EMPIRE'], alpha=al)
    region_label(cv, cam, 15.4, 53.7, '', darken(PAL['prussia_edge'], .1), 24, lines=['KINGDOM', 'OF PRUSSIA'], alpha=al)
    region_label(cv, cam, 21.6, 48.15, '', darken(PAL['austria_edge'], .1), 22, lines=['HABSBURG MONARCHY'], alpha=al * .8)
    water_label(cv, cam, 18.3, 56.4, 'Baltic Sea', 34, rot=-28, alpha=al * .85)
    for n, k, al_ in (('Warsaw', 'capital', 'left'), ('Kraków', 'town', 'left'), ('Lublin', 'town', 'left'), ('Wilno', 'town', 'left'),
                      ('Grodno', 'town', 'left'), ('Białystok', 'town', 'right'), ('Brest-Litovsk', 'town', 'left')):
        city(cv, cam, *CITIES[n], n, k, align=al_, size=28, alpha=al)

# --------------------------------------------------------------------------- stage 6: final division
def stage_final(cv, cam, a=None):
    a = a or {}; L = layers(); st = L['stages']['1795']; g = L['gains']; l72 = L['loss72']
    cv.save(); cam.apply(cv)
    _neutral(cv, cam, st, '1795')
    _poly(cv, cam, '1795_ottoman', st['ottoman'], 'ottoman')
    _poly(cv, cam, 'f_habs', L['stages']['1793']['habsburg'], 'habsburg')
    _poly(cv, cam, 'f_rus', st['russia95'], 'russia'); _poly(cv, cam, 'f_pru', st['prussia95'], 'prussia')
    tones = {'72': 0.0, '93': 0.22, '95': 0.45}
    parts = [('l72pru', l72['pru'], 'prussia', '72'), ('l72rus', l72['rus'], 'russia', '72'), ('l72aut', l72['aut'], 'habsburg', '72'),
             ('g93_pru', g['93_pru'], 'prussia', '93'), ('g93_rus', g['93_rus'], 'russia', '93'),
             ('g95_pru', g['95_pru'], 'prussia', '95'), ('g95_rus', g['95_rus'], 'russia', '95'), ('g95_rus_courland', g['95_rus_courland'], 'russia', '95'),
             ('g95_aut', g['95_aut'], 'habsburg', '95')]
    for key, geom, pw, yr in parts:
        pth = PATHS.get_path(key, geom); f, e = POW[pw]
        fill(cv, pth, lighten(PAL[f], tones[yr]) if tones[yr] else darken(PAL[f], 0.1)); ribbon(cv, cam, pth, PAL[e], 12, 0.3)
    for key, geom, pw, yr in parts:
        stroke(cv, cam, PATHS.get_path(key, geom), PAL['ink'], 0.9, 0.35, dash=[4, 5])
    _borders(cv, cam, [('f_rus', st['russia95']), ('f_pru', st['prussia95']), ('f_habs', L['stages']['1793']['habsburg'])], 1.6, 0.9)
    stroke(cv, cam, PATHS.get_path('plt_pre72', L['plt_pre72']), PAL['plt_edge'], 3.2, 0.95 * a.get('outline', 1))
    stroke(cv, cam, PATHS.get_path('plt_pre72', L['plt_pre72']), '#F3E3B5', 1.0, 0.9 * a.get('outline', 1))
    cv.restore()

def labels_final(cv, cam, al=1.0):
    region_label(cv, cam, 28.3, 52.9, '', darken(PAL['russia_edge'], .3), 32, lines=['RUSSIA'], alpha=al)
    region_label(cv, cam, 18.6, 53.0, '', darken(PAL['prussia_edge'], .3), 30, lines=['PRUSSIA'], alpha=al)
    region_label(cv, cam, 22.4, 49.45, '', darken(PAL['austria_edge'], .3), 30, lines=['AUSTRIA'], alpha=al)
    water_label(cv, cam, 18.3, 56.4, 'Baltic Sea', 34, rot=-28, alpha=al * .85)
    for n, k, al_ in (('Warsaw', 'capital', 'left'), ('Kraków', 'town', 'left'), ('Wilno', 'town', 'left'), ('Gdańsk', 'town', 'right'),
                      ('Lwów', 'town', 'left'), ('Minsk', 'town', 'left'), ('Kiev', 'town', 'left'), ('Riga', 'town', 'left')):
        city(cv, cam, *CITIES[n], n, k, align=al_, size=28, alpha=al)

def lifted_tone(pw, yr):
    return {'72': darken(PAL[POW[pw][0]], 0.1), '93': lighten(PAL[POW[pw][0]], 0.22), '95': lighten(PAL[POW[pw][0]], 0.45)}[yr]
