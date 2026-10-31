"""lens_glsl.py: the hyperbolic lens of the Dynasty Loom hypersphere, for a generator. Standard library only; deterministic.

The lens (the H3 / hyperbolic-browser idea, in the Poincare ball):
  pocket point p  ->  ball point x = c g(|p|/R) p/|p|  (R = R_GLASS; c < 1 keeps every life strictly inside the ball;
                                                       g(s) = tanh(k s)/tanh(k), a radial fisheye; k = 0 gives the plain x = c p / R)
  x' = (-a) (+) x                                       (Mobius addition: the Mobius translation that carries the focus a to the centre)
  p' = x' * R                                           (back to pocket units: the glass is the ball's boundary, which every Mobius map fixes)
  drawn at mix(p, p', lensMix)                          (lensMix 0 = the exact Euclidean layout)
Opacity falls with the hyperbolic distance d = 2 artanh|x'| from the focus: 1 inside h0, easing to `floor` at h1, and to 0 at the ball's edge.

What this module gives a generator (see the README, "v5 (Artifact version 5)"):
  LENS                       the numbers (c, horizon, floor, densify steps, default); the page reads the same block from <family>.hyper.json
  patch(part_def, file, src) the GLSL injector: returns `src` with the lens (and the logDepth hook) written in, for the shader parts it knows;
                             anything else comes back unchanged. Every anchor is matched exactly once or the build stops.
  fields(shader_def)         the extra <field>s (name, type, value) for that ComposedShader: lensA, lensMix, lensC, lensK, lensHorizon, logDepth
  pick_line(pts, step)       a person's pick polyline, thinned to at most `step` pocket units a segment (lens picking projects warped points)
  page_block()               the dict the generator writes into <family>.hyper.json as "lens"
and a Python mirror of the maths (mob_add, lens_map, lens_scale, lens_fade, geodesic, sphere) that the tests compare with lens.js and GLSL.
"""
import math, re

LENS = dict(
    c=0.92,             # ball scale: pocket p -> x = c g(|p|/R) p/|p|, R = R_GLASS
    k=1.35,             # radial fisheye of the ball map, g(s) = tanh(k s)/tanh(k): 0 = linear (x = c p / R); > 0 also magnifies the centre at a = 0
    h0=1.6,             # hyperbolic distance from the focus where the fade starts (fix-1: 1.3 -> 1.6, h1 3.6 -> 4.4, floor 0.14 -> 0.3: the
    h1=4.4,             # ... and where it reaches `floor`                          review found the rest of the family faded almost to nothing)
    floor=0.3,          # opacity kept past h1 (the far field stays a faint constellation, never vanishes)
    rim=(0.975, 0.997), # |x'| band where the last of it fades to 0 (the soft horizon at the glass)
    arc_floor=0.012,    # the finest arc step (radians); see arc_step()
    pick_step=0.03,     # pocket units between pick points (lens picking projects every warped point)
    a_max=0.9,          # the focus stays inside this ball radius
    ms_toggle=1100, ms_focus=1200,   # page eases (ms)
    ring_recede=0.62,   # the armillary (outside the ball, so no Mobius map moves it) recedes toward the ground by this much at lensMix 1
    default=False,      # the page's Lens toggle at load (off: decided from frames while prototyping; see the README's v5 section)
)


# ---------------------------------------------------------------- the maths (Python mirror of lens.js and of the GLSL below)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _len(a): return math.sqrt(_dot(a, a))


def mob_add(u, v):
    """Mobius addition in the unit ball: u (+) v = ((1 + 2<u,v> + |v|^2) u + (1 - |u|^2) v) / (1 + 2<u,v> + |u|^2 |v|^2)."""
    uv, uu, vv = _dot(u, v), _dot(u, u), _dot(v, v)
    k1, k2, den = 1 + 2 * uv + vv, 1 - uu, 1 + 2 * uv + uu * vv
    return ((k1 * u[0] + k2 * v[0]) / den, (k1 * u[1] + k2 * v[1]) / den, (k1 * u[2] + k2 * v[2]) / den)


def neg(u): return (-u[0], -u[1], -u[2])


def mob_scalar(t, v):
    """t (x) v = tanh(t artanh|v|) v/|v| (the gyrovector scalar multiple)."""
    n = _len(v)
    if n < 1e-15: return (0.0, 0.0, 0.0)
    return _mul(v, math.tanh(t * math.atanh(min(n, 1 - 1e-15))) / n)


