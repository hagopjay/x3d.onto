# 04 · 3D layout and X3D scene: the genealogy loom

Analyst 4 of 7. Angle: the spatial grammar plus a working generator, gated the way the loom rules ask. All paths are under `scratchpad/proto/x3d/` unless written in full.

## Verdict

There is now a working generator, `build_genealogy_x3d.py` (standard library only, deterministic). It reads the uploaded tree JSON and writes `genealogy.x3d` (X3D 4.0, Immersive profile, 221,261 bytes, 38,023 gzipped). It also writes `genealogy-anchors.json` and `genealogy-receipt.json` next to the scene. Every static check passes: xmllint, the X3D 4.0 XSD and the user's x3d_mcp fork. The live gate in X_ITE 16.5.1 passes 11 of 11 checks with 0 console messages. I shot frames at 13 stops across three rounds and changed the scene after each round. The drum works as an object and as a picker, but it is a poor surface for reading names. The narrative analyst's flat tapestry probably reads better (see the end).

## 1. Spatial grammar

**Primary: the loom drum.** Time runs along the drum's axis (+X, 0.07 units per year, 1875 at x = 0). Every dataset uses this same absolute scale, so families that lived at the same time sit side by side.
- **Houses.** Each house (the `branch` field) is a sector of the drum.
- **People.** A person is a warp thread: a bead at birth and a lit thread to death.
- **Lanes.** Lanes inside a house are interval-scheduled. A lane is reused 4 years after its occupant dies, a spouse goes next to the partner, and a child goes to the free lane nearest its parents.
- **Parentage** is a gold lift. It leaves the parent's thread 2 years before the birth and lands on the child's bead. Lifts between houses arch off the drum.
- **Marriage** is a rose weft across the two threads.
- **Kin marriage.** When the spouses share an ancestor, the weft loops back: the whole cycle (weft, both threads, the lifts up to the nearest common ancestor) is drawn as one ember loop with a light pulse running round it. Two such loops exist in the data:
  - James and Betty: he is a brother of her father Salomon.
  - Lionel and Charlotte: first cousins.

This is the x3d.loom metaphor taken literally, and it keeps the orb's idea of houses as directions.

**House order.** The generator keeps the orb's five equal slots and puts the founders' house (Frankfurt) in front. It then tries every circular order of the rest, keeping the one where cross-house lifts and wefts cross the least angle. Result: Frankfurt 0°, Naples 72°, London 144°, Vienna 216°, Paris 288°. That costs 18.85 rad against 20.11 rad for the orb's own angles, and every brother's lift is now 72°. `--house-order orb` restores the orb's angles.

**Secondary: generation rings, by a scriptless morph.** One TimeSensor (12 s round trip), one ScalarInterpolator, two PositionInterpolators per bead and CoordinateInterpolators for every line set. Together they slide each bead to one station per `generation` value, at the median birth year of that generation, and back. The morph is diagnostic: a bead that moves against the flow is a person whose generation label disagrees with the birth years. The data has 5 lifts whose generation does not step by one (Salomon→Betty, James→Edmond, Betty→Edmond, Alphonse→James Édouard, Edmond→Guy); in the rings they turn cyan.

**Rejected:**
- **Time helix.** It reads well for one line, but marriages across houses become chords through the middle.
- **Concentric generation rings as the primary layout.** They throw away the time axis, which is the one thing every family shares.
- **The existing orb as is.** It puts generations at latitudes, which crowds the poles. The datasets are offset from each other, and they collide.

## 2. X3D patterns used

The user's patterns from gobbler-demiurge and gobbler-v3 are reused: the receipt fields, gzip with mtime 0, `validate_fork.py`, the X3D header and ROUTEs written last.

