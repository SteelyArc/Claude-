"""Mux + delivery encode.
  finalize.py preview VIDEO T0 T1 OUT   -> high-quality preview with the mix cut to [T0, T1]
  finalize.py final   VIDEO OUT         -> two-pass H.264 sized for TikTok (<= 400 MB), AAC 256k
  finalize.py srt     OUT               -> captions from the narration's word timings"""
import os, sys, subprocess, json, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import ROOT

MIX = f'{ROOT}/render/mix.wav'
COMMON = ['-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.2', '-r', '30', '-tune', 'film', '-preset', 'slow']


def run(cmd): subprocess.run(cmd, check=True)


def preview(video, t0, t1, out):
    d = float(t1) - float(t0)
    run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-ss', str(t0), '-t', str(d), '-i', MIX,
         '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', *COMMON, '-crf', '18', '-maxrate', '24M', '-bufsize', '48M',
         '-af', f'afade=t=out:st={d - 1.2:.2f}:d=1.2', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out])


def final(video, out, size_mb=370):
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video], capture_output=True, text=True).stdout)
    vb = int((size_mb * 8e6 / dur - 256e3) / 1000)   # kbit/s
    tmp = tempfile.mkdtemp(dir=f'{ROOT}/render'); log = f'{tmp}/x264'
    base = ['ffmpeg', '-v', 'error', '-y', '-i', video]
    run(base + ['-c:v', 'libx264', *COMMON, '-b:v', f'{vb}k', '-maxrate', f'{int(vb * 1.6)}k', '-bufsize', f'{int(vb * 2.5)}k',
                '-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', '/dev/null'])
    run(base + ['-i', MIX, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', *COMMON, '-b:v', f'{vb}k', '-maxrate', f'{int(vb * 1.6)}k',
                '-bufsize', f'{int(vb * 2.5)}k', '-pass', '2', '-passlogfile', log, '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
                '-shortest', '-movflags', '+faststart', out])
    print('video bitrate', vb, 'kbit/s')


def srt(out, max_chars=38):
    words = [(w['w'].strip(), w['s'], w['e']) for seg in json.load(open(f'{ROOT}/research/transcript_words.json')) for w in seg['words']]
    fix = {'Targovica': 'Targowica'}
    caps, cur = [], []
    for w in words:
        cur.append(w)
        line = ' '.join(x[0] for x in cur)
        if len(line) >= max_chars or w[0].endswith(('.', '?', '!')) or (w[0].endswith(',') and len(line) > 18):
            caps.append(cur); cur = []
    if cur: caps.append(cur)
    def ts(s): h, s = divmod(s, 3600); m, s = divmod(s, 60); return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}'
    with open(out, 'w') as f:
        for i, cp in enumerate(caps, 1):
            txt = ' '.join(fix.get(re.sub(r'[^\w]', '', x[0]), None) and x[0].replace(re.sub(r'[^\w]', '', x[0]), fix[re.sub(r'[^\w]', '', x[0])]) or x[0] for x in cp)
            txt = re.sub(r' -(?=\w)', '-', txt)
            f.write(f'{i}\n{ts(cp[0][1])} --> {ts(cp[-1][2])}\n{txt}\n\n')
    print(len(caps), 'captions')


if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'preview': preview(*sys.argv[2:6])
    elif m == 'final': final(sys.argv[2], sys.argv[3])
    elif m == 'srt': srt(sys.argv[2])
