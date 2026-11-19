"""Analyse und schonende Aufbereitung der Sprecherdatei.

Grundsatz: Die Stimme wird weder beschleunigt noch verlangsamt und nicht
komprimiert. Es wird ausschließlich die Gesamtlautstärke angepasst
(eine einzige, gleichbleibende Verstärkung) – so klingt sie natürlich.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

AUDIO_ENDUNGEN = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma", ".aiff", ".aif"}

ZIEL_LUFS = -14.0  # übliche Lautheit für TikTok / Social Media
MAX_SPITZE_DBTP = -1.5  # Sicherheitsabstand gegen Übersteuerung


class AudioFehler(RuntimeError):
    pass


@dataclass
class AudioInfo:
    pfad: Path
    kanaele: int
    dauer: float
    lautheit_lufs: float
    spitze_dbtp: float
    verstaerkung_db: float


def finden(projektordner: Path) -> Path:
    kandidaten = sorted(
        p for p in projektordner.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_ENDUNGEN and not p.name.startswith(".")
    )
    if not kandidaten:
        raise AudioFehler(
            f"Im Ordner '{projektordner.name}' wurde keine Sprecherdatei gefunden "
            f"(erlaubt: {', '.join(sorted(AUDIO_ENDUNGEN))})."
        )
    if len(kandidaten) > 1:
        bevorzugt = [p for p in kandidaten if p.stem.lower() in {"sprecher", "sprache", "stimme", "voice"}]
        if len(bevorzugt) == 1:
            return bevorzugt[0]
        namen = ", ".join(p.name for p in kandidaten)
        raise AudioFehler(
            f"Mehrere Audiodateien gefunden ({namen}). Bitte die Sprecherdatei 'sprecher' nennen "
            f"(z. B. sprecher.mp3) oder die anderen entfernen."
        )
    return kandidaten[0]


def kanaele_messen(pfad: Path) -> int:
    erg = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels",
         "-of", "default=nw=1:nk=1", str(pfad)],
        capture_output=True, text=True,
    )
    try:
        return int(erg.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        raise AudioFehler(f"Die Audiodatei '{pfad.name}' enthält keine lesbare Tonspur.") from None


def _stereo_filter(kanaele: int) -> str:
    # Mono-Aufnahmen werden unverändert auf beide Lautsprecher gelegt.
    if kanaele == 1:
        return "pan=stereo|c0=c0|c1=c0"
    return "aformat=channel_layouts=stereo"


def dauer_messen(pfad: Path) -> float:
    erg = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(pfad)],
        capture_output=True, text=True,
    )
    try:
        return float(erg.stdout.strip())
    except ValueError:
        raise AudioFehler(f"Die Audiodatei '{pfad.name}' konnte nicht gelesen werden.") from None


def analysieren(pfad: Path) -> AudioInfo:
    dauer = dauer_messen(pfad)
    kanaele = kanaele_messen(pfad)
    if dauer < 3:
        raise AudioFehler(f"Die Audiodatei ist nur {dauer:.1f} Sekunden lang.")

    erg = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(pfad), "-vn",
         "-af", f"{_stereo_filter(kanaele)},loudnorm=I={ZIEL_LUFS}:TP={MAX_SPITZE_DBTP}:LRA=20:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    treffer = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", erg.stderr, re.S)
    if not treffer:
        raise AudioFehler("Die Lautstärke der Audiodatei konnte nicht gemessen werden.")
    werte = json.loads(treffer.group(0))
    lufs = float(werte["input_i"])
    spitze = float(werte["input_tp"])

    # Eine feste Verstärkung: auf Ziellautheit, aber nie über die Spitzengrenze.
    verstaerkung = ZIEL_LUFS - lufs
    verstaerkung = min(verstaerkung, MAX_SPITZE_DBTP - spitze)
    verstaerkung = max(min(verstaerkung, 20.0), -20.0)
    return AudioInfo(pfad, kanaele, dauer, lufs, spitze, verstaerkung)


def filterkette(info: AudioInfo, vorlauf: float, gesamt: float) -> str:
    """FFmpeg-Audiofilter: Lautstärke, Vorlauf (Stille), exakte Gesamtlänge.

    Kein Tempo-, Tonhöhen- oder Dynamikeingriff.
    """
    ms = int(round(vorlauf * 1000))
    return (
        f"asetpts=N/SR/TB,"
        f"{_stereo_filter(info.kanaele)},"
        f"aresample=48000:resampler=soxr,"
        f"volume={info.verstaerkung_db:.2f}dB,"
        f"aformat=sample_fmts=fltp,"
        f"adelay={ms}:all=1,"
        f"apad=whole_dur={gesamt:.6f},asetpts=N/SR/TB"
    )
