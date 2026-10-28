# x3d.onto: one-command helpers. Needs python3 with numpy + pillow; node only for test-astro.
PORT ?= 8791

assets:           ## unpack the shipped v2 scene and extra textures (no network)
	python3 v2/textures.py
	mkdir -p v2/tex v2/scenes
	tar xzf assets/v2-textures-extra.tar.gz -C v2/tex
	gunzip -c assets/solar-town.x3d.gz > v2/scenes/solar-town.x3d
	@echo "scene sha256 (expect 33856d7c1eb330c3163571cfc28d42408d0b390356b9a3cec4a2785be1f2f982):"
	@sha256sum v2/scenes/solar-town.x3d

demo: assets      ## serve and print the URLs
	@echo "v2: http://127.0.0.1:$(PORT)/v2/index.html   v1: /explorer.html /constellation.html /demo/demo.html"
	python3 -m http.server $(PORT) --bind 127.0.0.1

test-astro:
	node v2/test_astro.js

# Rebuilding the scene from code takes ~17 min (12,557 MCP calls) and needs an x3d_mcp checkout:
#   <x3d_mcp venv>/bin/python v2/make_v2.py
.PHONY: assets demo test-astro

# Gobbler v4, step 1: live hover on the Gobbler 3 Deep scene (gobbler-v4/README.md). Needs node for the tests, python3 + curl + npm for v4-data.
v4-data:          ## fetch the Gobbler 3 Deep build and X_ITE 16.5.1 (hash-checked), patch the engine, trim the ontology block
	sh gobbler-v4/tools/fetch_deep.sh
	python3 -I gobbler-v4/tools/build_onto_hover.py --graph gobbler-v4/data/deep/graph-v3.json

test-v4:          ## unit tests: placement (+ fuzz), picking, cards, density; the Deep graph tests run once v4-data has been done
	node gobbler-v4/test/test_placement.js
	node gobbler-v4/test/test_pick.js
	node gobbler-v4/test/test_cards.js
	node gobbler-v4/test/test_density.js

v4:               ## serve the live viewer: http://127.0.0.1:$(PORT)/index.html (?ui=none, ?view=Inside, ?hover=2338)
	@echo "http://127.0.0.1:$(PORT)/index.html"
	cd gobbler-v4 && python3 -m http.server $(PORT) --bind 127.0.0.1

e2e-v4:           ## live-scene tests in Chromium (Playwright); serve with `make v4` first (same PORT), see gobbler-v4/README.md
	cd gobbler-v4/e2e && GV4_BASE=http://127.0.0.1:$(PORT)/ node e2e.js
.PHONY: v4-data test-v4 v4 e2e-v4 demiurge-data feathers test-demiurge demiurge e2e-demiurge frames-demiurge artifact-demiurge

# Gobbler demiurge, step 2: the bird-first page (gobbler-demiurge/README.md). Needs make v4-data first (Deep build and X_ITE are fetched there, not committed).
demiurge-data:    ## compose the bird scene (Deep scene + layers), gzip it and the graph, validate with the fork (X3D_MCP=/path/to/x3d_mcp, default /home/user/x3d_mcp)
	python3 -I gobbler-demiurge/tools/build_bird.py --validate

feathers:         ## (needs a Python with bpy) model the feathers in Blender, bake golden-hour light, export through x3d-blender-io -> gobbler-demiurge/assets/feathers (committed)
	python3 gobbler-demiurge/tools/blender_feather.py --blenderio $${BLENDERIO:-../x3d-blender-io/source}

test-demiurge:    ## unit tests for the layers (node-free)
	python3 -I gobbler-demiurge/test/test_layers.py

demiurge:         ## serve the repo root: http://127.0.0.1:$(PORT)/gobbler-demiurge/index.html (?ui=none, ?view=establishing)
	@echo "http://127.0.0.1:$(PORT)/gobbler-demiurge/index.html"
	python3 -m http.server $(PORT) --bind 127.0.0.1

e2e-demiurge:     ## the live page in Chromium (serve with `make demiurge` first, same PORT)
	cd gobbler-demiurge && GD_BASE=http://127.0.0.1:$(PORT)/gobbler-demiurge/index.html node test/e2e.js

frames-demiurge:  ## the documentation frames in gobbler-demiurge/docs/frames
	cd gobbler-demiurge && GD_BASE=http://127.0.0.1:$(PORT)/gobbler-demiurge/index.html node test/frames.js

artifact-demiurge: ## a flat copy for a private host: make artifact-demiurge OUT=/some/dir (needs test/requests.js output in gobbler-demiurge/out/runtime-files.json)
	python3 -I gobbler-demiurge/tools/make_artifact.py $(OUT) gobbler-demiurge/out/runtime-files.json
