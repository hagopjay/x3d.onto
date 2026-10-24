#!/usr/bin/env python3
"""Procedural textures for the v2 scene (numpy + PIL; deterministic seeds). Everything is generated here, nothing downloaded. Outputs v2/tex/*.png.
Earth, Moon and Sun maps are procedural artworks (NOT real data); the Earth map is a plausible-looking planet, not a map of the real Earth."""
import numpy as np
from PIL import Image
from pathlib import Path
OUT = Path(__file__).resolve().parent / "tex"; OUT.mkdir(exist_ok=True)
def fbm(w, h, beta=2.6, seed=0, oct_cut=None):
    rng = np.random.default_rng(seed); fx = np.fft.fftfreq(w)[None, :]; fy = np.fft.fftfreq(h)[:, None]; f = np.sqrt(fx ** 2 + fy ** 2); f[0, 0] = 1
    amp = 1 / f ** (beta / 2); amp[0, 0] = 0
    if oct_cut: amp *= np.exp(-(f / oct_cut) ** 2)
    ph = np.exp(2j * np.pi * rng.random((h, w))); z = np.real(np.fft.ifft2(amp * ph)); z = (z - z.min()) / (z.max() - z.min()); return z
def save(a, name, mode="RGB"):
    a = np.clip(a, 0, 1); Image.fromarray((a * 255).astype(np.uint8), mode).save(OUT / name, optimize=True); print(name, a.shape, (OUT / name).stat().st_size // 1024, "KB")
def normal_from_height(hm, strength=3.0):
    gx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) * strength; gy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) * strength
    n = np.dstack([-gx, -gy, np.ones_like(hm)]); n /= np.linalg.norm(n, axis=2, keepdims=True); return (n + 1) / 2
def lerp(a, b, t): return a + (b - a) * t[..., None]
# ---------------- planets
def earth(w=2048, h=1024):
    el = fbm(w, h, 3.3, 5); el2 = fbm(w, h, 2.6, 8); el3 = fbm(w, h, 1.7, 12); e = 0.50 * el + 0.34 * el2 + 0.16 * el3; e = (e - e.min()) / (e.max() - e.min()); thr = np.percentile(e, 70)
    lat = (np.arange(h)[:, None] / h - 0.5) * np.pi; latd = np.abs(np.degrees(lat)) * np.ones((1, w))
    land = e > thr; moist = fbm(w, h, 3.0, 9); depth = np.clip((thr - e) / 0.25, 0, 1)
    ocean = lerp(np.array([0.02, 0.14, 0.36]), np.array([0.05, 0.30, 0.55]), 1 - depth) * 1.0
    shallow = np.clip((e - (thr - 0.05)) / 0.05, 0, 1) * (~land); ocean = lerp(ocean, np.array([0.15, 0.52, 0.62]), shallow * 0.8)
    desert = np.clip((1 - moist) * 1.6 - 0.5, 0, 1) * np.clip(1 - np.abs(latd - 25) / 18, 0, 1)
    forest = np.array([0.12, 0.33, 0.12]); grass = np.array([0.30, 0.46, 0.18]); sand = np.array([0.72, 0.62, 0.40]); tundra = np.array([0.46, 0.50, 0.42]); rock = np.array([0.45, 0.42, 0.38])
    ground = lerp(lerp(forest, grass, np.clip(moist * 1.4 - 0.2, 0, 1)), sand, desert)
    ground = lerp(ground, tundra, np.clip((latd - 55) / 12, 0, 1)); alt = np.clip((e - (thr + 0.12)) / 0.2, 0, 1); ground = lerp(ground, rock, alt)
    ice = np.clip((latd - 76) / 5, 0, 1) + np.clip((alt - 0.6) * 2, 0, 1) * 0.5; ground = lerp(ground, np.array([0.95, 0.97, 1.0]), np.clip(ice, 0, 1))
    img = np.where(land[..., None], ground, ocean) * (0.92 + 0.12 * fbm(w, h, 1.4, 14)[..., None]); img = lerp(img, np.array([0.94, 0.97, 1.0]), np.clip((latd - 78) / 4, 0, 1) * (~land) * 0.9)
    hs = np.roll(e, 1, 1) - np.roll(e, -1, 1); img = img * (1 + hs[..., None] * 14 * land[..., None]); save(img, "earth_day.png")
    save(np.dstack([np.where(land, 0.05, 0.85)] * 3), "earth_spec.png")
