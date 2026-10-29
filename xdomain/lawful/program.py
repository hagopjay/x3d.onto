#!/usr/bin/env python3
"""A DSPy program for "spec -> X3D" with the validator loop as a refine step and the lawful metric as its metric.

  SpecToX3D   the signature: request (+ the previous document and the validator's report on later rounds) -> x3d
  LawfulX3D   the module: write, extract, optionally run the fork's deterministic repair (kept only if it scores no
              worse), score with metric.score; while the score is below the threshold and rounds remain, send the
              document and the metric's feedback back (the A2 "report loop" of xdomain/eval-plan, with the lawful
              feedback in place of the bare validator list); returns the best document seen
  make_metric the lawful metric for DSPy: a float for Evaluate / MIPROv2, score + feedback for GEPA
  optimizer   GEPA (default) or MIPROv2, both present in the installed DSPy (3.4.1 when this was written)
  make_lm     provider "scripted" (offline, for tests), "recorded" (replays recorded model answers from the x3d.ml live
              run), "gemini-api" (PREFERRED for real runs: every call goes through xdomain/eval-plan/gemini_api.py from
              branch loom/gemini-api, so spend lands in the shared ledger and its cap), "gemini" (LiteLLM gemini/<model>,
              GEMINI_API_KEY or GOOGLE_API_KEY; ledger_sync() copies its costs into the same ledger), "vertex" (LiteLLM
              vertex_ai/<model>, ADC, GCP_PROJECT, location LOC default europe-west4). Temperature 1.0 and 8,192 output
              tokens, as xdomain/eval-plan/runner.py calls gemini-3.8-flash. Real providers REFUSE to run unless
              xdomain/lawful/GO.json exists (written only on the user's explicit go) and covers provider, model and cap.

Nothing here has called a real model. Any claim about model quality from this program is grade S until a real run.
usage: program.py [--provider scripted|recorded|gemini-api|gemini|vertex] [--model M] [--optimize gepa|mipro|none] [--n 4] [--cap USD]"""
import argparse, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dspy  # noqa: E402
from dspy.utils import DummyLM  # noqa: E402
import metric as M  # noqa: E402
import specs as SP  # noqa: E402

GO = HERE / "GO.json"
RUNNER_DEFAULTS = dict(temperature=1.0, max_tokens=8192, location="europe-west4", model="gemini-3.8-flash")


class SpecToX3D(dspy.Signature):
    """Write an X3D 4.0 scene in the XML encoding for the request. Use the smallest profile that covers the nodes, put
    every node in a field of its parent that accepts it, give each requested part its own Shape, and place parts that
    should touch so that they touch. When a previous document and a report are given, return the whole corrected
    document. Return only the document."""
    request: str = dspy.InputField(desc="what the scene must show")
    previous: str = dspy.InputField(desc="the previous document, empty on the first try")
    report: str = dspy.InputField(desc="what the checker found wrong with the previous document, empty on the first try")
    x3d: str = dspy.OutputField(desc="the complete X3D document, starting with <?xml or <X3D")


class CapReached(RuntimeError): pass


def spent(lm):
    if hasattr(lm, "api") and hasattr(lm.api, "spent"): return getattr(lm, "usd", 0.0)
    return sum((h.get("cost") or 0.0) for h in (getattr(lm, "history", None) or []))


def det_repair(doc):
    try:
        from validation.repair import repair_x3d
        r = repair_x3d(doc)
        return r["fixed"] if r and not r.get("error") and r.get("fixed") else doc
    except Exception:
        return doc


class LawfulX3D(dspy.Module):
    def __init__(self, rounds=3, threshold=1.0, repair=True, cap=None):
        super().__init__()
        self.write = dspy.Predict(SpecToX3D); self.rounds = rounds; self.threshold = threshold; self.repair = repair; self.cap = cap

    def forward(self, request, spec=None):
        spec = M.TaskSpec.from_json(spec) if isinstance(spec, dict) else (spec or M.spec_from_text(request))
        prev = report = ""; best = None; hist = []
        for r in range(self.rounds + 1):
            if self.cap is not None and dspy.settings.lm is not None and spent(dspy.settings.lm) >= self.cap:
                raise CapReached(f"cap ${self.cap} reached")
            doc = M.extract(self.write(request=request, previous=prev, report=report).x3d)
            s = M.score(doc, spec)
            if self.repair:
                fixed = det_repair(doc)
                if fixed != doc:
                    s2 = M.score(fixed, spec)
                    if s2.score >= s.score: doc, s = fixed, s2
            hist.append(dict(round=r, score=s.score, parts=s.parts))
            if best is None or s.score > best[1].score: best = (doc, s)
            if s.score >= self.threshold: break
            prev, report = doc, s.feedback
        doc, s = best
        return dspy.Prediction(x3d=doc, score=s.score, parts=s.parts, feedback=s.feedback, rounds=len(hist) - 1, history=hist)


