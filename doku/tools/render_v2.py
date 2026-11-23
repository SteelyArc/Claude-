"""Version 2 of the documentary body: denser cutting, more photos/film, animated graphics.

Reuses render_doc (timing, overlays, Clip/Photo/Card/Map/Bars/Anim/Still) and adds:
  PhotoText  - archive photo with kinetic headline text
  Counter    - animated number graphic
  FX         - full-frame design still with animated particles (dust / embers / rain)
  Lens       - magnifying lens gliding over the 1923 Odeonsplatz photo

python3 render_v2.py plan | frames <png> | render <worker> <n> <out_dir>
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import render_doc as RD
from render_doc import (FILM_N as N, FILM_P as P, TIMING, Anim, Bars, Card, Chapter, Clip, Map, Photo, Shot, Still,
                        bbox_layer, ease, ease_out, find_photo, media_frame)
import design_frames as DF
import design_frames_2 as DF2
import design_frames_3 as DF3
from design_frames import DIM, H, PAPER, RED, W, font, text_c, wrap, MONO, SERIF_B, SERIF_I, SANS_B
from design_frames_2 import GOLD, light_rays
import visual_test as VT

X0, X1 = RD.SAFE_X0, RD.SAFE_X1


_OLD = json.load(open(os.path.join(RD.ROOT, "audio", "narration_lewis_timing.json")))
_NEW_IDX = {}
_j = 0
for _i, _o in enumerate(_OLD):
    while TIMING[_j]["text"] != _o["text"]:
        _j += 1
    _NEW_IDX[_i] = _j
    _j += 1


def NI(i):
    """Map a line index of the shortened (Lewis) script onto the full script timing."""
    return _NEW_IDX[i]


def line_end(i):
    return RD.NAR0 + (TIMING[i + 1]["start"] if i + 1 < len(TIMING) else TIMING[i]["end"] + 1.6)


# ------------------------------------------------------------------ new shot types
class PhotoText(Photo):
    """Photo (or fallback) with a kinetic headline in the lower media area."""

    def __init__(self, keys, big, label, kicker=None, fallback=None, pan=1):
        super().__init__(keys, label, fallback, pan)
        self.big, self.kicker = big, kicker

    def frame(self, t, dur, idx):
        f = super().frame(t, dur, idx)
        if not hasattr(self, "_txt"):
            fo = font(SERIF_B, 92)
            probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
            size = 92
            while size > 44 and probe.textlength(self.big, font=font(SERIF_B, size)) > X1 - X0:
                size -= 4
            fo = font(SERIF_B, size)
            self._txt = bbox_layer(lambda d: (d.rectangle([0, 960, W, 1140], fill=(0, 0, 0, 120)),
                                              d.text((X0, 980), self.kicker or "", font=font(MONO, 26), fill=GOLD),
                                              d.text((X0, 1018), self.big, font=fo, fill=PAPER)), glow=0)
        if not self.found:
            return f
        k = ease_out((t * dur - 0.2) / 0.5)
        return self._txt.comp(f, k)


class Counter(Shot):
    def __init__(self, kicker, start, end, fmt, sub=None, color=PAPER, photo_keys=None):
        self.kicker, self.a, self.b, self.fmt, self.sub, self.color = kicker, start, end, fmt, sub, color
        self.photo_keys = photo_keys
        ph = find_photo(*photo_keys) if photo_keys else None
        self.credit = ph[1] if ph else None

    def frame(self, t, dur, idx):
        if not hasattr(self, "_base"):
            base = np.zeros((H, W, 3), np.float32) + 10
            ph = find_photo(*self.photo_keys) if self.photo_keys else None
            if ph:
                im = ImageOps.fit(Image.open(ph[0]).convert("L"), (W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
                base = np.asarray(im.convert("RGB"), np.float32) * 0.28
                self.credit = ph[1]
            base = base + light_rays((W, H), (W / 2, 300), (150, 120, 90), 0.4, seed=idx % 7)
            self._base = base
            self._k = bbox_layer(lambda d: text_c(d, 560, self.kicker, font(MONO, 32), GOLD, w=1000))
            self._s = bbox_layer(lambda d: [text_c(d, 960 + j * 50, s, font(SERIF_I, 40), DIM, w=1000) for j, s in enumerate(self.sub or [])])
        f = self._base.copy()
        f = self._k.comp(f, ease(t * dur / 0.3))
        v = self.a + (self.b - self.a) * ease_out((t * dur - 0.2) / max(0.8, dur * 0.55))
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        s = self.fmt(v)
        size = 190
        while size > 60 and d.textlength(s, font=font(SERIF_B, size)) > 960:
            size -= 6
        lay = Image.new("RGBA", (W, 320), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.text(((W - ld.textlength(s, font=font(SERIF_B, size))) / 2, 40), s, font=font(SERIF_B, size), fill=self.color + (255,))
        g = lay.filter(ImageFilter.GaussianBlur(16))
        img.paste(g, (0, 640), g)
        img.paste(lay, (0, 640), lay)
        f = np.asarray(img, np.float32).copy()
        f = self._s.comp(f, ease((t * dur - 0.8) / 0.5))
        self.zoom = (1.0, 1.04)
        return f


class FX(Still):
    """Full-frame design still + animated particles."""

    def __init__(self, make, fx="dust", push=0.05, center=(W / 2, H / 2)):
        super().__init__(make, None, push, center)
        self.fx = fx
        rng = np.random.default_rng(abs(hash(make.__name__)) % 1000)
        self.p = rng.uniform([0, 0], [W, H], (260, 2))
        self.s = rng.uniform(0.5, 1.5, 260)

    def frame(self, t, dur, idx):
        f = super().frame(t, dur, idx)
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        T = t * dur
        for (x, y), s in zip(self.p, self.s):
            if self.fx == "embers":
                yy = (y - T * 160 * s) % H
                xx = x + 14 * math.sin(T * 2 + y)
                d.line([(xx, yy), (xx, yy + 10 * s)], fill=(255, int(150 + 60 * s), 60, int(150 * s)), width=2)
            elif self.fx == "rain":
                yy = (y + T * 900 * s) % H
                d.line([(x, yy), (x - 3, yy + 26 * s)], fill=(200, 215, 235, int(70 * s)), width=1)
            else:
                yy = (y + T * 18 * s) % H
                xx = x + 10 * math.sin(T * 0.7 + y)
                r = 1 + s
                d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 245, 220, int(60 * s)))
        img.paste(lay, (0, 0), lay)
        return np.asarray(img, np.float32).copy()


class Lens(Shot):
    def __init__(self):
        self.label = "Odeonsplatz, Munich, after the clash · 9 Nov 1923"
        self.credit = DF3.photo("119-1426")[1]

    def frame(self, t, dur, idx):
        if not hasattr(self, "_big"):
            src, cred = DF3.photo("119-1426")
            self.credit = cred
            big = ImageOps.fit(src, (W, 900), Image.BICUBIC)
            self._big = big
            base = Image.new("RGB", (W, H), (12, 12, 13))
            base.paste(Image.eval(big, lambda v: int(v * 0.45)), (0, 270))
            self._base = base
            sc = 900 / src.height
            self._target = (min(640 * sc - (src.width * sc - W) / 2, 950), 276 * sc)
        R, mag = 200, 2.3
        tx, ty = self._target
        e = ease((t * dur - 0.2) / 1.6)
        cx = 250 + (tx - 250) * e
        cy = 600 + (ty - 600) * e
        img = self._base.copy()
        crop = self._big.crop((int(cx - R / mag), int(cy - R / mag), int(cx + R / mag), int(cy + R / mag))).resize((2 * R, 2 * R), Image.BICUBIC)
        m = Image.new("L", (2 * R, 2 * R), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
        px, py = int(cx - R), int(270 + cy - R)
        img.paste(crop, (px, py), m)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([px, py, px + 2 * R, py + 2 * R], outline=(210, 200, 180), width=9)
        d.line([(px + 1.7 * R, py + 1.7 * R), (px + 2.3 * R, py + 2.3 * R)], fill=(60, 50, 40), width=30)
        if e > 0.95:
            d.text((X0, 1180 - 30), "BANNER: 'VOM HITLERPUTSCH AM 9.11.23'", font=font(MONO, 24), fill=GOLD)
        self.zoom = (1.0, 1.04)
        return np.asarray(img, np.float32).copy()


# ------------------------------------------------------------------ shot list
def build_shots():
    S = []

    def at(i, *shots):
        i = NI(i)
        a, b = RD.T(i), line_end(i)
        for j, sh in enumerate(shots):
            S.append((a + (b - a) * j / len(shots), sh))

    crowd = Clip(P, 1810.0, "Crowd at a Nazi rally · 1930s")
    fmt_int = lambda v: f"{int(round(v)):,}"
    # ---------------- 0 intro
    at(0, Map("Germany, 1933", "A NATION IN CRISIS", cities=("Berlin", "Munich", "Hamburg", "Nuremberg", "Königsberg"), pulse=("Berlin",), note="Borders of 1933"))
    at(1, PhotoText(["Arbeitslose"], "Crisis.", "Unemployed dockworkers, Hamburg · 1931", "GERMANY", crowd))
    at(2, Clip(P, 739.0, "The Reichstag, Berlin"))
    at(3, Clip(P, 684.6, "Adolf Hitler · newsreel"), Clip(N, 174.0, "Hitler at a rally · 1930s"))
    at(4, Clip(N, 121.0, "Nazi leaders at the Nuremberg rally · 1930s"), Clip(N, 99.0, "Nuremberg rally grounds · 1930s"))
    at(5, Clip(P, 1597.6, "Ballot marked 'Ja'"))
    at(6, Card(["Not one sudden", "revolution."]))
    at(7, Photo(["Arbeitslose"], "Unemployed dockworkers, Hamburg · 1931", crowd), Clip(P, 759.0, "'Der Angriff', Goebbels' Nazi newspaper"),
       Clip(P, 1814.0, "Rally crowd · 1930s"))
    at(8, Photo(["Tag von Potsdam"], "Hitler and Hindenburg · 'Day of Potsdam', 21 Mar 1933", Clip(N, 182.0, "Hitler with SA leaders")),
       Photo(["Papen"], "Franz von Papen", Card(["The conservatives"], kicker="1933", size=90)))
    at(9, Card(["They were wrong."], accent=0))
    # ---------------- 1 1918-1919
    at(10, Chapter("I", "1918", "Defeat and Revolution"), Clip(N, 136.5, "First World War graves"))
    at(11, Counter("THE FIRST WORLD WAR", 0, 2000000, lambda v: f"{int(v):,}", ["German soldiers killed"]))
    at(12, Photo(["Wilhelm II"], "Kaiser Wilhelm II", Clip(N, 66.5, "Kaiser Wilhelm II · portrait (film graphic)")),
       Photo(["Revolution"], "Revolution in Berlin · November 1918", Card(["9 November 1918"], kicker="REVOLUTION", size=90)))
    at(13, Photo(["Nationalversammlung"], "National Assembly, Weimar · 1919", Card(["Article 1", "The German Reich", "is a republic."], kicker="WEIMAR CONSTITUTION · 11 AUGUST 1919", bg="paper", size=76)),
       Photo(["Erzberger"], "Matthias Erzberger, signed the 1918 armistice", Card(["The Weimar Republic"], kicker="1919", size=80)))
    at(14, Clip(N, 136.5, "First World War graves"), Card(["Defeat.", "Humiliation.", "Weakness."], accent=1))
    at(15, Photo(["R01217"], "Paris Peace Conference · treaty signing, 1919", Card(["Treaty of Versailles"], kicker="28 JUNE 1919", size=84)))
    at(16, Map("Lost territory", "TREATY OF VERSAILLES", mode="loss", cities=("Berlin", "Königsberg"), pulse=(), note="1914 German Empire vs. borders after 1920"))
    at(17, Photo(["Kapp"], "Kapp Putsch, Berlin · March 1920", Clip(P, 815.0, "Paramilitaries marching · newsreel")),
       Clip(P, 815.0, "Paramilitaries marching · newsreel"))
    at(18, Photo(["Erzberger"], "Matthias Erzberger, signed the armistice — murdered 1921", Card(["Betrayed?"], size=110)), Card(["„Im Felde unbesiegt“"], kicker="NATIONALIST SLOGAN", sub=["'Undefeated in the field'"], size=80))
    at(19, Card(["The stab-in-the-back myth"], kicker="A LIE", accent=0, size=80))
    # ---------------- 2 1919-1923
    at(20, Chapter("II", "1919", "The Nazi Movement"), Clip(N, 176.0, "Adolf Hitler · newsreel"))
    at(21, Map("Munich, 1919", "GERMAN WORKERS' PARTY", cities=("Munich", "Berlin", "Nuremberg"), pulse=("Munich",)), Clip(N, 176.0, "Adolf Hitler · newsreel"))
    at(22, Clip(P, 850.0, "SA man between party banners"), Clip(P, 761.0, "'Der Stürmer', antisemitic Nazi paper"))
    at(23, Clip(P, 1820.0, "Hitler speaking · newsreel"), Clip(P, 743.0, "Hitler speaking · newsreel"))
    at(24, Card(["NSDAP"], kicker="1920", sub=["National Socialist", "German Workers' Party"], size=150))
    at(25, Clip(N, 1080.0, "Hitler at a rally · newsreel"), Clip(N, 411.0, "Hitler · newsreel"), Clip(N, 180.0, "Crowd giving the Nazi salute"))
    at(26, Card(["Jews. Marxists.", "Democrats."], kicker="HIS SCAPEGOATS", size=90))
    at(27, Clip(P, 761.0, "'Der Stürmer', antisemitic Nazi paper"), Card(["False.", "Antisemitic."], accent=1, size=110))
    at(28, Clip(P, 696.2, "Propaganda rally: 'Ein Volk, ein Reich, ein Führer'"))
    # ---------------- 3 1923-1925
    at(29, Chapter("III", "1923", "The Beer Hall Putsch"), Photo(["Hitlerputsch"], "Odeonsplatz, Munich · 9 Nov 1923", crowd))
    at(30, Lens())
    at(31, PhotoText(["Landsberg"], "Landsberg Prison", "Landsberg Prison · 1924", "1924", Card(["Landsberg Prison"], kicker="1924", sub=["Sentenced to 5 years · released after 9 months"], size=90)))
    at(32, Clip(P, 825.0, "Mein Kampf · book covers"))
    at(33, Card(["New strategy:", "power through", "elections."], accent=2, size=88))
    at(34, Clip(P, 1597.6, "Ballot marked 'Ja'"))
    at(35, Clip(P, 815.0, "SA stormtroopers · newsreel"))
    at(36, Clip(P, 1200.0, "SA and SS formations · newsreel"), Clip(N, 127.0, "Party band, Nuremberg rally"))
    # ---------------- 4 1924-1932
    at(37, Chapter("IV", "1924", "The Golden Twenties"), Photo(["Stresemann"], "Gustav Stresemann, foreign minister", Card(["The Golden Twenties"], kicker="1924–1929", size=80)))
    at(38, Counter("MAY 1928 · NSDAP", 0, 2.6, lambda v: f"{v:.1f} %", ["A fringe party"]))
    at(39, Card(["1929"], size=200, accent=0))
    at(40, Photo(["Bankenkrise"], "Bank run · 1931 banking crisis", Card(["Wall Street", "crash"], kicker="OCTOBER 1929", accent=1, size=96)))
    at(41, Photo(["Arbeitslose", "Berlin"], "Unemployed in Berlin", crowd))
    at(42, Photo(["Bankenkrise"], "Banking crisis · July 1931", Card(["Banks failed."], size=100)))
    at(43, Counter("UNEMPLOYED IN GERMANY", 0, 6000000, fmt_int, ["registered, early 1932"], photo_keys=["Arbeitslose"]))
    at(44, Still(RD.still_unemployment), FX(DF3.d24_rain, "rain"))
    at(45, Photo(["Hindenburg"], "President Paul von Hindenburg", Card(["Article 48"], kicker="RULE BY EMERGENCY DECREE", size=110)),
       Photo(["Brüning"], "Chancellor Heinrich Brüning", Card(["Article 48"], kicker="RULE BY EMERGENCY DECREE", size=110)))
    at(46, Clip(N, 99.0, "Nazi rally · newsreel"))
    at(47, Clip(P, 790.0, "Labour service crews · mid-1930s"), Card(["Work. Bread.", "Strong leadership."], kicker="NAZI PROMISES", size=84))
    at(48, Photo(["Straßenkampf"], "Street clashes in Berlin", Clip(P, 815.0, "SA stormtroopers · newsreel")), Clip(P, 817.0, "SA stormtroopers · newsreel"))
    at(49, Clip(P, 771.0, "Joseph Goebbels, propaganda chief"), Clip(P, 1036.0, "Goebbels at the microphone"), Clip(P, 759.0, "'Der Angriff', Nazi newspaper"))
    at(50, Clip(P, 864.0, "Mass rally · newsreel"))
    at(51, Clip(P, 696.2, "Mass rally · newsreel"))
    # ---------------- 5 elections
    bars = Bars([RD.T(NI(53)) + 1.5, RD.T(NI(54)) + 2.0, RD.T(NI(56)) + 2.0], RD.T(NI(53)))
    at(52, Clip(N, 174.0, "Hitler at a rally · 1930s"), Photo(["Lustgarten"], "Election rally, Berlin Lustgarten", Clip(P, 864.0, "Election rally crowd")))
    at(53, bars)
    at(55, Card(["No majority."], accent=0, size=110))
    at(56, bars)
    at(57, Still(DF.d06_hemicycle))
    at(58, Card(["Behind", "closed doors."], size=100))
    # ---------------- 6 the deal
    at(59, Photo(["Papen"], "Franz von Papen", Clip(N, 182.0, "Hitler with SA leaders")), Card(["The conservative elites"], kicker="JANUARY 1933", size=80))
    at(60, Photo(["Papen"], "Former Chancellor Franz von Papen", Card(["Franz von Papen"], kicker="FORMER CHANCELLOR", size=90)))
    at(61, Photo(["Kabinett"], "Hitler's cabinet · 30 Jan 1933", Card(["3 of 11"], kicker="HITLER'S CABINET", sub=["Only three Nazis"], size=170)))
    at(62, Card(["3 of 11"], kicker="HITLER'S CABINET", sub=["Only three Nazis — the rest", "conservatives who thought", "they could control him."], size=170))
    at(63, Photo(["Hindenburg"], "President Paul von Hindenburg", Card(["13 August 1932"], kicker="HINDENBURG REFUSES HITLER", size=90)))
    at(64, Anim(lambda: VT.MapScene(RD.load_maps(os.path.join(RD.GEO_DIR, "world_1930.geojson"), os.path.join(RD.GEO_DIR, "modern.geojson"))[0])))
    at(66, PhotoText(["Fackelzug"], "30 January 1933", "SA torchlight parade, Berlin · 30 Jan 1933", "APPOINTED, NOT ELECTED", crowd))
    at(67, Photo(["Fackelzug"], "Torchlight parade through Berlin", crowd, pan=-1))
    # ---------------- 7 fire and fear
    at(68, Still(DF2.d18_52days))
    at(69, FX(DF2.d15_fire, "embers", 0.07, (W / 2, 900)), FX(DF3.d25_burn, "embers"))
    at(70, FX(DF3.d22_projector, "dust"), Card(["A communist plot?"], kicker="NAZI CLAIM", size=90))
    at(71, Still(DF.d08_document))
    at(72, Card(["Civil liberties", "suspended."], accent=1, size=90))
    at(73, Photo(["Hilfspolizei"], "SA as auxiliary police · 1933", Clip(P, 1200.0, "SA and SS · newsreel")))
    at(74, PhotoText(["Polizeipatrouille"], "5 March 1933", "Police and SA patrol · election day", "ELECTION UNDER TERROR", crowd))
    at(75, Counter("MARCH 1933 · NSDAP", 0, 43.9, lambda v: f"{v:.1f} %", ["Still no majority of its own"]))
    at(76, Clip(P, 745.0, "The Reichstag under Nazi rule"), Card(["Rule without", "parliament."], accent=1, size=100))
    # ---------------- 8 enabling act
    at(77, Photo(["Ermächtigungsgesetz"], "Hitler before the Reichstag · 23 Mar 1933", crowd), Clip(P, 745.0, "The Reichstag under Nazi rule"))
    at(78, Anim(lambda: VT.CrackScene()))
    at(80, Card(["Communist deputies:", "arrested or excluded."], size=72))
    at(81, FX(DF3.d23_halftone, "dust"), Still(DF.d10_vote, push=0.04))
    at(83, Counter("ENABLING ACT · 23 MARCH 1933", 0, 444, lambda v: f"{int(v)} : 94", ["The act passed"], color=PAPER))
    at(84, Clip(P, 741.0, "Reichstag deputies · 1930s"))
    at(85, Clip(P, 1200.0, "SA and SS · newsreel"), Clip(P, 856.0, "Rally hall · newsreel"))
    # ---------------- 9 forced into line
    at(86, FX(DF2.d14_gleichschaltung, "dust", 0.04))
    at(87, Photo(["Gewerkschaft"], "Trade union building occupied · 2 May 1933", Card(["2 May 1933"], kicker="TRADE UNIONS SMASHED", size=100)))
    at(88, Card(["One party."], kicker="14 JULY 1933", accent=0, size=120))
    at(89, Clip(P, 1610.0, "Book burning · 1933"), Photo(["Bücherverbrennung"], "Book burning · 10 May 1933", Clip(P, 1608.0, "Book burning · 1933")))
    at(90, Clip(P, 777.0, "'Volksgericht' – the Nazi People's Court"))
    at(91, FX(DF3.d27_dossier, "dust"), Photo(["Dachau"], "SS guard unit, Dachau · 1933", crowd))
    at(92, Photo(["Boykott"], "Boycott of Jewish businesses · 1 Apr 1933", Card(["Boycott"], kicker="1 APRIL 1933", sub=["of Jewish businesses"], size=130)))
    # ---------------- 10 1934
    at(93, Chapter("V", "1934", "The Dictator"), Clip(N, 421.0, "Hitler with SA men · newsreel"))
    at(94, Photo(["Röhm"], "SA chief Ernst Röhm", Card(["The Night of the", "Long Knives"], kicker="30 JUNE 1934", size=84)))
    at(95, Clip(P, 914.0, "US newspaper, July 1934: 'Roehm Assassinated in Nazi Purge'"), Clip(P, 878.0, "US newspaper, 1934: 'Hitler Claims Revolt Is Crushed'"),
       Clip(P, 874.0, "US newspaper, 1934: 'Hitler Executes More Anti-Nazi Leaders'"))
    at(96, Photo(["Beisetzung"], "Hindenburg's funeral · August 1934", Photo(["Hindenburg"], "President Paul von Hindenburg", Card(["2 August 1934"], kicker="HINDENBURG DIES", size=100))))
    at(97, Clip(P, 1824.0, "Hitler · newsreel"))
    at(98, FX(DF3.d29_searchlights, "dust"))
    at(99, Photo(["Vereidigung"], "Soldiers swear the oath to Hitler · 1934", Clip(P, 1305.0, "German soldiers · newsreel")))
    at(100, Anim(lambda: VT.FinalScene()))
    # ---------------- 11 why
    at(101, Card(["Not inevitable."], accent=0, size=104))
    at(102, PhotoText(["Arbeitslose"], "Economic catastrophe", "Unemployed dockworkers, Hamburg · 1931", None, crowd))
    at(103, Clip(P, 741.0, "Divided Reichstag"))
    at(104, Clip(P, 1036.0, "Goebbels at the microphone"))
    at(105, Clip(P, 761.0, "'Der Stürmer', antisemitic Nazi paper"))
    at(106, Clip(P, 815.0, "SA stormtroopers"))
    at(107, Card(["Democrats who", "did not defend", "the republic"], size=80))
    at(108, Photo(["Rundfunk"], "Hitler at a radio microphone · 1 Feb 1933", crowd), FX(DF3.d28_double, "dust"))
    at(109, Photo(["Tag von Potsdam"], "Hitler and Hindenburg · 21 Mar 1933", crowd))
    at(110, Photo(["Wahlplakat"], "Nazi poster, Nov 1933: 'The Marshal and the Corporal'", crowd))
    at(111, Card(["Instead…"], size=110))
    at(112, FX(DF3.d30_split, "dust"))
    # ---------------- 12 consequences
    at(113, Clip(P, 2260.0, "Wehrmacht parade · late 1930s"), Clip(N, 415.0, "Nuremberg rally · 1930s"))
    at(114, Card(["The Holocaust"], size=110))
    at(115, Card(["Six million", "Jews murdered."], size=96))
    at(116, Card(["Millions of", "other victims."], size=96))
    at(117, Card(["Democracy can be", "weakened", "step by step."], accent=2, size=86))
    at(118, FX(DF2.d13_crack, "dust", 0.05, (560, 820)))
    at(119, Clip(P, 739.0, "The Reichstag chamber"))
    at(120, Map("Germany, 1933", "A DEMOCRACY DESTROYED", cities=("Berlin",), pulse=("Berlin",)))
    at(121, Card(["A democracy", "destroyed."], size=96, accent=1))
    at(122, Card(["A dictatorship", "established."], size=96))
    at(123, Clip(N, 99.0, "Nuremberg rally grounds"))
    at(124, Card(["How Hitler", "Came to Power"], kicker="1918 – 1934", size=110,
                  sub=["Archive: Bundesarchiv (CC BY-SA 3.0 DE) · US War Dept. films (public domain)",
                       "Speech audio: British Pathé, film ID 604.06"]))
    # ---- lines restored from the full script (indices in the full ElevenLabs timing)
    def atn(j, *shots):
        a, b = RD.T(j), line_end(j)
        for k, sh in enumerate(shots):
            S.append((a + (b - a) * k / len(shots), sh))

    atn(10, Clip(P, 745.0, "The Reichstag under Nazi rule"))
    atn(11, Clip(P, 2262.0, "Wehrmacht parade · late 1930s"))
    atn(14, Clip(N, 136.5, "First World War graves"), Photo(["Wilhelm II"], "Kaiser Wilhelm II", Clip(N, 66.5, "Kaiser Wilhelm II")))
    atn(20, Counter("REPARATIONS · LONDON SCHEDULE 1921", 0, 132, lambda v: f"{int(v)} bn", ["gold marks demanded"]))
    atn(24, Card(["A lie used against", "democracy."], accent=0, size=80))
    atn(26, Card(["1914 – 1918"], kicker="CORPORAL HITLER", sub=["Bavarian army, Western Front"], size=110))
    atn(31, Clip(P, 1823.0, "Hitler speaking · newsreel"))
    atn(41, Card(["Not by force", "alone."], size=96))
    atn(53, Clip(P, 741.0, "Reichstag deputies · early 1930s"))
    atn(54, Card(["March 1930"], kicker="THE LAST MAJORITY GOVERNMENT FALLS", size=110))
    atn(55, Clip(P, 739.0, "The Reichstag chamber"))
    atn(59, Clip(P, 817.0, "SA stormtroopers · newsreel"))
    atn(62, Card(["Workers. Farmers.", "Business owners.", "The unemployed."], size=78), Clip(P, 866.0, "Mass rally · newsreel"))
    atn(77, Card(["Deadlock."], size=120))
    atn(82, Photo(["Tag von Potsdam"], "Hitler and Hindenburg · 21 Mar 1933", crowd))
    atn(83, Card(["They badly", "underestimated him."], accent=1, size=84))
    atn(89, Photo(["Hilfspolizei"], "SA as auxiliary police · 1933", Clip(P, 817.0, "SA men · newsreel")))
    atn(91, Card(["Newspapers", "banned."], accent=1, size=110))
    atn(92, Card(["„Schutzhaft“"], kicker="'PROTECTIVE CUSTODY'", sub=["Prison without trial"], size=110))
    atn(93, Clip(P, 1814.0, "Rally crowd · 1933"))
    atn(101, Clip(P, 741.0, "Reichstag deputies · 1933"))
    atn(106, Card(["Not truly", "democratic."], accent=1, size=100))
    atn(115, Clip(N, 99.0, "Nuremberg rally grounds"))
    atn(131, Card(["One decision."], accent=0, size=110))
    S.sort(key=lambda x: x[0])
    return S


RD.build_shots = build_shots

if __name__ == "__main__":
    RD.main()
