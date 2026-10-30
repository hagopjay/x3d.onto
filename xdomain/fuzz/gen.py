"""Scene generator: sample containment top-down from X3DUOM ranges ('uom') or the verified matrix ('verified'), fill a few fields with
values X3DUOM calls legal, add DEF/USE and type-matched ROUTEs. Mutation mode starts from an excerpt of a real scene instead.
Every scene is a pure function of (seed, index, options): scene(seed, i) gives the same bytes every time."""
import random, re, sys
from pathlib import Path
from lxml import etree
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model  # noqa

PROFILES = ["Interchange", "Interactive", "Immersive", "CADInterchange", "MedicalInterchange"]
SKIP_FIELDS = re.compile(r"(url|Url|Index|index|^set_|_changed$|^image$|matrix|Matrix|^source$|^family$|^string$)")
SKIP_TYPES = {"SFImage", "MFImage", "SFMatrix3f", "SFMatrix4f", "MFMatrix3f", "MFMatrix4f", "SFMatrix3d", "SFMatrix4d", "MFMatrix3d", "MFMatrix4d", "xs:NMTOKEN", "MFQuaternion"}
WIDTH = {"SFVec2f": 2, "SFVec2d": 2, "SFVec3f": 3, "SFVec3d": 3, "SFVec4f": 4, "SFVec4d": 4, "SFColor": 3, "SFColorRGBA": 4, "SFRotation": 4}
_root_cache = {}


def scene_roots(M):
    """Concrete nodes the fork's XSD accepts directly under <Scene> (measured once per process: 267 validations)."""
    if "r" not in _root_cache:
        sys.path.insert(0, str(model.FORK / "src"))
        from validation.validate import validate_xml
        _root_cache["r"] = [n for n in sorted(M.nodes) if validate_xml(wrap(f"<{n}/>"))["valid"]]
    return _root_cache["r"]


