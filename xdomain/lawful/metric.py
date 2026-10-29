"""The lawful metric: a graded score for one X3D document against the task that asked for it.

Six parts, each a number in [0, 1] (or None when it does not apply), plus one scalar and a feedback text:
  a  well_formed  the text parses as XML with an <X3D> root and a <Scene>
  b  valid        XSD (the fork's validate_xml, schema chosen by the document's version) and the fork's semantic
                  errors; this is the "strict validity" gate of xdomain/eval-plan/x3d_domain.py
  c  lawful       every parent.field -> child placement is allowed by the X3DUOM acceptableNodeTypes of that field
                  (the X3DUOM of the document's own version), a USE has the type of its DEF, an SFNode field holds
                  one node; each placement is also looked up in the XSD-verified matrix data/xcheck_all.json
  d  use_type     the node kinds the task needs are there, in the counts it needs, nothing it forbids is there, and
                  every required interpolator is wired TimeSensor -> interpolator -> a field of the right kind
  e  spatial      relations the task names (on top of, above, left of, side by side, a row, pointing down) and
                  "no floating parts", from world-space bounding boxes of the geometry that can be measured;
                  contact tolerance 5% (DIRECTIONS E20); None when the task names no spatial relation
  f  hatches      escape hatches closed: profile Full (or none) counts against, so do a profile above the smallest
                  sufficient one, component statements nothing needs, and Script / Inline / ExternProtoDeclare the
                  task did not ask for

Scalar = weighted mean of the parts that apply (weights W); 0 if not well-formed; halved if not XSD-valid.
Needs lxml and a checkout of the x3d_mcp fork (X3D_MCP, default /home/user/x3d_mcp). No model is called.
usage: metric.py FILE.x3d [--prompt TEXT]   prints the score, the parts and the feedback."""
import json, math, os, re, sys
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
X3D_MCP = Path(os.environ.get("X3D_MCP", "/home/user/x3d_mcp"))
if str(X3D_MCP / "src") not in sys.path:
    sys.path.insert(0, str(X3D_MCP / "src"))
from lxml import etree  # noqa: E402
from validation.validate import validate_xml  # noqa: E402
from validation.semantic import semantic_diagnostics  # noqa: E402
from validation.profile import profile_nodes  # noqa: E402
from x3d_utils.x3duom import X3DUOM, SCHEMAS_DIR  # noqa: E402

W = dict(well_formed=0.10, valid=0.20, lawful=0.20, use_type=0.25, spatial=0.15, hatches=0.10)
TOL = 0.05                      # contact tolerance, a fraction of the larger extent on the axis (DIRECTIONS E20)
PROFILE_CHAIN = ["Core", "Interchange", "Interactive", "Immersive", "Full"]
HATCH_NODES = ("Script", "Inline", "ExternProtoDeclare")
STATEMENTS = {"ROUTE", "IS", "connect", "field", "fieldValue", "ProtoDeclare", "ProtoInterface", "ProtoBody",
              "ExternProtoDeclare", "IMPORT", "EXPORT", "ProtoInstance", "head", "meta", "component", "unit", "Scene", "X3D"}
GEOM_WORDS = {"Box": ("box", "cube", "block", "slab", "brick"), "Sphere": ("sphere", "ball", "globe"),
              "Cone": ("cone",), "Cylinder": ("cylinder", "pole", "column")}


# ---------------------------------------------------------------- task spec
@dataclass
class TaskSpec:
    """What the request asks for, in checkable terms. Built by hand, from a prompt file, or by spec_from_text."""
    prompt: str
    required: list = field(default_factory=list)       # node kinds that must appear (ROUTE counts as a kind)
    min_counts: dict = field(default_factory=dict)     # kind -> minimum count; keys USE and DEF count attributes
    forbidden: list = field(default_factory=list)      # node kinds that must not appear
    relations: list = field(default_factory=list)      # [rel, a, b] with a/b a geometry kind or a DEF-name token
    connected: bool = False                            # the parts should form one assembly (no floating parts)
    allow: list = field(default_factory=list)          # escape hatches the task allows: "Full", "Script", "Inline", ...
    version: str = "4.0"
    profile: str = ""                                  # a profile the request itself orders (then declaring it is not a hatch)
    pid: str = ""

    def to_json(self): return asdict(self)

    @staticmethod
    def from_json(d): return TaskSpec(**{k: v for k, v in d.items() if k in TaskSpec.__dataclass_fields__})


