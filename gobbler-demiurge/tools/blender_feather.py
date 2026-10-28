"""Model the Gobbler's feathers in Blender, bake golden-hour light into them, export through the X3D Blender I/O ("blenderizer").

Run with a Python that can `import bpy` (the PyPI wheel works, Blender 5.2 LTS):

    python3 tools/blender_feather.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/feathers] [--samples 48]

Writes assets/feathers/feather_{a,b,c}.x3d (X3D 4.0, one file per variant) and assets/feathers/receipt.json.
tools/feathers.py reads them back for the page; the page build itself does not need Blender.

Feather frame: root at the origin, the quill runs along +X to 1.0, the vane's width is along Y, its face normal is +Z.
The geometry is exported in that local frame; layers.py places it with a Transform (rotation from the plume's own axes, uniform scale = length).
Objects per variant (mesh names F<v>_<part>): near_vane (faceted, light baked), near_quill (tapered tube), near_barbs (edges),
outline (edges), spine (edges), mid_vane (8 stations, light baked).
"""
import sys, os, math, json, random, hashlib, argparse, importlib.util

import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
R = 0.125                       # full vane width as a fraction of the length (a plume of 8.4 units is about 1 unit wide)
VARIANTS = {                    # name: seed, arch (the quill bends up), curl (sideways), cup (both sides droop), twist (one side up), sun azimuth in degrees
    'a': dict(seed=11, arch=0.055, curl=0.030, cup=0.20, twist=0.10, az=-40),
    'b': dict(seed=23, arch=0.085, curl=-0.040, cup=0.26, twist=0.18, az=5),
    'c': dict(seed=37, arch=0.040, curl=0.055, cup=0.14, twist=0.22, az=48),
}


def prof(t):
    return (math.sin(math.pi * min(1.0, t ** 0.82)) ** 0.62) if t < 1 else 0.0


def spine_pt(t, V):
    return Vector((t, V['curl'] * t * t, V['arch'] * t * t))


def vane_vertices(n_st, n_cross, V, rng, jitter):
    """grid of vertices: row 0 is the quill (shared), then n_cross rows out to each edge. returns dict (i, side, j) -> Vector"""
    P = {}
    for i in range(n_st + 1):
        t = i / n_st
        s0 = spine_pt(t, V)
        w = 0.5 * R * prof(t)
        P[(i, 0, 0)] = s0
        for side in (1, -1):
            for j in range(1, n_cross + 1):
                s = j / n_cross
                y = side * w * s
                x = 0.55 * w * s ** 1.3
                z = -V['cup'] * w * s * s + side * V['twist'] * w * s
                if jitter and 0 < i < n_st:                       # the facets: a small seeded wobble so the quads stop being flat
                    z += rng.uniform(-1, 1) * 0.07 * w * s
                    y += rng.uniform(-1, 1) * 0.03 * w * s
                P[(i, side, j)] = s0 + Vector((x, y, z))
    return P


def vane_mesh(name, n_st, n_cross, V, rng, jitter):
    P = vane_vertices(n_st, n_cross, V, rng, jitter)
    bm = bmesh.new()
    vm = {}
    def vert(key):
        k = (key[0], 0, 0) if key[2] == 0 else key
        if k not in vm: vm[k] = bm.verts.new(P[k])
        return vm[k]
    for i in range(1, n_st + 1):                                  # t = 0 has width 0: start at station 1 so no sliver faces at the root
        for side in (1, -1):
            for j in range(1, n_cross + 1):
                quad = [vert((i - 1, side, j - 1)), vert((i, side, j - 1)), vert((i, side, j)), vert((i - 1, side, j))]
                if side == -1: quad.reverse()
                if len(set(quad)) < 3: continue
                quad = list(dict.fromkeys(quad))
                try: bm.faces.new(quad)
                except ValueError: pass
    bm.faces.ensure_lookup_table()
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    return me


def edges_mesh(name, polylines):
    me = bpy.data.meshes.new(name); verts, edges = [], []
    for pl in polylines:
        base = len(verts); verts += [tuple(p) for p in pl]; edges += [(base + k, base + k + 1) for k in range(len(pl) - 1)]
    me.from_pydata(verts, edges, []); me.update()
    return me


def quill_mesh(name, V, n_seg=24, sides=6):
    bm = bmesh.new(); rings = []
    for i in range(n_seg + 1):
        t = i / n_seg
        c = spine_pt(t, V); r = 0.0036 * (1 - 0.8 * t) + 0.0004
        ring = [bm.verts.new(c + Vector((0, r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides)))) for k in range(sides)]
        rings.append(ring)
    for i in range(n_seg):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    return me


def add_obj(me, coll):
    ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob); return ob


