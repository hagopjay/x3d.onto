#!/bin/sh
# Rebuild everything. Needs an x3d_mcp checkout with a .venv (rdflib, mcp). Read-only on that checkout.
# data/X3dOntology4.1.ttl must be present (SHA-1 1b5d645a80917ebfd35d3088bad4affa4c73bea2; test_harness41.py checks it).
set -e
MCP="${1:-$HOME/Projects/x3d/x3d_mcp}"; PY="$MCP/.venv/bin/python"; HERE="$(cd "$(dirname "$0")/.." && pwd)"
cp "$MCP/src/validation/schemas/X3dOntology4.0.ttl" "$HERE/data/"
"$PY" -I "$HERE/harness/export_uom.py" "$MCP" "$HERE/data/uom_concrete.json"
"$PY" -I "$HERE/harness/build.py" "$HERE/data/X3dOntology4.0.ttl" "$HERE/data"
"$PY" -I "$HERE/harness/build.py" "$HERE/data/X3dOntology4.1.ttl" "$HERE/data" ontology41
"$PY" -I "$HERE/harness/xcheck_all.py" "$MCP"
"$PY" -I "$HERE/harness/uom_ranges.py" "$MCP"
"$PY" -I "$HERE/harness/xslt_diagnosis.py"
python3 -I "$HERE/harness/gen_sim.py"
"$PY" -I "$HERE/harness/build_sim.py" "$MCP"
python3 -I "$HERE/harness/merge.py"
"$PY" -I "$HERE/harness/uom_universe.py" "$MCP"
"$PY" -I "$HERE/harness/proposal_numbers.py" "$MCP"
"$PY" -I "$HERE/harness/proposal_sketch.py" "$MCP"
"$PY" -I "$HERE/harness/test_harness.py" "$MCP"
"$PY" -I "$HERE/harness/test_harness41.py" "$MCP"
python3 -I "$HERE/harness/embed.py"
"$PY" "$HERE/harness/make_constellation.py" "$MCP" | grep -v "Processing request"
echo "serve: (cd $HERE && python3 -m http.server 8791) -> /explorer.html and /constellation.html"
