"""Model a khachkar (an Armenian cross-stone) for the plaza of Aurelsbrunn in Blender, bake its light in Cycles with the village's own rig and export it through x3d-blender-io.

    python3 tools/blender_khachkar.py [--blenderio /path/to/x3d-blender-io/source] [--out assets/khachkar] [--samples 384]     (a Python that can `import bpy`, and shapely 2.1 or later)
    python3 tools/blender_khachkar.py --plan out.png                                                                            (no bpy: draw the face's carving plan, for checking)

Writes assets/khachkar/khachkar.x3d (X3D 4.0) and receipt.json. Village metres and axes, as in tools/blender_village.py (+X east, +Y north, +Z up, the plaza centre the origin):
the stone is modelled in place, at KHACHKAR_R metres from the fountain at azimuth KHACHKAR_AZ (tools/world_layer.py), standing upright on the curve of the planet with its carved face
toward the fountain, so the bake sees it in the same light and from the same side as the village it stands in. tools/world.py adds it to the village's lazy file.

The stone, from the ground up: a stepped pedestal of three dark basalt blocks; a slab of warm tufa 1.0 m wide, 0.3 m thick and 2.22 m tall; a cornice that projects over its face.
The slab with its cornice is 2.40 m tall, 2.82 m with the pedestal. The face is carved as real relief, two levels and a third for the bosses: the field is cut 4.5 cm back,
and what stands proud of it is the classic composition: a cross whose four arms flare and end in a pair of round buds with a small bud between them, standing on a
wheel of eternity (arevakhach, eight whirling blades in a ring) at its foot, two shoots that grow from the wheel and curl under the side arms, two small rosettes over the
side arms, and a frame of interlace (a two-strand plait: the pockets between the strands are cut back to the field) down both sides and across the top.

The carving is drawn as plane figures (shapely: unions, buffers, differences) and turned into faces: the raised tops are triangulated (constrained Delaunay), the walls
are quads between the levels along every outline, and the field is cut into a 7 cm grid so that the bake has corners where the shadows of the carving fall on it.
Light: the village's rig (a warm key at azimuth 220 and 55 degrees, a sky of 0.25), Cycles on the CPU, and a patch of paving under the stone that receives and bounces
light but is not exported. The exposure rule is the village's (the 70th percentile ground corner, here the patch's, lands at 1.0).
"""
import sys, os, math, json, hashlib, argparse, importlib.util, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import village_spec as VS
from world_layer import KHACHKAR_R, KHACHKAR_AZ                     # where it stands (shared with the page's tag; village_spec.py is pinned by the village's receipt)
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, GeometryCollection, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

KEY_AZ, KEY_ELEV = 220.0, 55.0                                        # the village's rig (tools/blender_village.py), so the stone stands in the same light as the plaza
KEY_COL, KEY_STRENGTH, KEY_ANGLE = (1.0, 0.85, 0.62), 5.0, 6.0
SKY_ELEV, SKY_STRENGTH = 26.0, 0.25
FLOOR = (0.050, 0.070, 0.120)
EXPOSE_PCT, EXPOSE_TO = 0.70, 1.0

# ---- the stone (metres) ----
W, T, HS = 1.00, 0.30, 2.22                    # slab: width, thickness, height of the carved face
CORNICE_H, CORNICE_W, CORNICE_OUT = 0.18, 1.10, 0.08
STEPS = ((1.75, 1.15, 0.14), (1.45, 0.85, 0.14), (1.22, 0.58, 0.14))    # the pedestal: width, depth, height of each block, from the ground up
SKIRT = 0.30                                   # the lowest block reaches this far below the ground, so no gap shows on the curve
Z0 = sum(s[2] for s in STEPS)                  # the slab stands on the pedestal
DEPTH, BOSS = 0.045, 0.012                     # the field is cut DEPTH behind the face; the bosses stand BOSS proud of it
BAND, BAND_FOOT = 0.11, 0.15                   # the frame: the side and top bands carry the plait, the foot band is plain
STRAND = 0.026                                 # the plait's strands
PLAIT_STRETCH = 1.7                            # a plait cell is this many band widths long
GRID = 0.08                                    # the field's cells, for the bake
TOL = 0.006                                    # outlines are simplified to this (metres)

