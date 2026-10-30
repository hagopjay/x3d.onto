# Loom measurements on the Gemini API (2026-10-29/30)

First real-model runs of the loom tooling built on 2026-10-29. Private; nothing sent outside. Grades: **C** measured here
(one machine, one run unless stated), **L** my reading, **S** a guess. Every call went through `gemini_api.py` (API key
`GEMINI_API_KEY2`; the first key is still `API_KEY_SERVICE_BLOCKED`) into the shared ledger
`/mnt/project-files/x3d-loom/gemini-ledger.jsonl`. The ledger prices every non-pro model as flash ($0.75 / $3.75 per 1M,
thinking billed as output), an upper bound that overstates Flash-Lite.

## Headline

| question | result | grade |
|---|---|---|
| Do the X3D definitions make an AI judge better? (fuzzer findings, with vs without XSD + X3DUOM excerpts) | Gemini 3.1 Pro: verdict right on **99 vs 87** of 115 (p 0.017), evidence invented **9 vs 29**; Gemini 3.8 Flash: **86 vs 75** (p 0.027). Grounded Flash matches bare Pro at under half the cost ($1.71 vs $3.97 per arm). | C (labels by blinded Claude reviewers; see caveats) |
| Does the lawful metric give DSPy something to optimise? | GEPA on 2.5 Flash-Lite, trained on 20 eval prompts: on the **50 held-out live prompts** first-try mean **31.3 → 58.3** and **32.6 → 60.2** (two runs; 40 and 37 of 50 prompts improved, sign p < 0.001); with the 3-round lawful repair loop **39.6 → 70.3**, perfect scenes 2 → 13 | C |
| Do exact-fix hints beat plain errors in the repair loop? | 2.5 Flash-Lite, 540 broken scenes: valid after the first repair **507 vs 489** (+31 / −13, McNemar p 0.0096); after two rounds 530 vs 524 (p 0.21). Stronger models are at ceiling without hints. | C |
| Is a Gemini vision judge usable on X_ITE frames? | 3.8 Flash, 35 frames, every frame judged twice: re-judging moves a frame's mean score by sd 0.12 to 0.25, against a 4.7 to 6.7 spread across frames; on the 32 frames 3.1 Pro also judged, rank agreement Spearman **0.66** | C |

## 1. Fuzzer adjudication: the thesis question asked of a model

`fuzz_adjudicate.py` gives each of the 115 minimised reproducers in `xdomain/fuzz/findings` (branch `loom/thesis`) to Gemini
twice: **bare** (bucket, reproducer, every oracle's output) and **grounded** (the same plus excerpts cut from the fork's own
`x3d-4.1.xsd` and `X3dUnifiedObjectModel-4.1.xml` for each element in the reproducer). The model names where the defect is
(xsd_error, uom_error, fork_validator_bug, xite_bug, generator_artifact, spec_ambiguous) with a quote and a fix.

Labels: seven Claude reviewers each took about 17 findings, decided their own verdict from the XSD, X3DUOM, the fork's code,
the fuzzer's code and the **X_ITE 16.5.1 source** (unminified `x_ite.js` from npm), and only then graded the two answers,
shown as "answer1/answer2" in a random order (key in `results-gemini-api/fuzz-adjudicate-blind-key.json`). 47 contested
findings went to two adversarial re-reviewers told to refute the first verdict; they upheld 46 of 47. Final label grades:
C 54, L 60, S 1.

| model | arm | verdict acceptable | exact label | evidence fully accurate / partly / invented | est. $ (both arms) |
|---|---|---:|---:|---|---:|
| 3.1 Pro | bare | 87 (76%) | 74 | 34 / 52 / 29 | 8.55 |
| 3.1 Pro | grounded | **99 (86%)** | 83 | **77 / 29 / 9** | |
| 3.8 Flash | bare | 75 (65%) | 55 | not graded | 3.05 |
| 3.8 Flash | grounded | **86 (75%)** | 70 | not graded | |