def spec_from_text(prompt, pid=""):
    """A heuristic spec from free text (grade L: keyword rules, mine). Explicit specs beat this one."""
    t = prompt.lower(); req, rel, mc = [], [], {}
    found = {k: any(re.search(rf"\b{w}s?\b", t) for w in ws) for k, ws in GEOM_WORDS.items()}
    req += [k for k, v in found.items() if v]
    if re.search(r"\b(rotat|spin|turn|sweep|swing|sway|orbit|wav)", t): req += ["TimeSensor", "OrientationInterpolator", "ROUTE"]
    if re.search(r"\b(bounc|mov|rise|fly|flying|path)\w*", t) and "PositionInterpolator" not in req: req += ["TimeSensor", "PositionInterpolator", "ROUTE"]
    if re.search(r"\b(click|touch|press)", t): req += ["TouchSensor", "ROUTE"]
    for n in re.findall(r"\b([A-Z][A-Za-z0-9]+(?:Sensor|Interpolator|Light|Material|Set|Grid|Toggle|Viewpoint|Location|LOD|Humanoid|Joint|Segment|Site|Extrusion))\b", prompt):
        req.append(n)
    kinds = [k for k, v in found.items() if v]
    for phrase, rname in (("on top of", "on_top"), ("above", "above")):
        m = re.search(rf"(\w+) (?:\w+ )?{phrase} ((?:\w+ ?){{1,4}})", t)
        if m:
            before = t[: m.start(1) + len(m.group(1))].split()[-3:]
            a = next((_kind_of(w) for w in reversed(before) if _kind_of(w)), None)
            b = next((_kind_of(w) for w in m.group(2).split() if _kind_of(w)), None)
            if a and b: rel.append([rname, a, b])
    if "side by side" in t and len(kinds) >= 2: rel.append(["side_by_side", kinds[0], kinds[1]])
    m = re.search(r"\b(two|three|four|five|six) (\w+?)s? in a row", t)
    if m:
        k = _kind_of(m.group(2)); n = ["two", "three", "four", "five", "six"].index(m.group(1)) + 2
        if k: rel.append(["row_x", k, n]); mc[k] = n
    if re.search(r"pointing down", t):
        for k in ("Cone",):
            if found.get(k): rel.append(["points_down", k, None])
    connected = bool(re.search(r"\b(with|made of|made from|built from)\b.*\b(and|legs|parts)\b", t)) and not rel
    return TaskSpec(prompt=prompt, required=sorted(set(req)), min_counts=mc, relations=rel, connected=connected, pid=pid)


def _kind_of(word):
    for k, ws in GEOM_WORDS.items():
        if any(word.startswith(w) for w in ws): return k
    return None


# ---------------------------------------------------------------- X3DUOM tables (per version)
@lru_cache(maxsize=4)
def uom(version):
    p = SCHEMAS_DIR / f"X3dUnifiedObjectModel-{'4.1' if version == '4.1' else '4.0'}.xml"
    u = X3DUOM(p); return u.get_concrete_nodes(), u.get_abstract_types()


@lru_cache(maxsize=4)
def _ancestry_table(version):
    nodes, abstracts = uom(version); out = {}
    for name in nodes:
        seen, todo = {name}, [name]
        while todo:
            cur = todo.pop(); info = nodes.get(cur) or abstracts.get(cur) or {}
            for b in [info.get("baseType"), *info.get("additionalBaseTypes", [])]:
                if b and b not in seen: seen.add(b); todo.append(b)
        out[name] = seen
    return out


@lru_cache(maxsize=1)
def verified_matrix():
    """(child, parent, ontology field) -> XSD verdict A/R/I from data/xcheck_all.json (4.1 XSD, every ontology pair)."""
    p = REPO / "data" / "xcheck_all.json"
    if not p.exists(): return {}
    return {(c, pa, f): v for c, pa, f, v, _ in json.loads(p.read_text())["rows"]}


def _accepts(field_info, anc):
    acc = {t for t in re.split(r"[|\s]+", field_info.get("acceptableNodeTypes") or "") if t}
    return None if not acc else bool(anc & acc)


