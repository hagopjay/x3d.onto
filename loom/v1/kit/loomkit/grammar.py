"""Grammar and Meaning witnesses through the x3d_mcp fork, run read-only in the fork's own venv.

Every verdict names the fork commit (law 15: name the instrument behind every number). If the fork or
its venv is missing, the result is status `error`, never `pass`.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .core import InstrumentError, portable

DEFAULT_FORK = Path(os.environ.get("LOOM_FORK", str(Path.home() / "Projects/x3d/x3d_mcp")))

_CHILD = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from src.validation.validate import validate_xml
from src.validation.semantic import semantic_diagnostics
out = {}
for path in sys.argv[2:]:
    text = open(path, encoding="utf-8").read()
    g = validate_xml(text)
    try:
        d = semantic_diagnostics(text)
        m = {"errors": [x.__dict__ for x in d if x.level == "error"],
             "warnings": [x.__dict__ for x in d if x.level == "warning"],
             "infos": sum(1 for x in d if x.level not in ("error", "warning"))}
    except Exception as e:  # reported as an instrument error for this file, not a pass
        m = {"error": f"{type(e).__name__}: {e}"}
    out[path] = {"grammar": g, "meaning": m}
print(json.dumps(out, default=str))
"""


def fork_identity(fork: Path = DEFAULT_FORK) -> dict:
    py = fork / ".venv/bin/python"
    if not py.exists():
        raise InstrumentError(f"fork venv not found at {py}")
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(fork), *args], capture_output=True, text=True, check=True).stdout.strip()
    try:
        commit, branch = git("rev-parse", "HEAD"), git("rev-parse", "--abbrev-ref", "HEAD")
        dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    except subprocess.CalledProcessError as e:
        raise InstrumentError(f"cannot read fork git state: {e}") from None
    return {"tool": "x3d_mcp fork (validate_xml + semantic_diagnostics)", "path": portable(fork), "commit": commit,
            "branch": branch, "dirty": dirty, "python": portable(py), "_python_exec": str(py)}


def validate(files: list[Path], fork: Path = DEFAULT_FORK) -> tuple[dict, dict]:
    """Return (instrument, results by file)."""
    ident = fork_identity(fork)
    proc = subprocess.run([ident.pop("_python_exec"), "-I", "-c", _CHILD, str(fork), *map(str, files)],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise InstrumentError(f"fork validator exited {proc.returncode}: {proc.stderr[-800:]}")
    return ident, json.loads(proc.stdout)


def summarise(result: dict) -> dict:
    """Reduce one file's fork output to counts the gate can decide on."""
    g, m = result["grammar"], result["meaning"]
    g_errors = g.get("errors") or []
    m_err = m.get("errors") if isinstance(m, dict) else None
    m_warn = m.get("warnings") if isinstance(m, dict) else None
    return {"xsd_valid": bool(g.get("valid")), "xsd_errors": len(g_errors), "xsd_version": g.get("version") or g.get("schema_version"),
            "semantic_errors": len(m_err or []), "semantic_warnings": len(m_warn or []),
            "semantic_instrument_error": m.get("error") if isinstance(m, dict) else "unexpected output"}
