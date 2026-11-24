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

# ------------------------------------------------------------------ music: 120 bpm funk groove
BEAT = 0.5; STEP = BEAT / 4; BAR = 4 * BEAT
def kick():
    t = tt(0.34); f = 46 + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * phase(f)) * np.exp(-t * 8.5) + 0.25 * hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 250)
def snare():
    t = tt(0.24); n = bp(rng.standard_normal(len(t)), 1200, 8000) * np.exp(-t * 17)
    return n * 0.8 + 0.45 * np.sin(2 * np.pi * phase(np.full(len(t), 185.0))) * np.exp(-t * 28)
def clap():
    t = tt(0.26); n = bp(rng.standard_normal(len(t)), 900, 4500); e = np.zeros_like(t)
    for d in (0.0, 0.011, 0.023):
        i = int(d * SR); e[i:] += np.exp(-t[:len(t) - i] * 70)
    e += 0.6 * np.exp(-t * 13); return n * e * 0.55
def chh(): t = tt(0.05); return hp(rng.standard_normal(len(t)), 8000) * np.exp(-t * 90)
def ohh(): t = tt(0.3); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 9)
def cowbell():
    t = tt(0.15); return bp(sq(540 * t) + sq(800 * t), 500, 3000) * np.exp(-t * 22)
def sbass(f, d):
    t = tt(d); s = saw(phase(np.full(len(t), f))) + 0.5 * sq(phase(np.full(len(t), f / 2)))
    return lp(s, 700 + 900 * 0.5, 2) * env(len(t), 0.004, 0.03) * (0.55 + 0.45 * np.exp(-t * 9))

# sections (bar = 2 s): A = bright funk, B = dark minor funk, None = silence
def section(t):
    if t >= 60.0: return None
    if 12.1 <= t < 14.5: return 'B0'            # engine coughing: music sputters
    if 14.5 <= t < 17.0: return 'BUILD'
    if 23.0 <= t < 29.0: return 'B'
    if 41.0 <= t < 48.0: return 'B'
    return 'A'
CH_A = [(48, [60, 64, 67]), (48, [60, 64, 67]), (53, [60, 65, 69]), (55, [59, 62, 67])]
CH_B = [(45, [57, 60, 64]), (45, [57, 60, 64]), (41, [57, 60, 65]), (40, [56, 59, 64])]
KICK_A = [0, 6, 8, 10]; SNARE_A = [4, 12]; BASS_A = [(0, 0), (3, 0), (6, 12), (8, 0), (10, 7), (11, 12), (14, 0)]
KICK_B = [0, 3, 10]; SNARE_B = [8]; BASS_B = [(0, 0), (3, 0), (8, 0), (11, 3), (14, 7)]
MEL_A = [[72,None,76,None,79,76,72,None,74,72,71,72,None,67,None,None],
         [77,None,81,None,84,81,77,None,79,77,76,74,None,71,None,67]]
MEL_B = [[69,None,None,72,None,76,None,None,74,None,72,None,71,None,None,None],
         [69,None,None,72,None,77,None,76,None,74,None,72,None,71,None,68]]
