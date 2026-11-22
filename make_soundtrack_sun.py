import sys
OUT_WAV = sys.argv[1] if len(sys.argv) > 1 else 'sun_soundtrack.wav'
import numpy as np
from scipy.signal import butter, lfilter, sosfilt
from scipy.io import wavfile

SR = 44100
DUR = 61.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
musL = np.zeros(N); musR = np.zeros(N)
sfxL = np.zeros(N); sfxR = np.zeros(N)

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def env(n, a=0.01, r=0.05):
    e = np.ones(n); na = max(1, min(n // 2, int(a * SR))); nr = max(1, min(n // 2, int(r * SR)))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
def place(L, R, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[:N - i] * gain
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * l * 1.41; R[i:i + len(sig)] += sig * r * 1.41
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)
def saw(ph): return 2 * (ph % 1.0) - 1
def sq(ph): return np.sign(np.sin(2 * np.pi * ph))
def phase(freq): return np.cumsum(freq) / SR

# ------------------------------------------------------------------ instruments
def tuba(f, d):
    t = tt(d); fr = f * (1 - 0.03 * np.exp(-t * 30))
    p = phase(fr * np.ones_like(t))
    s = np.sin(2*np.pi*p) + 0.5*np.sin(4*np.pi*p) + 0.25*np.sin(6*np.pi*p) + 0.12*np.sin(8*np.pi*p)
    return lp(s * env(len(t), 0.015, 0.08) * np.exp(-t * 3), 900)
def pluck(f, d):
    t = tt(d); s = np.zeros_like(t)
    for k in range(1, 9):
        s += (1 / k) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (6 + 5 * k))
    return s * env(len(t), 0.002, 0.03)
def kazoo(f, d):
    t = tt(d); vib = 1 + 0.012 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 6, 0, 1)
    fr = f * vib * (1 + 0.04 * np.exp(-t * 25) * -1)  # little scoop up
    s = saw(phase(fr)) + 0.15 * rng.standard_normal(len(t))
    return s * env(len(t), 0.02, 0.04)
def bell(f, d):
    t = tt(d)
    s = np.sin(2*np.pi*f*t)*np.exp(-t*4) + 0.4*np.sin(2*np.pi*f*2.76*t)*np.exp(-t*9) + 0.2*np.sin(2*np.pi*f*5.4*t)*np.exp(-t*14)
    return s * env(len(t), 0.002, 0.05)
def hat(d=0.05):
    t = tt(d); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 70)
def woodblock(f=1200, d=0.08):
    t = tt(d); return np.sin(2 * np.pi * f * t) * np.exp(-t * 60)

# ------------------------------------------------------------------ music (120 bpm polka)
BEAT = 0.5; E8 = BEAT / 2
_ = None
MEL = [
    [72,_,76,_,79,76,72,_], [74,72,71,72,_,67,_,_],
    [77,_,81,_,84,81,77,_], [79,77,76,74,_,71,_,67],
    [72,_,76,_,79,_,84,_], [83,_,84,_,79,_,76,_],
    [77,76,77,81,79,77,76,74], [79,_,74,_,71,_,67,_],
]
CH = [('C',48,[60,64,67]),('C',48,[60,64,67]),('F',53,[60,65,69]),('G',43,[59,62,67])] * 2
kaz = np.zeros(N)

def music_on(t):
    return not (31.0 <= t < 36.0) and t < 60.15

bars = int(DUR / (4 * BEAT))
for b in range(bars):
    tb = b * 4 * BEAT
    name, root, triad = CH[b % 8]
    space = tb >= 36
    for beat in range(4):
        t = tb + beat * BEAT
        if not music_on(t): continue
        if beat in (0, 2):
            bn = root if beat == 0 else root + 7 - (12 if root + 7 > 55 else 0)
            place(musL, musR, tuba(mtof(bn), 0.42), t, 0.35 if space else 0.55)
        else:
            for k, n in enumerate(triad):
                place(musL, musR, pluck(mtof(n), 0.25), t, 0.16, pan=-0.3 + 0.3 * k)
        place(musL, musR, woodblock(1500 if beat % 2 else 1100), t + E8, 0.03 if space else 0.06, 0.5)
        place(musL, musR, hat(), t, 0.05, -0.4)
    for i, n in enumerate(MEL[b % 8]):
        t = tb + i * E8
        if n is None or not music_on(t): continue
        if space:
            place(musL, musR, bell(mtof(n + 12), 0.6), t, 0.22, 0.15)
        elif 14 <= tb < 30 and b % 2:
            place(musL, musR, pluck(mtof(n), 0.3), t, 0.3, 0.2)
        else:
            s = kazoo(mtof(n), E8 * 0.85)
            i0 = int(t * SR); kaz[i0:i0 + len(s)] += s[:N - i0]
