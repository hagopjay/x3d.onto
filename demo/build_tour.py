#!/usr/bin/env python3
"""Builds demo/tour-data.json for the curator tour, tooltips and film captions. Every number is computed from a file here (or sources.json) and recorded with its source;
any number in the final text that is not a recorded fact fails the build (exit 1). usage: python3 -I build_tour.py"""
import json, math, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
D = json.loads((ROOT / "data" / "explorer.json").read_text()); CR = json.loads((ROOT / "out" / "constellation_run.json").read_text())
UR = json.loads((ROOT / "out" / "xdomain_urdf.json").read_text()); GL = json.loads((ROOT / "out" / "xdomain_gltf.json").read_text()); COMP = json.loads((ROOT / "data" / "components.json").read_text())
SRC = json.loads((HERE / "sources.json").read_text())["facts"]; N = {n["id"]: n for n in D["nodes"]}
R = 8.0; MAXD = D["stats"]["max_depth"]; RB = 5.5
def sph(n): lon = n["a"]; lat = math.radians(70 - n["d"] * 140 / MAXD); return [round(R * math.cos(lat) * math.cos(lon), 2), round(R * math.sin(lat), 2), round(R * math.cos(lat) * math.sin(lon), 2)]
F = {}
def f(key, val, src): F[key] = (str(val), src); return str(val)
sh = N["Shape"]; tb = D["xcheck"]["table"]["Shape"]; xa = D["xcheck"]["all"]
f("classes", D["stats"]["classes"], "data/explorer.json stats.classes"); f("new", len(D["delta"]["new"]), "data/explorer.json delta.new"); f("onto", "4.1", "X3dOntology4.1.ttl")
f("shape_parents", len(sh["lp"]), "data/explorer.json Shape.lp"); f("shape_pred", tb[0], "xcheck.table.Shape"); f("shape_acc", tb[1], "xcheck.table.Shape"); f("shape_rej", tb[2], "xcheck.table.Shape"); f("shape_inc", tb[3], "xcheck.table.Shape")
f("pairs", f"{xa['pairs']:,}", "xcheck.all.pairs"); f("pairs_acc", f"{xa['A']:,}", "xcheck.all.A"); f("pairs_rej", f"{xa['R']:,}", "xcheck.all.R"); f("pairs_inc", f"{xa['I']:,}", "xcheck.all.I")
f("kb", round(CR["bytes"] / 1000), "out/constellation_run.json bytes"); f("val_s", f"{CR['validate_x3d_ms'] / 1000:.1f}", "out/constellation_run.json validate_x3d_ms"); f("call_ms", f"{CR['nano_call_ms']['p50']:.1f}", "out/constellation_run.json nano_call_ms.p50")
for k, v in SRC.items():
    for i, tok in enumerate(re.findall(r"\d+(?:\.\d+)?", v["text"])): F[f"{k}_{i}"] = (tok, f"demo/sources.json {k} ({v['grade']})")
