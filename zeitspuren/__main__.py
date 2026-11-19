"""Startpunkt: ``python3 -m zeitspuren projekte/MEIN_PROJEKT``"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import __version__
from . import audio as audio_mod
from . import bilder as bilder_mod
from . import einstellungen as einst_mod
from . import zeitplan as zeitplan_mod
from .render import VOLL, VORSCHAU, RenderFehler, rendern

WURZEL = Path(__file__).resolve().parent.parent
PROJEKTE = WURZEL / "projekte"


def _projekt_finden(angabe: str) -> Path:
    pfad = Path(angabe)
    for kandidat in (pfad, PROJEKTE / angabe):
        if kandidat.is_dir():
            return kandidat.resolve()
    vorhanden = sorted(p.name for p in PROJEKTE.iterdir() if p.is_dir() and not p.name.startswith("_")) \
        if PROJEKTE.is_dir() else []
    tipp = f" Vorhandene Projekte: {', '.join(vorhanden)}" if vorhanden else ""
    raise SystemExit(f"FEHLER: Projekt '{angabe}' nicht gefunden.{tipp}")


def _pruefen(ziel: Path) -> dict:
    erg = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate,duration:format=duration,size",
         "-of", "json", str(ziel)],
        capture_output=True, text=True,
    )
    return json.loads(erg.stdout or "{}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zeitspuren", description="ZEITSPUREN Videoproduktion (9:16)")
    ap.add_argument("projekt", help="Projektordner, z. B. projekte/mauerfall oder einfach 'mauerfall'")
    ap.add_argument("--vorschau", action="store_true", help="schnelle Vorschau in halber Auflösung")
    args = ap.parse_args(argv)

    beginn = time.time()
    projekt = _projekt_finden(args.projekt)
    fmt = VORSCHAU if args.vorschau else VOLL
    print(f"ZEITSPUREN Videoproduktion v{__version__}")
    print(f"Projekt: {projekt.name}   ({'Vorschau 540×960' if fmt.vorschau else 'Endfassung 1080×1920'})\n")

    try:
        e = einst_mod.laden(projekt)

        print("1) Sprecheraufnahme analysieren …")
        info = audio_mod.analysieren(audio_mod.finden(projekt))
        print(f"   Datei: {info.pfad.name}  |  Länge: {zeitplan_mod.zeit_schreiben(info.dauer)} min  |  "
              f"Lautheit: {info.lautheit_lufs:.1f} LUFS → Anpassung {info.verstaerkung_db:+.1f} dB "
              f"(Tempo und Klang bleiben unverändert)")

        print("2) Bilder einlesen und zeitlich anordnen …")
        bilder = bilder_mod.finden(projekt)
        zp_datei = projekt / "zeitplan.txt"
        if zp_datei.exists():
            eintraege = zeitplan_mod.aus_datei(zp_datei, bilder)
            quelle = "zeitplan.txt"
            genutzt = {e_[1] for e_ in eintraege}
            for p in bilder:
                if p not in genutzt:
                    print(f"   Hinweis: '{p.name}' steht nicht in zeitplan.txt und wird nicht verwendet.")
        else:
            eintraege = zeitplan_mod.gleichmaessig(bilder, info.dauer)
            quelle = "gleichmäßig verteilt"
        szenen, gesamt, warnungen = zeitplan_mod.szenen_bilden(
            eintraege, info.dauer, e.vorlauf, e.nachlauf, e.ueberblendung, e.bilddauer_min)
        print(f"   {len(szenen)} Bilder, Anordnung: {quelle}, Videolänge {zeitplan_mod.zeit_schreiben(gesamt)} min")

        print("3) Bildplatten und Kamerafahrten vorbereiten …")

        def vorbereiten(nr_szene):
            i, sz = nr_szene
            bild = bilder_mod.oeffnen(sz.pfad)
            seitenv = fmt.breite / fmt.hoehe
            darstellung = sz.darstellung or bilder_mod._darstellung_waehlen(*bild.size, seitenv)
            # Hinweis, wenn ein Bild für die Endfassung stark vergrößert werden muss
            b, h = bild.size
            vergroesserung = (max if darstellung == "ganz" else min)(VOLL.breite / b, VOLL.hoehe / h)
            if vergroesserung > 1.8:
                sz.hinweis = f"geringe Auflösung ({b}×{h}), wird {vergroesserung:.1f}-fach vergrößert"
            sz.platte = bilder_mod.platte_bauen(bild, darstellung, fmt.breite, fmt.hoehe, e.hintergrund)
            bewegung = sz.bewegung or bilder_mod.bewegung_automatisch(
                i, sz.pfad, sz.platte, darstellung, fmt.breite, fmt.hoehe)
            sz.darstellung, sz.bewegung = darstellung, bewegung
            sz.fahrt = bilder_mod.fahrt_planen(
                sz.platte, bewegung, sz.sichtbar_bis - sz.sichtbar_von, e.bewegung, fmt.breite, fmt.hoehe)

        with ThreadPoolExecutor(4) as pool:
            list(pool.map(vorbereiten, enumerate(szenen)))

        ausgabe = projekt / "ausgabe"
        ausgabe.mkdir(exist_ok=True)
        zeilen = []
        for sz in szenen:
            sprechzeit = max(0.0, sz.beginn - e.vorlauf) if sz is not szenen[0] else 0.0
            zeilen.append(f"{zeitplan_mod.zeit_schreiben(sprechzeit):>7}   {sz.pfad.name:<40} "
                          f"{sz.darstellung:<11} {sz.bewegung}")
            print(f"   {zeilen[-1]}" + (f"   ⚠ {sz.hinweis}" if sz.hinweis else ""))
        (ausgabe / "zeitplan_verwendet.txt").write_text(
            "# Verwendeter Zeitplan. Zum Anpassen als 'zeitplan.txt' in den Projektordner kopieren.\n"
            "# Zeit (ab Beginn der Sprecheraufnahme)   Bild   Darstellung   Bewegung\n"
            + "\n".join(zeilen) + "\n", encoding="utf-8")
        for w in warnungen:
            print(f"   Hinweis: {w}")

        name = projekt.name + ("_vorschau" if fmt.vorschau else "")
        ziel = ausgabe / f"{name}.mp4"
        print(f"4) Video berechnen ({len(szenen)} Szenen, {fmt.breite}×{fmt.hoehe}, {fmt.fps} fps) …")
        rendern(szenen, info, e, gesamt, ziel, fmt, ausgabe / "ffmpeg_protokoll.txt")

        print("5) Ergebnis prüfen …")
        daten = _pruefen(ziel)
        v = next(s for s in daten["streams"] if s["codec_type"] == "video")
        a = next(s for s in daten["streams"] if s["codec_type"] == "audio")
        dauer_v, dauer_a = float(v["duration"]), float(a["duration"])
        groesse = int(daten["format"]["size"]) / 1e6
        print(f"   Bild: {v['codec_name']} {v['width']}×{v['height']} @ {v['r_frame_rate']}  |  "
              f"Ton: {a['codec_name']}  |  Länge Bild {dauer_v:.2f} s / Ton {dauer_a:.2f} s  |  {groesse:.1f} MB")
        if abs(dauer_v - dauer_a) > 0.1:
            print("   WARNUNG: Bild- und Tonlänge weichen voneinander ab!")

    except (audio_mod.AudioFehler, bilder_mod.BildFehler, einst_mod.EinstellungsFehler,
            zeitplan_mod.ZeitplanFehler, RenderFehler) as fehler:
        print(f"\nFEHLER: {fehler}", file=sys.stderr)
        return 1

    dauer = time.time() - beginn
    print(f"\nFERTIG nach {int(dauer // 60)}:{int(dauer % 60):02d} min → {ziel.relative_to(WURZEL) if ziel.is_relative_to(WURZEL) else ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
