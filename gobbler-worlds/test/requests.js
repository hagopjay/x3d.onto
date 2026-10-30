// node gobbler-worlds/test/requests.js > out/runtime-files.json : every file the worlds page asks the server for while it boots, dives to the village, visits every world stop and turns sound on (what a published copy must carry)
const { chromium } = require('playwright');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8792/gobbler-worlds/index.html', O = new URL(BASE).origin, DIR = new URL('.', BASE).pathname;
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }), seen = new Set();
  const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
  p.on('requestfinished', r => { const u = new URL(r.url()); if (u.origin === O) seen.add(decodeURIComponent(require('path').posix.relative(DIR, u.pathname))); });
  p.on('requestfailed', r => console.error('FAILED', r.url()));
  await p.goto(BASE + '?ui=min', { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.v4 === '1' && window.gdApi.worlds(), null, { timeout: 170000 }); await p.waitForTimeout(4000);
  await p.evaluate(() => window.gdApi.ready());
  const stops = await p.evaluate(() => [3, 4, 5, 6].concat(Object.keys(window.gdApi.views).filter(k => !/^\d/.test(k)).map(k => window.gdApi.views[k]).filter(i => i >= 8)));
  for (const i of [...new Set(stops)]) {
    await p.evaluate(i => window.gdApi.go(i, 0), i);
    await p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-4; }, i, { timeout: 120000 });
    let n = -1, still = 0; for (let k = 0; k < 60 && still < 4; k++) { still = seen.size === n ? still + 1 : 0; n = seen.size; await p.waitForTimeout(2000); }
    console.error('stop', i, seen.size);
  }
  await p.keyboard.press('m'); await p.waitForTimeout(8000);
  await b.close(); console.log(JSON.stringify([...seen].sort(), null, 1));
})().catch(e => { console.error(e); process.exit(1); });
