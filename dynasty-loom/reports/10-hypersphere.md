# 10 · The hypersphere in the Dynasty Loom Artifact

The Artifact now opens on the **hypersphere**; the **loom** is one click, V, or `#loom` away, and draws exactly as before. Nothing is published (file map: `proto/scene2/artifact/publish.json`).

## Concept and mapping

Each family is a glass time-sphere (`build_hypersphere.py` 1.2, from `loom-view.json`):

- **Radius = time:** the founders' seed at the core, 2026 at the glass, stated on screen (Rothschild: 313.5 years per pocket unit, a shell every 50 years).
- **Azimuth:** houses west to east by longitude, each sector ∝ 2 + its people.
- **Elevation:** order of descent; layout only, and the page says so.
- **Fiber:** a life from r(born) to r(died), bent on a move's shell; dotted where a year is estimated.
- **Arc:** a marriage on its year's shell, doubled if close (φ > 0).
- **Dye:** share of descent, stepped by generation; ecru = 0.

Both views read one `.cards.json` (byte-identity enforced), so cards, narration and grades match.

**One page, two engines.** The new `scene2/tools/merge_views.py` (deterministic, standard library) generates `page/index.html` from `page/loom.html` (the tapestry page, unchanged) and `hyper/page/index.html`.

- One shared chrome, so both gates' element ids hold.
- Each page's script runs verbatim apart from 45 anchored edits, each matching exactly once.
- A shell owns X_ITE, the hash (`#hypersphere`, `#loom`, `#<family>`, `#loom/<family>`) and the switch.
- One canvas per view, made on first open; the hidden one is `display:none`, so X_ITE pauses it.
- A switch carries the family, the story beat and a picked person.

## Camera grammar

Source: `hyper/docs/camera-grammar.md`.

- **Shots** are standard Viewpoints the pocket EXPORTs and the host IMPORTs: Host (ELS), Inside (POV, FLY), Colossus (MS, low), EyeToEye (CU, rolled), Crown (LS), one MS per house, Present (MCU), Wide (LS), and Flywheel (a scriptless 120 s idle orbit).
- **Flights** use a Probe Viewpoint in a ProbeFrame, moved by a van Wijk–Nuij zoom-and-pan (ρ = √2) with a quintic ease. The plunge takes 7 s and passes through ShellSense.
- **The tour** never cuts between two same-size shots; each move turns ≥ 20° or changes distance ≥ 2×. User input always wins.

## Look recipes

Source: `hyper/docs/look-bible.md`.

- **Glass:** a ComposedShader on a 1,280-triangle proxy. It draws a fresnel rim, time shells and erf + fbm haze, tone-maps in-shader (ACES, gamma, dither) and writes `gl_FragDepth`, so the gold rings composite.
- **Threads:** one IndexedTriangleSet drawn twice by USE, as an opaque core and a blended glow. Width is pixel-clamped with energy kept; pulses, the fell cut and a uFocus-eased selection animate it.
- **Seed, sky, light:** a breathing PhysicalMaterial seed; an fbm nebula with hashed stars; key, rim and seed lights.
- **X_ITE-only extras** (additive BlendMode, ContentScale, Multisampling) are feature-detected. Without them the scene stays standard X3D 4.0 with the Shaders component.
- **New:** the Blender Cycles hero plate is the loading still and fades out once the sphere is live.

## From the user's pocket pages

From the brief and `hyper/docs` (pages not reopened).

| Pocket technique | Where it went |
|---|---|
| A ComposedShader on a sphere proxy, with the ray from `inverse(x3d_ModelViewMatrix)` | Glass, seed glow, bead |
| `gl_FragDepth`; ACES, gamma and dither in the shader | All shaders |
| Nebula, hashed stars and `fwidth` LOD | Sky |
| Glow accumulated along the march | Haze |
| Quality uniform driven by an fps monitor | Tiers that lower themselves below 22 fps |
| Nesting by Transform scale; a ProximitySensor | The pocket at ×6; ShellSense |
| Instancing by USE | Threads drawn twice |
| Camera rig and the eased "Plunge in" | Probe flights |
| Outside/Inside viewpoints with EXAMINE and FLY | Host and Inside |

Two changes, both Confirmed:

- The rig's fixed centerOfRotation drifted 983 px after a plunge; the Probe drifts 0 px.
- Raw CDATA GLSL became a URL fetch in X_ITE 16.5.1, so the shaders now carry a `data:x-shader/…,` prefix, which X_ITE decodes in place.

