"""The villagers: H-Anim humanoids (HAnimHumanoid / HAnimJoint / HAnimSegment) with keyframed gait and gesture animation, walking closed paths via interpolators.  All through x3d_mcp."""
import math
from mcpkit import B
import town_layout as L, humans as Hm

def yaw_of(dx, dz): return math.atan2(dx, dz)
def colour(name): return Hm.COLORS[name]

async def build_people(b: B, core: str):
    G = Hm.geometries(); info = []
    lib = await b.mk("Switch", {"whichChoice": -1}, parent=core, name="HumanLibrary")
    for key, m in G.items():
        sh = await b.mk("Shape", parent=lib, name="GS_" + key); await b.ifs(sh, m.export(uv=False, colors=False), crease=0.9, solid=True, name="G_" + key)
    ap_made = set()
    async def appearance(shape, pid, cls, skin, hair):
        """appearances are DEF'd once per person and class inside the (unrendered) library, then USE'd by every segment shape"""
        name = f"Ap_{pid}_{cls}"
        if name not in ap_made:
            col = {"skin": skin, "hair": hair, "shirt": colour(pcfg["shirt"]), "sleeve": colour(pcfg["shirt"]), "pants": colour(pcfg["pants"])}.get(cls) or Hm.ACC_COLOR.get(cls) or (0.5, 0.5, 0.5)
            rough, metal = {"skin": (0.55, 0.0), "hair": (0.7, 0.0), "tool": (0.4, 0.9), "eye": (0.2, 0.0), "shoes": (0.6, 0.0)}.get(cls, (0.88, 0.0))
            ls = await b.mk("Shape", parent=lib); ap = await b.mk("Appearance", parent=ls, name=name); await b.mk("PhysicalMaterial", {"baseColor": list(col), "roughness": rough, "metallic": metal}, parent=ap); ap_made.add(name)
        return await b.use(shape, name, "appearance")
    positions = {p[0]: (p[5][0] if isinstance(p[5], tuple) else None, p[5][1] if isinstance(p[5], tuple) else None) for p in L.PEOPLE}
    for p in L.PEOPLE:
        pid, name, role, arch, (shirt_n, pants_n), where, face_or_speed, scl, note = p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8]
        pcfg = dict(shirt=shirt_n, pants=pants_n); skin = Hm.PALETTE["skin"][pid]; hair = Hm.PALETTE["hair"][pid]
        walker = isinstance(where, list)
        T = await b.mk("Transform", parent=core, name="T_" + pid)
        if walker: path, total = L.smooth_path(where, closed=True, rounds=3, step=0.45); x0, z0 = path[0]; yaw0 = yaw_of(path[1][0] - x0, path[1][1] - z0)
        else:
            x0, z0 = where; tgt = face_or_speed
            yaw0 = yaw_of(positions[tgt][0] - x0, positions[tgt][1] - z0) if isinstance(tgt, str) else float(tgt)
        await b.call("set_field", {"node_id": T, "field_name": "translation", "value": [round(x0, 3), 0.0, round(z0, 3)]}); await b.call("set_field", {"node_id": T, "field_name": "rotation", "value": [0, 1, 0, round(yaw0, 4)]})
        hh = await b.mk("HAnimHumanoid", {"name": pid, "version": "2.0", "scale": [scl, scl, scl], "info": [f"{name}: {role}", "invented for the v2 demo", "rigid-segment mannequin, 16 joints, H-Anim-style names"]}, parent=T, name="H_" + pid)
        jid = {}; sid = {}
        for (jn, par, c) in Hm.JOINTS:
            jid[jn] = await b.mk("HAnimJoint", {"name": jn, "center": list(c)}, parent=jid[par] if par else hh, cf="" if par else "skeleton", name=f"{pid}_{jn}")
        segs = {sn: (jn, [(g, cls) for (g, cls) in lst]) for sn, (jn, lst) in Hm.SEGMENTS.items()}
        for acc in Hm.ACC_FOR.get(pid, []):
            sn, cls = Hm.ACCESSORIES[acc]; segs[sn][1].append((acc, cls))
        for sn, (jn, lst) in segs.items():
            sid[sn] = await b.mk("HAnimSegment", {"name": sn}, parent=jid[jn])
            for (g, cls) in lst:
                sh = await b.mk("Shape", parent=sid[sn]); await appearance(sh, pid, cls, skin, hair); await b.use(sh, "G_" + g, "geometry")
        for jn in jid: await b.use(hh, f"{pid}_{jn}", "joints")
        # ---------------- animation
        async def anim(clock, ts, K, period):
            n = 0
            for jn, vals in K.items():
                if jn == "_root_pos": continue
                it = await b.mk("OrientationInterpolator", {"key": [round(t, 5) for t in ts], "keyValue": vals}, name=f"I_{pid}_{jn}"); await b.route(clock, "fraction_changed", it, "set_fraction"); await b.route(it, "value_changed", jid[jn], "rotation"); n += 1
            if "_root_pos" in K:
                it = await b.mk("PositionInterpolator", {"key": [round(t, 5) for t in ts], "keyValue": [[v[0], round(v[1] - 0.95, 4), v[2]] for v in K["_root_pos"]]}, name=f"I_{pid}_root"); await b.route(clock, "fraction_changed", it, "set_fraction"); await b.route(it, "value_changed", jid["humanoid_root"], "translation"); n += 1
            return n
        if walker:
            speed = face_or_speed; leg = 0.92 * scl; stride = 2 * (2 * leg * math.sin(math.radians(24))); Tg = stride / speed
            clock = await b.mk("TimeSensor", {"cycleInterval": round(Tg, 3), "loop": True}, name=f"Gait_{pid}"); ts, K = Hm.walk_keys(16); await anim(clock, ts, K, Tg)
            lap = total / speed; pc = await b.mk("TimeSensor", {"cycleInterval": round(lap, 2), "loop": True}, name=f"Path_{pid}")
            n = len(path) - 1; keys = [round(i / n, 6) for i in range(n + 1)]; yaws = []; prev = None
            for i in range(n + 1):
                a, c = path[i], path[min(i + 1, n)] if i < n else path[1]; y = yaw_of(c[0] - a[0], c[1] - a[1])
                if prev is not None:
                    while y - prev > math.pi: y -= 2 * math.pi
                    while y - prev < -math.pi: y += 2 * math.pi
                yaws.append(y); prev = y
            yaws[-1] = yaws[0] + (2 * math.pi * round((yaws[-1] - yaws[0]) / (2 * math.pi)))
            pi_ = await b.mk("PositionInterpolator", {"key": keys, "keyValue": [[round(x, 3), 0.0, round(z, 3)] for x, z in path]}, name=f"PP_{pid}"); oi = await b.mk("OrientationInterpolator", {"key": keys, "keyValue": [[0, 1, 0, round(y, 4)] for y in yaws]}, name=f"PO_{pid}")
            for it in (pi_, oi): await b.route(pc, "fraction_changed", it, "set_fraction")
            await b.route(pi_, "value_changed", T, "translation"); await b.route(oi, "value_changed", T, "rotation")
            info.append(dict(id=pid, name=name, role=role, arch=arch, shirt=shirt_n, pants=pants_n, scale=scl, speed=speed, lap=round(lap, 1), path_m=round(total), gait_s=round(Tg, 2), note=note))
        else:
            kind = {"talker": "talker", "listener": "listener", "greeter": "greeter", "smith": "smith"}[arch]; per, ts, K = Hm.idle_keys(kind, seed=int(pid[1:]) * 7 + 3)
            clock = await b.mk("TimeSensor", {"cycleInterval": round(per, 3), "loop": True}, name=f"Idle_{pid}"); await anim(clock, ts, K, per)
            info.append(dict(id=pid, name=name, role=role, arch=arch, shirt=shirt_n, pants=pants_n, scale=scl, period=round(per, 2), note=note))
    return info
