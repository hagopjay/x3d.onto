"""'Looks right' for the A/B: render every valid held-out scene (run 0 of each arm) with X_ITE 16.5.1 headless (render.mjs from spine/render),
then judge a 2x2 contact sheet against the request with gemini-3.8-flash (same rubric as spine/e1/render_check.py: 0 nothing asked for is visible .. 3 all of it).
A screen, not truth: judges miss real defects. Usage: render_eval.py <out_dir> <arm> [<arm>...]  (reads eval_<arm>.json)"""
import base64, io, json, os, re, subprocess, sys, time, urllib.request, concurrent.futures as cf
from PIL import Image
sys.path.insert(0, "/mnt/project-files/research/dspy-2026-10-17/code"); import vertex_lm as V
OUT, ARMS = sys.argv[1], sys.argv[2:]
prompts = {}
for l in open("/mnt/project-files/research/dspy-2026-10-17/data/e1_flash_r1_pred.jsonl"):
    rq = json.loads(l)["request"]; ref = re.findall(r"\[ref ([^\]]+)\]", json.dumps(rq))[-1]; _, cond, pid, _ = ref.rsplit("|", 3)
    user = rq["contents"][0]["parts"][0]["text"]; prompts[pid] = user.split("\n\nRequest: ", 1)[1] if user.startswith("Two valid X3D scenes") else user
rows = {}; jobs = []; os.makedirs(f"{OUT}/scenes", exist_ok=True)
for arm in ARMS:
    for r in json.load(open(f"{OUT}/eval_{arm}.json")):
        if r["run"] != 0 or not r["valid"]: continue
        sid = f"{arm}_{r['pid'].replace(':', '_')}"; p = f"{OUT}/scenes/{sid}.x3d"; x = S_x = re.search(r"<X3D[\s>].*?</X3D>", r["x3d"], re.S); x = x.group(0) if x else r["x3d"]
        open(p, "w").write(x); jobs.append({"scene_id": sid, "path": os.path.abspath(p), "bytes": len(x)}); rows[sid] = dict(arm=arm, pid=r["pid"], ok=r["ok"])
open(f"{OUT}/jobs.jsonl", "w").write("\n".join(json.dumps(j) for j in jobs) + "\n")
res_f = f"{OUT}/render_res.jsonl"
if os.path.exists(res_f): os.remove(res_f)
subprocess.run(["node", "render.mjs", f"{OUT}/jobs.jsonl", f"{OUT}/png", res_f, "3"], check=True)
res = {json.loads(l)["scene_id"]: json.loads(l) for l in open(res_f)}
SCHEMA = {"type": "OBJECT", "properties": {"score": {"type": "INTEGER"}, "present": {"type": "ARRAY", "items": {"type": "STRING"}}, "missing": {"type": "ARRAY", "items": {"type": "STRING"}}, "note": {"type": "STRING"}}, "required": ["score", "present", "missing", "note"]}
PROMPT = """You check 3D scenes against the request that produced them.
Request: {prompt}
The image is a 2x2 contact sheet rendered by an X3D browser: top-left is the author's viewpoint, the other three orbit the scene.
Judge only what is visible. Animation and interaction cannot be seen in stills: do not mark them missing, and do not count them either way.
Return JSON: score 0 to 3 (0 nothing asked for is visible, 1 a little, 2 most of it, 3 all of it), the requested elements present and missing, and one short note."""
tok = lambda: subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
def sheet(views):
    im = Image.new("RGB", (1024, 768))
    for v in views[:4]: im.paste(Image.open(v["file"]).convert("RGB"), ((v["view_index"] % 2) * 512, (v["view_index"] // 2) * 384))
    im = im.resize((768, 576)); b = io.BytesIO(); im.save(b, "JPEG", quality=85); return base64.b64encode(b.getvalue()).decode()
def judge(sid):
    m = rows[sid]; r = res.get(sid, {}); views = r.get("views", []); best = max([v["nonblank_ratio"] for v in views] or [0])
    out = {"scene_id": sid, **m, "load_ok": r.get("load_ok"), "nonblank_max": best}
    if best <= 0.005: out.update(score=0, note="blank render"); return out
    body = {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "image/jpeg", "data": sheet(views)}}, {"text": PROMPT.format(prompt=prompts[m["pid"]])}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "maxOutputTokens": 1024, "temperature": 0, "thinkingConfig": {"thinkingLevel": "LOW"}}}
    url = f"https://aiplatform.googleapis.com/v1/projects/{os.environ['GCP_PROJECT']}/locations/global/publishers/google/models/gemini-3.8-flash:generateContent"
    for k in range(4):
        try:
            rq = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok()}"})
            resp = json.loads(urllib.request.urlopen(rq, timeout=120).read()); u = resp.get("usageMetadata", {})
            j = json.loads("".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"] if not p.get("thought")))
            ti, to = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
            with open(V.LEDGER, "a") as f: f.write(json.dumps({"t": time.time(), "tag": "onto-judge", "model": "gemini-3.8-flash", "in": ti, "out": to, "usd": (ti * .75 + to * 3.75) / 1e6}) + "\n")
            out.update(j); return out
        except Exception as e: time.sleep(3 * 2 ** k); err = str(e)[:100]
    out.update(score=None, note="judge failed: " + err); return out
with cf.ThreadPoolExecutor(4) as ex: judged = list(ex.map(judge, list(rows)))
json.dump(judged, open(f"{OUT}/looks_right.json", "w"), indent=1)
for arm in ARMS:
    r = [x for x in judged if x["arm"] == arm]; sc = [x["score"] for x in r if x["score"] is not None]
    print(f"{arm}: valid {len(r)} | blank {sum(1 for x in r if x['nonblank_max'] <= 0.005)} | judge>=2 {sum(1 for s in sc if s >= 2)} | judge 3 {sum(1 for s in sc if s == 3)} | all four (valid+placed+usetype+judge>=2) {sum(1 for x in r if x['ok'] and (x['score'] or 0) >= 2)}")
