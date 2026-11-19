# History That Remains – Documentary Production

Vertical (1080×1920, 30 fps) historical documentaries for TikTok.

## Current project: West Prussia – A Region Shaped by History
| Path | Contents |
|---|---|
| `audio/narration_en.mp3` | Finished ElevenLabs narration (master clock, never modified) – 325.88 s |
| `research/phase1_report.md` | Project inspection, narration analysis, accuracy issues, open questions |
| `research/historical_timeline.md` | Verified timeline, place names, sources |
| `research/map_plan.md` | Map list, OpenHistoricalMap relation IDs, validation procedure |
| `research/image_sources.md` | Archival image targets and licence rules |
| `research/narration_transcript.json` | Word-level transcript with timestamps |
| `research/sources/` | Saved source texts (with revision IDs) |
| `storyboard/storyboard.md` | Scene-by-scene storyboard synced to the narration |
| `storyboard/shot_list_final.md` | Final shot list as built |
| `previews/maps/`, `previews/animation/` | Phase 2 map previews, Phase 3 animation preview |
| `qc/QC_REPORT.md` | Final technical QC report + review sheets |
| `engine/` | Reusable engine: geodata, atlas map renderer, photo/document shots, transitions, audio, video, QC |
| `projects/west_prussia/` | This film: relations, territories, maps, film timeline, audio, render scripts |
| `assets/images/SOURCES.csv`, `assets/SOURCES_OTHER.md` | Image and data sources with licences |

Render the film: `python3 projects/west_prussia/audio_film.py build/audio_film.wav && python3 projects/west_prussia/render_film.py`
(output → `output/West_Prussia_TikTok_1080x1920.mp4`, ~27 min on 4 cores).

Workflow: Phase 1 research & storyboard → Phase 2 map previews → Phase 3 animation preview → Phase 4 full production (only after approval).
