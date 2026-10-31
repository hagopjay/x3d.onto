#!/usr/bin/env python3
"""build_hypersphere.py: the dynasty hypersphere on the real data. Deterministic; standard library only.

    python3 -I build_hypersphere.py [--view PATH] [--cards DIR] [--out DIR] [--theme SLUG] [--portraits PATH] [--root-rel PREFIX]

v2: --theme picks a look from hyper/themes.py (DEFAULT_THEME without it): dye tones, line widths, glow tints, backgrounds and the GLSL constants
(themes.style_block, spliced into common.glsl at //#include style). --portraits names the release's portraits.json (tools/build_portraits.py):
close tour stops whose subject has an entry get camera-facing portrait plates, faded and drifted by X3D interpolators; --root-rel is the path
from this output's scenes back to the release root (the alternate theme's scenes sit two folders down, under theme/<slug>/).

Inputs (read only):
  proto/merged/loom-view.json            the data (contract proto/contracts/loom-view.md); possibly-living people are already withheld
  proto/scene2/out/<family>.cards.json   the tapestry generator's solved view of the same data: houses, moves (pieces), dye colours by share,
                                         estimated union years (fill_union_years), the person cards and the stops with graded narration.
                                         The hypersphere reuses these solutions instead of re-deriving them; every person and union in the
                                         cards is checked against loom-view.json before anything is drawn.
  proto/hyper/src/*.glsl                 the lookdev shaders (look bible), adapted: pick, per-family time scale, shells every 50 years
  proto/hyper/page/index.html            the page (a fragment: the Artifact host wraps it in its own skeleton)
  proto/x3d/vendor/x_ite                 X_ITE 16.5.1, byte-identical to the npm tarball

Writes into out/ (never edit these by hand; change this file, src/ or page/ and rebuild):
  pocket-<family>.x3d     the pocket world in its own units (standard X3D 4.0, Immersive + Shaders): founders' seed, glass shell with time
                          shells, one ribbon fiber per life, spawn arcs, move bends, marriage arcs; every shot of the camera grammar as a
                          Viewpoint (rolled shots inside an up frame), the Probe rig, the camera sensors, the Flywheel orbit, EXPORTs.
                          Inline it anywhere (the Gobbler host) and IMPORT what you need.
  hyper-<family>.x3d      the host the page opens: nebula sky, armillary, lights, the Host viewpoint, and the pocket Inlined at scale 6.
  <family>.hyper.json     the page's data: units and the stated mapping, sectors, shots, the tour (one shot per card stop), chain checks,
                          label anchors, per-person pick polylines and Present shots.
  <family>.geometry.json  every fiber and arc polyline with its colour, kind and years (for a Cycles hero still)
  <family>.cards.json     copied from scene2/out (the card text the page shows)
  hyper-manifest.json, index.html, x_ite/..., publish.json, receipt.json (sha256 of every input and output)

Mapping (stated on screen and in the receipt):
  radius = time, to scale: r(year) = R0 + (year - Y0) * K pocket units; Y0 is the family's first quarter-century (the tapestry's Y0), the
  tapestry's top year sits at R_TOP just inside the glass (R_GLASS); time shells every 50 years.
  direction = layout: houses take azimuth sectors west to east by longitude, angle proportional to 2 + people, 4 degree gaps, the eldest
  founder's house at azimuth 0 (+Z); inside a house people are ordered by descent (depth first, children by birth, an in-law right after
  their spouse) and spread in elevation in that order (siblings and cousins sit together), azimuth jittered by the golden ratio.
"""
import argparse, base64, hashlib, importlib.util, json, math, os, re, shutil, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))                        # proto/hyper
PROTO = os.path.dirname(HERE)
SRC, PAGE = os.path.join(HERE, 'src'), os.path.join(HERE, 'page', 'index.html')
VENDOR = os.path.join(PROTO, 'x3d', 'vendor', 'x_ite')
# NAV HOOK (README, "v5 (Artifact version 5)"): the lens library, loaded by path (python3 -I puts no script directory on sys.path)
LENS_LIB = os.environ.get('LENS_LIB', os.path.abspath(os.path.join(HERE, 'nav', 'lens_glsl.py')))
sys.dont_write_bytecode = True   # no __pycache__ beside the library
_spec = importlib.util.spec_from_file_location('lens_glsl', LENS_LIB); LENSG = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(LENSG)
NAV_LIB = os.path.dirname(LENS_LIB)   # orbit.js and lens.js ship beside the page as lib/*.js
VERSION = 'nav (orbit camera + hyperbolic lens) on build_hypersphere.py 2.0'
sys.path.insert(0, HERE)
import themes as TH   # noqa: E402  (v2: the look table)


def _arg(k, d):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d


THEME = TH.theme(_arg('--theme', TH.DEFAULT_THEME))   # read before the constants below, which take the theme's values
FAMILIES = ['rothschild', 'habsburg', 'darwin_wedgwood']
XITE_SRI = 'sha384-/U1JwiaA22Ilp0Ju84O+ud9jJvfpVM3sasBhBHoAY4wQXGMc2d82QmdIZYhC1a4g'   # the npm 16.5.1 dist/x_ite.min.js (the page pins it)

# ---- units (pocket units unless said otherwise)
R0, R_TOP = 0.08, 1.04                     # r(Y0) and r(top): the family's time runs from just outside the seed to just inside the glass
R_GLASS, R_PROXY = 1.10, 1.20              # the analytic glass sphere and its proxy mesh
SCALE = 6.0                                # pocket -> host (the host Inlines the pocket at this scale)
G = R_GLASS / 10.0                         # camera grammar units (present shell = 10) -> pocket units
GAP = math.radians(4.0)                    # gap between house sectors
LAT_MAX = 0.80                             # elevation band: asin(...) * 0.80, so nothing sits on the poles
ARC_STEP = 0.035                           # radians between samples along an arc (v3); NAV HOOK densify: arc_pts takes LENSG.arc_step(rad, R_GLASS)
RAD_STEP = 0.012                           # pocket units between samples along a fiber (pulses and the time cut need vertices)
CLOSE_DR = 0.0045                          # a close marriage is doubled: two arcs this far apart in radius
CORE_W = THEME['core_w']                            # ribbon half-widths (pocket units): hot core, soft glow by tier
GLOW_W_TIER = dict(THEME['glow_w'])   # v3: fast 0.013, balanced 0.018, ultra 0.02
CORE_MIN_PX, GLOW_MIN_PX, CORE_MAX_PX, GLOW_MAX_PX = THEME['core_px'][0], THEME['glow_px'][0], THEME['core_px'][1], THEME['glow_px'][1]   # v3: 0.65, 2.5, 4.0, 14.0
SEED_R, SEED_GLOW_R = 0.012, 0.24
BEAD_R, BEAD_RING = 0.02, 0.7              # the subject bead's proxy (pocket units) and its marriage ring (share of the proxy radius)
LINE_CAP = 32                              # people in a stop's lineage list (uLine[32] in fiber.vert)
DASH_ARC = 0.028                           # pocket units per dash period along an estimated arc (fiber.frag)
# point glows (seed.frag) in units of the proxy radius: e2 and s2 are the halo's softening and the core's Gaussian width (squared), halo and
# core the gains; in pocket units scale them by R^2, R^2, R^-3 and R (the integrals' units). The critique's seed numbers (e2 0.0008, s2 0.00035,
# halo 0.002, core 1.5, pocket units) still flooded the plunge's landing: modelled at the Inside camera (r 0.293) the halo stays over 1 out to
# 0.1 pocket units and the glow alone averages luma 0.455 (Confirmed: work/r1/probe, scene mean 0.77, 29 percent clipped). These keep it to a
# tight bloom: modelled glow mean 0.056 (python model in the build-2 notes; frames decide).
SEED_GLOW = dict(e2=0.00008 / SEED_GLOW_R ** 2, s2=0.00005 / SEED_GLOW_R ** 2, halo=0.000004 / SEED_GLOW_R ** 3, core=0.8 * SEED_GLOW_R, period=4,
                 halo_tint=THEME['seed_glow']['halo_tint'], core_tint=THEME['seed_glow']['core_tint'], exposure=THEME['seed_glow']['exposure'], knee=0.004, z=0.06)
BEAD_GLOW = dict(e2=0.002, s2=0.005, halo=0.0011, core=20.0, period=2, halo_tint=THEME['bead_glow']['halo_tint'], core_tint=THEME['bead_glow']['core_tint'], exposure=THEME['bead_glow']['exposure'], knee=0.002, z=-0.12)
LIFT = 0.16                                # caption lift (share of the half-height); see lifted()
HALO_CLEAR = 0.32                          # close shots keep the camera at least this far from the centre (outside the core glow)
ASPECT = 1527 / 923                        # design viewport (X_ITE: fieldOfView spans the smaller side)
Y = (0.0, 1.0, 0.0)
TIMING = {'base': 2.2, 'per_S': 0.55, 'per_rad': 0.9, 'min': 3.5, 'max': 7.5}   # flight s = base + per_S * van Wijk length + per_rad * turn
RINGS = [{'def': 'RingA', 'R': 6.95, 'r': 0.022, 'rot': [1, 0, 0.25, 0.32]}, {'def': 'RingB', 'R': 7.75, 'r': 0.03, 'rot': [0.2, 0, 1, 1.05]},
         {'def': 'RingC', 'R': 8.35, 'r': 0.02, 'rot': [1, 0.3, 0, -0.62]}]                       # armillary (host units), from the lookdev
GRADE_RANK = {'Suspected': 0, 'Likely': 1, 'Confirmed': 2}
# close-shot compositions (build 3, critique rank 3: every Present had the fiber vertical at screen centre, the bead at the bottom, the label
# beside it; the close shots read as one template). A tour cycles them per shot type, so two neighbouring close shots never share a framing.
# el: camera elevation above (+, from the later years) or below (-, from the seed side) the framed stretch; side: which side of the house
# plane; third: where the subject's fiber sits (-1 left third, +1 right third, 0 centre); roll: a dutch tilt (degrees, about the view axis);
# fill: the framed stretch's share of the frame height.
PRESENT_VARIANTS = [dict(name='descent', el=32.0, side=1.0, third=1.0, roll=-5.0, fov=0.68, fill=0.52),     # high: down the years toward the seed
                    dict(name='rise', el=-24.0, side=-1.0, third=-1.0, roll=7.0, fov=0.78, fill=0.5),       # low, other side: up the years
                    dict(name='diagonal', el=20.0, side=1.0, third=0.0, roll=27.0, fov=0.62, fill=0.68)]    # the life on a diagonal, from a little above, longer lens
EYE_VARIANTS = [dict(name='level', side=1.0, el=0.0, roll=0.0),                                            # eye to eye, the arc runs right
                dict(name='over', side=-1.0, el=26.0, roll=-6.0)]                                          # from the other side, above the shell
CAM_MAX_R = R_GLASS - 0.07                 # close shots keep the camera inside the glass (the inside look and its haze)
PEWTER = tuple(round(x, 3) for x in TH._rgb(THEME['ring']))                # the armillary (build 3, critique rank 2): the dye owns gold, so the host frame is pewter in every family


# ---------------------------------------------------------------- vectors
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
def hshot(k): return 'House_' + re.sub(r'[^A-Za-z0-9_]', '_', k)     # a house's shot DEF (X3D naming: no '-')
def sph(phi, lat, r=1.0): return (r * math.sin(phi) * math.cos(lat), r * math.sin(lat), r * math.cos(phi) * math.cos(lat))


def slerp(a, b, t):
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
    z = norm(sub(pos, tgt)); x = norm(cross(up, z))
    if length(x) < 1e-9: x = norm(cross((0.0, 0.0, 1.0) if abs(z[1]) > 0.9 else Y, z))
    return quat_to_aa(quat_from_basis(x, cross(z, x), z))


def frame_to(u):
    u = norm(u); c = clamp(dot(Y, u), -1.0, 1.0)
    if c > 1 - 1e-12: return (0.0, 0.0, 1.0, 0.0)
    if c < -1 + 1e-12: return (1.0, 0.0, 0.0, math.pi)
    return tuple(norm(cross(Y, u))) + (math.acos(c),)


def rotate(v, aa):
    ax = norm(aa[:3]); a = aa[3]; c, s = math.cos(a), math.sin(a)
    return add(add(mul(v, c), mul(cross(ax, v), s)), mul(ax, dot(ax, v) * (1 - c)))


def wijk_S(u1, w0, w1):
    rho2, rho4 = 2.0, 4.0; rho = math.sqrt(2)
    if u1 < 1e-7 * max(w0, w1): return abs(math.log(w1 / w0)) / rho
    b0 = (w1 * w1 - w0 * w0 + rho4 * u1 * u1) / (2 * w0 * rho2 * u1); b1 = (w1 * w1 - w0 * w0 - rho4 * u1 * u1) / (2 * w1 * rho2 * u1)
    return (math.log(math.sqrt(b1 * b1 + 1) - b1) - math.log(math.sqrt(b0 * b0 + 1) - b0)) / rho


# ---------------------------------------------------------------- text helpers
def fnum(x, nd=4):
    # build 2: strip trailing zeros only after a decimal point. Build 1 stripped them from integers too (nd=0), so person index 90 was
    # written as 9 in aAux and a pick or a close shot of person 10, 20, ... 100 lit person 1, 2, ... 10 (Confirmed: pocket-habsburg.x3d had no
    # vertex with index 90, Leopold I).
    s = '%.*f' % (nd, x)
    if '.' in s: s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '', '-') else s


def v3(v, nd=4): return ' '.join(fnum(x, nd) for x in v)
def flat(rows, nd): return ' '.join(fnum(x, nd) for r in rows for x in r)
def esc(s): return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;').replace('"', '&quot;')
def r5(v): return [round(x, 5) for x in v]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''): h.update(blk)
    return h.hexdigest()


def glsl(name):
    src = open(os.path.join(SRC, name), encoding='utf-8').read()
    for chunk in ('common', 'sky'):
        src = src.replace('//#include %s\n' % chunk, open(os.path.join(SRC, chunk + '.glsl'), encoding='utf-8').read())
    src = src.replace('//#include style\n', TH.style_block(THEME))   # v2: the theme's look constants (hyper/themes.py)
    if ']]>' in src: raise SystemExit('GLSL may not contain ]]> (CDATA)')
    if '%' in src: raise SystemExit('GLSL in a data: URL may not contain %% (%s): X_ITE runs decodeURIComponent on it' % name)
    return src


def part(defn, typ, name):
    # X_ITE 16.5.1 reads a ShaderPart's CDATA as its url; raw GLSL there is fetched as a relative URL. The data: prefix makes X_ITE decode it
    # in place (no request, nothing for connect-src to refuse); the look bible's CSP finding.
    mime = 'x-shader/x-vertex' if typ == 'VERTEX' else 'x-shader/x-fragment'
    return "<ShaderPart DEF='%s' type='%s'><![CDATA[data:%s,%s]]></ShaderPart>" % (defn, typ, mime, LENSG.patch(defn, name, glsl(name), R_GLASS))   # NAV HOOK: the lens (and logDepth where the shader has none)


