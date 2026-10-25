'use strict';
// UI: boot, data, pick registry (every pickable thing has a tooltip), input, HUD, time controls, info panel.
const $ = id => document.getElementById(id);
function el(tag, props, ...kids) { const n = document.createElement(tag); if (props) for (const [k, v] of Object.entries(props)) { if (v == null || v === false) continue; if (k === 'class') n.className = v; else if (k === 'style') n.style.cssText = v; else if (k.startsWith('on')) n[k] = v; else n.setAttribute(k, v); } for (const c of kids.flat()) { if (c == null || c === false) continue; n.append(c.nodeType ? c : document.createTextNode(String(c))); } return n; }
const setKids = (n, ...kids) => n.replaceChildren(...kids.flat().filter(x => x != null && x !== false));
const gradeTag = g => g ? el('span', { class: 'g g' + g }, g) : null;
const UI = { labelsOn: true, hover: null, pin: null, mx: 0, my: 0, inside: false, drag: null, vel: { az: 0, el: 0 }, keys: {}, town: null, people: null, tour: null, picks: null, personIdx: 0, soundOn: localStorage.getItem('v2-sound') === '1', ptrs: new Map(), lastClick: 0, frames: null };
const nowS = () => Date.now() / 1000;
const STAGE = { lat: 46.80, lon: 8.20 };
const localHours = t => (((t / 3600 + STAGE.lon / 15) % 24) + 24) % 24, fmtHM = h => { const H = Math.floor(h), M = Math.floor((h - H) * 60); return String(H).padStart(2, '0') + ':' + String(M).padStart(2, '0'); };
const ldeg = r => (r / D2R).toFixed(1) + '°';
function readQ(name) { const n = nd(name); if (!n) return [1, 0, 0, 0]; const r = n.rotation; return Q.axisAngle([r.x, r.y, r.z], r.angle); }
function townVec(name) { const n = nd(name); if (!n) return [0, 0, 0]; const t = n.translation; return [t.x, t.y, t.z]; }
const sc_ = (a, b) => b == null ? a : b;
// ------------------------------------------------------------------ data + registry
async function loadData() {
  const j = u => fetch(u).then(r => r.json()); const [picks, town, people, tour] = await Promise.all([j('data/picks.json'), j('data/town.json'), j('data/people.json'), j('data/tour-data.json')]); UI.picks = picks; UI.town = town; UI.people = people; UI.tour = tour;
}
function buildRegistry() {
  const T = UI.tour, reg = E.reg = [], by = E.by = new Map(); const add = e => { e.on = false; e.tc = [0, 0, 0]; reg.push(e); by.set(e.id, e); return e; };
  add({ id: 'sun', cat: 'body', name: 'Sun', label: 'Sun', sc: S => [0, 0, 0], r: RS, lab: 1, pri: 9, minPx: 0, fd: 2.4e9, col: '#ffe3a8', info: S => ({ t: 'Sun', sub: 'the star at the centre of the system', g: 'L', l: [`radius 695,700 km (${(RS / RE).toFixed(0)} Earth radii); the disc is a procedural noise map, not a photograph`, `distance to Earth now ${(V.len(S.E) / AU).toFixed(4)} AU = ${(V.len(S.E) / 1e9).toFixed(1)} million km; light takes ${(V.len(S.E) / 299792458 / 60).toFixed(2)} minutes`, `seen from the village: ${ldeg(S.sunElev)} above the horizon`, 'angular size from Earth about 0.53°, almost exactly that of the Moon'], src: 'IAU 2015 nominal solar radius; 1 AU (IAU 2012). Standard values quoted from memory, not re-derived here.' }) });
  add({ id: 'earth', cat: 'body', name: 'Earth', label: 'Earth', sc: S => S.E, r: RE, lab: 1, pri: 8, minPx: 0, fd: 2.4e7, col: '#9cd0ff', info: S => ({ t: 'Earth', sub: 'procedural planet: the continents are generated noise, not the real map', g: 'L', l: ['mean radius 6,371 km; axial tilt 23.44°; sidereal rotation 23 h 56 min', `orbit: ellipse e = 0.0167, now ${(V.len(S.E) / AU).toFixed(4)} AU from the Sun`, `Moon now ${(S.moonDist / 1000).toLocaleString('en', { maximumFractionDigits: 0 })} km away, ${(S.phaseFrac * 100).toFixed(0)} % lit`, `the village (orange pin) is at ${STAGE.lat}°N ${STAGE.lon}°E; local solar time ${fmtHM(localHours(S.t))}`], src: 'NASA Earth fact sheet / IAU values from memory; orientation by the GMST formula (Meeus, Astronomical Algorithms); maps are procedural (v2/textures.py)' }) });
  add({ id: 'moon', cat: 'body', name: 'Moon', label: 'Moon', sc: S => S.M, r: RM, lab: 1, pri: 8, minPx: 0, fd: 5.2e6, col: '#dfe4ee', info: S => ({ t: 'Moon', sub: 'tidally locked; procedural crater map', g: 'L', l: ['mean radius 1,737.4 km; mean distance 384,400 km (60.3 Earth radii)', `distance now ${(S.moonDist / 1000).toLocaleString('en', { maximumFractionDigits: 0 })} km; ${(S.phaseFrac * 100).toFixed(0)} % illuminated (elongation based)`, 'position from a truncated lunar series of about a dozen terms: good to roughly half a degree, not an eclipse predictor', `elevation above the village horizon ${ldeg(S.moonElev)}`], src: 'Meeus, Astronomical Algorithms ch. 47 (abridged) from memory; radius and distance are mean values' }) });
  add({ id: 'village', cat: 'town', name: 'Aurelsbrunn', label: 'Aurelsbrunn (invented village)', sc: S => S.T0, r: 6e4, lab: 1, pri: 7, minPx: 5, fd: 2.6e6, special: 'village', col: '#ffcf8a', info: S => ({ t: 'Aurelsbrunn', sub: 'a village that does not exist', g: 'I', l: [`illustrative site at ${STAGE.lat}°N ${STAGE.lon}°E: ${UI.town.houses.length} buildings, a fountain plaza, 3 market stalls, ${UI.people.length} villagers`, `local solar time ${fmtHM(localHours(S.t))}, sun ${ldeg(S.sunElev)} above the horizon`, 'everything at human scale lives in the same file as the solar system: metres, one scene graph, no level-of-detail switch'], src: 'invented for this demo (v2/town_layout.py); not a real place' }) });
  const MAJ = new Set(); for (const [id, c] of Object.entries(T.classes)) if ((c.d === 0 && c.kids >= 3) || c.new || ['Shape', 'Appearance', 'Material', 'Transform', 'Group', 'Geometry3D', 'Viewpoint', 'IndexedFaceSet'].includes(id)) MAJ.add(id);
  const F = () => UI.frames; const fq = { ConstSpin: () => F().c, Tilt_X3D: () => F().tilt.X3D, Tilt_URDF: () => F().tilt.URDF, Tilt_glTF: () => F().tilt.glTF, Spin_X3D: () => F().spin.X3D, Spin_URDF: () => F().spin.URDF, Spin_glTF: () => F().spin.glTF, LoopTilt: () => F().loopTilt, LoopRing: () => F().loop };
  for (const p of UI.picks) {
    const chain = p.frame, loc = p.p, qf = () => { let q = [1, 0, 0, 0]; for (const f of chain) q = Q.mul(q, fq[f]()); return q; };
    const e = { id: (p.cat === 'class' ? 'C_' : '') + p.id, cat: p.cat, p, sc: S => Q.rot(qf(), loc), r: p.r, minPx: 5, fd: p.r * 7, pri: p.cat === 'class' ? 1 : 3 };
    if (p.cat === 'class') { const c = T.classes[p.id]; e.name = p.id; e.lab = MAJ.has(p.id); e.pri = c.new ? 5 : c.d === 0 ? 2 : 1; e.col = c.new ? '#8dffb4' : '#e6eeff'; e.info = () => classInfo(p.id); }
    else if (p.cat === 'bead') { const b = T.beads[p.dom][p.idx]; e.name = p.dom === 'X3D' ? b.name : b.id; e.label = p.dom + ' · ' + e.name; e.lab = p.dom !== 'X3D'; e.minPx = 7; e.info = () => beadInfo(p.dom, p.idx); e.col = '#cfe0ff'; e.pri = 3; }
    else if (p.cat === 'station') { const s = T.stations[p.idx]; e.name = s[0]; e.label = 'loop: ' + s[0]; e.lab = true; e.pri = 6; e.fd = p.r * 9; e.info = () => ({ t: 'Loop station: ' + s[0], sub: 'flywheel station ' + (p.idx + 1) + ' of 7', g: s[2], l: [s[1]], src: 'v1 demo spec (demo/DEMO-SPEC.md); numbers carry their sources in demo/sources.json' }); e.col = '#ffe0a0'; }
    else if (p.cat === 'pillar') { const ev = T.pillars[p.dom]; e.name = p.dom + (p.idx ? ' after loop' : ' first try'); e.lab = true; e.pri = 4; e.minPx = 8; e.fd = Math.max(p.r * 4, 6e10); e.info = () => ({ t: `${p.dom}: ${p.idx ? 'after the report loop' : 'first try'}`, sub: 'evidence monolith', g: ev ? 'C' : 'L', l: [ev ? `${p.idx ? ev.a2 : ev.a0} % of generated files valid (Gemini flash, n = ${ev.n} first tries)` : 'evaluation still running'], src: 'xdomain/eval-plan/runs (measured; see RESULTS.md)' }); e.col = '#bfe9ff'; }
    add(e);
  }
  const H = UI.town.houses;
  for (const h of H) {
    const cx = h.x, cz = h.z, hx = h.w / 2, hz = h.d / 2, c = Math.cos(h.rot), s = Math.sin(h.rot);
    const e = add({ id: h.id, cat: 'building', name: h.name, label: h.name, sub: () => h.role, tw: () => [cx, h.h / 2, cz], r: Math.hypot(hx, hz) * 0.8, lab: true, pri: 2, minPx: 12, fd: Math.max(h.w, h.d, h.h) * 2.6, maxD: 260, special: 'building', col: h.id === 'B02' ? '#d7dce8' : '#ffe0b8', obb: { c: [cx, h.h * 0.55, cz], h: [hx, h.h * 0.6, hz], rot: h.rot },
      info: S => ({ t: h.name, sub: h.role, g: 'I', l: [`footprint ${h.w} × ${h.d} m, wall height ${h.h} m (${h.h >= 4.35 ? 'two storeys' : 'one storey and an attic'}), ${h.roof} roof, ${h.wall} walls`, `position ${cx.toFixed(0)} m east, ${(-cz).toFixed(0)} m north of the fountain`, `windows glow after dusk (lamp factor now ${(smooth(4, -3, S.sunElev / D2R) * 100).toFixed(0)} %)`, h.id === 'B02' ? 'tower 15.5 m plus a 7.5 m slate spire; four clock faces' : h.id === 'B03' ? 'the forge flickers; Old Bram strikes the anvil every 1.4 s' : h.id === 'B01' ? 'hanging sign, two tables outside, two chimneys' : ''].filter(Boolean), src: 'invented for this demo (v2/town_layout.py, v2/town_geo.py); one merged IndexedFaceSet per material' }) });
    const corner = (a, b, y) => { const lx = a * hx, lz = b * hz; return [cx + c * lx + s * lz, y, cz - s * lx + c * lz]; };
    e.box = view => { const q = [[-1, -1], [1, -1], [1, 1], [-1, 1]], lo = q.map(([a, b]) => view.projectTown(corner(a, b, 0.2))), hi = q.map(([a, b]) => view.projectTown(corner(a, b, h.h + 1.4))); if (lo.concat(hi).some(v => !v)) return null; return [lo[0], lo[1], hi[1], hi[2], lo[2], lo[3], hi[3], hi[0], lo[0]]; };
  }
  for (const s of UI.town.stalls) add({ id: s.id, cat: 'prop', name: s.name, label: s.name, tw: () => [s.x, 1.3, s.z], obb: { c: [s.x, 1.3, s.z], h: [1.5, 1.4, 1.0], rot: s.rot }, r: 1.8, lab: true, pri: 1, minPx: 14, fd: 9, maxD: 60, special: 'prop', col: '#ffd9a6', info: () => ({ t: s.name, sub: 'market stall on the plaza', g: 'I', l: ['2.6 × 1.8 m with a striped cloth canopy; counter and goods are geometry', s.id === 'S01' ? 'bread: nine small ellipsoids' : s.id === 'S02' ? 'vegetables: fourteen spheres in five colours' : 'cloth: folded bolts in five colours'], src: 'invented (v2/town_geo.py)' }) });
  add({ id: 'fountain', cat: 'prop', name: 'Fountain', label: 'Fountain', tw: () => [0, 1.6, 0], obb: { c: [0, 1.4, 0], h: [3.5, 1.5, 3.5], rot: 0 }, r: 3.6, lab: true, pri: 2, minPx: 14, fd: 16, maxD: 90, special: 'prop', col: '#bfe4ff', info: () => ({ t: 'Plaza fountain', sub: 'centre of the village', g: 'I', l: ['stone basin radius 3.2 m, two bowls and a column 4 m high', 'the water is a textured disc with a PBR material (roughness 0.06): it shows the sun as a glint'], src: 'invented (v2/town_geo.py)' }) });
  for (const pp of UI.people) {
    const T_ = 'T_' + pp.id, sc = pp.scale;
    const e = add({ id: pp.id, cat: 'person', name: pp.name, label: pp.name, sub: () => pp.role, subAlways: () => (E.pose && E.pose.w < 12) ? pp.role : null, tw: () => { const v = townVec(T_); return [v[0], v[1] + 0.92 * sc, v[2]]; }, r: 0.62 * sc, lab: true, pri: 6, minPx: 6, fd: 5.5 * sc + 1.5, fh: 1.35 * sc, maxD: 55, special: 'person', col: '#fff4c7',
      info: S => { const v = townVec(T_), rr = nd(T_).rotation, yaw = rr.y >= 0 ? rr.angle : -rr.angle; const L = [pp.role + (pp.note ? ': ' + pp.note : ''), `wears a ${pp.shirt} top and ${pp.pants} trousers; height ${(1.75 * sc).toFixed(2)} m (humanoid scale ${sc})`, pp.path_m ? `path ${pp.path_m} m at ${pp.speed} m/s, lap ${pp.lap} s; gait cycle ${pp.gait_s} s (hip swing ±24°, stride ${(2 * 2 * 0.92 * sc * Math.sin(24 * D2R)).toFixed(2)} m)` : `idle loop ${pp.period} s: ${pp.arch === 'smith' ? 'hammer strike every 1.4 s' : pp.arch === 'greeter' ? 'waves for about 3.5 s' : pp.arch === 'talker' ? 'speaks with the right arm and nods' : 'listens with small head movements'}`, 'body: 16 H-Anim joints (humanoid_root … l/r_talocrural) and 15 segments; keyframed in X3D with OrientationInterpolators, no scripts'];
        return { t: pp.name, sub: pp.role, g: 'I', l: L, live: `now ${v[0].toFixed(1)} m east, ${(-v[2]).toFixed(1)} m north of the fountain · heading ${((((yaw / D2R) % 360) + 360) % 360).toFixed(0)}°`, src: 'invented character (v2/town_layout.py); skeleton and animation built by v2/humans.py through x3d_mcp' }; } });
  }
  E.objPos = id => { const e = by.get(id); if (!e) return [0, 0, 0]; const S = E.S; if (e.tw) { const t = e.tw(S); return S.fromTown([t[0], t[1] + (e.fh ? e.fh - 0.92 * (UI.people.find(p => p.id === id) || { scale: 1 }).scale : 0), t[2]]); } return e.sc(S); };
  E.objBasis = id => { const e = by.get(id); return e && e.tw ? { E: E.S.X, U: E.S.Y, N: V.mul(E.S.Z, -1) } : ECL; };
  E.objMin = id => { const e = by.get(id); return e ? (e.cat === 'person' ? 0.7 : e.cat === 'building' ? 4 : e.cat === 'prop' ? 2.5 : e.r * 1.25) : 1; };
}
function classInfo(id) { const T = UI.tour, k = T.classes[id]; return { t: id, sub: `${k.kind} class · family ${k.fam}`, g: 'C', l: [`${k.comp ? 'component ' + k.comp + ' level ' + k.lvl + ' · ' : ''}depth ${k.d} in the hierarchy`, `${k.nf} fields · ${k.kids} subclasses`, `${k.lp} predicted (parent, field) pairs` + (k.xa + k.xr + k.xi ? `: XSD accepts ${k.xa}, rejects ${k.xr}, inconclusive ${k.xi}` : ''), k.new ? 'NEW in X3D Ontology 4.1' : '', k.defn].filter(Boolean), src: 'data/explorer.json (X3D Ontology ' + T.facts.onto[0] + ')' }; }
function beadInfo(dom, i) { const b = UI.tour.beads[dom][i]; if (dom === 'X3D') return { t: 'X3D component ' + b.name, sub: 'bead on the X3D ring', g: 'C', l: [`${b.nodes} concrete nodes${b.new ? ', ' + b.new + ' new in 4.1' : ''}`, `XSD accepts ${b.pct}% of the ontology's placements`, `X3DUOM lists agree with the XSD on ${b.agree}% of the pairs`], src: 'data/components.json' };
  return { t: `${dom} fault ${b.id}`, sub: 'bead on the ' + dom + ' ring', g: dom === 'URDF' ? 'L' : 'C', l: [b.desc, `${b.n} mutants`, `caught by: ${b.catcher}`].concat(b.codes && b.codes.length ? ['Khronos code ' + b.codes.join(', ')] : []).concat(b.repaired ? [`deterministic repair ends clean on ${b.repaired}`] : []), src: dom === 'URDF' ? 'out/xdomain_urdf.json (my own rules)' : 'out/xdomain_gltf.json (Khronos validator)' }; }
