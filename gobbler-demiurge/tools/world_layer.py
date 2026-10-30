"""The world layer of the Gobbler demiurge scene: Earth with its clouds and Moon (Blender), the village Aurelsbrunn (Blender), the villagers (the same H-Anim rig, dressed in three outfits in Blender, one per lane, shared by USE),
the tether from the village mast to the heart, and the stops of the zoom ladder that reach them (4 Earth and Moon, 5 the village from orbit, 6 the plaza, 7 a villager).
The villagers (three H-Anim bodies, twelve walkers) are a fifth lazy file, data/bird/villagers.x3d, loaded with the village, so none of them is in the boot payload.

The Earth also wears an atmosphere (ATMOSPHERE below): one sphere, drawn in a GLSL shader that integrates single scattering along each ray through a thin shell, so the planet gets
a blue limb that goes red at the terminator and a halo against the dark, and a camera standing on the ground sees a thin haze along the curved horizon. It is plain X3D 4.0 (a
ComposedShader on an alpha-blended Sphere, which X_ITE draws without writing depth); the one thing the page does for it is tell it whether the logarithmic depth buffer is on
(the `logDepth` field, see setDepth in src/boot.js), so that its depth matches the rest of the scene.

Everything here sits inside the Loom group so it moves with the bird; the page pauses the sway while the camera is down there (see src/boot.js). The big Inlines (the
planet, the village, the villagers) stay unloaded until the camera comes near: a ProximitySensor around Earth loads the planet files, one around the village loads the village, and each
group is only drawn while its sensor is active. The numbers come from tools/village_spec.py, shared with the Blender scripts.

build(L, anchor) -> (xml, info, villagers_x3d): L is the layers module (its helpers), anchor() adds a tag; info goes to data/bird/world.json for the page and the last item is
the text of data/bird/villagers.x3d.
"""
import math, random
import village_spec as VS

TENDER_GAIT_LANES = ((7.4, 0, +1, 4), (9.0, 1, -1, 4), (13.4, 2, +1, 4))       # radius (m), gait copy (and outfit), direction (+1 or -1), walkers
KHACHKAR_R, KHACHKAR_AZ = 11.0, 60.0          # the khachkar (tools/blender_khachkar.py): metres from the fountain and degrees from east toward north; between the stalls at 30 and 90 degrees, clear of the lanes at 9.0 and 13.4 m
VILLAGER_COPY = 3                                                              # the villagers' H-Anim copies are numbered after the three shell tenders (hanim_T3 to hanim_T5)

ATM_TOP, ATM_MARGIN = 1.07, 1.02          # the atmosphere reaches 7% above the planet's surface (17 m at village scale, about four times the real share, drawn big like everything else);
                                          # the sphere that carries the shader is 2% larger so that its polygon edge never cuts the glow
