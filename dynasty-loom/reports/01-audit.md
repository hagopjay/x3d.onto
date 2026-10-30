# 01 · Audit of the genealogy "Cosmos" code and its history

Paths are relative to the zip root `scratchpad/geneology_src/geneology/`.

**Basis tags:**
- **[read]**: file:line read by eye.
- **[audit]**: `scratchpad/audit_work/data_audit.py`, which parses the data literals with regexes under `python3 -I`.
- **[sim]**: `…/audit_work/orb_select_sim.py`, a numpy re-implementation of the layout and selection maths.
- **[grep]**: string search of the dist bundles.
- **[recall]**: model knowledge, not checked against Wikidata.

Nothing from the zip was executed, installed or rendered, and no `.env.local` was opened. No claim here has a renderer behind it, so any runtime claim is at most Likely.

## 0. Stop first: an API key ships in the zip (Confirmed, [grep])
- `roths/dist/assets/index-CxALOsYa.js:4315` and `roths2/dist/assets/index-DkHceFZh.js:4315` both contain `new GoogleGenAI({apiKey:"AIza…"})` with a literal Google key.
  - It is the same key in both (sha256 prefix 5037dc906a68; not printed).
  - Cause: `vite.config.ts:13-16` uses `define` to inline `GEMINI_API_KEY`.
- The zip also holds three `.env.local` files.
- **Rotate the key.** Never publish `dist/` or the zip. The X3D build should need no key.

## 1. Evolution map (file mtimes, Jan 2026)

| Version | When | What changed | Builds |
|---|---|---|---|
| `rothschilds.html` | 05 19:17 | Standalone three r128 page with 26 people. Generation layers with random z, glass spheres, auto-orbit, click info. | yes |
| `rothsch2.html` (= `roths/collateral/` copy) | 05 19:27 | Adds branches and notes, generation rings, stars, nebula and particles, labels, curved edges with flow particles, hover with edge highlight, search, generation filter, a timeline that dims people not alive in the year, focus on node or generation, labels toggle, zoom. | yes |
| AI Studio port (`roths/*` 19:41) | 05 19:41 | React 19, Vite 6, three 0.182, @google/genai. `family.ts` has 18 people with Wikipedia URLs. Adds a 5-stop tour and Gemini text and portraits. | n/a |
| `roths - Copy` | 05 20:09–20:21 | Adds 3 JSON trees (Rothschild 9, Habsburg 1, Darwin–Wedgwood 2) as a ring of constellations. A 748-line scene: portrait discs (monogram, then Wikipedia thumbnail), custom damped orbit, pan and zoom, hover, AI portrait on the node, nebula, edge particles. `repopack-output.txt` holds these same sources, so this is the code all three expert reviews saw. | L |
| `roths` | 05 23:36 | `v2.notes.md` picks the [model] plan of one orb per dataset. `App.tsx` gets the Phase-0 fixes. The Gemini client becomes lazy and guarded. **`components/CosmosScene.tsx` is missing**; `dist/` dates from 20:18. | **no** |
| `roths2` ("Copy of…") | 06 00:06–00:57 | Single dataset. A 293-line scene derived from [model]: per-orb state, spherical coordinates, raycasting against the canvas rectangle, quaternion "presentation" recomputed every frame. No labels, spouse edges, particles, camera controls, resize, hover or reset. Plans: [model] `Optimize` doc, `Buildnotes.md`. | L |
| `roths3` ("Copy of Copy of…") | 06 02:02–02:13 | A 778-line scene: the [model] single orb (same ORB_CONFIG numbers, geodesic tubes, labels at 1.25R, breathing shell) plus the [model] doc's 6 utility files. Restores orbit, zoom, orb drag, hover, auto-rotate and reset. Adds JSON import/export with localStorage. Only the Rothschild dataset. | L (tsc fails, 3a-10) |

**Most advanced: roths3** (Confirmed, [read]).

