// NODE_PATH=/opt/node-tools/node_modules node tools/hyper_csp_gate.js [--artifact=DIR (default hyper/out)] [--frames-dir=DIR (default hyper/frames/build-3)]
// The Artifact gate for the dynasty hypersphere, adapted from scene2/tools/artifact_csp_gate.js: it serves hyper/out the way a claude.ai Artifact does,
// as far as this container can copy it. The page fragment goes inside a skeleton like the host's, and every response carries a strict CSP written from
// the Artifact page contract: scripts from 'self', inline and the five CDNs; fetch only from 'self'; fonts only from fonts.gstatic.com; images only
// from 'self', data: and blob:; and no 'unsafe-eval'. .x3d is served as application/xml. The real host's policy is not visible from here, so a pass
// here is Likely there, never Confirmed. It records CSP violations, console messages and failed requests, waits for the page's loaded flag in every
// family (switching family through the #hash), checks that every ComposedShader compiled (a shader the policy refused would be invalid: X_ITE decodes
// the data: ShaderParts in place) and that X_ITE came from the page's own origin, and shoots one desktop frame (light) and one phone frame (dark).
// Writes hyper/csp-gate.json.
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const HERE = path.resolve(__dirname, '..');
const arg = k => (process.argv.find(a => a.startsWith('--' + k + '=')) || '').split('=')[1];
const ART = path.resolve(arg('artifact') || path.join(HERE, 'out')), FR = path.resolve(arg('frames-dir') || path.join(HERE, 'frames', 'build-3'));
const CDNS = 'https://cdnjs.cloudflare.com https://cdn.jsdelivr.net/npm/ https://unpkg.com https://cdn.tailwindcss.com https://code.jquery.com';
const CSP = ["default-src 'none'", "script-src 'self' 'unsafe-inline' " + CDNS, "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  'font-src https://fonts.gstatic.com', "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "media-src 'self' data: blob:"].join('; ');   // copied from scene2/tools/artifact_csp_gate.js
const TYPES = { '.svg': 'image/svg+xml', '.gif': 'image/gif', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.css': 'text/css', '.wasm': 'application/wasm', '.html': 'text/html', '.x3d': 'application/xml', '.json': 'application/json', '.js': 'text/javascript', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.png': 'image/png', '.md': 'text/markdown', '.txt': 'text/plain' };
const SKELETON = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
  '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}',
  'img{max-width:100%}[hidden]{display:none!important}</style></head><body>', '</body></html>'];
