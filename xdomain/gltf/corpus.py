"""glTF 2.0 base models built in pure Python (embedded base64 buffers). Deterministic; stdlib only."""
import base64, json, math, struct
def b64(data): return "data:application/octet-stream;base64," + base64.b64encode(data).decode()
class B:
    """tiny buffer builder: returns accessor indexes"""
    def __init__(s): s.data = bytearray(); s.views = []; s.acc = []
    def add(s, fmt, rows, typ, comp, target=None, minmax=False, stride=None):
        while len(s.data) % 4: s.data.append(0)
        off = len(s.data); flat = [v for r in rows for v in (r if isinstance(r, (tuple, list)) else (r,))]
        raw = struct.pack("<%d%s" % (len(flat), fmt), *flat); s.data += raw
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(raw)}
        if target: bv["target"] = target
        s.views.append(bv); a = {"bufferView": len(s.views) - 1, "componentType": comp, "count": len(rows), "type": typ}
        if minmax:
            n = len(rows[0]); a["min"] = [min(r[i] for r in rows) for i in range(n)]; a["max"] = [max(r[i] for r in rows) for i in range(n)]
        s.acc.append(a); return len(s.acc) - 1
def finish(b, d):
    while len(b.data) % 4: b.data.append(0)
    d.update(bufferViews=b.views, accessors=b.acc, buffers=[{"byteLength": len(b.data), "uri": b64(bytes(b.data))}]); return d
def cube_arrays():
    f = [((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]), ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
         ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]), ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
         ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]), ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)])]
    P, N, I = [], [], []
    for n, vs in f:
        k = len(P); P += [tuple(x * .5 for x in v) for v in vs]; N += [n] * 4; I += [k, k + 1, k + 2, k, k + 2, k + 3]
    return P, N, I
def mesh_prim(b, material=None, uv=False):
    P, N, I = cube_arrays(); a = {"POSITION": b.add("f", P, "VEC3", 5126, 34962, True), "NORMAL": b.add("f", N, "VEC3", 5126, 34962)}
    if uv: a["TEXCOORD_0"] = b.add("f", [((i % 2), (i // 2) % 2) for i in range(len(P))], "VEC2", 5126, 34962)
    p = {"attributes": a, "indices": b.add("H", I, "SCALAR", 5123, 34963), "mode": 4}
    if material is not None: p["material"] = material
    return p
def asset(): return {"version": "2.0", "generator": "xdomain corpus"}
def tri():
    b = B(); P = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    p = {"attributes": {"POSITION": b.add("f", P, "VEC3", 5126, 34962, True)}, "indices": b.add("H", [0, 1, 2], "SCALAR", 5123, 34963)}
    return finish(b, {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}], "meshes": [{"primitives": [p]}]})
def cube():
    b = B(); return finish(b, {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "cube"}], "meshes": [{"primitives": [mesh_prim(b)]}]})
def hierarchy():
    b = B(); s = math.sin(math.pi / 8); c = math.cos(math.pi / 8)
    return finish(b, {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}],
                      "nodes": [{"name": "root", "children": [1, 2], "translation": [0, 1, 0]}, {"name": "a", "mesh": 0, "rotation": [0, s, 0, c], "scale": [1, 2, 1]}, {"name": "b", "mesh": 0, "translation": [3, 0, 0], "children": [3]}, {"name": "c", "mesh": 0, "translation": [0, 2, 0]}],
                      "meshes": [{"primitives": [mesh_prim(b)]}]})
def pbr():
    b = B(); return finish(b, {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}], "meshes": [{"primitives": [mesh_prim(b, 0)]}],
                               "materials": [{"name": "gold", "pbrMetallicRoughness": {"baseColorFactor": [1, .77, .34, 1], "metallicFactor": 1, "roughnessFactor": .3}}]})
PNG1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
def textured():
    b = B(); return finish(b, {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}], "meshes": [{"primitives": [mesh_prim(b, 0, uv=True)]}],
                               "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}], "textures": [{"sampler": 0, "source": 0}], "images": [{"uri": PNG1}], "samplers": [{"magFilter": 9729, "minFilter": 9987}]})
def animated():
    b = B(); t = b.add("f", [0.0, 0.5, 1.0, 1.5], "SCALAR", 5126, minmax=False); b.acc[t]["min"] = [0.0]; b.acc[t]["max"] = [1.5]
    o = b.add("f", [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], "VEC3", 5126)
    d = {"asset": asset(), "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "mover"}], "meshes": [{"primitives": [mesh_prim(b)]}],
         "animations": [{"samplers": [{"input": t, "output": o, "interpolation": "LINEAR"}], "channels": [{"sampler": 0, "target": {"node": 0, "path": "translation"}}]}]}
    return finish(b, d)
CORPUS = {"triangle": tri, "cube": cube, "hierarchy": hierarchy, "pbr": pbr, "textured": textured, "animated": animated}
