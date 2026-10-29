"""The Armenian knot: what the four shuttles weave (layers.py calls `build`; plain X3D 4.0, no Script).

Each ornament is four closed strands, one per shuttle, rotated copies of one base curve in a disc round the heart:
    theta = 2 pi t,  r = R0 + R1 cos(L theta),  phi = theta + g sin(L theta) + a (r - R0) / R1 + k 2 pi / (4 L)
With L = 2 the four strands make the eight swirling arms of an arevakhach (the Armenian eternity sign, a "sun cross"; the bird's Sun
is its hub); with L = 3 a twelve-armed one; with g = a = 0 and a small R1 a four-strand plait bent into a ring, the interlaced border
of a carpet laid round a medallion. Over and under come from a checkerboard colouring of the diagram (a strand goes over where the
region ahead of it and to its left is dark), which makes every strand alternate over, under, over; a strand lifts toward the viewer
where it goes over and sinks where it goes under. A vertex shader evaluates the curve, its lift (from the list of crossings) and the
ribbon's width, so the file carries one shared strip of sample numbers, a few numbers per strand and the shuttles' paths. The thread
a shuttle has laid stays (the shader discards what lies ahead of it); a finished ornament holds, dissolves, and the next one, from
the next seed, begins."""
import math, random

N = 600                    # samples along a strand (one strip of sample numbers, shared by every strand; the shader bends it into shape)
NS = 150                   # samples of a shuttle's path (linear between them; within a few pixels of the thread's end at the heart stop)
HW, LIFT = 0.06, 0.05      # half width of the thread, and how far it moves toward the eye where it goes over (along the line of sight, so
                           # the ribbon stays flat in the picture and only its depth changes: no kinks where it climbs over another)
TW, TH, TF = 150.0, 24.0, 10.0   # seconds: weaving, holding the finished knot, dissolving while the shuttles cross to the next start
NORMAL = (0.5, 0.3, 2.3)   # the disc faces the Heart stop's camera (boot.js STOPS[2]: the Sun + (0.5, 0.3, 2.3))
# thread colours: gold, pomegranate (nur), the router's blue from the wing, apricot (tsiran); besides the gold, the red, blue and apricot of the Armenian flag
COLOURS = [(1.0, 0.80, 0.40), (0.86, 0.13, 0.19), (0.30, 0.62, 1.0), (1.0, 0.60, 0.30)]

FAMILIES = [                # (name, R0, R1, L, g, a, B); sizes in scene units (the Sun's radius is 0.36, the ribcage's 3.3); B spends samples on the curls
    ('arevakhach, eight arms', 1.75, 0.85, 2, -0.95, 1.1, 0.65),
    ('plaited border ring', 1.96, 0.34, 5, 0.0, 0.0, 0.1),
    ('arevakhach, twelve arms', 1.75, 0.85, 3, -0.62, 1.1, 0.75),
]

def ornaments(seed, K=3):
    """K ornaments in the order they are woven: ornament j is family j with a small jitter drawn from seed + j (the next seed)"""
    out = []
    for j in range(K):
        nm, R0, R1, L, g, a, B = FAMILIES[j % len(FAMILIES)]
        r = random.Random((seed + j) * 7919 + 101)
        if g: g *= 1 + r.uniform(-0.06, 0.06); a *= 1 + r.uniform(-0.15, 0.15)
        else: R1 *= 1 + r.uniform(-0.08, 0.08)
        out.append(dict(name=nm, R0=R0, R1=round(R1, 4), L=L, g=round(g, 4), a=round(a, 4), B=B, seed=seed + j))
    return out

def point(o, k, t):
    th = 2 * math.pi * t; c = math.cos(o['L'] * th); r = o['R0'] + o['R1'] * c
    ph = th + o['g'] * math.sin(o['L'] * th) + o['a'] * (r - o['R0']) / o['R1'] + k * 2 * math.pi / (4 * o['L'])
    return (r * math.cos(ph), r * math.sin(ph))

def tparam(o, u):
    """the strip's sample u (uniform) to the curve's t: samples crowd where the strand curls at its tips (t = m / L), dt/du = 1 - B there"""
    return u - o['B'] * math.sin(2 * math.pi * o['L'] * u) / (2 * math.pi * o['L'])

def polyline(o, k, n, off=0.0):
    return [point(o, k, (i + off) / n) for i in range(n)]

