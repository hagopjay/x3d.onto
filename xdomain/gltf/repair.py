"""Deterministic glTF repairs: derived data and defaults only. Dangling references are NOT removed (that would delete what the author asked for); those go back to the model or a person."""
import base64, json, math, struct
def repair(text: str):
    try: d = json.loads(text)
    except Exception: return text, []
    done = []
    if isinstance(d.get("asset"), dict) and "version" not in d["asset"]: d["asset"]["version"] = "2.0"; done.append(("UNDEFINED_PROPERTY", "asset.version", "added 2.0"))
    try:
        u = d["buffers"][0]["uri"]; raw = base64.b64decode(u.split(",", 1)[1])
        if d["buffers"][0].get("byteLength") != len(raw): d["buffers"][0]["byteLength"] = len(raw); done.append(("BUFFER_BYTE_LENGTH_MISMATCH", "buffers[0]", "byteLength from data"))
        for i, a in enumerate(d.get("accessors", [])):
            if a.get("type") == "VEC3" and a.get("componentType") == 5126 and "min" in a and "bufferView" in a and a["bufferView"] < len(d["bufferViews"]):
                bv = d["bufferViews"][a["bufferView"]]
                if bv.get("byteStride") or bv["byteOffset"] + a["count"] * 12 > len(raw): continue
                vals = struct.unpack_from("<%df" % (a["count"] * 3), raw, bv["byteOffset"]); rows = [vals[j:j + 3] for j in range(0, len(vals), 3)]
                mn = [min(r[k] for r in rows) for k in range(3)]; mx = [max(r[k] for r in rows) for k in range(3)]
                if any(abs(x - y) > 1e-6 for x, y in zip(mn + mx, a["min"] + a["max"])): a["min"], a["max"] = mn, mx; done.append(("ACCESSOR_MAX_MISMATCH", f"accessors[{i}]", "min/max from data"))
    except Exception: pass
    for i, n in enumerate(d.get("nodes", [])):
        r = n.get("rotation")
        if isinstance(r, list) and len(r) == 4:
            l = math.sqrt(sum(x * x for x in r))
            if l > 1e-9 and abs(l - 1) > 1e-4: n["rotation"] = [x / l for x in r]; done.append(("VALUE_NOT_IN_RANGE", f"nodes[{i}].rotation", "normalised"))
    return json.dumps(d), done
