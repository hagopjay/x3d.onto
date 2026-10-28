# Gobbler v4, step 1: live hover on the Gobbler 3 Deep scene

The cornerstone UI from `docs/v4/HOVER-UI-SPEC.md`, running for real: a **none / minimal** toggle, a **guided mouse**, **corner-docked cards** and **live ontology data on hover**, as a layer over the Gobbler 3 Deep scene. Nothing is replaced: the scene file is the Deep build byte for byte, and the v3 pages are untouched. This is a new folder.

```
make v4-data     # fetch the Deep build + X_ITE 16.5.1 (hash-checked), patch the engine, trim the ontology block
make test-v4     # unit tests (node only)
make v4          # serve: http://127.0.0.1:8791/index.html   (from gobbler-v4/; PORT=... to change it)
make e2e-v4      # the live-scene suite in Chromium, against the same PORT (see "Live-scene tests")
```

Page parameters (for the picture-judge loop and for deterministic frames):

| Parameter | Effect |
|---|---|
| `?ui=none` or `?ui=min` | the UI level; stills are always `?ui=none` |
| `?view=Wide`, `Colossus`, `EyeToEye`, `Inside`, `Flywheel`, `Crown` | start in that viewpoint (the tour does not start) |
| `?hover=<entity index>&tier=2` or `3` | open that star's card by URL, no mouse needed (an index outside 0 to 2,475 is ignored) |
| `?glass=1` | keep the blur behind cards even when frames are slow (frames for the docs) |
| `?tune=1` | open the tuning panel at load |

## What it does

