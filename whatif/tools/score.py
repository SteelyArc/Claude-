"""Original score for the film (composed here; no third-party material).
Tempo 60 BPM so 1 beat = 1 second: every section is placed on narration cue times (tools/cues.py).
Palette (General MIDI, rendered by FluidSynth with FluidR3_GM, MIT licence): string ensembles, cello/contrabass,
harp, piano, horn, choir, timpani, pizzicato. Output: render/score.mid -> render/score.wav"""
import os, sys, subprocess, mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cues import cue as C, ROOT

TPB = 480
mid = mido.MidiFile(ticks_per_beat=TPB)
tempo = mido.MidiTrack(); mid.tracks.append(tempo); tempo.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(60)))
EV = {}   # channel -> list of (time_s, msg)
CH = {}


def inst(name, ch, prog, vol=100, pan=64, rev=100, cho=20):
    CH[name] = ch; EV[ch] = [(0, mido.Message('program_change', channel=ch, program=prog))]
    for cc, v in ((7, vol), (10, pan), (91, rev), (93, cho)): EV[ch].append((0, mido.Message('control_change', channel=ch, control=cc, value=v)))


inst('str', 0, 49, 96, 50); inst('str2', 1, 48, 84, 78); inst('cello', 2, 42, 92, 70); inst('bass', 3, 43, 88, 64)
inst('harp', 4, 46, 80, 40, 110); inst('piano', 5, 0, 78, 60, 105); inst('horn', 6, 60, 82, 44, 110); inst('choir', 7, 52, 80, 64, 120)
inst('pizz', 8, 45, 78, 80); inst('trem', 10, 44, 70, 58)
TIMP = 11; EV[TIMP] = [(0, mido.Message('program_change', channel=TIMP, program=47))] + [(0, mido.Message('control_change', channel=TIMP, control=c_, value=v)) for c_, v in ((7, 110), (91, 90))]
CH['timp'] = TIMP


def note(name, t, dur, n, vel=60):
    ch = CH[name]
    EV[ch].append((t, mido.Message('note_on', channel=ch, note=n, velocity=int(max(1, min(127, vel))))))
    EV[ch].append((t + dur, mido.Message('note_off', channel=ch, note=n, velocity=0)))


def chord(name, t, dur, notes, vel=50):
    for n in notes: note(name, t, dur, n, vel)


def expr(name, t0, t1, v0, v1, steps=24):
    """CC11 expression ramp (swells / fades)."""
    ch = CH[name]
    for i in range(steps + 1):
        EV[ch].append((t0 + (t1 - t0) * i / steps, mido.Message('control_change', channel=ch, control=11, value=int(v0 + (v1 - v0) * i / steps))))


# pitches
D2, A2, F2, G2, Bb1, C2, E2 = 38, 45, 41, 43, 34, 36, 40
def tri(root, minor=False):   # close voicing around middle register
    third = 3 if minor else 4
    return [root, root + third, root + 7]

Dm = [50, 53, 57]; Dmaj = [50, 54, 57]; Bb = [46, 50, 53]; F = [48, 53, 57]; C_ = [48, 52, 55]; Gm = [50, 55, 58]
Am = [52, 57, 60]; A = [49, 52, 57]; G = [50, 55, 59]; Bm = [50, 54, 59]; Em = [52, 55, 59]


def pads(t0, t1, prog, step=4.0, vel=46, inst_='str', bass=True, octave_up=False):
    t = t0; i = 0
    while t < t1 - 0.5:
        root, ch_ = prog[i % len(prog)]
        d = min(step, t1 - t)
        chord(inst_, t, d + 0.15, [n + (12 if octave_up else 0) for n in ch_], vel)
        if bass: note('bass', t, d + 0.1, root, vel + 6); note('cello', t, d + 0.1, root + 12, vel - 6)
        t += step; i += 1


def arps(t0, t1, prog, step=4.0, rate=0.5, inst_='harp', vel=44, up=12):
    t = t0; i = 0
    while t < t1 - 0.3:
        root, ch_ = prog[i % len(prog)]
        seq = [ch_[0] + up, ch_[1] + up, ch_[2] + up, ch_[1] + up + 12, ch_[2] + up, ch_[1] + up]
        k = 0; tt = t
        while tt < min(t + step, t1) - 0.05:
            note(inst_, tt, rate * 2.2, seq[k % len(seq)], vel - 6 * (k % 2)); tt += rate; k += 1
        t += step; i += 1


