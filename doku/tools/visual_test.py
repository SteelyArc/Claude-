"""Visual test: ~30 s motion sample in the chosen style (designs 11-20).

No narration, no archival audio, no archival footage: grey areas are labelled PLACEHOLDER.
Sound is synthesised atmosphere only (drone, whooshes, impacts, projector clatter).

Usage: python3 visual_test.py <world_1930.geojson> <ne_50m_countries.geojson> <out.mp4>
"""
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import (CITIES, DIM, H, INK, MONO, MONO_L, PAPER, PARTY, RED, SANS, SANS_B, SERIF, SERIF_B,
                           SERIF_I, W, MapProj, font, load_maps, placeholder_photo, text_c, wrap)
from design_frames_2 import (GOLD, crack_paths, germany_rings, iso_prism, light_rays, perspective_coeffs, tilt)

FPS = 30
OVERLAP = 0.5
RNG = np.random.default_rng(42)


def clamp(x):
    return min(max(x, 0.0), 1.0)


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- compositing helpers
def layer(draw_fn, glow=0, glow_passes=1):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    if glow:
        g = lay.filter(ImageFilter.GaussianBlur(glow))
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for _ in range(glow_passes):
            base = Image.alpha_composite(base, g)
        lay = Image.alpha_composite(base, lay)
    a = np.asarray(lay, np.float32) / 255
    return a[..., :3] * a[..., 3:] * 255, a[..., 3:]


def comp(frame, L, k=1.0, dy=0, dx=0):
    if k <= 0.001:
        return frame
    rgb, a = L
    dy, dx = int(dy), int(dx)
    if dy or dx:
        rgb = np.roll(rgb, (dy, dx), (0, 1))
        a = np.roll(a, (dy, dx), (0, 1)).copy()
        if dy > 0:
            a[:dy] = 0
        elif dy < 0:
            a[dy:] = 0
        if dx > 0:
            a[:, :dx] = 0
        elif dx < 0:
            a[:, dx:] = 0
        rgb = rgb * (a > 0)
    return frame * (1 - a * k) + rgb * k


