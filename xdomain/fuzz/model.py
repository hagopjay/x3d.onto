"""The X3D object model the fuzzer samples from: X3DUOM 4.1 (the copy bundled in the x3d_mcp fork) plus the verified matrix in data/.
Read-only. Parses the UOM XML directly so that it also sees what the fork's parser drops: enumerations, containerField choice types
and ContentModel references.

  M = load()                      # cached singleton
  M.nodes['Transform'].fields     # {name: Field}
  M.uom_allows(child, parent, field)          # acceptableNodeTypes only (the reading behind the 441 residue)
  M.uom_allows_strict(child, parent, field)   # and the child's own containerField choice type admits the field
  M.edges(mode)                   # {(parent, field): [child, ...]}  mode 'uom' or 'verified'
"""
import json, os
from dataclasses import dataclass, field as dfield
from pathlib import Path
from lxml import etree

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FORK = Path(os.environ.get("X3D_MCP", "/home/user/x3d_mcp"))
UOM_PATH = FORK / "src" / "validation" / "schemas" / "X3dUnifiedObjectModel-4.1.xml"
CONTAIN = ("initializeOnly", "inputOutput")      # containment fields; inputOnly/outputOnly node fields are event ports
UNIVERSAL = ("metadata", "IS")
NOT_FIELDS = {"DEF", "USE", "class", "id", "style", "containerField"}   # XML attributes X3DUOM lists as SFString fields


@dataclass
class Field:
    name: str
    type: str
    access: str
    default: str | None = None
    acceptable: tuple = ()
    lo: float | None = None
    hi: float | None = None
    lo_excl: bool = False
    hi_excl: bool = False
    enum: tuple = ()
    enum_open: bool = True


@dataclass
class Node:
    name: str
    component: str
    level: int
    bases: tuple
    cf_default: str | None
    cf_type: str | None
    fields: dict = dfield(default_factory=dict)
    content_model: tuple = ()


