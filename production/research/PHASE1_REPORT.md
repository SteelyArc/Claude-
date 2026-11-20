# Phase 1 — Research report and storyboard

*The Second and Third Partitions of Poland-Lithuania (1793–1795)*, TikTok vertical edition

## 1. Project inspection

* **Repository:** it contained only `README.md`. There were no earlier scripts or automation to reuse. Everything new is under `production/`, and no existing file was changed.
* **Narration:** `ElevenLabs_2026-11-20T08_11_42_Charles_-_Social_Media_TV__Commercial__pvc_s50_sim75_v4.mp3`, copied unchanged to `production/audio/narration_original.mp3` (the SHA-256 matches the upload).
  * **Duration: 418.93 s (6 min 58.9 s)**, under the 10-minute limit.
  * MP3, 44.1 kHz, mono, 128 kb/s.
* **Tools available or installed:** ffmpeg 6.1, Python 3.13, skia-python (vector renderer), shapely/pyproj (GIS), faster-whisper (word-level timing), Pillow/NumPy, ImageMagick, Node 22, and headless Chromium.
* **Network:** Wikimedia upload host ✓ (the Commons API is rate-limited to about one call per minute); OpenHistoricalMap Overpass ✓; GitHub raw (Natural Earth, Google Fonts) ✓; en/pl/de Wikipedia raw ✓. Blocked: ru/be Wikipedia, Wikidata, UT Austin map library, Polona, David Rumsey, Nominatim.

## 2. Narration transcript and timing

The full word-level transcript is in `transcript_words.json`. Whisper skipped 105–111 s; that slice was transcribed separately: *"…formed the Targowica Confederation in 1792. Russia soon intervened militarily."*

## 3. Fact-check of the narration

The narration is not changed. Where its wording is loose, the on-screen text will be precise.

| Time | Claim | Verdict |
|---|---|---|
| 0:00 | First Partition 1772; Austria took part | ✓ |
| 1:10 | Constitution of 3 May 1791, "one of the first modern written constitutions in Europe" | ✓ (usually called the first in Europe and the second in the world) |
| 1:42 | Targowica Confederation 1792, backed by Catherine II | ✓ signed in St Petersburg 27 Apr, proclaimed 14 May 1792 |
| 1:49 | Russia intervened militarily | ✓ invasion began 18 May 1792 |
| 2:01 | The King joined the Targowica Confederation | ✓ 24 July 1792 |
| 2:17 | Second Partition by Russia and Prussia; Austria not involved | ✓ |
| 2:34 | "Prussia seized the region of Greater Poland, **including** Gdańsk and Toruń" | ⚠ Gdańsk and Toruń were in **Royal Prussia**, not Greater Poland. On screen they are labelled separately: *Gdańsk (Danzig), Toruń (Thorn)* and *Greater Poland* |
| 2:44 | Russia took much of present-day Belarus and parts of Ukraine | ✓ |
| 3:05 | Grodno Sejm 1793, under coercion | ✓ treaties with Russia 22 July and with Prussia 25 Sept 1793 |
| 3:37 | Kościuszko served in the American Revolutionary War | ✓ |
| 3:42 | 24 March, uprising proclaimed in Kraków | ✓ Act of Uprising, Kraków Market Square, 24 Mar 1794 |
| 3:58 | Racławice, victory over Russian troops | ✓ 4 April 1794 |
| 4:24 | October 1794, defeated and captured at Maciejowice | ✓ 10 Oct 1794 |
| 4:30 | Warsaw taken by Russian forces | ✓ Praga stormed 4 Nov; Warsaw capitulated 5 Nov 1794 |
| 4:40 | 1795, the three powers agree the Third Partition | ✓ treaties 3 Jan and 24 Oct 1795 |
| 4:56 | Prussia took Warsaw; Austria took Kraków | ✓ |
| 5:14 | Abdication 25 November 1795; taken to Russia | ✓ abdicated at Grodno; moved to St Petersburg in 1797; died there 12 Feb 1798 |
| 5:30–6:59 | Conclusion: people, culture and resistance survive | ✓ consistent with the brief; it does not imply that culture or resistance ended in 1795 |

## 4. Borders

