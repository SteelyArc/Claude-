# Playful score + sound design for "What if you shrank to the size of an ant?"
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'sh_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(170)
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
CUTS = [5, 11, 17, 23, 29, 35, 41, 48, 54]
for c in CUTS: place(whoosh(0.4, 400, 6000), c - 0.28, 0.25, rng.uniform(-0.4, 0.4))
# playful bass + pizzicato groove (F major) through most of the video
bass = [41, 41, 48, 48, 46, 46, 43, 48]
for i in range(int(47 / 0.5)):
    tb = 0.3 + i * 0.5
    if 11 <= tb < 17 or 41 <= tb < 48: continue
    place(pluck(bass[i % 8] - 12 + 12, 0.45, 0.9), tb, 0.35)
mel = [72, 77, 81, 79, 77, 74, 72, 74, 77, 76, 74, 72]
for blk in [0.3, 5.3, 23.3, 29.3, 35.3]:
    for i, m in enumerate(mel): place(marimba(m, 0.5, 0.75), blk + i * 0.45, 0.32, -0.3 + 0.05 * i)
# 0–5: shrink — descending "whoop" + sparkles
place(slide(1400, 180, 2.6, 0.45), 0.6, 0.7); for_ = [place(chime(rng.choice([84, 88, 91, 96]), 0.8, 0.7), 0.7 + k * 0.14, 0.3, rng.uniform(-0.6, 0.6)) for k in range(16)]
place(blip(True), 3.6, 0.5)
# 5–11: the dewdrop — glassy chimes, birds far away
for k in range(6): place(chime(rng.choice([86, 91, 93, 98]), 1.6, 0.8), 5.4 + k * 0.9, 0.35, rng.uniform(-0.5, 0.5))
birds(5.2, 5.5, 6, 0.03)
# 11–17: rain — slow, heavy drops (deep plops) and splashes, darker music
place(pad([41, 48, 53, 56], 6.2, 700), 11.0, 0.55)
for k in range(26):
    tq = 11.3 + k * 0.22 + rng.uniform(-0.05, 0.05); place(plop(rng.uniform(70, 140), 0.4) * 1.3, tq, 0.55, rng.uniform(-0.6, 0.6))
    place(hp(rng.standard_normal(int(0.25*SR)), 2500) * np.exp(-tt(0.25)*14) * 0.2, tq + 0.02, 0.5, rng.uniform(-0.6, 0.6))
# 17–23: the fall — whistle down, soft boing landing, happy thumbs-up
place(slide(1600, 400, 3.6, 0.3), 18.0, 0.6); place(boing(), 21.6, 0.9); place(blip(True), 22.0, 0.5)
# 23–29: ants — tiny clicky footsteps
place(steps(5.8, 22, 2600), 23.2, 0.35, 0.3); place(steps(5.0, 18, 2200), 24.0, 0.25, 0.5)
# 29–35: the honeybee — a real 230 Hz buzz, getting closer
place(buzz(5.8, 230) * np.linspace(0.3, 1.0, int(5.8*SR)), 29.1, 0.75, 0.2)
# 35–41: the long walk — tiny steps, clock ticks speeding up
place(steps(5.8, 7, 1400), 35.2, 0.4)
for k in range(40): place(tick(), 35.4 + 5.6 * (k / 40) ** 0.8, 0.22, 0.3)
# 41–48: 20 quadrillion ants — swelling crawl noise + rising strings
place(hp(rng.standard_normal(int(7*SR)), 3000) * np.linspace(0.05, 0.5, int(7*SR)) * (0.6 + 0.4*np.sin(2*np.pi*13*tt(7))), 41.0, 0.35)
place(pad([53, 57, 60, 65, 69], 7.0, 1800) * np.linspace(0.3, 1.0, int(7*SR)), 41.0, 0.6)
for i, m in enumerate([65, 69, 72, 77, 76, 72, 74, 77]): place(marimba(m, 0.6, 0.8), 41.4 + i * 0.8, 0.4)
# 48–54: the spider — sneaky pizzicato, glitter of dew
for i, m in enumerate([53, 56, 53, 56, 55, 52, 53, 49, 53, 56, 58, 60]): place(pluck(m, 0.4, 0.9), 48.2 + i * 0.45, 0.45, 0.2 * np.sin(i))
for k in range(8): place(chime(rng.choice([91, 96, 98]), 1.0, 0.6), 48.4 + k * 0.7, 0.25, rng.uniform(-0.6, 0.6))
place(blip(False), 50.6, 0.5)
# 54–61: grow back — rising "whoop", big happy finale
place(slide(160, 1500, 3.0, 0.45), 54.4, 0.7)
place(pad([53, 57, 60, 65, 69], 7.0, 2000), 54.0, 0.55)
for i, m in enumerate([77, 81, 84, 89, 88, 84, 86, 89, 93]): place(marimba(m, 0.7, 0.85), 55.0 + i * 0.45, 0.45, -0.2 + 0.05 * i)
place(piano(53, 3.5, 1.0) + piano(60, 3.5, 0.8) + piano(65, 3.5, 0.8) + piano(69, 3.5, 0.7), 59.0, 0.55)
place(blip(True), 58.0, 0.5)
# mix
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
