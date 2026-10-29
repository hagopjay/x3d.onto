"""Oracles. Each takes an X3D XML string and returns a plain dict; none of them changes anything.
  xsd(xml)       fork validate_xml (XSD 4.1, lxml/libxml2)
  semantic(xml)  fork semantic_diagnostics (error / warning / info)
  profile(xml)   fork check_profile (profile + component statements)
  uom(xml)       containment, containerField choice and value checks read from X3DUOM 4.1 (model.py), mine
  Xite           X_ITE 16.5.1 in headless Chromium through xite_worker.js, many scenes per page load
The fork is imported from X3D_MCP (default /home/user/x3d_mcp), read-only."""
import json, os, re, subprocess, sys, threading
from pathlib import Path
from lxml import etree
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model  # noqa
sys.path.insert(0, str(model.FORK / "src"))
from validation.validate import validate_xml            # noqa
from validation.semantic import semantic_diagnostics    # noqa
from validation.profile import check_profile            # noqa

STATEMENTS = {"ROUTE", "IS", "connect", "field", "fieldValue", "ProtoDeclare", "ExternProtoDeclare", "ProtoInterface", "ProtoBody",
              "ProtoInstance", "IMPORT", "EXPORT", "head", "meta", "component", "unit", "Scene", "X3D"}
NON_FIELD_ATTRS = {"DEF", "USE", "containerField", "class", "id", "style"}


def xsd(xml):
    try: v = validate_xml(xml)
    except Exception as e: return {"valid": False, "errors": [f"oracle exception: {e}"]}
    return {"valid": bool(v.get("valid")), "errors": [str(e) for e in (v.get("errors") or [])][:8]}


def semantic(xml):
    try: d = semantic_diagnostics(xml)
    except Exception as e: return {"exc": str(e)[:200], "diags": []}
    return {"exc": None, "diags": [{"level": x.level, "check": x.check, "message": str(x.message)[:240]} for x in d]}


def profile(xml):
    try: r = check_profile(etree.fromstring(xml.encode()))
    except Exception as e: return {"ok": None, "exc": str(e)[:200], "missing": [], "unknown": []}
    return {"ok": r.ok, "profile": r.profile, "missing": [m["node"] for m in r.missing], "missing_components": sorted({f"{m['component']}:{m['level']}" for m in r.missing}), "unknown": list(r.unknown)}


def field_of(el, M):
    """The parent field a node element fills: its containerField, else its UOM default."""
    return el.get("containerField") or (M.nodes[el.tag].cf_default if el.tag in M.nodes else None)


def _nums(s):
    out = []
    for t in re.split(r"[\s,]+", s.strip()):
        if not t: continue
        try: out.append(float(t))
        except ValueError: return None
    return out


def uom(xml):
    """Violations of X3DUOM 4.1 read literally. kinds: containment (acceptableNodeTypes says no), cardinality (second node in an SFNode field), cf-choice (the child's containerField
    choice type lacks the field), no-field (parent has no such node field), unknown-attr, range, enum."""
    M = model.load(); out = []
    try: root = etree.fromstring(xml.encode())
    except etree.XMLSyntaxError as e: return {"parse_error": str(e)[:200], "violations": []}
    for el in root.iter():
        if not isinstance(el.tag, str) or el.tag in STATEMENTS: continue
        par = el.getparent()
        if el.tag not in M.nodes: out.append({"kind": "unknown-node", "child": el.tag, "line": el.sourceline}); continue
        if par is not None and par.tag in M.nodes:
            f = field_of(el, M); fl = M.nodes[par.tag].fields.get(f)
            if not fl or fl.type not in ("SFNode", "MFNode"): out.append({"kind": "no-field", "parent": par.tag, "field": f, "child": el.tag, "line": el.sourceline})
            elif not M.uom_allows(el.tag, par.tag, f): out.append({"kind": "containment", "parent": par.tag, "field": f, "child": el.tag, "line": el.sourceline})
            elif not M.uom_allows_strict(el.tag, par.tag, f): out.append({"kind": "cf-choice", "parent": par.tag, "field": f, "child": el.tag, "cf_type": M.nodes[el.tag].cf_type, "line": el.sourceline})
        if not el.get("USE"):
            seen = {}
            for ch in el:
                if isinstance(ch.tag, str) and ch.tag in M.nodes:
                    f = field_of(ch, M); fl = M.nodes[el.tag].fields.get(f)
                    if fl and fl.type == "SFNode":
                        seen[f] = seen.get(f, 0) + 1
                        if seen[f] == 2: out.append({"kind": "cardinality", "parent": el.tag, "field": f, "child": ch.tag, "line": ch.sourceline})
        if el.get("USE"): continue
        fields = M.nodes[el.tag].fields
        for a, v in el.attrib.items():
            if a in NON_FIELD_ATTRS or a.startswith("{"): continue
            fl = fields.get(a)
            if not fl: out.append({"kind": "unknown-attr", "child": el.tag, "attr": a, "line": el.sourceline}); continue
            if fl.enum and not fl.enum_open and fl.type == "SFString" and v not in fl.enum:
                out.append({"kind": "enum", "child": el.tag, "attr": a, "value": v[:40], "line": el.sourceline})
            if (fl.lo is not None or fl.hi is not None) and fl.type not in ("SFString", "MFString", "SFBool", "MFBool"):
                ns = _nums(v)
                if ns and any((fl.lo is not None and (x < fl.lo or (fl.lo_excl and x == fl.lo))) or (fl.hi is not None and (x > fl.hi or (fl.hi_excl and x == fl.hi))) for x in ns):
                    out.append({"kind": "range", "child": el.tag, "attr": a, "value": v[:40], "line": el.sourceline})
    return {"violations": out}


class Xite:
    """X_ITE 16.5.1 oracle. One Chromium, one page; run(list_of_xml) -> list of result dicts in order."""
    def __init__(self, render=False, chunk=25):
        self.render, self.chunk, self.ms = render, chunk, 0
        self.p = subprocess.Popen(["node", str(HERE / "xite_worker.js")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        first = self.p.stdout.readline()
        if not first: raise RuntimeError("xite worker failed: " + self.p.stderr.read()[-800:])
        self.info = json.loads(first)
        self.lock = threading.Lock()

    def run(self, xmls):
        out = []
        with self.lock:
            for i in range(0, len(xmls), self.chunk):
                part = xmls[i:i + self.chunk]
                self.p.stdin.write(json.dumps({"batch": [{"id": str(i + j), "xml": x} for j, x in enumerate(part)], "render": self.render}) + "\n"); self.p.stdin.flush()
                line = self.p.stdout.readline()
                if not line: raise RuntimeError("xite worker died: " + self.p.stderr.read()[-800:])
                r = json.loads(line); self.ms += r["ms"]; out.extend(r["results"])
        return out

    def close(self):
        try: self.p.stdin.close(); self.p.wait(timeout=15)
        except Exception: self.p.kill()


def python_oracles(xml):
    return {"xsd": xsd(xml), "sem": semantic(xml), "prof": profile(xml), "uom": uom(xml)}
