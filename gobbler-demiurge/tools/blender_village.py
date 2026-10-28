"""Model the village Aurelsbrunn in Blender and export it through the X3D Blender I/O ("blenderizer").

    python3 tools/blender_village.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/village]     (a Python that can `import bpy`)

Writes assets/village/village.x3d (X3D 4.0) and receipt.json. One metre is one Blender unit; the plaza centre is the origin, +Z is up (X3D +Y after the exporter's own
conversion). The ground follows the curve of the planet (radius village_spec.R_PLANET), so buildings and trees lean to stay upright on it. Repeated things (eleven building
variants, three trees, a stall, a lamp) are one mesh each, linked into many objects, which the exporter writes as one DEF and many USEs. Faces carry baked colour from a fixed
key light with cool shadows, the same hand as the feathers and the tenders (the page draws them unlit).
"""
import sys, os, math, json, hashlib, argparse, importlib.util, subprocess, random

import bpy, bmesh
from mathutils import Vector, Quaternion, noise

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import village_spec as VS

KEY = Vector((-0.35, -0.30, 0.89)).normalized()
COOL = (0.20, 0.30, 0.42)
R = VS.R_PLANET
SKIRT = 0.8                                                           # buildings, stalls and trunks reach this far below their base so no gap shows on the uneven ground


def sag(r): return math.sqrt(max(R * R - r * r, 1.0)) - R              # how far the planet's surface drops away from the tangent plane at distance r (negative)


def shade(col, n):
    lit = max(0.0, n.dot(KEY)); k = 0.52 + 0.58 * lit + 0.08 * (n.z * 0.5 + 0.5)
    return tuple(min(1.0, col[i] * k + COOL[i] * (1.0 - lit) * 0.5) for i in range(3))


class MB:
    """a mesh under construction: parts share vertices inside themselves, faces get a baked colour from their normal"""
    def __init__(self): self.bm = bmesh.new(); self.cols = []

    def part(self, fn, colour, tint=None):
        """fn(bm) -> faces; colour is an RGB or a function of the face normal; then normals are made outward and the colours baked"""
        faces = fn(self.bm)
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        for f_ in faces:
            f_.normal_update(); c = colour(f_.normal) if callable(colour) else colour
            self.cols.append(shade(c, f_.normal.copy()))
        return faces

    def build(self, name):
        bm = self.bm; bm.faces.ensure_lookup_table()
        me = bpy.data.meshes.new(name); bm.to_mesh(me)
        for p in me.polygons: p.use_smooth = False
        attr = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
        me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Col')
        order = {}                                                          # to_mesh keeps face order
        for poly, c in zip(me.polygons, self.cols):
            for li in poly.loop_indices: attr.data[li].color = (c[0], c[1], c[2], 1.0)
        bm.free(); return me


