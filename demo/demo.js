// ---- loader diagnostics: never a silent blank page
(function () { const t0 = performance.now(), L = () => document.getElementById('load'); const gl = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch (e) { return false } })();
  const iv = setInterval(() => { const l = L(); if (!l || l.style.display === 'none') { clearInterval(iv); return; } const s = ((performance.now() - t0) / 1000) | 0;
    const parts = [`X_ITE library: ${typeof X3D !== 'undefined' ? 'loaded' : 'NOT loaded (cdn.jsdelivr.net blocked or offline?)'}`, `WebGL: ${gl ? 'available' : 'NOT available in this browser'}`, `waiting ${s} s`];
    l.innerHTML = `<div style="text-align:center;max-width:520px"><div style="font-size:18px;color:#d7deea;margin-bottom:6px">Loading the Ontology Dyson sphere</div><div>${parts.join(' · ')}</div><div style="margin-top:8px;font-size:12px">The scene has about 8,000 nodes and 460 touch sensors; the first load can take 10 to 40 seconds on a busy machine. If this does not change after a minute, open the browser console.</div></div>`; }, 1000);
  window.addEventListener('error', e => { const x = document.getElementById('err'); if (x) { x.style.display = 'block'; x.textContent = 'Script error: ' + e.message; } }); })();
