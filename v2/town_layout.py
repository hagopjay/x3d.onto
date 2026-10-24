"""Layout of the fictional village 'Aurelsbrunn' (metres; x east, y up, z south). Shared by the scene builder and the engine (data/town.json).
Everything here is invented for the demo: names, people, roles.  Run this file to validate walking paths against obstacles and write data/town.json."""
import math, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
FLAT_R = 270.0
LAT, LON = 46.80, 8.20          # illustrative site (not a real settlement); on the procedural Earth this is just a point
HOUSES = [  # id, name, x, z, w (along local x), d (along local z), wall height, rotY, wall tint, roof kind, role, shutters
 ("H01", "Baker's house", -42, -14, 9, 8, 4.4, 0, "ochre", "tile", "bakery with a front shop", "green"),
 ("H02", "Weaver's cottage", -78, -14, 8, 7, 4.0, 0, "cream", "tile", "weaver", "blue"),
 ("H03", "Miller's house", -116, -15, 10, 8, 4.6, 0, "cream", "slate", "miller", "brown"),
 ("H04", "Cooper's house", 34, -14, 9, 8, 4.2, 0, "terracotta", "tile", "cooper", "green"),
 ("H05", "Schoolhouse", 72, -15, 11, 8, 4.8, 0, "cream", "slate", "village school", "brown"),
 ("H06", "Doctor's house", 112, -14, 9, 8, 4.4, 0, "blue", "tile", "physician", "cream"),
 ("H07", "Fisher's cottage", -70, 16, 8, 7, 4.0, math.pi, "terracotta", "tile", "fisher", "blue"),
 ("H08", "Tailor's house", -110, 15, 9, 8, 4.4, math.pi, "cream", "tile", "tailor", "green"),
 ("H09", "Mayor's house", 12, 17, 12, 9, 5.2, math.pi, "ochre", "slate", "mayor and village hall", "brown"),
 ("H10", "Carter's house", 80, 16, 9, 8, 4.2, math.pi, "cream", "tile", "carter", "green"),
 ("H11", "Potter's house", 120, 16, 8, 7, 4.0, math.pi, "terracotta", "tile", "potter", "blue"),
 ("H12", "North farmhouse", 16, -78, 11, 9, 4.8, -math.pi / 2, "cream", "tile", "farm family", "green"),
 ("H13", "South farmhouse", -18, 84, 11, 9, 4.8, math.pi / 2, "ochre", "tile", "farm family", "brown"),
 ("H14", "Gatekeeper's lodge", 176, -12, 7, 6, 3.8, 0, "blue", "slate", "gatekeeper", "cream"),
]
INN = ("B01", "The Compass Rose (inn)", -36, 36, 15, 10, 5.4, math.pi, "ochre", "tile", "inn with stable", "green")
CHURCH = ("B02", "St. Aurel's church", -30, -52, 10, 20, 7.0, 0, "stone", "slate", "church with a tower", "brown")
SMITHY = ("B03", "The smithy", 46, 30, 9, 8, 3.6, math.pi, "wood", "tile", "open-front forge", "brown")
STALLS = [("S01", "Bread stall", 14, -9, 0.0), ("S02", "Vegetable stall", -16, 8, math.pi), ("S03", "Cloth stall", 17, 8, math.pi)]
FOUNTAIN = (0.0, 0.0, 3.2)        # x, z, basin radius
PLAZA_R = 21.0
LAMPS = [(-9, -9), (9, -9), (-9, 9), (9, 9), (-62, 4.6), (-100, 4.6), (-140, 4.6), (62, -4.6), (100, -4.6), (140, -4.6), (62, 4.6), (-62, -4.6), (4.6, -44), (4.6, 44), (-4.6, -84), (-4.6, 88),
         (-33.4, 18), (-27.4, -31), (49.4, 14), (-22, -4.6), (24, 4.6), (180, 4.6)]
