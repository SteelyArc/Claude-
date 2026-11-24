"""Design examples 37-42: restrained, broadcast-documentary style.

Typography: Source Serif 4 (titles), Inter (supers/lower thirds), IBM Plex Mono (data) - all SIL OFL.
Look: monochrome archive grade with gentle split tone, halation, fine grain, clean supers.
Usage: python3 design_frames_5.py <out_dir>
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import CITIES, H, W, MapProj, load_maps
from design_frames_2 import germany_rings
from design_frames_3 import photo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FD = os.path.join(ROOT, "fonts")
GEO = os.path.join(os.environ.get("SCRATCH", "/tmp"), "dl")
X0, X1 = 72, 930
IVORY = (238, 232, 220)
MUTED = (160, 154, 144)
ACCENT = (196, 64, 48)
GOLDL = (205, 175, 120)
BG = (12, 12, 13)


def vf(name, size, wght=400, opsz=None):
    f = ImageFont.truetype(os.path.join(FD, name), size)
    try:
        axes = f.get_variation_axes()
        vals = []
        for ax in axes:
            tag = ax.get("name", b"")
            tag = tag.decode() if isinstance(tag, bytes) else str(tag)
            t = tag.lower()
            if "weight" in t:
                vals.append(wght)
            elif "optical" in t:
                vals.append(opsz if opsz else min(max(size, ax["minimum"]), ax["maximum"]))
            elif "width" in t:
                vals.append(100)
            else:
                vals.append(ax["default"])
        f.set_variation_by_axes(vals)
    except Exception:  # noqa: BLE001  (static font)
        pass
    return f


def serif(size, w=600):
    return vf("SourceSerif4[opsz,wght].ttf", size, w)


def serif_i(size, w=400):
    return vf("SourceSerif4-Italic[opsz,wght].ttf", size, w)


def sans(size, w=400):
    return vf("Inter[opsz,wght].ttf", size, w)


def mono(size):
    return ImageFont.truetype(os.path.join(FD, "IBMPlexMono-Regular.ttf"), size)


def tracked(d, xy, s, f, fill, track=0.12, anchor_center=False):
    x, y = xy
    sp = f.size * track
    total = sum(d.textlength(c, font=f) + sp for c in s) - sp
    if anchor_center:
        x = (W - total) / 2
    for c in s:
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + sp
    return total


def grade(img, warm=0.6, halation=0.35, grain_amt=7, vignette=0.45, seed=0):
    """Monochrome archive grade: S-curve, split tone, halation, fine grain, vignette."""
    g = np.asarray(ImageOps.grayscale(img), np.float32) / 255
    g = 0.5 + (g - 0.5) * 1.12
    g = np.clip(g, 0, 1)
    g = g * g * (3 - 2 * g) * 0.35 + g * 0.65
    sh = np.array([14, 16, 20], np.float32)
    hi = np.array([242, 234, 218], np.float32)
    rgb = sh + (hi - sh) * g[..., None]
    lum = Image.fromarray((g * 255).astype(np.uint8))
    bright = lum.point(lambda v: max(0, v - 170) * 3).filter(ImageFilter.GaussianBlur(18))
    rgb += np.asarray(bright, np.float32)[..., None] / 255 * np.array([90, 50, 20]) * halation * warm * 2
    h, w = g.shape
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) - 128
    rgb += n[..., None] / 40 * grain_amt
    yy, xx = np.mgrid[0:h, 0:w]
    dd = ((xx - w / 2) / (w * 0.7)) ** 2 + ((yy - h / 2) / (h * 0.6)) ** 2
    rgb *= np.clip(1 - vignette * dd, 0.25, 1)[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def upscale(src, w, h, centering=(0.5, 0.5)):
    im = ImageOps.fit(src, (w, h), Image.LANCZOS, centering=centering)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def fade(img, y0, y1, color=BG, top=False):
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(y0, y1):
        a = (y - y0) / max(1, y1 - y0)
        a = 1 - a if top else a
        d.line([(0, y), (W, y)], fill=color + (int(255 * a ** 1.6),))


def footer(img, n, title, credit):
    d = ImageDraw.Draw(img)
    d.text((X0, 1488), credit, font=mono(17), fill=(130, 126, 118))
    d.text((X0, 1830), f"DESIGN {n:02d}/42 · {title}", font=mono(20), fill=(100, 96, 90))


def sig(cred):
    return cred.replace("Photo: ", "")


# ------------------------------------------------------------------ 37 portrait + lower third
def d37_portrait():
    src, cred = photo("R17289")
    img = Image.new("RGB", (W, H), BG)
    pic = grade(upscale(src, W, 1320, (0.5, 0.18)), seed=37)
    img.paste(pic, (0, 0))
    fade(img, 820, 1320)
    d = ImageDraw.Draw(img)
    d.line([(X0, 1150), (X0 + 64, 1150)], fill=GOLDL, width=3)
    d.text((X0, 1172), "Paul von Hindenburg", font=serif(64, 600), fill=IVORY)
    d.text((X0, 1256), "Reich President, 1925 – 1934", font=sans(30, 400), fill=MUTED)
    tracked(d, (X0, 1310), "FIELD MARSHAL · AGED 85 IN 1933", sans(20, 500), (150, 140, 120), 0.18)
    tracked(d, (X0, 210), "THE PRESIDENT", sans(22, 600), IVORY, 0.3)
    footer(img, 37, "PORTRAIT · LOWER THIRD", sig(cred))
    return img


# ------------------------------------------------------------------ 38 full-bleed location super
def d38_location():
    src, cred = photo("S38324")
    img = grade(upscale(src, W, H, (0.74, 0.5)), seed=38, vignette=0.5)
    fade(img, 0, 420, top=True)
    fade(img, 1100, 1560)
    ImageDraw.Draw(img).rectangle([0, 1560, W, H], fill=BG)
    d = ImageDraw.Draw(img)
    tracked(d, (X0, 210), "POTSDAM", sans(54, 600), IVORY, 0.22)
    tracked(d, (X0, 280), "21 MARCH 1933", sans(26, 400), GOLDL, 0.3)
    d.line([(X0, 1250), (X0 + 64, 1250)], fill=GOLDL, width=3)
    for i, ln in enumerate(["President Hindenburg on the 'Day of Potsdam'.", "Hitler stages himself as the heir of", "Prussian tradition — and of the old elites."]):
        d.text((X0, 1272 + i * 50), ln, font=serif_i(38, 400), fill=IVORY)
    footer(img, 38, "FULL-BLEED · LOCATION SUPER", sig(cred))
    return img


# ------------------------------------------------------------------ 39 seats chart
def d39_seats():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    tracked(d, (X0, 210), "REICHSTAG ELECTIONS", sans(22, 600), GOLDL, 0.3)
    d.text((X0, 250), "Nazi seats vs. a majority", font=serif(60, 600), fill=IVORY)
    data = [("May 1928", 12, 491), ("Sep 1930", 107, 577), ("Jul 1932", 230, 608), ("Nov 1932", 196, 584), ("Mar 1933*", 288, 647)]
    bx0, bx1 = X0, X1
    y = 460
    for lab, seats, total in data:
        maj = total // 2 + 1
        d.text((bx0, y), lab, font=sans(26, 500), fill=IVORY)
        d.text((bx1, y), f"{seats} / {total}", font=mono(24), fill=MUTED, anchor="ra")
        by = y + 46
        d.rectangle([bx0, by, bx1, by + 26], fill=(34, 34, 37))
        wfrac = seats / total
        col = ACCENT if lab.startswith("Mar") else (172, 150, 112)
        d.rectangle([bx0, by, bx0 + (bx1 - bx0) * wfrac, by + 26], fill=col)
        mx = bx0 + (bx1 - bx0) * maj / total
        d.line([(mx, by - 8), (mx, by + 34)], fill=IVORY, width=3)
        d.text((bx0, by + 36), f"{100 * seats / total:.1f} % of seats", font=sans(20, 400), fill=MUTED)
        y += 168
    d.line([(X0, y + 10), (X0 + 20, y + 10)], fill=IVORY, width=3)
    d.text((X0 + 32, y - 4), "Majority threshold", font=sans(22, 400), fill=IVORY)
    d.text((X0, y + 44), "* Held under terror after the Reichstag Fire Decree.", font=sans(22, 400), fill=MUTED)
    d.text((X0, y + 76), "No free election ever gave the NSDAP a majority.", font=serif_i(30, 400), fill=IVORY)
    footer(img, 39, "DATA · MINIMAL BAR CHART", "Data: official Reichstag election results, 1928–1933")
    return img


# ------------------------------------------------------------------ 40 quote card
def d40_quote():
    src, cred = photo("102-14439")
    img = Image.new("RGB", (W, H), BG)
    src = src.crop((0, int(src.height * 0.45), src.width, src.height))
    pic = grade(upscale(src, W, 900, (0.5, 0.5)), seed=40, vignette=0.6)
    pic = Image.eval(pic, lambda v: int(v * 0.55))
    img.paste(pic, (0, 120))
    fade(img, 120, 360, top=True)
    fade(img, 700, 1020)
    d = ImageDraw.Draw(img)
    d.text((X0 - 8, 860), "“", font=serif(200, 600), fill=ACCENT)
    q = ["Freedom and life", "can be taken from us,", "but not our honour."]
    for i, ln in enumerate(q):
        d.text((X0, 1040 + i * 78), ln, font=serif(66, 500), fill=IVORY)
    d.text((X0, 1290), "„Freiheit und Leben kann man uns nehmen, die Ehre nicht.“", font=serif_i(27, 400), fill=MUTED)
    d.line([(X0, 1352), (X0 + 64, 1352)], fill=GOLDL, width=3)
    d.text((X0, 1370), "Otto Wels, SPD chairman", font=sans(30, 600), fill=IVORY)
    d.text((X0, 1412), "Reichstag, 23 March 1933 — against the Enabling Act", font=sans(24, 400), fill=MUTED)
    footer(img, 40, "QUOTE CARD · ORIGINAL + TRANSLATION", sig(cred) + " (background)")
    return img


# ------------------------------------------------------------------ 41 editorial map
def d41_map():
    geo, _ = load_maps(os.path.join(GEO, "world_1930.geojson"), os.path.join(GEO, "modern.geojson"))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    proj = MapProj(5.5, 23.0, 47.0, 55.6, (40, 330, 1040, 1080))
    for n, rs in geo.items():
        if n in ("Germany", "East Prussia"):
            continue
        for r in rs:
            d.polygon([proj(*p) for p in r], fill=(24, 25, 28), outline=(40, 41, 45))
    for r in germany_rings(geo):
        pts = [proj(*p) for p in r]
        d.polygon(pts, fill=(52, 50, 46), outline=(150, 140, 120))
    places = [("Kiel", 10.13, 54.32, "Nov 1918", "Sailors' mutiny starts the revolution"),
              ("Berlin", 13.40, 52.52, "9 Nov 1918", "The republic is proclaimed"),
              ("Weimar", 11.33, 50.98, "1919", "National Assembly writes the constitution"),
              ("Munich", 11.58, 48.14, "9 Nov 1923", "Beer Hall Putsch fails"),
              ("Landsberg", 10.87, 48.05, "1924", "Hitler in prison, writes Mein Kampf"),
              ("Nuremberg", 11.08, 49.45, "1927 onwards", "Nazi Party rallies"),
              ("Potsdam", 13.06, 52.39, "21 Mar 1933", "'Day of Potsdam'"),
              ("Dachau", 11.43, 48.26, "22 Mar 1933", "Concentration camp opens")]
    offs = {"Potsdam": (-46, 10), "Berlin": (22, -30), "Landsberg": (-52, 30), "Dachau": (-20, -42), "Munich": (40, 26)}
    for i, (name, lon, lat, date, what) in enumerate(places, 1):
        x, y = proj(lon, lat)
        ox, oy = offs.get(name, (18, -14))
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=ACCENT)
        lx, ly = x + ox, y + oy
        d.ellipse([lx - 16, ly - 16, lx + 16, ly + 16], fill=IVORY)
        d.text((lx, ly), str(i), font=sans(20, 700), fill=BG, anchor="mm")
    tracked(d, (X0, 210), "GERMANY 1918 – 1933", sans(22, 600), GOLDL, 0.3)
    d.text((X0, 250), "Where it happened", font=serif(60, 600), fill=IVORY)
    y = 1110
    for i, (name, *_, date, what) in enumerate(places, 1):
        col = i - 1
        cx = X0 if col < 4 else 520
        cy = y + (col % 4) * 84
        d.ellipse([cx, cy + 2, cx + 30, cy + 32], fill=IVORY)
        d.text((cx + 15, cy + 17), str(i), font=sans(18, 700), fill=BG, anchor="mm")
        d.text((cx + 44, cy), f"{name} · {date}", font=sans(22, 600), fill=IVORY)
        d.text((cx + 44, cy + 30), what, font=sans(19, 400), fill=MUTED)
    footer(img, 41, "EDITORIAL MAP · NUMBERED KEY", "Borders c. 1930 (historical-basemaps)")
    return img


# ------------------------------------------------------------------ 42 chapter card
def d42_chapter():
    src, cred = photo("102-11008")
    img = grade(upscale(src, W, H, (0.5, 0.5)).filter(ImageFilter.GaussianBlur(2.5)), seed=42, vignette=0.7)
    img = Image.eval(img, lambda v: int(v * 0.5))
    d = ImageDraw.Draw(img)
    tracked(d, (0, 700), "CHAPTER FOUR", sans(26, 600), GOLDL, 0.45, anchor_center=True)
    d.line([(W / 2 - 40, 760), (W / 2 + 40, 760)], fill=GOLDL, width=2)
    for i, ln in enumerate(["The Great", "Depression"]):
        f = serif(120, 600)
        d.text(((W - d.textlength(ln, font=f)) / 2, 800 + i * 136), ln, font=f, fill=IVORY)
    f = serif_i(40, 400)
    s = "1929 — 1932"
    d.text(((W - d.textlength(s, font=f)) / 2, 1100), s, font=f, fill=MUTED)
    footer(img, 42, "CHAPTER CARD · BLURRED ARCHIVE PLATE", sig(cred) + " (background)")
    return img


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    fns = [d37_portrait, d38_location, d39_seats, d40_quote, d41_map, d42_chapter]
    frames = []
    for i, fn in enumerate(fns, 37):
        im = fn()
        im.save(os.path.join(out, f"design_{i:02d}.png"))
        frames.append(im)
    tw, th = 324, 576
    sheet = Image.new("RGB", (tw * 3 + 40, th * 2 + 30), (8, 8, 8))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (i % 3) * (tw + 10), 10 + (i // 3) * (th + 10)))
    sheet.save(os.path.join(out, "kontaktbogen_5.png"))


if __name__ == "__main__":
    main()
