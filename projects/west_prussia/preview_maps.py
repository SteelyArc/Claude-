"""Render Phase 2 map preview stills (final state of each map scene) + a contact sheet."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine.render import new_surface, save_png
from projects.west_prussia.maps import MAPS

OUT = os.path.join(os.path.dirname(__file__), "../../previews/maps")

def main(names=None):
    for name, fn in MAPS.items():
        if names and not any(n in name for n in names):
            continue
        t0 = time.time()
        s = new_surface()
        fn(s.getCanvas(), 1.0, 0)
        save_png(s, os.path.join(OUT, f"{name}.png"))
        print(f"{name}: {time.time() - t0:.1f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1:])
