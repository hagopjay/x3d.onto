#!/usr/bin/env python3
"""Score fuzz_adjudicate.py outputs against the reviewers' labels (fuzz-adjudicate-labels.json): a verdict counts when it is the
final label or one the reviewers listed as defensible. Paired bare vs grounded with an exact sign test.
usage: autoscore.py RUN.jsonl [RUN.jsonl ...]"""
import json, sys, collections, math
from pathlib import Path
lab = json.loads((Path(__file__).parent / "fuzz-adjudicate-labels.json").read_text())
def sign(pr):
    up = sum(g > b for b, g in pr); dn = sum(g < b for b, g in pr); n = up + dn
    return up, dn, len(pr) - n, (round(min(1, 2 * sum(math.comb(n, j) for j in range(min(up, dn) + 1)) / 2 ** n), 4) if n else 1.0)
for p in sys.argv[1:]:
    by = collections.defaultdict(dict)
    for l in open(p): r = json.loads(l); by[r["file"]][r["arm"]] = r.get("verdict")
    res = {arm: dict(exact=sum(by[f].get(arm) == L["final"] for f, L in lab.items()), acceptable=sum(by[f].get(arm) in L["acceptable"] for f, L in lab.items())) for arm in ("bare", "grounded")}
    pairs = [(int(by[f].get("bare") in L["acceptable"]), int(by[f].get("grounded") in L["acceptable"])) for f, L in lab.items()]
    print(Path(p).name, len(lab), res, "grounded better/worse/tie/p", sign(pairs))
