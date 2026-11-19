# Phase 1 Report – Project Inspection, Narration Analysis, Research

## 1. Existing project
| Item | Finding |
|---|---|
| Repository `SteelyArc/Claude-` | One commit, only `README.md` (title line). **No existing scripts, assets, renders or automation**; nothing to reuse or overwrite. |
| Environment setup script | Failed because `requirements.txt` was missing → fixed (now runs only if the file exists). `requirements.txt` added in this phase. |
| Tools present | ffmpeg/ffprobe (system), Python 3.13, numpy 2.5, Pillow 12.3, ImageMagick `convert`, Node 22, Chromium + Playwright. 4 CPUs, 15 GB RAM. |
| Installed this session | `faster-whisper` (transcription only). Needed for Phase 2: `shapely`, `pyproj`, `pycairo` (or `skia-python`) for vector map rendering. |
| Network | OHM Overpass ✔, raw.githubusercontent.com (Natural Earth) ✔, Wikipedia en/de/pl ✔ (added this session; rate-limited), Wikimedia Commons API ✖ currently rate-limited from this container. |

## 2. Narration (the master clock – untouched)
| Property | Value |
|---|---|
| File | `audio/narration_en.mp3` (byte-identical copy of the upload, SHA-256 `e5a50d6f…7de94e`) |
| Duration | **325.878 s (5:25.88)** → video length 9,777 frames at 30 fps (+ optional end-card tail) |
| Format | MP3, mono, 44.1 kHz, 128 kb/s CBR |
| Loudness | −21.4 LUFS integrated, LRA 3.2 LU, true peak −1.4 dBTP |
| Transcript | `research/narration_transcript.json` (word-level timestamps, Whisper medium.en) |

Final mix plan: the narration is used sample-for-sample (no time-stretch, pitch change or edits). Only a uniform gain is applied for the TikTok loudness target (about −14 LUFS for the full mix, with a true-peak limit), and the voice is upmixed to centred stereo for AAC.

## 3. Accuracy issues in the narration (it cannot be changed – your decision needed)
| Time | Narration says | Issue | Proposed visual handling |
|---|---|---|---|
| **294.96 s** | "Today, West Prussia is a historical region **divided between modern-day Poland and Germany**." | **Incorrect.** All of the former province's territory, including the parts that stayed German in 1920 (Deutsch Krone, Schlochau, Flatow, Elbing, Marienburg, Marienwerder), has been in **Poland** since 1945. No part lies in today's Germany. | The map shows the historic outline entirely inside Poland, captioned "Today: entirely within Poland". The narration and the image will then disagree for about 6 s. Alternative: you correct that one sentence in ElevenLabs and send a replacement file. |
| 223.92 s | "**Thousands** of people were imprisoned, deported or murdered." | Understated. Intelligenzaktion Pommern alone ≈ 23,000 victims; Stutthof 63,000–65,000 deaths; Piaśnica 12,000–14,000. | Caption with sourced figures (marked as estimates). |
| 158.98 s | "The historic province… was dissolved" (placed after the 1920 plebiscite) | Defensible, but the formal date is 1919 de facto / 1 July 1922 de jure. | Caption "1922 – Province formally dissolved". |
| 38.02 s | "the Kingdom of Poland and Lithuania" | In the 15th century these were two states in personal union. | Labels: "Kingdom of Poland" + "Grand Duchy of Lithuania". |
| 118.66 s | "Treaty of Versailles in 1919" | Signed 28 Jun 1919, in force 10 Jan 1920 (actual transfer). | Subtitle with both dates. |
| 84.84–103 s | 19th-century development | Between 1829 and 1878 the province didn't exist separately (merged into the Province of Prussia). | Map labelled "Province of West Prussia (1878–1919 borders)". |

## 4. Research findings that shape the maps
- **Marienwerder was not in Royal Prussia.** It stayed with the Order after 1466 (later Ducal/East Prussia) and was added to West Prussia only in 1773. The 1466 map must show this.
- **1772 ≠ 1773 ≠ 1793.** Danzig and Thorn stay outside Prussia until 1793. Warmia went to East Prussia and the Netze District stayed separate, so they're drawn as distinct areas.
- **1807–1814** (Napoleonic Free City of Danzig; Thorn in the Duchy of Warsaw) isn't narrated. The maps avoid implying a continuous 1793–1919 border.
- **Versailles split West Prussia four ways** (Poland / Free City / East Prussia after the plebiscite / Germany–Grenzmark). Never colour the whole province Polish.
- **Plebiscite:** 11 July 1920; Germany 96,923 vs Poland 8,018 (**≈92.4 %**), consistent across FRUS-based figures and Wikipedia. Five right-bank Vistula villages went to Poland (12 Aug 1920).
- **1939:** annexation of Danzig declared 1 Sep 1939 (one source says 2 Sep → the screen shows "September 1939"); Reichsgau created by decree 8 Oct 1939. The Reichsgau was an annexation not recognised in international law, so it's drawn hatched, not as a normal border.
- **1945:** Danzig fell on 30 Mar 1945; Potsdam was 2 Aug 1945. The border was confirmed only in the 1990 German–Polish treaty, so it's shown as "under Polish administration pending a peace settlement" (hatched), then solid with "1990" in Scene 13.

## 5. What's still to build
1. Vector map engine (geodata → projected paths → animated border stroke-draw, territory fills, labels, parallax, camera) rendering frames straight to ffmpeg.
2. Geodata download + validation for the 8 key maps (Phase 2).
3. Archival image retrieval and licensing (blocked by the Commons rate limit; retry or inbox).
4. Photo 2.5D parallax (depth-estimation model or hand-cut layers), document desk shots, transitions.
5. Music and sound design (licence-clean sources needed – see open questions).
6. Final mux + QC tooling (frame checks, black-frame detection, loudness, safe-zone overlay).

## 6. Open questions for you
1. **294.96 s sentence**: keep the narration and correct it on screen, or send a corrected ElevenLabs file for that sentence?
2. **End card**: may the final title hold about 3–4 s after the voice ends (music tail), or must the video end exactly at 325.88 s?
3. **Music**: do you have licensed music/SFX you want used? Otherwise I'll compose a restrained score procedurally (fully licence-free) or use only CC0 tracks with documented licences.
4. **Images**: if the Commons limit persists, can you add specific archival images to `assets/images/inbox/`?

## 7. Decisions (answered by the producer)
1. 294.96 s sentence: **keep the narration, correct it on screen** ("Today: entirely within Poland").
2. End card: **allowed** to hold 3–4 s after the narration ends (music tail).
3. Music/SFX: **none supplied** → licence-free score and sound design created for the project (procedural/own synthesis, documented).
4. Images: **find other sources** → Library of Congress (Photochrom prints, PD) and Europeana added to the network allowlist; Commons used whenever its rate limit allows.
5. Background music: **removed at the producer's request** (Phase 4). Final audio = untouched narration + subtle generated sound design.
