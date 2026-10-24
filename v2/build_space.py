"""Space half of the v2 scene: environment, Sun / Earth / Moon, ecliptic grid, orbits and the ontology constellation (all through x3d_mcp)."""
import colorsys, json, math, random
from pathlib import Path
from mcpkit import B, look
ROOT = Path(__file__).resolve().parent.parent
AU = 1.495978707e11; RE = 6.371e6; RM = 1.7374e6; RS = 6.957e8
RC = 3.6e11           # constellation shell radius (2.4 AU)
KS = RC / 8.0         # v1 shell radius was 8 units
RING = {"X3D": 2.20e11, "URDF": 2.55e11, "glTF": 2.90e11}; LOOP_R = 3.15e11
PILLAR_R = 1.95e11
D = json.loads((ROOT / "data" / "explorer.json").read_text()); MAN = json.loads((ROOT / "data" / "manifest.ontology41.json").read_text()); COMP = json.loads((ROOT / "data" / "components.json").read_text())
UR = json.loads((ROOT / "out" / "xdomain_urdf.json").read_text()); GL = json.loads((ROOT / "out" / "xdomain_gltf.json").read_text()); TOUR = json.loads((ROOT / "demo" / "tour-data.json").read_text())
MAXD = D["stats"]["max_depth"]; fams = sorted(D["families"], key=lambda f: -D["families"][f])
def rgb(f): return [round(v, 3) for v in colorsys.hls_to_rgb((fams.index(f) * 137.5 % 360) / 360, .62, .7)]
def sph(n, R=8.0):
    lon = n["a"]; lat = math.radians(70 - n["d"] * 140 / MAXD)
    return [R * math.cos(lat) * math.cos(lon), R * math.sin(lat), R * math.cos(lat) * math.sin(lon)]
def slerp(a, b, t, lift, R=8.0):
    ra = math.sqrt(sum(x * x for x in a)); rb = math.sqrt(sum(x * x for x in b)); ua = [x / ra for x in a]; ub = [x / rb for x in b]
    dot = max(-1, min(1, sum(x * y for x, y in zip(ua, ub)))); om = math.acos(dot)
    if om < 1e-6: return a
    s = [(math.sin((1 - t) * om) * x + math.sin(t * om) * y) / math.sin(om) for x, y in zip(ua, ub)]; r = R * (1 + lift * math.sin(math.pi * t)); return [r * x for x in s]
def circle(rad, n=128, y=0.0): return [[rad * math.cos(2 * math.pi * i / n), y, rad * math.sin(2 * math.pi * i / n)] for i in range(n)]
def e3(v): return [float(f"{x:.6g}") for x in v]                    # compact numbers for huge coordinates

async def build_env(b: B):
    await b.mk("NavigationInfo", {"type": ["NONE"], "headlight": False, "avatarSize": [0.2, 1.7, 0.4], "visibilityLimit": 1e14, "speed": 1}, name="Nav")
    await b.mk("Background", {"skyColor": [[0, 0, 0]], "frontUrl": ["../tex/stars_front.png"], "backUrl": ["../tex/stars_back.png"], "leftUrl": ["../tex/stars_left.png"], "rightUrl": ["../tex/stars_right.png"], "topUrl": ["../tex/stars_top.png"], "bottomUrl": ["../tex/stars_bottom.png"]}, name="BgSpace")
    await b.mk("Background", {"skyColor": [[0.12, 0.28, 0.62], [0.55, 0.74, 0.95]], "skyAngle": [1.5], "groundColor": [[0.28, 0.3, 0.26], [0.45, 0.5, 0.45]], "groundAngle": [1.4]}, name="BgDay")
    await b.mk("Fog", {"color": [0.7, 0.8, 0.9], "fogType": "EXPONENTIAL", "visibilityRange": 0}, name="FogNone")
    await b.mk("Fog", {"color": [0.7, 0.8, 0.9], "fogType": "EXPONENTIAL", "visibilityRange": 9000}, name="FogTown")
    await b.mk("Viewpoint", {"position": [0, 1.7, 30], "orientation": [0, 1, 0, 0], "fieldOfView": 0.9}, name="Cam")

