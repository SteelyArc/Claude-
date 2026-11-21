"""Render frames from a built scene.

python render.py scene.blend out_dir --frames 1,150,204 [--pct 50] [--samples 64]
python render.py scene.blend out_dir --range 1 408 [--pct 50] [--samples 64]
Frames already rendered in out_dir are skipped, so a long render can resume.
"""
import argparse
import os
import sys
import time

import bpy

ap = argparse.ArgumentParser()
ap.add_argument('blend')
ap.add_argument('out')
ap.add_argument('--frames', default='')
ap.add_argument('--range', nargs=2, type=int)
ap.add_argument('--pct', type=int, default=50)
ap.add_argument('--samples', type=int, default=0)
ap.add_argument('--threshold', type=float, default=0)
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.blend))
sc = bpy.context.scene
sc.render.resolution_percentage = args.pct
if args.samples:
    sc.cycles.samples = args.samples
if args.threshold:
    sc.cycles.adaptive_threshold = args.threshold
os.makedirs(args.out, exist_ok=True)

frames = [int(f) for f in args.frames.split(',') if f] if args.frames else \
    list(range(args.range[0], args.range[1] + 1))

# step through particle simulation from its start so caches are valid
psys_objs = [o for o in sc.objects if any(m.type == 'PARTICLE_SYSTEM' for m in o.modifiers)]
if psys_objs and frames and max(frames) >= 290:
    for f in range(285, min(frames[0], sc.frame_end) + 1):
        sc.frame_set(f)

for f in frames:
    path = os.path.join(args.out, f'f{f:04d}.png')
    if os.path.exists(path):
        continue
    sc.frame_set(f)
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time() - t:.1f}s', flush=True)
