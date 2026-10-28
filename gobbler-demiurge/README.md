# Gobbler demiurge: the bird first

A page that boots with the bird alone: the Gobbler 3 Deep head and knowledge graph, the Sun in its chest that beats a replay of real validator runs, a Dyson ribcage of the 364 ontology classes, plumage and a tail fan modelled in Blender, weaving shuttles and a slow cinematic tour. The village and the solar system are not here yet (step 3 of the integration plan and later). It is a **new folder on top of `gobbler-v4/`**, which is untouched: the Deep scene is used byte for byte, and the v4 hover layer runs on top of it unchanged.

Built so far (plan steps): 1 honest loader and gzip delivery, 2 the bird-first page in the locked look, 5 feathers made in Blender, 6 motion (tour, seeded drift, preening wave, shuttles), 7 the heartbeat (heart only), 8 the shell tenders as H-Anim humanoids made in Blender. Step 9 (the tail fan lit by real glTF, USD and video exports) stays **simulated** on purpose: a real export path is the ultimate vision, the plumes are tagged accordingly. Not built: 3 village Inlines and ladder stops 4 to 7, 10 music, 11 picture-judge loop, 12 trailer.

```
make v4-data          # (once) the Deep build and X_ITE 16.5.1, hash-checked
make demiurge-data    # compose the bird scene, gzip it, validate with the fork       -> gobbler-demiurge/data/bird/ (not committed)
make feathers         # (only to remake the feathers; needs a Python with bpy) model + bake + export in Blender -> assets/feathers/ (committed)
make tender           # (same) the H-Anim shell tender -> assets/tender/ (committed)
make test-demiurge    # layer tests (python only)
make demiurge         # serve the repo root: http://127.0.0.1:8791/gobbler-demiurge/index.html
make e2e-demiurge     # the live page in Chromium (serve first, same PORT)
```

Parameters: `?ui=none|min` (stills are `?ui=none`), `?view=face|ribcage|heart|feather|establishing`, `?seed=N` (the camera's drift and the flights' bows; the same seed repeats a take, `?seed=0` turns the randomness off, default 4), and the v4 ones (`?hover=<entity>&tier=2|3`, `?tune=1`, `?glass=1`).

## Look (locked 28 Oct: B's facets, lots of D)

