// NODE_PATH=/opt/node-tools/node_modules node tools/gate_hyper.js [--smoke] [--no-frames] [--families=rothschild,habsburg] [--frames-dir=frames/build-1]
//   [--artifact=DIR]: serve DIR (e.g. scene2/artifact, the two-view Dynasty Loom page, whose default view is this hypersphere) instead of out/;
//   the scene data is read from DIR too, results go to hyper/gate-artifact.json, and out/receipt.json is left alone.
// The live gate for the dynasty hypersphere (proto/hyper/out), modelled on scene2/tools/gate_loom.js and hyper/tools/drive_camera.js.
// X_ITE 16.5.1 (the copy shipped beside the page, byte-identical to the npm tarball), Chromium from Playwright on SwiftShader, 1527 x 923.
// It serves out/ the way the Artifact host does (the page fragment inside a document skeleton, .x3d as application/xml) and checks:
//   boot and engine; every shader compiled (ComposedShader.isValid); the Host shot bound at load; hash routing between families;
//   every tour stop of every family: the move is smooth (no speed spike, from the pose the pocket's ProximitySensor reports every frame) and lands
//   on its shot, the labels (an HTML overlay projected from the camera) do not overlap and stay inside the safe area, a frame;
//   every other shot of the camera grammar (Rothschild): bound or flown, smooth, landed, a frame; the plunge enters the pocket (ShellSense);
//   a real mouse click on a fiber (hover tag, card, highlight, a Present flight), Esc; the fell (uniforms, slider, keys) and its frame;
//   the quality tiers (uniforms, glow width, frame times) and the fps monitor; keys; phone width (390 x 844); a clean console; lookgates on every frame.
//   build 2: on every close stop the selection (uPick, uLine = the generator's lineage, uFocus eased to 1) and the subject bead (BeadSwitch on,
//   BeadXf at the stop's bead); on wider stops none; the camera's orientation on every Probe landing (the page's pose guard); the Inside
//   lookgate on every Inside frame (tools/scene_stats.py --inside: scene area mean <= 0.22, lit <= 0.70, clipped white <= 0.3 percent).
//   build 3: on every close stop no thread cuts a dark notch (the rest has no opaque core): an A/B with the clocks frozen, the frame as drawn
//   against the same frame with every thread hidden (FiberCore uFell far below the seed, GlowSwitch off); the share of scene pixels the threads
//   make darker by more than 0.05 luma AND leave under 0.15 luma must stay <= 0.0001 (tools/scene_stats.py --ab; build 2 measured 0.0041 and
//   0.00076 on S02 and S05); the bead projects inside the safe area (desktop); neighbouring close shots of one kind never share a composition.
// Writes hyper/gate.json and <frames-dir>/receipt.json, and adds an "xite_gate" block to out/receipt.json.
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const { execFileSync } = require('child_process');
const ARGV = process.argv.slice(2), SMOKE = ARGV.includes('--smoke'), FRAMES = !ARGV.includes('--no-frames');
const ARTIFACT = (ARGV.find(a => a.startsWith('--artifact=')) || '').slice(11);
const HYPER = path.resolve(__dirname, '..'), ROOT = path.resolve(HYPER, '..'), OUT = ARTIFACT ? path.resolve(ARTIFACT) : path.join(HYPER, 'out'), REC = path.join(HYPER, 'out', 'receipt.json');
const FR = path.resolve(HYPER, (ARGV.find(a => a.startsWith('--frames-dir=')) || '--frames-dir=frames/build-3').slice(13));
const MOTION_TIER = (ARGV.find(a => a.startsWith('--tier=')) || '--tier=fast').slice(7);   // the tier the moves run at (SwiftShader is slow); frames are shot at Ultra
const SLOWMO = +((ARGV.find(a => a.startsWith('--slowmo=')) || '--slowmo=2').slice(9));   // Probe flights run this many times slower, so SwiftShader samples them densely (the path is a function of normalised time)
const ONLYF = (ARGV.find(a => a.startsWith('--families=')) || '').slice(11).split(',').filter(Boolean);
const W = 1527, H = 923;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': 'application/xml', '.png': 'image/png', '.ttf': 'font/ttf', '.wasm': 'application/wasm', '.txt': 'text/plain', '.md': 'text/markdown', '.svg': 'image/svg+xml' };
const SKELETON = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
  '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui,sans-serif}[hidden]{display:none!important}</style></head><body>', '</body></html>'];
