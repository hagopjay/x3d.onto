# DRAFT, HELD. Not sent to anyone. For Hagop to edit, then decide.

Status 2026-10-21. Written by an AI-assisted session. Nothing in this file has been shared with Jakub Flotyński, Don Brutzman or the Consortium. Numbers are Confirmed (computed, scripts in `harness/`) unless marked L (a reading). Decide before sending: how to disclose the AI-assisted tooling, whether to attach data, and whether Brutzman is copied (he co-created the stylesheet).

---

## 1. Short cover note (draft)

> Subject: a question about per-parent ranges in the X3D Ontology 4.1 Turtle
>
> Dear Jakub,
>
> While measuring how well the X3D Ontology agrees with the XSD (for an MCP server that exposes it to agents), I found that the ranges the stylesheet intends per parent seem to get pooled when the Turtle is loaded: `:hasChildren` ends up with 49 `rdfs:domain` and many `rdfs:range` triples, so a query that pairs domain with range predicts about twice as many legal placements as the XSD accepts. X3DUOM's `acceptableNodeTypes` already holds the narrow answer and agrees with the XSD on 93.2% of the pairs I compared. I may be missing a design reason for the shared property names, so I would like to ask before suggesting anything. A two-page note with the numbers and a small additive sketch is attached. Nothing here needs a quick answer.
>
> [sender]

## 2. Note

### 2.1 What was looked at
| item | detail |
|---|---|
| X3D Ontology 4.1 Turtle | `X3dOntology4.1.ttl`, 1,170,960 bytes, SHA-1 1b5d645a80917ebfd35d3088bad4affa4c73bea2 (matches the manifest of the mirror listing); 18,121 triples, 364 classes |
| stylesheet | `X3duomToX3dOntology.xslt`, SVN HEAD via the SourceForge mirror, 1,220 lines, 67,046 bytes, SHA-1 f443c05f480795a5b3d71a01d0839bf20d105f80; **read in full** |
| X3DUOM | 4.1, "Generated 2026-06-21", as bundled in x3d_mcp |
| schema | X3D 4.1 XSD, via the `validate_xml` of x3d_mcp (checkout `fa0b389`) |
| method | the placement test of x3d_mcp's `evaluation/cross_validate_ontology.py`: a minimal document puts child under parent (with the field as containerField); accepted / rejected (error names the child) / inconclusive (the harness could not place the parent) |

### 2.2 Observation (mechanism)
The stylesheet emits, for each node's own SFNode/MFNode field, a property with **one** `rdfs:domain` (that node) and a range from that field's `@acceptableNodeTypes` (a single IRI, or an anonymous `owl:unionOf` list): lines 949-1030. Inherited fields come through the abstract-type branch with a domain list of the abstract type plus its inheritors (lines 755-784, with a comment that `owl:unionOf` is avoided for `rdfs:domain` on purpose). Property names depend only on the field name (`has` + field name, line 917-918), so every parent that declares `children` emits the same subject `:hasChildren`. In Turtle those triples merge.

Measured on the 4.1 file (`harness/xslt_diagnosis.py`): 125 properties under `:hasChild`; 48 of them have more than one `rdfs:domain`; `:hasChildren` has **49** domains and 7 IRI ranges plus 17 anonymous unions covering 30 distinct types. The per-parent pairing (Gain with its audio nodes) is no longer in the graph, only the pooled sets. (L: under strict RDFS semantics several `rdfs:domain` values are conjunctive; I read the stylesheet comment as a documentation-driven choice rather than a modelling claim, and may be wrong.)

### 2.3 Evidence
Containment fields only (initializeOnly / inputOutput), concrete parents and children; the 1,897 event-port pairs (addChildren, removeChildren and similar) and the 1,584 `metadata`/`IS` pairs are left out and reported below.

| | pairs | XSD accepts | rejects | inconclusive |
|---|---|---|---|---|
| ontology as the tool reads it (IRI ranges × domains) | 7,604 | 3,548 | 3,504 | 552 |
| event ports (left out) | 1,897 | 410 | 1,066 | 421 |
| `metadata` / `IS` (left out) | 1,584 | 1,248 | 0 | 336 |

- Accepted share of conclusive pairs: **50.3%** (3,548 of 7,052). The doc's own 10-type slice gives 47.9%, and that whole 10-type table is reproduced row by row.
- X3DUOM's `acceptableNodeTypes` (child or any of its ontology ancestors in the list) against the XSD on the same pairs: allow/accept 3,512; allow/reject 441; deny/accept 36; deny/reject 3,062. **Agreement 93.2%** of 7,051 comparable pairs; of the pairs it allows, 88.8% are accepted. The 441 allow/reject residue is not adjudicated (on the all-pairs run, 202 of the 643 such pairs were containerField-enumeration rejections).
- The other direction: the UOM universe is 4,907 containment pairs. The ontology as read predicts 4,455 of them (90.8%); the other 452 are XSD-accepted for 113, rejected for 322, inconclusive for 17. Of the 3,625 pairs that are UOM-allowed and XSD-accepted, the ontology predicts 3,512 (96.9%).
- So a prediction set built from the UOM lists has 4,907 pairs instead of 7,604 (35.5% fewer), keeps 96.9% of the legal ones, and is accepted by the XSD on 82.6% of its conclusive pairs (3,625 of 4,388) against 50.3%.

