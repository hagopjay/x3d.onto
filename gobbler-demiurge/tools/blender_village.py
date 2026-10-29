"""Model the village Aurelsbrunn in Blender, bake its light in Cycles and export it through the X3D Blender I/O ("blenderizer").

    python3 tools/blender_village.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/village] [--samples 384]     (a Python that can `import bpy`)

Writes assets/village/village.x3d (X3D 4.0) and receipt.json. One metre is one Blender unit; the plaza centre is the origin, +X is east, +Y north and +Z up (X3D +Y after the
exporter's own conversion). The ground follows the curve of the planet (radius village_spec.R_PLANET), so buildings and trees lean to stay upright on it.

Light is baked, not painted. The Heart is the village's sun (straight overhead on the real map; the key lamp here stands KEY_ELEV above the plaza so that every shape keeps a
shadow side): a warm key lamp with a soft disc and a cool multiple-scattering sky light the whole village at once in Cycles, with buildings, trees and ground shadowing each other,
and the bounce off every coloured surface counted (each face carries its albedo in the material, so the cream walls warm the paving and the pines cool the grass). The bake is the
light that arrives at every face corner; the face's own albedo, a floor of cool light in the deepest shadow, a filmic shoulder and the sRGB curve are applied afterwards, and the
lamps, windows and water keep a share of their own glow. The result is one colour per face corner, drawn unlit by the page, like the feathers and the planet.

Because the light differs per copy (every house stands at its own angle and in its own shadow), the copies cannot share colours, so the things are merged into four meshes
instead of being left as 108 objects: Ground, Buildings, Props and Trees. The page draws the village in four calls.
"""
import sys, os, math, json, hashlib, argparse, importlib.util, subprocess, random

import bpy, bmesh
from mathutils import Vector, Quaternion, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import village_spec as VS

KEY_AZ, KEY_ELEV = 220.0, 55.0                                        # degrees: the key lamp's azimuth (east round to north) and elevation above the plaza
KEY_COL, KEY_STRENGTH, KEY_ANGLE = (1.0, 0.85, 0.62), 5.0, 6.0        # warm, with a soft disc of 6 degrees (the real Heart would be wider still)
SKY_ELEV, SKY_STRENGTH = 26.0, 0.25                                   # the sky's own sun stands low (its disc is off), so its light is warm toward the horizon and blue overhead; 1.0 would be about as bright as the key
FLOOR = (0.050, 0.070, 0.120)                                         # the least light (linear, cool) a face keeps after exposure, so shadows stay readable
EXPOSE_PCT, EXPOSE_TO = 0.70, 1.0                                     # exposure: the 70th percentile ground corner (open, sunlit meadow) lands at this light, so sunlit ground shows its albedo
R = VS.R_PLANET
SKIRT = 0.8                                                           # buildings, stalls and trunks reach this far below their base so no gap shows on the uneven ground
VILLAGE_R = VS.VILLAGE_R
PLAZA_STEP = 1.0                                                      # the plaza's paving is laid in rings this wide (metres), the meadow beyond in cells of 2.4 m and up


def sag(r): return math.sqrt(max(R * R - r * r, 1.0)) - R              # how far the planet's surface drops away from the tangent plane at distance r (negative)


def lin(c): return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3])


def disp(x): return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def shoulder(x, x0=0.80):
    """display value to display value: unchanged up to x0, then a smooth shoulder that never reaches 1 (colours stay inside the X3D range)"""
    return max(0.0, x) if x <= x0 else 1.0 - (1.0 - x0) * math.exp(-(x - x0) / (1.0 - x0))


