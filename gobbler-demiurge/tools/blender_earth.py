"""Model the Earth, its clouds and the Moon in Blender and export them through the X3D Blender I/O ("blenderizer").

    python3 tools/blender_earth.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/earth]     (a Python that can `import bpy`)

Writes assets/earth/earth.x3d (three objects: Earth, Clouds, Moon, each one unit in radius at the origin) and receipt.json. The planet is a faceted icosphere whose faces carry
baked colour: the day side lit from the direction of the Sun (the village faces the Sun, so the home continent sits where village_spec.site_frame() says), a warm terminator,
a night side with a scatter of gold city lights; the clouds are a second, thinner shell of soft banks (per-corner alpha fades each bank out at its edge, and the sky over the
village is left clear, because at village scale the shell hangs only 7 m over the roofs); the Moon is grey, cratered and lit the same way.
Everything is drawn unlit by the page, with the colour baked here, in the same hand as the feathers, the tenders and the village.
"""
import sys, os, math, json, hashlib, argparse, importlib.util, subprocess, random

import bpy, bmesh
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import village_spec as VS

_, UP, _, _ = VS.site_frame()
SUN_DIR = Vector((UP[0], -UP[2], UP[1]))                 # the exporter turns Blender (x, y, z) into X3D (x, z, -y), so X3D (X, Y, Z) is Blender (X, -Z, Y)
SITE = SUN_DIR.copy()                                    # the village stands where the Sun is overhead


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def mix(a, b, t): return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def fbm(p, seed, octaves=5): return noise.fractal(p * 1.6 + Vector((seed * 11.3, seed * 7.1, seed * 3.7)), 1.0, 2.0, octaves, noise_basis='PERLIN_ORIGINAL')


def lit_of(n):
    d = n.dot(SUN_DIR)
    return smooth(-0.10, 0.42, d), d                      # a soft terminator


def earth_colour(n, rng):
    e = fbm(n, 3) + 0.30 * max(0.0, n.dot(SITE) - 0.55) * 1.6 - 0.04          # elevation: noise, raised under the home continent
    ang = math.degrees(math.acos(max(-1, min(1, n.dot(SITE)))))
    lat = abs(n.z)
    if lat > 0.86 + 0.05 * fbm(n * 3, 5): base = (0.93, 0.96, 1.0)                                                   # polar ice
    elif e <= 0.0:
        base = mix((0.05, 0.20, 0.45), (0.14, 0.42, 0.62), smooth(-0.22, 0.0, e))                                    # deep to shallow water
    else:
        h = smooth(0.0, 0.5, e); dry = smooth(0.25, 0.7, abs(fbm(n * 2, 8)) * 1.6 + 0.5 * (1 - lat) * (fbm(n, 9) + 0.2))
        low = mix((0.32, 0.56, 0.26), (0.62, 0.55, 0.30), dry)                                                       # green to dry gold
        base = mix(low, (0.64, 0.60, 0.56), smooth(0.35, 0.6, e)) if h > 0.0 else low                               # rock on the heights
        if ang < 26: base = mix(base, (0.40, 0.62, 0.28), smooth(30, 8, ang))                                         # the home valley is green
    lit, d = lit_of(n)
    day = tuple(c * (0.50 + 0.60 * lit) for c in base)
    warm = smooth(-0.14, 0.0, d) * (1 - smooth(0.0, 0.30, d))                                                         # a gold band along the terminator
    day = mix(day, (min(1, day[0] * 1.35 + 0.10), day[1] * 1.0, day[2] * 0.62), 0.5 * warm)
    night = (0.015 + base[0] * 0.05, 0.03 + base[1] * 0.06, 0.07 + base[2] * 0.12)
    c = mix(night, day, lit)
    if e > 0.02 and lat < 0.8 and rng.random() < 0.10 and lit < 0.5:                                                  # a city light on the night side
        c = mix(c, (1.0, 0.78, 0.38), 0.85 * (1 - lit))
    return c


