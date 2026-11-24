# Poland's Borders 1772–1938 — paper-relief TikTok video

Source for a 3:53 vertical (1080×1920) video in paper-relief map style.

Pipeline (run from `src/`, with `../cshapes/gw.topojson`, `../data/world_1700.geojson`, `../fonts/`, `../voice/` present):

1. `python3 states.py` – renders the layered-paper master map for each border state (CShapes 2.0 data + hand-drawn partition lines).
2. `python3 tts.py` – narration with Piper (`en_US-ryan-high`).
3. `python3 audio.py` – mixes narration, generated music and paper SFX.
4. `python3 render.py range <a> <b> <out.mp4>` – renders frames (camera, drop-in pieces, arrows, labels, captions).

Data: CShapes 2.0 (Weidmann, Schvitz, Girardin), aourednik/historical-basemaps (1700 Commonwealth outline). 1772/1793/1795 partition lines are hand-built approximations of the treaty boundaries.
The rendered MP4 (~156 MB) is not committed because it exceeds GitHub's 100 MB file limit.
