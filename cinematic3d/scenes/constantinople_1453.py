"""Visual test scene: Siege of Constantinople, April 1453.

Orban's great bronze bombard fires at the Theodosian Land Walls at dawn.

  Shot 1 (frames 1-264)   - approach the gun, "the breath" (the linstock
                            descends to the touch hole), then the shot.
  Shot 2 (frames 265-408) - the walls in stillness, then the impact on a
                            tower of the outer wall: THE BIG MOMENT.

Historical reference used:
  * Theodosian Walls: inner wall ~12 m high / ~5 m thick with towers
    ~18-20 m, outer wall ~8.5 m, terrace (peribolos) ~15-20 m, moat ~20 m
    wide and up to ~7 m deep. Limestone ashlar with bands of red brick
    (five courses per band) running through the wall.
  * Orban's bombard: cast bronze, ~8.2 m long, firing stone balls of
    roughly 270-550 kg (bore ~0.7-0.76 m). Bedded on a timber platform with
    a timber/earth abutment behind the breech, protected by earthworks and
    wooden screens, Ottoman lines fronted by a palisade.
  * Ottoman batteries lay west of the walls, so at dawn the sun rises
    behind the city (east) - the walls are backlit from the gun line.

Usage:  python constantinople_1453.py <output.blend>
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Vector, noise

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lib import (add_bevel, bm_box, bump, combine, coords, key, lathe, link,  # noqa: E402
                 map_range, math_node, mix_rgb, new_material, node, noise_tex,
                 obj_from_bmesh, rng, rock_mesh, separate)

FPS = 24
SHOT1 = (1, 264)
SHOT2 = (265, 408)
F_TOUCH = 196      # match touches the touch-hole
F_FIRE = 204       # main charge goes off
F_IMPACT = 295     # ball strikes the tower

GUN_AXIS_Z = 1.15
MUZZLE = Vector((0.0, 4.15, GUN_AXIS_Z + 0.11))
TOUCH_HOLE = Vector((0.0, -3.5, GUN_AXIS_Z + 0.47))
IMPACT = Vector((0.6, 229.0, 6.4))

SUN_AZ = 58.0      # degrees from +Y (towards the city) rotating to +X
SUN_EL = 7.5       # low dawn sun

R = rng(1453)


# =============================================================== utilities
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def col(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def link_to(ob, c):
    for uc in list(ob.users_collection):
        uc.objects.unlink(ob)
    c.objects.link(ob)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def ease_out(t, k=4.0):
    t = min(1.0, max(0.0, t))
    return 1 - math.exp(-k * t) if k > 0 else t


def ease_io(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


# =============================================================== materials
def mat_wall(name='TheodosianMasonry', tone=1.0):
    m, nt, out = new_material(name)
    p = coords(nt, 'Object')
    x, y, z = separate(nt, p)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    nx, ny, nz = separate(nt, geo.outputs['True Normal'])
    side = math_node(nt, 'GREATER_THAN', math_node(nt, 'ABSOLUTE', nx), math_node(nt, 'ABSOLUTE', ny))
    u = math_node(nt, 'ADD', x, math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', y, x), side))
    uv = combine(nt, u, z, 0.0)

    # limestone ashlar courses (~0.9 x 0.45 m blocks)
    ash = node(nt, 'ShaderNodeTexBrick', offset=0.5, squash=1.0)
    link(nt, uv, ash.inputs['Vector'])
    ash.inputs['Scale'].default_value = 1.0
    ash.inputs['Brick Width'].default_value = 0.92
    ash.inputs['Row Height'].default_value = 0.46
    ash.inputs['Mortar Size'].default_value = 0.022
    ash.inputs['Mortar Smooth'].default_value = 0.35
    ash.inputs['Bias'].default_value = 0.0
    ash.inputs['Color1'].default_value = (0.50 * tone, 0.44 * tone, 0.35 * tone, 1)
    ash.inputs['Color2'].default_value = (0.38 * tone, 0.34 * tone, 0.28 * tone, 1)
    ash.inputs['Mortar'].default_value = (0.47, 0.43, 0.37, 1)

    # red brick bands: 5 courses of thin bricks in thick lime mortar
    brk = node(nt, 'ShaderNodeTexBrick', offset=0.5, squash=1.0)
    link(nt, uv, brk.inputs['Vector'])
    brk.inputs['Scale'].default_value = 1.0
    brk.inputs['Brick Width'].default_value = 0.36
    brk.inputs['Row Height'].default_value = 0.085
    brk.inputs['Mortar Size'].default_value = 0.018
    brk.inputs['Mortar Smooth'].default_value = 0.4
    brk.inputs['Bias'].default_value = 0.0
    brk.inputs['Color1'].default_value = (0.36, 0.12, 0.065, 1)
    brk.inputs['Color2'].default_value = (0.46, 0.19, 0.10, 1)
    brk.inputs['Mortar'].default_value = (0.55, 0.47, 0.40, 1)

    period = 3.35
    zz = math_node(nt, 'MODULO', math_node(nt, 'ADD', z, 0.7), period)
    band = math_node(nt, 'LESS_THAN', zz, 0.44)

    # weathering
    big = noise_tex(nt, p, 0.06, 4, 0.6)
    mid = noise_tex(nt, p, 0.9, 8, 0.62, 0.2)
    streak_v = combine(nt, math_node(nt, 'MULTIPLY', u, 3.0), math_node(nt, 'MULTIPLY', z, 0.12), 0.0)
    streak = noise_tex(nt, streak_v, 1.5, 4, 0.5)
    base = mix_rgb(nt, band, ash.outputs['Color'], brk.outputs['Color'])
    # patched repairs: lighter, newer stone
    repair = map_range(nt, big.outputs['Fac'], 0.58, 0.62)
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', repair, 0.35), base, (0.58, 0.53, 0.45))
    grime = map_range(nt, streak.outputs['Fac'], 0.35, 0.75, 0.55, 1.0)
    base = mix_rgb(nt, 1.0, base, combine(nt, grime, grime, grime), 'MULTIPLY')
    dirt = map_range(nt, mid.outputs['Fac'], 0.3, 0.7, 0.75, 1.05)
    base = mix_rgb(nt, 1.0, base, combine(nt, dirt, dirt, dirt), 'MULTIPLY')
    # damp, dark base with a little moss
    damp = map_range(nt, z, 2.2, 0.0, 0.0, 1.0)
    moss = math_node(nt, 'MULTIPLY', damp, map_range(nt, mid.outputs['Fac'], 0.45, 0.65))
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', damp, 0.5), base, (0.12, 0.11, 0.09))
    base = mix_rgb(nt, math_node(nt, 'MULTIPLY', moss, 0.6), base, (0.10, 0.12, 0.05))

    mortar = mix_rgb(nt, band, ash.outputs['Fac'], brk.outputs['Fac'])
    fine = noise_tex(nt, p, 14.0, 10, 0.7)
    chip = noise_tex(nt, p, 3.5, 6, 0.6)
    h = math_node(nt, 'SUBTRACT', math_node(nt, 'MULTIPLY', fine.outputs['Fac'], 0.25),
                  math_node(nt, 'MULTIPLY', mortar, 0.9))
    h = math_node(nt, 'ADD', h, math_node(nt, 'MULTIPLY', chip.outputs['Fac'], 0.35))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled', (600, 0))
    link(nt, base, bsdf.inputs['Base Color'])
    link(nt, map_range(nt, fine.outputs['Fac'], 0.3, 0.7, 0.78, 0.95), bsdf.inputs['Roughness'])
    link(nt, bump(nt, h, 0.55, 0.06), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_rubble():
    m, nt, out = new_material('RubbleCore')
    p = coords(nt, 'Object')
    vor = node(nt, 'ShaderNodeTexVoronoi')
    link(nt, p, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 7.0
    n = noise_tex(nt, p, 18, 8, 0.7)
    cbrick = mix_rgb(nt, map_range(nt, vor.outputs['Color'], 0.55, 0.6), (0.52, 0.47, 0.40), (0.42, 0.17, 0.09))
    c = mix_rgb(nt, map_range(nt, n.outputs['Fac'], 0.4, 0.6, 0, 0.5), cbrick, (0.65, 0.6, 0.52))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.95
    link(nt, bump(nt, math_node(nt, 'ADD', vor.outputs['Distance'], n.outputs['Fac']), 0.9, 0.05),
         bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_bronze():
    m, nt, out = new_material('CastBronze')
    p = coords(nt, 'Object')
    x, y, z = separate(nt, p)
    n1 = noise_tex(nt, p, 1.6, 8, 0.62, 0.4)
    n2 = noise_tex(nt, p, 22.0, 8, 0.65)
    pits = node(nt, 'ShaderNodeTexVoronoi')
    link(nt, p, pits.inputs['Vector'])
    pits.inputs['Scale'].default_value = 90.0
    bronze = mix_rgb(nt, map_range(nt, n1.outputs['Fac'], 0.3, 0.7), (0.26, 0.15, 0.07), (0.40, 0.25, 0.12))
    # dark oxidation & grease (the crew oiled the gun after every shot)
    patina = map_range(nt, n1.outputs['Fac'], 0.48, 0.66)
    bronze = mix_rgb(nt, math_node(nt, 'MULTIPLY', patina, 0.7), bronze, (0.09, 0.075, 0.05))
    soot = map_range(nt, y, 2.4, 4.2)
    soot = math_node(nt, 'MULTIPLY', soot, map_range(nt, n2.outputs['Fac'], 0.25, 0.65, 0.6, 1.0))
    bronze = mix_rgb(nt, soot, bronze, (0.025, 0.022, 0.02))
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.12
    bronze = mix_rgb(nt, map_range(nt, ao.outputs['AO'], 0.4, 1.0, 0.8, 0.0), bronze, (0.05, 0.045, 0.03))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, bronze, bsdf.inputs['Base Color'])
    bsdf.inputs['Metallic'].default_value = 0.85
    rough = map_range(nt, n2.outputs['Fac'], 0.3, 0.7, 0.42, 0.68)
    link(nt, math_node(nt, 'ADD', rough, math_node(nt, 'MULTIPLY', patina, 0.15)), bsdf.inputs['Roughness'])
    h = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', n2.outputs['Fac'], 0.6),
                  math_node(nt, 'MULTIPLY', map_range(nt, pits.outputs['Distance'], 0.0, 0.12, -1.0, 0.0), 0.5))
    link(nt, bump(nt, h, 0.3, 0.006), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_wood(name='Oak', tint=(0.20, 0.14, 0.09), axis='Y'):
    m, nt, out = new_material(name)
    p = coords(nt, 'Object')
    sx = {'X': (0.08, 1, 1), 'Y': (1, 0.08, 1), 'Z': (1, 1, 0.08)}[axis]
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'MULTIPLY'
    link(nt, p, vm.inputs[0])
    vm.inputs[1].default_value = sx
    grain = noise_tex(nt, vm.outputs[0], 9.0, 10, 0.68, 2.5)
    blot = noise_tex(nt, p, 1.2, 5, 0.6)
    c = mix_rgb(nt, map_range(nt, grain.outputs['Fac'], 0.35, 0.65), tint,
                tuple(min(1, t * 1.7) for t in tint))
    c = mix_rgb(nt, map_range(nt, blot.outputs['Fac'], 0.45, 0.7, 0, 0.45), c, (0.16, 0.15, 0.135))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.82
    link(nt, bump(nt, grain.outputs['Fac'], 0.45, 0.01), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_stone_ball():
    m, nt, out = new_material('StoneShot')
    p = coords(nt, 'Object')
    x, y, z = separate(nt, p)
    vor = node(nt, 'ShaderNodeTexVoronoi')
    link(nt, p, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 55.0
    n = noise_tex(nt, p, 3.0, 8, 0.62, 0.4)
    nf = noise_tex(nt, p, 30.0, 6, 0.6)
    c = mix_rgb(nt, map_range(nt, n.outputs['Fac'], 0.3, 0.7), (0.20, 0.19, 0.17), (0.33, 0.31, 0.28))
    speck = map_range(nt, vor.outputs['Distance'], 0.0, 0.25, 0.35, 0.0)
    c = mix_rgb(nt, speck, c, (0.05, 0.05, 0.05))
    # mud and grime on the underside, where the balls sat in the dirt
    grime = map_range(nt, math_node(nt, 'ADD', z, math_node(nt, 'MULTIPLY', n.outputs['Fac'], 0.3)), 0.05, -0.25)
    c = mix_rgb(nt, grime, c, (0.08, 0.06, 0.045))
    chisel = node(nt, 'ShaderNodeTexVoronoi')
    link(nt, p, chisel.inputs['Vector'])
    chisel.inputs['Scale'].default_value = 11.0
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    link(nt, map_range(nt, nf.outputs['Fac'], 0.3, 0.7, 0.7, 0.92), bsdf.inputs['Roughness'])
    h = math_node(nt, 'ADD', math_node(nt, 'MULTIPLY', chisel.outputs['Distance'], 0.6), nf.outputs['Fac'])
    link(nt, bump(nt, h, 0.45, 0.02), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_iron():
    m, nt, out = new_material('WroughtIron')
    p = coords(nt, 'Object')
    n = noise_tex(nt, p, 12, 8, 0.65)
    c = mix_rgb(nt, map_range(nt, n.outputs['Fac'], 0.45, 0.65), (0.05, 0.045, 0.04), (0.22, 0.10, 0.04))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    bsdf.inputs['Metallic'].default_value = 0.6
    bsdf.inputs['Roughness'].default_value = 0.75
    link(nt, bump(nt, n.outputs['Fac'], 0.4, 0.01), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_terrain():
    m, nt, out = new_material('Ground')
    p = coords(nt, 'Object')
    x, y, z = separate(nt, p)
    # trampled ground around the battery, radiating from the gun
    d = math_node(nt, 'LENGTH' if False else 'SQRT',
                  math_node(nt, 'ADD', math_node(nt, 'POWER', x, 2.0),
                            math_node(nt, 'POWER', math_node(nt, 'SUBTRACT', y, -3.0), 2.0)))
    n_big = noise_tex(nt, p, 0.05, 6, 0.6)
    n_mid = noise_tex(nt, p, 0.6, 8, 0.6, 0.3)
    n_fine = noise_tex(nt, p, 9.0, 8, 0.7)
    dn = math_node(nt, 'ADD', d, math_node(nt, 'MULTIPLY', n_mid.outputs['Fac'], 14.0))
    mud = map_range(nt, dn, 30.0, 17.0)
    # trampled track to the walls side
    trk = map_range(nt, math_node(nt, 'ABSOLUTE', math_node(nt, 'ADD', x, math_node(nt, 'MULTIPLY', n_big.outputs['Fac'], 12.0))), 6.0, 2.0)
    trk = math_node(nt, 'MULTIPLY', trk, map_range(nt, y, -60.0, -40.0))
    mud = math_node(nt, 'MAXIMUM', mud, math_node(nt, 'MULTIPLY', trk, 0.0))
    # moat & wall zone: bare dusty earth
    moat = math_node(nt, 'MULTIPLY', map_range(nt, y, 196.0, 203.0), map_range(nt, z, 0.2, -0.6))
    terrace = map_range(nt, y, 224.0, 226.0)

    grass_c = mix_rgb(nt, map_range(nt, n_big.outputs['Fac'], 0.35, 0.65), (0.085, 0.10, 0.035), (0.21, 0.19, 0.08))
    soil_c = mix_rgb(nt, map_range(nt, n_mid.outputs['Fac'], 0.3, 0.7), (0.20, 0.15, 0.10), (0.30, 0.24, 0.17))
    mud_c = mix_rgb(nt, map_range(nt, n_fine.outputs['Fac'], 0.3, 0.7), (0.07, 0.055, 0.04), (0.13, 0.10, 0.07))
    patch = map_range(nt, n_mid.outputs['Fac'], 0.45, 0.6)
    c = mix_rgb(nt, patch, grass_c, soil_c)
    c = mix_rgb(nt, mud, c, mud_c)
    c = mix_rgb(nt, math_node(nt, 'MAXIMUM', moat, math_node(nt, 'MULTIPLY', terrace, 0.6)), c, soil_c)

    wet = math_node(nt, 'MULTIPLY', mud, map_range(nt, n_mid.outputs['Fac'], 0.55, 0.7))
    rough = map_range(nt, wet, 0.0, 1.0, 0.92, 0.38)
    peb = node(nt, 'ShaderNodeTexVoronoi')
    link(nt, p, peb.inputs['Vector'])
    peb.inputs['Scale'].default_value = 14.0
    h = math_node(nt, 'ADD', n_fine.outputs['Fac'], math_node(nt, 'MULTIPLY', peb.outputs['Distance'], 0.6))
    h = math_node(nt, 'ADD', h, math_node(nt, 'MULTIPLY', n_mid.outputs['Fac'], 2.0))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    link(nt, rough, bsdf.inputs['Roughness'])
    link(nt, bump(nt, h, 0.6, 0.05), bsdf.inputs['Normal'])
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_grass():
    m, nt, out = new_material('GrassBlades')
    hi = nt.nodes.new('ShaderNodeHairInfo')
    obi = nt.nodes.new('ShaderNodeObjectInfo')
    rnd = hi.outputs['Random']
    green = mix_rgb(nt, rnd, (0.06, 0.085, 0.02), (0.20, 0.18, 0.06))
    c = mix_rgb(nt, map_range(nt, hi.outputs['Intercept'], 0.4, 1.0, 0.0, 0.6), green, (0.32, 0.27, 0.14))
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    link(nt, c, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.55
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    link(nt, c, tr.inputs['Color'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    mix.inputs[0].default_value = 0.35
    link(nt, bsdf.outputs[0], mix.inputs[1])
    link(nt, tr.outputs[0], mix.inputs[2])
    link(nt, mix.outputs[0], out.inputs[0])
    return m


def mat_emit(name, color, strength):
    m, nt, out = new_material(name)
    e = node(nt, 'ShaderNodeEmission')
    e.inputs['Color'].default_value = color
    e.inputs['Strength'].default_value = strength
    link(nt, e.outputs[0], out.inputs[0])
    return m, e


def mat_dark_opening():
    m, nt, out = new_material('Opening')
    bsdf = node(nt, 'ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.012, 0.01, 0.008, 1)
    bsdf.inputs['Roughness'].default_value = 1.0
    link(nt, bsdf.outputs[0], out.inputs[0])
    return m


def mat_puff(name, color, anis=0.35, density_scale=1.0, temp=1500.0):
    """Billowing volume for powder smoke / dust. Object space unit sphere.

    Animatable inputs: node 'DENS' (density scale), 'EMIT' (emission
    strength), 'EVOLVE' (noise W, the boiling motion), 'EDGE' (erosion of
    the edge as the cloud thins).
    """
    m, nt, out = new_material(name)
    p = coords(nt, 'Object')
    ev = node(nt, 'ShaderNodeValue')
    ev.name = 'EVOLVE'
    ev.outputs[0].default_value = 0.0
    big = noise_tex(nt, p, 1.15, 10, 0.62, 0.5, '4D', ev.outputs[0])
    small = noise_tex(nt, p, 4.0, 6, 0.6, 0.0, '4D', ev.outputs[0])
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'LENGTH'
    link(nt, p, vm.inputs[0])
    edge = node(nt, 'ShaderNodeValue')
    edge.name = 'EDGE'
    edge.outputs[0].default_value = 0.0
    g = math_node(nt, 'SUBTRACT', 1.0, vm.outputs['Value'])
    g = math_node(nt, 'ADD', g, math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', big.outputs['Fac'], 0.5), 1.25))
    g = math_node(nt, 'ADD', g, math_node(nt, 'MULTIPLY', math_node(nt, 'SUBTRACT', small.outputs['Fac'], 0.5), 0.35))
    g = math_node(nt, 'SUBTRACT', g, edge.outputs[0])
    shape = map_range(nt, g, 0.0, 0.16, 0.0, 1.0, 'SMOOTHSTEP')
    dens = node(nt, 'ShaderNodeValue')
    dens.name = 'DENS'
    dens.outputs[0].default_value = density_scale
    emit = node(nt, 'ShaderNodeValue')
    emit.name = 'EMIT'
    emit.outputs[0].default_value = 0.0
    vol = node(nt, 'ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = color
    vol.inputs['Anisotropy'].default_value = anis
    link(nt, math_node(nt, 'MULTIPLY', shape, dens.outputs[0]), vol.inputs['Density'])
    bb = nt.nodes.new('ShaderNodeBlackbody')
    link(nt, map_range(nt, shape, 0.2, 1.0, temp * 0.75, temp * 1.35), bb.inputs['Temperature'])
    link(nt, bb.outputs[0], vol.inputs['Emission Color'])
    hot = math_node(nt, 'POWER', shape, 2.0)
    link(nt, math_node(nt, 'MULTIPLY', hot, emit.outputs[0]), vol.inputs['Emission Strength'])
    link(nt, vol.outputs[0], out.inputs['Volume'])
    return m


def key_node_value(mat, node_name, frame, value):
    n = mat.node_tree.nodes[node_name]
    n.outputs[0].default_value = value
    n.outputs[0].keyframe_insert('default_value', frame=frame)


def linear_all(idblock):
    from lib import fcurves_of
    ad = idblock.animation_data
    if ad:
        for fc in fcurves_of(ad):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


# =============================================================== world
def build_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('DawnSky')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = node(nt, 'ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = True
    sky.sun_size = math.radians(0.6)
    sky.sun_intensity = 0.2
    sky.sun_elevation = math.radians(SUN_EL)
    sky.sun_rotation = sky_rotation_for_azimuth(SUN_AZ)
    sky.altitude = 50.0
    sky.air_density = 1.0
    sky.aerosol_density = 1.6
    sky.ozone_density = 1.0
    bg = node(nt, 'ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 0.17
    link(nt, sky.outputs[0], bg.inputs[0])
    o = node(nt, 'ShaderNodeOutputWorld')
    link(nt, bg.outputs[0], o.inputs['Surface'])

    # Sun lamp aligned to the sky's sun
    sd = bpy.data.lights.new('Sun', 'SUN')
    sd.energy = 4.2
    sd.angle = math.radians(0.8)
    sd.color = blackbody_rgb(3300)
    sun = bpy.data.objects.new('Sun', sd)
    sc.collection.objects.link(sun)
    d = sun_vector()
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()

    # Atmospheric haze: big homogeneous volume, forward scattering
    m, nt2, out = new_material('Haze')
    vol = node(nt2, 'ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = 0.0011
    vol.inputs['Anisotropy'].default_value = 0.72
    vol.inputs['Color'].default_value = (0.82, 0.80, 0.78, 1)
    link(nt2, vol.outputs[0], out.inputs['Volume'])
    bm = bmesh.new()
    bm_box(bm, (0, 160, 40), (900, 1000, 100))
    haze = obj_from_bmesh('AtmosphereHaze', bm, m)
    haze.visible_shadow = False
    return sun


def sky_rotation_for_azimuth(az_deg):
    # Verified empirically (Blender 5.3): sun_rotation 0 puts the sun on +Y,
    # increasing rotation swings it towards +X - i.e. it equals our azimuth.
    return math.radians(az_deg)


def sun_vector():
    az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
    return Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))


def blackbody_rgb(k):
    # compact approximation (Tanner Helland) -> linear-ish RGB
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = [min(255, max(0, v)) / 255.0 for v in (r, g, b)]
    return tuple(v ** 2.2 for v in c)


# =============================================================== terrain
def terrain_height(x, y):
    h = 1.6 * noise.fractal(Vector((x / 140.0, y / 140.0, 0.3)), 0.6, 2.0, 4)
    h += 0.35 * noise.fractal(Vector((x / 18.0, y / 18.0, 1.7)), 0.55, 2.0, 4)
    h += 0.05 * noise.fractal(Vector((x / 1.6, y / 1.6, 4.1)), 0.6, 2.0, 3)
    # rise of ground toward the walls (gun line slightly lower)
    h += 0.004 * y
    # prepared battery platform: flattened, churned
    dgun = math.hypot(x, y + 1.0)
    flat = smoothstep(9.0, 16.0, dgun)
    h = h * flat + (1 - flat) * (0.03 * noise.fractal(Vector((x / 1.2, y / 1.2, 9.0)), 0.6, 2.0, 3))
    # wheel/drag ruts leading back from the gun
    if -45 < y < -5:
        for rx in (-1.1, 1.1):
            h -= 0.09 * math.exp(-((x - rx - 0.4 * math.sin(y / 9.0)) ** 2) / 0.05)
    # wall zone: level terrace
    wz = smoothstep(150.0, 200.0, y)
    base_wall = 0.75
    h = h * (1 - wz) + base_wall * wz + wz * 0.06 * noise.fractal(Vector((x / 2.0, y / 2.0, 3.0)), 0.6, 2.0, 3)
    # moat (fosse) between y 203 and 224 with sloped scarps, ~6 m deep
    if 199.5 < y < 227.5:
        a = smoothstep(201.5, 204.5, y) * (1 - smoothstep(222.0, 224.5, y))
        h -= 6.2 * a
        h += a * 0.25 * noise.fractal(Vector((x / 5.0, y / 5.0, 7.0)), 0.6, 2.0, 3)
    return h


def axis_samples(lo, hi, fine_ranges, fine_step, coarse_step):
    xs = []
    v = lo
    while v < hi:
        xs.append(v)
        step = coarse_step
        for a, b in fine_ranges:
            if a <= v <= b:
                step = fine_step
                break
            # gentle transition
            if a - 30 < v < a or b < v < b + 30:
                step = min(step, (fine_step + coarse_step) * 0.35)
        v += step
    xs.append(hi)
    return xs


def build_terrain(mat, c):
    xs = axis_samples(-600, 600, [(-55, 45)], 0.3, 7.0)
    ys = axis_samples(-300, 800, [(-38, 22), (180, 236)], 0.3, 7.0)
    nx, ny = len(xs), len(ys)
    print('terrain verts', nx * ny)
    me = bpy.data.meshes.new('Terrain')
    verts = [(x, y, terrain_height(x, y)) for y in ys for x in xs]
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('Terrain', me)
    c.objects.link(ob)
    me.materials.append(mat)

    # vertex groups for grass and pebbles
    vg_grass = ob.vertex_groups.new(name='grass')
    vg_peb = ob.vertex_groups.new(name='pebbles')
    gi, gw, pi_, pw = [], [], [], []
    for idx, (x, y, z) in enumerate(verts):
        dgun = math.hypot(x, y + 3)
        n = noise.fractal(Vector((x / 6.0, y / 6.0, 2.0)), 0.6, 2.0, 3)
        near1 = (-60 < x < 50 and -40 < y < 40)
        near2 = (-70 < x < 30 and 170 < y < 204)
        if near1 or near2:
            g = smoothstep(14.0, 24.0, dgun + 5 * n)
            if 199.5 < y < 227:
                g *= 0.4 * (1 - smoothstep(201.0, 203.0, y))
            g *= smoothstep(-0.15, 0.25, n + 0.2)
            if g > 0.02:
                gi.append(idx)
                gw.append(g)
        if near1 or near2 or (180 < y < 226 and -40 < x < 30):
            pw_ = 0.15 + 0.85 * (1 - smoothstep(8.0, 22.0, dgun))
            if 196 < y < 226:
                pw_ = 0.6
            pi_.append(idx)
            pw.append(pw_)
    for i, w in zip(gi, gw):
        vg_grass.add([i], w, 'REPLACE')
    for i, w in zip(pi_, pw):
        vg_peb.add([i], w, 'REPLACE')
    return ob


def scatter_hair(ob, name, vgroup, count, mat_index, kind, length=0.35, instance_col=None,
                 size=1.0, size_rand=0.5, seed=0, children=0):
    ps_mod = ob.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = ps_mod.particle_system
    ps.seed = seed
    s = ps.settings
    s.type = 'HAIR'
    s.count = count
    s.use_advanced_hair = True
    s.emit_from = 'FACE'
    s.distribution = 'RAND'
    s.use_emit_random = True
    ps.vertex_group_density = vgroup
    if kind == 'grass':
        s.hair_length = length
        s.render_type = 'PATH'
        s.material = mat_index
        s.root_radius = 0.0025 / 0.0025
        s.radius_scale = 0.0035
        s.tip_radius = 0.0
        s.use_rotations = True
        s.rotation_mode = 'NOR'
        s.normal_factor = 1.0
        s.factor_random = 0.6
        s.child_type = 'INTERPOLATED' if children else 'NONE'
        s.rendered_child_count = children
        s.child_percent = children
        s.child_radius = 0.06
        s.child_length = 1.0
        s.child_length_threshold = 0.5
        s.roughness_1 = 0.03
        s.roughness_endpoint = 0.04
        s.roughness_2 = 0.03
        s.clump_factor = 0.15
        s.kink = 'NO'
        s.display_step = 3
        s.render_step = 3
        s.hair_step = 4
    else:
        s.render_type = 'COLLECTION'
        s.instance_collection = instance_col
        s.use_collection_pick_random = True
        s.particle_size = size
        s.size_random = size_rand
        s.use_rotations = True
        s.rotation_mode = 'NOR'
        s.phase_factor_random = 2.0
        s.rotation_factor_random = 0.8
        s.hair_length = 0.01
    return ps


# =============================================================== walls
def crenellate(bm, x0, x1, y_front, z_top, axis='X', thick=0.8, merlon=1.25, gap=0.95, h=1.7, seed=0,
               missing=0.12):
    r = rng(seed)
    L = x1 - x0
    n = int(L / (merlon + gap))
    for i in range(n):
        if r.random() < missing:
            continue
        cx = x0 + gap * 0.5 + merlon * 0.5 + i * (merlon + gap)
        hh = h * (0.75 + 0.25 * r.random()) if r.random() < 0.2 else h
        if axis == 'X':
            bm_box(bm, (cx, y_front + thick / 2, z_top + hh / 2), (merlon, thick, hh))
        else:
            bm_box(bm, (y_front + thick / 2, cx, z_top + hh / 2), (thick, merlon, hh))


def build_walls(mat, c_walls, mat_open):
    base = 0.75
    X0, X1 = -560, 560
    # ---- inner wall
    bm = bmesh.new()
    IW_Y0, IW_Y1, IW_H = 255.0, 260.0, 12.5
    bm_box(bm, ((X0 + X1) / 2, (IW_Y0 + IW_Y1) / 2, base + IW_H / 2 - 1), (X1 - X0, IW_Y1 - IW_Y0, IW_H + 2))
    crenellate(bm, X0, X1, IW_Y0, base + IW_H, seed=1)
    towers = []
    for k in range(-9, 10):
        tx = 30 + 60 * k + rng(k).uniform(-6, 6)
        if not (X0 + 10 < tx < X1 - 10):
            continue
        r = rng(100 + k)
        tw = r.uniform(9.5, 11.0)
        th = r.uniform(18.0, 20.5)
        depth = r.uniform(7.5, 9.0)
        y0 = IW_Y0 - depth
        bm_box(bm, (tx, (y0 + IW_Y1) / 2, base + th / 2 - 1), (tw, IW_Y1 - y0, th + 2))
        crenellate(bm, tx - tw / 2, tx + tw / 2, y0, base + th, seed=200 + k, merlon=1.1, gap=0.85,
                   missing=0.18)
        crenellate(bm, y0, IW_Y0, tx - tw / 2, base + th, axis='Y', seed=300 + k, missing=0.2)
        crenellate(bm, y0, IW_Y0, tx + tw / 2 - 0.8, base + th, axis='Y', seed=400 + k, missing=0.2)
        towers.append((tx, y0, tw, th))
    inner = obj_from_bmesh('InnerWall', bm, mat, c_walls)
    add_bevel(inner, 0.04, 1)

    # windows on inner towers (arched openings read as dark recesses)
    bm = bmesh.new()
    for tx, y0, tw, th in towers:
        for dx in (-2.3, 2.3):
            bm_box(bm, (tx + dx, y0 - 0.02, base + th - 5.5), (1.3, 0.1, 2.4))
            bm_box(bm, (tx + dx, y0 - 0.02, base + th - 4.3), (0.9, 0.1, 0.5))
        bm_box(bm, (tx, y0 - 0.02, base + th - 10.5), (0.35, 0.1, 1.6))
    obj_from_bmesh('InnerTowerOpenings', bm, mat_open, c_walls)

    # ---- outer wall (lower), towers alternate with inner towers
    bm = bmesh.new()
    OW_Y0, OW_Y1, OW_H = 235.0, 237.6, 8.6
    bm_box(bm, ((X0 + X1) / 2, (OW_Y0 + OW_Y1) / 2, base + OW_H / 2 - 1), (X1 - X0, OW_Y1 - OW_Y0, OW_H + 2))
    crenellate(bm, X0, X1, OW_Y0, base + OW_H, thick=0.6, merlon=1.1, gap=0.9, h=1.5, seed=5, missing=0.15)
    for k in range(-9, 10):
        tx = 60 * k
        if k == 0 or not (X0 + 10 < tx < X1 - 10):
            continue
        r = rng(500 + k)
        tw, th, depth = r.uniform(7, 8.5), r.uniform(11.5, 13), r.uniform(5, 6.5)
        y0 = OW_Y0 - depth
        bm_box(bm, (tx, (y0 + OW_Y1) / 2, base + th / 2 - 1), (tw, OW_Y1 - y0, th + 2))
        crenellate(bm, tx - tw / 2, tx + tw / 2, y0, base + th, thick=0.6, merlon=1.0, gap=0.85, h=1.5,
                   seed=600 + k, missing=0.2)
    outer = obj_from_bmesh('OuterWall', bm, mat, c_walls)
    add_bevel(outer, 0.04, 1)

    # ---- the target tower (x=0) as its own object so it can be breached
    bm = bmesh.new()
    tw, th, y0 = 8.4, 12.4, 229.4
    bm_box(bm, (0, (y0 + OW_Y1) / 2, base + th / 2 - 1), (tw, OW_Y1 - y0, th + 2))
    target = obj_from_bmesh('TargetTower', bm, mat, c_walls)
    add_bevel(target, 0.05, 1)
    bm = bmesh.new()
    crenellate(bm, -tw / 2, tw / 2, y0, base + th, thick=0.6, merlon=1.0, gap=0.8, h=1.5, seed=77,
               missing=0.0)
    crenellate(bm, y0, OW_Y0, -tw / 2, base + th, axis='Y', thick=0.6, merlon=1.0, gap=0.8, h=1.5,
               seed=78, missing=0.1)
    merlons = obj_from_bmesh('TargetTowerMerlons', bm, mat, c_walls)
    add_bevel(merlons, 0.04, 1)
    # arrow slits on the target tower
    bm = bmesh.new()
    for dx in (-2.2, 2.2):
        bm_box(bm, (dx, y0 - 0.03, base + 8.2), (0.22, 0.1, 1.5))
    bm_box(bm, (0, y0 - 0.03, base + 3.2), (0.22, 0.1, 1.3))
    obj_from_bmesh('TargetTowerSlits', bm, mat_open, c_walls)

    # ---- low breastwork on the inner (city) lip of the moat
    bm = bmesh.new()
    bm_box(bm, (0, 225.3, base + 0.4), (X1 - X0, 1.3, 2.8))
    crenellate(bm, X0, X1, 224.65, base + 1.8, thick=0.5, merlon=0.9, gap=0.6, h=0.9, seed=9, missing=0.3)
    bw = obj_from_bmesh('MoatBreastwork', bm, mat, c_walls)
    add_bevel(bw, 0.03, 1)
    return target, merlons


# =============================================================== the bombard
def build_bombard(c, m_bronze, m_oak, m_iron):
    # profile: (radius, axial from breech).  8.2 m long, bore 0.74 m
    P = []
    s0 = -4.1
    outer = [
        (0.00, 0.00), (0.20, 0.01), (0.34, 0.06), (0.42, 0.16), (0.45, 0.30),
        (0.50, 0.32), (0.50, 0.42), (0.455, 0.44), (0.455, 1.40), (0.50, 1.42), (0.50, 1.55),
        (0.455, 1.57), (0.455, 2.75), (0.50, 2.77), (0.50, 2.92), (0.47, 2.95),
        (0.56, 3.10), (0.61, 3.22), (0.62, 3.30), (0.66, 3.32), (0.66, 3.50), (0.615, 3.52),
        (0.60, 5.30), (0.645, 5.32), (0.645, 5.50), (0.60, 5.52), (0.585, 7.55),
        (0.62, 7.62), (0.645, 7.75), (0.645, 8.02), (0.665, 8.05), (0.665, 8.17), (0.60, 8.20),
    ]
    inner = [(0.37, 8.20), (0.37, 3.35), (0.30, 3.25), (0.20, 3.15), (0.20, 0.70), (0.0, 0.62)]
    for r, s in outer + inner:
        P.append((r, s0 + s))
    gun = lathe('Bombard', P, 72, 'Y', m_bronze)
    gun.location = (0, 0, GUN_AXIS_Z)
    gun.rotation_euler = (math.radians(1.2), 0, 0)
    c.objects.link(gun) if gun.name not in c.objects else None
    for uc in list(gun.users_collection):
        if uc != c:
            uc.objects.unlink(gun)
    # touch hole
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=16, radius1=0.05, radius2=0.04, depth=0.02,
                          cap_ends=True, matrix=__import__('mathutils').Matrix.Translation((0, -3.5 + 4.1 - 4.1, 0.462)))
    th = obj_from_bmesh('TouchHole', bm, mat_dark_opening(), c)
    th.parent = gun

    # timber bed
    bm = bmesh.new()
    for x in (-0.62, 0.62):
        bm_box(bm, (x, 0.0, 0.32), (0.42, 9.4, 0.4))
    for y in (-3.4, -1.6, 0.4, 2.4, 3.9):
        bm_box(bm, (0, y, 0.08), (3.4, 0.38, 0.32))
    for y in (-2.9, -0.4, 2.0, 3.6):
        for x in (-1, 1):
            bm_box(bm, (x * 0.86, y, 0.78), (0.32, 0.5, 0.65))
    bed = obj_from_bmesh('TimberBed', bm, m_oak, c)
    add_bevel(bed, 0.035, 2)

    # breech abutment: driven posts + stacked beams + earth behind
    bm = bmesh.new()
    for i, x in enumerate((-1.6, -0.8, 0, 0.8, 1.6)):
        bm_box(bm, (x, -4.75, 0.45), (0.36, 0.36, 1.9))
    for k in range(3):
        bm_box(bm, (0, -4.45, 0.3 + k * 0.4), (3.8, 0.4, 0.38))
    for x in (-1.3, 1.3):
        bm_box(bm, (x, -5.6, 0.55), (0.3, 2.1, 0.3), 0.0)
    ab = obj_from_bmesh('Abutment', bm, m_oak, c)
    add_bevel(ab, 0.04, 2)
    mound = rock_mesh('AbutmentEarth', 1.0, seed=3, rough=0.25, subdiv=4, squash=(3.2, 1.6, 1.25))
    mound.location = (0, -6.6, -0.15)
    mound.data.materials.append(bpy.data.materials['Ground'])
    link_to(mound, c)

    return gun


def build_battery(c, m_oak, m_wood_old, m_ball, m_iron):
    # earthworks flanking the embrasure
    for i, (x, y, sx, sy, sz) in enumerate([(-7.0, 10.5, 4.8, 2.4, 1.9), (7.2, 10.8, 5.0, 2.5, 2.0),
                                             (-14.5, 12.0, 5.5, 2.6, 1.7), (15.0, 12.5, 5.0, 2.4, 1.6)]):
        mo = rock_mesh(f'Earthwork{i}', 1.0, seed=10 + i, rough=0.3, subdiv=4, squash=(sx, sy, sz))
        mo.location = (x, y, -0.4)
        mo.data.materials.append(bpy.data.materials['Ground'])
        link_to(mo, c)
    # wooden mantlets (screens) on posts, either side of the line of fire
    for sgn in (-1, 1):
        bm = bmesh.new()
        for k in range(9):
            bm_box(bm, (sgn * (3.0 + k * 0.33), 8.7, 1.5 + rng(k).uniform(-0.05, 0.05)),
                   (0.31, 0.12, 2.9 + rng(k + 9).uniform(-0.15, 0.1)))
        bm_box(bm, (sgn * 4.3, 8.6, 2.4), (3.2, 0.12, 0.2))
        bm_box(bm, (sgn * 4.3, 8.6, 0.8), (3.2, 0.12, 0.2))
        bm_box(bm, (sgn * 3.2, 9.4, 1.0), (0.14, 1.6, 0.14))
        mt = obj_from_bmesh(f'Mantlet{sgn}', bm, m_wood_old, c)
        mt.rotation_euler = (math.radians(-8), 0, 0)
        add_bevel(mt, 0.015, 1)

    # palisade of sharpened stakes along the Ottoman front
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=7, radius1=0.11, radius2=0.09, depth=2.6, cap_ends=True,
                          matrix=__import__('mathutils').Matrix.Translation((0, 0, 1.3)))
    bmesh.ops.create_cone(bm, segments=7, radius1=0.09, radius2=0.0, depth=0.35, cap_ends=True,
                          matrix=__import__('mathutils').Matrix.Translation((0, 0, 2.77)))
    stake_me = bpy.data.meshes.new('Stake')
    bm.to_mesh(stake_me)
    bm.free()
    stake_me.materials.append(m_wood_old)
    r = rng(42)
    x = -180.0
    while x < 180:
        x += r.uniform(0.24, 0.3)
        if abs(x) < 7.0:
            continue
        y = 36.0 + 1.5 * math.sin(x / 23.0) + r.uniform(-0.1, 0.1)
        st = bpy.data.objects.new('Stake', stake_me)
        st.location = (x, y, terrain_height(x, y) - 0.3)
        st.rotation_euler = (math.radians(r.uniform(-6, 4)), math.radians(r.uniform(-4, 4)), r.uniform(0, 6))
        st.scale = (1, 1, r.uniform(0.85, 1.1))
        c.objects.link(st)

    # stone shot piles (foreground)
    balls = []

    def pile(cx, cy, layout, seed):
        rr = rng(seed)
        for (dx, dy, dz) in layout:
            b = rock_mesh('StoneShot', 0.36, seed=rr.randint(0, 999), rough=0.035, subdiv=4)
            b.data.materials.append(m_ball)
            b.location = (cx + dx, cy + dy, dz + 0.31)
            b.rotation_euler = (rr.uniform(0, 6), rr.uniform(0, 6), rr.uniform(0, 6))
            link_to(b, c)
            balls.append(b)
    pile(-4.35, -11.3, [(0, 0, 0), (0.74, 0.05, 0), (0.37, 0.64, 0), (-0.4, 0.66, 0), (0.36, 0.25, 0.58),
                       (1.6, -0.4, 0), (-0.9, -0.5, 0)], 1)
    pile(2.4, -6.5, [(0, 0, 0), (0.75, 0, 0), (0.37, 0.65, 0), (0.37, 0.22, 0.6)], 2)

    # powder casks (wooden staves, hoops)
    prof = [(0.0, 0.0), (0.27, 0.0), (0.27, 0.02), (0.305, 0.12), (0.33, 0.32), (0.335, 0.4),
            (0.33, 0.48), (0.305, 0.68), (0.27, 0.78), (0.27, 0.8), (0.0, 0.8)]
    for i, (x, y, rz, tip) in enumerate([(-2.9, -9.3, 0.2, 0), (-3.55, -8.8, 1.0, 0), (-3.1, -8.4, 0.5, 0),
                                         (3.3, -9.6, 0.0, 1)]):
        cask = lathe('PowderCask', prof, 32, 'Z', m_oak)
        cask.location = (x, y, 0.0 if not tip else 0.33)
        cask.rotation_euler = (math.radians(90) if tip else 0, 0, rz)
        link_to(cask, c)
        for hz in (0.1, 0.24, 0.56, 0.7):
            rad = 0.309 + (0.025 if 0.2 < hz < 0.6 else 0.0)
            hoop = lathe('Hoop', [(rad, hz - 0.03), (rad + 0.012, hz - 0.03), (rad + 0.012, hz + 0.03),
                                  (rad, hz + 0.03)], 32, 'Z', m_wood_old)
            hoop.parent = cask
            link_to(hoop, c)

    # rammer / sponge pole lying in the mud
    pole = lathe('Rammer', [(0.0, 0.0), (0.05, 0.0), (0.05, 6.0), (0.0, 6.0)], 12, 'Z', m_wood_old)
    pole.location = (-1.65, -10.6, 0.07)
    pole.rotation_euler = (math.radians(90), 0, math.radians(-12))
    link_to(pole, c)
    head = lathe('RammerHead', [(0.0, 0.0), (0.33, 0.0), (0.34, 0.25), (0.0, 0.25)], 24, 'Z', m_oak)
    head.parent = pole
    head.location = (0, 0, 6.0)
    link_to(head, c)
    return balls


def build_brazier(c, m_iron):
    bm = bmesh.new()
    import mathutils
    for a in range(3):
        ang = a * 2 * math.pi / 3
        m = (mathutils.Matrix.Translation((0.28 * math.cos(ang), 0.28 * math.sin(ang), 0.45)) @
             mathutils.Matrix.Rotation(0.25, 4, mathutils.Vector((-math.sin(ang), math.cos(ang), 0))))
        bmesh.ops.create_cone(bm, segments=6, radius1=0.02, radius2=0.02, depth=0.95, cap_ends=True, matrix=m)
    brz = obj_from_bmesh('BrazierLegs', bm, m_iron, c)
    bowl = lathe('BrazierBowl', [(0.0, 0.85), (0.18, 0.86), (0.36, 0.98), (0.38, 1.08), (0.365, 1.08),
                                 (0.34, 1.0), (0.17, 0.9), (0.0, 0.89)], 32, 'Z', m_iron)
    link_to(bowl, c)
    coal_m, coal_e = mat_emit('Embers', (1.0, 0.28, 0.05, 1), 6.0)
    # embers: emissive lumpy disc, with flicker
    coals = rock_mesh('Coals', 0.3, seed=5, rough=0.35, subdiv=3, squash=(1, 1, 0.25))
    coals.location = (0, 0, 1.0)
    coals.data.materials.append(coal_m)
    link_to(coals, c)
    grp = bpy.data.objects.new('Brazier', None)
    c.objects.link(grp)
    for o in (brz, bowl, coals):
        o.parent = grp
    grp.location = (-4.3, -3.0, 0.0)
    ld = bpy.data.lights.new('BrazierLight', 'POINT')
    ld.color = blackbody_rgb(1900)
    ld.shadow_soft_size = 0.25
    li = bpy.data.objects.new('BrazierLight', ld)
    li.location = (-4.3, -3.0, 1.35)
    c.objects.link(li)
    r = rng(7)
    for f in range(1, SHOT1[1] + 2, 2):
        ld.energy = 260 * (0.8 + 0.4 * r.random())
        ld.keyframe_insert('energy', frame=f)
        coal_e.inputs['Strength'].default_value = 5.0 * (0.8 + 0.4 * r.random())
        coal_e.inputs['Strength'].keyframe_insert('default_value', frame=f)
    return grp


# =============================================================== smoke puffs
class Puff:
    def __init__(self, name, color, f0, p0, p1, r0, r1, travel_k=4.0, travel_frames=30,
                 dens=1.0, fade_frames=180, emit=0.0, emit_frames=4, squash=(1, 1, 1), rise=0.0,
                 wind=(0.025, 0.0), seed=0, anis=0.35, temp=1500.0, grow_frames=None, end=None,
                 dens_ramp=1):
        self.mat = mat_puff('Smoke_' + name, color, anis=anis, density_scale=0.0, temp=temp)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.25)
        self.ob = obj_from_bmesh('Puff_' + name, bm, self.mat)
        self.ob.visible_shadow = True
        ob = self.ob
        end = end or (SHOT1[1] + 4 if f0 < SHOT2[0] else SHOT2[1] + 4)
        grow_frames = grow_frames or travel_frames * 2
        p0, p1 = Vector(p0), Vector(p1)
        r = rng(seed)
        ob.rotation_euler = (r.uniform(0, 6), r.uniform(0, 6), r.uniform(0, 6))
        w0 = r.uniform(0, 100)
        for f in range(f0 - 1, end + 1):
            t = f - f0
            if t < 0:
                ob.location = p0
                ob.scale = (0.001, 0.001, 0.001)
                d = 0.0
                e = 0.0
                w = w0
            else:
                a = ease_out(t / travel_frames, travel_k)
                pos = p0.lerp(p1, a)
                pos += Vector((wind[0] * t, wind[1] * t, rise * ease_out(t / 90.0, 1.5)))
                rad = r0 + (r1 - r0) * ease_out(t / grow_frames, 3.0)
                ob.location = pos
                ob.scale = (rad * squash[0], rad * squash[1], rad * squash[2])
                d = dens * min(1.0, (t + 1) / dens_ramp) * math.exp(-t / fade_frames)
                e = emit * math.exp(-t / max(0.5, emit_frames / 2.5)) if t < emit_frames * 3 else 0.0
                w = w0 + 0.035 * t + 0.25 * ease_out(t / 20.0, 3.0)
            ob.keyframe_insert('location', frame=f)
            ob.keyframe_insert('scale', frame=f)
            key_node_value(self.mat, 'DENS', f, d)
            key_node_value(self.mat, 'EMIT', f, e)
            key_node_value(self.mat, 'EVOLVE', f, w)
            key_node_value(self.mat, 'EDGE', f, 0.25 * max(0.0, t) / max(1.0, fade_frames))
        linear_all(ob)
        linear_all(self.mat.node_tree)
        # hide entirely outside its life to save render time
        ob.hide_render = True
        ob.keyframe_insert('hide_render', frame=0)
        ob.hide_render = False
        ob.keyframe_insert('hide_render', frame=f0)
        ob.hide_render = True
        ob.keyframe_insert('hide_render', frame=end + 1)
        from lib import fcurves_of
        for fc in fcurves_of(ob.animation_data):
            if fc.data_path == 'hide_render':
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'


POWDER = (0.74, 0.72, 0.69, 1)
POWDER_DARK = (0.52, 0.50, 0.47, 1)
DUST = (0.62, 0.53, 0.42, 1)


def build_muzzle_blast(c):
    puffs = []
    mz = MUZZLE
    # flash core
    puffs.append(Puff('flash', POWDER, F_FIRE, mz + Vector((0, 0.8, 0)), mz + Vector((0, 4.5, 0.2)),
                      0.6, 3.2, travel_frames=5, dens=4.0, fade_frames=70, emit=60.0, emit_frames=2,
                      seed=1, temp=1700))
    r = rng(3)
    # forward jet that balloons into the main cloud
    for i in range(9):
        dist = 3.0 + 5.0 * (i ** 0.95)
        lat = r.uniform(-1.0, 1.0) * (0.4 + 0.25 * i)
        p1 = mz + Vector((lat, dist, r.uniform(-0.2, 0.6) + 0.12 * i))
        puffs.append(Puff(f'jet{i}', POWDER if i % 3 else POWDER_DARK, F_FIRE + i // 3, mz + Vector((0, 0.5, 0)), p1,
                          0.5 + 0.1 * i, 2.0 + 0.55 * i, travel_frames=10 + 2 * i, travel_k=3.5,
                          dens=7.0 if i < 4 else 5.0, fade_frames=170, emit=(14.0 if i < 2 else 0.0), emit_frames=2,
                          rise=1.0 + 0.2 * i, seed=10 + i, temp=1500))
    # ground blast: dust kicked out radially under the muzzle
    for i in range(7):
        ang = math.radians(-60 + i * 30)
        dirv = Vector((math.sin(ang), math.cos(ang), 0))
        p0 = Vector((mz.x, mz.y + 0.5, 0.35))
        p1 = p0 + dirv * r.uniform(5.0, 8.0) + Vector((0, 0, 0.3))
        puffs.append(Puff(f'ground{i}', DUST, F_FIRE + 1, p0, p1, 0.4, r.uniform(1.8, 2.6),
                          travel_frames=14, dens=3.0, fade_frames=120, squash=(1.2, 1.2, 0.55),
                          rise=0.8, seed=30 + i, anis=0.5))
    # breech/touch-hole vent and smoke rolling back over the gun toward camera
    th = TOUCH_HOLE
    puffs.append(Puff('vent', POWDER, F_FIRE, th, th + Vector((0.1, -0.3, 1.6)), 0.15, 1.1,
                      travel_frames=12, dens=5.0, fade_frames=90, emit=6, emit_frames=2, seed=40))
    for i, (p1, rr) in enumerate([((-1.5, -1.5, 2.4), 3.2), ((1.8, -3.5, 2.0), 3.6), ((-3.5, -6.5, 2.2), 4.2)]):
        puffs.append(Puff(f'rollback{i}', POWDER, F_FIRE + 8 + 6 * i, mz + Vector((0, 1.0, 0.8)), Vector(p1),
                          1.2, rr, travel_frames=55, travel_k=2.2, dens=2.5, fade_frames=200,
                          dens_ramp=12, seed=50 + i, rise=0.6))
    # recoil dust under the bed
    puffs.append(Puff('recoil', DUST, F_FIRE + 1, (0.0, -4.0, 0.3), (0.3, -6.0, 0.5), 0.3, 1.8,
                      travel_frames=14, dens=2.5, fade_frames=80, squash=(1.6, 1.0, 0.5), seed=60, anis=0.5))
    # priming flash at the touch hole
    puffs.append(Puff('prime', POWDER, F_TOUCH + 1, th + Vector((0, 0, 0.05)), th + Vector((0.05, -0.05, 0.8)),
                      0.05, 0.42, travel_frames=10, dens=6.0, fade_frames=40, emit=40, emit_frames=3,
                      seed=70, temp=1900))
    for p in puffs:
        link_to(p.ob, c)

    # light of the blast
    ld = bpy.data.lights.new('MuzzleFlash', 'POINT')
    ld.color = blackbody_rgb(2100)
    ld.shadow_soft_size = 1.5
    li = bpy.data.objects.new('MuzzleFlash', ld)
    li.location = mz + Vector((0, 2.0, 0.3))
    c.objects.link(li)
    for f, e in [(F_FIRE - 1, 0), (F_FIRE, 420000), (F_FIRE + 1, 260000), (F_FIRE + 2, 90000),
                 (F_FIRE + 4, 22000), (F_FIRE + 7, 4000), (F_FIRE + 12, 0)]:
        ld.energy = e
        ld.keyframe_insert('energy', frame=f)
    pd = bpy.data.lights.new('PrimeFlash', 'POINT')
    pd.color = blackbody_rgb(1900)
    pd.shadow_soft_size = 0.1
    pl = bpy.data.objects.new('PrimeFlash', pd)
    pl.location = TOUCH_HOLE + Vector((0, 0, 0.3))
    c.objects.link(pl)
    for f, e in [(F_TOUCH, 0), (F_TOUCH + 1, 900), (F_TOUCH + 2, 600), (F_TOUCH + 4, 150), (F_TOUCH + 7, 30),
                 (F_FIRE - 1, 10), (F_FIRE, 0)]:
        pd.energy = e
        pd.keyframe_insert('energy', frame=f)
    linear_all(ld)
    linear_all(pd)
    return puffs


def build_linstock(c, m_wood, m_iron):
    """Linstock entering frame from the right - held by an unseen gunner."""
    grp = bpy.data.objects.new('Linstock', None)
    c.objects.link(grp)
    shaft = lathe('LinstockShaft', [(0.0, 0.0), (0.022, 0.0), (0.02, 2.1), (0.0, 2.1)], 12, 'Z', m_wood)
    shaft.parent = grp
    link_to(shaft, c)
    fork = lathe('LinstockFork', [(0.0, 2.1), (0.012, 2.1), (0.008, 2.28), (0.0, 2.28)], 8, 'Z', m_iron)
    fork.parent = grp
    link_to(fork, c)
    em, ee = mat_emit('SlowMatchEmber', (1.0, 0.32, 0.06, 1), 60.0)
    ember = rock_mesh('MatchEmber', 0.016, seed=2, rough=0.2, subdiv=2)
    ember.data.materials.append(em)
    ember.location = (0, 0, 2.29)
    ember.parent = grp
    link_to(ember, c)
    ld = bpy.data.lights.new('MatchGlow', 'POINT')
    ld.energy = 1.8
    ld.color = blackbody_rgb(1800)
    ld.shadow_soft_size = 0.02
    gl = bpy.data.objects.new('MatchGlow', ld)
    gl.parent = grp
    gl.location = (0, 0, 2.31)
    c.objects.link(gl)
    # thin wisp of smoke from the slow match
    wisp = Puff('matchwisp', POWDER, 120, (0, 0, 0), (0, 0, 0.4), 0.05, 0.12, travel_frames=60, dens=0.6,
                fade_frames=600, rise=0.4, wind=(0.0, 0.0), seed=91, end=F_FIRE + 6)
    wisp.ob.parent = ember
    link_to(wisp.ob, c)

    # pose: the pole's tip (local +Z * 2.29) travels to the touch hole
    tip_off = 2.29
    import mathutils
    start_tip = TOUCH_HOLE + Vector((1.6, -1.2, 1.4))
    hold_tip = TOUCH_HOLE + Vector((0.18, -0.12, 0.32))
    touch_tip = TOUCH_HOLE + Vector((0.0, 0.0, 0.02))
    away_tip = TOUCH_HOLE + Vector((0.9, -0.7, 1.4))
    pole_dir = Vector((-0.55, 0.32, -0.77)).normalized()   # direction butt -> tip

    def place(f, tip, extra_tilt=0.0):
        d = (pole_dir + Vector((0, 0, extra_tilt))).normalized()
        grp.location = tip - d * tip_off
        grp.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        grp.keyframe_insert('location', frame=f)
        grp.keyframe_insert('rotation_euler', frame=f)

    place(1, start_tip + Vector((2.5, -2.0, 1.5)))
    place(148, start_tip + Vector((1.8, -1.6, 1.0)))
    place(168, start_tip)
    place(184, hold_tip, 0.02)           # hovering - the breath
    place(191, hold_tip + Vector((0.01, 0, 0.03)), 0.02)
    place(F_TOUCH, touch_tip)
    place(F_TOUCH + 4, touch_tip + Vector((0.08, -0.06, 0.18)))
    place(F_FIRE + 6, away_tip)
    place(SHOT1[1], away_tip + Vector((1.2, -1.0, 0.6)))
    from lib import fcurves_of
    for fc in fcurves_of(grp.animation_data):
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
    return grp


# =============================================================== impact (shot 2)
def build_impact(c, target, merlons, m_rubble, m_wall, m_ball):
    # crater: boolean cutter that appears at impact
    cut = rock_mesh('CraterCutter', 1.0, seed=8, rough=0.45, subdiv=4, squash=(1.35, 1.0, 1.2))
    cut.location = IMPACT + Vector((0, 0.35, 0))
    cut.data.materials.append(m_rubble)
    link_to(cut, c)
    cut.hide_render = True
    cut.display_type = 'WIRE'
    for f, s in [(F_IMPACT - 1, 0.001), (F_IMPACT, 1.0), (F_IMPACT + 1, 1.45), (F_IMPACT + 3, 1.6)]:
        cut.scale = (s, s, s)
        cut.keyframe_insert('scale', frame=f)
    linear_all(cut)
    b = target.modifiers.new('Breach', 'BOOLEAN')
    b.operation = 'DIFFERENCE'
    b.object = cut
    b.solver = 'EXACT'
    try:
        b.material_mode = 'TRANSFER'
    except Exception:
        pass
    target.data.materials.append(m_rubble)
    # Move bevel after boolean
    target.modifiers.move(1, 0) if target.modifiers[0].name == 'Bevel' and False else None

    # in-flight stone ball (motion blurred streak)
    ball = rock_mesh('BallInFlight', 0.36, seed=31, rough=0.03, subdiv=3)
    ball.data.materials.append(m_ball)
    link_to(ball, c)
    start = Vector((0.0, 120.0, 6.0))
    for f, pos, vis in [(F_IMPACT - 5, start, False), (F_IMPACT - 4, start, True),
                        (F_IMPACT, IMPACT + Vector((0, -0.2, 0)), True), (F_IMPACT + 1, IMPACT, False)]:
        ball.location = pos
        ball.keyframe_insert('location', frame=f)
        ball.hide_render = not vis
        ball.keyframe_insert('hide_render', frame=f)
    linear_all(ball)

    # debris: masonry chunks (limestone + brick) thrown out of the face
    chunks = bpy.data.collections.new('DebrisChunks')
    bpy.context.scene.collection.children.link(chunks)
    for i in range(10):
        ck = rock_mesh(f'Chunk{i}', 1.0, seed=100 + i, rough=0.5, subdiv=1,
                       squash=(1.0, rng(i).uniform(0.5, 1.0), rng(i + 5).uniform(0.4, 0.9)))
        ck.data.materials.append(m_wall if i < 6 else m_rubble)
        link_to(ck, chunks)
        ck.location = (0, 0, -50)
    for i in range(3):   # brick fragments
        bm = bmesh.new()
        bm_box(bm, (0, 0, 0), (1.0, 0.5, 0.14))
        bk = obj_from_bmesh(f'BrickFrag{i}', bm, m_rubble, chunks)
        bk.location = (0, 0, -50)
    chunks.hide_render = False
    em = bpy.data.objects.new('DebrisEmitter', None)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=0.9)
    emit = obj_from_bmesh('DebrisEmitter', bm, None, c)
    emit.location = IMPACT + Vector((0, -0.4, 0))
    emit.rotation_euler = (math.radians(90), 0, 0)   # normal -> -Y
    emit.hide_render = True
    ps_mod = emit.modifiers.new('Debris', 'PARTICLE_SYSTEM')
    s = ps_mod.particle_system.settings
    s.count = 650
    s.frame_start = F_IMPACT
    s.frame_end = F_IMPACT + 3
    s.lifetime = 200
    s.emit_from = 'FACE'
    s.normal_factor = -13.0
    s.factor_random = 9.0
    s.object_align_factor = (0, 0, 3.0)
    s.render_type = 'COLLECTION'
    s.instance_collection = chunks
    s.use_collection_pick_random = True
    s.particle_size = 0.11
    s.size_random = 0.85
    s.use_rotations = True
    s.rotation_mode = 'VEL'
    s.rotation_factor_random = 1.0
    s.angular_velocity_mode = 'RAND'
    s.angular_velocity_factor = 8.0
    s.use_dynamic_rotation = True
    s.damping = 0.02
    s.physics_type = 'NEWTON'
    s.timestep = 1 / 24 / 2
    ps_mod.particle_system.point_cache.frame_start = F_IMPACT - 2
    ps_mod.particle_system.point_cache.frame_end = SHOT2[1] + 2
    # make the hidden chunk collection not render on its own
    chunks.hide_render = True

    # terrain & walls collide
    for ob in (bpy.data.objects['Terrain'], bpy.data.objects['MoatBreastwork']):
        cm = ob.modifiers.new('Collision', 'COLLISION')
        ob.collision.damping_factor = 0.6
        ob.collision.friction_factor = 0.7
        ob.collision.damping_random = 0.3

    # merlons toppling off the tower top - secondary action
    fall = bpy.data.objects.new('FallingMerlons', None)
    c.objects.link(fall)
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (1.0, 0.6, 1.5))
    for i, (x0, dx, delay) in enumerate([(-0.9, -0.8, 4), (0.9, 1.4, 9)]):
        mo = obj_from_bmesh(f'Merlon{i}', bm.copy(), m_wall, c)
        add_bevel(mo, 0.04, 1)
        top = Vector((x0, 229.7, 0.75 + 12.4 + 0.75))
        g = 9.81 / (FPS * FPS)
        vx, vy = dx / 40.0, -0.11
        for f in range(F_IMPACT - 1, SHOT2[1] + 1):
            t = max(0, f - (F_IMPACT + delay))
            pos = top + Vector((vx * t, vy * t, -0.5 * g * t * t))
            ground = -4.8  # moat floor approx
            pos.z = max(pos.z, ground)
            mo.location = pos
            spin = min(t * 0.09, 2.2)
            mo.rotation_euler = (-spin, (0.4 if i else -0.3) * spin, 0.1 * spin)
            mo.keyframe_insert('location', frame=f)
            mo.keyframe_insert('rotation_euler', frame=f)
        linear_all(mo)
    bm.free()
    # remove the matching merlons from the static merlon mesh
    me = merlons.data
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = [v for v in bm.verts if v.co.y < 230.4 and v.co.z > 13.0 and (-1.5 < v.co.x < -0.3 or 0.3 < v.co.x < 1.5)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me)
    bm.free()

    # dust: explosion of pulverised mortar and stone
    puffs = []
    r = rng(9)
    base = IMPACT + Vector((0, -0.6, 0))
    for i in range(10):
        dirv = Vector((r.uniform(-1, 1), -r.uniform(0.6, 1.6), r.uniform(-0.3, 1.0))).normalized()
        p1 = base + dirv * r.uniform(4.0, 9.0)
        puffs.append(Puff(f'imp{i}', DUST if i % 3 else (0.72, 0.66, 0.57, 1), F_IMPACT + (i % 3),
                          base, p1, 0.4, r.uniform(2.4, 4.2), travel_frames=16, travel_k=3.8,
                          dens=r.uniform(4.0, 7.0), fade_frames=r.uniform(110, 160),
                          rise=r.uniform(0.5, 2.0), wind=(0.035, -0.01), seed=200 + i, anis=0.55,
                          emit=1.2 if i < 3 else 0, emit_frames=2, temp=1300))
    # falling curtain of dust down the wall face into the moat
    for i in range(5):
        p0 = base + Vector((r.uniform(-1.5, 1.5), -0.8, -1.0))
        p1 = Vector((p0.x + r.uniform(-2, 2), 226.0 + r.uniform(-1, 1), -2.5 + r.uniform(0, 2)))
        puffs.append(Puff(f'curtain{i}', DUST, F_IMPACT + 6 + i * 3, p0, p1, 0.8, r.uniform(2.5, 3.6),
                          travel_frames=40, travel_k=2.0, dens=2.5, fade_frames=150, dens_ramp=6,
                          wind=(0.03, 0.0), seed=300 + i, anis=0.55))
    for p in puffs:
        link_to(p.ob, c)
    return puffs


# =============================================================== cameras
def build_camera(name, lens, fstop):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 7
    cd.clip_start = 0.05
    cd.clip_end = 2000
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    return cam


def shake(f, f0, amp, decay=10.0, freq=1.0, seed=0):
    if f < f0:
        return Vector((0, 0, 0)), 0.0
    t = f - f0
    env = amp * math.exp(-t / decay)
    v = Vector((noise.noise(Vector((t * 0.45 * freq, seed, 0))),
                noise.noise(Vector((t * 0.45 * freq, seed + 7, 3))),
                noise.noise(Vector((t * 0.45 * freq, seed + 13, 9)))))
    roll = env * 0.02 * noise.noise(Vector((t * 0.5, seed + 21, 1)))
    return v * env, roll


def animate_cam1(cam):
    """Low creeping approach past the shot pile -> breath at the breech -> fire."""
    cd = cam.data
    P0, T0 = Vector((-7.4, -16.6, 0.62)), Vector((-2.0, -6.0, 0.9))
    P1, T1 = Vector((-2.65, -7.7, 2.3)), Vector((0.2, 3.0, 1.25))
    P2, T2 = Vector((-2.5, -7.35, 2.26)), Vector((0.15, 2.6, 1.3))
    P3, T3 = Vector((-2.95, -8.3, 2.55)), Vector((0.6, 9.0, 2.6))
    for f in range(SHOT1[0], SHOT1[1] + 1):
        if f <= 150:
            a = ease_io((f - 1) / 149.0)
            # arc: swing outwards slightly mid-move for parallax past the shot pile
            pos = P0.lerp(P1, a) + Vector((-0.6 * math.sin(math.pi * a), 0, 0.15 * math.sin(math.pi * a)))
            tgt = T0.lerp(T1, ease_io(min(1, (f - 1) / 140.0)))
        elif f < F_FIRE:
            a = (f - 150) / (F_FIRE - 150)
            pos = P1.lerp(P2, a * a * (3 - 2 * a))
            tgt = T1.lerp(T2, a)
        else:
            a = ease_out((f - F_FIRE) / 50.0, 2.5)
            pos = P2.lerp(P3, a)
            tgt = T2.lerp(T3, ease_out((f - F_FIRE) / 40.0, 2.0))
        # handheld micro-drift (very subtle)
        drift = Vector((noise.noise(Vector((f * 0.012, 1, 1))), noise.noise(Vector((f * 0.012, 2, 2))),
                        noise.noise(Vector((f * 0.012, 3, 3))))) * 0.03
        sh, roll = shake(f, F_FIRE, 0.12, 7.0, 2.2, 1)
        sh2, roll2 = shake(f, F_TOUCH, 0.004, 4.0, 2.0, 5)
        cam.location = pos + drift + sh + sh2
        d = (tgt + sh * 1.6 - cam.location)
        q = d.to_track_quat('-Z', 'Y').to_euler()
        q.y += roll
        cam.rotation_euler = q
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        # lens: subtle push-in during the breath
        cd.lens = 32.0 if f < 150 else (32.0 + 4.0 * ease_io((f - 150) / (F_FIRE - 150)) if f < F_FIRE else 36.0)
        cd.keyframe_insert('lens', frame=f)
        # focus: shot pile -> breech/touch-hole -> rack to the blast
        if f < 120:
            fd = (Vector((-4.2, -11.2, 0.6)) - cam.location).length if f < 60 else \
                (TOUCH_HOLE - cam.location).length * ease_io((f - 60) / 60) + \
                (Vector((-4.2, -11.2, 0.6)) - cam.location).length * (1 - ease_io((f - 60) / 60))
        elif f < F_FIRE + 2:
            fd = (TOUCH_HOLE - cam.location).length
        else:
            k = ease_io((f - F_FIRE - 2) / 16.0)
            fd = (TOUCH_HOLE - cam.location).length * (1 - k) + 16.0 * k
        cd.dof.focus_distance = fd
        cd.dof.keyframe_insert('focus_distance', frame=f)
    from lib import fcurves_of
    for idb in (cam, cd):
        for fc in fcurves_of(idb.animation_data):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def animate_cam2(cam):
    """Static observer at the moat's edge, slow push, impact shake."""
    cd = cam.data
    P0, P1 = Vector((-27.0, 199.0, 2.0)), Vector((-25.2, 201.0, 2.1))
    T0, T1 = Vector((0.2, 229.5, 7.6)), Vector((0.4, 229.5, 7.0))
    for f in range(SHOT2[0] - 1, SHOT2[1] + 2):
        a = ease_io((f - SHOT2[0]) / (SHOT2[1] - SHOT2[0]))
        pos = P0.lerp(P1, a)
        tgt = T0.lerp(T1, a)
        sh, roll = shake(f, F_IMPACT + 2, 0.05, 9.0, 2.5, 11)
        drift = Vector((noise.noise(Vector((f * 0.01, 4, 1))), noise.noise(Vector((f * 0.01, 5, 2))),
                        noise.noise(Vector((f * 0.01, 6, 3))))) * 0.04
        cam.location = pos + sh + drift
        q = (tgt + sh * 2.0 - cam.location).to_track_quat('-Z', 'Y').to_euler()
        q.y += roll
        cam.rotation_euler = q
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        cd.dof.focus_distance = (IMPACT - cam.location).length
        cd.dof.keyframe_insert('focus_distance', frame=f)
    from lib import fcurves_of
    for idb in (cam, cd):
        for fc in fcurves_of(idb.animation_data):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


