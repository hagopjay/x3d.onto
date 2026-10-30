#!/usr/bin/env python3
"""Camera grammar for the dynasty hypersphere: every shot computed from loom-view.json, and a stand-in X3D that proves the moves in X_ITE.

    python3 -I build_camera_proof.py [--data PATH] [--out DIR]

For each family (rothschild, habsburg, darwin_wedgwood) it writes into DIR (default ../proof):
  hyper-<fam>.x3d     the pocket, in its own units (the present = radius 10): a stand-in hypersphere (core, glass shell, year rings,
                      sector meridians, one fiber per life, lineage links, marriage arcs on the shell of their year, birth beads),
                      every shot as a Viewpoint (rolled shots inside an "up frame" Transform), the Probe rig the page flies, the
                      camera sensor, the scriptless Flywheel orbit, two clickable beads, and EXPORTs so a host can IMPORT them;
  camera.x3d (rothschild) / camera-<fam>.x3d   the host: a stand-in host space, the opening viewpoint, the pocket pages' rig (a control),
                      and the pocket Inlined at scale 0.5 with IMPORTs;
  shots-<fam>.json    the shot table and the tour (position, target, up, fov, size, transition, hold, caption with grade) and the chain checks;
  receipt-build.json  sha256 of every input and output.

The hypersphere layout here is a stand-in for the scene generator's: radius = time (the earliest founder's birth at the centre, the
`asof` year at radius 10), houses as azimuth sectors west to east (by longitude; angle proportional to 2 + people), the founders' house
facing +Z, a life as a radial fiber from its birth radius to its death radius. The camera reads only: r(year), the sector centres and
spans, and the fiber end points, so it follows whatever layout the real scene settles on. Deterministic, standard library only."""
import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.normpath(os.path.join(HERE, '..', '..'))
FAMILIES = ['rothschild', 'habsburg', 'darwin_wedgwood']
R = 10.0                  # the present (asof) shell, pocket units
CORE_R = 0.45             # the founders' core glow; fibers start no nearer than this
POCKET_SCALE = 0.5        # host units per pocket unit (the host Inlines the pocket at this scale)
ASPECT = 1527 / 923       # design viewport (X_ITE: fieldOfView spans the smaller side, the height here)
Y = (0.0, 1.0, 0.0)
SIZES = ['ELS', 'LS', 'MS', 'MCU', 'CU', 'POV']
CONF_V = {'Confirmed': 1.0, 'Likely': 0.82, 'Suspected': 0.55}
GRADE_RANK = {'Suspected': 0, 'Likely': 1, 'Confirmed': 2}
TIMING = {'base': 2.2, 'per_S': 0.55, 'per_rad': 0.9, 'min': 3.5, 'max': 7.5}   # flight seconds = base + per_S * van Wijk path length + per_rad * turn of the view direction


# ---------------------------------------------------------------- vectors and rotations
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def norm(a):
    L = length(a)
    return mul(a, 1.0 / L) if L > 1e-12 else (0.0, 0.0, 0.0)
def clamp(x, a, b): return max(a, min(b, x))


def sph(phi, lat, r=1.0):
    """Azimuth phi from +Z toward +X (west to east reads left to right from the +Z side), latitude toward +Y (the pole)."""
    return (r * math.sin(phi) * math.cos(lat), r * math.sin(lat), r * math.cos(phi) * math.cos(lat))


def slerp_dir(a, b, t):
    a, b = norm(a), norm(b); c = clamp(dot(a, b), -1.0, 1.0); w = math.acos(c)
    if w < 1e-6: return a
    s = math.sin(w)
    return add(mul(a, math.sin((1 - t) * w) / s), mul(b, math.sin(t * w) / s))