ROADS = [  # polyline (x,z), width, surface
 ([(-235, 0), (-24, 0), (24, 0), (235, 0)], 7.0, "dirt"), ([(0, -205), (0, -22), (0, 22), (0, 205)], 6.0, "dirt"),
 ([(-30, -22), (-30, -42)], 3.2, "cobble"), ([(46, 4), (46, 25)], 3.0, "dirt"), ([(-36, 4), (-36, 30)], 3.0, "dirt"),
 ([(16, -69), (16, -40), (0, -22)], 2.6, "dirt"), ([(-18, 74), (-18, 50), (0, 22)], 2.6, "dirt"),
]
BENCHES = [(-14.5, -3.4, math.pi / 2), (14.5, -3.4, -math.pi / 2), (-5, 12.5, 0.0), (6, -12.8, math.pi)]
BARRELS = [(-26.5, 38.5), (-25.8, 39.6), (-44.6, 38.2), (36.4, 8.4), (-18.2, 10.6), (19.8, 10.8), (51.6, 26), (41.4, 33.2), (-46.8, -9.2), (30.2, -9.6)]
CRATES = [(-17.2, 5.6, 0.3), (18.4, 5.5, -0.2), (43.2, 25.3, 0.5), (-45.5, -8.6, 0.1)]
FIELDS = [(16, -125, 60, 38, -0.05, "wheat"), (-60, -120, 44, 30, 0.1, "furrow"), (-18, 130, 62, 36, 0.0, "wheat"), (55, 120, 40, 34, -0.1, "furrow"), (-95, 85, 40, 26, 0.0, "furrow")]
PEOPLE = [  # id, name, role, archetype, colours (shirt, pants), path | (x, z) , facing (id | yaw), speed/pace, note
 ("P01", "Mara", "baker on her rounds", "walker", ("brick", "navy"), [(-40, -3.4), (-12, -3.4), (-6, -6.8), (6, -6.8), (12, -3.4), (28, -3.4), (30.4, 0), (28, 3.4), (12, 3.4), (6, 6.8), (-6, 6.8), (-12, 3.4), (-40, 3.4), (-43, 0)], 1.25, 1.0, "walks a closed loop of about 190 m past the fountain"),
 ("P02", "Tomas", "carter on the main street", "walker", ("ochre", "brown"), [(160, -1.0), (30, -1.0), (24, 0), (30, 1.0), (160, 1.0), (163, 0)], 1.35, 1.04, "walks the east half of the main street, about 270 m per lap"),
 ("P03", "Ilse", "child running errands", "walker", ("yellow", "teal"), [(2.0, -40), (2.0, -13), (4.6, -4.4), (6.0, 0), (4.6, 4.4), (2.0, 13), (2.0, 40), (-2.0, 40), (-2.0, 13), (-4.6, 4.4), (-6.0, 0), (-4.6, -4.4), (-2.0, -13), (-2.0, -40)], 1.15, 0.7, "runs errands along the cross street"),
 ("P04", "Doctor Veit", "physician on a house call", "walker", ("grey", "charcoal"), [(112, -7.8), (108, -2.6), (60, -2.6), (54, 0), (60, 2.6), (108, 2.6), (114, 0)], 1.3, 1.02, "walks between his house and the plaza"),
 ("P05", "Nell", "vegetable seller", "talker", ("blue", "brown"), (-16.0, 9.3), "P06", 1.0, "talks across the counter of her stall"),
 ("P06", "Anselm", "customer at the vegetable stall", "talker", ("green", "tan"), (-15.4, 6.0), "P05", 1.04, "talks with the seller"),
 ("P07", "Greta", "cloth merchant", "greeter", ("purple", "charcoal"), (17.0, 9.3), 3.14159, 0.96, "waves at passers-by"),
 ("P08", "Old Bram", "blacksmith", "smith", ("leather", "dark"), (46.0, 27.8), 3.14159, 1.06, "hammers on the anvil, one strike every 1.4 s"),
 ("P09", "Hanne", "villager by the fountain", "talker", ("orange", "navy"), (5.6, -2.0), "P10", 0.98, "chats at the fountain"),
 ("P10", "Piet", "villager by the fountain", "listener", ("teal", "brown"), (7.0, 0.0), "P09", 1.04, "listens"),
 ("P11", "Father Anselm", "priest on the church lane", "walker", ("black", "black"), [(-30.7, -24.5), (-30.7, -40.0), (-29.3, -40.0), (-29.3, -24.5)], 0.9, 1.0, "paces the church lane slowly"),
 ("P12", "Jonas", "gatekeeper", "listener", ("olive", "brown"), (178.5, -6.2), 0.0, 1.0, "watches the east gate"),
]
SMITH_ANVIL = (46.0, 26.2)
CHILD_SCALE = 0.7

