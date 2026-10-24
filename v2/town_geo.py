"""Geometry of the village 'Aurelsbrunn' as merged meshes, one per material.  Pure Python; consumed by make_v2.py (x3d_mcp) and nothing else."""
import math, random
from meshkit import Mesh, fbm_sin, norm, sub, cross, add, mul
import town_layout as L

R_EARTH = 6371000.0
def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def H(x, z):
    """terrain height (m) above the village tangent plane, incl. Earth-curvature drop. Mirrored 1:1 in engine.js"""
    r2 = x * x + z * z; r = math.sqrt(r2)
    h = smooth(280, 1100, r) * (24 * fbm_sin(x, z, 1) + 9 * fbm_sin(x * 2.3, z * 2.3, 2))
    m = smooth(2500, 9500, r); ang = math.atan2(z, x)
    ridge = 0.5 + 0.5 * fbm_sin(x * 0.12, z * 0.12, 7); bias = 0.55 + 0.45 * math.cos(ang - 1.1)
    h += m * (260 + 900 * ridge) * (0.3 + 0.7 * bias)
    return h - r2 / (2 * R_EARTH)

WALL = {"ochre": (0.98, 0.82, 0.55), "cream": (1.0, 0.97, 0.88), "terracotta": (0.95, 0.66, 0.50), "blue": (0.66, 0.77, 0.88), "stone": (0.90, 0.88, 0.84), "wood": (0.78, 0.62, 0.46)}
SHUT = {"green": (0.20, 0.40, 0.26), "blue": (0.22, 0.36, 0.58), "brown": (0.42, 0.26, 0.15), "cream": (0.92, 0.88, 0.74)}
KEYS = ["plaster", "paint", "roof_tile", "roof_slate", "wood", "stone", "metal", "glass", "glass_lit", "cloth", "lampglass", "forge", "goods"]
TILE = dict(plaster=4.0, paint=4.0, roof_tile=4.0, roof_slate=3.0, wood=2.0, stone=3.0, cobble=3.6, dirt=6.0, grass=5.0)

class AtAll:
    def __init__(s, M, x=0.0, y=0.0, z=0.0, rot=0.0, scale=1.0, keys=None): s.M = M; s.a = (x, y, z, rot, scale); s.keys = keys or list(M.keys())
    def __enter__(s): s.c = [M_.at(*s.a) for M_ in (s.M[k] for k in s.keys)]; [c.__enter__() for c in s.c]; return s
    def __exit__(s, *e): [c.__exit__(*e) for c in reversed(s.c)]

def slab(m, P, t, tile, color=None, uvs=None):
    """closed slab: top polygon P (CCW from outside, 4 pts) extruded by -t along its normal"""
    n = norm(cross(sub(P[1], P[0]), sub(P[2], P[1]))); Q = [sub(p, mul(n, t)) for p in P]
    m.face(P, uvs, color=color)
    m.face([Q[0], Q[3], Q[2], Q[1]], uvs and [uvs[0], uvs[3], uvs[2], uvs[1]], color=color)
    for i in range(4):
        j = (i + 1) % 4; m.face([P[i], Q[i], Q[j], P[j]], [(0, 0), (0, t / tile), (1, t / tile), (1, 0)], color=color)

def gable_roof(M, w, d, hh, key, pitch=36.0, ov=0.55, ovx=0.35, t=0.13, wall_key="plaster", wall_col=(1, 1, 1), col=(1, 1, 1), ridge_col=None):
    tn = math.tan(math.radians(pitch)); X = w / 2 + ovx; Z = d / 2 + ov; ye = hh - ov * tn; R = hh + (d / 2) * tn; ls = math.hypot(Z, R - ye); k = 1.0 / TILE[key]; m = M[key]
    for sgn in (1, -1):
        if sgn == 1: P = [(-X, ye, Z), (X, ye, Z), (X, R, 0), (-X, R, 0)]
        else: P = [(X, ye, -Z), (-X, ye, -Z), (-X, R, 0), (X, R, 0)]
        slab(m, P, t, TILE[key], color=col, uvs=[(0, 0), (2 * X * k, 0), (2 * X * k, ls * k), (0, ls * k)])
    m.box(0, R + 0.03, 0, 2 * X + 0.04, 0.14, 0.36, tile=TILE[key], color=ridge_col or tuple(c * 0.8 for c in col))
    pl = M[wall_key]; Rw = R
    for sx in (1, -1):
        x = sx * w / 2
        P = [(x, hh, Z - ov), (x, hh, -(Z - ov)), (x, Rw, 0)] if sx == 1 else [(x, hh, -(Z - ov)), (x, hh, Z - ov), (x, Rw, 0)]
        pl.face(P, [(P[0][2] / TILE[wall_key], P[0][1] / TILE[wall_key]), (P[1][2] / TILE[wall_key], P[1][1] / TILE[wall_key]), (P[2][2] / TILE[wall_key], P[2][1] / TILE[wall_key])], color=wall_col)
    return R

