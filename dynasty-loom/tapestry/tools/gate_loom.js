// NODE_PATH=/opt/node-tools/node_modules node tools/gate_loom.js [--no-frames] [--tag=NAME] [--frames-dir=DIR (under scene2/, default frames)] [--all-stops (a frame at every stop)]
// The live gate for the tapestry-loom page (scene2/out) in X_ITE 16.5.1, modelled on proto/x3d/tools/gate.js: local X_ITE (?local=1, the vendored copy,
// byte-identical to the npm tarball), Chromium from Playwright on SwiftShader, 1527 x 923 (the design viewport). It serves proto/ itself, records every
// console message and request, binds every stop of every family and MEASURES the labels from X_ITE's own Text.textBounds (through the Label PROTO's
// textBounds/origin outputs) projected with the bound viewpoint, clicks a thread with the real mouse, moves the fell, presses ladder keys, checks the page
// at phone width, shoots frames, runs lookgates.py on them, and writes scene2/gate.json plus an "xite_gate" block in out/receipt.json.
// Fix round 09: each stop also sets the fell to its own year and labels its subject; names without a leader must sit on their thread's row
// (the X_ITE text box within 48 px across and 14 px up or down of the generator's anchor); on the phone page every stop of the default family
// binds its own phone viewpoint and labels, which are measured the same way at 390 x 844 (text >= 12 px, no overlap, inside the phone safe area).
// Merge (tools/merge_views.py): the page now opens on the hypersphere view, so this gate asks for the loom by its hash (#loom); nothing else changed.
// v2: --artifact=DIR serves a release set the way the Artifact host does (the page inside a skeleton, .x3d as application/xml, X_ITE beside it) and
// writes tapestry/gate-artifact.json (frames anywhere, --frames-dir absolute). With the looks (dynastyApi.looks) it adds: the header's look switch in
// the loom view (html[data-look], the brand, ground, panels, ink and type change; the loom scene is not reloaded: its colours stay v3's), and back;
// at 1280x800, 1366x768, 1527x923 and 390x844, in both looks, the rail, caption and open card sit below the measured header with no sideways scroll.
// The phone UI may hide the rail when the caption carries previous and next.
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path'); const { execFileSync } = require('child_process');
const ARGV = process.argv.slice(2), FRAMES = !ARGV.includes('--no-frames'), TAG = (ARGV.find(a => a.startsWith('--tag=')) || '--tag=').slice(6), ALL_STOPS = ARGV.includes('--all-stops');
const ARTIFACT = (ARGV.find(a => a.startsWith('--artifact=')) || '').slice(11);
const SCENE2 = path.resolve(__dirname, '..'), ROOT = path.resolve(SCENE2, '..'), OUT = ARTIFACT ? path.resolve(ARTIFACT) : path.join(SCENE2, 'out'), REC = path.join(OUT, 'receipt.json');
const PAGE = ARTIFACT ? 'index.html#loom' : 'tapestry/out/index.html?local=1#loom', XITE_AT = ARTIFACT ? 'x_ite/' : 'x3d/vendor/x_ite/', SIZES = [[1280, 800], [1366, 768], [1527, 923], [390, 844]];
const FR = path.resolve(SCENE2, (ARGV.find(a => a.startsWith('--frames-dir=')) || '--frames-dir=frames').slice(13));
if (!ARTIFACT && !FR.startsWith(SCENE2 + path.sep)) throw new Error('--frames-dir must lie under tapestry/');
const W = 1527, H = 923;
const SHOTS = { rothschild: ['cloth', 'arrows', 'doubles', 'closeweave'], habsburg: ['cloth'], darwin_wedgwood: ['doubles'] };
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': ARTIFACT ? 'application/xml' : 'model/x3d+xml', '.webp': 'image/webp', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.png': 'image/png', '.svg': 'image/svg+xml', '.wasm': 'application/wasm' };
const SKELETON = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui,sans-serif}[hidden]{display:none!important}</style></head><body>', '</body></html>'];
const SRV_ROOT = ARTIFACT ? OUT : ROOT;
const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0].split('#')[0]); let p = path.join(SRV_ROOT, u); if (p.endsWith('/')) p += 'index.html';
  if (!p.startsWith(SRV_ROOT)) { r.writeHead(403); return r.end(); }
  if (u === '/favicon.ico') { r.writeHead(204); return r.end(); }
  fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } if (ARTIFACT && p === path.join(OUT, 'index.html')) d = Buffer.from(SKELETON[0] + d.toString('utf8') + SKELETON[1]);
    r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream', 'cache-control': 'no-store' }); r.end(d); }); });