f("ncomp", len(COMP), "data/components.json"); best = max(COMP, key=lambda c: c[6] if c[6] is not None else 0); worst = min(COMP, key=lambda c: c[6] if c[6] is not None else 9)
f("comp_best", best[0], "components.json"); f("comp_best_pct", round(best[6] * 100, 1), "components.json"); f("comp_worst", worst[0], "components.json"); f("comp_worst_pct", round(worst[6] * 100, 1), "components.json")
phys = next(c for c in COMP if c[0] == "RigidBodyPhysics"); f("phys_pct", round(phys[6] * 100, 1), "components.json RigidBodyPhysics")
f("u_faults", len(UR["faults"]), "out/xdomain_urdf.json"); f("u_mut", UR["totals"]["n"], "out/xdomain_urdf.json totals.n")
for k in ("L0", "L1", "L2", "warn", "contact"): f("u_" + k, UR["totals"][k], f"out/xdomain_urdf.json totals.{k}")
f("g_faults", len(GL["faults"]), "out/xdomain_gltf.json"); f("g_mut", GL["totals"]["n"], "out/xdomain_gltf.json totals.n")
ge = GL["totals"]["khronos_error_total"]; f("g_err", ge, "out/xdomain_gltf.json khronos_error_total"); f("g_err_pct", round(100 * ge / GL["totals"]["n"], 1), "derived"); f("g_warn", GL["totals"]["khronos-warning"], "out/xdomain_gltf.json"); f("g_base", GL["totals"]["baseline_total"], "out/xdomain_gltf.json baseline_total")
f("uom_agree", round(D["uom"]["agreement"] * 100, 1), "data/explorer.json uom.agreement")
def evals(dom):
    p = ROOT / "xdomain" / "eval-plan" / "runs" / f"{dom}-gemini-3.8-flash.jsonl"
    if not p.exists(): return None
    rows = [json.loads(l) for l in p.read_text().splitlines()]; a0 = [r for r in rows if r["arm"] == "A0"]; a2 = [r for r in rows if r["arm"] == "A2-final"]
    return dict(a0=round(100 * sum(r["valid"] for r in a0) / len(a0)), a2=round(100 * sum(r["valid"] for r in a2) / len(a2)), n=len(a0)) if len(a0) >= 30 and a2 else None
EV = {d: evals(d) for d in ("x3d", "urdf", "gltf")}
for d, e in EV.items():
    if e: f(f"ev_{d}_a0", e["a0"], f"runs/{d}"); f(f"ev_{d}_a2", e["a2"], f"runs/{d}"); f(f"ev_{d}_n", e["n"], f"runs/{d}")
