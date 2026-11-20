# The First Partition of Poland–Lithuania (1772): vertical documentary

A 1080 × 1920 documentary for TikTok, with 8 min 46 s of narration. This folder holds the cartographic data pipeline, the animation engine and the **visual-quality preview** (≈ 2 min 27 s) that comes before full production.

## Pipeline

| Step | File | What it does |
|---|---|---|
| 1 | `src/build_geo.py` | Assembles OpenHistoricalMap relations into polygons |
| 2 | `src/prep_geo.py` | Builds the 1772 layer set in a Lambert azimuthal **equal-area** projection centred on 52° N 22° E: the Commonwealth before and after, the three acquisitions, the new 1772 borders, the neighbours, rivers and cities |
| 3 | `src/base.py` | Pre-renders the atlas base at two levels (Europe and Commonwealth): hill-shaded relief from Terrarium DEM tiles, parchment land tone, engraved coastal water lines, graticule |
| 4 | `src/engine.py` | Skia-based motion engine. It provides a camera with log-space zoom and true perspective tilt (2.5D), ink-spread reveal masks for territories, border drawing along the real path with a pen tip, flowing rivers, and typography with per-letter reveals. A finishing pass adds paper grain, film grain, a breathing key light, a vignette and parallax dust |
| 5 | `src/scenes.py` | Scene direction, keyed to the narration's word timestamps (`data/transcript.json`) |
| 6 | `src/render.py` | Renders frames, applies a colour grade and pipes them to H.264 |
| 7 | `work/build_audio.sh` | Cuts the preview's narration track |

## Historical-geography sources and accuracy decisions

- **Commonwealth before and after 1772:** OpenHistoricalMap (CC0) relations *Poland-Lithuania 1686–1773* and *1773–1793*. OHM dates the change to the Sejm ratification of 18 September 1773; the conventions were signed on 5 August 1772.
- **Prussian acquisition:** the intersection with OHM *Kingdom of Prussia 1772–1791*. It covers Royal Prussia, Warmia (Ermland) and the Netze District. **Danzig and Thorn stay with the Commonwealth.**
- **Austrian acquisition:** the intersection with OHM *Kingdom of Galicia and Lodomeria 1772–1786*. Kraków stays with the Commonwealth.
- **Russian acquisition (corrected):** OHM wrongly puts the Nevel, Sebezh and Velizh districts, and strips of the eastern frontier, in Russia *before* 1772. English Wikipedia confirms that Velizh and Sebezh were Commonwealth towns until the First Partition. I restored them using the 1897 Vitebsk and Mogilev district boundaries from **RISTAT** (Kessler & Markevich, *Electronic Repository of Russian Historical Statistics*, CC0). Those districts were formed entirely from Commonwealth land, so their outer edge preserves the pre-1772 state frontier. The correction added ≈ 18,000 km².
- **Area check** against commonly cited figures (land area measured on the WGS84 ellipsoid):

| Power | This map | Published |
|---|---|---|
| Russia | 89,400 km² | ≈ 92,000 km² |
| Austria | 82,900 km² | ≈ 83,000 km² |
| Prussia | 38,300 km² | ≈ 36,000 km² |

  On-screen statistics use the published figures, marked as estimates.
- **Duchy of Courland** is shown hatched as a Polish fief, not as core territory.
- **Neighbours in 1772:** OHM Prussia, Russia, Ottoman Empire, Crimean Khanate, Sweden and Holy Roman Empire. The Habsburg Monarchy is the union of Bohemia, the Austrian Circle, Hungary, Transylvania and the Banat of Temesvar. No 19th-century borders are used for 1772.

### Remaining uncertainty

- The Netze District line and the exact course of the Russian line between the Dvina and the Drut follow OHM. They agree with standard atlases at the scale shown, but I could not check them against a primary 1772–73 boundary survey.
- The pre-1772 frontier near Nevel, Sebezh and Velizh is reconstructed from 1897 district boundaries. Their outer edge is the old state border, but local adjustments made between 1772 and 1897 cannot be ruled out.
- Small Spisz enclaves (the towns pledged to Hungary in 1412) follow OHM detail.

## Authentic visual material (Wikimedia Commons, public domain)

- Catherine II, after Alexander Roslin, 1780s. Kunsthistorisches Museum, Vienna (GG 7131).
- Frederick II, by Johann Georg Ziesenis, 1763. Sanssouci Palace, Potsdam (SPSG).
- Maria Theresa, by Martin van Meytens, 1759. Academy of Fine Arts, Vienna (GG-103).
- Stanisław August Poniatowski in coronation robes, by Marcello Bacciarelli, 1764. Royal Castle, Warsaw.
- Prince Henry of Prussia, by J. H. W. Tischbein, 1769. Wenzel Anton von Kaunitz, by Jean-Étienne Liotard.
- *The Troelfth Cake / Le Gâteau des Rois*, engraving by Noël Le Mire after Jean-Michel Moreau, 1773.
- *Picture of Europe for July 1772*, an anonymous British satirical print.
- *A new map of the Kingdom of Poland with its dismembered provinces*, by Robert Sayer, 1787 (via Polona).
- Jan Matejko, *Rejtan*, 1866. This is a 19th-century painting and will be labelled as such.

No portrait, document or quotation is generated or invented.

## Subtitles

Subtitles are burned into the video by `src/subtitles.py`:

- **Timing:** word-timed cues taken from the narration transcript.
- **Line breaks:** phrase-aware, at most 34 characters per line. The breaker never splits names such as "Catherine II" or "East Prussia".
- **Style:** EB Garamond on a translucent dark plate. Spoken words brighten as the narrator reads them.
- **Position:** centred at y ≈ 1468 px, inside TikTok's safe area (above the caption and music strip, clear of the right-hand icon rail). Cards and title blocks were moved above this band.
- **Text corrections to the automatic transcript:**
  - Thorne → Thorn, royal Prussia → Royal Prussia, Habsburg monarchy → Habsburg Monarchy, the same → the Sejm, Liberum Vito → Liberum Veto.
  - British spelling throughout.
  - The dropped words "its territory" at 0:25 were restored after a second, larger model confirmed them.
- **Separate file:** `render/partition1772_preview.srt` holds the same cues for platforms where you upload captions yourself.

## Colour system (consistent throughout)

| Territory | Colour | Treatment |
|---|---|---|
| Commonwealth | golden beige | Solid fill |
| Prussia | desaturated blue | Home territory: light wash with a coloured frontier band |
| Russia | terracotta | Same as Prussia |
| Habsburg Monarchy | ochre | Same as Prussia |
| 1772 acquisitions | the acquiring power's colour | Solid fill with fine hatching |
| Neutral neighbours | pale grey-green | Light wash |
