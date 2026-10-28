# Gobbler v4: hover, guided mouse and corner UI (spec, draft 2: step 1 is built)

Draft 1 was written 27 Oct 2026 for HagopJay's taste check; draft 2 (28 Oct) keeps it and adds what was built and measured on the live scene: section 12 and the amendments marked *draft 2* below. The viewer is in `gobbler-v4/` (see its README).

Draft 1 text: Nothing here spends money. Copies of the frames and the pack are also in `/mnt/project-files/ontology-extraction/v4-ui/`. Numbers are measured on the real Gobbler 3 Deep graph (`graph-v3.json`, 2,476 drawn stars) or computed from your two stills. The one thing I cannot measure in the cloud is real-GPU frame cost; it is flagged Suspected and has a test (section 9).

Your words this spec answers: "a toggle with none/minimal, guided mouse and optimal UI corner placements when UI and onHover goes live for the real time and deep ontological data", "stills: none is fine", "one scene in the browser, if it is not a trade-off in efficiency", "I don't want to lose anything".

## 0. What to look at first

| File | What it is |
|---|---|
| `docs/v4/mock/out/storyboard.png` | six frames on one sheet: none, minimal at rest, hover, NodeType card, placement map, Finding card |
| `docs/v4/mock/out/B-4-card-nodetype.png`, `A-4-card-finding.png`, `B-5-placement-map.png` | the three frames that carry the design, full size |
| `docs/v4/mock/mock.html` | the mock itself, params `still=A\|B state=none\|rest\|min\|card\|zones card=shape\|finding hover=x,y` |
| `docs/v4/mock/placement.js` + `test_placement.js` | the corner-placement function and its 8 tests (all pass: `node docs/v4/mock/test_placement.js`) |
| `docs/v4/mock/data.json` | the real card text (Shape from the ontology, a measured X_ITE Finding, THE TETHER loop) |
| `docs/v4/mock/render.js`, `storyboard.py` | regenerate the frames: serve `docs/v4/mock/` over http, `node render.js 8793`, then `python3 -I storyboard.py` |
| `docs/v4/mock/bench/pick_views.js`, `pick_timing.js` | the pick-accuracy and timing measurements below; input is the Deep `graph-v3.json` from hagopjay/x3d.ML branch `claude/project-thread-0105va` @ `51e185f` (sha256 `36a308c8…`) |

MOCK rules: card text is real data; star positions and corner choices are illustrative on your stills (the stills are screenshots, so hover points were found by luminance blobs and eyeballed). The stills carried the old v3 chip strip at the bottom, cropped in the mock (A: 32 px, B: 54 px plus a 1 px window border) so the v4 chrome shows alone. The originals are untouched in `docs/v4/mock/stills/`.

## 1. UI levels (the toggle)

| Level | Shows | Hover | Use |
|---|---|---|---|
| **none** | nothing: no chips, no tooltip, no ring, no dim | off (camera input still works) | stills, judge frames, screenshots, presenting |
| **minimal** (default) | four corner chips (section 3) and nothing else at rest | on | normal viewing |
| **deep** (not a mode, a dwell) | one card, docked in a corner, only while you dwell or pin | on | reading the graph |

- Toggle chip at bottom-left cycles none and minimal. Keys: `U` cycles, `H` hides everything while held (momentary none for a screenshot), `Esc` unpins and closes. Choice persists per browser (try/catch around storage; works without it).
- URL control for automation and the judge loop: `?ui=none|min`, `?view=Face|Wide|...`, `?hover=<entity index>` (forces that card open, deterministic for Playwright), `window.gobbler.hover(idx)` for the same from code. Stills are always `?ui=none`.
- Nothing is added to the X3D scene. The overlay is DOM and SVG above the canvas, so the scene file, its validator verdict and every earlier Gobbler version stay byte-identical (add, never replace).

## 2. Guided mouse

The pointer is guided so the dense graph never feels like a pixel hunt.

