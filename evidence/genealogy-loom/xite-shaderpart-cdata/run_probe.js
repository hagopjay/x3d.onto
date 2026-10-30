// Loads probe-<name>.x3d in X_ITE 16.5.1 (x_ite/ beside the files: link gobbler-v4/vendor/x_ite from `make v4-data`) in headless Chromium,
// reports ComposedShader.isValid, console errors and requests, and saves frame-<name>.png.
// Usage: NODE_PATH=<playwright> node run_probe.js DIR [raw,prefixed,percent,percent-escape]   (writes result-<names>.json)
const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const root = process.argv[2];
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split(/[?#]/)[0])); fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); r.end(b); }); });
srv.listen(0, async () => {
  const base = 'http://127.0.0.1:' + srv.address().port + '/', out = {};
  const b = await chromium.launch({ ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}), args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const n of (process.argv[3] || 'raw,prefixed').split(',')) {
    const p = await (await b.newContext({ viewport: { width: 520, height: 400 } })).newPage(), log = [], req = [];
    p.on('console', m => { if (m.type() === 'error') log.push(m.text().slice(0, 160)); });
    p.on('request', q => { const u = q.url().replace(base, ''); if (!u.startsWith('x_ite/')) req.push(u.slice(0, 80)); });
    await p.goto(base + 'probe-' + n + '.html'); await p.waitForTimeout(8000);
    const v = await p.evaluate(() => { const B = X3D.getBrowser(document.querySelector('x3d-canvas')); return { xite: B.version, isValid: B.currentScene.getNamedNode('Probe').isValid }; });
    await p.screenshot({ path: path.join(root, 'frame-' + n + '.png') });
    out[n] = { ...v, consoleErrors: log, requests: req };
  }
  console.log(JSON.stringify(out, null, 1)); fs.writeFileSync(path.join(root, 'result-' + (process.argv[3] || 'raw,prefixed').replace(/,/g, '-') + '.json'), JSON.stringify(out, null, 1) + '\n'); await b.close(); srv.close();
});
