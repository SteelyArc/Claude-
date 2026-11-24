"""Broadcast-documentary style layer.

Importing this module patches the existing renderers in place:
  * every font request (DejaVu/Liberation/JetBrains paths) -> Source Serif 4 / Inter / IBM Plex Mono
  * every photo / film frame -> monochrome archive grade (S-curve + gentle split tone)
  * light-ray backgrounds toned down for a restrained look
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import design_frames as DF
import design_frames_2 as DF2
import design_frames_5 as DF5

FD = DF5.FD
_FONT_MAP = {
    DF.SERIF_B: ("SourceSerif4[opsz,wght].ttf", 600),
    DF.SERIF: ("SourceSerif4[opsz,wght].ttf", 400),
    DF.SERIF_I: ("SourceSerif4-Italic[opsz,wght].ttf", 400),
    DF.SANS_B: ("Inter[opsz,wght].ttf", 600),
    DF.SANS: ("Inter[opsz,wght].ttf", 400),
    DF.MONO: ("IBMPlexMono-Medium.ttf", None),
    DF.MONO_L: ("IBMPlexMono-Regular.ttf", None),
}
_cache = {}


def pro_font(path, size):
    key = (path, int(size))
    if key not in _cache:
        if path in _FONT_MAP:
            name, w = _FONT_MAP[path]
            _cache[key] = DF5.vf(name, int(size), w) if w else ImageFont.truetype(os.path.join(FD, name), int(size))
        else:
            _cache[key] = ImageFont.truetype(path, int(size))
    return _cache[key]


# monochrome split-tone LUT
_g = np.arange(256, dtype=np.float32) / 255
_g = np.clip(0.5 + (_g - 0.5) * 1.12, 0, 1)
_g = _g * _g * (3 - 2 * _g) * 0.35 + _g * 0.65
_SH = np.array([14, 16, 20], np.float32)
_HI = np.array([242, 234, 218], np.float32)
LUT = np.clip(_SH + (_HI - _SH) * _g[:, None], 0, 255).astype(np.uint8)  # 256 x 3


def grade_img(img):
    a = np.asarray(img.convert("RGB"), np.float32)
    g = (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114).clip(0, 255).astype(np.uint8)
    return Image.fromarray(LUT[g])


_graded = {}


def graded(src):
    k = id(src)
    if k not in _graded:
        _graded[k] = (src, grade_img(src))  # keep src alive so id stays unique
    return _graded[k][1]


def patch(*modules):
    for m in modules:
        if hasattr(m, "font"):
            m.font = pro_font
        if hasattr(m, "light_rays"):
            orig = DF2.light_rays

            def soft_rays(size, origin, color, strength=1.0, seed=0, _o=orig):
                return _o(size, origin, color, strength * 0.3, seed)
            m.light_rays = soft_rays
        if hasattr(m, "media_frame"):
            orig_mf = m.media_frame

            def mf(src, t, *a, _o=orig_mf, **k):
                film = k.get("film", False)
                g = grade_img(src) if film else graded(src)
                return _o(g, t, *a, **k)
            m.media_frame = mf


DF.font = pro_font
DF2.font = pro_font