TUFA_HI, TUFA_FACE, TUFA_WALL, TUFA_FIELD = (0.86, 0.64, 0.46), (0.82, 0.59, 0.43), (0.76, 0.53, 0.39), (0.64, 0.42, 0.32)   # weathered faces lighter, the cut field darker and redder
BASALT, BASALT_TOP = (0.50, 0.46, 0.43), (0.56, 0.52, 0.48)
PAVE = (0.66, 0.565, 0.435)                    # the receiver patch: the plaza's two sandstones averaged


def lin(c): return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3])
def disp(x): return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
def shoulder(x, x0=0.80): return max(0.0, x) if x <= x0 else 1.0 - (1.0 - x0) * math.exp(-(x - x0) / (1.0 - x0))
def luma(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def sag(r): return math.sqrt(max(VS.R_PLANET ** 2 - r * r, 1.0)) - VS.R_PLANET


# ---- the carving plan: plane figures on the face (u to the right as you face the stone, v up from the slab's foot) ----
def _polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, (MultiPolygon, GeometryCollection)): return [p for q in g.geoms for p in _polys(q)]
    return []


def plait(x0, y0, x1, y1, vertical):
    """the pockets of a two-strand plait in the band x0..x1, y0..y1: per cell a triangle against each rail and a lozenge across each cell boundary, shrunk by half a strand"""
    L = (y1 - y0) if vertical else (x1 - x0); B = (x1 - x0) if vertical else (y1 - y0)
    n = max(1, round(L / (B * PLAIT_STRETCH))); s = L / n; h = STRAND / 2; out = []
    P = (lambda a, b: (x0 + b, y0 + a)) if vertical else (lambda a, b: (x0 + a, y0 + b))           # a along the band, b across it
    for i in range(n):
        a0, a1, am = i * s, (i + 1) * s, (i + 0.5) * s
        for tri in ([(a0, 0), (a1, 0), (am, B / 2)], [(a0, B), (am, B / 2), (a1, B)]): out.append(Polygon([P(*q) for q in tri]))
        if i < n - 1: out.append(Polygon([P(a1, 0), P(a1 + s / 2, B / 2), P(a1, B), P(a1 - s / 2, B / 2)]))
    return [p.buffer(-h, join_style='mitre') for p in out]


def terminal(cx, cy, ang, w):
    """an arm's end, pointing along ang from (cx, cy): two round buds side by side, each with a drilled eye, and a pointed bud between them that reaches a little further"""
    c, s = math.cos(ang), math.sin(ang); at = lambda a, b: (cx + a * c - b * s, cy + a * s + b * c)
    g = [Point(at(0.0, side * 0.50 * w)).buffer(0.50 * w, quad_segs=5) for side in (-1, 1)]
    g.append(Polygon([at(0.0, -0.28 * w), at(0.72 * w, 0.0), at(0.0, 0.28 * w)]).buffer(0.07 * w, quad_segs=2))
    g.append(Polygon([at(-0.45 * w, -0.85 * w), at(-0.45 * w, 0.85 * w), at(0.0, 0.6 * w), at(0.0, -0.6 * w)]))
    eyes = [Point(at(0.04 * w, side * 0.56 * w)).buffer(0.13 * w, quad_segs=2) for side in (-1, 1)]
    return unary_union(g).difference(unary_union(eyes))


