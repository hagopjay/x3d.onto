# Ontology ideas from Daniel Beach, "What the !@#$% is Ontology?" (Data Engineering Central, 16 Nov 2026)

Distilled for the X3D Semantic Twin Lab. Visual version: x3d.demo, demos/ontology-field-notes/v1.
Grades: C = measured here, L = well sourced but not checked here, S = the article's claim, not checked.

## Definition (article)
An ontology is a machine-readable model of the concepts in a domain, their relationships and, when needed, the rules governing them.

## Question ladder (article's two rungs, plus our two)
1. How much? Answered by a semantic or metrics layer.
2. What is it? Answered by an ontology (the article's distinction, "at least for now").
3. Where is it? Answered by the X3D scene (ours).
4. Is it allowed? Answered by SHACL over the scene and the records (ours).

## Ontology-specific ideas, ranked by usefulness to x3d
1. Evals or it didn't happen: does an agent with an ontology beat a good agent with a semantic layer? Built here: eval-set-v1.json, 45 items, three conditions (A scene only, B raw records, C ontology through MCP). Not yet run against a model.
2. Layer lift (C, measured on our own planted cases, so biased toward our stack):
   - Questions and rules: the scene alone answers 0 of 36, the records alone 27 of 36, both together 36 of 36.
   - Planted faults: the records alone catch 5 of 18, the scene plus records catch 18 of 18.
   - Fire code subtlety: "Exit stair B locked" is a record fault, but only geometry shows which rooms become too far from an open exit.
3. OntoRank signals (Genie Ontology, S): authority, relevance, certification, popularity, recency. Maps onto our C/L/S grades. Proposal: give every record a twin:grade and prov:generatedAtTime, plus a shape that warns when an answer rests on a Suspected fact.
4. The machine drafts and a person certifies (NVIDIA auto-ontology, Genie; S). This is our flywheel step: an LLM drafts a domain graph from a bare scene, and the oracle and shapes accept or reject each triple.
5. Every answer shows its working (auto-ontology returns its SQL; S). This is our tether: SPARQL, rows, and the failing shape.
6. Format vs engine (a semantic-layer spec vs auto-ontology): bet on the files (X3D, Turtle); x3d_mcp is one engine of several.
7. Multimodal gap: auto-ontology does not read PDFs (S). 3D geometry is another unread modality, and it is our niche.
8. Weight: COA and auto-ontology need standing infrastructure (S). Our stack is text files plus one stdio process.
9. Expected "ontology war", like the catalog war (Unity, Polaris, Nessie): stand on W3C and ISO standards.
10. Context problem: "customer" means different things in different departments. Our "room" is a BOT space, a Brick zone and an IBC occupant-load area at once.

## Terms (added to the field guide)
- Semantic layer: governed formulas for metrics.
- Context layer: the vendor word for whatever gets fed to agents.
- OntoRank: a trust ranking.
- Genie Ontology: Databricks.
- auto-ontology: NVIDIA, open source, SQL only. Its core units are Term, SQL attribute and Relationship.
- COA: AWS context-ontology-accelerator; heavy, reads documents.

## Files
- ontology-lab/eval/eval-set-v1.json
- ontology-lab/eval/layers-2026-11-16.json
- ontology-lab/eval/layers.py and layers2.py
- ontology-lab/scenarios/scenarios-v2-2026-11-16.tgz