kaz = np.zeros(N)
nbars = int(DUR / BAR) + 1
for b in range(nbars):
    tb = b * BAR
    for st in range(16):
        t = tb + st * STEP
        sec = section(t)
        if sec is None or t >= DUR: continue
        if sec == 'A':
            root, triad = CH_A[b % 4]
            if st in KICK_A: place(musL, musR, kick(), t, 0.85)
            if st in SNARE_A: place(musL, musR, snare(), t, 0.5); place(musL, musR, clap(), t, 0.35, 0.2)
            place(musL, musR, chh(), t, 0.10 if st % 2 else 0.16, -0.35)
            if st == 14: place(musL, musR, ohh(), t, 0.10, 0.35)
            if st in (2, 9) and b % 2: place(musL, musR, cowbell(), t, 0.07, 0.5)
            for s2, iv in BASS_A:
                if s2 == st: place(musL, musR, sbass(mtof(root - 12 + iv), STEP * 1.6), t, 0.5)
            if st in (4, 12):
                for k, n in enumerate(triad): place(musL, musR, pluck(mtof(n), 0.22), t + STEP, 0.10, -0.3 + 0.3 * k)
            # kazoo lead only where Earth is not whistling
            if True:
                n = MEL_A[b % 2][st]
                if n is not None:
                    s = kazoo(mtof(n), STEP * 1.7); i0 = int(t * SR); kaz[i0:i0 + len(s)] += s[:N - i0]
        elif sec in ('BUILD', 'BUILD1'):
            root, triad = CH_A[b % 4]
            prog = (t - 14.5) / 2.5
            if st % 4 == 0: place(musL, musR, kick(), t, 0.85)
            rate = 4 if prog < 0.5 else (2 if prog < 0.85 else 1)
            if st % rate == 0: place(musL, musR, snare(), t, 0.4 + 0.5 * prog)
            place(musL, musR, chh(), t, 0.12, -0.35)
            if st % 2 == 0:
                for s2, iv in BASS_A:
                    if s2 == st: place(musL, musR, sbass(mtof(root - 12 + iv), STEP * 1.6), t, 0.5)
        else:  # B0 / B
            root, triad = CH_B[b % 4]
            if st in KICK_B: place(musL, musR, kick(), t, 0.9)
            for s2, iv in BASS_B:
                if s2 == st: place(musL, musR, sbass(mtof(root - 12 + iv), STEP * 2.2), t, 0.55)
            if sec == 'B':
                if st in SNARE_B: place(musL, musR, snare(), t, 0.5); place(musL, musR, clap(), t, 0.3, -0.2)
                if st % 2 == 0: place(musL, musR, chh(), t, 0.12, -0.35)
                if st == 6: place(musL, musR, ohh(), t, 0.08, 0.35)
                n = MEL_B[b % 2][st]
                if n is not None: place(musL, musR, bell(mtof(n + 12), 0.7), t, 0.2, 0.2)
                if st == 0:
                    for k, n2 in enumerate(triad): place(musL, musR, pluck(mtof(n2), 0.6), t, 0.08, -0.3 + 0.3 * k)
kaz = bp(kaz, 350, 2600) + 0.6 * bp(kaz, 900, 1300, 2)
kaz = np.tanh(kaz * 1.6) * 0.16
musL += kaz * 0.95; musR += kaz * 1.05
# riser into the lights-out moment
_t = tt(4.0); _r = bp(rng.standard_normal(len(_t)), 800, 6000) * (_t / 4.0) ** 2 * 0.6
place(musL, musR, _r, 13.4, 1.0)


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


def whistle(m, d):
    t = tt(d); fr = mtof(m) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t)) * (1 + 0.03 * np.exp(-t * 30))
    return (np.sin(2 * np.pi * phase(fr)) + 0.02 * rng.standard_normal(len(t))) * env(len(t), 0.03, 0.05)
def kazoo_brr(d=0.9):
    t = tt(d); fr = 140 * (1 + 0.08 * np.sign(np.sin(2 * np.pi * 18 * t)))
    return np.tanh(bp(saw(phase(fr)), 300, 2500) * 2) * env(len(t), 0.02, 0.15)

def beep(f=2000, d=0.09):
    t = tt(d); return sq(f * t) * 0.4 * env(len(t), 0.003, 0.01)
def bleat(d=0.6):
    t = tt(d); f = 330 * (1 + 0.06 * np.sin(2 * np.pi * 7 * t)) * (1 - 0.1 * t / d)
    return np.tanh(bp(saw(phase(f)), 500, 2600) * 2.5) * env(len(t), 0.03, 0.15)
def dig():
    t = tt(0.16); return lp(rng.standard_normal(len(t)), 1800) * np.exp(-t * 28) + 0.3 * np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30)
def sizzle(d):
    t = tt(d); return hp(rng.standard_normal(len(t)), 4000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3 * t))) * env(len(t), 0.3, 0.3)
def plip(f=900):
    t = tt(0.08); return np.sin(2 * np.pi * phase(f * (1 + 2 * t / 0.08))) * np.sin(np.pi * t / 0.08)


