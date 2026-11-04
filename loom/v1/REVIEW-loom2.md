# Review: the loom2 delivery (4 Nov 2026)

Source: `~/Downloads/loom2-20261104T152546Z-1-001.zip` (sha256 `ee1d4454…8fa1`), unpacked read-only into `../incoming2/` (`READY.txt` lists 494 files with hashes). Two projects from the other model, each with a debrief, receipts, an upgrade patch and a fold-back patch. Grades as in LOOM-v1.md: C = a tool ran here; L = read; S = suspected.

## What arrived

| Item | What it is | State here |
|---|---|---|
| Gobbler · Cabinet of Worlds (`Gobbler-Worlds-Within (2).zip`) | The Gobbler bird with four nested worlds (Giza, Pantheon splats, materials, Drillfield): seven-chapter journey, a residency controller (at most two world groups resident), baked GGX studio reflection, profiler | Runs at :8818; renders, no console errors (C, built-in browser, 4 Nov) |
| `Gobbler-Upgrade (2).patch`, `Gobbler-Loom-Foldback (2).patch`, `Gobbler-Technical-Debrief (3).html`, `Gobbler-Delivery-Receipt (1).json` | Upgrade from the supplied export; fold-back kit `loom-feedback/gobbler-cabinet/` (9 files) | Receipt hashes match the files (C) |
| Linked Observatory (`Linked-Observatory.zip`) | Gobbler 5 and Constellation 3 joined by 103 canonical class links; one iframe/renderer at a time; arrival acknowledged by an observed camera frame | Runs at :8820; renders, no console errors (C) |
| Gobbler 5 · Living Archive (`Gobbler-5-Living-Archive.zip`) | The Gobbler half of the Observatory, standalone | **Zip truncated at source** (see below); restored; runs at :8819, renders (C) |
| Constellation 3 · Human Atlas | The ontology constellation: solar system, village, smithy, night sky | Runs at :8821; renders, no console errors (C) |
| `Loom-Patch-Kit.zip` | `gobbler-refinement.patch` (from "Gobbler 4 Live Hover"), `ontology-refinement.patch` (from "Ontology Constellation 2"), `loom-foldback-additions.patch` (`loom-feedback/linked-observatory/`, 7 files), `patch-verification.json` | Patch hashes match the receipt (C). The two refinement patches' base archives are not in either Drive folder, so their clean apply was not re-checked here |
| `Linked-Observatory-Technical-Debrief.html`, `Delivery-Receipt.json` | Debrief; receipt covering five artifacts | Receipt hashes match (C) |

## Finding 1: a receipt certified a broken archive (C)

`Gobbler-5-Living-Archive.zip` is 998,467 bytes with 51 complete local entries and **no central directory**: `unzip` refuses it. The Drive copy has the same size, so it was truncated before upload. `Delivery-Receipt.json` lists exactly this size and sha256. The producer's receipt hashed the broken bytes and called them delivered.

Recovery (C): `v1/kit/examples/salvage_zip.py` inflated all 51 entries, each passing its CRC-32. The archive's own `evidence/candidate.json` lists 40 executable files; 8 were missing, all vendored X_ITE 16.5.1 files. Byte-identical copies (same sha256 as the inventory) exist in `Linked-Observatory/gobbler/vendor/x_ite/`, and were copied in. All 40 inventory hashes then verify. `Linked-Observatory/gobbler/` is itself an intact copy of the whole Living Archive, so nothing unique was lost.

**Rule (new, R26):** a delivery gate opens what it hashes. Each archive must pass an integrity test (`unzip -t`, or a full listing) before its hash enters a receipt. A hash binds bytes; it does not say the bytes are a valid archive.

## Finding 2: page titles lag the release (C, minor)

The Living Archive serves the title "Gobbler 4 Live Hover", and Constellation 3 serves "Ontology Constellation 2": the titles of the projects they were refined from. Cosmetic, but it is the stale-badge failure the Gobbler debrief itself names (lesson 1: a claim needs a content key). A release check could compare `<title>` with the release name.

## Finding 3: the fold-back shape diverged (C)

