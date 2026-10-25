'use strict';
// 2D overlay: sun glare, atmosphere limb, labels with collision avoidance, hover ring, scale ladder, sparks, village mini-map.  All drawn from the same camera the X3D scene uses.
const OV = { c: null, x: null, w: 0, h: 0, dpr: 1, sparks: [], lastStrike: -1, mini: null, mx: null };
const fmtD = m => { const a = Math.abs(m); if (a < 1) return (m * 100).toFixed(0) + ' cm'; if (a < 1000) return (a < 10 ? m.toFixed(1) : m.toFixed(0)) + ' m'; if (a < 1e7) return (m / 1000 < 100 ? (m / 1000).toFixed(1) : (m / 1000).toFixed(0)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + ' km'; if (a < 1.2e10) return (m / 1e6).toLocaleString('en', { maximumFractionDigits: 0 }) + ' Mm'; const au = m / AU; return (au < 10 ? au.toFixed(2) : au.toFixed(1)) + ' AU'; };
function ovInit() { OV.c = document.getElementById('ov'); OV.x = OV.c.getContext('2d'); OV.mini = document.getElementById('mini'); OV.mx = OV.mini.getContext('2d'); ovResize(); window.addEventListener('resize', ovResize); }
function ovResize() { OV.dpr = Math.min(2, window.devicePixelRatio || 1); OV.w = innerWidth; OV.h = innerHeight; OV.c.width = OV.w * OV.dpr; OV.c.height = OV.h * OV.dpr; OV.x.setTransform(OV.dpr, 0, 0, OV.dpr, 0, 0); }
// distance from a ray (o, unit d, up to length L) to a sphere centre, relative to the sphere radius (<1 means the sphere blocks the ray)
function occ(o, d, L, c, r) { const oc = V.sub(c, o), t = clamp(V.dot(oc, d), 0, L), p = V.madd(o, d, t); return V.len(V.sub(c, p)) / r; }
function chip(x, y, text, o = {}) {
  const c = OV.x; c.font = (o.bold ? '600 ' : '') + (o.size || 12) + 'px -apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif'; const w = c.measureText(text).width + 12, h = (o.size || 12) + 8, sub = o.sub ? (c.font = '11px -apple-system,Inter,sans-serif', c.measureText(o.sub).width + 12) : 0, W = Math.max(w, sub), H = h + (o.sub ? 13 : 0);
  const rx = Math.round(x - (o.anchor === 'l' ? 0 : W / 2)), ry = Math.round(y - H);
  return { x: rx, y: ry, w: W, h: H, draw() {
    c.globalAlpha = o.alpha == null ? 1 : o.alpha; c.fillStyle = o.hot ? 'rgba(40,60,110,.88)' : 'rgba(6,10,20,.66)'; c.strokeStyle = o.hot ? 'rgba(130,180,255,.9)' : 'rgba(80,110,170,.45)'; c.lineWidth = 1; c.beginPath(); c.roundRect(rx + .5, ry + .5, W, H, 6); c.fill(); c.stroke();
    c.font = (o.bold ? '600 ' : '') + (o.size || 12) + 'px -apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif'; c.fillStyle = o.color || '#e6eeff'; c.textBaseline = 'middle'; c.textAlign = 'left'; c.fillText(text, rx + 6, ry + h / 2 + .5);
    if (o.sub) { c.font = '11px -apple-system,Inter,sans-serif'; c.fillStyle = '#8fa2c8'; c.fillText(o.sub, rx + 6, ry + h + 6); } c.globalAlpha = 1; } };
}
function drawOverlay(dt, now) {
  const c = OV.x, W = OV.w, H = OV.h; c.clearRect(0, 0, W, H); if (!E.ready || !E.camT) return; const S = E.S, view = E.viewMatrix(); OV.view = view;
  c.save(); c.globalCompositeOperation = 'lighter';
  drawSun(c, view, S); drawLimbs(c, view, S); c.restore();
  drawSparks(c, view, S, dt, now);
  if (UI.labelsOn) drawLabels(c, view, S);
  drawHover(c, view, S);
  drawLadder(c);
  drawMini(S);
}
// elevation angle (radians) of the terrain horizon toward a direction (town coordinates), from a coarse ray march over the real height field
function horizonAngle(dirT) {
  const h = Math.hypot(dirT[0], dirT[2]); if (h < 1e-6) return 0; const ux = dirT[0] / h, uz = dirT[2] / h, x0 = E.camT[0], z0 = E.camT[2], y0 = E.camT[1]; let best = -0.05;
  for (const d of [60, 150, 300, 600, 1000, 1600, 2400, 3500, 5000, 7000, 10000, 14000, 20000]) { const a = Math.atan2(terrainH(x0 + ux * d, z0 + uz * d) - y0, d); if (a > best) best = a; }
  return best;
}
// ---------------------------------------------------------------- sun glare / corona
function drawSun(c, view, S) {
  const p = view.project([0, 0, 0]); if (!p) return; const camS = E.camS, d = V.norm(V.mul(camS, -1)), L = V.len(camS);
  let vis = clamp(Math.min(occ(camS, d, L, S.E, RE * 1.001), occ(camS, d, L, S.M, RM * 1.001)) - 0.995, 0, 0.3) / 0.3; vis = smooth(0, 1, vis);
  if (E.near && E.alt < 3000) { const hz = horizonAngle(S.sunT); vis *= smooth(-0.002, 0.006, S.sunElev - hz); }
  if (E.near && S.sunElev < -1.2 * D2R) vis = 0; if (!E.near || E.alt > 50000) { } else vis *= smooth(-1.5, 0.5, S.sunElev / D2R);
  const disc = RS * p[3]; let eclipse = 0;
  { const mo = V.sub(S.M, camS), dm = V.len(mo), sepAng = Math.acos(clamp(V.dot(V.norm(mo), d), -1, 1)), rM = Math.asin(clamp(RM / dm, 0, 1)), rS = Math.asin(clamp(RS / L, 0, 1)); eclipse = clamp((rM + rS - sepAng) / (2 * Math.min(rM, rS)), 0, 1); E.eclipse = { sep: sepAng, rM, rS, cover: clamp((rM + rS - sepAng) / (2 * rS), 0, 1), dm }; }
  const X = p[0], Y = p[1]; if (!isFinite(E.eclipse.cover)) E.eclipse.cover = 0; if (!isFinite(X) || !isFinite(Y) || !isFinite(disc)) return; if (X < -400 || X > OV.w + 400 || Y < -400 || Y > OV.h + 400) return;
  const k = E.near ? 1 : 0.8, R = clamp(disc * 7, 38, 420) * (1 - 0.82 * smooth(0.6, 1, E.eclipse.cover) * 0.6), col = E.sky ? E.sky.day : 1;
  const warm = E.near ? clamp(1 - S.sunElev / (22 * D2R), 0, 1) : 0.15, cR = 255, cG = Math.round(236 - 80 * warm), cB = Math.round(205 - 130 * warm);
  const dim = 1 - 0.93 * smooth(0.82, 1.0, E.eclipse.cover);
  let g = c.createRadialGradient(X, Y, 0, X, Y, R); g.addColorStop(0, `rgba(${cR},${cG},${cB},${0.85 * vis * dim * k})`); g.addColorStop(0.18, `rgba(${cR},${cG},${cB},${0.38 * vis * dim * k})`); g.addColorStop(1, `rgba(${cR},${cG},${cB},0)`); c.fillStyle = g; c.fillRect(X - R, Y - R, R * 2, R * 2);
  const R2 = R * 3.4; g = c.createRadialGradient(X, Y, R * 0.3, X, Y, R2); g.addColorStop(0, `rgba(${cR},${cG - 30},${cB - 30},${0.16 * vis * dim * k})`); g.addColorStop(1, `rgba(${cR},${cG - 30},${cB - 30},0)`); c.fillStyle = g; c.fillRect(X - R2, Y - R2, R2 * 2, R2 * 2);
  if (E.eclipse.cover > 0.92) { // corona: only when the Moon covers the disc
    const f = smooth(0.92, 1.0, E.eclipse.cover), Rc = Math.max(disc * 4.6, 24), r0 = Math.max(disc * 0.97, 3); const gg = c.createRadialGradient(X, Y, 0, X, Y, Rc), q0 = r0 / Rc; gg.addColorStop(0, 'rgba(0,0,0,0)'); gg.addColorStop(Math.max(0, q0 - 0.002), 'rgba(0,0,0,0)'); gg.addColorStop(q0, `rgba(255,250,240,${0.85 * f})`); gg.addColorStop(q0 + (1 - q0) * 0.12, `rgba(235,240,255,${0.55 * f})`); gg.addColorStop(q0 + (1 - q0) * 0.4, `rgba(170,190,255,${0.2 * f})`); gg.addColorStop(1, 'rgba(120,150,255,0)'); c.fillStyle = gg; c.fillRect(X - Rc, Y - Rc, Rc * 2, Rc * 2);
    c.strokeStyle = `rgba(235,240,255,${0.35 * f})`; c.lineWidth = 1; for (let i = 0; i < 18; i++) { const a = i * TAU / 18 + 0.3 * Math.sin(i * 3.7), L2 = Rc * (1.0 + 0.9 * Math.abs(Math.sin(i * 2.3 + 1))); c.beginPath(); c.moveTo(X + Math.cos(a) * disc * 1.02, Y + Math.sin(a) * disc * 1.02); c.lineTo(X + Math.cos(a) * L2, Y + Math.sin(a) * L2); c.stroke(); } }
  // glare streaks and a few lens ghosts toward the centre of the screen
  if (vis * dim > 0.05 && R > 60) {
    c.strokeStyle = `rgba(255,235,200,${0.20 * vis * dim})`; c.lineWidth = 1.2; for (const [ox, oy] of [[1, 0], [0, 1], [0.7, 0.7], [0.7, -0.7]]) { c.beginPath(); c.moveTo(X - ox * R * 2.4, Y - oy * R * 2.4); c.lineTo(X + ox * R * 2.4, Y + oy * R * 2.4); c.stroke(); }
    const cx = OV.w / 2, cy = OV.h / 2; for (const [t, rr, a] of [[0.35, 0.22, 0.10], [0.6, 0.12, 0.09], [1.1, 0.30, 0.06], [1.6, 0.18, 0.07]]) { const gx = X + (cx - X) * t, gy = Y + (cy - Y) * t, r2 = R * rr * 2.2; const gh = c.createRadialGradient(gx, gy, 0, gx, gy, r2); gh.addColorStop(0, `rgba(180,210,255,${a * vis * dim})`); gh.addColorStop(1, 'rgba(180,210,255,0)'); c.fillStyle = gh; c.beginPath(); c.arc(gx, gy, r2, 0, TAU); c.fill(); }
  }
}
// ---------------------------------------------------------------- atmosphere limb of the Earth (and a hint of earthshine)
function drawLimbs(c, view, S) {
  const dE = V.len(V.sub(E.camS, S.E)); if (dE > RE * 60 || dE < RE * 1.0008) return; const pc = view.project(S.E); if (!pc) return;
  const ang = Math.asin(RE / dE), Rpx = Math.tan(ang) * view.sy; if (Rpx < 12 || pc[0] < -Rpx * 2 || pc[0] > OV.w + Rpx * 2 || pc[1] < -Rpx * 2 || pc[1] > OV.h + Rpx * 2) return;
  const qi = Q.conj(E.qCamT), sdir = Q.rot(qi, S.qInv ? Q.rot(S.qInv, V.norm(V.sub([0, 0, 0], S.E))) : [0, 0, 1]); // direction to the Sun in camera space
  // angular step so that one segment is about 3 px long; only the part of the ring that can be on screen is drawn
  const W = OV.w, Hh = OV.h, pad = 120, thick = clamp(Rpx * 0.0105, 3, 90), step = clamp(3 / Rpx, 0.0009, 0.05);
  const onS = a => { const x = pc[0] + Math.cos(a) * Rpx, y = pc[1] - Math.sin(a) * Rpx; return x > -pad && x < W + pad && y > -pad && y < Hh + pad; };
  const arcs = []; let start = null;
  for (let a = 0; a < TAU + 1e-6; a += Math.min(step * 8, 0.02)) { const v = onS(a); if (v && start === null) start = a; if (!v && start !== null) { arcs.push([start, a]); start = null; } } if (start !== null) arcs.push([start, TAU]);
  let budget = 900;
  for (const [a0, a1] of arcs) {
    const n = Math.max(1, Math.min(Math.ceil((a1 - a0) / step), budget)); budget -= n; if (budget <= 0) break; const da = (a1 - a0) / n;
    for (let j = 0; j < 5; j++) {
      const rr = Rpx + thick * (0.15 + j * 0.55), lw = thick * (1.0 + j * 0.55), a_j = 0.34 * Math.pow(1 - j / 5.5, 2);
      for (let i = 0; i < n; i++) { const a = a0 + (i + 0.5) * da, u = [Math.cos(a), Math.sin(a), 0], lit = clamp(0.5 + 0.55 * V.dot(u, sdir) - 0.25 * Math.max(0, sdir[2]), 0, 1), alpha = a_j * Math.pow(lit, 1.5); if (alpha < 0.004) continue;
        c.strokeStyle = `rgba(${90 + 60 * lit | 0},${160 + 50 * lit | 0},255,${alpha})`; c.lineWidth = lw; c.beginPath(); c.arc(pc[0], pc[1], rr, -(a + da * 0.55), -(a - da * 0.55)); c.stroke(); } }
  }
}
// ---------------------------------------------------------------- labels
function drawLabels(c, view, S) {
  const placed = [], out = []; const add = (e, wx, wy, text, o) => { const ch = chip(wx, wy, text, o); for (const p of placed) if (ch.x < p.x + p.w + 3 && ch.x + ch.w + 3 > p.x && ch.y < p.y + p.h + 2 && ch.y + ch.h + 2 > p.y) return false; placed.push(ch); out.push(ch); return true; };
  const cand = []; for (const e of E.reg) { if (!e.lab || !e.on) continue; const t = e.tc, p = view.projectTown(t); if (!p) continue; const px = (e.r || 1) * p[3]; if (px < (e.minPx || 4)) continue; if (e.maxD && V.len(V.sub(t, E.camT)) > e.maxD) continue; if (p[0] < -50 || p[0] > OV.w + 50 || p[1] < -30 || p[1] > OV.h + 30) continue; cand.push({ e, p, px, pr: (e.pri || 0) * 1e4 + Math.min(px, 9999) }); }
  cand.sort((a, b) => b.pr - a.pr); let n = 0;
  const maxL = document.body.classList.contains('cinema') ? 16 : 70; for (const { e, p, px } of cand) { if (n > maxL) break; const hot = UI.hover === e || UI.pin === e; const o = { bold: e.cat === 'body' || e.cat === 'town', size: e.cat === 'body' ? 13 : 12, hot, color: e.col || '#e6eeff', sub: hot ? e.sub && e.sub() : (e.subAlways && e.subAlways()) };
    const lift = Math.min(px, 60) + 8; if (add(e, p[0], p[1] - lift, e.label || e.name, o)) { n++; const ch = out[out.length - 1]; if (lift > 14) { c.strokeStyle = 'rgba(140,175,235,.4)'; c.lineWidth = 1; c.beginPath(); c.moveTo(p[0], p[1] - Math.min(px, 60)); c.lineTo(p[0], ch.y + ch.h); c.stroke(); } } }
  for (const ch of out) ch.draw();
}
function drawHover(c, view, S) {
  for (const e of [UI.hover, UI.pin]) { if (!e || !e.on) continue; const p = view.projectTown(e.tc); if (!p) continue; const rpx = Math.max(10, (e.r || 1) * p[3] * 1.15); c.strokeStyle = e === UI.pin ? 'rgba(255,207,122,.95)' : 'rgba(150,200,255,.95)'; c.lineWidth = 1.6; c.setLineDash([5, 4]); c.lineDashOffset = -(performance.now() / 60) % 18;
    if (e.box) { c.strokeStyle = e === UI.pin ? 'rgba(255,207,122,.95)' : 'rgba(150,200,255,.95)'; const q = e.box(view); if (q) { c.beginPath(); c.moveTo(q[0][0], q[0][1]); for (const v of q.slice(1)) c.lineTo(v[0], v[1]); c.closePath(); c.stroke(); } } else { c.beginPath(); c.arc(p[0], p[1], rpx, 0, TAU); c.stroke(); } c.setLineDash([]); }
}
// ---------------------------------------------------------------- scale ladder (left edge)
const LADDER = [[3.6e11, 'constellation shell'], [1.496e11, 'Earth orbit (1 AU)'], [6.957e8, 'Sun radius'], [3.844e8, 'Moon orbit'], [6.371e6, 'Earth radius'], [4e5, 'ISS altitude'], [1.2e4, 'airliner'], [3.0e2, 'village'], [20, 'plaza'], [1.75, 'human']];
function ladderY(m, y0, y1) { const t = (Math.log10(clamp(m, 0.3, 4e12)) - Math.log10(0.3)) / (Math.log10(4e12) - Math.log10(0.3)); return y1 - t * (y1 - y0); }
function drawLadder(c) {
  if (document.body.classList.contains('cinema')) return; const y0 = Math.max(150, OV.h * 0.2), y1 = OV.h - 150, x = 22; c.save(); c.strokeStyle = 'rgba(150,175,225,.5)'; c.lineWidth = 1; c.beginPath(); c.moveTo(x, y0); c.lineTo(x, y1); c.stroke();
  c.font = '10.5px ui-monospace,Menlo,monospace'; c.textBaseline = 'middle';
  for (let k = 0; k <= 12; k++) { const y = ladderY(Math.pow(10, k), y0, y1); c.strokeStyle = 'rgba(150,175,225,.35)'; c.beginPath(); c.moveTo(x - 3, y); c.lineTo(x + (k % 3 === 0 ? 7 : 4), y); c.stroke(); if (k % 3 === 0) { c.fillStyle = 'rgba(130,150,190,.8)'; c.fillText('10^' + k + ' m', x + 10, y); } }
  const w = E.pose ? E.pose.w : 1; let near = 0, bd = 1e9; for (const [m, name] of LADDER) { const d = Math.abs(Math.log10(m / w)); if (d < bd) { bd = d; near = name; } }
  for (const [m, name] of LADDER) { const y = ladderY(m, y0, y1), hot = name === near && bd < 0.5; c.fillStyle = hot ? '#ffd88a' : 'rgba(170,190,235,.85)'; c.beginPath(); c.arc(x, y, hot ? 3.5 : 2.4, 0, TAU); c.fill(); c.font = (hot ? '600 ' : '') + '11px -apple-system,Inter,sans-serif'; c.fillStyle = hot ? '#ffe3ad' : 'rgba(150,170,210,.75)'; c.textAlign = 'left'; c.fillText(name, x + 52 + 12 * 0, y - 0.0); }
  const yc = ladderY(w, y0, y1); c.fillStyle = '#7db2ff'; c.beginPath(); c.moveTo(x - 9, yc - 5); c.lineTo(x - 1, yc); c.lineTo(x - 9, yc + 5); c.closePath(); c.fill(); c.font = '600 11.5px ui-monospace,Menlo,monospace'; c.fillStyle = '#d6e6ff'; c.textAlign = 'left'; c.fillText(fmtD(w), x + 10, yc - 11);
  c.restore();
}
// ---------------------------------------------------------------- sparks at the smithy (world space, town coordinates)
function drawSparks(c, view, S, dt, now) {
  const ax = L_ANVIL[0], az = L_ANVIL[1]; const dx = E.camT[0] - ax, dz = E.camT[2] - az; if (dx * dx + dz * dz > 120 * 120) { OV.sparks.length = 0; return; }
  const idle = nd('Idle_P08'); if (idle) { const f = idle.fraction_changed; if (typeof f === 'number') { if (OV.lastF != null && OV.lastF < 0.66 && f >= 0.66) { for (let i = 0; i < 26; i++) { const a = Math.random() * TAU, sp = 1.5 + Math.random() * 3.2; OV.sparks.push({ p: [ax, 0.95, az - 0.1], v: [Math.cos(a) * sp, 2.2 + Math.random() * 3.0, Math.sin(a) * sp], t: 0, life: 0.5 + Math.random() * 0.7 }); } UI.onStrike && UI.onStrike(); } OV.lastF = f; } }
  c.save(); c.globalCompositeOperation = 'lighter';
  for (const s of OV.sparks) { s.t += dt; s.v[1] -= 9.8 * dt; s.p = [s.p[0] + s.v[0] * dt, Math.max(0.03, s.p[1] + s.v[1] * dt), s.p[2] + s.v[2] * dt]; const q = view.projectTown(s.p); if (!q) continue; const a = clamp(1 - s.t / s.life, 0, 1), r = Math.max(1.2, 0.035 * q[3]); c.fillStyle = `rgba(255,${150 + 90 * a | 0},${60 + 80 * a * a | 0},${a})`; c.beginPath(); c.arc(q[0], q[1], r * (0.4 + a), 0, TAU); c.fill(); }
  c.restore(); OV.sparks = OV.sparks.filter(s => s.t < s.life);
}
const L_ANVIL = [46.0, 26.2];
// ---------------------------------------------------------------- mini-map of the village
function drawMini(S) {
  const m = OV.mini, show = E.near && E.alt < 15000 && !document.body.classList.contains('cinema'); if (m.style.display !== (show ? 'block' : 'none')) m.style.display = show ? 'block' : 'none'; if (!show || !UI.town) return;
  const g = OV.mx, W = m.width, Hh = m.height, sc = W / 560, cx = W / 2, cy = Hh / 2; g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, Hh);
  const P = (x, z) => [cx + x * sc, cy + z * sc]; g.save(); g.beginPath(); g.arc(cx, cy, W / 2 - 2, 0, TAU); g.clip(); g.fillStyle = 'rgba(30,48,28,.9)'; g.fillRect(0, 0, W, Hh);
  g.strokeStyle = 'rgba(190,160,110,.8)'; for (const r of UI.town.roads) { g.lineWidth = Math.max(1.2, r.w * sc); g.beginPath(); r.pts.forEach((p, i) => { const q = P(p[0], p[1]); i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]); }); g.stroke(); }
  g.fillStyle = 'rgba(150,150,150,.9)'; const pq = P(0, 0); g.beginPath(); g.arc(pq[0], pq[1], UI.town.plaza_r * sc, 0, TAU); g.fill(); g.fillStyle = 'rgba(70,130,190,.9)'; g.beginPath(); g.arc(pq[0], pq[1], 3.2 * sc, 0, TAU); g.fill();
  for (const b of UI.town.houses) { g.save(); const q = P(b.x, b.z); g.translate(q[0], q[1]); g.rotate(-b.rot); g.fillStyle = b.id === 'B02' ? '#aeb4c0' : '#c9704a'; g.fillRect(-b.w * sc / 2, -b.d * sc / 2, b.w * sc, b.d * sc); g.restore(); }
  for (const e of E.reg) if (e.cat === 'person') { const t = e.tc; const q = P(t[0], t[2]); g.fillStyle = e === UI.pin ? '#ffcf7a' : '#fff'; g.beginPath(); g.arc(q[0], q[1], 2.4, 0, TAU); g.fill(); }
  const ct = E.camT, q = P(ct[0], ct[2]), fw = E.fwdT, ang = Math.atan2(fw[0], fw[2]), fov = 0.9; g.fillStyle = 'rgba(125,178,255,.28)'; g.beginPath(); g.moveTo(q[0], q[1]); g.arc(q[0], q[1], 70, Math.PI / 2 - ang - fov * 0.8, Math.PI / 2 - ang + fov * 0.8); g.closePath(); g.fill(); g.fillStyle = '#7db2ff'; g.beginPath(); g.arc(q[0], q[1], 3.5, 0, TAU); g.fill();
  const sd = S.sunT; g.strokeStyle = 'rgba(255,207,122,.9)'; g.lineWidth = 2; const sa = [sd[0], sd[2]], sl = Math.hypot(sa[0], sa[1]) || 1; g.beginPath(); g.moveTo(cx + sa[0] / sl * (W / 2 - 24), cy + sa[1] / sl * (W / 2 - 24)); g.lineTo(cx + sa[0] / sl * (W / 2 - 8), cy + sa[1] / sl * (W / 2 - 8)); g.stroke();
  g.restore(); g.fillStyle = '#9fb4e0'; g.font = '11px -apple-system,Inter,sans-serif'; g.fillText('N', cx - 3, 14); g.strokeStyle = 'rgba(100,130,190,.6)'; g.lineWidth = 1.5; g.beginPath(); g.arc(cx, cy, W / 2 - 1.5, 0, TAU); g.stroke();
}