def fields(spec, ind):
    return ''.join("\n%s<field name='%s' type='%s' accessType='inputOutput' value='%s'/>" % (ind, n, t, v) for n, t, v in spec)


def icosphere(sub_n, radius):
    t = (1 + 5 ** 0.5) / 2
    v = [norm(p) for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(sub_n):
        cache, nf = {}, []
        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache: cache[key] = len(v); v.append(norm(add(v[i], v[j])))
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a); nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return [mul(p, radius) for p in v], list(v), f


def torus(R, r, M=144, N=10):
    pts, nrm, idx = [], [], []
    for i in range(M):
        u = 2 * math.pi * i / M; cu, su = math.cos(u), math.sin(u)
        for j in range(N):
            w = 2 * math.pi * j / N; cw, sw = math.cos(w), math.sin(w)
            nrm.append((cw * cu, sw, cw * su)); pts.append(((R + r * cw) * cu, r * sw, (R + r * cw) * su))
    for i in range(M):
        for j in range(N):
            a, b = i * N + j, ((i + 1) % M) * N + j
            c, d = ((i + 1) % M) * N + (j + 1) % N, i * N + (j + 1) % N
            idx += [a, d, b, b, d, c]
    return pts, nrm, idx


# ---------------------------------------------------------------- data: the cards, checked against loom-view.json
def load(view_path, cards_dir):
    view = json.load(open(view_path, encoding='utf-8'))
    fams = {}
    for F in view['families']:
        if F['key'] not in FAMILIES: continue
        C = json.load(open(os.path.join(cards_dir, F['key'] + '.cards.json'), encoding='utf-8'))
        vp = {p['id']: p for p in F['people']}
        if set(vp) != set(C['people']): raise SystemExit('%s: cards people differ from loom-view.json' % F['key'])
        for pid, p in C['people'].items():
            q = vp[pid]
            for k in ('born', 'died', 'house', 'father', 'mother', 'core'):
                if q.get(k) != p.get(k): raise SystemExit('%s/%s: %s differs (view %r, cards %r)' % (F['key'], pid, k, q.get(k), p.get(k)))
        vu = {u['id']: u for u in F['unions']}
        if set(vu) != set(C['unions']): raise SystemExit('%s: cards unions differ from loom-view.json' % F['key'])
        for uid, u in C['unions'].items():
            q = vu[uid]
            if q.get('year') is not None and q['year'] != u['year']: raise SystemExit('%s: union %s year differs' % (F['key'], uid))
            if q.get('year') is None and u.get('year_precision') != 'unknown': raise SystemExit('%s: union %s has no year in the data but is not marked unknown' % (F['key'], uid))
        fams[F['key']] = (F, C)
    return view, fams


def last_known(p, P, U):
    ys = [p['born']] + [P[c]['born'] for c in p['children'] if c in P] + [U[u]['year'] for u in p['unions'] if u in U and U[u]['year_precision'] in ('year', 'day', 'month')]
    return max(ys)


# ---------------------------------------------------------------- layout
def layout(F, C):
    P, U = C['people'], C['unions']
    Y0, TOP = C['layout']['Y0'], C['layout']['top']
    K = (R_TOP - R0) / (TOP - Y0)
    def r(y): return R0 + (y - Y0) * K
    founders = [i for d in C['dyes'].values() for i in d['founders'] if i in P]
    f0 = min(founders, key=lambda i: (P[i]['born'], i))
    kids = defaultdict(list)
    for pid in sorted(P, key=lambda i: (P[i]['born'], i)):
        for k in ('father', 'mother'):
            if P[pid].get(k) in P: kids[P[pid][k]].append(pid)
    spouses = defaultdict(list)
    for uid in sorted(U, key=lambda u: (U[u]['year'], u)):
        u = U[uid]; spouses[u['a']].append(u['b']); spouses[u['b']].append(u['a'])
    def inlaw(pid): return not P[pid]['core'] and P[pid].get('father') not in P and P[pid].get('mother') not in P
    # houses: sectors west to east by longitude (ties: opened, key); angle proportional to 2 + people who have a piece there
    members = defaultdict(set)
    for pid, p in P.items():
        for pc in p['pieces']: members[pc[0]].add(pid)
    hs = sorted(C['houses'], key=lambda h: (h['lon'], h.get('opened') or 0, h['key']))
    keys = [h['key'] for h in hs]
    wts = [2 + len(members[k]) for k in keys]; avail = 2 * math.pi - GAP * len(keys)
    spans = [avail * w / sum(wts) for w in wts]; cents = []; a = 0.0
    for s in spans: cents.append(a + GAP / 2 + s / 2); a += s + GAP
    fh = P[f0]['pieces'][0][0]; shift = cents[keys.index(fh)]; cents = [c - shift for c in cents]
    sectors = {k: {'key': k, 'name': h['name'], 'phi': cents[i], 'span': spans[i], 'people': len(members[k]), 'lon': h['lon'],
                   'opened': h.get('opened'), 'closed': h.get('closed')} for i, (k, h) in enumerate(zip(keys, hs))}
    # slots: inside a house, depth-first descent order (children by birth, an in-law right after their spouse), elevation in that order
    slot = {}
    for hi, k in enumerate(keys):
        ids = members[k]; seq, seen = [], set()
        def dfs(pid):
            if pid in seen: return
            seen.add(pid); seq.append(pid)
            for s in spouses[pid]:
                if s in ids and s not in seen and inlaw(s): seen.add(s); seq.append(s)
            for c in kids[pid]:
                if c in ids: dfs(c)
        roots = sorted([i for i in ids if not any(P[i].get(f) in ids for f in ('father', 'mother')) and not (inlaw(i) and any(s in ids for s in spouses[i]))],
                       key=lambda i: (P[i]['born'], i))
        for rt in roots: dfs(rt)
        for i in sorted(ids - seen, key=lambda i: (P[i]['born'], i)): dfs(i)
        n = len(seq)
        for i, pid in enumerate(seq):
            lat = math.asin(clamp(1 - 2 * (i + 0.5) / n, -1, 1)) * LAT_MAX
            jit = ((i + 1) * 0.6180339887498949) % 1.0 - 0.5
            slot[(pid, k)] = sph(cents[hi] + jit * spans[hi] * 0.72, lat, 1.0)
    order = sorted(P, key=lambda i: (P[i]['born'], i)); index = {pid: i for i, pid in enumerate(order)}
    def dir_at(pid, y):
        pcs = P[pid]['pieces']
        for pc in pcs:
            if pc[3] - 1e-6 <= y <= pc[4] + 1e-6: return slot[(pid, pc[0])]
        pc = min(pcs, key=lambda pc: min(abs(y - pc[3]), abs(y - pc[4])))
        return slot[(pid, pc[0])]
    dye = {pid: dye_rgb(P[pid].get('shares'), C['dyes'])[0] for pid in P}
    return dict(P=P, U=U, Y0=Y0, TOP=TOP, K=K, r=r, dye=dye, founders=founders, f0=f0, fh=fh, kids=kids, spouses=spouses, sectors=sectors, keys=keys,
                slot=slot, dir_at=dir_at, order=order, index=index, inlaw=inlaw, shell0=(Y0 // 50 + 1) * 50)


# ---------------------------------------------------------------- geometry: polylines, then camera-facing ribbons
def arc_pts(d1, d2, rad):
    a = math.acos(clamp(dot(norm(d1), norm(d2)), -1, 1)); n = max(2, int(math.ceil(a / LENSG.arc_step(rad, R_GLASS, ARC_STEP))) + 1)   # NAV HOOK densify
    return [mul(slerp(d1, d2, i / (n - 1)), rad) for i in range(n)]


def radial_years(y0, y1, K):
    n = max(1, int(math.ceil((y1 - y0) * K / RAD_STEP)))
    return [y0 + (y1 - y0) * i / n for i in range(n + 1)]


def polylines(L):
    P, U, r, K, idx = L['P'], L['U'], L['r'], L['K'], L['index']
    out = []
    def col(pid): return L['dye'][pid]
    for pid in L['order']:
        p = P[pid]; pcs = p['pieces']; born, end = pcs[0][3], pcs[-1][4]
        lk = last_known(p, P, U) if p['died'] is None else None
        mv_est = bool(p.get('move') and p['move'].get('estimated'))
        # a founder's root: from the seed's edge to the birth point, layout only
        if pid in L['founders'] and P[pid].get('father') not in P and P[pid].get('mother') not in P and born > L['Y0']:
            d = L['slot'][(pid, pcs[0][0])]; ys = radial_years(L['Y0'], born, K)
            out.append(dict(kind='root', ids=[pid], color=col(pid), pts=[mul(d, r(y)) for y in ys], years=ys, est=[0] * len(ys), kinds=[1] * len(ys)))
        # spawn arc: on the birth shell, from the parent's fiber to the child's
        par = [x for x in (p.get('father'), p.get('mother')) if x in P]
        if par:
            par.sort(key=lambda x: (0 if P[x]['core'] else 1, x))
            a, b = L['dir_at'](par[0], born), L['slot'][(pid, pcs[0][0])]
            if math.acos(clamp(dot(a, b), -1, 1)) > 1e-3:
                pts = arc_pts(a, b, r(born))
                out.append(dict(kind='spawn', ids=[pid, par[0]], color=col(pid), pts=pts, years=[born] * len(pts), est=[0] * len(pts), kinds=[1] * len(pts)))
        # the life: radial runs per piece, bent along the shell of each move year
        pts, years, est, kinds = [], [], [], []
        for j, pc in enumerate(pcs):
            d = L['slot'][(pid, pc[0])]
            if j > 0:
                prev = L['slot'][(pid, pcs[j - 1][0])]
                for q in arc_pts(prev, d, r(pc[3]))[1:-1]:
                    pts.append(q); years.append(pc[3]); est.append(1 if mv_est else 0); kinds.append(1)
            for y in radial_years(pc[3], pc[4], K):
                if pts and years[-1] == y and kinds[-1] == 0: continue
                e = 0
                if p.get('born_precision') == 'circa' and y < born + 10: e = 1
                if p.get('died') is None and y > lk: e = 1
                if p.get('died_precision') == 'circa' and y > end - 10: e = 1
                pts.append(mul(d, r(y))); years.append(y); est.append(e); kinds.append(0)
        out.append(dict(kind='life', ids=[pid], color=col(pid), pts=pts, years=years, est=est, kinds=kinds, born=born, end=end,
                        end_rule=None if p['died'] is not None else 'death not in the data: drawn dashed after the last dated event (%d) to %d, the tapestry\'s 60-year rule' % (lk, end)))
    for uid in sorted(U, key=lambda u: (U[u]['year'], u)):
        u = U[uid]; y = u['year']; a, b = L['dir_at'](u['a'], y), L['dir_at'](u['b'], y)
        sa = sum(float(eval_frac(v)) for v in P[u['a']]['shares'].values()); sb = sum(float(eval_frac(v)) for v in P[u['b']]['shares'].values())
        c = col(u['a']) if sa >= sb else col(u['b'])
        e = 0 if u['year_precision'] in ('year', 'day', 'month') else 1
        rads = [r(y) - CLOSE_DR, r(y) + CLOSE_DR] if u['close'] else [r(y)]
        for rad in rads:
            pts = arc_pts(a, b, rad)
            out.append(dict(kind='close' if u['close'] else 'union', ids=[u['a'], u['b']], uid=uid, color=c, pts=pts, years=[y] * len(pts), est=[e] * len(pts),
                            kinds=[3 if u['close'] else 2] * len(pts)))
    return out


def eval_frac(s):
    s = str(s)
    if '/' in s: n, d = s.split('/'); return int(n) / int(d)
    return float(s)


# ---------------------------------------------------------------- the dye (build 3, critique rank 2): ramp indexed by generations of descent
# The tapestry ramps the dye by LINEAR share (ecru mixed toward the dye in CIELAB), so a share below 1/16 lands on its ecru end: 43 of 106
# Habsburg lives (Philip IV 0.0034, Leopold I 0.0024) were drawn like spouses who married in. Here the step is the number of generations of
# descent, k = clamp(round(-log2(share)), 0, 4), and step k is the tapestry's colour at the equivalent share 1 - k/8: k 0 is the full dye,
# k 4 (1/16 or less) is the tapestry's '1/2' colour, the floor. Ecru is kept for share 0 only (no descent from the founders in the data).
# Same CIELAB maths and constants as proto/scene2/build_loom_scene.py (thread_color, dye_top_lab; DYE_L 54, ECRU), re-implemented here.
ECRU = tuple(round(x, 4) for x in TH._rgb(THEME['ecru']))   # v3: (0.89, 0.85, 0.76)
DYE_L = THEME['dye_l']
STYLE_INK, STYLE_CHROMA, STYLE_INK_VALUE, STYLE_ECRU_WORD, STYLE_VALUE_NORM = THEME['ink'], THEME['chroma'], THEME['ink_value'], THEME['ecru_word'], THEME.get('value_norm', 1.0)
STYLE_DYES = THEME['dyes']   # each family keeps its v3 hue family (red, gold, green, blue); only the tone is the theme's
DYE_K_MAX = 4
_WP = (0.95047, 1.0, 1.08883)
def _lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def _gam(c): c = max(0.0, min(1.0, c)); return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
def hex_rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
def hex_of(c): return '#%02x%02x%02x' % tuple(int(round(clamp(x, 0, 1) * 255)) for x in c)


def lab(rgb):
    r, g, b = [_lin(c) for c in rgb]
    xyz = (0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b, 0.0193 * r + 0.1192 * g + 0.9505 * b)
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (xyz[0] / _WP[0], xyz[1] / _WP[1], xyz[2] / _WP[2])]
    return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))


def lab_rgb(L_, a_, b_, clip=True):
    fy = (L_ + 16) / 116; fx, fz = fy + a_ / 500, fy - b_ / 200
    inv = lambda t: t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787
    X, Y_, Z = inv(fx) * _WP[0], inv(fy) * _WP[1], inv(fz) * _WP[2]
    lin = (3.2406 * X - 1.5372 * Y_ - 0.4986 * Z, -0.9689 * X + 1.8758 * Y_ + 0.0415 * Z, 0.0557 * X - 0.2040 * Y_ + 1.0570 * Z)
    return tuple(_gam(c) for c in lin) if clip else lin


def dye_top_lab(hexc):
    L0, a0, b0 = lab(hex_rgb(hexc)); C0 = math.hypot(a0, b0); h = math.atan2(b0, a0); C = C0 * 1.2
    while C > 1:
        if all(-1e-4 <= c <= 1.0001 for c in lab_rgb(DYE_L, C * math.cos(h), C * math.sin(h), clip=False)): break
        C -= 1.0
    return (DYE_L, C * math.cos(h), C * math.sin(h))


