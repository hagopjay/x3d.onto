"""Finish the Cycles hero plates (Loom): scale caption, WebP copies, look gates and hero-receipt.json.

    /usr/bin/python3 -I hero_finish.py   (standard library + Pillow + numpy; paths are fixed below)

For each plate (wide 1600x900, tall 1080x1350) written by hero_render.py:
  1. look gates from proto/gates/lookgates.py: nonblack(), and node_recall() with every life's mid-point projected through the same camera
     (the X3D Wide Viewpoint; fieldOfView spans the smaller side). A control samples random points inside the glass disc, so a lit haze
     cannot pass for recall.
  2. the poster: the plate plus a caption strip that states the radial and angular scales (data rule: every scale is stated on screen),
     the counts (counted from the geometry file the build wrote from loom-view.json), the colour key and what is decoration.
  3. PNG and WebP of the poster and of the clean plate (the page's poster image wants no caption: the page states the scales itself).
  4. hero-receipt.json: sha256 of every input and output, Blender version, render settings and timings, gate numbers, graded claims.
"""
import hashlib, json, math, os, random, re, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # dynasty-loom/
HYPER = ROOT + '/hyper'
HERO = HYPER + '/hero'
OUT = HYPER + '/out'
GEO = OUT + '/rothschild.geometry.json'
POCKET = OUT + '/pocket-rothschild.x3d'
FONT = ROOT + '/x3d/vendor/fonts/UbuntuMono-R.ttf'
GATES = ROOT + '/gates'
HI_THR = 0.5
sys.path.insert(0, GATES)
import lookgates  # noqa: E402  (our own gate module, read-only)


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def quat_axis_angle(ax, ang):
    n = math.sqrt(sum(a * a for a in ax)); x, y, z = (a / n for a in ax)
    c, s = math.cos(ang), math.sin(ang); t = 1 - c
    return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]


def projector(st):
    vp = st['viewpoint_pose']; W, H = st['resolution']
    R = quat_axis_angle(vp['orientation'][:3], vp['orientation'][3]); pos = vp['position']
    span = H if st['sensor_fit'] == 'VERTICAL' else W
    f = (span / 2) / math.tan(st['fov'] / 2)
    def proj(p):
        d = [p[i] - pos[i] for i in range(3)]
        c = [sum(R[r][k] * d[r] for r in range(3)) for k in range(3)]   # R^T d: world -> camera
        if c[2] >= -1e-6:
            return None
        return (W / 2 + f * c[0] / -c[2], H / 2 - f * c[1] / -c[2])
    return proj


def counts(geo):
    lives = {pl['ids'][0] for pl in geo['polylines'] if pl['kind'] == 'life'}
    unions = {tuple(sorted(pl['ids'])) for pl in geo['polylines'] if pl['kind'] in ('union', 'close')}
    est = sum(1 for pl in geo['polylines'] if any(pl['estimated']))
    return len(lives), len(unions), est