GRAIN = [RNG.normal(0, 11, (H, W, 1)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
VIG = np.clip(1 - 0.5 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2) ** 1.1, 0, 1)[..., None].astype(np.float32)
del yy, xx


def finish(frame, idx, zoom=1.0, center=(W / 2, H / 2), shake=(0, 0)):
    f = np.clip(frame * VIG + GRAIN[idx % len(GRAIN)], 0, 255).astype(np.uint8)
    img = Image.fromarray(f)
    if zoom != 1.0 or shake != (0, 0):
        cx, cy = center
        w, h = W / zoom, H / zoom
        x0 = cx - w * (cx / W) + shake[0]
        y0 = cy - h * (cy / H) + shake[1]
        img = img.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
    return img


# ---------------------------------------------------------------- scene 1: tilted map
class MapScene:
    dur = 7.0

    def __init__(self, geo):
        base = Image.new("RGB", (W, H), (8, 10, 14))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        proj = MapProj(5.0, 23.4, 46.4, 56.0, (20, 700, 1060, 1700))
        d = ImageDraw.Draw(lay)
        for n, rs in geo.items():
            if n in ("Germany", "East Prussia"):
                continue
            for r in rs:
                d.polygon([proj(*p) for p in r], fill=(22, 26, 32, 255), outline=(44, 50, 58, 255))
        for lon in range(5, 24, 2):
            d.line([proj(lon, 46.4), proj(lon, 56.0)], fill=(60, 70, 80, 90), width=1)
        for lat in range(47, 57):
            d.line([proj(5.0, lat), proj(23.4, lat)], fill=(60, 70, 80, 90), width=1)
        for k in range(26, 0, -1):
            c = int(30 + 40 * (1 - k / 26))
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
        t = tilt(lay, top_inset=260, top_y=0.3)
        base.paste(t, (0, 0), t)
        a, b, c_, dd, e, f, g, h = perspective_coeffs([(0, 0), (W, 0), (W, H), (0, H)],
                                                       [(260, H * 0.3), (W - 260, H * 0.3), (W, H), (0, H)])
        den = g * bx + h * by + 1
        self.px, self.py = (a * bx + b * by + c_) / den, (dd * bx + e * by + f) / den
        self.base = np.asarray(base, np.float32)
        self.rays = light_rays((W, H), (self.px, self.py), (255, 190, 110), 0.3, seed=3)
        px, py = self.px, self.py

        def beam(d):
            d.polygon([(px - 6, py), (px + 6, py), (px + 60, 0), (px - 60, 0)], fill=(255, 210, 140, 80))
        bl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        beam(ImageDraw.Draw(bl))
        bl = bl.filter(ImageFilter.GaussianBlur(22))
        ba = np.asarray(bl, np.float32) / 255
        self.beam = (ba[..., :3] * ba[..., 3:] * 255, ba[..., 3:])
        self.l_date = layer(lambda d: d.text((60, 150), "30 JANUARY 1933", font=font(MONO, 34), fill=GOLD))
        self.l_title = layer(lambda d: d.text((60, 200), "Power Handed Over", font=font(SERIF_B, 84), fill=PAPER), glow=14)
        self.l_sub = layer(lambda d: d.text((60, 310), "Hindenburg appoints Hitler Reich Chancellor.",
                                            font=font(SERIF_I, 38), fill=DIM))
        self.l_berlin = layer(lambda d: d.text((px + 30, py - 70), "Berlin", font=font(SANS_B, 40), fill=PAPER), glow=10)
        self.dust = RNG.uniform([0, 0], [W, H], (160, 2))

    def frame(self, t, idx):
        T = t * self.dur
        f = self.base + self.rays * ease((T - 0.6) / 2.0)
        f = comp(f, self.beam, ease((T - 0.3) / 1.5))
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(3):
            ph = (T * 0.6 + i / 3) % 1
            r = 20 + 130 * ph
            d.ellipse([self.px - r, self.py - r * 0.4, self.px + r, self.py + r * 0.4], outline=(255, 200, 120, int(200 * (1 - ph))), width=3)
        d.ellipse([self.px - 10, self.py - 10, self.px + 10, self.py + 10], fill=(255, 235, 200))
        for k, (x, y) in enumerate(self.dust):
            yy_ = (y - T * 18 * (1 + k % 3)) % H
            d.ellipse([x - 2, yy_ - 2, x + 2, yy_ + 2], fill=(255, 240, 210, 70))
        f = np.asarray(img, np.float32)
        f = comp(f, self.l_berlin, ease((T - 1.2) / 0.6))
        k = ease((T - 0.8) / 0.6)
        f = comp(f, self.l_date, k, dy=20 * (1 - k))
        k = ease((T - 1.2) / 0.8)
        f = comp(f, self.l_title, k, dy=30 * (1 - k))
        f = comp(f, self.l_sub, ease((T - 2.0) / 0.8))
        return finish(f, idx, zoom=1.0 + 0.07 * ease(t), center=(self.px, self.py))


# ---------------------------------------------------------------- scene 2: archive placeholder w/ parallax
class ArchiveScene:
    dur = 6.0

    def __init__(self):
        self.bg = placeholder_photo((1400, 2400), seed=31, label="PLACEHOLDER · ARCHIVE FILM")
        self.fg = self.bg.crop((0, 1500, 1400, 2400)).filter(ImageFilter.GaussianBlur(9))
        self.fg = Image.eval(self.fg, lambda v: int(v * 0.55))
        self.l_date = layer(lambda d: d.text((60, 140), "27 FEBRUARY 1933 · BERLIN", font=font(MONO, 32), fill=PAPER))

        def lt(d):
            d.rectangle([0, H - 420, W, H], fill=(8, 8, 8, 225))
            d.line([(60, 1180), (60, 1440)], fill=RED, width=8)
            d.text((95, 1180), "The Reichstag", font=font(SERIF_B, 80), fill=PAPER)
            d.text((95, 1280), "is burning", font=font(SERIF_B, 80), fill=PAPER)
            d.text((95, 1390), "The Nazi leadership immediately uses the fire", font=font(SANS, 28), fill=DIM)
            d.text((95, 1426), "to persecute political opponents.", font=font(SANS, 28), fill=DIM)
            d.text((60, 1490), "Photo: [archive, reference no.] · licence", font=font(MONO_L, 22), fill=(170, 160, 140))
        self.l_lt = layer(lt)
        grad = np.zeros((H, W, 1), np.float32)
        for i in range(520):
            grad[H - 420 - i] = 0.9 * (1 - i / 520)
        grad[H - 420:] = 0.9
        self.shade = (np.zeros((H, W, 3), np.float32), grad)

    def frame(self, t, idx):
        s = 1.0 + 0.08 * t
        cw, ch = W / s * 1.15, H / s * 1.15
        x0 = 60 + 120 * t + RNG.uniform(-2, 2)
        y0 = 120 - 60 * t + RNG.uniform(-2, 2)
        img = self.bg.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)
        fx = 260 * t
        fg = self.fg.crop((fx, 0, fx + W, 900))
        img.paste(fg, (0, 1020))
        f = np.asarray(img, np.float32) * (0.82 + 0.06 * math.sin(idx * 2.3) + RNG.normal(0, 0.015))
        f += np.array([10, 14, 20], np.float32)
        f = comp(f, self.shade, ease(t / 0.3))
        f = comp(f, self.l_date, ease((t - 0.08) / 0.12))
        k = ease_out((t - 0.2) / 0.25)
        f = comp(f, self.l_lt, k, dx=-500 * (1 - k))
        if idx % 37 == 0:
            f[:, int(RNG.uniform(100, W - 100))] += 40
        return finish(f, idx)


