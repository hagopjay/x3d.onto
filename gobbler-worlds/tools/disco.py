"""Giza, disco night: the host file that nests Giza v2.1 inside the Gobbler, plus its fun layer.

giza_host(cfg) -> text of giza-nest.x3d. It Inlines five Giza v2.1 scene files (the plateau, the Sphinx's ground, the Sphinx mesh, its temples, the Osiris Shaft)
and adds, in Giza's own metres (x east, y up, z south, Khufu at the origin, as in v2.1):
  - light: a low dusk sun and a cool fill, scoped to this file (global='false'), because the bird's scene has no light of its own
  - Khufu's look cycles today -> X-ray (with the chambers) every 8 s, through the plateau's own exported switches (KhufuLook, InteriorSwitch)
  - a mirror ball over Khufu, two fans of light beams that turn against each other, lasers apex to apex, a dance floor on Khufu's flat summit,
    rings that pulse out from Khufu on the bird's heartbeat (1 s)
  - a marker at the Osiris Shaft (a gold ring and a light pillar) so it can be found from the air
  - the Hall of Records, HYPOTHETICAL: an invented chamber under the Sphinx's left paw, drawn as a glowing wire box with scrolls, and a scan plane that sweeps through it
Every part is plain X3D 4.0 nodes (interpolators, sequencers, Switch, Unlit/Material), no Script and no shader.
The Hall is fiction made visible: its tag says so, and the only real thing behind it is a reported seismic anomaly (see HALL_NOTE).
"""
import math, random

HALL_NOTE = ('Hypothetical. Edgar Cayce (1930s readings) placed a "Hall of Records" under the Sphinx; a 1991 seismic survey reported a cavity under the left paw that was never '
             'excavated. The chamber drawn here is invented: its size, depth and contents are guesses for the picture, not data.')

SPHINX_SITE = (312.61, -40.0, 429.55)      # giza-v21.xml Transform SphinxSite
OSIRIS_SITE = (209.61, -26.34, 445.7)      # giza-v21.xml Transform OsirisSite
KHUFU_TOP = (0.0, 138.5, 0.0)              # present height 138.5 m (plateau-v21.xml description); the flat summit is about 10 m across
KHAFRE_TOP = (-340.0, 143.0, 343.0)        # centre from the VwKhafreCap view's centre of rotation; height approximate (it stands on higher ground)
MENKAURE_TOP = (-581.0, 70.0, 740.0)       # centre from VwMenkaureGranite; height approximate
SPHINX_HEAD = (SPHINX_SITE[0] + 12.0, SPHINX_SITE[1] + 20.0, SPHINX_SITE[2])
BALL = (0.0, 205.0, 0.0)                   # the mirror ball, 66 m over the summit
HALL = (SPHINX_SITE[0] + 24.0, SPHINX_SITE[1] - 6.0, SPHINX_SITE[2] - 4.0)    # under the left (north) paw, below the enclosure floor; invented
HALL_SIZE = (12.0, 5.0, 9.0)

def f(x): return '%.4g' % x
def v(p): return ' '.join(f(x) for x in p)
def cols(c): return ' '.join(v(x) for x in c)

PARTY = [(1.0, 0.15, 0.75), (0.1, 0.95, 1.0), (1.0, 0.78, 0.15), (0.55, 0.2, 1.0), (0.2, 1.0, 0.45)]

def color_loop(DEF, palette, period, shift=0):
    p = palette[shift:] + palette[:shift]; p = p + [p[0]]; n = len(p) - 1
    keys = ' '.join(f(i / n) for i in range(n + 1))
    return ("<TimeSensor DEF='%sT' cycleInterval='%s' loop='true'/><ColorInterpolator DEF='%s' key='%s' keyValue='%s'/>"
            "<ROUTE fromNode='%sT' fromField='fraction_changed' toNode='%s' toField='set_fraction'/>") % (DEF, f(period), DEF, keys, cols(p), DEF, DEF)

def spin(DEF, axis, period, reverse=False):
    a = [i * math.pi / 2 for i in range(5)]
    if reverse: a = [-x for x in a]
    kv = ', '.join('%s %s' % (v(axis), f(x)) for x in a)
    return ("<TimeSensor DEF='%sT' cycleInterval='%s' loop='true'/><OrientationInterpolator DEF='%sI' key='0 0.25 0.5 0.75 1' keyValue='%s'/>"
            "<ROUTE fromNode='%sT' fromField='fraction_changed' toNode='%sI' toField='set_fraction'/><ROUTE fromNode='%sI' fromField='value_changed' toNode='%s' toField='set_rotation'/>") % (DEF, f(period), DEF, kv, DEF, DEF, DEF, DEF)

