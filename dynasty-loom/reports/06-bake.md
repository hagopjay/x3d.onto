# 06 The Blender bake path ("blenderizer") for the genealogy scene

Grades: **Confirmed** means reproduced here by the tool named; **Likely** follows from what was seen; **Suspected** is not measured.

Tools, as run: Blender 5.2.3 LTS (PyPI `bpy` wheel, Python 3.13, CPU, 4 cores); x3d-blender-io `d9bbf91` (the commit the demiurge receipts name); the x3d_mcp fork validator at `2b696f5` (remote HEAD, the commit in the demiurge README) and at `acdf5c4` (the shared checkout, ten days older); x3d.py 4.0.65.7; lxml 6.1.3 with libxml2 2.14.6; X_ITE 16.5.1 from npm, served locally; Chromium 153.0.8010.12 (Playwright 1.63.0) on SwiftShader. These are the demiurge's own versions, except Blender 5.2.3 instead of 5.2.2.

## 1. What deserves baked light, a shader, or nothing

One fact decides most of this: **the family orb turns.** `CosmosScene.tsx` rotates the orb group by 0.0015 rad per frame and slerps it to "present" a selected node (roths3, lines 513-525). Confirmed by reading the source. So everything parented to the orb is a mover in the recipe's sense: a baked light direction is right at one angle only. Static set pieces therefore go in a world-fixed Stage group, outside the orb.

| Element | Treatment | Why |
|---|---|---|
| Loom frame and plinth | **Cycles bake** (built, below) | Static and large. Contact shadows and bounce are what sell it. |
| Five-arrows crest | **Cycles bake, in the same bake as the loom** (built) | Static. Baking them together lets it cast onto the lintel. |
| Branch-city dioramas (Frankfurt, Vienna, London, Naples, Paris), and the Judengasse house inside Frankfurt | **Cycles bake**, same rig, one bake per diorama | Static. Far apart, so no cross-shadows are lost by baking separately. |
| Portrait bezels and plinths on the orb (18) | **Bake that does not depend on rotation:** uniform world, no sun (an occlusion bake), times the tenders' fixed warm/cool key in local space | It turns with the orb. Light from a uniform world is the same at every rotation, so one mesh can be DEF'd once and USE'd 18 times. The village trap (lost sharing) does not bite. Likely; not built. |
| Orb shell | **Shader**: fresnel rim plus breathing | Its look depends on the view. |
| Selection highlight, thread pulses | **Shader** (a `time` field from a TimeSensor ROUTE; one draw call for all threads) | They change over time. |
| Threads, portraits, generation rings, labels, starfield | **Flat/unlit** (emissive Color, unlit textures, Text in a Billboard, PointSet) | They glow or carry their own picture; light would only muddy them. |

The orb is left out of the bake as an occluder. Its shell is 8% opaque and it turns. Likely.

## 2. Asset specifications

**Planning ratio, measured.** A baked page file costs **26 to 34 bytes per face gzipped**: loom 25.6, crest 31.7, the village 33.7 (330,180 bytes over 9,790 faces in its README). The same meshes with flat per-corner albedo cost 9.9 (loom) and 11.4 (crest). **So the bake multiplies bytes by 2.6 (loom) to 2.8 (crest).** Confirmed (`page.json`, gzip level 9).

