"""Word-level transcript of the untouched narration (faster-whisper medium.en)."""
import json, subprocess, numpy as np
from faster_whisper import WhisperModel
m = WhisperModel('medium.en', device='cpu', compute_type='int8')
segs, _ = m.transcribe(np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i','audio/narration_original.mp3','-ac','1','-ar','16000','-f','f32le','-'],capture_output=True).stdout,np.float32), word_timestamps=True, beam_size=5, language='en')
out = []
for s in segs:
    out.append({'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(),
                'words': [{'w': w.word, 's': round(w.start, 2), 'e': round(w.end, 2)} for w in s.words]})
    print(f"{s.start:7.2f} {s.text.strip()}", flush=True)
json.dump(out, open('research/transcript_words.json', 'w'), indent=1, ensure_ascii=False)