| Part | What it is | Source of the shape |
|---|---|---|
| Head | the faceted Deep head, unchanged (B) | Gobbler 3 Deep scene |
| Heart | the Sun in the chest: a shader sphere (granulation, limb darkening) with two glows. It **beats a tape of 30 real validator runs**: a gold beat for a scene that passed (or was repaired), a quicker red beat for each failing round, and a ping ring leaves the heart on every beat. 38 beats, about 37 s, a seeded few percent of heart-rate variability | `data/heartbeat/xbench-run1.json`, `tools/layers.py` |
| Ribcage | lat/lon gold lattice, 364 faceted gem beads (one per class, green = new in 4.1), three domain rings turning slowly | x3d.onto `data/explorer.json`: latitude from class depth as in v2; **longitude respaced evenly** (v2's own angles stack classes into strings) |
| Flywheel | a ring of 8 stations around the heart with a running pulse (display only) | layers.py |
| Tenders | 10 walkers on the ribcage shell, points of light beyond 5 units. Each is an **H-Anim humanoid modelled in Blender** (18 joints, faceted gold skin, cool shadows), exported by x3d-blender-io. Three copies with their own gait (1.2, 1.5 and 1.8 s a cycle) are shared by USE; each walker orbits at the speed its stride needs, so feet do not slide. The walk is joint rotations by interpolators and ROUTEs, no Script. What they tend is simulated | `assets/tender/`, `tools/blender_tender.py`, `tools/tender.py`, layers.py |
| Wing | 10 primaries, one per orchestrator role; a role colour shows while that role "works" (**simulated**, staggered clocks); every 27 s a **preening wave** lifts them in turn | layers.py |
| Tail fan | 18 plumes grown from the Blender root orb; streams from the graph converge on it with 5 running pulses. The fan **starts closed and unfurls** the first time the camera comes near. Three plumes are tagged for the Blender paths glTF, USD and video and six are outline-only mocks (O3DE, ParaView, 3D Slicer, Unity, Defold, IFC); **all of it is simulated for now** and tagged so | layers.py |
| Feathers | modelled in Blender: a tapered quill tube, a faceted vane, barbs, outline; **golden-hour light baked in Cycles** (a warm low sun over a cool sky), exported by x3d-blender-io as X3D 4.0. Sunlit facets take gold (or the role colour), shadowed facets stay cool. Three variants, drawn at two detail levels (`LOD` at 11 and 60 units) | `assets/feathers/`, `tools/blender_feather.py` |
| Shuttles | four agents weaving across the bird on smooth closed paths with fading trails (simulated, seeded wobble) | layers.py |

Real plumes are drawn ready, not lit by a passing export; that wiring is the ultimate vision and the tags say so.

## Blender pipeline for the feathers

`tools/blender_feather.py` builds each feather in Blender's Python (bmesh): a quill, a vane on a 24 by 3 grid with cup, twist and a small seeded wobble (so the quads stop being flat), triangulated and flat shaded. It lights a white copy with a golden-hour rig (a warm sun lamp at 24 degrees plus a cool multiple-scattering sky), bakes direct and indirect light into corner colours with Cycles, sets the exposure so the 92nd percentile facet sits at 0.92, and exports through x3d-blender-io as X3D 4.0, one file per variant. `tools/feathers.py` reads those files back and `layers.py` places them with a Transform per plume (rotation from the plume's own axes, scale from its length and width). The page build itself does not need Blender. `assets/feathers/receipt.json` records the Blender version, the exporter commit, the script's sha256 and the file hashes.

## Blender pipeline for the tenders

`tools/blender_tender.py` builds an armature of 18 joints in Blender (the lowest H-Anim 2.0 articulation level as I remember it: humanoid_root, sacroiliac, vl5, vt6, vc4, skullbase, and left and right shoulder, elbow, wrist, hip, knee, ankle; **the joint list is from memory and has not been checked against ISO/IEC 19774-1**) and one faceted skin mesh weighted rigidly to those joints, with per-face colours from a fixed key light (gold, cool shadows). x3d-blender-io exports the armature plus its skinned mesh as an `HAnimHumanoid` (version 2.0) with an `HAnimJoint` per bone, `skinCoord`, per-joint `skinCoordIndex` and `skinCoordWeight`, and one skin Shape. `tools/tender.py` reads that file and hands out copies with a prefix on every DEF; the PhysicalMaterial is dropped so the baked face colours draw unlit like the feathers. The composed scene gets one more head statement, `<component name='HAnim' level='1'/>`, so the compose step now makes three insertions (the test checks all three and that the rest is the Deep scene byte for byte). A bug caught on the way: the first export weighted only the torso joints (new bmesh vertices have no valid index until `index_update`), so arms and legs did not bend; it shows as 0 skin indices on the limb joints in the file.

## Step 1 in this build: honest loader and gzip delivery

`src/boot.js` replaces the engine's fixed status text. Every stage names itself with bytes and seconds, and a failure prints the stage and the error text instead of a counter:

```
starting X_ITE → fetching the bird · 308 KB of 308 KB → parsing the scene · 1.37 MB of X3D → drawing the first frame → bird on screen
```

The scene ships as `gobbler4-bird.x3d.gz` and is inflated in the page (`DecompressionStream`); a published copy can carry base64 text of the gzip (`GD_CFG.enc = 'b64gz'`) for hosts that refuse binary. The graph (266 KB gzipped), the ontology block, the tag anchors and the validator receipt load **after the first frame**; the hover layer starts when the graph arrives. This ports the technique from the Constellation 2 version 3 fix (gzip on the wire, inflate in the page, a status line that says where it is); the code is new, because that fix lives in a packaged copy, not in this repo.

## Controls: four, as planned

