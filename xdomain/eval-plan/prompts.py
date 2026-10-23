"""Task prompts with machine-checkable expectations (completeness without a judge). `expect` keys are minimum counts; the check is mechanical.
URDF expect: links, joints (dict type->min count). glTF expect: nodes, meshes, materials, animations, cameras."""
URDF = [
 # tier A
 ("U-A1", "A", "a single link named base_link: a box 0.2 x 0.1 x 0.1 m, mass 1 kg, no joints", dict(links=1, joints={})),
 ("U-A2", "A", "a planar two-link arm: base, upper arm 0.4 m, forearm 0.3 m, two revolute joints about the z axis with limits of plus and minus 1.5 rad", dict(links=3, joints={"revolute": 2})),
 ("U-A3", "A", "a rover: a chassis box and two continuous wheel joints on the left and right", dict(links=3, joints={"continuous": 2})),
 ("U-A4", "A", "a simple pendulum: a fixed pivot and a rod on one revolute joint, rod 0.5 m, mass 0.5 kg", dict(links=2, joints={"revolute": 1})),
 ("U-A5", "A", "a linear slider: a rail and a carriage on one prismatic joint travelling 0 to 0.5 m", dict(links=2, joints={"prismatic": 1})),
 ("U-A6", "A", "a three-link arm whose joints rotate about z, y and y", dict(links=4, joints={"revolute": 3})),
 # tier B
 ("U-B1", "B", "a six-degree-of-freedom arm with six revolute joints and a base", dict(links=7, joints={"revolute": 6})),
 ("U-B2", "B", "a parallel gripper: a palm and two mirrored prismatic fingers", dict(links=3, joints={"prismatic": 2})),
 ("U-B3", "B", "a mobile manipulator: a rover with two wheels and a two-link arm on top", dict(links=6, joints={"continuous": 2, "revolute": 2})),
 ("U-B4", "B", "a quadruped body with one leg of three revolute joints (hip abduction, hip, knee)", dict(links=4, joints={"revolute": 3})),
 ("U-B5", "B", "a differential-drive robot with a caster, and a lidar link fixed on top", dict(links=5, joints={"continuous": 2, "fixed": 2})),
 ("U-B6", "B", "a pan-tilt camera: a base, a pan revolute joint, a tilt revolute joint, and a fixed camera link", dict(links=4, joints={"revolute": 2, "fixed": 1})),
 # tier C
 ("U-C1", "C", "a humanoid upper body: torso, head, and two arms each with shoulder, upper arm and forearm joints (three degrees of freedom per arm)", dict(links=9, joints={"revolute": 6})),
 ("U-C2", "C", "a full quadruped: a body and four legs, each leg with three revolute joints", dict(links=13, joints={"revolute": 12})),
 ("U-C3", "C", "an excavator: base, swing joint, boom, stick and bucket", dict(links=5, joints={"revolute": 4})),
 ("U-C4", "C", "a hexapod with six legs of three revolute joints each", dict(links=19, joints={"revolute": 18})),
 ("U-C5", "C", "a four-wheel steering rover: four steering revolute joints and four continuous drive joints", dict(links=9, joints={"revolute": 4, "continuous": 4})),
 ("U-C6", "C", "a robotic hand: a palm and three fingers, each with three phalanges on revolute joints", dict(links=10, joints={"revolute": 9})),
 ("U-C7", "C", "a SCARA arm: two revolute joints, one prismatic joint and one final revolute joint", dict(links=5, joints={"revolute": 3, "prismatic": 1})),
 ("U-C8", "C", "a biped lower body: a pelvis and two legs of six revolute joints each", dict(links=13, joints={"revolute": 12})),
]
GLTF = [
 # tier A: no binary data
 ("G-A1", "A", "an empty scene with three nodes in a chain named root, child and grandchild, each translated by 1 along x from its parent", dict(nodes=3)),
 ("G-A2", "A", "a scene with a perspective camera node looking down the negative z axis from z = 5", dict(nodes=1, cameras=1)),
 ("G-A3", "A", "two sibling nodes named left and right under a root, left rotated 45 degrees about y using a unit quaternion", dict(nodes=3)),
 ("G-A4", "A", "a scene with an orthographic camera and a node with a non-uniform scale of 1, 2, 3", dict(nodes=2, cameras=1)),
 ("G-A5", "A", "a scene with two scenes in the file and the second one selected as default, each with one node", dict(nodes=2)),
 ("G-A6", "A", "a node using a 4x4 column-major matrix that translates by (2, 0, 0)", dict(nodes=1)),
 # tier B: embedded geometry
 ("G-B1", "B", "one triangle with positions (0,0,0), (1,0,0), (0,1,0) and a 16-bit index buffer, embedded as a base64 data URI", dict(nodes=1, meshes=1)),
 ("G-B2", "B", "a unit quad made of two triangles with indices, embedded buffer", dict(nodes=1, meshes=1)),
 ("G-B3", "B", "a unit cube with positions and normals, embedded buffer", dict(nodes=1, meshes=1)),
 ("G-B4", "B", "a triangle with a red PBR material (baseColorFactor 1,0,0,1, metallic 0)", dict(nodes=1, meshes=1, materials=1)),
 ("G-B5", "B", "a triangle with per-vertex colours red, green, blue via COLOR_0", dict(nodes=1, meshes=1)),
 ("G-B6", "B", "two triangles as two primitives of one mesh with two different materials", dict(nodes=1, meshes=1, materials=2)),
 # tier C: animation, extensions, textures
 ("G-C1", "C", "a triangle that moves 2 units along x and back over 2 seconds using a translation animation with LINEAR interpolation", dict(nodes=1, meshes=1, animations=1)),
 ("G-C2", "C", "a cube that rotates a full turn about y over 4 seconds using quaternion keyframes", dict(nodes=1, meshes=1, animations=1)),
 ("G-C3", "C", "a triangle whose scale pulses from 1 to 2 to 1 over 2 seconds", dict(nodes=1, meshes=1, animations=1)),
 ("G-C4", "C", "a parent node and a child cube, with the animation on the child's translation only", dict(nodes=2, meshes=1, animations=1)),
 ("G-C5", "C", "a triangle using KHR_materials_unlit, declared properly in extensionsUsed", dict(nodes=1, meshes=1, materials=1)),
 ("G-C6", "C", "a quad with UV coordinates and a baseColorTexture from this 1x1 PNG data URI: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", dict(nodes=1, meshes=1, materials=1)),
 ("G-C7", "C", "two cubes under one root, the root animated by rotation, both cubes sharing one mesh", dict(nodes=3, meshes=1, animations=1)),
 ("G-C8", "C", "a cube with a step-interpolated translation animation of three keyframes", dict(nodes=1, meshes=1, animations=1)),
]
def completeness_urdf(xml, expect):
    from lxml import etree
    try: r = etree.fromstring(xml.encode())
    except Exception: return False
    links = len(r.findall("link")); jt = {}
    for j in r.findall("joint"): jt[j.get("type")] = jt.get(j.get("type"), 0) + 1
    return links >= expect["links"] and all(jt.get(k, 0) >= v for k, v in expect["joints"].items())
def completeness_gltf(text, expect):
    import json
    try: d = json.loads(text)
    except Exception: return False
    n = lambda k: len(d.get(k, [])) if isinstance(d.get(k), list) else 0
    return n("nodes") >= expect.get("nodes", 0) and n("meshes") >= expect.get("meshes", 0) and n("materials") >= expect.get("materials", 0) and n("animations") >= expect.get("animations", 0) and n("cameras") >= expect.get("cameras", 0)
