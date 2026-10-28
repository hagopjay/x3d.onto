/* node gobbler-v4/test/test_density.js */
'use strict';
var assert = require('assert'), D = require('../src/density.js'), P = require('../src/placement.js'), n = 0;
function t(name, fn) { fn(); n++; console.log('ok  ' + name); }
function frame(w, h, f) { var d = new Uint8ClampedArray(w * h * 4); for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) { var v = f(x, y) * 255, i = (y * w + x) * 4; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; } return d; }

t('fromLuma: bright regions read as subject, background as empty, clamped to 0..1', function () {
  var w = 64, h = 36, d = D.fromLuma(frame(w, h, function (x, y) { return x > 40 ? 0.8 : 0.0; }), w, h, 1280, 720);
  assert(d(1200, 300) > 0.95 && d(100, 300) < 0.02 && d(-50, -50) <= 1 && d(5000, 5000) >= 0);
  assert(d.meanLuma > 0.1);
});
t('fromLuma: a black readback reports meanLuma ~ 0 so the caller can fall back', function () {
  assert(D.fromLuma(new Uint8ClampedArray(64 * 36 * 4), 64, 36, 1280, 720).meanLuma < 1e-6);
});
t('fromStars: cells with 3+ stars are full, empty cells are empty', function () {
  var xs = [], ys = [], vis = []; for (var i = 0; i < 40; i++) { xs.push(1000 + (i % 7)); ys.push(500 + (i % 5)); vis.push(i); }
  var d = D.fromStars(xs, ys, vis, 40, 1280, 720);
  assert(d(1003, 502) > 0.9 && d(100, 100) === 0);
});
t('both sources steer the card away from the subject in the same direction', function () {
  var W = 1280, H = 720, w = 64, h = 36;
  var luma = D.fromLuma(frame(w, h, function (x) { return x > 40 ? 0.8 : 0.02; }), w, h, W, H);
  var xs = [], ys = [], vis = []; for (var i = 0; i < 800; i++) { xs.push(850 + (i * 37) % 400); ys.push(40 + (i * 53) % 640); vis.push(i); }
  var stars = D.fromStars(xs, ys, vis, 800, W, H);
  [luma, stars].forEach(function (den) { var r = P.choose({ W: W, H: H, hover: { x: 640, y: 360 }, size: { w: 348, h: 380 }, density: den }); assert(r.slot === 'TL' || r.slot === 'BL', r.slot); });
});
console.log(n + ' tests passed');