See **BORDER_VERIFICATION.md**. In short: OpenHistoricalMap polygons were checked against a georeferenced atlas reference and against published area figures. Two lines were wrong and were replaced: the **1793 Russian line**, which was off by up to ~80 km, and the 1772 Russian zone. The corrected 1793 Russian gain is 229,194 km² against 228,600 km² published (Roos). All 22 documented towns now fall on the correct side.

## 5. Scene-by-scene storyboard (timed to the narration)

Times are narration seconds. The film runs **≈ 419.5 s** (narration plus a 0.6 s tail), with no cuts or speed changes to the audio.

| # | Time | Narration (abridged) | Visuals |
|---|---|---|---|
| **1 Intro** | 0.0–21.4 | First partition 1772 … continued to exist | Cold open: slow push-in across parchment on the **Cary 1799 period map** (PD), with 2.5D parallax. Title card *"The Partitions of Poland-Lithuania · 1793–1795"*. Dissolve into **Map 1 (1773)** |
| | 21.4–48.8 | Russia and Prussia saw an opportunity; Austria … the 1790s | Map 1 animated: hatched 1772 losses flash in each power's colour; labels for the three powers fade in one by one; camera drifts east to west |
| **2 Crisis** | 48.9–70.0 | Weak government, foreign influence, reformers | Bellotto's *View of Warsaw from the Royal Castle* (1773, PD) with parallax and fog layers; on-screen keywords *"weak government · foreign influence · no standing army"* in engraved type |
| | 70.0–96.3 | 3 May 1791 constitution | Date card **3 May 1791**; Matejko's *Constitution of 3 May 1791* (1891, PD), slow pan; document animation: title-page facsimile of the *Ustawa Rządowa* (to be sourced) unrolls with a highlight sweep. **Map 2** with the Warsaw marker |
| | 96.3–110.6 | Opponents … Catherine II … Targowica 1792 | **Portrait: Catherine II** (Lampi, 1793, Hermitage, PD) in a gilt frame with name and dates *"Catherine II · Empress of Russia 1762–1796"*; caption *"Confederation of Targowica · signed in St Petersburg, 27 April 1792"* |
| | 110.6–137.4 | Russian forces enter; the King joins Targowica | Map 2: Russian frontier glows; date card *18 May 1792*. **Portrait: Stanisław August Poniatowski** (Bacciarelli, MNW, PD) with *"King of Poland 1764–1795"* and a date stamp *24 July 1792: joins Targowica*. Shot ends on the line "Russia was not finished" over the darkening map |
| **3 Second Partition** | 137.4–148.4 | 1793, Russia and Prussia; Austria not involved | **Portrait pair**, split frame: Catherine II and **Frederick William II** (Anton Graff, PD). Austria's border dims with the caption *"Austria: not a party in 1793"* |
| | 148.9–175.0 | Prussia: Greater Poland, Gdańsk, Toruń; Russia: Belarus, Ukraine | **Map 3 animated**: hatched Prussian gain sweeps in (camera flies to Gdańsk and Toruń; city cards *Gdańsk (Danzig)*, *Toruń (Thorn)*); then the Russian gain sweeps east to west; area counters *≈58,000 km²* and *≈230,000 km²* (sourced) |
| | 175.0–206.1 | Reduced state; Grodno Sejm | Pull back to the rump state; old border dashed. Grodno marker; caption *"Grodno Sejm · 1793 · treaty with Russia 22 July, with Prussia 25 September"*; **Laurie & Whittle 1794** period map (PD) slides in as a layered plate with parallax |
| **4/5 Uprising** | 206.1–222.1 | Resistance; Kościuszko, American war | **Portrait: Tadeusz Kościuszko** (Josef Grassi, 1792–93, PD) with a name card. Short caption *"Served in the Continental Army 1776–1783"* |
| | 222.1–233.0 | 24 March, Kraków | **Map 4**: marker 1, Kraków; Smuglewicz's *Kościuszko's Oath on the Kraków Market Square* (1797, PD) with parallax (foreground crowd / background) |
| | 233.0–249.2 | Racławice victory | Map 4: marker 2; Matejko's *Kościuszko at Racławice* (1888, PD), slow pan |
| | 249.6–263.6 | Russia and Prussia join forces | Map 4: Warsaw (3), Wilno (4), Szczekociny (5); **no troop routes**; Prussian and Russian borders pulse; caption *"Siege of Warsaw, 13 July – 6 Sept 1794"* |
| | 263.9–280.0 | Maciejowice; Warsaw falls | Marker 6; Plersch's *Kościuszko in the Battle of Maciejowice* (c. 1794–1810s, PD); marker 7 *Praga, 4 Nov 1794*; desaturate to sepia |
| **6 Third Partition** | 280.0–313.4 | 1795 final division: Russia east, Prussia west incl. Warsaw, Austria south incl. Kraków | **Map 5, step by step**: the Russian share sweeps in, then Prussia (camera to Warsaw), then Austria (camera to Kraków and Lublin); add **portrait: Francis II** (1792, PD) for Austria. Treaty-date cards *3 Jan 1795 · 24 Oct 1795* |
| **7 End** | 314.3–329.4 | Abdication 25 Nov 1795; to Russia | **Bacciarelli** portrait reprised and desaturated; document card *"Abdication · Grodno · 25 November 1795"*; the Commonwealth's gold fill drains from the map |
| **8 Conclusion** | 329.9–386.0 | People, languages and cultures endure; 19th-century uprisings | Reflective montage: **Map 6** slowly rotates in 2.5D; muted plates of period maps; captions *1830 · 1863 uprisings* only where the narration names them in general terms |
| | 386.0–418.9 | 1772, 1793, 1795 … the idea survived | **Map 6 final**: three tonal steps per empire appear in sequence 1772 → 1793 → 1795; the gold 1772 outline glows on top; fade to parchment and the title *"Poland-Lithuania · 1569–1795"* |

