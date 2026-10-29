# The lawful metric and a DSPy program around it (built 2026-10-29)

DIRECTIONS item 16. A graded score for one X3D document against the task that asked for it, built on the fork's own checks plus what they do not cover, and a DSPy "spec -> X3D" program that uses it as its refine step and its metric. Grades: **C** confirmed by a tool run here, **L** likely (my rule or my reading), **S** suspected. No model was called and nothing was spent. Private; no outside contact.

## What it scores (`metric.py`)
| part | weight | what it checks | source of truth |
|---|---|---|---|
| a well_formed | 0.10 | XML, `<X3D>` root, a `<Scene>` | lxml |
| b valid | 0.20 | XSD for the document's version, plus the fork's semantic errors ("strict validity", the gate in `eval-plan/x3d_domain.py`) | fork `validate_xml`, `semantic_diagnostics` |
| c lawful | 0.20 | every parent.field -> child placement accepted by that field's X3DUOM `acceptableNodeTypes` (the X3DUOM of the document's version, 4.0 or 4.1); a USE has its DEF's type; an SFNode field holds one node; each placement is also looked up in the XSD-verified matrix `data/xcheck_all.json` | X3DUOM in the fork; `data/uom_ranges.json` shows UOM ranges agree with the XSD on 93.1% of 9,775 conclusive pairs (C) |
| d use_type | 0.25 | the requested node kinds, counts and exclusions; each requested interpolator is driven (ROUTE into `set_fraction`) and drives a field of its kind (rotation, translation, colour) | the task spec |
| e spatial | 0.15 | named relations (on top of, above, left of, side by side, a row, pointing down) and "no floating parts", from world-space bounding boxes (Box, Sphere, Cone, Cylinder, ElevationGrid, Rectangle2D, Disk2D, coordinate sets; Extrusion approximated); contact within **5%** of the larger extent on the axis (DIRECTIONS E20); None when the task names no relation | my geometry code (L) |
| f hatches | 0.10 | profile Full or none = 0; a profile above the smallest sufficient one (Interchange / Interactive / Immersive, at most one extra component) = 0.75 unless the request orders it; -0.25 per component statement that widens the profile for nothing, -0.05 per one that repeats it; -0.25 per Script / Inline / ExternProtoDeclare not asked for | fork `profile_nodes` |

Scalar = weighted mean of the parts that apply; 0 if not well-formed; halved if not XSD-valid; any unlawful placement halves part c. The feedback text (up to 14 lines, each tagged with its part, with locations and the fix where one is known) is what GEPA reads. Weights, penalties and the 5% rule are my choices (L); change them in `W`, `TOL` and the hatch block.

## Results, model-free (`offline.py`, written to `results/offline.json` and `results/live_scores.jsonl`)
**Recorded corpora.** `xdomain/eval-plan/runs/` (where the eval-plan answers and per-document Gemini judge scores were written) is gitignored and is not on this machine; no `judge-x3d-*.jsonl` exists anywhere here, and no Polys-rerun trial files either. **So there is no per-document judge comparison** (C). The only committed judge numbers are RESULTS.md aggregates: X3D, 118 valid documents judged, every one 2/2. A judge that gives every valid document full marks cannot be ranked against. The corpus used instead is the x3d.ml live run of 2026-10-17 (x3d.ml at 6eb8169, `runs/live-2026-10-17`): 383 recorded documents, 5 models, 50 prompts, up to 3 attempts each; its prompts are copied to `data/prompts_live.jsonl`. The node-kind constraints are the run's own; the spatial relations and "connected" flags for 20 prompts are my reading (L, `specs.py`). The run's system prompt orders profile Immersive, so the specs carry that and declaring it is not counted as a hatch.

