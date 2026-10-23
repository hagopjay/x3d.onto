#!/usr/bin/env python3
"""Every standalone number in the scene's Text strings must be derivable from a source file or listed in sources.json. Fails (exit 1) otherwise.
usage: python3 audit_numbers.py -> ../out/demo_audit.json"""
import json, re, sys
from pathlib import Path
from lxml import etree
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sc = etree.parse(str(HERE / "scenes" / "ontology-dyson.x3d")).getroot()
D = json.loads((ROOT / "data" / "explorer.json").read_text()); CR = json.loads((ROOT / "out" / "constellation_run.json").read_text())
UR = json.loads((ROOT / "out" / "xdomain_urdf.json").read_text()); GL = json.loads((ROOT / "out" / "xdomain_gltf.json").read_text()); COMP = json.loads((ROOT / "data" / "components.json").read_text())
SRC = json.loads((HERE / "sources.json").read_text())["facts"]
allowed = {}
def ok(tok, why): allowed.setdefault(tok, why)
ok(str(D["stats"]["classes"]), "data/explorer.json stats.classes"); ok("4.1", "ontology version (manifest.ontology41.json, X3dOntology4.1.ttl)")
ok(str(round(CR["bytes"] / 1000)), "out/constellation_run.json bytes / 1000 (KB)"); ok(f"{CR['validate_x3d_ms'] / 1000:.1f}", "out/constellation_run.json validate_x3d_ms")
ok(f"{CR['nano_call_ms']['p50']:.1f}", "out/constellation_run.json nano_call_ms.p50")
for k, f in SRC.items():
    for tok in re.findall(r"\d+(?:\.\d+)?", f["text"]): ok(tok, f"demo/sources.json {k}: {f['source']} ({f['grade']})")
ok(str(len(COMP)), "data/components.json rows"); ok(str(len(UR["faults"])), "out/xdomain_urdf.json faults"); ok(str(len(GL["faults"])), "out/xdomain_gltf.json faults")
for dom, key in (("x3d", "X3D"), ("urdf", "URDF"), ("gltf", "glTF")):
    p = ROOT / "xdomain" / "eval-plan" / "runs" / f"{dom}-gemini-3.8-flash.jsonl"
    if p.exists():
        rows = [json.loads(l) for l in p.read_text().splitlines()]; a0 = [r for r in rows if r["arm"] == "A0"]; a2 = [r for r in rows if r["arm"] == "A2-final"]
        if len(a0) >= 30 and a2:
            ok(str(len(a0)), f"{p.name} A0 rows"); ok(f"{round(100 * sum(r['valid'] for r in a0) / len(a0))}", f"{p.name} A0 validity"); ok(f"{round(100 * sum(r['valid'] for r in a2) / len(a2))}", f"{p.name} A2-final validity")
strings = []
for t in sc.iter("Text"): strings += re.findall(r"'([^']*)'|\"([^\"]*)\"", t.get("string", "")) and [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", t.get("string", ""))]
found = {}; bad = []
for s in strings:
    for m in re.finditer(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)(?![A-Za-z0-9_])", s):
        tok = m.group(1); found.setdefault(tok, []).append(s[:60])
        if tok not in allowed: bad.append((tok, s[:80]))
out = dict(strings=len(strings), numbers=sorted(found), unexplained=bad, allowed={k: allowed[k] for k in found if k in allowed})
(ROOT / "out" / "demo_audit.json").write_text(json.dumps(out, indent=1)); print(json.dumps({k: out[k] for k in ("strings", "numbers", "unexplained")}))
sys.exit(1 if bad else 0)