async def build_world(b: B):
    w = await b.mk("Transform", name="World")
    await b.mk("DirectionalLight", {"direction": [0, 0, 1], "intensity": 4.2, "color": [1, 0.97, 0.92]}, parent=w, name="SunDir")
    sunT = await b.mk("Transform", parent=w, name="SunT"); sh = await b.mk("Shape", parent=sunT, name="SunBody"); ap = await b.mk("Appearance", parent=sh)
    um = await b.mk("UnlitMaterial", {"emissiveColor": [1, 0.9, 0.7]}, parent=ap, name="Mat_Sun"); it = await b.mk("ImageTexture", {"url": ["../tex/sun.png"]}, parent=um, cf="emissiveTexture"); await b.mk("Sphere", {"radius": RS}, parent=sh)
    # ecliptic grid: circles every 0.5 AU and 12 spokes
    pts = []; idx = []
    for k in range(1, 6):
        base = len(pts); c = circle(AU * 0.5 * k, 192); pts += c; idx += list(range(base, base + len(c))) + [base, -1]
    for i in range(12):
        a = 2 * math.pi * i / 12; base = len(pts); pts += [[0, 0, 0], [AU * 2.5 * math.cos(a), 0, AU * 2.5 * math.sin(a)]]; idx += [base, base + 1, -1]
    await b.lines(w, [e3(p) for p in pts], idx, (0.07, 0.12, 0.22), name="EclipticGrid", tr=0.35)
    # Earth orbit ellipse (e = 0.0167, perihelion longitude 102.94 deg): same elements as engine.js
    e = 0.0167; wp = math.radians(102.94); pts = []
    for i in range(361):
        nu = 2 * math.pi * i / 360; r = AU * (1 - e * e) / (1 + e * math.cos(nu)); lam = wp + nu; pts.append([r * math.cos(lam), 0, -r * math.sin(lam)])
    await b.lines(w, [e3(p) for p in pts], list(range(361)) + [-1], (0.25, 0.5, 0.95), name="EarthOrbitLine")
    eo = await b.mk("Transform", parent=w, name="EarthOrbitT")
    es = await b.mk("Transform", parent=eo, name="EarthSpin"); sh = await b.mk("Shape", parent=es, name="EarthBody")
    await b.pbr(sh, base="earth_day.jpg", mr="earth_mr.png", emis_tex="earth_lights.png", emissive=(1.0, 0.8, 0.5), rough=1.0, metal=1.0, aniso=4, name="Ap_Earth"); await b.mk("Sphere", {"radius": RE}, parent=sh)
    ct = await b.mk("Transform", parent=es, name="CloudsT"); sh = await b.mk("Shape", parent=ct); await b.pbr(sh, base="earth_clouds.png", rough=1.0, metal=0.0, aniso=2); await b.mk("Sphere", {"radius": RE * 1.0045}, parent=sh)
    # graticule + axis in the body frame
    pts = []; idx = []
    for lat in (-60, -30, 0, 30, 60):
        base = len(pts); la = math.radians(lat); pts += [[RE * 1.002 * math.cos(la) * math.cos(2 * math.pi * i / 96), RE * 1.002 * math.sin(la), RE * 1.002 * math.cos(la) * math.sin(2 * math.pi * i / 96)] for i in range(96)]; idx += list(range(base, base + 96)) + [base, -1]
    for lon in range(0, 360, 30):
        base = len(pts); lo = math.radians(lon); pts += [[RE * 1.002 * math.cos(math.pi * (i / 48 - 1)) * math.cos(lo), RE * 1.002 * math.sin(math.pi * (i / 48 - 1)), RE * 1.002 * math.cos(math.pi * (i / 48 - 1)) * math.sin(lo)] for i in range(97)]; idx += list(range(base, base + 97)) + [-1]
    await b.lines(es, [e3(p) for p in pts], idx, (0.35, 0.55, 0.9), name="Graticule", tr=0.82)
    await b.lines(es, [[0, -RE * 1.9, 0], [0, RE * 1.9, 0]], [0, 1, -1], (0.9, 0.8, 0.3), name="EarthAxis")
    mk_ = await b.mk("Transform", {"translation": [0, 0, 0]}, parent=es, name="TownMarkerT")
    await b.emissive_shape(mk_, (1, 0.45, 0.15), "Sphere", {"radius": 4.0e4}, name="Mat_TownMarker")
    # Moon
    mo = await b.mk("Transform", parent=eo, name="MoonOrbitT"); ms = await b.mk("Transform", parent=mo, name="MoonSpin"); sh = await b.mk("Shape", parent=ms, name="MoonBody")
    await b.pbr(sh, base="moon.jpg", rough=0.96, metal=0.0, aniso=4, name="Ap_Moon"); await b.mk("Sphere", {"radius": RM}, parent=sh)
    mp = await b.mk("Transform", parent=eo, name="MoonOrbitPlane"); await b.lines(mp, [e3(p) for p in circle(3.844e8, 192)], list(range(192)) + [0, -1], (0.55, 0.6, 0.7), name="MoonOrbitLine", tr=0.25)
    return w

