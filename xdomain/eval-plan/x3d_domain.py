"""X3D adapter for the same evaluation, so all three domains run the same arms. Oracle = the fork's validate_xml (XSD) plus semantic_diagnostics errors, the same gate x3d_mcp's tools express.
Imports x3d_mcp read-only from the checkout. Prompts are in the style of the Polys 2024 primitives and objects, plus animation with ROUTEs (not his prompts)."""
import os, sys
from pathlib import Path
SRC = Path(os.path.expanduser("~/Projects/x3d/x3d_mcp/src"))
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))
from validation.validate import validate_xml
from validation.semantic import semantic_diagnostics
from validation.repair import repair_x3d
from lxml import etree
X3D = [
 ("X-A1", "A", "a red box", dict(shapes=1, has=["Box"])), ("X-A2", "A", "a blue sphere and a green cone side by side", dict(shapes=2, has=["Sphere", "Cone"])),
 ("X-A3", "A", "a yellow cylinder resting on top of a gray box", dict(shapes=2, has=["Cylinder", "Box"])), ("X-A4", "A", "three spheres in a row, red, green and blue from left to right", dict(shapes=3, has=["Sphere"])),
 ("X-A5", "A", "a cone pointing down, white", dict(shapes=1, has=["Cone"])), ("X-A6", "A", "a flat purple square floor made from a box, with a small orange sphere above it", dict(shapes=2, has=["Box", "Sphere"])),
 ("X-B1", "B", "a table with a top and four legs", dict(shapes=5, has=["Box"])), ("X-B2", "B", "a snowman made of three spheres with a carrot nose", dict(shapes=4, has=["Sphere", "Cone"])),
 ("X-B3", "B", "a simple house with walls and a roof", dict(shapes=2, has=["Box"])), ("X-B4", "B", "a traffic light with a housing and three lamps", dict(shapes=4, has=["Sphere"])),
 ("X-B5", "B", "a desk lamp with a base, an arm and a shade", dict(shapes=3, has=[])), ("X-B6", "B", "a simple tree with a trunk and a crown", dict(shapes=2, has=["Cylinder"])),
 ("X-B7", "B", "a pawn made of a base, a stem and a head", dict(shapes=3, has=["Sphere"])),
 ("X-C1", "C", "a box that rotates forever, using a TimeSensor, an OrientationInterpolator and ROUTEs", dict(shapes=1, has=["TimeSensor", "OrientationInterpolator", "ROUTE"])),
 ("X-C2", "C", "a sphere that moves around a square path, with a PositionInterpolator", dict(shapes=1, has=["TimeSensor", "PositionInterpolator", "ROUTE"])),
 ("X-C3", "C", "a box that turns red when clicked, using a TouchSensor", dict(shapes=1, has=["TouchSensor", "ROUTE"])),
 ("X-C4", "C", "a spotlight that sweeps left and right", dict(shapes=0, has=["SpotLight", "TimeSensor", "ROUTE"])),
 ("X-C5", "C", "a ball that bounces up and down", dict(shapes=1, has=["Sphere", "PositionInterpolator", "ROUTE"])),
 ("X-C6", "C", "a clock hand that rotates once per minute", dict(shapes=1, has=["TimeSensor", "OrientationInterpolator", "ROUTE"])),
 ("X-C7", "C", "a cube that scales up while the pointer is over it, using a TouchSensor isOver", dict(shapes=1, has=["TouchSensor", "ROUTE"])),
]
EX = ['''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interchange" version="4.0"><Scene>
  <Shape><Appearance><Material diffuseColor="1 0 0"/></Appearance><Box size="1 1 1"/></Shape>
</Scene></X3D>''', '''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Interactive" version="4.0"><Scene>
  <Transform DEF="Spinner"><Shape><Appearance><Material diffuseColor="0 0.4 1"/></Appearance><Box/></Shape></Transform>
  <TimeSensor DEF="Clock" cycleInterval="4" loop="true"/>
  <OrientationInterpolator DEF="Spin" key="0 0.5 1" keyValue="0 1 0 0 0 1 0 3.14159 0 1 0 6.28318"/>
  <ROUTE fromNode="Clock" fromField="fraction_changed" toNode="Spin" toField="set_fraction"/>
  <ROUTE fromNode="Spin" fromField="value_changed" toNode="Spinner" toField="set_rotation"/>
</Scene></X3D>''']
def check(xml):
    """-> dict(valid, errors, warnings, diags[list of dict])"""
    v = validate_xml(xml); diags = [dict(rule="XSD", severity="error", where=e.split(":")[0], message=e, fix="") for e in v.get("errors", [])]
    if v["valid"] or not diags:
        try:
            for d in semantic_diagnostics(xml):
                diags.append(dict(rule=d.check, severity="error" if d.level == "error" else ("warning" if d.level == "warning" else "info"), where=d.node_tag or "", message=d.message, fix=""))
        except Exception as e: diags.append(dict(rule="SEMANTIC", severity="error", where="", message=str(e)[:200], fix=""))
    errs = sum(d["severity"] == "error" for d in diags)
    return dict(valid=errs == 0 and v["valid"], errors=errs, warnings=sum(d["severity"] == "warning" for d in diags), diags=[d for d in diags if d["severity"] != "info"])
def repair(xml):
    r = repair_x3d(xml)
    if r.get("error") or not r.get("fixed"): return xml, []
    return r["fixed"], [("x3d", c.get("kind", ""), c.get("reason", c.get("change", "")) if isinstance(c, dict) else str(c)) for c in r.get("changes", [])]
def complete(xml, expect):
    try: root = etree.fromstring(xml.encode())
    except Exception: return False
    tags = [etree.QName(e).localname for e in root.iter() if isinstance(e.tag, str)]
    return tags.count("Shape") >= expect.get("shapes", 0) and all(h in tags for h in expect.get("has", []))
if __name__ == "__main__":
    for i, e in enumerate(EX): r = check(e); print("example", i, r["valid"], r["errors"], r["warnings"], [d["message"][:90] for d in r["diags"]][:3])
