#!/usr/bin/env python3
"""Gemini judge for fidelity ("does this document do what was asked?"), run on VALID documents only, blind to arm and to validator output.
Complements the mechanical completeness check (H4). Calls go through tools/vertex.py (ledger, cap). Requires GO.json. Every verdict and reason is logged.
usage: judge.py --domain D --model M --judge gemini-3.8-flash [--max N]  -> runs/judge-D-M.jsonl"""
import argparse, json, os, random, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; XD = HERE.parent
sys.path.insert(0, str(HERE))
import prompts as P
ap = argparse.ArgumentParser(); ap.add_argument("--domain", required=True); ap.add_argument("--model", required=True); ap.add_argument("--judge", default="gemini-3.8-flash"); ap.add_argument("--max", type=int, default=0); ap.add_argument("--cap", type=float, default=2.0); ap.add_argument("--location", default="us-east4"); ap.add_argument("--workers", type=int, default=6); a = ap.parse_args()
go = json.loads((HERE / "GO.json").read_text()); assert go.get("approved_by") == "user" and a.judge in go["models"] and a.cap <= go["cap_usd"]
if os.environ.get("GEMINI_BACKEND") == "api": from gemini_api import call   # API key instead of Vertex; same ledger/cap contract
else: sys.path.insert(0, str(XD.parent.parent / "tools")); from vertex import call
runs = HERE / "runs"; rows = [json.loads(l) for l in (runs / f"{a.domain}-{a.model}.jsonl").read_text().splitlines()]
raw = [json.loads(l) for l in (runs / f"raw-{a.domain}-{a.model}.jsonl").read_text().splitlines()]
byp = {r["purpose"].replace("xdomain-eval ", ""): r["text"] for r in raw}
if a.domain == "x3d":
    sys.path.insert(0, str(HERE)); import x3d_domain as X3; _T = X3.X3D
else: _T = P.URDF if a.domain == "urdf" else P.GLTF
desc = {t[0]: t[2] for t in _T}
def extract(t):
    b = re.findall(r"```[a-zA-Z]*\n(.*?)```", t, re.S); return max(b, key=len).strip() if b else t.strip()
todo = []
for r in rows:
    if r["arm"] in ("A0", "A2-final", "A1") and r["valid"]:
        pur = f"{a.domain}:{r['arm'] if r['arm']!='A2-final' else 'A2'}:{r['pid']}:{r['sample']}"
        key = [k for k in byp if k.startswith(pur) and ((r["arm"] == "A2-final" and k.endswith(f":r{r['round']}")) or r["arm"] != "A2-final")]
        if key: todo.append((r, extract(byp[key[-1] if r["arm"] == "A2-final" else key[0]])))
random.Random(7).shuffle(todo)
if a.max: todo = todo[:a.max]
import threading
from concurrent.futures import ThreadPoolExecutor
jpath = runs / f"judge-{a.domain}-{a.model}.jsonl"; done = {}
if jpath.exists():
    for l in jpath.read_text().splitlines():
        try: r = json.loads(l); done[(r["pid"], r["sample"], r["arm"])] = r
        except Exception: pass
lock = threading.Lock(); st = dict(spent=sum(r.get("est_usd", 0) for r in done.values()))
def one(item):
    r, doc = item
    if (r["pid"], r["sample"], r["arm"]) in done: return None
    with lock:
        if st["spent"] >= a.cap: return None
    q = (f"You are checking a generated {'URDF robot description' if a.domain == 'urdf' else 'glTF 2.0 file' if a.domain == 'gltf' else 'X3D scene'} against a request.\nRequest: {desc[r['pid']]}.\n\nDocument:\n```\n{doc[:12000]}\n```\n\n"
         'Does the document actually describe what was requested (right parts, counts, relations), ignoring whether it is syntactically valid? Reply as JSON: {"score": 0|1|2, "reason": "one sentence"} where 2 = fully, 1 = partly, 0 = no.')
    for attempt in range(4):
        try: res = call(a.judge, [q], location=a.location, max_tokens=600, temperature=0.0, json_out=True, purpose=f"xdomain-judge {a.domain}:{r['arm']}:{r['pid']}:{r['sample']}"); break
        except Exception as e:
            if attempt == 3: return dict(pid=r["pid"], sample=r["sample"], arm=r["arm"], mech_complete=r["complete"], score=None, reason="call failed: " + repr(e)[:80], est_usd=0)
            time.sleep(10 * (attempt + 1))
    try: j = json.loads(res["text"])
    except Exception: j = {"score": None, "reason": res["text"][:120]}
    row = dict(pid=r["pid"], sample=r["sample"], arm=r["arm"], mech_complete=r["complete"], score=j.get("score"), reason=j.get("reason"), est_usd=round(res["est_usd"], 5))
    with lock:
        st["spent"] += res["est_usd"]
        with open(jpath, "a") as f: f.write(json.dumps(row) + "\n")
    return row
import time
with ThreadPoolExecutor(max_workers=a.workers) as ex: list(ex.map(one, todo))
print(f"judge {a.domain}: {len(todo)} candidate documents, est ${st['spent']:.2f} cumulative")
