#!/usr/bin/env python3
"""Checks on the fuzzer's generator, minimiser and classifier. python3 -I xdomain/fuzz/test_fuzz.py  (X_ITE checks run when the vendored X_ITE is present)."""
import os, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model, gen, oracles, classify, minimize  # noqa
from lxml import etree

fails = []
def check(n, ok, d=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {d}" if d else ""))
    if not ok: fails.append(n)

M = model.load()
N = 200

# ---- model: the numbers the residue rests on
check("model: X3DUOM universe of containment pairs is 4,907 (FACTS N)", sum(map(len, M.edges("uom").values())) == 4907, str(sum(map(len, M.edges("uom").values()))))
R = model.residue_pairs(M)
check("model: residue recomputed from data/ is 441 pairs (FACTS N, DIRECTIONS A3)", len(R) == 441, str(len(R)))
check("model: every residue pair is allowed by acceptableNodeTypes as model.py reads it", all(M.uom_allows(c, p, f) for c, p, f, e in R))

# ---- generator
a = [gen.scene(1, i) for i in range(30)]; b = [gen.scene(1, i) for i in range(30)]
check("gen: same (seed, index) gives the same bytes", a == b)
check("gen: a different seed gives different scenes", sum(x != y for x, y in zip(a, [gen.scene(2, i) for i in range(30)])) >= 25)
def depth(xml):
    sc = etree.fromstring(xml.encode()).find("Scene")
    def d(e): return 1 + max([d(c) for c in e if isinstance(c.tag, str) and c.tag != "ROUTE"] or [0])
    return max([d(c) for c in sc if c.tag != "ROUTE"] or [0]) - 1
gs = [(i, gen.scene(3, i)) for i in range(N)]
check("gen: nesting never exceeds the requested depth (1 + i mod 5)", all(depth(x) <= 1 + i % 5 for i, x in gs))
check("gen: trees of 1 to 5 levels all occur", {depth(x) + 1 for i, x in gs} == {1, 2, 3, 4, 5}, str(sorted({depth(x) + 1 for _, x in gs})))
bad = [(i, v) for i, x in gs for v in oracles.uom(x)["violations"] if v["kind"] in ("containment", "cardinality", "no-field", "unknown-node", "unknown-attr", "range", "enum")]
check("gen (uom mode): no placement, cardinality, field, bound or enumeration X3DUOM objects to", not bad, str(bad[:2]))
V = set(model.verified_pairs())
def placements(xml):
    root = etree.fromstring(xml.encode())
    for el in root.iter():
        p = el.getparent()
        if isinstance(el.tag, str) and el.tag in M.nodes and p is not None and p.tag in M.nodes:
            yield (el.tag, p.tag, oracles.field_of(el, M))
vs = [gen.scene(4, i, "verified") for i in range(N)]
outside = [t for x in vs for t in placements(x) if t not in V]
check("gen (verified mode): every placement is one the XSD accepted in the matrix", not outside, str(outside[:3]))
def routes_ok(xml):
    root = etree.fromstring(xml.encode()); defs = {e.get("DEF"): e.tag for e in root.iter() if isinstance(e.tag, str) and e.get("DEF")}
    for r in root.iter("ROUTE"):
        f, t = defs.get(r.get("fromNode")), defs.get(r.get("toNode"))
        if not f or not t: return False
        ff, tf = M.nodes[f].fields.get(r.get("fromField")), M.nodes[t].fields.get(r.get("toField"))
        if not ff or not tf or ff.type != tf.type or ff.access not in ("outputOnly", "inputOutput") or tf.access not in ("inputOnly", "inputOutput"): return False
    return True
check("gen: every generated ROUTE joins DEFs that exist, with matching types and directions", all(routes_ok(x) for _, x in gs + list(enumerate(vs))))
check("gen: ROUTEs come after every node (the legal order)", all(all(e.tag == "ROUTE" for e in list(etree.fromstring(x.encode()).find("Scene"))[[c.tag for c in etree.fromstring(x.encode()).find("Scene")].index("ROUTE"):]) for _, x in gs if "<ROUTE" in x))
uses = sum(x.count(" USE=") for _, x in gs); defs_ = sum(x.count(" DEF=") for _, x in gs); routes = sum(x.count("<ROUTE") for _, x in gs)
check("gen: DEF, USE and ROUTE all occur", uses > 0 and defs_ > 0 and routes > 0, f"DEF {defs_}, USE {uses}, ROUTE {routes}")
check("gen: profiles other than Full occur (~20%)", 15 <= sum("profile=\"Full\"" not in x for _, x in gs) <= 70, str(sum("profile=\"Full\"" not in x for _, x in gs)))
ms = [gen.mutate(5, i) for i in range(60)]
check("mutate: deterministic", ms[:10] == [gen.mutate(5, i) for i in range(10)])
check("mutate: every mutant is well-formed and starts from a real scene", all(etree.fromstring(x.encode()) is not None and ops[0].startswith("seed:") for x, ops in ms))
oor = [(x, ops) for i in range(300) for x, ops in [gen.mutate(6, i, k=1)] if any(o.startswith("out_of_range") for o in ops)]
check("mutate: out_of_range always leaves a value X3DUOM's bounds reject", oor and all(any(v["kind"] == "range" for v in oracles.uom(x)["violations"]) for x, _ in oor), f"{len(oor)} mutants")
rf = [(x, ops) for i in range(300) for x, ops in [gen.mutate(6, i, k=1)] if "route_first" in ops]
check("mutate: route_first puts a ROUTE first in the Scene", rf and all(etree.fromstring(x.encode()).find("Scene")[0].tag == "ROUTE" for x, _ in rf), f"{len(rf)} mutants")

# ---- minimiser
keep = minimize.ddmin(20, lambda cands: [{3, 11} <= set(c) for c in cands])
check("ddmin: finds the two units a predicate needs out of 20", sorted(keep) == [3, 11], str(keep))
keep = minimize.ddmin(16, lambda cands: [7 in c for c in cands])
check("ddmin: single culprit", keep == [7], str(keep))
big = gen.wrap("<Group><Transform><Shape><Appearance><Material/></Appearance><Box size='1 2 3'/></Shape></Transform><Viewpoint/><Group><Sphere/></Group></Group><Transform/>")
calls = []
def has_box(cs):
    calls.append(len(cs)); return [("<Box" in c and "<Shape" in c) for c in cs]
small = minimize.minimize(big, has_box)
check("minimize: keeps the predicate true", has_box([small])[0])
check("minimize: drops everything else, wrappers included (Shape + Box, no attributes)", re.sub(r"\s+", "", small).endswith("<Scene><Shape><Box/></Shape></Scene></X3D>"), re.sub(r"\s+", " ", small)[60:200])
check("minimize: tests candidates in batches", max(calls) > 1, f"largest batch {max(calls)}")
check("minimize: returns the input unchanged when the predicate is false on it", minimize.minimize(big, lambda cs: [False] * len(cs)) == big)

# ---- classifier on fixed examples (no browser: X_ITE's answer is supplied)
route_first = gen.wrap("<ROUTE fromNode='T' fromField='fraction_changed' toNode='I' toField='set_fraction'/><TimeSensor DEF='T'/><PositionInterpolator DEF='I'/>")
o = oracles.python_oracles(route_first)
o["xite"] = {"warn": ["XML Parser: Unknown named or imported node 'T'."], "error": [], "routes": 0, "counts": {"TimeSensor": 1, "PositionInterpolator": 1}, "exc": None}
fs = classify.classify(route_first, o, M); bs = {f[0] for f in fs}
check("classify: ROUTE before its node = XSD-valid, fork semantic silent, X_ITE drops (the gobbler-demiurge gap)",
      o["xsd"]["valid"] and {"xsd_valid_xite_drops", "semantic_silent_drop"} <= bs and not [d for d in o["sem"]["diags"] if d["level"] == "error"], str(sorted(bs)))
proxy = gen.wrap("<Collision><Analyser containerField='proxy'/></Collision>")
o = oracles.python_oracles(proxy); fs = classify.classify(proxy, o, M)
check("classify: Analyser as Collision proxy = UOM-allows/XSD-rejects, cf-enum, and UOM's own choice type agrees with the XSD",
      any(f[0] == "uom_allows_xsd_rejects" and f[1][1] == "cf-enum" and f[1][-1] == "uom-choice-type-agrees" for f in fs), str([f[1] for f in fs]))
ok = gen.wrap("<Transform><Shape><Box/></Shape></Transform>")
o = oracles.python_oracles(ok); o["xite"] = {"warn": [], "error": [], "routes": 0, "counts": {"Transform": 1, "Shape": 1, "Box": 1}, "exc": None}
check("classify: a clean scene gives no finding", classify.classify(ok, o, M) == [])
o["xite"] = {"warn": [], "error": [], "routes": 0, "counts": {"Transform": 1, "Shape": 1}, "exc": None}
check("classify: a node X_ITE did not build is a drop", any(f[0] == "xsd_valid_xite_drops" and f[1][1:5] == ("node", "Shape", "geometry", "Box") for f in classify.classify(ok, o, M)))

# ---- X_ITE end to end (optional)
xd = Path(os.environ.get("XITE_DIR", model.REPO / "gobbler-v4" / "vendor" / "x_ite"))
if (xd / "x_ite.min.js").exists():
    X = oracles.Xite()
    r = X.run([route_first, ok])
    check("xite: 16.5.1 drops the ROUTE that precedes its node and says why", X.info.get("version") == "16.5.1" and r[0]["routes"] == 0 and any("Unknown named" in m for m in r[0]["warn"]), str(r[0]))
    check("xite: builds every node of a clean scene, silently", r[1]["counts"] == {"Transform": 1, "Shape": 1, "Box": 1} and not r[1]["warn"] and not r[1]["error"], str(r[1]))
    noisy = gen.wrap("<Group DEF='G'><Transform translation='1 2 3'><Shape><Sphere/></Shape></Transform></Group><ROUTE fromNode='T' fromField='fraction_changed' toNode='I' toField='set_fraction'/>"
                     "<Viewpoint description='v'/><TimeSensor DEF='T' loop='true'/><PositionInterpolator DEF='I' key='0 1' keyValue='0 0 0, 1 1 1'/><Background/>")
    def holds(cs):
        rs = [oracles.python_oracles(c) for c in cs]
        for q, xr in zip(rs, X.run(cs)): q["xite"] = xr
        return [any(f[0] == "semantic_silent_drop" for f in classify.classify(c, q, M)) for c, q in zip(cs, rs)]
    small = minimize.minimize(noisy, holds)
    tags = [e.tag for e in etree.fromstring(small.encode()).iter() if isinstance(e.tag, str)]
    check("minimize + xite: a padded ROUTE-first scene shrinks to ROUTE + the two nodes it names", holds([small])[0] and tags.count("ROUTE") == 1 and len(tags) <= 5, str(tags))
    X.close()
else:
    print("SKIP xite checks: no X_ITE at " + str(xd) + " (make v4-data)")

print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
