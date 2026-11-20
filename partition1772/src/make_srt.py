"""Write an SRT for the preview timeline (narration clock -> preview clock)."""
import sys
from subtitles import CUES
MAP = [(0.0, 31.95, 1.0), (168.40, 181.50, 33.75 + 0.5 - 168.40), (248.50, 261.05, 33.75 + 0.5 + 13.10 - 248.50),
       (304.30, 315.35, 60.90 + 0.6 - 304.30), (315.35, 372.25, 73.05 - 315.35), (372.25, 388.0, 129.95 - 372.25)]
def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"
out = []; n = 1
for c in CUES:
    for a0, a1, off in MAP:
        if a0 - 0.3 <= c['s'] < a1:
            out.append(f"{n}\n{ts(c['s'] + off)} --> {ts(min(c['hold'], a1) + off)}\n{c['t']}\n"); n += 1; break
open(sys.argv[1], 'w').write('\n'.join(out)); print(n - 1, 'cues')
