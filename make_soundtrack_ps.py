# Score + sound design for "What if you flew to the nearest star?" (cinematic sci-fi)
import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'to_soundtrack.wav'
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100; DUR = 61.0; N = int(SR * DUR)
rng = np.random.default_rng(1999)
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

def breath(d, rate=0.35, g=1.0):
    t = tt(d); ph = (t * rate) % 1.0; e = np.where(ph < 0.4, np.sin(np.pi*ph/0.4), 0.0) * 1.0 + np.where(ph >= 0.5, np.sin(np.pi*(ph-0.5)/0.5)*0.7, 0.0)
    return bp(rng.standard_normal(len(t)), 400, 2500) * e * 0.45 * g * env(len(t), 0.2, 0.2)
def beep(f=1400, d=0.12): t = tt(d); return np.sin(2*np.pi*f*t) * env(len(t), 0.005, 0.03) * 0.35
def clunk(): t = tt(0.4); return (np.sin(2*np.pi*phase(140*np.exp(-t*8)+60)) * np.exp(-t*14) + hp(rng.standard_normal(len(t)), 1500)*np.exp(-t*40)*0.6) * 0.8
def hiss(d): t = tt(d); return hp(rng.standard_normal(len(t)), 3000) * np.exp(-t*2.5) * 0.5
def sonic():
    t = tt(2.5); return (lp(rng.standard_normal(len(t)), 300, 2) * 6 * np.exp(-t*3) + hp(rng.standard_normal(len(t)), 1200) * np.exp(-t*30) * 2) * env(len(t), 0.001, 0.5) + np.sin(2*np.pi*phase(40+60*np.exp(-t*6))) * np.exp(-t*2) * 1.2
def snap():
    t = tt(0.8); return (bp(rng.standard_normal(len(t)), 150, 2000) * np.exp(-t*9) * 2.5 + np.sin(2*np.pi*phase(90*np.exp(-t*5)+40)) * np.exp(-t*6)) * env(len(t), 0.002, 0.2)
def cheer(d):
    t = tt(d); x = bp(rng.standard_normal(len(t)), 500, 3500) * (0.7 + 0.3*np.sin(2*np.pi*1.3*t)); return x * env(len(t), 0.4, 1.0) * 0.6
def rising_roar(d, f0, f1, a0, a1):
    t = tt(d); x = rng.standard_normal(len(t)); n = len(t); out = np.zeros(n); seg = int(0.25*SR)
    for i in range(0, n, seg):
        u = i / n; f = f0 * (f1/f0) ** u; y = bp(x[i:i+seg], f*0.5, min(f*3.0, 18000)); out[i:i+len(y)] = y * (a0 + (a1-a0)*u)
    return lp(out, 9000) * env(n, 0.3, 0.3)

def drone(d, f=55, bright=400):
    t = tt(d); s = sum(np.sin(2*np.pi*f*k*t + np.sin(2*np.pi*0.07*k*t)*2) / k for k in (1, 2, 3, 5)); return lp(s, bright) * 0.4 * env(len(t), d*0.3, d*0.3)
def icecrack(v=1.0):
    t = tt(0.6); x = hp(rng.standard_normal(len(t)), 1800) * np.exp(-t*25) * (rng.random(len(t)) > 0.6); ping = np.sin(2*np.pi*phase(2400*np.exp(-t*3)+600)) * np.exp(-t*9) * 0.4
    return (x + ping) * v
def bubbles(d, rate):
    s = np.zeros(int(d*SR)); tc = 0.0
    while tc < d - 0.3:
        b = bubble(rng.uniform(300, 900), 0.12); i = int(tc*SR); s[i:i+len(b)] += b[:len(s)-i] * rng.uniform(0.3, 1.0); tc += rng.exponential(1/rate)
    return s
def click(): t = tt(0.05); return hp(rng.standard_normal(len(t)), 2000) * np.exp(-t*200) * 0.8

def boom(d=3.0, v=1.0):
    t = tt(d); return (np.sin(2*np.pi*phase(30+70*np.exp(-t*5))) * np.exp(-t*1.6) * 1.4 + lp(rng.standard_normal(len(t)), 250, 3) * 6 * np.exp(-t*2.2) + hp(rng.standard_normal(len(t)), 2000) * np.exp(-t*20) * 1.2) * env(len(t), 0.002, 0.6) * v