def gates(img, st, geo):
    proj = projector(st)
    pts = []
    for pl in geo['polylines']:
        if pl['kind'] != 'life':
            continue
        mid = pl['points'][len(pl['points']) // 2]
        q = proj(mid)
        if q:
            pts.append((pl['ids'][0], q[0], q[1]))
    rec = lookgates.node_recall(img, pts, radius=3, thr=0.15)
    # control: random points inside the projected glass disc (same radius and threshold)
    c = proj((0.0, 0.0, 0.0))
    vp = st['viewpoint_pose']; dist = math.dist(vp['position'], (0, 0, 0)); W, H = st['resolution']
    span = H if st['sensor_fit'] == 'VERTICAL' else W
    rad_px = (span / 2) / math.tan(st['fov'] / 2) * 1.1 / math.sqrt(dist * dist - 1.21)
    rng = random.Random(11); ctrl = []
    while len(ctrl) < 400:
        a = rng.random() * 2 * math.pi; r = rad_px * math.sqrt(rng.random())
        ctrl.append(('ctrl', c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    con = lookgates.node_recall(img, ctrl, radius=3, thr=0.15)
    # the haze lights most of the disc at the gate's 0.15, so also ask at a threshold the haze does not reach
    hi = lookgates.node_recall(img, pts, radius=3, thr=HI_THR); hc = lookgates.node_recall(img, ctrl, radius=3, thr=HI_THR)
    nb = lookgates.nonblack(img)
    return dict(nonblack=nb, node_recall=dict(onscreen=rec['onscreen'], seen=rec['seen'], recall=rec['recall'], missed=rec['missed']),
                control_random_in_glass=dict(n=con['onscreen'], recall=con['recall']),
                strict=dict(thr=HI_THR, recall=hi['recall'], seen=hi['seen'], control=hc['recall']), glass_disc_px=dict(centre=[round(c[0], 1), round(c[1], 1)], radius=round(rad_px, 1)))


def caption(plate, lines, title):
    im = plate.convert('RGBA'); W, H = im.size
    u = W / 1600 if W >= H else W / 1080
    fs, ft = max(13, round(15 * u)), max(16, round(21 * u))
    f = ImageFont.truetype(FONT, fs); fT = ImageFont.truetype(FONT, ft)
    pad = round(22 * u); lh = round(fs * 1.38)
    # wrap each line to the strip width
    maxw = W - 2 * pad; wrapped = []
    for ln in lines:
        words, cur = ln.split(' '), ''
        for w_ in words:
            t = (cur + ' ' + w_).strip()
            if f.getlength(t) <= maxw:
                cur = t
            else:
                wrapped.append(cur); cur = w_
        wrapped.append(cur)
    strip = pad + round(ft * 1.5) + lh * len(wrapped) + pad
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    ramp = round(70 * u)
    for i in range(strip + ramp):                           # dark under the text, fading out above it
        a = 0.80 if i <= strip else 0.80 * (1 - (i - strip) / ramp)
        d.line([(0, H - 1 - i), (W, H - 1 - i)], fill=(6, 5, 14, int(255 * a)))
    im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
    y = H - strip + pad
    d.text((pad, y), title, font=fT, fill=(226, 196, 132, 255)); y += round(ft * 1.5)
    for ln in wrapped:
        d.text((pad, y), ln, font=f, fill=(222, 216, 204, 255)); y += lh
    return im.convert('RGB'), dict(font_px=fs, title_px=ft, strip_px=strip, lines=len(wrapped))


def cpu_time(path):
    try:
        t = open(path).read()
    except OSError:
        return None
    def sec(k):
        m = re.search(r'^%s\s+(\d+)m([\d.]+)s' % k, t, re.M)
        return round(int(m.group(1)) * 60 + float(m.group(2)), 1) if m else None
    return dict(wall_s=sec('real'), cpu_user_s=sec('user'), cpu_sys_s=sec('sys'))


def claims(rc):
    w, t = rc['renders']['wide'], rc['renders']['tall']; gw, gt = rc['gates']['wide'], rc['gates']['tall']
    tw, tt = w['timing'] or {}, t['timing'] or {}
    return [
        {'grade': 'Confirmed', 'tool': 'Blender %s Cycles CPU (hero_render.py stats)' % w['blender'],
         'claim': 'both plates rendered from the build geometry unedited: %d fiber objects (cores + glow sheaths), %d polyline segments, %d dash pieces for estimated years; '
                  '%d triangles after curve evaluation; %d samples, adaptive %.3f, OpenImageDenoise; AgX "%s"; Bloom + Fog Glow in the compositor (CPU device)'
                  % (w['fiber_objects'], w['fiber_segments'], w['dash_pieces'], w['scene_triangles'], w['samples'], w['adaptive_threshold'], w['look'])},
        {'grade': 'Confirmed', 'tool': 'bash time around the bpy process (4 threads)',
         'claim': 'wide 1600x900: %s s wall, %s s CPU user; tall 1080x1350: %s s wall, %s s CPU user (target: under about 10 minutes of CPU each)'
                  % (tw.get('wall_s'), tw.get('cpu_user_s'), tt.get('wall_s'), tt.get('cpu_user_s'))},
        {'grade': 'Confirmed', 'tool': 'proto/gates/lookgates.py nonblack()',
         'claim': 'neither plate is black: lit share %.3f / %.3f, p99 luma %.3f / %.3f (wide / tall)'
                  % (gw['nonblack']['lit'], gt['nonblack']['lit'], gw['nonblack']['p99'], gt['nonblack']['p99'])},
        {'grade': 'Likely', 'tool': 'proto/gates/lookgates.py node_recall() with each life mid-point projected through the Wide camera; control = 400 random points in the glass disc',
         'claim': 'life recall at the gate threshold 0.15: %d/%d (wide), %d/%d (tall), but random points in the glass score %.2f / %.2f there (the haze is lit); '
                  'at luma %.2f recall is %.2f / %.2f against a control of %.2f / %.2f, so the lives are drawn where the data puts them; luma recall cannot tell one thread from a neighbour'
                  % (gw['node_recall']['seen'], gw['node_recall']['onscreen'], gt['node_recall']['seen'], gt['node_recall']['onscreen'],
                     gw['control_random_in_glass']['recall'], gt['control_random_in_glass']['recall'], HI_THR,
                     gw['strict']['recall'], gt['strict']['recall'], gw['strict']['control'], gt['strict']['control'])},
        {'grade': 'Likely', 'tool': 'Read of both PNGs (my eye)',
         'claim': 'reads as the Wide shot of the page: dye-coloured threads with hot cores around the founders\' glow, a clear glass with a blue rim and faint 50-year time shells, '
                  'the gold armillary, a dark violet nebula; depth of field softens the near threads and turns stars into small bokeh discs'},
        {'grade': 'Confirmed', 'tool': 'hero_render.py source',
         'claim': 'still-only departures from the page look, stated: thin glass as Fresnel(1.45) between pass-through and a mirror on the outside only; rim (0.55, 0.68, 1.0) x (0.9 F^7 + 0.012 F^2); '
                  'shell limbs raised to 0.3 exp(-cos^2/0.006); gold tubes drawn 2x thick; a glossy-only warm dome and a light-linked softbox so the gold reads; caption strip states the scales'},
        {'grade': 'Suspected', 'tool': 'Read at full size',
         'claim': 'an estimated year\'s dashes (4-5 px on at 1600 px) are hard to see at poster size; the caption says what dashing means'},
    ]


def main():
    geo = json.load(open(GEO))
    n_lives, n_unions, n_est = counts(geo)
    scale = geo['mapping']['lines'][0]
    lines = [
        '%d lives, %d marriages (counted from the build\'s geometry of loom-view.json). Red = Rothschild descent, ecru = in-law; '
        'a dashed, dimmer thread is an estimated year (%d threads).' % (n_lives, n_unions, n_est),
        scale + ' ' + geo['mapping']['lines'][1],
        'Rendered in Blender Cycles from the Wide shot. The gold rings and the nebula are decoration and carry no data.',
    ]
    title = 'DYNASTY HYPERSPHERE  ·  %s' % geo['family'].replace('_', '-').upper()
    receipt = {'what': 'Cycles hero still of the dynasty hypersphere (Rothschild): poster, docs and sharing',
               'generator': {'render': HERO + '/hero_render.py', 'finish': HERO + '/hero_finish.py'},
               'inputs': {}, 'outputs': {}, 'renders': {}, 'gates': {}}
    for p in (GEO, POCKET, FONT, HERO + '/hero_render.py', HERO + '/hero_finish.py', GATES + '/lookgates.py'):
        receipt['inputs'][p] = sha(p)
    for shot in ('wide', 'tall'):
        st = json.load(open(HERO + '/final/stats-%s.json' % shot))
        plate_p = HERO + '/final/plate-%s.png' % shot
        receipt['inputs'][plate_p] = sha(plate_p)
        receipt['inputs'][HERO + '/final/stats-%s.json' % shot] = sha(HERO + '/final/stats-%s.json' % shot)
        plate = Image.open(plate_p).convert('RGB')
        g = gates(np.asarray(plate), st, geo)
        poster, cap = caption(plate, lines, title)
        outs = {}
        for name, im in (('poster-%s' % shot, poster), ('poster-%s-plate' % shot, plate)):
            png, webp = OUT + '/' + name + '.png', OUT + '/' + name + '.webp'
            im.save(png, optimize=True); im.save(webp, quality=90, method=6)
            outs[name] = [png, webp]
            for p in (png, webp):
                receipt['outputs'][p] = dict(sha256=sha(p), bytes=os.path.getsize(p), size=list(im.size))
        g['poster_nonblack'] = lookgates.nonblack(np.asarray(poster))
        receipt['gates'][shot] = g
        st['timing'] = cpu_time(HERO + '/final/time-%s.txt' % shot)
        st['caption'] = cap
        receipt['renders'][shot] = st
    receipt['caption_lines'] = [title] + lines
    receipt['claims'] = claims(receipt)
    receipt['blender'] = receipt['renders']['wide']['blender'] + ' (bpy module, ' + os.environ.get('LOOM_BPY_VENV', 'venv-bpy') + ')'
    receipt['pillow'] = Image.__version__ if hasattr(Image, '__version__') else __import__('PIL').__version__
    json.dump(receipt, open(OUT + '/hero-receipt.json', 'w'), indent=1, sort_keys=True)
    for shot in ('wide', 'tall'):
        g = receipt['gates'][shot]; t = receipt['renders'][shot]['timing']
        print(shot, 'nonblack', g['nonblack']['ok'], 'lit %.3f p99 %.3f' % (g['nonblack']['lit'], g['nonblack']['p99']),
              'recall %d/%d=%.3f' % (g['node_recall']['seen'], g['node_recall']['onscreen'], g['node_recall']['recall']),
              'control %.3f' % g['control_random_in_glass']['recall'], 'strict', g['strict'], 'timing', t)


main()