def geodesic(a0, a1, t):
    """The hyperbolic geodesic from a0 (t = 0) to a1 (t = 1): a0 (+) (t (x) ((-a0) (+) a1)). From the centre: tanh(t artanh|a1|) a1/|a1|."""
    if t >= 1: return tuple(a1)
    return mob_add(a0, mob_scalar(t, mob_add(neg(a0), a1)))


def _rad(s, k):
    """The radial profile g(s) of the ball map (s = |p|/R): tanh(k s)/tanh(k), g(1) = 1; s itself at k = 0."""
    return s if k < 1e-4 else math.tanh(k * s) / math.tanh(k)


def _rad_inv(r, k): return r if k < 1e-4 else math.atanh(min(r * math.tanh(k), 1 - 1e-15)) / k


def _ratio(s, k):
    """g(s)/s, the tangential stretch of the ball map (k/tanh(k) at the centre)."""
    if k < 1e-4: return 1.0
    return k / math.tanh(k) if s < 1e-9 else _rad(s, k) / s


def to_ball(p, c, R, k=0.0): return _mul(p, c * _ratio(_len(p) / R, k) / R)
def from_ball(x, R): return _mul(x, R)


def lens_map(p, a, mix, c, R, k=0.0):
    """Pocket point -> where the lens draws it (pocket units)."""
    if mix <= 0: return tuple(p)
    y = from_ball(mob_add(neg(a), to_ball(p, c, R, k)), R)
    return tuple(pi + (yi - pi) * mix for pi, yi in zip(p, y))


def lens_unmap(q, a, c, R, k=0.0):
    """The inverse at mix = 1: a drawn point back to the pocket point (x = a (+) x', then the radial profile undone)."""
    x = mob_add(a, _mul(q, 1.0 / R))
    if k < 1e-4: return _mul(x, R / c)
    n = _len(x)
    return (0.0, 0.0, 0.0) if n < 1e-15 else _mul(x, R * _rad_inv(n / c, k) / n)


def lens_scale(p, a, mix, c, R, k=0.0):
    """Local magnification of lens_map at p. The Mobius part is conformal: |d((-a)(+)x)/dx| = (1 - |a|^2) / (1 - 2<a,x> + |a|^2 |x|^2); the
    ball map stretches across the radius by c g(s)/s (exact for a ribbon's width across a radial fiber; at k = 0 the whole map is conformal)."""
    x = to_ball(p, c, R, k); aa = _dot(a, a)
    lam = (1 - aa) / max(1 - 2 * _dot(a, x) + aa * _dot(x, x), 1e-6)
    return 1 + (c * _ratio(_len(p) / R, k) * lam - 1) * mix


def hyp_dist(p, a, c, R, k=0.0):
    """Hyperbolic distance from the focus to p: 2 artanh|(-a) (+) x|."""
    r = min(_len(mob_add(neg(a), to_ball(p, c, R, k))), 0.999999)
    return 2 * math.atanh(r)


def _smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return t * t * (3 - 2 * t)


def lens_fade(p, a, mix, c, R, h0=LENS['h0'], h1=LENS['h1'], floor=LENS['floor'], rim=LENS['rim'], k=0.0):
    y = mob_add(neg(a), to_ball(p, c, R, k)); r = min(_len(y), 0.999999); d = 2 * math.atanh(r)
    f = (1 + (floor - 1) * _smooth(h0, h1, d)) * (1 - _smooth(rim[0], rim[1], r))
    return 1 + (f - 1) * mix


def sphere(rk, a, mix, c, R, k=0.0):
    """The time shell |p| = rk under the lens: a Mobius map sends spheres to spheres. Returns (centre, radius) in pocket units, blended by mix
    (exact at mix 0 and 1). The image is centred on the focus axis; its ends on the axis are (s - |a|)/(1 - |a| s) and (-s - |a|)/(1 + |a| s)."""
    s, al = c * _rad(rk / R, k), _len(a)
    ah = _mul(a, 1 / al) if al > 1e-9 else (0.0, 0.0, 1.0)
    e1, e2 = (s - al) / (1 - al * s), (-s - al) / (1 + al * s)
    cm, rm = _mul(ah, 0.5 * (e1 + e2) * R), 0.5 * (e1 - e2) * R
    return _mul(cm, mix), rk + (rm - rk) * mix