def luma(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def colour_mesh(me, albedo):
    """albedo: one (r, g, b, emit) per face, in face order. `Alb` keeps it (display values, emit in the alpha channel); `Col` is what gets exported, the albedo until the bake has run."""
    alb = me.color_attributes.new(name='Alb', type='FLOAT_COLOR', domain='CORNER')
    col = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
    for poly, c in zip(me.polygons, albedo):
        for li in poly.loop_indices: alb.data[li].color = c; col.data[li].color = (c[0], c[1], c[2], 1.0)
    me.color_attributes.active_color = col; me.color_attributes.render_color_index = me.color_attributes.find('Col')


class MB:
    """a thing under construction (a house, a tree, a lamp): parts share vertices inside themselves; every face gets an albedo and a share of glow (the light itself comes from the bake)"""
    def __init__(self): self.bm = bmesh.new(); self.alb = []

    def part(self, fn, colour, emit=0.0):
        """fn(bm) -> faces; colour is an RGB or a function of the face normal; normals are made outward and the albedo noted per face"""
        faces = fn(self.bm)
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        for f_ in faces:
            f_.normal_update(); c = colour(f_.normal) if callable(colour) else colour
            self.alb.append((c[0], c[1], c[2], emit))
        return faces


class Bank:
    """many placed copies of things, merged into one mesh (one draw call in the page); the faces keep the order they were made in, so `alb` lines up with them"""
    def __init__(self, name): self.name = name; self.bm = bmesh.new(); self.alb = []

    def add(self, t, mat, tint=(1.0, 1.0, 1.0)):
        vm = {v: self.bm.verts.new(mat @ v.co) for v in t.bm.verts}
        for f_, a in zip(t.bm.faces, t.alb):
            self.bm.faces.new([vm[v] for v in f_.verts]); self.alb.append((min(1.0, a[0] * tint[0]), min(1.0, a[1] * tint[1]), min(1.0, a[2] * tint[2]), a[3]))

    def mesh(self):
        self.bm.faces.ensure_lookup_table()
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()                    # to_mesh keeps the face order
        for p in me.polygons: p.use_smooth = False
        colour_mesh(me, self.alb); return me


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


def ring_block(z0, h, r_in, r_out, sides=16):
    """a closed ring (a coping, a kerb, a collar): an outer wall, a top, an inner wall and an underside, so the bake has a proper solid to light"""
    def fn(bm):
        rs = [[bm.verts.new((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)] for r, z in ((r_out, z0), (r_out, z0 + h), (r_in, z0 + h), (r_in, z0))]
        return [bm.faces.new((rs[a][k], rs[a][(k + 1) % sides], rs[b][(k + 1) % sides], rs[b][k])) for k in range(sides) for a, b in ((0, 1), (1, 2), (2, 3), (3, 0))]
    return fn


def strut(a, b, r0, r1, sides=3):
    """a thin tapered prism from point a to point b, closed at both ends: a jet of water, a falling sheet"""
    def fn(bm):
        a_, b_ = Vector(a), Vector(b); ax = (b_ - a_).normalized()
        h = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0)); u = ax.cross(h).normalized(); w = ax.cross(u)
        rings = [[bm.verts.new(c + (u * math.cos(2 * math.pi * k / sides + math.pi / 2) + w * math.sin(2 * math.pi * k / sides + math.pi / 2)) * r) for k in range(sides)] for c, r in ((a_, r0), (b_, r1))]
        fs = [bm.faces.new((rings[0][k], rings[0][(k + 1) % sides], rings[1][(k + 1) % sides], rings[1][k])) for k in range(sides)]
        return fs + [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[1])]
    return fn


def ball(c, r, sub=1):
    def fn(bm):
        g = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(Vector(c)))
        return [f_ for f_ in bm.faces if f_.verts[0] in g['verts']]
    return fn


# ---- colours (display values, as picked by eye; the bake works in linear light) ----
CREAM = [(1.0, 0.88, 0.66), (0.95, 0.80, 0.58), (0.98, 0.84, 0.72)]
TERRA = [(0.86, 0.40, 0.24), (0.78, 0.30, 0.20), (0.90, 0.52, 0.28)]
WOOD = (0.50, 0.32, 0.18)
DOOR = (0.30, 0.18, 0.12)
GOLD = (1.0, 0.80, 0.34)
GRASS = [(0.42, 0.60, 0.28), (0.34, 0.52, 0.26), (0.50, 0.62, 0.30)]
PAVE = [(0.70, 0.60, 0.46), (0.62, 0.53, 0.41)]                          # cobbles: sandstone in two tones, laid as a checker
SPOKE, BAND, KERB = (0.66, 0.37, 0.24), (0.38, 0.43, 0.50), (0.50, 0.44, 0.36)   # terracotta spokes, slate ring bands, the kerb
STEP_ST, WALL_LO, WALL_ST, COPING = (0.58, 0.52, 0.45), (0.56, 0.50, 0.43), (0.70, 0.62, 0.52), (0.82, 0.74, 0.62)      # the fountain's step, wall (two bands) and coping
PLINTH = (0.62, 0.58, 0.52)
GLASS, FRAME = (1.0, 0.80, 0.42), (0.95, 0.90, 0.80)                    # a window lit from inside, in a pale frame
WATER, SPRAY = (0.30, 0.68, 0.90), (0.88, 0.96, 1.0)


