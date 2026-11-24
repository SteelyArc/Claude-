#!/usr/bin/env python3
"""Edit real NASA solar footage into the 62 s vertical SUN video.

Every shot is cut from public-domain NASA footage (SDO, Parker Solar Probe / WISPR, eclipse imagery,
SWFO-L1 visualisation) and reframed to 1080x1920 with a smooth virtual camera move,
graded into one gold/orange palette, and cut on the beat of the score (86 BPM).

Usage: python3 edit.py <clips_dir> <music.wav> <out.mp4> [--preview N] [--stills b1,b2,...]
"""
import json, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
BPM = 86
B = 60 / BPM
BEATS = 89
DUR = BEATS * B
NFRAMES = round(DUR * FPS)
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ edit decision list
# clip: file key; t: source start (s); sp: playback speed; c0/c1: (cx, cy, zoom) in normalised source
# coords at shot start/end (zoom 1 = full source height); r0/r1: roll (deg); g: grade; fx: extras
SHOTS = json.load(open(os.path.join(HERE, "shots.json")))
IMPACTS = [40, 48, 54, 72]


def ease(x):
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ grading
def gradient_lut():
    # black -> deep red -> orange -> gold -> white-gold (solar palette)
    stops = [(0, (0, 0, 0)), (.18, (8, 2, 60)), (.38, (10, 40, 190)), (.6, (40, 140, 250)), (.8, (120, 210, 255)), (1, (225, 245, 255))]  # BGR
    lut = np.zeros((256, 3), np.float32)
    xs = [s[0] for s in stops]
    for c in range(3):
        lut[:, c] = np.interp(np.linspace(0, 1, 256), xs, [s[1][c] for s in stops])
    return lut.astype(np.uint8)


GOLD = gradient_lut()


def grade(img, mode, amt=1.0):
    if mode == "gold":  # map luminance through the solar gradient (for single-wavelength SDO channels)
        lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mapped = GOLD[lum]
        return cv2.addWeighted(mapped, amt, img, 1 - amt, 0) if amt < 1 else mapped
    if mode == "warm":  # keep natural colours, push toward gold
        f = img.astype(np.float32)
        f[..., 0] *= .82; f[..., 1] *= .97; f[..., 2] *= 1.06
        return np.clip(f, 0, 255).astype(np.uint8)
    if mode == "cool":  # space shots: deepen blacks, cool shadows
        f = img.astype(np.float32)
        f[..., 0] *= 1.06; f[..., 2] *= .96
        return np.clip(f, 0, 255).astype(np.uint8)
    return img


