#!/usr/bin/env python3
"""Tests for the lawful metric and the DSPy program. Model-free: no network, no spend.
Metric tests need lxml and the x3d_mcp fork (X3D_MCP, default /home/user/x3d_mcp). The DSPy tests need `pip install dspy`
(and optuna for MIPROv2); without it they are reported as SKIP, unless LAWFUL_REQUIRE_DSPY=1, which makes them fail.
The live-corpus check runs when the x3d.ml checkout is present (X3D_ML, default /home/claude/x3d.ml).
usage: python3 -I xdomain/lawful/test_lawful.py   (or: make lawful-test LAWFUL_PY=<python with dspy>)"""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metric as M, specs as SP, adversarial as ADV  # noqa: E402

fails, skips = [], []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""))
    if not ok: fails.append(name)

S, CTL, CASES = ADV.cases()
# ---- the metric
for k, d in CTL.items():
    r = M.score(d, S[k]); check(f"control {k} scores 1.0", r.score == 1.0, f"{r.score} {r.parts}")
for name, k, part, d in CASES:
    r, c = M.score(d, S[k]), M.score(CTL[k], S[k])
    check(f"adversarial {name}: below control, {part} < 1", r.score < c.score and (r.parts[part] if r.parts[part] is not None else 0) < 1, f"{r.score} vs {c.score}, {part}={r.parts[part]}")
xsd_pass = [n for n, k, p, d in CASES if M.score(d, S[k]).details["xsd_valid"]]
check("15 of 16 adversarial documents pass the XSD (the metric's catches are not XSD catches)", len(xsd_pass) == 15, str(len(xsd_pass)))
wt = M.score(dict((n, d) for n, k, p, d in CASES)["unlawful/wrong-type-USE"], S["X-A3"])
check("wrong-type USE passes XSD and the fork's semantic gate, the metric flags it", wt.details["strict_valid"] and wt.parts["lawful"] < 1 and "wrong-type USE" in wt.feedback)
check("not well-formed scores 0", M.score("<X3D><Scene>", S["X-A1"]).score == 0.0)
bad = ADV.doc(ADV.ON_TOP.replace('size="2 1 2"', 'size="2 1 2" colour="red"'))
r = M.score(bad, S["X-A3"]); check("XSD-invalid scores at most 0.5", not r.details["xsd_valid"] and r.score <= 0.5, str(r.score))
check("extract takes the longest fenced block", M.extract("text\n```xml\n<X3D/>\n```\nmore ```\n<X3D><Scene/></X3D>\n```") == "<X3D><Scene/></X3D>")
for gap, want in ((0.04, True), (0.06, False), (-0.04, True), (-0.06, False)):
    r = M.score(ADV.doc(ADV.BOX + ADV.cyl(y=1.0 + gap)), S["X-A3"])
    check(f"contact tolerance 5%: gap {gap:+} -> {'contact' if want else 'no contact'}", (r.parts["spatial"] == 1.0) == want, str(r.parts["spatial"]))
