# Sources

Every input to Loom v1: where it is, what it contributed, how it was read, and where sources disagree. Read on 3 November 2026. Drive files were read through the Drive connector, and the same docs were read again from the `.docx` exports in `incoming/drive/` (converted with macOS `textutil`). Nothing in Drive, `incoming/` or `projects/` was edited.

Drive folder: `[Drive folder id withheld]` (owner hagopjay). Download: `incoming/` from `loom-20261103T192438Z-1-001.zip` (sha256 `4a2371b9…e5f3`), 2,230 files listed in `incoming/READY.txt` by the projects agent.

## 1. Source IDs used in LOOM-v1.md

### Core definition and method (Drive Google Docs)
| ID | Document (Drive id) | Author, date | What it contributed | How read |
|---|---|---|---|---|
| DEF | The Loom full definition v1.md (`[Drive id]`) | HagopJay, 1 Nov | Purpose, the 16 laws, anatomy, toolchain organs, 11 witnesses, receipts, C/L/S grades, flywheel, knowledge graph, agent architecture, repo map, 18 ranked lessons, 13 gaps, M1-M12, video to world, 7 decisions, report-in brief | In full |
| KICK | Loom kickoff what to paste before and after.md (`1rTua…`) | HagopJay, 1 Nov | PRE (7 blocks), POST (8 items), where outputs land, second-factor options, Materials worked example, "why each part is there" | In full |
| MEAS | X3D loom on a hosted model first measurements (`[Drive id]`) and …first measurements.md (`[Drive id]`) | HagopJay, 30 Oct | The four a hosted model measurements, spend, caveats | In full, both. The two copies differ only in blank lines (C, `diff` of the exports) |
| LEC | Lectures on the Loom (2).html (`[Drive id]`) | the builder model, 30 Oct | Ten lectures: the laws' origins, eight witnesses, receipts, grades, flywheel, people, metrics, copying, budget; exercises | In full |
| SPEC | Loomsong music visualization build spec v1.md (`[Drive id]`) | HagopJay, 1 Nov | Loomsong brief, 16-witness table with thresholds, five proposed trap rules, Gobblering, knobs, [cost withheld] plan | Brief, witnesses, Gobblering and budget read; vision and media sections by heading |
| LS1 | Loomsong-Technical-Debrief (`[Drive id]`) | Other model's debrief, 2 Nov (Study 01 v1.0.0) | Local-vs-global distinction, witness inventory with boundaries, gates vs witnesses, audit findings A01 and A02, incidents F01-F06, P0/P1 gate proposals, status taxonomy, acceptance algorithm, promotion matrix | In full |
| LS2 | Loomsong-Second-Run-Debrief-Addendum (`[Drive id]`) | Other model, 2 Nov (Cinematic v2) | Candidate-bound evidence, 7 diagnostics, image-difference isolation, cuts vs moves, cancelled measurements, "three questions" | In full |
| LS3 | Loomsong-v3-Technical-Learnings-Debrief (`[Drive id]`) and its copy "(1)" (`[Drive id]`) | Other model, 1 Nov (Cinematic v3) | 8 required reports, coordinate spaces, topology, optics, camera contract, rendered IDs, scoped Ear, interruption paths | In full. The two exports are byte-identical (C, `diff -q`) |
| STUMP | stumping-field-guide.md (`[Drive id]`) | 3 Nov | Stumping method summary, graded references, rubric templates, seam catalogue, version traps, fairness checklist, reference-image recipes | In full |
| STUMPB | Stumping Method Blender First (`[Drive id]`) | @jason, 2 Nov | The 16 levers and the attack atlas behind STUMP | Summary and headings (STUMP summarises it) |
| TIDE | blender-tide-line-prompt-rubric.md (`[Drive id]`) | 3 Nov | A complete stump prompt and 30-criterion rubric; the 8 PNGs in the folder are its spec and grader images | Concept and headings |
| BLUE | x3d Integration Blueprint (`[Drive id]`) + .pdf (`[Drive id]`) | 1 Nov | x3d_mcp vs x3d.xray overlap, MemoryRecord schema (§3.2), ClaimAnchor, "no witness, no tie" | Headings and §2-3; the PDF was not opened separately (same title; L that it matches) |
| MC | x3d_mcp Fork Masterclass.md (`[Drive id]`) + "(1).zip" (an HTML page) | the builder model, 30 Oct | Fork numbers, 12 series, the four flywheel loops FW1-FW4, upstream state, the 33-PR plan, pins spread over five commits | §1, §2, §6 read; others by heading |
| WD | WikidataGraph ("Wikidata.loom", `[Drive id]`) | A model's reply in another project | Eight candidate rules from a non-X3D pipeline (load gate, two-route rule, blast radius, path fixtures, metric guard, transfer witness, build receipt, "a refusal is a verdict") | In full |
| AGENDA | visualization-ai-era-agenda.md (`[Drive id]`) | HagopJay, 8 Oct | Context: validator-backed AI visualisation is the field's pattern; X3D-Bench; scene-graph behaviour as the weak spot | Summary only |
| WIKI | Mapping English Wikipedia Iteration 1 plan (`[Drive id]`) + wikigrokker-step1 and WikiData.x3d tarballs | @jason, 1 Nov | Context only (user decision, 3 Nov): a Loom-adjacent data pipeline that WD reviews against the Loom | Summary only |
| MUJ | X3D & 3MF → MuJoCo Converters, Bridges & Playbook.md (`[Drive id]`) | @jason, 1 Nov | Context only: "two entries, one generator, then validation", the same shape as the Loom | Bottom line only |

