// debug: X_ITE internals of the Probe around a TELEPORT rebind (read-only peeks, debug only)
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const ROOT = path.resolve(__dirname, '../..'); const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.x3d': 'application/xml', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 900, height: 540 } });
  await p.goto(BASE + 'hyper/proof/camera.html?ui=min&idle=0'); await p.waitForFunction(() => document.body.dataset.loaded === '1');
  const peek = () => p.evaluate(() => { const v = camApi.debugNode('Probe').getValue(), B = document.getElementById('x3d').browser, n = B.activeNavigationInfo;
    const oo = v._orientationOffset.getValue(), po = v._positionOffset.getValue();
    return { off_deg: +(oo.angle * 180 / Math.PI).toFixed(3), posoff: +Math.hypot(po.x, po.y, po.z).toFixed(4), ts_active: v.timeSensor._isActive.getValue(), ts_desc: v.timeSensor._description.getValue(),
      jump: v._jump.getValue(), retain: v._retainUserOffsets.getValue(), nav: n.getNodeName() + ' ' + n.transitionType[0] + ' ' + n.transitionTime, bound: B.activeViewpoint.description, viewer: B.getBrowserOption ? 'x' : '' }; });
  console.log('load          ', JSON.stringify(await peek()));
  await p.evaluate(() => camApi.flyTo('Wide')); await p.waitForTimeout(400); console.log('after Wide    ', JSON.stringify(await peek()));
  await p.evaluate(() => camApi.flyTo('EyeToEye')); console.log('after EyeToEye', JSON.stringify(await peek())); await p.waitForTimeout(800); console.log('  +800ms      ', JSON.stringify(await peek()));
  await p.evaluate(() => camApi.flyTo('Crown')); console.log('after Crown   ', JSON.stringify(await peek())); await p.waitForTimeout(800); console.log('  +800ms      ', JSON.stringify(await peek()));
  // no NavigationInfo rebind at arrival: emulate by binding Probe directly with TELEPORT at the same pose, no frame change
  const r = await p.evaluate(async () => { const sl = ms => new Promise(r => setTimeout(r, ms)), P = camApi.debugNode('Probe'), B = document.getElementById('x3d').browser;
    B.activeNavigationInfo.transitionType = new X3D.MFString('TELEPORT'); P.set_bind = true; await sl(500); const v = P.getValue();
    return { off_after_plain_rebind: +(v._orientationOffset.getValue().angle * 180 / Math.PI).toFixed(3), ts_active: v.timeSensor._isActive.getValue(), ts_desc: v.timeSensor._description.getValue() }; });
  console.log('plain rebind  ', JSON.stringify(r));
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