def melody(t0, notes, inst_='piano', vel=56, transpose=0):
    t = t0
    for n, d in notes:
        if n: note(inst_, t, d * 1.05, n + transpose, vel)
        t += d
    return t


# original motifs (D minor sigh; rising hope)
SIGH = [(69, 1), (74, 1), (72, 0.5), (70, 0.5), (69, 2), (65, 1), (67, 1), (69, 2)]
HOPE = [(62, 1), (66, 1), (69, 1), (74, 2), (73, 0.5), (71, 0.5), (69, 2), (66, 1), (69, 1), (74, 3)]
FINAL = [(74, 1.5), (76, 0.5), (78, 1), (81, 2), (79, 1), (78, 1), (76, 2), (74, 3)]

PROG_DOC = [(D2, Dm), (Bb1, Bb), (F2, F), (C2 + 12, C_)]
PROG_DOC2 = [(G2, Gm), (D2, Dm), (A2, A), (D2, Dm)]
PROG_HOPE = [(F2, F), (Bb1, Bb), (D2, Dm), (C2 + 12, C_)]
PROG_ALT = [(D2, Dmaj), (Bb1 + 12, Bm), (G2, G), (A2, A)]
PROG_19 = [(G2, G), (D2, Dmaj), (E2 + 12, Em), (A2, A)]

# ---------------- 1 hook (0 - 6.2): pedal, swell, timpani
T = C('imagine')
note('bass', 0.0, T + 0.4, D2 - 12 + 12, 70); note('cello', 0.0, T + 0.4, D2, 62)
chord('trem', 0.2, T, [62, 69, 74], 40); expr('trem', 0, T, 30, 110)
for i, tt in enumerate((0.05, 2.5, 3.9)): note('timp', tt, 1.5, 38, 90 - i * 10)
chord('choir', C('empire') - 0.4, T - C('empire') + 0.8, [62, 65, 69], 46); expr('choir', C('empire') - 0.4, T, 40, 100)
# ---------------- 2 imagine (hyp, warm major)
t0, t1 = C('imagine'), C('in our timeline')
expr('str', t0, t0 + 2, 50, 100); pads(t0, t1, PROG_ALT, 3.8, 44); arps(t0 + 0.3, t1, PROG_ALT, 3.8, 0.38, 'harp', 46)
chord('horn', C('warsaw') - 0.2, 3.2, [62, 66, 69], 44)
# ---------------- 3 in our timeline (minor) and rewind
t0, t1 = C('in our timeline'), C('1791')
pads(t0, t1, [(D2, Dm), (Bb1, Bb), (G2, Gm), (A2, A)], 3.0, 48)
for tt in (C('disappeared') - 0.1,): note('timp', tt, 2.0, 38, 100)
expr('str', C('alternative world') - 0.6, C('1791'), 100, 50)
# ---------------- 4 documented history (34 - 67): main theme
t0, t1 = C('1791'), C('then came')
expr('str', t0, t0 + 2, 50, 96)
pads(t0, t1, PROG_DOC + PROG_DOC2, 4.0, 44)
melody(C('once one') - 0.3, SIGH, 'piano', 52); melody(C('peoples') + 1.0, SIGH, 'piano', 46, -5)
melody(C('dangerously weak') + 0.5, SIGH, 'cello', 58, -12)
for i in range(16):   # quiet pizzicato pulse as the neighbours grow stronger
    tt = C('neighboring monarchies') + i * 0.5
    if tt < t1 - 0.2: note('pizz', tt, 0.4, (38, 45, 41, 45)[i % 4] + 12, 46 + i)
