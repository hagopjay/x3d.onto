# Gobbler demiurge: the bird first

A page that boots with the bird alone: the Gobbler 3 Deep head and knowledge graph, the Sun in its chest that beats a replay of real validator runs, a Dyson ribcage of the 364 ontology classes, plumage and a tail fan modelled in Blender, weaving shuttles and a slow cinematic tour. Fly down the rail (keys 4 to 7) and the camera leaves the bird for Earth and the Moon, then the village Aurelsbrunn on it, its plaza and a villager 1.75 m tall, with a scale bar that says what the screen is showing in village metres. Earth, the Moon, the village and the villagers are modelled in Blender and load only when the camera comes near. It is a **new folder on top of `gobbler-v4/`**, which is untouched: the Deep scene is used byte for byte, and the v4 hover layer runs on top of it unchanged.

Built so far (plan steps): 1 honest loader and gzip delivery, 2 the bird-first page in the locked look, 3 the world as lazy Inlines and ladder stops 4 to 7 (done with a new Blender village, not v2's), 5 feathers made in Blender, 6 motion (tour, seeded drift, preening wave, shuttles), 7 the heartbeat (heart only), 8 the shell tenders as H-Anim humanoids made in Blender, 11 the picture-judge loop (measured: [docs/PICTURE-JUDGE.md](docs/PICTURE-JUDGE.md)). Step 9 (the tail fan lit by real glTF, USD and video exports) stays **simulated** on purpose: a real export path is the ultimate vision, the plumes are tagged accordingly. Not built: 10 music, 12 trailer, the flywheel growing the village, the eclipse stop.

```
make v4-data          # (once) the Deep build and X_ITE 16.5.1, hash-checked
make demiurge-data    # compose the bird scene, gzip it, validate with the fork       -> gobbler-demiurge/data/bird/ (not committed)
make feathers         # (only to remake the feathers; needs a Python with bpy) model + bake + export in Blender -> assets/feathers/ (committed)
make tender           # (same) the H-Anim shell tender -> assets/tender/ (committed)
make world            # (same) Earth, clouds, Moon and the village -> assets/earth/, assets/village/ (committed); make demiurge-data then writes the four lazy files and world.json into data/bird/
make test-demiurge    # layer tests (python only)
make demiurge         # serve the repo root: http://127.0.0.1:8791/gobbler-demiurge/index.html
make e2e-demiurge     # the live page in Chromium (serve first, same PORT)
```

Parameters: `?ui=none|min` (stills are `?ui=none`), `?view=face|ribcage|heart|earth|village|plaza|villager|feather|establishing`, `?seed=N` (the camera's drift and the flights' bows; the same seed repeats a take, `?seed=0` turns the randomness off, default 4), `?look=gold` (the gold-only knowledge graph, arm C of the picture-judge test), `?tourat=N` (start the tour N seconds in; a test hook: the dive to the village comes at 65 s), and the v4 ones (`?hover=<entity>&tier=2|3`, `?tune=1`, `?glass=1`).

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
| Earth and Moon | Blender icospheres, faceted and drawn unlit like the rest: Earth 5,120 faces, a cloud shell of 489 faces that turns once in 420 s, the Moon of 1,280 faces orbiting in 150 s. Day and night are **baked** from the Sun's direction (the village stands where the Sun is overhead); the Moon is counter-rotated against its orbit so its lit side keeps facing the Sun. Drawn about 1,700 times too large, the Moon about 85 times too far out, and the tag says so | `assets/earth/`, `tools/blender_earth.py`, `tools/world.py`, `tools/world_layer.py` |
| Village Aurelsbrunn | a ground cap that follows the curve of a 250 m planet, a plaza with a fountain, four roads, 8 cottages, 6 houses, 2 halls, a mill, 6 stalls, 12 lamps, 70 trees and a gold tether mast; 108 Blender objects drawn from 18 meshes (the exporter writes each mesh once and 90 of the objects as USE); face colour baked from a fixed key light with cool shadows | `assets/village/`, `tools/blender_village.py` |
| Villagers | 12 walkers on three lanes of the plaza (radius 7.4, 9.0 and 13.4 m), 1.75 m tall: the **tender bodies, shared by USE** and scaled, so the villagers are the same Blender H-Anim humanoids as the tenders on the ribcage. What they do is simulated | `tools/world_layer.py` |
| Tether | a fine gold line and a sunbeam ribbon from the tip of the village mast to the heart, with four climbers on it (simulated) | `tools/world_layer.py` |

Real plumes are drawn ready, not lit by a passing export; that wiring is the ultimate vision and the tags say so.

## Blender pipeline for the feathers

`tools/blender_feather.py` builds each feather in Blender's Python (bmesh): a quill, a vane on a 24 by 3 grid with cup, twist and a small seeded wobble (so the quads stop being flat), triangulated and flat shaded. It lights a white copy with a golden-hour rig (a warm sun lamp at 24 degrees plus a cool multiple-scattering sky), bakes direct and indirect light into corner colours with Cycles, sets the exposure so the 92nd percentile facet sits at 0.92, and exports through x3d-blender-io as X3D 4.0, one file per variant. `tools/feathers.py` reads those files back and `layers.py` places them with a Transform per plume (rotation from the plume's own axes, scale from its length and width). The page build itself does not need Blender. `assets/feathers/receipt.json` records the Blender version, the exporter commit, the script's sha256 and the file hashes.

