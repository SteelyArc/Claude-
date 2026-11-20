"""Phase 3 vertical preview: narration 287.3-329.7 s (Third Partition -> abdication -> vanished map).
Renders frames in parallel chunks, then muxes the untouched narration slice + music bed."""
import sys, os, subprocess, math, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from map_stages import *
from fx import *
import numpy as np
from multiprocessing import Pool

FPS = 30
A0, A1 = 287.3, 329.7            # narration window (seconds of the original audio)
N = int(round((A1 - A0) * FPS))
ARC = os.path.join(ROOT, 'assets', 'archive')
IMG = {
    'cary': 'A_new_map_of_Poland_and_the_Grand_Duchy_of_Lithuania_shewing_their_dismemberments.jpg',
    'king': 'Marcello_Bacciarelli_-_Portrait_of_Stanis_aw_August_Poniatowski_with_hourglass_-.jpg',
    'catherine': 'Catherine_II_by_J.B.Lampi_1793_Hermitage_.jpg',
    'fw2': 'Anton_Graff_-_Frederick_William_II_of_Prussia.png',
    'francis': 'Christian_Wilhelm_Ketterlinus_Francis_II_Holy_Roman_Emperor_1792_NGA_78568.jpg',
}
# face centres (normalised) for medallion / portrait framing — set after inspecting each image
FACE = {'king': (0.5, 0.3), 'catherine': (0.5, 0.25), 'fw2': (0.5, 0.28), 'francis': (0.5, 0.22)}
FACE.update(json.load(open(os.path.join(ROOT, 'research', 'faces.json'))) if os.path.exists(os.path.join(ROOT, 'research', 'faces.json')) else {})

def img(k):
    import glob
    m = sorted(glob.glob(os.path.join(ARC, IMG[k][:40] + '*')))
    return load_image(m[0]) if m and os.path.getsize(m[0]) > 1000 else None

C_RUMP = Camera.lonlat(24.4, 53.0, 0.98)
C_WAR = Camera.lonlat(21.5, 52.35, 1.40)
C_KRA = Camera.lonlat(21.3, 50.95, 1.40)
C_WIDE = Camera.lonlat(23.8, 52.9, 0.92)
C_FIN = Camera.lonlat(24.0, 52.7, 0.80)

def cam_at(a):
    keys = [(291.3, C_RUMP), (294.5, Camera.lerp(C_RUMP, C_RUMP, 0)), (297.2, C_WAR), (298.1, C_WAR), (300.4, C_KRA), (302.2, C_KRA), (305.2, C_WIDE)]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if a <= t1:
            return Camera.lerp(c0, c1, ease(seg(a, t0, t1)))
    # gentle continuing drift
    d = seg(a, 305.2, 314.0); c = Camera.lerp(C_WIDE, Camera.lonlat(23.8, 52.9, 0.97), d); return c

def finish(cv, fi, vig=0.45):
    vignette(cv, vig); film_grain(cv, fi, 0.05)

# ------------------------------------------------------------------ shots
def shot_document(a, fi):
    s = new_surface(); cv = s.getCanvas(); dark_desk(cv)
    t = seg(a, A0, 292.2); im = img('cary')
    if im is not None:
        document(cv, im, t, focus=(0.5, 0.5), zoom0=1.0, zoom1=1.55, tilt0=0.35, settle=(0.0, 0.5), sweep=(0.2, 0.75))
    al = eseg(a, A0 + 0.2, A0 + 1.0)
    draw_text(cv, 'THE FINAL DIVISION', W / 2, 330, font('caps', 46), '#E7D3A2', align='center', tracking=0.32, alpha=al, shadow=True)
    draw_text(cv, '1795', W / 2, 410, font('serif_bold', 60), '#F4EAD2', align='center', alpha=al, shadow=True)
    caption(cv, 'John Cary, A New Map of Poland … shewing their dismemberments, London, 1799', alpha=al * 0.95, y=1585, dark=True)
    finish(cv, fi, 0.5); return s

