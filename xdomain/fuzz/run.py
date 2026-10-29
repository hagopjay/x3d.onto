#!/usr/bin/env python3
"""Differential fuzzer for the X3D validation stack: generate scenes, run every oracle, bucket the disagreements, minimise one reproducer
per signature, write the findings table.
  python3 -I xdomain/fuzz/run.py [--n 2000] [--seed 1] [--no-xite] [--render] [--min-max 400] [--out xdomain/fuzz/findings]
Scene mix: 40% sampled from X3DUOM ranges, 30% from the verified matrix, 30% mutants of excerpts of real scenes in this repo; depth 1 to 5."""
import argparse, json, os, re, sys, time, hashlib
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model, gen, oracles, classify, minimize  # noqa

XITE_BUCKETS = {"xsd_valid_xite_drops", "xsd_valid_xite_warns", "semantic_false_alarm", "semantic_silent_drop", "profile_mismatch"}


def make_scenes(n, seed, M):
    out = []
    for i in range(n):
        r = i % 10
        if r < 4: out.append(("uom", gen.scene(seed, i, "uom", M=M), []))
        elif r < 7: out.append(("verified", gen.scene(seed, i, "verified", M=M), []))
        else:
            x, ops = gen.mutate(seed, i, M=M); out.append(("mutant", x, ops))
    return out


def evaluate(xmls, xite):
    res = [oracles.python_oracles(x) for x in xmls]
    if xite is not None:
        for r, xr in zip(res, xite.run(xmls)): r["xite"] = xr
    return res


def slug(sig):
    s = "-".join(str(x) for x in sig[1:4] if x)
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:70].strip("_")
    return f"{s}-{hashlib.sha1(repr(sig).encode()).hexdigest()[:6]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-xite", action="store_true"); ap.add_argument("--render", action="store_true")
    ap.add_argument("--min-max", type=int, default=400, help="signatures to minimise at most")
    ap.add_argument("--out", default=str(HERE / "findings"))
    a = ap.parse_args()
    t0 = time.time(); M = model.load(); gen.scene_roots(M); t_roots = time.time() - t0
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for b in classify.BUCKETS:
        for old in (out / b).glob("*.x3d"): old.unlink()   # residue/ belongs to residue.py
    xite = None if a.no_xite else oracles.Xite(render=a.render)
    t1 = time.time(); scenes = make_scenes(a.n, a.seed, M); t_gen = time.time() - t1
    t1 = time.time(); res = evaluate([s[1] for s in scenes], xite); t_eval = time.time() - t1
    per_bucket_scenes = Counter(); sigs = defaultdict(list); verdicts = Counter(); by_mode = defaultdict(Counter)
    for idx, ((mode, xml, ops), o) in enumerate(zip(scenes, res)):
        verdicts[("xsd_valid" if o["xsd"]["valid"] else "xsd_invalid", "uom_clean" if not o["uom"]["violations"] else "uom_flags")] += 1
        fs = classify.classify(xml, o, M)
        for b in {f[0] for f in fs}: per_bucket_scenes[b] += 1; by_mode[b][mode] += 1
        for b, sig, det in fs: sigs[(b, sig)].append((len(xml), idx, det))
    # which of the 441 residue pairs did random generation reach on its own?
    res_set = {(c, p, f) for c, p, f, e in model.residue_pairs(M)}
    hit = {tuple(d["pair"]) for (b, s), v in sigs.items() if b == "uom_allows_xsd_rejects" for _, _, d in v if d.get("pair")}
    a_pairs = len(hit); a_in_res = len(hit & res_set)
    # minimise: smallest example of each signature
    t1 = time.time(); rows = []
    order = sorted(sigs, key=lambda k: (classify.BUCKETS.index(k[0]), -len(sigs[k])))
    for k_i, (b, sig) in enumerate(order):
        ex = sorted(sigs[(b, sig)])[0]; xml = scenes[ex[1]][1]
        need_x = b in XITE_BUCKETS and xite is not None
        def holds(cands, b=b, sig=sig, need_x=need_x):
            ok = []
            rs = [oracles.python_oracles(c) for c in cands]
            if need_x:
                for r, xr in zip(rs, xite.run(cands)): r["xite"] = xr
            for c, r in zip(cands, rs):
                try: ok.append(any(f[0] == b and f[1] == sig for f in classify.classify(c, r, M)))
                except Exception: ok.append(False)
            return ok
        small = minimize.minimize(xml, holds) if k_i < a.min_max else xml
        small = minimize.pretty(small)
        rep = holds([small])[0]
        name = f"{b}/{slug(sig)}.x3d"; (out / b).mkdir(exist_ok=True); (out / name).write_text(small)
        final = evaluate([small], xite)[0]
        rows.append(dict(bucket=b, signature=list(sig), scenes=len(sigs[(b, sig)]), file=name, bytes=len(small), elements=small.count("<") - small.count("</") - 2,
                         reproduces=rep, minimised=k_i < a.min_max, detail=sigs[(b, sig)][0][2],
                         xsd=final["xsd"], uom=final["uom"]["violations"][:3], sem_errors=[d for d in final["sem"]["diags"] if d["level"] == "error"][:3],
                         profile_ok=final["prof"].get("ok"), xite={k: final["xite"].get(k) for k in ("warn", "error", "routes", "exc")} if "xite" in final else None))
    t_min = time.time() - t1
    bucket_sigs = Counter(r["bucket"] for r in rows)
    summary = dict(n=a.n, seed=a.seed, xite=None if xite is None else xite.info, render=a.render, uom_sha1=M.uom_sha1, fork=str(model.FORK),
                   scenes_by_verdict={f"{k[0]}/{k[1]}": v for k, v in verdicts.items()},
                   buckets={b: {"scenes": per_bucket_scenes.get(b, 0), "signatures": bucket_sigs.get(b, 0), "by_mode": dict(by_mode.get(b, {}))} for b in classify.BUCKETS},
                   seconds=dict(roots=round(t_roots, 1), generate=round(t_gen, 1), oracles=round(t_eval, 1), xite_ms_in_page=None if xite is None else xite.ms,
                                minimise=round(t_min, 1), total=round(time.time() - t0, 1)),
                   reproducers_verified=sum(r["reproduces"] for r in rows), reproducers=len(rows),
                   residue=dict(pairs=len(res_set), uom_allows_xsd_rejects_pairs_seen=a_pairs, of_which_in_the_441=a_in_res))
    (out / "findings.json").write_text(json.dumps(dict(summary=summary, rows=rows), indent=1))
    write_table(out, summary, rows)
    if xite: xite.close()
    print(json.dumps(summary, indent=1))


