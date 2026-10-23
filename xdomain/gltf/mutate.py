"""Fault injection for glTF JSON. Each operator takes a deep copy of the document and returns it mutated, or None if not applicable."""
import base64, copy, json, struct
def getbuf(d):
    u = d["buffers"][0]["uri"]; return bytearray(base64.b64decode(u.split(",", 1)[1]))
def setbuf(d, raw): d["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(bytes(raw)).decode()
F = {}
def fault(i, level, desc):
    def deco(fn): F[i] = (level, desc, fn); return fn
    return deco
@fault("G01", "L1", "asset.version removed")
def _(d): del d["asset"]["version"]; return d
@fault("G02", "L1", "asset.version 3.0")
def _(d): d["asset"]["version"] = "3.0"; return d
@fault("G03", "L2", "accessor.bufferView out of range")
def _(d): d["accessors"][0]["bufferView"] = len(d["bufferViews"]) + 3; return d
@fault("G04", "L2", "accessor.count larger than its bufferView")
def _(d): d["accessors"][0]["count"] *= 50; return d
@fault("G05", "L2", "bufferView runs past the buffer")
def _(d): d["bufferViews"][-1]["byteLength"] += 4096; return d
@fault("G06", "L2", "buffer.byteLength does not match embedded data")
def _(d): d["buffers"][0]["byteLength"] += 8; return d
@fault("G07", "L2", "scene refers to a missing node")
def _(d): d["scenes"][0]["nodes"].append(99); return d
@fault("G08", "L2", "node cycle")
def _(d):
    if len(d["nodes"]) < 2: return None
    d["nodes"][0].setdefault("children", []).append(1); d["nodes"][1].setdefault("children", []).append(0); return d
@fault("G09", "L2", "node.mesh out of range")
def _(d):
    for n in d["nodes"]:
        if "mesh" in n: n["mesh"] = 42; return d
@fault("G10", "L2", "primitive.material out of range")
def _(d): d["meshes"][0]["primitives"][0]["material"] = 7; return d
@fault("G11", "D", "index value beyond the vertex count (data)")
def _(d):
    ia = next((a for a in d["accessors"] if a["type"] == "SCALAR" and a["componentType"] == 5123 and "min" not in a), None)
    if not ia or "animations" in d and ia is d["accessors"][-1]: return None
    bv = d["bufferViews"][ia["bufferView"]]; raw = getbuf(d); struct.pack_into("<H", raw, bv["byteOffset"], 60000); setbuf(d, raw); return d
@fault("G12", "D", "POSITION min/max wrong (data)")
def _(d):
    for p in d["meshes"][0]["primitives"]:
        a = d["accessors"][p["attributes"]["POSITION"]]; a["max"] = [v + 5 for v in a["max"]]; return d
@fault("G13", "L2", "non-unit rotation quaternion")
def _(d):
    for n in d["nodes"]:
        if "rotation" in n: n["rotation"] = [0, 2, 0, 2]; return d
@fault("G14", "L2", "matrix together with translation")
def _(d): d["nodes"][0]["matrix"] = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; d["nodes"][0]["translation"] = [1, 1, 1]; return d
@fault("G15", "D", "animation input not increasing (data)")
def _(d):
    if "animations" not in d: return None
    a = d["accessors"][d["animations"][0]["samplers"][0]["input"]]; bv = d["bufferViews"][a["bufferView"]]; raw = getbuf(d)
    struct.pack_into("<f", raw, bv["byteOffset"] + 8, 0.1); setbuf(d, raw); return d
@fault("G16", "L2", "animation channel node out of range")
def _(d):
    if "animations" not in d: return None
    d["animations"][0]["channels"][0]["target"]["node"] = 50; return d
@fault("G17", "L2", "texture.source out of range")
def _(d):
    if "textures" not in d: return None
    d["textures"][0]["source"] = 9; return d
@fault("G18", "L2", "required extension not supported")
def _(d): d["extensionsRequired"] = ["KHR_fake_extension"]; d["extensionsUsed"] = ["KHR_fake_extension"]; return d
@fault("G19", "L2", "vertex bufferView byteStride not a multiple of 4")
def _(d): d["bufferViews"][0]["byteStride"] = 10; return d
@fault("G20", "L1", "accessor.componentType invalid")
def _(d): d["accessors"][0]["componentType"] = 9999; return d
@fault("G21", "W", "unused accessor added (warning/info expected)")
def _(d):
    d["bufferViews"].append({"buffer": 0, "byteOffset": 0, "byteLength": 12}); d["accessors"].append({"bufferView": len(d["bufferViews"]) - 1, "componentType": 5126, "count": 1, "type": "VEC3"}); return d
@fault("G22", "L1", "primitive.mode invalid")
def _(d): d["meshes"][0]["primitives"][0]["mode"] = 99; return d
@fault("G23", "L2", "primitive without POSITION")
def _(d):
    for p in d["meshes"][0]["primitives"]:
        if "NORMAL" in p["attributes"]: del p["attributes"]["POSITION"]; return d
@fault("G24", "L2", "scene index out of range")
def _(d): d["scene"] = 5; return d
@fault("G25", "L0", "JSON broken (text level)")
def _(d): return "TEXT:" + json.dumps(d)[:-1]
