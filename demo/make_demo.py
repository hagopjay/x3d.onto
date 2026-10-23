#!/usr/bin/env python3
"""Ontology Dyson sphere demo (see DEMO-SPEC.md). Authored ONLY through x3d_mcp's granular tools (stdio MCP client); head and profile are patched in afterwards.
usage: ~/Projects/x3d/x3d_mcp/.venv/bin/python make_demo.py [x3d_mcp checkout]  -> scenes/ontology-dyson.x3d, ../out/demo_run.json"""
import asyncio, colorsys, datetime, hashlib, json, math, os, random, re, statistics, subprocess, sys, time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
REPO = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Projects/x3d/x3d_mcp")
D = json.loads((ROOT / "data" / "explorer.json").read_text()); MAN = json.loads((ROOT / "data" / "manifest.ontology41.json").read_text())
COMP = json.loads((ROOT / "data" / "components.json").read_text())           # [name, nodes, new, A, R, I, accepted_share, uom_agreement]
UR = json.loads((ROOT / "out" / "xdomain_urdf.json").read_text()); GL = json.loads((ROOT / "out" / "xdomain_gltf.json").read_text())
txt = lambda r: "".join(getattr(c, "text", "") for c in r.content)
R = 8.0; MAXD = D["stats"]["max_depth"]
fams = sorted(D["families"], key=lambda f: -D["families"][f])
def rgb(f): return [round(v, 3) for v in colorsys.hls_to_rgb((fams.index(f) * 137.5 % 360) / 360, .62, .7)]
def sph(n):
    lon = n["a"]; lat = math.radians(70 - n["d"] * 140 / MAXD)
    return [round(R * math.cos(lat) * math.cos(lon), 3), round(R * math.sin(lat), 3), round(R * math.cos(lat) * math.sin(lon), 3)]
def slerp(a, b, t, lift):
    ra = math.sqrt(sum(x * x for x in a)); rb = math.sqrt(sum(x * x for x in b)); ua = [x / ra for x in a]; ub = [x / rb for x in b]
    dot = max(-1, min(1, sum(x * y for x, y in zip(ua, ub)))); om = math.acos(dot)
    if om < 1e-6: return a
    s = [(math.sin((1 - t) * om) * x + math.sin(t * om) * y) / math.sin(om) for x, y in zip(ua, ub)]
    r = R * (1 + lift * math.sin(math.pi * t)); return [round(r * x, 3) for x in s]
def qmul(a, b): return (a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3], a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2], a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1], a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0])
def aa(axis, ang): s = math.sin(ang / 2); return (math.cos(ang / 2), axis[0] * s, axis[1] * s, axis[2] * s)
def toaa(q):
    w = max(-1, min(1, q[0])); ang = 2 * math.acos(w); s = math.sqrt(max(1e-12, 1 - w * w)); return [round(q[1] / s, 5), round(q[2] / s, 5), round(q[3] / s, 5), round(ang, 5)] if ang > 1e-6 else [0, 1, 0, 0]
def look(pos, target=(0, 0, 0)):
    """camera orientation (axis-angle) for a viewpoint at pos looking at target: yaw about Y, then pitch about X"""
    dx, dy, dz = [t - p for t, p in zip(target, pos)]; yaw = math.atan2(-dx, -dz); pitch = math.atan2(dy, math.hypot(dx, dz))
    return toaa(qmul(aa((0, 1, 0), yaw), aa((1, 0, 0), pitch)))
XT = set(D["xcheck"]["table"]); STATIONS = [("spec", [1, 1, 1]), ("agent", [.35, .6, 1]), ("x3d_mcp", [1, .35, .3]), ("Blender + fork", [1, .6, .2]), ("runtime", [.4, 1, .6]), ("verdict", [.7, .5, 1]), ("tether", [1, .85, .3])]
def eval_rates(dom):
    p = ROOT / "xdomain" / "eval-plan" / "runs" / f"{dom}-gemini-3.8-flash.jsonl"
    if not p.exists(): return None
    rows = [json.loads(l) for l in p.read_text().splitlines()]; a0 = [r for r in rows if r["arm"] == "A0"]; a2 = [r for r in rows if r["arm"] == "A2-final"]; dt = [r for r in rows if r["arm"] == "A0+det"]
    if len(a0) < 30 or not a2: return None
    f = lambda rr: sum(r["valid"] for r in rr) / len(rr)
    return dict(a0=f(a0), a2=f(a2), det=f(dt) if dt else None, n=len(a0))
try: git = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception: git = "?"

