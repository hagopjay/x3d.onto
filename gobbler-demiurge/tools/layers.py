"""Gobbler demiurge, step 2: the layers that sit on top of the Gobbler 3 Deep scene (generated, seeded, deterministic).
Everything here is plain X3D 4.0 (no Script): Sun in the chest, Dyson ribcage (364 class beads from the ontology), flywheel ring,
shell tenders, wing primaries, tail fan with the Blender root, Face and Establishing viewpoints.  Nothing in the Deep scene is edited:
the layers are spliced in before </Scene> by build_bird.py, and they USE two things the Deep scene already DEFs (PointShader, SwayTurn).
Look = B's faceted head (already in the Deep scene) plus lots of D: plumage drawn as gold wireframe feathers with translucent facets, the flywheel ring, tenders, the Blender fan root. Not drawn yet: the nebula sky and the red and blue streaming trails of frame D."""
import json, math, os, random, colorsys, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feathers as FE
import tender as TD

SUN = (6.5, -2.6, 0.4)          # the heart, in the chest where the neck meets the graph (Deep scene coordinates)
RIB_R = 3.3                      # Dyson ribcage radius around the Sun
ROOT = (17.4, -2.5, 0.0)         # tail root: the Blender i/o window
FAN_L = 8.4                      # tail plume length
FAN_CLOSED = 0.16                # the fan starts closed to this share of its opening angle and unfurls when the camera first comes near
GOLD = (0.84, 0.70, 0.36)
BLENDER = (0.95, 0.52, 0.10)

def f(x): return ('%.4g' % x) if abs(x) >= 1e-4 else '0'
def v3(p): return ' '.join(f(x) for x in p)
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    l = math.sqrt(sum(x * x for x in a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)
def axis_angle_to_q(ax, ang): s = math.sin(ang / 2); n = norm(ax); return (n[0] * s, n[1] * s, n[2] * s, math.cos(ang / 2))

SUN_SHADER = """<ComposedShader DEF='SunShader' language='GLSL'><field name='time' type='SFTime' accessType='inputOutput' value='0'/>
<ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex,#version 300 es
precision highp float;
precision highp int;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform mat3 x3d_NormalMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
out vec3 vN;
out vec3 vP;
void main() {
  vN = normalize(x3d_NormalMatrix * x3d_Normal);
  vP = x3d_Vertex.xyz;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
]]></ShaderPart>
<ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,#version 300 es
precision highp float;
precision highp int;
uniform float time;
in vec3 vN;
in vec3 vP;
out vec4 x3d_FragColor;
float h1(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(h1(i), h1(i + vec3(1, 0, 0)), f.x), mix(h1(i + vec3(0, 1, 0)), h1(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(h1(i + vec3(0, 0, 1)), h1(i + vec3(1, 0, 1)), f.x), mix(h1(i + vec3(0, 1, 1)), h1(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
void main() {
  float mu = clamp(normalize(vN).z, 0.0, 1.0);
  float g = vnoise(vP * 26.0 + vec3(0.0, time * 0.10, 0.0)) * 0.6 + vnoise(vP * 64.0 - vec3(time * 0.17, 0.0, 0.0)) * 0.4;
  vec3 c = mix(vec3(1.0, 0.55, 0.12), vec3(1.0, 0.97, 0.82), pow(mu, 0.5)) * (0.8 + 0.5 * g);
  c += vec3(1.0, 0.45, 0.08) * pow(1.0 - mu, 3.0) * 0.6;
  x3d_FragColor = vec4(c, 1.0);
}
]]></ShaderPart></ComposedShader>"""

GLOW_SHADER = """<ComposedShader DEF='GlowShader' language='GLSL'>
<ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex,#version 300 es
precision highp float;
precision highp int;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in vec4 x3d_Color;
out vec2 vUV;
out vec3 vCol;
void main() {
  vUV = x3d_Vertex.xy;
  vCol = x3d_Color.rgb;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
]]></ShaderPart>
<ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,#version 300 es
precision highp float;
precision highp int;
in vec2 vUV;
in vec3 vCol;
out vec4 x3d_FragColor;
void main() {
  float r = length(vUV);
  if (r >= 1.0) discard;
  float a = pow(1.0 - r, 2.6) * 0.85 + exp(-r * r * 22.0) * 0.5;
  x3d_FragColor = vec4(vCol * (0.9 + 0.8 * exp(-r * r * 14.0)), clamp(a, 0.0, 1.0));
}
]]></ShaderPart></ComposedShader>"""
_glow_defined = [False]
def glow(center, radius, col):
    """a screen-facing soft glow (Billboard quad with GlowShader): size in scene units, no point-size limit"""
    sh = "<ComposedShader USE='GlowShader'/>" if _glow_defined[0] else GLOW_SHADER
    _glow_defined[0] = True
    c = v3(col)
    return ("<Transform translation='%s' scale='%s %s %s'><Billboard axisOfRotation='0 0 0'><Shape><Appearance alphaMode='BLEND'>%s</Appearance>"
            "<IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1'><Color color='%s'/><Coordinate point='-1 -1 0 1 -1 0 1 1 0 -1 1 0'/></IndexedFaceSet></Shape></Billboard></Transform>"
            % (v3(center), f(radius), f(radius), f(radius), sh, ' '.join([c] * 4)))

def gems(pts, cols, radii):
    """faceted gem beads: one octahedron per point, flat per-face colour with a fake key light (B's facets, unlit), one IndexedFaceSet"""
    P, I, C = [], [], []
    L = norm((-0.4, 0.7, 0.6))
    for p, c, r in zip(pts, cols, radii):
        b = len(P)
        V = [(r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r)]
        P += [add(p, v) for v in V]
        for (a_, b_, c_) in ((2, 4, 0), (2, 1, 4), (2, 5, 1), (2, 0, 5), (3, 0, 4), (3, 4, 1), (3, 1, 5), (3, 5, 0)):
            I.append('%d %d %d -1' % (b + a_, b + b_, b + c_))
            n = norm(add(add(V[a_], V[b_]), V[c_])); k = 0.5 + 0.62 * max(0.0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2])
            C.append(v3(tuple(min(1.0, x * k) for x in c)))
    return ("<Shape><Appearance/><IndexedFaceSet solid='false' colorPerVertex='false' coordIndex='%s'><Color color='%s'/><Coordinate point='%s'/></IndexedFaceSet></Shape>"
            % (' '.join(I), ' '.join(C), ' '.join(v3(p) for p in P)))

def alpha(kind, size):
    """PointShader (Deep scene) encodes the sprite kind and size in the colour alpha: kind * 0.25 + size / 16, size under 4.
    kind 1 = star (lit by the scene's moving lights, spikes above size 2.75), kind 3 = mote (steady)"""
    assert 0 <= kind <= 3 and 0 < size < 4
    return kind * 0.25 + size / 16.0

