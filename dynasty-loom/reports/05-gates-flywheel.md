# 05 · Validation gates and the flywheel for the genealogy loom

Analyst 05 of 7. Grades: **Confirmed** = reproduced by a tool run or test named here. **Likely** = follows from code or files read but not rendered. **Suspected** = not measured. No genealogy X3D exists yet, so no X3D validator or renderer has run on genealogy output. The fork validator is not in this container (`/home/user/x3d_mcp` is absent).

## 0. In one paragraph

The data gates I built (`proto/gates/`, stdlib Python, 29 tests) ran over every dataset in the zip: 13 data files, which reduce to 6 distinct datasets, plus 4 app variants and 2 built bundles. They found **20 errors, 26 warnings and 14 info findings**. Every Rothschild version fails, and so does the Darwin–Wedgwood stub. The shipped `family.ts` has six distinct defects:
- Victor points to a parent who was deleted.
- Guy was born four years after the "father" listed for him died.
- Betty sits in her own father's generation.
- Two full brothers sit in different generations.
- Two portraits are random stock photos.

The Darwin marriage edge is never drawn. One tour stop points at nobody. Fingerprints, compared across the four Rothschild versions, show when each defect entered the data. Two of the worst defects came in with "corrections". That record is the seed of the flywheel's regression corpus.

## 1. How the user's machinery works today (cited)

**Gate.**
- The validator is the x3d_mcp fork: `validate_xml` (XSD), `validate_semantic` and `check_profile`, called from `gobbler-demiurge/tools/validate_fork.py` and `x3d.ml/gobbler-v3/tools/validate.py`.
- `build_bird.py --validate` (lines 57–68) writes the verdict and the fork's commit into `receipt.json`. Example, README row 100: "XSD valid, profile Immersive OK, 0 semantic errors … fork `2b696f5`".
- Known blind spots are closed by hand:
  - A ROUTE written before its node passes the fork, but X_ITE 16.5.1 drops it (row 127).
  - A colour above 1 failed the XSD under a misleading size-limit message (row 126).
  - So `test/test_layers.py` regex-checks ROUTE/USE order and asserts "adds, never edits" (byte equality with the Deep scene) and size and sha256 rules.
- Console clean: `test/e2e.js` ends every suite with "no page errors" (`pageerror` plus `console.error`); `pagetest.mjs` and `shoot.mjs` also log any HTTP response of 400 or above.

**Frames.**
- `test/frames.js` shoots 15 stops at 1527×923 with `?ui=none`.
- It waits for the camera pose (within 1e-3) and 9 s for Inlines.
- It retakes any JPEG under 90 KB, up to 3 times; `e2e.js` passes a frame over 80 KB as "not black".
- Both are byte-size proxies with a thin margin: the smallest real full frame, `15-villagers.jpg` at 131,611 B, is 1.46× the threshold.

**Picture judge** (`docs/PICTURE-JUDGE.md`).
- The judge sees two owner stills and one candidate, scores 4 criteria from 1 to 10, and votes 3 times per still.
- Re-judging the same 12 images moved the mean by 0.09; paired differences have SE 0.11, so anything under about 0.2 is noise.
- A black still scored 2.33.
- The judge's density complaint contradicts the owner, so the owner's eye is the judge of record.

**Receipts.**
- `assets/*/receipt.json` records the Blender version, the x3d-blender-io commit, the script and spec sha256s, bake settings, light percentiles per mesh, and the file's bytes and sha256.
- A changed script voids its receipt. README line 155 leaves a wrong comment in place for exactly that reason.
- `x3d.ml/src/x3dprov.py` chains these steps (`prev`, `input_sha256`, `output_sha256`) inside the X3D `<head><meta>`; `verify()` returns verified, stale or broken-chain.
- `runs/*/result.json` holds real ingest → validate → repair chains.
- `x3d.ml/drift/` names the fork commit at which each of 37 verdicts changed.

**Flywheel.**
- `HOOKS.md`: spec → agent → validating x3d_mcp → Blender + x3d-blender-io → X_ITE → verdict → x3dprov tether.
- `x3d.ml/docs/blender-scivis-expert/FLYWHEEL-SYNERGY-v1.md` makes it a state graph: E13 write-back grows the fixtures, E14 promotes failures to lints and rungs, and L4 lets computed oracles (ID mask) take over from judges.
- Correction to the brief: `VISION-v4.md` never says "flywheel". The phrase "growing the village from its own validated scenes" is an open item in `gobbler-demiurge/README.md:139`; PLAN §3.3 adds "lit windows" for loops with measured results.
- `FACTS.md` item 26: 203 of 1,058 valid scenes draw nothing.

