"""Deterministic URDF repairs that change one thing and invent nothing. Anything needing a design decision (a missing limit, a mass) is left to the model or a person."""
import re, math
from lxml import etree
def repair(xml: str):
    """returns (fixed_xml, [applied]); applied entries name the rule and the element."""
    try: root = etree.fromstring(xml.encode())
    except etree.XMLSyntaxError: return xml, []
    done = []
    for j in root.findall("joint"):
        ax = j.find("axis")
        if ax is not None:
            try: v = [float(t) for t in ax.get("xyz").split()]
            except Exception: v = None
            if v and len(v) == 3:
                n = math.sqrt(sum(a * a for a in v))
                if 1e-9 < n and abs(n - 1) > 1e-3: ax.set("xyz", " ".join(f"{a / n:.6g}" for a in v)); done.append(("U-08", j.get("name"), "normalised axis"))
        lim = j.find("limit")
        if lim is not None:
            try:
                lo, hi = float(lim.get("lower", 0)), float(lim.get("upper", 0))
                if lo > hi: lim.set("lower", str(hi)); lim.set("upper", str(lo)); done.append(("U-09", j.get("name"), "swapped lower and upper"))
                v = float(lim.get("velocity", 1))
                if v < 0: lim.set("velocity", str(-v)); done.append(("U-09", j.get("name"), "velocity sign"))
            except Exception: pass
    for c in root.iter("color"):
        try:
            v = [float(t) for t in c.get("rgba").split()]
            if len(v) == 4 and any(a < 0 or a > 1 for a in v): c.set("rgba", " ".join(str(min(1, max(0, a))) for a in v)); done.append(("U-15", "color", "clamped to [0,1]"))
        except Exception: pass
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode(), done
