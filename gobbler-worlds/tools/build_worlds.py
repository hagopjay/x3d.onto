"""Worlds inside the Gobbler: four whole scenes nested, scaled down, in glass bubbles that hang round the heart inside the Dyson ribcage.

  python3 -I gobbler-worlds/tools/build_worlds.py --giza DIR --poc DIR --pantheon FILE [--validate]

  --giza      the scene/ folder of the Giza v2.1 site (polyxandria/giza/v2.1/giza-v2.1-site.tar, site/scene; PRIVATE: its files go to data/, never into git)
  --poc       x3d.poc assets/gifts (the Materials and Drillfield demos)
  --pantheon  the 50,058-splat Pantheon subset (pantheon-subset-50k-x3d41.x3d)

Needs gobbler-demiurge/data/bird/ (make demiurge-data). Writes gobbler-worlds/data/: bird/ (the bird scene with the worlds layer spliced into the Loom group, gzipped,
and a copy of the demiurge's lazy village files), worlds/<id>/ (each world's files) and bird/worlds.json (bubbles, scales and the dive stops, for the page).

Each world keeps its own metres. A Transform scales it into its bubble (scale = 0.82 x bubble radius / the world's radius), so a world is as large as you want
it to be once you are inside: the dive and the logarithmic depth buffer are the village's (gobbler-demiurge/src/boot.js). Nothing of a world is in the boot
payload: each one loads when a ProximitySensor round its bubble says the camera is near.
"""
import gzip, io, json, math, os, re, shutil, subprocess, sys, time, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
DEMI = os.path.join(REPO, 'gobbler-demiurge'); OUT = os.path.join(ROOT, 'data')
sys.path.insert(0, HERE)
import disco

SUN = (6.5, -2.6, 0.4)          # the heart (gobbler-demiurge tools/layers.py SUN)
RB = 0.36                       # bubble radius, scene units (Earth is drawn 0.1)
ORBIT = 2.15                    # bubble centres stand this far from the heart, inside the ribcage (radius 3.3); Earth is at 2.5

SKY = dict(giza=((0.01, 0.01, 0.05), (0.10, 0.03, 0.16), (0.42, 0.14, 0.22), (0.05, 0.02, 0.03)), pantheon=((0.02, 0.02, 0.03), (0.06, 0.05, 0.05), (0.16, 0.13, 0.10), (0.03, 0.03, 0.03)),
           materials=((0.01, 0.008, 0.008), (0.03, 0.02, 0.02), (0.09, 0.05, 0.04), (0.01, 0.01, 0.01)), drillfield=((0.02, 0.03, 0.10), (0.10, 0.12, 0.30), (0.62, 0.36, 0.30), (0.04, 0.03, 0.05)))

WORLDS = [
    dict(id='giza', label='Giza, disco night', short='Giza', tint=(1.0, 0.72, 0.3), dir=(-0.80, 0.50, 0.33), centre=(-140.0, 0.0, 330.0), radius=900.0, lift=0.30,
         file='giza-nest.x3d', note='Giza v2.1 at 1:3,000 of its own metres; the disco and the Hall of Records are additions, the Hall is hypothetical',
         stops=[('giza', 'Giza from the air', (600, 380, 820), (-160, 0, 300), 0.8),
                ('disco', 'Disco on Khufu', (150, 175, 160), (0, 175, 0), 0.9),
                ('hall', 'Hall of Records (hypothetical)', (disco.HALL[0] - 8, disco.HALL[1] + 1.5, disco.HALL[2] - 24), disco.HALL, 0.95),
                ('osiris', 'Osiris Shaft', (disco.OSIRIS_SITE[0] - 34, disco.OSIRIS_SITE[1] + 46, disco.OSIRIS_SITE[2] + 62), disco.OSIRIS_SITE, 0.7)]),
    dict(id='pantheon', label='Pantheon, 50,058 splats', short='Pantheon', tint=(0.95, 0.9, 0.78), dir=(0.82, 0.50, 0.30), centre=(0.0, 7.0, 0.0), radius=17.0, lift=0.0,
         file='pantheon.x3d', note='the Pantheon subset at 1:58 of its own metres',
         stops=[('pantheon', 'Under the oculus', (0.0, 1.0, 3.0), (0.0, 8.0, -6.0), 1.15)]),
    dict(id='materials', label='Materials from nothing', short='Materials', tint=(0.86, 0.35, 0.2), dir=(-0.62, -0.52, 0.58), centre=(0.0, 1.0, 0.0), radius=8.0, lift=0.25,
         file='materials.x3d', note='the swatch shelf at 1:27 of its own metres',
         stops=[('materials', 'The swatch shelf', (0.0, 2.0, 7.0), (0.0, 0.75, 0.0), 0.62)]),
    dict(id='drillfield', label='The Drillfield (imagery: Google)', short='Drillfield', tint=(0.55, 0.12, 0.2), dir=(0.74, -0.58, 0.34), centre=(0.0, 10.0, 0.0), radius=330.0, lift=0.25,
         file='drillfield.x3d', note='the Drillfield at 1:1,100 of its own metres; imagery and data: Google',
         stops=[('drillfield', 'Over the Drillfield', (200, 110, 215), (-89, 0, -73), 0.8)]),
]

