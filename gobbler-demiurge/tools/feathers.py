"""Read the Blender-made feathers (assets/feathers/feather_*.x3d, written by tools/blender_feather.py) into plain Python data.

Each feather is in its own unit frame: the quill runs along +X to 1.0, the vane's width is along Y, its face normal is +Z.
Geometry is read as exported (mesh-local points); the object Transform that the exporter wrote for the Z-up to Y-up change is not used.
"""
import os, re, json
import xml.etree.ElementTree as ET

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'feathers')
PARTS = ('near_vane', 'near_quill', 'near_barbs', 'outline', 'spine')


def _floats(s): return [float(x) for x in s.split()]


def load(variant, assets=ASSETS):
    """-> {part: dict(kind='faces'|'lines', index=[...], points=[(x,y,z)], colors=[(r,g,b)] or None)}"""
    root = ET.parse(os.path.join(assets, 'feather_%s.x3d' % variant)).getroot()
    out = {}
    for node in root.iter():
        tag = node.tag
        if tag not in ('IndexedFaceSet', 'IndexedLineSet'): continue
        m = re.match(r'ME_F%s_(\w+)$' % variant, node.get('DEF', ''))
        if not m: continue
        coord = node.find('Coordinate'); P = _floats(coord.get('point'))
        pts = [tuple(P[i:i + 3]) for i in range(0, len(P), 3)]
        col = node.find('ColorRGBA')
        cols = None
        if col is not None:
            C = _floats(col.get('color')); cols = [tuple(C[i:i + 3]) for i in range(0, len(C), 4)]
        out[m.group(1)] = dict(kind='faces' if tag == 'IndexedFaceSet' else 'lines', index=[int(i) for i in node.get('coordIndex').split()], points=pts, colors=cols)
    missing = [p for p in PARTS if p not in out]
    if missing: raise ValueError('feather %s lacks %s' % (variant, missing))
    return out


def variants(assets=ASSETS):
    return sorted(f[8] for f in os.listdir(assets) if re.match(r'feather_\w\.x3d$', f))


def receipt(assets=ASSETS):
    return json.load(open(os.path.join(assets, 'receipt.json')))


def tip(variant, assets=ASSETS):
    return load(variant, assets)['spine']['points'][-1]
