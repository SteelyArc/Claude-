"""Version 3: version-2 cutting with the broadcast-documentary style (designs 37-42).

python3 render_v3.py plan | frames <png> | render <worker> <n> <out_dir>
Environment: NARR_TIMING, SCRATCH, NAR0 as for render_v2.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import pro_style
import render_doc as RD
import render_v2 as V2
import visual_test as VT
import design_frames_5 as DF5
from design_frames import H, W

pro_style.patch(RD, V2, VT)
_orig_bbox = RD.bbox_layer
RD.bbox_layer = lambda fn, glow=0: _orig_bbox(fn, 0)
V2.bbox_layer = RD.bbox_layer
DF5.footer = lambda img, n, title, credit: ImageDraw.Draw(img).text((DF5.X0, 1488), credit, font=DF5.mono(17), fill=(130, 126, 118))

from render_doc import FILM_N as N, FILM_P as P, Card, Clip, Map, Photo, Shot, Still, bbox_layer, ease, ease_out, find_photo  # noqa: E402

IVORY, MUTED, GOLDL, ACCENT, BG = DF5.IVORY, DF5.MUTED, DF5.GOLDL, DF5.ACCENT, DF5.BG
X0, X1 = DF5.X0, DF5.X1
WORDS = {"I": "ONE", "II": "TWO", "III": "THREE", "IV": "FOUR", "V": "FIVE"}


def L(fn):
    return RD.bbox_layer(fn)


class ProChapter(Shot):
    def __init__(self, num, years, title, plate):
        self.num, self.years, self.title, self.plate = num, years, title, plate

    def frame(self, t, dur, idx):
        if not hasattr(self, "_base"):
            ph = find_photo(self.plate)
            if ph:
                src = Image.open(ph[0]).convert("RGB")
                im = DF5.grade(DF5.upscale(src, W, H).filter(ImageFilter.GaussianBlur(3)), seed=7, vignette=0.7)
                self._base = np.asarray(Image.eval(im, lambda v: int(v * 0.45)), np.float32)
            else:
                self._base = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
            self._k = L(lambda d: (DF5.tracked(d, (0, 700), f"CHAPTER {WORDS[self.num]}", DF5.sans(26, 600), GOLDL, 0.45, True),
                                   d.line([(W / 2 - 40, 760), (W / 2 + 40, 760)], fill=GOLDL, width=2)))
            f = DF5.serif(110, 600)
            words = self.title.split(" ")
            lines = [self.title] if len(self.title) < 16 else [" ".join(words[:len(words) // 2]), " ".join(words[len(words) // 2:])]
            self._t = L(lambda d: [d.text(((W - d.textlength(ln, font=f)) / 2, 800 + i * 128), ln, font=f, fill=IVORY) for i, ln in enumerate(lines)])
            fy = 800 + len(lines) * 128 + 20
            fi = DF5.serif_i(40, 400)
            self._y = L(lambda d: d.text(((W - d.textlength(self.years, font=fi)) / 2, fy), self.years, font=fi, fill=MUTED))
        T = t * dur
        f = self._base.copy()
        f = self._k.comp(f, ease(T / 0.5))
        f = self._t.comp(f, ease((T - 0.3) / 0.6))
        f = self._y.comp(f, ease((T - 0.8) / 0.6))
        self.zoom = (1.0, 1.04)
        return f


class ProList(Shot):
    """Minimal vertical list revealed item by item."""

    def __init__(self, kicker, title, items):
        self.kicker, self.title, self.items = kicker, title, items

    def frame(self, t, dur, idx):
        if not hasattr(self, "_head"):
            self._head = L(lambda d: (DF5.tracked(d, (X0, 210), self.kicker, DF5.sans(22, 600), GOLDL, 0.3),
                                      d.text((X0, 250), self.title, font=DF5.serif(60, 600), fill=IVORY)))
            self._rows = []
            step = min(110, 1000 // len(self.items))
            for i, (date, text, hot) in enumerate(self.items):
                y = 400 + i * step
                self._rows.append(L(lambda d, y=y, date=date, text=text, hot=hot: (
                    d.text((X0, y), date, font=DF5.mono(24), fill=ACCENT if hot else MUTED),
                    d.text((X0 + 190, y - 4), text, font=DF5.sans(30, 600 if hot else 400), fill=IVORY),
                    d.line([(X0, y + step - 24), (X1, y + step - 24)], fill=(40, 40, 43), width=1))))
        T = t * dur
        f = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
        f = self._head.comp(f, ease(T / 0.4))
        per = max(0.12, (dur * 0.7) / len(self._rows))
        for i, r in enumerate(self._rows):
            f = r.comp(f, ease((T - 0.3 - i * per) / 0.35))
        self.zoom = (1.0, 1.02)
        return f


class ProDoc(Shot):
    def __init__(self, kicker, german, english, source):
        self.kicker, self.german, self.english, self.source = kicker, german, english, source

    def frame(self, t, dur, idx):
        if not hasattr(self, "_a"):
            fg, fe = DF5.serif_i(32, 400), DF5.serif(56, 500)

            def da(d):
                DF5.tracked(d, (X0, 300), self.kicker, DF5.sans(22, 600), GOLDL, 0.3)
                d.text((X0, 340), "§ 1", font=DF5.serif(44, 600), fill=IVORY)
                y = 420
                for ln in RD.wrap(d, "„" + self.german + "“", fg, X1 - X0):
                    d.text((X0, y), ln, font=fg, fill=MUTED)
                    y += 44
            self._a = L(da)

            def db(d):
                y = 760
                d.line([(X0, y - 30), (X0 + 64, y - 30)], fill=GOLDL, width=3)
                for ln in RD.wrap(d, self.english, fe, X1 - X0):
                    d.text((X0, y), ln, font=fe, fill=IVORY)
                    y += 70
                d.text((X0, y + 30), self.source, font=DF5.mono(20), fill=(130, 126, 118))
            self._b = L(db)
        T = t * dur
        f = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
        f = self._a.comp(f, ease(T / 0.5))
        f = self._b.comp(f, ease((T - 0.8) / 0.6))
        self.zoom = (1.0, 1.03)
        return f


class ProBars(Shot):
    data = [("May 1928", 2.6), ("Sep 1930", 18.3), ("Jul 1932", 37.3), ("Nov 1932", 33.1)]

    def __init__(self, cues, s0):
        self.cues, self.s0 = cues, s0
        self.label = None

    def frame(self, t, dur, idx):
        now = self.s0 + t * dur
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        DF5.tracked(d, (X0, 210), "REICHSTAG ELECTIONS", DF5.sans(22, 600), GOLDL, 0.3)
        d.text((X0, 250), "NSDAP share of the vote", font=DF5.serif(58, 600), fill=IVORY)
        y = 440
        for i, (lab, v) in enumerate(self.data):
            p = 1.0 if i == 0 else ease_out((now - self.cues[i - 1]) / 1.0)
            d.text((X0, y), lab, font=DF5.sans(28, 500), fill=IVORY)
            if p > 0.02:
                d.text((X1, y), f"{v * p:.1f} %", font=DF5.mono(28), fill=IVORY if i != 2 else (230, 200, 150), anchor="ra")
            by = y + 50
            d.rectangle([X0, by, X1, by + 30], fill=(34, 34, 37))
            col = (186, 160, 118) if i != 2 else ACCENT
            d.rectangle([X0, by, X0 + (X1 - X0) * v / 100 * p, by + 30], fill=col)
            mx = X0 + (X1 - X0) * 0.5
            d.line([(mx, by - 10), (mx, by + 40)], fill=IVORY, width=3)
            y += 170
        d.text((X0 + (X1 - X0) * 0.5 + 10, 400), "50 %", font=DF5.mono(22), fill=IVORY)
        d.text((X0, y + 10), "The NSDAP never won a majority in a free election.", font=DF5.serif_i(32, 400), fill=MUTED)
        self.zoom = (1.0, 1.03)
        return np.asarray(img, np.float32)


def pro_counter(kicker, a, b, fmt, sub, photo_keys=None):
    return V2.Counter(kicker, a, b, fmt, sub, color=IVORY, photo_keys=photo_keys)


# ------------------------------------------------------------------ build: v2 list, then swap shots
PLATES = {"I": "R01217", "II": "146-1989-072-16", "III": "119-1426", "IV": "102-11008", "V": "2006-0429-502"}
YEARS = {"I": "1918 — 1919", "II": "1919 — 1923", "III": "1923 — 1924", "IV": "1924 — 1932", "V": "1933 — 1934"}
crowd = Clip(P, 1810.0, "Crowd at a Nazi rally · 1930s")
EVENTS_52 = [("30 Jan", "Hitler becomes Chancellor", False), ("1 Feb", "Reichstag dissolved", False),
             ("4 Feb", "Decree restricts press and meetings", False), ("22 Feb", "SA and SS made auxiliary police", True),
             ("27 Feb", "Reichstag fire", True), ("28 Feb", "Reichstag Fire Decree", True),
             ("5 Mar", "Election under terror · NSDAP 43.9 %", False), ("22 Mar", "Dachau camp opens", True),
             ("23 Mar", "Enabling Act", True)]
PARTIES = [("2 May", "Trade unions smashed", True), ("22 Jun", "SPD banned", True), ("27 Jun", "DNVP dissolves", False),
           ("28 Jun", "DStP dissolves", False), ("4 Jul", "BVP and DVP dissolve", False), ("5 Jul", "Centre Party dissolves", False),
           ("14 Jul", "New parties forbidden by law", True)]


def swap(sh):
    name = type(sh).__name__
    if name == "Chapter":
        num = sh.kicker.replace("CHAPTER ", "")
        return ProChapter(num, YEARS[num], sh.sub[0], PLATES[num])
    if name == "Lens":
        return V2.PhotoText(["Hitlerputsch"], "9 November 1923", "Odeonsplatz, Munich, after the clash", "MUNICH", crowd)
    if name == "Bars":
        return ProBars(sh.cue, sh.s0)
    if name in ("Still", "FX"):
        mk = sh.make.__name__
        table = {
            "still_unemployment": Photo(["Arbeitslose"], "Unemployed dockworkers, Hamburg · 1931", crowd, pan=-1),
            "d24_rain": Card(["Six million", "out of work."], size=96),
            "d06_hemicycle": Still(DF5.d39_seats),
            "d18_52days": ProList("30 JANUARY – 23 MARCH 1933", "52 days", EVENTS_52),
            "d15_fire": V2.PhotoText(["Reichstagsbrand"], "27 February 1933", "The burnt-out Reichstag, Berlin", "BERLIN", crowd),
            "d25_burn": Card(["The Reichstag", "is on fire."], size=96),
            "d22_projector": Photo(["Reichstagsbrand"], "Onlookers at the burnt-out Reichstag", crowd, pan=-1),
            "d08_document": ProDoc("REICHSTAG FIRE DECREE · 28 FEBRUARY 1933",
                                   "Die Artikel 114, 115, 117, 118, 123, 124 und 153 der Verfassung des Deutschen Reichs werden bis auf weiteres außer Kraft gesetzt.",
                                   "Basic rights of the constitution are suspended until further notice.",
                                   "Reichsgesetzblatt 1933 I, p. 83"),
            "d23_halftone": Still(DF5.d40_quote),
            "d10_vote": Card(["Only the SPD", "voted no."], size=96),
            "d14_gleichschaltung": ProList("SUMMER 1933", "Forced into line", PARTIES),
            "d27_dossier": Photo(["Dachau"], "SS guard unit, Dachau · 1933", crowd),
            "d29_searchlights": Clip(N, 411.0, "Hitler · newsreel"),
            "d28_double": Still(DF5.d38_location),
            "d30_split": Card(["They helped destroy", "the democracy they", "claimed to protect."], accent=1, size=74),
            "d13_crack": Card(["Step by step."], accent=0, size=110),
        }
        return table.get(mk, sh)
    if name == "Anim":
        names = sh.factory.__code__.co_names
        if "MapScene" in names:
            return Map("30 January 1933", "BERLIN", cities=("Berlin", "Munich", "Hamburg"), pulse=("Berlin",))
        if "CrackScene" in names:
            return Card(["Laws without", "parliament."], sub=["Even laws that broke the constitution."], accent=1, size=96)
        if "FinalScene" in names:
            return pro_counter("30 JAN 1933 – 2 AUG 1934", 0, 549, lambda v: f"{int(v)} days", ["from Chancellor to dictator"])
    if name == "Counter":
        sh.color = IVORY
    return sh


_v2_build = V2.build_shots


def build_shots():
    S = [(t, swap(sh)) for t, sh in _v2_build()]

    S2 = list(S)
    # Hindenburg portrait (design 37) where his refusal is mentioned; Potsdam super (38) at "found a way to use him"
    out = []
    t63 = RD.T(V2.NI(63))
    t82 = RD.T(82)
    for t, sh in S2:
        if abs(t - t63) < 0.05:
            sh = Still(DF5.d37_portrait)
        if abs(t - t82) < 0.05:
            sh = Still(DF5.d38_location)
        out.append((t, sh))
    # second shot at line 4 -> design 41 map
    t4 = RD.T(V2.NI(4))
    seen = 0
    final = []
    for t, sh in sorted(out, key=lambda x: x[0]):
        if t > t4 + 0.05 and t < RD.T(V2.NI(5)) - 0.05 and seen == 0:
            sh = Still(DF5.d41_map)
            seen = 1
        final.append((t, sh))
    return final


RD.build_shots = build_shots

if __name__ == "__main__":
    RD.main()
