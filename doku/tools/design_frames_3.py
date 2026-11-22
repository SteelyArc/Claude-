"""Design examples 21-30: immersive styles built on real Bundesarchiv photos.

Usage: python3 design_frames_3.py <out_dir>
Illustrated elements are labelled ILLUSTRATION; photos carry their archive credit.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import DIM, H, INK, MONO, MONO_L, PAPER, RED, SANS, SANS_B, SERIF, SERIF_B, SERIF_I, W, font, text_c, wrap
from design_frames_2 import GOLD, add_light, dust, glow_text, light_rays

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PH = os.path.join(ROOT, "archive", "photos")
X0, X1 = 64, 936  # TikTok-safe text column


def photo(key):
    for c in json.load(open(os.path.join(PH, "credits.json"))):
        if key in c["title"]:
            sig = c["title"].replace("File:Bundesarchiv ", "").split(",")[0]
            art = c["artist"].replace("Unknown authorUnknown author", "unknown").replace("UnknownUnknown", "unknown")
            return Image.open(os.path.join(PH, c["file"])).convert("RGB"), f"Photo: Bundesarchiv, {sig} / {art or 'unknown'} / CC BY-SA 3.0 DE"
    raise KeyError(key)


def grain(img, amt=12, vig=0.5, seed=1):
    rng = np.random.default_rng(seed)
    a = np.asarray(img, np.float32) + rng.normal(0, amt, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    d = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2
    a *= np.clip(1 - vig * d ** 1.1, 0, 1)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def footer(img, n, title, credit=None):
    d = ImageDraw.Draw(img)
    if credit:
        for i, ln in enumerate(wrap(d, credit, font(MONO_L, 18), X1 - X0)):
            d.text((X0, 1475 + i * 23), ln, font=font(MONO_L, 18), fill=(165, 158, 145))
    d.text((X0, 1830), f"DESIGN {n:02d}/30 · {title}", font=font(MONO_L, 22), fill=(110, 105, 98))


def title_block(img, y, kicker, lines, color=PAPER, size=78):
    d = ImageDraw.Draw(img)
    d.text((X0, y), kicker, font=font(MONO, 28), fill=GOLD)
    for i, ln in enumerate(lines):
        glow_text(img, (X0, y + 44 + i * (size + 8)), ln, font(SERIF_B, size), color, radius=12, strength=1)


def cover(src, w, h):
    return ImageOps.fit(src, (w, h), Image.BICUBIC)


# ------------------------------------------------------------------ 21 archive desk
def d21_desk():
    rng = np.random.default_rng(21)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    grainw = np.sin(xx / 9 + np.sin(yy / 140) * 6 + rng.normal(0, 0.3, (H, W))) * 0.5 + 0.5
    wood = np.stack([60 + 30 * grainw, 38 + 18 * grainw, 24 + 10 * grainw], -1)
    lamp = np.clip(1.25 - np.sqrt(((xx - 560) / 900) ** 2 + ((yy - 760) / 1000) ** 2) * 1.6, 0.12, 1.25)[..., None]
    img = Image.fromarray(np.clip(wood * lamp, 0, 255).astype(np.uint8))

    def print_(src, w, rot, xy):
        h = int(src.height * w / src.width)
        p = Image.new("RGBA", (w + 36, h + 36), (238, 232, 218, 255))
        p.paste(src.resize((w, h), Image.BICUBIC), (18, 18))
        p = p.rotate(rot, resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", p.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), (0, 0), p.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        img.paste(sh, (xy[0] + 22, xy[1] + 28), sh)
        img.paste(p, xy, p)

    a, cred = photo("119-1426")
    b, _ = photo("102-14381")
    print_(b, 430, 7, (480, 420))
    print_(a, 820, -3, (90, 560))
    d = ImageDraw.Draw(img, "RGBA")
    # index card
    card = Image.new("RGBA", (470, 250), (246, 240, 222, 255))
    cd = ImageDraw.Draw(card)
    for i in range(5):
        cd.line([(20, 70 + i * 36), (450, 70 + i * 36)], fill=(150, 170, 200, 255), width=1)
    cd.line([(20, 52), (450, 52)], fill=(200, 80, 70, 255), width=2)
    cd.text((22, 14), "BUNDESARCHIV · BILD 119-1426", font=font(MONO, 20), fill=INK)
    cd.text((22, 76), "Munich, Odeonsplatz", font=font(MONO, 22), fill=INK)
    cd.text((22, 112), "after the clash, 9 Nov 1923", font=font(MONO, 22), fill=INK)
    cd.text((22, 148), "Beer Hall Putsch fails", font=font(MONO, 22), fill=(160, 40, 30))
    card = card.rotate(4, resample=Image.BICUBIC, expand=True)
    img.paste(card, (430, 1090), card)
    # paperclip
    d.rounded_rectangle([150, 540, 182, 640], 14, outline=(190, 190, 195), width=5)
    img = grain(img, 8, 0.35)
    title_block(img, 190, "9 NOVEMBER 1923", ["The Beer Hall Putsch"], size=70)
    footer(img, 21, "ARCHIVE DESK · PHOTO PRINTS + INDEX CARD", cred)
    return img


# ------------------------------------------------------------------ 22 projection room
def d22_projector():
    img = Image.new("RGB", (W, H), (6, 6, 8))
    src, cred = photo("146-1977-148-19A")
    scr = cover(src, 900, 650)
    scr = Image.eval(scr, lambda v: int(v * 0.92 + 10))
    # keystone + light falloff on screen
    yy, xx = np.mgrid[0:650, 0:900]
    fall = np.clip(1.15 - np.sqrt(((xx - 450) / 600) ** 2 + ((yy - 300) / 500) ** 2), 0.4, 1.0)[..., None]
    scr = Image.fromarray((np.asarray(scr) * fall).astype(np.uint8))
    img.paste(scr, (90, 360))
    f = np.asarray(img, np.float32)
    beam = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(beam)
    bd.polygon([(1020, 1705), (990, 1010), (90, 1010), (90, 360), (990, 360)], fill=38)
    bd.polygon([(1020, 1705), (700, 900), (300, 700), (500, 520)], fill=22)
    beam = beam.filter(ImageFilter.GaussianBlur(28))
    f += np.asarray(beam, np.float32)[..., None] * np.array([1.0, 0.95, 0.85]) * 1.2
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    img = dust(img, 420, seed=22, color=(255, 245, 220), region=(120, 380, 1060, 1700))
    d = ImageDraw.Draw(img, "RGBA")
    # silhouetted seat rows
    for row in range(3):
        y = 1320 + row * 120
        for k in range(7):
            x = 40 + k * 150 + (row % 2) * 60
            d.ellipse([x, y, x + 110, y + 130], fill=(4, 4, 5, 255))
            d.ellipse([x + 30, y - 60, x + 80, y + 4], fill=(4, 4, 5, 255))
    d.ellipse([1005, 1690, 1035, 1720], fill=(255, 250, 230))
    img = grain(img, 10, 0.45)
    title_block(img, 190, "27 FEBRUARY 1933", ["The morning after"], size=66)
    d = ImageDraw.Draw(img)
    d.text((X0, 1040), "ONLOOKERS AT THE BURNT-OUT REICHSTAG", font=font(MONO, 22), fill=GOLD)
    footer(img, 22, "PROJECTION ROOM · BEAM + DUST", cred)
    return img


# ------------------------------------------------------------------ 23 halftone print
def d23_halftone():
    src, cred = photo("102-14439")
    g = ImageOps.grayscale(cover(src.crop((0, int(src.height * 0.42), src.width, src.height)), W, 980))
    g = ImageOps.autocontrast(g, cutoff=2)
    paper = Image.new("RGB", (W, H), (232, 224, 205))
    dots = Image.new("L", (W, 980), 255)
    dd = ImageDraw.Draw(dots)
    a = np.asarray(g, np.float32) / 255
    step = 11
    for y in range(0, 980, step):
        for x in range(0, W, step):
            v = 1 - a[y:y + step, x:x + step].mean()
            r = v * step * 0.72
            cx, cy = x + step / 2 + (step / 2 if (y // step) % 2 else 0), y + step / 2
            if r > 0.4:
                dd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    ink = Image.new("RGB", (W, 980), (24, 22, 20))
    paper.paste(ink, (0, 240), ImageOps.invert(dots))
    d = ImageDraw.Draw(paper, "RGBA")
    # red overprint band, slightly misregistered
    d.rectangle([0, 1080, W, 1260], fill=(170, 34, 28, 230))
    d.text((X0 + 4, 1096), "444 : 94", font=font(SERIF_B, 120), fill=(120, 20, 16))
    d.text((X0, 1092), "444 : 94", font=font(SERIF_B, 120), fill=(246, 238, 220))
    d.text((X0, 150), "23 MARCH 1933 · KROLL OPERA HOUSE", font=font(MONO, 28), fill=(140, 30, 24))
    d.text((X0, 186), "The Enabling Act", font=font(SERIF_B, 46), fill=INK)
    d.text((X0, 1290), "Parliament votes away its own power.", font=font(SERIF_I, 38), fill=INK)
    d.text((X0, 1340), "Only the Social Democrats vote no.", font=font(SERIF_I, 38), fill=INK)
    img = grain(paper, 7, 0.3)
    footer(img, 23, "HALFTONE PRINT · RED OVERPRINT", cred)
    return img


# ------------------------------------------------------------------ 24 rain window
def d24_rain():
    src, cred = photo("102-11008")
    base = cover(src, W, H)
    blur = base.filter(ImageFilter.GaussianBlur(9))
    f = np.asarray(blur, np.float32) * np.array([0.62, 0.72, 0.85]) * 0.8
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    sharp = Image.fromarray(np.clip(np.asarray(base, np.float32) * np.array([0.75, 0.82, 0.95]), 0, 255).astype(np.uint8))
    rng = np.random.default_rng(24)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.choice([2, 3, 4, 5, 7, 10, 14])
        md.ellipse([x - r, y - r * 1.15, x + r, y + r * 1.15], fill=255)
        hd.ellipse([x - r * 0.45, y - r * 0.7, x - r * 0.05, y - r * 0.3], fill=(255, 255, 255, 120))
    for _ in range(40):
        x = rng.uniform(0, W)
        y0 = rng.uniform(0, H * 0.6)
        L = rng.uniform(150, 700)
        md.line([(x, y0), (x + rng.normal(0, 8), y0 + L)], fill=200, width=int(rng.choice([2, 3, 4])))
    img.paste(sharp, (0, 0), mask.filter(ImageFilter.GaussianBlur(0.8)))
    img.paste(hl, (0, 0), hl)
    img = add_light(img, light_rays((W, H), (900, -100), (90, 110, 140), 0.35, seed=24))
    img = grain(img, 9, 0.5)
    title_block(img, 190, "HAMBURG · JANUARY 1931", ["Waiting for work"], size=72)
    d = ImageDraw.Draw(img)
    d.text((X0, 1360), "Unemployed dockworkers in the harbour district", font=font(SERIF_I, 34), fill=PAPER)
    footer(img, 24, "RAIN WINDOW · REFRACTED DROPS", cred)
    return img


# ------------------------------------------------------------------ 25 burning edge
def d25_burn():
    src, cred = photo("146-1977-148-19A")
    img = Image.new("RGB", (W, H), (8, 6, 5))
    pw, ph = 960, 700
    pic = cover(src, pw, ph)
    rng = np.random.default_rng(25)
    n = rng.normal(0, 1, (ph // 30 + 2, pw // 30 + 2))
    n = np.asarray(Image.fromarray(((n - n.min()) / np.ptp(n) * 255).astype(np.uint8)).resize((pw, ph), Image.BICUBIC), np.float32) / 255
    yy, xx = np.mgrid[0:ph, 0:pw]
    edge = np.minimum.reduce([xx, yy, pw - xx, ph - yy]).astype(np.float32) / 160
    field = edge + (n - 0.5) * 0.9
    alpha = np.clip((field - 0.15) * 6, 0, 1)
    rim = np.clip(1 - np.abs(field - 0.2) * 8, 0, 1)
    char = np.clip(1 - np.abs(field - 0.32) * 5, 0, 1)
    p = np.asarray(pic, np.float32) * (1 - 0.8 * char[..., None])
    p = p * alpha[..., None] + rim[..., None] * np.array([255, 120, 30]) * 1.2
    layer = Image.fromarray(np.clip(p, 0, 255).astype(np.uint8))
    m = Image.fromarray((np.clip(alpha + rim, 0, 1) * 255).astype(np.uint8))
    glow = Image.fromarray((rim * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))
    gl = Image.new("RGB", (pw, ph), (255, 110, 20))
    ox, oy = 60, 380
    img.paste(gl, (ox, oy), glow)
    img.paste(layer, (ox, oy), m)
    img = add_light(img, light_rays((W, H), (W / 2, 1150), (255, 100, 30), 0.35, seed=25))
    sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for _ in range(260):
        x, y = rng.uniform(60, 1020), rng.uniform(250, 1150)
        sd.line([(x, y), (x + rng.normal(0, 2), y - rng.uniform(4, 16))], fill=(255, int(rng.uniform(120, 220)), 60, int(rng.uniform(80, 220))), width=2)
    img.paste(sp, (0, 0), sp)
    img = grain(img, 10, 0.5)
    title_block(img, 190, "BERLIN · FEBRUARY 1933", ["Fire and Fear"], color=(255, 210, 160), size=84)
    d = ImageDraw.Draw(img)
    d.text((X0, 1200), "The next day, basic rights", font=font(SERIF_I, 40), fill=PAPER)
    d.text((X0, 1250), "were suspended.", font=font(SERIF_I, 40), fill=PAPER)
    footer(img, 25, "BURNING EDGE · EMBERS", cred)
    return img


# ------------------------------------------------------------------ 26 investigation lens
def d26_lens():
    src, cred = photo("119-1426")
    big = cover(src, W, 900)
    dark = Image.eval(big, lambda v: int(v * 0.45))
    img = Image.new("RGB", (W, H), (12, 12, 13))
    img.paste(dark, (0, 300))
    # magnify banner region (src 800x481: banner ~ x310-490, y150-195)
    sc = 900 / src.height
    cx, cy = min(640 * sc - (src.width * sc - W) / 2, 960), 276 * sc
    R, mag = 230, 2.3
    crop = big.crop((int(cx - R / mag), int(cy - R / mag), int(cx + R / mag), int(cy + R / mag))).resize((2 * R, 2 * R), Image.BICUBIC)
    m = Image.new("L", (2 * R, 2 * R), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
    lx, ly = 300, 700
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([lx - R + 20, ly - R + 30, lx + R + 20, ly + R + 30], fill=(0, 0, 0, 180))
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    img.paste(sh, (0, 0), sh)
    img.paste(crop, (int(lx - R), int(ly - R)), m)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([lx - R, ly - R, lx + R, ly + R], outline=(210, 200, 180), width=10)
    d.arc([lx - R + 22, ly - R + 22, lx + R - 22, ly + R - 22], 200, 250, fill=(255, 255, 255, 150), width=6)
    d.line([(lx + R * 0.7, ly + R * 0.7), (lx + R * 1.25, ly + R * 1.25)], fill=(60, 50, 40), width=34)
    # annotation
    ax, ay = cx, 300 + cy
    d.line([(lx + R, ly - 40), (ax, ay)], fill=GOLD + (220,), width=2)
    d.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], fill=GOLD)
    d.text((lx + R + 20, ly - 10), "Banner:", font=font(MONO, 24), fill=GOLD)
    d.text((lx + R + 20, ly + 24), "'Vom Hitlerputsch", font=font(SERIF_I, 30), fill=PAPER)
    d.text((lx + R + 20, ly + 60), " am 9.11.23'", font=font(SERIF_I, 30), fill=PAPER)
    d.text((lx + R + 20, ly + 104), "Odeonsplatz after", font=font(SANS, 26), fill=DIM)
    d.text((lx + R + 20, ly + 136), "the clash", font=font(SANS, 26), fill=DIM)
    img = grain(img, 9, 0.45)
    title_block(img, 190, "MUNICH · 9 NOVEMBER 1923", ["Read the evidence"], size=70)
    footer(img, 26, "INVESTIGATION LENS · ANNOTATION", cred)
    return img


# ------------------------------------------------------------------ 27 typewriter dossier
def d27_dossier():
    src, cred = photo("152-01-16")
    img = Image.new("RGB", (W, H), (214, 205, 182))
    rng = np.random.default_rng(27)
    a = np.asarray(img, np.float32) + rng.normal(0, 7, (H, W, 1))
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    tf = font(MONO, 34)
    y = 760
    text = ("DACHAU, 22 MARCH 1933. Seven weeks after Hitler became Chancellor, a camp opens "
            "near Munich for political prisoners: Communists, Social Democrats, trade unionists. "
            "Run by the SS from April, it becomes the model for the camp system to come.")
    for ln in wrap(d, text, tf, 860):
        for k, ch in enumerate(ln):
            pass
        d.text((X0 + 20 + rng.normal(0, 0.6), y), ln, font=tf, fill=(30, 28, 26, int(rng.uniform(200, 250))))
        y += 52
    pic = cover(src, 700, 452)
    pp = Image.new("RGBA", (740, 492), (244, 240, 230, 255))
    pp.paste(pic, (20, 20))
    pp = pp.rotate(-2.5, resample=Image.BICUBIC, expand=True)
    img.paste(pp, (150, 250), pp)
    d = ImageDraw.Draw(img, "RGBA")
    d.line([(520, 236), (600, 236)], fill=(150, 150, 155), width=6)
    st = Image.new("RGBA", (360, 120), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([4, 4, 356, 116], 10, outline=(170, 30, 25, 210), width=6)
    sd.text((30, 26), "1933", font=font(SERIF_B, 70), fill=(170, 30, 25, 210))
    st = st.rotate(12, resample=Image.BICUBIC, expand=True)
    img.paste(st, (600, 1230), st)
    # depth of field: blur top and bottom bands
    f = np.asarray(img, np.float32)
    bl = np.asarray(img.filter(ImageFilter.GaussianBlur(7)), np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    m = np.clip(np.abs(yy - 0.5) * 3.2 - 0.9, 0, 1)
    img = Image.fromarray((f * (1 - m) + bl * m).astype(np.uint8))
    img = grain(img, 6, 0.55)
    d = ImageDraw.Draw(img)
    d.text((X0, 150), "THE FIRST CAMPS", font=font(MONO, 28), fill=(140, 30, 24))
    d.text((X0, 1180), "SS guard unit, Dachau, 1933", font=font(MONO, 22), fill=(60, 56, 50))
    footer(img, 27, "TYPEWRITER DOSSIER · DEPTH OF FIELD", cred)
    return img


# ------------------------------------------------------------------ 28 double exposure
def d28_double():
    a, cred = photo("183-1987-0703-506")
    b, cred_b = photo("102-11008")
    base = Image.eval(ImageOps.grayscale(cover(a, W, H)), lambda v: int(v * 0.85)).convert("RGB")
    over = ImageOps.grayscale(cover(b, W, H)).convert("RGB")
    img = ImageChops.screen(Image.eval(base, lambda v: int(v * 0.7)), Image.eval(over, lambda v: int(v * 0.45)))
    f = np.asarray(img, np.float32) * np.array([1.0, 0.93, 0.8])
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = 780, 560
    for r in range(80, 1100, 70):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 210, 140, max(10, 90 - r // 14)), width=3)
    img = add_light(img, light_rays((W, H), (cx, cy), (255, 190, 110), 0.3, seed=28))
    img = grain(img, 11, 0.55)
    title_block(img, 1120, "1 FEBRUARY 1933", ["The voice", "on the radio"], size=84)
    d = ImageDraw.Draw(img)
    d.text((X0, 1360), "Hitler's first radio address as Chancellor", font=font(SERIF_I, 34), fill=PAPER)
    footer(img, 28, "DOUBLE EXPOSURE · RADIO WAVES", cred + " · " + cred_b.replace("Photo: ", ""))
    return img


# ------------------------------------------------------------------ 29 searchlights
def d29_searchlights():
    img = Image.new("RGB", (W, H), (6, 8, 14))
    f = np.asarray(img, np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    f = f + (1 - yy) * np.array([10, 14, 26])
    beams = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(beams)
    for x0, ang in ((120, -0.35), (360, -0.12), (700, 0.1), (960, 0.32), (520, -0.02)):
        L = 2200
        dx, dy = math.sin(ang) * L, -math.cos(ang) * L
        bd.polygon([(x0 - 10, 1300), (x0 + 10, 1300), (x0 + dx + 120, 1300 + dy), (x0 + dx - 120, 1300 + dy)], fill=70)
    beams = beams.filter(ImageFilter.GaussianBlur(26))
    f += np.asarray(beams, np.float32)[..., None] * np.array([1.0, 1.0, 0.95])
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    sil = (3, 3, 5)
    # simplified Brandenburg Gate + skyline silhouette (illustration)
    base = 1310
    d.rectangle([0, base, W, H], fill=sil)
    gx = 540
    d.rectangle([gx - 330, base - 260, gx + 330, base - 220], fill=sil)
    d.polygon([(gx - 120, base - 260), (gx + 120, base - 260), (gx, base - 330)], fill=sil)
    for k in range(6):
        x = gx - 300 + k * 120
        d.rectangle([x, base - 220, x + 36, base], fill=sil)
    d.rectangle([gx - 40, base - 380, gx + 40, base - 330], fill=sil)
    for x, h in ((0, 120), (80, 180), (160, 90), (860, 150), (930, 220), (1010, 110)):
        d.rectangle([x, base - h, x + 75, base], fill=sil)
    img = dust(img, 150, seed=29, color=(220, 225, 240), region=(0, 0, W, 1200))
    img = grain(img, 9, 0.45)
    title_block(img, 190, "2 AUGUST 1934", ["The Führer state"], size=80)
    d = ImageDraw.Draw(img)
    d.text((X0, 1360), "Hindenburg is dead. Hitler takes both offices.", font=font(SERIF_I, 34), fill=PAPER)
    d.text((X0, 1405), "The army swears an oath to him personally.", font=font(SERIF_I, 34), fill=PAPER)
    footer(img, 29, "SEARCHLIGHTS · NIGHT SILHOUETTE", "ILLUSTRATION · not archive footage")
    return img


# ------------------------------------------------------------------ 30 split then/now
def d30_split():
    a, ca = photo("146-1989-072-16")
    b, cb = photo("152-01-16")
    img = Image.new("RGB", (W, H), (10, 10, 11))
    top = ImageOps.fit(a, (W, 640), Image.BICUBIC, centering=(0.5, 0.15))
    bot = cover(b, W, 480)
    img.paste(Image.eval(top, lambda v: int(v * 0.9)), (0, 240))
    img.paste(Image.eval(bot, lambda v: int(v * 0.85)), (0, 900))
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(0, 870), (W, 840), (W, 910), (0, 940)], fill=(10, 10, 11, 255))
    d.line([(0, 870), (W, 840)], fill=RED, width=5)
    d.rectangle([0, 240, W, 330], fill=(0, 0, 0, 150))
    d.text((X0, 262), "1919 · REPUBLIC", font=font(MONO, 32), fill=PAPER)
    d.rectangle([0, 1380, W, 1444], fill=(0, 0, 0, 175))
    d.text((X0, 1392), "1933 · DICTATORSHIP", font=font(MONO, 32), fill=(230, 110, 95))
    d.text((X0, 790), "Matthias Erzberger signed the 1918 armistice —", font=font(SERIF_I, 28), fill=PAPER)
    d.text((X0, 824), "murdered by nationalist extremists in 1921.", font=font(SERIF_I, 28), fill=PAPER)
    d.text((X0, 1330), "SS guard unit, Dachau concentration camp", font=font(SERIF_I, 28), fill=PAPER)
    img = grain(img, 9, 0.45)
    d = ImageDraw.Draw(img)
    d.text((X0, 150), "FOURTEEN YEARS", font=font(MONO, 28), fill=GOLD)
    d.text((X0, 186), "From democracy to terror", font=font(SERIF_B, 46), fill=PAPER)
    footer(img, 30, "SPLIT TIME · THEN / AFTER", ca.replace("Photo: ", "Top: ") + " · " + cb.replace("Photo: ", "Bottom: "))
    return img


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    fns = [d21_desk, d22_projector, d23_halftone, d24_rain, d25_burn, d26_lens, d27_dossier, d28_double,
           d29_searchlights, d30_split]
    frames = []
    for i, fn in enumerate(fns, 21):
        im = fn()
        im.save(os.path.join(out, f"design_{i:02d}.png"))
        frames.append(im)
    tw, th = 324, 576
    sheet = Image.new("RGB", (tw * 5 + 60, th * 2 + 30), (10, 10, 10))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (i % 5) * (tw + 10), 10 + (i // 5) * (th + 10)))
    sheet.save(os.path.join(out, "kontaktbogen_3.png"))


if __name__ == "__main__":
    main()