def points_shape(pts, cols, kind, sizes, bind_def=None):
    rgba = ' '.join('%s %s %s %s' % (f(c[0]), f(c[1]), f(c[2]), '%.4f' % alpha(kind, s)) for c, s in zip(cols, sizes))
    return ("<Shape><Appearance alphaMode='BLEND'><Material diffuseColor='0 0 0' emissiveColor='1 0.8 0.42'/><ComposedShader USE='PointShader'/></Appearance>"
            "<PointSet><ColorRGBA color='%s'/><Coordinate point='%s'/></PointSet></Shape>") % (rgba, ' '.join(v3(p) for p in pts))

def lines_shape(polys, mat, defname=None, transparency=0.0):
    pts, idx = [], []
    for poly in polys:
        base = len(pts); pts += poly; idx += list(range(base, base + len(poly))) + [-1]
    m = "<Material %semissiveColor='%s' diffuseColor='0 0 0'%s/>" % ("DEF='%s' " % defname if defname else '', v3(mat), (" transparency='%s'" % f(transparency)) if transparency else '')
    return ("<Shape><Appearance alphaMode='BLEND'>%s</Appearance><IndexedLineSet coordIndex='%s'><Coordinate point='%s'/></IndexedLineSet></Shape>"
            % (m, ' '.join(map(str, idx)), ' '.join(v3(p) for p in pts)))

def circle(c, ax, r, n=96):
    ax = norm(ax); h = (0, 1, 0) if abs(ax[1]) < .9 else (1, 0, 0)
    u = norm(cross(ax, h)); w = cross(ax, u)
    return [add(c, add(mul(u, r * math.cos(2 * math.pi * i / n)), mul(w, r * math.sin(2 * math.pi * i / n)))) for i in range(n + 1)]

# ---------------------------------------------------------------- feathers
def feather(root, u, v, n, L, W, nb, arch, curl, tilt):
    """one feather as a faceted wireframe: spine, barbs, outline, facets. returns lists in world coordinates"""
    S, Lt, Rt = [], [], []
    for i in range(nb + 1):
        t = i / nb
        p = add(root, mul(u, L * t)); p = add(p, mul(n, arch * L * t * t)); p = add(p, mul(v, curl * L * t * t))
        S.append(p)
    for i in range(1, nb + 1):
        t = i / nb
        prof = (math.sin(math.pi * min(1.0, t ** 0.82)) ** 0.62) if t < 1 else 0.0
        w = 0.5 * W * prof
        base = S[i]
        l = add(add(base, mul(v, w)), mul(u, 0.55 * w)); r = add(add(base, mul(v, -w)), mul(u, 0.55 * w))
        Lt.append(add(l, mul(n, tilt * w))); Rt.append(add(r, mul(n, -tilt * w)))
    return S, Lt, Rt

def plume_lod_proc(name, root, u, v, n, L, W, style, rng, nb_near=22, nb_mid=8):
    """the earlier procedural plume (kept as the fallback when assets/feathers is missing, and as the source of the random draws that keep the rest of the scene where it was).
    style: plain | mock | (real, rgb) | (work, rgb): returns an LOD (near, mid, far) in X3D, plus the tip position"""
    arch, curl, tilt = rng.uniform(.04, .10), rng.uniform(-.05, .05), rng.uniform(.10, .22)
    out = []
    kind = style if isinstance(style, str) else style[0]
    col = None if isinstance(style, str) else style[1]
    edge = {'plain': (0.80, 0.64, 0.30), 'mock': (0.42, 0.40, 0.38), 'real': col, 'work': (0.80, 0.64, 0.30)}[kind]
    barb = {'plain': (0.50, 0.38, 0.17), 'mock': None, 'real': tuple(c * 0.55 for c in col) if col else None, 'work': (0.50, 0.38, 0.17)}[kind]
    face_a = {'plain': 0.26, 'mock': 0.0, 'real': 0.36, 'work': 0.26}[kind]
    ftint = col if kind == 'real' else (1.0, 0.80, 0.40)
    levels = []
    for nb, with_barbs in ((nb_near, True), (nb_mid, False)):
        S, Lt, Rt = feather(root, u, v, n, L, W, nb, arch, curl, tilt)
        parts = []
        # facets: a quad strip each side, per-face tint and alpha (B's facets), unlit
        if face_a > 0:
            pts = S[1:] + Lt + Rt; k = len(S) - 1
            sI = lambda i: i - 1                 # S[1..nb] -> 0..nb-1
            lI = lambda i: k + i - 1
            rI = lambda i: 2 * k + i - 1
            faces, cols = [], []
            for i in range(1, nb):
                faces.append((sI(i), sI(i + 1), lI(i + 1), lI(i))); faces.append((sI(i), rI(i), rI(i + 1), sI(i + 1)))
            for fi in range(len(faces)):
                jit = rng.uniform(.55, 1.15); tcol = tuple(min(1, c * jit) for c in ftint)
                cols.append('%s %s %s %s' % (f(tcol[0]), f(tcol[1]), f(tcol[2]), f(face_a * rng.uniform(.6, 1.25))))
            parts.append("<Shape><Appearance alphaMode='BLEND'/><IndexedFaceSet solid='false' colorPerVertex='false' coordIndex='%s'><ColorRGBA color='%s'/><Coordinate point='%s'/></IndexedFaceSet></Shape>"
                         % (' '.join(' '.join(map(str, q)) + ' -1' for q in faces), ' '.join(cols), ' '.join(v3(p) for p in pts)))
        if with_barbs and barb:
            parts.append(lines_shape([[S[i], Lt[i - 1]] for i in range(1, nb + 1)] + [[S[i], Rt[i - 1]] for i in range(1, nb + 1)], barb, transparency=0.25))
        outline = [S[0]] + Lt + [S[-1]] + Rt[::-1] + [S[0]]
        parts.append(lines_shape([S, outline] if kind != 'mock' else [outline, S], edge, defname=(name + '_edge') if kind == 'work' and nb == nb_near else None))
        levels.append(''.join(parts))
    S, _, _ = feather(root, u, v, n, L, W, 4, arch, curl, tilt)
    tip = S[-1]
    far = lines_shape([S], edge, transparency=0.2) + points_shape([tip], [edge], 1, [2.4 if kind == 'real' else 1.5])
    mid_pt = S[len(S) // 2]
    xml = "<LOD DEF='%s' center='%s' range='11 60'>%s</LOD>" % (name, v3(mid_pt), ''.join("<Group>%s</Group>" % s for s in (levels[0], levels[1], far)))
    return xml, tip


# ---------------------------------------------------------------- Blender-made feathers (assets/feathers, tools/blender_feather.py)
_feathers = {}                    # variant -> parts, loaded once
_defined = set()                  # DEF names already written in this build (later uses are USE)
GOLD_MASK = (1.0, 0.93, 0.66)     # sunlit facets: a touch more gold on the warm bake
COOL_MASK = (0.78, 0.98, 1.18)    # shadowed facets: kept cool (teal and blue), the complement of the sun

def feather_parts(variant):
    if variant not in _feathers: _feathers[variant] = FE.load(variant)
    return _feathers[variant]

def have_feathers():
    try: return len(FE.variants()) > 0
    except OSError: return False

def basis_rotation(u, v, n):
    """axis-angle (X3D rotation) of the matrix whose columns are u, v, n (an orthonormal right-handed basis)"""
    m = ((u[0], v[0], n[0]), (u[1], v[1], n[1]), (u[2], v[2], n[2]))
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1) * 2; qw = s / 4; qx = (m[2][1] - m[1][2]) / s; qy = (m[0][2] - m[2][0]) / s; qz = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; qw = (m[2][1] - m[1][2]) / s; qx = s / 4; qy = (m[0][1] + m[1][0]) / s; qz = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; qw = (m[0][2] - m[2][0]) / s; qx = (m[0][1] + m[1][0]) / s; qy = s / 4; qz = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; qw = (m[1][0] - m[0][1]) / s; qx = (m[0][2] + m[2][0]) / s; qy = (m[1][2] + m[2][1]) / s; qz = s / 4
    qw = max(-1.0, min(1.0, qw)); ang = 2 * math.acos(qw); sn = math.sqrt(max(0.0, 1 - qw * qw))
    return ((1, 0, 0), 0.0) if sn < 1e-6 else ((qx / sn, qy / sn, qz / sn), ang)