def window(M, px, py, pz, rot, ww, wh, shutter, lit, frame=(0.95, 0.93, 0.86), arch=False, shutters=True, detail=None):
    detail = shutters if detail is None else detail
    with AtAll(M, px, py, pz, rot, keys=["glass", "glass_lit", "paint"]):
        g = M["glass_lit" if lit else "glass"]
        if arch: g.face([(-ww / 2, -wh / 2, 0.03), (ww / 2, -wh / 2, 0.03), (ww / 2, wh / 2 - ww * 0.5, 0.03), (ww * 0.38, wh / 2 - ww * 0.12, 0.03), (0, wh / 2, 0.03), (-ww * 0.38, wh / 2 - ww * 0.12, 0.03), (-ww / 2, wh / 2 - ww * 0.5, 0.03)], [(0, 0)] * 7, color=(1, 1, 1))
        else: g.quad((-ww / 2, -wh / 2, 0.03), (ww / 2, -wh / 2, 0.03), (ww / 2, wh / 2, 0.03), (-ww / 2, wh / 2, 0.03), uv=[(0, 0)] * 4)
        p = M["paint"]; f = "pnPNz"
        parts = [(0, wh / 2 + 0.04, 0.045, ww + 0.16, 0.08, 0.09, "pnPz"), (0, -wh / 2 - 0.04, 0.045, ww + 0.16, 0.08, 0.09, "pnNz"), (-ww / 2 - 0.04, 0, 0.045, 0.08, wh, 0.09, "pz"), (ww / 2 + 0.04, 0, 0.045, 0.08, wh, 0.09, "nz")]
        if detail: parts += [(0, 0.05, 0.045, 0.035, wh, 0.06, "pnz"), (0, wh * 0.18, 0.045, ww, 0.035, 0.06, "PNz")]
        for (cx, cy, cz, sx, sy, sz, ff) in parts: p.box(cx, cy, cz, sx, sy, sz, tile=2.0, color=frame, faces=ff)
        if detail: p.box(0, -wh / 2 - 0.10, 0.10, ww + 0.30, 0.06, 0.2, tile=2.0, color=frame, faces="pnPNz")
        if shutters:
            for sx_ in (-1, 1): p.box(sx_ * (ww / 2 + 0.04 + 0.27), 0, 0.05, 0.5, wh + 0.12, 0.05, tile=2.0, color=shutter, faces=f)

def door(M, px, pz, rot, col, wd=1.1, hd=2.15):
    with AtAll(M, px, 0, pz, rot, keys=["paint", "stone", "metal", "wood"]):
        M["paint"].box(0, hd / 2, 0.04, wd, hd, 0.08, tile=2.0, color=col, faces="pnPz")
        M["paint"].box(0, hd + 0.08, 0.06, wd + 0.3, 0.16, 0.12, tile=2.0, color=(0.92, 0.9, 0.84), faces="pnPNz")
        M["paint"].box(-wd / 2 - 0.09, hd / 2, 0.06, 0.18, hd, 0.12, tile=2.0, color=(0.92, 0.9, 0.84), faces="pnPz")
        M["paint"].box(wd / 2 + 0.09, hd / 2, 0.06, 0.18, hd, 0.12, tile=2.0, color=(0.92, 0.9, 0.84), faces="pnPz")
        M["stone"].box(0, 0.09, 0.42, wd + 0.9, 0.18, 0.84, tile=3.0, color=(0.9, 0.88, 0.85), faces="pnPz")
        M["metal"].box(wd * 0.34, 1.0, 0.1, 0.06, 0.06, 0.06, color=(0.2, 0.2, 0.22), faces="pnPNz")
        for yy in (0.4, 1.7): M["metal"].box(0, yy, 0.095, wd, 0.05, 0.02, color=(0.12, 0.12, 0.14), faces="Pz")

def chimney(M, x, z, ytop, w=0.9):
    M["stone"].box(x, ytop - 1.1, z, w, 2.4, w, tile=2.0, color=(0.82, 0.78, 0.72))
    M["stone"].box(x, ytop + 0.08, z, w + 0.2, 0.14, w + 0.2, tile=2.0, color=(0.7, 0.68, 0.65))
    M["metal"].box(x, ytop + 0.16, z, w - 0.2, 0.02, w - 0.2, color=(0.05, 0.05, 0.05), faces="P")

def house(M, h, rng):
    hid, name, x, z, w, d, hh, rot, tint, roof, role, shut = h
    wc = WALL[tint]; sc = SHUT[shut]; rk = "roof_slate" if roof == "slate" else "roof_tile"
    rc = (1, 1, 1) if rk == "roof_tile" else (1, 1, 1); rc = (rng.uniform(0.9, 1.05),) * 3 if rk == "roof_tile" else (rng.uniform(0.9, 1.1),) * 3
    two = hh >= 4.35
    with AtAll(M, x, 0, z, rot):
        M["stone"].box(0, 0.25, 0, w + 0.4, 0.5, d + 0.4, tile=3.0, color=(0.85, 0.83, 0.8), faces="pnPzZ")
        M["plaster"].box(0, (0.5 + hh) / 2, 0, w, hh - 0.5, d, tile=TILE["plaster"], color=wc, faces="pnzZ")
        R = gable_roof(M, w, d, hh, rk, wall_col=wc, col=rc)
        cols = 2 * round((w / 2.8 - 1) / 2) + 1; cols = max(3, cols); step = (w - 2.0) / (cols - 1)
        slots = [(i - (cols - 1) / 2) * step for i in range(cols)]
        rows = [1.7, hh - 1.15] if two else [1.7]
        for xs in slots:
            for ry in rows:
                if abs(xs) < 1.25 and ry < 2.5: continue
                window(M, xs, ry, d / 2, 0.0, 0.85, 1.2, sc, rng.random() < 0.55)
        door(M, 0.0, d / 2, 0.0, sc)
        for xs in slots:
            for ry in rows: window(M, xs, ry, -d / 2, math.pi, 0.85, 1.2, sc, rng.random() < 0.4, shutters=False)
        ns = max(1, round(d / 3.6))
        for i in range(ns):
            zz = (i - (ns - 1) / 2) * min(3.4, (d - 2.4) / max(1, ns - 1) if ns > 1 else 0)
            for ry in rows:
                window(M, w / 2, ry, zz, math.pi / 2, 0.8, 1.15, sc, rng.random() < 0.4, shutters=False); window(M, -w / 2, ry, zz, -math.pi / 2, 0.8, 1.15, sc, rng.random() < 0.4, shutters=False)
        # attic window in the gable
        for sx in (1, -1): window(M, sx * w / 2, hh + 0.9, 0, sx * math.pi / 2, 0.55, 0.65, sc, rng.random() < 0.5, shutters=False)
        chimney(M, w * 0.25, -d * 0.12, R + 0.35)
        if hid == "H01":  # bakery: awning over the shop window and a hanging pretzel sign
            M["cloth"].face([(-3.0, 2.7, d / 2 + 0.05), (3.0, 2.7, d / 2 + 0.05), (3.0, 3.0, d / 2 + 1.1), (-3.0, 3.0, d / 2 + 1.1)][::1], [(0, 0)] * 4, color=(0.75, 0.22, 0.16))
            M["cloth"].face([(-3.0, 3.0, d / 2 + 1.1), (3.0, 3.0, d / 2 + 1.1), (3.0, 2.7, d / 2 + 0.05), (-3.0, 2.7, d / 2 + 0.05)][::1], [(0, 0)] * 4, color=(0.55, 0.15, 0.12))
        if hid in ("H05",): M["paint"].box(0, hh + 1.9, 0, 0.8, 1.0, 0.8, color=(0.95, 0.93, 0.85)); M["metal"].box(0, hh + 2.6, 0, 0.5, 0.35, 0.5, color=(0.8, 0.65, 0.2))  # school bell turret (toy)

