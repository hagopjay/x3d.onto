#!/usr/bin/env python3
"""Adjudicate the residue (DIRECTIONS A3): the 441 containment pairs X3DUOM's acceptableNodeTypes allows and the XSD rejects (FACTS N).
For each pair: (1) recompute it from data/ (must give 441); (2) rebuild it in a context the XSD has verified, not the harness wrapper
(the parent is reached from <Scene> by the shortest chain of verified placements); (3) ask three X3DUOM structures (acceptableNodeTypes,
the child's containerField choice type, the parent's ContentModel with its group names resolved in the XSD) and the XSD; (4) ask X_ITE.
  python3 -I xdomain/fuzz/residue.py [--no-xite] [--out xdomain/fuzz/findings/residue.json]"""
import argparse, json, sys, time
from collections import Counter, deque
from pathlib import Path
from lxml import etree
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model, gen, oracles  # noqa

XS = "{http://www.w3.org/2001/XMLSchema}"


def xsd_groups():
    """{group name: set of element names} from the fork's bundled x3d-4.1.xsd, nested group refs resolved."""
    t = etree.parse(str(model.FORK / "src" / "validation" / "schemas" / "x3d-4.1.xsd"))
    raw = {}
    for g in t.getroot().iter(XS + "group"):
        if g.get("name"):
            raw[g.get("name")] = ([e.get("ref") for e in g.iter(XS + "element") if e.get("ref")],
                                  [x.get("ref") for x in g.iter(XS + "group") if x.get("ref")])
    out = {}
    def res(n, stack=()):
        if n in out: return out[n]
        if n not in raw or n in stack: return set()
        els, refs = raw[n]; s = set(els)
        for r in refs: s |= res(r, stack + (n,))
        out[n] = s; return s
    for n in raw: res(n)
    return out


def content_model_admits(M, G, parent, child):
    names = M.nodes[parent].content_model
    if not names: return None
    s = set()
    for n in names: s |= G.get(n, {n})
    return child in s


def paths_to(M):
    """Shortest chain of verified placements from <Scene> to every node: {node: [(tag, field_it_fills)]}."""
    V = M.edges("verified"); roots = gen.scene_roots(M)
    best = {r: [(r, None)] for r in roots}; q = deque(roots)
    adj = {}
    for (p, f), kids in V.items():
        for c in kids: adj.setdefault(p, []).append((f, c))
    while q:
        p = q.popleft()
        for f, c in sorted(adj.get(p, [])):
            if c not in best: best[c] = best[p] + [(c, f)]; q.append(c)
    return best


