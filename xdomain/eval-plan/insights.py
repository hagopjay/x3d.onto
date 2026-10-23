#!/usr/bin/env python3
"""Verbose, deterministic insight report for one run: INSIGHTS-<domain>-<model>.md. No model calls.
usage: insights.py --domain D --model M  (x3d_mcp venv python)"""
import argparse, collections, difflib, importlib.util, json, math, re, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.argv_backup = sys.argv; sys.argv = [sys.argv[0]]
spec = importlib.util.spec_from_file_location("runner", HERE / "runner.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
sys.argv = sys.argv_backup
ap = argparse.ArgumentParser(); ap.add_argument("--domain", required=True); ap.add_argument("--model", required=True); a = ap.parse_args()
runs = HERE / "runs"; rows = [json.loads(l) for l in (runs / f"{a.domain}-{a.model}.jsonl").read_text().splitlines()]
raw = [json.loads(l) for l in (runs / f"raw-{a.domain}-{a.model}.jsonl").read_text().splitlines()]
tasks = {t[0]: t for t in (R.X3.X3D if a.domain == "x3d" else R.P.URDF if a.domain == "urdf" else R.P.GLTF)}
pct = lambda k, n: f"{k}/{n} = {k / n:.0%}" if n else "n/a"
L = [f"# Insights: {a.domain} x {a.model}", ""]
arms = sorted({r["arm"] for r in rows}); samples = len({(r["pid"], r["sample"]) for r in rows})
L += [f"{samples} first tries ({len({r['pid'] for r in rows})} prompts). Arms present: {', '.join(arms)}.", ""]
# 1 cost, latency, throughput
cost = sum(r["est_usd"] for r in raw); sec = [r["seconds"] for r in raw if "seconds" in r]; tin = sum(r.get("tokens_in", 0) for r in raw); tout = sum(r.get("tokens_out", 0) for r in raw)
L += ["## Cost, latency, tokens", f"- {len(raw)} model calls, estimated ${cost:.2f} (prices assumed in vertex.py), {tin:,} tokens in, {tout:,} out (thinking included by vertex.py).",
      f"- latency per call: median {statistics.median(sec):.1f}s, p90 {sorted(sec)[int(len(sec) * .9)]:.1f}s, max {max(sec):.1f}s (shared quota; 429 back-offs are not in these numbers)." if sec else "- latency not recorded.",
      f"- finish reasons: {dict(collections.Counter(r.get('finish') for r in raw))}", ""]
# 2 validity by arm and tier
L += ["## Validity by arm (strict gate)", "| arm | all | tier A | tier B | tier C |", "|---|---|---|---|---|"]
for arm in ("A0", "A1", "A0+det", "A1+det", "A2-final", "A4-final", "A3-final"):
    rr = [r for r in rows if r["arm"] == arm]
    if not rr: continue
    cells = [pct(sum(r["valid"] for r in rr), len(rr))] + [pct(sum(r["valid"] for r in rr if r["tier"] == t), sum(1 for r in rr if r["tier"] == t)) for t in "ABC"]
    L.append(f"| {arm} | " + " | ".join(cells) + " |")
L.append("")
# 3 first-failure rules
ff = collections.Counter(rule for r in rows if r["arm"] == "A0" and not r["valid"] for rule in r["rules"]); nA0f = sum(1 for r in rows if r["arm"] == "A0" and not r["valid"])
L += [f"## What fails first ({nA0f} invalid zero-shot answers)", "| rule | answers | share of failures |", "|---|---|---|"] + [f"| {k} | {v} | {v / nA0f:.0%} |" for k, v in ff.most_common(12)] + [""]
# 4 rounds to valid (A2)
fin = [r for r in rows if r["arm"] == "A2-final"]
rd = collections.Counter((r["round"] if r["valid"] else "never") for r in fin)
L += ["## Report loop: rounds to valid (A2, from the zero-shot answer)", "| rounds used | documents |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(rd.items(), key=lambda kv: (kv[0] == 'never', str(kv[0])))] + [""]
per_round = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["arm"] == "A2" and r["round"] > 0: per_round[r["round"]][0] += r["valid"]; per_round[r["round"]][1] += 1
L += ["Round-by-round conversion of the documents still invalid: " + "; ".join(f"round {k}: {pct(v[0], v[1])}" for k, v in sorted(per_round.items())), ""]
# 5 persistent rules
pers = collections.Counter(rule for r in rows if r["arm"] == "A2" and r["round"] >= 2 and not r["valid"] for rule in r["rules"])
L += ["## Rules that survive two or more rounds", ", ".join(f"{k} ({v})" for k, v in pers.most_common(8)) or "none", ""]
# 6 Goodhart guard
def comp(arm):
    rr = [r for r in rows if r["arm"] == arm and r["valid"]]; return sum(r["complete"] for r in rr), len(rr)
L += ["## Valid is not complete (mechanical expectation: counts of parts)"] + [f"- {arm}: {pct(*comp(arm))} of valid documents meet the expectation" for arm in ("A0", "A1", "A0+det", "A2-final", "A4-final", "A3-final") if comp(arm)[1]]
A0 = {(r["pid"], r["sample"]): r for r in rows if r["arm"] == "A0"}; dmg = [(r["pid"], r["sample"]) for r in fin if r["valid"] and not r["complete"] and A0.get((r["pid"], r["sample"]), {}).get("complete")]
L += [f"- documents whose zero-shot answer met the expectation but whose repaired answer no longer does: {len(dmg)} {dmg[:6]}", ""]
# 7 worked examples
byp = {r["purpose"].replace("xdomain-eval ", ""): R.extract(r["text"]) for r in raw}
ex = 0; L += ["## Worked examples (report loop)"]
for (pid, k), r0 in A0.items():
    if r0["valid"] or ex >= 3: continue
    docs = [byp.get(f"{a.domain}:A0:{pid}:{k}")] + [byp.get(f"{a.domain}:A2:{pid}:{k}:r{i}") for i in (1, 2, 3)]; docs = [d for d in docs if d]
    if len(docs) < 2: continue
    ex += 1; L += [f"### {pid} sample {k}: {tasks[pid][2]}"]
    for i, d in enumerate(docs):
        s = R.score(a.domain, {"x": d})["x"]; tag = "zero-shot answer" if i == 0 else f"after report {i}"
        L += [f"- **{tag}**: valid={s['valid']}, errors={s['errors']}, warnings={s['warnings']}, {len(d)} chars" + (f", {sum(1 for l in difflib.ndiff(docs[i-1].splitlines(), d.splitlines()) if l[:1] in '+-')} changed lines" if i else "")]
        for dg in s["diags"][:4]: L.append(f"  - [{dg['severity']}] {dg['rule']} {dg['where']}: {dg['message'][:140]}")
L += ["", "## Reading these numbers", "- Gate = errors only after the strict policy; completeness is a floor (counts), not fidelity.", "- Rates are for this model and these prompts; see PLAN.md threats."]
(HERE / f"INSIGHTS-{a.domain}-{a.model}.md").write_text("\n".join(L)); print("\n".join(L)[:3000])
