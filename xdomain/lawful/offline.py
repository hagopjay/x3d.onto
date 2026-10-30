#!/usr/bin/env python3
"""Validate the lawful metric offline, model-free, on what is recorded:
  1. the x3d.ml live run of 2026-10-17 (383 recorded documents, 5 models, 50 prompts, every attempt; x3d.ml at 6eb8169,
     runs/live-2026-10-17): metric vs XSD validity, vs strict validity (XSD + fork semantic errors), vs the run's own
     string-count constraint check, and vs the X_ITE 16.5.0 render record (draws = no error and nonblank >= 0.005,
     the rule in x3d.ml demo/tether-firehose-v3.template.html)
  2. the eval-plan runs (xdomain/eval-plan/runs/, gitignored): per-document Gemini judge scores are looked for and reported
  3. the hand-built adversarial set (adversarial.py)
Writes results/offline.json and prints the summary. usage: offline.py [--live DIR] (default $X3D_ML or /home/claude/x3d.ml)"""
import argparse, collections, hashlib, json, os, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metric as M, specs as SP, adversarial as ADV  # noqa: E402

DRAW_MIN = 0.005


def auc(pos, neg):
    """Probability that a random positive outranks a random negative (ties count half)."""
    if not pos or not neg: return None
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg); return w / (len(pos) * len(neg))


def live(root):
    run = root / "runs" / "live-2026-10-17"; specs = SP.live_specs()
    ev = {}
    for l in (run / "events.jsonl").read_text().splitlines():
        e = json.loads(l); ev[(e["model"].replace("/", "_"), e["prompt_id"], e["attempt"])] = e
    rpath = root / "demo" / "data" / "renders_live_x_ite_16.5.0.json"; R = json.loads(rpath.read_text()) if rpath.exists() else {}
    rows = []
    for f in sorted((run / "x3d").glob("*/*.x3d")):
        model = f.parent.name; pid, att = f.stem.rsplit("_a", 1); att = int(att); text = f.read_text(encoding="utf-8")
        e = ev.get((model, pid, att), {}); sp = specs[pid]; s = M.score(text, sp)
        rr = R.get(f"{model}/{f.name}")
        rows.append(dict(model=model, pid=pid, attempt=att, sha=hashlib.sha256(text.encode()).hexdigest()[:16], sha_matches_event=e.get("sha", "")[:16] == hashlib.sha256(text.encode()).hexdigest()[:16],
                         score=s.score, parts=s.parts, xsd=s.details.get("xsd_valid", False), strict=s.details.get("strict_valid", False),
                         run_valid=e.get("valid"), constraints_ok=e.get("constraints_ok"), draws=(None if rr is None else bool(not rr.get("err") and (rr.get("nonblank") or 0) >= DRAW_MIN)),
                         profile=s.details.get("profile"), minimal_profile=s.details.get("minimal_profile"), unlawful=s.details.get("unlawful", 0),
                         semantic=s.details.get("semantic_errors", []), feedback=s.feedback, final=False))
    last = {}
    for r in rows: last[(r["model"], r["pid"])] = max(last.get((r["model"], r["pid"]), 0), r["attempt"])
    for r in rows: r["final"] = r["attempt"] == last[(r["model"], r["pid"])]
    return rows