def hoot(f=420, d=0.35):
    t = tt(d); fr = f * (1 + 0.08 * np.sin(np.pi * t / d)) ; return np.sin(2 * np.pi * phase(fr)) * np.sin(np.pi * t / d) ** 1.5
def gullcry(d=0.5):
    t = tt(d); fr = 1800 * (1 - 0.35 * t / d) * (1 + 0.03 * np.sin(2 * np.pi * 30 * t)); return bp(saw(phase(fr)), 1200, 4000) * env(len(t), 0.02, 0.15)
def wash(d):
    t = tt(d); x = lp(rng.standard_normal(len(t)), 1200, 2) * 2; return x * (0.35 + 0.65 * np.sin(np.pi * ((t * 0.38) % 1)) ** 2) * env(len(t), 0.4, 0.4)
def wub(d):
    t = tt(d); return np.sin(2 * np.pi * phase(70 + 25 * np.sin(2 * np.pi * 0.9 * t))) * env(len(t), 0.2, 0.3)

def drip(f=1400):
    t = tt(0.12); return np.sin(2 * np.pi * phase(f * (1 + 3 * t))) * np.exp(-t * 30)
def clink():
    return bell(mtof(98), 0.4) * 0.6 + bell(mtof(103), 0.4) * 0.4
def splashS(d=0.8):
    t = tt(d); return hp(rng.standard_normal(len(t)), 600) * np.exp(-t * 4.5) * env(len(t), 0.005, 0.2)
def honk(f=520, d=0.18):
    t = tt(d); return np.tanh(bp(saw(phase(np.full(len(t), f))), 400, 2200) * 3) * env(len(t), 0.01, 0.05)

def rumbleR(d):
    t = tt(d); return lp(rng.standard_normal(len(t)), 160, 3) * 5 * env(len(t), 0.1, 0.5)
def thunder():
    t = tt(1.6); return (lp(rng.standard_normal(len(t)), 300, 2) * 4 + hp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 25)) * np.exp(-t * 2.2)
def squish():
    t = tt(0.5); return np.sin(2 * np.pi * phase(400 * np.exp(-t * 5) + 60)) * np.exp(-t * 4) + 0.3 * bp(rng.standard_normal(len(t)), 300, 1200) * np.exp(-t * 8)
def freeze():
    t = tt(0.9); return sum(np.sin(2 * np.pi * f * t) * np.exp(-t * (3 + k)) for k, f in enumerate([2093, 2637, 3136, 4186])) * 0.25 + hp(rng.standard_normal(len(t)), 5000) * np.exp(-t * 10) * 0.3
def creak(d=0.9):
    t = tt(d); f = 180 * (1 - 0.35 * t / d) * (1 + 0.04 * np.sin(2 * np.pi * 23 * t))
    return bp(saw(phase(f)), 300, 2500) * env(len(t), 0.05, 0.2)

def ping(f=1150):
    t = tt(2.2); s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.5)
    out = s.copy(); d = int(0.45 * SR); out[d:] += 0.35 * s[:-d]; return out * env(len(t), 0.005, 0.3)
def whalesong(d=3.0):
    t = tt(d); f = 180 + 90 * np.sin(2 * np.pi * 0.35 * t) + 40 * np.sin(2 * np.pi * 1.3 * t)
    return np.tanh(bp(saw(phase(f)), 150, 1400) * 1.5) * env(len(t), 0.5, 0.8)
def underwater(d):
    t = tt(d); return lp(rng.standard_normal(len(t)), 220, 3) * 3 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.2 * t)) * env(len(t), 0.5, 0.5)
def thud():
    t = tt(0.8); return np.sin(2 * np.pi * phase(70 * np.exp(-t * 4) + 30)) * np.exp(-t * 5) + lp(rng.standard_normal(len(t)), 300) * np.exp(-t * 6) * 2
# ---------------------------------------------------------------- car to the Moon SFX
def cheer(d=1.6):
    t = tt(d); x = bp(rng.standard_normal(len(t)), 500, 5000) * 1.5; return x * env(len(t), 0.05, 0.9) * (1 + 0.3 * np.sin(2 * np.pi * 7 * t))
