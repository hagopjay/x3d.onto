// NODE_PATH=/opt/node-tools/node_modules node tools/artifact_csp_gate.js [--artifact=DIR (default scene2/artifact)]
// The Artifact gate for the Dynasty Loom page and its two views (the hypersphere, the default, and the loom): serves scene2/artifact the way a
// claude.ai Artifact does, as far as this container can copy it. The page goes inside a skeleton like the host's, only the files the publish map
// ships are served, .x3d goes out as application/xml, and every response carries a strict CSP written from the Artifact page contract: scripts from
// 'self', inline and the five CDNs; fetch only from 'self'; fonts only from fonts.gstatic.com; images only from 'self', data: and blob:; and no
// 'unsafe-eval'. The real host's policy is not visible from here, so a pass here is Likely there, never Confirmed.
// Per run (desktop 1527 x 923 light, phone 400 x 860 dark) it records CSP violations, console messages and failed requests, and checks:
//   (v2: a light system setting opens on the default look, a dark one on the dark alternate; the run records which.)
//   the hypersphere: the default view; every family loads through the #hash; every ComposedShader compiled (isValid); the Host shot bound; its
//   HTML labels drawn; the loading still shown, then gone; a frame.
//   the loom: #loom switches view and keeps the family; a bare family hash keeps the view, #loom/<family> names both; every family loads; X_ITE drew
//   every label of the bound stop (Text.textBounds > 0); the chrome stays inside the generator's safe area (header above y0, caption strip below
//   y1), so the merged header did not push into the labels; a frame.
//   the switch: the view buttons and the V key; a picked person and the family carry across; the shared fell slider and Tour button drive the
//   active view only. X_ITE from the page's own origin; no eval in our code. Writes scene2/artifact-gate.json and frames/artifact-<view>-<run>.png.
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const HERE = path.resolve(__dirname, '..');
const arg = k => (process.argv.find(a => a.startsWith('--' + k + '=')) || '').split('=')[1];
const ART = path.resolve(arg('artifact') || path.join(HERE, 'artifact'));
const CDNS = 'https://cdnjs.cloudflare.com https://cdn.jsdelivr.net/npm/ https://unpkg.com https://cdn.tailwindcss.com https://code.jquery.com';
const CSP = ["default-src 'none'", "script-src 'self' 'unsafe-inline' " + CDNS, "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  'font-src https://fonts.gstatic.com', "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "media-src 'self' data: blob:"].join('; ');
const TYPES = { '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.gif': 'image/gif', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.css': 'text/css', '.wasm': 'application/wasm', '.html': 'text/html', '.x3d': 'application/xml', '.json': 'application/json', '.js': 'text/javascript', '.ttf': 'font/ttf', '.png': 'image/png', '.md': 'text/markdown', '.txt': 'text/plain' };
const SKELETON = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
  '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}',
  'img{max-width:100%}[hidden]{display:none!important}</style></head><body>', '</body></html>'];
const published = new Set(Object.keys(JSON.parse(fs.readFileSync(path.join(ART, 'publish.json'), 'utf8'))).concat(['index.html']));   // serve only what ships
const sleep = ms => new Promise(r => setTimeout(r, ms));

