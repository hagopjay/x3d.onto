'use strict';
// ---- plain-array vector / quaternion maths in doubles (quaternion = [w,x,y,z]) and a low-precision Sun-Earth-Moon model.
// Scene axes: X toward the vernal equinox, Y = ecliptic north, Z = -(ecliptic longitude 90 deg). Units: metres, seconds.
const D2R = Math.PI / 180, TAU = Math.PI * 2;
const AU = 1.495978707e11, RE = 6.371e6, RM = 1.7374e6, RS = 6.957e8;
const V = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]], sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], mul: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
  len: a => Math.hypot(a[0], a[1], a[2]), norm: a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
  lerp: (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t], madd: (a, b, s) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s],
  slerp: (a, b, t) => { const d = Math.max(-1, Math.min(1, V.dot(a, b))), om = Math.acos(d); if (om < 1e-6) return V.norm(V.lerp(a, b, t)); if (Math.PI - om < 1e-6) { const p = Math.abs(a[0]) < .9 ? [1, 0, 0] : [0, 1, 0], o = V.norm(V.cross(a, p)); return V.add(V.mul(a, Math.cos(Math.PI * t)), V.mul(o, Math.sin(Math.PI * t))); } const s = Math.sin(om); return V.add(V.mul(a, Math.sin((1 - t) * om) / s), V.mul(b, Math.sin(t * om) / s)); },
};
const Q = {
  mul: (a, b) => [a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2], a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]],
  conj: q => [q[0], -q[1], -q[2], -q[3]], norm: q => { const l = Math.hypot(q[0], q[1], q[2], q[3]) || 1; return [q[0] / l, q[1] / l, q[2] / l, q[3] / l]; },
  rot: (q, v) => { const u = [q[1], q[2], q[3]], t = V.mul(V.cross(u, v), 2); return V.add(V.add(v, V.mul(t, q[0])), V.cross(u, t)); },
  axisAngle: (ax, an) => { const s = Math.sin(an / 2), a = V.norm(ax); return [Math.cos(an / 2), a[0] * s, a[1] * s, a[2] * s]; },
  toAxisAngle: q => { q = Q.norm(q); if (q[0] < 0) q = q.map(x => -x); const w = Math.min(1, q[0]), an = 2 * Math.acos(w), s = Math.sqrt(Math.max(1e-16, 1 - w * w)); return an < 1e-9 ? [0, 1, 0, 0] : [q[1] / s, q[2] / s, q[3] / s, an]; },
  fromCols: (c0, c1, c2) => { // rotation matrix with columns c0,c1,c2
    const m00 = c0[0], m10 = c0[1], m20 = c0[2], m01 = c1[0], m11 = c1[1], m21 = c1[2], m02 = c2[0], m12 = c2[1], m22 = c2[2], tr = m00 + m11 + m22; let w, x, y, z;
    if (tr > 0) { const s = Math.sqrt(tr + 1) * 2; w = s / 4; x = (m21 - m12) / s; y = (m02 - m20) / s; z = (m10 - m01) / s; }
    else if (m00 > m11 && m00 > m22) { const s = Math.sqrt(1 + m00 - m11 - m22) * 2; w = (m21 - m12) / s; x = s / 4; y = (m01 + m10) / s; z = (m02 + m20) / s; }
    else if (m11 > m22) { const s = Math.sqrt(1 + m11 - m00 - m22) * 2; w = (m02 - m20) / s; x = (m01 + m10) / s; y = s / 4; z = (m12 + m21) / s; }
    else { const s = Math.sqrt(1 + m22 - m00 - m11) * 2; w = (m10 - m01) / s; x = (m02 + m20) / s; y = (m12 + m21) / s; z = s / 4; }
    return Q.norm([w, x, y, z]);
  },
  // camera orientation (X3D: looks along -Z, up +Y) for a forward direction and an up hint
  look: (f, u) => { f = V.norm(f); let r = V.cross(f, u); if (V.len(r) < 1e-9) r = V.cross(f, Math.abs(f[1]) < .9 ? [0, 1, 0] : [1, 0, 0]); r = V.norm(r); const up = V.cross(r, f); return Q.fromCols(r, up, V.mul(f, -1)); },
  slerp: (a, b, t) => { let d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]; if (d < 0) { b = b.map(x => -x); d = -d; } if (d > .9995) return Q.norm(a.map((x, i) => x + (b[i] - x) * t)); const om = Math.acos(d), s = Math.sin(om), A = Math.sin((1 - t) * om) / s, B = Math.sin(t * om) / s; return a.map((x, i) => x * A + b[i] * B); },
};
const clamp = (x, a, b) => Math.min(b, Math.max(a, x)), smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }, mix = (a, b, t) => a + (b - a) * t;
const mixc = (a, b, t) => [mix(a[0], b[0], t), mix(a[1], b[1], t), mix(a[2], b[2], t)];

