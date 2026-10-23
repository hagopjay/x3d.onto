#!/usr/bin/env python3
"""Read-only export of X3DUOM facts from an x3d_mcp checkout: concrete node names plus per-node component/level.
usage: export_uom.py <x3d_mcp checkout> <out.json>   (run with that checkout's .venv python)"""
import json, sys
from pathlib import Path
root = Path(sys.argv[1]).expanduser()
sys.path.insert(0, str(root / "src"))
from x3d_utils.x3duom import get_x3duom  # noqa
u = get_x3duom()
nodes = u.get_concrete_nodes()
sample = next(iter(nodes.values()))
out = {"count": len(nodes), "sample_keys": sorted(sample.keys()) if isinstance(sample, dict) else str(type(sample)),
       "nodes": {n: {k: v for k, v in (d.items() if isinstance(d, dict) else []) if k in ("component", "level", "containerField", "parent", "inheritsFrom", "inherits")} for n, d in nodes.items()}}
Path(sys.argv[2]).write_text(json.dumps(out, separators=(",", ":"), sort_keys=True))
print(out["count"], out["sample_keys"])
