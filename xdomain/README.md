# Cross-domain prototypes: the x3d_mcp validator pattern for URDF and glTF (built 2026-10-21)

One MCP server (`xdomain_server.py`, 7 tools: describe, validate and repair per domain, record_step, verify_chain), two domains, one report shape (`kit.py`: rule, severity, ladder rung, location, fix hint, X3D counterpart). Rebuild and test: `xdomain/run_all.sh`. 10 checks pass in `test_xdomain.py`.

| | URDF (robotics) | glTF 2.0 |
|---|---|---|
| oracle | `urdf/urdf_check.py`, 17 rules written by me from the URDF spec and ROS conventions: **grade L, not validated against urdfdom or MuJoCo** | official **Khronos glTF-Validator** 2.0.0-dev.3.10 (Apache-2.0; npm, 383 KB, installed with your OK, scripts disabled) |
| corpus | 6 valid robots (arm, gripper arm, rover, humanoid tree, 6-link chain, quadruped), inertia from solid-cylinder formulas | 6 valid models (triangle, cube, hierarchy, PBR, textured, animated), built in Python, 0 issues of any severity from the validator |
| injected faults | 24 operators, 135 mutants | 25 operators, 123 mutants |
| result | caught: parse 6, structure 36, semantics 81, warning-only 6, contact 6; 0 missed (**by construction**: the faults were written against my own rules) | Khronos error-level on **106 of 123 (86.2%)**; a naive structural baseline on 18 (14.6%); warning-or-info only on 17 |
| repair | 17 of 17 applicable mutants end clean; no-op on clean models | 19 of 19 applicable mutants end clean (re-validated by Khronos); no-op on clean documents; dangling references are deliberately not removed |
| latency | 0.7 ms mean in-process (max 7.6) | 1.9 ms mean in-process (max 16.0); **93 ms median per MCP call** because node is spawned per call (a warm process would remove this) |

## What it says
1. **The pattern ports in a day.** Located diagnostics, a ladder rung, a fix hint, a deterministic repair that invents nothing, and a hash-chained record fit both domains unchanged. Same shapes as `validate_x3d`, `validate_semantic`, `repair_x3d` and x3dprov.
2. **Oracle severity is not gate policy (glTF, C).** Khronos reports a required-but-unsupported extension (G18, 6 of 6) and a primitive without POSITION (G23, 5 of 5) as warnings. A gate that counts errors would pass both. The server's `strict` policy promotes them; `out/xdomain_mcp_run.json` shows the same document passing with 1 error upstream and failing with 2 under the gate. Same lesson as the X3D finding that XSD-valid is not semantic-clean.
3. **Valid is not placed (URDF, rung 6).** A joint attached 1 m from its parent passes every structural and semantic rule; only the contact rule (U-16, a one-axis version of the parts-and-contact check) sees it. Same gap as "15 of 34 resting on the sphere".
4. **Shared rules.** URDF mass-above-zero, tree and body-in-one-structure rules are the siblings of X3D's physics-mass, body-outside-collection and joint-target checks (the fork's X-09/X-10).
5. **The tether works the same.** Chain over validate, repair, revalidate: edit after the last step gives `stale`, a forged step or a deleted step gives `broken-chain`. It is a sketch of x3dprov, unsigned (the X3D flywheel REPORT notes flipping the last step still verifies; this sketch has the same limit).

## What it does not say
- No model was called: nothing here measures how often an agent produces these faults or how fast report-driven repair converges. That needs model access (spend; not used).
- URDF detection is circular by construction. Its value is the pipeline and the measured gap categories, not the 100%. An independent oracle (urdfdom's `check_urdf` or MuJoCo's compiler) is the next step and would turn L to C.
- The glTF baseline is deliberately minimal (JSON parses, `asset.version`, arrays are arrays), not a JSON-Schema validation. The 14.6% says little beyond "format-level checks miss most semantic faults".
- USD was named in the earlier option and is not done: it needs `pxr`/`usdchecker`.
- Fault sets are mine. Real generator errors will differ.

## Model-driven evaluation (planned, not run)
`eval-plan/PLAN.md`: pre-registered design (4 arms: first try, two examples, report loop, blind-retry control, plus a free deterministic-repair post-step), 20+20 prompts with mechanical completeness checks, cost model (`plan_cost.py`), and a stub pipeline that already runs end to end. `runner.py --real` refuses to run without `GO.json`. Expected cost of the lean run with a flash-class model: about $3.4 (upper bound $6.9). No spend has happened.