## Blender pipeline for the tenders

`tools/blender_tender.py` builds an armature of 18 joints in Blender (the lowest H-Anim 2.0 articulation level as I remember it: humanoid_root, sacroiliac, vl5, vt6, vc4, skullbase, and left and right shoulder, elbow, wrist, hip, knee, ankle; **the joint list is from memory and has not been checked against ISO/IEC 19774-1**) and one faceted skin mesh weighted rigidly to those joints, with per-face colours from a fixed key light (gold, cool shadows). x3d-blender-io exports the armature plus its skinned mesh as an `HAnimHumanoid` (version 2.0) with an `HAnimJoint` per bone, `skinCoord`, per-joint `skinCoordIndex` and `skinCoordWeight`, and one skin Shape. `tools/tender.py` reads that file and hands out copies with a prefix on every DEF; the PhysicalMaterial is dropped so the baked face colours draw unlit like the feathers. The composed scene gets one more head statement, `<component name='HAnim' level='1'/>`, so the compose step now makes three insertions (the test checks all three and that the rest is the Deep scene byte for byte). A bug caught on the way: the first export weighted only the torso joints (new bmesh vertices have no valid index until `index_update`), so arms and legs did not bend; it shows as 0 skin indices on the limb joints in the file.

## Blender pipeline for the world

`tools/blender_earth.py` and `tools/blender_village.py` build the world in Blender's Python (bmesh) and export it through x3d-blender-io (commit d9bbf91, Blender 5.2.2 from the `bpy` wheel): the same hand as the feathers and the tenders. Face colour is baked (the Sun's direction for the planet, a fixed key light with cool shadows for the village), the exporter writes it as per-corner `ColorRGBA`, and linked duplicates become DEF and USE. `tools/village_spec.py` holds the numbers both scripts and the page share (scale, the Earth's place, the village's frame). `tools/world.py` then writes the page's four files: the PhysicalMaterial goes (the faces draw unlit, like the feathers), numbers shorten to four decimals, the exporter's navigation node goes, and the Earth export splits into planet, clouds and Moon because the page animates them separately. `assets/earth/receipt.json` and `assets/village/receipt.json` record the Blender version, the exporter commit, the script's sha256 and the file hashes; the village build is deterministic (a rebuild gives the same sha256).