def hissjet(d): t = tt(d); return bp(rng.standard_normal(len(t)), 800, 6000) * (0.6 + 0.4*np.sin(2*np.pi*0.7*t)) * env(len(t), 0.2, 0.4) * 0.6
def boil(d, rate=30): return bubbles(d, rate) * 1.2 + lp(rng.standard_normal(int(d*SR)), 300, 2) * 0.8 * env(int(d*SR), 0.5, 0.5)
def sea_swell(d, period=8.0, g=1.0):
    t = tt(d); ph = (t / period) % 1.0; sh = 0.35 + 0.65*np.sin(np.pi*ph)**2
    return (lp(rng.standard_normal(len(t)), 600, 2) * 1.6 * sh + bp(rng.standard_normal(len(t)), 1200, 5000) * 0.25 * sh**3) * env(len(t), 0.5, 0.5) * g
def creak(d=1.2):
    t = tt(d); f = 95 + 25*np.sin(2*np.pi*0.8*t); s = saw(phase(f)) * (0.5 + 0.5*np.sin(2*np.pi*13*t)); return bp(s, 200, 1600) * env(len(t), 0.2, 0.4) * 0.3
def horn(d=2.4, f=110):
    t = tt(d); s = sum(saw(phase(np.full(len(t), f*k*(1+0.002*j)))) / k for k in (1, 2) for j in (0, 1)); return lp(s, 900, 2) * env(len(t), 0.15, 0.5) * 0.3
def crash(d=3.0, v=1.0):
    t = tt(d); return (lp(rng.standard_normal(len(t)), 700, 2) * 5 * np.exp(-t*1.3) + bp(rng.standard_normal(len(t)), 1500, 7000) * 1.5 * np.exp(-t*2.5) + np.sin(2*np.pi*phase(45+40*np.exp(-t*6))) * np.exp(-t*2) * 1.2) * env(len(t), 0.005, 0.8) * v
def sat_ping(f=1800): t = tt(0.6); return np.sin(2*np.pi*f*t) * np.exp(-t*7) * 0.3
def arp(notes, t0, d, step, v=0.3, fn=None):
    fn = fn or pluck; k = 0; tc = t0
    while tc < t0 + d: place(fn(notes[k % len(notes)], 0.5, 0.8), tc, v, 0.3 * np.sin(k)); k += 1; tc += step
def thin_wind(d): t = tt(d); return bp(rng.standard_normal(len(t)), 600, 3000) * (0.5 + 0.5*np.sin(2*np.pi*0.17*t)**2) * env(len(t), 0.6, 0.6) * 0.5
def siren(d):
    t = tt(d); f = 520 + 380*np.sin(2*np.pi*t/4.0 - np.pi/2)*0.5 + 190; s = saw(phase(f)); g = 0.55 + 0.45*np.sin(2*np.pi*0.45*t)**2
    return lp(bp(s, 300, 2500), 2200) * g * env(len(t), 0.4, 0.5) * 0.35
def hail_hits(d, rate, f0=1800):
    s = np.zeros(int(d*SR)); tc = 0.0
    while tc < d:
        i = int(tc*SR); c = clink(rng.uniform(f0*0.6, f0*1.8)) * rng.uniform(0.2, 1.0); thud = plop(rng.uniform(90, 160), 0.15) * rng.uniform(0.2, 0.6)
        s[i:i+len(c)] += c[:len(s)-i]; s[i:i+len(thud)] += thud[:len(s)-i]; tc += rng.exponential(1/rate)
    return s
def freight(d, amt=1.0):
    t = tt(d); x = lp(rng.standard_normal(len(t)), 260, 3) * 6 + bp(rng.standard_normal(len(t)), 300, 1500) * 1.2
    return x * (0.75 + 0.25*np.sin(2*np.pi*0.6*t)) * env(len(t), 0.6, 0.6) * amt
def alarm(d):
    t = tt(d); return np.sin(2*np.pi*phase(900 + 500*(np.sin(2*np.pi*3*t) > 0))) * env(len(t), 0.01, 0.1) * 0.25
def notif():
    return np.concatenate([beep(1320, 0.1), np.zeros(int(0.05*SR)), beep(1760, 0.14)]) * 1.4

def braam(notes, d=1.8, v=1.0):
    t = tt(d); s = np.zeros(len(t))
    for m in notes:
        for det in (-0.1, 0.0, 0.1): s += saw(phase(np.full(len(t), mtof(m + det)))) * 0.2
    s = np.tanh(lp(s, 900, 2) * 2.0)
    return s * env(len(t), 0.02, d*0.6) * v
