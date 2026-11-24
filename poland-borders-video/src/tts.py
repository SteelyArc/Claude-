import json, os, wave
from piper import PiperVoice, SynthesisConfig
from script import SCENES, tts_text

HERE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(HERE, '..', 'build', 'vo')
os.makedirs(VO, exist_ok=True)
voice = PiperVoice.load(os.path.join(HERE, '..', 'voice', 'en_US-ryan-high.onnx'))
cfg = SynthesisConfig(length_scale=0.93, noise_scale=0.6, noise_w_scale=0.75)
meta = []
for si, sc in enumerate(SCENES):
    for li, (cap, ev) in enumerate(sc['lines']):
        p = os.path.join(VO, f'{si:02d}_{li:02d}.wav')
        with wave.open(p, 'wb') as w:
            voice.synthesize_wav(tts_text(cap), w, syn_config=cfg)
        with wave.open(p) as w:
            dur = w.getnframes() / w.getframerate()
            sr = w.getframerate()
        meta.append(dict(scene=si, line=li, path=p, dur=dur, sr=sr))
        print(si, li, round(dur, 2), tts_text(cap))
json.dump(meta, open(os.path.join(VO, 'meta.json'), 'w'), indent=1)
print('total', round(sum(m['dur'] for m in meta), 1))
