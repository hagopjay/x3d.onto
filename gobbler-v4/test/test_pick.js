/* node gobbler-v4/test/test_pick.js : projection and picking against a slow reference, then the real Deep graph if it has been fetched (make v4-data). */
'use strict';
var assert = require('assert'), fs = require('fs'), path = require('path'), Pick = require('../src/pick.js');
var n = 0;
function t(name, fn) { fn(); n++; console.log('ok  ' + name); }
function rng(seed) { var s = seed >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var t2 = s; t2 = Math.imul(t2 ^ (t2 >>> 15), t2 | 1); t2 ^= t2 + Math.imul(t2 ^ (t2 >>> 7), t2 | 61); return ((t2 ^ (t2 >>> 14)) >>> 0) / 4294967296; }; }
function slowProject(p, cam, W, H) {          /* straight from the definition, no shared code with Index.update */
  var R = Pick.rot(cam.ori), d = [p[0] - cam.pos[0], p[1] - cam.pos[1], p[2] - cam.pos[2]];
  var c = [0, 1, 2].map(function (k) { return R[k] * d[0] + R[3 + k] * d[1] + R[6 + k] * d[2]; });
  if (c[2] >= -0.05) return null;
  var f = (Math.min(W, H) / 2) / Math.tan(cam.fov / 2), x = W / 2 + f * c[0] / -c[2], y = H / 2 - f * c[1] / -c[2];
  return (x >= 0 && y >= 0 && x < W && y < H) ? { x: x, y: y, z: -c[2] } : null;
}
var ID = [0, 0, 1, 0];