def _seg_x(p, q, r, s):
    """intersection of segments p-q and r-s: (u, v) along each, or None"""
    d = (q[0] - p[0]) * (s[1] - r[1]) - (q[1] - p[1]) * (s[0] - r[0])
    if abs(d) < 1e-14: return None
    u = ((r[0] - p[0]) * (s[1] - r[1]) - (r[1] - p[1]) * (s[0] - r[0])) / d
    v = ((r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])) / d
    if 0 <= u < 1 and 0 <= v < 1: return (u, v)
    return None

def crossings(o, n=1440):
    """every crossing of the four strands (each strand with itself too): dicts with the two strands, their parameters, the point,
    the directions there, and which strand goes over (by the checkerboard rule)"""
    OFF = 0.3719                                                       # sample off the symmetric points, so no crossing falls on a shared corner
    P = [polyline(o, k, n, OFF) for k in range(4)]
    segs = [(k, i, P[k][i], P[k][(i + 1) % n]) for k in range(4) for i in range(n)]
    cell = 0.08; grid = {}
    for si, (k, i, a, b) in enumerate(segs):
        for gx in range(int(math.floor(min(a[0], b[0]) / cell)), int(math.floor(max(a[0], b[0]) / cell)) + 1):
            for gy in range(int(math.floor(min(a[1], b[1]) / cell)), int(math.floor(max(a[1], b[1]) / cell)) + 1):
                grid.setdefault((gx, gy), []).append(si)
    found = {}
    for lst in grid.values():
        for x in range(len(lst)):
            for y in range(x + 1, len(lst)):
                s1, s2 = lst[x], lst[y]
                if (s1, s2) in found: continue
                k1, i1, a1, b1 = segs[s1]; k2, i2, a2, b2 = segs[s2]
                if k1 == k2 and (abs(i1 - i2) <= 1 or abs(i1 - i2) >= n - 1): continue          # neighbours on one strand share an end
                uv = _seg_x(a1, b1, a2, b2)
                if uv: found[(s1, s2)] = uv
    out = []
    for (s1, s2), (u, v) in found.items():
        k1, i1, a1, b1 = segs[s1]; k2, i2, a2, b2 = segs[s2]
        X = (a1[0] + u * (b1[0] - a1[0]), a1[1] + u * (b1[1] - a1[1]))
        d1 = _unit((b1[0] - a1[0], b1[1] - a1[1])); d2 = _unit((b2[0] - a2[0], b2[1] - a2[1]))
        out.append(dict(ka=k1, ta=((i1 + OFF + u) / n) % 1.0, kb=k2, tb=((i2 + OFF + v) / n) % 1.0, p=X, da=d1, db=d2))
    for c in out:
        c['a_over'] = _a_over(c, segs)
    return out

def _unit(d):
    l = math.hypot(d[0], d[1]) or 1.0
    return (d[0] / l, d[1] / l)

def _parity(q, segs):
    """checkerboard colour of the region holding q: how many strand segments a ray from q crosses, mod 2"""
    ang = 0.7853981 + 0.1234567; e = (math.cos(ang), math.sin(ang)); far = (q[0] + 10 * e[0], q[1] + 10 * e[1]); n = 0
    for (_, _, a, b) in segs:
        if _seg_x(q, far, a, b): n += 1
    return n & 1

def _a_over(c, segs, eps=2e-4):
    """strand a goes over iff the quadrant ahead of a and to its left is dark (parity 1). Successive crossings along a strand then
    alternate (the left-hand region changes colour each time a strand is crossed), and at each crossing exactly one strand is over"""
    da, db = c['da'], c['db']
    left = db if da[0] * db[1] - da[1] * db[0] > 0 else (-db[0], -db[1])
    q = (c['p'][0] + eps * (da[0] + left[0]), c['p'][1] + eps * (da[1] + left[1]))
    return _parity(q, segs) == 1

def strand_crossings(cs, k, angles=False):
    """(t, +1 over / -1 under) along strand k, sorted; with angles=True also the angle between the two strands there"""
    out = []
    for c in cs:
        ang = math.acos(min(1.0, abs(c['da'][0] * c['db'][0] + c['da'][1] * c['db'][1])))
        if c['ka'] == k: out.append((c['ta'], 1 if c['a_over'] else -1) + ((ang,) if angles else ()))
        if c['kb'] == k: out.append((c['tb'], -1 if c['a_over'] else 1) + ((ang,) if angles else ()))
    return sorted(out)

