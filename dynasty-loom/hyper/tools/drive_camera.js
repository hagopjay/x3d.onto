// NODE_PATH=/opt/node-tools/node_modules node drive_camera.js [--smoke] [--only=tour,drag,roll,rig,native,fly,families]
// Drives the hypersphere camera proof (hyper/proof/camera.html) in X_ITE 16.5.1 (the vendored copy), full Chromium on SwiftShader, 1527 x 923.
// Serves proto/ itself with a strict copy of the Artifact CSP on every response (no unsafe-eval, connect-src 'self'; .x3d as application/xml).
// Records the camera pose per frame from the pocket's ProximitySensor, runs the tour and the single moves, checks smoothness (no jumps),
// arrival, EXAMINE after a page-driven move (orbit about the subject, horizon level), a click on a person, the two controls (rolled shot
// without an up frame; the pocket pages' rig), native X3D binds, the scriptless Flywheel, and shoots one frame per shot into proof/frames/.
// Writes proof/camera-proof.json (checks, metrics, traces summary, frame hashes).
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
const { execFileSync } = require('child_process');
const ARGV = process.argv.slice(2), SMOKE = ARGV.includes('--smoke');
const ONLY = ((ARGV.find(a => a.startsWith('--only=')) || '--only=').slice(7) || 'tour,drag,roll,rig,native,families').split(',');
const HYPER = path.resolve(__dirname, '..'), ROOT = path.resolve(HYPER, '..'), PROOF = path.join(HYPER, 'proof'), FR = path.join(PROOF, 'frames');
const W = 1527, H = 923;
const CDNS = 'https://cdnjs.cloudflare.com https://cdn.jsdelivr.net/npm/ https://unpkg.com https://cdn.tailwindcss.com https://code.jquery.com';
const CSP = ["default-src 'none'", "script-src 'self' 'unsafe-inline' " + CDNS, "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  'font-src https://fonts.gstatic.com', "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "media-src 'self' data: blob:"].join('; ');   // copied from scene2/tools/artifact_csp_gate.js
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': 'application/xml', '.png': 'image/png', '.ttf': 'font/ttf', '.wasm': 'application/wasm', '.txt': 'text/plain' };
const served = [];
const srv = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])), csp = /[?&]csp=1(&|$)/.test(q.url) ? { 'content-security-policy': CSP } : {};
  if (!p.startsWith(ROOT)) { r.writeHead(403); return r.end(); }
  fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } served.push(q.url.split('?')[0]);
    r.writeHead(200, Object.assign({ 'content-type': MIME[path.extname(p)] || 'application/octet-stream', 'cache-control': 'no-store' }, csp)); r.end(d); }); });   // the CSP rides on the page (document) response of a ?csp=1 run