## Gate results

Tools: X_ITE 16.5.1 (vendored, tarball-identical), Chromium 153.0.8010.12 (SwiftShader), Playwright 1.63.0, node 22.22.0, Python 3.13.17, xmllint (libxml 20914), the fork's `validate_x3d.py`, and `lookgates.py`.

- **merge_views.py:** no eval, `new Function` or data: fetch; its `--check` rebuild is byte-identical (Confirmed, sha256).
- **build_loom_scene.py --validate:** 3 scenes CLEAN. The `.x3d` and `.cards.json` files are byte-identical to the pre-merge build (Confirmed, cmp).
- **xmllint (x3d-4.0.xsd) and the fork validator:** all 9 shipped `.x3d` files, 0 errors, 0 warnings (Confirmed).
- **gate_loom.js --all-stops: 54/54** (Confirmed), with a clean console, local requests only, and lookgates passing all 41 frames.
  - The gate's only change: its URL asks for `#loom`.
  - A pixel diff against fix round 09's final frames finds changes only in the header and the key-hint line (Confirmed, numpy).
- **gate_hyper.js --artifact=scene2/artifact** (a new option: 175 checks run on the merged page):
  - **Run 1: 171/175.** Three smoothness checks sampled only 5–12 poses around 1.5–3.1 s SwiftShader frames; one 404 for X_ITE's PT Sans UI font, which `make_artifact.py` now ships.
  - **Run 2: 174/175**, console 0. "shot Host (native bind)" failed on 8 sensed poses with a 1.27 s frame, as in build 3's run 1.
  - **Isolated A/B** with the gate's own analysis (`work/merge-bench/host_bind_ab.js`): standalone 5/5 smooth, merged 5/5, so a sampling flake, not a regression (Likely).
  - **Run 3: 175/175**, console 0 (Confirmed; `hyper/gate-artifact.json`).
- **artifact_csp_gate.js** (rewritten for two views; a strict copy of the Artifact CSP): **PASS** on desktop light 1527×923 and phone dark 400×860, 19 checks each.
  - Default view, every family in both views, all four hash forms.
  - Shaders `isValid`, labels drawn, loading still shown then gone.
  - The button and V carry family and picked card; Fell and Tour drive only the active view.
  - Same-origin X_ITE, no errors, no missing files. Only the known-harmless refusals (PT Sans font-src, `wasm-eval`). Likely on the real host.
- **Frames:** all four Artifact frames pass lookgates; I read each.
- **make_artifact.py:** 87 files, 13,024,244 bytes. No secrets; 302 people in the cards, none possibly living, and every `.hyper.json` person is among them. Deterministic: a second run differs only in the absolute paths in `publish.json`.

## Costs

- **Triangles per frame (hypersphere):**

  | Family | Triangles |
  |---|---|
  | Rothschild | 42,032 |
  | Habsburg | 30,380 |
  | Darwin–Wedgwood | 28,372 |

  Fill (the raymarched glass and sky) dominates.
- **SwiftShader median frame time at 1527×923** (relative only; gate run 2):

  | Tier | Frame time | vs Fast |
  |---|---|---|
  | Fast | 483 ms | 1× |
  | Balanced | 900 ms | 1.9× |
  | Ultra | 1,633 ms | 3.4× |

- **The merge costs no measurable frame time:** with the clocks frozen, merged/standalone ratios are 0.90, 1.03 and 0.96 (`ab_bench.js`).
- **iGPU and phone smoothness:** Suspected (no GPU here).
- The loom's X_ITE browser starts only when its view opens.
- **Artifact:** 13.0 MB, up from 6.6 MB.

## Open issues

1. Once both views have been opened, two WebGL contexts stay alive; phone memory is untested.
2. The loading still is a build-2 Rothschild render, so its dyes predate build 3 (the caption says it is a still).
3. `scene2/out/index.html?local=1` opens on the hypersphere, whose files live in `hyper/out`. Test through `scene2/artifact` instead.
4. `scene2/receipt.json` still describes round 09 (`write_receipt.py` hard-codes its change list). This round's receipts: `page/merge-receipt.json`, `out/receipt.json`, `artifact/receipt.json` and the gate JSONs.
5. Whether the host keeps a `/` in a hash is unknown; plain `#loom` and `#habsburg` both work.
6. Inlining into Gobbler is untested.
7. Critique round 2 scored 6/10, so the hypersphere is not demo-ready yet. The merge left the look unchanged; a new critique pass is due.