note('timp', C('opportunities') + 0.9, 1.6, 38, 96)
# ---------------- 5 constitution (hope)
t0, t1 = C('then came'), C('alarmed')
expr('str', t0, C('3rd'), 60, 112)
pads(t0, t1, PROG_HOPE, 4.0, 50); arps(C('3rd'), t1, PROG_HOPE, 4.0, 0.5, 'harp', 42)
melody(C('3rd') + 0.2, HOPE, 'horn', 62, -2); chord('choir', C('3rd'), 6.0, [65, 69, 72], 48)
melody(C('brief moment') - 0.4, HOPE[:6], 'piano', 50, -2)
# ---------------- 6 intervention & partitions (tension)
t0, t1 = C('alarmed'), C('commonwealth disappeared')
pads(t0, t1, [(D2, Dm), (Bb1, Bb), (G2, Gm), (A2, A)], 4.0, 42)
k = 0; tt = C('intervened') - 0.5
while tt < t1:
    note('pizz', tt, 0.25, (38, 38, 45, 41)[k % 4] + 12, 58 + (k % 4 == 0) * 14); tt += 0.5; k += 1
chord('trem', C('intervened'), t1 - C('intervened'), [62, 65, 70], 36); expr('trem', C('intervened'), t1, 40, 112)
for w0 in ('intervened', 'second partition', 'third partition'):
    note('timp', C(w0) + 0.9, 2.0, 38, 112); note('bass', C(w0) + 0.9, 2.2, D2 - 12 + 12, 80)
expr('str', t1 - 0.6, t1 + 0.3, 110, 0); expr('trem', t1 - 0.4, t1 + 0.2, 112, 0)
# ---------------- 7 silence: 'The Commonwealth disappeared.' (no music until 'imagine a different')
# ---------------- 8 alternative (warm major, rising)
t0, t1 = C('imagine a different'), C('threat')
for nm in ('str', 'trem'): expr(nm, t0 - 0.1, t0 + 0.1, 0, 90)
expr('str', t0, t0 + 3, 40, 100)
pads(t0, t1, PROG_ALT, 4.0, 46); arps(C('may constitution') - 0.2, t1, PROG_ALT, 4.0, 0.33, 'harp', 46)
chord('choir', C('may constitution') - 0.2, 6, [62, 66, 69], 50); melody(C('move') + 0.4, HOPE, 'horn', 56)
t0, t1 = C('threat'), C('crisis')
pads(t0, t1, [(D2, Dm), (Bb1, Bb), (G2, Gm), (A2, A)], 3.0, 46)
for i in range(int((t1 - t0) / 0.5)): note('pizz', t0 + i * 0.5, 0.3, (38, 45)[i % 2] + 12, 54)
note('timp', C('far more costly') + 0.5, 1.4, 38, 100); chord('horn', C('far more costly') + 0.6, 2.5, [62, 66, 69], 66)
t0, t1 = C('crisis'), C('19th century')
pads(t0, t1, PROG_ALT, 4.0, 50); arps(t0, t1, PROG_ALT, 4.0, 0.33, 'harp', 44)
for w0 in ('second partition never', 'no third'):
    chord('horn', C(w0) + 0.9, 2.2, [62, 66, 69, 74], 70); note('timp', C(w0) + 0.9, 1.4, 38, 92)
chord('choir', C('remains on the map') - 0.2, 4.2, [62, 66, 69, 74], 64); expr('choir', C('remains on the map') - 0.2, C('remains on the map') + 4, 60, 120)
melody(C('remains on the map') - 0.3, FINAL[:5], 'horn', 70)
# ---------------- 9 19th century (flowing)
t0, t1 = C('19th century'), C('stand still')
pads(t0, t1, PROG_19, 4.0, 42); arps(t0, t1, PROG_19, 4.0, 0.25, 'piano', 38, 12)
melody(C('greatest challenge') + 0.2, HOPE, 'cello', 54, -12)
melody(C('bridge') + 0.2, HOPE, 'horn', 52)
# ---------------- 10 Europe would not stand still (motion, modal)
t0, t1 = C('stand still'), C('first world war')
pads(t0, t1, [(D2, Dm), (C2 + 12, C_), (Bb1, Bb), (A2, A)], 4.0, 48)
k = 0; tt = t0
while tt < t1 - 0.4:
    note('pizz', tt, 0.25, (38, 45, 41, 45, 36, 43, 34, 45)[k % 8] + 12, 56); tt += 0.5; k += 1