let pass = 0, fail = 0; const checks = [], metrics = {}, frames = [];
const check = (name, ok, detail) => { ok ? pass++ : fail++; checks.push({ name, ok: !!ok, detail: detail === undefined ? '' : (typeof detail === 'string' ? detail : JSON.stringify(detail)).slice(0, 900) });
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? '  ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)).slice(0, 400) : '')); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------------------------------------------------------- maths (pocket units)
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], len = a => Math.hypot(a[0], a[1], a[2]);
const qmul = (a, b) => [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0], a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
const qconj = a => [-a[0], -a[1], -a[2], a[3]], qrot = (q, v) => { const p = qmul(qmul(q, [v[0], v[1], v[2], 0]), qconj(q)); return [p[0], p[1], p[2]]; };
const qang = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]))) * 180 / Math.PI;
const deg = (a, b) => Math.acos(Math.max(-1, Math.min(1, dot(a, b) / (len(a) * len(b) || 1)))) * 180 / Math.PI;
function project(p, pose) {   // X_ITE: fieldOfView spans the smaller side of the canvas
  const c = qrot(qconj(pose.q), sub(p, pose.p)), depth = -c[2], f = 1 / Math.tan(pose.fov / 2), asp = W / H;
  const nx = asp >= 1 ? f * c[0] / (depth * asp) : f * c[0] / depth, ny = asp >= 1 ? f * c[1] / depth : f * c[1] * asp / depth;
  return { x: (nx + 1) / 2 * W, y: (1 - ny) / 2 * H, depth };
}
function rollDeg(q, frame) {   // tilt of the camera's right vector out of the horizontal plane of `frame` (+Y up there)
  const x = qrot(qconj(frame || [0, 0, 0, 1]), qrot(q, [1, 0, 0])); return Math.asin(Math.max(-1, Math.min(1, x[1]))) * 180 / Math.PI;
}
function analyse(samples, t0, t1, end, scale) {   // one move: samples inside [t0, t1] plus the last one before t0 (the rest pose)
  const before = samples.filter(s => s.t < t0).slice(-1), mv = samples.filter(s => s.t >= t0 && s.t <= t1 + 30), S = before.concat(mv);
  if (S.length < 3) return { n: S.length, ok: false, why: 'too few samples' };
  const steps = [], vs = [], angs = []; let L = 0, cosMin = 1;
  for (let i = 1; i < S.length; i++) { const d = sub(S[i].p, S[i - 1].p), l = len(d), dt = Math.max(1, (S[i].tc != null ? S[i].tc - S[i - 1].tc : S[i].t - S[i - 1].t)); steps.push(l); vs.push(l / dt * 1000); angs.push(qang(S[i].q, S[i - 1].q)); L += l;
    if (i >= 2) { const d0 = sub(S[i - 1].p, S[i - 2].p); if (len(d0) > 1e-4 && l > 1e-4) cosMin = Math.min(cosMin, dot(d0, d) / (len(d0) * l)); } }
  const T = (S[S.length - 1].t - mv[0].t) / 1000, vmean = L / Math.max(1e-6, T), vmax = Math.max(...vs.slice(1)), maxStep = Math.max(...steps), meanStep = L / steps.length;   // time from the first moving frame (the rest pose before can be a hold)
  const angTot = angs.reduce((a, b) => a + b, 0), maxAng = Math.max(...angs);
  const startStep = steps[0], endP = S[S.length - 1];
  const r = { n: S.length, seconds: +T.toFixed(2), path: +L.toFixed(3), max_step: +maxStep.toFixed(4), step_ratio: +(maxStep / Math.max(1e-9, meanStep)).toFixed(2), speed_ratio: +(vmax / Math.max(1e-9, vmean)).toFixed(2),
    first_step_share: +(startStep / Math.max(1e-9, L)).toFixed(3), turn_deg: +angTot.toFixed(1), max_turn_step_deg: +maxAng.toFixed(2), ang_ratio: +(maxAng / Math.max(1e-9, angTot / angs.length)).toFixed(2), min_step_cos: +cosMin.toFixed(3) };
  if (end) { r.end_pos_err = +len(sub(endP.p, end.p)).toFixed(4); r.end_ang_err_deg = +qang(endP.q, end.q).toFixed(3); }
  r.frame_jumps = steps.filter((l, i) => l > 0.25 * L && L > 0.05 * (scale || 1) && steps.length > 6).length + angs.filter(a => a > 0.25 * angTot && angTot > 3 && angs.length > 6).length;   // per frame: a slow frame carries a long step
  // per second: the flight is a function of the clock, so a renderer hitch (long frame) lengthens a step but must not raise its speed.
  // A jump is a step whose linear or angular speed is more than 2.5x both neighbours' and more than half the peak.
  const ck = x => (x.tc != null ? x.tc : x.t), dts = []; for (let i = 1; i < S.length; i++) dts.push(Math.max(1, ck(S[i]) - ck(S[i - 1])));   // the frame clock that drives the move
  const ws = angs.map((a, i) => a / dts[i] * 1000), wmax = Math.max(...ws), spike = (v, vm) => v.filter((x, i) => i > 0 && i < v.length - 1 && x > 0.5 * vm && x > 2.5 * Math.max(v[i - 1], v[i + 1], 1e-9)).length;
  r.jumps = spike(vs, vmax) + spike(ws, wmax);
  r.max_frame_ms = Math.round(Math.max(...dts.slice(1))); r.median_frame_ms = Math.round(median(dts.slice(1)));
  r.ang_speed_ratio = +(wmax / Math.max(1e-9, angTot / Math.max(1e-6, T))).toFixed(2);
  return r;
}
function lookQ(pos, tgt, up) { // same as the page's
  const nrm = a => { const l = len(a); return [a[0] / l, a[1] / l, a[2] / l]; }, cr = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const z = nrm(sub(pos, tgt)), x = nrm(cr(up, z)), y = cr(z, x), m = [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]], tr = m[0][0] + m[1][1] + m[2][2]; let s, r;
  if (tr > 0) { s = Math.sqrt(tr + 1) * 2; r = [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]; }
  else if (m[0][0] > m[1][1] && m[0][0] > m[2][2]) { s = Math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; r = [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]; }
  else if (m[1][1] > m[2][2]) { s = Math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; r = [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]; }
  else { s = Math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; r = [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]; }
  return r;
}
const shotEnd = (SH, name) => { const s = SH.shots[name], k = s.space === 'host' ? 1 / SH.pocket_scale : 1, p = s.pos.map(x => x * k), t = s.tgt.map(x => x * k); return { p, q: lookQ(p, t, s.up), F: t }; };
const median = a => { const b = a.slice().sort((x, y) => x - y); return b.length ? b[Math.floor(b.length / 2)] : null; };