The brief's Scene 4 (historical figures) is woven through the narration where each person is named. No portrait appears without a name card, and every portrait is a period or near-period work by a named painter.

## 6. Archival material shortlist

All files below are on Wikimedia Commons and **public domain** unless stated otherwise. Full records are in `research/commons_candidates.json`.

* Catherine II: *Catherine II by J.B.Lampi (1793, Hermitage).jpg*
* Frederick William II: *Anton Graff – Frederick William II of Prussia.png*
* Stanisław August: *Marcello Bacciarelli – Portrait of Stanisław August Poniatowski with hourglass – MNW*
* Kościuszko: *Tadeusz Kościuszko (1793, Joseph Grassi).jpg*
* Francis II: *Christian Wilhelm Ketterlinus, Francis II, 1792, NGA* (CC0)
* Paintings: Smuglewicz, *Oath on the Kraków Market Square* (1797); Matejko, *Constitution of 3 May 1791* (1891); Matejko, *Kościuszko at Racławice* (1888); Plersch, *Kościuszko in the Battle of Maciejowice*; Bellotto, *View of Warsaw from the Royal Castle* (1773)
* Period maps: Laurie & Whittle 1794 (after the Second Partition); John Cary, *A New Map of Poland … Dismemberments 1772, 1793 and 1795*
* Still to source in Phase 3: a facsimile of the Constitution document, the 1794 Act of Uprising, Orłowski's or Norblin's 1794 Warsaw scenes, and an engraving of the Grodno Sejm (searches so far returned nothing usable)

Matejko's paintings (1866–1891) are **19th-century history paintings**, not eyewitness images, and will be captioned with painter and year. No AI-generated imagery will be used anywhere.

## 7. Technical plan for the final render

* 1080×1920, 30 fps, H.264 High (CRF ~18 with maxrate 6.5 Mb/s), AAC 192 kb/s, MP4 with faststart. At 419.5 s the estimated size is **≈ 300–360 MB**, under the 400 MB cap; the encoder will be capped so the file cannot exceed it.
* Music: a restrained, royalty-free bed, ducked to about −22 dB under the voice with side-chain compression. One option is a public-domain recording of Ogiński's polonaise *Farewell to the Homeland* (composed 1794), if a properly licensed recording can be found; otherwise an original ambient score synthesised in the pipeline. **This is your call at Phase 3.**
* QC: ffprobe checks for resolution, fps, codec, duration and size; the audio track is checksum-compared against the untouched narration decode; contact sheets of every scene.