def rrect(cx, cz, w, d, rot, px, pz, pad):
    """is point inside rotated rectangle (expanded by pad)"""
    c, s = math.cos(rot), math.sin(rot); dx, dz = px - cx, pz - cz; lx = c * dx - s * dz; lz = s * dx + c * dz   # inverse of yaw rotation
    return abs(lx) <= w / 2 + pad and abs(lz) <= d / 2 + pad
def smooth_path(pts, closed=True, rounds=3, step=0.35):
    """Chaikin corner cutting (rounds times) then resample at constant arc length 'step'"""
    P = [tuple(p) for p in pts]
    for _ in range(rounds):
        Q = []; n = len(P)
        for i in range(n if closed else n - 1):
            a, b = P[i], P[(i + 1) % n]; Q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        P = Q
    if closed: P.append(P[0])
    out = [P[0]]; acc = 0.0; i = 0; cur = P[0]; L = 0.0
    seg = [math.hypot(P[k + 1][0] - P[k][0], P[k + 1][1] - P[k][1]) for k in range(len(P) - 1)]; total = sum(seg); n = max(8, int(total / step)); d = total / n
    k = 0; pos = 0.0; res = [P[0]]
    for j in range(1, n + 1):
        target = j * d
        while k < len(seg) - 1 and pos + seg[k] < target: pos += seg[k]; k += 1
        u = (target - pos) / (seg[k] or 1); a, b = P[k], P[k + 1]; res.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    return res, total
def obstacles():
    obs = []
    for h in HOUSES + [INN, CHURCH, SMITHY]: obs.append(("rect", h[0], h[2], h[3], h[4], h[5], h[7]))
    return obs
def check_paths(verbose=True):
    bad = []
    for p in PEOPLE:
        if isinstance(p[5], list):
            pts, tot = smooth_path(p[5], closed=True)
            for (x, z) in pts:
                for o in obstacles():
                    if rrect(o[2], o[3], o[4], o[5], o[6], x, z, 0.8): bad.append((p[0], "inside", o[1], round(x, 1), round(z, 1))); break
                if math.hypot(x - FOUNTAIN[0], z - FOUNTAIN[1]) < FOUNTAIN[2] + 0.9: bad.append((p[0], "fountain", round(x, 1), round(z, 1)))
                for (lx, lz) in LAMPS:
                    if math.hypot(x - lx, z - lz) < 0.6: bad.append((p[0], "lamp", lx, lz))
                for s in STALLS:
                    if rrect(s[2], s[3], 2.6, 1.8, s[4], x, z, 0.5): bad.append((p[0], "stall", s[0], round(x, 1), round(z, 1))); break
            if verbose: print(p[0], p[1], "path", round(tot), "m", "lap", round(tot / p[6]), "s")
    seen = set(); bad = [b for b in bad if not (b in seen or seen.add(b))]
    return bad
if __name__ == "__main__":
    bad = check_paths(); print("clearance violations:", len(bad)); [print(" ", b) for b in bad[:30]]
    (HERE / "data").mkdir(exist_ok=True)
    def b(h): return dict(id=h[0], name=h[1], x=h[2], z=h[3], w=h[4], d=h[5], h=h[6], rot=round(h[7], 5), wall=h[8], roof=h[9], role=h[10])
    people = []
    for p in PEOPLE:
        e = dict(id=p[0], name=p[1], role=p[2], arch=p[3], shirt=p[4][0], pants=p[4][1], scale=p[7] if isinstance(p[5], tuple) else p[7], note=p[8] if isinstance(p[5], list) else p[6] if False else None)
        if isinstance(p[5], list): e.update(path=[list(q) for q in p[5]], speed=p[6], note=p[8])
        else: e.update(pos=list(p[5]), face=p[6], note=p[8])
        people.append(e)
    d = dict(lat=LAT, lon=LON, houses=[b(h) for h in HOUSES + [INN, CHURCH, SMITHY]], people=people, stalls=[dict(id=s[0], name=s[1], x=s[2], z=s[3], rot=s[4]) for s in STALLS], plaza_r=PLAZA_R, fountain=list(FOUNTAIN), lamps=[list(l) for l in LAMPS], roads=[dict(pts=[list(q) for q in r[0]], w=r[1], kind=r[2]) for r in ROADS], flat_r=FLAT_R)
    (HERE / "data" / "town.json").write_text(json.dumps(d, indent=1)); print("town.json", len(d["houses"]), "buildings", len(d["people"]), "people")
