# X3D ontology constellation (v1: 4.1 + XSD matrix + simulated sc:)

Built 2026-10-20/21. Serve with `cd ontology && python3 -m http.server 8791`, open `/explorer.html` or `/constellation.html`. Rebuild everything: `harness/make.sh`.

## What is here
- `explorer.html` (2.1 MB, self-contained): 2D explorer of **X3D Ontology 4.1** (364 classes, 18,121 triples). Eight colour lenses, seven overlays, hover cards, a six-tab inspector, SPARQL gallery, MCP-tool popup, cross-check popup, a full XSD containment matrix (three modes), a ladder popup, and a simulated sc: layer. Press `?`.
- `constellation.html` + `scenes/ontology-constellation.x3d`: the same classes on a Dyson-style shell in X_ITE 16.5.0 (CDN), authored through x3d_mcp's tools and validated by it. Green = new in 4.1; edges from Shape are coloured by XSD verdict.
- `data/`: `X3dOntology4.0.ttl` (copied from x3d_mcp), `X3dOntology4.1.ttl` (downloaded from the Web3D SVN mirror on SourceForge; SHA-1 matches the doc's manifest), models, `xcheck_all.json` (11,085 verdicts), `uom_ranges.json`, `sim.json`, `explorer.json`.
- `sim/*.ttl`: the **simulated** sc:-style vocabulary (8 files, 80 concepts). `DIRECTIONS.md`: possibilities and augmentations. `INDEX/FACTS/GLOSSARY/HOOKS/GAPS.md`: the ingestion deliverables from the first session.

## Results (all Confirmed unless marked; fork checkout fa0b389; one run each, this machine)
| what | result |
|---|---|
| 4.1 file | 18,121 triples, 364 classes; adds 9 classes, 11 object and 15 datatype properties, 385 triples: all four match the doc |
| node_parents on 4.0 and 4.1 | identical to the live tool logic for all 355 and 364 classes |
| doc's 10-type table (348 / 150 / 163 / 35) | **reproduced row by row** on the real 4.1 file with the method of `evaluation/cross_validate_ontology.py` |
| extended to every concrete node | 11,085 pairs in 1.9 s: **5,206 accepted, 4,570 rejected, 1,309 inconclusive**; accepted share of conclusive pairs 53.3% (10-type slice 47.9%) |
| X3DUOM `acceptableNodeTypes` as an oracle | agrees with the XSD on **93.0%** of 9,775 comparable pairs (95.0% setting aside 202 containerField-enumeration rejections); UOM allows/XSD rejects 643, UOM denies/XSD accepts 36 |
| constellation scene via x3d_mcp | 4,784 tool calls in 10.0 s (p50 1.9 ms, p95 2.7 ms); 165,953 B; `validate_x3d` valid against XSD 4.1 (1,792 ms); `validate_semantic` 0 errors, 0 warnings, 378 infos (`unused-def`, kept so classes can be picked by name) |
| 4.0 reading of the doc's 319 | 366 (parent, field) pairs on 4.0, 319 with a concrete parent; 4.1: 397 and 348 |

## Narrowed-ranges proposal (drafted, HELD, nothing sent)
`proposal/PROPOSAL-narrowed-ranges.md` (cover note + two-page note for Jakub Flotyński, with questions first), `proposal/X3dOntology4.1.narrowing-sketch.ttl` (310 additive restriction axioms), `proposal/narrowed_node_parents.rq`. Basis: `X3duomToX3dOntology.xslt` (SVN HEAD via SourceForge, 67,046 B, SHA-1 f443c05f…, read in full, kept in `data/xslt/` as untrusted data and never executed). Finding: the stylesheet already writes each range from `acceptableNodeTypes`, but every parent emits the same property IRI, so the Turtle pools them (`hasChildren`: 49 domains; 48 of 125 hasChild-family properties have more than one). On containment fields only: 7,604 ontology pairs, XSD accepts 50.3% of the conclusive ones; X3DUOM lists agree with the XSD on 93.2%; a list-built set has 4,907 pairs, keeps 96.9% of the legal ones and is accepted 82.6%. The restriction sketch round-trips X3DUOM exactly (4,907 pairs, 0.5 s) but no reasoner, Protégé or patched stylesheet was run.

## The simulated sc: layer (grade S, read before using)
The real sc: ontology (Dr. Polys's 3D_perspective_skill; reported as 16 files, 418 triples) could not be read: the repo returns 404 and the fork holds only a 363-byte test fixture. `sim/` is a **guess**, written from this project's own measurements (frame check, parts-and-contact, the 2024 prompts, the Shroud ledger grades, the verification ladder), in the namespace `https://example.invalid/sim/spatial-cognition#` so it cannot be confused with the real one. 80 concepts, 908 triples; all 96 class and 63 field groundings resolve against 4.1 (the first draft had 5 misses, fixed against the model, which says only that the guesses name real terms, not that they match Polys). The `verification` module is formalised from DOC.md's ladder (grade L), not simulated. Swap in the real files by pointing `build_sim.py` at them.

## Cross-domain prototypes (`xdomain/`, README inside)
The validator-MCP pattern applied to **URDF** (own rules, grade L) and **glTF** (Khronos validator, installed with your OK): one server, seven tools, one report shape, deterministic repairs, a hash-chained record. 135 URDF mutants and 123 glTF mutants; Khronos flags 86.2% at error level and treats three fault classes as warnings only (a gate policy is needed); repairs end clean 36 of 36; 10 tests pass. No model was called, so agent behaviour is not measured. Dashboard in the conversation; numbers in `out/xdomain_*.json`.

## Razzle-dazzle demo (`demo/`, README inside)
The ontology Dyson sphere: the loop ring, the 364-class shell and three domain rings as three modules in one X3D scene (authored through x3d_mcp, valid XSD 4.1, 0 semantic errors), pulled into one sphere by an Assemble animation. `demo/demo.html`; number audit passes; evaluation pillars fill in when the model runs finish. Private.

## Harness (`harness/`)
`export_uom.py` (X3DUOM facts) · `build.py` (ttl → model; run for 4.0 and 4.1) · `xcheck_all.py` (XSD verdict for every pair) · `uom_ranges.py` (UOM oracle) · `gen_sim.py`, `build_sim.py` (simulation and its resolution report) · `merge.py` · `embed.py` · `test_harness.py` (4.0, 12 checks) · `test_harness41.py` (4.1, XSD, UOM, sim, 13 checks) · `make_constellation.py` (MCP stdio client). All read-only on the x3d_mcp checkout.

## Limits
- Layout, colours and families are display choices. Gallery SPARQL results are precomputed by rdflib, not run live in the browser.
- Verdict rows are the pairs the **ontology predicted**, one placement each, with the doc's harness rules; not every possible pair, and not a full-schema conformance test. 1,309 pairs are inconclusive (mostly the harness cannot place the parent: LayoutGroup 444, GeoLOD 237, Viewport 156).
- The 643 UOM-allows/XSD-rejects pairs: 202 are containerField enumerations, 441 are not adjudicated.
- The proposal is a draft: its numbers are from this harness, its option A is a sketch, and a reply from the Consortium side could change the picture (a design reason for the shared property names).
- Shroud ledger rows are not in the explorer (waiting on gemini-eval's schema note). No SHACL was generated: the Turtle converter's property path for each child field must be fixed first. No x3dprov stamp on the scene. Not checked in a second runtime.
- x3d_mcp checkout is on `fix/physics-findings` (unpushed). Nothing in any repo was changed; no email or message was sent to Jakub or anyone.
- Reproducibility: every number was computed against x3d_mcp checkout `fa0b389` on the unpushed branch `fix/physics-findings`. The public fork `main` is `cf84f64`; the physics fixes are not in it. Re-running on `cf84f64` is untested here, and the choice of pin is yours (coordinator note, 2026-10-21).
- Coordinator's rules honoured: no push, no Vertex or other spend, my own stdio x3d_mcp per call, the live Blender untouched, nothing sent outward.
