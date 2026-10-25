'use strict';
// Engine: binds the X3D scene (solar-town.x3d) to the astronomy model, the camera rig and the sky/lighting model.  The scene file holds all geometry and the keyframed animation;
// this file only moves the Sun/Earth/Moon system relative to the village (floating origin = village), drives the camera and updates lights.
const E = { B: null, nodes: {}, S: null, t: Date.now() / 1000, rate: 1, paused: false, last: 0, fov: 0.9, hidden: {}, ready: false, picks: [], onFrame: [], flight: null, tooltipMs: 0, quality: 'high' };
const nd = n => { if (n in E.nodes) return E.nodes[n]; let v = null; try { v = E.B.currentScene.getNamedNode(n); } catch (e) { } if (v) E.nodes[n] = v; return v; };
const set = (n, f, v) => { const x = nd(n); if (x) x[f] = v; };
const SFV = a => new X3D.SFVec3f(a[0], a[1], a[2]), SFR = a => new X3D.SFRotation(a[0], a[1], a[2], a[3]), SFC = a => new X3D.SFColor(a[0], a[1], a[2]);
const lastSet = {};
function setIf(n, f, v, eps = 1e-9) { // set a field only if it changed (arrays of numbers compared)
  const k = n + '.' + f, o = lastSet[k]; if (o && o.length === v.length) { let same = true; for (let i = 0; i < v.length; i++) if (Math.abs(o[i] - v[i]) > eps * (1 + Math.abs(v[i]))) { same = false; break; } if (same) return; }
  lastSet[k] = v.slice(); const x = nd(n); if (!x) return; x[f] = toX(f, v);
}
const MFC = a => { const arr = []; for (let i = 0; i < a.length; i += 3) arr.push(new X3D.SFColor(a[i], a[i + 1], a[i + 2])); return new X3D.MFColor(...arr); };
function toX(f, v) {
  if (f === 'skyColor' || f === 'groundColor') return MFC(v); if (f === 'skyAngle' || f === 'groundAngle') return new X3D.MFFloat(...v);
  if (v.length === 1) return v[0]; if (v.length === 4) return SFR(v); if (f === 'color' || f.endsWith('Color')) return SFC(v); return SFV(v);
}
// ------------------------------------------------------------------ focus frames
const ECL = { E: [1, 0, 0], U: [0, 1, 0], N: [0, 0, -1] };
const FOCUS = {
  system: { label: 'Constellation', minD: 3e9, maxD: 2.5e13, pos: () => [0, 0, 0], basis: () => ECL },
  sun: { label: 'Sun', minD: RS * 1.25, maxD: 2.5e13, pos: () => [0, 0, 0], basis: () => ECL },
  earth: { label: 'Earth', minD: RE * 1.12, maxD: 2.5e13, pos: () => E.S.E, basis: () => ECL },
  moon: { label: 'Moon', minD: RM * 1.12, maxD: 2.5e13, pos: () => E.S.M, basis: () => ECL },
  town: { label: 'Village', minD: 0.45, maxD: 2e12, pos: c => E.S.fromTown([c.pan[0], terrainH(c.pan[0], c.pan[1]) + (c.h || 1.4), c.pan[1]]), basis: () => ({ E: E.S.X, U: E.S.Y, N: V.mul(E.S.Z, -1) }) },
};
function focusPos(c) { const f = FOCUS[c.f]; if (f) return f.pos(c); if (c.f === 'obj') return E.objPos(c.id); return [0, 0, 0]; }
function focusBasis(c) { const f = FOCUS[c.f]; if (f) return f.basis(c); if (c.f === 'obj') return E.objBasis(c.id); return ECL; }
function focusMin(c) { const f = FOCUS[c.f]; if (f) return f.minD; return E.objMin ? E.objMin(c.id) : 1; }
function focusMax(c) { const f = FOCUS[c.f]; return f ? f.maxD : 2.5e13; }
const cam = { f: 'system', id: null, d: 1.1e12, az: 0.5, el: 0.4, pan: [0, 0], h: 1.4, look: false };
const copyCam = c => ({ f: c.f, id: c.id, d: c.d, az: c.az, el: c.el, pan: c.pan.slice(), h: c.h, look: !!c.look });
function poseOf(c) { // pose of an orbit camera: focus point, direction focus->camera, up hint, width (distance)
  if (c.look) { // walk / look mode: the camera sits at eye height above the ground, az = heading from north, el = pitch up
    const S = E.S, B = { E: S.X, U: S.Y, N: V.mul(S.Z, -1) }, P = S.fromTown([c.pan[0], terrainH(c.pan[0], c.pan[1]) + 1.7, c.pan[1]]), ce2 = Math.cos(c.el), fw = V.norm(V.add(V.add(V.mul(B.E, ce2 * Math.sin(c.az)), V.mul(B.N, ce2 * Math.cos(c.az))), V.mul(B.U, Math.sin(c.el))));
    return { F: V.madd(P, fw, 0.05), dir: V.mul(fw, -1), up: B.U, w: 0.05 }; }
  const F = focusPos(c), B = focusBasis(c), ce = Math.cos(c.el);
  const dir = V.norm(V.add(V.add(V.mul(B.E, ce * Math.sin(c.az)), V.mul(B.N, ce * Math.cos(c.az))), V.mul(B.U, Math.sin(c.el))));
  return { F, dir, up: B.U, w: c.d };
}
// van Wijk & Nuij, "Smooth and efficient zooming and panning" (2003), rho = sqrt(2): optimal path in (centre, width) space
function wijk(u1, w0, w1) {
  const rho = Math.SQRT2, rho2 = 2, rho4 = 4;
  if (u1 < 1e-7 * Math.max(w0, w1)) return { S: Math.abs(Math.log(w1 / w0)) / rho, at: tau => ({ f: 0, w: w0 * Math.pow(w1 / w0, tau) }) };
  const b0 = (w1 * w1 - w0 * w0 + rho4 * u1 * u1) / (2 * w0 * rho2 * u1), b1 = (w1 * w1 - w0 * w0 - rho4 * u1 * u1) / (2 * w1 * rho2 * u1);
  const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1), S = (r1 - r0) / rho;
  return { S, at: tau => { const s = tau * S, w = w0 * Math.cosh(r0) / Math.cosh(rho * s + r0), u = (w0 / rho2) * Math.cosh(r0) * Math.tanh(rho * s + r0) - (w0 / rho2) * Math.sinh(r0); return { f: clamp(u / u1, 0, 1), w }; } };
}
const ease = x => x * x * x * (x * (x * 6 - 15) + 10);
function flyTo(to, opts = {}) {
  const from = copyCam(cam), pa = poseOf(from), pb = poseOf(to), u1 = V.len(V.sub(pb.F, pa.F)), W = wijk(u1, Math.max(pa.w, 1e-3), Math.max(pb.w, 1e-3));
  const dur = opts.dur || clamp(2.0 + 0.55 * W.S, 2.4, opts.maxDur || 15);
  if (opts.instant) { Object.assign(cam, copyCam(to)); E.flight = null; return Promise.resolve(); }
  return new Promise(res => { E.flight = { from, to: copyCam(to), t0: performance.now(), dur: dur * 1000, res, fov: opts.fov, fov0: E.fov, name: opts.name || '' }; });
}
function applyFlight(now) {
  const fl = E.flight; if (!fl) return null; let tau = clamp((now - fl.t0) / fl.dur, 0, 1); const pa = poseOf(fl.from), pb = poseOf(fl.to), u1 = V.len(V.sub(pb.F, pa.F)), W = wijk(u1, Math.max(pa.w, 1e-3), Math.max(pb.w, 1e-3)), k = ease(tau), r = W.at(k);
  const F = V.add(pa.F, V.mul(V.sub(pb.F, pa.F), r.f)), e = ease(clamp(k * 1.15 - 0.075, 0, 1));
  if (fl.fov) E.fov = mix(fl.fov0, fl.fov, e);
  const out = { F, dir: V.slerp(pa.dir, pb.dir, e), up: V.norm(V.lerp(pa.up, pb.up, e)), w: r.w, tau };
  if (tau >= 1) { Object.assign(cam, copyCam(fl.to)); E.flight = null; fl.res(); return poseOf(cam); }
  return out;
}
// ------------------------------------------------------------------ sky and lighting
const SKY = { zen: [0.14, 0.33, 0.74], hor: [0.62, 0.79, 0.96] };
function skyModel(S, alt) {
  const e = S.sunElev / D2R, ob = S.obsc || 0, dim = 1 - 0.97 * Math.pow(ob, 1.7);
  let day = smooth(-4, 9, e) * dim, gold = Math.exp(-Math.pow((e - 3) / 9, 2)) * smooth(-9, -1, e), twi = smooth(-18, -4, e) * (1 - day) + 0.7 * Math.pow(ob, 3) * smooth(0, 10, e); gold = Math.min(1, gold + 0.9 * Math.pow(ob, 2.5) * smooth(0, 10, e));
  const zen = mixc(mixc([0.004, 0.008, 0.02], [0.03, 0.06, 0.17], twi), [0.14, 0.33, 0.74], day), hor0 = mixc(mixc([0.02, 0.03, 0.06], [0.30, 0.22, 0.32], twi), [0.62, 0.79, 0.96], day), warm = [1.0, 0.58, 0.30];
  const hor = mixc(hor0, warm, gold * 0.75), mid = mixc(mixc(zen, hor, 0.45), warm, gold * 0.15);
  // the sky thins into space with altitude
  const thin = 1 - smooth(8000, 90000, alt), f = x => x.map(v => v * thin);
  return { zen: f(zen), mid: f(mid), hor: f(hor), day, gold, twi, e, fog: hor };
}
function updateLighting(S, alt, near) {
  const m = skyModel(S, alt), e = m.e, sd = S.sunT, md = S.moonT, me = S.moonElev / D2R;
  const sunI = 4.6 * Math.pow(smooth(-2.5, 12, e), 0.8) * Math.pow(1 - (S.obsc || 0), 1.15), sunCol = mixc([1.0, 0.54, 0.24], [1.0, 0.96, 0.9], smooth(0, 26, e));
  const moonI = 0.6 * S.phaseFrac * smooth(-1, 8, me) * (1 - m.day); const wS = sunI / Math.max(1e-6, sunI + moonI * 3.0), wM = 1 - wS;
  let dir = V.norm(V.add(V.mul(sd, wS), V.mul(md, wM))); if (sunI + moonI < 0.02) dir = sd;
  const col = mixc([0.55, 0.65, 1.0], sunCol, wS), I = sunI + moonI;
  const top = 0.30 + 1.15 * m.day + 0.45 * m.twi + 0.30 * m.gold, side = 0.17 + 0.55 * m.day + 0.30 * m.twi + 0.30 * m.gold;
  const topCol = mixc(m.zen, [0.7, 0.82, 1.0], 0.55).map((v, i) => Math.max(v, [0.16, 0.22, 0.42][i])), sideCol = mixc(m.hor, [0.62, 0.75, 1.0], 0.55).map((v, i) => Math.max(v, [0.14, 0.2, 0.4][i]));
  for (const p of ['', 'Out']) {
    setIf(p + 'KeyLight', 'direction', V.mul(dir, -1), 2e-4); setIf(p + 'KeyLight', 'intensity', [I], 1e-3); setIf(p + 'KeyLight', 'color', col, 1e-3);
    setIf(p + 'SkyLight', 'intensity', [top], 1e-3); setIf(p + 'SkyLight', 'color', topCol, 1e-3);
    for (let k = 0; k < 3; k++) { setIf(p + 'Fill' + k, 'intensity', [side], 1e-3); setIf(p + 'Fill' + k, 'color', sideCol, 1e-3); }
  }
  if (near) { setIf('BgDay', 'skyColor', [].concat(m.zen, m.mid, m.hor, m.hor.map(v => v * 0.9)), 1e-3); setIf('BgDay', 'skyAngle', [0.9, 1.4, 1.57], 1e-3); setIf('BgDay', 'groundColor', [].concat(m.hor.map(v => v * 0.55), m.hor.map(v => v * 0.35)), 1e-3); setIf('BgDay', 'groundAngle', [1.52], 1e-3);
    setIf('BgSpace', 'skyColor', [].concat(m.zen, m.mid, m.hor), 1e-3); setIf('BgSpace', 'skyAngle', [1.1, 1.5], 1e-3); setIf('BgSpace', 'groundColor', m.hor.map(v => v * 0.3), 1e-3); setIf('BgSpace', 'groundAngle', [], 1e-3);
    setIf('FogTown', 'color', m.fog.map(v => v * 0.95), 1e-3); setIf('FogTown', 'visibilityRange', [mix(5200, 11500, m.day) * (1 - 0.35 * m.gold) * (1 + Math.max(0, alt) / 2200)], 1e-3); }
  else if (!E.spaceBlack) { setIf('BgSpace', 'skyColor', [0, 0, 0], 1e-3); setIf('BgSpace', 'skyAngle', [], 1e-3); setIf('BgSpace', 'groundColor', [], 1e-3); setIf('BgSpace', 'groundAngle', [], 1e-3); }
  E.spaceBlack = !near;
  // lamps and windows come on at dusk; the forge flickers
  const lamp = Math.max(smooth(4, -3, e), smooth(0.9, 0.99, S.obsc || 0)), flick = 0.82 + 0.18 * Math.sin(E.clock * 9.3) * Math.sin(E.clock * 5.1 + 1.3) + 0.06 * Math.sin(E.clock * 23);
  setIf('Mat_lampglass', 'emissiveColor', [1.0 * lamp * 2.2, 0.72 * lamp * 2.2, 0.38 * lamp * 2.2], 1e-3); setIf('Mat_glass_lit', 'emissiveColor', [1.0 * lamp * 1.6, 0.74 * lamp * 1.6, 0.4 * lamp * 1.6], 1e-3);
  for (const n of ['LampA', 'LampB']) setIf(n, 'intensity', [lamp * 6.0], 1e-3); setIf('ForgeL', 'intensity', [(0.5 + 1.8 * lamp) * flick], 1e-3); setIf('Mat_forge', 'emissiveColor', [1.0 * flick * 1.6, 0.42 * flick * 1.6, 0.1 * flick * 1.6], 1e-3);
  E.sky = m; E.keyDir = dir;
}
// fade the constellation with distance so that it does not crowd the Earth / village views
function constAlpha(S, near) {
  if (near) return S.sunElev < -4 * D2R || E.alt > 15000 ? 1 : 0;
  const c = E.cam, d = E.pose ? E.pose.w : c.d, rel = V.len(V.sub(E.camS || [0, 0, 0], [0, 0, 0]));
  return smooth(1.2e9, 1.2e10, Math.min(d, rel));        // far from the centre and far from the focus -> visible
}
let fadeLast = -1, fadeNames = null;
function fadeConstellation(a) {
  if (a === fadeLast) return; if (Math.abs(a - fadeLast) < 0.015 && a !== 0 && a !== 1) return; fadeLast = a;
  if (!fadeNames) { fadeNames = []; try { const nn = E.B.currentScene.namedNodes; for (let i = 0; i < nn.length; i++) { const k = nn[i].getNodeName(); if (/^(Fam_|New41|BeadM_|Hierarchy|ShellWires|Shape(Accepts|Rejects|Inconclusive|Abstract)|RingLine_|LoopLine)/.test(k)) fadeNames.push(k); } } catch (e) { console.warn('fade list', e); } }
  const tr = 1 - a;
  for (const k of fadeNames) { const n = nd(k); if (!n) continue; try { const tn = n.getTypeName(), m = (tn === 'Material' || tn === 'PhysicalMaterial') ? n : tn === 'Appearance' ? n.material : (n.appearance && n.appearance.material); if (m) m.transparency = Math.min(0.995, tr); } catch (e) { } }
}
// ------------------------------------------------------------------ per-frame update
function placeWorld(S) {
  const o = S.toTown([0, 0, 0]); setIf('World', 'translation', o, 1e-12); setIf('World', 'rotation', Q.toAxisAngle(S.qInv), 1e-12);
  setIf('EarthOrbitT', 'translation', S.E, 1e-13); setIf('EarthSpin', 'rotation', Q.toAxisAngle(S.qEarth), 1e-12);
  setIf('MoonOrbitT', 'translation', S.Mrel, 1e-13); setIf('MoonSpin', 'rotation', Q.toAxisAngle(S.qMoon), 1e-12);
  const m1 = moonRel(S.d + 1.0).pos, nrm = V.norm(V.cross(S.Mrel, m1)), ax = V.cross([0, 1, 0], nrm), an = Math.acos(clamp(nrm[1], -1, 1)); setIf('MoonOrbitPlane', 'rotation', V.len(ax) < 1e-9 ? [0, 1, 0, 0] : Q.toAxisAngle(Q.axisAngle(ax, an)), 1e-9);
  setIf('CloudsT', 'rotation', [0, 1, 0, (S.d * 0.11) % TAU], 1e-9); setIf('SunDir', 'direction', V.norm(S.E), 1e-6);
}
function frame(now) {
  requestAnimationFrame(frame); if (!E.ready) return; const dt = Math.min(0.25, (now - (E.last || now)) / 1000); E.last = now; E.clock = (E.clock || 0) + dt;
  if (!E.paused) E.t += dt * E.rate; const S = E.S = solar(E.t);
  // camera: flight or orbit state
  let pose = applyFlight(now); if (!pose) pose = poseOf(cam);
  E.pose = pose; const camS = V.madd(pose.F, pose.dir, pose.w), fwdS = V.mul(pose.dir, -1);
  let camT = S.toTown(camS); const fT = Q.rot(S.qInv, fwdS), uT = Q.rot(S.qInv, pose.up);
  const gh = terrainH(camT[0], camT[2]);
  const rEarth = V.len(V.sub(camS, S.E)), alt = rEarth - RE, near = alt < 120000 && rEarth < RE * 2;
  if (near && camT[1] < gh + 0.35) camT[1] = gh + 0.35;                                    // never below the ground
  E.camT = camT; E.camS = camS; E.alt = alt; E.near = near; E.fwdT = fT; E.upT = uT; E.qCamT = Q.look(fT, uT);
  const oa = Q.toAxisAngle(E.qCamT); for (const cn of ['Cam', 'CamTown']) { setIf(cn, 'position', camT, 1e-14); setIf(cn, 'orientation', oa, 1e-9); setIf(cn, 'fieldOfView', [E.fov], 1e-6); }
  placeWorld(S); updateLighting(S, Math.max(alt, 0), near);
  // visibility: village only when near the ground; the constellation not in daytime at ground level
  const showTown = alt < 400000 && rEarth < RE * 1.2, ca = E.constMode === 'off' ? 0 : E.constMode === 'on' ? 1 : constAlpha(S, near), showConst = ca > 0.004; fadeConstellation(E.constMode === 'on' ? 1 : ca);
  if (E.hidden.town !== !showTown) { const t = nd('Town'); if (t) { t.visible = showTown; E.hidden.town = !showTown; } }
  if (E.hidden.const !== !showConst) { const t = nd('ConstSpin'); if (t) { t.visible = showConst; E.hidden.const = !showConst; } }
  // backgrounds and fog
  const stars = !near || S.sunElev < -5 * D2R || alt > 60000 || (S.obsc || 0) > 0.97; const bg = stars ? 'BgSpace' : 'BgDay'; if (E.bg !== bg) { set(bg, 'set_bind', true); E.bg = bg; }
  const lines = !(near && alt < 400000); if (E.hidden.lines !== !lines) { for (const n of ['EclipticGrid', 'EarthOrbitLine', 'MoonOrbitLine', 'Graticule', 'EarthAxis']) { const x = nd(n); if (x) x.visible = lines; } E.hidden.lines = !lines; }
  const cd = alt < 9000 && near; if (E.hidden.cloud !== !cd) { const c = nd('CloudDeckT'); if (c) { c.scale = SFV(cd ? [1, 1, 1] : [0, 0, 0]); E.hidden.cloud = !cd; } }
  if (cd) { E.cloudU = ((E.cloudU || 0) + dt * 0.0006) % 1; const tt = nd('CloudTT'); if (tt) tt.translation = new X3D.SFVec2f(E.cloudU, E.cloudU * 0.3); }
  const wt = nd('Mat_water'); for (const f of E.onFrame) f(dt, now, S);
}
// ------------------------------------------------------------------ projection helpers (also used by the overlay)
function viewMatrix() { // returns functions from scene coords to normalised screen coords
  const cv = E.canvas, w = cv.clientWidth, h = cv.clientHeight, th = Math.tan(E.fov / 2), asp = w / h, qi = Q.conj(E.qCamT);
  const sy = h / 2 / th, ox = w / 2, oy = h / 2, ex = asp >= 1 ? sy : sy, S = E.S;
  return { w, h, th, sy, project: (pScene, out) => { const pt = S.toTown(pScene), v = Q.rot(qi, V.sub(pt, E.camT)); if (v[2] >= -1e-3) return null; const k = sy / -v[2]; return [ox + v[0] * k, oy - v[1] * k, -v[2], k]; },
    projectTown: pt => { const v = Q.rot(qi, V.sub(pt, E.camT)); if (v[2] >= -1e-3) return null; const k = sy / -v[2]; return [ox + v[0] * k, oy - v[1] * k, -v[2], k]; },
    ray: (x, y) => { const vx = (x - ox) / sy, vy = -(y - oy) / sy, d = V.norm([vx, vy, -1]), dt_ = Q.rot(E.qCamT, d); return { o: E.camT, d: dt_ }; } };
}
Object.assign(E, { cam, copyCam, flyTo, focusPos, focusBasis, focusMin, focusMax, FOCUS, viewMatrix });
