#!/usr/bin/env python3
"""Author the ontology constellation as X3D through x3d_mcp's granular tools (stdio MCP client), then validate it with the same server.
Nodes sit on a Dyson-style shell: longitude = the explorer's layout angle, latitude = class depth. Layout is a display choice, not an ontology fact (said in <head>).
Records per-call latency (nano scale) and whole-scene validation timing (giga scale) in out/constellation_run.json.
usage: ~/Projects/x3d/x3d_mcp/.venv/bin/python harness/make_constellation.py [x3d_mcp checkout]"""
import asyncio, colorsys, datetime, hashlib, json, math, os, re, statistics, subprocess, sys, time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
REPO = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Projects/x3d/x3d_mcp")
D = json.loads((ROOT / "data" / "explorer.json").read_text())
MAN = json.loads((ROOT / "data" / "manifest.ontology41.json").read_text())
txt = lambda r: "".join(getattr(c, "text", "") for c in r.content)
R = 8.0
maxd = D["stats"]["max_depth"]
def sph(n):
    lon = n["a"]; lat = math.radians(70 - n["d"] * 140 / maxd)
    return [round(R * math.cos(lat) * math.cos(lon), 3), round(R * math.sin(lat), 3), round(R * math.cos(lat) * math.sin(lon), 3)]
fams = sorted(D["families"], key=lambda f: -D["families"][f])
def rgb(f):
    h = (fams.index(f) * 137.5 % 360) / 360
    return [round(v, 3) for v in colorsys.hls_to_rgb(h, .62, .7)]
XT = set(D["xcheck"]["table"])
try: git = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception: git = "?"