# ---- shapes (each returns the list of faces it made) ----
def box(c, size, taper=1.0, z0=None):
    def fn(bm):
        sx, sy, sz = size; vs = []; cz = c[2] if z0 is None else z0 + sz / 2
        for z, t in ((-0.5, 1.0), (0.5, taper)):
            for x, y in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)): vs.append(bm.verts.new((c[0] + x * sx * t, c[1] + y * sy * t, cz + z * sz)))
        return [bm.faces.new([vs[i] for i in q]) for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    return fn


def gable(c, w, d, z0, h, over=0.35):
    """a gable roof: ridge along Y, eaves at z0, ridge at z0 + h, overhanging by `over`"""
    def fn(bm):
        hw, hd = w / 2 + over, d / 2 + over
        A = [bm.verts.new(v) for v in ((c[0] - hw, c[1] - hd, z0), (c[0] + hw, c[1] - hd, z0), (c[0] + hw, c[1] + hd, z0), (c[0] - hw, c[1] + hd, z0), (c[0], c[1] - hd, z0 + h), (c[0], c[1] + hd, z0 + h))]
        return [bm.faces.new(q) for q in ([A[0], A[1], A[4]], [A[2], A[3], A[5]], [A[1], A[2], A[5], A[4]], [A[3], A[0], A[4], A[5]], [A[3], A[2], A[1], A[0]])]
    return fn


def hip(c, w, d, z0, h, over=0.4, top=0.25):
    def fn(bm):
        hw, hd = w / 2 + over, d / 2 + over; tw, td = hw * top, hd * top
        B = [bm.verts.new(v) for v in ((c[0] - hw, c[1] - hd, z0), (c[0] + hw, c[1] - hd, z0), (c[0] + hw, c[1] + hd, z0), (c[0] - hw, c[1] + hd, z0),
                                         (c[0] - tw, c[1] - td, z0 + h), (c[0] + tw, c[1] - td, z0 + h), (c[0] + tw, c[1] + td, z0 + h), (c[0] - tw, c[1] + td, z0 + h))]
        return [bm.faces.new(q) for q in ([B[0], B[1], B[5], B[4]], [B[1], B[2], B[6], B[5]], [B[2], B[3], B[7], B[6]], [B[3], B[0], B[4], B[7]], [B[7], B[6], B[5], B[4]], [B[3], B[2], B[1], B[0]])]
    return fn


def prism(c, z0, h, r0, r1, sides=8, cap=True, rot=0.0):
    def fn(bm):
        rings = []
        for z, r in ((z0, r0), (z0 + h, r1)):
            rings.append([bm.verts.new((c[0] + r * math.cos(2 * math.pi * k / sides + rot), c[1] + r * math.sin(2 * math.pi * k / sides + rot), z)) for k in range(sides)])
        fs = [bm.faces.new((rings[0][k], rings[0][(k + 1) % sides], rings[1][(k + 1) % sides], rings[1][k])) for k in range(sides)]
        if cap:
            fs.append(bm.faces.new(rings[0][::-1]))
            if r1 > 0.01: fs.append(bm.faces.new(rings[1]))
        return fs
    return fn


def cone(c, z0, h, r, sides=8):
    def fn(bm):
        base = [bm.verts.new((c[0] + r * math.cos(2 * math.pi * k / sides), c[1] + r * math.sin(2 * math.pi * k / sides), z0)) for k in range(sides)]; tip = bm.verts.new((c[0], c[1], z0 + h))
        return [bm.faces.new((base[k], base[(k + 1) % sides], tip)) for k in range(sides)] + [bm.faces.new(base[::-1])]
    return fn


def ball(c, r, sub=1):
    def fn(bm):
        g = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=__import__('mathutils').Matrix.Translation(Vector(c)))
        return [f_ for f_ in bm.faces if f_.verts[0] in g['verts']]
    return fn


# ---- the building types ----
CREAM = [(1.0, 0.88, 0.66), (0.95, 0.80, 0.58), (0.98, 0.84, 0.72)]
TERRA = [(0.86, 0.40, 0.24), (0.78, 0.30, 0.20), (0.90, 0.52, 0.28)]
WOOD = (0.50, 0.32, 0.18)
DOOR = (0.30, 0.18, 0.12)
GOLD = (1.0, 0.80, 0.34)
GRASS = [(0.42, 0.60, 0.28), (0.34, 0.52, 0.26), (0.50, 0.62, 0.30)]
STONE = [(0.92, 0.84, 0.72), (0.84, 0.76, 0.64)]


def cottage(v):
    m = MB(); w, d, h = 7.0, 6.0, 3.2
    m.part(box((0, 0, 0), (w, d, h + SKIRT), 1.0, z0=-SKIRT), CREAM[v % 3]); m.part(gable((0, 0, 0), w, d, h, 2.3), TERRA[v % 3])
    m.part(box((0, -d / 2 - 0.05, 0), (1.1, 0.2, 2.1), 1.0, z0=0.0), DOOR); m.part(box((w / 2 - 1.3, 0.8, 0), (0.9, 0.9, 5.2 + SKIRT), 1.0, z0=-SKIRT), (0.62, 0.50, 0.42))
    return m.build('Cottage%d' % v)


def house(v):
    m = MB(); w, d, h = 8.5, 7.0, 5.4
    m.part(box((0, 0, 0), (w, d, h + SKIRT), 1.0, z0=-SKIRT), CREAM[(v + 1) % 3]); m.part(hip((0, 0, 0), w, d, h, 2.6), TERRA[(v + 2) % 3])
    m.part(box((0, -d / 2 - 0.05, 0), (1.2, 0.2, 2.2), 1.0, z0=0.0), DOOR); m.part(box((-2.3, -d / 2 - 0.04, 2.8), (1.4, 0.2, 1.3), 1.0, z0=2.8), (0.55, 0.78, 0.88)); m.part(box((2.3, -d / 2 - 0.04, 2.8), (1.4, 0.2, 1.3), 1.0, z0=2.8), (0.55, 0.78, 0.88))
    return m.build('House%d' % v)


