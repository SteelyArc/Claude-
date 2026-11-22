"""Opening sequence: Krupp speech (British Pathé audio) over 1933 map + archive film/photos, then title card.

TikTok-safe layout: key content kept inside x 64-936, y 200-1460 (top bar, right-hand buttons and
bottom caption area left clear).

Usage: python3 opening.py <world_1930.geojson> <ne_50m.geojson> <out.mp4> [--preview-frames]
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from design_frames import (CITIES, DIM, H, INK, MONO, MONO_L, PAPER, RED, SANS, SANS_B, SERIF, SERIF_B, SERIF_I, W,
                           MapProj, font, load_maps, text_c, wrap)
from design_frames_2 import GOLD, germany_rings, light_rays, perspective_coeffs, tilt
from visual_test import GRAIN, VIG, clamp, comp, ease, ease_out, layer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FPS = 30
AUDIO_START = 1.0
SPEECH = os.path.join(ROOT, "audio", "krupp_speech_british_pathe.mp3")
FILM_P = os.path.join(ROOT, "archive", "film", "Why_We_Fight.1.Prelude_to_War.webm.480p.vp9.webm")
FILM_N = os.path.join(ROOT, "archive", "film", "Why_We_Fight.2.The_Nazis_Strike.webm.480p.vp9.webm")
PHOTOS = os.path.join(ROOT, "archive", "photos")
SAFE_X0, SAFE_X1 = 64, 936
RNG = np.random.default_rng(7)

CREDIT_P = "Film: 'Prelude to War' (US War Dept., 1942) · public domain"
CREDIT_N = "Film: 'The Nazis Strike' (US War Dept., 1943) · public domain"


def credit_bundesarchiv(file_slug):
    c = {x["file"]: x for x in json.load(open(os.path.join(PHOTOS, "credits.json")))}[file_slug]
    sig = c["title"].replace("File:Bundesarchiv ", "").split(",")[0]
    artist = c["artist"].replace("Unknown authorUnknown author", "unknown").replace("UnknownUnknown", "unknown")
    return f"Photo: Bundesarchiv, {sig} / {artist} / CC BY-SA 3.0 DE"


# ------------------------------------------------------------------ subtitles (speech words + 1.0 s offset)
SUBS = [
    (1.00, 5.95, "Ob du meine Arbeit für richtig hältst,", "Whether you consider my work right,"),
    (6.22, 10.10, "ob du glaubst, dass ich fleißig gewesen bin, dass ich gearbeitet habe,",
     "whether you believe that I have been diligent, that I have worked,"),
    (10.36, 12.95, "dass ich mich in diesen Jahren für dich eingesetzt habe,",
     "that in these years I have committed myself to you,"),
    (13.52, 18.45, "dass ich anständig meine Zeit verwendet habe im Dienste meines Volkes –",
     "that I have used my time decently in the service of my people –"),
    (18.90, 20.50, "gib du jetzt deine Stimme ab.", "now cast your vote."),
    (20.70, 25.40, "Wenn ja, dann tritt für mich ein, so wie ich für dich eingetreten bin!",
     "If yes, then stand up for me, as I have stood up for you!"),
]


def sub_layers():
    out = []
    fde, fen = font(SERIF_I, 30), font(SANS_B, 44)
    cx = (SAFE_X0 + SAFE_X1) / 2
    for s, e, de, en in SUBS:
        def draw(d, de=de, en=en):
            de_l = wrap(d, de, fde, SAFE_X1 - SAFE_X0 - 20)
            en_l = wrap(d, en, fen, SAFE_X1 - SAFE_X0 - 20)
            y = 1250
            for ln in de_l:
                d.text((cx - d.textlength(ln, font=fde) / 2, y), ln, font=fde, fill=GOLD + (235,))
                y += 38
            y += 10
            for ln in en_l:
                tw = d.textlength(ln, font=fen)
                d.rounded_rectangle([cx - tw / 2 - 14, y - 4, cx + tw / 2 + 14, y + 54], 8, fill=(0, 0, 0, 150))
                d.text((cx - tw / 2, y), ln, font=fen, fill=(255, 255, 255, 255))
                y += 60
        out.append((s, e, layer(draw)))
    return out


# ------------------------------------------------------------------ media helpers
def read_clip(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-t", str(dur + 0.2), "-i", path,
                          "-vf", f"fps={FPS},scale=640:480", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (640 * 480 * 3)
    return [Image.fromarray(np.frombuffer(raw, np.uint8, 640 * 480 * 3, i * 640 * 480 * 3).reshape(480, 640, 3))
            for i in range(n)]


BOX_TOP, BOX_H = 250, 900


def feather_mask(w, h, f=60):
    m = np.ones((h, w), np.float32)
    ramp = np.linspace(0, 1, f)
    m[:f] *= ramp[:, None]
    m[-f:] *= ramp[::-1][:, None]
    return Image.fromarray((m * 255).astype(np.uint8))


def media_frame(src, t, push=0.08, pan=(0.0, 0.0), film=False, idx=0):
    """Place a photo/film frame into the TikTok layout with blurred fill, Ken Burns push and archive texture."""
    src = src.convert("RGB")
    # blurred background fill
    small = src.resize((54, 96), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
    bg = small.resize((W, H), Image.BICUBIC)
    bg = Image.eval(bg, lambda v: int(v * 0.35))
    sw, sh = src.size
    portrait = sh > sw
    scale = (BOX_H / sh) if portrait else (W / sw) * 1.0
    scale *= 1.0 + push * ease(t)
    nw, nh = int(sw * scale), int(sh * scale)
    img = src.resize((nw, nh), Image.BICUBIC)
    ox = (W - nw) / 2 + pan[0] * ease(t) * 60
    oy = BOX_TOP + (BOX_H - nh) / 2 + pan[1] * ease(t) * 40
    if film:
        ox += RNG.uniform(-1.5, 1.5)
        oy += RNG.uniform(-1.5, 1.5)
    bg.paste(img, (int(ox), int(oy)), feather_mask(nw, nh, 70))
    f = np.asarray(bg, np.float32)
    if film:
        f *= 0.95 + 0.05 * math.sin(idx * 2.7) + RNG.normal(0, 0.01)
    return f


# ------------------------------------------------------------------ 1933 map shot
class Map1933:
    def __init__(self, geo):
        base = Image.new("RGB", (W, H), (8, 10, 14))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        proj = MapProj(5.0, 23.4, 46.4, 56.0, (20, 640, 1060, 1640))
        d = ImageDraw.Draw(lay)
        for n, rs in geo.items():
            if n in ("Germany", "East Prussia"):
                continue
            for r in rs:
                d.polygon([proj(*p) for p in r], fill=(22, 26, 32, 255), outline=(44, 50, 58, 255))
        for k in range(24, 0, -1):
            c = int(30 + 40 * (1 - k / 24))
            for r in germany_rings(geo):
                d.polygon([(x, y + k) for x, y in (proj(*p) for p in r)], fill=(c, c - 4, c - 10, 255))
        for r in germany_rings(geo):
            pts = [proj(*p) for p in r]
            d.polygon(pts, fill=(92, 84, 70, 255))
            d.line(pts + [pts[0]], fill=GOLD + (255,), width=3)
        for c in ("Berlin", "Hamburg", "Munich", "Königsberg"):
            x, y = proj(*CITIES[c])
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=PAPER + (255,))
            d.text((x + 14, y - 16), c, font=font(SANS, 28), fill=PAPER + (230,))
        ex, ey = proj(*CITIES["Essen"])
        t = tilt(lay, top_inset=240, top_y=0.28)
        base.paste(t, (0, 0), t)
        a, b, c_, dd, e, f, g, h = perspective_coeffs([(0, 0), (W, 0), (W, H), (0, H)],
                                                       [(240, H * 0.28), (W - 240, H * 0.28), (W, H), (0, H)])
        den = g * ex + h * ey + 1
        self.px, self.py = (a * ex + b * ey + c_) / den, (dd * ex + e * ey + f) / den
        self.base = np.asarray(base, np.float32)
        self.rays = light_rays((W, H), (self.px, self.py), (255, 190, 110), 0.22, seed=5)
        px, py = self.px, self.py
        self.l_title = layer(lambda d: d.text((SAFE_X0, 330), "Germany, 1933", font=font(SERIF_B, 78), fill=PAPER), glow=12)
        self.l_lab = layer(lambda d: (d.text((px + 26, py - 64), "Essen", font=font(SANS_B, 40), fill=PAPER),
                                      d.text((px + 26, py - 18), "Krupp works", font=font(MONO, 24), fill=GOLD)), glow=6)
        self.l_note = layer(lambda d: d.text((SAFE_X0, 1470), "Borders 1933 · Saar under League of Nations administration",
                                             font=font(MONO_L, 20), fill=DIM))

    def frame(self, t):
        f = self.base + self.rays * ease(t / 0.5)
        img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(3):
            ph = (t * 1.6 + i / 3) % 1
            r = 16 + 110 * ph
            d.ellipse([self.px - r, self.py - r * 0.42, self.px + r, self.py + r * 0.42],
                      outline=(255, 200, 120, int(220 * (1 - ph))), width=3)
        d.ellipse([self.px - 9, self.py - 9, self.px + 9, self.py + 9], fill=(255, 230, 190))
        f = np.asarray(img, np.float32)
        k = ease(t / 0.25)
        f = comp(f, self.l_title, k, dy=20 * (1 - k))
        f = comp(f, self.l_lab, ease((t - 0.2) / 0.2))
        f = comp(f, self.l_note, ease((t - 0.3) / 0.2))
        return f, 1.0 + 0.10 * ease(t), (self.px, self.py)


# ------------------------------------------------------------------ title card
class Title:
    def __init__(self):
        self.base = np.zeros((H, W, 3), np.float32) + light_rays((W, H), (W / 2, -60), (190, 175, 150), 0.7, seed=12)
        self.l_k = layer(lambda d: text_c(d, 640, "A HISTORICAL DOCUMENTARY", font(MONO, 30), GOLD, w=1000))
        self.l_t1 = layer(lambda d: text_c(d, 700, "How Hitler", font(SERIF_B, 120), PAPER, w=1000), glow=16)
        self.l_t2 = layer(lambda d: text_c(d, 840, "Came to Power", font(SERIF_B, 104), PAPER, w=1000), glow=16)
        self.l_d = layer(lambda d: (d.line([(380, 1010), (620, 1010)], fill=RED, width=4),
                                    text_c(d, 1040, "1918 – 1934", font(SERIF_I, 52), DIM, w=1000)))

    def frame(self, t):
        f = self.base.copy()
        f = comp(f, self.l_k, ease(t / 0.2))
        k = ease((t - 0.05) / 0.25)
        f = comp(f, self.l_t1, k, dy=24 * (1 - k))
        k = ease((t - 0.15) / 0.25)
        f = comp(f, self.l_t2, k, dy=24 * (1 - k))
        f = comp(f, self.l_d, ease((t - 0.35) / 0.25))
        if os.environ.get("OPENING_STANDALONE", "1") == "1":
            f *= 1 - ease((t - 0.85) / 0.15)
        return f


# ------------------------------------------------------------------ shot list
def build_shots(geo):
    ph = lambda n: next(f for f in os.listdir(PHOTOS) if f.startswith(n))
    shots = [
        # (start, end, kind, payload, label, credit)
        (1.0, 6.2, "map", Map1933(geo), None, None),
        (6.2, 8.3, "clip", read_clip(FILM_N, 616.0, 2.2), "Steelworks, 1930s", CREDIT_N),
        (8.3, 10.3, "clip", read_clip(FILM_N, 639.6, 2.1), "Steelworker, 1930s", CREDIT_N),
        (10.3, 13.3, "photo", Image.open(os.path.join(PHOTOS, ph("Bundesarchiv_Bild_183_1987_0703_506"))),
         "Hitler at a radio microphone · 1 Feb 1933", credit_bundesarchiv(ph("Bundesarchiv_Bild_183_1987_0703_506"))),
        (13.3, 15.8, "clip", read_clip(FILM_P, 684.6, 2.6), "Hitler speaking · 1930s newsreel", CREDIT_P),
        (15.8, 18.6, "clip", read_clip(FILM_P, 696.2, 2.9), "Rally: 'Ein Volk, ein Reich, ein Führer'", CREDIT_P),
        (18.6, 20.6, "clip", read_clip(FILM_P, 1597.6, 2.1), "Ballot marked 'Ja' (yes)", CREDIT_P),
        (20.6, 22.6, "photo", Image.open(os.path.join(PHOTOS, ph("Bundesarchiv_Bild_102_14381"))),
         "Police and SA patrol · election day, 5 Mar 1933", credit_bundesarchiv(ph("Bundesarchiv_Bild_102_14381"))),
        (22.6, 25.4, "clip", read_clip(FILM_P, 1820.0, 2.9), "Hitler addressing a crowd · 1930s newsreel", CREDIT_P),
        (25.4, 27.6, "photo", Image.open(os.path.join(PHOTOS, ph("Bundesarchiv_Bild_102_14439"))),
         "Hitler before the Reichstag · Enabling Act, 23 Mar 1933", credit_bundesarchiv(ph("Bundesarchiv_Bild_102_14439"))),
    ]
    return shots


def caption_layer(label, credit):
    def draw(d):
        if label:
            d.text((SAFE_X0, 1170), label.upper(), font=font(MONO, 24), fill=GOLD)
        if credit:
            for i, ln in enumerate(wrap(d, credit, font(MONO_L, 18), SAFE_X1 - SAFE_X0)):
                d.text((SAFE_X0, 1475 + i * 24), ln, font=font(MONO_L, 18), fill=(165, 158, 145))
    return layer(draw)


def finish(f, idx, zoom=1.0, center=(W / 2, H / 2)):
    f = np.clip(f * VIG + GRAIN[idx % len(GRAIN)], 0, 255).astype(np.uint8)
    img = Image.fromarray(f)
    if zoom != 1.0:
        cx, cy = center
        w, h = W / zoom, H / zoom
        x0, y0 = cx - w * (cx / W), cy - h * (cy / H)
        img = img.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
    return img


# ------------------------------------------------------------------ audio
def build_audio(total, cuts, path, sr=48000):
    n = int(total * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, n)
    out = (0.035 * np.sin(2 * np.pi * 55 * t) + 0.02 * np.sin(2 * np.pi * 82.4 * t + 1)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t))
    soft = np.convolve(noise, np.ones(60) / 60, "same")
    for c in cuts:
        s, e = max(0, int((c - 0.25) * sr)), min(n, int((c + 0.25) * sr))
        out[s:e] += 0.18 * soft[s:e] * np.sin(np.linspace(0, np.pi, e - s)) ** 2
    for at, amp in ((0.0, 0.5), (27.6, 0.55), (28.2, 0.35)):
        s = int(at * sr)
        L = min(int(2.5 * sr), n - s)
        tt = np.arange(L) / sr
        out[s:s + L] += amp * np.sin(2 * np.pi * 42 * tt) * np.exp(-tt * 2.2) + 0.2 * amp * noise[s:s + L] * np.exp(-tt * 25)
    # speech
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SPEECH, "-af",
                          "highpass=f=70,lowpass=f=9000,loudnorm=I=-15:TP=-1.5:LRA=9", "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    sp = np.frombuffer(raw, np.float32)
    s = int(AUDIO_START * sr)
    L = min(len(sp), n - s)
    out[s:s + L] += sp[:L]
    out = np.tanh(out * 1.05) * 0.95
    st = np.stack([out, out], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ main
def main():
    hist, modern, out = sys.argv[1:4]
    preview = "--preview-frames" in sys.argv
    geo, _ = load_maps(hist, modern)
    shots = build_shots(geo)
    subs = sub_layers()
    caps = [caption_layer(s[4], s[5]) for s in shots]
    title = Title()
    TITLE_START = float(os.environ.get("TITLE_START", "28.0"))
    TOTAL = float(os.environ.get("OPENING_TOTAL", "33.5"))
    l_tag = layer(lambda d: (d.rounded_rectangle([SAFE_X0, 200, SAFE_X0 + 560, 246], 6, fill=RED),
                             d.text((SAFE_X0 + 16, 208), "● HISTORICAL AUDIO · ORIGINAL GERMAN", font=font(MONO, 24), fill=PAPER)))
    l_src = layer(lambda d: d.text((SAFE_X0, 258), "Hitler to Krupp workers, Essen, c. 1935/36 · British Pathé, film ID 604.06",
                                   font=font(MONO_L, 20), fill=(200, 190, 170)))
    l_ctx = layer(lambda d: (text_c(d, 860, "HISTORICAL DOCUMENTARY", font(MONO, 30), GOLD, w=1000),
                             text_c(d, 910, "Contains original Nazi-era propaganda,", font(SERIF_I, 36), PAPER, w=1000),
                             text_c(d, 956, "shown for education and context.", font(SERIF_I, 36), PAPER, w=1000)))
    cuts = [s[0] for s in shots] + [27.6, TITLE_START]
    tmp = tempfile.mkdtemp()
    wav = os.environ.get("OPENING_WAV") or os.path.join(tmp, "a.wav")
    build_audio(TOTAL, cuts, wav)
    if preview:
        frames_to = [int(x * FPS) for x in (0.5, 3.5, 7.0, 11.5, 14.5, 17.0, 19.5, 21.5, 24.0, 26.5, 30.5)]
    else:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                               "-tune", "grain", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p",
                               "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
                               "-shortest", out], stdin=subprocess.PIPE)
        frames_to = range(int(TOTAL * FPS))
    saved = []
    for i in frames_to:
        T = i / FPS
        zoom, center = 1.0, (W / 2, H / 2)
        if T < AUDIO_START:
            f = np.zeros((H, W, 3), np.float32)
            f = comp(f, l_ctx, ease(T / 0.3))
        elif T < TITLE_START:
            k = next((j for j, s in enumerate(shots) if s[0] <= T < s[1]), None)
            if k is None:
                f = np.zeros((H, W, 3), np.float32)
            else:
                s0, s1, kind, payload, label, credit = shots[k]
                lt = (T - s0) / (s1 - s0)
                if kind == "map":
                    f, zoom, center = payload.frame(lt)
                elif kind == "clip":
                    fr = payload[min(int((T - s0) * FPS), len(payload) - 1)]
                    f = media_frame(fr, lt, push=0.06, film=True, idx=i)
                else:
                    f = media_frame(payload, lt, push=0.10, pan=((-1) ** k, 0.5))
                f = comp(f, caps[k], ease((T - s0) / 0.25))
                # quick flash on cut
                if T - s0 < 0.08 and k > 0:
                    f = f + 70 * (1 - (T - s0) / 0.08)
            f = comp(f, l_tag, 1.0)
            f = comp(f, l_src, ease((T - 1.0) / 0.4))
            for s, e, L in subs:
                if s - 0.1 <= T <= e + 0.25:
                    f = comp(f, L, min(ease((T - s + 0.1) / 0.15), 1 - ease((T - e) / 0.25)))
            if T > 27.3:
                f *= 1 - ease((T - 27.3) / 0.3)
        else:
            f = title.frame((T - TITLE_START) / (TOTAL - TITLE_START))
        img = finish(f, i, zoom, center)
        if preview:
            saved.append(img.resize((360, 640)))
        else:
            ff.stdin.write(img.tobytes())
    if preview:
        sheet = Image.new("RGB", (360 * 6, 640 * 2), (0, 0, 0))
        for j, im in enumerate(saved):
            sheet.paste(im, ((j % 6) * 360, (j // 6) * 640))
        sheet.save(out)
    else:
        ff.stdin.close()
        ff.wait()
    print("done")


if __name__ == "__main__":
    main()