UI level (`U`, none / minimal), Face (home view, key 1), Tour, and a right-edge rail of 8 zoom stops (keys 1 to 8). Live stops: 1 Face, 2 Dyson ribcage, 3 Heart, 8 A feather. Stops 4 to 7 (Earth and Moon, village from orbit, plaza, a villager) show dashed and "next step". `T` toggles the tour and `Shift+T` opens the v4 tuning panel (the plan's key rule; the panel's own footer still says "T tune"). `Shift+F` is full screen; hold `H` hides everything. Lights out (`L`) is not wired. The v4 corner cards stay the one card style. Minimal UI also shows 15 small anchor tags (heart, ribcage, flywheel, wing, tenders, Blender, 9 export targets); tenders and mock plumes appear only within 15 units.

**The tour** plays the shot list on a spline with continuous velocity (no stop at every waypoint), easing the field of view with it, and starts by flying from wherever the camera is: Establishing, Face, push-in on the eye and wattle, an orbit of the ribcage (over the head and round behind), underneath the bird and up to the tenders, the heart (watch the rings), the fan reveal (the fan unfurls), and back to the Establishing frame so the loop closes. About 85 s. A slow seeded drift keeps the camera alive; flights between ladder stops bow slightly off the straight line. The village shots (the dive, the plaza) come with step 3.

## Measured (X_ITE 16.5.1 npm package, unpatched, full Chromium 1243 on SwiftShader software GL, local server, 1280 x 800 and 1527 x 923)

Grades: **Confirmed** = reproduced by a test or tool output in this folder; **Likely** = follows from what was seen; **Suspected** = not measured.