ATM_K, ATM_DECAY, ATM_GAIN, ATM_MIE = 4.5, 6.0, 1.0, 0.05      # extinction, how fast the air thins with height (scale height is the top divided by this), brightness, share of forward scattering
ATMOSPHERE = """<ComposedShader DEF='AirShader' language='GLSL'><field name='sunDir' type='SFVec3f' accessType='inputOutput' value='@SUN@'/><field name='logDepth' type='SFFloat' accessType='inputOutput' value='0'/>
<ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex,#version 300 es
precision highp float;
precision highp int;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec3 vP;
out float depth;
void main() {
  vec4 p = x3d_ModelViewMatrix * x3d_Vertex;
  vP = p.xyz;
  gl_Position = x3d_ProjectionMatrix * p;
  depth = 1.0 + gl_Position.w;
}
]]></ShaderPart>
<ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,#version 300 es
precision highp float;
precision highp int;
uniform mat4 x3d_ModelViewMatrix;
uniform float x3d_LogarithmicFarFactor1_2;
uniform vec3 sunDir;
uniform float logDepth;
in vec3 vP;
in float depth;
out vec4 x3d_FragColor;
const float TOP = @TOP@;
const float MARGIN = @MARGIN@;
const float K = @K@;
const float DECAY = @DECAY@;
const float GAIN = @GAIN@;
const float MIE = @MIE@;
void main() {
  vec3 d = normalize(vP);
  float rs = length(x3d_ModelViewMatrix[0].xyz) / MARGIN;
  float rp = rs / TOP;
  vec3 C = x3d_ModelViewMatrix[3].xyz;
  vec3 S = normalize(mat3(x3d_ModelViewMatrix) * sunDir);
  float cc = dot(C, C), b = dot(d, C);
  bool inside = cc < rs * rs;
  if (gl_FrontFacing == inside) discard;
  float disc = b * b - (cc - rs * rs);
  if (disc <= 0.0) discard;
  float sq = sqrt(disc);
  float t0 = max(b - sq, 0.0), t1 = b + sq;
  float dp = b * b - (cc - rp * rp);
  if (dp > 0.0) { float tp = b - sqrt(dp); if (tp > 0.0) t1 = min(t1, tp); }
  if (t1 <= t0) discard;
  float dt = (t1 - t0) / 10.0;
  float cs = dot(d, S);
  float phase = 0.45 * (1.0 + cs * cs) + MIE * 0.64 / pow(1.36 - 1.2 * cs, 1.5);
  vec3 acc = vec3(0.0);
  float od = 0.0;
  for (int i = 0; i < 10; i++) {
    vec3 p = d * (t0 + (float(i) + 0.5) * dt) - C;
    float r = length(p);
    float rho = exp(-DECAY * clamp((r - rp) / (rs - rp), 0.0, 1.0));
    float up = dot(p / r, S);
    vec3 src = mix(vec3(1.0, 0.40, 0.12), vec3(0.40, 0.66, 1.0), smoothstep(-0.05, 0.55, up));
    float w = rho * dt / rp;
    acc += src * (smoothstep(-0.18, 0.22, up) * w * phase);
    od += w;
  }
  float alpha = 1.0 - exp(-K * od);
  x3d_FragColor = vec4(min(acc * (K * GAIN) / max(alpha, 0.02), vec3(1.5)), alpha);
  gl_FragDepth = logDepth > 0.5 ? log2(depth) * x3d_LogarithmicFarFactor1_2 : gl_FragCoord.z;
}
]]></ShaderPart></ComposedShader>"""


def fp(x): return '%.7g' % x
def gf(x):
    """A float literal for GLSL ES 3.00, which has no implicit int to float conversion: always carries a point or an exponent."""
    t = fp(x)
    return t if any(c in t for c in '.eE') else t + '.0'


def v7(p): return ' '.join(fp(x) for x in p)


