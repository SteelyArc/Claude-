"""Design examples 31-36: further immersive styles on real Bundesarchiv photos.

Usage: python3 design_frames_4.py <out_dir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import DIM, H, INK, MONO, MONO_L, PAPER, RED, SANS, SANS_B, SERIF, SERIF_B, SERIF_I, W, font, text_c, wrap
from design_frames_2 import GOLD, add_light, dust, glow_text, light_rays
from design_frames_3 import X0, X1, cover, grain, photo, title_block


def footer(img, n, title, credit=None):
    d = ImageDraw.Draw(img)
    if credit:
        for i, ln in enumerate(wrap(d, credit, font(MONO_L, 18), X1 - X0)):
            d.text((X0, 1475 + i * 23), ln, font=font(MONO_L, 18), fill=(165, 158, 145))
    d.text((X0, 1830), f"DESIGN {n:02d}/36 · {title}", font=font(MONO_L, 22), fill=(110, 105, 98))


def shadowed(img, layer, xy, blur=16, off=(14, 20), alpha=170):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, alpha), (0, 0), layer.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    img.paste(sh, (xy[0] + off[0], xy[1] + off[1]), sh)
    img.paste(layer, xy, layer)


def short_sig(credit):
    return credit.replace("Photo: Bundesarchiv, ", "").split(" / ")[0]


# ------------------------------------------------------------------ 31 timeline string
def d31_timeline():
    img = Image.new("RGB", (W, H), (24, 22, 20))
    rng = np.random.default_rng(31)
    a = np.asarray(img, np.float32) + rng.normal(0, 5, (H, W, 1))
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    img = add_light(img, light_rays((W, H), (W / 2, -150), (120, 100, 70), 0.4, seed=31))
    items = [("R95251", "9 NOV 1918", "The Kaiser abdicates"), ("R01217", "1919", "Peace treaties, Paris"),
             ("119-1426", "9 NOV 1923", "The Putsch fails"), ("102-02982A", "30 JAN 1933", "Hitler appointed"),
             ("2006-0429-502", "7 AUG 1934", "Hindenburg buried")]
    pts = []
    credits = []
    for i, (key, date, cap) in enumerate(items):
        src, cred = photo(key)
        credits.append(short_sig(cred))
        left = i % 2 == 0
        w = 380
        h = int(src.height * w / src.width)
        h = min(h, 200)
        pic = ImageOps.fit(src, (w, h), Image.BICUBIC, centering=(0.5, 0.2))
        card = Image.new("RGBA", (w + 30, h + 90), (238, 232, 218, 255))
        card.paste(pic, (15, 15))
        cd = ImageDraw.Draw(card)
        cd.text((15, h + 26), date, font=font(MONO, 22), fill=(150, 34, 26))
        cd.text((15, h + 54), cap, font=font(SERIF_I, 24), fill=INK)
        card = card.rotate((-3 if left else 3) + rng.uniform(-1, 1), resample=Image.BICUBIC, expand=True)
        x = 70 if left else 1010 - card.width
        y = 290 + i * 222
        shadowed(img, card, (x, y))
        pts.append((x + card.width // 2, y + 18))
    d = ImageDraw.Draw(img, "RGBA")
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.line([(x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2 + 30), (x1, y1)], fill=(190, 30, 28, 230), width=4, joint="curve")
    for x, y in pts:
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(200, 30, 30))
        d.ellipse([x - 5, y - 8, x + 2, y - 2], fill=(255, 140, 140))
    img = grain(img, 8, 0.45)
    title_block(img, 160, "1918 – 1934", ["Sixteen years, five photos"], size=60)
    footer(img, 31, "EVIDENCE TIMELINE · RED STRING", "Photos: Bundesarchiv, " + ", ".join(credits) + " / CC BY-SA 3.0 DE")
    return img


# ------------------------------------------------------------------ 32 shattered glass
def d32_shatter():
    src, cred = photo("S38324")
    pw, ph = W, 900
    pic = np.asarray(cover(src, pw, ph), np.float32)
    rng = np.random.default_rng(32)
    cx, cy = 560, 420
    seeds = np.concatenate([rng.normal([cx, cy], [180, 160], (26, 2)), rng.uniform([0, 0], [pw, ph], (20, 2))])
    yy, xx = np.mgrid[0:ph, 0:pw]
    dist = np.stack([(xx - sx) ** 2 + (yy - sy) ** 2 for sx, sy in seeds])
    cell = dist.argmin(0)
    out = np.zeros_like(pic) + 8
    for k, (sx, sy) in enumerate(seeds):
        m = cell == k
        dx, dy = (sx - cx), (sy - cy)
        L = math.hypot(dx, dy) + 1
        sh = min(22, 900 / L) if L < 600 else 2
        ox, oy = int(dx / L * sh), int(dy / L * sh)
        ys, xs = np.nonzero(m)
        ys2 = np.clip(ys - oy, 0, ph - 1)
        xs2 = np.clip(xs - ox, 0, pw - 1)
        tint = 0.82 + 0.25 * rng.random()
        out[ys, xs] = pic[ys2, xs2] * tint
    edges = (np.abs(np.diff(cell, axis=0, prepend=cell[:1])) + np.abs(np.diff(cell, axis=1, prepend=cell[:, :1]))) > 0
    out[edges] = 235
    layer = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    img = Image.new("RGB", (W, H), (8, 8, 9))
    img.paste(layer, (0, 300))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([cx - 10, 300 + cy - 10, cx + 10, 300 + cy + 10], fill=(255, 255, 255, 200))
    img = grain(img, 9, 0.45)
    title_block(img, 160, "POTSDAM · 21 MARCH 1933", ["The handshake"], size=72)
    d = ImageDraw.Draw(img)
    d.text((X0, 1230), "Hindenburg greets Hitler, the man", font=font(SERIF_I, 38), fill=PAPER)
    d.text((X0, 1278), "he believed could be controlled.", font=font(SERIF_I, 38), fill=PAPER)
    footer(img, 32, "SHATTERED GLASS · VORONOI SHARDS", cred)
    return img


# ------------------------------------------------------------------ 33 torn paper reveal
def d33_torn():
    a, ca = photo("R17289")
    b, cb = photo("102-02982A")
    img = Image.new("RGB", (W, H), (12, 11, 10))
    under = ImageOps.fit(b, (W, 1150), Image.BICUBIC)
    img.paste(Image.eval(under, lambda v: int(v * 0.9)), (0, 300))
    top = ImageOps.fit(a, (W, 1150), Image.BICUBIC, centering=(0.5, 0.25))
    top = Image.eval(ImageOps.grayscale(top), lambda v: int(v * 0.95)).convert("RGB")
    rng = np.random.default_rng(33)
    # jagged diagonal tear
    pts = []
    for k in range(41):
        x = k * W / 40
        y = 640 + (x / W) * 260 + rng.normal(0, 16)
        pts.append((x, y))
    mask = Image.new("L", (W, 1150), 0)
    md = ImageDraw.Draw(mask)
    md.polygon([(0, 0), (W, 0)] + [(x, y) for x, y in reversed(pts)], fill=255)
    paper_edge = Image.new("L", (W, 1150), 0)
    ed = ImageDraw.Draw(paper_edge)
    ed.line(pts, fill=255, width=16)
    paper_edge = paper_edge.filter(ImageFilter.GaussianBlur(1.5))
    img.paste(top, (0, 300), mask)
    shadow = Image.new("RGBA", (W, 1150), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.line([(x, y + 14) for x, y in pts], fill=(0, 0, 0, 200), width=26)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.paste(shadow, (0, 300), shadow)
    img.paste(Image.new("RGB", (W, 1150), (236, 228, 210)), (0, 300), paper_edge)
    img = grain(img, 10, 0.45)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 300, W, 360], fill=(0, 0, 0, 140))
    d.text((X0, 314), "THE PRESIDENT · 1932", font=font(MONO, 26), fill=PAPER)
    d.rectangle([0, 1390, W, 1450], fill=(0, 0, 0, 160))
    d.text((X0, 1404), "THE TORCHLIGHT PARADE · 30 JAN 1933", font=font(MONO, 26), fill=GOLD)
    title_block(img, 160, "30 JANUARY 1933", ["Appointed, not elected"], size=66)
    footer(img, 33, "TORN PAPER REVEAL", "Top: " + short_sig(ca) + " · Bottom: " + short_sig(cb) + " · Bundesarchiv / CC BY-SA 3.0 DE")
    return img


# ------------------------------------------------------------------ 34 spotlight stage
def d34_spotlight():
    src, cred = photo("17049")
    img = Image.new("RGB", (W, H), (5, 5, 6))
    pic = ImageOps.fit(src, (760, 1080), Image.BICUBIC, centering=(0.5, 0.3))
    pic = ImageOps.grayscale(pic).convert("RGB")
    yy, xx = np.mgrid[0:1080, 0:760]
    spot = np.clip(1.25 - np.sqrt(((xx - 380) / 360) ** 2 + ((yy - 420) / 520) ** 2), 0.05, 1.0)[..., None]
    pic = Image.fromarray((np.asarray(pic, np.float32) * spot).astype(np.uint8))
    img.paste(pic, (160, 300))
    f = np.asarray(img, np.float32)
    cone = Image.new("L", (W, H), 0)
    cd = ImageDraw.Draw(cone)
    cd.polygon([(500, 0), (580, 0), (980, 1300), (100, 1300)], fill=46)
    cone = cone.filter(ImageFilter.GaussianBlur(40))
    f += np.asarray(cone, np.float32)[..., None] * np.array([1.0, 0.95, 0.8])
    img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    # stage curtains
    for side in (0, 1):
        for k in range(9):
            x = (k * 18) if side == 0 else (W - 160 + k * 18)
            shade = 70 + (k % 2) * 30
            d.rectangle([x, 0, x + 18, H], fill=(shade, 10, 12, 255))
    img = dust(img, 260, seed=34, color=(255, 240, 210), region=(150, 0, 930, 1300))
    img = grain(img, 10, 0.5)
    title_block(img, 160, "BERLIN · 25 AUGUST 1934", ["The propaganda chief"], size=64)
    d = ImageDraw.Draw(img)
    d.text((X0 + 120, 1400), "Joseph Goebbels, Reich Minister of Propaganda", font=font(SERIF_I, 32), fill=PAPER)
    footer(img, 34, "SPOTLIGHT STAGE · CURTAINS + DUST", cred)
    return img


# ------------------------------------------------------------------ 35 negative strip
def d35_negatives():
    a, ca = photo("102-14468, Berlin, NS-Boykott gegen jüdische Geschäfte.jpg")
    b, cb = photo("102-14598")
    c, cc = photo("102-14597")
    img = Image.new("RGB", (W, H), (226, 222, 214))
    lt = np.asarray(img, np.float32) + np.random.default_rng(35).normal(0, 4, (H, W, 1))
    img = Image.fromarray(np.clip(lt, 0, 255).astype(np.uint8))
    strip_w, fh = 820, 300
    strip = Image.new("RGB", (strip_w + 120, 3 * (fh + 40) + 40), (28, 22, 16))
    sd = ImageDraw.Draw(strip)
    for y in range(14, strip.height, 44):
        sd.rounded_rectangle([18, y, 44, y + 22], 4, fill=(226, 222, 214))
        sd.rounded_rectangle([strip.width - 44, y, strip.width - 18, y + 22], 4, fill=(226, 222, 214))
    frames = [(a, False), (b, True), (c, False)]
    for i, (src, positive) in enumerate(frames):
        fr = ImageOps.grayscale(cover(src, strip_w, fh))
        if not positive:
            fr = ImageOps.invert(fr)
            fr = Image.merge("RGB", [fr.point(lambda v: int(v * 0.95 + 10)), fr.point(lambda v: int(v * 0.78)), fr.point(lambda v: int(v * 0.55))])
        else:
            fr = fr.convert("RGB")
        strip.paste(fr, (60, 40 + i * (fh + 40)))
        sd.text((64, 40 + i * (fh + 40) + fh + 6), f"{14 + i}A  ▸  KODAK SAFETY FILM", font=font(MONO, 18), fill=(230, 160, 70))
    strip = strip.convert("RGBA").rotate(-3, resample=Image.BICUBIC, expand=True)
    shadowed(img, strip, (40, 250), blur=20, alpha=120)
    d = ImageDraw.Draw(img, "RGBA")
    # grease-pencil circle around the positive frame
    cx, cy = 520, 250 + 60 + fh + 40 + fh // 2
    for k in range(3):
        d.ellipse([cx - 460 + k * 4, cy - 230 + k * 3, cx + 440 - k * 3, cy + 220 - k * 4], outline=(200, 30, 30, 200), width=6)
    d.text((X0, 150), "1933", font=font(MONO, 30), fill=(150, 34, 26))
    d.text((X0, 190), "Persecution begins", font=font(SERIF_B, 64), fill=INK)
    d.text((X0, 1390), "1 April: boycott of Jewish shops  ·  10 May: book burning", font=font(SERIF_I, 30), fill=INK)
    img = grain(img, 5, 0.25)
    footer(img, 35, "NEGATIVE STRIP · GREASE PENCIL", "Photos: Bundesarchiv, " + ", ".join(short_sig(x) for x in (ca, cb, cc)) + " / CC BY-SA 3.0 DE")
    return img


# ------------------------------------------------------------------ 36 memorial stone
def d36_memorial():
    src, cred = photo("2006-0429-502")
    rng = np.random.default_rng(36)
    n = rng.normal(0, 1, (H // 6, W // 6))
    stone = np.asarray(Image.fromarray(((n - n.min()) / np.ptp(n) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)), np.float32)
    base = 70 + stone[..., None] * 0.25 + rng.normal(0, 6, (H, W, 1))
    img = Image.fromarray(np.clip(base * np.array([1.0, 0.98, 0.94]), 0, 255).astype(np.uint8))
    img = add_light(img, light_rays((W, H), (200, -200), (120, 110, 90), 0.4, seed=36))
    pic = cover(src, 880, 620)
    pic = ImageOps.grayscale(pic).convert("RGB")
    frame = Image.new("RGB", (920, 660), (30, 28, 26))
    frame.paste(pic, (20, 20))
    img.paste(frame, (80, 420))
    d = ImageDraw.Draw(img, "RGBA")

    def carved(xy, s, f, center=False):
        x, y = xy
        if center:
            x = (W - d.textlength(s, font=f)) / 2
        d.text((x + 2, y + 2), s, font=f, fill=(225, 220, 210, 170))
        d.text((x, y), s, font=f, fill=(12, 11, 10, 255))

    carved((0, 200), "2 · VIII · 1934", font(SERIF_B, 64), True)
    carved((0, 290), "THE LAST OBSTACLE", font(SERIF, 40), True)
    carved((0, 1130), "Hindenburg is buried at the Tannenberg Memorial,", font(SERIF_I, 34), True)
    carved((0, 1176), "7 August 1934. Hitler is now head of state,", font(SERIF_I, 32), True)
    carved((0, 1222), "head of government and supreme commander.", font(SERIF_I, 32), True)
    # candles
    for x in (150, 930):
        d.rectangle([x - 14, 1290, x + 14, 1400], fill=(225, 215, 190))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([x - 60, 1210, x + 60, 1330], fill=(255, 180, 80, 120))
        glow = glow.filter(ImageFilter.GaussianBlur(20))
        img.paste(glow, (0, 0), glow)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 7, 1258, x + 7, 1288], fill=(255, 220, 140))
    img = grain(img, 8, 0.5)
    footer(img, 36, "MEMORIAL STONE · CARVED TYPE + CANDLES", cred)
    return img


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    fns = [d31_timeline, d32_shatter, d33_torn, d34_spotlight, d35_negatives, d36_memorial]
    frames = []
    for i, fn in enumerate(fns, 31):
        im = fn()
        im.save(os.path.join(out, f"design_{i:02d}.png"))
        frames.append(im)
    tw, th = 324, 576
    sheet = Image.new("RGB", (tw * 3 + 40, th * 2 + 30), (10, 10, 10))
    for i, im in enumerate(frames):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (i % 3) * (tw + 10), 10 + (i // 3) * (th + 10)))
    sheet.save(os.path.join(out, "kontaktbogen_4.png"))


if __name__ == "__main__":
    main()