def summarise_live(rows):
    n = len(rows); S = {}
    S["n_docs"] = n; S["by_model"] = dict(collections.Counter(r["model"] for r in rows)); S["prompts"] = len({r["pid"] for r in rows})
    S["sha_matches_event"] = sum(r["sha_matches_event"] for r in rows)
    S["well_formed"] = sum(r["parts"]["well_formed"] == 1 for r in rows); S["xsd_valid"] = sum(r["xsd"] for r in rows); S["strict_valid"] = sum(r["strict"] for r in rows)
    S["strict_agrees_with_run_record"] = sum(1 for r in rows if r["run_valid"] is not None and r["run_valid"] == r["strict"]); S["run_record_n"] = sum(r["run_valid"] is not None for r in rows)
    sv = [r for r in rows if r["strict"]]; nv = [r for r in rows if not r["strict"]]
    S["auc_metric_vs_strict"] = round(auc([r["score"] for r in sv], [r["score"] for r in nv]), 4)
    S["auc_metric_vs_xsd"] = round(auc([r["score"] for r in rows if r["xsd"]], [r["score"] for r in rows if not r["xsd"]]), 4)
    # same prompt, same model: pairs where one attempt is strict-valid and one is not
    by = collections.defaultdict(list)
    for r in rows: by[(r["model"], r["pid"])].append(r)
    conc = disc = tie = 0
    for g in by.values():
        for a in g:
            for b in g:
                if a["strict"] and not b["strict"]:
                    conc += a["score"] > b["score"]; disc += a["score"] < b["score"]; tie += a["score"] == b["score"]
    S["paired_attempts_valid_ranked_higher"] = dict(higher=conc, lower=disc, tie=tie)
    S["metric_mean"] = dict(strict_valid=round(statistics.mean(r["score"] for r in sv), 4) if sv else None, xsd_only=round(statistics.mean(r["score"] for r in rows if r["xsd"] and not r["strict"]), 4) if any(r["xsd"] and not r["strict"] for r in rows) else None,
                            xsd_invalid=round(statistics.mean(r["score"] for r in rows if not r["xsd"]), 4) if any(not r["xsd"] for r in rows) else None)
    S["strict_valid_metric_1"] = sum(1 for r in sv if r["score"] >= 0.9999)
    S["strict_valid_part_below_1"] = {k: sum(1 for r in sv if r["parts"][k] is not None and r["parts"][k] < 1) for k in M.W}
    S["strict_valid_unlawful_docs"] = sum(1 for r in sv if r["unlawful"])
    S["xsd_valid_unlawful_docs"] = sum(1 for r in rows if r["xsd"] and r["unlawful"])
    S["larger_profile_than_needed_strict_valid"] = sum(1 for r in sv if r["profile"] in M.PROFILE_CHAIN and r["minimal_profile"] in M.PROFILE_CHAIN and M.PROFILE_CHAIN.index(r["profile"]) > M.PROFILE_CHAIN.index(r["minimal_profile"]))
    S["profiles"] = dict(collections.Counter(r["profile"] for r in rows)); S["minimal_profiles_strict_valid"] = dict(collections.Counter(r["minimal_profile"] for r in sv))
    # use_type vs the run's own constraint check (string counts)
    cc = [r for r in rows if r["constraints_ok"] is not None and r["parts"]["well_formed"] == 1]
    tab = collections.Counter((bool(r["constraints_ok"]), r["parts"]["use_type"] >= 0.9999) for r in cc)
    S["use_type_vs_constraints_ok"] = {f"constraints_{a}_use_type_full_{b}": tab[(a, b)] for a in (True, False) for b in (True, False)}
    # renders
    dr = [r for r in rows if r["draws"] is not None and r["xsd"]]
    S["render_record_xsd_valid"] = len(dr); S["render_draws_nothing_xsd_valid"] = sum(not r["draws"] for r in dr)
    S["auc_metric_vs_draws_among_xsd_valid"] = round(auc([r["score"] for r in dr if r["draws"]], [r["score"] for r in dr if not r["draws"]]), 4) if dr else None
    blank = [r for r in dr if not r["draws"]]
    S["blank_renders"] = [dict(doc=f"{r['model']}/{r['pid']}_a{r['attempt']}", score=r["score"], strict=r["strict"], parts=r["parts"]) for r in blank]
    # spatial
    spr = [r for r in sv if r["parts"]["spatial"] is not None]
    S["spatial_judged_strict_valid"] = len(spr); S["spatial_full"] = sum(r["parts"]["spatial"] >= 0.9999 for r in spr)
    S["finals"] = dict(n=sum(r["final"] for r in rows), strict=sum(r["final"] and r["strict"] for r in rows), metric_1=sum(r["final"] and r["score"] >= 0.9999 for r in rows))
    # examples where the metric and strict validity disagree most
    lo = sorted(sv, key=lambda r: r["score"])[:8]; hi = sorted(nv, key=lambda r: -r["score"])[:5]
    ex = lambda r: dict(doc=f"{r['model']}/{r['pid']}_a{r['attempt']}", score=r["score"], parts=r["parts"], feedback=r["feedback"].splitlines()[:4])
    S["strict_valid_lowest_metric"] = [ex(r) for r in lo]; S["strict_invalid_highest_metric"] = [ex(r) for r in hi]
    # failure classes inside strict-valid documents
    cls = collections.Counter()
    for r in sv:
        for line in r["feedback"].splitlines():
            if "wrong-type USE" in line: cls["wrong-type USE"] += 1
            elif line.startswith("[use_type]") and "never driven" in line: cls["interpolator not driven"] += 1
            elif line.startswith("[use_type]") and "drives nothing" in line: cls["interpolator drives nothing"] += 1
            elif line.startswith("[use_type]") and "needs at least" in line: cls["count below request"] += 1
            elif line.startswith("[use_type]") and "needs a" in line: cls["requested kind missing"] += 1
            elif line.startswith("[spatial]") and "float free" in line: cls["floating parts"] += 1
            elif line.startswith("[spatial] FAIL"): cls["relation fails"] += 1
            elif line.startswith("[hatches]") and "Full" in line: cls["profile Full"] += 1
            elif line.startswith("[hatches]") and "larger than needed" in line: cls["profile larger than needed"] += 1
            elif line.startswith("[hatches]") and "repeats what" in line: cls["component repeats the profile"] += 1
            elif line.startswith("[hatches]") and "widens" in line: cls["component widens, unused"] += 1
            elif line.startswith("[hatches]") and "Script" in line: cls["unrequested Script"] += 1
    S["strict_valid_failure_lines"] = dict(cls.most_common())
    return S