| Behaviour | Rule | Why |
|---|---|---|
| Snap | nearest star within **30 px** of the pointer wins; distance only, depth breaks ties; a gold ring marks it | Pure distance beat size-weighted picking in the measurement below (weighted was up to 5 points worse) |
| Focus dim | outside a 330 px radial the frame dims 34% (tooltip) or 46% (card), eased in 120 ms | quiet guidance: the eye goes to the neighbourhood, the chaos stays beautiful |
| Dwell tiers | **0.15 s** label, **0.45 s** card, **1.2 s** deep; a ring around the star fills as dwell advances, so you see that more is coming | you choose the depth by patience; no clicks needed |
| Pin / fly | click pins the card (camera does not move); double-click or `F` flies there through the existing Probe viewpoint; `Esc` unpins | keeps your orbit under your control |
| Drag | dragging orbits and suspends hover; hover resumes 120 ms after release | no flicker while you steer |
| Crowded spots | if two or more stars sit within 12 px, the tooltip shows `+k` and the wheel (or `←` `→`) cycles candidates | measured need, see below |
| Neighbour echo | hovering a relation row in a card pulses that star and brightens its tether; clicking a row flies to it | the card and the sky stay one object (design only, not in the mock) |
| Touch and narrow | no hover: tap = label, second tap = card; below 720 px the card becomes a bottom sheet | `placement.js` already returns `SHEET` under 720 px |