# kazoo formant / nasal buzz
kaz = bp(kaz, 350, 2600) + 0.6 * bp(kaz, 900, 1300, 2)
kaz = np.tanh(kaz * 1.6) * 0.18
musL += kaz * 0.95; musR += kaz * 1.05

# ------------------------------------------------------------------ SFX
def boing(f0=180, d=0.7):
    t = tt(d); fr = f0 * (1 + 0.6 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 5)) * (1 + 0.4 * t)
    return np.sin(2 * np.pi * phase(fr)) * np.exp(-t * 4.5) * env(len(t), 0.003, 0.05)
def slide_whistle(f1, f2, d):
    t = tt(d); x = t / d; fr = f1 * (f2 / f1) ** (x ** 0.8) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    s = np.sin(2 * np.pi * phase(fr)) + 0.03 * rng.standard_normal(len(t))
    return s * env(len(t), 0.03, 0.06)
def pop(f0=900, d=0.09):
    t = tt(d); fr = f0 * np.exp(-t * 30) + 120
    return np.sin(2 * np.pi * phase(fr)) * np.exp(-t * 35)
def whoosh(d=0.8, lo=300, hi=4000):
    n = int(d * SR); x = rng.standard_normal(n); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        c = i / n; f = lo * (hi / lo) ** np.sin(np.pi * c)
        out[i:i + blk] = bp(x[i:i + blk], f * 0.6, min(f * 1.6, 20000))
    w = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return out * w
def screech(d=0.7):
    t = tt(d); fr = 2300 + 250 * np.sin(2 * np.pi * 37 * t) + 120 * rng.standard_normal(len(t)).cumsum() / 200
    s = np.sin(2 * np.pi * phase(fr)) * 0.6 + 0.3 * bp(rng.standard_normal(len(t)), 1800, 4000)
    return s * env(len(t), 0.01, 0.2) * (1 - t / d * 0.5)
def horn(d=0.18):
    t = tt(d); s = 0.5 * sq(400 * t) + 0.5 * sq(500 * t)
    return lp(s, 2500) * env(len(t), 0.005, 0.02)
def boom():
    t = tt(2.2)
    thump = np.sin(2 * np.pi * phase(70 * np.exp(-t * 2) + 28)) * np.exp(-t * 2.2)
    crack = hp(rng.standard_normal(len(t)), 300) * np.exp(-t * 18)
    rumble = lp(rng.standard_normal(len(t)), 180, 4) * np.exp(-t * 1.6) * 3
    s = thump * 1.0 + crack * 0.5 + rumble * 0.6
    # N-wave: second bang 0.12 s later
    j = int(0.12 * SR); s2 = np.zeros_like(s); s2[j:] = (thump * 0.7 + crack * 0.4)[:-j]
    return np.tanh((s + s2) * 1.4)
def wind(d, howl=True):
    t = tt(d); n = len(t)
    x = bp(rng.standard_normal(n), 200, 1500)
    am = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t + 1) * np.sin(2 * np.pi * 0.9 * t)
    s = x * am
    if howl:
        fr = 420 + 160 * np.sin(2 * np.pi * 0.25 * t) + 60 * np.sin(2 * np.pi * 0.7 * t)
        s += 0.25 * np.sin(2 * np.pi * phase(fr)) * am
    return s * env(n, 0.6, 0.4)
def rumble(d):
    t = tt(d); x = lp(rng.standard_normal(len(t)), 120, 4) * 6
    return x * (t / d) ** 2
def splash():
    t = tt(1.4); s = hp(rng.standard_normal(len(t)), 500) * np.exp(-t * 3.5)
    return s * env(len(t), 0.005, 0.2)