def build(L, anchor):
    E = VS.earth_pos(); site, up, east, north = VS.site_frame(); S = VS.SCALE; SUN = VS.SUN
    neg = lambda a: (-a[0], -a[1], -a[2])
    axis, ang = L.basis_rotation(east, up, neg(north))                       # village local X = east, Y = up, Z = south (a right-handed frame)
    at = lambda x, y, h: tuple(site[i] + (east[i] * x + north[i] * y + up[i] * h) * S for i in range(3))      # a village point (metres east, north, up) in scene units
    sag = lambda r: math.sqrt(max(VS.R_PLANET ** 2 - r * r, 1.0)) - VS.R_PLANET
    tip = at(0, 0, 62.45)
    X = []

    # ---- sensors (outside the groups, so they keep working while the groups are hidden) and the lazy loads
    X.append("<ProximitySensor DEF='EarthSense' center='%s' size='16 16 16'/><ProximitySensor DEF='VillageSense' center='%s' size='2.6 2.6 2.6'/>" % (v7(E), v7(site)))
    ROUTES = ("<BooleanFilter DEF='EarthLoad'/><BooleanFilter DEF='VillageLoad'/>"
             "<ROUTE fromNode='EarthSense' fromField='isActive' toNode='EarthLoad' toField='set_boolean'/>"
             "<ROUTE fromNode='VillageSense' fromField='isActive' toNode='VillageLoad' toField='set_boolean'/>"
             + ''.join("<ROUTE fromNode='EarthLoad' fromField='inputTrue' toNode='%s' toField='set_load'/>" % n for n in ('EarthPlanet', 'EarthClouds', 'EarthMoon'))
             + ''.join("<ROUTE fromNode='VillageLoad' fromField='inputTrue' toNode='%s' toField='set_load'/>" % n for n in ('VillageInline', 'VillagersInline'))
             + "<ROUTE fromNode='EarthSense' fromField='isActive' toNode='EarthWorld' toField='set_visible'/>"
             "<ROUTE fromNode='VillageSense' fromField='isActive' toNode='Villagers' toField='set_visible'/>")  # the routes come after the nodes they name

    # ---- Earth, clouds, Moon (Blender): the planet is a little under its true sphere so the village ground (which lies on the sphere) stands clear of it
    RE = VS.R_EARTH
    inl = lambda d, f_: "<Inline DEF='%s' load='false' url='\"data/bird/%s\"'/>" % (d, f_)
    W = ["<Transform DEF='EarthBody' translation='%s' scale='%s %s %s'>%s</Transform>" % (v7(E), fp(RE * 0.9992), fp(RE * 0.9992), fp(RE * 0.9992), inl('EarthPlanet', 'earth-planet.x3d'))]
    W.append("<Transform DEF='CloudTurn' translation='%s' scale='%s %s %s'>%s</Transform>" % (v7(E), fp(RE), fp(RE), fp(RE), inl('EarthClouds', 'earth-clouds.x3d')))
    ax = L.norm((0.09, 1.0, 0.04)); angs = (0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi)
    W.append("<Transform DEF='MoonOrbit' center='%s'><Transform translation='%s'><Transform DEF='MoonKeep' scale='%s %s %s'>%s</Transform></Transform></Transform>"
             % (v7(E), v7((E[0] + VS.MOON_ORBIT, E[1], E[2])), fp(VS.MOON_R), fp(VS.MOON_R), fp(VS.MOON_R), inl('EarthMoon', 'earth-moon.x3d')))
    W.append("<TimeSensor DEF='MoonClock' cycleInterval='150' loop='true'/><OrientationInterpolator DEF='MoonPath' key='0 0.25 0.5 0.75 1' keyValue='%s'/><OrientationInterpolator DEF='MoonUnturn' key='0 0.25 0.5 0.75 1' keyValue='%s'/>"
             "<ROUTE fromNode='MoonClock' fromField='fraction_changed' toNode='MoonPath' toField='set_fraction'/><ROUTE fromNode='MoonPath' fromField='value_changed' toNode='MoonOrbit' toField='set_rotation'/>"
             "<ROUTE fromNode='MoonClock' fromField='fraction_changed' toNode='MoonUnturn' toField='set_fraction'/><ROUTE fromNode='MoonUnturn' fromField='value_changed' toNode='MoonKeep' toField='set_rotation'/>"      # the Moon does not turn as it orbits, so the Sun-lit side baked into it keeps facing the Sun
             % (', '.join('%s %s' % (v7(ax), fp(a_)) for a_ in angs), ', '.join('%s %s' % (v7(ax), fp(-a_)) for a_ in angs)))
    shader = ATMOSPHERE.replace('@SUN@', v7(up)).replace('@TOP@', gf(ATM_TOP)).replace('@MARGIN@', gf(ATM_MARGIN)).replace('@K@', gf(ATM_K)).replace('@DECAY@', gf(ATM_DECAY)).replace('@GAIN@', gf(ATM_GAIN)).replace('@MIE@', gf(ATM_MIE))
    W.append("<Transform DEF='EarthAir' translation='%s' scale='%s %s %s'><Shape><Appearance alphaMode='BLEND'>%s</Appearance><Sphere solid='false' radius='1'/></Shape></Transform>"
             % (v7(E), fp(RE * ATM_TOP * ATM_MARGIN), fp(RE * ATM_TOP * ATM_MARGIN), fp(RE * ATM_TOP * ATM_MARGIN), shader))
    W.append("<TimeSensor DEF='CloudClock' cycleInterval='420' loop='true'/><OrientationInterpolator DEF='CloudPath' key='0 0.25 0.5 0.75 1' keyValue='%s'/>"
             "<ROUTE fromNode='CloudClock' fromField='fraction_changed' toNode='CloudPath' toField='set_fraction'/><ROUTE fromNode='CloudPath' fromField='value_changed' toNode='CloudTurn' toField='set_rotation'/>"
             % ', '.join('0 1 0 %s' % fp(a_) for a_ in (0, math.pi / 2, math.pi, 3 * math.pi / 2, 2 * math.pi)))

    # ---- the tether: from the mast tip to the heart, with climbers (simulated), drawn as a fine gold line
    W.append("<Shape><Appearance alphaMode='BLEND'><Material emissiveColor='1 0.84 0.46' diffuseColor='0 0 0' transparency='0.12'/></Appearance>"
             "<IndexedLineSet coordIndex='0 1 -1'><Coordinate point='%s %s'/></IndexedLineSet></Shape>" % (v7(tip), v7(SUN)))
    dt = L.norm(L.sub(SUN, tip)); rax = L.cross((0, 1, 0), dt); rang = math.acos(max(-1.0, min(1.0, dt[1]))); Lt = math.dist(SUN, tip)
    W.append("<Transform translation='%s' rotation='%s %s'><Billboard axisOfRotation='0 1 0'><Shape><Appearance alphaMode='BLEND'/><IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1'>"
             "<ColorRGBA color='1 0.86 0.5 0.85 1 0.86 0.5 0.85 1 0.92 0.66 0.10 1 0.92 0.66 0.10'/><Coordinate point='%s %s %s %s'/></IndexedFaceSet></Shape></Billboard></Transform>"
             % (v7(tip), v7(L.norm(rax)), fp(rang), v7((-0.00045, 0, 0)), v7((0.00045, 0, 0)), v7((0.006, Lt, 0)), v7((-0.006, Lt, 0))))       # a sunbeam ribbon that always faces you, widening toward the heart
    for k, (per, off, sz) in enumerate(((46, 0.0, 2.4), (58, 0.31, 2.0), (73, 0.64, 2.2), (52, 0.82, 1.8))): W.append(_climber(L, k, per, off, sz, tip, SUN))

    # ---- the village frame: the Blender village and the villagers, two lazy Inlines in one frame (village metres, +Y up, scaled to the planet)
    W.append("<Transform DEF='VillageFrame' translation='%s' rotation='%s %s' scale='%s %s %s'>%s<Group DEF='Villagers' visible='false'>%s</Group></Transform>"
             % (v7(site), v7(axis), fp(ang), fp(S), fp(S), fp(S), inl('VillageInline', 'village.x3d'), inl('VillagersInline', 'villagers.x3d')))
    X.append("<Group DEF='EarthWorld' visible='false'>%s</Group>" % ''.join(W)); X.append(ROUTES)

    cam = lambda x, y, h: at(x, y, h + sag(math.hypot(x, y)))
    c4 = tuple(E[i] + 0.88 * (0.78 * up[i] + 0.55 * east[i] + 0.30 * north[i]) for i in range(3))
    # ---- tags
    unit_km = 2.4 / 3.3 * 149597871                                              # one scene unit in km, if the 3.3-unit ribcage is the plan's 2.4 AU
    big = VS.R_EARTH * unit_km / 6371; far = VS.MOON_ORBIT * unit_km / 384400
    right = L.norm(L.cross(L.sub(E, c4), (0, 1, 0)))
    anchor('earth', 'Earth and Moon', 'drawn about %s times too large so that you can see it, and the Moon about %d times too far out' % (format(int(round(big, -2)), ','), round(far)), tuple(E[i] + right[i] * VS.R_EARTH * 1.25 for i in range(3)))
    anchor('village', 'Aurelsbrunn', 'a 160 m village on a planet drawn 250 m in radius: the real Earth is 6,371 km, so the village is about 25,000 times too big for its planet', at(0, 0, 30))
    anchor('tether', 'The tether', 'from the fountain mast to the heart · the climbers on it are simulated', tuple(tip[i] + (SUN[i] - tip[i]) * 0.012 for i in range(3)))
    kx, ky = KHACHKAR_R * math.cos(math.radians(KHACHKAR_AZ)), KHACHKAR_R * math.sin(math.radians(KHACHKAR_AZ))
    anchor('khachkar', 'Khachkar', 'an Armenian cross-stone, 2.4 m of warm tufa: a cross growing from a wheel of eternity, framed in interlace · modelled in Blender', cam(kx, ky, 3.3))
    anchor('villagers', 'Villagers', 'H-Anim humans made in Blender, 1.75 m tall · their walk and their errands are simulated', cam(8.6, 3.4, 2.3))

    # ---- the stops
    c5 = tuple(site[i] + 0.13 * (0.33 * up[i] + 0.92 * east[i] + 0.25 * north[i]) for i in range(3))
    stops = {
        'earth': dict(label='Earth and Moon', pos=c4, look=E, fov=0.8, up=(0, 1, 0)),
        'village': dict(label='Village from orbit', pos=c5, look=at(0, 0, 30), fov=0.85, up=up),
        'plaza': dict(label='Plaza', pos=cam(-14.6, 0.0, 1.9), look=at(0, 0, 7), fov=1.15, up=up),
        'villager': dict(label='A villager', pos=cam(11.6, 0.3, 1.5), look=cam(6.5, 0.0, 1.25), fov=0.9, up=up),
    }
    info = dict(earth=E, site=site, up=up, east=east, north=north, sun=SUN, tip=tip, scale=S, r_earth=RE, r_planet=VS.R_PLANET, human_h=VS.HUMAN_H,
                stops={k_: dict(v_, **{c: [round(x, 7) for x in v_[c]] for c in ('pos', 'look', 'up')}) for k_, v_ in stops.items()},
                inlines=dict(planet='data/bird/earth-planet.x3d', clouds='data/bird/earth-clouds.x3d', moon='data/bird/earth-moon.x3d', village='data/bird/village.x3d'),
                villagers=k)
    return ''.join(X), info, villagers_file(L, sag)