def window(m, wall, plane, u, z0, w, h):
    """a lit window with a pale frame, standing 0.16 to 0.2 m off a wall: wall 'f' faces -Y, 'b' +Y, 'l' -X, 'r' +X; `plane` is where the wall is, `u` the window's place along it"""
    sgn = -1.0 if wall in 'fl' else 1.0
    if wall in 'fb': fr = ((u, plane + sgn * 0.07, 0), (w + 0.4, 0.18, h + 0.4)); gl = ((u, plane + sgn * 0.10, 0), (w, 0.2, h))
    else: fr = ((plane + sgn * 0.07, u, 0), (0.18, w + 0.4, h + 0.4)); gl = ((plane + sgn * 0.10, u, 0), (0.2, w, h))
    m.part(box(fr[0], fr[1], 1.0, z0=z0 - 0.2), FRAME); m.part(box(gl[0], gl[1], 1.0, z0=z0), GLASS, emit=0.85)


def cottage(v):
    m = MB(); w, d, h = 7.0, 6.0, 3.2; roof = TERRA[v % 3]
    m.part(box((0, 0, 0), (w + 0.3, d + 0.3, 0.55 + SKIRT), 1.0, z0=-SKIRT), PLINTH)
    m.part(box((0, 0, 0), (w, d, h - 0.4), 1.0, z0=0.4), CREAM[v % 3]); m.part(gable((0, 0, 0), w, d, h, 2.3), roof)
    m.part(box((0, 0, 0), (0.45, d + 0.9, 0.22), 1.0, z0=h + 2.3 - 0.06), tuple(x * 0.82 for x in roof))                                    # ridge cap
    m.part(box((0, -d / 2 - 0.05, 0), (1.1, 0.2, 2.1), 1.0, z0=0.0), DOOR); m.part(box((0, -d / 2 - 0.45, 0), (1.5, 0.7, 0.18), 1.0, z0=0.0), PLINTH)      # door and its step
    m.part(box((w / 2 - 1.3, 0.8, 0), (0.9, 0.9, 5.2 - 0.4), 1.0, z0=0.4), (0.62, 0.50, 0.42)); m.part(box((w / 2 - 1.3, 0.8, 0), (1.15, 1.15, 0.22), 1.0, z0=5.2), (0.40, 0.36, 0.34))
    for u in (-2.2, 2.2): window(m, 'f', -d / 2, u, 1.1, 1.0, 1.2)
    window(m, 'b', d / 2, 0.0, 1.1, 1.0, 1.2); window(m, 'l', -w / 2, 0.0, 1.1, 1.0, 1.2); window(m, 'r', w / 2, -1.2, 1.1, 1.0, 1.2)
    return m


def house(v):
    m = MB(); w, d, h = 8.5, 7.0, 5.4; roof = TERRA[(v + 2) % 3]
    m.part(box((0, 0, 0), (w + 0.3, d + 0.3, 0.55 + SKIRT), 1.0, z0=-SKIRT), PLINTH)
    m.part(box((0, 0, 0), (w, d, h - 0.4), 1.0, z0=0.4), CREAM[(v + 1) % 3]); m.part(hip((0, 0, 0), w, d, h, 2.6), roof)
    m.part(box((0, -d / 2 - 0.05, 0), (1.2, 0.2, 2.2), 1.0, z0=0.0), DOOR); m.part(box((0, -d / 2 - 0.45, 0), (1.6, 0.7, 0.18), 1.0, z0=0.0), PLINTH)
    for u in (-2.8, 2.8): window(m, 'f', -d / 2, u, 0.9, 1.1, 1.4)
    for u in (-2.8, 0.0, 2.8): window(m, 'f', -d / 2, u, 3.2, 1.1, 1.4)
    for u in (-1.6, 1.6): window(m, 'l', -w / 2, u, 3.2, 1.1, 1.4); window(m, 'r', w / 2, u, 3.2, 1.1, 1.4)
    window(m, 'l', -w / 2, 0.0, 0.9, 1.1, 1.4); window(m, 'r', w / 2, 0.0, 0.9, 1.1, 1.4)
    return m


