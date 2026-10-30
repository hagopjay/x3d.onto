// node gobbler-worlds/test/solo.js NAME 'w=...&pos=...&look=...' WAIT_MS : one frame of a world file on its own (debugging)
const { chromium } = require('playwright'), path = require('path'), fs = require('fs');
(async () => {
  const [name, qs, wait] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1200, height: 720 } }), errs = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.text().slice(0, 240)); });
  await p.goto('http://127.0.0.1:8792/gobbler-worlds/test/solo.html?' + qs); await p.waitForFunction(() => document.body.dataset.ready === '1', null, { timeout: 60000 });
  await p.waitForTimeout(+wait || 20000);
  const out = process.env.GD_SOLO_OUT || path.join(__dirname, '..', 'docs', 'solo'); fs.mkdirSync(out, { recursive: true });
  await p.screenshot({ path: path.join(out, name + '.jpg'), type: 'jpeg', quality: 80 });
  console.log(name, 'errors', errs.length); errs.slice(0, 12).forEach(e => console.log('  ', e)); await b.close();
})();
