// node gobbler-worlds/test/frames.js [ONLY=giza,disco] : frames of the nested worlds (1527 x 923), X_ITE 16.5.1 on software GL (looks only: no speeds).
// Serve the repo root first (python3 -m http.server 8792). Each world stop waits for the camera to arrive, then for its lazy files; console errors are logged.
const { chromium } = require('playwright'), path = require('path'), fs = require('fs');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8792/gobbler-worlds/index.html', OUT = process.env.GD_FRAMES_OUT || path.join(__dirname, '..', 'docs', 'frames');
const SHOTS = [['01-ribcage', 1, 4500], ['02-heart', 2, 4500], ['03-bubbles', { pos: [6.5, -1.2, 6.2], look: [6.5, -2.6, 0.4], fov: 0.95 }, 9000],
  ['10-giza', 'giza', 8000], ['11-disco', 'disco', 8000], ['12-hall', 'hall', 8000], ['13-osiris', 'osiris', 8000],
  ['20-pantheon', 'pantheon', 10000], ['30-materials', 'materials', 8000], ['40-drillfield', 'drillfield', 8000]];
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean), PICK = s => !ONLY.length || ONLY.some(o => s[0].includes(o));
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1527, height: 923 } }), errs = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text().slice(0, 300)); });
  p.on('requestfailed', r => errs.push('FAILED ' + r.url()));
  const t0 = Date.now(); await p.goto(BASE + '?ui=none&seed=0', { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.v4 === '1' && window.gdApi.worlds(), null, { timeout: 170000 }); await p.waitForTimeout(5000);
  console.log('booted', ((Date.now() - t0) / 1000).toFixed(1), 's (software GL, not a speed)');
  const log = [];
  for (const [name, stop, wait] of SHOTS.filter(PICK)) {
    const idx = await p.evaluate(s => {
      if (typeof s === 'object') { window.gdApi.flyTo(['x', 'x', s.pos, s.look, s.fov], 0); return -2; }
      const i = typeof s === 'number' ? s : window.gdApi.views[s]; window.gdApi.go(i, 0); return i;
    }, stop);
    if (idx >= 8) await p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-5; }, idx, { timeout: 120000 });
    const t1 = Date.now(), wid = await p.evaluate(i => { const t = window.gdApi.stops[i]; return t && t[5] && t[5].world; }, idx);
    if (wid) {                                   // the world's lazy files: wait until no new one has arrived for 8 s (at most 150 s), then the shot's own wait
      let n = -1, still = 0;
      for (let k = 0; k < 75 && still < 4; k++) { const m = await p.evaluate(w => performance.getEntriesByType('resource').filter(e => e.name.includes('data/worlds/' + w + '/')).length, wid); still = m === n && m > 0 ? still + 1 : 0; n = m; await p.waitForTimeout(2000); }
    }
    await p.waitForTimeout(wait);
    const info = await p.evaluate(() => { const c = window.gdApi.cam(), w = window.gdApi.worldAt(c.pos); return { pos: c.pos, inside: w ? w.id : null }; });
    const buf = await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86, timeout: 180000 });
    log.push({ name, stop, inside: info.inside, bytes: buf.length, waited_s: (Date.now() - t1) / 1000 }); console.log('frame', name, info.inside, buf.length, 'B');
  }
  const reqs = await p.evaluate(() => performance.getEntriesByType('resource').filter(e => /data\/worlds\//.test(e.name)).map(e => ({ url: e.name.replace(/^.*data\/worlds\//, ''), bytes: e.transferSize, ms: Math.round(e.duration) })));
  fs.writeFileSync(path.join(OUT, 'frames-log.json'), JSON.stringify({ frames: log, world_requests: reqs, console: errs.slice(0, 80) }, null, 1));
  console.log('world files fetched', reqs.length, '; console', errs.length); errs.slice(0, 25).forEach(e => console.log('  ', e));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
