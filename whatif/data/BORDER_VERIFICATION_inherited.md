# Border verification — Partitions of Poland-Lithuania

How every territorial boundary in the maps was obtained, checked, and what remains uncertain.

## Sources

| Layer | Source | Licence |
|---|---|---|
| Political polygons (dated) | OpenHistoricalMap relations (see table below) | CC0 |
| Atlas reference used for checking | *Rzeczpospolita Rozbiory 3.png*, Halibutt, Wikimedia Commons (compiled from Polish historical atlases) | CC BY-SA 3.0 (used **only** as a reference; not shown on screen) |
| Area figures | N. Davies, *God's Playground* I (2005), p. 394; H. Roos in *Handbuch der Europäischen Geschichte* 4 (1968), pp. 746–751; J. Jędruch (1998), pp. 186–187 | citation |
| Coastline, rivers, lakes, Latvia/Czechia outlines | Natural Earth 10 m | public domain |
| Event coordinates | English Wikipedia `{{coord}}` templates, OpenHistoricalMap place nodes | — |

**Important caveat:** every OHM boundary used here carries the tag `fixme:s = needs source for boundary lines`. OHM was used only as digitised starting geometry. Each partition stage was then checked against the atlas reference, which was georeferenced with 22 city control points (RMS error 5.6 px ≈ 5 km), and against towns whose year of annexation is documented.

## Results by stage

| Stage | OHM relation(s) | Check result | Action |
|---|---|---|---|
| Commonwealth 1773–93 | 2692511 | Outline matches the reference closely | used as is |
| 1772 Prussian gain | 2748497 − 2748498 | 36,955 km² vs 36,000 published | used |
| 1772 Austrian gain (Galicia) | 2748048 | 82,947 km² vs 83,000 published | used |
| 1772 Russian gain | 2851992 − 2851879 | **Off by 20–40 km** (misses a northern strip of Polish Livonia and cuts a wrong corner near Vitebsk) | **replaced** with the zone digitised from the reference: 85,305 km² (published figures run from about 84,000 to 92,000 km²) |
| 1793 Prussian gain | 2748500 − 2830452 | 56,335 km² vs 58,000–58,400 published | used |
| **1793 Russian line** | 2692510 / 2890609 | **Wrong:** it leaves Pinsk, Nesvizh, Mir, Rivne and Ostroh, all annexed in 1793, inside the rump state, and the rump comes out about 60,000 km² too large | **replaced** with the line digitised from the reference (Druja on the Dvina → west of Minsk and Nesvizh → east of Pinsk → west of Rivne → Galician border near the upper Zbruch). Result: **229,194 km² vs 228,600 km² (Roos)**, within 0.3 % |
| 1795 Prussia (New East Prussia, South Prussia, New Silesia) | 2692579, 2693945, 2693948 | Match the reference | used; Prussian gain 47,108 km² vs ~48,000 |
| 1795 Austria (West Galicia) | 2748050 | Matches the reference | used; 51,072 km² vs ~47,000 |
| 1795 Russia | remainder of the rump | — | 138,257 km² plus Courland 30,189 km² (published about 120,000 + Courland) |

### Town checks for the 1793 line (all now correct)

Annexed by Russia in 1793: Minsk, Pinsk, Slutsk, Nesvizh, Mir, Barysaw, Rivne, Ostroh, Iziaslav, Kamianets-Podilskyi.
Remained in the Commonwealth until 1795: Vilnius, Hrodna, Navahrudak, Brest, Lutsk, Kremenets, Kovel, Dubno, Lida, Kobryn, Ashmyany, Braslaw.
City sanity checks: Gdańsk and Toruń stay Polish until 1793 and pass to Prussia in 1793; Warsaw and Białystok go to Prussia in 1795; Kraków and Lublin go to Austria in 1795; Brest and Vilnius go to Russia in 1795.

## Reported uncertainties

1. **The 1793 line near towns that sit on it (±15 km):** the status of Druja, Vileyka and Mir could not be confirmed from an independent text source; Russian- and Belarusian-language sources are blocked by this environment's network policy. Rivne lies 3 km from the line. At full-map scale the difference cannot be seen, so **no close-up of the 1793 eastern line** is planned.
2. **Published area figures disagree with each other by up to about 10 %**, for example 228,600 vs 250,000 km² for Russia's 1793 gain. On screen we round them and attribute them to a source, or leave them out.
3. **Third Partition timing:** the treaties were signed on 3 January 1795 (Russia–Austria) and 24 October 1795 (all three powers). The Prussian–Austrian demarcation near Kraków was finalised only in 1796. The maps show the final 1795–96 settlement.
4. **Courland** (a Polish fief until 1795) is approximated by today's Latvian border inside the 1773 outline. The only notable difference is a strip about 10 km wide at Palanga. It is shown hatched as a fief, not as Commonwealth core territory.
5. **Context borders outside the Commonwealth** (Habsburg lands, Ottoman Empire, Sweden and the Holy Roman Empire) come from OHM and modern Natural Earth outlines. They are shown for orientation only and were not verified individually.
6. **Coastlines** are modern (Natural Earth). The differences are negligible at these scales.
7. **Targowica:** the place where the confederation was proclaimed on 14 May 1792 could not be geolocated reliably, so it is **not pinned** on any map. The confederation was signed in St Petersburg on 27 April 1792.

## Context borders, revised after review
- **Habsburg Monarchy:** now includes Transylvania (OHM 2878295), the Banat of Temeswar (2747562), the Banat Military Frontier (2746839) and Bačka/Syrmia (unassigned land between the Danube and the Sava, bounded by the Ottoman frontier). Croatia-Slavonia is approximated by modern Croatia north of 44.55°N (orientation only).
- **Ottoman Empire, 1773:** OHM 2746687 (1718–1774, which includes the vassal Crimean Khanate) plus Bukovina (Moldavian until the Habsburg occupation of 1774/75). From 1791–92, the Russian outline after the Treaty of Jassy (January 1792) applies.
- **Republic of Venice:** Istria, Dalmatia and Albania (Kotor) shown as a separate state. **Republic of Ragusa** shown separately.
- Check: no unassigned land larger than ~500 km² remains inside any map frame.
