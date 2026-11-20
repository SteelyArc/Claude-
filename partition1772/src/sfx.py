"""Cinematic sound design for the cold open, synthesised (no third-party samples).
Deep layered impacts for each territory torn away, a low tearing rumble, soft cut 'slices', a sub swell into the whip-out."""
import numpy as np, sys
from scipy import signal
from scipy.io import wavfile
SR = 48000
rng = np.random.default_rng(7)
def t_(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=4): return signal.sosfilt(signal.butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=4): return signal.sosfilt(signal.butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def brown(n):
    w = rng.standard_normal(n); b = np.cumsum(w); b -= lp(b, 8, 2); return b / (np.abs(b).max() + 1e-9)

def impact(f0=62, f1=27, dur=3.2, body=1.0):
    t = t_(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 5.5)                     # pitch drop
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 1.35)
    sub = np.tanh(2.2 * sub) / np.tanh(2.2)                      # warm saturation -> harmonics audible on phones
    knock = lp(rng.standard_normal(len(t)), 320) * np.exp(-t * 26) * 2.2   # felt 'thud' transient
    rumble = lp(brown(len(t)), 140) * np.exp(-t * 2.2) * 0.8
    att = 1 - np.exp(-t * 400)
    return att * (0.9 * sub + 0.55 * body * knock + 0.45 * rumble)

def tear(dur=0.9):
    """Low, heavy rip: band-limited brown noise with grainy amplitude modulation (earth/parchment, not hiss)."""
    t = t_(dur); n = brown(len(t))
    grain = np.clip(lp(rng.standard_normal(len(t)), 38), 0, None); grain /= grain.max() + 1e-9
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * (0.35 + 0.65 * grain)
    return bp(n, 90, 700) * env * 1.4

def slice_(dur=0.45):
    t = t_(dur); n = rng.standard_normal(len(t))
    sweep = bp(n, 300, 2400) * np.exp(-t * 9) * (1 - np.exp(-t * 120))
    return lp(sweep, 2600) * 0.35

def swell(dur=1.6):
    t = t_(dur); n = brown(len(t))
    env = (t / dur) ** 2.2 * np.exp(-((t - dur) / 0.08) ** 2 * 0.0 + 0)    # rises into the whip
    env = np.where(t < dur * 0.9, (t / (dur * 0.9)) ** 2, np.exp(-(t - dur * 0.9) * 25))
    return lp(n, 420) * env * 0.9

def reverb(x, rt=1.6, mix=0.28):
    n = int(rt * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / rt); ir = lp(ir, 2200, 2); ir /= np.sqrt((ir ** 2).sum())
    wet = signal.fftconvolve(x, ir)[:len(x)]
    return (1 - mix) * x + mix * wet * 3.0

def place(buf, x, at, g=1.0):
    i = int(at * SR); j = min(len(buf), i + len(x)); buf[i:j] += g * x[:j - i]

if __name__ == '__main__':
    out = np.zeros(int(7.0 * SR))
    # film clock: narration starts at 1.0 s; hook events from scenes.HOOK_PIECES (a = t - 1)
    place(out, impact(54, 30, 2.6, body=0.6), 0.03, 0.55)          # opening hit under the title
    for k, at in enumerate((0.20, 0.38, 0.56)):                     # glowing cuts
        place(out, slice_(), at, 0.9)
    for k, (at, f0, f1) in enumerate(((0.95, 58, 26), (1.13, 66, 30), (1.31, 62, 28))):   # the three lands torn away
        place(out, tear(0.95), at - 0.08, 0.75)
        place(out, impact(f0, f1, 3.0), at, 0.95)
    place(out, swell(1.5), 3.0, 0.8)                                # into the whip-out to Europe
    place(out, impact(48, 26, 2.4, body=0.3), 4.45, 0.35)           # soft landing on the Europe map
    out = reverb(out)
    out = hp(out, 22, 2)
    out = out / np.abs(out).max() * 0.70                             # peak ≈ -3 dBFS before mixing
    wavfile.write(sys.argv[1], SR, (out * 32767).astype(np.int16))