def speed(o, t, e=1e-5):
    a, b = point(o, 0, t - e), point(o, 0, t + e)
    return math.hypot(b[0] - a[0], b[1] - a[1]) / (2 * e)

def lift_profile(o, cs=None):
    """the base strand's lift as a function of t, in units of LIFT (+1 = over, toward the viewer), the sign each strand multiplies it
    by (the four strands are rotations of one; a rotation keeps or swaps the checkerboard colours), the base crossings and the half
    window round each crossing in which the strand stays fully up or down: the stretch where the two ribbons overlap, HW cot(angle / 2)
    along the strand, long where two strands cross at a shallow angle, with a margin, and never more than 45 per cent of the way to
    the next crossing. Between the windows the strand turns over smoothly (smoothstep); the shader does exactly this"""
    cs = cs if cs is not None else crossings(o)
    base = strand_crossings(cs, 0, angles=True)
    assert base and len(base) % 2 == 0, 'a strand crosses an even number of times'
    for (t0, s0, _), (t1, s1, _) in zip(base, base[1:] + base[:1]): assert s0 == -s1, 'not alternating at t=%.4f' % t0
    flips = []
    for k in range(4):
        sk = strand_crossings(cs, k); assert len(sk) == len(base)
        fl = sk[0][1] * base[0][1]
        for (ta, sa, _), (tb, sb) in zip(base, sk): assert abs(ta - tb) < 2e-3 and sa * fl == sb, 'strand %d is not a rotated copy' % k
        flips.append(fl)
    ts = [c[0] for c in base]; ss = [c[1] for c in base]; m = len(ts)
    gap = lambda j, d: ((ts[(j + d) % m] - ts[j]) * d) % 1.0
    hs = [round(min(1.3 * HW / math.tan(max(0.05, base[j][2]) / 2) / speed(o, ts[j]), 0.45 * gap(j, 1), 0.45 * gap(j, -1)), 5) for j in range(m)]
    def lift(t):
        t %= 1.0
        j = max([x for x in range(m) if ts[x] <= t], default=m - 1)       # the last crossing at or before t (cyclic)
        t0 = ts[j]; t1 = ts[(j + 1) % m] + (1 if j == m - 1 else 0)
        if t < t0: t += 1
        a, b = t0 + hs[j], t1 - hs[(j + 1) % m]
        u = min(1.0, max(0.0, (t - a) / (b - a)))
        return ss[j] * (1 - 2 * u * u * (3 - 2 * u))
    lift.windows = hs
    return lift, flips, [(c[0], c[1]) for c in base]

def disc_rotation(norm_fn, cross_fn):
    """axis-angle that turns local +Z onto NORMAL"""
    n = norm_fn(NORMAL); z = (0.0, 0.0, 1.0); ax = cross_fn(z, n); s = math.hypot(*ax); ang = math.atan2(s, n[2])
    return (ax[0] / s, ax[1] / s, ax[2] / s), ang