def hall(v):
    m = MB(); w, d, h = 15.0, 9.5, 5.6
    m.part(box((0, 0, 0), (w, d, h + SKIRT), 1.0, z0=-SKIRT), (0.96, 0.86, 0.66)); m.part(gable((0, 0, 0), w, d, h, 4.2, 0.6), TERRA[v % 3])
    m.part(box((0, -d / 2 - 0.05, 0), (2.4, 0.3, 3.6), 1.0, z0=0.0), DOOR)
    m.part(box((w / 2 - 1.5, 0, 0), (3.0, 3.0, 12.0 + SKIRT), 1.0, z0=-SKIRT), (0.94, 0.82, 0.62)); m.part(cone((w / 2 - 1.5, 0, 0), 12.0, 5.0, 2.6, 4), GOLD)
    return m.build('Hall%d' % v)


def mill():
    m = MB()
    m.part(prism((0, 0), -SKIRT, 13.0 + SKIRT, 3.6, 2.6, 8), (0.94, 0.84, 0.66)); m.part(cone((0, 0), 13.0, 4.6, 3.0, 8), TERRA[0])
    for k in range(4):                                                            # four sails: flat slats on the front
        a = k * math.pi / 2 + math.pi / 4
        m.part(lambda bm, a=a: _sail(bm, a), WOOD)
    return m.build('Mill')


def _sail(bm, a):
    """one sail: a thin slab on the front of the mill, turned by a about the hub (0, -3.9, 11)"""
    c, s = math.cos(a), math.sin(a); vs = []
    for y in (-4.0, -3.8):
        for u, v in ((-0.35, 0.8), (0.35, 0.8), (0.35, 5.8), (-0.35, 5.8)):
            vs.append(bm.verts.new((u * c - v * s, y, 11.0 + u * s + v * c)))
    return [bm.faces.new([vs[i] for i in q]) for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))]


def stall(v):
    m = MB(); cols = [(0.85, 0.30, 0.25), (0.25, 0.60, 0.70)]
    m.part(box((0, 0, 0), (3.2, 1.8, 1.0 + SKIRT), 1.0, z0=-SKIRT), WOOD)
    for k in range(4):                                                             # a striped awning
        x0 = -1.6 + k * 0.8
        m.part(lambda bm, x0=x0: [bm.faces.new([bm.verts.new(p) for p in ((x0, -1.4, 2.6), (x0 + 0.8, -1.4, 2.6), (x0 + 0.8, 0.9, 3.0), (x0, 0.9, 3.0))])], cols[(k + v) % 2])
    for x in (-1.5, 1.5): m.part(prism((x, 0.8), 0.0, 3.0, 0.08, 0.08, 4), WOOD)
    return m.build('Stall%d' % v)


def lamp():
    m = MB(); m.part(prism((0, 0), 0.0, 3.4, 0.14, 0.09, 6), (0.40, 0.32, 0.26)); m.part(ball((0, 0, 3.6), 0.34, 1), (1.0, 0.92, 0.6))
    return m.build('Lamp')


def tree(kind):
    m = MB()
    if kind == 0:                                                                  # pine
        m.part(prism((0, 0), -0.4, 2.2, 0.28, 0.2, 6), WOOD); m.part(cone((0, 0), 1.2, 4.6, 2.0, 7), (0.20, 0.46, 0.34)); m.part(cone((0, 0), 3.2, 4.0, 1.5, 7), (0.24, 0.52, 0.36))
    elif kind == 1:                                                                # round, autumn gold
        m.part(prism((0, 0), -0.4, 3.0, 0.32, 0.24, 6), WOOD); m.part(ball((0, 0, 4.4), 2.5, 1), (0.88, 0.70, 0.28)); m.part(ball((0.9, 0.5, 5.3), 1.7, 1), (0.82, 0.56, 0.24))
    else:                                                                          # poplar
        m.part(prism((0, 0), -0.4, 2.0, 0.24, 0.18, 6), WOOD); m.part(cone((0, 0), 1.2, 9.0, 1.3, 6), (0.30, 0.55, 0.32))
    return m.build('Tree%d' % kind)


