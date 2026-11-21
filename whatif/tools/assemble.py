"""Frame-exact assembly of the rendered pieces into one 9000-frame master (near-lossless intermediate).
Each entry: (file, first_frame, n_frames)."""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import ROOT
R = f'{ROOT}/render'
SEGS = [(f'{R}/final_A.mp4', 0, 480), (f'{R}/fix_16_25.mp4', 0, 270), (f'{R}/final_A.mp4', 750, 3750),
        (f'{R}/partsB/p0.mp4', 0, 675), (f'{R}/partsB/fill0.mp4', 0, 450), (f'{R}/partsB/p1.mp4', 0, 1125),
        (f'{R}/partsB/p2.mp4', 0, 1125), (f'{R}/partsB/p3.mp4', 0, 975), (f'{R}/partsB/fill3.mp4', 0, 150)]
assert sum(s[2] for s in SEGS) == 9000
files = list(dict.fromkeys(s[0] for s in SEGS))
cmd = ['ffmpeg', '-v', 'error', '-y']
for f in files: cmd += ['-i', f]
fc = ''.join(f'[{files.index(f)}:v]trim=start_frame={a}:end_frame={a + n},setpts=PTS-STARTPTS[v{i}];' for i, (f, a, n) in enumerate(SEGS))
fc += ''.join(f'[v{i}]' for i in range(len(SEGS))) + f'concat=n={len(SEGS)}:v=1:a=0[out]'
# final_A is used twice: split it
k = files.index(f'{R}/final_A.mp4')
fc = f'[{k}:v]split=2[A0][A1];' + fc.replace(f'[{k}:v]', '[A0]', 1).replace(f'[{k}:v]', '[A1]', 1)
cmd += ['-filter_complex', fc, '-map', '[out]', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', f'{R}/master.mp4']
subprocess.run(cmd, check=True); print('master written')