def build(M, chain, child, field):
    """XML: the chain, then the child in the parent's field."""
    def open_tag(tag, f):
        cf = f" containerField='{f}'" if f and f != M.nodes[tag].cf_default else ""
        return f"<{tag}{cf}>"
    body = "".join(open_tag(t, f) for t, f in chain)
    cf = f" containerField='{field}'" if field != M.nodes[child].cf_default else ""
    if child == "ProtoInstance":   # a ProtoInstance needs a name and a declaration; the harness wrapper gave neither
        body += f"<ProtoInstance name='P'{cf}/>" + "".join(f"</{t}>" for t, _ in reversed(chain))
        return gen.wrap("<ProtoDeclare name='P'><ProtoBody><Group/></ProtoBody></ProtoDeclare>" + body)
    body += f"<{child}{cf}/>" + "".join(f"</{t}>" for t, _ in reversed(chain))
    return gen.wrap(body)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--no-xite", action="store_true"); ap.add_argument("--out", default=str(HERE / "findings" / "residue.json"))
    a = ap.parse_args(); t0 = time.time()
    M = model.load(); G = xsd_groups(); R = model.residue_pairs(M); P = paths_to(M)
    rows = []
    for c, p, f, err in R:
        chain = P.get(p)
        xml = build(M, chain, c, f) if chain else None
        strict = M.uom_allows_strict(c, p, f); cm = content_model_admits(M, G, p, c)
        v = oracles.xsd(xml) if xml else {"valid": None, "errors": []}
        kind = "cf-enum" if "enumeration" in err else ("not-expected" if "not expected" in err else "other")
        rows.append(dict(child=c, parent=p, field=f, harness_error_kind=kind, cf_choice_admits=strict, content_model_admits=cm,
                         context=len(chain) if chain else None, xsd_in_context=v["valid"], xsd_error=(v["errors"] or [""])[0][:200], xml=xml))
    if not a.no_xite:
        X = oracles.Xite(); todo = [r for r in rows if r["xml"]]
        for r, xr in zip(todo, X.run([r["xml"] for r in todo])):
            built = (xr.get("counts") or {}).get("P" if r["child"] == "ProtoInstance" else r["child"], 0) > 0 and not xr.get("exc")
            warned = [m for m in xr.get("warn", []) + xr.get("error", []) if r["child"] in m or "ontainer field" in m]
            r["xite_builds"] = bool(built and not warned); r["xite_msg"] = (warned or [""])[0][:200]
        X.close(); xinfo = X.info
    else: xinfo = None
    def cause(r):
        if r["xsd_in_context"] and r["child"] == "ProtoInstance": return "harness: ProtoInstance without name/ProtoDeclare (XSD accepts once declared)"
        if r["xsd_in_context"]: return "harness-context (XSD accepts once the parent is placed by a verified chain)"
        if r["cf_choice_admits"] is False: return "UOM containerField choice type excludes the field"
        if r["content_model_admits"] is False: return "UOM ContentModel (XSD groups) excludes the child"
        if r["context"] is None: return "parent unreachable through verified placements"
        return "every UOM structure admits it; XSD rejects"
    for r in rows: r["cause"] = cause(r)
    summ = dict(pairs=len(rows), reproduces_441=len(rows) == 441, by_cause=dict(Counter(r["cause"] for r in rows)),
                by_parent=dict(Counter(r["parent"] for r in rows).most_common(12)), by_harness_error=dict(Counter(r["harness_error_kind"] for r in rows)),
                xsd_still_rejects_in_verified_context=sum(1 for r in rows if r["xsd_in_context"] is False),
                xite=xinfo, xite_builds=None if a.no_xite else sum(1 for r in rows if r.get("xite_builds")),
                xite_builds_by_cause=None if a.no_xite else dict(Counter(r["cause"] for r in rows if r.get("xite_builds"))),
                seconds=round(time.time() - t0, 1))
    # one reproducer per (cause, key): the verified-context document itself, already one child in one chain
    rd = Path(a.out).parent / "residue"; rd.mkdir(parents=True, exist_ok=True)
    for old in rd.glob("*.x3d"): old.unlink()
    files = {}
    for r in rows:
        if not r["xml"]: continue
        short = {"UOM containerField": "cfchoice", "UOM ContentModel": "contentmodel", "harness-context": "context", "harness: ProtoInstance": "proto", "every UOM": "xsdonly"}
        tag = next((v for k, v in short.items() if r["cause"].startswith(k)), "other")
        key = (tag, M.nodes[r["child"]].cf_type or r["child"], r["field"]) if tag == "cfchoice" else (tag, r["parent"], r["field"]) if tag in ("contentmodel", "proto") else (tag, r["parent"], r["field"], r["child"])
        if key in files: files[key]["pairs"] += 1; continue
        name = "-".join(str(k) for k in key) + ".x3d"; (rd / name).write_text(r["xml"]); files[key] = dict(file="residue/" + name, pairs=1, cause=r["cause"], example=[r["child"], r["parent"], r["field"]], xite_builds=r.get("xite_builds"))
    summ["reproducers"] = len(files)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(summary=summ, reproducers=sorted(files.values(), key=lambda x: x["file"]), rows=[{k: v for k, v in r.items() if k != "xml"} for r in rows]), indent=0))
    print(json.dumps(summ, indent=1))
    return rows


if __name__ == "__main__":
    main()
