# Break the Loom — additions for review

No existing GitHub repository was read, edited, committed or published. The GitHub integration is disabled by the workspace administrator. These additions have no claimed compatibility with an unseen checkout.

`break-loom-additions.patch` adds a new `tools/break_loom/` directory containing standard-library detectors, recipes, generation functions and a paired smoke test. The standalone gate kit contains the same files. Rendering and XSD witnesses remain in the full application bundle.

```sh
git apply --check /path/to/break-loom-additions.patch
git apply /path/to/break-loom-additions.patch
python tools/break_loom/smoke.py
python -O tools/break_loom/smoke.py
```

The patch is checked and smoke-tested in an empty temporary repository. Before using it elsewhere, check paths, run that repository's corpus, and review the source. No existing acceptance profile is weakened or replaced.

| Candidate destination | Addition | Boundary |
|---|---|---|
| x3d.onto | Minimal traps, scoped intent contracts, paired controls and clear-cell candidate records | Runtime-specific facts must remain labelled by runtime |
| x3d_mcp fork | Review the order-aware ROUTE specimen | Do not present this local checker as the fork or a complete semantic validator |
| x3d.ML | Receipt subject binding, exact report hashes, corpus result ingestion | No signatures or authenticated origin claimed |
| Shared acceptance code | Required coverage, controls, named diagnostics, candidate binding, optimized-Python tests | A reported pass without its conditions is rejected |

The twelve rule proposals are produced by `tools/matrix.py` from executed reports. Each names the negative fixture, repaired control, diagnostic, owner, scope and candidate digest. Every clear cell creates a coverage candidate. Grammar blind spots are delegated: valid syntax should stay valid.

`github-actions.yml.example` is inactive. It assumes the full application is at the checkout root; adjust the working directory before adopting it. Upstream promotion remains a separate review and publication step.
