"""Read the Blender-made world (assets/earth/earth.x3d and assets/village/village.x3d, written by tools/blender_earth.py and tools/blender_village.py) and write the files the
page loads lazily as Inlines: data/bird/earth-planet.x3d, earth-clouds.x3d, earth-moon.x3d and village.x3d.

Per file the exporter's own nodes are kept as they came out (the Z-up to Y-up Transform around each object, the IndexedFaceSet with its ColorRGBA, the DEF/USE sharing of the
linked-duplicate buildings and trees). Three things change: the PhysicalMaterial in every Appearance goes (the faces carry their baked colour and are drawn unlit, like the
feathers and the tenders), long numbers are shortened to four decimals, and the head and the NavigationInfo go (an Inline's bindables are ignored anyway). Earth, Clouds and
Moon are written as three files because the page animates them separately (the clouds turn, the Moon orbits).
"""
import os, re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__)); ASSETS = os.path.join(HERE, '..', 'assets')
_SHORT = ('point', 'color', 'center', 'translation', 'rotation', 'scale')


def _num(t):
    x = float(t)
    s = ('%.4f' % x).rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def _clean(e):
    for k in _SHORT:
        v = e.get(k)
        if v is not None: e.set(k, ' '.join(_num(t) for t in v.split()))
    if e.tag == 'Appearance':
        for c in list(e): e.remove(c)
    for c in e: _clean(c)


def document(children):
    body = ''.join(ET.tostring(c, encoding='unicode') for c in children)
    return ("<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='4.0'>\n  <head><component name='Shape' level='2'/></head>\n  <Scene>\n    " + body + "\n  </Scene>\n</X3D>\n")


def split(path, only=None):
    """-> {DEF of the top-level Transform: X3D document text}"""
    sc = ET.parse(path).getroot().find('Scene'); out = {}
    for c in sc:
        if c.tag == 'NavigationInfo' or (only and c.get('DEF') not in only): continue
        _clean(c); out[c.get('DEF')] = c
    return out


def earth_files():
    objs = split(os.path.join(ASSETS, 'earth', 'earth.x3d'))
    return {'earth-planet.x3d': document([objs['OB_Earth']]), 'earth-clouds.x3d': document([objs['OB_Clouds']]), 'earth-moon.x3d': document([objs['OB_Moon']])}


def village_file():
    sc = ET.parse(os.path.join(ASSETS, 'village', 'village.x3d')).getroot().find('Scene'); kids = []
    for c in sc:
        if c.tag == 'NavigationInfo': continue
        _clean(c); kids.append(c)
    return {'village.x3d': document(kids)}


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True); files = {}
    files.update(earth_files()); files.update(village_file())
    for name, text in files.items():
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as fh: fh.write(text)
    return {k: len(v.encode('utf-8')) for k, v in files.items()}


if __name__ == '__main__':
    import sys
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'data', 'bird')))