def mirror_ball(rng):
    R, nl, nm = 30.0, 12, 24
    pts, idx, cc = [], [], []
    for i in range(nl + 1):
        th = math.pi * i / nl
        for j in range(nm):
            ph = 2 * math.pi * j / nm; pts.append((R * math.sin(th) * math.cos(ph), R * math.cos(th), R * math.sin(th) * math.sin(ph)))
    for i in range(nl):
        for j in range(nm):
            a, b = i * nm + j, i * nm + (j + 1) % nm; c, d = a + nm, b + nm
            idx.append('%d %d %d %d -1' % (a, c, d, b))
            r = rng.random()
            cc.append((0.95, 0.95, 1.0) if r < 0.12 else rng.choice(PARTY) if r < 0.3 else (0.42 + 0.2 * rng.random(),) * 3)
    shape = ("<Shape><Appearance><Material DEF='BallGlow' diffuseColor='0.8 0.8 0.85' specularColor='1 1 1' shininess='0.9' emissiveColor='0.3 0.1 0.3'/></Appearance>"
             "<IndexedFaceSet solid='true' ccw='false' creaseAngle='0' colorPerVertex='false' coordIndex='%s'><Coordinate point='%s'/><Color color='%s'/></IndexedFaceSet></Shape>") % (' '.join(idx), cols(pts), cols(cc))
    halo = "<Shape><Appearance><UnlitMaterial DEF='HaloMat' emissiveColor='1 0.4 0.9' transparency='0.82'/></Appearance><Sphere radius='46' solid='false'/></Shape>"
    hang = "<Shape><Appearance><UnlitMaterial emissiveColor='0.9 0.8 0.5'/></Appearance><IndexedLineSet coordIndex='0 1 -1'><Coordinate point='0 30 0 0 400 0'/></IndexedLineSet></Shape>"
    return ("<Transform translation='%s'>%s<Transform DEF='BallSpin'>%s</Transform>%s</Transform>" % (v(BALL), hang, shape, halo)
            + spin('BallSpin', (0, 1, 0), 9) + color_loop('BallHue', PARTY, 6)
            + "<ROUTE fromNode='BallHue' fromField='value_changed' toNode='BallGlow' toField='set_emissiveColor'/>"
            + color_loop('HaloHue', PARTY, 6, 2) + "<ROUTE fromNode='HaloHue' fromField='value_changed' toNode='HaloMat' toField='set_emissiveColor'/>")

def beams():
    out = []
    for g, (rev, period, shift) in enumerate(((False, 14, 0), (True, 10, 2))):
        parts = []
        for k in range(6):
            az = 2 * math.pi * (k + 0.5 * g) / 6; tilt = 0.55 + 0.18 * ((k + g) % 3)
            # a cone of light 300 m long, apex at the ball, leaning out by `tilt` toward azimuth `az`
            ax = (math.sin(az), 0.0, -math.cos(az))
            parts.append("<Transform rotation='%s %s'><Transform translation='0 -160 0'><Shape><Appearance><UnlitMaterial USE='Beam%dMat'/></Appearance>"
                         "<Cone height='320' bottomRadius='42' bottom='false' solid='false'/></Shape></Transform></Transform>" % (v(ax), f(tilt), g)) if k else \
                parts.append("<Transform rotation='%s %s'><Transform translation='0 -160 0'><Shape><Appearance><UnlitMaterial DEF='Beam%dMat' emissiveColor='1 0.3 0.8' transparency='0.72'/></Appearance>"
                             "<Cone height='320' bottomRadius='42' bottom='false' solid='false'/></Shape></Transform></Transform>" % (v(ax), f(tilt), g))
        out.append("<Transform translation='%s'><Transform DEF='Beams%d'>%s</Transform></Transform>" % (v(BALL), g, ''.join(parts)))
        out.append(spin('Beams%d' % g, (0, 1, 0), period, rev))
        out.append(color_loop('Beam%dHue' % g, PARTY, 4 + 2 * g, shift) + "<ROUTE fromNode='Beam%dHue' fromField='value_changed' toNode='Beam%dMat' toField='set_emissiveColor'/>" % (g, g))
    return ''.join(out)

