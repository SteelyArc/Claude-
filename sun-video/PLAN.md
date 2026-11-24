# SUN: recreation plan

**Reference:** a 17.3 s, 1280×720 space montage with music only (no voiceover; checked with `/watch` and Whisper). It has 24 hard cuts, roughly one per 0.7 s beat. The title "S P A C E" types out one letter per cut over the first 3.3 s, in widely spaced white Trajan-style capitals. After the title, 4.0–8.3 s is the fastest stretch (cuts every 0.2–0.7 s). The held shots are a black hole (10.8–11.4 s) and a final Earth-Moon-star shot (15.7 s to the end).

**Recreation:**
- 62.09 s at 1080×1920, 30 fps.
- 86 BPM (one beat = 0.698 s = the reference's cut rhythm), 89 beats in total.
- The structure is kept and stretched: title build, then rapid cuts, then slower cinematic shots, then a build to the eruptions, then a held final shot.

## Scene mapping (reference → SUN)

| Reference | Time in ref | SUN shot | Beats |
|---|---|---|---|
| Ringed planets in a blue starfield + "S" | 0.0–0.6 | Full solar disk in a starfield + "S" | 0–1 |
| Earth horizon at sunrise + "SP" | 0.6–1.3 | Sun rising over a planet's limb + "S U" | 1–2 |
| Station over an orange planet + "SPAC" | 1.3–2.1 | Solar probe over the photosphere + "S U N" | 2–3 |
| Station over Earth + "SPACE" | 2.1–2.8 | Probe above the solar limb | 3–4 |
| Blue swirling nebula | 2.8–3.3 | Extreme close-up of rolling granulation | 4–5 |
| Black disc with a fiery ring | 3.3–4.0 | Total eclipse, corona streamers (title fades out) | 5–6 |
| Rapid cuts: Earth horizon, city lights, Earth glow, black hole, ring station | 4.0–8.3 | Rapid cuts: limb horizon, planet night side with the Sun, disk, granulation, flare, diamond ring, coronal loops, probes | 6–12 |
| Red nebula, planet + moon over the Milky Way | 8.3–10.7 | The Sun as a star in a red nebula, then a blue nebula with a planet | 12–16 |
| Black hole (held) | 10.8–11.4 | **Coronal loop arcade**, slow push-in | 16–20 |
| Spacecraft module close-up, ring station | 12.2–13.5 | Probe close-up, probe over the limb | 20–24 |
| Milky Way over a desert at dusk | 13.5–14.3 | Sunrise over a planet horizon with the Milky Way | 30–32 |
| *(new)* | | Surface flyover, prominence, wide rotating Sun, probe approach, sunspots | 24–40 |
| *(new: the build)* | | CME eruption, loops, CME, flares, eclipse, quick cuts, impacts on 40 / 48 / 54 / 72 | 40–74 |
| The Moon | 15.0 | Planet transit across the disk | 74–77 |
| Earth + Moon + bright blue star (held, end) | 15.7–17.3 | The Sun as a bright star behind a planet, slow pull-back, fade out | 77–89 |

## Science shown

Every effect is computed in a shader:
- **Disk:** convective granulation (Voronoi cells with dark intergranular lanes), sunspots (umbra and penumbra), faculae near the limb, and limb darkening.
- **Limb:** the chromosphere rim with spicules, and prominences.
- **Corona:** radial streamers (shown at full strength during the eclipses), and coronal loop arcades tracing magnetic field lines.
- **Eruptions:** flares, and coronal mass ejections with the classic bright front, dark cavity and bright core.
- **Spacecraft:** a generic heat-shielded solar probe that keeps its shield facing the Sun.

## Tools and their limits

No AI image or video generation tool or stock footage is available in this environment. Everything is therefore procedural:
- **Rendering:** three.js and GLSL in headless Chromium (software GL).
- **Music:** synthesised with numpy/scipy; it is original, with no copyrighted audio.
- **Encoding:** ffmpeg.

The result is a stylised, physically motivated render rather than photographic footage.

## Files

- `sun.src.html`: the renderer. `build.py` embeds the title font (Cinzel, OFL) to produce `sun.html`.
- `render_frames.js`: renders the frames (it can run as several workers in parallel).
- `music.py`: writes the score to `music.wav`.
- `assemble.sh`: encodes the frames and audio into `SUN_tiktok_1080x1920.mp4`.
