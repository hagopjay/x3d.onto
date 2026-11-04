"""Run the fold-back witness over every PR patch found in the unpacked Loom zips.

  python3 -I kit/examples/check_all_foldbacks.py [INCOMING_UNPACKED] [OUT_DIR] [--python SUBSTRING=INTERPRETER ...]

--python picks the interpreter for patches whose path contains SUBSTRING (a project's own venv that
already has its dependencies), so nothing has to be installed for the check.

Read-only against incoming/: each patch is applied in its own empty temporary git repository. Copies of
the same patch (a project zip and its Gate-/Foldback-Kit) are grouped by sha256 and checked once.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from loomkit import foldback  # noqa: E402
from loomkit.core import portable, sha256_file, utc_now  # noqa: E402

V1 = KIT.parent
args, pythons = [], {}
it = iter(sys.argv[1:])
for a in it:
    if a == "--python":
        k, v = next(it).split("=", 1); pythons[k] = v
    else:
        args.append(a)
src = Path(args[0]) if args else V1.parent / "incoming/unpacked"
out = Path(args[1]) if len(args) > 1 else V1 / "runs/foldbacks-20261104"

groups: dict[str, list[str]] = {}
for p in sorted(src.rglob("*.patch")):
    groups.setdefault(sha256_file(p), []).append(p.relative_to(src).as_posix())

rows = []
for digest, paths in groups.items():
    py = next((v for k, v in pythons.items() if k in paths[0]), sys.executable)
    res = foldback.check(src / paths[0], python=py)
    res["interpreter"] = portable(py)
    res["patch"] = paths[0]
    rows.append({"sha256": digest, "copies": paths, **{k: v for k, v in res.items() if k != "patch_sha256"}})
    print(f"{res['status']:6} additions_only={res['additions_only']!s:5} files={res['files']:3} {paths[0]}"
          + (f"  [{res['reason']}]" if res["reason"] else ""))

out.mkdir(parents=True, exist_ok=True)
report = {"schema": "loomkit.foldback-survey/1", "ran_at": utc_now(), "python": sys.version.split()[0], "interpreters": {k: portable(v) for k, v in pythons.items()},
          "scope": "Each patch applied to an empty repo; its smoke.py run normally and with -O. Compatibility with the "
                   "target repositories (x3d.onto, the fork, x3d.ML) is not tested: none is checked out here.",
          "patches": rows}
(out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print("wrote", out / "report.json")
