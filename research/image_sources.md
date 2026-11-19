# Archival Image Plan – Search Targets and Licence Rules

**Status:** The Wikimedia Commons API is rate-limiting this cloud container's shared address (HTTP "too many requests"). No image has been downloaded or verified yet. Below are *search targets*, not confirmed files. Each image is verified individually (date, place, author, licence, original archive ID) and logged in `assets/images/SOURCES.csv` before use.

## Licence rules
- Accept: Public domain (author died > 70 years ago / US pre-1930 / PD-Poland pre-1994 without copyright notice where Commons confirms), CC0, CC BY, CC BY-SA (attribution shown in end credits and in SOURCES.csv), Bundesarchiv CC BY-SA 3.0 DE.
- Reject: anything without a traceable original archive or author; colourised or "enhanced" images (unless clearly labelled); AI images; stills from dramatised films.
- Library of Congress Photochrom prints (Detroit Publishing Co., c. 1890–1900) are public domain → good for 19th-century Danzig, Marienburg, Thorn.

## Targets per scene
| Scene | Search target | Likely archive / Commons category |
|---|---|---|
| 1, 13 | Modern Vistula landscape, Malbork Castle aerial | Commons CC BY-SA "Malbork Castle", "Vistula" |
| 2 | Marienburg Castle (historic photo/photochrom), Grand Master's Palace; Thorn castle ruins; Teutonic seals | LoC Photochrom "Marienburg"; Commons "Malbork Castle in the 19th century" |
| 3 | 1466 treaty document scan (Polish State Archives / Prussian Privy State Archives); 15th-c. map of Prussia | Commons "Second Peace of Thorn"; Archiwum Główne Akt Dawnych |
| 4 | *Le Gâteau des Rois* (J.-M. Moreau, 1773) | Commons "Le gâteau des rois" (PD) |
| 5 | 18th-century plan of Danzig; Frederick II homage at Marienburg 1772 (engraving) | Commons "Maps of Gdańsk 18th century" |
| 6 | Danzig Long Market, Crane Gate, Motława harbour (photochrom); Dirschau Vistula bridge; Thorn old town; Marienwerder cathedral & castle; Elbing harbour | LoC Photochrom; Commons "Gdańsk in the 19th century", "Tczew bridge" |
| 7a/7 | WWI photo; Treaty of Versailles printed text; Paris 1919 signing | LoC; Commons "Treaty of Versailles" (PD) |
| 8 | Marienwerder plebiscite poster / ballot / voting scenes 1920 | Commons "East Prussian plebiscite 1920" |
| 8b | Corridor border crossings, transit trains (Korridorzug) | Bundesarchiv on Commons |
| 9 | Gdynia harbour under construction 1920s–30s, MS *Piłsudski*, Danzig 1930s streets | NAC (Narodowe Archiwum Cyfrowe) via Commons |
| 10 | Westerplatte 1 Sep 1939; Polish Post Office Danzig; SMS *Schleswig-Holstein* | Bundesarchiv Bild 183 / 101I (CC BY-SA 3.0 DE) |
| 11 | Stutthof camp (non-graphic: gate, barracks), Piaśnica memorial, Danzig Great Synagogue (pre-1939), documents | Commons "Stutthof concentration camp", USHMM (licence check required) |
| 12 | Refugees crossing the frozen Vistula Lagoon (Frisches Haff) 1945; Danzig ruins 1945; Polish settlers 1945–47 | Bundesarchiv; NAC |
| 13 | Gdańsk today, Toruń old town (UNESCO), Kwidzyn castle | Commons CC BY-SA |

## How the images will be retrieved
- Retry the Commons API with a backoff (one request per ~5 s). If the block persists, files can be fetched directly from `upload.wikimedia.org` (allowed) once file names are confirmed, or you can drop images into `assets/images/inbox/` and I will verify and catalogue them.
