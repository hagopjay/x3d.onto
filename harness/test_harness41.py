#!/usr/bin/env python3
"""4.1 / XSD matrix / sim checks. usage: test_harness41.py <x3d_mcp checkout>  (that checkout's .venv python)"""
import hashlib, json, sys, tempfile, time
from pathlib import Path
root = Path(sys.argv[1]).expanduser(); sys.path.insert(0, str(root / "src"))
from x3d_utils.ontology import X3DOntology  # noqa
H = Path(__file__).resolve().parent.parent / "data"
D = json.loads((H / "explorer.json").read_text())
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not ok: fails.append(name)
ttl = H / "X3dOntology4.1.ttl"
check("4.1 file SHA-1 equals the doc's manifest", hashlib.sha1(ttl.read_bytes()).hexdigest() == "1b5d645a80917ebfd35d3088bad4affa4c73bea2")
check("4.1 triples == 18121 (doc)", D["stats"]["triples"] == 18121, str(D["stats"]["triples"]))
check("4.1 adds exactly 9 classes (doc: 9)", len(D["delta"]["new"]) == 9, str(D["delta"]["new"]))
# tool logic on the 4.1 file: only the namespace version is rewritten, as the doc did
tmp = Path(tempfile.mkdtemp()) / "X3dOntology4.0.ttl"
tmp.write_text(ttl.read_text().replace("X3dOntology4.1#", "X3dOntology4.0#"))
onto = X3DOntology(path=tmp, extensions="")
t0 = time.time(); bad = []
for n in D["nodes"]:
    tool = sorted((r["parent"], r["field"]) for r in onto.node_parents(n["id"]))
    if tool != sorted(map(tuple, n["lp"])): bad.append(n["id"])
check("node_parents (tool logic on the 4.1 file) identical for all classes", not bad, f"{len(D['nodes'])} classes, {len(bad)} differ {bad[:4]}, {time.time()-t0:.1f}s")
x = D["xcheck"]
check("doc's 10-type table reproduced row by row", x["reproduced"])
check("10-type totals 348/150/163/35", [x["ten_totals"][k] for k in ("predicted", "accepts", "rejects", "inconclusive")] == [348, 150, 163, 35])
check("verdict counts add up", x["all"]["A"] + x["all"]["R"] + x["all"]["I"] == x["all"]["pairs"], f"{x['all']['pairs']} pairs")
npairs = sum(1 for n in D["nodes"] if n["kind"] == "concrete" for d, _ in n["lp"] if d in {m['id'] for m in D['nodes'] if m['kind'] == 'concrete'})
check("every concrete (child, concrete parent) pair has a verdict", npairs == x["all"]["pairs"], f"{npairs}")
U = D["uom"]["confusion"]; tot = sum(U[k] for k in ("uom_yes_xsd_accepts", "uom_yes_xsd_rejects", "uom_no_xsd_accepts", "uom_no_xsd_rejects"))
check("UOM-vs-XSD confusion covers every A/R pair but one", tot + U["no_uom_field_info"] == x["all"]["A"] + x["all"]["R"], f"{tot} + {U['no_uom_field_info']}")
xs = H / "xslt" / "X3duomToX3dOntology.xslt"
check("stylesheet SHA-1 recorded in the proposal", hashlib.sha1(xs.read_bytes()).hexdigest() == "f443c05f480795a5b3d71a01d0839bf20d105f80")
pc = json.loads((H.parent / "out" / "proposal_check.json").read_text())
check("restriction sketch reproduces the X3DUOM universe exactly", pc["identical_to_universe"] and pc["unresolved_count"] == 0, f"{pc['concrete_pairs']} pairs, {pc['axioms']} axioms")
pn = json.loads((H / "proposal_numbers.json").read_text())
check("proposal numbers add up", pn["containment_pairs"] == sum(pn["verdicts"].values()) == pn["uom_universe_in_ontology"] + pn["ontology_pairs_outside_uom_universe"], str(pn["verdicts"]))
S = D["sim"]["stats"]
check("sim: all node groundings resolve against 4.1", S["node_resolved"] == S["node_groundings"], f"{S['node_resolved']}/{S['node_groundings']}")
check("sim: all field groundings resolve against 4.1", S["field_resolved"] == S["field_groundings"], f"{S['field_resolved']}/{S['field_groundings']}")
check("sim: namespace cannot collide with the real sc:", all("example.invalid" in (Path(__file__).resolve().parent.parent / "sim" / f"{m['id']}.ttl").read_text() for m in D["sim"]["modules"]))
check("sim: every concept carries a grade", all(c["grade"] in ("S", "L") for c in D["sim"]["concepts"]))
check("sim: simulated concepts are grade S", all(c["grade"] == "S" for c in D["sim"]["concepts"] if c["origin"] == "simulated"))
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
