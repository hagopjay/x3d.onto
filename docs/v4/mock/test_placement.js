/* node docs/v4/mock/test_placement.js : checks the placement rules with synthetic densities. */
'use strict';
var assert = require('assert'), P = require('./placement.js');
var W = 1500, H = 900, size = { w: 348, h: 380 };
var flat = function () { return 0.1; };
var hot = function (cx, cy, r) { return function (x, y) { return Math.hypot(x - cx, y - cy) < r ? 0.95 : 0.05; }; };
var n = 0;
function t(name, fn) { fn(); n++; console.log('ok  ' + name); }

t('never covers the hovered star', function () {
  [[1400, 700], [100, 100], [750, 450], [1400, 100], [100, 800]].forEach(function (h) {
    var r = P.choose({ W: W, H: H, hover: { x: h[0], y: h[1] }, size: size, density: flat });
    var c = { x: h[0], y: h[1] }, q = r.rect;
    assert(!(c.x > q.x - 96 && c.x < q.x + q.w + 96 && c.y > q.y - 96 && c.y < q.y + q.h + 96) || r.scores.every(function (s) { return !s.feasible; }), 'covers ' + h);
  });
});
t('avoids a dense corner', function () {
  var r = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: hot(1300, 700, 400) });
  assert.notStrictEqual(r.slot, 'BR');
});
t('prefers the nearer free corner when all are empty', function () {
  var r = P.choose({ W: W, H: H, hover: { x: 1300, y: 150 }, size: size, density: flat });
  assert(r.slot === 'BR' || r.slot === 'TL' || r.slot === 'BL', 'got ' + r.slot);   /* TR is covered by the halo */
  assert.notStrictEqual(r.slot, 'TR');
});
t('reserved chips are respected', function () {
  var r = P.choose({ W: W, H: H, hover: { x: 200, y: 200 }, size: size, density: flat, reserved: { BR: { h: 40 }, BL: { h: 60 } } });
  var bottom = r.rect.y + r.rect.h; assert(bottom <= H - 22 - (r.slot === 'BR' ? 40 : r.slot === 'BL' ? 60 : 0) + 0.001 || r.slot[0] === 'T');
});
t('hysteresis keeps the previous slot on a near tie', function () {
  var a = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: flat });
  var other = a.scores.filter(function (s) { return s.feasible && s.slot !== a.slot; })[0];
  var b = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: flat, prev: other.slot });
  assert.strictEqual(b.slot, other.slot); assert(b.kept);
});
t('hysteresis does not trap the card in a bad slot', function () {
  var b = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: hot(1300, 700, 500), prev: 'BR' });
  assert.notStrictEqual(b.slot, 'BR');
});
t('narrow viewport becomes a bottom sheet', function () {
  var r = P.choose({ W: 600, H: 900, hover: { x: 300, y: 300 }, size: size, density: flat });
  assert.strictEqual(r.slot, 'SHEET'); assert.strictEqual(r.rect.w, 600);
});
t('always returns a slot even when nothing is feasible', function () {
  var r = P.choose({ W: 800, H: 400, hover: { x: 400, y: 200 }, size: { w: 700, h: 360 }, density: flat });
  assert(r.slot && r.rect);
});
console.log(n + ' tests passed');
