"""URDF checker: the robotics sibling of x3d_mcp's validate / validate_semantic. Oracle = this module's rules (grade L: written from the URDF
specification and ROS conventions as I know them; NOT validated against urdfdom, MuJoCo or any independent oracle).
Levels mirror X3D: L0 well-formed XML, L1 structural (required elements, enums, numbers) ~ the XSD's job, L2 semantic (tree, inertia, limits) ~ validate_semantic.
Each semantic rule names its X3D RigidBodyPhysics counterpart where one exists."""
import math, re, time
from lxml import etree
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from kit import Diag, Report

JOINT_TYPES = {"revolute", "continuous", "prismatic", "fixed", "floating", "planar"}
def floats(s, n=None):
    try: v = [float(x) for x in re.split(r"[\s,]+", (s or "").strip()) if x != ""]
    except ValueError: return None
    return v if n is None or len(v) == n else None

def check(xml: str, level: int = 2) -> Report:
    t0 = time.perf_counter(); R = Report("urdf", "urdf_check.py rules (L)")
    add = lambda *a, **k: R.diags.append(Diag(*a, **k))
    try: root = etree.fromstring(xml.encode(), parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as e:
        add("U-00", "error", 0, f"line {e.lineno}", f"not well-formed XML: {e.msg}", "fix the XML syntax"); R.ms = (time.perf_counter() - t0) * 1000; return R
    line = lambda el: f"line {el.sourceline}"
    if root.tag != "robot": add("U-01", "error", 2, line(root), f"root element is <{root.tag}>, expected <robot>", "wrap the model in <robot name='...'>")
    if not root.get("name"): add("U-01", "error", 2, line(root), "<robot> has no name attribute", "add name='...'")
    links = {}; joints = {}
    for l in root.findall("link"):
        n = l.get("name")
        if not n: add("U-02", "error", 2, line(l), "<link> without a name", "add name"); continue
        if n in links: add("U-02", "error", 2, line(l), f"duplicate link name '{n}'", "rename one link")
        links[n] = l
    for j in root.findall("joint"):
        n = j.get("name")
        if not n: add("U-02", "error", 2, line(j), "<joint> without a name", "add name"); continue
        if n in joints: add("U-02", "error", 2, line(j), f"duplicate joint name '{n}'", "rename one joint")
        joints[n] = j
    # L1 structural: enums, required children, numbers
    for n, j in joints.items():
        t = j.get("type")
        if t not in JOINT_TYPES: add("U-03", "error", 2, line(j), f"joint '{n}' has type '{t}'; allowed: {', '.join(sorted(JOINT_TYPES))}", "use a valid joint type")
        for tag in ("parent", "child"):
            e = j.find(tag)
            if e is None or not e.get("link"): add("U-04", "error", 2, line(j), f"joint '{n}' has no <{tag} link='...'>", f"add <{tag} link='LINK'/>")
        for o in j.findall("origin"):
            for a, k in (("xyz", 3), ("rpy", 3)):
                if o.get(a) is not None and floats(o.get(a), k) is None: add("U-05", "error", 1, line(o), f"joint '{n}' origin {a}='{o.get(a)}' is not {k} numbers", f"write {k} numbers")
    for n, l in links.items():
        for g in l.iter("box", "cylinder", "sphere", "mesh"):
            pass
    if level < 2:
        R.ms = (time.perf_counter() - t0) * 1000; return R
    # L2 semantic
    parent_of = {}; children = {}
    for n, j in joints.items():
        p = (j.find("parent").get("link") if j.find("parent") is not None else None); c = (j.find("child").get("link") if j.find("child") is not None else None)
        for tag, ln in (("parent", p), ("child", c)):
            if ln and ln not in links: add("U-06", "error", 3, line(j), f"joint '{n}' {tag} refers to undefined link '{ln}'", "define the link or fix the name", "X3D joint refers to a node that is not a RigidBody")
        if c:
            if c in parent_of: add("U-07", "error", 3, line(j), f"link '{c}' is the child of two joints ('{parent_of[c]}' and '{n}'); a URDF is a tree", "remove one joint", "X3D body in two collections")
            parent_of.setdefault(c, n)
        if p and c: children.setdefault(p, []).append(c)
        t = j.get("type"); ax = j.find("axis")
        if t in ("revolute", "continuous", "prismatic", "planar"):
            if ax is not None and floats(ax.get("xyz"), 3) is not None:
                v = floats(ax.get("xyz"), 3); nrm = math.sqrt(sum(x * x for x in v))
                if nrm < 1e-9: add("U-08", "error", 3, line(ax), f"joint '{n}' axis is the zero vector", "give a unit axis such as 0 0 1")
                elif abs(nrm - 1) > 1e-3: add("U-08", "warning", 3, line(ax), f"joint '{n}' axis {v} is not unit length ({nrm:.3f})", "normalise the axis")
            elif ax is not None: add("U-05", "error", 1, line(ax), f"joint '{n}' axis xyz is not 3 numbers", "write 3 numbers")
        if t in ("revolute", "prismatic"):
            lim = j.find("limit")
            if lim is None: add("U-09", "error", 3, line(j), f"{t} joint '{n}' has no <limit>", "add <limit lower upper effort velocity/>")
            else:
                lo, hi = floats(lim.get("lower", "0")), floats(lim.get("upper", "0"))
                if lim.get("effort") is None or lim.get("velocity") is None: add("U-09", "error", 3, line(lim), f"joint '{n}' limit needs effort and velocity", "add effort and velocity")
                if lo and hi and lo[0] > hi[0]: add("U-09", "error", 3, line(lim), f"joint '{n}' lower {lo[0]} is above upper {hi[0]}", "swap or fix the bounds", "X3D min>max limits (deferred in the fork)")
                v = floats(lim.get("velocity", "1"))
                if v and v[0] <= 0: add("U-09", "error", 3, line(lim), f"joint '{n}' velocity limit {v[0]} is not positive", "use a positive limit")
        m = j.find("mimic")
        if m is not None and m.get("joint") not in joints: add("U-10", "error", 3, line(m), f"joint '{n}' mimics undefined joint '{m.get('joint')}'", "fix the joint name")
    roots = [n for n in links if n not in parent_of]
    if links and len(roots) != 1: add("U-11", "error", 3, "tree", f"{len(roots)} root links ({', '.join(roots[:4])}); a URDF needs exactly one", "connect the pieces with joints", "X3D body outside any RigidBodyCollection")
    seen = set(); stack = list(roots)
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); stack.extend(children.get(x, []))
    for n in links:
        if n not in seen and roots and n not in roots: add("U-11", "error", 3, line(links[n]), f"link '{n}' is not reachable from the root (cycle or detached)", "attach it to the tree")
    for n, l in links.items():
        inn = l.find("inertial")
        is_root = n in roots
        if inn is None:
            if not is_root: add("U-12", "warning", 4, line(l), f"link '{n}' has no <inertial>; simulators treat it as massless", "add mass and inertia", "X3D RigidBody mass")
            continue
        ms = inn.find("mass"); mass = floats(ms.get("value"), 1) if ms is not None else None
        if mass is None: add("U-12", "error", 4, line(inn), f"link '{n}' inertial has no valid mass", "add <mass value='...'/>")
        elif mass[0] <= 0: add("U-12", "error", 4, line(inn), f"link '{n}' mass is {mass[0]}; a dynamic link needs mass above zero", "set a positive mass", "X3D physics-mass (X-09): mass 0 only if fixed")
        ie = inn.find("inertia")
        if ie is None: add("U-13", "error", 4, line(inn), f"link '{n}' inertial has no <inertia>", "add the six inertia terms")
        else:
            try:
                ixx, iyy, izz, ixy, ixz, iyz = (float(ie.get(k, 0)) for k in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz"))
                if ixx <= 0 or iyy <= 0 or izz <= 0: add("U-13", "error", 4, line(ie), f"link '{n}' has a non-positive principal moment", "moments must be positive")
                else:
                    d = ixx * (iyy * izz - iyz * iyz) - ixy * (ixy * izz - iyz * ixz) + ixz * (ixy * iyz - iyy * ixz)
                    if d <= 0 or ixx * iyy - ixy * ixy <= 0: add("U-13", "error", 4, line(ie), f"link '{n}' inertia matrix is not positive definite", "recompute the inertia from the shape")
                    elif ixx + iyy < izz or ixx + izz < iyy or iyy + izz < ixx: add("U-13", "error", 4, line(ie), f"link '{n}' inertia breaks the triangle inequality (ixx+iyy>=izz etc.)", "recompute the inertia; no rigid body has these moments")
            except ValueError: add("U-13", "error", 1, line(ie), f"link '{n}' inertia has a non-numeric term", "write numbers")
        o = inn.find("origin")
        if o is not None and o.get("xyz") is not None and floats(o.get("xyz"), 3) is None: add("U-05", "error", 1, line(o), "inertial origin xyz is not 3 numbers", "write 3 numbers")
    for n, l in links.items():
        for g in l.iter("box", "cylinder", "sphere"):
            vals = {"box": ("size", 3), "cylinder": ("radius", 1), "sphere": ("radius", 1)}[g.tag]
            if g.tag == "cylinder":
                r, ln = floats(g.get("radius"), 1), floats(g.get("length"), 1)
                if not r or not ln or r[0] <= 0 or ln[0] <= 0: add("U-14", "error", 3, line(g), f"link '{n}' cylinder radius/length must be positive numbers", "use positive dimensions")
            else:
                v = floats(g.get(vals[0]), vals[1])
                if not v or any(x <= 0 for x in v): add("U-14", "error", 3, line(g), f"link '{n}' {g.tag} {vals[0]} must be {vals[1]} positive number(s)", "use positive dimensions")
        for c in l.iter("color"):
            v = floats(c.get("rgba"), 4)
            if v is None or any(x < 0 or x > 1 for x in v): add("U-15", "error", 3, line(c), f"link '{n}' color rgba must be 4 numbers in [0,1]", "scale to 0..1")
    # rung 6, "complete": is the child attached where the parent actually is? (the parts-and-contact idea from the X3D thread, one axis-aligned cylinder per link)
    ext = {}
    for n, l in links.items():
        c = l.find("collision/geometry/cylinder")
        if c is None: c = l.find("visual/geometry/cylinder")
        if c is not None:
            r, h = floats(c.get("radius"), 1), floats(c.get("length"), 1)
            o = l.find("visual/origin"); z0 = (floats(o.get("xyz"), 3) or [0, 0, 0])[2] if o is not None and o.get("xyz") else 0.0
            if r and h and r[0] > 0 and h[0] > 0: ext[n] = (r[0], z0 - h[0] / 2, z0 + h[0] / 2)
    for n, j in joints.items():
        p = j.find("parent").get("link") if j.find("parent") is not None else None; o = j.find("origin")
        if p in ext and o is not None and floats(o.get("xyz"), 3):
            x, y, z = floats(o.get("xyz"), 3); r, lo, hi = ext[p]; tol = 0.05 * max(r, hi - lo)
            if math.hypot(x, y) > r + tol or z < lo - tol or z > hi + tol:
                add("U-16", "warning", 6, line(o), f"joint '{n}' attaches {j.find('child').get('link')} at ({x:g}, {y:g}, {z:g}), outside parent '{p}' geometry (radius {r:g}, z {lo:g} to {hi:g}): the part floats", "move the joint origin onto the parent", "parts-and-contact: floating part (step 4)")
    R.ms = (time.perf_counter() - t0) * 1000; return R

RULES = [("U-00", 0, "XML well-formed", ""), ("U-01", 2, "root <robot name>", ""), ("U-02", 2, "unique, present names", ""), ("U-03", 2, "joint type enum", ""), ("U-04", 2, "joint parent/child present", ""),
         ("U-05", 1, "numeric attributes parse", ""), ("U-06", 3, "joint links defined", "joint refers to a non-RigidBody"), ("U-07", 3, "one parent per link (tree)", "body in two collections"),
         ("U-08", 3, "axis non-zero, unit", ""), ("U-09", 3, "limits present, ordered, positive velocity", "min>max limits (deferred)"), ("U-10", 3, "mimic target exists", ""),
         ("U-11", 3, "exactly one root, all reachable", "body outside any collection"), ("U-12", 4, "mass positive (dynamic links)", "X-09 physics-mass"), ("U-13", 4, "inertia positive definite, triangle inequality", "inertia rules (deferred)"),
         ("U-14", 3, "geometry dimensions positive", ""), ("U-15", 3, "colour in [0,1]", ""), ("U-16", 6, "joint attached on the parent geometry (contact)", "parts-and-contact: floating part")]
