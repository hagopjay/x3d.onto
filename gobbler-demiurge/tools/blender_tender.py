"""Model a shell tender in Blender as an H-Anim humanoid and export it through the X3D Blender I/O ("blenderizer").

Run with a Python that can `import bpy` (the PyPI wheel works, Blender 5.2 LTS):

    python3 tools/blender_tender.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/tender]

Writes assets/tender/tender.x3d (X3D 4.0, one HAnimHumanoid, 18 joints, skinned) and assets/tender/receipt.json.

Armature: the 18 joints of the lowest H-Anim 2.0 articulation level as I remember it (humanoid_root, sacroiliac, l_ and r_ hip, knee, ankle,
vl5, vt6, vc4, skullbase, l_ and r_ shoulder, elbow, wrist). The joint list is from memory and has not been checked against ISO/IEC 19774-1.
Skin: one faceted low-poly mesh (pelvis, abdomen, chest, neck, head, arms, legs, feet, joint caps), every part weighted 1.0 to its own joint,
per-face colour from a fixed key light (B's facets). The figure is 1 unit tall, stands on Z, faces -Y (Blender's front), left side is +X.
"""
import sys, os, math, json, hashlib, argparse, importlib.util, subprocess

import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
COOL = (0.20, 0.30, 0.42)                                          # the shadow tint
KEY = Vector((-0.4, -0.5, 0.75)).normalized()                      # the fixed key light (Blender frame: from the front left above)

# joint -> (parent, head position)
J = {
    'humanoid_root': (None, (0, 0, 0.52)),
    'sacroiliac': ('humanoid_root', (0, 0, 0.55)),
    'vl5': ('sacroiliac', (0, 0, 0.60)),
    'vt6': ('vl5', (0, 0, 0.72)),
    'vc4': ('vt6', (0, 0, 0.84)),
    'skullbase': ('vc4', (0, 0, 0.885)),
}
for s, sx in (('l', 1), ('r', -1)):
    J[s + '_hip'] = ('sacroiliac', (0.055 * sx, 0, 0.50)); J[s + '_knee'] = (s + '_hip', (0.058 * sx, 0.004, 0.28)); J[s + '_ankle'] = (s + '_knee', (0.058 * sx, 0, 0.06))
    J[s + '_shoulder'] = ('vc4', (0.115 * sx, 0, 0.82)); J[s + '_elbow'] = (s + '_shoulder', (0.16 * sx, 0, 0.62)); J[s + '_wrist'] = (s + '_elbow', (0.185 * sx, 0, 0.44))
assert len(J) == 18


def P(name): return Vector(J[name][1])


def prism(bm, a, b, r0, r1, sides=6, twist=0.0):
    """a tapered prism from a to b (closed at both ends)"""
    a, b = Vector(a), Vector(b); ax = (b - a).normalized()
    h = Vector((0, 1, 0)) if abs(ax.y) < .9 else Vector((1, 0, 0))
    u = ax.cross(h).normalized(); w = ax.cross(u)
    rings = []
    for c, r in ((a, r0), (b, r1)):
        rings.append([bm.verts.new(c + (u * math.cos(2 * math.pi * k / sides + twist) + w * math.sin(2 * math.pi * k / sides + twist)) * r) for k in range(sides)])
    for k in range(sides):
        bm.faces.new((rings[0][k], rings[0][(k + 1) % sides], rings[1][(k + 1) % sides], rings[1][k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[1])


def box(bm, c, size, taper=1.0):
    """a box centred on c; taper scales the top face (x and y) against the bottom"""
    c = Vector(c); sx, sy, sz = size; vs = []
    for z, t in ((-0.5, 1.0), (0.5, taper)):
        for x, y in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            vs.append(bm.verts.new(c + Vector((x * sx * t, y * sy * t, z * sz))))
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in q])


def gem(bm, c, r):
    """an octahedron: a joint cap"""
    c = Vector(c); V = [bm.verts.new(c + Vector(d) * r) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    for f in ((2, 4, 0), (2, 1, 4), (2, 5, 1), (2, 0, 5), (3, 0, 4), (3, 4, 1), (3, 1, 5), (3, 5, 0)):
        bm.faces.new([V[i] for i in f])


def icosphere(bm, c, r):
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r, matrix=__import__('mathutils').Matrix.Translation(Vector(c)))