def arc_step(rad, R, base=0.035):
    """Densify (generator hook): the angular step for an arc on the shell of radius rad. Under the lens an arc is drawn at most about
    lambda = c / (1 - (c rad / R)^2) times larger (its magnification with the focus on it), and a chord's sagitta grows about as lambda, so the
    step shrinks by sqrt(lambda): the bend stays as smooth as v3's 0.035 rad at 1x. Inner shells, which the lens never magnifies much, keep
    nearly their old step."""
    s = min(LENS['c'] * _rad(rad / R, LENS['k']), 0.999)
    lam = LENS['c'] * _ratio(rad / R, LENS['k']) / (1 - s * s)
    return max(LENS['arc_floor'], base / math.sqrt(max(lam, 1.0)))


def pick_line(pts, step=LENS['pick_step']):
    """Thin a dense polyline to points at most `step` apart along it (first, last and every corner of more than 2 degrees kept)."""
    if len(pts) <= 2: return [tuple(p) for p in pts]
    out, acc = [tuple(pts[0])], 0.0
    for i in range(1, len(pts) - 1):
        acc += _len(_add(pts[i], neg(pts[i - 1])))
        d0, d1 = _add(pts[i], neg(pts[i - 1])), _add(pts[i + 1], neg(pts[i]))
        n0, n1 = _len(d0), _len(d1)
        corner = n0 > 1e-12 and n1 > 1e-12 and _dot(d0, d1) / (n0 * n1) < math.cos(math.radians(2.0))
        if acc >= step - 1e-12 or corner: out.append(tuple(pts[i])); acc = 0.0
    out.append(tuple(pts[-1]))
    return out


def page_block():
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in sorted(LENS.items())}


# ---------------------------------------------------------------- the GLSL (ES 3.00; no '%' and no ']]>': the parts travel as data: URLs)
def _f(x): s = repr(float(x)); return s if ('.' in s or 'e' in s) else s + '.'

GLSL_LIB = """// LENS (nav/lib/lens_glsl.py): the hyperbolic lens. Pocket p -> ball x = p lensC / LENS_R; x' = (-lensA) (+) x (Mobius addition: the
// translation that carries the focus to the centre); back p' = x' LENS_R; drawn at mix(p, p', lensMix). lensHorizon = (h0, h1, floor): opacity 1
// within hyperbolic distance h0 of the focus, easing to floor at h1 and to 0 at the glass. lensMix 0 leaves every vertex where it was.
uniform vec3 lensA, lensHorizon;
uniform float lensMix, lensC, lensK;   // lensK: the radial fisheye g(s) = tanh(k s)/tanh(k) of the ball map (0 = linear)
const float LENS_R = @R@;
float lensRad(float s) { return lensK > 1e-4 ? tanh(lensK * s) / tanh(lensK) : s; }
float lensRatio(vec3 p) { float s = length(p) / LENS_R; return lensK > 1e-4 ? (s > 1e-6 ? lensRad(s) / s : lensK / tanh(lensK)) : 1.; }
vec3 lensBall(vec3 p) { return p * (lensC * lensRatio(p) / LENS_R); }
vec3 lensMob(vec3 u, vec3 v) {
  float uv = dot(u, v), uu = dot(u, u), vv = dot(v, v);
  return ((1. + 2. * uv + vv) * u + (1. - uu) * v) / (1. + 2. * uv + uu * vv);
}
vec3 lensWarp(vec3 p) { return mix(p, lensMob(-lensA, lensBall(p)) * LENS_R, lensMix); }
float lensScale(vec3 p) {
  vec3 x = lensBall(p); float aa = dot(lensA, lensA);
  return mix(1., lensC * lensRatio(p) * (1. - aa) / max(1. - 2. * dot(lensA, x) + aa * dot(x, x), 1e-6), lensMix);
}
float lensFade(vec3 p) {
  float r = min(length(lensMob(-lensA, lensBall(p))), .999999), d = 2. * atanh(r);
  float f = mix(1., lensHorizon.z, smoothstep(lensHorizon.x, lensHorizon.y, d)) * (1. - smoothstep(@RIM0@, @RIM1@, r));
  return mix(1., f, lensMix);
}
"""