## 2. The genealogy gate stack

In the loom, the script is the data plus the generator. Any gate may send work back to the data, and nobody hand-edits the X3D. An error blocks the build, a warning travels to the owner with the build, and info goes to the receipt only.

### Layer D: data (built and run; see §3)

| Gate | Rule | Note |
|---|---|---|
| D00 schema | the `FamilyMember` fields and types from `types.ts` | a missing note shows as "undefined" |
| D01 dangling parent | every parent id exists | the scene skips the edge silently: `if (parentPos)` in `CosmosScene.tsx` |
| D02 cycle | no one is their own ancestor (iterative DFS; self-parent included) | |
| D03 / D05 parent age | the child is younger than each parent; the parent's age at the birth is between 12 and 80 | |
| D04 posthumous | the child is born no later than a parent's death + 1 year | there is no sex field, so the stricter mother rule cannot apply (a schema gap) |
| D06 dates | death after birth, lifespan of 122 or less, no date after `asof` | |
| D07 duplicates | duplicate ids (JS keeps the last silently), a shared Wikipedia article, same name tokens born within 1 year | |
| D08 generation vs topology | a child is below every parent (error); a skipped generation warns "ancestor missing"; full siblings share a generation (error) | the layout maps `generation` to latitude |
| D09 spouse | the spouse exists and points back | the scene draws the edge only from the id that sorts first, so a one-sided link vanishes depending on spelling |
| D10 privacy | no death year and born within 110 years: presumed living (error) | without a death year the card prints "– Present" |
| D11 portrait | the imageUrl is not a placeholder-photo service | |
| D12 Wikipedia | a well-formed article URL whose title shares a name token | |
| D14 island | no one is connected to nobody | |
| D15 placeholder text | stub, TODO or lorem text does not appear in a name or note | |
| X01–X03 app cross-references | tour stops, branch angles and generation colours all resolve | otherwise angle 0, colour white |
| R01 / R02 bundle | the built JS carries its source's names and no presumed-living name | a text scan |

### Layer S: scene (designed; the static part is built)

1. **Static gates (`scenegates.py`)**, run before the fork: S1 DEF unique per scope, S2 USE after DEF, S3 ROUTE after its nodes, S4 colour in [0, 1] (reports the element, index and value), S5 size budget, S6 advisory (opaque ColorRGBA should be Color). On the user's 15 X3D files: 0 hard findings; S6 fires only on the 9 raw Blender exports, as expected. **Confirmed.**
2. **The fork's XSD + semantic + profile check** at the commit named in `docs/PIN.md` (PLAN §2.1), alongside the XSD version, X_ITE 16.5.1 and the Chromium build.
3. **Data↔scene parity:**
   - one `Transform DEF='P_<dataset>__<id>'` per published person (ids map one-to-one to valid NCNames)
   - edge counts equal the resolvable parent links and the symmetric spouse pairs
   - every node carries its id and the data sha256 as metadata
   - a flagged edge is drawn as "unverified" or excluded with a receipt note, never dropped silently
4. **Edges point down the generations:** a child's latitude is greater than its parent's. Betty would fail this even if the data gate were skipped.
5. **X_ITE console clean:** no "Unknown named or imported node" (the dropped-ROUTE symptom), no shader error, no HTTP response of 400 or above, and every `P_*` node resolves.
6. **Size budget:** for example, boot at 150 KB gzipped or less for 500 people or fewer.

### Layer L: look (designed; the pixel parts are built)

1. **Stops** = `TOUR_SEQUENCE` + Wide + one per branch + the founders. Use the pose wait and settle from `frames.js`, at 1527×923 with `?ui=none`.
2. **Non-black (`lookgates.nonblack`)** replaces the JPEG-size proxy. The rule: at least 2% of pixels with luma above 0.1, and p99 luma of 0.25 or more. Against a stop's golden frame the rule is relative instead, because sparse starfields legitimately fail the 2% floor.
   - All 34 of the user's committed frames pass (the darkest has 7.0% lit pixels). **Confirmed.**
   - A black frame is retaken and never scored.
3. **Node recall:** project each person who should be on screen with the stop's camera and require lit pixels at 95% or more of them. Precise version: render an ID-mask variant (unique flat colour per person and edge) for exact occlusion. This follows FLYWHEEL L4 and the v4 projection check (scale 0.997–1.001).
4. **Label legibility (`label_metrics`, `contrast`):**
   - Overlap share at most 5% at tour stops and 15% at Wide.
   - Text height at least 12 px.
   - WCAG contrast of 4.5:1 or more against the frame pixels behind the label.
   - The current labels are fixed 12×3 world-unit sprites, so overlap grows with distance.
