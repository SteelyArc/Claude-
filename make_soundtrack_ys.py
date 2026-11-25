# Epic score + sound design for "What if Yellowstone erupted?"
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'ys_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(640)
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

import math
def jhash(i, k):
    x = math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - math.floor(x)
def pluck(m, d=0.5, v=1.0):
    t = tt(d); f = mtof(m); s = (np.sin(2*np.pi*f*t) + 0.4*np.sin(4*np.pi*f*t) + 0.15*np.sin(6*np.pi*f*t)) * np.exp(-t * 9)
    return s * env(len(t), 0.002, 0.05) * v * 0.45
def marimba(m, d=0.6, v=1.0):
    t = tt(d); f = mtof(m); s = (np.sin(2*np.pi*f*t) + 0.25*np.sin(2*np.pi*f*4*t)*np.exp(-t*30)) * np.exp(-t * 6)
    return s * env(len(t), 0.002, 0.05) * v * 0.5
def taiko(d=0.9, f0=70):
    t = tt(d); f = f0 * (1 + 1.2*np.exp(-t*30)); s = np.sin(2*np.pi*phase(f)) * np.exp(-t*5) + lp(rng.standard_normal(len(t)), 900, 2) * np.exp(-t*25) * 2.5
    return s * env(len(t), 0.001, 0.2)
def brass(notes, d, bright=1600):
    t = tt(d); s = np.zeros(len(t))
    for m in notes:
        for det in (-0.06, 0.06): s += saw(phase(np.full(len(t), mtof(m+det)))) * 0.12
    e = env(len(t), 0.05, d*0.5); return lp(s, bright, 2) * e
def thunder(d=3.0, v=1.0):
    t = tt(d); crack = hp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 18) * 1.5
    rum = lp(rng.standard_normal(len(t)), 160, 3) * 9 * np.exp(-t * 1.1) * (0.6 + 0.4*np.sin(2*np.pi*3.3*t)**2)
    return (crack + rum) * env(len(t), 0.002, 0.8) * v
def crackle(d, rate):
    s = np.zeros(int(d*SR)); tc = 0.0
    while tc < d:
        i = int(tc*SR); n = int(SR*0.012); c = bp(rng.standard_normal(n), 800, 5000) * np.exp(-np.arange(n)/(SR*0.002))
        s[i:i+n] += c[:len(s)-i] * rng.uniform(0.3, 1.0); tc += rng.exponential(1/rate)
    return s
def bubble(f0=90, d=0.35):
    t = tt(d); f = f0 * (1 + 1.5*t/d); return np.sin(2*np.pi*phase(f)) * np.exp(-t*9) * env(len(t), 0.005, 0.05)
def moo(d=1.1, f0=140, happy=False):
    t = tt(d); f = f0 * (1 + (0.25 if happy else -0.2) * t / d) * (1 + 0.02*np.sin(2*np.pi*5*t))
    s = saw(phase(f)); s = bp(s, 200, 1400) * 0.8 + bp(s, 600, 900) * 0.6
    return s * env(len(t), 0.12, 0.35) * 0.35
def chatter(d=1.0):
    s = np.zeros(int(d*SR))
    for k in range(int(d*22)):
        i = int(k/22*SR); n = int(0.008*SR); s[i:i+n] += hp(rng.standard_normal(n), 2500) * np.exp(-np.arange(n)/(SR*0.0015))
    return s * 0.6
def birds(t0, d, n, g=0.05):
    for k in range(n):
        tb = t0 + rng.uniform(0, d); t = tt(0.22); f = 2800 + 1600*np.sin(2*np.pi*(8+rng.uniform(0,6))*t) + rng.uniform(-300, 600)
        place(np.sin(2*np.pi*phase(f)) * env(len(t), 0.01, 0.08) * g, tb, 1.0, rng.uniform(-0.7, 0.7))
CUTS = [2.6, 5, 11, 17, 23, 29, 41, 48, 54]
for c in CUTS: place(whoosh(0.45, 400, 5000), c - 0.3, 0.35, rng.uniform(-0.4, 0.4))
# 0–5: nature, the geyser, a curious bison, playful plucks (G major)
place(wind(5.2), 0.0, 0.07); birds(0.2, 4.6, 9)
place(whoosh(3.2, 300, 6000) * 0.9 + rumble(3.2, 300, 1.2), 0.0, 0.55)
place(moo(1.0, 150), 1.25, 0.9, -0.3)
mel = [67, 71, 74, 79, 78, 74, 76, 74, 71, 72, 74, 79]
for i, m in enumerate(mel): place(pluck(m, 0.5, 0.9), 0.25 + i * 0.4, 0.55, -0.3 + 0.05 * i)
for i, m in enumerate([43, 47, 50, 45, 43, 50]): place(pluck(m, 0.8, 1.0), 0.25 + i * 0.8, 0.5)
place(pad([55, 59, 62, 67], 2.6, 1500), 2.4, 0.35)
# 5–11: under the ground — minor drone, magma bubbles, rising pulse
place(pad([38, 45, 50], 6.2, 380), 5.0, 0.9); place(rumble(6.0, 80, 2.2), 5.0, 0.55)
for k in range(26): place(bubble(rng.uniform(60, 140)), 5.4 + rng.uniform(0, 5.4), 0.35, rng.uniform(-0.5, 0.5))
for i in range(11):
    tb = 5.6 + i * 0.5; place(taiko(0.6, 55), tb, 0.25 + 0.05 * i)
