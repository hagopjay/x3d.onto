"""Fold-back witness: does a PR-style fold-back patch apply cleanly and do its own controls hold?

Every project PR patch in the Loom folder has the same shape (LEARNINGS-from-patches.md, "The PR shape"):
an additions-only directory under tools/<name>/, a README, and a smoke.py that must pass under normal
Python and `python -O`. This witness re-checks exactly that claim in an empty temporary git repo.

The patch's smoke test is the patch author's code: it runs in a throwaway directory with `python -E -s`
(no environment variables, no user site), exactly as the PR README says: `python3 tools/<name>/smoke.py`.
Not `-I`: since Python 3.11 that also drops the script's own directory from sys.path, so a smoke test
cannot import its sibling package. That mistake was made once here and showed up, correctly, as status
`error` rather than a false `fail` (LEARNINGS-from-patches.md, "the instrument is tested too").
A missing dependency is status `error` (the instrument could not complete), not `fail`.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .core import portable, sha256_file


def patch_files(patch: Path) -> list[dict]:
    """List target files and whether each is an addition (old side /dev/null)."""
    text = patch.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^diff --git ", text, re.M):  # git patches: one header per file, binary entries included
        out = []
        for block in re.split(r"^(?=diff --git )", text, flags=re.M)[1:]:
            head = block.split("\n@@", 1)[0].split("GIT binary patch", 1)[0]
            name = re.match(r"diff --git a/\S+ b/(\S+)", block).group(1)
            out.append({"path": name, "added": "new file mode" in head})
        return out
    out = []
    old = None
    for line in text.splitlines():
        if line.startswith("--- "):
            old = line[4:].strip()
        elif line.startswith("+++ ") and old is not None:
            new = re.sub(r"^b/", "", line[4:].strip())
            out.append({"path": new, "added": old == "/dev/null"})
            old = None
    if not out:  # binary-only git patches carry no ---/+++ pairs
        for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)\n(new file mode)?", text, re.M):
            out.append({"path": m.group(2), "added": bool(m.group(3))})
    return out


def check(patch: Path, python: str = sys.executable, timeout: int = 900) -> dict:
    patch = Path(patch).resolve()
    files = patch_files(patch)
    result = {"patch": portable(patch), "patch_sha256": sha256_file(patch), "files": len(files),
              "additions_only": bool(files) and all(f["added"] for f in files),
              "tool_dirs": sorted({"/".join(f["path"].split("/")[:2]) for f in files}),
              "apply_check": None, "smoke": [], "status": None, "reason": ""}
    with tempfile.TemporaryDirectory(prefix="loom-foldback-") as td:
        repo = Path(td)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        chk = subprocess.run(["git", "-C", str(repo), "apply", "--check", str(patch)], capture_output=True, text=True)
        result["apply_check"] = chk.returncode == 0
        if chk.returncode != 0:
            result.update(status="fail", reason="git apply --check failed: " + chk.stderr.strip()[-400:])
            return result
        subprocess.run(["git", "-C", str(repo), "apply", str(patch)], check=True)
        smokes = sorted(repo.glob("tools/*/smoke.py"))
        if not smokes:
            result.update(status="fail", reason="no tools/<name>/smoke.py: the fold-back carries no executable control")
            return result
        for smoke in smokes:
            for flags in ([], ["-O"]):
                p = subprocess.run([python, "-E", "-s", *flags, str(smoke)], cwd=smoke.parent,
                                   capture_output=True, text=True, timeout=timeout)
                tail = (p.stdout.strip().splitlines() or [""])[-1][:300]
                err = p.stderr.strip().splitlines()[-1][:300] if p.stderr.strip() else ""
                result["smoke"].append({"smoke": str(smoke.relative_to(repo)), "optimized": bool(flags),
                                        "exit_code": p.returncode, "stdout_tail": tail, "stderr_tail": err})
    codes = [s["exit_code"] for s in result["smoke"]]
    missing = [s for s in result["smoke"] if "ModuleNotFoundError" in s["stderr_tail"]]
    if all(c == 0 for c in codes) and result["additions_only"]:
        result["status"] = "pass"
    elif missing:
        result.update(status="error", reason="smoke needs an uninstalled dependency: " + missing[0]["stderr_tail"])
    elif not result["additions_only"]:
        result.update(status="fail", reason="patch modifies existing files; a fold-back must be additions-only")
    else:
        result.update(status="fail", reason="smoke failed in at least one mode")
    return result