### The other model's projects: zips, kits and PR patches (`incoming/unpacked/`)
User's note, 3 Nov: the zips carry GitHub-PR-style patches explaining what the Loom taught each project. Verified for five projects (C); listed in [LEARNINGS-from-patches.md](LEARNINGS-from-patches.md).

| ID | Inputs | Contributed | How read |
|---|---|---|---|
| LS4 | Loomsong-Cinematic-v4.zip (`TECHNICAL-V4.md`, `integration/loom-fidelity-v4.patch`); `Loomsong-v3-to-v4.patch` (drive, 30 files); Loomsong-v4-Foldback-Kit.zip | Fidelity chain, three failures that earned gates, four-clock profiler, picture protocol (flags only), 9 proposed rules, the fold-back generator `gen/foldback.py` | TECHNICAL-V4 in full; patch stats in full; contract, gates, package, picture, check_release, foldback diffs read |
| GEAR | Gear-Loom.zip (`TECHNICAL.md`, `integration/gear-loom-additions.patch`), Gear-Loom-Gate-Kit.zip | Structure/motion/appearance as separate evidence, clearance certificate, frame-clock motion witness, 9 gates, "test the observer" | TECHNICAL in full; kit README; patch file list |
| BREAK | Break-The-Loom.zip (`TECHNICAL.md`, `integration/break-loom-additions.patch`, `corpus/`), Break-The-Loom-Gate-Kit.zip | Mutant/control corpus, matrix cell semantics, exact-diagnostic requirement, coverage ownership | TECHNICAL in full; kit README; corpus used as a test for loomkit.traps |
| CITY | Data-City-Loom.zip (`TECHNICAL.md`, `README.md`, `integration/data-city-gates.patch`), Data-City-Gate-Kit.zip | Source-to-render lineage, four identities, null semantics, exit-code convention 0/1/2, 19 diagnostics | TECHNICAL in full; README in part; **the worked example for loomkit** |
| IFC | Confluence-Technical-Debrief.html; Confluence-IFC-X3D-Studio.zip (`docs/TECHNICAL-DEBRIEF.md`, `docs/FOLDBACK.md`, `studio/integration/loom-ifc-bridge.patch`); `IFC-X3D-Bridge-upgrade.patch` (drive, 53 files); Confluence-Loom-Foldback-Kit.zip | One authority with derived views, commit ≠ ack ≠ frame, 15 gates with boundaries, -O refusal, rollback boundary, "release acceptance is a closed set, not a score" | Debrief in full; patch stats and release_contract/gates read |
| AUD | Loomsong-Debrief-Audit-Evidence (1).zip | The A01/A02 probes' logs and audit.py behind LS1 §9 | File list; the debrief's account trusted (L) |
| LSV | Loomsong-Study-01-v1 (2).zip, Loomsong-Cinematic-v2.zip, -v3 (1).zip: `evidence/FACTS.md` and receipts | Per-version FACTS (5, V2-01 to 05, 11 lessons) that the debriefs summarise | v2 vs v3 FACTS diffed; Study 01 FACTS read |

