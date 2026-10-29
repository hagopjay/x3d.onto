#!/usr/bin/env python3
"""Gemini adjudicates the differential fuzzer's findings (x3d.onto loom/thesis, xdomain/fuzz/findings), with and without the
X3D definitions in the prompt. This is the thesis question asked of a model: do the XML definitions (XSD 4.1, X3DUOM 4.1) make
an AI's judgement about a disagreement between validators better?

Arms, paired per signature:
  bare      bucket, the minimised reproducer, what each oracle said (XSD errors, UOM findings, fork semantic errors, profile, X_ITE)
  grounded  the same, plus excerpts cut from the fork's own x3d-4.1.xsd and X3dUnifiedObjectModel-4.1.xml for every element in
            the reproducer (the xs:element definition and the types and groups it references; the UOM ConcreteNode with the
            fields the reproducer uses and its node-valued fields; containerField choice types)
The model returns JSON: verdict (one of VERDICTS), confidence, evidence (a quote), fix. Calls go through gemini_api.py (shared
ledger, cap, $25 alerts). Grading the verdicts is a separate step (a reviewer with the files open), not done here.
usage: fuzz_adjudicate.py FINDINGS_DIR [--x3d-mcp DIR] [--model M] [--arms bare,grounded] [--limit N] [--out runs/fuzz-adjudicate-<model>.jsonl]"""
import argparse, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from lxml import etree
from gemini_api import call

XS = "{http://www.w3.org/2001/XMLSchema}"
VERDICTS = ["xsd_error", "uom_error", "fork_validator_bug", "xite_bug", "generator_artifact", "spec_ambiguous"]
ap = argparse.ArgumentParser(); ap.add_argument("findings"); ap.add_argument("--x3d-mcp", default="/home/user/x3d_mcp")
ap.add_argument("--model", default="gemini-3.1-pro-preview"); ap.add_argument("--arms", default="bare,grounded"); ap.add_argument("--limit", type=int)
ap.add_argument("--workers", type=int, default=6); ap.add_argument("--out"); a = ap.parse_args()
F = Path(a.findings); S = Path(a.x3d_mcp) / "src/validation/schemas"
rows = json.loads((F / "findings.json").read_text())["rows"][: a.limit]
xsd = etree.parse(str(S / "x3d-4.1.xsd")).getroot(); uom = etree.parse(str(S / "X3dUnifiedObjectModel-4.1.xml")).getroot()
X_EL = {e.get("name"): e for e in xsd.findall(f"{XS}element")}
X_TY = {e.get("name"): e for e in xsd if e.tag in (f"{XS}simpleType", f"{XS}complexType", f"{XS}group", f"{XS}attributeGroup")}
U_NODE = {e.get("name"): e for e in uom.iter("ConcreteNode", "AbstractNodeType", "AbstractObjectType")}
U_CHOICE = {e.get("name"): e for e in uom.iter("ContainerFieldChoices", "SimpleType")}

def _strip_docs(el, keep=240):
    el = etree.fromstring(etree.tostring(el))
    for d in el.iter(f"{XS}documentation"):
        t = (d.text or "").strip(); d.text = t[:keep] + ("..." if len(t) > keep else ""); [d.remove(c) for c in list(d)]
    for ap_ in el.iter(f"{XS}appinfo"): ap_.getparent().remove(ap_)
    return _nons(etree.tostring(el, pretty_print=True).decode())

def _nons(s): return re.sub(r'\s+xmlns(:\w+)?="[^"]*"', "", s)

def xsd_excerpt(name, attrs, cap=5000):
    el = X_EL.get(name)
    if el is None: return f"<!-- no global xs:element named {name} in x3d-4.1.xsd -->"
    out = [_strip_docs(el)]; refs = set()
    for e in el.iter():
        for k in ("type", "base", "ref"):
            v = (e.get(k) or "").split(":")[-1]
            if v in X_TY and (e.tag != f"{XS}attribute" or e.get("name") in attrs or k == "ref"): refs.add(v)
    for r in sorted(refs): out.append(_strip_docs(X_TY[r], 160))
    s = "\n".join(out); return s[:cap] + ("\n<!-- excerpt truncated -->" if len(s) > cap else "")

def uom_excerpt(name, attrs, cap=4000):
    n = U_NODE.get(name)
    if n is None: return f"<!-- no node named {name} in X3DUOM 4.1 -->"
    n = etree.fromstring(etree.tostring(n)); idef = n.find("InterfaceDefinition"); refs = set()
    for f in list(idef.findall("field")) if idef is not None else []:
        keep = f.get("name") in attrs or f.get("type") in ("SFNode", "MFNode")
        if not keep: idef.remove(f); continue
        if (f.get("description") or "") and len(f.get("description")) > 200: f.set("description", f.get("description")[:200] + "...")
        for k in ("baseType", "simpleType"):
            if f.get(k) in U_CHOICE: refs.add(f.get(k))
    cf = n.find("containerField")
    if cf is not None and cf.get("type") in U_CHOICE: refs.add(cf.get("type"))
    out = [_nons(etree.tostring(n, pretty_print=True).decode())] + [_nons(etree.tostring(U_CHOICE[r], pretty_print=True).decode())[:600] for r in sorted(refs)]
    s = "\n".join(out); return s[:cap] + ("\n<!-- excerpt truncated -->" if len(s) > cap else "")

