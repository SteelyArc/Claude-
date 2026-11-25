# Calm, wondrous score for "What if Earth had rings like Saturn?"
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'er_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(2270)
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

def chime(m, d=1.6, v=1.0):
    t = tt(d); f = mtof(m); s = sum(np.sin(2*np.pi*f*r*t) * np.exp(-t*(2.2+i*1.6)) / (1+i) for i, r in enumerate([1, 2.0, 3.01, 4.2]))
    return s * env(len(t), 0.002, 0.3) * v * 0.35
def clink(f=None):
    f = f or rng.uniform(2500, 6000); t = tt(0.25); return (np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*f*1.53*t)) * np.exp(-t*28) * 0.4
def waves(d):
    t = tt(d); x = lp(rng.standard_normal(len(t)), 900, 2) * (0.35 + 0.65*np.sin(np.pi*((t/3.2) % 1))**2) + hp(rng.standard_normal(len(t)), 3000) * 0.15 * np.sin(np.pi*((t/3.2) % 1))**4
    return x * env(len(t), 0.5, 0.5)
def gull(): t = tt(0.5); f = 1500 + 700*np.sin(np.pi*t/0.5) - 600*t; return bp(saw(phase(f)), 900, 3500) * env(len(t), 0.03, 0.15) * 0.25
def crickets(d):
    t = tt(d); car = np.sin(2*np.pi*4300*t); gate = (np.sin(2*np.pi*28*t) > 0.3) * (np.sin(2*np.pi*0.9*t) > -0.2); return car * gate * 0.06 * env(len(t), 0.3, 0.3)
def blip(up=True):
    t = tt(0.35); f = (500 + 900*t/0.35) if up else (1200 - 700*t/0.35); return np.sin(2*np.pi*phase(f)) * env(len(t), 0.01, 0.12) * 0.35
