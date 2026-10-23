#!/bin/sh
# Full run (GO.json: user approved spend as needed; $20 per domain here, $60 total). Pilots already stashed in runs/pilot. LOC and WORKERS can be overridden.
cd "$(dirname "$0")"; PY="$HOME/Projects/x3d/x3d_mcp/.venv/bin/python"; M=gemini-3.8-flash; LOC="${LOC:-us-east4}"; W="${WORKERS:-4}"
full() { d=$1; echo "$(date -u +%H:%M:%S) start full $d loc=$LOC workers=$W"; $PY -I runner.py --domain $d --real --model $M --prompts 20 --samples 3 --arms A0,A1,A2,A3,A4 --cap 20 --location $LOC --workers $W > runs/full-$d.log 2>&1; echo "$(date -u +%H:%M:%S) full $d exit $?"; $PY -I insights.py --domain $d --model $M > runs/insights-$d.log 2>&1; }
for d in x3d urdf gltf; do full $d & sleep 5; done
wait; echo "$(date -u +%H:%M:%S) all done"