T = lambda s: re.sub(r"\{(\w+)\}", lambda m: F[m.group(1)][0], s)
newn = [n for n in D["delta"]["new"] if N[n]["kind"] == "concrete"]
gs = sph(N["GaussianSplats"]); shp = sph(sh); ph = 2 * math.pi * 2 / 7; st2 = [round(-26 + 2.2 * RB * math.cos(ph), 2), 0, round(-2.2 * RB * math.sin(ph), 2)]
out_ = lambda p, k: [round(c * k, 2) for c in p]
STOPS = [
 dict(id=1, title="Welcome", cam=[0, 16, 100], tgt=[0, 0, 0], halo=None, text=T("Three modules sit in a row: the loop, the ontology shell and three domain rings. Press Next, or hover anything for its source."), look="Everything on screen is a toy layout; the numbers are real and carry their grade.", src="demo/DEMO-SPEC.md", grade="L"),
 dict(id=2, title="The map: X3D Ontology {onto}".replace("{onto}", "4.1"), cam=[0, 10, 32], tgt=[0, 0, 0], halo=None, text=T("{classes} classes on a glass shell: longitude is the layout angle, latitude is the class's depth. Squares are abstract types, spheres are concrete nodes, colours are families."), look="Hover a class: definition, family, how many parents the ontology predicts, and what the XSD said about them.", src="data/explorer.json (364 classes, Web3D draft dated 29 September 2026)", grade="C"),
 dict(id=3, title="Born in 4.1", cam=out_(gs, 1.9), tgt=gs, halo=dict(at=gs, s=1.1), text=T("{new} classes are new in 4.1, including " + ", ".join(newn[:5]) + ". They pulse green."), look="GaussianSplats is here: radiance fields became a first-class X3D node.", src="data/explorer.json delta.new", grade="C"),
 dict(id=4, title="Shape and its parents", cam=out_(shp, 1.85), tgt=shp, halo=dict(at=shp, s=1.0), text=T("The ontology predicts {shape_parents} parent placements for Shape. For the {shape_pred} with a concrete parent the XSD accepts {shape_acc}, rejects {shape_rej}, and {shape_inc} are inconclusive."), look="Arcs from Shape: green accepted, red rejected, amber inconclusive, blue abstract. The ontology is a map, not a gate.", src="harness/xcheck_all.py (4.1 ontology vs XSD 4.1; same method as the doc's table, reproduced row by row)", grade="C"),
 dict(id=5, title="The loop", cam=[-26, 22, 34], tgt=[-26, 0, 0], halo=dict(at=[-26, 0, 0], s=0.0), text="A packet circles seven stations. It turns red at x3d_mcp, a report packet flies back to the agent, a repair turns it green, and the tether stamps the result.", look="Watch the colour: white spec, blue draft, red invalid, amber report, green repaired, gold stamp.", src="demo/DEMO-SPEC.md section 2", grade="L"),
 dict(id=6, title="x3d_mcp, the exact oracle", cam=[st2[0] + 4, 14, st2[2] + 18], tgt=st2, halo=dict(at=st2, s=2.4), text=T("Whole-scene validation of this {kb} KB demo: {val_s} s. A median tool call: {call_ms} ms. In the doc's E1 run, first-try validity went {e1_first_try_0}% to {e1_first_try_1}% with two retrieved examples, and about {e1_after_loop_0}% after report-guided repair."), look="Checks are cheap, deterministic and line-located: that is what makes a loop possible.", src="out/constellation_run.json; DOC.md section 2 (E1)", grade="C"),
 dict(id=7, title="Domain ring: X3D's components", cam=[26, 20, 40], tgt=[26, 0, 0], halo=dict(at=[26, 0, 0], s=0.0), text=T("{ncomp} components, each its own field. The XSD accepts {comp_best_pct}% of the ontology's predictions for {comp_best} but only {comp_worst_pct}% for {comp_worst} and {phys_pct}% for RigidBodyPhysics."), look="Bead colour is the accepted share. The more specialist the vocabulary, the less the supertype ranges say (my reading, L).", src="data/components.json", grade="C"),
 dict(id=8, title="URDF and glTF rings", cam=[26, 12, 44], tgt=[26, 0, 0], halo=None, text=T("URDF: {u_faults} fault kinds, {u_mut} mutants (my own rules, L). glTF: {g_faults} kinds, {g_mut} mutants; the Khronos validator flags {g_err} ({g_err_pct}%) at error level, and {g_warn} of the {g_mut} mutants (from three fault kinds) only as warnings."), look="Hover a bead for the fault. Orange and amber beads are the ones a gate that counts only errors would let through.", src="out/xdomain_urdf.json, out/xdomain_gltf.json", grade="C"),
 dict(id=9, title="Model results", cam=[26, -6, 34], tgt=[26, -12.8, 0], halo=dict(at=[26, -12.8, 0], s=5.0), text=("Pillars: first try in blue, after the report loop in green, for each domain. " + (T("X3D {ev_x3d_a0}% to {ev_x3d_a2}%, URDF {ev_urdf_a0}% to {ev_urdf_a2}%, glTF {ev_gltf_a0}% to {ev_gltf_a2}% (Gemini flash, n={ev_x3d_n} first tries each).") if all(EV.values()) else "The evaluation is still running: the pillars are ghosts until the runs finish.")), look="The same loop, three domains, one model.", src="xdomain/eval-plan/runs", grade="C" if all(EV.values()) else "L"),
 dict(id=10, title="Assemble", cam=None, tgt=[0, 0, 0], halo=None, action="assemble", text="The loop and the rings are drawn into the shell. Captions fade, the star flares, a shockwave rolls out.", look="One sphere: the ontology proposes, shapes dispose, the validator gates.", src="demo/DEMO-SPEC.md section 4", grade="L"),
 dict(id=11, title="What is not here", cam=[0, 8, 34], tgt=[0, 0, 0], halo=None, action="orbit", text="No Shroud content and no simulated sc: layer. Layout, colours and motion are display choices. Everything is private until 2027-01-01.", look="Use the buttons to replay the film, jump to a stop, or roam freely.", src="demo/README.md", grade="L"),
]
FILM = [(0, "Ontology Dyson sphere", "a toy, built through x3d_mcp"), (7, "The loop", "spec, agent, validator, Blender, runtime, verdict, tether"), (26, "The map", T("{classes} classes of X3D Ontology 4.1, {new} new")), (38, "Three domains", "X3D, URDF and glTF through the same loop"), (44, "Assemble", "one sphere"), (60, "Orbit", "ontology proposes, shapes dispose, the validator gates"), (72, "Press Tour to explore", "hover anything for its source")]
STATION = [("spec", "X3DUOM: the machine-readable spec; XSD, ontology and tool text are generated from it.", "C"), ("agent", "A model drafts the scene.", "L"), ("x3d_mcp", T("Validate, explain, repair. Whole-scene validation {val_s} s; median call {call_ms} ms."), "C"), ("Blender + fork", "x3d-blender-io round trip: provenance kept in " + T("{provenance_kept_0}") + " of " + T("{provenance_kept_1}") + " scenes (doc).", "C"), ("runtime", "X_ITE render and frame check: valid is not visible.", "L"), ("verdict", "Valid, visible, complete: three tests.", "L"), ("tether", "x3dprov: a hash chain inside the file; edit after the last step reads 'stale'.", "C")]
cat = {"L0": "parse", "L1": "structure", "baseline": "structure", "L2": "semantics", "khronos-error": "Khronos error", "warn": "warning only", "khronos-warning": "warning only", "contact": "contact rule"}
def verdict(v):
    for k in ("L0", "L1", "L2", "contact", "warn", "baseline", "khronos-error", "khronos-warning"):
        if v.get(k): return k