VS = """<ShaderPart DEF='WeaveVS' type='VERTEX'><![CDATA[data:x-shader/x-vertex,#version 300 es
precision highp float;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform vec3 w;
uniform vec4 P;
uniform vec4 Q;
uniform vec3 S;
uniform float X[32];
uniform float H[32];
in vec4 x3d_Vertex;
out float vu;
out float vs;
out float vl;
out vec3 vP;
vec2 crv(float t) {
  float th = 6.2831853 * t, r = P.x + P.y * cos(Q.x * th);
  float ph = th + P.z * sin(Q.x * th) + P.w * (r - P.x) / P.y + Q.y * 6.2831853 / (4.0 * Q.x);
  return r * vec2(cos(ph), sin(ph));
}
float tp(float u) { return u - S.z * sin(6.2831853 * Q.x * u) / (6.2831853 * Q.x); }
float lift(float t) {
  int n = int(S.x);
  float t0 = X[n - 1] - 1.0, h0 = H[n - 1], t1 = X[0], h1 = H[0], s = S.y * (n %% 2 == 0 ? -1.0 : 1.0);
  for (int j = 0; j < 32; j++) {
    if (j >= n || X[j] > t) break;
    t0 = X[j]; h0 = H[j]; t1 = j + 1 < n ? X[j + 1] : X[0] + 1.0; h1 = j + 1 < n ? H[j + 1] : H[0]; s = S.y * (j %% 2 == 0 ? 1.0 : -1.0);
  }
  return s * (1.0 - 2.0 * smoothstep(t0 + h0, t1 - h1, t));
}
void main() {
  float u = x3d_Vertex.x / %(N)s.0, t = tp(u);
  vu = u; vs = x3d_Vertex.y; vl = lift(t) * Q.z;
  vec2 c = crv(t), d = normalize(crv(t + 0.0004) - crv(t - 0.0004));
  vec4 p = x3d_ModelViewMatrix * vec4(c + vec2(-d.y, d.x) * %(HW)s * vs, 0.0, 1.0);
  vP = p.xyz;
  p.xyz += normalize(-p.xyz) * vl * %(LIFT)s;
  gl_Position = abs(w.x - Q.w) < 0.5 ? x3d_ProjectionMatrix * p : vec4(2.0, 2.0, 2.0, 1.0);
}
]]></ShaderPart>"""
FS = """<ShaderPart DEF='WeaveFS' type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,#version 300 es
precision highp float;
uniform vec3 w;
uniform vec3 col;
in float vu;
in float vs;
in float vl;
in vec3 vP;
out vec4 x3d_FragColor;
void main() {
  if (vu > w.y) discard;
  if (fract(sin(dot(floor(gl_FragCoord.xy), vec2(12.9898, 78.233))) * 43758.5453) > w.z) discard;
  vec3 n = normalize(cross(dFdx(vP), dFdy(vP)));
  float k = 0.62 + 0.5 * max(0.0, dot(n, normalize(vec3(-0.4, 0.7, 0.6))));
  k *= vs < 0.0 ? 1.08 : 0.74;
  k *= 0.82 + 0.22 * vl;
  vec3 c = mix(col * k, vec3(0.06, 0.03, 0.01), smoothstep(0.62, 0.92, abs(vs)));
  float hot = exp(-(w.y - vu) * 55.0) * step(w.y, 0.9999);
  c = mix(c, vec3(1.0, 0.86, 0.62) * 1.25, 0.85 * hot);
  x3d_FragColor = vec4(min(c, vec3(1.0)), 1.0);
}
]]></ShaderPart>"""

