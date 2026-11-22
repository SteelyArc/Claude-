"""Bouncy oom-pah music + cartoon SFX for the 62 s solar-system short. All synthesized, deterministic (seeded).
uv run --with numpy python gen_audio.py  ->  music.wav, sfx.wav, mix.wav
"""
import numpy as np, wave
from pathlib import Path

SR, DUR = 44100, 62.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
OUT = Path(__file__).parent

def t_(d): return np.arange(int(SR * d)) / SR
def env(n, a=0.005, d=None, r=0.05):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    if d: e *= np.exp(-np.arange(n) / SR / d)
    nr = min(n, int(r * SR)); e[-nr:] *= np.linspace(1, 0, nr); return e
def lp(x, a):  # one-pole low-pass, a in (0,1]
    y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x): s += a * (v - s); y[i] = s
    return y
def lp_fast(x, cutoff):
    # FFT brickwall-ish low-pass (fast, fine for synthesis)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (f / cutoff) ** 4); return np.fft.irfft(X, len(x))
def hp_fast(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (cutoff / np.maximum(f, 1)) ** 4); return np.fft.irfft(X, len(x))
def bp_fast(x, lo, hi): return hp_fast(lp_fast(x, hi), lo)
def add(buf, x, at, gain=1.0):
    i = int(at * SR); j = min(len(buf), i + len(x));
    if j > i: buf[i:j] += x[: j - i] * gain
def hz(m): return 440 * 2 ** ((m - 69) / 12)

# ---------------- instruments ----------------
def tuba(m, d):
    t = t_(d); f = hz(m) * (1 + 0.02 * np.exp(-t * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * k) / k ** 1.3 for k in range(1, 7))
    return x * env(len(t), 0.012, 0.35, 0.04) * 0.5
def pluck(m, d, bright=0.5):  # Karplus-Strong
    n = int(SR * d); p = max(2, int(SR / hz(m))); buf = rng.uniform(-1, 1, p); out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.994 - 0.004 * (1 - bright))
    return out * env(n, 0.001, None, 0.03) * 0.5
def marimba(m, d):
    t = t_(d); f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 18) + 0.12 * np.sin(2 * np.pi * f * 10 * t) * np.exp(-t * 40)
    return x * env(len(t), 0.002, 0.28, 0.03) * 0.42
def woodblock(d=0.08, f=1400):
    t = t_(d); return np.sin(2 * np.pi * f * t) * np.exp(-t * 60) * 0.4
def shaker(d=0.06):
    n = int(SR * d); return hp_fast(rng.uniform(-1, 1, n), 6000) * env(n, 0.004, 0.02, 0.02) * 0.25

# ---------------- music ----------------
BPM = 128; B = 60 / BPM
prog = ['F', 'C7', 'F', 'Bb', 'F', 'C7', 'F', 'C7']   # one chord per bar (4 beats)
CH = {'F': [53, 57, 60], 'C7': [48, 52, 55, 58], 'Bb': [46, 50, 53], 'G7': [43, 47, 50, 53]}
ROOT = {'F': (41, 48), 'C7': (36, 43), 'Bb': (46, 41), 'G7': (43, 38)}
music = np.zeros(N)
# silly melody: chord-tone hops with grace notes, 8th notes, rests; deterministic pattern per bar
mel_pat = [[0, 2, None, 1, 2, None, 0, None], [1, None, 1, 2, 3, 2, None, None], [2, 1, 0, None, 2, None, 2, 1], [0, None, None, 2, 1, 0, None, None]]
bars = int(DUR / (4 * B)) + 1
for bar in range(bars):
    t0 = bar * 4 * B; ch = prog[bar % len(prog)]
    if t0 > 61.2: break
    sect = 'intro' if t0 < 4.4 else 'main'
    r, f5 = ROOT[ch]
    # oom (beats 1,3) pah (2,4)
    for b in range(4):
        tb = t0 + b * B
        if tb > 61.5: break
        if b % 2 == 0: add(music, tuba(r if b == 0 else f5, B * 0.9), tb, 0.9)
        else:
            for m in CH[ch]: add(music, pluck(m + 12, B * 0.6, 0.8), tb, 0.33)
        add(music, woodblock(f=1500 if b % 2 else 1100), tb + B / 2, 0.35)
        add(music, shaker(), tb + B / 4, 0.5); add(music, shaker(), tb + 3 * B / 4, 0.35)
    if sect == 'main':
        pat = mel_pat[bar % 4]; tones = CH[ch] + [CH[ch][0] + 12]
        for i, k in enumerate(pat):
            if k is None: continue
            m = tones[k % len(tones)] + 24
            if (bar + i) % 5 == 0: add(music, marimba(m - 1, 0.05), t0 + i * B / 2 - 0.04, 0.5)   # grace note
            add(music, marimba(m, B * 0.8), t0 + i * B / 2, 0.8)
