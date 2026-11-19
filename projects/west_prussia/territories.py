"""Derived historical territories for the West Prussia maps (WGS84 shapely geometries)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from functools import lru_cache
from shapely.ops import unary_union
from shapely.geometry import box
from engine.geo import ohm_relation
from projects.west_prussia.relations import R

def rel(key):
    return ohm_relation(R[key])[0]

@lru_cache(None)
def T(name):
    if name == "prussian_share_1772":   # Commonwealth land taken by Prussia in 1772
        return rel("plc_1686").intersection(rel("prussia_1772")).buffer(0)
    if name == "partition_1772_rest":    # remaining 1772 losses (Russia + Austria), split by location below
        lost = rel("plc_1686").difference(rel("plc_1773")).difference(T("prussian_share_1772"))
        return lost.buffer(-0.01).buffer(0.01)   # drop slivers from non-identical shared edges
    if name in ("russian_share_1772", "austrian_share_1772"):
        parts = [p for p in getattr(T("partition_1772_rest"), "geoms", [T("partition_1772_rest")]) if p.area > 0.05]
        rus = [p for p in parts if p.centroid.y > 51.5]
        aus = [p for p in parts if p.centroid.y <= 51.5]
        return unary_union(rus if name.startswith("russian") else aus)
    if name == "west_prussia_1773":     # derived: no direct OHM relation exists
        wp = T("prussian_share_1772").difference(rel("warmia")).difference(rel("netze_1773"))
        wp = unary_union([wp, rel("kreis_marienwerder_1773")]).buffer(0)
        # Draheim exclave (≈16.3°E, annexed 1772): provincial assignment unverified → excluded, see map_validation.md
        return wp.difference(box(10, 50, 16.75, 56)).buffer(0)
    if name == "plebiscite_area_marienwerder":   # Treaty of Versailles Art. 96: Kreise Stuhm, Rosenberg,
        kreise = unary_union([rel(k) for k in ("kreis_stuhm_1818", "kreis_rosenberg_1818",   # Marienwerder E of Vistula,
                              "kreis_marienwerder_1818", "kreis_marienburg_1818")])          # Marienburg E of Nogat
        return kreise.difference(rel("pomorskie_1919")).difference(rel("danzig_allied_1920")).buffer(-0.001).buffer(0.001)
    if name == "five_villages_1920":    # assigned to Poland 12 Aug 1920 (right bank of the Vistula)
        return T("plebiscite_area_marienwerder").intersection(rel("pomorskie_1920")).buffer(-0.0005).buffer(0.0005)
    if name == "annexed_1939":          # former Polish + Free City land in the Reichsgau (RB West Prussia was German)
        return rel("reichsgau_dwp").intersection(unary_union([rel("poland_1938"), rel("free_city")])).buffer(-0.002).buffer(0.002)
    if name == "soviet_1945":           # northern East Prussia under Soviet control: pre-war East Prussia minus Poland 1945
        return rel("east_prussia_1922").difference(rel("poland_1945")).buffer(-0.002).buffer(0.002)
    if name == "soviet_kaliningrad":    # northern East Prussia under Soviet rule from 1945 (OHM has no 1945 relation)
        from engine.geo import ne_clip
        from shapely.geometry import Point
        polys = [g for g, p in ne_clip("ne_10m_admin_0_countries", (19.0, 54.2, 23.0, 55.4), lambda p: p.get("ADM0_A3") == "RUS")]
        return unary_union(polys)
    return rel(name)
