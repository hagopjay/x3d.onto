// debug: which step leaves a user orientation offset when the Probe's up frame changes?
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const ROOT = path.resolve(__dirname, '../..'); const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 900, height: 540 } });
  await p.goto(BASE + 'hyper/proof/camera.html?ui=min&idle=0'); await p.waitForFunction(() => document.body.dataset.loaded === '1');
  const exp = async (label, mode) => {
    await p.evaluate(() => camApi.flyTo('EyeToEye')); await p.waitForTimeout(700);
    const r = await p.evaluate(async (mode) => {
      const sl = ms => new Promise(r => setTimeout(r, ms));
      const qmul = (a, b) => [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0], a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
      const qang = (a, b) => 2 * Math.acos(Math.min(1, Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]))) * 180 / Math.PI;
      const aa2q = (x, y, z, a) => { const l = Math.hypot(x, y, z) || 1, s = Math.sin(a / 2); return [x / l * s, y / l * s, z / l * s, Math.cos(a / 2)]; };
      const q2aa = q => { let [x, y, z, w] = q; if (w < 0) { x = -x; y = -y; z = -z; w = -w; } w = Math.min(1, w); const a = 2 * Math.acos(w), s = Math.sqrt(Math.max(0, 1 - w * w)); return s < 1e-9 ? [0, 0, 1, 0] : [x / s, y / s, z / s, a]; };
      const P = camApi.debugNode('Probe'), F = camApi.debugNode('ProbeFrame'), pose0 = camApi.pose(), qw = pose0.q;
      const fr = F.rotation, qf = aa2q(fr.x, fr.y, fr.z, fr.angle), o = P.orientation, ql = aa2q(o.x, o.y, o.z, o.angle);
      const out = { before_err_vs_fields: +qang(qmul(qf, ql), qw).toFixed(3) };
      const inner = P.getValue ? P.getValue() : null;
      const offs = () => { try { const v = inner; const oo = v._orientationOffset.getValue(); return +(oo.angle * 180 / Math.PI).toFixed(3); } catch (e) { return 'n/a ' + e; } };
      out.offset_before = offs();
      // new frame = identity, local pose = world pose (the world pose does not change)
      if (mode !== 'none') { F.rotation = new X3D.SFRotation(0, 0, 1, 0); const a = q2aa(qw); P.orientation = new X3D.SFRotation(a[0], a[1], a[2], a[3]); const pp = pose0.p; P.position = new X3D.SFVec3f(pp[0], pp[1], pp[2]); }
      if (mode === 'bind-same-tick') { const n = X3D.getBrowser ? null : null; document.getElementById('x3d').browser.activeNavigationInfo.transitionType = new X3D.MFString('TELEPORT'); P.set_bind = true; }
      await sl(600);
      out.offset_after_change = offs();
      out.err_after_change = +qang(camApi.pose().q, qw).toFixed(3);
      if (mode === 'bind-later') { document.getElementById('x3d').browser.activeNavigationInfo.transitionType = new X3D.MFString('TELEPORT'); P.set_bind = true; await sl(600); out.offset_after_bind = offs(); out.err_after_bind = +qang(camApi.pose().q, qw).toFixed(3); }
      return out;
    }, mode);
    console.log(label, JSON.stringify(r));
  };
  await exp('A frame change, no rebind      ', 'no-bind');
  await exp('B frame change, rebind same tick', 'bind-same-tick');
  await exp('C frame change, rebind 600 ms later', 'bind-later');
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