def lasers():
    P = [KHUFU_TOP, KHAFRE_TOP, MENKAURE_TOP, SPHINX_HEAD, BALL, (OSIRIS_SITE[0], OSIRIS_SITE[1] + 2, OSIRIS_SITE[2])]
    sets = [((0, 1), (1, 2), (2, 0), (3, 0), (3, 1)), ((4, 1), (4, 2), (4, 3), (4, 5), (5, 0))]
    out = []
    for s, pairs in enumerate(sets):
        out.append("<Shape><Appearance><UnlitMaterial DEF='Laser%dMat' emissiveColor='0.1 1 0.6'/><LineProperties linewidthScaleFactor='4'/></Appearance>"
                   "<IndexedLineSet coordIndex='%s'><Coordinate point='%s'/></IndexedLineSet></Shape>" % (s, ' '.join('%d %d -1' % p for p in pairs), cols(P)))
        out.append(color_loop('Laser%dHue' % s, PARTY, 3 + s, 1 + 2 * s) + "<ROUTE fromNode='Laser%dHue' fromField='value_changed' toNode='Laser%dMat' toField='set_emissiveColor'/>" % (s, s))
    return ''.join(out)

def dance_floor():
    """5 x 5 tiles of 1.9 m on Khufu's flat summit (about 10 m across at 138.5 m), four colour groups on four tempos"""
    out, groups = [], {0: [], 1: [], 2: [], 3: []}
    for i in range(5):
        for j in range(5):
            groups[(i + 2 * j) % 4].append((-4.0 + 2.0 * i, KHUFU_TOP[1] + 0.2, -4.0 + 2.0 * j))
    for g, tiles in groups.items():
        for n, p in enumerate(tiles):
            mat = ("<UnlitMaterial DEF='Tile%dMat' emissiveColor='1 0.2 0.8'/>" % g) if n == 0 else "<UnlitMaterial USE='Tile%dMat'/>" % g
            out.append("<Transform translation='%s'><Shape><Appearance>%s</Appearance><Box size='1.85 0.25 1.85'/></Shape></Transform>" % (v(p), mat))
        out.append(color_loop('Tile%dHue' % g, PARTY, (0.5, 0.75, 1.0, 1.5)[g], g) + "<ROUTE fromNode='Tile%dHue' fromField='value_changed' toNode='Tile%dMat' toField='set_emissiveColor'/>" % (g, g))
    return ''.join(out)