let pass = 0, fail = 0; const checks = [];
const check = (name, ok, detail) => { ok ? pass++ : fail++; checks.push({ name, ok: !!ok, detail: detail === undefined ? '' : String(detail).slice(0, 600) }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? '  ' + String(detail).slice(0, 300) : '')); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
function rotm(a) { let [x, y, z, an] = a; const l = Math.hypot(x, y, z) || 1; x /= l; y /= l; z /= l; const c = Math.cos(an), s = Math.sin(an), t = 1 - c;
  return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y], [t * x * y + s * z, t * y * y + c, t * y * z - s * x], [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]; }
const mul = (R, v) => [0, 1, 2].map(i => R[i][0] * v[0] + R[i][1] * v[1] + R[i][2] * v[2]);
function project(p, vp, w = W, h = H) {   // X_ITE: fieldOfView spans the smaller side of the canvas
  const R = rotm(vp.orientation), d = [0, 1, 2].map(i => p[i] - vp.position[i]);
  const c = [0, 1, 2].map(j => R[0][j] * d[0] + R[1][j] * d[1] + R[2][j] * d[2]), depth = -c[2], f = 1 / Math.tan(vp.fov / 2), asp = w / h;
  const nx = asp >= 1 ? f * c[0] / (depth * asp) : f * c[0] / depth, ny = asp >= 1 ? f * c[1] / depth : f * c[1] * asp / depth;
  return { x: (nx + 1) / 2 * w, y: (1 - ny) / 2 * h, depth };
}
function boxOf(L, vp, w = W, h = H) {   // a label's drawn text box on screen: textBounds/origin in text units -> scale -> rotation -> translation -> projection
  const R = rotm(L.r), xs = [L.o[0], L.o[0] + L.tb[0]], ys = [L.o[1] - L.tb[1], L.o[1]], pts = [];
  for (const x of xs) for (const y of ys) { const q = mul(R, [x * L.sc[0], y * L.sc[1], 0]); pts.push(project([L.t[0] + q[0], L.t[1] + q[1], L.t[2] + q[2]], vp, w, h)); }
  const X = pts.map(q => q.x), Y = pts.map(q => q.y); return { x: Math.min(...X), y: Math.min(...Y), w: Math.max(...X) - Math.min(...X), h: Math.max(...Y) - Math.min(...Y) };
}
const offRow = (st, boxes) => st.labels.map((l, k) => [l, boxes[k]]).filter(([l, b]) => b && l.kind === 'name' && l.at && !l.leader)
  .map(([l, b]) => [l.text, Math.round(Math.max(b.x - l.at[0], 0, l.at[0] - (b.x + b.w))), Math.round(Math.max(b.y - l.at[1], 0, l.at[1] - (b.y + b.h)))]).filter(([, dx, dy]) => dx > 48 || dy > 14);
const MEASURE = (i, sw) => { const A = window.loomApi, sc = A.browser.currentScene, S = sc.getNamedNode(sw), g = S.children[i], st = A.cards.stops[i], vp = sc.getNamedNode(sw === 'LabelsPhone' ? st.phone.def_ : st.def_), out = [];
  for (let k = 0; k < g.children.length; k++) { const n = g.children[k], t = n.translation, r = n.rotation, s = n.scale, tb = n.textBounds, o = n.origin;
    out.push({ s: n.string[0], t: [t.x, t.y, t.z], r: [r.x, r.y, r.z, r.angle], sc: [s.x, s.y, s.z], tb: [tb.x, tb.y], o: [o.x, o.y, o.z] }); }
  const P = vp.position, O = vp.orientation;
  const MK = sc.getNamedNode('Marks');
  return { which: S.whichChoice, view: A.view, fell: A.fell, marks: MK ? MK.whichChoice : -1, bound: A.browser.activeViewpoint.description, boundIsStop: A.browser.activeViewpoint.getValue() === vp.getValue(),
    vp: { position: [P.x, P.y, P.z], orientation: [O.x, O.y, O.z, O.angle], fov: vp.fieldOfView }, labels: out }; };
const inter = (a, b) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));

