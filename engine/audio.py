"""Licence-free score synthesis, sound design and mixing (all generated here – no third-party audio).

Narration handling: decoded sample-exact from the supplied file; only a uniform gain is applied, plus a
transparent look-ahead peak limiter on the final mix (documented in the QC report). No time-stretch, pitch
change or edits.
"""
import subprocess, numpy as np
from scipy import signal

SR = 44100   # same rate as the narration → no resampling of the voice

# ------------------------------------------------------------------------------------------- utilities
def load_narration(path, t0=None, t1=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if t0 is not None:
        cmd += ["-af", f"atrim=start={t0}:end={t1},asetpts=PTS-STARTPTS"]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()

def write_wav(path, stereo):
    import wave
    x = np.clip(stereo, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)

def env_adsr(n, a, r, sus=1.0):
    e = np.ones(n, np.float32) * sus
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr: e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e

# ------------------------------------------------------------------------------------------- instruments
def pad_voice(freq, dur, rng, bright=0.35, detune_cents=7.0):
    """Ensemble 'strings': 3 detuned band-limited saws, slow vibrato, soft low-pass weighting."""
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for d in (-detune_cents, 0.0, detune_cents):
        f = freq * 2 ** (d / 1200)
        vib = 1 + 0.0016 * np.sin(2 * np.pi * (4.2 + rng.random()) * t + rng.random() * 6)
        phase = 2 * np.pi * np.cumsum(f * vib) / SR + rng.random() * 6
        K = int(min(28, 7000 / f))
        for k in range(1, K + 1):
            out += (np.sin(k * phase) / k * np.exp(-k * (1 - bright) / 3.2)).astype(np.float32)
    return out / 3

def piano_note(freq, dur, vel=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    B = 0.00035
    for k in range(1, 10):
        fk = k * freq * np.sqrt(1 + B * k * k)
        if fk > 9000: break
        out += (np.sin(2 * np.pi * fk * t) * (1 / k ** 1.25) * np.exp(-t * (0.55 + 0.45 * k))).astype(np.float32)
    att = np.minimum(1, t / 0.006)
    return out * att * vel

def reverb_ir(seconds=3.4, seed=1, damp_hz=4200):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR); t = np.arange(n) / SR
    ir = []
    for ch in range(2):
        x = rng.normal(0, 1, n).astype(np.float32) * np.exp(-6.9 * t / seconds)
        b, a = signal.butter(1, damp_hz / (SR / 2))
        x = signal.lfilter(b, a, x)
        x[:int(0.012 * SR)] = 0  # pre-delay
        ir.append(x / np.sqrt((x ** 2).sum()))
    return np.stack(ir, 1)

def reverb(stereo, wet=0.35, seconds=3.4):
    ir = reverb_ir(seconds)
    w = np.stack([signal.fftconvolve(stereo[:, c], ir[:, c])[:len(stereo)] for c in range(2)], 1)
    return stereo * (1 - wet) + w * wet

# ------------------------------------------------------------------------------------------- score
CHORDS = {  # midi notes (low → high)
    "Dm9": [38, 50, 57, 62, 65, 69, 64], "Bbmaj7": [34, 46, 53, 58, 62, 65, 69], "Gm9": [31, 43, 50, 55, 58, 62, 57],
    "Asus": [33, 45, 52, 57, 62, 64], "A": [33, 45, 52, 57, 61, 64], "Fmaj7": [29, 41, 48, 53, 57, 60, 64],
    "C": [36, 48, 55, 60, 64, 67], "Dm": [38, 50, 57, 62, 65, 69], "Gm": [31, 43, 50, 55, 58, 62],
}

def compose(duration, progression=("Dm9", "Bbmaj7", "Gm9", "Asus", "Dm9", "Fmaj7", "Gm9", "A"), chord_len=7.5,
            seed=4, piano=True, intensity=0.6):
    """Restrained documentary bed: overlapping pad chords, low drone, sparse piano motif, hall reverb."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    L = np.zeros(n + int(8 * SR), np.float32); R = np.zeros_like(L)
    t_ch = 0.0; i = 0
    while t_ch < duration:
        name = progression[i % len(progression)]
        notes = CHORDS[name]
        dur = chord_len + 3.0
        s = int(t_ch * SR)
        e = env_adsr(int(dur * SR), 2.6, 3.0)
        for j, m in enumerate(notes):
            v = pad_voice(midi(m), dur, rng, bright=0.25 + 0.2 * intensity) * e
            g = (0.55 if j == 0 else 0.30) / len(notes)
            pan = 0.5 if j == 0 else 0.5 + 0.35 * ((j % 2) * 2 - 1) * (0.4 + 0.6 * rng.random())
            L[s:s + len(v)] += v * g * np.sqrt(1 - pan); R[s:s + len(v)] += v * g * np.sqrt(pan)
        if piano:  # sparse motif: chord tones, two or three notes per chord
            tones = [m + 12 for m in notes[2:]]
            for k in range(int(rng.integers(2, 4))):
                tt = t_ch + 0.8 + k * chord_len / 3 + rng.random() * 0.4
                if tt > duration - 1: break
                p = piano_note(midi(int(rng.choice(tones))), 6.0, 0.18 + 0.08 * intensity)
                ss = int(tt * SR); pan = 0.35 + 0.3 * rng.random()
                L[ss:ss + len(p)] += p * np.sqrt(1 - pan); R[ss:ss + len(p)] += p * np.sqrt(pan)
        t_ch += chord_len; i += 1
    st = np.stack([L, R], 1)[:n]
    b, a = signal.butter(2, 40 / (SR / 2), "high"); st = signal.lfilter(b, a, st, axis=0)
    b, a = signal.butter(2, 7500 / (SR / 2)); st = signal.lfilter(b, a, st, axis=0)
    st = reverb(st, wet=0.42)
    st = np.tanh(st * 1.2) / 1.2
    return (st / (np.abs(st).max() + 1e-9) * 0.7).astype(np.float32)

# ------------------------------------------------------------------------------------------- sound design
def noise_burst(dur, lo, hi, a=0.05, r=0.3, seed=0, curve=None):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    b, aa = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); x = signal.lfilter(b, aa, x)
    e = env_adsr(n, a, r)
    if curve is not None: e *= curve(np.linspace(0, 1, n))
    x = x * e
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)

def paper_slide(seed=2):
    return noise_burst(0.9, 900, 6000, 0.08, 0.5, seed, lambda u: 0.4 + 0.6 * np.sin(np.pi * u) ** 0.5)

def soft_whoosh(dur=1.2, seed=3):
    return noise_burst(dur, 150, 1800, dur * 0.45, dur * 0.5, seed)

def wind(dur, seed=5):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.normal(0, 1, n)
    b, a = signal.butter(2, [80 / (SR / 2), 700 / (SR / 2)], "band"); x = signal.lfilter(b, a, x)
    mod = signal.resample(rng.random(int(dur * 0.5) + 4), n) if dur > 2 else np.ones(n)
    x = x * (0.6 + 0.4 * (mod - mod.min()) / (np.ptp(mod) + 1e-9))
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)

# ------------------------------------------------------------------------------------------- mixing
def db(x):
    return 10 ** (x / 20)

def voice_envelope(voice, attack=0.08, release=0.7):
    """Smoothed 'voice present' envelope (0..1) for ducking the music."""
    win = int(0.03 * SR)
    rms = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, "same"))
    act = np.clip((20 * np.log10(rms + 1e-9) + 50) / 20, 0, 1)
    out = np.zeros_like(act); g = 0.0
    a_c = np.exp(-1 / (attack * SR)); r_c = np.exp(-1 / (release * SR))
    for i in range(0, len(act), 64):   # block-wise for speed
        v = act[i]
        g = a_c * g + (1 - a_c) * v if v > g else r_c ** 64 * g + (1 - r_c ** 64) * v
        out[i:i + 64] = g
    return out

def limiter(stereo, ceiling_db=-1.5, lookahead=0.005, release=0.08):
    """Look-ahead peak limiter on the full mix (true-peak approximated with 4× oversampling)."""
    over = signal.resample_poly(np.abs(stereo).max(1), 4, 1)
    peak = np.maximum.reduceat(over, np.arange(0, len(over), 4))[:len(stereo)]
    ceil = db(ceiling_db)
    need = np.minimum(1.0, ceil / (peak + 1e-9))
    la = int(lookahead * SR)
    from scipy.ndimage import minimum_filter1d   # min over the look-ahead window
    need = minimum_filter1d(need, size=2 * la + 1, origin=0)
    g = np.empty_like(need); cur = 1.0; rc = np.exp(-1 / (release * SR))
    for i in range(len(need)):
        cur = need[i] if need[i] < cur else rc * cur + (1 - rc) * need[i]
        g[i] = cur
    return stereo * g[:, None], float(20 * np.log10(g.min()))

def loudness(stereo):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(stereo)
