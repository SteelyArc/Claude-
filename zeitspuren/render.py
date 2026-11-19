"""Erzeugt die Einzelbilder und übergibt sie zusammen mit dem Ton an FFmpeg."""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import audio as audio_mod
from .bilder import Szene, einzelbild
from .einstellungen import Einstellungen


@dataclass
class Format:
    breite: int = 1080
    hoehe: int = 1920
    fps: int = 30
    crf: int = 18
    preset: str = "fast"  # gleiche Qualität wie "slow" (SSIM gemessen), halbe Rechenzeit
    vorschau: bool = False


VOLL = Format()
VORSCHAU = Format(breite=540, hoehe=960, fps=30, crf=23, preset="veryfast", vorschau=True)


class RenderFehler(RuntimeError):
    pass


def _weich(x: float) -> float:
    """Sanfte Überblendkurve (langsam beginnen, langsam enden)."""
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def _szenenbild(sz: Szene, t: float, fmt: Format) -> Image.Image:
    """Ein Bild der Szene: Foto-Kamerafahrt (Etappe 1) oder eigener Renderer
    (Karte, Archivfilm), danach die Texteinblendungen der Szene."""
    if sz.renderer is not None:
        bild = sz.renderer(t)
    else:
        bild = einzelbild(sz, t, fmt.breite, fmt.hoehe)
    for e in sz.einblendungen:
        e.auftragen(bild, t)
    return bild


def _bild_zur_zeit(szenen: list[Szene], t: float, fmt: Format) -> bytes:
    aktiv = [s for s in szenen if s.sichtbar_von <= t < s.sichtbar_bis] or [szenen[-1]]
    if len(aktiv) == 1:
        return _szenenbild(aktiv[0], t, fmt).tobytes()
    alt, neu = aktiv[0], aktiv[1]
    spanne = alt.sichtbar_bis - neu.sichtbar_von
    a = _weich((t - neu.sichtbar_von) / spanne)
    bild = Image.blend(_szenenbild(alt, t, fmt), _szenenbild(neu, t, fmt), a)
    return bild.tobytes()


def _videofilter(e: Einstellungen, fmt: Format, gesamt: float) -> str:
    teile = []
    if e.farbe == "warm":
        teile.append("colorbalance=rs=0.025:bs=-0.025:rm=0.02:bm=-0.02")
    elif e.farbe == "schwarzweiss":
        teile.append("hue=s=0")
    teile.append("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p")
    if e.vignette:
        teile.append("vignette=angle=0.42")
    if e.filmkorn == "leicht" and not fmt.vorschau:
        teile.append("noise=c0s=3:c0f=t")
    aus = min(1.6, e.nachlauf)
    teile.append("fade=t=in:st=0:d=1.0")
    teile.append(f"fade=t=out:st={gesamt - aus:.3f}:d={aus:.3f}")
    return ",".join(teile)


def rendern(szenen: list[Szene], info: audio_mod.AudioInfo, e: Einstellungen, gesamt: float,
            ziel: Path, fmt: Format, protokoll: Path) -> None:
    anzahl = int(round(gesamt * fmt.fps))
    gesamt_exakt = anzahl / fmt.fps

    befehl = [
        "ffmpeg", "-hide_banner", "-y", "-loglevel", "warning",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{fmt.breite}x{fmt.hoehe}",
        "-r", str(fmt.fps), "-thread_queue_size", "64", "-i", "-",
        "-i", str(info.pfad),
        "-filter_complex",
        f"[0:v]{_videofilter(e, fmt, gesamt_exakt)}[v];"
        f"[1:a]{audio_mod.filterkette(info, e.vorlauf, gesamt_exakt)}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", fmt.preset, "-crf", str(fmt.crf),
        "-profile:v", "high", "-level:v", "4.2", "-pix_fmt", "yuv420p",
        "-g", str(fmt.fps * 2), "-maxrate", "25M", "-bufsize", "50M",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{gesamt_exakt:.6f}",
        str(ziel),
    ]

    with open(protokoll, "w", encoding="utf-8") as log:
        prozess = subprocess.Popen(befehl, stdin=subprocess.PIPE, stderr=log)
        threads = max(2, (os.cpu_count() or 2))
        start = time.time()
        letzte_meldung = -1
        try:
            with ThreadPoolExecutor(threads) as pool:
                warteschlange: deque = deque()
                k = 0
                fertig = 0
                while fertig < anzahl:
                    while k < anzahl and len(warteschlange) < threads * 3:
                        warteschlange.append(pool.submit(_bild_zur_zeit, szenen, k / fmt.fps, fmt))
                        k += 1
                    prozess.stdin.write(warteschlange.popleft().result())
                    fertig += 1
                    prozent = fertig * 100 // anzahl
                    if prozent // 10 != letzte_meldung:
                        letzte_meldung = prozent // 10
                        vergangen = time.time() - start
                        rest = vergangen / fertig * (anzahl - fertig)
                        print(f"   {prozent:3d} %  (noch ca. {int(rest // 60)}:{int(rest % 60):02d} min)", flush=True)
        except BrokenPipeError:
            pass
        finally:
            if prozess.stdin:
                try:
                    prozess.stdin.close()
                except BrokenPipeError:
                    pass
            prozess.wait()

    if prozess.returncode != 0:
        fehlertext = protokoll.read_text(encoding="utf-8", errors="replace")[-1500:]
        print(fehlertext, file=sys.stderr)
        raise RenderFehler("FFmpeg hat die Videoerstellung abgebrochen (Details siehe ffmpeg_protokoll.txt).")
