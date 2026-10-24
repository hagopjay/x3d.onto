"""Thin async helper around the x3d_mcp stdio client: every scene node in v2 is created through the granular MCP tools (create_node, add_child, def_node, use_node, add_route)."""
import asyncio, json, math, os, re, statistics, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = os.path.expanduser("~/Projects/x3d/x3d_mcp")
txt = lambda r: "".join(getattr(c, "text", "") for c in r.content)

class B:
    def __init__(self, session):
        self.s = session; self.lat = []; self.calls = {}; self.names = set()
    async def call(self, name, args):
        t0 = time.perf_counter(); t = txt(await self.s.call_tool(name, args)); self.lat.append((time.perf_counter() - t0) * 1000); self.calls[name] = self.calls.get(name, 0) + 1
        if t.startswith("Error") or "Error executing" in t: raise SystemExit(f"{name} {json.dumps(args)[:300]} -> {t[:400]}")
        return t
    async def mk(self, nt, fields=None, parent=None, cf="", name=None):
        t = await self.call("create_node", {"node_type": nt, "fields": fields or {}}); nid = re.search(r"ID: (\S+)", t).group(1)
        if parent: await self.call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf})
        if name:
            assert name not in self.names, "duplicate DEF " + name
            self.names.add(name); await self.call("def_node", {"node_id": nid, "name": name})
        return nid
    async def use(self, parent, def_name, cf=""):
        t = await self.call("use_node", {"def_name": def_name}); nid = re.search(r"ID: (\S+)", t).group(1)
        await self.call("add_child", {"parent_id": parent, "child_id": nid, "container_field": cf}); return nid
    async def route(self, a, fa, b, fb): return await self.call("add_route", {"from_node": a, "from_field": fa, "to_node": b, "to_field": fb})
    # ---- composite helpers
    async def ifs(self, parent, e, crease=0.9, solid=True, name=None, line=False):
        """IndexedFaceSet from meshkit export dict"""
        f = {"coordIndex": e["coordIndex"], "creaseAngle": crease, "solid": solid}
        if "texCoordIndex" in e: f["texCoordIndex"] = e["texCoordIndex"]
        if "colorIndex" in e: f["colorIndex"] = e["colorIndex"]
        g = await self.mk("IndexedFaceSet", f, parent=parent, name=name)
        await self.mk("Coordinate", {"point": e["point"]}, parent=g, cf="coord")
        if "uv" in e: await self.mk("TextureCoordinate", {"point": e["uv"]}, parent=g, cf="texCoord")
        if "color" in e: await self.mk("Color", {"color": e["color"]}, parent=g, cf="color")
        return g
    async def pbr(self, parent, name=None, base=None, normal=None, mr=None, emis_tex=None, color=(1, 1, 1), rough=0.9, metal=0.0, emissive=None, aniso=8, transparency=None, norm_scale=1.0, tex_dir="../tex/", mat_name=None):
        ap = await self.mk("Appearance", parent=parent, name=name)
        f = {"baseColor": list(color), "roughness": rough, "metallic": metal}
        if emissive: f["emissiveColor"] = list(emissive)
        if transparency: f["transparency"] = transparency
        if normal and norm_scale != 1.0: f["normalScale"] = norm_scale
        pm = await self.mk("PhysicalMaterial", f, parent=ap, name=mat_name)
        for tex, cf, srgb in ((base, "baseTexture", True), (normal, "normalTexture", False), (mr, "metallicRoughnessTexture", False), (emis_tex, "emissiveTexture", True)):
            if not tex: continue
            it = await self.mk("ImageTexture", {"url": [tex_dir + tex]}, parent=pm, cf=cf)
            await self.mk("TextureProperties", {"anisotropicDegree": aniso, "generateMipMaps": True, "minificationFilter": "AVG_PIXEL_AVG_MIPMAP", "magnificationFilter": "AVG_PIXEL"}, parent=it, cf="textureProperties")
        return ap
    async def emissive_shape(self, parent, col, geom, gfields=None, name=None, tr=0.0):
        sh = await self.mk("Shape", parent=parent); ap = await self.mk("Appearance", parent=sh)
        m = {"diffuseColor": [0, 0, 0], "emissiveColor": list(col)}
        if tr: m["transparency"] = tr
        await self.mk("Material", m, parent=ap, name=name); await self.mk(geom, gfields or {}, parent=sh); return sh
    async def lines(self, parent, pts, idx, col, name=None, tr=0.0):
        sh = await self.mk("Shape", parent=parent, name=name); ap = await self.mk("Appearance", parent=sh)
        m = {"diffuseColor": [0, 0, 0], "emissiveColor": list(col)}
        if tr: m["transparency"] = tr
        await self.mk("Material", m, parent=ap); ils = await self.mk("IndexedLineSet", {"coordIndex": idx}, parent=sh); await self.mk("Coordinate", {"point": pts}, parent=ils, cf="coord"); return sh

def qmul(a, b): return (a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3], a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2], a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1], a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0])
def aa(axis, ang): s = math.sin(ang / 2); return (math.cos(ang / 2), axis[0] * s, axis[1] * s, axis[2] * s)
def toaa(q):
    w = max(-1, min(1, q[0])); ang = 2 * math.acos(w); s = math.sqrt(max(1e-12, 1 - w * w)); return [round(q[1] / s, 5), round(q[2] / s, 5), round(q[3] / s, 5), round(ang, 5)] if ang > 1e-6 else [0, 1, 0, 0]
def look(pos, target=(0, 0, 0)):
    dx, dy, dz = [t - p for t, p in zip(target, pos)]; yaw = math.atan2(-dx, -dz); pitch = math.atan2(dy, math.hypot(dx, dz)); return toaa(qmul(aa((0, 1, 0), yaw), aa((1, 0, 0), pitch)))

def server_params(): return StdioServerParameters(command=os.path.join(REPO, ".venv/bin/python"), args=["-m", "src.server"], cwd=REPO)