GLSL_SPHERE = """// LENS: the time shell |p| = rk under the lens is a sphere again, centred on the focus axis (exact at lensMix 0 and 1)
void lensSphere(float rk, out vec3 cc, out float rr) {
  float s = lensC * lensRad(rk / LENS_R), al = length(lensA);
  vec3 ah = al > 1e-6 ? lensA / al : vec3(0., 0., 1.);
  float e1 = (s - al) / (1. - al * s), e2 = (-s - al) / (1. + al * s);
  cc = ah * (.5 * (e1 + e2) * LENS_R * lensMix); rr = mix(rk, .5 * (e1 - e2) * LENS_R, lensMix);
}
"""

GLSL_LOGDEPTH = """uniform float logDepth, x3d_LogarithmicFarFactor1_2;   // logDepth: the page sets it from X_ITE's LogarithmicDepthBuffer option
float fragZ() { return logDepth > .5 ? log2(1. + 1. / gl_FragCoord.w) * x3d_LogarithmicFarFactor1_2 : gl_FragCoord.z; }
"""
DEPTHOF_OLD = "float depthOf(vec3 p) { vec4 c = x3d_ProjectionMatrix * (x3d_ModelViewMatrix * vec4(p, 1.)); return clamp(c.z / c.w * .5 + .5, 0., 1.); }\n"
DEPTHOF_NEW = ("float depthOf(vec3 p) { vec4 c = x3d_ProjectionMatrix * (x3d_ModelViewMatrix * vec4(p, 1.)); "
               "if (logDepth > .5) return log2(1. + c.w) * x3d_LogarithmicFarFactor1_2; return clamp(c.z / c.w * .5 + .5, 0., 1.); }\n")


def _lib(R):
    return GLSL_LIB.replace('@R@', _f(R)).replace('@RIM0@', _f(LENS['rim'][0])).replace('@RIM1@', _f(LENS['rim'][1]))


# Each edit: (old, new). `old` must occur exactly once in the source.
def _fiber_vert(R):
    return [
        ("float inLine(float x) {\n", "out float vLens;   // LENS: 1 at the focus, toward lensHorizon.z past h1\n" + _lib(R) + "float inLine(float x) {\n"),
        ("  vec4 pe = x3d_ModelViewMatrix * x3d_Vertex;\n  vec3 te = mat3(x3d_ModelViewMatrix) * aTan;\n",
         "  vec3 lp = x3d_Vertex.xyz, lt = aTan; float lk = 1.; vLens = 1.;\n"
         "  if (lensMix > 0.) {   // LENS: the point, its tangent (a finite difference: the map is conformal) and the local magnification\n"
         "    lp = lensWarp(x3d_Vertex.xyz); lt = lensWarp(x3d_Vertex.xyz + aTan * 1e-3) - lp; lt = length(lt) > 1e-9 ? normalize(lt) : aTan;\n"
         "    lk = lensScale(x3d_Vertex.xyz); vLens = lensFade(x3d_Vertex.xyz);\n  }\n"
         "  vec4 pe = x3d_ModelViewMatrix * vec4(lp, 1.);\n  vec3 te = mat3(x3d_ModelViewMatrix) * lt;\n"),
        ("  float wEye = uWidth * wk * taper * sc;\n", "  float wEye = uWidth * wk * taper * sc * lk;\n"),
        ("  vFade = min(wEye / w, 1.) * smoothstep(.015, .06, -pe.z / sc);\n", "  vFade = min(wEye / w, 1.) * smoothstep(.015, .06, -pe.z / sc) * vLens;\n"),
    ]


FIBER_FRAG = [
    ("in vec3 vDye; in float vS, vYear, vSeed, vKind, vEst, vFade, vPa, vPb, vSel, vAlong, vSheen;\n",
     "in vec3 vDye; in float vS, vYear, vSeed, vKind, vEst, vFade, vPa, vPb, vSel, vAlong, vSheen;\nin float vLens;   // LENS (nav/lib/lens_glsl.py)\n"),
    ("      x3d_FragColor = vec4(mix(c, S_GROUND_TOP, (1. - est) * .55), 1.);",
     "      if (vLens < .03) discard;   // LENS: past the horizon the ink thins into the ground\n"
     "      x3d_FragColor = vec4(mix(mix(c, S_GROUND_TOP, (1. - est) * .55), S_GROUND_TOP, 1. - vLens), 1.);"),
    ("a = max(a, exp(-q2 * 60.) * (1. - uFocus));", "a = max(a, exp(-q2 * 60.) * (1. - uFocus) * vLens);"),
    ("    x3d_FragColor = vec4(core * (.7 + .3 * vFade) * kc, 1.);\n",
     "    if (vLens < .03) discard;   // LENS\n    x3d_FragColor = vec4(core * (.7 + .3 * vFade) * kc * vLens, 1.);\n"),
    ("e += core * (.7 + .3 * vFade) * exp(-s2 * 60.) * (1. - uFocus);", "e += core * (.7 + .3 * vFade) * exp(-s2 * 60.) * (1. - uFocus) * vLens;"),
]


