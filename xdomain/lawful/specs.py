"""Task specs for the corpora the metric is validated on. The node-kind constraints come from the prompt files as written;
the spatial relations and the "connected" flags are MY reading of the prompts (grade L), added here, not in the source files.
  live_specs()  the 50 prompts of the x3d.ml live run of 2026-10-17 (data/prompts_live.jsonl, copied from
                x3d.ml demo/live/prompts_live.jsonl at 6eb8169, sha256 bb0d09fb...)
  eval_specs()  the 20 X3D prompts of xdomain/eval-plan/x3d_domain.py (copied here so importing needs no fork path)"""
import json
from pathlib import Path
from metric import TaskSpec

HERE = Path(__file__).resolve().parent
LIVE_KEYS = {"min_use": "USE", "min_defs": "DEF", "min_routes": "ROUTE", "min_transforms": "Transform", "min_joints": "HAnimJoint",
             "min_humanoids": "HAnimHumanoid", "min_geolocations": "GeoLocation"}
# my reading of which live prompts name a spatial relation or an assembly whose parts should touch (L)
LIVE_SPATIAL = {
    "obj-01": dict(relations=[["on_top", "Sphere", "ground"]]),
    "obj-02": dict(relations=[["on_top", "Box", "Cylinder"]], connected=True),
    "obj-03": dict(relations=[["on_top", "Cone", "Box"]], connected=True),
    "asm-01": dict(relations=[["on_top", "IndexedFaceSet", "Box"]], connected=True),
    "asm-04": dict(connected=True), "asm-05": dict(connected=True),
    "sp-01": dict(connected=True), "sp-03": dict(connected=True), "sp-04": dict(connected=True), "sp-05": dict(connected=True),
    "sp-06": dict(connected=True), "sp-08": dict(connected=True), "sp-09": dict(connected=True),
    "sp-12": dict(relations=[["on_top", "Cylinder", "ground"]], connected=True), "sp-14": dict(connected=True),
    "sp-15": dict(connected=True), "sp-16": dict(connected=True), "sp-17": dict(connected=True), "sp-20": dict(connected=True),
}
EVAL_X3D = [
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
EVAL_SPATIAL = {
    "X-A2": dict(relations=[["side_by_side", "Sphere", "Cone"]]), "X-A3": dict(relations=[["on_top", "Cylinder", "Box"]]),
    "X-A4": dict(relations=[["row_x", "Sphere", 3]]), "X-A5": dict(relations=[["points_down", "Cone", None]]),
    "X-A6": dict(relations=[["above", "Sphere", "Box"]]),
    **{k: dict(connected=True) for k in ("X-B1", "X-B2", "X-B3", "X-B4", "X-B5", "X-B6", "X-B7")},
}


def live_specs():
    out = {}
    for line in (HERE / "data" / "prompts_live.jsonl").read_text().splitlines():
        if not line.strip(): continue
        p = json.loads(line); c = p.get("constraints", {})
        mc = {LIVE_KEYS[k]: v for k, v in c.items() if k in LIVE_KEYS}
        out[p["prompt_id"]] = TaskSpec(prompt=p["prompt"], required=list(c.get("required_nodes", [])), min_counts=mc, pid=p["prompt_id"], profile="Immersive",   # the run's system prompt orders Immersive
                                       **LIVE_SPATIAL.get(p["prompt_id"], {}))
    return out


def eval_specs():
    out = {}
    for pid, tier, desc, ex in EVAL_X3D:
        mc = {"Shape": ex["shapes"]} if ex.get("shapes") else {}
        out[pid] = TaskSpec(prompt=desc, required=list(ex.get("has", [])), min_counts=mc, pid=pid, **EVAL_SPATIAL.get(pid, {}))
    return out
