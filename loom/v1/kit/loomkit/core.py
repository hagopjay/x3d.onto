"""Loom v1 core: fail-closed predicates, candidate identity and witness records.

Every rule here comes from a failure the Loom already paid for (see LEARNINGS-from-patches.md):
- predicates raise; they never use `assert`, so `python -O` cannot turn a red gate green (Loomsong A02);
- a witness record names the exact candidate it checked, test code included (Loomsong A01, v2);
- a candidate that changes while a witness runs is rejected (Loomsong v3, CANDIDATE_CHANGED_DURING_WITNESS);
- status and grade are separate axes (Loomsong technical debrief section 12).
Standard library only, Python 3.10+.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

WITNESS_SCHEMA = "loom.witness/1"
CANDIDATE_SCHEMA = "loom.candidate/1"

# Status says what happened; grade says how far the claim can be leaned on. They are orthogonal.
STATUSES = ("pass", "fail", "error", "not_run", "not_applicable", "deferred")
GRADES = ("C", "L", "S")

# Never part of a candidate: evidence (avoids a self-referential digest), caches, VCS and archives.
DEFAULT_EXCLUDE_DIRS = {"evidence", ".git", "node_modules", ".venv", "__pycache__", "receipts", "runs-local"}
DEFAULT_EXCLUDE_NAMES = {"SHA256SUMS.txt", ".build-in-progress", ".DS_Store"}
DEFAULT_EXCLUDE_SUFFIXES = {".pyc", ".zip"}


class GateError(Exception):
    """A candidate violated a stated contract. `code` is a stable diagnostic."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class InstrumentError(Exception):
    """The instrument itself could not complete. This is status `error`, never `fail` and never `pass`."""


def need(condition: object, code: str, detail: str = "") -> None:
    """Raise GateError(code) unless condition holds. Use this instead of assert everywhere a gate decides."""
    if not condition:
        raise GateError(code, detail)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value: object) -> bytes:
    """Sorted keys, no whitespace, UTF-8: the same bytes on every run."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def portable(path: Path | str) -> str:
    """Record a path without the user's home directory (law 16: no identities in evidence)."""
    s, home = str(path), str(Path.home())
    return "~" + s[len(home):] if s == home or s.startswith(home + "/") else s


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def inventory(root: Path | str, extra_exclude_dirs: set[str] | None = None) -> dict[str, str]:
    """sha256 of every candidate file, keyed by POSIX relative path, sorted."""
    root = Path(root)
    skip_dirs = DEFAULT_EXCLUDE_DIRS | (extra_exclude_dirs or set())
    files: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in skip_dirs for part in rel.parts[:-1]):
            continue
        if p.name in DEFAULT_EXCLUDE_NAMES or p.suffix in DEFAULT_EXCLUDE_SUFFIXES:
            continue
        files[rel.as_posix()] = sha256_file(p)
    return files


def candidate(root: Path | str, extra_exclude_dirs: set[str] | None = None) -> dict:
    files = inventory(root, extra_exclude_dirs)
    need(files, "EMPTY_CANDIDATE", str(root))
    return {"schema": CANDIDATE_SCHEMA, "files": files, "sha256": sha256_bytes(canonical(files))}


def write_witness(
    evidence_dir: Path | str,
    candidate_root: Path | str,
    subject_sha256: str,
    name: str,
    status: str,
    grade: str,
    instrument: dict,
    measurements: dict | None = None,
    coverage: dict | None = None,
    limitations: list[str] | None = None,
    evidence: list[dict] | None = None,
    development: bool = False,
    reason: str = "",
) -> dict:
    """Write one immutable witness record. Refuses if the candidate changed while the witness ran."""
    need(status in STATUSES, "UNKNOWN_STATUS", status)
    need(grade in GRADES, "UNKNOWN_GRADE", grade)
    need(status not in ("deferred", "not_applicable") or reason, "STATUS_NEEDS_REASON", f"{name}: {status}")
    now = candidate(candidate_root)["sha256"]
    need(now == subject_sha256, "CANDIDATE_CHANGED_DURING_WITNESS", name)
    record = {
        "schema": WITNESS_SCHEMA,
        "witness": name,
        "status": status,
        "grade": grade,
        "subject_sha256": subject_sha256,
        "instrument": instrument,
        "measurements": measurements or {},
        "coverage": coverage or {},
        "limitations": limitations or [],
        "evidence": evidence or [],
        "development": development,
        "reason": reason,
        "finished_at": utc_now(),
        "environment": {"python": platform.python_version(), "optimized": bool(sys.flags.optimize)},
    }
    dest = Path(evidence_dir) / f"{name}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record
