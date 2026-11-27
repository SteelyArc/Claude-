# Y2K Streetwear Design Generator — "CYBER SAINT"

A print-ready Y2K graphic tee / oversized hoodie design, generated entirely from code.

| File | Contents |
|---|---|
| `y2k_design.png` | 3000 × 4000 px, RGBA with a real transparent alpha channel (ready for DTG/DTF) |
| `y2k_design.svg` | Scalable vector version (no font dependencies: all lettering is paths) |
| `y2k_generator/generate.py` | Generator: builds the SVG, then renders the PNG |
| `y2k_generator/render.js` | Renders the SVG with headless Chromium (Playwright) onto a transparent background |

## Regenerate

```bash
pip install numpy
python3 y2k_generator/generate.py            # writes y2k_design.svg + y2k_design.png
python3 y2k_generator/generate.py --seed 7   # varies the sparkle positions
```

Requires Node.js with `playwright` (Chromium) for the PNG export.

## Design

- Chrome bubble lettering "CYBER / SAINT" set on an arc, with a hot-pink 3D extrusion and horizon-line chrome
- Central emblem: a wireframe cyber globe, a bevelled chrome 4-point star, a tilted chrome orbit ring and a halo
- Symmetric tribal wings with an electric violet → blue → cyan gradient and highlights
- Early-internet details: a pixel cursor, a loading bar, a barcode and a tech microline
- Every element has a dark navy outline, so the motif works on both black and white shirts

---

# Phoenix Embroidery — vintage Japanese-style hoodie graphic

| File | Contents |
|---|---|
| `phoenix_embroidery.png` | 3000 × 4000 px, RGBA, transparent background: phoenix rising from flames in an embroidery look |
| `phoenix_embroidery/phoenix.js` | Procedural stitch renderer (canvas): satin, herringbone feather barbs, stem-stitch outlines, tatami fill |
| `phoenix_embroidery/render.js` | Renders in headless Chromium and exports the PNG |

```bash
node phoenix_embroidery/render.js                 # -> phoenix_embroidery.png
node phoenix_embroidery/render.js out.png 42      # different seed = different stitch irregularities / flame shapes
```

Every visible mark is a simulated single thread with its own shading (dark at the needle holes, a highlight on the raised part, a fine groove between threads, and a glint of twisted thread). Overlapping layers cast a soft "raised" shadow that only falls on stitches already underneath, so nothing appears outside the motif.
