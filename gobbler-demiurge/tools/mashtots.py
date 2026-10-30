#!/usr/bin/env python3
"""The Mashtots ring: the 36 letters Mesrop Mashtots made for Armenian (traditionally dated 405 AD), Ա (U+0531) to Ք (U+0554), as faceted gold glyphs on a slow ring
around the Heart, outside the Dyson ribcage, in the bird's own coordinates. Օ and Ֆ, added in the Middle Ages, are left out.

Two stages, so the page build needs nothing but Python:
  python3 tools/mashtots.py --extract     (needs fontTools) read Noto Serif Armenian Bold (assets/mashtots/, OFL) and write the outlines as the font has them
                                          (TrueType quadratic contours, font units) to assets/mashtots/glyphs.json, plus letters.json and manifest.json (committed)
  python3 -I tools/mashtots.py            write the fragment alone to data/bird/mashtots-fragment.x3d and print its size (the page build calls build() from layers.py)

build(L, anchor) -> xml: flatten each contour (quadratic and cubic segments to lines), triangulate the letter with its holes (ear clipping, holes bridged to the
outer contour: pure Python), and cut a bevel: the face of the letter is the outline inset by BEVEL and raised by BEVEL_H, and a chamfer band joins it to the outline.
Each face takes one of PALETTE_N shades between a cool shadow and the tenders' warm gold, by its normal against a fixed key light, as the tenders do (this layer is
not baked, and the letters turn). One Shape per letter, because each letter is a Billboard that turns about the ring's axis to face the viewer (so no letter is
ever seen mirrored); the shade palette and the Appearance are shared by DEF/USE. A soft glow reads the letters in order, Ա to Ք, and starts again.
"""
import json, math, os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, 'assets', 'mashtots')
FONT_FILE = 'NotoSerifArmenian-Bold.ttf'
FONT_URL = 'https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSerifArmenian/unhinted/ttf/NotoSerifArmenian-Bold.ttf'
CLDR_URL = 'https://raw.githubusercontent.com/unicode-org/cldr/main/common/rbnf/root.xml'

# the 36 letters in Mashtots' order: (code point, the traditional name as the owner spells it, the classical numeric value)
NAMES = ['Ayb', 'Ben', 'Gim', 'Da', 'Yech', 'Za', 'E', 'Et', 'To', 'Zhe', 'Ini', 'Lyun', 'Khe', 'Tsa', 'Ken', 'Ho', 'Dza', 'Ghat', 'Tche', 'Men', 'Hi', 'Nu', 'Sha', 'Vo',
         'Cha', 'Pe', 'Dje', 'Ra', 'Se', 'Vev', 'Tyun', 'Re', 'Tso', 'Hyun', 'Pyur', 'Ke']