CUTS = [5, 11, 17, 23, 29, 35, 41, 48, 54, 56.5]
for c in CUTS: place(whoosh(0.5, 300, 5000), c - 0.32, 0.25, rng.uniform(-0.4, 0.4))
# 0–5: Earth gets its rings — shimmering swirl, chimes, a happy "wow"
place(pad([48, 55, 62, 64, 71], 5.4, 1400), 0.0, 0.55); place(whoosh(3.0, 1500, 9000), 0.1, 0.35)
for i in range(16): place(chime(rng.choice([79, 83, 86, 88, 91, 95]), 1.2, 0.8), 0.15 + i * 0.17, 0.35, rng.uniform(-0.7, 0.7))
place(blip(True), 2.55, 0.8, -0.1)
for i, m in enumerate([72, 76, 79, 83, 84, 83, 79, 76]): place(marimba(m, 0.7, 0.8), 2.7 + i * 0.28, 0.45, -0.2 + 0.05 * i)
# 5–11: Saturn — majestic low pad, harp arpeggios, a thin 'shing' when the rings go edge-on
place(pad([41, 48, 53, 57], 6.2, 900), 5.0, 0.6)
for i in range(22): place(pluck([53, 57, 60, 64, 65, 64, 60, 57][i % 8] + 12, 0.8, 0.8), 5.2 + i * 0.27, 0.4, -0.4 + 0.04 * i)
place(chime(96, 2.5, 1.0) + chime(91, 2.5, 0.6), 8.9, 0.6)
# 11–17: inside the rings — ice clinks, soft pad, a wave from the astronaut
place(pad([52, 59, 64, 68, 71], 6.2, 1600), 11.0, 0.5)
for k in range(46): place(clink(), 11.2 + rng.uniform(0, 5.6), rng.uniform(0.15, 0.4), rng.uniform(-0.8, 0.8))
place(blip(True), 12.0, 0.6, 0.2); place(blip(False), 12.4, 0.5, 0.2)
for i, m in enumerate([76, 79, 83, 81, 79, 76, 74, 76]): place(marimba(m, 0.7, 0.7), 11.4 + i * 0.68, 0.4)
# 17–23: Earth scaled — gentle arpeggio, sonar pings when labels appear
place(pad([45, 52, 57, 61, 64], 6.2, 1200), 17.0, 0.55)
for i in range(24): place(pluck([57, 61, 64, 69][i % 4] + 12, 0.6, 0.8), 17.1 + i * 0.25, 0.35, 0.3 * np.sin(i))
for tq in (17.6, 18.4, 19.0): place(chime(93, 1.2, 0.9), tq, 0.5)
# 23–29: equator beach — waves, gulls, ukulele-ish plucks
place(waves(6.3), 23.0, 0.5); place(gull(), 24.0, 1.0, 0.5); place(gull(), 26.3, 0.8, -0.4)
for i, m in enumerate([67, 71, 74, 71, 72, 76, 79, 76, 74, 71, 67, 71, 72, 74]): place(pluck(m, 0.45, 0.85), 23.2 + i * 0.4, 0.45, -0.2 + 0.03 * i)
place(pad([55, 59, 62, 67], 6.0, 1600), 23.0, 0.3)
# 29–35: the giant arch — birds, wind, a sweeping swell
place(wind(6.2), 29.0, 0.08); birds(29.2, 5.6, 10, 0.04)
place(pad([48, 55, 60, 64, 67, 71], 6.2, 2200) * np.linspace(0.4, 1.0, int(6.2 * SR)), 29.0, 0.7)
for i, m in enumerate([72, 79, 84, 83, 79, 76, 79, 72]): place(piano(m, 2.0, 0.8), 29.3 + i * 0.7, 0.45, -0.25 + 0.07 * i)
# 35–41: ring shadow / winter — colder minor pad, bells
place(pad([45, 48, 52, 55], 6.2, 900), 35.0, 0.6); place(wind(6.2) * 1.3, 35.0, 0.12)
for i, m in enumerate([81, 79, 76, 74]): place(chime(m, 2.2, 0.9), 35.6 + i * 1.3, 0.45, -0.3 + 0.2 * i)
# 41–48: bright night — crickets, campfire crackle, music box
place(crickets(7.2), 41.0, 0.8, 0.4); place(crickets(7.2), 41.0, 0.6, -0.5); place(crackle(7.0, 25), 41.0, 0.12, -0.2)
place(pad([53, 57, 60, 64], 7.2, 1000), 41.0, 0.45)
for i, m in enumerate([84, 79, 76, 79, 84, 86, 84, 79, 77, 79, 76, 72, 74, 76]): place(chime(m, 1.0, 0.8), 41.3 + i * 0.47, 0.35, 0.2 * np.sin(i))
# 48–54: Saturn's rings are raining away — gentle, a little sad, sparkling 'rain'
place(pad([50, 53, 57, 60], 6.2, 900), 48.0, 0.55)
for i, m in enumerate([74, 72, 69, 67, 65, 64, 62, 64]): place(piano(m, 2.2, 0.8), 48.3 + i * 0.7, 0.45)
for k in range(40): place(clink(rng.uniform(3500, 7000)) * 0.6, 48.3 + rng.uniform(0, 5.4), 0.25, rng.uniform(-0.8, 0.8))
place(blip(False), 49.2, 0.5)
# 54–61: Earth's ancient ring — ocean, trilobite skitters, uplifting finale
place(waves(7.0), 54.0, 0.35)
place(pad([48, 55, 60, 64, 67], 7.0, 1800), 54.0, 0.6)
for k in range(10): place(chatter(0.35) * 0.5, 56.7 + k * 0.42, 0.35, rng.uniform(-0.4, 0.4))
place(blip(True), 57.1, 0.6, 0.1)
for i, m in enumerate([72, 76, 79, 84, 83, 79, 81, 84, 88]): place(marimba(m, 0.8, 0.85), 54.3 + i * 0.5, 0.45, -0.2 + 0.05 * i)
place(chime(84, 3.0, 1.0) + chime(88, 3.0, 0.8) + chime(91, 3.0, 0.7), 59.0, 0.5)
place(piano(48, 3.5, 1.0) + piano(55, 3.5, 0.8) + piano(64, 3.5, 0.8) + piano(67, 3.5, 0.7), 59.2, 0.55)
# mix
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