BEADS = dict(X3D=[dict(name=c[0], nodes=c[1], new=c[2], pct=round(100 * c[6], 1) if c[6] is not None else None, agree=round(100 * c[7], 1) if c[7] is not None else None) for c in COMP],
             URDF=[dict(id=k, desc=v["desc"], n=v["n"], catcher=cat[verdict(v)], repaired=v.get("repair_fixed", 0)) for k, v in UR["faults"].items()],
             glTF=[dict(id=k, desc=v["desc"], n=v["n"], catcher=cat["L0" if k == "G25" else verdict(v)], codes=sorted(GL["codes"].get(k, {}))[:2]) for k, v in GL["faults"].items()])
PILL = {d: EV[k] for d, k in (("X3D", "x3d"), ("URDF", "urdf"), ("glTF", "gltf"))}
CL = {n["id"]: dict(kind=n["kind"], fam=n["fam"], comp=n["comp"], lvl=n["lvl"], d=n["d"], nf=n["nf"], lp=len(n["lp"]), xa=n["xa"], xr=n["xr"], xi=n["xi"], new=n["new"], defn=n["defn"][:200], kids=n["kids"]) for n in D["nodes"]}
out = dict(stops=STOPS, film=FILM, stations=STATION, beads=BEADS, pillars=PILL, classes=CL, facts={k: list(v) for k, v in F.items()})
strings = [x for st in STOPS for x in (st["title"], st["text"], st["look"])] + [c for _, a_, b_ in FILM for c in (a_, b_)] + [t for _, t, _g in STATION]
bad = []; known = {v[0] for v in F.values()} | {"2027", "01"}   # embargo date is literal
for sx in strings:
    for m in re.finditer(r"(?<![A-Za-z0-9_.\-])(\d+(?:[.,]\d+)?)(?![A-Za-z0-9_])", sx):
        if m.group(1) not in known: bad.append((m.group(1), sx[:60]))
(HERE / "tour-data.json").write_text(json.dumps(out, separators=(",", ":")))
(ROOT / "out" / "demo_tour_facts.json").write_text(json.dumps(dict(unexplained=bad, facts=out["facts"]), indent=1))
print("tour-data.json", len(json.dumps(out)) // 1024, "KB; facts", len(F), "; unexplained numbers:", sorted(set(bad))); sys.exit(1 if bad else 0)
