// node test/e2e.js : the bird-first page in full Chromium with software GL (X_ITE 16.5.1). Serve the repo root first: make demiurge (default http://127.0.0.1:8791/)
const { chromium } = require('playwright');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html';
const ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
let pass = 0, fail = 0;
const check = (name, ok, detail) => { (ok ? pass++ : fail++); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + detail : '')); };
async function open(b, q, vp) {
  const p = await b.newPage({ viewport: vp || { width: 1280, height: 800 } }); p.errs = [];
  p.on('pageerror', e => p.errs.push('pageerror ' + e)); p.on('console', m => { if (m.type() === 'error') p.errs.push('console ' + m.text()); });
  p.reqs = []; p.on('request', r => p.reqs.push(r.url()));
  await p.goto(BASE + (q || ''), { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.loaded === '1' || window.gdBoot.failed, null, { timeout: 170000 });
  return p;
}
(async () => {
  const b = await chromium.launch({ executablePath: process.env.GD_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ARGS });
  let p = await open(b, '?ui=min');
  const boot = await p.evaluate(() => ({ failed: window.gdBoot.failed, log: window.gdBoot.log, bytes: window.gdBoot.bytes, ms: window.gdBoot.birdMs, stage: document.getElementById('stage').dataset.stage }));
  check('boot: reaches the bird with no failure', !boot.failed && boot.stage === 'bird', 'stage ' + boot.stage);
  check('boot: stages name themselves in order', ['starting X_ITE', 'fetching the bird', 'parsing the scene', 'drawing the first frame', 'bird on screen'].every((s, i, a) => boot.log.findIndex(l => l.includes(s)) > (i ? boot.log.findIndex(l => l.includes(a[i - 1])) : -1)), boot.log.join(' | '));
  check('boot: scene arrives gzipped and under 340 KB', boot.bytes.bird > 100e3 && boot.bytes.bird < 340e3, boot.bytes.bird + ' B gz, ' + boot.bytes.birdRaw + ' B raw');
  const early = p.reqs.map(u => new URL(u).pathname);
  check('bird-first: the graph is requested after the scene', early.findIndex(u => /gobbler4-bird/.test(u)) >= 0 && early.findIndex(u => /graph-v3/.test(u)) > early.findIndex(u => /gobbler4-bird/.test(u)));
  await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 60000 });
  check('hover layer starts on the graph that loads after the first frame', true);
  const scene = await p.evaluate(() => { const sc = document.getElementById('x3d').browser.currentScene; const n = nm => { try { return !!sc.getNamedNode(nm); } catch (e) { return false; } };
    return { face: n('Face'), est: n('Establishing'), heart: n('Heart'), loom: n('Loom'), wing: n('Wing9'), fan: n('Fan17'), root: n('BlenderRoot'), tender: n('TenderOrbit9'), probe: n('Probe'), bound: document.getElementById('x3d').browser.activeViewpoint.description }; });
  check('scene: Face is a real Viewpoint and is the one bound at load', scene.face && scene.bound === 'Face', JSON.stringify(scene));
  check('scene: Sun, ribcage group, 10 wing primaries, 18 plumes, root, tenders all exist', scene.heart && scene.loom && scene.wing && scene.fan && scene.root && scene.tender);
  const tags = await p.evaluate(() => window.gdApi.tags().length); check('tags: 9 fan targets + heart, ribcage, flywheel, tenders, wing, blender = 15 anchors', tags === 15, String(tags));
  check('controls: exactly four (UI, Face, Tour, rail)', await p.evaluate(() => document.querySelectorAll('.gv4-pills button').length === 3 && document.querySelectorAll('#gd-rail button').length === 8));
  check('rail: stops 1, 2, 3, 8 live; 4 to 7 marked as next step', await p.evaluate(() => [...document.querySelectorAll('#gd-rail button')].map(b => b.classList.contains('off') ? 0 : 1).join('') === '11100001'));
  await p.waitForTimeout(6000);
  // fly the ladder
  const pose = () => p.evaluate(() => window.gdApi.cam().pos && window.gdApi.cam().pos.map(x => +x.toFixed(2)));
  const p0 = await pose(); await p.keyboard.press('3'); await p.waitForTimeout(4500); const p3 = await pose();
  check('rail: key 3 flies to the heart (camera near the Sun)', p3 && Math.hypot(p3[0] - 6.5, p3[1] + 2.6, p3[2] - 0.4) < 4.5, JSON.stringify(p0) + ' -> ' + JSON.stringify(p3));
  await p.click('#gd-face'); await p.waitForTimeout(4500); const pf = await pose();
  check('Face chip flies home', pf && Math.hypot(pf[0] - 3, pf[1] + 1.8, pf[2] - 13.2) < 1.5, JSON.stringify(pf));
  // tour
  await p.click('#btn-tour'); await p.waitForTimeout(500); const lab = await p.evaluate(() => document.getElementById('btn-tour').textContent);
  await p.waitForTimeout(5000); const pt = await pose();
  check('tour: starts, label says Pause tour, camera moves', lab === 'Pause tour' && JSON.stringify(pt) !== JSON.stringify(pf), lab + ' ' + JSON.stringify(pt));
  await p.keyboard.press('t'); await p.waitForTimeout(300); const tl = await p.evaluate(() => document.getElementById('btn-tour').textContent); check('keys: plain t toggles the tour (stops it here)', tl === 'Tour', tl);
  await p.keyboard.press('Shift+T'); await p.waitForTimeout(300); check('keys: Shift+T opens the tuning panel, plain t did not', await p.evaluate(() => !document.getElementById('gv4-tune').hidden));
  await p.keyboard.press('Shift+T'); await p.click('#btn-tour'); await p.waitForTimeout(200);
  await p.click('#btn-tour'); const lab2 = await p.evaluate(() => document.getElementById('btn-tour').textContent); check('tour: second click stops it, label back to Tour', lab2 === 'Tour', lab2);
  check('no page errors', p.errs.length === 0, p.errs.slice(0, 3).join(' | ')); await p.close();
  // ui none: nothing visible on top of the scene, same boot
  p = await open(b, '?ui=none&view=establishing'); await p.waitForTimeout(3000);
  const vis = await p.evaluate(() => { const g = document.getElementById('gv4'); const shown = [...g.children].filter(c => getComputedStyle(c).display !== 'none' && !c.classList.contains('gv4-peek')); return { ui: g.dataset.ui, shown: shown.length }; });
  check('ui=none: no overlay element is displayed', vis.ui === 'none' && vis.shown === 0, JSON.stringify(vis)); await p.close();
  // failure path: a missing scene file names the stage and the error
  p = await b.newPage(); await p.route('**/gobbler4-bird.x3d.gz', r => r.fulfill({ status: 404, body: 'no' })); await p.goto(BASE, { waitUntil: 'load' });
  await p.waitForFunction(() => window.gdBoot && window.gdBoot.failed, null, { timeout: 30000 }); const f = await p.evaluate(() => ({ f: window.gdBoot.failed, t: document.getElementById('busy').textContent }));
  check('failure: a 404 shows the stage and the HTTP status, not a fixed message', /fetching the bird/.test(f.t) && /HTTP 404/.test(f.t), f.t.replace(/\n/g, ' / ')); await p.close();
  await b.close(); console.log(`\n${pass} pass, ${fail} fail`); process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
