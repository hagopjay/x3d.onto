// one-off probe: does X_ITE 16.5.1 bind an IMPORTed Viewpoint from an Inline, and does an IMPORTed ProximitySensor report in pocket units?
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const ROOT = path.resolve(__dirname, '../..'); const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); if (!p.startsWith(ROOT)) { r.writeHead(403); return r.end(); }
  fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 800, height: 450 } }); const cons = [];
  p.on('console', m => cons.push(m.type() + ': ' + m.text().slice(0, 300))); p.on('pageerror', e => cons.push('pageerror ' + e));
  await p.goto(BASE + 'hyper/work/inl/t.html'); await p.waitForFunction(() => window.R.loaded || window.R.err, null, { timeout: 60000 }); await p.waitForTimeout(2500);
  const out = await p.evaluate(async () => {
    const S = window.S, B = window.B, o = {};
    const sl = ms => new Promise(r => setTimeout(r, ms));
    o.active0 = B.activeViewpoint && B.activeViewpoint.description;
    let pv, ps; try { pv = S.getImportedNode('PocketPV2'); o.imported = !!pv; } catch (e) { o.importErr = String(e); }
    try { ps = S.getImportedNode('PocketPS'); const pos = []; ps.addFieldCallback('t', 'position_changed', v => pos.push([v.x, v.y, v.z])); o.psOk = true; window._pos = pos; } catch (e) { o.psErr = String(e); }
    if (pv) { pv.set_bind = true; await sl(1500); o.active1 = B.activeViewpoint && B.activeViewpoint.description; o.isBound = pv.isBound; }
    o.pos = window._pos ? window._pos.slice(-2) : null;
    try { o.vpList = B.getViewpoints ? 'has getViewpoints' : 'n/a'; } catch (e) {}
    return o; });
  console.log(JSON.stringify(out)); console.log(cons.join('\n'));
  await p.screenshot({ path: path.join(ROOT, 'hyper/work/inl/shot.png') });
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
