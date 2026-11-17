# Semantic Twin Lab — design spec v1 (13 Nov 2026)

Picks (all accepted 13 Nov): finish line BUILD, home BOTH (preview first, then the public x3d.demo page), engine LIVE, LLM evidence RECORDED, look TWIN, scene BESPOKE.

Tagline: **Every object has a twin made of facts. Ask it. Reason over it. Hold it to account.**
Thesis (carried from Oct 2026, never contradict): **the ontology proposes, SHACL shapes dispose, the validator gates.** Never write "the ontology can gate". Tether: "X3D is the 3D format an AI can be held accountable to."

## 1. The look: three strata, one world
- **World (floor):** the bespoke X3D scene "The Cabinet", rendered by X_ITE. Dark museum, glass plinths, PBR specimens.
- **Twin (mid-air, ABox):** the scene's RDF graph. Each DEF'd node's twin bead hovers directly above its object (same x,z; lifted). Edges = `x3do:has<Field>` triples drawn as thin threads; DEF/USE identity = `owl:sameAs` threads; ROUTEs = animated arcs.
- **Ontology (sky dome, TBox):** the X3D Ontology 4.1 classes used by the scene (and their ancestors, ~40-60 of 364) on a dome/ring. `rdf:type` = vertical plumb lines from twin beads up to classes. `rdfs:subClassOf` edges along the dome.
- **Lenses:** Query = spotlight cones from the dome down onto matching objects (and their beads); Reason = inferred triples appear as GOLD threads (explicit stays silver/teal); Shapes = red beacon + sh:message on violators, green halo on conformers; Gate = validator ladder stations (parse, XSD, semantic, SHACL, render).
- Colour grammar (one palette everywhere): explicit facts teal #3de6d1; inferred gold #ffc857; query hit cyan-white #e8fbff; violation red #ff5a5f WITH an icon/shape cue (never colour alone, deuteranopia-safe); warning amber #ffb347; pass green #5fd18a WITH check glyph. Grades: C green, L amber, S magenta #ff4fd8.
- Labels: HTML overlay with collision avoidance, not X3D Text (X3D Text overprints; under the CSP it needs a self-hosted .woff anyway).

## 2. The Cabinet (bespoke X3D 4.1 scene, profile Immersive unless the validator prefers Interchange+components)
Every meaningful node is DEF'd (DEF = stable IRI; "DEF what matters" is itself a lesson). Small: target < 100 KB, ready < 3 s on SwiftShader. 7 plinths in an arc, each one a lesson hook:
1. **Twin Orbs** — Sphere with DEF'd Material `Gilt`; two more orbs USE it → identity, `owl:sameAs`, DEF-as-IRI.
2. **Spinner** — TimeSensor `Clock` → OrientationInterpolator `Spin` → Transform `Spinner` (ROUTE chain, animated) → property paths, 2-hop queries, ROUTE arcs.
3. **Prism Shelf** — 5 Boxes with Materials of varied diffuseColor/transparency (one emissive) → FILTER, luminance computed from the rdf:List colour, ORDER BY, OPTIONAL emissive.
4. **Carousel** — Switch `Carousel` with 3 DEF'd children → "what RDF forgets": MFNode order and whichChoice cannot be resolved from the graph.
5. **Bare Specimen** — Shape with geometry but no Appearance → OPTIONAL / NOT EXISTS; X_ITE draws it unlit white, so the absence is visible.
6. **Label Plinth** — MetadataSet/MetadataString annotations inside X3D (title, creator, a "specimen" note) → X3D's own metadata nodes as triples.
7. **Lantern** — PointLight + the scene's Viewpoints (one per plinth + overview) → camera tour and "valid is not visible".
Lighting/backdrop: Background gradient (deep navy), a key DirectionalLight, plinth glow. Navigation: EXAMINE.

