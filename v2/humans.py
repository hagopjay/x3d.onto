"""H-Anim style humanoids for the village: rigid-segment mannequins (LOA-1-like, 17 joints), procedural gait / gesture keyframes.
Joint centres are absolute humanoid coordinates (feet at y=0, facing +z, left = +x), as in H-Anim 1.1 / 2.0 example files.
Pure Python; make_v2.py turns this into HAnimHumanoid / HAnimJoint / HAnimSegment nodes through x3d_mcp."""
import math
from meshkit import Mesh

JOINTS = [  # name, parent, centre
 ("humanoid_root", None, (0, 0.95, 0)), ("sacroiliac", "humanoid_root", (0, 0.98, 0)), ("vl5", "sacroiliac", (0, 1.10, 0)), ("skullbase", "vl5", (0, 1.55, 0)),
 ("l_shoulder", "vl5", (0.19, 1.43, 0)), ("l_elbow", "l_shoulder", (0.19, 1.15, 0)), ("l_radiocarpal", "l_elbow", (0.19, 0.88, 0)),
 ("r_shoulder", "vl5", (-0.19, 1.43, 0)), ("r_elbow", "r_shoulder", (-0.19, 1.15, 0)), ("r_radiocarpal", "r_elbow", (-0.19, 0.88, 0)),
 ("l_hip", "humanoid_root", (0.09, 0.92, 0)), ("l_knee", "l_hip", (0.09, 0.50, 0)), ("l_talocrural", "l_knee", (0.09, 0.09, 0)),
 ("r_hip", "humanoid_root", (-0.09, 0.92, 0)), ("r_knee", "r_hip", (-0.09, 0.50, 0)), ("r_talocrural", "r_knee", (-0.09, 0.09, 0)),
]
# segment name -> (joint, [(geometry key, colour class)])
SEGMENTS = {
 "sacrum": ("humanoid_root", [("pelvis", "pants")]), "vl5": ("vl5", [("torso", "shirt"), ("neck", "skin")]), "skull": ("skullbase", [("head", "skin"), ("eyes", "eye")]),
 "l_upperarm": ("l_shoulder", [("uparm_l", "shirt")]), "l_forearm": ("l_elbow", [("farm_l", "sleeve")]), "l_hand": ("l_radiocarpal", [("hand_l", "skin")]),
 "r_upperarm": ("r_shoulder", [("uparm_r", "shirt")]), "r_forearm": ("r_elbow", [("farm_r", "sleeve")]), "r_hand": ("r_radiocarpal", [("hand_r", "skin")]),
 "l_thigh": ("l_hip", [("thigh_l", "pants")]), "l_calf": ("l_knee", [("calf_l", "pants")]), "l_hindfoot": ("l_talocrural", [("foot_l", "shoes")]),
 "r_thigh": ("r_hip", [("thigh_r", "pants")]), "r_calf": ("r_knee", [("calf_r", "pants")]), "r_hindfoot": ("r_talocrural", [("foot_r", "shoes")]),
}
ACCESSORIES = {  # geometry key -> (segment, class)
 "hair": ("skull", "hair"), "beard": ("skull", "hair"), "hat_top": ("skull", "hat"), "hat_cap": ("skull", "hat"), "scarf": ("skull", "scarf"), "braid": ("skull", "hair"), "apron": ("vl5", "apron"), "collar": ("vl5", "collar"),
 "hammer": ("r_hand", "tool"), "tongs": ("l_hand", "tool"), "bag": ("vl5", "leather"),
}
def geometries():
    """neutral geometry (no vertex colours) per key, absolute humanoid coordinates"""
    G = {}
    def mesh(key): m = Mesh(key); G[key] = m; return m
    m = mesh("pelvis"); m.lathe([(0.10, 0.84), (0.15, 0.90), (0.165, 0.98), (0.15, 1.06), (0.135, 1.10)], n=14, ex=1.0, ez=0.66, cap_top=False, cap_bottom=True)
    m = mesh("torso"); m.lathe([(0.135, 1.06), (0.145, 1.16), (0.158, 1.28), (0.185, 1.38), (0.19, 1.45), (0.10, 1.50), (0.05, 1.52)], n=16, ex=1.0, ez=0.62, cap_top=True, cap_bottom=False)
    m = mesh("neck"); m.tube((0, 1.47, 0), (0, 1.60, 0.012), 0.052, 0.046, n=10, color=None)
    m = mesh("head"); m.lathe([(0.0, 1.565), (0.055, 1.575), (0.092, 1.61), (0.104, 1.665), (0.100, 1.715), (0.080, 1.76), (0.045, 1.782), (0.0, 1.79)], n=18, ex=0.92, ez=1.04, cap_top=False, cap_bottom=False)
    with m.at(0, 1.66, 0.098): m.cone(0, -0.02, 0, 0.018, 0.05, n=6)
    m = mesh("eyes")
    for sx in (-1, 1): m.icosphere((sx * 0.036, 1.688, 0.087), 0.0125, 0, color=None)
    m = mesh("hair"); m.lathe([(0.108, 1.69), (0.113, 1.72), (0.098, 1.765), (0.062, 1.795), (0.0, 1.805)], n=18, ex=0.95, ez=1.06, cap_top=False, cap_bottom=False)
    with m.at(0, 0, -0.03): m.lathe([(0.105, 1.69), (0.108, 1.62), (0.09, 1.58)], n=14, ex=0.95, ez=0.8, cap_top=False, cap_bottom=False)  # hair at the nape
    m = mesh("beard"); m.lathe([(0.0, 1.51), (0.055, 1.52), (0.09, 1.56), (0.103, 1.62), (0.094, 1.655)], n=14, ex=0.9, ez=0.9, cap_top=False, cap_bottom=False)
    with m.at(0, 0, 0.0): m.icosphere((0, 1.64, 0.08), 0.03, 1, squash=(1.8, 0.4, 0.6))
    m = mesh("hat_top"); m.lathe([(0.15, 1.755), (0.115, 1.758), (0.1, 1.77), (0.1, 1.93), (0.0, 1.935)], n=18, cap_top=False, cap_bottom=False)
    m = mesh("hat_cap"); m.lathe([(0.114, 1.725), (0.12, 1.76), (0.1, 1.80), (0.0, 1.81)], n=18, ex=1.0, ez=1.05, cap_top=False, cap_bottom=False)
    with m.at(0, 1.735, 0.1): m.box(0, 0, 0.03, 0.19, 0.012, 0.08, tile=1.0)
    m = mesh("scarf"); m.lathe([(0.112, 1.665), (0.118, 1.71), (0.104, 1.765), (0.06, 1.795), (0.0, 1.805)], n=18, ex=0.97, ez=1.1, cap_top=False, cap_bottom=False)
    m.lathe([(0.07, 1.50), (0.085, 1.55), (0.075, 1.58)], n=12, cap_top=False, cap_bottom=False)
    m = mesh("braid"); m.tube((0, 1.70, -0.1), (0.0, 1.45, -0.12), 0.026, 0.02, n=7)
    m = mesh("apron"); m.box(0, 1.03, 0.115, 0.30, 0.56, 0.035, tile=1.0); m.box(0, 1.34, 0.06, 0.05, 0.12, 0.05, tile=1.0)
    m = mesh("collar"); m.lathe([(0.062, 1.50), (0.072, 1.525), (0.060, 1.545)], n=12, cap_top=False, cap_bottom=False)
    m = mesh("bag"); m.box(-0.2, 0.96, -0.02, 0.1, 0.22, 0.2, tile=1.0); m.tube((-0.19, 1.43, 0.0), (0.0, 1.20, 0.12), 0.01, 0.01, n=5)
    for side, sx in (("l", 1), ("r", -1)):
        m = mesh(f"uparm_{side}"); m.tube((sx * 0.19, 1.45, 0), (sx * 0.19, 1.15, 0), 0.056, 0.045, n=10)
        m = mesh(f"farm_{side}"); m.tube((sx * 0.19, 1.15, 0), (sx * 0.19, 0.89, 0), 0.043, 0.033, n=10)
        m = mesh(f"hand_{side}"); m.lathe([(0.0, 0.76), (0.022, 0.77), (0.034, 0.80), (0.036, 0.85), (0.03, 0.90)], n=10, ex=1.0, ez=0.6, cap_top=True, cap_bottom=False)
        with m.at(sx * 0.19, 0, 0): m.tube((0.0, 0.88, 0.02), (0.0, 0.82, 0.05), 0.01, 0.01, n=5)
        m = mesh(f"thigh_{side}"); m.tube((sx * 0.09, 0.95, 0), (sx * 0.09, 0.50, 0), 0.085, 0.056, n=12)
        m = mesh(f"calf_{side}"); m.tube((sx * 0.09, 0.50, 0), (sx * 0.09, 0.10, 0), 0.054, 0.04, n=10)
        m = mesh(f"foot_{side}")
        with m.at(sx * 0.09, 0, 0.05):
            m.lathe([(0.04, 0.0), (0.052, 0.03), (0.05, 0.08), (0.04, 0.12)], n=10, ex=1.0, ez=2.4, cap_top=True, cap_bottom=True)
    m = mesh("hammer"); m.tube((-0.19, 0.84, 0.03), (-0.19, 1.06, 0.2), 0.016, 0.014, n=6); m.box(-0.19, 1.08, 0.215, 0.07, 0.06, 0.16, tile=1.0)
    m = mesh("tongs"); m.tube((0.19, 0.84, 0.03), (0.19, 0.92, 0.38), 0.012, 0.01, n=6)
    return G