def value(i): return (i % 9 + 1) * 10 ** (i // 9)          # 1..9, 10..90, 100..900, 1000..9000: checked against CLDR's armenian-upper rules in --extract
LETTERS = [(0x531 + i, NAMES[i], value(i)) for i in range(36)]

# ---------------------------------------------------------------- look (bird units; the ribcage is 3.3, the domain rings 4.0 to 5.1, the flywheel 5.7)
RING_R = 4.35                      # the ring's radius about the Sun
RING_AXIS = (0.06, 1.0, 0.30)      # tilted toward the Face camera so the ring opens into an ellipse instead of a line
LETTER_H = 0.50                    # cap height of a letter (scene units)
TURN_S = 360                       # one turn of the ring, seconds
READ_S = 2.5                       # the reading glow stays this long on each letter (the alphabet takes 90 s)
READ_GROW = 1.4                    # the letter being read grows by this much
BEVEL, BEVEL_H = 34, 30            # the chamfer: inset and rise, font units (the cap height of Noto Serif Armenian Bold is about 700)
TOL = 12.0                          # flattening tolerance, font units
QUANT = 3                          # points are written as whole numbers of this many font units (3 units is 0.002 scene units on a letter 0.5 tall)
PALETTE_N = 14
GOLD = (1.0, 0.78, 0.36); COOL = (0.20, 0.30, 0.42)                 # a paler gold than the tenders' (0.96, 0.68, 0.26), which read bronze against the heart's glow; their shadow tint
KEY = (-0.36, 0.46, 0.81)          # the fixed key light in the letter's own frame: from the upper left, mostly in front (the face of a letter sits at 0.81 of full light)

# ---------------------------------------------------------------- stage 1: the font (needs fontTools)
def sha(b): return hashlib.sha256(b).hexdigest()

def extract():
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    import fontTools, unicodedata
    path = os.path.join(ASSETS, FONT_FILE); raw = open(path, 'rb').read(); ft = TTFont(path)
    cmap = ft.getBestCmap(); gs = ft.getGlyphSet(); nm = ft['name']
    glyphs = {}
    for cp, name, val in LETTERS:
        g = cmap[cp]; pen = DecomposingRecordingPen(gs); gs[g].draw(pen)
        glyphs['%04X' % cp] = dict(glyph=g, advance=ft['hmtx'][g][0], ops=[[op, [list(map(int, p)) if p is not None else None for p in pts]] for op, pts in pen.value])
    cldr = open(os.path.join(ASSETS, 'cldr-rbnf-armenian-upper.txt'), encoding='utf-8').read()
    rules = {}
    for line in cldr.splitlines():
        k, _, v = line.partition(':')
        if k.strip().isdigit() and v.strip()[:1] and 0x531 <= ord(v.strip()[0]) <= 0x556: rules[int(k)] = ord(v.strip()[0])
    letters = []
    for i, (cp, name, val) in enumerate(LETTERS):
        assert rules.get(val) == cp, (name, val, rules.get(val))                  # the value against CLDR's own table
        letters.append(dict(order=i + 1, glyph=chr(cp), codepoint='U+%04X' % cp, unicode_name=unicodedata.name(chr(cp)), name=name, value=val))
    os2 = ft['OS/2']
    meta = dict(font=nm.getDebugName(4), version=nm.getDebugName(5), licence='SIL Open Font License 1.1 (OFL.txt beside it)', copyright=nm.getDebugName(0), file=FONT_FILE, url=FONT_URL,
                bytes=len(raw), sha256=sha(raw), units_per_em=ft['head'].unitsPerEm, cap_height=getattr(os2, 'sCapHeight', None), fonttools=fontTools.version,
                numerals=dict(source='CLDR common/rbnf/root.xml, rule set %armenian-upper (excerpt in cldr-rbnf-armenian-upper.txt)', url=CLDR_URL,
                              excerpt_sha256=sha(cldr.encode('utf-8')), checked=len(letters)))
    json.dump(dict(meta=meta, glyphs=glyphs), open(os.path.join(ASSETS, 'glyphs.json'), 'w'), separators=(',', ':'))
    json.dump(dict(about='The 36 letters of Mesrop Mashtots (traditionally 405 AD), in his order, with their classical numeric values. Names as the owner spells them; unicode_name is Unicode\'s.',
                   letters=letters), open(os.path.join(ASSETS, 'letters.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    gj = open(os.path.join(ASSETS, 'glyphs.json'), 'rb').read()
    json.dump(dict(meta, glyphs_json_sha256=sha(gj), script_sha256=sha(open(os.path.abspath(__file__), 'rb').read())), open(os.path.join(ASSETS, 'manifest.json'), 'w'), indent=1)
    print('wrote glyphs.json (%d B), letters.json, manifest.json: %s %s' % (len(gj), meta['font'], meta['version']))

# ---------------------------------------------------------------- stage 2: geometry (pure Python)
def flatten(ops, tol=TOL):
    """pen operations (TrueType quadratic, or cubic) -> closed polygons of float points"""
    polys, cur = [], []
    def quad(p0, p1, p2):
        n = max(1, min(16, int(math.ceil(math.sqrt(math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]) / (2 * tol))))))   # the curve's deviation from its chord
        for k in range(1, n + 1):
            t = k / n; a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            cur.append((a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]))
    def cubic(p0, p1, p2, p3):
        d = max(math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]), math.hypot(p1[0] - 2 * p2[0] + p3[0], p1[1] - 2 * p2[1] + p3[1]))
        n = max(1, min(24, int(math.ceil(math.sqrt(0.75 * d / tol)))))
        for k in range(1, n + 1):
            t = k / n; a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            cur.append(tuple(a * p0[i] + b * p1[i] + c * p2[i] + e * p3[i] for i in range(2)))
    for op, pts in ops:
        if op == 'moveTo': cur = [tuple(pts[0])]
        elif op == 'lineTo': cur.append(tuple(pts[0]))
        elif op == 'curveTo': cubic(cur[-1], pts[0], pts[1], pts[2])
        elif op == 'qCurveTo':
            if pts[-1] is None:                                             # a contour of off-curve points only: start at the midpoint of the last and first
                off = [tuple(p) for p in pts[:-1]]; start = ((off[-1][0] + off[0][0]) / 2, (off[-1][1] + off[0][1]) / 2); cur = [start]; pts = [list(p) for p in off] + [list(start)]
            off = [tuple(p) for p in pts[:-1]]; end = tuple(pts[-1])
            for k, c in enumerate(off):                                     # implied on-curve points halfway between consecutive off-curve points
                nxt = end if k == len(off) - 1 else ((c[0] + off[k + 1][0]) / 2, (c[1] + off[k + 1][1]) / 2)
                quad(cur[-1], c, nxt)
        elif op in ('closePath', 'endPath'):
            if len(cur) > 1 and math.hypot(cur[0][0] - cur[-1][0], cur[0][1] - cur[-1][1]) < 1e-6: cur.pop()
            if len(cur) >= 3: polys.append(clean(cur))
            cur = []
    return [p for p in polys if len(p) >= 3]