(async () => {
  fs.mkdirSync(FR, { recursive: true });
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const cons = [], bad = [];
  async function open(fam, cspRun) {
    const p = await b.newPage({ viewport: { width: W, height: H } }); p.setDefaultTimeout(180000);
    const run = cspRun ? 'csp' : 'main'; p.on('console', m => cons.push({ fam, run, type: m.type(), text: m.text().slice(0, 400) })); p.on('pageerror', e => cons.push({ fam, run, type: 'pageerror', text: String(e).slice(0, 400) }));
    p.on('requestfailed', r => { if (!cspRun) bad.push('requestfailed ' + r.url()); }); p.on('response', r => { if (r.status() >= 400 && !/favicon\.ico$/.test(r.url())) bad.push('HTTP ' + r.status() + ' ' + r.url()); });
    const t0 = Date.now();
    await p.goto(BASE + 'hyper/proof/camera.html?ui=min&idle=0' + (fam ? '&family=' + fam : '') + (cspRun ? '&csp=1' : ''), { waitUntil: 'load' });
    await p.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', null, { timeout: 120000 });
    const st = await p.evaluate(() => ({ failed: camApi.failed, engine: camApi.engine, pose: camApi.pose(), shots: camApi.shots }));
    st.bootMs = Date.now() - t0; return { p, st };
  }
  async function shoot(p, name, purpose) { const f = path.join(FR, name + '.png'); await p.screenshot({ path: f }); frames.push({ name, file: path.relative(HYPER, f), purpose, sha256: crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex') }); }
  async function drag(p, x0, y0, dx, dy, steps) { await p.mouse.move(x0, y0); await p.mouse.down(); for (let i = 1; i <= steps; i++) { await p.mouse.move(x0 + dx * i / steps, y0 + dy * i / steps); await sleep(35); } await sleep(350); await p.mouse.up(); await sleep(900); }

  // ================================================================ Rothschild: boot
  const { p, st } = await open(null); const SH = st.shots;
  check('boot: camera.html loads camera.x3d, Inlines the pocket and resolves the IMPORTs (Probe, CamSense) in X_ITE 16.5.1', !st.failed && st.engine && st.engine.version === '16.5.1' && st.pose.p,
    { failed: st.failed, engine: st.engine, bootMs: st.bootMs, pose: st.pose });
  check('boot: the opening viewpoint (Host, in the host space) is bound at load and the camera sensor reports in pocket units', st.pose.bound === 'Opening: the pocket in its host' && Math.abs(len(st.pose.p) - len(shotEnd(SH, 'Host').p)) < 0.05,
    { bound: st.pose.bound, sensed_dist: len(st.pose.p), planned_pocket_dist: len(shotEnd(SH, 'Host').p) });
  if (SMOKE) { await shoot(p, 'smoke-host', 'smoke'); await p.evaluate(() => camApi.flyTo('Wide')); await sleep(400); await shoot(p, 'smoke-wide', 'smoke'); console.log(JSON.stringify(cons.slice(0, 20))); await finish(); return; }

  // ================================================================ the tour: chained stops, a frame per stop, the whole trace checked
  if (ONLY.includes('tour')) {
    await p.evaluate(() => camApi.recStart());
    const run = p.evaluate(() => camApi.tour());
    const seen = new Set(), holds = []; let state = null; const tStart = Date.now();
    while (Date.now() - tStart < 240000) {
      state = await p.evaluate(() => camApi.tourState);
      if (state && state.phase === 'hold' && !seen.has(state.i)) { seen.add(state.i); await sleep(state.shot === 'Flywheel' ? 200 : 600);
        const nn = String(state.i + 1).padStart(2, '0') + '-' + state.shot; await shoot(p, nn, SH.tour[state.i].caption); holds.push(state); }
      if (state && (state.phase === 'done' || state.phase === 'stopped')) break;
      await sleep(120);
    }
    await run; const tr = await p.evaluate(() => camApi.recStop()); const fpsList = await p.evaluate(() => camApi.fps());
    metrics.tour = { samples: tr.samples.length, marks: tr.marks.map(m => [+((m.t - tr.t0) / 1000).toFixed(2), m.label]), fps_median: median(fpsList), fps_min: Math.min(...fpsList), moves: [] };
    const mk = tr.marks; let allOk = true;
    for (let i = 0; i < mk.length; i++) {
      const m = mk[i], fm = /^fly (\S+)/.exec(m.label) || /^bind (\S+)/.exec(m.label); if (!fm) continue;
      const name = fm[1], endMark = mk.slice(i + 1).find(x => x.label === 'arrive ' + name || x.label === 'hold ' + name);
      const t1 = endMark ? endMark.t : m.t + 8000, isBind = m.label.startsWith('bind');
      const a = analyse(tr.samples, m.t, t1, isBind ? null : shotEnd(SH, name), 10);
      a.shot = name; a.kind = isBind ? 'native bind' : (name === 'Inside' ? 'plunge (Probe)' : 'Probe flight'); a.planned_s = (SH.tour.find(s => s.shot === name) || {}).dur_s;
      metrics.tour.moves.push(a); if (isBind) fs.writeFileSync(path.join(HYPER, 'work', 'bind-trace.json'), JSON.stringify(tr.samples.filter(x => x.t >= m.t - 200 && x.t <= t1 + 30).map(x => [Math.round(x.t), Math.round(x.tc), x.p.map(v => +v.toFixed(4))])));
      const ok = a.jumps === 0 && a.speed_ratio < 6 && a.ang_speed_ratio < 6 && a.first_step_share < 0.1 && (isBind || (a.end_pos_err < 2e-3 && a.end_ang_err_deg < 0.1));
      allOk = allOk && ok;
    }
    { // tracking: each commanded Probe pose is what the ProximitySensor reports on a following frame (the sensor sees the command, not a lagging copy)
      const errs = []; for (const c of tr.cmds) { const nx = tr.samples.find(x => x.t > c.t + 0.5); if (!nx) continue; const e = len(sub(nx.p, c.p)); errs.push(e); }
      errs.sort((a, b) => a - b); const q = f => errs.length ? +errs[Math.min(errs.length - 1, Math.floor(f * errs.length))].toFixed(4) : null;
      metrics.tour.tracking = { commands: tr.cmds.length, median_err: q(0.5), p95_err: q(0.95), note: 'next sensed position minus commanded position, pocket units; includes one frame of motion when a newer command lands first' };
    }
    check('tour: 9 stops played in order with a hold at each (Host, plunge to Inside, Colossus, EyeToEye, Crown, House, Present, Wide, Flywheel)', holds.length === SH.tour.length && holds.map(h => h.shot).join() === SH.tour.map(s => s.shot).join(), holds.map(h => h.shot));
    check('tour: every move is smooth per second (no speed spike over 2.5x its neighbours, peak/mean linear and angular speed < 6, first step < 10% of the path; frame hitches of SwiftShader reported, not judged) and every Probe flight lands on its planned pose (< 0.002 units, < 0.1 degree)', allOk,
      metrics.tour.moves.map(m => [m.shot, m.seconds, 'v', m.speed_ratio, 'w', m.ang_speed_ratio, 'j', m.jumps, 'fj', m.frame_jumps, 'maxms', m.max_frame_ms, 'end', m.end_pos_err, m.end_ang_err_deg]));
    const plunge = metrics.tour.moves.find(m => m.shot === 'Inside');
    check('opening: the plunge crosses the pocket shell (ShellSense fires) and takes the planned 7 s', !!mk.find(x => x.label === 'enter pocket') && plunge && Math.abs(plunge.seconds - 7) < 0.6, { enter: mk.filter(x => /pocket/.test(x.label)).map(x => +((x.t - tr.t0) / 1000).toFixed(2)), seconds: plunge && plunge.seconds });
    const holdLen = []; for (let i = 0; i < mk.length; i++) { const m = /^hold (\S+)/.exec(mk[i].label); if (!m) continue; const nx = mk.slice(i + 1).find(x => /^(fly|bind|tour end)/.test(x.label)); if (nx) holdLen.push([m[1], +((nx.t - mk[i].t) / 1000).toFixed(2), (SH.tour.find(s => s.shot === m[1]) || {}).hold_s]); }
    metrics.tour.holds = holdLen;
    check('tour: each hold lasts at least its reading time (1.5 s + words / 3, 4 to 9 s)', holdLen.filter(h => h[2]).every(h => h[1] >= h[2] - 0.15), holdLen);
    check('tour: shot sizes alternate and no framing repeats twice in a row (generator chain check)', SH.chain_checks.every(c => c.ok), SH.chain_checks.map(c => [c.pair.join('>'), c.sizes ? c.sizes.join('>') : 'hand-off', c.axis_turn_deg, c.dist_ratio]));
  }

  // ================================================================ EXAMINE and click after a page-driven move; a pick flies from the real pose
  if (ONLY.includes('drag')) {
    await p.evaluate(() => camApi.flyTo('Present')); await sleep(600);
    const p0 = await p.evaluate(() => camApi.pose()); await shoot(p, 'check-present-before-drag', 'Present, before the EXAMINE drag');
    await p.evaluate(() => camApi.recStart());
    await drag(p, W * 0.62, H * 0.42, 150, 12, 16);
    const p1 = await p.evaluate(() => camApi.pose()); const dtr = await p.evaluate(() => camApi.recStop());
    await shoot(p, 'check-present-after-drag', 'Present, after the EXAMINE drag (orbit about the subject, horizon level in the up frame)');
    const C = p0.C, s0 = project(C, p0), s1 = project(C, p1);
    const fw0 = qrot(p0.q, [0, 0, -1]), fw1 = qrot(p1.q, [0, 0, -1]);
    const dr = { rotated_deg: +deg(fw0, fw1).toFixed(2), pivot_drift_px: +Math.hypot(s1.x - s0.x, s1.y - s0.y).toFixed(2), dist_change: +(Math.abs(len(sub(p1.p, C)) - len(sub(p0.p, C))) / len(sub(p0.p, C))).toFixed(4),
      roll_in_frame_before: +rollDeg(p0.q, p0.frameQ).toFixed(2), roll_in_frame_after: +rollDeg(p1.q, p1.frameQ).toFixed(2), max_turn_step_deg: dtr.samples.length > 1 ? +Math.max(...dtr.samples.slice(1).map((s, i) => qang(s.q, dtr.samples[i].q))).toFixed(2) : null };
    metrics.drag_present = dr;
    check('EXAMINE after a Probe flight (Present, time-up frame): a drag orbits the subject (it stays put on screen, distance kept) and the horizon stays level in the up frame (no snap)',
      dr.rotated_deg > 5 && dr.pivot_drift_px < 4 && dr.dist_change < 0.01 && Math.abs(dr.roll_in_frame_after) < 1.5 && dr.max_turn_step_deg < 6, dr);
    // click the person's bead (the birth end of the fiber): the TouchSensor fires and the page flies there from the dragged pose
    const bead = SH.shots.Present.bead, sp = project(bead, p1);
    const nT0 = await p.evaluate(() => camApi.touches.length);
    await p.evaluate(() => camApi.recStart());
    await p.mouse.click(Math.round(sp.x), Math.round(sp.y)); await sleep(500);
    const flying = await p.evaluate(() => camApi.log.slice(-4)); await p.waitForFunction(() => /arrive Present/.test(camApi.log[camApi.log.length - 1] || ''), null, { timeout: 20000 }).catch(() => null); await sleep(300);
    const ctr = await p.evaluate(() => camApi.recStop()), nT1 = await p.evaluate(() => camApi.touches.length);
    const fm = ctr.marks.find(m => /^fly Present/.test(m.label)), am = ctr.marks.find(m => m.label === 'arrive Present');
    const ca = fm ? analyse([{ t: fm.t - 1, p: p1.p, q: p1.q }].concat(ctr.samples), fm.t, am ? am.t : fm.t + 8000, shotEnd(SH, 'Present'), 10) : null;
    metrics.click_fly = { click_px: [Math.round(sp.x), Math.round(sp.y)], touches: nT1 - nT0, log: flying, flight: ca };
    check('click after the drag: the bead (projected from the sensed pose) is hit, the TouchSensor fires', nT1 - nT0 >= 1, metrics.click_fly.click_px);
    check('a pick flies the Probe from the real (user-orbited) pose: no jump at the start (first step < 10% of the path), smooth, lands on the shot', !!ca && ca.first_step_share < 0.1 && ca.jumps === 0 && ca.end_pos_err < 2e-3, ca);
  }

  // ================================================================ control: a rolled shot WITHOUT the up frame snaps on the first drag
  if (ONLY.includes('roll')) {
    await p.evaluate(() => camApi.flyTo('Wide')); await sleep(400);
    await p.evaluate(() => camApi.flyTo('Present', { noFrame: true })); await sleep(600);
    const p0 = await p.evaluate(() => camApi.pose()); await p.evaluate(() => camApi.recStart());
    await drag(p, W * 0.62, H * 0.42, 40, 0, 6);
    const p1 = await p.evaluate(() => camApi.pose()), rt = await p.evaluate(() => camApi.recStop());
    const steps = rt.samples.slice(1).map((s, i) => qang(s.q, rt.samples[i].q));
    const rr = { roll_world_before: +rollDeg(p0.q).toFixed(2), roll_world_after: +rollDeg(p1.q).toFixed(2), max_turn_step_deg: steps.length ? +Math.max(...steps).toFixed(2) : null, frames: steps.length };
    metrics.roll_control = rr;
    check('control: the same rolled shot with the Probe at the root (no up frame): X_ITE straightens the horizon on the first drag (a snap), so rolled shots need the up frame',
      Math.abs(rr.roll_world_before) > 10 && Math.abs(rr.roll_world_after) < 2, rr);
    await shoot(p, 'check-roll-control-after-drag', 'control: rolled shot without the up frame, after a 40 px drag (snapped level)');
  }

  // ================================================================ control: the pocket pages' rig, as written and with the centre fix
  if (ONLY.includes('rig')) {
    for (const fix of [false, true]) {
      await p.evaluate(f => camApi.rigPlunge(f), fix); await sleep(500);
      const p0 = await p.evaluate(() => camApi.pose()); await drag(p, W * 0.55, H * 0.5, 110, 0, 12); const p1 = await p.evaluate(() => camApi.pose());
      const C = [0, 0, 0], s0 = project(C, p0), s1 = project(C, p1);
      const m = { rotated_deg: +deg(qrot(p0.q, [0, 0, -1]), qrot(p1.q, [0, 0, -1])).toFixed(2), centre_drift_px: +Math.hypot(s1.x - s0.x, s1.y - s0.y).toFixed(1),
        dist_to_centre_before: +len(p0.p).toFixed(3), dist_to_centre_after: +len(p1.p).toFixed(3) };
      metrics['rig_' + (fix ? 'fixed' : 'as_written')] = m;
      if (!fix) check('control: the pocket pages\' rig as written (centerOfRotation fixed in the moving rig): after "Plunge in" an EXAMINE drag orbits a point 22 host units behind the pocket, so the pocket centre slides off its spot and the camera leaves the pocket',
        m.centre_drift_px > 40 && Math.abs(m.dist_to_centre_after - m.dist_to_centre_before) > 0.5, m);
      else check('control: the same rig with centerOfRotation kept on the pocket centre as the rig moves: the drag orbits the pocket centre (drift < 4 px, distance kept)', m.rotated_deg > 5 && m.centre_drift_px < 4 && Math.abs(m.dist_to_centre_after - m.dist_to_centre_before) < 0.05, m);
    }
  }

  // ================================================================ native X3D binds: ANIMATE transitions, Viewpoint.navigationInfo, the scriptless Flywheel
  if (ONLY.includes('native')) {
    await p.evaluate(() => camApi.bindNative('Wide', 1.6)); await sleep(2600);
    await p.evaluate(() => camApi.recStart()); const tb = Date.now(); await p.evaluate(() => camApi.bindNative('Crown', 1.6)); await sleep(2800);
    let tr = await p.evaluate(() => camApi.recStop()); let mv = tr.samples.filter((s, i) => i > 0 && len(sub(s.p, tr.samples[i - 1].p)) > 1e-5);
    const nb = analyse(tr.samples, tr.marks[0].t, tr.marks[0].t + 3000, shotEnd(SH, 'Crown'), 10);
    nb.motion_s = mv.length ? +((mv[mv.length - 1].t - tr.marks[0].t) / 1000).toFixed(2) : 0;
    const vs = tr.samples.slice(1).map((s, i) => ({ t: (s.t - tr.marks[0].t) / 1000, v: len(sub(s.p, tr.samples[i].p)) / Math.max(1, s.t - tr.samples[i].t) }));
    const vmax = Math.max(...vs.map(x => x.v)), early = vs.filter(x => x.t < 0.2 * 1.6), late = vs.filter(x => x.t > 0.8 * 1.6 && x.t < 1.6);
    nb.ease = { v_early_over_peak: early.length ? +(Math.max(...early.map(x => x.v)) / vmax).toFixed(2) : null, v_late_over_peak: late.length ? +(Math.max(...late.map(x => x.v)) / vmax).toFixed(2) : null };
    metrics.native_wide_to_crown = nb;
    check('native bind (X3D only): Wide to Crown with NavigationInfo transitionType ANIMATE, transitionTime 1.6: X_ITE eases in and out over ~1.6 s, no jump, ends on the Crown pose',
      nb.jumps === 0 && Math.abs(nb.motion_s - 1.6) < 0.45 && nb.end_pos_err < 0.01 && nb.end_ang_err_deg < 0.2 && nb.ease.v_early_over_peak < 0.8 && nb.ease.v_late_over_peak < 0.8, nb);
    await p.evaluate(() => camApi.recStart()); await p.evaluate(() => camApi.bindNative('EyeToEye', 1.6)); await sleep(2800);
    tr = await p.evaluate(() => camApi.recStop());
    const ne = analyse(tr.samples, tr.marks[0].t, tr.marks[0].t + 2600, shotEnd(SH, 'EyeToEye'), 10); metrics.native_crown_to_eye = ne;
    check('native bind into a rolled shot (Crown to EyeToEye, its Viewpoint inside its up frame Transform): smooth, no jump, ends on the EyeToEye pose', ne.jumps === 0 && ne.end_pos_err < 0.01 && ne.end_ang_err_deg < 0.2, ne);
    await p.evaluate(() => camApi.recStart()); await p.evaluate(() => camApi.bindNative('Inside')); await sleep(3600);
    tr = await p.evaluate(() => camApi.recStop()); mv = tr.samples.filter((s, i) => i > 0 && len(sub(s.p, tr.samples[i - 1].p)) > 1e-5);
    const pin = await p.evaluate(() => camApi.pose());
    const inside = { motion_s: mv.length ? +((mv[mv.length - 1].t - tr.marks[0].t) / 1000).toFixed(2) : 0, nav_after: pin.nav, bound: pin.bound };
    metrics.native_inside_navinfo = inside;
    check('Viewpoint.navigationInfo (X3D 4.0): binding Inside also binds its NavigationInfo (FLY, NavFly)', /^FLY NavFly/.test(inside.nav_after || ''), inside);
    check('note: the transition into Inside uses the NavigationInfo bound BEFORE it (HostNav 1.6 s), not Inside\'s own (NavFly 2.4 s)', Math.abs(inside.motion_s - 1.6) < 0.45, inside);
    await p.evaluate(() => camApi.bindNative('Flywheel', 2.4)); await sleep(3200);
    await p.evaluate(() => camApi.recStart()); await sleep(6000); tr = await p.evaluate(() => camApi.recStop());
    const az = [], rad = [], tt = []; let prev = null, off = 0;
    for (const s of tr.samples) { let a = Math.atan2(s.p[0], s.p[2]); if (prev !== null) { while (a + off - prev > Math.PI) off -= 2 * Math.PI; while (a + off - prev < -Math.PI) off += 2 * Math.PI; } a += off; prev = a; az.push(a); rad.push(Math.hypot(s.p[0], s.p[2])); tt.push(s.t / 1000); }
    const n = az.length, mt = tt.reduce((x, y) => x + y, 0) / n, ma = az.reduce((x, y) => x + y, 0) / n;
    const slope = tt.reduce((acc, t, i) => acc + (t - mt) * (az[i] - ma), 0) / tt.reduce((acc, t) => acc + (t - mt) ** 2, 0);
    const resid = Math.max(...az.map((a, i) => Math.abs(a - (ma + slope * (tt[i] - mt))))) * 180 / Math.PI;
    const fly = { samples: n, rad_per_s: +slope.toFixed(5), expected: +(2 * Math.PI / SH.shots.Flywheel.period_s).toFixed(5), max_residual_deg: +resid.toFixed(3), radius_range: +(Math.max(...rad) - Math.min(...rad)).toFixed(4) };
    metrics.flywheel = fly;
    check('Flywheel, scriptless: a TimeSensor turns the rig that carries the Viewpoint; constant angular speed (one turn in 120 s) and constant radius', n > 10 && Math.abs(Math.abs(slope) - fly.expected) / fly.expected < 0.03 && resid < 0.5 && fly.radius_range < 0.01, fly);
    await shoot(p, 'check-flywheel', 'Flywheel orbit, bound natively');
  }
  const fpsAll = await p.evaluate(() => camApi.fps()); metrics.fps_rothschild = { median: median(fpsAll), min: Math.min(...fpsAll), max: Math.max(...fpsAll), note: 'SwiftShader software GL at 1527 x 923; relative only' };
  const csp = await p.evaluate(() => camApi.csp); await p.close();

  // ================================================================ the other two families: the same grammar from their data
  if (ONLY.includes('families')) {
    for (const fam of ['habsburg', 'darwin_wedgwood']) {
      const o = await open(fam); const ok = !o.st.failed && o.st.pose.p; const FS = o.st.shots;
      check(fam + ': boots with its own pocket and shots', ok, { failed: o.st.failed, bootMs: o.st.bootMs, eye: FS.picked.eye_name, present: FS.picked.present_name });
      for (const s of ['Crown', 'EyeToEye', 'Present']) {
        await o.p.evaluate(n => camApi.flyTo(n), s); await sleep(700);
        const ps = await o.p.evaluate(() => camApi.pose()), e = shotEnd(FS, s);
        check(fam + ': ' + s + ' lands on its computed pose', len(sub(ps.p, e.p)) < 2e-3 && qang(ps.q, e.q) < 0.1, { err: +len(sub(ps.p, e.p)).toFixed(5) });
        await o.p.evaluate(c => { document.getElementById('cap').textContent = c; }, s + ' · ' + (s === 'EyeToEye' ? FS.shots.EyeToEye.why.text + ' (' + FS.shots.EyeToEye.why.grade + ')' : s === 'Present' ? FS.picked.present_name : FS.tour.find(t => t.shot === 'Crown').caption));
        await shoot(o.p, fam + '-' + s, fam + ' ' + s);
      }
      csp.push(...(await o.p.evaluate(() => camApi.csp))); await o.p.close();
    }
  }
  // ================================================================ the same page under a strict copy of the Artifact CSP
  {
    const o = await open(null, true);
    let flew = false; if (!o.st.failed && o.st.pose.p) { flew = await o.p.evaluate(() => camApi.flyTo('Present')); await sleep(400); }
    const viol = (await o.p.evaluate(() => camApi.csp)).concat(csp), known = v => /PT_Sans/.test(v) || /wasm-eval/.test(v);
    const cc = cons.filter(c => c.run === 'csp' && (c.type === 'error' || c.type === 'pageerror')), ours = cc.filter(c => !(/PT_Sans|WebAssembly|wasm|favicon|404 \(Not Found\)/.test(c.text)));
    metrics.csp = { violations: viol, console_errors: cc.map(c => c.text.slice(0, 160)) };
    check('Artifact CSP copy (no unsafe-eval, connect-src self, .x3d as application/xml): the page boots and flies; the only refusals are X_ITE\'s own (its PT Sans UI font, its tangent wasm), as in scene2\'s Artifact gate', !o.st.failed && flew === true && viol.every(known) && ours.length === 0,
      { flew, unknown: viol.filter(v => !known(v)), ours: ours.map(c => c.text.slice(0, 200)), known: viol.filter(known).length });
    await o.p.close();
  }
  await finish();

  async function finish() {
    const mainCons = cons.filter(c => c.run !== 'csp'), errs = mainCons.filter(c => (c.type === 'error' || c.type === 'pageerror' || /shader|compile|GLSL/i.test(c.text)) && !/favicon|404 \(Not Found\)/.test(c.text)), warns = mainCons.filter(c => c.type === 'warning');
    check('console (no CSP): no errors, no page errors, no shader messages, no failed requests (a favicon 404 ignored)', errs.length === 0 && bad.length === 0, { errs: errs.slice(0, 8), bad: bad.slice(0, 8), warnings: warns.length });
    // lookgates: a frame is not black
    let look = null; try { look = execFileSync('python3', ['-I', path.join(ROOT, 'gates', 'lookgates.py')].concat(frames.map(f => path.join(HYPER, f.file))), { encoding: 'utf8' }); } catch (e) { look = 'lookgates failed: ' + String(e.stdout || e).slice(0, 800); }
    check('lookgates.py: every frame is not black', !/black|fail/i.test(look.replace(/not black|nonblack/gi, '')), look.slice(0, 900));
    const out = { by: 'proto/hyper/tools/drive_camera.js', when: new Date().toISOString(), engine: 'X_ITE 16.5.1 (proto/x3d/vendor/x_ite, byte-identical to the npm tarball)', browser: 'Chromium 1243 (Playwright), SwiftShader, 1527 x 923',
      pass, fail, checks, metrics, frames, lookgates: look, console: cons.slice(0, 60), served: [...new Set(served)].sort() };
    fs.writeFileSync(path.join(PROOF, SMOKE ? 'camera-proof-smoke.json' : 'camera-proof.json'), JSON.stringify(out, null, 1));
    console.log('pass', pass, 'fail', fail); await b.close(); srv.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
