# Production: The Second and Third Partitions of Poland-Lithuania (1793–1795)

A vertical (1080×1920, 30 fps) historical documentary, synchronised to the finished ElevenLabs narration.

| Path | Contents |
|---|---|
| `audio/narration_original.mp3` | The untouched narration (418.93 s) |
| `research/PHASE1_REPORT.md` | Project inspection, fact-check, storyboard, asset shortlist |
| `research/BORDER_VERIFICATION.md` | How every border was sourced, checked and corrected; uncertainties |
| `research/transcript_words.json` | Word-level timing (faster-whisper medium.en) |
| `research/commons_candidates.json` | Wikimedia Commons candidates with licence and author |
| `previews/maps/` | Phase 2 approval stills (six map stages) |
| `tools/` | Pipeline scripts |
| `assets/fonts/` | Cormorant Garamond, Cinzel, EB Garamond (SIL OFL) |

## Rebuild

```bash
# 1. fetch OHM relations into data/ohm/<id>.json (Overpass `rel(<id>);out geom;`), Natural Earth into data/ne/
python3 tools/ohm_assemble.py data/ohm data/geo
python3 tools/digitise_1793_line.py          # needs research/diagnostics/ref_rozbiory3.png
python3 tools/digitise_zone.py 190,149,145 ref_russia_gain_1772 800,250,1450,1060
python3 tools/build_corrected.py
python3 tools/prep_layers.py                 # -> data/layers.pkl
python3 tools/render_map_previews.py         # -> previews/maps/*.png
```
