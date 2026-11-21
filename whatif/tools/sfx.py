"""Synthesised sound design (no samples), placed from the film's own timeline data so it is in sync by construction.
Output: render/sfx.wav (48 kHz stereo, 300 s)."""
import os, sys, numpy as np
from scipy import signal
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import cue as C, ROOT
import film

SR = 48000; N = int(300 * SR)
out = np.zeros((N, 2), np.float32)
rng = np.random.default_rng(11)


def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=4): return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def brown(n):
    b = np.cumsum(rng.standard_normal(n)); b -= lp(b, 8, 2); return b / (np.abs(b).max() + 1e-9)


def add(x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i + len(x) <= 0: return
    x = x[:N - i]
    out[i:i + len(x), 0] += x * gain * np.sqrt(0.5 * (1 - pan)) * 1.414
    out[i:i + len(x), 1] += x * gain * np.sqrt(0.5 * (1 + pan)) * 1.414


def impact(f0=60, f1=28, dur=2.6, body=1.0):
    t = tt(dur); f = f1 + (f0 - f1) * np.exp(-t * 5.5)
    sub = np.tanh(2.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.5)) / np.tanh(2.0)
    knock = lp(rng.standard_normal(len(t)), 300) * np.exp(-t * 28) * 2.0
    rum = lp(brown(len(t)), 140) * np.exp(-t * 2.4) * 0.7
    return (1 - np.exp(-t * 400)) * (0.9 * sub + 0.5 * body * knock + 0.4 * rum)


def whoosh(dur=1.6, f_lo=300, f_hi=2600, rise=0.6):
    t = tt(dur); n = rng.standard_normal(len(t)); y = np.zeros_like(n)
    for i, s in enumerate(range(0, len(t), 2400)):   # sweep a band-pass through the noise
        p = s / len(t); fc = f_lo + (f_hi - f_lo) * (np.sin(np.pi * min(p / rise, 1) / 2) if p < rise else 1 - (p - rise) / (1 - rise) * 0.7)
        seg_ = n[s:s + 2400]; y[s:s + 2400] = bp(seg_, max(60, fc * 0.6), min(SR / 2 - 100, fc * 1.4), 2)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    return lp(y, 7000) * env * 1.6


def rumble(dur=1.4):
    t = tt(dur); env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.2
    grain = np.clip(lp(rng.standard_normal(len(t)), 30), 0, None); grain /= grain.max() + 1e-9
    return lp(brown(len(t)), 220) * env * (0.5 + 0.5 * grain) * 1.4


def shimmer(dur=2.2, base=1568):
    t = tt(dur); y = np.zeros_like(t)
    for i, m in enumerate((1, 1.5, 2, 2.5, 3, 4)):
        y += np.sin(2 * np.pi * base * m * t + i) * np.exp(-t * (1.4 + i * 0.5)) * (0.6 ** i) * (1 - np.exp(-t * (30 + 8 * i)))
    return y * 0.5 * (0.7 + 0.3 * np.sin(2 * np.pi * 5 * t))


def tick():
    t = tt(0.09); return (bp(rng.standard_normal(len(t)), 1800, 6000, 2) * np.exp(-t * 90) + np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.4) * 0.8


def swish(dur=0.7):   # paper/air for plates appearing
    t = tt(dur); return bp(rng.standard_normal(len(t)), 900, 6000, 2) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2 * 0.7


def reverse_swell(dur=2.4):
    t = tt(dur); x = bp(rng.standard_normal(len(t)), 2000, 9000, 2) * (t / dur) ** 3
    return x * 1.2


# ---------------- events
add(impact(70, 30, 3.5, 1.2), 0.02, 0.55)
add(whoosh(2.9, 200, 1800, 0.5), 0.0, 0.32); add(whoosh(2.4, 300, 2600, 0.4), 0.6, 0.18, 0.3)
add(shimmer(2.6, 1175), 0.4, 0.10, -0.2)
# plates: rumble while lifting, impact on settle; fails = rumble + shimmer, no impact
seen = set()
for name, ks in film.KT.items():
    for a, b in zip(ks, ks[1:]):
        kind = b[2] if len(b) > 2 else None
        if kind in ('annex', 'rev', 'fail') and b[0] > a[0]:
            key = (round(a[0], 1), kind)
            gain = 0.5 if key not in seen else 0.22
            seen.add(key)
            d = b[0] - a[0]; pan = {'p': -0.5, 'r': 0.5, 'a': 0.0, 'c': 0.3}[name[-1]]
            add(rumble(d), a[0], 0.30 * gain / 0.5, pan)
            if kind == 'annex': add(impact(55, 26, 2.2, 0.8), b[0] - 0.08, 0.42 * gain / 0.5, pan)
            if kind == 'rev': add(reverse_swell(d), a[0], 0.10, pan)
            if kind == 'fail': add(shimmer(1.8, 1397), a[0] + d * 0.5, 0.10, pan)
# counter changes
for e in film._years():
    if e[1]: add(tick(), e[0], 0.20); add(tick(), e[0] + 0.07, 0.12)
# camera whooshes on big moves (zoom ratio or tilt change)
K = film.CAM_KEYS
for (t0, v0), (t1, v1) in zip(K, K[1:]):
    zr = abs(np.log(v1[2] / v0[2])); dt = abs(v1[4] - v0[4])
    if (zr > 0.28 or dt > 0.18) and t1 - t0 < 6 and t0 > 3:
        add(whoosh(min(2.2, (t1 - t0) * 0.8), 250, 2200, 0.55), t0 + 0.1, 0.14 + 0.08 * min(zr, 1))
# plates (paintings) appearing
for w0 in ('dangerously weak', 'russia increasingly', 'opportunities', '3rd', 'brief moment', 'napoleon'):
    add(swish(), C(w0) - 0.6, 0.12)
add(swish(), C('warsaw', 201) - 0.9, 0.12)
# gold moments
for w0, g in (('may constitution', 0.14), ('remains on the map', 0.14), ('still there', 0.12), ('a different world', 0.10)):
    add(shimmer(2.6, 1175), C(w0) - 0.2, g)
add(shimmer(3.0, 1175), C('what if poland', 290) - 0.1, 0.14)
# arrows: low drum roll / stop
add(rumble(2.0), C('intervened') - 0.1, 0.35, 0.5)
add(rumble(1.6), C('far more costly') - 0.6, 0.30, 0.5); add(impact(90, 50, 1.2, 0.5), C('far more costly') + 0.6, 0.25, 0.5)
# silence beat after 'disappeared': only a faint low wind
wind = lp(brown(int(3.2 * SR)), 300) * np.sin(np.pi * np.linspace(0, 1, int(3.2 * SR))) ** 2
add(wind, C('commonwealth disappeared') + 0.6, 0.12)
add(impact(46, 24, 3.6, 0.6), C('commonwealth disappeared') + 0.75, 0.5)
# closing
add(impact(60, 28, 3.0, 0.8), C('what if poland', 290) - 0.1, 0.4)
add(whoosh(3.0, 200, 1600, 0.6), C('a different world') + 0.4, 0.2)

peak = np.abs(out).max(); out *= (0.7 / peak) if peak > 0.7 else 1.0
os.makedirs(f'{ROOT}/render', exist_ok=True)
wavfile.write(f'{ROOT}/render/sfx.wav', SR, out.astype(np.float32))
print('sfx written, peak', round(float(peak), 3))
