# What the patches teach

What the other model learned while running the Loom, and what it changed and why, read from its patches and version histories and turned into reusable rules. Source IDs are defined in [SOURCES.md](SOURCES.md). Grades: C = a tool ran (named); L = read or reasoned; S = suspected.

The user's framing (3 Nov): the project zips carry GitHub-PR-style patches that explain what the Loom taught each project. That holds for five projects (C, below). Two more patches sit loose in the Drive folder.

## 1. The seven patches

| # | Patch | sha256 (first 16) | Files | What it is | `loom foldback` here |
|---|---|---|---|---|---|
| 1 | Gear-Loom `integration/gear-loom-additions.patch` (= Gear-Loom-Gate-Kit) | c40049849bbdcef0 | 8, adds `tools/gear_loom/` | Fold-back: 9 gates for mechanisms (frame clock, phase, mesh cycle, pair coverage, adjacency, body topology, rendered pose, observation window, receipt closure) | **pass**: clean apply, additions-only; smoke "3 positive contracts and 8 negative controls" normal and `-O` (C) |
| 2 | Break-The-Loom `integration/break-loom-additions.patch` (= Gate-Kit) | e0f083d5c3c01756 | 7, adds `tools/break_loom/` | Fold-back: mutant/control recipes, standard-library detectors, matrix → rule proposals | **pass**: "24 paired local specimens", normal and `-O` (C) |
| 3 | Data-City-Loom `integration/data-city-gates.patch` (= Gate-Kit) | c73e2cfceced21b8 | 9, adds `tools/loom_data_city/` | Fold-back: source-to-scene truth gate with 19 diagnostics | **pass**: "missing-to-zero rejected", normal and `-O` (C) |
| 4 | Loomsong-Cinematic-v4 `integration/loom-fidelity-v4.patch` (= v4 Foldback Kit) | ef34002adbc1ec5f | 6 (2 binary fixtures), adds `tools/loom_fidelity_v4/` | Fold-back: 6 fidelity predicates, 12 negative controls | **pass**, normal and `-O` (C) |
| 5 | Confluence-IFC-X3D-Studio `studio/integration/loom-ifc-bridge.patch` (= Confluence Foldback Kit) | fdbe8c07c9194549 | 15, adds `tools/loom_ifc_bridge_v1/` | Fold-back: IFC bridge contracts, edge-connected normals, revision reducer, world-triangle witness, fixtures, XSDs | **fail** with the studio's venv (IfcOpenShell 0.8.5, arm64): the positive control raises WORLD_TRIANGLE_MISMATCH on 2 of 111 boxes (other quad diagonal); node protocol check passes. The hash matches the debrief's published "portable Loom patch" (C) |
| 6 | `Loomsong-v3-to-v4.patch` (Drive) | c9de17a4870cecc8 | 30 | The version upgrade itself: v3 source → v4 source | Not a fold-back; read below. Only sources and generators. The projects agent confirmed it reproduces v4: sources byte-equal, rebuilt content identical, PNG bytes platform-dependent (C, [CAT]) |
| 7 | `IFC-X3D-Bridge-upgrade.patch` (Drive) | c70b151b283bad29 | 53 (52 new, 1 modified) | The upgrade from the supplied ifc2x3d v2 converter to the live studio | Not a fold-back. Hash matches the debrief's published "source upgrade patch"; reverse/forward-applies to exactly the Studio zip (C, [CAT]) |

Survey record: `runs/foldbacks-20261104/report.json`. Every patch was applied in an empty temporary repository. Compatibility with x3d.onto, the fork or x3d.ML is **not** tested: none is checked out at a target commit here, and the patches themselves say so.

Zips without a patch (C, grep over `incoming/unpacked`): Dynasty Loom, the GEDCOM Reader, Loomsong Study 01 / v2 / v3 (they carry `evidence/FACTS.md` instead), the five Loomsong media zips, MV_CUSTOM_011, WikiData.x3d, wikigrokker. The x3d_mcp Masterclass page describes PRs but holds none.