**Canonical: none.**
- **Code:** roths3 is the reference, but it cannot be ported as is (§3a). roths2 is the only React tree without the rebuild storm (3a-1), because its scene effect depends only on `[graphs]`.
- **Behaviour spec:** `rothsch2.html` is the most coherent one-file spec. The layout spec is the roths3/[model] formula.
- **Data:** four copies (26, 26, 18 and 9 people), all different and all with errors.

## 2. Feature inventory → X3D / X_ITE

"External API" in the table means the pattern already in `x3d.onto/gobbler-demiurge/src/boot.js`: `getNamedNode` (:122), ProximitySensor with `addFieldCallback` (:182-184), Viewpoint `set_bind` (:293).

| Feature (best source) | X3D / X_ITE path | Verdict |
|---|---|---|
| Spherical layout: generation→latitude, branch→longitude, birth-year jitter (roths3 :176-213) | The generator writes each `Transform.translation`. Add a separation pass and derive branch angles from the data. | Carry |
| Orb shell with breathing (roths3 :388-399) | Sphere plus transparent Material. Breathing: TimeSensor → PositionInterpolator → `set_scale`. | Carry |
| Geodesic parent and spouse edges (roths3 :285-314) | The generator emits slerp polylines at 1.02R/1.03R as IndexedLineSet (or Extrusion tubes) inside the orb Transform. | Carry |
| Flow particles along edges (roths3 :316-338) | One TimeSensor drives N PositionInterpolators with cyclically shifted keys. | Rebuild or drop (frame noise for the picture judge) |
| Portrait discs, rings, monograms (Copy :91-137) | Billboard (`axisOfRotation 0 0 0`) holding an IndexedFaceSet disc and an ImageTexture. Disk2D would need Geometry2D level 2, outside Immersive. Monograms baked. | Carry |
| Wikipedia thumbnails fetched at runtime, plus caches (roths3 `utils/`) | Fetch at build time. URL, Commons licence and sha256 go in the receipt; the scene uses local files. | Rebuild |
| Labels with name and years (roths3 :248-282) | Billboard plus Text/FontStyle as a child of the person, so one Switch hides both. | Carry |
| Hover tooltip and edge highlight (rothsch2 :1311-1381) | A TouchSensor per person. `addFieldCallback('isOver')` drives an HTML tooltip. | Carry (external API) |
| Click → side panel (all Apps) | `touchTime` callback opens an HTML panel fed by JSON the generator emits. | Carry (external API) |
| Selection "presents" the node: the orb turns it toward the camera ([model] doc; roths3 :514-535) | The generator precomputes a target SFRotation per person. On select: set OrientationInterpolator `keyValue [current,target]` and `startTime`. | **Rebuild** (3a-6) |
| Custom orbit, pan and zoom (Copy :534-601) | NavigationInfo `EXAMINE` and `centerOfRotation`. | Drop the code |
| Drag to rotate the orb (roths3 :631-639) | A SphereSensor next to the shell, `rotation_changed` routed to a drag Transform. Node TouchSensors sit deeper in the tree, so they keep receiving clicks. | Carry (native) |
| Auto-rotate, toggle, reset | Looping TimeSensor → OrientationInterpolator → spin Transform. `pauseTime`/`resumeTime` toggle it; `set_bind` resets. | Carry |
| Generation filter (rothsch2 :1453-1477) | One Switch per person and per edge. The external API sets `whichChoice` from a table the generator emits. | Carry (external API) |
| Timeline year (rothsch2 dims the not-alive; React only hides the unborn) | (a) The slider sets `transparency` through the external API. (b) A ROUTE-only time-lapse: one TimeSensor drives a ScalarInterpolator per person, with step keys at birth and death. | Carry; (b) is loom-native |
| Search (rothsch2 :1249-1286) | HTML input; select by id. | Carry (external API) |
| 5-stop tour; its titles and descriptions are never shown (`constants.tsx`) | Named Viewpoints with a tour camera, as in boot.js:250-316. HTML captions. The stops become the frame shot list. | **Carry (strong)** |
| Multiple datasets: ring (Copy), one orb each (roths2), sectors of one orb (roths3) | One generated `.x3d` and receipt per dataset, combined with Inline and Switch, as `v2.notes.md` decided. | Rebuild; drop the stubs |
| Stars and nebula | Background plus a seeded PointSet. | Carry (seeded) |
| Gemini text; AI portrait on the node | Offline only, with provenance `model_recall` and grade Suspected. A generated likeness of a real person is not evidence. | Drop at runtime |
| Import/export, localStorage, performance monitor, object pool | A JSON schema and validator in the generator. | Drop |

