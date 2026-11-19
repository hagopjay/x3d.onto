# DSPy and the ontology: where the work is heading

Short orientation for anyone joining. Claims are graded C (confirmed from files), L (likely), S (suspected).

## The idea
A scene-writing prompt can be *optimised* instead of hand-tuned, but only against a metric the model cannot talk its way past. The X3D validator and the ontology give such a metric. The thread is: **use the ontology as a lawful judge, let DSPy search prompts and programs against it, and keep every number tied to a named validator.**

## What exists here
- `scene_metric.py`: three terms for a scene-writing prompt, scored together. **Valid** (XSD plus semantic checker), **placed** (every node sits in a parent and field the X3DUOM allows, from the placement table) and **use-type clean** (a USE names the same node type as its DEF). Score is 1.0 only when all three hold; otherwise a weighted partial so an optimiser's Pareto front stays informative. The feedback text lists validator errors, then not-placed lines that name the allowed parents, then USE-type mismatches.
- `calibrate_cached.py`: runs the three terms over cached model answers with no model calls (free). Needs a checkout of the pinned validator in `X3D_MCP_TREE`.

## What was found (27 Oct 2026, one writer model, 61 held-out prompts x 2 runs per arm)
1. A learned prompt lifted first-try validity from about a third to about three quarters (33.6% to 73.0%, C). Counting only scenes that also render something recognisable, 23% to 61% (C; the render judge is a screen, not truth).
2. The placement and USE-type terms did **not** add signal on top of validity for this prompt (L). A generator that is valid was already placed and type-clean. The USE-type term caught 2 of 253 valid scenes that the XSD and semantic checker passed (C, small n). Their use is as a guard for tools that skip the validator.
3. Valid-but-blank scenes exist (8 of 102 rendered, C), so "valid" alone is not "looks right".

## Where it goes next
- Rule synthesis: write the detector that turns an incident into a check, scored against clean scenes, twins and near-misses (the sealed-variant design in the loom repo's DSPy sweep).
- Writer ablation: fixed prompt, then plus a deterministic repair ladder, then an optimised prompt, then a router; the metric is "delivered", valid and meets the structural constraints.
- An ontology-aware metric that joins the placement and USE-type terms to the render check inside the optimisation loop (needs a render per metric call, about 2.5 s per scene).

## Withheld on purpose
The run harness, the render judge wiring, model and spend details, raw per-scene rows and local notes are not published here.
