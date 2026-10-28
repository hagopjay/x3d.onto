// node test/frames.js : the documentation frames (1527 x 923, the size of the owner's stills), X_ITE 16.5.1 on software GL. 1 to 5 with UI none, 6 with UI minimal (tags, rail).
const { chromium } = require('playwright'), path = require('path');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html', OUT = path.join(__dirname, '..', 'docs', 'frames');
const SHOTS = [['1-face', 0, 'none'], ['2-establishing', -1, 'none'], ['3-ribcage', 1, 'none'], ['4-heart', 2, 'none'], ['5-feather', 7, 'none'], ['6-establishing-ui', -1, 'min']];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const ui of ['none', 'min']) {
    const p = await b.newPage({ viewport: { width: 1527, height: 923 } });
    await p.goto(BASE + '?ui=' + ui, { waitUntil: 'load' }); await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 }); await p.waitForTimeout(7000);
    for (const [name, stop, u] of SHOTS.filter(s => s[2] === ui)) {
      await p.evaluate(s => window.gdApi.go(s, 0), stop); await p.waitForTimeout(4500);
      await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86 }); console.log('frame', name);
    }
    await p.close();
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
