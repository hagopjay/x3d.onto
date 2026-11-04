"""Picture review protocol: a model judge locates suspected issues; it never grades (user decision, 3 Nov).

Ported from Loomsong v4 witnesses/picture.py and the IFC studio's release_contract.py. A review is
bound to the candidate and to each frame's sha256; every flag is located (normalised region) and stays
`suspected` (grade S). Numeric scores are allowed only in a labelled experiment record, never here.
"""
from __future__ import annotations

import math
import re

from .core import need

REVIEW_SCHEMA = "loom.picture-review/1"
_NUMERIC_GRADE = re.compile(r"\b(?:score|rating|grade)\s*[:=]\s*\d|\b\d+(?:\.\d+)?\s*/\s*(?:5|10|100)\b", re.I)


def validate(review: dict, subject_sha256: str, frames: dict[str, str]) -> dict:
    """frames maps view name -> sha256 of the captured image. Raises GateError on any violation."""
    need(set(review) == {"schema", "subject_sha256", "reviewer", "state", "images", "flags", "scope"}, "PICTURE_FIELDS")
    need(review["schema"] == REVIEW_SCHEMA, "PICTURE_SCHEMA")
    need(review["subject_sha256"] == subject_sha256, "STALE_PICTURE_REVIEW")
    need(review["state"] == "suspected", "MODEL_TRUTH_PROMOTION", "review state must stay 'suspected'")
    need(isinstance(review["reviewer"], str) and review["reviewer"].strip(), "PICTURE_REVIEWER")
    need(set(review["images"]) == set(frames), "PICTURE_COVERAGE")
    for view, digest in frames.items():
        need(review["images"][view] == digest, "PICTURE_IMAGE_BINDING", view)
    need(isinstance(review["flags"], list), "PICTURE_FLAGS")
    seen = set()
    for f in review["flags"]:
        need(isinstance(f, dict) and set(f) == {"id", "view", "region", "concern", "state"}, "PICTURE_FLAG_FIELDS")
        need(f["id"] not in seen, "PICTURE_DUPLICATE", str(f["id"]))
        seen.add(f["id"])
        need(f["view"] in frames, "PICTURE_FLAG_VIEW", str(f["view"]))
        need(f["state"] == "suspected", "MODEL_TRUTH_PROMOTION", str(f["id"]))
        r = f["region"]
        need(isinstance(r, list) and len(r) == 4
             and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in r)
             and r[0] < r[2] and r[1] < r[3], "PICTURE_REGION", str(f["id"]))
        need(isinstance(f["concern"], str) and len(f["concern"].strip()) > 15, "PICTURE_CONCERN", str(f["id"]))
    need(not _NUMERIC_GRADE.search(str(review)), "PICTURE_GRADING", "a model judge may not score")
    return {"protocol": "valid", "flags": len(review["flags"]), "grade": "S",
            "scope": "Image-bound suspected observations; no approval and no truth verdict."}
