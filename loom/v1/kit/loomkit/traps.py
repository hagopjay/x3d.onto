"""Traps witness: 'has this exact trap already cost us once?'

A portable, standard-library subset of the traps recorded in x3d.onto FACTS P/Q, the kickoff doc's
trap list and the Loomsong spec's five proposed rules. It reads the file only (cheap witness, runs
first). Each rule names the incident that paid for it and is tested on both sides in tests/test_traps.py.

Runtime-specific traps are labelled with the runtime they were observed on: a browser fact must not
become a universal X3D prohibition (Break-the-Loom TECHNICAL.md, Confluence debrief).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

COLOR_FIELDS = {"diffuseColor", "emissiveColor", "specularColor", "baseColor", "color", "skyColor",
                "groundColor", "fogColor", "shadowColor"}
NODES_41_ONLY = {"GaussianSplats", "FontLibrary", "HAnimPose", "InlineGeometry", "RenderedTexture"}


@dataclass
class Hit:
    rule: str
    severity: str
    where: str
    detail: str


@dataclass
class Rule:
    id: str
    severity: str  # "error" stops the build; "warning" is listed
    runtime: str   # "any" or the runtime it was observed on
    origin: str    # the incident that paid for it
    hits: list = field(default_factory=list)


RULES = {
    "shader-raw-source": Rule("shader-raw-source", "error", "X_ITE 16.5.1",
                              "Pocket worlds drew white spheres: raw GLSL in a ShaderPart is read as a URL "
                              "(Lectures 1; FACTS P; gate rule merged 30 Oct)"),
    "route-before-def": Rule("route-before-def", "error", "X_ITE 16.5.1",
                             "A ROUTE written before its node: the fork passed it, X_ITE dropped it "
                             "(definition, Behaviour witness; fork 788041c)"),
    "route-undefined": Rule("route-undefined", "error", "any",
                            "A ROUTE naming a DEF that never exists (x3d.onto loom_gate route-undefined)"),
    "color-range": Rule("color-range", "error", "any",
                        "Colour above 1 fails the XSD with a message that blames a size limit (kickoff traps)"),
    "color-emissive-white": Rule("color-emissive-white", "warning", "X_ITE 16.5.1",
                                 "x3d-ray ring: red and blue faces drew 255 255 255 under white emissive (FACTS Q)"),
    "splat-bbox": Rule("splat-bbox", "error", "X_ITE 16.5.x",
                       "GaussianSplats without bboxSize/bboxCenter never finishes loading when culled "
                       "(definition, Video to world; Loomsong spec)"),
    "movie-not-still": Rule("movie-not-still", "error", "X_ITE 16.5.1",
                            "A still PNG in MovieTexture hangs the world (kickoff traps; Loomsong spec)"),
    "version-fits-nodes": Rule("version-fits-nodes", "error", "any",
                               "A 4.0 file rejects GaussianSplats, FontLibrary, HAnimPose, InlineGeometry, "
                               "RenderedTexture (kickoff traps)"),
    "no-script-under-host": Rule("no-script-under-host", "warning", "strict hosted-page policy",
                                 "The host policy refuses eval; drive the scene from page JS through SAI "
                                 "(kickoff traps; Lectures 3)"),
    "metadata-containerfield": Rule("metadata-containerfield", "warning", "X_ITE 16.5.1",
                                    "Valid metadata left unattached: X_ITE warned until containerField="
                                    "'metadata' was explicit (Gear-Loom TECHNICAL 8.1; Confluence debrief)"),
    "glsl-reserved-active": Rule("glsl-reserved-active", "warning", "X_ITE 16.5.1 GLSL ES 3.00",
                                 "Valid X3D, invalid GLSL: the identifier 'active' broke compilation "
                                 "(Loomsong Study 01, F01). Lexical guard only, not a GLSL validator"),
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _floats(text: str) -> list[float]:
    out = []
    for tok in re.split(r"[\s,]+", text.strip()):
        if tok:
            try:
                out.append(float(tok))
            except ValueError:
                pass
    return out


def check(xml_bytes: bytes, profile: dict | None = None) -> list[Hit]:
    """Return every trap hit. Raises ET.ParseError if the bytes are not XML (that is Grammar's job)."""
    profile = profile or {}
    root = ET.fromstring(xml_bytes)
    hits: list[Hit] = []
    version = root.get("version", "")
    order = list(root.iter())
    first_def: dict[str, int] = {}
    for i, el in enumerate(order):
        d = el.get("DEF")
        if d and d not in first_def:
            first_def[d] = i
    parent = {c: p for p in order for c in p}

    for i, el in enumerate(order):
        tag = _local(el.tag)
        where = f"{tag}#{el.get('DEF') or el.get('USE') or i}"
        if tag == "ShaderPart":
            src = (el.text or "").strip()
            url = el.get("url", "")
            body = src or url
            if body and ("#version" in body or "void main" in body) and not re.match(r"^['\"]?\s*data:", body):
                hits.append(Hit("shader-raw-source", "error", where, "GLSL source without a data: prefix"))
            if re.search(r"\b(?:in|out|uniform|varying|attribute|float|int|bool|vec[234])\s+active\b", body):
                hits.append(Hit("glsl-reserved-active", "warning", where, "identifier 'active' declared"))
        if tag == "ROUTE":
            for end in ("fromNode", "toNode"):
                ref = el.get(end)
                if ref is None:
                    continue
                if ref not in first_def:
                    hits.append(Hit("route-undefined", "error", where, f"{end}={ref} has no DEF"))
                elif first_def[ref] > i:
                    hits.append(Hit("route-before-def", "error", where, f"{end}={ref} defined later"))
        for attr in COLOR_FIELDS & set(el.attrib):
            vals = _floats(el.get(attr, ""))
            if any(v < 0 or v > 1 for v in vals):
                hits.append(Hit("color-range", "error", where, f"{attr} outside [0,1]"))
        if tag == "Material":
            em = _floats(el.get("emissiveColor", "0 0 0"))
            dif = _floats(el.get("diffuseColor", "0.8 0.8 0.8"))
            if len(em) == 3 and min(em) >= 0.999 and len(dif) == 3 and max(dif) - min(dif) > 0.05:
                hits.append(Hit("color-emissive-white", "warning", where, "white emissive washes out a coloured diffuse"))
        if tag == "GaussianSplats" and not (el.get("bboxSize") and el.get("bboxCenter")):
            hits.append(Hit("splat-bbox", "error", where, "missing bboxSize or bboxCenter"))
        if tag == "MovieTexture" and re.search(r"\.(png|jpe?g)\b", el.get("url", ""), re.I):
            hits.append(Hit("movie-not-still", "error", where, "MovieTexture points at a still image"))
        if tag in NODES_41_ONLY and version and version < "4.1":
            hits.append(Hit("version-fits-nodes", "error", where, f"{tag} needs X3D 4.1, file declares {version}"))
        if tag == "Script" and profile.get("host") == "strict":
            hits.append(Hit("no-script-under-host", "warning", where, "Script node under a strict host policy"))
        if tag.startswith("Metadata") and el in parent:
            ptag = _local(parent[el].tag)
            if not ptag.startswith("Metadata") and ptag not in ("head", "X3D") and "containerField" not in el.attrib:
                hits.append(Hit("metadata-containerfield", "warning", where, "Metadata node without explicit containerField"))
    return hits