async def main():
    params = StdioServerParameters(command=os.path.join(REPO, ".venv/bin/python"), args=["-m", "src.server"], cwd=REPO)
    lat_ms = []; calls = {}
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await s.call_tool("reset_scene", {})
            async def call(name, args):
                t0 = time.perf_counter(); t = txt(await s.call_tool(name, args)); lat_ms.append((time.perf_counter() - t0) * 1000)
                calls[name] = calls.get(name, 0) + 1
                if t.startswith("Error") or "Error executing" in t: raise SystemExit(f"{name} {json.dumps(args)[:160]} -> {t[:300]}")
                return t
            async def mk(nt, fields=None, parent=None, cf="", name=None):
                t = await call("create_node", {"node_type": nt, "fields": fields or {}})
                nid = re.search(r"ID: (\S+)", t).group(1)
                if parent: await call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf})
                if name: await call("def_node", {"node_id": nid, "name": name})
                return nid
            async def use(parent, def_name, cf):
                t = await call("use_node", {"def_name": def_name}); nid = re.search(r"ID: (\S+)", t).group(1)
                await call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf}); return nid
            t_build = time.perf_counter()
            await mk("NavigationInfo", {"type": ["EXAMINE", "ANY"], "headlight": True, "speed": 4})
            await mk("Background", {"skyColor": [[0.03, 0.04, 0.07]]})
            await mk("Viewpoint", {"position": [0, 3, 26], "orientation": [1, 0, 0, -0.1], "fieldOfView": 0.8, "description": "Shell overview"}, name="Overview")
            await mk("Viewpoint", {"position": [0, 0, 0.5], "orientation": [0, 1, 0, 0], "fieldOfView": 1.2, "description": "Inside the shell"}, name="Inside")
            await mk("Viewpoint", {"position": [0, 24, 0.1], "orientation": [1, 0, 0, -1.5708], "fieldOfView": 0.8, "description": "Top"}, name="Top")
            # per-family appearances, DEF once, USE per node
            mats = await mk("Group", name="FamilyMaterials")
            # one emissive appearance for classes new in 4.1
            shn = await mk("Shape", parent=mats); apn = await mk("Appearance", parent=shn, name="New41")
            await mk("Material", {"diffuseColor": [.2, 1, .5], "emissiveColor": [.2, .9, .45]}, parent=apn); await mk("Sphere", {"radius": 0.001}, parent=shn)
            for f in fams:
                sh = await mk("Shape", parent=mats); ap = await mk("Appearance", parent=sh, name="Fam_" + f)
                await mk("Material", {"diffuseColor": rgb(f), "emissiveColor": [c * .35 for c in rgb(f)], "specularColor": [.3, .3, .3]}, parent=ap)
                await mk("Sphere", {"radius": 0.001}, parent=sh)
            # the star at the core: layout anchor only
            star = await mk("Shape"); ap = await mk("Appearance", parent=star); await mk("Material", {"diffuseColor": [1, .8, .3], "emissiveColor": [1, .75, .25]}, parent=ap)
            await mk("Sphere", {"radius": 0.5}, parent=star)
            await mk("PointLight", {"location": [0, 0, 0], "intensity": 1.2, "radius": 40, "color": [1, .9, .7]})
            nodes_grp = await mk("Group", name="Classes")
            pos = {}
            for n in D["nodes"]:
                p = sph(n); pos[n["id"]] = p
                r = round(min(0.38, 0.07 + 0.035 * math.sqrt(1 + n["desc"])) * (1.5 if n["new"] else 1), 3)
                tr = await mk("Transform", {"translation": p}, parent=nodes_grp, name="C_" + n["id"])
                sh = await mk("Shape", parent=tr)
                await use(sh, "New41" if n["new"] else "Fam_" + n["fam"], "appearance")
                await mk("Box" if n["kind"] == "abstract" else "Sphere", {"size": [r * 1.6] * 3} if n["kind"] == "abstract" else {"radius": r}, parent=sh)
            # labels for roots and the 10 cross-check types
            lab = await mk("Group", name="Labels")
            for n in D["nodes"]:
                if n["d"] == 0 and n["desc"] >= 3 or n["id"] in XT or n["new"]:
                    p = pos[n["id"]]; tr = await mk("Transform", {"translation": [p[0] * 1.06, p[1] * 1.06 + .25, p[2] * 1.06]}, parent=lab)
                    bb = await mk("Billboard", {"axisOfRotation": [0, 0, 0]}, parent=tr); sh = await mk("Shape", parent=bb)
                    ap = await mk("Appearance", parent=sh); await mk("Material", {"diffuseColor": [0, 0, 0], "emissiveColor": [.3, 1, .5] if n["new"] else ([1, 1, 1] if n["id"] not in XT else [.4, 1, .6])}, parent=ap)
                    tx = await mk("Text", {"string": [n["id"]]}, parent=sh); await mk("FontStyle", {"family": ["SANS"], "size": 0.34, "justify": ["MIDDLE"]}, parent=tx)
            # edges: primary-parent hierarchy chords and containment of Shape, as two IndexedLineSets
            ids = [n["id"] for n in D["nodes"]]; ix = {c: i for i, c in enumerate(ids)}
            hier = [v for n in D["nodes"] if n["pp"] for v in (ix[n["id"]], ix[n["pp"]], -1)]
            shape = next(n for n in D["nodes"] if n["id"] == "Shape")
            sets = {"A": [], "R": [], "I": [], "-": []}
            for (d, _), v in zip(shape["lp"], shape["lpv"]): sets[v] += [ix["Shape"], ix[d], -1]
            specs = [("Hierarchy", hier, [.25, .32, .5]), ("ShapeXsdAccepts", sets["A"], [.3, 1, .55]), ("ShapeXsdRejects", sets["R"], [1, .35, .35]),
                     ("ShapeXsdInconclusive", sets["I"], [1, .78, .3]), ("ShapeAbstractParents", sets["-"], [.35, .8, 1.0])]
            for nm_, idx, col in specs:
                if not idx: continue
                sh = await mk("Shape", name=nm_); ap = await mk("Appearance", parent=sh); await mk("Material", {"diffuseColor": [0, 0, 0], "emissiveColor": col}, parent=ap)
                ils = await mk("IndexedLineSet", {"coordIndex": idx}, parent=sh)
                await mk("Coordinate", {"point": [pos[c] for c in ids]}, parent=ils, cf="coord")
            build_s = time.perf_counter() - t_build
            xml = await call("get_scene", {"encoding": "xml"})
            head = ("<head>\n"
                    "    <meta name='title' content='X3D Ontology constellation (Dyson-style shell)'/>\n"
                    "    <meta name='description' content='364 classes of X3D Ontology 4.1 (Web3D draft dated 29 September 2026) on a shell: longitude = layout angle, latitude = class depth. Layout is a display choice, not an ontology fact. Square boxes are abstract types, spheres concrete nodes. Core star is a layout anchor. Green = new in 4.1. Edges from Shape: green = XSD accepts that parent, red = rejects, amber = inconclusive, blue = abstract parent (untested).'/>\n"
                    f"    <meta name='source-ontology-sha256' content='{MAN['input_sha256']}'/>\n"
                    f"    <meta name='source-model-sha256' content='{MAN['output_sha256']}'/>\n"
                    f"    <meta name='created' content='{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}'/>\n"
                    f"    <meta name='generator' content='x3d_mcp granular tools ({git}) driven by harness/make_constellation.py; head and profile patched in by the script because no tool sets them'/>\n"
                    "  </head>\n")
            xml = re.sub(r"(<X3D[^>]*?)profile='[^']*'", r"\1profile='Immersive'", xml, count=1)
            xml = xml.replace("<Scene>", head + "  <Scene>", 1)
            path = ROOT / "scenes" / "ontology-constellation.x3d"; path.write_text(xml, encoding="utf-8")
            rep = {"file": str(path), "bytes": len(xml.encode()), "sha256": hashlib.sha256(xml.encode()).hexdigest(), "x3d_mcp_commit": git,
                   "tool_calls": sum(calls.values()), "calls_by_tool": calls, "build_seconds": round(build_s, 2),
                   "nano_call_ms": {"p50": round(statistics.median(lat_ms), 2), "p95": round(sorted(lat_ms)[int(.95 * len(lat_ms))], 2), "max": round(max(lat_ms), 1)}}
            for tool, args in (("validate_x3d", {"content": xml, "encoding": "xml"}), ("validate_semantic", {"content": xml})):
                t0 = time.perf_counter(); t = txt(await s.call_tool(tool, args)); ms = round((time.perf_counter() - t0) * 1000)
                try: rep[tool] = json.loads(t)
                except Exception: rep[tool] = {"raw": t[:3000]}
                rep[tool + "_ms"] = ms
    (ROOT / "out" / "constellation_run.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("bytes", "tool_calls", "build_seconds", "nano_call_ms", "validate_x3d_ms", "validate_semantic_ms")}))
    print("validate_x3d:", json.dumps(rep["validate_x3d"])[:400]); print("validate_semantic:", json.dumps(rep["validate_semantic"])[:1200])
asyncio.run(main())
