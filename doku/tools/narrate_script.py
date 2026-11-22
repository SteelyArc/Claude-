"""Narrate SCRIPT_FINAL.txt with Kokoro (ONNX), turning stage directions into pacing.

python3 narrate_script.py <model.onnx> <voices.npz> <voice> <out.wav> <timing.json> [base_speed]

Stage directions cannot change the voice's emotion; they control tempo and pauses:
  slow / grave / dramatic / somber / deliberate -> slower; intense / tense -> slightly faster
  [short pause] 0.7 s, [dramatic pause] 1.0 s, [long pause] 1.6 s, '---' section break 1.3 s
Timing JSON lists every spoken line with start/end seconds and section index (for picture sync).
"""
import json
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

PAUSES = {"short pause": 0.7, "dramatic pause": 1.0, "long pause": 1.6}
LINE_GAP = float(__import__("os").environ.get("LINE_GAP", "0.42"))


def speed_for(tag, base):
    t = tag.lower()
    s = base
    if any(k in t for k in ("slow", "somber", "reflective")):
        s -= 0.08
    elif any(k in t for k in ("grave", "dramatic", "deliberate", "dark", "lower")):
        s -= 0.04
    if any(k in t for k in ("intense", "tense")):
        s += 0.03
    return s


def main():
    model, voices, voice, out_wav, out_json = sys.argv[1:6]
    base = float(sys.argv[6]) if len(sys.argv) > 6 else 0.95
    lang = "en-gb" if voice.startswith("b") else "en-us"
    k = Kokoro(model, voices)
    sr = 24000
    pieces, timing = [], []
    t = 0.0
    section, tag = 0, ""
    for raw in open(sys.argv[0].replace("tools/narrate_script.py", "SCRIPT_FINAL.txt") if False else
                    __import__("os").path.join(__import__("os").path.dirname(__file__), "..", "SCRIPT_FINAL.txt")):
        line = raw.strip()
        if not line:
            continue
        if line == "---":
            section += 1
            gap = float(__import__("os").environ.get("SECTION_GAP", "1.3"))
        elif line.startswith("["):
            inner = line.strip("[]").lower()
            if inner in PAUSES:
                gap = PAUSES[inner]
            else:
                tag = inner
                continue
        else:
            text = line.replace("…", "...")
            parts = [p for p in re.split(r"\.\.\.\s*", text)]
            sp = speed_for(tag, base)
            start = t
            for j, p in enumerate(parts):
                p = p.strip()
                if not p:
                    continue
                a, sr = k.create(p if j == len(parts) - 1 or p.endswith((".", "!", "?")) else p + ",",
                                 voice=voice, speed=sp, lang=lang)
                # trim leading/trailing near-silence
                nz = np.where(np.abs(a) > 0.01)[0]
                if len(nz):
                    a = a[max(0, nz[0] - 240): nz[-1] + 480]
                pieces.append(a)
                t += len(a) / sr
                if j < len(parts) - 1:
                    pieces.append(np.zeros(int(sr * 0.45), np.float32))
                    t += 0.45
            timing.append({"section": section, "tag": tag, "text": line, "start": round(start, 3), "end": round(t, 3)})
            gap = LINE_GAP
        pieces.append(np.zeros(int(sr * gap), np.float32))
        t += gap
    audio = np.concatenate(pieces)
    sf.write(out_wav, audio, sr)
    json.dump(timing, open(out_json, "w"), indent=1, ensure_ascii=False)
    print("lines", len(timing), "sections", section + 1, "duration", round(len(audio) / sr, 1))


if __name__ == "__main__":
    main()
