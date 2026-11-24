"""Six overall look-and-feel designs. Each renders a content frame + a chapter card (1920x1080)."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance
from scipy.ndimage import gaussian_filter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
IMG = os.path.join(ROOT, "assets", "images")
W, H = 1920, 1080

CROPS = {  # fractional crops removing scan borders / colour charts
    "plumbcake_1774": (0.14, 0.05, 0.80, 0.95),
    "europe_july_1772": (0.07, 0.14, 0.93, 0.79),
    "prussian_prizefighter_1791": (0.04, 0.30, 0.97, 0.70),
    "kosciuszko_general_182x": (0.05, 0.03, 0.91, 0.97),
    "stanislaw_to_church_1791": (0.0, 0.0, 1.0, 0.86),
    "stanislaw_portrait": (0.0, 0.0, 1.0, 0.80),
    "kosciuszko_1870": (0.0, 0.0, 1.0, 0.72),
    "catherine_ii_b": (0.10, 0.04, 0.84, 0.86),
    "rozbior_1795_print1891": (0.0, 0.0, 1.0, 1.0),
    "suvorov": (0.0, 0.0, 1.0, 0.80),
}


def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var:
        try: f.set_variation_by_name(var)
        except Exception: pass
    return f


def load(name):
    im = Image.open(os.path.join(IMG, name + ".jpg")).convert("RGB")
    if name in CROPS:
        l, t, r, b = CROPS[name]; w, h = im.size
        im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    return im


def cover(im, w, h, focus=(0.5, 0.4)):
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, int(im.width * s)), max(h, int(im.height * s))), Image.LANCZOS)
    x = int((im.width - w) * focus[0]); y = int((im.height - h) * focus[1])
    return im.crop((x, y, x + w, y + h))


def contain(im, w, h):
    im = im.copy(); im.thumbnail((w, h), Image.LANCZOS)
    if im.width < w and im.height < h:
        s = min(w / im.width, h / im.height); im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    return im


def tone(im, dark, light, contrast=1.0):
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    if contrast != 1.0:
        g = ImageEnhance.Contrast(g).enhance(contrast)
    return ImageOps.colorize(g, dark, light)


def grain(im, amt=10, seed=0):
    a = np.asarray(im).astype(np.float32)
    n = np.random.default_rng(seed).normal(0, amt, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))


def vignette(im, strength=0.6, power=2.0):
    y, x = np.mgrid[0:im.height, 0:im.width]
    r = np.sqrt(((x - im.width / 2) / (im.width / 2)) ** 2 + ((y - im.height / 2) / (im.height / 2)) ** 2) / 1.414
    m = 1 - strength * np.clip(r, 0, 1) ** power
    return Image.fromarray(np.clip(np.asarray(im).astype(np.float32) * m[..., None], 0, 255).astype(np.uint8))


def hgrad(w, h, c, a0, a1, x0=0.0, x1=1.0):
    """horizontal alpha gradient layer of colour c from alpha a0 (left) to a1 (right)"""
    x = np.clip((np.linspace(0, 1, w) - x0) / max(1e-6, x1 - x0), 0, 1)
    a = (a0 + (a1 - a0) * x)[None, :].repeat(h, 0)
    arr = np.zeros((h, w, 4), np.uint8); arr[..., :3] = c; arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def vgrad(w, h, c, a0, a1, y0=0.0, y1=1.0):
    y = np.clip((np.linspace(0, 1, h) - y0) / max(1e-6, y1 - y0), 0, 1)
    a = (a0 + (a1 - a0) * y)[:, None].repeat(w, 1)
    arr = np.zeros((h, w, 4), np.uint8); arr[..., :3] = c; arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def paper(w, h, base=(232, 220, 190), dark=(196, 176, 136), seed=1):
    rng = np.random.default_rng(seed)
    n = sum(gaussian_filter(rng.standard_normal((h // 2, w // 2)), s) * s for s in (1, 6, 40))
    n = (n - n.min()) / (n.max() - n.min())
    a = np.asarray(base)[None, None] * (1 - n[..., None]) + np.asarray(dark)[None, None] * n[..., None]
    return Image.fromarray(a.astype(np.uint8)).resize((w, h), Image.BICUBIC)


def shadow(canvas, box, radius=30, offset=(14, 18), opacity=150):
    sh = Image.new("L", canvas.size, 0)
    d = ImageDraw.Draw(sh); x0, y0, x1, y1 = box
    d.rectangle((x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]), fill=opacity)
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    black = Image.new("RGB", canvas.size, (0, 0, 0))
    canvas.paste(black, (0, 0), sh)


def text(d, xy, s, f, fill, anchor="la", spacing=0, **kw):
    if spacing:
        x, y = xy
        if anchor[0] == "m":
            total = sum(d.textlength(ch, font=f) + spacing for ch in s) - spacing; x -= total / 2; anchor = "l" + anchor[1]
        for ch in s:
            d.text((x, y), ch, font=f, fill=fill, anchor=anchor, **kw); x += d.textlength(ch, font=f) + spacing
    else:
        d.text(xy, s, font=f, fill=fill, anchor=anchor, **kw)


def letterbox(im, ratio=2.39):
    bar = int((H - W / ratio) / 2)
    d = ImageDraw.Draw(im); d.rectangle((0, 0, W, bar), fill=(0, 0, 0)); d.rectangle((0, H - bar, W, H), fill=(0, 0, 0))
    return bar


# ---------------------------------------------------------------------------
def d1_royal_archive(out):
    gold, ivory = (212, 175, 106), (240, 230, 210)
    # content: King's portrait, sepia, lower third
    im = Image.new("RGB", (W, H), (18, 13, 9))
    p = tone(load("stanislaw_portrait"), (26, 18, 10), (236, 214, 170), 1.1)
    p = cover(p, 1150, H, (0.5, 0.25)); im.paste(p, (W - 1150, 0))
    im.paste(hgrad(W, H, (18, 13, 9), 1, 0, 0.38, 0.62), (0, 0), hgrad(W, H, (18, 13, 9), 1, 0, 0.38, 0.62))
    im = vignette(im, 0.55); d = ImageDraw.Draw(im)
    d.line((120, 760, 560, 760), fill=gold, width=2)
    text(d, (120, 700), "STANISŁAW AUGUST PONIATOWSKI", font("Cinzel.ttf", 40, "Bold"), gold)
    text(d, (120, 785), "King of Poland and Grand Duke of Lithuania · 1764–1795", font("EBGaramond-Italic.ttf", 34), ivory)
    text(d, (120, 1030), "Engraving after a portrait of the King · Library of Congress", font("EBGaramond.ttf", 20), (150, 135, 110))
    grain(im, 9).save(out + "_a.png")
    # chapter card
    bg = tone(load("plumbcake_1774"), (12, 9, 6), (120, 96, 60)).filter(ImageFilter.GaussianBlur(6))
    im = cover(bg, W, H, (0.5, 0.45)); im = ImageEnhance.Brightness(im).enhance(0.55); im = vignette(im, 0.85)
    d = ImageDraw.Draw(im)
    text(d, (W / 2, 400), "CHAPTER II", font("Cinzel.ttf", 34), gold, "mm", spacing=10)
    d.line((W / 2 - 260, 450, W / 2 + 260, 450), fill=gold, width=1)
    text(d, (W / 2, 540), "The Sovereignty Crisis", font("Cinzel.ttf", 84, "Bold"), ivory, "mm")
    text(d, (W / 2, 630), "of Poland-Lithuania", font("EBGaramond-Italic.ttf", 56), (220, 200, 160), "mm")
    d.line((W / 2 - 260, 700, W / 2 + 260, 700), fill=gold, width=1)
    grain(im, 10, 1).save(out + "_b.png")


def d2_cold_empire(out):
    steel = (150, 180, 205)
    im = Image.new("RGB", (W, H), (8, 12, 16))
    p = tone(load("catherine_ii_b"), (6, 10, 16), (196, 214, 228), 1.25)
    p = cover(p, W, int(W / 2.39) + 40, (0.5, 0.2))
    im.paste(p, (0, (H - p.height) // 2))
    im.paste(hgrad(W, H, (6, 10, 16), 0.95, 0, 0.0, 0.55), (0, 0), hgrad(W, H, (6, 10, 16), 0.95, 0, 0.0, 0.55))
    bar = letterbox(im); d = ImageDraw.Draw(im)
    text(d, (130, 520), "CATHERINE II", font("Bebas.ttf", 120), (235, 240, 245))
    text(d, (136, 640), "EMPRESS OF RUSSIA  ·  1762–1796", font("Oswald.ttf", 30), steel, spacing=4)
    d.rectangle((136, 690, 220, 694), fill=(200, 60, 60))
    text(d, (W - 40, H - bar - 26), "19th-century engraving · Library of Congress", font("Inter.ttf", 18), (120, 135, 150), "rs")
    grain(im, 7).save(out + "_a.png")
    # chapter card — big number over the map silhouette
    im = Image.new("RGB", (W, H), (8, 12, 16))
    m = Image.open(os.path.join(ROOT, "output", "design_options", "maps", "M2_dark_command_1772.png")).convert("L")
    m = ImageOps.colorize(ImageEnhance.Contrast(m).enhance(0.7), (6, 10, 16), (60, 78, 96)).filter(ImageFilter.GaussianBlur(3))
    im.paste(m); im = vignette(im, 0.9); bar = letterbox(im); d = ImageDraw.Draw(im)
    text(d, (W / 2, 470), "03", font("Bebas.ttf", 260), (200, 60, 60), "mm")
    text(d, (W / 2, 650), "THE FIRST PARTITION", font("Bebas.ttf", 110), (235, 240, 245), "mm", spacing=8)
    text(d, (W / 2, 740), "1772", font("Oswald.ttf", 36), steel, "mm", spacing=14)
    grain(im, 7, 2).save(out + "_b.png")


def d3_ink_parchment(out):
    ink = (52, 36, 22)
    im = paper(W, H)
    doc = tone(load("plumbcake_1774"), (40, 28, 16), (238, 226, 196))
    doc = contain(doc, 640, 860)
    x, y = 300, (H - doc.height) // 2 - 10
    rot = doc.rotate(-2.2, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0))
    mask = Image.new("L", doc.size, 255).rotate(-2.2, expand=True)
    shadow(im, (x, y, x + rot.width, y + rot.height), 22, (12, 16), 130)
    im.paste(rot, (x, y), mask); d = ImageDraw.Draw(im)
    text(d, (1060, 380), "The Polish Plumb-Cake", font("EBGaramond-Italic.ttf", 64), ink)
    text(d, (1062, 460), "British satirical print, 1774", font("EBGaramond.ttf", 34), (100, 74, 48))
    d.line((1062, 520, 1500, 520), fill=(140, 40, 30), width=2)
    for i, l in enumerate(["A contemporary British satire", "on the First Partition —", "Europe's courts and the Polish \"cake\"."]):
        text(d, (1062, 560 + i * 46), l, font("EBGaramond.ttf", 32), ink)
    vignette(im, 0.5).save(out + "_a.png")
    # chapter card: handwritten-feel heading on parchment with ink rule & seal
    im = paper(W, H, seed=4); d = ImageDraw.Draw(im)
    text(d, (W / 2, 360), "— Chapter the Fourth —", font("EBGaramond-Italic.ttf", 40), (120, 86, 56), "mm")
    text(d, (W / 2, 500), "The Crushing of the", font("EBGaramond-Italic.ttf", 92), ink, "mm")
    text(d, (W / 2, 620), "3 May Constitution", font("EBGaramond.ttf", 110, "SemiBold"), ink, "mm")
    d.line((W / 2 - 300, 720, W / 2 + 300, 720), fill=(140, 40, 30), width=3)
    cx, cy = W / 2, 820
    d.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=(150, 34, 28)); d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), outline=(110, 20, 16), width=3)
    text(d, (cx, cy), "1791", font("EBGaramond.ttf", 26, "Bold"), (235, 200, 180), "mm")
    vignette(im, 0.5).save(out + "_b.png")


def d4_crimson_shadow(out):
    red = (196, 30, 46)
    im = Image.new("RGB", (W, H), (6, 6, 7))
    p = tone(load("kosciuszko_1870"), (4, 4, 5), (235, 235, 235), 1.35)
    p = contain(p, 900, 1180); p = p.crop((0, 40, p.width, 40 + H))
    x = W - p.width - 120; im.paste(p, (x, 0))
    g = hgrad(p.width, H, (6, 6, 7), 1, 0, 0, 0.35); im.paste(g, (x, 0), g)
    g = hgrad(p.width, H, (6, 6, 7), 0, 1, 0.65, 1); im.paste(g, (x, 0), g)
    im = vignette(im, 0.6); d = ImageDraw.Draw(im)
    d.rectangle((120, 470, 126, 650), fill=red)
    text(d, (160, 470), "Tadeusz", font("Playfair.ttf", 62), (230, 230, 230))
    text(d, (160, 540), "Kościuszko", font("Playfair.ttf", 100, "Bold"), (255, 255, 255))
    text(d, (164, 668), "1746 – 1817", font("Inter.ttf", 28), (170, 170, 170), spacing=3)
    text(d, (164, 1030), "Engraved portrait, c. 1870 · Library of Congress", font("Inter.ttf", 18), (100, 100, 100))
    grain(im, 6).save(out + "_a.png")
    im = Image.new("RGB", (W, H), (6, 6, 7)); d = ImageDraw.Draw(im)
    d.rectangle((0, 520, W, 524), fill=red)
    text(d, (160, 500), "V", font("Playfair.ttf", 200, "Bold"), red, "ls")
    text(d, (330, 500), "The Kościuszko Uprising", font("Playfair.ttf", 96), (245, 245, 245), "ls")
    text(d, (334, 590), "MARCH – NOVEMBER 1794", font("Inter.ttf", 30), (160, 160, 160), spacing=6)
    grain(vignette(im, 0.5), 6, 3).save(out + "_b.png")


def gilt_frame(canvas, art, x, y, pad=46):
    w, h = art.size
    fr = Image.new("RGB", (w + 2 * pad, h + 2 * pad))
    a = np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    dist = np.minimum.reduce([xx, yy, a.shape[1] - 1 - xx, a.shape[0] - 1 - yy]).astype(np.float32)
    band = 0.55 + 0.45 * np.cos(dist / pad * np.pi * 2.2) * np.exp(-dist / pad)
    rng = np.random.default_rng(3); band += gaussian_filter(rng.standard_normal(band.shape), 1.2) * 0.08
    for i, c in enumerate((196, 156, 82)):
        a[..., i] = c * band
    fr = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    shadow(canvas, (x, y, x + fr.width, y + fr.height), 40, (20, 30), 190)
    canvas.paste(fr, (x, y)); canvas.paste(art, (x + pad, y + pad))
    d = ImageDraw.Draw(canvas); d.rectangle((x + pad - 3, y + pad - 3, x + pad + w + 2, y + pad + h + 2), outline=(70, 50, 20), width=3)


def wall(base=(44, 22, 26), seed=5):
    rng = np.random.default_rng(seed)
    n = gaussian_filter(rng.standard_normal((H, W)), 2) * 0.5 + gaussian_filter(rng.standard_normal((H, W)), 30) * 6
    a = np.asarray(base)[None, None].astype(np.float32) * (1 + 0.06 * n[..., None])
    y, x = np.mgrid[0:H, 0:W]
    light = np.exp(-(((x - W * 0.42) / (W * 0.35)) ** 2 + ((y - H * 0.35) / (H * 0.55)) ** 2))
    a = a * (0.45 + 1.1 * light[..., None])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def d5_museum(out):
    im = wall()
    art = load("kosciuszko_general_182x"); art = contain(art, 560, 720)
    gilt_frame(im, art, 520, 120)
    d = ImageDraw.Draw(im)
    px, py = 1330, 640
    shadow(im, (px, py, px + 420, py + 200), 12, (6, 8), 120)
    d = ImageDraw.Draw(im); d.rectangle((px, py, px + 420, py + 200), fill=(236, 232, 222))
    text(d, (px + 28, py + 30), "Thaddeus Kosciuszko,", font("EBGaramond.ttf", 28, "SemiBold"), (30, 30, 30))
    text(d, (px + 28, py + 66), "General en Chef des", font("EBGaramond-Italic.ttf", 26), (30, 30, 30))
    text(d, (px + 28, py + 98), "Armées Polonaises", font("EBGaramond-Italic.ttf", 26), (30, 30, 30))
    text(d, (px + 28, py + 146), "Engraving, 1820s · Library of Congress", font("Inter.ttf", 15), (90, 90, 90))
    vignette(im, 0.55).save(out + "_a.png")
    im = wall((30, 36, 32), 8); d = ImageDraw.Draw(im)
    bx, by = W // 2 - 420, 360
    shadow(im, (bx, by, bx + 840, by + 360), 18, (8, 10), 140)
    d = ImageDraw.Draw(im); d.rectangle((bx, by, bx + 840, by + 360), fill=(236, 232, 222))
    text(d, (W / 2, by + 70), "GALLERY VI", font("Inter.ttf", 26, "SemiBold"), (120, 100, 60), "mm", spacing=8)
    text(d, (W / 2, by + 170), "Final Thoughts", font("EBGaramond.ttf", 96), (28, 28, 28), "mm")
    d.line((W / 2 - 120, by + 250, W / 2 + 120, by + 250), fill=(160, 130, 70), width=2)
    text(d, (W / 2, by + 295), "1795 and after", font("EBGaramond-Italic.ttf", 34), (80, 80, 80), "mm")
    vignette(im, 0.6).save(out + "_b.png")


def d6_explainer(out):
    bg, ink, acc = (244, 242, 238), (28, 32, 38), (200, 52, 52)
    im = Image.new("RGB", (W, H), bg)
    art = load("europe_july_1772"); art = contain(art, 1000, 780)
    x, y = 110, (H - art.height) // 2
    shadow(im, (x, y, x + art.width, y + art.height), 30, (0, 16), 70)
    m = Image.new("L", art.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, art.width - 1, art.height - 1), 22, fill=255)
    im.paste(art, (x, y), m); d = ImageDraw.Draw(im)
    tx = x + art.width + 90
    text(d, (tx, 300), "SOURCE", font("Inter.ttf", 22, "SemiBold"), acc, spacing=4)
    text(d, (tx, 340), "“Picture of Europe", font("Inter.ttf", 50, "Bold"), ink)
    text(d, (tx, 400), "for July 1772”", font("Inter.ttf", 50, "Bold"), ink)
    for i, (k, v) in enumerate([("Type", "British satirical print"), ("Date", "1772"), ("Context", "Published as the First Partition"), ("", "was being agreed")]):
        if k: text(d, (tx, 500 + i * 52), k, font("Inter.ttf", 24), (120, 126, 134))
        text(d, (tx + 140, 500 + i * 52), v, font("Inter.ttf", 26, "Medium"), ink)
    text(d, (tx, 980), "Library of Congress", font("Inter.ttf", 18), (150, 155, 160))
    d.rectangle((0, H - 10, W, H), fill=acc)
    im.save(out + "_a.png")
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
    chapters = ["Introduction", "The Sovereignty Crisis of Poland-Lithuania", "The First Partition",
                "The Crushing of the 3 May Constitution", "The Kościuszko Uprising", "Final Thoughts"]
    text(d, (140, 330), "04", font("Inter.ttf", 220, "Bold"), acc, "ls")
    text(d, (140, 450), "The Crushing of the", font("Inter.ttf", 72, "Bold"), ink, "ls")
    text(d, (140, 540), "3 May Constitution", font("Inter.ttf", 72, "Bold"), ink, "ls")
    for i, c in enumerate(chapters):
        yy = 700 + i * 50; on = i == 3
        d.rectangle((140, yy - 14, 146, yy + 14), fill=acc if on else (205, 208, 212))
        text(d, (170, yy), f"{i+1:02d}  {c}", font("Inter.ttf", 26, "SemiBold" if on else "Regular"), ink if on else (150, 155, 160), "lm")
    im.save(out + "_b.png")


DESIGNS = {
    "D1_royal_archive": d1_royal_archive,
    "D2_cold_empire": d2_cold_empire,
    "D3_ink_and_parchment": d3_ink_parchment,
    "D4_crimson_and_shadow": d4_crimson_shadow,
    "D5_museum_gallery": d5_museum,
    "D6_modern_explainer": d6_explainer,
}

if __name__ == "__main__":
    outdir = os.path.join(ROOT, "output", "design_options", "overall")
    os.makedirs(outdir, exist_ok=True)
    for k in (sys.argv[1:] or DESIGNS):
        DESIGNS[k](os.path.join(outdir, k)); print("wrote", k)