| Asset | Faces (budget) | Shapes | Gzipped (budget) | Loading |
|---|---|---|---|---|
| Loom + plinth | **4,650 built** (≤ 5,000) | 2 (Loom, Base) | **119.2 KB built** (≤ 130 KB) | `Inline load='false'`; the boot script sets `set_load` after the first frame (the demiurge's world.json timing) |
| Crest | **672 built** (≤ 800) | 1 | **21.3 KB built** (≤ 25 KB) | With the loom. Kept as its own file so it can be reused. |
| Diorama ×5 | ≤ 2,500 each | 2 each (Ground, Buildings) | ≤ 85 KB each | One ProximitySensor per site → BooleanFilter → `set_load`; the group is shown only while active |
| Judengasse house | ≤ 900, inside Frankfurt's 2,500 | (in Frankfurt) | (in Frankfurt) | With Frankfurt |
| Portrait bezel | ≤ 160 | 1, used 18 times | ≤ 6 KB | Boot |
| Shell, threads, rings, labels | primitives, 28 polylines | ~5 | ≤ 10 KB | Boot |

Boot then stays near 20 KB gzipped plus thumbnails. The loom and crest add 140 KB after the first frame; dioramas add up to 425 KB, and only near their sites. Likely: these are budgets, except the built rows. The diorama sites I suggest: satellite plinths at radius about 95 along the five branch azimuths (0, 72, ... degrees, the page's `BRANCH_POSITIONS`). Lazy wiring follows `world_layer.py`, with ROUTEs written after the nodes they name:

```xml
<ProximitySensor DEF='ParisSense' center='…' size='90 60 90'/>
<Group DEF='ParisGroup' visible='false'><Transform translation='…'><Inline DEF='ParisInline' load='false' url='"dioramas/paris.x3d"'/></Transform></Group>
<BooleanFilter DEF='ParisLoad'/>
<ROUTE fromNode='ParisSense' fromField='isActive' toNode='ParisLoad' toField='set_boolean'/>
<ROUTE fromNode='ParisLoad' fromField='inputTrue' toNode='ParisInline' toField='set_load'/>
<ROUTE fromNode='ParisSense' fromField='isActive' toNode='ParisGroup' toField='set_visible'/>
```

## 3. The generator, run end to end

Everything is in `proto/bake/`:

- `blender_loom.py` builds the asset.
- `loombake.py` holds the `bpy` half: builders, the recipe's rig, the probe, bake, finish, export, receipt.
- `loomkit.py` holds the half with no `bpy`: finish formulas, clean-up, read-back, and a self-test that colours stay in [0, 1].
- `blenderize.py` is the CLI.
- `fork_check.py`, `exporter_check.py` and `look.cjs` are the gate.
- `stops.json` lists the camera stops.

**The asset.** A vertical tapestry loom frames the orb: two posts on feet, a warp beam with its roll, a cloth beam with red cloth, ratchet wheels, handles and a lintel. The orb hangs in the **shed**: 21 warp threads, alternating in front of and behind it. Each is drawn taut round a clearance sphere of radius 43.5 (tangent, arc, tangent), outside the shell at full breath (35 × 1.15 × 1.015 = 40.86). It stands on a two-step pentagonal plinth whose faces look toward the five branch cities, each marked by a brass roundel. The crest stands on the lintel: five gold arrows bound by a band, points down, on a red heater shield ("zum roten Schild"). It is a **stylised device, not the blazoned arms**, and leans back 18 degrees so its face also takes the high key.

**Recipe, followed exactly**, every value in the receipt:

- bmesh merged into 3 meshes, albedo in `Alb`.
- The recipe's Cycles rig, sun and sky unchanged (seed 11).
- A `VERTEX_COLORS` DIFFUSE bake, direct + indirect, no colour pass.
- The finish in the recipe's order. Exposure is 0.5156, from the 70th-percentile plinth-top corner (the village's was 0.5186). Only the band has a glow share (0.35).
- Export as X3D 4.0, then the `world.py` clean-up: 3 decimals, `ColorRGBA` to `Color`, and no material, background or navigation node.

Confirmed (`out/receipt.json`). Light after exposure:

| Mesh | p50 | p95 |
|---|---|---|
| Base | 0.916 | 1.029 |
| Loom | 0.395 | 1.087 |
| Crest | 0.546 | 1.068 |

Display channels land in [0.009, 0.967].

**The gate passes on all 8 files** (4 exports and 4 page files, flat and baked). Confirmed by each tool named:

- `xmllint`: well-formed.
- Both fork commits: XSD valid, profile OK, 0 semantic errors and 0 warnings (3 to 6 info notes: unused DEFs, and a missing Viewpoint, which an Inlined file does not need).
- The exporter's own check through x3d.py: 0 errors and 0 warnings.
- Read-back: one colour per point, channels in [0, 1]; `solid` true on the baked files (the flat comparison files keep the exporter's false).
- X_ITE 16.5.1 at 7 stops: zero console problems, both Inlines `complete` every time, no black frame. Loads took 0.75 to 1.0 s on software GL, which is not a benchmark.
- **The console check has teeth.** A negative control was caught on all three counts: an undeclared `DepthMode`, a ROUTE written before its node ("Unknown named or imported node 'Clock'"), and a missing Inline (404, state `failed`). Confirmed.

**The clean-up matters.** It cut the loom's gzip from 211,720 to 119,246 bytes (44%). Confirmed.

**Look (frames in `out/frames/`, before and after).** After the bake, the arrows stand in relief with soft shadows on the field. The shield shadows the lintel, the rolls read as lit cylinders, and the feet and roundels sit in contact shadows. Before the bake, the same stops look like paper cut-outs. Confirmed (frames); whether it looks right is the owner's eye.

**Two things the Look sent back to the script:**

- **A starburst on the plinth.** The top's centre was a fan of 80 sliver triangles, and per-corner light interpolated across slivers drew streaks. I rebuilt the top as stitched rings, with points per edge growing with the ring, so cells stay near-square. The streaks are gone. Confirmed, before and after frames.
- **The wide stop cropped the plinth.** It moved back; stops are gate input, not generator output.

One composition issue is left for art direction. **At the page's own default camera (0, 25, 110) the front sheet of the warp hangs in front of every portrait.** Either drop the front sheet (about 700 faces, about 18 KB) or open the default camera to about 260. Confirmed (`look_page_default_after.png`).

## 4. Findings for the recipe

1. **Adaptive sampling caps the bake (new).** Blender 5.2.3's default is adaptive on, threshold 0.01. Measured on a flat white plane, where any spread across corners is pure noise:

   | Samples | Adaptive on | Adaptive off |
   |---|---|---|
   | 96 | 1.30% | 1.25% |
   | 384 | 1.00% | 0.32% |
   | 1536 | 0.99% | 0.07% |

   With it on, "384 samples" in a receipt overstates the work. The village script never sets this flag, so its 384 was Likely capped the same way. I set `use_adaptive_sampling = False` and record it in the receipt. That raised this bake from 6.9 to 19.0 s. It also cut the plinth's exported points by 24% (5,075 to 3,851) and the loom's gzip by 8.6%. Confirmed (`noise_probe2.py`, both runs' read-backs). Why identical geometry exports fewer points: Suspected (more corners baked identical and merged). The 1% noise was not visible in the crest frames: red-channel sd was 9.13 with it on and 9.22 off. Confirmed (crops).
2. **Slivers and fans show the per-corner light as streaks.** A surface that receives shadows needs near-square cells; a shadow smaller than a cell blurs into it. Confirmed (frames).
3. **The probe reproduces the README in part.** Sky 1.0 lights the plane at 3.43 (README 3.4). The key at 5 gives 1.128 in luma, which is 1.30 × 0.865, the key colour's own luma. So the README's 1.3 matches if its probe key was white. That puts sky 0.25 against the key at 0.76, not "two thirds". Measured values Confirmed (probe); the explanation Likely (arithmetic).
4. **The shell trap is live in the source.** The page allows `minZoom` 30, inside the shell's radius of 40.25. An X3D port must hold the camera outside it. Confirmed (source numbers).
5. **Smaller items:**
   - The exporter stamps "v2.6.1" from `bl_info` while its manifest says 2.6.4. Confirmed (both files).
   - x3d.py greets on stdout, which breaks JSON tooling. Confirmed.
   - The dataset has a parent link to a missing node (`victor -> charles`), so one thread has no end. Confirmed (regex count: 18 members, 24 parent links, 4 spouse pairs).

## 5. Sharing it with the Mashtots thread: a reusable `blenderize` CLI

I could not read the Mashtots thread: it is not among this project's threads, and no local file mentions it. Confirmed (`list_threads`, grep). The user's words ask for shared "modeling and validation flywheel tech, and blenderizer", so the interface below is generic.

- **Commands:**
  - `blenderize run GEN.py --out DIR [--preview|--samples N] [--probe]`
  - `page DIR`
  - `gate DIR --stops STOPS.json`
  - `verify DIR`
  - `all ...`
- **Inputs:**
  - A generator: Python that imports `loombake`, tags its exposure-reference faces `ground`, and writes exports plus `receipt.json`.
  - A stops file: name, eye, target, Inlines per DEF, stand-in orb on or off, before/after.
  - Tool locations from environment variables: `BLENDERIZE_BPY`, `_IO`, `_MCP` (several validator checkouts, each with its own Python), `_XITE`.
- **Outputs, beside the asset:**
  - The exports, and `page/` (what the page Inlines).
  - `receipt.json`: Blender version, exporter commit, sha256 per script, the full bake block (samples, adaptive flag, key, sky, exposure and rule, floor, shoulder, probe, light percentiles per mesh, display range), faces per mesh, bytes and sha256 per file.
  - `page.json`: bytes, gzip bytes, hash and faces per page file.
  - `gate.json`: each check named by commit or version, and a verdict.
  - `frames/`.
- **`verify`** applies the recipe's rule: an edited script is reported, never re-receipted. It already flags the earlier run (`out_adaptive_on`: `loombake.py` "CHANGED since the receipt"). Confirmed.

For Mashtots, a letterform or statue generator reuses `Part`/`Bank`, the rig, `finish` and the gate unchanged. Static letters bake; letters that move take the fixed key or the uniform-world bake. Likely.

Open for the owner:

- Where the shared code should live. The exporter repo's `tools/` already runs tests under the `bpy` wheel.
- Whether the shared validator checkout should move to `2b696f5`. Both commits agree on these files.

**Not done:**

- The dioramas, house and bezels are specified, not built.
- No GPU frame rate. SwiftShader is not a bench.
- History unchecked: the name's origin "zum roten Schild" is Likely; that the family's house from 1784 was "zum grünen Schild" is Suspected, from memory. These are for the history analyst.
- Taste is the owner's call.
