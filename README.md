# x3d.onto

Private. The ontology work of the x3d family, extracted from the Mac working tree on 27 Oct 2026.

| | |
|---|---|
| **v2** `v2/` | "Sun, Earth, Moon and a village": one X3D scene (12.9 MB, 12,557 x3d_mcp tool calls) holding the 364 classes of X3D Ontology 4.1 on a 2.4 AU shell, three domain rings, the agent flywheel loop, a village of 17 buildings and 12 H-Anim style villagers, floating-origin camera, staged eclipse. Details: `docs/V2-README.md`. |
| **v1** root | Ontology explorer (`explorer.html`), constellation (`constellation.html`), Dyson-sphere demo (`demo/demo.html`), harness, cross-domain URDF/glTF validator loops (`xdomain/`), simulated sc: layer (`sim/`, grade S), narrowed-ranges proposal (`proposal/`, HELD, unsent). Details: `docs/ONTOLOGY-V1-README.md`. |
| **assets/** | `solar-town.x3d.gz` (generated v2 scene), `v2-textures-extra.tar.gz` (12 textures not produced by `v2/textures.py`), `flywheel/trace-pipeline-source.tar.gz` (flywheel source, sanitised). |
| **docs/integration/** | How this meets x3d_mcp, the Blenderizer and Gobbler. |

## Run
```
make demo     # unpacks assets, serves http://127.0.0.1:8791/v2/index.html
```
Needs python3 with numpy and pillow. The page loads X_ITE 16.5.0 from the jsdelivr CDN, so the browser needs internet. Software-rendered browsers are slow: see `docs/RUN-LOG.md` for measured load times.

Rebuilding the scene from code (17 min, needs an x3d_mcp checkout) is optional: the generated scene is shipped.

## Rules (from the owner)
Private until 2027-01-01. Grades C/L/S/I on every claim. Nothing goes to outside repos or the Web3D Consortium without an explicit "send". Before any public candidate: rewrite history (author emails), scrub model/vendor names and cost figures.