# final stinger: F major "ta-da"
for k, m in enumerate([65, 69, 72, 77]): add(music, marimba(m, 1.2), 61.0 + k * 0.05, 0.9)
add(music, tuba(41, 1.0), 61.0, 1.0)

# ---------------- SFX ----------------
def whoosh(d=0.6, lo=300, hi=3000, up=True, amp=0.5):
    n = int(SR * d); x = rng.uniform(-1, 1, n); out = np.zeros(n); seg = 2048
    for i in range(0, n, seg):
        k = i / n; fc = lo + (hi - lo) * (k if up else 1 - k); out[i:i + seg] = bp_fast(x[i:i + seg], fc * 0.6, fc * 1.6)[: len(out[i:i + seg])]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5 * amp * 3
def slide(f0, f1, d, amp=0.35, vib=6):
    t = t_(d); f = f0 * (f1 / f0) ** (t / d) * (1 + 0.012 * np.sin(2 * np.pi * vib * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.25 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return x * env(len(t), 0.03, None, 0.08) * amp
def boing(f0=180, d=0.7, amp=0.55):
    t = t_(d); f = f0 * (1 + 0.6 * np.exp(-t * 6) * np.sin(2 * np.pi * 9 * t)) + 40 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4) * amp
def bonk(amp=0.8):
    t = t_(0.5); f = 420 * np.exp(-t * 4) + 120
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) + woodblock(0.5, 900)[: len(t)] * 1.2
    return x * amp
def snap(amp=0.7):
    t = t_(0.25); x = hp_fast(rng.uniform(-1, 1, len(t)), 2500) * np.exp(-t * 60) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 25) * 0.6
    return x * amp
def ding(f=1760, d=1.2, amp=0.35):
    t = t_(d); x = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
    return x * np.exp(-t * 3) * amp
def pop(f=600, amp=0.5):
    t = t_(0.12); fr = f * (1 + 2 * np.exp(-t * 50)); return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 35) * amp
def sizzle(d=2.0, amp=0.12):
    n = int(SR * d); x = hp_fast(rng.uniform(-1, 1, n), 4000) * (0.5 + 0.5 * (rng.uniform(0, 1, n) > 0.985))
    return x * env(n, 0.2, None, 0.6) * amp
def zip_(amp=0.35):
    return slide(500, 2400, 0.22, amp, 0)
def rattle(d=3.0, amp=0.5):
    out = np.zeros(int(SR * d)); r = np.random.default_rng(3)
    for k in range(int(d * 26)):
        at = r.uniform(0, d - 0.1); f = r.uniform(500, 1800); add(out, woodblock(0.05, f) * r.uniform(0.3, 1), at)
    return out * env(len(out), 0.3, None, 0.6) * amp
def bloop(amp=0.6):
    t = t_(0.35); f = 250 + 900 * (t / 0.35) ** 2; return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.01, 0.2, 0.05) * amp
def splash(amp=0.5):
    n = int(SR * 0.8); return bp_fast(rng.uniform(-1, 1, n), 800, 6000) * env(n, 0.005, 0.18, 0.2) * amp
def rumble(d=3.0, amp=0.5):
    t = t_(d); x = lp_fast(rng.uniform(-1, 1, len(t)), 180) * 4 * (0.7 + 0.3 * np.sin(2 * np.pi * 3.2 * t))
    return x * env(len(t), 0.2, None, 0.4) * amp
