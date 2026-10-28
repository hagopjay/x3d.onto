"""The world layer of the Gobbler demiurge scene: Earth with its clouds and Moon (Blender), the village Aurelsbrunn (Blender), the villagers (the Blender tenders, shared by USE),
the tether from the village mast to the heart, and the stops of the zoom ladder that reach them (4 Earth and Moon, 5 the village from orbit, 6 the plaza, 7 a villager).

Everything here sits inside the Loom group so it moves with the bird; the page pauses the sway while the camera is down there (see src/boot.js). The two big Inlines (the
planet, the village) stay unloaded until the camera comes near: a ProximitySensor around Earth loads the planet files, one around the village loads the village, and each
group is only drawn while its sensor is active. The numbers come from tools/village_spec.py, shared with the Blender scripts.

build(L, anchor) -> (xml, info): L is the layers module (its helpers), anchor() adds a tag; info goes to data/bird/world.json for the page.
"""
import math
import village_spec as VS

TENDER_GAIT_LANES = ((7.4, 0, +1, 4), (9.0, 1, -1, 4), (13.4, 2, +1, 4))       # radius (m), gait copy, direction (+1 or -1), walkers


def fp(x): return '%.7g' % x


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
             + "<ROUTE fromNode='VillageLoad' fromField='inputTrue' toNode='VillageInline' toField='set_load'/>"
             "<ROUTE fromNode='EarthSense' fromField='isActive' toNode='EarthWorld' toField='set_visible'/>"
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

    # ---- the village frame: the Blender village as an Inline, the walkers beside it
    walkers = []; k = 0; scale = VS.HUMAN_H / L.TENDER_H; STRIDE = 0.8 * VS.HUMAN_H
    for r, gait, d, count in TENDER_GAIT_LANES:
        Tg = L.TENDER_GAITS[gait]; per = 2 * math.pi * r * Tg / STRIDE
        for j in range(count):
            ph = 2 * math.pi * (j + 0.25 * gait) / count; s = -1.0 if d > 0 else 1.0           # axis -Y carries the walker toward +Z at phase 0 (it faces +Z); axis +Y needs the figure turned round
            face = '' if d > 0 else " rotation='0 1 0 3.14159'"
            keys = ' '.join(fp(q) for q in (0, .25, .5, .75, 1)); vals = ', '.join('0 %s 0 %s' % (fp(s), fp(ph + q * 2 * math.pi)) for q in (0, .25, .5, .75, 1))
            walkers.append("<Transform DEF='Villager%d'><Transform translation='%s %s 0'%s><Transform scale='%s %s %s'><Group USE='TenderBody%d'/></Transform></Transform></Transform>"
                           "<TimeSensor DEF='VillagerClock%d' cycleInterval='%s' loop='true'/><OrientationInterpolator DEF='VillagerOrbit%d' key='%s' keyValue='%s'/>"
                           "<ROUTE fromNode='VillagerClock%d' fromField='fraction_changed' toNode='VillagerOrbit%d' toField='set_fraction'/><ROUTE fromNode='VillagerOrbit%d' fromField='value_changed' toNode='Villager%d' toField='set_rotation'/>"
                           % (k, fp(r), fp(sag(r)), face, fp(scale), fp(scale), fp(scale), gait, k, fp(per), k, keys, vals, k, k, k, k))
            k += 1
    W.append("<Transform DEF='VillageFrame' translation='%s' rotation='%s %s' scale='%s %s %s'>%s<Group DEF='Villagers' visible='false'>%s</Group></Transform>"
             % (v7(site), v7(axis), fp(ang), fp(S), fp(S), fp(S), inl('VillageInline', 'village.x3d'), ''.join(walkers)))
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
    return ''.join(X), info


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