async def main():
    params = StdioServerParameters(command=os.path.join(REPO, ".venv/bin/python"), args=["-m", "src.server"], cwd=REPO)
    lat = []; calls = {}
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); await s.call_tool("reset_scene", {})
            async def call(name, args):
                t0 = time.perf_counter(); t = txt(await s.call_tool(name, args)); lat.append((time.perf_counter() - t0) * 1000); calls[name] = calls.get(name, 0) + 1
                if t.startswith("Error") or "Error executing" in t: raise SystemExit(f"{name} {json.dumps(args)[:200]} -> {t[:300]}")
                return t
            async def mk(nt, fields=None, parent=None, cf="", name=None):
                t = await call("create_node", {"node_type": nt, "fields": fields or {}}); nid = re.search(r"ID: (\S+)", t).group(1)
                if parent: await call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf})
                if name: await call("def_node", {"node_id": nid, "name": name})
                return nid
            async def use(parent, def_name, cf):
                t = await call("use_node", {"def_name": def_name}); nid = re.search(r"ID: (\S+)", t).group(1)
                await call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf}); return nid
            route = lambda a, fa, b, fb: call("add_route", {"from_node": a, "from_field": fa, "to_node": b, "to_field": fb})
            async def emissive(parent, col, tr=0.0, diffuse=None):
                sh = await mk("Shape", parent=parent); ap = await mk("Appearance", parent=sh)
                m = {"diffuseColor": diffuse or [0, 0, 0], "emissiveColor": col}
                if tr: m["transparency"] = tr
                await mk("Material", m, parent=ap); return sh
            async def label(parent, text, at, size=0.5, col=(1, 1, 1), name=None):
                tr = await mk("Transform", {"translation": list(at)}, parent=parent); bb = await mk("Billboard", {"axisOfRotation": [0, 0, 0]}, parent=tr)
                sh = await emissive(bb, list(col)); tx = await mk("Text", {"string": text if isinstance(text, list) else [text]}, parent=sh)
                await mk("FontStyle", {"family": ["SANS"], "size": size, "justify": ["MIDDLE"], "spacing": 1.2}, parent=tx); return tr
            async def circle(parent, rad, col, n=96):
                pts = [[round(rad * math.cos(2 * math.pi * i / n), 3), 0, round(rad * math.sin(2 * math.pi * i / n), 3)] for i in range(n)]
                sh = await emissive(parent, col); ils = await mk("IndexedLineSet", {"coordIndex": list(range(n)) + [0, -1]}, parent=sh); await mk("Coordinate", {"point": pts}, parent=ils, cf="coord")
            t_build = time.perf_counter()
            # ---------------- environment
            await mk("NavigationInfo", {"type": ["EXAMINE", "ANY"], "headlight": False, "speed": 6, "visibilityLimit": 400})
            await mk("Background", {"skyColor": [[0.01, 0.015, 0.035]]})
            await mk("DirectionalLight", {"direction": [-0.3, -0.6, -0.5], "intensity": 0.35, "color": [0.7, 0.8, 1]})
            vp = [("Row", (0, 12, 78)), ("Shell", (0, 9, 30)), ("Flywheel", (-26, 22, 34)), ("Domains", (26, 20, 40)), ("Fly", (0, 12, 78)), ("FlyBack", (0, 8, 34)), ("Orbit", (0, 8, 34)), ("Film", (0, 16, 100)), ("Tour", (0, 12, 78))]
            vids = {}
            for nm, p in vp:
                tgt = {"Shell": (0, 0, 0), "Flywheel": (-26, 0, 0), "Domains": (26, 0, 0), "FlyBack": (0, 0, 0), "Orbit": (0, 0, 0), "Fly": (0, 0, 0), "Row": (0, 0, 0), "Film": (0, 0, 0), "Tour": (0, 0, 0)}[nm]
                vids[nm] = await mk("Viewpoint", {"position": list(p), "orientation": look(p, tgt), "fieldOfView": 0.8, "description": nm}, name=nm)
            # stars
            rnd = random.Random(11); pts = []; cols = []
            for _ in range(900):
                z = rnd.uniform(-1, 1); a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(110, 170); q = math.sqrt(1 - z * z)
                pts.append([round(rr * q * math.cos(a), 1), round(rr * z, 1), round(rr * q * math.sin(a), 1)]); b = rnd.uniform(.4, 1); cols.append([round(b, 2), round(b, 2), round(min(1, b + .2), 2)])
            st = await mk("Shape", name="Stars"); ap = await mk("Appearance", parent=st); await mk("Material", {"emissiveColor": [1, 1, 1], "diffuseColor": [0, 0, 0]}, parent=ap)
            ps = await mk("PointSet", parent=st); await mk("Coordinate", {"point": pts}, parent=ps, cf="coord"); await mk("Color", {"color": cols}, parent=ps, cf="color")
            # shared appearances
            mats = await mk("Group", name="Materials")
            for f in fams:
                sh = await mk("Shape", parent=mats); ap = await mk("Appearance", parent=sh, name="Fam_" + f)
                await mk("Material", {"diffuseColor": rgb(f), "emissiveColor": [c * .45 for c in rgb(f)], "specularColor": [.3, .3, .3]}, parent=ap); await mk("Sphere", {"radius": 0.001}, parent=sh)
            shn = await mk("Shape", parent=mats); apn = await mk("Appearance", parent=shn, name="New41")
            await mk("Material", {"diffuseColor": [.2, 1, .5], "emissiveColor": [.3, 1, .55]}, parent=apn); await mk("Sphere", {"radius": 0.001}, parent=shn)
            # ---------------- module A: the shell
            modA = await mk("Transform", {"translation": [0, 0, 0]}, name="ModA")
            sunT = await mk("Transform", name="SunT", parent=modA); heart = await mk("Transform", name="Heart", parent=sunT); star = await emissive(heart, [1, .78, .3], diffuse=[1, .8, .3]); await mk("Sphere", {"radius": 0.7}, parent=star)
            await mk("PointLight", {"location": [0, 0, 0], "intensity": 1.3, "radius": 60, "color": [1, .9, .7]}, parent=modA)
            glass = await emissive(modA, [.05, .12, .3], tr=0.92, diffuse=[.3, .5, 1]); await mk("Sphere", {"radius": R + 0.35}, parent=glass)
            wires = []; n = 64
            for lat_d in (-60, -30, 0, 30, 60):
                la = math.radians(lat_d); base = len(wires); wires += [[round((R + .4) * math.cos(la) * math.cos(2 * math.pi * i / n), 3), round((R + .4) * math.sin(la), 3), round((R + .4) * math.cos(la) * math.sin(2 * math.pi * i / n), 3)] for i in range(n)]
            widx = []
            for k in range(5): widx += list(range(k * n, (k + 1) * n)) + [k * n, -1]
            for lon_d in range(0, 180, 30):
                lo = math.radians(lon_d); base = len(wires)
                wires += [[round((R + .4) * math.cos(math.pi * (i / n * 2 - 1) / 1) * math.cos(lo), 3), round((R + .4) * math.sin(math.pi * (i / n * 2 - 1)), 3), round((R + .4) * math.cos(math.pi * (i / n * 2 - 1)) * math.sin(lo), 3)] for i in range(n + 1)]
                widx += list(range(base, base + n + 1)) + [-1]
            wsh = await emissive(modA, [.12, .25, .5]); wl = await mk("IndexedLineSet", {"coordIndex": widx}, parent=wsh, name="ShellWires"); await mk("Coordinate", {"point": wires}, parent=wl, cf="coord")
            cls = await mk("Group", parent=modA, name="Classes"); pos = {}; newT = []
            for nd in D["nodes"]:
                p = sph(nd); pos[nd["id"]] = p; rad = round(min(0.38, 0.07 + 0.035 * math.sqrt(1 + nd["desc"])) * (1.6 if nd["new"] else 1), 3)
                tr = await mk("Transform", {"translation": p}, parent=cls, name="C_" + nd["id"]); sh = await mk("Shape", parent=tr)
                await use(sh, "New41" if nd["new"] else "Fam_" + nd["fam"], "appearance")
                await mk("Box" if nd["kind"] == "abstract" else "Sphere", {"size": [rad * 1.6] * 3} if nd["kind"] == "abstract" else {"radius": rad}, parent=sh)
                await mk("TouchSensor", parent=tr, name="T_" + nd["id"])
                if nd["new"]: newT.append(tr)
            lab = await mk("Group", parent=modA, name="ClassLabels")
            for nd in D["nodes"]:
                if (nd["d"] == 0 and nd["desc"] >= 3) or nd["id"] in XT or nd["new"]:
                    p = pos[nd["id"]]; await label(lab, nd["id"], [p[0] * 1.07, p[1] * 1.07 + .3, p[2] * 1.07], .36, (.3, 1, .5) if nd["new"] else ((.5, 1, .7) if nd["id"] in XT else (1, 1, 1)))
            ids = [n_["id"] for n_ in D["nodes"]]; ix = {c: i for i, c in enumerate(ids)}
            hier = [v for n_ in D["nodes"] if n_["pp"] for v in (ix[n_["id"]], ix[n_["pp"]], -1)]
            sh = await emissive(modA, [.2, .26, .42]); ils = await mk("IndexedLineSet", {"coordIndex": hier}, parent=sh); await mk("Coordinate", {"point": [pos[c] for c in ids]}, parent=ils, cf="coord")
            shape = next(n_ for n_ in D["nodes"] if n_["id"] == "Shape"); sets = {"A": [], "R": [], "I": [], "-": []}
            for (d_, _), v in zip(shape["lp"], shape["lpv"]): sets[v].append(d_)
            for key, nm, col in (("A", "ShapeAccepts", [.3, 1, .55]), ("R", "ShapeRejects", [1, .35, .35]), ("I", "ShapeInconclusive", [1, .78, .3]), ("-", "ShapeAbstract", [.35, .8, 1])):
                pts_, idx = [], []
                for d_ in sets[key]:
                    base = len(pts_); arc = [slerp(pos["Shape"], pos[d_], i / 12, 0.16) for i in range(13)]; pts_ += arc; idx += list(range(base, base + 13)) + [-1]
                if not idx: continue
                sh = await emissive(modA, col); ils = await mk("IndexedLineSet", {"coordIndex": idx}, parent=sh, name=nm); await mk("Coordinate", {"point": pts_}, parent=ils, cf="coord")
            await label(modA, "ONTOLOGY  364 classes, 4.1", [0, R + 2.4, 0], .7, (.8, .9, 1))
            # ---------------- module B: the flywheel ring
            modB = await mk("Transform", {"translation": [-26, 0, 0], "scale": [2.2, 2.2, 2.2]}, name="ModB"); RB = 5.5
            await circle(modB, RB, [.45, .5, .65]); await circle(modB, RB * .55, [.2, .22, .3], 64)
            stT = []
            for k, (nm, col) in enumerate(STATIONS):
                ph = 2 * math.pi * k / 7; p = [round(RB * math.cos(ph), 3), 0, round(-RB * math.sin(ph), 3)]
                tr = await mk("Transform", {"translation": p}, parent=modB, name=f"St_{k}"); sh = await emissive(tr, [c * .8 for c in col], diffuse=col); await mk("Sphere", {"radius": 0.5}, parent=sh); await mk("TouchSensor", parent=tr, name=f"T_St_{k}")
                await label(tr, nm, [0, 1.15, 0], .5, col); stT.append(tr)
            orbit = await mk("Transform", parent=modB, name="PacketOrbit"); pk = await mk("Transform", {"translation": [RB, 0, 0]}, parent=orbit)
            pks = await mk("Shape", parent=pk); ap = await mk("Appearance", parent=pks); pmat = await mk("Material", {"diffuseColor": [1, 1, 1], "emissiveColor": [1, 1, 1]}, parent=ap, name="PacketMat"); await mk("Sphere", {"radius": 0.32}, parent=pks)
            trails = []
            for tk in range(1, 6):
                to = await mk("Transform", parent=modB, name=f"TrailOrbit{tk}"); ti = await mk("Transform", {"rotation": [0, 1, 0, -0.11 * tk]}, parent=to); tp = await mk("Transform", {"translation": [RB, 0, 0]}, parent=ti)
                ts_ = await emissive(tp, [.5 / tk + .1, .6 / tk + .1, .9 / tk + .1], tr=min(.85, .25 + .13 * tk)); await mk("Sphere", {"radius": round(.30 - .04 * tk, 3)}, parent=ts_); trails.append(to)
            rorb = await mk("Transform", {"scale": [0, 0, 0]}, parent=modB, name="ReportOrbit"); rp = await mk("Transform", {"translation": [RB * .8, 0, 0]}, parent=rorb)
            rps = await emissive(rp, [1, .75, .2], diffuse=[1, .75, .2]); await mk("Sphere", {"radius": 0.2}, parent=rps)
            capB = ["MEASURED (C):", "validate 166 KB scene: 1.8 s", "tool call median: 1.9 ms", "first try 27.3% to 56.7% (E1, doc)", "after report loop: about 100%", "provenance kept 6 of 6 via Blender"]
            capBT = await mk("Transform", parent=modB, name="CapB"); await label(capBT, capB, [0, 4.2, 0], .38, (.75, .85, 1))
            await label(modB, "THE LOOP", [0, -2.6, 0], .6, (.8, .9, 1))
            # packet clock and interpolators
            lap = await mk("TimeSensor", {"cycleInterval": 14, "loop": True}, name="Lap")
            ks = [0, 1/7, 2/7, 2.35/7, 2.7/7, 3/7, 4/7, 5/7, 6/7, 1]
            cv = [[1, 1, 1], [.35, .6, 1], [1, .2, .2], [1, .75, .2], [.3, 1, .45], [.3, 1, .45], [.3, 1, .45], [.7, .5, 1], [1, .85, .3], [1, 1, 1]]
            ci = await mk("ColorInterpolator", {"key": ks, "keyValue": cv}, name="PacketColor"); await route(lap, "fraction_changed", ci, "set_fraction"); await route(ci, "value_changed", pmat, "emissiveColor")
            oi = await mk("OrientationInterpolator", {"key": [0, .25, .5, .75, 1], "keyValue": [[0, 1, 0, 0], [0, 1, 0, math.pi / 2], [0, 1, 0, math.pi], [0, 1, 0, 3 * math.pi / 2], [0, 1, 0, 2 * math.pi]]}, name="PacketRot")
            await route(lap, "fraction_changed", oi, "set_fraction"); await route(oi, "value_changed", orbit, "rotation")
            for to in trails: await route(oi, "value_changed", to, "rotation")
            si = await mk("PositionInterpolator", {"key": [0, 2/7, 2/7 + .001, 2.4/7, 2.4/7 + .001, 1], "keyValue": [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1], [0, 0, 0], [0, 0, 0]]}, name="ReportScale")
            await route(lap, "fraction_changed", si, "set_fraction"); await route(si, "value_changed", rorb, "scale")
            ro = await mk("OrientationInterpolator", {"key": [0, 2/7, 2.4/7, 1], "keyValue": [[0, 1, 0, 4 * math.pi / 7], [0, 1, 0, 4 * math.pi / 7], [0, 1, 0, 2 * math.pi / 7], [0, 1, 0, 2 * math.pi / 7]]}, name="ReportRot")
            await route(lap, "fraction_changed", ro, "set_fraction"); await route(ro, "value_changed", rorb, "rotation")
            for k in (2, 6):
                sc = await mk("PositionInterpolator", {"key": [0, (k - .15) / 7, k / 7, (k + .3) / 7, 1], "keyValue": [[1, 1, 1], [1, 1, 1], [1.8, 1.8, 1.8], [1, 1, 1], [1, 1, 1]]}, name=f"StationPulse{k}")
                await route(lap, "fraction_changed", sc, "set_fraction"); await route(sc, "value_changed", stT[k], "scale")
            # ---------------- module C: three domain rings
            modC = await mk("Transform", {"translation": [26, 0, 0], "scale": [2.2, 2.2, 2.2]}, name="ModC")
            cat_col = {"L0": [.7, .7, .65], "L1": [.55, .55, .5], "baseline": [.55, .55, .5], "L2": [.25, .55, 1], "khronos-error": [.25, .55, 1], "warn": [1, .65, .15], "khronos-warning": [1, .65, .15], "contact": [.95, .35, .2]}
            def verdict(v):
                for k in ("L0", "L1", "L2", "contact", "warn", "baseline", "khronos-error", "khronos-warning"):
                    if v.get(k): return k
            rings = [("X3D", 6.6, (1, 0, 0), .42, [(c[0], c[1], c[6]) for c in COMP], "components"), ("URDF", 6.0, (0, 0, 1), -.55, [(f, v["n"], verdict(v)) for f, v in UR["faults"].items()], "faults"), ("glTF", 5.4, (.707, 0, .707), 1.0, [(f, v["n"], "L0" if f == "G25" else verdict(v)) for f, v in GL["faults"].items()], "faults")]
            summary = {}; spins = {}
            for dom, rad, axis, ang, items, kind in rings:
                spin = await mk("Transform", parent=modC, name=f"Spin_{dom}"); spins[dom] = spin; rt = await mk("Transform", {"rotation": [axis[0], axis[1], axis[2], ang]}, parent=spin, name=f"Ring_{dom}"); await circle(rt, rad, [.3, .34, .5])
                for i, (nm, size, v) in enumerate(items):
                    ph = 2 * math.pi * i / len(items); p = [round(rad * math.cos(ph), 3), 0, round(rad * math.sin(ph), 3)]
                    if dom == "X3D": col = list(colorsys.hls_to_rgb(0.33 * (v if v is not None else .5), .55, .8)); r_ = round(.1 + .018 * math.sqrt(size) * 2, 3)
                    else: col = cat_col[v]; r_ = round(.1 + .035 * math.sqrt(size), 3)
                    tr = await mk("Transform", {"translation": p}, parent=rt); sh = await emissive(tr, [c * .7 for c in col], diffuse=col); await mk("Sphere", {"radius": r_}, parent=sh); await mk("TouchSensor", parent=tr, name=f"T_{dom}_{i}")
                summary[dom] = eval_rates({"X3D": "x3d", "URDF": "urdf", "glTF": "gltf"}[dom])
            for xi, dom in enumerate(("X3D", "URDF", "glTF")):
                ev = summary[dom]; g = await mk("Transform", {"translation": [(xi - 1) * 6.5, -5.8, 0]}, parent=modC)
                for j, (nm, hh, col) in enumerate((("first try", (ev["a0"] if ev else .5), [.35, .6, 1]), ("report loop", (ev["a2"] if ev else .8), [.3, 1, .5]))):
                    hgt = max(.05, 2.2 * hh); pl = await mk("Transform", {"translation": [(j - .5) * .9, hgt / 2, 0]}, parent=g)
                    sh = await emissive(pl, [c * (.8 if ev else .35) for c in col], tr=0.0 if ev else 0.55, diffuse=col); await mk("Cylinder", {"radius": .3, "height": hgt}, parent=sh); await mk("TouchSensor", parent=pl, name=f"T_P_{dom}_{j}")
                await label(g, ([dom, f"first try {ev['a0']:.0%}  loop {ev['a2']:.0%}", f"Gemini flash, n={ev['n']}"] if ev else [dom, "model eval running", "(ghost pillars)"]), [0, -1.1, 0], .36, (.8, .85, 1))
            rc = await mk("TimeSensor", {"cycleInterval": 90, "loop": True}, name="RingClock")
            for dom, mult in (("X3D", 1), ("URDF", -2), ("glTF", 3)):
                ks_ = [i / 24 for i in range(25)]; vals = [[0, 1, 0, round(2 * math.pi * mult * i / 24, 5)] for i in range(25)]
                if abs(mult) == 3: vals = [[0, 1, 0, round(2 * math.pi * 3 * i / 24, 5)] for i in range(25)]
                ri = await mk("OrientationInterpolator", {"key": ks_, "keyValue": vals}, name=f"Spin_{dom}_I"); await route(rc, "fraction_changed", ri, "set_fraction"); await route(ri, "value_changed", spins[dom], "rotation")
            capCT = await mk("Transform", parent=modC, name="CapC"); await label(capCT, ["X3D: 37 components, bead = XSD-accepted share", "URDF: 24 fault operators (L), bead = who catches", "glTF: 25 fault operators (C), bead = who catches"], [0, 8.6, 0], .38, (.85, .9, 1))
            await label(modC, "THREE DOMAINS", [0, -9.4, 0], .7, (.8, .9, 1))
            # ---------------- assemble / disassemble
            clocks = {}; assem = []
            async def clock(name): return await mk("TimeSensor", {"cycleInterval": 16, "loop": False}, name=name)
            for cname, rev in (("AssembleClock", False), ("DisassembleClock", True)):
                ck = await clock(cname); clocks[cname] = ck
                bpos, bscale = ([[-26, 0, 0], [0, 0, 0]], [[2.2] * 3, [1, 1, 1]]) if not rev else ([[0, 0, 0], [-26, 0, 0]], [[1, 1, 1], [2.2] * 3])
                cpos, cscale = ([[26, 0, 0], [0, 0, 0]], [[2.2] * 3, [1, 1, 1]]) if not rev else ([[0, 0, 0], [26, 0, 0]], [[1, 1, 1], [2.2] * 3])
                for nm, tgt, field, key, val in ((f"{cname}_Bp", modB, "translation", [0, .12, .8, 1], [bpos[0], bpos[0], bpos[1], bpos[1]]), (f"{cname}_Bs", modB, "scale", [0, .12, .8, 1], [bscale[0], bscale[0], bscale[1], bscale[1]]),
                                                    (f"{cname}_Cp", modC, "translation", [0, .12, .8, 1], [cpos[0], cpos[0], cpos[1], cpos[1]]), (f"{cname}_Cs", modC, "scale", [0, .12, .8, 1], [cscale[0], cscale[0], cscale[1], cscale[1]])):
                    pi = await mk("PositionInterpolator", {"key": key, "keyValue": val}, name=nm); await route(ck, "fraction_changed", pi, "set_fraction"); await route(pi, "value_changed", tgt, field); (assem.append(pi) if not rev else None)
                flare = await mk("PositionInterpolator", {"key": [0, .7, .8, .9, 1], "keyValue": [[1, 1, 1], [1, 1, 1], [3, 3, 3], [1.2, 1.2, 1.2], [1, 1, 1]] if not rev else [[1, 1, 1]] * 5}, name=f"{cname}_Flare"); await route(ck, "fraction_changed", flare, "set_fraction"); await route(flare, "value_changed", sunT, "scale"); (assem.append(flare) if not rev else None)
                fade = [[1, 1, 1], [1, 1, 1], [0, 0, 0], [0, 0, 0]] if not rev else [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1]]
                for tg, nm2 in ((capBT, "CapB"), (capCT, "CapC")):
                    fi = await mk("PositionInterpolator", {"key": [0, .4, .7, 1] if not rev else [0, .6, .9, 1], "keyValue": fade}, name=f"{cname}_{nm2}"); await route(ck, "fraction_changed", fi, "set_fraction"); await route(fi, "value_changed", tg, "scale"); (assem.append(fi) if not rev else None)
                fly = "Fly" if not rev else "FlyBack"
                p0, p1 = ((0, 12, 78), (0, 8, 34)) if not rev else ((0, 8, 34), (0, 12, 78))
                tgt0 = (0, 0, 0)
                cp = await mk("PositionInterpolator", {"key": [0, .3, .8, 1], "keyValue": [list(p0), list(p0), list(p1), list(p1)]}, name=f"{cname}_CamP"); co = await mk("OrientationInterpolator", {"key": [0, 1], "keyValue": [look(p0), look(p1)]}, name=f"{cname}_CamO")
                for it in (cp, co): await route(ck, "fraction_changed", it, "set_fraction")
                await route(cp, "value_changed", vids[fly], "position"); await route(co, "value_changed", vids[fly], "orientation")
                await route(ck, "isActive", vids[fly], "set_bind")
                bf = await mk("BooleanFilter", name=f"{cname}_End"); await route(ck, "isActive", bf, "set_boolean"); await route(bf, "inputNegate", vids["Orbit" if not rev else "Row"], "set_bind")
            # signs with touch sensors
            for nm, txt_, at, cname in (("SignAssemble", "ASSEMBLE", [-6, -15, 0], "AssembleClock"), ("SignDisassemble", "DISASSEMBLE", [6, -15, 0], "DisassembleClock")):
                tr = await mk("Transform", {"translation": at}, name=nm); await label(tr, txt_, [0, 0, 0], .9, (1, .85, .3))
                sh = await mk("Shape", parent=tr); ap = await mk("Appearance", parent=sh); await mk("Material", {"transparency": 1.0}, parent=ap); await mk("Box", {"size": [7, 1.4, .3]}, parent=sh)
                ts = await mk("TouchSensor", parent=tr, name=nm + "Touch"); await route(ts, "touchTime", clocks[cname], "startTime")
            hc = await mk("TimeSensor", {"cycleInterval": 2.4, "loop": True}, name="HeartClock"); hi = await mk("PositionInterpolator", {"key": [0, .15, .3, .45, 1], "keyValue": [[1, 1, 1], [1.25, 1.25, 1.25], [1, 1, 1], [1.15, 1.15, 1.15], [1, 1, 1]]}, name="HeartI")
            await route(hc, "fraction_changed", hi, "set_fraction"); await route(hi, "value_changed", heart, "scale")
            shock = await mk("Transform", name="Shock", parent=modA); ssh = await mk("Shape", parent=shock); sap = await mk("Appearance", parent=ssh); smat = await mk("Material", {"diffuseColor": [.2, .4, 1], "emissiveColor": [.4, .7, 1], "transparency": 1.0}, parent=sap, name="ShockMat"); await mk("Sphere", {"radius": R + 0.5}, parent=ssh)
            sw = await mk("PositionInterpolator", {"key": [0, .8, 1], "keyValue": [[1, 1, 1], [1, 1, 1], [4.5, 4.5, 4.5]]}, name="ShockScale"); st_ = await mk("ScalarInterpolator", {"key": [0, .79, .8, 1], "keyValue": [1, 1, .55, 1]}, name="ShockFade")
            ac = clocks["AssembleClock"]
            for it in (sw, st_): await route(ac, "fraction_changed", it, "set_fraction")
            await route(sw, "value_changed", shock, "scale"); await route(st_, "value_changed", smat, "transparency")
            # pulse for the classes new in 4.1
            pc = await mk("TimeSensor", {"cycleInterval": 2.4, "loop": True}, name="Pulse"); pi = await mk("PositionInterpolator", {"key": [0, .5, 1], "keyValue": [[1, 1, 1], [1.7, 1.7, 1.7], [1, 1, 1]]}, name="PulseScale")
            await route(pc, "fraction_changed", pi, "set_fraction")
            for tr in newT: await route(pi, "value_changed", tr, "scale")
            # ---- film clock chain (assemble without the camera flight), halo for the tour
            af = await mk("TimeSensor", {"cycleInterval": 16, "loop": False}, name="AssembleFilm")
            for it in assem + [sw, st_]: await route(af, "fraction_changed", it, "set_fraction")
            FILM = 75.0
            way = [(0, (0, 16, 100), (0, 0, 0)), (7, (0, 11, 72), (0, 0, 0)), (10, (-12, 14, 44), (-26, 0, 0)), (15, (-26, 24, 34), (-26, 0, 0)), (20, (-44, 12, 10), (-26, 0, 0)), (24, (-26, 16, -30), (-26, 0, 0)),
                   (28, (-4, 10, 36), (0, 0, 0)), (33, (14, 6, 22), (0, 2, 0)), (37, (0, 3, 20), (0, 0, 0)), (40, (26, 22, 46), (26, 0, 0)), (43, (40, 10, 24), (26, 0, 0)), (47, (0, 20, 84), (0, 0, 0)),
                   (52, (0, 12, 62), (0, 0, 0)), (58, (0, 8, 40), (0, 0, 0)), (62, (22, 8, 30), (0, 0, 0)), (67, (34, 9, 10), (0, 0, 0)), (72, (16, 8, 30), (0, 0, 0)), (75, (0, 8, 34), (0, 0, 0))]
            def spl(a, b, c, d, u): return [0.5 * ((2 * y1) + (-x0 + y2) * u + (2 * x0 - 5 * y1 + 4 * y2 - d_) * u * u + (-x0 + 3 * y1 - 3 * y2 + d_) * u ** 3) for x0, y1, y2, d_ in zip(a, b, c, d)]
            def at(t, idx):
                i = max(j for j in range(len(way) - 1) if way[j][0] <= t) if t < way[-1][0] else len(way) - 2
                u = (t - way[i][0]) / (way[i + 1][0] - way[i][0]); u = min(1, max(0, u)); u = u * u * (3 - 2 * u) * 0.35 + u * 0.65
                g = lambda k: way[max(0, min(len(way) - 1, k))][idx]
                return spl(g(i - 1), g(i), g(i + 1), g(i + 2), u)
            fk, fpv, fov = [], [], []
            for n_ in range(151):
                t = n_ * 0.5; pz = [round(x, 3) for x in at(t, 1)]; tg = at(t, 2); fk.append(round(t / FILM, 5)); fpv.append(pz); fov.append(look(pz, tg))
            fc = await mk("TimeSensor", {"cycleInterval": FILM, "loop": False}, name="FilmClock")
            fpi = await mk("PositionInterpolator", {"key": fk, "keyValue": fpv}, name="FilmP"); foi = await mk("OrientationInterpolator", {"key": fk, "keyValue": fov}, name="FilmO")
            for it in (fpi, foi): await route(fc, "fraction_changed", it, "set_fraction")
            await route(fpi, "value_changed", vids["Film"], "position"); await route(foi, "value_changed", vids["Film"], "orientation"); await route(fc, "isActive", vids["Film"], "set_bind")
            fbf = await mk("BooleanFilter", name="Film_End"); await route(fc, "isActive", fbf, "set_boolean"); await route(fbf, "inputNegate", vids["Orbit"], "set_bind")
            d44 = await mk("TimeSensor", {"cycleInterval": 44, "loop": False}, name="Delay44"); await route(fc, "cycleTime", d44, "startTime")
            dbf = await mk("BooleanFilter", name="Delay_End"); await route(d44, "isActive", dbf, "set_boolean"); ttg = await mk("TimeTrigger", name="AssembleAt44"); await route(dbf, "inputNegate", ttg, "set_boolean"); await route(ttg, "triggerTime", af, "startTime")
            hl = await mk("Transform", {"scale": [0, 0, 0]}, name="HaloT"); hp = await mk("Transform", parent=hl, name="HaloPulse"); hsh = await emissive(hp, [1, .8, .3], tr=0.78, diffuse=[1, .8, .3]); await mk("Sphere", {"radius": 1.0}, parent=hsh)
            hring = await emissive(hp, [1, .9, .5]); hil = await mk("IndexedLineSet", {"coordIndex": list(range(64)) + [0, -1]}, parent=hring); await mk("Coordinate", {"point": [[round(1.5 * math.cos(2 * math.pi * i / 64), 3), 0, round(1.5 * math.sin(2 * math.pi * i / 64), 3)] for i in range(64)]}, parent=hil, cf="coord")
            hc_ = await mk("TimeSensor", {"cycleInterval": 1.6, "loop": True}, name="HaloClock"); hpi = await mk("PositionInterpolator", {"key": [0, .5, 1], "keyValue": [[1, 1, 1], [1.18, 1.18, 1.18], [1, 1, 1]]}, name="HaloI")
            await route(hc_, "fraction_changed", hpi, "set_fraction"); await route(hpi, "value_changed", hp, "scale")
            # orbit camera (bound after assemble): slow loop around the finished sphere
            oc = await mk("TimeSensor", {"cycleInterval": 90, "loop": True}, name="OrbitClock"); keys = [i / 16 for i in range(17)]; ps_, os_ = [], []
            for i in range(17):
                th = 2 * math.pi * i / 16; p = (34 * math.sin(th), 8 + 2.5 * math.sin(2 * th), 34 * math.cos(th)); ps_.append(list(p)); os_.append(look(p))
            op = await mk("PositionInterpolator", {"key": keys, "keyValue": ps_}, name="OrbitP"); oo = await mk("OrientationInterpolator", {"key": keys, "keyValue": os_}, name="OrbitO")
            for it in (op, oo): await route(oc, "fraction_changed", it, "set_fraction")
            await route(op, "value_changed", vids["Orbit"], "position"); await route(oo, "value_changed", vids["Orbit"], "orientation")
            build_s = time.perf_counter() - t_build
            xml = await call("get_scene", {"encoding": "xml"})
            head = ("<head>\n    <meta name='title' content='Ontology Dyson sphere (TOY demo)'/>\n"
                    "    <meta name='description' content='Three modules pulled into one toy ontology Dyson sphere: 364 classes of X3D Ontology 4.1 on a shell, the flywheel loop ring, and three domain rings (X3D components, URDF and glTF fault operators). Layout, colour and motion are display choices; timings in captions are quoted from measured runs, not played in real time. Private until 2027-01-01.'/>\n"
                    f"    <meta name='source-ontology-sha256' content='{MAN['input_sha256']}'/>\n    <meta name='source-model-sha256' content='{MAN['output_sha256']}'/>\n"
                    f"    <meta name='created' content='{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}'/>\n"
                    f"    <meta name='generator' content='x3d_mcp granular tools ({git}) driven by demo/make_demo.py; head and profile patched in by the script because no tool sets them'/>\n  </head>\n")
            xml = re.sub(r"(<X3D[^>]*?)profile='[^']*'", r"\1profile='Immersive'", xml, count=1); xml = xml.replace("<Scene>", head + "  <Scene>", 1)
            path = HERE / "scenes" / "ontology-dyson.x3d"; path.write_text(xml, encoding="utf-8")
            rep = dict(file=str(path), bytes=len(xml.encode()), sha256=hashlib.sha256(xml.encode()).hexdigest(), x3d_mcp_commit=git, tool_calls=sum(calls.values()), calls=calls, build_seconds=round(build_s, 1),
                       call_ms=dict(p50=round(statistics.median(lat), 2), p95=round(sorted(lat)[int(.95 * len(lat))], 2), max=round(max(lat), 1)), eval=summary)
            for tool, args in (("validate_x3d", {"content": xml, "encoding": "xml"}), ("validate_semantic", {"content": xml})):
                t0 = time.perf_counter(); t = txt(await s.call_tool(tool, args)); rep[tool + "_ms"] = round((time.perf_counter() - t0) * 1000)
                try: rep[tool] = json.loads(t)
                except Exception: rep[tool] = {"raw": t[:2500]}
    (ROOT / "out" / "demo_run.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("bytes", "tool_calls", "build_seconds", "call_ms", "validate_x3d_ms", "validate_semantic_ms")})); print("validate_x3d:", json.dumps(rep["validate_x3d"])[:500]); print("semantic:", json.dumps(rep["validate_semantic"])[:900])
asyncio.run(main())
r_ = subprocess.run([sys.executable, "-I", str(HERE / "build_tour.py")], capture_output=True, text=True); print("build_tour:", r_.returncode, (r_.stdout or r_.stderr).strip()[-200:])