def hall(v):
    m = MB(); w, d, h = 15.0, 9.5, 5.6; roof = TERRA[v % 3]
    m.part(box((0, 0, 0), (w + 0.4, d + 0.4, 0.65 + SKIRT), 1.0, z0=-SKIRT), PLINTH)
    m.part(box((0, 0, 0), (w, d, h - 0.5), 1.0, z0=0.5), (0.96, 0.86, 0.66)); m.part(gable((0, 0, 0), w, d, h, 4.2, 0.6), roof)
    m.part(box((0, 0, 0), (0.5, d + 1.4, 0.26), 1.0, z0=h + 4.2 - 0.07), tuple(x * 0.82 for x in roof))
    m.part(box((0, -d / 2 - 0.05, 0), (2.4, 0.3, 3.6), 1.0, z0=0.0), DOOR); m.part(box((0, -d / 2 - 0.55, 0), (3.2, 0.9, 0.2), 1.0, z0=0.0), PLINTH)
    m.part(box((w / 2 - 1.5, 0, 0), (3.0, 3.0, 12.0 - 0.5), 1.0, z0=0.5), (0.94, 0.82, 0.62)); m.part(cone((w / 2 - 1.5, 0, 0), 12.0, 5.0, 2.6, 4), GOLD, emit=0.2)
    for u in (-6.0, -3.2, 3.2): window(m, 'f', -d / 2, u, 1.5, 1.2, 2.4)
    window(m, 'f', -d / 2, 6.0, 1.5, 1.2, 2.4)
    m.part(box((w / 2 - 1.5, -1.5 - 0.07, 0), (1.9, 0.16, 1.9), 1.0, z0=8.4), (0.98, 0.96, 0.90), emit=0.25)                                    # the clock face on the tower
    for z in (8.9, 9.65): m.part(box((w / 2 - 1.5, -1.5 - 0.15, 0), (0.7 if z > 9 else 0.1, 0.1, 0.1 if z > 9 else 0.7), 1.0, z0=z), (0.25, 0.20, 0.18))
    return m


def mill():
    m = MB()
    m.part(prism((0, 0), -SKIRT, 13.0 + SKIRT, 3.6, 2.6, 8), (0.94, 0.84, 0.66)); m.part(cone((0, 0), 13.0, 4.6, 3.0, 8), TERRA[0])
    m.part(box((0, -3.45, 0), (1.2, 0.3, 2.2), 1.0, z0=0.0), DOOR)
    for k in range(4):                                                            # four sails: flat slats on the front
        a = k * math.pi / 2 + math.pi / 4
        m.part(lambda bm, a=a: _sail(bm, a), WOOD)
    return m


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
    m.part(box((0, 0.1, 0), (2.8, 1.2, 0.12), 1.0, z0=1.0), (0.80, 0.62, 0.34))                                                                  # the counter top
    for k in range(4):                                                             # a striped awning, lit on top and shaded underneath
        x0 = -1.6 + k * 0.8; q = ((x0, -1.4, 2.6), (x0 + 0.8, -1.4, 2.6), (x0 + 0.8, 0.9, 3.0), (x0, 0.9, 3.0))
        m.part(lambda bm, q=q: [bm.faces.new([bm.verts.new(p) for p in q])], cols[(k + v) % 2])
        m.part(lambda bm, q=q: [bm.faces.new([bm.verts.new((p[0], p[1], p[2] - 0.04)) for p in q[::-1]])], tuple(0.7 * x for x in cols[(k + v) % 2]))
    for x in (-1.5, 1.5): m.part(prism((x, 0.8), 0.0, 3.0, 0.08, 0.08, 4), WOOD)
    return m


def lamp():
    m = MB(); m.part(prism((0, 0), 0.0, 3.4, 0.14, 0.09, 6), (0.40, 0.32, 0.26)); m.part(ball((0, 0, 3.6), 0.34, 1), (1.0, 0.92, 0.6), emit=0.9)
    return m


def tree(kind):
    m = MB()
    if kind == 0:                                                                  # pine
        m.part(prism((0, 0), -0.4, 2.2, 0.28, 0.2, 6), WOOD); m.part(cone((0, 0), 1.2, 4.6, 2.0, 7), (0.20, 0.46, 0.34)); m.part(cone((0, 0), 3.2, 4.0, 1.5, 7), (0.24, 0.52, 0.36))
        m.part(cone((0, 0), 5.2, 3.2, 1.0, 7), (0.28, 0.56, 0.38))
    elif kind == 1:                                                                # round, autumn gold
        m.part(prism((0, 0), -0.4, 3.0, 0.32, 0.24, 6), WOOD); m.part(ball((0, 0, 4.4), 2.5, 1), (0.88, 0.70, 0.28)); m.part(ball((0.9, 0.5, 5.3), 1.7, 0), (0.82, 0.56, 0.24))
        m.part(ball((-1.2, -0.6, 5.0), 1.4, 0), (0.92, 0.62, 0.26))
    else:                                                                          # poplar
        m.part(prism((0, 0), -0.4, 2.0, 0.24, 0.18, 6), WOOD); m.part(cone((0, 0), 1.2, 9.0, 1.3, 6), (0.30, 0.55, 0.32))
    return m