def villagers_file(L, sag):
    """the text of data/bird/villagers.x3d: twelve walkers on three lanes of the plaza (village metres, +Y up), three H-Anim bodies (one outfit and one gait each) shared by USE among the
    walkers of a lane, each walker a little taller or shorter than 1.75 m, with the walk cycles and the orbits. All of it is plain X3D (interpolators and ROUTEs, no Script)."""
    walkers = []; walks = []; made = set(); k = 0; STRIDE = 0.8 * VS.HUMAN_H; jit = random.Random(29)                     # the villager files are one unit tall: scale them to people
    for r, gait, d, count in TENDER_GAIT_LANES:
        Tg = L.TENDER_GAITS[gait]; per = 2 * math.pi * r * Tg / STRIDE
        for j in range(count):
            ph = 2 * math.pi * (j + 0.25 * gait) / count; s = -1.0 if d > 0 else 1.0           # axis -Y carries the walker toward +Z at phase 0 (it faces +Z); axis +Y needs the figure turned round
            face = '' if d > 0 else " rotation='0 1 0 3.14159'"
            keys = ' '.join(fp(q) for q in (0, .25, .5, .75, 1)); vals = ', '.join('0 %s 0 %s' % (fp(s), fp(ph + q * 2 * math.pi)) for q in (0, .25, .5, .75, 1))
            if gait in made: body = "<Group USE='VillagerBody%d'/>" % gait
            else:
                body = "<Group DEF='VillagerBody%d'>%s</Group>" % (gait, L.TD.humanoid(VILLAGER_COPY + gait, L.TD.VILLAGERS['abc'[gait]])); made.add(gait); walks.append(L.tender_walk(VILLAGER_COPY + gait, L.TENDER_GAITS[gait]))
            scale = VS.HUMAN_H * (0.94 + 0.12 * jit.random())
            walkers.append("<Transform DEF='Villager%d'><Transform translation='%s %s 0'%s><Transform scale='%s %s %s'>%s</Transform></Transform></Transform>"
                           "<TimeSensor DEF='VillagerClock%d' cycleInterval='%s' loop='true'/><OrientationInterpolator DEF='VillagerOrbit%d' key='%s' keyValue='%s'/>"
                           "<ROUTE fromNode='VillagerClock%d' fromField='fraction_changed' toNode='VillagerOrbit%d' toField='set_fraction'/><ROUTE fromNode='VillagerOrbit%d' fromField='value_changed' toNode='Villager%d' toField='set_rotation'/>"
                           % (k, fp(r), fp(sag(r)), face, fp(scale), fp(scale), fp(scale), body, k, fp(per), k, keys, vals, k, k, k, k))
            k += 1
    assert k == sum(c for _, _, _, c in TENDER_GAIT_LANES)
    return ("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'>\n  <head><component name='HAnim' level='1'/></head>\n  <Scene>\n    "
            + ''.join(walkers) + ''.join(walks) + "\n  </Scene>\n</X3D>\n")


