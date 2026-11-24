# Analysis of the reference video

**File:** 50 s, 720×1280 (9:16), 30 fps, with an audio track that plays throughout (music or voiceover; I could only measure its level).

**Story (timeline shape):**

1. **0–2 s hook.** A centred serif line over a globe: *"Pangaea wasn't the first. Or the last."*
2. **Past.** A big serif counter ticks through time: 1.6 billion years ago (Nuna), 1.0 billion years ago (Rodinia), 567 million years ago (Pannotia?, flagged as debated), 306 to 252 million years ago (Pangaea).
3. **Mechanism.** *"Heat builds underneath until it cracks"* shows orange mantle-heat glows. At **Today**, glowing orange subduction lines appear with *"Old seafloor sinks at trenches and drags the land back together."*
4. **Future.** *"The next one: in about 200 million years"* shows Amasia.
5. **Opinion, clearly labelled.** *"My bet: the Pacific closes."* Probability bars follow: 60% / 30% / 10%, with a chip saying "… CALL · NOT A FORECAST".
6. **Reflective close.** *"And then it splits again. Will we see it? Not us. Maybe whoever we become."*

**Visual language:**
- **Background:** near-black, with a realistic relief globe and a blue atmosphere rim glow.
- **Header (top left):**
  - a small uppercase sans kicker: "THE SUPERCONTINENT CYCLE"
  - a big serif number plus a smaller unit: "**1.4** billion years ago"
  - pill chips for the source and its status: "PLATE MODEL · MÜLLER ET AL. 2025", "DEBATED", "PROJECTION · MODEL MAP"
- **Captions:** one italic serif line, centred above the globe.
- **Names on the globe:** letter-spaced capitals placed on the landmasses (NUNA, RODINIA, PANGAEA, AMASIA).
- **Scrubber:** a timeline overlaid on the lower globe, with nodes NUNA · RODINIA · PANNOTIA? · PANGAEA · NEXT and a moving triangle playhead.
- **Honesty devices:** "?" after contested names, source chips, and a label that marks opinion as opinion.

---

# Reusable prompt

Paste this and fill in the brackets:

```
Make a [DURATION]-second vertical 3D animation (1080x1920) as one HTML file with three.js, and render it to MP4.
Topic: [TOPIC, e.g. "how a lithium-ion battery charges" / "how the Moon formed"].
Story shape: [mechanism: wide shot → fly in → casing fades to a cutaway showing it working | timeline: one hero object morphing through dated states].

Style:
- Near-black background, one realistic hero object with a soft rim glow.
- Top left: small uppercase kicker "[SERIES TITLE]". Below it, a big serif number with a smaller unit that tweens between beats.
- Pill chips under the headline for the source ("MODEL · AUTHOR YEAR") and the status ("DEBATED", "PROJECTION", "MY CALL · NOT A FORECAST").
- One italic serif caption per beat, under 9 words, with one key word in a blue box.
- Thin leader-line labels for the key parts. Names placed on the object in spaced capitals. A timeline scrubber with a moving playhead if the story spans time.
- Glowing additive effects for energy and flow.

Beats: open with a 2-second surprising hook, use one idea per beat, and end on a reflective line rather than a summary.
Real facts only. Mark anything uncertain with "?" or a chip, and mark opinion as opinion.
Keep text out of the top 100 px and bottom 180 px.
```

To use the skill instead, say: **"Use the science-short skill: [topic], [duration]s."**
