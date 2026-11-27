#!/usr/bin/env python3
"""
Y2K Streetwear Design Generator  —  "CYBER SAINT"

Builds a fully vector, font-independent graphic-tee motif as SVG and
rasterises it (via headless Chromium) into a transparent RGBA PNG.

    python3 y2k_generator/generate.py            # -> y2k_design.svg + y2k_design.png
    python3 y2k_generator/generate.py --seed 7   # different sparkle/pixel scatter

All lettering is drawn with a custom stroke font defined below, so the SVG
renders identically everywhere (no font files needed for print shops).
"""
import argparse
import math
import os
import random
import subprocess
import sys

import numpy as np

W, H = 3000, 4000
CX, CY = 1500, 2020          # centre of the emblem (globe)
INK = "#07061a"             # outline colour (near-black navy)

# ----------------------------------------------------------------------------
# Stroke font (grid: x 0..4, y 0..6, y downwards). Octagonal "techno" cuts.
# ----------------------------------------------------------------------------
GLYPHS = {
    "A": [[(0, 6), (0, 1.6), (1.3, 0), (2.7, 0), (4, 1.6), (4, 6)], [(0, 3.5), (4, 3.5)]],
    "B": [[(0, 3), (0, 0), (2.9, 0), (3.7, 0.8), (3.7, 2.2), (2.9, 3), (0, 3), (0, 6), (3, 6),
           (4, 5), (4, 4), (3, 3)]],
    "C": [[(4, 0), (1.2, 0), (0, 1.2), (0, 4.8), (1.2, 6), (4, 6)]],
    "D": [[(0, 0), (0, 6), (2.6, 6), (4, 4.6), (4, 1.4), (2.6, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 0), (1.2, 0), (0, 1.2), (0, 4.8), (1.2, 6), (2.8, 6), (4, 4.8), (4, 3.2), (2.2, 3.2)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(0, 0), (0, 6)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3.6)], [(1.4, 2.4), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1.2, 0), (2.8, 0), (4, 1.2), (4, 4.8), (2.8, 6), (1.2, 6), (0, 4.8), (0, 1.2), (1.2, 0)]],
    "P": [[(0, 6), (0, 0), (2.9, 0), (4, 1.1), (4, 2), (2.9, 3.1), (0, 3.1)]],
    "R": [[(0, 6), (0, 0), (2.9, 0), (4, 1.1), (4, 2), (2.9, 3.1), (0, 3.1)], [(2.2, 3.1), (4, 6)]],
    "S": [[(4, 0), (1.1, 0), (0, 1.1), (0, 1.9), (1.1, 3), (2.9, 3), (4, 4.1), (4, 4.9), (2.9, 6), (0, 6)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 4.8), (1.2, 6), (2.8, 6), (4, 4.8), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 2.6), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "0": [[(1.2, 0), (2.8, 0), (4, 1.2), (4, 4.8), (2.8, 6), (1.2, 6), (0, 4.8), (0, 1.2), (1.2, 0)],
          [(3.2, 1.2), (0.8, 4.8)]],
    "1": [[(0.6, 1.2), (2, 0), (2, 6)]],
    "2": [[(0, 1.1), (1.1, 0), (2.9, 0), (4, 1.1), (4, 2.2), (0, 6), (4, 6)]],
    "/": [[(4, 0), (0, 6)]],
    "-": [[(0.6, 3), (3.4, 3)]],
    ".": [[(0.5, 6), (0.5, 6)]],
    ":": [[(0.5, 2), (0.5, 2)], [(0.5, 6), (0.5, 6)]],
    " ": [],
}
GLYPH_W = {"I": 0, ".": 1, ":": 1, " ": 2.2, "1": 2.6, "-": 4}


def glyph_width(ch):
    return GLYPH_W.get(ch, 4)


def glyph_path(ch, s, ox=0.0, oy=0.0):
    """SVG path data for a glyph scaled by s with its origin at (ox, oy) = top-left."""
    d = []
    for stroke in GLYPHS[ch]:
        pts = [(ox + x * s, oy + y * s) for x, y in stroke]
        d.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts))
    return " ".join(d)