def _climber(L, k, per, off, sz, tip, SUN):
    """one bead that runs the tether from the mast to the heart every `per` seconds; `off` starts it part-way up. Wrapping is a step key (two equal keys), not a flight back down."""
    if off > 0:
        mid = tuple(tip[i] + (SUN[i] - tip[i]) * off for i in range(3)); e = fp(1 - off)
        key = '0 %s %s 1' % (e, e); vals = '%s, %s, %s, %s' % (v7(mid), v7(SUN), v7(tip), v7(mid)); start = mid
    else:
        key = '0 1'; vals = '%s, %s' % (v7(tip), v7(SUN)); start = tip
    return ("<Transform DEF='Climber%d' translation='%s'>%s</Transform>"
            "<TimeSensor DEF='ClimbClock%d' cycleInterval='%d' loop='true'/><PositionInterpolator DEF='ClimbPath%d' key='%s' keyValue='%s'/>"
            "<ROUTE fromNode='ClimbClock%d' fromField='fraction_changed' toNode='ClimbPath%d' toField='set_fraction'/><ROUTE fromNode='ClimbPath%d' fromField='value_changed' toNode='Climber%d' toField='set_translation'/>"
            % (k, v7(start), L.points_shape([(0, 0, 0)], [(1.0, 0.9, 0.62)], 3, [sz]), k, per, k, key, vals, k, k, k, k))
