# SirHistora — Vietnam Presentation (TikTok video source)

A vertical TikTok-style video (1080x1920, 30 fps, ~3:20) of a PowerPoint-style Vietnam history presentation with Morph-like transitions, filmed on a monitor in a dark room. No voice-over.

- `video.html` — the whole video: room scene, monitor, slides and the morph engine. `window.render(t)` draws time `t`.
- `render.js <from> <to> <out.mp4>` — renders a fraction of the timeline with Playwright and pipes frames into ffmpeg.
- `preview.js slides` — screenshots one still per slide into `prev/`.
- `times.js` — prints transition times (used to place the whoosh sounds).
- `assets/` — public-domain photos (Library of Congress, Wikimedia Commons) and generated textures.

Rebuild: `npm install`, render four chunks in parallel (`node render.js 0 0.25 parts/p0.mp4`, ...), then concatenate with ffmpeg and add audio.
