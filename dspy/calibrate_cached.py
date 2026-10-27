"""Free calibration: run the three metric terms over the 600 cached E1 flash answers (data/e1_flash_r1_pred.jsonl). No model calls."""
import json, sys, collections, os
sys.path.insert(0, os.path.dirname(__file__)); import scene_metric as S
rows = [json.loads(l) for l in open(sys.argv[1])]; C = collections.Counter(); ex = {}
for r in rows:
    try: txt = "".join(p.get("text", "") for p in r["response"]["candidates"][0]["content"]["parts"])
    except Exception: continue
    c = S.check(txt); k = (c["valid"], c["placed"], not c["mismatch"]); C[k] += 1
    if k != (True, True, True): ex.setdefault(k, (S.report(c)[:300]))
print("n", sum(C.values()))
for k, v in sorted(C.items(), reverse=True): print("valid=%s placed=%s usetype_ok=%s: %d" % (*k, v))
for k, v in ex.items(): print("\n--", k, "\n", v)
json.dump({str(k): v for k, v in C.items()}, open(sys.argv[2], "w"), indent=1)
