"""python3 -I measure.py DIR : the rendered colour at the middle of each face (probe) and of the point and line (probe-unlit), from frame-*.png. Needs Pillow."""
import sys, os, json
from PIL import Image
d = sys.argv[1] if len(sys.argv) > 1 else '.'
def px(name, pts):
    im = Image.open(os.path.join(d, 'frame-%s.png' % name)).convert('RGB'); W, H = im.size; s = (H / 2) / 3.728   # Viewpoint at z 9, fieldOfView 0.7854
    return {k: im.getpixel((int(W / 2 + x * s), int(H / 2 - y * s))) for k, (x, y) in pts.items()}
out = {'probe': {}, 'probe-unlit': px('probe-unlit', {'point (red Color)': (-2, 0), 'line (blue Color)': (1, 0)})}
for i, n in enumerate(['emissiveColor 1 1 1', 'emissiveColor 0.85', 'default Material', 'no Material']):
    out['probe'][n] = px('probe', {'red face': (-3 + 2 * i, -0.9), 'blue face': (-3 + 2 * i, 0.9)})
print(json.dumps(out, indent=1))
