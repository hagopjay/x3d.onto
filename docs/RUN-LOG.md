# Run log

## 27 Oct 2026, headless Chromium (SwiftShader software GL, Linux container), X_ITE 16.5.0 (npm package, served locally in place of the CDN)
- Assets: `solar-town.x3d.gz` gunzips to sha256 33856d7c...f2f982 (matches the README of the pack). 43 textures in `v2/tex` (31 from `v2/textures.py`, 12 from the extra tar).
- Page served with `python3 -m http.server 8791`; X_ITE loaded, scene file parsed, loader stage reached "building the pick registry".
- **Not reached `E.ready` within 1,515 s (25 min).** No screenshot of the live scene was obtained. The page's own estimate is 10 to 40 s on a real machine; software GL on this container is far slower. Grade: S that it works on a GPU browser here (the owner has run it on a Mac); C that the files unpack, hash-match and parse far enough to start the pick registry.
- First attempt failed only because the harness pointed X_ITE at the wrong CDN path (my test script), not the repo.
- Not tested: GPU browser, X_ITE 16.5.1, v1 pages (explorer.html, demo/demo.html).
