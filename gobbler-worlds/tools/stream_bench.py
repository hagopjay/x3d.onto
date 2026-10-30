"""python3 -I gobbler-worlds/tools/stream_bench.py : what each nested world costs on the wire today, and what the streaming options would save, measured on the built files.

Reads data/worlds/ (made by build_worlds.py) and writes data/bird/stream-bench.json. Every number is computed here on the real files; nothing is fetched.
  text      each .x3d/.xml: raw, gzip -9, brotli -q 11
  mesh      the Sphinx close-up mesh (one IndexedTriangleSet, 80,000 vertices) as a plain quantised binary: 16-bit positions, 2 x 8-bit normals (octahedral),
            8-bit colours, indices delta-coded as varints; then gzip and brotli. A floor for what meshopt or Draco reach, not their number.
  splats    the Pantheon's GaussianSplats as 17 bytes a splat: 16-bit positions, 8-bit log scales, 8-bit quaternion, 8-bit opacity, 8-bit colour
  images    every .jpg/.png re-encoded as WebP (quality 80) and AVIF (quality 60) at the same size; visual parity is not checked
  gpu       texture memory once decoded: RGBA8 with mipmaps, against 1 byte a pixel (ASTC 4x4, BC7) and half a byte (ETC1S, BC1), the KTX2 route
"""
import gzip, io, json, math, os, re, sys
import brotli, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); W = os.path.join(ROOT, 'data', 'worlds')

def gz(b): bio = io.BytesIO(); g = gzip.GzipFile(fileobj=bio, mode='wb', compresslevel=9, mtime=0); g.write(b); g.close(); return len(bio.getvalue())
def br(b): return len(brotli.compress(b, quality=11))
def attr(s, k): m = re.search(r"\b%s=['\"]([^'\"]*)['\"]" % k, s); return m.group(1) if m else None
def floats(t): return np.array(t.split(), dtype=np.float64)

def varints(a):
    out = bytearray()
    for x in a.tolist():
        x = (x << 1) ^ (x >> 63)                       # zigzag
        while x >= 0x80: out.append((x & 0x7f) | 0x80); x >>= 7
        out.append(x)
    return bytes(out)

def oct8(n):
    n = n / np.maximum(np.abs(n).sum(1, keepdims=True), 1e-12); x, y, z = n[:, 0].copy(), n[:, 1].copy(), n[:, 2]
    neg = z < 0; x2 = (1 - np.abs(y[neg])) * np.sign(x[neg]); y2 = (1 - np.abs(x[neg])) * np.sign(y[neg]); x[neg], y[neg] = x2, y2
    return np.clip(np.round((np.stack([x, y], 1) * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)

def q16(p):
    lo, hi = p.min(0), p.max(0); ext = np.maximum(hi - lo, 1e-12)
    return np.round((p - lo) / ext * 65535).astype(np.uint16), float((ext / 65535 / 2).max())

def mesh(path):
    s = open(path, encoding='utf-8').read()
    P = floats(attr(s, 'point')).reshape(-1, 3); N = floats(attr(s, 'vector')).reshape(-1, 3); C = floats(attr(s, 'color')).reshape(-1, 3)
    I = np.array(attr(s, 'index').split(), dtype=np.int64)
    qp, err = q16(P); d = np.diff(I, prepend=0)
    blob = qp.tobytes() + oct8(N).tobytes() + np.clip(np.round(C * 255), 0, 255).astype(np.uint8).tobytes() + varints(d)
    raw = os.path.getsize(path); b = open(path, 'rb').read()
    return dict(file=os.path.relpath(path, W), vertices=len(P), triangles=len(I) // 3, xml=dict(raw=raw, gz=gz(b), br=br(b)),
                binary=dict(raw=len(blob), gz=gz(blob), br=br(blob)), max_position_error_m=round(err, 5))

def splats(path):
    s = open(path, encoding='utf-8').read(); i = s.find('<GaussianSplats'); t = s[i:]
    P = floats(attr(t, 'positions')).reshape(-1, 3); S = floats(attr(t, 'scales')).reshape(-1, 3); Q = floats(attr(t, 'orientations')).reshape(-1, 4)
    O = floats(attr(t, 'opacities')); C = floats(attr(t, 'sphericalHarmonicsDegree0Coef0')).reshape(-1, 3)
    qp, err = q16(P)
    ls = np.log(np.maximum(np.abs(S), 1e-9)); ls8 = np.round((ls - ls.min()) / max(ls.max() - ls.min(), 1e-9) * 255).astype(np.uint8)
    Qn = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12); q8 = np.round((Qn * 0.5 + 0.5) * 255).astype(np.uint8)
    def u8(a): lo, hi = a.min(), a.max(); return np.round((a - lo) / max(hi - lo, 1e-9) * 255).astype(np.uint8)
    blob = qp.tobytes() + ls8.tobytes() + q8.tobytes() + u8(O).tobytes() + u8(C).tobytes()
    b = open(path, 'rb').read()
    return dict(file=os.path.relpath(path, W), splats=len(P), xml=dict(raw=len(b), gz=gz(b), br=br(b)), binary=dict(raw=len(blob), gz=gz(blob), br=br(blob)),
                bytes_per_splat=dict(xml_gz=round(gz(b) / len(P), 1), binary_br=round(br(blob) / len(P), 1)), max_position_error_units=round(err, 5))

def images(d):
    out = dict(files=0, jpg_png=0, webp=0, avif=0, pixels=0, gpu_rgba8_mips=0, gpu_1bpp=0, gpu_half_bpp=0)
    for root, _, fs in os.walk(d):
        for n in fs:
            if not n.lower().endswith(('.jpg', '.png')): continue
            p = os.path.join(root, n); im = Image.open(p); im.load(); w, h = im.size; px = w * h
            rgb = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
            for fmt, kw in (('webp', dict(quality=80, method=6)), ('avif', dict(quality=60))):
                bio = io.BytesIO(); rgb.save(bio, fmt.upper(), **kw); out[fmt] += len(bio.getvalue())
            out['files'] += 1; out['jpg_png'] += os.path.getsize(p); out['pixels'] += px
            out['gpu_rgba8_mips'] += int(px * 4 * 4 / 3); out['gpu_1bpp'] += int(px * 4 / 3); out['gpu_half_bpp'] += int(px * 0.5 * 4 / 3)
    return out

def main():
    rep = dict(text={}, images={}, mesh=None, splats=None)
    for wid in sorted(os.listdir(W)):
        d = os.path.join(W, wid)
        if not os.path.isdir(d): continue
        t = dict(files=0, raw=0, gz=0, br=0)
        for root, _, fs in os.walk(d):
            for n in fs:
                if n.endswith(('.x3d', '.xml')):
                    b = open(os.path.join(root, n), 'rb').read(); t['files'] += 1; t['raw'] += len(b); t['gz'] += gz(b); t['br'] += br(b)
        rep['text'][wid] = t; rep['images'][wid] = images(d)
        print(wid, t, rep['images'][wid], flush=True)
    rep['mesh'] = mesh(os.path.join(W, 'giza', 'sphinx-today-mesh-v21.xml')); print(rep['mesh'], flush=True)
    rep['splats'] = splats(os.path.join(W, 'pantheon', 'pantheon.x3d')); print(rep['splats'], flush=True)
    json.dump(rep, open(os.path.join(ROOT, 'data', 'bird', 'stream-bench.json'), 'w'), indent=1)

if __name__ == '__main__': main()
