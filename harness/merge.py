#!/usr/bin/env python3
"""Merge 4.1 model + 4.0 delta + XSD verdict matrix + SIM concepts into data/explorer.json (the explorer's single input)."""
import json, collections
from pathlib import Path
H = Path(__file__).resolve().parent.parent / "data"
B = json.loads((H / "ontology41.json").read_text()); A = json.loads((H / "ontology.json").read_text())
X = json.loads((H / "xcheck_all.json").read_text()); S = json.loads((H / "sim.json").read_text())
mA = json.loads((H / "manifest.json").read_text()); mB = json.loads((H / "manifest.ontology41.json").read_text())
A_ = {n["id"]: n for n in A["nodes"]}
UR = json.loads((H / "uom_ranges.json").read_text())
uflag = {(c, pp, f): u for c, pp, f, v, u in UR["rows"]}
verdict = {(c, p, f): v for c, p, f, v, e in X["rows"]}; errs = {(c, p, f): e for c, p, f, v, e in X["rows"] if e}
cnt = collections.defaultdict(lambda: [0, 0, 0])
for c, p, f, v, e in X["rows"]: cnt[c]["ARI".index(v)] += 1
for n in B["nodes"]:
    o = A_.get(n["id"])
    n["new"] = o is None
    n["lpv"] = "".join(verdict.get((n["id"], p, f), "-") for p, f in n["lp"])
    n["lpu"] = "".join(uflag.get((n["id"], p, f), "-") for p, f in n["lp"])
    n["xa"], n["xr"], n["xi"] = cnt.get(n["id"], [0, 0, 0])
    if o:
        p0, p1 = {p for p, _ in o["lp"]}, {p for p, _ in n["lp"]}
        n["gained"] = sorted(p1 - p0); n["lost"] = sorted(p0 - p1)
        n["fadd"] = sorted(set(n["fields"]) - set(o["fields"])); n["frm"] = sorted(set(o["fields"]) - set(n["fields"]))
        n["chg"] = bool(n["gained"] or n["lost"] or n["fadd"] or n["frm"])
    else:
        n["gained"] = n["lost"] = n["fadd"] = n["frm"] = []; n["chg"] = False
        n["x40"] = None
    n["errs"] = {f"{p}|{f}": errs[(n["id"], p, f)] for p, f in n["lp"] if (n["id"], p, f) in errs}
# new classes were laid out in the 4.1 layout already (build.py ran on 4.1); the explorer uses 4.1 layout throughout
ten = ["Sphere", "Box", "Material", "Appearance", "Coordinate", "PointLight", "TimeSensor", "Transform", "Shape", "ImageTexture"]
table = {c: [sum(cnt[c]), cnt[c][0], cnt[c][1], cnt[c][2]] for c in ten}
doc = {"Sphere": (10, 5, 3, 2), "Box": (10, 5, 3, 2), "Material": (3, 2, 0, 1), "Appearance": (2, 2, 0, 0), "Coordinate": (15, 14, 1, 0), "PointLight": (57, 24, 27, 6),
       "TimeSensor": (57, 24, 27, 6), "Transform": (57, 21, 30, 6), "Shape": (59, 22, 30, 7), "ImageTexture": (78, 31, 42, 5)}
reproduced = all(tuple(table[c]) == doc[c] for c in ten)
tot = [sum(table[c][i] for c in ten) for i in range(4)]
B["xcheck"] = dict(src="harness/xcheck_all.py: 4.1 ontology vs XSD 4.1 via x3d_mcp validate_xml (method of evaluation/cross_validate_ontology.py)",
                   table=table, doc_table={k: list(v) for k, v in doc.items()}, doc_totals=dict(predicted=348, accepts=150, rejects=163, inconclusive=35),
                   ten_totals=dict(predicted=tot[0], accepts=tot[1], rejects=tot[2], inconclusive=tot[3]), reproduced=reproduced,
                   all=dict(pairs=X["pairs"], A=X["totals"]["A"], R=X["totals"]["R"], I=X["totals"]["I"], seconds=X["seconds"], schema=X["schema"]))
B["uom"] = dict(confusion=UR["confusion"], agreement=UR["agreement"], ontology_only_precision=UR["ontology_only_precision"], uom_precision=UR["uom_precision"],
                containerfield_enum_rejects=202, rejects_total=X["totals"]["R"], agreement_excl_cf_enum=0.9502)
B["v40"] = dict(stats=A["stats"], manifest=mA)
B["manifest"] = mB
B["manifest40"] = mA
B["sim"] = S
tenpairs = lambda M_: (sum(len(n["lp"]) for n in M_["nodes"] if n["id"] in ten), sum(1 for n in M_["nodes"] if n["id"] in ten for d, _ in n["lp"] if d in {m["id"] for m in M_["nodes"] if m["kind"] == "concrete"}))
B["pairs10"] = dict(v40=tenpairs(A), v41=tenpairs(B))
B["delta"] = dict(new=[n["id"] for n in B["nodes"] if n["new"]], changed=sum(1 for n in B["nodes"] if n["chg"]),
                  new_props=sorted(set(B["props"]) - set(A["props"])), removed_props=sorted(set(A["props"]) - set(B["props"])),
                  triples=(A["stats"]["triples"], B["stats"]["triples"]))
(H / "explorer.json").write_text(json.dumps(B, separators=(",", ":"), sort_keys=True))
print("reproduced doc 10-type table:", reproduced, "| ten totals", tot, "| all", B["xcheck"]["all"], "| new", B["delta"]["new"], "| changed", B["delta"]["changed"])
print("bytes", (H / "explorer.json").stat().st_size)