## 3. Defects (file:line)

### 3a. roths3, the would-be base
1. **Rebuild storm** (Confirmed, [read]). `App.tsx:124,133` pass inline callbacks, and `CosmosScene.tsx:729-743` lists them as dependencies.
   - Every App render tears the scene down: a new WebGLRenderer, and the camera reset to (0,25,110) (:359-364).
   - Renders happen on every hover, every mousemove while hovering (App :112-118), every slider tick and every AI reply. `React.memo` (:778) is defeated.
   - Likely result: flicker and lost WebGL contexts (L).
   - Inherited from `roths - Copy` (:627, App :109) and from [model]'s own App (`Expert.v2.[model].md:1432` vs :1161).
2. **Filters silently undone** (Confirmed, [read]). The filter effect (:754-766) does not re-run after a rebuild, which shows every node again. The next hover clears the generation and year filters while their buttons still show as active.
3. **Hidden labels never return** (Confirmed, [read]). :764 reads `labels.get(id)?.visible && (…visible = visible)`, so a hidden label is never set visible again.
4. **Edges and particles never filtered** (Confirmed, [read]). They are created at :285-339 and not tracked.
5. **Any UI click closes the side panel** (Confirmed by reading; runtime L). The pointerup handler is on `window` (:651-669, :695). A click on any HTML control raycasts into the scene, and with nothing behind it calls `onNodeSelect({globalId:'',member:null})`. That includes the AI Portrait button, the slider and the filters. `dragDistance` is only reset by pointerdown on the canvas (:593-598).
6. **Selection drifts to the pole** (L on screen; Confirmed in [sim]).
   - :514-535 retarget the orb every frame to the camera's +Z axis, while the camera chases node + 15·radial + 2·Y.
   - The selected node drifts to the north pole and the camera ends up looking straight down: polar angle 13–27° at 30 s and 0.1–0.2° at 120 s, for every person tested.
   - roths2's version (world offset (0,2,12)) settles stably at 80.5° [sim].
7. **Camera controls dead while selected** (Confirmed, [read]). Orbit input is ignored (:528-549), and Reset (:746-751) does not clear the selection.
8. **People overlap** (Confirmed, [sim]). James and Betty sit 0.01 units apart, because the within-generation spread and the birth-year jitter cancel. Nathan and Hannah are 3.86 apart, with rings 4.0 across. Labels are 12×3 units, so they collide.
9. **App dies with no key** (L, [read]+[grep]). `geminiService.ts:4` (roths2 and roths3) builds the client at module load. The bundled SDK throws "An API Key must be set when running in a browser" when the key is null. roths had a guarded lazy client (`roths/services/geminiService.ts:4-17`).
10. **AI portrait no longer reaches the node** (Confirmed for the missing prop; L for the tsc failure). `App.tsx:129` passes `selectedPortraitUrl`, but the scene's props (:12-22) do not declare it. Vite strips types without checking, so the build runs while `tsc` would fail.
11. **Year starts off the slider** (Confirmed, [read]). `App.tsx:19` sets year 2025 against a slider maximum of 2007, with no clamp. roths had one at `roths/App.tsx:44-50`.
12. **Stale loads, cache churn** (Confirmed, [read]). Cancellation is one shared boolean, `mountedRef` (:115, :345, :442), not a per-build token. The cached textures (`ImageCache.ts:56`) are disposed by `SceneCleanup` on every rebuild (`SceneCleanup.ts:26-30`).
13. **Import is unsafe** (Confirmed, [read]). `DatasetManager.ts:101-106` only checks the graph header; a member without `parents` throws at :485. Import replaces the data (App :80-84), and the saved copy overrides built-in data forever (:21-24).
14. **Dead code** (Confirmed, [read]). The `perfMonitor.update()` result is discarded (:507); types.ts:34-52 is unused; the object pool serves one vector (:545-548); App :64-67 is an empty `if`.

