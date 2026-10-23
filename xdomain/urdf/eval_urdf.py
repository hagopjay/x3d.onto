#!/usr/bin/env python3
"""Fault-injection evaluation for the URDF checker, in the style of README (28)'s USE-check scale run: false alarms on clean models, detection of injected faults by level.
usage: python3 eval_urdf.py (needs lxml) -> ../../out/xdomain_urdf.json"""
import json, sys, time, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from corpus import CORPUS; from mutate import F; from urdf_check import check, RULES; from repair import repair
OUT = Path(__file__).resolve().parent.parent.parent / "out"
clean = {k: v() for k, v in CORPUS.items()}
fa = {k: [d.rule for d in check(x).diags if d.severity == "error"] for k, x in clean.items()}
res = dict(corpus=list(CORPUS), clean_errors=fa, clean_warnings={k: [d.rule for d in check(x).diags if d.severity == "warning"] for k, x in clean.items()}, faults={}, rows=[])
tot = collections.Counter(); lat = []
for fid, (level, desc, fn) in F.items():
    c = collections.Counter()
    for k, x in clean.items():
        y = fn(x)
        if y is None or y == x: c["n/a"] += 1; continue
        c["n"] += 1
        r1, r2 = check(y, 1), check(y, 2); lat.append(r2.ms)
        e1 = len(r1.errors); e2 = len(r2.errors); w2 = sum(d.severity == "warning" for d in r2.diags)
        verdict = "L0" if any(d.rule == "U-00" for d in r2.errors) else "L1" if e1 else ("L2" if e2 else ("contact" if any(d.rule == "U-16" for d in r2.diags) else ("warn" if w2 else "missed")))
        c[verdict] += 1
        rows = [d.rule for d in r2.errors] or [d.rule for d in r2.diags if d.severity == "warning"]
        fixed, applied = repair(y); r3 = check(fixed, 2)
        before = e2 or w2; after = len(r3.errors) if e2 else sum(d.severity == "warning" for d in r3.diags)
        rep = ("fixed" if applied and after == 0 else ("partial" if applied and after < before else "no-repair"))
        if applied: c["repair_" + rep] += 1
        res["rows"].append(dict(fault=fid, robot=k, verdict=verdict, rules=sorted(set(rows)), repair=rep if applied else None))
    res["faults"][fid] = dict(level=level, desc=desc, **c); tot.update({k: v for k, v in c.items() if k != "n/a"})
# damage check: repair on clean files must be a no-op in substance
noop = {k: (repair(x)[1] == []) for k, x in clean.items()}
res.update(totals=dict(tot), repair_noop_on_clean=noop, latency_ms=dict(mean=round(sum(lat) / len(lat), 2), max=round(max(lat), 2), n=len(lat)), rules=[dict(id=a, rung=b, what=c, x3d=d) for a, b, c, d in RULES])
(OUT / "xdomain_urdf.json").write_text(json.dumps(res, indent=1))
print("clean errors:", {k: v for k, v in fa.items() if v}, "| clean warnings:", res["clean_warnings"])
for fid, v in res["faults"].items(): print(fid, v["level"], v["desc"][:40].ljust(40), {k: n for k, n in v.items() if k not in ("level", "desc")})
print(res["totals"], res["latency_ms"], "repair noop on clean:", all(noop.values()))