def arm(cx, cy, ang, length, w0, w1, end=True):
    """a flared arm from the centre (cx, cy) along ang: width w0 at the centre, w1 where it meets its terminal (or, with end=False, where it meets the wheel)"""
    c, s = math.cos(ang), math.sin(ang); at = lambda a, b: (cx + a * c - b * s, cy + a * s + b * c)
    wm = 0.62 * w0 + 0.38 * w1
    body = Polygon([at(0, -w0 / 2), at(0.55 * length, -wm / 2), at(length, -w1 / 2), at(length, w1 / 2), at(0.55 * length, wm / 2), at(0, w0 / 2)])
    if not end: return body
    tw = w1 * 0.80
    return unary_union([body, terminal(*at(length + 0.42 * tw, 0), ang, tw)])


def wheel(cx, cy, R):
    """the wheel of eternity: a ring, a hub and eight blades that whirl from the hub to the ring"""
    ring = Point(cx, cy).buffer(R, quad_segs=10).difference(Point(cx, cy).buffer(R - 0.028, quad_segs=10))
    hub = Point(cx, cy).buffer(0.05, quad_segs=5); g = [ring, hub]; r0, r1 = 0.035, R - 0.02; n = 8; twist = 1.25
    for k in range(n):
        a0 = 2 * math.pi * k / n; wd = 0.46 * 2 * math.pi / n; lead, trail = [], []
        for i in range(7):
            t = i / 6; r = r0 + (r1 - r0) * t; a = a0 + twist * t * t
            wdt = wd * (0.35 + 0.65 * math.sin(math.pi * min(1.0, 0.15 + t)))                              # a blade is narrow at the hub and swells outward
            lead.append((cx + r * math.cos(a), cy + r * math.sin(a))); trail.append((cx + r * math.cos(a + wdt), cy + r * math.sin(a + wdt)))
        g.append(Polygon(lead + trail[::-1]).buffer(0))
    return unary_union(g)


def shoot(side, v0, v1):
    """a shoot that grows from the wheel, rises beside the lower arm and curls under a side arm, with a leaf"""
    pts = []
    for i in range(15):
        t = i / 14; v = v0 + (v1 - v0) * t
        u = 0.13 + 0.15 * math.sin(math.pi * t * 0.9)
        pts.append((side * u, v))
    cx, cy, rc = side * 0.24, v1 + 0.015, 0.055                                                         # the curl: most of a circle at the top
    a_start = math.atan2(pts[-1][1] - cy, pts[-1][0] - cx)
    for i in range(1, 10):
        a = a_start + side * (-1) * 0.0 + (-side) * i * 0.6; rr = rc * (1 - 0.06 * i)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    stem = LineString(pts).buffer(0.012, quad_segs=2, cap_style='round')
    bx, by = side * 0.262, v0 + 0.36; ang = math.radians(90 - side * 50); L = 0.11                            # a leaf off the stem, pointing out and up: two arcs that meet in points
    c, s = math.cos(ang), math.sin(ang); at = lambda a, b: (bx + a * c - b * s, by + a * s + b * c)
    leaf = Polygon([at(L * t, 0.028 * math.sin(math.pi * t)) for t in (0, .25, .5, .75, 1)] + [at(L * t, -0.028 * math.sin(math.pi * t)) for t in (.75, .5, .25)])
    return unary_union([stem, leaf])


def rosette(cx, cy, r):
    """a small rosette: a disc with six petals cut into it around a boss"""
    d = Point(cx, cy).buffer(r, quad_segs=8)
    cuts = [Point(cx + 0.55 * r * math.cos(a), cy + 0.55 * r * math.sin(a)).buffer(0.20 * r, quad_segs=3) for a in (2 * math.pi * k / 6 + math.pi / 6 for k in range(6))]
    return d.difference(unary_union(cuts))


