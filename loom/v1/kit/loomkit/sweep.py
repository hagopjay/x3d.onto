"""Leak sweep (law 16: public pages pass a leak sweep first).

Copies a tree to a destination, applies the ordered replacements in a rules file to text files, then
fails if any forbidden pattern survives anywhere in the copy, binary files included. The source tree
is never modified. Rules: kit/profiles/public-sweep.json.

  python -m loomkit sweep SRC DEST --rules RULES.json [--exclude NAME ...]
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .core import need, sha256_file

TEXT_SUFFIXES = {".md", ".txt", ".json", ".py", ".sh", ".yml", ".yaml", ".x3d", ".html", ".cjs", ".js", ""}


def load_rules(path: Path) -> dict:
    rules = json.loads(Path(path).read_text())
    need(rules.get("schema") == "loom.sweep-rules/1", "SWEEP_RULES_SCHEMA")
    for r in rules["replace"]:
        re.compile(r["pattern"])
    return rules


def sweep(src: Path, dest: Path, rules: dict, exclude: set[str]) -> dict:
    src, dest = Path(src).resolve(), Path(dest).resolve()
    need(not str(dest).startswith(str(src) + "/"), "SWEEP_DEST_INSIDE_SRC")
    if dest.exists():
        shutil.rmtree(dest)
    changed: dict[str, int] = {}
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if any(part in exclude for part in rel.parts) or not p.is_file():
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix in TEXT_SUFFIXES:
            text = p.read_text(encoding="utf-8", errors="strict")
            n = 0
            for r in rules["replace"]:
                text, k = re.subn(r["pattern"], r["with"], text)
                n += k
            out.write_text(text, encoding="utf-8")
            if n:
                changed[rel.as_posix()] = n
        else:
            shutil.copy2(p, out)
        out.chmod(p.stat().st_mode)
    residue = []
    forbidden = [re.compile(f) for f in rules["forbid"]]
    for p in sorted(dest.rglob("*")):
        if p.is_file():
            data = p.read_bytes().decode("utf-8", errors="replace")
            for f in forbidden:
                for m in f.finditer(data):
                    residue.append({"file": p.relative_to(dest).as_posix(), "pattern": f.pattern, "match": m.group(0)[:60]})
    report = {"schema": "loom.sweep-report/1", "rules_sha256": sha256_file(rules["_path"]) if "_path" in rules else None,
              "files_changed": changed, "replacements": sum(changed.values()), "residue": residue,
              "status": "pass" if not residue else "fail"}
    return report
