# Directions and augmentations (brainstorm; each line says what it needs and what it rests on)

Tags: **[C-based]** rests on a measured result in this folder; **[S]** speculative. Nothing here has been sent to anyone; upstream means Web3D Consortium, whose X3D ontology sources live in SVN (contributions go through the working group, not a GitHub PR; the x3d_mcp repo is on GitHub).

## A. Close gaps with evidence already in hand
1. **Keep the per-parent ranges that the stylesheet already writes.** Having read `X3duomToX3dOntology.xslt` in full: it emits each range from `acceptableNodeTypes` per parent, but all parents emit the same property IRI (`hasChildren`: 49 domains), so the Turtle pools them. Three options and the numbers are in `proposal/PROPOSAL-narrowed-ranges.md` (held, not sent); option A (additive restriction axioms) is sketched and round-trips X3DUOM exactly (4,907 pairs). [C-based]
2. **`node_parents(verified=true)` in x3d_mcp.** Additive option backed by the UOM lookup (no XSD run needed at query time) or the shipped verdict table. Needs: upstream agreement; tests. [C-based]
3. **Adjudicate the residue.** 441 UOM-allows/XSD-rejects pairs (Layer 96, LayoutLayer 93, GeoLOD 52, Collision 50, pick sensors ~95): either the UOM list is too wide or the XSD has extra rules (sibling or content-model constraints). Each answer is a concrete question for the Consortium; hold until you say send. [C-based]
4. **Exact-fix hints from the 4,570 rejection messages.** "Element X is not expected" becomes "X cannot go in P.field; allowed parents: …". Pairs with the exact-fix item already in DOC section 6 row 10. [C-based]
5. **SHACL for rung 4.** Generate one shape per (parent, field) from UOM ranges; validate on the 200-scene archive sample from README (28) as an oracle (0 expected false alarms). Needs: fix the Turtle property path (run X3dToTurtle.xslt HEAD on a scene), `pyshacl`. [C-based]

## B. Interaction and visual ideas
6. **Scene lens.** Convert a real scene (the Shroud cloth, 195 features) to Turtle and light up the classes it uses, with instance counts, on the map. [S]
7. **Live bridge.** A small local HTTP wrapper over x3d_mcp's three ontology tools so the explorer calls them live and shows what an agent would see. [S]
8. **Trace replay.** Animate an x3dprov chain across the constellation: each step lights the nodes it created, with a time slider. Ties the tether to the ontology. [S]
9. **Ledger satellites.** Evidence rows orbit the Metadata-bearing nodes they concern, coloured by grade (Confirmed, Likely, Contested, Suspected, Question). Needs gemini-eval's schema note. [S]
10. **Quiz mode.** "Guess the legal parents of X" scored against the verified matrix; a teaching aid for conference demos. [S]
11. **Matrix as a diff tool.** Overlay two ontology versions or two validators (XSD vs Schematron vs UOM) cell by cell. The UOM-vs-XSD mode is the first instance. [C-based]

## C. Harness and scale (the Dyson-shell goal)
12. **Scale ladder.** Run the constellation builder at 10^2 → 10^6 nodes through MCP with DEF/USE and Inline; record per-call latency, validate time and X_ITE render time; find the knee. Today: 4,784 calls, 166 KB, validate 1.8 s. [C-based]
13. **Nano-scale precision test.** Place features of 1e-6 m at offsets of 1e6 m and see where float32 translation loses them; compare against `GeoOrigin`/double paths. The sim `NanoScale` concept carries this as an arithmetic hypothesis. [S]
14. **Property-based fuzzing of the validator.** Sample legal containment from the verified matrix to generate scenes; any XSD rejection of a verified-legal placement is a bug report. [C-based]
15. **Two-runtime check.** Render the constellation in X_ITE and X3DOM and diff pixels (cull-list items 2 and 16 in the flywheel REPORT). [S]

## D. Evals and DSPy
16. **Lawful metric.** A DSPy metric that scores valid + lawful containment + use-type + parts/contact, with escape hatches (profile Full) closed, run on the 1,200 Polys trials. Needs: the DSPy thread. [S]
    - Built 2026-10-29: `xdomain/lawful/` (metric, DSPy program, tests). Model-free: catches 16 of 16 hand-built failures (strict gate passes 13), AUC 0.997 vs strict validity on 383 recorded x3d.ml documents [C]; the 1,200 Polys trial files and per-document judge scores are not on this machine; model quality S until a Gemini run (README there).
17. **Lookup before judge.** Give the judge model the verdict matrix and UOM ranges so it names the real error more than 73% of the time. [S]
18. **Mine tighter rules.** Count real containment in the 3,058 spine scenes, compare with UOM ranges (OntoGuard pattern). Needs the spine converted to Turtle (DOC row 6). [S]

## E. Standards-facing (for the extension proposal with Jakub Flotyński)
19. **Per-field ranges from UOM** (A1) plus a **smoke-test set**: the gallery queries and the 10-type table as ROBOT-style assertions the build runs. [C-based]
20. **Spatial relations with tolerance semantics.** What "contact" means (5% in step 4), judged on camera axes; strict vs loose. The sim `parts_contact` and `prepositions` modules sketch the vocabulary; the real sc: files should replace them. [S]
21. **Provenance.** Map x3dprov to PROV-O; Time ontology for dating records (DOC Q7). [L]
22. **Stable 4.1 IRIs** and a statement of what changes before 4.1 is final (DOC Q6): the 4.1 file dropped 19 shared child-field property names (`children`, `geometry`, ...) in favour of per-parent forms. [C-based]

## F. Wilder
23. **Ontology as an MCP resource** for agents (the paper's 7.3 proposal): ship `explorer.json`-style data plus the verdict table. [C-based]
24. **Cross-format alignment** with glTF/USD vocabularies via `t3dmo.ttl`; heat-map the missing mappings. [S]
25. **Mind-palace Shroud.** The ontology shell as an orbit around the cloth twin, ledger rows as satellites; a showcase scene for the Dyson-shell theme. [S]