### 3b. Data (`family.ts` is identical in all four React trees)
- **Dangling parent** (Confirmed, [audit]). Victor's parent is `charles` (:140), who was dropped from the file.
- **Wrong parent for Guy.**
  - `family.ts` gives `alphonse` (:148) (Confirmed, [audit]): born 1909, after Alphonse died in 1905, with a generation jump of +3.
  - His father was Édouard (1868–1949), Alphonse's son (L, [recall]).
  - Both HTML files say `edmond` (`rothsch2.html:781`, `rothschilds.html:388`), which is also wrong (L, [recall]).
- **Generation field contradicts parent links** (Confirmed, [audit]). Edmond is generation 4 with generation-2 parents (:123); Betty is generation 2 but a child of the generation-2 Salomon (:75-76). The layout is driven by this field.
- **"James Édouard" mixes two people** (L, [recall]). `rothsch2.html:755-759` gives James Armand's dates, 1878–1957, under Alphonse. `rothschilds.html:356` gives 1844–1881, whose father is Nathaniel, who is not in the data.
- **Stock photos as portraits** (Confirmed, [audit]). Mayer and Gutle use picsum.photos images (:12, :21).
- **Membership shrinks** (Confirmed, [audit]). 26 in the HTML files, 18 in `family.ts` (8 dropped), 9 in `rothschild.json` (generations 1–2 only). Tour stop `lionel` is absent there, so stop 5 does nothing.
- **Unsourced notes** (Confirmed, [read]). For example `rothsch2.html:764`, "alleged Soviet spy", needs a source and a grade.
- **Wrong branch count** (Confirmed). "6 Family Branches" is hard-coded (Copy `App.tsx:309`, roths2 :218); the data has 5.

### 3c. Older trees: do not re-port (Confirmed, [read] unless marked)
- **rothschilds.html.** Spouse edges are drawn twice (:491-493). The auto-orbit (:683-687) overwrites drag, Reset and Expand All. The z position is random (:519).
- **rothsch2.html.**
  - The edge filter keeps edges with a hidden end (:1469-1476).
  - The labels toggle ignores the generation filter (:1503-1507).
  - Unhover undoes the timeline dimming (:1371).
  - Particles are never filtered (:1571-1579).
  - Auto-rotate overrides zoom (:1540).
  - Labels show first names only, giving two "James" and two "Edmond" (:1122-1125).
- **roths - Copy.**
  - The `+=` bob makes nodes drift off their edges and labels (:487).
  - Cleanup leaks GPU resources and the renderer (:612-626).
  - The filter hides node groups only (:672).
  - Non-Rothschild branches all sit at angle 0 (:699).
  - A single dataset is anchored 80 units off-axis (:324-330), likely off-screen at start (L).
  - Closing the panel keeps the selection (App :233).
- **roths2.**
  - Cleanup leaves the canvas (:266-270), so StrictMode in dev shows two canvases, the visible one frozen (L).
  - Clicks are caught on `window` (:264).
  - No resize handling or camera controls.
  - Generation 6 sits at φ=π, so Victor and Guy share the point (0,-53.97,0) [sim].
  - The camera starts inside the shell (45.3 < 47.0) and never calls `lookAt` before a selection.

### 3d. Build and hygiene
- **roths/ cannot build** (Confirmed). `App.tsx:5` imports a missing file.
- **Console noise.** `index.html:39` links `/index.css`, which exists in no tree, so there is a 404 (Confirmed). The Tailwind Play CDN and an unpinned esm.sh importmap stay in `dist/index.html`, and the CDN warns in the console (L). Both fail the loom "console clean" gate.
- **Duplicates** (Confirmed). `Expert.v2incomplete..[model].md` is a truncated plain-text copy of `Expert.v2.[model].md` (it stops mid-App). `repopack-output.txt` is the `roths - Copy` sources again. Package managers are mixed.