**Fault bench (break-it variants, each its own scene + Turtle):**
- F1 colour 1.5 in a diffuseColor (XSD accepts some out-of-range values via the 1.5 re-split; SHACL range catches)
- F2 Shape geometry removed (valid X3D, draws nothing; SHACL warning)
- F3 wrong-type USE (a Material USE pointing at a texture DEF; XSD passes; SPARQL/SHACL catches)
- F4 ROUTE from 'Ghost' (dangling ROUTE endpoint)
- F5 Box directly under a Transform (ontology allows via pooled hasChildren range; SHACL child-node gate and XSD reject)
- F6 USE before DEF (graph-invisible: the Turtle is identical; only the XML-order check sees it)
- F7 duplicate DEF (XSD xs:ID fails; RDF silently merges into one IRI)
Each fault states which layer catches it: ontology/reasoner (never), SPARQL, SHACL, XSD, x3d_mcp semantic, X_ITE render.

## 3. Tiers and stations (beginner → advanced; ~28 stations)
Each station: concept · misconception · 3D moment (what lights up) · live editable artefact (SPARQL / Turtle shapes / N3 rules) · expected answer from the Python oracle (the page shows LIVE result vs ORACLE with a parity badge) · equivalent x3d_mcp tool call · numbers with source and grade · a "try this edit" with its expected outcome.

- **T1 Facts (RDF):** one scene three bodies (render / Turtle / graph); a triple = subject-predicate-object; IRIs not labels (`x3do:geometry` 0 rows vs `x3do:hasGeometry`); instance vs class (`rdf:type` plumb line); DEF as identity and positional IRIs (insert one node, unnamed IRIs shift); colours as rdf:Lists.
- **T2 Questions (SPARQL):** spotlight SELECT; FILTER + computed luminance; OPTIONAL (bare specimen); property paths (`a/rdfs:subClassOf*` all geometry); the ROUTE chain 2-hop; COUNT/GROUP BY census; NOT EXISTS (dangling USE); ASK.
- **T3 Meaning (RDFS/OWL):** subclass inference (gold threads, small, safe); the Chimera (full RDFS closure: one Transform sprouts dozens of types because multiple rdfs:domain = intersection); the NURBS Box (pooled ranges); inference launders a violation (SHACL with inference=rdfs: red becomes green); OWL is not a schema (0 disjointWith: a Box can also be a Transform, consistently); open world vs closed world.
- **T4 Accountability (SHACL + gates):** first shape (Shape must have geometry); colour range via list path; the set-semantics trap (sh:minCount 3 rejects white (1 1 1)); wrong-type USE via SPARQL constraint; map vs gate (ontology proposes N parents for Box/ImageTexture, X3DUOM where_can_place lists M, XSD accepts K); two validators disagree (shacl-engine needs subClassOf in the shapes graph: 305 vs 9 on the scout data); break-it bench (F1-F7, which layer catches what); valid is not visible.
- **T5 Agents (MCP + LLM, the BUILD finish line):** what an LLM sees through x3d_mcp (tool list, the gap before this work); the new tools (scene_to_rdf, sparql_scene, shacl_validate, rdf_infer, ontology_vs_gate); recorded sessions replayed as packets travelling LLM → tool → twin; write your own shape and see the MCP verdict format; SHACL 1.2 `sh:agentInstruction` (the same shapes graph instructs and checks the agent); claims ledger receipts (hash chain, C/L/S grades) and x3dprov PROV-O.
- **Capstone: The Ladder** rung 0 parses → 1 typed → 2 valid (XSD) → 3 coherent (semantic) → 4 lawful (SHACL) → 5 visible (render) → 6 complete (judge) → 7 meaningful (provenance), all on the Cabinet.

