"""Village half of the v2 scene: lights, terrain, buildings and props (merged meshes per material), trees, cloud deck - all through x3d_mcp."""
import math, random
from mcpkit import B
import town_layout as L, town_geo as G
from meshkit import fbm_sin, Mesh

TEX = {  # mesh key -> (base, normal, roughness, metallic, crease)
 "plaster": ("plaster.png", "plaster_n.png", 0.93, 0.0, 0.9), "paint": ("plaster.png", "plaster_n.png", 0.7, 0.0, 0.9),
 "roof_tile": ("roof.png", "roof_n.png", 0.78, 0.0, 0.9), "roof_slate": ("slate.png", "slate_n.png", 0.55, 0.0, 0.9),
 "wood": ("wood.png", "wood_n.png", 0.82, 0.0, 0.9), "stone": ("ashlar.png", "ashlar_n.png", 0.9, 0.0, 0.9), "bush": (None, None, 0.9, 0.0, 0.35), "cobble": ("cobble.png", "cobble_n.png", 0.86, 0.0, 0.9),
 "dirt": ("dirt.png", "dirt_n.png", 0.97, 0.0, 0.9), "wheat": ("wheat.png", "wheat_n.png", 0.95, 0.0, 0.9), "furrow": ("furrow.png", "furrow_n.png", 0.97, 0.0, 0.9),
 "water": ("water.png", "water_n.png", 0.06, 0.0, 0.9),
 "metal": (None, None, 0.42, 0.85, 0.9), "glass": (None, None, 0.05, 0.1, 0.9), "glass_lit": (None, None, 0.12, 0.0, 0.9), "cloth": (None, None, 0.95, 0.0, 0.3),
 "lampglass": (None, None, 0.3, 0.0, 0.9), "forge": (None, None, 0.6, 0.0, 0.9), "goods": (None, None, 0.8, 0.0, 0.9),
}
BASECOL = {"glass": (0.10, 0.14, 0.19), "glass_lit": (0.10, 0.13, 0.17), "water": (0.4, 0.7, 0.8), "lampglass": (0.9, 0.85, 0.7), "forge": (0.2, 0.1, 0.05)}
EMIS = {"forge": (1.0, 0.42, 0.1)}
TEXKEYS = {"plaster", "paint", "roof_tile", "roof_slate", "wood", "stone", "cobble", "dirt", "wheat", "furrow", "water"}
def grass_tint(x, z, y):
    n1 = fbm_sin(x * 8, z * 8, 21); n2 = fbm_sin(x * 21, z * 21, 22); dry = max(0.0, min(1.0, (n1 - 0.05) * 3.0))
    k = 0.86 + 0.18 * n2 + 0.06 * n1
    return (min(1, k * (1.0 - 0.06 * dry)), min(1, k * (1.0 - 0.14 * dry)), min(1, k * (1.0 - 0.45 * dry)))
def far_tint(x, z, y):
    r = math.hypot(x, z); n1 = 0.5 + 0.5 * fbm_sin(x * 0.7, z * 0.7, 41); n2 = 0.5 + 0.5 * fbm_sin(x * 2.1, z * 2.1, 42)
    forest = (0.12 + 0.05 * n2, 0.24 + 0.07 * n2, 0.10); meadow = (0.34 + 0.08 * n1, 0.44 + 0.06 * n1, 0.16); autumn = (0.55, 0.38, 0.12); rock = (0.42, 0.40, 0.37); snow = (0.93, 0.95, 0.98)
    t = max(0.0, min(1.0, (n1 - 0.45) * 3)); c = [meadow[i] * (1 - t) + forest[i] * t for i in range(3)]
    a = max(0.0, min(1.0, (n2 - 0.7) * 4)) * 0.5; c = [c[i] * (1 - a) + autumn[i] * a for i in range(3)]
    ra = max(0.0, min(1.0, (y - 420) / 380)); c = [c[i] * (1 - ra) + rock[i] * ra for i in range(3)]
    sn = max(0.0, min(1.0, (y - 760 - 80 * (n2 - 0.5)) / 160)); c = [c[i] * (1 - sn) + snow[i] * sn for i in range(3)]
    return tuple(c)
def near_tint(x, z, y):
    c = grass_tint(x, z, y); return c

