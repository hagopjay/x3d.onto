#!/usr/bin/env python3
"""The other direction: pairs X3DUOM's acceptableNodeTypes allows but the ontology (as the tool reads it) does not predict. Run the XSD on them.
Universe = every concrete (child, concrete parent, node-typed field) where child or one of its ontology ancestors is in the field's acceptableNodeTypes.
Same minimal_doc/validate_xml method as xcheck_all.py. usage: uom_universe.py <x3d_mcp checkout> -> data/uom_universe.json"""
import json, sys, collections
from pathlib import Path
root = Path(sys.argv[1]).expanduser(); sys.path.insert(0, str(root / "src")); sys.path.insert(0, str(root / "evaluation"))
from validation.validate import validate_xml            # noqa
from x3d_utils.x3duom import get_x3duom                  # noqa
from cross_validate_ontology import minimal_doc          # noqa
H = Path(__file__).resolve().parent.parent / "data"
M = json.loads((H / "explorer.json").read_text()); N = {n["id"]: n for n in M["nodes"]}
U = get_x3duom().get_concrete_nodes()
ACC = {(p, f["name"]): f["accessType"] for p, d in U.items() for f in d["fields"]}
KEEP = ("initializeOnly", "inputOutput")   # containment fields; inputOnly/outputOnly are event ports (addChildren, removeChildren), reported separately
onto = {}
for n in M["nodes"]:
    for (p, f), v in zip(n["lp"], n["lpv"]):
        if p in U and n["id"] in U:
            cf = f[3:4].lower() + f[4:] if f.startswith("has") else f
            onto[(n["id"], p, cf)] = v
uni = []
for p, d in U.items():
    for f in d["fields"]:
        a = f.get("acceptableNodeTypes")
        if not a or f["name"] in ("IS", "metadata") or f["type"] not in ("SFNode", "MFNode"): continue
        if f["accessType"] not in KEEP: continue
        rng = set(a.split("|"))
        for c in U:
            if ({c} | set(N[c]["ancs"])) & rng: uni.append((c, p, f["name"]))
onto_all = len(onto); onto = {k: v for k, v in onto.items() if (ACC.get((k[1], k[2])) in KEEP or ACC.get((k[1], k[2])) is None) and k[2] not in ("metadata", "IS")}
inO = [t for t in uni if t in onto]; miss = [t for t in uni if t not in onto]
out = collections.Counter(); rows = []
for c, p, f in miss:
    dcf = U[c].get("containerField"); cfa = None if f == dcf else f
    v = validate_xml(minimal_doc(p, c, cfa, U[p].get("containerField")))
    k = "A" if v["valid"] else ("R" if f"'{c}'" in v["errors"][0] else "I"); out[k] += 1
    rows.append([c, p, f, k])
onto_not_uom = [k for k in onto if k not in set(uni)]
res = dict(event_port_and_universal_pairs_excluded=onto_all - len(onto), universe=len(uni), in_ontology=len(inO), missing_from_ontology=len(miss), missing_verdicts=dict(out), ontology_pairs=len(onto), ontology_pairs_not_in_uom_universe=len(onto_not_uom),
           note="universe uses node-typed fields with acceptableNodeTypes, excluding IS and metadata; ontology keys are (child, parent, containerField) of the concrete pairs in xcheck_all", rows=rows)
(H / "uom_universe.json").write_text(json.dumps(res, separators=(",", ":")))
print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
print(collections.Counter(r[1] for r in rows if r[3] == "A").most_common(6)); print(rows[:4])
