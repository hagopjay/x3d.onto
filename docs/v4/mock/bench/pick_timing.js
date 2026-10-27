// node pick_timing.js <path to graph-v3.json>
// Timing of the screen-space picker (project all drawn stars, bucket into a grid, nearest-star query) in plain JS on real coordinates.
// A naive centred camera is used, so only the timings are meaningful here; use pick_views.js for crowding and accuracy.
// Numbers in docs/v4/HOVER-UI-SPEC.md: node v22.22.0, project 10.4 us, grid rebuild 18.7 us, query 0.5 us (2,476 stars).
const g = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const maxEdge = Math.max(...g.edges.map(e => Math.max(e.s, e.t))); console.log("max edge endpoint index", maxEdge, "drawn count", g.drawn);
const nodes = g.nodes.slice(0, g.drawn);
const N = nodes.length;
const xs = new Float64Array(N), ys = new Float64Array(N), zs = new Float64Array(N), ws = new Float64Array(N);
nodes.forEach((n, i) => { xs[i] = n.xyz[0]; ys[i] = n.xyz[1]; zs[i] = n.xyz[2]; ws[i] = n.w || 0.1; });
const mn = a => Math.min(...a), mx = a => Math.max(...a);
console.log('drawn', N, 'bbox x', mn(xs).toFixed(1), mx(xs).toFixed(1), 'y', mn(ys).toFixed(1), mx(ys).toFixed(1), 'z', mn(zs).toFixed(1), mx(zs).toFixed(1));
// camera: look from +z toward origin, fov 45deg, 1527x923
const W = 1527, H = 923, fov = 45 * Math.PI / 180, f = 0.5 * H / Math.tan(fov / 2);
const cam = { x: 0, y: 0, z: 60 };
const px = new Float32Array(N), py = new Float32Array(N), pz = new Float32Array(N);
function project() {
  for (let i = 0; i < N; i++) {
    const dz = cam.z - zs[i];
    if (dz <= 0.1) { px[i] = -1e9; py[i] = -1e9; pz[i] = dz; continue; }
    px[i] = W / 2 + (xs[i] - cam.x) * f / dz;
    py[i] = H / 2 - (ys[i] - cam.y) * f / dz;
    pz[i] = dz;
  }
}
const CELL = 32, GW = Math.ceil(W / CELL), GH = Math.ceil(H / CELL);
let heads = new Int32Array(GW * GH), next = new Int32Array(N);
function grid() {
  heads.fill(-1);
  for (let i = 0; i < N; i++) {
    const cx = (px[i] / CELL) | 0, cy = (py[i] / CELL) | 0;
    if (cx < 0 || cy < 0 || cx >= GW || cy >= GH) continue;
    const c = cy * GW + cx; next[i] = heads[c]; heads[c] = i;
  }
}
function nearest(mx_, my_, R) {
  const cx = (mx_ / CELL) | 0, cy = (my_ / CELL) | 0, r = Math.ceil(R / CELL);
  let best = -1, bs = 1e18;
  for (let y = Math.max(0, cy - r); y <= Math.min(GH - 1, cy + r); y++)
    for (let x = Math.max(0, cx - r); x <= Math.min(GW - 1, cx + r); x++)
      for (let i = heads[y * GW + x]; i >= 0; i = next[i]) {
        const d2 = (px[i] - mx_) ** 2 + (py[i] - my_) ** 2; if (d2 > R * R) continue;
        const rr = 6 + 30 * ws[i]; const s = d2 / (rr * rr) + pz[i] * 1e-4;
        if (s < bs) { bs = s; best = i; }
      }
  return best;
}
function time(label, fn, it) { for (let k = 0; k < 200; k++) fn(); const t = process.hrtime.bigint(); for (let k = 0; k < it; k++) fn(); const us = Number(process.hrtime.bigint() - t) / 1e3 / it; console.log(label.padEnd(34), us.toFixed(1), 'us per call'); return us; }
const a = time('project 2,476 stars', project, 2000);
const b = time('grid rebuild', () => { project(); grid(); }, 2000);
project(); grid();
const c = time('nearest-star query (R=30)', () => nearest(760 + Math.random() * 100, 460 + Math.random() * 100, 30), 200000);
let hit = 0, tot = 0, amb = 0;
for (let k = 0; k < 4000; k++) { const x = Math.random() * W, y = Math.random() * H; const i = nearest(x, y, 30); tot++; if (i >= 0) hit++; }
console.log('random pointer within 30 px of a star:', (100 * hit / tot).toFixed(1) + '%', '(synthetic centred camera, not the Face view)');
// ambiguity: stars with another star within 12 px
let close = 0; for (let i = 0; i < N; i++) { const cx = (px[i] / CELL) | 0, cy = (py[i] / CELL) | 0; if (cx < 0 || cy < 0 || cx >= GW || cy >= GH) continue; let found = false; for (let y = Math.max(0, cy - 1); y <= Math.min(GH - 1, cy + 1) && !found; y++) for (let x = Math.max(0, cx - 1); x <= Math.min(GW - 1, cx + 1) && !found; x++) for (let j = heads[y * GW + x]; j >= 0; j = next[j]) { if (j !== i && (px[i] - px[j]) ** 2 + (py[i] - py[j]) ** 2 < 144) { found = true; break; } } if (found) close++; }
console.log('stars with a neighbour within 12 px:', close, 'of', N, '(' + (100 * close / N).toFixed(1) + '%)');
console.log('node', process.version);
