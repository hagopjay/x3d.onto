# Gate checklist

Use it twice: at kickoff, to choose the profile and thresholds, and before release, to tick what really ran. Every row names its source in LOOM-v1.md or LEARNINGS-from-patches.md. Tick a box only when a witness record with status `pass` and grade C exists for the current candidate.

## A. Acceptance infrastructure (every project)
- [ ] Candidate inventory covers runtime, generators, **test code**, sources, docs and vendored runtime; it excludes evidence, caches, VCS and archives (R1)
- [ ] Every required witness record names the current candidate sha256; `loom accept` passes (R1, R4)
- [ ] Records written while the candidate changed were refused and rerun (R2)
- [ ] All gate predicates raise; the gate suite passes under `python` **and** `python -O`; any dependency that needs asserts makes the app refuse `-O` (R3)
- [ ] Every negative control fails with its intended diagnostic; none survives (R6)
- [ ] Coverage fields required by the profile are present (R7); no development or preview record counts (R8)
- [ ] Evidence files are hashed in their records and verified at acceptance (R9)
- [ ] Unrun witnesses appear in the receipt with reasons (R11); the receipt chains to its predecessor and was not overwritten (R12)

## B. File witnesses (cheap, first)
- [ ] Grammar: XSD for the declared version on the **pinned** fork; 0 errors
- [ ] Meaning: fork semantic checks; 0 errors; warnings listed
- [ ] Traps: family gate or loomkit subset; 0 error hits; warnings reviewed (shader prefix, ROUTE order, colour range, emissive white, splat bbox, MovieTexture still, version vs nodes, Script under host, metadata containerField, GLSL `active`)
- [ ] Receipts: a full regeneration is byte-identical; a rebuild with the clock moved changes nothing (law 4; BREAK)

## C. Runtime witnesses (browser, then person)
- [ ] Behaviour: pinned X_ITE loads; every ComposedShader `isValid`; console clean, with any allowlisted warning named exactly; every ROUTE fires (R14)
- [ ] Asset preflight: every required asset's bytes and sha256 are verified before scene creation; a corrupted asset stops startup (LOOM §8 #21)
- [ ] Runtime reads: metadata attached on the live node; loaded coordinates match emitted ones (R14; GEAR)
- [ ] Host: strict policy copy; 0 external requests; fonts and wasm as the policy allows
- [ ] Eyes: fixed-time frames, UI and overlays excluded, unchanged-twice control, then the effect check; nonblank thresholds; frames hashed (R15; LS2 §4)
- [ ] Picture review: `loom picture` validates (flags only, bound to the frame hashes) (R10)
- [ ] His look: recorded as a decision, with scope and version

## D. Contracts that need probes (when the project has them)
- [ ] Coordinate spaces declared (local vs world; Z-up vs Y-up done exactly once) (R16)
- [ ] Sampler domains: GPU texel probes at declared coordinates; wrap and clamp modes explicit; no mips on data maps (R16)
- [ ] Texture ownership: one DEF owner with USE references (R16)
- [ ] Topology: shared indices, outward winding, vertex links; a reversed-face control (R16)
- [ ] Clocks: the audio or page clock owns time; rAF, display, CPU and GPU kept apart; unknown is null (R17)
- [ ] Measurements cancel and erase on any condition change (R18)
- [ ] Camera: cuts declared on the director card; motion within shots sampled against bounds; handoff transfers pose **and** lens
- [ ] Rate **and** phase checked wherever alignment matters (GEAR)
- [ ] Unknown is not zero, end to end (R19)

## E. Truth, budget, safety
- [ ] Truth: content matches its named source (edition, dataset, IFC); identity matched, not counts (BREAK)
- [ ] People: no invented person, face or date; AI portraits labelled "after <work>"; silhouettes for the rest (law 10)
- [ ] Budget: under the cap; duplicate-key and over-cap checked separately (BREAK); paid calls cached by prompt hash (law 11)
- [ ] Ear (music): loudness, true peak and onsets against the profile's numbers, stem named
- [ ] Flash: a named flash-analysis method; calm mode is not a pass
- [ ] Fps: real GPU named, full uninterrupted run; or explicitly `not_run`

## F. Fold-back
- [ ] FACTS entry written for each new trap
- [ ] Fold-back patch: additions-only `tools/<name>/`, README, smoke with counted negative controls; `loom foldback` passes (R13)
- [ ] Destinations table filled; runtime facts labelled by runtime; nothing sent without "send" (R21; law 16)