# ---------------------------------------------------------------- scene 3: 3D bars rising
class BarsScene:
    dur = 7.0
    data = [("1928", 2.6), ("1930", 18.3), ("Jul 32", 37.3), ("Nov 32", 33.1)]

    def __init__(self):
        img = Image.new("RGB", (W, H), (14, 14, 16))
        f = np.asarray(img, np.float32) + light_rays((W, H), (W / 2, 260), (120, 110, 100), 0.35, seed=9)
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(14):
            y = 1330 + i * i * 2.2
            d.line([(0, y), (W, y)], fill=(70, 66, 60, 120 - i * 7), width=1)
        for i in range(-10, 11):
            d.line([(W / 2 + i * 40, 1330), (W / 2 + i * 220, 1720)], fill=(70, 66, 60, 60), width=1)
        self.base = img
        self.l_kicker = layer(lambda d: d.text((60, 150), "NSDAP · REICHSTAG ELECTIONS", font=font(MONO, 30), fill=GOLD))
        self.l_t1 = layer(lambda d: d.text((60, 195), "Largest party.", font=font(SERIF_B, 80), fill=PAPER), glow=12)
        self.l_t2 = layer(lambda d: d.text((60, 290), "Never a majority.", font=font(SERIF_B, 80), fill=(230, 110, 95)), glow=12)

    def frame(self, t, idx):
        T = t * self.dur
        img = self.base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        x0, bw, gap, scale, base = 110, 150, 72, 15, 1330
        my = base - 50 * scale
        kp = ease((T - 0.4) / 0.8)
        d.polygon([(60, my), (1000, my), (1040, my - 24), (100, my - 24)], fill=(163, 39, 31, int(60 * kp)),
                  outline=(200, 60, 50, int(200 * kp)))
        d.text((70, my - 70), "50 % · absolute majority", font=font(MONO, 26), fill=(230, 110, 95, int(255 * kp)))
        for i, (lab, v) in enumerate(self.data):
            p = ease_out((T - 1.0 - i * 0.55) / 1.1)
            x = x0 + i * (bw + gap)
            h = max(v * scale * p, 2)
            hi = 1 if i == 2 else 0.8
            c = PARTY["NSDAP"]
            iso_prism(d, x, base, bw, h, tuple(int(q * hi * 1.5) for q in c), tuple(int(q * hi) for q in c),
                      tuple(int(q * hi * 0.6) for q in c))
            val = v * p
            s = f"{val:.1f} %"
            fo = font(SERIF_B, 50 if i == 2 else 40)
            d.text((x + bw / 2 - d.textlength(s, font=fo) / 2 + 20, base - h - 100), s, font=fo, fill=PAPER + (int(255 * clamp(p * 3)),))
            d.text((x + bw / 2 - d.textlength(lab, font=font(MONO, 26)) / 2, base + 30), lab, font=font(MONO, 26), fill=DIM)
        f = np.asarray(img, np.float32)
        f = comp(f, self.l_kicker, ease(T / 0.5))
        k = ease((T - 0.2) / 0.6)
        f = comp(f, self.l_t1, k, dy=25 * (1 - k))
        k = ease((T - 4.0) / 0.6)
        f = comp(f, self.l_t2, k, dy=25 * (1 - k))
        return finish(f, idx, zoom=1.0 + 0.04 * t, center=(W / 2, 900))