def clouds(w=2048, h=1024):
    c = fbm(w, h, 2.7, 21); c2 = fbm(w, h, 1.8, 22); a = np.clip((0.65 * c + 0.35 * c2 - 0.50) * 3.2, 0, 1); rgba = np.dstack([np.ones_like(a), np.ones_like(a), np.ones_like(a), a * 0.92]); save(rgba, "earth_clouds.png", "RGBA")
def moon(w=2048, h=1024):
    rng = np.random.default_rng(31); base = 0.45 + 0.28 * fbm(w, h, 2.6, 30); yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(420):
        cx, cy = rng.integers(0, w), rng.integers(0, h); r = rng.pareto(2.2) * 6 + 5; r = min(r, 70)
        dx = (xx - cx + w / 2) % w - w / 2; d = np.sqrt(dx ** 2 + (yy - cy) ** 2) / r; m = d < 2.2
        prof = np.where(d < 1, -0.28 * (1 - d ** 2) + 0.0, 0.22 * np.exp(-((d - 1.05) / 0.22) ** 2)) * np.where(d < 2.2, 1, 0)
        base = base + prof * m
    mare = fbm(w, h, 3.2, 33); base = base - 0.18 * np.clip((mare - 0.55) * 4, 0, 1); save(np.dstack([base * 1.0, base * 0.99, base * 0.96]), "moon.png")
def sun(w=1024, h=512):
    g = fbm(w, h, 2.4, 40); g2 = fbm(w, h, 1.2, 41); t = np.clip(0.35 + 0.8 * g + 0.25 * g2, 0, 1.2); img = np.dstack([np.clip(1.0 * t + 0.1, 0, 1), np.clip(0.62 * t + 0.1, 0, 1), np.clip(0.18 * t ** 2, 0, 1)]); save(img, "sun.png")
# ---------------- town materials (tileable) with normal maps
def tile_pair(name, color_fn, height_fn, size=512, strength=3.0):
    hm = height_fn(size); col = color_fn(size, hm); save(col, name + ".png"); save(normal_from_height(hm, strength), name + "_n.png")
def grass(s): return 0.6 * fbm(s, s, 2.2, 50) + 0.4 * fbm(s, s, 0.8, 51)
def grass_c(s, hm):
    v = fbm(s, s, 2.8, 52); a = np.array([0.20, 0.38, 0.10]); b = np.array([0.38, 0.52, 0.18]); c = np.array([0.30, 0.30, 0.12]); out = lerp(a, b, hm); out = lerp(out, c, np.clip((v - 0.62) * 3, 0, 1) * 0.5); return out * (0.78 + 0.35 * fbm(s, s, 1.0, 53)[..., None])
def dirt(s): return 0.5 * fbm(s, s, 2.0, 60) + 0.5 * fbm(s, s, 0.6, 61)
def dirt_c(s, hm):
    a = np.array([0.36, 0.28, 0.18]); b = np.array([0.55, 0.45, 0.30]); out = lerp(a, b, hm); st = (fbm(s, s, 0.3, 62) > 0.93)[..., None] * 0.18; return out * (0.85 + 0.3 * fbm(s, s, 2.5, 63)[..., None]) + st
def cobble(s, n=8, seed=70):
    rng = np.random.default_rng(seed); yy, xx = np.mgrid[0:s, 0:s] / s * n; cells = np.floor(xx + 0.5 * (np.floor(yy) % 2)).astype(int); row = np.floor(yy).astype(int)
    fx = (xx + 0.5 * (np.floor(yy) % 2)) % 1; fy = yy % 1; edge = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)); hm = np.clip(edge * 7, 0, 1) ** 0.6
    var = rng.random((n + 2, n + 2)); v = var[row % n, cells % n]; return hm * (0.85 + 0.15 * v) + 0.0 * fbm(s, s, 2.4, seed + 1)
