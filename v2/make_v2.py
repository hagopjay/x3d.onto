#!/usr/bin/env python3
"""v2: ontology constellation orbiting Sun, Earth and Moon, with a village at human scale.  Every node is authored through x3d_mcp's granular tools (stdio MCP client).
usage: ~/Projects/x3d/x3d_mcp/.venv/bin/python make_v2.py [--only space|town|people] -> scenes/solar-town.x3d, data/picks.json, out/v2_run.json"""
import asyncio, datetime, hashlib, json, os, re, statistics, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from mcp import ClientSession
from mcp.client.stdio import stdio_client
import mcpkit; from mcpkit import B, server_params, txt
import build_space as S, build_town as T, build_people as P
ROOT = HERE.parent
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "all"
try: git = subprocess.run(["git", "-C", mcpkit.REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception: git = "?"

async def main():
    t_build = time.perf_counter(); rep = {}
    async with stdio_client(server_params()) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); await s.call_tool("reset_scene", {}); b = B(s)
            await S.build_materials(b); await S.build_env(b)
            picks = []; people = []; tinfo = {}
            if only in ("all", "space"):
                world = await S.build_world(b); picks, pos = await S.build_constellation(b, world)
            else: world = await b.mk("Transform", name="World")
            if only in ("all", "town", "people"):
                core, out, tinfo = await T.build_town(b)
                if only in ("all", "people"): people = await P.build_people(b, core)
            build_s = time.perf_counter() - t_build
            xml = await b.call("get_scene", {"encoding": "xml"})
            head = ("<head>\n    <meta name='title' content='Ontology constellation v2: Sun, Earth, Moon and a village (TOY demo)'/>\n"
                    "    <meta name='description' content='A vision scene: 364 classes of X3D Ontology 4.1 and three domain rings orbit the Sun, Earth and Moon (true sizes and distances); the camera can descend to a fictional village with H-Anim villagers. Orbits use low-precision mean elements; the village, its people and the Earth/Moon maps are invented or procedural. Private until 2027-01-01.'/>\n"
                    f"    <meta name='source-ontology-sha256' content='{S.MAN['input_sha256']}'/>\n    <meta name='source-model-sha256' content='{S.MAN['output_sha256']}'/>\n"
                    f"    <meta name='created' content='{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}'/>\n"
                    f"    <meta name='generator' content='x3d_mcp granular tools ({git}) driven by v2/make_v2.py; head and profile patched in by the script because no tool sets them'/>\n  </head>\n")
            xml = re.sub(r"(<X3D[^>]*?)profile='[^']*'", r"\1profile='Full'", xml, count=1); xml = xml.replace("<Scene>", head + "  <Scene>", 1)
            (HERE / "scenes").mkdir(exist_ok=True); name = {"all": "solar-town", "space": "space-only", "town": "town-only", "people": "town-people"}[only]
            path = HERE / "scenes" / f"{name}.x3d"; path.write_text(xml, encoding="utf-8")
            rep = dict(file=str(path), bytes=len(xml.encode()), sha256=hashlib.sha256(xml.encode()).hexdigest(), x3d_mcp_commit=git, tool_calls=sum(b.calls.values()), calls=b.calls, build_seconds=round(build_s, 1),
                       call_ms=dict(p50=round(statistics.median(b.lat), 2), p95=round(sorted(b.lat)[int(.95 * len(b.lat))], 2), max=round(max(b.lat), 1)), town=tinfo, people=len(people))
            if "--no-validate" not in sys.argv:
                for tool, args in (("validate_x3d", {"content": xml, "encoding": "xml"}), ("validate_semantic", {"content": xml})):
                    t0 = time.perf_counter(); t = txt(await s.call_tool(tool, args)); rep[tool + "_ms"] = round((time.perf_counter() - t0) * 1000)
                    try: rep[tool] = json.loads(t)
                    except Exception: rep[tool] = {"raw": t[:2500]}; (HERE / "data" / (tool + "_report.txt")).write_text(t)
    (HERE / "data").mkdir(exist_ok=True); (HERE / "data" / "picks.json").write_text(json.dumps(picks, separators=(",", ":"))); (HERE / "data" / "people.json").write_text(json.dumps(people, indent=1))
    (ROOT / "out").mkdir(exist_ok=True); (ROOT / "out" / "v2_run.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("bytes", "tool_calls", "build_seconds", "call_ms") if k in rep})); print("validate_x3d:", json.dumps(rep.get("validate_x3d"))[:600]); print("semantic:", json.dumps(rep.get("validate_semantic"))[:900])
asyncio.run(main())
