# Serious cinematic score for "What if a nuclear bomb went off over New York City?"
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'nyc_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(1945)
L = np.zeros(N); Rr = np.zeros(N)
def tt(d): return np.arange(int(d * SR)) / SR
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a=0.01, r=0.05):
    e = np.ones(n); na = max(1, min(n // 2, int(a * SR))); nr = max(1, min(n // 2, int(r * SR)))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def place(sig, t0, g=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[:N - i] * g; l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * l * 1.41; Rr[i:i + len(sig)] += sig * r * 1.41
def phase(f): return np.cumsum(f) / SR
def saw(ph): return 2 * (ph % 1.0) - 1
# instruments
def pad(notes, d, bright=900):
    t = tt(d); s = np.zeros(len(t))
    for m in notes:
        for det in (-0.08, 0.0, 0.08):
            s += saw(phase(np.full(len(t), mtof(m + det)))) * 0.15
    return lp(s, bright, 2) * env(len(t), d * 0.35, d * 0.4)
def piano(m, d=2.5, v=1.0):
    t = tt(d); f = mtof(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (1.6 + k * 0.9)) / k for k in range(1, 7))
    return s * env(len(t), 0.003, 0.4) * v * 0.5
def sub_boom(d=6.0):
    t = tt(d); f = 22 + 60 * np.exp(-t * 2.5)
    return (np.sin(2 * np.pi * phase(f)) * np.exp(-t * 0.7) * 1.4 + lp(rng.standard_normal(len(t)), 180, 3) * 4 * np.exp(-t * 0.6)) * env(len(t), 0.004, 1.0)
def rumble(d, f=120, amp=3.0):
    t = tt(d); return lp(rng.standard_normal(len(t)), f, 3) * amp * env(len(t), d * 0.2, d * 0.3)
def wind(d):
    t = tt(d); x = bp(rng.standard_normal(len(t)), 300, 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t)); return x * env(len(t), 0.8, 1.0)
def heartbeat():
    t = tt(0.5); b = lambda: np.sin(2 * np.pi * phase(55 * np.exp(-tt(0.18) * 6) + 35)) * np.exp(-tt(0.18) * 18)
    s = np.zeros(len(t)); a = b(); s[:len(a)] += a; i = int(0.17 * SR); s[i:i + len(a)] += 0.7 * a[:len(s) - i]; return s
def tinnitus(d):
    t = tt(d); return np.sin(2 * np.pi * 4100 * t) * 0.05 * env(len(t), 0.05, d * 0.8)
def shatter(d=1.6):
    t = tt(d); x = hp(rng.standard_normal(len(t)), 3500) * np.exp(-t * 3)
    x *= (rng.random(len(t)) > 0.85)
    tones = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * (4 + k)) for k, f in enumerate([3200, 4700, 6100, 7900])) * 0.08
    return (x * 0.9 + tones)
def whoosh(d, lo=200, hi=3000):
    t = tt(d); x = bp(rng.standard_normal(len(t)), lo, hi) * np.sin(np.pi * t / d) ** 2; return x
def geiger(d, rate):
    s = np.zeros(int(d * SR)); tc = 0.0
    while tc < d:
        i = int(tc * SR); c = hp(rng.standard_normal(60), 2000) * np.exp(-np.arange(60) / 8); s[i:i + 60] += c[:len(s) - i]
        tc += rng.exponential(1 / rate)
    return s
def tick():
    t = tt(0.04); return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120)
def bell(f, d=3.0):
    t = tt(d); return sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t * (0.8 + i * 0.7)) for i, r in enumerate([1, 2.76, 5.4])) * env(len(t), 0.002, 0.6) * 0.3
