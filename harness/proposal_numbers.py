#!/usr/bin/env python3
"""Numbers for the narrowed-ranges proposal, containment fields only (initializeOnly / inputOutput); event ports (inputOnly/outputOnly) reported apart."""
import json, collections, sys
from pathlib import Path
root = Path(sys.argv[1]).expanduser(); sys.path.insert(0, str(root / "src"))
from x3d_utils.x3duom import get_x3duom
H = Path(__file__).resolve().parent.parent / "data"
X = json.loads((H / "xcheck_all.json").read_text())["rows"]; UR = {tuple(r[:3]): r[4] for r in json.loads((H / "uom_ranges.json").read_text())["rows"]}
UV = json.loads((H / "uom_universe.json").read_text()); U = get_x3duom().get_concrete_nodes()
ACC = {(p, f["name"]): f["accessType"] for p, d in U.items() for f in d["fields"]}
def cf(f): return f[3:4].lower() + f[4:] if f.startswith("has") else f
ev = lambda p, f: ACC.get((p, cf(f))) in ("inputOnly", "outputOnly")
univ = lambda f: cf(f) in ("metadata", "IS")   # universal fields: every node takes metadata, IS
sub = [r for r in X if not ev(r[1], r[2]) and not univ(r[2])]; evp = [r for r in X if ev(r[1], r[2])]; unip = [r for r in X if univ(r[2]) and not ev(r[1], r[2])]
cnt = lambda rows: collections.Counter(r[3] for r in rows)
c = cnt(sub); conf = collections.Counter()
for ch, p, f, v, e in sub:
    u = UR.get((ch, p, f))
    if v in "AR" and u in ("Y", "N"): conf[(u, v)] += 1
mv = UV["missing_verdicts"]
in_uni_A = sum(1 for ch, p, f, v, e in sub if v == "A" and UR.get((ch, p, f)) == "Y")
out = dict(containment_pairs=len(sub), event_port_pairs=len(evp), universal_field_pairs=len(unip), universal_field_verdicts=dict(cnt(unip)), verdicts=dict(c), accepted_share=round(c["A"] / (c["A"] + c["R"]), 4),
           event_port_verdicts=dict(cnt(evp)),
           uom_confusion={"allow_accept": conf[("Y", "A")], "allow_reject": conf[("Y", "R")], "deny_accept": conf[("N", "A")], "deny_reject": conf[("N", "R")]},
           uom_agreement=round((conf[("Y", "A")] + conf[("N", "R")]) / sum(conf.values()), 4), uom_allow_precision=round(conf[("Y", "A")] / (conf[("Y", "A")] + conf[("Y", "R")]), 4),
           uom_universe=UV["universe"], uom_universe_in_ontology=UV["in_ontology"], uom_universe_missing_from_ontology=UV["missing_from_ontology"], missing_verdicts=mv,
           ontology_pairs_outside_uom_universe=UV["ontology_pairs_not_in_uom_universe"],
           xsd_accepted_and_uom_allowed_total=conf[("Y", "A")] + mv.get("A", 0))
(H / "proposal_numbers.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=0))