LD = 'logDepth'   # an edit tagged LD writes the logDepth hook; patch() skips it when the source already declares `uniform float logDepth` (v2)


def _shell_frag(R):
    return [
        ("uniform int uQ, uBlend;\n", "uniform int uQ, uBlend;\n" + _lib(R) + GLSL_SPHERE),
        ("uniform int uQ, uBlend;\n", "uniform int uQ, uBlend;\n" + GLSL_LOGDEPTH, LD),
        (DEPTHOF_OLD, DEPTHOF_NEW, LD),
        ("  float depth = gl_FragCoord.z;\n", "  float depth = fragZ();\n", LD),
        ("float dep = gl_FragCoord.z, cr = sqrt(rr),", "float dep = fragZ(), cr = sqrt(rr),", LD),
        # ink: the 50-year shells as limb circles of the warped spheres
        ("        float rk = uR0 + (yk - uY0) * uK;\n        if (rr <= rk * rk) continue;\n"
         "        float woven = smoothstep(uFell + 3., uFell - 3., yk), ak = asin(clamp(rk / cr, 0., 1.));\n"
         "        over(acc, mix(S_PAST, S_PRESENT, smoothstep(.05, 1.05, rk)), S_SHELL_A * exp(-pow((ak - beta) / pxr / .8, 2.)) * mix(.35, 1., woven));\n",
         "        float rk0 = uR0 + (yk - uY0) * uK, rk; vec3 lc; lensSphere(rk0, lc, rk);   // LENS: the shell's image (centre lc, radius rk)\n"
         "        vec3 lo = ro - lc; float lo2 = dot(lo, lo);\n        if (lo2 <= rk * rk) continue;\n"
         "        float lr = sqrt(lo2), lbeta = acos(clamp(dot(rd, -lo / max(lr, 1e-5)), -1., 1.));\n"
         "        float woven = smoothstep(uFell + 3., uFell - 3., yk), ak = asin(clamp(rk / lr, 0., 1.));\n"
         "        over(acc, mix(S_PAST, S_PRESENT, smoothstep(.05, 1.05, rk0)), S_SHELL_A * exp(-pow((ak - lbeta) / pxr / .8, 2.)) * mix(.35, 1., woven));\n"),
        # screen: the emitting shells, intersected as warped spheres
        ("      float rk = uR0 + (yk - uY0) * uK, hk = rk * rk - d2;\n",
         "      float rk0 = uR0 + (yk - uY0) * uK, rk; vec3 lc; lensSphere(rk0, lc, rk);   // LENS\n"
         "      vec3 lo = ro - lc; float lb = dot(lo, rd), ltc = -lb, hk = rk * rk - max(dot(lo, lo) - lb * lb, 0.);\n"),
        ("exp(-pow((rk - rWave) / .045, 2.))", "exp(-pow((rk0 - rWave) / .045, 2.))"),
        ("vec3 c = timeTint(rk) * line", "vec3 c = timeTint(rk0) * line"),
        ("      if (tc - sk > t0) E += c;", "      if (ltc - sk > t0) E += c;"),
        ("      if (tc + sk > t0) E += c * .5;", "      if (ltc + sk > t0) E += c * .5;"),
        ("    float hf = rFell * rFell - d2;                         // the fell: the shell being woven now glows hot\n    if (hf > 0. && rFell < uR) {\n",
         "    vec3 fc; float fr; lensSphere(rFell, fc, fr);          // the fell: the shell being woven now glows hot (LENS: its image)\n"
         "    vec3 fo = ro - fc; float fb = dot(fo, rd), ftc = -fb, hf = fr * fr - max(dot(fo, fo) - fb * fb, 0.);\n"
         "    if (hf > 0. && rFell < uR) {\n"),
        ("      float sf = sqrt(hf), cf = sf / rFell;\n", "      float sf = sqrt(hf), cf = sf / fr;\n"),
        ("      if (tc - sf > t0) E += c;\n      if (tc + sf > t0) E += c * .45;\n", "      if (ftc - sf > t0) E += c;\n      if (ftc + sf > t0) E += c * .45;\n"),
    ]


