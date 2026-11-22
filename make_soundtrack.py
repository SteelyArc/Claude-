import numpy as np
from scipy.signal import butter, lfilter, sosfilt
from scipy.io import wavfile

SR = 44100
DUR = 60.0
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
    return not (9.2 <= t < 10.25) and t < 59.15

bars = int(DUR / (4 * BEAT))
for b in range(bars):
    tb = b * 4 * BEAT
    name, root, triad = CH[b % 8]
    space = tb >= 40
    for beat in range(4):
        t = tb + beat * BEAT
        if not music_on(t): continue
        if beat in (0, 2):
            bn = root if beat == 0 else root + 7 - (12 if root + 7 > 55 else 0)
            place(musL, musR, tuba(mtof(bn), 0.42), t, 0.55)
        else:
            for k, n in enumerate(triad):
                place(musL, musR, pluck(mtof(n), 0.25), t, 0.16, pan=-0.3 + 0.3 * k)
        place(musL, musR, woodblock(1500 if beat % 2 else 1100), t + E8, 0.06, 0.5)
        place(musL, musR, hat(), t, 0.05, -0.4)
    for i, n in enumerate(MEL[b % 8]):
        t = tb + i * E8
        if n is None or not music_on(t): continue
        if space:
            place(musL, musR, bell(mtof(n + 12), 0.6), t, 0.22, 0.15)
        elif 16 <= tb < 40 and b % 2:
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

# scene 1: town cruising east
S(horn(), 3.0, 0.22, 0.4); S(horn(), 3.25, 0.22, 0.4)
S(whoosh(1.2, 200, 2000), 1.0, 0.10, 0.0)
S(horn(), 6.4, 0.18, -0.2)
# scene 2: the stop
S(scratch(musL + musR, 9.2), 9.2, 0.3)
S(screech(0.9), 9.2, 0.35, 0.0)
S(slide_whistle(500, 1800, 0.9), 9.35, 0.22, 0.4)
for i in range(16):
    S(boing(R := rng.uniform(140, 320), 0.6), 9.45 + i * 0.27 + rng.uniform(0, 0.1), 0.18, rng.uniform(-0.3, 0.9))
for i in range(6):
    S(pop(rng.uniform(600, 1100)), 9.3 + rng.uniform(0, 1.0), 0.25, rng.uniform(-0.5, 0.5))
S(wind(6.8, howl=False), 9.2, 0.10, 0.3)
S(slide_whistle(1600, 400, 1.0), 13.6, 0.15, 0.6)
# scene 3: supersonic car + sonic boom
S(whoosh(0.7), 15.7, 0.35, -0.6)
S(wind(8, howl=False) * 0.6, 16, 0.08, 0.0)
S(boom(), 17.0, 0.75, 0.0)
S(boing(110, 0.9), 18.6, 0.2, 0.3)
S(slide_whistle(900, 300, 0.7), 21.5, 0.15, -0.5)
# scene 4: wind and the bars
S(whoosh(0.7), 23.7, 0.35, 0.6)
S(wind(8.0), 24.0, 0.32, 0.5)
S(slide_whistle(300, 700, 1.0), 24.6, 0.22, -0.4)
S(slide_whistle(300, 2200, 1.6), 25.8, 0.24, 0.4)
S(boing(260, 0.8), 27.45, 0.25, 0.4)
S(bell(mtof(96), 1.0), 27.45, 0.15, 0.4)
for i in range(10):
    S(pop(rng.uniform(300, 700), 0.07), 24.5 + rng.uniform(0, 7), 0.12, rng.uniform(-0.2, 0.9))
# scene 5: tsunami
S(whoosh(0.7), 31.7, 0.35, -0.6)
S(rumble(7.6), 32.0, 0.55, -0.2)
S(slide_whistle(250, 1300, 2.5), 36.0, 0.10, -0.3)
S(splash(), 39.1, 0.55, 0.0)
for i in range(14):
    S(bubble(rng.uniform(300, 900)), 39.35 + i * 0.045, 0.22, rng.uniform(-0.5, 0.5))
S(gulp(), 39.6, 0.5, 0.0)
# scene 6: globe + arrows + sad trombone for ~0 km/h at the pole
S(pop(1200, 0.12), 40.35, 0.3)
for i in range(5):
    S(pluck(mtof(84 - i * 3), 0.25), 40.45 + i * 0.25, 0.35, 0.3)
for k, (m, d) in enumerate([(55, 0.45), (54, 0.45), (53, 0.45), (52, 1.4)]):
    S(trombone(m, d, wobble=(k == 3)), 42.8 + k * 0.48, 0.32, -0.2)
# scene 7: one day = one year
S(whoosh(0.7), 46.7, 0.35, 0.6)
S(bell(mtof(84), 1.5), 47.4, 0.3); S(bell(mtof(91), 1.5), 47.55, 0.25)
for i in range(16):
    tb = 47.6 + rng.uniform(0, 2.7)
    for k in range(3): S(chirp(rng.uniform(2600, 3800)), tb + k * 0.08, 0.08, rng.uniform(-0.6, 0.6))
S(slide_whistle(1400, 300, 0.6), 50.3, 0.15, 0.0)
for i in range(13):
    S(cricket(), 50.7 + i * 0.24, 0.06, -0.4 if i % 2 else 0.4)
# scene 8: oceans drain to the poles
S(whoosh(0.7), 53.7, 0.35, -0.6)
S(gulp(), 55.0, 0.35, -0.2); S(gulp(), 55.9, 0.35, 0.2)
for i in range(40):
    S(bubble(rng.uniform(250, 800)), 54.8 + rng.uniform(0, 3.6), 0.15, rng.uniform(-0.6, 0.6))
S(slide_whistle(1500, 350, 1.4), 55.4, 0.12, 0.0)
# ta-da ending
S(brass_hit([60, 64, 67, 72], 0.18), 58.9, 0.28)
S(brass_hit([60, 64, 67, 72, 76], 1.0), 59.12, 0.32)
S(bell(mtof(96), 1.0), 59.12, 0.12)
# caption pops
for t0 in [0.35, 8.35, 16.35, 24.35, 32.35, 40.35, 47.35, 54.35]:
    S(pop(800, 0.08), t0 + 0.05, 0.18, 0.0)

# ------------------------------------------------------------------ mix
# duck music under the big moments
duck = np.ones(N)
for t0, d in [(16.9, 1.6), (39.0, 1.2), (42.7, 2.3)]:
    i0 = int(t0 * SR); n = int(d * SR)
    duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 0.45)
duck = lp(duck, 6, 1)
mL = musL * duck * 0.9; mR = musR * duck * 0.9
L = mL + sfxL; Rr = mR + sfxR
# gentle fades
fi = int(0.4 * SR); fo = int(0.5 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.abs(L).max(), np.abs(Rr).max())
L = np.tanh(L / peak * 1.25) * 0.9; Rr = np.tanh(Rr / peak * 1.25) * 0.9
wavfile.write('/tmp/claude-0/-home-user-Claude-/863ad0ad-d4b2-5db8-ba22-d69147deca8f/scratchpad/soundtrack.wav', SR,
              (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
