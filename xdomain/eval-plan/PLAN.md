# Model-driven evaluation of the URDF and glTF loops: pre-registered plan (NO SPEND UNTIL THE USER SAYS GO)

Status 2026-10-21. Nothing here has called a model. The pipeline was exercised with a deterministic stub (`runner.py --stub`, files tagged STUB; its numbers are meaningless). Real runs are refused by `runner.py` unless `GO.json` exists, and `GO.json` is written only after your explicit go.

## 1. Questions and decision rules (fixed before any data)
| | question | decision rule |
|---|---|---|
| H1 | Does returning the validator's report fix more documents than the same number of blind retries? | A2 (report loop) minus A3 (blind resample), final validity, paired McNemar p < 0.05 and at least 10 points: "the report carries information". Otherwise: "extra tries, not the report". |
| H2 | Do two examples raise first-try validity? | A1 minus A0, paired, p < 0.05. |
| H3 | How much does the deterministic repairer add without a model? | A0+det minus A0; reported, no threshold. |
| H4 | Does the loop buy validity at the cost of completeness (Goodhart)? | Share of valid documents meeting the task's machine-checked expectation, A2-final vs A0: a fall of more than 10 points means "repair deleted what was asked"; I then read 10 repaired documents by eye. |
| H5 | Do the domains differ? | URDF vs glTF first-try validity, unpaired, reported with CIs. |

## 2. Design
- **Tasks:** 20 URDF and 20 glTF prompts in three tiers (`prompts.py`), each with a mechanical completeness expectation (link and joint counts; node, mesh, material, animation and camera counts). Prompts are mine; the wording is the whole instruction: "Write {format} for {task}. Return only the document, in one code block."
- **Arms:** A0 zero-shot first try. A1 two valid examples first try. A2 report loop: from the A0 answer, up to R = 3 rounds, each round sends the task, the previous document and up to 8 located diagnostics with fix hints. A3 blind control: from the A0 answer, up to 3 fresh independent tries with no report. Post-step on A0 and A1: the deterministic repairer, no model call.
- **Samples:** 2 per prompt in the lean run (40 first tries per domain per arm); temperature 1.0; max 8,192 tokens out; one model.
- **Oracles:** glTF = Khronos validator 2.0.0-dev.3.10 with the strict gate (UNSUPPORTED_EXTENSION and MESH_PRIMITIVE_NO_POSITION count as errors; fixed now, before data). URDF = my 17 rules (grade L).
- **Metrics:** valid under the gate (Wilson 95% CI); paired McNemar on discordant pairs; completeness among valid; rule histogram of first failures; calls and cost per valid document; rounds to valid.

## 3. Threats, said now
- URDF's oracle is mine: a "valid" URDF here is valid by my rules, not by urdfdom or MuJoCo. Treat URDF results as L until an independent oracle is installed.
- URDF and glTF are heavily represented in model training data; X3D much less. Do not read these rates as comparable with the X3D E1 numbers (27.3% to 56.7% first-try; about 100% after repair): different prompts, models, validators.
- 40 first tries per arm give CIs of roughly plus or minus 15 points. Only large effects will be visible.
- Prompts and expectations are mine; the completeness check is a floor (counts), not fidelity.
- The Vertex quota is shared with gemini-eval, which is running jobs; 429s are retried by `vertex.py` and slow the run, not its cost.
- Thinking tokens bill as output; the estimate assumes 1,500 for flash. A model that thinks more costs more.

## 4. Cost (`plan_cost.py`, all assumptions in the file)
Prices are the assumptions already in `tools/vertex.py`: flash class $0.75 in / $3.75 out per 1M tokens; pro class $2.50 / $15 (the ledger calls them upper-bound style, not a billing export). Per flash call: URDF output about 2.9k tokens including thinking, glTF about 2.5k; a report-loop call reads about 1.4-1.8k tokens.

