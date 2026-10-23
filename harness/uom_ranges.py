#!/usr/bin/env python3
"""Does X3DUOM's own `acceptableNodeTypes` predict the XSD verdicts better than the ontology's supertype ranges?
For every verdict row (child, parent, ontology-field) take the containerField the XSD check used, read the parent's field of that name in X3DUOM,
and test whether the child, or any of its ontology ancestors, appears in acceptableNodeTypes. Read-only on x3d_mcp.
usage: uom_ranges.py <x3d_mcp checkout> (that checkout's .venv python) -> data/uom_ranges.json"""
import json, sys, collections
from pathlib import Path
root = Path(sys.argv[1]).expanduser(); sys.path.insert(0, str(root / "src"))
from x3d_utils.x3duom import get_x3duom  # noqa
H = Path(__file__).resolve().parent.parent / "data"
M = json.loads((H / "ontology41.json").read_text()); X = json.loads((H / "xcheck_all.json").read_text())
N = {n["id"]: n for n in M["nodes"]}; U = get_x3duom().get_concrete_nodes()
acc = {}
for p, d in U.items():
    acc[p] = {f["name"]: set(f["acceptableNodeTypes"].split("|")) for f in d["fields"] if f.get("acceptableNodeTypes")}
rows, conf = [], collections.Counter()
for c, p, f, v, e in X["rows"]:
    cf = f[3:4].lower() + f[4:] if f.startswith("has") else f
    cf = cf if cf in acc.get(p, {}) else (U[c].get("containerField") if U[c].get("containerField") in acc.get(p, {}) else cf)
    rng = acc.get(p, {}).get(cf)
    if rng is None: u = "?"
    else:
        names = {c} | set(N[c]["ancs"]); u = "Y" if names & rng else "N"
    rows.append([c, p, f, v, u])
    if v in "AR" and u in "YN": conf[(u, v)] += 1
tp, fp, fn, tn = conf[("Y", "A")], conf[("Y", "R")], conf[("N", "A")], conf[("N", "R")]
unk = sum(1 for r in rows if r[4] == "?" and r[3] in "AR")
res = dict(rows=rows, confusion=dict(uom_yes_xsd_accepts=tp, uom_yes_xsd_rejects=fp, uom_no_xsd_accepts=fn, uom_no_xsd_rejects=tn, no_uom_field_info=unk),
           agreement=round((tp + tn) / max(1, tp + tn + fp + fn), 4), ontology_only_precision=round(X["totals"]["A"] / (X["totals"]["A"] + X["totals"]["R"]), 4),
           uom_precision=round(tp / max(1, tp + fp), 4))
(H / "uom_ranges.json").write_text(json.dumps(res, separators=(",", ":")))
print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
