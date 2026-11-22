"""Erzeugt 10 Design-Beispiele (1080x1920, 9:16) fuer die Doku
"Wie Hitler an die Macht kam".

Archivbilder sind in diesen Entwuerfen bewusst als PLATZHALTER markiert:
Es wurde noch kein echtes Archivmaterial heruntergeladen.

Aufruf: python3 design_frames.py <pfad/world_1930.geojson> <pfad/ne_50m_countries.geojson> <ausgabeordner>
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SAFE_BOTTOM = 1520  # TikTok-UI unten freihalten

F = "/usr/share/fonts/truetype/"
SERIF_B = F + "dejavu/DejaVuSerif-Bold.ttf"
SERIF = F + "liberation/LiberationSerif-Regular.ttf"
SERIF_I = F + "liberation/LiberationSerif-Italic.ttf"
SANS = F + "liberation/LiberationSans-Regular.ttf"
SANS_B = F + "liberation/LiberationSans-Bold.ttf"
MONO = F + "jetbrains-mono/JetBrainsMono-Medium.ttf"
MONO_L = F + "jetbrains-mono/JetBrainsMono-Light.ttf"

INK = (14, 13, 12)
PAPER = (232, 225, 211)
DIM = (150, 144, 132)
RED = (163, 39, 31)
STEEL = (120, 146, 168)

PARTY = {
    "NSDAP": (122, 74, 42),
    "SPD": (196, 34, 46),
    "KPD": (110, 16, 20),
    "Zentrum": (40, 40, 40),
    "DNVP": (52, 82, 130),
    "BVP": (90, 130, 170),
    "DVP": (200, 160, 60),
    "Sonstige": (120, 120, 120),
}


def font(path, size):
    return ImageFont.truetype(path, size)


def grain(img, amount=18, vignette=0.55, seed=1):
    rng = np.random.default_rng(seed)
    a = np.asarray(img).astype(np.float32)
    n = rng.normal(0, amount, (H, W, 1))
    a = a + n
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    v = np.clip(1 - vignette * d ** 2.2, 0, 1)[..., None]
    a = a * v
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def scratches(img, n=6, seed=2):
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(n):
        x = int(rng.uniform(60, W - 60))
        d.line([(x, 0), (x + rng.integers(-8, 8), H)], fill=(255, 255, 255, int(rng.uniform(10, 35))), width=1)
    return img


def text_c(d, y, s, f, fill, w=W):
    tw = d.textlength(s, font=f)
    d.text(((w - tw) / 2, y), s, font=f, fill=fill)


def wrap(d, s, f, maxw):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def tag(d, x, y, s, fg=INK, bg=PAPER, f=None):
    f = f or font(MONO, 26)
    tw = d.textlength(s, font=f)
    d.rectangle([x, y, x + tw + 28, y + 46], fill=bg)
    d.text((x + 14, y + 7), s, font=f, fill=fg)
    return tw + 28


def label_footer(d, n, title):
    f = font(MONO_L, 22)
    d.text((60, 1830), f"DESIGN {n:02d}/10 · {title}", font=f, fill=(110, 105, 98))


def placeholder_photo(size, seed=3, label="PLATZHALTER · ARCHIVFOTO"):
    """Graue Flaeche mit Struktur; ausdruecklich KEIN historisches Bild."""
    w, h = size
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 1, (h // 24 + 1, w // 24 + 1))
    im = Image.fromarray(((base - base.min()) / (np.ptp(base) + 1e-6) * 90 + 50).astype(np.uint8))
    im = im.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18)).convert("RGB")
    d = ImageDraw.Draw(im)
    for i in range(-h, w, 60):
        d.line([(i, 0), (i + h, h)], fill=(95, 92, 88), width=2)
    f = font(MONO, 30)
    tw = d.textlength(label, font=f)
    d.rectangle([(w - tw) / 2 - 20, h / 2 - 30, (w + tw) / 2 + 20, h / 2 + 30], fill=(20, 20, 20))
    d.text(((w - tw) / 2, h / 2 - 19), label, font=f, fill=(230, 200, 120))
    return im


# ---------------------------------------------------------------- Karte
class MapProj:
    def __init__(self, lon0, lon1, lat0, lat1, box):
        self.lon0, self.lon1, self.lat0, self.lat1 = lon0, lon1, lat0, lat1
        x0, y0, x1, y1 = box
        k = math.cos(math.radians((lat0 + lat1) / 2))
        sx = (x1 - x0) / ((lon1 - lon0) * k)
        sy = (y1 - y0) / (lat1 - lat0)
        self.s = min(sx, sy)
        self.k = k
        cw = (lon1 - lon0) * k * self.s
        ch = (lat1 - lat0) * self.s
        self.ox = x0 + ((x1 - x0) - cw) / 2
        self.oy = y0 + ((y1 - y0) - ch) / 2

    def __call__(self, lon, lat):
        return (self.ox + (lon - self.lon0) * self.k * self.s, self.oy + (self.lat1 - lat) * self.s)


def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [p[0] for p in geom["coordinates"]]


def load_maps(hist_path, modern_path):
    hist = json.load(open(hist_path))
    modern = json.load(open(modern_path))
    g = {}
    for f in hist["features"]:
        n = f["properties"].get("NAME")
        if f["geometry"] and n in ("Germany", "East Prussia", "Danzig", "Poland", "Austria", "Czechoslovakia",
                                   "France", "Netherlands", "Belgium", "Denmark", "Switzerland", "Lithuania",
                                   "Luxembourg", "Hungary", "Italy", "Sweden"):
            g.setdefault(n, []).extend(rings(f["geometry"]))
    mod = []
    for f in modern["features"]:
        if f["properties"].get("ADMIN") == "Germany":
            mod = rings(f["geometry"])
    return g, mod


def dashed(d, pts, fill, width=3, dash=14, gap=10):
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        if L == 0:
            continue
        t = 0
        while t < L:
            t1 = min(t + dash, L)
            d.line([(x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L),
                    (x0 + (x1 - x0) * t1 / L, y0 + (y1 - y0) * t1 / L)], fill=fill, width=width)
            t += dash + gap


CITIES = {
    "Berlin": (13.40, 52.52),
    "München": (11.58, 48.14),
    "Nürnberg": (11.08, 49.45),
    "Hamburg": (9.99, 53.55),
    "Weimar": (11.33, 50.98),
    "Köln": (6.96, 50.94),
    "Königsberg": (20.51, 54.71),
    "Essen": (7.01, 51.46),
    "Breslau": (17.04, 51.11),
    "Dresden": (13.74, 51.05),
    "Frankfurt a.M.": (8.68, 50.11),
}


def draw_map(img, geo, mod, proj, show_modern=True, glow=True, land=(38, 40, 44), de_fill=(70, 66, 58),
             de_line=PAPER):
    d = ImageDraw.Draw(img, "RGBA")
    for n, rs in geo.items():
        if n in ("Germany", "East Prussia"):
            continue
        for r in rs:
            d.polygon([proj(*p) for p in r], fill=land, outline=(70, 72, 78))
    if glow:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        for n in ("Germany", "East Prussia"):
            for r in geo.get(n, []):
                ld.line([proj(*p) for p in r], fill=(232, 210, 160, 160), width=14)
        lay = lay.filter(ImageFilter.GaussianBlur(14))
        img.paste(lay, (0, 0), lay)
        d = ImageDraw.Draw(img, "RGBA")
    for n in ("Germany", "East Prussia"):
        for r in geo.get(n, []):
            pts = [proj(*p) for p in r]
            d.polygon(pts, fill=de_fill)
            d.line(pts + [pts[0]], fill=de_line, width=3)
    if show_modern:
        for r in mod:
            dashed(d, [proj(*p) for p in r], fill=(120, 170, 210, 220), width=2)
    return d


# ---------------------------------------------------------------- Designs
def d01_opening():
    img = Image.new("RGB", (W, H), INK)
    ph = placeholder_photo((1080, 1100), seed=11, label="PLATZHALTER · REDNERPULT, 1936")
    img.paste(ph, (0, 260))
    d = ImageDraw.Draw(img, "RGBA")
    # Letterbox-Verlauf
    for i in range(300):
        a = int(255 * (1 - i / 300))
        d.line([(0, 260 + i), (W, 260 + i)], fill=(14, 13, 12, a))
        d.line([(0, 1360 - i), (W, 1360 - i)], fill=(14, 13, 12, a))
    tag(d, 60, 150, "● HISTORISCHE TONAUFNAHME", fg=PAPER, bg=RED)
    # Wellenform
    rng = np.random.default_rng(4)
    for i in range(96):
        x = 60 + i * 10
        h = abs(rng.normal(0, 1)) * 38 * (0.4 + 0.6 * math.sin(i / 96 * math.pi))
        d.line([(x, 1420 - h), (x, 1420 + h)], fill=(232, 225, 211, 200), width=5)
    f = font(SERIF_I, 52)
    y = 1495
    for ln in wrap(d, "„… ob du glaubst, dass ich fleißig gewesen bin, dass ich gearbeitet habe …“", f, 940):
        text_c(d, y, ln, f, PAPER)
        y += 64
    text_c(d, y + 20, "Adolf Hitler · Rede vor Krupp-Arbeitern, Essen · März 1936", font(MONO, 26), DIM)
    text_c(d, y + 60, "Wortlaut & Datum: Prüfung gegen Archivkopie ausstehend", font(MONO_L, 22), (200, 150, 90))
    img = grain(scratches(img), 20)
    d = ImageDraw.Draw(img)
    label_footer(d, 1, "COLD OPEN · ARCHIV-TON")
    return img


def d02_chapter():
    img = Image.new("RGB", (W, H), (22, 21, 19))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 560, "KAPITEL IV", font(MONO, 34), DIM)
    text_c(d, 640, "1929", font(SERIF_B, 250), PAPER)
    d.line([(440, 930), (640, 930)], fill=RED, width=6)
    text_c(d, 960, "1932", font(SERIF_B, 250), PAPER)
    text_c(d, 1270, "Die Krise", font(SERIF_I, 76), PAPER)
    # Zeitstrahl
    years = [1918, 1923, 1929, 1933, 1934]
    x0, x1, y = 120, 960, 1460
    d.line([(x0, y), (x1, y)], fill=(90, 86, 80), width=4)
    px = x0 + (x1 - x0) * (1929 - 1918) / 16
    pe = x0 + (x1 - x0) * (1932 - 1918) / 16
    d.line([(px, y), (pe, y)], fill=RED, width=8)
    for yr in years:
        x = x0 + (x1 - x0) * (yr - 1918) / 16
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=PAPER if yr != 1929 else RED)
        d.text((x - 36, y + (26 if yr != 1933 else -64)), str(yr), font=font(MONO, 26), fill=DIM)
    img = grain(img, 14)
    label_footer(ImageDraw.Draw(img), 2, "KAPITELKARTE + ZEITSTRAHL")
    return img


def d03_map(geo, mod):
    img = Image.new("RGB", (W, H), (16, 20, 26))
    proj = MapProj(5.2, 23.2, 46.6, 56.2, (40, 380, 1040, 1300))
    d = draw_map(img, geo, mod, proj)
    for c in ("Berlin", "München", "Nürnberg", "Hamburg", "Weimar", "Königsberg"):
        x, y = proj(*CITIES[c])
        big = c in ("Berlin", "München")
        r = 11 if big else 7
        d.ellipse([x - r, y - r, x + r, y + r], fill=RED if c == "München" else PAPER)
        d.text((x + 16, y - 18), c, font=font(SANS_B if big else SANS, 32 if big else 26), fill=PAPER)
    x, y = proj(*CITIES["München"])
    d.ellipse([x - 40, y - 40, x + 40, y + 40], outline=(163, 39, 31, 200), width=3)
    d.text((60, 140), "DEUTSCHES REICH", font=font(MONO, 30), fill=DIM)
    d.text((60, 185), "Grenzen von 1930", font=font(SERIF_B, 66), fill=PAPER)
    # Legende
    y = 1360
    d.rectangle([60, y, 110, y + 30], fill=(70, 66, 58), outline=PAPER, width=3)
    d.text((130, y - 2), "Weimarer Republik (1920–1935)", font=font(SANS, 30), fill=PAPER)
    dashed(d, [(60, y + 75), (110, y + 75)], (120, 170, 210), width=3)
    d.text((130, y + 57), "Heutige Grenze (zum Vergleich)", font=font(SANS, 30), fill=(150, 190, 220))
    d.text((60, y + 120), "Saargebiet 1920–1935 unter Völkerbundsverwaltung", font=font(MONO_L, 22), fill=DIM)
    img = grain(img, 8, 0.4)
    label_footer(ImageDraw.Draw(img), 3, "KARTE · HISTORISCH vs. HEUTE")
    return img


def d04_campaign(geo, mod):
    img = Image.new("RGB", (W, H), (26, 24, 20))
    proj = MapProj(5.2, 23.2, 46.6, 56.2, (40, 360, 1040, 1280))
    d = draw_map(img, geo, mod, proj, show_modern=False, glow=False, land=(44, 41, 36), de_fill=(62, 57, 50),
                 de_line=(180, 170, 150))
    route = ["München", "Dresden", "Breslau", "Königsberg", "Berlin", "Hamburg", "Essen", "Köln", "Frankfurt a.M.",
             "Nürnberg"]
    pts = [proj(*CITIES[c]) for c in route]
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 - 0.18 * math.hypot(x1 - x0, y1 - y0)
        arc = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1)
               for t in np.linspace(0, 1, 40)]
        dashed(d, arc, (220, 180, 120, 230), width=3, dash=10, gap=7)
    for c, (x, y) in zip(route, pts):
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(220, 180, 120))
        d.text((x + 14, y - 16), c, font=font(SANS, 24), fill=PAPER)
    d.text((60, 140), "WAHLKAMPF 1932", font=font(MONO, 30), fill=DIM)
    for i, ln in enumerate(["Mit dem Flugzeug", "durch Deutschland"]):
        d.text((60, 185 + i * 74), ln, font=font(SERIF_B, 62), fill=PAPER)
    d.text((60, 1330), "Route schematisch · Stationen werden für die", font=font(MONO_L, 22), fill=DIM)
    d.text((60, 1362), "finale Fassung gegen Quellen abgeglichen", font=font(MONO_L, 22), fill=DIM)
    img = grain(img, 12)
    label_footer(ImageDraw.Draw(img), 4, "KARTE · KAMPAGNENROUTE")
    return img


def d05_elections():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((70, 150), "REICHSTAGSWAHLEN", font=font(MONO, 30), fill=(90, 84, 76))
    d.text((70, 195), "Stimmenanteil NSDAP", font=font(SERIF_B, 64), fill=INK)
    data = [("Mai 1928", 2.6), ("Sep 1930", 18.3), ("Jul 1932", 37.3), ("Nov 1932", 33.1), ("Mär 1933*", 43.9)]
    x0, base, bw, gap, scale = 90, 1300, 150, 30, 18
    d.line([(70, base - 50 * scale), (1010, base - 50 * scale)], fill=RED, width=3)
    d.text((760, base - 50 * scale - 44), "50 % = Mehrheit", font=font(MONO, 24), fill=RED)
    for i, (lab, v) in enumerate(data):
        x = x0 + i * (bw + gap)
        col = (122, 74, 42) if i < 4 else (122, 74, 42, 120)
        d.rectangle([x, base - v * scale, x + bw, base], fill=col)
        s = f"{v:.1f} %".replace(".", ",")
        d.text((x + bw / 2 - d.textlength(s, font=font(SANS_B, 34)) / 2, base - v * scale - 50), s,
               font=font(SANS_B, 34), fill=INK)
        d.text((x + bw / 2 - d.textlength(lab, font=font(MONO, 22)) / 2, base + 16), lab, font=font(MONO, 22),
               fill=(70, 66, 60))
    d.line([(70, base), (1010, base)], fill=INK, width=3)
    f = font(SERIF_I, 32)
    y = 1380
    for ln in wrap(d, "Die NSDAP wurde stärkste Partei – eine absolute Mehrheit erreichte sie in keiner freien Reichstagswahl.", f, 930):
        d.text((70, y), ln, font=f, fill=INK)
        y += 42
    d.text((70, y + 10), "* März 1933: keine freie Wahl mehr (Terror, KPD verfolgt)", font=font(MONO_L, 22), fill=(90, 84, 76))
    img = grain(img, 10, 0.35)
    label_footer(ImageDraw.Draw(img), 5, "WAHLGRAFIK · PAPIER-STIL")
    return img


def d06_hemicycle():
    img = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(img, "RGBA")
    d.text((60, 140), "REICHSTAG · 6. NOVEMBER 1932", font=font(MONO, 30), fill=DIM)
    d.text((60, 185), "584 Sitze", font=font(SERIF_B, 70), fill=PAPER)
    seats = [("KPD", 100), ("SPD", 121), ("Zentrum", 70), ("BVP", 20), ("DVP", 11), ("Sonstige", 15),
             ("DNVP", 51), ("NSDAP", 196)]
    total = sum(s for _, s in seats)
    cx, cy = W / 2, 1020
    rows = 14
    positions = []
    for r in range(rows):
        rad = 180 + r * 27
        n = int(round(math.pi * rad / 26.5))
        for k in range(n):
            a = math.pi - math.pi * (k + 0.5) / n
            positions.append((a, rad))
    positions.sort(key=lambda p: -p[0])
    positions = positions[:total]
    i = 0
    for name, s in seats:
        for _ in range(s):
            a, rad = positions[i]
            x, y = cx + rad * math.cos(a), cy - rad * math.sin(a)
            col = PARTY[name]
            d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=col,
                      outline=(200, 200, 200, 90) if name == "Zentrum" else None)
            i += 1
    big = font(SERIF_B, 110)
    text_c(d, cy - 140, "196", big, PAPER)
    text_c(d, cy - 10, "NSDAP · 33,1 %", font(MONO, 28), DIM)
    y = 1120
    col_x = [70, 560]
    for j, (name, s) in enumerate(sorted(seats, key=lambda t: -t[1])):
        x = col_x[j % 2]
        yy = y + (j // 2) * 56
        d.rectangle([x, yy + 6, x + 30, yy + 36], fill=PARTY[name], outline=(120, 120, 120))
        d.text((x + 46, yy), f"{name}  {s}", font=font(SANS, 32), fill=PAPER)
    d.text((70, 1370), "Mehrheit: 293 Sitze – NSDAP + DNVP = 247", font=font(MONO, 26), fill=(220, 180, 120))
    img = grain(img, 10)
    label_footer(ImageDraw.Draw(img), 6, "SITZVERTEILUNG · HALBRUND")
    return img


def d07_unemployment():
    img = Image.new("RGB", (W, H), (20, 19, 18))
    ph = placeholder_photo((1080, 760), seed=21, label="PLATZHALTER · ARBEITSAMT, 1932")
    img.paste(ph, (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(260):
        d.line([(0, 760 - i), (W, 760 - i)], fill=(20, 19, 18, int(255 * (1 - i / 260) ** 1.4)))
    d.text((60, 640), "ARBEITSLOSE IM DEUTSCHEN REICH", font=font(MONO, 28), fill=DIM)
    d.text((60, 690), "≈ 6 Millionen", font=font(SERIF_B, 110), fill=PAPER)
    d.text((60, 830), "im Winter 1932 (registriert, Jahreshöchststand)", font=font(SERIF_I, 34), fill=DIM)
    data = [(1928, 1.4), (1929, 1.9), (1930, 3.1), (1931, 4.5), (1932, 5.6)]
    x0, x1, y0, y1 = 110, 980, 1380, 960
    for v in (2, 4, 6):
        yy = y0 - (y0 - y1) * v / 6
        d.line([(x0, yy), (x1, yy)], fill=(60, 58, 54), width=1)
        d.text((60, yy - 14), f"{v}", font=font(MONO, 22), fill=DIM)
    pts = [(x0 + (x1 - x0) * i / 4, y0 - (y0 - y1) * v / 6) for i, (_, v) in enumerate(data)]
    d.polygon([(x0, y0)] + pts + [(x1, y0)], fill=(163, 39, 31, 60))
    d.line(pts, fill=RED, width=6, joint="curve")
    for (yr, v), (x, y) in zip(data, pts):
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=PAPER)
        d.text((x - 32, y0 + 14), str(yr), font=font(MONO, 24), fill=DIM)
        s = f"{v:.1f}".replace(".", ",")
        d.text((x - 24, y - 52), s, font=font(SANS_B, 28), fill=PAPER)
    d.text((60, 1450), "Jahresdurchschnitt in Mio. · Werte vor Final-Render gegen Statistik prüfen", font=font(MONO_L, 20),
           fill=DIM)
    img = grain(img, 16)
    label_footer(ImageDraw.Draw(img), 7, "FOTO + DATENLINIE")
    return img


def d08_document():
    img = Image.new("RGB", (W, H), (30, 28, 25))
    d = ImageDraw.Draw(img, "RGBA")
    # Papierblatt, leicht gedreht
    sheet = Image.new("RGBA", (880, 1100), (226, 216, 192, 255))
    sd = ImageDraw.Draw(sheet)
    rng = np.random.default_rng(8)
    for _ in range(4000):
        x, y = rng.integers(0, 880), rng.integers(0, 1100)
        sd.point((x, y), fill=(200, 188, 160, 255))
    sd.text((60, 70), "Verordnung des Reichspräsidenten", font=font(SERIF_B, 38), fill=INK)
    sd.text((60, 120), "zum Schutz von Volk und Staat", font=font(SERIF_B, 38), fill=INK)
    sd.text((60, 180), "Vom 28. Februar 1933", font=font(SERIF_I, 32), fill=(60, 55, 48))
    sd.line([(60, 240), (820, 240)], fill=INK, width=2)
    sd.text((60, 275), "§ 1", font=font(SERIF_B, 34), fill=INK)
    f = font(SERIF, 34)
    y = 330
    q = ("Die Artikel 114, 115, 117, 118, 123, 124 und 153 der Verfassung des Deutschen Reichs "
         "werden bis auf weiteres außer Kraft gesetzt.")
    for ln in wrap(sd, q, f, 760):
        sd.text((60, y), ln, font=f, fill=INK)
        y += 48
    # Markierung
    sd.rectangle([52, y - 52, 470, y - 4], outline=RED, width=4)
    sd.text((60, y + 40), "[…]", font=f, fill=(90, 84, 76))
    sd.text((60, 1000), "Reichsgesetzblatt 1933 I, S. 83 · Zitat", font=font(MONO, 22), fill=(90, 84, 76))
    sheet = sheet.rotate(-2.2, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 170), (0, 0), sheet.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    img.paste(shadow, (110, 300), shadow)
    img.paste(sheet, (80, 270), sheet)
    d = ImageDraw.Draw(img, "RGBA")
    tag(d, 60, 150, "DOKUMENT · REICHSTAGSBRANDVERORDNUNG")
    f = font(SERIF_I, 36)
    y = 1440
    for ln in wrap(d, "Grundrechte wie Meinungs-, Presse- und Versammlungsfreiheit – mit einem Satz ausgesetzt.", f, 960):
        d.text((60, y), ln, font=f, fill=PAPER)
        y += 46
    img = grain(img, 12)
    label_footer(ImageDraw.Draw(img), 8, "DOKUMENT · ZITAT MIT QUELLE")
    return img


def d09_lowerthird():
    ph = placeholder_photo((1300, 1920), seed=31, label="PLATZHALTER · REICHSTAG, 28.2.1933")
    img = ph.crop((110, 0, 1190, 1920)).convert("RGB")
    # Parallax-Andeutung: Vordergrund-Ebene dunkler/geblurrt
    fg = img.crop((0, 1100, W, 1920)).filter(ImageFilter.GaussianBlur(6))
    img.paste(fg, (0, 1100))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, H], fill=(10, 14, 20, 90))
    for i in range(500):
        d.line([(0, H - 400 - i), (W, H - 400 - i)], fill=(8, 8, 8, int(230 * (1 - i / 500))))
    d.rectangle([0, H - 400, W, H], fill=(8, 8, 8, 230))
    d.text((60, 120), "27. FEBRUAR 1933 · BERLIN", font=font(MONO, 32), fill=PAPER)
    d.line([(60, 1180), (60, 1440)], fill=RED, width=8)
    d.text((95, 1180), "Der Reichstag", font=font(SERIF_B, 80), fill=PAPER)
    d.text((95, 1280), "brennt", font=font(SERIF_B, 80), fill=PAPER)
    d.text((95, 1390), "Die NS-Führung nutzt den Brand sofort zur Verfolgung", font=font(SANS, 28), fill=DIM)
    d.text((95, 1426), "politischer Gegner.", font=font(SANS, 28), fill=DIM)
    d.text((60, 1490), "Foto: [Archiv, Signatur] · Lizenz", font=font(MONO_L, 22), fill=(170, 160, 140))
    img = grain(img, 18, 0.5)
    label_footer(ImageDraw.Draw(img), 9, "VOLLBILD-FOTO · BAUCHBINDE")
    return img


def d10_vote():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 300, "23. MÄRZ 1933 · KROLLOPER", font(MONO, 30), DIM)
    text_c(d, 360, "Ermächtigungsgesetz", font(SERIF_B, 76), PAPER)
    text_c(d, 560, "444", font(SERIF_B, 260), PAPER)
    text_c(d, 840, "JA", font(MONO, 34), DIM)
    text_c(d, 920, "94", font(SERIF_B, 150), (196, 34, 46))
    text_c(d, 1090, "NEIN – alle Stimmen der SPD", font(MONO, 30), (196, 34, 46))
    f = font(SERIF_I, 34)
    y = 1200
    for ln in wrap(d, "Die 81 Abgeordneten der KPD waren verhaftet, geflohen oder untergetaucht. "
                      "SA und SS standen im Saal.", f, 900):
        text_c(d, y, ln, f, PAPER)
        y += 46
    img = grain(img, 16)
    label_footer(ImageDraw.Draw(img), 10, "SCHLÜSSELZAHL · TYPOGRAFIE")
    return img


def main():
    hist, modern, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    geo, mod = load_maps(hist, modern)
    frames = [d01_opening(), d02_chapter(), d03_map(geo, mod), d04_campaign(geo, mod), d05_elections(),
              d06_hemicycle(), d07_unemployment(), d08_document(), d09_lowerthird(), d10_vote()]
    for i, im in enumerate(frames, 1):
        im.save(os.path.join(out, f"design_{i:02d}.png"))
    # Kontaktbogen 5x2
    tw, th = 324, 576
    sheet = Image.new("RGB", (tw * 5 + 60, th * 2 + 40), (10, 10, 10))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (i % 5) * (tw + 10), 10 + (i // 5) * (th + 10)))
    sheet.save(os.path.join(out, "kontaktbogen.png"))


if __name__ == "__main__":
    main()