def make_metric(feedback=False):
    """Lawful metric with DSPy's signatures. gold carries `spec` (a TaskSpec dict); pred carries `x3d`."""
    def lawful_metric(gold, pred, trace=None, pred_name=None, pred_trace=None, *args, **kw):
        s = M.score(getattr(pred, "x3d", "") or "", M.TaskSpec.from_json(gold.spec))
        if not feedback: return s.score
        hist = getattr(pred, "history", None) or []
        tail = ("\nRounds: " + ", ".join(f"r{h['round']}={h['score']}" for h in hist)) if hist else ""
        return dspy.Prediction(score=s.score, feedback=s.feedback + tail)
    lawful_metric.__name__ = "lawful_metric_feedback" if feedback else "lawful_metric"
    return lawful_metric


def examples(which="eval"):
    S = SP.eval_specs() if which == "eval" else SP.live_specs()
    return [dspy.Example(request=s.prompt, spec=s.to_json(), pid=pid).with_inputs("request", "spec") for pid, s in S.items()]


def optimizer(kind="gepa", reflection_lm=None, budget=None, auto="light", threads=1):
    """-> (optimizer, compile kwargs). GEPA reads the metric's feedback text; MIPROv2 (needs optuna: pip install dspy[optuna])
    reads the scalar. A budget (metric calls for GEPA, trials for MIPROv2) replaces the auto preset."""
    if kind == "gepa":
        kw = dict(max_metric_calls=budget) if budget else dict(auto=auto)
        return dspy.GEPA(metric=make_metric(True), reflection_lm=reflection_lm, num_threads=threads, track_stats=True, seed=0,
                         reflection_minibatch_size=2, **kw), {}
    if kind == "mipro":
        if budget:
            return (dspy.MIPROv2(metric=make_metric(False), prompt_model=reflection_lm, auto=None, num_candidates=2, num_threads=threads, max_bootstrapped_demos=1, max_labeled_demos=0, seed=9, verbose=False),
                    dict(num_trials=budget, requires_permission_to_run=False, minibatch=False))
        return (dspy.MIPROv2(metric=make_metric(False), prompt_model=reflection_lm, auto=auto, num_threads=threads, max_bootstrapped_demos=2, max_labeled_demos=0, seed=9),
                dict(requires_permission_to_run=False))
    raise ValueError(kind)


# ---------------------------------------------------------------- language models
class ScriptedLM(DummyLM):
    """Offline LM. `writer(request, report) -> document` answers SpecToX3D calls in the chat-adapter format; anything
    else (a GEPA reflection or a MIPROv2 proposal) gets `proposal` in a fenced block. NOT a model."""
    def __init__(self, writer, proposal="Write X3D 4.0 with the smallest sufficient profile; put parts that touch in contact."):
        super().__init__([]); self.writer = writer; self.proposal = proposal; self.calls = 0
        from dspy.clients.engines.dummy_engine import DummyEngine, AsyncDummyEngine
        owner = self
        class _E(DummyEngine):
            def _complete_messages(self, messages):
                from dspy.lm15 import Message, Response, TextPart, Usage
                return Response(id=None, model="scripted", message=Message.assistant([TextPart(owner.respond(messages))]), finish_reason="stop",
                                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0))
        self._engine_spec = _E(self); self._async_engine_spec = AsyncDummyEngine(self._engine_spec)

    def copy(self, **kw): return self

    def respond(self, messages):
        import re, inspect
        self.calls += 1; text = "\n".join(m.get("content") or "" for m in messages); last = messages[-1].get("content") or ""
        if "[[ ## x3d ## ]]" in text and "[[ ## request ## ]]" in last:
            req, rep = _field(last, "request"), _field(last, "report")
            args = (req, rep, messages[0].get("content") or "") if len(inspect.signature(self.writer).parameters) >= 3 else (req, rep)
            return f"[[ ## x3d ## ]]\n{self.writer(*args)}\n\n[[ ## completed ## ]]"
        prop = self.proposal(text) if callable(self.proposal) else self.proposal
        m = re.search(r"in the following order of fields: (.*?)\.?$", last.strip().splitlines()[-1]) if last.strip() else None
        outs = re.findall(r"`(\w+)`", m.group(1)) if m else []
        if outs and "JSON" in last.strip().splitlines()[-1]: return json.dumps({f: prop for f in outs})
        if outs: return "\n\n".join(f"[[ ## {f} ## ]]\n{prop}" for f in outs) + "\n\n[[ ## completed ## ]]"
        return f"```\n{prop}\n```"


