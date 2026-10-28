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
    (function step() {
      var k = D <= 0 ? 1 : Math.min(1, (performance.now() - t0) / D); k = k * k * k * (k * (6 * k - 15) + 10);          /* smootherstep */
      var p = [0, 1, 2].map(function (i) { return a[i] + (b[i] - a[i]) * k; }), t = [0, 1, 2].map(function (i) { return tgt0[i] + (tgt1[i] - tgt0[i]) * k; }), o = lookAt(p, t);
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
      d.innerHTML = '<i></i><b></b><small></small>'; $('b', d).textContent = a.label + (/^fan_/.test(a.id) ? (mock ? ' · mock' : ' · real path') : ''); $('small', d).textContent = '';
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
  var TOUR = { kind: 'keys', vp: 'TourCam', fov: 0.8, auto: false, keys: [        /* time, camera xyz, look-at xyz: Establishing, Face push-in, ribcage, tenders, fan reveal, back */
    [0, 12, -1.5, 25, 12, -1.5, 0], [9, -0.4, -0.3, 8.4, -0.8, 0.2, 0], [18, 3.0, -1.8, 13.2, 3.0, -1.8, 0],
    [28, 13.5, 1.8, 9.5, SUN[0], SUN[1], SUN[2]], [38, 2.0, 2.6, 9.0, SUN[0], SUN[1], SUN[2]], [46, SUN[0] + 1.6, SUN[1] + 4.6, SUN[2] + 2.8, SUN[0], SUN[1] + 2.9, SUN[2]],
    [56, 19.0, -1.0, 16.0, 21.0, -2.5, 0], [66, 12, -1.5, 25, 12, -1.5, 0]] };
  function tourLabel(on) { var b = $('#btn-tour'); if (b) { b.classList.toggle('on', on); b.textContent = on ? 'Pause tour' : 'Tour'; } }
  function tourToggle() {
    if (PX.tourOn || PX.tourHeld()) { PX.tourStop(); tourLabel(false); }
    else { PX.cfg = Object.assign(PX.cfg || {}, { tour: TOUR }); PX.tourStart(); Cam.fov = TOUR.fov; tourLabel(true); }
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
      PX.cfg = { tour: TOUR }; installSensor(el); hud(el); buildRail(); wire(el);
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