def clean(poly, eps=0.6):
    """drop repeated points and points on a straight line (within eps font units of the chord)"""
    out = []
    for p in poly:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6: out.append(p)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < 1e-9 or abs((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / L < eps:
                out.pop(i); changed = True; break
    return out

def area(poly): return 0.5 * sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c

def nest(polys):
    """-> [(outer, [holes])]: a contour inside an odd number of others is a hole of the smallest one around it. Outers are made counter-clockwise, holes clockwise."""
    depth, parent = [], []
    for i, p in enumerate(polys):
        enc = [j for j, q in enumerate(polys) if j != i and inside(p[0], q)]
        depth.append(len(enc)); parent.append(min(enc, key=lambda j: abs(area(polys[j]))) if enc else None)
    out = {}
    for i, p in enumerate(polys):
        if depth[i] % 2 == 0: out[i] = (p if area(p) > 0 else p[::-1], [])
    for i, p in enumerate(polys):
        if depth[i] % 2 == 1: out[parent[i]][1].append(p if area(p) < 0 else p[::-1])
    return [out[k] for k in sorted(out)]

def _cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
def _segs_cross(p1, p2, q1, q2):
    d1, d2, d3, d4 = _cross(q1, q2, p1), _cross(q1, q2, p2), _cross(p1, p2, q1), _cross(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and abs(d1) > 1e-9 and abs(d2) > 1e-9 and abs(d3) > 1e-9 and abs(d4) > 1e-9

def bridge(P, outer, holes):
    """merge the holes into the outer ring (lists of indices into P) by cutting a bridge from each hole's rightmost vertex to the nearest outer vertex it can see"""
    ring = list(outer); holes = sorted(holes, key=lambda h: -max(P[i][0] for i in h))
    for hi, h in enumerate(holes):
        m = max(range(len(h)), key=lambda k: (P[h[k]][0], -P[h[k]][1])); M = P[h[m]]
        edges = [(ring[k - 1], ring[k]) for k in range(len(ring))] + [(g[k - 1], g[k]) for g in holes[hi:] for k in range(len(g))]
        best = None
        for k in sorted(range(len(ring)), key=lambda k: (P[ring[k]][0] - M[0]) ** 2 + (P[ring[k]][1] - M[1]) ** 2):
            V = P[ring[k]]
            if any(_segs_cross(M, V, P[a], P[b]) for a, b in edges if h[m] not in (a, b) and ring[k] not in (a, b)): continue
            best = k; break
        assert best is not None, 'no bridge'
        hr = h[m:] + h[:m]
        ring = ring[:best + 1] + hr + [hr[0], ring[best]] + ring[best + 1:]
    return ring

def earclip(P, ring):
    """triangulate a simple (bridged) counter-clockwise ring of indices into P"""
    V = list(ring); tris = []; guard = 0
    def is_ear(i):
        a, b, c = V[i - 1], V[i], V[(i + 1) % len(V)]; A, B, C = P[a], P[b], P[c]
        if _cross(A, B, C) <= 1e-9: return False
        for j in V:
            if j in (a, b, c): continue
            p = P[j]
            if p in (A, B, C): continue                                    # a bridge repeats a vertex: its twin is not inside
            if _cross(A, B, p) >= 0 and _cross(B, C, p) >= 0 and _cross(C, A, p) >= 0: return False
        return True
    while len(V) > 3 and guard < 100000:
        guard += 1
        for i in range(len(V)):
            if is_ear(i):
                tris.append((V[i - 1], V[i], V[(i + 1) % len(V)])); V.pop(i); break
        else:                                                              # nothing clips cleanly (rounding): take the most convex corner and go on
            i = max(range(len(V)), key=lambda i: _cross(P[V[i - 1]], P[V[i]], P[V[(i + 1) % len(V)]]))
            tris.append((V[i - 1], V[i], V[(i + 1) % len(V)])); V.pop(i)
    if len(V) == 3: tris.append(tuple(V))
    return [t for t in tris if abs(_cross(P[t[0]], P[t[1]], P[t[2]])) > 1e-6]

def inset(poly, d, others=()):
    """each vertex moved d to the inside (the left of a counter-clockwise outer, the left of a clockwise hole), mitred, the miter clamped at 2.2 d, and never more than
    0.42 of the distance to the nearest stroke edge that is not its own neighbour (so a thin serif or a hairline is not turned inside out)"""
    n = len(poly); arc = [0.0]
    for i in range(1, n + 1): arc.append(arc[-1] + math.hypot(poly[i % n][0] - poly[i - 1][0], poly[i % n][1] - poly[i - 1][1]))
    per = arc[-1]; out = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = _n2((b[0] - a[0], b[1] - a[1])); e2 = _n2((c[0] - b[0], c[1] - b[1]))
        n1 = (-e1[1], e1[0]); n2 = (-e2[1], e2[0]); m = _n2((n1[0] + n2[0], n1[1] + n2[1]))
        cs = max(0.45, m[0] * n1[0] + m[1] * n1[1]); L = min(2.2 * d, d / cs)
        near = 1e9
        for j in range(n):                                                 # the stroke's own thickness here: edges of this ring farther along than 3 d either way
            da = abs(arc[j] - arc[i]); da = min(da, per - da)
            if da < 3 * d: continue
            near = min(near, _segdist(b, poly[j], poly[(j + 1) % n]))
        for q in others:
            for j in range(len(q)): near = min(near, _segdist(b, q[j - 1], q[j]))
        L = min(L, 0.42 * near)
        out.append((b[0] + m[0] * L, b[1] + m[1] * L))
    return out
def _segdist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]; l2 = vx * vx + vy * vy
    t = 0.0 if l2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)
def _n2(v): l = math.hypot(v[0], v[1]) or 1.0; return (v[0] / l, v[1] / l)
def _n3(v): l = math.sqrt(sum(x * x for x in v)) or 1.0; return tuple(x / l for x in v)

def shade_index(n):
    """the face's shade, 0 (cool shadow) .. PALETTE_N - 1 (full gold), by its normal against the key light"""
    k = _n3(KEY); lit = max(0.0, sum(a * b for a, b in zip(_n3(n), k)))
    return max(0, min(PALETTE_N - 1, int(round(lit * (PALETTE_N - 1)))))
def palette():
    out = []
    for s in range(PALETTE_N):
        lit = s / (PALETTE_N - 1); k = 0.52 + 0.58 * lit
        out.append(tuple(min(1.0, GOLD[i] * k + COOL[i] * (1.0 - lit) * 0.50) for i in range(3)))
    return out

def glyph_mesh(ops):
    """one letter: points (x, y, z in font units, rounded), faces (index lists) and a shade per face"""
    polys = flatten(ops); groups = nest(polys)
    P, F, S = [], [], []
    cap = (0, 0, 1)
    for outer, holes in groups:
        rings = []
        for poly in [outer] + holes:
            base = len(P); ins = inset(poly, BEVEL, [q for q in [outer] + holes if q is not poly])
            P += [(x, y, 0.0) for x, y in poly] + [(x, y, float(BEVEL_H)) for x, y in ins]
            rings.append((base, len(poly)))
        for base, n in rings:                                              # the chamfer band: outline (z 0) up to the inset face (z BEVEL_H)
            for i in range(n):
                a, b = base + i, base + (i + 1) % n; A, B = P[a], P[b]
                e = _n2((B[0] - A[0], B[1] - A[1])); out = (e[1], -e[0])                       # outward (the right of the walking direction)
                F.append((a, b, b + n, a + n)); S.append(shade_index((out[0] * BEVEL_H, out[1] * BEVEL_H, BEVEL)))
        P2 = {}; idx2d = []
        for base, n in rings: idx2d.append([base + n + i for i in range(n)])                # the cap is cut from the inset rings (same topology as the outline)
        flat = {i: (P[i][0], P[i][1]) for r in idx2d for i in r}
        ring = bridge(flat, idx2d[0], idx2d[1:])
        tris = earclip(flat, ring)
        for t in tris:
            if _cross(flat[t[0]], flat[t[1]], flat[t[2]]) <= 0: continue           # a sliver turned over where a miter pinched (a few in all 36 letters): dropped
            F.append(t); S.append(shade_index(cap))
    return P, F, S

def letter_shape(ops, first, scale):
    P, F, S = glyph_mesh(ops)
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    pts = ' '.join('%d %d %d' % (round((x - cx) / QUANT), round((y - cy) / QUANT), round(z / QUANT)) for x, y, z in P)     # whole numbers of QUANT font units: small and gzip-friendly
    ci = ' '.join(' '.join(map(str, f_)) + ' -1' for f_ in F)
    col = ("<Color DEF='MashtotsShades' color='%s'/>" % ' '.join('%.3f %.3f %.3f' % c for c in palette())) if first else "<Color USE='MashtotsShades'/>"
    app = "<Appearance DEF='MashtotsLook'/>" if first else "<Appearance USE='MashtotsLook'/>"
    scale *= QUANT
    shp = ("<Transform scale='%s %s %s'><Shape>%s<IndexedFaceSet solid='false' colorPerVertex='false' coordIndex='%s' colorIndex='%s'>%s<Coordinate point='%s'/></IndexedFaceSet></Shape></Transform>"
           % (_f(scale), _f(scale), _f(scale), app, ci, ' '.join(map(str, S)), col, pts))
    return shp, dict(points=len(P), faces=len(F), w=(max(xs) - min(xs)) * scale / QUANT, h=(max(ys) - min(ys)) * scale / QUANT)

def _f(x): return ('%.4g' % x) if abs(x) >= 1e-4 else '0'

def load_glyphs():
    return json.load(open(os.path.join(ASSETS, 'glyphs.json')))

def build(L, anchor=None, sun=None):
    """the ring as an X3D fragment for the Loom group (bird coordinates). L is the layers module (its helpers: v3, f, glow, basis_rotation, lines_shape, circle)."""
    G = load_glyphs(); sun = sun or L.SUN
    cap = G['meta'].get('cap_height') or 700; scale = LETTER_H / cap
    A = L.norm(RING_AXIS); z = (0, 0, 1); w = L.norm(L.sub(z, L.mul(A, sum(a * b for a, b in zip(A, z))))); u = L.cross(A, w)
    ax, ang = L.basis_rotation(u, A, w)
    out = ["<Transform DEF='MashtotsRing' center='%s'>" % L.v3(sun),
           L.lines_shape([L.circle(sun, A, RING_R, 180)], (0.85, 0.66, 0.30), transparency=0.55),          # the track the letters ride on
           "<Transform translation='%s' rotation='%s %s'>" % (L.v3(sun), L.v3(ax), L.f(ang))]
    stats = []; slots = []
    for i, (cp, name, val) in enumerate(LETTERS):
        th = 2 * math.pi * i / 36; p = (RING_R * math.sin(th), 0.0, RING_R * math.cos(th)); slots.append(p)
        shp, st = letter_shape(G['glyphs']['%04X' % cp]['ops'], i == 0, scale); stats.append(st)
        out.append("<Transform DEF='Mashtots%02d' translation='%s'><Billboard axisOfRotation='0 1 0'>%s</Billboard></Transform>" % (i + 1, L.v3(p), shp))
    # the reading glow: it rests on each letter for most of READ_S, then glides to the next, Ա to Ք and round again
    keys, vals = [], []
    for i in range(36):
        a = slots[i]; b = slots[(i + 1) % 36]
        keys += [i / 36, (i + 0.78) / 36]; vals += [a, a]
    keys.append(1.0); vals.append(slots[0])
    out.append("<Transform DEF='MashtotsReader' translation='%s'>%s</Transform>" % (L.v3(slots[0]), L.glow((0, 0, 0), LETTER_H * 1.6, (1.0, 0.80, 0.42))))
    grow = []                                                              # and the letter being read stands READ_GROW times taller while the glow rests on it
    for i in range(36):
        if i == 0: k, v = [0, 0.78 / 36, 1 / 36, 35.78 / 36, 1], [READ_GROW, READ_GROW, 1, 1, READ_GROW]
        else: k, v = [0, (i - 0.22) / 36, i / 36, (i + 0.78) / 36, (i + 1) / 36, 1], [1, 1, READ_GROW, READ_GROW, 1, 1]
        grow.append("<PositionInterpolator DEF='MashtotsGrow%02d' key='%s' keyValue='%s'/>" % (i + 1, ' '.join('%.5f' % x for x in k), ', '.join('%s %s %s' % ((L.f(x),) * 3) for x in v)))
        grow.append("<ROUTE fromNode='MashtotsReadClock' fromField='fraction_changed' toNode='MashtotsGrow%02d' toField='set_fraction'/><ROUTE fromNode='MashtotsGrow%02d' fromField='value_changed' toNode='Mashtots%02d' toField='set_scale'/>" % (i + 1, i + 1, i + 1))
    out.append("</Transform></Transform>")
    out.append("<TimeSensor DEF='MashtotsClock' cycleInterval='%d' loop='true'/><OrientationInterpolator DEF='MashtotsSpin' key='0 0.5 1' keyValue='%s 0, %s -3.14159, %s -6.28318'/>"
               "<TimeSensor DEF='MashtotsReadClock' cycleInterval='%s' loop='true'/><PositionInterpolator DEF='MashtotsRead' key='%s' keyValue='%s'/>"
               "<ROUTE fromNode='MashtotsClock' fromField='fraction_changed' toNode='MashtotsSpin' toField='set_fraction'/>"
               "<ROUTE fromNode='MashtotsSpin' fromField='value_changed' toNode='MashtotsRing' toField='set_rotation'/>"
               "<ROUTE fromNode='MashtotsReadClock' fromField='fraction_changed' toNode='MashtotsRead' toField='set_fraction'/>"
               "<ROUTE fromNode='MashtotsRead' fromField='value_changed' toNode='MashtotsReader' toField='set_translation'/>"
               % (TURN_S, L.v3(A), L.v3(A), L.v3(A), L.f(36 * READ_S), ' '.join('%.5f' % k for k in keys), ', '.join(L.v3(v) for v in vals)))
    out += grow
    if anchor:
        anchor('mashtots', 'Mashtots ring', 'the 36 letters Mesrop Mashtots made for Armenian (405 AD), Ա (1) to Ք (9000), from Noto Serif Armenian; a glow reads them in order', L.add(sun, L.mul(u, RING_R * 1.02)))      # on the ring's right-hand edge: a ring turned about its own axis keeps its place, so a fixed tag stays on it
    xml = ''.join(out)
    build.stats = dict(letters=36, points=sum(s['points'] for s in stats), faces=sum(s['faces'] for s in stats), bytes=len(xml.encode('utf-8')),
                       max_w=round(max(s['w'] for s in stats), 3), max_h=round(max(s['h'] for s in stats), 3))
    return xml

if __name__ == '__main__':
    if '--extract' in sys.argv: extract(); sys.exit(0)
    sys.path.insert(0, HERE); import layers, gzip
    x = build(layers); out = os.path.join(ROOT, 'data', 'bird'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'mashtots-fragment.x3d'), 'w', encoding='utf-8').write(x)
    print(json.dumps(dict(build.stats, gz_bytes=len(gzip.compress(x.encode('utf-8'), 9, mtime=0)))))