def boom(amp=0.8):
    t = t_(1.0); f = 90 * np.exp(-t * 3) + 35; return (np.sin(2 * np.pi * np.cumsum(f) / SR) + lp_fast(rng.uniform(-1, 1, len(t)), 300) * 0.8) * np.exp(-t * 4) * amp
def harp(t0, buf, amp=0.25):
    for k, m in enumerate([65, 69, 72, 77, 81, 84, 89]): add(buf, pluck(m, 0.8, 1.0), t0 + k * 0.045, amp)
def tick(amp=0.3): return woodblock(0.03, 2600) * amp

sfx = np.zeros(N)
for t0 in [0.3, 2.05, 3.8, 12.6, 14.35, 58.9, 60.65]: add(sfx, whoosh(0.7, 400, 1500, True, 0.18), t0)   # lantern swings
add(sfx, snap(), 5.28); add(sfx, slide(500, 2200, 1.5, 0.22), 5.35); add(sfx, ding(2093, 1.5, 0.3), 7.6)
add(sfx, slide(1800, 300, 0.7, 0.3, 9), 9.75); add(sfx, bonk(), 10.45); add(sfx, boing(160, 0.9, 0.4), 10.5)
for k in range(4): add(sfx, ding(2637 + k * 300, 0.5, 0.1), 10.7 + k * 0.35)
add(sfx, whoosh(1.6, 300, 3500, True, 0.35), 12.6); harp(15.1, sfx)
add(sfx, sizzle(2.4), 17.5); add(sfx, pop(700), 20.0)
add(sfx, slide(1500, 400, 1.8, 0.2, 7), 22.6); add(sfx, boing(220, 0.8, 0.5), 24.8); add(sfx, whoosh(0.8, 600, 4000, True, 0.4), 27.0)
add(sfx, zip_(), 29.6); add(sfx, zip_(), 31.2); add(sfx, sizzle(1.6, 0.14), 32.0); add(sfx, ding(1568, 1.2, 0.35), 32.3); add(sfx, ding(1568, 1.2, 0.3), 32.6)
add(sfx, rattle(3.4), 34.6)
add(sfx, whoosh(0.5, 300, 5000, True, 0.5), 38.95); add(sfx, boom(), 39.45); add(sfx, pop(500, 0.6), 41.0)
add(sfx, bloop(), 46.25); add(sfx, splash(), 46.3); add(sfx, bloop(0.4), 47.2)
add(sfx, rumble(3.0), 48.5); add(sfx, boing(120, 0.6, 0.35), 51.0)
add(sfx, whoosh(3.4, 200, 1200, True, 0.25), 51.5)
tk = 51.5
for i in range(40):
    tk += max(0.035, 0.14 * (1 - i / 40)); add(sfx, tick(), tk) if tk < 54.1 else None
add(sfx, ding(2093, 1.0, 0.35), 54.1)
add(sfx, whoosh(3.6, 200, 2500, False, 0.35), 55.0); add(sfx, whoosh(0.7, 500, 3000, True, 0.35), 58.8)

# duck music a little under the big hits
duck = np.ones(N)
for at in [5.28, 10.45, 24.8, 39.45, 46.3, 54.1]:
    i = int(at * SR); n = int(0.6 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], 0.55 + 0.45 * np.linspace(0, 1, len(duck[i:i + n])))
music *= duck
fade = np.ones(N); fade[: int(0.08 * SR)] = np.linspace(0, 1, int(0.08 * SR)); music *= fade

def norm(x, peak): return x / (np.max(np.abs(x)) + 1e-9) * peak
music = norm(music, 0.55); sfx = norm(sfx, 0.75)
mix = music + sfx; mix = np.tanh(mix * 1.1) / np.tanh(1.1); mix = norm(mix, 0.92)
def write(path, x):
    st = np.stack([x, np.roll(x, 40) * 0.98], 1)        # a touch of width
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(st, -1, 1) * 32767).astype('<i2').tobytes())
write(OUT / 'music.wav', music); write(OUT / 'sfx.wav', sfx); write(OUT / 'mix.wav', mix)
print('ok', OUT / 'mix.wav')
