#!/usr/bin/env python3
"""Gemini vision judge on rendered frames, via gemini_api.py (API key, shared ledger, cap). Protocol follows gobbler-demiurge/docs/PICTURE-JUDGE.md
without the owner's reference stills (they are private): each frame is scored 1-10 on beauty, clarity, polish and plausibility of the 3D build,
plus one fix and one keep, by K votes per frame. --repeat judges every frame twice so the judge's own noise floor is measured in the same run.
usage: frame_judge.py FRAME_DIR [--model M] [--votes 3] [--repeat] [--out runs/frames-<name>.jsonl]"""
import argparse, json, statistics, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from gemini_api import call
ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("--model", default="gemini-2.5-flash"); ap.add_argument("--votes", type=int, default=3)
ap.add_argument("--repeat", action="store_true"); ap.add_argument("--out"); ap.add_argument("--workers", type=int, default=6); a = ap.parse_args()
frames = sorted(p for p in Path(a.dir).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
out = Path(a.out or f"runs/frames-{Path(a.dir).name}-{a.model}.jsonl"); out.parent.mkdir(exist_ok=True)
Q = ("This is a still rendered in a web browser from an X3D scene that an AI pipeline built. Judge it as a picture of a 3D build.\n"
     'Reply as JSON: {"beauty": 1-10, "clarity": 1-10, "polish": 1-10, "plausibility": 1-10, "black_or_broken": true|false, '
     '"fix": "the one concrete change that would most improve this frame", "keep": "the one thing to keep"}')
CRIT = ("beauty", "clarity", "polish", "plausibility")
def one(job):
    f, rnd, v = job
    try: r = call(a.model, [Q, f], max_tokens=2000, temperature=0.8, json_out=True, purpose=f"frame-judge {f.name} r{rnd} v{v}")
    except Exception as e: return dict(frame=f.name, round=rnd, vote=v, error=repr(e)[:160])
    try: j = json.loads(r["text"]); s = statistics.mean(float(j[c]) for c in CRIT)
    except Exception: j, s = {"raw": r["text"][:200]}, None
    return dict(frame=f.name, round=rnd, vote=v, model=a.model, score=s, **j, est_usd=round(r["est_usd"], 6))
jobs = [(f, rnd, v) for rnd in range(2 if a.repeat else 1) for f in frames for v in range(a.votes)]
with ThreadPoolExecutor(a.workers) as ex: rows = list(ex.map(one, jobs))
out.write_text("".join(json.dumps(r) + "\n" for r in rows))
ok = [r for r in rows if r.get("score") is not None]
per = {(r["frame"], r["round"]): [] for r in ok}
for r in ok: per[(r["frame"], r["round"])].append(r["score"])
print(f"{len(ok)}/{len(rows)} votes landed, est ${sum(r.get('est_usd', 0) for r in rows):.3f}, -> {out}")
for rnd in sorted({k[1] for k in per}):
    m = [statistics.mean(v) for k, v in sorted(per.items()) if k[1] == rnd]; print(f"round {rnd}: mean {statistics.mean(m):.2f} over {len(m)} frames")
if a.repeat:
    d = [statistics.mean(per[(f.name, 1)]) - statistics.mean(per[(f.name, 0)]) for f in frames if (f.name, 0) in per and (f.name, 1) in per]
    if len(d) > 1: print(f"noise floor: same frames judged twice, mean diff {statistics.mean(d):+.2f}, sd per frame {statistics.stdev(d):.2f}, n={len(d)}")
for f in frames:
    s = [r["score"] for r in ok if r["frame"] == f.name]
    if s: print(f"  {f.name:28s} {statistics.mean(s):.2f}  fix: {next((r.get('fix') for r in ok if r['frame'] == f.name), '')[:90]}")