def inn(M, h, rng):
    hid, name, x, z, w, d, hh, rot, tint, roof, role, shut = h; wc = WALL[tint]; sc = SHUT[shut]; rows = [1.7, 4.0]
    with AtAll(M, x, 0, z, rot):
        M["stone"].box(0, 0.3, 0, w + 0.5, 0.6, d + 0.5, tile=3.0, color=(0.82, 0.8, 0.77), faces="pnPzZ")
        M["plaster"].box(0, (0.6 + hh) / 2, 0, w, hh - 0.6, d, tile=4.0, color=wc, faces="pnzZ")
        # half-timber: dark beams on the upper storey
        for xx in [i * w / 5 for i in range(-2, 3)]: M["wood"].box(xx, 4.0, d / 2 + 0.03, 0.22, 2.7, 0.07, tile=2.0, color=(0.55, 0.5, 0.45), faces="pnPNz")
        M["wood"].box(0, 2.62, d / 2 + 0.04, w, 0.24, 0.08, tile=2.0, color=(0.55, 0.5, 0.45), faces="pnPNz"); M["wood"].box(0, hh - 0.14, d / 2 + 0.04, w, 0.24, 0.08, tile=2.0, color=(0.55, 0.5, 0.45), faces="pnPNz")
        R = gable_roof(M, w, d, hh, "roof_tile", wall_col=wc, pitch=34, col=(0.95, 0.95, 0.95))
        slots = [(-5.6), -2.8, 2.8, 5.6]
        for xs in slots:
            for ry in rows: window(M, xs, ry, d / 2, 0.0, 0.9, 1.25, sc, rng.random() < 0.85)
        window(M, -0.0, 4.0, d / 2, 0.0, 1.0, 1.3, sc, True)
        for xs in (-5.6, -2.8, 0, 2.8, 5.6):
            for ry in rows: window(M, xs, ry, -d / 2, math.pi, 0.9, 1.25, sc, rng.random() < 0.7, shutters=False)
        for zz in (-2.5, 2.5):
            for ry in rows: window(M, w / 2, ry, zz, math.pi / 2, 0.85, 1.2, sc, rng.random() < 0.7, shutters=False); window(M, -w / 2, ry, zz, -math.pi / 2, 0.85, 1.2, sc, rng.random() < 0.7, shutters=False)
        door(M, 0.0, d / 2, 0.0, (0.35, 0.18, 0.1), wd=1.5, hd=2.3)
        chimney(M, w * 0.3, 0.0, R + 0.4, 1.0); chimney(M, -w * 0.3, 0.0, R + 0.4, 1.0)
        # hanging sign
        M["metal"].box(2.6, 3.45, d / 2 + 0.7, 0.05, 0.05, 1.4, color=(0.1, 0.1, 0.12)); M["wood"].box(2.6, 3.0, d / 2 + 1.2, 0.07, 0.8, 1.0, tile=2.0, color=(0.75, 0.6, 0.4)); M["paint"].box(2.6, 3.0, d / 2 + 1.2, 0.09, 0.5, 0.65, color=(0.8, 0.2, 0.15), faces="pnz"); M["goods"].box(2.6, 3.0, d / 2 + 1.2, 0.1, 0.18, 0.18, color=(0.95, 0.85, 0.35), faces="pnz")
        # tables and benches out front
        for tx in (-4.5, 4.2):
            M["wood"].box(tx, 0.78, d / 2 + 2.6, 1.5, 0.07, 0.8, tile=2.0, color=(0.8, 0.7, 0.6)); [M["wood"].box(tx + sx * 0.6, 0.38, d / 2 + 2.6 + sz * 0.3, 0.07, 0.76, 0.07, tile=2.0, color=(0.7, 0.6, 0.5)) for sx in (-1, 1) for sz in (-1, 1)]
            for sz in (-1, 1): M["wood"].box(tx, 0.45, d / 2 + 2.6 + sz * 0.7, 1.5, 0.06, 0.28, tile=2.0, color=(0.75, 0.65, 0.55)); [M["wood"].box(tx + sx * 0.6, 0.22, d / 2 + 2.6 + sz * 0.7, 0.06, 0.44, 0.06, tile=2.0, color=(0.7, 0.6, 0.5)) for sx in (-1, 1)]
            M["goods"].cylinder(tx - 0.3, 0.88, d / 2 + 2.6, 0.06, 0.12, n=8, color=(0.9, 0.78, 0.4)); M["goods"].cylinder(tx + 0.3, 0.88, d / 2 + 2.7, 0.06, 0.12, n=8, color=(0.9, 0.78, 0.4))