Paired, grounded vs bare: Pro 17 better / 5 worse (p 0.017, automatic score; 17 / 6, p 0.035 on the reviewers' grades, which
give 3 bare answers half credit), evidence 55 better / 8 worse (p < 0.0001); Flash 16 / 5 (p 0.027). 5 of Flash's 230
answers came back without a verdict (3 bare, 2 grounded) and count as wrong. Flash is scored automatically against the reviewers' labels (`results-gemini-api/autoscore.py`); Pro's
reviewer grades and the automatic score agree (99 and 99, 88.5 and 87).

Caveats (L): the reviewers had the same files the grounded arm was shown, so "evidence accurate" favours answers that quote
those files; the ISO specification was not reachable (web3d.org is refused by the proxy), so no label rests on spec prose;
one reviewer pass plus a refute pass, not independent double labelling.

What the labels say about the stack (counts of the 115; C where the reviewer cited file and line):
- **xsd_error 55.** Mostly `uom_allows_xsd_rejects`: content models written as `xs:sequence` or narrow choices where the
  field is a set (NurbsSet, ParticleSystem.physics, ComposedTexture3D.texture, MovieTexture.textureProperties, ...).
- **xite_bug 28.** 15 of the 21 profile signatures: X_ITE's `createNode` calls `hasComponent(name)` without the level
  (x_ite.js:52514), so a level-3 to level-5 node (StaticGroup, LocalFog, ClipPlane, OrthoViewpoint, EaseInEaseOut, ...)
  builds silently under a profile that only grants level 1 or 2. Also: Analyser min/maxDecibels clamped to ≤ 0 and set in
  the wrong order (x_ite.js:88028-88034); MultiTexture in TextureBackground calls a missing `checkLoadState`
  (x_ite.js:36966); AudioDestination.maxChannelCount declared outputOnly; BufferAudioSource.loopStart typed SFTime;
  ListenerPointSource built on the wrong base type.
- **uom_error 16.** X3DUOM's profile node lists are stale for 4.0 nodes (PhysicalMaterial, Shape 2, missing from
  Interchange/CADInterchange/Immersive lists although those profiles grant Shape 2), so the fork's profile flag is a false
  alarm there; pick sensors' `pickingGeometry` says X3DGeometryNode while the same node's ContentModel and the XSD allow only
  PointSet / LineSet / Box|Cone|Cylinder|Sphere.
- **fork_validator_bug 5.** ROUTE-before-DEF is not checked (semantic.py builds the DEF map over the whole scene first);
  the fuzzer's UOM reader does not resolve `bboxSizeType` or `sizeUnits` enumerations.
- **generator_artifact 7, spec_ambiguous 4.** Interpolator key/keyValue mismatches made by the generator, the harness's own
  20 s timeout, a deprecated-node warning, HAnim segments/sites deprecation gated on version 4.1 only in X_ITE.

Per-finding labels: `results-gemini-api/fuzz-adjudicate-labels.json`. None of this has been reported upstream.

## 2. DSPy with the lawful metric (`xdomain/lawful`, branch `loom/lawful-metric` at aa2f724)

| model | prompts | rounds | baseline | after GEPA | note | grade |
|---|---|---:|---:|---:|---|---|
| 3.8 Flash | 20 eval | 3 | 100% (20/20) | stopped by me at 10 of 120 rollouts | the refine loop alone already saturates; GEPA's validation score was 0.9 only because a connection reset failed one example | C |
| 3.8 Flash | 20 eval | 1 | 99.6% | stopped | nothing for GEPA to fix ("all subsample scores perfect") | C |
| 3.8 Flash | 50 live | 1 | 93.2% | did not finish | some answers ramble instead of returning a document (DSPy parse failures score 0) | C |
| **2.5 Flash-Lite** | 20 eval (train/val) | 1 | **49.4%** | **79.9%** | 456 calls, ledger $1.48 | C |
| 2.5 Flash-Lite | **50 live, held out** | 1 | 31.3% / 32.6% | **58.3% / 60.2%** | two runs; 40/7/3 and 37/12/1 improved/worse/tied | C |
| 2.5 Flash-Lite | 50 live, held out | 3 | 39.6% | **70.3%** | perfect 2 → 13 | C |
| 3.1 Flash-Lite | 50 live, held out | 1 | 92.6% | 93.6% | transfer of the Flash-Lite program; ceiling, p 0.45 | C |

