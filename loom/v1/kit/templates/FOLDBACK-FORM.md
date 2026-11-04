# Fold-back: <tools/name> from <project> <version>

The PR body for a fold-back patch: what the Loom taught this project, returned as a small rule with its counterexample. The shape is common to the five project patches (LEARNINGS-from-patches.md §2). Check the patch with:

```sh
kit/loom foldback <project-root> --evidence <run>/evidence --patch <project>/integration/<name>.patch
```

## Summary
<One paragraph: the failure, the rule, its scope.>

## Apply and test (from the target repository root)
```sh
git apply --check <name>.patch
git apply <name>.patch
python3 tools/<name>/smoke.py
python3 -O tools/<name>/smoke.py
```
Tested in an empty temporary git repository. Compatibility with <target repo @ commit> is <tested | not tested>.

## What it adds (additions only)
| File | Role |
|---|---|
| tools/<name>/README.md | This text |
| tools/<name>/<module>.py | Production predicates (fail-closed, stable codes; no assert) |
| tools/<name>/fixtures/… | Minimal passing and failing fixtures (label synthetic ones) |
| tools/<name>/smoke.py | Runs positives and negatives; raises SURVIVING_CONTROL if a negative passes; pinned control count |

## Rules proposed
| Gate | Evidence consumed | Deliberate rejection (diagnostic) | Boundary (blind spots, tolerance, runtime) |
|---|---|---|---|

## Incident that paid for it
- Symptom: <…>  Cause (as far as isolated): <…>  Grade: <C/L/S>
- Minimal reproducer: <path, sha256>
- Repaired control: <path, sha256>

## Destinations
| Piece | Destination | Why there |
|---|---|---|
| Fact | x3d.onto FACTS.md §<…> | Graded finding with instrument |
| Trap rule | x3d.onto loom_gate.py | A trap the validator passes |
| Semantic check | x3d_mcp fork | Only if a minimal example shows a standard-level invariant |
| Lineage | x3d.ML | Receipt or provenance shape |
| Release rule | Shared acceptance code | Required coverage, candidate binding |
| Stays local | — | Creative or project-specific |

## Before promotion
- [ ] Profile trigger, units, tolerance, severity and budget chosen
- [ ] Target repository's family corpus re-run; false positives reviewed
- [ ] Tool versions recorded with the fact
- [ ] Not CI-activated, not pushed, not sent: waits for "send"
