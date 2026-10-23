# Ontology Dyson sphere: the razzle-dazzle demo (spec v1)

Decided with the user 2026-10-21: audience = you and your team (private); form = an X3D scene in X_ITE authored through x3d_mcp and validated by it, plus a thin HTML shell; centrepiece = all three modules specified, then pulled into one toy ontology Dyson sphere; the Shroud is left out. It is a **toy**: said in the scene's `<head>`, and on screen.

## 0. Rules the demo keeps
1. Every number on screen comes from a file in this folder and carries its grade (C measured here; L my reading; S simulated). `demo/audit_numbers.py` checks the scene text against the JSON sources and fails the build on a mismatch.
2. Layout, colour and motion are display choices; the head and a corner caption say so. Animation timings are staged (the real timings are quoted as text, not played at real speed).
3. Evaluation results appear only when the runs have finished; until then their pillars are ghosted and say "running".
4. Private until 2027-01-01. No Shroud content. The simulated sc: layer is not included (it can come back as a labelled violet ring later).
5. The scene must itself pass `validate_x3d` (XSD 4.1) and `validate_semantic` with 0 errors, and be authored only through x3d_mcp's tools (head and profile patched in by the script, as before).

## 1. Module A, the shell (ontology)
- 364 classes of X3D Ontology 4.1 on a sphere of radius 8: longitude = layout angle, latitude = class depth; family colours; abstract types as boxes, concrete nodes as spheres; the 9 classes new in 4.1 glow green and pulse.
- A translucent glass shell (transparency 0.9) with latitude and longitude wires; a warm star at the core with a PointLight.
- Edges: the hierarchy as faint chords; the 68 parent placements of Shape as arcs coloured by XSD verdict (green accepts, red rejects, amber inconclusive, blue abstract).
- Data: `data/explorer.json` (nodes, lpv). Captions: "364 classes", "9 new in 4.1", "Shape: 68 predicted parents, XSD agrees with ..." (computed).

## 2. Module B, the flywheel ring (the loop)
- Seven stations on a ring of radius 5.5 in the horizontal plane: spec, agent, x3d_mcp, Blender + fork, runtime (X_ITE), verdict, tether. Each a glowing sphere with a Billboard label.
- One packet circles the ring (12 s per lap, looping). It changes colour with the story: white (spec) -> blue (agent drafts) -> red at x3d_mcp (invalid) -> a second small packet flies back from x3d_mcp to the agent with the report (amber) -> packet turns green (repaired) -> carries on through Blender and the runtime -> verdict -> a gold stamp pulse at the tether and the lap restarts with the chain one link longer (a growing arc).
- Quoted numbers (text only, with grade): whole-scene validation 1.8 s and per-call median 1.9 ms (C, constellation run); first-try 27.3% -> 56.7% with two examples, about 100% after report-guided repair (doc, C, E1); 6 of 6 scenes kept the provenance record through Blender (doc, C).

## 3. Module C, the three-domain moons
- Three tilted rings around the core: X3D (37 components, bead colour = XSD-accepted share of the ontology's placements, size = node count), URDF (24 fault operators), glTF (25 fault operators); bead colour for the last two = who catches the fault (parse, structure, semantics/Khronos error, warning only, contact), size = mutants.
- Per domain a pair of pillars next to its ring: first-try validity (blue) and after the report loop (green), from `eval-plan/runs/*.jsonl` when present; ghosted with "evaluation running" otherwise. A small amber marker shows the deterministic-repair-only level.
- Quoted numbers: URDF 135 mutants (L), glTF 123 mutants, 86.2% error-level by Khronos (C), warning-only 17 (C), X3D 7,604 containment pairs, 50.3% accepted (C).

## 4. The merge: "assemble"
- Start state "Row": module B far left (x = -26, scale 2.2), module A in the centre, module C far right (x = +26, scale 2.2); three bound viewpoints (Flywheel, Shell, Domains) and a wide one (Row).
- On trigger (button in the HTML shell, or touching the ASSEMBLE sign in the scene) a 16 s sequence runs from one TimeSensor: B and C translate to the origin and scale to fit inside the shell (B at radius 5.5, C rings 5.0 to 6.5), the camera flies from Row to a slow orbit outside, the star flares, the shell wires brighten, captions step: "Spec" -> "Validate" -> "Map" -> "Domains" -> "One loop".
- After assembly: continuous slow rotation of the shell, packets keep lapping, rings precess. A second trigger "Disassemble" reverses it.

## 5. HTML shell (`demo.html`)
X_ITE canvas; top-left title and the TOY / PRIVATE / numbers-graded caption; buttons: Row, Shell, Flywheel, Domains, Assemble, Disassemble; a caption strip synchronised to the assemble sequence; a footer with source files and grades; no network except the X_ITE CDN.

## 6. Build and checks
`demo/make_demo.py` (MCP stdio client, as `harness/make_constellation.py`) -> `demo/scenes/ontology-dyson.x3d`; `demo/audit_numbers.py`; `demo/check_render.js` or a browser-pane screenshot per viewpoint; size budget under 2 MB; node count and tool-call count recorded in `out/demo_run.json`.

## 7. Phases and acceptance
| phase | content | accepted when |
|---|---|---|
| P1 | module A on its own | valid; 9 new classes glow; Shape arcs coloured |
| P2 | module B | packet laps, colour story visible, back-flowing report packet |
| P3 | module C | three rings, beads, pillars (ghost or real) |
| P4 | merge animation, camera, HTML shell | assemble and disassemble run clean in X_ITE |
| P5 | audit and polish | audit_numbers passes; validate 0 errors; screenshots reviewed |

## 8. Known risks
Interpolator and ROUTE counts raise the semantic-check info noise (unused DEFs, as before). X_ITE transparency sorting can flicker on dense shells (fallback: shell wires only). Evaluation pillars depend on the background runs finishing.