def fountain():
    m = MB()
    m.part(prism((0, 0), 0.0, 1.0, VS.FOUNTAIN_R, VS.FOUNTAIN_R - 0.3, 12, cap=False), (0.92, 0.86, 0.76))                   # basin wall
    m.part(prism((0, 0), 0.0, 0.05, VS.FOUNTAIN_R - 0.3, VS.FOUNTAIN_R - 0.3, 12), (0.40, 0.45, 0.50))                      # basin floor
    m.part(prism((0, 0), 0.7, 0.05, VS.FOUNTAIN_R - 0.35, VS.FOUNTAIN_R - 0.35, 12), (0.35, 0.74, 0.95))                    # water
    m.part(prism((0, 0), 0.0, 1.9, 1.0, 0.7, 8), (0.90, 0.82, 0.70))
    m.part(prism((0, 0), 1.9, 0.5, 1.6, 1.4, 10), (0.95, 0.90, 0.80)); m.part(prism((0, 0), 2.35, 0.05, 1.3, 1.3, 10), (0.35, 0.74, 0.95))
    return m.build('Fountain')


def mast():
    """the tether mast: a gold needle from the fountain's centre, with rings; the tether leaves its tip"""
    m = MB(); m.part(prism((0, 0), 2.4, VS.MAST_H, 0.55, 0.06, 8), GOLD)
    for z in (14.0, 30.0, 46.0): m.part(prism((0, 0), z, 0.5, 1.3 - z / 60.0 * 0.6, 1.3 - z / 60.0 * 0.6, 8), (1.0, 0.92, 0.6))
    return m.build('Mast')


def ground():
    """the cap of the planet under the village: polar rings, plaza paving, four roads, grass with a little variation; curved by sag()"""
    bm = bmesh.new(); rings = [0.0, 6.0, 11.0, 16.0, 22.0, 30.0, 40.0, 52.0, 66.0, VILLAGE_R]; N = 48; cols = []; vgrid = []
    for i, r in enumerate(rings):
        row = []
        for k in range(N if r > 0 else 1):
            a = 2 * math.pi * k / N
            dz = 0.0 if r < 20 else 0.30 * noise.fractal(Vector((r * math.cos(a) * 0.06, r * math.sin(a) * 0.06, 0.0)), 1.0, 2.0, 3, noise_basis='PERLIN_ORIGINAL')
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), sag(r) + dz)))
        vgrid.append(row)
    faces = []
    for i in range(len(rings) - 1):
        for k in range(N):
            k2 = (k + 1) % N; r0, r1 = rings[i], rings[i + 1]
            if i == 0: vs = [vgrid[0][0], vgrid[1][k], vgrid[1][k2]]
            else: vs = [vgrid[i][k], vgrid[i + 1][k], vgrid[i + 1][k2], vgrid[i][k2]]
            f_ = bm.faces.new(vs); faces.append((f_, i, k))
    for f_, i, k in faces:
        if f_.normal.z < 0: f_.normal_flip()
    out = []
    for f_, i, k in faces:
        f_.normal_update(); mid = (rings[i] + rings[i + 1]) / 2; ang = (k + 0.5) * 2 * math.pi / N; rng = random.Random(i * 97 + k)
        road = min(abs(((ang + math.pi / 4) % (math.pi / 2)) - math.pi / 4) * mid, 99.0) < 3.2 and mid > 16.0                     # four roads, 6.4 m wide
        if mid < VS.PLAZA_R: c = STONE[(i + k) % 2] if i % 2 == 0 else STONE[(i + k + 1) % 2]
        elif road: c = (0.88, 0.78, 0.58)
        else: c = tuple(x * (0.9 + 0.2 * rng.random()) for x in GRASS[(i * 3 + k) % 3])
        out.append(shade(c, f_.normal.copy()))
    me = bpy.data.meshes.new('Ground'); bm.to_mesh(me)
    for p in me.polygons: p.use_smooth = False
    attr = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER'); me.color_attributes.active_color = attr; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for poly, c in zip(me.polygons, out):
        for li in poly.loop_indices: attr.data[li].color = (c[0], c[1], c[2], 1.0)
    bm.free(); return me


VILLAGE_R = VS.VILLAGE_R