def ring(r, n=96):
    return [(r * math.cos(2 * math.pi * i / n), 0.0, r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def pulse_rings():
    """two gold rings that grow out from Khufu's base and fade, one beat a second (the bird's heart beats about once a second)"""
    out = []
    for k in range(2):
        out.append("<Transform DEF='Pulse%d' translation='0 1 0'><Shape><Appearance><UnlitMaterial DEF='Pulse%dMat' emissiveColor='1 0.82 0.35'/><LineProperties linewidthScaleFactor='2'/></Appearance>"
                   "<IndexedLineSet coordIndex='%s 0 -1'><Coordinate point='%s'/></IndexedLineSet></Shape></Transform>" % (k, k, ' '.join(str(i) for i in range(96)), cols(ring(1.0))))
        out.append("<TimeSensor DEF='Pulse%dT' cycleInterval='2' loop='true' %s/><PositionInterpolator DEF='Pulse%dS' key='0 1' keyValue='130 1 130 900 1 900'/>"
                   "<ColorInterpolator DEF='Pulse%dC' key='0 0.7 1' keyValue='1 0.82 0.35 0.6 0.2 0.5 0 0 0'/>"
                   "<ROUTE fromNode='Pulse%dT' fromField='fraction_changed' toNode='Pulse%dS' toField='set_fraction'/><ROUTE fromNode='Pulse%dT' fromField='fraction_changed' toNode='Pulse%dC' toField='set_fraction'/>"
                   "<ROUTE fromNode='Pulse%dS' fromField='value_changed' toNode='Pulse%d' toField='set_scale'/><ROUTE fromNode='Pulse%dC' fromField='value_changed' toNode='Pulse%dMat' toField='set_emissiveColor'/>"
                   % (k, "startTime='1'" if k else '', k, k, k, k, k, k, k, k, k, k))
    return ''.join(out)

def osiris_marker():
    x, y, z = OSIRIS_SITE
    return ("<Transform translation='%s'><Shape><Appearance><UnlitMaterial emissiveColor='1 0.8 0.3'/><LineProperties linewidthScaleFactor='2'/></Appearance>"
            "<IndexedLineSet coordIndex='%s 0 -1'><Coordinate point='%s'/></IndexedLineSet></Shape>"
            "<Transform translation='0 60 0'><Shape><Appearance><UnlitMaterial DEF='OsirisPillar' emissiveColor='0.3 0.9 1' transparency='0.8'/></Appearance><Cylinder radius='4' height='120' top='false' bottom='false' solid='false'/></Shape></Transform></Transform>"
            % (v((x, y + 1.5, z)), ' '.join(str(i) for i in range(64)), cols(ring(9.0, 64))))

def box_lines(c, s):
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    P = [(c[0] + sx * hx, c[1] + sy * hy, c[2] + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    E = [(0, 1), (0, 2), (0, 4), (3, 1), (3, 2), (3, 7), (5, 1), (5, 4), (5, 7), (6, 2), (6, 4), (6, 7)]
    return P, E

def hall(rng):
    c, s = HALL, HALL_SIZE
    P, E = box_lines(c, s)
    # a corridor up to the left paw's tip (Cayce's story has a passage from the paw; invented here)
    paw = (SPHINX_SITE[0] + 30.0, SPHINX_SITE[1] + 1.4, SPHINX_SITE[2] - 4.0); door = (c[0] + s[0] / 2, c[1] - s[1] / 2 + 1.0, c[2])
    P += [door, (paw[0], door[1], door[2]), paw]; E += [(8, 9), (9, 10)]
    scrolls = []
    for row in range(3):
        for k in range(8):
            p = (c[0] - 5.0 + 1.4 * k, c[1] - 1.6 + 1.3 * row, c[2] - s[2] / 2 + 0.5)
            q = (p[0], p[1], c[2] + s[2] / 2 - 0.5)
            for pp in (p, q):
                scrolls.append("<Transform translation='%s' rotation='1 0 0 1.5708'><Shape><Appearance><UnlitMaterial USE='ScrollMat'/></Appearance><Cylinder radius='0.22' height='0.9'/></Shape></Transform>" % v(pp))
    scrolls[0] = scrolls[0].replace("<UnlitMaterial USE='ScrollMat'/>", "<UnlitMaterial DEF='ScrollMat' emissiveColor='1 0.78 0.3'/>")
    tablet = "<Transform translation='%s'><Shape><Appearance><UnlitMaterial DEF='TabletMat' emissiveColor='0.2 1 0.9'/></Appearance><Box size='0.3 2.2 1.6'/></Shape></Transform>" % v((c[0] - s[0] / 2 + 1.0, c[1] - 0.9, c[2]))
    walls = "<Transform translation='%s'><Shape><Appearance><UnlitMaterial emissiveColor='0.05 0.6 0.7' transparency='0.86'/></Appearance><Box size='%s' solid='false'/></Shape></Transform>" % (v(c), v(s))
    wire = ("<Shape><Appearance><UnlitMaterial DEF='HallWire' emissiveColor='0.2 1 0.9'/><LineProperties linewidthScaleFactor='3'/></Appearance>"
            "<IndexedLineSet coordIndex='%s'><Coordinate point='%s'/></IndexedLineSet></Shape>") % (' '.join('%d %d -1' % e for e in E), cols(P))
    scan = ("<Transform DEF='HallScan' translation='%s'><Shape><Appearance><UnlitMaterial emissiveColor='0.3 1 0.8' transparency='0.7'/></Appearance><Box size='%s' solid='false'/></Shape></Transform>"
            "<TimeSensor DEF='HallScanT' cycleInterval='3' loop='true'/><PositionInterpolator DEF='HallScanI' key='0 0.5 1' keyValue='%s %s %s'/>"
            "<ROUTE fromNode='HallScanT' fromField='fraction_changed' toNode='HallScanI' toField='set_fraction'/><ROUTE fromNode='HallScanI' fromField='value_changed' toNode='HallScan' toField='set_translation'/>"
            % (v(c), v((s[0] + 6, 0.08, s[2] + 6)), v((c[0], c[1] - 8, c[2])), v((c[0], c[1] + 14, c[2])), v((c[0], c[1] - 8, c[2]))))
    pillar = ("<Transform translation='%s'><Shape><Appearance><UnlitMaterial emissiveColor='0.2 1 0.9' transparency='0.85'/></Appearance><Cylinder radius='3' height='70' top='false' bottom='false' solid='false'/></Shape></Transform>"
              % v((c[0], c[1] + 35, c[2])))
    return walls + wire + scan + tablet + ''.join(scrolls) + pillar + color_loop('HallHue', [(0.2, 1, 0.9), (0.4, 0.6, 1.0), (0.2, 1, 0.5)], 5) + \
        "<ROUTE fromNode='HallHue' fromField='value_changed' toNode='HallWire' toField='set_emissiveColor'/>"

def giza_host(seed=7):
    rng = random.Random(seed)
    x, y, z = SPHINX_SITE; ox, oy, oz = OSIRIS_SITE
    inl = lambda DEF, url, load=True: "<Inline DEF='%s' url='\"%s\"'%s/>" % (DEF, url, '' if load else " load='false'")
    body = [
        "<WorldInfo title='Giza, disco night (nested in the Gobbler)' info='\"Giza v2.1 files, unchanged except the Khufu level of detail forced to its mesh\" \"the disco layer and the Hall of Records are additions; the Hall is hypothetical\"'/>",
        "<Group DEF='GizaLit'>",
        "<DirectionalLight DEF='DuskSun' global='false' direction='-0.82 -0.32 0.47' color='1 0.62 0.4' intensity='1.3' ambientIntensity='0.15'/>",
        "<DirectionalLight DEF='NightFill' global='false' direction='0.5 -0.6 -0.6' color='0.5 0.55 1' intensity='0.7' ambientIntensity='0.2'/>",
        inl('Plateau', 'plateau-v21.xml'),
        "<Transform translation='%s'>%s%s%s</Transform>" % (v(SPHINX_SITE), inl('Ground', 'sphinx-terrain-v21.xml'), inl('SphinxMesh', 'sphinx-today-mesh-v21.xml', False), inl('SiteToday', 'sphinx-context-today-v21.xml')),
        "<Transform translation='%s'>%s</Transform>" % (v(OSIRIS_SITE), inl('Osiris', 'osiris-paganini-v21.xml')),
        "<PointLight DEF='BallLight' global='false' location='%s' color='1 0.3 0.8' intensity='2.4' radius='1200' attenuation='1 0 0'/>" % v(BALL),
        "<Group DEF='Disco'>", mirror_ball(rng), beams(), lasers(), dance_floor(), pulse_rings(), osiris_marker(), "</Group>",
        "<ROUTE fromNode='BallHue' fromField='value_changed' toNode='BallLight' toField='set_color'/>",
        "</Group>",
        # the Sphinx mesh (2 MB gzipped) waits until the camera comes within about 600 m of the Sphinx
        "<ProximitySensor DEF='SphinxNear' center='%s' size='1200 1200 1200'/><BooleanFilter DEF='SphinxLoad'/>" % v((x, y + 20, z)),
        "<IMPORT inlineDEF='Plateau' importedDEF='KhufuLook' AS='KhufuLook'/><IMPORT inlineDEF='Plateau' importedDEF='InteriorSwitch' AS='InteriorSwitch'/>",
        "<TimeSensor DEF='XrayClock' cycleInterval='16' loop='true'/><IntegerSequencer DEF='XrayLook' key='0 0.5' keyValue='0 1'/><IntegerSequencer DEF='XrayInterior' key='0 0.5' keyValue='-1 0'/>",
        "<Group DEF='HallOfRecords'>", hall(rng), "</Group>",
        "<ROUTE fromNode='SphinxNear' fromField='isActive' toNode='SphinxLoad' toField='set_boolean'/><ROUTE fromNode='SphinxLoad' fromField='inputTrue' toNode='SphinxMesh' toField='set_load'/>",
        "<ROUTE fromNode='XrayClock' fromField='fraction_changed' toNode='XrayLook' toField='set_fraction'/><ROUTE fromNode='XrayClock' fromField='fraction_changed' toNode='XrayInterior' toField='set_fraction'/>",
        "<ROUTE fromNode='XrayLook' fromField='value_changed' toNode='KhufuLook' toField='set_whichChoice'/><ROUTE fromNode='XrayInterior' fromField='value_changed' toNode='InteriorSwitch' toField='set_whichChoice'/>",
    ]
    head = ("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.1' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.1.xsd'>\n"
            "<head><component name='Rendering' level='5'/><component name='Shape' level='4'/><component name='Lighting' level='3'/><component name='Interpolation' level='5'/><component name='EventUtilities' level='1'/><component name='Networking' level='3'/>"
            "<meta name='title' content='giza-nest.x3d'/><meta name='description' content='Giza v2.1 (plateau, Sphinx, temples, Osiris Shaft) nested in the Gobbler, with a disco layer and a hypothetical Hall of Records. Synthetic and schematic: a simulacrum, not a survey.'/>"
            "<meta name='hall-of-records' content=\"%s\"/></head>\n<Scene>\n" % HALL_NOTE.replace('"', '&quot;'))
    return head + '\n'.join(body) + "\n</Scene>\n</X3D>\n"
