# SirHistora — The Fall of the Polish–Lithuanian Commonwealth

Vertical (1080x1920) animated-map history video, ~6:40, no voice-over yet.

- `video.html` — scenes (`SC` list: camera, map layers, labels, arrows, banners, captions). `window.render(t)` draws time `t`.
- `render.js <from> <to> <out.mp4>` — renders part of the timeline with Playwright → ffmpeg.
- `narration_script.txt` / `script.srt` — timed captions to read the narration from.
- `geo/build_geo.py` — builds `geodata.js` from aourednik/historical-basemaps + Natural Earth; `geo/terrain.py` builds the relief base map.
- Images: Library of Congress (public domain).

To sync to a voice-over: set each scene's `hold` in `video.html` to the length of its narration line, re-render, and mux the audio.