def engine(d, f0, f1, rough=1.0):
    t = tt(d); f = f0 + (f1 - f0) * (t / d) ** 0.7; f = f * (1 + 0.03 * np.sin(2 * np.pi * 7 * t))
    x = saw(phase(f)) + 0.6 * sq(phase(f * 0.5)) + 0.3 * rough * rng.standard_normal(len(t))
    return np.tanh(lp(x, 900, 2) * 1.6) * env(len(t), 0.05, 0.25)
def cough():
    t = tt(0.42); x = bp(rng.standard_normal(len(t)), 300, 2400) * np.exp(-t * 9) * 1.6
    x += np.sin(2 * np.pi * phase(110 * np.exp(-t * 3))) * np.exp(-t * 10)
    return np.tanh(x * 1.5)
def jet(d):
    t = tt(d); f = np.linspace(1.15, 0.85, len(t)); x = bp(rng.standard_normal(len(t)), 600, 5000) + 0.4 * np.sin(2 * np.pi * phase(900 * f))
    return x * np.exp(-((t - d / 2) / (d / 4)) ** 2) * 0.8
def hiss(d):
    t = tt(d); return hp(rng.standard_normal(len(t)), 4000) * env(len(t), 0.01, d * 0.6) * 0.6
def crunch():
    t = tt(0.25); return bp(rng.standard_normal(len(t)), 1500, 7000) * (rng.random(len(t)) > 0.7) * np.exp(-t * 12) * 1.5
def clank():
    t = tt(0.3); return (np.sin(2 * np.pi * 420 * t) + 0.6 * np.sin(2 * np.pi * 1130 * t) + 0.3 * np.sin(2 * np.pi * 2470 * t)) * np.exp(-t * 14) * 0.6
CUTS = [5, 11, 17, 23, 29, 35, 41, 48, 54]
for k, c in enumerate(CUTS): S(whoosh(0.5, 400, 6000), c - 0.3, 0.28, 0.5 if k % 2 else -0.5)
for t0 in [0.0] + CUTS: S(pop(800, 0.08), t0 + 0.2, 0.14, 0.0)
# 0–5 start the engine, honk under the sign
S(click(), 0.35, 0.3); S(engine(0.5, 40, 55, 2.0), 0.45, 0.2); S(engine(4.6, 55, 120), 0.95, 0.22, -0.1)
S(honk(520, 0.16), 3.7, 0.22, 0.2); S(honk(520, 0.28), 3.92, 0.22, 0.2)
# 5–11 climbing into the sky, jet flyby
S(engine(6.0, 120, 135), 5.0, 0.2, -0.1); S(wind(6.0, False), 5.0, 0.12, 0.0)
S(jet(3.4), 7.0, 0.35, 0.4); S(slide_whistle(500, 1500, 0.4), 8.4, 0.16, 0.3); S(honk(600, 0.14), 9.0, 0.2); S(honk(600, 0.14), 9.2, 0.2)
# 11–17 the engine chokes, helmet on, oxygen tanks, revs again
S(engine(1.2, 125, 90), 11.0, 0.2, -0.1)
for t0 in [12.2, 12.75, 13.5, 14.1]: S(cough(), t0, 0.45, rng.uniform(-0.2, 0.2)); S(engine(0.35, 70, 40, 2.5), t0 + 0.05, 0.16)
S(trombone(48, 0.5, wobble=True), 13.0, 0.12, 0.2)
S(pop(1200, 0.09), 14.4, 0.25); S(clink(), 14.5, 0.25); S(hiss(0.6), 14.55, 0.22, -0.3)
S(engine(1.8, 60, 160), 15.2, 0.26); S(slide_whistle(400, 1800, 0.6), 15.3, 0.14)
for i in range(5): S(bell(mtof(96 + 2 * i), 0.4), 15.4 + i * 0.12, 0.08, -0.5 + 0.25 * i)
# 17–23 edge of space: crossing the Kármán line
S(engine(6.0, 150, 150), 17.0, 0.14, -0.1); S(wind(3.0, False), 17.0, 0.08, 0.0)
S(ping(1320), 19.9, 0.3); S(brass_hit([60, 64, 67, 72], 0.6), 19.9, 0.22); S(cheer(1.4), 20.0, 0.25)
# 23–29 day counter ticks, arrival ding
for t0 in np.arange(23.5, 28.5, 0.16): S(tick(2400 + 200 * ((t0 * 6) % 3)), t0, 0.06, rng.uniform(-0.3, 0.3))
S(bell(mtof(91), 1.2), 28.5, 0.18)
# 29–35 road-trip party: radio scratch, snack crunches, music notes
S(whoosh(0.3, 1500, 7000), 29.2, 0.15)
for t0 in [30.4, 30.7, 32.2, 32.5, 33.9]: S(crunch(), t0, 0.35, rng.uniform(-0.4, 0.4))
for t0 in [29.8, 31.0, 32.8, 34.2]: S(pop(1600, 0.05), t0, 0.12, rng.uniform(-0.5, 0.5))
# 35–41 hundreds of fuel barrels pop in
bt = 35.3
while bt < 39.9:
    S(pop(700 + rng.integers(0, 600), 0.05), bt, 0.12, rng.uniform(-0.6, 0.6))
    if rng.random() < 0.3: S(clank(), bt, 0.08, rng.uniform(-0.5, 0.5))
    bt += max(0.06, 0.32 * (1 - (bt - 35.3) / 4.6) ** 1.5)