def plan():
    """-> (slab outline, the raised level, the bosses, a summary): plane figures in metres on the face"""
    slab = sbox(-W / 2, 0, W / 2, HS)
    fx0, fx1, fy0, fy1 = -W / 2 + BAND, W / 2 - BAND, BAND_FOOT, HS - BAND
    field = sbox(fx0, fy0, fx1, fy1)
    frame = slab.difference(field)
    pockets = plait(-W / 2, fy0, fx0, fy1, True) + plait(fx1, fy0, W / 2, fy1, True) + plait(fx0, fy1, fx1, HS, False)
    frame = frame.difference(unary_union(pockets))
    vr, Rr = fy0 + 0.25, 0.215                                  # the wheel
    vc = 1.62                                                   # the crossing
    figs = [frame, wheel(0.0, vr, Rr)]
    figs += [arm(0.0, vc, math.pi / 2, 0.35, 0.095, 0.14), arm(0.0, vc, -math.pi / 2, vc - (vr + Rr) + 0.012, 0.095, 0.15, end=False),
             arm(0.0, vc, 0.0, 0.22, 0.095, 0.14), arm(0.0, vc, math.pi, 0.22, 0.095, 0.14)]
    figs.append(Point(0, vc).buffer(0.075, quad_segs=6))                                          # the crossing's round
    for side in (-1, 1): figs.append(shoot(side, vr + Rr - 0.03, vc - 0.20)); figs.append(rosette(side * 0.235, 1.905, 0.072))
    raised = unary_union(figs).intersection(slab).simplify(TOL, preserve_topology=True)
    bosses = unary_union([Point(0, vc).buffer(0.042, quad_segs=5), Point(0, vr).buffer(0.03, quad_segs=4)] + [Point(s * 0.235, 1.905).buffer(0.024, quad_segs=3) for s in (-1, 1)])
    bosses = bosses.simplify(TOL, preserve_topology=True)
    return slab, raised, bosses


def draw_plan(path, px=420):
    """a picture of the plan (no bpy): field dark, raised level light, bosses lighter"""
    from PIL import Image, ImageDraw
    slab, raised, bosses = plan(); s = px / W; H = int(HS * s)
    im = Image.new('RGB', (px, H), (110, 70, 55)); d = ImageDraw.Draw(im)
    P = lambda c: [(x * s + px / 2, H - y * s) for x, y in c]
    for g, col in ((raised, (215, 160, 128)), (bosses, (240, 200, 170))):
        for p in sorted(_polys(g), key=lambda q: -q.area):
            d.polygon(P(p.exterior.coords), fill=col)
            for r in p.interiors: d.polygon(P(r.coords), fill=(110, 70, 55) if g is raised else (215, 160, 128))
    im.save(path)


# ---- faces ----
class Mesh:
    """vertices and faces with an albedo per face (display values); faces are kept as lists of 3D points and made into one bmesh at the end"""
    def __init__(self): self.faces = []; self.alb = []

    def add(self, pts, colour, want=None):
        """one convex face; `want` is the outward direction it must face (the winding is flipped to match)"""
        if want is not None:
            a, b, c = pts[0], pts[1], pts[2]; n = _cross(_sub(b, a), _sub(c, a))
            if len(pts) > 3 and _dot(n, n) < 1e-14: n = _cross(_sub(c, a), _sub(pts[3], a))
            if _dot(n, want) < 0: pts = pts[::-1]
        self.faces.append(pts); self.alb.append(colour)


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def face_pt(u, v, depth): return (u, -T / 2 + depth, Z0 + v)          # a point on the face: depth 0 is the face, +DEPTH the field (behind it), -BOSS a boss (in front)


def tris(poly):
    out = []
    for t in _polys(constrained_delaunay_triangles(poly)):
        c = list(t.exterior.coords)[:3]
        if Polygon(c).area > 1e-9: out.append(c)
    return out


def flat(m, g, depth, colour):
    for p in _polys(g):
        for t in tris(p): m.add([face_pt(u, v, depth) for u, v in t], colour, (0, -1, 0))


