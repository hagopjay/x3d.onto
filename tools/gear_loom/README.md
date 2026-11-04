# Gear Loom — reusable gate additions

This kit contains actual geometry, graph and frame-clock witnesses, a small fixture, negative controls and an additions-only Git patch. No existing repository has been changed. GitHub access was unavailable in the authoring session.

Apply from your chosen repository root after reviewing the patch:

```sh
git apply --check gear-loom-additions.patch
git apply gear-loom-additions.patch
python3 tools/gear_loom/smoke.py
python3 -O tools/gear_loom/smoke.py
```

The smoke test uses only Python's standard library. It checks a closed, oriented genus-one mesh, declared train adjacency, frame-clock ratios and phase, with paired defects. The full clearance certificate additionally requires Shapely and NumPy and the complete demo's meshes. The smoke test does not certify arbitrary meshes or a browser renderer.

The patch creates only `tools/gear_loom/…`. It intentionally leaves workflow activation to the repository owner: copy `ci-template.yml` to `.github/workflows/gear-loom.yml` to enable it. The patch was applied and smoke-tested in an empty temporary Git repository, normally and with `python -O`. Compatibility with an unseen existing repository was not tested.

Candidate global rules:

| Gate | Evidence consumed | Deliberate rejection |
|---|---|---|
| G-FRAME-CLOCK | Timestamped observed rotations | Capped elapsed time, frozen rotor, wrong speed |
| G-PHASE-CONTRACT | Tooth-weighted phase invariants | Half-pitch indexing error |
| G-MESH-CYCLE | Delivered polygons, complete interval cover | Interpenetration, unresolved interval |
| G-PAIR-COVERAGE | Every unordered tooth-body pair | Missing pair, wrong axial assumption |
| G-ADJACENCY | Typed mesh/rigid graph | Disconnected train, duplicate edge, wrong ratio |
| G-BODY-TOPOLOGY | Indexed triangles and vertex links | Open edge, winding conflict, pinched link |
| G-RENDERED-POSE | Captured marker pixels and camera model | Displaced rendered marker |
| G-OBSERVATION-WINDOW | Immutable command state during recording | Interrupted or undersampled window |
| G-RECEIPT-CLOSURE | Candidate, report and trace hashes | Stale, missing, development or failed evidence |

Promote these as scoped rules after review. Preserve their tolerances, numerical assumptions, negative controls and applicability; do not turn one certified gear family into a universal collision claim. See the full demo's `TECHNICAL.md` for derivations and limitations.