def bass(m, d=0.22, v=1.0):
    t = tt(d); s = saw(phase(np.full(len(t), mtof(m)))) + 0.5*np.sin(2*np.pi*mtof(m-12)*t)
    e = np.exp(-t*25); return (lp(s, 1800, 2)*e + lp(s, 320, 2)*(1-e)) * env(len(t), 0.003, 0.06) * v * 0.6
def zap(f0=2400, f1=300, d=0.35):
    t = tt(d); f = f0 * (f1/f0) ** (t/d); return (np.sin(2*np.pi*phase(f)) + 0.3*saw(phase(f*1.5))) * env(len(t), 0.003, 0.1) * 0.4
def laserhum(d, f=110):
    t = tt(d); s = sum(saw(phase(np.full(len(t), f*k*(1+0.004*j)))) / k for k in (1, 2, 3) for j in (0, 1))
    return bp(s, 200, 2500) * (0.7 + 0.3*np.sin(2*np.pi*7*t)) * env(len(t), 0.05, 0.3) * 0.2
def sparkle(d=1.5, n=14):
    s = np.zeros(int(d*SR))
    for k in range(n):
        c = chime(rng.choice([81, 84, 86, 88, 93]), 0.8, rng.uniform(0.3, 0.8)); i = int(rng.uniform(0, d-0.8)*SR); s[i:i+len(c)] += c
    return s