const published = new Set(Object.keys(JSON.parse(fs.readFileSync(path.join(ART, 'publish.json'), 'utf8'))));   // serve only what the publish map ships

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
  const out = { csp: CSP, base, served_from: path.relative(HERE, ART), runs: [], pass: true };
  const page = fs.readFileSync(path.join(ART, 'index.html'), 'utf8');
  out.static = { eval_or_function: /\beval\s*\(|new\s+Function\b/.test(page), data_url_fetch: /fetch\(\s*['"]data:/.test(page) };
  for (const run of [{ name: 'desktop-light', viewport: { width: 1527, height: 923 }, scheme: 'light', q: '?tier=fast&idle=0' }, { name: 'phone-dark', viewport: { width: 400, height: 860 }, scheme: 'dark', q: '?idle=0' }]) {
    const ctx = await b.newContext({ viewport: run.viewport, colorScheme: run.scheme, deviceScaleFactor: 1 }), p = await ctx.newPage();
    const r = { name: run.name, console: [], violations: [], failed: [], families: {}, checks: {} };
    await p.addInitScript(() => { window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI)); });
    p.on('console', m => r.console.push(m.type() + ': ' + m.text().slice(0, 240) + (m.location() && m.location().url ? ' @ ' + m.location().url.replace(base, '') : '')));
    p.on('pageerror', e => r.console.push('pageerror: ' + String(e).slice(0, 240)));
    p.on('requestfailed', q => r.failed.push(q.url().replace(base, '') + ' ' + (q.failure() || {}).errorText));
    p.on('response', q => { if (q.status() >= 400) r.failed.push(q.url().replace(base, '') + ' HTTP ' + q.status()); });
    await p.goto(base + run.q, { waitUntil: 'load' });
    await p.waitForFunction(() => window.hyperApi && window.hyperApi.manifest, null, { timeout: 120000 }).catch(() => {});
    const keys = await p.evaluate(() => window.hyperApi.manifest ? window.hyperApi.manifest.families.map(f => f.key) : []).catch(() => []);
    for (const [i, key] of (keys.length ? keys : ['?']).entries()) {
      if (i > 0) await p.evaluate(k => { location.hash = '#' + k.replace(/_/g, '-'); }, key);
      await p.waitForFunction(k => window.hyperApi && (window.hyperApi.family === k && document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed'), key, { timeout: 180000 }).catch(() => {});
      const st = await p.evaluate(() => ({ loaded: document.body.dataset.loaded, fam: hyperApi.family, hash: location.hash, xite: hyperApi.xite, shaders: hyperApi.shaders(), bound: hyperApi.pose().bound, failed: hyperApi.failed || null })).catch(e => ({ error: String(e) }));
      r.families[key] = st;
      if (i === 0) { await new Promise(res => setTimeout(res, 2500)); fs.mkdirSync(FR, { recursive: true }); await p.screenshot({ path: path.join(FR, 'csp-' + run.name + '.png') }); }
    }
    r.violations = await p.evaluate(() => window.__csp);
    const F = Object.values(r.families);
    r.checks.all_loaded = F.length === 3 && F.every(f => f.loaded === '1' && !f.failed);
    r.checks.shaders_compiled = F.every(f => f.shaders && f.shaders.length === 8 && f.shaders.every(s => s.isValid === true));
    r.checks.host_bound = F.every(f => /^Opening/.test(f.bound || ''));
    r.checks.xite_same_origin = F.every(f => f.xite === base + 'x_ite/x_ite.min.js');
    r.checks.hash_routing = Object.entries(r.families).every(([k, f]) => f.hash === '#' + k.replace(/_/g, '-') && f.fam === k);
    // Known and harmless under this strict policy (as in the loom gate): X_ITE's own UI font (PT Sans, for its menus) refused by font-src, and its
    // mikktspace WebAssembly (tangents for normal maps; this scene has none) refused without 'wasm-unsafe-eval'. Listed, not counted as errors.
    const known = c => /PT_Sans|PTSans|wasm|WebAssembly|CompileError/i.test(c) || / @ favicon\.ico$/.test(c);
    r.harmless = r.console.filter(c => /^(error|pageerror)/.test(c) && known(c)).concat(r.violations.filter(known));
    r.checks.no_errors = !r.console.some(c => /^(error|pageerror|warning)/.test(c) && !known(c));
    r.checks.no_unexpected_violations = !r.violations.some(v => !known(v));
    r.checks.no_missing_files = !r.failed.some(f => / HTTP 404$/.test(f));
    r.checks.no_eval_in_our_code = !out.static.eval_or_function && !out.static.data_url_fetch;
    r.pass = Object.values(r.checks).every(Boolean);
    out.pass = out.pass && r.pass; out.runs.push(r);
    console.log((r.pass ? 'PASS ' : 'FAIL ') + run.name + ' ' + JSON.stringify(r.checks));
    if (r.violations.length) console.log('  CSP violations: ' + JSON.stringify([...new Set(r.violations)]));
    if (r.failed.length) console.log('  failed requests: ' + JSON.stringify(r.failed.slice(0, 8)));
    const noisy = r.console.filter(c => !/^(log|debug|info):/.test(c) && !known(c)); if (noisy.length) console.log('  console: ' + JSON.stringify(noisy.slice(0, 8)));
    if (r.harmless.length) console.log('  known, harmless here: ' + r.harmless.length + ' (X_ITE UI font, mikktspace wasm)');
    await ctx.close();
  }
  await b.close(); srv.close();
  fs.writeFileSync(path.join(HERE, 'csp-gate.json'), JSON.stringify(out, null, 1));
  console.log(out.pass ? 'ARTIFACT CSP GATE PASS' : 'ARTIFACT CSP GATE FAIL');
  process.exit(out.pass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