def setup_world(az_deg, elevation_deg=24.0):
    """golden hour: a warm low sun lamp plus a cool sky fill from a multiple-scattering sky (its own sun disc switched off)"""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False; sc.cycles.seed = 7
    w = bpy.data.worlds.new('golden'); w.use_nodes = True; sc.world = w
    nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False; sky.sun_elevation = math.radians(6); sky.sun_rotation = math.radians(az_deg)
    bg = nt.nodes.new('ShaderNodeBackground'); out = nt.nodes.new('ShaderNodeOutputWorld')
    bg.inputs['Strength'].default_value = 0.14
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    e, a = math.radians(elevation_deg), math.radians(az_deg)
    toward = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))     # from the feather to the sun
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 16.0; ld.color = (1.0, 0.64, 0.34); ld.angle = math.radians(2.5)
    lo = bpy.data.objects.new('sun', ld); sc.collection.objects.link(lo)
    lo.rotation_euler = (-toward).to_track_quat('-Z', 'Y').to_euler()
    return sky


def bake_vertex_light(ob, coll_scene):
    """Cycles bake of direct plus indirect light on a white diffuse surface into a corner colour attribute (no base colour)."""
    me = ob.data
    mat = bpy.data.materials.new('white'); mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1); bsdf.inputs['Roughness'].default_value = 1.0
    me.materials.append(mat)
    attr = me.color_attributes.new(name='Light', type='FLOAT_COLOR', domain='CORNER')
    me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Light')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bk = bpy.context.scene.render.bake
    bk.target = 'VERTEX_COLORS'; bk.use_pass_direct = True; bk.use_pass_indirect = True; bk.use_pass_color = False
    bpy.ops.object.bake(type='DIFFUSE')
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    raw = [tuple(d.color[:3]) for d in attr.data]
    top = sorted(lum(c) for c in raw)[int(len(raw) * 0.92)] or 1.0
    k = 0.92 / top                                              # exposure: the 92nd percentile facet lands at 0.92, so the sunlit facets keep their hue (the X3D colour range is 0 to 1)
    vals = []
    for d, c in zip(attr.data, raw):
        c = [x * k for x in c]; l = lum(c)
        if l < 0.28: c = [x + (0.28 - l) * (0.6, 0.9, 1.2)[i] for i, x in enumerate(c)]            # degenerate root slivers and shadowed facets keep a floor of light
        c = tuple(min(1.0, max(0.0, x)) for x in c)
        d.color = (c[0], c[1], c[2], 1.0); vals.append(c)
    return vals


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source')
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'feathers'))
    ap.add_argument('--samples', type=int, default=48)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)

    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    m = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = m; spec.loader.exec_module(m); m.register()
    import subprocess
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'

    receipt = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), samples=a.samples, bake='Cycles CPU diffuse, direct+indirect, multiple-scattering sky', variants={})
    for name, V in VARIANTS.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene; sc.cycles.samples = a.samples
        setup_world(V['az'])
        coll = sc.collection; rng = random.Random(V['seed'])
        near = add_obj(vane_mesh('F%s_near_vane' % name, 24, 3, V, rng, True), coll)
        mid = add_obj(vane_mesh('F%s_mid_vane' % name, 8, 1, V, random.Random(V['seed'] + 1), False), coll)
        add_obj(quill_mesh('F%s_near_quill' % name, V), coll)
        P = vane_vertices(24, 3, V, random.Random(V['seed']), True)             # same rng stream as near_vane: the barbs end on its (jittered) edge vertices
        barbs = []
        for i in range(1, 25):
            for side in (1, -1):
                barbs.append([P[(i, 0, 0)], P[(i, side, 3)]])
        add_obj(edges_mesh('F%s_near_barbs' % name, barbs), coll)
        L = [P[(i, 1, 3)] for i in range(1, 25)]; Rr = [P[(i, -1, 3)] for i in range(1, 25)]
        add_obj(edges_mesh('F%s_outline' % name, [[P[(0, 0, 0)]] + L + Rr[::-1] + [P[(0, 0, 0)]]]), coll)
        add_obj(edges_mesh('F%s_spine' % name, [[P[(i, 0, 0)] for i in range(25)]]), coll)
        stats = {}
        for ob in (near, mid):
            vals = bake_vertex_light(ob, sc)
            lum = [0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] for c in vals]; warm = sum(c[0] / max(c[2], 1e-3) for c in vals) / len(vals)
            stats[ob.name] = dict(tris=len(ob.data.polygons), lum_min=round(min(lum), 3), lum_mean=round(sum(lum) / len(lum), 3), lum_max=round(max(lum), 3), warm_r_over_b=round(warm, 2))
        bpy.ops.object.select_all(action='DESELECT')
        for ob in bpy.data.objects:
            if ob.type == 'MESH': ob.select_set(True)                       # meshes only: the bake lamp stays out of the file
        path = os.path.join(out, 'feather_%s.x3d' % name)
        bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=False, name_decorations=True,
                                 meta_creator='Gobbler demiurge', meta_title='Feather %s' % name, meta_description='Blender-modelled feather, golden-hour light baked (Cycles), unit frame: quill along +X, vane width along Y')
        receipt['variants'][name] = dict(params=V, objects=stats, file='feather_%s.x3d' % name, bytes=os.path.getsize(path), sha256=sha(path))
        print(name, json.dumps(stats))
    json.dump(receipt, open(os.path.join(out, 'receipt.json'), 'w'), indent=1)
    print('wrote', out)


main()
