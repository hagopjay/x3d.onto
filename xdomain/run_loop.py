#!/usr/bin/env python3
"""End-to-end through the MCP server over stdio: validate -> repair -> revalidate -> record, for a faulty URDF and a faulty glTF, plus tamper tests on the chain.
usage: ~/Projects/x3d/x3d_mcp/.venv/bin/python run_loop.py -> ../out/xdomain_mcp_run.json"""
import asyncio, json, os, sys, time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
HERE = Path(__file__).resolve().parent; OUT = HERE.parent / "out"
import importlib.util
def load(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ucorp = load("ucorp", HERE / "urdf" / "corpus.py"); umut = load("umut", HERE / "urdf" / "mutate.py")
gc = load("gcorp", HERE / "gltf" / "corpus.py"); gm = load("gmut", HERE / "gltf" / "mutate.py")
txt = lambda r: "".join(getattr(c, "text", "") for c in r.content)
async def main():
    py = os.path.expanduser("~/Projects/x3d/x3d_mcp/.venv/bin/python")
    async with stdio_client(StdioServerParameters(command=py, args=[str(HERE / "xdomain_server.py")], cwd=str(HERE))) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); lat = {}; log = {}
            async def call(name, args):
                t0 = time.perf_counter(); out = txt(await s.call_tool(name, args)); lat.setdefault(name, []).append((time.perf_counter() - t0) * 1000); return json.loads(out)
            tools = [t.name for t in (await s.list_tools()).tools]
            # URDF: a mutant with two fixable defects and one that needs a decision
            u = ucorp.arm2()
            u1 = umut.F["F13"][2](u); u1 = umut.F["F14"][2](u1) if False else u1
            u1 = u1.replace('xyz="0 1 0"', 'xyz="0 0 2"', 1).replace('velocity="2"', 'velocity="-2"', 1)
            chain = []
            v0 = await call("urdf_validate", {"content": u1}); chain = await call("record_step", {"chain_json": json.dumps(chain), "op": "validate", "artifact": u1, "report_json": json.dumps(v0)})
            rp = await call("urdf_repair", {"content": u1}); chain = await call("record_step", {"chain_json": json.dumps(chain), "op": "repair", "artifact": rp["content"], "report_json": json.dumps(rp["applied"])})
            v1 = await call("urdf_validate", {"content": rp["content"]}); chain = await call("record_step", {"chain_json": json.dumps(chain), "op": "revalidate", "artifact": rp["content"], "report_json": json.dumps(v1)})
            tamper_edit = [dict(c) for c in chain]; tamper_edit[1]["op"] = "forged"
            log["urdf"] = dict(errors_before=v0["errors"], warnings_before=v0["warnings"], rules_before=sorted({d["rule"] for d in v0["diagnostics"]}), applied=[a[2] for a in rp["applied"]], errors_after=v1["errors"], warnings_after=v1["warnings"],
                               chain_ok=(await call("verify_chain", {"chain_json": json.dumps(chain), "artifact": rp["content"]}))["verdict"], after_edit=(await call("verify_chain", {"chain_json": json.dumps(chain), "artifact": rp["content"] + " "}))["verdict"],
                               after_forged_step=(await call("verify_chain", {"chain_json": json.dumps(tamper_edit)}))["verdict"], after_deleted_step=(await call("verify_chain", {"chain_json": json.dumps(chain[1:])}))["verdict"], chain_len=len(chain))
            # glTF: required unsupported extension (warning upstream), and a repairable pair
            g = json.dumps(gc.cube()); g1 = json.loads(g); g1["buffers"][0]["byteLength"] += 8; del g1["asset"]["version"]; g1["extensionsRequired"] = ["KHR_fake"]; g1["extensionsUsed"] = ["KHR_fake"]; g1 = json.dumps(g1)
            a = await call("gltf_validate", {"content": g1, "strict": False}); b = await call("gltf_validate", {"content": g1, "strict": True})
            rp = await call("gltf_repair", {"content": g1}); c = await call("gltf_validate", {"content": rp["content"], "strict": True})
            log["gltf"] = dict(upstream_policy=dict(errors=a["errors"], warnings=a["warnings"]), strict_policy=dict(errors=b["errors"]), codes_before=sorted({d["rule"] for d in b["diagnostics"]}), applied=[x[2] for x in rp["applied"]],
                               errors_after_strict=c["errors"], remaining=sorted({d["rule"] for d in c["diagnostics"] if d["severity"] == "error"}), oracle=b["oracle"])
            log["tools"] = tools; log["latency_ms"] = {k: dict(n=len(v), median=round(sorted(v)[len(v) // 2], 1), max=round(max(v), 1)) for k, v in lat.items()}
    (OUT / "xdomain_mcp_run.json").write_text(json.dumps(log, indent=1)); print(json.dumps(log, indent=1))
asyncio.run(main())