## 2. The PR shape (what every fold-back has in common)

All five fold-back patches share a shape, so v1 makes it the standard (law 20; `kit/templates/FOLDBACK-FORM.md`; checked by `kit/loom foldback`):

1. **Additions only**, one new directory `tools/<name>/`. Nothing existing is modified, no CI is activated, no policy is installed [GEAR, BREAK, CITY, LS4, IFC READMEs].
2. **A README** stating: `git apply --check`, `git apply`, `python3 tools/<name>/smoke.py`, `python3 -O tools/<name>/smoke.py`, and the boundary: "tested in an empty temporary repository; compatibility with an unseen checkout not claimed".
3. **Production predicates**, not demo code: the same fail-closed `need(value, CODE)` functions the project's release used. Fixtures are labelled synthetic where they are.
4. **Negative controls inside the smoke test.** A control that survives raises `SURVIVING_CONTROL` [LS4 gen/foldback.py], and the count of controls is pinned.
5. **A destinations table**: x3d.onto for facts and traps; the fork only for standard-level semantics; x3d.ML for lineage; shared acceptance code for release rules. Runtime facts stay labelled by runtime [BREAK; CITY].
6. **Observed incidents travel with the rule**: the minimal failing fixture and the repaired control [LS4 integration README].
7. **Built and re-checked by the project's own witness run.** In Loomsong v4, `gen/foldback.py --check-only` is one of the required witnesses, so the fold-back cannot drift from the release that produced it [LS4 run.py, contract.py `integration`].
8. **Nothing pushed.** GitHub integration was disabled or unavailable in every session, and every README says nothing was published (law 16).

## 3. The Loomsong version history (Study 01 → v2 → v3 → v4)

Each version kept its predecessor's archive and receipt, chained by hash (law 14, C).

