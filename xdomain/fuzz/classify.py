"""Turn the oracle outputs for one scene into findings: (bucket, signature, detail). Signatures are coarse on purpose so that
one cause gives one signature: names of DEFs, numbers and quoted values are stripped from messages.

Buckets
  uom_allows_xsd_rejects   X3DUOM (acceptableNodeTypes, fields, bounds) finds nothing wrong, the XSD rejects
  uom_denies_xsd_accepts   the XSD accepts, X3DUOM read literally says no (containment, choice type, bound, enumeration)
  xsd_valid_xite_drops     XSD-valid, and X_ITE builds fewer nodes or ROUTEs than the file has, or throws
  xsd_valid_xite_warns     XSD-valid, X_ITE warns or errors but builds everything
  semantic_false_alarm     the fork's semantic check reports an error on a scene that XSD, X3DUOM and X_ITE all take cleanly
  semantic_silent_drop     the fork's semantic check reports no error on an XSD-valid scene X_ITE drops part of (the ROUTE gap shape)
  profile_mismatch         the fork's profile check and X_ITE disagree about a profile/component
"""
import re
from collections import Counter
from lxml import etree

BUCKETS = ["uom_allows_xsd_rejects", "uom_denies_xsd_accepts", "xsd_valid_xite_drops", "xsd_valid_xite_warns",
           "semantic_false_alarm", "semantic_silent_drop", "profile_mismatch"]
STATEMENT_TAGS = {"ROUTE", "IS", "connect", "field", "fieldValue", "head", "meta", "component", "unit", "Scene", "X3D", "ProtoDeclare",
                  "ExternProtoDeclare", "ProtoInterface", "ProtoBody", "ProtoInstance", "IMPORT", "EXPORT"}


def is_profile_msg(m):
    return "insufficient component/profile" in m or "does not match component/profile" in m


def template(msg):
    m = re.sub(r"'[^']*'", "'_'", msg); m = re.sub(r'"[^"]*"', '"_"', m)
    m = re.sub(r"\b\d+(\.\d+)?\b", "#", m); m = re.sub(r"\s+", " ", m).strip()
    return m[:160]


def xml_inventory(xml):
    root = etree.fromstring(xml.encode())
    lines = {}
    counts = Counter(); routes = 0
    for el in root.iter():
        if not isinstance(el.tag, str): continue
        lines.setdefault(el.sourceline, el)
        if el.tag == "ROUTE": routes += 1
        elif el.tag not in STATEMENT_TAGS and not el.get("USE"): counts[el.tag] += 1
    return root, lines, counts, routes


def _fam(M, tag):
    n = M.nodes.get(tag)
    return n.bases[0] if n and n.bases else tag


def xsd_pair(err, lines, M):
    """(child, parent, field) of the element an XSD error names, or None."""
    m = re.match(r"Line (\d+): Element '([^']+)'", err)
    if not m: return None
    el = lines.get(int(m.group(1)))
    if el is None or el.tag != m.group(2) or el.getparent() is None: return None
    return (el.tag, el.getparent().tag, el.get("containerField") or (M.nodes[el.tag].cf_default if el.tag in M.nodes else None))


def xsd_signature(err, lines, M):
    """('cf-enum', child cf type, field) | ('not-expected', parent, field, child family) | ('missing-child', parent) | ('attr', tag, attr, facet) | ('other', template)."""
    m = re.match(r"Line (\d+): (.*)", err, re.S); line, msg = (int(m.group(1)), m.group(2)) if m else (None, err)
    el = lines.get(line)
    em = re.match(r"Element '([^']+)'(?:, attribute '([^']+)')?: (.*)", msg, re.S)
    if not em: return ("other", template(msg))
    tag, attr, rest = em.groups()
    if el is not None and el.tag != tag:
        el = next((e for e in lines.values() if e.tag == tag), el)
    par = el.getparent().tag if el is not None and el.getparent() is not None else "?"
    fld = (el.get("containerField") or (M.nodes[tag].cf_default if tag in M.nodes else None)) if el is not None else None
    if attr == "containerField" and "enumeration" in rest:
        return ("cf-enum", M.nodes[tag].cf_type if tag in M.nodes else tag, el.get("containerField") if el is not None else "?")
    if attr: return ("attr", attr, re.sub(r".*\[facet '([^']+)'\].*", r"\1", rest, flags=re.S)[:30] if "facet" in rest else template(rest)[:60])
    if "not expected" in rest: return ("not-expected", par, fld, _fam(M, tag))
    if "Missing child" in rest: return ("missing-child", tag, template(rest)[:80])
    return ("other", tag, template(rest))