| scenario | model | calls (mid) | expected USD, first-try failure 30% / 55% / 80% | upper bound (every document fails every round) |
|---|---|---|---|---|
| pilot: 5 prompts x 1 sample, arms A0+A2, both domains | flash | 20 | $0.17 / $0.21 / $0.26 | $0.45 |
| lean: 20 prompts x 2 samples, arms A0-A3, both domains | flash | 314 | $2.62 / $3.38 / $4.14 | $6.92 |
| full: 20 prompts x 3 samples, arms A0-A3, both domains | flash | 472 | $3.93 / $5.06 / $6.20 | $10.38 |
| pilot, pro class | pro | 20 | $0.99 / $1.28 / $1.58 | $2.66 |
| lean, pro class | pro | 314 | $15.87 / $20.47 / $25.05 | $41.82 |

Context: the shared ledger shows $0.96 spent over 285 calls so far (all flash); the coordinator's note gives a first-pass budget of $25 of $100. Recommendation: flash only; pro only for the pilot if you want a contrast. Guard rails: each run has `--cap` (the run stops when its own estimated spend reaches it), `vertex.py` has its shared hard cap and ledger (every call logged before and after, purpose-tagged `xdomain-eval ...`), runs are resumable, and I stop after the pilot for your review. Stop rule: if the pilot costs more than 2x its estimate, I stop and re-plan.

## 5. Go items (nothing starts without them)
1. **Pilot** with gemini-3.8-flash through `shroud-artifacts/tools/vertex.py`, cap $1.00 (expected about $0.21).
2. **Lean run** after you read the pilot, cap $8.00 (expected about $3.4; upper bound $6.9).
3. Approval to use `vertex.py`'s gcloud OAuth token mechanism (the token is never printed or written; I do not touch keys and use no other provider).
4. Say whether the embargo (private until 2027-01-01) covers these results; they stay in `ontology/` regardless.
5. Optional: I tell gemini-eval before the run so the shared quota is not a surprise.

## 6. Protocol on go
I write `GO.json` {approved_by: "user", models, domains, cap_usd} with exactly what you approved, then run `runner.py --real`. Outputs: `runs/{domain}-{model}.jsonl` (one row per scored document), a printed report, and a summary in `xdomain/README.md`. Free prep already done: prompts and checks (20+20), stub pipeline, cost model.

## 7. Status log (2026-10-21)
- 05:00Z first pilot attempt stalled on the shared Vertex quota (global endpoint 429, us-central1 154 s on a probe, europe-west4 3 s): runs now use europe-west4 and my own 429 back-off (vertex.py re-raises HTTPError 429 at once; I did not edit it).
- User clarified "upper bound it" as: spend as much as needed, open things up, use Gemini tools, log verbosely. GO.json widened: domains urdf, gltf and x3d (the same arms on X3D as a third point), cap $60 for this evaluation (vertex.py's shared $100 cap stays in force), model gemini-3.8-flash only. Added arm A4 (deterministic repair first, then the report loop), a Gemini judge script (`judge.py`, run after the main runs), per-call raw logs with latency and tokens, and `insights.py`.
- X3D pilot (5 tier-A prompts, 1 sample): first try 5 of 5 valid under the XSD plus semantic gate and 5 of 5 meeting the count expectation. Tier A is easy; this is a ceiling, not a rate. Latency per call 5 to 15 s, with one 199 s stall under quota contention; about $0.004 per call.
- Full run (`run_full.sh`): 20 prompts x 3 samples x arms A0-A4, three domains in parallel, cap $20 each, logs `runs/full-*.log`, results `runs/{domain}-gemini-3.8-flash.jsonl`, raw responses `runs/raw-*`, insight reports `INSIGHTS-*.md`.
- Overnight: watchdog.py supervises restarts (resume from raw-log cache), then judge, insights, RESULTS.md, demo rebuild and number audit; see MORNING.md. caffeinate -i ties to the watchdog.
