"""Free calibration: run the three metric terms over cached writer answers (a JSONL file, one answer per line). No model calls."""
import json, sys, collections, os
sys.path.insert(0, os.path.dirname(__file__)); import scene_metric as S
rows = [json.loads(l) for l in open(sys.argv[1])]; C = collections.Counter(); ex = {}
for r in rows:
    txt = r.get("text") or r.get("response") if isinstance(r.get("text") or r.get("response"), str) else None
    if txt is None:  # nested provider shapes: walk to the first list of parts carrying text
        def _walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("text"), str): yield o["text"]
                for v in o.values(): yield from _walk(v)
            elif isinstance(o, list):
                for v in o: yield from _walk(v)
        txt = "".join(_walk(r.get("response", r)))
    if not txt: continue
    c = S.check(txt); k = (c["valid"], c["placed"], not c["mismatch"]); C[k] += 1
    if k != (True, True, True): ex.setdefault(k, (S.report(c)[:300]))
print("n", sum(C.values()))
for k, v in sorted(C.items(), reverse=True): print("valid=%s placed=%s usetype_ok=%s: %d" % (*k, v))
for k, v in ex.items(): print("\n--", k, "\n", v)
json.dump({str(k): v for k, v in C.items()}, open(sys.argv[2], "w"), indent=1)
