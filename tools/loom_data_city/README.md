# Reusable Data City gate additions

No GitHub repository was changed. The GitHub integration is disabled by the workspace administrator, and no target checkout was available. The supplied patch adds a self-contained directory only; it was checked against an empty temporary Git repository, not against your current repositories.

## Local review and application

The standalone `Data-City-Gate-Kit.zip` contains the exact standard-library gate code, a four-row fixture, emitted manifest and X3D, and a smoke test. The same files are represented by `data-city-gates.patch` under `tools/loom_data_city/`.

```sh
git apply --check /path/to/data-city-gates.patch
git apply /path/to/data-city-gates.patch
python tools/loom_data_city/smoke.py
```

Review the new files before committing. These commands are instructions for your chosen checkout, not actions performed in this delivery. The patch does not modify an existing gate, workflow, manifest or registry, and does not install a global acceptance profile automatically.

The full application also exposes:

```sh
python -m citycore.cli source.csv manifest.json --scene world.x3d
```

Exit 0 means the named checks passed. Exit 1 is a candidate contract violation with a stable diagnostic. Exit 2 is an instrument or input error. Running under `python -O` retains enforcement.

## Proposed integration boundaries

| Destination named in the supplied Loom definition | Proposed addition | Keep separate |
|---|---|---|
| `x3d.onto` | Data-family facts, null semantics, row/glyph correspondence and two-sided fixtures | User-specific visual taste |
| `x3d.ML` | Source/row/glyph/run lineage adapter and receipt ingestion | Integrity versus authenticated origin |
| Runtime witness adapters | Checksum ID pass, actual picking, pixel ablation and offline host checks | Data parsing and standard-level semantics |
| Common release infrastructure | Required coverage and exact subject/test-code binding | Repo-specific path assumptions |

The exact current layouts and APIs of those repositories were not inspected. Adapt paths and record shapes on a branch, run the existing family corpus, and preserve both valid and invalid cases before promotion. A browser-specific fact should not become an arbitrary X3D syntax prohibition.

## Useful new diagnostics

`SOURCE_HASH`, `ROW_RANGE`, `ROW_RANGE_CONTENT`, `ROW_HASH`, `ROW_BIJECTION`, `UNKNOWN_COERCION`, `INVALID_COERCION`, `VALUE_TRUTH`, `UNKNOWN_GEOMETRY`, `HEIGHT_TRUTH`, `SIGN_TRUTH`, `SCALE_TRUTH`, `DIMENSION_TRUTH`, `PARTIAL_TOTAL`, `AGGREGATE_LINEAGE`, `SCENE_LINEAGE`, `SCENE_HEIGHT`, `STALE_WITNESS`, `MISSING_BROWSER_COVERAGE`.

The first flywheel proposal should be narrow: a valid measured zero must pass, a missing value converted to zero must fail, and an all-unknown group must retain a null sum. Then extend coverage to emitted geometry and framebuffer identity.

`github-actions.yml.example` is an optional workflow template for a checkout whose Data City project is at the repository root. Adjust the working directory for another layout. It is not activated or published by this bundle.