// ---- time
const J2000 = Date.UTC(2000, 0, 1, 12) / 1000;
const daysJ2000 = tUnix => (tUnix - J2000) / 86400;
const eclToScene = (x, y, z) => [x, z, -y];
// ---- Earth (heliocentric, e = 0.0167, perihelion longitude 102.94 deg: same elements as the orbit line in the scene file)
function earthPos(d) {
  const M = (357.5291092 + 0.98560028 * d) * D2R, e = 0.0167; let E = M; for (let i = 0; i < 6; i++) E = M + e * Math.sin(E);
  const nu = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2)), r = AU * (1 - e * Math.cos(E)), lam = 102.94 * D2R + nu;
  return eclToScene(r * Math.cos(lam), r * Math.sin(lam), 0);
}
// ---- Moon: low-precision series (a few dozen arc minutes; fine for a picture, not for eclipse prediction)
function moonRel(d) {
  const T = d / 36525, r = x => (x % 360) * D2R, Lp = r(218.3164477 + 481267.88123421 * T), Dd = r(297.8501921 + 445267.1114034 * T), M = r(357.5291092 + 35999.0502909 * T), Mp = r(134.9633964 + 477198.8675055 * T), F = r(93.272095 + 483202.0175233 * T);
  const lam = Lp + D2R * (6.288774 * Math.sin(Mp) + 1.274027 * Math.sin(2 * Dd - Mp) + 0.658314 * Math.sin(2 * Dd) + 0.213618 * Math.sin(2 * Mp) - 0.185116 * Math.sin(M) - 0.114332 * Math.sin(2 * F) + 0.058793 * Math.sin(2 * Dd - 2 * Mp) + 0.057066 * Math.sin(2 * Dd - M - Mp) + 0.053322 * Math.sin(2 * Dd + Mp) + 0.045758 * Math.sin(2 * Dd - M));
  const bet = D2R * (5.128122 * Math.sin(F) + 0.280602 * Math.sin(Mp + F) + 0.277693 * Math.sin(Mp - F) + 0.173237 * Math.sin(2 * Dd - F) + 0.055413 * Math.sin(2 * Dd - Mp + F) + 0.046271 * Math.sin(2 * Dd - Mp - F));
  const dist = 1000 * (385000.56 - 20905.355 * Math.cos(Mp) - 3699.111 * Math.cos(2 * Dd - Mp) - 2955.968 * Math.cos(2 * Dd) - 569.925 * Math.cos(2 * Mp) + 48.888 * Math.cos(M) - 3.149 * Math.cos(2 * F) + 246.158 * Math.cos(2 * Dd - 2 * Mp));
  return { pos: eclToScene(dist * Math.cos(bet) * Math.cos(lam), dist * Math.cos(bet) * Math.sin(lam), dist * Math.sin(bet)), lam, bet, dist, Dd, Mp };
}
// ---- Earth orientation: columns of (body -> scene).  Body frame: y = north pole, z = (lat 0, lon 0), x = (lat 0, lon +90 east); matches the sphere texture mapping in X3D.
function earthBasis(d) {
  const th = ((280.46061837 + 360.98564736629 * d) % 360) * D2R, eps = (23.439291 - 3.56e-7 * d) * D2R, cT = Math.cos(th), sT = Math.sin(th), cE = Math.cos(eps), sE = Math.sin(eps);
  const f = v => { const xe = v[0], ye = v[1] * cE + v[2] * sE, ze = -v[1] * sE + v[2] * cE; return eclToScene(xe, ye, ze); };
  return [f([-sT, cT, 0]), f([0, 0, 1]), f([cT, sT, 0])];
}
const bodyToScene = (B, v) => V.add(V.add(V.mul(B[0], v[0]), V.mul(B[1], v[1])), V.mul(B[2], v[2]));
// ---- the village (illustrative site)
const TOWN = { lat: 46.80 * D2R, lon: 8.20 * D2R };
const townBody = (() => { const p = [Math.cos(TOWN.lat) * Math.sin(TOWN.lon), Math.sin(TOWN.lat), Math.cos(TOWN.lat) * Math.cos(TOWN.lon)], e = [Math.cos(TOWN.lon), 0, -Math.sin(TOWN.lon)], n = V.cross(p, e); return { P: p, E: e, U: p, N: n }; })();
// ---- one call computes everything the renderer needs for time t (unix seconds)
const ECLIPSE = { on: false, t0: 0, sig: 5 * 3600, delta: [0, 0, 0], info: null };   // staged eclipse: the Moon is nudged near one chosen new moon so that the village sees totality
function solar(t, raw) {
  const d = daysJ2000(t), E = earthPos(d), m = moonRel(d), B = earthBasis(d); if (ECLIPSE.on && !raw) { const w = Math.exp(-Math.pow((t - ECLIPSE.t0) / ECLIPSE.sig, 2)); if (w > 1e-4) m.pos = V.add(m.pos, V.mul(ECLIPSE.delta, w)); m.dist = V.len(m.pos); } const Mpos = V.add(E, m.pos);
  const X = bodyToScene(B, townBody.E), Y = bodyToScene(B, townBody.U), Z = bodyToScene(B, V.mul(townBody.N, -1)), T0 = V.add(E, V.mul(bodyToScene(B, townBody.P), RE));
  const qT = Q.fromCols(X, Y, Z), qInv = Q.conj(qT);
  const toTown = p => { const r = V.sub(p, T0); return [V.dot(r, X), V.dot(r, Y), V.dot(r, Z)]; }, fromTown = q => V.add(T0, V.add(V.add(V.mul(X, q[0]), V.mul(Y, q[1])), V.mul(Z, q[2])));
  const dirTown = p => V.norm(toTown(p)); const sunT = dirTown([0, 0, 0]), moonT = dirTown(Mpos);
  // moon phase: illuminated fraction seen from Earth
  const toSun = V.norm(V.mul(E, -1)), toMoon = V.norm(m.pos), cosElong = V.dot(toSun, toMoon), phaseFrac = (1 - cosElong) / 2;   // 0 new .. 1 full (elongation-based)
  // moon body: +z toward Earth (near side), y toward ecliptic north
  const mz = V.norm(V.mul(m.pos, -1)), mx = V.norm(V.cross([0, 1, 0], mz)), my = V.cross(mz, mx), qMoon = Q.fromCols(mx, my, mz);
  const sunDist = V.len(T0), moonD = V.len(V.sub(Mpos, T0)), rS_ = Math.asin(clamp(RS / sunDist, 0, 1)), rM_ = Math.asin(clamp(RM / moonD, 0, 1)), sep = Math.acos(clamp(V.dot(sunT, moonT), -1, 1)), obsc = obscuration(rS_, rM_, sep);
  return { t, d, E, M: Mpos, obsc, sep, rS: rS_, rM: rM_, Mrel: m.pos, B, X, Y, Z, T0, qT, qInv, toTown, fromTown, sunT, moonT, sunElev: Math.asin(clamp(sunT[1], -1, 1)), moonElev: Math.asin(clamp(moonT[1], -1, 1)), phaseFrac, qMoon, qEarth: Q.fromCols(B[0], B[1], B[2]), moonDist: m.dist, moonLam: m.lam, moonBet: m.bet };
}
// ---- terrain height above the village tangent plane (mirrors town_geo.H in the builder)
function fbmSin(x, z, seed, oct = 4) { let s = 0, a = 1, f = 1, tot = 0; for (let o = 0; o < oct; o++) { const ph = seed * 1.7 + o * 2.3; s += a * (Math.sin(f * 0.0123 * x + ph) * Math.sin(f * 0.0137 * z + ph * 1.3) + 0.6 * Math.sin(f * 0.0091 * (x + z) + ph * 0.7) * Math.cos(f * 0.0111 * (x - z) + ph * 1.9)); tot += a * 1.6; a *= 0.5; f *= 2.07; } return s / tot; }
function terrainH(x, z) {
  const r2 = x * x + z * z, r = Math.sqrt(r2); let h = smooth(280, 1100, r) * (24 * fbmSin(x, z, 1) + 9 * fbmSin(x * 2.3, z * 2.3, 2));
  const m = smooth(2500, 9500, r), ang = Math.atan2(z, x), ridge = 0.5 + 0.5 * fbmSin(x * 0.12, z * 0.12, 7), bias = 0.55 + 0.45 * Math.cos(ang - 1.1); h += m * (260 + 900 * ridge) * (0.3 + 0.7 * bias);
  return h - r2 / (2 * RE);
}

