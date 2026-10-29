// node test/requests.js > out/runtime-files.json : every file the page asks the server for while it boots, flies down the ladder to a villager, tours and opens a deep card (what a published copy must carry)
const { chromium } = require('playwright');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html', O = new URL(BASE).origin;
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }), seen = new Set();
  for (const q of ['?ui=min', '?ui=min&hover=2338&tier=3']) {
    const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
    p.on('requestfinished', r => { const u = new URL(r.url()); if (u.origin === O) seen.add(decodeURIComponent(new URL('.', BASE).pathname === '/' ? u.pathname : require('path').posix.relative(new URL('.', BASE).pathname, u.pathname))); });
    p.on('requestfailed', r => console.error('FAILED', r.url()));
    await p.goto(BASE + q, { waitUntil: 'load' });
    await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 }); await p.waitForTimeout(5000);
    await p.evaluate(() => { window.gdApi.go(2, 0); window.gdApi.tour(); }); await p.waitForTimeout(8000);
    if (q === '?ui=min') {                                           // fly the ladder down to a villager: the world.json, the five lazy files and anything the dive asks for
      await p.evaluate(() => window.gdApi.tour()); await p.evaluate(() => window.gdApi.ready());
      for (const i of [3, 4, 5, 6]) {
        await p.evaluate(i => window.gdApi.go(i, 0), i);
        await p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-3; }, i, { timeout: 120000 });
        await p.waitForTimeout(6000);
      }
    }
    await p.close();
  }
  await b.close(); console.log(JSON.stringify([...seen].sort(), null, 1));
})().catch(e => { console.error(e); process.exit(1); });