def walls(m, g, d_back, d_front, colour, skip=None):
    """quads between two levels along every outline of g (exterior and holes), each facing away from the material; edges on `skip` (the slab's own outline) are left out"""
    for p in _polys(orient(g, 1.0) if isinstance(g, Polygon) else g):
        p = orient(p, 1.0)
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)
            for (u0, v0), (u1, v1) in zip(c, c[1:]):
                if skip is not None and skip.boundary.buffer(1e-6).contains(LineString([(u0, v0), (u1, v1)])): continue
                du, dv = u1 - u0, v1 - v0
                if du * du + dv * dv < 1e-10: continue
                m.add([face_pt(u0, v0, d_back), face_pt(u1, v1, d_back), face_pt(u1, v1, d_front), face_pt(u0, v0, d_front)], colour, (dv, 0, -du))


def field_cells(m, field):
    """the field, cut into GRID cells so the bake has corners where the carving's shadows fall"""
    x0, y0, x1, y1 = field.bounds; nx = max(1, round((x1 - x0) / GRID)); ny = max(1, round((y1 - y0) / GRID)); gx = (x1 - x0) / nx; gy = (y1 - y0) / ny
    for i in range(nx):
        for j in range(ny):
            cellb = sbox(x0 + i * gx, y0 + j * gy, x0 + (i + 1) * gx, y0 + (j + 1) * gy); piece = field.intersection(cellb)
            if piece.is_empty: continue
            if abs(piece.area - cellb.area) < 1e-9: m.add([face_pt(u, v, DEPTH) for u, v in list(cellb.exterior.coords)[:4]], TUFA_FIELD, (0, -1, 0))
            else: flat(m, piece, DEPTH, TUFA_FIELD)


def grid_quad(m, o, ea, eb, na, nb, colour, want):
    """a rectangle o + s ea + t eb (s, t in 0..1) cut into na x nb quads"""
    P = lambda i, j: tuple(o[k] + ea[k] * i / na + eb[k] * j / nb for k in range(3))
    for i in range(na):
        for j in range(nb): m.add([P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)], colour, want)


def block(m, cx, cy, z0, w, d, h, side, top, n_top=(1, 1), n_side=1, bottom=False):
    x0, x1, y0, y1, z1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, z0 + h
    grid_quad(m, (x0, y0, z1), (w, 0, 0), (0, d, 0), n_top[0], n_top[1], top, (0, 0, 1))
    grid_quad(m, (x0, y0, z0), (w, 0, 0), (0, 0, h), n_top[0], n_side, side, (0, -1, 0)); grid_quad(m, (x0, y1, z0), (w, 0, 0), (0, 0, h), n_top[0], n_side, side, (0, 1, 0))
    grid_quad(m, (x0, y0, z0), (0, d, 0), (0, 0, h), n_top[1], n_side, side, (-1, 0, 0)); grid_quad(m, (x1, y0, z0), (0, d, 0), (0, 0, h), n_top[1], n_side, side, (1, 0, 0))
    if bottom: grid_quad(m, (x0, y0, z0), (w, 0, 0), (0, d, 0), 1, 1, side, (0, 0, -1))


