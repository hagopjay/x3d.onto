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