ACC_FOR = {  # person id -> accessory keys
 "P01": ["hair", "apron"], "P02": ["hat_cap", "bag"], "P03": ["hair", "braid"], "P04": ["hat_top", "bag", "collar"], "P05": ["hair", "scarf", "apron"], "P06": ["hat_cap"], "P07": ["scarf"], "P08": ["hair", "beard", "apron", "hammer", "tongs"],
 "P09": ["hair"], "P10": ["hair", "beard"], "P11": ["collar"], "P12": ["hat_cap"],
}
PALETTE = {
 "skin": {"P01": (0.93, 0.76, 0.64), "P02": (0.85, 0.66, 0.52), "P03": (0.95, 0.80, 0.68), "P04": (0.78, 0.58, 0.45), "P05": (0.90, 0.72, 0.6), "P06": (0.7, 0.5, 0.38), "P07": (0.62, 0.42, 0.3), "P08": (0.78, 0.57, 0.45), "P09": (0.94, 0.78, 0.66), "P10": (0.84, 0.64, 0.5), "P11": (0.9, 0.74, 0.62), "P12": (0.73, 0.52, 0.4)},
 "hair": {"P01": (0.25, 0.14, 0.08), "P02": (0.35, 0.25, 0.15), "P03": (0.85, 0.65, 0.3), "P04": (0.45, 0.45, 0.47), "P05": (0.55, 0.3, 0.15), "P06": (0.2, 0.2, 0.2), "P07": (0.15, 0.1, 0.1), "P08": (0.6, 0.6, 0.62), "P09": (0.12, 0.1, 0.08), "P10": (0.4, 0.28, 0.18), "P11": (0.8, 0.8, 0.82), "P12": (0.3, 0.2, 0.12)},
}
COLORS = {"red": (0.7, 0.18, 0.15), "brick": (0.64, 0.25, 0.18), "navy": (0.12, 0.17, 0.3), "ochre": (0.78, 0.58, 0.2), "brown": (0.38, 0.25, 0.15), "yellow": (0.92, 0.78, 0.2), "teal": (0.1, 0.45, 0.48), "grey": (0.5, 0.5, 0.52), "charcoal": (0.2, 0.2, 0.22),
          "blue": (0.2, 0.35, 0.7), "green": (0.22, 0.5, 0.25), "tan": (0.65, 0.55, 0.38), "purple": (0.5, 0.2, 0.55), "leather": (0.45, 0.3, 0.18), "dark": (0.16, 0.14, 0.13), "orange": (0.88, 0.4, 0.12), "black": (0.07, 0.07, 0.08), "olive": (0.4, 0.42, 0.2), "white": (0.93, 0.93, 0.9)}