def gen_step(share):
    """generations of descent: 0 for a share of 1 (a founder, or a close marriage's child at 3/4), 1 for 1/2, ... 4 for 1/16 or less"""
    if share >= 1.0: return 0
    return int(clamp(math.floor(-math.log2(share) + 0.5), 0, DYE_K_MAX))


def dye_rgb(shares, dyes):
    """the thread's dye: share 0 is ecru; otherwise the equivalent share 1 - k/8 (k from the TOTAL share), split between the dyes in proportion
    to the person's shares, mixed from ecru toward the dyes in CIELAB (the tapestry's mixing)"""
    sh = {dk: clamp(float(eval_frac((shares or {}).get(dk, 0) or 0)), 0.0, 1.0) for dk in dyes}
    tot = sum(sh.values())
    if tot <= 0: return ECRU, None
    k = gen_step(min(tot, 1.0)); seq = 1.0 - k / 8.0; e = lab(ECRU); acc = [0.0, 0.0, 0.0]
    for dk, d in dyes.items():
        if sh[dk] > 0: acc = [a + seq * sh[dk] / tot * x for a, x in zip(acc, dye_top_lab(d['color']))]
    return tuple(round(c, 4) for c in lab_rgb(*[e[i] * (1 - seq) + acc[i] for i in range(3)])), k


def drawn(rgb):
    """what fiber.frag draws from a dye at full value (the core before its white mix): chroma raised 1.4x about the luminance, then normalised"""
    l = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    c = [clamp(l + STYLE_CHROMA * (x - l), 0.0, 1.0) for x in rgb]; m = (1.0 / STYLE_INK_VALUE) if STYLE_INK else (1.0 - STYLE_VALUE_NORM) + STYLE_VALUE_NORM * max(max(c), 1e-3)   # ink draws the dye as is
    return tuple(x / m for x in c)


def dye_legend(C):
    """the header legend and its swatches (drawn colours), from the same functions the threads use"""
    dyes = C['dyes']; steps = []
    for dk, d in dyes.items():
        row = []
        for k in range(DYE_K_MAX + 1):
            rgb, _ = dye_rgb({dk: 2.0 ** -k}, {dk: d}); row.append(dict(k=k, share='1' if k == 0 else ('1/%d' % 2 ** k if k < DYE_K_MAX else '1/%d or less' % 2 ** k), hex=hex_of(drawn(rgb))))
        steps.append(dict(dye=dk, hue=d.get('hue') or 'dye', ramp=row))
    hues = [s['hue'] for s in steps]
    if len(steps) == 1: text = '%s = descended from the founders (deeper = closer); %s = none' % (hues[0], STYLE_ECRU_WORD)
    else: text = ('%s descent (deeper = closer); ' + STYLE_ECRU_WORD + ' = neither') % ', '.join('%s = %s' % (s['hue'], s['dye'].capitalize()) for s in steps)
    return dict(text=text, steps=steps, ecru=hex_of(drawn(ECRU)), rule='step k = round(-log2(share of descent)), 0 to %d; a share of 0 is ' % DYE_K_MAX + STYLE_ECRU_WORD)


class Ribbons:
    def __init__(self): self.pos, self.tan, self.col, self.info, self.aux, self.idx = [], [], [], [], [], []

    def add(self, pts, years, kinds, alongs, ests, rgb, seed, pa, pb):
        base = len(self.pos); tans = []
        for i in range(len(pts)):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]; tans.append(norm(sub(b, a)))
        for p, t, y, k, a, e in zip(pts, tans, years, kinds, alongs, ests):
            for side in (-1.0, 1.0):
                self.pos.append(p); self.tan.append(t); self.col.append(rgb); self.info.append((side, y, seed, k)); self.aux.append((a, e, pa, pb))
        for i in range(len(pts) - 1):
            v = base + 2 * i; self.idx += [v, v + 1, v + 2, v + 1, v + 3, v + 2]

    @property
    def triangles(self): return len(self.idx) // 3


def ribbons(L, polys):
    rib = Ribbons(); idx = L['index']
    for pl in polys:
        pa = idx[pl['ids'][0]]; pb = idx[pl['ids'][1]] if len(pl['ids']) > 1 and pl['kind'] in ('union', 'close') else pa
        cum = [0.0]
        for i in range(1, len(pl['pts'])): cum.append(cum[-1] + length(sub(pl['pts'][i], pl['pts'][i - 1])))
        if pl['kind'] == 'life':   # a life's radial points carry 0..1 from birth to death (the taper); its move bends carry arc length (dashes)
            span = max(pl['end'] - pl['born'], 1e-6); al = [max(0.0, (y - pl['born']) / span) if k == 0 else c for y, k, c in zip(pl['years'], pl['kinds'], cum)]
        else: al = cum
        rib.add(pl['pts'], pl['years'], pl['kinds'], al, pl['est'], pl['color'], ((pa + 1) * 0.6180339887) % 1.0, pa, pb)
    return rib


# ---------------------------------------------------------------- the selection: lineage lists and subject beads (critique fix 2)
def share_sum(p): return sum(float(eval_frac(v)) for v in (p.get('shares') or {}).values())


def lineage(L, subject, spouse=None):
    """the people a close shot keeps lit, as person indices (fiber.vert uLine): the subject, the spouse, then the main line back to the
    founders (from each, the parent born in the family with the larger share of descent, eldest on a tie), then the other parent at each
    step (so the marriages along the line light too), then the rest of the subject's ancestors by generation; at most LINE_CAP"""
    P = L['P']; out = []
    def addp(x):
        if x in P and x not in out and len(out) < LINE_CAP: out.append(x)
    def parents(x): return sorted([q for q in (P[x].get('father'), P[x].get('mother')) if q in P], key=lambda q: (0 if P[q]['core'] else 1, -share_sum(P[q]), P[q]['born'], q))
    def chain(x):
        seq, seen = [], {x}
        while True:
            par = parents(x)
            if not par: return seq
            seq.append(par); x = par[0]
            if x in seen: return seq
            seen.add(x)
    who = [x for x in (subject, spouse) if x in P]
    for x in who: addp(x)
    chains = [chain(x) for x in who]
    for ch in chains:
        for par in ch: addp(par[0])
    for ch in chains:
        for par in ch:
            for q in par[1:]: addp(q)
    for x in who:
        gen = [x]
        while gen:
            nxt = []
            for g in gen:
                for q in parents(g):
                    addp(q); nxt.append(q)
            gen = nxt
    return [L['index'][x] for x in out]


def union_bead(L, uid, pid=None, max_s=None):
    """a marriage bead with a ring, on the marriage arc (the shell of its year): at the middle of the arc, or, when the shot frames one end
    of a long arc (spouses in distant houses), max_s pocket units along the arc from the subject's end, so the bead stays in the frame"""
    P, U, r = L['P'], L['U'], L['r']; u = U[uid]; y = u['year']
    a, b = L['dir_at'](u['a'], y), L['dir_at'](u['b'], y)
    if pid == u['b']: a, b = b, a
    ang = math.acos(clamp(dot(a, b), -1, 1)); s_mid = ang * r(y) / 2; mid = max_s is None or s_mid <= max_s
    m = slerp(a, b, 0.5 if mid else max_s / max(ang * r(y), 1e-9))
    est = u['year_precision'] not in ('year', 'day', 'month')
    where = 'the bead sits on the middle of their arc' if mid else 'the bead sits on their arc beside %s (the arc runs %d degrees round the shell)' % (P[pid]['label'].rsplit(' ', 1)[0], round(math.degrees(ang)))
    return dict(pos=r5(mul(m, r(y))), ring=True, year=y, estimated=est, grade=u.get('confidence') or 'Suspected', union=uid,
                what='%s and %s marry, %s; %s' % (P[u['a']]['name'], P[u['b']]['name'], ('year not in the data, drawn %d' % y) if est else y, where))


def point_bead(L, pid, year, what, est, grade):
    return dict(pos=r5(mul(L['dir_at'](pid, year), L['r'](year))), ring=False, year=year, estimated=est, grade=grade, what=what)


# ---------------------------------------------------------------- shots (the camera grammar, scaled to pocket units by G)
def tangent_toward(n, d2):
    g = sub(d2, mul(n, dot(n, d2)))
    if length(g) > 1e-6: return norm(g)
    c = cross(Y, n)
    return norm(c) if length(c) > 1e-6 else (1.0, 0.0, 0.0)


def clear_halo(pos, n):
    if length(pos) >= HALO_CLEAR: return pos
    for _ in range(60):
        pos = add(pos, mul(n, 0.01))
        if length(pos) >= HALO_CLEAR: break
    return pos


def lifted(pos, tgt, fov, up):
    # the caption strip covers the lower fifth of the frame: slide the camera down along its up vector so the subject sits LIFT of the half-height
    # above the frame centre, in the middle of the free area (Confirmed by frames: build-1 run 1 put MCU subjects behind the caption)
    h = LIFT * length(sub(pos, tgt)) * math.tan(fov / 2); u = norm(up)
    return sub(pos, mul(u, h)), sub(tgt, mul(u, h))


def put(shots, name, pos, tgt, fov, size, beat, up=Y, space='pocket', nav='EXAMINE', subject=None, lift=True, **kw):
    if lift and space == 'pocket': pos, tgt = lifted(pos, tgt, fov, up)
    s = dict(name=name, pos=r5(pos), tgt=r5(tgt), up=[round(x, 6) for x in norm(up)], fov=fov, size=size, beat=beat, space=space, nav=nav, subject=subject,
             frame=None if length(sub(norm(up), Y)) < 1e-9 else [round(x, 6) for x in frame_to(up)])
    s.update(kw); shots[name] = s
    return s


def fiber_span(L, pid):
    p = L['P'][pid]; return L['r'](p['pieces'][0][3]), L['r'](p['pieces'][-1][4])


def compose(pos, tgt, up, fov, third, roll):
    """square the up vector to the view, apply the dutch roll, then slide camera and target sideways so the target lands on a third"""
    f = norm(sub(tgt, pos)); u = norm(sub(up, mul(f, dot(up, f))))
    if roll: u = norm(rotate(u, tuple(f) + (math.radians(roll),)))
    if third:
        rt = norm(cross(f, u)); hw = length(sub(tgt, pos)) * math.tan(fov / 2) * ASPECT
        d = mul(rt, -third * hw / 3); pos, tgt = add(pos, d), add(tgt, d)
    return pos, tgt, u


def inside_glass(pos, tgt, n):
    """pull a close shot's camera toward its target until it is inside the glass and outside the seed's halo"""
    for _ in range(40):
        if length(pos) <= CAM_MAX_R: break
        pos = add(tgt, mul(sub(pos, tgt), 0.94))
    return clear_halo(pos, n)


def eye_shot(L, shots, name, pid, prefer_union=None, variant=0):
    """CU, time up: one life at one year (the union given, else the first dated marriage, else the first child's birth, else mid-life, computed)"""
    P, U, r = L['P'], L['U'], L['r']; p = P[pid]; why = None
    us = [U[prefer_union]] if prefer_union in U else sorted([U[u] for u in p['unions'] if u in U and U[u]['year_precision'] in ('year', 'day', 'month')], key=lambda u: (u['year'], u['id']))
    if us:
        u = us[0]; sp = u['b'] if u['a'] == pid else u['a']; year = u['year']
        est = u['year_precision'] not in ('year', 'day', 'month')
        why = dict(kind='marriage', year=year, estimated=est, spouse=sp, union=u['id'], grade=u.get('confidence') or 'Suspected',
                   text='%s marries %s, %s' % (p['name'], P[sp]['name'], ('year not in the data, drawn %d' % year) if est else year))
        g = tangent_toward(L['dir_at'](pid, year), L['dir_at'](sp, year))
    else:
        ch = [c for c in p['children'] if c in P and P[c].get('born_precision') in ('year', 'day')]
        if ch:
            c = min(ch, key=lambda c: (P[c]['born'], c)); year = P[c]['born']
            why = dict(kind='first child', year=year, estimated=False, child=c, grade=min([p.get('grade') or 'Suspected', P[c].get('grade') or 'Suspected'], key=lambda g: GRADE_RANK.get(g, 3)),
                       text='%s: first child, %s, born %d' % (p['name'], P[c]['name'], year))
            g = tangent_toward(L['dir_at'](pid, year), L['dir_at'](c, year))
        else:
            year = (p['born'] + (p['died'] or p['pieces'][-1][4])) // 2
            why = dict(kind='mid-life (computed)', year=year, estimated=True, grade='∑', text='%s at %d, mid-life (computed, not an event in the data)' % (p['name'], year))
            g = tangent_toward(L['dir_at'](pid, year), cross(Y, L['dir_at'](pid, year)))
    n = L['dir_at'](pid, year); ra, rb = fiber_span(L, pid); fov = 0.62; V = EYE_VARIANTS[variant % len(EYE_VARIANTS)]
    de = clamp((rb - ra) / (0.85 * 2 * math.tan(fov / 2)), 1.2 * G, 5.0 * G); hw = de * math.tan(fov / 2) * ASPECT
    Pt = mul(n, r(year)); tgt = add(Pt, mul(g, hw / 3)); t = norm(cross(g, n)); el = math.radians(V['el'])
    pos = add(tgt, mul(add(mul(t, V['side'] * math.cos(el)), mul(n, math.sin(el))), de))
    pos, tgt, up = compose(pos, tgt, n, fov, 0.0, V['roll'])
    pos = inside_glass(pos, tgt, n)
    if why['kind'] == 'marriage': bead = union_bead(L, why['union'], pid, hw / 3)   # hw / 3: the shot's target sits that far toward the spouse
    else: bead = point_bead(L, pid, year, why['text'], why['estimated'], why['grade'])
    pl, tl = lifted(pos, tgt, fov, up)
    return put(shots, name, pos, tgt, fov, 'CU', 'Eye to eye with one life at one year', up=up, subject=pid, year=year, year_point=r5(Pt), why=why, bead=bead,
               composition=V['name'], roll=V['roll'], subject_xy=[round(v, 3) for v in screen_xy(pl, tl, up, fov, Pt)])


def screen_xy(pos, tgt, up, fov, q):
    """normalised design-viewport coordinates of q (x, y in -1..1; X_ITE's fieldOfView spans the height, the smaller side)"""
    f = norm(sub(tgt, pos)); rt = norm(cross(f, up)); u = cross(rt, f); d = sub(q, pos); z = max(dot(d, f), 1e-6); t = math.tan(fov / 2)
    return dot(d, rt) / (z * t * ASPECT), dot(d, u) / (z * t)


