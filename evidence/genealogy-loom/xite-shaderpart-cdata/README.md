# ShaderPart CDATA in X_ITE 16.5.1: raw GLSL fails, a data: prefix works

A minimal reproducer for the `shader-raw-source` rule in `gobbler-demiurge/tools/loom_gate.py`. Found on 2026-10-30 in the genealogy loom thread, when HagopJay's three pocket-universe pages, as shared, drew every pocket as a plain white sphere.

| File | ShaderPart CDATA | X_ITE 16.5.1 | xmllint (fork x3d-4.0.xsd) | fork validator acdf5c4 |
|---|---|---|---|---|
| `probe-raw.x3d` | `#version 300 es ...` | `isValid` false; "ShaderPart: Couldn't load URL '…/probe-raw.x3d#version 300 es…'" twice; the sphere draws white (`frame-raw.png`) | valid | 0 errors, 0 warnings |
| `probe-prefixed.x3d` | `data:x-shader/x-vertex,#version 300 es ...` | `isValid` true; no console error; normals drawn as colour (`frame-prefixed.png`) | valid | 0 errors, 0 warnings |
| `probe-percent.x3d` | prefixed, GLSL with `int(gl_FragCoord.x) % 2` | `isValid` true | not run | not run |
| `probe-percent-escape.x3d` | prefixed, GLSL with `int(gl_FragCoord.x) %20` | `isValid` true: the body is not percent-decoded (decoding would leave `x) 0;`, which does not compile) | not run | not run |

All rows are Confirmed: `result.json` holds what `run_probe.js` recorded (X_ITE 16.5.1 from the npm tarball, Chromium 153 with SwiftShader, Playwright 1.63).

**Why it fails.** X_ITE reads a ShaderPart's inline text as its `url` field. Raw GLSL starts with `#version`, which resolves as a fragment of the world URL. X_ITE fetches the scene file itself (the three requests for `probe-raw.x3d` in `result.json`) and the shader is invalid. The XSD and the fork pass the file, because neither looks inside the CDATA. Only a run that reads the console, or `isValid`, sees it: rung 5 (Visible) of the ladder, FACTS item 26.

**Run it.**

```sh
ln -s ../../../gobbler-v4/vendor/x_ite x_ite        # X_ITE 16.5.1 from `make v4-data`
NODE_PATH=<dir with playwright> node run_probe.js "$PWD" raw,prefixed,percent,percent-escape
python3 -I ../../../gobbler-demiurge/tools/loom_gate.py probe-*.x3d   # shader-raw-source: 2 errors in probe-raw.x3d, none elsewhere
```

Set `CHROME=/path/to/chrome` if Playwright's own browser is not installed.

**The rule on real files.**
- It flags all 6 ShaderParts of the three pocket-universe pages as shared, and none once each has its prefix.
- It finds no hit on 798 X3D files from x3d.onto (excluding `xdomain/fuzz`), x3d.ml, x3d-blender-io and the genealogy builds. Of those files, 26 contain ShaderParts, and all of them are prefixed, as `tools/layers.py`, `world_layer.py` and `weave.py` already write them.
