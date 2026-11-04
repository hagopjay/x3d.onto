"""Acceptance: a closed set of current-candidate witnesses, decided by a named profile, never by a score.

Algorithm (Loomsong technical debrief section 14, tightened by Cinematic v2-v4 and the IFC studio):
freeze the candidate, resolve the profile's required set, require one well-formed record per required
witness bound to this exact candidate, check its status, grade, coverage and evidence hashes, and only
then let a receipt be written. Missing, stale, failed, errored, development or ungraded records reject.
"""
from __future__ import annotations

import json
from pathlib import Path

from .core import WITNESS_SCHEMA, GateError, candidate, need, sha256_file

PROFILE_SCHEMA = "loom.profile/1"


def load_profile(path: Path | str) -> dict:
    profile = json.loads(Path(path).read_text())
    need(profile.get("schema") == PROFILE_SCHEMA, "PROFILE_SCHEMA", str(path))
    need(isinstance(profile.get("required"), list) and profile["required"], "EMPTY_PROFILE", str(path))
    names = [r.get("witness") for r in profile["required"]]
    need(all(isinstance(n, str) and n for n in names), "PROFILE_WITNESS_NAME")
    need(len(names) == len(set(names)), "PROFILE_DUPLICATE_WITNESS")
    return profile


def status_acceptable(rule: dict, record: dict) -> None:
    """Decide whether a required witness's status lets the release through.

    Policy chosen for v1 (see LOOM-v1.md, "Status and grade"):
    - `pass` is the only status that satisfies a required witness by default;
    - `deferred` and `not_applicable` satisfy it only when the profile names that status in the rule's
      `allow` list AND the record carries a reason, so a scope decision is always written down;
    - `fail`, `error` and `not_run` never satisfy a required witness. An instrument crash is not a pass,
      and it is not a "caught defect" either.
    """
    status = record.get("status")
    if status == "pass":
        return
    allowed = set(rule.get("allow", []))
    need(status in ("deferred", "not_applicable") and status in allowed, "WITNESS_NOT_PASS",
         f"{record.get('witness')}: {status}")
    need(bool(record.get("reason")), "STATUS_NEEDS_REASON", f"{record.get('witness')}: {status}")


def accept(candidate_root: Path | str, evidence_dir: Path | str, profile: dict) -> dict:
    """Return an acceptance summary or raise GateError with a stable code."""
    subject = candidate(candidate_root)
    evidence_dir = Path(evidence_dir)
    rows = []
    for rule in profile["required"]:
        name = rule["witness"]
        path = evidence_dir / f"{name}.json"
        need(path.is_file(), "MISSING_WITNESS", name)
        try:
            record = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise GateError("MALFORMED_WITNESS", f"{name}: {e}") from None
        need(record.get("schema") == WITNESS_SCHEMA, "WITNESS_SCHEMA", name)
        need(record.get("witness") == name, "WRONG_WITNESS_NAME", name)
        need(record.get("subject_sha256") == subject["sha256"], "STALE_WITNESS", name)
        need(record.get("development") is False, "DEVELOPMENT_WITNESS", name)
        status_acceptable(rule, record)
        if record.get("status") == "pass":
            need(record.get("grade") == "C", "UNMEASURED_REQUIRED_WITNESS", f"{name}: grade {record.get('grade')}")
        for key, expected in rule.get("coverage", {}).items():
            need(record.get("coverage", {}).get(key) == expected, "COVERAGE_REQUIRED", f"{name}.{key}")
        for item in record.get("evidence", []):
            p = evidence_dir / item["path"]
            need(p.is_file() and sha256_file(p) == item["sha256"], "EVIDENCE_DRIFT", f"{name}: {item['path']}")
        rows.append({"witness": name, "status": record["status"], "grade": record["grade"],
                     "record_sha256": sha256_file(path)})
    return {"status": "accepted", "profile": profile["name"], "subject_sha256": subject["sha256"],
            "witnesses": rows, "visible_not_run": profile.get("visible_not_run", [])}
