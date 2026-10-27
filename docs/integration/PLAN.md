# Integration plan: x3d.onto with the x3d family (draft, 27 Oct 2026)
Grades: C confirmed from files read, L likely, S suspected. No model calls were used to write this.

## 1. What x3d.onto needs from siblings (all C unless noted)
| sibling | what x3d.onto uses today | pin / gap |
|---|---|---|
| x3d_mcp fork (hagopjay/x3d_mcp) | v2 scene authored by `v2/make_v2.py` through the MCP stdio tools; harness is read-only on the checkout; v1 numbers computed on unpushed branch `fix/physics-findings` (`fa0b389`) | fork main is `2b696f5` (this session) with PR #12/#13 (ontology tools: `query_ontology_page`, `where_can_place`, claims). Re-run v1 harness tests on main and name the pin (open). |
| Blenderizer (hagopjay/x3d-blender-io) | not used yet | candidates below |
| x3d.ml (hagopjay/x3d.ml) | not used yet | Gobbler v3 graph (`gobbler-v3/`) is the natural v4 host |

## 2. Proposed seams (cheap first)
1. **Pin file** `docs/PIN.md` naming x3d_mcp commit + X3DUOM + X_ITE versions behind every number (rule: name the validator). Replace the unpushed-branch pin. (S: tests may differ on main.)
2. **where_can_place as the oracle**: v1 `xcheck_all.py` computes XSD verdicts for 11,085 (parent, child) pairs; PR #13's `where_can_place` table (6,509 rows from X3DUOM) is the maintained equivalent. Swap harness to call it; diff against `data/xcheck_all.json` (L: should agree on UOM-vs-XSD 93%).
3. **Blenderizer round trip of v2**: import `solar-town.x3d` into Blender via x3d-blender-io, export, re-validate. Tests whether a 12.9 MB, 12.5k-node scene with Layers, H-Anim and interpolators survives (S). Also gives a Blender-rendered still of the village for the Gobbler look.
4. **Ontology as a Blender-side asset**: the 364-class shell exported as a collection (instances per class, custom property = IRI) so Blender owns the look and X3D stays the validated master (matches stack rule: X3D master, Blender owns the look).
5. **Tether loop**: use-type-mismatch check (fork branch `claude/ontology-lentz-polys-3j5h8z`, 96/96 injected found, 0 false alarms on 200 scenes, fork eb4b4b4) run over every scene this repo builds.

## 3. Gobbler v4: order inside the chaos (design sketch, nothing built)
Gobbler v3 draws 604 entities / 1,179 relations / 15 loops as a dense graph (`x3d.ml` `gobbler-v3/GRAPH-v3.md`). Ideas, ranked by risk:
1. **Orbital grammar for order.** Keep the graph chaotic at the micro level; give it one ordered macro-structure: the ontology shell (364 classes on a sphere, already built) as the "sky", entities from the graph attached to the class they instantiate. Order = geometry of the shell; chaos = the graph's tangle between shells. (Gleick's strange attractor: bounded, never repeating.)
2. **Scale ladder as the camera path.** v2's floating-origin rig and van Wijk-Nuij flights already travel 1e12 m to 0.5 m; reuse it so a Gobbler entity can be "zoomed into" and become a village building.
3. **Village = loops.** The 15 flywheel loops become walking paths of the 12 villagers (position interpolators already exist); a loop with measured results gets lit windows.
4. **Eclipse as the reveal.** The staged eclipse lights lamps and shows the corona; use it as the transition from overview to evidence view.
Open: how much of v3 is drawn (604 of 2,734 entities) vs ordered; whether the shell stays spherical or follows ontology depth.

## 4. Order of work (my default if you say go; no model spend)
A. PIN.md + RUN-LOG.md (this PR). B. Blenderizer round trip of v2 (needs Blender, probably on your PC via Remote Control). C. where_can_place swap. D. Gobbler v4 sketch as an X3D mock after your taste check.

## 5. Not for public yet
History carries author emails; docs name models and costs (`xdomain/eval-plan/*`, `cost_table.md`); sim/ is a guess, not Polys's ontology; Shroud ledger layer stays out until 2027-01-01.