BEAD_BOX = (-0.55, 0.55, -0.34, 0.66)        # where a close shot keeps its bead (x0, x1, y0, y1): clear of the caption, the header and the rail;
                                             # x within 0.55 of the landscape half-width keeps it on a portrait phone too (x 0.55 x 1527/923 < 0.92)


def present_shot(L, shots, name, pid, store=True, fell=None, unions=(), variant=0, flip=False, mirror=False):
    """the stop's composition (PRESENT_VARIANTS[variant]); when its bead cannot be kept in BEAD_BOX (the camera meets the glass before it
    is wide enough), the next composition that can, else the one that misses least"""
    best = None
    for j in range(len(PRESENT_VARIANTS)):
        V = dict(PRESENT_VARIANTS[(variant + j) % len(PRESENT_VARIANTS)])
        if flip: V['side'] = -V['side']
        if mirror: V['third'] = -V['third']
        s, miss = present_try(L, name, pid, fell, unions, V)
        if best is None or miss < best[1] - 1e-9: best = (s, miss)
        if miss <= 0: break
    s = best[0]
    if store: shots[name] = s
    return s


def present_try(L, name, pid, fell, unions, V):
    P, r = L['P'], L['r']; p = P[pid]
    pcs = [pc for pc in p['pieces'] if fell is None or pc[3] < fell - 4] or p['pieces']
    pc = max(pcs, key=lambda pc: (min(pc[4], fell or pc[4]) - pc[3], -pc[3]))
    n2 = L['slot'][(pid, pc[0])]; ra, rb = r(pc[3]), r(min(pc[4], fell) if fell and fell > pc[3] + 4 else pc[4]); fov = V['fov']
    mid0 = mul(n2, (ra + rb) / 2)
    mine = [u for u in unions if u in L['U'] and pid in (L['U'][u]['a'], L['U'][u]['b'])]
    # the camera's side axis: square to the stop's marriage arc when there is one (build 3: from along the arc it was seen end-on), else the
    # horizontal tangent of the house
    e2 = norm(cross(Y, n2)) if length(cross(Y, n2)) > 1e-6 else (1.0, 0.0, 0.0)
    if mine:
        u = L['U'][mine[0]]; sp = u['b'] if u['a'] == pid else u['a']; c2 = cross(tangent_toward(n2, L['dir_at'](sp, u['year'])), n2)
        if length(c2) > 1e-6: e2 = norm(c2)
    el = math.radians(V['el']); dp0 = clamp((rb - ra) / (V['fill'] * 2 * math.tan(fov / 2)), 1.5 * G, 6.0 * G)
    for it in range(12):   # widen until the bead sits in BEAD_BOX (Confirmed need: build 3 probe, Habsburg S05 rise put the ring on the header)
        dp = dp0 * 1.12 ** it
        pos = add(mid0, add(mul(e2, V['side'] * dp * math.cos(el)), mul(n2, dp * math.sin(el))))
        pos, mid, up = compose(pos, mid0, n2, fov, V['third'], V['roll'])
        pos = inside_glass(pos, mid, n2); pos, mid = lifted(pos, mid, fov, up)
        if mine: bead = union_bead(L, mine[0], pid, 0.3 * dp * math.tan(fov / 2) * ASPECT)
        elif pc is p['pieces'][0]:
            circa = p.get('born_precision') == 'circa'
            bead = point_bead(L, pid, pc[3], '%s is born, %s%d' % (p['name'], 'c. ' if circa else '', p['born']), circa, p.get('grade') or 'Suspected')
        else:
            mv = p.get('move') or {}; est = bool(mv.get('estimated'))
            bead = point_bead(L, pid, pc[3], '%s moves to the %s column, %s' % (p['name'], L['sectors'][pc[0]]['name'], ('year not in the data, drawn %d' % pc[3]) if est else pc[3]),
                              est, '≈' if est else (mv.get('grade') or '∑'))
        bx, by = screen_xy(pos, mid, up, fov, bead['pos'])
        if BEAD_BOX[0] <= bx <= BEAD_BOX[1] and BEAD_BOX[2] <= by <= BEAD_BOX[3]: break
    ya, yb = pc[3], (min(pc[4], fell) if fell and fell > pc[3] + 4 else pc[4])
    s = dict(name=name, pos=r5(pos), tgt=r5(mid), up=[round(x, 6) for x in up], fov=fov, size='MCU', beat='Present one person: a whole life, its parents and marriages',
             space='pocket', nav='EXAMINE', subject=pid, frame=[round(x, 6) for x in frame_to(up)], year=round((ya + yb) / 2), composition=V['name'],   # year: where the subject's label sits (the framed piece)
             bead=bead, bead_xy=[round(bx, 3), round(by, 3)], widened=it, roll=V['roll'], subject_xy=[round(v, 3) for v in screen_xy(pos, mid, up, fov, mid0)])
    miss = max(0.0, BEAD_BOX[0] - bx, bx - BEAD_BOX[1], BEAD_BOX[2] - by, by - BEAD_BOX[3])
    return s, miss