MED = {'catherine': (850, 1395, 'Catherine II', 'Russia', 292.0), 'fw2': (230, 1395, 'Frederick William II', 'Prussia', 294.7),
       'francis': (540, 1395, 'Francis II', 'Austria', 298.2)}

def shot_map1795(a, fi):
    s = new_surface(); cv = s.getCanvas(); cam = cam_at(a)
    params = {'rus': eseg(a, 292.0, 294.1), 'pru': eseg(a, 294.8, 296.8), 'aut': eseg(a, 298.3, 300.3)}
    draw_base(cv, cam); stage_1795(cv, cam, params); draw_physical_overlay(cv, cam); coast_line(cv, cam)
    draw_paper_texture(cv, alpha=0.5)
    labels_1795(cv, cam, al=eseg(a, 300.6, 301.8))
    # city pulses on the spoken word
    for c, tw in (('Warsaw', 297.16), ('Kraków', 301.48)):
        al = eseg(a, tw - 0.6, tw)
        if al > 0:
            event_marker(cv, cam, *CITIES[c], '', c, {'Warsaw': 'to Prussia', 'Kraków': 'to Austria'}[c], 'right', alpha=al,
                         pulse=seg(a, tw, tw + 1.2) if a < tw + 1.2 else 0)
    vignette(cv, 0.42)
    title_block(cv, '1795', 'The Third Partition', 'Russia · Prussia · Austria')
    # cameo rail of the three partitioning monarchs
    hl = eseg(a, 310.9, 311.8) * (1 - eseg(a, 312.8, 313.4))
    if a > 291.8:
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 1180), skia.Point(0, H)],
                                            [skia.Color4f(0.94, 0.9, 0.8, 0), skia.Color4f(0.94, 0.9, 0.8, 0.82 * eseg(a, 291.8, 292.6))], [0, 0.45])
        cv.drawRect(skia.Rect(0, 1180, W, H), skia.Paint(Shader=sh))
    for k, (x, y, nm, sub, t_in) in MED.items():
        im = img(k)
        if im is None: continue
        al = eseg(a, t_in, t_in + 0.8); pop = 1 + 0.06 * (1 - eseg(a, t_in, t_in + 0.8)) + 0.05 * hl
        medallion(cv, im, x, y - 20 * (1 - al), 100 * pop, face=FACE[k], zoom=2.2, alpha=al, name=nm, sub=sub)
    # statement on 'ceased to exist'
    al = eseg(a, 306.1, 306.9) * (1 - eseg(a, 312.6, 313.2))
    if al > 0:
        caption(cv, 'The Polish–Lithuanian state ceases to exist as an independent state', alpha=al, y=425)
    source_line(cv, 'Borders: OpenHistoricalMap (CC0), verified against atlas reference · Portraits: Wikimedia Commons (PD / CC0)')
    plate_frame(cv); film_grain(cv, fi, 0.05); return s

def shot_portrait(a, fi):
    s = new_surface(); cv = s.getCanvas(); cv.drawColor(C('#1E1610'))
    im = img('king'); t = seg(a, 313.3, 323.4)
    if im is not None:
        parallax_portrait(cv, im, t, face=FACE['king'], push=(1.0, 1.10), depth=0.05, desat=0.55 * eseg(a, 318.5, 322.8))
    dust(cv, a, alpha=0.3)
    name_card(cv, 'Stanisław August Poniatowski', 'King of Poland and Grand Duke of Lithuania, 1764–1795', seg(a, 314.3, 315.3), y=1345)
    al = eseg(a, 316.1, 316.9) * (1 - eseg(a, 319.7, 320.2))
    date_card(cv, 'ABDICATION · GRODNO', '25 November 1795', None, seg(a, 316.1, 316.9), alpha=al, y=430)
    al2 = eseg(a, 320.3, 321.0)
    date_card(cv, 'TAKEN TO RUSSIA', 'St Petersburg', 'left Grodno in 1797 · died there in 1798', seg(a, 320.3, 321.0), alpha=al2, y=430)
    caption(cv, 'Marcello Bacciarelli, Portrait of Stanisław August with an hourglass · National Museum in Warsaw', alpha=0.85 * eseg(a, 314.6, 315.4), y=1585, dark=True)
    finish(cv, fi, 0.5); return s