| Version | Receipt schema; prev | What broke or was found | What changed | Why (the rule it teaches) |
|---|---|---|---|---|
| **Study 01 v1.0.0** | `loomsong.receipt/1`; prev null | F01: valid X3D, invalid GLSL (`active`). F02: the spec's melody "from memory" did not match any edition. F03: output clock vs render clock. Then the audit: **A01** the packager accepted a changed shader against a saved browser pass; **A02** under `python -O`, asserts vanished and a red Score report packaged with exit 0 [LS1 §9-10; AUD] | Renamed `sounding`; runtime `isValid`; a named public-domain edition (Mutopia 528) preserved and hashed with a separate literal fixture; one transport authority | Run the real runtime even after the XSD passes. A named source beats memory. **Witnesses must be bound to the candidate, and gates must not be asserts** |
| **Cinematic v2** | `/2`; prev = v1 receipt `3bd48f88…` | The two audit gaps; the first material pass was technically fine but looked evenly lit | `witnesses/contract.py`: a canonical sha256 inventory of runtime, generated assets, generators, **test code**, sources, docs and vendored runtime; every report records it; packaging recomputes it; explicit raising predicates; 7 cases × normal/`-O` = 14 controls with diagnostics `ACCEPT`, `LOCAL_CHECK_NOT_PASS`, `MISSING_WITNESS`, `STALE_WITNESS`, `MISSING_LOCAL_CHECK`, `WITNESS_NOT_PASS`, `FULL_PLAYBACK_REQUIRED`. Image comparisons with UI hidden and an unchanged-frame control first. Interrupted benchmarks cancelled [LS2 §2, §4] | Freshness and enforcement are infrastructure, so fix them before adding features (LS1's suggested order, followed). Separate "did it reach the renderer", "is it sound" and "is it better" |
| **Cinematic v3** | `/3`; prev = v2 receipt `90e43657…` | A preview loaded new JS with the old scene; a fixture added mid-rebuild triggered `CANDIDATE_CHANGED_DURING_WITNESS`; v2's shader treated local position as world; unshared vertices broke smoothing **after** a full acceptance run; the first note-ID decoder saw 11 future IDs | Required reports 5 → 8 (optics, motion, onsets); browser coverage flags become acceptance conditions; build-then-witness sequencing; welded topology and full re-run with the pre-weld receipt kept; overlay-free checksum ID diagnostic; stem-scoped onset witness; camera cards with declared cuts; 11 cases × 2 = 22 gate executions [LS3] | **A pass cannot make a broader, untested claim true** (the weld found after acceptance). Coverage must be an acceptance field, not a comment. Scope every tolerance to the named signal |
| **Cinematic v4** (`Loomsong-v3-to-v4.patch`) | `/4`; prev = `evidence/history/v3-receipt.json` | Shaders compiled while bake images 404'd; an atlas V convention swapped materials (all files valid); one ImageTexture per binding; an ablation inherited a close camera and saw too little floor | New `gen/radiance.py` bakes; G-ASSET-PREFLIGHT (bytes and sha256 checked before scene creation; a build marker refuses requests); 21 GPU texel probes; 7 DEF-owned shared textures; a four-clock profiler with nulls for the unknown; **picture protocol: a model judge gives located `suspected` flags, and any score is rejected**; required reports 8 → 12 (fidelity, integration, profiler, picture-protocol); `DEVELOPMENT_WITNESS` rejection; cases 11 → 20 (40 executions); `check_release.py` after extraction; the fold-back generated and checked in the run [LS4; patch diffs of contract.py, gates.py, package.py, picture.py, foldback.py] | Fidelity is a chain of correspondences, and every boundary needs its own instrument. Camera state is part of an ablation contract. **A model may locate concerns; it may not grade.** Turn misses into portable counterexamples before naming universal rules |

The shape of the history (L): each version's new gates are the previous version's incidents, and each fix ships with the negative fixture that proves it. The required set grew 5 → 8 → 12 and the gate executions 14 → 22 → 40, while the music, score and audio stayed byte-identical, re-verified each time. That is the flywheel at project scale.

Patch 6 itself: 30 files, all sources (generators, shaders, app, witnesses, docs, the embedded fold-back patch). No generated asset is in the patch; v4's 22 outputs come from re-running the generator (C, file list). The projects agent's `projects/_patches/v3patched-vs-v4.diff.txt` shows that a patched v3 differs from v4 in its generated assets and evidence until it is rebuilt. That is expected under law 1; whether a rebuild reproduces v4 byte for byte is the projects agent's check, not repeated here.

## 4. The Gate-Kits (Gear, Break, Data City)

| Kit | What it taught | Reusable rule |
|---|---|---|
| **Gear** [GEAR] | A correct equation does not establish mesh placement; a closed mesh does not establish clearance; a correct transform does not establish what the viewer saw. Phase errors survive ratio checks (half-pitch collision). A 2.5 s window was too few frames. A blanket "ignore console warnings" would have hidden the metadata bug | **Derivative truth needs state truth** (rate and phase: a correct BPM does not prove a correct downbeat). **A witness names its equivalence class** (one tooth pitch suffices only because repetition was checked). **Margins are part of the model.** **Test the observer**: displaced marker, 1% speed mutant, an induced 180 ms stall that must appear in the trace. Evidence is valid over a state interval. Report a certified bound, never a sampled minimum (0.0448 mm vs 0.150 mm) |
| **Break** [BREAK] | The loading overlay made an empty frame pass; the first CSP broke even the repaired control; a texture's URL scheme is not its final image scheme; a white emission made a loaded texture look missing; a duplicate charge hid under the cap; an immediate rebuild is a weak perturbation (move the clock 3 days instead) | **Every mutant has a repaired control, and both are schema-valid. The release needs the assigned witness's exact diagnostic. A clear cell is a coverage question for an owner.** A rule needs an intent predicate (white emission is fine without a palette contract). Identity beats count. "The suite can pass while artifacts fail": accept the experiment, not its defective specimens |
| **Data City** [CITY] | Shipping only the X_ITE loader was not enough; a test chose a non-negative ID by mistake; a HEAD 405 had a body; runtime and shader bytes were outside the receipt; Decimal rounded above 28 digits; a cancelled optional fetch | **Unknown is not zero, end to end** (null never through float or COALESCE; an all-unknown group keeps a null sum). **Four identities** (file hash, raw row hash, canonical row hash, business key) must not be conflated. Exit codes 0 / 1 / 2. Waive a failed request only by exact URL with another success; a 503 on a required shader must block |

## 5. The fold-back kits (Loomsong v4, IFC) and the IFC upgrade patch

**Loomsong v4 fidelity kit** [LS4]: `bake_binding` (the correct texture for the wrong scene is still wrong), `atlas_layout` (roughness layers are data, not an image), `brdf_table` (a plausible gradient is not a BRDF integral: 25 independent reference probes), `texture_contract` (repeated URLs do not declare one owner), `camera_handoff` (transfer the lens as well as the pose), `profile_contract` (`UNKNOWN_IS_NOT_ZERO`, `UNAVAILABLE_GPU_MEASURED`).

**IFC upgrade patch (patch 7)**: 52 new files plus a banner on the old `README_SCALE.md`: "Historical v2 experiment. These are the supplied measurements, not measurements of the new live bridge". The old converter and its results stay beside the new studio (law 14). It also records an interpretation: "IFX" in the request was read as IFC. What it teaches [IFC]:
- **One authority, derived views.** IFC bytes in SQLite are the truth; X3D is a projection. Commit ≠ acknowledgement ≠ applied frame: each boundary gets its own evidence.
- **A rejection needs a rollback boundary**: catching an error is not undoing its work (savepoint).
- **`-O` reaches dependencies**: IfcOpenShell 0.8.5 assigns inside an assert, so the app refuses optimised Python before creating a workspace, and a witness checks that refusal. A gate must say whether it validates behaviour or validates refusal of an unsupported environment.
- **Stable identity is not byte reproducibility** (set ordering changed placement numbers); **quantisation is not tolerance** (a one-to-one triangle match within 20 µm); **smoothness needs topology** (edge-connected fans).
- **Independence is not absolute**: both geometry paths use IfcOpenShell, and the report says so.
- **"Release acceptance is a closed set of current-candidate witnesses, not a score."**

## 6. Reusable rules (adopted in v1)

These are the rules v1 takes from the patches. "Kit" names where loomkit implements one; the rest are templates or checklist items.

| # | Rule | Evidence (grade) | In the kit |
|---|---|---|---|
| R1 | Bind every witness record to the sha256 of the full candidate inventory, test code included; reject stale records | A01 reproduced; closed in v2-v4, Gear, Data City, IFC (C) | `core.write_witness`, `accept` STALE_WITNESS |
| R2 | Refuse a witness whose candidate changed while it ran | v3 enforcement event (C) | CANDIDATE_CHANGED_DURING_WITNESS |
| R3 | Gate predicates raise; never `assert`; test every gate under `-O`; refuse `-O` if a dependency needs asserts | A02 (C); IFC refusal (C) | `need()`; `tests/test_gates.py` runs both modes |
| R4 | A named profile lists the required witnesses; an empty or partial set never passes | LS1 §9 (L); v2+ (C) | `accept`, `load_profile` EMPTY_PROFILE |
| R5 | Status ≠ grade; `fail`, `error`, `not_run` never satisfy a required witness; `deferred` / `not_applicable` only if the profile allows it and a reason is written | LS1 §12 (L); BREAK cell semantics (C) | `accept.status_acceptable` |
| R6 | Every negative control expects one stable diagnostic; a crash is `error`; a surviving control fails the suite | LS1 §12; BREAK; LS4 SURVIVING_CONTROL (C) | `tests/test_gates.py` `expect()` |
| R7 | Coverage fields are acceptance conditions, not comments | v3, v4 BROWSER_COVERAGE_REQUIRED (C) | profile `coverage` → COVERAGE_REQUIRED |
| R8 | Development and preview runs never count | v4 DEVELOPMENT_WITNESS (C) | DEVELOPMENT_WITNESS |
| R9 | Evidence files are hashed in the record and re-verified at acceptance | v4 evidence_hashes; Gear trace hashes (C) | EVIDENCE_DRIFT |
| R10 | Model judges give located, image-bound `suspected` flags; no number in a release | v4, IFC (C); user decision 3 Nov | `picture.validate` |
| R11 | Keep unrun witnesses visible in the receipt, with their reason | Every debrief's "not converted into passes" (C) | profile `visible_not_run`; receipt `not_run` |
| R12 | Receipts chain to their predecessor and never overwrite | v1→v4 chain (C) | `receipt.write` RECEIPT_EXISTS; `prev` |
| R13 | Fold back as an additions-only patch whose smoke test carries the counterexamples, checked normal and `-O` in an empty repo | 5 patches (C, survey) | `foldback.check` |
| R14 | Run the real runtime even when the file is valid: shader compile, asset preflight, metadata attachment | F01; v4 404 bakes; Gear/IFC metadata (C) | Template checklist; traps glsl-reserved-active, metadata-containerfield (lexical guards only) |
| R15 | Isolate the measured pixels from the presentation (UI, overlays, splash, CSS animation); unchanged-twice control first | v2, v3, Break (C) | Gate checklist |
| R16 | Declare coordinate spaces, sampler domains, texture ownership and topology as contracts with probes | v3, v4, IFC (C) | Gate checklist |
| R17 | Four clocks stay apart (rAF, display, CPU, GPU); unknown stays null; an idle renderer has no frame rate | v4, IFC G-MEASURED-WORK (C) | Gate checklist; `profile_contract` in LS4 kit |
| R18 | A condition change cancels and erases a measurement in progress | v2-v4, Gear (C) | Gate checklist |
| R19 | Unknown is not zero, end to end | Data City (C) | Gate checklist; first fold-back to promote [CITY] |
| R20 | Report certified bounds and the equivalence class, never a sampled best case | Gear (C) | Debrief form |
| R21 | Promote a rule only with its minimal reproducer, both sides of the test, a corpus re-run and the exact tool versions; browser facts stay runtime-labelled | All five READMEs (L) | Fold-back form |
| R22 | Creative choices stay local as scoped art-direction memory; tests passing never raise S to C | v2, v3 (L) | Debrief form "What stays local" |
| R24 | Reproduction across platforms compares decoded content (pixels, tolerance floats), not file bytes; byte identity is a same-platform claim | v3+patch vs v4 (C, [CAT]) | Debrief form |
| R25 | Run a fold-back's smoke on a second platform before promotion; geometry witnesses compare surfaces, not one kernel's triangulation | IFC positive control fails on arm64 (C) | `foldback.check` with `python=` |
| R23 | Test the instrument too: a wrong instrument must show up as `error`, not as a product `fail` | Break's CSP control; loomkit's own `-I` smoke mistake, 3 Nov (C) | `foldback.check` error path |

## 7. What should stay local

Cathedral staging, the brass palette, the flower resonators, the eight-shot edit, the pavilion's oak and bronze, the gear recipes, Data City's fog look: these are project decisions, to keep as scoped art-direction records after his review. None is a validation rule [LS3 §10; LS2 §6; IFC].

## 8. What the patches do not prove

- That any rule works on the family corpus (798 to 883 files in x3d.onto): none was run there.
- Anything about real GPUs, physical A/V latency, flash safety or human taste: all are explicitly unmeasured in every project.
- Authenticity: every receipt is unsigned byte integrity, and every project says so.
