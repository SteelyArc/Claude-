"""Startpunkt: ``python3 -m zeitspuren projekte/MEIN_PROJEKT``"""

from __future__ import annotations

import argparse
import json
import math
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
from . import drehbuch as drehbuch_mod
from . import film as film_mod
from . import karten as karten_mod
from . import texte as texte_mod
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
    ap.add_argument("--pruefen", action="store_true",
                    help="nur Material prüfen (Länge, Bildanzahl), kein Video erstellen")
    ap.add_argument("--bestaetigt", action="store_true",
                    help="Video trotz gemeldeter Abweichungen erstellen (nach Rückfrage)")
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
        db_datei = projekt / "drehbuch.txt"
        zp_datei = projekt / "zeitplan.txt"
        dszenen = None
        arten = None
        if db_datei.exists():
            dszenen = drehbuch_mod.lesen(db_datei, projekt)
            fehlerliste = drehbuch_mod.pruefen(dszenen)
            if fehlerliste:
                raise drehbuch_mod.DrehbuchFehler(
                    "Das Drehbuch enthält Fehler:\n   • " + "\n   • ".join(fehlerliste))
            eintraege = [(d.zeit, d.pfad or Path(d.anzeigename), d.optionen.get("darstellung", ""),
                          d.optionen.get("bewegung", "")) for d in dszenen]
            arten = [d.art for d in dszenen]
            quelle = "drehbuch.txt"
            genutzt = {d.pfad for d in dszenen if d.pfad}
            for p in drehbuch_mod._dateien(projekt):
                if p not in genutzt:
                    print(f"   Hinweis: '{p.name}' kommt im Drehbuch nicht vor und wird nicht verwendet.")
        elif zp_datei.exists():
            bilder = bilder_mod.finden(projekt)
            eintraege = zeitplan_mod.aus_datei(zp_datei, bilder)
            quelle = "zeitplan.txt"
            genutzt = {e_[1] for e_ in eintraege}
            for p in bilder:
                if p not in genutzt:
                    print(f"   Hinweis: '{p.name}' steht nicht in zeitplan.txt und wird nicht verwendet.")
        else:
            bilder = bilder_mod.finden(projekt)
            eintraege = zeitplan_mod.gleichmaessig(bilder, info.dauer)
            quelle = "gleichmäßig verteilt"
        szenen, gesamt, warnungen, zu_lang = zeitplan_mod.szenen_bilden(
            eintraege, info.dauer, e.vorlauf, e.nachlauf, e.ueberblendung, e.bilddauer_min, e.bilddauer_max,
            arten)
        einheit = "Szenen" if dszenen else "Bilder"
        print(f"   {len(szenen)} {einheit}, Anordnung: {quelle}, Videolänge {zeitplan_mod.zeit_schreiben(gesamt)} min")
        if dszenen:
            for sz, d in zip(szenen, dszenen):
                sz.art, sz.spez = d.art, d
            for h in drehbuch_mod.schnittanalyse(dszenen):
                print(f"   {h}")

        # --- Kanalvorgabe prüfen, BEVOR gerechnet wird -------------------------
        probleme = []
        abweichung = info.dauer - e.ziel_laenge
        ziel_txt = zeitplan_mod.zeit_schreiben(e.ziel_laenge)
        if abs(abweichung) > e.laenge_toleranz:
            richtung = "kürzer" if abweichung < 0 else "länger"
            probleme.append(
                f"Die Sprecheraufnahme ist {zeitplan_mod.zeit_schreiben(info.dauer)} min lang und damit "
                f"{abs(abweichung):.0f} s {richtung} als die Vorgabe von {ziel_txt} min "
                f"(erlaubt ± {e.laenge_toleranz:.0f} s). Die Stimme wird NICHT gedehnt oder gestaucht.")
        else:
            print(f"   Länge OK: {zeitplan_mod.zeit_schreiben(info.dauer)} min "
                  f"(Vorgabe {ziel_txt} min, Abweichung {abweichung:+.1f} s)")
        empfohlen = math.ceil(info.dauer / 8)  # ca. 8 s pro Bild = ruhig, aber nicht statisch
        mindestens = math.ceil(info.dauer / e.bilddauer_max)
        if zu_lang:
            beispiele = "; ".join(zu_lang[:5]) + ("; …" if len(zu_lang) > 5 else "")
            probleme.append(
                f"Zu wenige {einheit}: Für {zeitplan_mod.zeit_schreiben(info.dauer)} min Erzählung werden "
                f"mindestens {mindestens}, empfohlen etwa {empfohlen} {einheit} gebraucht (vorhanden: "
                f"{len(szenen)}). {len(zu_lang)} Szene(n) würden zu lange stehen, das wirkt wie "
                f"künstliche Verlängerung ({beispiele}).")
        else:
            print(f"   Anzahl OK: {len(szenen)} {einheit} (empfohlen etwa {empfohlen}, "
                  f"durchschnittlich {info.dauer / len(szenen):.1f} s pro Szene)")

        if probleme:
            print("\nBITTE PRÜFEN – Abweichung von der Kanalvorgabe:")
            for pr in probleme:
                print(f"   • {pr}")
            if not args.bestaetigt and not args.pruefen:
                print("\nEs wurde noch KEIN Video erstellt. Zum Erstellen trotz Abweichung erneut mit "
                      "--bestaetigt starten.")
                return 2
        if args.pruefen:
            print("\nPrüfung abgeschlossen – " + ("Abweichungen siehe oben." if probleme
                                                   else "alles entspricht der Kanalvorgabe."))
            return 0

        print("3) Bildplatten und Kamerafahrten vorbereiten …")

        def vorbereiten(nr_szene):
            i, sz = nr_szene
            d = sz.spez
            if d is not None:
                return szene_aus_drehbuch(i, sz, d)
            foto_vorbereiten(i, sz)

        def zeit_im_video(text):
            return e.vorlauf + zeitplan_mod.zeit_lesen(text) if text else None

        def ortsmarke(sz, o):
            if not (o.get("ort") or o.get("zeit") or o.get("quelle")):
                return
            b, x, y = texte_mod.ortsmarke(o.get("ort", ""), o.get("zeit", ""), o.get("quelle", ""),
                                          fmt.breite, fmt.hoehe)
            von = max(sz.beginn + 0.4, 1.0)
            bis = min(sz.beginn + 7.5, sz.sichtbar_bis - 0.9)
            if bis - von > 1.8:
                sz.einblendungen.append(texte_mod.Einblendung(b, x, y, von, bis))

        def szene_aus_drehbuch(i, sz, d):
            o = d.optionen
            if d.ist_datenkarte:
                jahr = int(d.quelle)
                staende = [karten_mod.Kartenstand(jahr, drehbuch_mod.hervorhebungen(o.get("hervorheben", ""), jahr))]
                if "wechsel" in o:
                    jahr2 = int(o["wechsel"])
                    staende.append(karten_mod.Kartenstand(jahr2, drehbuch_mod.hervorhebungen(
                        o.get("hervorheben_danach", o.get("hervorheben", "")), jahr2)))
                karte = karten_mod.Kartenszene(
                    staende, zeit_im_video(o.get("wechsel_bei")), o.get("ausschnitt", "Europa"),
                    o.get("fahrt"), zeit_im_video(o.get("fahrt_von")), zeit_im_video(o.get("fahrt_bis")),
                    drehbuch_mod.orte_liste(o.get("orte", "")), o.get("titel", ""), o.get("jahreszahl"),
                    sz.sichtbar_von, sz.sichtbar_bis, fmt.breite, fmt.hoehe)
                sz.renderer = karte.bild
                sz.darstellung = "animiert"
                sz.bewegung = ("fahrt → " + o["fahrt"]) if "fahrt" in o else "langsamer Zoom"
                return
            if d.art == "film":
                ab = zeitplan_mod.zeit_lesen(o.get("ab", "0"))
                darstellung = o.get("darstellung", "eingepasst")
                f = film_mod.Archivfilm(d.pfad, ab, sz.sichtbar_bis - sz.sichtbar_von, fmt.breite, fmt.hoehe,
                                        fmt.fps, darstellung)
                if f.zu_kurz:
                    sz.hinweis = (f"Film ab {o.get('ab', '0:00')} nur noch {f.verfuegbar:.1f} s lang, "
                                  f"Szene braucht {f.dauer:.1f} s – letztes Bild wird gehalten")
                start = sz.sichtbar_von
                sz.renderer = lambda t, f=f, start=start: f.bild(t - start)
                sz.darstellung, sz.bewegung = darstellung, "Originalbewegung"
                ortsmarke(sz, o)
                return
            # Foto, Dokument oder eingescannte Karte
            if d.art == "dokument":
                sz.darstellung = sz.darstellung or "eingepasst"
                sz.bewegung = sz.bewegung or "zoom-rein"
            elif d.art == "karte":
                sz.darstellung = sz.darstellung or "eingepasst"
                sz.bewegung = sz.bewegung or "zoom-rein"
            foto_vorbereiten(i, sz)
            ortsmarke(sz, o)

        def foto_vorbereiten(i, sz):
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

        if any(sz.art == "film" for sz in szenen):
            print("   (Archivfilme laufen in Originalgeschwindigkeit und ohne Originalton)")

        with ThreadPoolExecutor(4) as pool:
            list(pool.map(vorbereiten, enumerate(szenen)))

        ausgabe = projekt / "ausgabe"
        ausgabe.mkdir(exist_ok=True)
        zeilen = []
        for sz in szenen:
            sprechzeit = max(0.0, sz.beginn - e.vorlauf) if sz is not szenen[0] else 0.0
            if dszenen:
                zeilen.append(f"{zeitplan_mod.zeit_schreiben(sprechzeit):>7}   {sz.art:<9} "
                              f"{sz.spez.anzeigename:<34} {sz.darstellung:<11} {sz.bewegung}")
            else:
                zeilen.append(f"{zeitplan_mod.zeit_schreiben(sprechzeit):>7}   {sz.pfad.name:<40} "
                              f"{sz.darstellung:<11} {sz.bewegung}")
            print(f"   {zeilen[-1]}" + (f"   ⚠ {sz.hinweis}" if sz.hinweis else ""))
        if dszenen:
            (ausgabe / "szenenplan.txt").write_text(
                "# Übersicht der Szenen (Zeit ab Beginn der Sprecheraufnahme). Geändert wird in drehbuch.txt.\n"
                + "\n".join(zeilen) + "\n", encoding="utf-8")
        else:
            (ausgabe / "zeitplan_verwendet.txt").write_text(
                "# Verwendeter Zeitplan. Zum Anpassen als 'zeitplan.txt' in den Projektordner kopieren.\n"
                "# Zeit (ab Beginn der Sprecheraufnahme)   Bild   Darstellung   Bewegung\n"
                + "\n".join(zeilen) + "\n", encoding="utf-8")
        for w in warnungen:
            print(f"   Hinweis: {w}")

        name = projekt.name + ("_vorschau" if fmt.vorschau else "")
        ziel = ausgabe / f"{name}.mp4"
        print(f"4) Video berechnen ({len(szenen)} Szenen, {fmt.breite}×{fmt.hoehe}, {fmt.fps} fps) …")
        try:
            rendern(szenen, info, e, gesamt, ziel, fmt, ausgabe / "ffmpeg_protokoll.txt")
        finally:
            for sz in szenen:
                f = getattr(sz.renderer, "__defaults__", None)
                if f and isinstance(f[0], film_mod.Archivfilm):
                    f[0].schliessen()

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
            zeitplan_mod.ZeitplanFehler, RenderFehler, karten_mod.KartenFehler,
            film_mod.FilmFehler) as fehler:
        print(f"\nFEHLER: {fehler}", file=sys.stderr)
        return 1

    dauer = time.time() - beginn
    print(f"\nFERTIG nach {int(dauer // 60)}:{int(dauer % 60):02d} min → {ziel.relative_to(WURZEL) if ziel.is_relative_to(WURZEL) else ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
