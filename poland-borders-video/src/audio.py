import os, wave
import numpy as np
from render import build_timeline, BUILD

SR = 48000
TL = build_timeline()
N = int((TL['total'] + 0.5) * SR)
rng = np.random.default_rng(5)


def load_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    # resample to SR (linear)
    x = np.linspace(0, len(a) - 1, int(len(a) * SR / sr))
    return np.interp(x, np.arange(len(a)), a)


def lp(x, a):
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)


# ---- voice
vo = np.zeros(N, np.float32)
for v in TL['vo']:
    a = load_wav(v['path'])
    i = int(v['t'] * SR)
    vo[i:i + len(a)] += a[:N - i]
vo *= 0.95 / (np.abs(vo).max() + 1e-6)

# ---- music: slow minor progression pad + plucked arpeggio
t = np.arange(N) / SR
def midi(n): return 440 * 2 ** ((n - 69) / 12)
prog = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64]]   # Dm Bb F C
bar = 4.0
pad = np.zeros(N, np.float32)
arp = np.zeros(N, np.float32)
nb = int(TL['total'] / bar) + 2
dark_t = TL['total'] - 15.5
for b in range(nb):
    s0 = b * bar
    chord = prog[b % 4] if s0 < dark_t else [38, 45, 50, 53]
    i0, i1 = int(s0 * SR), min(N, int((s0 + bar + 1.5) * SR))
    if i0 >= N:
        break
    tt = np.arange(i1 - i0) / SR
    env = np.minimum(1, tt / 1.2) * np.exp(-np.maximum(0, tt - bar) / 0.6)
    for n in chord:
        f = midi(n)
        sig = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 0.3) + 0.12 * np.sin(2 * np.pi * 3.01 * f * tt)
        sig *= 1 + 0.003 * np.sin(2 * np.pi * 0.3 * tt)
        pad[i0:i1] += (sig * env * 0.06).astype(np.float32)
    # arpeggio (Karplus-Strong plucks), 8th notes at 4 notes/beat pattern
    if s0 < dark_t:
        pattern = [chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 12, chord[1] + 12, chord[3] + 12, chord[2] + 24, chord[3] + 12]
        for k, n in enumerate(pattern):
            st = s0 + k * bar / 8
            f = midi(n)
            L = int(SR / f)
            buf = rng.uniform(-1, 1, L).astype(np.float32)
            dur = int(1.6 * SR)
            out = np.zeros(dur, np.float32)
            for j in range(dur):
                if j >= L:
                    break
            # vectorised KS approximation: decaying harmonic tone
            tt2 = np.arange(dur) / SR
            out = (np.sin(2 * np.pi * f * tt2) * 0.7 + 0.3 * np.sin(2 * np.pi * 2 * f * tt2)) * np.exp(-tt2 * 3.2)
            out[:200] *= np.linspace(0, 1, 200)
            j0 = int(st * SR)
            if j0 < N:
                arp[j0:j0 + dur] += (out[:N - j0] * 0.035).astype(np.float32)
music = lp(pad, 0.85) + lp(arp, 0.6)
# low heartbeat drum in war scene & outro
def kick(at, amp=0.35):
    i = int(at * SR)
    tt = np.arange(int(0.4 * SR)) / SR
    k = np.sin(2 * np.pi * (55 + 60 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 9) * amp
    music[i:i + len(k)] += k[:max(0, N - i)]
war = [s for s in TL['scenes'] if s['i'] == 9][0]
bt = war['start']
while bt < war['end']:
    kick(bt); kick(bt + 0.28, 0.2); bt += 1.4
out = TL['scenes'][-1]
if out['darken']:
    bt = out['darken']
    while bt < TL['total'] - 3:
        kick(bt, 0.4); bt += 1.8

# fades
music *= np.minimum(1, t / 2.0) * np.clip((TL['total'] - t) / 3.0, 0, 1)
# sidechain duck under voice
envv = lp(np.abs(vo), 0.9995)
envv = envv / (envv.max() + 1e-6)
duck = 1 - 0.55 * np.clip(envv * 4, 0, 1)
music = music / (np.abs(music).max() + 1e-6) * 0.32 * duck

# ---- sfx
sfx = np.zeros(N, np.float32)
def thump(at, amp=0.5):
    i = int(at * SR)
    d = int(0.5 * SR)
    tt = np.arange(d) / SR
    n = rng.uniform(-1, 1, d)
    low = lp(n, 0.97) * np.exp(-tt * 18) * 6
    rustle = (n - lp(n, 0.5)) * np.exp(-tt * 9) * 0.25
    body = np.sin(2 * np.pi * 90 * tt) * np.exp(-tt * 22) * 0.6
    s = (low + rustle + body) * amp
    sfx[i:i + d] += s[:max(0, N - i)].astype(np.float32)
def whoosh(at, dur, amp=0.18):
    i = int(at * SR)
    d = int(dur * SR)
    tt = np.linspace(0, 1, d)
    n = rng.uniform(-1, 1, d)
    s = (lp(n, 0.8) - lp(n, 0.97)) * np.sin(np.pi * tt) ** 2 * amp * 3
    sfx[i:i + d] += s[:max(0, N - i)].astype(np.float32)
for tr in TL['trans']:
    if tr['kind'] == 'drop':
        whoosh(tr['t'], tr['dur'] * 0.7, 0.12)
        thump(tr['t'] + tr['dur'] * 0.7)
    elif tr['kind'] == 'dropfade':
        whoosh(tr['t'], tr['dur'] * 0.7, 0.15)
        thump(tr['t'] + tr['dur'] * (0.25 + 0.75 * 0.7))
    elif tr['kind'] == 'fade':
        whoosh(tr['t'], tr['dur'] + 0.4, 0.14)
for s in TL['scenes'][1:]:
    whoosh(s['start'] - 0.2, 1.2, 0.08)   # camera move
    # paper flick for badge
    thump(s['start'] + 0.35, 0.12)

mix = vo + music + sfx
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix /= max(1e-6, np.abs(mix).max()) / 0.92
st = np.stack([mix, mix], -1)
st[:, 1] = np.concatenate([[0] * 24, mix[:-24]])  # tiny width
with wave.open(os.path.join(BUILD, 'audio.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print('audio done', N / SR)