def eval_plan_judge():
    runs = HERE.parent / "eval-plan" / "runs"
    found = sorted(str(p.relative_to(HERE.parent.parent)) for p in runs.glob("judge-x3d-*.jsonl")) if runs.exists() else []
    return dict(runs_dir_exists=runs.exists(), judge_files=found,
                note=("xdomain/eval-plan/runs/ is gitignored and absent from this checkout and from every other checkout on this machine; "
                      "only RESULTS.md aggregates are committed (x3d: 118 valid documents judged, every one 2/2, judge vs count check 118/118). "
                      "A judge with no variance on valid documents cannot be ranked against; per-document agreement needs the runs/ files.") if not found else "")


def adversarial():
    S, ctl, C = ADV.cases(); out = []
    cs = {k: M.score(d, S[k]) for k, d in ctl.items()}
    for name, k, part, d in C:
        r = M.score(d, S[k])
        out.append(dict(case=name, spec=k, target=part, score=r.score, control=cs[k].score, part=r.parts[part], xsd=r.details["xsd_valid"], strict=r.details["strict_valid"],
                        caught=bool(r.score < cs[k].score and (r.parts[part] if r.parts[part] is not None else 0) < 1), feedback=r.feedback.splitlines()[0]))
    return dict(controls={k: dict(score=v.score, parts=v.parts) for k, v in cs.items()}, cases=out, caught=sum(c["caught"] for c in out), n=len(out),
                xsd_passes=sum(c["xsd"] for c in out), strict_passes=sum(c["strict"] for c in out))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--live", default=os.environ.get("X3D_ML", "/home/claude/x3d.ml")); a = ap.parse_args()
    res = dict(metric_weights=M.W, tolerance=M.TOL)
    root = Path(a.live)
    if (root / "runs" / "live-2026-10-17" / "events.jsonl").exists():
        rows = live(root); res["live"] = summarise_live(rows)
        (HERE / "results").mkdir(exist_ok=True)
        (HERE / "results" / "live_scores.jsonl").write_text("\n".join(json.dumps({k: v for k, v in r.items() if k != "feedback"}) for r in rows) + "\n")
    else:
        res["live"] = dict(missing=str(root))
    res["eval_plan_judge"] = eval_plan_judge(); res["adversarial"] = adversarial()
    (HERE / "results").mkdir(exist_ok=True); (HERE / "results" / "offline.json").write_text(json.dumps(res, indent=1))
    L = res["live"]
    if "n_docs" in L:
        print(f"live: {L['n_docs']} documents, {L['prompts']} prompts; well-formed {L['well_formed']}, XSD-valid {L['xsd_valid']}, strict-valid {L['strict_valid']} "
              f"(strict agrees with the run's record on {L['strict_agrees_with_run_record']}/{L['run_record_n']})")
        print(f"  AUC metric vs strict {L['auc_metric_vs_strict']}, vs XSD {L['auc_metric_vs_xsd']}; same-prompt attempts {L['paired_attempts_valid_ranked_higher']}")
        print(f"  metric mean: {L['metric_mean']}; strict-valid at 1.0: {L['strict_valid_metric_1']}/{L['strict_valid']}; parts below 1 among strict-valid: {L['strict_valid_part_below_1']}")
        print(f"  failure lines in strict-valid docs: {L['strict_valid_failure_lines']}")
        print(f"  use_type vs constraints_ok: {L['use_type_vs_constraints_ok']}")
        print(f"  renders: {L['render_draws_nothing_xsd_valid']} of {L['render_record_xsd_valid']} XSD-valid draw nothing; AUC metric vs draws {L['auc_metric_vs_draws_among_xsd_valid']}")
        print(f"  spatial judged on {L['spatial_judged_strict_valid']} strict-valid docs, full marks {L['spatial_full']}; finals {L['finals']}")
    else: print("live corpus not found:", L)
    J = res["eval_plan_judge"]; print("eval-plan judge files:", J["judge_files"] or "none.", J["note"][:160])
    A = res["adversarial"]; print(f"adversarial: caught {A['caught']}/{A['n']} (XSD passes {A['xsd_passes']}, strict passes {A['strict_passes']})")
    for c in A["cases"]: print(f"  {'caught' if c['caught'] else 'MISSED'} {c['case']}: {c['score']} vs control {c['control']}, {c['target']}={c['part']}, xsd={c['xsd']} strict={c['strict']}")
    return res


if __name__ == "__main__": main()