def fountain():
    """a stepped basin with a coping and a pool, a column with a bowl, twelve sheets that fall from the bowl and ten jets of different heights that arc over the pool (the water is drawn glowing, light-blue to white)"""
    m = MB(); FR = VS.FOUNTAIN_R; N = 16; Z = 0.60                                         # N sides; Z is the pool's level
    m.part(prism((0, 0), 0.0, 0.2, FR + 0.9, FR + 0.8, N), STEP_ST)                         # a low step all round
    m.part(ring_block(0.15, 0.40, FR - 0.5, FR, N), WALL_LO)                                # the wall's foot
    m.part(ring_block(0.55, 0.20, FR - 0.5, FR - 0.05, N), WALL_ST)                         # its upper band, set back a little
    m.part(ring_block(0.75, 0.09, FR - 0.62, FR + 0.12, N), COPING)                         # the coping, proud of the wall
    m.part(prism((0, 0), 0.15, Z - 0.15, FR - 0.5, FR - 0.5, N), WATER, emit=0.40)           # the pool
    m.part(prism((0, 0), 0.0, 1.9, 1.0, 0.7, 8), (0.80, 0.72, 0.60))                       # the column
    m.part(prism((0, 0), 1.9, 0.4, 1.6, 1.4, 10), (0.84, 0.78, 0.66)); m.part(prism((0, 0), 2.3, 0.06, 1.25, 1.25, 10), WATER, emit=0.40)
    m.part(ring_block(2.3, 0.14, 1.25, 1.72, 10), COPING)                                   # the bowl, its water and its coping
    for k in range(12):                                                                   # sheets falling from the bowl's lip to the pool, in four bars each
        c, s_ = math.cos(2 * math.pi * k / 12 + 0.13), math.sin(2 * math.pi * k / 12 + 0.13)
        pts = [(1.72 + 0.8 * t, 2.4 - 1.8 * t * t) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]): m.part(strut((r0 * c, r0 * s_, z0), (r1 * c, r1 * s_, z1), 0.05, 0.04), SPRAY, emit=0.55)
    for k in range(10):                                                                   # jets that rise from the pool near its rim and arc back into it, each a little higher or lower than its neighbour
        c, s_ = math.cos(2 * math.pi * k / 10), math.sin(2 * math.pi * k / 10); peak = 1.3 + 0.55 * ((k * 7) % 5) / 4
        pts = [(3.4 - 0.7 * t, Z + 4 * peak * t * (1 - t)) for t in (i / 8 for i in range(9))]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]): m.part(strut((r0 * c, r0 * s_, z0), (r1 * c, r1 * s_, z1), 0.04, 0.028), SPRAY, emit=0.55)
    return m


def mast():
    """the tether mast: a gold needle from the fountain's centre, with rings; the tether leaves its tip"""
    m = MB(); m.part(prism((0, 0), 2.4, VS.MAST_H, 0.55, 0.06, 8), GOLD, emit=0.75); m.part(prism((0, 0), 2.4, 0.9, 0.85, 0.62, 8), (1.0, 0.92, 0.6), emit=0.45)
    for z in (14.0, 30.0, 46.0): m.part(prism((0, 0), z, 0.5, 1.3 - z / 60.0 * 0.6, 1.3 - z / 60.0 * 0.6, 8), (1.0, 0.92, 0.6), emit=0.45)
    return m


# ---- the ground ----
def fld(x, y, s, seed): return noise.fractal(Vector((x * s, y * s, seed)), 1.0, 2.0, 3, noise_basis='PERLIN_ORIGINAL')     # a smooth field, about -0.5 to 0.5


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def mix(a, b, t): return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def ground_z(x, y):
    r = math.hypot(x, y)
    return sag(r) + (0.0 if r < 20 else 0.30 * fld(x, y, 0.06, 0.0))


def road_d(x, y): return min(abs(x), abs(y))                                                         # distance to the nearest of the two road axes


def field_kind(x, y):
    """0 meadow, 1 wheat, 2 ploughed: patches beyond the trees' meadow, fading out before the edge so the cap meets the planet's own green"""
    r = math.hypot(x, y)
    if r < 44 or r > 76 or road_d(x, y) < 5.5: return 0
    f = fld(x, y, 0.05, 23.0)
    return 1 if f > 0.14 else (2 if f < -0.17 else 0)


