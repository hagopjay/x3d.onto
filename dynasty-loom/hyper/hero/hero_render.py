"""Cycles hero still of the dynasty hypersphere (Loom). Generator, not file: the PNG plate and its stats JSON are rebuilt from this script.

Run with the bpy virtualenv (Blender 5.2.3 as a module), isolated:
    venv-bpy/bin/python -I hero_render.py --geometry G.json --pocket P.x3d --shot wide|tall --res 1600x900 --samples 96 --out plate.png --stats stats.json

Reads only (never edits): the build's <family>.geometry.json (fibers, arcs, seed, time shells, glass) and pocket-<family>.x3d (the Wide Viewpoint,
copied as-is). Everything is built in X3D coordinates (Y up) under one root turned +90 degrees about X, so the X3D Viewpoint pose is used unchanged.

Look (from docs/look-bible.md, translated to a path tracer):
  fibers   curves with a hot core (dye normalised to its max channel, whitening toward the tube centre) and a transparent glow sheath;
           kinds as the page: bends 0.7 wide x0.75, unions 0.75 wide x1.2, close unions x1.5, founders' root lines faint (layout only);
           a segment with an estimated year is dashed (4 on / 3 off, as the page) and its glow drops to 0.45.
  seed     an emissive core r 0.012 and a centre-weighted glow (proxy r 0.24), plus a warm point light that lights the gold.
  glass    a thin shell (r 1.1): Fresnel (IOR 1.45) between pass-through and a sharp mirror, so it reflects and does not bend with a Schlick-shaped blue rim; time shells 1750-2000 as faint limb lines,
           warm at the core to cool at the glass, far crossing x0.5; a violet haze body.
  frame    the gold armillary (host rings / 6, the pocket's scale in its host), metallic gold.
  world    a dark procedural nebula (violet / teal, galactic band, rose) and hashed stars, nothing fetched.
  camera   the pocket's Wide Viewpoint (camera-grammar.md: sph(0, 16 deg, d), shell fills 74%); fieldOfView spans the smaller side, as in X_ITE.
           Depth of field focused on the seed.
  post     OpenImageDenoise, AgX view transform, compositor Bloom (real, in the render) plus a wide Fog Glow.
"""
import argparse, json, math, re, sys, time, hashlib
import xml.etree.ElementTree as ET
import bpy
from mathutils import Matrix, Vector

SEED = 7
R_GLASS_OUT = 1.10
RINGS = [(6.95, 0.022, (1, 0, 0.25), 0.32), (7.75, 0.03, (0.2, 0, 1), 1.05), (8.35, 0.02, (1, 0.3, 0), -0.62)]   # host units (build_hypersphere.RINGS)
HOST_SCALE = 6.0                                    # the pocket sits in its host at scale 6
KIND = {  # radius (pocket units), intensity, glow radius
    'life':  (0.0032, 1.00, 0.012),
    'spawn': (0.0023, 0.75, 0.009),
    'union': (0.0025, 1.20, 0.010),
    'close': (0.0025, 1.50, 0.011),
    'root':  (0.0018, 0.45, 0.006),
}
DASH_ON, DASH_OFF = 0.016, 0.012                    # pocket units (about 4 on / 3 off years at 313.5 years per unit)
CORE_STRENGTH, GLOW_STRENGTH, GLASS_IOR, HAZE = 1.6, 1.6, 1.45, 0.035
SHELL_LIMB = (0.3, 0.0006, 0.006)                  # a exp(-cos^2/k) + b/max(cos, 0.05): the look bible's 0.045 and 0.0012, raised for a still
RING_TUBE_X = 2.0                                   # gold tubes drawn 2x the page's (host 0.022-0.03) so they read at poster size
STUDIO = (0.22, 0.012)                               # glossy-only dome: top strength, floor (warm white)
RIM_GAIN, NEBULA_GAIN, SEED_GLOW, SOFTBOX_W = 2.6, 0.8, 4.0, 220.0


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def neon(rgb):
    m = max(rgb) or 1.0
    return tuple(srgb_to_lin(min(1.0, c / m)) for c in rgb)


# ------------------------------------------------------------------ scene plumbing
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    root = bpy.data.objects.new('X3DRoot', None)          # X3D (Y up) -> Blender (Z up)
    sc.collection.objects.link(root)
    root.rotation_euler = (math.pi / 2, 0, 0)
    return sc, root


def link(obj, root):
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = root
    return obj