def quat_from_basis(x, y, z):
    m = [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2; w = 0.25 * s; qx = (m[2][1] - m[1][2]) / s; qy = (m[0][2] - m[2][0]) / s; qz = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2; w = (m[2][1] - m[1][2]) / s; qx = 0.25 * s; qy = (m[0][1] + m[1][0]) / s; qz = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2; w = (m[0][2] - m[2][0]) / s; qx = (m[0][1] + m[1][0]) / s; qy = 0.25 * s; qz = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2; w = (m[1][0] - m[0][1]) / s; qx = (m[0][2] + m[2][0]) / s; qy = (m[1][2] + m[2][1]) / s; qz = 0.25 * s
    n = math.sqrt(w * w + qx * qx + qy * qy + qz * qz)
    return (qx / n, qy / n, qz / n, w / n)


def quat_to_aa(q):
    x, y, z, w = q
    if w < 0: x, y, z, w = -x, -y, -z, -w
    w = clamp(w, -1.0, 1.0); ang = 2 * math.acos(w); s = math.sqrt(max(0.0, 1 - w * w))
    if s < 1e-9 or ang < 1e-9: return (0.0, 0.0, 1.0, 0.0)
    return (x / s, y / s, z / s, ang)


def look_at(pos, tgt, up=Y):
    """X3D orientation (axis, angle) of a camera at pos looking at tgt (cameras look down -Z with +Y up)."""
    z = norm(sub(pos, tgt)); x = norm(cross(up, z))
    if length(x) < 1e-9: x = norm(cross((0.0, 0.0, 1.0) if abs(z[1]) > 0.9 else Y, z))
    yv = cross(z, x)
    return quat_to_aa(quat_from_basis(x, yv, z))


def frame_to(u):
    """Rotation (axis, angle) that takes +Y to u: the 'up frame' a rolled shot lives in, so X_ITE's horizon straightening keeps u up."""
    u = norm(u); c = clamp(dot(Y, u), -1.0, 1.0)
    if c > 1 - 1e-12: return (0.0, 0.0, 1.0, 0.0)
    if c < -1 + 1e-12: return (1.0, 0.0, 0.0, math.pi)
    return tuple(norm(cross(Y, u))) + (math.acos(c),)


def rotate(v, aa):
    ax = norm(aa[:3]); a = aa[3]; c, s = math.cos(a), math.sin(a)
    return add(add(mul(v, c), mul(cross(ax, v), s)), mul(ax, dot(ax, v) * (1 - c)))


def inv(aa): return (aa[0], aa[1], aa[2], -aa[3])


def fmt(x):
    s = ('%.4f' % x).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def v3(v): return ' '.join(fmt(x) for x in v)
def rot4(aa): return ' '.join(fmt(x) for x in aa)
def xa(s): return str(s).replace('&', '&amp;').replace("'", '&apos;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def wijk_S(u1, w0, w1):
    """Length of van Wijk and Nuij's optimal zoom-and-pan path (rho = sqrt 2), as in x3d.onto/v2/engine.js."""
    rho, rho2, rho4 = math.sqrt(2), 2.0, 4.0
    if u1 < 1e-7 * max(w0, w1): return abs(math.log(w1 / w0)) / rho
    b0 = (w1 * w1 - w0 * w0 + rho4 * u1 * u1) / (2 * w0 * rho2 * u1); b1 = (w1 * w1 - w0 * w0 - rho4 * u1 * u1) / (2 * w1 * rho2 * u1)
    r0 = math.log(math.sqrt(b0 * b0 + 1) - b0); r1 = math.log(math.sqrt(b1 * b1 + 1) - b1)
    return (r1 - r0) / rho


def icosphere(sub_n):
    t = (1 + math.sqrt(5)) / 2
    pts = [norm(p) for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    tris = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(sub_n):
        cache = {}; nt = []
        def mid(i, j):
            k = (min(i, j), max(i, j))
            if k not in cache: pts.append(norm(mul(add(pts[i], pts[j]), 0.5))); cache[k] = len(pts) - 1
            return cache[k]
        for a, b, c in tris:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a); nt += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        tris = nt
    return pts, tris


def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def brighten(c, v=1.0, s_max=0.78):
    mx = max(c); mn = min(c)
    if mx < 1e-9: return (v, v, v)
    sat = min(s_max, (mx - mn) / mx); k = [(x - mn) / (mx - mn) if mx > mn else 1.0 for x in c]
    return tuple(v * (1 - sat + sat * x) for x in k)


def yr(y, prec):
    return ('c. %d' % y) if prec == 'circa' else str(y)


# ---------------------------------------------------------------- layout (stand-in) and shots
def build_family(fam, asof):
    P = {p['id']: p for p in fam['people']}
    founders = [i for d in fam['dyes'].values() for i in d['founders'] if i in P]
    f0 = min(founders, key=lambda i: (P[i]['born'], i))
    y0 = P[f0]['born']; span = asof - y0
    def r(y): return R * (y - y0) / span
    kids = defaultdict(list)
    for p in sorted(P.values(), key=lambda p: (p['born'], p['id'])):
        for k in ('father', 'mother'):
            if p.get(k) in P: kids[p[k]].append(p['id'])
    known_unions = [u for u in fam['unions'] if u.get('year') and u.get('year_precision') in ('year', 'day') and u['a'] in P and u['b'] in P]
    uyears = defaultdict(list)
    for u in known_unions: uyears[u['a']].append(u['year']); uyears[u['b']].append(u['year'])

    # houses: azimuth sectors west to east by longitude (ties: opened, key), angle proportional to 2 + people, founders' house at azimuth 0
    hs = sorted(fam['houses'], key=lambda h: (h['lon'], h.get('opened') or 0, h['key']))
    keys = [h['key'] for h in hs]; cnt = Counter(p['house'] for p in P.values())
    gap = math.radians(4.0); wts = [2 + cnt[k] for k in keys]; avail = 2 * math.pi - gap * len(hs)
    spans = [avail * w / sum(wts) for w in wts]; cents = []; a = 0.0
    for s in spans: cents.append(a + gap / 2 + s / 2); a += s + gap
    fh = P[f0]['house']; shift = cents[keys.index(fh)]; cents = [c - shift for c in cents]
    sectors = {k: {'name': h['name'], 'phi': cents[i], 'span': spans[i], 'people': cnt[k], 'opened': h.get('opened'), 'closed': h.get('closed'), 'lon': h['lon']} for i, (k, h) in enumerate(zip(keys, hs))}

    # people: lineage order inside each house (DFS from the roots, children by birth), latitude bands top to bottom, golden-ratio azimuth jitter
    dirs = {}
    for hi, k in enumerate(keys):
        ids = {p['id'] for p in P.values() if p['house'] == k}
        roots = sorted([P[i] for i in ids if not any(P[i].get(f) in ids for f in ('father', 'mother'))], key=lambda p: (p['born'], p['id']))
        seq, seen = [], set()
        def dfs(pid):
            if pid in seen: return
            seen.add(pid); seq.append(pid)
            for c in kids[pid]:
                if c in ids: dfs(c)
        for rt in roots: dfs(rt['id'])
        for i in sorted(ids - seen, key=lambda i: (P[i]['born'], i)): dfs(i)
        n = len(seq)
        for i, pid in enumerate(seq):
            lat = math.asin(clamp(1 - 2 * (i + 0.5) / n, -1, 1)) * 0.80
            jit = ((i + 1) * 0.6180339887498949) % 1.0 - 0.5
            dirs[pid] = sph(cents[hi] + jit * spans[hi] * 0.72, lat, 1.0)

    fibers = {}
    for pid, p in P.items():
        ra = max(r(p['born']), CORE_R)
        if p.get('died') is not None: rb, est = r(p['died']), False
        else:
            cand = [P[c]['born'] for c in kids[pid]] + uyears[pid]
            rb, est = (r(max(cand)), True) if cand else (ra + 0.15, True)
        rb = max(rb, ra + 0.05)
        fibers[pid] = {'a': mul(dirs[pid], ra), 'b': mul(dirs[pid], rb), 'ra': ra, 'rb': rb, 'end_estimated': est}
    links = []
    for pid, p in P.items():
        par = p['father'] if p.get('father') in P else (p['mother'] if p.get('mother') in P else None)
        if par: links.append((par, pid, max(r(p['born']), CORE_R)))
    return dict(P=P, founders=founders, f0=f0, y0=y0, asof=asof, span=span, r=r, kids=kids, sectors=sectors, keys=keys,
                dirs=dirs, fibers=fibers, links=links, known_unions=known_unions, fh=fh)


def tangent_toward(n, d2):
    g = sub(d2, mul(n, dot(n, d2)))
    return norm(g) if length(g) > 1e-6 else norm(cross(Y, n)) if length(cross(Y, n)) > 1e-6 else (1.0, 0.0, 0.0)


def life(p):
    return '%s (%s–%s)' % (p['name'], yr(p['born'], p.get('born_precision')), yr(p['died'], p.get('died_precision')) if p.get('died') is not None else 'death year not given')


def lowest(*gs):
    gs = [g for g in gs if g]
    return min(gs, key=lambda g: GRADE_RANK.get(g, 3)) if gs else '∑'


def make_shots(fam, L):
    P, r, S_ = L['P'], L['r'], L['sectors']
    uf = sph(S_[L['fh']]['phi'], 0.0, 1.0)
    shots = {}
    def put(name, pos, tgt, fov, size, beat, up=Y, space='pocket', nav='EXAMINE', subject=None):
        shots[name] = dict(name=name, pos=[round(x, 5) for x in pos], tgt=[round(x, 5) for x in tgt], up=[round(x, 6) for x in norm(up)], fov=fov,
                           size=size, beat=beat, space=space, nav=nav, subject=subject, frame=None if length(sub(norm(up), Y)) < 1e-9 else [round(x, 6) for x in frame_to(up)])
    # Host (ELS): outside the pocket, in host units; the pocket fills 40% of the frame height; behind the core as seen from the founders' house
    fov = 0.9; d = R * POCKET_SCALE / math.sin(0.40 * fov / 2); el = math.radians(14)
    put('Host', add(mul(uf, -d * math.cos(el)), (0.0, d * math.sin(el), 0.0)), (0.0, 0.0, 0.0), fov, 'ELS',
        'Opening: a small bright world in a larger one', space='host')
    # Inside (POV): behind the founders' core (outside its glow), looking out along their house's fibers
    side = norm(cross(uf, Y))
    put('Inside', add(add(mul(uf, -2.6), (0.0, 0.55, 0.0)), mul(side, -0.45)), add(add(mul(uf, 6.0), (0.0, 1.0, 0.0)), mul(side, 0.4)), 1.15, 'POV',
        'The founders: everything grows out of this core', nav='FLY')
    # Wide (LS): the whole sphere from the founders' house side; the sphere is 74% of the frame height
    fov = 0.8; d = R / math.sin(0.74 * fov / 2)
    put('Wide', sph(0.0, math.radians(16), d), (0.0, 0.0, 0.0), fov, 'LS', 'The whole dynasty at once')
    # Crown (LS, top): over the pole, the founders' house at the top of the frame (no roll: the camera sits on the far side, 74 degrees up)
    fov = 1.0; d = R / math.sin(0.86 * fov / 2)
    put('Crown', sph(math.pi, math.radians(74), d), (0.0, 0.0, 0.0), fov, 'LS', 'The houses as a compass, west to east')
    # Colossus (MS, low angle): inside the shell under the largest house, looking up its fibers to the core; wide lens
    big = max(L['keys'], key=lambda k: (S_[k]['people'], -S_[k]['lon']))
    phi = S_[big]['phi']
    put('Colossus', sph(phi, math.radians(-40), 0.84 * R), sph(phi, math.radians(18), 0.22 * R), 1.22, 'MS', 'The largest house towers over you', subject=big)
    # Houses (MS): outside the shell facing a sector; its chord fills 70% of the frame width; never nearer than R + 1.5 to the centre
    fov = 0.75
    for k in L['keys']:
        sc = S_[k]; ids = sorted(p['born'] for p in P.values() if p['house'] == k)
        rm = r(ids[len(ids) // 2]) if ids else 0.5 * R
        tgt = sph(sc['phi'], 0.0, rm); chord = 2 * R * math.sin(min(sc['span'], math.pi) / 2)
        dd = (chord / 2) / (0.7 * math.tan(fov / 2) * ASPECT); dirv = sph(sc['phi'], math.radians(12), 1.0)
        dd = max(dd, (-dot(tgt, dirv) + math.sqrt(dot(tgt, dirv) ** 2 - dot(tgt, tgt) + (R + 1.5) ** 2)))
        put('House_' + k, add(tgt, mul(dirv, dd)), tgt, fov, 'MS', 'One house: %s' % sc['name'], subject=k)
    # the two people the close shots are about
    nonf = [p for p in P.values() if p['id'] not in L['founders'] and p.get('core')]
    by_kids = sorted(nonf, key=lambda p: (-len(L['kids'][p['id']]), p['born'], p['id']))
    pe = by_kids[0]; pp = next((p for p in by_kids if p['house'] != pe['house']), by_kids[1])
    # EyeToEye (CU): level with pe's fiber at a year the file gives (first dated marriage, else first child's birth, else mid-life, computed)
    n = L['dirs'][pe['id']]; why = None
    us = sorted([u for u in L['known_unions'] if pe['id'] in (u['a'], u['b'])], key=lambda u: (u['year'], u['id']))
    if us:
        u = us[0]; sp = P[u['b'] if u['a'] == pe['id'] else u['a']]; year = u['year']; g = tangent_toward(n, L['dirs'][sp['id']])
        why = dict(kind='marriage', year=year, text='%s marries %s, %d' % (pe['name'], sp['name'], year), grade=u.get('confidence') or 'Likely', spouse=sp['id'], union=u['id'])
    else:
        ch = [P[c] for c in L['kids'][pe['id']] if P[c].get('born_precision') in ('year', 'day')]
        if ch:
            c = min(ch, key=lambda c: (c['born'], c['id'])); year = c['born']; g = tangent_toward(n, L['dirs'][c['id']])
            why = dict(kind='first child', year=year, text='%s: first child, %s, born %d' % (pe['name'], c['name'], year), grade=lowest(pe.get('confidence'), c.get('confidence')), child=c['id'])
        else:
            year = (pe['born'] + (pe.get('died') or pe['born'])) // 2; g = norm(cross(Y, n))
            why = dict(kind='mid-life (computed)', year=year, text='%s at %d, mid-life (computed)' % (pe['name'], year), grade='∑')
    fb = L['fibers'][pe['id']]; Lf = fb['rb'] - fb['ra']; fov = 0.62
    de = clamp(Lf / (0.85 * 2 * math.tan(fov / 2)), 1.2, 5.0); hw = de * math.tan(fov / 2) * ASPECT
    Pt = mul(n, r(year)); mid = mul(n, (fb['ra'] + fb['rb']) / 2); lead = mul(g, hw / 3)
    t = norm(cross(g, n))                     # camera side: screen right is +g (the spouse), so the subject sits on the left third with lead room
    tgt = add(add(mid, mul(n, 0.0)), lead)
    put('EyeToEye', add(tgt, mul(t, de)), tgt, fov, 'CU', 'Eye to eye with one life at one year', up=n, subject=pe['id'])
    shots['EyeToEye'].update(year=year, year_r=round(r(year), 4), year_point=[round(x, 5) for x in Pt], why=why)
    # Present (MCU): the picked person, Probe flight from the real camera pose (Gobbler v4); time is up (radial up), whole life in 62% of the height
    n2 = L['dirs'][pp['id']]; fb2 = L['fibers'][pp['id']]; L2 = fb2['rb'] - fb2['ra']; fov = 0.75
    dp = clamp(L2 / (0.62 * 2 * math.tan(fov / 2)), 1.5, 6.0); mid2 = mul(n2, (fb2['ra'] + fb2['rb']) / 2)
    e2 = norm(cross(Y, n2)) if length(cross(Y, n2)) > 1e-6 else (1.0, 0.0, 0.0); el = math.radians(10)
    put('Present', add(mid2, add(mul(e2, dp * math.cos(el)), mul(n2, dp * math.sin(el)))), mid2, fov, 'MCU', 'Present one person: a whole life, its parents and marriages', up=n2, subject=pp['id'])
    shots['Present'].update(bead=[round(x, 5) for x in fb2['a']])
    shots['EyeToEye'].update(bead=[round(x, 5) for x in fb['a']])
    # Flywheel (LS): the idle orbit, scriptless (a TimeSensor turns the rig that holds the Viewpoint): one turn in 120 s, 20 degrees up
    put('Flywheel', sph(0.0, math.radians(20), 2.3 * R), (0.0, 0.0, 0.0), 0.85, 'LS', 'Idle: the world keeps turning')
    shots['Flywheel'].update(period_s=120)
    return shots, pe, pp, big, why


def make_tour(fam, L, shots, pe, pp, big, why):
    P, S_ = L['P'], L['sectors']
    fz = [P[i] for i in L['founders']]
    fu = [u for u in L['known_unions'] if {u['a'], u['b']} <= set(L['founders'])]
    births = [p['born'] for p in P.values()]
    caps = {}
    caps['Host'] = ('%s: %d people in %d houses, born %d to %d. Radius is time: %d at the core, %d at the shell.' % (
        fam['name'], len(P), len(S_), min(births), max(births), L['y0'], L['asof']), '∑')
    t = 'The core: ' + ' and '.join(life(p) for p in fz[:2]) + (', married %d' % fu[0]['year'] if fu else '')
    caps['Inside'] = (t, lowest(*[p.get('confidence') for p in fz[:2]], *(u.get('confidence') for u in fu[:1])))
    caps['Colossus'] = ('%s, the largest house: %d people.' % (S_[big]['name'], S_[big]['people']), '∑')
    caps['EyeToEye'] = (why['text'] + '.', why['grade'])
    caps['Crown'] = ('%d houses, west to east: %s. Angle = 2 + people.' % (len(S_), ', '.join(S_[k]['name'] for k in L['keys'])), '∑')
    hk = pp['house']; sc = S_[hk]
    caps['House_' + hk] = ('%s: %d people; the house runs %s to %s in the file.' % (sc['name'], sc['people'], sc['opened'], sc['closed'] or 'the present'), '∑')
    caps['Present'] = ('%s, %s: %d children in the file.' % (life(pp), sc['name'], len(L['kids'][pp['id']])), lowest(pp.get('confidence')))
    nu = len(fam['unions']); nk = len(L['known_unions'])
    caps['Wide'] = ('%d marriages: %d with a year sit on the shell of that year; %d without one are not drawn here.' % (nu, nk, nu - nk), '∑')
    caps['Flywheel'] = ('Idle orbit: one turn in %d s.' % shots['Flywheel']['period_s'], None)
    order = [('Host', 'load'), ('Inside', 'plunge'), ('Colossus', 'fly'), ('EyeToEye', 'fly'), ('Crown', 'fly'), ('House_' + hk, 'fly'),
             ('Present', 'fly'), ('Wide', 'fly'), ('Flywheel', 'bind')]
    stops, prev = [], None
    for name, move in order:
        s = shots[name]; text, grade = caps[name]
        words = len(text.split()); hold = math.ceil(clamp(1.5 + words / 3.0, 4.0, 9.0) * 10) / 10 if name != 'Flywheel' else 3.0   # the tour ends inside the idle orbit, which keeps turning
        st = dict(shot=name, move=move, caption=text, grade=grade, hold_s=hold, words=words, size=s['size'])
        if prev is not None:
            a = shots[prev]; pa, pb = to_pocket(a), to_pocket(s)
            u1 = length(sub(pb['F'], pa['F'])); S = wijk_S(u1, max(pa['w'], 1e-3), max(pb['w'], 1e-3))
            turn = math.acos(clamp(dot(pa['dir'], pb['dir']), -1, 1))
            dur = 7.0 if move == 'plunge' else 2.4 if move == 'bind' else round(clamp(TIMING['base'] + TIMING['per_S'] * S + TIMING['per_rad'] * turn, TIMING['min'], TIMING['max']), 2)
            fa = norm(sub(pa['F'], pa['pos'])); fb_ = norm(sub(pb['F'], pb['pos']))
            st.update(path_S=round(S, 3), dur_s=dur, axis_turn_deg=round(math.degrees(math.acos(clamp(dot(fa, fb_), -1, 1))), 1),
                      dist_ratio=round(max(pa['w'], pb['w']) / max(1e-6, min(pa['w'], pb['w'])), 2))
        stops.append(st); prev = name
    checks = []
    for i in range(1, len(stops)):
        a, b = stops[i - 1], stops[i]
        if b['move'] == 'bind':
            checks.append(dict(pair=[a['shot'], b['shot']], ok=True, note='hand-off to the idle orbit (continuous, not a new framing)')); continue
        ok = a['size'] != b['size'] and (b['axis_turn_deg'] >= 20 or b['dist_ratio'] >= 2)
        checks.append(dict(pair=[a['shot'], b['shot']], ok=ok, sizes=[a['size'], b['size']], axis_turn_deg=b['axis_turn_deg'], dist_ratio=b['dist_ratio']))
    reads = [dict(shot=s['shot'], words=s['words'], hold_s=s['hold_s'], need_s=round(1.5 + s['words'] / 3.0, 1), ok=s['hold_s'] is None or s['hold_s'] >= min(9.0, 1.5 + s['words'] / 3.0) - 1e-9) for s in stops]
    return stops, checks, reads


def to_pocket(s):
    """A shot as the flight engine sees it, in pocket units: focus F, direction from focus to camera, distance w, up, fov."""
    k = 1.0 / POCKET_SCALE if s['space'] == 'host' else 1.0
    pos = mul(s['pos'], k); F = mul(s['tgt'], k)
    return dict(pos=pos, F=F, dir=norm(sub(pos, F)), w=length(sub(pos, F)), up=s['up'], fov=s['fov'])


# ---------------------------------------------------------------- X3D writers
HEAD = ("<?xml version='1.0' encoding='UTF-8'?>\n<!DOCTYPE X3D PUBLIC 'ISO//Web3D//DTD X3D 4.0//EN' 'https://www.web3d.org/specifications/x3d-4.0.dtd'>\n"
        "<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>\n")


def vp_xml(name, s, desc, ind='    ', extra=''):
    """A shot as a standard Viewpoint; a rolled shot goes inside an up-frame Transform (DEF Frame_<name>) and is written in its local axes."""
    pos, tgt = s['pos'], s['tgt']
    if s['frame']:
        fr = s['frame']; lp, lt = rotate(pos, inv(fr)), rotate(tgt, inv(fr))
        o = look_at(lp, lt, Y)
        return ("%s<Transform DEF='Frame_%s' rotation='%s'>\n%s  <Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'%s/>\n%s</Transform>\n" % (
            ind, name, rot4(fr), ind, name, xa(desc), v3(lp), rot4(o), v3(lt), fmt(s['fov']), extra, ind))
    o = look_at(pos, tgt, Y)
    return "%s<Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'%s/>\n" % (
        ind, name, xa(desc), v3(pos), rot4(o), v3(tgt), fmt(s['fov']), extra)


def lineset(DEF, segs, color_of, width, ind='    '):
    """segs: list of polylines [(points, colors)]; one IndexedLineSet with per-vertex colour."""
    pts, cols, idx = [], [], []
    for poly, cl in segs:
        base = len(pts); pts += poly; cols += cl; idx += [str(base + i) for i in range(len(poly))] + ['-1']
    return ("%s<Shape DEF='%s'>\n%s  <Appearance><Material emissiveColor='1 1 1' diffuseColor='0 0 0'/><LineProperties linewidthScaleFactor='%s'/></Appearance>\n"
            "%s  <IndexedLineSet colorPerVertex='true' coordIndex='%s'>\n%s    <Coordinate point='%s'/>\n%s    <Color color='%s'/>\n%s  </IndexedLineSet>\n%s</Shape>\n") % (
        ind, DEF, ind, fmt(width), ind, ' '.join(idx), ind, ', '.join(v3(p) for p in pts), ind, ', '.join(v3(c) for c in cols), ind, ind), len(idx) - idx.count('-1') - (len(segs))


def trimesh(DEF, sub_n, radius, mat, center=(0.0, 0.0, 0.0), ind='    ', solid='false'):
    pts, tris = icosphere(sub_n)
    return ("%s<Shape DEF='%s'>\n%s  <Appearance>%s</Appearance>\n%s  <IndexedTriangleSet solid='%s' index='%s'>\n%s    <Coordinate point='%s'/>\n%s  </IndexedTriangleSet>\n%s</Shape>\n") % (
        ind, DEF, ind, mat, ind, solid, ' '.join('%d %d %d' % t for t in tris), ind, ', '.join(v3(add(center, mul(p, radius))) for p in pts), ind, ind), len(tris)


def arc(d1, d2, rad, step=0.06):
    a = math.acos(clamp(dot(norm(d1), norm(d2)), -1, 1)); n = max(2, int(math.ceil(a / step)) + 1)
    return [mul(slerp_dir(d1, d2, i / (n - 1)), rad) for i in range(n)]


def write_pocket(fam, L, shots, pe, pp, path):
    P, r = L['P'], L['r']; tri = 0; seg = 0
    dye = {k: brighten(hex_rgb(v['color'])) for k, v in fam['dyes'].items()}
    grey = (0.42, 0.45, 0.6)
    def colour(p, scale=1.0):
        sh = p.get('shares') or {}; tot = sum(sh.values()); c = (0.0, 0.0, 0.0)
        for k, s in sorted(sh.items()):
            if k in dye: c = add(c, mul(dye[k], s))
        c = mul(c, 1.0 / tot) if tot > 1e-9 else grey
        c = add(mul(c, min(1.0, tot) * 0.85 + 0.15), mul(grey, (1 - min(1.0, tot)) * 0.85))
        return mul(c, CONF_V.get(p.get('confidence'), 0.8) * scale)
    o = [HEAD, "  <head>\n    <component name='Shape' level='5'/>\n",
         "    <meta name='title' content='%s'/>\n" % os.path.basename(path),
         "    <meta name='description' content='Dynasty hypersphere, camera stand-in, %s: radius = time (%d at the centre, %d at radius 10), houses as azimuth sectors west to east (angle = 2 + people), one radial fiber per life, marriages as arcs on the shell of their year. Every shot of the camera grammar is a Viewpoint here. Generated; do not edit.'/>\n" % (xa(fam['name']), L['y0'], L['asof']),
         "    <meta name='generator' content='proto/hyper/tools/build_camera_proof.py'/>\n    <meta name='data' content='proto/merged/loom-view.json'/>\n  </head>\n  <Scene>\n",
         "    <WorldInfo title='Hypersphere camera proof: %s'/>\n" % xa(fam['name']),
         "    <NavigationInfo DEF='Nav' type='\"EXAMINE\" \"ANY\"' headlight='false' speed='2' transitionType='\"ANIMATE\"' transitionTime='1.6'/>\n",
         "    <NavigationInfo DEF='NavFly' type='\"FLY\" \"ANY\"' headlight='false' speed='1.2' transitionType='\"ANIMATE\"' transitionTime='2.4'/>\n",
         "    <Background DEF='PocketSky' skyColor='0.012 0.01 0.03'/>\n",
         "    <!-- The shots. Wide comes first so it is bound when this file is opened alone; inside a host the host's opening viewpoint is bound. -->\n"]
    for name in ['Wide', 'Crown', 'Colossus', 'EyeToEye', 'Present'] + ['House_' + k for k in L['keys']]:
        o.append(vp_xml(name, shots[name], name.replace('_', ' ') if not name.startswith('House_') else 'House: ' + L['sectors'][name[6:]]['name']))
    s = shots['Inside']; ori = look_at(s['pos'], s['tgt'])
    o.append("    <Viewpoint DEF='Inside' description='Inside' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'>\n      <NavigationInfo USE='NavFly' containerField='navigationInfo'/>\n    </Viewpoint>\n" % (
        v3(s['pos']), rot4(ori), v3(s['tgt']), fmt(s['fov'])))
    s = shots['Flywheel']; ori = look_at(s['pos'], s['tgt'])
    o.append("    <!-- Flywheel: the idle orbit with no script. The clock turns the rig, the rig carries the Viewpoint; EXAMINE still works on top. -->\n"
             "    <Transform DEF='FlywheelRig'>\n      <Viewpoint DEF='Flywheel' description='Flywheel (idle orbit)' position='%s' orientation='%s' centerOfRotation='0 0 0' fieldOfView='%s'/>\n    </Transform>\n"
             "    <TimeSensor DEF='FlywheelClock' cycleInterval='%d' loop='true'/>\n"
             "    <OrientationInterpolator DEF='FlywheelTurn' key='0 0.25 0.5 0.75 1' keyValue='0 1 0 0, 0 1 0 1.570796, 0 1 0 3.141593, 0 1 0 4.712389, 0 1 0 6.283185'/>\n"
             "    <ROUTE fromNode='FlywheelClock' fromField='fraction_changed' toNode='FlywheelTurn' toField='set_fraction'/>\n"
             "    <ROUTE fromNode='FlywheelTurn' fromField='value_changed' toNode='FlywheelRig' toField='set_rotation'/>\n" % (
                 v3(s['pos']), rot4(ori), fmt(s['fov']), s['period_s']))
    w = shots['Wide']
    o.append("    <!-- Probe: the viewpoint the page flies (from the real camera pose). ProbeFrame turns +Y to the shot's up, so X_ITE's horizon\n"
             "         straightening keeps a rolled shot (time up) level when the user drags. CamSense reports the camera in pocket units. -->\n"
             "    <Transform DEF='ProbeFrame'>\n      <Viewpoint DEF='Probe' description='Probe' position='%s' orientation='%s' centerOfRotation='0 0 0' fieldOfView='%s'/>\n    </Transform>\n"
             "    <ProximitySensor DEF='CamSense' size='1000000 1000000 1000000'/>\n    <ProximitySensor DEF='ShellSense' size='%s %s %s'/>\n" % (
                 v3(w['pos']), rot4(look_at(w['pos'], w['tgt'])), fmt(w['fov']), fmt(2 * R), fmt(2 * R), fmt(2 * R)))
    # stand-in geometry
    o.append("    <!-- Stand-in hypersphere (the real one is the scene generator's): core, glass shell, year rings, sector meridians, fibers, links, marriages. -->\n")
    t_, n_ = trimesh('Core', 3, CORE_R, "<Material emissiveColor='1 0.92 0.78' diffuseColor='0 0 0'/>"); o.append(t_); tri += n_
    t_, n_ = trimesh('CoreHalo', 2, 1.0, "<Material emissiveColor='1 0.66 0.32' diffuseColor='0 0 0' transparency='0.72'/>"); o.append(t_); tri += n_
    t_, n_ = trimesh('CoreHalo2', 2, 1.6, "<Material emissiveColor='0.9 0.45 0.25' diffuseColor='0 0 0' transparency='0.93'/>"); o.append(t_); tri += n_
    t_, n_ = trimesh('Shell', 4, R, "<Material emissiveColor='0.2 0.2 0.42' diffuseColor='0 0 0' transparency='0.92'/>"); o.append(t_); tri += n_
    rings = []
    y = (L['y0'] // 50 + 1) * 50
    while y < L['asof']:
        rad = r(y); pts = [sph(2 * math.pi * i / 128, 0.0, rad) for i in range(129)]; rings.append((pts, [(0.32, 0.3, 0.5)] * len(pts))); y += 50
    pts = [sph(2 * math.pi * i / 160, 0.0, R) for i in range(161)]; rings.append((pts, [(0.5, 0.48, 0.75)] * len(pts)))
    for k in L['keys']:
        sc = L['sectors'][k]; b = sc['phi'] - sc['span'] / 2 - math.radians(2.0)
        pts = [sph(b, -math.pi / 2 + math.pi * i / 48, R) for i in range(49)]; rings.append((pts, [(0.36, 0.34, 0.58)] * len(pts)))
    t_, n_ = lineset('ScaleLines', rings, None, 1.0); o.append(t_); seg += n_
    fl = []
    for pid in sorted(P, key=lambda i: (P[i]['born'], i)):
        f = L['fibers'][pid]; c = colour(P[pid])
        fl.append(([f['a'], f['b']], [c, mul(c, 0.45 if f['end_estimated'] else 0.9)]))
    t_, n_ = lineset('Fibers', fl, None, 2.0); o.append(t_); seg += n_
    lk = []
    for par, ch, rad in L['links']:
        a = arc(L['dirs'][par], L['dirs'][ch], rad)
        if len(a) >= 2 and length(sub(a[0], a[-1])) > 1e-4: c = mul(colour(P[ch]), 0.55); lk.append((a, [c] * len(a)))
    t_, n_ = lineset('Lineage', lk, None, 1.2); o.append(t_); seg += n_
    mg = []
    for u in sorted(L['known_unions'], key=lambda u: (u['year'], u['id'])):
        a = arc(L['dirs'][u['a']], L['dirs'][u['b']], r(u['year']))
        if len(a) >= 2 and length(sub(a[0], a[-1])) > 1e-4:
            c = (1.0, 0.82, 0.35) if not u.get('close') else (1.0, 0.55, 0.3); mg.append((a, [mul(c, CONF_V.get(u.get('confidence'), 0.8))] * len(a)))
    t_, n_ = lineset('Marriages', mg, None, 2.2); o.append(t_); seg += n_
    ids = sorted(P, key=lambda i: (P[i]['born'], i))
    o.append("    <Shape DEF='Beads'>\n      <Appearance><Material emissiveColor='1 1 1' diffuseColor='0 0 0'/><PointProperties pointSizeScaleFactor='4' pointSizeMinValue='2' pointSizeMaxValue='8'/></Appearance>\n"
             "      <PointSet>\n        <Coordinate point='%s'/>\n        <Color color='%s'/>\n      </PointSet>\n    </Shape>\n" % (
                 ', '.join(v3(L['fibers'][i]['a']) for i in ids), ', '.join(v3(add(mul(colour(P[i]), 0.8), (0.2, 0.2, 0.2))) for i in ids)))
    for key, who in (('present', pp), ('eye', pe)):
        a = L['fibers'][who['id']]['a']
        t_, n_ = trimesh('PickBead_' + key, 1, 0.14, "<Material emissiveColor='1 0.95 0.8' diffuseColor='0 0 0'/>", center=a, ind='      ')
        o.append("    <Group DEF='Pick_%s'>\n      <TouchSensor DEF='PickTouch_%s' description='%s'/>\n%s    </Group>\n" % (key, key, xa(who['name']), t_)); tri += n_
    exports = ['Probe', 'ProbeFrame', 'CamSense', 'ShellSense', 'Nav', 'NavFly', 'Wide', 'Crown', 'Colossus', 'EyeToEye', 'Frame_EyeToEye', 'Present', 'Frame_Present',
               'Inside', 'Flywheel', 'FlywheelRig', 'FlywheelClock', 'PickTouch_present', 'PickTouch_eye'] + ['House_' + k for k in L['keys']]
    o += ["    <EXPORT localDEF='%s'/>\n" % e for e in exports]
    o.append("  </Scene>\n</X3D>\n")
    with open(path, 'w', encoding='utf-8') as fh: fh.write(''.join(o))
    return exports, tri, seg


def write_host(fam, shots, exports, pocket_file, path):
    s = shots['Host']; ori = look_at(s['pos'], s['tgt'])
    o = [HEAD, "  <head>\n    <component name='Shape' level='5'/>\n    <meta name='title' content='%s'/>\n" % os.path.basename(path),
         "    <meta name='description' content='Host space for the hypersphere camera proof (%s): the opening viewpoint, a stand-in host, the pocket pages&apos; camera rig as a control, and the pocket Inlined at scale %s with IMPORTs. Generated; do not edit.'/>\n" % (xa(fam['name']), fmt(POCKET_SCALE)),
         "    <meta name='generator' content='proto/hyper/tools/build_camera_proof.py'/>\n  </head>\n  <Scene>\n",
         "    <WorldInfo title='Hypersphere camera proof (host): %s'/>\n" % xa(fam['name']),
         "    <NavigationInfo DEF='HostNav' type='\"EXAMINE\" \"ANY\"' headlight='false' speed='4' transitionType='\"ANIMATE\"' transitionTime='1.6'/>\n",
         "    <Background DEF='HostSky' skyColor='0.012 0.01 0.03'/>\n",
         "    <Viewpoint DEF='Host' description='Opening: the pocket in its host' position='%s' orientation='%s' centerOfRotation='0 0 0' fieldOfView='%s'/>\n" % (v3(s['pos']), rot4(ori), fmt(s['fov'])),
         "    <!-- Control: the pocket pages' camera rig verbatim (a Transform the page moves; its Viewpoint's centerOfRotation is rig-local). -->\n",
         "    <Transform DEF='PocketRig' translation='0 3 26'>\n      <Viewpoint DEF='RigView' description='Pocket-page rig (control)' position='0 0 0' centerOfRotation='0 -3 -26' fieldOfView='0.9'/>\n    </Transform>\n"]
    # host stand-in: two floor rings, a deterministic star field, two sibling pockets (the same appearance, USE)
    st = []; seed = 1234567
    for i in range(420):
        seed = (seed * 1103515245 + 12345) % 2147483648; u = seed / 2147483648.0
        seed = (seed * 1103515245 + 12345) % 2147483648; v = seed / 2147483648.0
        seed = (seed * 1103515245 + 12345) % 2147483648; w = seed / 2147483648.0
        st.append(sph(2 * math.pi * u, math.asin(2 * v - 1), 90 + 60 * w))
    o.append("    <Shape DEF='HostStars'>\n      <Appearance><Material emissiveColor='0.85 0.82 0.95' diffuseColor='0 0 0'/><PointProperties pointSizeScaleFactor='2' pointSizeMinValue='1' pointSizeMaxValue='3'/></Appearance>\n"
             "      <PointSet><Coordinate point='%s'/></PointSet>\n    </Shape>\n" % ', '.join(v3(p) for p in st))
    rings = []
    for rr in (14.0, 22.0, 32.0):
        pts = [(rr * math.sin(2 * math.pi * i / 128), -9.0, rr * math.cos(2 * math.pi * i / 128)) for i in range(129)]; rings.append((pts, [(0.22, 0.2, 0.36)] * len(pts)))
    t_, n_ = lineset('HostFloor', rings, None, 1.0); o.append(t_)
    t_, n_ = trimesh('Sibling1', 2, 1.0, "<Material DEF='SiblingMat' emissiveColor='0.42 0.26 0.62' diffuseColor='0 0 0' transparency='0.35'/>", center=(-24.0, 6.0, -14.0)); o.append(t_)
    t_, n_ = trimesh('Sibling2', 2, 0.7, "<Material USE='SiblingMat'/>", center=(22.0, -5.0, -18.0)); o.append(t_)
    o.append("    <!-- The pocket: one unit inside = %s host units. Its sensors report in pocket units; the page drives its Probe through the IMPORTs. -->\n" % fmt(POCKET_SCALE))
    o.append("    <Transform DEF='PocketXf' scale='%s %s %s'>\n      <Inline DEF='Pocket' url='\"%s\"'/>\n    </Transform>\n" % (fmt(POCKET_SCALE), fmt(POCKET_SCALE), fmt(POCKET_SCALE), pocket_file))
    o += ["    <IMPORT inlineDEF='Pocket' importedDEF='%s' AS='%s'/>\n" % (e, e) for e in exports]
    o.append("  </Scene>\n</X3D>\n")
    with open(path, 'w', encoding='utf-8') as fh: fh.write(''.join(o))
    return 2 * 320


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f: h.update(f.read())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(PROTO, 'data', 'loom-view.json'))
    ap.add_argument('--out', default=os.path.join(PROTO, 'hyper', 'proof'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = json.load(open(a.data, encoding='utf-8'))
    outs, summary = [], {}
    for fam in data['families']:
        if fam['key'] not in FAMILIES: continue
        L = build_family(fam, data['asof'])
        shots, pe, pp, big, why = make_shots(fam, L)
        stops, checks, reads = make_tour(fam, L, shots, pe, pp, big, why)
        pocket = 'hyper-%s.x3d' % fam['key']; host = 'camera.x3d' if fam['key'] == 'rothschild' else 'camera-%s.x3d' % fam['key']
        exports, tri, seg = write_pocket(fam, L, shots, pe, pp, os.path.join(a.out, pocket))
        htri = write_host(fam, shots, exports, pocket, os.path.join(a.out, host))
        sec = {k: dict(name=v['name'], phi_deg=round(math.degrees(v['phi']), 2), span_deg=round(math.degrees(v['span']), 2), people=v['people']) for k, v in L['sectors'].items()}
        doc = dict(version='hyper-camera/1', family=fam['key'], name=fam['name'], host=host, pocket=pocket, pocket_scale=POCKET_SCALE, R=R, timing=TIMING,
                   scale=dict(radius='r(year) = %g * (year - %d) / (%d - %d); 1 unit = %.1f years' % (R, L['y0'], L['asof'], L['y0'], L['span'] / R),
                              azimuth='houses west to east by longitude, founders’ house (%s) at azimuth 0 (+Z), sector angle = 2 + people, 4 degree gaps' % L['sectors'][L['fh']]['name'],
                              y0=L['y0'], asof=L['asof'], years_per_unit=round(L['span'] / R, 2)),
                   sectors=sec, order_west_to_east=L['keys'], shots=shots, tour=stops, chain_checks=checks, read_checks=reads,
                   picked=dict(eye=pe['id'], eye_name=pe['name'], present=pp['id'], present_name=pp['name'], colossus_house=big),
                   counts=dict(people=len(L['P']), unions=len(fam['unions']), unions_drawn=len(L['known_unions']), fibers_end_estimated=sum(1 for f in L['fibers'].values() if f['end_estimated']),
                               triangles_pocket=tri, triangles_host=htri, line_segments_pocket=seg),
                   exports=exports)
        sp = os.path.join(a.out, 'shots-%s.json' % fam['key'])
        with open(sp, 'w', encoding='utf-8') as fh: json.dump(doc, fh, indent=1, ensure_ascii=False)
        outs += [pocket, host, os.path.basename(sp)]
        summary[fam['key']] = dict(chain_ok=all(c['ok'] for c in checks), reads_ok=all(x['ok'] for x in reads), eye=pe['name'], eye_year=shots['EyeToEye']['year'],
                                   present=pp['name'], colossus=big, triangles=tri, segments=seg)
    ins = {os.path.relpath(a.data, PROTO): sha(a.data), 'hyper/tools/build_camera_proof.py': sha(os.path.abspath(__file__))}
    rec = dict(by='proto/hyper/tools/build_camera_proof.py', python=sys.version.split()[0], inputs=ins, outputs={o_: sha(os.path.join(a.out, o_)) for o_ in outs}, summary=summary)
    with open(os.path.join(a.out, 'receipt-build.json'), 'w', encoding='utf-8') as fh: json.dump(rec, fh, indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
