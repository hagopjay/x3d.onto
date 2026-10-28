// node test/frames.js : the documentation frames (1527 x 923, the size of the owner's stills), X_ITE 16.5.1 on software GL. 1 to 5 and 9 to 12 with UI none, 6 and 13 with UI minimal (tags, rail, scale bar;
// frame 13 hides the page's own fps readout because software GL's number is not a measurement). Frames 9 to 13 are the ladder stops 4 to 7: each waits for the camera to arrive, then 9 s for the lazy files to load and draw.
const { chromium } = require('playwright'), path = require('path');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html', OUT = path.join(__dirname, '..', 'docs', 'frames');
const SHOTS = [['1-face', 0, 'none'], ['2-establishing', -1, 'none'], ['3-ribcage', 1, 'none'], ['4-heart', 2, 'none'], ['5-feather', 7, 'none'], ['7-fan', { pos: [19, -1, 16], look: [21.5, -2.5, 0], fov: 0.9 }, 'none'], ['6-establishing-ui', -1, 'min'],
  ['9-earth', 3, 'none'], ['10-village-orbit', 4, 'none'], ['11-plaza', 5, 'none'], ['12-villager', 6, 'none'], ['13-village-scale-ui', 6, 'min']];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const ui of ['none', 'min']) {
    const p = await b.newPage({ viewport: { width: 1527, height: 923 } });
    await p.goto(BASE + '?ui=' + ui, { waitUntil: 'load' }); await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 }); await p.waitForTimeout(7000);
    for (const [name, stop, u] of SHOTS.filter(s => s[2] === ui)) {
      await p.evaluate(s => typeof s === 'object' ? window.gdApi.flyTo(['x', 'x', s.pos, s.look, s.fov], 0) : window.gdApi.go(s, 0), stop);
      if (stop >= 3) {                                                  // the world stops: wait for the camera, then for the Inlines to load and draw
        await p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-3; }, stop, { timeout: 120000 });
        await p.waitForTimeout(9000);
        if (name.startsWith('13')) await p.evaluate(() => { document.getElementById('hud').style.display = 'none'; });
      } else await p.waitForTimeout(typeof stop === 'object' || stop === -1 ? 11000 : 4500);
      await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86 }); console.log('frame', name);
    }
    await p.close();
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
