"""Read the Blender-made shell tender (assets/tender/tender.x3d, written by tools/blender_tender.py) and hand out copies of its HAnimHumanoid as X3D text.

The humanoid is kept as the blenderizer wrote it: 18 HAnimJoints, skinCoord, one skin Shape. Per copy only three things change: every DEF gets a copy prefix
(hanim_Tender -> hanim_T<n>, so a scene can hold several), the PhysicalMaterial becomes a plain Appearance (the faces carry baked colours, drawn unlit like the feathers),
and long floats are shortened. The figure is 1 unit tall, stands on Y after the exporter's own Z-up to Y-up Transform, and faces +Z.
"""
import os, re
import xml.etree.ElementTree as ET

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'tender', 'tender.x3d')
VILLAGERS = {k: os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'villager', 'villager_%s.x3d' % k) for k in 'abc'}      # the same rig dressed as villagers (tools/blender_tender.py --look)
JOINTS = ('humanoid_root', 'sacroiliac', 'vl5', 'vt6', 'vc4', 'skullbase', 'l_shoulder', 'l_elbow', 'l_wrist', 'r_shoulder', 'r_elbow', 'r_wrist',
          'l_hip', 'l_knee', 'l_ankle', 'r_hip', 'r_knee', 'r_ankle')
_SHORT = ('point', 'color', 'center', 'translation', 'rotation', 'scale', 'skinCoordWeight')      # numeric attributes worth shortening (index lists stay exact)
_cache = {}


def _num(t):
    x = float(t)
    s = ('%.4f' % x).rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def _tree(asset=None):
    asset = asset or ASSET
    if asset not in _cache: _cache[asset] = ET.parse(asset).getroot()
    return _cache[asset]


def joints():
    """the joint names as exported, parents before children"""
    return [j.get('name') for j in _tree().iter('HAnimJoint') if j.get('DEF')]


def joint_centers():
    return {j.get('name'): tuple(float(x) for x in j.get('center').split()) for j in _tree().iter('HAnimJoint') if j.get('DEF')}


def humanoid(n, asset=None):
    """-> X3D text of copy n: the exporter's Z-up to Y-up Transform around one HAnimHumanoid; joint DEFs are hanim_T<n>_<joint>. `asset` picks a villager file instead of the tender"""
    root = ET.fromstring(ET.tostring(_tree(asset)))                                        # a fresh copy to edit
    tr = next(c for c in root.find('Scene') if c.tag == 'Transform')
    del tr.attrib['DEF']
    for e in tr.iter():
        for k in ('DEF', 'USE'):
            v = e.get(k)
            if v: e.set(k, v.replace('hanim_Tender', 'hanim_T%d' % n).replace('ME_TenderSkin_skin', 'ME_T%d_skin' % n))
        for k in _SHORT:
            v = e.get(k)
            if v is not None: e.set(k, ' '.join(_num(t) for t in v.split()))
        if e.tag == 'Appearance':
            for c in list(e): e.remove(c)                                             # PhysicalMaterial out: faces are unlit and carry their own colour
    if 'DEF' in tr.attrib: del tr.attrib['DEF']
    return ET.tostring(tr, encoding='unicode')