def nodes_of(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return nt, nt.nodes, nt.links


def math_node(N, op, a=None, b=None, L=None, clamp=False):
    n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            L.new(v, n.inputs[i])
    return n.outputs[0]


def centre_weight(N, L, blend=0.5):
    """1 at the tube or sphere centre (facing the camera), 0 at the limb"""
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    return math_node(N, 'SUBTRACT', 1.0, lw.outputs['Facing'], L, clamp=True)


def mix_io(mix):
    """the colour A, B inputs and the colour output of a ShaderNodeMix in RGBA mode"""
    ins = [i for i in mix.inputs if i.type == 'RGBA']
    outs = [o for o in mix.outputs if o.type == 'RGBA']
    return ins[0], ins[1], outs[0]


def object_colour(N):
    oi = N.new('ShaderNodeObjectInfo')
    return oi.outputs['Color']


# ------------------------------------------------------------------ materials
def mat_core(name, intensity):
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    c = centre_weight(N, L)
    hot = math_node(N, 'POWER', c, 6.0, L)
    hot = math_node(N, 'MULTIPLY', hot, 0.25, L)
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    L.new(hot, mix.inputs['Factor']); L.new(object_colour(N), mix_io(mix)[0]); mix_io(mix)[1].default_value = (1.0, 0.93, 0.84, 1)
    em = N.new('ShaderNodeEmission'); L.new(mix_io(mix)[2], em.inputs['Color'])
    em.inputs['Strength'].default_value = CORE_STRENGTH * intensity
    out = N.new('ShaderNodeOutputMaterial'); L.new(em.outputs[0], out.inputs['Surface'])
    return m


def mat_glow(name, gain):
    """transparent sheath whose emission peaks on the tube axis: a 3D glow that the lens can defocus"""
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    c = centre_weight(N, L)
    prof = math_node(N, 'POWER', c, 3.0, L)
    em = N.new('ShaderNodeEmission'); L.new(object_colour(N), em.inputs['Color'])
    L.new(math_node(N, 'MULTIPLY', prof, GLOW_STRENGTH * gain, L), em.inputs['Strength'])
    tr = N.new('ShaderNodeBsdfTransparent')
    add = N.new('ShaderNodeAddShader'); L.new(tr.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1])
    out = N.new('ShaderNodeOutputMaterial'); L.new(add.outputs[0], out.inputs['Surface'])
    m.cycles.emission_sampling = 'NONE'          # a glow, not a lamp: do not spend light samples on it
    return m


def mat_veil(name, colour, strength, power, back=1.0, limb=None):
    """transparent sphere with emission by viewing angle: power > 0 peaks face-on (haze, seed glow);
    limb=(a, b, k) gives the time shells' limb line a*exp(-cos^2/k) + b/max(cos, 0.05)"""
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    c = centre_weight(N, L)
    if limb:
        a, b, k = limb
        c2 = math_node(N, 'MULTIPLY', c, c, L)
        g = math_node(N, 'EXPONENT', math_node(N, 'DIVIDE', c2, -k, L), None, L)
        g = math_node(N, 'MULTIPLY', g, a, L)
        f = math_node(N, 'DIVIDE', b, math_node(N, 'MAXIMUM', c, 0.05, L), L)
        w = math_node(N, 'ADD', g, f, L)
    else:
        w = math_node(N, 'POWER', c, power, L)
    if back != 1.0:
        geo = N.new('ShaderNodeNewGeometry')
        bf = math_node(N, 'MULTIPLY_ADD', geo.outputs['Backfacing'], back - 1.0, L); bf.node.inputs[2].default_value = 1.0
        w = math_node(N, 'MULTIPLY', w, bf, L)
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*colour, 1)
    L.new(math_node(N, 'MULTIPLY', w, strength, L), em.inputs['Strength'])
    tr = N.new('ShaderNodeBsdfTransparent')
    add = N.new('ShaderNodeAddShader'); L.new(tr.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1])
    out = N.new('ShaderNodeOutputMaterial'); L.new(add.outputs[0], out.inputs['Surface'])
    m.cycles.emission_sampling = 'NONE'
    return m


def mat_emit(name, colour, strength):
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*colour, 1); em.inputs['Strength'].default_value = strength
    out = N.new('ShaderNodeOutputMaterial'); L.new(em.outputs[0], out.inputs['Surface'])
    return m


