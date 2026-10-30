// X_ITE oracle worker: one headless Chromium page with X_ITE loaded once; scenes arrive in batches as JSON lines on stdin,
// results leave as one JSON line per batch on stdout. Files are served from the vendored X_ITE through page.route (no server, no network).
//   in : {"batch": [{"id": "s1", "xml": "<X3D ...>"}, ...], "render": true}
//   out: {"results": [{"id", "warn": [..], "error": [..], "routes": n, "counts": {Type: n}, "exc": null | "..."}], "ms": n}
// XITE_DIR (default gobbler-v4/vendor/x_ite, git-ignored, fetched and hash-checked by `make v4-data`); CHROME optional.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), readline = require('readline');
const REPO = path.resolve(__dirname, '..', '..');
const XD = process.env.XITE_DIR || path.join(REPO, 'gobbler-v4', 'vendor', 'x_ite');
const PAGE = '<!doctype html><html><body><x3d-canvas id="c" style="width:96px;height:96px" splashScreen="false" notifications="false"></x3d-canvas>' +
  '<script src="/x_ite/x_ite.min.js"></script></body></html>';
const ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

// runs inside the page: load each scene, collect what X_ITE says and what it built
async function runBatch({ batch, render }) {
  const br = document.getElementById('c').browser, C = X3D.X3DConstants, out = [];
  const cap = { warn: [], error: [] }, orig = { warn: console.warn, error: console.error };
  console.warn = (...a) => { cap.warn.push(a.map(String).join(' ')); };
  console.error = (...a) => { cap.error.push(a.map(String).join(' ')); };
  const count = (scene) => {
    const counts = {}, seen = new Set();
    const visit = (n) => {
      if (!n || seen.has(n)) return;
      seen.add(n); const t = n.getNodeTypeName(); counts[t] = (counts[t] || 0) + 1;
      for (const fd of n.getFieldDefinitions()) {
        if (fd.accessType !== C.initializeOnly && fd.accessType !== C.inputOutput) continue;
        if (fd.dataType === C.SFNode) { const v = n[fd.name]; if (v) visit(v); }
        else if (fd.dataType === C.MFNode) { const v = n[fd.name]; for (let i = 0; i < v.length; i++) if (v[i]) visit(v[i]); }
      }
    };
    for (let i = 0; i < scene.rootNodes.length; i++) if (scene.rootNodes[i]) visit(scene.rootNodes[i]);
    return counts;
  };
  for (const s of batch) {
    cap.warn = []; cap.error = []; const r = { id: s.id, exc: null }; const t0 = performance.now();
    try {
      // a scene whose load never settles (e.g. waits on a resource) must not stall the batch: 20 s each
      const tmo = (ms) => new Promise((_, rej) => setTimeout(() => rej(new Error('scene load did not settle in ' + ms + ' ms')), ms));
      const scene = await Promise.race([br.createX3DFromString(s.xml), tmo(20000)]);
      if (render) { await Promise.race([br.replaceWorld(scene), tmo(20000)]); await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res))); }
      r.routes = scene.routes.length; r.counts = count(scene);
    } catch (e) { r.exc = String(e && e.message || e).slice(0, 400); }
    r.ms = Math.round(performance.now() - t0); r.warn = cap.warn.slice(0, 20); r.error = cap.error.slice(0, 20); out.push(r);
  }
  if (render) { try { await br.replaceWorld(null); } catch (e) { } }
  console.warn = orig.warn; console.error = orig.error;
  return out;
}

async function newPage(b) {
  const p = await b.newPage();
  await p.route('http://fuzz.local/**', r => {
    const u = new URL(r.request().url());
    if (u.pathname === '/') return r.fulfill({ contentType: 'text/html', body: PAGE });
    const f = path.join(XD, u.pathname.replace(/^\/x_ite\//, ''));
    if (u.pathname.startsWith('/x_ite/') && fs.existsSync(f)) return r.fulfill({ path: f });
    return r.fulfill({ status: 404, body: '' });
  });
  p.pageErrors = []; p.on('pageerror', e => p.pageErrors.push(String(e).slice(0, 300)));
  await p.goto('http://fuzz.local/');
  await p.waitForFunction(() => window.X3D && document.getElementById('c').browser, null, { timeout: 60000 });
  p.version = await p.evaluate(async () => { const br = document.getElementById('c').browser;
    try { await br.loadComponents(br.getProfile('Full')); } catch (e) { }
    return String(br.version || br.getVersion?.() || '?'); });
  return p;
}

(async () => {
  const opts = { args: ARGS }; if (process.env.CHROME) opts.executablePath = process.env.CHROME;
  const b = await chromium.launch(opts);
  let p = await newPage(b);
  process.stdout.write(JSON.stringify({ ready: true, version: p.version, xite_dir: XD }) + '\n');
  const rl = readline.createInterface({ input: process.stdin });
  for await (const line of rl) {
    if (!line.trim()) continue;
    const req = JSON.parse(line), t0 = Date.now(); let results;
    const timeout = req.timeout_ms || 600000;
    try {
      p.pageErrors = [];
      results = await Promise.race([p.evaluate(runBatch, { batch: req.batch, render: !!req.render }),
        new Promise((_, rej) => setTimeout(() => rej(new Error('batch timeout')), timeout))]);
      const pe = p.pageErrors.splice(0);
      if (pe.length && results.length) results[results.length - 1].pageerror = pe;
    } catch (e) {
      // one scene hung or crashed the page: reload and run the batch one scene at a time so the culprit is named
      results = [];
      for (const s of req.batch) {
        try { await p.close(); } catch (e2) { }
        p = await newPage(b);
        try { results.push((await Promise.race([p.evaluate(runBatch, { batch: [s], render: !!req.render }),
          new Promise((_, rej) => setTimeout(() => rej(new Error('scene timeout')), 30000))]))[0]); }
        catch (e3) { results.push({ id: s.id, exc: 'worker: ' + String(e3.message || e3), warn: [], error: [] }); }
      }
    }
    // a load that never settled keeps working in the background and slows every later scene: start a fresh page
    if (results.some(r => r && r.exc && /did not settle/.test(r.exc))) { try { await p.close(); } catch (e) { } p = await newPage(b); }
    process.stdout.write(JSON.stringify({ results, ms: Date.now() - t0 }) + '\n');
  }
  setTimeout(() => process.exit(0), 3000).unref(); await b.close(); process.exit(0);
})().catch(e => { process.stderr.write(String(e && e.stack || e) + '\n'); process.exit(1); });
