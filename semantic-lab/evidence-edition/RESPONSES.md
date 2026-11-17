# Evidence Edition: what was adopted, re-checked and built (17 Nov 2026)

The Evidence Edition is an audit and extension of the Semantic Twin Lab, contributed by the project owner on 16 Nov 2026. This file records how each of its points was handled. Evidence states:

- **re-run here:** recomputed in this session.
- **as recorded:** taken from the edition's own records.
- **built:** new code, with tests.

## Its claims, re-checked

| Claim | How checked | Result |
|---|---|---|
| 117 Node tests and 32 Python tests pass | Ran `node --test tests/*.js` and `python3 -m unittest` on the package | re-run here: 117/117 and 32/32 |
| The 58 manifest files match their digests; 7 source hashes differ from the published copies | Recomputed SHA-256 of every listed file in Python | re-run here: 58 match; 7 differ, as stated |
| F5: S7 goes from 1 result to 0 under the RDFS rule subset, with no source edit | Re-measured in a second engine: pyshacl 0.40.2 with full RDFS (owlrl 7.6.2), on the same graph, slice and shapes | re-run here: without inference, 1 result (the Box under ChildrenAreChildNodesShape); with RDFS, that result is gone and **57,769 new results appear on 142 focus nodes** (57,674 ContainmentDomainShape, 95 ShapeGeometryShape). The edition's warning that inference "may satisfy one constraint while expanding the target population of others" is understated by four orders of magnitude on the full closure. |
| Pearl: plain SELECT returns `1` three times, DISTINCT once | rdflib on cabinet.ttl, path `diffuseColor/rdf:rest*/rdf:first` | re-run here: plain `1 1 1`, distinct `1` |
| The Cabinet and F6 graphs share a fingerprint while the XML differs (forward USE) | Not re-run | as recorded |

## Its proposals, and what was built

| Proposal (UPSTREAM-PLAN / STUDY-AUDIT) | Status |
|---|---|
| F05 guarded, byte-preserving attribute edit with a source witness | built: x3d_mcp `patch_x3d_attribute` (PR #24). It also re-runs the XSD and `validate_semantic` on the edited bytes, which the companion left to the pipeline. |
| F09 source locations, plus order facts the graph cannot hold | built: x3d_mcp `source_witness_audit` (PR #24) |
| Keep the asserted and derived graphs separate, and compare per check rather than totals | built: x3d_mcp `shacl_counterfactual` (PR #24), with hidden, added and unchanged buckets and a plain verdict |
| Eight station corrections (T3.1, T3.4, T4.5, T4.6/T5.7, T5.1, T5.8, T2.2/T5.6, T4.8) | adopted: lab v2 on x3d.demo applies them as overlays, so the v1 bytes and receipts keep their hashes |
| Evidence states (computed here, hash checked, recorded, explained difference, not packaged) instead of a bare "Confirmed" | adopted in lab v2 (the workbench), in this file, and for the nine twin cases: x3d_mcp `examples/semantic_twins/build/evidence.py` (PR #24) gives 238 claims one state each (162 computed here, 60 recorded, 13 explained difference, 1 hash checked, 2 not packaged, 0 mismatch), shown as badges on x3d.demo `semantic-twins/v2` (PR #44). The C/L/S grades on domain facts stay; they grade the sources, the states grade the computation. |
| Typed RDF terms, ORDER BY kept, blank and unbound kept apart (F03, F04) | built: `sparql_scene(result_format="typed")` and ORDER BY kept (x3d_mcp PR #24). It found that the recorded MCP runs of 16 Nov had lost ORDER BY in 13 of 54 ordered answers (rows right, order wrong). A strict xfail records an rdflib 7.6.0 bug: a VALUES row whose OPTIONAL does not match is dropped. |
| Verdict contract (execution, policy and inputs as separate fields) | partly in place: `shacl_validate` already separates `ok` from `conforms`; the full contract is not built |
| RDFC-1.0 graph identity | not built; the edition's own fingerprint is labelled as not RDFC-1.0 |
| Controlled LLM comparison | designed: eval set v1 in `../eval/` (45 items, three conditions); not yet run |

## Files here

- `STUDY-AUDIT.md`, `UPSTREAM-PLAN.md` and `VALIDATION.md`: the edition's own documents, unchanged.
- `study-corrections.json`: the eight overlays.
- `Evidence-Edition-upgrade.patch`: the edition as a diff against the original lab archive.
- The runnable edition (workbench, guide, companion, tests) is x3d.demo `demos/ontology-lab/v2/` (PR #42).