| Do | Get |
|---|---|
| rest on a star, 0.15 s | one-line tooltip: name, kind, provenance (`+k` when k more stars sit within 12 px; `←` `→` cycle them) |
| 0.45 s | the card: key numbers (a Finding leads with its measurements) or the best evidence quote, grade, top four relations with direction and grade dot |
| 1.2 s, or click | deep: for X3D names the ontology block (ancestry, the ontology's own definition, how the XSD judged its predicted placements, "map, not gate"), edge evidence, sources, loop membership |
| click / `Esc` | pin the card / close it |
| double-click or `F`, or click a relation row | fly there through the scene's `Probe` viewpoint, from the real camera pose |
| `Shift` | hover every star (in crowded views only the 648 core stars answer, so the pick is right 79 to 92% instead of 72 to 81%) |
| `U` / hold `H` | UI none and minimal / hide everything while held (releases the tour too) |
| `T` | the tuning panel (below) |

The pointer snaps to the nearest star within 30 px (distance only, depth breaks ties), dims the frame outside a 330 px radial, and holds the tour still while something is being read (the tour resumes from the same phase). The card docks in the emptiest of the four corners that does not cover the star or a chip, with a leader line that fades with distance. Below 720 px it is a sheet on the bottom or top edge. Touch: tap a star for its label, tap it again for the card, tap the sky to close.

UI **none** shows nothing, installs no sensor and adds nothing to the scene. In **minimal** the page adds one `ProximitySensor` to the *in-memory* scene to read the camera (X_ITE's public API does not expose the user's orbit offset otherwise); the `.x3d` file is never changed.

### The tuning panel (press `T`)

The taste calls of the spec as live settings, remembered per browser (`localStorage`, in try/catch):

| Setting | Default | What it changes |
|---|---|---|
| Snap distance | 30 px | how far from a star the pointer still catches it |
| Tooltip after / Card after / Deep card after | 150 / 450 / 1200 ms | the dwell tiers (kept in order: tooltip, then card, then deep) |
| Focus dim | 1.0x | strength of the dim outside the 330 px radial (0 = off) |
| Card keeps clear of the star | 96 px | the halo no card may enter |
| Crowded views: hover core stars only | on | off = every star answers all the time (accuracy 72 to 81% when wide) |
| Leader line from star to card | on | the curve from the star to its card |
| Frosted glass | auto | auto drops the blur to a solid panel if frames fall under 50 fps; always; off |

`window.gobbler.tune({snap: 40})` does the same from code; the open panel is an obstacle for the cards, so a card never lands on it.

## How it works

```
X_ITE scene (Deep, untouched) ──ProximitySensor──▶ camera pose ─┐
graph-v3.json (2,476 stars) ─────────────────────▶ pick.js ◀────┘  project, grid, nearest star, core-tier LOD
frame pixels (end-of-frame readback) ──▶ density.js ──▶ placement.js ──▶ corner, sheet, leader
graph + onto-hover.json ──▶ cards.js ──▶ tooltip and card HTML ──▶ hover.js draws DOM + SVG above the canvas
```

- **Camera.** A run-time `ProximitySensor` reports the real position and orientation (it follows the user's orbit); the field of view comes from the active viewpoint. The page projects the graph's own star coordinates with them (`pick.js`), so a star is picked from data, not by reading pixels.
- **Where the card goes.** The frame itself is read inside X_ITE's end-of-frame callback (a 192 px copy of the canvas, valid there without `preserveDrawingBuffer`), turned into a luminance density, and `placement.js` scores the four corners (density, leader density, distance, a 96 px halo, the measured chips). If the readback fails three times it falls back to projected stars and tethers, which cannot see the bird, and retries after 15 s.
- **What the card says.** Everything is read from the graph already in the page: provenance and grade on every card, evidence quotes, relations, loops; for 105 of the 178 drawn NodeType and Component stars the ontology block (104 classes, 39 KB, 7.8 KB gzip) built by `tools/build_onto_hover.py` from the ontology and the XSD cross-check.
- **Tour.** The engine gets `PX.tourHold` and `PX.tourRelease` (a pause that keeps the phase); the star under the pointer holds still and the tour resumes where it stopped. `tools/patch_engine.py` makes `engine/common.js` and asserts every edit.

## Files

| Path | What |
|---|---|
| `index.html`, `src/ui.css` | the page and its overlay styles (all classes `gv4-` prefixed) |
| `src/placement.js` | corner placement, pure function: halo, chip obstacles, reserved heights, hysteresis, shrink and fallback, sheet |
| `src/pick.js` | project every drawn star with the camera pose, grid index, nearest-star pick, core-tier LOD with hysteresis |
| `src/cards.js` | tooltip and card HTML from the graph and the ontology block; every card names provenance and grade; everything escaped |
| `src/density.js` | where the subject is on screen: the frame's own pixels (primary) or projected stars and tethers (fallback) |
| `src/hover.js` | the controller: camera, pointer, dwell tiers, UI levels, tuning panel, drawing, readback, keys, fly |
| `engine/common.js` | the shared PolyXandria engine from Gobbler 3 Deep plus `PX.tourHold` / `PX.tourRelease` |
| `tools/build_onto_hover.py`, `data/onto-hover.json` | the ontology block |
| `tools/fetch_deep.sh` | fetches the Deep build (x3d.ML `51e185f`, `gobbler-v3/deep/build-private/`) and X_ITE 16.5.1; verifies sha256 before installing |
| `tools/make_artifact.py` | a copy of the page for a host that adds its own document skeleton (body only, plus exactly the files the page loads) |
| `test/`, `e2e/` | unit tests and the live-scene Playwright suite; `e2e/frames.js` and `e2e/storyboard.py` make the frames in `docs/v4/live/` |

Fetched, not committed: `data/deep/`, `vendor/`.

## Measured (27 to 28 Oct 2026)

Grades: **Confirmed** = reproduced by a test in this folder; **Likely** = works in software-GL Chromium, not yet seen on a real GPU; **Suspected** = not measured.

| Claim | Result | Grade |
|---|---|---|
| Placement rules (halo, chips, hysteresis, sheet, shrink, fallback) | 19 tests, incl. a 4,000-case seeded fuzz that covers narrow screens; deliberate mutations caught | Confirmed |
| Pick: on-screen counts and LOD in the six Deep views | identical to the spec table (1,896 / 1,548 / 2,220 / 758 / 174 / 186 stars) | Confirmed |
| Pick: self-pick accuracy at 3 px pointer noise, on the live scene | Wide 92%, Colossus 80%, Crown 79% (core tier only); Eye 92%, Flywheel 91%, Inside 100% | Confirmed |
| Cost of picking | project + bucket ~50 us, query ~0.5 us (node 22) | Confirmed |
| Every card has provenance and grade, no template leaks | all 2,476 drawn stars at both tiers | Confirmed |
| Ontology block | 105 of 178 drawn NodeType/Component stars (104 classes); Shape reproduces 59 predicted, XSD accepts 22 / rejects 30 / 7 inconclusive | Confirmed |
| Card placement on the live scene | 42 of 42 cards (Wide, Flywheel, Crown) opened by a real mouse hover, none within 90 px of its star, none over a chip, all placed from the frame's own pixels | Confirmed |
| Dwell tiers | card no earlier than 0.45 s, deep no earlier than 1.2 s (software GL runs ~5 fps, so each tier lands up to a frame late) | Confirmed |
| UI none: nothing visible, no sensor, no added scene node | checked in the DOM and in the scene | Confirmed |
| Pose after UI none, camera moved, UI minimal | projected stars land on the drawn stars again (scale 0.999 to 1.001, offset 0.5 px or less, 200 or more sprites in Flywheel) | Confirmed |
| Projection of the graph's coordinates onto the rendered frame | Wide, Inside, Flywheel, Crown: scale 0.997 to 1.001, offset 1.6 px or less (two runs). Colossus and Eye: too few isolated star sprites to decide (Eye reads 0.984, offset 8 to 9 px from 17 sprites, so treat it as unresolved) | Likely |
| Fallback density (frame cannot be read): corner within 0.25 score of the pixel-best | Flywheel 14 of 14, Crown 14 of 14, Wide 6 of 14 (it cannot see the bird); the exact same corner in 4 to 10 of 14 (Flywheel), 11 of 14 (Crown), 6 of 14 (Wide) | Confirmed, a limit |
| Cost with a deep card open, software GL | frame interval 82 to 92% of UI none across two runs (e.g. 204 ms against 221 ms), so no measurable cost here | Likely |
| Cost on a real GPU, blur behind cards | not measured; the blur drops to a solid panel if the frame rate stays under 50 | Suspected |
| Phone: tap, second tap, sheet inside the screen, tap sky closes | 390 x 844 touch emulation | Likely |

Under a strict content policy (own files only, no `eval`) the page boots and works; only X_ITE's tangent module (`mikktspace_bg.wasm`) is refused, which the Deep scene does not need.

## Live-scene tests

`e2e/e2e.js` drives a real mouse in full Chromium with software GL (the default headless shell crashes on this scene). Serve with `make v4` (or any server on `GV4_BASE`, default `http://127.0.0.1:8795/`) and run `make e2e-v4`, or `cd e2e && node e2e.js [suites]`. Suites: `fit`, `pick`, `place`, `ui`, `toggle`, `keys`, `tour`, `deterministic`, `badparams`, `touch`, `tune`, `resize`, `cost` (default: all). Frames land in `e2e/out/`; `node frames.js` makes the six documentation frames and `python3 -I storyboard.py` the contact sheet. `node requests.js` lists every file the page loads (what a published copy must carry).

## Known limits and open items

- The "Face" camera from the owner's stills is not a Viewpoint of the Deep scene, so it is not in the view list; the card-to-tether brightening is not built (relation rows ring the neighbour star only).
- Real-GPU frame cost is open (Suspected). Touch is exercised with emulation only.
- Eye and Colossus views: the projection fit is undecided (too few isolated sprites), see the table.
- One flake seen: in a full 75-check run the double-click flight check failed once (the camera did not move); it passed 3 of 3 times alone and in earlier full runs, and the cause is not found, so it is not called fixed.
- Test clean-ups noted by the last review and left for later: the "extra star" check in `test/test_pick.js` re-tests its own reference (it can never fail), `test_density.js` exercises `fromStars` but the page runs `fromGraph`, and the seeded random generator is copied into three test files.
