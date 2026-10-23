#!/usr/bin/env python3
"""Inline data/explorer.json into harness/explorer.tpl.html -> explorer.html (self-contained)."""
from pathlib import Path
root = Path(__file__).resolve().parent.parent
tpl = (root / "harness" / "explorer.tpl.html").read_text()
data = (root / "data" / "explorer.json").read_text().replace("</", "<\\/")
out = tpl.replace("/*DATA*/null", data)
(root / "explorer.html").write_text(out)
print("explorer.html", len(out), "bytes")
