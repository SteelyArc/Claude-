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
