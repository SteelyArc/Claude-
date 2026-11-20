"""Phase 2: render the six historical map stages as 1080x1920 approval stills."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from map_stages import *

OUT = os.path.join(ROOT, 'previews', 'maps'); os.makedirs(OUT, exist_ok=True)
SRC = 'Borders: OpenHistoricalMap (CC0), 1793 line corrected from atlas reference · Physical: Natural Earth'
WIDE = Camera.lonlat(24.0, 52.55, 0.79)

def frame(name, cam, draw, labels, year, title, sub, legend_items, legend_title=None, src=SRC):
    t0 = time.time(); s = new_surface(); cv = s.getCanvas()
    draw_base(cv, cam); draw(cv, cam); draw_physical_overlay(cv, cam); coast_line(cv, cam)
    draw_paper_texture(cv, alpha=0.5)
    labels(cv, cam)
    vignette(cv, 0.42)
    title_block(cv, year, title, sub)
    if legend_items: legend(cv, legend_items, title=legend_title)
    source_line(cv, src); plate_frame(cv); film_grain(cv, 0, 0.05)
    save_png(s, os.path.join(OUT, name)); print(name, f'{time.time() - t0:.2f}s')

ACQ = lambda pw, f=0.25: lighten(PAL[POW[pw][0]], f)
frame('map1_1773_after_first_partition.png', WIDE, stage_1773, labels_1773, '1773', 'After the First Partition',
      'The Commonwealth and its three neighbours',
      [('Polish–Lithuanian Commonwealth', PAL['plt'], False), ('Duchy of Courland (Polish fief)', PAL['plt'], True),
       ('Lost in 1772 (hatched)', PAL['paper_dark'], C(PAL['ink_soft'])), ('Commonwealth before 1772', PAL['paper'], False)])
frame('map2_1791_constitution.png', Camera.lonlat(23.6, 52.6, 0.80), stage_1791, labels_1791, '1791 – 1792', 'Reform and Reaction',
      'The Constitution of 3 May and the Russian intervention',
      [('Polish–Lithuanian Commonwealth', PAL['plt'], False), ('Russian Empire', PAL['russia'], False),
       ('Kingdom of Prussia', PAL['prussia'], False), ('Habsburg Monarchy', PAL['austria'], False)])
frame('map3_1793_second_partition.png', Camera.lonlat(23.8, 52.5, 0.80), lambda cv, cam: stage_1793(cv, cam), labels_1793,
      '1793', 'The Second Partition', 'Russia and Prussia annex; Austria does not take part',
      [('Remaining Commonwealth', PAL['plt'], False), ('Annexed by Russia, 1793', ACQ('russia'), True),
       ('Annexed by Prussia, 1793', ACQ('prussia'), True), ('Border before 1793 (dashed)', PAL['paper'], False)])
frame('map4_1794_kosciuszko_uprising.png', Camera.lonlat(22.6, 52.2, 1.12), stage_1794, labels_1794, '1794', 'The Kościuszko Uprising',
      'Documented events — dates and places only', [], src='Event sites: Wikipedia/OpenHistoricalMap coordinates · no troop routes are shown')
frame('map5_1795_third_partition.png', Camera.lonlat(23.0, 53.0, 0.92), lambda cv, cam: stage_1795(cv, cam), labels_1795,
      '1795', 'The Third Partition', 'Russia, Prussia and Austria divide the remainder',
      [('To Russia, 1795', ACQ('russia', .42), True), ('To Prussia, 1795', ACQ('prussia', .42), True),
       ('To Austria, 1795', ACQ('habsburg', .42), True)])
frame('map6_final_division.png', WIDE, stage_final, labels_final, '1772 · 1793 · 1795', 'Three Empires',
      'The former Commonwealth, divided',
      [('Russia  1772 / 1793 / 1795', lifted_tone('russia', '93'), False), ('Prussia  1772 / 1793 / 1795', lifted_tone('prussia', '93'), False),
       ('Austria  1772 / 1795', lifted_tone('habsburg', '93'), False), ('Commonwealth in 1772', PAL['plt'], False)],
      legend_title='Darker = earlier annexation')
