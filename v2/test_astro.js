// Sanity tests for the low-precision astronomy in astro.js (run: node test_astro.js).  Not a validation of accuracy beyond what is stated here.
const fs = require('fs'), vm = require('vm'); vm.runInThisContext(fs.readFileSync(__dirname + '/astro.js', 'utf8') + '\n;globalThis.__A = { solar, earthPos, moonRel, daysJ2000, findEclipse, ECLIPSE, obscuration, terrainH, V, Q, AU, RE, RM, RS, D2R };');
const A = globalThis.__A; let fail = 0; const ok = (name, cond, extra = '') => { console.log((cond ? 'PASS ' : 'FAIL ') + name + ' ' + extra); if (!cond) fail++; };
const T = (y, m, d, h = 12) => Date.UTC(y, m - 1, d, h) / 1000;
// 1. Earth-Sun distance: perihelion in early January ~0.9833 AU, aphelion in early July ~1.0167 AU
const dJan = A.V.len(A.earthPos(A.daysJ2000(T(2026, 1, 3)))) / A.AU, dJul = A.V.len(A.earthPos(A.daysJ2000(T(2026, 7, 4)))) / A.AU;
ok('perihelion distance', Math.abs(dJan - 0.9833) < 0.002, dJan.toFixed(4)); ok('aphelion distance', Math.abs(dJul - 1.0167) < 0.002, dJul.toFixed(4));
// 2. Sun declination: ~ -23.4 deg at December solstice, ~ 0 at March equinox, +23.4 deg in June (Sun direction from the village is checked indirectly through the Earth tilt)
function decl(t) { const S = A.solar(t); const sunDirScene = A.V.norm(A.V.mul(S.E, -1)); const axis = S.B[1]; return Math.asin(A.V.dot(sunDirScene, axis)) / A.D2R; }
const dDec = decl(T(2026, 12, 21)), dMar = decl(T(2026, 3, 20, 15)), dJun = decl(T(2026, 6, 21));
ok('declination December', Math.abs(dDec + 23.4) < 0.6, dDec.toFixed(2)); ok('declination March equinox', Math.abs(dMar) < 0.6, dMar.toFixed(2)); ok('declination June', Math.abs(dJun - 23.4) < 0.6, dJun.toFixed(2));
// 3. Moon distance over a year stays between 356,000 and 407,000 km
let mn = 1e12, mx = 0; for (let i = 0; i < 400; i++) { const m = A.moonRel(A.daysJ2000(T(2026, 1, 1) + i * 86400)).dist; mn = Math.min(mn, m); mx = Math.max(mx, m); }
ok('Moon distance range', mn > 354e6 && mx < 409e6, `${(mn / 1e6).toFixed(1)}..${(mx / 1e6).toFixed(1)} Mm`);
// 4. Known new moon: 2027-08-02 (total solar eclipse over Egypt/Spain): geocentric elongation below 1.5 deg at 10:00 UTC
const S = A.solar(T(2027, 8, 2, 10), true), toSun = A.V.norm(A.V.mul(S.E, -1)), toMoon = A.V.norm(S.Mrel), el = Math.acos(A.V.dot(toSun, toMoon)) / A.D2R;
ok('new moon 2027-08-02 elongation', el < 1.5, el.toFixed(2) + ' deg');
// 5. Noon sun elevation at the village in late October about 90 - 46.8 - 11.5 = 31.7 deg
let best = -9; for (let s = 0; s < 86400; s += 300) best = Math.max(best, A.solar(T(2026, 10, 22, 0) + s).sunElev / A.D2R);
ok('noon elevation 22 Oct', Math.abs(best - 31.7) < 1.5, best.toFixed(2));
// 6. obscuration formula limits
ok('obscuration none', A.obscuration(0.0046, 0.0046, 0.02) === 0); ok('obscuration total', A.obscuration(0.0046, 0.0048, 0.0001) === 1); const h = A.obscuration(0.0046, 0.0046, 0.0046); ok('obscuration partial 0..1', h > 0.2 && h < 0.7, h.toFixed(3));
// 7. staged eclipse: found within two years, nudge small, village sees totality at the chosen time
const t0 = Date.UTC(2026, 9, 24) / 1000, info = A.findEclipse(t0); ok('eclipse found', !!info, JSON.stringify(info && { when: new Date(info.t0 * 1000).toISOString(), rawSepDeg: +info.rawSepDeg.toFixed(3), nudgeKm: Math.round(info.nudgeKm), sunEl: +info.sunElevDeg.toFixed(1) }));
ok('eclipse total at staged time', info && A.solar(info.t0).obsc > 0.999, info && A.solar(info.t0).obsc.toFixed(4)); ok('eclipse over after 5 h', A.solar(info.t0 + 5 * 3600).obsc < 0.01); ok('eclipse nudge < 0.5 deg', info.nudgeDeg < 0.5, info.nudgeDeg.toFixed(3));
// 8. terrain is flat inside 280 m and rises far away
ok('terrain flat in the village', Math.abs(A.terrainH(100, 100)) < 5e-3); ok('terrain rises far away', A.terrainH(8000, 2000) > 50, A.terrainH(8000, 2000).toFixed(0) + ' m');
console.log(fail ? fail + ' FAILED' : 'all passed'); process.exit(fail ? 1 : 0);