def bubble(f0):
    t = tt(0.07); fr = f0 * (1 + 3 * t / 0.07)
    return np.sin(2 * np.pi * phase(fr)) * np.sin(np.pi * t / 0.07)
def gulp():
    t = tt(0.35); fr = 160 + 500 * (t / 0.35) ** 2
    return np.sin(2 * np.pi * phase(fr)) * np.sin(np.pi * t / 0.35) ** 2
def trombone(m, d, wobble=False):
    t = tt(d); vib = 1 + (0.03 * np.sin(2 * np.pi * 6 * t) * np.clip(t - 0.2, 0, 1) * 2 if wobble else 0.006 * np.sin(2 * np.pi * 5 * t))
    fr = mtof(m) * vib * (1 - 0.02 * np.exp(-t * 20))
    s = lp(saw(phase(fr)), 1400, 2)
    e = env(len(t), 0.04, 0.12)
    if wobble: e *= np.exp(-t * 0.8)
    return s * e
def chirp(f0):
    t = tt(0.06); fr = f0 + 2500 * (t / 0.06)
    return np.sin(2 * np.pi * phase(fr)) * np.sin(np.pi * t / 0.06)
def cricket():
    t = tt(0.25); s = np.sin(2 * np.pi * 4300 * t) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 30 * t)))
    return s * np.sin(np.pi * t / 0.25)
def brass_hit(ms, d):
    t = tt(d); s = sum(saw(mtof(m) * t * (1 + 0.003 * k)) for k, m in enumerate(ms))
    return lp(s, 2600) * env(len(t), 0.02, 0.25) * np.exp(-t * 1.2)
def scratch(buf, t0, d=0.55):
    # rewind/forward the music like a DJ record scratch
    n = int(d * SR); i0 = int(t0 * SR)
    tt_ = np.arange(n) / SR
    rate = np.sin(2 * np.pi * 7 * tt_) * 2.2 - 0.6
    pos = i0 - int(0.05 * SR) + np.cumsum(rate)
    pos = np.clip(pos, 0, N - 1).astype(int)
    s = buf[pos] * 3 + 0.25 * bp(rng.standard_normal(n), 800, 5000) * np.abs(rate) / 2.8
    return s * env(n, 0.005, 0.08)

S = lambda sig, t0, g=1.0, p=0.0: place(sfxL, sfxR, sig, t0, g, p)

def tick(f=2400):
    t = tt(0.03); return np.sin(2*np.pi*f*t)*np.exp(-t*160)
def click():
    t = tt(0.04); return (hp(rng.standard_normal(len(t)), 2000)*0.6 + np.sin(2*np.pi*1800*t))*np.exp(-t*120)
def drumroll(d):
    t = tt(d); x = hp(rng.standard_normal(len(t)), 1500)
    am = 0.55 + 0.45*np.sign(np.sin(2*np.pi*(14 + 10*t/d)*t))
    return x * am * (0.2 + 0.8*(t/d)**1.5)
def chatter(d=1.0):
    out = np.zeros(int(d*SR)); k = 0.0
    while k < d - 0.03:
        c = click()*0.8; i = int(k*SR); out[i:i+len(c)] += c[:len(out)-i]; k += rng.uniform(0.035, 0.06)
    return out * env(len(out), 0.02, 0.15)
def crackle(d):
    out = np.zeros(int(d*SR))
    for _ in range(int(d*14)):
        i = int(rng.uniform(0, d-0.05)*SR); n = int(rng.uniform(0.005, 0.02)*SR)
        out[i:i+n] += hp(rng.standard_normal(n), 3000) * rng.uniform(0.3, 1.0)
    return out
def hum(d):
    t = tt(d); return (np.sin(2*np.pi*120*t) + 0.4*np.sin(2*np.pi*240*t)) * env(len(t), 0.02, 0.3) * (0.6 + 0.4*np.sin(2*np.pi*3*t))

