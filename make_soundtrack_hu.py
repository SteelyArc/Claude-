# Cinematic score + storm sound design for "What if you flew into a hurricane?"
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'hu_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(345)
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

def slide(f0, f1, d, v=0.4):
    t = tt(d); f = f0 * (f1 / f0) ** (t / d); s = np.sin(2*np.pi*phase(f)) + 0.3*np.sin(4*np.pi*phase(f)); return s * env(len(t), 0.02, 0.1) * v
def plop(f0=180, d=0.25):
    t = tt(d); f = f0 * (1 + 2.5*np.exp(-t*30)); return np.sin(2*np.pi*phase(f)) * np.exp(-t*14) * env(len(t), 0.002, 0.05)
def boing(d=0.6):
    t = tt(d); f = 220 + 90*np.sin(2*np.pi*11*t)*np.exp(-t*5); return np.sin(2*np.pi*phase(f)) * np.exp(-t*4) * 0.5
def buzz(d, f0=230):
    t = tt(d); f = f0 * (1 + 0.03*np.sin(2*np.pi*5*t)); s = saw(phase(f)); return bp(s, 300, 3000) * 0.3 * env(len(t), 0.2, 0.3)
def steps(d, rate, f=1800):
    s = np.zeros(int(d*SR)); tc = 0.0
    while tc < d:
        i = int(tc*SR); n = int(0.02*SR); c = bp(rng.standard_normal(n), f*0.6, f*1.6) * np.exp(-np.arange(n)/(SR*0.004)); s[i:i+n] += c[:len(s)-i]; tc += 1/rate * rng.uniform(0.8, 1.2)
    return s * 0.5

# ---- storm sounds ----
def roar(d, lo=150, hi=1400, gust=0.18):
    t = tt(d); x = bp(rng.standard_normal(len(t)), lo, hi); ph = rng.uniform(0, 6)
    g = 0.6 + 0.4 * np.sin(2*np.pi*gust*t + ph) * np.sin(2*np.pi*gust*0.37*t + 1)
    return x * g * env(len(t), 0.3, 0.3)
def howl(d, f0=420):
    t = tt(d); f = f0 * (1 + 0.25*np.sin(2*np.pi*0.21*t) + 0.1*np.sin(2*np.pi*0.53*t))
    n = bp(rng.standard_normal(len(t)), f0*0.8, f0*1.6); s = np.sin(2*np.pi*phase(f))
    return bp(s + n*3, f0*0.7, f0*2.0) * 0.25 * env(len(t), 0.5, 0.5)
def props(d, f=68):
    t = tt(d); s = np.zeros(len(t))
    for j in range(4):
        for k in (1, 2, 3): s += saw(phase(np.full(len(t), f*k*(1 + 0.003*j)))) * 0.3 / k
    return lp(s, 700, 2) * 0.22 * env(len(t), 0.3, 0.3)
def rainhiss(d): t = tt(d); return hp(rng.standard_normal(len(t)), 2500) * 0.35 * env(len(t), 0.3, 0.3)
def breakers(d, period=4.0):
    t = tt(d); ph = (t / period) % 1.0; sh = np.where(ph < 0.25, ph/0.25, np.exp(-(ph-0.25)*5))
    return (lp(rng.standard_normal(len(t)), 500, 2) * 2.2 * sh + bp(rng.standard_normal(len(t)), 800, 4000) * 0.6 * sh**2) * env(len(t), 0.5, 0.5)
def radio():
    t = tt(0.5); s = np.sin(2*np.pi*1200*t) * (t < 0.08) + np.sin(2*np.pi*1600*t) * ((t > 0.12) & (t < 0.2))
    return (s + bp(rng.standard_normal(len(t)), 900, 3000) * 0.4 * (t < 0.45)) * 0.3
