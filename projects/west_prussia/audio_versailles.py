"""Audio for the Phase 3 preview (narration 117.8–151.0 s): narration + generated score + sound design."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from engine.audio import (SR, load_narration, compose, paper_slide, soft_whoosh, wind, voice_envelope, limiter,
                          loudness, write_wav, db)
from projects.west_prussia.seq_versailles import T0, T1

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET_LUFS = -15.0

def build(out_wav):
    v = load_narration(os.path.join(ROOT, "audio/narration_en.mp3"), T0, T1)
    n = len(v); dur = n / SR
    music = compose(dur + 0.5, progression=("Dm9", "Bbmaj7", "Gm9", "Asus", "Dm9"), chord_len=7.2, seed=19,
                    intensity=0.55)[:n]
    duck = voice_envelope(v)
    mus_gain = db(-17) * (1 - 0.55 * duck)              # music well below the voice, ducked further while speaking
    fade = np.minimum(1, np.minimum(np.arange(n) / (0.6 * SR), (n - np.arange(n)) / (0.8 * SR)))
    mix = music * (mus_gain * fade)[:, None]
    def place(sig, t, gain_db, pan=0.5):
        s = int((t - T0) * SR); e = min(n, s + len(sig))
        if s < n:
            mix[s:e, 0] += sig[:e - s] * db(gain_db) * np.sqrt(1 - pan)
            mix[s:e, 1] += sig[:e - s] * db(gain_db) * np.sqrt(pan)
    for t, seed in ((123.3, 3), (141.1, 9)):
        place(soft_whoosh(1.4, seed), t, -34)
    place(paper_slide(), 135.5, -28, 0.55)
    w = wind(dur, 5); mix += (w * db(-46) * fade)[:, None] * np.array([[1.0, 0.9]])
    voice = np.stack([v, v], 1) * np.sqrt(0.5) * 2 ** 0.5   # centred, unchanged
    full = voice + mix
    lufs = loudness(full)
    g = db(TARGET_LUFS - lufs)
    full, gr = limiter(full * g, -1.5)
    print(f"mix: {lufs:.1f} LUFS → gain {20*np.log10(g):+.1f} dB, limiter max reduction {gr:.1f} dB, final {loudness(full):.1f} LUFS")
    write_wav(out_wav, full)
    return out_wav

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build/audio_versailles.wav"))
