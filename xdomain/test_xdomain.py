#!/usr/bin/env python3
"""Checks on the cross-domain prototype results (reads ../out/xdomain_*.json)."""
import json, sys
from pathlib import Path
O = Path(__file__).resolve().parent.parent / "out"
u = json.loads((O / "xdomain_urdf.json").read_text()); g = json.loads((O / "xdomain_gltf.json").read_text()); m = json.loads((O / "xdomain_mcp_run.json").read_text())
fails = []
def check(n, ok, d=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {d}" if d else ""))
    if not ok: fails.append(n)
check("urdf: 0 errors and 0 warnings on every clean robot", not any(u["clean_errors"].values()) and not any(u["clean_warnings"].values()), f"{len(u['corpus'])} robots")
check("urdf: every applicable mutant is flagged by some level", u["totals"]["n"] == sum(u["totals"].get(k, 0) for k in ("L0", "L1", "L2", "warn", "contact")), f"{u['totals']['n']} mutants")
check("urdf: repair is a no-op on clean models", all(u["repair_noop_on_clean"].values()))
check("urdf: every repaired mutant ends clean", u["totals"].get("repair_fixed", 0) > 0 and all(r["repair"] in (None, "fixed") for r in u["rows"]))
check("gltf: Khronos validator reports nothing on clean models", all(not any(v.values()) for v in g["clean"].values()), g["validator"])
check("gltf: repair is a no-op on clean documents and fixes all it attempts", g["repair"]["noop_on_clean"] and g["repair"]["outcome"].get("fixed") == g["repair"]["attempted"], str(g["repair"]["outcome"]))
check("gltf: warnings-only classes recorded (G18, G21, G23)", {k for k, v in g["faults"].items() if v.get("khronos-warning")} == {"G18", "G21", "G23"})
check("mcp: seven tools exposed", len(m["tools"]) == 7)
check("mcp: tether verdicts ok / stale / broken-chain", (m["urdf"]["chain_ok"], m["urdf"]["after_edit"], m["urdf"]["after_forged_step"], m["urdf"]["after_deleted_step"]) == ("ok", "stale", "broken-chain", "broken-chain"))
check("mcp: strict gate policy adds the warning-only extension error", m["gltf"]["strict_policy"]["errors"] > m["gltf"]["upstream_policy"]["errors"])
print("\nALL PASS" if not fails else f"\n{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
