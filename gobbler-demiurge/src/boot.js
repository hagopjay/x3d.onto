/* Gobbler demiurge, step 2: bird-first boot.
 *  1. an honest staged loader: every stage names itself, shows bytes and seconds, and a failure says what failed (no fixed "parsing" text)
 *  2. gzip delivery: the scene arrives as gobbler4-bird.x3d.gz (or base64 text for hosts that refuse binary) and is inflated here
 *  3. the bird alone first (scene about 0.2 MB gzipped); the graph, ontology block, anchors and receipt load after the first frame
 *  4. four controls (UI level, Face, Tour, zoom rail), anchor tags, flights, then the v4 hover layer on top
 * Config (window.GD_CFG, set by a published copy): bird, enc ('gz' | 'b64gz'), graph, graphEnc, onto, anchors, receipt.
 */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var q = new URLSearchParams(location.search);
  var CFG = Object.assign({ bird: 'data/bird/gobbler4-bird.x3d.gz', enc: 'gz', graph: 'data/bird/graph-v3.json.gz', graphEnc: 'gz', onto: '../gobbler-v4/data/onto-hover.json',
    anchors: 'data/bird/anchors.json', receipt: 'data/bird/receipt.json' }, window.GD_CFG || {});
  var REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var Boot = window.gdBoot = { log: [], stage: '', t0: performance.now(), ms: {}, bytes: {} };
  var busy = $('#busy'), stageEl = $('#stage');

  /* ---------- honest status line ---------- */
  var cur = null, beat = 0;
  function secs(t) { return ((performance.now() - t) / 1000).toFixed(1) + ' s'; }
  function kb(n) { return n >= 1e6 ? (n / 1e6).toFixed(2) + ' MB' : Math.round(n / 1e3) + ' KB'; }
  function show(text) { if (busy) { busy.hidden = false; busy.classList.remove('err'); busy.textContent = text; } }
  function stage(name, detail) {                 /* name the stage, keep the clock running on it */
    if (cur) Boot.ms[cur.name] = Math.round(performance.now() - cur.t);
    cur = { name: name, t: performance.now(), detail: detail || '' }; Boot.stage = name; stageEl.dataset.stage = name;
    Boot.log.push(secs(Boot.t0) + ' ' + name + (detail ? ' · ' + detail : '')); paint();
    if (!beat) beat = setInterval(paint, 500);
  }
  function paint() { if (cur && !Boot.done) show('Gobbler · ' + cur.name + (cur.detail ? ' · ' + cur.detail : '') + ' · ' + secs(cur.t)); }
  function fail(where, e) {
    clearInterval(beat); beat = 0; var msg = (e && e.message) || String(e);
    Boot.log.push('FAILED ' + where + ': ' + msg); Boot.failed = where + ': ' + msg; stageEl.dataset.stage = 'failed';
    if (busy) { busy.hidden = false; busy.classList.add('err'); busy.textContent = 'Gobbler could not load.\nStage: ' + where + '\n' + msg + '\nReload to try again.'; }
    console.error('[gobbler] ' + where, e);
  }

  /* ---------- fetch with progress, gzip inflate ---------- */
  function fetchBytes(url, label) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url);
      var total = +r.headers.get('content-length') || 0, rd = r.body && r.body.getReader && r.body.getReader();
      if (!rd) return r.arrayBuffer().then(function (b) { return new Uint8Array(b); });
      var parts = [], got = 0;
      return (function pump() {
        return rd.read().then(function (x) {
          if (x.done) { var out = new Uint8Array(got), o = 0; parts.forEach(function (p) { out.set(p, o); o += p.length; }); return out; }
          parts.push(x.value); got += x.value.length; if (cur) cur.detail = kb(got) + (total ? ' of ' + kb(total) : ''); return pump();
        });
      })();
    });
  }
  function inflate(u8) {
    if (typeof DecompressionStream === 'undefined') throw new Error('this browser has no DecompressionStream, cannot unzip');
    return new Response(new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
  }
  function fetchText(url, enc, label) {
    if (enc === 'b64gz') return fetch(url).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url); return r.text(); })
      .then(function (t) { var s = atob(t.replace(/\s+/g, '')), b = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); Boot.bytes[label] = b.length; return inflate(b); });
    if (enc === 'gz') return fetchBytes(url, label).then(function (b) { Boot.bytes[label] = b.length; if (cur) cur.detail = kb(b.length); return inflate(b); });
    return fetch(url).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url); return r.text(); });
  }

  /* ---------- canvas ---------- */
  function makeCanvas() {
    var el = document.createElement('x3d-canvas'), dpr = Math.min(window.devicePixelRatio || 1, 2);
    el.id = 'x3d'; el.setAttribute('splashScreen', 'false'); el.setAttribute('notifications', 'false'); el.setAttribute('contextMenu', 'false');
    el.setAttribute('update', 'auto'); el.setAttribute('contentScale', String(dpr)); el.setAttribute('multisampling', dpr >= 2 ? '4' : '8');
    el.setAttribute('toneMapping', 'KHR_PBR_NEUTRAL'); el.setAttribute('exposure', '1');
    stageEl.insertBefore(el, stageEl.firstChild); return el;
  }
  function frames(el, n) {                        /* resolve after n new rendered frames (X_ITE time advances per frame) */
    return new Promise(function (res) {
      var t0 = -1, seen = 0, start = performance.now();
      (function tick() {
        var t = -1; try { t = el.browser.getCurrentTime(); } catch (e) {}
        if (t !== t0) { t0 = t; seen++; }
        if (seen > n || performance.now() - start > 30000) return res(seen > n); requestAnimationFrame(tick);
      })();
    });
  }

  /* ---------- camera pose, flights, tags ---------- */
  var Cam = { pos: null, ori: null, fov: 0.72, ps: null };
  var SUN = [6.5, -2.6, 0.4];
  var STOPS = [                                   /* the zoom ladder: [name, label, pos, look, fov] ; null = comes with the village step */
    ['face', 'Face', [3.0, -1.8, 13.2], [3.0, -1.8, 0], 0.74],
    ['ribcage', 'Dyson ribcage', [SUN[0] + 5.2, SUN[1] + 2.2, SUN[2] + 8.2], SUN, 0.8],
    ['heart', 'Heart', [SUN[0] + 0.5, SUN[1] + 0.3, SUN[2] + 2.3], SUN, 0.8],
    null, null, null, null,
    ['feather', 'A feather', [10.5, 6.4, 8.6], [11.9, 4.6, 3.0], 0.8]
  ];
  var LATER = ['Earth and Moon', 'Village from orbit', 'Plaza', 'A villager'];
  var VIEWS = { face: 0, ribcage: 1, heart: 2, feather: 7, establishing: -1 };
  var ESTABLISH = ['establishing', 'Establishing', [12.0, -1.5, 25.0], [12.0, -1.5, 0], 0.88];
  var fly = { raf: 0, probe: null };
  function lookAt(p, t) { return PX.lookAt(p, t); }
  function orbit(o) {                             /* the point the camera looks at, at distance d, from the current pose */
    var R = rot(o.ori), d = Math.hypot(o.pos[0] - o.look[0], o.pos[1] - o.look[1], o.pos[2] - o.look[2]) || 10;
    return [o.pos[0] - R[2] * d, o.pos[1] - R[5] * d, o.pos[2] - R[8] * d];
  }
  function rot(a) { var x = a[0], y = a[1], z = a[2], an = a[3], l = Math.hypot(x, y, z) || 1; x /= l; y /= l; z /= l; var c = Math.cos(an), s = Math.sin(an), t = 1 - c;
    return [t * x * x + c, t * x * y - s * z, t * x * z + s * y, t * x * y + s * z, t * y * y + c, t * y * z - s * x, t * x * z - s * y, t * y * z + s * x, t * z * z + c]; }
  function flyTo(stop, ms, then) {
    var el = PX.el, sc = el.browser.currentScene, v;
    PX.tourStop(); tourLabel(false); cancelAnimationFrame(fly.raf);
    try { v = sc.getNamedNode('Probe'); } catch (e) { return; }
    var pos = Cam.pos ? Cam.pos.slice() : stop[2].slice(), ori = Cam.ori || [0, 0, 1, 0], a = pos, tgt0 = Cam.pos ? orbit({ pos: pos, ori: ori, look: stop[3] }) : stop[3].slice();
    var b = stop[2], tgt1 = stop[3], fov0 = Cam.fov, fov1 = stop[4], t0 = performance.now(), D = ms == null ? (REDUCED ? 0 : 2200) : ms;
    try { v.position = new X3D.SFVec3f(a[0], a[1], a[2]); v.orientation = new X3D.SFRotation(ori[0], ori[1], ori[2], ori[3]); v.fieldOfView = fov0; v.centerOfRotation = new X3D.SFVec3f(tgt1[0], tgt1[1], tgt1[2]); v.set_bind = true; } catch (e) {}
    var dv = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], dl = Math.hypot(dv[0], dv[1], dv[2]) || 1, pv = [dv[1] * 0 - dv[2] * 1, dv[2] * 0 - dv[0] * 0, dv[0] * 1 - dv[1] * 0];      /* the flight bows a little off the straight line (up cross direction), seeded */
    var pl = Math.hypot(pv[0], pv[1], pv[2]) || 1, bow = SEED && D > 0 ? (RND() - 0.5) * 0.34 * dl : 0;
    (function step() {
      var k = D <= 0 ? 1 : Math.min(1, (performance.now() - t0) / D); k = k * k * k * (k * (6 * k - 15) + 10);          /* smootherstep */
      var bk = bow * Math.sin(Math.PI * k);
      var p = [0, 1, 2].map(function (i) { return a[i] + (b[i] - a[i]) * k + bk * pv[i] / pl; }), t = [0, 1, 2].map(function (i) { return tgt0[i] + (tgt1[i] - tgt0[i]) * k; }), o = lookAt(p, t);
      try { v.position = new X3D.SFVec3f(p[0], p[1], p[2]); v.orientation = new X3D.SFRotation(o[0], o[1], o[2], o[3]); v.fieldOfView = Cam.fov = fov0 + (fov1 - fov0) * k; } catch (e) {}
      if (k < 1) fly.raf = requestAnimationFrame(step); else if (then) then();
    })();
  }
  function installSensor(el) {
    var sc = el.browser.currentScene, ps = sc.createNode('ProximitySensor'); ps.size = new X3D.SFVec3f(1e7, 1e7, 1e7); sc.addRootNode(ps);
    ps.addFieldCallback('gd', 'position_changed', function (v) { Cam.pos = [v.x, v.y, v.z]; tagsDirty = true; });
    ps.addFieldCallback('gd', 'orientation_changed', function (v) { Cam.ori = [v.x, v.y, v.z, v.angle]; tagsDirty = true; });
    Cam.ps = ps;
    try { Cam.fov = el.browser.activeViewpoint.fieldOfView || Cam.fov; } catch (e) {}
  }

  var tags = [], tagsDirty = true, level = 'min';
  function buildTags(anchors) {
    var host = $('#gd-tags'); host.innerHTML = '';
    var cols = { heart: '#ffe9a8', ribcage: '#d6b25c', flywheel: '#f2c35f', blender: '#f5851a', fan_gltf: '#40d9ff', fan_usd: '#ffeebb', fan_video: '#f24dd9', tenders: '#8cf0a8', wing: '#9ed7ff' };
    tags = anchors.map(function (a) {
      var mock = /mock/.test(a.tag), d = document.createElement('div'); d.className = 'gd-tag' + (mock ? ' mock' : ''); d.style.setProperty('--c', cols[a.id] || '#e9cf8a');
      d.innerHTML = '<i></i><b></b><small></small>'; $('b', d).textContent = a.label + (/^fan_/.test(a.id) ? (mock ? ' · mock' : ' · simulated') : ''); $('small', d).textContent = '';
      d.title = a.tag; host.appendChild(d); return { a: a, el: d, shown: false };
    });
  }
  function projectTags() {
    if (!Cam.pos || !Cam.ori || !tags.length) return;
    var W = stageEl.clientWidth, H = stageEl.clientHeight, R = rot(Cam.ori), f = (Math.min(W, H) / 2) / Math.tan(Cam.fov / 2), p = Cam.pos;
    tags.forEach(function (t) {
      var P = t.a.pos, dx = P[0] - p[0], dy = P[1] - p[1], dz = P[2] - p[2], cz = R[2] * dx + R[5] * dy + R[8] * dz, on = false;
      if (cz < -0.5 && level !== 'none') {
        var cx = R[0] * dx + R[3] * dy + R[6] * dz, cy = R[1] * dx + R[4] * dy + R[7] * dz, k = f / -cz, X = W / 2 + cx * k, Y = H / 2 - cy * k, dist = Math.hypot(dx, dy, dz);
        var near = t.a.level === 'full' ? dist < 15 : true;
        on = near && X > 30 && X < W - 30 && Y > 30 && Y < H - 30;
        if (on) t.el.style.transform = 'translate(' + Math.round(X + 10) + 'px,' + Math.round(Y - 6) + 'px)';
      }
      if (on !== t.shown) { t.shown = on; t.el.classList.toggle('on', on); }
    });
  }
  (function loop() { if (tagsDirty) { tagsDirty = false; projectTags(); } requestAnimationFrame(loop); })();
  setInterval(function () { try { var f = PX.el.browser.activeViewpoint.fieldOfView; if (f) Cam.fov = f; } catch (e) {} tagsDirty = true; }, 400);       /* the sway moves the layers a little even when the camera rests */

  /* ---------- the four controls ---------- */
  function buildRail() {
    var rail = $('#gd-rail'); rail.innerHTML = '';
    for (var i = 0; i < 8; i++) {
      (function (i) {
        var s = STOPS[i], b = document.createElement('button'); b.type = 'button';
        var label = s ? s[1] : LATER[i - 3], off = !s;
        b.className = off ? 'off' : ''; b.dataset.stop = i + 1; b.setAttribute('aria-label', (i + 1) + ' ' + label + (off ? ' (with the village step)' : ''));
        b.innerHTML = '<span>' + (i + 1) + ' · ' + label + (off ? ' · next step' : '') + '</span><i></i>';
        if (off) b.setAttribute('aria-disabled', 'true'); else b.addEventListener('click', function () { go(i); });
        rail.appendChild(b);
      })(i);
    }
  }
  var curStop = 0;
  function go(i, ms) {
    var s = i < 0 ? ESTABLISH : STOPS[i]; if (!s) return; curStop = i;
    [].forEach.call(document.querySelectorAll('#gd-rail button'), function (b) { b.classList.toggle('on', +b.dataset.stop === i + 1); });
    flyTo(s, ms);
  }
  /* ---------- the tour: the shot list on a spline (continuous velocity, no stop at every key), with seeded handheld drift ---------- */
  function rng32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  var SEED = q.get('seed') === null ? 4 : (+q.get('seed') || 0), RND = rng32(SEED * 7919 + 13);          /* ?seed=0 turns the drift and the bows off; the same seed repeats a take exactly */
  function orbitPos(az, r, el) { var a = az * Math.PI / 180, e = el * Math.PI / 180; return [SUN[0] + r * Math.sin(a) * Math.cos(e), SUN[1] + r * Math.sin(e), SUN[2] + r * Math.cos(a) * Math.cos(e)]; }
  var SHOTS = [                                   /* the shot list: seconds, name, camera, look-at, field of view. The village shots (dive, plaza) come with the village step */
    [0, 'Establishing', [12, -1.5, 25], [12, -1.5, 0], 0.88],
    [9, 'Face', [3.0, -1.8, 13.2], [3.0, -1.8, 0], 0.74],
    [17, 'Push-in', [-0.4, -0.3, 8.4], [-0.8, 0.2, 0], 0.72],
    [26, 'Orbit', orbitPos(-35, 11, 14), SUN, 0.8],
    [33, 'Orbit', orbitPos(-95, 12, 38), SUN, 0.8],
    [40, 'Orbit', orbitPos(-150, 12.5, 30), SUN, 0.8],
    [48, 'Tenders', [SUN[0] + 4.6, SUN[1] + 3.0, SUN[2] + 5.4], SUN, 0.82],
    [55, 'Heart', [SUN[0] + 0.9, SUN[1] + 0.8, SUN[2] + 3.4], SUN, 0.8],
    [64, 'Fan reveal', [19.0, -1.0, 16.0], [21.5, -2.5, 0], 0.9],
    [74, 'Return', [12, -1.5, 25], [12, -1.5, 0], 0.88]];
  var TOURK = SHOTS.map(function (s) { return { t: s[0], v: s[2].concat(s[3], [s[4]]) }; }), TOURD = TOURK[TOURK.length - 1].t, LEAD = 2.4;
  var DRIFT = [0, 1, 2, 3, 4, 5].map(function () { return { f: 0.05 + RND() * 0.11, g: 0.17 + RND() * 0.16, p: RND() * 6.283, q: RND() * 6.283 }; });
  function sampleTour(tau) {
    var K = TOURK, i = 0; while (i < K.length - 2 && tau > K[i + 1].t) i++;
    var a = K[i], b = K[i + 1], dt = b.t - a.t, u = Math.max(0, Math.min(1, (tau - a.t) / dt)), u2 = u * u, u3 = u2 * u;
    var h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
    return a.v.map(function (_, c) {
      var m0 = i === 0 ? 0 : (b.v[c] - K[i - 1].v[c]) / (b.t - K[i - 1].t), m1 = i + 1 === K.length - 1 ? 0 : (K[i + 2].v[c] - a.v[c]) / (K[i + 2].t - a.t);
      return h00 * a.v[c] + h10 * dt * m0 + h01 * b.v[c] + h11 * dt * m1;
    });
  }
  var tr = { on: false, held: false, t0: 0, heldAt: 0, raf: 0, vp: null, from: null };
  function trStep() {
    if (!tr.on) return;
    var t = (performance.now() - tr.t0) / 1000, v, k;
    if (t < LEAD) { k = t / LEAD; k = k * k * k * (k * (6 * k - 15) + 10); var s0 = sampleTour(0); v = s0.map(function (x, c) { return tr.from[c] + (x - tr.from[c]) * k; }); }
    else v = sampleTour((t - LEAD) % TOURD);
    if (SEED) {                                   /* slow seeded drift, a little different every take of a different seed; it grows with the distance to the subject */
      var dist = Math.hypot(v[0] - v[3], v[1] - v[4], v[2] - v[5]) / 12 + 0.25;
      for (var c = 0; c < 6; c++) { var d = DRIFT[c]; v[c] += (c < 3 ? 0.16 : 0.07) * dist * (Math.sin(6.283 * d.f * t + d.p) + 0.5 * Math.sin(6.283 * d.g * t + d.q)); }
      v[6] += 0.006 * Math.sin(6.283 * 0.07 * t + DRIFT[0].q);
    }
    var o = lookAt(v.slice(0, 3), v.slice(3, 6));
    try { tr.vp.position = new X3D.SFVec3f(v[0], v[1], v[2]); tr.vp.orientation = new X3D.SFRotation(o[0], o[1], o[2], o[3]); tr.vp.fieldOfView = Cam.fov = v[6]; } catch (e) {}
    tr.raf = requestAnimationFrame(trStep);
  }
  function trStart() {
    var sc = PX.el.browser.currentScene; try { tr.vp = sc.getNamedNode('TourCam'); } catch (e) { return; }
    cancelAnimationFrame(fly.raf); cancelAnimationFrame(tr.raf);
    var ori = Cam.ori || [0, 0, 1, 0], pos = Cam.pos ? Cam.pos.slice() : SHOTS[0][2].slice(), tg = Cam.pos ? orbit({ pos: pos, ori: ori, look: SHOTS[0][3] }) : SHOTS[0][3];
    tr.from = pos.concat(tg, [Cam.fov]);
    try { tr.vp.position = new X3D.SFVec3f(pos[0], pos[1], pos[2]); tr.vp.orientation = new X3D.SFRotation(ori[0], ori[1], ori[2], ori[3]); tr.vp.fieldOfView = Cam.fov; tr.vp.set_bind = true; } catch (e) {}
    PX.tourOn = tr.on = true; tr.held = false; tr.t0 = performance.now(); tr.raf = requestAnimationFrame(trStep);
  }
  function trStop() { PX.tourOn = tr.on = false; tr.held = false; cancelAnimationFrame(tr.raf); }
  function trHold() { if (!tr.on) return false; tr.heldAt = performance.now() - tr.t0; tr.held = true; PX.tourOn = tr.on = false; cancelAnimationFrame(tr.raf); return true; }
  function trRelease() { if (!tr.held) return false; tr.held = false; PX.tourOn = tr.on = true; tr.t0 = performance.now() - tr.heldAt; cancelAnimationFrame(tr.raf); tr.raf = requestAnimationFrame(trStep); return true; }
  function tourLabel(on) { var b = $('#btn-tour'); if (b) { b.classList.toggle('on', on); b.textContent = on ? 'Pause tour' : 'Tour'; } }
  function tourToggle() {
    if (PX.tourOn || PX.tourHeld()) { PX.tourStop(); tourLabel(false); }
    else { PX.tourStart(); tourLabel(true); }
  }

  /* ---------- fps ---------- */
  function hud(el) {
    var out = $('#hud'), frames = 0, last = performance.now(), lastT = -1;
    (function tick() {
      var t = -1; try { t = el.browser.getCurrentTime(); } catch (e) {} if (t !== lastT) { frames++; lastT = t; }
      var now = performance.now();
      if (now - last > 1500) { out.dataset.fps = (frames * 1000 / (now - last)).toFixed(0); out.textContent = out.dataset.fps + ' fps on this device' + (Boot.summary ? ' · ' + Boot.summary : ''); frames = 0; last = now; }
      requestAnimationFrame(tick);
    })();
  }

  /* ---------- go ---------- */
  function run() {
    var uiSaved = null; try { uiSaved = localStorage.getItem('gv4.ui'); } catch (e) {}
    level = q.get('ui') === 'none' ? 'none' : q.get('ui') === 'min' ? 'min' : (uiSaved === 'none' ? 'none' : 'min');
    $('#gv4').dataset.ui = level;
    stage('starting X_ITE');
    var el = PX.el = makeCanvas(), scene;
    var ready = el.browser ? Promise.resolve() : customElements.whenDefined('x3d-canvas').then(function () { return new Promise(function (r) { setTimeout(r, 0); }); });
    var textP;
    ready.then(function () {
      stage('fetching the bird', CFG.bird.split('/').pop());
      return fetchText(CFG.bird, CFG.enc, 'bird');
    }).then(function (xml) {
      Boot.bytes.birdRaw = xml.length; stage('parsing the scene', kb(xml.length) + ' of X3D');
      return el.browser.createX3DFromString(xml);
    }).then(function (scn) {
      stage('drawing the first frame');
      return el.browser.replaceWorld(scn);
    }).then(function () { return frames(el, 2); }).then(function (ok) {
      if (cur) Boot.ms[cur.name] = Math.round(performance.now() - cur.t);
      Boot.done = true; clearInterval(beat); beat = 0; busy.hidden = true; stageEl.dataset.stage = 'bird';
      Boot.birdMs = Math.round(performance.now() - Boot.t0); Boot.log.push(secs(Boot.t0) + ' bird on screen (' + kb(Boot.bytes.bird || 0) + ' gzipped scene)');
      Boot.summary = 'bird ' + (Boot.birdMs / 1000).toFixed(1) + ' s · ' + kb(Boot.bytes.bird || 0);
      installSensor(el); hud(el); buildRail(); wire(el);
      document.body.dataset.loaded = '1';
      var v = q.get('view'); if (v && v in VIEWS) go(VIEWS[v], 0);
      later(el);
    }).catch(function (e) { fail((cur && cur.name) || 'start', e); });
  }

  function later(el) {                           /* after the first frame: the graph, the ontology block, anchors, receipt */
    var t0 = performance.now(), saved = null;
    var graphP = fetchText(CFG.graph, CFG.graphEnc, 'graph').then(JSON.parse);
    var ontoP = fetch(CFG.onto).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    fetch(CFG.anchors).then(function (r) { return r.json(); }).then(buildTags).catch(function (e) { console.warn('anchors', e); });
    fetch(CFG.receipt).then(function (r) { return r.json(); }).then(function (r) { var v = r.validator || {}; if (v.xsd_valid) $('#gv4-valid').textContent = '✓ valid X3D 4.0 · ' + (v.label || 'fork validator'); }).catch(function () {});
    Promise.all([graphP, ontoP]).then(function (a) {
      var G = a[0]; Boot.graphMs = Math.round(performance.now() - t0); Boot.summary += ' · graph ' + kb(Boot.bytes.graph || 0) + ' after ' + (Boot.graphMs / 1000).toFixed(1) + ' s';
      $('#gv4-counts').textContent = 'bird first · ' + G.drawn.toLocaleString('en-US') + ' stars · ' + G.loops.length + ' loops';
      var hv = q.get('hover');
      window.gobbler = GobblerV4.start({ G: G, ONTO: a[1], el: el, stage: stageEl, root: $('#gv4'), level: level, hover: hv === null ? null : +hv, hoverTier: +q.get('tier') || 3, glass: q.get('glass') === '1', tune: q.get('tune') === '1' });
      document.body.dataset.v4 = '1';
    }).catch(function (e) { console.warn('[gobbler] graph', e); Boot.log.push('graph FAILED: ' + e.message); $('#gv4-counts').textContent = 'bird only · graph failed: ' + e.message; });
  }

  function wire(el) {
    PX.tourStart = trStart; PX.tourStop = trStop; PX.tourHold = trHold; PX.tourRelease = trRelease; PX.tourHeld = function () { return tr.held; };      /* the spline tour replaces the engine's; the hover layer holds and releases it the same way */
    var ts = PX.tourStop, tb = PX.tourStart;                    /* the engine writes 'Resume tour' on its own button; the page owns the label */
    PX.tourStop = function () { ts(); tourLabel(false); }; PX.tourStart = function () { tb(); tourLabel(true); };
    $('#gd-face').addEventListener('click', function () { go(0); });
    $('#btn-tour').addEventListener('click', tourToggle);
    el.addEventListener('pointerdown', function () { if (PX.tourOn || PX.tourHeld()) { PX.tourStop(); tourLabel(false); } });
    document.addEventListener('keydown', function (ev) {
      if (ev.metaKey || ev.ctrlKey || ev.altKey || (ev.target && /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName))) return;
      if (/^[1-8]$/.test(ev.key)) { go(+ev.key - 1); }
      else if (ev.key === 'F' && ev.shiftKey) { if (document.fullscreenElement) document.exitFullscreen(); else if (stageEl.requestFullscreen) stageEl.requestFullscreen(); }
        });
    window.addEventListener('keydown', function (ev) {      /* plan key rule: T = tour, Shift+T = the v4 tuning panel (the hover layer's own T handler never sees a plain t) */
      if (ev.key !== 't' || ev.shiftKey || ev.metaKey || ev.ctrlKey || ev.altKey || (ev.target && /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName))) return;
      ev.stopImmediatePropagation(); ev.preventDefault(); tourToggle();
    }, true);
    window.addEventListener('resize', function () { tagsDirty = true; });
    new MutationObserver(function () { level = $('#gv4').dataset.ui === 'none' ? 'none' : 'min'; tagsDirty = true; }).observe($('#gv4'), { attributes: true, attributeFilter: ['data-ui'] });   /* the hover layer owns U and the UI chip */
  }

  window.gdApi = { go: go, tour: tourToggle, cam: function () { return Cam; }, stops: STOPS, tags: function () { return tags; }, flyTo: flyTo };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