async def build_constellation(b: B, world: str):
    """364 ontology classes on a shell, three domain rings, the flywheel loop, evidence monoliths: the v1 modules at a much larger scale"""
    cs = await b.mk("Transform", parent=world, name="ConstSpin")
    await b.mk("DirectionalLight", {"direction": [-0.35, -0.5, -0.8], "intensity": 1.1, "color": [0.8, 0.88, 1.0]}, parent=cs, name="ConstFill")
    mats = await b.mk("Switch", {"whichChoice": -1}, name="Materials")
    for f in fams:
        sh = await b.mk("Shape", parent=mats); ap = await b.mk("Appearance", parent=sh, name="Fam_" + f)
        c = rgb(f); await b.mk("PhysicalMaterial", {"baseColor": c, "emissiveColor": [x * 0.5 for x in c], "roughness": 0.45, "metallic": 0.0}, parent=ap); await b.mk("Sphere", {"radius": 1.0}, parent=sh)
    sh = await b.mk("Shape", parent=mats); ap = await b.mk("Appearance", parent=sh, name="New41"); await b.mk("PhysicalMaterial", {"baseColor": [0.2, 1, 0.5], "emissiveColor": [0.3, 1, 0.55], "roughness": 0.4, "metallic": 0.0}, parent=ap); await b.mk("Sphere", {"radius": 1.0}, parent=sh)
    glass = await b.emissive_shape(cs, (0.04, 0.09, 0.22), "Sphere", {"radius": RC * 1.03}, tr=0.94)
    # lat/lon wires
    R = RC * 1.04; wires = []; n = 96; widx = []
    for k, lat_d in enumerate((-60, -30, 0, 30, 60)):
        la = math.radians(lat_d); base = len(wires); wires += [[R * math.cos(la) * math.cos(2 * math.pi * i / n), R * math.sin(la), R * math.cos(la) * math.sin(2 * math.pi * i / n)] for i in range(n)]; widx += list(range(base, base + n)) + [base, -1]
    for lon_d in range(0, 180, 30):
        lo = math.radians(lon_d); base = len(wires); wires += [[R * math.cos(math.pi * (i / n * 2 - 1)) * math.cos(lo), R * math.sin(math.pi * (i / n * 2 - 1)), R * math.cos(math.pi * (i / n * 2 - 1)) * math.sin(lo)] for i in range(n + 1)]; widx += list(range(base, base + n + 1)) + [-1]
    await b.lines(cs, [e3(p) for p in wires], widx, (0.1, 0.22, 0.5), name="ShellWires")
    cls = await b.mk("Group", parent=cs, name="Classes"); pos = {}; newT = []; picks = []
    for nd in D["nodes"]:
        p = [x * KS for x in sph(nd)]; pos[nd["id"]] = p; rad = min(0.38, 0.07 + 0.035 * math.sqrt(1 + nd["desc"])) * (1.6 if nd["new"] else 1) * KS
        f = {"translation": e3(p)}; tr = await b.mk("Transform", f, parent=cls, name=("C_" + nd["id"]) if nd["new"] else None); sh = await b.mk("Shape", parent=tr)
        await b.use(sh, "New41" if nd["new"] else "Fam_" + nd["fam"], "appearance")
        await b.mk("Box" if nd["kind"] == "abstract" else "Sphere", {"size": [rad * 1.6] * 3} if nd["kind"] == "abstract" else {"radius": e3([rad])[0]}, parent=sh)
        if nd["new"]: newT.append(tr)
        picks.append(dict(id=nd["id"], cat="class", frame=["ConstSpin"], p=e3(p), r=e3([rad * (0.95 if nd["kind"] != "abstract" else 1.0)])[0]))
    ids = [n_["id"] for n_ in D["nodes"]]; ix = {c: i for i, c in enumerate(ids)}
    hier = [v for n_ in D["nodes"] if n_["pp"] for v in (ix[n_["id"]], ix[n_["pp"]], -1)]
    await b.lines(cs, [e3(pos[c]) for c in ids], hier, (0.2, 0.26, 0.42), name="Hierarchy")
    shape = next(n_ for n_ in D["nodes"] if n_["id"] == "Shape"); sets = {"A": [], "R": [], "I": [], "-": []}
    for (d_, _), v in zip(shape["lp"], shape["lpv"]): sets[v].append(d_)
    for key, nm, col in (("A", "ShapeAccepts", [.3, 1, .55]), ("R", "ShapeRejects", [1, .35, .35]), ("I", "ShapeInconclusive", [1, .78, .3]), ("-", "ShapeAbstract", [.35, .8, 1])):
        pts_, idx = [], []
        for d_ in sets[key]:
            base = len(pts_); arc = [slerp(pos["Shape"], pos[d_], i / 12, 0.16, RC) for i in range(13)]; pts_ += arc; idx += list(range(base, base + 13)) + [-1]
        if idx: await b.lines(cs, [e3(p) for p in pts_], idx, col, name=nm)
    # pulse for the classes new in 4.1
    pc = await b.mk("TimeSensor", {"cycleInterval": 2.4, "loop": True}, name="Pulse"); pi = await b.mk("PositionInterpolator", {"key": [0, .5, 1], "keyValue": [[1, 1, 1], [1.7, 1.7, 1.7], [1, 1, 1]]}, name="PulseScale")
    await b.route(pc, "fraction_changed", pi, "set_fraction")
    for tr in newT: await b.route(pi, "value_changed", tr, "scale")
    # ---------------- domain rings (gyroscopes)
    cat_col = {"L0": [.7, .7, .65], "L1": [.55, .55, .5], "baseline": [.55, .55, .5], "L2": [.25, .55, 1], "khronos-error": [.25, .55, 1], "warn": [1, .65, .15], "khronos-warning": [1, .65, .15], "contact": [.95, .35, .2]}
    def verdict(v):
        for k in ("L0", "L1", "L2", "contact", "warn", "baseline", "khronos-error", "khronos-warning"):
            if v.get(k): return k
    v1rad = {"X3D": 6.6, "URDF": 6.0, "glTF": 5.4}
    rings = [("X3D", (1, 0, 0), .42, [(c[0], c[1], c[6]) for c in COMP]), ("URDF", (0, 0, 1), -.55, [(f, v["n"], verdict(v)) for f, v in UR["faults"].items()]), ("glTF", (.707, 0, .707), 1.0, [(f, v["n"], "L0" if f == "G25" else verdict(v)) for f, v in GL["faults"].items()])]
    spins = {}
    for dom, axis, ang, items in rings:
        k = RING[dom] / v1rad[dom]; tilt = await b.mk("Transform", {"rotation": [axis[0], axis[1], axis[2], ang]}, parent=cs, name=f"Tilt_{dom}"); spin = await b.mk("Transform", parent=tilt, name=f"Spin_{dom}"); spins[dom] = spin
        await b.lines(spin, [e3(p) for p in circle(RING[dom], 192)], list(range(192)) + [0, -1], (0.3, 0.34, 0.5), name=f"RingLine_{dom}")
        for i, (nm, size, v) in enumerate(items):
            ph = 2 * math.pi * i / len(items); p = [v1rad[dom] * k * math.cos(ph), 0, v1rad[dom] * k * math.sin(ph)]
            if dom == "X3D": col = list(colorsys.hls_to_rgb(0.33 * (v if v is not None else .5), .55, .8)); r_ = (.1 + .018 * math.sqrt(size) * 2) * k
            else: col = cat_col[v]; r_ = (.1 + .035 * math.sqrt(size)) * k
            tr = await b.mk("Transform", {"translation": e3(p)}, parent=spin); sh = await b.mk("Shape", parent=tr); ap = await b.mk("Appearance", parent=sh)
            await b.mk("PhysicalMaterial", {"baseColor": col, "emissiveColor": [c * .7 for c in col], "roughness": 0.4, "metallic": 0.0}, parent=ap, name=f"BeadM_{dom}_{i}"); await b.mk("Sphere", {"radius": e3([r_])[0]}, parent=sh)
            picks.append(dict(id=f"{dom}_{i}", cat="bead", dom=dom, idx=i, frame=["ConstSpin", f"Tilt_{dom}", f"Spin_{dom}"], p=e3(p), r=e3([r_])[0]))
    rc = await b.mk("TimeSensor", {"cycleInterval": 240, "loop": True}, name="RingClock")
    for dom, mult in (("X3D", 1), ("URDF", -2), ("glTF", 3)):
        ks_ = [i / 24 for i in range(25)]; vals = [[0, 1, 0, round(2 * math.pi * mult * i / 24, 5)] for i in range(25)]
        ri = await b.mk("OrientationInterpolator", {"key": ks_, "keyValue": vals}, name=f"Spin_{dom}_I"); await b.route(rc, "fraction_changed", ri, "set_fraction"); await b.route(ri, "value_changed", spins[dom], "rotation")
    # constellation turns slowly (one revolution per 20 minutes)
    cc = await b.mk("TimeSensor", {"cycleInterval": 1200, "loop": True}, name="ConstClock"); co = await b.mk("OrientationInterpolator", {"key": [i / 12 for i in range(13)], "keyValue": [[0, 1, 0, round(2 * math.pi * i / 12, 5)] for i in range(13)]}, name="ConstSpin_I")
    await b.route(cc, "fraction_changed", co, "set_fraction"); await b.route(co, "value_changed", cs, "rotation")
    # ---------------- the flywheel loop ring
    STATIONS = [("spec", [1, 1, 1]), ("agent", [.35, .6, 1]), ("x3d_mcp", [1, .35, .3]), ("Blender + fork", [1, .6, .2]), ("runtime", [.4, 1, .6]), ("verdict", [.7, .5, 1]), ("tether", [1, .85, .3])]
    kB = LOOP_R / 5.5; loopT = await b.mk("Transform", {"rotation": [1, 0, 0, -0.32]}, parent=cs, name="LoopTilt"); loop = await b.mk("Transform", parent=loopT, name="LoopRing")
    await b.lines(loop, [e3(p) for p in circle(LOOP_R, 192)], list(range(192)) + [0, -1], (0.45, 0.5, 0.65), name="LoopLine"); stT = []
    for k_, (nm, col) in enumerate(STATIONS):
        ph = 2 * math.pi * k_ / 7; p = [5.5 * kB * math.cos(ph), 0, -5.5 * kB * math.sin(ph)]
        tr = await b.mk("Transform", {"translation": e3(p)}, parent=loop, name=f"St_{k_}"); await b.emissive_shape(tr, [c * .8 for c in col], "Sphere", {"radius": e3([0.5 * kB])[0]}); stT.append(tr)
        picks.append(dict(id=f"St_{k_}", cat="station", idx=k_, frame=["ConstSpin", "LoopTilt", "LoopRing"], p=e3(p), r=e3([0.5 * kB])[0]))
    orbit = await b.mk("Transform", parent=loop, name="PacketOrbit"); pk = await b.mk("Transform", {"translation": [e3([5.5 * kB])[0], 0, 0]}, parent=orbit)
    pks = await b.mk("Shape", parent=pk); ap = await b.mk("Appearance", parent=pks); pmat = await b.mk("Material", {"diffuseColor": [1, 1, 1], "emissiveColor": [1, 1, 1]}, parent=ap, name="PacketMat"); await b.mk("Sphere", {"radius": e3([0.32 * kB])[0]}, parent=pks)
    trails = []
    for tk in range(1, 6):
        to = await b.mk("Transform", parent=loop, name=f"TrailOrbit{tk}"); ti = await b.mk("Transform", {"rotation": [0, 1, 0, -0.11 * tk]}, parent=to); tp = await b.mk("Transform", {"translation": [e3([5.5 * kB])[0], 0, 0]}, parent=ti)
        await b.emissive_shape(tp, [.5 / tk + .1, .6 / tk + .1, .9 / tk + .1], "Sphere", {"radius": e3([(0.30 - 0.04 * tk) * kB])[0]}, tr=min(.85, .25 + .13 * tk)); trails.append(to)
    rorb = await b.mk("Transform", {"scale": [0, 0, 0]}, parent=loop, name="ReportOrbit"); rp = await b.mk("Transform", {"translation": [e3([5.5 * kB * .8])[0], 0, 0]}, parent=rorb)
    await b.emissive_shape(rp, [1, .75, .2], "Sphere", {"radius": e3([0.2 * kB])[0]})
    lap = await b.mk("TimeSensor", {"cycleInterval": 40, "loop": True}, name="Lap"); ks = [0, 1/7, 2/7, 2.35/7, 2.7/7, 3/7, 4/7, 5/7, 6/7, 1]
    cv = [[1, 1, 1], [.35, .6, 1], [1, .2, .2], [1, .75, .2], [.3, 1, .45], [.3, 1, .45], [.3, 1, .45], [.7, .5, 1], [1, .85, .3], [1, 1, 1]]
    ci = await b.mk("ColorInterpolator", {"key": ks, "keyValue": cv}, name="PacketColor"); await b.route(lap, "fraction_changed", ci, "set_fraction"); await b.route(ci, "value_changed", pmat, "emissiveColor")
    oi = await b.mk("OrientationInterpolator", {"key": [0, .25, .5, .75, 1], "keyValue": [[0, 1, 0, 0], [0, 1, 0, math.pi / 2], [0, 1, 0, math.pi], [0, 1, 0, 3 * math.pi / 2], [0, 1, 0, 2 * math.pi]]}, name="PacketRot")
    await b.route(lap, "fraction_changed", oi, "set_fraction"); await b.route(oi, "value_changed", orbit, "rotation")
    for to in trails: await b.route(oi, "value_changed", to, "rotation")
    si = await b.mk("PositionInterpolator", {"key": [0, 2/7, 2/7 + .001, 2.4/7, 2.4/7 + .001, 1], "keyValue": [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1], [0, 0, 0], [0, 0, 0]]}, name="ReportScale")
    await b.route(lap, "fraction_changed", si, "set_fraction"); await b.route(si, "value_changed", rorb, "scale")
    ro = await b.mk("OrientationInterpolator", {"key": [0, 2/7, 2.4/7, 1], "keyValue": [[0, 1, 0, 4 * math.pi / 7], [0, 1, 0, 4 * math.pi / 7], [0, 1, 0, 2 * math.pi / 7], [0, 1, 0, 2 * math.pi / 7]]}, name="ReportRot")
    await b.route(lap, "fraction_changed", ro, "set_fraction"); await b.route(ro, "value_changed", rorb, "rotation")
    for k_ in (2, 6):
        sc = await b.mk("PositionInterpolator", {"key": [0, (k_ - .15) / 7, k_ / 7, (k_ + .3) / 7, 1], "keyValue": [[1, 1, 1], [1, 1, 1], [1.8, 1.8, 1.8], [1, 1, 1], [1, 1, 1]]}, name=f"StationPulse{k_}")
        await b.route(lap, "fraction_changed", sc, "set_fraction"); await b.route(sc, "value_changed", stT[k_], "scale")
    # ---------------- evidence monoliths on the ecliptic plane
    pillars = await b.mk("Transform", {"translation": [e3([PILLAR_R * math.cos(math.radians(205))])[0], 0, e3([PILLAR_R * math.sin(math.radians(205))])[0]]}, parent=cs, name="Pillars")
    for xi, dom in enumerate(("X3D", "URDF", "glTF")):
        ev = TOUR["pillars"].get(dom)
        for j, (nm, hh, col) in enumerate((("first try", (ev["a0"] / 100 if ev else .5), [.35, .6, 1]), ("report loop", (ev["a2"] / 100 if ev else .8), [.3, 1, .5]))):
            hgt = max(.05, 2.2 * hh) * 2.4e10; x = (xi * 3.0 + (j - .5) * 1.05) * 1.9e10; pl = await b.mk("Transform", {"translation": e3([x, hgt / 2, 0])}, parent=pillars)
            sh = await b.emissive_shape(pl, [c * (.8 if ev else .35) for c in col], "Cylinder", {"radius": 0.34e10 * 2.4, "height": e3([hgt])[0]}, tr=0.0 if ev else 0.55)
            ox, oz = PILLAR_R * math.cos(math.radians(205)), PILLAR_R * math.sin(math.radians(205))
            picks.append(dict(id=f"P_{dom}_{j}", cat="pillar", dom=dom, idx=j, frame=["ConstSpin"], p=e3([x + ox, hgt / 2, oz]), r=e3([hgt * 0.5])[0]))
    return picks, pos
