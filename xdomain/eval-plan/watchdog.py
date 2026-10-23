#!/usr/bin/env python3
"""Unattended supervisor: restart stalled or dead runners (they resume from the raw log), then run the judge, insights, demo rebuild, number audit and RESULTS.md.
Stops after 9 hours. Spend stays under GO.json caps (runner caps are cumulative per domain: $20)."""
import json, os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; runs = HERE / "runs"; PY = os.path.expanduser("~/Projects/x3d/x3d_mcp/.venv/bin/python"); M = "gemini-3.8-flash"
LOC = os.environ.get("LOC", "us-east4"); t0 = time.time(); restarts = {d: 0 for d in ("x3d", "urdf", "gltf")}; log = open(runs / "watchdog.log", "a")
def say(m): log.write(time.strftime("%H:%M:%S ", time.gmtime()) + m + "\n"); log.flush()
def alive(d): return subprocess.run(["pgrep", "-f", f"runner.py --domain {d} --real"], capture_output=True).returncode == 0
def launch(d):
    restarts[d] += 1; say(f"launch {d} (restart {restarts[d]})")
    subprocess.Popen([PY, "-I", "runner.py", "--domain", d, "--real", "--model", M, "--prompts", "20", "--samples", "3", "--arms", "A0,A1,A2,A3,A4", "--cap", "25" if d == "gltf" else "20", "--location", LOC, "--workers", "6"] + (["--max-tokens", "32768"] if d == "gltf" else []), cwd=HERE, stdout=open(runs / f"full-{d}.log", "a"), stderr=subprocess.STDOUT)
say("watchdog start")
while time.time() - t0 < 9 * 3600:
    pending = [d for d in restarts if not (runs / f"{d}-{M}.jsonl").exists()]
    if not pending: break
    for d in pending:
        raw = runs / f"raw-{d}-{M}.jsonl"; age = time.time() - raw.stat().st_mtime if raw.exists() else 0
        if not alive(d):
            if restarts[d] < 8:
                time.sleep(8)
                if not alive(d) and not (runs / f"{d}-{M}.jsonl").exists(): launch(d)
        elif age > 25 * 60:
            say(f"{d} stalled {age / 60:.0f} min: kill and resume"); subprocess.run(["pkill", "-f", f"runner.py --domain {d} --real"]); time.sleep(5); launch(d)
    time.sleep(90)
say("runs finished or time out; post-processing")
def sh(args, name):
    r = subprocess.run(args, cwd=HERE, capture_output=True, text=True); say(f"{name}: exit {r.returncode} {r.stdout[-200:].strip()} {r.stderr[-200:].strip()}")
for d in ("x3d", "urdf", "gltf"):
    if (runs / f"{d}-{M}.jsonl").exists(): sh([PY, "-I", "judge.py", "--domain", d, "--model", M, "--judge", M, "--cap", "3.0", "--location", LOC], f"judge {d}"); sh([PY, "-I", "insights.py", "--domain", d, "--model", M], f"insights {d}")
sh([PY, "-I", "final_report.py"], "final_report")
sh([PY, str(HERE.parent.parent / "demo" / "make_demo.py")], "make_demo"); sh([PY, "-I", str(HERE.parent.parent / "demo" / "audit_numbers.py")], "audit_numbers")
(runs / "WATCHDOG-DONE").write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())); say("done")