def f(x): return '%.7g' % x
def v(p): return ' '.join(f(x) for x in p)
def nrm(a): l = math.sqrt(sum(x * x for x in a)) or 1.0; return tuple(x / l for x in a)
def gz(b): bio = io.BytesIO(); g = gzip.GzipFile(fileobj=bio, mode='wb', compresslevel=9, mtime=0); g.write(b); g.close(); return bio.getvalue()
def sha(b): return hashlib.sha256(b).hexdigest()

def frame(w):
    """bubble centre, scale (scene units per world metre) and the translation that puts the world's centre at the bubble's centre, a little low"""
    C = tuple(SUN[i] + ORBIT * nrm(w['dir'])[i] for i in range(3))
    s = 0.82 * RB / w['radius']
    T = tuple(C[i] - s * w['centre'][i] + (-w['lift'] * RB if i == 1 else 0.0) for i in range(3))
    return C, s, T

def to_bird(w, p):
    C, s, T = frame(w); return [T[i] + s * p[i] for i in range(3)]

# ---------------------------------------------------------------- each world's files

def shrink_image(src, dst, edge=512, as_jpg=True):
    from PIL import Image
    im = Image.open(src); im.thumbnail((edge, edge))
    if as_jpg: im.convert('RGB').save(dst, 'JPEG', quality=86, optimize=True)
    else: im.save(dst, optimize=True)

def strip_scene_nodes(s):
    s = re.sub(r'<!DOCTYPE[^>]*>', '', s)
    s = re.sub(r'<NavigationInfo\b[^>]*/>', '', s); s = re.sub(r'<Background\b[^>]*/>', '', s)
    return s

def light_scope(s):
    """a world's lights must light only that world: global='false' on every light (DirectionalLight defaults to false, Point and Spot to true)"""
    def fix(m):
        t = m.group(0)
        return re.sub(r"global=(['\"])true\1", "global='false'", t) if 'global=' in t else t.replace('<' + m.group(1), '<' + m.group(1) + " global='false'", 1)
    return re.sub(r'<(DirectionalLight|PointLight|SpotLight)\b[^>]*>', fix, s)