def church(M, h, rng):
    hid, name, x, z, w, d, hh, rot, tint, roof, role, shut = h; sc = (0.4, 0.25, 0.15); stone = (0.95, 0.93, 0.9)
    with AtAll(M, x, 0, z, rot):
        M["stone"].box(0, 0.35, 0, w + 0.6, 0.7, d + 0.6, tile=3.0, color=(0.8, 0.78, 0.75), faces="pnPzZ")
        M["stone"].box(0, (0.7 + hh) / 2, 0, w, hh - 0.7, d, tile=3.0, color=stone, faces="pnzZ")
        with AtAll(M, 0, 0, 0, -math.pi / 2, keys=["roof_slate", "plaster", "stone"]):  # build roof with ridge along z
            R = gable_roof({k: M[k] for k in ("roof_slate", "plaster", "stone")}, d, w, hh, "roof_slate", pitch=44, ov=0.5, ovx=0.5, wall_key="stone", wall_col=stone, col=(0.95, 0.97, 1.0))
        for sx in (-1, 1):
            for i in range(4):
                zz = -d / 2 + 3.2 + i * 4.3
                window(M, sx * w / 2, 3.6, zz, sx * math.pi / 2, 1.1, 3.2, (0.9, 0.9, 0.9), True, frame=(0.85, 0.83, 0.8), arch=True, shutters=False)
                M["stone"].box(sx * (w / 2 + 0.35), 2.4, zz + 1.75, 0.7, 4.8, 0.6, tile=3.0, color=(0.9, 0.88, 0.85)) if i < 3 else None
        # tower at the front (+z end)
        tw = 5.4; th = 15.5; tz = d / 2 + tw / 2 - 0.3
        M["stone"].box(0, th / 2, tz, tw, th, tw, tile=3.0, color=stone, faces="pnzZ")
        for i in range(4): M["stone"].box(0, 4.0 + i * 3.4, tz, tw + 0.25, 0.22, tw + 0.25, tile=3.0, color=(0.8, 0.78, 0.75))
        for (fx, fz, fr) in ((0, tz + tw / 2, 0.0), (0, tz - tw / 2, math.pi), (tw / 2, tz, math.pi / 2), (-tw / 2, tz, -math.pi / 2)):
            window(M, fx, th - 3.1, fz, fr, 1.0, 2.2, (0.9, 0.9, 0.9), False, frame=(0.8, 0.78, 0.75), arch=True, shutters=False)
            with AtAll(M, fx, 0, fz, fr, keys=["goods", "paint", "metal"]):
                M["goods"].cylinder(0, th - 6.0, 0.06, 1.0, 0.1, n=24, color=(0.97, 0.95, 0.88), caps=True, ex=1.0, ez=0.02)
                M["metal"].box(0.0, th - 6.0 + 0.3, 0.12, 0.05, 0.6, 0.02, color=(0.05, 0.05, 0.06), faces="z"); M["metal"].box(0.2, th - 6.0, 0.12, 0.4, 0.05, 0.02, color=(0.05, 0.05, 0.06), faces="z")
        M["roof_slate"].face([(-tw / 2 - 0.3, th, tz + tw / 2 + 0.3), (tw / 2 + 0.3, th, tz + tw / 2 + 0.3), (0, th + 7.5, tz)], [(0, 0), (2, 0), (1, 2.5)], color=(0.9, 0.95, 1))
        M["roof_slate"].face([(tw / 2 + 0.3, th, tz - tw / 2 - 0.3), (-tw / 2 - 0.3, th, tz - tw / 2 - 0.3), (0, th + 7.5, tz)], [(0, 0), (2, 0), (1, 2.5)], color=(0.9, 0.95, 1))
        M["roof_slate"].face([(tw / 2 + 0.3, th, tz + tw / 2 + 0.3), (tw / 2 + 0.3, th, tz - tw / 2 - 0.3), (0, th + 7.5, tz)], [(0, 0), (2, 0), (1, 2.5)], color=(0.9, 0.95, 1))
        M["roof_slate"].face([(-tw / 2 - 0.3, th, tz - tw / 2 - 0.3), (-tw / 2 - 0.3, th, tz + tw / 2 + 0.3), (0, th + 7.5, tz)], [(0, 0), (2, 0), (1, 2.5)], color=(0.9, 0.95, 1))
        M["metal"].cylinder(0, th + 8.4, tz, 0.07, 1.8, n=6, color=(0.75, 0.6, 0.2)); M["metal"].box(0, th + 8.5, tz, 0.8, 0.07, 0.07, color=(0.75, 0.6, 0.2)); M["metal"].box(0, th + 8.9, tz, 0.07, 0.07, 0.07, color=(0.75, 0.6, 0.2))
        # west door of the tower
        M["wood"].box(0, 1.6, tz + tw / 2 + 0.05, 2.0, 3.2, 0.12, tile=2.0, color=(0.55, 0.4, 0.3), faces="pnPz"); M["stone"].box(0, 0.15, tz + tw / 2 + 0.8, 3.4, 0.3, 1.6, tile=3.0, color=(0.82, 0.8, 0.77), faces="pnPz")
        M["metal"].box(0.6, 1.5, tz + tw / 2 + 0.13, 0.08, 0.5, 0.04, color=(0.1, 0.1, 0.1))

