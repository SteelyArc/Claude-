import numpy as np, json
from faster_whisper import WhisperModel
a=np.fromfile('narr16k.f32',dtype=np.float32)
m=WhisperModel('medium.en',device='cpu',compute_type='int8',cpu_threads=2)
segs,_=m.transcribe(a,word_timestamps=True,beam_size=5)
out=[]
for s in segs:
    out.append({"start":s.start,"end":s.end,"text":s.text,"words":[{"w":w.word,"s":w.start,"e":w.end} for w in s.words]})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text}", flush=True)
json.dump(out,open('../data/transcript_medium.json','w'),indent=1)
