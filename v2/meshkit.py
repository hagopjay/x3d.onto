"""Tiny mesh toolkit (pure Python) for the v2 scene: build merged IndexedFaceSet data with explicit normals, UVs and vertex colours.
Conventions: right-handed, y up, faces CCW seen from outside (solid=true).  Everything is in metres.  Textures tile once per `tile` metres."""
import math, random

def norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)

class Mesh:
    """Accumulates faces.  `at(x,y,z,rotY)` pushes a yaw+translate transform (nestable); `scale` is applied before it."""
    def __init__(self, name=""):
        self.name = name; self.p = []; self.n = []; self.uv = []; self.c = []; self.f = []; self.stack = []; self.col = (1.0, 1.0, 1.0)
    # ---- transform stack
    def at(self, x=0.0, y=0.0, z=0.0, rot=0.0, scale=1.0):
        m = self
        class Ctx:
            def __enter__(s): m.stack.append((x, y, z, math.cos(rot), math.sin(rot), scale)); return m
            def __exit__(s, *a): m.stack.pop()
        return Ctx()
    def _tp(self, p):
        for (x, y, z, c, s, k) in reversed(self.stack):
            px, py, pz = p[0] * k, p[1] * k, p[2] * k
            p = (c * px + s * pz + x, py + y, -s * px + c * pz + z)
        return p
    def _tn(self, n):
        for (x, y, z, c, s, k) in reversed(self.stack):
            n = (c * n[0] + s * n[2], n[1], -s * n[0] + c * n[2])
        return n
    # ---- primitives
    def face(self, pts, uvs=None, normal=None, color=None, normals=None):
        """one polygon (CCW from outside).  uvs per vertex; normal flat unless `normals` (per vertex, local frame) given"""
        n0 = normal or norm(cross(sub(pts[1], pts[0]), sub(pts[2], pts[1])))
        base = len(self.p); col = color or self.col
        for i, p in enumerate(pts):
            self.p.append(self._tp(p)); self.n.append(self._tn(normals[i] if normals else n0))
            self.uv.append(uvs[i] if uvs else (0.0, 0.0)); self.c.append(col[i] if isinstance(col[0], tuple) else col)
        self.f.append(list(range(base, base + len(pts))))
    def quad(self, a, b, c, d, uv=((0, 0), (1, 0), (1, 1), (0, 1)), color=None): self.face([a, b, c, d], list(uv), color=color)
    def box(self, cx, cy, cz, sx, sy, sz, tile=3.0, color=None, faces="pnPNzZ", shade=None):
        """axis aligned box centred at (cx,cy,cz).  faces: p=+x n=-x P=+y(top) N=-y z=+z Z=-z"""
        x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2; k = 1.0 / tile
        def F(pts, u, v, col=None): self.face(pts, [(a * k, b * k) for a, b in zip(u, v)], color=color)
        if "z" in faces: F([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], [x0, x1, x1, x0], [y0, y0, y1, y1])
        if "Z" in faces: F([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], [-x1, -x0, -x0, -x1], [y0, y0, y1, y1])
        if "p" in faces: F([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], [-z1, -z0, -z0, -z1], [y0, y0, y1, y1])
        if "n" in faces: F([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], [z0, z1, z1, z0], [y0, y0, y1, y1])
        if "P" in faces: F([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], [x0, x1, x1, x0], [-z1, -z1, -z0, -z0])
        if "N" in faces: F([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], [x0, x1, x1, x0], [z0, z0, z1, z1])
    def lathe(self, prof, n=16, color=None, smooth=True, tile=3.0, cap_top=True, cap_bottom=True, ex=1.0, ez=1.0, vmode="arc"):
        """surface of revolution about +y.  prof: [(radius, y), ...] bottom to top.  ex/ez squash x/z (ellipse).  uv: u around, v = arclength/tile"""
        pts = []; L = 0.0; ls = [0.0]
        for i in range(1, len(prof)): L += math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]); ls.append(L)
        # profile normals (2D outward)
        def pn(i):
            a = prof[max(0, i - 1)]; b = prof[min(len(prof) - 1, i + 1)]; dx, dy = b[0] - a[0], b[1] - a[1]; l = math.hypot(dx, dy) or 1; return (dy / l, -dx / l)
        for j in range(len(prof) - 1):
            for i in range(n):
                a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n
                def P(rr, yy, aa): return (rr * math.sin(aa) * ex, yy, rr * math.cos(aa) * ez)
                def N(k, aa):
                    nr, ny = pn(k); v = (nr * math.sin(aa) / max(ex, 1e-6), ny, nr * math.cos(aa) / max(ez, 1e-6)); return norm(v)
                (r0, y0), (r1, y1) = prof[j], prof[j + 1]
                q = [P(r0, y0, a0), P(r0, y0, a1), P(r1, y1, a1), P(r1, y1, a0)]
                u0, u1 = i / n * 2 * math.pi * max(r0, r1) / tile * ex, (i + 1) / n * 2 * math.pi * max(r0, r1) / tile * ex
                uv = [(u0, ls[j] / tile), (u1, ls[j] / tile), (u1, ls[j + 1] / tile), (u0, ls[j + 1] / tile)]
                if r1 < 1e-9 or r0 < 1e-9:  # degenerate edge (cone tip) -> triangle
                    tri = [0, 1, 2] if r1 < 1e-9 and r0 >= 1e-9 else [0, 1, 3] if r0 < 1e-9 else None
                    if r1 < 1e-9 and r0 >= 1e-9: self.face([q[0], q[1], q[2]], [uv[0], uv[1], uv[2]], color=color, normals=[N(j, a0), N(j, a1), N(j + 1, (a0 + a1) / 2)] if smooth else None)
                    elif r0 < 1e-9 and r1 >= 1e-9: self.face([q[0], q[2], q[3]], [uv[0], uv[2], uv[3]], color=color, normals=[N(j + 1, (a0 + a1) / 2), N(j + 1, a1), N(j + 1, a0)] if smooth else None)
                    continue
                self.face(q, uv, color=color, normals=[N(j, a0), N(j, a1), N(j + 1, a1), N(j + 1, a0)] if smooth else None)
        def cap(rr, yy, up):
            if rr < 1e-9: return
            ring = [(rr * math.sin(2 * math.pi * i / n) * ex, yy, rr * math.cos(2 * math.pi * i / n) * ez) for i in range(n)]
            if not up: ring.reverse()
            self.face(ring, [(p[0] / tile, p[2] / tile) for p in ring], normal=(0, 1 if up else -1, 0), color=color)
        if cap_top: cap(prof[-1][0], prof[-1][1], True)
        if cap_bottom: cap(prof[0][0], prof[0][1], False)
    def cylinder(self, cx, cy, cz, r, h, n=12, tile=3.0, color=None, caps=True, ex=1.0, ez=1.0):
        with self.at(cx, cy - h / 2, cz): self.lathe([(r, 0), (r, h)], n=n, tile=tile, color=color, cap_top=caps, cap_bottom=caps, ex=ex, ez=ez)
    def cone(self, cx, cy, cz, r, h, n=12, tile=3.0, color=None):
        with self.at(cx, cy, cz): self.lathe([(r, 0), (0.0, h)], n=n, tile=tile, color=color, cap_top=False, cap_bottom=True, smooth=True)
    def icosphere(self, c, r, sub=1, color=None, jitter=0.0, rng=None, squash=(1, 1, 1), flat=True):
        """low poly sphere; `jitter` randomly displaces vertices (organic blobs, foliage)"""
        t = (1 + 5 ** 0.5) / 2
        V = [norm(v) for v in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
        T = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        cache = {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache: V.append(norm(mul(add(V[a], V[b]), 0.5))); cache[k] = len(V) - 1
            return cache[k]
        for _ in range(sub):
            T2 = []
            for a, b, cc in T: ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a); T2 += [(a, ab, ca), (b, bc, ab), (cc, ca, bc), (ab, bc, ca)]
            T = T2
        rng = rng or random.Random(1)
        W = [mul(v, 1.0 + (rng.uniform(-jitter, jitter) if jitter else 0.0)) for v in V]
        for a, b, cc in T:
            pts = [(c[0] + W[i][0] * r * squash[0], c[1] + W[i][1] * r * squash[1], c[2] + W[i][2] * r * squash[2]) for i in (a, b, cc)]
            col = color(rng) if callable(color) else color
            self.face(pts, [(0, 0), (1, 0), (0.5, 1)], color=col, normals=None if flat else [V[a], V[b], V[cc]])
    def tube(self, p0, p1, r0, r1, n=10, color=None, caps=(True, True), ex=1.0, ez=1.0, tile=3.0):
        """tapered capsule-ish limb between two points (any direction): lathe along local y, rotated to the axis.  Note: yaw+pitch only (no roll)"""
        d = sub(p1, p0); L = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2);
        yaw = math.atan2(d[0], d[2]); pitch = math.acos(max(-1, min(1, d[1] / L)))
        # build in local frame then rotate: local +y -> d  (rotate about x by pitch from +y toward +z, then yaw about y)
        prof = [(r0 * 0.55, 0.0), (r0 * 0.9, L * 0.02), (r0, L * 0.06), (r0 + (r1 - r0) * 0.5, L * 0.5), (r1, L * 0.94), (r1 * 0.9, L * 0.985), (r1 * 0.5, L)]
        tmp = Mesh(); tmp.lathe(prof, n=n, color=color, smooth=True, tile=tile, cap_top=True, cap_bottom=True, ex=ex, ez=ez)
        cp, sp, cy_, sy_ = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
        def R(v):
            x, y, z = v; y2, z2 = y * cp - z * sp, y * sp + z * cp   # pitch about x (+y toward +z)
            return (x * cy_ + z2 * sy_, y2, -x * sy_ + z2 * cy_)       # yaw about y
        for fidx in tmp.f:
            self.face([add(R(tmp.p[i]), p0) for i in fidx], [tmp.uv[i] for i in fidx], normals=[R(tmp.n[i]) for i in fidx], color=[tmp.c[i] for i in fidx] if isinstance(tmp.c[fidx[0]], tuple) else None)
    def merge(self, other):
        base = len(self.p); self.p += other.p; self.n += other.n; self.uv += other.uv; self.c += other.c; self.f += [[i + base for i in f] for f in other.f]
    # ---- export (flat lists, ready for x3d_mcp fields)
    def export(self, nd=3, uv=True, colors="auto"):
        """lists for x3d_mcp: welded positions (coordIndex) with separate texCoordIndex/colorIndex, so X_ITE can derive smooth normals from creaseAngle"""
        pos = {}; pts = []; wmap = []
        for p in self.p:
            k = (round(p[0], nd), round(p[1], nd), round(p[2], nd))
            if k not in pos: pos[k] = len(pts); pts.append(k)
            wmap.append(pos[k])
        cidx = []; tidx = []
        for f in self.f:
            if len(f) > 2: cidx += [wmap[i] for i in f] + [-1]; tidx += f + [-1]
        out = dict(point=[list(p) for p in pts], coordIndex=cidx, faces=len(self.f), verts=len(pts), corners=len(self.p))
        if uv: out["uv"] = [[round(t[0], 3), round(t[1], 3)] for t in self.uv]; out["texCoordIndex"] = tidx
        white = all(abs(c[0] - 1) + abs(c[1] - 1) + abs(c[2] - 1) < 0.01 for c in self.c) if colors == "auto" else not colors
        if not white: out["color"] = [[round(min(1.0, max(0.0, x)), 2) for x in c] for c in self.c]; out["colorIndex"] = tidx
        return out

def fbm_sin(x, z, seed=0, octaves=4):
    """smooth deterministic pseudo-noise shared with engine.js (same formula): sum of products of sines"""
    s = 0.0; a = 1.0; f = 1.0; tot = 0.0
    for o in range(octaves):
        ph = seed * 1.7 + o * 2.3
        s += a * (math.sin(f * 0.0123 * x + ph) * math.sin(f * 0.0137 * z + ph * 1.3) + 0.6 * math.sin(f * 0.0091 * (x + z) + ph * 0.7) * math.cos(f * 0.0111 * (x - z) + ph * 1.9))
        tot += a * 1.6; a *= 0.5; f *= 2.07
    return s / tot  # about -1..1
