// node e2e/frames.js : the frames for the docs and the picture-judge loop, glass kept on, full 1527 x 923 like the owner's stills
const fs = require('fs'), path = require('path'), L = require('./lib.js');
const OUT = path.join(__dirname, 'out', 'frames'); fs.mkdirSync(OUT, { recursive: true });
const VP = { width: 1527, height: 923 };
async function starOf(page, label) { return page.evaluate(l => { const g = window.gobbler; for (let i = 0; i < 2476; i++) { const n = g.node(i); if (n.label === l) { const s = g.screen(i); return { i, x: s.x, y: s.y, vis: s.visible, tier: n.tier }; } } return null; }, label); }
async function hoverTo(p, st, until, ms) {
  await p.mouse.move(3, 460); await p.waitForTimeout(400); await p.mouse.move(st.x + 1, st.y + 1);
  await p.waitForFunction(([i, f]) => { const s = window.gobbler.state(); return s.snap === i && eval(f)(s); }, [st.i, until], { timeout: 20000 });
  await p.waitForTimeout(ms || 900);
}
(async () => {
  const b = await L.launch(); let p;
  // 1 and 2: the same view with UI none, then minimal at rest
  p = await L.open(b, '?ui=none&view=Wide&glass=1', VP); await L.settle(p, 7000, true); await p.screenshot({ path: path.join(OUT, '1-none.png') }); await p.close();
  p = await L.open(b, '?ui=min&view=Wide&glass=1', VP); await L.settle(p, 2500);
  await p.screenshot({ path: path.join(OUT, '2-rest.png') });
  // 3: tooltip with the progress ring part-filled (the card tier is stretched so the frame holds still)
  const shape = await starOf(p, 'Shape'); console.log('shape', JSON.stringify(shape));
  await p.evaluate(() => window.gobbler.dwell({ card: 1e9, deep: 1e9 }));
  await hoverTo(p, shape, '(s)=>s.tier>=1', 600); await p.screenshot({ path: path.join(OUT, '3-tooltip.png') });
  await p.evaluate(() => window.gobbler.dwell({ card: 450, deep: 1200 }));
  // 4: the deep card with the ontology block
  await hoverTo(p, shape, '(s)=>s.open>=0&&s.openTier>=3', 1500); await p.screenshot({ path: path.join(OUT, '4-card-shape.png') });
  console.log(JSON.stringify(await p.evaluate(() => window.gobbler.state().place)));
  // 5: a Finding card at the card tier (a few seconds on a quiet corner first, so the previous card closes)
  await p.keyboard.press('Escape'); await p.mouse.move(3, 460); await p.waitForTimeout(2600);
  const fin = await starOf(p, 'X_ITE renders on demand and starts every scene with blank frames'); console.log('finding', JSON.stringify(fin));
  await p.close();
  p = await L.open(b, '?hover=723&tier=2&glass=1', VP); await L.settle(p, 3000); await p.waitForFunction(() => window.gobbler.state().place, null, { timeout: 30000 }); await p.waitForTimeout(1500);
  await p.screenshot({ path: path.join(OUT, '5-card-finding.png') }); await p.close();
  // 6: the same Shape card on a narrow screen: a bottom sheet
  p = await L.open(b, '?hover=2338&tier=3&glass=1', { width: 600, height: 900 }); await L.settle(p, 3000); await p.waitForFunction(() => window.gobbler.state().place, null, { timeout: 30000 }); await p.waitForTimeout(1500);
  await p.screenshot({ path: path.join(OUT, '6-sheet.png') }); await p.close();
  await b.close(); console.log('frames in', OUT);
})().catch(e => { console.error(e); process.exit(1); });