## 4. Live engine stack (in page, no wasm required)
Self-hosted `lab-stack.js` (scout build): N3.js 2.13.12 + Comunica query-sparql-rdfjs-lite 5.4.1 + shacl-engine 1.1.3 + d3-force-3d 3.0.6 (1.50 MB min / 362 KB gzip). Cross-check validator rdf-validate-shacl 0.6.5. shacl-engine pitfall P1: copy rdfs:subClassOf triples into the shapes graph or results are wrong. P2: focusNode/value are PathList objects (use `.term`). Wasm tier (Oxigraph 0.5.13, EYE-js) only after `WebAssembly.compile` feature-detect; never required. Reasoning default = subclass-only; "full RDFS" only inside the Chimera/launder stations with a visible warning and a derivation budget.

## 5. X_ITE in the artifact
Bundle X_ITE **16.5.1** as own files (the only version with real-host evidence; MIT licence). Apply the shadow-root CSS dress (inline x_ite.css into `canvas.shadowRoot`, unhide `.x_ite-private-browser`, re-dress every 250 ms × 20), install an in-memory localStorage shim before X_ITE, self-host a .woff if any X3D Text is used. Serve scenes as `.xml` with the DOCTYPE stripped (artifact host refuses DTDs) — BUT the Turtle twin is always built at build time from the faithful pipeline (DOCTYPE kept, DTD defaults injected), never from the stripped copy (stripping changes the vocabulary: hasSphere etc.). Highlight via SAI: `getNamedNode(DEF).emissiveColor = new X3D.SFColor(...)` (0.2-0.4 ms). Picking: TouchSensor touchTime callbacks.

## 6. Faithful X3D → Turtle (build time, ground truth)
lxml parse with the local X3D DTD and `attribute_defaults=True` (injects containerField defaults) → SaxonC-HE 13.1 runs X3dToTurtle.xslt r40388. Reproduces 5/5 published Consortium .ttl byte-identically (scout C). Runner: scout `sources-and-state-of-art/scripts/x2t_lxml.py`. Pinned ontology: X3dOntology4.1.ttl mirror HEAD r40416 sha256 057f1ba083a636aa… Stylesheet sha256 e3c5aa40756b9772…

## 7. New x3d_mcp tools (fork PR, trailer-free, author x3d-xfer)
`scene_to_rdf` (native lxml walker matching X3dToTurtle conventions, containerField defaults from X3DUOM, 4.1 ontology bundled and chosen by version; Saxon optional golden), `sparql_scene` (SELECT/ASK over scene + optional ontology, guarded, paged), `shacl_validate` (bundled x3d-core shapes; results carry focus DEF, path, severity, message, shape id, fix hint), `rdf_infer` (profiles subclass-only default / rdfs / owl-rl with an explosion report), `ontology_vs_gate(child)` (map vs X3DUOM vs XSD), INSTRUCTIONS + `semantic_audit` prompt so an LLM is steered to these tools, an `instrument` block (commit, hashes, library versions) on every verdict.

## 8. Recorded LLM sessions (T5)
The LLM acts as the MCP client, deciding each call live; recorded over real MCP stdio against the PR-branch server; every call stores args, latency, result sha256 and an excerpt. Five tasks: inventory the scene; where may an ImageTexture go (map vs gate); make the prism shelf glass but keep it valid; audit a stranger's scene (fault variant) end to end with receipts; should I turn reasoning on. Never claim measured LLM improvement (no bare-vs-grounded trial was run).

## 9. Accountability of the page itself
Every number names its source and grade. One pin table (ontology sha, stylesheet sha, X3DUOM, XSD, x3d_mcp commit, X_ITE, engine versions, Chromium version). Live-vs-oracle parity badge per station. Receipts panel. `audit_numbers` step fails the build on untraceable numbers. Three-engine SHACL parity (pyshacl / shacl-engine / rdf-validate-shacl) on every shipped shape.

## 10. Privacy and publication gates
Preview first, then the public page. A leak sweep runs before every publish against the owner's private list. Exhibits about the Consortium ontology's modelling (multi-domain pooling, RDFS type explosion) are presented as the lab's own reproducible measurements on the public Turtle, never as a critique. Web3D example files are BSD-style: keep the licence notice; never host paywalled PDFs (link DOIs).
