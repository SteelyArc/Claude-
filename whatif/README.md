# What if Poland-Lithuania had never been partitioned? – vertical documentary

1080 × 1920, 30 fps, H.264/AAC, synchronised to the untouched ElevenLabs narration (298.84 s).

| Path | Contents |
|---|---|
| `audio/narration_original.mp3` | Original narration (master timeline, never modified). MD5 3343581c… |
| `research/PHASE1_REPORT.md` | Project inspection, voice-over analysis, fact-check, map rules, missing assets |
| `research/transcript_words.json` | Word-level timestamps (faster-whisper medium.en) |
| `previews/concepts/` | Four concept sample videos, stills, overview sheet, `CONCEPTS.md` |
| `tools/core.py` | Motion engine: 2.5D map camera, geodata to paths, typography, post-processing, H.264 writer |
| `tools/concept*.py` | The four concept samples |
| `tools/build_relief.py`, `tools/depth.py`, `tools/transcribe.py` | Relief raster, painting depth maps, transcript |
| `data/layers.pkl` | Verified political layers 1772–1795 (inherited; see `data/BORDER_VERIFICATION_inherited.md`) |

Rebuild: `python3 tools/build_relief.py && HF_HUB_DISABLE_XET=1 python3 tools/depth.py assets/images/<painting>` then `cd tools && python3 concept1_atlas.py` (and so on).
Dependencies: skia-python, shapely, pyproj, opencv-python-headless, scipy, torch, transformers, faster-whisper, ffmpeg.
