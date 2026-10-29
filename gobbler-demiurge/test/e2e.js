// node test/e2e.js : the bird-first page in full Chromium with software GL (X_ITE 16.5.1). Serve the repo root first: make demiurge (default http://127.0.0.1:8791/)
const { chromium } = require('playwright');
const BASE = process.env.GD_BASE || 'http://127.0.0.1:8791/gobbler-demiurge/index.html';
const ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
let pass = 0, fail = 0;
const check = (name, ok, detail) => { (ok ? pass++ : fail++); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + detail : '')); };
async function open(b, q, vp) {
  const p = await b.newPage({ viewport: vp || { width: 1280, height: 800 } }); p.errs = [];
  p.on('pageerror', e => p.errs.push('pageerror ' + e)); p.on('console', m => { if (m.type() === 'error') p.errs.push('console ' + m.text()); });
  p.reqs = []; p.fin = []; p.on('request', r => p.reqs.push(r.url())); p.on('requestfinished', r => p.fin.push(r.url()));
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
  check('boot: scene arrives gzipped and under 370 KB (329 KB before the Mashtots ring, which adds about 25 KB)', boot.bytes.bird > 100e3 && boot.bytes.bird < 370e3, boot.bytes.bird + ' B gz, ' + boot.bytes.birdRaw + ' B raw');
  const early = p.reqs.map(u => new URL(u).pathname);
  check('bird-first: the graph is requested after the scene', early.findIndex(u => /gobbler4-bird/.test(u)) >= 0 && early.findIndex(u => /graph-v3/.test(u)) > early.findIndex(u => /gobbler4-bird/.test(u)));
  await p.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 60000 });
  check('hover layer starts on the graph that loads after the first frame', true);
  const scene = await p.evaluate(() => { const sc = document.getElementById('x3d').browser.currentScene; const n = nm => { try { return !!sc.getNamedNode(nm); } catch (e) { return false; } };
    return { face: n('Face'), est: n('Establishing'), heart: n('Heart'), loom: n('Loom'), wing: n('Wing9'), fan: n('Fan17'), root: n('BlenderRoot'), tender: n('TenderOrbit9'), probe: n('Probe'), bound: document.getElementById('x3d').browser.activeViewpoint.description }; });
  check('scene: Face is a real Viewpoint and is the one bound at load', scene.face && scene.bound === 'Face', JSON.stringify(scene));
  check('scene: Sun, ribcage group, 10 wing primaries, 18 plumes, root, tenders all exist', scene.heart && scene.loom && scene.wing && scene.fan && scene.root && scene.tender);
  const gait = await p.evaluate(async () => { const sc = document.getElementById('x3d').browser.currentScene; const k = sc.getNamedNode('hanim_T0_l_knee'), h = sc.getNamedNode('hanim_T2_r_hip');
    const a = k.rotation.toString() + h.rotation.toString(); await new Promise(r => setTimeout(r, 900)); const b = k.rotation.toString() + h.rotation.toString(); return { moved: a !== b, joints: sc.getNamedNode('hanim_T1').name }; });
  check('tenders: three H-Anim humanoids from Blender are in the scene and their joints are walking', gait.moved && gait.joints === 'Tender', JSON.stringify(gait));
  const tags = await p.evaluate(() => window.gdApi.tags().length); check('tags: 9 fan targets + heart, ribcage, flywheel, tenders, wing, blender + earth, village, tether, villagers, khachkar + the Mashtots ring = 21 anchors', tags === 21, String(tags));
  const ring = await p.evaluate(async () => { const sc = document.getElementById('x3d').browser.currentScene, n = nm => { try { return sc.getNamedNode(nm); } catch (e) { return null; } };
    const R = n('MashtotsRing'), G = n('MashtotsReader'), letters = Array.from({ length: 36 }, (_, i) => !!n('Mashtots' + String(i + 1).padStart(2, '0'))).filter(Boolean).length;
    const a = R.rotation.angle, g = G.translation.toString(); await new Promise(r => setTimeout(r, 3000)); return { letters, a0: a, a1: R.rotation.angle, readerMoved: g !== G.translation.toString() }; });
  check('mashtots: the ring of 36 letters exists, turns (rotation changes over 3 s) and the reading glow walks', ring.letters === 36 && Math.abs(ring.a1 - ring.a0) > 1e-3 && ring.readerMoved, JSON.stringify(ring));
  check('controls: exactly four (UI, Face, Tour, rail)', await p.evaluate(() => document.querySelectorAll('.gv4-pills button').length === 3 && document.querySelectorAll('#gd-rail button').length === 8));
  await p.evaluate(() => window.gdApi.ready());
  check('rail: all eight stops live once world.json has arrived', await p.evaluate(() => [...document.querySelectorAll('#gd-rail button')].map(b => b.classList.contains('off') ? 0 : 1).join('') === '11111111'));
  check('world: Earth, Moon, village and villagers are in the scene but nothing heavy has loaded yet', await p.evaluate(() => { const sc = document.getElementById('x3d').browser.currentScene; const n = nm => { try { return !!sc.getNamedNode(nm); } catch (e) { return false; } };
    return n('EarthWorld') && n('VillageInline') && n('VillagersInline') && n('MoonOrbit') && n('Climber3'); }) && !p.reqs.some(u => /earth-planet|village\.x3d|villagers\.x3d/.test(u)), p.reqs.filter(u => /data\/bird/.test(u)).map(u => u.split('/').pop()).join(','));
  await p.waitForTimeout(6000);
  // fly the ladder
  const pose = () => p.evaluate(() => window.gdApi.cam().pos && window.gdApi.cam().pos.map(x => +x.toFixed(2)));
  const p0 = await pose(); await p.keyboard.press('3'); await p.waitForTimeout(4500); const p3 = await pose();
  check('rail: key 3 flies to the heart (camera near the Sun)', p3 && Math.hypot(p3[0] - 6.5, p3[1] + 2.6, p3[2] - 0.4) < 4.5, JSON.stringify(p0) + ' -> ' + JSON.stringify(p3));
  await p.click('#gd-face'); await p.waitForTimeout(4500); const pf = await pose();
  check('Face chip flies home', pf && Math.hypot(pf[0] - 3, pf[1] + 1.8, pf[2] - 13.2) < 1.5, JSON.stringify(pf));
  // the dive: Earth and Moon, the village from orbit, the plaza, a villager; the sway pauses down there and resumes when you fly out
  const swayAt = () => p.evaluate(() => { const L = document.getElementById('x3d').browser.currentScene.getNamedNode('Loom'); return L.rotation.toString(); });
  const s0 = await swayAt(); await p.waitForTimeout(700); const s1 = await swayAt(); check('sway: the bird sways at the Face (rotation changes)', s0 !== s1, s0 + ' -> ' + s1);
  const arrived = i => p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 2e-6; }, i, { timeout: 90000 });      // the flights run on the wall clock, the Inline parses can stall frames for seconds
  await p.keyboard.press('4'); await arrived(3); await p.waitForTimeout(2500);
  const w4 = await p.evaluate(() => { const c = window.gdApi.cam(), W = window.gdApi.world(), E = window.gdApi.toWorld(W.earth); return { d: Math.hypot(c.pos[0] - E[0], c.pos[1] - E[1], c.pos[2] - E[2]), paused: window.gdApi.swayPaused(), scale: (document.querySelector('#gd-scale b') || {}).textContent }; });
  check('stop 4: the camera is at Earth (0.88 away), the sway is paused, the scale bar speaks village metres', Math.abs(w4.d - 0.88) < 0.02 && w4.paused && /village scale/.test(w4.scale), JSON.stringify(w4));
  check('stop 4: the Earth, cloud and Moon files were requested only now', ['earth-planet', 'earth-clouds', 'earth-moon'].every(n => p.reqs.some(u => u.includes(n))), p.reqs.filter(u => /data\/bird\/(earth|village)/.test(u)).map(u => u.split('/').pop()).join(','));
  const sA = await swayAt(); await p.waitForTimeout(800); const sB = await swayAt(); check('sway: paused down there (rotation holds)', sA === sB, sA + ' ' + sB);
  await p.keyboard.press('5'); await arrived(4); await p.waitForTimeout(2500); const w5 = await p.evaluate(() => { const c = window.gdApi.cam(), W = window.gdApi.world(), S = window.gdApi.toWorld(W.site); return { d: Math.hypot(c.pos[0] - S[0], c.pos[1] - S[1], c.pos[2] - S[2]) }; });
  check('stop 5: the camera is about 0.13 from the village site and the village file has arrived', Math.abs(w5.d - 0.13) < 0.01 && p.fin.some(u => /data\/bird\/village\.x3d/.test(u)), JSON.stringify(w5));
  await p.keyboard.press('7'); await arrived(6); await p.waitForTimeout(2500);
  const w7 = await p.evaluate(async () => { const c = window.gdApi.cam(), W = window.gdApi.world(), S = window.gdApi.toWorld(W.site), U = window.gdApi.dirToWorld(W.up), sc = document.getElementById('x3d').browser.currentScene, inl = sc.getNamedNode('VillagersInline').getValue().getInternalScene(), v = inl.getNamedNode('Villager0'), k = inl.getNamedNode('hanim_T3_l_knee');
    const a = v.rotation.toString() + k.rotation.toString(); await new Promise(r => setTimeout(r, 1500)); const b = v.rotation.toString() + k.rotation.toString();
    const g = sc.getNamedNode('Villagers'); return { air: sc.getNamedNode('AirShader').logDepth, height: (c.pos[0] - S[0]) * U[0] + (c.pos[1] - S[1]) * U[1] + (c.pos[2] - S[2]) * U[2], moved: a !== b, shown: g.visible, bar: document.querySelector('#gd-scale b').textContent }; });
  check('stop 7: about 1.5 m above the plaza (village scale), villagers shown and walking, bar in metres', Math.abs(w7.height / 4e-4 - 1.5) < 0.6 && w7.moved && w7.shown && /m · village scale/.test(w7.bar), JSON.stringify(w7));
  check('stop 7: the atmosphere shader is told the logarithmic depth buffer is on (its depth matches the scene)', w7.air === 1, String(w7.air));
  const shot = await p.screenshot({ type: 'jpeg', quality: 80 }); check('stop 7: the frame is not black (software GL, X_ITE 16.5.1 unpatched)', shot.length > 80e3, shot.length + ' B');
  const onlyWorld = await p.evaluate(() => window.gdApi.tags().filter(t => t.shown).map(t => t.a.id)); check('stop 7: only the village tags show, not the bird\'s', onlyWorld.every(i => ['earth', 'village', 'tether', 'khachkar', 'villagers'].includes(i)), onlyWorld.join(','));
  await p.click('#gd-face'); await arrived(0); await p.waitForTimeout(1500); const sC = await swayAt(); await p.waitForTimeout(900); const sD = await swayAt();
  check('flying back to the Face resumes the sway', sC !== sD && !(await p.evaluate(() => window.gdApi.swayPaused())), sC + ' -> ' + sD);
  const airBack = await p.evaluate(() => document.getElementById('x3d').browser.currentScene.getNamedNode('AirShader').logDepth); check('back at the Face the atmosphere shader is told the logarithmic depth buffer is off', airBack === 0, String(airBack));
  // tour
  await p.click('#btn-tour'); await p.waitForTimeout(500); const lab = await p.evaluate(() => document.getElementById('btn-tour').textContent);
  await p.waitForTimeout(5000); const pt = await pose();
  check('tour: starts, label says Pause tour, camera moves', lab === 'Pause tour' && JSON.stringify(pt) !== JSON.stringify(pf), lab + ' ' + JSON.stringify(pt));
  await p.keyboard.press('t'); await p.waitForTimeout(300); const tl = await p.evaluate(() => document.getElementById('btn-tour').textContent); check('keys: plain t toggles the tour (stops it here)', tl === 'Tour', tl);
  await p.keyboard.press('Shift+T'); await p.waitForTimeout(300); check('keys: Shift+T opens the tuning panel, plain t did not', await p.evaluate(() => !document.getElementById('gv4-tune').hidden));
  await p.keyboard.press('Shift+T'); await p.click('#btn-tour'); await p.waitForTimeout(200);
  await p.click('#btn-tour'); const lab2 = await p.evaluate(() => document.getElementById('btn-tour').textContent); check('tour: second click stops it, label back to Tour', lab2 === 'Tour', lab2);
  check('no page errors', p.errs.length === 0, p.errs.slice(0, 3).join(' | ')); await p.close();
  // the tour dives to the village at 65 s and flies back to the Heart shot (started 64 s in so the test does not wait a minute)
  p = await open(b, '?ui=min&tourat=64'); await p.waitForFunction(() => window.gdApi.ready()); await p.click('#btn-tour');
  await p.waitForFunction(() => { const c = window.gdApi.cam(), W = window.gdApi.world(); if (!window.gdApi.swayPaused() || !c.pos) return false; const S = window.gdApi.toWorld(W.site); return Math.hypot(c.pos[0] - S[0], c.pos[1] - S[1], c.pos[2] - S[2]) < 0.2; }, null, { timeout: 120000, polling: 250 });
  const td = await p.evaluate(() => { const c = window.gdApi.cam(), W = window.gdApi.world(), S = window.gdApi.toWorld(W.site); return { dSite: Math.hypot(c.pos[0] - S[0], c.pos[1] - S[1], c.pos[2] - S[2]), paused: window.gdApi.swayPaused(), label: document.getElementById('btn-tour').textContent }; });
  check('tour: dives to the village (camera within 0.2 of the site, sway paused, tour still on)', td.paused && td.dSite < 0.2 && td.label === 'Pause tour', JSON.stringify(td));
  await p.waitForFunction(() => !window.gdApi.swayPaused(), null, { timeout: 60000 }); await p.waitForTimeout(3000);
  const tb = await p.evaluate(() => { const c = window.gdApi.cam(); return { dSun: Math.hypot(c.pos[0] - 6.5, c.pos[1] + 2.6, c.pos[2] - 0.4), label: document.getElementById('btn-tour').textContent }; });
  check('tour: comes back out to the Heart shot and carries on (sway running, tour still on)', tb.dSun < 8 && tb.label === 'Pause tour', JSON.stringify(tb));
  check('tour dive: no page errors', p.errs.length === 0, p.errs.slice(0, 3).join(' | ')); await p.close();
  // sound: silent to begin with, M starts it, the mix follows the camera (equal power), the heart thumps on the tape, M mutes; a missing bed fails soft
  p = await open(b, '?ui=min'); await p.evaluate(() => window.gdApi.ready());
  const hint = await p.evaluate(() => document.getElementById('gv4-hint').textContent);
  check('sound: silent to begin with (no context, no audio file requested) and the hint line names M', (await p.evaluate(() => window.gdApi.sound())).ctx === 'none' && !p.reqs.some(u => /assets\/audio|heart\.json/.test(u)) && /M for sound/.test(hint), hint);
  await p.keyboard.press('m'); await p.waitForFunction(() => { const s = window.gdApi.sound(); return s.on || s.error; }, null, { timeout: 60000 });
  let sn = await p.evaluate(() => window.gdApi.sound());
  check('sound: M starts it (context running, both beds decoded, the beat tape read) and a toast says so', sn.on && sn.ctx === 'running' && sn.beds === 2 && sn.beats > 20 && await p.evaluate(() => document.querySelector('.gd-toast.on') !== null), JSON.stringify(sn));
  await p.waitForTimeout(5000); sn = await p.evaluate(() => window.gdApi.sound());
  check('sound: at the Face the cosmos bed plays alone and the heart thumps on the tape (about two thumps a second)', sn.gain.cosmos > 0.95 && sn.gain.village < 0.01 && sn.thumps >= 6 && sn.heart > 0.2, JSON.stringify(sn.gain) + ' thumps ' + sn.thumps);
  const stopAt = i => p.waitForFunction(i => { const c = window.gdApi.cam(), t = window.gdApi.stopWorld(i); return c.pos && t && Math.hypot(c.pos[0] - t[0], c.pos[1] - t[1], c.pos[2] - t[2]) < 1e-3; }, i, { timeout: 120000 });
  await p.evaluate(() => window.gdApi.go(4, 0)); await stopAt(4); await p.waitForTimeout(3500); sn = await p.evaluate(() => window.gdApi.sound());
  check('sound: from orbit the two beds cross at equal power (cos squared plus sin squared is 1) and the heart is fading', Math.abs(sn.gain.cosmos ** 2 + sn.gain.village ** 2 - 1) < 0.03 && sn.gain.village > sn.gain.cosmos && sn.heart < 0.5, JSON.stringify(sn.gain));
  await p.evaluate(() => window.gdApi.go(5, 0)); await stopAt(5); await p.waitForTimeout(3500); sn = await p.evaluate(() => window.gdApi.sound()); const th = sn.thumps; await p.waitForTimeout(2500);
  check('sound: in the plaza only the village bed is heard and the heart is silent (no thump even scheduled)', sn.gain.village > 0.99 && sn.gain.cosmos < 0.02 && sn.gain.heart < 0.001 && (await p.evaluate(() => window.gdApi.sound())).thumps === th, JSON.stringify(sn.gain));
  await p.keyboard.press('m'); await p.waitForTimeout(3000); sn = await p.evaluate(() => window.gdApi.sound());
  check('sound: M again mutes it and the context is suspended', !sn.on && sn.ctx === 'suspended' && await p.evaluate(() => document.documentElement.dataset.sound === 'off'), JSON.stringify({ on: sn.on, ctx: sn.ctx }));
  check('sound: no page errors', p.errs.length === 0, p.errs.slice(0, 3).join(' | ')); await p.close();
  p = await b.newPage(); p.errs = []; p.on('pageerror', e => p.errs.push(String(e))); await p.route('**/assets/audio/village.m4a', r => r.fulfill({ status: 404, body: 'no' })); await p.goto(BASE + '?ui=min', { waitUntil: 'load' });
  await p.waitForFunction(() => document.body.dataset.loaded === '1', null, { timeout: 170000 }); await p.keyboard.press('m'); await p.waitForFunction(() => { const s = window.gdApi.sound(); return s.on || s.error; }, null, { timeout: 60000 });
  sn = await p.evaluate(() => window.gdApi.sound()); const tt = await p.evaluate(() => (document.querySelector('.gd-toast') || {}).textContent);
  check('sound: a missing bed fails soft (stays silent, names the HTTP status in a toast, the page carries on)', !sn.on && /HTTP 404/.test(sn.error) && /Sound is off/.test(tt || '') && p.errs.length === 0, sn.error + ' | ' + tt); await p.close();
  p = await open(b, '?ui=none'); await p.keyboard.press('m'); await p.waitForFunction(() => window.gdApi.sound().on, null, { timeout: 60000 });
  check('sound: with ui=none it still plays but shows no toast (stills stay clean)', await p.evaluate(() => document.querySelector('.gd-toast') === null), ''); await p.close();
  // ui none: nothing visible on top of the scene, same boot
  p = await open(b, '?ui=none&view=establishing'); await p.waitForTimeout(3000);
  const vis = await p.evaluate(() => { const g = document.getElementById('gv4'); const shown = [...g.children].filter(c => getComputedStyle(c).display !== 'none' && !c.classList.contains('gv4-peek')); return { ui: g.dataset.ui, shown: shown.length }; });
  check('ui=none: no overlay element is displayed', vis.ui === 'none' && vis.shown === 0, JSON.stringify(vis)); await p.close();
  // the A/B variant: ?look=gold loads the additional file, not the default
  p = await open(b, '?ui=min&look=gold'); const gl = await p.evaluate(() => ({ failed: window.gdBoot.failed, stage: document.getElementById('stage').dataset.stage }));
  check('look=gold: the gold-graph variant file loads and the bird appears', !gl.failed && gl.stage === 'bird' && p.reqs.some(u => /gobbler4-bird-gold\.x3d\.gz/.test(u)) && !p.reqs.some(u => /gobbler4-bird\.x3d\.gz/.test(u)), gl.stage); await p.close();
  // failure path: a missing scene file names the stage and the error
  p = await b.newPage(); await p.route('**/gobbler4-bird.x3d.gz', r => r.fulfill({ status: 404, body: 'no' })); await p.goto(BASE, { waitUntil: 'load' });
  await p.waitForFunction(() => window.gdBoot && window.gdBoot.failed, null, { timeout: 30000 }); const f = await p.evaluate(() => ({ f: window.gdBoot.failed, t: document.getElementById('busy').textContent }));
  check('failure: a 404 shows the stage and the HTTP status, not a fixed message', /fetching the bird/.test(f.t) && /HTTP 404/.test(f.t), f.t.replace(/\n/g, ' / ')); await p.close();
  await b.close(); console.log(`\n${pass} pass, ${fail} fail`); process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