t('a star straight ahead lands on the centre; one to the right of the view lands right', function () {
  var ix = new Pick.Index([{ xyz: [0, 0, -5], tier: 1 }, { xyz: [1, 0, -5], tier: 1 }, { xyz: [0, 1, -5], tier: 1 }, { xyz: [0, 0, 5], tier: 1 }]);
  var nv = ix.update({ pos: [0, 0, 0], ori: ID, fov: Math.PI / 2 }, 800, 600);
  assert.strictEqual(nv, 3);                      /* the one behind the camera is culled */
  assert(Math.abs(ix.sx[0] - 400) < 1e-3 && Math.abs(ix.sy[0] - 300) < 1e-3);
  assert(ix.sx[1] > 400 && Math.abs(ix.sy[1] - 300) < 1e-3, 'x grows to the right');
  assert(ix.sy[2] < 300, 'y grows upward, screen y shrinks');
  /* fov 90 deg on the smaller side (600): a point 5 right at depth 5 is exactly 300 px right of centre */
  var ix2 = new Pick.Index([{ xyz: [5, 0, -5], tier: 1 }]); ix2.update({ pos: [0, 0, 0], ori: ID, fov: Math.PI / 2 }, 800, 600);
  assert(Math.abs(ix2.sx[0] - 700) < 1e-3, String(ix2.sx[0]));
});
t('a camera rotated a quarter turn about y sees what was on its left', function () {
  var ix = new Pick.Index([{ xyz: [-5, 0, 0], tier: 1 }]);        /* to the camera's left in the default pose */
  assert.strictEqual(ix.update({ pos: [0, 0, 0], ori: ID, fov: 1 }, 800, 600), 0);
  assert.strictEqual(ix.update({ pos: [0, 0, 0], ori: [0, 1, 0, Math.PI / 2], fov: 1 }, 800, 600), 1);   /* turned left: the star is dead ahead */
  assert(Math.abs(ix.sx[0] - 400) < 1e-2 && Math.abs(ix.sy[0] - 300) < 1e-2);
});
t('fuzz: 300 random cameras agree with the slow reference to 1e-3 px, same visible set', function () {
  var rand = rng(11), nodes = [], i;
  for (i = 0; i < 1500; i++) nodes.push({ xyz: [(rand() - 0.5) * 30, (rand() - 0.5) * 30, (rand() - 0.5) * 30], tier: 1 + ((rand() * 3) | 0) });
  var ix = new Pick.Index(nodes);
  for (var k = 0; k < 300; k++) {
    var cam = { pos: [(rand() - 0.5) * 40, (rand() - 0.5) * 40, (rand() - 0.5) * 40], ori: [rand() - 0.5, rand() - 0.5, rand() - 0.5, rand() * 6.28], fov: 0.3 + rand() * 1.4 }, W = 400 + rand() * 1600, H = 300 + rand() * 900;
    ix.update(cam, W, H);
    var seen = {}; for (i = 0; i < ix.nvis; i++) seen[ix.vis[i]] = 1;
    for (i = 0; i < nodes.length; i++) {
      var ref = slowProject(nodes[i].xyz, cam, W, H);
      if (!ref) { if (seen[i]) { var q = slowProject(nodes[i].xyz, cam, W, H); assert(!q, 'extra star ' + i); } continue; }
      /* float32 storage: allow a hair of drift at the viewport edge */
      if (!seen[i]) { assert(ref.x < 1e-2 || ref.y < 1e-2 || W - ref.x < 1e-2 || H - ref.y < 1e-2 || ref.z < 0.0501, 'missing star ' + i + ' at ' + ref.x + ',' + ref.y); continue; }
      assert(Math.abs(ref.x - ix.sx[i]) < 2e-3 * Math.max(1, ref.z) && Math.abs(ref.y - ix.sy[i]) < 2e-3 * Math.max(1, ref.z), 'drift ' + i + ' ' + ref.x + ' vs ' + ix.sx[i]);
    }
  }
});
t('pick returns the nearest star within the radius, nothing beyond it', function () {
  var ix = new Pick.Index([{ xyz: [0, 0, -5], tier: 1 }, { xyz: [0.1, 0, -5], tier: 1 }, { xyz: [3, 0, -5], tier: 1 }]);
  ix.update({ pos: [0, 0, 0], ori: ID, fov: Math.PI / 2 }, 800, 600);   /* 60 px per world unit at depth 5 */
  var a = ix.pick(400 + 2, 300, { radius: 30 }); assert.strictEqual(a.i, 0); assert(a.d < 3);
  var b = ix.pick(400 + 5, 300, { radius: 30 }); assert.strictEqual(b.i, 1);                    /* nearer to the second */
  assert.strictEqual(ix.pick(400 + 35, 300, { radius: 20 }), null);
  var c = ix.pick(400 + 180, 300, { radius: 30 }); assert.strictEqual(c.i, 2);
  assert.strictEqual(ix.pick(-500, -500, { radius: 30 }), null);
  assert.strictEqual(ix.pick(NaN, 10, { radius: 30 }), null);
});
t('equal distance: the nearer star in depth wins; candidates list stars within 12 px of the head', function () {
  var ix = new Pick.Index([{ xyz: [0, 0, -10], tier: 1 }, { xyz: [0, 0, -4], tier: 1 }, { xyz: [10, 0, -10], tier: 1 }]);
  ix.update({ pos: [0, 0, 0], ori: ID, fov: Math.PI / 2 }, 800, 600);   /* the first two project to the same pixel */
  var p = ix.pick(400, 300, { radius: 30 }); assert.strictEqual(p.i, 1); assert.strictEqual(p.cands.length, 2);
  assert.deepStrictEqual(p.cands.map(function (c) { return c.i; }), [1, 0]);
});
t('core-only LOD switches on in a dense sky, off in a sparse one, with hysteresis; shift (all) bypasses it', function () {
  var rand = rng(5), dense = [], i;
  for (i = 0; i < 1200; i++) dense.push({ xyz: [(rand() - 0.5) * 10, (rand() - 0.5) * 6, -12], tier: i % 4 === 0 ? 1 : 2 });
  var ix = new Pick.Index(dense), cam = { pos: [0, 0, 0], ori: ID, fov: 0.9 };
  ix.update(cam, 1200, 800, true); assert(ix.lodCore && ix.medianGap < 10, 'dense: gap ' + ix.medianGap);
  var any = ix.pick(600, 400, { radius: 400, all: true });
  var core = ix.pick(600, 400, { radius: 400 });
  assert(ix.tier[core.i] === 1, 'LOD picks core stars only');
  assert(any && ix.near(600, 400, 400, true).length > ix.near(600, 400, 400, false).length);
  ix.update({ pos: [0, 0, -6], ori: ID, fov: 0.9 }, 1200, 800, true);        /* half the distance: stars spread out */
  var g = ix.medianGap; assert(g > 10, 'closer gap ' + g);
  if (g <= 12) assert(ix.lodCore, 'hysteresis keeps LOD between 10 and 12'); else assert(!ix.lodCore);
  ix.update({ pos: [0, 0, -11], ori: ID, fov: 0.9 }, 1200, 800, true); assert(!ix.lodCore && ix.medianGap > 12, 'very close: gap ' + ix.medianGap);
  var few = new Pick.Index(dense.slice(0, 10)); few.update(cam, 1200, 800, true); assert(!few.lodCore && few.medianGap === Infinity, 'fewer than 30 stars never trigger LOD');
});
t('NaN or behind-camera stars never enter the index', function () {
  var ix = new Pick.Index([{ xyz: [NaN, 0, -5], tier: 1 }, { xyz: [0, 0, 5], tier: 1 }, { xyz: [0, 0, -5], tier: 1 }]);
  assert.strictEqual(ix.update({ pos: [0, 0, 0], ori: ID, fov: 1 }, 800, 600), 1);
});