- **A `PersonBead` PROTO** (29 instances) holds the bead, the scaled lifeline cylinder, the name and a TouchSensor exported as `isActive`.
- **DEF/USE is used throughout.** There are 233 DEFs and 737 USEs. Each pick's lineage highlight is assembled from USEs of one never-drawn `Library` Switch.
- **Selection needs no Script.** A bead's TouchSensor feeds an IntegerTrigger, which drives two Switches: the halo plus lineage in the world, and the person's card in a HUD. A ProximitySensor carries the HUD by routing to a Transform. Touching the drum clears the pick.
- **Ten Viewpoint stops:** the loom, five houses, two kin loops and two stub bolts. House stops look radially, so time runs left to right and lanes stack up the screen.
- **All 231 ROUTEs are written after both nodes they name.** The generator's own static check enforces this, because X_ITE drops a ROUTE that comes first and the fork validator does not catch it (from the gobbler-demiurge README).
- **`index.html`** loads the hash-checked X_ITE 16.5.1 from `vendor/` (fetched with `npm pack`, the same tarball hash as the user's `fetch_deep.sh`). It builds the stop rail from the anchors (keys 1 to 9, G for the morph). It exposes `window.genApi` for the gate, and `?ui=none` gives clean frames.

## 3. Gate results (graded)

| Claim | Grade | Named by |
|---|---|---|
| Well-formed; valid against x3d-4.0.xsd | Confirmed | xmllint (libxml2 2.14.6) with the fork's schema |
| XSD valid; Immersive profile plus Shape level 2 covers every node; 0 semantic errors and 0 warnings (16 infos, all DEFs reached only by the SAI) | Confirmed | x3d_mcp fork at main `2b696f5` (the commit the user's receipts name); the coordinator's `acdf5c4` copy agrees |
| X_ITE loads it with 231 of 231 ROUTEs live, the PersonBead proto, all 10 stops, and VP_Loom bound | Confirmed | X_ITE 16.5.1, Chromium 1243 (Playwright 1.63.0), SwiftShader |
| A real mouse click on Nathan's bead at the London stop picks him in both Switches; a click on the drum clears the pick | Confirmed | same |
| The morph reaches the ring station (Betty within 3.6e-5) and returns; generation labels show and year rings hide during it | Confirmed | same |
| Console clean: 0 messages, no unknown nodes, no dropped ROUTEs | Confirmed | same |
| It runs the same on hardware GL | Likely | untested; only SwiftShader was used |
| The HUD card fits narrow screens | Suspected false | it was placed for 1527×923, and screens narrower than about 1.3:1 will cut it |
| Whether the fork checks ROUTEs into ProtoInstance fields | Not tested | probe planned, not run |

One X_ITE finding is worth keeping (Confirmed, X_ITE 16.5.1). `browser.currentTime` is undefined, so starting a TimeSensor with it gives NaN fractions and no console message. The morph failed this way silently in round 1. The fix is `browser.getCurrentTime()`, which the user's `boot.js` already uses.

The receipt records all of this. It holds the scene and generator sha256 (scene `34a855cb…`, generator `7ca31412…`), counts, sources, conflicts, data notes, layout, validators, `gate_static: clean` and an `xite` block written by the gate. `gate.json` holds the full console log and per-frame luminance. Near-black frames are retaken; none were needed in round 3.

## 4. What the frames showed, and what changed

- **Round 1 → 2.** The translucent drum showed its far side mirrored through the front. Year labels were repeated five times, a stub bolt intruded into the house stops, a floating title showed up in odd places, and "generation N" labels overlapped. Round 2 made the drum opaque, moved the bolts 9.5 units below, removed the title, shortened the generation labels and added the house-order search and lane reuse.
- **Round 2 → 3** (the one fix allowed at the end). Billboarded names turned toward an off-axis camera and sank into the now-solid drum: "Har", "Lior", "Cha", "180(". Names and year labels are now printed flat on the drum, in the bead's frame (+X time, +Y tangent, +Z outward). Text in the tangent plane can never cut into a cylinder. The London stop now reads "Hannah Barent Cohen", "Nathan Mayer", "Lionel", "Charlotte", "Nathaniel". Gate and validators were re-run on this build: 11 of 11, clean.

**Still visible in the round-3 frames (not fixed):**
- **The overview shows only the front half of the drum.** London, the largest house at 144°, is hidden at load. My planned fix is a slowly turning cloth beam: 70 s per turn, matching the orb's `autoRotateSpeed` of 0.0015 rad per frame. House stops would ride inside the beam and a pick would pause it. I checked that X_ITE 16.5.1 implements `set_pauseTime` and `set_resumeTime` (read in the engine source), but I did not build it.
- **Printed names near the silhouette are edge-on.** At the London stop the Vienna row is unreadable. This is the price of printing.
- **The loop stops sit too close to show a 144° wedge.** The camera needs to be about R/cos 78° ≈ 22 units from the axis; it is now about 13.
- **Clutter.** House names at the left edge are cut off in house stops. The world-space "generation rings" button lands in odd places and belongs in the HUD. "Ferdinand" overlaps the 1850 label, and the kin label sits among the names.

Frames are in `frames/` (round 3), `frames/round2/` and `frames/round1/`, with `gate-round1.json` and `gate-round2.json` and the round-2 receipt alongside.

## 5. Data findings that shaped the layout

- **Rothschild has 26 people.** That is the 9 in `rothschild.json` plus 17 more read from the `familyData` literal in `rothsch2.html`. `tools/extract_familydata.py` reads that literal with a tokenizer and never evaluates it; its output records the source's sha256.
- **The sources disagree.** One field conflict is listed in the receipt. The roths3 `family.ts` (18 people) disagrees with the HTML version on Guy's parent (Alphonse in one, Edmond in the other) and on two notes.
- **No marriage dates.** The weft goes at the year before the first child in the data and is flagged as estimated when there is no child. This misses by two years for James and Betty: the weft lands at 1826, but they married in 1824.
- **No sex field.** Kin relations are worded neutrally ("uncle/aunt and niece/nephew").
- **`branch` means residence, not descent.** Betty is filed under her husband's house, which is why her lift from Salomon crosses houses.
- **The stubs are thin.** The Darwin–Wedgwood stub has a one-sided marriage, and the Habsburg stub has one person.

## 6. A larger dataset (~400 people across 3 families) and the tapestry loom

The generator already merges trees that share an id and gives each family its own drum on the shared time axis, so three families arrive without code changes. At about 130 people per family, three things would need to change:
- **Lanes.** The real limit is lanes. Interval scheduling keeps a house to its peak count of living members, perhaps 25 to 40 per family. At 0.5 units per lane that no longer fits round a 4.5-unit drum. Either the radius grows with the lane count, or houses become their own bolts, with names shown only at the bound house stop (a Switch per stop).
- **House-order search.** The brute-force search is (n−1)!, which is fine up to the 8 houses where it already falls back to the orb's angles. Past that it needs a greedy or annealed order.
- **Scene weight.** The scene is about 7.6 KB per person now, mostly HUD cards, the lineage USE lists and the two morph interpolators per bead. Scaled to 400 that is about 3 MB raw and 0.5 MB gzipped, with roughly 1,500 ROUTEs. X_ITE should cope, but boot on software GL is already 16 s. So the cards should move to an HTML overlay driven through the SAI, and each family should become an Inline with its own receipt.

The narrative analyst's tapestry loom (`reports/07-narrative-ux.md`) works as a new mapping inside the same `layout()` rather than as a new generator:
- **Axes.** Time runs up the cloth. Houses run west to east by their city's longitude: London, Paris, Frankfurt, Naples, Vienna. Latitude gives depth.
- **Marriage** is a level weft at the wedding year, doubled when the couple share founders. The data has no wedding years, so this falls back to my child-year rule, flagged.
- **Red dye** is the share of descent from Mayer and Gutle: founders are 1, in-laws 0, and a child is the mean of its parents. That is one pass over the parents, fed into the PersonBead `color` field, which already exists.

A flat cloth fixes exactly what my frames show the drum doing badly. Every name faces one camera, nothing hides on a back side, and the 144° loops become flat shapes. What it loses is the drum's wrap-round adjacency of houses. Because every line set already carries two layouts with matching point counts, the drum can stay as a morph: the cloth "rolled onto the beam". My recommendation is the tapestry as the primary reading layout, the drum as the rolled-up overview reached by the morph, and the generation rings kept as the diagnostic third state.

## Files

- Generator: `build_genealogy_x3d.py`. Tools: `tools/extract_familydata.py`, `tools/validate_fork.py`, `tools/fetch_xite.sh`, `tools/gate.js`. `tools/probe_morph.js` is a one-off debug script.
- Scene: `genealogy.x3d` and `.x3d.gz`, `genealogy-anchors.json`, `genealogy-receipt.json`, `gate.json`, `index.html`.
- Data read: `data/rothschild_html26.json` and `data/rothschild_ts18.json`, extracted, with provenance.
- Rebuild:

```
python3 -I build_genealogy_x3d.py roths/data/trees/rothschild.json data/rothschild_html26.json roths/data/trees/habsburg_stub.json roths/data/trees/darwin_wedgwood_stub.json --out . --validate --x3d-mcp <fork>
node tools/gate.js --tag=NAME
```
