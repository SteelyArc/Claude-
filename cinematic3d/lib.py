"""Shared helpers for building cinematic scenes with Blender (bpy).

Node-wiring helpers, mesh builders and keyframe utilities used by the
scene scripts. Everything is procedural so the pipeline runs headless
on CPU-only machines.
"""
import math
import random

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Euler, Matrix, Vector, noise


# ----------------------------------------------------------------- nodes
def node(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
        else:
            setattr(n, k, v)
    return n


def link(nt, a, b):
    nt.links.new(a, b)


def math_node(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            link(nt, v, n.inputs[i])
    return n.outputs[0]


def mix_rgb(nt, fac, a, b, blend='MIX'):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = blend
    for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, (tuple, list)):
            sock.default_value = tuple(v) + ((1.0,) if len(v) == 3 else ())
        else:
            link(nt, v, sock)
    return n.outputs[2]


def map_range(nt, v, a0, a1, b0=0.0, b1=1.0, interp='LINEAR'):
    n = nt.nodes.new('ShaderNodeMapRange')
    n.interpolation_type = interp
    link(nt, v, n.inputs['Value'])
    n.inputs['From Min'].default_value = a0
    n.inputs['From Max'].default_value = a1
    n.inputs['To Min'].default_value = b0
    n.inputs['To Max'].default_value = b1
    return n.outputs[0]


def noise_tex(nt, vec, scale, detail=6.0, rough=0.55, distortion=0.0, dims='3D', w=None):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.noise_dimensions = dims
    if vec is not None:
        link(nt, vec, n.inputs['Vector'])
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = distortion
    if w is not None:
        if isinstance(w, (int, float)):
            n.inputs['W'].default_value = w
        else:
            link(nt, w, n.inputs['W'])
    return n


def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = node(nt, 'ShaderNodeOutputMaterial', (900, 0))
    return m, nt, out


def coords(nt, kind='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    return tc.outputs[kind]


def separate(nt, vec):
    n = nt.nodes.new('ShaderNodeSeparateXYZ')
    link(nt, vec, n.inputs[0])
    return n.outputs


def combine(nt, x, y, z):
    n = nt.nodes.new('ShaderNodeCombineXYZ')
    for i, v in enumerate((x, y, z)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            link(nt, v, n.inputs[i])
    return n.outputs[0]


def bump(nt, height, strength, distance=0.02, normal=None):
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = distance
    link(nt, height, b.inputs['Height'])
    if normal is not None:
        link(nt, normal, b.inputs['Normal'])
    return b.outputs[0]


# ----------------------------------------------------------------- objects
def obj_from_bmesh(name, bm, mat=None, collection=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
        if hasattr(me, 'set_sharp_from_angle'):
            me.set_sharp_from_angle(angle=math.radians(35))
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def bm_box(bm, center, size, rot_z=0.0):
    m = Matrix.Translation(Vector(center)) @ Matrix.Rotation(rot_z, 4, 'Z') @ \
        Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)


def lathe(name, profile, segments=64, axis='Y', mat=None, smooth=True):
    """Revolve a list of (radius, axial) points around an axis."""
    bm = bmesh.new()
    rings = []
    for a in range(segments):
        ang = 2 * math.pi * a / segments
        ring = []
        for r, s in profile:
            x, z = r * math.cos(ang), r * math.sin(ang)
            co = (x, s, z) if axis == 'Y' else (x, z, s)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    n = len(profile)
    for a in range(segments):
        r0, r1 = rings[a], rings[(a + 1) % segments]
        for i in range(n - 1):
            bm.faces.new((r0[i], r1[i], r1[i + 1], r0[i + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bmesh(name, bm, mat, smooth=smooth)


def rock_mesh(name, radius=1.0, seed=0, rough=0.35, subdiv=3, squash=(1, 1, 1), mat=None):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        d = v.co.normalized()
        n = noise.fractal(d * 1.6 + off, 0.6, 2.0, 4)
        v.co = d * radius * (1 + rough * n)
        v.co.x *= squash[0]
        v.co.y *= squash[1]
        v.co.z *= squash[2]
    return obj_from_bmesh(name, bm, mat, smooth=True)


def add_bevel(ob, width=0.03, segments=2):
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    return m


# ----------------------------------------------------------------- animation
def key(datablock, path, frame, value, interp=None, index=-1):
    setattr_path(datablock, path, value)
    datablock.keyframe_insert(data_path=path, frame=frame, index=index)
    if interp:
        set_last_interp(datablock, path, frame, interp)


def setattr_path(db, path, value):
    if path.startswith('['):
        db[path[2:-2]] = value
        return
    parts = path.split('.')
    tgt = db
    for p in parts[:-1]:
        tgt = getattr(tgt, p)
    last = parts[-1]
    if '[' in last:
        nm, idx = last[:-1].split('[')
        getattr(tgt, nm)[int(idx)] = value
    else:
        setattr(tgt, last, value)


def set_last_interp(db, path, frame, interp, easing='AUTO'):
    ad = db.animation_data if hasattr(db, 'animation_data') else None
    if ad is None or ad.action is None:
        return
    for fc in fcurves_of(ad):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.01:
                    kp.interpolation = interp
                    kp.easing = easing


def fcurves_of(ad):
    act = ad.action
    if act is None:
        return []
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return list(act.fcurves)
    # Blender 4.4+ layered actions
    out = []
    try:
        slot = ad.action_slot
        for layer in act.layers:
            for strip in layer.strips:
                cb = strip.channelbag(slot)
                if cb:
                    out.extend(cb.fcurves)
    except Exception:
        pass
    return out


def smooth_keys(ob, interp='BEZIER'):
    if ob.animation_data:
        for fc in fcurves_of(ob.animation_data):
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                kp.handle_left_type = 'AUTO_CLAMPED'
                kp.handle_right_type = 'AUTO_CLAMPED'


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def rng(seed):
    return random.Random(seed)
