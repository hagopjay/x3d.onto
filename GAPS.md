# Gaps and what I could not read

## Read depth (be skeptical accordingly)
- **Full:** README (27)-(30), references.md, hitzler2021-notes.md, polys2024-notes.md, web3d-search-summaries.md, fetch-list.md, x3d_mcp semantics.py + ontology.py, flywheel REPORT.md, MANIFEST listing.
- **DOC.md** (82,259 chars; fetched via connector, saved to tool-results, not to my output folder): read §1 (partly, truncated at ~300 chars/line for Lentz/Polys/Brutzman/Narra bullets), §2, §3 (table; ~1.5 KB truncated mid-way), §4, §6, §7, §8 DSPy join + heuristics, Sources table, App A, App D. **Skimmed/unread:** §1 "adjacent people", §5 (dup of references.md), §8 steps 2-4 body (dup of README 30), App B (run log), C (source map), E (reproduce).
- **Local INDEX.md:** read lines 1-120, threads 68-72 tables; grep for ontology/DSPy/ledger. Other thread entries and artifact lists skimmed/unread.
- **EVIDENCE.md / REPORT.md:** first ~2.5 KB + grep only; ledger schema taken from EVIDENCE.md header. No ontology mentions (0 hits).
- MANIFEST: file list only; 85 SVN files unread.

## Not available / blocked
- **Artifact bodies** for threads 68 (DSPy standing note, picture-judge spec, repair-ladder spec, X3D Verifier Gap), 69 (Tether Firehose 1-3, MLOps tethering), 70 (original), 71 (Brutzman roadmap, thread 71 not otherwise ingested): private claude.ai URLs, not fetched (per instructions). DSPy method details (optimiser, metric, budgets) are only known via README (30)'s summary.
- **Underlying evidence sources** cited but not in Drive reads: cross_validate_ontology run txts, scale200/summary.json, results.json, trials-scored.json, ledger.jsonl, E1-results.md, Y8/Y9, judge-bench-v2, spine findings, X3dOntology4.1.ttl, 3D_perspective_skill (404). All numbers here are as reported in the READMEs/DOC, not re-verified.
- web3d.org pages (Apr 2026 MCP thread 022491/3/4, 17 Jul 2026 blog, x3dmcp page, Nov 2025 slides), SHACL/ShEx book chapters, ROBOT, VOWL papers: blocked at the original author's environment; items 1-8 of fetch-list.md. I did not try to fetch them (task scope: Drive + local only).
- Books/specs in references.md: author did not read them either.

## Discrepancies / cautions noticed
- Task brief said DOC.md is 47 KB; the connector returned 82,259 chars (rev 68 patched).
- README (27) says "Ontology answers advisory…17,736 triples (bundled 4.0)"; local x3d_mcp (fa0b389) still bundles only 4.0 and its `node_parents` excludes bare X3DNode / non-IRI ranges. The 348/150/163 numbers come from fork eb4b4b4's harness; I did not check whether that filter existed then.
- Step-2 branch claude/ontology-lentz-polys-3j5h8z is **public** with an AI trailer; user was asked rewrite/delete — outcome unknown. Don't cite it as private.
- gemini/gpt model names in sources ("gemini-3.8-flash", "gpt-6.1-sol") are as written; not verified.
- README (30) laguna pilot: "n = 40" in one table, "38 trials (57.9%)" in another; quoted both.
- Cost figures use recalled list prices (not billing export).
- Grades: C/L/S (thread) vs Confirmed/Likely/Contested/Suspected/Question (Shroud ledger) are different scales.

## Needed to proceed (when un-back-burnered)
1. Allowlist/paste of web3d.org + validatingrdf pages (DOC §6 row 1).
2. DSPy thread artifacts (68) and Tether Firehose (69) exported as text.
3. Raw data folders (research/ontology-lentz-polys-2026-10-17/…, dspy-2026-10-17) to verify numbers.
4. Decision on the public step-2 branch.
5. Decide whether ledger rows should carry ladder-rung/epistemic tags (HOOKS §7) before any ledger edit.

## Update 2026-10-21
- **Now available locally:** 4.1 Turtle (downloaded with your OK; SHA-1 verified). The doc's 4.1 numbers are recomputed, not carried.
- **Still unavailable:** Dr. Polys's real sc: files (repo 404; fork has a 363-byte fixture). `sim/` is a simulation, grade S. To replace: export the 16 .ttl files into `data/` and re-run `harness/build_sim.py`.
- Replies pending from the coordinator and gemini-eval (ledger schema, which x3d_mcp ref to pin). The ledger layer is not built.
- `X3duomToX3dOntology.xslt` is now read in full. Still unread: the Nov 2025 Visioning Lab slides, the SHACL chapters, `X3dToTurtle.xslt` (needed to fix SHACL property paths).
- Not run: Saxon (so no patched stylesheet), a reasoner, Protégé. Option A is a sketch.

## Cross-domain prototypes (2026-10-21)
- No model calls: agent failure rates in URDF and glTF are unmeasured. URDF oracle is mine (L); an independent oracle (urdfdom check_urdf, MuJoCo compile) is not installed. USD (`pxr`/usdchecker) not done. glTF corpus is synthetic; Blender exports not used.
- Model-driven eval of the URDF and glTF loops is planned (`xdomain/eval-plan/PLAN.md`) and waits for the user's go; stub run only.

## Ledger note from gemini-eval (2026-10-21, `ai/NOTE-for-ontology.md`)
- Row schema is unchanged. `corpus/ledger.jsonl` has an `id` plus a `cols` dict whose columns vary by document and version, so the fixed `id|claim|value|uncertainty|primary source|second witness|grade|year` row exists for only part of the occurrences. A ledger layer must read `cols` tolerantly.
- Parse artifact: some `grade_history` steps in `corpus/ledger_latest.json` come from reference-list lines (A1 shows a false "Confirmed" step). Do not treat every history entry as a real grade change.
- The audit (`ai/ledger-audit/`, not final) lists flags, never corrections, each `verified` or `plausible-unverified`. Model-proposed features are candidates graded Suspected, never ledger rows; the AI work does not edit `corpus/` or EVIDENCE.md.
- Grade rules to respect: every claim carries a grade (Confirmed / Likely / Contested / Suspected / Question), a source and a hash tether; generated content is labelled as generated. Private until 1 Jan 2027.
- So the Shroud ledger layer in the explorer is now buildable from `corpus/ledger.jsonl`, read-only; not started.