def tree_sites(rng, n, rmin, rmax, avoid_far=True):
    out = []; tries = 0
    def rects():
        return [(h[2], h[3], h[4], h[5], h[7]) for h in L.HOUSES + [L.INN, L.CHURCH, L.SMITHY]]
    R = rects()
    while len(out) < n and tries < n * 120:
        tries += 1; a = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(rmin * rmin, rmax * rmax)); x, z = r * math.sin(a), r * math.cos(a)
        if abs(z) < 8.5 and abs(x) < 245: continue
        if abs(x) < 7.5 and abs(z) < 215: continue
        if math.hypot(x, z) < L.PLAZA_R + 4: continue
        if any(L.rrect(cx, cz, w, d, rot, x, z, 4.5) for cx, cz, w, d, rot in R): continue
        if any(abs(x - fx) < w / 2 + 2 and abs(z - fz) < d / 2 + 2 for fx, fz, w, d, rot, k in L.FIELDS): continue
        if -36 < x < -24 and -46 < z < -20: continue
        if -41 < x < -31 and 0 < z < 34: continue
        if 41 < x < 52 and 0 < z < 28: continue
        if 8 < x < 24 and -72 < z < -20: continue
        if -26 < x < -10 and 20 < z < 80: continue
        grove = 0.5 + 0.5 * fbm_sin(x * 5, z * 5, 31)
        if rng.random() > 0.12 + 0.88 * grove ** 2: continue
        out.append((x, z, a));
    return out

