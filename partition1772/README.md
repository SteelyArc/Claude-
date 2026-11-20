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
- **Croatia (checked on review):** in 1772 Croatia was **Habsburg**, not Ottoman. The Kingdom of Croatia, Slavonia and the Croatian and Slavonian Military Frontier came under Habsburg rule after the treaties of 1699 and 1718; Ottoman rule ended at the Una and Sava rivers. OHM has Slavonia and parts of the Military Frontier but no complete Croatia polygon for 1772. I therefore took the land between the mapped 1772 neighbours (Ottoman Bosnia, the Republic of Venice's Dalmatia, Ragusa, Hungary and the Austrian lands) and assigned it to the Habsburg Monarchy, then spot-checked it town by town:
  - Habsburg: Zagreb, Karlovac, Gospić, Senj, Osijek.
  - Ottoman: Bihać, Banja Luka, Sarajevo.
  - Venetian: Split, Zadar, Knin.
  
  Venice and Ragusa are shown as neutral neighbours.

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

## Cold-open hook (first 3.5 s)

- **Frame 1:** the Commonwealth on a tilted map, with the headline "THREE POWERS. ONE COUNTRY." It says "powers" rather than "empires" because Prussia was a kingdom.
- **The cuts:** glowing lines race along the real 1772 partition borders, and the three acquisitions tear away as lifted paper pieces in their power colours.
- **The line:** "Divided not by battle, but by agreement." This is the narration's own point, not an invented quotation.
- **The transition:** the pieces snap back and the camera whips out to Europe.
- **Sound:** subtle synthesised accents (low impact, three slashes, a whoosh) sit under the narration.

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


## Final version (full narration, 8 min 50 s)

`src/film.py` puts the whole film on one narration clock, with designed transitions between chapters (dissolve, dip to black, dip to parchment). `src/render_film.py` renders it in parallel chunks. `work/assemble_film.sh` muxes the video with the soundtrack (narration plus synthesised hook sound design from `src/sfx.py`).

| Time | Chapter | Visual material |
|---|---|---|
| 0:00 | Cold open and the Commonwealth in 1772 | animated map |
| 0:33 | Three questions | *Picture of Europe for July 1772* (British print, 1772) |
| 0:47 | Rewind to 1569 | animated timeline |
| 0:52 | Union of Lublin | 1569 map (OHM), the Crown and Lithuania joining |
| 1:19 | Elected monarchy | J.-P. Norblin (attr.), election field at Wola, c. 1790, Wawel |
| 1:27 | The Sejm | English engraving, 1698, National Library of Poland |
| 1:39 | Liberum veto | animated hemicycle diagram ("Nie pozwalam!") |
| 2:01 | Foreign influence | map with diplomatic and military vectors |
| 2:19 | Augustus III † 1763 | Louis de Silvestre, after 1733, Wilanów |
| 2:25 | Election of 1764 | Bernardo Bellotto, 1778, Royal Castle Warsaw |
| 2:34 | Stanisław August | Marcello Bacciarelli, 1764 |
| 2:49 | Catherine II, Frederick II | portraits |
| 3:03 | 1767: Russian pressure | map, then N. Repnin (anonymous print, 1779, ÖNB) |
| 3:27 | Confederation of Bar (1768–72) | map, Bar, timeline |
| 3:59 | Russo-Turkish War (1768–74) | map, Larga and Kagul 1770 |
| 4:09 | Maria Theresa; the three powers | portraits, triptych |
| 4:22 | Frederick's plan | Royal Prussia gap; cameo of Prince Henry (Tischbein, 1769) |
| 4:49 | Agreement and occupation | map with army vectors; cameo of Kaunitz (Liotard) |
| 5:05 | 5 August 1772 | *Le Gâteau des Rois*, 1773 |
| 5:16 | The three acquisitions | animated partition map |
| 6:13 | Before and after | animated comparison |
| 6:29 | The king, the demand, the Partition Sejm, Rejtan | Bacciarelli; diagram; Jan Matejko, *Rejtan* (1866, labelled as a later painting) |
| 7:01 | 30 September 1773: ratification | map, seal |
| 7:12 | Consequences | West Prussia; Galicia and Lodomeria; Pskov and Mogilev governorates; Kraków and the Vistula border |
| 7:51 | A warning | remaining Commonwealth |
| 8:14 | Constitution of 3 May 1791 | Kazimierz Wojniakowski, 1806, National Museum Warsaw |
| 8:28 | 1793 and 1795 | timeline; the Commonwealth fades (no unverified 1793 lines are drawn) |
| 8:38 | Finale and credits | |

**Why there is no 1793 boundary:** the OHM 1793 geometry gives Russia about 192,000 km² in the Second Partition, against about 250,000 km² in standard references. I therefore don't draw it. The narration only mentions the later partitions, so the film shows them as clearly labelled dates while the remaining Commonwealth fades. They are never mixed up with the borders of 1772.

**Transcript:** the subtitles now use a second, larger-model transcription (medium.en). It recovers the sentence "The experience of 1772 became a warning", which the first pass dropped.