sp = M.spec_from_text("a yellow cylinder resting on top of a gray box")
check("spec_from_text finds on_top(Cylinder, Box)", ["on_top", "Cylinder", "Box"] in sp.relations and {"Cylinder", "Box"} <= set(sp.required), str(sp.relations))
check("spec_from_text finds a row of three spheres", ["row_x", "Sphere", 3] in M.spec_from_text("three spheres in a row, left to right").relations)
check("spec_from_text: rotation needs TimeSensor, OrientationInterpolator, ROUTE", {"TimeSensor", "OrientationInterpolator", "ROUTE"} <= set(M.spec_from_text("a box that rotates forever").required))
r = M.score(ADV.doc('<EnvironmentLight/>' + ADV.ON_TOP), S["X-A3"])
check("a 4.1 node in a 4.0 document is unlawful under the 4.0 X3DUOM", r.parts["lawful"] < 1 and "not an X3D 4.0 node" in r.feedback)
ps, _ = M.parts(M.etree.fromstring(ADV.doc('<Transform scale="1 2 1"><Transform translation="0 1 0"><Shape><Box size="1 1 1"/></Shape></Transform></Transform>').encode()).find("Scene"), {})
check("nested transforms: scale 2 over translation 1 puts a unit box at y in [1, 3]", abs(ps[0].lo[1] - 1) < 1e-9 and abs(ps[0].hi[1] - 3) < 1e-9, f"{ps[0].lo[1]}, {ps[0].hi[1]}")
r = M.score(ADV.doc(ADV.ON_TOP + '<Shape><Appearance/><Appearance/><Box/></Shape>'), S["X-A3"])
check("two nodes in one SFNode field are unlawful", "SFNode but holds a second node" in r.feedback)
ls = SP.live_specs(); es = SP.eval_specs()
check("specs: 50 live prompts and 20 eval-plan prompts", len(ls) == 50 and len(es) == 20)
src = (HERE.parent / "eval-plan" / "x3d_domain.py").read_text()
check("eval specs copy the eval-plan X3D prompts verbatim", all(f'"{desc}"' in src for _, _, desc, _ in SP.EVAL_X3D))

# ---- the recorded live corpus (x3d.ml, 2026-10-17)
root = Path(os.environ.get("X3D_ML", "/home/claude/x3d.ml"))
if (root / "runs" / "live-2026-10-17" / "events.jsonl").exists():
    import offline as OFF
    L = OFF.summarise_live(OFF.live(root))
    check("live: 383 documents, every sha matches the run's event", L["n_docs"] == 383 and L["sha_matches_event"] == 383)
    check("live: strict validity here equals the run's own verdict on every document", L["strict_agrees_with_run_record"] == L["run_record_n"] == 383)
    check("live: XSD-valid 208, strict-valid 178", (L["xsd_valid"], L["strict_valid"]) == (208, 178), f"{L['xsd_valid']}, {L['strict_valid']}")
    check("live: metric separates strict-valid from not (AUC > 0.99)", L["auc_metric_vs_strict"] > 0.99, str(L["auc_metric_vs_strict"]))
else:
    skips.append("live corpus"); print(f"SKIP live corpus: {root} not found")

# ---- the DSPy program
try:
    import dspy  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False