def _field(text, name):
    import re
    m = re.search(rf"\[\[ ## {name} ## \]\]\n(.*?)(?=\n\n\[\[ ## |\n\nRespond with the corresponding output fields|\Z)", text, re.S); return (m.group(1).strip() if m else "")


class LedgerLM(ScriptedLM):
    """Routes every DSPy call through xdomain/eval-plan/gemini_api.py (branch loom/gemini-api): call(model, [prompt]) with
    GEMINI_API_KEY, so each call is a row in the shared ledger (GEMINI_LEDGER, default /mnt/project-files/x3d-loom/
    gemini-ledger.jsonl) and the shared cap (GEMINI_CAP_USD) is checked before it. The chat messages are flattened into one
    text part (system first). `api` is the loaded gemini_api module (or anything with the same call())."""
    def __init__(self, api, model, purpose="lawful-dspy", temperature=1.0, max_tokens=8192):
        super().__init__(lambda req, rep: ""); self.api = api; self.model_id = model; self.purpose = purpose
        self.temperature = temperature; self.max_out = max_tokens; self.usd = 0.0

    def respond(self, messages):
        self.calls += 1
        prompt = "\n\n".join(f"[{m.get('role')}]\n{m.get('content') or ''}" if m.get("role") == "system" else (m.get("content") or "") for m in messages)
        r = self.api.call(self.model_id, [prompt], max_tokens=self.max_out, temperature=self.temperature, purpose=f"{self.purpose} call {self.calls}")
        self.usd += r.get("est_usd", 0.0); return r["text"]