def text_path(txt, s, gap, cx, top):
    """Path data for a horizontally centred line of stroke-font text."""
    widths = [glyph_width(c) * s for c in txt]
    total = sum(widths) + gap * (len(txt) - 1)
    x = cx - total / 2
    parts = []
    for c, w in zip(txt, widths):
        if GLYPHS[c]:
            parts.append(glyph_path(c, s, x, top))
        x += w + gap
    return " ".join(parts), total


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def bezier(p0, p1, p2, p3, n=90):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
    return pts, t[:, 0]


def tapered(pts, widths):
    """Polygon for a brush stroke along pts with per-point widths."""
    d = np.gradient(pts, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    left = pts + nrm * (widths[:, None] / 2)
    right = pts - nrm * (widths[:, None] / 2)
    poly = np.concatenate([left, right[::-1]])
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in poly) + " Z"


def blade(p0, p1, p2, p3, wmax, start_frac=0.55, power=1.15, side_shift=0.0):
    """Tribal blade: thick at the root, swelling slightly, tapering to a sharp tip."""
    pts, t = bezier(p0, p1, p2, p3)
    prof = (1 - t) ** power * (start_frac + (1 - start_frac) * np.sin(np.clip(t * 2.2, 0, math.pi / 2)))
    widths = wmax * prof + 1.0
    if side_shift:
        d = np.gradient(pts, axis=0)
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
        nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
        pts = pts + nrm * (side_shift * widths[:, None])
    return tapered(pts, widths)


def mirror(p):
    return (2 * CX - p[0], p[1])


def star4(cx, cy, rx, ry, inner):
    """Concave 4-point sparkle star."""
    pts = []
    for k in range(8):
        a = -math.pi / 2 + k * math.pi / 4
        if k % 2 == 0:
            r_x, r_y = rx, ry
        else:
            r_x = r_y = inner
        pts.append((cx + r_x * math.cos(a), cy + r_y * math.sin(a)))
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for k in range(1, 9):
        p = pts[k % 8]
        # quadratic curve through the centre-ish for concave sides
        q = (cx + (pts[k - 1][0] + p[0] - 2 * cx) * 0.18, cy + (pts[k - 1][1] + p[1] - 2 * cy) * 0.18)
        d += f" Q{q[0]:.1f} {q[1]:.1f} {p[0]:.1f} {p[1]:.1f}"
    return d + " Z", pts


# ----------------------------------------------------------------------------
# Design
# ----------------------------------------------------------------------------
def defs():
    return f"""
<defs>
  <!-- classic Y2K chrome: sky -> horizon line -> ground reflection -->
  <linearGradient id="chrome" x1="0" y1="-260" x2="0" y2="260" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="0.16" stop-color="#e9eefc"/>
    <stop offset="0.40" stop-color="#9aa6c9"/>
    <stop offset="0.49" stop-color="#262c5c"/>
    <stop offset="0.53" stop-color="#4f5fb4"/>
    <stop offset="0.70" stop-color="#cfdcff"/>
    <stop offset="0.86" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#a9b6e6"/>
  </linearGradient>
  <linearGradient id="chromeSmall" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="0.45" stop-color="#a7b2d6"/>
    <stop offset="0.5" stop-color="#2c3468"/>
    <stop offset="0.58" stop-color="#7f8fd6"/>
    <stop offset="1" stop-color="#ffffff"/>
  </linearGradient>
  <linearGradient id="chromeRing" x1="0" y1="-160" x2="0" y2="160" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="0.45" stop-color="#9aa6c9"/>
    <stop offset="0.5" stop-color="#262c5c"/>
    <stop offset="0.58" stop-color="#8fa0e8"/>
    <stop offset="1" stop-color="#ffffff"/>
  </linearGradient>
  <linearGradient id="starLight" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#c3cdf0"/>
  </linearGradient>
  <linearGradient id="starDark" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#7b88c4"/>
    <stop offset="0.6" stop-color="#2a2f66"/>
    <stop offset="1" stop-color="#5d6fd0"/>
  </linearGradient>
  <linearGradient id="wing" x1="{CX}" y1="0" x2="{CX + 1400}" y2="0" gradientUnits="userSpaceOnUse" spreadMethod="reflect">
    <stop offset="0" stop-color="#5a12ff"/>
    <stop offset="0.45" stop-color="#1f3dff"/>
    <stop offset="1" stop-color="#00c8ff"/>
  </linearGradient>
  <linearGradient id="wingL" x1="{CX}" y1="0" x2="{CX - 1400}" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#5a12ff"/>
    <stop offset="0.45" stop-color="#1f3dff"/>
    <stop offset="1" stop-color="#00c8ff"/>
  </linearGradient>
  <radialGradient id="globe" cx="{CX - 150}" cy="{CY - 190}" r="640" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#3b2dff"/>
    <stop offset="0.45" stop-color="#1a0f8a"/>
    <stop offset="0.85" stop-color="#0a0640"/>
    <stop offset="1" stop-color="#07061a"/>
  </radialGradient>
  <linearGradient id="pinkExtrude" x1="0" y1="-260" x2="0" y2="300" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#ff5ce1"/>
    <stop offset="1" stop-color="#c2008f"/>
  </linearGradient>
  <linearGradient id="loadbar" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#ff2bd6"/>
    <stop offset="1" stop-color="#00d9ff"/>
  </linearGradient>
</defs>"""