def mat_glass(name, rim=True):
    """clear glass; the outer face also carries a blue rim (0.55, 0.68, 1.0) x (0.9 (1-cos)^7 + 0.012 (1-cos)^2): the page's (1.1, 6, 0.05) filled the disc in blue"""
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    # a thin shell as Fresnel(IOR) between a straight pass-through and a mirror: no bending, no light-sampled speckle
    # (a rough thin-walled Principled sampled the emissive fibers through NEE and denoised into a grey, blue-cast disc: preview 3)
    fr = N.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = GLASS_IOR
    tr = N.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (0.97, 0.98, 1.0, 1)
    gs = N.new('ShaderNodeBsdfGlossy'); gs.inputs['Roughness'].default_value = 0.0; gs.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1)
    # mirror only on the outside: from inside, the concave back wall magnified the fiber ball into a white annulus (preview 5, diagnosis e1/e3)
    geo0 = N.new('ShaderNodeNewGeometry')
    fr_out = math_node(N, 'MULTIPLY', fr.outputs[0], math_node(N, 'SUBTRACT', 1.0, geo0.outputs['Backfacing'], L), L)
    gl = N.new('ShaderNodeMixShader'); L.new(fr_out, gl.inputs[0]); L.new(tr.outputs[0], gl.inputs[1]); L.new(gs.outputs[0], gl.inputs[2])
    sh = gl.outputs[0]
    if rim:
        lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        f = lw.outputs['Facing']
        r6 = math_node(N, 'MULTIPLY', math_node(N, 'POWER', f, 7.0, L), 0.9, L)
        r2 = math_node(N, 'MULTIPLY', math_node(N, 'POWER', f, 2.0, L), 0.012, L)
        geo = N.new('ShaderNodeNewGeometry')
        front = math_node(N, 'SUBTRACT', 1.0, geo.outputs['Backfacing'], L)
        w = math_node(N, 'MULTIPLY', math_node(N, 'ADD', r6, r2, L), front, L)
        em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (srgb_to_lin(0.55), srgb_to_lin(0.68), 1.0, 1)
        L.new(math_node(N, 'MULTIPLY', w, RIM_GAIN, L), em.inputs['Strength'])
        add = N.new('ShaderNodeAddShader'); L.new(gl.outputs[0], add.inputs[0]); L.new(em.outputs[0], add.inputs[1])
        sh = add.outputs[0]
    out = N.new('ShaderNodeOutputMaterial'); L.new(sh, out.inputs['Surface'])
    m.cycles.emission_sampling = 'NONE'
    return m


def mat_gold(name):
    m = bpy.data.materials.new(name); nt, N, L = nodes_of(m)
    p = N.new('ShaderNodeBsdfPrincipled')
    p.inputs['Base Color'].default_value = (1.0, 0.78, 0.45, 1); p.inputs['Metallic'].default_value = 1.0; p.inputs['Roughness'].default_value = 0.22
    out = N.new('ShaderNodeOutputMaterial'); L.new(p.outputs[0], out.inputs['Surface'])
    return m


# ------------------------------------------------------------------ geometry
def uv_sphere(name, r, seg=96, rings=48, flip=False):
    verts, faces = [], []
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            verts.append((r * math.sin(th) * math.cos(ph), r * math.cos(th), r * math.sin(th) * math.sin(ph)))
    top, bot = len(verts), len(verts) + 1
    verts += [(0, r, 0), (0, -r, 0)]
    def v(i, j): return (i - 1) * seg + (j % seg)
    for j in range(seg):
        faces.append((top, v(1, j + 1), v(1, j)))
        faces.append((bot, v(rings - 1, j), v(rings - 1, j + 1)))
    for i in range(1, rings - 1):
        for j in range(seg):
            faces.append((v(i, j), v(i, j + 1), v(i + 1, j + 1), v(i + 1, j)))
    if flip:
        faces = [tuple(reversed(f)) for f in faces]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    me.shade_smooth()
    return me, sum(1 if len(f) == 3 else 2 for f in faces)


def torus_mesh(name, R, r, M=320, Nn=14):
    verts, faces = [], []
    for i in range(M):
        u = 2 * math.pi * i / M; cu, su = math.cos(u), math.sin(u)
        for j in range(Nn):
            w = 2 * math.pi * j / Nn; cw, sw = math.cos(w), math.sin(w)
            verts.append(((R + r * cw) * cu, r * sw, (R + r * cw) * su))
    for i in range(M):
        for j in range(Nn):
            a, b = i * Nn + j, ((i + 1) % M) * Nn + j
            c, d = ((i + 1) % M) * Nn + (j + 1) % Nn, i * Nn + (j + 1) % Nn
            faces.append((a, d, c, b))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); me.shade_smooth()
    return me, 2 * len(faces)


def add_mesh(root, name, me, mat):
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), root)


