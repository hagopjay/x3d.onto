# Semantic lab: RDF, SPARQL and SHACL on X3D (Nov 2026)

This chapter collects the ontology lab work from 13 to 16 Nov 2026 and links to where each part runs.

| Part | Where it lives |
|---|---|
| Design spec of the 38-station Semantic Twin Lab | `DESIGN.md` |
| 16 issues found while LLM sessions drove the semantic tools (F-01 fixed in x3d_mcp PR #18) | `TOOL-FINDINGS.md` |
| Scenario specs, rounds 1 and 2 (nine cases) | `scenarios/` |
| Daniel Beach's ontology essay, distilled into ten ranked ideas | `ARTICLE-NOTES-beach-ontology.md` |
| Eval set (45 items, gold answers, three conditions) and the layer test | `eval/` |
| Semantic tools: `scene_to_rdf`, `sparql_scene`, `shacl_validate`, `rdf_infer` and more | hagopjay/x3d_mcp, PR #17, #18 and #20 |
| The nine cases as a runnable example (scenes, domain graphs, shapes, oracle, MCP recordings) | hagopjay/x3d_mcp `examples/semantic_twins/` (PR #21) |
| Evidence Edition: an audit of the lab with 8 station corrections, a witness workbench and a companion; how it was re-checked and adopted | `evidence-edition/` (start with `RESPONSES.md`) |
| Evidence tools: `source_witness_audit`, `patch_x3d_attribute`, `shacl_counterfactual` | hagopjay/x3d_mcp PR #24 |
| Pages | hagopjay/x3d.demo: `demos/ontology-lab/v1` and `v2` (Evidence Edition), `demos/semantic-twins/v1`, `demos/ontology-field-notes/v1` |

## Ladder

| Question | Answered by |
|---|---|
| How much? | A semantic or metrics layer |
| What is it? | An ontology: published vocabularies |
| Where is it? | The X3D scene, converted to RDF |
| Is it allowed? | SHACL over the scene and the records together |

## Measured (Confirmed; the cases and faults are ours, so this shows lift on this data only)

| Graph used | Questions and rules answered | Planted faults caught |
|---|---|---|
| Scene alone | 0 of 36 | not measured |
| Domain records alone | 27 of 36 | 5 of 18 |
| Scene plus records | 36 of 36 | 18 of 18 |

Measured with rdflib and pyshacl over the x3d_mcp converter.

## Next

- Run the eval set on a model: scene only, raw records, and ontology through MCP.
- Store grades and record dates as data: `twin:grade` and `prov:generatedAtTime` on every fact, plus a shape that warns when an answer rests on a Suspected fact.
- Draft and certify: an LLM drafts a domain graph from a bare scene, and the oracle and the shapes accept or reject each triple.
