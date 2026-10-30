#!/usr/bin/env python3
"""Held-out check of a GEPA-optimised LawfulX3D program: the baseline program and the saved optimised one, same model, same
rounds, on a prompt set the optimiser never saw (default: the 50 live prompts; the optimiser trained on the eval set).
Paired per prompt: mean scores, prompts improved / worse / tied, an exact sign-test p, and how many reach 1.0.
usage: heldout.py SAVED_PROGRAM.json [--model M] [--set live|eval] [--rounds 1] [--cap USD] [--out results/heldout-<name>.json]"""
import argparse, json, math
from pathlib import Path
import dspy
import program as P

ap = argparse.ArgumentParser(); ap.add_argument("saved"); ap.add_argument("--model", default="gemini-2.5-flash-lite"); ap.add_argument("--set", default="live")
ap.add_argument("--rounds", type=int, default=1); ap.add_argument("--cap", type=float, default=3.0); ap.add_argument("--n", type=int); ap.add_argument("--out"); a = ap.parse_args()
lm = P.make_lm("gemini-api", a.model, cap=a.cap); dspy.configure(lm=lm)
data = P.examples(a.set)[: a.n]; met = P.make_metric(False)
base = P.LawfulX3D(rounds=a.rounds, cap=a.cap); opt = P.LawfulX3D(rounds=a.rounds, cap=a.cap); opt.load(a.saved)
ev = lambda prog: dspy.Evaluate(devset=data, metric=met, num_threads=4, display_progress=False, provide_traceback=False)(prog)
rb, ro = ev(base), ev(opt)
sc = lambda r: float(r[2].score if hasattr(r[2], "score") else r[2] or 0.0)
rows = [dict(pid=e.pid, base=round(sc(x), 4), opt=round(sc(y), 4)) for e, x, y in zip(data, rb.results, ro.results)]
up = sum(r["opt"] > r["base"] + 1e-9 for r in rows); down = sum(r["opt"] < r["base"] - 1e-9 for r in rows); n = up + down
p = min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(up, down) + 1)) / 2 ** n) if n else 1.0
res = dict(model=a.model, set=a.set, rounds=a.rounds, n=len(rows), saved=a.saved, base_mean=round(100 * sum(r["base"] for r in rows) / len(rows), 2),
           opt_mean=round(100 * sum(r["opt"] for r in rows) / len(rows), 2), improved=up, worse=down, tied=len(rows) - n, sign_p=round(p, 5),
           base_perfect=sum(r["base"] >= 1 for r in rows), opt_perfect=sum(r["opt"] >= 1 for r in rows), usd=round(getattr(lm, "usd", 0.0) or 0.0, 4), rows=rows)
out = Path(a.out or f"results/heldout-{Path(a.saved).stem}-{a.set}.json"); out.write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1))
