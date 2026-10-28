/* node gobbler-v4/test/test_placement.js : placement rules on synthetic densities, plus a seeded fuzz over viewport, card and star positions. */
'use strict';
var assert = require('assert'), P = require('../src/placement.js');
var W = 1500, H = 900, size = { w: 348, h: 380 }, HALO = 96, M = 22;
var flat = function () { return 0.1; };
var hot = function (cx, cy, r) { return function (x, y) { return Math.hypot(x - cx, y - cy) < r ? 0.95 : 0.05; }; };
var n = 0;
function t(name, fn) { fn(); n++; console.log('ok  ' + name); }
function hitsHalo(rect, h) { var nx = Math.max(rect.x, Math.min(h.x, rect.x + rect.w)), ny = Math.max(rect.y, Math.min(h.y, rect.y + rect.h)); return Math.hypot(h.x - nx, h.y - ny) < HALO; }
function hits(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
function rng(seed) { var s = seed >>> 0; return function () { s = (s + 0x6D2B79F5) >>> 0; var t2 = s; t2 = Math.imul(t2 ^ (t2 >>> 15), t2 | 1); t2 ^= t2 + Math.imul(t2 ^ (t2 >>> 7), t2 | 61); return ((t2 ^ (t2 >>> 14)) >>> 0) / 4294967296; }; }

t('never covers the hovered star', function () {
  [[1400, 700], [100, 100], [750, 450], [1400, 100], [100, 800]].forEach(function (h) {
    var r = P.choose({ W: W, H: H, hover: { x: h[0], y: h[1] }, size: size, density: flat });
    assert(!r.fallback && !hitsHalo(r.rect, { x: h[0], y: h[1] }), 'covers ' + h);
  });
});
t('avoids a dense corner', function () {
  var r = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: hot(1300, 700, 400) });
  assert.notStrictEqual(r.slot, 'BR');
});
t('prefers a nearer free corner when all are empty', function () {
  var r = P.choose({ W: W, H: H, hover: { x: 1300, y: 150 }, size: size, density: flat });
  assert.notStrictEqual(r.slot, 'TR');          /* TR is under the halo */
  assert(r.scores.filter(function (s) { return s.slot === 'TR'; })[0].feasible === false);
});
t('reserved chip heights push the card clear of the chips in every corner', function () {
  var reserved = { TL: { h: 58 }, TR: { h: 36 }, BL: { h: 52 }, BR: { h: 44 } };
  ['TL', 'TR', 'BL', 'BR'].forEach(function (slot) {
    var r = P.slotRect(slot, W, H, size, M, reserved);
    if (slot[0] === 'T') assert.strictEqual(r.y, M + reserved[slot].h, slot); else assert.strictEqual(r.y + r.h, H - M - reserved[slot].h, slot);
    assert.strictEqual(r.x, slot[1] === 'L' ? M : W - M - size.w);
  });
  var res = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: flat, reserved: reserved });
  var chip = { TL: { x: 26, y: 22, w: 200, h: 48 }, TR: { x: W - 26 - 340, y: 22, w: 340, h: 26 }, BL: { x: 26, y: H - 22 - 42, w: 560, h: 42 }, BR: { x: W - 26 - 110, y: H - 22 - 34, w: 110, h: 34 } };
  Object.keys(chip).forEach(function (k) { assert(!hits(res.rect, chip[k]), res.slot + ' hits chip ' + k); });
});
t('obstacles are respected even when no reservation is given', function () {
  var ob = [{ x: 0, y: 0, w: 700, h: 120 }, { x: W - 700, y: H - 120, w: 700, h: 120 }];
  var res = P.choose({ W: W, H: H, hover: { x: 750, y: 450 }, size: size, density: flat, obstacles: ob });
  ob.forEach(function (o) { assert(!hits(res.rect, o)); });
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
t('hysteresis does not keep a slot that has become infeasible', function () {
  var b = P.choose({ W: W, H: H, hover: { x: 1300, y: 150 }, size: size, density: flat, prev: 'TR' });
  assert.notStrictEqual(b.slot, 'TR');
});
t('narrow viewport becomes a bottom sheet with no leader and a rect inside the viewport', function () {
  var r = P.choose({ W: 600, H: 900, hover: { x: 300, y: 300 }, size: size, density: flat });
  assert.strictEqual(r.slot, 'SHEET'); assert.strictEqual(r.edge, 'bottom'); assert.strictEqual(r.rect.w, 600 - 2 * M); assert.strictEqual(r.leader, null);
  assert(r.rect.y >= 0 && r.rect.y + r.rect.h <= 900 && r.rect.h <= 450 + 1e-9, JSON.stringify(r.rect));
  assert(!r.shrunk);                             /* 380 < 450: not cut */
});
t('sheet height is clamped to half the viewport and keeps its bottom margin', function () {
  var r = P.choose({ W: 600, H: 700, hover: { x: 300, y: 100 }, size: { w: 348, h: 900 }, density: flat });
  assert.strictEqual(r.rect.h, 350); assert.strictEqual(r.rect.y, 700 - 350 - 22); assert(r.shrunk);
});
t('the sheet moves to the top when the star is in the bottom half', function () {
  var r = P.choose({ W: 600, H: 900, hover: { x: 300, y: 760 }, size: size, density: flat });
  assert(r.rect.y < 100, 'y ' + r.rect.y);
});
t('the sheet clears the corner chips and, with the star mid-screen, still keeps its halo', function () {
  var reserved = { TL: { h: 50 }, TR: { h: 36 }, BL: { h: 106 }, BR: { h: 44 } };
  [[300, 450], [300, 300], [300, 700], [120, 150], [500, 820]].forEach(function (h) {
    var r = P.choose({ W: 600, H: 900, hover: { x: h[0], y: h[1] }, size: { w: 556, h: 520 }, density: flat, reserved: reserved });
    assert.strictEqual(r.slot, 'SHEET'); assert(!r.fallback, 'fallback at ' + h);
    assert(!hitsHalo(r.rect, { x: h[0], y: h[1] }), 'covers the star at ' + h + ' ' + JSON.stringify(r.rect));
    assert(r.rect.y >= M + 50 && r.rect.y + r.rect.h <= 900 - M - 106 + 1e-9, 'on a chip at ' + h + ' ' + JSON.stringify(r.rect));
  });
  var mid = P.choose({ W: 600, H: 900, hover: { x: 300, y: 450 }, size: { w: 556, h: 520 }, density: flat, reserved: reserved });
  assert(mid.shrunk && mid.rect.h >= P.MIN_H && mid.rect.h < 450, 'mid-screen sheet is cut to the room there is: ' + mid.rect.h);
});
t('the sheet is flagged as a fallback when neither edge has room', function () {
  var r = P.choose({ W: 600, H: 300, hover: { x: 300, y: 150 }, size: size, density: flat });
  assert.strictEqual(r.slot, 'SHEET'); assert(r.fallback && r.rect.h >= Math.min(P.MIN_H, 150) && r.rect.y >= 0 && r.rect.y + r.rect.h <= 300);
});
t('obstacles alone (no reservation) also keep the sheet off the chips', function () {
  var ob = [{ x: 4, y: 800, w: 592, h: 90 }, { x: 4, y: 14, w: 300, h: 56 }];
  var r = P.choose({ W: 600, H: 900, hover: { x: 300, y: 450 }, size: { w: 556, h: 520 }, density: flat, obstacles: ob });
  ob.forEach(function (q) { assert(!hits(r.rect, q), JSON.stringify(r.rect)); });
});
t('a card too tall for the viewport is shrunk rather than covering the star', function () {
  var r = P.choose({ W: 1000, H: 500, hover: { x: 500, y: 250 }, size: { w: 348, h: 560 }, density: flat });
  assert(r.shrunk && !r.fallback, JSON.stringify([r.shrunk, r.fallback]));
  assert(r.rect.h >= P.MIN_H && r.rect.h < 560 && r.rect.y >= 0 && r.rect.y + r.rect.h <= 500 && !hitsHalo(r.rect, { x: 500, y: 250 }));
});
t('fallback: nothing fits even shrunk, the farthest corner is used and flagged', function () {
  var r = P.choose({ W: 760, H: 300, hover: { x: 380, y: 150 }, size: { w: 700, h: 360 }, density: flat });
  assert(r.slot && r.rect && r.fallback && r.shrunk);
  assert(r.leader && isFinite(r.leader.x) && isFinite(r.leader.y));
});
t('density glitches (NaN, negative, > 1, throws) never break the choice', function () {
  [function () { return NaN; }, function () { return -5; }, function () { return 7; }, function () { throw new Error('off canvas'); }, undefined].forEach(function (d) {
    var r = P.choose({ W: W, H: H, hover: { x: 600, y: 400 }, size: size, density: d });
    assert(r.slot && r.scores.every(function (s) { return isFinite(s.score) && s.density >= 0 && s.density <= 1 && s.leader >= 0 && s.leader <= 1; }));
  });
});
t('a drifting pointer does not make the card jump (1 px steps, hysteresis on)', function () {
  var rand = rng(7), jumps = 0, runs = 60;
  for (var k = 0; k < runs; k++) {
    var x = 200 + rand() * 1100, y = 150 + rand() * 600, den = hot(rand() * W, rand() * H, 250 + rand() * 200), prev = null, last = null;
    for (var s = 0; s < 40; s++) {
      var r = P.choose({ W: W, H: H, hover: { x: x + s, y: y + s * 0.5 }, size: size, density: den, prev: prev });
      if (last && r.slot !== last) jumps++;
      prev = last = r.slot;
    }
  }
  assert(jumps <= runs * 0.5, 'jumps ' + jumps + ' in ' + runs + ' drifts');
});
t('fuzz: 4000 random cases keep every invariant', function () {
  var rand = rng(20261027), bad = [];
  for (var k = 0; k < 4000; k++) {
    var w = 300 + rand() * 2300, h = 300 + rand() * 1200, sz = { w: 200 + rand() * 220, h: 120 + rand() * 580 };
    var hv = { x: rand() * w, y: rand() * h }, den = hot(rand() * w, rand() * h, 80 + rand() * 500);
    var ob = rand() < 0.6 ? [{ x: 26, y: h - 64, w: 100 + rand() * 500, h: 42 }, { x: w - 140, y: 22, w: 114, h: 30 }] : [];
    var o = { W: w, H: h, hover: hv, size: sz, density: den, obstacles: ob, reserved: rand() < 0.6 ? { TL: { h: 50 }, TR: { h: 36 }, BL: { h: 52 }, BR: { h: 44 } } : undefined, prev: ['TL', 'TR', 'BL', 'BR', null][(rand() * 5) | 0] };
    var r = P.choose(o);
    var why = null;
    if (!r || !r.rect || !isFinite(r.rect.x + r.rect.y + r.rect.w + r.rect.h)) why = 'bad rect';
    else if (JSON.stringify(P.choose(o)) !== JSON.stringify(r)) why = 'not deterministic';
    else if (r.slot === 'SHEET') {
      if (w >= P.NARROW || r.leader !== null || r.rect.y < 0 || r.rect.y + r.rect.h > h + 1e-6 || r.rect.x < 0 || r.rect.x + r.rect.w > w + 1e-6) why = 'bad sheet';
      else if (!r.fallback && hitsHalo(r.rect, hv)) why = 'sheet covers star';
      else if (!r.fallback && ob.some(function (q) { return hits(r.rect, q); })) why = 'sheet hits obstacle';
    }
    else if (w < P.NARROW) why = 'narrow viewport without a sheet';
    else if (!r.leader || !isFinite(r.leader.x + r.leader.y)) why = 'no leader';
    else if (!r.fallback) {
      if (r.rect.x < 0 || r.rect.y < 0 || r.rect.x + r.rect.w > w + 1e-6 || r.rect.y + r.rect.h > h + 1e-6) why = 'outside viewport';
      else if (hitsHalo(r.rect, hv)) why = 'covers star';
      else if (ob.some(function (q) { return hits(r.rect, q); })) why = 'hits obstacle';
      else if (r.rect.w !== sz.w || r.rect.h > sz.h + 1e-9 || (r.shrunk && r.rect.h < P.MIN_H - 1e-9) || (!r.shrunk && r.rect.h !== sz.h)) why = 'size mismatch';
      else if (Math.abs(Math.max(r.rect.x, Math.min(hv.x, r.rect.x + r.rect.w)) - r.leader.x) > 1e-6 || Math.abs(Math.max(r.rect.y, Math.min(hv.y, r.rect.y + r.rect.h)) - r.leader.y) > 1e-6) why = 'leader off the nearest point';
    }
    if (why) bad.push(why + ' ' + JSON.stringify({ w: w, h: h, sz: sz, hv: hv }));
  }
  assert.strictEqual(bad.length, 0, bad.length + ' violations, first: ' + bad[0]);
});
console.log(n + ' tests passed');