# ---------------------------------------------------------------- scene 4: constitution cracks
class CrackScene:
    dur = 6.0
    hit = 0.42

    def __init__(self):
        img = Image.new("RGB", (W, H), (226, 218, 198))
        d = ImageDraw.Draw(img)
        text_c(d, 360, "THE CONSTITUTION OF THE GERMAN REICH", font(MONO, 30), (90, 84, 76))
        text_c(d, 410, "11 August 1919", font(SERIF_I, 40), (90, 84, 76))
        text_c(d, 560, "Article 1", font(SERIF_B, 66), INK)
        y = 680
        for ln in ["The German Reich", "is a republic.", "State authority", "derives from the people."]:
            text_c(d, y, ln, font(SERIF, 54), INK)
            y += 74
        self.paper = img
        self.origin = (560, 820)
        self.paths = crack_paths(self.origin)
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon([(0, 0), (W, 0), (W, 760), self.origin, (0, 980)], fill=255)
        self.mask = mask

        def panel(d):
            d.rectangle([0, 1180, W, H], fill=(14, 13, 12, 245))
            d.text((60, 1240), "28 FEBRUARY – 23 MARCH 1933", font=font(MONO, 30), fill=GOLD)
            yy_ = 1290
            for ln in ["In 23 days,", "the constitution", "is hollowed out."]:
                d.text((60, yy_), ln, font=font(SERIF_B, 58), fill=PAPER)
                yy_ += 70
        self.l_panel = layer(panel)

    def frame(self, t, idx):
        p = ease_out((t - 0.15) / (self.hit - 0.15))
        img = self.paper
        if t >= self.hit:
            img = Image.composite(Image.fromarray(np.roll(np.asarray(img), (-9, -5), (0, 1))), img, self.mask)
        img = img.copy()
        d = ImageDraw.Draw(img, "RGBA")
        for path in self.paths:
            n = max(2, int(len(path) * p))
            if p > 0:
                d.line(path[:n], fill=(20, 16, 12, 230), width=4, joint="curve")
        f = np.asarray(img, np.float32)
        if self.hit <= t < self.hit + 0.05:
            f = f + 60 * (1 - (t - self.hit) / 0.05)
        k = ease_out((t - 0.55) / 0.2)
        f = comp(f, self.l_panel, k, dy=600 * (1 - k))
        sh = (0, 0)
        if t >= self.hit:
            amp = 14 * math.exp(-(t - self.hit) * 30)
            sh = (RNG.uniform(-amp, amp), RNG.uniform(-amp, amp))
        return finish(f, idx, zoom=1.03 + 0.04 * t, center=self.origin, shake=sh)


# ---------------------------------------------------------------- scene 5: 549 finale
class FinalScene:
    dur = 6.5

    def __init__(self):
        base = Image.new("RGB", (W, H), (4, 4, 5))
        self.base = np.asarray(base, np.float32) + light_rays((W, H), (W / 2, -80), (200, 190, 170), 0.9, seed=20)
        self.l_date = layer(lambda d: text_c(d, 420, "2 AUGUST 1934", font(MONO, 34), GOLD))
        self.l_head = layer(lambda d: text_c(d, 480, "Hindenburg dies.", font(SERIF_B, 82), PAPER), glow=14)

        def sub(d):
            yy_ = 620
            for ln in ["Hitler merges the offices of", "President and Chancellor."]:
                text_c(d, yy_, ln, font(SERIF_I, 40), DIM)
                yy_ += 52
        self.l_sub = layer(sub)
        self.l_cap = layer(lambda d: text_c(d, 1190, "DAYS FROM CHANCELLOR TO DICTATOR", font(MONO, 32), PAPER))

        def body(d):
            d.line([(340, 1290), (740, 1290)], fill=RED, width=4)
            yy_ = 1330
            for ln in wrap(d, "Democracy was not abolished in a single day – but step by step, through laws, "
                              "violence and the help of those who thought they could control him.", font(SERIF_I, 34), 900):
                text_c(d, yy_, ln, font(SERIF_I, 34), PAPER)
                yy_ += 46
        self.l_body = layer(body)
        self.dust = RNG.uniform([200, 0], [880, 900], (220, 2))
        self.dsz = RNG.choice([1, 1, 2, 2, 3], 220)

    def frame(self, t, idx):
        T = t * self.dur
        f = self.base.copy()
        f = comp(f, self.l_date, ease((T - 0.2) / 0.5))
        k = ease((T - 0.5) / 0.7)
        f = comp(f, self.l_head, k, dy=20 * (1 - k))
        f = comp(f, self.l_sub, ease((T - 1.2) / 0.7))
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        n = int(round(549 * ease_out((T - 1.6) / 2.0)))
        if T > 1.6:
            num = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
            nd = ImageDraw.Draw(num)
            s = str(n)
            fo = font(SERIF_B, 300)
            nd.text(((W - nd.textlength(s, font=fo)) / 2, 40), s, font=fo, fill=(240, 225, 200, 255))
            g = num.filter(ImageFilter.GaussianBlur(24))
            img.paste(g, (0, 820), g)
            img.paste(g, (0, 820), g)
            img.paste(num, (0, 820), num)
        d = ImageDraw.Draw(img, "RGBA")
        for (x, y), r in zip(self.dust, self.dsz):
            yy_ = (y + T * 25 * r) % 900
            xx_ = x + 8 * math.sin(T + y)
            d.ellipse([xx_ - r, yy_ - r, xx_ + r, yy_ + r], fill=(255, 240, 210, 110))
        f = np.asarray(img, np.float32)
        f = comp(f, self.l_cap, ease((T - 3.4) / 0.6))
        f = comp(f, self.l_body, ease((T - 4.0) / 0.8))
        fade = 1 - ease((T - (self.dur - 0.6)) / 0.6)
        return finish(f * fade, idx, zoom=1.0 + 0.03 * t, center=(W / 2, 950))


