# How a Nuclear Submarine Works: pixel-art 3D TikTok video (5:00, 1080x1920)

Final video: `../output/nuclear_submarine_pixel3d_tiktok.mp4`

How it was made:
1. `build/script.json`: the narration script (52 lines; words in `*stars*` are highlighted in the captions).
2. `build/tts.py`: generates the voiceover with Piper TTS (en_US-ryan-high).
3. `build/timeline.py`: spaces the lines out to exactly 300 s and writes `web/timeline.json`.
4. `web/main.js`: a three.js scene engine. It renders at 270x480, upscales 4x with nearest-neighbour (the pixel look) and draws captions, labels and HUD on top.
5. `build/render.js`: renders every frame headlessly with Playwright (`npm i three@0.170.0 @fontsource/silkscreen @fontsource/press-start-2p` in `web/`, serve `web/` on :8123).
6. `build/audio.py`: procedural chiptune score, sound effects and the voice mix. Then ffmpeg muxes it all with loudness set to -14 LUFS.
