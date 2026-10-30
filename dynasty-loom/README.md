# Dynasty Loom (v3)

Three families' public genealogy drawn as X3D 4.0 scenes in X_ITE 16.5.1: the Rothschilds (120 lives, 43 marriages), the Habsburgs (106, 39) and the Darwin–Wedgwoods (76, 12). One page, two views:

- **Hypersphere** (the default view). Each family is a glass sphere of time.
- **Loom.** Each family is a tapestry on a loom.

Both views read the same person cards, so the narration, sources and grades match.

**Live:** [Dynasty Loom on claude.ai](https://claude.ai/artifact/BRwe3b1L48fAkxDzDsvcm1). It is a private Artifact. Version 3 was published on 30 October 2026, and `release/v3/` holds exactly the bytes that version serves.

| Hypersphere | Loom |
|---|---|
| ![Rothschild hypersphere, wide](frames/03-rothschild-hyper-wide.webp) | ![Rothschild loom, wide](frames/10-rothschild-loom-wide.webp) |

## What the views show

**Hypersphere** (`hyper/build_hypersphere.py` 1.2). The mapping is stated on screen:

- **Radius is time, to scale:** the founders' seed at the core and 2026 at the glass, with a shell every 50 years. For the Rothschilds, one pocket unit is 313.5 years.
- **Azimuth:** houses run west to east by longitude, and each house's sector is proportional to 2 + its people.
- **Elevation:** order of descent. It is layout only, and the page says so.
- **Fibers:** a life is a glowing fiber from r(born) to r(died). It bends on the shell of a move, and is dotted where a year is estimated.
- **Arcs:** a marriage is an arc on the shell of its year, doubled when the couple share founders.
- **Dye:** each fiber is dyed by its share of descent from the founders. Ecru means an in-law.
- **Decoration:** the nebula sky and the pewter armillary carry no data.

**Loom** (`tapestry/build_loom_scene.py`, layout v2):

- **Time runs up the cloth.**
- **Houses** stand west to east by the longitude of their seat, and latitude is a small depth.
- **Warp threads:** each life is an upright warp thread from a birth bead to death. It bends only when the person moves house.
- **Weft picks:** each marriage is a level weft pick, doubled when the couple share founders. It is translucent where the year is estimated.
- **Dye:** the share of descent from each dye's founders. An in-law's thread stays faint until their first wedding.
- **The fell:** the present-year plane, which the slider moves.

Both views have:

- a guided tour per family (12 stops for the Rothschilds, 8 each for the others);
- click for a person card with sources and a grade;
- quality tiers;
- `#hash` routing: `#hypersphere`, `#loom`, `#<family>` or `#loom/<family>`.

**Data:** `data/loom-view.json` (contract: `data/loom-view.md`) holds 302 people. It is the *public-candidate* view written by `ingest/` (`ingest.py` 0.2.0, `loomview.py`). Anyone possibly living is left out, together with any union that touches them. "Possibly living" means born within 110 years of 2026 with no death recorded. `data/loom-view.receipt.json` is that run's receipt. `data/data-issues.json` lists what the tapestry generator found while drawing; none of it is patched in the scene.

## Layout

| Folder | What it holds | Original workspace path |
|---|---|---|
| `data/` | the build's only input, its contract, its ingest receipt, the data issues | `proto/merged/`, `proto/contracts/` |
| `ingest/` | the pipeline that wrote the data, with its config, curated decisions, schema, tests and the GEDCOM 7 prototype (`gedcom7.py`, with a fictional fixture in `fixtures/`) | `proto/ingest/` |
| `tapestry/` | the loom generator, the loom page, the page merge, the publish stage and the live gates | `proto/scene2/` |
| `hyper/` | the hypersphere generator, its GLSL (`src/`), its page, its tools and gates, its docs (look bible, camera grammar), the Cycles hero-still scripts and the two plates the page shows while loading (`hero/plates/`) | `proto/hyper/` |
| `x3d/` | `build_genealogy_x3d.py` (the first, drum generator; the loom imports its helpers), the Ubuntu Mono TTF label font and its licence; `vendor/x_ite/` is fetched, not committed | `proto/x3d/` |
| `gates/` | `lookgates.py` (frame gates), `datagates.py` (used by ingest), the source gates | `proto/gates/` |
| `release/v3/` | the published file set without `x_ite/`; `SHA256SUMS` for all 87 published files, `x_ite/` included; `publish.json` (the Artifact files map, with relative paths); `receipt.json` (the publish stage's receipt, as published) | the published file set |
| `tools/` | `vendor_xite.py`, `rebuild.py`, `validate_x3d.py` (the x3d_mcp fork validator wrapper) | new; `validate_x3d.py` from the workspace |
| `frames/` | 12 curated stills (WebP) with `receipt.json` (source and sha256 of each) | gate frames, Cycles posters |
| `reports/` | the project reports 01 to 10 | the workspace reports |
| `provenance.json` | every file copied from the workspace: its source path, its sha256 at copy time, and whether it was edited for repo paths | new |

Some text still names the original layout:

- generated text (the `<meta name='data'>` in the pocket scenes, the comment at the top of the merged page);
- docstrings;
- receipts.

That text is kept as it was, so the published bytes do not change. Read `proto/merged` as `data/` and `proto/scene2` as `tapestry/`.

## Rebuild

You need Python 3.13 (standard library only for the build) and network access to registry.npmjs.org once.

```sh
python3 -I dynasty-loom/tools/vendor_xite.py   # X_ITE 16.5.1 from the npm tarball (sha256 pinned) -> x3d/vendor/x_ite/ and release/v3/x_ite/
python3 -I dynasty-loom/tools/rebuild.py       # merge -> loom -> hypersphere -> publish stage into dynasty-loom/build/, then compares with release/v3
```

`vendor_xite.py` does three things:

- It fetches X_ITE and checks the tarball against its pinned sha256 (`f93bc35f…71be5`).
- It writes the build copy to `x3d/vendor/x_ite/` and keeps the tarball beside it.
- It writes the 65 X_ITE files the release ships under `release/v3/x_ite/`, and checks every one against `SHA256SUMS`. A mismatch fails the run.

`rebuild.py` runs the stages in order, each as its own `python3 -I` process:

1. `tapestry/tools/merge_views.py` builds `tapestry/page/index.html` from `tapestry/page/loom.html` and `hyper/page/index.html`.
2. `tapestry/build_loom_scene.py data/loom-view.json --out build/tapestry`.
3. `hyper/build_hypersphere.py --cards build/tapestry --out build/hyper`.
4. It copies the two Blender plates in.
5. `tapestry/tools/make_artifact.py --out build/tapestry --hyper build/hyper --artifact build/artifact`.

It then compares every published path by sha256, and compares `receipt.json` field by field. It exits 1 if a published file differs.

Generated files are git-ignored and never edited by hand: `tapestry/page/index.html`, `*/out/`, `build/`. Change a generator, `hyper/src/`, a page source or the data, then rebuild. The two loading plates come from `hyper/hero/` (Blender 5.2.3 Cycles, `hero_render.py`, then `hero_finish.py`). They are committed rather than re-rendered.

**Reproducibility caveat:** the loom scenes carry the build date (`<meta name='created'>` and the `generator` meta). A rebuild on another day differs in those two lines of the three loom `.x3d` files and nowhere else.

## Gate

```sh
cd dynasty-loom
xmllint --noout --schema "$X3D_MCP/src/validation/schemas/x3d-4.0.xsd" release/v3/*.x3d
X3D_MCP=/path/to/x3d_mcp  /path/to/python-with-lxml -I tools/validate_x3d.py release/v3/*.x3d
python3 -I ../gobbler-demiurge/tools/loom_gate.py release/v3/*.x3d
NODE_PATH=/opt/node-tools/node_modules node tapestry/tools/artifact_csp_gate.js --artifact=release/v3   # Chromium path: GEN_CHROME
```

The live gates are `tapestry/tools/gate_loom.js` and `hyper/tools/gate_hyper.js`. They serve the tree over a local http server and drive X_ITE in headless Chromium (SwiftShader). They take their frame-gate Python from `LOOM_GATE_PYTHON`, which needs numpy and Pillow. `build_loom_scene.py --validate` reads `X3D_MCP` and `LOOM_FORK_PYTHON`.

## Publish (the Artifact recipe)

The page is `release/v3/index.html`. The files map is `release/v3/publish.json`: published path to file, with relative paths, so use `release/v3` as the root.

- **Page fragment.** `make_artifact.py` strips the document shell (doctype, html, head, body, metas), because the host wraps the page itself. The page must open with its `<title>`.
- **Scenes as XML.** `.x3d` files are served as `application/xml`, which X_ITE needs. JSON is served as `application/json` and the label font as `font/ttf`.
- **TTF label font.** The labels use Ubuntu Mono as a plain TTF beside the scenes. X_ITE's own WOFF2 goes through a decoder it runs with `new Function`, which the Artifact CSP refuses.
- **Vendored X_ITE.** X_ITE 16.5.1 ships beside the page (`<meta name="loom:xite" content="x_ite/x_ite.min.js">`), and jsDelivr is only a fallback. X_ITE fetches its components, PBR lookup tables, line types and wasm from beside its script, and the CSP admits a CDN for scripts only.
- **Hash routing.** Routing uses a plain `#hash`, with no `/` needed.
- **Pre-publish gates.** `make_artifact.py` checks, before it writes anything:
  - no secret-shaped strings;
  - no possibly-living person in any card or `.hyper.json`;
  - every `.hyper.json` person is in the family's cards;
  - every link host is listed;
  - the Artifact limits (64 MB, 15 MB a file, 255 files).

## Status: what was checked (30 October 2026)

| Claim | Grade | Tool |
|---|---|---|
| `release/v3/` plus the vendored `x_ite/` is byte-identical to the published v3: all 87 files match `SHA256SUMS`, which was written from the frozen v3 set. That set also matches the per-file sha256 in `receipt.json`. | Confirmed | sha256 (Python hashlib) |
| A clean export of this folder rebuilds all 87 published files byte-identically. `receipt.json` differs only in `source` and `hyper_source`, the output paths. `make_artifact.py` is byte-identical to the v3 script, and its sha256 matches the receipt's `script` field. | Confirmed | `tools/rebuild.py` on a `git checkout-index` export, with `vendor_xite.py` |
| The 9 `.x3d` files validate against x3d-4.0.xsd. | Confirmed | xmllint (libxml 20914) |
| The 9 `.x3d` files have 0 errors and 0 warnings from the fork validator, with XSD and profile ok. Info lines are 16 to 112 per file. | Confirmed | x3d_mcp fork `acdf5c4`, `tools/validate_x3d.py` |
| The x3d.onto Loom gate finds 0 errors in the 9 files. It reports 6 `glsl-logdepth` warnings and 59 precision infos; the warnings are the SeedGlow and ShellShader in each pocket, which write `gl_FragDepth`. | Confirmed | `gobbler-demiurge/tools/loom_gate.py` at x3d.onto `77ae473` (PR #4 branch, sha256 `ec08ef75…`) |
| The same gate at this branch's base (`2fed4ee`) also finds 0 errors. It adds 6 `glsl-int-literal` warnings on `smoothstep(0, …)` in SkyFS and ShellFS, a false alarm that PR #4 fixes. | Confirmed | `gobbler-demiurge/tools/loom_gate.py` at `2fed4ee` |
| The Artifact CSP gate passes on desktop light 1527×923 and phone dark: 19 of 19 checks each. The console is clean apart from three known-harmless entries:<br>• X_ITE's PT Sans UI font, refused by `font-src`;<br>• mikktspace `wasm-eval`;<br>• the local server's `favicon.ico` 404. | Confirmed (local strict-CSP copy); Likely on the real host | `artifact_csp_gate.js`, Chromium 153.0.8010.12, Playwright 1.63.0, node 22.22.0, SwiftShader |
| No possibly-living person is in `data/`, the cards, `.hyper.json` or any committed JSON. | Confirmed | make_artifact's rule, re-run over every committed JSON |
| No secrets: no key-shaped strings, private keys or assigned API keys. | Confirmed | regex scan of every committed text file |
| No AI model names are in the committed files. | Confirmed | regex scan of every committed text file |
| The hypersphere's live gate on the merged page passed 175 of 175 checks with a clean console (run 3). | Confirmed | `hyper/tools/gate_hyper.js --artifact` (report 10) |
| Run 2 passed 174 of 175, and run 1 passed 171 of 175. The failures were smoothness samples on SwiftShader, so they are flakes of the software renderer. An isolated A/B was smooth 5 of 5 on both the standalone and the merged page. | Likely | `gate_hyper.js`'s own analysis (report 10) |
| The loom's live gate passed 54 of 54 checks with a clean console, and lookgates passed all 41 frames. | Confirmed | `tapestry/tools/gate_loom.js --all-stops` (report 10) |
| The family facts are graded per person in the cards: Confirmed, Likely or Suspected. | as graded | ingest gates (reports 03 and 08) |

## Known rough edges (v3)

- The opening caption still describes the tapestry's "upright threads".
- The caption panel is too tall.
- The landing inside the glass is muddy.
- The camera-smoothness checks can flake on the software renderer (see above).
- Once both views have been opened, two WebGL contexts stay alive. Phone memory is untested.
- The loading still is a build-2 render, so its dyes predate build 3. The caption says it is a still.
- The last art critique scored the hypersphere 6/10. The look is not final.
- `ingest/` reads a harvest, fact-check files and the original upload, none of which are in this repo. It cannot re-run from here; `data/loom-view.json` is its committed output. Its GEDCOM 7 prototype refuses GEDCOM 5.5.1, the version most real `.ged` files use.
- Inlining into the Gobbler is untested.

## What was changed on the way in

- **Paths.** Scripts that pointed into the original workspace now use paths relative to this folder (`Path(__file__)`), or an environment variable whose default matches the old behaviour:
  - `X3D_MCP` for the fork's XSD and validator;
  - `LOOM_FORK_PYTHON` and `LOOM_GATE_PYTHON` for the validator's and gates' Python;
  - `LOOM_BPY_VENV`, used only as a label.

  The edited files are `tapestry/build_loom_scene.py`, `hyper/build_hypersphere.py` (two defaults), `hyper/hero/hero_finish.py`, `hyper/tools/{finish_receipt.py, build_camera_proof.py, gate_hyper.js, probe_look.js}`, `tapestry/tools/{gate_loom.js, write_receipt.py}` and `tools/validate_x3d.py`. `provenance.json` lists each one with its original sha256. Every other script is byte-identical to the one that built v3.
- **Reports and the hero receipt.** Absolute workspace paths were shortened to `scratchpad/…`. In reports 01 and 07, the names of the AI models behind some of the original upload's documents were replaced with `[model]`.
- **Left out:**
  - the uploaded zip and anything copied from it;
  - every `.env*` file;
  - `dist/`, `node_modules`, the virtual environments;
  - `work/`, `tmp/` and `out/` folders;
  - the private data build (`proto/merged/private/`, `gates.json`);
  - the full public-candidate exports (`genealogy.*`, `cosmos-datasets.json`), which are not build inputs;
  - development probes (`hyper/hero/probe_*.py`, `scene2/adapt_harvest.py` and its `dev/` view), lookdev scenes, proof builds;
  - all gate frame runs except the 12 curated stills.