place(rumble(1.4, 140, 5.0) * np.linspace(0, 1, int(1.4 * SR)), 9.9, 0.7)
place(whoosh(1.2, 100, 3000), 10.2, 0.6)
# 11.35: THE ERUPTION
place(sub_boom(7.0), 11.35, 1.3); place(thunder(4.0, 1.4), 11.35, 0.8)
place(rumble(17.7, 110, 3.2), 11.4, 0.85)                     # constant roar
place(crackle(17.0, 40), 11.6, 0.25, -0.3); place(crackle(17.0, 40), 11.6, 0.25, 0.3)
# epic drums + brass (D minor) 12.4–28.2
beat = 0.5
for i in range(int((28.2 - 12.4) / beat)):
    tb = 12.4 + i * beat; place(taiko(0.9, 62 if i % 2 == 0 else 80), tb, 0.55 if i % 4 == 0 else 0.35, -0.2 if i % 2 else 0.2)
    if i % 8 == 6: place(taiko(0.4, 120), tb + 0.25, 0.3)
for t0, ch in [(12.4, [50, 57, 62]), (14.4, [46, 53, 58]), (16.4, [48, 55, 60]), (18.4, [45, 52, 57]), (20.4, [50, 57, 62]), (22.4, [46, 53, 58]), (24.4, [43, 50, 55]), (26.4, [45, 52, 57, 61])]:
    place(brass(ch, 2.05), t0, 0.42)
# thunder synced to the drawn lightning bolts (same hash as the page)
for k in range(int(14.4 * 6), int(29 * 6)):
    if jhash(k, 901) > 0.62 or jhash(k, 902) > 0.4: continue
    place(thunder(2.6, 0.5 + 0.5 * jhash(k, 903)), k / 6 + 0.05, 0.5, rng.uniform(-0.6, 0.6))
# 17–23: cubes stacking — ticks that speed up, then a heavy thud
prev = 0
for i in range(0, 600):
    tq = 18.4 + i * 0.005; a = tq - 17; n = 0 if a < 1.4 else min(999, round(999 * min(1, (a - 1.4) / 2.8) ** 1.6))
    if n // 40 > prev // 40: place(tick() * 0.8, tq, 0.35, rng.uniform(-0.5, 0.5))
    prev = n
place(tick(), 17.35, 0.6); place(taiko(1.2, 45), 21.4, 0.9)
# 23–29: the pyroclastic flow comes for the camera
place(whoosh(5.3, 60, 1500) * 1.4, 23.0, 1.0); place(rumble(5.3, 260, 5.0) * np.linspace(0.3, 1.0, int(5.3 * SR)), 23.0, 0.9)
place(whoosh(0.9, 100, 8000), 27.8, 0.9); place(sub_boom(2.5), 28.6, 0.8)
# 29–41: the ash spreads — ominous strings, low pulse, wind
place(pad([38, 41, 45, 50], 6.2, 600), 29.0, 0.7); place(pad([36, 43, 48, 51], 6.2, 600), 35.0, 0.7)
place(wind(12.0), 29.0, 0.12)
for i in range(24): place(heartbeat(), 29.3 + i * 0.5, 0.25)
for i, m in enumerate([62, 65, 69, 67, 65, 62, 60, 62]): place(piano(m, 2.4, 0.7), 29.4 + i * 1.45, 0.35, -0.2 + 0.05 * i)
for k in range(4): place(tick(), 35.6 + k * 0.5, 0.35)
# 41–48: volcanic winter — cold wind, sad piano, a shivering bison
place(wind(7.2) * 1.6, 41.0, 0.28); place(pad([45, 48, 52], 7.2, 700), 41.0, 0.4)
for i, m in enumerate([69, 67, 65, 64, 65, 64, 62, 64]): place(piano(m, 2.8, 0.8), 41.3 + i * 0.82, 0.5, 0.1 * (i % 3 - 1))
for k in range(3): place(chatter(0.9), 42.0 + k * 2.1, 0.55, -0.2)
place(moo(1.3, 120), 46.2, 0.7, -0.2)
# 48–54: "don't panic!" — relief, playful marimba (C major), counter whoosh
place(pad([60, 64, 67], 6.0, 1800), 48.0, 0.45)
for i, m in enumerate([72, 76, 79, 76, 77, 74, 71, 74, 76, 72, 67, 72]): place(marimba(m, 0.6, 0.9), 48.3 + i * 0.45, 0.55, -0.3 + 0.05 * i)
for i, m in enumerate([48, 55, 53, 55, 48, 55]): place(pluck(m, 0.9, 1.0), 48.3 + i * 0.9, 0.5)
place(whoosh(4.5, 300, 6000), 48.8, 0.35)
# 54–61: Old Faithful at sunset — happy finale
place(whoosh(4.0, 300, 6000) * 0.9 + rumble(4.0, 300, 1.0), 54.4, 0.5)
place(pad([55, 59, 62, 67], 7.0, 1800), 54.0, 0.5)
mel2 = [79, 78, 76, 74, 76, 79, 81, 79, 76, 74, 71, 74, 79]
for i, m in enumerate(mel2): place(pluck(m, 0.6, 0.9), 54.3 + i * 0.42, 0.55, -0.3 + 0.05 * i)
for i, m in enumerate([43, 50, 47, 50, 45, 52, 43, 50]): place(pluck(m, 0.9, 1.0), 54.3 + i * 0.75, 0.5)
place(moo(0.9, 150, happy=True), 56.0, 0.8, -0.3)
birds(54.5, 5.5, 10)
place(piano(55, 4.0, 1.0) + piano(59, 4.0, 0.8) + piano(62, 4.0, 0.8) + piano(67, 4.0, 0.7), 59.6, 0.55)
# mix
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
