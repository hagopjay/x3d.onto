#!/usr/bin/env python3
"""Model-driven evaluation of the URDF and glTF validator loops. PRE-REGISTERED in PLAN.md. Two modes:
  --stub  free: a deterministic fake model (mutation-based) exercises the whole pipeline; numbers are meaningless and files are tagged STUB.
  --real  spends money through shroud-artifacts/tools/vertex.py (shared ledger, hard cap). REFUSES to run unless GO.json exists next to this file, written only after the user's explicit go.
usage: runner.py --domain urdf|gltf --model NAME [--stub|--real] [--prompts 20] [--samples 2] [--rounds 3] [--arms A0,A1,A2,A3] [--limit N] [--report]
Run with the x3d_mcp venv python (lxml); glTF scoring needs node and ../gltf/node_modules."""
import argparse, collections, importlib.util, json, math, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; XD = HERE.parent
def load(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
sys.path.insert(0, str(XD)); sys.path.insert(0, str(HERE))
import prompts as P
try:
    import x3d_domain as X3
except Exception as _e:
    X3 = None
urdf_check = load("urdf_check", XD / "urdf" / "urdf_check.py"); urdf_repair = load("urdf_repair", XD / "urdf" / "repair.py"); gltf_repair = load("gltf_repair", XD / "gltf" / "repair.py")
ucorp = load("ucorp", XD / "urdf" / "corpus.py"); umut = load("umut", XD / "urdf" / "mutate.py"); gcorp = load("gcorp", XD / "gltf" / "corpus.py"); gmut = load("gmut", XD / "gltf" / "mutate.py")
STRICT = {"UNSUPPORTED_EXTENSION", "MESH_PRIMITIVE_NO_POSITION"}
HINT = {"urdf": "a URDF robot description (XML)", "gltf": "a glTF 2.0 file (JSON, .gltf), with any binary data embedded as base64 data URIs", "x3d": "an X3D 4.0 scene (XML encoding)"}
def task_prompt(dom, desc): return f"Write {HINT[dom]} for {desc}. Return only the document, in one code block."
def fewshot(dom):
    ex = X3.EX if dom == "x3d" else [ucorp.arm2(), ucorp.mobile()] if dom == "urdf" else [json.dumps(gcorp.tri()), json.dumps(gcorp.hierarchy())]
    return "Here are two valid examples of the format:\n\n" + "\n\n".join(f"```\n{e}\n```" for e in ex) + "\n\n"
def extract(text):
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S); return max(blocks, key=len).strip() if blocks else text.strip()
def report_text(diags, cap=8):
    lines = [f"- [{d['severity']}] {d['rule']} at {d['where']}: {d['message']}" + (f" Fix: {d['fix']}" if d.get("fix") else "") for d in diags[:cap]]
    return "\n".join(lines) + (f"\n(+{len(diags) - cap} more)" if len(diags) > cap else "")
def loop_prompt(dom, desc, prev, diags): return task_prompt(dom, desc) + f"\n\nYour previous document:\n```\n{prev}\n```\n\nA validator reported these problems:\n{report_text(diags)}\n\nReturn the complete corrected document only, in one code block."
# ---- scoring
def run_node(files):
    d = tempfile.mkdtemp()
    for k, t in files.items(): Path(d, k + ".gltf").write_text(t)
    p = subprocess.run(["node", str(XD / "gltf" / "validate.mjs"), d], capture_output=True, text=True, cwd=XD / "gltf")
    return {json.loads(l)["file"][:-5]: json.loads(l) for l in p.stdout.splitlines()}
def score(dom, docs):
    """docs: {key: text} -> {key: dict(valid_strict, errors, warnings, diags)}; strict gate = errors plus the warning classes an agent gate should not pass"""
    out = {}
    if dom == "x3d":
        for k, t in docs.items(): out[k] = X3.check(t)
    elif dom == "urdf":
        for k, t in docs.items():
            r = urdf_check.check(t, 2); out[k] = dict(valid=r.valid, errors=len(r.errors), warnings=sum(d.severity == "warning" for d in r.diags), diags=[dict(rule=d.rule, severity=d.severity, where=d.where, message=d.message, fix=d.fix) for d in r.diags if d.severity != "info"])
    else:
        res = run_node(docs)
        for k, r in res.items():
            if "crash" in r: out[k] = dict(valid=False, errors=1, warnings=0, diags=[dict(rule="CRASH", severity="error", where="", message=r["crash"], fix="")]); continue
            ds = []; e = 0
            for m in r["messages"]:
                sev = "error" if m["severity"] == 0 or m["code"] in STRICT else ("warning" if m["severity"] == 1 else "info"); e += sev == "error"
                if sev != "info": ds.append(dict(rule=m["code"], severity=sev, where=m["pointer"], message=m["message"], fix=""))
            out[k] = dict(valid=e == 0, errors=e, warnings=sum(d["severity"] == "warning" for d in ds), diags=ds)
    return out