def poly_curve(name, runs, radius, resolution=2):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_mode = 'ROUND'; cu.bevel_depth = radius; cu.bevel_resolution = resolution; cu.use_fill_caps = True
    for pts in runs:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            p.co = (q[0], q[1], q[2], 1.0)
    return cu


def split_runs(points, est):
    """[(estimated?, [points])]: a segment is estimated when either end's year is not in the data (the honest side)"""
    runs = []
    for i in range(len(points) - 1):
        e = bool(est[i] or est[i + 1])
        if runs and runs[-1][0] == e:
            runs[-1][1].append(points[i + 1])
        else:
            runs.append((e, [points[i], points[i + 1]]))
    return runs


def dashes(pts):
    """cut a polyline into DASH_ON pieces with DASH_OFF gaps, by arc length"""
    out, cur, s, on = [], [pts[0]], 0.0, True
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b); t0 = 0.0
        while seg - t0 > 1e-9:
            left = (DASH_ON if on else DASH_OFF) - s
            step = min(left, seg - t0)
            t1 = t0 + step
            p = tuple(a[k] + (b[k] - a[k]) * t1 / seg for k in range(3))
            if on:
                cur.append(p)
            s += step; t0 = t1
            if s >= (DASH_ON if on else DASH_OFF) - 1e-12:
                if on and len(cur) > 1:
                    out.append(cur)
                on = not on; s = 0.0; cur = [p]
    if on and len(cur) > 1:
        out.append(cur)
    return out


GLOW_SHEATHS = True


def build_fibers(root, geo, stats):
    mats = {}
    def mat(kind, est, glow):
        key = (kind, est, glow)
        if key not in mats:
            r, inten, gr = KIND[kind]
            if glow:
                mats[key] = mat_glow('Glow_%s%s' % (kind, '_est' if est else ''), inten * (0.45 if est else 1.0))
            else:
                mats[key] = mat_core('Core_%s%s' % (kind, '_est' if est else ''), inten * (0.6 if est else 1.0))
        return mats[key]
    n_obj = n_seg = n_dashed = 0
    for i, pl in enumerate(geo['polylines']):
        kind = pl['kind']; r, inten, gr = KIND[kind]
        col = (*neon(pl['color']), 1.0)
        for j, (est, pts) in enumerate(split_runs([tuple(p) for p in pl['points']], pl['estimated'])):
            n_seg += len(pts) - 1
            core_runs = dashes(pts) if est else [pts]
            n_dashed += len(core_runs) if est else 0
            for glow in ((False, True) if GLOW_SHEATHS else (False,)):
                runs = core_runs if (est or not glow) else [pts]
                cu = poly_curve('F%03d_%d_%s' % (i, j, 'g' if glow else 'c'), runs, gr if glow else r, 1 if glow else 2)
                ob = link(bpy.data.objects.new(cu.name, cu), root)
                ob.data.materials.append(mat(kind, est, glow)); ob.color = col
                if glow:
                    ob.visible_shadow = False
                n_obj += 1
    stats['fiber_objects'] = n_obj; stats['fiber_segments'] = n_seg; stats['dash_pieces'] = n_dashed


