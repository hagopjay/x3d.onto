"""Fault injection for URDF: each operator returns a mutated document or None if not applicable. level = first level that should catch it (L0 parse, L1 structure, L2 semantics)."""
import re
def sub1(pat, rep, x, flags=0):
    y, n = re.subn(pat, rep, x, count=1, flags=flags); return y if n else None
def first_joint(x, typ=None):
    m = re.search(r'<joint name="([^"]+)" type="%s"' % (typ or "[a-z]+"), x); return m.group(1) if m else None
F = {}
def fault(i, level, desc):
    def d(fn): F[i] = (level, desc, fn); return fn
    return d
@fault("F01", "L0", "closing tag removed")
def _(x): return x.replace("</robot>", "", 1)
@fault("F02", "L1", "root renamed")
def _(x): return x.replace("<robot ", "<robots ", 1).replace("</robot>", "</robots>")
@fault("F03", "L1", "robot name removed")
def _(x): return sub1(r'<robot name="[^"]*"', "<robot", x)
@fault("F04", "L1", "invalid joint type")
def _(x): return sub1(r'type="revolute"', 'type="revolve"', x) or sub1(r'type="continuous"', 'type="spin"', x)
@fault("F05", "L1", "joint without child")
def _(x): return sub1(r'<child link="[^"]*"/>', "", x)
@fault("F06", "L1", "origin xyz with two numbers")
def _(x): return sub1(r'(<joint [^>]*>.*?<origin xyz=")[^"]+(")', r'\g<1>0 0\2', x, re.S)
@fault("F07", "L1", "duplicate link name")
def _(x):
    names = re.findall(r'<link name="([^"]+)"', x); return x.replace(f'<link name="{names[1]}"', f'<link name="{names[0]}"', 1) if len(names) > 1 else None
@fault("F08", "L2", "joint parent undefined")
def _(x): return sub1(r'(<joint [^>]*><parent link=")[^"]+', r"\1ghost_link", x)
@fault("F09", "L2", "link has two parent joints")
def _(x):
    js = re.findall(r'<joint name="([^"]+)"[^>]*><parent link="([^"]+)"/><child link="([^"]+)"', x)
    if len(js) < 2: return None
    return x.replace(f'<joint name="{js[1][0]}" type', f'<joint name="{js[1][0]}x" type', 1).replace(f'<child link="{js[1][2]}"/>', f'<child link="{js[0][2]}"/>', 1)
@fault("F10", "L2", "link detached (joint removed)")
def _(x):
    ms = list(re.finditer(r'  <joint .*?</joint>\n', x, re.S)); return x[:ms[-1].start()] + x[ms[-1].end():] if len(ms) > 1 else None
@fault("F11", "L2", "cycle: leaf becomes parent of the root")
def _(x):
    js = re.findall(r'<joint name="[^"]+"[^>]*><parent link="([^"]+)"/><child link="([^"]+)"', x)
    if not js: return None
    root = js[0][0]; leaf = js[-1][1]
    return x.replace("</robot>", f'  <joint name="loop" type="fixed"><parent link="{leaf}"/><child link="{root}"/></joint>\n</robot>')
@fault("F12", "L2", "revolute joint without limit")
def _(x): return sub1(r'(<joint [^>]*type="revolute".*?)<limit [^>]*/>', r"\1", x, re.S)
@fault("F13", "L2", "limit lower above upper")
def _(x): return sub1(r'lower="([^"]+)" upper="([^"]+)"', lambda m: f'lower="{abs(float(m.group(2))) + 1}" upper="{m.group(2)}"', x) if "lower=" in x else None
@fault("F14", "L2", "axis is the zero vector")
def _(x): return sub1(r'<axis xyz="[^"]+"/>', '<axis xyz="0 0 0"/>', x)
@fault("F15", "L2", "mass zero on a dynamic link")
def _(x): return sub1(r'<mass value="[^"]+"/>', '<mass value="0"/>', x)
@fault("F16", "L2", "negative mass")
def _(x): return sub1(r'<mass value="[^"]+"/>', '<mass value="-1"/>', x)
@fault("F17", "L2", "inertia not positive definite")
def _(x): return sub1(r'ixx="[^"]+"', 'ixx="-0.01"', x)
@fault("F18", "L2", "inertia breaks the triangle inequality")
def _(x): return sub1(r'ixx="[^"]+"( ixy="0" ixz="0" iyy=")([^"]+)(" iyz="0" izz=")([^"]+)"', lambda m: f'ixx="{(float(m.group(2)) + float(m.group(4))) * 3:.6f}"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}"', x)
@fault("F19", "L2", "negative cylinder radius")
def _(x): return sub1(r'<cylinder radius="[^"]+"', '<cylinder radius="-0.05"', x)
@fault("F20", "L2", "colour out of range")
def _(x): return sub1(r'rgba="[^"]+"', 'rgba="2 0 0 1"', x)
@fault("F21", "L2", "mimic joint undefined")
def _(x):
    j = first_joint(x, "revolute") or first_joint(x, "prismatic"); return sub1(rf'(<joint name="{j}" .*?<origin [^>]*/>)', r'\1<mimic joint="ghost_joint"/>', x, re.S) if j else None
@fault("F22", "L2", "negative velocity limit")
def _(x): return sub1(r'velocity="[^"]+"', 'velocity="-2"', x)
@fault("F23", "W", "axis not unit length (warning only)")
def _(x): return sub1(r'<axis xyz="[^"]+"/>', '<axis xyz="0 0 2"/>', x)
@fault("F24", "C", "child attached 1 m away from the parent (valid but floating)")
def _(x):
    m = re.search(r'(<joint name="[^"]+" type="[a-z]+"><parent link="[^"]+"/><child link="[^"]+"/><origin xyz=")([^"]+)(")', x)
    if not m: return None
    v = [float(t) for t in m.group(2).split()]; v[0] += 1.0
    return x[:m.start(2)] + " ".join(f"{t:g}" for t in v) + x[m.end(2):]