**A defect the validator caught, and a wrong message from it.** The first Earth export baked some colours above 1 (up to about 1.1 by the formula for the bright ice). The X3D schema keeps `ColorRGBA` within [0, 1], a renderer simply clamps, and the fork's XSD check failed the file. Its message was wrong: it said libxml2 had stopped at its 10 MB start-tag limit, but the longest attribute was 263 KB. Bisecting the colour array found the cause (the first 100 colours pass, the 101st, with channels at 1.0059 and 1.0511, fails). libxml2 2.14.6 reports "Internal error in XML Schema validation" instead of a pattern error when such a value sits near the end of an array of 12 colours or more, and the fork turns any such error into the size message. The script now clamps the colours, and all six world files validate (below). The fork's message is worth fixing; this repo does not touch the fork.

## The zoom ladder: Earth to a villager

Stops 4 to 7 use the same rail and keys as the bird's stops. What happens between them:

- **Lazy files.** `world.json` (1.9 KB) arrives after the first frame and fills in the four stops. The planet, clouds, Moon and village files stay unloaded (`Inline load='false'`) until a ProximitySensor around each says the camera is near: its `isActive` goes through a `BooleanFilter` to the Inline's `set_load`, and the group is drawn only while the sensor is active. Nothing heavy loads at boot: the e2e test's first request list is the scene, `world.json`, the graph, the anchors and the receipt, and the four world files are requested only after key 4 is pressed.
- **The sway pauses.** The Deep scene's own slow sway (up to about 0.2 rad every 32 s about the pivot (0.72, -0.76)) moves the Sun by about 1.2 units. That is harmless at the Face and fatal at the village, which a camera 0.13 units away would lose. So at stops 4 to 7 the page pauses the sway (the TimeSensor's `pauseTime`), converts the stop's bird-frame coordinates through the frozen rotation, and flies there; any flight back to a bird stop, the Face chip or the tour resumes it.
- **The dive.** A flight that starts or ends at a world stop is geometric in its distance to the subject (an equal factor of zoom per second, eased at both ends, so more than four orders of magnitude of distance read as one smooth fall), with the camera's up vector blended into the village's local up, the near and far clip planes set every frame from that distance, and X_ITE's logarithmic depth buffer on while down there. Flights between bird stops keep the smoothstep with the seeded bow.
- **Scale, said plainly.** The village is 160 m across on a planet drawn 250 m in radius (0.1 scene units; one village metre is 4e-4 units). The real Earth has a radius of 6,371 km, so the village is about 25,000 times too large for its planet. If the 3.3-unit ribcage is the plan's 2.4 AU, one unit is about 0.73 AU, Earth is drawn about 1,700 times too large and the Moon about 85 times too far out. A scale bar at the foot of the page shows a bar and what it spans in village metres (200 m, 20 m, 2 m, 0.5 m as you fall), and the Earth, village, tether and villager tags say these numbers.

## Step 1 in this build: honest loader and gzip delivery

`src/boot.js` replaces the engine's fixed status text. Every stage names itself with bytes and seconds, and a failure prints the stage and the error text instead of a counter:

```
starting X_ITE → fetching the bird · 308 KB of 308 KB → parsing the scene · 1.37 MB of X3D → drawing the first frame → bird on screen
```

The scene ships as `gobbler4-bird.x3d.gz` and is inflated in the page (`DecompressionStream`); a published copy can carry base64 text of the gzip (`GD_CFG.enc = 'b64gz'`) for hosts that refuse binary. The graph (266 KB gzipped), the ontology block, the tag anchors and the validator receipt load **after the first frame**; the hover layer starts when the graph arrives. This ports the technique from the Constellation 2 version 3 fix (gzip on the wire, inflate in the page, a status line that says where it is); the code is new, because that fix lives in a packaged copy, not in this repo.

## Controls: four, as planned