def load_gemini_api(path=None):
    import importlib.util
    p = Path(path or os.environ.get("GEMINI_API_PY", HERE.parent / "eval-plan" / "gemini_api.py"))
    if not p.exists(): raise SystemExit(f"{p} not found: merge branch loom/gemini-api or set GEMINI_API_PY")
    sp = importlib.util.spec_from_file_location("gemini_api", p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def recorded_writer(root, model="gemini-3.8-flash"):
    """Replays the recorded attempts of one model from the x3d.ml live run: round k serves attempt k+1 (the last one
    again when the record runs out). The recorded repair prompts were the run's, not this program's: a replay, not a run."""
    run = Path(root) / "runs" / "live-2026-10-17" / "x3d" / model.replace("/", "_"); by_prompt = {}
    for pid, s in SP.live_specs().items():
        docs = sorted(run.glob(f"{pid}_a*.x3d"))
        if docs: by_prompt[s.prompt] = [d.read_text(encoding="utf-8") for d in docs]
    state = {}
    def writer(req, report):
        docs = by_prompt.get(req) or ["<X3D/>"]; k = state.get(req, -1) + 1 if report else 0; state[req] = k
        return docs[min(k, len(docs) - 1)]
    writer.prompts = set(by_prompt); return writer


def go_ok(provider, model, cap):
    if not GO.exists(): raise SystemExit(f"REFUSED: no {GO.relative_to(HERE.parent.parent)}. Real calls need the user's explicit go.")
    g = json.loads(GO.read_text())
    if not (g.get("approved_by") == "user" and provider in g.get("providers", []) and model in g.get("models", []) and cap is not None and cap <= g.get("cap_usd", 0)):
        raise SystemExit("REFUSED: GO.json does not cover this provider, model and cap.")


def make_lm(provider, model=RUNNER_DEFAULTS["model"], cap=None, writer=None, **kw):
    if provider == "scripted": return ScriptedLM(writer or (lambda req, rep: "<X3D/>"))
    if provider == "recorded": return ScriptedLM(writer or recorded_writer(kw.get("root", os.environ.get("X3D_ML", "/home/claude/x3d.ml")), model))
    base = dict(temperature=RUNNER_DEFAULTS["temperature"], max_tokens=RUNNER_DEFAULTS["max_tokens"], engine="litellm", cache=True, num_retries=8)
    if provider == "gemini-api":   # preferred for a real run: one ledger and one cap with runner.py / judge.py (GEMINI_BACKEND=api)
        if not kw.get("dry"): go_ok(provider, model, cap)
        return LedgerLM(kw.get("api") or load_gemini_api(), model, temperature=RUNNER_DEFAULTS["temperature"], max_tokens=RUNNER_DEFAULTS["max_tokens"])
    if provider == "gemini":       # LiteLLM; its cost is only in lm.history until ledger_sync() copies it into the shared ledger
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not kw.get("dry"): go_ok(provider, model, cap)
        if not key and not kw.get("dry"): raise SystemExit("set GEMINI_API_KEY or GOOGLE_API_KEY")
        return dspy.LM(f"gemini/{model}", api_key=key or "unset", **base)
    if provider == "vertex":
        if not kw.get("dry"): go_ok(provider, model, cap)
        return dspy.LM(f"vertex_ai/{model}", vertex_project=os.environ.get("GCP_PROJECT", ""), vertex_location=os.environ.get("LOC", RUNNER_DEFAULTS["location"]), **base)
    raise ValueError(provider)


def ledger_sync(lm, purpose="lawful-dspy litellm", ledger=None):
    """Append LiteLLM-reported costs from lm.history to the shared Gemini ledger (same row shape as gemini_api.py), so a
    LiteLLM-path run is counted in one place. Returns USD written. Rows already synced are skipped by position."""
    led = Path(ledger or os.environ.get("GEMINI_LEDGER", "/mnt/project-files/x3d-loom/gemini-ledger.jsonl"))
    hist = getattr(lm, "history", None) or []; start = getattr(lm, "_synced", 0); usd = 0.0
    if start >= len(hist): return 0.0
    led.parent.mkdir(parents=True, exist_ok=True)
    with open(led, "a") as f:
        for h in hist[start:]:
            u = h.get("usage") or {}; c = float(h.get("cost") or 0.0); usd += c
            f.write(json.dumps(dict(t=h.get("timestamp", ""), model=str(getattr(lm, "model", "")).split("/")[-1], purpose=purpose,
                                    tokens_in=u.get("prompt_tokens", 0), tokens_out=u.get("completion_tokens", 0), est_usd=round(c, 6), via="litellm")) + "\n")
    lm._synced = len(hist); return usd


def run(provider="scripted", model=RUNNER_DEFAULTS["model"], optimize="gepa", n=4, cap=None, writer=None, rounds=3, budget=None, out=None, which="eval"):
    """Baseline evaluation, optional optimisation, evaluation of the optimised program. Returns a dict of numbers."""
    lm = make_lm(provider, model, cap=cap, writer=writer); dspy.configure(lm=lm)
    data = examples(which)
    if provider == "recorded" and getattr(lm.writer, "prompts", None) is not None:
        data = [e for e in data if e.request in lm.writer.prompts]
    data = data[:n] if n else data
    train, val = data[: max(1, len(data) // 2)], data[max(1, len(data) // 2):] or data[:1]
    prog = LawfulX3D(rounds=rounds, cap=cap); met = make_metric(False)
    ev = lambda p, d: dspy.Evaluate(devset=d, metric=met, num_threads=1, display_progress=False, provide_traceback=True)(p)
    base = ev(prog, data); res = dict(provider=provider, model=model, n=len(data), baseline=round(float(base.score), 2))
    res["baseline_rows"] = [dict(pid=e.pid, score=r[2] if not hasattr(r[2], "score") else r[2].score, rounds=r[1].rounds) for e, r in zip(data, base.results)]
    if optimize != "none":
        opt, ckw = optimizer(optimize, reflection_lm=lm, budget=budget or (4 * len(train) + 2 * len(val) if optimize == "gepa" else 2))
        best = opt.compile(prog, trainset=train, valset=val, **ckw)
        res["optimized"] = round(float(ev(best, data).score), 2); res["instruction"] = best.write.signature.instructions[:400]
        if out: best.save(str(out))
    if provider == "gemini": ledger_sync(lm)
    res["lm_calls"] = getattr(lm, "calls", len(getattr(lm, "history", []) or [])); res["usd"] = round(getattr(lm, "usd", 0.0) or spent(lm), 4)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--provider", default="scripted"); ap.add_argument("--model", default=RUNNER_DEFAULTS["model"])
    ap.add_argument("--optimize", default="gepa"); ap.add_argument("--n", type=int, default=4); ap.add_argument("--cap", type=float); ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--budget", type=int); ap.add_argument("--set", default="eval", choices=["eval", "live"]); ap.add_argument("--out")
    a = ap.parse_args()
    if a.provider == "scripted":
        import adversarial as ADV
        S, ctl, _ = ADV.cases(); good = {S[k].prompt: d for k, d in ctl.items()}
        first = {S["X-A3"].prompt: ADV.doc(ADV.BOX + ADV.cyl(y=0.6))}   # X-A3: the cylinder sinks into the box on the first try
        w = lambda req, rep: good.get(req, ADV.doc(ADV.ON_TOP)) if rep else first.get(req, ADV.doc(ADV.ON_TOP, "Full"))   # first tries are flawed; the report fixes them
        print(json.dumps(run("scripted", optimize=a.optimize, n=a.n, writer=w, rounds=a.rounds, budget=a.budget, out=a.out), indent=1))
    else:
        print(json.dumps(run(a.provider, a.model, a.optimize, a.n, a.cap, rounds=a.rounds, budget=a.budget, out=a.out, which=("live" if a.provider == "recorded" else a.set)), indent=1))