def ground_albedo(x, y, rng, ring=0, sec=0, spoke=False):
    r = math.hypot(x, y)
    if r < VS.PLAZA_R:
        c = PAVE[(ring + sec) % 2]                                                                       # cobbles: a checker of two tones, one cell to a ring and sector
        if r < VS.FOUNTAIN_R + 1.4: c = mix(c, (0.84, 0.78, 0.66), 0.5)                                   # paler round the basin
        if spoke and r > VS.FOUNTAIN_R + 0.9: c = SPOKE                                                  # eight terracotta spokes (a compass rose), one sector wide
        elif 6.0 <= r < 7.0 or 12.0 <= r < 13.0: c = BAND                                                # two slate bands
        elif r >= 14.0: c = KERB                                                                         # the kerb
        return tuple(min(1.0, x_ * (0.94 + 0.12 * rng.random())) for x_ in c)
    g = mix(GRASS[1], GRASS[2], smooth(-0.30, 0.30, fld(x, y, 0.045, 5.0))); g = mix(g, GRASS[0], smooth(0.10, 0.45, fld(x, y, 0.09, 8.0)) * 0.7)
    fk = field_kind(x, y)
    if fk == 1: g = mix(g, (0.86, 0.72, 0.34), 0.88)
    elif fk == 2: g = mix(g, (0.52, 0.38, 0.24), 0.85)
    d = road_d(x, y)
    if d < 4.2:
        road = (0.88, 0.78, 0.58); t = smooth(4.2, 2.6, d); g = mix(g, road, t)                          # the roads are 6.4 m wide, with a soft verge
    return tuple(min(1.0, x_ * (0.93 + 0.14 * rng.random())) for x_ in g)


def cell(r): return 2.4 + 1.2 * smooth(30.0, 70.0, r)                                                 # the ground's cell size in metres, coarser toward the edge


def ground(bank):
    """the cap of the planet under the village, as a polar mesh: 2 m rings in the plaza, then cells of 2.4 m growing to 3.6 m, 12 to 192 sectors so a cell is never much longer than
    wide, curved by sag(); one extra ring dips below the planet's surface so the edge disappears into it"""
    radii = [0.0]; r = 0.0
    while r < VS.PLAZA_R - 1e-6: r += PLAZA_STEP; radii.append(r)
    while r + cell(r) < VILLAGE_R - 0.35 * cell(r): r += cell(r); radii.append(r)
    radii.append(VILLAGE_R); n_of = []
    for r in radii[1:]:
        n = 12; reach = 1.25 * PLAZA_STEP if r <= VS.PLAZA_R + 1e-6 else 1.6 * cell(r)
        while 2 * math.pi * r / n > reach: n *= 2
        n_of.append(max(n, n_of[-1] if n_of else 0))
    skirt_r = VILLAGE_R + 2.5; radii.append(skirt_r); n_of.append(n_of[-1])
    bm = bank.bm; rng = random.Random(7)
    rows = [[bm.verts.new((0.0, 0.0, ground_z(0.0, 0.0)))]]
    for i, r in enumerate(radii[1:], 1):
        n = n_of[i - 1]; row = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n; x, y = r * math.cos(a), r * math.sin(a)
            row.append(bm.verts.new((x, y, ground_z(x, y) - (1.0 if r == skirt_r else 0.0))))
        rows.append(row)
    def face(vs, ring, sec):
        f_ = bm.faces.new(vs); f_.normal_update()
        if f_.normal.z < 0: f_.normal_flip()
        cx = sum(v.co.x for v in vs) / len(vs); cy = sum(v.co.y for v in vs) / len(vs); rr = math.hypot(cx, cy)
        if rr > VILLAGE_R: cx, cy = cx * (VILLAGE_R - 0.5) / rr, cy * (VILLAGE_R - 0.5) / rr                          # the skirt takes the meadow's colour at the edge
        ac = math.atan2(cy, cx); d = [(math.atan2(v.co.y, v.co.x) - ac + math.pi) % (2 * math.pi) - math.pi for v in vs]
        spoke = any(min(d) + 1e-6 < ((j * math.pi / 4 - ac + math.pi) % (2 * math.pi) - math.pi) < max(d) - 1e-6 for j in range(8))              # one of the eight compass lines runs through this face
        bank.alb.append(ground_albedo(cx, cy, rng, ring, sec, spoke) + (0.0,))
    n1 = len(rows[1])
    for k in range(n1): face([rows[0][0], rows[1][k], rows[1][(k + 1) % n1]], 0, k)
    for i in range(1, len(rows) - 1):
        a, b = rows[i], rows[i + 1]; na, nb = len(a), len(b)
        for k in range(na):
            if nb == na: face([a[k], b[k], b[(k + 1) % nb], a[(k + 1) % na]], i, k)
            else: face([a[k], b[2 * k], b[2 * k + 1]], i, k); face([a[k], b[2 * k + 1], b[(2 * k + 2) % nb], a[(k + 1) % na]], i, k)
    return len(radii), n_of