CUTS = [5, 11, 17, 23, 29, 35, 41, 47, 53]
for c in CUTS: place(whoosh(0.45, 300, 6000), c - 0.3, 0.3, rng.uniform(-0.4, 0.4))
# 0–5: high above the storm — airy D-minor pad, deep swell, soft high wind
place(sub_boom(5.0), 0.2, 0.5)
place(pad([50, 57, 62, 65, 69], 5.4, 1400), 0.0, 0.6)
place(roar(5.2, 500, 3000, 0.1), 0.0, 0.12)
for k in range(6): place(chime(rng.choice([74, 77, 81, 86]), 1.4, 0.7), 0.6 + k*0.7, 0.22, rng.uniform(-0.6, 0.6))
place(slide(900, 300, 3.5, 0.18), 1.4, 0.4)
# 5–11: approach under the clouds — turboprops, rain, building drums
place(props(6.2), 4.9, 0.55); place(roar(6.2, 150, 1500, 0.2), 4.9, 0.55); place(rainhiss(6.2), 5.0, 0.35)
for k in range(12): place(taiko(0.9, 62), 5.3 + k*0.5, 0.25 + 0.25*k/12)
place(pad([50, 53, 57, 62], 6.2, 900), 5.0, 0.45)
place(thunder(3.0, 0.8), 7.4, 0.55, -0.5); place(thunder(3.0, 0.9), 9.6, 0.6, 0.5)
# 11–17: in the eyewall (cockpit) — muffled roar, rain on glass, rattles, big thunder
place(lp(roar(6.2, 80, 900, 0.35), 700), 11.0, 1.1); place(crackle(6.0, 160) * 0.5, 11.0, 0.55, -0.2); place(crackle(6.0, 25) * 0.6, 11.0, 0.3, 0.3)
place(lp(props(6.2), 400), 11.0, 0.5)
place(thunder(3.2, 1.2), 13.4, 0.95, 0.3); place(thunder(3.0, 0.9), 15.6, 0.75, -0.3)
place(radio(), 12.1, 0.6, -0.4); place(radio(), 16.0, 0.5, 0.4)
place(pad([50, 51, 57, 62], 6.0, 600), 11.0, 0.5)
for k in range(12): place(heartbeat(), 11.2 + k*0.5, 0.35)
# 17–23: outside in the cloud — lightning, war drums, brass hits
place(roar(6.2, 150, 1800, 0.3), 17.0, 0.7); place(rainhiss(6.0), 17.0, 0.45); place(howl(6.0, 480), 17.0, 0.35, 0.3)
for c, p in ((18.3, -0.4), (20.4, 0.4), (22.0, 0.0)): place(thunder(3.0, 1.1), c, 0.8, p)
for k in range(24): place(taiko(0.8, 58 if k % 4 else 50), 17.1 + k*0.25, 0.35 if k % 2 else 0.5)
for tb, ch in ((17.2, [50, 57, 62]), (19.2, [48, 55, 60]), (21.2, [46, 53, 58])): place(brass(ch, 1.8, 1800), tb, 0.45)
# 23–29: breaking into the eye — roar swells, then sudden calm and a warm D-major
place(roar(1.8, 150, 2500, 0.5) * np.linspace(0.6, 1.4, int(1.8*SR)), 23.0, 0.8); place(whoosh(1.2, 200, 5000), 23.9, 0.6)
place(lp(roar(4.4, 60, 300, 0.1), 250), 24.8, 0.25)
place(pad([50, 57, 62, 66, 69], 4.6, 1600), 24.6, 0.6)
for k in range(10): place(chime(rng.choice([86, 90, 93, 98]), 1.6, 0.7), 24.7 + k*0.18, 0.22, rng.uniform(-0.6, 0.6))
for i, m in enumerate([74, 78, 81, 86, 85, 81, 83]): place(piano(m, 2.2, 0.9), 25.4 + i*0.5, 0.45)
place(gull(), 26.6, 0.6, -0.5); place(gull(), 27.8, 0.5, 0.6)
# 29–35: the eye — calm pad, piano, gulls, pressure dropping (low falling tone)
place(pad([50, 57, 62, 66, 69], 6.2, 1300), 28.9, 0.55)
for i, m in enumerate([69, 74, 78, 76, 74, 73, 71, 69]): place(piano(m, 2.4, 0.85), 29.3 + i*0.7, 0.42, -0.2 + 0.05*i)
place(slide(220, 110, 4.5, 0.25), 29.6, 0.5); place(lp(props(6.0), 500), 29.0, 0.3)
for k in range(4): place(gull(), 29.5 + k*1.4 + rng.uniform(0, 0.4), 0.45, rng.uniform(-0.7, 0.7))
place(lp(roar(6.0, 60, 300, 0.1), 250), 29.0, 0.22)
# 35–41: giant waves — breakers, howling wind, dark drums
place(breakers(6.2, 3.1), 35.0, 0.9); place(howl(6.2, 380), 35.0, 0.45, -0.3); place(roar(6.2, 200, 2500, 0.3), 35.0, 0.55)
place(pad([50, 53, 57, 60], 6.2, 800), 35.0, 0.5)
for k in range(12): place(taiko(1.0, 48), 35.3 + k*0.5, 0.45 if k % 2 == 0 else 0.3)
# 41–47: storm surge — rushing water rising, thunder, drums
place(lp(rng.standard_normal(int(6.2*SR)), 1200, 2) * np.linspace(0.3, 1.3, int(6.2*SR)) * env(int(6.2*SR), 0.3, 0.3), 41.0, 0.55)
place(breakers(6.2, 2.4), 41.0, 0.55); place(rainhiss(6.2), 41.0, 0.35)
place(thunder(3.0, 1.0), 42.2, 0.6, 0.4)
for k in range(24): place(taiko(0.8, 55), 41.2 + k*0.25, 0.25 + 0.3*k/24)
for tb, ch in ((41.3, [50, 57, 62]), (43.3, [46, 53, 58]), (45.3, [48, 55, 60, 64])): place(brass(ch, 1.9, 2000), tb, 0.45)
# 47–53: above the cloud tops at sunset — warm strings, soft high wind
place(pad([50, 57, 62, 66, 69], 3.2, 1800), 47.0, 0.6); place(pad([55, 62, 67, 71, 74], 3.4, 1900), 50.0, 0.6)
place(roar(6.2, 600, 3500, 0.08), 47.0, 0.12); place(props(6.0), 47.0, 0.3)
for i, m in enumerate([78, 81, 86, 85, 83, 81, 79, 81]): place(chime(m, 1.6, 0.8), 47.4 + i*0.7, 0.3, -0.3 + 0.08*i)
# 53–61: up to space — heroic finale
place(whoosh(2.5, 200, 4000), 53.0, 0.5)
for tb, ch in ((53.2, [50, 57, 62, 66]), (55.2, [55, 62, 67, 71]), (57.2, [57, 64, 69, 73]), (59.0, [50, 57, 62, 66, 69])): place(brass(ch, 2.2 if tb < 59 else 2.0, 2200), tb, 0.5)
for k in range(16): place(taiko(0.9, 52), 53.2 + k*0.5, 0.35)
place(pad([50, 57, 62, 66, 69, 74], 8.0, 2200), 53.0, 0.5)
for i, m in enumerate([74, 78, 81, 86, 85, 81, 83, 86, 90]): place(chime(m, 1.6, 0.85), 54.0 + i*0.5, 0.3, -0.2 + 0.05*i)
place(piano(50, 3.0, 1.0) + piano(57, 3.0, 0.8) + piano(62, 3.0, 0.8) + piano(66, 3.0, 0.7), 59.2, 0.55); place(bell(587.3, 2.5), 59.2, 0.4)
# mix
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