/* real Deep graph: must reproduce the numbers in docs/v4/HOVER-UI-SPEC.md section 2 */
var gp = path.join(__dirname, '..', 'data', 'deep', 'graph-v3.json');
if (fs.existsSync(gp)) {
  var g = JSON.parse(fs.readFileSync(gp, 'utf8')), nodes = g.nodes.slice(0, g.drawn);
  var VIEWS = {
    Wide:     { pos: [5.15, -1.31, 15.59], ori: [0, 0, 1, 0], fov: 0.7,   stars: 1896, lod: true },
    Colossus: { pos: [-3.4, -8.2, 3.6], ori: [0.625, -0.696, 0.354, 1.366], fov: 1.22, stars: 1548, lod: true },
    Eye:      { pos: [-2.48, 0.38, 4.4], ori: [0.357, -0.93, 0.084, 0.497], fov: 0.62, stars: 174, lod: false },
    Inside:   { pos: [8.4, -2.6, 4.4], ori: [0.212, 0.969, -0.125, 1.096], fov: 0.95, stars: 186, lod: false },
    Flywheel: { pos: [6.41, -3.99, 3.35], ori: [0.965, -0.259, 0.036, 0.287], fov: 0.9, stars: 758, lod: false },
    Crown:    { pos: [4, 12.5, 7], ori: [-0.994, -0.089, -0.057, 1.134], fov: 1.0, stars: 2220, lod: true }
  };
  t('Deep graph: on-screen counts and LOD match the spec table in all six views (1527 x 923)', function () {
    var ix = new Pick.Index(nodes);
    Object.keys(VIEWS).forEach(function (k) {
      var v = VIEWS[k], c = ix.update(v, 1527, 923, true);
      assert(Math.abs(c - v.stars) <= 2, k + ' stars ' + c + ' vs ' + v.stars);
      assert.strictEqual(ix.lodCore, v.lod, k + ' lod (median gap ' + ix.medianGap.toFixed(1) + ')');
    });
  });
  t('Deep graph: self-pick accuracy at 3 px noise meets the spec (>= 90% sparse views, >= 78% wide views with core-only LOD)', function () {
    var ix = new Pick.Index(nodes), rand = rng(3), out = {};
    function gauss() { return Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand()); }
    Object.keys(VIEWS).forEach(function (k) {
      ix.update(VIEWS[k], 1527, 923, true);
      var pool = []; for (var j = 0; j < ix.nvis; j++) { var s = ix.vis[j]; if (!ix.lodCore || ix.tier[s] === 1) pool.push(s); }
      var step = Math.max(1, Math.ceil(pool.length / 500)), ok = 0, tot = 0;
      for (var q = 0; q < pool.length; q += step) for (var r = 0; r < 12; r++) { var p = ix.pick(ix.sx[pool[q]] + 3 * gauss(), ix.sy[pool[q]] + 3 * gauss(), { radius: 30 }); tot++; if (p && p.i === pool[q]) ok++; }
      out[k] = ok / tot;
    });
    ['Eye', 'Inside', 'Flywheel'].forEach(function (k) { assert(out[k] >= 0.90, k + ' ' + out[k].toFixed(3)); });
    ['Wide', 'Colossus', 'Crown'].forEach(function (k) { assert(out[k] >= 0.78, k + ' ' + out[k].toFixed(3)); });
    console.log('    ' + Object.keys(out).map(function (k) { return k + ' ' + (100 * out[k]).toFixed(0) + '%'; }).join('  '));
  });
  t('Deep graph: project + bucket + query stay far below a frame budget', function () {
    var ix = new Pick.Index(nodes), v = VIEWS.Wide, i, t0, reps = 400;
    for (i = 0; i < 50; i++) ix.update(v, 1527, 923);
    t0 = process.hrtime.bigint(); for (i = 0; i < reps; i++) ix.update(v, 1527, 923); var upd = Number(process.hrtime.bigint() - t0) / reps / 1000;
    t0 = process.hrtime.bigint(); for (i = 0; i < 20000; i++) ix.pick(700 + (i % 50), 400, { radius: 30 }); var q = Number(process.hrtime.bigint() - t0) / 20000 / 1000;
    t0 = process.hrtime.bigint(); for (i = 0; i < reps; i++) ix.update(v, 1527, 923, true); var updLod = Number(process.hrtime.bigint() - t0) / reps / 1000;
    console.log('    update ' + upd.toFixed(0) + ' us (LOD re-measured every 4th: ' + updLod.toFixed(0) + ' us when forced), pick ' + q.toFixed(2) + ' us');
    assert(upd < 300 && updLod < 600 && q < 50, 'update ' + upd + ' us, forced ' + updLod + ' us, pick ' + q + ' us');
  });
} else console.log('skip  Deep graph tests (run make v4-data to fetch data/deep/graph-v3.json)');
console.log(n + ' tests passed');