**Measured on the real coordinates** (`docs/v4/mock/bench/pick_views.js` over the 2,476 drawn stars of Gobbler 3 Deep, the scene's own Viewpoint presets, viewport 1527 x 923, pointer noise 3 px sigma, 12 samples per star). The Face camera in your stills is not among the Deep scene's Viewpoints that I could read (Wide, Colossus, Eye, Inside, Flywheel, Crown), so it is not measured here.

| View | stars on screen | median gap to nearest star | stars with a neighbour under 12 px | right star picked (all, distance) | right star picked (core tier only) |
|---|---|---|---|---|---|
| Wide | 1,896 | 7.7 px | 79% | 81% | 92% (560 stars) |
| Colossus | 1,548 | 5.7 px | 90% | 72% | 81% (476) |
| Crown | 2,220 | 6.1 px | 86% | 73% | 84% (609) |
| Flywheel | 758 | 15.5 px | 35% | 94% | 99% (179) |
| Eye | 174 | 12.7 px | 39% | 94% | 99% (18) |
| Inside | 186 | 30.8 px | 4% | 100% | 100% (60) |

Reading it: in the three wide views the sky is genuinely crowded (stars are 6 to 8 px apart), so a pure nearest-star pick is right only 72 to 81% of the time. Decision (mine, flagged in section 10): while the median gap is under 10 px, only the **core tier** (648 stars, tier 1) is hoverable, which lifts accuracy to 81 to 92%; the other 1,828 wake as you zoom in. Numbers are a Monte Carlo over three runs and moved by 1 to 2 points. Hold `Shift` to hover every star anyway. Grade: **Confirmed** for the arithmetic (it is projection of the real coordinates), **Likely** for what it will feel like until it runs on a real GPU.

## 3. Corner chips and card slots

Four always-on chips in minimal mode, one job per corner, sized to the viewer's 22 px stage padding:

| Corner | Chip | Content (real) |
|---|---|---|
| TL | identity | `GOBBLER` plus "3 Deep, 2,476 stars, 19 loops" (becomes the view breadcrumb in v4) |
| TR | legend and badge | the seven family dots (spec, tool, people, work, learn, rule, loop) and `valid, fork 2b696f5` so "valid" always names its validator |
| BL | views and toggle | UI toggle, then Face, Wide, Flywheel, Crown pills |
| BR | health | fps, plus "hover a star" until you first hover |

Tokens are the viewer's own: bg `#08070a`, gold `#e9cf8a`, gold2 `#b8964a`, maroon `#9b2c47`, ember `#e5751f`, serif Iowan Old Style / Palatino / Georgia for titles and quotes, mono for metadata, `.chip` pills with a gold hairline.

## 4. Where the card goes (optimal corner placement)

The card docks to one of the same four corners (or the bottom sheet), never floats over the star. `placement.js` is a pure function (no DOM), so the mock, the node tests and the live viewer run identical code.

```
score(slot) = 2.0 * meanDensity(slot) + 0.6 * leaderDensity + 0.35 * distance/diagonal   (+10 if infeasible)
feasible    = slot inside the viewport AND not within 96 px of the hovered star
reserved    = the measured height of that corner's chip + 10 px, so a card stacks above or below the chips
hysteresis  = keep last slot unless another wins by more than 0.12 (the card does not jump while you drift)
fallback    = nothing feasible -> the corner farthest from the star
```

`density(x, y)` is how much subject sits at a screen point. The mock reads it from your still's luminance. *Draft 2:* the live viewer reads the frame itself: inside X_ITE's own end-of-frame callback it copies the canvas to a 192 px wide 2D canvas and reads luminance from that (valid there without `preserveDrawingBuffer`; one read while the dwell runs, again only after the camera moves). If a read ever fails three times it falls back to the projected stars and their tethers (the plan in draft 1). The fallback cannot see the bird, so in the Wide view it picks the pixel-best corner only 6 times in 14; in Flywheel and Crown it stays within 0.25 score of the best in 14 of 14. It is a safety net, not the normal path: every card in the live runs was placed from pixels.

*Draft 2, narrow screens:* below 720 px the card is a sheet inset 22 px from the sides, on the bottom edge (nearest the thumb) or the top edge, whichever leaves the star its 96 px halo and clears the corner chips; if the room is smaller than the card it is cut and fades at the foot.

Results on your stills (lower is better):

| Still | hover | TL | TR | BL | BR | chosen |
|---|---|---|---|---|---|---|
| B | star near the right edge | 0.98 | covers star | **0.83** | covers star | BL |
| A | star near the right edge | 0.76 | covers star | 0.66 | **0.28** | BR |

Known limitation, visible in frame B-4: when the star sits within about 100 px of the right edge, both right-hand slots would cover it, so the card docks far away and the leader line crosses the bird (about 800 px). Options are in section 10; I recommend keeping corner docks as you asked and fading the leader with distance.

Tests (8, all pass): never covers the hovered star; avoids a dense corner; prefers a nearer free corner; respects reserved chip heights; hysteresis keeps a near-tie; hysteresis does not trap a bad slot; narrow viewport becomes a bottom sheet; always returns a slot.

## 5. What hover shows (the deep ontological data)

Every tooltip and card names provenance and grade, because your rule is that every claim carries Confirmed, Likely or Suspected and simulated or recalled things are tagged.

| Tier | When | Shows |
|---|---|---|
| 1 label | 0.15 s | name, kind, provenance tag |
| 2 card | 0.45 s | kind, provenance tag, grade tag, title, key numbers (a Finding leads with its measurements, named verbatim), best evidence quote, top 4 relations with direction, predicate, class and a grade dot, "+n more" |
| 3 deep | 1.2 s or click | ontology-aware block for X3D names (below), edge evidence, source documents, loop membership |

Tags: `data` green, `doc` lilac, `model_recall` and `simulated` ember (simulated dashed), grade dots green (Confirmed), gold (Likely), ember (Suspected). Suspected is common (888 of the 2,476 stars), so it must never look like Confirmed.

**Ontology-aware block** (the "intellified" part). Of the 178 drawn NodeType and Component stars, **105** match an X3D Ontology 4.1 class name (104 distinct; case-insensitive; 95 of those also have XSD verdict rows). For those the card adds: the ancestry chain, the ontology's own definition, field count, and a bar of how the ontology's predicted placements fared against the XSD. For Shape: 59 predicted placements, XSD 4.1 accepts 22, rejects 30, 7 inconclusive, labelled **map, not gate** (the ontology over-predicts legal containment, the finding from the Lentz and Polys work). Validator behind those numbers: `data/xcheck_all.json`, "XSD 4.1 via x3d_mcp validate_xml", run on the x3d_mcp checkout `fa0b389`, ontology sha256 `8307e90…` (verdict totals A 5,206, R 4,570, I 1,309 over 11,085 rows). Grade: **Confirmed** (reproducible from the file).

What the other stars have to show (real counts over the 2,476): 522 carry measured values, 167 carry notes, 2,355 name source documents, 1,946 of 2,412 edges carry an evidence line. 835 stars are untethered (no relations), so their cards show documents and values instead of a relations list.

## 6. What "active, dynamic, semantic-aware" means here without a trade-off

In the page, in memory, with no server call: the pointer drives live lookups into three data blocks and the card re-lays itself out as you move. The scene is not touched. If you later want a live `where_can_place` call against x3d_mcp, that is a server hop and a separate decision; this spec does not need it.

| Data | Source | Cost |
|---|---|---|
| hover index (label, kind, provenance, grade, tier, top 6 relations, degree) | already inside `graph-v3.json`, which the viewer loads today (1.64 MB raw) | **0 new bytes** (as a separate file it would be 260 KB raw, 49 KB gzip) |
| evidence quotes (tier 3) | same file, read on demand | 0 new bytes (188 KB raw, 59 KB gz if split out) |
| star positions for picking | `xyz` and weight per node, same file | 0 new bytes (66 KB raw, 23 KB gz if split out) |
| ontology block (ancestors, definition, fields, XSD counts) | `ontology41.json` + `xcheck_all.json`, trimmed to the 364 classes | **+16 KB gzip** (84 KB raw); the 104 classes that are drawn need only 6 KB gzip |

## 7. Efficiency budget (your "if it is not a trade-off")

| Cost | Measured or planned | Grade |
|---|---|---|
| project 2,476 stars to screen | **about 10 us** per call (node 22, this machine; `bench/pick_timing.js`) | Confirmed |
| rebuild the pick grid (project + bucket) | **about 19 us**; query **0.5 us** (*draft 2:* the shipped `pick.js` with the crowding check measures about 50 us per update) | Confirmed |
| per frame, if it ran every frame | about 0.02 ms of a 16.7 ms budget | Confirmed (arithmetic) |
| extra data | +16 KB gzip (section 6); *draft 2:* the shipped ontology block covers only the 104 drawn classes, 39 KB raw, 7.8 KB gzip | Confirmed |
| extra JS | target 40 KB minified or less, no dependencies | Planned |
| DOM overlay over the canvas | cards are DOM, created on dwell, removed on leave | Likely cheap |
| `backdrop-filter` blur under a card | a blur behind a continuously redrawing canvas can cost GPU time | **Suspected**; fallback is a solid 92% panel, switched on when fps drops under 50 |

Verdict: the picking and data side has no measurable efficiency cost; the only open cost is the compositor and it has a fallback. It is the same single scene in the browser.

## 8. Judge hook (for the picture-judge loop, later and only after you approve the look)

- Scene-look scoring always uses `?ui=none` frames, so the judge compares your stills to the scene, not to chrome.
- UI frames get their own small rubric: legibility, does the card cover the subject, corner discipline, hierarchy, order inside chaos. Deterministic frames come from `?ui=min&hover=<idx>`.
- No judge-model or warehouse spend happens until you say the mock's taste is right.

## 9. Acceptance tests

1. `node docs/v4/mock/test_placement.js` prints 8 passed (done). *Draft 2:* the shipped `gobbler-v4/src/placement.js` has 19 tests (4,000-case fuzz that includes narrow screens, the sheet's halo and chip rules, mutations caught): all pass.
2. Projection accuracy: projected star position within **2 px** of its rendered centre for 200 random stars in each of Wide and Face (to run in real Chromium; Suspected until run). *Draft 2, run on the live scene:* the drawn stars are blurred sprites, so the test regresses the centroids of every isolated sprite against the projection (scale and offset, outliers trimmed). Across two runs scale 0.997 to 1.001 and offset 1.6 px or less in Wide, Inside, Flywheel and Crown: **Likely** (software-GL Chromium). Colossus and Eye have too few isolated sprites to decide (Eye reads scale 0.984, offset 9 px from 17 sprites: unresolved). Face is not a Viewpoint of the Deep scene, so it was not run. After UI none, a camera move and UI minimal the fit is scale 0.9995 to 1.0008, offset 0.5 px or less (200 or more sprites): **Confirmed**.
3. Pick accuracy: at 3 px noise, 90% or better in Inside, Eye and Flywheel, and 81% or better in the wide views with the core-tier LOD (arithmetic done above; re-check on the live scene). *Draft 2, live:* Inside 100%, Eye 92%, Flywheel 91%, Wide 92%, Colossus 80%, Crown 79%. The two wide-view results at 80% and 79% sit just under the 81% the arithmetic predicted (a mouse hover in the page also has the 12 px crowd rule and sprite sizes the arithmetic ignores): **Confirmed** as measured, slightly below target.
4. Placement: with `?hover=<idx>` over 200 random stars per view, the card never covers the hovered star and never covers a chip; the same slot is chosen at least 90% of the time using the projected-geometry density and using the pixel density (proxy check). *Draft 2, live:* 14 random stars in each of Wide, Flywheel and Crown opened by a real mouse hover (42 of 42): none within 90 px of its star, none over a chip, all placed from the frame's own pixels (**Confirmed**). The proxy check changed meaning, because the page now uses pixels and keeps the stars only as a fallback: the fallback picks the same corner as the pixel density in 6 of 14 (Wide), 4 to 10 of 14 (Flywheel) and 11 of 14 (Crown) across runs; in score terms it is within 0.25 of the pixel-best in 6, 14 and 14 of 14. The Wide miss is the bird, which is not in the graph. The 90% bar is not met by the fallback; it is not the normal path.
5. Frame cost on your Mac: fps with a card open is at least 95% of fps with UI none; first-frame time within 3% of v3 Deep. *Draft 2:* software-GL Chromium here, frame interval with a deep card open is 82 to 92% of UI none across two runs (e.g. 204 ms against 221 ms, noise included): no measurable cost, **Likely**. Real GPU: still **Suspected** and still yours to run (`?glass=1` and the Tune panel's glass setting switch the blur on and off to compare).
6. No-leak: the card shows only fields that exist in the graph; every card has a provenance tag and a grade. *Draft 2:* all 2,476 drawn stars at both tiers, no template leak, no field that is not in the graph (`test_cards.js`): **Confirmed**.
7. Stills: `?ui=none` frame is pixel-identical to a v3 Deep frame at the same viewpoint (nothing leaks from the overlay). *Draft 2:* the scene animates (embers, twinkle, sway), so two frames are never pixel-identical. The test became: in UI none no overlay element is visible, no sensor exists and the scene has no added node (**Confirmed**); the `.x3d` file is the Deep file byte for byte (sha256 pinned in `fetch_deep.sh`).

## 10. Decisions I made, and what is yours

I chose these so work can continue; each is cheap to flip.

| Decision | My pick | Alternative |
|---|---|---|
| Card docks in a corner with a leader line | **corner dock** (your "optimal corner placements") | float the card beside the star |
| Dense views hover only the core 648 stars until you zoom (Shift = all) | **core tier first** | every star always (accuracy 72 to 81% when wide) |
| Default level on load | **minimal** | none |
| Dwell times 0.15 / 0.45 / 1.2 s | as listed, tunable | longer, or click only |
| Titles and quotes in the serif, metadata in mono | **serif** | all sans |

## 11. Open items (nothing blocks the taste check)

- The Face camera is not among the Deep scene's Viewpoints that I could read, so pick statistics for it are unmeasured; your two stills are the only evidence so far.
- ~~Camera pose~~ *Draft 2, resolved:* the page does not own the camera. A `ProximitySensor` added to the in-memory scene at run time reports the real pose (it follows the user's orbit); the field of view comes from the active viewpoint. In UI none nothing is added.
- ~~Live density from projected stars~~ *Draft 2, resolved:* the frame's own pixels are the primary source, stars are the fallback (section 4).
- Real-GPU frame cost with the overlay on and off (acceptance test 5): still open, software GL only so far.
- Where this lands in the layer stack: PLAN.md section 6 (add-only, new v4 folder, versioned).

## 12. Built: step 1 on the live scene (draft 2, 28 Oct 2026)

Everything in sections 1 to 5 runs in `gobbler-v4/` as a layer over the Gobbler 3 Deep scene (new folder, nothing replaced; the README there has the commands). What differs from draft 1, and why:

| Draft 1 | Built | Why |
|---|---|---|
| the page owns the camera | a `ProximitySensor` added to the in-memory scene reports the real pose; none is added in UI none | X_ITE's public API does not expose the user's orbit offset; the sensor does, and the scene file stays byte-identical |
| density from projected stars | density from the frame's own pixels, read at the end of X_ITE's frame; stars and tethers only as the fallback | pixels see the bird and the glow; the stars do not (Wide: the fallback agrees with the pixels in 6 of 14) |
| bottom sheet under 720 px | a sheet inset 22 px on the bottom or top edge, clear of the star's halo and the corner chips; cut and faded if the room is smaller than the card | the first sheet covered the star when it sat mid-screen (found in the frames) |
| `H` hides everything while held | and releases the held tour, so the scene keeps moving; losing window focus ends the hold | a held `H` froze the camera |
| fixed dwell, snap and dim | all of them are live settings in a tuning panel (key `T`) | your taste calls from section 10 can be flipped while you look |

**Frames** (real screenshots of the running page, software GL, `?glass=1`; `docs/v4/live/`, kept as JPEG at quality 95; `node gobbler-v4/e2e/frames.js` makes the PNG originals): `1-none.jpg` UI none, `2-rest.jpg` minimal at rest, `3-tooltip.jpg` tooltip with the dwell ring, `4-card-shape.jpg` the NodeType card with the ontology block, `5-card-finding.jpg` a measured Finding after a flight, `6-sheet.jpg` the narrow-screen sheet, `7-tune.jpg` the tuning panel open with a card clear of it, `storyboard.jpg` all seven.

**The tuning panel** (`T`): snap distance, the three dwell times, focus dim, card halo, core-tier-only hover in crowded views, the leader line, frosted glass (auto, always, off). Settings persist per browser. The two taste calls that were mine in section 10 (core tier first, corner dock with a leader) are two switches there.

**What a review found and what was done.** A first review pass found ten behaviour bugs, all fixed with a regression test (two of the tests were shown to fail with the fix removed): hover stalled after a drag or flight until the mouse moved, `Pause tour` restarted a held tour, held `H` or `Shift` stuck after losing focus, an invisible hot zone covered the toggle chip, one readback timeout switched pixel placement off for the session, `?hover=` took any number, ontology names that match `Object.prototype` members threw, the fetch script did not stop on a failed download, and `make e2e-v4` used another port than `make v4`. A second pass at the highest level (run inline as one pass, not as a fan-out of separate reviewers) found more, fixed in the same way: a card measured with sheet leftovers after widening the window, a double-click on a card or chip that flew the camera, a core-tier crowding measure that stayed stale after a camera jump, a leader line drawn to a card that was still hidden, an unescaped `?view=`, a missing provenance that printed "undefined", an unverified download that was installed before its hash check, and X_ITE not hash-pinned.

**Left for later (tests only, nothing user-visible).** The "extra star" check in `test_pick.js` re-tests its own reference; `test_density.js` covers `fromStars` while the page runs `fromGraph`; the seeded random generator is copied into three test files.

**Open.** The Face camera (not a Viewpoint of the Deep scene); the card-to-tether brightening (rows ring the neighbour star only); real-GPU frame cost; the Eye and Colossus projection fits; touch beyond emulation.