def shot_final(a, fi):
    s = new_surface(); cv = s.getCanvas()
    cam = Camera.lerp(Camera.lonlat(24.0, 52.7, 0.86), C_FIN, ease(seg(a, 322.6, 329.7)))
    out = 1 - eseg(a, 327.9, 329.4)
    draw_base(cv, cam); stage_final(cv, cam, {'outline': out}); draw_physical_overlay(cv, cam); coast_line(cv, cam)
    draw_paper_texture(cv, alpha=0.5); labels_final(cv, cam, al=eseg(a, 323.0, 324.0))
    vignette(cv, 0.42)
    title_block(cv, '1772 · 1793 · 1795', 'Gone from the Map', 'The Commonwealth divided between three empires', alpha=eseg(a, 323.2, 324.2))
    legend(cv, [('Commonwealth in 1772', PAL['plt'], False)], alpha=out * eseg(a, 323.6, 324.4), y=1440)
    source_line(cv, 'Borders: OpenHistoricalMap (CC0), verified against atlas reference · Physical: Natural Earth')
    plate_frame(cv); film_grain(cv, fi, 0.05); return s

def arr(s):
    a = s.makeImageSnapshot().toarray()  # RGBA or BGRA depending on platform
    if s.makeImageSnapshot().colorType() == skia.kBGRA_8888_ColorType: a = a[..., [2, 1, 0, 3]]
    return np.ascontiguousarray(a[..., :3])

def frame(fi):
    a = A0 + fi / FPS
    if a < 291.3: return arr(shot_document(a, fi))
    if a < 292.2: return deckle_wipe(arr(shot_document(a, fi)), arr(shot_map1795(a, fi)), seg(a, 291.3, 292.2))
    if a < 313.3: return arr(shot_map1795(a, fi))
    if a < 314.3: return deckle_wipe(arr(shot_map1795(a, fi)), arr(shot_portrait(a, fi)), seg(a, 313.3, 314.3))
    if a < 322.6: return arr(shot_portrait(a, fi))
    if a < 323.4: return crossfade(arr(shot_portrait(a, fi)), arr(shot_final(a, fi)), seg(a, 322.6, 323.4))
    f = arr(shot_final(a, fi))
    fade = seg(a, A1 - 0.5, A1)
    return (f * (1 - fade)).astype(np.uint8) if fade > 0 else f

def render_chunk(args):
    k, lo, hi, out = args
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(lo, hi):
        p.stdin.write(frame(fi).tobytes())
        if (fi - lo) % 60 == 0: print(f'chunk {k}: {fi - lo}/{hi - lo}  {time.time() - t0:.0f}s', flush=True)
    p.stdin.close(); p.wait(); return out

if __name__ == '__main__':
    outdir = os.path.join(ROOT, 'previews', 'phase3'); tmp = os.path.join(outdir, 'chunks'); os.makedirs(tmp, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'stills':
        for a in [float(x) for x in sys.argv[2:]]:
            fi = int(round((a - A0) * FPS)); from PIL import Image
            Image.fromarray(frame(fi)).save(os.path.join(outdir, f'still_{a:.1f}.png')); print('still', a)
        sys.exit()
    nw = 4; bounds = [round(N * i / nw) for i in range(nw + 1)]
    jobs = [(i, bounds[i], bounds[i + 1], os.path.join(tmp, f'c{i}.mp4')) for i in range(nw)]
    with Pool(nw) as pool: outs = pool.map(render_chunk, jobs)
    open(os.path.join(tmp, 'list.txt'), 'w').write(''.join(f"file '{o}'\n" for o in outs))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'list.txt'), '-c', 'copy', os.path.join(tmp, 'video.mp4')], check=True)
    print('video done', N, 'frames')