// ------------------------------------------------------------------ per-frame registry refresh and picking
function refreshFrames() { UI.frames = { c: readQ('ConstSpin'), tilt: { X3D: readQ('Tilt_X3D'), URDF: readQ('Tilt_URDF'), glTF: readQ('Tilt_glTF') }, spin: { X3D: readQ('Spin_X3D'), URDF: readQ('Spin_URDF'), glTF: readQ('Spin_glTF') }, loopTilt: readQ('LoopTilt'), loop: readQ('LoopRing') }; }
function refreshReg() {
  const S = E.S, near = E.near, far = !near, nearTown = E.alt < 6e5 && V.len(E.camT) < 5e5, constOn = !E.hidden.const && E.constMode !== 'off' && (typeof fadeLast === 'number' ? fadeLast > 0.25 : true);
  if (constOn) refreshFrames();
  for (const e of E.reg) {
    let on;
    switch (e.cat) {
      case 'body': on = e.id === 'earth' ? (far || E.alt > 20000) : true; if (e.id === 'sun' && near && S.sunElev < -1 * D2R && E.alt < 50000) on = false; if (e.id === 'moon' && near && S.moonElev < -1 * D2R && E.alt < 50000) on = false; break;
      case 'town': on = far || E.alt > 3000; break;
      case 'class': case 'bead': case 'station': case 'pillar': on = constOn; break;
      default: on = nearTown && E.alt < 3e5;
    }
    e.on = on; if (!on) continue; e.tc = e.tw ? e.tw(S) : S.toTown(e.sc(S));
  }
}
function rayOBB(o, d, b) { const c = Math.cos(b.rot), s = Math.sin(b.rot), r = V.sub(o, b.c); const lo = [c * r[0] - s * r[2], r[1], s * r[0] + c * r[2]], ld = [c * d[0] - s * d[2], d[1], s * d[0] + c * d[2]]; let t0 = 0, t1 = 1e18; for (let i = 0; i < 3; i++) { if (Math.abs(ld[i]) < 1e-9) { if (Math.abs(lo[i]) > b.h[i]) return -1; } else { let a = (-b.h[i] - lo[i]) / ld[i], z = (b.h[i] - lo[i]) / ld[i]; if (a > z) [a, z] = [z, a]; t0 = Math.max(t0, a); t1 = Math.min(t1, z); if (t0 > t1) return -1; } } return t0; }
function pickAt(mx, my) {
  if (!E.camT) return null; const view = OV.view || E.viewMatrix(), ray = view.ray(mx, my); let best = null, bs = Infinity, br = 9;
  for (const e of E.reg) { if (!e.on) continue; const oc = V.sub(e.tc, ray.o), t = V.dot(oc, ray.d); if (t <= 0) continue; const dist = Math.sqrt(V.dot(oc, oc)), rank = e.cat === 'person' ? 0 : 1; if (rank > br) continue; let sc = -1;
    if (e.obb) { const tt = rayOBB(ray.o, ray.d, e.obb); if (tt >= 0) sc = tt + e.r * 0.2; }
    if (sc < 0 && !e.obb || sc < 0 && e.cat === 'person') { const tol = (e.cat === 'person' ? 14 : e.cat === 'body' || e.cat === 'town' ? 6 : 10) / view.sy * dist, rr = Math.max(e.r, tol), d2 = V.dot(oc, oc) - t * t; if (d2 <= rr * rr) sc = t - Math.sqrt(Math.max(0, rr * rr - d2)) + 0.5 * rr; }
    if (sc >= 0 && (rank < br || sc < bs)) { bs = sc; br = rank; best = e; } }
  return best;
}
// ------------------------------------------------------------------ navigation presets
function sunSideCam(focus, d, off = 0.8, dEl = 0.22) { const S = E.S, p = focus === 'earth' ? S.E : S.M, dir = V.norm(V.sub([0, 0, 0], p)), az = Math.atan2(dir[0], -dir[2]) + off, el = Math.asin(dir[1]) + dEl; return { f: focus, d, az, el, pan: [0, 0], h: 1.4, id: null }; }
function placeCam(name) {
  const base = { pan: [0, 0], h: 1.4, id: null };
  switch (name) {
    case 'constellation': return Object.assign({ f: 'system', d: 1.15e12, az: 0.5, el: 0.45 }, base);
    case 'sun': return Object.assign({ f: 'sun', d: 5.5e9, az: 0.9, el: 0.18 }, base);
    case 'earth': return sunSideCam('earth', 2.6e7);
    case 'moon': return sunSideCam('moon', 5.2e6);
    case 'orbit': return Object.assign({ f: 'town', d: 2.4e6, az: 2.9, el: 0.95 }, base);
    case 'village': return Object.assign({ f: 'town', d: 620, az: 2.45, el: 0.5 }, base);
    case 'plaza': return Object.assign({ f: 'town', d: 21, az: -2.28, el: 0.1 }, base, { pan: [3, -4] });
    case 'street': return Object.assign({ f: 'town', d: 7, az: 1.7, el: 0.1 }, base, { pan: [-34, 2.2] });
    case 'nightsky': return Object.assign({ f: 'town', d: 0.05, az: 2.3, el: 1.05, look: true }, base, { pan: [-3, 6] });
  }
}
function go(name, opt) {
  if (name === 'person') { const p = UI.people[UI.personIdx++ % UI.people.length]; return goEntry(E.by.get(p.id), opt); }
  return E.flyTo(placeCam(name), opt || {});
}
function goEntry(e, opt) {
  if (!e) return Promise.resolve(); UI.pin = e; showInfo();
  if (e.special === 'village') return E.flyTo({ f: 'town', pan: [0, 0], d: 2200, az: 2.6, el: 0.7, h: 1.4, id: null }, opt || {});
  let az = E.cam.az, el = 0.3;
  if (e.cat === 'person') { const v = nd('T_' + e.id).rotation, yaw = v.y >= 0 ? v.angle : -v.angle; az = Math.PI - yaw + 0.5; el = 0.14; } else if (e.cat === 'building') { el = 0.28; az = Math.PI - UI.town.houses.find(h => h.id === e.id).rot + 0.45; } else if (e.cat === 'prop') el = 0.25;
  return E.flyTo({ f: 'obj', id: e.id, d: e.fd, az, el, pan: [0, 0], h: 1.4 }, opt || {});
}
// ------------------------------------------------------------------ time controls
function scanSun(kind) {
  const base = E.t - localHours(E.t) * 3600; let res = null, max = -9, tmax = base + 43200;
  for (let s = 0; s < 86400; s += 120) { const t = base + s, el = solar(t).sunElev / D2R; if (el > max) { max = el; tmax = t; }
    if (kind === 'dawn' && !res && s > 3600 && el >= 2.5) res = t; if (kind === 'golden' && s > 43200 && !res && el <= 9) res = t; if (kind === 'dusk' && s > 43200 && !res && el <= -3.5) res = t; }
  if (kind === 'noon') return tmax; if (kind === 'night') return base + (localHours(E.t) > 1.5 ? 86400 : 0) + 1.5 * 3600; return res;
}
function timePreset(k) { if (k === 'now') { E.t = nowS(); E.rate = 1; E.paused = false; return; } if (k === 'eclipse') return window.stageEclipse ? window.stageEclipse() : UI.toast('eclipse staging not available yet'); const t = scanSun(k); if (t) E.t = t; E.paused = true; E.rate = 1; }
// ------------------------------------------------------------------ staged total solar eclipse over the village
window.stageEclipse = function () {
  if (!ECLIPSE.on) { UI.toast('searching the next two years for the best new moon…'); const i = findEclipse(); if (!i) return UI.toast('no suitable new moon found'); }
  const S0 = solar(ECLIPSE.t0); E.t = ECLIPSE.t0 - 42 * 60; E.rate = 150; E.paused = false; E.eclAuto = true; E.constMode = 'off'; $('cm').textContent = 'off'; const c = placeCam('nightsky'); c.az = Math.atan2(S0.sunT[0], -S0.sunT[2]) - 0.5; c.el = Math.asin(S0.sunT[1]) - 0.15; c.pan = [-2, 8]; E.flyTo(c, { dur: 5, fov: 0.95 });
  const i = ECLIPSE.info; UI.toast(`staged eclipse: raw closest approach ${i.rawSepDeg.toFixed(2)}°, Moon nudged ${i.nudgeKm.toFixed(0)} km (${i.nudgeDeg.toFixed(2)}°) for ±5 h`);
};
function eclipseAuto(dt) {
  if (!E.eclAuto || E.flight && E.flight.dur > 1e11) return; const S = E.S; if (!ECLIPSE.on) { E.eclAuto = false; return; } const ob = S.obsc || 0;
  if (E.cam.look && !E.flight) { const azT = Math.atan2(S.sunT[0], -S.sunT[2]), elT = Math.asin(clamp(S.sunT[1], -1, 1)), k = 1 - Math.exp(-dt * 2.2); let da = azT - E.cam.az; da = Math.atan2(Math.sin(da), Math.cos(da)); const off = E.eclAim === 'sun' ? 0 : 0; E.cam.az += da * k; E.cam.el += (elT - E.cam.el) * k; const fovT = mix(0.95, 0.2, smooth(0.0, 0.55, ob)); E.fov += (fovT - E.fov) * (1 - Math.exp(-dt * 1.5)); }
  E.rate = ob > 0.985 ? 12 : ob > 0.5 ? 55 : ob > 0.02 ? 150 : (E.t < ECLIPSE.t0 ? 220 : 300); if (E.t > ECLIPSE.t0 + 75 * 60) { E.eclAuto = false; E.paused = true; E.rate = 1; }
}
// ------------------------------------------------------------------ input
function wire() {
  const cv = E.canvas, opt = { passive: false, capture: true };
  cv.addEventListener('contextmenu', e => e.preventDefault(), opt);
  cv.addEventListener('pointerdown', e => { UI.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY }); try { cv.setPointerCapture(e.pointerId); } catch (_) { } UI.drag = UI.ptrs.size === 1 ? { x: e.clientX, y: e.clientY, shift: e.shiftKey || e.button === 2 || e.button === 1, moved: 0, t: performance.now(), btn: e.button } : null; UI.vel.az = UI.vel.el = 0; if (window.tourPause) tourPause(); e.preventDefault(); }, opt);
  cv.addEventListener('pointermove', e => {
    UI.mx = e.clientX; UI.my = e.clientY; UI.inside = true; const pp = UI.ptrs.get(e.pointerId); if (!pp) return; const px = pp.x, py = pp.y; pp.x = e.clientX; pp.y = e.clientY;
    if (UI.ptrs.size === 2) { const a = [...UI.ptrs.values()], d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y), d0 = UI.pinch || d; UI.pinch = d; zoomBy(Math.log(d0 / d) * 1.2); return; }
    if (UI.drag && !E.flight) { const dx = e.clientX - px, dy = e.clientY - py; UI.drag.moved += Math.abs(dx) + Math.abs(dy); if (E.cam.look) { const k = 0.0042 * Math.min(1, E.fov / 0.9); E.cam.az -= dx * k; E.cam.el = clamp(E.cam.el + dy * k, -1.4, 1.55); } else if (UI.drag.shift) panBy(-dx, -dy); else { const k = 0.0052; E.cam.az -= dx * k; E.cam.el = clamp(E.cam.el + dy * k, -1.5, 1.52); UI.vel.az = -dx * k * 60; UI.vel.el = dy * k * 60; } }
  }, opt);
  const up = e => { UI.ptrs.delete(e.pointerId); UI.pinch = 0; if (UI.drag && UI.drag.moved < 5 && performance.now() - UI.drag.t < 450 && UI.drag.btn === 0) clickAt(e.clientX, e.clientY); UI.drag = null; };
  cv.addEventListener('pointerup', up, opt); cv.addEventListener('pointercancel', up, opt); cv.addEventListener('pointerleave', () => { UI.inside = false; }, opt);
  cv.addEventListener('wheel', e => { e.preventDefault(); const dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1); if (window.tourPause) tourPause(); zoomBy(dy * (e.ctrlKey ? 0.012 : 0.0012), true); }, opt);
  cv.addEventListener('dblclick', e => { const p = pickAt(e.clientX, e.clientY); if (p) goEntry(p); else zoomBy(-0.7); }, opt);
  window.addEventListener('keydown', e => { if (e.metaKey || e.ctrlKey || e.altKey) return; const k = e.key.toLowerCase(); UI.keys[k] = true; keyCmd(k, e); });
  window.addEventListener('keyup', e => { UI.keys[e.key.toLowerCase()] = false; });
  $('mini').addEventListener('click', e => { const r = $('mini').getBoundingClientRect(), x = ((e.clientX - r.left) / r.width - 0.5) * 560, z = ((e.clientY - r.top) / r.height - 0.5) * 560; E.flyTo({ f: 'town', pan: [x, z], d: Math.min(E.pose ? E.pose.w : 80, 90), az: E.cam.az, el: Math.max(0.12, E.cam.el), id: null, h: 1.4 }, { dur: 2.2 }); });
  $('nav').onclick = e => { const b = e.target.closest('button'); if (!b) return; if (b.dataset.go) go(b.dataset.go); else { const a = b.dataset.act; if (a === 'film') filmStart(); else if (a === 'tour') tourOpen(0); else if (a === 'const') keyCmd('c', e); else if (a === 'labels') UI.labelsOn = !UI.labelsOn; else if (a === 'help') toggle('help'); } };
  $('clock').onclick = e => { const b = e.target.closest('button'); if (!b) return; if (b.dataset.rate != null) { const r = +b.dataset.rate; if (r === 0) E.paused = true; else { E.paused = false; E.rate = r; } } else if (b.dataset.tod) timePreset(b.dataset.tod); };
  $('sndbtn').onclick = () => soundToggle && soundToggle();
}
function zoomBy(dl, fromWheel) {
  if (E.flight) return; if (E.cam.look) { E.fov = clamp(E.fov * Math.exp(dl * 0.8), 0.2, 1.5); return; } const c = E.cam, hov = UI.hover; const d = c.d * Math.exp(dl);
  if (dl < 0 && fromWheel && hov && hov.cat !== 'person' && !(c.f === 'obj' && c.id === hov.id)) { const dist = V.len(V.sub(hov.tc, E.camT)); if (dist > hov.r * 3 && dist < c.d * 3 + 1 && performance.now() - (UI.diveCool || 0) > 900) { UI.diveCool = performance.now(); E.flyTo({ f: hov.special === 'village' ? 'town' : 'obj', id: hov.id, d: Math.max(hov.fd, dist * 0.5), az: c.az, el: c.el, pan: [0, 0], h: 1.4 }, { dur: 1.3 }); return; } }
  c.d = clamp(d, E.focusMin(c), E.focusMax(c));
}
function panBy(dx, dy) {
  const c = E.cam; if (c.f !== 'town') { c.az -= dx * 0.004; c.el = clamp(c.el + dy * 0.004, -1.5, 1.52); return; }
  const k = Math.max(0.02, c.d * 0.0012), fx = Math.sin(c.az + Math.PI), fz = -Math.cos(c.az + Math.PI), rx = -fz, rz = fx; c.pan[0] += (rx * dx - fx * dy) * k; c.pan[1] += (rz * dx - fz * dy) * k; clampPan();
}
function clampPan() { const c = E.cam, r = Math.hypot(c.pan[0], c.pan[1]); if (r > 3000) { c.pan[0] *= 3000 / r; c.pan[1] *= 3000 / r; } }
function clickAt(x, y) { const p = pickAt(x, y), now = performance.now(); if (now - UI.lastClick < 320 && p) { goEntry(p); UI.lastClick = 0; return; } UI.lastClick = now; UI.pin = p; showInfo(); if (window.sfx) sfx.click(); }
function keyCmd(k, e) {
  if (/^[1-8]$/.test(k) && !UI.tourOpen) { go(['constellation', 'sun', 'earth', 'moon', 'orbit', 'village', 'plaza', 'person'][+k - 1]); return; }
  switch (k) {
    case 'escape': if (UI.cineOn) return filmStop(); if (E.flight) { E.flight.t0 = -1e9; return; } if (UI.tourOpen) return tourClose(); UI.pin = null; showInfo(); $('help').style.display = 'none'; break;
    case ' ': E.paused = !E.paused; e.preventDefault(); break; case 'h': case '?': toggle('help'); break; case 'g': toggleLook(); break; case 'l': UI.labelsOn = !UI.labelsOn; break;
    case 'c': E.constMode = E.constMode === 'auto' ? 'on' : E.constMode === 'on' ? 'off' : 'auto'; $('cm').textContent = E.constMode; break;
    case 'f': filmStart(); break; case 't': tourOpen(0); break; case 'm': soundToggle(); break;
    case '[': E.rate = Math.max(1, Math.abs(E.rate) / 4); break; case ']': E.rate = Math.min(5e6, Math.max(1, Math.abs(E.rate)) * 4); E.paused = false; break;
    case 'arrowright': if (UI.tourOpen) tourOpen(UI.tourI + 1); break; case 'arrowleft': if (UI.tourOpen) tourOpen(UI.tourI - 1); break;
  }
}
function toggleLook() {
  const c = E.cam, S = E.S; if (c.look) { const a = c.az, p0 = c.pan; c.look = false; c.d = 12; c.pan = [p0[0] + Math.sin(a) * 12, p0[1] - Math.cos(a) * 12]; c.az = a + Math.PI; c.el = 0.16; c.h = 1.4; E.fov = 0.95; return; }
  if (!E.near || E.alt > 400) { UI.toast && UI.toast('Walk mode needs a ground position: press 7 (plaza) first'); return; }
  const f = E.fwdT, ct = E.camT; c.look = true; c.f = 'town'; c.pan = [ct[0], ct[2]]; c.az = Math.atan2(f[0], -f[2]); c.el = Math.asin(clamp(f[1], -1, 1)); c.d = 0.05; E.fov = 0.95; }
