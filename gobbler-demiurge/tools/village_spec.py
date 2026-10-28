"""Numbers the village, the Earth and the zoom ladder share (the Blender scripts, layers.py and the page agree on them).

Two scales meet in one scene. Earth is drawn 0.1 scene units in radius. The village sits on its surface at the point that faces the Sun and is drawn at SCALE
scene units per metre, which makes the planet 250 m in radius at village scale: the village is drawn about 25,000 times larger than the real ratio would show,
so you can see it from orbit. The page says so on the stops and in the scale readout.
"""
import math

SUN = (6.5, -2.6, 0.4)                    # the heart (same as layers.SUN)
EARTH_DIST = 2.5                          # Earth stands this far from the Sun, inside the Dyson ribcage (radius 3.3)
EARTH_DIR = (0.15, -0.30, 0.94)           # from the Sun toward the Face camera side, so the zoom from the Face view meets it
R_EARTH = 0.1                             # scene units
SCALE = 4.0e-4                            # scene units per metre of village
R_PLANET = R_EARTH / SCALE                # 250 m at village scale
MOON_R = 0.027                            # 0.273 of Earth's radius, as in life
MOON_ORBIT = 0.30                         # compressed from about 60 Earth radii to 3 so that Earth and Moon fit one frame
PLAZA_R = 16.0                            # metres
FOUNTAIN_R = 4.5
MAST_H = 60.0                             # the tether mast at the fountain: the foot of the tether
VILLAGE_R = 80.0
HUMAN_H = 1.75                            # metres


def norm(a):
    n = math.sqrt(sum(x * x for x in a)) or 1.0
    return tuple(x / n for x in a)


def earth_pos():
    d = norm(EARTH_DIR)
    return tuple(SUN[i] + EARTH_DIST * d[i] for i in range(3))


def site_frame():
    """(site, up, east, north): the village point on Earth's surface facing the Sun, its up (toward the Sun) and two tangent axes"""
    e = earth_pos(); up = norm(tuple(SUN[i] - e[i] for i in range(3)))
    ref = (0, 1, 0) if abs(up[1]) < 0.9 else (1, 0, 0)
    east = norm((ref[1] * up[2] - ref[2] * up[1], ref[2] * up[0] - ref[0] * up[2], ref[0] * up[1] - ref[1] * up[0]))
    north = (up[1] * east[2] - up[2] * east[1], up[2] * east[0] - up[0] * east[2], up[0] * east[1] - up[1] * east[0])
    site = tuple(e[i] + R_EARTH * up[i] for i in range(3))
    return site, up, east, north