The optimised instruction (4,699 characters, saved in `results/gemini-lite-gepa-eval-r1.json`) is the metric's feedback
turned into rules: smallest profile, each node in a field that accepts it, one Shape per part, touching parts computed from
sizes. GEPA's reflection model was the same Flash-Lite. Reading (L): the lawful metric is a usable optimisation target, the
gain transfers to unseen prompts, and the validator loop adds about ten points on top of the optimised prompt; for models
that already write lawful X3D the eval sets are too easy to show anything.

## 3. Exact-fix hints (x3d_mcp `loom/exact-fix`, `evaluation/exact_fix/MODEL_RUNS.md`)

| model | cases | valid r1 E / H | gained / lost, p | valid r2 E / H |
|---|---:|---|---|---|
| 3.8 Flash | 60 | 59 / 57 | 0 / 2 (one a connection reset), 0.5 | 60 / 60 |
| 3.1 Flash-Lite | 60 | 60 / 59 | 0 / 1, 1.0 | 60 / 60 |
| 2.5 Flash-Lite | 540 | **489 / 507** | **31 / 13, 0.0096** | 524 / 530 |

The gain is concentrated in misplaced ROUTEs (32 → 45 of 45) and random relocations (35 → 39); classes whose error text
already names the fix are 45/45 in both arms. On 3.8 Flash the hint arm used 17% fewer output tokens and answered 22%
faster (C, one run). Reading (L): hints buy one repair round for a weaker model, not a capability.

## 4. Vision judge (`frame_judge.py`)

Frames: gobbler-demiurge `docs/frames` (15), the `loom/armenian` sets `mashtots` (3), `khachkar` (4), `weave` (9), and the
Mashtots X3D shots (alphabet loom, khachkar; 4). 3.8 Flash, 3 votes, every frame twice; 3.1 Pro, 3 votes, once.

| set | frames | Flash mean (first judging) | Pro mean | sd of the change on re-judging |
|---|---:|---:|---:|---:|
| gobbler-demiurge | 15 | 5.25 | 5.09 | 0.13 |
| Mashtots X3D shots | 4 | 6.31 | 5.52 | 0.14 |
| loom/armenian khachkar | 4 | 5.27 | 4.75 | 0.12 |
| loom/armenian weave | 9 | 5.44 | 5.19 | 0.17 |
| loom/armenian mashtots | 3 | 5.14 | (not run) | 0.25 |

Flash vs Pro on the 32 frames both judged: Pearson 0.665, Spearman 0.663 (C). Pro scores 0.3 lower on average. The fix both
judges name most often is the same: thin out the dense line/particle network on the right of the gobbler frames. Highest:
`alphabet-loom-1.png` 6.71 (Flash, mean of both judgings); lowest: `12-villager.jpg` 4.67. Reading (L): the judge is stable enough to rank frames
0.5 apart, and two models broadly agree, but it is not calibrated against people.

## Cost

Ledger total after these runs about **$36.2** (from $0.00 at the start): exact-fix 10.2, lawful DSPy 12.4, fuzz
adjudication 11.6, frame judge 2.0. One $25 alert fired and was reported; the user approved a second $25.

## Files
- `fuzz_adjudicate.py`, `results-gemini-api/` (adjudications, reviewer grades, labels, blind key, frame-judge votes,
  `autoscore.py`)
- `gemini_api.py`: now retries connection resets, 429 and 5xx (a reset killed one DSPy run and one hint round before)
- lawful: `heldout.py` and `results/heldout-*.json` (branch `loom/lawful-gemini`)
- x3d_mcp: `evaluation/exact_fix/MODEL_RUNS.md` (branch `loom/exact-fix-gemini`)
- full logs: `/mnt/project-files/x3d-loom/runs/`
