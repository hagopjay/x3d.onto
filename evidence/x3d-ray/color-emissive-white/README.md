# A white emissiveColor washes out per-vertex colours

Reported by the x3d-ray project on 2026-10-31. Its ring geometry, an IndexedFaceSet with a Color node under a Material with `emissiveColor='1 1 1'`, drew plain white in X_ITE 16.7.0. The fix in hagopjay/x3d.xray (commit dd3f12b, `x3dray/compiler.py` `ring()`) drops the Material. This folder reproduces the trap in X_ITE 16.5.1 and is the evidence for the Loom gate rule `color-emissive-white`.

Why: in the X3D lighting model a Color node replaces the material's diffuse colour, and the emissive colour is still added on top. With emissive at or near 1 in every channel, every face clamps to white, whatever its colour. Points and lines are unlit and draw their Color as given, so they are not affected.

| File | What it is |
|---|---|
| `probe.x3d` | four quads, each with one red face and one blue face from a per-face Color. Left to right: Material emissiveColor `1 1 1`; emissiveColor `0.85`; a default Material; no Material |
| `probe-unlit.x3d` | a red PointSet and a blue IndexedLineSet, each with Color under a Material whose emissiveColor is `1 1 1` |
| `run_probe.js` | loads one probe in X_ITE in headless Chromium (SwiftShader) and saves `frame-<name>.png` |
| `measure.py` | reads the colour at the middle of each face, point and line → `result.json` |
| `frame-probe.png`, `frame-probe-unlit.png`, `result.json` | the run of 2026-11-01: X_ITE 16.5.1, Chromium 153, Playwright 1.63, no console errors |

Result (8-bit RGB at the middle of each face; the Color asks for red `204 26 26` and blue `26 51 179`):

| Appearance | Red face | Blue face |
|---|---|---|
| Material emissiveColor `1 1 1` | 255 255 255 | 255 255 255 |
| Material emissiveColor `0.85` | 255 242 242 | 242 255 255 |
| default Material | 204 26 26 | 26 51 179 |
| no Material | 204 26 26 | 26 51 179 |
| PointSet / IndexedLineSet under emissive `1 1 1` | 204 26 26 (point) | 26 51 179 (line) |

Both probes validate against x3d-4.0.xsd (xmllint). `loom_gate.py probe.x3d` warns twice, for the first two quads, and is silent on `probe-unlit.x3d`.

Rerun: link a vendored X_ITE as `x_ite/` beside these files, then `NODE_PATH=<playwright> node run_probe.js . probe`, `node run_probe.js . probe-unlit` and `python3 -I measure.py .`.