def _lum(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def feather_faces(variant, part, key, mask, alpha, gain=1.0):
    """a Blender-modelled vane as one unlit Shape. Face colour = the baked golden-hour light: sunlit facets take the role mask (gold, or the role colour),
    shadowed facets stay cool (blue-teal), so the blade reads as jewel facets, not brown glass. Alpha follows the light."""
    dn = 'FV_%s_%s_%s' % (variant, part, key)
    if dn in _defined: return "<Shape USE='%s'/>" % dn
    _defined.add(dn)
    g = feather_parts(variant)[part]
    cols = []
    for c in g['colors']:
        l = _lum(c); s = min(1.0, max(0.0, (l - 0.22) / 0.5)); s = s * s * (3 - 2 * s)
        m = tuple(COOL_MASK[i] + (mask[i] - COOL_MASK[i]) * s for i in range(3))
        rgb = tuple(min(1.0, c[i] * m[i] * gain) for i in range(3))
        cols.append('%s %s %s %s' % (f(rgb[0]), f(rgb[1]), f(rgb[2]), f(min(0.95, alpha * (0.50 + 0.95 * l)))))
    return ("<Shape DEF='%s'><Appearance alphaMode='BLEND'/><IndexedFaceSet solid='false' coordIndex='%s'><ColorRGBA color='%s'/><Coordinate point='%s'/></IndexedFaceSet></Shape>"
            % (dn, ' '.join(map(str, g['index'])), ' '.join(cols), ' '.join(v3(p) for p in g['points'])))

def feather_quill(variant, key, base):
    """the quill tube: flat facets lit by a fixed key light (B's facets), unlit so the tube reads as cut metal"""
    dn = 'FQ_%s_%s' % (variant, key)
    if dn in _defined: return "<Shape USE='%s'/>" % dn
    _defined.add(dn)
    g = feather_parts(variant)['near_quill']; P = g['points']; I = g['index']; cols = []
    L = norm((-0.35, 0.55, 0.75))
    for k in range(0, len(I), 4):
        a, b, c = P[I[k]], P[I[k + 1]], P[I[k + 2]]
        nrm = norm(cross(sub(b, a), sub(c, a))); kk = 0.45 + 0.75 * abs(nrm[0] * L[0] + nrm[1] * L[1] + nrm[2] * L[2])
        cols.append(v3(tuple(min(1.0, x * kk) for x in base)))
    return ("<Shape DEF='%s'><Appearance/><IndexedFaceSet solid='false' colorPerVertex='false' coordIndex='%s'><Color color='%s'/><Coordinate point='%s'/></IndexedFaceSet></Shape>"
            % (dn, ' '.join(map(str, I)), ' '.join(cols), ' '.join(v3(p) for p in P)))

def feather_lines(variant, part, mat, key, transparency=0.0, mat_def=None):
    """Blender edge geometry as lines. The geometry node is shared per variant; the Appearance is the plume's own when its colour animates (mat_def)"""
    gd = 'FL_%s_%s' % (variant, part)
    g = feather_parts(variant)[part]
    if gd in _defined: geo = "<IndexedLineSet USE='%s'/>" % gd
    else:
        _defined.add(gd)
        geo = "<IndexedLineSet DEF='%s' coordIndex='%s'><Coordinate point='%s'/></IndexedLineSet>" % (gd, ' '.join(map(str, g['index'])), ' '.join(v3(p) for p in g['points']))
    m = "<Material %semissiveColor='%s' diffuseColor='0 0 0'%s/>" % ("DEF='%s' " % mat_def if mat_def else '', v3(mat), (" transparency='%s'" % f(transparency)) if transparency else '')
    return "<Shape><Appearance alphaMode='BLEND'>%s</Appearance>%s</Shape>" % (m, geo)

def plume_lod(name, root, u, v, n, L, W, style, rng, nb_near=22, nb_mid=8):
    """a plume from the Blender-modelled feather: same signature and the same random draws as the procedural one, so nothing else in the scene moves.
    returns an LOD (near, mid, far) and the tip position"""
    if not have_feathers():
        return plume_lod_proc(name, root, u, v, n, L, W, style, rng, nb_near, nb_mid)
    plume_lod_proc(name, root, u, v, n, L, W, style, rng, nb_near, nb_mid)             # burn the draws it used to take
    pr = random.Random(hash_name(name))
    vs = FE.variants(); var = vs[pr.randrange(len(vs))]
    kind = style if isinstance(style, str) else style[0]
    col = None if isinstance(style, str) else style[1]
    edge = {'plain': (0.80, 0.64, 0.30), 'mock': (0.42, 0.40, 0.38), 'real': col, 'work': (0.80, 0.64, 0.30)}[kind]
    barb = {'plain': (0.50, 0.38, 0.17), 'mock': None, 'real': tuple(c * 0.55 for c in col) if col else None, 'work': (0.50, 0.38, 0.17)}[kind]
    face_a = {'plain': 0.48, 'mock': 0.0, 'real': 0.58, 'work': 0.48}[kind]
    if kind == 'real': mask = tuple(0.45 * GOLD_MASK[i] + 0.55 * col[i] for i in range(3)); key = 'r%02d%02d%02d' % tuple(int(c * 9.99) for c in col)
    else: mask = GOLD_MASK; key = 'gold'
    ax, ang = basis_rotation(u, v, n)
    sx, sy = L, W / FE_R                                                              # length along the quill, width from the plume's own W
    xf = "<Transform translation='%s' rotation='%s %s' scale='%s %s %s'>" % (v3(root), v3(ax), f(ang), f(sx), f(sy), f(sx))
    def place(p): return add(root, add(add(mul(u, sx * p[0]), mul(v, sy * p[1])), mul(n, sx * p[2])))
    sp = feather_parts(var)['spine']['points']
    tip = place(sp[-1]); mid_pt = place(sp[len(sp) // 2])
    near, mid = [], []
    if face_a > 0:
        near.append(feather_faces(var, 'near_vane', key, mask, face_a * 1.25, 1.05)); mid.append(feather_faces(var, 'near_vane', key, mask, face_a * 1.05, 1.05))
    near.append(feather_quill(var, key, edge if kind == 'real' else (0.95, 0.80, 0.46)))
    if barb: near.append(feather_lines(var, 'near_barbs', barb, key, 0.25))
    near.append(feather_lines(var, 'outline', edge, key, 0.0, (name + '_edge') if kind == 'work' else None))
    near.append(feather_lines(var, 'spine', edge, key))
    mid.append(feather_lines(var, 'outline', edge, key)); mid.append(feather_lines(var, 'spine', edge, key))
    far_pts = [place(p) for p in sp[::6]] + [tip]
    far = lines_shape([far_pts], edge, transparency=0.2) + points_shape([tip], [edge], 1, [2.4 if kind == 'real' else 1.5])
    lvl = lambda parts: "<Group>%s%s</Transform></Group>" % (xf, ''.join(parts))
    xml = "<LOD DEF='%s' center='%s' range='11 60'>%s<Group>%s</Group></LOD>" % (name, v3(mid_pt), lvl(near) + lvl(mid), far)
    return xml, tip

TENDER_H = 0.55                   # a tender stands this tall (the Blender figure is 1 unit)
TENDER_GAITS = (1.2, 1.5, 1.8)    # seconds per walk cycle of the three humanoid copies

def tender_walk(n, Tg, steps=16):
    """one copy's walk cycle: OrientationInterpolators on the H-Anim joints (turns about the joint's own X, the figure's left-right axis; negative swings forward),
    a pelvis twist and a bob. One looping TimeSensor drives them all, so the copy and every walker that shares it keep step."""
    def ax(name, fn, axis='1 0 0'):
        keys = ' '.join(f(i / steps) for i in range(steps + 1))
        vals = ', '.join('%s %s' % (axis, f(fn(2 * math.pi * i / steps))) for i in range(steps + 1))
        return ("<OrientationInterpolator DEF='T%dW_%s' key='%s' keyValue='%s'/><ROUTE fromNode='T%dGait' fromField='fraction_changed' toNode='T%dW_%s' toField='set_fraction'/>"
                "<ROUTE fromNode='T%dW_%s' fromField='value_changed' toNode='hanim_T%d_%s' toField='set_rotation'/>" % (n, name, keys, vals, n, n, name, n, name, n, name))
    swing = lambda side, ph: (lambda t: -0.42 * math.cos(t + ph))                            # hip: forward at heel strike, back at toe-off
    knee = lambda ph: (lambda t: 0.10 + 0.78 * max(0.0, -math.sin(t + ph)) ** 1.3)             # the knee folds while the leg swings through
    out = ["<TimeSensor DEF='T%dGait' cycleInterval='%s' loop='true'/>" % (n, f(Tg))]
    for side, ph, sg in (('l', 0.0, 1), ('r', math.pi, -1)):
        out.append(ax('%s_hip' % side, swing(side, ph)))
        out.append(ax('%s_knee' % side, knee(ph)))
        out.append(ax('%s_ankle' % side, lambda t, ph=ph: 0.16 * math.cos(t + ph + 1.2)))
        out.append(ax('%s_shoulder' % side, lambda t, ph=ph: 0.34 * math.cos(t + ph)))      # the arm swings against its own-side leg
        out.append(ax('%s_elbow' % side, lambda t, ph=ph: -0.38 - 0.12 * math.cos(t + ph)))
    out.append(ax('vt6', lambda t: 0.10 * math.cos(t), '0 0 1'))                             # the chest turns against the pelvis
    out.append(ax('sacroiliac', lambda t: -0.07 * math.cos(t), '0 0 1'))
    keys = ' '.join(f(i / steps) for i in range(steps + 1)); vals = ', '.join('0 0 %s' % f(0.012 * (1 - math.cos(4 * math.pi * i / steps)) * 0.5 - 0.012) for i in range(steps + 1))
    out.append("<PositionInterpolator DEF='T%dW_bob' key='%s' keyValue='%s'/><ROUTE fromNode='T%dGait' fromField='fraction_changed' toNode='T%dW_bob' toField='set_fraction'/>"
               "<ROUTE fromNode='T%dW_bob' fromField='value_changed' toNode='hanim_T%d_humanoid_root' toField='set_translation'/>" % (n, keys, vals, n, n, n, n))
    return ''.join(out)

def hash_name(s): return sum((i + 1) * ord(c) for i, c in enumerate(s)) * 2654435761 % (2 ** 32)

FE_R = 0.125                      # the vane's full width over its length in the Blender asset (tools/blender_feather.py R)

# ---------------------------------------------------------------- assembly
def heart_beats(seed=4):
    """the heartbeat tape: one beat per validator verdict in data/heartbeat/xbench-run1.json. A scene that failed first shows a red beat
    (and one more red beat for every repair attempt that failed again), then a gold beat when it passes. returns [(seconds, is_red)]; the
    beat length varies by a few percent (seeded) like a real pulse"""
    doc = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'heartbeat', 'xbench-run1.json')))
    hr = random.Random(seed * 131 + 7); out = []
    for r in doc['rounds']:
        if r['first_pass']: out.append((1.0 * (1 + hr.uniform(-.06, .06)), False)); continue
        for k in range(r['repair_attempts']): out.append((0.85 * (1 + hr.uniform(-.06, .06)), True))
        out.append((1.0 * (1 + hr.uniform(-.06, .06)), False))
    return out