def build_world(sc):
    w = bpy.data.worlds.new('Nebula'); sc.world = w
    w.use_nodes = True; nt = w.node_tree; N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    tc = N.new('ShaderNodeTexCoord')
    nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; L.new(tc.outputs['Generated'], nrm.inputs[0])
    d = nrm.outputs[0]
    # galactic band: pole (0.28, 0.92, -0.27) in X3D -> (0.28, 0.27, 0.92) in Blender, weight exp(-7 lat^2)
    pole = Vector((0.28, 0.27, 0.92)).normalized()
    dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'; L.new(d, dp.inputs[0]); dp.inputs[1].default_value = pole
    lat2 = math_node(N, 'MULTIPLY', dp.outputs['Value'], dp.outputs['Value'], L)
    band = math_node(N, 'EXPONENT', math_node(N, 'MULTIPLY', lat2, -7.0, L), None, L)
    # domain-warped fbm nebula
    warp = N.new('ShaderNodeTexNoise'); warp.noise_dimensions = '3D'
    warp.inputs['Scale'].default_value = 1.6; warp.inputs['Detail'].default_value = 4; warp.inputs['Distortion'].default_value = 0.0
    L.new(d, warp.inputs['Vector'])
    wv = N.new('ShaderNodeVectorMath'); wv.operation = 'MULTIPLY_ADD'
    L.new(warp.outputs['Color'], wv.inputs[0]); wv.inputs[1].default_value = (0.9, 0.9, 0.9); L.new(d, wv.inputs[2])
    neb = N.new('ShaderNodeTexNoise'); neb.noise_dimensions = '3D'
    neb.inputs['Scale'].default_value = 2.4; neb.inputs['Detail'].default_value = 8; neb.inputs['Roughness'].default_value = 0.58
    L.new(wv.outputs[0], neb.inputs['Vector'])
    dens = N.new('ShaderNodeMapRange'); dens.inputs['From Min'].default_value = 0.42; dens.inputs['From Max'].default_value = 0.78
    dens.interpolation_type = 'SMOOTHSTEP'; L.new(neb.outputs['Fac'], dens.inputs['Value'])
    hue = N.new('ShaderNodeTexNoise'); hue.inputs['Scale'].default_value = 1.1; hue.inputs['Detail'].default_value = 2
    L.new(d, hue.inputs['Vector'])
    hmap = N.new('ShaderNodeMapRange'); hmap.inputs['From Min'].default_value = 0.35; hmap.inputs['From Max'].default_value = 0.65
    hmap.interpolation_type = 'SMOOTHSTEP'; L.new(hue.outputs['Fac'], hmap.inputs['Value'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    L.new(hmap.outputs[0], mix.inputs['Factor'])
    mix_io(mix)[0].default_value = (0.36, 0.05, 0.50, 1); mix_io(mix)[1].default_value = (0.02, 0.30, 0.42, 1)
    # rose knots where the nebula is densest
    rose = N.new('ShaderNodeMix'); rose.data_type = 'RGBA'
    rk = math_node(N, 'POWER', dens.outputs[0], 3.0, L)
    L.new(math_node(N, 'MULTIPLY', rk, 0.45, L), rose.inputs['Factor']); L.new(mix_io(mix)[2], mix_io(rose)[0]); mix_io(rose)[1].default_value = (0.8, 0.2, 0.32, 1)
    mad = math_node(N, 'MULTIPLY_ADD', band, 0.20, L); mad.node.inputs[2].default_value = 0.06    # 0.06 + 0.2 band
    amp = math_node(N, 'MULTIPLY', mad, dens.outputs[0], L)
    nebc = N.new('ShaderNodeVectorMath'); nebc.operation = 'SCALE'
    L.new(mix_io(rose)[2], nebc.inputs[0]); L.new(math_node(N, 'MULTIPLY', amp, NEBULA_GAIN, L), nebc.inputs['Scale'])
    # stars: two hashed layers (Voronoi cells), ~4.5% and ~1.5% of cells lit
    def star_layer(scale, keep, radius, gain):
        v = N.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = scale; v.inputs['Randomness'].default_value = 0.9
        L.new(d, v.inputs['Vector'])
        sep = N.new('ShaderNodeSeparateColor'); L.new(v.outputs['Color'], sep.inputs[0])
        lit = math_node(N, 'GREATER_THAN', sep.outputs[0], 1.0 - keep, L)
        core = N.new('ShaderNodeMapRange'); core.inputs['From Min'].default_value = 0.0; core.inputs['From Max'].default_value = radius
        core.inputs['To Min'].default_value = 1.0; core.inputs['To Max'].default_value = 0.0; core.interpolation_type = 'SMOOTHSTEP'
        L.new(v.outputs['Distance'], core.inputs['Value'])
        mag = math_node(N, 'MULTIPLY_ADD', math_node(N, 'POWER', sep.outputs[1], 4.0, L), 4.5, L); mag.node.inputs[2].default_value = 0.5
        e = math_node(N, 'MULTIPLY', math_node(N, 'MULTIPLY', lit, core.outputs[0], L), math_node(N, 'MULTIPLY', mag, gain, L), L)
        tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; L.new(sep.outputs[2], tint.inputs['Factor'])
        mix_io(tint)[0].default_value = (1.0, 0.74, 0.52, 1); mix_io(tint)[1].default_value = (0.72, 0.84, 1.0, 1)
        sc_ = N.new('ShaderNodeVectorMath'); sc_.operation = 'SCALE'; L.new(mix_io(tint)[2], sc_.inputs[0]); L.new(e, sc_.inputs['Scale'])
        return sc_.outputs[0]
    s1 = star_layer(150.0, 0.045, 0.16, 1.2)
    s2 = star_layer(60.0, 0.03, 0.10, 4.0)
    base = (0.0035, 0.003, 0.009)
    acc = N.new('ShaderNodeVectorMath'); acc.operation = 'ADD'; L.new(nebc.outputs[0], acc.inputs[0]); acc.inputs[1].default_value = base
    acc2 = N.new('ShaderNodeVectorMath'); acc2.operation = 'ADD'; L.new(acc.outputs[0], acc2.inputs[0]); L.new(s1, acc2.inputs[1])
    acc3 = N.new('ShaderNodeVectorMath'); acc3.operation = 'ADD'; L.new(acc2.outputs[0], acc3.inputs[0]); L.new(s2, acc3.inputs[1])
    bg = N.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0; L.new(acc3.outputs[0], bg.inputs['Color'])
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(d, sep.inputs[0])
    up = N.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = -0.3; up.inputs['From Max'].default_value = 1.0
    up.interpolation_type = 'SMOOTHSTEP'; L.new(sep.outputs['Z'], up.inputs['Value'])
    up2 = math_node(N, 'MULTIPLY_ADD', math_node(N, 'POWER', up.outputs[0], 2.0, L), STUDIO[0], L); up2.node.inputs[2].default_value = STUDIO[1]
    st = N.new('ShaderNodeBackground'); st.inputs['Color'].default_value = (1.0, 0.86, 0.70, 1); L.new(up2, st.inputs['Strength'])
    lp = N.new('ShaderNodeLightPath')
    mx = N.new('ShaderNodeMixShader'); L.new(lp.outputs['Is Glossy Ray'], mx.inputs[0]); L.new(bg.outputs[0], mx.inputs[1]); L.new(st.outputs[0], mx.inputs[2])
    out = N.new('ShaderNodeOutputWorld'); L.new(mx.outputs[0], out.inputs['Surface'])


def build_compositor(sc, bloom):
    ng = bpy.data.node_groups.new('HeroPost', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers')
    g1 = N.new('CompositorNodeGlare')
    g1.inputs['Type'].default_value = 'Bloom'; g1.inputs['Quality'].default_value = 'High'
    for k, v in bloom['bloom'].items():
        g1.inputs[k].default_value = v
    g2 = N.new('CompositorNodeGlare')
    g2.inputs['Type'].default_value = 'Fog Glow'; g2.inputs['Quality'].default_value = 'High'
    for k, v in bloom['fog'].items():
        g2.inputs[k].default_value = v
    out = N.new('NodeGroupOutput')
    L.new(rl.outputs['Image'], g1.inputs['Image']); L.new(g1.outputs['Image'], g2.inputs['Image']); L.new(g2.outputs['Image'], out.inputs[0])
    sc.render.use_compositing = True
    sc.render.compositor_device = 'CPU'           # the GPU compositor needs EGL, absent here (the render aborts)
    sc.render.compositor_precision = 'FULL'


def read_viewpoint(pocket, name):
    tree = ET.parse(pocket)
    for vp in tree.iter('Viewpoint'):
        if vp.get('DEF') == name:
            f = lambda k: [float(x) for x in vp.get(k).split()]
            return dict(position=f('position'), orientation=f('orientation'), centerOfRotation=f('centerOfRotation'), fieldOfView=float(vp.get('fieldOfView')))
    raise SystemExit('viewpoint %s not found' % name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geometry', required=True); ap.add_argument('--pocket', required=True)
    ap.add_argument('--shot', default='wide'); ap.add_argument('--viewpoint', default='Wide')
    ap.add_argument('--res', default='1600x900'); ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--fov-scale', type=float, default=1.0); ap.add_argument('--fstop', type=float, default=0.75)
    ap.add_argument('--exposure', type=float, default=0.0); ap.add_argument('--look', default='AgX - Punchy')
    ap.add_argument('--no-glow', action='store_true'); ap.add_argument('--no-denoise', action='store_true'); ap.add_argument('--hide', default=''); ap.add_argument('--out', required=True); ap.add_argument('--stats', required=True)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    t0 = time.time()
    geo = json.load(open(a.geometry))
    global GLOW_SHEATHS; GLOW_SHEATHS = not a.no_glow
    sc, root = reset()
    stats = {'family': geo['family'], 'shot': a.shot, 'viewpoint': a.viewpoint}
    tri = {}

    build_fibers(root, geo, stats)
    # founders' seed: core, glow proxy, warm lamp
    me, t = uv_sphere('Seed', geo['seed']['r'], 32, 16); tri['seed'] = t
    add_mesh(root, 'Seed', me, mat_emit('SeedHot', (1.0, srgb_to_lin(0.86), srgb_to_lin(0.62)), 40.0))
    gr = geo['seed']['glow_r']
    me, t = uv_sphere('SeedGlow', gr, 64, 32); tri['seed_glow'] = t
    add_mesh(root, 'SeedGlow', me, mat_veil('SeedGlowM', (1.0, srgb_to_lin(0.60), srgb_to_lin(0.28)), SEED_GLOW, 6.0))
    me, t = uv_sphere('SeedHalo', gr * 0.42, 48, 24); tri['seed_halo'] = t
    add_mesh(root, 'SeedHalo', me, mat_veil('SeedHaloM', (1.0, srgb_to_lin(0.90), srgb_to_lin(0.74)), SEED_GLOW * 1.5, 5.0))
    lamp = bpy.data.lights.new('SeedLamp', 'POINT'); lamp.energy = 14.0; lamp.shadow_soft_size = 0.03
    lamp.color = (1.0, srgb_to_lin(0.74), srgb_to_lin(0.45))
    lo = link(bpy.data.objects.new('SeedLamp', lamp), root)
    # time shells (1750-2000): limb lines, warm at the core to cool at the glass, far crossing x0.5
    for s in geo['shells']:
        k = s['r'] / geo['glass']['r']
        col = tuple(srgb_to_lin(a_ + (b_ - a_) * k) for a_, b_ in zip((1.0, 0.60, 0.30), (0.40, 0.55, 1.0)))
        me, t = uv_sphere('Shell%d' % s['year'], s['r'], 128, 64); tri['shell_%d' % s['year']] = t
        add_mesh(root, 'Shell%d' % s['year'], me, mat_veil('ShellM%d' % s['year'], col, 1.0, 0, back=0.5, limb=SHELL_LIMB))
    # haze body
    me, t = uv_sphere('Haze', 1.04, 96, 48); tri['haze'] = t
    add_mesh(root, 'Haze', me, mat_veil('HazeM', (srgb_to_lin(0.42), srgb_to_lin(0.26), srgb_to_lin(0.78)), HAZE, 1.6))
    # glass: a thin solid shell (outer normals out, inner normals in)
    me, t = uv_sphere('Glass', R_GLASS_OUT, 192, 96); tri['glass'] = t
    add_mesh(root, 'Glass', me, mat_glass('GlassM', rim=True))
    # gold armillary
    gold = mat_gold('Gold'); gold_set = bpy.data.collections.new('GoldRings')     # light linking: the softbox lights only the gold
    for i, (R, r, ax, ang) in enumerate(RINGS):
        me, t = torus_mesh('Ring%d' % i, R / HOST_SCALE, RING_TUBE_X * r / HOST_SCALE); tri['ring_%d' % i] = t
        ob = add_mesh(root, 'Ring%d' % i, me, gold); gold_set.objects.link(ob)
        ob.rotation_mode = 'AXIS_ANGLE'; axn = Vector(ax).normalized(); ob.rotation_axis_angle = (ang, axn.x, axn.y, axn.z)
    # key and rim lights (look bible directions), cool and magenta
    for name, dirn, colr, strength in (('Key', (-0.45, -0.62, -0.64), (0.78, 0.85, 1.0), 2.2), ('Rim', (0.55, 0.15, 0.82), (1.0, 0.5, 0.78), 1.2)):
        L_ = bpy.data.lights.new(name, 'SUN'); L_.energy = strength; L_.color = tuple(srgb_to_lin(c) for c in colr); L_.angle = math.radians(1.5)
        ob = link(bpy.data.objects.new(name, L_), root)
        z = -Vector(dirn).normalized()           # a sun shines down its local -Z
        ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(z)
    sb = bpy.data.lights.new('Softbox', 'AREA'); sb.shape = 'DISK'; sb.size = 2.4; sb.energy = SOFTBOX_W; sb.color = (1.0, 0.88, 0.74)
    so = link(bpy.data.objects.new('Softbox', sb), root); so.location = (-2.6, 2.9, 2.2)
    so.rotation_mode = 'QUATERNION'; so.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(so.location).normalized())
    so.visible_camera = False; so.light_linking.receiver_collection = gold_set
    build_world(sc)

    # camera: the X3D Viewpoint, unchanged, inside the Y-up root
    vp = read_viewpoint(a.pocket, a.viewpoint)
    W, H = (int(x) for x in a.res.split('x'))
    cam = bpy.data.cameras.new('Cam'); co = link(bpy.data.objects.new('Cam', cam), root)
    ax = vp['orientation']
    co.matrix_basis = Matrix.Translation(vp['position']) @ Matrix.Rotation(ax[3], 4, Vector(ax[:3]).normalized())
    cam.sensor_fit = 'VERTICAL' if W >= H else 'HORIZONTAL'      # X_ITE: fieldOfView spans the smaller side
    cam.angle = vp['fieldOfView'] * a.fov_scale
    cam.clip_start = 0.01; cam.clip_end = 100
    focus = math.dist(vp['position'], (0, 0, 0))                  # focus on the founders' seed
    cam.dof.use_dof = True; cam.dof.focus_distance = focus; cam.dof.aperture_fstop = a.fstop; cam.dof.aperture_blades = 7; cam.dof.aperture_rotation = 0.2
    sc.camera = co

    r = sc.render
    r.engine = 'CYCLES'; r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
    r.threads_mode = 'FIXED'; r.threads = 4
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.color_depth = '8'
    cy = sc.cycles
    cy.device = 'CPU'; cy.samples = a.samples; cy.seed = SEED
    cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.015
    cy.use_denoising = not a.no_denoise; cy.denoiser = 'OPENIMAGEDENOISE'; cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; cy.denoising_prefilter = 'ACCURATE'
    cy.max_bounces = 16; cy.diffuse_bounces = 1; cy.glossy_bounces = 4; cy.transmission_bounces = 12; cy.volume_bounces = 0; cy.transparent_max_bounces = 96
    cy.sample_clamp_direct = 0.0; cy.sample_clamp_indirect = 8.0; cy.blur_glossy = 0.0      # filter glossy blurred everything seen through the glass into a grey disc (preview 1)
    cy.caustics_reflective = False; cy.caustics_refractive = False
    r.film_transparent = False; r.filter_size = 1.2
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    try:
        vs.look = a.look
    except TypeError:
        pass
    vs.exposure = a.exposure; vs.gamma = 1.0
    bloom = {'bloom': {'Threshold': 0.9, 'Smoothness': 0.25, 'Strength': 0.75, 'Size': 0.82},
             'fog': {'Threshold': 3.0, 'Smoothness': 0.4, 'Strength': 0.22, 'Size': 0.9}}
    build_compositor(sc, bloom)
    for ob in sc.objects:                         # diagnosis only: --hide Shell,Haze
        if a.hide and any(ob.name.startswith(h) for h in a.hide.split(',')):
            ob.hide_render = True
    r.filepath = a.out

    stats.update(dict(resolution=[W, H], samples=a.samples, adaptive_threshold=cy.adaptive_threshold, denoiser='OpenImageDenoise (albedo+normal, accurate prefilter)',
                      view_transform=vs.view_transform, look=vs.look, exposure=vs.exposure, fstop=a.fstop, focus_distance=round(focus, 4),
                      fov=round(cam.angle, 5), sensor_fit=cam.sensor_fit, viewpoint_pose=vp, seed=SEED, threads=r.threads,
                      bounces=dict(max=cy.max_bounces, diffuse=cy.diffuse_bounces, glossy=cy.glossy_bounces, transmission=cy.transmission_bounces, transparent=cy.transparent_max_bounces),
                      clamp_indirect=cy.sample_clamp_indirect, filter_glossy=cy.blur_glossy, compositor=bloom, scene_build_s=round(time.time() - t0, 2),
                      mesh_triangles=tri, kinds=KIND, dash=[DASH_ON, DASH_OFF], core_strength=CORE_STRENGTH, glow_strength=GLOW_STRENGTH, glow_sheaths=GLOW_SHEATHS, glass_ior=GLASS_IOR, haze=HAZE, ring_tube_x=RING_TUBE_X, shell_limb=SHELL_LIMB, rim_gain=RIM_GAIN, nebula_gain=NEBULA_GAIN, seed_glow=SEED_GLOW, softbox_w=SOFTBOX_W, studio=STUDIO,
                      blender=bpy.app.version_string))
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    stats['render_wall_s'] = round(time.time() - t1, 1)
    # triangle count of the evaluated scene (curves included)
    dg = bpy.context.evaluated_depsgraph_get(); total = 0
    for ob in sc.objects:
        if ob.type in ('MESH', 'CURVE'):
            ev = ob.evaluated_get(dg); m = ev.to_mesh()
            if m:
                m.calc_loop_triangles(); total += len(m.loop_triangles); ev.to_mesh_clear()
    stats['scene_triangles'] = total
    json.dump(stats, open(a.stats, 'w'), indent=1, sort_keys=True)
    print('HERO', json.dumps({k: stats[k] for k in ('render_wall_s', 'scene_triangles', 'fiber_objects', 'look', 'view_transform')}))


main()
