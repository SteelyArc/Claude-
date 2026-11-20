"""Render the full film (or a time range) to H.264; or dump stills.  usage: render_film.py out.mp4 T0 T1 | --stills T1,T2 outdir"""
import sys, subprocess, time, skia, numpy as np
import film
from engine import W, H, FPS
film.setup()
_g = skia.Surface(W, H)
def grade(s):
    img = s.makeImageSnapshot(); c = _g.getCanvas()
    k, sat, off = 1.08, 1.06, -0.03
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    def row(i):
        r = [(1 - sat) * lr, (1 - sat) * lg, (1 - sat) * lb]; r[i] += sat
        return [v * k for v in r] + [0, off]
    c.drawImage(img, 0, 0, skia.SamplingOptions(), skia.Paint(ColorFilter=skia.ColorFilters.Matrix(row(0) + row(1) + row(2) + [0, 0, 0, 1, 0])))
    return _g.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
if __name__ == '__main__':
    s = skia.Surface(W, H)
    if sys.argv[1] == '--stills':
        from PIL import Image
        for T in [float(x) for x in sys.argv[2].split(',')]:
            t0 = time.time(); film.render_frame(s.getCanvas(), T)
            Image.fromarray(grade(s)).save(f'{sys.argv[3]}/F_{T:07.2f}.png'); print(T, f'{time.time()-t0:.2f}s', flush=True)
    else:
        out, T0, T1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
        n0, n1 = int(round(T0 * FPS)), int(round(T1 * FPS))
        ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-tune', 'film', out], stdin=subprocess.PIPE)
        st = time.time()
        for n in range(n0, n1):
            film.render_frame(s.getCanvas(), n / FPS); ff.stdin.write(grade(s).tobytes())
            if (n - n0) % 90 == 0: print(n, f'{(time.time()-st)/(n-n0+1):.2f}s/f', flush=True)
        ff.stdin.close(); ff.wait()
