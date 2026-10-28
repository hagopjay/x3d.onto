# Gobbler v4, step 1: live hover on the Gobbler 3 Deep scene

The cornerstone UI from `docs/v4/HOVER-UI-SPEC.md`, running for real: a **none / minimal** toggle, a **guided mouse**, **corner-docked cards** and **live ontology data on hover**, as a layer over the Gobbler 3 Deep scene. Nothing is replaced: the scene file is the Deep build byte for byte, and the v3 pages are untouched. This is a new folder.

```
make v4-data     # fetch the Deep build + X_ITE 16.5.1 (hash-checked), patch the engine, trim the ontology block
make test-v4     # unit tests (node only)
make v4          # serve: http://127.0.0.1:8791/index.html   (from gobbler-v4/)
```

Page parameters (for the picture-judge loop and for deterministic frames): `?ui=none|min`, `?view=Wide|Colossus|EyeToEye|Inside|Flywheel|Crown`, `?hover=<entity index>&tier=2|3` (opens that card, no mouse needed), `?glass=1` (keep the blur behind cards even when frames are slow). Stills are always `?ui=none`.

## What it does

| Do | Get |
|---|---|
| rest on a star, 0.15 s | one-line tooltip: name, kind, provenance (`+k` when k more stars sit within 12 px; `←` `→` cycle them) |
| 0.45 s | the card: key numbers (a Finding leads with its measurements) or the best evidence quote, grade, top four relations with direction and grade dot |
| 1.2 s, or click | deep: for X3D names the ontology block (ancestry, the ontology's own definition, how the XSD judged its predicted placements, "map, not gate"), edge evidence, sources, loop membership |
| click / `Esc` | pin the card / close it |
| double-click or `F`, or click a relation row | fly there through the scene's `Probe` viewpoint, from the real camera pose |
| `Shift` | hover every star (in crowded views only the 648 core stars answer, so the pick is right 79 to 92% instead of 72 to 81%) |
| `U` / hold `H` | UI none and minimal / hide everything while held |

The pointer snaps to the nearest star within 30 px (distance only, depth breaks ties), dims the frame outside a 330 px radial, and holds the tour still while something is being read (the tour resumes from the same phase). The card docks in the emptiest of the four corners that does not cover the star or a chip, with a leader line that fades with distance. Below 720 px it is a bottom sheet.

UI **none** shows nothing, installs no sensor and adds nothing to the scene. In **minimal** the page adds one `ProximitySensor` to the *in-memory* scene to read the camera (X_ITE's public API does not expose the user's orbit offset otherwise); the `.x3d` file is never changed.

## Files

| Path | What |
|---|---|
| `index.html`, `src/ui.css` | the page and its overlay styles (all classes `gv4-` prefixed) |
| `src/placement.js` | corner placement, pure function: halo, chip obstacles, reserved heights, hysteresis, shrink and fallback, bottom sheet |
| `src/pick.js` | project every drawn star with the camera pose, grid index, nearest-star pick, core-tier LOD with hysteresis |
| `src/cards.js` | tooltip and card HTML from the graph and the ontology block; every card names provenance and grade; everything escaped |
| `src/density.js` | where the subject is on screen: the frame's own pixels (primary) or projected stars and tethers (fallback) |
| `src/hover.js` | the controller: camera, pointer, dwell tiers, UI levels, drawing, readback, keys, fly |
| `engine/common.js` | the shared PolyXandria engine from Gobbler 3 Deep plus `PX.tourHold` / `PX.tourRelease` (`tools/patch_engine.py` makes it, asserting every edit) |
| `tools/build_onto_hover.py`, `data/onto-hover.json` | the ontology block: 104 classes drawn as stars, 39 KB (7.8 KB gzip) |
| `tools/fetch_deep.sh` | fetches the Deep build (x3d.ML `51e185f`, `gobbler-v3/deep/build-private/`) and X_ITE 16.5.1; verifies sha256 |
| `test/`, `e2e/` | unit tests and the live-scene Playwright suite |

Fetched, not committed: `data/deep/`, `vendor/`.

## Measured (27 to 28 Oct 2026)

Grades: **Confirmed** = reproduced by a test in this folder; **Likely** = works in software-GL Chromium, not yet seen on a real GPU; **Suspected** = not measured.

| Claim | Result | Grade |
|---|---|---|
| Placement rules (halo, chips, hysteresis, sheet, shrink, fallback) | 16 tests, incl. a 4,000-case seeded fuzz; three deliberate mutations all caught | Confirmed |
| Pick: on-screen counts and LOD in the six Deep views | identical to the spec table (1,896 / 1,548 / 2,220 / 758 / 174 / 186 stars) | Confirmed |
| Pick: self-pick accuracy at 3 px pointer noise, on the live scene | Wide 92%, Colossus 80%, Crown 79% (core tier only); Eye 92%, Flywheel 91%, Inside 100% | Confirmed |
| Cost of picking | project + bucket ~50 us, query ~0.5 us (node 22) | Confirmed |
| Every card has provenance and grade, no template leaks | all 2,476 drawn stars at both tiers | Confirmed |
| Ontology block | 105 of 178 drawn NodeType/Component stars (104 classes); Shape reproduces 59 predicted, XSD accepts 22 / rejects 30 / 7 inconclusive | Confirmed |
| Dwell tiers | card no earlier than 0.45 s, deep no earlier than 1.2 s (software GL runs ~5 fps, so each tier lands up to a frame late) | Confirmed |
| UI none: nothing visible, no sensor, no added scene node | checked in the DOM and in the scene | Confirmed |
| Projection of the graph's coordinates onto the rendered frame | Wide, Inside, Flywheel, Crown: scale 0.999 to 1.001, offset 1.8 px or less. Colossus and Eye: too few isolated star sprites to decide | Likely |
| Cost on a real GPU, blur behind cards | not measured; the blur drops to a solid panel if the frame rate stays under 50 | Suspected |

Not done yet: the "Face" camera from the owner's stills is not a Viewpoint of the Deep scene; the card-to-tether brightening; touch input is written but only tap logic was exercised.

## Live-scene tests

`e2e/e2e.js` drives a real mouse in full Chromium with software GL (the default headless shell crashes on this scene). Serve `gobbler-v4/` on port 8795 (`GV4_BASE` overrides), then `cd e2e && node e2e.js [fit,pick,place,ui,keys,tour,deterministic,resize,cost]`. Frames land in `e2e/out/`.