const srv = http.createServer((q, r) => {
  const u = decodeURIComponent(new URL(q.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html', f = path.join(OUT, u);
  if (u === 'favicon.ico') { r.writeHead(204); return r.end(); }   // the Artifact host gives the page its own icon
  if (!f.startsWith(OUT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  let d = fs.readFileSync(f); if (u === 'index.html') d = Buffer.from(SKELETON[0] + SKELETON[1] + d.toString('utf8') + SKELETON[2]);
  r.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); r.end(d);
});
let pass = 0, fail = 0; const checks = [], metrics = { moves: [], stops: [], tiers: {}, labels: [] }, frames = [];
const check = (name, ok, detail) => { ok ? pass++ : fail++; const d = detail === undefined ? '' : (typeof detail === 'string' ? detail : JSON.stringify(detail));
  checks.push({ name, ok: !!ok, detail: d.slice(0, 1200) }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (d ? '  ' + d.slice(0, 420) : '')); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const H256 = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');

// ---------------------------------------------------------------- maths (pocket units), the motion analysis of drive_camera.js
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], len = a => Math.hypot(a[0], a[1], a[2]);
const qang = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]))) * 180 / Math.PI;
const median = a => { const b = a.slice().sort((x, y) => x - y); return b.length ? b[Math.floor(b.length / 2)] : null; };
function analyse(S0, endPos) {
  // SwiftShader frames come unevenly (50 ms after 600 ms): a pose sampled a moment after the last one gives the instantaneous speed while its
  // neighbours average over long frames, which near a speed peak reads as a false 2.5x spike. Fold any sample closer than half the median frame to
  // the one before into the next interval (a real jump still shows: the displacement is kept, only the clock window widens).
  const raw = []; for (let i = 1; i < S0.length; i++) raw.push(S0[i].tc - S0[i - 1].tc);
  const md = median(raw) || 0, S = S0.length < 4 ? S0 : S0.filter((x, i) => i === 0 || i === S0.length - 1 || x.tc - S0[i - 1].tc >= 0.5 * md);
  if (S.length < 3) return { n: S.length, jumps: 0, few: true, end_pos_err: S.length && endPos ? +len(sub(S[S.length - 1].p, endPos)).toFixed(4) : null };
  const steps = [], vs = [], angs = [], dts = []; let L = 0;
  for (let i = 1; i < S.length; i++) { const l = len(sub(S[i].p, S[i - 1].p)), dt = Math.max(1, S[i].tc - S[i - 1].tc); steps.push(l); dts.push(dt); vs.push(l / dt * 1000); angs.push(qang(S[i].q, S[i - 1].q)); L += l; }
  const T = Math.max(1e-3, (S[S.length - 1].tc - S[0].tc) / 1000), vmax = Math.max(...vs), angTot = angs.reduce((a, b) => a + b, 0), ws = angs.map((a, i) => a / dts[i] * 1000), wmax = Math.max(...ws);
  const spike = (v, vm) => v.filter((x, i) => i > 0 && i < v.length - 1 && x > 0.5 * vm && x > 2.5 * Math.max(v[i - 1], v[i + 1], 1e-9)).length;   // a jump: > 2.5x both neighbours and > half the peak
  const r = { n: S.length, n_raw: S0.length, seconds: +T.toFixed(2), path: +L.toFixed(4), turn_deg: +angTot.toFixed(1), speed_ratio: +(vmax / Math.max(1e-9, L / T)).toFixed(2), ang_speed_ratio: +(wmax / Math.max(1e-9, angTot / T)).toFixed(2),
    first_step_share: +(steps[0] / Math.max(1e-9, L)).toFixed(3), jumps: spike(vs, vmax) + spike(ws, wmax), median_frame_ms: Math.round(median(dts)), max_frame_ms: Math.round(Math.max(...dts)) };
  if (endPos) r.end_pos_err = +len(sub(S[S.length - 1].p, endPos)).toFixed(4);
  return r;
}
function segDist(p, a, b) { const ab = sub(b, a), l2 = dot(ab, ab), t = l2 > 0 ? Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2)) : 0; return len(sub(p, [a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t])); }
// A Probe flight is judged on its commanded poses (one per page frame, a pure function of the frame clock, so SwiftShader's uneven frames cannot fake a
// spike) and on tracking: every pose the pocket's ProximitySensor reports must lie on the commanded path, and the last one on the shot.
// A native bind (X_ITE's own ANIMATE transition) has no commands and is judged on the sensed poses.
function motion(rec, endPos) {
  const C = rec.cmds || [], S = rec.samples, sensed = analyse(S, endPos);
  if (C.length < 3) return Object.assign({ basis: 'sensed' }, sensed);
  const a = analyse(C, null); let trk = 0;
  for (const x of S.filter(x => x.tc >= C[0].tc)) { let best = Infinity; for (let i = 1; i < C.length; i++) best = Math.min(best, segDist(x.p, C[i - 1].p, C[i].p)); trk = Math.max(trk, best); }
  return Object.assign(a, { basis: 'commanded', sensed_n: S.length, sensed_spikes: sensed.jumps, tracking_max: +trk.toFixed(5), end_pos_err: sensed.end_pos_err });
}
const smooth = a => (a.tracking_max == null || a.tracking_max < 2e-3) && (a.few || (a.jumps === 0 && a.speed_ratio < 6 && (a.turn_deg < 3 || a.ang_speed_ratio < 6)));

