// node pick_views.js <path to graph-v3.json>
// Screen-space pick statistics on the real Gobbler 3 Deep star coordinates (first g.drawn nodes), using the scene's own Viewpoint presets.
// Input used for docs/v4/HOVER-UI-SPEC.md: hagopjay/x3d.ML branch claude/project-thread-0105va @51e185f, gobbler-v3/deep/build-private/graph-v3.json (sha256 36a308c89af35877...).
// Pointer noise 3 px sigma, 12 samples per star, Monte Carlo (numbers move 1 to 2 points between runs).
const g = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const nodes = g.nodes.slice(0, g.drawn), N = nodes.length;
const W = 1527, H = 923;
const VIEWS = {
  Wide:     { pos: [5.15, -1.31, 15.59], ori: [0, 0, 1, 0], fov: 0.7 },
  Colossus: { pos: [-3.4, -8.2, 3.6], ori: [0.625, -0.696, 0.354, 1.366], fov: 1.22 },
  Eye:      { pos: [-2.48, 0.38, 4.4], ori: [0.357, -0.93, 0.084, 0.497], fov: 0.62 },
  Inside:   { pos: [8.4, -2.6, 4.4], ori: [0.212, 0.969, -0.125, 1.096], fov: 0.95 },
  Flywheel: { pos: [6.41, -3.99, 3.35], ori: [0.965, -0.259, 0.036, 0.287], fov: 0.9 },
  Crown:    { pos: [4, 12.5, 7], ori: [-0.994, -0.089, -0.057, 1.134], fov: 1.0 },
};
function rot(ax) { // axis-angle -> 3x3 (row-major)
  let [x, y, z, a] = ax; const l = Math.hypot(x, y, z) || 1; x /= l; y /= l; z /= l;
  const c = Math.cos(a), s = Math.sin(a), t = 1 - c;
  return [t*x*x + c, t*x*y - s*z, t*x*z + s*y, t*x*y + s*z, t*y*y + c, t*y*z - s*x, t*x*z - s*y, t*y*z + s*x, t*z*z + c];
}
function project(v) {
  const R = rot(v.ori), f = (H / 2) / Math.tan(v.fov / 2), out = [];
  for (let i = 0; i < N; i++) {
    const d = [nodes[i].xyz[0] - v.pos[0], nodes[i].xyz[1] - v.pos[1], nodes[i].xyz[2] - v.pos[2]];
    // camera space = R^T d
    const cx = R[0]*d[0] + R[3]*d[1] + R[6]*d[2], cy = R[1]*d[0] + R[4]*d[1] + R[7]*d[2], cz = R[2]*d[0] + R[5]*d[1] + R[8]*d[2];
    if (cz >= -0.05) continue;
    const sx = W / 2 + f * cx / -cz, sy = H / 2 - f * cy / -cz;
    if (sx < 0 || sy < 0 || sx >= W || sy >= H) continue;
    out.push({ i, sx, sy, depth: -cz, w: nodes[i].w || 0.1, tier: nodes[i].tier });
  }
  return out;
}
function nn(stars) { // nearest-neighbour screen distance per star
  const CELL = 40, m = new Map();
  stars.forEach((s, k) => { const key = ((s.sx / CELL) | 0) + ',' + ((s.sy / CELL) | 0); (m.get(key) || m.set(key, []).get(key)).push(k); });
  return stars.map((s, k) => { let best = 1e9; const cx = (s.sx / CELL) | 0, cy = (s.sy / CELL) | 0;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) for (const j of (m.get((cx + dx) + ',' + (cy + dy)) || [])) if (j !== k) best = Math.min(best, Math.hypot(s.sx - stars[j].sx, s.sy - stars[j].sy)); return best; });
}
function pick(stars, x, y, R, mode) { let best = -1, bs = 1e18;
  for (let k = 0; k < stars.length; k++) { const s = stars[k], d2 = (s.sx - x) ** 2 + (s.sy - y) ** 2; if (d2 > R * R) continue;
    const rr = mode === 'weighted' ? 5 + 30 * s.w : 1; const sc = d2 / (rr * rr) + s.depth * 1e-4; if (sc < bs) { bs = sc; best = k; } }
  return best; }
function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-12)) * Math.cos(2 * Math.PI * Math.random()); }
const tiers = {}; nodes.forEach(n => tiers[n.tier] = (tiers[n.tier] || 0) + 1);
console.log('tier counts among the 2,476 drawn:', JSON.stringify(tiers), ' (viewport ' + W + 'x' + H + ')');
console.log('view      onscreen  medNN  <12px   self-pick@σ3px: all(dist)  all(weighted)  tier1-only   tier≤2');
for (const [name, v] of Object.entries(VIEWS)) {
  const all = project(v); if (!all.length) { console.log(name, 'none'); continue; }
  const d = nn(all), med = d.slice().sort((a, b) => a - b)[d.length >> 1], close = d.filter(x => x < 12).length;
  const sets = { all, t1: all.filter(s => s.tier === 1), t12: all.filter(s => s.tier <= 2) };
  function acc(set, mode, pool) { let ok = 0, tot = 0; const sample = set.length > 600 ? set.filter((_, k) => k % Math.ceil(set.length / 600) === 0) : set;
    for (const s of sample) for (let r = 0; r < 12; r++) { const x = s.sx + 3 * gauss(), y = s.sy + 3 * gauss(); const k = pick(pool, x, y, 30, mode); tot++; if (k >= 0 && pool[k].i === s.i) ok++; } return tot ? (100 * ok / tot).toFixed(0) + '%' : 'n/a'; }
  console.log(name.padEnd(9), String(all.length).padStart(7), ' ', med.toFixed(1).padStart(5), ' ', (100 * close / all.length).toFixed(0).padStart(4) + '% ',
    '      ', acc(all, 'dist', all).padStart(8), '    ', acc(all, 'weighted', all).padStart(8), '     ', (acc(sets.t1, 'dist', sets.t1) + ' (' + sets.t1.length + ')').padStart(12), '  ', (acc(sets.t12, 'dist', sets.t12) + ' (' + sets.t12.length + ')').padStart(12));
}