def stone():
    """the whole khachkar in its own frame: base centre at the origin, the carved face toward -Y, +Z up -> (Mesh, counts)"""
    m = Mesh(); slab, raised, bosses = plan(); n0 = {}
    z = -SKIRT
    for k, (w, d, h) in enumerate(STEPS):                                                         # the pedestal
        hh = h + (SKIRT if k == 0 else 0.0)
        block(m, 0.0, 0.0, z, w, d, hh, BASALT, BASALT_TOP, (max(1, round(w / 0.3)), max(1, round(d / 0.3))), 2 if k == 0 else 1); z += hh
    n0['pedestal'] = len(m.faces)
    flat(m, raised.difference(bosses), 0.0, TUFA_FACE); flat(m, bosses, -BOSS, TUFA_HI)          # the carved face: tops of the relief, the bosses
    walls(m, raised, DEPTH, 0.0, TUFA_WALL, skip=slab); walls(m, bosses, 0.0, -BOSS, TUFA_HI)
    open_ = slab.difference(raised); main = open_.intersection(sbox(-W / 2 + BAND, BAND_FOOT, W / 2 - BAND, HS - BAND))
    field_cells(m, main); flat(m, open_.difference(main), DEPTH, TUFA_FIELD)                  # the field in cells; the plait's pockets whole
    n0['face'] = len(m.faces) - n0['pedestal']
    y0, y1 = -T / 2, T / 2                                                                         # the slab's sides and back, cut so the cornice's shadow has corners to land on
    grid_quad(m, (-W / 2, y0, Z0), (0, T, 0), (0, 0, HS), 2, 10, TUFA_WALL, (-1, 0, 0)); grid_quad(m, (W / 2, y0, Z0), (0, T, 0), (0, 0, HS), 2, 10, TUFA_WALL, (1, 0, 0))
    grid_quad(m, (-W / 2, y1, Z0), (W, 0, 0), (0, 0, HS), 5, 10, TUFA_WALL, (0, 1, 0))
    zc = Z0 + HS; yf = -T / 2 - CORNICE_OUT; yb = T / 2 + 0.03; xs = CORNICE_W / 2                  # the cornice: a block with a chamfer under its front edge
    prof = [(yf + 0.05, zc), (yf, zc + 0.07), (yf, zc + CORNICE_H), (yb, zc + CORNICE_H), (yb, zc)]
    for (ya, za), (yb_, zb) in zip(prof, prof[1:] + prof[:1]):
        dy, dz = yb_ - ya, zb - za; n = (0, dz, -dy)
        if _dot(n, (0, ya + yb_ - 2 * (yf + yb) / 2, za + zb - 2 * (zc + CORNICE_H / 2))) < 0: n = (0, -dz, dy)
        grid_quad(m, (-xs, ya, za), (2 * xs, 0, 0), (0, dy, dz), 6, 1, TUFA_HI if dz > 0.06 and abs(dy) < 1e-9 and ya < 0 else TUFA_FACE, n)
    for x, nx in ((-xs, -1), (xs, 1)):
        pts = [(x, y_, z_) for y_, z_ in prof]
        m.add([pts[0], pts[1], pts[4]], TUFA_FACE, (nx, 0, 0)); m.add([pts[1], pts[2], pts[3], pts[4]], TUFA_FACE, (nx, 0, 0))
    n0['slab_and_cornice'] = len(m.faces) - n0['pedestal'] - n0['face']
    return m, n0