(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: process.env.GEN_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); p.setDefaultTimeout(240000);
  const cons = [], errs = [], bad = [], reqs = [];
  const hook = (pg, tag) => { pg.on('console', m => cons.push({ page: tag, type: m.type(), text: m.text().slice(0, 600) })); pg.on('pageerror', e => errs.push(tag + ' pageerror ' + String(e).slice(0, 400)));
    pg.on('request', r => reqs.push(r.url())); pg.on('requestfailed', r => bad.push('requestfailed ' + r.url())); pg.on('response', r => { if (r.status() >= 400) bad.push('HTTP ' + r.status() + ' ' + r.url()); }); };
  hook(p, 'desktop');
  const loaded = pg => pg.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', null, { timeout: 240000 });
  const t0 = Date.now();
  await p.goto(BASE + 'index.html?auto=0&idle=0&tier=' + MOTION_TIER, { waitUntil: 'load' }); await loaded(p);
  const bootMs = Date.now() - t0, failed = await p.evaluate(() => window.hyperApi.failed || null);
  await p.evaluate(k => { window.hyperApi.slowmo = k; }, SLOWMO);
  check('boot: the page loads the default family in X_ITE with no failure', !failed, failed || bootMs + ' ms to loaded (SwiftShader, local server)');
  if (failed) return finish();
  const eng = await p.evaluate(() => ({ name: hyperApi.browser.name, version: hyperApi.browser.version, fam: hyperApi.family, xite: hyperApi.xite, hash: location.hash }));
  check('engine: X_ITE 16.5.1, the copy shipped beside the page (same origin)', eng.version === '16.5.1' && eng.xite === BASE + 'x_ite/x_ite.min.js' && eng.hash === '#rothschild', eng);
  const manifest = JSON.parse(fs.readFileSync(path.join(OUT, 'hyper-manifest.json'), 'utf8'));
  const fams = manifest.families.filter(f => !ONLYF.length || ONLYF.includes(f.key));
  for (const [fi, fam] of fams.entries()) {
    if (fi > 0 || fam.key !== 'rothschild') {
      await p.evaluate(k => { location.hash = '#' + k.replace(/_/g, '-'); }, fam.key);
      await p.waitForFunction(k => hyperApi.family === k && document.body.dataset.loaded === '1', fam.key, { timeout: 240000 });
    }
    const D = JSON.parse(fs.readFileSync(path.join(OUT, fam.data), 'utf8'));
    await sleep(1500);
    const st0 = await p.evaluate(() => ({ fam: hyperApi.family, hash: location.hash, bound: hyperApi.pose().bound, shaders: hyperApi.shaders(), tier: hyperApi.tier, scale: document.getElementById('scale').textContent,
      sub: document.getElementById('sub').textContent, has: hyperApi.has }));
    check(fam.key + ': loaded through the #hash, the Host shot bound at load, every ComposedShader compiled (isValid), the radial scale stated on screen',
      st0.fam === fam.key && st0.hash === '#' + fam.key.replace(/_/g, '-') && /^Opening/.test(st0.bound || '') && st0.shaders.length === 8 && st0.shaders.every(s => s.isValid === true) &&
      st0.scale.includes(D.units.Y0 + ' at the seed') && st0.scale.includes('years per pocket unit'), st0);
    if (FRAMES) frames.push(await shoot(p, fam.key + '-S00-Host'));
    if (SMOKE && fi > 0) continue;
    // ---- the tour, stop by stop
    for (let i = 1; i < D.tour.length; i++) {
      const t = D.tour[i], s = D.shots[t.shot], k = s.space === 'host' ? 1 / D.pocket_scale : 1, endPos = s.pos.map(x => x * k);
      await p.evaluate(() => hyperApi.recStart());
      const ok = await p.evaluate(i => hyperApi.goStop(i), i);
      await settle(p, endPos);
      await p.waitForFunction(n => hyperApi.pose().nav === n, s.nav, { timeout: 15000 }).catch(() => {});   // the page switches NavigationInfo three frames after arrival
      const rec = await p.evaluate(() => hyperApi.recStop()), pose = await p.evaluate(() => hyperApi.pose());
      const a = motion(rec, endPos), marks = rec.marks.map(m => m.label);
      const entered = t.move === 'plunge' ? marks.includes('enter pocket') || pose.inside : true;
      const navOk = s.nav === 'FLY' ? pose.nav === 'FLY' : pose.nav === 'EXAMINE';
      metrics.moves.push(Object.assign({ family: fam.key, stop: i, shot: t.shot, size: s.size, move: t.move, planned_s: t.dur_s }, a));
      check(fam.key + ' stop ' + (i + 1) + ' ' + t.key + ' -> ' + t.shot + ' (' + s.size + ', ' + t.move + '): arrives, smooth (no speed spike, peak/mean < 6), lands on the shot (< 0.002 pocket units)' + (t.move === 'plunge' ? ', enters the pocket, FLY bound' : ''),
        ok === true && smooth(a) && a.end_pos_err < 2e-3 && entered && navOk, Object.assign({ entered, nav: pose.nav, marks: marks.slice(-4) }, a));
      await stopChecks(p, D, fam.key, i, W, H);
      if (SMOKE && i >= 2) break;
    }
    if (!SMOKE) {   // build 3: the close shots are not one template
      const cl = D.tour.map(t => D.shots[t.shot]).filter(s => s.size === 'CU' || s.size === 'MCU'), rep = [];
      ['Present', 'EyeToEye'].forEach(kd => { const xs = cl.filter(s => s.name.endsWith(kd)); for (let j = 1; j < xs.length; j++) if (xs[j].composition === xs[j - 1].composition) rep.push(xs[j - 1].name + '/' + xs[j].name); });
      const kinds = [...new Set(cl.map(s => s.composition))];
      check(fam.key + ' close shots: compositions ' + cl.map(s => s.name.slice(0, 3) + s.composition).join(', ') + '; no two neighbouring shots of one kind share a framing', rep.length === 0 && (cl.length < 2 || kinds.length > 1), { repeats: rep, kinds });
    }
    if (fam.key === 'rothschild' && !SMOKE) await rothschildExtras(p, D);
  }
  await phone();
  // ---- console and network
  const noisy = cons.filter(c => c.type === 'error' || c.type === 'warning' || /unknown|error|could not|fail|invalid|compile|link/i.test(c.text));
  check('console: no errors or warnings (no shader compile or link error, no unknown node or field), no page error, no failed request', noisy.length === 0 && errs.length === 0 && bad.length === 0, noisy.concat(errs, bad).slice(0, 8));
  const ext = [...new Set(reqs.filter(u => !u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')))];
  check('network: every request stays on the page\'s own origin', ext.length === 0, { external: ext });
  return finish();

  // ---------------------------------------------------------------- helpers
  async function stopChecks(pg, D, fam, i, w, h) {
    const t = D.tour[i], s = D.shots[t.shot];
    await sleep(400);
    const L = await pg.evaluate(() => ({ boxes: hyperApi.labelBoxes(), safe: hyperApi.safeRect(), fell: hyperApi.fell, cap: document.getElementById('capt').textContent, chip: document.getElementById('shotchip').textContent,
      narr: document.getElementById('narr').innerHTML.length, grades: document.querySelectorAll('#narr .g, #comp .g').length }));
    const B = L.boxes, ov = [];
    for (let a = 0; a < B.length; a++) for (let c = a + 1; c < B.length; c++) { const ix = Math.min(B[a].x + B[a].w, B[c].x + B[c].w) - Math.max(B[a].x, B[c].x), iy = Math.min(B[a].y + B[a].h, B[c].y + B[c].h) - Math.max(B[a].y, B[c].y); if (ix > 0 && iy > 0) ov.push(B[a].text + ' / ' + B[c].text); }
    const S = L.safe, unsafe = B.filter(x => x.x < S.x0 - 1 || x.y < S.y0 - 1 || x.x + x.w > S.x1 + 1 || x.y + x.h > S.y1 + 1).map(x => x.text), small = B.filter(x => x.h < 12).map(x => x.text);
    const subj = (D.stop_labels[t.shot] || []).filter(l => l.kind === 'subject').map(l => l.text), drawnSubj = subj.filter(x => B.some(b => b.text === x));
    const close = s.size === 'CU' || s.size === 'MCU';
    // build 2: the selection and the bead, written on arrival and eased in; the camera's orientation (the pose guard clears stray X_ITE offsets)
    await pg.waitForFunction(() => !hyperApi.focusBusy(), null, { timeout: 20000 }).catch(() => {});
    if (s.space !== 'host') await pg.waitForFunction(() => hyperApi.poseGuard.errDeg !== null && hyperApi.poseGuard.errDeg < 1, null, { timeout: 20000, polling: 200 }).catch(() => {});
    const SEL = await pg.evaluate(() => { const g = n => hyperApi.browser.currentScene.getImportedNode(n), t = g('BeadXf').translation, L = g('FiberCore').uLine;
      return { pick: g('FiberCore').uPick, pickGlow: g('FiberGlow').uPick, line: Array.from({ length: L.length }, (_, k) => L[k]).filter(x => x > -0.5), focus: g('FiberCore').uFocus,
        bead: g('BeadSwitch').whichChoice, beadAt: [t.x, t.y, t.z], ring: g('BeadGlow').uRing, guard: Object.assign({}, hyperApi.poseGuard) }; });
    const subjI = close && s.subject && D.people[s.subject] ? D.people[s.subject].i : -1;
    const selOk = close ? SEL.pick === subjI && SEL.pickGlow === subjI && JSON.stringify(SEL.line) === JSON.stringify(t.line) && Math.abs(SEL.focus - 1) < 1e-6 && SEL.bead === 0 &&
      Math.hypot(...SEL.beadAt.map((x, k) => x - s.bead.pos[k])) < 1e-4 && (SEL.ring > 0) === !!s.bead.ring : SEL.pick === -1 && SEL.bead === -1;
    const orientOk = s.space === 'host' || (SEL.guard.errDeg !== null && SEL.guard.errDeg < 1);
    metrics.selection = metrics.selection || []; metrics.selection.push({ family: fam, stop: i + 1, shot: t.shot, size: s.size, pick: SEL.pick, line_n: SEL.line.length, bead: SEL.bead, ring: SEL.ring, orient_err_deg: SEL.guard.errDeg, guard_cleared: SEL.guard.cleared });
    check(fam + (w < 600 ? ' phone' : '') + ' stop ' + (i + 1) + ' selection: ' + (close ? 'the subject lit (uPick), its lineage (' + (t.line || []).length + ' people, uLine), eased in (uFocus 1), the bead on (' + (s.bead && s.bead.ring ? 'ringed marriage' : 'point') + ') at the stop\'s event' : 'nothing selected, no bead') + '; camera orientation on the shot (< 1 deg)',
      selOk && orientOk, { pick: SEL.pick, want: subjI, line: SEL.line.length, focus: SEL.focus, bead: SEL.bead, ring: SEL.ring, orient_err_deg: SEL.guard.errDeg, guard_cleared: SEL.guard.cleared });
    const fellOk = t.fell == null || Math.abs(L.fell - Math.max(D.units.Y0, Math.min(D.units.top, t.fell))) < 0.6;
    const rec = { family: fam, stop: i + 1, shot: t.shot, size: s.size, labels: B.length, overlaps: ov, outside_safe: unsafe, small, subjects: subj, subjects_drawn: drawnSubj, fell: L.fell, grades: L.grades, viewport: [w, h],
      boxes: B.map(x => [x.text, Math.round(x.x), Math.round(x.y), Math.round(x.w), Math.round(x.h)]) };
    metrics.labels.push(rec);
    check(fam + (w < 600 ? ' phone' : '') + ' stop ' + (i + 1) + ' labels: ' + B.length + ' drawn, none overlapping, all inside the safe area, text >= 12 px' + (close ? ', the subject labelled' : '') + '; caption with graded lines; fell ' + (t.fell == null ? 'top' : t.fell),
      ov.length === 0 && unsafe.length === 0 && small.length === 0 && (!close || !subj.length || drawnSubj.length > 0) && L.cap.length > 0 && L.narr > 0 && fellOk,
      { overlaps: ov.slice(0, 3), unsafe: unsafe.slice(0, 3), small, subjects: subj, drawn: drawnSubj, fell: L.fell, cap: L.cap, chip: L.chip, grades: L.grades });
    const fname = (w < 600 ? 'phone-' : '') + fam + '-S' + String(i).padStart(2, '0') + '-' + t.shot.replace(/^S\d\d_/, '');
    if (FRAMES) frames.push(await shoot(pg, fname, w, h, w < 600 ? null : 2));
    if (close && s.bead) {   // build 3: the bead on screen, inside the safe area
      const bp = await pg.evaluate(b => { const q = hyperApi.project(b), S = hyperApi.safeRect(); return { q, S }; }, s.bead.pos);
      const inB = bp.q && bp.q.x >= bp.S.x0 && bp.q.x <= bp.S.x1 && bp.q.y >= bp.S.y0 && bp.q.y <= bp.S.y1;
      check(fam + (w < 600 ? ' phone' : '') + ' stop ' + (i + 1) + ' bead: projects inside the safe area (' + (s.composition || '') + ')', w < 600 || inB,
        { at: bp.q && [Math.round(bp.q.x), Math.round(bp.q.y)], safe: [bp.S.x0, bp.S.y0, bp.S.x1, bp.S.y1].map(Math.round), phone_reported_only: w < 600 });
    }
    if (close && FRAMES) await threadsAddLight(pg, fname, fam + (w < 600 ? ' phone' : '') + ' stop ' + (i + 1));
  }

  async function threadsAddLight(pg, name, label) {   // build 3, critique rank 1: A/B with the clocks frozen; threads may only add light
    const dir = path.join(FR, 'ab'); fs.mkdirSync(dir, { recursive: true });
    const fa = path.join(dir, name + '-A.png'), fb = path.join(dir, name + '-B-nothreads.png');
    const raf3 = () => pg.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))));
    await pg.evaluate(() => hyperApi.freeze(0.25)); await raf3(); await sleep(300); await raf3();
    const safe = await pg.evaluate(() => hyperApi.safeRect());
    await pg.screenshot({ path: fa, type: 'png' });
    await pg.evaluate(() => { const g = n => hyperApi.browser.currentScene.getImportedNode(n); window.__abFell = g('FiberCore').uFell; g('FiberCore').uFell = -100000; g('GlowSwitch').whichChoice = -1; });
    await raf3(); await sleep(300); await raf3();
    await pg.screenshot({ path: fb, type: 'png' });
    await pg.evaluate(() => { const g = n => hyperApi.browser.currentScene.getImportedNode(n); g('FiberCore').uFell = window.__abFell; g('GlowSwitch').whichChoice = 0; hyperApi.unfreeze(); });
    await raf3();
    let row = null; try { row = JSON.parse(execFileSync(process.env.LOOM_GATE_PYTHON || 'python3', ['-I', path.join(__dirname, 'scene_stats.py'), '--ab', fa + '@' + fb + ':' + [safe.x0, safe.y0, safe.x1, safe.y1].map(Math.round).join(',')], { encoding: 'utf8' }).trim()); } catch (e) { row = { error: String(e).slice(0, 300) }; }
    metrics.notch = metrics.notch || []; metrics.notch.push(Object.assign({ stop: label }, row));
    check(label + ' no dark notches: share of scene pixels the threads darken by > 0.05 luma and leave under 0.15 <= 0.0001 (A/B, clocks frozen; tools/scene_stats.py --ab)', !!row && row.notch !== undefined && row.notch <= 0.0001, row);
  }

  async function fly(pg, name, label, opts) {   // fly (or bind) to a named shot with the recorder on; returns the analysis
    await pg.evaluate(() => hyperApi.recStart());
    const D = await pg.evaluate(() => ({ shots: hyperApi.data.shots, scale: hyperApi.data.pocket_scale }));
    const s = D.shots[name], k = s.space === 'host' ? 1 / D.scale : 1, endPos = s.pos.map(x => x * k);
    const native = name === 'Host' || name === 'Flywheel';
    if (native) { await pg.evaluate(n => hyperApi.flyShot(n), name); if (name === 'Flywheel') await sleep(3200); else { await sleep(1800); await settle(pg, endPos, 0.01); } }
    else { await pg.evaluate(n => hyperApi.flyShot(n), name); await settle(pg, endPos); }
    await sleep(300);
    const rec = await pg.evaluate(() => hyperApi.recStop()), pose = await pg.evaluate(() => hyperApi.pose()), chip = await pg.evaluate(() => document.getElementById('shotchip').textContent);
    const a = motion(rec, name === 'Flywheel' ? null : endPos); a.chip = chip;
    metrics.moves.push(Object.assign({ family: 'rothschild', shot: name, size: s.size, move: native ? 'bind (X3D ANIMATE)' : 'Probe flight' }, a));
    const landed = name === 'Flywheel' ? /Flywheel/.test(pose.bound || '') : a.end_pos_err < (native ? 0.01 : 2e-3);
    check('shot ' + name + ' (' + s.size + ', ' + (native ? 'native bind' : 'Probe flight') + '): smooth, no jump, lands on the shot, the chip names it' + (label ? '; ' + label : ''), smooth(a) && landed && chip.indexOf(s.size + ' · ') === 0 && (!opts || !opts.extra || opts.extra(pose)), Object.assign({ bound: pose.bound, nav: pose.nav }, a));
    if (FRAMES) frames.push(await shoot(pg, 'rothschild-shot-' + name));
    return { a, pose };
  }

  async function rothschildExtras(pg, D) {
    // every shot of the camera grammar that the tour did not already fly
    const names = ['Host', 'Wide', 'Crown', 'Colossus'].concat(D.order_west_to_east.map(k => D.sectors[k].shot), Object.keys(D.shots).filter(n => /^S\d\d_/.test(n)), ['Inside', 'Flywheel']);
    for (const n of names) {
      if (n === 'Inside') {   // the plunge from the Host, through the shell
        await fly(pg, 'Host');
        await pg.evaluate(() => hyperApi.recStart()); await pg.keyboard.press('p'); await sleep(1500);
        await pg.waitForFunction(() => !hyperApi.pose().flying && hyperApi.pose().shot === 'Inside', null, { timeout: 120000 }).catch(() => {}); await settle(pg, D.shots.Inside.pos);
        await pg.waitForFunction(() => hyperApi.pose().nav === 'FLY', null, { timeout: 15000 }).catch(() => {});
        const rec = await pg.evaluate(() => hyperApi.recStop()), pose = await pg.evaluate(() => hyperApi.pose()), s = D.shots.Inside, a = motion({ samples: rec.samples.filter(x => x.t > (rec.marks.find(m => /^fly/.test(m.label)) || { t: 0 }).t - 5), cmds: rec.cmds.filter(x => x.t > (rec.marks.find(m => /^fly/.test(m.label)) || { t: 0 }).t - 5) }, s.pos);
        metrics.moves.push(Object.assign({ family: 'rothschild', shot: 'Inside', size: s.size, move: 'plunge (key P)' }, a));
        check('plunge (key P): Host to Inside in 7 s (x' + SLOWMO + ' slow motion here), smooth, through the shell (ShellSense reports enter pocket), lands on the Inside shot, FLY bound', smooth(a) && a.end_pos_err < 2e-3 && rec.marks.some(m => m.label === 'enter pocket') && pose.nav === 'FLY' && a.seconds > 6 * SLOWMO && a.seconds < 8.6 * SLOWMO,
          Object.assign({ marks: rec.marks.map(m => m.label), nav: pose.nav }, a));
        if (FRAMES) frames.push(await shoot(pg, 'rothschild-shot-Inside'));
        continue;
      }
      await fly(pg, n);
    }
    // ---- click a fiber with the real mouse: hover tag, card, highlight, a Present flight; then Esc
    await fly(pg, 'Wide');
    const tgt = await pg.evaluate(() => { const A = hyperApi, R = A.safeRect(), ids = Object.keys(A.data.people).sort((a, b) => A.data.people[a].i - A.data.people[b].i);
      const boxes = A.labelBoxes();
      for (const id of ids) { const L = A.data.people[id].line;
        for (let i = 0; i < L.length - 1; i++) for (const f of [0.3, 0.5, 0.7]) {
          const m = [0, 1, 2].map(k => L[i][k] + (L[i + 1][k] - L[i][k]) * f), s = A.project(m);
          if (!s || s.x < R.x0 + 30 || s.x > R.x1 - 30 || s.y < R.y0 + 30 || s.y > R.y1 - 30) continue;
          if (boxes.some(b => s.x > b.x - 8 && s.x < b.x + b.w + 8 && s.y > b.y - 8 && s.y < b.y + b.h + 8)) continue;
          if (A.nearestPerson(s.x, s.y, 12) === id && A.nearestPerson(s.x + 3, s.y + 3, 12) === id) return { id, x: s.x, y: s.y, name: A.cards.people[id].name, label: A.data.people[id].label, i: A.data.people[id].i };
        } }
      return null; });
    if (!tgt) check('click: a free point on a fiber at the Wide shot', false, 'none found');
    else {
      await pg.mouse.move(tgt.x + 2, tgt.y); await sleep(300); await pg.mouse.move(tgt.x, tgt.y); await sleep(600);
      const hover = await pg.evaluate(() => ({ hidden: document.getElementById('tag').hidden, text: document.getElementById('tag').textContent }));
      await pg.evaluate(() => hyperApi.recStart());
      await pg.mouse.click(tgt.x, tgt.y); await sleep(600);
      const r = await pg.evaluate(() => ({ picked: hyperApi.picked, card: !document.getElementById('card').hidden, h2: (document.querySelector('#card h2') || {}).textContent || '',
        uPick: hyperApi.browser.currentScene.getImportedNode('FiberCore').uPick, uPickGlow: hyperApi.browser.currentScene.getImportedNode('FiberGlow').uPick, sections: [...document.querySelectorAll('#card h3')].map(e => e.textContent) }));
      await pg.waitForFunction(() => !hyperApi.pose().flying, null, { timeout: 30000 }).catch(() => {}); await sleep(700);
      const rec = await pg.evaluate(() => hyperApi.recStop()), a = motion(rec, null);
      check('click: the real mouse on ' + tgt.name + '\'s fiber shows the hover tag, picks the life, opens its card (RECORD and COMPUTED), lights it (uPick) and flies smoothly to its Present shot',
        !hover.hidden && hover.text.startsWith(tgt.label) && r.picked && r.card && r.h2.startsWith(tgt.name) && r.uPick === tgt.i && r.uPickGlow === tgt.i && r.sections.join() === 'RECORD,COMPUTED' && smooth(a) && rec.marks.some(m => /^arrive Present/.test(m.label)),
        { at: [Math.round(tgt.x), Math.round(tgt.y)], hover, r, a });
      if (FRAMES) frames.push(await shoot(pg, 'rothschild-pick-card'));
      await pg.keyboard.press('Escape'); await sleep(400);
      const cl = await pg.evaluate(() => ({ picked: hyperApi.picked, card: !document.getElementById('card').hidden, uPick: hyperApi.browser.currentScene.getImportedNode('FiberCore').uPick }));
      check('click: Esc clears the pick, closes the card and relights every fiber', cl.picked === null && !cl.card && cl.uPick === -1, cl);
    }
    // ---- the fell
    await fly(pg, 'Wide');
    const fell = await pg.evaluate(async () => { const A = hyperApi, sc = A.browser.currentScene, g = n => sc.getImportedNode(n);
      A.setFell(1850); await new Promise(r => setTimeout(r, 300));
      const o = { fell: A.fell, core: g('FiberCore').uFell, glow: g('FiberGlow').uFell, shell: g('ShellShader').uFell, slider: document.getElementById('fell').value, out: document.getElementById('fellv').textContent };
      return o; });
    if (FRAMES) frames.push(await shoot(pg, 'rothschild-fell-1850'));
    await pg.keyboard.press('}'); await sleep(200); await pg.keyboard.press(']'); await sleep(200);
    const k = await pg.evaluate(() => ({ fell: hyperApi.fell, core: hyperApi.browser.currentScene.getImportedNode('FiberCore').uFell }));
    const sl = await pg.$('#fell'); const bb = await sl.boundingBox(); await pg.mouse.click(bb.x + bb.width * 0.25, bb.y + bb.height / 2); await sleep(300);
    const s2 = await pg.evaluate(() => ({ fell: hyperApi.fell, core: hyperApi.browser.currentScene.getImportedNode('FiberCore').uFell, slider: +document.getElementById('fell').value }));
    check('fell: 1850 reaches the core, glow and glass shaders (uFell) and the slider; } and ] add 25 and 1 years; a real click on the slider moves the time cut', fell.fell === 1850 && fell.core === 1850 && fell.glow === 1850 && fell.shell === 1850 && fell.slider === '1850' && fell.out === '1850' &&
      k.fell === 1876 && k.core === 1876 && s2.fell === s2.slider && s2.core === s2.slider && s2.fell < 1876, { fell, keys: k, slider: s2 });
    await pg.evaluate(() => hyperApi.setFell(hyperApi.data.units.top));
    // ---- the quality tiers: uniforms, glow width, frame time (SwiftShader, relative only)
    const tiers = {};
    for (const [ti, name] of ['fast', 'balanced', 'ultra'].entries()) {
      const r = await pg.evaluate(async ti => { const A = hyperApi; A.setTier(ti); A.freeze(0.25); await new Promise(r => setTimeout(r, 400));
        const sc = A.browser.currentScene, q = ['FiberCore', 'FiberGlow', 'ShellShader', 'SeedGlow'].map(n => sc.getImportedNode(n).uQ).concat([sc.getNamedNode('SkyShader').uQ]);
        const bench = await A.bench(12); A.unfreeze(); return { tier: A.tier, q, glow: sc.getImportedNode('FiberGlow').uWidth, want: A.data.glow[A.tier], pressed: document.querySelector('#tiers button.on').dataset.tier, bench }; }, ti);
      tiers[name] = r; metrics.tiers[name] = r.bench;
      if (FRAMES) frames.push(await shoot(pg, 'rothschild-tier-' + name, W, H, null));
    }
    check('tiers: Fast, Balanced and Ultra set uQ on every shader (0, 1, 2) and the glow width (' + JSON.stringify(D.glow) + '), the pressed button follows; frame times measured',
      ['fast', 'balanced', 'ultra'].every((n, i) => tiers[n].tier === n && tiers[n].q.every(x => x === i) && Math.abs(tiers[n].glow - tiers[n].want) < 1e-6 && tiers[n].pressed === String(i)),
      Object.fromEntries(Object.entries(tiers).map(([k, v]) => [k, { q: v.q, glow: v.glow, ms: v.bench.medianMs }])));
    const mon = await pg.evaluate(async () => { const A = hyperApi; A.setTier(2); A.auto = true; document.getElementById('auto').checked = true; A.autoLowered.length = 0;
      await new Promise(r => setTimeout(r, 9000)); const o = { fps: A.fps, lowered: A.autoLowered.slice(), tier: A.tier, toast: document.getElementById('toast').textContent }; A.setTier(2); return o; });
    check('fps monitor: with auto on, a frame rate under 22 fps lowers the tier (and says so); at or over it the tier stays', mon.fps < 22 ? mon.lowered.length >= 1 && mon.tier !== 'ultra' && /Quality lowered/.test(mon.toast) : mon.lowered.length === 0, mon);
    // ---- keys
    await pg.evaluate(() => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); });   // the fell slider kept focus from its click: arrows belong to it
    await pg.keyboard.press('w'); await sleep(200); const kw = await pg.evaluate(() => hyperApi.pose().flying);
    await pg.waitForFunction(() => !hyperApi.pose().flying, null, { timeout: 30000 }).catch(() => {}); const kw2 = await pg.evaluate(() => hyperApi.pose().shot);
    const k0 = await pg.evaluate(() => [hyperApi.stop, hyperApi.data.tour.length]);
    await pg.keyboard.press('ArrowRight'); await sleep(300); const kr = await pg.evaluate(k0 => (hyperApi.stop - ((Math.max(0, k0[0]) + 1) % k0[1])), k0);   // 0 = moved to the next stop
    await pg.keyboard.press('t'); await sleep(300); const tOn = await pg.evaluate(() => document.getElementById('tour').textContent);
    await pg.keyboard.press('t'); await sleep(300); const tOff = await pg.evaluate(() => document.getElementById('tour').textContent);
    await pg.keyboard.press('q'); await sleep(200); const kq = await pg.evaluate(() => hyperApi.tier);
    await pg.keyboard.press('Escape'); await sleep(300);
    check('keys: W flies to Wide, the right arrow goes to the next stop, T starts and stops the tour, Q cycles the quality', kw === true && kw2 === 'Wide' && kr === 0 && /❚❚/.test(tOn) && /▸/.test(tOff) && kq === 'balanced', { kw, kw2, kr, tOn, tOff, kq });
    await pg.evaluate(t => hyperApi.setTier(['fast', 'balanced', 'ultra'].indexOf(t)), MOTION_TIER);   // back to the motion tier for the other families
  }

  async function phone() {
    const ph = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true }); ph.setDefaultTimeout(240000); hook(ph, 'phone');
    await ph.goto(BASE + 'index.html?auto=0&idle=0', { waitUntil: 'load' }); await loaded(ph); await sleep(1500);
    const pl = await ph.evaluate(() => { const r = id => { const e = document.getElementById(id).getBoundingClientRect(); return [Math.round(e.left), Math.round(e.top), Math.round(e.right), Math.round(e.bottom)]; };
      return { sw: document.documentElement.scrollWidth, iw: innerWidth, cap: r('cap'), rail: r('rail'), head: (function () { var e = document.querySelector('header').getBoundingClientRect(); return [Math.round(e.left), Math.round(e.top), Math.round(e.right), Math.round(e.bottom)]; })(), tier: hyperApi.tier, failed: hyperApi.failed || null, shaders: hyperApi.shaders() }; });
    check('phone (390 x 844): loads (Balanced tier by default on a small or coarse screen), no horizontal scroll, header, caption and stop rail inside the 16 px gutters, shaders compiled',
      !pl.failed && pl.sw <= pl.iw && pl.cap[0] >= 16 && pl.cap[2] <= pl.iw - 16 && pl.rail[0] >= 16 && pl.rail[2] <= pl.iw - 16 && pl.head[0] >= 16 && pl.head[2] <= pl.iw - 16 && pl.tier === 'balanced' && pl.shaders.every(s => s.isValid), pl);
    const D = JSON.parse(fs.readFileSync(path.join(OUT, manifest.families[0].data), 'utf8'));
    if (FRAMES) frames.push(await shoot(ph, 'phone-rothschild-S00-Host', 390, 844, null));
    for (let i = 1; i < D.tour.length; i++) {
      if (SMOKE && i > 2) break;
      await ph.evaluate(i => hyperApi.goStop(i), i); { const s = D.shots[D.tour[i].shot], k = s.space === 'host' ? 1 / D.pocket_scale : 1; await settle(ph, s.pos.map(x => x * k)); }
      await stopChecks(ph, D, 'rothschild', i, 390, 844);
    }
    // a tap on a fiber opens the card as a bottom sheet
    const tgt = await ph.evaluate(() => { const A = hyperApi, R = A.safeRect(); for (const id of Object.keys(A.data.people)) { const L = A.data.people[id].line;
      for (let i = 0; i < L.length - 1; i++) { const m = [0, 1, 2].map(k => (L[i][k] + L[i + 1][k]) / 2), s = A.project(m); if (s && s.x > R.x0 + 20 && s.x < R.x1 - 20 && s.y > R.y0 + 20 && s.y < R.y1 - 20 && A.nearestPerson(s.x, s.y, 22) === id) return { id, x: s.x, y: s.y }; } } return null; });
    if (tgt) {
      await ph.touchscreen.tap(tgt.x, tgt.y); await sleep(900);
      const c = await ph.evaluate(() => { const e = document.getElementById('card'), r = e.getBoundingClientRect(); return { hidden: e.hidden, l: r.left, r: r.right, b: r.bottom, iw: innerWidth, ih: innerHeight, picked: hyperApi.picked }; });
      check('phone: a tap on a fiber opens its card as a sheet inside the gutters', !c.hidden && c.picked && c.l >= 16 && c.r <= c.iw - 16 && c.b <= c.ih, c);
      if (FRAMES) frames.push(await shoot(ph, 'phone-rothschild-card', 390, 844, null));
    } else check('phone: a fiber to tap', false, 'none found');
    await ph.close();
  }

  async function settle(pg, endPos, tol = 2e-3) {   // the sensor reports the pose a rendered frame after the Probe is written: wait for it
    await pg.waitForFunction(a => { const P = hyperApi.pose().p, e = a[0]; return P && Math.hypot(P[0] - e[0], P[1] - e[1], P[2] - e[2]) < a[1]; }, [endPos, tol], { timeout: 30000, polling: 100 }).catch(() => {});
    await sleep(300);
  }
  async function shoot(pg, name, w = W, h = H, tier = 2) {   // frames at Ultra (the look), whatever tier the moves ran at
    fs.mkdirSync(FR, { recursive: true }); const file = path.join(FR, name + '.png'); const safe = await pg.evaluate(() => hyperApi.safeRect());
    const prev = await pg.evaluate(t => { const A = hyperApi, p = A.tierIndex; if (t != null && t !== p) A.setTier(t); return p; }, tier);
    if (tier != null && tier !== prev) await pg.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))));
    await pg.screenshot({ path: file, type: 'png' }); console.log('frame', name);
    if (tier != null && tier !== prev) {   // back to the motion tier, and let X_ITE's rebuild after the option change pass before the next move is recorded
      await pg.evaluate(p => hyperApi.setTier(p), prev);
      await pg.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))));
    }
    return { name, file: path.relative(HYPER, file), tier: ['fast', 'balanced', 'ultra'][tier != null ? tier : prev], safe: [safe.x0, safe.y0, safe.x1, safe.y1].map(Math.round) };
  }

  async function finish() {
    let look = null;
    if (FRAMES && frames.length) {
      try { const txt = execFileSync(process.env.LOOM_GATE_PYTHON || 'python3', ['-I', path.join(ROOT, 'gates', 'lookgates.py'), ...frames.map(f => path.join(HYPER, f.file))], { encoding: 'utf8' });
        look = txt.trim().split('\n').map(l => ({ ok: l.startsWith('ok'), line: l.replace(HYPER + '/', '') }));
        check('lookgates.py nonblack: every frame (' + look.length + ') is lit (p99 luma and lit share over the gate\'s thresholds)', look.every(x => x.ok), look.filter(x => !x.ok).map(x => x.line).join(' | ') || look.length + ' ok');
      } catch (e) { check('lookgates.py ran', false, String(e).slice(0, 300)); }
      const ins = frames.filter(f => /-Inside$/.test(f.name));   // build 2 (critique fix 1): the plunge's landing keeps its black
      if (ins.length) {
        let txt = ''; try { txt = execFileSync(process.env.LOOM_GATE_PYTHON || 'python3', ['-I', path.join(__dirname, 'scene_stats.py'), '--inside', ...ins.map(f => path.join(HYPER, f.file) + ':' + f.safe.join(','))], { encoding: 'utf8' }); }
        catch (e) { txt = String(e.stdout || ''); }
        const rows = txt.trim().split('\n').filter(Boolean).map(l => JSON.parse(l)); metrics.inside_gate = rows;
        check('Inside lookgate (tools/scene_stats.py --inside, scene area inside the UI): every Inside frame (' + ins.length + ') has mean luma <= 0.22, lit share <= 0.70, clipped white <= 0.3 percent',
          rows.length === ins.length && rows.every(r => r.inside_gate === 'ok'), rows.map(r => r.file + ' mean ' + r.mean + ' lit ' + r.lit + ' clipped ' + r.clipped + ' ' + r.inside_gate).join(' | '));
      }
    }
    let tarCheck = null;
    try { const tgz = path.join(ROOT, 'x3d', 'vendor', 'x_ite-16.5.1.tgz'), entries = new Set(execFileSync('tar', ['tzf', tgz], { encoding: 'utf8' }).split('\n'));
      const pulled = [...new Set(reqs.filter(u => u.startsWith(BASE + 'x_ite/')).map(u => u.slice((BASE + 'x_ite/').length).split('?')[0]))].sort();
      tarCheck = { pulled, missing_in_tarball: pulled.filter(x => !entries.has('package/dist/' + x)) };
      check('cdn: each X_ITE file the page pulled (' + pulled.length + ') exists at package/dist/<same path> in the npm tarball, so the jsDelivr fallback serves it', tarCheck.missing_in_tarball.length === 0, tarCheck);
    } catch (e) { check('cdn: tarball listing', false, String(e).slice(0, 200)); }
    const out = { when: new Date().toISOString(), smoke: SMOKE, engine: 'X_ITE 16.5.1 (shipped copy beside the page)', chromium: b.version(), playwright: require('playwright/package.json').version, gl: 'SwiftShader (ANGLE), software',
      viewport: [W, H], slowmo: SLOWMO, motion_tier: MOTION_TIER, boot_ms: bootMs, pass, fail, checks, metrics, frames, lookgates: look, cdn_assets: tarCheck, console_all: cons, page_errors: errs, bad_requests: bad, requests: [...new Set(reqs)].length };
    if (ARTIFACT) out.served = OUT;
    fs.writeFileSync(path.join(HYPER, ARTIFACT ? 'gate-artifact.json' : 'gate.json'), JSON.stringify(out, null, 1));
    if (!SMOKE && !ARTIFACT) {
      try { const rec = JSON.parse(fs.readFileSync(REC, 'utf8'));
        rec.xite_gate = { file: 'hyper/gate.json', run: out.when, engine: out.engine, chromium: out.chromium, playwright: out.playwright, gl: out.gl, pass, fail, script_sha256: H256(__filename),
          checks: checks.map(c => (c.ok ? 'PASS ' : 'FAIL ') + c.name), console_messages: cons.length, frames: frames.map(f => f.file), frame_ms_swiftshader: metrics.tiers };
        rec.lookgates = look; rec.inside_gate = metrics.inside_gate || null; rec.selection = metrics.selection || null; rec.threads_add_light = metrics.notch || null; fs.writeFileSync(REC, JSON.stringify(rec, null, 1)); } catch (e) { console.log('receipt not updated', e); }
      if (frames.length) fs.writeFileSync(path.join(FR, 'receipt.json'), JSON.stringify({ what: 'frames shot by tools/gate_hyper.js: every tour stop of every family, every shot of the camera grammar (Rothschild), the pick, the fell, the tiers, the phone', run: out.when, inside_gate: metrics.inside_gate || null,
        gate_script_sha256: H256(__filename), scene_inputs: Object.fromEntries(fs.readdirSync(OUT).filter(f => /\.(x3d|json|html)$/.test(f) && f !== 'receipt.json').sort().map(f => [f, H256(path.join(OUT, f))])),
        tools: { engine: out.engine, chromium: out.chromium, playwright: out.playwright, gl: out.gl, viewport: [W, H], lookgates: 'proto/gates/lookgates.py (venv-gate python)' },
        frames: Object.fromEntries(frames.map(f => [path.basename(f.file), H256(path.join(HYPER, f.file))])), lookgates: look }, null, 1));
    }
    console.log(pass + ' passed, ' + fail + ' failed; console messages: ' + cons.length);
    await b.close(); srv.close(); process.exit(fail ? 1 : 0);
  }
})().catch(e => { console.error(e); process.exit(2); });
