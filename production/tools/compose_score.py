"""Original restrained underscore (composed for this film; no third-party material).
A minor, 56 BPM, slow harmonic rhythm. Strings pad + cello pedal + sparse piano motif.
Sections build gently and thin out at the end. Output: MIDI for FluidSynth."""
import mido, sys
BPM = 56; TPB = 480
mid = mido.MidiFile(ticks_per_beat=TPB)
def track(ch, prog, name, vol=100, pan=64):
    t = mido.MidiTrack(); mid.tracks.append(t)
    t.append(mido.MetaMessage('track_name', name=name))
    t.append(mido.Message('program_change', channel=ch, program=prog))
    t.append(mido.Message('control_change', channel=ch, control=7, value=vol))
    t.append(mido.Message('control_change', channel=ch, control=10, value=pan))
    t.append(mido.Message('control_change', channel=ch, control=91, value=90))  # reverb send
    return t
tempo = mido.MidiTrack(); mid.tracks.insert(0, tempo); tempo.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
strings = track(0, 49, 'strings', 88, 54)    # GM 50: String Ensemble 2 (slow attack)
cello = track(1, 42, 'cello', 80, 74)        # GM 43: Cello
piano = track(2, 0, 'piano', 70, 64)         # GM 1: Acoustic Grand
horn = track(3, 60, 'horn', 52, 40)          # GM 61: French Horn (very sparse)

# chord progression, 2 bars (8 beats) each: (bass, voicing)
A, F, C, G, E, D = 45, 41, 48, 43, 40, 38
prog_a = [(A, [57, 60, 64]), (F, [57, 60, 65]), (C, [55, 60, 64]), (E, [56, 59, 64])]           # Am F C E
prog_b = [(D, [57, 62, 65]), (A, [57, 60, 64]), (F, [57, 60, 65]), (E, [56, 59, 64])]           # Dm Am F E
motif = [(76, 2), (74, 1), (72, 1), (71, 3), (69, 1)]   # 8 beats, descending sigh (original)
motif2 = [(72, 2), (71, 1), (69, 1), (68, 3), (64, 1)]

events = {k: [] for k in ('s', 'c', 'p', 'h')}   # (start_beat, dur_beats, note, vel)
beat = 0
plan = ['intro'] * 2 + ['a'] * 4 + ['b'] * 2 + ['a'] * 4 + ['b'] * 2 + ['a'] * 4 + ['b'] * 2 + ['a'] * 2 + ['outro'] * 2
# each plan item = one 4-chord cycle = 32 beats (~34 s at 56 BPM); ~24 cycles ≈ 13.7 min (trimmed in the mix)
for i, sec in enumerate(plan):
    pr = prog_b if sec == 'b' else prog_a
    for j, (bass, chord) in enumerate(pr):
        b0 = beat + j * 8
        sv = 34 if sec in ('intro', 'outro') else 46
        for n in chord: events['s'].append((b0, 8, n, sv))
        if sec != 'intro': events['c'].append((b0, 8, bass, 50))
        if sec in ('a', 'b') and (i % 2 == 0 or j % 2 == 0):
            m = motif if (j % 2 == 0) else motif2
            t = b0
            for n, d in m:
                events['p'].append((t, d, n, 40 if sec == 'a' else 44)); t += d
        if sec == 'b' and j == 0: events['h'].append((b0, 8, bass + 24, 38))
    beat += 32

def write(track, ch, evs):
    msgs = []
    for st, du, n, v in evs:
        msgs.append((int(st * TPB), 'on', n, v)); msgs.append((int((st + du) * TPB) - 10, 'off', n, 0))
    msgs.sort(key=lambda m: (m[0], m[1] == 'on'))
    last = 0
    for tk, kind, n, v in msgs:
        track.append(mido.Message('note_on' if kind == 'on' else 'note_off', channel=ch, note=n, velocity=v, time=tk - last)); last = tk
write(strings, 0, events['s']); write(cello, 1, events['c']); write(piano, 2, events['p']); write(horn, 3, events['h'])
mid.save(sys.argv[1]); print('saved', sys.argv[1], f'{beat / BPM * 60:.0f} s')
