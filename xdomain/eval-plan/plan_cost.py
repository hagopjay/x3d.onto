#!/usr/bin/env python3
"""Cost model for the model-driven evaluation. Every assumption is a named constant; change them and re-run. NOTHING here calls a model.
Prices are the ASSUMPTIONS already in shroud-artifacts/tools/vertex.py (flash class 0.75 in / 3.75 out per 1M tokens; pro class 2.5 / 15), which the ledger itself calls upper-bound style, not a billing export.
usage: python3 plan_cost.py -> prints markdown; writes plan_cost.json"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "gltf"))
import importlib.util
def load(n, p): s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
import prompts as P
uc = load("uc", HERE.parent / "urdf" / "corpus.py"); gc = load("gc", HERE.parent / "gltf" / "corpus.py")
CPT = {"urdf": 3.4, "gltf": 2.5}                 # characters per token: XML ~3.4; JSON with base64 data ~2.5 (assumption)
THINK = {"flash": 1500, "pro": 3000}              # hidden reasoning tokens counted as output by vertex.py (assumption; Gemini thinking is billed as output)
PRICE = {"flash": (0.75, 3.75), "pro": (2.5, 15.0)}
# doc size per task, from the corpus: URDF ~ links * per-link chars (measured on the 6 corpus robots); glTF by tier from corpus docs
per_link = sum(len(f()) / max(1, f().count("<link ")) for f in uc.CORPUS.values()) / len(uc.CORPUS)
gl = {"A": 700, "B": (len(json_ := __import__("json").dumps(gc.tri())) + len(__import__("json").dumps(gc.cube()))) / 2, "C": len(__import__("json").dumps(gc.animated())) * 1.3}
urdf_chars = [t[3]["links"] * per_link for t in P.URDF]; gltf_chars = [gl[t[1]] for t in P.GLTF]
task_tok = 60                                      # the task sentence and instruction
FEWSHOT = {"urdf": (len(uc.arm2()) + len(uc.mobile())) / CPT["urdf"], "gltf": (len(__import__("json").dumps(gc.tri())) + len(__import__("json").dumps(gc.hierarchy()))) / CPT["gltf"]}
VERB = 1.5                                         # models write pretty-printed, commented documents: assume 1.5x the compact corpus size (assumption)
REPORT_TOK = 350                                   # eight diagnostics with fixes
def per_call(dom, mdl):
    ch = urdf_chars if dom == "urdf" else gltf_chars; doc = VERB * sum(ch) / len(ch) / CPT[dom]
    return dict(doc=doc, a0_in=task_tok, a1_in=task_tok + FEWSHOT[dom], loop_in=task_tok + doc + REPORT_TOK, out=doc + THINK[mdl])
def cost(dom, mdl, prompts, samples, fail0, surv, arms=("A0", "A1", "A2", "A3"), rounds=3, upper=False):
    c = per_call(dom, mdl); n = prompts * samples; pin, pout = PRICE[mdl]; calls = 0; tin = tout = 0.0
    def add(k, i, o): nonlocal calls, tin, tout; calls += k; tin += k * i; tout += k * o
    if "A0" in arms or "A2" in arms or "A3" in arms: add(n, c["a0_in"], c["out"])
    if "A1" in arms: add(n, c["a1_in"], c["out"])
    f = 1.0 if upper else fail0                    # share of first tries that fail (upper bound: all fail, every round)
    for arm in ("A2", "A3"):
        if arm not in arms: continue
        alive = f
        for r in range(rounds):
            add(n * alive, c["loop_in"] if arm == "A2" else c["a0_in"], c["out"]); alive = alive * (1.0 if upper else surv)
    return dict(calls=round(calls), usd=round((tin * pin + tout * pout) / 1e6, 2), tin=round(tin), tout=round(tout))
S = [("pilot", 5, 1, ("A0", "A2")), ("lean", 20, 2, ("A0", "A1", "A2", "A3")), ("full", 20, 3, ("A0", "A1", "A2", "A3"))]
FAIL = {"low 30%": .30, "mid 55%": .55, "high 80%": .80}; SURV = .5
out = {"assumptions": dict(chars_per_token=CPT, thinking_tokens=THINK, price_per_M=PRICE, loop_survival=SURV, verbosity_factor=VERB, report_tokens=REPORT_TOK, per_link_chars=round(per_link), gltf_doc_chars={k: round(v) for k, v in gl.items()}), "scenarios": {}}
print("| scenario | model | domain | calls (expected, mid) | expected USD low / mid / high failure | upper bound USD |\n|---|---|---|---|---|---|")
for name, npr, ns, arms in S:
    for mdl in ("flash", "pro"):
        if name != "pilot" and mdl == "pro" and name == "full": continue
        tot = {k: 0 for k in FAIL}; tot_up = 0; calls = 0
        for dom in ("urdf", "gltf"):
            for k, f in FAIL.items(): tot[k] += cost(dom, mdl, npr, ns, f, SURV, arms)["usd"]
            tot_up += cost(dom, mdl, npr, ns, 1, SURV, arms, upper=True)["usd"]; calls += cost(dom, mdl, npr, ns, .55, SURV, arms)["calls"]
        out["scenarios"][f"{name}-{mdl}"] = dict(calls_mid=calls, usd={k: round(v, 2) for k, v in tot.items()}, upper=round(tot_up, 2))
        print(f"| {name} ({npr} prompts x {ns} samples, arms {'+'.join(arms)}) | {mdl} | both | {calls} | ${tot['low 30%']:.2f} / ${tot['mid 55%']:.2f} / ${tot['high 80%']:.2f} | ${tot_up:.2f} |")
(HERE / "plan_cost.json").write_text(json.dumps(out, indent=1))
c = per_call("urdf", "flash"); g = per_call("gltf", "flash")
print(f"\nper call (flash): URDF doc ~{c['doc']:.0f} tokens, output incl. thinking ~{c['out']:.0f}, report-loop input ~{c['loop_in']:.0f}; glTF doc ~{g['doc']:.0f}, output ~{g['out']:.0f}, loop input ~{g['loop_in']:.0f}")
