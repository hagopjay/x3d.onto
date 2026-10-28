# Gobbler demiurge, step 2: the bird first

A page that boots with the bird alone: the Gobbler 3 Deep head and knowledge graph, the Sun in its chest, a Dyson ribcage of the 364 ontology classes, gold wireframe plumage and the Blender tail fan. The village and the solar system are not here yet (steps 3 and later of the integration plan). It is a **new folder on top of `gobbler-v4/`**, which is untouched: the Deep scene is used byte for byte, and the v4 hover layer runs on top of it unchanged.

```
make v4-data          # (once) the Deep build and X_ITE 16.5.1, hash-checked
make demiurge-data    # compose the bird scene, gzip it, validate with the fork       -> gobbler-demiurge/data/bird/ (not committed)
make test-demiurge    # layer tests (python only)
make demiurge         # serve the repo root: http://127.0.0.1:8791/gobbler-demiurge/index.html
make e2e-demiurge     # the live page in Chromium (serve first, same PORT)
```

Parameters: `?ui=none|min` (stills are `?ui=none`), `?view=face|ribcage|heart|feather|establishing`, and the v4 ones (`?hover=<entity>&tier=2|3`, `?tune=1`, `?glass=1`).

## Look (locked 28 Oct: B's facets, lots of D)

| Part | What it is | Source of the shape |
|---|---|---|
| Head | the faceted Deep head, unchanged (B) | Gobbler 3 Deep scene |
| Heart | the Sun in the chest: a shader sphere (granulation, limb darkening) with two glows; idles at about 3.4 s a breath, **display only** | `tools/layers.py` |
| Ribcage | lat/lon gold lattice, 364 faceted gem beads (one per class, green = new in 4.1), three domain rings turning slowly | x3d.onto `data/explorer.json`: latitude from class depth as in v2; **longitude respaced evenly** (v2's own angles stack classes into strings) |
| Flywheel | a ring of 8 stations around the heart with a running pulse (display only) | layers.py |
| Tenders | 10 faceted mannequins walking the lattice, points of light beyond 5 units; **placeholders**, H-Anim is step 8 | layers.py |
| Wing | 10 primaries, one per orchestrator role; a role colour shows while that role "works" (**simulated**, staggered clocks) | layers.py |
| Tail fan | 18 plumes grown from the Blender root orb; streams from the graph converge on it with 5 running pulses. 3 plumes are real Blender paths (glTF, USD, video) and 6 are outline-only **mocks** (O3DE, ParaView, 3D Slicer, Unity, Defold, IFC), all tagged | layers.py |

Every plume and primary is an `LOD` with three levels (full barbs, faceted outline, spine and tip), switching at 11 and 60 units. The faceted plumes are procedural stand-ins: step 5 replaces them with Blender-made feathers through the blenderizer. Real plumes are drawn ready, not lit by a passing export; that wiring is step 9, and the tags say so.

## Step 1 in this build: honest loader and gzip delivery

`src/boot.js` replaces the engine's fixed status text. Every stage names itself with bytes and seconds, and a failure prints the stage and the error text instead of a counter:

```
starting X_ITE → fetching the bird · 239 KB of 239 KB → parsing the scene · 1.15 MB of X3D → drawing the first frame → bird on screen
```

The scene ships as `gobbler4-bird.x3d.gz` and is inflated in the page (`DecompressionStream`); a published copy can carry base64 text of the gzip (`GD_CFG.enc = 'b64gz'`) for hosts that refuse binary. The graph (266 KB gzipped), the ontology block, the tag anchors and the validator receipt load **after the first frame**; the hover layer starts when the graph arrives. This ports the technique from the Constellation 2 version 3 fix (gzip on the wire, inflate in the page, a status line that says where it is); the code is new, because that fix lives in a packaged copy, not in this repo.

## Controls: four, as planned

UI level (`U`, none / minimal), Face (home view, key 1), Tour (a slow flight over the shot list), and a right-edge rail of 8 zoom stops (keys 1 to 8). Live stops: 1 Face, 2 Dyson ribcage, 3 Heart, 8 A feather. Stops 4 to 7 (Earth and Moon, village from orbit, plaza, a villager) show dashed and "next step". `Shift+F` is full screen; hold `H` hides everything, `T` opens the v4 tuning panel. Lights out (`L`) is not wired in this step. The v4 corner cards stay the one card style. Minimal UI also shows 15 small anchor tags (heart, ribcage, flywheel, wing, tenders, Blender, 9 export targets); tenders and mock plumes appear only within 15 units.

## Measured (X_ITE 16.5.1 npm package, unpatched, full Chromium 1243 on SwiftShader software GL, local server, 1280 x 800 and 1527 x 923)

Grades: **Confirmed** = reproduced by a test or tool output in this folder; **Likely** = follows from what was seen; **Suspected** = not measured.

| Claim | Result | Grade |
|---|---|---|
| Composed scene validates | XSD valid, profile Immersive OK, 0 semantic errors and 0 warnings (36 info), validator x3d_mcp fork `2b696f5` | Confirmed |
| Deep scene unchanged | everything outside the two insertions equals the Deep file byte for byte (`test/test_layers.py`) | Confirmed |
| Bytes | scene 1,147,882 raw, 239,417 gzipped (Deep alone 685,470); graph 1,638,991 raw, 265,588 gzipped. First frame needs the scene only: 239 KB on the wire (plus X_ITE), against 2,324,461 raw for scene plus graph | Confirmed |
| Boot, software GL | bird on screen in 4.8 to 5.8 s (X_ITE start about 1 s, fetch 0.2 s, parse 2.6 s, first frame 1.5 to 1.8 s); graph 0.1 s later | Confirmed here, real GPU and real network Suspected |
| Failure path | a 404 on the scene shows "Stage: fetching the bird / HTTP 404 ..." | Confirmed (e2e) |
| Frame rate | 3 to 5 fps on software GL; real GPU not measured | Suspected |
| Overlay | `?ui=none`: no element of the overlay displayed (e2e) | Confirmed |
| Ladder and tour | key 3 flies to the heart, Face chip flies home, Tour moves the camera and the label follows | Confirmed (e2e) |
| Gold wireframe plumage and the Sun read at the Face, ribcage, heart and feather stops | frames in `docs/frames/` | Likely (one rig, one judge: the owner's eye) |

`node test/e2e.js` runs 17 checks, `python3 -I test/test_layers.py` 6.

## Known rough edges

- The cloud of 2,476 stars is dense; at the ribcage stop the gems and lattice stand out from it but share the frame with it. A dimmed chest cavity behind the Sun was considered and not built: sorting transparent shapes against the star cloud is not controllable in plain X3D.
- Tenders are boxes, not H-Anim; the wing's role colours and all pulses are simulated; the plume facets are alpha-blended and look brown where they overlap.
- Frame rate on a real GPU, and the blur behind cards, are unmeasured.
- Sprites keep the Deep scene's `PointShader`; the Sun's halos and the Blender orb use a billboard glow because the point sprite cannot grow that large cleanly.

## Files

| Path | What |
|---|---|
| `index.html`, `src/demiurge.css` | the page and the rail and tag styles (`gd-` prefixed) |
| `src/boot.js` | staged loader, gzip inflate, flights, rail, tour, tags, then the v4 hover layer |
| `tools/layers.py` | the layers (seeded, deterministic, plain X3D 4.0, no Script) |
| `tools/build_bird.py` | splice the layers into the Deep scene, gzip, validate, write the receipt |
| `tools/make_artifact.py` | a flat copy for a private host (base64 text of the gzip; `../gobbler-v4/` files moved up) |
| `test/` | `test_layers.py`, `e2e.js`, `requests.js` (the runtime file list), `frames.js` |
| `docs/frames/` | six frames, 1527 x 923 |

Fetched or built, not committed: `data/bird/`, `out/`; the Deep build and X_ITE live in `gobbler-v4/data` and `gobbler-v4/vendor`.
