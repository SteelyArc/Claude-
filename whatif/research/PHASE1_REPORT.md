# Phase 1 – Project inspection: *What if Poland-Lithuania had never been partitioned?*

## 1. Repository and pipeline

| Finding | Detail |
|---|---|
| Working branch `ccr-17c5c430-reblfq` | Was empty (README only). This film lives in `whatif/`. |
| Earlier projects (other branches) | West Prussia (×2), *The First Partition 1772*, *The Second and Third Partitions*. All three use a **light parchment atlas** look, so the new concepts deliberately avoid it. |
| Reused (copied, not modified) | Border-verified political layers for 1772, 1773, 1791, 1793 and 1795 (`data/layers.pkl`, built from OpenHistoricalMap CC0 relations and checked against a georeferenced atlas reference; the 1772 Russian zone and the 1793 Russian line were corrected; see `data/BORDER_VERIFICATION_inherited.md`). Terrarium z8 elevation tiles. OFL fonts (Cormorant, Cinzel, EB Garamond, Source Sans 3). Public-domain paintings and prints with recorded sources. |
| New engine | `tools/core.py`: Skia renderer with a perspective (2.5D) camera, geodata-to-path conversion, typography with per-letter reveals, bloom, grain and vignette, and an ffmpeg H.264 writer. `tools/build_relief.py`: hill-shade in the project projection. `tools/depth.py`: per-pixel depth for paintings (Depth Anything V2 Small, Apache-2.0) for true parallax. |
| Environment fixes | Installed skia-python, shapely, pyproj, opencv, torch (CPU), transformers, faster-whisper and libEGL. Hugging Face's Xet storage is blocked, so models are fetched with `HF_HUB_DISABLE_XET=1`. PyAV is incompatible with faster-whisper, so audio is decoded through ffmpeg into memory. |

## 2. Voice-over (master timeline)

| Property | Value |
|---|---|
| File | `audio/narration_original.mp3` (byte-identical copy of the upload, MD5 `3343581c59671553e140b448c42acb0f`) |
| Duration | **298.84 s (4:58.84)** |
| Format | MP3, 44.1 kHz, mono, 128 kb/s |
| Transcript | `research/transcript_words.json`: word-level timestamps (faster-whisper medium.en) |

The narration is never re-encoded for analysis on disk. The final mix will use it at its original speed and pitch, with music and effects ducked under it.

### Narrative structure (from the transcript)

| Time | Section | Status |
|---|---|---|
| 0:00–0:32 | Hook: "What if…", imagined Europe, "In our timeline this country disappeared" | framing |
| 0:32–1:10 | The Commonwealth and its 18th-century weakness | **documented** |
| 1:10–1:32 | Constitution of 3 May 1791 | **documented** |
| 1:32–2:00 | 1792 Russian intervention and Targowica; Second (1793) and Third (1795) Partitions | **documented** |
| 2:00–2:42 | The alternate timeline: the reforms hold, no partitions | **hypothetical** |
| 2:42–4:07 | A 19th-century Commonwealth: federation, peoples, cities, Napoleon, alliances, balance of power | **hypothetical** |
| 4:07–4:25 | Open questions (WWI, Germany, Russia, modern borders) | hypothetical questions |
| 4:25–4:58 | Return to reality: why it disappeared; the closing "What if" | documented + framing |

## 3. Fact-check of the narration

All five required dates match the narration: 1772 First Partition, 3 May 1791 Constitution, 1792 Russian intervention, 1793 Second Partition (Russia and Prussia), 1795 Third Partition (Russia, Prussia, Austria).

Minor notes. None requires changing the audio; they only affect on-screen wording.
1. Whisper spells **"Targovica"**. On screen it will read **Targowica Confederation** (signed in St Petersburg on 27 April 1792, proclaimed 14 May 1792; Russian troops crossed the border on 18 May 1792).
2. "One of the first modern written constitutions in Europe" is a safe formulation, often given as the first in Europe and the second in the world after the US Constitution. No stronger claim will be made on screen.
3. "Limit the power of the nobility" is a simplification. The constitution abolished the *liberum veto* and confederations, and removed landless nobles from the sejmiks. On-screen text will name these concrete measures rather than repeat the generalisation.
4. "Secure diplomatic backing from European powers" is hypothetical. A documented hook exists: the Polish–Prussian alliance of 1790, which Prussia did not honour in 1792. This could be shown as a labelled documented fact inside the hypothetical section.

## 4. Map accuracy rules for this film

* **Historical maps** use only the verified stages (pre-1772, 1773–1793, 1793–1795, 1795).
* **The surviving Commonwealth in the alternate timeline is shown with its 1791 borders** (after the First Partition, Courland as a fief), because the alternate timeline starts in 1791. The pre-1772 outline is never presented as the surviving state.
* **No invented borders.** For 19th-century or present-day speculation, I recommend the 1791 outline overlaid on a neutral modern Europe, labelled "illustrative: 1791 borders" (to confirm at the storyboard stage).
* Every hypothetical scene carries a persistent **HYPOTHETICAL** marker with a consistent visual code: gold, dashed lines. Documented scenes use solid lines and an ivory **DOCUMENTED** marker.

## 5. Missing assets and technical issues

| Item | Status |
|---|---|
| English ElevenLabs voice-over | ✅ received 20 Nov 2026 |
| Paintings for documented sections (Constitution 1791, Stanisław August, Catherine II, Frederick William II, Francis II, Kościuszko, *The Troelfth Cake*, Rizzi-Zannoni 1772 map) | ✅ available (public domain, sources recorded) |
| Images for the hypothetical 19th-century section (Napoleon, Warsaw and Vilnius city views, 1848, industry) | ⚠️ **not yet sourced.** Wikimedia Commons returns HTTP 429 from this environment and Polona is blocked. The Library of Congress is reachable and will be the primary source. |
| Background music | ⚠️ no licensed music in the repository. Plan: an original score composed for this film (the previous project's `compose_score.py` approach), mixed at −18 to −22 dB under the voice with ducking. |
| Concept previews | Silent design samples (about 11 s each). Sound and narration come in production. |