for w0 in ('napoleon', 'revolutions', 'balance', 'radically different'): note('timp', C(w0) - 0.05, 1.2, 38, 90)
expr('str', C('radically different') - 2, t1, 90, 120)
# ---------------- 11 questions (sparse, suspended)
t0, t1 = C('first world war'), C('what we do know')
chord('str', t0, t1 - t0, [69, 74, 76], 32); expr('str', t0, t0 + 1, 120, 70); expr('str', C('cannot know') - 0.5, C('cannot know') + 1, 70, 40)
for i, w0 in enumerate(('first world war', 'germany and russia', 'borders of modern', 'cannot know', 'one possible path')):
    note('piano', C(w0) - 0.1, 3.0, (74, 72, 69, 62, 66)[i], 46)
# ---------------- 12 documented reprise
t0, t1 = C('what we do know'), C('destroy it') + 0.6
expr('str', t0, t0 + 1.5, 40, 96)
pads(t0, t1, PROG_DOC2 + PROG_DOC, 3.2, 46); melody(t0 + 0.4, SIGH, 'cello', 60, -12)
for w0 in ('political weakness', 'foreign intervention', 'ambitions'): note('timp', C(w0) - 0.05, 1.0, 38, 84)
expr('str', t1 - 0.5, t1 + 0.2, 96, 0)
# ---------------- 13 imagine today -> final
t0 = C('imagine looking')
expr('str', t0, t0 + 0.2, 0, 70); expr('str', t0, C('a different world'), 70, 120)
pads(t0, 297.6, PROG_ALT, 3.0, 50); arps(t0 + 1.5, 297.6, PROG_ALT, 3.0, 0.25, 'harp', 48)
chord('choir', C('still there') - 0.3, 10, [62, 66, 69], 56); expr('choir', C('still there'), C('a different world') + 2, 70, 118)
melody(C('still there') - 0.2, FINAL, 'horn', 72)
chord('str', 297.6, 3.0, [50, 54, 57, 62, 66, 69], 60); note('bass', 297.6, 3.0, D2, 70); note('timp', 297.6, 2.0, 38, 90)
chord('choir', 297.6, 3.0, [62, 66, 69, 74], 60); expr('str', 297.6, 300.0, 110, 0); expr('choir', 297.6, 300.0, 110, 0)

# ---------------- write
for ch, evs in sorted(EV.items()):
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    evs.sort(key=lambda e: (e[0], 0 if e[1].type in ('program_change', 'control_change') else (1 if e[1].type == 'note_off' else 2)))
    last = 0
    for t, m in evs:
        tick = int(round(t * TPB)); m.time = max(0, tick - last); last = max(last, tick); tr.append(m)
os.makedirs(f'{ROOT}/render', exist_ok=True)
mid.save(f'{ROOT}/render/score.mid')
raw = f'{ROOT}/render/score_raw.wav'
subprocess.run(['fluidsynth', '-ni', '-g', '0.55', '-r', '48000', '-R', '1', '-C', '1',
                '-o', 'synth.reverb.room-size=0.86', '-o', 'synth.reverb.damp=0.3', '-o', 'synth.reverb.level=0.8', '-o', 'synth.reverb.width=1.0',
                '-F', raw, '/usr/share/sounds/sf2/FluidR3_GM.sf2', f'{ROOT}/render/score.mid'], check=True, capture_output=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', 'highpass=f=35,lowpass=f=9000,aecho=0.8:0.55:90|210:0.18|0.10,atrim=0:300,apad=whole_dur=300',
                '-ar', '48000', '-ac', '2', f'{ROOT}/render/score.wav'], check=True)
# silence envelopes (dramatic beats): music cut completely
import numpy as np
from scipy.io import wavfile
sr, x = wavfile.read(f'{ROOT}/render/score.wav'); x = x.astype(np.float32) / (32768.0 if x.dtype == np.int16 else 1.0)
tv = np.arange(len(x)) / sr; g = np.ones(len(x), np.float32)
for a, b in ((C('commonwealth disappeared') + 0.15, C('imagine a different') - 0.05), (C('destroy it') + 0.55, C('imagine looking') - 0.05)):
    fade_out = np.clip((a + 0.55 - tv) / 0.55, 0, 1); fade_in = np.clip((tv - b) / 0.05, 0, 1)
    g *= np.where(tv < a, 1.0, np.where(tv < b, fade_out, fade_in))
wavfile.write(f'{ROOT}/render/score.wav', sr, (x * g[:, None]).astype(np.float32))
print('score written')