def make_shots(L):
    S_, r = L['sectors'], L['r']; shots = {}
    uf = sph(S_[L['fh']]['phi'], 0.0, 1.0); side = norm(cross(uf, Y))
    fov = 0.9; d = R_GLASS * SCALE / math.sin(0.40 * fov / 2); el = math.radians(14)
    put(shots, 'Host', add(mul(uf, -d * math.cos(el)), (0.0, d * math.sin(el), 0.0)), (0.0, 0.0, 0.0), fov, 'ELS', 'Opening: a small bright world inside a larger one', space='host')
    put(shots, 'Inside', add(add(mul(uf, -2.6 * G), (0.0, 0.55 * G, 0.0)), mul(side, -0.45 * G)), add(add(mul(uf, 6.0 * G), (0.0, 1.0 * G, 0.0)), mul(side, 0.4 * G)),
        1.15, 'POV', 'The founders: everything grows out of this core', nav='FLY')
    fov = 0.8; put(shots, 'Wide', sph(0.0, math.radians(16), R_GLASS / math.sin(0.74 * fov / 2)), (0.0, 0.0, 0.0), fov, 'LS', 'The whole dynasty at once')
    fov = 1.0; put(shots, 'Crown', sph(math.pi, math.radians(74), R_GLASS / math.sin(0.86 * fov / 2)), (0.0, 0.0, 0.0), fov, 'LS', 'The houses as a compass, west to east')
    big = max(L['keys'], key=lambda k: (S_[k]['people'], -S_[k]['lon'], k)); phi = S_[big]['phi']
    put(shots, 'Colossus', sph(phi, math.radians(-40), 0.84 * R_GLASS), sph(phi, math.radians(18), 0.22 * R_GLASS), 1.22, 'MS', 'The largest house towers over you', subject=big)
    fov = 0.75
    for k in L['keys']:
        sc = S_[k]; ys = sorted(L['P'][i]['born'] for i in L['P'] if any(pc[0] == k for pc in L['P'][i]['pieces']))
        rm = r(ys[len(ys) // 2]) if ys else 0.5 * R_GLASS
        tgt = sph(sc['phi'], 0.0, rm); chord = 2 * R_GLASS * math.sin(min(sc['span'], math.pi) / 2)
        dd = (chord / 2) / (0.7 * math.tan(fov / 2) * ASPECT); dirv = sph(sc['phi'], math.radians(12), 1.0); Rmin = R_GLASS + 1.5 * G
        dd = max(dd, -dot(tgt, dirv) + math.sqrt(dot(tgt, dirv) ** 2 - dot(tgt, tgt) + Rmin ** 2))
        put(shots, hshot(k), add(tgt, mul(dirv, dd)), tgt, fov, 'MS', 'One house: %s' % sc['name'], subject=k)
    put(shots, 'Flywheel', sph(0.0, math.radians(20), 2.3 * R_GLASS), (0.0, 0.0, 0.0), 0.85, 'LS', 'Idle: the world keeps turning', lift=False, period_s=120)
    return shots, big


def to_pocket(s):
    k = 1.0 / SCALE if s['space'] == 'host' else 1.0
    pos = mul(s['pos'], k); F = mul(s['tgt'], k)
    return dict(pos=pos, F=F, dir=norm(sub(pos, F)), w=length(sub(pos, F)))


def chain(a, b):
    pa, pb = to_pocket(a), to_pocket(b)
    S = wijk_S(length(sub(pb['F'], pa['F'])), max(pa['w'], 1e-3), max(pb['w'], 1e-3))
    turn = math.acos(clamp(dot(pa['dir'], pb['dir']), -1, 1))
    fa = norm(sub(pa['F'], pa['pos'])); fb = norm(sub(pb['F'], pb['pos']))
    return dict(path_S=round(S, 3), turn=turn, axis_turn_deg=round(math.degrees(math.acos(clamp(dot(fa, fb), -1, 1))), 1),
                dist_ratio=round(max(pa['w'], pb['w']) / max(1e-6, min(pa['w'], pb['w'])), 2),
                dur_s=round(clamp(TIMING['base'] + TIMING['per_S'] * S + TIMING['per_rad'] * turn, TIMING['min'], TIMING['max']), 2))


def words_of(st):
    return sum(len(x['text'].split()) for x in st['narration'] + st['computed'])


def make_tour(L, C, shots, big):
    """one shot per card stop: the first candidate that keeps the chain rules (a new size class; the axis turns >= 20 degrees or the distance
    changes >= 2x), else the first candidate"""
    P = L['P']; tour = []; prev = None; n_eye = n_pres = 0; last_close = None; last_pres = None
    for i, st in enumerate(C['stops']):
        subj = [x for x in st['subject'] if x in P]; cands = []
        key = 'S%02d_' % i
        if i == 0: cands = [('Host', 'load')]
        elif i == 1: cands = [('Inside', 'plunge')]
        elif st['key'] == 'wide': cands = [('Wide', 'fly')]
        elif st['key'] == 'ruptures': cands = [('Colossus', 'fly'), ('Wide', 'fly')]
        elif st['key'] == 'arrows': cands = [('Crown', 'fly'), ('Wide', 'fly')]
        else:
            us = [u for u in st.get('unions', []) if u in L['U']]
            if us:
                u = L['U'][us[0]]; who = next((x for x in subj if x in (u['a'], u['b'])), u['a'])
                cands.append(('eye|%s|%s' % (who, us[0]), 'fly'))
            if subj: cands += [('present|' + subj[0], 'fly'), ('house|' + P[subj[0]]['house'], 'fly'), ('eye|' + subj[0] + '|', 'fly')]
            cands += [('Crown', 'fly')]
        chosen = None
        for c, move in cands:
            if c.startswith('eye|'):
                _, pid, uid = c.split('|', 2); s = eye_shot(L, {}, key + 'EyeToEye', pid, uid or None, variant=n_eye)
            elif c.startswith('present|'):   # either side of the house plane: the one the camera turns less to reach (build 3 gate run 1: a 164 degree
                # turn into Darwin S05 peaked the angular speed at 6.8x the mean); the composition (elevation, third, roll) stays the cycle's
                # and the subject on the other third from the last close shot's subject (build 3 run 2: S04 EyeToEye and S05 Present both put
                # the fiber on the left third with the arc running right, one template again across kinds). Compositions are tried in the
                # cycle's order, never the last Present's; when no option can change sides, the one whose roll differs most from the last close shot.
                nv = len(PRESENT_VARIANTS); order = [(n_pres + j) % nv for j in range(nv) if PRESENT_VARIANTS[(n_pres + j) % nv]['name'] != last_pres]
                names = [PRESENT_VARIANTS[v]['name'] for v in order]   # ranked by the composition each option really got (present_shot may fall back)
                opts = [present_shot(L, {}, key + 'Present', c.split('|', 1)[1], store=False, fell=st.get('fell'), unions=st.get('unions', []), variant=v, flip=f, mirror=m)
                        for v in order for f in (False, True) for m in (False, True)]
                opts = [(names.index(x['composition']), x) for x in opts if x['composition'] in names] or [(0, x) for x in opts]
                def third(x): return 0 if abs(x['subject_xy'][0]) < 0.15 else (1 if x['subject_xy'][0] > 0 else -1)
                def rank(j):
                    oi, x = opts[j]
                    if prev is None: return (0, 0, 0, oi, 0.0, j)
                    ch = chain(prev, x); same = 1 if last_close and third(x) != 0 and third(x) == third(last_close) else 0
                    roll = next(V['roll'] for V in PRESENT_VARIANTS if V['name'] == x['composition'])
                    return (0 if prev['size'] != x['size'] and (ch['axis_turn_deg'] >= 20 or ch['dist_ratio'] >= 2) else 1, 1 if ch['turn'] > math.radians(150) else 0, same,
                            -abs(roll - (last_close or {}).get('roll', 0.0)) if same else oi, ch['turn'], j)
                s = opts[min(range(len(opts)), key=rank)][1]
            elif c.startswith('house|'): s = shots[hshot(c.split('|', 1)[1])]
            else: s = shots[c]
            ok = True
            if prev is not None and move != 'plunge':
                ch = chain(prev, s); ok = prev['size'] != s['size'] and (ch['axis_turn_deg'] >= 20 or ch['dist_ratio'] >= 2)
            if ok or chosen is None:
                if chosen is None or ok: chosen = (s, move)
            if ok: break
        s, move = chosen
        if s['name'].startswith('S%02d_' % i): shots[s['name']] = s
        n_eye += s['name'].endswith('_EyeToEye'); n_pres += s['name'].endswith('_Present')
        if s.get('subject_xy'): last_close = s
        if s['name'].endswith('_Present'): last_pres = s.get('composition')
        w = words_of(st); hold = math.ceil(clamp(1.5 + w / 3.0, 4.0, 9.0) * 10) / 10
        t = dict(i=i, key=st['key'], title=st['title'], shot=s['name'], size=s['size'], composition=s.get('composition'), move=move, fell=st.get('fell'), years=st['years'],
                 subject=[x for x in st['subject'] if x in P], focus=[x for x in st['focus'] if x in P], unions=[u for u in st.get('unions', []) if u in L['U']], words=w, hold_s=hold)
        if prev is not None:
            ch = chain(prev, s)
            t.update(path_S=ch['path_S'], axis_turn_deg=ch['axis_turn_deg'], dist_ratio=ch['dist_ratio'], dur_s=7.0 if move == 'plunge' else ch['dur_s'])
        if s.get('subject') in P and s['size'] in ('CU', 'MCU'):   # close shots light the subject and the line back to the founders
            sp = None; b = s.get('bead') or {}
            if b.get('union'): u = L['U'][b['union']]; sp = u['b'] if u['a'] == s['subject'] else u['a']
            t['line'] = lineage(L, s['subject'], sp)
        tour.append(t); prev = s
    checks = []
    for a, b in zip(tour, tour[1:]):
        if b['move'] == 'plunge':
            checks.append(dict(pair=[a['shot'], b['shot']], ok=a['size'] != b['size'], sizes=[a['size'], b['size']], note='the plunge: through the shell into the core (fixed 7 s)')); continue
        ok = a['size'] != b['size'] and (b['axis_turn_deg'] >= 20 or b['dist_ratio'] >= 2)
        checks.append(dict(pair=[a['shot'], b['shot']], ok=ok, sizes=[a['size'], b['size']], axis_turn_deg=b['axis_turn_deg'], dist_ratio=b['dist_ratio']))
    return tour, checks


# ---------------------------------------------------------------- labels (anchors only: the page projects and places them, greedily, never overlapping)
def label_point(L, pid, year=None):
    p = L['P'][pid]
    if year is None:
        pc = max(p['pieces'], key=lambda pc: (pc[4] - pc[3], -pc[3])); year = (pc[3] + pc[4]) / 2
    year = clamp(year, p['pieces'][0][3], p['pieces'][-1][4])
    return r5(mul(L['dir_at'](pid, year), L['r'](year)))


def stop_labels(L, t, shots):
    P = L['P']; out = []; s = shots.get(t['shot'], {})
    fell = t['fell'] or L['TOP']
    for pid in t['subject']:
        y = s.get('year') if s.get('subject') == pid else None
        if y is None: y = min(fell, (P[pid]['pieces'][0][3] + P[pid]['pieces'][-1][4]) / 2)
        out.append(dict(text=P[pid]['label'], kind='subject', ref=pid, pos=label_point(L, pid, y), pri=0))
    for pid in t['focus']:
        if pid in t['subject']: continue
        y = min(fell, (P[pid]['pieces'][0][3] + P[pid]['pieces'][-1][4]) / 2)
        if P[pid]['born'] > fell: continue
        out.append(dict(text=P[pid]['label'], kind='name', ref=pid, pos=label_point(L, pid, y), pri=3))
    return out


# ---------------------------------------------------------------- v2: the sphere's words in the stops (the cards keep the tapestry's)
HYPER_WORDS = [   # ordered; whole words only; the file name loom-view.json is never touched
    (r'\bThe weft doubles back\b', 'The arc doubles back'), (r'\bThe close weave\b', 'Close marriages'), (r'\bRuptures, then the fell\b', 'Ruptures, then the present'),
    (r' \(an open diamond marks the end that moves\)', ''), (r' \(open diamond\)', ''), (r'\bMarked on the cloth from the narration\b', 'From the narration'),
    (r'\bthe cloth\b', 'the sphere'), (r'\bPull any thread\b', 'Click any fiber'), (r'\bwedding picks\b', 'wedding arcs'), (r'\bwedding pick\b', 'wedding arc'),
    (r'\bThreads\b', 'Fibers'), (r'\bthreads\b', 'fibers'), (r'\bthread\b', 'fiber'), (r'\bpicks\b', 'marriages'), (r'\bpick\b', 'marriage'),
    (r'\bcolumns\b', 'sectors'), (r'\bcolumn\b', 'sector'),
]
LOOM_WORDS = re.compile(r'\b(cloth|threads?|weft|warp|picks?|woven|weave|upright|columns?)\b', re.I)


def hyper_words(s):
    for a, b in HYPER_WORDS: s = re.sub(a, b, s)
    return s


def stop_text(L, C, t, i0=False):
    """the caption of a hypersphere stop: the card stop's title, narration and computed lines in the sphere's words; the opening stop describes
    the sphere itself (the style board's text: v3 reused the tapestry's 'upright thread' line). Grades are kept."""
    st = C['stops'][t['i']]
    if i0:
        hs = [L['sectors'][k]['name'] for k in L['keys']]; U = L['U']
        out = dict(title=C['name'], narration=[dict(text='A sphere of time: the founders sit at the centre (%d), the present is the glass (%d). Each life is a fiber running '
                                                     'outward from birth to death; each marriage is an arc on the shell of its year.' % (L['Y0'], L['TOP']), grade='∑')],
                   computed=[dict(text='%d lives and %d marriages (%d between close kin), in %d houses placed west to east: %s.' % (
                       len(L['P']), len(U), sum(1 for u in U.values() if u['close']), len(hs), ', '.join(hs)), grade='∑'),
                             dict(text=dye_legend(C)['text'] + '; dashed = an estimated year.', grade='∑')])
    else:
        out = dict(title=hyper_words(st['title']), narration=[dict(x, text=hyper_words(x['text'])) for x in st['narration']],
                   computed=[dict(x, text=hyper_words(x['text'])) for x in st['computed']])
    left = [m.group(0) for x in [out['title']] + [y['text'] for y in out['narration'] + out['computed']] for m in LOOM_WORDS.finditer(x)]
    if left: raise SystemExit('stop %s still uses tapestry words: %s' % (st['key'], sorted(set(left))))
    return out


# ---------------------------------------------------------------- v2: portrait plates (camera-facing, faded and drifted by X3D interpolators)
PLATE_K = 0.10                 # a plate's height as a share of the shot camera's distance to the person (about a seventh of the frame)
PLATE_ASPECT = 0.8             # the cut-outs are 4:5
PLATE_FADE = (0.55, 1.0)       # share of the flight over which a stop's plates fade in (the page runs the clock over the flight)
PLATE_T = 0.06                 # transparency once in (a little of the scene shows through)
PLATE_OUT_S = 0.9              # seconds to fade out when the camera leaves
PLATE_DRIFT = 0.30             # the drift on arrival, in plate heights, toward the plate's resting place
PLATE_LINKED = 2               # at most two linked people (a spouse or a parent with an entry) beside the subject


def make_plates(L, shots, tour, portraits, root_rel=''):
    """per close stop (CU, MCU) whose subject has a portraits.json entry: the subject and at most two linked people with entries (the stop's
    marriage partner first, then other spouses, then the parents), each a plate near their fiber at the stop's year. Pending or rejected entries
    carry their monogram (portraits.json says which file); people with no entry get no plate."""
    P, U = L['P'], L['U']; out = {}
    for t in tour:
        s = shots.get(t['shot']) or {}; subj = s.get('subject')
        if s.get('size') not in ('CU', 'MCU') or subj not in P or subj not in portraits: continue
        b = s.get('bead') or {}; y = b.get('year') or s.get('year') or (P[subj]['pieces'][0][3] + P[subj]['pieces'][-1][4]) / 2
        cands = []
        if b.get('union') in U: u = U[b['union']]; cands.append(u['b'] if u['a'] == subj else u['a'])
        for uid in P[subj].get('unions') or []:
            if uid in U: u = U[uid]; cands.append(u['b'] if u['a'] == subj else u['a'])
        cands += [P[subj].get('father'), P[subj].get('mother')]
        linked = []
        for c in cands:
            if c and c in P and c in portraits and c != subj and c not in linked and P[c]['born'] <= y: linked.append(c)
        linked = linked[:PLATE_LINKED]
        pos, tgt, up = s['pos'], s['tgt'], s['up']
        f = norm(sub(tgt, pos)); rt = norm(cross(f, up)); uv = cross(rt, f)
        sx0 = screen_xy(pos, tgt, up, s['fov'], label_point(L, subj, y))[0]
        items = []
        for k, pid in enumerate([subj] + linked):
            q = label_point(L, pid, y); d = max(length(sub(q, pos)), 1e-3); h = PLATE_K * d; wd = PLATE_ASPECT * h
            sx = screen_xy(pos, tgt, up, s['fov'], q)[0]
            # the subject's plate goes to the side with less room (the page's portrait card takes the side with more); a linked person's away from the subject
            side = (-1.0 if sx0 < 0 else 1.0) if k == 0 else (1.0 if sx >= sx0 else -1.0)
            end = add(q, add(mul(uv, 0.62 * h), mul(rt, side * 0.78 * wd)))
            start = add(end, add(mul(rt, side * PLATE_DRIFT * h), mul(uv, -0.5 * PLATE_DRIFT * h)))
            e = portraits[pid]
            items.append(dict(id=pid, role='subject' if k == 0 else 'linked', pos=r5(end), start=r5(start), h=round(h, 5), w=round(wd, 5), kind=e['kind'], status=e['status'],
                              label=e['label'], tex=root_rel + e['cutout'], year=round(y, 2)))
        key = re.sub(r'[^A-Za-z0-9_]', '_', t['shot'])
        out[t['shot']] = dict(stop=t['i'], tour=tour.index(t), year=round(y, 2), group='Plates_' + key, clock_in='PlatesIn_' + key, clock_out='PlatesOut_' + key,
                              mat='PlateMat_' + key, items=items)
    return out


def write_plates(w, plates):
    """the plates as standard X3D: Transform > Billboard (screen-aligned) > Transform (size) > Shape (UnlitMaterial + ImageTexture of the cut-out,
    whose alpha is the feathered edge). Per stop, one material fades every plate: PlatesIn (a TimeSensor the page starts with the flight, its
    cycleInterval set to the flight's length) drives a ScalarInterpolator into the material's transparency and a PositionInterpolator per plate
    (a short drift into place); PlatesOut (started when the camera leaves) fades them out. Returns the DEFs to EXPORT."""
    if not plates: return []
    w("    <!-- PORTRAIT PLATES (v2): on a close stop the subject and up to two linked people, near their fibers at the stop's year; the cut-outs come from\n"
      "         portraits.json (an AI portrait with its label, or a monogram card). Transparency and a slight drift come from X3D interpolators. -->\n")
    w("    <Group DEF='Plates'>\n"); defs, tex, quad = [], set(), False
    for shot, g in plates.items():
        w("      <Group DEF='%s'>\n" % g['group'])
        for k, it in enumerate(g['items']):
            mat = ("<UnlitMaterial DEF='%s' emissiveColor='1 1 1' transparency='1'/>" % g['mat']) if k == 0 else "<UnlitMaterial USE='%s'/>" % g['mat']
            tdef = 'Tex_' + re.sub(r'[^A-Za-z0-9_]', '_', it['id'])
            tx = ("<ImageTexture USE='%s'/>" % tdef) if tdef in tex else ("<ImageTexture DEF='%s' url='\"%s\"' repeatS='false' repeatT='false'/>" % (tdef, it['tex'])); tex.add(tdef)
            geo = "<IndexedTriangleSet USE='PlateQuad'/>" if quad else ("<IndexedTriangleSet DEF='PlateQuad' solid='false' index='0 1 2 0 2 3'><Coordinate point='-0.5 -0.5 0 0.5 -0.5 0 0.5 0.5 0 -0.5 0.5 0'/>"
                                                                       "<TextureCoordinate point='0 0 1 0 1 1 0 1'/></IndexedTriangleSet>"); quad = True
            w("        <Transform DEF='PlateLens_%s_%d'>\n" % (g['group'][7:], k))   # NAV HOOK: the page moves and scales it with the lens
            w("        <Transform DEF='Plate_%s_%d' translation='%s'>\n          <Billboard axisOfRotation='0 0 0'>\n            <Transform scale='%s %s 1'>\n"
              "              <Shape>\n                <Appearance>%s%s</Appearance>\n                %s\n              </Shape>\n            </Transform>\n          </Billboard>\n        </Transform>\n" % (
                  g['group'][7:], k, v3(it['start'], 5), fnum(it['w'], 5), fnum(it['h'], 5), mat, tx, geo))
            w("        </Transform>\n")
        w("      </Group>\n")
    w("    </Group>\n")
    for shot, g in plates.items():
        k0, k1 = PLATE_FADE
        w("    <TimeSensor DEF='%s' cycleInterval='4' loop='false'/>\n    <TimeSensor DEF='%s' cycleInterval='%s' loop='false'/>\n" % (g['clock_in'], g['clock_out'], fnum(PLATE_OUT_S)))
        w("    <ScalarInterpolator DEF='PlateIn_%s' key='0 %s 1' keyValue='1 1 %s'/>\n" % (g['group'][7:], fnum(k0), fnum(PLATE_T)))
        w("    <ScalarInterpolator DEF='PlateOut_%s' key='0 1' keyValue='%s 1'/>\n" % (g['group'][7:], fnum(PLATE_T)))
        for k, it in enumerate(g['items']):
            w("    <PositionInterpolator DEF='PlateDrift_%s_%d' key='0 %s 1' keyValue='%s, %s, %s'/>\n" % (g['group'][7:], k, fnum(k0), v3(it['start'], 5), v3(it['start'], 5), v3(it['pos'], 5)))
        w("    <ROUTE fromNode='%s' fromField='fraction_changed' toNode='PlateIn_%s' toField='set_fraction'/>\n" % (g['clock_in'], g['group'][7:]))
        w("    <ROUTE fromNode='PlateIn_%s' fromField='value_changed' toNode='%s' toField='set_transparency'/>\n" % (g['group'][7:], g['mat']))
        w("    <ROUTE fromNode='%s' fromField='fraction_changed' toNode='PlateOut_%s' toField='set_fraction'/>\n" % (g['clock_out'], g['group'][7:]))
        w("    <ROUTE fromNode='PlateOut_%s' fromField='value_changed' toNode='%s' toField='set_transparency'/>\n" % (g['group'][7:], g['mat']))
        for k, it in enumerate(g['items']):
            w("    <ROUTE fromNode='%s' fromField='fraction_changed' toNode='PlateDrift_%s_%d' toField='set_fraction'/>\n" % (g['clock_in'], g['group'][7:], k))
            w("    <ROUTE fromNode='PlateDrift_%s_%d' fromField='value_changed' toNode='Plate_%s_%d' toField='set_translation'/>\n" % (g['group'][7:], k, g['group'][7:], k))
        defs += [g['clock_in'], g['clock_out'], g['mat']] + ['PlateLens_%s_%d' % (g['group'][7:], k) for k in range(len(g['items']))]   # NAV HOOK
    return defs


# ---------------------------------------------------------------- X3D writers
HEAD = "<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>\n"


def vp_xml(name, s, desc, ind='    ', extra='', children=''):
    pos, tgt = s['pos'], s['tgt']
    close = ("/>\n" if not children else ">\n%s%s  %s\n%s%s</Viewpoint>\n")
    if s['frame']:
        fr = s['frame']; inv = (fr[0], fr[1], fr[2], -fr[3]); lp, lt = rotate(pos, inv), rotate(tgt, inv); o = look_at(lp, lt, Y)
        return "%s<Transform DEF='Frame_%s' rotation='%s'>\n%s  <Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'%s/>\n%s</Transform>\n" % (
            ind, name, v3(fr, 6), ind, name, esc(desc), v3(lp, 5), v3(o, 6), v3(lt, 5), fnum(s['fov'], 3), extra, ind)
    o = look_at(pos, tgt, Y)
    head = "%s<Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'%s" % (ind, name, esc(desc), v3(pos, 5), v3(o, 6), v3(tgt, 5), fnum(s['fov'], 3), extra)
    return head + ("/>\n" if not children else ">\n%s  %s\n%s</Viewpoint>\n" % (ind, children, ind))


def write_pocket(F, C, L, shots, tour, rib, path, mapping, plates=None):
    P = L['P']; o = []; w = o.append; tri = {}
    fam = C['family']
    common = [('uCycle', 'SFFloat', '0.25')]
    units = [('uY0', 'SFFloat', fnum(L['Y0'])), ('uR0', 'SFFloat', fnum(R0)), ('uK', 'SFFloat', fnum(L['K'], 7))]
    def fiber_f(wd, mpx, xpx, pas): return common + [('uFell', 'SFFloat', fnum(L['TOP']))] + units + [('uExposure', 'SFFloat', '1'), ('uGhost', 'SFFloat', '0.05'), ('uGain', 'SFFloat', '1'),
                                                    ('uPick', 'SFFloat', '-1'), ('uLine', 'MFFloat', ' '.join(['-1'] * LINE_CAP)), ('uFocus', 'SFFloat', '1'), ('uWidth', 'SFFloat', fnum(wd, 5)), ('uMinPx', 'SFFloat', fnum(mpx, 3)), ('uMaxPx', 'SFFloat', fnum(xpx, 3)),
                                                    ('uQ', 'SFInt32', '2'), ('uPass', 'SFInt32', str(pas)), ('uBlend', 'SFInt32', '0')]
    shell_f = common + [('uSeed', 'SFFloat', '0.618'), ('uExposure', 'SFFloat', '1.2'), ('uFell', 'SFFloat', fnum(L['TOP']))] + units + [
        ('uR', 'SFFloat', fnum(R_GLASS)), ('uRp', 'SFFloat', fnum(R_PROXY)), ('uHaze', 'SFFloat', '1'), ('uGain', 'SFFloat', '1'), ('uShell0', 'SFFloat', fnum(L['shell0'])),
        ('uTop', 'SFFloat', fnum(L['TOP'])), ('uInside', 'SFFloat', '0.35'), ('uQ', 'SFInt32', '2'), ('uBlend', 'SFInt32', '0'), ('logDepth', 'SFFloat', '0')]
    def glow_f(g, rg, ring, gain): return common + [('uExposure', 'SFFloat', fnum(g['exposure'])), ('uRg', 'SFFloat', fnum(rg)), ('uGain', 'SFFloat', fnum(gain)),
                                                    ('uE2', 'SFFloat', fnum(g['e2'], 6)), ('uS2', 'SFFloat', fnum(g['s2'], 6)), ('uHalo', 'SFFloat', fnum(g['halo'], 6)),
                                                    ('uCore', 'SFFloat', fnum(g['core'], 5)), ('uPeriod', 'SFFloat', fnum(g['period'])), ('uRing', 'SFFloat', fnum(ring, 3)), ('uKnee', 'SFFloat', fnum(g['knee'], 5)), ('uZ', 'SFFloat', fnum(g['z'], 3)),
                                                    ('uHaloTint', 'SFVec3f', v3(g['halo_tint'], 3)), ('uCoreTint', 'SFVec3f', v3(g['core_tint'], 3)), ('uBlend', 'SFInt32', '0'), ('logDepth', 'SFFloat', '0')]
    seed_f = glow_f(SEED_GLOW, SEED_GLOW_R, 0, 1)
    ev, en, ef = icosphere(3, SEED_R); gv, gn, gf = icosphere(2, SEED_GLOW_R); sv, sn, sf = icosphere(3, R_PROXY); bv, bn, bf = icosphere(2, BEAD_R)
    w(HEAD)
    w("  <head>\n    <component name='Shaders' level='1'/>\n    <component name='Shape' level='2'/>\n    <component name='Rendering' level='5'/>\n")
    w("    <meta name='title' content='%s'/>\n" % os.path.basename(path))
    w("    <meta name='description' content='%s'/>\n" % esc('Dynasty hypersphere, %s: the pocket world, to be Inlined in a host (it EXPORTs its shots, Probe, sensors and shaders). %s Generated by %s from loom-view.json; do not edit.' % (C['name'], mapping['short'], VERSION)))
    w("    <meta name='generator' content='%s'/>\n    <meta name='data' content='proto/merged/loom-view.json (via proto/scene2/out/%s.cards.json)'/>\n" % (VERSION, fam))
    w("    <meta name='license' content='generated scene; shaders written for this prototype; data from the project&apos;s harvest (see the cards for sources)'/>\n  </head>\n  <Scene>\n")
    w("    <WorldInfo title='Dynasty hypersphere: %s' info='%s'/>\n" % (esc(C['name']), ' '.join('&quot;%s&quot;' % esc(x) for x in mapping['lines'])))
    w("    <NavigationInfo DEF='Nav' type='\"EXAMINE\" \"ANY\"' headlight='false' speed='0.6' avatarSize='0.01 0.16 0.075' transitionType='\"ANIMATE\"' transitionTime='1.6'/>\n")
    w("    <NavigationInfo DEF='NavFly' type='\"FLY\" \"ANY\"' headlight='false' speed='0.15' avatarSize='0.004 0.16 0.075' transitionType='\"ANIMATE\"' transitionTime='2.4'/>\n")
    w("    <!-- NavNone (nav): the page owns the camera. The Probe binds it, so X_ITE adds no navigation of its own (it still delivers clicks to sensors). -->\n")
    w("    <NavigationInfo DEF='NavNone' type='\"NONE\"' headlight='false' avatarSize='0.004 0.16 0.075' transitionType='\"TELEPORT\"' transitionTime='0'/>\n")
    w("    <Background DEF='PocketSky' skyColor='%s'/>\n" % ' '.join('%.3f' % x for x in TH._rgb(THEME['ground_bot'])))
    w("    <!-- THE SHOTS (camera grammar). Wide first, so it is bound when this file is opened alone; inside a host the host's opening view is bound. -->\n")
    names = ['Wide', 'Crown', 'Colossus'] + [hshot(k) for k in L['keys']] + sorted(n for n in shots if n.startswith('S'))
    for n in names:
        s = shots[n]
        desc = ('House: ' + L['sectors'][next(k for k in L['keys'] if hshot(k) == n)]['name']) if n.startswith('House_') else (n.split('_', 1)[1] + ': ' + str(P.get(s.get('subject'), {}).get('name', '')) if n.startswith('S') else n)
        w(vp_xml(n, s, desc))
    s = shots['Inside']
    w(vp_xml('Inside', s, 'Inside: the founders', children="<NavigationInfo USE='NavFly' containerField='navigationInfo'/>"))
    s = shots['Flywheel']
    w("    <!-- Flywheel: the idle orbit with no script. The clock turns the rig, the rig carries the Viewpoint; EXAMINE still works on top. -->\n")
    w("    <Transform DEF='FlywheelRig'>\n%s    </Transform>\n" % vp_xml('Flywheel', s, 'Flywheel (idle orbit)', ind='      '))
    w("    <TimeSensor DEF='FlywheelClock' cycleInterval='%d' loop='true'/>\n" % s['period_s'])
    w("    <OrientationInterpolator DEF='FlywheelTurn' key='0 0.25 0.5 0.75 1' keyValue='0 1 0 0, 0 1 0 1.570796, 0 1 0 3.141593, 0 1 0 4.712389, 0 1 0 6.283185'/>\n")
    w("    <ROUTE fromNode='FlywheelClock' fromField='fraction_changed' toNode='FlywheelTurn' toField='set_fraction'/>\n")
    w("    <ROUTE fromNode='FlywheelTurn' fromField='value_changed' toNode='FlywheelRig' toField='set_rotation'/>\n")
    wd = shots['Wide']
    w("    <!-- Probe: the viewpoint the page flies from the real camera pose. ProbeFrame turns +Y to the shot's up (rolled shots stay level under EXAMINE).\n"
      "         CamSense reports the camera in pocket units; ShellSense reports entering the glass. -->\n")
    w("    <Transform DEF='ProbeFrame'>\n      <Viewpoint DEF='Probe' description='Probe' position='%s' orientation='%s' centerOfRotation='0 0 0' fieldOfView='%s'>\n        <NavigationInfo USE='NavNone' containerField='navigationInfo'/>\n      </Viewpoint>\n    </Transform>\n" % (
        v3(wd['pos'], 5), v3(look_at(wd['pos'], wd['tgt']), 6), fnum(wd['fov'], 3)))
    w("    <ProximitySensor DEF='CamSense' size='1000000 1000000 1000000'/>\n    <ProximitySensor DEF='ShellSense' size='%s %s %s'/>\n" % ((fnum(2 * R_GLASS),) * 3))
    w("    <!-- THE FOUNDERS' SEED: a small limb-darkened sun (SeedCore, tone-mapped like every shader here; the PhysicalMaterial is the fallback),\n"
      "         a point light, and an analytic glow on a small proxy (SeedGlow). Both breathe with the Clock (4 s). -->\n")
    w("    <PointLight DEF='SeedLight' global='true' location='0 0 0' color='1 0.74 0.45' intensity='0.35' radius='100' attenuation='1 0 0'/>\n")
    w("    <!-- SeedXf (nav): the lens moves and scales the seed from the page (its glow is analytic in its own local space). -->\n    <Transform DEF='SeedXf'>\n")
    w("    <Shape DEF='Seed'>\n      <Appearance DEF='SeedApp'><PhysicalMaterial DEF='SeedMat' baseColor='1 0.95 0.85' emissiveColor='0.55 0.45 0.32' metallic='0' roughness='0.2'/>\n"
      "        <ComposedShader DEF='SeedCore' language='GLSL'>%s\n          %s\n          %s\n        </ComposedShader>\n      </Appearance>\n" % (
        fields(common + [('uExposure', 'SFFloat', '1')], '          '), part('SeedVS', 'VERTEX', 'ring.vert.glsl'), part('SeedCoreFS', 'FRAGMENT', 'seedcore.frag.glsl')))
    w("      <IndexedTriangleSet solid='true' index='%s'>\n        <Coordinate point='%s'/>\n        <Normal vector='%s'/>\n      </IndexedTriangleSet>\n    </Shape>\n" % (' '.join(str(i) for t in ef for i in t), flat(ev, 5), flat(en, 4)))
    w("    <Shape DEF='SeedGlowShape'>\n      <Appearance DEF='SeedGlowApp' alphaMode='BLEND'>\n        <ComposedShader DEF='SeedGlow' language='GLSL'>%s\n          %s\n          %s\n        </ComposedShader>\n      </Appearance>\n" % (
        fields(seed_f + LENSG.fields('SeedGlow', seed_f), '          '), part('RayVS', 'VERTEX', 'ray.vert.glsl'), part('SeedFS', 'FRAGMENT', 'seed.frag.glsl')))
    w("      <IndexedTriangleSet DEF='SeedGlowProxy' solid='false' index='%s'>\n        <Coordinate point='%s'/>\n      </IndexedTriangleSet>\n    </Shape>\n" % (' '.join(str(i) for t in gf for i in t), flat(gv, 5)))
    w("    </Transform>\n")
    w("    <!-- THE SUBJECT BEAD: on a close shot the page moves BeadXf to the stop's event (a point on the subject's life, or the middle of a marriage\n"
      "         arc, where uRing draws a ring) and turns BeadSwitch on. The same point-glow shader as the seed, smaller, on a 2 s breath. -->\n")
    w("    <Transform DEF='BeadXf'>\n      <Switch DEF='BeadSwitch' whichChoice='-1'>\n        <Shape DEF='Bead'>\n          <Appearance DEF='BeadApp' alphaMode='BLEND'>\n"
      "            <ComposedShader DEF='BeadGlow' language='GLSL'>%s\n              <ShaderPart USE='RayVS'/>\n              <ShaderPart USE='SeedFS'/>\n            </ComposedShader>\n          </Appearance>\n" % fields(glow_f(BEAD_GLOW, BEAD_R, 0, 1) + LENSG.fields('BeadGlow', glow_f(BEAD_GLOW, BEAD_R, 0, 1)), '              '))
    w("          <IndexedTriangleSet DEF='BeadProxy' solid='false' index='%s'>\n            <Coordinate point='%s'/>\n          </IndexedTriangleSet>\n        </Shape>\n      </Switch>\n    </Transform>\n" % (
        ' '.join(str(i) for t in bf for i in t), flat(bv, 6)))
    w("    <!-- THE THREADS: one ribbon mesh drawn twice (USE). The hot core is opaque and narrow; the glow is transparent and wide. A life is a radial\n"
      "         fiber from r(born) to r(died); a spawn arc on the birth shell joins it to a parent; a move bends it along the shell of the move year;\n"
      "         a marriage is an arc on the shell of its year (a close one doubled and brighter). Vertex attributes carry year, kind, estimate, person. -->\n")
    w("    <Shape DEF='Threads'>\n      <Appearance DEF='CoreApp' alphaMode='OPAQUE'>\n        <ComposedShader DEF='FiberCore' language='GLSL'>%s\n          %s\n          %s\n        </ComposedShader>\n      </Appearance>\n" % (
        fields(fiber_f(CORE_W, CORE_MIN_PX, CORE_MAX_PX, 0) + LENSG.fields('FiberCore', fiber_f(CORE_W, CORE_MIN_PX, CORE_MAX_PX, 0)), '          '), part('FiberVS', 'VERTEX', 'fiber.vert.glsl'), part('FiberFS', 'FRAGMENT', 'fiber.frag.glsl')))
    w("      <IndexedTriangleSet DEF='Ribbons' solid='false' colorPerVertex='true' index='%s'>\n" % ' '.join(str(i) for i in rib.idx))
    w("        <Coordinate point='%s'/>\n        <Color color='%s'/>\n" % (flat(rib.pos, 5), flat(rib.col, 3)))
    w("        <FloatVertexAttribute name='aTan' numComponents='3' value='%s'/>\n" % flat(rib.tan, 3))
    w("        <FloatVertexAttribute name='aInfo' numComponents='4' value='%s'/>\n" % ' '.join('%s %s %s %s' % (fnum(i[0], 0), fnum(i[1], 2), fnum(i[2], 3), fnum(i[3], 0)) for i in rib.info))
    w("        <FloatVertexAttribute name='aAux' numComponents='4' value='%s'/>\n" % ' '.join('%s %s %s %s' % (fnum(a[0], 3), fnum(a[1], 0), fnum(a[2], 0), fnum(a[3], 0)) for a in rib.aux))
    w("      </IndexedTriangleSet>\n    </Shape>\n")
    w("    <Switch DEF='GlowSwitch' whichChoice='0'>\n      <Shape DEF='Glow'>\n        <Appearance DEF='GlowApp' alphaMode='BLEND'>\n          <ComposedShader DEF='FiberGlow' language='GLSL'>%s\n            <ShaderPart USE='FiberVS'/>\n            <ShaderPart USE='FiberFS'/>\n          </ComposedShader>\n        </Appearance>\n        <IndexedTriangleSet USE='Ribbons'/>\n      </Shape>\n    </Switch>\n" % fields(fiber_f(GLOW_W_TIER['ultra'], GLOW_MIN_PX, GLOW_MAX_PX, 1) + LENSG.fields('FiberGlow', fiber_f(GLOW_W_TIER['ultra'], GLOW_MIN_PX, GLOW_MAX_PX, 1)), '            '))
    w("    <!-- THE GLASS: analytic sphere r=%s on a proxy r=%s (solid false: the shader keeps one layer outside and the far wall inside); time shells\n"
      "         every 50 years from %d; the fell shell; raymarched haze; gl_FragDepth from the analytic entry point, so host geometry composites. -->\n" % (fnum(R_GLASS), fnum(R_PROXY), L['shell0']))
    w("    <Shape DEF='Shell'>\n      <Appearance DEF='ShellApp' alphaMode='BLEND'>\n        <ComposedShader DEF='ShellShader' language='GLSL'>%s\n          <ShaderPart USE='RayVS'/>\n          %s\n        </ComposedShader>\n      </Appearance>\n" % (
        fields(shell_f + LENSG.fields('ShellShader', shell_f), '          '), part('ShellFS', 'FRAGMENT', 'shell.frag.glsl')))
    w("      <IndexedTriangleSet DEF='ShellProxy' solid='false' index='%s'>\n        <Coordinate point='%s'/>\n      </IndexedTriangleSet>\n    </Shape>\n" % (' '.join(str(i) for t in sf for i in t), flat(sv, 5)))
    plate_defs = write_plates(w, plates or {})
    w("    <!-- CLOCKS: standard X3D drives the shaders, so the pocket animates by itself when Inlined in any host. Every period divides 600 s. -->\n")
    w("    <TimeSensor DEF='Clock' cycleInterval='600' loop='true'/>\n")
    for s_ in ('ShellShader', 'SeedGlow', 'SeedCore', 'BeadGlow', 'FiberCore', 'FiberGlow'):
        w("    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='%s' toField='uCycle'/>\n" % s_)
    exports = ['Probe', 'ProbeFrame', 'CamSense', 'ShellSense', 'Nav', 'NavFly', 'NavNone', 'SeedXf', 'Inside', 'Flywheel', 'FlywheelRig', 'FlywheelClock'] + names + \
              ['Frame_' + n for n in names if shots[n]['frame']] + ['FiberCore', 'FiberGlow', 'ShellShader', 'SeedGlow', 'SeedCore', 'BeadGlow', 'BeadXf', 'BeadSwitch', 'GlowApp', 'ShellApp', 'SeedGlowApp', 'BeadApp', 'GlowSwitch', 'Clock', 'SeedMat'] + plate_defs
    for e in exports: w("    <EXPORT localDEF='%s'/>\n" % e)
    w("  </Scene>\n</X3D>\n")
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(o))
    tri = {'portrait_plates': 2 * sum(len(p['items']) for p in (plates or {}).values()), 'threads_per_pass': rib.triangles, 'threads_drawn (core + glow)': 2 * rib.triangles, 'glass_proxy': len(sf), 'seed': len(ef), 'seed_glow_proxy': len(gf), 'bead_proxy (close shots only)': len(bf)}
    return exports, tri


def write_host(C, L, shots, exports, pocket_file, path, mapping):
    s = shots['Host']; o = []; w = o.append
    kv, kn, kf = icosphere(2, 400.0)
    w(HEAD)
    w("  <head>\n    <component name='Shaders' level='1'/>\n    <component name='Shape' level='2'/>\n    <component name='Rendering' level='5'/>\n")
    w("    <meta name='title' content='%s'/>\n" % os.path.basename(path))
    w("    <meta name='description' content='%s'/>\n" % esc('Host space for the dynasty hypersphere (%s): the %s backdrop, the armillary, lights, the opening viewpoint, and the pocket %s Inlined at scale %g with IMPORTs. Generated by %s; do not edit.' % (C['name'], THEME['name'], pocket_file, SCALE, VERSION)))
    w("    <meta name='generator' content='%s'/>\n  </head>\n  <Scene>\n" % VERSION)
    w("    <WorldInfo title='Dynasty hypersphere (host): %s'/>\n" % esc(C['name']))
    w("    <NavigationInfo DEF='HostNav' type='\"EXAMINE\" \"ANY\"' headlight='false' speed='4' avatarSize='0.05 1.6 0.75' transitionType='\"ANIMATE\"' transitionTime='1.6'/>\n")
    w("    <Background DEF='HostSky' skyColor='%s'/>\n" % ' '.join('%.3f' % x for x in TH._rgb(THEME['ground_bot'])))
    w("    <Viewpoint DEF='Host' description='Opening: the pocket in its host' position='%s' orientation='%s' centerOfRotation='0 0 0' fieldOfView='%s'/>\n" % (v3(s['pos'], 4), v3(look_at(s['pos'], s['tgt']), 6), fnum(s['fov'], 3)))
    w("    <!-- LIGHTS: they light only the PhysicalMaterial fallbacks (seed, armillary); the shaders make their own light. global='true' (x3d-blender-io finding). -->\n")
    w("    <DirectionalLight DEF='Key' global='true' direction='-0.45 -0.62 -0.64' color='0.78 0.85 1' intensity='0.5' ambientIntensity='0.08'/>\n")
    w("    <DirectionalLight DEF='Rim' global='true' direction='0.55 0.15 0.82' color='1 0.5 0.78' intensity='0.35'/>\n")
    w("    <!-- HOST BACKDROP (theme %s): computed per pixel from the view direction; nothing fetched. -->\n" % THEME['name'])
    w("    <Shape DEF='SkyDome'>\n      <Appearance DEF='SkyApp' alphaMode='OPAQUE'>\n        <ComposedShader DEF='SkyShader' language='GLSL'>%s\n          %s\n          %s\n        </ComposedShader>\n      </Appearance>\n" % (
        fields([('uCycle', 'SFFloat', '0.25'), ('uSeed', 'SFFloat', '0.618'), ('uExposure', 'SFFloat', '1'), ('uQ', 'SFInt32', '2')], '          '),
        part('RayVS', 'VERTEX', 'ray.vert.glsl'), part('SkyFS', 'FRAGMENT', 'sky.frag.glsl')))
    w("      <IndexedTriangleSet solid='false' index='%s'>\n        <Coordinate point='%s'/>\n      </IndexedTriangleSet>\n    </Shape>\n" % (' '.join(str(i) for t in kf for i in t), flat(kv, 2)))
    w("    <!-- HOST FRAME: a pewter armillary (the dye owns gold). Ring A passes between the analytic glass and its proxy: the gl_FragDepth composite. -->\n    <Transform DEF='Armillary'>\n")
    ring_tri = 0
    for i, g in enumerate(RINGS):
        tp, tn, ti = torus(g['R'], g['r']); ring_tri += len(ti) // 3
        app = ("<Appearance DEF='Pewter'><PhysicalMaterial DEF='PewterMat' baseColor='%s' emissiveColor='0.03 0.032 0.036' metallic='0.75' roughness='0.36'/>"
               "<ComposedShader DEF='RingShader' language='GLSL'>%s %s %s</ComposedShader></Appearance>" % (v3(PEWTER, 3), fields([('uCycle', 'SFFloat', '0.25'), ('uExposure', 'SFFloat', '1.6'), ('uTint', 'SFVec3f', v3(PEWTER, 3))] + LENSG.fields('RingShader'), '            '),
               part('RingVS', 'VERTEX', 'ring.vert.glsl'), part('RingFS', 'FRAGMENT', 'ring.frag.glsl'))) if i == 0 else "<Appearance USE='Pewter'/>"
        w("      <Transform DEF='%s' rotation='%s'>\n        <Shape>\n          %s\n" % (g['def'], ' '.join(fnum(v, 4) for v in g['rot']), app))
        w("          <IndexedTriangleSet solid='true' index='%s'>\n            <Coordinate point='%s'/>\n            <Normal vector='%s'/>\n          </IndexedTriangleSet>\n        </Shape>\n      </Transform>\n" % (' '.join(str(v) for v in ti), flat(tp, 4), flat(tn, 3)))
    w("    </Transform>\n")
    w("    <!-- THE POCKET: one pocket unit = %g host units. Its sensors report in pocket units; the page flies its Probe through the IMPORTs. -->\n" % SCALE)
    w("    <Transform DEF='PocketXf' scale='%s %s %s'>\n      <Inline DEF='Pocket' url='\"%s\"'/>\n    </Transform>\n" % (fnum(SCALE), fnum(SCALE), fnum(SCALE), pocket_file))
    for e in exports: w("    <IMPORT inlineDEF='Pocket' importedDEF='%s' AS='%s'/>\n" % (e, e))
    w("    <TimeSensor DEF='HostClock' cycleInterval='600' loop='true'/>\n    <ROUTE fromNode='HostClock' fromField='fraction_changed' toNode='SkyShader' toField='uCycle'/>\n")
    w("  </Scene>\n</X3D>\n")
    open(path, 'w', encoding='utf-8', newline='\n').write(''.join(o))
    return {'sky_dome': len(kf), 'armillary': ring_tri}


# ---------------------------------------------------------------- per family
def build_family(F, C, out, portraits=None, root_rel=''):
    fam = C['family']; L = layout(F, C)
    polys = polylines(L); rib = ribbons(L, polys)
    shots, big = make_shots(L)
    tour, checks = make_tour(L, C, shots, big)
    P, U = L['P'], L['U']
    yrs_per_unit = 1.0 / L['K']
    mapping = {
        'radius': 'r(year) = %s + (year - %d) x %s pocket units: %d at the seed edge, %d at r %s just inside the glass (r %s); %s years per pocket unit; time shells every 50 years from %d' % (
            fnum(R0), L['Y0'], fnum(L['K'], 6), L['Y0'], L['TOP'], fnum(R_TOP), fnum(R_GLASS), fnum(yrs_per_unit, 1), L['shell0']),
        'azimuth': 'houses west to east by longitude, sector angle proportional to 2 + people (4 degree gaps), the eldest founder\'s house (%s) at azimuth 0 (+Z)' % L['sectors'][L['fh']]['name'],
        'elevation': 'layout only: inside a house, depth-first order of descent (children by birth, in-laws beside their spouse) from top to bottom',
        'fiber': 'a life runs radially from r(born) to r(died); a spawn arc on the birth shell joins it to a parent; a move bends it along the shell of the move year (dotted when the year is not in the data); a death not in the data is dashed after the last dated event, to the tapestry\'s 60-year end',
        'marriage': 'an arc on the shell of the wedding year between the spouses\' fibers; a close marriage (phi > 0) is doubled and brighter in the dye; an estimated year is dashed and translucent',
        'dye': 'the contract\'s dye colours, stepped by generations of descent from the founders: step k = round(-log2(share)), 0 to %d, drawn as the tapestry\'s colour at the equivalent share 1 - k/8 (deeper = closer; 1/16 or less is floored at the tapestry\'s 1/2 colour); a share of 0 (no descent in the data, in-laws) is ecru' % DYE_K_MAX,
        'root': 'a founder\'s root line from the seed to their birth point is layout only (no years of life)',
        'nesting': 'the pocket sits in its host at scale %g: 1 pocket unit = %g host units; a century = %s host units' % (SCALE, SCALE, fnum(100 * L['K'] * SCALE, 2)),
        'focus': 'on a close shot (CU, MCU) or a pick the subject\'s threads burn brightest, the line back to the founders stays lit (at most %d people: the main line by the larger share of descent, the other parent at each step, then other ancestors) and every other thread dims to a fifth; a bead marks the stop\'s event, ringed when it is a marriage (drawn at the middle of the arc)' % LINE_CAP,
    }
    mapping['short'] = 'Radius = time: %d at the core, %d at the glass, %s years per pocket unit, shells every 50 years. Azimuth: houses west to east, angle = 2 + people. Elevation: order of descent (layout only).' % (L['Y0'], L['TOP'], fnum(yrs_per_unit, 1))
    mapping['lines'] = [mapping['short'], 'Each life a fiber, each marriage an arc on the shell of its year.']
    pocket, host = 'pocket-%s.x3d' % fam, 'hyper-%s.x3d' % fam
    plates = make_plates(L, shots, tour, portraits or {}, root_rel)
    for t in tour:   # v2: the sphere's words (the cards keep the loom's, under card_title)
        t['text'] = stop_text(L, C, t, i0=t['i'] == 0 and t['shot'] == 'Host'); t['card_title'] = t['title']; t['title'] = t['text']['title']
    exports, tri = write_pocket(F, C, L, shots, tour, rib, os.path.join(out, pocket), mapping, plates)
    tri.update(write_host(C, L, shots, exports, pocket, os.path.join(out, host), mapping))
    tri['total_drawn'] = sum(v for k, v in tri.items() if k != 'threads_per_pass')
    # page data
    people = {}
    for pid in L['order']:
        p = P[pid]; pts = []
        for pl in polys:
            if pl['kind'] == 'life' and pl['ids'][0] == pid:
                pts = [r5(q) for q in LENSG.pick_line(pl['pts'])]   # NAV HOOK: every pick_step pocket units, so lens picking can warp it
        ps = present_shot(L, {}, 'Pick', pid, store=False, variant=L['index'][pid])
        people[pid] = dict(i=L['index'][pid], label=p['label'], name=p['name'], house=p['house_name'], born=p['born'], died=p['died'], line=pts,
                           present={k: ps[k] for k in ('pos', 'tgt', 'up', 'fov', 'size', 'frame', 'nav', 'space', 'beat', 'bead', 'composition')}, anchor=label_point(L, pid),
                           lineage=lineage(L, pid))
    sectors = {k: dict(shot=hshot(k), name=v['name'], phi_deg=round(math.degrees(v['phi']), 2), span_deg=round(math.degrees(v['span']), 2), people=v['people'],
                       anchor=r5(sph(v['phi'], 0.0, R_GLASS * 1.03)), lon=v['lon']) for k, v in L['sectors'].items()}
    labels = {t['shot']: stop_labels(L, t, shots) for t in tour}
    doc = dict(version='hyper-view/1', family=fam, name=C['name'], host=host, pocket=pocket, cards='%s.cards.json' % fam, pocket_scale=SCALE, timing=TIMING,
               units=dict(Y0=L['Y0'], top=L['TOP'], R0=R0, K=L['K'], R=R_GLASS, Rp=R_PROXY, Rtop=R_TOP, shell0=L['shell0'], years_per_unit=round(yrs_per_unit, 2)),
               mapping=mapping, sectors=sectors, order_west_to_east=L['keys'], founders=L['founders'], shots=shots, tour=tour, chain_checks=checks, stop_labels=labels,
               people=people, glow=GLOW_W_TIER, picked=dict(colossus_house=big), lens=LENSG.page_block(), dye_legend=dye_legend(C), bead_r=BEAD_R, theme=THEME['slug'],
               theme_dyes={dk: d['color'] for dk, d in C['dyes'].items()}, plates=plates, plate_timing=dict(fade=list(PLATE_FADE), out_s=PLATE_OUT_S, t=PLATE_T),
               dye_steps={str(k): sum(1 for pid in P if dye_rgb(P[pid].get('shares'), C['dyes'])[1] == k) for k in list(range(DYE_K_MAX + 1)) + [None]},
               counts=dict(people=len(P), unions=len(U), close=sum(1 for u in U.values() if u['close']), unions_year_estimated=sum(1 for u in U.values() if u['year_precision'] not in ('year', 'day', 'month')),
                           deaths_not_in_data=sum(1 for p in P.values() if p['died'] is None), moves=sum(1 for p in P.values() if p.get('move')),
                           moves_estimated=sum(1 for p in P.values() if p.get('move') and p['move'].get('estimated')), triangles=tri, ribbon_vertices=len(rib.pos),
                           polylines=len(polys)))
    jp = os.path.join(out, '%s.hyper.json' % fam)
    json.dump(doc, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    geo = dict(version='hyper-geometry/1', family=fam, units='pocket units (radius = time, see mapping)', mapping=mapping, colour_space='display sRGB (the dye as drawn)',
               polylines=[dict(kind=pl['kind'], ids=pl['ids'], uid=pl.get('uid'), color=[round(c, 4) for c in pl['color']], points=[r5(q) for q in pl['pts']],
                               years=[round(y, 2) for y in pl['years']], estimated=pl['est']) for pl in polys],
               seed=dict(center=[0, 0, 0], r=SEED_R, glow_r=SEED_GLOW_R), glass=dict(r=R_GLASS), shells=[dict(year=y, r=round(L['r'](y), 5)) for y in range(L['shell0'], L['TOP'] + 1, 50)])
    gp = os.path.join(out, '%s.geometry.json' % fam)
    json.dump(geo, open(gp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return dict(host=host, pocket=pocket, data=os.path.basename(jp), geometry=os.path.basename(gp), cards='%s.cards.json' % fam, name=C['name'], key=fam, plates=plates,
                tri=tri, chain_ok=all(c['ok'] for c in checks), tour=[(t['key'], t['shot'], t['size'], t['move']) for t in tour], mapping=mapping, counts=doc['counts'])


CHANGES = {   # what changed since build_hypersphere.py 1.0, and why, per build
  'build_3 (1.2, fix round 2: critique ranks 1-3; rank 4 on was not received)': {
    'rest_no_core': 'fiber.frag: with a selection on, the rest discards in the core pass (no colour, no depth), so it cannot cut dark opaque notches across the subject or occlude its glow and the sky; it lives only in the glow pass (screen or additive: it can only add light) at 0.22 (was 0.12), tinted cool slate (0.55 0.62 0.80, 70 percent at full focus) instead of 65 percent grey; while uFocus eases in, the glow pass carries a narrow core-shaped term times (1 - uFocus), so the cores dim out instead of popping (rank 1)',
    'dye_by_generation': 'the dye ramp is indexed by generations of descent, k = round(-log2(total share)) clamped 0..4, drawn as the tapestry CIELAB colour at the equivalent share 1 - k/8; 1/16 or less floors at the tapestry 1/2 colour; ecru only for share 0. Habsburg: 43 lives below 1/16 (Philip IV, Leopold I, Charles II) now gold, not ecru (rank 2)',
    'chroma': 'fiber.frag: the dye is pushed 1.4x away from its luminance before the full-value normalisation (the low-chroma steps had turned cream-white); a dyed core mixes 0.12 (was 0.3) plus tip, pulse and focus heat toward white, so Rothschild red stays red in Host, Wide and House (rank 2)',
    'pewter': 'the armillary is pewter (0.80 0.82 0.88: RingShader uTint and the PhysicalMaterial fallback, DEF Pewter/PewterMat) in every family, so gold belongs to the dye alone (rank 2)',
    'legend': 'header: hue = descended from the founders (deeper = closer), with the drawn ramp as swatches (step per generation) and ecru = no descent in the data; the scale line states the dye rule too (rank 2)',
    'compositions': 'close shots cycle compositions instead of one template: Present descent (high, fiber on the right third, -5 degree roll), rise (low, 24 degrees below, left third, +7 roll), diagonal (27 degree roll, 20 degrees above, centred, longer lens); EyeToEye level and over (other side, 26 degrees above the shell, -6 roll); a tour never repeats a framing on neighbouring close shots, picks vary by person; every close camera stays inside the glass; a Present chooses its side of the house plane and its third: a chain-valid move first, no turn over 150 degrees (gate run 1: a 164 degree turn into Darwin S05 peaked the angular speed), the subject on the other third from the last close shot (across kinds; else the composition whose roll differs most), never the composition of the last Present, then the least turn; a Present with a marriage takes its side axis square to the arc (seen end-on before), widens until its bead sits in BEAD_BOX (clear of the caption, header and rail) and falls to the next composition when the glass stops it (rank 3)',
    'labels': 'page: the bead and its ring are an obstacle for the greedy label placement (the subject label sat on the ring)',
    'native_bind_slowmo': 'page: under a gate\'s slow motion (A.slowmo, set only by the gate) the native Host bind\'s transition is stretched like the Probe flights, so the gate samples X_ITE\'s eased ANIMATE transition densely (gate run 1 failed it twice on 4-5 sensed poses); without slowmo the page is unchanged',
  },
  'build_2 (1.1, fix round 1: critique ranks 1-2)': {   # build 2 (fix round 1): what changed since build_hypersphere.py 1.0, and why (critique ranks 1 and 2; the rest found while checking them)
    'seed': 'the founders\' seed is a limb-darkened sun (SeedCore, seedcore.frag, tone-mapped) instead of a clipped PhysicalMaterial disc; its glow (seed.frag) has the steeper 1/(r^2+e^2)^2 kernel with a cubic window and a black knee, sized so the plunge keeps its black, and draws behind the disc so it never clips; the Breath ColorInterpolator is gone (the shaders breathe with the Clock)',
    'inside': 'shell.frag: with the camera inside the glass the haze body and flow are scaled by uInside (0.35), the shells\' face-on emission by 0.15 and a black knee applies; decided in the shader from the camera radius, so it holds in any host',
    'selection': 'fiber.vert/frag: the subject (uPick), the lineage (uLine[32], written by the page from the generator\'s list) and the rest; the selection acts after the tone map (rest x0.2 core, x0.12 glow, 65 percent grey) and eases with uFocus',
    'bead': 'a subject bead (BeadXf/BeadSwitch/BeadGlow, seed.frag at r 0.02, 2 s breath), ringed for a marriage, placed by the page on arrival at the stop\'s event',
    'dashes': 'an estimated arc is dashed along its length (aAux.x = arc length); keyed on its single year it was all on or all off (the Habsburg 1672 marriage vanished)',
    'indices': 'fnum no longer strips zeros from integers: person index 90 had been written as 9, so close shots and picks of persons 10, 20, ... 100 lit the wrong thread',
    'pose_guard': 'page: after a landing, a stray X_ITE orientationOffset on the Probe (seen intermittently, 45 and 67 degrees) is cleared until the next move or input',
  },
}
XITE_FILES = ['x_ite.min.js', 'x_ite.css', 'LICENSE.md', 'assets/fonts/PT_Sans/PTSans-Regular.woff2', 'assets/fonts/PT_Sans/OFL.txt', 'assets/lib/mikktspace_bg.wasm', 'assets/linetype/linetypes.png',
              'assets/lib/lut_ggx.png', 'assets/lib/lut_charlie.png', 'assets/lib/lut_sheen_E.png']
TYPES = {'.html': 'text/html', '.x3d': 'application/xml', '.json': 'application/json', '.js': 'text/javascript', '.css': 'text/css',
         '.wasm': 'application/wasm', '.woff2': 'font/woff2', '.png': 'image/png', '.svg': 'image/svg+xml', '.md': 'text/markdown', '.txt': 'text/plain'}
SECRET = re.compile(r'AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--view', default=os.path.join(PROTO, 'data', 'loom-view.json'))
    ap.add_argument('--cards', default=os.path.join(PROTO, 'tapestry', 'out'))
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--theme', default=TH.DEFAULT_THEME, choices=sorted(TH.BY_SLUG))
    ap.add_argument('--portraits', default=None, help='the release portraits.json (tools/build_portraits.py); none: no plates')
    ap.add_argument('--root-rel', default='', help='path from these scenes to the release root, for the plate textures')
    a = ap.parse_args()
    out = a.out; os.makedirs(out, exist_ok=True)
    view, fams = load(a.view, a.cards)
    for _k, (_F, _C) in fams.items():   # v2: the theme's tone of each dye (its hue family kept); the cards on disk stay the loom's, byte for byte
        for _d in _C['dyes'].values(): _d['color'] = STYLE_DYES.get(_d.get('hue'), _d['color'])
    portraits = json.load(open(a.portraits, encoding='utf-8'))['people'] if a.portraits else {}
    sri = 'sha384-' + base64.b64encode(hashlib.sha384(open(os.path.join(VENDOR, 'x_ite.min.js'), 'rb').read()).digest()).decode()
    if sri != XITE_SRI: raise SystemExit('vendored X_ITE is not the npm 16.5.1 file the page pins')
    summary = {}; man = dict(version='hyper-manifest/1', built_by=VERSION, asof=view['asof'], xite='16.5.1', theme=THEME['slug'], families=[])
    for key in FAMILIES:
        F, C = fams[key]
        s = build_family(F, C, out, portraits, a.root_rel); summary[key] = s
        shutil.copyfile(os.path.join(a.cards, key + '.cards.json'), os.path.join(out, key + '.cards.json'))
        man['families'].append(dict(key=key, name=s['name'], host=s['host'], pocket=s['pocket'], data=s['data'], cards=s['cards'], geometry=s['geometry']))
    json.dump(man, open(os.path.join(out, 'hyper-manifest.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    page = open(PAGE, encoding='utf-8').read()
    if XITE_SRI not in page or 'name="loom:xite"' not in page: raise SystemExit('page/index.html must pin X_ITE 16.5.1 and name the shipped copy in <meta name="loom:xite">')
    if re.search(r'\beval\s*\(|new\s+Function\b', page): raise SystemExit('page/index.html uses eval or new Function')
    page = TH.fill_page(page, [THEME['slug']], phone=None)   # the standalone page: this theme only (the merged page carries two)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8', newline='\n').write(page)
    files = list(XITE_FILES) + ['assets/components/' + n for n in sorted(os.listdir(os.path.join(VENDOR, 'assets', 'components'))) if n.endswith('.min.js')]
    files += ['assets/images/' + n for n in sorted(os.listdir(os.path.join(VENDOR, 'assets', 'images')))]
    for rel in files:
        dst = os.path.join(out, 'x_ite', rel); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(os.path.join(VENDOR, rel), dst)
    os.makedirs(os.path.join(out, 'lib'), exist_ok=True)   # NAV HOOK: the orbit camera and the lens mirror, plain scripts beside the page
    for fn in ('orbit.js', 'lens.js'):
        js = open(os.path.join(NAV_LIB, fn), encoding='utf-8').read()
        if re.search(r'\beval\s*\(|new\s+Function\b', js): raise SystemExit('lib/%s uses eval or new Function' % fn)
        open(os.path.join(out, 'lib', fn), 'w', encoding='utf-8', newline='\n').write(js)
    own = ['index.html', 'hyper-manifest.json', 'lib/orbit.js', 'lib/lens.js'] + [x for s in summary.values() for x in (s['host'], s['pocket'], s['data'], s['geometry'], s['cards'])]
    problems, living = [], []
    for f in own:
        text = open(os.path.join(out, f), encoding='utf-8').read()
        problems += ['%s: secret-shaped string' % f for _ in SECRET.finditer(text)]
        if f.endswith('.cards.json'):
            for pid, p in json.loads(text)['people'].items():
                if isinstance(p.get('born'), int) and p['born'] >= view['asof'] - 110 and p.get('died') is None: living.append('%s %s' % (f, p.get('name')))
    if problems or living: raise SystemExit('publish gates: %r %r' % (problems, living))
    published = own + ['x_ite/' + r for r in files]
    pub = {p: {'from': p, 'contentType': TYPES.get(os.path.splitext(p)[1], 'application/octet-stream')} for p in published}
    json.dump(pub, open(os.path.join(out, 'publish.json'), 'w', encoding='utf-8'), indent=1, sort_keys=True)
    inputs = {os.path.relpath(p, PROTO): sha_file(p) for p in [os.path.abspath(__file__), LENS_LIB, os.path.join(NAV_LIB, 'orbit.js'), os.path.join(NAV_LIB, 'lens.js'), os.path.join(HERE, 'themes.py'), a.view, PAGE] + [os.path.join(a.cards, k + '.cards.json') for k in FAMILIES] +
              sorted(os.path.join(SRC, n) for n in os.listdir(SRC)) + [os.path.join(VENDOR, 'x_ite.min.js')]}
    outputs = {p: sha_file(os.path.join(out, p)) for p in own + ['publish.json']}
    outputs['x_ite/* (%d files, copied)' % len(files)] = hashlib.sha256(''.join(sha_file(os.path.join(out, 'x_ite', r)) for r in files).encode()).hexdigest()
    rec = dict(built_by=VERSION, theme=THEME['slug'], portraits=dict(file=a.portraits and os.path.basename(a.portraits), sha256=a.portraits and sha_file(a.portraits)),
               plates={k: sum(len(p['items']) for p in s['plates'].values()) for k, s in summary.items()}, python=sys.version.split()[0], deterministic=True, xite_sri=sri, changes=CHANGES, data='loom-view.json (asof %d), rothschild, habsburg, darwin_wedgwood' % view['asof'],
               units=dict(R0=R0, R_TOP=R_TOP, R_GLASS=R_GLASS, R_PROXY=R_PROXY, pocket_scale=SCALE, grammar_to_pocket=G),
               families={k: dict(mapping={m: v for m, v in s['mapping'].items() if m not in ('lines',)}, counts=s['counts'], chain_ok=s['chain_ok'], tour=s['tour'],
                                 files=dict(host=s['host'], pocket=s['pocket'], data=s['data'], geometry=s['geometry'], cards=s['cards'])) for k, s in summary.items()},
               x3d_bytes={s[f]: os.path.getsize(os.path.join(out, s[f])) for s in summary.values() for f in ('host', 'pocket')},
               inputs_sha256=inputs, outputs_sha256=outputs)
    json.dump(rec, open(os.path.join(out, 'receipt.json'), 'w', encoding='utf-8'), indent=1, sort_keys=True, ensure_ascii=False)
    print(json.dumps({k: dict(tri=s['tri']['total_drawn'], chain_ok=s['chain_ok'], tour=s['tour'], counts={c: v for c, v in s['counts'].items() if c != 'triangles'}) for k, s in summary.items()}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
