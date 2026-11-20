"""Render a scene (or a time range of it) to an H.264 segment, or dump stills.
usage: render.py SCENE out.mp4 [t0 t1]   |   render.py --stills SCENE t1,t2,... outdir"""
import sys, subprocess, time, numpy as np, skia
import scenes
from engine import W, H, FPS
_g = skia.Surface(W, H)
def grade(s, name):
    """Final colour grade: gentle contrast S-curve + saturation for map scenes, warm lift for archival scenes."""
    img = s.makeImageSnapshot(); c = _g.getCanvas()
    if name in ('S1', 'S4', 'S5'): k, sat, off = 1.13, 1.10, -0.055
    else: k, sat, off = 1.04, 1.0, -0.01
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    def row(i):
        r = [(1 - sat) * lr, (1 - sat) * lg, (1 - sat) * lb]; r[i] += sat
        return [v * k for v in r] + [0, off]
    m = row(0) + row(1) + row(2) + [0, 0, 0, 1, 0]
    c.drawImage(img, 0, 0, skia.SamplingOptions(), skia.Paint(ColorFilter=skia.ColorFilters.Matrix(m)))
    return _g.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
def stills(name, ts, outdir):
    scenes.init(); sc = scenes.SCENES[name]
    s = skia.Surface(W, H)
    for t in ts:
        c = s.getCanvas(); t0 = time.time(); sc.render(c, t)
        from PIL import Image; Image.fromarray(grade(s, name)).save(f'{outdir}/{name}_{t:06.2f}.png'); print(name, t, f'{time.time()-t0:.2f}s', flush=True)
def video(name, out, t0=0.0, t1=None):
    scenes.init(); sc = scenes.SCENES[name]
    t1 = sc.dur if t1 is None else t1
    n0, n1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-tune', 'film', out], stdin=subprocess.PIPE)
    s = skia.Surface(W, H); st = time.time()
    for n in range(n0, n1):
        c = s.getCanvas(); sc.render(c, n / FPS)
        arr = grade(s, name)
        ff.stdin.write(arr.tobytes())
        if (n - n0) % 60 == 0: print(name, n, f'{(time.time()-st)/(n-n0+1):.2f}s/f', flush=True)
    ff.stdin.close(); ff.wait()
if __name__ == '__main__':
    if sys.argv[1] == '--stills': stills(sys.argv[2], [float(x) for x in sys.argv[3].split(',')], sys.argv[4])
    else: video(sys.argv[1], sys.argv[2], *(float(x) for x in sys.argv[3:5]))
