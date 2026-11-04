# Proposed global Loom additions: IFC bridge profile

The additions-only patch installs `tools/loom_ifc_bridge_v1/`. It contains the actual bridge contracts, the edge-connected normal routine, the client revision reducer, the independent world-triangle witness, an IFC/X3D fixture pair and the X3D 4.0 schemas.

```sh
git apply --check loom-ifc-bridge.patch
git apply loom-ifc-bridge.patch
python3 -m pip install -r tools/loom_ifc_bridge_v1/requirements.txt
python3 tools/loom_ifc_bridge_v1/smoke.py
python3 -O tools/loom_ifc_bridge_v1/smoke.py
node tools/loom_ifc_bridge_v1/protocol.cjs
```

The smoke test has a positive IFC/X3D correspondence and deliberately wrong yet valid mutations. The client reducer includes valid, duplicate, gap and rollback cases. The kit does not substitute for the full demo's real WebSocket, two-browser, watched-file, GPU sampler or device-timing tests. No CI workflow is enabled automatically.

Before promotion, choose the profile trigger, units, tolerances, severity and budget. Keep world-triangle matching separate from byte hashing, and metadata ownership separate from DEF existence. Keep revision acceptance separate from rendering completion. Do not promote visual concerns into measured truth or infer general IFC compatibility from one authored building.

The complete diagnosis and catch matrix are in `docs/TECHNICAL-DEBRIEF.md` in the full release. This patch has been tested in a clean local Git repository; compatibility with an unseen upstream tree is not claimed.