def cobble_c(s, hm):
    rng = np.random.default_rng(71); n = 8; yy, xx = np.mgrid[0:s, 0:s] / s * n; cells = np.floor(xx + 0.5 * (np.floor(yy) % 2)).astype(int) % n; row = np.floor(yy).astype(int) % n; tone = rng.random((n, n))[row, cells]
    a = np.array([0.42, 0.40, 0.37]); b = np.array([0.62, 0.58, 0.52]); out = lerp(a, b, tone); out = out * (0.55 + 0.45 * hm[..., None]); return out * (0.85 + 0.25 * fbm(s, s, 2.2, 72)[..., None])
def roof(s):
    yy, xx = np.mgrid[0:s, 0:s] / s * 12; fx = (xx + 0.5 * (np.floor(yy) % 2)) % 1; fy = yy % 1; return np.clip(np.sqrt((fx - 0.5) ** 2 * 1.2) * -1.6 + 0.9 + fy * 0.35, 0, 1) * (0.9 + 0.1 * fbm(s, s, 2.0, 80))
def roof_c(s, hm):
    rng = np.random.default_rng(81); n = 12; yy, xx = np.mgrid[0:s, 0:s] / s * n; cells = np.floor(xx + 0.5 * (np.floor(yy) % 2)).astype(int) % n; row = np.floor(yy).astype(int) % n; tone = rng.random((n, n))[row, cells]
    a = np.array([0.45, 0.14, 0.09]); b = np.array([0.72, 0.30, 0.16]); out = lerp(a, b, tone); return out * (0.45 + 0.7 * hm[..., None])
def plaster(s): return 0.5 * fbm(s, s, 2.6, 90) + 0.5 * fbm(s, s, 1.0, 91)
def plaster_c(s, hm): return lerp(np.array([0.78, 0.74, 0.66]), np.array([0.92, 0.88, 0.80]), hm) * (0.9 + 0.15 * fbm(s, s, 2.0, 92)[..., None])
def wood(s):
    yy, xx = np.mgrid[0:s, 0:s]; g = np.sin(xx / s * 2 * np.pi * 14 + 3 * fbm(s, s, 2.6, 100)) * 0.5 + 0.5; return 0.7 * g + 0.3 * fbm(s, s, 1.0, 101)
def wood_c(s, hm): return lerp(np.array([0.22, 0.13, 0.07]), np.array([0.46, 0.30, 0.16]), hm) * (0.9 + 0.2 * fbm(s, s, 1.6, 102)[..., None])
def rock(s): return 0.65 * fbm(s, s, 2.8, 110) + 0.35 * fbm(s, s, 1.2, 111)
def rock_c(s, hm): return lerp(np.array([0.28, 0.27, 0.26]), np.array([0.58, 0.55, 0.50]), hm)
def water(s): return 0.6 * fbm(s, s, 2.0, 120) + 0.4 * fbm(s, s, 1.0, 121)
def water_c(s, hm): return lerp(np.array([0.04, 0.16, 0.24]), np.array([0.14, 0.38, 0.46]), hm)

def slate(s):
    yy, xx = np.mgrid[0:s, 0:s] / s * 10; fx = (xx + 0.5 * (np.floor(yy) % 2)) % 1; fy = yy % 1; edge = np.minimum(np.minimum(fx, 1 - fx) * 2.2, np.minimum(fy, 1 - fy) * 2.8); return np.clip(edge, 0, 1) ** 0.7 * (0.85 + 0.15 * fbm(s, s, 2.0, 130))
def slate_c(s, hm):
    rng = np.random.default_rng(131); n = 10; yy, xx = np.mgrid[0:s, 0:s] / s * n; cells = np.floor(xx + 0.5 * (np.floor(yy) % 2)).astype(int) % n; row = np.floor(yy).astype(int) % n; tone = rng.random((n, n))[row, cells]
    a = np.array([0.20, 0.22, 0.27]); b = np.array([0.40, 0.42, 0.47]); out = lerp(a, b, tone); return out * (0.4 + 0.75 * hm[..., None]) * (0.9 + 0.2 * fbm(s, s, 2.2, 132)[..., None])