def smithy(M, h, rng):
    hid, name, x, z, w, d, hh, rot, tint, roof, role, shut = h
    with AtAll(M, x, 0, z, rot):
        M["stone"].box(0, 0.15, 0, w + 0.3, 0.3, d + 0.3, tile=3.0, color=(0.55, 0.52, 0.5), faces="pPnpzZ".replace("n", "n"))
        M["wood"].box(0, hh / 2, -d / 2 + 0.15, w, hh, 0.3, tile=2.0, color=(0.7, 0.62, 0.55))
        for sx in (-1, 1): M["wood"].box(sx * (w / 2 - 0.15), hh / 2, 0, 0.3, hh, d, tile=2.0, color=(0.7, 0.62, 0.55))
        for sx in (-1, 1): M["wood"].box(sx * (w / 2 - 0.2), hh / 2, d / 2 - 0.2, 0.36, hh, 0.36, tile=2.0, color=(0.55, 0.45, 0.38))
        M["wood"].box(0, hh - 0.2, d / 2 - 0.2, w, 0.4, 0.36, tile=2.0, color=(0.55, 0.45, 0.38))
        R = gable_roof(M, w, d, hh, "roof_tile", pitch=30, col=(0.62, 0.55, 0.52), wall_col=(0.6, 0.5, 0.42), wall_key="wood")
        # forge, chimney, anvil are in world space of the building
        M["stone"].box(-w / 2 + 1.3, 0.55, -d / 2 + 1.1, 1.8, 1.1, 1.4, tile=3.0, color=(0.55, 0.5, 0.48))
        M["stone"].box(-w / 2 + 1.3, hh + 1.2, -d / 2 + 0.9, 1.0, 5.0, 1.0, tile=3.0, color=(0.5, 0.46, 0.44)); M["stone"].box(-w / 2 + 1.3, hh + 3.8, -d / 2 + 0.9, 1.25, 0.2, 1.25, tile=3.0, color=(0.45, 0.42, 0.4))
        M["forge"].quad((-w / 2 + 0.9, 0.9, -d / 2 + 1.82), (-w / 2 + 1.7, 0.9, -d / 2 + 1.82), (-w / 2 + 1.7, 1.12, -d / 2 + 1.82), (-w / 2 + 0.9, 1.12, -d / 2 + 1.82))
        M["forge"].box(-w / 2 + 1.3, 1.1, -d / 2 + 1.1, 1.2, 0.04, 0.9, color=(1, 0.5, 0.15), faces="P")
        M["wood"].box(-w / 2 + 2.9, 0.4, -d / 2 + 0.7, 1.6, 0.8, 0.5, tile=2.0, color=(0.6, 0.5, 0.4)); M["metal"].box(w / 2 - 1.6, 0.4, -d / 2 + 1.2, 1.2, 0.3, 0.6, color=(0.18, 0.18, 0.2))  # trough / tool bench
    ax, az = L.SMITH_ANVIL
    M["wood"].cylinder(ax, 0.32, az, 0.3, 0.64, n=10, tile=1.0, color=(0.55, 0.42, 0.32)); M["metal"].box(ax, 0.72, az, 0.2, 0.16, 0.5, color=(0.22, 0.22, 0.25)); M["metal"].box(ax, 0.84, az, 0.4, 0.1, 0.14, color=(0.3, 0.3, 0.33)); M["metal"].box(ax, 0.9, az - 0.3, 0.06, 0.06, 0.28, color=(0.25, 0.25, 0.28))

