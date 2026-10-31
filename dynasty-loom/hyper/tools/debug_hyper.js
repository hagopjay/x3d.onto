// NODE_PATH=/opt/node-tools/node_modules node tools/debug_hyper.js 'QUERY' 'JS expression evaluated after load' ['expr2' ...]  (debug helper; frames to work/debug-N.png)
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const HYPER = path.resolve(__dirname, '..'), OUT = path.join(HYPER, 'out');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': 'application/xml', '.png': 'image/png', '.wasm': 'application/wasm' };
const srv = http.createServer((q, r) => { const u = decodeURIComponent(new URL(q.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html', f = path.join(OUT, u);
  if (!f.startsWith(OUT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  let d = fs.readFileSync(f); if (u === 'index.html') d = Buffer.from('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>' + d + '</body></html>');
  r.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' }); r.end(d); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const vw = process.env.VW ? process.env.VW.split('x').map(Number) : [1527, 923];
  const p = await b.newPage({ viewport: { width: vw[0], height: vw[1] } }); p.setDefaultTimeout(240000);
  p.on('console', m => { if (m.type() !== 'log' || /error|warn/i.test(m.text())) console.log('console', m.type(), m.text().slice(0, 300)); }); p.on('pageerror', e => console.log('pageerror', String(e).slice(0, 300)));
  await p.goto(BASE + 'index.html' + process.argv[2], { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed', null, { timeout: 240000 });
  let n = 0;
  for (let ex of process.argv.slice(3)) {
    if (ex.startsWith('@file ')) ex = fs.readFileSync(ex.slice(6), 'utf8');
    if (ex.startsWith('@shot')) { await p.screenshot({ path: path.join(HYPER, 'work', 'debug-' + (ex.slice(6) || n++) + '.png') }); continue; }
    if (ex.startsWith('@sleep')) { await new Promise(r => setTimeout(r, +ex.slice(7))); continue; }
    try { const v = await p.evaluate('(async () => { return ' + ex + ' })()'); console.log('>', ex.slice(0, 80), '\n ', JSON.stringify(v).slice(0, 2500)); } catch (e) { console.log('ERR', ex.slice(0, 80), String(e).slice(0, 300)); }
  }
  await b.close(); srv.close();
})();
