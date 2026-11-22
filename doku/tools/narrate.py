"""Generate narration WAVs per section from NARRATION.md with Kokoro (ONNX).

python3 narrate.py <model.onnx> <voices.npz> <voice> <out_dir> [speed]
Writes <out_dir>/<nn>_<slug>.wav and <out_dir>/timing.json (durations).
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def sections():
    text = open(os.path.join(ROOT, "NARRATION.md")).read()
    text = text.split("---", 1)[1].rsplit("---", 1)[0]
    out = []
    for block in re.split(r"\n## ", text)[1:]:
        title, body = block.split("\n", 1)
        body = re.sub(r"\*\(interpretation\)\*", "", body)
        body = re.sub(r"\s+", " ", body).strip()
        out.append((title.strip(), body))
    return out


def main():
    model, voices, voice, out_dir = sys.argv[1:5]
    speed = float(sys.argv[5]) if len(sys.argv) > 5 else 0.92
    lang = "en-gb" if voice.startswith("b") else "en-us"
    os.makedirs(out_dir, exist_ok=True)
    k = Kokoro(model, voices)
    timing = []
    for i, (title, body) in enumerate(sections()):
        paras = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", body) if p]
        chunks, sr = [], 24000
        for p in paras:
            a, sr = k.create(p, voice=voice, speed=speed, lang=lang)
            chunks.append(a)
            chunks.append(np.zeros(int(sr * 0.28), np.float32))
        audio = np.concatenate(chunks)
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
        path = os.path.join(out_dir, f"{i:02d}_{slug}.wav")
        sf.write(path, audio, sr)
        timing.append({"section": title, "file": os.path.basename(path), "seconds": round(len(audio) / sr, 2)})
        print(timing[-1], flush=True)
    json.dump(timing, open(os.path.join(out_dir, "timing.json"), "w"), indent=1)
    print("total", round(sum(t["seconds"] for t in timing), 1))


if __name__ == "__main__":
    main()
