# Hooks: where ontology, DSPy and evals plug in

Flywheel (per ~/Projects/x3d/work/trace-pipeline/out/flywheel/REPORT.md): **spec → agent → validating x3d_mcp → Blender + x3d-blender-io fork → runtime (X_ITE) → verdict → x3dprov tether**. Proposals below are mine (L) unless a source number is cited; nothing here has been built by this session.

## 1. Spec / grounding
- Ontology as *retrieval map* for the agent: `node_parents`, `describe_ontology_term` (answers legality questions in ms [FW]). Advisory only; 348 predicted vs 150 accepted of 313 conclusive [FACTS 3]. Gate stays XSD+semantic.
- UOM exact-lookup tests for model-written spec statements ("node N has field F of type T / parent P / component C") — seed = the 8 rows of README (29) (7/8 consistent). [FACTS 17] (S wiring in source)

## 2. Agent (prompt)
- DSPy: optimise writer prompt against the validator metric. Evidence: Full-barred prompt cuts hard-prompt failure 84% → 30% [FACTS 23]. **Metric must close escape hatches** (profile Full, roughness, castShadows) or it Goodharts [FACTS 24]. DOC §6 row 9: add use-type-mismatch / SPARQL USE check into the DSPy metric (not done).
- Few-shot / retrieved examples beat optimised prompt on Polys prompts (6% vs 30%); combo untested.

## 3. Validating x3d_mcp
- Add (on private branch): use-type-mismatch semantic check (exists, commit 29a4e98, branch public — decision pending), exact-fix hints (xmlns on root: 32 trials; Cone radius → bottomRadius: 54 scenes) [FACTS 14, 21]. Candidate: bundle 4.1 ontology (currently 4.0 only) [DOC Q6].
- SHACL/Schematron layer = rung 4 "Lawful"; rules mined from the 3,058 spine scenes (OntoGuard pattern) to tighten the over-permissive ontology [DOC §6 rows 8, 11]. All unbuilt.

## 4. Blender + x3d-blender-io fork
- Round-trip as eval: x3dprov survived 6/6 (DOC) and 7/7 (FW); verdict unchanged. Run the same USE/containment checks after export. Fork findings F1 (FONT tessellation >100 s for 63 labels), F2 (306 KB → 1.6 MB), F4 (one mesh per USE, loses instancing), F5 (277-287 unused-def infos) [FW] touch DEF/USE semantics and so the ontology USE checks.
- Open-work item 6 (triples for other 3D formats, t3dmo.ttl) = Blender bridge table as raw material (S) [REF].

## 5. Runtime (X_ITE) and evals
- Visible: frame check; 203/1,058 valid draw nothing [FACTS 26]. Complete: contact-sheet judge (kappa 0.82; 97% right / 73% names real error) — keep an independent exact run as the gate.
- Parts/contact (strict vs loose) as an eval for relations no schema states [FACTS 25]; candidate `sc:` relations (attached, support). Polys 2024 prompt set rerun is the repeatable baseline (29.4% schema failure, ledger.jsonl, SHA256SUMS in the Drive export).
- Eval hygiene rules from DOC §7: name validator behind every number; both sides of a check (false alarms + injected faults); state extraction rule.

## 6. Verdict → tether (x3dprov)
- Record per step: op, hash, validator version (eb4b4b4/fa0b389), X_ITE version, ontology file+version, grades. Export to PROV-JSON/OpenLineage exists (`export_prov.py`) [FW]; PROV-O mapping is open Q7 [H21, DOC]. Limit: flipping last step still verifies → sign (x3dprov 0.2) [FW].
- Ontology/shape version and SPARQL query text belong in the step record so verdicts are reproducible.

## 7. Shroud evidence ledgers (EVIDENCE.md: 136 rows, v1 16 Oct; REPORT.md v3)
Existing row schema: `id | claim | value (with unit) | uncertainty/interval | primary source | second witness/counter | grade | source year`; grades Confirmed 27 / Likely 53 / Contested 30 / Suspected 22 / Question 4 (REPORT.md); verification S/UNVERIFIED/opened (92 opened, 24 S, 17 S?, 3 U after v2); rows appended as dated sections, never edited.
Plug-ins (proposal, L):
- **Epistemic tag per row** from the ladder: which rung produced it (0-3 exact; 4 lawful; 5 visible; 6 complete; 7 meaningful) and whether *lookup* (UOM/XSD/XML), *instrument* (X_ITE, frame check), *judge* (model, kappa) or *record* (provenance).
- Ontology use: row ids as individuals (`DEF` names like P50 already appear in the 195-feature scene's MetadataSet: position_status measured/estimated/geometric/question), query "all Contested rows touching feature X" via SPARQL; closed-world checks (every Confirmed row has primary source + uncertainty) as SHACL — not shipped.
- Keep the C/L/S ↔ Confirmed/Likely/Suspected mapping explicit; ledger's Contested/Question have no C/L/S counterpart. Never upgrade a grade in translation.
- DSPy/judge on ledgers: judges may flag, not grade; grade moves stay recorded (as REPORT.md logs "Likely→Confirmed 11" etc.).

## 7b. Constraints confirmed by gemini-eval (2026-10-21)
Model outputs enter any ledger view only as candidates graded Suspected, labelled as generated, never as rows; ontology tags (rung, lookup/instrument/judge/record) are added on the ontology side and must not edit `corpus/` or EVIDENCE.md.