(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: process.env.GEN_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); p.setDefaultTimeout(180000);
  const cons = [], errs = [], bad = [], reqs = [];
  p.on('console', m => cons.push({ type: m.type(), text: m.text().slice(0, 500) }));
  p.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 400)));
  p.on('request', r => reqs.push(r.url()));
  p.on('requestfailed', r => bad.push('requestfailed ' + r.url()));
  p.on('response', r => { if (r.status() >= 400) bad.push('HTTP ' + r.status() + ' ' + r.url()); });
  const loaded = () => p.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', null, { timeout: 240000 });
  const t0 = Date.now();
  await p.goto(BASE + PAGE, { waitUntil: 'load' }); await loaded();
  const bootMs = Date.now() - t0, failed = await p.evaluate(() => window.loomApi.failed || null);
  check('boot: the page loads the default family (rothschild) in X_ITE with no failure', !failed, failed || bootMs + ' ms to loaded (software GL, local server)');
  if (failed) { await finish(); return; }
  const eng = await p.evaluate(() => ({ name: window.loomApi.browser.name, version: window.loomApi.browser.version, fam: window.loomApi.family, xite: [...document.scripts].map(s => s.src).filter(Boolean) }));
  check('engine: X_ITE 16.5.1, the vendored copy' + (ARTIFACT ? ' shipped beside the page' : ' under ?local=1'), eng.version === '16.5.1' && eng.fam === 'rothschild' && eng.xite.some(s => s === BASE + XITE_AT + 'x_ite.min.js'), JSON.stringify(eng));
  const manifest = JSON.parse(fs.readFileSync(path.join(OUT, 'loom-manifest.json'), 'utf8')); const measured = {}; const frames = [];
  for (const fam of manifest.families) {
    if (fam.key !== 'rothschild') { await p.evaluate(k => window.loomApi.loadFamily(k, 0), fam.key); await sleep(300); await loaded(); }
    const C = JSON.parse(fs.readFileSync(path.join(OUT, fam.cards), 'utf8'));
    const live = await p.evaluate(defs => { const A = window.loomApi, sc = A.browser.currentScene; return { fam: A.family, missing: defs.filter(d => { try { return !sc.getNamedNode(d); } catch (e) { return true; } }),
      bound: A.browser.activeViewpoint ? A.browser.activeViewpoint.description : null, routes: sc.routes.length, protos: [...Array(sc.protos.length).keys()].map(i => sc.protos[i].name), labels: sc.getNamedNode('Labels').children.length }; }, C.stops.map(s => s.def_));
    check(fam.key + ': every stop is a Viewpoint (description = stop title), the first stop is bound at load, one label group per stop, no ROUTE',
      live.fam === fam.key && live.missing.length === 0 && live.bound === C.stops[0].title && live.labels === C.stops.length && live.routes === 0 && live.protos.includes('Label'), JSON.stringify(live));
    measured[fam.key] = [];
    for (let i = 0; i < C.stops.length; i++) {
      const st = C.stops[i];
      await p.evaluate(i => window.loomApi.bindStop(i), i); await sleep(2300);
      const m = await p.evaluate(new Function('a', 'return (' + MEASURE.toString() + ')(a[0], a[1])'), [i, 'Labels']);
      const boxes = m.labels.map(L => ({ s: L.s, ...boxOf(L, m.vp), drawn: L.tb[0] > 0 && L.tb[1] > 0 }));
      const kinds = st.labels.map(l => l.kind), names = kinds.filter(k => k === 'name').length;
      let overlaps = []; for (let a = 0; a < boxes.length; a++) for (let c = a + 1; c < boxes.length; c++) if (inter(boxes[a], boxes[c]) > 0) overlaps.push(boxes[a].s + ' / ' + boxes[c].s);
      const S = C.layout.safe_area, off = boxes.filter(x => x.x < 0 || x.y < 0 || x.x + x.w > W || x.y + x.h > H).map(x => x.s), unsafe = boxes.filter(x => x.x < S.x0 - 2 || x.y < S.y0 - 2 || x.x + x.w > S.x1 + 2 || x.y + x.h > S.y1 + 2).map(x => x.s);
      const undrawn = boxes.filter(x => !x.drawn).map(x => x.s), minH = Math.min(...boxes.map(x => x.h));
      const rows = offRow(st, boxes), subj = st.labels.filter(l => l.subject).map(l => l.text), drawnS = new Set(boxes.filter(x => x.drawn).map(x => x.s)), subjMissing = subj.filter(t => !drawnS.has(t));
      const rec = { family: fam.key, stop: st.n, title: st.title, bound: m.bound, labels: boxes.length, names, overlaps, offscreen: off, outside_safe_area: unsafe, undrawn, min_text_px: +minH.toFixed(1),
        fell: m.fell, subject_labels: subj, off_row: rows, boxes: boxes.map(x => [x.s, +x.x.toFixed(1), +x.y.toFixed(1), +x.w.toFixed(1), +x.h.toFixed(1)]) };
      measured[fam.key].push(rec);
      check(fam.key + ' stop ' + st.n + ' "' + st.title + '": bound, ' + boxes.length + ' labels (' + names + ' names <= 12), none overlapping, all drawn and inside the safe area, text >= 12 px; fell at ' + st.fell + ', subject labelled (' + subj.length + '), names on their rows',
        m.bound === st.title && m.boundIsStop && m.which === i && names <= 12 && overlaps.length === 0 && off.length === 0 && unsafe.length === 0 && undrawn.length === 0 && minH >= 12 &&
        m.fell === st.fell && m.marks === st.marks && subjMissing.length === 0 && subj.length === st.subject.filter(id => st.labels.some(l => l.ref === id && l.kind === 'name')).length && rows.length === 0,
        JSON.stringify({ overlaps: overlaps.slice(0, 4), offscreen: off.slice(0, 4), unsafe: unsafe.slice(0, 4), undrawn: undrawn.slice(0, 4), min_text_px: rec.min_text_px, fell: m.fell, subject_missing: subjMissing, off_row: rows.slice(0, 4) }));
      if (fam.key === 'rothschild' && st.key === 'doubles') await clickTest(p, C, i, m.vp, boxes);
      if (FRAMES && (ALL_STOPS || (SHOTS[fam.key] || []).includes(st.key))) frames.push(await shoot(p, fam.key + '-' + st.n + '-' + st.key));
    }
    if (fam.key === 'rothschild') {
      const f = await p.evaluate(() => { const A = window.loomApi, sc = A.browser.currentScene; A.setFell(1850); const c = sc.getNamedNode('FellClip').plane, g = sc.getNamedNode('GhostClip').plane, t = sc.getNamedNode('Fell').translation;
        const out = { fell: A.fell, clip: [c.x, c.y, c.z, c.w], ghost: [g.x, g.y, g.z, g.w], y: t.y, slider: document.getElementById('fellv').textContent }; A.setFell(A.cards.layout.top); return out; });
      const y = (1850 - C.layout.Y0) * C.layout.TY;
      check('fell: setting 1850 moves the plane and both clip planes (woven below, bare warp above)', Math.abs(f.y - y) < 1e-4 && Math.abs(f.clip[3] - (y + 0.05)) < 1e-4 && Math.abs(f.ghost[3] + (y + 0.05)) < 1e-4 && f.clip[1] === -1 && f.ghost[1] === 1 && f.slider === '1850', JSON.stringify(f));
      await p.keyboard.press('4'); await sleep(400);
      const k4 = await p.evaluate(() => window.loomApi.cards.stops[window.loomApi.stop].key);
      await p.keyboard.press('t'); await sleep(300); const tOn = await p.evaluate(() => document.getElementById('tour').textContent); await p.keyboard.press('t'); await sleep(200); const tOff = await p.evaluate(() => document.getElementById('tour').textContent);
      await p.keyboard.press('5'); await sleep(300); const toast = await p.evaluate(() => document.getElementById('toast').textContent);
      check('keys: 4 flies to the Five Arrows stop, T starts and stops the tour, 5 says the rung is not built', k4 === 'arrows' && /❚❚/.test(tOn) && /▸/.test(tOff) && /not built/.test(toast), JSON.stringify({ k4, tOn, tOff, toast }));
      await p.evaluate(() => window.loomApi.bindStop(0)); await sleep(1500);
    }
  }
  if (await p.evaluate(() => !!(window.dynastyApi && dynastyApi.looks))) await v2Looks(p);
  // ---- phone width: no horizontal scroll, the caption and rail stay on screen
  const ph = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true }); ph.setDefaultTimeout(180000);
  const pcons = []; ph.on('console', m => pcons.push({ type: m.type(), text: m.text().slice(0, 300) })); ph.on('pageerror', e => errs.push('phone pageerror ' + String(e).slice(0, 300)));
  ph.on('request', r => reqs.push(r.url()));
  await ph.goto(BASE + PAGE, { waitUntil: 'load' });
  await ph.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', null, { timeout: 240000 }); await sleep(2500);
  const pl = await ph.evaluate(() => { const r = id => { const e = document.getElementById(id).getBoundingClientRect(); return [Math.round(e.left), Math.round(e.top), Math.round(e.right), Math.round(e.bottom)]; };
    const A = window.loomApi, st = A.cards.stops[A.stop], c = A.view === 'phone' ? st.phone.camera : st.camera, need = 2 * Math.atan((c.frame_w / 2) / c.dist);
    const railShown = getComputedStyle(document.getElementById('rail')).display !== 'none', pn = !!document.getElementById('prev').offsetWidth && !!document.getElementById('next').offsetWidth;
    return { sw: document.documentElement.scrollWidth, iw: innerWidth, cap: r('cap'), rail: railShown ? r('rail') : null, prevNext: pn, view: A.view, fov: A.browser.activeViewpoint.fieldOfView, need }; }).catch(e => ({ error: String(e) }));
  check('phone (390 x 844): no horizontal page scroll; the caption strip and the stop rail (or, v2 phone UI, the caption\'s previous and next) sit inside the 16 px gutters; the stop\'s phone viewpoint is bound and its field of view spans its frame\'s width',
    pl.sw <= pl.iw && pl.cap[0] >= 16 && pl.cap[2] <= pl.iw - 16 && (pl.rail ? pl.rail[0] >= 16 && pl.rail[2] <= pl.iw - 16 : pl.prevNext) && pl.view === 'phone' && pl.fov >= pl.need - 1e-6, JSON.stringify(pl));
  const PC = JSON.parse(fs.readFileSync(path.join(OUT, manifest.families[0].cards), 'utf8')); measured.phone = [];
  for (let i = 0; i < PC.stops.length; i++) {
    const st = PC.stops[i], PS = st.phone.camera.safe_area;
    await ph.evaluate(i => window.loomApi.bindStop(i), i); await sleep(2300);
    const m = await ph.evaluate(new Function('a', 'return (' + MEASURE.toString() + ')(a[0], a[1])'), [i, 'LabelsPhone']);
    const boxes = m.labels.map(L => ({ s: L.s, ...boxOf(L, m.vp, 390, 844), drawn: L.tb[0] > 0 && L.tb[1] > 0 })), names = st.phone.labels.filter(l => l.kind === 'name').length;
    let overlaps = []; for (let a = 0; a < boxes.length; a++) for (let c = a + 1; c < boxes.length; c++) if (inter(boxes[a], boxes[c]) > 0) overlaps.push(boxes[a].s + ' / ' + boxes[c].s);
    const unsafe = boxes.filter(x => x.x < PS.x0 - 2 || x.y < PS.y0 - 2 || x.x + x.w > PS.x1 + 2 || x.y + x.h > PS.y1 + 2).map(x => x.s), undrawn = boxes.filter(x => !x.drawn).map(x => x.s), minH = Math.min(...boxes.map(x => x.h));
    measured.phone.push({ family: PC.family, stop: st.n, title: st.title, view: m.view, labels: boxes.length, names, overlaps, outside_safe_area: unsafe, undrawn, min_text_px: +minH.toFixed(1), fell: m.fell, boxes: boxes.map(x => [x.s, +x.x.toFixed(1), +x.y.toFixed(1), +x.w.toFixed(1), +x.h.toFixed(1)]) });
    check('phone ' + PC.family + ' stop ' + st.n + ' "' + st.title + '": its phone viewpoint and labels, ' + boxes.length + ' labels (' + names + ' names <= 6), none overlapping, all drawn and inside the phone safe area, text >= 12 px',
      m.view === 'phone' && m.boundIsStop && m.which === i && names <= 6 && overlaps.length === 0 && unsafe.length === 0 && undrawn.length === 0 && minH >= 12 && m.fell === st.fell,
      JSON.stringify({ overlaps: overlaps.slice(0, 4), unsafe: unsafe.slice(0, 4), undrawn: undrawn.slice(0, 4), min_text_px: +minH.toFixed(1), fell: m.fell }));
    if (FRAMES) frames.push(await shoot(ph, 'phone-' + PC.family + '-' + st.n + '-' + st.key, 390, 844));
  }
  cons.push(...pcons);
  // ---- the console and the network
  const xite = cons.filter(c => c.type === 'error' || c.type === 'warning' || /unknown|warning|error|could not|dropp/i.test(c.text));
  check('console: no errors or warnings (no unknown nodes or fields), no failed request', xite.length === 0 && errs.length === 0 && bad.length === 0, JSON.stringify(xite.concat(errs, bad).slice(0, 6)));
  const ext = [...new Set(reqs.filter(u => !u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:') && !/^https:\/\/fonts\.(googleapis|gstatic)\.com\//.test(u)))];   // v2: Google Fonts is the one font host
  const paths = [...new Set(reqs.filter(u => u.startsWith(BASE)).map(u => u.slice(BASE.length).split('?')[0]))].sort();
  check('network: no request leaves the page\'s own origin under ?local=1 (the CDN path is the only external one, and only without it)', ext.length === 0, JSON.stringify({ external: ext, fetched: paths }));
  await finish();

  async function clickTest(p, C, i, vp, boxes) {
    const st = C.stops[i], id = st.focus[1] || st.focus[0], P = C.people[id], Y = yr => (yr - C.layout.Y0) * C.layout.TY;
    let at = null;
    for (const pc of P.pieces) for (let yr = Math.max(pc[3] + 2, st.years[0] + 2); yr <= Math.min(pc[4] - 1, st.years[1] - 2) && !at; yr += 1) {
      const s = project([pc[1], Y(yr), pc[2]], vp); if (s.x < 30 || s.x > W - 120 || s.y < 90 || s.y > H - 220) continue;
      if (boxes.some(b => s.x >= b.x - 6 && s.x <= b.x + b.w + 6 && s.y >= b.y - 6 && s.y <= b.y + b.h + 6)) continue; at = { s, yr };
    }
    if (!at) { check('click: a free point on ' + P.name + '\'s thread', false, 'none found'); return; }
    await p.mouse.move(at.s.x + 1, at.s.y); await sleep(500); await p.mouse.move(at.s.x, at.s.y); await sleep(700);
    const hover = await p.evaluate(() => ({ hidden: document.getElementById('tag').hidden, text: document.getElementById('tag').textContent }));
    await p.mouse.click(at.s.x, at.s.y); await sleep(1200);
    const r = await p.evaluate(() => ({ picked: window.loomApi.picked, card: !document.getElementById('card').hidden, h2: (document.querySelector('#card h2') || {}).textContent || '',
      sel: window.loomApi.browser.currentScene.getNamedNode('SelLine').vertexCount.length }));
    check('click: the real mouse on ' + P.name + '\'s thread at ' + at.yr + ' (stop "' + st.title + '") shows the hover tag, picks her, opens her card and draws the highlight',
      !hover.hidden && hover.text.startsWith(P.label) && r.picked === id && r.card && r.h2.startsWith(P.name) && r.sel >= 1, JSON.stringify({ at: [Math.round(at.s.x), Math.round(at.s.y)], hover, r }));
    if (FRAMES) frames.push(await shoot(p, 'rothschild-' + st.n + '-' + st.key + '-pick'));
    await p.keyboard.press('Escape'); await sleep(500);
    const cl = await p.evaluate(() => ({ picked: window.loomApi.picked, card: !document.getElementById('card').hidden }));
    check('click: Esc clears the pick and closes the card', cl.picked === null && !cl.card, JSON.stringify(cl));
  }
  async function v2Looks(p) {   // v2: the look switch in the loom view, and the header against the rail, caption and card at four sizes in both looks
    const L = await p.evaluate(() => dynastyApi.looks), alt = L.order[1], def = L.default; measured.v2 = { looks: [], header: [] };
    await p.evaluate(() => window.loomApi.bindStop(0)); await sleep(1500);
    const chrome = () => p.evaluate(() => { const cs = q => getComputedStyle(document.querySelector(q)), A = window.loomApi; return { look: document.documentElement.dataset.look, bg: cs('body').backgroundColor, panel: cs('#cap').backgroundColor, ink: cs('#capt').color,
      font: cs('#capt').fontFamily, brand: document.getElementById('brand').textContent, btn: document.getElementById('look-t').textContent, pressed: document.getElementById('look-t').getAttribute('aria-pressed'), view: document.body.dataset.view,
      fam: A.family, stop: A.stop, bound: A.browser.activeViewpoint && A.browser.activeViewpoint.description, loaded: document.body.dataset.loaded, labels: A.browser.currentScene.getNamedNode('Labels').children.length }; });
    if (!alt) { check('look switch: an alternate look ships', false, JSON.stringify(L.order)); return; }
    const c0 = await chrome(), n0 = reqs.length;
    await p.click('#look-t'); await sleep(1500);
    const c1 = await chrome(), got = reqs.slice(n0).filter(u => /\.(x3d|json)$/.test(u.split('?')[0]));
    measured.v2.looks.push({ from: c0, to: c1, requests: got });
    check('look switch (loom view): the header button "' + c0.btn + '" turns on ' + alt + ' (html[data-look], aria-pressed, the brand, panels, ink and type); the loom scene stays loaded and bound, not refetched, on the same page ground (its colours stay v3\'s)',
      c0.look === def && c1.look === alt && c1.pressed === 'true' && c1.bg === c0.bg && c1.panel !== c0.panel && c1.font !== c0.font && c1.brand !== c0.brand && c1.view === 'loom' && c1.fam === c0.fam && c1.stop === c0.stop && c1.bound === c0.bound && c1.loaded === '1' && got.length === 0,
      JSON.stringify({ c0, c1, refetched: got }));
    if (FRAMES) frames.push(await shoot(p, 'loom-v2-' + alt + '-' + c1.fam + '-' + c1.stop));
    for (const look of [alt, def]) {
      if ((await p.evaluate(() => document.documentElement.dataset.look)) !== look) { await p.evaluate(l => dynastyApi.setLook(l, true), look); await sleep(600); }
      for (const [w, h] of SIZES) {
        await p.setViewportSize({ width: w, height: h }); await sleep(1600);
        await p.evaluate(() => { const A = window.loomApi, st = A.cards.stops[A.stop]; A.pick(st.focus[0]); }); await sleep(500);
        const m = await p.evaluate(() => { const R = q => { const e = document.querySelector(q); if (!e || e.hidden) return null; const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; const r = e.getBoundingClientRect(); return r.width && r.height ? [r.left, r.top, r.right, r.bottom].map(x => Math.round(x * 10) / 10) : null; };
          const hd = document.querySelector('header'), kids = [...hd.querySelectorAll('*')].filter(e => e.offsetWidth && getComputedStyle(e).display !== 'none').map(e => e.getBoundingClientRect());
          return { headerH: dynastyApi.headerH, cssVar: getComputedStyle(document.documentElement).getPropertyValue('--header-h').trim(), head: R('header'), kidsBottom: Math.max(...kids.map(k => k.bottom)), kidsRight: Math.max(...kids.map(k => k.right)), rail: R('#rail'), cap: R('#cap'), card: R('#card'), sw: document.documentElement.scrollWidth, iw: innerWidth, ih: innerHeight, picked: window.loomApi.picked }; });
        const hb = m.head[3], below = b => !b || b[1] >= hb - 0.5, ix = (a, b) => a && b && Math.min(a[2], b[2]) - Math.max(a[0], b[0]) > 0 && Math.min(a[3], b[3]) - Math.max(a[1], b[1]) > 0;
        const ok = below(m.rail) && below(m.cap) && below(m.card) && m.kidsBottom <= hb + 0.5 && m.kidsRight <= m.iw && m.sw <= m.iw && Math.abs(m.headerH - Math.ceil(hb)) <= 1 && !ix(m.rail, m.cap) && (!m.card || m.card[3] <= m.ih + 0.5);
        measured.v2.header.push(Object.assign({ look, view: 'loom', size: [w, h], ok }, m));
        if (w === W) {   // the chrome is legible on the loom's dark ground: WCAG contrast of each text against its composited background (the page ground under all)
          const cr = await p.evaluate(() => { const rgb = s => (s.match(/[\d.]+/g) || []).map(Number), over = (f, b) => { const a = f.length > 3 ? f[3] : 1; return [0, 1, 2].map(i => f[i] * a + b[i] * (1 - a)); };
            const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
            const bgOf = el => { const chain = []; for (let e = el; e; e = e.parentElement) chain.push(rgb(getComputedStyle(e).backgroundColor)); let bg = [255, 255, 255]; chain.reverse().forEach(c => { if (c.length) bg = over(c, bg); }); return bg; };
            const ratio = el => { const fg = over(rgb(getComputedStyle(el).color), bgOf(el)), bg = bgOf(el), a = lum(fg), b = lum(bg); return +((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)).toFixed(2); };
            const els = [['brand', document.getElementById('brand')], ['caption title', document.getElementById('capt')], ['look switch', document.getElementById('look-t')]]
              .concat([...document.querySelectorAll('#fams button')].map(e => ['family ' + e.textContent, e]), [...document.querySelectorAll('#views button')].map(e => ['view ' + e.textContent, e]), [...document.querySelectorAll('#rail button')].map(e => ['rail ' + e.textContent, e]));
            return els.filter(x => x[1] && x[1].offsetWidth).map(([k, e]) => [k, ratio(e)]); });
          const low = cr.filter(x => x[1] < 4.5);
          measured.v2.contrast = (measured.v2.contrast || []).concat([{ look, rows: cr }]);
          check('legible chrome (' + look + ', loom view): the brand, caption title, look switch, family, view and rail buttons have WCAG contrast >= 4.5 against their composited background', low.length === 0, JSON.stringify({ low, min: Math.min(...cr.map(x => x[1])) }));
        }
        check('header (' + look + ', loom view, ' + w + 'x' + h + '): the rail, caption and open card sit below the measured header (--header-h ' + m.cssVar + '), nothing in the header spills out of it, the rail and caption do not meet, no sideways scroll', ok, JSON.stringify(m));
        if (FRAMES && (w === 1280 || w === 1366)) frames.push(await shoot(p, 'loom-v2-header-' + look + '-' + w + 'x' + h, w, h));
        await p.keyboard.press('Escape'); await sleep(300);
      }
    }
    await p.setViewportSize({ width: W, height: H }); await sleep(1200);
    const c2 = await chrome();
    check('look switch back (loom view): ' + def + ' again with the same chrome as before', c2.look === def && c2.bg === c0.bg && c2.panel === c0.panel && c2.font === c0.font && c2.btn === c0.btn && c2.loaded === '1', JSON.stringify(c2));
  }
  async function shoot(pg, name, w = W, h = H) {
    fs.mkdirSync(FR, { recursive: true }); const file = path.join(FR, name + '.png'); let st = null;
    for (let k = 0; k < 4; k++) {
      const buf = await pg.screenshot({ path: file, type: 'png' });
      st = await pg.evaluate(async b64 => { const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
        const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0, lit = 0; for (let i = 0; i < d.length; i += 4) { const y = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]; s += y; if (y > 40) lit++; }
        return { mean: +(s / (d.length / 4)).toFixed(2), lit: +(lit / (d.length / 4)).toFixed(4) }; }, buf.toString('base64'));
      if (st.mean > 6 && st.lit > 0.004) break;
      console.log('retake', name, JSON.stringify(st)); await sleep(5000);
    }
    console.log('frame', name, JSON.stringify(st)); return { name, file: path.relative(SCENE2, file), ...st };
  }
  async function finish() {
    let look = null;
    if (FRAMES && frames.length) {
      try { const py = process.env.LOOM_GATE_PYTHON || 'python3', lg = path.join(ROOT, 'gates', 'lookgates.py');
        const txt = execFileSync(py, ['-I', lg, ...frames.map(f => path.join(SCENE2, f.file))], { encoding: 'utf8' });
        look = txt.trim().split('\n').map(l => ({ ok: l.startsWith('ok'), line: l.replace(SCENE2 + '/', '') }));
        check('lookgates.py nonblack: every frame is lit (p99 luma and lit share over the gate\'s thresholds)', look.every(x => x.ok), look.map(x => x.line).join(' | '));
      } catch (e) { check('lookgates.py ran', false, String(e).slice(0, 300)); }
    }
    const crypto = require('crypto'), H256 = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
    let tarCheck = null;                        // every X_ITE file the page pulled (vendored) must exist at the same path in the npm tarball, i.e. on the CDN
    try { const tgz = path.join(ROOT, 'x3d', 'vendor', 'x_ite-16.5.1.tgz'), entries = new Set(execFileSync('tar', ['tzf', tgz], { encoding: 'utf8' }).split('\n'));
      const pulled = [...new Set(reqs.filter(u => u.startsWith(BASE + XITE_AT)).map(u => u.slice((BASE + XITE_AT).length).split('?')[0]))].sort();
      tarCheck = { pulled, missing_in_tarball: pulled.filter(x => !entries.has('package/dist/' + x)) };
      check('cdn: each X_ITE file the page pulled (' + pulled.length + ') exists at package/dist/<same path> in the npm tarball, so the jsDelivr path serves it', tarCheck.missing_in_tarball.length === 0, JSON.stringify(tarCheck));
    } catch (e) { check('cdn: tarball listing', false, String(e).slice(0, 200)); }
    const out = { tag: TAG, when: new Date().toISOString(), served: ARTIFACT ? OUT : null, cdn_assets: tarCheck, engine: ARTIFACT ? 'X_ITE 16.5.1 (shipped beside the page)' : 'X_ITE 16.5.1 (vendored, ?local=1)', chromium: b.version(), playwright: require('playwright/package.json').version, gl: 'SwiftShader (ANGLE), software',
      viewport: [W, H], boot_ms: bootMs, pass, fail, checks, measured, frames, lookgates: look, console_all: cons, page_errors: errs, bad_requests: bad, requests: [...new Set(reqs)].length };
    fs.writeFileSync(path.join(SCENE2, ARTIFACT ? 'gate-artifact.json' : 'gate.json'), JSON.stringify(out, null, 1));
    if (!ARTIFACT) try { const rec = JSON.parse(fs.readFileSync(REC, 'utf8'));
      rec.xite_gate = { file: 'tapestry/gate.json', run: out.when, engine: out.engine, chromium: out.chromium, playwright: out.playwright, gl: out.gl, pass, fail,
        checks: checks.map(c => (c.ok ? 'PASS ' : 'FAIL ') + c.name), console_messages: cons.length, frames: frames.map(f => f.file) };
      rec.xite_gate.script_sha256 = H256(__filename); rec.xite_gate.cdn_assets = tarCheck;
      rec.lookgates = look; fs.writeFileSync(REC, JSON.stringify(rec, null, 1)); } catch (e) { console.log('receipt not updated', e); }
    if (frames.length) fs.writeFileSync(path.join(FR, ARTIFACT ? 'receipt-loom.json' : 'receipt.json'), JSON.stringify({ what: 'frames shot by tools/gate_loom.js at ' + (ALL_STOPS ? 'every tour stop of every family' : 'the tour stops'), tag: TAG, run: out.when, gate_script_sha256: H256(__filename),
      scene_inputs: Object.fromEntries(['rothschild.x3d', 'habsburg.x3d', 'darwin_wedgwood.x3d', 'rothschild.cards.json', 'habsburg.cards.json', 'darwin_wedgwood.cards.json', 'loom-manifest.json', 'index.html'].map(f => [f, H256(path.join(OUT, f))])),
      tools: { engine: out.engine, chromium: out.chromium, playwright: out.playwright, gl: out.gl, viewport: [W, H], lookgates: 'proto/gates/lookgates.py (venv-gate python)' },
      frames: Object.fromEntries(frames.map(f => [path.basename(f.file), H256(path.join(SCENE2, f.file))])), lookgates: look }, null, 1));
    console.log(pass + ' passed, ' + fail + ' failed; console messages: ' + cons.length);
    await b.close(); srv.close(); process.exit(fail ? 1 : 0);
  }
})().catch(e => { console.error(e); process.exit(2); });