# --- score ---
# 0–6: calm morning city, piano + soft pad, clock ticking towards the flash
for t0, notes in [(0.0, [57, 64, 69]), (3.0, [55, 62, 67])]: place(pad(notes, 3.4, 700), t0, 0.45)
for i, m in enumerate([76, 74, 72, 69, 72, 74]): place(piano(m, 2.2, 0.8), 0.3 + i * 0.85, 0.5, -0.2 + 0.08 * i)
for t0 in np.arange(0.5, 6.0, 0.5): place(tick(), t0, 0.25, 0.3)
place(wind(6.0), 0.0, 0.08)
# 6.0: flash — silence, then high whine, then the boom
place(whoosh(0.25, 2000, 9000), 5.95, 0.4)
place(tinnitus(4.5), 6.05, 1.0)
place(sub_boom(7.0), 6.4, 1.0)
# 11–17 fireball: deep drone + low rumble
place(pad([33, 40, 45], 6.0, 300), 11.0, 0.9); place(rumble(6.0, 90, 2.5), 11.0, 0.6)
# 17–23 map: low tension pulse
for i in range(12): place(heartbeat(), 17.2 + i * 0.5, 0.55)
place(pad([45, 48, 52], 6.0, 500), 17.0, 0.5)
# 23–29 shock wave: rising roar, impact, shattering glass
place(whoosh(4.0, 80, 1200), 23.0, 1.2); place(rumble(6.0, 200, 4.5), 23.2, 0.9)
place(sub_boom(5.0), 27.0, 0.8)
for k in range(5): place(shatter(), 25.3 + k * 0.45, 0.35, rng.uniform(-0.7, 0.7))
# 29–35 mushroom cloud: huge low drone + wind
place(pad([28, 35, 40, 47], 6.0, 400), 29.0, 1.0); place(rumble(6.0, 70, 3.0), 29.0, 0.7); place(wind(6.0), 29.0, 0.2)
# 35–41 radiation: Geiger counter clicks speeding up
place(geiger(6.0, 6) + geiger(6.0, 1) * 0, 35.0, 0.35, 0.2); place(geiger(3.0, 30), 38.0, 0.3, -0.2)
place(pad([40, 43, 47], 6.0, 450), 35.0, 0.6)
# 41–48 Hiroshima: quiet piano, temple bell, water
for i, m in enumerate([69, 72, 76, 74, 72, 69, 67, 69]): place(piano(m, 3.0, 0.8), 41.3 + i * 0.82, 0.55, -0.3 + 0.08 * i)
place(bell(220, 5.0), 41.2, 0.6); place(bell(220, 5.0), 45.4, 0.4)
place(bp(rng.standard_normal(int(7 * SR)), 400, 2500) * 0.05, 41.0, 1.0)
place(pad([45, 52, 57, 60], 7.0, 600), 41.0, 0.45)
# 48–54 12,000 warheads: building tension
for i in range(24):
    tt0 = 48.4 + i * (5.4 / 24) ** 1.0
    place(heartbeat(), tt0, 0.25 + 0.4 * i / 24)
place(pad([38, 45, 50, 53], 6.0, 800), 48.0, 0.7); place(rumble(5.5, 150, 2.0), 48.5, 0.5)
# 54–61 hope: major chord, piano melody, birds
place(pad([60, 64, 67, 72], 7.0, 1400), 54.0, 0.6)
for i, m in enumerate([72, 76, 79, 77, 76, 72, 74, 72]): place(piano(m, 2.6, 0.9), 54.4 + i * 0.75, 0.55, -0.2 + 0.06 * i)
place(piano(60, 4.0, 1.0) + piano(64, 4.0, 0.8) + piano(67, 4.0, 0.8), 59.8, 0.6)
for k in range(8):
    tt0 = 54.6 + k * 0.6; t = tt(0.25); f = 3000 + 1500 * np.sin(2 * np.pi * 9 * t)
    place(np.sin(2 * np.pi * phase(f)) * env(len(t), 0.01, 0.1) * 0.05, tt0, 1.0, rng.uniform(-0.6, 0.6))
# mix
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
