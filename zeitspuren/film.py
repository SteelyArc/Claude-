"""Szenen mit echtem Archivfilm (Wochenschau, Dokumentaraufnahmen …).

Grundsätze:
- Der Film läuft in seiner Originalgeschwindigkeit; er wird nur auf 30 Bilder
  pro Sekunde umgerechnet (Bilder werden wiederholt, nicht neu erfunden).
- Der Originalton des Films wird nicht verwendet – es spricht der Sprecher.
- Erlaubt sind nur Ausschnitt und Bildgröße; querformatiges Material steht
  vollständig vor einem unscharfen, abgedunkelten Hintergrund.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PIL import Image

FILM_ENDUNGEN = {".mp4", ".mov", ".mkv", ".avi", ".mpg", ".mpeg", ".m4v", ".webm", ".wmv"}


class FilmFehler(RuntimeError):
    pass


def info(pfad: Path) -> tuple[int, int, float]:
    erg = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "default=nw=1", str(pfad)],
        capture_output=True, text=True,
    )
    werte = dict(z.split("=", 1) for z in erg.stdout.split() if "=" in z)
    try:
        return int(werte["width"]), int(werte["height"]), float(werte["duration"])
    except (KeyError, ValueError):
        raise FilmFehler(f"Der Film '{pfad.name}' kann nicht gelesen werden.") from None


class Archivfilm:
    """Liefert Einzelbilder eines Filmausschnitts zu beliebigen (fortlaufenden) Zeiten."""

    PUFFER = 48

    def __init__(self, pfad: Path, ab: float, dauer: float, breite: int, hoehe: int, fps: int,
                 darstellung: str = "eingepasst"):
        self.pfad, self.ab, self.dauer = pfad, ab, dauer
        self.breite, self.hoehe, self.fps = breite, hoehe, fps
        self.darstellung = darstellung
        b, h, laenge = info(pfad)
        self.quellmasse = (b, h)
        self.verfuegbar = max(0.0, laenge - ab)
        self._lock = threading.Lock()
        self._prozess = None
        self._gestartet = False
        self._gelesen = -1  # Index des zuletzt gelesenen Bildes
        self._puffer: dict[int, bytes] = {}
        self._letztes: bytes | None = None

    @property
    def zu_kurz(self) -> bool:
        return self.verfuegbar + 0.05 < self.dauer

    def _filter(self) -> str:
        W, H = self.breite, self.hoehe
        basis = f"fps={self.fps},yadif=deint=interlaced,setsar=1"
        if self.darstellung == "ganz":
            return f"{basis},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
        kb, kh = max(2, W // 8 // 2 * 2), max(2, H // 8 // 2 * 2)
        return (
            f"{basis},split[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[vorne];"
            f"[b]scale={kb}:{kh}:force_original_aspect_ratio=increase,crop={kb}:{kh},"
            f"boxblur=6:2,scale={W}:{H},eq=brightness=-0.22:saturation=0.6[hinten];"
            f"[hinten][vorne]overlay=(W-w)/2:(H-h)/2,format=rgb24"
        )

    def _starten(self) -> None:
        self._prozess = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", f"{self.ab:.3f}", "-i", str(self.pfad),
             "-t", f"{self.dauer + 1:.3f}", "-an", "-filter_complex", self._filter(),
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def bild(self, sekunde_in_szene: float) -> Image.Image:
        index = max(0, int(sekunde_in_szene * self.fps + 1e-6))
        groesse = self.breite * self.hoehe * 3
        with self._lock:
            if not self._gestartet:
                self._gestartet = True
                self._starten()
            while self._gelesen < index and self._prozess is not None:
                daten = self._prozess.stdout.read(groesse)
                if len(daten) < groesse:  # Filmende: letztes Bild halten
                    self._prozess.stdout.close()
                    self._prozess.wait()
                    self._prozess = None
                    break
                self._gelesen += 1
                self._puffer[self._gelesen] = daten
                self._letztes = daten
                for alt in [k for k in self._puffer if k < self._gelesen - self.PUFFER]:
                    del self._puffer[alt]
            daten = self._puffer.get(index) or self._puffer.get(min(self._puffer, key=lambda k: abs(k - index))) \
                if self._puffer else self._letztes
        if daten is None:
            return Image.new("RGB", (self.breite, self.hoehe), (0, 0, 0))
        return Image.frombytes("RGB", (self.breite, self.hoehe), daten)

    def schliessen(self) -> None:
        if self._prozess is not None:
            self._prozess.kill()
            self._prozess = None
