#!/usr/bin/env python3
"""One MCP server, two domains: the validator-MCP pattern from x3d_mcp applied to URDF (own rules, grade L) and glTF (official Khronos validator).
Tools mirror x3d_mcp's roles: describe, validate, repair, record/verify. Run with the x3d_mcp venv python (has mcp, lxml); needs node for glTF.
Prototype: stdio only, no network, reads nothing outside its arguments."""
import asyncio, json, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mcp.server.fastmcp import FastMCP
from kit import Diag, Report, stamp, verify, RUNGS
import importlib.util
def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
urdf_check = _load("urdf_check", HERE / "urdf" / "urdf_check.py"); urdf_repair_mod = _load("urdf_repair", HERE / "urdf" / "repair.py"); gltf_repair_mod = _load("gltf_repair", HERE / "gltf" / "repair.py")
mcp = FastMCP("xdomain-validators")
# gate policy: Khronos reports these as warnings; an agent gate should not let them through
STRICT_WARNINGS = {"UNSUPPORTED_EXTENSION": "a required extension this oracle cannot check", "MESH_PRIMITIVE_NO_POSITION": "primitive without POSITION draws nothing"}
HINTS = {"UNRESOLVED_REFERENCE": "an index points at nothing: fix the index or add the object", "ACCESSOR_TOO_LONG": "count x element size exceeds the bufferView: reduce count or enlarge the view",
         "BUFFER_BYTE_LENGTH_MISMATCH": "set buffers[i].byteLength to the real data length (deterministic repair available)", "ACCESSOR_MAX_MISMATCH": "recompute min/max from the data (deterministic repair available)",
         "NODE_LOOP": "a node is its own ancestor: remove one child link", "VALUE_NOT_IN_RANGE": "value outside the allowed range or not unit length (quaternions: normalise)", "UNDEFINED_PROPERTY": "a required property is missing (asset.version: add \"2.0\")",
         "ACCESSOR_INDEX_OOB": "an index value is beyond the vertex count: regenerate indices", "NODE_MATRIX_TRS": "use either matrix or translation/rotation/scale, not both", "INVALID_JSON": "fix JSON syntax"}
def _ser(r: Report, extra=None):
    j = r.to_json()
    if extra: j.update(extra)
    return json.dumps(j)
@mcp.tool()
def xdomain_describe(domain: str) -> str:
    """Describe a domain's checks. domain: 'urdf' or 'gltf'. Lists rule ids with their verification-ladder rung and the X3D counterpart where one exists."""
    if domain == "urdf":
        return json.dumps({"oracle": "urdf_check.py rules (grade L; not validated against urdfdom or MuJoCo)", "rules": [dict(id=a, rung=b, what=c, x3d_counterpart=d) for a, b, c, d in urdf_check.RULES], "ladder": RUNGS})
    if domain == "gltf":
        return json.dumps({"oracle": "Khronos glTF-Validator 2.0.0-dev.3.10 (Apache-2.0), run through node", "gate_policy": {"strict_warnings": STRICT_WARNINGS}, "hints": HINTS, "ladder": RUNGS})
    return json.dumps({"error": "domain must be 'urdf' or 'gltf'"})
@mcp.tool()
def urdf_validate(content: str, level: int = 2) -> str:
    """Validate URDF XML. level 1 = structure (XSD-like job), 2 = semantics (tree, limits, inertia, contact). Returns located diagnostics with fix hints and the ladder rung."""
    return _ser(urdf_check.check(content, level))
@mcp.tool()
def urdf_repair(content: str) -> str:
    """Apply deterministic URDF repairs (axis normalisation, swapped limits, velocity sign, colour clamp). Invents nothing. Returns the new document and what changed."""
    fixed, done = urdf_repair_mod.repair(content); r = urdf_check.check(fixed, 2)
    return json.dumps({"content": fixed, "applied": done, "valid_after": r.valid, "errors_after": len(r.errors)})
async def _khronos(text: str):
    d = tempfile.mkdtemp(); Path(d, "doc.gltf").write_text(text)
    p = await asyncio.create_subprocess_exec("node", str(HERE / "gltf" / "validate.mjs"), d, cwd=str(HERE / "gltf"), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await p.communicate()
    return json.loads(out.decode().splitlines()[0]) if out else {"crash": err.decode()[:300]}
@mcp.tool()
async def gltf_validate(content: str, strict: bool = True) -> str:
    """Validate glTF JSON with the Khronos validator. strict=True applies the agent gate policy: UNSUPPORTED_EXTENSION and MESH_PRIMITIVE_NO_POSITION (warnings upstream) count as errors."""
    r = await _khronos(content)
    if "crash" in r: return json.dumps({"error": r["crash"]})
    rep = Report("gltf", f"Khronos glTF-Validator {r.get('version')}", ms=r["ms"])
    for m in r["messages"]:
        sev = {0: "error", 1: "warning", 2: "info", 3: "info"}.get(m["severity"], "info")
        if strict and m["code"] in STRICT_WARNINGS and sev != "error": sev = "error"
        rep.diags.append(Diag(m["code"], sev, 2 if m["code"] != "INVALID_JSON" else 0, m["pointer"], m["message"], HINTS.get(m["code"], "")))
    return _ser(rep, {"policy": "strict" if strict else "upstream", "upstream": {k: r[k] for k in ("errors", "warnings", "infos", "hints")}})
@mcp.tool()
def gltf_repair(content: str) -> str:
    """Deterministic glTF repairs: missing asset.version, byteLength from data, min/max from data, quaternion normalisation. Does not remove dangling references."""
    fixed, done = gltf_repair_mod.repair(content); return json.dumps({"content": fixed, "applied": done})
@mcp.tool()
def record_step(chain_json: str, op: str, artifact: str, report_json: str) -> str:
    """Append a hash-chained step (sketch of x3dprov: op, artifact hash, report hash, previous hash). Returns the new chain."""
    return json.dumps(stamp(json.loads(chain_json or "[]"), op, artifact, json.loads(report_json or "{}")))
@mcp.tool()
def verify_chain(chain_json: str, artifact: str = "") -> str:
    """Verify a chain: ok, stale (artifact changed after the last step) or broken-chain (a step was edited or removed)."""
    return json.dumps({"verdict": verify(json.loads(chain_json), artifact or None)})
if __name__ == "__main__": mcp.run()
