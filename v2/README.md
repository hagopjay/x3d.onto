# Ontology constellation 2 (v2): Sun, Earth, Moon and a village

A toy vision of x3d · mcp · agents · ontologies, branch `v2-solar` (v1 is tagged `v1-constellation`).
One X3D scene graph, authored node by node through the `x3d_mcp` fork, spans 10^12 m to half a metre:

* **Space (true sizes and distances).** Sun, Earth and Moon on low-precision mean orbital elements; the 364 classes of X3D Ontology 4.1 on a shell of radius 2.4 AU; three domain rings (X3D components, URDF and glTF fault operators), the agent flywheel loop and evidence monoliths (measured first-try vs after-loop validity).
* **The village "Aurelsbrunn" (invented).** 17 buildings, plaza, fountain, stalls, fields, ~120 trees, 12 H-Anim style villagers (16 joints, keyframed gait and gestures, walking closed paths on position interpolators, no scripts).
* **Camera rig.** The village sits at the scene origin (floating origin); `engine.js` places the Sun/Earth/Moon system around it every frame in double precision, a logarithmic depth buffer keeps 1 cm and 1 AU in one frame, and flights follow van Wijk and Nuij's optimal zoom-and-pan path.
* **Layers.** The village lives in its own X3D `Layer` so fog (aerial perspective) never touches the Sun, Moon or constellation.
* **Sky and light.** Time of day drives key/fill lights, sky gradient, fog, lamps and windows; the constellation appears in the night sky; a staged total eclipse (the Moon is nudged by about 9,000 km for five hours around 2 Aug 2027) lights the lamps and shows the corona.
* **Interface.** Tooltips on everything pickable (grade C/L/S/I and a source for each), pinned info panel, village mini-map, scale ladder, time controls, walk mode (G), film (F, about 3 minutes), curator tour (T), synthesised sound (M).

## Run

```bash
cd ontology && python3 -m http.server 8791 --bind 127.0.0.1     # then open http://localhost:8791/v2/index.html
```

Rebuild the scene (needs the x3d_mcp venv; about 30 s plus validation):

```bash
python3 v2/textures.py && python3 v2/town_layout.py
~/Projects/x3d/x3d_mcp/.venv/bin/python v2/make_v2.py          # -> v2/scenes/solar-town.x3d, v2/data/*.json, out/v2_run.json
node v2/test_astro.js                                              # astronomy sanity tests
```

`v2/tex/` and `v2/scenes/` are generated and git-ignored. All textures (planets, Sun, stars, village materials) are procedural: nothing is downloaded.

## Honesty notes

* Orbits are low-precision (Earth: Kepler ellipse, Moon: abridged lunar series, good to about half a degree). The test suite checks perihelion/aphelion, solstice declinations, Moon distance range and that the new moon of 2027-08-02 is found. **Not an ephemeris.**
* The eclipse is staged: the Moon is displaced by 0.13° (9,090 km) with a Gaussian window of five hours so that the village sees totality. The viewer says so.
* The Earth and Moon maps are procedural artworks. The village, its people and the ontology-shell layout are invented or display choices. Grades: C confirmed from repo files, L likely (standard values from memory, models), S suspected, I illustrative.
* Private until 2027-01-01. Nothing here is sent anywhere.