What the tool reads is not the whole file: x3d_mcp's `node_parents` takes only IRI ranges and ignores a bare `X3DNode` range and anonymous unions (its comment says they would admit every node). The numbers above describe that reading. Other consumers may read the file differently.

### 2.4 Options (smallest change first)
**A. Additive restriction axioms (sketch built and checked).** Leave every existing triple alone and add, per concrete parent and field, one axiom:
```turtle
:Gain rdfs:subClassOf [ a owl:Restriction ; owl:onProperty :hasChildren ;
    owl:allValuesFrom [ a owl:Class ; owl:unionOf ( :Analyser :AudioClip ... ) ] ] .
```
The sketch generated from X3DUOM 4.1 has 310 axioms and 2,088 triples (`proposal/X3dOntology4.1.narrowing-sketch.ttl`), parses as Turtle, resolves every term in the 4.1 file, and `proposal/narrowed_node_parents.rq` run over base + sketch returns exactly the 4,907 UOM-universe pairs in 0.5 s (`out/proposal_check.json`). It is a consistency check of the encoding, **not** a reasoner or Protégé run, and I did not run a patched stylesheet.

**B. Per-parent sub-properties.** Emit `:has<Field>` as a general property without domain/range and a per-parent sub-property carrying that parent's domain and range, along the lines of the `fieldXHasParentY` inverses already in lines 1114-1139 (there the parent name is dropped for `children`, line 1119). Cleaner for pairing, but it changes the property graph consumers query today.

**C. Closed-world companion (SHACL).** One shape per (parent, field) from the same UOM data, so that the ontology proposes and shapes dispose. Needs the property path the scene converter (`X3dToTurtle.xslt`) emits for each child field, which differs from the class-level `hasChildren` (at HEAD it emits per-type properties such as `hasShape`; observed on the Altar example earlier). Not built.

My leaning (L): A first, because it is additive and costs existing queries nothing, then C once the converter's property paths are fixed. B only if you prefer to change the property structure.

### 2.5 Questions
1. Is sharing the property IRI across parents intended, for example for readable documentation in Protégé? Is the pooled domain/range meant to be read as a union?
2. Which consumers rely on the current shape (the `.rq` examples, Protégé views, the Examples Archive builds)?
3. Would restriction axioms, a companion shapes file, or neither fit the working group's plans for 4.1 before it is final? Will the 4.1 IRIs stay stable?
4. For the 441 pairs where the UOM list allows a placement the XSD rejects (Layer, LayoutLayer, GeoLOD, Collision and the pick sensors lead): is that the XSD being stricter, the UOM list being wide, or a placement my harness cannot express?
5. Is a smoke-test set useful for the build (the tests listed under "Reproduce", for example the 10-type table as assertions)?

### 2.6 Limits, said plainly
- The XSD is a proxy for the specification; the Schematron rules were not run. 552 containment pairs are inconclusive (the harness could not place the parent), mostly LayoutGroup, GeoLOD and Viewport contexts.
- The sample is the pairs the ontology predicts plus the UOM universe, one placement each. It is not every possible pair and not a conformance test of the schema.
- 4.1 is the draft dated 29 September 2026. I have not read the November 2025 Visioning Lab slides.
- Option A is a sketch. I did not run a reasoner, Protégé or a patched stylesheet (Saxon was not installed here).
- I make no claim about intent. Nothing here is a bug report against the Consortium.

### 2.7 Reproduce
In `harness/` (all read-only on the x3d_mcp checkout; run with its `.venv` python): `build.py`, `xcheck_all.py`, `uom_ranges.py`, `uom_universe.py`, `proposal_numbers.py`, `xslt_diagnosis.py`, `proposal_sketch.py`, `test_harness41.py`. Data: `data/xcheck_all.json` (11,085 verdicts), `data/proposal_numbers.json`, `data/xslt_diagnosis.json`.

---

## 3. For the sender, before anything leaves
- The explorer is local (`localhost`); it cannot be shared as is. A static export would need the layout and sim layer reviewed (the simulated sc: layer must not be attached or described as Dr. Polys's work).
- Decide whether to attach `narrowing-sketch.ttl` and the verdict table, or offer them.
- Consider asking Brutzman's view before the working group, since the stylesheet is theirs jointly.
- Check the working group's preferred channel (list, issue tracker, or SVN) before sending.
- The coordinator's hand-over notes say everything stays private until 2027-01-01 and nothing goes to Flotyński or anyone else without your explicit go-ahead. This draft honours that; check whether the date applies to this note too.
