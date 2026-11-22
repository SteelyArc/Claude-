"""Main documentary body renderer (after the opening).

Timeline is driven by the narration timing JSON (one entry per spoken line).
Each shot starts at the start of a narration line and lasts until the next shot.

python3 render_doc.py plan                       -> print the shot list with times
python3 render_doc.py frames <out.png>           -> contact sheet preview (one frame per shot)
python3 render_doc.py render <worker> <nworkers> <out_dir>   -> render a slice to <out_dir>/part_XX.mp4
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import design_frames as DF
import design_frames_2 as DF2

DF.label_footer = lambda *a, **k: None
DF2.footer = lambda *a, **k: None
from design_frames import (CITIES, DIM, H, INK, MONO, MONO_L, PAPER, RED, SANS, SANS_B, SERIF, SERIF_B, SERIF_I, W,
                           MapProj, dashed, font, load_maps, rings, text_c, wrap)
from design_frames_2 import GOLD, germany_rings, light_rays
import visual_test as VT
from visual_test import GRAIN, VIG, clamp, ease, ease_out

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCR = os.environ.get("SCRATCH", "/tmp")
GEO_DIR = os.path.join(SCR, "dl")
FPS = 30
NAR0 = float(os.environ.get("NAR0", "31.0"))
TIMING = json.load(open(os.path.join(ROOT, "audio", "narration_lewis_timing.json")))
FILM_P = os.path.join(ROOT, "archive", "film", "Why_We_Fight.1.Prelude_to_War.webm.480p.vp9.webm")
FILM_N = os.path.join(ROOT, "archive", "film", "Why_We_Fight.2.The_Nazis_Strike.webm.480p.vp9.webm")
PHOTOS = os.path.join(ROOT, "archive", "photos")
CREDIT_P = "Film: 'Prelude to War' (US War Dept., 1942) · public domain"
CREDIT_N = "Film: 'The Nazis Strike' (US War Dept., 1943) · public domain"
SAFE_X0, SAFE_X1 = 64, 936
RNG = np.random.default_rng(11)

SECTIONS = [
    "GERMANY · 1933",
    "1918–1919 · DEFEAT AND REVOLUTION",
    "1919–1923 · THE NAZI MOVEMENT",
    "1923–1925 · PUTSCH AND PRISON",
    "1924–1932 · THE GREAT DEPRESSION",
    "1930–1932 · THE ELECTIONS",
    "JANUARY 1933 · THE DEAL",
    "FEBRUARY–MARCH 1933 · FIRE AND FEAR",
    "23 MARCH 1933 · THE ENABLING ACT",
    "1933 · FORCED INTO LINE",
    "1934 · THE DICTATOR",
    "WHY IT HAPPENED",
    "THE CONSEQUENCES",
]


def T(i):
    return NAR0 + TIMING[i]["start"]


# ------------------------------------------------------------------ cropped layers (memory-friendly)
class Layer:
    def __init__(self, draw_fn, glow=0, y0=0, y1=H):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(lay))
        if glow:
            g = lay.filter(ImageFilter.GaussianBlur(glow))
            lay = Image.alpha_composite(Image.alpha_composite(Image.new("RGBA", (W, H)), g), lay)
        a = np.asarray(lay, np.float32)[y0:y1] / 255
        self.rgb = a[..., :3] * a[..., 3:] * 255
        self.a = a[..., 3:]
        self.y0, self.y1 = y0, y1

    def comp(self, f, k=1.0):
        if k <= 0.002:
            return f
        sl = f[self.y0:self.y1]
        f[self.y0:self.y1] = sl * (1 - self.a * k) + self.rgb * k
        return f


def bbox_layer(draw_fn, glow=0):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    bb = lay.getbbox() or (0, 0, 1, 1)
    pad = glow * 3 + 4
    return Layer(draw_fn, glow, max(0, bb[1] - pad), min(H, bb[3] + pad))


# ------------------------------------------------------------------ assets
def find_photo(*keys):
    cpath = os.path.join(PHOTOS, "credits.json")
    if not os.path.exists(cpath):
        return None
    for c in json.load(open(cpath)):
        if all(k.lower() in c["title"].lower() for k in keys) and os.path.exists(os.path.join(PHOTOS, c["file"])):
            try:
                Image.open(os.path.join(PHOTOS, c["file"])).verify()
            except Exception:  # noqa: BLE001
                continue
            sig = c["title"].replace("File:Bundesarchiv ", "").split(",")[0]
            artist = c["artist"]
            for junk in ("Unknown authorUnknown author", "UnknownUnknown", "Unknown author"):
                artist = artist.replace(junk, "unknown")
            lic = c["licence"] or "CC BY-SA 3.0 DE"
            return os.path.join(PHOTOS, c["file"]), f"Photo: Bundesarchiv, {sig} / {artist} / {lic}"
    return None


_clip_cache = {}


def read_clip(path, start, dur):
    key = (path, start, round(dur, 2))
    if key not in _clip_cache:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-t", str(dur + 0.3), "-i", path,
                              "-vf", f"fps={FPS},scale=640:480", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        n = len(raw) // (640 * 480 * 3)
        _clip_cache.clear()
        _clip_cache[key] = [np.frombuffer(raw, np.uint8, 640 * 480 * 3, i * 640 * 480 * 3).reshape(480, 640, 3) for i in range(n)]
    return _clip_cache[key]


BOX_TOP, BOX_H = 270, 880


def feather(w, h, f=70):
    m = np.ones((h, w), np.float32)
    r = np.linspace(0, 1, f)
    m[:f] *= r[:, None]
    m[-f:] *= r[::-1][:, None]
    return Image.fromarray((m * 255).astype(np.uint8))


def media_frame(src, t, push=0.08, pan=0.0, film=False, idx=0):
    src = src.convert("RGB")
    bg = src.resize((54, 96), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BICUBIC)
    bg = Image.eval(bg, lambda v: int(v * 0.32))
    sw, sh = src.size
    scale = (BOX_H / sh) if sh > sw else (W / sw)
    scale *= 1.0 + push * ease(t)
    nw, nh = int(sw * scale), int(sh * scale)
    img = src.resize((nw, nh), Image.BICUBIC)
    ox = (W - nw) / 2 + pan * ease(t) * 50
    oy = BOX_TOP + (BOX_H - nh) / 2
    if film:
        ox += RNG.uniform(-1.4, 1.4)
        oy += RNG.uniform(-1.4, 1.4)
    bg.paste(img, (int(ox), int(oy)), feather(nw, nh))
    f = np.asarray(bg, np.float32).copy()
    if film:
        f *= 0.95 + 0.05 * math.sin(idx * 2.7) + RNG.normal(0, 0.01)
    return f


# ------------------------------------------------------------------ shot types
class Shot:
    label = None
    credit = None
    zoom = (1.0, 1.0)
    center = (W / 2, H / 2)

    def prepare(self):
        pass

    def frame(self, t, dur, idx):  # t in 0..1
        raise NotImplementedError


class Clip(Shot):
    def __init__(self, film, start, label, credit=None):
        self.film, self.start, self.label = film, start, label
        self.credit = credit or (CREDIT_P if film == FILM_P else CREDIT_N)

    def frame(self, t, dur, idx):
        frames = read_clip(self.film, self.start, dur)
        fr = frames[min(int(t * dur * FPS), len(frames) - 1)]
        return media_frame(Image.fromarray(fr), t, push=0.06, film=True, idx=idx)


class Photo(Shot):
    def __init__(self, keys, label, fallback=None, pan=1):
        self.keys, self.label, self.fallback, self.pan = keys, label, fallback, pan
        self.found = find_photo(*keys)
        if self.found:
            self.credit = self.found[1]
        elif fallback is not None:
            self.label, self.credit = fallback.label, fallback.credit

    def frame(self, t, dur, idx):
        if not self.found:
            return self.fallback.frame(t, dur, idx)
        if not hasattr(self, "_img"):
            self._img = Image.open(self.found[0]).convert("RGB")
        return media_frame(self._img, t, push=0.10, pan=self.pan)


class Still(Shot):
    """Full-frame design image with slow push."""

    def __init__(self, make, label=None, push=0.05, center=(W / 2, H / 2)):
        self.make, self.label, self.push, self.center = make, label, push, center

    def frame(self, t, dur, idx):
        if not hasattr(self, "_arr"):
            self._arr = np.asarray(self.make().convert("RGB"), np.float32)
        self.zoom = (1.0, 1.0 + self.push)
        return self._arr.copy()


class Anim(Shot):
    """Wrap visual_test scenes (they return finished PIL images)."""

    def __init__(self, factory, label=None):
        self.factory, self.label = factory, label

    def frame(self, t, dur, idx):
        if not hasattr(self, "_obj"):
            self._obj = self.factory()
        return np.asarray(self._obj.frame(t, idx).convert("RGB"), np.float32)


class Card(Shot):
    """Kinetic typography card."""

    def __init__(self, lines, kicker=None, accent=None, sub=None, bg="dark", size=96):
        self.lines, self.kicker, self.accent, self.sub, self.bgk, self.size = lines, kicker, accent, sub, bg, size

    def prepare(self):
        if hasattr(self, "_base"):
            return
        if self.bgk == "paper":
            base = np.zeros((H, W, 3), np.float32) + np.array([226, 218, 198], np.float32)
            col = INK
        else:
            base = np.zeros((H, W, 3), np.float32) + np.array([10, 10, 11], np.float32)
            base = base + light_rays((W, H), (W / 2, -100), (150, 140, 120), 0.45, seed=len(self.lines[0]))
            col = PAPER
        self._base = base
        size = self.size
        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        while size > 40 and max(probe.textlength(ln, font=font(SERIF_B, size)) for ln in self.lines) > 900:
            size -= 4
        self.size = size
        fo = font(SERIF_B, self.size)
        y = 820 - (len(self.lines) * self.size * 1.15) / 2
        self._lines = []
        for i, ln in enumerate(self.lines):
            c = (220, 70, 55) if self.accent == i else col
            yy = y + i * self.size * 1.15
            self._lines.append(bbox_layer(lambda d, ln=ln, yy=yy, c=c: text_c(d, yy, ln, fo, c, w=1000), glow=10 if self.bgk != "paper" else 0))
        self._kick = bbox_layer(lambda d: text_c(d, y - 70, self.kicker, font(MONO, 30), GOLD, w=1000)) if self.kicker else None
        endy = y + len(self.lines) * self.size * 1.15 + 30
        ssize = 38
        while self.sub and ssize > 18 and max(probe.textlength(x, font=font(SERIF_I, ssize)) for x in self.sub) > 900:
            ssize -= 2
        self._sub = bbox_layer(lambda d: [text_c(d, endy + j * (ssize + 8), s, font(SERIF_I, ssize), DIM if self.bgk != "paper" else (80, 74, 66), w=1000)
                                          for j, s in enumerate(self.sub)]) if self.sub else None

    def frame(self, t, dur, idx):
        self.prepare()
        f = self._base.copy()
        T = t * dur
        if self._kick:
            f = self._kick.comp(f, ease(T / 0.4))
        for i, L in enumerate(self._lines):
            f = L.comp(f, ease((T - 0.15 - i * 0.25) / 0.45))
        if self._sub:
            f = self._sub.comp(f, ease((T - 0.6 - len(self._lines) * 0.25) / 0.5))
        self.zoom = (1.0, 1.03)
        return f


class Chapter(Card):
    def __init__(self, num, years, title):
        super().__init__([years], kicker=f"CHAPTER {num}", sub=[title], size=130)


class Map(Shot):
    """Germany map: mode 'loss' (1914 vs 1920 borders) or 'city' (pulse on cities)."""

    def __init__(self, title, kicker, mode="city", cities=("Berlin",), pulse=("Berlin",), note=None):
        self.title, self.kicker, self.mode, self.cities, self.pulse, self.note = title, kicker, mode, cities, pulse, note

    def prepare(self):
        if hasattr(self, "_base"):
            return
        geo, _ = load_maps(os.path.join(GEO_DIR, "world_1930.geojson"), os.path.join(GEO_DIR, "modern.geojson"))
        img = Image.new("RGB", (W, H), (9, 11, 15))
        d = ImageDraw.Draw(img, "RGBA")
        proj = MapProj(4.5, 24.0, 46.0, 56.4, (30, 420, 1050, 1180))
        self.proj = proj
        for n, rs in geo.items():
            if n in ("Germany", "East Prussia"):
                continue
            for r in rs:
                d.polygon([proj(*p) for p in r], fill=(24, 28, 34), outline=(48, 54, 62))
        if self.mode == "loss":
            emp = [f for f in json.load(open(os.path.join(GEO_DIR, "world_1914.geojson")))["features"]
                   if f["properties"].get("NAME") == "German Empire"][0]
            for r in rings(emp["geometry"]):
                d.polygon([proj(*p) for p in r], fill=(150, 40, 32))
        for r in germany_rings(geo):
            pts = [proj(*p) for p in r]
            d.polygon(pts, fill=(92, 84, 70))
            d.line(pts + [pts[0]], fill=GOLD, width=3)
        for c in self.cities:
            x, y = proj(*CITIES[c])
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=PAPER)
            d.text((x + 14, y - 17), c, font=font(SANS_B if c in self.pulse else SANS, 32 if c in self.pulse else 26), fill=PAPER)
        d.text((SAFE_X0, 250), self.kicker, font=font(MONO, 28), fill=GOLD)
        d.text((SAFE_X0, 292), self.title, font=font(SERIF_B, 70), fill=PAPER)
        if self.mode == "loss":
            d.rectangle([SAFE_X0, 1180, SAFE_X0 + 40, 1206], fill=(150, 40, 32))
            d.text((SAFE_X0 + 56, 1176), "Lost after 1919 (Treaty of Versailles)", font=font(SANS, 28), fill=PAPER)
        if self.note:
            d.text((SAFE_X0, 1478), self.note, font=font(MONO_L, 19), fill=(165, 158, 145))
        self._base = np.asarray(img, np.float32)

    def frame(self, t, dur, idx):
        self.prepare()
        f = self._base.copy()
        img = Image.fromarray(f.astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        T = t * dur
        for c in self.pulse:
            x, y = self.proj(*CITIES[c])
            for i in range(3):
                ph = (T * 0.7 + i / 3) % 1
                r = 14 + 90 * ph
                d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 200, 120, int(220 * (1 - ph))), width=3)
        if self.mode == "loss":
            # blink the lost territory lightly
            pass
        self.zoom = (1.0, 1.08)
        if self.pulse:
            self.center = self.proj(*CITIES[self.pulse[0]])
        return np.asarray(img, np.float32)


class Bars(Shot):
    """Election bars that rise when each result is spoken (times absolute)."""

    data = [("1928", 2.6), ("Sep 1930", 18.3), ("Jul 1932", 37.3), ("Nov 1932", 33.1)]

    def __init__(self, cue_abs, shot_start):
        self.cue = cue_abs
        self.s0 = shot_start
        self.label = "Reichstag elections · NSDAP share of the vote"
        self.zoom = (1.0, 1.07)
        self.center = (W / 2, 800)

    def prepare(self):
        if hasattr(self, "_base"):
            return
        img = Image.new("RGB", (W, H), (14, 14, 16))
        f = np.asarray(img, np.float32) + light_rays((W, H), (W / 2, 260), (120, 110, 100), 0.35, seed=9)
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(-10, 11):
            d.line([(W / 2 + i * 40, 1110), (W / 2 + i * 220, 1500)], fill=(70, 66, 60, 50), width=1)
        d.text((SAFE_X0, 250), "REICHSTAG ELECTIONS", font=font(MONO, 28), fill=GOLD)
        d.text((SAFE_X0, 292), "NSDAP share of the vote", font=font(SERIF_B, 64), fill=PAPER)
        self._base = img

    def frame(self, t, dur, idx):
        self.prepare()
        img = self._base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        now = self.s0 + t * dur
        x0, bw, gap, scale, base = 90, 150, 62, 13, 1110
        my = base - 50 * scale
        d.polygon([(60, my), (960, my), (990, my - 22), (90, my - 22)], fill=(163, 39, 31, 70), outline=(200, 60, 50, 220))
        d.text((70, my - 62), "50 % · majority", font=font(MONO, 26), fill=(230, 110, 95))
        for i, (lab, v) in enumerate(self.data):
            p = 1.0 if i == 0 else ease_out((now - self.cue[i - 1]) / 1.2)
            x = x0 + i * (bw + gap)
            h = max(v * scale * p, 2)
            hi = 1.0 if i == 2 else 0.8
            c = DF.PARTY["NSDAP"]
            DF2.iso_prism(d, x, base, bw, h, tuple(int(q * hi * 1.5) for q in c), tuple(int(q * hi) for q in c),
                          tuple(int(q * hi * 0.6) for q in c), depth=36)
            s = f"{v * p:.1f} %"
            fo = font(SERIF_B, 46 if i == 2 else 38)
            d.text((x + bw / 2 - d.textlength(s, font=fo) / 2 + 14, base - h - 86), s, font=fo, fill=PAPER + (int(255 * clamp(p * 3)),))
            d.text((x + bw / 2 - d.textlength(lab, font=font(MONO, 24)) / 2, base + 24), lab, font=font(MONO, 24), fill=DIM)
        return np.asarray(img, np.float32)


# ------------------------------------------------------------------ design stills (reuse chosen designs)
def still_unemployment():
    img = DF.d07_unemployment()
    p = find_photo("Arbeitslose")
    if p:
        ph = Image.open(p[0]).convert("RGB")
        sc = 1080 / ph.width
        ph = ph.resize((1080, int(ph.height * sc)))
        top = ph.crop((0, 0, 1080, min(760, ph.height)))
        img.paste(top, (0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(260):
            d.line([(0, 760 - i), (W, 760 - i)], fill=(20, 19, 18, int(255 * (1 - i / 260) ** 1.4)))
        d.text((60, 640), "UNEMPLOYED IN GERMANY", font=font(MONO, 28), fill=DIM)
        d.text((60, 690), "≈ 6 million", font=font(SERIF_B, 110), fill=PAPER)
        d.rectangle([0, 1440, W, 1500], fill=(20, 19, 18))
    return img


def build_shots():
    S = []

    def add(line, shot, section_override=None):
        S.append((T(line), shot))

    P, N = FILM_P, FILM_N
    fallback_crowd = Clip(P, 1810.0, "Crowd at a Nazi rally · 1930s")
    # ---- section 0: intro
    add(0, Map("Germany, 1933", "A NATION IN CRISIS", cities=("Berlin", "Munich", "Hamburg", "Nuremberg", "Königsberg"),
               pulse=("Berlin",), note="Borders of 1933"))
    add(1, Clip(P, 1810.0, "Crowds in the 1930s"))
    add(2, Clip(P, 726.0, "The Reichstag, Berlin"))
    add(3, Clip(P, 684.6, "Adolf Hitler · newsreel"))
    add(4, Clip(N, 105.0, "Nazi Party rally, Nuremberg · 1930s"))
    add(5, Card(["Not through", "one election."]))
    add(6, Card(["Not through one", "sudden revolution."]))
    add(7, Photo(["Hamburg", "Arbeitslose"], "Unemployed dockworkers, Hamburg · 1931", fallback_crowd))
    add(8, Photo(["Hindenburg"], "President Paul von Hindenburg", Clip(P, 1820.0, "Hitler addressing a crowd")))
    add(9, Card(["They were wrong."], accent=0))
    # ---- section 1: 1918-1919
    add(10, Chapter("I", "1918", "Defeat and Revolution"))
    add(11, Card(["11 November 1918"], kicker="ARMISTICE", sub=["Germany has lost the First World War."], size=84))
    add(12, Photo(["Wilhelm II"], "Kaiser Wilhelm II", Card(["The Kaiser abdicates."], kicker="9 NOVEMBER 1918", size=84)))
    add(13, Photo(["Nationalversammlung"], "National Assembly, Weimar · 1919",
                  Card(["Article 1", "The German Reich", "is a republic."], kicker="WEIMAR CONSTITUTION · 11 AUGUST 1919", bg="paper", size=76)))
    add(14, Card(["Defeat.", "Humiliation.", "Weakness."], accent=1))
    add(15, Photo(["Versailles"], "Treaty of Versailles · 28 June 1919",
                  Card(["Treaty of Versailles"], kicker="28 JUNE 1919", sub=["Territory · Army limits · Reparations"], size=84)))
    add(16, Map("Lost territory", "TREATY OF VERSAILLES", mode="loss", cities=("Berlin", "Königsberg"), pulse=(),
                note="1914 German Empire vs. borders after 1920"))
    add(17, Clip(P, 810.0, "Nazi paramilitaries marching · 1930s"))
    add(18, Card(["„Im Felde unbesiegt“"], kicker="NATIONALIST SLOGAN", sub=["'Undefeated in the field'"], size=80))
    add(19, Card(["The stab-in-the-back myth"], kicker="A LIE", accent=0, size=80))
    # ---- section 2
    add(20, Chapter("II", "1919", "The Nazi Movement"))
    add(21, Map("Munich, 1919", "GERMAN WORKERS' PARTY", cities=("Munich", "Berlin", "Nuremberg"), pulse=("Munich",)))
    add(22, Clip(P, 840.0, "Nazi supporters · newsreel"))
    add(23, Clip(P, 1820.0, "Hitler speaking · newsreel"))
    add(24, Card(["NSDAP"], kicker="1920", sub=["National Socialist", "German Workers' Party"], size=150))
    add(25, Clip(N, 1080.0, "Hitler at a rally · newsreel"))
    add(26, Card(["Jews. Marxists.", "Democrats."], kicker="HIS SCAPEGOATS", size=90))
    add(27, Card(["False.", "Antisemitic."], accent=1, size=110))
    add(28, Clip(P, 696.2, "Propaganda rally: 'Ein Volk, ein Reich, ein Führer'"))
    # ---- section 3
    add(29, Photo(["Hitlerputsch"], "Beer Hall Putsch, Munich · 9 Nov 1923",
                  Chapter("III", "1923", "The Beer Hall Putsch")))
    add(30, Card(["The coup failed."], kicker="MUNICH · 9 NOVEMBER 1923", sub=["4 police officers and 16 putschists killed"], size=90))
    add(31, Card(["Landsberg Prison"], kicker="1924", sub=["Sentenced to 5 years · released after 9 months"], size=90))
    add(32, Clip(P, 1605.0, "Mein Kampf · book display"))
    add(33, Card(["New strategy:", "power through", "elections."], accent=2, size=88))
    add(35, Clip(P, 1597.6, "Ballot marked 'Ja'"))
    add(36, Clip(P, 1200.0, "SA and SS formations · newsreel"))
    # ---- section 4
    add(37, Chapter("IV", "1929", "The Great Depression"))
    add(38, Card(["2.6 %"], kicker="MAY 1928 · NSDAP", sub=["A fringe party"], size=170))
    add(40, Photo(["Börse"], "Berlin Stock Exchange", Card(["Wall Street", "crash"], kicker="OCTOBER 1929", accent=1, size=96)))
    add(41, Photo(["Hamburg", "Arbeitslose"], "Unemployed dockworkers, Hamburg · 1931", fallback_crowd, pan=-1))
    add(44, Still(still_unemployment, None))
    add(45, Photo(["Hindenburg"], "President Paul von Hindenburg",
                  Card(["Article 48"], kicker="RULE BY EMERGENCY DECREE", sub=["Parliament pushed aside"], size=110)))
    add(46, Clip(N, 105.0, "Nazi Party rally · newsreel"))
    add(47, Photo(["Wahlplakat", "NSDAP"], "NSDAP election poster", Card(["Work. Bread.", "Strong leadership."], kicker="NAZI PROMISES", size=84)))
    add(48, Clip(P, 810.0, "SA stormtroopers · newsreel"))
    add(49, Clip(P, 765.0, "Goebbels' Propaganda Ministry"))
    add(50, Clip(P, 696.2, "Mass rally · newsreel"))
    # ---- section 5
    bars = Bars([T(53) + 1.5, T(54) + 2.0, T(56) + 2.0], T(52))
    add(52, bars)
    add(57, Still(DF.d06_hemicycle))
    add(58, Card(["Behind", "closed doors."], size=100))
    # ---- section 6
    add(59, Photo(["Papen"], "Franz von Papen", Card(["The conservative elites"], kicker="JANUARY 1933", size=80)))
    add(61, Card(["3 of 11"], kicker="HITLER'S CABINET", sub=["Only three Nazis — the rest were conservatives", "who thought they could control him."], size=170))
    add(63, Photo(["Hindenburg"], "President Paul von Hindenburg",
                  Card(["13 August 1932"], kicker="HINDENBURG REFUSES HITLER", size=90)))
    add(64, Anim(lambda: VT.MapScene(load_maps(os.path.join(GEO_DIR, "world_1930.geojson"), os.path.join(GEO_DIR, "modern.geojson"))[0])))
    add(66, Photo(["Fackelzug"], "SA torchlight parade, Berlin · 30 Jan 1933",
                  Clip(N, 105.0, "Nazi rally · newsreel")))
    # ---- section 7
    add(68, Still(DF2.d18_52days))
    add(69, Still(DF2.d15_fire, push=0.07, center=(W / 2, 900)))
    add(70, Photo(["Reichstagsbrand"], "The burnt Reichstag · February 1933", Card(["A communist plot?"], kicker="NAZI CLAIM", size=90)))
    add(71, Still(DF.d08_document))
    add(74, Photo(["Polizeipatrouille"], "Police and SA patrol · election day, 5 Mar 1933", fallback_crowd))
    add(76, Card(["Rule without", "parliament."], accent=1, size=100))
    # ---- section 8
    add(77, Photo(["Ermächtigungsgesetz"], "Hitler before the Reichstag · 23 Mar 1933", fallback_crowd))
    add(78, Anim(lambda: VT.CrackScene()))
    add(80, Card(["Communist deputies:", "arrested or excluded."], size=72))
    add(81, Still(DF.d10_vote, push=0.04))
    add(84, Clip(P, 1200.0, "SA and SS · newsreel"))
    # ---- section 9
    add(86, Still(DF2.d14_gleichschaltung, push=0.04))
    add(89, Clip(P, 1610.0, "Book burning · 1933"))
    add(91, Photo(["Dachau"], "Dachau concentration camp · 1933",
                  Card(["Dachau"], kicker="22 MARCH 1933", sub=["One of the first concentration camps"], size=130)))
    add(92, Photo(["Boykott"], "Boycott of Jewish businesses · 1 Apr 1933",
                  Card(["Boycott"], kicker="1 APRIL 1933", sub=["Nazi boycott of Jewish businesses"], size=130)))
    # ---- section 10
    add(93, Chapter("V", "1934", "The Dictator"))
    add(94, Card(["The Night of the", "Long Knives"], kicker="30 JUNE – 2 JULY 1934", sub=["At least 85 people murdered"], size=84))
    add(96, Photo(["Hindenburg", "Beisetzung"], "Hindenburg's funeral · August 1934",
                  Photo(["Hindenburg"], "President Paul von Hindenburg", Card(["2 August 1934"], kicker="HINDENBURG DIES", size=100))))
    add(97, Clip(P, 1824.0, "Hitler · newsreel"))
    add(99, Clip(P, 1305.0, "German soldiers · newsreel"))
    add(100, Anim(lambda: VT.FinalScene()))
    # ---- section 11
    add(101, Card(["Not inevitable."], accent=0, size=104))
    add(102, Card(["Economic", "catastrophe"], size=92))
    add(103, Card(["Political", "division"], size=92))
    add(104, Card(["Extremist", "propaganda"], size=92))
    add(105, Card(["Antisemitism"], accent=0, size=92))
    add(106, Card(["Street", "violence"], size=92))
    add(107, Card(["Democrats who", "did not defend", "the republic"], size=80))
    add(108, Photo(["Rundfunk"], "Hitler at a radio microphone · 1 Feb 1933", fallback_crowd))
    add(111, Card(["Instead…"], size=110))
    add(112, Card(["They helped destroy", "the democracy they", "claimed to protect."], accent=1, size=74))
    # ---- section 12
    add(113, Clip(P, 2260.0, "Wehrmacht parade · late 1930s"))
    add(114, Card(["The Holocaust"], sub=["Six million Jews murdered", "Millions of other victims"], size=104))
    add(117, Card(["Democracy can be", "weakened", "step by step."], accent=2, size=86))
    add(119, Still(DF2.d13_crack, push=0.05, center=(560, 820)))
    add(120, Map("Germany, 1933", "A DEMOCRACY DESTROYED", cities=("Berlin",), pulse=("Berlin",)))
    add(124, Card(["How Hitler", "Came to Power"], kicker="1918 – 1934", size=110,
                  sub=["Archive: Bundesarchiv (CC BY-SA 3.0 DE) · US War Dept. films (public domain)",
                       "Speech audio: British Pathé, film ID 604.06"]))
    return S


def timeline():
    S = build_shots()
    end = NAR0 + TIMING[-1]["end"] + 1.6
    out = []
    for i, (s, shot) in enumerate(S):
        e = S[i + 1][0] if i + 1 < len(S) else end
        out.append((s, e, shot))
    return out, end


# ------------------------------------------------------------------ overlays
def section_of(tsec):
    sec = 0
    for l in TIMING:
        if NAR0 + l["start"] - 0.8 <= tsec:
            sec = l["section"]
    return sec


def make_overlays():
    tags = [bbox_layer(lambda d, s=s: (d.rounded_rectangle([SAFE_X0, 196, SAFE_X0 + 18 + d.textlength(s, font=font(MONO, 24)) + 18, 238], 6, fill=(20, 20, 22, 210)),
                                       d.rectangle([SAFE_X0, 196, SAFE_X0 + 6, 238], fill=RED),
                                       d.text((SAFE_X0 + 22, 203), s, font=font(MONO, 24), fill=PAPER))) for s in SECTIONS]
    caps = []
    fen = font(SANS_B, 42)
    cx = (SAFE_X0 + SAFE_X1) / 2
    for l in TIMING:
        def draw(d, txt=l["text"].replace("…", "…")):
            lines = wrap(d, txt, fen, SAFE_X1 - SAFE_X0 - 30)
            y = 1300 - (len(lines) - 1) * 28
            for ln in lines:
                tw = d.textlength(ln, font=fen)
                d.rounded_rectangle([cx - tw / 2 - 14, y - 4, cx + tw / 2 + 14, y + 52], 8, fill=(0, 0, 0, 165))
                d.text((cx - tw / 2, y), ln, font=fen, fill=(255, 255, 255))
                y += 58
        caps.append(Layer(draw, 0, 1180, 1440))
    return tags, caps


def label_layer(label, credit):
    def draw(d):
        if label:
            d.text((SAFE_X0, 1150), label.upper(), font=font(MONO, 22), fill=GOLD)
        if credit:
            for i, ln in enumerate(wrap(d, credit, font(MONO_L, 18), SAFE_X1 - SAFE_X0)):
                d.text((SAFE_X0, 1475 + i * 23), ln, font=font(MONO_L, 18), fill=(165, 158, 145))
    return Layer(draw, 0, 1140, 1530)


def finish(f, idx, zoom=1.0, center=(W / 2, H / 2)):
    f = np.clip(f * VIG + GRAIN[idx % len(GRAIN)], 0, 255).astype(np.uint8)
    img = Image.fromarray(f)
    if abs(zoom - 1.0) > 1e-4:
        cx, cy = center
        w, h = W / zoom, H / zoom
        x0, y0 = cx - w * (cx / W), cy - h * (cy / H)
        img = img.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
    return img


def render_frame(tl, tags, caps, labels, i):
    tsec = i / FPS
    k = next((j for j, (s, e, _) in enumerate(tl) if s <= tsec < e), len(tl) - 1)
    s, e, shot = tl[k]
    dur = e - s
    t = (tsec - s) / dur
    f = shot.frame(t, dur, i)
    if f.shape != (H, W, 3):
        f = np.asarray(Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize((W, H)), np.float32)
    f = np.ascontiguousarray(f, dtype=np.float32)
    z0, z1 = shot.zoom
    zoom = z0 + (z1 - z0) * ease(t)
    if isinstance(shot, (Clip, Photo)) and labels[k] is not None:
        f = labels[k].comp(f, ease((tsec - s) / 0.3))
    # short flash on hard cuts into media
    if tsec - s < 0.06 and k > 0:
        f = f + 45 * (1 - (tsec - s) / 0.06)
    # fade from previous shot (0.25 s dissolve) handled by caller via blending
    plain = not isinstance(shot, (Still, Anim))
    sec = section_of(tsec)
    if plain:
        f = tags[sec].comp(f, 1.0)
    for li, l in (enumerate(TIMING) if plain else []):
        a, b = NAR0 + l["start"], NAR0 + l["end"]
        if a - 0.1 <= tsec <= b + 0.2:
            f = caps[li].comp(f, min(ease((tsec - a + 0.1) / 0.12), 1 - ease((tsec - b) / 0.2)))
    end = tl[-1][1]
    if tsec > end - 1.2:
        f *= 1 - ease((tsec - (end - 1.2)) / 1.2)
    return finish(f, i, zoom, shot.center)


def main():
    cmd = sys.argv[1]
    tl, end = timeline()
    if cmd == "plan":
        for s, e, shot in tl:
            print(f"{s:7.2f}-{e:7.2f} {type(shot).__name__:6s} {getattr(shot, 'label', '') or ''} | {getattr(shot, 'credit', '') or ''}")
        print("end", round(end, 2))
        return
    tags, caps = make_overlays()
    labels = []
    for s, e, shot in tl:
        lab = getattr(shot, "label", None)
        cred = getattr(shot, "credit", None)
        if isinstance(shot, Photo) and not shot.found:
            lab, cred = getattr(shot.fallback, "label", None), getattr(shot.fallback, "credit", None)
        labels.append(label_layer(lab, cred) if (lab or cred) else None)
    if cmd == "frames":
        out = sys.argv[2]
        idxs = [int(((s + e) / 2) * FPS) for s, e, _ in tl]
        thumbs = [render_frame(tl, tags, caps, labels, i).resize((216, 384)) for i in idxs]
        cols = 10
        rows = math.ceil(len(thumbs) / cols)
        sheet = Image.new("RGB", (216 * cols, 384 * rows))
        for j, im in enumerate(thumbs):
            sheet.paste(im, ((j % cols) * 216, (j // cols) * 384))
        sheet.save(out)
        return
    if cmd == "render":
        wk, nw, out_dir = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        first, last = int(NAR0 * FPS), int(end * FPS)
        n = last - first
        a = first + n * wk // nw
        b = first + n * (wk + 1) // nw
        os.makedirs(out_dir, exist_ok=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-tune", "grain",
                               "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-profile:v", "high",
                               os.path.join(out_dir, f"part_{wk:02d}.mp4")], stdin=subprocess.PIPE)
        for i in range(a, b):
            img = render_frame(tl, tags, caps, labels, i)
            ff.stdin.write(img.tobytes())
            if (i - a) % 300 == 0:
                print(f"worker {wk}: {i - a}/{b - a}", flush=True)
        ff.stdin.close()
        ff.wait()
        print(f"worker {wk} done")


if __name__ == "__main__":
    main()
