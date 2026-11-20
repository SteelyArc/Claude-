from faster_whisper import WhisperModel
import json
m = WhisperModel("small.en", device="cpu", compute_type="int8")
import numpy as np
audio=np.fromfile("narr16k.f32",dtype=np.float32)
segs, info = m.transcribe(audio, word_timestamps=True)
out=[]
for s in segs:
    out.append({"start":s.start,"end":s.end,"text":s.text,"words":[{"w":w.word,"s":w.start,"e":w.end} for w in s.words]})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text}", flush=True)
json.dump(out, open("/home/user/Claude-/partition1772/data/transcript.json","w"), indent=1)