def complete(dom, t, expect): return X3.complete(t, expect) if dom == "x3d" else P.completeness_urdf(t, expect) if dom == "urdf" else P.completeness_gltf(t, expect)
def det_repair(dom, t): return X3.repair(t) if dom == "x3d" else (urdf_repair if dom == "urdf" else gltf_repair).repair(t)
# ---- models
class CapReached(Exception): pass
class Stub:
    """Deterministic fake: serves a corpus document, sometimes faulted; on a repair prompt it fixes what the deterministic repairer can, else resamples. NOT a model."""
    def __init__(s, dom, seed=1): s.dom = dom; s.rng = random.Random(seed); s.cost = 0.0
    def __call__(s, prompt, purpose=""):
        dom = s.dom
        if dom == "x3d":
            d = s.rng.choice(X3.EX)
            if "validator reported" not in prompt and s.rng.random() < 0.6: d = d.replace("</Scene>", "", 1) if s.rng.random() < .5 else d.replace('profile="Interchange"', 'profile="Core"').replace('profile="Interactive"', 'profile="Core"')
            return "```\n" + d + "\n```", 0
        src = list(ucorp.CORPUS.values()) if dom == "urdf" else list(gcorp.CORPUS.values()); doc = s.rng.choice(src)()
        faults = list((umut.F if dom == "urdf" else gmut.F).items()); fault = None
        if "validator reported" in prompt:
            if s.rng.random() < 0.5: return "```\n" + (doc if isinstance(doc, str) else json.dumps(doc)) + "\n```", 0
        elif s.rng.random() < 0.6: fault = s.rng.choice(faults)
        if fault:
            import copy; m = fault[1][2](doc if dom == "urdf" else copy.deepcopy(doc)); doc = m if m is not None else doc
        return "```\n" + (doc if isinstance(doc, str) else json.dumps(doc)) + "\n```", 0
def real_model(dom, model, cap, location="europe-west4", max_tokens=8192):
    go = HERE / "GO.json"
    if not go.exists(): raise SystemExit("REFUSED: no GO.json. Real calls need the user's explicit go; see PLAN.md.")
    g = json.loads(go.read_text()); assert g.get("approved_by") == "user" and model in g["models"] and dom in g["domains"] and cap <= g["cap_usd"], "GO.json does not cover this run"
    if os.environ.get("GEMINI_BACKEND") == "api": from gemini_api import call, spent   # API key instead of Vertex; same ledger/cap contract
    else: sys.path.insert(0, str(XD.parent.parent / "tools")); from vertex import call, spent
    import signal, threading
    def _h(*x): raise TimeoutError("per-call alarm")
    main_t = threading.current_thread()
    if main_t is threading.main_thread(): signal.signal(signal.SIGALRM, _h)
    def f(prompt, purpose=""):
        last = None; import urllib.error, random as _r
        for attempt in range(9):
            t0 = time.time()
            try:
                (signal.alarm(420) if threading.current_thread() is threading.main_thread() else None); r = call(model, [prompt], location=location, max_tokens=max_tokens, temperature=1.0, purpose=f"xdomain-eval {purpose}"); (signal.alarm(0) if threading.current_thread() is threading.main_thread() else None)
                return r["text"], r["est_usd"], dict(seconds=round(time.time() - t0, 1), tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], finish=r["finish"], attempt=attempt)
            except urllib.error.HTTPError as e:
                (signal.alarm(0) if threading.current_thread() is threading.main_thread() else None); last = e
                if e.code not in (429, 503) or attempt >= 8: raise
                wait = min(150, 8 * 2 ** attempt) * (0.7 + 0.6 * _r.random()); print(f"  HTTP {e.code} (shared quota), backing off {wait:.0f}s, attempt {attempt + 1}/9: {purpose}", flush=True); time.sleep(wait)
            except (TimeoutError, RuntimeError) as e:
                (signal.alarm(0) if threading.current_thread() is threading.main_thread() else None); last = e; print(f"  call failed ({type(e).__name__}: {str(e)[:80]}), attempt {attempt + 1}/9: {purpose}", flush=True)
                if attempt >= 2: raise
        raise last
    f.last = {}
    f.spent = spent; return f