def world_giza(src, out):
    os.makedirs(os.path.join(out, 'tex21'), exist_ok=True)
    names = ['plateau-v21.xml', 'sphinx-terrain-v21.xml', 'sphinx-today-mesh-v21.xml', 'sphinx-context-today-v21.xml', 'osiris-paganini-v21.xml']
    tex = set()
    for n in names:
        s = open(os.path.join(src, n), encoding='utf-8').read()
        if n == 'sphinx-terrain-v21.xml':     # the outer ground runs 20 km out; in a bubble it would cut the glass. Hidden, not removed (its material is exported)
            s, k = re.subn(r'<Shape DEF="OuterGround">', '<Shape DEF="OuterGround" visible="false">', s); assert k == 1, 'OuterGround not found'
        if n == 'plateau-v21.xml':     # level 0 and 1 of KhufuLOD are splat Inlines that only giza21-boot.js would load; force the mesh level at every distance
            s, k = re.subn(r'(<LOD DEF="KhufuLOD"[^>]*range=")260 900(")', r'\g<1>1e-06 2e-06\2', s); assert k == 1, 'KhufuLOD not found'
        for u in re.findall(r'tex21/([\w.-]+)', s): tex.add(u)
        s = re.sub(r'tex21/([\w-]+?)([_-])normal\.png', r'tex21/\1\2normal.jpg', s)
        s = light_scope(strip_scene_nodes(s))
        open(os.path.join(out, n), 'w', encoding='utf-8').write(s)
    for u in sorted(tex):
        p = os.path.join(src, 'tex21', u)
        if u.endswith('normal.png'): shrink_image(p, os.path.join(out, 'tex21', u[:-4] + '.jpg'))
        elif u.endswith('.jpg'): shrink_image(p, os.path.join(out, 'tex21', u))
        else: shutil.copyfile(p, os.path.join(out, 'tex21', u))
    open(os.path.join(out, 'giza-nest.x3d'), 'w', encoding='utf-8').write(disco.giza_host())

def world_pantheon(src, out):
    os.makedirs(out, exist_ok=True)
    s = strip_scene_nodes(open(src, encoding='utf-8').read())
    open(os.path.join(out, 'pantheon.x3d'), 'w', encoding='utf-8').write(s)

def world_materials(poc, out):
    os.makedirs(out, exist_ok=True); d = os.path.join(poc, 'materials')
    s = open(os.path.join(d, 'materials.x3d'), encoding='utf-8').read()
    s, k = re.subn(r"<Transform rotation='0 1 0 2.2'>\s*<Shape>(?:(?!</Shape>).)*?starry_sky\.jpg(?:(?!</Shape>).)*?<Sphere radius='40' solid='false'/>\s*</Shape>\s*</Transform>", '', s, flags=re.S); assert k == 1, 'sky sphere not found'
    s = s.replace("<Box size='60 0.02 60'/>", "<Box size='12 0.02 9'/>")
    for u in sorted(set(re.findall(r'url=\'"([\w.-]+\.(?:jpg|png))"\'', s))):
        if u.endswith('_normal.png'): shrink_image(os.path.join(d, u), os.path.join(out, u[:-4] + '.jpg')); s = s.replace('"%s"' % u, '"%s"' % (u[:-4] + '.jpg'))
        elif u.endswith('.jpg'): shrink_image(os.path.join(d, u), os.path.join(out, u))
        else: shutil.copyfile(os.path.join(d, u), os.path.join(out, u))
    open(os.path.join(out, 'materials.x3d'), 'w', encoding='utf-8').write(light_scope(strip_scene_nodes(s)))

def world_drillfield(poc, out):
    os.makedirs(out, exist_ok=True); d = os.path.join(poc, 'drillfield')
    s = open(os.path.join(d, 'drillfield.x3d'), encoding='utf-8').read()
    shrink_image(os.path.join(d, 'drillfield-rgb.jpg'), os.path.join(out, 'drillfield-rgb.jpg'), edge=1600)
    open(os.path.join(out, 'drillfield.x3d'), 'w', encoding='utf-8').write(light_scope(strip_scene_nodes(s)))

# ---------------------------------------------------------------- the layer in the bird

def circle(r, n, axis):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n; c, s = r * math.cos(a), r * math.sin(a)
        pts.append((c, 0.0, s) if axis == 'y' else (c, s, 0.0) if axis == 'z' else (0.0, c, s))
    return pts