def build_sphere(name, sub, radius, colour_fn, keep=None, push=None, alpha=1.0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    rng = random.Random(len(name) * 101 + sub)
    for v in bm.verts:                                                                           # a little relief so the horizon is not a perfect polygon
        if push: v.co = v.co.normalized() * push(v.co.normalized())
        else: v.co = v.co.normalized() * radius
    if keep:
        bmesh.ops.delete(bm, geom=[f_ for f_ in bm.faces if not keep(f_.calc_center_median().normalized())], context='FACES')
    bm.faces.ensure_lookup_table(); cols = []
    for f_ in bm.faces:
        f_.normal_update(); cols.append(tuple(min(1.0, max(0.0, x)) for x in colour_fn(f_.calc_center_median().normalized(), rng)) + (alpha,))      # the X3D schema keeps colours within [0, 1]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    attr = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER'); me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for poly, c in zip(me.polygons, cols):
        for li in poly.loop_indices: attr.data[li].color = c
    return me


def cloud_colour(n, rng):
    lit, d = lit_of(n)
    c = tuple(x * (0.22 + 0.78 * lit) for x in (1.0, 0.99, 0.96))
    warm = smooth(-0.14, 0.0, d) * (1 - smooth(0.0, 0.30, d))
    c = mix(c, (1.0, 0.72, 0.45), 0.45 * warm)
    return (c[0], c[1], c[2] * (0.55 + 0.45 * lit))


CLEAR_DEG = (25.0, 38.0)                                  # no cloud within 25 degrees of the village, fading in by 38


def cloud_density(n):
    """0 to 1: how thick the cloud is over this point of the sphere; soft at the edges, and zero over the village"""
    f = fbm(n * 1.5, 31) + 0.35 * fbm(n * 4, 32)
    ang = math.degrees(math.acos(max(-1, min(1, n.dot(SITE)))))
    return smooth(0.14, 0.44, f) * smooth(CLEAR_DEG[0], CLEAR_DEG[1], ang)


def build_clouds(name, sub, radius):
    """a thin shell of soft cloud banks: every corner has its own alpha (the density there), the colour is flat per face, the bank swells a little where it is thickest"""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    dens = {}
    for v in bm.verts:
        n = v.co.normalized(); dens[v.index] = cloud_density(n); v.co = n * (radius + 0.010 * dens[v.index])
    bmesh.ops.delete(bm, geom=[f_ for f_ in bm.faces if max(dens[v.index] for v in f_.verts) < 0.02], context='FACES')
    bm.faces.ensure_lookup_table(); rng = random.Random(41); cols = []
    for f_ in bm.faces:
        f_.normal_update(); c = cloud_colour(f_.calc_center_median().normalized(), rng)
        cols.append((tuple(min(1.0, max(0.0, x)) for x in c), [dens[v.index] for v in f_.verts]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    attr = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER'); me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for poly, (c, ds) in zip(me.polygons, cols):
        for li, d in zip(poly.loop_indices, ds): attr.data[li].color = (c[0], c[1], c[2], round(0.86 * d, 3))
    return me


def moon_colour(n, rng):
    lit, d = lit_of(n)
    g = 0.46 + 0.20 * fbm(n * 3, 21) + (0.0 if fbm(n * 5, 22) > -0.2 else -0.16)                  # maria and craters
    g = max(0.18, min(0.8, g)); base = (g * 1.0, g * 0.97, g * 0.92)
    c = tuple(x * (0.12 + 0.95 * lit) for x in base)
    shine = (g * 0.17, g * 0.20, g * 0.29)                                  # earthshine: blue light off the Earth keeps the craters and maria readable on the night side
    return mix(shine, c, 0.12 + 0.88 * lit)


def moon_radius(n): return 1.0 + 0.045 * fbm(n * 4, 23)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'earth'))
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    m = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = m; spec.loader.exec_module(m); m.register()
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'
    bpy.ops.wm.read_factory_settings(use_empty=True); coll = bpy.context.scene.collection
    earth = build_sphere('Earth', 5, 1.0, earth_colour, push=lambda n: 1.0 + 0.006 * fbm(n * 2, 3))
    clouds = build_clouds('Clouds', 5, 1.028)
    moon = build_sphere('Moon', 4, 1.0, moon_colour, push=moon_radius)
    for nm, me in (('Earth', earth), ('Clouds', clouds), ('Moon', moon)): coll.objects.link(bpy.data.objects.new(nm, me))
    bpy.ops.object.select_all(action='SELECT')
    path = os.path.join(out, 'earth.x3d')
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=False, meta_creator='Gobbler demiurge', meta_title='Earth and Moon',
                             meta_description='A faceted Earth (day side lit from the village side), its cloud shell and the Moon, one unit in radius each; made in Blender')
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    rec = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), village_spec_sha256=sha(os.path.join(HERE, 'village_spec.py')),
               faces=dict(earth=len(earth.polygons), clouds=len(clouds.polygons), moon=len(moon.polygons)), file='earth.x3d', bytes=os.path.getsize(path), sha256=sha(path))
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w'), indent=1); print(json.dumps(rec))


main()