Both new fold-backs are additions-only (9 of 9 and 7 of 7 files new) but use `loom-feedback/<name>/` with `tests/*.cjs` and `tests/*.py`, instead of the earlier `tools/<name>/smoke.py`. Their own tests all pass in empty repos here, under normal Python and `-O`, given an interpreter with the dependency (`numpy` for `radiance.py`, `lxml` for the Observatory's `predicates.py`):

| Kit | node tests | Python tests |
|---|---|---|
| gobbler-cabinet | profiler.cjs pass, stream.cjs pass | predicates.py pass (both modes); radiance.py pass with numpy (both modes) |
| linked-observatory | contracts.cjs 9/9 pass, profiler.cjs pass | predicates.py pass with lxml (both modes) |

`kit/loom foldback` only looks for `tools/*/smoke.py`, so it would mark these as failing for shape alone. Open question for v1: accept `loom-feedback/<name>/` with a test manifest as a second shape, or ask fold-backs to keep one `smoke.py` entry point?

## What the other model learned (from the debriefs; L, as reported)

Gobbler Cabinet (13 numbered failures) and Linked Observatory (sections 02 to 12), condensed into rules worth adding to LEARNINGS:

| # | Lesson | Evidence it reports |
|---|---|---|
| L1 | **Witness the witness.** An old expected camera and an old observed camera agreed perfectly before the new command reached a frame. Arrival = matching intent serial + an applied frame later than the intent + a completed flight + a sensor pose within tolerance (ARRIVAL-EPOCH) | Observatory §01, §04 |
| L2 | **Stale green badges.** The page showed "valid X3D 4.0" while its scene's bytes differed from the historical receipt (1,663,991 vs 1,714,665 bytes). Claims are rebound to current bytes or shown as historical (CLAIM-SCOPE) | Gobbler §evidence, lesson 1 |
| L3 | **Intentional degeneracy is a declared representation.** 3,605 zero-area quads in 4 ribbon meshes crashed automatic tangent generation; explicit Tangent nodes fixed it without deleting the ribbons. A blanket "delete degenerate faces" repair would have destroyed the design | Gobbler §ribbon |
| L4 | **Resolve assets against the scene URL.** 39 textures silently failed in Constellation because the scene was decoded into a string whose base became the HTML page's URL (URL-SCOPE); optional engine features need their own asset closure (DEPENDENCY-CLOSURE) | Observatory §02 |
| L5 | **Numerically stable camera algebra.** `log(sqrt(1+b²)−b)` cancels to log(0) at astronomical scales; `−asinh(b)` does not (ZOOM-RANGE) | Observatory §04 |
| L6 | **Canonical joins, unknown stays unknown.** Name intersection suggested 105 links; 103 survive canonical-ID matching with row hashes; 261 classes stay explicitly unmatched (SEMANTIC-JOIN) | Observatory §07 |
| L7 | **One owner per clock and per resource.** User pause vs offscreen culling (CLOCK-OWNERSHIP); a single residency controller that protects the visible world and the destination; a prefetch grace period accidentally became a load timeout | Observatory §06; Gobbler lessons 4, 11 |
| L8 | **Mock success cannot certify an adapter.** X_ITE keeps FAILED_STATE until `loadNow()`; `LoadSensor.watchList` vs `children` in the pinned runtime | Gobbler lessons 3, 13 |
| L9 | **Duration is not sample size.** Profiles need ≥ 120 draw intervals and 5 s, unchanged settings and an observed camera; sparse runs stay recorded but rejected (PROFILE-SCOPE) | Both |
| L10 | **Eyes catch lifecycle bugs.** A "ready" frame showing only sky; an arrival label over a still-moving bind transition; a HUD clock throttled behind scene time | Gobbler lessons 6, 12; Observatory fold-back README |
| L11 | **Judge the composite.** Twelve transparent beam layers summed to near-opaque; per-cone opacity is not the visible result | Gobbler lesson 7 |
| L12 | **A witness can be the defective component.** An audio-cleanup assertion counted the intentionally running heartbeat as a leak | Gobbler lesson 9 |

Everything else matches Loom v1 already: candidate binding, unsigned receipts, null for unmeasured GPU, SwiftShader scope, flags-not-grades for image review, no publication.

## Not done here

- Browser QA suites (`tests/browser.cjs`, `tests/controls.cjs`) not run: they need Playwright.
- The refinement patches' base archives ("Gobbler 4 Live Hover", "Ontology Constellation 2") are not in either Drive folder, so their reproduction was not re-checked.
- Both new fold-backs are PRs into hagopjay/x3d.onto, applied unchanged under `loom-feedback/`: gobbler-cabinet #16, linked-observatory #17 (opened 4 Nov, not merged).
