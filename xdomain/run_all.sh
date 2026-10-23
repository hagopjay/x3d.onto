#!/bin/sh
# Rebuild the cross-domain prototypes. Needs: x3d_mcp checkout with .venv (mcp, lxml), node, and `npm install gltf-validator@2.0.0-dev.3.10 --ignore-scripts` in gltf/.
set -e
H="$(cd "$(dirname "$0")" && pwd)"; PY="${1:-$HOME/Projects/x3d/x3d_mcp}/.venv/bin/python"
"$PY" -I "$H/urdf/eval_urdf.py" | tail -2
python3 -I "$H/gltf/eval_gltf.py" | tail -2
"$PY" -I "$H/run_loop.py" 2>&1 | grep -v "Processing request" | tail -3
"$PY" -I "$H/test_xdomain.py"
