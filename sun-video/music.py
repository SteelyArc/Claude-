#!/usr/bin/env python3
"""Original cinematic ambient score for the SUN video (synthesised, no samples).

86 BPM (one beat = one cut in the title section), D minor, 89 beats = 62.09 s.
Impacts land on the eruption beats used by the edit: 40, 48, 54, 72 (+ a soft one at 77).
Usage: python3 music.py out.wav
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 86
B = 60 / BPM
BEATS = 89
DUR = BEATS * B + 2.5          # tail for reverb, trimmed when muxing
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)


def hz(note):  # MIDI -> Hz
    return 440.0 * 2 ** ((note - 69) / 12)


def at(beat):
    return int(beat * B * SR)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def env_ar(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na) ** 2
    if nr: e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def saw(f, n, harmonics=10, phase=0.0):
    tt = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(1, harmonics + 1):
        if f * k > 9000: break
        y += np.sin(2 * np.pi * f * k * tt + phase * k) / k
    return y


def add(buf, start, sig, gain=1.0):
    s = max(start, 0)
    e = min(start + len(sig), len(buf))
    if e > s: buf[s:e] += sig[s - start:e - start] * gain


L = np.zeros(N); R = np.zeros(N)
send_L = np.zeros(N); send_R = np.zeros(N)   # reverb send


def put(sig, start, g=1.0, pan=0.0, wet=0.3):
    gl, gr = g * np.sqrt(0.5 * (1 - pan)), g * np.sqrt(0.5 * (1 + pan))
    add(L, start, sig, gl * (1 - wet * 0.5)); add(R, start, sig, gr * (1 - wet * 0.5))
    add(send_L, start, sig, gl * wet); add(send_R, start, sig, gr * wet)


# section intensity curve (0..1) by beat
def intensity(beat):
    pts = [(0, .35), (6, .5), (12, .3), (30, .45), (40, .85), (48, .95), (56, .8), (64, .9), (72, 1.0), (74, .45), (89, .25)]
    xs, ys = zip(*pts)
    return float(np.interp(beat, xs, ys))


# ---------------------------------------------------------------- drone (D1 + D2 + A2), slow swell
drone = (np.sin(2 * np.pi * hz(26) * t) * .55 + np.sin(2 * np.pi * hz(38) * t + .3) * .35 + np.sin(2 * np.pi * hz(45) * t + 1.1) * .18)
drone *= .75 + .25 * np.sin(2 * np.pi * t / 9.3)
dr_env = np.interp(t / B, [0, 2, 12, 40, 72, 80, 89, 92], [.5, .8, .7, .85, 1., .8, .5, 0])
drone = np.tanh(drone * 1.4) * dr_env
put(drone, 0, .32, 0, wet=.2)

# ---------------------------------------------------------------- pad chords (Dm  Bb  F  C), 4 beats each
CHORDS = [[50, 53, 57, 62], [46, 50, 53, 58], [41, 45, 48, 53], [48, 52, 55, 60]]
for bar in range(0, 23):
    b0 = bar * 4
    if b0 >= 89: break
    ch = CHORDS[bar % 4]
    if b0 >= 74: ch = [50, 53, 57, 62, 69] if bar % 2 == 0 else [46, 50, 53, 58, 65]
    n = int((4 * B + 1.6) * SR)
    seg = np.zeros(n)
    for i, note in enumerate(ch):
        for det in (-0.07, 0.0, 0.07):
            seg += saw(hz(note + det), n, 9, phase=rng.uniform(0, 6))
    inten = intensity(b0 + 2)
    cutoff = 500 + 2600 * inten ** 1.6
    seg = lp(seg, cutoff, 2) * env_ar(n, 1.0, 1.5) / len(ch)
    put(seg, at(b0) - int(.3 * SR), .16 + .1 * inten, pan=(-.25 if bar % 2 else .25), wet=.55)

# high string layer in the big sections
for bar in range(10, 18):
    ch = CHORDS[bar % 4]
    n = int((4 * B + 1.2) * SR)
    seg = sum(saw(hz(nn + 12 + d), n, 6, rng.uniform(0, 6)) for nn in ch[1:] for d in (-.05, .05))
    seg = bp(seg, 700, 5000) * env_ar(n, .6, 1.2) * (.6 + .4 * np.sin(2 * np.pi * 5.5 * np.arange(n) / SR) ** 2)
    put(seg, at(bar * 4), .05, pan=.4 if bar % 2 else -.4, wet=.6)


# ---------------------------------------------------------------- percussion
def kick(level=1.0, length=.55):
    n = int(length * SR); tt = np.arange(n) / SR
    f = 42 + 95 * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-tt * 6.5)
    y += lp(rng.standard_normal(n), 1800) * np.exp(-tt * 90) * .3
    return np.tanh(y * 1.6) * level


def hat(level=1.0):
    n = int(.09 * SR); tt = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000, 4) * np.exp(-tt * 55) * level


def tom(note, level=1.0):
    n = int(.8 * SR); tt = np.arange(n) / SR
    f = hz(note) * (1 + .5 * np.exp(-tt * 18))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4.5) * level


def impact(level=1.0):
    n = int(5.0 * SR); tt = np.arange(n) / SR
    f = 30 + 60 * np.exp(-tt * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.1)
    crack = lp(rng.standard_normal(n), 3500) * np.exp(-tt * 9) * .55
    air = bp(rng.standard_normal(n), 300, 6000) * np.exp(-tt * 1.6) * .12
    return np.tanh((boom * 1.3 + crack + air) * 1.2) * level


def riser(beats, level=1.0):
    n = int(beats * B * SR); tt = np.arange(n) / SR; p = tt / tt[-1]
    noise = rng.standard_normal(n)
    lo, mid, hi = lp(noise, 600), bp(noise, 800, 4000), hp(noise, 4000)
    y = lo * (1 - p) ** 2 + mid * np.sin(np.pi * p) + hi * p ** 2
    y *= p ** 2.2
    f = 180 * 2 ** (p * 2.3)
    y += np.sin(2 * np.pi * np.cumsum(f) / SR) * p ** 3 * .25
    return y * level


def reverse_swell(beats, level=1.0):
    return riser(beats, level)[::-1][::-1]


def bell(note, level=1.0, length=2.5):
    n = int(length * SR); tt = np.arange(n) / SR; f = hz(note)
    y = sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt * d) for a, m, d in [(1, 1, 1.6), (.4, 2.76, 3.5), (.2, 5.4, 6), (.12, 8.9, 9)])
    return y * np.minimum(1, tt * 200) * level


# Act 1: soft pulse on every cut (beats 0-6)
for b in range(0, 6):
    put(kick(.55 + .05 * b, .8), at(b), .9, wet=.25)
    put(bell(74 if b % 2 == 0 else 69, .5), at(b), .06, pan=(-.5 + .2 * b), wet=.8)
put(impact(.45), at(0), .5, wet=.5)
put(riser(1, .4), at(5), .25, wet=.4)
# Act 2: rapid cuts (beats 6-12)
for b in range(6, 12):
    put(kick(.8), at(b), .95, wet=.2)
    for e in (0, .5):
        put(hat(.6 if e else .35), at(b + e + .25), .35, pan=.3, wet=.15)
    put(tom(38 if b % 2 else 41, .5), at(b + .5), .3, pan=-.3, wet=.3)
put(impact(.6), at(6), .55, wet=.5)
put(riser(2, .5), at(10), .3, wet=.4)
# Act 3: cinematic, heartbeat pulse every 2 beats, bells
put(impact(.5), at(12), .55, wet=.6)
for b in range(12, 40, 2):
    put(kick(.45, .7), at(b), .8, wet=.3)
    put(kick(.25, .5), at(b + .35), .8, wet=.3)
arp = [62, 65, 69, 74, 72, 69, 65, 64]
for i, b in enumerate(np.arange(16, 40, 1.0)):
    put(bell(arp[i % 8] + (0 if (b // 8) % 2 == 0 else -2), .5, 3), at(b + .5), .055, pan=np.sin(i) * .6, wet=.85)
put(riser(4, .9), at(36), .45, wet=.4)
# Act 4: drive (beats 40-72)
bass_roots = {0: 38, 1: 34, 2: 41, 3: 36}
for b in range(40, 72):
    put(kick(1.0), at(b), 1.0, wet=.15)
    put(hat(.7), at(b + .5), .4, pan=.35, wet=.1)
    if b % 2 == 1: put(hat(.4), at(b + .75), .3, pan=-.35, wet=.1)
    root = bass_roots[(b // 4) % 4]
    for e in (0, .5):
        n = int(.33 * SR); tt = np.arange(n) / SR
        bs = np.tanh(2 * (np.sin(2 * np.pi * hz(root) * tt) + .3 * np.sin(2 * np.pi * hz(root + 12) * tt))) * env_ar(n, .005, .2)
        put(lp(bs, 900), at(b + e), .26, wet=.05)
    if b % 4 == 2: put(tom(36, .8), at(b + .75), .35, pan=-.25, wet=.3)
for ib in (40, 48, 54, 72):
    put(impact(1.0), at(ib), .9, wet=.45)
put(riser(4, 1.0), at(44), .5, wet=.4)
put(riser(2, 1.0), at(52), .5, wet=.4)
put(riser(4, 1.0), at(68), .6, wet=.4)
for b in np.arange(64, 72, .5):  # rising arp into the climax
    put(bell(62 + int((b - 64) * 2) % 12 + 12, .5, 1.5), at(b), .05, pan=np.sin(b * 3) * .5, wet=.6)
# Act 5: outro
put(impact(.6), at(77), .5, wet=.7)
for i, b in enumerate(np.arange(74, 86, 1.5)):
    put(bell([74, 69, 65, 62][i % 4], .5, 4), at(b), .06, pan=np.sin(i * 1.7) * .5, wet=.9)

# ---------------------------------------------------------------- reverb (stereo exponential-noise IR)
ir_n = int(3.8 * SR); it = np.arange(ir_n) / SR
irL = lp(rng.standard_normal(ir_n), 5000) * np.exp(-it * 1.9)
irR = lp(rng.standard_normal(ir_n), 5000) * np.exp(-it * 1.9)
irL /= np.sqrt(np.sum(irL ** 2)); irR /= np.sqrt(np.sum(irR ** 2))
wetL = fftconvolve(send_L, irL)[:N]; wetR = fftconvolve(send_R, irR)[:N]
outL = L + wetL * .9; outR = R + wetR * .9

# master: gentle high-pass, glue, fades, limiter
out = np.stack([outL, outR])
out = np.array([hp(ch, 25) for ch in out])
fade = np.interp(t, [0, .05, BEATS * B - 2.2, BEATS * B + .2, DUR], [0, 1, 1, 0, 0])
out *= fade
out /= np.max(np.abs(out)) + 1e-9
out = np.tanh(out * 1.6) / np.tanh(1.6) * .89

import wave
pcm = (np.clip(out.T, -1, 1) * 32767).astype('<i2')
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', sys.argv[1] if len(sys.argv) > 1 else 'music.wav', f'{DUR:.2f}s')