function obscuration(r1, r2, d) { // fraction of the Sun's disc (radius r1) covered by the Moon (radius r2) at centre separation d
  if (d >= r1 + r2) return 0; if (d <= Math.abs(r1 - r2)) return r2 >= r1 ? 1 : (r2 * r2) / (r1 * r1);
  const A = r1 * r1 * Math.acos(clamp((d * d + r1 * r1 - r2 * r2) / (2 * d * r1), -1, 1)) + r2 * r2 * Math.acos(clamp((d * d + r2 * r2 - r1 * r1) / (2 * d * r2), -1, 1)) - 0.5 * Math.sqrt(Math.max(0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)));
  return clamp(A / (Math.PI * r1 * r1), 0, 1);
}
// choose the new moon in the next two years whose closest approach to the Sun, as seen from the village in daytime, is smallest; then stage totality there
function findEclipse(from) {
  const t00 = from || Date.now() / 1000; let best = null;
  for (let day = 0; day < 760; day += 1) { const t = t00 + day * 86400; if (solar(t, true).phaseFrac > 0.03 && solar(t + 43200, true).phaseFrac > 0.03 && solar(t - 43200, true).phaseFrac > 0.03) continue;
    for (let s = -43200; s <= 43200; s += 600) { const tt = t + s, S = solar(tt, true); if (S.sunElev < 12 * D2R) continue; const sep = S.sep; if (!best || sep < best.sep) best = { t: tt, sep, el: S.sunElev }; } }
  if (!best) return null;
  for (let s = -900; s <= 900; s += 20) { const S = solar(best.t + s, true); if (S.sep < best.sep) best = { t: best.t + s, sep: S.sep, el: S.sunElev }; }
  const S0 = solar(best.t, true), u = V.norm(V.mul(S0.T0, -1)), Dtop = 3.62e8, target = V.sub(V.add(S0.T0, V.mul(u, Dtop)), S0.E), delta = V.sub(target, S0.Mrel);
  ECLIPSE.on = true; ECLIPSE.t0 = best.t; ECLIPSE.delta = delta; const S1 = solar(best.t);
  ECLIPSE.info = { t0: best.t, rawSepDeg: best.sep / D2R, nudgeDeg: Math.acos(clamp(V.dot(V.norm(S0.Mrel), V.norm(target)), -1, 1)) / D2R, nudgeKm: V.len(delta) / 1000, moonKm: Dtop / 1000, sunElevDeg: S1.sunElev / D2R, obsc: S1.obsc };
  return ECLIPSE.info;
}