def build(explorer_path, seed=4):
    rng = random.Random(seed); _glow_defined[0] = False; _defined.clear()
    D = json.load(open(explorer_path))
    maxd = D['stats']['max_depth']
    fams = sorted(D['families'], key=lambda k: -D['families'][k])
    def fam_col(fm):
        h = (fams.index(fm) * 137.5 % 360) / 360
        return colorsys.hls_to_rgb(h, .66, .72)
    anchors = []
    X = []                                  # xml chunks inside the sway group
    def anchor(id_, label, tag, pos, level='min'):
        anchors.append(dict(id=id_, label=label, tag=tag, pos=[round(c, 3) for c in pos], level=level))

    # ---- the Sun: validator heart. It beats the tape of 30 real validator runs (data/heartbeat/xbench-run1.json): gold = a clean or repaired scene, red = a defect found
    beats = heart_beats(seed)
    T = sum(d for d, _ in beats); eps = 0.002
    X.append("<Transform DEF='Heart' translation='%s'><Transform DEF='HeartPulse'>" % v3(SUN))
    X.append("<Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='1 0.9 0.6'/>%s</Appearance><Sphere radius='0.36'/></Shape>" % SUN_SHADER)
    X.append(glow((0, 0, 0), 2.1, (1.0, 0.62, 0.18)))
    X.append(glow((0, 0, 0), 0.95, (1.0, 0.92, 0.62)))
    X.append("</Transform>")
    ring = []                                                       # a flat annulus facing the camera: the "ping" that leaves the heart with every validator run
    for k in range(64):
        a0, a1 = 2 * math.pi * k / 64, 2 * math.pi * (k + 1) / 64
        ring.append((math.cos(a0), math.sin(a0), 0)); ring.append((0.93 * math.cos(a0), 0.93 * math.sin(a0), 0))
    idx = ' '.join('%d %d %d %d -1' % (2 * k, 2 * k + 1, (2 * k + 3) % 128, (2 * k + 2) % 128) for k in range(64))
    X.append("<Transform DEF='HeartRing'><Billboard axisOfRotation='0 0 0'><Shape><Appearance alphaMode='BLEND'><Material DEF='HeartRingMat' diffuseColor='0 0 0' emissiveColor='1 0.84 0.38' transparency='1'/></Appearance>"
             "<IndexedFaceSet solid='false' coordIndex='%s'><Coordinate point='%s'/></IndexedFaceSet></Shape></Billboard></Transform>" % (idx, ' '.join(v3(p) for p in ring)))
    X.append("</Transform>")
    kS, vS, kR, vR, kF, vF, kC, vC = [], [], [], [], [], [], [], []
    t0 = 0.0
    for i, (d, red) in enumerate(beats):
        amp = 0.13 if red else 0.10
        for off, val in ((0.0, 1.0), (0.07, 1 + amp), (0.17, 0.99), (0.30, 1 + 0.55 * amp), (0.52, 1.0)):
            kS.append((t0 + off * d) / T); vS.append(val)
        col = (1.0, 0.22, 0.16) if red else (1.0, 0.86, 0.42)
        for off, sc, fade in ((0.0, 0.45, 0.0), (0.75 * d, 2.7, 1.0), (d - eps, 2.7, 1.0)):
            kR.append((t0 + off) / T); vR.append(sc); kF.append((t0 + off) / T); vF.append(fade); kC.append((t0 + off) / T); vC.append(col)
        t0 += d
    kS.append(1.0); vS.append(1.0)
    kR[-1] = kF[-1] = kC[-1] = 1.0
    ks = lambda k: ' '.join('%.5f' % x for x in k)
    X.append("<TimeSensor DEF='HeartClock' cycleInterval='%s' loop='true'/>"
             "<PositionInterpolator DEF='HeartBreath' key='%s' keyValue='%s'/>"
             "<PositionInterpolator DEF='HeartRingGrow' key='%s' keyValue='%s'/>"
             "<ScalarInterpolator DEF='HeartRingFade' key='%s' keyValue='%s'/>"
             "<ColorInterpolator DEF='HeartRingColor' key='%s' keyValue='%s'/>"
             "<ROUTE fromNode='Twinkle' fromField='elapsedTime' toNode='SunShader' toField='time'/>"
             "<ROUTE fromNode='HeartClock' fromField='fraction_changed' toNode='HeartBreath' toField='set_fraction'/>"
             "<ROUTE fromNode='HeartBreath' fromField='value_changed' toNode='HeartPulse' toField='set_scale'/>"
             "<ROUTE fromNode='HeartClock' fromField='fraction_changed' toNode='HeartRingGrow' toField='set_fraction'/>"
             "<ROUTE fromNode='HeartRingGrow' fromField='value_changed' toNode='HeartRing' toField='set_scale'/>"
             "<ROUTE fromNode='HeartClock' fromField='fraction_changed' toNode='HeartRingFade' toField='set_fraction'/>"
             "<ROUTE fromNode='HeartRingFade' fromField='value_changed' toNode='HeartRingMat' toField='set_transparency'/>"
             "<ROUTE fromNode='HeartClock' fromField='fraction_changed' toNode='HeartRingColor' toField='set_fraction'/>"
             "<ROUTE fromNode='HeartRingColor' fromField='value_changed' toNode='HeartRingMat' toField='set_emissiveColor'/>"
             % (f(T), ks(kS), ', '.join('%s %s %s' % (f(x), f(x), f(x)) for x in vS), ks(kR), ', '.join('%s %s %s' % (f(x), f(x), f(x)) for x in vR),
                ks(kF), ' '.join(f(x) for x in vF), ks(kC), ', '.join(v3(c) for c in vC)))
    nred = sum(1 for _, r in beats if r)
    anchor('heart', 'The validator', 'the Sun, the bird\'s heart · it beats a replay of 30 real validator runs (X3D-Bench run 1, 8 Oct 2026): red = a defect found (%d beats), gold = clean or repaired (%d)' % (nred, len(beats) - nred), add(SUN, (0.5, -0.45, 0.4)))

    # ---- Dyson ribcage: lat/lon lattice + 364 ontology class beads (x3d.onto v2 layout: longitude = a, latitude from depth)
    wires = []
    for lat in (-60, -30, 0, 30, 60):
        la = math.radians(lat); wires.append([add(SUN, (RIB_R * math.cos(la) * math.cos(2 * math.pi * i / 72), RIB_R * math.sin(la), RIB_R * math.cos(la) * math.sin(2 * math.pi * i / 72))) for i in range(73)])
    for lon in range(0, 360, 30):
        lo = math.radians(lon); wires.append([add(SUN, (RIB_R * math.cos(math.pi * (i / 48 * 2 - 1) / 2) * math.cos(lo), RIB_R * math.sin(math.pi * (i / 48 * 2 - 1) / 2), RIB_R * math.cos(math.pi * (i / 48 * 2 - 1) / 2) * math.sin(lo))) for i in range(49)])
    X.append(lines_shape(wires, (1.0, 0.82, 0.42), transparency=0.0))
    dots = [p for w in wires for p in w[::3]]
    X.append(points_shape(dots, [(1.0, 0.85, 0.5)] * len(dots), 3, [0.9] * len(dots)))
    bp, bc, bs = [], [], []
    bands = {}
    for nd in D['nodes']: bands.setdefault(nd['d'], []).append(nd)
    place = {}
    for d_, grp in bands.items():                                   # latitude from depth as in v2; longitude respaced evenly (v2's own `a` stacks classes into strings)
        grp.sort(key=lambda n_: n_['a']); ph = rng.uniform(0, 2 * math.pi)
        for k, nd in enumerate(grp):
            lon = ph + 2 * math.pi * (k + 0.5) / len(grp); lat = math.radians(70 - d_ * 140 / maxd + (9 if k % 2 else -9) * rng.uniform(.3, 1.0))
            place[nd['id']] = (lon, max(-1.45, min(1.45, lat)))
    for nd in D['nodes']:
        lon, lat = place[nd['id']]
        p = add(SUN, (RIB_R * math.cos(lat) * math.cos(lon), RIB_R * math.sin(lat), RIB_R * math.cos(lat) * math.sin(lon)))
        bp.append(p)
        if nd['new']: bc.append((0.35, 1.0, 0.55)); bs.append(2.74)
        else: bc.append(fam_col(nd['fam'])); bs.append(1.7 if nd['kind'] == 'abstract' else 2.1)
    assert len(bp) == 364
    X.append(gems(bp, bc, [0.17 if z > 2.5 else 0.105 for z in bs]))
    anchor('ribcage', 'Dyson ribcage', '364 ontology classes, X3D Ontology 4.1 (x3d.onto) · green = new in 4.1', add(SUN, (RIB_R * .7, RIB_R * .75, 0)))

    # ---- three domain rings, slowly turning (X3D, URDF, glTF) and the flywheel loop ring with a running pulse
    rings = [('RingX3D', (1, 0.2, 0), RIB_R * 1.22, (0.84, 0.70, 0.36), 63), ('RingURDF', (0.1, 0, 1), RIB_R * 1.38, (0.45, 0.62, 0.9), 83), ('RingGLTF', (0.7, 0, 0.7), RIB_R * 1.54, (0.30, 0.82, 0.78), 103)]
    for nm, ax, r, col, per in rings:
        X.append("<Transform DEF='%s' center='%s'>" % (nm, v3(SUN)))
        X.append(lines_shape([circle(SUN, ax, r, 120)], col, transparency=0.35))
        dots = circle(SUN, ax, r, 40)[:-1]
        X.append(points_shape(dots, [col] * len(dots), 3, [1.3] * len(dots)))
        X.append("</Transform>")
        X.append("<TimeSensor DEF='%sClock' cycleInterval='%d' loop='true'/><OrientationInterpolator DEF='%sSpin' key='0 0.5 1' keyValue='0 1 0 0, 0 1 0 3.14159, 0 1 0 6.28318'/>"
                 "<ROUTE fromNode='%sClock' fromField='fraction_changed' toNode='%sSpin' toField='set_fraction'/><ROUTE fromNode='%sSpin' fromField='value_changed' toNode='%s' toField='set_rotation'/>" % (nm, per, nm, nm, nm, nm, nm))
    LR = RIB_R * 1.72; lax = (0.25, 0.1, 1.0)
    X.append("<Transform DEF='Flywheel4' center='%s'>" % v3(SUN))
    X.append(lines_shape([circle(SUN, lax, LR, 140)], (0.95, 0.75, 0.35), transparency=0.15))
    st = circle(SUN, lax, LR, 8)[:-1]
    X.append(points_shape(st, [(1.0, 0.82, 0.45)] * 8, 1, [2.4] * 8))
    X.append("<Transform DEF='FlywheelPulse' center='%s'>%s</Transform>" % (v3(SUN), points_shape([st[0]], [(1.0, 0.97, 0.8)], 3, [3.2])))
    X.append("</Transform>")
    X.append("<TimeSensor DEF='FlywheelClock' cycleInterval='9' loop='true'/><OrientationInterpolator DEF='FlywheelSpin' key='0 0.5 1' keyValue='%s 0, %s 3.14159, %s 6.28318'/>"
             "<ROUTE fromNode='FlywheelClock' fromField='fraction_changed' toNode='FlywheelSpin' toField='set_fraction'/><ROUTE fromNode='FlywheelSpin' fromField='value_changed' toNode='FlywheelPulse' toField='set_rotation'/>" % ((v3(norm(lax)),) * 3))
    anchor('flywheel', 'The flywheel', 'write, validate, repair, render, around the heart · pulse is display only', st[2])

    # ---- shell tenders: H-Anim humanoids modelled in Blender (tools/blender_tender.py, exported through the blenderizer), walking the ribcage; points of light from far away.
    # Three copies of the humanoid with their own gait (1.2, 1.5 and 1.8 s a cycle), shared by USE among ten walkers. How they walk and what they tend is simulated.
    NTEN = 10; NG = 3; STRIDE = 0.8 * TENDER_H
    for k in range(NTEN):
        n = k % NG; Tg = TENDER_GAITS[n]
        a0 = norm((rng.uniform(-1, 1), rng.uniform(-.3, 1), rng.uniform(-1, 1))); rng.choice([47, 59, 71, 83, 97])     # the same random draws as the box placeholders made,
        d = norm((rng.uniform(.3, 1), rng.uniform(-.4, .4), rng.uniform(-1, 1))); rng.uniform(-.5, .5)               # so the wing and fan that follow keep their look
        a = norm(sub(a0, mul(d, sum(x * y for x, y in zip(a0, d)))))                            # the walker's great circle: axis a, perpendicular to where it stands (d)
        fwd = cross(a, d); left = cross(d, fwd)                                                  # forward is the direction of the orbit; the figure faces +Z, up +Y, its left +X
        per = max(20, int(round(2 * math.pi * RIB_R * 1.01 * Tg / STRIDE)))                      # the orbit takes as long as the gait needs for its stride, so feet do not slide
        r0 = add(SUN, mul(d, RIB_R * 1.01))
        body = ("<Group DEF='TenderBody%d'><Transform scale='%s %s %s'>%s</Transform></Group>" % (n, f(TENDER_H), f(TENDER_H), f(TENDER_H), TD.humanoid(n))) if k < NG else "<Group USE='TenderBody%d'/>" % n
        X.append("<Transform DEF='TenderOrbit%d' center='%s'><Transform translation='%s' rotation='%s %s'><LOD range='5'>"
                 "%s<Group>%s</Group></LOD></Transform></Transform>" % (k, v3(SUN), v3(r0), v3(basis_rotation(left, d, fwd)[0]), f(basis_rotation(left, d, fwd)[1]), body,
                                                                             points_shape([(0, 0, 0)], [(1.0, 0.92, 0.7)], 3, [1.9])))
        X.append("<TimeSensor DEF='TenderClock%d' cycleInterval='%d' loop='true'/><OrientationInterpolator DEF='TenderSpin%d' key='0 0.5 1' keyValue='%s 0, %s 3.14159, %s 6.28318'/>"
                 "<ROUTE fromNode='TenderClock%d' fromField='fraction_changed' toNode='TenderSpin%d' toField='set_fraction'/><ROUTE fromNode='TenderSpin%d' fromField='value_changed' toNode='TenderOrbit%d' toField='set_rotation'/>"
                 % (k, per, k, v3(a), v3(a), v3(a), k, k, k, k))
    for n in range(NG): X.append(tender_walk(n, TENDER_GAITS[n]))
    anchor('tenders', 'Shell tenders', 'they tend the ribcage · H-Anim humanoids made in Blender, their walk and their tending simulated', add(SUN, (-RIB_R * .2, RIB_R * 1.0, RIB_R * .3)), 'full')

    # ---- wing: 10 primaries on the upper back (orchestrator roles; role colour only while working, simulated)
    ROLES = [('planner', (0.25, 0.85, 0.85)), ('router', (0.30, 0.65, 1.0)), ('validator', (1.0, 0.93, 0.66)), ('repair', (0.30, 0.95, 0.55)), ('vision judge', (0.95, 0.35, 0.85)),
             ('DSPy optimizer', (0.68, 0.45, 1.0)), ('memory', (1.0, 0.65, 0.25)), ('Blender operator', BLENDER), ('exporter', (0.40, 0.85, 1.0)), ('curator', (0.85, 0.85, 0.45))]
    shoulder = (8.6, 1.6, 2.0)
    interp = []; preen = []; wr = random.Random(seed * 17 + 5)
    for i, (role, rc) in enumerate(ROLES):
        ang = math.radians(8 + i * 6.2)
        u = norm((math.cos(ang), math.sin(ang), 0.22 - 0.03 * i)); v = norm(cross((0, 0, 1), u)); n = norm(cross(u, v))
        L = 6.4 + 1.5 * math.sin(math.pi * (i + .5) / 10)
        wroot = add(shoulder, (0, 0.06 * i, 0.0))
        xml, tip = plume_lod('Wing%d' % i, wroot, u, v, n, L, 0.9, ('work', rc), rng, 18, 7)
        X.append("<Transform DEF='WingPreen%d' center='%s'>%s</Transform>" % (i, v3(wroot), xml))
        # the preening wave: one pass along the primaries, each lifting its tip a few degrees a beat after its neighbour (a seeded wobble in timing and height)
        s0 = 0.05 + 0.034 * i + wr.uniform(-.006, .006); pk = 0.16 + wr.uniform(-.03, .03)
        ks = [0, s0, s0 + .018, s0 + .042, s0 + .066, s0 + .09, 1]; an = [0, 0, .55 * pk, pk, .5 * pk, 0, 0]
        preen.append("<OrientationInterpolator DEF='WingLift%d' key='%s' keyValue='%s'/><ROUTE fromNode='PreenClock' fromField='fraction_changed' toNode='WingLift%d' toField='set_fraction'/>"
                     "<ROUTE fromNode='WingLift%d' fromField='value_changed' toNode='WingPreen%d' toField='set_rotation'/>" % (i, ' '.join(f(k) for k in ks), ', '.join('%s %s' % (v3(v), f(a_)) for a_ in an), i, i, i))
        per = round(11 + 1.7 * i, 1)
        interp.append("<TimeSensor DEF='WingClock%d' cycleInterval='%s' loop='true'/><ColorInterpolator DEF='WingTint%d' key='0 0.08 0.3 0.42 1' keyValue='0.80 0.64 0.30, %s, %s, 0.80 0.64 0.30, 0.80 0.64 0.30'/>"
                      "<ROUTE fromNode='WingClock%d' fromField='fraction_changed' toNode='WingTint%d' toField='set_fraction'/><ROUTE fromNode='WingTint%d' fromField='value_changed' toNode='Wing%d_edge' toField='set_emissiveColor'/>"
                      % (i, per, i, v3(rc), v3(rc), i, i, i, i))
    X += interp
    X.append("<TimeSensor DEF='PreenClock' cycleInterval='27' loop='true'/>" + ''.join(preen))
    anchor('wing', 'Primaries', '10 orchestrator roles; a colour = that role working · simulated until real runs replace them', add(shoulder, (3.4, 3.0, 0)))

    # ---- Blender: the i/o window at the tail root, streams converging on it, 18 plumes fanned from it
    cloud = [p for p in [(rng.uniform(9, 16.5), rng.uniform(-6.5, 4.5), rng.uniform(-6, 6)) for _ in range(40)]]
    X.append("<Transform DEF='BlenderRoot' translation='%s'>" % v3(ROOT))
    X.append("<Transform DEF='BlenderPulse'>%s%s%s</Transform>" % (glow((0, 0, 0), 1.7, BLENDER), glow((0, 0, 0), 0.8, (1.0, 0.86, 0.6)), points_shape([(0, 0, 0)], [(1.0, 0.95, 0.85)], 1, [3.0])))
    X.append(lines_shape([circle((0, 0, 0), (0, 0, 1), 0.95, 64), circle((0, 0, 0), (0, 0.4, 1), 1.25, 64)], BLENDER, transparency=0.15))
    X.append("</Transform>")
    X.append("<TimeSensor DEF='BlenderClock' cycleInterval='5.2' loop='true'/><PositionInterpolator DEF='BlenderBreath' key='0 0.5 1' keyValue='1 1 1, 1.12 1.12 1.12, 1 1 1'/>"
             "<ROUTE fromNode='BlenderClock' fromField='fraction_changed' toNode='BlenderBreath' toField='set_fraction'/><ROUTE fromNode='BlenderBreath' fromField='value_changed' toNode='BlenderPulse' toField='set_scale'/>")
    streams = []
    for k, c0 in enumerate(cloud[:16]):
        mid = add(mul(add(c0, ROOT), .5), (rng.uniform(-1, 1), rng.uniform(-1.6, 1.6), rng.uniform(-1, 1)))
        pts = []
        for i in range(25):
            t = i / 24; a = mul(c0, (1 - t) ** 2); b = mul(mid, 2 * (1 - t) * t); c = mul(ROOT, t * t); pts.append(add(add(a, b), c))
        streams.append(pts)
    X.append(lines_shape(streams, (0.62, 0.40, 0.16), transparency=0.5))
    for k in range(5):                      # five pulses that run in along the streams (simulated input traffic)
        sp = streams[k * 3]; key = ' '.join(f(i / (len(sp) - 1)) for i in range(len(sp)))
        X.append("<Transform DEF='InPulse%d' translation='%s'>%s</Transform>" % (k, v3(sp[0]), points_shape([(0, 0, 0)], [(1.0, 0.75, 0.4)], 3, [2.0])))
        X.append("<TimeSensor DEF='InClock%d' cycleInterval='%s' loop='true'/><PositionInterpolator DEF='InPath%d' key='%s' keyValue='%s'/>"
                 "<ROUTE fromNode='InClock%d' fromField='fraction_changed' toNode='InPath%d' toField='set_fraction'/><ROUTE fromNode='InPath%d' fromField='value_changed' toNode='InPulse%d' toField='set_translation'/>"
                 % (k, f(5.5 + 1.3 * k), k, key, ', '.join(v3(p) for p in sp), k, k, k, k))
    anchor('blender', 'Blender', 'the i/o window: everything in and out passes through it (the real exporter and the blenderizer)', ROOT)

    TARGETS = {1: ('O3DE', 'mock'), 3: ('ParaView', 'mock'), 5: ('3D Slicer', 'mock'), 6: ('video', 'real', (0.95, 0.30, 0.85)), 8: ('USD', 'real', (1.0, 0.93, 0.7)), 9: ('glTF', 'real', (0.25, 0.85, 1.0)),
               11: ('Unity', 'mock'), 13: ('Defold', 'mock'), 15: ('IFC', 'mock')}
    fold = []
    for i in range(18):
        th = math.radians(-82 + i * (164 / 17))
        u = norm((math.cos(th), math.sin(th), 0.10 * math.sin(th * 1.0)))
        v = norm(cross((0, 0, 1), u)); n = norm(cross(u, v))
        tg = TARGETS.get(i)
        style = 'plain' if not tg else ('mock' if tg[1] == 'mock' else ('real', tg[2]))
        L = FAN_L * (0.92 + 0.12 * math.cos(th) + rng.uniform(-.03, .03))
        xml, tip = plume_lod('Fan%d' % i, add(ROOT, mul(u, 0.9)), u, v, n, L, 1.0 if tg is None or tg[1] != 'mock' else 0.9, style, rng, 22, 8)
        # the fan unfurls the first time the camera comes near: each plume swings out from a closed fan about the root, a little later than its neighbour
        r0 = -(1 - FAN_CLOSED) * th; s0 = 0.30 * i / 17; mid = s0 + (1 - s0) * 0.45
        X.append("<Transform DEF='FanFold%d' center='%s' rotation='0 0 1 %s'>%s</Transform>" % (i, v3(ROOT), f(r0), xml))
        fold.append("<OrientationInterpolator DEF='FanSwing%d' key='0 %s %s 1' keyValue='0 0 1 %s, 0 0 1 %s, 0 0 1 %s, 0 0 1 0'/><ROUTE fromNode='FanClock' fromField='fraction_changed' toNode='FanSwing%d' toField='set_fraction'/>"
                    "<ROUTE fromNode='FanSwing%d' fromField='value_changed' toNode='FanFold%d' toField='set_rotation'/>" % (i, f(s0), f(mid), f(r0), f(r0), f(r0 * 0.12), i, i, i))
        if tg: anchor('fan_' + tg[0].lower().replace(' ', ''), tg[0], ('Blender export path · simulated for now, a real export is the ultimate vision' if tg[1] == 'real' else 'mock: outline only, no Blender path yet'), tip, 'min' if tg[1] == 'real' else 'full')
    X.append("<ProximitySensor DEF='FanSense' center='%s' size='30 30 56'/><TimeSensor DEF='FanClock' cycleInterval='4.2' loop='false'/><ROUTE fromNode='FanSense' fromField='enterTime' toNode='FanClock' toField='set_startTime'/>" % v3(add(ROOT, (8, 0, 0))))
    X += fold

    # ---- shuttles: four agents weaving across the bird on smooth closed paths, each with a short fading trail (simulated; they stand for the orchestrator's work)
    sr = random.Random(seed * 29 + 3)
    SHUT = [((11.5, -1.2, 1.2), (8.5, 2.4, 1.8), (0.0, 0.6, 1.0), 13.0, (0.25, 0.85, 0.85)), ((10.5, -3.2, -0.8), (7.5, 2.0, 2.2), (2.2, 1.7, 0.2), 17.0, (0.30, 0.65, 1.0)),
            ((13.0, 0.8, 2.4), (6.5, 3.0, 1.2), (4.0, 0.3, 2.5), 11.0, (0.30, 0.95, 0.55)), ((9.5, -2.0, -2.0), (8.8, 2.6, 1.6), (5.1, 2.4, 3.4), 19.0, (0.95, 0.35, 0.85))]
    NS, NT = 48, 5
    for j, (C, A, ph, per, rc) in enumerate(SHUT):
        wob = [(sr.uniform(0, 6.28), sr.uniform(0, 6.28), sr.uniform(0, 6.28)) for _ in range(3)]
        def spos(s, C=C, A=A, ph=ph, wob=wob):
            x = C[0] + A[0] * math.cos(2 * math.pi * s + ph[0]) + 0.16 * math.sin(2 * math.pi * 7 * s + wob[0][0])
            y = C[1] + A[1] * math.sin(4 * math.pi * s + ph[1]) + 0.14 * math.sin(2 * math.pi * 9 * s + wob[1][0])
            z = C[2] + A[2] * math.sin(2 * math.pi * s + ph[2]) + 0.14 * math.sin(2 * math.pi * 11 * s + wob[2][0])
            return (x, y, z)
        X.append("<TimeSensor DEF='ShuttleClock%d' cycleInterval='%s' loop='true'/>" % (j, f(per)))
        for m in range(NT):
            lag = 0.011 * m
            keys = [i / NS for i in range(NS + 1)]; vals = [spos((k - lag) % 1.0) for k in keys]
            head = m == 0
            col = (1.0, 0.93, 0.72) if head else tuple(min(1.0, (0.55 + 0.45 * (1 - m / NT)) * (0.62 * g + 0.38 * r_)) for g, r_ in zip((1.0, 0.82, 0.48), rc))
            X.append("<Transform DEF='Shuttle%d_%d' translation='%s'>%s</Transform><PositionInterpolator DEF='ShuttlePath%d_%d' key='%s' keyValue='%s'/>"
                     "<ROUTE fromNode='ShuttleClock%d' fromField='fraction_changed' toNode='ShuttlePath%d_%d' toField='set_fraction'/><ROUTE fromNode='ShuttlePath%d_%d' fromField='value_changed' toNode='Shuttle%d_%d' toField='set_translation'/>"
                     % (j, m, v3(vals[0]), points_shape([(0, 0, 0)], [col], 1 if head else 3, [2.6 if head else max(0.7, 2.0 - 0.32 * m)]), j, m, ' '.join(f(k) for k in keys), ', '.join(v3(v_) for v_ in vals), j, j, m, j, m, j, m))

    sway = "<Transform DEF='Loom' center='0.72 -0.76 0'>%s</Transform><ROUTE fromNode='SwayTurn' fromField='value_changed' toNode='Loom' toField='set_rotation'/>" % ''.join(X)
    # ---- viewpoints (spliced before the Deep scene's own first Viewpoint so Face is the one bound at load)
    vps = {
        'Face': dict(position=(3.0, -1.8, 13.2), orientation=(0, 0, 1, 0), fov=0.74, center=(3.0, -1.8, 0)),
        'Establishing': dict(position=(12.0, -1.5, 25.0), orientation=(0, 0, 1, 0), fov=0.88, center=(12, -1.5, 0)),
    }
    vp_xml = ''.join("<Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'/>" % (k, k, v3(d['position']), v3(d['orientation']), v3(d['center']), f(d['fov'])) for k, d in vps.items())
    vp_xml += "<Viewpoint DEF='TourCam' description='Tour' position='3 -1.8 13.2' fieldOfView='0.8'/>"
    routes = ''.join("<ROUTE fromNode='%s' fromField='bindTime' toNode='Intro' toField='set_startTime'/>" % k for k in vps)
    return dict(sway=sway, viewpoints=vp_xml, component="<component name='HAnim' level='1'/>", routes=routes, anchors=anchors, counts=dict(beads=len(bp), tenders=NTEN, wing=len(ROLES), fan=18, streams=len(streams)))