def stall(M, s, rng, kind):
    sid, name, x, z, rot = s
    with AtAll(M, x, 0, z, rot):
        for sx in (-1, 1):
            for sz in (-1, 1): M["wood"].box(sx * 1.25, 1.2, sz * 0.8, 0.09, 2.4 if sz > 0 else 2.7, 0.09, tile=2.0, color=(0.7, 0.55, 0.42))
        # canopy: striped cloth, slightly pitched back
        cols = [(0.85, 0.2, 0.15), (0.97, 0.94, 0.88)] if kind == 0 else [(0.18, 0.45, 0.25), (0.97, 0.94, 0.88)] if kind == 1 else [(0.25, 0.3, 0.6), (0.96, 0.8, 0.3)]
        n = 6
        for i in range(n):
            x0 = -1.5 + 3.0 * i / n; x1 = -1.5 + 3.0 * (i + 1) / n
            M["cloth"].face([(x0, 2.35, 1.05), (x1, 2.35, 1.05), (x1, 2.72, -1.05), (x0, 2.72, -1.05)], [(0, 0)] * 4, color=cols[i % 2]); M["cloth"].face([(x0, 2.7, -1.05), (x1, 2.7, -1.05), (x1, 2.33, 1.05), (x0, 2.33, 1.05)], [(0, 0)] * 4, color=tuple(c * 0.7 for c in cols[i % 2]))
            M["cloth"].face([(x0, 2.35, 1.05), (x0, 2.2, 1.05), (x1, 2.2, 1.05), (x1, 2.35, 1.05)], [(0, 0)] * 4, color=cols[i % 2])
        M["wood"].box(0, 0.88, 0.75, 2.7, 0.08, 0.7, tile=2.0, color=(0.82, 0.7, 0.58)); M["wood"].box(0, 0.44, 0.75, 2.6, 0.88, 0.6, tile=2.0, color=(0.6, 0.48, 0.38), faces="pnzZ"); M["wood"].box(0, 1.0, -0.78, 2.6, 0.06, 0.4, tile=2.0, color=(0.75, 0.62, 0.5))
        if kind == 0:
            for i in range(9): M["goods"].icosphere((-1.1 + 0.28 * (i % 5) + 0.1 * (i // 5), 1.0 + 0.05, 0.8 + 0.12 * (i // 5)), 0.11, 1, color=(0.78, 0.5, 0.22), squash=(1.4, 0.8, 1.0), rng=rng, jitter=0.05)
        elif kind == 1:
            pal = [(0.8, 0.15, 0.1), (0.3, 0.6, 0.2), (0.9, 0.65, 0.1), (0.55, 0.3, 0.55), (0.9, 0.4, 0.1)]
            for i in range(14): M["goods"].icosphere((-1.15 + 0.17 * i % 2.5 + 0.0, 0.98 + 0.08 + 0.02 * (i % 3), 0.9 + 0.1 * (i // 7) - 0.15), 0.1, 1, color=pal[i % 5], rng=rng, jitter=0.06)
            for cx in (-0.9, 0.0, 0.9): M["wood"].box(cx, 0.99, -0.78, 0.7, 0.2, 0.34, tile=2.0, color=(0.7, 0.55, 0.4)); [M["goods"].icosphere((cx - 0.2 + 0.2 * k, 1.12, -0.78), 0.1, 1, color=pal[(k + int(cx * 2)) % 5], rng=rng, jitter=0.05) for k in range(3)]
        else:
            pal = [(0.7, 0.2, 0.3), (0.25, 0.4, 0.7), (0.9, 0.8, 0.3), (0.2, 0.55, 0.4), (0.95, 0.95, 0.9)]
            for i in range(5): M["goods"].box(-1.0 + i * 0.5, 0.97 + 0.12, 0.8, 0.42, 0.16, 0.5, tile=1.0, color=pal[i])
            for i in range(4): M["goods"].box(-0.75 + i * 0.5, 0.97 + 0.28, 0.8, 0.4, 0.14, 0.45, tile=1.0, color=pal[(i + 2) % 5])

def lamp(M, x, z, rng):
    M["metal"].cylinder(x, 1.7, z, 0.055, 3.4, n=8, color=(0.1, 0.1, 0.12)); M["metal"].cylinder(x, 0.12, z, 0.14, 0.24, n=8, color=(0.1, 0.1, 0.12))
    M["metal"].box(x, 3.52, z, 0.34, 0.06, 0.34, color=(0.1, 0.1, 0.12)); M["metal"].cone(x, 3.9, z, 0.26, 0.2, n=4, color=(0.1, 0.1, 0.12)); M["lampglass"].box(x, 3.72, z, 0.22, 0.3, 0.22, tile=1.0, color=(1, 1, 1))
    for sx, sz in ((-1, -1), (1, -1), (-1, 1), (1, 1)): M["metal"].box(x + sx * 0.12, 3.72, z + sz * 0.12, 0.025, 0.32, 0.025, color=(0.1, 0.1, 0.12))

def bench(M, x, z, rot):
    with AtAll(M, x, 0, z, rot, keys=["wood"]):
        m = M["wood"]; m.box(0, 0.46, 0, 1.6, 0.06, 0.4, tile=2.0, color=(0.7, 0.55, 0.42)); m.box(0, 0.78, -0.2, 1.6, 0.36, 0.05, tile=2.0, color=(0.65, 0.5, 0.38))
        for sx in (-1, 1): m.box(sx * 0.7, 0.23, 0, 0.08, 0.46, 0.34, tile=2.0, color=(0.55, 0.42, 0.32))

def barrel(M, x, z, rng):
    M["wood"].lathe([(0.0, 0), (0.28, 0.0), (0.34, 0.25), (0.37, 0.45), (0.34, 0.65), (0.28, 0.9), (0.0, 0.9)], n=12) if False else None
    with AtAll(M, x, 0, z, 0.0, keys=["wood", "metal"]):
        M["wood"].lathe([(0.27, 0.0), (0.33, 0.22), (0.35, 0.45), (0.33, 0.7), (0.27, 0.9)], n=12, tile=1.2, color=(0.72, 0.58, 0.45), cap_top=True, cap_bottom=False)
        for yy, rr in ((0.15, 0.31), (0.75, 0.31)): M["metal"].cylinder(0, yy, 0, rr + 0.012, 0.04, n=12, color=(0.15, 0.15, 0.17), caps=False)
def crate(M, x, z, rot, rng):
    with AtAll(M, x, 0, z, rot, keys=["wood"]): M["wood"].box(0, 0.25, 0, 0.7, 0.5, 0.5, tile=1.0, color=(0.75, 0.62, 0.48))

def fountain(M):
    fx, fz, R = L.FOUNTAIN
    with AtAll(M, fx, 0, fz, 0.0, keys=["stone"]):
        st = M["stone"]
        st.lathe([(R, 0), (R, 0.75), (R - 0.35, 0.75), (R - 0.35, 0.5), (0.55, 0.5)], n=48, tile=3.0, color=(0.88, 0.86, 0.82), cap_top=False, cap_bottom=False)
        st.lathe([(0.55, 0.5), (0.5, 1.4), (0.3, 2.1), (0.45, 2.3), (1.25, 2.5), (1.35, 2.75), (1.05, 2.6), (0.2, 2.5)], n=24, tile=2.0, color=(0.9, 0.88, 0.84), cap_top=False, cap_bottom=False)
        st.lathe([(0.2, 2.5), (0.22, 3.2), (0.3, 3.6), (0.18, 3.9), (0.02, 4.0)], n=14, tile=2.0, color=(0.9, 0.88, 0.84))
def water_disc(m, cx, cz, r, y, n=48, tile=4.0, color=(1, 1, 1)):
    ring = [(cx + r * math.sin(2 * math.pi * i / n), y, cz + r * math.cos(2 * math.pi * i / n)) for i in range(n)]
    m.face(ring, [(p[0] / tile, p[2] / tile) for p in ring], normal=(0, 1, 0), color=color)

BARK = (0.33, 0.25, 0.18)
def tree_variants(rng_seed=5):
    """returns list of (crown Mesh, trunk Mesh) in unit local frame (origin at ground)"""
    V = []; rng = random.Random(rng_seed)
    palettes = [((0.18, 0.40, 0.12), 0.18), ((0.35, 0.50, 0.14), 0.18), ((0.78, 0.60, 0.12), 0.2), ((0.78, 0.34, 0.10), 0.2), ((0.60, 0.20, 0.10), 0.16), ((0.25, 0.45, 0.16), 0.2)]
    for pi, (base, var) in enumerate(palettes):
        crown = Mesh("crown"); trunk = Mesh("trunk"); hgt = rng.uniform(3.0, 3.8)
        trunk.lathe([(0.34, 0), (0.28, 0.6), (0.2, hgt * 0.6), (0.14, hgt)], n=9, tile=2.0, color=BARK, cap_top=False, cap_bottom=False)
        for b in range(2): ba = rng.uniform(0, 6.28); trunk.tube((0, hgt * 0.6, 0), (0.9 * math.sin(ba), hgt * 0.6 + 1.3, 0.9 * math.cos(ba)), 0.1, 0.05, n=6, color=BARK)
        def col(r_, base=base, var=var):
            k = 1 + r_.uniform(-var, var); return (min(1, base[0] * k), min(1, base[1] * (1 + r_.uniform(-var * 0.6, var * 0.6))), min(1, base[2] * k))
        spots = [(0, hgt + 1.5, 0, 2.5), (1.5, hgt + 0.9, 0.4, 1.9), (-1.4, hgt + 1.1, -0.5, 2.0), (0.3, hgt + 0.8, 1.5, 1.8), (-0.4, hgt + 2.5, -0.3, 1.6)]
        for (cx, cy, cz, cr) in spots: crown.icosphere((cx, cy, cz), cr, 1, color=col, jitter=0.2, rng=rng, squash=(1, 0.85, 1))
        crown.merge(trunk); V.append(crown)
    # conifer
    crown = Mesh("crown"); trunk = Mesh("trunk"); rng2 = random.Random(77)
    trunk.lathe([(0.3, 0), (0.18, 4.0)], n=8, tile=2.0, color=BARK, cap_top=False, cap_bottom=False)
    for i, (rr, yy, hh_) in enumerate(((2.4, 1.2, 3.0), (1.9, 3.0, 2.8), (1.4, 4.7, 2.6), (0.9, 6.2, 2.2))):
        c = (0.07 + 0.02 * i, 0.22 + 0.03 * i, 0.12); crown.cone(0, yy, 0, rr, hh_, n=9, tile=2.0, color=c)
    crown.merge(trunk); V.append(crown)
    crown = Mesh("crown"); trunk = Mesh("trunk")   # poplar
    trunk.lathe([(0.25, 0), (0.14, 2.0)], n=7, tile=2.0, color=BARK, cap_top=False, cap_bottom=False)
    for i in range(4): crown.icosphere((0, 2.6 + i * 1.5, 0), 1.25 - 0.08 * i, 1, color=lambda r_, i=i: (0.65 + r_.uniform(-.1, .1), 0.55 + r_.uniform(-.08, .08), 0.12), jitter=0.15, rng=rng2, squash=(0.8, 1.5, 0.8))
    crown.merge(trunk); V.append(crown)
    return V

def road_strips(m, pts, width, kind, y, rng, step=3.0):
    """textured strip following polyline pts with wobbly edges; colours blend to grass at the edges"""
    P = [pts[0]]
    for (a, b) in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        for i in range(1, n + 1): P.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    rows = []; s = 0.0; tile = TILE["cobble"] if kind == "cobble" else TILE["dirt"]
    for i, p in enumerate(P):
        a = P[max(0, i - 1)]; b = P[min(len(P) - 1, i + 1)]; tx, tz = b[0] - a[0], b[1] - a[1]; l = math.hypot(tx, tz) or 1; tx, tz = tx / l, tz / l; nx, nz = -tz, tx
        if i: s += math.hypot(p[0] - P[i - 1][0], p[1] - P[i - 1][1])
        hw = width / 2; w1 = 0.22 * fbm_sin(p[0] * 3.1, p[1] * 3.1, 11) * 4; w2 = 0.22 * fbm_sin(p[0] * 3.1, p[1] * 3.1, 12) * 4
        offs = [-(hw + 0.45 + w1), -hw * 0.88, hw * 0.88, hw + 0.45 + w2]
        rows.append([(p[0] + nx * o, y, p[1] + nz * o) for o in offs] + [s])
    cols = [(0.62, 0.74, 0.40), (1.0, 0.97, 0.92), (1.0, 0.97, 0.92), (0.62, 0.74, 0.40)] if kind != "cobble" else [(0.7, 0.8, 0.55), (1, 1, 1), (1, 1, 1), (0.7, 0.8, 0.55)]
    for r0, r1 in zip(rows[:-1], rows[1:]):
        for j in range(3):
            q = [r0[j], r0[j + 1], r1[j + 1], r1[j]]; uv = [(q_[0] / tile, q_[2] / tile) for q_ in q]; c = [cols[j], cols[j + 1], cols[j + 1], cols[j]]
            n = norm(cross(sub(q[1], q[0]), sub(q[2], q[1])))
            if n[1] < 0: q = q[::-1]; uv = uv[::-1]; c = c[::-1]
            m.face(q, uv, normal=(0, 1, 0), color=c)

def plaza(mc, mp):
    """cobbled plaza disc with a wobbly edge; mc = cobble mesh"""
    n = 96; ring = []
    for i in range(n):
        a = 2 * math.pi * i / n; r = L.PLAZA_R + 0.7 * math.sin(5 * a + 1) + 0.5 * math.sin(11 * a + 2)
        ring.append((r * math.sin(a), 0.07, r * math.cos(a)))
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        mc.face([(0, 0.07, 0), a, b], [(0, 0), (a[0] / TILE["cobble"], a[2] / TILE["cobble"]), (b[0] / TILE["cobble"], b[2] / TILE["cobble"])], normal=(0, 1, 0), color=(1, 1, 1))
        # soft grass-tinted edge ring
    outer = [(p[0] * 1.045, 0.065, p[2] * 1.045) for p in ring]
    for i in range(n):
        a, b, a2, b2 = ring[i], ring[(i + 1) % n], outer[i], outer[(i + 1) % n]
        mc.face([a, a2, b2, b], [(p[0] / TILE["cobble"], p[2] / TILE["cobble"]) for p in (a, a2, b2, b)], normal=(0, 1, 0), color=[(1, 1, 1), (0.6, 0.72, 0.4), (0.6, 0.72, 0.4), (1, 1, 1)])

def fence(M, x0, z0, x1, z1, rng):
    n = max(1, int(math.hypot(x1 - x0, z1 - z0) / 2.2)); dx, dz = (x1 - x0) / n, (z1 - z0) / n; ang = math.atan2(dx, dz)
    for i in range(n + 1): M["wood"].box(x0 + dx * i, 0.55, z0 + dz * i, 0.1, 1.1, 0.1, tile=2.0, color=(0.55, 0.45, 0.36))
    for yy in (0.4, 0.8):
        with AtAll(M, (x0 + x1) / 2, yy, (z0 + z1) / 2, ang, keys=["wood"]): M["wood"].box(0, 0, 0, 0.05, 0.08, math.hypot(x1 - x0, z1 - z0), tile=2.0, color=(0.62, 0.5, 0.4))

def hay(M, x, z, rng):
    M["goods"].cone(x, 0, z, 1.1, 1.5, n=10, color=(0.88, 0.72, 0.3)); M["goods"].icosphere((x, 0.35, z), 0.9, 1, color=(0.85, 0.7, 0.3), squash=(1, 0.5, 1), rng=rng, jitter=0.05)

def field(m, x, z, w, d, rot, y=0.015, tile=3.0):
    pts = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    with m.at(x, y, z, rot): m.face([(px, 0, pz) for px, pz in pts][::-1], [(px / tile, pz / tile) for px, pz in pts][::-1], normal=(0, 1, 0), color=(1, 1, 1))

def build_core(seed=3):
    rng = random.Random(seed); M = {k: Mesh(k) for k in KEYS}; M["bush"] = Mesh("bush"); M["cobble"] = Mesh("cobble"); M["dirt"] = Mesh("dirt"); M["wheat"] = Mesh("wheat"); M["furrow"] = Mesh("furrow"); M["water"] = Mesh("water")
    for h in L.HOUSES: house(M, h, rng)
    inn(M, L.INN, rng); church(M, L.CHURCH, rng); smithy(M, L.SMITHY, rng)
    for i, s in enumerate(L.STALLS): stall(M, s, rng, i)
    for (x, z) in L.LAMPS: lamp(M, x, z, rng)
    for (x, z, r) in L.BENCHES: bench(M, x, z, r)
    for (x, z) in L.BARRELS: barrel(M, x, z, rng)
    for (x, z, r) in L.CRATES: crate(M, x, z, r, rng)
    fountain(M)
    for (hid, dx, dz, a, b) in (("H12", 0, 0, 17, 14), ("H13", 0, 0, 17, 14)):
        h = next(q for q in L.HOUSES if q[0] == hid); c, s = math.cos(h[7]), math.sin(h[7]); cx, cz = h[2] + 0 * c, h[3]
        # yard fence rectangle in front of the farmhouse (world axis aligned)
        sgn = -1 if hid == "H12" else 1; x0, x1 = h[2] - 9, h[2] + 9; z0, z1 = h[3] - 11, h[3] + 11
        fence(M, x0, z0, x1, z0, rng); fence(M, x0, z1, x1, z1, rng); fence(M, x1, z0, x1, z1, rng); fence(M, x0, z0, x0, z0 + 8, rng); fence(M, x0, z1 - 8, x0, z1, rng)
        hay(M, h[2] + 5, h[3] + 8, rng)
    brng = random.Random(41)
    def bushes(x, z, n, spread, base=(0.2, 0.42, 0.14)):
        for _ in range(n):
            bx, bz = x + brng.uniform(-spread, spread), z + brng.uniform(-spread * 0.4, spread * 0.4); r = brng.uniform(0.35, 0.8); k = brng.uniform(0.8, 1.2)
            col = lambda rr, k=k: (min(1, base[0] * k * rr.uniform(0.85, 1.2)), min(1, base[1] * k * rr.uniform(0.9, 1.15)), min(1, base[2] * k))
            M["bush"].icosphere((bx, r * 0.6, bz), r, 1, color=col, jitter=0.18, rng=brng, squash=(1.2, 0.8, 1.0))
    for h in L.HOUSES:
        c, s_ = math.cos(h[7]), math.sin(h[7]); fx, fz = h[2] + s_ * (h[5] / 2 + 0.9), h[3] + c * (h[5] / 2 + 0.9)       # in front of the facade
        for side in (-1, 1): bushes(fx + side * h[4] * 0.36 * c, fz - side * h[4] * 0.36 * s_, 2, 1.2)
    for (x, z, w, d, rot, kind) in L.FIELDS: bushes(x, z - d / 2 - 1.0, 6, w * 0.45, base=(0.25, 0.4, 0.12))
    plaza(M["cobble"], None)
    for pts, width, kind in L.ROADS:
        yv = {"dirt": 0.02, "cobble": 0.05}[kind] + (0.01 if pts[0][0] == 0 and pts[0][1] != 0 else 0.0) + (0.015 if width < 4 else 0.0)
        road_strips(M["cobble"] if kind == "cobble" else M["dirt"], pts, width, kind, yv, rng)
    for (x, z, w, d, rot, kind) in L.FIELDS: field(M["wheat" if kind == "wheat" else "furrow"], x, z, w, d, rot)
    water_disc(M["water"], L.FOUNTAIN[0], L.FOUNTAIN[1], L.FOUNTAIN[2] - 0.36, 0.52, n=48)
    return M

def terrain_rings(rmin, rmax, nang, dr0, grow, hfun, tint_fun, flat_until=0.0, tile=5.0, skirt=False):
    """radial grid mesh; returns Mesh with vertex colours from tint_fun(x,z,h) and smooth normals from finite differences"""
    m = Mesh("terrain"); radii = [rmin]; dr = dr0
    while radii[-1] < rmax:
        radii.append(min(rmax, radii[-1] + dr)); dr = dr * grow if radii[-1] > flat_until else dr
    verts = []
    for r in radii:
        row = []
        for i in range(nang):
            a = 2 * math.pi * i / nang; x, z = r * math.sin(a), r * math.cos(a); y = hfun(x, z); e = max(1.0, r * 0.004)
            nx = (hfun(x - e, z) - hfun(x + e, z)) / (2 * e); nz = (hfun(x, z - e) - hfun(x, z + e)) / (2 * e); n = norm((nx, 1.0, nz)); row.append(((x, y, z), n, tint_fun(x, z, y)))
        verts.append(row)
    for j in range(len(radii) - 1):
        for i in range(nang):
            i2 = (i + 1) % nang; q = [verts[j][i], verts[j + 1][i], verts[j + 1][i2], verts[j][i2]]
            m.face([v[0] for v in q], [(v[0][0] / tile, v[0][2] / tile) for v in q], normals=[v[1] for v in q], color=[v[2] for v in q])
    return m
