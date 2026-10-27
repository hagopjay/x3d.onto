# Scene-writing prompt with placement and USE-type terms (27 Oct 2026)
Grades: C confirmed from the files here, L likely, S suspected. Validator pin: x3d_mcp main 2b696f5 (XSD + semantic checker); placement table = X3DUOM via `where_can_place` (6,509 rows, sha256 e749eda517ba...); use-type-mismatch ported from fork branch claude/ontology-lentz-polys-3j5h8z (nothing pushed to the public fork). Renderer X_ITE 16.5.1 headless. Writer gemini-3.8-flash, reflection gemini-3.1-pro-preview, judge gemini-3.8-flash (a screen, not truth). Spend $4.83 (prices assumed, ledger in scratch), inside the $10 budget.

## Metric (`scene_metric.py`)
score = 1.0 only if valid AND placed AND USE types match; otherwise 0.6 valid + 0.25 placed + 0.15 types (keeps GEPA's Pareto front informative). Feedback text = validator errors, then `[not-placed]` lines naming the allowed parents/fields from the table, then `[use-type-mismatch]` lines.

## Calibration, free, 600 cached E1 flash answers (`calibrate_cached.py`)
valid+placed+types ok 251 | valid but USE-type mismatch 2 | invalid but placed 287 | invalid and unplaced 60 | valid but unplaced **0**. (C)
So placement never disagreed with the validator on a valid scene; the USE-type term caught 2 of 253 valid scenes (0.8%), scenes the XSD and semantic checker passed. (C, n small)

## A/B, 61 held-out prompts (bench + ood) x 2 runs = 122 scenes per arm (C)
| arm | valid | placed | all three | rate |
|---|---|---|---|---|
| seed prompt | 41 | 107 | 41 | 33.6% |
| earlier learned (17 Oct, valid-only metric) | 89 | 105 | 89 | 73.0% |
| new learned (this metric, GEPA stopped at the cap after ~10 iterations) | 83 | 106 | 83 | 68.0% |
Across 366 generated scenes: 0 valid-but-unplaced, 0 USE-type mismatches. New vs earlier: 83 vs 89 of 122, within noise (L: no gain).

## Looks right, run 0 only, 61 prompts per arm (C counts; judge is a screen)
| arm | valid scenes rendered | blank | judge >= 2 | all four (valid+placed+types+judge >= 2) |
|---|---|---|---|---|
| seed | 19 | 2 | 14 | 14 of 61 (23%) |
| earlier learned | 42 | 4 | 37 | 37 of 61 (61%) |
| new learned | 41 | 2 | 37 | 37 of 61 (61%) |
No scene scored 3 (the judge never says "all of it"), so the bar here is "most of it visible". Valid-but-blank: 8 of 102 (C). 

## Reading
1. The new terms do not move this prompt. A generator that is valid is already placed and type-clean, so they add feedback words, not signal (L). Their use is as a guard on tools and scenes that skip the validator, and for the 2-in-253 USE-type case.
2. The gain is the 17 Oct learned prompt: 33.6% to 73.0% first-try on this metric, 23% to 61% with looks-right. (C)
3. The new prompt kept the seed's "add a GeoLocation when a place is named" rule, which University scale found hides valid scenes (S).
4. The run hit the $4 cap mid-GEPA (the first launch wasted calls on a module GEPA could not trace; fixed in `run_onto_gepa.py`). A fuller GEPA run with a looks-right term inside the loop is untested; it needs a render per metric call (~2.5 s per scene here, 250 s for 102 scenes).
Files: `scene_metric.py`, `calibrate_cached.py`, `run_onto_gepa.py`, `render_eval.py`; results in `out/dspy/`.