UI level (`U`, none / minimal), Face (home view, key 1), Tour, and a right-edge rail of 8 zoom stops (keys 1 to 8), all live: 1 Face, 2 Dyson ribcage, 3 Heart, 4 Earth and Moon, 5 Village from orbit, 6 Plaza, 7 A villager, 8 A feather (stops 4 to 7 light up when `world.json` has arrived, a moment after the first frame). `T` toggles the tour and `Shift+T` opens the v4 tuning panel (the plan's key rule; the panel's own footer still says "T tune"). `Shift+F` is full screen; hold `H` hides everything. Lights out (`L`) is not wired. The v4 corner cards stay the one card style. Minimal UI also shows 19 small anchor tags: the bird's 15 (heart, ribcage, flywheel, wing, tenders, Blender, 9 export targets; tenders and mock plumes appear only within 15 units) and four for the world (Earth and Moon, Aurelsbrunn, the tether, the villagers), which carry their honest scale notes. Inside the village the bird's own tags hide.

**The tour** plays the shot list on a spline with continuous velocity (no stop at every waypoint), easing the field of view with it, and starts by flying from wherever the camera is: Establishing, Face, push-in on the eye and wattle, an orbit of the ribcage (over the head and round behind), underneath the bird and up to the tenders, the heart (watch the rings), the fan reveal (the fan unfurls), and back to the Establishing frame so the loop closes. About 85 s. When the spline reaches the Heart shot (65 s in) the tour **dives to the village**: Earth and Moon, the village from orbit, the plaza and a villager, then flies back out to the Heart shot, where the spline carries on. A slow seeded drift keeps the camera alive; flights between bird stops bow slightly off the straight line.

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
| World files validate | `earth-planet.x3d`, `earth-clouds.x3d`, `earth-moon.x3d`, `village.x3d` and the two raw exports (`assets/earth/earth.x3d`, `assets/village/village.x3d`): XSD valid, profile OK, 0 semantic errors and 0 warnings (3 to 115 info), fork `2b696f5` | Confirmed |
| World bytes | planet 609,806 B raw (106,720 gzipped), clouds 42,618 (8,338), Moon 191,742 (32,583), village 192,193 (26,335), `world.json` 1,884. All lazy: none is requested before the camera comes near | Confirmed |
| Ladder stops 4 to 7 | e2e: key 4 stops 0.880 from Earth (planned 0.88), key 5 0.131 from the village site (planned 0.13), key 7 puts the camera 1.2 m above the plaza's tangent plane (1.5 m above the ground under it); the sway rotation holds while down there and moves again after the Face chip; villagers shown and walking (one villager's rotation and a knee joint change over 1.5 s); the frame at stop 7 is not black; no page errors | Confirmed (software GL, X_ITE 16.5.1) |
| Tour dive | e2e: started 64 s in, the tour pauses the sway and brings the camera within 0.2 of the village site, then flies back to the Heart shot with the tour still on | Confirmed |
| Colour range defect | the first Earth export had colours up to about 1.1, the fork's XSD check failed it, bisecting the array found the 101st colour; clamped in Blender, valid. The fork's message blamed a size limit, which was wrong (see the world pipeline above) | Confirmed (fork `2b696f5`, lxml 6.1.3, libxml2 2.14.6) |
| A validator gap | a ROUTE placed before the node it names passes the fork (XSD valid, 0 semantic errors, profile OK); X_ITE 16.5.1 warns "XML Parser: Unknown named or imported node", **drops the ROUTE** and loads the scene (a 5-line scene shows both) | Confirmed (fork `2b696f5`, X_ITE 16.5.1). Whether the specification calls it an error: Suspected |
| Picture judge | 3 arms of 12 stills, about 35 votes each: baseline 3.67, with the edits it asked for 3.56, gold-only graph 3.43 (mean score of four criteria, 1 to 10); the judge's own repeat noise is about 0.1 on the mean, so the edits are not detectable and the gold graph is slightly lower. 83 per cent of its top fixes ask for less density, which the owner does not want | Confirmed as measured; "gold graph slightly lower" Likely ([docs/PICTURE-JUDGE.md](docs/PICTURE-JUDGE.md)) |
| Preening wave, shuttles | wired by ROUTE from timers; not seen as motion in a still, only as wired | Likely |
| Plumage and Sun read at the Face, ribcage, heart, fan and feather stops | frames in `docs/frames/` | Likely (one rig; the judge is the owner's eye) |

`node test/e2e.js` runs 34 checks (all pass), `python3 -I test/test_layers.py` 9.

## What step 3 did with the planning notes

- **Scale.** The plan's note was to scale the Loom group so the ribcage radius 3.3 equals 2.4 AU. The page keeps the bird's own coordinates instead, puts Earth, the Moon and the village inside the Loom group at display sizes, and says so in the tags (see the ladder section). The 0.36 Sun stays one Sun; there is no second, true-radius Sun for a near LOD.
- **The pivot.** The `Loom` group still sways about the scene's pivot (0.72, -0.76); rather than move the heart, the page pauses the sway while the camera is at stops 4 to 7.
- **Lazy loading** is by ProximitySensor and `Inline`, as in the fan's unfurl (a ProximitySensor starting a TimeSensor); the 364 beads stay in the boot payload.
- **Still open:** the nebula sky and the red and blue streaming trails of frame D (only the gold and orange Blender streams are drawn), the eclipse stop, the flywheel growing the village from its own validated scenes, a second Sun LOD, music (step 10) and the trailer (step 12).

## Known rough edges

- The cloud of 2,476 stars is dense; at the ribcage stop the gems and lattice stand out from it but share the frame with it. Sorting transparent shapes against the star cloud is not controllable in plain X3D.
- The tenders are H-Anim, but their gait is a fixed cycle (no foot planting, no terrain), and what they tend is simulated; the wing's role colours, the shuttles and the pings of the flywheel are simulated.
- The heart beats about once a second now (varying a few percent); the tape is in the order of the run's scoreboard (by category), not a time order: the run wrote its scenes in parallel.
- Close to a feather the shadowed facets read dark navy; the plumes are alpha-blended, so overlapping blades look browner than a single one.
- Tour: the fly-through is checked against the geometry by eye at the keys, not frame by frame on a GPU.
- Frame rate on a real GPU, and the blur behind cards, are unmeasured. Nothing here quotes a software-GL frame rate: the readout in the corner of the page shows the viewer's own.
- At stops 4 and 5 the knowledge graph's beads and edges stay in the frame, because the bird's cosmos is the village's sky; it is by design, and it is the picture judge's main complaint.
- The village cap seen from orbit is a round green patch with a plaza target on a faceted Earth; it is the village, drawn 25,000 times too large for its planet, and the tag says so.
- The dive passes close to the tether mast on its way to the plaza; the villagers walk circles on three lanes and do not enter buildings; the four villagers of a lane share one gait clock, so their legs move in step and only their places on the lane differ.
- The bird holds still while the camera is at stops 4 to 7 (the sway is paused), and starts swaying again from where it stopped when you fly out.
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
| `tools/village_spec.py` | the numbers the Blender world scripts and the page share: scale, Earth's place, the village frame |
| `tools/blender_earth.py`, `tools/blender_village.py` | model Earth, clouds, Moon and the village in Blender, export through x3d-blender-io |
| `assets/earth/`, `assets/village/` | the exported X3D and the Blender receipts (committed) |
| `tools/world.py`, `tools/world_layer.py` | read the exports and write the four lazy files; the world layer spliced into the Loom group (sensors, Inlines, tether, villagers, stops, tags) |
| `tools/build_bird.py` | splice the layers into the Deep scene, gzip, validate, write the receipt, the lazy world files and `world.json` |
| `docs/PICTURE-JUDGE.md` | the picture-judge test: method, three arms, noise, what it could and could not tell |
| `tools/make_artifact.py` | a flat copy for a private host (base64 text of the gzip; `../gobbler-v4/` files moved up) |
| `test/` | `test_layers.py`, `e2e.js`, `requests.js` (the runtime file list), `frames.js` |
| `docs/frames/` | frames of the page, 1527 x 923 (9 to 13: the ladder stops 4 to 7, frame 13 with the minimal UI and the scale bar) |

Fetched or built, not committed: `data/bird/`, `out/`; the Deep build and X_ITE live in `gobbler-v4/data` and `gobbler-v4/vendor`.
