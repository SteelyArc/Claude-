"""Frame-exact assembly of the rendered pieces into one 9000-frame master (near-lossless intermediate).
Each entry: (file, first_frame, n_frames)."""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import ROOT
R = f'{ROOT}/render'
SEGS = [(f'{R}/final_A.mp4', 0, 480), (f'{R}/fix_16_25.mp4', 0, 270), (f'{R}/final_A.mp4', 750, 3750),
        (f'{R}/partsB/p0.mp4', 0, 675), (f'{R}/partsB/fill0.mp4', 0, 450), (f'{R}/partsB/p1.mp4', 0, 1125),
        (f'{R}/partsB/p2.mp4', 0, 1125), (f'{R}/partsB/p3.mp4', 0, 975), (f'{R}/partsB/fill3.mp4', 0, 150)]
# later patches override frames of the base list: (file, first_frame_on_timeline, n)
PATCHES = [(f'{R}/fix_23_30.mp4', 690, 210), (f'{R}/fix_44_52.mp4', 1320, 240), (f'{R}/fix_174_195.mp4', 5220, 630)]
base, pos = [], 0
for f, a, n in SEGS: base.append((f, a, n, pos)); pos += n
for pf, p0, pn in PATCHES:
    new = []
    for f, a, n, t in base:
        if t + n <= p0 or t >= p0 + pn: new.append((f, a, n, t)); continue
        if t < p0: new.append((f, a, p0 - t, t))
        if t + n > p0 + pn: d = p0 + pn - t; new.append((f, a + d, n - d, p0 + pn))
    new.append((pf, 0, pn, p0)); base = sorted(new, key=lambda x: x[3])
SEGS = [(f, a, n) for f, a, n, t in base]
assert sum(s[2] for s in SEGS) == 9000
files = list(dict.fromkeys(s[0] for s in SEGS))
cmd = ['ffmpeg', '-v', 'error', '-y']
for f in files: cmd += ['-i', f]
fc = ''.join(f'[{files.index(f)}:v]trim=start_frame={a}:end_frame={a + n},setpts=PTS-STARTPTS[v{i}];' for i, (f, a, n) in enumerate(SEGS))
fc += ''.join(f'[v{i}]' for i in range(len(SEGS))) + f'concat=n={len(SEGS)}:v=1:a=0[out]'
pre = ''
for k, f in enumerate(files):   # split inputs used more than once
    m = sum(1 for s in SEGS if s[0] == f)
    if m > 1:
        pre += f'[{k}:v]split={m}' + ''.join(f'[s{k}_{j}]' for j in range(m)) + ';'
        for j in range(m): fc = fc.replace(f'[{k}:v]', f'[s{k}_{j}]', 1)
fc = pre + fc
cmd += ['-filter_complex', fc, '-map', '[out]', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', f'{R}/master.mp4']
subprocess.run(cmd, check=True); print('master written')