CHORDS = [[38, 45, 50, 53], [34, 41, 46, 50], [36, 43, 48, 52], [33, 40, 45, 49]]  # Dm Bb C A
BEATS = [1.2,2.5,3.8, 6.2,7.9,9.6, 12.0,13.6,15.4, 18.0,20.0,21.8, 24.4,26.5,28.0, 30.2,31.6,33.0, 36.4,38.2,39.8, 42.4,44.0,45.6, 48.6,50.0,51.6, 54.0,56.2]
CUTS = [5, 11, 17, 23, 29, 35, 41, 47, 53]
for c in CUTS: place(whoosh(0.5, 300, 8000), c - 0.35, 0.3, rng.uniform(-0.4, 0.4))
for b in BEATS: place(whoosh(0.3, 600, 9000), b - 0.1, 0.18, rng.uniform(-0.6, 0.6)); place(taiko(0.7, 48), b, 0.4)
# driving synth bass (16ths feel at 120 bpm) through the journey
for k in range(int(52.8 / 0.25)):
    tb = 0.25 * k; bar = int(tb // 2.0) % 4; root = CHORDS[bar][0] + 12
    if 29.0 <= tb < 35.0 and k % 2: continue
    place(bass(root + (12 if k % 4 == 2 else 0), 0.22, 1.0), tb, 0.22 + 0.08*min(1, tb/20))
    if k % 2 == 0: place(click(), tb + 0.125, 0.05)
for i in range(26):
    tb = i * 2.0
    if tb >= 53: break
    place(pad(CHORDS[i % 4][1:], 2.1, 1100), tb, 0.28)
place(drone(53.0, 36.7, 260), 0.0, 0.35)
# 0–5 launch site at dusk
place(crickets(4.0), 0.0, 0.2); place(wind(5.2), 0.0, 0.2)
place(clunk(), 1.2, 0.6); place(hp(rng.standard_normal(int(0.4*SR)), 3000) * np.exp(-tt(0.4)*10), 1.2, 0.2)
place(hiss(2.0), 2.5, 0.6, -0.3); place(hiss(1.6), 2.7, 0.4, 0.3)
place(rumble(1.6, 90, 3.0), 3.8, 0.35); place(beep(1200, 0.1), 0.5, 0.25); place(beep(1200, 0.1), 1.0, 0.25)
# 5–11 lift-off
for k in range(5): place(beep(1500 if k < 4 else 2000, 0.12 if k < 4 else 0.3), 5.1 + k*0.27, 0.35)
place(boom(4.0, 1.4), 6.2, 0.8); place(rumble(5.0, 140, 3.5), 6.2, 0.6); place(rising_roar(4.8, 80, 2400, 0.6, 2.0), 6.2, 0.5)
place(sonic(), 7.9, 0.6); place(whoosh(1.4, 200, 6000), 9.2, 0.7, 0.5); place(braam([38, 45, 50], 2.0, 1.0), 6.2, 0.4)
# 11–17 light sail and lasers
place(laserhum(5.0, 110), 12.0, 0.5); place(zap(3000, 400, 0.5), 12.0, 0.5); place(zap(2600, 200, 0.6), 13.6, 0.55); place(whoosh(0.9, 400, 9000), 13.55, 0.5)
place(sparkle(1.6, 16), 15.4, 0.5); arp([62, 69, 74, 77], 11.2, 5.6, 0.125, 0.12, pluck)
# 17–23 near light speed
place(rising_roar(1.1, 60, 4000, 0.2, 2.4), 16.95, 0.55); place(boom(3.0, 1.2), 18.0, 0.7); place(braam([38, 45, 50, 53], 2.4, 1.0), 18.0, 0.45)
place(laserhum(5.0, 55), 18.0, 0.35); place(whoosh(1.0, 300, 9000), 19.6, 0.45); place(sonic(), 21.8, 0.4)
# 23–29 dust impacts on the shield
place(roar(6.0, 1000, 6000, 0.5), 23.0, 0.15)
for b in (24.4, 26.5, 28.0): place(boom(2.0, 1.0), b, 0.6, rng.uniform(-0.3, 0.3)); place(zap(4000, 600, 0.4), b, 0.4); place(shatter(1.0), b + 0.02, 0.35); place(alarm(0.5), b + 0.3, 0.15)
# 29–35 looking back at the Sun: helmet breathing, radio pulses
place(breath(6.0, 0.35, 1.0), 29.0, 0.35); place(pad([50, 57, 62, 65], 6.0, 900), 29.0, 0.3)
for i, m in enumerate([62, 65, 69, 74]): place(piano(m, 2.4, 0.8), 29.4 + i*0.8, 0.3)
for b in (31.6, 32.1, 33.0, 33.5): place(sat_ping(1760), b, 0.5); place(blip(True), b, 0.2)
place(chime(81, 1.4), 30.4, 0.3)
# 35–41 arrival: three suns, big brass
for i, ch in enumerate(([50, 57, 62, 65], [46, 53, 58, 62], [48, 55, 60, 64], [45, 52, 57, 61])): place(brass(ch, 1.6, 1900), 35.2 + i*1.45, 0.42)
place(whoosh(1.6, 150, 7000), 35.7, 0.75, -0.5); place(rumble(1.4, 120, 2.0), 36.2, 0.4)
for b in (36.8, 37.5, 38.2): place(chime(86, 1.2), b, 0.3)
place(braam([38, 45, 50], 2.0, 0.9), 39.8, 0.35)
# 41–47 Proxima b's racing year
arp([74, 77, 81, 86, 81, 77], 41.2, 5.6, 0.125, 0.12, marimba)
for b in (42.4, 44.0, 45.6): place(chime(93, 1.2), b, 0.4); place(blip(True), b, 0.25)
for k in range(24): place(tick(), 41.2 + k*0.25, 0.1)
# 47–53 the flare
place(rising_roar(1.6, 60, 3000, 0.2, 2.6), 47.0, 0.5); place(boom(4.0, 1.5), 48.6, 0.85); place(braam([37, 44, 49], 2.5, 1.0), 48.6, 0.45)
place(roar(4.0, 200, 3000, 0.6), 48.8, 0.45); place(crash(2.5, 1.0), 50.0, 0.7); place(zap(3500, 300, 0.5), 50.0, 0.4)
place(alarm(2.4), 50.5, 0.3); place(boom(2.0, 0.9), 51.6, 0.55)
# 53–61 standing on Proxima b
place(pad([50, 57, 62, 66, 69], 8.0, 2000), 53.0, 0.45); place(clunk(), 54.0, 0.5); place(chime(86, 1.8), 54.0, 0.35); place(chime(90, 1.8), 56.2, 0.3)
for tb, ch in ((53.3, [50, 57, 62, 66]), (55.3, [46, 53, 58, 62]), (57.3, [48, 55, 60, 64]), (59.0, [50, 57, 62, 66, 69])): place(brass(ch, 2.2 if tb < 59 else 2.0, 2000), tb, 0.4)
for k in range(14): place(taiko(0.9, 50), 54.2 + k*0.5, 0.18)
arp([74, 78, 81, 86], 53.4, 5.4, 0.25, 0.1, chime)
place(piano(50, 3.0, 1.0) + piano(57, 3.0, 0.8) + piano(62, 3.0, 0.8) + piano(66, 3.0, 0.7), 59.2, 0.55); place(bell(587.3, 2.5), 59.2, 0.35)
fi = int(0.4 * SR); fo = int(0.8 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.98), np.percentile(np.abs(Rr), 99.98))
L = np.tanh(L / peak * 1.1) * 0.92; Rr = np.tanh(Rr / peak * 1.1) * 0.92
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