async def build_town(b: B):
    rng = random.Random(7); info = {}
    town = await b.mk("Group", name="Town"); core = await b.mk("Group", parent=town, name="TownCore"); out = await b.mk("Group", parent=town, name="Outskirts")
    # ---- lights (JS drives direction / colour / intensity from the Sun and Moon positions)
    for grp, pre in ((core, ""), (out, "Out")):
        await b.mk("DirectionalLight", {"direction": [-0.5, -0.6, -0.6], "intensity": 4.0, "color": [1, 0.92, 0.8], "shadows": grp is core, "shadowIntensity": 0.8}, parent=grp, name=pre + "KeyLight")
        await b.mk("DirectionalLight", {"direction": [0, -1, 0], "intensity": 0.9, "color": [0.55, 0.7, 1.0]}, parent=grp, name=pre + "SkyLight")
        for k_, az in enumerate((0.3, 0.3 + 2.0944, 0.3 + 4.1888)):
            await b.mk("DirectionalLight", {"direction": [round(-math.sin(az) * 0.94, 3), -0.34, round(-math.cos(az) * 0.94, 3)], "intensity": 0.4, "color": [0.6, 0.72, 0.95]}, parent=grp, name=f"{pre}Fill{k_}")
    for nm, (x, y, z), col in (("LampA", (-9, 3.7, -9), [1, 0.72, 0.4]), ("LampB", (9, 3.7, 9), [1, 0.72, 0.4]), ("ForgeL", (49.0, 1.6, 32.0), [1, 0.45, 0.15])):
        await b.mk("PointLight", {"location": [x, y, z], "intensity": 0.0, "color": col, "radius": 26, "attenuation": [1, 0.04, 0.012]}, parent=core, name=nm)
    # ---- merged meshes per material
    M = G.build_core()
    for key in ("plaster", "paint", "roof_tile", "roof_slate", "wood", "stone", "metal", "glass", "glass_lit", "cloth", "lampglass", "forge", "goods", "bush", "cobble", "dirt", "wheat", "furrow", "water"):
        e = M[key].export(uv=key in TEXKEYS); base, normal, rough, metal, crease = TEX[key]
        sh = await b.mk("Shape", parent=core, name="S_" + key)
        await b.pbr(sh, base=base, normal=normal, color=BASECOL.get(key, (1, 1, 1)), rough=rough, metal=metal, emissive=EMIS.get(key), mat_name="Mat_" + key if key in ("glass_lit", "lampglass", "forge", "water") else None, aniso=8,
                    transparency=0.12 if key == "water" else None)
        if key == "water": ap_ = None
        await b.ifs(sh, e, crease=crease, solid=key not in ("cloth", "water", "wheat", "furrow", "dirt", "cobble", "glass", "glass_lit"), name="G_" + key)
        info[key] = dict(verts=e["verts"], faces=e["faces"])
    # ---- terrain: flat core disc (textured grass, vertex tint) inside the shadow volume; textured outskirts ring; far vertex-coloured landscape
    core_t = G.terrain_rings(0.0, 215.0, 192, 5.0, 1.0, G.H, near_tint, tile=5.0); e = core_t.export(uv=True)
    sh = await b.mk("Shape", parent=core, name="S_terrain_core"); await b.pbr(sh, base="grass.png", normal="grass_n.png", rough=0.96, aniso=16); await b.ifs(sh, e, crease=1.0, solid=True); info["terrain_core"] = dict(verts=e["verts"], faces=e["faces"])
    out_t = G.terrain_rings(215.0, 1700.0, 192, 9.0, 1.05, G.H, near_tint, flat_until=300.0, tile=5.0); e = out_t.export(uv=True)
    sh = await b.mk("Shape", parent=out, name="S_terrain_out"); await b.pbr(sh, base="grass.png", normal="grass_n.png", rough=0.96, aniso=16); await b.ifs(sh, e, crease=1.0, solid=True); info["terrain_out"] = dict(verts=e["verts"], faces=e["faces"])
    far_t = G.terrain_rings(1650.0, 28000.0, 192, 90.0, 1.07, G.H, far_tint, flat_until=1700.0, tile=5.0); e = far_t.export(uv=False)
    sh = await b.mk("Shape", parent=out, name="S_terrain_far"); await b.pbr(sh, rough=0.95, aniso=2); await b.ifs(sh, e, crease=1.0, solid=True); info["terrain_far"] = dict(verts=e["verts"], faces=e["faces"])
    # ---- trees: eight DEF'd variants in an unrendered library, instanced with Transform + USE
    lib = await b.mk("Switch", {"whichChoice": -1}, parent=town, name="TreeLibrary"); V = G.tree_variants(); first = {}
    for i, m in enumerate(V):
        sh = await b.mk("Shape", parent=lib, name=f"Tree{i}"); await b.pbr(sh, rough=0.9, aniso=1); await b.ifs(sh, m.export(uv=False), crease=0.25 if i < 6 else 0.5 if i == 6 else 0.3, solid=True)
    def pick(r):
        x = rng.random()
        if r > 500: return 6 if x < 0.5 else 7 if x < 0.57 else rng.choice([0, 1, 2, 3, 5])
        return 7 if x < 0.07 else rng.choice([0, 1, 2, 3, 3, 4, 5])
    near_sites = tree_sites(rng, 70, 25, 214); mid_sites = tree_sites(rng, 420, 215, 1500)
    for grp, sites in ((core, near_sites), (out, mid_sites)):
        for (x, z, a) in sites:
            v = pick(math.hypot(x, z)); sc = rng.uniform(0.78, 1.4) * (1.25 if math.hypot(x, z) > 900 else 1.0)
            tr = await b.mk("Transform", {"translation": [round(x, 2), round(G.H(x, z), 2), round(z, 2)], "rotation": [0, 1, 0, round(a * 3.7 % 6.28, 3)], "scale": [sc, sc * rng.uniform(0.9, 1.15), sc]}, parent=grp); await b.use(tr, f"Tree{v}", "children")
    info["trees"] = dict(near=len(near_sites), mid=len(mid_sites))
    # ---- cloud deck (drifting texture; lit by the outskirts lights)
    cd = await b.mk("Transform", {"translation": [0, 2600, 0]}, parent=out, name="CloudDeckT"); sh = await b.mk("Shape", parent=cd, name="CloudDeck"); ap = await b.mk("Appearance", parent=sh)
    pm = await b.mk("PhysicalMaterial", {"baseColor": [1, 1, 1], "roughness": 1.0, "metallic": 0.0, "emissiveColor": [0.18, 0.18, 0.2]}, parent=ap, name="Mat_Clouds"); it = await b.mk("ImageTexture", {"url": ["../tex/cloud_sheet.png"]}, parent=pm, cf="baseTexture")
    await b.mk("TextureProperties", {"anisotropicDegree": 4, "generateMipMaps": True, "minificationFilter": "AVG_PIXEL_AVG_MIPMAP"}, parent=it, cf="textureProperties"); await b.mk("TextureTransform", {"scale": [8, 8]}, parent=ap, name="CloudTT")
    n = 48; ring = [[round(26000 * math.sin(2 * math.pi * i / n), 1), 0, round(26000 * math.cos(2 * math.pi * i / n), 1)] for i in range(n)]
    ifs = await b.mk("IndexedFaceSet", {"coordIndex": list(range(n)) + [-1], "solid": False, "texCoordIndex": list(range(n)) + [-1]}, parent=sh)
    await b.mk("Coordinate", {"point": [[0, 0, 0]] * 0 + ring}, parent=ifs, cf="coord"); await b.mk("TextureCoordinate", {"point": [[0.5 + 0.5 * math.sin(2 * math.pi * i / n), 0.5 + 0.5 * math.cos(2 * math.pi * i / n)] for i in range(n)]}, parent=ifs, cf="texCoord")
    return core, out, info