def grounding(doc):
    try: root = etree.fromstring(doc.encode())
    except Exception: return "(the reproducer does not parse, so no excerpts)"
    used = {}
    for e in root.iter():
        if isinstance(e.tag, str) and e.tag not in ("X3D", "Scene", "head", "component", "meta", "unit"): used.setdefault(e.tag, set()).update(e.attrib)
    parts = []
    for name, attrs in used.items():
        parts.append(f"### {name}: x3d-4.1.xsd\n{xsd_excerpt(name, attrs)}\n### {name}: X3dUnifiedObjectModel-4.1.xml\n{uom_excerpt(name, attrs)}")
    return "\n\n".join(parts)

BRIEF = """You are adjudicating a disagreement found by a differential fuzzer of the X3D 4.1 validation stack. The oracles are:
the X3D 4.1 XSD (lxml), X3DUOM 4.1 (a reader of acceptableNodeTypes, containerField choice types, bounds and enumerations),
the x3d_mcp fork's semantic checks and profile check, and the X_ITE 16.5.1 browser (console warnings/errors, nodes dropped).
Bucket "{bucket}": {bucket_doc}
Decide where the defect is:
  xsd_error           the XSD is wrong (it rejects what X3D allows, or accepts what X3D forbids)
  uom_error           X3DUOM is wrong or incomplete (it states a rule the XSD/spec contradicts, or omits one it should carry)
  fork_validator_bug  the fork's semantic/profile check (or the fuzzer's UOM reader) misjudges the scene
  xite_bug            the runtime is wrong (it drops, warns or throws on a scene X3D allows)
  generator_artifact  the scene itself is not a fair test (the fuzzer made something no rule is meant to cover)
  spec_ambiguous      the definitions genuinely leave it open; both sides are defensible
Reply as JSON: {{"verdict": one of the six, "confidence": 0-1, "evidence": "a short quote or precise reference that decides it",
"fix": "which artifact should change, and how, in one sentence"}}"""
BUCKET_DOC = {
    "uom_allows_xsd_rejects": "X3DUOM accepts the scene, the XSD rejects it.",
    "uom_denies_xsd_accepts": "X3DUOM flags the scene, the XSD accepts it.",
    "xsd_valid_xite_drops": "XSD-valid, but X_ITE drops part of the scene or fails the load.",
    "xsd_valid_xite_warns": "XSD-valid, X_ITE builds it but warns.",
    "semantic_false_alarm": "the fork's semantic check reports an error on a scene XSD, UOM and X_ITE take cleanly.",
    "semantic_silent_drop": "X_ITE drops part of an XSD-valid scene and the fork's semantic check says nothing.",
    "profile_mismatch": "the fork's profile check and X_ITE disagree about whether a node is inside the declared profile/components.",
}

def prompt(r, grounded):
    doc = (F / r["file"]).read_text()
    obs = dict(xsd=r.get("xsd"), uom=r.get("uom"), fork_semantic_errors=r.get("sem_errors"), profile_ok=r.get("profile_ok"), xite=r.get("xite"), detail=r.get("detail"))
    p = BRIEF.format(bucket=r["bucket"], bucket_doc=BUCKET_DOC.get(r["bucket"], "")) + f"\n\nMinimised reproducer ({r['scenes']} fuzzed scenes share this signature):\n```xml\n{doc}\n```\nWhat the oracles said:\n```json\n{json.dumps(obs)[:4000]}\n```"
    if grounded: p += "\n\nExcerpts of the definitions (from the validator's own copies):\n" + grounding(doc)
    return p

def one(job):
    r, arm = job; sig = "/".join(r["signature"][1:])
    try: res = call(a.model, [prompt(r, arm == "grounded")], max_tokens=8000, temperature=0.2, json_out=True, purpose=f"fuzz-adjudicate {arm} {r['file'][:60]}")
    except Exception as e: return dict(file=r["file"], arm=arm, error=repr(e)[:200])
    try: j = json.loads(res["text"])
    except Exception: j = {"raw": res["text"][:300]}
    if isinstance(j, list): j = j[0] if j else {}
    return dict(file=r["file"], bucket=r["bucket"], signature=sig, scenes=r["scenes"], arm=arm, model=a.model, **j, est_usd=round(res["est_usd"], 6))

arms = a.arms.split(",")
with ThreadPoolExecutor(a.workers) as ex: out_rows = list(ex.map(one, [(r, arm) for r in rows for arm in arms]))
out = Path(a.out or f"runs/fuzz-adjudicate-{a.model}.jsonl"); out.parent.mkdir(exist_ok=True)
out.write_text("".join(json.dumps(r) + "\n" for r in out_rows))
by = {}
for r in out_rows: by.setdefault(r["file"], {})[r["arm"]] = r.get("verdict")
print(f"{sum(1 for r in out_rows if r.get('verdict') in VERDICTS)}/{len(out_rows)} verdicts, est ${sum(r.get('est_usd', 0) for r in out_rows):.3f} -> {out}")
for arm in arms:
    c = {}
    for r in out_rows:
        if r["arm"] == arm: c[r.get("verdict", "error")] = c.get(r.get("verdict", "error"), 0) + 1
    print(arm, dict(sorted(c.items(), key=lambda kv: -kv[1])))
if len(arms) == 2:
    both = [v for v in by.values() if all(v.get(x) for x in arms)]
    print(f"arms agree on {sum(v[arms[0]] == v[arms[1]] for v in both)} of {len(both)} signatures")
