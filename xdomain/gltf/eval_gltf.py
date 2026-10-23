#!/usr/bin/env python3
"""Fault-injection run against the Khronos glTF-Validator, with a naive structural baseline. usage: python3 eval_gltf.py -> ../../out/xdomain_gltf.json (needs node)"""
import copy, json, os, subprocess, sys, tempfile, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from corpus import CORPUS; from mutate import F; from repair import repair
OUT = HERE.parent.parent / "out"
def baseline(text):
    """what a format-level check finds without the spec's semantics: JSON parses, asset.version is 2.0, top-level collections are arrays"""
    try: d = json.loads(text)
    except Exception as e: return ["json: " + str(e)[:60]]
    out = []
    if not isinstance(d, dict) or d.get("asset", {}).get("version") != "2.0": out.append("asset.version missing or not 2.0")
    for k in ("scenes", "nodes", "meshes", "accessors", "bufferViews", "buffers", "materials", "textures", "images", "animations"):
        if k in d and not isinstance(d[k], list): out.append(k + " not an array")
    return out
def run_node(files):
    d = tempfile.mkdtemp()
    for name, text in files.items(): Path(d, name + ".gltf").write_text(text)
    p = subprocess.run(["node", str(HERE / "validate.mjs"), d], capture_output=True, text=True, cwd=HERE)
    return {json.loads(l)["file"][:-5]: json.loads(l) for l in p.stdout.splitlines()}
def serialize(d): return d[5:] if isinstance(d, str) and d.startswith("TEXT:") else json.dumps(d)
clean = {k: json.dumps(fn()) for k, fn in CORPUS.items()}
cr = run_node({"clean_" + k: v for k, v in clean.items()})
res = dict(clean={k: dict(errors=cr["clean_" + k]["errors"], warnings=cr["clean_" + k]["warnings"], infos=cr["clean_" + k]["infos"], hints=cr["clean_" + k]["hints"]) for k in clean}, validator=cr["clean_cube"]["version"], faults={}, rows=[], codes=collections.defaultdict(lambda: collections.Counter()))
files = {}; meta = {}
for fid, (level, desc, fn) in F.items():
    for k, fnc in CORPUS.items():
        d = copy.deepcopy(fnc()); m = fn(d)
        if m is None: meta[(fid, k)] = None; continue
        t = serialize(m)
        if t == json.dumps(fnc()): meta[(fid, k)] = None; continue
        files[f"{fid}_{k}"] = t; meta[(fid, k)] = t
vr = run_node(files); tot = collections.Counter(); lat = []
for fid, (level, desc, fn) in F.items():
    c = collections.Counter()
    for k in CORPUS:
        t = meta[(fid, k)]
        if t is None: c["n/a"] += 1; continue
        r = vr[f"{fid}_{k}"]; c["n"] += 1; lat.append(r["ms"])
        b = baseline(t); kh_e, kh_w = r.get("errors", 0), r.get("warnings", 0) + r.get("infos", 0) + r.get("hints", 0)
        v = "L0" if fid == "G25" else ("baseline" if b else ("khronos-error" if kh_e else ("khronos-warning" if kh_w else "missed")))
        c[v] += 1; c["khronos_error_total"] += bool(kh_e); c["baseline_total"] += bool(b); codes = sorted({m["code"] for m in r.get("messages", [])})
        for m in r.get("messages", []): res["codes"][fid][m["code"]] += 1
        res["rows"].append(dict(fault=fid, base=k, verdict=v, codes=codes[:6], first=(r["messages"][0]["message"][:110] if r.get("messages") else "")))
    res["faults"][fid] = dict(level=level, desc=desc, **c); tot.update({k: v for k, v in c.items() if k != "n/a"})
# repairs: re-validate with the same oracle
rfiles = {}; applied = {}
for (fid, k), t in meta.items():
    if t is None or fid == "G25": continue
    fixed, done = repair(t)
    if done: rfiles[f"{fid}_{k}"] = fixed; applied[f"{fid}_{k}"] = done
rv = run_node(rfiles) if rfiles else {}
rep = collections.Counter()
for key, r in rv.items():
    before = vr[key]; ok = r["errors"] == 0 and r["warnings"] <= before["warnings"] and before["errors"] > 0
    rep["fixed" if ok else ("partial" if r["errors"] < before["errors"] else "no-help")] += 1
res["repair"] = dict(attempted=len(rv), outcome=dict(rep), applied_rules=sorted({a[0] for v in applied.values() for a in v}))
# repair on clean documents must change nothing
res["repair"]["noop_on_clean"] = all(repair(t)[1] == [] for t in clean.values())
res["codes"] = {k: dict(v) for k, v in res["codes"].items()}
res["totals"] = dict(tot); res["latency_ms"] = dict(mean=round(sum(lat) / len(lat), 2), max=round(max(lat), 2), n=len(lat))
(OUT / "xdomain_gltf.json").write_text(json.dumps(res, indent=1))
print("validator", res["validator"], "| clean:", {k: v for k, v in res["clean"].items() if any(v.values())} or "all clean")
for fid, v in res["faults"].items(): print(fid, v["level"], v["desc"][:46].ljust(46), {k: n for k, n in v.items() if k not in ("level", "desc")}, sorted(res["codes"].get(fid, {}))[:3])
print(res["totals"], res["latency_ms"], res["repair"])
