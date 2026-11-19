# Phase 2 – Map Previews (final frames of each animated map scene)

All frames 1080 × 1920. Rendered by `projects/west_prussia/preview_maps.py` (engine: `engine/render.py`, skia).
Borders: OpenHistoricalMap (CC0, relation IDs in `projects/west_prussia/relations.py`), coast/rivers/lakes: Natural Earth (PD),
Vistula delta: OHM dated waterways. Validation: `research/map_validation.md` (71 point-in-territory tests, 0 failures).

| File | Map | Key checks |
|---|---|---|
| 01_1466.png | Second Peace of Thorn | Royal Prussia (Pomerelia, Culm Land, Marienburg, Elbing) vs. Order; Warmia separate; Marienwerder stays with the Order |
| 02_1772.png | First Partition | Prussian, Russian, Austrian shares; Danzig & Thorn ringed as still Polish |
| 03_1773.png | Province of West Prussia | Derived 1773 province; Warmia → East Prussia; Netze District separate; Danzig & Thorn outside |
| 04_1793.png | Danzig & Thorn incorporated | 1793 province incl. Danzig and Thorn territories (red outline = added) |
| 05_1919.png | Treaty of Versailles | Corridor (Poland), Free City, plebiscite area, German west; old province dashed |
| 06_1920_plebiscite.png | Marienwerder plebiscite | Voting area per Treaty Art. 96–97; result bar from official figures |
| 07_1939.png | Invasion & annexation | Annexed area hatched (not shown as a normal border); arrows schematic |
| 08_1945.png | End of German rule | Oder–Neisse line; Polish administration hatched (pending peace settlement); Soviet zone |
| 09_today.png | Today | Historic outline lies entirely within Poland; modern names |
| contact_sheet.png | All nine maps | – |

Animation (Phase 3) reuses exactly these scenes: each map function takes `t` (0→1) and animates border drawing (with pen nib),
ink-spread territory reveals, label fades and camera moves.
