// debug: commanded vs sensed orientation around a rolled -> level flight
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const ROOT = path.resolve(__dirname, '../..'); const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); });
const qmul = (a, b) => [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0], a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
const qang = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]))) * 180 / Math.PI;
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1000, height: 600 } });
  await p.goto(BASE + 'hyper/proof/camera.html?ui=min&idle=0'); await p.waitForFunction(() => document.body.dataset.loaded === '1');
  for (const seq of [['EyeToEye', 'Crown'], ['Wide', 'Present']]) {
    await p.evaluate(n => camApi.flyTo(n), seq[0]); await p.waitForTimeout(800);
    await p.evaluate(() => camApi.recStart()); await p.evaluate(n => camApi.flyTo(n), seq[1]); await p.waitForTimeout(1500);
    const r = await p.evaluate(() => { const R = camApi.recStop(), P = camApi.debugNode('Probe'), F = camApi.debugNode('ProbeFrame'), o = P.orientation, fr = F.rotation;
      return { R, probeOri: [o.x, o.y, o.z, o.angle], frame: [fr.x, fr.y, fr.z, fr.angle], pose: camApi.pose() }; });
    const cm = r.R.cmds, sm = r.R.samples;
    console.log('==', seq.join(' -> '), 'cmds', cm.length, 'samples', sm.length, 'probe local ori', r.probeOri.map(x => +x.toFixed(4)), 'frame', r.frame.map(x => +x.toFixed(4)), 'frameQ(page)', r.pose.frameQ.map(x => +x.toFixed(4)));
    // for each sample, the nearest earlier command
    const rows = sm.map(s => { const c = cm.filter(c => c.t <= s.t).slice(-1)[0], c2 = cm.filter(c => c.t <= s.t).slice(-2)[0]; return [+(s.t - r.R.t0).toFixed(0), c ? +qang(c.q, s.q).toFixed(2) : null, c2 ? +qang(c2.q, s.q).toFixed(2) : null, c ? +Math.hypot(c.p[0] - s.p[0], c.p[1] - s.p[1], c.p[2] - s.p[2]).toFixed(4) : null]; });
    console.log('t, ang(sensed, last cmd), ang(sensed, cmd before), pos err:', JSON.stringify(rows.slice(0, 6)), '...', JSON.stringify(rows.slice(-6)));
    console.log('marks', JSON.stringify(r.R.marks.map(m => [+(m.t - r.R.t0).toFixed(0), m.label])));
  }
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
