"""Design-Beispiele 11-20: aufwendigere Looks (3D-Karte, Licht, Partikel, Riss-Effekt).

Archivbilder sind weiterhin als PLATZHALTER markiert; gezeichnete Szenen sind als ILLUSTRATION markiert.
Aufruf: python3 design_frames_2.py <world_1930.geojson> <ne_50m_countries.geojson> <ausgabeordner>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import (CITIES, DIM, H, INK, MONO, MONO_L, PAPER, PARTY, RED, SANS, SANS_B, SERIF, SERIF_B,
                           SERIF_I, W, MapProj, dashed, font, grain, load_maps, placeholder_photo, tag, text_c,
                           wrap)

GOLD = (226, 190, 120)
EMBER = (255, 140, 40)


def footer(img, n, title):
    ImageDraw.Draw(img).text((60, 1830), f"DESIGN {n:02d}/20 · {title}", font=font(MONO_L, 22), fill=(110, 105, 98))


def glow_text(img, xy, s, f, fill, radius=18, strength=2):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(xy, s, font=f, fill=fill + (255,))
    g = lay.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        img.paste(g, (0, 0), g)
    img.paste(lay, (0, 0), lay)


def glow_text_c(img, y, s, f, fill, **kw):
    tw = ImageDraw.Draw(img).textlength(s, font=f)
    glow_text(img, ((W - tw) / 2, y), s, f, fill, **kw)


def light_rays(size, origin, color, strength=1.0, seed=0):
    """Volumetrische Lichtstrahlen per Zoom-Blur."""
    w, h = size
    rng = np.random.default_rng(seed)
    src = Image.new("L", size, 0)
    d = ImageDraw.Draw(src)
    ox, oy = origin
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(200, 1600)
        wdt = rng.uniform(0.01, 0.05)
        d.polygon([(ox, oy), (ox + L * math.cos(a - wdt), oy + L * math.sin(a - wdt)),
                   (ox + L * math.cos(a + wdt), oy + L * math.sin(a + wdt))], fill=int(rng.uniform(20, 70)))
    d.ellipse([ox - 90, oy - 90, ox + 90, oy + 90], fill=255)
    src = src.filter(ImageFilter.GaussianBlur(6))
    acc = np.zeros((h, w), np.float32)
    for i in range(14):
        s = 1 + i * 0.06
        z = src.resize((int(w * s), int(h * s)), Image.BILINEAR)
        cx, cy = int(ox * s - ox), int(oy * s - oy)
        acc += np.asarray(z.crop((cx, cy, cx + w, cy + h)), np.float32) / 14
    acc = np.clip(acc * strength / 255, 0, 1)[..., None]
    col = np.array(color, np.float32)[None, None, :]
    return acc * col


def add_light(img, light):
    a = np.asarray(img).astype(np.float32) + light
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def dust(img, n=260, seed=5, color=(255, 240, 210), region=None):
    rng = np.random.default_rng(seed)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = region or (0, 0, W, H)
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.choice([1, 1, 2, 2, 3, 6, 10])
        a = int(rng.uniform(30, 160) if r < 6 else rng.uniform(15, 40))
        d.ellipse([x - r, y - r, x + r, y + r], fill=color + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(1.2))
    img.paste(lay, (0, 0), lay)
    return img


def chroma(img, shift=3):
    r, g, b = img.split()
    r = ImageChops.offset(r, shift, 0)
    b = ImageChops.offset(b, -shift, 0)
    return Image.merge("RGB", (r, g, b))


def letterbox(img, h=110):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, h], fill=(0, 0, 0))
    d.rectangle([0, H - h, W, H], fill=(0, 0, 0))


def perspective_coeffs(dst, src):
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def tilt(layer, top_inset=200, top_y=0.18, bottom_y=1.0):
    w, h = layer.size
    dst = [(top_inset, h * top_y), (w - top_inset, h * top_y), (w, h * bottom_y), (0, h * bottom_y)]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    return layer.transform(layer.size, Image.PERSPECTIVE, perspective_coeffs(dst, src), Image.BICUBIC)


def germany_rings(geo):
    return [r for n in ("Germany", "East Prussia") for r in geo.get(n, [])]


# ------------------------------------------------------------------ 11
def d11_tilted_map(geo, mod):
    img = Image.new("RGB", (W, H), (8, 10, 14))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    proj = MapProj(5.0, 23.4, 46.4, 56.0, (20, 700, 1060, 1700))
    d = ImageDraw.Draw(layer)
    for n, rs in geo.items():
        if n in ("Germany", "East Prussia"):
            continue
        for r in rs:
            d.polygon([proj(*p) for p in r], fill=(22, 26, 32, 255), outline=(44, 50, 58, 255))
    # Gitter
    for lon in range(5, 24, 2):
        d.line([proj(lon, 46.4), proj(lon, 56.0)], fill=(60, 70, 80, 90), width=1)
    for lat in range(47, 57, 1):
        d.line([proj(5.0, lat), proj(23.4, lat)], fill=(60, 70, 80, 90), width=1)
    # Extrusion
    depth = 26
    for k in range(depth, 0, -1):
        c = int(30 + 40 * (1 - k / depth))
        for r in germany_rings(geo):
            d.polygon([(x, y + k) for x, y in (proj(*p) for p in r)], fill=(c, c - 4, c - 10, 255))
    for r in germany_rings(geo):
        pts = [proj(*p) for p in r]
        d.polygon(pts, fill=(92, 84, 70, 255))
        d.line(pts + [pts[0]], fill=GOLD + (255,), width=3)
    for c in ("Hamburg", "Munich", "Nuremberg", "Cologne", "Königsberg"):
        x, y = proj(*CITIES[c])
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=PAPER + (255,))
        d.text((x + 14, y - 16), c, font=font(SANS, 26), fill=PAPER + (230,))
    bx, by = proj(*CITIES["Berlin"])
    t = tilt(layer, top_inset=260, top_y=0.3)
    img.paste(t, (0, 0), t)
    # Berlin-Position nach Perspektive bestimmen
    co = perspective_coeffs([(0, 0), (W, 0), (W, H), (0, H)],
                            [(260, H * 0.3), (W - 260, H * 0.3), (W, H), (0, H)])
    a, b, c_, dd, e, f, g, h = co
    den = g * bx + h * by + 1
    px, py = (a * bx + b * by + c_) / den, (dd * bx + e * by + f) / den
    # Lichtsaeule ueber Berlin
    beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam)
    bd.polygon([(px - 6, py), (px + 6, py), (px + 60, 0), (px - 60, 0)], fill=(255, 210, 140, 70))
    beam = beam.filter(ImageFilter.GaussianBlur(22))
    img.paste(beam, (0, 0), beam)
    img = add_light(img, light_rays((W, H), (px, py), (255, 190, 110), 0.28, seed=3))
    d2 = ImageDraw.Draw(img, "RGBA")
    for r_ in (40, 70, 110):
        d2.ellipse([px - r_, py - r_ * 0.4, px + r_, py + r_ * 0.4], outline=(255, 200, 120, 150 - r_), width=3)
    d2.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(255, 235, 200))
    glow_text(img, (px + 30, py - 70), "Berlin", font(SANS_B, 40), PAPER, radius=10, strength=1)
    letterbox(img, 0)
    d2 = ImageDraw.Draw(img)
    d2.text((60, 150), "30 JANUARY 1933", font=font(MONO, 34), fill=GOLD)
    glow_text(img, (60, 200), "Power Handed Over", font(SERIF_B, 84), PAPER, radius=14, strength=1)
    d2.text((60, 310), "Hindenburg appoints Hitler Reich Chancellor.", font=font(SERIF_I, 38), fill=DIM)
    img = dust(img, 180, seed=11)
    img = grain(img, 10, 0.5)
    footer(img, 11, "3D MAP · TILTED · LIGHT BEAM")
    return img


# ------------------------------------------------------------------ 12
def iso_prism(d, x, base_y, w, h, top, left, right, depth=46):
    dx, dy = depth * 0.9, -depth * 0.5
    d.polygon([(x, base_y), (x + w, base_y), (x + w, base_y - h), (x, base_y - h)], fill=left)
    d.polygon([(x + w, base_y), (x + w + dx, base_y + dy), (x + w + dx, base_y - h + dy), (x + w, base_y - h)],
              fill=right)
    d.polygon([(x, base_y - h), (x + w, base_y - h), (x + w + dx, base_y - h + dy), (x + dx, base_y - h + dy)],
              fill=top)


def d12_iso_bars():
    img = Image.new("RGB", (W, H), (14, 14, 16))
    img = add_light(img, light_rays((W, H), (W / 2, 260), (120, 110, 100), 0.35, seed=9))
    d = ImageDraw.Draw(img, "RGBA")
    # Boden-Gitter in Perspektive
    for i in range(14):
        y = 1300 + i * i * 2.2
        d.line([(0, y), (W, y)], fill=(70, 66, 60, 120 - i * 7), width=1)
    for i in range(-10, 11):
        d.line([(W / 2 + i * 40, 1300), (W / 2 + i * 220, 1720)], fill=(70, 66, 60, 60), width=1)
    data = [("1928", 2.6), ("1930", 18.3), ("Jul 32", 37.3), ("Nov 32", 33.1)]
    x0, bw, gap, scale, base = 110, 150, 72, 15, 1330
    # Mehrheitsebene als halbtransparente Glasplatte
    my = base - 50 * scale
    d.polygon([(60, my), (1000, my), (1040, my - 24), (100, my - 24)], fill=(163, 39, 31, 60), outline=(200, 60, 50, 200))
    d.text((70, my - 70), "50 % · absolute majority", font=font(MONO, 26), fill=(230, 110, 95))
    for i, (lab, v) in enumerate(data):
        x = x0 + i * (bw + gap)
        h = v * scale
        hi = 1 if i == 2 else 0.8
        top = tuple(int(c * hi * 1.5) for c in PARTY["NSDAP"])
        iso_prism(d, x, base, bw, h, top, tuple(int(c * hi) for c in PARTY["NSDAP"]),
                  tuple(int(c * hi * 0.6) for c in PARTY["NSDAP"]))
        s = f"{v:.1f} %"
        f = font(SERIF_B, 50 if i == 2 else 40)
        d.text((x + bw / 2 - d.textlength(s, font=f) / 2 + 20, base - h - 100), s, font=f, fill=PAPER)
        d.text((x + bw / 2 - d.textlength(lab, font=font(MONO, 26)) / 2, base + 30), lab, font=font(MONO, 26), fill=DIM)
    d.text((60, 150), "NSDAP · REICHSTAG ELECTIONS", font=font(MONO, 30), fill=GOLD)
    glow_text(img, (60, 195), "Largest party.", font(SERIF_B, 80), PAPER, radius=12, strength=1)
    glow_text(img, (60, 290), "Never a majority.", font(SERIF_B, 80), (230, 110, 95), radius=12, strength=1)
    img = dust(img, 120, seed=4)
    img = grain(img, 9, 0.5)
    footer(img, 12, "3D COLUMNS · 50 % GLASS PLANE")
    return img


# ------------------------------------------------------------------ 13
def crack_paths(origin, seed=7, n=9):
    rng = np.random.default_rng(seed)
    paths = []
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.25, 0.25)
        x, y = origin
        pts = [(x, y)]
        L = rng.uniform(500, 1200)
        steps = 26
        for _ in range(steps):
            a += rng.uniform(-0.35, 0.35)
            x += math.cos(a) * L / steps
            y += math.sin(a) * L / steps
            pts.append((x, y))
            if rng.random() < 0.12:
                b, bx, by = a + rng.choice([-1, 1]) * rng.uniform(0.5, 1.1), x, y
                br = [(bx, by)]
                for _ in range(8):
                    b += rng.uniform(-0.3, 0.3)
                    bx += math.cos(b) * 28
                    by += math.sin(b) * 28
                    br.append((bx, by))
                paths.append(br)
        paths.append(pts)
    return paths


def d13_crack():
    img = Image.new("RGB", (W, H), (226, 218, 198))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 360, "THE CONSTITUTION OF THE GERMAN REICH", font(MONO, 30), (90, 84, 76))
    text_c(d, 410, "11 August 1919", font(SERIF_I, 40), (90, 84, 76))
    text_c(d, 560, "Article 1", font(SERIF_B, 66), INK)
    f = font(SERIF, 54)
    y = 680
    for ln in ["The German Reich", "is a republic.", "State authority", "derives from the people."]:
        text_c(d, y, ln, f, INK)
        y += 74
    # Riss: Bild verschieben entlang einer Bruchlinie
    origin = (560, 820)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.polygon([(0, 0), (W, 0), (W, 760), origin, (0, 980)], fill=255)
    shifted = ImageChops.offset(img, -5, -9)
    img = Image.composite(shifted, img, mask)
    d = ImageDraw.Draw(img, "RGBA")
    for p in crack_paths(origin):
        d.line(p, fill=(20, 16, 12, 230), width=4, joint="curve")
        d.line([(x + 2, y + 2) for x, y in p], fill=(255, 255, 255, 90), width=1)
    # Splitter
    rng = np.random.default_rng(3)
    for _ in range(40):
        x, y = origin[0] + rng.normal(0, 60), origin[1] + rng.normal(0, 60)
        s = rng.uniform(4, 14)
        d.polygon([(x, y), (x + s, y + s * 0.3), (x + s * 0.4, y + s)], fill=(30, 26, 20, 200))
    d.rectangle([0, 1180, W, H], fill=(14, 13, 12, 240))
    d.text((60, 1240), "28 FEBRUARY – 23 MARCH 1933", font=font(MONO, 30), fill=GOLD)
    f = font(SERIF_B, 58)
    yy = 1290
    for ln in ["In 23 days,", "the constitution", "is hollowed out."]:
        d.text((60, yy), ln, font=f, fill=PAPER)
        yy += 70
    img = grain(img, 12, 0.5)
    footer(img, 13, "TYPE + CRACK EFFECT")
    return img


# ------------------------------------------------------------------ 14
def d14_gleichschaltung():
    img = Image.new("RGB", (W, H), (16, 16, 17))
    d = ImageDraw.Draw(img, "RGBA")
    d.text((60, 150), "SUMMER 1933 · GLEICHSCHALTUNG", font=font(MONO, 30), fill=GOLD)
    glow_text(img, (60, 195), "Forced into Line", font(SERIF_B, 84), PAPER, radius=12, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    rows = [
        ("Trade unions", "2 May", "smashed"),
        ("SPD", "22 June", "banned"),
        ("DNVP", "27 June", "dissolved"),
        ("DStP", "28 June", "dissolved"),
        ("BVP", "4 July", "dissolved"),
        ("DVP", "4 July", "dissolved"),
        ("Centre Party", "5 July", "dissolved"),
        ("New parties", "14 July", "banned by law"),
    ]
    y = 380
    for i, (name, date, what) in enumerate(rows):
        faded = i < 7
        a = 110 if faded else 255
        d.rectangle([60, y, 1020, y + 112], fill=(30, 30, 32, 255), outline=(60, 60, 62))
        d.text((90, y + 18), name, font=font(SERIF_B, 46), fill=PAPER + (a,))
        d.text((90, y + 72), f"{date} 1933 · {what}", font=font(MONO, 24), fill=DIM + (a,))
        if faded:
            d.line([(80, y + 46), (80 + d.textlength(name, font=font(SERIF_B, 46)) + 24, y + 46)], fill=RED, width=6)
        y += 126
    d.rectangle([60, y + 10, 1020, y + 130], fill=(163, 39, 31))
    text_c(d, y + 36, "NSDAP · the only permitted party", font(SANS_B, 42), PAPER)
    d.text((60, y + 150), "KPD: persecuted from March 1933, seats annulled", font=font(MONO_L, 22), fill=DIM)
    img = grain(img, 10, 0.45)
    footer(img, 14, "LIST · STRIKE-THROUGH ANIMATION")
    return img


# ------------------------------------------------------------------ 15
def reichstag_silhouette(d, cx, base, s, fill):
    """Vereinfachte, gezeichnete Silhouette (Illustration, kein Foto)."""
    w = 820 * s
    d.rectangle([cx - w / 2, base - 210 * s, cx + w / 2, base], fill=fill)
    for sx in (-1, 1):
        tx = cx + sx * (w / 2 - 70 * s)
        d.rectangle([tx - 70 * s, base - 300 * s, tx + 70 * s, base], fill=fill)
    d.polygon([(cx - 170 * s, base - 210 * s), (cx + 170 * s, base - 210 * s), (cx, base - 290 * s)], fill=fill)
    d.rectangle([cx - 130 * s, base - 380 * s, cx + 130 * s, base - 260 * s], fill=fill)
    d.chord([cx - 130 * s, base - 470 * s, cx + 130 * s, base - 300 * s], 180, 360, fill=fill)
    for i in range(6):
        x = cx - 150 * s + i * 60 * s
        d.rectangle([x, base - 200 * s, x + 18 * s, base - 20 * s], fill=tuple(max(0, c - 8) for c in fill))


def d15_fire():
    img = Image.new("RGB", (W, H), (6, 5, 6))
    rng = np.random.default_rng(15)
    # Rauch
    n = rng.normal(0, 1, (H // 40 + 1, W // 40 + 1))
    smoke = Image.fromarray(((n - n.min()) / np.ptp(n) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    smoke = smoke.filter(ImageFilter.GaussianBlur(30))
    s = np.asarray(smoke, np.float32)[..., None] / 255
    yy = np.linspace(0, 1, H)[:, None, None]
    a = np.asarray(img, np.float32) + s * (1 - yy) * np.array([70, 50, 45])
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img = add_light(img, light_rays((W, H), (W / 2, 900), (255, 110, 30), 0.7, seed=15))
    # Glut hinter dem Gebaeude
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(420, 0, -20):
        gd.ellipse([W / 2 - r * 1.4, 880 - r, W / 2 + r * 1.4, 880 + r],
                   fill=(255, int(80 + 100 * (1 - r / 420)), 20, int(14 + 18 * (1 - r / 420))))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img, "RGBA")
    reichstag_silhouette(d, W / 2, 1180, 1.15, (10, 8, 8))
    # Flammenzungen in der Kuppel
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fl)
    for _ in range(60):
        x = W / 2 + rng.normal(0, 70)
        h = rng.uniform(80, 260)
        fd.polygon([(x - 18, 860), (x + 18, 860), (x + rng.normal(0, 20), 860 - h)], fill=(255, int(rng.uniform(90, 190)), 30, 90))
    fl = fl.filter(ImageFilter.GaussianBlur(8))
    img.paste(fl, (0, 0), fl)
    # Funken
    sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for _ in range(340):
        x, y = W / 2 + rng.normal(0, 260), rng.uniform(200, 1100)
        L = rng.uniform(4, 22)
        sd.line([(x, y), (x + rng.normal(0, 3), y - L)], fill=(255, int(rng.uniform(120, 220)), 60, int(rng.uniform(80, 230))), width=2)
    img.paste(sp.filter(ImageFilter.GaussianBlur(0.8)), (0, 0), sp)
    letterbox(img, 120)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 1180, W, H - 120], fill=(6, 5, 6, 235))
    d.text((60, 1240), "27 FEBRUARY 1933 · 9:14 PM", font=font(MONO, 30), fill=EMBER)
    glow_text(img, (60, 1290), "The Reichstag", font(SERIF_B, 92), PAPER, radius=16, strength=1)
    glow_text(img, (60, 1395), "is on fire", font(SERIF_B, 92), (255, 200, 150), radius=16, strength=2)
    d = ImageDraw.Draw(img)
    d.text((60, 1520), "ILLUSTRATION · not archive footage", font=font(MONO_L, 22), fill=(170, 150, 130))
    img = chroma(img, 2)
    img = grain(img, 12, 0.45)
    footer(img, 15, "ILLUSTRATED SCENE · FIRE")
    return img


# ------------------------------------------------------------------ 16
def d16_board():
    img = Image.new("RGB", (W, H), (34, 30, 26))
    rng = np.random.default_rng(16)
    a = np.asarray(img, np.float32) + rng.normal(0, 6, (H, W, 1))
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))
    img = add_light(img, light_rays((W, H), (W / 2, -200), (140, 120, 90), 0.5, seed=16))
    people = {
        "Hindenburg": ((540, 520), "Reich President"),
        "von Papen": ((250, 900), "Former chancellor"),
        "Hitler": ((830, 900), "NSDAP leader"),
        "Hugenberg": ((250, 1300), "DNVP"),
        "von Schleicher": ((830, 1300), "Chancellor since Dec 1932"),
    }
    links = [("von Papen", "Hitler", "4 Jan 1933 · meeting in Cologne"),
             ("von Papen", "Hindenburg", "Confidant"),
             ("Hindenburg", "von Schleicher", "28 Jan · resigns"),
             ("Hitler", "Hugenberg", "Coalition"),
             ("Hindenburg", "Hitler", "30 Jan · appointment")]
    d = ImageDraw.Draw(img, "RGBA")
    for a_, b_, lab in links:
        (x0, y0), (x1, y1) = people[a_][0], people[b_][0]
        col = (200, 40, 35, 230)
        d.line([(x0, y0), (x1, y1)], fill=(0, 0, 0, 120), width=7)
        d.line([(x0, y0), (x1, y1)], fill=col, width=4)
    for i, (name, ((x, y), role)) in enumerate(people.items()):
        card = Image.new("RGBA", (260, 330), (236, 230, 214, 255))
        ph = placeholder_photo((228, 230), seed=40 + i, label="PHOTO").convert("RGBA")
        card.paste(ph, (16, 16))
        cd = ImageDraw.Draw(card)
        cd.text((16, 256), name, font=font(SERIF_B, 28), fill=INK)
        cd.text((16, 294), role, font=font(MONO, 17), fill=(80, 74, 66))
        card = card.rotate(rng.uniform(-4, 4), resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 160), (0, 0), card.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        img.paste(sh, (int(x - card.width / 2 + 10), int(y - card.height / 2 + 14)), sh)
        img.paste(card, (int(x - card.width / 2), int(y - card.height / 2)), card)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 12, y - card.height / 2 + 4, x + 12, y - card.height / 2 + 28], fill=(190, 30, 30))
    for a_, b_, lab in links:
        (x0, y0), (x1, y1) = people[a_][0], people[b_][0]
        t = {"meeting": 0.5, "Confidant": 0.62, "resigns": 0.62, "Coalition": 0.5, "appointment": 0.62}
        k = next(v for kk, v in t.items() if kk in lab)
        mx, my = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        if "meeting" in lab:
            my += 60
        f = font(MONO, 20)
        tw = d.textlength(lab, font=f)
        mx = min(max(mx, tw / 2 + 20), W - tw / 2 - 20)
        d.rectangle([mx - tw / 2 - 10, my - 18, mx + tw / 2 + 10, my + 16], fill=(235, 228, 200), outline=(200, 40, 35))
        d.text((mx - tw / 2, my - 13), lab, font=f, fill=INK)
    d.rectangle([0, 0, W, 330], fill=(14, 13, 12, 220))
    d.text((60, 150), "JANUARY 1933", font=font(MONO, 30), fill=GOLD)
    glow_text(img, (60, 195), "Backroom Deals", font(SERIF_B, 76), PAPER, radius=12, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 1500, W, H], fill=(14, 13, 12, 230))
    f = font(SERIF_I, 34)
    y = 1530
    for ln in wrap(d, "Not an election victory: conservative elites believed they could “box Hitler in”.", f, 960):
        d.text((60, y), ln, font=f, fill=PAPER)
        y += 44
    img = grain(img, 10, 0.55)
    footer(img, 16, "INVESTIGATION BOARD · KEY PLAYERS")
    return img


# ------------------------------------------------------------------ 17
def d17_inflation():
    img = Image.new("RGB", (W, H), (12, 12, 12))
    d = ImageDraw.Draw(img, "RGBA")
    # Hintergrund: Ziffernkaskade
    rng = np.random.default_rng(17)
    f_small = font(MONO_L, 30)
    for col in range(16):
        x = 20 + col * 66
        y = rng.uniform(-400, 0)
        while y < H:
            d.text((x, y), str(rng.integers(0, 10)), font=f_small, fill=(60, 55, 45, int(rng.uniform(30, 110))))
            y += 38
    d.rectangle([0, 520, W, 1260], fill=(12, 12, 12, 225))
    text_c(d, 150, "20 NOVEMBER 1923", font(MONO, 32), GOLD)
    glow_text_c(img, 200, "Hyperinflation", font(SERIF_B, 86), PAPER, radius=12, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 580, "1 US dollar =", font(SERIF_I, 52), DIM)
    glow_text_c(img, 680, "4,200,000,000,000", font(SERIF_B, 98), (240, 200, 120), radius=18, strength=2)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 830, "marks", font(SERIF_B, 70), PAPER)
    text_c(d, 960, "For comparison, July 1914: 1 dollar = 4.20 marks", font(MONO, 28), DIM)
    d.line([(160, 1050), (920, 1050)], fill=(90, 86, 80), width=2)
    f = font(SERIF_I, 36)
    y = 1100
    for ln in wrap(d, "Savings become worthless. That same month, Hitler attempts his putsch in Munich.", f, 900):
        text_c(d, y, ln, f, PAPER)
        y += 48
    img = grain(img, 12, 0.5)
    footer(img, 17, "NUMBER CASCADE · GLOW")
    return img


# ------------------------------------------------------------------ 18
def d18_52days():
    img = Image.new("RGB", (W, H), (10, 11, 13))
    d = ImageDraw.Draw(img, "RGBA")
    d.text((60, 140), "30 JANUARY – 23 MARCH 1933", font=font(MONO, 30), fill=GOLD)
    glow_text(img, (60, 180), "52 Days", font(SERIF_B, 120), PAPER, radius=16, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    events = [
        ("30 Jan", "Hitler becomes Chancellor", False),
        ("1 Feb", "Reichstag dissolved – new election called", False),
        ("4 Feb", "Emergency decree restricts press & assembly", False),
        ("22 Feb", "SA & SS become auxiliary police in Prussia", True),
        ("27 Feb", "Reichstag fire", True),
        ("28 Feb", "Reichstag Fire Decree", True),
        ("5 Mar", "Reichstag election – NSDAP 43.9 %", False),
        ("22 Mar", "Dachau concentration camp opens", True),
        ("23 Mar", "Enabling Act", True),
    ]
    x = 250
    y0, y1 = 420, 1560
    d.line([(x, y0), (x, y1)], fill=(60, 60, 64), width=4)
    d.line([(x, y0), (x, y0 + (y1 - y0) * 0.72)], fill=RED, width=6)
    step = (y1 - y0) / (len(events) - 1)
    for i, (dt, txt, hot) in enumerate(events):
        y = y0 + i * step
        if hot:
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse([x - 26, y - 26, x + 26, y + 26], fill=(230, 60, 40, 180))
            g = g.filter(ImageFilter.GaussianBlur(12))
            img.paste(g, (0, 0), g)
            d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=RED if hot else PAPER)
        d.text((x - 40 - d.textlength(dt, font=font(MONO, 32)), y - 20), dt, font=font(MONO, 32), fill=GOLD if hot else DIM)
        f = font(SANS_B if hot else SANS, 32)
        lines = wrap(d, txt, f, 700)
        for k, ln in enumerate(lines):
            d.text((x + 40, y - 20 + k * 38), ln, font=f, fill=PAPER)
    img = grain(img, 9, 0.45)
    footer(img, 18, "VERTICAL CHRONICLE · SCROLL")
    return img


# ------------------------------------------------------------------ 19
def d19_filmstrip():
    img = Image.new("RGB", (W, H), (8, 8, 8))
    img = add_light(img, light_rays((W, H), (W / 2, H / 2), (90, 100, 120), 0.45, seed=19))
    strip = Image.new("RGBA", (760, 2300), (18, 16, 14, 255))
    sd = ImageDraw.Draw(strip)
    for y in range(20, 2300, 56):
        sd.rounded_rectangle([20, y, 58, y + 30], 6, fill=(200, 195, 185, 255))
        sd.rounded_rectangle([702, y, 740, y + 30], 6, fill=(200, 195, 185, 255))
    labels = ["PLACEHOLDER · TORCHLIGHT PARADE 30 JAN 1933", "PLACEHOLDER · SPORTPALAST 10 FEB 1933",
              "PLACEHOLDER · KROLL OPERA 23 MAR 1933"]
    for i, lab in enumerate(labels):
        ph = placeholder_photo((620, 560), seed=60 + i, label=lab.split(" · ")[1]).convert("RGBA")
        strip.paste(ph, (70, 120 + i * 720))
        sd.text((80, 120 + i * 720 + 575), f"{i + 1:02d}  ▸  00:{12 + i * 7:02d}:{(i * 13) % 25:02d}", font=font(MONO, 22),
                fill=(230, 180, 90, 255))
    strip = strip.rotate(-8, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", strip.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 200), (0, 0), strip.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    ox, oy = (W - strip.width) // 2, (H - strip.height) // 2 - 60
    img.paste(sh, (ox + 30, oy + 40), sh)
    img.paste(strip, (ox, oy), strip)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 330], fill=(8, 8, 8, 225))
    d.text((60, 150), "ARCHIVE FILM", font=font(MONO, 30), fill=GOLD)
    glow_text(img, (60, 195), "Images of Power", font(SERIF_B, 80), PAPER, radius=12, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 1460, W, H], fill=(8, 8, 8, 230))
    f = font(SERIF_I, 34)
    y = 1490
    for ln in wrap(d, "Much of this footage is Nazi propaganda. We show it – and put it in context.", f, 960):
        d.text((60, y), ln, font=f, fill=PAPER)
        y += 44
    img = grain(img, 14, 0.55)
    footer(img, 19, "FILM STRIP · TRANSITION")
    return img


# ------------------------------------------------------------------ 20
def d20_finale():
    img = Image.new("RGB", (W, H), (4, 4, 5))
    img = add_light(img, light_rays((W, H), (W / 2, -80), (200, 190, 170), 0.9, seed=20))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 420, "2 AUGUST 1934", font(MONO, 34), GOLD)
    glow_text_c(img, 480, "Hindenburg dies.", font(SERIF_B, 82), PAPER, radius=14, strength=1)
    d = ImageDraw.Draw(img, "RGBA")
    f = font(SERIF_I, 40)
    y = 620
    for ln in ["Hitler merges the offices of", "President and Chancellor."]:
        text_c(d, y, ln, f, DIM)
        y += 52
    glow_text_c(img, 860, "549", font(SERIF_B, 300), (240, 225, 200), radius=24, strength=2)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, 1190, "DAYS FROM CHANCELLOR TO DICTATOR", font(MONO, 32), PAPER)
    d.line([(340, 1290), (740, 1290)], fill=RED, width=4)
    f = font(SERIF_I, 34)
    y = 1330
    for ln in wrap(d, "Democracy was not abolished in a single day – but step by step, "
                      "through laws, violence and the help of those who thought they could control him.", f, 900):
        text_c(d, y, ln, f, PAPER)
        y += 46
    img = dust(img, 300, seed=21, region=(200, 0, 880, 900))
    img = grain(img, 12, 0.6)
    footer(img, 20, "FINALE · LIGHT FROM ABOVE")
    return img


def main():
    hist, modern, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    geo, mod = load_maps(hist, modern)
    frames = [d11_tilted_map(geo, mod), d12_iso_bars(), d13_crack(), d14_gleichschaltung(), d15_fire(),
              d16_board(), d17_inflation(), d18_52days(), d19_filmstrip(), d20_finale()]
    for i, im in enumerate(frames, 11):
        im.save(os.path.join(out, f"design_{i:02d}.png"))
    tw, th = 324, 576
    sheet = Image.new("RGB", (tw * 5 + 60, th * 2 + 30), (10, 10, 10))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (i % 5) * (tw + 10), 10 + (i // 5) * (th + 10)))
    sheet.save(os.path.join(out, "kontaktbogen_2.png"))


if __name__ == "__main__":
    main()
