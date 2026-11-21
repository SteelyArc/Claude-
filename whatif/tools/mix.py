"""Final audio mix. The narration is passed through UNCHANGED (no gain, EQ, compression, speed or pitch change);
music and sound design are shaped and sidechain-ducked under it. Output: render/mix.wav (48 kHz stereo, 300 s)."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import ROOT

MUSIC_GAIN, SFX_GAIN = 2.0, 0.55
fc = ("[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur=300,asplit=3[voice][k1][k2];"
      f"[1:a]aresample=48000,volume={MUSIC_GAIN}[m];[m][k1]sidechaincompress=threshold=0.012:ratio=5:attack=40:release=500:knee=4[md];"
      f"[2:a]aresample=48000,volume={SFX_GAIN}[s];[s][k2]sidechaincompress=threshold=0.02:ratio=2.2:attack=15:release=300[sd];"
      "[voice][md][sd]amix=inputs=3:normalize=0:duration=longest,atrim=0:300[out]")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{ROOT}/audio/narration_original.mp3', '-i', f'{ROOT}/render/score.wav',
                '-i', f'{ROOT}/render/sfx.wav', '-filter_complex', fc, '-map', '[out]', '-c:a', 'pcm_f32le', f'{ROOT}/render/mix.wav'], check=True)
print('mix written')