def build_parts():
    """[(joint, colour, builder)]: every part is one object-space chunk weighted 1.0 to its joint"""
    gold, pale, dark = (0.96, 0.68, 0.26), (1.0, 0.80, 0.48), (0.72, 0.46, 0.18)
    parts = [
        ('sacroiliac', gold, lambda bm: box(bm, (0, 0, 0.53), (0.17, 0.10, 0.10), 0.95)),
        ('vl5', gold, lambda bm: box(bm, (0, 0, 0.63), (0.15, 0.09, 0.13), 1.05)),
        ('vt6', gold, lambda bm: box(bm, (0, 0, 0.77), (0.20, 0.105, 0.16), 1.0)),
        ('vc4', pale, lambda bm: prism(bm, (0, 0, 0.84), (0, 0, 0.885), 0.026, 0.022)),
        ('skullbase', pale, lambda bm: icosphere(bm, (0, 0, 0.94), 0.056)),
    ]
    for s, sx in (('l', 1), ('r', -1)):
        hip, knee, ank, sh, el, wr = (P(s + n) for n in ('_hip', '_knee', '_ankle', '_shoulder', '_elbow', '_wrist'))
        parts += [
            (s + '_hip', gold, lambda bm, hip=hip, knee=knee: prism(bm, hip, knee, 0.042, 0.032)),
            (s + '_knee', dark, lambda bm, knee=knee, ank=ank: prism(bm, knee, ank, 0.031, 0.024)),
            (s + '_knee', pale, lambda bm, knee=knee: gem(bm, knee, 0.036)),
            (s + '_ankle', gold, lambda bm, ank=ank, sx=sx: box(bm, (ank.x, ank.y - 0.03, 0.03), (0.05, 0.12, 0.04), 0.9)),
            (s + '_shoulder', gold, lambda bm, sh=sh, el=el: prism(bm, sh, el, 0.03, 0.025)),
            (s + '_shoulder', pale, lambda bm, sh=sh: gem(bm, sh, 0.04)),
            (s + '_elbow', dark, lambda bm, el=el, wr=wr: prism(bm, el, wr, 0.024, 0.02)),
            (s + '_elbow', pale, lambda bm, el=el: gem(bm, el, 0.03)),
            (s + '_wrist', pale, lambda bm, wr=wr: box(bm, (wr.x, wr.y, wr.z - 0.03), (0.035, 0.03, 0.06), 0.9)),
        ]
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source')
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'tender'))
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    m = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = m; spec.loader.exec_module(m); m.register()
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'

    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = bpy.context.scene.collection
    # armature
    arm = bpy.data.armatures.new('Tender'); aob = bpy.data.objects.new('Tender', arm); coll.objects.link(aob)
    bpy.context.view_layer.objects.active = aob; bpy.ops.object.mode_set(mode='EDIT')
    bones = {}
    for name, (parent, head) in J.items():
        b = arm.edit_bones.new(name); b.head = Vector(head)
        kids = [Vector(h) for n, (p, h) in J.items() if p == name]
        b.tail = (sum(kids, Vector()) / len(kids)) if kids else Vector(head) + Vector((0, 0, 0.04))
        if (b.tail - b.head).length < 0.01: b.tail = b.head + Vector((0, 0, 0.02))
        bones[name] = b
    for name, (parent, head) in J.items():
        if parent: bones[name].parent = bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')

    # skin: one mesh, one vertex group per joint, per-face colour from the fixed key light
    bm = bmesh.new(); face_part = []; part_verts = []
    for joint, colour, build in build_parts():
        n0 = len(bm.faces); v0 = len(bm.verts); build(bm); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
        for fc in bm.faces[n0:]: face_part.append((joint, colour))
        part_verts.append((joint, [v for v in bm.verts[v0:]]))
    bm.verts.index_update(); bm.faces.index_update()                    # new vertices carry no valid index until this
    vert_joint = {v.index: joint for joint, vs in part_verts for v in vs}   # parts never share vertices, so each vertex follows its own joint
    for f_ in bm.faces: f_.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('TenderSkin'); bm.to_mesh(me)
    for p in me.polygons: p.use_smooth = False
    attr = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for poly, (joint, colour) in zip(me.polygons, face_part):
        lit = max(0.0, poly.normal.dot(KEY)); k = 0.52 + 0.58 * lit + 0.08 * (poly.normal.z * 0.5 + 0.5)       # sunlit facets gold, shadowed facets lean cool (as the feathers do)
        shade = [min(1.0, colour[i] * k + COOL[i] * (1.0 - lit) * 0.50) for i in range(3)]
        for li in poly.loop_indices: attr.data[li].color = (shade[0], shade[1], shade[2], 1.0)
    sob = bpy.data.objects.new('TenderSkin', me); coll.objects.link(sob)
    for name in J: sob.vertex_groups.new(name=name)
    for vi, joint in vert_joint.items(): sob.vertex_groups[joint].add([vi], 1.0, 'REPLACE')
    sob.parent = aob; mod = sob.modifiers.new('Armature', 'ARMATURE'); mod.object = aob
    bm.free()

    bpy.ops.object.select_all(action='DESELECT'); aob.select_set(True); sob.select_set(True)
    path = os.path.join(out, 'tender.x3d')
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=True,
                             meta_creator='Gobbler demiurge', meta_title='Shell tender', meta_description='H-Anim humanoid, 18 joints, faceted skin, 1 unit tall; made in Blender')
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    rec = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), joints=len(J), skin_faces=len(face_part),
               file='tender.x3d', bytes=os.path.getsize(path), sha256=sha(path), joint_names='lowest-level H-Anim 2.0 set, from memory, not checked against the standard')
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w'), indent=1)
    print(json.dumps(rec))


main()