5. **Picture judge** on frames that passed 2–4 only, following the PICTURE-JUDGE protocol, with the noise re-measured every round. Genealogy criteria: can you trace founder → stop, are siblings grouped, are the names readable.

### Receipt

Every build writes one `receipt.json` and an x3dprov chain (ingest-data → data-gate → generate → validate → render → judge). It records:
- the sha256 of every input
- the gate checker by sha256, the thresholds and `asof`
- the generator's and the scene's sha256, and the scene's bytes raw and gzipped
- the validator's name, commit and XSD version
- the X_ITE and browser versions
- each frame's sha256 and non-black statistics
- the judge round and its noise floor
- the grades

`proto/gates/out/receipt.json` already carries the data-gate part.

## 3. What the checker found (run 2026-10-29, `genealogy-gates 0.1`, Python 3.13.17, 0.09 s)

The lineage is ordered by file time: v1 `rothschilds.html` (26 people) → v2 `rothsch2.html` (26; identical to `roths/collateral/rothsch2.html`) → v3 `data/family.ts` (18; four byte-identical copies, shipped in `roths2/dist`) → v4 `data/trees/rothschild.json` (9; shipped in `roths/dist` together with the two stubs).

| Defect (fingerprint) | Versions v1 v2 v3 v4 | Grade |
|---|---|---|
| D01 victor → `charles`, a dangling parent; Victor becomes an island (D14) (`eb5910e66973`) | . . X − (introduced in v3, when Charles was dropped) | Confirmed |
| D04 + D05 guy → alphonse: born 1909, Alphonse died 1905 and would have been 82 (`5843114f7308`, `d26f8d61cc21`) | . . X − (v3 re-parented Guy from Edmond to Alphonse; v1/v2's D08 skip "resolved" into three defects) | Confirmed |
| D08 betty: generation 2 = parent Salomon's generation 2 (`fa47d7f80ed5`) | . X X X (introduced in v2 by adding `parents: ["salomon"]`) | Confirmed |
| D08 full siblings in different generations: Alphonse 3 / Edmond 4 (also Gustave 3 in v1/v2) (`c31935a4b754`); Betty 2 / Anselm 3 (v2, v3); Maurice 5 / Guy 6 (v1, v2) | X X X − | Confirmed |
| D08 skips: Guy 6 → Alphonse 3 (two generations skipped), plus Edmond 4 → James 2 and → Betty 2, and James Édouard 5 → Alphonse 3 (v1/v2) | | Confirmed (warning) |
| D11 Mayer and Gutle shown with `picsum.photos` random photos (`c3523042232d`, `ba3a34e27f27`) | . . X X; in both shipped bundles | Confirmed |
| D09 Emma names `charles_darwin` as spouse, Charles names no one: with the shipped rule `ee<Te` (read in `roths/dist`) the marriage edge is never drawn | stub | Data and code Confirmed; on screen Likely |
| X01 tour stop `lionel` is missing from rothschild.json, which `roths` and `roths - Copy` tour (`DATASETS[0]`): stop 5 holds 8 s on nothing | app | Confirmed (data and code read) |
| X02 Habsburg, Darwin and Wedgwood have no `BRANCH_POSITIONS` entry in `roths` and `roths - Copy`, so they are placed at angle 0 | app | Confirmed (angle); visual effect Likely |
| D15 "Stub dataset: replace with a richer JSON later." is the card note for all 3 stub people (in `roths/dist`) | stubs | Confirmed |
| D00 schema: no `id` on 26/26 records (v1, v2), no `branch` on 26/26 (v1), notes missing on 11 then 3 | X X . . (resolved in v3) | Confirmed |

**Clean results** (Confirmed for these rules on these files):
- no cycles
- no child older than a parent
- no death before birth
- no duplicate ids or people
- no presumed-living people, so D10 and R02 pass vacuously; they are exercised by an injected test
- Wikipedia titles all consistent
- bundle parity holds: `roths/dist` carries 9/9 + 1/1 + 2/2 names and `roths2/dist` carries 18/18

**A receipt gap.** `roths/components/` is empty, yet `roths/App.tsx` imports `./components/CosmosScene`. The source tree cannot rebuild its own bundle, and the bundle is the only copy of the scene code that shipped. **Confirmed** (directory listing).

**Historical reading** (Likely, from memory; not checked against a source in this session):
- Victor's father is Charles (1877–1923), as v1 and v2 had it.
- Guy's father is Édouard (1868–1949), Alphonse's son. He is missing from every version, which is exactly what the two-generation skip points at.
- Betty was Salomon's daughter and married her uncle James. Her `generation` encodes generation by marriage, while her parent link encodes generation by blood.

The gates check the data against itself; only a second source per relation can settle these questions.

## 4. The flywheel for genealogy

**Layout.** The data (`data/<lineage>/*.json`) is the only hand-edited input. Each relation gets a witness record in `sources/` (URL, quote, date, grade), as in the Shroud ledger. The other folders:
- `gen/build.py` and `gates/`
- `corpus/defects/<gate>/<fp>.json` and `corpus/clean/`
- `golden/<stop>.{jpg,json}`, `judge/picks.jsonl`, `issues/<fp>.json`, `builds/<date>-<scene-sha>/`

**One turn of the flywheel:**
1. **Data gates.** Each new error fingerprint is auto-filed to the data stage as `issues/<fp>.json`, with the records, the rule, and the specific question a witness must answer. Example: "Guy 1909: listed parent died 1905; which parent record is right?"
   - Model-proposed fixes are Suspected and labelled as generated (HOOKS §7b). A fix lands only with a witness.
   - If a closed fingerprint reappears, its issue reopens; the lineage table marks it present after absent.
2. **Generate,** then run scene gates S1–S6, the pinned fork, parity, "edges point down the generations", and console clean.
3. **Look gates.** Non-black relative to the golden frame, node recall, and label metrics come first; the judge runs only on frames that survive them.
4. **Receipt and x3dprov chain,** then a contact sheet goes to the owner.
5. **The owner's picks feed back.**
   - A picked frame becomes the stop's golden frame and calibrates its non-black and recall thresholds.
   - Each pick is logged with the judge's votes. A prompt or criterion survives only while it agrees with the owner beyond the noise floor; the density complaint would have been dropped.
   - The judge stays advisory until it agrees with the owner on held-out picks.
6. **Corpus update and promotion.**
   - Each new defect gets a minimal reproducer: the subject, its refs and their records.
   - Every past fingerprint is replayed on each run. "Both sides" applies: the clean corpus must stay silent.
   - A complaint raised twice, by the owner or the judge, is promoted to a computed gate plus a fixture (FLYWHEEL E14/L4). Example: "names unreadable at Wide" becomes `label_metrics` with a threshold. The judge is left with taste.
7. **Drift.** When the checker sha or the fork pin changes, the whole corpus is re-run and every changed verdict is attributed to that commit (the `drift_attribution.json` pattern).

**Metrics that show the flywheel turning:** open defects by gate, regressions per data version, retake rate, false alarms on the clean corpus (must stay 0), judge–owner agreement, and the noise floor.

**Growing the village from validated scenes.** A family build whose x3dprov chain verifies becomes an Inline "house" in the village, and only verified receipts may be composed. Its windows light up for each gate layer it passed, following PLAN §3.3. The Heart can beat the genealogy verdict tape the same way it beats `xbench-run1.json`.

**Shared infrastructure with the Mashtots/X3D modeling thread and the blenderizer** (`x3d-blender-io`). I found nothing on Mashtots on disk, so that seam is generic.
- **One finding schema** (gate, severity, subject, refs, fingerprint, grade), **one receipt shape** and **one x3dprov chain**. Domain gates plug in as modules: `datagates.py` for genealogy, and whatever source-table gate Mashtots needs.
- **`scenegates.py` is domain-free.** It already ran clean on the demiurge's Blender exports. S3 and S4 are the bake skill's own traps.
- **One pin, one frame harness parameterised by a stop list, and one judge service** with per-domain criteria and per-domain owner picks.
- **The blenderizer's export is just another chain step.** Its receipt fields already match. For example, a baked "hall of ancestors" would go through the bake stage and be composed as an Inline under the "adds, never edits" byte-equality test.
- **One corpus layout** `corpus/<domain>/<gate>/<fp>.json`, re-run together on every validator bump.

## 5. Files

Everything is in `scratchpad/proto/gates/`:
- `jsobj.py` reads a JS/TS literal without executing it and refuses code.
- `sources.py` is the allowlist loader; `.env*` is never opened.
- `datagates.py`, `run_gates.py`, `scenegates.py`, `lookgates.py`.
- `test_gates.py` (19 tests, OK) and `test_scene_look.py` (10, OK).
- `out/` holds `findings.jsonl`, `lineage.json`, `receipt.json` and `console.txt`.

Run with `python3 -I run_gates.py <geneology root> out`; the exit status is 1 on any error.
