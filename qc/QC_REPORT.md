# Technical Quality-Control Report – Final Film

File: `output/West_Prussia_TikTok_1080x1920.mp4` (282 MB, not stored in git – exceeds GitHub's 100 MB limit)

| Check | Result |
|---|---|
| Resolution / aspect | 1080 × 1920, 9:16 ✔ |
| Frame rate | 30/1 constant (r_frame_rate = avg_frame_rate) ✔ |
| Video codec / pixel format | H.264 High, yuv420p, CRF 18 (~6.6 Mbit/s) ✔ |
| Audio | AAC stereo 44.1 kHz (narration's native rate – no resampling) ✔ |
| Duration | 329.4 s = narration 325.88 s + approved 3.5 s end-card tail ✔ |
| Black frames (blackdetect d≥0.1 s) | none (only the intended final fade) ✔ |
| Frozen frames (freezedetect ≥2.5 s) | none ✔ |
| Loudness | −15.1 LUFS integrated, LRA 3.1 LU, true peak −1.4 dBTP ✔ |
| Narration | Complete, unedited, original timing (no stretch/pitch/cuts); uniform gain +3.5 dB; look-ahead peak limiter on rare transients (max 3.6 dB) |
| Background music | Removed at producer's request; subtle generated sound design only |
| Text safe zones | All text inside x 60–930 / y 220–1560 (title zone 220–560, captions ≤ 1560); auto-fit for titles/captions |
| Full visual review | Every 1.5 s across the whole film (`qc/sheet_01–10.png`); issues found in the first pass were fixed and re-checked |

## Content checks
- Map borders: OpenHistoricalMap (CC0), 71 point-in-territory tests, 0 failures (`research/map_validation.md`).
- Dates and figures: `research/historical_timeline.md` (sourced). Uncertain figures shown as estimates.
- Narration error at 4:55 ("divided between Poland and Germany") corrected on screen: "The former province lies entirely within Poland".
- Images: all Library of Congress, rights statements recorded in `assets/images/SOURCES.csv`; no AI-generated or fabricated images.
- Scenes without location-verified, licence-clear photographs (1939 crimes, 1945 flight) use map animation and sourced text instead.
