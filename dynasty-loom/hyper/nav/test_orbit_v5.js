// node hyper/nav/test_orbit_v5.js: the v5 fixes to orbit.js (shipped as lib/orbit.js) from the nav review (no DOM; a fake element and clock).
//   release double step: the first frame after a release moves no more than a drag frame did (input between frames, and input before the frame);
//   lens glide: the release speed is kept (no brake at release) and the coast is capped at lensCoast px;
//   pinch: a small accidental twist does not roll the view, and the view eases level when the pinch ends; a deliberate twist rolls and stays.
//   v5 review (feel): no dead frame when the release comes a frame after the last move, and the pointerup's own move is applied; a held arrow
//   key turns at a steady rate; a twist just past the dead zone ends level (< 0.05 deg); the page's lens coast cap (hooks.lensCoast); a pinch
//   waiting for its frame is applied by flushGesture().
const assert = require('assert'), path = require('path');
const O = require(path.join(__dirname, 'orbit.js')), U = O.util;
let n = 0; const ok = (c, m) => { assert(c, m); n++; console.log('ok', m); };
const W = 1280, H = 720, DT = 1000 / 60;
function rig(o) {
  const L = {}, el = { addEventListener: (k, f) => { L[k] = f; }, removeEventListener: () => {}, getBoundingClientRect: () => ({ left: 0, top: 0 }), setPointerCapture: () => {}, clientWidth: W, clientHeight: H };
  let T = 1000; global.performance = { now: () => T };
  const c = new O.Core({ tau: 0.36 }); c.setPose([0, 0.6, 3.2], [0, 0, 0], [0, 1, 0], 0.7);
  const lensMoves = []; const hooks = Object.assign({ viewport: () => [W, H], lens: () => !!(o && o.lens), lensDrag: (dx, dy) => lensMoves.push([dx, dy]) }, (o && o.hooks) || {});
  c.hooks.lensDrag = (dx, dy) => lensMoves.push([dx, dy]);
  const KL = {}; const ctl = O.attach(el, c, hooks, { keyTarget: { addEventListener: (k, f) => { KL[k] = f; } }, raf: (o && o.raf) || null });
  const ev = (type, x, y, t, extra) => { T = t; L[type](Object.assign({ pointerId: 1, clientX: x, clientY: y, button: 0, buttons: type === 'pointerup' ? 0 : 1, pointerType: 'mouse', timeStamp: t, preventDefault() {} }, extra || {})); };
  return { c, ev, lensMoves, ctl, KL, setT: t => { T = t; } };
}
const wrap = a => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
// ---- release double step, both input orderings
for (const order of ['between', 'before']) {
  const { c, ev, setT } = rig(); let t = 2000, y = c.yaw(); const steps = [];
  const frame = () => { t += DT; setT(t); c.step(DT / 1000, t); const y2 = c.yaw(); steps.push(Math.abs(wrap(y2 - y))); y = y2; };
  // 'between': input stamped at the last frame's time arrives after that frame (the virtual clock of nav/tools/vt.js);
  // 'before': input stamped 4 ms before the next frame is handled just before it (a browser that aligns input to rAF)
  const at = () => order === 'between' ? t : t + DT - 4;
  frame(); ev('pointerdown', 400, 400, at()); frame();
  for (let i = 1; i <= 10; i++) { ev('pointermove', 400 + 20 * i, 400, at()); if (i < 10) frame(); }
  ev('pointerup', 600, 400, at()); for (let i = 0; i < 6; i++) frame();
  const k = steps.length - 6, drag = steps[k - 1], first = steps[k], second = steps[k + 1];
  ok(c.lastRelease && c.lastRelease.v && c.lastRelease.v[0] > 1000, order + ': the flick has momentum (' + (c.lastRelease.v || [0])[0].toFixed(0) + ' px/s)');
  ok(first <= drag * 1.3 + 1e-9, order + ': the first frame after the release moves ' + (first / drag).toFixed(2) + 'x a drag frame (the double step was 2x)');
  ok(second > 0.5 * drag, order + ': the coast carries on (' + (second / drag).toFixed(2) + 'x a drag frame)');
}
// ---- lens glide: no brake at the release, the coast capped
for (const v of [1300, 2600, 300]) {
  const c = new O.Core({ tau: 0.36 }); const mv = []; c.hooks.lensDrag = (dx, dy) => mv.push(Math.hypot(dx, dy));
  c.fling('lens', v, 0, W, H); for (let i = 0; i < 600 && (c.vel.lx || c.vel.ly); i++) c.step(1 / 60);
  const total = mv.reduce((a, b) => a + b, 0), f0 = mv[0] * 60;
  ok(f0 > 0.8 * v, v + ' px/s lens flick: the first coast frame keeps ' + (f0 / v * 100).toFixed(0) + '% of the release speed');
  ok(total <= 170 + 1e-6 && total > (v > 472 ? 160 : 0.9 * v * 0.36), v + ' px/s lens flick: coast ' + total.toFixed(1) + ' px (cap 170)');
}
// ---- pinch: twist dead zone and relevel
for (const [twistDeg, keep] of [[3, false], [6, false], [29, true]]) {
  const { c, ev } = rig(); let t = 3000; const r0 = c.roll(), cx = 640, cy = 360, R = 120, a = twistDeg * Math.PI / 180;
  const P = (id, ang, rad) => ({ pointerId: id, pointerType: 'touch', clientX: cx + Math.cos(ang) * rad, clientY: cy + Math.sin(ang) * rad });
  const tev = (type, id, ang, rad) => { t += 4; const p = P(id, ang, rad); ev(type, p.clientX, p.clientY, t, { pointerId: id, pointerType: 'touch' }); };
  tev('pointerdown', 1, Math.PI, R); tev('pointerdown', 2, 0, R);
  let maxRoll = 0;
  for (let i = 1; i <= 12; i++) { const ang = a * i / 12, rad = R * (1 + 0.5 * i / 12); tev('pointermove', 1, Math.PI + ang, rad); tev('pointermove', 2, ang, rad); maxRoll = Math.max(maxRoll, Math.abs(c.roll() - r0)); }
  const rollEnd = Math.abs(c.roll() - r0);
  tev('pointerup', 1, Math.PI + a, R * 1.5); tev('pointerup', 2, a, R * 1.5);
  for (let i = 0; i < 90; i++) c.step(1 / 60);
  const after = Math.abs(c.roll() - r0);
  if (!keep) { ok(maxRoll < 1e-9, twistDeg + ' deg accidental twist in a pinch: no roll while pinching (' + (maxRoll * 180 / Math.PI).toFixed(3) + ' deg)'); ok(after < 0.002, twistDeg + ' deg twist: level after the pinch (' + (after * 180 / Math.PI).toFixed(3) + ' deg)'); }
  else { ok(Math.abs(rollEnd - (a - 0.12)) < 0.01, twistDeg + ' deg deliberate twist rolls past the 0.12 rad dead zone (' + (rollEnd * 180 / Math.PI).toFixed(2) + ' deg)'); ok(Math.abs(after - rollEnd) < 1e-6, twistDeg + ' deg twist: the roll stays after the pinch'); }
}
// ---- v5 review: the release a frame after the last move (no dead frame); the pointerup's own move is applied
for (const upMove of [0, 14]) {
  const { c, ev, setT } = rig(); let t = 2000, y = c.yaw(); const steps = [];
  const frame = () => { t += DT; setT(t); c.step(DT / 1000, t); const y2 = c.yaw(); steps.push(Math.abs(wrap(y2 - y))); y = y2; };
  frame(); ev('pointerdown', 400, 400, t); frame();
  for (let i = 1; i <= 10; i++) { ev('pointermove', 400 + 17 * i, 400, t); frame(); }   // each move shown by the next frame
  const yBefore = c.yaw(); ev('pointerup', 570 + upMove, 400, t); const upStep = Math.abs(wrap(c.yaw() - yBefore));   // the release a frame later
  for (let i = 0; i < 4; i++) frame();
  const k = steps.length - 4, drag = steps[k - 1], first = steps[k];
  ok(first > 0.6 * drag && first <= drag * 1.3 + 1e-9, 'release a frame after the last move' + (upMove ? ' (the pointerup ' + upMove + ' px further on)' : '') + ': the first coast frame moves ' + (first / drag).toFixed(2) + 'x a drag frame (no dead frame)');
  if (upMove) ok(Math.abs(upStep - c.dragGain(W, H) * upMove) < 1e-9, 'the pointerup\'s own ' + upMove + ' px are applied (' + (upStep * 180 / Math.PI).toFixed(3) + ' deg)');
}
// ---- v5 review: a held arrow key turns at keyRate (75 deg/s) without a step per OS repeat
{
  const { c, KL } = rig(); let y = c.yaw(); const rates = []; let t = 0;
  const key = (type, k, rep) => KL[type]({ key: k, repeat: !!rep, preventDefault() {}, metaKey: false, ctrlKey: false, altKey: false });
  key('keydown', 'ArrowLeft', false);
  for (let f = 0; f < 150; f++) { t += DT; if (f > 30 && f % 2 === 0) key('keydown', 'ArrowLeft', true); c.step(DT / 1000, t); const y2 = c.yaw(); rates.push(Math.abs(wrap(y2 - y)) * 60 * 180 / Math.PI); y = y2; }
  const late = rates.slice(100, 150), mx = Math.max(...late), mn = Math.min(...late);
  ok(mx < 80 && mn > 70, 'held arrow key: a steady ' + mn.toFixed(1) + '-' + mx.toFixed(1) + ' deg/s (was about 470 deg/s, judder 7.8/6.8 deg a frame)');
  key('keyup', 'ArrowLeft'); let left = 0; for (let f = 0; f < 120; f++) { const y0 = c.yaw(); c.step(DT / 1000); left += Math.abs(wrap(c.yaw() - y0)); }
  ok(left * 180 / Math.PI < 12 && !c.moving(), 'held arrow key released: it eases out in ' + (left * 180 / Math.PI).toFixed(1) + ' deg and stops');
}
// ---- v5 review: a 12 deg twist (just past the dead zone) ends level
{
  const { c, ev } = rig(); let t = 3000; const r0 = c.roll(), cx = 640, cy = 360, R = 120, a = 12 * Math.PI / 180;
  const tev = (type, id, ang, rad) => { t += 4; ev(type, cx + Math.cos(ang) * rad, cy + Math.sin(ang) * rad, t, { pointerId: id, pointerType: 'touch' }); };
  tev('pointerdown', 1, Math.PI, R); tev('pointerdown', 2, 0, R);
  for (let i = 1; i <= 12; i++) { const ang = a * i / 12; tev('pointermove', 1, Math.PI + ang, R); tev('pointermove', 2, ang, R); }
  const peak = Math.abs(c.roll() - r0); tev('pointerup', 1, Math.PI + a, R); tev('pointerup', 2, a, R);
  for (let i = 0; i < 180; i++) c.step(1 / 60);
  const after = Math.abs(c.roll() - r0) * 180 / Math.PI;
  ok(peak > 0.05 && after < 0.05 && c.relevel === 0, '12 deg twist: rolled ' + (peak * 180 / Math.PI).toFixed(2) + ' deg, level after the pinch (' + after.toFixed(3) + ' deg, the relevel ended on the angle)');
}
// ---- v5 review: the page's lens coast cap
{
  const c = new O.Core({ tau: 0.36 }); const mv = []; c.hooks.lensDrag = (dx, dy) => mv.push(Math.hypot(dx, dy)); c.hooks.lensCoast = () => 34;
  c.fling('lens', 600, 0, W, H); for (let i = 0; i < 600 && (c.vel.lx || c.vel.ly); i++) c.step(1 / 60);
  const total = mv.reduce((a, b) => a + b, 0);
  ok(total <= 34 + 1e-6 && total > 30 && mv[0] * 60 > 0.8 * 600 * 0.8, 'hooks.lensCoast: a 600 px/s lens flick coasts ' + total.toFixed(1) + ' px (cap 34), first frame at ' + (mv[0] * 60).toFixed(0) + ' px/s');
}
// ---- v5 review: flushGesture applies a pinch waiting for its frame
{
  const q = []; const { c, ev, ctl } = rig({ raf: f => q.push(f) }); let t = 3000; const d0 = c.dist;
  const tev = (type, id, x) => { t += 4; ev(type, x, 360, t, { pointerId: id, pointerType: 'touch' }); };
  tev('pointerdown', 1, 520); tev('pointerdown', 2, 760); tev('pointermove', 1, 500); tev('pointermove', 2, 780);
  const before = c.dist; ctl.flushGesture(); const after = c.dist; q.forEach(f => f()); const later = c.dist;
  ok(before === d0 && after < d0 && later === after, 'flushGesture: the pending pinch lands at the frame start (distance ' + d0.toFixed(4) + ' -> ' + after.toFixed(4) + '), and its queued callback then does nothing');
}
console.log('orbit.js v5 fixes: ' + n + ' checks passed');