def chrome_word(word, arc_cy, R, mode, s=74, sw=100, outline=26, extrude=(0, 44)):
    """Big chrome bubble letters laid out on an arc. mode 'arch' (top) or 'smile' (bottom)."""
    gap = sw + 70
    widths = [glyph_width(c) * s for c in word]
    total = sum(widths) + gap * (len(word) - 1)
    out = []
    x = -total / 2
    for c, w in zip(word, widths):
        mid = x + w / 2
        th = mid / R
        if mode == "arch":
            px, py, rot = CX + R * math.sin(th), arc_cy - R * math.cos(th), math.degrees(th)
        else:
            px, py, rot = CX + R * math.sin(th), arc_cy + R * math.cos(th), -math.degrees(th)
        d = glyph_path(c, s, -w / 2, -3 * s)
        # skew for speed, extrude for depth
        steps = 10
        ext = [(extrude[0] * k / steps, extrude[1] * k / steps) for k in range(1, steps + 1)]
        g = [f'<g transform="translate({px:.1f} {py:.1f}) rotate({rot:.2f}) skewX(-9)">']
        for ex, ey in ext:
            g.append(f'<path d="{d}" transform="translate({ex:.1f} {ey:.1f})" fill="none" stroke="{INK}" '
                     f'stroke-width="{sw + 2 * outline}" stroke-linecap="round" stroke-linejoin="round"/>')
        for ex, ey in ext:
            g.append(f'<path d="{d}" transform="translate({ex:.1f} {ey:.1f})" fill="none" stroke="url(#pinkExtrude)" '
                     f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
        g.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw + 16}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
        g.append(f'<path d="{d}" fill="none" stroke="url(#chrome)" stroke-width="{sw}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
        # specular highlight streak
        g.append(f'<path d="{d}" transform="translate(-14 -16)" fill="none" stroke="#ffffff" '
                 f'stroke-opacity="0.9" stroke-width="{sw * 0.16:.1f}" stroke-linecap="round" '
                 f'stroke-linejoin="round" stroke-dasharray="{s * 1.3:.0f} 99999"/>')
        g.append("</g>")
        out.append("\n".join(g))
        x += w + gap
    return "\n".join(out)


def small_text(txt, s, cy, fill="#ffffff", sw=None, outline=None, gap=None):
    sw = sw or s * 0.62
    outline = outline or s * 0.42
    gap = gap or s * 1.9
    d, total = text_path(txt, s, gap, CX, cy - 3 * s)
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw + 2 * outline:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="{sw:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'), total


def wings():
    """Symmetric tribal blades radiating from the globe."""
    C = np.array([CX, CY])
    # (p0, p1, p2, p3) relative to centre, right side; width
    specs = [
        (((230, -200), (620, -560), (1080, -520), (1360, -1060)), 430),
        (((280, -40), (720, -260), (1130, -220), (1400, -600)), 340),
        (((300, 110), (740, 60), (1080, 30), (1350, -170)), 270),
        (((270, 250), (660, 380), (960, 350), (1200, 170)), 230),
        (((190, 370), (440, 660), (760, 760), (1000, 600)), 200),
    ]
    # little reverse hooks that give the tribal "thorns"
    hooks = [
        (((860, -560), (930, -720), (1010, -800), (960, -930)), 120),
        (((1010, -280), (1090, -400), (1170, -450), (1150, -560)), 100),
        (((960, 330), (1040, 420), (1110, 470), (1100, 580)), 80),
        (((700, 700), (760, 800), (830, 860), (800, 960)), 80),
    ]
    paths_r, shine_r = [], []
    for (pp, w) in specs + hooks:
        abs_pts = [tuple(C + np.array(p)) for p in pp]
        paths_r.append(blade(*abs_pts, w))
        shine_r.append(blade(*abs_pts, w * 0.28, side_shift=-0.25))
    paths_l, shine_l = [], []
    for (pp, w) in specs + hooks:
        abs_pts = [mirror(tuple(C + np.array(p))) for p in pp]
        paths_l.append(blade(*abs_pts, w))
        shine_l.append(blade(*abs_pts, w * 0.28, side_shift=0.25))
    out = []
    for d in paths_r + paths_l:
        out.append(f'<path d="{d}" fill="{INK}" stroke="{INK}" stroke-width="52" stroke-linejoin="round"/>')
    for d in paths_r:
        out.append(f'<path d="{d}" fill="url(#wing)"/>')
    for d in paths_l:
        out.append(f'<path d="{d}" fill="url(#wingL)"/>')
    for d in shine_r + shine_l:
        out.append(f'<path d="{d}" fill="#bff4ff" fill-opacity="0.85"/>')
    return "\n".join(out)


def globe(r=470, tilt=math.radians(24)):
    out = [f'<circle cx="{CX}" cy="{CY}" r="{r + 26}" fill="{INK}"/>',
           f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="url(#globe)"/>']

    def proj(lat, lon):
        x = np.cos(lat) * np.sin(lon)
        y = -np.sin(lat)
        z = np.cos(lat) * np.cos(lon)
        y2 = y * math.cos(tilt) - z * math.sin(tilt)
        z2 = y * math.sin(tilt) + z * math.cos(tilt)
        return CX + r * x, CY + r * y2, z2

    lines = []
    for lat_deg in range(-60, 90, 30):
        lon = np.linspace(-math.pi, math.pi, 240)
        lines.append(proj(np.full_like(lon, math.radians(lat_deg)), lon))
    for lon_deg in range(0, 180, 30):
        lat = np.linspace(-math.pi, math.pi, 240)
        lines.append(proj(lat, np.full_like(lat, math.radians(lon_deg + 10))))
    for xs, ys, zs in lines:
        seg = []
        for x, y, z in zip(xs, ys, zs):
            if z > 0:
                seg.append((x, y))
            elif len(seg) > 1:
                out.append(_poly(seg))
                seg = []
            else:
                seg = []
        if len(seg) > 1:
            out.append(_poly(seg))
    # glass highlight
    out.append(f'<ellipse cx="{CX - 170}" cy="{CY - 230}" rx="190" ry="105" transform="rotate(-32 {CX - 170} {CY - 230})" '
               f'fill="#ffffff" fill-opacity="0.22"/>')
    out.append(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="#00e1ff" stroke-width="12"/>')
    return "\n".join(out)


def _poly(seg):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in seg)
    return f'<path d="{d}" fill="none" stroke="#38e6ff" stroke-opacity="0.85" stroke-width="7" stroke-linecap="round"/>'


def ring_half(rx, ry, angle, front):
    """Half of a tilted chrome orbit ring (front = lower half)."""
    sweep = "0" if front else "1"
    d = f"M{-rx} 0 A{rx} {ry} 0 0 {sweep} {rx} 0"
    if front:
        d = f"M{-rx} 0 A{rx} {ry} 0 0 0 {rx} 0"
    else:
        d = f"M{-rx} 0 A{rx} {ry} 0 0 1 {rx} 0"
    return (f'<g transform="translate({CX} {CY}) rotate({angle})">'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="96" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="url(#chromeRing)" stroke-width="56" stroke-linecap="round"/>'
            f'<path d="{d}" transform="translate(0 -12)" fill="none" stroke="#ffffff" stroke-width="10" '
            f'stroke-linecap="round" stroke-dasharray="260 140"/>'
            f'</g>')


def halo(cy, rx=330, ry=78):
    return (f'<ellipse cx="{CX}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{INK}" stroke-width="104"/>'
            f'<ellipse cx="{CX}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="#ff2bd6" stroke-width="64"/>'
            f'<g transform="translate({CX} {cy})"><ellipse cx="0" cy="0" rx="{rx}" ry="{ry}" fill="none" '
            f'stroke="url(#chromeRing)" stroke-width="40" transform="scale(1 1)"/></g>'
            f'<ellipse cx="{CX}" cy="{cy - 10}" rx="{rx - 40}" ry="{ry - 30}" fill="none" stroke="#ffffff" '
            f'stroke-width="9" stroke-dasharray="180 520"/>')


def chrome_star(cx, cy, rx, ry, inner, outline=30):
    d, pts = star4(cx, cy, rx, ry, inner)
    out = [f'<path d="{d}" fill="{INK}" stroke="{INK}" stroke-width="{2 * outline}" stroke-linejoin="round"/>']
    # bevelled facets: each arm split along its spine into a light and dark half
    for k in range(0, 8, 2):
        tip = pts[k]
        left = pts[(k - 1) % 8]
        right = pts[(k + 1) % 8]
        # light/dark alternate to simulate a single light source top-left
        light_first = k in (0, 6)
        for side, (a, b) in enumerate(((left, tip), (tip, right))):
            fill = "url(#starLight)" if (side == 0) == light_first else "url(#starDark)"
            out.append(f'<path d="M{cx:.1f} {cy:.1f} L{a[0]:.1f} {a[1]:.1f} L{b[0]:.1f} {b[1]:.1f} Z" fill="{fill}"/>')
    # clip facets to concave outline by redrawing concave notch areas is complex;
    # instead, draw facets clipped with a clipPath
    return d, out


def star_group(cx, cy, rx, ry, inner, cid):
    d, parts = chrome_star(cx, cy, rx, ry, inner)
    outline = parts[0]
    facets = "\n".join(parts[1:])
    return (f'<clipPath id="{cid}"><path d="{d}"/></clipPath>{outline}'
            f'<g clip-path="url(#{cid})">{facets}</g>'
            f'<path d="{d}" fill="none" stroke="#ffffff" stroke-opacity="0.6" stroke-width="5"/>')


def sparkle(cx, cy, r, color):
    d, _ = star4(cx, cy, r * 0.62, r, r * 0.14)
    return (f'<path d="{d}" fill="{INK}" stroke="{INK}" stroke-width="{max(14, r * 0.28):.0f}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{color}"/>')


def pixels(x0, y0, pattern, size, color):
    out = []
    for j, row in enumerate(pattern):
        for i, ch in enumerate(row):
            if ch == "#":
                x, y = x0 + i * size, y0 + j * size
                out.append(f'<rect x="{x - 7}" y="{y - 7}" width="{size + 14}" height="{size + 14}" fill="{INK}"/>')
    for j, row in enumerate(pattern):
        for i, ch in enumerate(row):
            if ch == "#":
                x, y = x0 + i * size, y0 + j * size
                out.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{color}"/>')
    return "\n".join(out)


CURSOR = [
    "#.........",
    "##........",
    "#o#.......",
    "#oo#......",
    "#ooo#.....",
    "#oooo#....",
    "#ooooo#...",
    "#oooooo#..",
    "#ooooooo#.",
    "#oooo#####",
    "#o#oo#....",
    "##.#oo#...",
    "#..#oo#...",
    "....#oo#..",
    "....####..",
]


def cursor(x0, y0, size):
    out = []
    pad = 9
    for j, row in enumerate(CURSOR):
        for i, ch in enumerate(row):
            if ch in "#o":
                out.append(f'<rect x="{x0 + i * size - pad}" y="{y0 + j * size - pad}" width="{size + 2 * pad}" '
                           f'height="{size + 2 * pad}" fill="{INK}"/>')
    for j, row in enumerate(CURSOR):
        for i, ch in enumerate(row):
            if ch in "#o":
                col = INK if ch == "#" else "#ffffff"
                out.append(f'<rect x="{x0 + i * size}" y="{y0 + j * size}" width="{size}" height="{size}" fill="{col}"/>')
    return "\n".join(out)


def loading_bar(cy, width=1180, height=92, filled=7, segs=10):
    x0 = CX - width / 2
    out = [f'<rect x="{x0 - 22}" y="{cy - height / 2 - 22}" width="{width + 44}" height="{height + 44}" rx="{height / 2 + 22}" fill="{INK}"/>',
           f'<rect x="{x0}" y="{cy - height / 2}" width="{width}" height="{height}" rx="{height / 2}" fill="none" '
           f'stroke="url(#chromeSmall)" stroke-width="14"/>']
    inner_w = width - 56
    seg_w = inner_w / segs
    for k in range(filled):
        sx = x0 + 28 + k * seg_w + 6
        out.append(f'<rect x="{sx:.1f}" y="{cy - height / 2 + 22}" width="{seg_w - 12:.1f}" height="{height - 44}" '
                   f'rx="8" fill="url(#loadbar)"/>')
    return "\n".join(out)


def barcode(x0, cy, h, rng):
    out = []
    x = x0
    bars = []
    for _ in range(18):
        w = rng.choice([6, 6, 10, 14, 20])
        bars.append((x, w))
        x += w + rng.choice([8, 10, 14])
    total = x - x0
    out.append(f'<rect x="{x0 - 22}" y="{cy - h / 2 - 22}" width="{total + 34}" height="{h + 44}" rx="14" fill="{INK}"/>')
    for bx, bw in bars:
        out.append(f'<rect x="{bx}" y="{cy - h / 2}" width="{bw}" height="{h}" fill="#e9eefc"/>')
    return "\n".join(out), total


def build_svg(seed=2000):
    rng = random.Random(seed)
    body = []

    # --- layer 1: tribal wings ------------------------------------------------
    body.append(wings())

    # --- layer 2: orbit ring (back half), globe, ring front -------------------
    ring_rx, ring_ry, ring_ang = 760, 168, -14
    body.append(ring_half(ring_rx, ring_ry, ring_ang, front=False))
    body.append(globe())
    body.append(ring_half(ring_rx, ring_ry, ring_ang, front=True))

    # --- layer 3: halo + chrome star -----------------------------------------
    body.append(halo(CY - 790))
    body.append(star_group(CX, CY, 380, 690, 92, "starclip"))

    # --- layer 4: sparkles & pixel bits --------------------------------------
    sparkle_spots = [(CX - 640, CY - 720, 120, "#ffffff"), (CX + 700, CY - 590, 86, "#ff2bd6"),
                     (CX + 560, CY + 640, 110, "#ffffff"), (CX - 760, CY + 470, 76, "#00e1ff"),
                     (CX - 300, CY - 1000, 60, "#00e1ff"), (CX + 330, CY - 1040, 70, "#ffffff")]
    for (x, y, r, c) in sparkle_spots:
        jx, jy = rng.uniform(-25, 25), rng.uniform(-25, 25)
        body.append(sparkle(x + jx, y + jy, r, c))
    body.append(cursor(CX + 300, CY + 300, 20))

    # --- layer 5: lettering ---------------------------------------------------
    body.append(chrome_word("CYBER", arc_cy=780 + 2600, R=2600, mode="arch"))
    body.append(chrome_word("SAINT", arc_cy=3150 - 2600, R=2600, mode="smile"))

    tag, tw = small_text("DIGITAL SALVATION", 15, 3520, fill="#ffffff")
    body.append(tag)
    # info row: barcode | loading bar | version tag
    bar_w = 980
    body.append(loading_bar(3715, width=bar_w))
    bc, bw = barcode(0, 3715, 92, random.Random(seed))
    body.append(f'<g transform="translate({CX - bar_w / 2 - 90 - bw:.0f} 0)">{bc}</g>')
    v, vw = small_text("V.2K", 15, 3715, fill="#00e1ff")
    body.append(f'<g transform="translate({bar_w / 2 + 90 + vw / 2:.0f} 0)">{v}</g>')
    tiny, _ = small_text("SYSTEM ONLINE - EST 2000 - VOL 01", 7.5, 3870, fill="#c9d6ff", sw=6, outline=6, gap=13)
    body.append(tiny)

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<title>CYBER SAINT — Y2K graphic</title>{defs()}\n' + "\n".join(body) + "\n</svg>\n")
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2000)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "y2k_design"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    svg_path, png_path = out + ".svg", out + ".png"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(build_svg(args.seed))
    print("wrote", svg_path)
    render = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.js")
    subprocess.run(["node", render, svg_path, png_path, str(W), str(H)], check=True)
    print("wrote", png_path)


if __name__ == "__main__":
    sys.exit(main())
