# Loomsong IV — fidelity rules for the global Loom

This is an additions-only proposal under `tools/loom_fidelity_v4/`. It changes no existing validator or policy. The patch includes the production predicates and two pinned generated numeric fixtures. The smoke test executes both positive and deliberately invalid cases.

```sh
git apply --check loom-fidelity-v4.patch
git apply loom-fidelity-v4.patch
python3 -m pip install -r tools/loom_fidelity_v4/requirements.txt
python3 tools/loom_fidelity_v4/smoke.py
python3 -O tools/loom_fidelity_v4/smoke.py
```

| Implemented predicate | Lesson | Bound |
|---|---|---|
| bake_binding | Correct texture, wrong scene is still wrong | Declared digest set; unsigned |
| atlas_layout | Roughness layers are data, not an ordinary image | Six RGBM16 levels with exact gutters |
| brdf_table | A plausible gradient is not a BRDF integral | 25 scalar references, fixed quadrature and tolerance |
| texture_contract | Repeated URLs do not declare shared resource ownership | One DEF owner, USE references, packed maps without mip blending |
| camera_handoff | Control changes must transfer lens as well as pose | Position, target and FOV continuity |
| profile_contract | Missing measurement must remain unknown | Nulls, sample counts and quantile order |

The full demo also executes GPU sampler probes, corrupted-asset startup refusal, rendered ablations, the profiler's disjoint/epoch controls, actual camera observations and benchmark invalidation. Those need the X_ITE browser and are not replaced by this small kit.

The in-memory texture graph and profile/binding fixtures are explicitly synthetic. They exercise the real predicates without claiming a renderer or hardware run. The two PNGs are real generated numerical data from the project, not screenshots.

A suitable opt-in CI job installs the two pinned dependencies and runs `smoke.py` normally and with `-O`. No workflow is activated automatically. Integrating a predicate into the family gate requires choosing its trigger, severity and applicable asset profile, then rerunning the family's existing corpus.

Observed incidents should travel with the rules: missing textures despite compiled shaders, inverted sampler coordinates, repeated texture allocation, and camera-dependent ablations. The complete account is `TECHNICAL-V4.md` in the full project. Models raise suspected visual issues; this kit does not turn model prose into a numeric grade.

The patch was applied and tested in an empty temporary repository. Compatibility with an unseen existing repository, a global merge, graph ingestion or upstream acceptance is not claimed.
