"""Valid URDF robots, built programmatically with physically consistent inertia (solid cylinder/box formulas)."""
import math
def inertia_cyl(m, r, h): return (m * (3 * r * r + h * h) / 12, m * (3 * r * r + h * h) / 12, m * r * r / 2)
def link(name, m=1.0, r=0.05, h=0.3, color=None, root=False):
    ixx, iyy, izz = inertia_cyl(m, r, h)
    inert = "" if root else f'<inertial><origin xyz="0 0 {h/2}"/><mass value="{m}"/><inertia ixx="{ixx:.6f}" ixy="0" ixz="0" iyy="{iyy:.6f}" iyz="0" izz="{izz:.6f}"/></inertial>'
    col = f'<material name="m_{name}"><color rgba="{color}"/></material>' if color else ""
    return f'  <link name="{name}">{inert}<visual><origin xyz="0 0 {h/2}"/><geometry><cylinder radius="{r}" length="{h}"/></geometry>{col}</visual><collision><geometry><cylinder radius="{r}" length="{h}"/></geometry></collision></link>\n'
def joint(name, parent, child, typ="revolute", xyz="0 0 0.3", axis="0 0 1", lo=-1.57, hi=1.57, eff=10, vel=2):
    ax = f'<axis xyz="{axis}"/>' if typ in ("revolute", "continuous", "prismatic") else ""
    lim = f'<limit lower="{lo}" upper="{hi}" effort="{eff}" velocity="{vel}"/>' if typ in ("revolute", "prismatic") else ""
    return f'  <joint name="{name}" type="{typ}"><parent link="{parent}"/><child link="{child}"/><origin xyz="{xyz}" rpy="0 0 0"/>{ax}{lim}</joint>\n'
def robot(name, body): return f'<?xml version="1.0"?>\n<robot name="{name}">\n{body}</robot>\n'
def arm2():
    return robot("arm2", link("base", root=True, h=0.1, r=0.1) + link("l1", 2.0, .05, .4, "0.8 0.2 0.2 1") + link("l2", 1.0, .04, .3, "0.2 0.2 0.8 1") +
                 joint("j1", "base", "l1", xyz="0 0 0.1") + joint("j2", "l1", "l2", axis="0 1 0", xyz="0 0 0.4"))
def arm3_gripper():
    return robot("arm3g", link("base", root=True) + link("l1", 2.0) + link("l2", 1.5) + link("l3", 1.0) + link("fL", .1, .01, .05) + link("fR", .1, .01, .05) +
                 joint("j1", "base", "l1") + joint("j2", "l1", "l2", axis="0 1 0") + joint("j3", "l2", "l3", axis="0 1 0") +
                 joint("gL", "l3", "fL", "prismatic", axis="1 0 0", lo=0, hi=0.03) + joint("gR", "l3", "fR", "prismatic", axis="-1 0 0", lo=0, hi=0.03))
def mobile():
    return robot("rover", link("chassis", 8.0, .25, .15, root=False) + link("wl", .5, .08, .04) + link("wr", .5, .08, .04) + link("caster", .2, .03, .03) +
                 joint("jl", "chassis", "wl", "continuous", xyz="0 .2 0", axis="0 1 0") + joint("jr", "chassis", "wr", "continuous", xyz="0 -.2 0", axis="0 1 0") + joint("jc", "chassis", "caster", "fixed", xyz="-.2 0 0"))
def tree_humanoid():
    L = link("torso", 10, .12, .5) + link("head", 3, .08, .2) + "".join(link(n, 1.2, .04, .3) for n in ("uarmL", "larmL", "uarmR", "larmR", "ulegL", "llegL", "ulegR", "llegR"))
    J = joint("neck", "torso", "head", xyz="0 0 .5") + joint("shL", "torso", "uarmL", xyz="0 .12 .4", axis="0 1 0") + joint("elL", "uarmL", "larmL", axis="0 1 0") + \
        joint("shR", "torso", "uarmR", xyz="0 -.12 .4", axis="0 1 0") + joint("elR", "uarmR", "larmR", axis="0 1 0") + \
        joint("hipL", "torso", "ulegL", xyz="0 .06 0", axis="0 1 0") + joint("knL", "ulegL", "llegL", axis="0 1 0") + joint("hipR", "torso", "ulegR", xyz="0 -.06 0", axis="0 1 0") + joint("knR", "ulegR", "llegR", axis="0 1 0")
    return robot("humanoid", L + J)
def chain(n=6):
    L = link("base", root=True) + "".join(link(f"c{i}", 1.0 - i * .1) for i in range(1, n + 1))
    J = joint("q1", "base", "c1") + "".join(joint(f"q{i+1}", f"c{i}", f"c{i+1}", axis="0 1 0" if i % 2 else "0 0 1") for i in range(1, n))
    return robot("chain6", L + J)
def quad():
    L = link("body", 6, .25, .1) + "".join(link(f"{s}{k}", .8, .03, .2) for s in ("fl", "fr", "rl", "rr") for k in ("u", "d"))
    J = ""
    for s, xy in (("fl", ".15 .1 0"), ("fr", ".15 -.1 0"), ("rl", "-.15 .1 0"), ("rr", "-.15 -.1 0")):
        J += joint(s + "hip", "body", s + "u", xyz=xy, axis="0 1 0") + joint(s + "knee", s + "u", s + "d", xyz="0 0 .2", axis="0 1 0")
    return robot("quad", L + J)
CORPUS = {"arm2": arm2, "arm3_gripper": arm3_gripper, "mobile": mobile, "humanoid": tree_humanoid, "chain6": chain, "quad": quad}
