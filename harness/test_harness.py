#!/usr/bin/env python3
"""Checks the built model against the live x3d_mcp tool code (read-only import).
usage: test_harness.py <x3d_mcp checkout>   (use that checkout's .venv python)"""
import json, sys, time
from pathlib import Path
root = Path(sys.argv[1]).expanduser()
sys.path.insert(0, str(root / "src"))
from x3d_utils.ontology import get_ontology  # noqa
D = json.loads((Path(__file__).resolve().parent.parent / "data" / "ontology.json").read_text())
man = json.loads((Path(__file__).resolve().parent.parent / "data" / "manifest.json").read_text())
onto = get_ontology()
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not ok: fails.append(name)

check("triples == 17736 (README figure)", D["stats"]["triples"] == 17736, str(D["stats"]["triples"]))
check("355 classes", D["stats"]["classes"] == 355)
t0 = time.time(); bad = []
for n in D["nodes"]:
    tool = sorted((r["parent"], r["field"]) for r in onto.node_parents(n["id"]))
    mine = sorted(map(tuple, n["lp"]))
    if tool != mine: bad.append(n["id"])
check("node_parents identical to x3d_mcp tool for all 355 classes", not bad, f"{len(bad)} differ {bad[:5]} in {time.time()-t0:.1f}s")
ten = D["xcheck"]["table"].keys()
nconc = sum(D["xcheck"]["mine_concrete_parent_pairs_this_file"].values())
check("10-type concrete-parent pairs on 4.0 == 319 (DOC figure for bundled 4.0)", nconc == 319, str(nconc))
check("describe_term sample (Sphere) has parent X3DGeometryNode", "X3DGeometryNode" in onto.describe_term("Sphere")["superClasses"])
for q in D["gallery"]:
    tool = onto.query(q["sparql"])
    check(f"gallery {q['id']} row count matches tool SPARQL", len(tool) == q["n"], f"{q['n']}")
check("manifest hash present", len(man["output_sha256"]) == 64)
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