| Claim | Result | Grade |
|---|---|---|
| Composed scene validates | XSD valid, profile Immersive OK, 0 semantic errors and 0 warnings (45 info), validator x3d_mcp fork `2b696f5` | Confirmed |
| Feather files validate | each of the three exported files: XSD valid, profile OK, 0 semantic errors and 0 warnings (13 info), fork `2b696f5` | Confirmed |
| Tender file validates | `assets/tender/tender.x3d`: XSD valid, profile OK (HAnim 1, Shape 2), 0 semantic errors and 0 warnings (4 info), fork `2b696f5` | Confirmed |
| Deep scene unchanged | everything outside the three insertions (viewpoints, the HAnim component statement, the layers block) equals the Deep file byte for byte (`test/test_layers.py`) | Confirmed |
| Bytes | scene 1,515,127 raw, 325,562 gzipped (Deep alone 685,470; the three humanoid copies add about 18 KB gzipped); graph 1,638,991 raw, 265,588 gzipped. First frame needs the scene only: 326 KB on the wire (plus X_ITE) | Confirmed |
| Boot, software GL | bird on screen in 4.0 to 5.3 s (X_ITE start about 1 s, fetch 0.2 s, parse 2.7 s, first frame 1.2 to 1.5 s); graph 0.1 s later | Confirmed here, real GPU and real network Suspected |
| Failure path | a 404 on the scene shows "Stage: fetching the bird / HTTP 404 ..." | Confirmed (e2e) |
| Frame rate | not measured on a GPU (software GL is not a bench); the fps readout in the corner shows the viewer's own number | Suspected |
| Overlay | `?ui=none`: no element of the overlay displayed (e2e) | Confirmed |
| Ladder, tour and keys | key 3 flies to the heart, Face chip flies home, Tour moves the camera and the label follows, `t` and `Shift+T` | Confirmed (e2e) |
| Heart tape | 30 scenes, 24 passed first time, 30 passed after repair; 8 failing rounds drawn red and 30 passing rounds gold, from the run's own scoreboard | Confirmed (data file); the beats on screen Likely (frames, red ping seen at the ribcage view) |
| Fan unfurl | closed on load, open after the camera enters the fan's sensor box; seen closed to open in a sequence of frames | Confirmed (frames) |
| Tender walk | the humanoid copies bend at the joints in the page (e2e: a knee and a hip change over 0.9 s); a side-view strip of the cycle shows stride, knee fold and arm swing | Confirmed (e2e, frames in `docs/frames/`) |
| Preening wave, shuttles | wired by ROUTE from timers; not seen as motion in a still, only as wired | Likely |
| Plumage and Sun read at the Face, ribcage, heart, fan and feather stops | frames in `docs/frames/` | Likely (one rig; the judge is the owner's eye) |

`node test/e2e.js` runs 19 checks, `python3 -I test/test_layers.py` 6.

## Notes for step 3 (from the planning review)

- Scale the Loom group uniformly so the ribcage radius 3.3 equals 2.4 AU (about 1.088e11 m per unit); the bird's ribcage is then the shell on the combined page (v2's shell geometry is skipped) and hover reads the same bead positions. The 0.36 Sun becomes the far child of a Sun LOD (v2's true-radius Sun the near child). Keep v2's camera-relative placement and log depth buffer; check that Earth's orbit clears the head.
- The `Loom` group sways about the scene's pivot (0.72, -0.76); pivot it on the Sun, or move Heart and the ribcage out of the swaying group, before the Sun becomes a cosmic anchor.
- LOD ranges (11 and 60) are local and survive the scale. Inline loads are keyed off ProximitySensors in the frame of what they load (village at v2's near-town threshold, Earth and Moon textures at about twice the Moon's distance); the 364 beads stay in the boot payload. The fan's unfurl already uses this pattern (a ProximitySensor starting a TimeSensor).
- Not in this build: the nebula sky and the red and blue streaming trails of frame D (only the gold and orange Blender streams are drawn), Earth and Moon.

## Known rough edges

- The cloud of 2,476 stars is dense; at the ribcage stop the gems and lattice stand out from it but share the frame with it. Sorting transparent shapes against the star cloud is not controllable in plain X3D.
- The tenders are H-Anim, but their gait is a fixed cycle (no foot planting, no terrain), and what they tend is simulated; the wing's role colours, the shuttles and the pings of the flywheel are simulated.
- The heart beats about once a second now (varying a few percent); the tape is in the order of the run's scoreboard (by category), not a time order: the run wrote its scenes in parallel.
- Close to a feather the shadowed facets read dark navy; the plumes are alpha-blended, so overlapping blades look browner than a single one.
- Tour: the fly-through is checked against the geometry by eye at the keys, not frame by frame on a GPU.
- Frame rate on a real GPU, and the blur behind cards, are unmeasured.
- Sprites keep the Deep scene's `PointShader`; the Sun's halos and the Blender orb use a billboard glow because the point sprite cannot grow that large cleanly.

## Files

| Path | What |
|---|---|
| `index.html`, `src/demiurge.css` | the page and the rail and tag styles (`gd-` prefixed) |
| `src/boot.js` | staged loader, gzip inflate, flights, rail, spline tour, tags, then the v4 hover layer |
| `tools/layers.py` | the layers (seeded, deterministic, plain X3D 4.0, no Script) |
| `tools/blender_feather.py`, `tools/feathers.py` | model, bake and export the feathers in Blender; read them back |
| `assets/feathers/` | the three exported feathers and the Blender receipt (committed) |
| `tools/blender_tender.py`, `tools/tender.py` | model the tender in Blender (armature, skinned mesh), export; read it back and hand out copies |
| `assets/tender/` | the exported H-Anim humanoid and the Blender receipt (committed) |
| `data/heartbeat/xbench-run1.json` | the validator tape the heart beats (30 scenes, committed) |
| `tools/build_bird.py` | splice the layers into the Deep scene, gzip, validate, write the receipt |
| `tools/make_artifact.py` | a flat copy for a private host (base64 text of the gzip; `../gobbler-v4/` files moved up) |
| `test/` | `test_layers.py`, `e2e.js`, `requests.js` (the runtime file list), `frames.js` |
| `docs/frames/` | frames of the page, 1527 x 923 |

Fetched or built, not committed: `data/bird/`, `out/`; the Deep build and X_ITE live in `gobbler-v4/data` and `gobbler-v4/vendor`.
