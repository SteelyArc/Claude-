# Four visual concepts – preview samples

Each sample is a real render from the production engine: 1080 × 1920, 30 fps, H.264. Samples are 11–11.5 s long and silent. They use the verified border data and genuine historical paintings. Stills from each sample are saved next to the videos.

All four share one rule: **documented history = solid lines and an ivory "DOCUMENTED" marker; hypothetical = dashed gold lines and a gold "HYPOTHETICAL" marker.** In the alternate timeline the Commonwealth always keeps its **1791 borders**.

---

## Concept 1 – Cinematic Historical Atlas ("Night Atlas")
`concept1_cinematic_atlas.mp4`

**Design language.** A dark relief map rendered from real elevation data (Carpathians, coastlines and river valleys picked out by low raking light). States are drawn as luminous tinted glass over the terrain. Borders are traced by a moving point of gold light. Type is engraved-style Cinzel and Cormorant with an editorial sans for status chips.

**Camera and transitions.** The opening move swoops down from a low, tilted 2.5D angle over Warsaw and pulls back to the full Commonwealth while the camera rolls level. Annexations spread outward from the annexing power's side, with a bright "ink front". A mechanical roll counter moves 1772 → 1793 → 1795. After 1795 a dashed ghost outline remains, then the 1791 state re-ignites outward from Warsaw in gold.

**With the narration.** This is the backbone for every geographic sentence: 0:32 "one of Europe's largest states", the 1793 and 1795 partitions, and 2:34 "Poland-Lithuania remains on the map". Camera beats land on key words ("Russia", "Prussia", "Austria", the dates).

**Eye-catching.** A cinematic 3D map in place of a flat diagram, real terrain, light that literally draws history, and a strong first 3 seconds (light-traced border plus title).

---

## Concept 2 – Living History (cinematic 2.5D)
`concept2_living_history.mp4`

**Design language.** Genuine paintings re-photographed by a virtual camera. Per-pixel depth maps (AI depth estimation) let near figures move against the background with real parallax. A rack focus guides the eye, volumetric light falls through the hall windows, dust drifts in depth of field, and candlelight flickers subtly. The grade is warm and filmic, with teal shadows and amber highlights. Lower thirds use a thin gold rule, a serif title and a full painting credit.

**Camera and transitions.** A lateral dolly and push-in through Wojniakowski's *Passing of the Constitution of 3 May 1791* (1806). A "light-burn" transition (a warm flare sweeps and the exposure blooms) leads into Bacciarelli's coronation portrait of Stanisław August (1764). There the camera travels from the full figure to his face as the focus pulls from the background onto the king.

**With the narration.** The human moments: 1:10 the Constitution, the king and the reformers, Catherine II at 1:32 ("Russia intervened"), Targowica, and Kościuszko. It carries the emotional weight of the film.

**Eye-catching.** Paintings feel like film footage without being altered or cartoonish: no invented faces, no AI-generated imagery, only camera, light and depth.

---

## Concept 3 – The Animated Timeline
`concept3_animated_timeline.mp4`

**Design language.** A clean "museum wall" or editorial look: bone-white ground, black ink, one crimson accent for the Commonwealth. Swiss-grid sans typography is paired with large serif dates, and giant outline numerals drift behind with parallax. Paintings and prints arrive as physical cards with real shadows. Mini-maps show the territory at each date.

**Camera and transitions.** The camera glides down a slightly tilted 2.5D timeline. Each date is drawn in as the camera reaches it. **At 1791 the line forks**: a solid black "Our timeline" branch (1792 Russia invades → 1793 → 1795 the state disappears) and a dashed gold "Alternate timeline" branch (1792 reforms hold → 1795 no partition), each marked HYPOTHETICAL. The sample ends by pulling back to show both branches with a legend.

**With the narration.** Best for 0:32–2:42, where the script is a sequence of dates, and as a recurring "chapter navigator" between sections.

**Eye-catching.** It is instantly readable on a phone, the fork makes the "what if" idea visual in a single image, and its bright look stands out in a dark TikTok feed.

---

## Concept 4 – The Two Timelines (split screen)
`concept4_two_timelines.mp4`

**Design language.** A broadcast or data-journalism style: flat vector maps on graphite, crisp hairlines, bold sans captions. **Top = OUR HISTORY · DOCUMENTED** in cool, desaturated tones. **Bottom = ALTERNATE TIMELINE · HYPOTHETICAL** in warm gold with dashed borders. A year pill rides the seam between them.

**Camera and transitions.** The hook ("ONE STATE.") shows a single 1791 map, then a scan line cuts it and the two halves slide apart ("TWO FUTURES."). Year by year the panels diverge. In 1792 Russian invasion arrows (schematic) cross the border on top and are stopped at the frontier below. In 1793 and 1795 the top panel is partitioned while the bottom holds. Finally the top panel wipes away and the hypothetical Commonwealth takes over the frame ("still on the map").

**With the narration.** It carries the core "what if" contrast, 1:32–2:42, where the script itself alternates between "in our timeline…" and "in this alternative timeline…". It returns at 4:25–4:58 for the closing comparison.

**Eye-catching.** It holds attention through direct comparison, and the real/hypothetical split can never be misread.

---

## Version 2: quality upgrade (applies to all four)

**Engine**
- **Real motion blur**: every frame averages 3–6 sub-frames over a 180° shutter, like a film camera. Camera moves and type animation no longer step.
- **Filmic finishing**: halation (warm glow around highlights), multi-radius bloom, lens chromatic aberration, a soft highlight shoulder, and tilt-shift depth of field on tilted maps.
- **Grain** at full resolution on luminance only. It also dithers the 8-bit output, so the dark gradients no longer band.
- x264 `-tune film` at CRF 16; parallel rendering on 4 cores.

**Concept 1 – Atlas**
- Relief at 340 m/px (the native resolution of the elevation tiles), with fine ridge shading plus broad landform shading.
- Sea-depth gradient with engraved coastal contour lines; glowing rivers.
- The camera descends through two parallax cloud layers in the hook, with a gentle "operated camera" drift.
- **Partitions as physical plates**: each annexed territory lifts out of the map, leaving a shadowed void, drifts toward the annexing power, takes on its colour and drops back into place.
- Metallic gold title type with a moving specular highlight. The light tracing the border has a glowing pen tip. Cities pulse.
- A focus falloff fades the world into darkness away from the Commonwealth. Russia's display shape continues east of the 42°E data window.

**Concept 2 – Living History**
- Lanczos upscaling, gentle local-contrast enhancement and sharpening of the paintings.
- Two-level lens blur for smooth bokeh, and atmospheric haze by depth.
- **Light shafts masked by depth**: they pass behind the foreground crowd instead of lying flat on top.
- Handheld camera drift, and an anamorphic lens streak in the light-burn transition.

**Concept 3 – Timeline**
- Paper texture tied to the wall, so it travels with the camera, plus soft moving window light.
- Cards swing in with true 3D perspective, with separate contact and ambient shadows.
- Mini-maps appear with an organic ink-bleed reveal.

**Concept 4 – Two Timelines**
- Terrain relief under the flat vector maps, and a focus falloff.
- A glowing seam with a lens flare at the year pill.
- Campaign arrows with particles flowing along them, and a light-wipe takeover at the end.

---

## Recommendation
For a premium film, **combine them, with one as the master look**: Concept 1 as the cartographic backbone, Concept 2 for people and paintings, and Concept 4 for the real-versus-alternate comparison. Concept 3 would serve as the chapter navigator, restyled dark to match. These four samples are deliberately pure so you can judge each language on its own.