def place(x, y, yaw=0.0, scale=1.0):
    """the matrix that stands an object upright on the planet at (x, y): z follows the ground, the object leans to the local vertical"""
    z = ground_z(x, y) - 0.05
    n = (Vector((x, y, z)) - Vector((0, 0, -R))).normalized()
    q = Vector((0, 0, 1)).rotation_difference(n) @ Quaternion((0, 0, 1), yaw)
    return Matrix.LocRotScale(Vector((x, y, z)), q, Vector((scale, scale, scale)))


def tint(rng, amt):
    j = 1 + amt * (2 * rng.random() - 1); h = 0.5 * amt * (2 * rng.random() - 1); return (j * (1 + h), j, j * (1 - h))


# ---- the bake ----
def setup_light(samples, sky_strength, key_strength):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = False; sc.cycles.seed = 11; sc.cycles.sample_clamp_indirect = 4.0
    w = bpy.data.worlds.new('village'); w.use_nodes = True; sc.world = w; nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'; sky.sun_disc = False; sky.sun_elevation = math.radians(SKY_ELEV); sky.sun_rotation = math.radians(KEY_AZ)
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = sky_strength; out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    e, a = math.radians(KEY_ELEV), math.radians(KEY_AZ)
    toward = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))                  # from the village to the lamp
    ld = bpy.data.lights.new('key', 'SUN'); ld.energy = key_strength; ld.color = KEY_COL; ld.angle = math.radians(KEY_ANGLE)
    lo = bpy.data.objects.new('key', ld); sc.collection.objects.link(lo); lo.rotation_euler = (-toward).to_track_quat('-Z', 'Y').to_euler()
    mat = bpy.data.materials.new('albedo'); mat.use_nodes = True; nt = mat.node_tree; bsdf = nt.nodes.get('Principled BSDF')
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Alb'; nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])      # the bounce off a wall is the colour of the wall
    bsdf.inputs['Roughness'].default_value = 1.0
    return mat


def bake(obs, mat):
    """Cycles bake of direct plus indirect light on every face corner of every object, into the `Light` attribute (white-lit: each face's own albedo is left out)"""
    for ob in obs:
        me = ob.data; me.materials.append(mat)
        li = me.color_attributes.new(name='Light', type='FLOAT_COLOR', domain='CORNER'); me.color_attributes.active_color = li; me.color_attributes.render_color_index = me.color_attributes.find('Light')
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bk = bpy.context.scene.render.bake; bk.target = 'VERTEX_COLORS'; bk.use_pass_direct = True; bk.use_pass_indirect = True; bk.use_pass_color = False
    bpy.ops.object.bake(type='DIFFUSE')