| on 383 recorded documents | number | grade |
|---|---|---|
| well-formed / XSD-valid / strict-valid | 319 / 208 / 178 | C |
| strict validity here equals the run's recorded verdict | 383 of 383 | C |
| AUC, metric vs strict validity (vs XSD validity) | 0.997 (1.000) | C |
| same model, same prompt, one attempt strict-valid and one not: metric ranks the valid one higher | 110 of 111 | C |
| mean metric: strict-valid / XSD-valid only / XSD-invalid | 0.992 / 0.885 / 0.230 | C |
| strict-valid documents the metric marks below 1.0 | 26 of 178 | C |
| ... of which: floating parts 10, unrequested Script 8 (6 of them on three interaction prompts, int-01/04/05, where a Script is a fair answer), profile Full 2, wrong-type USE 1, requested kind missing 1, a component that widens the profile for nothing 1; 18 more carry a 0.05 note for a component that repeats the profile | counts C; whether each is a real defect L (I read 3 of the 10 floating cases: a lamp head 2.3 m above its pole, shelves with no sides, and one I could not settle) | |
| strict-valid documents that declare a larger profile than they need (ordered by the run's system prompt) | 164 of 178 | C |
| node-kind check vs the run's own string-count check | agree on 318 of 319 well-formed documents; the 1 split is a document whose interpolator is never driven (the string check only counts tags) | C |
| XSD-valid documents that draw nothing in X_ITE 16.5.0 (draws = no error and nonblank >= 0.005) | 10 of 208; AUC metric vs draws 0.63 | C |

Where the metric and strict validity disagree, by design:
- `gemini-3.1-pro-preview/obj-04`: attempt 1 is strict-invalid (UnlitMaterial outside the Immersive header, by the fork's 4.1 X3DUOM appinfo); attempt 2 "fixes" it by declaring profile Full. Strict validity prefers attempt 2; the metric scores it 0.88 against 0.91. This is the Goodhart route of FACTS 24 in a recorded answer. (C that it happened; L that the metric's order is the right one.)
- `gemini-3.8-flash/sp-10_a2`: strict-valid, `<Group USE='StoneLantern'>` where the DEF is a Transform, under profile Full. The fork passes it; the metric gives 0.76.
- `nvidia_nemotron/asm-04_a2` (street lamp): strict-valid; the lamp head floats 2.3 m above the top of its 5 m pole (pole centred at y=0). Spatial 0.5.
- Blank renders: of the 10 XSD-valid documents that draw nothing, 5 still score 1.0 and one 0.99 (geospatial and proximity-light prompts). The metric does not look at pixels; rung 5 ("visible") needs the render.

**Adversarial set** (`adversarial.py`, 16 hand-built documents next to 4 clean controls that score 1.0): the metric catches **16 of 16** (scores below the control, the targeted part below 1). The XSD passes 15 of them and the strict gate 13 (C).

| family | cases | XSD passes | strict passes | metric |
|---|---|---|---|---|
| valid but unlawful | wrong-type USE (Shape as Transform; Box as Cylinder), Material in a non-existent `geometry` field, Box in Shape.appearance, ImageTexture in PhysicalMaterial's default `texture` field | 4 of 5 | 2 of 5 (both wrong-type USE) | lawful 0.46-0.47, scalar 0.37-0.89 |
| lawful but not what was asked | sphere for a cylinder, cylinder sunk 0.4 into the box, floating 0.6 above, beside it, interpolator never driven, table legs 1 m below the top, cone pointing up | 7 of 7 | 7 of 7 | use_type or spatial below 1, scalar 0.77-0.95 |
| escape hatches | profile Full, an unneeded NURBS component, an unrequested Script, Immersive for a static scene | 4 of 4 | 4 of 4 | hatches 0-0.75, scalar 0.90-0.975 |

Penalty sizes are small for hatches (0.10 weight): a Full-profile scene scores 0.90. Enough to rank it below its control, which is what an optimiser needs; whether it is enough to stop a model drifting to Full is a model question (S until a run).

## The DSPy program (`program.py`, DSPy 3.4.1)
- `SpecToX3D`: request, previous document, report -> x3d. `LawfulX3D`: write, extract, the fork's deterministic repair (kept only if it scores no worse), score; while below 1.0 and rounds remain (default 3), send the document and the metric's feedback back (eval-plan arm A4 with the lawful feedback as the report); return the best document.
- `make_metric(feedback)`: a float for `dspy.Evaluate` and MIPROv2, score plus feedback for GEPA. `optimizer("gepa"|"mipro", ...)`: GEPA with the reflection LM and a metric-call budget or `auto="light"`; MIPROv2 needs `pip install optuna`.
- Providers (`make_lm`): `scripted` (tests), `recorded` (replays x3d.ml live answers of one model; a replay, not a run), **`gemini-api` (preferred for a real run)**: every call goes through `xdomain/eval-plan/gemini_api.py` from branch `loom/gemini-api` (GEMINI_API_KEY), so each call is a row in the shared ledger (`GEMINI_LEDGER`, default `/mnt/project-files/x3d-loom/gemini-ledger.jsonl`, purpose `lawful-dspy call N`) and the shared cap `GEMINI_CAP_USD` is checked before it; `gemini` (LiteLLM `gemini/<model>`, GEMINI_API_KEY or GOOGLE_API_KEY; `ledger_sync()` copies LiteLLM's reported costs into the same ledger at the end of `run()`); `vertex` (LiteLLM `vertex_ai/<model>`, ADC, GCP_PROJECT, LOC default europe-west4). All use temperature 1.0 and 8,192 output tokens, as `eval-plan/runner.py` does. Real providers refuse to start without `xdomain/lawful/GO.json` = `{"approved_by": "user", "providers": [...], "models": [...], "cap_usd": N}`, which does not exist.
- Proven wired, offline (C): the feedback reaches the next round (a sunk cylinder fixed in round 1); GEPA end to end with a scripted LM whose writer obeys one instruction raises the mean from 73.7 to 84.2 by proposing that instruction from the metric's feedback; MIPROv2 compiles end to end; the gemini-api provider writes one ledger row per call (fake `call()`, temp ledger). These numbers test the plumbing and say **nothing about any model (S)**.
- Replay (C as arithmetic on recorded documents, not a model claim): gemini-3.8-flash's recorded answers on the 50 live prompts, best of up to three attempts plus deterministic repair, mean lawful score 97.3; 41 of 50 reach 1.0.

## What a Gemini run would need
1. The user's go, written as `xdomain/lawful/GO.json` (provider `gemini-api`, model `gemini-3.8-flash`, a cap).
2. `GEMINI_API_KEY` in the environment and `gemini_api.py` present (merge `loom/gemini-api`, or set `GEMINI_API_PY`); network access to generativelanguage.googleapis.com.
3. A Python with lxml, `dspy==3.4.1` (plus `optuna` for MIPROv2) and the fork at `X3D_MCP`.
4. `python -I xdomain/lawful/program.py --provider gemini-api --cap 5 --optimize gepa --n 20 --budget 120` (eval-plan prompts; half train, half validation). Cost is not estimated here; at about $0.004 per flash call (PLAN.md status log) a 120-call GEPA budget times up to 4 rounds is on the order of $2, an estimate (S).

## Limits
- The metric inherits the fork's X3DUOM and profile tables; where they are wrong, it is wrong the same way (UnlitMaterial outside Immersive is one place to check).
- Spatial checks use axis-aligned boxes at time 0: rotated parts are over-sized, animated scenes are judged at rest, Text, Geo* frames and IndexedFaceSet without coordinates are not measured. A relation that cannot be judged scores 0.
- `spec_from_text` (free-text prompts) is keyword rules, L; the corpora above use explicit specs.
- No colour, size or count-of-parts-by-role checks; no rendering.

## Files
`metric.py`, `specs.py`, `adversarial.py`, `offline.py`, `program.py`, `test_lawful.py` (51 checks; `make lawful-test LAWFUL_PY=<python with dspy>`; with plain `python3` the DSPy checks are skipped), `data/prompts_live.jsonl`, `results/`.