# ---------------------------------------------------------------- helpers
def local(el): t = el.tag; return "" if not isinstance(t, str) else t.split("}", 1)[1] if t.startswith("{") else t


def extract(text):
    """The document from a model answer: the longest fenced block, else from <?xml or <X3D to </X3D>."""
    blocks = re.findall(r"```[a-zA-Z0-9]*\n(.*?)```", text or "", re.S)
    if blocks: return max(blocks, key=len).strip()
    m = re.search(r"(<\?xml.*?</X3D>|<X3D\b.*?</X3D>)", text or "", re.S)
    return m.group(1).strip() if m else (text or "").strip()


def floats(s):
    try: return [float(x) for x in re.split(r"[\s,]+", (s or "").strip()) if x]
    except ValueError: return []


# ---------------------------------------------------------------- 4x4 math (row-major, column vectors)
def mmul(a, b): return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def ident(): return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
def tmat(t): m = ident(); m[0][3], m[1][3], m[2][3] = t; return m
def smat(s): m = ident(); m[0][0], m[1][1], m[2][2] = s; return m
def rmat(r):
    x, y, z, a = (list(r) + [0, 1, 0, 0])[:4] if len(r) >= 4 else (0, 1, 0, 0)
    n = math.sqrt(x * x + y * y + z * z) or 1.0; x, y, z = x / n, y / n, z / n; c, s, C = math.cos(a), math.sin(a), 1 - math.cos(a)
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s, 0], [y * x * C + z * s, c + y * y * C, y * z * C - x * s, 0],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C, 0], [0, 0, 0, 1]]
def apply(m, p): return [m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3] for i in range(3)]


def transform_matrix(el):
    """X3D Transform order: T * C * R * SR * S * -SR * -C (the same fields on HAnimJoint/HAnimHumanoid)."""
    g = lambda k, d: (floats(el.get(k)) + d)[: len(d)] if el.get(k) is not None else d
    t, c, r = g("translation", [0, 0, 0]), g("center", [0, 0, 0]), g("rotation", [0, 0, 1, 0])
    s, so = g("scale", [1, 1, 1]), g("scaleOrientation", [0, 0, 1, 0])
    soi = list(so[:3]) + [-so[3]]
    m = tmat(t)
    for x in (tmat(c), rmat(r), rmat(so), smat(s), rmat(soi), tmat([-c[0], -c[1], -c[2]])): m = mmul(m, x)
    return m


# ---------------------------------------------------------------- geometry bounds
def local_bounds(geom, defs):
    """(min[3], max[3], how) of a geometry node in its own frame, or None when it cannot be measured."""
    tag = local(geom)
    if geom.get("USE"): geom = defs.get(geom.get("USE"), geom); tag = local(geom)
    f = lambda k, d: (floats(geom.get(k)) or d)
    if tag == "Box": s = (f("size", [2, 2, 2]) + [2, 2, 2])[:3]; return [-s[0] / 2, -s[1] / 2, -s[2] / 2], [s[0] / 2, s[1] / 2, s[2] / 2], "exact"
    if tag == "Sphere": r = f("radius", [1])[0]; return [-r] * 3, [r] * 3, "exact"
    if tag == "Cone": r, h = f("bottomRadius", [1])[0], f("height", [2])[0]; return [-r, -h / 2, -r], [r, h / 2, r], "exact"
    if tag == "Cylinder": r, h = f("radius", [1])[0], f("height", [2])[0]; return [-r, -h / 2, -r], [r, h / 2, r], "exact"
    if tag == "Rectangle2D": s = (f("size", [2, 2]) + [2, 2])[:2]; return [-s[0] / 2, -s[1] / 2, 0], [s[0] / 2, s[1] / 2, 0], "exact"
    if tag == "Disk2D": r = f("outerRadius", [1])[0]; return [-r, -r, 0], [r, r, 0], "exact"
    if tag == "ElevationGrid":
        xd, zd = int(f("xDimension", [0])[0]), int(f("zDimension", [0])[0]); xs, zs = f("xSpacing", [1])[0], f("zSpacing", [1])[0]; h = f("height", [0])
        if xd < 2 or zd < 2: return None
        return [0, min(h or [0]), 0], [(xd - 1) * xs, max(h or [0]), (zd - 1) * zs], "exact"
    if tag == "Extrusion":
        sp = f("spine", [0, 0, 0, 0, 1, 0]); cs = f("crossSection", [1, 1, 1, -1, -1, -1, -1, 1, 1, 1]); sc = f("scale", [1, 1])
        if len(sp) < 6: return None
        rad = max(math.hypot(cs[i], cs[i + 1]) for i in range(0, len(cs) - 1, 2)) * max(sc or [1])
        pts = [sp[i:i + 3] for i in range(0, len(sp) - 2, 3)]
        return [min(p[k] for p in pts) - rad for k in range(3)], [max(p[k] for p in pts) + rad for k in range(3)], "approx"
    for ch in geom:
        if local(ch) in ("Coordinate", "CoordinateDouble"):
            c = defs.get(ch.get("USE"), ch) if ch.get("USE") else ch; p = floats(c.get("point"))
            if len(p) >= 3:
                pts = [p[i:i + 3] for i in range(0, len(p) - 2, 3)]
                return [min(q[k] for q in pts) for k in range(3)], [max(q[k] for q in pts) for k in range(3)], "points"
    return None


