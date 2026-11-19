"""Full-film audio: untouched narration + generated score with a mood arc + subtle sound design.

Score sections (narration time):
  A   0–60   orientation, Middle Ages      D minor, gentle
  B  57–106  Prussian era                  brighter (F major colour)
  C 103–203  1918 → interwar tension       D minor, fuller pads
  D 200–248  1939–1945: war and crimes     dark, slow, no piano, quieter
  E 245–300  post-war, loss, displacement  reflective
  F 297–end  today & end card              warm resolution, fade-out
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from scipy import signal
from engine.audio import (SR, load_narration, compose, paper_slide, soft_whoosh, wind, voice_envelope, limiter,
                          loudness, write_wav, db, noise_burst)
from projects.west_prussia import film as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET_LUFS = -15.0
MUSIC = os.environ.get("MUSIC", "0") == "1"   # producer decision: no background music (default off)

SECTIONS = [  # start, end, progression, chord_len, intensity, piano, gain_db, seed
    (0.0, 60.0, ("Dm9", "Bbmaj7", "Fmaj7", "C"), 7.5, 0.45, True, 0.0, 11),
    (57.0, 106.0, ("Fmaj7", "C", "Dm9", "Bbmaj7"), 7.0, 0.55, True, 0.0, 12),
    (103.0, 203.0, ("Dm9", "Bbmaj7", "Gm9", "Asus", "Dm9", "Bbmaj7", "Gm9", "A"), 7.2, 0.6, True, 0.0, 13),
    (200.0, 248.0, ("Dm", "Gm", "Dm", "A"), 9.0, 0.3, False, -2.5, 14),
    (245.0, 300.0, ("Gm9", "Dm9", "Bbmaj7", "Asus"), 8.0, 0.45, True, -0.5, 15),
    (297.0, F.T_END + 0.5, ("Fmaj7", "C", "Dm9", "Bbmaj7", "Dm9"), 7.0, 0.5, True, 0.0, 16),
]

def surf(dur, seed=8):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); x = rng.normal(0, 1, n)
    b, a = signal.butter(2, [180 / (SR / 2), 2200 / (SR / 2)], "band"); x = signal.lfilter(b, a, x)
    t = np.arange(n) / SR
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.5) ** 2
    x = x * swell
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)

def build(out_wav):
    v = load_narration(os.path.join(ROOT, "audio/narration_en.mp3"))
    n = int(F.T_END * SR)
    voice = np.zeros(n, np.float32); voice[:len(v)] = v
    # ---- score
    music = np.zeros((n, 2), np.float32)
    for (t0, t1, prog, cl, inten, piano, gdb, seed) in (SECTIONS if MUSIC else []):
        dur = t1 - t0
        m = compose(dur, progression=prog, chord_len=cl, seed=seed, piano=piano, intensity=inten)
        s = int(t0 * SR); e = min(n, s + len(m)); m = m[:e - s]
        k = np.ones(len(m), np.float32)
        fi = int(3.0 * SR)
        if t0 > 0: k[:fi] = np.sin(np.linspace(0, np.pi / 2, fi)) ** 2
        if t1 < F.T_END: k[-fi:] = np.cos(np.linspace(0, np.pi / 2, fi)) ** 2
        music[s:e] += m * (k * db(gdb))[:, None]
    end_fade = np.ones(n, np.float32); fo = int(3.2 * SR); end_fade[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
    duck = voice_envelope(voice)
    mus = music * (db(-17) * (1 - 0.55 * duck) * end_fade)[:, None]
    fade_in = np.minimum(1, np.arange(n) / (0.5 * SR))
    mix = mus * fade_in[:, None]
    def place(sig, t, gain_db, pan=0.5):
        s = int(t * SR); e = min(n, s + len(sig))
        if 0 <= s < n:
            mix[s:e, 0] += sig[:e - s] * db(gain_db) * np.sqrt(1 - pan)
            mix[s:e, 1] += sig[:e - s] * db(gain_db) * np.sqrt(pan)
    # ---- sound design
    for (a0, b0, f0), (a1, b1, f1) in zip(F.SHOTS, F.SHOTS[1:]):
        if a1 < b0 and F.trans_style(f0, f1) == "ink":
            dark = 200 <= a1 <= 250
            place(soft_whoosh(1.4, int(a1 * 10) % 97), a1 - 0.2, -40 if dark else -35)
    for t in (135.5, 165.9):
        place(paper_slide(int(t)), t, -28, 0.55)
    w = wind(F.T_END, 5); mix += (w * db(-47) * fade_in)[:, None] * np.array([[1.0, 0.9]])
    sea = surf(21.0); env = np.minimum(1, np.minimum(np.arange(len(sea)) / (2 * SR), (len(sea) - np.arange(len(sea))) / (4 * SR)))
    place(sea * env, 0.0, -38, 0.45)
    sea2 = surf(F.T_END - 305.0, 9); env2 = np.minimum(1, np.minimum(np.arange(len(sea2)) / (4 * SR), (len(sea2) - np.arange(len(sea2))) / (3 * SR)))
    place(sea2 * env2, 305.0, -40, 0.55)
    # ---- final mix: narration centred and unchanged, uniform gain only, look-ahead peak limiter
    full = np.stack([voice, voice], 1) + mix
    lufs = loudness(full); g = db(TARGET_LUFS - lufs)
    full, gr = limiter(full * g, -1.5)
    print(f"mix {lufs:.1f} LUFS → gain {20*np.log10(g):+.2f} dB, limiter max {gr:.1f} dB, final {loudness(full):.1f} LUFS")
    if MUSIC:
        vl, ml = loudness(np.stack([voice, voice], 1)), loudness(mus)
        print(f"voice {vl:.1f} LUFS, music bed {ml:.1f} LUFS → music {vl-ml:.1f} LU under voice")
    else:
        print("no background music (narration + subtle sound design only)")
    write_wav(out_wav, full)
    return out_wav

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build/audio_film.wav"))
