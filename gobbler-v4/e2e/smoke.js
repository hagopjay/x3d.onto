// node e2e/smoke.js [url-query] [out.png]  : loads the v4 page in full Chromium (SwiftShader), prints errors and state, saves a screenshot
const { chromium } = require('playwright');
const q = process.argv[2] || '', out = process.argv[3] || '/tmp/gv4-smoke.png';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1527, height: 923 } });
  const errs = []; p.on('pageerror', e => errs.push('pageerror ' + e)); p.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text()); });
  const t0 = Date.now();
  await p.goto('http://127.0.0.1:8795/index.html' + q, { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 });
  console.log('started in', Date.now() - t0, 'ms');
  await p.waitForTimeout(6000);
  console.log(JSON.stringify(await p.evaluate(() => window.gobbler.state())));
  await p.screenshot({ path: out });
  console.log('errors:', JSON.stringify(errs.slice(0, 8)));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
