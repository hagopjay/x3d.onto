#!/usr/bin/env python3
"""Cross-check EVERY concrete (parent, field, child) the 4.1 ontology predicts against the 4.1 XSD, using x3d_mcp's own
minimal_doc / validate_xml (read-only imports). Extends the doc's 10-type run to all concrete nodes.
Verdicts follow evaluation/cross_validate_ontology.py exactly: accept = valid; reject = invalid with the child named in the first error;
inconclusive = invalid for another reason (harness could not place the parent).
usage: xcheck_all.py <x3d_mcp checkout> [out.json]   (that checkout's .venv python)"""
import json, sys, time
from pathlib import Path
root = Path(sys.argv[1]).expanduser()
sys.path.insert(0, str(root / "src")); sys.path.insert(0, str(root / "evaluation"))
from validation.validate import validate_xml            # noqa
from x3d_utils.x3duom import get_x3duom                  # noqa
from cross_validate_ontology import minimal_doc          # noqa
HERE = Path(__file__).resolve().parent.parent
M = json.loads((HERE / "data" / "ontology41.json").read_text())
out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "data" / "xcheck_all.json"
nodes = get_x3duom().get_concrete_nodes()
rows, t0, done = [], time.time(), 0
kids = [n for n in M["nodes"] if n["id"] in nodes]
total = sum(1 for n in kids for d, _ in n["lp"] if d in nodes)
for n in kids:
    child = n["id"]; default_cf = nodes[child].get("containerField")
    for parent, field in n["lp"]:
        if parent not in nodes: continue
        cf = field[3:4].lower() + field[4:] if field.startswith("has") else field
        cf_attr = None if cf == default_cf else cf
        doc = minimal_doc(parent, child, cf_attr, nodes[parent].get("containerField"))
        v = validate_xml(doc)
        if v["valid"]: verdict, err = "A", ""
        elif f"'{child}'" in v["errors"][0]: verdict, err = "R", v["errors"][0][:140]
        else: verdict, err = "I", v["errors"][0][:140]
        rows.append([child, parent, field, verdict, err]); done += 1
    if len(rows) % 500 < len(n["lp"]): print(f"{done}/{total} {time.time()-t0:.0f}s", flush=True)
summ = {"A": 0, "R": 0, "I": 0}
for r in rows: summ[r[3]] += 1
ten = ["Sphere", "Box", "Material", "Appearance", "Coordinate", "PointLight", "TimeSensor", "Transform", "Shape", "ImageTexture"]
t10 = {"A": 0, "R": 0, "I": 0}
for r in rows:
    if r[0] in ten: t10[r[3]] += 1
res = dict(schema="XSD 4.1 via x3d_mcp validate_xml", ontology_sha256=json.loads((HERE / "data" / "manifest.ontology41.json").read_text())["input_sha256"],
           seconds=round(time.time() - t0, 1), pairs=len(rows), totals=summ, ten_type_totals=t10, rows=rows)
out.write_text(json.dumps(res, separators=(",", ":")))
print(json.dumps({k: res[k] for k in ("seconds", "pairs", "totals", "ten_type_totals")}))