function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const u = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html';
      const f = path.join(ART, u);
      if (!published.has(u) || !f.startsWith(ART) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404, { 'content-security-policy': CSP }); rsp.end('not found'); return; }
      let body = fs.readFileSync(f);
      if (u === 'index.html') body = Buffer.from(SKELETON.slice(0, 3).join('') + body.toString('utf8') + SKELETON[3]);
      rsp.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-security-policy': CSP, 'cache-control': 'no-store' });
      rsp.end(body);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  const srv = await serve(), base = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: process.env.GEN_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = fs.readFileSync(path.join(ART, 'index.html'), 'utf8');
  const out = { csp: CSP, base, chromium: b.version(), playwright: require('playwright/package.json').version, static: { eval_or_function: /\beval\s*\(|new\s+Function\b/.test(page), data_url_fetch: /fetch\(\s*['"]data:/.test(page) }, runs: [], pass: true };
  fs.mkdirSync(path.join(HERE, 'frames'), { recursive: true });
  for (const run of [{ name: 'desktop-light', viewport: { width: 1527, height: 923 }, scheme: 'light', q: '?idle=0&auto=0&tier=balanced' }, { name: 'phone-dark', viewport: { width: 400, height: 860 }, scheme: 'dark', q: '?idle=0&auto=0' }]) {
    const ctx = await b.newContext({ viewport: run.viewport, colorScheme: run.scheme, deviceScaleFactor: 1 }), p = await ctx.newPage(); p.setDefaultTimeout(180000);
    const r = { name: run.name, console: [], violations: [], failed: [], ok200: [], hyper: {}, loom: {}, switch: {}, checks: {} };
    await p.addInitScript(() => { window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI)); });
    p.on('console', m => r.console.push(m.type() + ': ' + m.text().slice(0, 240) + (m.location() && m.location().url ? ' @ ' + m.location().url.replace(base, '') : '')));
    p.on('pageerror', e => r.console.push('pageerror: ' + String(e).slice(0, 240)));
    p.on('requestfailed', q => r.failed.push(q.url().replace(base, '') + ' ' + (q.failure() || {}).errorText));
    p.on('response', q => { if (q.status() >= 400) r.failed.push(q.url().replace(base, '') + ' HTTP ' + q.status()); else r.ok200.push(q.url().replace(base, '').split('?')[0]); });
    const t0 = Date.now();
    await p.goto(base + run.q, { waitUntil: 'load' });
    const until = (fn, arg, ms = 180000) => p.waitForFunction(fn, arg, { timeout: ms, polling: 100 }).then(() => true).catch(() => false);
    const hyperState = () => p.evaluate(() => ({ view: dynastyApi.view, loaded: document.body.dataset.loaded, fam: hyperApi.family, hash: location.hash, xite: hyperApi.xite, shaders: hyperApi.shaders(),
      bound: hyperApi.pose().bound, labels: hyperApi.labelBoxes().length, failed: hyperApi.failed || null, poster: (e => e.hidden || e.classList.contains('gone'))(document.getElementById('poster')),
      look: document.documentElement.dataset.look || null, ink: !!(window.dynastyApi && dynastyApi.looks && (dynastyApi.looks.themes[document.documentElement.dataset.look] || {}).ink) }));
    const loomState = () => p.evaluate(async () => {   // label text drawn: give X_ITE's font fetch a moment, then read every Label of the bound stop
      const A = window.loomApi; let lab = null;
      for (let t = 0; t < 60; t++) {
        const sw = A.browser.currentScene.getNamedNode(A.view === 'phone' ? 'LabelsPhone' : 'Labels'), g = sw.children[A.stop]; let n = 0, drawn = 0;
        for (let k = 0; k < g.children.length; k++) { const tb = g.children[k].textBounds; n++; if (tb && tb.x > 0 && tb.y > 0) drawn++; }
        lab = { labels: n, drawn }; if (drawn === n && n > 0) break; await new Promise(r => setTimeout(r, 250));
      }
      const rc = id => { const e = id === 'header' ? document.querySelector('header') : document.getElementById(id), q = e.getBoundingClientRect(); return [Math.round(q.left), Math.round(q.top), Math.round(q.right), Math.round(q.bottom)]; };
      const st = A.cards.stops[A.stop], safe = A.view === 'phone' ? st.phone.camera.safe_area : A.cards.layout.safe_area;
      return { view: dynastyApi.view, loaded: document.body.dataset.loaded, fam: A.family, hash: location.hash, xite: A.xite, failed: A.failed || null, stop: A.stop, layout: A.view, labels: lab,
        header: rc('header'), cap: rc('cap'), rail: rc('rail'), safe };
    });
    // ---- the hypersphere: the default view, every family through the #hash
    r.boot_ms = await until(() => window.dynastyApi && window.hyperApi && hyperApi.manifest && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed') ? Date.now() - t0 : null;
    r.default_view = await p.evaluate(() => dynastyApi.view);
    const keys = await p.evaluate(() => hyperApi.manifest ? hyperApi.manifest.families.map(f => f.key) : []).catch(() => []);
    for (const [i, key] of keys.entries()) {
      if (i > 0) { await p.evaluate(k => { location.hash = '#' + k.replace(/_/g, '-'); }, key); await until(k => hyperApi.family === k && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', key); }
      await sleep(i === 0 ? 2500 : 800);
      r.hyper[key] = await hyperState().catch(e => ({ error: String(e) }));
      if (i === 0) await p.screenshot({ path: path.join(HERE, 'frames', 'artifact-hyper-' + run.name + '.png') });
    }
    // ---- to the loom by #loom: the family (the last one) carries; a bare family hash keeps the view; #loom/<family> names both
    const last = keys[keys.length - 1];
    await p.evaluate(() => { location.hash = '#loom'; });
    await until(k => window.loomApi && loomApi.family === k && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', last);
    r.switch.by_hash = await loomState().catch(e => ({ error: String(e) }));
    for (const [i, key] of keys.entries()) {
      if (key === last) { r.loom[key] = r.switch.by_hash; continue; }
      await p.evaluate(a => { location.hash = a[1] % 2 ? '#loom/' + a[0].replace(/_/g, '-') : '#' + a[0].replace(/_/g, '-'); }, [key, i]);
      await until(k => loomApi.family === k && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', key);
      await sleep(600);
      r.loom[key] = await loomState().catch(e => ({ error: String(e) }));
      if (i === 0) await p.screenshot({ path: path.join(HERE, 'frames', 'artifact-loom-' + run.name + '.png') });
    }
    const loomFam = await p.evaluate(() => loomApi.family);
    // ---- the shared controls drive the active view only: the fell slider and the Tour button
    r.switch.controls_loom = await p.evaluate(async () => { const f = document.getElementById('fell'), h0 = hyperApi.fell; f.value = 1900; f.dispatchEvent(new Event('input'));
      const t = document.getElementById('tour'); t.click(); await new Promise(r => setTimeout(r, 200)); const on = t.textContent; t.click(); await new Promise(r => setTimeout(r, 200));
      return { loom: loomApi.fell, hyper_untouched: hyperApi.fell === h0, tourOn: on, tourOff: t.textContent, hyperTour: hyperApi.tourState }; });
    // ---- a pick carries across: the same person's card in the other view (and the hypersphere flies to them)
    const who = await p.evaluate(() => { const st = loomApi.cards.stops[loomApi.stop], ids = (st.subject || []).concat(Object.keys(loomApi.cards.people)); return ids.find(id => loomApi.cards.people[id] && hyperApi.data && true) || null; });
    await p.evaluate(id => loomApi.pick(id), who); await sleep(400);
    const cardLoom = await p.evaluate(() => (document.querySelector('#card h2') || {}).textContent || '');
    await p.click('#views button[data-view="hyper"]');
    await until(k => hyperApi.family === k && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', loomFam);
    await until(id => hyperApi.picked === id, who, 30000); await sleep(800);
    r.switch.by_button = await p.evaluate(() => ({ view: dynastyApi.view, fam: hyperApi.family, hash: location.hash, loaded: document.body.dataset.loaded, picked: hyperApi.picked,
      card: (document.querySelector('#card h2') || {}).textContent || '', cardHidden: document.getElementById('card').hidden, loomPicked: loomApi.picked }));
    r.switch.pick = { who, cardLoom };
    r.switch.controls_hyper = await p.evaluate(() => { const f = document.getElementById('fell'), l0 = loomApi.fell; f.value = 1880; f.dispatchEvent(new Event('input'));
      return { hyper: hyperApi.fell, uFell: hyperApi.browser.currentScene.getImportedNode('FiberCore').uFell, loom_untouched: loomApi.fell === l0 }; });
    // ---- the V key
    await p.evaluate(() => { document.activeElement && document.activeElement.blur && document.activeElement.blur(); hyperApi.clear(); });
    await p.keyboard.press('v'); await until(() => dynastyApi.view === 'loom' && document.body.dataset.loaded === '1', null, 60000);
    r.switch.by_key = await p.evaluate(() => ({ view: dynastyApi.view, fam: loomApi.family, hash: location.hash, loaded: document.body.dataset.loaded, canvases: [...document.querySelectorAll('x3d-canvas')].map(c => c.id + (c.hidden ? ':hidden' : ':shown')) }));
    r.violations = await p.evaluate(() => window.__csp);
    // ---- checks
    const H = Object.values(r.hyper), L = Object.values(r.loom), S = r.switch;
    r.checks.hyper_default_view = r.default_view === 'hyper';
    r.checks.hyper_all_loaded = H.length === 3 && H.every(f => f.loaded === '1' && !f.failed);
    r.checks.hyper_shaders_compiled = H.every(f => f.shaders && f.shaders.length === 8 && f.shaders.every(s => s.isValid === true));
    r.checks.hyper_host_bound = H.every(f => /^Opening/.test(f.bound || ''));
    r.checks.hyper_labels_drawn = H.every(f => f.labels > 0);
    r.checks.hyper_hash_routing = Object.entries(r.hyper).every(([k, f]) => f.hash === '#' + k.replace(/_/g, '-') && f.fam === k && f.view === 'hyper');
    // v2: an ink look (light ground) loads on its own ground and never fetches the dark loading still; a dark look shows it, then lets it go
    r.checks.loading_still_shown_then_gone = !!H[0] && H[0].poster === true && (H[0].ink ? !r.ok200.some(u => /^poster-/.test(u)) : r.ok200.some(u => /^poster-(wide|tall)-plate\.webp$/.test(u)));
    r.checks.loom_all_loaded = L.length === 3 && L.every(f => f.loaded === '1' && !f.failed && f.view === 'loom');
    r.checks.loom_labels_drawn = L.every(f => f.labels && f.labels.drawn === f.labels.labels && f.labels.labels > 0);
    r.checks.loom_hash_routing = S.by_hash && S.by_hash.fam === last && S.by_hash.hash === '#loom/' + last.replace(/_/g, '-') && Object.entries(r.loom).every(([k, f]) => f.fam === k && f.hash === '#loom/' + k.replace(/_/g, '-'));
    r.checks.loom_chrome_inside_safe_area = L.every(f => f.header[3] <= f.safe.y0 && Math.min(f.cap[1], f.layout === 'phone' && f.rail[3] > 0 ? f.rail[1] : 1e9) >= f.safe.y1);   // v2 phone UI: no rail (the caption has previous and next)
    r.checks.view_button_carries_family_and_pick = S.by_button && S.by_button.view === 'hyper' && S.by_button.fam === loomFam && S.by_button.hash === '#' + loomFam.replace(/_/g, '-') && S.by_button.loaded === '1' &&
      S.by_button.picked === who && !S.by_button.cardHidden && S.by_button.card.length > 0 && S.by_button.card === S.pick.cardLoom && !S.by_button.loomPicked;
    r.checks.view_key = S.by_key && S.by_key.view === 'loom' && S.by_key.fam === loomFam && S.by_key.loaded === '1' && S.by_key.hash === '#loom/' + loomFam.replace(/_/g, '-') && S.by_key.canvases.length === 2 && S.by_key.canvases.includes('x3d-hyper:hidden') && S.by_key.canvases.includes('x3d-loom:shown');
    r.checks.shared_controls_drive_the_active_view = S.controls_loom && S.controls_loom.loom === 1900 && S.controls_loom.hyper_untouched && /❚❚/.test(S.controls_loom.tourOn) && /▸/.test(S.controls_loom.tourOff) &&
      S.controls_hyper && S.controls_hyper.hyper === 1880 && Math.abs(S.controls_hyper.uFell - 1880) < 1e-3 && S.controls_hyper.loom_untouched;
    r.checks.xite_same_origin = H.concat(L).every(f => f.xite === base + 'x_ite/x_ite.min.js');
    // Known and harmless under this strict policy: X_ITE's own UI font (PT Sans, for its menus) refused by font-src, and its mikktspace WebAssembly
    // (tangents for normal maps; neither scene has any) refused without 'wasm-unsafe-eval'. Listed in the result, not counted as errors.
    const known = c => /PT_Sans|PTSans|wasm|WebAssembly|CompileError/i.test(c) || / @ favicon\.ico$/.test(c);
    r.harmless = r.console.filter(c => /^(error|pageerror)/.test(c) && known(c)).concat(r.violations.filter(known));
    r.checks.no_errors_or_warnings = !r.console.some(c => /^(error|pageerror|warning)/.test(c) && !known(c));
    r.checks.no_unexpected_violations = !r.violations.some(v => !known(v));
    r.checks.no_missing_files = !r.failed.some(f => / HTTP 404$/.test(f));
    r.checks.no_eval_in_our_code = !out.static.eval_or_function && !out.static.data_url_fetch;
    r.pass = Object.values(r.checks).every(Boolean);
    out.pass = out.pass && r.pass; delete r.ok200; out.runs.push(r);
    console.log((r.pass ? 'PASS ' : 'FAIL ') + run.name + ' (boot ' + r.boot_ms + ' ms) ' + JSON.stringify(r.checks));
    if (!r.pass) console.log('  hyper ' + JSON.stringify(r.hyper).slice(0, 900) + '\n  loom ' + JSON.stringify(r.loom).slice(0, 900) + '\n  switch ' + JSON.stringify(r.switch).slice(0, 1200));
    if (r.violations.length) console.log('  CSP violations: ' + JSON.stringify([...new Set(r.violations)]));
    if (r.failed.length) console.log('  failed requests: ' + JSON.stringify(r.failed.slice(0, 8)));
    const noisy = r.console.filter(c => !/^(log|debug|info):/.test(c) && !known(c)); if (noisy.length) console.log('  console: ' + JSON.stringify(noisy.slice(0, 8)));
    if (r.harmless.length) console.log('  known, harmless here: ' + r.harmless.length + ' (X_ITE UI font, mikktspace wasm)');
    await ctx.close();
  }
  await b.close(); srv.close();
  fs.writeFileSync(path.join(HERE, 'artifact-gate.json'), JSON.stringify(out, null, 1));
  console.log(out.pass ? 'ARTIFACT GATE PASS' : 'ARTIFACT GATE FAIL');
  process.exit(out.pass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