def bark(s):
    yy, xx = np.mgrid[0:s, 0:s]; g = np.sin(xx / s * 2 * np.pi * 9 + 5 * fbm(s, s, 2.4, 140)) * 0.5 + 0.5; return 0.55 * g + 0.45 * fbm(s, s, 1.1, 141)
def bark_c(s, hm): return lerp(np.array([0.13, 0.10, 0.08]), np.array([0.36, 0.29, 0.22]), hm) * (0.85 + 0.25 * fbm(s, s, 1.8, 142)[..., None])
def cloud_sheet(s=1024):
    c = 0.62 * fbm(s, s, 2.9, 150) + 0.38 * fbm(s, s, 1.7, 151); a = np.clip((c - 0.52) * 3.4, 0, 1) ** 1.3; shade = 0.80 + 0.20 * np.clip((c - 0.5) * 2, 0, 1)
    save(np.dstack([shade, shade, np.minimum(1, shade * 1.03), a * 0.9]), "cloud_sheet.png", "RGBA")
def earth_mr(w=2048, h=1024):
    e = np.asarray(Image.open(OUT / "earth_spec.png").convert("L"), dtype=float) / 255; rough = np.where(e > 0.5, 0.20, 0.88); save(np.dstack([np.ones_like(rough), rough, np.zeros_like(rough)]), "earth_mr.png")
FACES = {"front": lambda u, v: (u, v, -1 + 0 * u), "back": lambda u, v: (-u, v, 1 + 0 * u), "left": lambda u, v: (-1 + 0 * u, v, -u), "right": lambda u, v: (1 + 0 * u, v, u), "top": lambda u, v: (u, 1 + 0 * u, v), "bottom": lambda u, v: (u, -1 + 0 * u, -v)}
def vnoise3(x, y, z, seed):
    rng = np.random.default_rng(seed); k = rng.uniform(0.7, 1.6, (6, 3)); p = rng.uniform(0, 6.28, (6, 3)); out = 0
    for i in range(6): out = out + np.sin(x * k[i, 0] * (2 + i) + p[i, 0]) * np.sin(y * k[i, 1] * (2 + i) + p[i, 1]) * np.sin(z * k[i, 2] * (2 + i) + p[i, 2]) / (1 + 0.45 * i)
    return out / 2.2