def classify(xml, o, M):
    """o: {'xsd','sem','prof','uom', 'xite' (optional)}. Returns list of (bucket, signature tuple, detail dict)."""
    out = []
    try: root, lines, counts, nroutes = xml_inventory(xml)
    except etree.XMLSyntaxError: return out
    xs, uv = o["xsd"], o["uom"].get("violations", [])
    contain_v = [v for v in uv if v["kind"] in ("containment", "no-field", "unknown-node", "cardinality")]
    soft_v = [v for v in uv if v["kind"] in ("cf-choice", "range", "enum", "unknown-attr")]
    sem_err = [d for d in o["sem"]["diags"] if d["level"] == "error"]
    if not xs["valid"] and not uv:
        out.append(("uom_allows_xsd_rejects", ("A",) + xsd_signature(xs["errors"][0], lines, M), {"xsd": xs["errors"][0][:300], "pair": xsd_pair(xs["errors"][0], lines, M)}))
    if not xs["valid"] and not contain_v and soft_v and not o.get("strict_only"):
        # UOM's loose reading (acceptableNodeTypes, the reading behind the 441) allows it; only the strict reading or a bound objects
        sig = xsd_signature(xs["errors"][0], lines, M)
        if sig[0] == "cf-enum" and all(v["kind"] == "cf-choice" for v in soft_v):
            out.append(("uom_allows_xsd_rejects", ("A",) + sig + ("uom-choice-type-agrees",), {"xsd": xs["errors"][0][:300], "pair": xsd_pair(xs["errors"][0], lines, M)}))
    if xs["valid"] and uv:
        v = uv[0]
        sig = (v["kind"], v.get("parent", ""), v.get("field", ""), v.get("child", ""), v.get("attr", ""))
        if v["kind"] in ("containment", "cf-choice", "no-field", "cardinality"): sig = (v["kind"], v["parent"], v["field"], _fam(M, v["child"]))
        out.append(("uom_denies_xsd_accepts", ("B",) + sig, {"violation": v}))
    x = o.get("xite")
    if xs["valid"] and x is not None:
        msgs = [("warn", m) for m in x.get("warn", [])] + [("error", m) for m in x.get("error", [])]
        msgs = [(k, m) for k, m in msgs if "X_ITE" not in m[:6]]
        drops = []
        if x.get("exc"): drops.append(("exception", template(x["exc"])))
        elif x.get("counts") is not None:
            xc = Counter(x["counts"])
            prof_missing = set(o["prof"].get("missing") or [])
            for t, n in sorted(counts.items()):
                if xc.get(t, 0) < n and t not in prof_missing: drops.append(("node", t))   # a node the profile check already flags is agreement, not a drop
            if x.get("routes", 0) < nroutes: drops.append(("route",))
        for pe in x.get("pageerror", []): drops.append(("pageerror", template(pe)))
        if drops:
            d = drops[0]
            if d[0] == "node":
                el = next((e for e in root.iter(d[1]) if not e.get("USE")), None)
                par = el.getparent().tag if el is not None and el.getparent() is not None else "?"
                fld = el.get("containerField") or (M.nodes[d[1]].cf_default if d[1] in M.nodes else "?") if el is not None else "?"
                rel = [m for _, m in msgs if d[1] in m]
                d = ("node", par, fld, d[1])
            elif d[0] == "route": rel = [m for _, m in msgs if re.search(r"ROUTE|[Rr]oute|named|imported|field", m)]
            else: rel = []
            why = template(rel[0]) if rel else "silent"
            # does the fork's semantic check report an error about the same thing? (its profile rule is not counted here)
            sem_rel = [e for e in sem_err if e["check"] != "profile-component" and (e["check"].startswith("route") if d[0] == "route" else True)]
            sem = "sem-flags" if sem_rel else "sem-silent"
            out.append(("xsd_valid_xite_drops", ("C",) + d + (why, sem), {"msgs": [m for _, m in msgs][:4], "drops": drops[:6]}))
            if not sem_rel:
                out.append(("semantic_silent_drop", ("S",) + d[:2] + (why,), {"msgs": [m for _, m in msgs][:3]}))
        else:
            seen = set()
            for k, m in msgs:
                t = template(m)
                if t in seen or is_profile_msg(m): continue
                seen.add(t); out.append(("xsd_valid_xite_warns", ("D", k, t), {"msg": m[:300]}))
        clean_x = not msgs and not drops
        sem_err_np = [d for d in sem_err if d["check"] != "profile-component"]   # the semantic check's profile rule is judged with the profile check
        if sem_err_np and clean_x and not uv and o["prof"].get("ok") is not False:
            for chk in sorted({d["check"] for d in sem_err_np}):
                out.append(("semantic_false_alarm", ("E", chk), {"diag": next(d for d in sem_err_np if d["check"] == chk)}))
        # profile: X_ITE refuses a node for profile/component reasons vs the fork's verdict
        px = [m for k, m in msgs if is_profile_msg(m)] if root.get("profile") != "Full" else []
        pr = o["prof"]
        if pr.get("ok") is False and not px:
            out.append(("profile_mismatch", ("F", "fork-flags_xite-loads", root.get("profile"), (pr.get("missing_components") or ["?"])[0].split(":")[0]),
                        {"missing": pr.get("missing")}))
        if pr.get("ok") and px:
            nm = re.search(r"(?:Unknown node type|Node type) '([^']+)'", px[0]); nm = nm.group(1) if nm else "?"
            comp = M.nodes[nm].component if nm in M.nodes else "?"
            out.append(("profile_mismatch", ("F", "fork-ok_xite-refuses", root.get("profile"), comp), {"msg": px[0][:200]}))
    return out