def write_table(out, s, rows):
    L = [f"# Fuzz findings (seed {s['seed']}, {s['n']} scenes)", "", "Generated by `xdomain/fuzz/run.py`; numbers are what the tools reported on this machine (grade C). "
         "Whether a row is a specification error or a validator bug is not decided here (S).", "",
         "| bucket | scenes | signatures |", "|---|---:|---:|"]
    for b, v in s["buckets"].items(): L.append(f"| {b} | {v['scenes']} | {v['signatures']} |")
    L += ["", f"Scenes by verdict: {s['scenes_by_verdict']}. Run time (s): {s['seconds']}.", "",
          f"Residue: of the (child, parent, field) placements behind uom_allows_xsd_rejects, {s['residue']['uom_allows_xsd_rejects_pairs_seen']} distinct were seen, "
          f"{s['residue']['of_which_in_the_441']} of them among the {s['residue']['pairs']} residue pairs (the rest are combinations the matrix's one-child documents never test). "
          "The pair-by-pair adjudication of all 441 is in residue.json (`residue.py`).", "", "| bucket | signature | scenes | reproducer | elements | reproduces |", "|---|---|---:|---|---:|---|"]
    for r in rows:
        sig = " / ".join(str(x) for x in r["signature"][1:]).replace("|", "\\|")
        L.append(f"| {r['bucket']} | {sig[:150]} | {r['scenes']} | [{r['file']}]({r['file']}) | {r['elements']} | {'yes' if r['reproduces'] else 'NO'} |")
    (out / "TABLE.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
