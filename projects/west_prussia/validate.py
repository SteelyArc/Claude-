"""Point-in-territory validation of every key map. Writes research/map_validation.md."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shapely.geometry import Point
from projects.west_prussia.territories import T

C = {  # lon, lat (city centres)
 "Danzig": (18.6466, 54.3520), "Thorn": (18.6050, 53.0100), "Elbing": (19.4044, 54.1561),
 "Marienwerder": (18.9286, 53.7286), "Marienburg": (19.0280, 54.0359), "Culm": (18.4300, 53.3486),
 "Graudenz": (18.7536, 53.4837), "Gdynia": (18.5305, 54.5189), "Königsberg": (20.5108, 54.7104),
 "Stuhm": (19.0244, 53.9089), "Rosenberg": (19.3350, 53.7180), "Frauenburg": (19.6830, 54.3570),
 "Bromberg": (18.0084, 53.1235), "Konitz": (17.5667, 53.6974), "Schlochau": (17.3640, 53.6620),
 "Deutsch Krone": (16.4644, 53.2731), "Dirschau": (18.7790, 54.0920), "Lemberg": (24.03, 49.84),
 "Polotsk": (28.78, 55.49), "Warsaw": (21.01, 52.23),
}
TESTS = [  # (map, city, territory, expected)
 ("1466", "Danzig", "royal_prussia_1466", True), ("1466", "Thorn", "royal_prussia_1466", True),
 ("1466", "Elbing", "royal_prussia_1466", True), ("1466", "Marienburg", "royal_prussia_1466", True),
 ("1466", "Culm", "royal_prussia_1466", True), ("1466", "Frauenburg", "warmia", True),
 ("1466", "Marienwerder", "order_1466", True), ("1466", "Marienwerder", "royal_prussia_1466", False),
 ("1466", "Königsberg", "order_1466", True),
 ("1772", "Danzig", "prussian_share_1772", False), ("1772", "Thorn", "prussian_share_1772", False),
 ("1772", "Elbing", "prussian_share_1772", True), ("1772", "Marienburg", "prussian_share_1772", True),
 ("1772", "Bromberg", "prussian_share_1772", True), ("1772", "Danzig", "plc_1773", True),
 ("1772", "Thorn", "plc_1773", True), ("1772", "Lemberg", "austrian_share_1772", True),
 ("1772", "Polotsk", "russian_share_1772", True), ("1772", "Warsaw", "plc_1773", True),
 ("1773", "Marienwerder", "west_prussia_1773", True), ("1773", "Elbing", "west_prussia_1773", True),
 ("1773", "Bromberg", "west_prussia_1773", False), ("1773", "Frauenburg", "west_prussia_1773", False),
 ("1773", "Danzig", "west_prussia_1773", False), ("1773", "Thorn", "west_prussia_1773", False),
 ("1793", "Danzig", "prussia_1793", True), ("1793", "Thorn", "prussia_1793", True),
 ("1793", "Danzig", "west_prussia_1793", True), ("1793", "Thorn", "west_prussia_1793", None),
 ("1878", "Danzig", "west_prussia_1878", True), ("1878", "Thorn", "west_prussia_1878", True),
 ("1878", "Elbing", "west_prussia_1878", True), ("1878", "Marienwerder", "west_prussia_1878", True),
 ("1878", "Graudenz", "west_prussia_1878", True), ("1878", "Konitz", "west_prussia_1878", True),
 ("1878", "Schlochau", "west_prussia_1878", True), ("1878", "Deutsch Krone", "west_prussia_1878", True),
 ("1878", "Bromberg", "west_prussia_1878", False), ("1878", "Königsberg", "west_prussia_1878", False),
 ("1920", "Danzig", "free_city", True), ("1920", "Gdynia", "pomorskie_1920", True),
 ("1920", "Thorn", "pomorskie_1920", True), ("1920", "Graudenz", "pomorskie_1920", True),
 ("1920", "Konitz", "pomorskie_1920", True), ("1920", "Dirschau", "pomorskie_1920", True),
 ("1920", "Elbing", "reich_1920_12", True), ("1920", "Marienburg", "reich_1920_12", True),
 ("1920", "Marienwerder", "reich_1920_12", True), ("1920", "Schlochau", "pomorskie_1920", False),
 ("1922", "Deutsch Krone", "grenzmark_1922", True), ("1922", "Schlochau", "grenzmark_1922", True),
 ("1922", "Marienwerder", "rb_westpreussen_1922", True),
 ("plebiscite", "Stuhm", "plebiscite_area_marienwerder", True),
 ("plebiscite", "Marienwerder", "plebiscite_area_marienwerder", True),
 ("plebiscite", "Marienburg", "plebiscite_area_marienwerder", True),
 ("plebiscite", "Rosenberg", "plebiscite_area_marienwerder", True),
 ("plebiscite", "Graudenz", "plebiscite_area_marienwerder", False),
 ("plebiscite", "Elbing", "plebiscite_area_marienwerder", False),
 ("plebiscite", "Marienwerder", "five_villages_1920", False),
 ("1939", "Danzig", "reichsgau_dwp", True), ("1939", "Gdynia", "reichsgau_dwp", True),
 ("1939", "Thorn", "reichsgau_dwp", True), ("1939", "Danzig", "poland_1938", False),
 ("1939", "Gdynia", "poland_1938", True),
 ("1945", "Danzig", "poland_1945", True), ("1945", "Elbing", "poland_1945", True),
 ("1945", "Königsberg", "poland_1945", False), ("1945", "Königsberg", "soviet_kaliningrad", True),
 ("today", "Danzig", "poland_today", True), ("today", "Deutsch Krone", "poland_today", True),
 ("today", "Schlochau", "poland_today", True), ("today", "Elbing", "poland_today", True),
]
def main():
    rows, fails = [], 0
    for m, c, t, exp in TESTS:
        got = T(t).contains(Point(*C[c]))
        ok = "info" if exp is None else ("PASS" if got == exp else "FAIL")
        fails += ok == "FAIL"
        rows.append(f"| {m} | {c} | `{t}` | {exp} | {got} | {ok} |")
        print(f"{ok:5s} {m:10s} {c:14s} in {t:30s} exp={exp} got={got}")
    a = {k: T(k).area for k in ["west_prussia_1773","prussian_share_1772","russian_share_1772","austrian_share_1772","plebiscite_area_marienwerder","five_villages_1920"]}
    md = ["# Map Validation – point-in-territory tests", "",
          "Generated by `projects/west_prussia/validate.py` from OpenHistoricalMap geometry (CC0).", "",
          "| Map | City | Territory | Expected | Result | Status |", "|---|---|---|---|---|---|"] + rows
    md += ["", f"**{len(TESTS)} tests, {fails} failures.**", "", "Derived areas (deg², for plausibility):", ""]
    md += [f"- `{k}`: {v:.3f}" for k, v in a.items()]
    md += ["", "## Known data limits / decisions", "",
           "- **Five villages (12 Aug 1920)** on the right bank of the Vistula assigned to Poland after the plebiscite are "
           "not modelled in OpenHistoricalMap (`five_villages_1920` = 0). They are **not drawn**; the fact is given in text only.",
           "- **Draheim exclave** (≈16.3°E, annexed 1772): its provincial assignment in 1773 could not be verified, so it is "
           "**excluded** from the derived 1773 West Prussia polygon and shown only as Prussian territory.",
           "- **West Prussia 1773** has no OHM relation; it is derived = Prussian 1772 gains − Warmia − Netze District + "
           "Kreis Marienwerder (en.wikipedia 'West Prussia': composition of the 1773 province).",
           "- **Austrian/Russian 1772 shares** are derived from the Commonwealth before/after 1773 minus the Prussian share, "
           "split by location (south = Austria/Galicia, north-east = Russia).",
           "- **Poland Jan/Aug 1920** relations are open in the east (border not yet fixed); northern maps use Poland 1924, "
           "whose northern border (Corridor/Free City) is identical to 1920.",
           "- **1939 annexed area** = Reichsgau Danzig-West Prussia ∩ (Poland 1938 ∪ Free City); the Reichsgau's eastern part "
           "(Regierungsbezirk West Prussia) was already German and is not hatched.",
           "- **Soviet zone 1945** = East Prussia (1922–39) − Poland 1945, so the two borders coincide exactly.",
           "- **Vistula delta** is period-dependent (OHM dated waterways): pre-1895 course to Danzig; the 1895 cut only from 1895.",
           "- **Thorn 1793–1807**: OHM places Thorn in the Province of West Prussia; some sources assign it to South Prussia. "
           "The 1793 map therefore only states 'incorporated into Prussia'."]
    open(os.path.join(os.path.dirname(__file__), "../../research/map_validation.md"), "w").write("\n".join(md) + "\n")
    print("failures:", fails, a)
if __name__ == "__main__":
    main()