def place(coll, name, mesh, x, y, yaw=0.0, scale=1.0):
    """an object standing upright on the planet at (x, y): z follows the curve, the object leans to the local vertical"""
    r = math.hypot(x, y); z = sag(r) - 0.05
    ob = bpy.data.objects.new(name, mesh); coll.objects.link(ob); ob.location = (x, y, z)
    n = (Vector((x, y, z)) - Vector((0, 0, -R))).normalized()
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(n) @ Quaternion((0, 0, 1), yaw)
    ob.scale = (scale, scale, scale); return ob


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'village'))
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    m = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = m; spec.loader.exec_module(m); m.register()
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'
    bpy.ops.wm.read_factory_settings(use_empty=True); coll = bpy.context.scene.collection
    rng = random.Random(1618)
    g = bpy.data.objects.new('Ground', ground()); coll.objects.link(g)
    bpy.data.objects.new('Fountain', fountain()); coll.objects.link(bpy.data.objects['Fountain']); fo = bpy.data.objects['Fountain']; fo.location = (0, 0, 0.05)
    mo = bpy.data.objects.new('Mast', mast()); coll.objects.link(mo); mo.location = (0, 0, 0.05)
    cot = [cottage(i) for i in range(3)]; hou = [house(i) for i in range(3)]; hl = [hall(0), hall(1)]; mi = mill(); st = [stall(0), stall(1)]; la = lamp(); tr = [tree(0), tree(1), tree(2)]
    placed = []; count = 0
    def face_centre(name, mesh, r, th, **kw):
        nonlocal count
        x, y = r * math.cos(th), r * math.sin(th); yaw = th - math.pi / 2                                   # the front (-Y) faces the plaza centre
        place(coll, '%s_%02d' % (name, count), mesh, x, y, yaw, **kw); placed.append((x, y, 7.5)); count += 1
    for k in range(8): face_centre('Cottage', cot[k % 3], 27.0, math.radians(k * 45 + 10))
    for k in range(6): face_centre('House', hou[k % 3], 42.0, math.radians(k * 60 + 24))
    face_centre('Hall', hl[0], 34.0, math.radians(205)); face_centre('Hall', hl[1], 36.0, math.radians(75))
    x, y = 54.0 * math.cos(math.radians(315)), 54.0 * math.sin(math.radians(315)); place(coll, 'Mill', mi, x, y, math.radians(315) - math.pi / 2); placed.append((x, y, 6.0)); count += 1
    for k in range(6): face_centre('Stall', st[k % 2], 11.5, math.radians(k * 60 + 30))
    for k in range(12):
        th = math.radians(k * 30 + 15); place(coll, 'Lamp_%02d' % k, la, 15.4 * math.cos(th), 15.4 * math.sin(th), 0.0)
    n_trees = 0; tries = 0
    while n_trees < 70 and tries < 4000:
        tries += 1; r = rng.uniform(21.0, 76.0); th = rng.uniform(0, 2 * math.pi)
        if min(abs(((th + math.pi / 4) % (math.pi / 2)) - math.pi / 4) * r, 99.0) < 5.0: continue                      # keep the roads clear
        x, y = r * math.cos(th), r * math.sin(th)
        if any(math.hypot(x - px, y - py) < pr + 2.5 for px, py, pr in placed): continue
        kind = rng.choice([0, 0, 1, 2]); place(coll, 'Tree_%02d' % n_trees, tr[kind], x, y, rng.uniform(0, 6.28), rng.uniform(0.8, 1.35)); placed.append((x, y, 2.0)); n_trees += 1
    bpy.ops.object.select_all(action='SELECT')
    path = os.path.join(out, 'village.x3d')
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=False, meta_creator='Gobbler demiurge', meta_title='Aurelsbrunn',
                             meta_description='A village on a planet 250 m in radius: plaza, fountain, tether mast, 17 buildings, 6 stalls, 12 lamps, %d trees; made in Blender' % n_trees)
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    rec = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), village_spec_sha256=sha(os.path.join(HERE, 'village_spec.py')),
               objects=len(bpy.data.objects), buildings=count - 6, stalls=6, lamps=12, trees=n_trees, file='village.x3d', bytes=os.path.getsize(path), sha256=sha(path))
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w'), indent=1); print(json.dumps(rec))


main()
