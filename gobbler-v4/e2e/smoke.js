// node e2e/smoke.js [url-query] [out.png]  : loads the v4 page in full Chromium (SwiftShader), prints errors and state, saves a screenshot
const L = require('./lib.js');
(async () => {
  const q = process.argv[2] || '', out = process.argv[3] || '/tmp/gv4-smoke.png';
  const b = await L.launch(), p = await L.open(b, q, { width: 1527, height: 923 });
  await p.waitForTimeout(6000);
  console.log(JSON.stringify({ errors: p.errs, state: await p.evaluate(() => window.gobbler.state()) }, null, 1));
  await p.screenshot({ path: out }); await b.close();
})().catch(e => { console.error(e); process.exit(1); });