def stars(n=2048, nstars=9000):
    rng = np.random.default_rng(7); d = rng.normal(size=(nstars, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    mag = 6.5 + np.log10(rng.random(nstars)) / 0.6; tint = rng.uniform(0, 1, nstars)
    col = np.where(tint[:, None] < 0.2, np.array([0.75, 0.82, 1.0]), np.where(tint[:, None] < 0.75, np.array([1.0, 0.98, 0.94]), np.array([1.0, 0.82, 0.62])))
    g = np.array([0.35, 0.9, 0.25]); g /= np.linalg.norm(g)
    extra = rng.normal(size=(60000, 3)); extra /= np.linalg.norm(extra, axis=1, keepdims=True); keep = rng.random(60000) < np.exp(-(extra @ g) ** 2 / (2 * 0.14 ** 2)) * 0.5; extra = extra[keep]
    d = np.vstack([d, extra]); mag = np.concatenate([mag, 6.6 + np.log10(rng.random(len(extra))) / 0.8]); col = np.vstack([col, np.tile([1.0, 0.95, 0.9], (len(extra), 1))])
    for name, fn in FACES.items():
        img = np.zeros((n, n, 3)); uu, vv = np.meshgrid((np.arange(n) + 0.5) / n * 2 - 1, 1 - (np.arange(n) + 0.5) / n * 2); x, y, z = fn(uu, vv); l = np.sqrt(x * x + y * y + z * z); x, y, z = x / l, y / l, z / l
        band = np.exp(-((x * g[0] + y * g[1] + z * g[2]) ** 2) / (2 * 0.11 ** 2)); core = vnoise3(x * 3, y * 3, z * 3, 5) * 0.5 + 0.5; dust = np.clip(vnoise3(x * 9, y * 9, z * 9, 6) * 0.5 + 0.5, 0, 1)
        mw = band * (0.25 + 0.75 * core) * (1 - 0.65 * np.clip((dust - 0.45) * 2.2, 0, 1)) * 0.30 + 0.01 * band
        img += mw[..., None] * np.array([0.78, 0.74, 0.9]) * np.array([1, 0.96, 0.98])
        ax = {"front": 2, "back": 2, "left": 0, "right": 0, "top": 1, "bottom": 1}[name]; sgn = {"front": -1, "back": 1, "left": -1, "right": 1, "top": 1, "bottom": -1}[name]
        sel = (np.abs(d[:, ax]) >= np.abs(d).max(axis=1) - 1e-12) & (d[:, ax] * sgn > 0); dd = d[sel] / np.abs(d[sel][:, ax:ax + 1])
        if name == "front": uu_, vv_ = dd[:, 0], dd[:, 1]
        elif name == "back": uu_, vv_ = -dd[:, 0], dd[:, 1]
        elif name == "left": uu_, vv_ = -dd[:, 2], dd[:, 1]
        elif name == "right": uu_, vv_ = dd[:, 2], dd[:, 1]
        elif name == "top": uu_, vv_ = dd[:, 0], dd[:, 2]
        else: uu_, vv_ = dd[:, 0], -dd[:, 2]
        cx = (uu_ + 1) / 2 * n; cy = (1 - vv_) / 2 * n; m = mag[sel]; c = col[sel]
        for k in range(len(cx)):
            b = min(1.6, (10 ** (-0.4 * (m[k] - 1.5))) ** 0.5); sig = 0.55 + 0.30 * min(b, 1.0); x0, y0 = int(cx[k]), int(cy[k]); r = 3
            for yy_ in range(max(0, y0 - r), min(n, y0 + r + 1)):
                for xx_ in range(max(0, x0 - r), min(n, x0 + r + 1)):
                    w = np.exp(-((xx_ + 0.5 - cx[k]) ** 2 + (yy_ + 0.5 - cy[k]) ** 2) / (2 * sig ** 2)); img[yy_, xx_] += b * w * c[k]
        img = np.clip(img, 0, 1) ** 0.85; a = np.clip(img.max(axis=2) * 1.15, 0, 1); rgbn = np.where(a[..., None] > 1e-4, img / np.maximum(a[..., None], 1e-4), 0).clip(0, 1)
        Image.fromarray((np.dstack([rgbn, a]) * 255).astype(np.uint8), "RGBA").save(OUT / f"stars_{name}.png", optimize=True); print("stars", name, (OUT / f"stars_{name}.png").stat().st_size // 1024, "KB")

def wheat(s):
    yy, xx = np.mgrid[0:s, 0:s]; st = np.sin(xx / s * 2 * np.pi * 16 + 1.2 * fbm(s, s, 2.8, 160)) * 0.5 + 0.5; return 0.55 * st + 0.45 * fbm(s, s, 0.7, 161)
def wheat_c(s, hm): return lerp(np.array([0.55, 0.40, 0.14]), np.array([0.86, 0.70, 0.30]), hm) * (0.85 + 0.25 * fbm(s, s, 2.0, 162)[..., None])
def furrow(s):
    yy, xx = np.mgrid[0:s, 0:s]; st = np.sin(xx / s * 2 * np.pi * 12) * 0.5 + 0.5; return 0.7 * st + 0.3 * fbm(s, s, 1.0, 170)
def furrow_c(s, hm):
    out = lerp(np.array([0.20, 0.14, 0.08]), np.array([0.44, 0.33, 0.20]), hm); sp = (fbm(s, s, 0.4, 171) > 0.9)[..., None] * (hm[..., None] > 0.6); return lerp(out, np.array([0.30, 0.45, 0.12]), np.clip(sp.astype(float), 0, 1)[..., 0] * 0.6) * (0.9 + 0.2 * fbm(s, s, 2.0, 172)[..., None])

def ashlar_maps(s=512, seed=300):
    rng = np.random.default_rng(seed); rows = 8; hs = rng.uniform(0.7, 1.3, rows); hs = hs / hs.sum(); edges = np.concatenate([[0], np.cumsum(hs)]); tone = np.zeros((s, s)); hm = np.zeros((s, s)); yy, xx = np.mgrid[0:s, 0:s] / s
    for r in range(rows):
        y0, y1 = edges[r], edges[r + 1]; n = rng.integers(3, 6); ws = rng.uniform(0.7, 1.3, n); ws /= ws.sum(); xs = np.concatenate([[0], np.cumsum(ws)]); off = rng.uniform(0, 1)
        for k in range(n):
            xa, xb = (xs[k] + off) % 1.0, (xs[k + 1] + off) % 1.0; t = rng.uniform(0.0, 1.0)
            if xa < xb: m = (xx >= xa) & (xx < xb) & (yy >= y0) & (yy < y1); u = (xx - xa) / (xb - xa)
            else: m = ((xx >= xa) | (xx < xb)) & (yy >= y0) & (yy < y1); u = np.where(xx >= xa, (xx - xa) / (1 - xa + xb), (xx + 1 - xa) / (1 - xa + xb))
            v = (yy - y0) / (y1 - y0); edge = np.minimum(np.minimum(u, 1 - u) * (xb - xa if xb > xa else 1 - xa + xb), np.minimum(v, 1 - v) * (y1 - y0)); h = np.clip(edge * s / 5.0, 0, 1) ** 0.7
            tone[m] = t; hm[m] = h[m]
    return tone, hm
def ashlar():
    tone, hm = ashlar_maps(); n1 = fbm(512, 512, 2.4, 301); n2 = fbm(512, 512, 1.0, 302)
    a = np.array([0.52, 0.50, 0.46]); b = np.array([0.76, 0.73, 0.67]); col = lerp(a, b, tone * 0.7 + n1 * 0.3) * (0.55 + 0.45 * hm[..., None]) * (0.92 + 0.12 * n2[..., None])
    save(col, "ashlar.png"); save(normal_from_height(hm * 0.8 + 0.2 * n2, 4.0), "ashlar_n.png")

if __name__ == "__main__":
    import sys; only = sys.argv[1:]
    if only and only[0] == "town":
        for nm, h_, c_, st in (("wheat", wheat, wheat_c, 3.0), ("furrow", furrow, furrow_c, 4.0)): tile_pair(nm, c_, h_, 512, st)
        raise SystemExit
    if only and only[0] == "extra": cloud_sheet(); earth_mr(); stars(); raise SystemExit
    earth(); clouds(); moon(); sun(); cloud_sheet(); earth_mr()
    for nm, h_, c_, st in (("grass", grass, grass_c, 4.0), ("dirt", dirt, dirt_c, 3.0), ("cobble", cobble, cobble_c, 5.0), ("roof", roof, roof_c, 4.0), ("plaster", plaster, plaster_c, 2.0), ("wood", wood, wood_c, 3.0), ("rock", rock, rock_c, 5.0), ("water", water, water_c, 2.5), ("slate", slate, slate_c, 4.0), ("bark", bark, bark_c, 4.0), ("wheat", wheat, wheat_c, 3.0), ("furrow", furrow, furrow_c, 4.0)):
        tile_pair(nm, c_, h_, 512, st)

def earth_lights(w=2048, h=1024):
    land = np.asarray(Image.open(OUT / "earth_spec.png").convert("L"), dtype=float) / 255 < 0.5; lat = np.abs((np.arange(h)[:, None] / h - 0.5) * 180) * np.ones((1, w))
    pop = fbm(w, h, 2.3, 200); pop2 = fbm(w, h, 3.0, 201); clus = np.clip((pop * 0.6 + pop2 * 0.4 - 0.52) * 7, 0, 1) * np.clip((72 - lat) / 22, 0, 1) * land
    dots = np.clip((fbm(w, h, 0.35, 202) - 0.62) * 9, 0, 1); glow = np.clip((fbm(w, h, 1.6, 203) - 0.5) * 3, 0, 1) * 0.35
    L = np.clip(clus * (dots + glow), 0, 1) ** 0.8; save(np.dstack([L * 1.0, L * 0.85, L * 0.55]) * 0.6, "earth_lights.png")
def to_jpeg():
    for n in ("earth_day", "moon", "sun"):
        Image.open(OUT / f"{n}.png").convert("RGB").save(OUT / f"{n}.jpg", quality=92); print(n, ".jpg", (OUT / f"{n}.jpg").stat().st_size // 1024, "KB")
