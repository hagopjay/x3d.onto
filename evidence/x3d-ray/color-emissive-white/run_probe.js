// Loads <name>.x3d through a one-line page in X_ITE (x_ite/ beside the files, e.g. a link to a vendored copy) in headless Chromium and
// saves frame-<name>.png (measure.py reads the colours). Usage: NODE_PATH=<playwright> node run_probe.js DIR [probe|probe-unlit]
const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const root = process.argv[2], name = process.argv[3] || 'probe';
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split(/[?#]/)[0])); fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); r.end(b); }); });
srv.listen(0, async () => {
  const base = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await (await b.newContext({ viewport: { width: 660, height: 420 } })).newPage(), log = [];
  p.on('console', m => { if (m.type() === 'error') log.push(m.text().slice(0, 160)); });
  await p.route('**/page.html', r => r.fulfill({ contentType: 'text/html', body: '<!doctype html><meta charset="utf-8"><script src="x_ite/x_ite.min.js"></script><x3d-canvas src="' + name + '.x3d" style="width:640px;height:400px" update="auto"></x3d-canvas>' }));
  await p.goto(base + 'page.html'); await p.waitForTimeout(8000);
  const xite = await p.evaluate(() => X3D.getBrowser(document.querySelector('x3d-canvas')).version);
  const clip = await p.evaluate(() => { const r = document.querySelector('x3d-canvas').getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; });
  await p.screenshot({ path: path.join(root, 'frame-' + name + '.png'), clip });
  console.log(JSON.stringify({ name, xite, consoleErrors: log })); await b.close(); srv.close();
});
