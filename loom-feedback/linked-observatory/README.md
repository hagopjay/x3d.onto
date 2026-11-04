# Linked Observatory · Loom foldback proposal

Status: **locally exercised; proposed for global calibration**. This is an addition-only kit. It neither replaces a global policy nor certifies the supplied research datasets. No scene geometry, private graph records, or third-party media is included.

Run `node tests/contracts.cjs`, `node tests/profiler.cjs`, and `python3 tests/predicates.py` (lxml required). The scripts expose narrow contracts with counterexamples. Keep the full browser witness from the project when adopting the frame/arrival protocol; unit tests alone cannot establish renderer timing.

| Candidate | Trigger and required witness | Necessary counterexample | Promotion condition |
| --- | --- | --- | --- |
| URL-SCOPE | A scene is decoded or embedded; resolve rendering assets relative to its own URL, then verify actual browser loads. | Valid XML with a missing scene-relative texture; the same URI valid at one base and broken at another. | Exercise URL fallback lists, Inline boundaries, redirects, caches and authorized remote assets. |
| ARRIVAL-EPOCH | Navigation changes a camera. Require the matching intent serial, an applied frame later than the intent, and a sensor pose within a declared tolerance. | Expected and observed positions both stale; superseded intent; matching serial before the new frame. | Calibrate moving targets, XR, nested transforms, orientation and scale-relative tolerances. |
| ZOOM-RANGE | Camera paths span several orders of magnitude. Use stable algebra and check finite paths, endpoint equality, reversal symmetry and cancellation continuity. | Astronomical-to-submetre widths where subtracting similar magnitudes yields log(0). | Test other curve families and very large/small positive ranges; reject invalid inputs explicitly. |
| SEMANTIC-JOIN | Two worlds link entities. Require unique canonical source identity and source-row hashes, plus scoped acknowledgements. | Duplicate labels, duplicate canonical IDs, missing entities, stale sessions and wrong-window messages. | Add namespaces, ontology versions, renames and explicit mapping migrations. Matching names alone never establish semantic truth. |
| DEPENDENCY-CLOSURE | Optional rendering features load runtime assets. Audit local URLs and observe actual HTTP/renderer load state. | An engine loads but its BRDF LUT or line-style atlas is absent. | Probe each enabled feature tier, vendor version and cold cache. Version pinning is insufficient without its supporting assets. |
| PROFILE-SCOPE | Record CPU/GPU samples. Bind device, drawing buffer, scene, settings, camera and visibility; reject changed, unobserved-camera or sparse runs. | Missing GPU extension, disjoint query, stale query epoch, unobserved camera, movement during capture, too few samples. | The local 120-interval/5-second threshold is provisional, not a universal statistical guarantee. Add repeatability and uncertainty before ranking changes. |
| CLOCK-OWNERSHIP | User pause and offscreen culling affect the same TimeSensors. One owner computes the desired pause state. | An offscreen optimization resumes an animation the user deliberately paused. | Browser-test transitions, hidden tabs, moving targets and ownership precedence. |
| CLAIM-SCOPE | Inherited grades or validation badges are displayed. Separate source assertions from current candidate measurements. | A historically green badge is carried onto modified bytes. | Calibrate wording with users; preserve original grades without silently promoting them. |

The important technique is to challenge the witness itself. A receipt may be internally consistent while observing the wrong frame. Keep a control that would have passed the old witness and fails the new one. Give every new rule an escape condition: intentional shader-expanded degeneracy is not a license to reject every degenerate face; authored reflections are not live scene reflections; an identity join is not an ontology proof.

## Integration guidance

- `src/contracts.js` is UMD and dependency-free. `appliedForIntent` only establishes event ordering; pair it with an independent camera sensor, finite-pose checks and a declared tolerance.
- `src/profiler.js` uses pinned X_ITE display callbacks and optional WebGL2 timer queries. It does not measure browser compositing, physical display latency or GPU memory. Missing measurements remain null. Dispose its callbacks and queries when replacing a renderer.
- `tools/scene_contracts.py` contains local-only policies. External assets return an explicit external status so another policy can authorize and verify them; this is not a general prohibition on remote URLs.
- Never convert a failed or missing witness into a zero-valued metric. Never promote a source's confidence label into this run's validation result.

## Eyes found a different clock

The camera sensor could be correct while an eight-frame HUD throttle still displayed an old time on a slow renderer. Explicit paused-time changes now invalidate the cadence, and a browser control compares displayed UTC to scene time. A position witness does not certify the associated interface. A compact-window card also overlapped a caption; suppressing the redundant caption made the evidence readable without changing geometry. Retain both as examples of why Eyes flags observable conflicts instead of issuing a universal beauty grade.
