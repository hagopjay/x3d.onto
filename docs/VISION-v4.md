# Gobbler v4 vision spec (owner's words, 27 Oct 2026; arranged by Claude)
Status: requirements only. Nothing built from this yet. Owner called this "my greatest prompt ever".
Evidence for what the stills show: two screenshots from the owner (Hokie gobbler, the "Face" preset). Claude saw them as images; they are not stored in this repo.

## What the stills show (C, read by eye)
- Low-poly gobbler head in profile, triangulated mesh, warm gradient (gold/amber to deep maroon), glowing white node points on the vertices, a detailed amber eye, wattle and snood in red.
- The mesh dissolves to the right into a constellation of nodes and edges: the knowledge graph is the bird's body and feathers. Black starfield, soft bloom, sparse pink and gold stars.
- Viewer UI visible: bottom-left pills "Show text", "Full screen", "Face", "Wide", "Close"; an fps readout bottom-right (about 57 fps in one still). Two slightly different camera positions (one nearer, one more profile). The owner is "particularly fond of this camera aspect".

## Owner's decisions
| # | Decision |
|---|---|
| Lead | **The Gobbler leads.** It is the multiverse ("Gobble is like God"); everything else is secondary to it. |
| Secondary | The village is welcome as a secondary layer; the villagers will eventually build a **space elevator with the Gobbler's help and guidance** (story hook). |
| Scope | Leave the **Shroud out**; use everything else; some Shroud allowed, not all. |
| Scene | **One scene in the browser**, if no efficiency trade-off: "intellified with active, dynamic, ontology- and semantic-aware AI". |
| Look in stills | The KG has become the bird's body and feathers. Order mixes with chaos (Gleick). |
| Stills' role | Between ideal and example: "the KG is too compelling not to compete". |
| Judge | Composition, depth, light, detail and order-mixed-with-chaos; picture-judge vs. the owner's stills. |
| Editing | The loop edits the scene **directly** (via x3d_mcp tools). |
| Spend | **Double the cap** (previous Gobbler cap was $15, so $30 at the owner's word; API spend only, no new GCP resources, no quota or grants without a yes). |

## CORNERSTONE UI requirement (first full statement, owner: "very important")
1. **UI toggle: none / minimal** for stills and hero views; clean frames by default.
2. **Guided mouse**: the pointer drives guided exploration (hover, approach and dwell reveal meaning), not only free orbit.
3. **Optimal UI corner placement** for every panel (preset corners per panel type, never covering the focal subject, collision-aware).
4. **onHover goes live** for real-time, deep ontological data: hovering any node, edge or feather shows class, relations, provenance and grade from the knowledge graph, live, with the ontology (X3D Ontology 4.1) as the semantic layer.
5. This must hold in the real-time browser scene, not only in stills.

## Open questions (few, only if they change the build)
- Third still: not received.
- Does "Gobbler leads" mean the bird is the default home view and every other layer (ontology shell, village, solar system) is reached from it?
- Hover data source: Gobbler 3 Deep's graph-v3.jsonld (provenance and grade on every relation) is the natural feed.
- Efficiency: one scene of 3,759 entities plus a village (12,000 nodes) may cost frames; measure on the owner's Mac before merging layers.
