// node e2e/requests.js > out/runtime-files.json : every file the page asks the server for while it loads, tours, hovers and opens a deep card (what a published copy must carry)
const L = require('./lib.js');
(async () => {
  const b = await L.launch(), seen = new Set();
  for (const q of ['', '?view=Wide&hover=2338&tier=3', '?view=Inside']) {
    const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
    p.on('requestfinished', r => { const u = new URL(r.url()); if (u.origin === new URL(L.BASE).origin) seen.add(decodeURIComponent(u.pathname.replace(/^\//, ''))); });
    p.on('requestfailed', r => console.error('FAILED', r.url()));
    await p.goto(L.BASE + 'index.html' + q, { waitUntil: 'load' });
    await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 }); await p.waitForTimeout(6000); await p.close();
  }
  await b.close(); console.log(JSON.stringify([...seen].sort(), null, 1));
})().catch(e => { console.error(e); process.exit(1); });
