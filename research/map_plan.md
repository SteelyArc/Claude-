# Map Plan and Geodata Sources

## Base layers (all maps)
| Layer | Source | Licence |
|---|---|---|
| Coastline, land, lakes, rivers (Vistula, Nogat, Oder, Neisse, Pregel) | Natural Earth 1:10m (`nvkelso/natural-earth-vector`, reachable) | Public domain |
| Detailed lower-Vistula hydrography and the Vistula Lagoon / Curonian Lagoon | OpenStreetMap-derived Natural Earth 10m, refined with OHM waterways where needed | PD / CC0 |
| Projection | ETRS89 LAEA (EPSG:3035), rotated to fit 9:16, so shapes are not distorted | – |

Note: the Vistula's modern mouth (Przekop Wisły, cut in 1895) is a modern feature. Maps before 1895 use the old mouth at Danzig (Weichselmünde/Leniwka), drawn from OHM historic waterways or historical atlases. Before that goes on screen it is checked against a reference ⚠.

## Historical boundaries – OpenHistoricalMap (CC0), relation IDs
| Map | Polygon(s) | OHM relation(s) | Status |
|---|---|---|---|
| M2 Teutonic Order (c. 1410 / 1455) | State of the Teutonic Order | 2748596 (1435–1455), 2748599 (1455–1466), 2826609 (1237–1558, general) | Geometry to check against IEG-Maps / Putzger before use |
| **M3 1466** | Royal Prussia; Order 1466–1525; Prince-Bishopric of Warmia; Kingdom of Poland | 2693991, 2748600, 2696443, (Crown 2696309 is post-1569 – Poland 1466 to be derived or simplified ⚠) | Royal Prussia + Order available |
| **M4 1772** | Poland-Lithuania before/after 1773; Kingdom of Prussia before/after 22 Sep 1772 | 2961392 (PLC 1686–1773), 2692511 (PLC 1773–1793), 2748498 / 2748497 (Prussia) | Prussian share = difference. Russian/Austrian shares need Russia/Habsburg relations (to query) ⚠ |
| **M5 1773** | Province of West Prussia 1773 | **No direct relation** → derived: Prussian 1772 share − Warmia (2696443) − Netze District (2748039) + Kreis Marienwerder (2828862) | Derived; checked against the GHDI partition map and en/de article text ⚠ |
| **M5 1793** | Province of West Prussia 1793–1807 | 2809773 | Available |
| M6 19th c. | Province of West Prussia 1878–1909 / 1909–1919; RB Danzig, RB Marienwerder | 2691483, 2828868, 2694699, 2828867 | Available |
| **M7 1919/20** | Pomeranian Voivodeship 1920; Free City of Danzig; German Reich 1920; East Prussia 1920 | 2741477, 2691478, 2741459, 2855640 | Available |
| **M8 1920 plebiscite** | Kreise Marienwerder, Stuhm, Rosenberg, Marienburg as voting areas (east of Vistula/Nogat) | 2693146 (Kreis Marienwerder 1818–1920) + Stuhm/Rosenberg/Marienburg (to query); result area = RB Marienwerder 1920-12-24 (2855646) | Plebiscite-area outline must match the treaty text (Art. 96–97) ⚠ |
| M8 1922 | Regierungsbezirk West Prussia; Grenzmark Posen–West Prussia | 2692538, 2694718 | Available |
| M9 Interwar | Poland 1924–38 (2692205), German Reich 1936 (2693085), East Prussia 1922 (2691479), Free City (2691478) | Available |
| **M10 1939** | Poland 1938–39 (2741574); Reichsgau Danzig-West Prussia (2747833); German Reich 1939 (2704716) | Available. Invasion arrows schematic (labelled) |
| **M12 1945** | Poland 1945–48 (2692206); Oder–Neisse line; Soviet front arrows (schematic) | Available + Natural Earth |
| **M13 Today** | Poland (2870169), voivodeships 1999 (2694728, 2695509, 2694729, 2694734), Germany (Natural Earth) | Available |

### Validation procedure (each map, before the Phase 2 preview)
1. Download the relation geometry (Overpass `out geom`), assemble polygons, and simplify only with topology preserved (< 150 m tolerance at the regional zoom).
2. Overlay on a reference map image of the same date (IEG-Maps Mainz, GHDI, *Putzger* or Westermann historical atlases, Commons PD maps). Check visually at 50 % opacity and render a diff PNG.
3. Check the key cities fall on the correct side of each border: Marienwerder (Order in 1466 / Germany in 1920), Danzig (outside Prussia 1772–93 / Free City 1920), Thorn (outside Prussia 1772–93 / Poland 1920), Elbing (Royal Prussia 1466 / Germany 1920), Gdingen/Gdynia (Poland 1920).
4. Record the result in `research/map_validation.md`. Any border that can't be confirmed is drawn **dashed and labelled "approximate"**, and listed for your decision.

## Map previews planned for Phase 2 (stills, 1080×1920)
1. 1466 Second Peace of Thorn · 2. 1772/1773 First Partition + new province · 3. 1793 Danzig & Thorn · 4. 1919/20 Versailles + Corridor + Free City · 5. 1920 Marienwerder plebiscite · 6. 1939 invasion / annexation · 7. 1945 Oder–Neisse / post-war · 8. Today