ACC_COLOR = {"hat": (0.2, 0.17, 0.15), "scarf": (0.75, 0.2, 0.25), "apron": (0.86, 0.84, 0.78), "collar": (0.95, 0.95, 0.95), "tool": (0.28, 0.28, 0.3), "leather": (0.4, 0.27, 0.16), "eye": (0.03, 0.03, 0.04), "shoes": (0.12, 0.09, 0.07)}

D2R = math.pi / 180.0
def ax(axis, ang): return [axis[0], axis[1], axis[2], round(ang, 5)]
RX = lambda a: ax((1, 0, 0), a); RY = lambda a: ax((0, 1, 0), a); RZ = lambda a: ax((0, 0, 1), a)
def bump(t, c, w):
    d = (t - c + 0.5) % 1.0 - 0.5; return math.exp(-(d / w) ** 2)
def walk_keys(N=16):
    """gait cycle: dict joint -> list of rotations (N+1 keys, closed), plus root bob / sway positions.  Angles in radians; forward swing = negative x rotation (humanoid faces +z)."""
    K = {}; ts = [i / N for i in range(N + 1)]
    def leg(side, ph):
        sign = 1
        hip = [RX(-(8 + 24 * math.cos(2 * math.pi * (t + ph))) * D2R) for t in ts]
        knee = [RX((6 + 52 * bump(t + ph, 0.72, 0.13) + 14 * bump(t + ph, 0.14, 0.09)) * D2R) for t in ts]
        ank = [RX((-10 * math.sin(2 * math.pi * (t + ph - 0.1)) - 8 * bump(t + ph, 0.62, 0.08)) * D2R) for t in ts]
        K[f"{side}_hip"] = hip; K[f"{side}_knee"] = knee; K[f"{side}_talocrural"] = ank
    leg("l", 0.0); leg("r", 0.5)
    def arm(side, ph, sx):
        sh = [RX(-(3 + 22 * math.cos(2 * math.pi * (t + ph))) * D2R) for t in ts]
        el = [RX(-(16 + 12 * (0.5 + 0.5 * math.cos(2 * math.pi * (t + ph + 0.05)))) * D2R) for t in ts]
        K[f"{side}_shoulder"] = [ax((0.2, 0.0, sx * 0.1) if False else (1, 0, 0), s_[3]) for s_ in sh]; K[f"{side}_elbow"] = el
    arm("l", 0.5, 1); arm("r", 0.0, -1)
    K["vl5"] = [RY(0.10 * math.sin(2 * math.pi * t)) for t in ts]; K["sacroiliac"] = [RY(-0.10 * math.sin(2 * math.pi * t)) for t in ts]
    K["skullbase"] = [RY(-0.03 * math.sin(2 * math.pi * t)) for t in ts]
    K["_root_pos"] = [[round(0.012 * math.sin(2 * math.pi * t), 4), round(0.95 - 0.026 * (0.5 + 0.5 * math.cos(4 * math.pi * t)) + 0.0, 4), 0.0] for t in ts]
    return ts, K

