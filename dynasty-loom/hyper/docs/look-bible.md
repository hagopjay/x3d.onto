# Dynasty hypersphere: look bible (lookdev 1.0)

`proto/hyper/lookdev/`: `gen_lookdev.py` (stdlib, seeded) + `src/*.glsl` + `src/page.html` writes `out/` and `out/receipt.json` (sha256 of all inputs and outputs). Data is labelled stand-in: 300 synthetic threads (252 lives, 48 in-laws), 66 unions; no people. Grades name their tool.

## Units (stated on screen)
- Radius is time: r = 0.08 + 0.003 × (year − 1700) pocket units, or 0.30 per century. The seed sits at the centre (1700). The glass is at r 1.10 and its proxy mesh at r 1.20.
- Nesting: `Transform scale 6`, so the glass is 6.6 host units and a century is 1.8 host units.
- Angle is layout only: 20° per century twist; a child bends off its parent over 14 years; samples every 3 years.

## 1. Glass shell (`shell.frag`, proxy icosphere of 1,280 triangles)
- Ray from `inverse(x3d_ModelViewMatrix)` (pocket pages' recipe); analytic except the haze.
- Rim: Schlick fresnel with F0 0.04. Colour (0.40, 0.56, 1.0) × (1.1(1−cos)^6 + 0.05(1−cos)^2).
- Sky reflection: × F × 2.5 (balanced and ultra only).
- Key glint: (14·k^600 + 0.35·k^24) × F.
- Halo between the glass and the proxy: (0.40, 0.56, 1) × 0.22 e^(−9x)(1−x).
- Time shells at 1750 through 2000 (6 shells). Emission is 0.0012/max(cos, 0.05) + 0.045·e^(−cos²/0.012): a faint glow face-on and a crisp line at the limb. The near crossing counts × 1, the far crossing × 0.5, and an unwoven shell × 0.12. The tint runs from warm (1, 0.60, 0.30) at the core to cool (0.40, 0.55, 1.0) at the glass.
- Fell shell: (1, 0.80, 0.52) × (0.002/max(cos, 0.05) + 0.08·e^(−cos²/0.012)).
- Haze body (every tier): an analytic Gaussian path integral (erf), σ² 0.36, colour (0.42, 0.26, 0.78) × 0.02.
- Haze flow (balanced 12 steps, ultra 28): e^(−r²/0.5) × smoothstep(0.5, 0.9, fbm(direction × 3.3, 3 or 5 octaves)); direction-only noise makes outward streaks; times:
  - ripples 0.6 + 0.4·sin 2π(r/0.15 − t/4), moving outward at 0.0375 units/s;
  - × (0.25 + 0.75·woven);
  - a 12 s energy front;
  - glow accumulated × 0.08 from a jittered start.
- Output: exposure 1.2, ACES, gamma 1/2.2, ±½ LSB dither.
- `gl_FragDepth`: the analytic entry point when outside, the closest approach for halo pixels, and the proxy's far wall when inside, so threads stay crisp in front.
- Ring A (r 6.95) passes between glass (6.6) and proxy (7.2) and composites correctly (frame `glass`; Confirmed by frames).

## 2. Threads (`fiber.vert` / `fiber.frag`)
- One `IndexedTriangleSet` (13,326 triangles) is drawn twice through `USE`. Each polyline point becomes two vertices. Attributes:
  - `FloatVertexAttribute aTan` (3): tangent;
  - `aInfo` (4): side ±1, year, seed, kind (0 life, 1 bend, 2 union, 3 close union);
  - `aAux` (2): along, estimated;
  - `Color`: the dye.
- The vertex shader pushes each side across `cross(tangent, view)`. Width is in pocket units, clamped to a pixel floor and ceiling through `x3d_Viewport`. When the floor wins, the intensity drops by w_world/w so energy is kept. Threads within 0.015–0.06 units of the lens fade out.
- Core pass (opaque, `alphaMode OPAQUE`, writes depth): half-width 0.0026, 0.65–4 px. Colour mix(neon, white, (0.35 + 0.4·tip + 0.3·pulse)(1 − s²)) × lum.
- Glow pass (`alphaMode BLEND`): half-width 0.020, 0.018 or 0.013 (ultra, balanced, fast), 2.5–14 px. Profile 0.7e^(−3.2s²) + 0.3e^(−14s²), × 0.8. Ghost beyond the fell 0.05.
- Colour: neon = dye / max channel (display space); only brightness goes through scalar ACES: lum = ACES(0.9·I)^(1/2.2). Dyes #9e1b1b, #b8860b, #2f6b3a, #3f74a8; in-laws #8d93a3; close unions rose (1, 0.42, 0.70). Full-colour ACES washed dyes to pastel (Confirmed by frames).
- I = 1 + 1.6·pulse + 1.1·front + 2·tip. Unions × 1.2, bends × 0.75. Bends are 0.7 wide and unions 0.75 wide, and a life tapers in from 0.3 over its first 8 %.
- Pulses: (½ + ½cos 2π(year/75 − t/3))^24, so 75 years apart moving 25 years/s outward. Ultra adds a phase of 0.35 × seed.
- Energy front: year 1680 + 380·fract(t/12), σ 10 years. The glass shares the same front.
- Time cut: woven = smoothstep(fell + 1.5, fell − 1.5, year). Tip = e^(−(fell − year)/2.5). The core is discarded past the fell.
- Estimated years are dashed, 4 years on and 3 off; the glow drops to 0.45.

## 3. Founders' core
- Seed: an icosphere of r 0.012 with `PhysicalMaterial` baseColor (1, 0.86, 0.62), roughness 0.2. Emissive (0.8, 0.58, 0.3) breathes 0.6–1.0 via `TimeSensor` (4 s) → `ColorInterpolator`.
- Glow (`seed.frag`, proxy r 0.24): the windowed point integral ∫(1 − r²/Rg²)/(r² + e²), which is closed form and zero at the proxy, so there is no edge. It uses e² = 0.0025·b, colour (1, 0.60, 0.28) × 0.008·b, plus a Gaussian core σ² 0.0007·b × 4.5 (1, 0.90, 0.74). The breath is b = 0.8 + 0.2 sin(2πt/4). Depth sits 0.03 in front of the seed, so the bloom covers it.

## 4. Host sky (`sky.glsl`, inverted icosphere r 400, opaque)
- Seed 0.618, nothing fetched. Base (0.0035, 0.003, 0.009).
- Galactic band: pole (0.28, 0.92, −0.27), weight e^(−7·lat²).
- Domain-warped fbm nebula: 2, 4 or 6 octaves, violet (0.36, 0.05, 0.50) ↔ teal (0.02, 0.30, 0.42) × (0.06 + 0.2·band). Rose (0.8, 0.2, 0.32) × 0.14. Dust lanes from balanced up.
- Stars: hashed grids 60/150/320 (1–3 layers by tier), ~4.5 % of cells, ≥1.3 px wide with energy kept; a layer under ~2 px per cell is skipped (`fwidth` LOD). Magnitude 0.5 + 4.5h⁴; twinkle 3/1.5/1 s; tints (1, 0.74, 0.52)–(0.72, 0.84, 1).
- Every period divides the 600 s loop, so the animation never jumps.

## 5. Light and materials (standard X3D 4.0)
- Key `DirectionalLight global="true"`: direction (−0.45, −0.62, −0.64), colour (0.78, 0.85, 1), intensity 1, ambient 0.1.
- Rim light: (0.55, 0.15, 0.82), colour (1, 0.5, 0.78), intensity 0.55.
- `PointLight` at the seed: global, colour (1, 0.74, 0.45), radius 100, attenuation 1 0 0. Headlight off.
- Armillary rings: r 6.95, 7.75 and 8.35 host; tube 0.022, 0.03 and 0.02; 2,880 triangles each. Gold `PhysicalMaterial` (1, 0.78, 0.45), metallic 0.6, roughness 0.35. At metallic 1.0 they rendered black, since X3D 4.0 has no environment light (Confirmed by frames).

## Standard X3D 4.0 versus X_ITE-only
- Standard, in the `.x3d` (Immersive with Shaders 1, Shape 2, Rendering 5):
  - `ComposedShader` / `ShaderPart`, `FloatVertexAttribute`, `IndexedTriangleSet`, `Appearance alphaMode`, `PhysicalMaterial`, global lights;
  - `TimeSensor` routed to each shader's `uCycle` (600 s), so the pocket animates by itself when Inlined;
  - the seed's breath, and `OrientationInterpolator` orbit (240 s);
  - `ProximitySensor` (HUD: radius → year, and the proxy flips `solid`), `Switch`, `NavigationInfo` EXAMINE or FLY with ANIMATE 1.6 s;
  - three viewpoints, the main one inside a rig `Transform`.
- Page-side, X_ITE-only, behind feature detection:
  - `ToneMapping` ACES_NARKOWICZ and `Exposure` 1.25 (these touch only X_ITE's own materials);
  - `BlendMode` ONE/ONE (ZERO/ONE for alpha) on glow, glass and seed glow, with uBlend = 1 and gains of 0.5 (glow) and 0.7 (glass). Its component is loaded on demand, then `scene.addComponent`, which stops the profile warning;
  - `ContentScale` min(DPR, 1/1.5/2) and `Multisampling` 0/4/4.
- On/off: same composition; additive runs hotter at crossings (frames `hero-ultra-extras` / `hero-ultra-standard`).
- Glow without extras: write (e/max e, max e); SRC_ALPHA blending gives out = e + dst(1 − max e), an order-independent screen. Discard below 0.002.

## Camera
- Outside rig at (7.9, 4.4, 16.9) → (0, 0.2, 0), fov 0.78. Glass view (−6.4, −1.9, 12.6) → (1.3, 0.9, 0), fov 0.62. Inside view (1.9, 0.9, 3.2) → centre, fov 1.05.
- Plunge: a cubic Bézier through (7.6, 2.9, 10.8) and (3.6, 1.2, 5.2) to (0.95, 0.4, 1.75), lasting 9 s with a cubic ease. The look target slides past the seed over the last 45 %, and fov goes from 0.78 to 1.02.
- Vertigo: dolly d 19.1 → 12.5, fov = 2·atan(tan(fov0/2)·k(d)/k(d0)), k = R/√(d² − R²); glass holds size, host swells; 7 s each way.

## CSP findings (`tools/lookdev_csp_gate.js`, the Artifact policy string from the loom gate)
- Raw GLSL in CDATA fails in X_ITE 16.5.1: it becomes the ShaderPart url, is fetched against the world URL, and the shader is invalid, via both `createX3DFromString` (the pocket pages' pattern) and `loadURL`. Confirmed by `tools/cdata_probe.js`.
- Fix: prefix `data:x-shader/x-vertex,` / `data:x-shader/x-fragment,`. X_ITE decodes in place, no request; all 5 shaders `isValid`. No `%` allowed in GLSL (decodeURIComponent); the generator asserts it.
- Only known-harmless refusals: X_ITE's PT Sans UI font (font-src × 3) and mikktspace `wasm-eval`. 15 requests, all same-origin; no data: fetch; no eval; `.x3d` as application/xml. Confirmed by gate; Likely on the real host.

## Tier cost
- 38,492 triangles drawn per frame: threads 2 × 13,326, armillary 8,640, glass 1,280, seed 1,280, seed glow 320, sky 320.
- SwiftShader ms/frame, 1527×923, median of 8 (ratios only): fast 683 ms (1×), balanced 1,383 (2.0×), ultra 2,500 (3.7×); ultra without extras 2,267; ultra inside 2,517; phone 400 × 860 balanced 367.
- The fps monitor (below 22 fps after a 4 s settle) stepped the phone run from ultra to balanced to fast (Confirmed by gate).
- iGPU/phone smoothness: Suspected (no GPU here).
- Known gap: the fast tier's 2-octave sky is softer and pinker.