S(trombone(55, 0.25), 39.9, 0.16); S(trombone(54, 0.25), 40.18, 0.16); S(trombone(53, 0.7, wobble=True), 40.46, 0.16)
# 41–48 the Moon laps Earth: a whoosh per lap
def ease_py(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
lap_t = []
for tt0 in np.arange(41.5, 47.5, 0.005):
    k = int(5.86 * ease_py((tt0 - 41.5) / 6.0))
    if k > len(lap_t): lap_t.append(tt0)
for i, t0 in enumerate(lap_t): S(whoosh(0.45, 500, 5000), t0 - 0.2, 0.3, -0.6 + 0.24 * i); S(woodblock(900 + 120 * i), t0, 0.15)
S(boing(140, 0.5), 43.2, 0.2); S(kazoo_brr(0.8), 45.2, 0.12)
# 48–54 landing on the Moon
S(engine(3.2, 120, 60), 48.0, 0.18); S(thud(), 51.2, 0.5); S(cheer(2.2), 51.25, 0.3); S(pop(1100, 0.08), 51.2, 0.2)
S(whistle(84, 0.15), 51.7, 0.12, 0.2); S(whistle(88, 0.3), 51.88, 0.12, 0.2); S(clink(), 51.65, 0.18)
# 54–61 shades on, recap card, finale
S(ping(1760), 54.3, 0.2)
for t0 in [55.3, 56.0, 56.7, 57.4]: S(pop(1300, 0.08), t0, 0.18, 0.0)
S(honk(520, 0.16), 58.6, 0.2); S(honk(660, 0.3), 58.8, 0.2)
S(brass_hit([60, 64, 67, 72], 0.18), 59.75, 0.26)
S(brass_hit([60, 64, 67, 72, 76], 1.0), 60.0, 0.30)
S(bell(mtof(96), 1.0), 60.0, 0.12); S(kick(), 60.0, 0.6); S(snare(), 59.75, 0.3)

# ------------------------------------------------------------------ mix
duck = np.ones(N)
for t0, d in [(12.1, 2.4)]:
    i0 = int(t0 * SR); n = int(d * SR); duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 0.65)
duck = lp(duck, 6, 1)
L = musL * duck * 0.9 + sfxL; Rr = musR * duck * 0.9 + sfxR
fi = int(0.4 * SR); fo = int(0.6 * SR)
for ch in (L, Rr):
    ch[:fi] *= np.linspace(0, 1, fi); ch[-fo:] *= np.linspace(1, 0, fo)
peak = max(np.percentile(np.abs(L), 99.97), np.percentile(np.abs(Rr), 99.97))
L = np.tanh(L / peak * 1.25) * 0.9; Rr = np.tanh(Rr / peak * 1.25) * 0.9
wavfile.write(OUT_WAV, SR, (np.stack([L, Rr], 1) * 32767).astype(np.int16))
print('ok', peak)
