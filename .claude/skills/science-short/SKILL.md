---
name: science-short
description: Make a vertical (1080x1920) 3D science explainer video as one three.js HTML file, then render it to MP4. Editorial style - serif headline with a big animated number, small-caps kicker, italic one-line captions, source/uncertainty chips, thin leader-line labels, a timeline scrubber and one highlighted key word. Use when asked for a short, reel, TikTok/Shorts-style animation or "video" explaining how something works or how something changed over time, with real facts.
---

# Science short

A 6-60 s vertical explainer built in three.js, rendered deterministically to MP4.
Two story shapes cover most requests:

- **Mechanism** ("how an SSD stores data"): wide shot → camera fly-in → casing fades to a cutaway → the inside works (pulses, glowing parts) → labels.
- **Timeline** ("the supercontinent cycle"): one hero object (globe, cell, star) morphs through dated states while a big number counts and a scrubber moves.

## 1. Write the script first (facts before pixels)

Plan beats in a table before coding: `time | camera | on-screen change | headline | caption | chip`.

- **Hook (0-2 s):** one short, surprising sentence, centred, serif. ("Pangaea wasn't the first. Or the last.")
- **Body beats:** one idea per beat, 2-5 s each. A caption is one line, under ~9 words.
- **Close:** a turn or a reflective line, not a summary.
- **Real facts only.** Every number, date, name and mechanism must be correct. Where science is uncertain, say so on screen: a `?` after the name (PANNOTIA?), a chip such as `DEBATED`, `MODEL`, `PROJECTION`, or `MY CALL · NOT A FORECAST` for opinion. Cite the model or data source in a chip when a visual is based on one (`PLATE MODEL · AUTHOR YEAR`). If unsure of a fact, check it (WebSearch) or leave it out.
- Never copy another creator's branding, handle or exact script. Use the user's own handle if they give one.

## 2. Visual system

Stage: fixed `1080x1920` div scaled to fit the window; WebGL canvas + SVG overlay + DOM text.

| Element | Spec |
|---|---|
| Background | near-black `#05070c`, faint radial glow under the subject, no clutter |
| Kicker | top-left, ~26 px sans, uppercase, letter-spacing .12em, muted white |
| Headline | serif (e.g. EB Garamond / Georgia fallback); big number ~96 px + unit ~56 px on one baseline; numbers tween between beats |
| Chips | pill, 1 px border, dark fill, tiny dot + uppercase 18-20 px text, just under the headline |
| Caption | italic serif ~52 px, centred, above or below the subject, fades/slides 20 px |
| Key word | one word per caption in a solid blue box (`#2f7bff`, white bold, radius 10 px). Wrap `<b>word</b>,` in a nowrap span so punctuation doesn't wrap alone |
| Labels | 2 px thin leader lines (anchor dot + ring → elbow → text), line draws in over ~0.4 s, text on a dark translucent plate, title + one-line fact in muted text |
| In-world names | spaced uppercase (letter-spacing .3em) placed on the object (NUNA, PANGAEA) |
| Scrubber | thin line with named nodes and a small triangle playhead that moves with time |
| Data | when showing odds/shares, horizontal bars with % inside; colours mean something |
| Glow | additive-blended emissive meshes for "energy": data pulses, heat plumes, subduction lines |
| Safe area | keep text out of the top ~100 px and bottom ~180 px (platform UI) |

Lighting/camera lessons that save iterations:
- Vertical frames are narrow: use `fov` 45-50 and check the subject fits horizontally (`halfWidth = dist * tan(fov/2) * 9/16`).
- `ACESFilmicToneMapping`, exposure ~0.9, hemisphere ≤0.35, key light ~1.0. Brighter washes dark materials out to pastel.
- Keep pulses/halos small (core ~0.045, halo ~0.1 units); big glows turn into blobs.
- Put the hero action near the frame centre at the final camera position, not at the edge.

## 3. Code contract (required for rendering)

- One HTML file; three.js r128 from `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` (global `THREE`). No other external assets; textures via canvas.
- `renderer = new THREE.WebGLRenderer({ preserveDrawingBuffer: true, antialias: true })`, pixel ratio 1, size 1080x1920.
- All animation is a pure function of time: `window.renderAt(t)` sets camera, materials, DOM overlay for time `t`; `window.DURATION = N`. No `Math.random()` (use a seeded PRNG), no `Date.now()` inside it.
- Normal load: loop with `requestAnimationFrame`, hold the last frame ~1 s. With `?capture` in the URL: call `renderAt(0)` once and stop.
- Helpers: `ss(a,b,t)` smoothstep window, `easeInOutCubic`, `lerp`. Drive every element by `ss(start, end, t)` windows from the beat table.
- Labels: project 3D anchor with `vector.project(camera)` to screen px every frame.
- Cutaway: material with `clippingPlanes` + `renderer.localClippingEnabled = true`, `side: DoubleSide` so the cut shell looks hollow; sweep the plane, then fade opacity; leave an `EdgesGeometry` ghost outline.

## 4. Render and check

```bash
cd .claude/skills/science-short/scripts
[ -d node_modules/three ] || npm i three@0.128.0 --silent     # local copy if the CDN is blocked
node render.js /abs/path/page.html /abs/path/page.mp4 --stills 0,1.5,3,4.5,6   # contact sheet
node render.js /abs/path/page.html /abs/path/page.mp4                          # full MP4
```

Look at the contact sheet (Read the PNG) before the full render. Check: subject fits the frame, nothing washed out, captions on ≤2 lines, labels readable and not covering the action, every fact on screen still true. Fix, re-render stills, then render the MP4. Deliver both files and list any simplifications (things shown schematically rather than literally).