def idle_keys(kind, seed, N=24):
    """slow idle / gesture loops; returns (period_seconds, ts, dict joint -> rotations)"""
    import random; rng = random.Random(seed); ts = [i / N for i in range(N + 1)]; K = {}
    per = {"talker": 7.0 + rng.uniform(-1, 1.5), "listener": 8.0 + rng.uniform(0, 2), "greeter": 6.4, "smith": 1.4}[kind]
    ph = rng.uniform(0, 1)
    def S(t, f=1, p=0): return math.sin(2 * math.pi * (f * t + p))
    K["vl5"] = [RX(0.02 * S(t, 2, ph)) for t in ts]
    K["sacroiliac"] = [RY(0.03 * S(t, 1, ph + 0.2)) for t in ts]
    K["_root_pos"] = [[round(0.012 * S(t, 1, ph), 4), 0.95, 0.0] for t in ts]
    for s_ in ("l", "r"):
        K[f"{s_}_hip"] = [RX(0.0) for t in ts]; K[f"{s_}_knee"] = [RX(0.03 + 0.02 * S(t, 1, ph)) for t in ts]; K[f"{s_}_talocrural"] = [RX(0.0) for t in ts]
    if kind == "talker":
        K["skullbase"] = [RY(0.28 * S(t, 1, ph) + 0.1 * S(t, 3, ph)) if True else None for t in ts]
        K["r_shoulder"] = [RX(-(0.35 + 0.28 * max(0, S(t, 2, ph)) * (1 if (int(t * N) % 12) < 8 else 0.3))) for t in ts]
        K["r_elbow"] = [RX(-(0.9 + 0.45 * S(t, 2, ph + 0.3))) for t in ts]
        K["l_shoulder"] = [RX(-(0.08 + 0.05 * S(t, 1, ph))) for t in ts]; K["l_elbow"] = [RX(-(0.25 + 0.1 * S(t, 1, ph))) for t in ts]
    elif kind == "listener":
        K["skullbase"] = [ax((0.3, 1, 0), 0.12 * S(t, 1, ph) + 0.0) if False else RX(0.07 * max(0, S(t, 3, ph))) for t in ts]
        K["r_shoulder"] = [RX(-0.10) for t in ts]; K["r_elbow"] = [RX(-(0.3 + 0.05 * S(t, 1, ph))) for t in ts]
        K["l_shoulder"] = [RX(-0.55) for t in ts]; K["l_elbow"] = [RX(-(1.3 + 0.05 * S(t, 2, ph))) for t in ts]
    elif kind == "greeter":
        wave = [max(0.0, min(1.0, 1.8 * math.sin(math.pi * min(1.0, t / 0.55)))) for t in ts]   # raise/lower in the first 55 % of the cycle
        K["r_shoulder"] = [RZ(-(2.45 * w_)) if w_ > 0.0 else RX(-0.05) for w_ in wave]
        K["r_elbow"] = [RZ(-(0.5 + 0.35 * math.sin(2 * math.pi * 5 * t)) * w_) for t, w_ in zip(ts, wave)]
        K["l_shoulder"] = [RX(-(0.05 + 0.02 * S(t, 1, ph))) for t in ts]; K["l_elbow"] = [RX(-0.2) for t in ts]
        K["skullbase"] = [RY(0.35 * S(t, 1, ph) * 0.7) for t in ts]
    elif kind == "smith":
        # hammer: raise (0..0.55), hold, strike (0.62..0.7), rest
        def sh(t):
            if t < 0.55: u = t / 0.55; return -(0.5 + 1.25 * (u * u * (3 - 2 * u)))
            if t < 0.62: return -1.75
            if t < 0.70: u = (t - 0.62) / 0.08; return -(1.75 - 1.25 * u)
            return -(0.5 + 0.0)
        def el(t):
            if t < 0.55: u = t / 0.55; return -(1.0 + 0.35 * u)
            if t < 0.62: return -1.35
            if t < 0.70: u = (t - 0.62) / 0.08; return -(1.35 - 0.7 * u)
            return -(0.65 + 0.35 * (t - 0.7) / 0.3)
        K["r_shoulder"] = [RX(sh(t)) for t in ts]; K["r_elbow"] = [RX(el(t)) for t in ts]
        K["l_shoulder"] = [RX(-0.55 + 0.04 * S(t, 2, ph)) for t in ts]; K["l_elbow"] = [RX(-1.0) for t in ts]
        K["vl5"] = [RX(0.12 + 0.12 * (1 if 0.62 <= t < 0.72 else 0) - 0.08 * (1 if t < 0.55 else 0)) for t in ts]
        K["skullbase"] = [RX(0.15) for t in ts]
        K["_root_pos"] = [[0.0, 0.95 - (0.018 if 0.64 <= t < 0.74 else 0.0), 0.0] for t in ts]
    return per, ts, K
