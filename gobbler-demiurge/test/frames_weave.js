// node test/frames_weave.js : frames of the Armenian knot (tools/weave.py) at its start, middle and end, 1527 x 923, X_ITE 16.5.1 on software GL -> docs/frames/weave/
// Each frame is its own page load with ?weaveat=N (the weave starts N seconds in), so the frames do not wait the real minutes. The Loom sways, so a stop's distance to the Sun varies a little between takes.
const { chromium } = require('playwright'), path = require('path');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html', OUT = path.join(__dirname, '..', 'docs', 'frames', 'weave');
const KNOT = { pos: [8.08, -1.65, 7.7], look: [6.5, -2.6, 0.4], fov: 0.8 };              // a free camera on the disc's axis, 7.5 from the heart
const SHOTS = [['1-knot-start', 15, KNOT], ['2-knot-middle', 80, KNOT], ['3-knot-complete', 160, KNOT], ['4-knot-dissolving', 175, KNOT, [0, 1, 0.55]],
  ['5-heart-middle', 90, 2], ['6-heart-complete', 160, 2], ['7-face-complete', 160, 0], ['8-face-border-ring', 330, 0], ['9-knot-twelve-arms', 530, KNOT]];
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean);
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const [name, at, stop, hold] of SHOTS.filter(s => !ONLY.length || ONLY.some(o => s[0].startsWith(o + '-')))) {
    const p = await b.newPage({ viewport: { width: 1527, height: 923 } });
    await p.goto(BASE + '?ui=none&weaveat=' + at, { waitUntil: 'load' });
    await p.waitForFunction(() => document.body.dataset.loaded === '1', null, { timeout: 170000 });
    await p.evaluate(s => typeof s === 'number' ? window.gdApi.go(s, 0) : window.gdApi.flyTo(['x', 'x', s.pos, s.look, s.fov], 0), stop);
    await p.waitForTimeout(5000);
    await p.evaluate(() => { window.gdApi.node('WeaveClock').stopTime = Date.now() / 1000; }); await p.waitForTimeout(400);      // restart the clock here (stop it, then start it at = seconds in):
    await p.evaluate(at => { const c = window.gdApi.node('WeaveClock'); c.stopTime = 0; c.startTime = Date.now() / 1000 - at; }, at);   // a loaded machine can stall for many seconds while the page boots
    if (hold) await p.evaluate(h => { const n = window.gdApi.node; n('WeaveClock').stopTime = Date.now() / 1000;       // a short phase (the dissolve, 10 s) is held still: stop the clock, set the strands' shaders by hand
      setTimeout(() => { for (let j = 0; j < 3; j++) for (let k = 0; k < 4; k++) n('WeaveSh' + j + '_' + k).w = new X3D.SFVec3f(h[0], h[1], h[2]); }, 300); }, hold);
    await p.waitForTimeout(1500);
    let buf, k = 0;
    do { if (k) { console.log('retake', name); await p.waitForTimeout(5000); } buf = await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86 }); } while (buf.length < 90e3 && ++k < 4);   // a near-black frame is a stall, not a picture
    const w = await p.evaluate(() => String(window.gdApi.node('WeaveSh0_0').w));
    console.log('frame', name, buf.length, 'B', 'weave (ornament, laid, shown):', w); await p.close();
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