def build(L, seed=4):
    """the Weave group for layers.py (L = the layers module, for its number formatting and point sprites): returns (xml, info)"""
    f, v3 = L.f, L.v3
    orns = ornaments(seed); K = len(orns); TT = TW + TH + TF
    ax, ang = disc_rotation(L.norm, L.cross)
    X = ["<Switch DEF='Weave' whichChoice='0'><Transform DEF='Knot' translation='%s' rotation='%s %s'>" % (v3(L.SUN), v3(ax), f(ang))]
    info = []
    for j, o in enumerate(orns):
        lift, flips, base = lift_profile(o)
        assert len(base) <= 32
        info.append(dict(o, crossings_per_strand=len(base), flips=flips))
        xs = ' '.join('%.5f' % t for t, _ in base)
        for k in range(4):
            sh = ("<ComposedShader DEF='WeaveSh%d_%d' language='GLSL'><field name='w' type='SFVec3f' accessType='inputOutput' value='0 1 1'/>"
                  "<field name='P' type='SFVec4f' accessType='initializeOnly' value='%s %s %s %s'/><field name='Q' type='SFVec4f' accessType='initializeOnly' value='%d %d %d %d'/>"
                  "<field name='S' type='SFVec3f' accessType='initializeOnly' value='%d %d %s'/><field name='X' type='MFFloat' accessType='initializeOnly' value='%s'/><field name='H' type='MFFloat' accessType='initializeOnly' value='%s'/>"
                  "<field name='col' type='SFColor' accessType='initializeOnly' value='%s'/>%s%s</ComposedShader>"
                  % (j, k, f(o['R0']), f(o['R1']), f(o['g']), f(o['a']), o['L'], k, flips[k], j, len(base), base[0][1], f(o['B']), xs, ' '.join('%.5f' % h for h in lift.windows), v3(COLOURS[k]),
                     VS % dict(N=N, HW=HW, LIFT=LIFT) if (j, k) == (0, 0) else "<ShaderPart USE='WeaveVS'/>", FS if (j, k) == (0, 0) else "<ShaderPart USE='WeaveFS'/>"))
            # one strip of sample numbers for all twelve strands: (sample, side, 0); the shader puts each where its own curve is
            geo = ("<TriangleStripSet DEF='WeaveStrip' solid='false' stripCount='%d'><Coordinate point='%s'/></TriangleStripSet>" % (2 * (N + 1), ' '.join('%d -1 0 %d 1 0' % (i, i) for i in range(N + 1)))
                   if (j, k) == (0, 0) else "<TriangleStripSet USE='WeaveStrip'/>")
            X.append("<Shape bboxCenter='0 0 0' bboxSize='5.4 5.4 0.2'><Appearance>%s</Appearance>%s</Shape>" % (sh, geo))
    # the shuttles: each rides its own strand (a rotation of the base path) at the thread's end, hovering a little over the cloth
    keys, vals = [], []
    for j, o in enumerate(orns):
        s = j / K
        for i in range(NS + 1):
            keys.append(s + (TW / TT) * (i / NS) / K); x, y = point(o, 0, tparam(o, i / NS)); vals.append((x, y))
        keys.append(s + ((TW + TH) / TT) / K); vals.append(vals[-1])                                  # hold the finished knot
    keys.append(1.0); vals.append(vals[0])                                                             # cross to the next start while the knot dissolves
    rk, rv = [], [[] for _ in range(4)]
    for j, o in enumerate(orns):
        for kk in (j / K, (j + (TW + TH) / TT) / K):
            rk.append(kk)
            for k in range(4): rv[k].append(k * 2 * math.pi / (4 * o['L']))
    rk.append(1.0)
    for k in range(4): rv[k].append(rv[k][0])
    for k in range(4):
        X.append("<Transform DEF='ShuttleTurn%d' rotation='0 0 1 %s'><Transform DEF='Shuttle%d' translation='%s 0.07'>%s%s</Transform></Transform>"
                 % (k, f(rv[k][0]), k, '%.3f %.3f' % vals[0], L.points_shape([(0, 0, 0)], [(1.0, 0.93, 0.72)], 1, [3.4]), L.points_shape([(0, 0, 0)], [(1.0, 0.66, 0.36)], 3, [3.9])))
    X.append("</Transform></Switch>")
    # the clock: started by the page after the first frame (boot.js; ?weaveat=N starts N seconds in). Left alone (another viewer) it never starts and the first knot shows complete.
    wk, wv = [], []
    for j in range(K):
        s = j / K
        for kk, val in ((s, (j, 0, 1)), (s + (TW / TT) / K, (j, 1, 1)), (s + ((TW + TH) / TT) / K, (j, 1, 1)), (s + 1 / K - 1e-5, (j, 1, 0))):
            wk.append(kk); wv.append(val)
    wk.append(1.0); wv.append((0, 0, 1))
    ks = lambda k: ' '.join('%.5f' % x for x in k)
    X.append("<TimeSensor DEF='WeaveClock' cycleInterval='%s' loop='true' startTime='1e12'/>" % f(K * TT))
    X.append("<PositionInterpolator DEF='WeaveTape' key='%s' keyValue='%s'/>" % (ks(wk), ', '.join(v3(x) for x in wv)))
    X.append("<PositionInterpolator DEF='ShuttleWeave' key='%s' keyValue='%s'/>" % (ks(keys), ', '.join('%.3f %.3f 0.07' % p for p in vals)))
    X.append("<ROUTE fromNode='WeaveClock' fromField='fraction_changed' toNode='WeaveTape' toField='set_fraction'/>"
             "<ROUTE fromNode='WeaveClock' fromField='fraction_changed' toNode='ShuttleWeave' toField='set_fraction'/>")
    for j in range(K):
        for k in range(4): X.append("<ROUTE fromNode='WeaveTape' fromField='value_changed' toNode='WeaveSh%d_%d' toField='w'/>" % (j, k))
    for k in range(4):
        X.append("<OrientationInterpolator DEF='ShuttleRot%d' key='%s' keyValue='%s'/>" % (k, ks(rk), ', '.join('0 0 1 %s' % f(a) for a in rv[k])))
        X.append("<ROUTE fromNode='WeaveClock' fromField='fraction_changed' toNode='ShuttleRot%d' toField='set_fraction'/><ROUTE fromNode='ShuttleRot%d' fromField='value_changed' toNode='ShuttleTurn%d' toField='set_rotation'/>"
                 "<ROUTE fromNode='ShuttleWeave' fromField='value_changed' toNode='Shuttle%d' toField='set_translation'/>" % (k, k, k, k))
    return ''.join(X), dict(ornaments=info, cycle=K * TT, weave_s=TW, hold_s=TH, fade_s=TF)