SEED_FRAG = [
    ("uniform int uBlend;\n", "uniform int uBlend;\n" + GLSL_LOGDEPTH, LD),
    (DEPTHOF_OLD, DEPTHOF_NEW, LD),
]

# the armillary (host scene): it sits outside the ball, where no Mobius map of the ball should move it, so with the lens on it recedes
# toward the ground (ink) or dims (light) instead of cutting across the warped content (fix-1)
RING_FRAG = [
    ("uniform vec3 uTint;", "uniform float lensMix;   // LENS (nav/lib/lens_glsl.py): the armillary recedes while the lens is on\nuniform vec3 uTint;"),
    ("  x3d_FragColor = vec4((S_INK > .5 ? clamp(col, 0., 1.) : encode(col, uExposure))",
     "  col = S_INK > .5 ? mix(col, S_GROUND_TOP, @RR@ * lensMix) : col * (1. - @RR@ * lensMix);   // LENS\n"
     "  x3d_FragColor = vec4((S_INK > .5 ? clamp(col, 0., 1.) : encode(col, uExposure))"),
]


def edits_for(part_def, filename, R):
    """The edits for one ShaderPart, by its DEF and source file. The seed's mesh (SeedVS) and the bead are moved by the page (SeedXf, BeadXf)
    from the CPU mirror, so ring.vert is left alone (the host's armillary uses it too)."""
    if filename == 'fiber.vert.glsl': return _fiber_vert(R)
    if filename == 'fiber.frag.glsl': return FIBER_FRAG
    if filename == 'shell.frag.glsl': return _shell_frag(R)
    if filename == 'seed.frag.glsl': return SEED_FRAG
    if filename == 'ring.frag.glsl': return [(o, n.replace('@RR@', _f(LENS['ring_recede']))) for o, n in RING_FRAG]
    return []


def has_logdepth(src):
    """True when a shader source already declares its own logDepth hook (the v2 generator's shell.frag and seed.frag do)."""
    return re.search(r'^\s*uniform\s+float\s+logDepth\b', src, re.M) is not None


def patch(part_def, filename, src, R):
    """Write the lens into one ShaderPart's source. Edits tagged LD (the logDepth hook) are skipped when the source has its own hook."""
    own = has_logdepth(src)
    for e in edits_for(part_def, filename, R):
        old, new = e[0], e[1]
        if len(e) > 2 and e[2] == LD and own: continue
        n = src.count(old)
        if n != 1: raise SystemExit('lens_glsl: anchor found %d times in %s (%s): %r' % (n, filename, part_def, old[:90]))
        src = src.replace(old, new)
    if own and filename in ('shell.frag.glsl', 'seed.frag.glsl') and 'gl_FragCoord.z;' in src.replace('gl_FragCoord.z;   //', '') and 'fragDepth()' not in src:
        raise SystemExit('lens_glsl: %s declares logDepth but still writes the plain depth' % filename)
    if '%' in src or ']]>' in src: raise SystemExit('lens_glsl: patched %s holds %% or ]]>' % filename)
    return src


def fields(shader_def, have=()):
    """Extra fields for a ComposedShader, as (name, type, value). Lens fields where the vertex or fragment part is patched with the lens;
    logDepth wherever the fragment part writes gl_FragDepth. `have` is the shader's own field list (tuples or names): a field it already
    declares (v2's logDepth) is not added twice."""
    names = {h[0] if isinstance(h, (tuple, list)) else h for h in have}
    lens = [('lensA', 'SFVec3f', '0 0 0'), ('lensMix', 'SFFloat', '0'), ('lensC', 'SFFloat', _g(LENS['c'])), ('lensK', 'SFFloat', _g(LENS['k'])),
            ('lensHorizon', 'SFVec3f', '%s %s %s' % (_g(LENS['h0']), _g(LENS['h1']), _g(LENS['floor'])))]
    logd = [('logDepth', 'SFFloat', '0')]
    out = {'FiberCore': lens, 'FiberGlow': lens, 'ShellShader': lens + logd, 'SeedGlow': logd, 'BeadGlow': logd,
           'RingShader': [('lensMix', 'SFFloat', '0')]}.get(shader_def, [])
    return [f for f in out if f[0] not in names]


def _g(x): return ('%.6g' % x)