# scene 1: cheerful orbit
S(whoosh(1.4, 200, 1800), 0.8, 0.10, -0.4)
# 7.8 the Sun vanishes: pop + poof
S(pop(1400, 0.15), T_V := 7.8, 0.5)
S(whoosh(0.6, 2000, 6000), 7.8, 0.22)
S(slide_whistle(1800, 500, 0.7), 7.95, 0.16, 0.2)
# the 8 min 20 s clock (sped up): soft ticking
k = 0
for i in range(int((31.0 - 8.3) / 0.5)):
    S(tick(2400 if k % 2 == 0 else 1900), 8.3 + i * 0.5, 0.10, 0.6 if k % 2 else -0.6); k += 1
# scene 3: normal day on Earth
for i in range(10):
    tb = 14.6 + rng.uniform(0, 6.5)
    for j in range(3): S(chirp(rng.uniform(2600, 3800)), tb + j * 0.08, 0.06, rng.uniform(-0.6, 0.6))
S(horn(), 17.2, 0.16, 0.3); S(horn(), 17.45, 0.16, 0.3)
S(boing(220, 0.6), 20.4, 0.12, -0.2)
# scene 4: the front approaches (shimmer) + suspense drumroll
S(whoosh(1.6, 800, 7000), 22.4, 0.10, -0.5)
S(drumroll(1.9), 29.1, 0.22, 0.0)
S(drumroll(1.4), 29.6, 0.18, 0.0)
# 31.0: lights out
S(click(), 31.0, 0.7, 0.0)
S(scratch(musL + musR, 31.0), 31.0, 0.3)
for k2, (m, d) in enumerate([(55, 0.42), (54, 0.42), (53, 0.42), (52, 1.3)]):
    S(trombone(m, d, wobble=(k2 == 3)), 31.7 + k2 * 0.45, 0.30, -0.2)
for i in range(4): S(click(), 31.0 + 0.4 + i * 0.3, 0.25, -0.5 + 0.33 * i)   # windows switching on
S(hum(2.5), 32.6, 0.05, 0.4)                                                   # street lamps
for i in range(14): S(cricket(), 32.4 + i * 0.25, 0.06, -0.4 if i % 2 else 0.4)
# scene 6: Earth flies off in a straight line
S(whoosh(0.7), 35.75, 0.3, -0.6)
S(slide_whistle(400, 1400, 1.6), 36.6, 0.16, 0.4)
S(whoosh(2.0, 150, 1500), 38.2, 0.12, 0.6)
S(boing(150, 0.9), 42.5, 0.15, 0.3)
# scene 7: slow cooling
S(whoosh(0.7), 43.75, 0.3, 0.6)
S(wind(8.0, howl=True) * 0.6, 44.0, 0.12, 0.3)
S(slide_whistle(1200, 700, 2.6), 44.6, 0.13, -0.3)
S(slide_whistle(700, 250, 2.8), 48.2, 0.13, -0.3)
S(chatter(1.0), 46.6, 0.22, 0.2)
S(chatter(1.4), 50.2, 0.26, -0.2)
S(crackle(6.5), 44.8, 0.10, 0.0)
# scene 8: drifting into the dark
S(whoosh(0.7), 51.75, 0.3, -0.6)
S(whoosh(3.5, 100, 900), 53.5, 0.12, 0.0)
S(brass_hit([60, 64, 67, 72], 0.18), 59.9, 0.26)
S(brass_hit([60, 64, 67, 72, 76], 1.0), 60.12, 0.30)
S(bell(mtof(96), 1.0), 60.12, 0.12)
# caption pops
for t0 in [0.35, 7.35, 14.35, 22.35, 29.95, 36.35, 44.35, 52.35]:
    S(pop(800, 0.08), t0 + 0.05, 0.16, 0.0)

# ------------------------------------------------------------------ mix
duck = np.ones(N)
for t0, d in [(7.7, 0.9), (29.2, 1.8)]:
    i0 = int(t0 * SR); n = int(d * SR); duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 0.6)
duck = lp(duck, 6, 1)
L = musL * duck * 0.9 + sfxL; Rr = musR * duck * 0.9 + sfxR
fi = int(0.4 * SR); fo = int(0.6 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.abs(L).max(), np.abs(Rr).max())
L = np.tanh(L / peak * 1.25) * 0.9; Rr = np.tanh(Rr / peak * 1.25) * 0.9
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