def finish(img, flash=0.0, fade=0.0, bloom=0.35, grain=5.0, rng=np.random.default_rng(3)):
    f = img.astype(np.float32)
    # bloom: blurred highlights added back
    small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hi = np.clip(small - 150, 0, None) * 1.6
    hi = cv2.GaussianBlur(hi, (0, 0), 18)
    f += cv2.resize(hi, (W, H), interpolation=cv2.INTER_LINEAR) * bloom
    # gentle filmic contrast
    f = 255 * (1 - np.exp(-f / 255 * 1.35)) / (1 - math.exp(-1.35))
    f = f * VIG
    if grain: f += rng.normal(0, grain, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    if flash: f = f * (1 - flash) + np.array([205, 235, 255], np.float32) * flash
    if fade: f *= (1 - fade)
    return np.clip(f, 0, 255).astype(np.uint8)


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - .38 * (((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2))[..., None].clip(0, 1)


# ------------------------------------------------------------------ title (letters appear on each cut)
def make_title():
    font = ImageFont.truetype(os.path.join(HERE, "Cinzel-Regular.ttf"), 170)
    spacing = 105
    letters = "SUN"
    ws = [font.getbbox(c)[2] - font.getbbox(c)[0] for c in letters]
    total = sum(ws) + spacing * 2
    x0 = (W - total) / 2
    y = 830
    layers = []
    for n in range(1, 4):
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        x = x0
        for i, c in enumerate(letters):
            if i < n: d.text((x - font.getbbox(c)[0], y), c, font=font, fill=255)
            x += ws[i] + spacing
        glow = im.filter(ImageFilter.GaussianBlur(18))
        layers.append((np.asarray(im, np.float32) / 255, np.asarray(glow, np.float32) / 255))
    return layers


TITLE = make_title()


def put_title(img, n, alpha):
    if n <= 0 or alpha <= 0: return img
    core, glow = TITLE[n - 1]
    f = img.astype(np.float32)
    f += (glow[..., None] * np.array([90, 170, 255], np.float32) * .55) * alpha
    a = (core * alpha)[..., None]
    f = f * (1 - a) + 255 * a
    return np.clip(f, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ source reading
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", path], capture_output=True, text=True)
    j = json.loads(r.stdout)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def read_frames(path, t0, sp, n, max_h):
    sw, sh, dur = probe(path)
    scale = min(1.0, max_h / sh)
    ww, hh = int(sw * scale) // 2 * 2, int(sh * scale) // 2 * 2
    t0 = max(0.0, min(t0, dur - 0.2))
    need = n * sp / FPS + 0.5
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{need:.3f}", "-i", path,
           "-vf", f"setpts=PTS/{sp},fps={FPS},scale={ww}:{hh}:flags=lanczos", "-an", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fs = ww * hh * 3
    frames = [np.frombuffer(raw[i:i + fs], np.uint8).reshape(hh, ww, 3) for i in range(0, len(raw) - fs + 1, fs)]
    if not frames: raise RuntimeError(f"no frames from {path} @ {t0}")
    while len(frames) < n: frames.append(frames[-1])  # hold last frame if the clip runs out
    return frames[:n]


def reframe(src, cx, cy, zoom, roll):
    sh, sw = src.shape[:2]
    out_h_src = sh / zoom                      # source pixels covered by the output height
    s = H / out_h_src
    M = cv2.getRotationMatrix2D((cx * sw, cy * sh), roll, s)
    M[0, 2] += W / 2 - cx * sw
    M[1, 2] += H / 2 - cy * sh
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def clamp_center(shape, cx, cy, z, roll):
    """Keep the (rotated) crop inside the source so no hard black edges appear; wide shots larger than the source stay centred."""
    sh_, sw_ = shape[:2]
    ch = sh_ / z; cw = ch * W / H
    c, s_ = abs(math.cos(math.radians(roll))), abs(math.sin(math.radians(roll)))
    ex, ey = (cw * c + ch * s_) / 2, (cw * s_ + ch * c) / 2
    px, py = cx * sw_, cy * sh_
    if 2 * ex <= sw_: px = min(max(px, ex), sw_ - ex)
    if 2 * ey <= sh_: py = min(max(py, ey), sh_ - ey)
    return px / sw_, py / sh_


# ------------------------------------------------------------------ render
def shot_frames(sh, clips, f_from=None, f_to=None):
    f0, f1 = round(sh["b0"] * B * FPS), round(sh["b1"] * B * FPS)
    n = f1 - f0
    c0, c1 = sh["c0"], sh.get("c1", sh["c0"])
    max_zoom = max(c0[2], c1[2])
    frames = read_frames(os.path.join(clips, sh["clip"] + ".mp4"), sh.get("t", 0), sh.get("sp", 1), n, int(H * max_zoom * 1.1))
    for i in range(n):
        gi = f0 + i
        if f_from is not None and not (f_from <= gi < f_to): continue
        k = ease(i / max(1, n - 1)) if sh.get("ease", True) else i / max(1, n - 1)
        cx, cy, z = (c0[j] + (c1[j] - c0[j]) * k for j in range(3))
        roll = sh.get("r0", 0) + (sh.get("r1", sh.get("r0", 0)) - sh.get("r0", 0)) * k
        # impact shake
        if sh.get("shake"):
            a = sh["shake"] * .004 * math.exp(-i / FPS * 3.5)
            cx += a * math.sin(gi * 1.9); cy += a * math.sin(gi * 2.7 + 1)
        src = frames[i]
        if sh.get("blank_below"):
            src = src.copy(); src[int(src.shape[0] * sh["blank_below"]):] = 0
        if not sh.get("noclamp"):
            cx, cy = clamp_center(src.shape, cx, cy, z, roll)
        img = reframe(src, cx, cy, z, roll)
        img = grade(img, sh.get("g", "none"), sh.get("ga", 1.0))
        if sh.get("bright"): img = cv2.convertScaleAbs(img, alpha=sh["bright"], beta=0)
        t = gi / FPS
        lt = i / FPS
        flash = .10 * math.exp(-lt * 14)                                  # small exposure kick on every cut
        if sh.get("flash"): flash = max(flash, .85 * math.exp(-lt * 7))
        fade = 0.0
        if sh.get("fadein"): fade = max(fade, 1 - min(1, lt / sh["fadein"]))
        fade = max(fade, min(1, max(0, (t - (DUR - 2.4)) / 2.2)))
        out = finish(img, flash=flash, fade=fade, bloom=sh.get("bloom", .35))
        # title: S on beat 0, S U on beat 1, S U N from beat 2, fades out before beat 6
        bt = t / B
        if bt < 6:
            n_l = 1 if bt < 1 else 2 if bt < 2 else 3
            alpha = min(1, bt / .2) * (1 - max(0, min(1, (bt - 5.55) / .45)))
            out = put_title(out, n_l, alpha)
        yield gi, out


def main():
    clips, music, out = sys.argv[1], sys.argv[2], sys.argv[3]
    stills = None
    if "--stills" in sys.argv:
        stills = [float(x) for x in sys.argv[sys.argv.index("--stills") + 1].split(",")]
    if stills:
        os.makedirs(out, exist_ok=True)
        for bt in stills:
            gi = round(bt * B * FPS)
            sh = next(s for s in SHOTS if s["b0"] * B * FPS <= gi < s["b1"] * B * FPS)
            for g, img in shot_frames(sh, clips, gi, gi + 1):
                cv2.imwrite(f"{out}/b{bt:05.1f}.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", music, "-map", "0:v", "-map", "1:a", "-t", f"{DUR:.3f}",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
                            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    written = 0
    for sh in SHOTS:
        for gi, img in shot_frames(sh, clips):
            enc.stdin.write(img.tobytes()); written += 1
        print(f"shot {sh['b0']:>5}-{sh['b1']:<5} {sh['clip']:<12} frames {written}/{NFRAMES}", flush=True)
    enc.stdin.close(); enc.wait()
    print("wrote", out, written, "frames")


if __name__ == "__main__":
    main()