def finish(ob, expo):
    """light x albedo, with exposure, a floor, the glow share, the shoulder and the sRGB curve, into `Col`; then the helper attributes go"""
    me = ob.data; alb = me.color_attributes['Alb']; li = me.color_attributes['Light']; col = me.color_attributes['Col']; out = []
    for p in me.polygons:
        for k in p.loop_indices:
            L = [x * expo if x == x else 0.0 for x in li.data[k].color[:3]]
            L = [max(L[i], FLOOR[i]) for i in range(3)]
            a = alb.data[k].color; al = lin(a); e = a[3]
            c = tuple(shoulder(disp(al[i] * L[i])) * (1 - e) + min(1.0, a[i]) * e for i in range(3))
            col.data[k].color = (c[0], c[1], c[2], 1.0); out.append(c)
    me.color_attributes.active_color = col; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for nm in ('Alb', 'Light'): me.color_attributes.remove(me.color_attributes[nm])
    me.materials.clear()
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'village'))
    ap.add_argument('--samples', type=int, default=384); ap.add_argument('--sky', type=float, default=SKY_STRENGTH); ap.add_argument('--key', type=float, default=KEY_STRENGTH)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    m = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = m; spec.loader.exec_module(m); m.register()
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'
    bpy.ops.wm.read_factory_settings(use_empty=True); coll = bpy.context.scene.collection
    rng = random.Random(1618)
    banks = {k: Bank(k) for k in ('Ground', 'Buildings', 'Props', 'Trees')}
    rings, sectors = ground(banks['Ground'])
    fo, ma = fountain(), mast()
    banks['Props'].add(fo, Matrix.Translation((0, 0, 0.05))); banks['Props'].add(ma, Matrix.Translation((0, 0, 0.05)))
    cot = [cottage(i) for i in range(3)]; hou = [house(i) for i in range(3)]; hl = [hall(0), hall(1)]; mi = mill(); st = [stall(0), stall(1)]; la = lamp(); tr = [tree(0), tree(1), tree(2)]
    placed = []; count = 0
    def face_centre(t, r, th, amt=0.04):
        nonlocal count
        x, y = r * math.cos(th), r * math.sin(th); yaw = th - math.pi / 2                                   # the front (-Y) faces the plaza centre
        banks['Buildings'].add(t, place(x, y, yaw), tint(rng, amt)); placed.append((x, y, 7.5)); count += 1
    for k in range(8): face_centre(cot[k % 3], 27.0, math.radians(k * 45 + 10))
    for k in range(6): face_centre(hou[k % 3], 42.0, math.radians(k * 60 + 24))
    face_centre(hl[0], 34.0, math.radians(205)); face_centre(hl[1], 36.0, math.radians(75))
    x, y = 54.0 * math.cos(math.radians(315)), 54.0 * math.sin(math.radians(315)); banks['Buildings'].add(mi, place(x, y, math.radians(315) - math.pi / 2)); placed.append((x, y, 6.0)); count += 1
    for k in range(6): face_centre(st[k % 2], 11.5, math.radians(k * 60 + 30), 0.06)
    for k in range(12):
        th = math.radians(k * 30 + 15); banks['Props'].add(la, place(15.4 * math.cos(th), 15.4 * math.sin(th), 0.0))
    n_trees = 0; tries = 0
    while n_trees < 70 and tries < 4000:
        tries += 1; r = rng.uniform(21.0, 76.0); th = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(th), r * math.sin(th)
        if road_d(x, y) < 5.0 or field_kind(x, y) != 0: continue                                              # keep the roads clear, and the fields
        if any(math.hypot(x - px, y - py) < pr + 2.5 for px, py, pr in placed): continue
        kind = rng.choice([0, 0, 1, 2]); banks['Trees'].add(tr[kind], place(x, y, rng.uniform(0, 6.28), rng.uniform(0.8, 1.35)), tint(rng, 0.10)); placed.append((x, y, 2.0)); n_trees += 1
    faces = {k: len(b.alb) for k, b in banks.items()}
    for t in [fo, ma] + cot + hou + hl + [mi] + st + [la] + tr: t.bm.free()
    obs = []
    for k, b in banks.items():
        ob = bpy.data.objects.new(k, b.mesh()); coll.objects.link(ob); obs.append(ob)
    mat = setup_light(a.samples, a.sky, a.key); bake(obs, mat)
    lum = lambda ob: sorted(luma(d.color) for d in ob.data.color_attributes['Light'].data)
    g = lum(obs[0]); expo = EXPOSE_TO / g[int(len(g) * EXPOSE_PCT)]
    stats = {}
    for ob in obs:
        l = [x * expo for x in lum(ob)]; stats[ob.name] = dict(light_p05=round(l[int(len(l) * 0.05)], 3), light_p50=round(l[len(l) // 2], 3), light_p95=round(l[int(len(l) * 0.95)], 3))
        finish(ob, expo)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    path = os.path.join(out, 'village.x3d')
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=False, meta_creator='Gobbler demiurge', meta_title='Aurelsbrunn',
                             meta_description='A village on a planet 250 m in radius: plaza, fountain, tether mast, 17 buildings, 6 stalls, 12 lamps, %d trees; made in Blender, light baked in Cycles' % n_trees)
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    rec = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), village_spec_sha256=sha(os.path.join(HERE, 'village_spec.py')),
               bake=dict(engine='Cycles CPU', samples=a.samples, key=dict(azimuth=KEY_AZ, elevation=KEY_ELEV, colour=KEY_COL, strength=a.key, disc_degrees=KEY_ANGLE),
                         sky=dict(type='multiple scattering, disc off', sun_elevation=SKY_ELEV, strength=a.sky), passes='direct + indirect, albedo-coloured bounce',
                         exposure=round(expo, 4), exposure_rule='%d%% ground corner -> %.2f' % (EXPOSE_PCT * 100, EXPOSE_TO), floor_linear=FLOOR, shoulder_from=0.80, light_stats=stats),
               meshes=faces, ground=dict(rings=rings, sectors_outer=sectors[-1]), objects=len(obs), buildings=count - 6, stalls=6, lamps=12, trees=n_trees, file='village.x3d',
               bytes=os.path.getsize(path), sha256=sha(path))
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w'), indent=1); print(json.dumps(rec))


main()