def sky_dome(w, nl=16, nm=32):
    """the world's own sky: a sphere whose faces point inward (the quads below run down then east, which faces the centre), solid, so it is drawn only from inside the bubble;
    from outside you look through the glass at the world"""
    top, mid, hor, low = SKY[w['id']]; r = RB * 0.995; P, Cc, I = [], [], []
    def mix(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    for i in range(nl + 1):
        th = math.pi * i / nl; y = math.cos(th)
        c = mix(top, mid, min(1, (1 - y) / 0.7)) if y > 0.3 else mix(mid, hor, (0.3 - y) / 0.3) if y > 0 else mix(hor, low, min(1, -y / 0.25))
        for j in range(nm):
            ph = 2 * math.pi * j / nm; P.append((r * math.sin(th) * math.cos(ph), r * y, r * math.sin(th) * math.sin(ph))); Cc.append(c)
    for i in range(nl):
        for j in range(nm):
            a, b = i * nm + j, i * nm + (j + 1) % nm; I.append('%d %d %d %d -1' % (a, a + nm, b + nm, b))
    import random as _r; g = _r.Random(hash(w['id']) & 0xffff); S = []
    for k in range(260):
        z = g.uniform(0.12, 1.0); ph = g.uniform(0, 2 * math.pi); q = math.sqrt(1 - z * z); S.append((r * 0.985 * q * math.cos(ph), r * 0.985 * z, r * 0.985 * q * math.sin(ph)))
    return ("<Shape><Appearance><UnlitMaterial/></Appearance><IndexedFaceSet solid='true' colorPerVertex='true' coordIndex='%s'><Coordinate point='%s'/><Color color='%s'/></IndexedFaceSet></Shape>"
            "<Shape><Appearance><UnlitMaterial emissiveColor='1 0.95 0.85'/></Appearance><PointSet><Coordinate point='%s'/></PointSet></Shape>") % (
        ' '.join(I), ' '.join(v(p) for p in P), ' '.join(v(c) for c in Cc), ' '.join(v(p) for p in S))

def bubble(w):
    C, s, T = frame(w); t = w['tint']; ID = w['id'].capitalize()
    rings = []
    for k, ax in enumerate(('y', 'z', 'x')):
        P = circle(RB * (1.0 if k else 1.004), 96, ax)
        rings.append("<IndexedLineSet coordIndex='%s 0 -1'><Coordinate point='%s'/></IndexedLineSet>" % (' '.join(str(i) for i in range(96)), ' '.join(v(p) for p in P)))
    ring_shapes = ''.join("<Shape><Appearance><UnlitMaterial %s/>%s</Appearance>%s</Shape>" % ("DEF='%sRim' emissiveColor='%s'" % (ID, v(t)) if i == 0 else "USE='%sRim'" % ID, "<LineProperties linewidthScaleFactor='2'/>", r) for i, r in enumerate(rings))
    base = circle(RB * 0.86, 96, 'y'); yb = -w['lift'] * RB - 0.004
    plinth = "<Transform translation='0 %s 0'><Shape><Appearance><UnlitMaterial emissiveColor='1 0.84 0.45'/></Appearance><IndexedLineSet coordIndex='%s 0 -1'><Coordinate point='%s'/></IndexedLineSet></Shape></Transform>" % (
        f(yb), ' '.join(str(i) for i in range(96)), ' '.join(v(p) for p in base))
    sky = "<Inline DEF='%sSky' load='false' url='\"data/worlds/%s/sky.x3d\"'/>" % (ID, w['id'])      # the world's own sky arrives with the world (not in the boot payload)
    glass = "<Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='%s' transparency='0.93'/></Appearance><Sphere radius='%s' solid='false'/></Shape>" % (v(tuple(0.35 * x for x in t)), f(RB))
    halo = ("<Billboard axisOfRotation='0 0 0'><Shape><Appearance><UnlitMaterial emissiveColor='%s' transparency='0.25' emissiveTextureMapping='uv'><ImageTexture containerField='emissiveTexture' url='\"data/worlds/glow.png\"'/></UnlitMaterial></Appearance>"
            "<IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1' texCoordIndex='0 1 2 3 -1'><Coordinate point='%s'/><TextureCoordinate point='0 0 1 0 1 1 0 1'/></IndexedFaceSet></Shape></Billboard>") % (
        v(t), ' '.join(v(p) for p in ((-2.2 * RB, -2.2 * RB, -RB * 1.05), (2.2 * RB, -2.2 * RB, -RB * 1.05), (2.2 * RB, 2.2 * RB, -RB * 1.05), (-2.2 * RB, 2.2 * RB, -RB * 1.05))))      # a glow behind the glass, so a bubble reads in the crowded cosmos
    seed = "<Shape DEF='%sSeed'><Appearance><UnlitMaterial emissiveColor='%s' transparency='0.35'/></Appearance><Sphere radius='%s'/></Shape>" % (ID, v(t), f(0.012))      # the world's seed, seen from outside; hidden once you are in
    world = "<Transform DEF='%sWorld' translation='%s' scale='%s %s %s'><Inline DEF='%sInline' load='false' url='\"data/worlds/%s/%s\"'/></Transform>" % (ID, v(T), f(s), f(s), f(s), ID, w['id'], w['file'])
    sense = ("<ProximitySensor DEF='%sSense' center='%s' size='%s'/><BooleanFilter DEF='%sLoad'/>" % (ID, v(C), v((12 * RB,) * 3), ID) +      # loads from about 2 units off
             "<ProximitySensor DEF='%sInside' center='%s' size='%s'/><BooleanFilter DEF='%sHide'/>" % (ID, v(C), v((2 * RB,) * 3), ID))         # inside the glass the seed goes out
    routes = ("<ROUTE fromNode='%sSense' fromField='isActive' toNode='%sLoad' toField='set_boolean'/><ROUTE fromNode='%sLoad' fromField='inputTrue' toNode='%sInline' toField='set_load'/>"
              "<ROUTE fromNode='%sLoad' fromField='inputTrue' toNode='%sSky' toField='set_load'/>"
              "<ROUTE fromNode='%sInside' fromField='isActive' toNode='%sHide' toField='set_boolean'/><ROUTE fromNode='%sHide' fromField='inputNegate' toNode='%sSeed' toField='set_visible'/>" % ((ID,) * 10))
    return "<Transform DEF='%sBubble' translation='%s'>%s%s%s%s<Transform translation='0 %s 0'>%s</Transform></Transform>%s%s%s" % (ID, v(C), sky + halo, glass, ring_shapes, plinth, f(-w['lift'] * RB - 0.02), seed, world, sense, routes)

def layer():
    return "<Group DEF='Worlds'>" + ''.join(bubble(w) for w in WORLDS) + "</Group>"

def worlds_json(files):
    out = []
    for w in WORLDS:
        C, s, T = frame(w)
        out.append(dict(id=w['id'], label=w['label'], short=w['short'], centre=[round(x, 7) for x in C], bubble=RB, scale=s, metres_per_unit=1 / s, note=w['note'],
                        stops=[dict(id=i, label=l, pos=[round(x, 9) for x in to_bird(w, p)], look=[round(x, 9) for x in to_bird(w, q)], fov=fv, up=[0, 1, 0], dist_m=round(math.dist(p, q), 1)) for i, l, p, q, fv in w['stops']],
                        files=files.get(w['id'], {})))
    return dict(sun=list(SUN), orbit=ORBIT, worlds=out)

def main():
    a = sys.argv; arg = lambda k: a[a.index(k) + 1]
    t0 = time.time(); W = os.path.join(OUT, 'worlds'); B = os.path.join(OUT, 'bird')
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    os.makedirs(B)
    world_giza(arg('--giza'), os.path.join(W, 'giza')); world_pantheon(arg('--pantheon'), os.path.join(W, 'pantheon'))
    world_materials(arg('--poc'), os.path.join(W, 'materials')); world_drillfield(arg('--poc'), os.path.join(W, 'drillfield'))
    shutil.copyfile(os.path.join(arg('--poc'), 'materials', 'glow.png'), os.path.join(W, 'glow.png'))      # x3d.poc's soft glow sprite (14 KB), the halos behind the bubbles
    for w in WORLDS:
        open(os.path.join(W, w['id'], 'sky.x3d'), 'w').write("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'><head><component name='Shape' level='1'/><meta name='title' content='sky.x3d'/><meta name='description' content='the inside of a world bubble: a sky drawn only from inside (gobbler-worlds/tools/build_worlds.py)'/></head><Scene>" + sky_dome(w) + "</Scene></X3D>\n")
    files = {}
    for wid in sorted(os.listdir(W)):
        d = os.path.join(W, wid)
        if not os.path.isdir(d): continue
        files[wid] = {}
        for root, _, fs in os.walk(d):
            for n in fs:
                p = os.path.join(root, n); b = open(p, 'rb').read(); files[wid][os.path.relpath(p, d)] = dict(bytes=len(b), gz=len(gz(b)) if n.endswith(('.x3d', '.xml')) else len(b))
    for n in os.listdir(os.path.join(DEMI, 'data', 'bird')):
        if not n.startswith('gobbler4-bird'): shutil.copyfile(os.path.join(DEMI, 'data', 'bird', n), os.path.join(B, n))
    s = open(os.path.join(DEMI, 'data', 'bird', 'gobbler4-bird.x3d'), encoding='utf-8').read()
    i = s.find("<Transform DEF='Loom'"); d = 0; end = None
    for m in re.finditer(r'<(/?)Transform\b[^>]*?(/?)>', s[i:]):
        if m.group(1): d -= 1
        elif not m.group(2): d += 1
        if d == 0: end = i + m.start(); break
    L = layer(); s2 = s[:end] + L + s[end:]
    s2 = s2.replace("<meta name='title' content='gobbler.x3d'/>", "<meta name='title' content='gobbler.x3d'/><meta name='worlds' content='four nested worlds in glass bubbles round the heart (gobbler-worlds/tools/build_worlds.py)'/>", 1)
    sb = s2.encode('utf-8'); open(os.path.join(B, 'gobbler4-worlds.x3d'), 'wb').write(sb); open(os.path.join(B, 'gobbler4-worlds.x3d.gz'), 'wb').write(gz(sb))
    wj = worlds_json(files); json.dump(wj, open(os.path.join(B, 'worlds.json'), 'w'), indent=1)
    rec = dict(scene_bytes=len(sb), scene_gz_bytes=len(gz(sb)), bird_gz_bytes=len(gz(s.encode('utf-8'))), layer_bytes=len(L.encode()), scene_sha256=sha(sb),
               worlds={k: dict(files=len(v_), bytes=sum(x['bytes'] for x in v_.values()), wire=sum(x['gz'] for x in v_.values())) for k, v_ in files.items()}, built_in_s=round(time.time() - t0, 2))
    if '--validate' in a:
        val = os.path.join(DEMI, 'tools', 'validate_fork.py'); rec['validator'] = {}
        targets = [os.path.join(B, 'gobbler4-worlds.x3d'), os.path.join(W, 'giza', 'giza-nest.x3d'), os.path.join(W, 'giza', 'plateau-v21.xml'), os.path.join(W, 'materials', 'materials.x3d'), os.path.join(W, 'drillfield', 'drillfield.x3d'), os.path.join(W, 'giza', 'sky.x3d'), os.path.join(W, 'pantheon', 'pantheon.x3d')]
        for t in targets:
            r = subprocess.run([sys.executable, val, t], capture_output=True, text=True)
            try: j = json.loads(r.stdout); rec['validator'][os.path.relpath(t, OUT)] = {k: j.get(k) for k in ('xsd_valid', 'xsd_errors', 'profile_ok')}
            except Exception: rec['validator'][os.path.relpath(t, OUT)] = dict(error=(r.stdout + r.stderr)[-400:])
        mcp = os.environ.get('X3D_MCP', '/home/user/x3d_mcp')
        try: rec['validator_commit'] = subprocess.run(['git', '-C', mcp, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        except Exception: pass
    json.dump(rec, open(os.path.join(B, 'worlds-receipt.json'), 'w'), indent=1); print(json.dumps(rec, indent=1))

if __name__ == '__main__': main()