### On this Mac (read only)
| ID | Input | Contributed |
|---|---|---|
| SITE | `~/Projects/x3d/work/mashtots-demo-site-eval/site/web/demo/dist/data/loom.json` (generated 2026-10-30T05:21Z) | The "loom heuristic" thesis, the 7-step generate→record loop, the hints-alone result (522 of 540), 16 caveats, spend by purpose, branch/commit sources for every MEAS number |
| EVAL | `…/mashtots-demo-site-eval/EVALUATION.md`, `integrated/ROADMAP.md`, `QA.md` | That the loom research chapter belongs on a separate "how this was made" page, not on the stage (decision E5) |
| FORK | `~/Projects/x3d/x3d_mcp` (fa0b389, branch fix/physics-findings, 17 Oct) | The Grammar and Meaning instrument for loomkit (`validate_xml`, `semantic_diagnostics`), run in its own venv, read only |
| BLIO | `~/Projects/x3d/x3d-blender-io` (78212bc, 17 Oct) | Not run by v1; organ described from DEF and MC |
| — | `~/Projects/x3d/shroud-artifacts/`, `x3d.poc/assets/shroud/graph/INDEX.md` | Checked: their "loom" mentions concern a textile loom (Shroud weave reconstruction), not the X3D Loom. Contributed nothing beyond the Shroud ledger's grade names, which DEF already cites |
| CAT | `projects/CATALOGUE.md` (projects agent, 3 Nov) | 17 of 21 items run in the built-in browser; both loose patches reproduce their newer versions (content-identical; PNG bytes and two last-bit floats differ across platforms); what was not checked (audio by ear, real GPU, the projects' own QA suites) |
| KIT | This repository's runs (`runs/`, `kit/tests/last-run.json`) | §7.4 of LOOM-v1.md |

### Inventoried, not used as method sources
| Input | Why not |
|---|---|
| Dynasty Loom (2).zip | The built scenes and `loom-manifest.json`. Its lessons arrive through LEC and DEF (the builder model's account); the zip carries no debrief or patch. Scanned by loomkit.traps (0 hits) |
| Loom GEDCOM Reader.zip, Loomsong Masters / First Light / Preview / Drafts / styleboard .zip | Single-page apps or media; no debrief, FACTS or patch inside. Left to the projects agent to run |
| MV_CUSTOM_011.zip | One STEP file; no Loom material |
| Cross-repo knowledge graph (interactive) (1).html | The 3,977-node, 9,385-edge, 214-community code map BLUE's appendix describes; DEF warns it is a map, not a call graph (1,192 dangling endpoints) |
| Blender Python Crib Sheets.html, Blender to Unreal Engine Bridge crib sheet | Reference material for Blender work; no Loom rules |
| solve.py | A photochemistry curve fit (LED flux constants); unrelated to the Loom |
| The 8 PNGs (ref_sunray, shell_model, finish_map, crab_anatomy, shot_plan, watch_drawing, ref_timing, gait) | The Tide Line stump's spec and grader images, named in STUMP App. E |

## 2. Where sources disagree, and how v1 resolves it

| # | Disagreement | Sources | v1 resolution |
|---|---|---|---|
| 1 | **Grade scale.** C/L/S everywhere vs the consolidation brief's Measured / Established / Estimate / Conjecture | DEF, LEC, all projects vs the brief | **User decision 3 Nov:** keep C/L/S; LOOM-v1 gives the mapping; "synthetic" is a separate label |
| 2 | **Model judge numbers.** MEAS and DEF used 1-10 frame scores ("under 0.2 is noise"); LS4 and IFC reject any numeric grade from a model | MEAS, DEF vs LS4, IFC | **User decision 3 Nov:** flags only in releases; numbers only in labelled experiments (Gobblering) |
| 3 | **How many witnesses.** 8 (LEC: 6 + 2), 11 (DEF), 16 for Loomsong (SPEC), per-project report sets (LS2-LS4, IFC, CITY) | LEC, DEF, SPEC, projects | v1 keeps DEF's 11 as the vocabulary and names the extras as optional domain witnesses; **acceptance profiles** decide what is required per delivery |
| 4 | **Loudness target.** −14 LUFS ±1 (SPEC) vs −18 to −12 enforced (LS2) | SPEC vs LS2 | Both kept, each tied to its profile (full production vs local study). Open question 5 |
| 5 | **Onset tolerance.** Median ≤ 5 ms / p95 ≤ 15 ms on drum and piano (SPEC) vs max ≤ 25 ms on one isolated stem (LS3) | SPEC vs LS3 | Same: profile-bound. LS3's is scoped to the silver stem and says so |
| 6 | **Sync design.** SPEC proposes FractionBus/SecondsBus ROUTEs with u_time on every shader; Loomsong wrote through the page API directly, with no ROUTE network | SPEC vs LS1 §1 | Both satisfy "the page (audio clock) owns time" (DEF lesson 9). The ROUTE design stays proposed; its trap rule `bus-wired` is not in loomkit |
| 7 | **"Exact-fix hints help."** DEF: 15.0% → 96.9% repaired on 540; SITE: 81 → 522 of 540 (15.0% → 96.7%; a 0.2-point gap, perhaps a later recount, not resolved here); MEAS: the model effect shows only in round 1 for one weak model; hints alone restored the *original* in 257 of 540 | DEF vs SITE, MEAS | Both are C on different questions: hints repair to valid (corpus) vs hints help a model (paired). v1 quotes SITE's counts (newest, with commit) and keeps "valid is not restored" as a caveat |
| 8 | **Fold-back route.** DEF's flywheel goes incident → FACTS → loom_gate → fork → upstream; the other model's projects fold back as additions-only `tools/<name>/` patches without touching FACTS or loom_gate | DEF vs GEAR, BREAK, CITY, LS4, IFC | v1 joins them: a fold-back patch is the vehicle; its destinations table maps each piece onto a flywheel stage; promotion into x3d.onto or the fork is a PR on his word |
| 9 | **Is Loomsong "the Loom"?** LS1: a *local implementation of Loom practices*, not integrated with the global Loom (no pinned fork, family gate, graph or x3dprov) | LS1 vs SPEC's 16-witness plan | v1 states it plainly: every project so far ran a local subset; none used the family pin or loom_gate (C, their own receipts) |
| 10 | **Grade for "C" under emulation.** DEF: C under a strict copy, L on the real host. The other model labels SwiftShader browser results C | DEF vs LS1-LS4 | Compatible if scoped: C for *what SwiftShader did*, never for GPU performance. Every v1 row names the renderer |
| 11 | **The "7 to 10 of 10 repairs" thesis line.** Stale: holds at upstream 74da0ec only; 3 to 6 at 020221e | DEF gap 7 | v1 does not quote it except as the law 15 example |
| 12 | **Stumping's place.** STUMP and STUMPB never mention the Loom; the consolidation brief lists stumping as a loop step | STUMP vs brief | **User decision 3 Nov:** stumping is the Loom's attack step, paired with Break-the-Loom |
| 13 | **Cost of grounded model F vs bare model P.** "a third" in an earlier version vs "under half" | SITE caveat | v1 uses the newest: under half ([cost withheld] vs [cost withheld] per arm) |
| 14 | **MODEL_RUNS.md costs.** First [cost withheld] / [cost withheld], newest [cost withheld] / [cost withheld] | SITE caveat | Newest, which matches the ledger |

## 3. What v1 could not check

- None of the target repositories (x3d.onto, the fork at its pin, x3d.ML main) is checked out at the commits the sources cite, so every number from them keeps its source grade. loom_gate.py and loom_receipt.py are not on this Mac.
- Browser witnesses (Behaviour, Eyes, Host) were not run by v1. The projects agent runs the pages.
- The IFC bridge fold-back was rerun with the studio's existing venv (installed by the projects agent with the user's OK; nothing new downloaded here). It fails its positive control on arm64 (LOOM-v1 §7.4).
- The two Drive copies of the Loom kickoff, definition and spec were read once each; the `(1)` suffixes in LS1's source list refer to copies not in this folder.