if HAVE:
    import program as P
    import dspy
    sunk = ADV.doc(ADV.BOX + ADV.cyl(y=0.6))
    lm = P.ScriptedLM(lambda req, rep: CTL["X-A3"] if "sinks" in rep else sunk); dspy.configure(lm=lm)
    out = P.LawfulX3D(rounds=3)(request=S["X-A3"].prompt, spec=S["X-A3"].to_json())
    check("program: the metric's feedback reaches the next round (sunk -> fixed in 1 round)", out.score == 1.0 and out.rounds == 1 and out.history[0]["parts"]["spatial"] == 0.0, str(out.history))
    m = P.make_metric(True)(dspy.Example(spec=S["X-A3"].to_json()), dspy.Prediction(x3d=sunk), None, "write", None)
    check("metric for GEPA returns score and feedback", hasattr(m, "feedback") and "sinks" in m.feedback and m.score < 1)
    check("metric for Evaluate/MIPROv2 returns a float", isinstance(P.make_metric(False)(dspy.Example(spec=S["X-A3"].to_json()), dspy.Prediction(x3d=sunk)), float))
    RULE = "Never declare profile='Full'."
    w = lambda req, rep, system: ADV.doc(ADV.ON_TOP, "Interchange" if RULE in system else "Full")
    lm = P.ScriptedLM(w, proposal=lambda t: P.SpecToX3D.instructions + " " + RULE if "profile='Full'" in t else P.SpecToX3D.instructions); dspy.configure(lm=lm)
    ex = P.examples()[:4]; met = P.make_metric(False)
    ev = lambda p: dspy.Evaluate(devset=ex, metric=met, display_progress=False)(p).score
    prog = P.LawfulX3D(rounds=0); base = ev(prog)
    opt, kw = P.optimizer("gepa", reflection_lm=lm, budget=16); best = opt.compile(prog, trainset=ex[:2], valset=ex[2:], **kw)
    check("GEPA end to end (scripted LM): the feedback-driven instruction raises the score", ev(best) > base and RULE in best.write.signature.instructions, f"{base:.2f} -> {ev(best):.2f}")
    try:
        import optuna  # noqa: F401
        lm2 = P.ScriptedLM(lambda req, rep: CTL["X-A3"]); dspy.configure(lm=lm2)
        opt, kw = P.optimizer("mipro", reflection_lm=lm2, budget=2); best = opt.compile(P.LawfulX3D(rounds=0), trainset=P.examples()[:3], valset=P.examples()[3:6], **kw)
        check("MIPROv2 end to end (scripted LM) compiles", best is not None and lm2.calls > 0)
    except ImportError:
        skips.append("mipro"); print("SKIP MIPROv2: optuna not installed")
    g = P.make_lm("gemini", dry=True)
    check("gemini LM: LiteLLM gemini/gemini-3.8-flash, temperature 1.0, 8192 tokens (as runner.py)", g.model == "gemini/gemini-3.8-flash" and g.kwargs["temperature"] == 1.0 and g.kwargs["max_tokens"] == 8192 and g._engine_spec == "litellm")
    v = P.make_lm("vertex", dry=True); check("vertex LM: vertex_ai/..., europe-west4 by default", v.model == "vertex_ai/gemini-3.8-flash" and v.kwargs["vertex_location"] == os.environ.get("LOC", "europe-west4"))
    import tempfile, json as _j
    led = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    class FakeApi:   # stands in for gemini_api.call: writes the same ledger row, returns a scripted answer, no network
        def call(self, model, parts, max_tokens=8192, temperature=1.0, purpose="", **k):
            with open(led, "a") as f: f.write(_j.dumps(dict(model=model, purpose=purpose, est_usd=0.001)) + "\n")
            return dict(text=f"[[ ## x3d ## ]]\n{CTL['X-A3']}\n\n[[ ## completed ## ]]", est_usd=0.001)
        def spent(self): return 0.0
    gl = P.make_lm("gemini-api", dry=True, api=FakeApi()); dspy.configure(lm=gl)
    o = P.LawfulX3D(rounds=1)(request=S["X-A3"].prompt, spec=S["X-A3"].to_json())
    rows = [_j.loads(l) for l in led.read_text().splitlines()]
    check("gemini-api provider: each DSPy call goes through gemini_api.call and its ledger", o.score == 1.0 and len(rows) == 1 and rows[0]["purpose"].startswith("lawful-dspy") and abs(P.spent(gl) - 0.001) < 1e-9, str(rows))
    class H: model = "gemini/gemini-3.8-flash"; history = [dict(cost=0.002, usage=dict(prompt_tokens=10, completion_tokens=20), timestamp="t")]
    h = H(); n1 = P.ledger_sync(h, ledger=led); n2 = P.ledger_sync(h, ledger=led)
    check("ledger_sync copies LiteLLM costs into the shared ledger once", abs(n1 - 0.002) < 1e-9 and n2 == 0.0 and len(led.read_text().splitlines()) == 2)
    try:
        P.make_lm("gemini-api", cap=1.0); P.make_lm("gemini", cap=1.0); refused = not P.GO.exists()
    except SystemExit as e:
        refused = "REFUSED" in str(e)
    check("a real provider refuses to run without xdomain/lawful/GO.json", refused)
else:
    skips.append("dspy"); print("SKIP DSPy tests: dspy not installed (pip install dspy)")
    if os.environ.get("LAWFUL_REQUIRE_DSPY") == "1": fails.append("dspy missing")

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAIL: ' + str(fails)}" + (f" (skipped: {', '.join(skips)})" if skips else ""))
sys.exit(1 if fails else 0)
