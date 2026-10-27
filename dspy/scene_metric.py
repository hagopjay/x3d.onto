"""Metric terms for a scene-writing prompt: valid AND placed AND use-type-clean (looks-right is measured in render_eval.py).
Validator pin: hagopjay/x3d_mcp main 2b696f5 (XSD + semantic checker); placement table = X3DUOM via x3d_utils.placement.where_can_place
(6,509 rows, sha256 e749eda517ba...). use-type-mismatch is ported from fork branch claude/ontology-lentz-polys-3j5h8z (semantic.py
_check_use_type_mismatch) as a standalone function so nothing is pushed to the public fork.
Set X3D_MCP_TREE to a checkout of the pinned commit."""
import os, re, sys
TREE = os.environ.get("X3D_MCP_TREE", "/tmp/fork_main")
sys.path[0:0] = [os.path.join(TREE, "src"), TREE]
from lxml import etree                                # noqa: E402
from validation.validate import validate_xml          # noqa: E402
from validation.semantic import validate_semantic     # noqa: E402
from x3d_utils.placement import get_table             # noqa: E402

STRUCT = {"X3D", "head", "Scene", "meta", "component", "unit", "ROUTE", "field", "fieldValue", "IS", "connect", "ProtoDeclare",
          "ProtoInterface", "ProtoBody", "ProtoInstance", "ExternalProtoDeclare", "import", "export", "ProtoInstance", "Metadata"}
_t = None
def _table():
    global _t
    if _t is None: _t = get_table()["rows"]
    return _t

def _tag(el):
    t = el.tag if isinstance(el.tag, str) else ""
    return t.split("}")[-1]

def extract_x3d(text):
    text = text or ""
    m = re.search(r"<X3D[\s>].*?</X3D>", text, re.S)
    return m.group(0) if m else re.sub(r"^```\w*\n|```\s*$", "", text.strip())

def placed_errors(root):
    """Every node element must sit in a parent and field the X3DUOM allows (where_can_place). Root-level scene children and
    nodes under a proto body, Script/field or non-node wrappers are skipped. Returns list of strings."""
    rows, errs = _table(), []
    for el in root.iter():
        t, p = _tag(el), el.getparent()
        if not t or t in STRUCT or p is None: continue
        pt = _tag(p)
        if pt in STRUCT or pt in ("Script", "field") or t not in rows: continue
        if any(_tag(a) in ("ProtoBody", "ProtoDeclare") for a in el.iterancestors()): continue
        want = el.get("containerField")
        ok = [r for r in rows[t] if r["parent"] == pt]
        if not ok:
            errs.append(f"- **[not-placed]** <{t}> cannot be a child of <{pt}> (X3DUOM). Line {el.sourceline}. Allowed parents include: {', '.join(sorted({r['parent'] for r in rows[t]})[:8])}.")
        elif want:
            if not any(r["field"] == want for r in ok):
                errs.append(f"- **[not-placed]** <{t}> in <{pt}> has containerField='{want}', but <{pt}> holds it in: {', '.join(sorted({r['field'] for r in ok}))}. Line {el.sourceline}.")
        elif not any(not r["needsContainerField"] for r in ok):
            errs.append(f"- **[not-placed]** <{t}> in <{pt}> needs containerField='{ok[0]['field']}' (its default field does not hold it under <{pt}>). Line {el.sourceline}.")
    return errs

def use_type_mismatch(root):
    """Ported from fork branch claude/ontology-lentz-polys-3j5h8z: a USE must be the same node type as the DEF it names."""
    def scope_of(el):
        for a in el.iterancestors():
            if _tag(a) == "ProtoBody": return a
        return None
    defs, uses = {}, []
    for pos, el in enumerate(root.iter()):
        tag = _tag(el)
        if not tag: continue
        if el.get("DEF"): defs.setdefault((scope_of(el), el.get("DEF")), []).append((pos, tag, el.sourceline))
        if el.get("USE"): uses.append(((scope_of(el), el.get("USE")), tag, el.get("USE"), pos))
    out, seen = [], set()
    for key, use_tag, name, pos in uses:
        cands = defs.get(key)
        if not cands: continue
        prec = [c for c in cands if c[0] < pos]
        _, def_tag, line = prec[-1] if prec else cands[0]
        if def_tag == use_tag or (use_tag, def_tag, name) in seen: continue
        seen.add((use_tag, def_tag, name))
        out.append(f"- **[use-type-mismatch]** USE='{name}' is a {use_tag} but DEF='{name}' (line {line}) is a {def_tag}. Write <{def_tag} USE='{name}'/> or point this {use_tag} at a DEF that is a {use_tag}.")
    return out

def check(text):
    xml = extract_x3d(text)
    x = validate_xml(xml)
    sem = validate_semantic(xml)
    sec = re.search(r"## Errors\n(.*?)(?=\n## |\Z)", sem, re.S)
    sem_errs = [l for l in (sec.group(1).splitlines() if sec else []) if l.startswith("- **[")][:12]
    valid = bool(x.get("valid")) and not sem_errs
    placed, mism = [], []
    try:
        root = etree.fromstring(xml.encode("utf-8"), etree.XMLParser(recover=False))
        placed, mism = placed_errors(root), use_type_mismatch(root)
    except Exception as e:
        placed = [f"- **[not-parsed]** {str(e)[:120]}"]
    return {"valid": valid, "xsd_valid": bool(x.get("valid")), "xsd_errors": x.get("errors", [])[:12], "sem_errors": sem_errs,
            "placed": not placed, "placed_errors": placed[:12], "mismatch": bool(mism), "mismatch_errors": mism[:6]}

def report(r):
    parts = []
    if not r["valid"]: parts += ["Validator errors:", *(r["xsd_errors"] or ["none from XSD"]), *r["sem_errors"]]
    if not r["placed"]: parts += ["Placement (where_can_place) errors:", *r["placed_errors"]]
    if r["mismatch"]: parts += ["USE/DEF type errors:", *r["mismatch_errors"]]
    return "valid, placed, use types match" if not parts else "\n".join(parts)

def score(r):
    """All three must hold. Partial credit keeps GEPA's Pareto front informative: 1.0 only for valid+placed+clean."""
    return (0.6 * r["valid"]) + (0.25 * r["placed"]) + (0.15 * (not r["mismatch"])) if not (r["valid"] and r["placed"] and not r["mismatch"]) else 1.0