def build_cam2_foreground(c, m_wood_old):
    """Foreground for shot 2: broken stakes and tumbled stones on the counterscarp."""
    r = rng(77)
    stake = bpy.data.meshes['Stake']
    for i in range(14):
        x = -24.5 + r.uniform(-3.5, 4.5)
        y = 202.4 + r.uniform(-0.6, 0.9)
        st = bpy.data.objects.new('BrokenStake', stake)
        st.location = (x, y, terrain_height(x, y) - 0.4)
        st.rotation_euler = (math.radians(r.uniform(-25, 15)), math.radians(r.uniform(-20, 20)), r.uniform(0, 6))
        st.scale = (1.1, 1.1, r.uniform(0.35, 0.8))
        c.objects.link(st)


# =============================================================== render setup
def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = 64
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    cy.max_bounces = 6
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 2
    cy.transmission_bounces = 2
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 8
    cy.sample_clamp_indirect = 8.0
    cy.volume_step_rate = 4.0
    cy.volume_max_steps = 256
    cy.light_sampling_threshold = 0.01
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.render.fps = FPS
    sc.frame_start = SHOT1[0]
    sc.frame_end = SHOT2[1]
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 804      # 2.39:1 anamorphic frame
    sc.render.resolution_percentage = 50
    sc.render.film_transparent = False
    vs = sc.view_settings
    try:
        vs.view_transform = 'AgX'
        vs.look = 'AgX - Medium High Contrast'
    except Exception:
        try:
            vs.look = 'Medium High Contrast'
        except Exception as e:
            print('look not set', e)
    vs.exposure = -0.35
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'


