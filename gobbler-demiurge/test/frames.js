// node test/frames.js [ONLY=9,10,11 env: just those frames] : the documentation frames (1527 x 923, the size of the owner's stills), X_ITE 16.5.1 on software GL. 1 to 5 and 9 to 12 with UI none, 6 and 13 with UI minimal (tags, rail, scale bar;
// frame 13 hides the page's own fps readout because software GL's number is not a measurement). Frames 9 to 13 are the ladder stops 4 to 7: each waits for the camera to arrive, then 9 s for the lazy files to load and draw.
const { chromium } = require('playwright'), path = require('path');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html', OUT = path.join(__dirname, '..', 'docs', 'frames');
const SHOTS = [['1-face', 0, 'none'], ['2-establishing', -1, 'none'], ['3-ribcage', 1, 'none'], ['4-heart', 2, 'none'], ['5-feather', 7, 'none'], ['7-fan', { pos: [19, -1, 16], look: [21.5, -2.5, 0], fov: 0.9 }, 'none'], ['6-establishing-ui', -1, 'min'],
  ['9-earth', 3, 'none'], ['10-village-orbit', 4, 'none'], ['11-plaza', 5, 'none'], ['12-villager', 6, 'none'], ['13-village-scale-ui', 6, 'min'],
  ['14-fountain', { v: true, pos: [-10.5, -3.0, 2.2], look: [0, 0, 1.2], fov: 0.95 }, 'none'], ['15-villagers', { v: true, pos: [-12.0, 3.0, 1.6], look: [-5.5, 0.5, 1.25], fov: 0.85 }, 'none'],      // 14 and 15: free cameras in village metres (east, north, height above the plaza)
  ['khachkar/1-plaza', 5, 'none'], ['khachkar/2-near', { v: true, pos: [4.2, 6.1, 1.7], look: [5.5, 9.53, 1.55], fov: 0.8 }, 'none'], ['khachkar/3-detail', { v: true, pos: [4.6, 8.0, 2.0], look: [5.5, 9.53, 1.9], fov: 0.75 }, 'none'],
  ['khachkar/4-tag', 5, 'min']];      // the khachkar (tools/blender_khachkar.py, 11 m from the fountain at 60 degrees, its face toward the fountain): the plaza stop, two free cameras, the plaza stop with its tag
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean), PICK = s => !ONLY.length || ONLY.some(o => s[0].startsWith(o + '-') || s[0].startsWith(o + '/'));
(async () => {
  require('fs').mkdirSync(path.join(OUT, 'khachkar'), { recursive: true });
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const ui of ['none', 'min']) {
    const p = await b.newPage({ viewport: { width: 1527, height: 923 } });
    await p.goto(BASE + '?ui=' + ui, { waitUntil: 'load' }); await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 }); await p.waitForTimeout(7000);
    for (const [name, stop, u] of SHOTS.filter(s => s[2] === ui && PICK(s))) {
      const free = typeof stop === 'object' && stop.v;
      await p.evaluate(s => {
        if (typeof s !== 'object') return window.gdApi.go(s, 0);
        if (!s.v) return window.gdApi.flyTo(['x', 'x', s.pos, s.look, s.fov], 0);
        const w = window.gdApi.world(), R = w.r_planet, sag = r => Math.sqrt(Math.max(R * R - r * r, 1)) - R;      // a village point (x east, y north, h up) in scene units, on the curve of the planet
        const at = (x, y, h) => [0, 1, 2].map(i => w.site[i] + (w.east[i] * x + w.north[i] * y + w.up[i] * (h + sag(Math.hypot(x, y)))) * w.scale);
        window.__free = at(...s.pos); window.gdApi.flyTo(['x', 'x', window.__free, at(...s.look), s.fov, { loom: true, up: w.up }], 0);
      }, stop);
      if (free) {                                                       // a free village camera: wait for the pose through the frozen sway, then for the Inlines
        await p.waitForFunction(() => { const c = window.gdApi.cam(), t = window.gdApi.toWorld(window.__free); return c.pos && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-4; }, null, { timeout: 120000 });
        await p.waitForTimeout(9000);
      } else if (stop >= 3) {                                                  // the world stops: wait for the camera, then for the Inlines to load and draw
        await p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-3; }, stop, { timeout: 120000 });
        await p.waitForTimeout(9000);
        if (name.startsWith('13')) await p.evaluate(() => { document.getElementById('hud').style.display = 'none'; });
      } else await p.waitForTimeout(typeof stop === 'object' || stop === -1 ? 11000 : 4500);
      let buf = await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86 });
      for (let k = 0; k < 3 && buf.length < 90e3 && stop !== -1 && !(typeof stop === 'number' && stop < 3); k++) {      // a near-black frame is a stall while an Inline parses, not a picture: wait and retake (the world stops only)
        console.log('retake', name, buf.length, 'B'); await p.waitForTimeout(7000); buf = await p.screenshot({ path: path.join(OUT, name + '.jpg'), type: 'jpeg', quality: 86 });
      }
      console.log('frame', name, buf.length, 'B');
    }
    await p.close();
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