# ---- run
def main():
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    ap = argparse.ArgumentParser(); ap.add_argument("--domain", required=True); ap.add_argument("--model", default="stub"); ap.add_argument("--stub", action="store_true"); ap.add_argument("--real", action="store_true")
    ap.add_argument("--prompts", type=int, default=20); ap.add_argument("--samples", type=int, default=2); ap.add_argument("--rounds", type=int, default=3); ap.add_argument("--arms", default="A0,A1,A2,A3")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--cap", type=float, default=0.0); ap.add_argument("--location", default=os.environ.get("LOC", "europe-west4")); ap.add_argument("--workers", type=int, default=0); ap.add_argument("--max-tokens", type=int, default=8192); ap.add_argument("--runsdir", default="runs"); ap.add_argument("--report", action="store_true"); a = ap.parse_args()
    dom = a.domain; tag = "STUB" if a.stub else a.model; out = HERE / a.runsdir; out.mkdir(exist_ok=True); path = out / f"{dom}-{tag}.jsonl"
    if a.report: return report(path)
    assert a.stub != a.real, "choose --stub or --real"
    gen = Stub(dom) if a.stub else real_model(dom, a.model, a.cap, a.location, a.max_tokens)
    workers = a.workers or (1 if a.stub else 6)
    tasks = (X3.X3D if dom == "x3d" else P.URDF if dom == "urdf" else P.GLTF)[: a.prompts]; arms = a.arms.split(",")
    lock = threading.Lock(); st = dict(spent=0.0, ncalls=0, cached=0); rawlog = out / f"raw-{dom}-{tag}.jsonl"
    cache = {}
    if a.real and rawlog.exists():   # resume: answers already paid for are served from the raw log (same purpose key), and their cost counts toward the cap
        for l in rawlog.read_text().splitlines():
            try: r = json.loads(l)
            except Exception: continue
            cache[r["purpose"]] = r; st["spent"] += r.get("est_usd", 0)
        print(f"resuming: {len(cache)} cached answers, ${st['spent']:.2f} already spent", flush=True)
    def ask(prompt, purpose):
        with lock:
            if purpose in cache and cache[purpose].get("text") is not None: st["cached"] += 1; return extract(cache[purpose]["text"])
        with lock:
            if a.real and st["spent"] >= a.cap: raise CapReached(f"cap ${a.cap} reached after {st['ncalls']} calls (est ${st['spent']:.2f})")
        res = gen(prompt, purpose); t, c = res[0], res[1]; meta = res[2] if len(res) > 2 else {}
        with lock:
            st["spent"] += c; st["ncalls"] += 1; n_ = st["ncalls"]
            with open(rawlog, "a") as f: f.write(json.dumps(dict(purpose=purpose, est_usd=round(c, 5), prompt_chars=len(prompt), text=t, **meta)) + "\n")
            if a.real: print(f"  [{n_:3d}] ${st['spent']:.3f} {purpose} {meta.get('seconds', '?')}s in={meta.get('tokens_in', '?')} out={meta.get('tokens_out', '?')} {meta.get('finish', '')}", flush=True)
        return extract(t)
    def mkrow(pid, tier, k, arm, rnd, s, t, expect, rules=None): return dict(domain=dom, model=tag, pid=pid, tier=tier, sample=k, arm=arm, round=rnd, valid=s["valid"], errors=s["errors"], warnings=s["warnings"], complete=complete(dom, t, expect) if t else False, rules=rules if rules is not None else sorted({d["rule"] for d in s.get("diags", []) if d["severity"] == "error"}))
    def unit(task, k):
        pid, tier, desc, expect = task; rows = []; base = task_prompt(dom, desc); first = {}
        for arm in ("A0", "A1"):
            if arm in arms: first[arm] = ask((fewshot(dom) if arm == "A1" else "") + base, f"{dom}:{arm}:{pid}:{k}")
        sc = score(dom, {arm: t for arm, t in first.items()}) if first else {}
        for arm, t in first.items():
            rows.append(mkrow(pid, tier, k, arm, 0, sc[arm], t, expect))
            fx = det_repair(dom, t)[0]; s2 = score(dom, {"x": fx})["x"]; rows.append(mkrow(pid, tier, k, arm + "+det", 0, s2, fx, expect, []))
        if "A2" in arms:   # report loop from the A0 answer
            cur = first.get("A0") or ask(base, f"{dom}:A2:{pid}:{k}:r0"); s = score(dom, {"x": cur})["x"]; r = 0
            while not s["valid"] and r < a.rounds:
                r += 1; cur = ask(loop_prompt(dom, desc, cur, s["diags"]), f"{dom}:A2:{pid}:{k}:r{r}"); s = score(dom, {"x": cur})["x"]; rows.append(mkrow(pid, tier, k, "A2", r, s, cur, expect))
            rows.append(mkrow(pid, tier, k, "A2-final", r, s, cur, expect, []))
        if "A4" in arms:   # fixer first, model second
            cur = det_repair(dom, first.get("A0") or ask(base, f"{dom}:A4:{pid}:{k}:r0"))[0]; s = score(dom, {"x": cur})["x"]; r = 0
            while not s["valid"] and r < a.rounds:
                r += 1; cur = ask(loop_prompt(dom, desc, cur, s["diags"]), f"{dom}:A4:{pid}:{k}:r{r}"); s = score(dom, {"x": cur})["x"]
            rows.append(mkrow(pid, tier, k, "A4-final", r, s, cur, expect))
        if "A3" in arms:   # blind resample control
            ok = "A0" in sc and sc["A0"]["valid"]; r = 0; cur = first.get("A0")
            while not ok and r < a.rounds:
                r += 1; cur = ask(base, f"{dom}:A3:{pid}:{k}:t{r}"); s3 = score(dom, {"x": cur})["x"]; ok = s3["valid"]
            s3 = score(dom, {"x": cur})["x"] if cur else dict(valid=False, errors=1, warnings=0, diags=[])
            rows.append(mkrow(pid, tier, k, "A3-final", r, s3, cur, expect, []))
        return rows
    rows = []; note = ""
    jobs = [(t, k) for t in tasks for k in range(a.samples)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(unit, t, k): (t[0], k) for t, k in jobs}
        try:
            for fu in as_completed(futs):
                try: rows += fu.result()
                except CapReached as e: note = "STOPPED: " + str(e); continue
                except Exception as e: print(f"  unit {futs[fu]} failed: {repr(e)[:160]}", flush=True)
        finally:
            if note:
                for fu in futs: fu.cancel()
    rows.sort(key=lambda r: (r["pid"], r["sample"], r["arm"], r["round"]))
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n"); print(f"{path.name}: {len(rows)} rows, {st['ncalls']} new model calls, {st['cached']} served from cache, est ${st['spent']:.2f} cumulative {note}"); report(path)
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return ((c - h) / d, (c + h) / d)
def mcnemar(b, c):   # exact two-sided on discordant pairs
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
def report(path):
    R = [json.loads(l) for l in path.read_text().splitlines()]; stub = "STUB" in path.name
    if stub: print("!! STUB RUN: the numbers below test the pipeline only and mean nothing about any model.")
    def rate(arm, rr=None):
        rows = [r for r in R if r["arm"] == arm and (rr is None or r["round"] == rr)]; k = sum(r["valid"] for r in rows); lo, hi = wilson(k, len(rows)); return k, len(rows), lo, hi
    for arm, label in (("A0", "zero-shot first try"), ("A1", "two examples, first try"), ("A0+det", "A0 then deterministic repair"), ("A1+det", "A1 then deterministic repair"), ("A2-final", "A0 then report loop (<=R rounds)"), ("A4-final", "A0, det repair, then report loop"), ("A3-final", "A0 then blind resamples (<=R tries)")):
        k, n, lo, hi = rate(arm)
        if n: print(f"{label.ljust(36)} valid {k}/{n} = {k/n:.1%}  [{lo:.1%}, {hi:.1%}]")
    key = lambda r: (r["pid"], r["sample"]); A0 = {key(r): r for r in R if r["arm"] == "A0"}
    for arm in ("A2-final", "A4-final", "A3-final", "A0+det"):
        pr = {key(r): r for r in R if r["arm"] == arm}; b = sum(1 for k, r in pr.items() if r["valid"] and k in A0 and not A0[k]["valid"]); c = sum(1 for k, r in pr.items() if not r["valid"] and k in A0 and A0[k]["valid"])
        if pr: print(f"paired vs A0: {arm}: gained {b}, lost {c}, exact McNemar p = {mcnemar(b, c):.3g}")
    # Goodhart guard: completeness among valid, before vs after the loop
    for arm in ("A0", "A2-final", "A4-final", "A0+det"):
        rows = [r for r in R if r["arm"] == arm and r["valid"]]
        if rows: print(f"complete among valid, {arm}: {sum(r['complete'] for r in rows)}/{len(rows)} = {sum(r['complete'] for r in rows)/len(rows):.1%}")
if __name__ == "__main__": main()
