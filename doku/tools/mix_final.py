"""Mix final soundtrack and assemble the finished MP4.

python3 mix_final.py <parts_dir> <out.mp4>
Expects parts_dir/opening.wav, opening.mp4, part_00..03.mp4.
"""
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("SCRATCH", "/tmp")
import render_doc as RD
if os.environ.get("RENDER_V2"):
    import render_v2  # noqa: F401  (patches RD.build_shots)

SR = 48000


def read_wav(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    parts, out = sys.argv[1], sys.argv[2]
    tl, end = RD.timeline()
    total = end
    n = int(total * SR)
    mix = np.zeros(n, np.float32)
    op = read_wav(os.path.join(parts, "opening.wav"))
    mix[:min(len(op), n)] += op[:n]
    nar = read_wav(os.environ.get("NARRATION") or os.path.join(RD.ROOT, "audio", "narration_lewis.wav"))
    nar = nar / (np.abs(nar).max() + 1e-6) * 0.85
    s = int(RD.NAR0 * SR)
    L = min(len(nar), n - s)
    mix[s:s + L] += nar[:L]
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    noise = rng.normal(0, 1, n).astype(np.float32)
    bed = (0.03 * np.sin(2 * np.pi * 55 * t) + 0.018 * np.sin(2 * np.pi * 82.4 * t + 1) + 0.008 * np.sin(2 * np.pi * 110.2 * t))
    bed *= 0.65 + 0.35 * np.sin(2 * np.pi * 0.05 * t)
    fade_in = np.clip((t - RD.NAR0 + 1.0) / 2.0, 0, 1)
    mix += (bed * fade_in).astype(np.float32)
    soft = np.convolve(noise, np.ones(80) / 80, "same")
    for s0, e0, shot in tl:
        if s0 <= RD.NAR0 + 0.1:
            continue
        a, b = int((s0 - 0.25) * SR), int((s0 + 0.25) * SR)
        mix[a:b] += 0.10 * soft[a:b] * np.sin(np.linspace(0, np.pi, b - a)) ** 2
        if isinstance(shot, RD.Chapter) or type(shot).__name__ in ("Anim",):
            k = int(s0 * SR)
            LL = min(int(2.2 * SR), n - k)
            tt = np.arange(LL) / SR
            mix[k:k + LL] += 0.30 * np.sin(2 * np.pi * 44 * tt) * np.exp(-tt * 2.4)
    fade = np.clip((total - t) / 1.5, 0, 1)
    mix = np.tanh(mix * fade * 1.1) * 0.9
    wav = os.path.join(parts, "final_raw.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(parts, "opening.mp4"), "-an", "-c", "copy",
                    os.path.join(parts, "opening_v.mp4")], check=True)
    lst = os.path.join(parts, "list.txt")
    with open(lst, "w") as f:
        for name in ["opening_v.mp4"] + [f"part_{i:02d}.mp4" for i in range(4)]:
            f.write(f"file '{os.path.join(parts, name)}'\n")
    video = os.path.join(parts, "video_concat.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-an", "-c", "copy", video], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", out], check=True)
    print("done", out)


if __name__ == "__main__":
    main()