# ---- Blender ----
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--blenderio', default='/home/user/x3d-blender-io/source'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'assets', 'khachkar'))
    ap.add_argument('--samples', type=int, default=384); ap.add_argument('--plan')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    if a.plan: draw_plan(a.plan); print('plan ->', a.plan); return
    import bpy, bmesh
    from mathutils import Vector, Quaternion, Matrix
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('x3dio', os.path.join(a.blenderio, '__init__.py'), submodule_search_locations=[a.blenderio])
    mod = importlib.util.module_from_spec(spec); sys.modules['x3dio'] = mod; spec.loader.exec_module(mod); mod.register()
    try: io_head = subprocess.check_output(['git', '-C', a.blenderio, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: io_head = 'unknown'
    bpy.ops.wm.read_factory_settings(use_empty=True); coll = bpy.context.scene.collection

    th = math.radians(KHACHKAR_AZ); x, y = KHACHKAR_R * math.cos(th), KHACHKAR_R * math.sin(th)       # in place: upright on the curve, the face toward the fountain
    z = sag(KHACHKAR_R) - 0.02; nrm = (Vector((x, y, z)) - Vector((0, 0, -VS.R_PLANET))).normalized()
    M = Matrix.LocRotScale(Vector((x, y, z)), Vector((0, 0, 1)).rotation_difference(nrm) @ Quaternion((0, 0, 1), th - math.pi / 2), Vector((1, 1, 1)))

    def make(name, faces, alb):
        bm = bmesh.new(); cache = {}
        for f_ in faces:
            vs = []
            for p in f_:
                k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
                if k not in cache: cache[k] = bm.verts.new(p)
                vs.append(cache[k])
            bm.faces.new(vs)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.transform(M if name == 'Khachkar' else Matrix.Identity(4))
        for p in me.polygons: p.use_smooth = False
        a_ = me.color_attributes.new(name='Alb', type='FLOAT_COLOR', domain='CORNER'); c_ = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
        for poly, c in zip(me.polygons, alb):
            for li in poly.loop_indices: a_.data[li].color = (c[0], c[1], c[2], 0.0); c_.data[li].color = (c[0], c[1], c[2], 1.0)
        me.color_attributes.active_color = c_; me.color_attributes.render_color_index = me.color_attributes.find('Col')
        ob = bpy.data.objects.new(name, me); coll.objects.link(ob); return ob

    m, parts = stone()
    kh = make('Khachkar', m.faces, m.alb)
    gf, ga = [], []; S, N = 16.0, 32                                                           # the receiver: a patch of paving round the stone, on the curve (bounces, takes shadow, not exported)
    for i in range(N):
        for j in range(N):
            q = []
            for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
                px, py = x - S / 2 + S * (i + di) / N, y - S / 2 + S * (j + dj) / N; q.append((px, py, sag(math.hypot(px, py))))
            gf.append(q); ga.append(PAVE)
    gr = make('Receiver', gf, ga)

    sc = bpy.context.scene; sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'; sc.cycles.samples = a.samples; sc.cycles.use_denoising = False; sc.cycles.seed = 11; sc.cycles.sample_clamp_indirect = 4.0
    w = bpy.data.worlds.new('village'); w.use_nodes = True; sc.world = w; nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'; sky.sun_disc = False; sky.sun_elevation = math.radians(SKY_ELEV); sky.sun_rotation = math.radians(KEY_AZ)
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = SKY_STRENGTH; wo = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], wo.inputs[0])
    e, az = math.radians(KEY_ELEV), math.radians(KEY_AZ); toward = Vector((math.cos(e) * math.cos(az), math.cos(e) * math.sin(az), math.sin(e)))
    ld = bpy.data.lights.new('key', 'SUN'); ld.energy = KEY_STRENGTH; ld.color = KEY_COL; ld.angle = math.radians(KEY_ANGLE)
    lo = bpy.data.objects.new('key', ld); coll.objects.link(lo); lo.rotation_euler = (-toward).to_track_quat('-Z', 'Y').to_euler()
    mat = bpy.data.materials.new('albedo'); mat.use_nodes = True; mt = mat.node_tree; bsdf = mt.nodes.get('Principled BSDF')
    vc = mt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Alb'; mt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = 1.0
    obs = [kh, gr]
    for ob in obs:
        me = ob.data; me.materials.append(mat)
        li = me.color_attributes.new(name='Light', type='FLOAT_COLOR', domain='CORNER'); me.color_attributes.active_color = li; me.color_attributes.render_color_index = me.color_attributes.find('Light')
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active = kh
    bk = sc.render.bake; bk.target = 'VERTEX_COLORS'; bk.use_pass_direct = True; bk.use_pass_indirect = True; bk.use_pass_color = False
    bpy.ops.object.bake(type='DIFFUSE')

    lum = lambda ob: sorted(luma(d.color) for d in ob.data.color_attributes['Light'].data)
    g = lum(gr); expo = EXPOSE_TO / g[int(len(g) * EXPOSE_PCT)]
    stats = {}
    for ob in obs:
        l = [v * expo for v in lum(ob)]; stats[ob.name] = dict(light_p05=round(l[int(len(l) * 0.05)], 3), light_p50=round(l[len(l) // 2], 3), light_p95=round(l[int(len(l) * 0.95)], 3))
    me = kh.data; alb = me.color_attributes['Alb']; li = me.color_attributes['Light']; col = me.color_attributes['Col']
    groups = {}                                                                               # one light per point and plane: the corners that meet at a vertex on one flat surface get their mean
    for p in me.polygons:                                                                     # (they differ only by sampling noise), so the exporter can share the vertex among them
        n = tuple(round(x, 3) for x in p.normal)
        for k in p.loop_indices: groups.setdefault((me.loops[k].vertex_index, n), []).append(k)
    for ks in groups.values():
        if len(ks) > 1:
            m_ = [sum(li.data[k].color[i] for k in ks) / len(ks) for i in range(3)]
            for k in ks: li.data[k].color = (m_[0], m_[1], m_[2], 1.0)
    for p in me.polygons:                                                                     # the finish, in the recipe's order: exposure, floor, albedo, sRGB, shoulder
        for k in p.loop_indices:
            L = [max(v * expo if v == v else 0.0, FLOOR[i]) for i, v in enumerate(li.data[k].color[:3])]
            al = lin(alb.data[k].color)
            c = tuple(min(1.0, shoulder(disp(al[i] * L[i]))) for i in range(3))
            col.data[k].color = (c[0], c[1], c[2], 1.0)
    me.color_attributes.active_color = col; me.color_attributes.render_color_index = me.color_attributes.find('Col')
    for nm in ('Alb', 'Light'): me.color_attributes.remove(me.color_attributes[nm])
    me.materials.clear()

    bpy.ops.object.select_all(action='DESELECT'); kh.select_set(True)
    path = os.path.join(out, 'khachkar.x3d')
    bpy.ops.export_scene.x3d(filepath=path, x3d_version='X3D40', use_selection=True, use_mesh_modifiers=False, use_hierarchy=False, meta_creator='Gobbler demiurge', meta_title='Khachkar',
                             meta_description='An Armenian cross-stone in warm tufa on a stepped basalt pedestal, carved in relief, in the plaza of Aurelsbrunn; made in Blender, light baked in Cycles')
    sha = lambda p_: hashlib.sha256(open(p_, 'rb').read()).hexdigest()
    rec = dict(blender=bpy.app.version_string, blenderio='x3d-blender-io ' + io_head, script_sha256=sha(__file__), village_spec_sha256=sha(os.path.join(HERE, 'village_spec.py')),
               bake=dict(engine='Cycles CPU', samples=a.samples, key=dict(azimuth=KEY_AZ, elevation=KEY_ELEV, colour=KEY_COL, strength=KEY_STRENGTH, disc_degrees=KEY_ANGLE),
                         sky=dict(type='multiple scattering, disc off', sun_elevation=SKY_ELEV, strength=SKY_STRENGTH), passes='direct + indirect, albedo-coloured bounce',
                         exposure=round(expo, 4), exposure_rule='%d%% receiver ground corner -> %.2f' % (EXPOSE_PCT * 100, EXPOSE_TO), floor_linear=FLOOR, shoulder_from=0.80, light_stats=stats,
                         receiver='a %g m square of paving round the stone, %d x %d cells, on the curve; baked with the stone, not exported' % (S, N, N)),
               meshes=dict(Khachkar=len(me.polygons)), parts=parts,
               place=dict(radius_m=KHACHKAR_R, azimuth_deg=KHACHKAR_AZ, faces='the fountain'),
               size_m=dict(slab_width=W, slab_thickness=T, slab_height=HS, cornice=CORNICE_H, stone_height=round(HS + CORNICE_H, 3), pedestal=round(Z0, 3), overall=round(Z0 + HS + CORNICE_H, 3)),
               relief_m=dict(field_depth=DEPTH, boss=BOSS, grid=GRID), objects=1, file='khachkar.x3d', bytes=os.path.getsize(path), sha256=sha(path))
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w'), indent=1); print(json.dumps(rec))


if __name__ == '__main__': main()
