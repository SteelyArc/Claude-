"""Music bed + final mux.
music: CC0 MIDI transcription of Ogiński's polonaise 'Farewell to the Homeland' (composition public domain),
rendered with FluidSynth + FluidR3_GM soundfont (MIT licence).
The narration is passed through UNCHANGED (no gain, EQ or normalisation); only the music is shaped and ducked.

usage:
  music_mix.py render  MIDI OUT.wav
  music_mix.py mux     VIDEO.mp4 NARRATION.mp3 MUSIC.wav OUT.mp4 [--ss A0 --to A1] [--music-offset S]
"""
import sys, subprocess, os

SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'

def run(cmd):
    print(' '.join(cmd)); subprocess.run(cmd, check=True)

def render(midi, out):
    raw = out.replace('.wav', '_raw.wav')
    run(['fluidsynth', '-ni', '-g', '0.6', '-r', '44100', '-R', '1', '-C', '0',
         '-o', 'synth.reverb.room-size=0.82', '-o', 'synth.reverb.damp=0.35', '-o', 'synth.reverb.level=0.75', '-o', 'synth.reverb.width=0.9',
         '-F', raw, SF2, midi])
    # soften: gentle low-pass, warm low shelf cut, slow hall echo, normalise the MUSIC ONLY to a quiet bed level
    run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af',
         'lowpass=f=5200,highpass=f=70,aecho=0.8:0.6:120|260:0.22|0.14,loudnorm=I=-30:TP=-6:LRA=9', '-ar', '44100', '-ac', '2', out])

def mux(video, narr, music, out, ss=None, to=None, music_offset=0.0, full=None):
    nin = ['-ss', str(ss), '-to', str(to)] if ss is not None else []
    dur = (to - ss) if ss is not None else full
    fade_out = f',afade=t=out:st={dur - 2.0:.2f}:d=2.0' if dur else ''
    pad = f",apad=whole_dur={full}" if full else ""
    fc = (f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo{pad},asplit=2[voice][sc];"
          f"[2:a]atrim=start={music_offset},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
          f"afade=t=in:st=0:d=1.5{fade_out}[mus];"
          f"[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=60:release=700:makeup=1[ducked];"
          f"[voice][ducked]amix=inputs=2:duration=first:normalize=0:weights=1 1[a]")
    run(['ffmpeg', '-v', 'error', '-y', '-i', video, *nin, '-i', narr, '-stream_loop', '-1', '-i', music,
         '-filter_complex', fc, '-map', '0:v', '-map', '[a]',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-maxrate', '6500k', '-bufsize', '13000k', '-pix_fmt', 'yuv420p',
         '-profile:v', 'high', '-r', '30', '-c:a', 'aac', '-b:a', '192k', *(['-t', str(full)] if full else ['-shortest']), '-movflags', '+faststart', out])

if __name__ == '__main__':
    if sys.argv[1] == 'render':
        render(sys.argv[2], sys.argv[3])
    else:
        a = sys.argv[2:]; kw = {}
        if '--ss' in a: kw['ss'] = float(a[a.index('--ss') + 1]); kw['to'] = float(a[a.index('--to') + 1])
        if '--full' in a: kw['full'] = float(a[a.index('--full') + 1])
        if '--music-offset' in a: kw['music_offset'] = float(a[a.index('--music-offset') + 1])
        mux(a[0], a[1], a[2], a[3], **kw)