class Model:
    def __init__(self, path=UOM_PATH):
        t = etree.parse(str(path))
        self.uom_sha1 = __import__("hashlib").sha1(Path(path).read_bytes()).hexdigest()
        self.enums = {s.get("name"): tuple(e.get("value") for e in s.iter("enumeration")) for s in t.iter("SimpleType")}
        self.abstract_bases = {}
        for a in t.iter("AbstractNodeType", "AbstractObjectType"):
            idef = a.find("InterfaceDefinition")
            self.abstract_bases[a.get("name")] = self._bases(idef)
        self.nodes = {}
        for c in t.iter("ConcreteNode"):
            idef = c.find("InterfaceDefinition"); ci = idef.find("componentInfo"); cf = idef.find("containerField")
            n = Node(c.get("name"), ci.get("name") if ci is not None else "", int(ci.get("level", 1)) if ci is not None else 1,
                     self._bases(idef), cf.get("default") if cf is not None else None, cf.get("type") if cf is not None else None)
            for f in idef.iterchildren("field"):
                g = lambda k: f.get(k)
                if g("name") in NOT_FIELDS: continue
                lo = g("minInclusive") or g("minExclusive"); hi = g("maxInclusive") or g("maxExclusive")
                n.fields[g("name")] = Field(g("name"), g("type"), g("accessType"), g("default"),
                                            tuple(g("acceptableNodeTypes").split("|")) if g("acceptableNodeTypes") else (),
                                            _num(lo), _num(hi), bool(g("minExclusive")), bool(g("maxExclusive")),
                                            tuple(e.get("value") for e in f.iter("enumeration")), g("additionalEnumerationValuesAllowed") != "false")
            cm = idef.find("ContentModel")
            if cm is not None: n.content_model = tuple(x.get("name") for x in cm)
            self.nodes[n.name] = n
        self._anc = {}

    @staticmethod
    def _bases(idef):
        if idef is None: return ()
        return tuple(x.get("baseType") for x in idef if x.tag in ("Inheritance", "AdditionalInheritance") and x.get("baseType"))

    def ancestors(self, name):
        """name plus every abstract type it inherits from (UOM Inheritance + AdditionalInheritance, transitively)."""
        if name in self._anc: return self._anc[name]
        seen, todo = {name}, list(self.nodes[name].bases if name in self.nodes else self.abstract_bases.get(name, ()))
        while todo:
            b = todo.pop()
            if b in seen: continue
            seen.add(b); todo.extend(self.abstract_bases.get(b, ()))
        self._anc[name] = frozenset(seen); return self._anc[name]

    def node_fields(self, parent):
        """Containment fields of a concrete parent: node-typed, initializeOnly/inputOutput, not metadata/IS."""
        return [f for f in self.nodes[parent].fields.values()
                if f.type in ("SFNode", "MFNode") and f.access in CONTAIN and f.name not in UNIVERSAL and f.acceptable]

    def uom_allows(self, child, parent, field):
        f = self.nodes.get(parent) and self.nodes[parent].fields.get(field)
        if not f or child not in self.nodes: return False
        return bool(self.ancestors(child) & set(f.acceptable))

    def cf_choices(self, child):
        """containerField values the child's own UOM containerField type allows, or None when the type is xs:NMTOKEN (open)."""
        t = self.nodes[child].cf_type
        return None if not t or t not in self.enums else set(self.enums[t])

    def uom_allows_strict(self, child, parent, field):
        if not self.uom_allows(child, parent, field): return False
        ch = self.cf_choices(child)
        return ch is None or field in ch

    def edges(self, mode="uom"):
        """{(parent, field): [children]}. 'uom': acceptableNodeTypes; 'verified': only pairs the fork's XSD accepted in data/ (xcheck_all + uom_universe)."""
        key = "_edges_" + mode
        if hasattr(self, key): return getattr(self, key)
        E = {}
        if mode == "uom":
            for p in sorted(self.nodes):
                for f in self.node_fields(p):
                    kids = [c for c in sorted(self.nodes) if self.uom_allows(c, p, f.name)]
                    if kids: E[(p, f.name)] = kids
        else:
            for c, p, f in verified_pairs():
                if p in self.nodes and c in self.nodes and f in self.nodes[p].fields and self.nodes[p].fields[f].access in CONTAIN:
                    E.setdefault((p, f), []).append(c)
            for k in E: E[k] = sorted(set(E[k]))
        setattr(self, key, E); return E


def _num(s):
    try: return float(s) if s not in (None, "") else None
    except ValueError: return None


def cf_name(f):
    return f[3:4].lower() + f[4:] if f.startswith("has") else f


def verified_pairs():
    """(child, parent, containerField) the fork's XSD accepted in the matrix runs (harness/xcheck_all.py, harness/uom_universe.py)."""
    D = REPO / "data"; out = set()
    for c, p, f, v, e in json.loads((D / "xcheck_all.json").read_text())["rows"]:
        if v == "A" and cf_name(f) not in UNIVERSAL: out.add((c, p, cf_name(f)))
    for c, p, f, v in json.loads((D / "uom_universe.json").read_text())["rows"]:
        if v == "A": out.add((c, p, f))
    return sorted(out)


def residue_pairs(M=None):
    """The 441 UOM-allows / XSD-rejects containment pairs of FACTS N, recomputed from data/ exactly as harness/proposal_numbers.py does."""
    M = M or load(); D = REPO / "data"
    X = json.loads((D / "xcheck_all.json").read_text())["rows"]
    UR = {tuple(r[:3]): r[4] for r in json.loads((D / "uom_ranges.json").read_text())["rows"]}
    out = []
    for c, p, f, v, e in X:
        cf = cf_name(f); fl = M.nodes.get(p) and M.nodes[p].fields.get(cf)
        if fl and fl.access in ("inputOnly", "outputOnly"): continue
        if cf in UNIVERSAL: continue
        if v == "R" and UR.get((c, p, f)) == "Y": out.append((c, p, cf, e))
    return out


_M = None
def load():
    global _M
    if _M is None: _M = Model()
    return _M
