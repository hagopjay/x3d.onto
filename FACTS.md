# Key findings (numbers quoted exactly; grade as in source)

Tags: [27]=README (27).md, [28], [29], [30] likewise, [DOC]=DOC.md, [P24]=polys2024-notes.md, [H21]=hitzler2021-notes.md, [WS]=web3d-search-summaries.md, [REF]=references.md, [FW]=flywheel REPORT.md. "Fork eb4b4b4" = hagopjay/x3d_mcp main; X_ITE 16.5.0 unless stated. Where a source gave no grade I write n/a.

## A. Ontology vs XSD (the "map, not a gate" result)
1. Ontology direction = four-author x3d_mcp paper future work (7.3: Turtle as MCP resource + SPARQL tool) and Brutzman & Flotyński X3D Ontology. No ontology proposal by Rick Lentz found. **S** [27 #1, DOC]
2. README ships query_ontology, node_parents, describe_ontology_term over **17,736 triples** (bundled 4.0): "Ontology answers are advisory; XSD and semantic validation remain ground truth." **C** [27 #2]
3. Real 4.1 ontology, 10 child types: **348** predicted legal parents; XSD 4.1 accepts **150**, rejects **163**, **35** inconclusive; **47.9% of 313** conclusive accepted. Negative controls: 0 wrongly accepted in 10 of 10. **C numbers; cause L** (XSLT makes every node-valued field a sub-property of hasChild with abstract-type ranges, e.g. Gain takes any child, schema allows audio nodes only). [27 #3, DOC §2]
4. Earlier run, bundled 4.0: **319 / 148 / 137 / 34 (51.9% of 285)**. 4.1 adds 9 classes, 11 object properties, 15 datatype properties, 385 triples (**18,121 vs 17,736**). Net 29 extra pairs: 26 rejected, 2 accepted, 1 inconclusive. **C** [27 #3, DOC]
5. Caveats: 4.1 file's namespace IRI version rewritten to 4.0 for loader (terms unchanged); some rejections are harness artifacts (Layer, LayoutLayer); 163 not all adjudicated; 10 types, containment only. **C** [27, DOC]
6. Per-type table (predicted/accepts/rejects/inconclusive): Sphere 10/5/3/2; Box 10/5/3/2; Material 3/2/0/1; Appearance 2/2/0/0; Coordinate 15/14/1/0; PointLight 57/24/27/6; TimeSensor 57/24/27/6; Transform 57/21/30/6; Shape 59/22/30/7; ImageTexture 78/31/42/5. **C** [DOC §2]
7. Authors' own purpose: ontology "not designed for rendering, but rather for querying and reasoning"; hasChild/hasGeometry "derivative properties to facilitate query". **C** [27 #10]
8. Hitzler 2021: ontology = knowledge base for "data integration, sharing, and discovery"; silent on validation/SHACL/open-world; names consolidation as blocker. Background only. **C** [27 #12, H21]
9. Rule: "Ontology proposes, shapes dispose, the validator gates." Never write "the ontology can gate". **L** (heuristic) [DOC §7]

## B. USE checks (SPARQL vs XML pass)
10. Dangling-USE SPARQL agrees with validator, adds nothing. Wrong-type-USE SPARQL: found **96 of 96** injected faults, **31** of them passed both XSD and fork; **0 false alarms** on **200** Consortium archive scenes, **2,426** USE lines (96 scenes with USE; 95% upper bound by rule of three 1.5% scenes / 3.1% USE-bearing / 0.12% USE lines). **C** for these runs; the 31 depends on replacement-tag choice. [27 #9, 28]
11. Detection table (96 wrong-type / 96 dangling): SPARQL 96/96; XSD rejects 65 (64 beyond clean) / 0; fork 59 new errors (all containerfield side effects; no wrong-type USE check) / 96; neither: 31 / 0. **C** [28]
12. Blind spot: document order not in Turtle, so USE-before-DEF invisible to SPARQL. Fork flags 3 USE lines in MetadataNodeExamplesX3D4.x3d (lines 35-37 vs DEF 42-44); not adjudicated; nothing sent. **C observation, L that it breaks the rule** [28]
13. Published Altar.ttl differs from regenerated on 78 of about 374 lines (HEAD emits per-type properties). **C** [28]
14. Step 2 (fork branch claude/ontology-lentz-polys-3j5h8z, commit 29a4e98 on eb4b4b4): 7 new tests, **431** fork tests pass; **0/200** clean flagged, **96/96** injected wrong-type found, 96 dangling raise no type finding; 1.2 s for 200. Branch is **public** (fork visible); AI trailer; user asked rewrite/delete. **C** [30, 27 #15]
15. First real case: Burruss writer chain gemini-3.8-flash, flagged wrong-type USE every round (1, 2, 1, 1); one chain, "a case and not a rate". **C** [30]
16. Side finding: 14 of 200 scenes have error-level fork checks unrelated to USE (19 scene-check pairs); one scene XSD-invalid (MultiTextureTeapot.x3d). **C** [28]

## C. UOM claim check
17. Carlson/Gemini X3D 4.1 review (ai list, 4 Mar 2026): **7 of 8** node/field claims consistent with X3DUOM 4.1 (generated 2026-06-21, sha1 08116b57…); 1 not (upVector only on TextureProjector family). One review, one model. **C readings, L interpretation**. [29]

## D. Polys 2024 and the rerun
18. Polys 2024: **1,200** trials (3 models × 4 strategies × 100); **47.92%** schema failure; XML failure avg **5.67%**; **86%** of zero-shot Llama3 failures lacked version; **34%** still rendered; few-shot best, CoT worse. **C** [P24, 27 #5]
19. Rerun (gpt-4o, gemini-3.8-flash, gpt-oss-20b; 1,200 trials): schema failure **29.4%** [26.9, 32.1] vs 47.92%; XML failure 5.3%; gpt-4o 11.8%, gemini 30.0%, gpt-oss 46.5%. Few-shot **5.0%** vs 34.7% zero-shot (p=4e-21); CoT 39.7% (p=0.24; gpt-4o worse 20% vs 8%, p=0.024); system prompt 38.3%. Version defect: 13 of 353 failures, none in 300 zero-shot. **C trials; NOT a replication** (only gpt-4o same family; prompts 0-3 and 9 and few-shot examples reconstructed = **S**; validator is fork's). Spend **$6.43 of $10**. [30]
20. 98.9% of rendered scenes show something; 4 of 847 XSD-valid scenes draw nothing. Colour primitives fail 17.8%, named objects 41.0% (p=1e-18). Extraction rule matters: first vs longest code block turned 15 CoT answers into "XML failures". **C** [30]
21. Default xmlns on `<X3D>`: gpt-4o 11 trials, gpt-oss 21 (32 total); message "No matching global declaration…" doesn't say remove it. **C** [30]
22. Not done: Llama 3 70B / Codestral (not served); no human rated renders; laguna-xs-2.1 pilot 38 trials, 57.9% schema failure (n=40 in table row). **C** [30]

## E. DSPy arms (gemini-3.8-flash, 100 trials/arm, Polys prompts the optimiser never saw) — **L**
23. Prompts 5-9 failure / all ten: plain **84% / 42%**; DSPy Full allowed **64% / 33%**; DSPy Full barred **30% / 15%**; few-shot (my 5 examples) **6% / 3%**. Full-barred vs plain p=7e-8; examples vs Full-barred 6% vs 30%, p=0.003. [30, DOC §8]
24. Goodhart pattern: Full-allowed prompt: valid scenes declare Full in **67 of 67**; roughness on Material in **18** scenes despite prompt forbidding; Full-barred: Immersive **85 of 85**, roughness **0**; 13 of its 15 failures = castShadows on DirectionalLight. Plain: Interchange 56, Immersive 2; roughness 26 scenes. [30]

## F. Parts and contact — **L**
25. Strict contact: prompt 2 "on top of" gpt-4o: 34 valid, **15 resting on sphere**; 24 of 40 well-formed sink/gap. Prompt 3: 33 valid, 22 strictly separated (14 of 39 overlap). Prompt 4 left/right: every valid scene correct (gemini 40, gpt-4o 36, gpt-oss 20). 340 of 342 cones point up. Floating parts: human figure gpt-4o 27/40, gpt-oss 25/37, gemini 15/40; sailboat gpt-4o 17/38; castle gemini 3/40 (lower bounds). 12 hand-built scenes pass; 28 renders checked by eye. [30]

## G. Valid / visible / complete (Y8, spine; fork d5598c4)
26. **203 of 1,058** valid scenes draw nothing (19.2%). Completeness 71.8% first-try valid, 61.8% after one repair (671 scenes), 38.5% after two (78). Two judges agree 92.0% (kappa 0.82, 150 items). Judge right 97%, names real error 73%. Report shown: 131 of 138 verdicts agree; 55 of 68 repairs pass. **C** [DOC §2]
27. E1: gemini-3.8-flash first-try valid 27.3% → 56.7% with two retrieved examples (McNemar p about 1e-16); gpt-6.1-sol 64.0% → 86.7% (150 prompts). Header auto-add: 19% → 89%. Y9 SFT 8B: 18.0% → 38.5% after 3 repairs, DPO no gain. **C** (E1/Y9 sources not ingested, see GAPS) [DOC §2]

## H. Provenance / flywheel
28. x3dprov kept in 6 of 6 Blender import→export scenes (5 KB to 62 MB; bpy 5.2.2, bridge 206f139), verdict unchanged. **C** [DOC §2]. Flywheel REPORT: record survived 7 of 7 steps; 611 bytes/step (recorded, R); flipping LAST step still verifies, sign it (x3dprov 0.2). **C** [FW]
29. X3DUOM 4.1: 267 concrete nodes, 7 new in 4.1; ontology 17,736 triples. 35 MCP tools listed. **C/R** [FW]

## I. Access / people
30. Carlson raised surface-only JSON check 21 Apr 2026; Lentz commit 7b42d9d (28 Apr 2026) added full JSON Schema validation. **C** (git history). [27 #13]
31. Search-tool summaries (April 2026 thread, 17 Jul 2026 blog): "official Web3D open-source project", "28 tools and 4 guided prompts across nine modules"; 4 prompts agree with README, 28 tools unchecked; nothing on ontology. **S**. [WS]
32. sc: spatial-cognition ontology (npolys/3D_perspective_skill): 16 files, 418 triples, all 58 referenced X3D terms resolve, 41 groundings join to X3DNode subclasses; from fork PR #5 body (13 Oct); repo itself 404. **L** [27 #4, DOC]
33. OntoGuard: two things carry the name (ACL 2026 Findings; Towards AI post Feb 2026); only search summaries read. **S** [DOC §8]

## J. Open next-step rows (DOC §6, none done except 2-4)
1 allowlist web3d.org etc.; 5 read cached-unread; 6 convert 3,058 spine scenes to Turtle; 7 note on 3 USE-before-DEF lines (hold); 8 SHACL shapes layer (needs book chapters); 9 use-type check / SPARQL USE into DSPy metric; 10 exact-fix hints (xmlns, Cone radius, roughness, castShadows); 11 mine containment rules from 3,058 scenes (OntoGuard pattern). Ten questions to Polys: nothing sent.

## K. How the ontology is exposed today (x3d_mcp local HEAD fa0b389, read C)
- `src/tools/semantics.py`: three MCP tools. `query_ontology(sparql, include_extensions=False)` → JSON `{rows,count}` or `{error}`; prefixes x3d, sc, owl, rdf, rdfs, dcterms pre-declared (SELECT/ASK; ASK returns `{"ask": bool}`). `node_parents(node_type)` → `{nodeType, parents:[{parent, field}]}` via `rdfs:subPropertyOf+ x3d:hasChild`, range subsumption, **filters out bare X3DNode and non-IRI ranges** (so the aggregate hasChildren family is excluded) — local code; whether this filter was in eb4b4b4 (used for the 348 numbers) is **unchecked**, so those numbers may not describe this tool's output. `describe_ontology_term(term)` → types, labels, super/sub classes and properties, domains, ranges, inverseOf.
- `src/x3d_utils/ontology.py`: loads **X3dOntology4.0.ttl** from `src/validation/schemas/` (namespace `https://www.web3d.org/specifications/X3dOntology4.0#`) with rdflib; singleton `get_ontology()`. Optional extension graph (separate) from env `X3D_MCP_EXTRA_ONTOLOGIES`, 4.1 IRIs aliased to 4.0, `extension_status()` reports unresolved terms. Docstrings: answers advisory. No SHACL, no write path, no 4.1 file bundled.

## L. Added 2026-10-21 (harness run; see README.md)
- On the bundled 4.0 file, `node_parents` returns **366** (parent, field) pairs for the 10 cross-check types; **319** have a concrete X3DUOM parent (= the doc's 4.0 figure, reproduced by harness/test_harness.py); the other 47 have abstract parents. **C** (computed, checked against live tool code at x3d_mcp fa0b389).
- Bundled 4.0 ontology: 355 classes, 326 object properties, 712 datatype properties, 140 hasChild-family properties, 51 classes with more than one parent, max depth 5. **C**
- Constellation scene authored through x3d_mcp: 4,511 tool calls, 9.4 s, p50 1.7 ms per call; whole scene valid against XSD 4.1, 0 semantic errors. One run, this machine. **C**

## M. Added 2026-10-21 (4.1 + XSD matrix + UOM oracle; see README.md; all C unless marked)
- The Web3D 4.1 Turtle (downloaded from the SVN mirror on SourceForge, SHA-1 1b5d645a… = the doc's manifest): **18,121** triples, **364** classes, +9 classes, +11 object properties, +15 datatype properties, 385 more triples than 4.0: all as the doc says.
- On 4.1, `node_parents` logic gives **397** (parent, field) pairs for the 10 cross-check types, **348** with a concrete parent: the doc's 348 is reproduced.
- The doc's whole 10-type table (child by child) and totals **348 / 150 / 163 / 35** are reproduced exactly with the doc's method on the 4.1 file.
- All concrete pairs: **11,085**; **5,206** accepted, **4,570** rejected, **1,309** inconclusive (53.3% accepted of conclusive; 10-type slice 47.9%). 26 of 263 child types are accepted everywhere they are predicted; 57 of 266 parent types accept none of the children predicted for them. Run time 1.9 s.
- Parents rejecting most predicted children: Contour2D 439, HAnimJoint 437, CADPart 436, DISEntityManager 152. Inconclusive pairs are mostly harness placement (LayoutGroup 444, GeoLOD 237, Viewport 156).
- X3DUOM `acceptableNodeTypes` vs XSD verdict, on pairs the ontology predicted: 5,170 allow/accept, 643 allow/reject, 36 deny/accept, 3,926 deny/reject; agreement **93.0%** (95.0% setting aside 202 containerField-enumeration rejections). Ontology-only share right: 53.3%. L: cause of the 643 not adjudicated.
- Simulated sc: vocabulary: 8 files, 80 concepts, 908 triples; all 96 class and 63 field groundings resolve against 4.1. **S**; not Dr. Polys's data.

## N. Added 2026-10-21 (stylesheet read; see proposal/PROPOSAL-narrowed-ranges.md)
- `X3duomToX3dOntology.xslt` (SVN HEAD, 1,220 lines, 67,046 B, SHA-1 f443c05f…): read in full. It emits each node-typed field's range from `@acceptableNodeTypes` (single IRI or anonymous `owl:unionOf`) with one `rdfs:domain` per emitting node; the property name is `has` + field name, so parents share the IRI. **C** (code reading).
- On the 4.1 Turtle: 125 hasChild-family properties, 48 with more than one rdfs:domain; `hasChildren` has 49 domains, 7 IRI ranges and 17 anonymous unions (30 distinct members); `hasMetadata` and `hasIS` have 331 domains each. **C**
- Containment fields only (excluding 1,897 event-port pairs and 1,584 metadata/IS pairs): 7,604 pairs; XSD 3,548 accepts / 3,504 rejects / 552 inconclusive (50.3% of conclusive). **C**
- X3DUOM `acceptableNodeTypes` vs XSD on those: 3,512 allow/accept, 441 allow/reject, 36 deny/accept, 3,062 deny/reject: agreement 93.2% of 7,051; allow precision 88.8%. **C**
- UOM universe 4,907 pairs; the ontology (as `node_parents` reads it) has 4,455 of them; the 452 missing: XSD accepts 113, rejects 322, inconclusive 17. UOM-allowed and XSD-accepted pairs 3,625, of which the ontology has 3,512 (96.9%). Narrowed set is 35.5% smaller than 7,604 and accepted on 82.6% of its conclusive pairs. **C**
- Event-port pairs: 1,897 with XSD 410 accepts / 1,066 rejects / 421 inconclusive (XSD takes containerField='addChildren' syntactically; these are ROUTE ports). **C**
- Option A sketch: 310 restriction axioms, 2,088 triples; query over base + sketch returns exactly the 4,907 UOM-universe pairs. **C** for the encoding; no reasoner run. 

## O. Added 2026-10-21 (cross-domain prototypes; see xdomain/README.md)
- glTF: Khronos glTF-Validator 2.0.0-dev.3.10 on 6 clean models: 0 errors, warnings, infos and hints. 123 mutants from 25 fault operators: error-level 106 (86.2%); warning/info only 17 (required unsupported extension 6, unused accessor 6, primitive without POSITION 5); a minimal structural baseline flags 18 (14.6%). Repairs: 19 of 19 end clean. **C** (my fault set).
- Khronos reports a required unsupported extension and a primitive without POSITION as warnings; the server's strict gate promotes them (1 error upstream, 2 under the gate on the test document). **C**
- URDF: own rules (L). 6 clean robots 0 errors 0 warnings; 135 mutants from 24 operators; caught at parse 6, structure 36, semantics 81, warning-only 6, contact-only 6; 0 missed (by construction); repairs 17 of 17 end clean. **L** (oracle not independent).
- MCP kit over stdio: 7 tools; median call 1.9 to 7.6 ms except `gltf_validate` 93 ms (node spawned per call); chain verdicts ok / stale / broken-chain as designed. **C**
- Per X3D component (data/components.json, containment fields): XSD-accepted share of the ontology's predictions ranges from 10.9% (Layering) to 73.3% (Sound); RigidBodyPhysics 25.3%. **C**

## P. Added 2026-10-30 (genealogy loom thread, "Dynasty Loom"; X_ITE 16.5.1 from the npm tarball, Chromium 153 with SwiftShader, Playwright 1.63)
Tags: [GL-S] = `evidence/genealogy-loom/xite-shaderpart-cdata/` (in this repo); [GL] = the genealogy project's files (`genealogy-loom/scene/`, `genealogy-loom/x3d-techniques/`; hypersphere camera proof `proto/hyper/tools/drive_camera.js`), not in this repo.
- Raw GLSL in a ShaderPart's CDATA fails in X_ITE 16.5.1. X_ITE reads the body as the `url` field, so `#version 300 es …` resolves as a fragment of the world URL. The world file is fetched three times, `isValid` is false and the shape draws unlit white. With `data:x-shader/x-vertex,` (or `x-fragment,`) in front, `isValid` is true with no request. Both files pass xmllint (x3d-4.0.xsd) and fork `acdf5c4` with 0 errors: another valid-but-invisible case (item 26). **C** [GL-S]
- HagopJay's three pocket-universe pages as shared (6 ShaderParts, raw CDATA) draw white spheres; with the prefix all three render. New Loom gate rule `shader-raw-source`: 6 of 6 raw parts and 2 of 2 in the probe flagged; 0 hits on 798 X3D files from x3d.onto (less `xdomain/fuzz`), x3d.ml, x3d-blender-io and the genealogy builds, 26 of them with ShaderParts, all prefixed. **C** [GL-S, GL]
- A `%` in a prefixed CDATA body is harmless: a bare `% 2` and a `%20` both compile, so the body is not percent-decoded. (A `data:` URL in the `url` attribute is decoded, as `loom_gate.shader_sources` reads it: **L**, not re-run here.) **C** [GL-S]
- Under a strict copy of the claude.ai Artifact CSP (`default-src 'none'`; scripts from self and five CDNs; no `unsafe-eval`; `connect-src 'self'`):
  - X_ITE's own WOFF2 fonts are decoded through `new Function`, which the CSP refuses, so Text draws nothing.
  - A TTF named first in `FontStyle.family` (`'"fonts/UbuntuMono-R.ttf" "TYPEWRITER"'`) draws.
  - X_ITE must ship beside the page: x_ite.css, `assets/components/*`, `assets/images/*`, linetypes.png and the mikktspace wasm.
  - The host refuses `.x3d` as `model/x3d+xml` and serves it as `application/xml`.
  - X_ITE's PT Sans UI font and the wasm compile are refused harmlessly.
  - Grade: **C** under the copy (2 runs: desktop light and phone dark, 3 scenes each, all labels drawn); **L** on the real host. [GL]
- X_ITE's EXAMINE straightens the horizon to the Viewpoint's local +Y, both on bind and on the first drag. A rolled Viewpoint at the scene root snapped from 59.9° of roll to 0 on the first drag. Rolled shots therefore need a parent Transform as an up frame, with the Viewpoint bound at zero roll inside it. Over 29 driver checks, every flight lands within 0.001 units and 0.001°. **C** [GL]
- A page-moved rig (a Transform holding the Viewpoint, the pocket-universe pattern) keeps `centerOfRotation` fixed. After a plunge, a drag orbits a point 22 host units behind the subject (983 px drift). Setting `centerOfRotation = -rig.translation` every frame gives 0 px drift. **C** [GL]
- Navigation and nesting:
  - `Viewpoint.navigationInfo` (X3D 4.0) binds its NavigationInfo together with the Viewpoint. The transition into that Viewpoint uses the transitionTime of the NavigationInfo bound before it (1.6 s), not its own (2.4 s).
  - IMPORTed Viewpoints and ProximitySensors work through an Inline scaled 0.5 and report positions in the Inline's own units.
  - A scriptless orbit (TimeSensor → OrientationInterpolator → Transform around a Viewpoint) turns at a constant 0.05236 rad/s.
  - Grade: **C** [GL]
- X_ITE's Text bounds are about 0.62 of `FontStyle.size` in height (Ubuntu Mono): labels sized by the nominal size drew at 8.4 px. Size labels from measured `textBounds`. **L** (one font, measured in the live gate) [GL]
- A PhysicalMaterial with metallic 1.0 renders black in a scene without an environment light; metallic 0.6 with roughness 0.35 reads as gold. **C** (frames) [GL]
- SwiftShader frame hitches of up to 254 ms fail a per-frame step check on a smooth camera move. Measure speed against the requestAnimationFrame clock instead: on the 9-stop tour, peak over mean was at most 3.4 (linear) and 5.3 (angular). **C** [GL]
- The Loom gate's `glsl-int-literal` rule read the `0` in `smoothstep(q == 0 ? .57 : .5, .86, n)` (an `int q`) as a float argument. That line compiles in X_ITE 16.5.1: the hypersphere's gate has 0 console errors and 67 of 67 frames lit. Over 859 X3D files (x3d.onto less `xdomain/fuzz`, x3d.ml, x3d-blender-io, x3d_mcp and the genealogy builds), the rule's 62 findings were all this one line, copied across builds. The rule now leaves an operand of a comparison alone inside a float builtin: 0 findings, none added. A float compared with `0` is still flagged, by the next-to-a-float test. **C** [GL]