def wrap(body, profile="Full", head=""):
    """A whole document, indented one element per line (XSD messages carry line numbers; classify.py maps them back to elements)."""
    h = f"<head>{head}</head>" if head else ""
    doc = f"<X3D profile='{profile}' version='4.1'>{h}<Scene>{body}</Scene></X3D>"
    root = etree.fromstring(doc, etree.XMLParser(remove_blank_text=True)); etree.indent(root, "  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root, encoding="unicode") + "\n"


def _fmt(x, integer=False):
    return str(int(x)) if integer else (f"{x:.3f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x)))


def value(fl, R, legal=True):
    """A value for one non-node field. legal=True stays inside UOM bounds/enumerations; False steps just outside a bound (for mutation)."""
    t = fl.type; base = t.replace("MF", "SF")
    lo = fl.lo if fl.lo is not None else (0.0 if base == "SFColor" or base == "SFColorRGBA" else -5.0)
    hi = fl.hi if fl.hi is not None else (1.0 if base in ("SFColor", "SFColorRGBA") else 5.0)
    if fl.lo is not None and fl.hi is None: hi = max(hi, fl.lo + 5)
    if fl.hi is not None and fl.lo is None: lo = min(lo, fl.hi - 5)
    if not legal:
        if fl.lo is None and fl.hi is None: return None
        x = (fl.lo - 1) if fl.lo is not None else (fl.hi + 1)
        n = WIDTH.get(base, 1); return " ".join(_fmt(x) for _ in range(n))
    integer = base == "SFInt32"
    def num():
        if fl.lo_excl and fl.hi is None and lo == 0: return R.choice([0.5, 1, 2])
        x = R.uniform(lo, hi) if not integer else R.randint(int(max(lo, -5)), int(min(hi, 5)) if hi >= lo else int(lo))
        if fl.lo_excl and x <= lo: x = lo + (hi - lo) / 2
        if fl.hi_excl and x >= hi: x = lo + (hi - lo) / 2
        return round(x, 3) if not integer else x
    def one():
        if base == "SFBool": return R.choice(["true", "false"])
        if base == "SFString":
            if fl.enum: return R.choice(fl.enum)
            return "fz" + str(R.randint(0, 99))
        if base == "SFRotation": return R.choice(["0 1 0 ", "1 0 0 ", "0 0 1 "]) + _fmt(round(R.uniform(-3, 3), 3))
        if base in WIDTH: return " ".join(_fmt(num(), integer) for _ in range(WIDTH[base]))
        if base in ("SFFloat", "SFDouble", "SFTime", "SFInt32"): return _fmt(num(), integer)
        return None
    if t == "SFString": return one()
    if t == "MFString":
        if fl.enum: return " ".join((v if v.startswith('"') else f'"{v}"') for v in (R.choice(fl.enum) for _ in range(R.randint(1, 2))))   # UOM writes some MFString choices already quoted
        return '"fz"'
    if t.startswith("MF"):
        k = R.randint(1, 3); vs = [one() for _ in range(k)]
        return None if None in vs else (", " if base in WIDTH else " ").join(vs)
    return one()


class Builder:
    def __init__(self, R, M, mode, depth, fill=2, def_p=0.35, use_p=0.08, route_p=0.6, prefix="N"):
        self.R, self.M, self.mode, self.depth, self.fill = R, M, mode, depth, fill
        self.def_p, self.use_p, self.route_p = def_p, use_p, route_p
        self.E = M.edges(mode); self.defs = []; self.n = 0; self.done = set(); self.prefix = prefix
        self.by_parent = {}
        for (p, f), kids in self.E.items(): self.by_parent.setdefault(p, []).append((f, kids))

    def node(self, tag, d, field=None, stack=()):
        R, M = self.R, self.M; self.n += 1
        el = etree.Element(tag)
        if field and field != M.nodes[tag].cf_default: el.set("containerField", field)
        if R.random() < self.def_p: el.set("DEF", f"{self.prefix}{self.n}")
        fs = [f for f in M.nodes[tag].fields.values() if f.type not in ("SFNode", "MFNode") and f.access in model.CONTAIN
              and f.type not in SKIP_TYPES and not SKIP_FIELDS.search(f.name) and f.name not in ("DEF", "USE", "class", "id", "style", "containerField")]
        for f in R.sample(fs, min(len(fs), R.randint(0, self.fill))):
            v = value(f, R)
            if v is not None: el.set(f.name, v)
        if d < self.depth:
            slots = self.by_parent.get(tag, [])
            for f, kids in R.sample(slots, min(len(slots), R.randint(0, 2))):
                fl = M.nodes[tag].fields[f]; k = 1 if fl.type == "SFNode" else R.randint(1, 2)
                for _ in range(k):
                    reuse = [x for x in self.defs if x.tag in kids and x not in stack and id(x) in self.done]
                    if reuse and R.random() < self.use_p:
                        src = R.choice(reuse); u = etree.SubElement(el, src.tag); u.set("USE", src.get("DEF"))
                        if f != M.nodes[src.tag].cf_default: u.set("containerField", f)
                    else:
                        el.append(self.node(R.choice(kids), d + 1, f, stack + (el,)))
        if el.get("DEF"): self.defs.append(el)
        self.done.add(id(el))
        return el

    def routes(self, k):
        out = []
        M, R = self.M, self.R
        srcs = [(e, f) for e in self.defs for f in M.nodes[e.tag].fields.values() if f.access in ("outputOnly", "inputOutput") and f.type not in ("SFNode", "MFNode")]
        dsts = {}
        for e in self.defs:
            for f in M.nodes[e.tag].fields.values():
                if f.access in ("inputOnly", "inputOutput") and f.type not in ("SFNode", "MFNode"): dsts.setdefault(f.type, []).append((e, f))
        for _ in range(k):
            if not srcs: break
            e, f = R.choice(srcs); cands = [x for x in dsts.get(f.type, []) if x[0] is not e]
            if not cands: continue
            e2, f2 = R.choice(cands)
            r = etree.Element("ROUTE"); r.set("fromNode", e.get("DEF")); r.set("fromField", f.name); r.set("toNode", e2.get("DEF")); r.set("toField", f2.name)
            out.append(r)
        return out


def header(R, M, tags, p_full=0.8):
    """Profile plus, sometimes, component statements: Full most of the time, otherwise a smaller profile with or without the components the scene needs."""
    if R.random() < p_full: return "Full", ""
    prof = R.choice(PROFILES)
    comps = {}
    for t in tags:
        n = M.nodes.get(t)
        if n and n.component: comps[n.component] = max(comps.get(n.component, 0), n.level)
    if R.random() < 0.5 or not comps: return prof, ""
    pick = R.sample(sorted(comps), max(1, len(comps) // 2))
    return prof, "".join(f"<component name='{c}' level='{comps[c]}'/>" for c in pick)


def scene(seed, i, mode="uom", depth=None, M=None):
    """Generated scene number i of run `seed`. depth: max nesting below the Scene root (default: 1 to 5 cycling with i)."""
    M = M or model.load(); R = random.Random(f"{seed}:{i}:{mode}")
    depth = depth if depth is not None else 1 + i % 5
    roots = scene_roots(M)
    if mode == "verified":
        reach = {p for p, _ in M.edges("verified")}
        roots = [r for r in roots if r in reach] or roots
    b = Builder(R, M, mode, depth)
    body = [b.node(R.choice(roots), 0) for _ in range(R.randint(1, 3))]
    if R.random() < b.route_p: body += b.routes(R.randint(1, 2))
    tags = {e.tag for x in body for e in x.iter()}
    prof, head = header(R, M, tags)
    return wrap("\n".join(etree.tostring(x, encoding="unicode") for x in body), prof, head)


# ---------- mutation mode ----------
SEED_SCENES = ["scenes/ontology-constellation.x3d", "demo/scenes/ontology-dyson.x3d", "gobbler-demiurge/assets/tender/tender.x3d",
               "gobbler-demiurge/assets/feathers/feather_a.x3d", "gobbler-demiurge/assets/villager/villager_b.x3d"]
_seed_cache = {}


def seed_trees(paths=None):
    key = tuple(paths or SEED_SCENES)
    if key not in _seed_cache:
        out = []
        for p in key:
            fp = Path(p) if Path(p).is_absolute() else model.REPO / p
            if fp.exists(): out.append((fp.name, etree.parse(str(fp), etree.XMLParser(remove_comments=True, huge_tree=True)).getroot()))
        _seed_cache[key] = out
    return _seed_cache[key]


def excerpt(root, R, max_el=60):
    """A legal-looking slice of a real scene: the path from Scene to one subtree of at most max_el elements, siblings pruned,
    url fields, protos, scripts and dangling USE/ROUTE removed."""
    sc = root.find(".//Scene")
    cands = [e for e in sc.iter() if isinstance(e.tag, str) and e is not sc and e.tag not in ("ROUTE",) and sum(1 for _ in e.iter()) <= max_el]
    if not cands: return None
    pick = R.choice(cands)
    keep = set(pick.iter()) | set(pick.iterancestors())
    new = etree.fromstring(etree.tostring(sc))
    # map by preorder index
    old_list = list(sc.iter()); new_list = list(new.iter()); idx = {id(o): n for o, n in zip(old_list, new_list)}
    keep_new = {id(idx[id(e)]) for e in keep if id(e) in idx}
    defs_kept = {idx[id(e)].get("DEF") for e in keep if id(e) in idx and idx[id(e)].get("DEF")}
    for e in list(new.iter()):
        if e is new or not isinstance(e.tag, str): continue
        if id(e) not in keep_new and e.tag != "ROUTE" and e.getparent() is not None and id(e.getparent()) in keep_new | {id(new)}:
            e.getparent().remove(e)
    for e in list(new.iter()):
        if not isinstance(e.tag, str) or e is new: continue
        if e.tag in ("ProtoDeclare", "ExternProtoDeclare", "ProtoInstance", "Script", "Inline", "IMPORT", "EXPORT", "ComposedShader", "PackagedShader", "ProgramShader"):
            if e.getparent() is not None: e.getparent().remove(e); continue
        for a in list(e.attrib):
            if "url" in a.lower() or a.startswith("{"): del e.attrib[a]
    defs = {e.get("DEF") for e in new.iter() if isinstance(e.tag, str) and e.get("DEF")}
    for e in list(new.iter()):
        if not isinstance(e.tag, str): continue
        if e.tag == "ROUTE" and not (e.get("fromNode") in defs and e.get("toNode") in defs): e.getparent().remove(e)
        elif e.get("USE") and e.get("USE") not in defs and e.getparent() is not None: e.getparent().remove(e)
    return new


MUTATIONS = ["swap_child", "move_field", "route_first", "add_route", "set_value", "out_of_range", "profile_swap", "deepen"]


def mutate(seed, i, M=None, paths=None, k=None):
    """Mutant number i: an excerpt of a real scene with 1 to 3 operators applied. Returns (xml, [ops])."""
    M = M or model.load(); R = random.Random(f"{seed}:{i}:mut")
    trees = seed_trees(paths)
    name, root = R.choice(trees)
    sc = excerpt(root, R)
    if sc is None: return scene(seed, i, M=M), ["fallback"]
    ops = []
    prof = "Full"; head = ""
    for _ in range(k or R.randint(1, 3)):
        op = R.choice(MUTATIONS); els = [e for e in sc.iter() if isinstance(e.tag, str) and e.tag in M.nodes and e.getparent() is not None and e.getparent().tag in M.nodes]
        if op == "swap_child" and els:
            e = R.choice(els); f = e.get("containerField") or M.nodes[e.tag].cf_default
            kids = M.edges("uom").get((e.getparent().tag, f), [])
            if kids and not e.get("USE") and not e.get("DEF"):
                new = etree.Element(R.choice(kids))
                if f != M.nodes[new.tag].cf_default: new.set("containerField", f)
                e.getparent().replace(e, new); ops.append(f"swap_child:{e.tag}->{new.tag}")
        elif op == "move_field" and els:
            e = R.choice(els); p = e.getparent().tag
            alts = [f for (pp, f), kids in M.edges("uom").items() if pp == p and e.tag in kids and f != (e.get("containerField") or M.nodes[e.tag].cf_default)]
            if alts:
                f = R.choice(alts)
                if f == M.nodes[e.tag].cf_default: e.attrib.pop("containerField", None)
                else: e.set("containerField", f)
                ops.append(f"move_field:{p}.{f}<-{e.tag}")
        elif op == "route_first":
            rs = [e for e in sc.iter("ROUTE")]
            if not rs:
                b = Builder(R, M, "uom", 0); b.defs = [e for e in sc.iter() if isinstance(e.tag, str) and e.get("DEF") and e.tag in M.nodes]; rs = b.routes(1)
            if rs:
                r = R.choice(rs)
                if r.getparent() is not None: r.getparent().remove(r)
                sc.insert(0, r); ops.append("route_first")
        elif op == "add_route":
            b = Builder(R, M, "uom", 0); b.defs = [e for e in sc.iter() if isinstance(e.tag, str) and e.get("DEF") and e.tag in M.nodes]
            for r in b.routes(1): sc.append(r); ops.append("add_route")
        elif op in ("set_value", "out_of_range"):
            nodes = [e for e in sc.iter() if isinstance(e.tag, str) and e.tag in M.nodes and not e.get("USE")]
            if nodes:
                e = R.choice(nodes)
                fs = [f for f in M.nodes[e.tag].fields.values() if f.type not in ("SFNode", "MFNode") and f.access in model.CONTAIN and f.type not in SKIP_TYPES and not SKIP_FIELDS.search(f.name)]
                if op == "out_of_range": fs = [f for f in fs if f.lo is not None or f.hi is not None]
                if fs:
                    f = R.choice(fs); v = value(f, R, legal=(op == "set_value"))
                    if v is not None: e.set(f.name, v); ops.append(f"{op}:{e.tag}.{f.name}")
        elif op == "profile_swap":
            prof = R.choice(PROFILES); ops.append(f"profile:{prof}")
        elif op == "deepen" and els:
            e = R.choice(els)
            if not e.get("USE"):
                b = Builder(R, M, "uom", 2, prefix=f"FZ{len(ops)}_"); slots = b.by_parent.get(e.tag, [])
                if slots:
                    f, kids = R.choice(slots); e.append(b.node(R.choice(kids), 1, f)); ops.append(f"deepen:{e.tag}.{f}")
    etree.cleanup_namespaces(sc)
    body = "\n".join(etree.tostring(x, encoding="unicode") for x in sc)
    return wrap(body, prof, head), [f"seed:{name}"] + ops
