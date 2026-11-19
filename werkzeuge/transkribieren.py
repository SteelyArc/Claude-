"""Transkribiert die Sprecheraufnahme eines Projekts mit Wort-Zeitstempeln (faster-whisper).

Aufruf:  python3 werkzeuge/transkribieren.py projekte/<name> [modell]
Ergebnis: projekte/<name>/ausgabe/transkript.json und transkript.txt (Satz je Zeile mit Startzeit).
Die Aufnahme wird dabei nicht verändert.
"""

import json
import sys
from pathlib import Path

import subprocess

import numpy as np
from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zeitspuren import audio  # noqa: E402

projekt = Path(sys.argv[1])
modell = sys.argv[2] if len(sys.argv) > 2 else "medium"
datei = audio.finden(projekt)
m = WhisperModel(modell, device="cpu", compute_type="int8", cpu_threads=4)
# Ton per FFmpeg als 16-kHz-Mono einlesen (nur für die Erkennung; die Datei bleibt unverändert)
roh = subprocess.run(["ffmpeg", "-v", "error", "-i", str(datei), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True, check=True).stdout
ton = np.frombuffer(roh, dtype=np.float32)
segmente, info = m.transcribe(ton, language=(sys.argv[3] if len(sys.argv) > 3 else None), word_timestamps=True, beam_size=5,
                              vad_filter=False, condition_on_previous_text=True)
woerter, saetze, aktuell = [], [], []
for seg in segmente:
    for w in seg.words:
        woerter.append({"wort": w.word.strip(), "von": round(w.start, 2), "bis": round(w.end, 2)})
        aktuell.append(woerter[-1])
        if w.word.strip().endswith((".", "!", "?")):
            saetze.append({"von": aktuell[0]["von"], "bis": aktuell[-1]["bis"],
                           "text": " ".join(x["wort"] for x in aktuell)})
            aktuell = []
if aktuell:
    saetze.append({"von": aktuell[0]["von"], "bis": aktuell[-1]["bis"], "text": " ".join(x["wort"] for x in aktuell)})
ziel = projekt / "ausgabe"
ziel.mkdir(exist_ok=True)
(ziel / "transkript.json").write_text(json.dumps({"modell": modell, "dauer": info.duration, "saetze": saetze,
                                                  "woerter": woerter}, ensure_ascii=False, indent=1), encoding="utf-8")
with open(ziel / "transkript.txt", "w", encoding="utf-8") as fh:
    for s in saetze:
        m_, sek = divmod(s["von"], 60)
        fh.write(f"{int(m_)}:{sek:05.2f}  {s['text']}\n")
print(f"{len(saetze)} Sätze, {len(woerter)} Wörter, Dauer {info.duration:.1f} s")