# =============================================================== main
def main(out_path):
    clear()
    sc = bpy.context.scene
    c_env = col('Environment')
    c_walls = col('Walls')
    c_gun = col('Battery')
    c_fx = col('FX')

    m_ground = mat_terrain()
    m_wall = mat_wall()
    m_rubble = mat_rubble()
    m_bronze = mat_bronze()
    m_oak = mat_wood('Oak', (0.17, 0.11, 0.07), 'Y')
    m_wood_old = mat_wood('WeatheredWood', (0.10, 0.08, 0.06), 'Z')
    m_ball = mat_stone_ball()
    m_iron = mat_iron()
    m_grass = mat_grass()
    m_open = mat_dark_opening()

    build_world()
    terrain = build_terrain(m_ground, c_env)
    terrain.data.materials.append(m_grass)
    target, merlons = build_walls(m_wall, c_walls, m_open)
    gun = build_bombard(c_gun, m_bronze, m_oak, m_iron)
    build_battery(c_gun, m_oak, m_wood_old, m_ball, m_iron)
    build_brazier(c_gun, m_iron)
    build_linstock(c_gun, m_wood_old, m_iron)
    build_cam2_foreground(c_env, m_wood_old)

    # rocks scattered on the ground
    rocks = bpy.data.collections.new('ScatterRocks')
    sc.collection.children.link(rocks)
    for i in range(6):
        rk = rock_mesh(f'Pebble{i}', 1.0, seed=50 + i, rough=0.45, subdiv=2, squash=(1, 0.8, 0.55))
        rk.data.materials.append(m_rubble if i % 2 else m_ball)
        link_to(rk, rocks)
        rk.location = (0, 0, -60)
    rocks.hide_render = True
    scatter_hair(terrain, 'Pebbles', 'pebbles', 26000, 1, 'inst', instance_col=rocks, size=0.07,
                 size_rand=0.85, seed=4)
    if os.environ.get('NO_GRASS') != '1':
        scatter_hair(terrain, 'Grass', 'grass', 60000, 2, 'grass', length=0.2, seed=5,
                     children=int(os.environ.get('GRASS_CHILDREN', '20')))

    # gun recoil
    for f, dy in [(F_FIRE - 1, 0.0), (F_FIRE, -0.12), (F_FIRE + 2, -0.32), (F_FIRE + 6, -0.36),
                  (F_FIRE + 30, -0.33)]:
        gun.location = (0, dy, GUN_AXIS_Z)
        gun.keyframe_insert('location', frame=f)
    linear_all(gun)

    build_muzzle_blast(c_fx)
    build_impact(c_fx, target, merlons, m_rubble, m_wall, m_ball)

    cam1 = build_camera('CAM_Shot1_Battery', 32, 2.4)
    cam2 = build_camera('CAM_Shot2_Walls', 40, 4.0)
    animate_cam1(cam1)
    animate_cam2(cam2)
    mk1 = sc.timeline_markers.new('SHOT1', frame=SHOT1[0])
    mk1.camera = cam1
    mk2 = sc.timeline_markers.new('SHOT2', frame=SHOT2[0])
    mk2.camera = cam2
    sc.timeline_markers.new('TOUCH', frame=F_TOUCH)
    sc.timeline_markers.new('FIRE', frame=F_FIRE)
    sc.timeline_markers.new('IMPACT', frame=F_IMPACT)
    sc.camera = cam1

    setup_render()
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    print('saved', out_path)


if __name__ == '__main__':
    argv = sys.argv
    out = argv[argv.index('--') + 1] if '--' in argv else (argv[1] if len(argv) > 1 else 'scene.blend')
    main(os.path.abspath(out))