@dataclass
class Part:
    kind: str; names: list; lo: list; hi: list; how: str; up: list
    def ext(self, k): return self.hi[k] - self.lo[k]
    def mid(self, k): return (self.hi[k] + self.lo[k]) / 2


def parts(scene, defs):
    """World-space boxes of every Shape whose geometry can be measured. Expands USE; skips Geo* frames and Switch choices
    other than whichChoice; counts what it could not measure."""
    out, skipped = [], []
    def walk(el, m, names, depth):
        if depth > 60: return
        if el.get("USE") and el.get("USE") in defs and local(el) not in ("Coordinate",): el = defs[el.get("USE")]
        tag = local(el); nm = names + ([el.get("DEF")] if el.get("DEF") else [])
        if tag.startswith("Geo") and tag != "GeoViewpoint": skipped.append(tag); return
        if tag in ("Transform", "HAnimJoint", "HAnimHumanoid", "HAnimSite"): m = mmul(m, transform_matrix(el))
        if tag == "Shape":
            g = [c for c in el if local(c) and local(c) not in ("Appearance", "IS") and not local(c).startswith("Metadata")]
            if not g: return
            b = local_bounds(g[0], defs); gk = local(defs.get(g[0].get("USE"), g[0]) if g[0].get("USE") else g[0])
            if b is None: skipped.append(gk); return
            lo, hi, how = b
            corners = [apply(m, [x, y, z]) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
            up = [m[0][1], m[1][1], m[2][1]]
            out.append(Part(gk, nm, [min(c[k] for c in corners) for k in range(3)], [max(c[k] for c in corners) for k in range(3)], how, up)); return
        kids = list(el)
        if tag == "Switch":
            w = int((floats(el.get("whichChoice")) or [-1])[0]); kids = [c for c in kids if local(c)]; kids = [kids[w]] if 0 <= w < len(kids) else []
        for c in kids:
            if local(c) and local(c) not in ("ROUTE", "ProtoDeclare", "ExternProtoDeclare"): walk(c, m, nm, depth + 1)
    walk(scene, ident(), [], 0)
    return out, skipped


def _select(ps, token):
    if token is None: return []
    if token == "ground":   # the part with the largest horizontal footprint
        return [max(ps, key=lambda p: p.ext(0) * p.ext(2))] if ps else []
    t = str(token).lower()
    return [p for p in ps if p.kind == token or any(t in (n or "").lower() for n in p.names)]


def _gap(a, b, k):   # signed gap on axis k: >0 separated, <0 overlapping
    return max(a.lo[k] - b.hi[k], b.lo[k] - a.hi[k])


def relation(rel, ps):
    """-> (ok: bool|None, message). None = cannot be judged (a part is missing or not measurable)."""
    r, a, b = (list(rel) + [None, None])[:3]
    A, B = _select(ps, a), _select(ps, b)
    if r == "row_x":
        n = int(b); A = sorted(A, key=lambda p: p.mid(0))
        if len(A) < n: return False, f"row: needs {n} {a} parts side by side along x, found {len(A)} measurable"
        xs = [p.mid(0) for p in A]; ys = [p.mid(1) for p in A]
        ok = all(xs[i + 1] - xs[i] > 0.5 * max(A[i].ext(0), A[i + 1].ext(0)) for i in range(len(xs) - 1)) and max(ys) - min(ys) <= max(p.ext(1) for p in A)
        return ok, f"row of {n} {a}: x centres {[round(x, 2) for x in xs[:n]]}" + ("" if ok else " (overlapping or not level)")
    if r == "points_down":
        if not A: return None, f"points_down: no measurable {a}"
        ok = all(p.up[1] < 0 for p in A)
        return ok, f"{a} apex direction y = {[round(p.up[1], 2) for p in A]} (negative = down)"
    if not A or not B: return None, f"{r}({a}, {b}): {'no measurable ' + str(a) if not A else 'no measurable ' + str(b)}"
    best = None
    for pa in A:
        for pb in B:
            if pa is pb: continue
            tol = TOL * max(pa.ext(1), pb.ext(1), 1e-9)
            if r == "on_top":
                d = pa.lo[1] - pb.hi[1]; over = _gap(pa, pb, 0) <= 0 and _gap(pa, pb, 2) <= 0
                ok = abs(d) <= tol and over
                msg = (f"{a} bottom at y={pa.lo[1]:.3g}, {b} top at y={pb.hi[1]:.3g}: " + ("in contact" if abs(d) <= tol else ("gap " if d > 0 else "sinks ") + f"{abs(d):.3g} (tolerance {tol:.3g})")
                       + ("" if over else "; not over its footprint"))
            elif r == "above":
                d = pa.lo[1] - pb.hi[1]; ok = d >= -tol; msg = f"{a} bottom y={pa.lo[1]:.3g} vs {b} top y={pb.hi[1]:.3g}"
            elif r == "left_of":
                ok = pa.mid(0) < pb.mid(0); msg = f"{a} centre x={pa.mid(0):.3g}, {b} centre x={pb.mid(0):.3g}"
            elif r == "side_by_side":
                tolh = TOL * max(pa.ext(0), pb.ext(0), pa.ext(2), pb.ext(2))
                ok = max(_gap(pa, pb, 0), _gap(pa, pb, 2)) >= -tolh and _gap(pa, pb, 1) <= 0
                msg = f"{a} and {b}: horizontal gap {max(_gap(pa, pb, 0), _gap(pa, pb, 2)):.3g}, vertical overlap {'yes' if _gap(pa, pb, 1) <= 0 else 'no'}"
            else: return None, f"unknown relation {r}"
            if best is None or ok: best = (ok, msg)
            if ok: return best
    return best if best else (None, f"{r}({a}, {b}): one part only")


def connectivity(ps):
    """Share of parts in the largest group of parts that touch (bounding-box gap within tolerance on every axis)."""
    if len(ps) < 2: return 1.0, ""
    n = len(ps); par = list(range(n))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ps[i], ps[j]
            if all(_gap(a, b, k) <= TOL * max(a.ext(k), b.ext(k), 1e-9) + 1e-9 for k in range(3)): par[find(i)] = find(j)
    groups = {}
    for i in range(n): groups.setdefault(find(i), []).append(i)
    big = max(groups.values(), key=len); loose = [ps[i] for i in range(n) if i not in big]
    names = ", ".join(f"{p.kind}{'(' + p.names[-1] + ')' if p.names else ''} at y={p.mid(1):.2g}" for p in loose[:4])
    return len(big) / n, (f"{len(loose)} of {n} parts float free of the main assembly: {names}" if loose else "")


# ---------------------------------------------------------------- the metric
@dataclass
class LawfulScore:
    score: float
    parts: dict
    feedback: str
    details: dict

    def to_json(self): return asdict(self)


def _profile_rank(p): return PROFILE_CHAIN.index(p) if p in PROFILE_CHAIN else None


def minimal_profile(tags, version="4.0"):
    """The smallest of Interchange, Interactive, Immersive whose missing nodes come from at most one component (one
    component statement in the header). Full is never needed: any node is reachable by component statements."""
    pn = profile_nodes(); nodes, _ = uom(version); used = {t for t in tags if t not in STATEMENTS and t in nodes}
    for p in ("Interchange", "Interactive", "Immersive"):
        if len({nodes[t]["component"] for t in used - pn[p]}) <= 1: return p
    return "Immersive"


def _profile_level(profile, comp, version):
    """The highest level of `comp` the profile already includes (0 if none)."""
    nodes, _ = uom(version); allowed = profile_nodes().get(profile)
    if allowed is None: return 99
    return max([nodes[n]["level"] or 1 for n in allowed if n in nodes and nodes[n]["component"] == comp] or [0])


def score(xml, spec, run_fork=True):
    """-> LawfulScore. xml is the document (or a model answer; it is extracted). spec is a TaskSpec or a prompt string."""
    if isinstance(spec, str): spec = spec_from_text(spec)
    xml = extract(xml); fb = []; det = {}; P = {k: None for k in W}
    # a well-formed
    try:
        root = etree.fromstring(xml.encode("utf-8"), etree.XMLParser(remove_comments=True, resolve_entities=False, no_network=True))
        scene = next((e for e in root.iter() if local(e) == "Scene"), None)
        P["well_formed"] = 1.0 if local(root) == "X3D" and scene is not None else 0.0
        if not P["well_formed"]: fb.append("[well_formed] the root must be <X3D> with a <Scene> inside.")
    except etree.XMLSyntaxError as e:
        P["well_formed"] = 0.0; fb.append(f"[well_formed] not XML: {e}")
    if not P["well_formed"]:
        P = {k: (0.0 if k != "spatial" else None) for k in W}; P["well_formed"] = 0.0
        return LawfulScore(0.0, P, "\n".join(fb), dict(xsd_valid=False, strict_valid=False))
    version = root.get("version") or spec.version or "4.0"; det["version"] = version
    nodes, _ = uom(version); anc = _ancestry_table(version)
    all_els = [e for e in scene.iter() if local(e)]
    tags = [local(e) for e in all_els]
    defs = {e.get("DEF"): e for e in all_els if e.get("DEF")}
    # b valid
    v = validate_xml(xml); xsd = bool(v.get("valid")); det["xsd_valid"] = xsd; det["xsd_errors"] = (v.get("errors") or [])[:5]
    sem = []
    if run_fork:
        try: sem = [d for d in semantic_diagnostics(xml) if d.level == "error"]
        except Exception as e: sem = [type("D", (), dict(check="semantic-crash", message=str(e)[:160], level="error"))()]
    det["semantic_errors"] = sorted({d.check for d in sem}); strict = xsd and not sem; det["strict_valid"] = strict
    P["valid"] = (1.0 if strict else 0.75 / (1 + 0.25 * len(sem))) if xsd else 0.4 / (1 + len(v.get("errors") or [1]))
    for e in (v.get("errors") or [])[:3]: fb.append(f"[valid] XSD: {e[:200]}")
    for d in sem[:3]: fb.append(f"[valid] {d.check}: {d.message[:200]}")
    # c lawful containment
    mat = verified_matrix(); placements = lawful = unchecked = 0; bad = []; disputed = []
    for parent in [scene] + all_els:
        ptag = "Scene" if parent is scene else local(parent)
        if ptag in STATEMENTS - {"Scene"} or (ptag not in nodes and ptag != "Scene"): continue
        pf = {"children": {"type": "MFNode", "acceptableNodeTypes": "X3DChildNode|X3DMetadataObject|LayerSet"}} if ptag == "Scene" else {f["name"]: f for f in nodes[ptag]["fields"]}
        filled = {}
        for ch in parent:
            ctag = local(ch)
            if not ctag or ctag in STATEMENTS: continue
            placements += 1
            if ctag not in nodes:
                bad.append(f"{ctag} is not an X3D {version} node (inside {ptag})"); continue
            if ch.get("USE"):
                tgt = defs.get(ch.get("USE"))
                if tgt is not None and local(tgt) != ctag:
                    bad.append(f"<{ctag} USE='{ch.get('USE')}'> but DEF '{ch.get('USE')}' is a {local(tgt)} (wrong-type USE, inside {ptag})"); continue
            cf = ch.get("containerField") or nodes[ctag].get("containerField") or "children"
            fi = pf.get(cf)
            if fi is None:
                bad.append(f"{ptag} has no field '{cf}' to hold a {ctag}" + _suggest(pf, anc[ctag])); continue
            if fi.get("type") not in ("SFNode", "MFNode"):
                bad.append(f"{ptag}.{cf} is a {fi.get('type')} value field, not a node field ({ctag})"); continue
            ok = _accepts(fi, anc[ctag])
            if ok is None: unchecked += 1; lawful += 1; continue
            if not ok:
                bad.append(f"{ptag}.{cf} does not accept {ctag} (accepts {fi.get('acceptableNodeTypes')})" + _suggest(pf, anc[ctag])); continue
            if fi.get("type") == "SFNode":
                filled[cf] = filled.get(cf, 0) + 1
                if filled[cf] > 1: bad.append(f"{ptag}.{cf} is SFNode but holds a second node ({ctag})"); continue
            lawful += 1
            mv = mat.get((ctag, ptag, "has" + cf[:1].upper() + cf[1:]))
            if mv == "R": disputed.append(f"{ptag}.{cf} <- {ctag}")
    P["lawful"] = (lawful / placements) * (0.5 if bad else 1.0) if placements else 0.0   # any unlawful placement halves the part
    det.update(placements=placements, unlawful=len(bad), unchecked_fields=unchecked, matrix_rejects=len(disputed))
    for b in bad[:5]: fb.append(f"[lawful] {b}")
    if len(bad) > 5: fb.append(f"[lawful] (+{len(bad) - 5} more unlawful placements)")
    if not placements: fb.append("[lawful] the Scene is empty.")
    if disputed: fb.append(f"[lawful] note: X3DUOM allows but the XSD-verified matrix rejects {len(disputed)} placement(s), e.g. {disputed[0]}")
    # d use-type
    items = []; cnt = {t: tags.count(t) for t in set(tags)}
    cnt["USE"] = sum(1 for e in all_els if e.get("USE")); cnt["DEF"] = sum(1 for e in all_els if e.get("DEF"))
    for k in spec.required:
        ok = cnt.get(k, 0) > 0; items.append(1.0 if ok else 0.0)
        if not ok: fb.append(f"[use_type] the request needs a {k}; the document has none.")
    for k, n in spec.min_counts.items():
        have = cnt.get(k, 0); items.append(min(1.0, have / n) if n else 1.0)
        if have < n: fb.append(f"[use_type] the request needs at least {n} {k}; the document has {have}.")
    for k in spec.forbidden:
        ok = cnt.get(k, 0) == 0; items.append(1.0 if ok else 0.0)
        if not ok: fb.append(f"[use_type] the request rules out {k}; the document uses it {cnt[k]} time(s).")
    wires = _wiring(all_els, defs, spec)
    for ok, msg in wires:
        items.append(1.0 if ok else 0.0)
        if not ok: fb.append(f"[use_type] {msg}")
    P["use_type"] = sum(items) / len(items) if items else 1.0
    det["use_items"] = len(items)
    # e spatial
    if spec.relations or spec.connected:
        ps, skipped = parts(scene, defs); det["parts"] = len(ps); det["parts_unmeasured"] = len(skipped); s_items = []
        for rel in spec.relations:
            ok, msg = relation(rel, ps)
            s_items.append(1.0 if ok else 0.0)
            if not ok: fb.append(f"[spatial] {'cannot judge' if ok is None else 'FAIL'}: {msg}")
        if spec.connected:
            c, msg = connectivity(ps); s_items.append(c)
            if msg: fb.append(f"[spatial] {msg}")
        if skipped: fb.append(f"[spatial] note: {len(skipped)} shape(s) not measured ({', '.join(sorted(set(skipped))[:4])})")
        P["spatial"] = sum(s_items) / len(s_items) if s_items else None
    # f hatches
    prof = root.get("profile"); mp = minimal_profile(tags, version); det.update(profile=prof, minimal_profile=mp)
    allow = set(spec.allow); h = 1.0
    if prof == "Full" and "Full" not in allow: h = 0.0; fb.append(f"[hatches] profile='Full' admits every node and hides what the scene needs; '{mp}' (plus component statements for anything outside it) is enough.")
    elif _profile_rank(prof) is None and prof not in ("CADInterchange", "MedicalInterchange", "MPEG4Interactive"): h = 0.0; fb.append(f"[hatches] the X3D element needs a profile; '{mp}' is enough here.")
    elif _profile_rank(prof) is not None and _profile_rank(prof) > _profile_rank(mp) and prof != spec.profile: h = 0.75; fb.append(f"[hatches] profile '{prof}' is larger than needed; '{mp}' is enough.")
    comps = [(e.get("name"), int((floats(e.get("level")) or [1])[0])) for e in root.iter() if local(e) == "component"]
    allowed = profile_nodes().get(prof) if prof in profile_nodes() else None
    need = {}
    for t in set(tags):
        if t in nodes and allowed is not None and t not in allowed:
            c = nodes[t]["component"]; need[c] = max(need.get(c, 0), nodes[t]["level"] or 1)
    for name, lvl in comps:
        if allowed is None or name in need: continue
        if lvl <= _profile_level(prof, name, version):
            h -= 0.05; fb.append(f"[hatches] <component name='{name}' level='{lvl}'/> repeats what profile '{prof}' already includes.")
        else:
            h -= 0.25; fb.append(f"[hatches] <component name='{name}' level='{lvl}'/> widens the profile but nothing in the scene needs it.")
    for n in HATCH_NODES:
        if cnt.get(n, 0) and n not in allow: h -= 0.25; fb.append(f"[hatches] {n} was not asked for; it moves the scene out of reach of the checks.")
    P["hatches"] = max(0.0, h)
    # scalar
    act = {k: w for k, w in W.items() if P[k] is not None}
    s = sum(P[k] * w for k, w in act.items()) / sum(act.values())
    if not xsd: s *= 0.5
    if not fb: fb.append("All checks pass: valid, lawful, the requested node kinds, relations and a tight profile.")
    return LawfulScore(round(s, 4), {k: (round(v, 4) if v is not None else None) for k, v in P.items()}, "\n".join(fb[:14]), det)


def _suggest(pf, anc_set):
    c = [n for n, f in pf.items() if f.get("type") in ("SFNode", "MFNode") and _accepts(f, anc_set)]
    return f"; use containerField='{c[0]}'" if c else ""


TARGET_KIND = {"OrientationInterpolator": ("SFRotation", ("rotation", "set_rotation", "orientation", "set_orientation")),
               "PositionInterpolator": ("SFVec3f", ("translation", "set_translation", "position", "set_position", "location", "set_location", "center", "set_center", "scale", "set_scale", "size", "set_size")),
               "ColorInterpolator": ("SFColor", ("diffuseColor", "set_diffuseColor", "emissiveColor", "set_emissiveColor", "baseColor", "set_baseColor", "color", "set_color", "specularColor", "set_specularColor", "skyColor", "set_skyColor")),
               "ScalarInterpolator": ("SFFloat", ()), "GeoPositionInterpolator": ("SFVec3d", ())}


def _wiring(els, defs, spec):
    """Each required interpolator must be driven (a ROUTE into set_fraction) and must drive a field of its kind."""
    routes = [e for e in els if local(e) == "ROUTE"]; out = []
    for k in spec.required:
        if k not in TARGET_KIND: continue
        inst = [e.get("DEF") for e in els if local(e) == k and e.get("DEF")]
        if not inst: continue      # absence is already counted as a missing kind; an un-DEFed interpolator cannot be routed
        names, fields = TARGET_KIND[k]
        driven = any(r.get("toNode") in inst and r.get("toField") in ("set_fraction", "fraction") for r in routes)
        drives = [r for r in routes if r.get("fromNode") in inst and r.get("fromField") in ("value_changed", "geovalue_changed")]
        good = not fields or any(r.get("toField") in fields for r in drives)
        out.append((driven, f"{k} is never driven: ROUTE a TimeSensor fraction_changed to its set_fraction."))
        out.append((bool(drives) and good, f"{k} drives nothing" if not drives else f"{k} value_changed goes to {drives[0].get('toNode')}.{drives[0].get('toField')}, not a {names} field such as {fields[0] if fields else '?'}"))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("file"); ap.add_argument("--prompt", default=""); ap.add_argument("--spec", help="JSON TaskSpec"); a = ap.parse_args()
    sp = TaskSpec.from_json(json.loads(a.spec)) if a.spec else spec_from_text(a.prompt)
    r = score(Path(a.file).read_text(encoding="utf-8"), sp)
    print(json.dumps(dict(score=r.score, parts=r.parts, details={k: v for k, v in r.details.items() if k != "xsd_errors"}), indent=1)); print(r.feedback)