# ---------------------------------------------------------------- timeline + transitions
def burn(a, b, x):
    """Film-burn transition: crossfade with a warm flash peaking in the middle."""
    fa = np.asarray(a, np.float32)
    fb = np.asarray(b, np.float32)
    m = ease(x)
    out = fa * (1 - m) + fb * m
    flash = math.sin(math.pi * x)
    out += BURN * flash
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def make_burn():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W * 0.85) / W) ** 2 + ((yy - H * 0.15) / H) ** 2)
    g = np.clip(1 - d * 1.4, 0, 1) ** 2
    return (g[..., None] * np.array([255, 150, 60], np.float32)).astype(np.float32)


BURN = make_burn()


def audio(total, cuts, events, path, sr=48000):
    n = int(total * sr)
    t = np.arange(n) / sr
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    drone = (0.05 * np.sin(2 * np.pi * 55 * t) + 0.03 * np.sin(2 * np.pi * 82.4 * t + 1)
             + 0.015 * np.sin(2 * np.pi * 110.3 * t)) * lfo
    out = drone.copy()
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 1, n)
    # low-passed noise for whooshes
    k = np.ones(40) / 40
    soft = np.convolve(noise, k, "same")
    for c in cuts:
        s, e = int((c - 0.6) * sr), int((c + 0.6) * sr)
        s, e = max(s, 0), min(e, n)
        env = np.sin(np.linspace(0, np.pi, e - s)) ** 2
        out[s:e] += 0.5 * soft[s:e] * env
    for at, kind in events:
        s = int(at * sr)
        L = min(int(1.8 * sr), n - s)
        tt = np.arange(L) / sr
        if kind == "impact":
            out[s:s + L] += 0.45 * np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 3.5)
            out[s:s + L] += 0.25 * noise[s:s + L] * np.exp(-tt * 22)
        elif kind == "projector":
            seg = int(6.0 * sr)
            seg = min(seg, n - s)
            tt = np.arange(seg) / sr
            clicks = (np.sin(2 * np.pi * 24 * tt) > 0.97).astype(float)
            out[s:s + seg] += 0.08 * clicks * noise[s:s + seg] + 0.01 * noise[s:s + seg]
    fade = np.minimum(1, np.minimum(t / 1.0, (total - t) / 1.5))
    out = np.tanh(out * fade * 1.2) * 0.8
    st = np.stack([out, out * 0.97], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main():
    hist, modern, out = sys.argv[1:4]
    geo, _ = load_maps(hist, modern)
    scenes = [MapScene(geo), ArchiveScene(), BarsScene(), CrackScene(), FinalScene()]
    starts, s = [], 0.0
    for sc in scenes:
        starts.append(s)
        s += sc.dur - OVERLAP
    total = s + OVERLAP
    nframes = int(total * FPS)
    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "a.wav")
    cuts = starts[1:]
    events = [(starts[1], "projector"), (starts[3] + CrackScene.hit * CrackScene.dur, "impact"),
              (starts[4] + 3.6, "impact")]
    audio(total, cuts, events, wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "27", "-tune", "grain", "-maxrate", "9M", "-bufsize", "18M",
                           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                           "-shortest", out], stdin=subprocess.PIPE)
    for i in range(nframes):
        T = i / FPS
        active = [(k, (T - starts[k]) / scenes[k].dur) for k in range(len(scenes))
                  if starts[k] <= T < starts[k] + scenes[k].dur]
        if len(active) == 1:
            k, lt = active[0]
            img = scenes[k].frame(lt, i)
        else:
            (ka, la), (kb, lb) = active[:2]
            x = (T - starts[kb]) / OVERLAP
            img = burn(scenes[ka].frame(la, i), scenes[kb].frame(lb, i), x)
        ff.stdin.write(img.convert("RGB").tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done", total)


if __name__ == "__main__":
    main()
