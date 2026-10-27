"""GEPA on a scene-writing prompt with the metric valid AND placed AND use-type-clean (scene_metric.py), then an A/B on held-out prompts:
seed prompt | earlier learned prompt (valid-only metric, 17 Oct) | new learned prompt (this metric). Writer gemini-3.8-flash, reflection gemini-3.1-pro-preview.
Env: GCP_PROJECT, X3D_MCP_TREE (fork main 2b696f5 checkout), DSPY_LEDGER (fresh file so the cap is this run's), DSPY_CAP_USD, OUT.
Prompts and splits are those of research/dspy-2026-10-17/code/run_gepa.py (lib prompts train/val; bench+ood held out)."""
import json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CODE = "/mnt/project-files/research/dspy-2026-10-17/code"; sys.path.insert(1, CODE)
import dspy, scene_metric as S, vertex_lm as V
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/mnt/project-files/spine/e1"); import prompts_sys
OUT = os.environ.get("OUT", "out/dspy"); os.makedirs(OUT, exist_ok=True)
PROJ = os.environ["GCP_PROJECT"]; MAXCALLS = int(os.environ.get("MAXCALLS", "240")); RUNS = int(os.environ.get("EVAL_RUNS", "2"))

class Write(dspy.Signature):
    """Write the X3D scene."""
    request: str = dspy.InputField()
    references: str = dspy.InputField(desc="zero or two valid reference scenes from the checked library, or empty")
    x3d: str = dspy.OutputField(desc="the whole <X3D> document only")
class WriteProg(dspy.Module):
    def __init__(self):
        super().__init__(); self.write = dspy.Predict(Write)
    def forward(self, request, references=""):
        return self.write(request=request, references=references)
def prog_with(instr):
    m = WriteProg(); m.write.signature = m.write.signature.with_instructions(instr); return m

INTRO = "Two valid X3D scenes from a checked library that are similar to the request follow."
ex = {}
for l in open("/mnt/project-files/research/dspy-2026-10-17/data/e1_flash_r1_pred.jsonl"):
    pr = json.loads(l); rq = pr["request"]
    ref = re.findall(r"\[ref ([^\]]+)\]", json.dumps(rq))[-1]; _, cond, pid, _ = ref.rsplit("|", 3)
    user = rq["contents"][0]["parts"][0]["text"]
    refs, request = user.split("\n\nRequest: ", 1) if user.startswith(INTRO) else ("", user)
    ex[(pid, cond)] = dspy.Example(request=request, references=refs, pid=pid).with_inputs("request", "references")
sets = lambda s: [v for (pid, cc), v in sorted(ex.items()) if cc == "none" and pid.split(":")[0] in s]
held = sets({"bench", "ood"}); lib = sets({"lib"}); random.Random(0).shuffle(lib); train, val = lib[:40], lib[40:80]
task = V.VertexLM("gemini-3.8-flash", PROJ, "onto-task"); refl = V.VertexLM("gemini-3.1-pro-preview", PROJ, "onto-reflect"); dspy.configure(lm=task)

def metric(example, pred, trace=None, pred_name=None, pred_trace=None):
    r = S.check(getattr(pred, "x3d", "")); return dspy.Prediction(score=S.score(r), feedback=S.report(r))

def evaluate(instr, tag, runs):
    prog = prog_with(instr); res = {}
    def one(args):
        e, k = args
        try:
            x = prog(**e.inputs()).x3d; c = S.check(x)
            return dict(pid=e.pid, run=k, valid=c["valid"], placed=c["placed"], mismatch=c["mismatch"], x3d=x, ok=c["valid"] and c["placed"] and not c["mismatch"])
        except Exception as err:
            if isinstance(err, V.BudgetExceeded): raise
            return dict(pid=e.pid, run=k, valid=False, placed=False, mismatch=False, x3d="", ok=False, err=str(err)[:100])
    with ThreadPoolExecutor(8) as t: rows = list(t.map(one, [(e, k) for k in range(runs) for e in held]))
    n = len(rows); f = lambda key: sum(r[key] for r in rows)
    print(f"[{tag}] n={n} valid={f('valid')} placed={f('placed')} all3={f('ok')} ({100*f('ok')/n:.1f}%) spent ${V.spent():.2f}", flush=True)
    json.dump(rows, open(f"{OUT}/eval_{tag}.json", "w")); return rows

seed = prompts_sys.SYSTEM
earlier = json.load(open(f"{CODE}/../results/B_prog.json"))["write_instructions"]
for _tag, _ins in (("seed", seed), ("earlier_learned", earlier)):
    if not os.path.exists(f"{OUT}/eval_{_tag}.json"): evaluate(_ins, _tag, RUNS)   # resumable: arms already evaluated are kept
if not os.path.exists(f"{OUT}/new_prompt.json"):
    g = dspy.GEPA(metric=metric, max_metric_calls=MAXCALLS, reflection_lm=refl, reflection_minibatch_size=3, num_threads=8, seed=0, track_stats=True, log_dir=f"{OUT}/gepa_log")
    opt = g.compile(prog_with(seed), trainset=train, valset=val)
    json.dump({"write_instructions": opt.write.signature.instructions, "spent": V.spent()}, open(f"{OUT}/new_prompt.json", "w"), indent=1)
new = json.load(open(f"{OUT}/new_prompt.json"))["write_instructions"]; print("new prompt chars", len(new), flush=True)
evaluate(new, "new_learned", RUNS)
print("DONE spent", V.spent(), flush=True)