## 4. Prior expert docs: recommended, done, open

| Recommendation | Status |
|---|---|
| **[model]:** fix drift; rebuild on `graphs` change | Drift fixed by removing the bob. The rebuild is overdone: roths3 rebuilds on every render (3a-1) |
| [model]: filters hide nodes, labels and edges | **Open** (3a-3, 3a-4) |
| [model]: raycast against the canvas rectangle; deep dispose | Done (roths3 :587-591; `SceneCleanup`) |
| [model]: build token for async loads | **Open** (a boolean is used) |
| [model]: one orb per dataset | Chosen in `v2.notes.md`. Partly built in roths2 (every orb at the origin). Abandoned in roths3 without a note |
| [model]: rotation target computed once, centre→camera, applied as `q·current` | **Open**. Replaced by per-frame retargeting: stable in roths2, drifting in roths3 |
| [model]: App search deps, year extent, clamp | Done in roths. roths3 lost the clamp |
| [model]: Gemini env; depth-faded edges | Open; open |
| **[model]:** single orb, breathing shell, geodesic tubes, particles, labels at 1.25R | Done (roths3) |
| [model]: inner glow, guide rings, glow sprites, rotation inertia | Not carried |
| [model]: memoised callbacks | Open; its own App had the bug |
| **[model]:** image cache, Wikipedia cache, `SceneCleanup`, `DatasetManager` | Done near-verbatim. Import replaces where the doc said merge |
| [model]: object pool, performance monitor, types; split into hooks | Dead or unused; split **open** (778-line file) |
| **Buildnotes** A (caches, dispose, build token) / B (centre-based quaternion) / C (import/export) | A done except the token. **B open**. C done |
| Buildnotes claims: roths2 edges "can throw"; roths2 quaternion "wrong-direction" | Neither borne out: edges need both ends (roths2 :185), and the quaternion converges [sim]. roths3's version is the unstable one |
| roths2 `cline_docs`: `VITE_GEMINI_API_KEY` and graceful AI disable | Not done |
| `v2.notes.md`: (1) one orb per dataset, (2) pretty edges, (3) client-side key | (1) reversed; (2) done; (3) done, and the key leaked into dist |

## 5. Carry forward, rebuild, drop

**Carry forward** into a seeded Python generator, with no hand edits:
- the roths3/[model] layout formula, plus a separation pass;
- great-circle edges;
- the orb shell, optionally with the [model] guide rings;
- the generation palette and gold-on-black look;
- labels as children of each person;
- rothsch2's interaction meanings: hover with edge highlight, dimming people not alive in the year, filters covering nodes, labels and edges, search;
- the 5 tour stops with their captions, as Viewpoints and the frame shot list;
- baked monograms;
- generated stats and legend.

**Rebuild:**
- selection: a precomputed SFRotation per person, played once by an interpolator;
- camera: `EXAMINE` navigation, a SphereSensor orb drag, and an auto-spin TimeSensor, each on its own nested Transform;
- filters: Switch nodes through the external API, plus the ROUTE-only time-lapse;
- portraits: fetched at build time, with licence and sha256 in the receipt;
- datasets: one orb each, combined with Inline;
- data: a validated `people.json` with Wikidata QIDs and per-field provenance and grade. Start from the 26-person rothsch2 set and the `family.ts` Wikipedia URLs, and fix the §3b errors. Gate it on dangling parents, generation = max(parent generation)+1, plausible dates and reciprocal spouses.

**Drop:**
- runtime Gemini and the client key (rotate it);
- AI portraits;
- picsum images;
- the React, Vite, Tailwind and importmap scaffolding;
- the caches, object pool, performance monitor, `DatasetManager` and localStorage;
- the custom pointer maths and the bob;
- `Math.random` in the layout;
- the Habsburg and Darwin stubs;
- both `dist/` folders, the duplicate HTML, the repopack and the truncated [model] doc.