function toggle(id) { const n = $(id), on = n.style.display !== 'block'; $('help').style.display = 'none'; n.style.display = on ? 'block' : 'none'; }
function stepKeys(dt) {
  const k = UI.keys; if (E.flight) return; const c = E.cam; let mx = 0, my = 0, rot = 0, zm = 0;
  if (k['w'] || k['arrowup']) my -= 1; if (k['s'] || k['arrowdown']) my += 1; if (k['a'] || (k['arrowleft'] && !UI.tourOpen)) mx -= 1; if (k['d'] || (k['arrowright'] && !UI.tourOpen)) mx += 1; if (k['q']) rot -= 1; if (k['e']) rot += 1; if (k['r']) zm -= 1; if (k['z']) zm += 1;
  if ((mx || my) && c.look) { const sp = (k['shift'] ? 9 : 2.6) * dt, ps = Math.sin(c.az), pc = Math.cos(c.az); c.pan[0] += (ps * -my + pc * mx) * sp; c.pan[1] += (-pc * -my + ps * mx) * sp; clampPan(); }
  else if (mx || my) { if (c.f === 'town') panBy(mx * 360 * dt * (k['shift'] ? 3 : 1), my * 360 * dt * (k['shift'] ? 3 : 1)); else { c.az -= mx * dt * 0.8; c.el = clamp(c.el - my * dt * 0.6, -1.5, 1.52); } if (window.tourPause) tourPause(); }
  if (rot) c.az += rot * dt * 1.1; if (zm) if (!c.look) c.d = clamp(c.d * Math.exp(zm * dt * 1.2), E.focusMin(c), E.focusMax(c));
}
// ------------------------------------------------------------------ HUD, tooltip, info panel
function infoBlock(i, max) { return [el('div', { class: 'h' }, i.t, ' ', gradeTag(i.g)), i.sub && el('div', { class: 'sub' }, i.sub)].concat(i.l.slice(0, max || 99).map(x => el('div', { class: 'ln' }, x)), i.live && el('div', { class: 'live', id: 'live' }, i.live), el('div', { class: 'src' }, i.src || '')); }
function showInfo() {
  const p = $('info'), e = UI.pin; if (!e || !e.on) { p.style.display = 'none'; return; } const i = e.info ? e.info(E.S) : { t: e.name, l: [] };
  const acts = el('div', { class: 'acts' }, el('button', { onclick: () => goEntry(e) }, 'Fly here'), e.cat === 'person' && el('button', { onclick: () => { const ps = UI.people, i2 = ps.findIndex(x => x.id === e.id); goEntry(E.by.get(ps[(i2 + 1) % ps.length].id)); } }, 'Next villager'), el('button', { onclick: () => { UI.pin = null; showInfo(); } }, 'Close'));
  setKids(p, infoBlock(i), acts); p.style.display = 'block';
}
function showTip() {
  const t = $('tip'), e = UI.hover; if (!e || !e.on || UI.drag && UI.drag.moved > 5) { t.style.display = 'none'; UI.tipFor = null; return; }
  if (UI.tipFor !== e) { const i = e.info ? e.info(E.S) : { t: e.name, l: [] }; const b = infoBlock(i, 5); setKids(t, b); const h = b[0]; UI.tipFor = e; }
  t.style.display = 'block'; const w = t.offsetWidth, h = t.offsetHeight; t.style.left = Math.min(innerWidth - w - 12, UI.mx + 18) + 'px'; t.style.top = Math.min(innerHeight - h - 12, UI.my + 18) + 'px';
}
function hud() {
  const c = E.cam, f = E.FOCUS[c.f], e = c.f === 'obj' ? E.by.get(c.id) : null; $('where').textContent = c.look ? 'Village · walking (G to leave)' : e ? e.name : f ? f.label : '—'; const w = E.pose ? E.pose.w : c.d;
  $('dist').textContent = `${fmtD(w)} from the focus` + (E.near ? ` · altitude ${fmtD(Math.max(0, E.alt))}` : '') + (E.flight ? ' · flying…' : '');
  $('utc').textContent = new Date(E.t * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const rate = E.paused ? 'paused' : E.rate === 1 ? 'real time' : E.rate >= 86400 ? +(E.rate / 86400).toPrecision(2) + ' days/s' : E.rate >= 3600 ? +(E.rate / 3600).toPrecision(2) + ' h/s' : +(E.rate / 60).toPrecision(2) + ' min/s';
  setKids($('lst'), el('span', null, 'village solar time ' + fmtHM(localHours(E.t)) + ' · sun ' + ldeg(E.S.sunElev) + (E.S.obsc > 0.001 ? ' · eclipse ' + (E.S.obsc * 100).toFixed(1) + ' %' : '')), el('span', null, rate));
  document.querySelectorAll('#clock [data-rate]').forEach(b => b.classList.toggle('on', (b.dataset.rate === '0' && E.paused) || (!E.paused && +b.dataset.rate === E.rate)));
}
// ------------------------------------------------------------------ boot
function lstat(t) { const l = $('lstat'); if (l) l.textContent = t; }
function boot() {
  ovInit(); E.canvas = $('cv'); E.constMode = 'auto'; const t0 = performance.now();
  const iv = setInterval(() => { if (E.ready) { clearInterval(iv); return; } lstat(`X_ITE ${typeof X3D !== 'undefined' ? 'loaded' : 'NOT loaded (cdn.jsdelivr.net blocked?)'} · scene parsing · ${((performance.now() - t0) / 1000) | 0} s`); }, 700);
  window.addEventListener('error', e => { const x = $('err'); x.style.display = 'block'; x.textContent = 'Script error: ' + e.message; });
  X3D(async () => {
    try {
      const B = E.B = X3D.getBrowser(E.canvas); lstat('loading data…'); await loadData();
      const ready = () => {
        if (E.ready || !nd('World') || !nd('Cam') || !nd('T_P01')) return;
        for (const [k, v] of [['LogarithmicDepthBuffer', true], ['ToneMapping', 'KHR_PBR_NEUTRAL'], ['PrimitiveQuality', 'HIGH'], ['TextureQuality', 'HIGH']]) { try { B.setBrowserOption(k, v); } catch (e) { console.warn('option', k, e); } }
        try { const kl = nd('KeyLight'); kl.shadowMapSize = 4096; kl.shadowBias = 0.004; } catch (e) { console.warn('shadow', e); }
        try { nd('CloudsT').children[0].appearance.material.transparency = 0.02; } catch (e) { console.warn('clouds', e); }   // a non-zero transparency puts the cloud shell on X_ITE's blend path
        lstat('building the pick registry…'); refreshFrames(); buildRegistry(); wire(); initStart();
        E.ready = true; $('load').style.opacity = 0; setTimeout(() => $('load').style.display = 'none', 900); nd('Cam').set_bind = true; console.log('v2 ready'); window.dispatchEvent(new Event('v2ready'));
      };
      B.addBrowserCallback('boot', X3D.X3DConstants.INITIALIZED_EVENT, () => setTimeout(ready, 400)); setInterval(ready, 900);
    } catch (e) { $('err').style.display = 'block'; $('err').textContent = 'Failed: ' + e; }
  }, e => { $('err').style.display = 'block'; $('err').textContent = 'X_ITE failed: ' + e; });
  E.onFrame.push(frameUI); requestAnimationFrame(frame);
}
function initStart() {
  E.t = nowS(); E.rate = 1; Object.assign(E.cam, placeCam('constellation')); E.fov = 0.9;
  UI.toast = msg => { const t = $('foot'), old = t.firstChild; setKids(t, el('b', null, msg)); setTimeout(() => setKids(t, old), 2600); };
}
let uiTick = 0;
function frameUI(dt, now) {
  eclipseAuto(dt); stepKeys(dt); if (!E.flight && !UI.drag) { E.cam.az += UI.vel.az * dt; E.cam.el = clamp(E.cam.el + UI.vel.el * dt, -1.5, 1.52); const k = Math.exp(-dt * 3.2); UI.vel.az *= k; UI.vel.el *= k; if (Math.abs(UI.vel.az) < 1e-3) UI.vel.az = 0; if (Math.abs(UI.vel.el) < 1e-3) UI.vel.el = 0; }
  if (E.cam.f === 'town') { clampPan(); const c = E.cam; if (!c.look) c.d = clamp(c.d, E.focusMin(c), E.focusMax(c)); }
  refreshReg(); if (UI.inside && !UI.drag && !E.flight) UI.hover = pickAt(UI.mx, UI.my); else if (E.flight || !UI.inside) UI.hover = null; if (E.canvas) E.canvas.style.cursor = UI.hover ? 'pointer' : UI.drag ? 'grabbing' : 'grab';
  drawOverlay(dt, now); showTip(); if ((uiTick++ & 7) === 0) { hud(); const e = UI.pin; if (e) { if (!e.on) { UI.pin = null; showInfo(); } else if (e.info && $('live')) { const i = e.info(E.S); if (i.live) $('live').textContent = i.live; } } }
  if (UI.snd) UI.snd(dt);
}
window.V2 = { E, UI, cam: E.cam, go, goEntry, setTime(iso) { E.t = Date.parse(iso) / 1000; }, rate(r) { E.rate = r; E.paused = false; }, pause(p) { E.paused = p; }, place: placeCam, tod: timePreset, pickAt };
boot();