// Ontology Dyson sphere: film, curator tour, tooltips, synthesised soundtrack. All data from tour-data.json (built from files with sources).
let B, D, ctx = null, master = null, soundOn = localStorage.getItem('dyson-sound') !== '0', dirty = false, assembled = false, filmOn = false, filmT0 = 0, filmTimer = null, tourI = -1, flyTok = 0, pin = null, hover = null, mx = 0, my = 0;
let pose = { p: [0, 16, 100], t: [0, 0, 0] };
const $ = id => document.getElementById(id), now = () => Date.now() / 1000, esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const nd = n => { try { return B.currentScene.getNamedNode(n) } catch (e) { return null } };
function V(n) { const v = nd(n); if (v) v.set_bind = true; }
function toggle(id) { const e = $(id), on = e.style.display !== 'block'; ['leg', 'help'].forEach(x => $(x).style.display = 'none'); e.style.display = on ? 'block' : 'none'; }
// ---- camera maths (port of the builder's look())
const qm = (a, b) => [a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3], a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2], a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1], a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]];
const aa = (ax, an) => { const s = Math.sin(an / 2); return [Math.cos(an / 2), ax[0] * s, ax[1] * s, ax[2] * s] };
function ori(p, t) {
  const dx = t[0] - p[0], dy = t[1] - p[1], dz = t[2] - p[2], yaw = Math.atan2(-dx, -dz), pitch = Math.atan2(dy, Math.hypot(dx, dz)), q = qm(aa([0, 1, 0], yaw), aa([1, 0, 0], pitch));
  const w = Math.max(-1, Math.min(1, q[0])), an = 2 * Math.acos(w), s = Math.sqrt(Math.max(1e-12, 1 - w * w));
  return an > 1e-6 ? new X3D.SFRotation(q[1] / s, q[2] / s, q[3] / s, an) : new X3D.SFRotation(0, 1, 0, 0);
}
function fly(toP, toT, dur = 3000) {
  const tok = ++flyTok, vp = nd('Tour'), p0 = pose.p.slice(), t0 = pose.t.slice();
  vp.position = new X3D.SFVec3f(...p0); vp.orientation = ori(p0, t0); vp.set_bind = true; const s = performance.now();
  return new Promise(res => { (function step() {
    const u = Math.min(1, (performance.now() - s) / dur), e = u * u * (3 - 2 * u), p = p0.map((a, i) => a + (toP[i] - a) * e), t = t0.map((a, i) => a + (toT[i] - a) * e);
    vp.position = new X3D.SFVec3f(...p); vp.orientation = ori(p, t);
    if (u < 1 && tok === flyTok) requestAnimationFrame(step); else { if (tok === flyTok) pose = { p: toP, t: toT }; res(); } })(); });
}
function halo(h) { const n = nd('HaloT'); if (!n) return; if (!h || !h.s) { n.scale = new X3D.SFVec3f(0, 0, 0); return; } n.translation = new X3D.SFVec3f(...h.at); const k = h.s * 0.55; n.scale = new X3D.SFVec3f(k, k, k); }
// ---- sound (WebAudio, no files)
function audio() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)(); master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520; lp.connect(master); const lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value = 0.07; lg.gain.value = 260; lfo.connect(lg); lg.connect(lp.frequency); lfo.start();
    [[55, 'sine', .22], [82.41, 'triangle', .1], [110.3, 'sine', .12], [164.8, 'triangle', .05], [220.4, 'sine', .03]].forEach(([f, ty, g], i) => { const o = ctx.createOscillator(), og = ctx.createGain(); o.type = ty; o.frequency.value = f * (1 + (i - 2) * 0.0013); og.gain.value = g; o.connect(og); og.connect(lp); o.start(); });
  }
  if (ctx.state === 'suspended') ctx.resume(); master.gain.setTargetAtTime(soundOn ? 0.55 : 0, ctx.currentTime, 0.4); $('snd').classList.toggle('on', soundOn);
}
function sound() { soundOn = !soundOn; localStorage.setItem('dyson-sound', soundOn ? '1' : '0'); audio(); }
function ping(f, d = 1.4, v = .16, at = 0) { if (!ctx || !soundOn) return; const t = ctx.currentTime + at, o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.value = f; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(v, t + .02); g.gain.exponentialRampToValueAtTime(0.0001, t + d); o.connect(g); g.connect(master); o.start(t); o.stop(t + d + .1); }
function arp() { [440, 554.4, 659.3, 880].forEach((f, i) => ping(f, 1.6, .12, i * .09)); }
function whoosh(d = 4) { if (!ctx || !soundOn) return; const n = ctx.sampleRate * d, b = ctx.createBuffer(1, n, ctx.sampleRate), x = b.getChannelData(0); for (let i = 0; i < n; i++) x[i] = Math.random() * 2 - 1; const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain(), t = ctx.currentTime; s.buffer = b; f.type = 'bandpass'; f.Q.value = 3; f.frequency.setValueAtTime(180, t); f.frequency.exponentialRampToValueAtTime(3400, t + d); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(.35, t + d * .8); g.gain.exponentialRampToValueAtTime(0.0001, t + d); s.connect(f); f.connect(g); g.connect(master); s.start(t); }
function boom() { if (!ctx || !soundOn) return; const t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.setValueAtTime(120, t); o.frequency.exponentialRampToValueAtTime(26, t + 1.8); g.gain.setValueAtTime(.7, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 2); o.connect(g); g.connect(master); o.start(t); o.stop(t + 2.1); }
// ---- assemble
function assemble() { const c = nd('AssembleClock'); if (!c) return; audio(); c.startTime = now(); assembled = dirty = true; whoosh(4.5); setTimeout(boom, 12800); }
function disassemble() { const c = nd('DisassembleClock'); if (c) { audio(); c.startTime = now(); assembled = false; dirty = true; whoosh(3); } }
// ---- film
function film() { if (!nd('FilmClock')) return; if (dirty) { location.hash = 'film'; location.reload(); return; } startFilm(); }
function startFilm() {
  closeTour(); audio(); $('cine').style.display = 'block'; ['title', 'bar', 'foot'].forEach(i => $(i).style.opacity = .0); filmT0 = performance.now(); nd('FilmClock').startTime = now(); filmOn = true; dirty = true; let ci = -1;
  clearInterval(filmTimer); filmTimer = setInterval(() => {
    const t = (performance.now() - filmT0) / 1000; $('pb').style.width = Math.min(100, t / 75 * 100) + '%';
    let k = -1; D.film.forEach((c, i) => { if (t >= c[0]) k = i; });
    if (k !== ci) { ci = k; const c = D.film[k]; $('ch').textContent = c[1]; $('cs').textContent = c[2]; const card = $('cc'); card.classList.remove('on'); setTimeout(() => card.classList.add('on'), 120); arp(); setTimeout(() => { if (ci === k && k !== 0 && k !== D.film.length - 1) card.classList.remove('on'); }, 5200); }
    if (Math.abs(t - 44) < .15) whoosh(5); if (Math.abs(t - 57.2) < .15) boom();
    if (t > 76) endFilm();
  }, 100);
}
function endFilm() { clearInterval(filmTimer); filmOn = false; setTimeout(() => { $('cine').style.display = 'none'; ['title', 'bar', 'foot'].forEach(i => $(i).style.opacity = 1); }, 2500); }
function skipFilm() { if (!filmOn) return; nd('FilmClock').stopTime = now(); const d = nd('Delay44'); if (d) d.stopTime = now(); clearInterval(filmTimer); filmOn = false; $('cine').style.display = 'none'; ['title', 'bar', 'foot'].forEach(i => $(i).style.opacity = 1); V('Orbit'); }
// ---- tour
function closeTour() { $('tour').style.display = 'none'; tourI = -1; halo(null); }
async function tour(i) {
  if (!nd('FilmClock')) return;
  if (i === 0 && dirty) { location.hash = 'tour'; location.reload(); return; }
  const s = D.stops[i]; if (!s) return; tourI = i; hover = null; pin = null; $('tip').style.display = 'none'; audio(); ping(660, 1.2, .1); const el = $('tour'); el.style.display = 'block';
  el.innerHTML = `<div class="n">Stop ${i + 1} of ${D.stops.length} · grade ${s.grade}</div><h3>${esc(s.title)}</h3><div>${esc(s.text)}</div><div class="look"><b>What to look for.</b> ${esc(s.look)}</div><div class="src">Source: ${esc(s.src)}</div><div class="dots">${D.stops.map((x, k) => `<i class="${k === i ? 'on' : ''}" title="${esc(x.title)}" onclick="tour(${k})"></i>`).join('')}</div><div class="nav"><button onclick="tour(${i - 1})" ${i ? '' : 'disabled'}>Back</button><button onclick="closeTour()" data-tip="Leave the guided path and roam freely">Free roam</button><button class="go" id="nx" onclick="tour(${i + 1})" ${i < D.stops.length - 1 ? '' : 'disabled'}>Next</button></div>`;
  halo(s.halo);
  if (s.action === 'assemble') { assemble(); $('nx').disabled = true; setTimeout(() => { if (tourI === i) $('nx').disabled = false; }, 17000); return; }
  if (s.action === 'orbit') { V('Orbit'); halo(null); return; }
  if (s.cam) await fly(s.cam, s.tgt, i === 0 ? 1200 : 3200);
}
// ---- tooltips
const FAM = '';
function info(name) {
  const c = D.classes;
  if (name.startsWith('T_St_')) { const s = D.stations[+name.slice(5)]; return { t: s[0], l: [s[1]], g: s[2], src: 'demo/DEMO-SPEC.md, measured numbers per source' }; }
  if (name.startsWith('T_P_')) { const [, , dom, j] = name.split('_'), e = D.pillars[dom]; const lab = j === '0' ? 'first try' : 'after the report loop';
    return e ? { t: `${dom}: ${lab}`, l: [`${j === '0' ? e.a0 : e.a2}% valid (Gemini flash, n=${e.n} first tries)`], g: 'C', src: 'xdomain/eval-plan/runs' } : { t: `${dom}: ${lab}`, l: ['Evaluation still running: this pillar is a ghost.'], g: 'L', src: 'xdomain/eval-plan/PLAN.md' }; }
  const m = name.match(/^T_(X3D|URDF|glTF)_(\d+)$/);
  if (m) { const b = D.beads[m[1]][+m[2]]; if (m[1] === 'X3D') return { t: `X3D component ${b.name}`, l: [`${b.nodes} concrete nodes${b.new ? ', ' + b.new + ' new in 4.1' : ''}`, `XSD accepts ${b.pct}% of the ontology's placements`, `X3DUOM lists agree with the XSD on ${b.agree}% of the pairs`], g: 'C', src: 'data/components.json' };
    return { t: `${m[1]} fault ${b.id}`, l: [b.desc, `${b.n} mutants`, `caught by: ${b.catcher}`].concat(b.codes && b.codes.length ? ['Khronos code ' + b.codes.join(', ')] : []).concat(b.repaired ? [`deterministic repair ends clean on ${b.repaired}`] : []), g: m[1] === 'URDF' ? 'L' : 'C', src: m[1] === 'URDF' ? 'out/xdomain_urdf.json (my own rules)' : 'out/xdomain_gltf.json (Khronos validator)' }; }
  const id = name.slice(2), k = c[id]; if (!k) return { t: name, l: [], g: 'L', src: '' };
  return { t: id, l: [`${k.kind}${k.comp ? ' · component ' + k.comp + ' level ' + k.lvl : ''} · family ${k.fam} · depth ${k.d}`, `${k.nf} fields · ${k.kids} subclasses`, `${k.lp} predicted (parent, field) pairs` + (k.xa + k.xr + k.xi ? `: XSD accepts ${k.xa}, rejects ${k.xr}, inconclusive ${k.xi}` : ''), k.new ? 'NEW in 4.1' : '', k.defn].filter(Boolean), g: 'C', src: 'data/explorer.json (X3D Ontology 4.1)' };
}
function show(name) {
  const i = info(name), t = $('tip'); t.innerHTML = `<h4>${esc(i.t)}<span class="g g${i.g}">${i.g}</span></h4>` + i.l.map(x => `<div class="mu" style="color:#c3cde0">${esc(x)}</div>`).join('') + `<div class="mu" style="margin-top:3px">Source: ${esc(i.src)}</div>`; t.style.display = 'block'; place();
}
function place() { const t = $('tip'); t.style.left = Math.min(innerWidth - 350, mx + 16) + 'px'; t.style.top = Math.min(innerHeight - t.offsetHeight - 12, my + 16) + 'px'; }
function wire() {
  const names = []; Object.keys(D.classes).forEach(c => names.push('T_' + c)); D.stations.forEach((_, k) => names.push('T_St_' + k));
  ['X3D', 'URDF', 'glTF'].forEach(d => D.beads[d].forEach((_, i) => names.push(`T_${d}_${i}`))); ['X3D', 'URDF', 'glTF'].forEach(d => [0, 1].forEach(j => names.push(`T_P_${d}_${j}`)));
  let n = 0; names.forEach(nm => { const s = nd(nm); if (!s) return; n++;
    s.getField('isOver').addFieldCallback('tip', v => { if (pin) return; if (v) { hover = nm; show(nm); } else if (hover === nm) { hover = null; $('tip').style.display = 'none'; } });
    s.getField('touchTime').addFieldCallback('pin', () => { pin = pin === nm ? null : nm; if (pin) show(nm); else $('tip').style.display = 'none'; }); });
  return n;
}
$('cv').addEventListener('mouseleave', () => { if (!pin) { hover = null; $('tip').style.display = 'none'; } });
document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; if ($('tip').style.display === 'block' && !pin) place(); });
document.addEventListener('mouseover', e => { const t = e.target.closest && e.target.closest('[data-tip]'); if (t) { const tp = $('tip'); tp.innerHTML = `<div style="color:#c3cde0">${esc(t.dataset.tip)}</div>`; tp.style.display = 'block'; place(); } });
document.addEventListener('mouseout', e => { const t = e.target.closest && e.target.closest('[data-tip]'); if (t && !hover) $('tip').style.display = 'none'; });
document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey) return; const k = e.key.toLowerCase();
  if (k === 'escape') { if (filmOn) skipFilm(); else if (tourI >= 0) closeTour(); else { pin = null; $('tip').style.display = 'none'; ['leg', 'help'].forEach(x => $(x).style.display = 'none'); } }
  else if (k === 'f') film(); else if (k === 't') tour(0); else if (k === 'a') assemble(); else if (k === 'd') disassemble(); else if (k === 'o') V('Orbit'); else if (k === 'm') sound(); else if (k === 'l') toggle('leg'); else if (k === 'h' || k === '?') toggle('help');
  else if (k === 'arrowright' && tourI >= 0) tour(tourI + 1); else if (k === 'arrowleft' && tourI > 0) tour(tourI - 1); else if (/^[1-9]$/.test(k)) tour(+k - 1);
});
window.addEventListener('beforeunload', () => {});
X3D(async () => {
  try {
    B = X3D.getBrowser($('cv')); D = await (await fetch('tour-data.json')).json();
    const ready = () => { const n = wire(); $('load').style.opacity = 0; setTimeout(() => $('load').style.display = 'none', 900); V('Row'); if (location.hash === '#film') { history.replaceState(null, '', location.pathname); setTimeout(startFilm, 600); } else if (location.hash === '#tour') { history.replaceState(null, '', location.pathname); setTimeout(() => tour(0), 600); } console.log('tooltips wired:', n); };
    let go = false; const tryReady = () => { if (go) return; try { if (nd('FilmClock')) { go = true; ready(); } } catch (e) {} }; B.addBrowserCallback('boot', X3D.X3DConstants.INITIALIZED_EVENT, () => setTimeout(tryReady, 400)); setTimeout(tryReady, 1500); setInterval(tryReady, 1500);
  } catch (e) { $('err').style.display = 'block'; $('err').textContent = 'Demo failed: ' + e; }
}, e => { $('err').style.display = 'block'; $('err').textContent = 'X_ITE failed: ' + e; });
