// NODE_PATH=/opt/node-tools/node_modules node tools/probe_look.js --family=rothschild --stops=1,4 --out=work/r1/probe [--tier=ultra] [--w=1527 --h=923] [--eval=JS] [--serve=DIR] [--ab]
// build 3: --serve serves another built out/ (e.g. a build-2 rebuild for an A/B of the gate); --ab also shoots the frame with the threads hidden
// and prints tools/scene_stats.py --ab (the share of pixels the threads darken), the gate's threadsAddLight in miniature.
// Look-dev probe (build 2): serves out/ the way gate_hyper.js does, flies to tour stops, waits for the selection to settle, freezes the clocks
// at uCycle 0.25 (comparable frames), shoots, and prints lookgates frame_stats of the scene area (the page's safe rect, so the UI panels are
// not counted) plus the clipped-white share. Not a gate: gate_hyper.js is the gate.
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path'); const { execFileSync } = require('child_process');
const arg = (k, d) => { const a = process.argv.find(x => x.startsWith('--' + k + '=')); return a ? a.slice(k.length + 3) : d; };
const HYPER = path.resolve(__dirname, '..'), OUT = path.resolve(HYPER, arg('serve', 'out')), DIR = path.resolve(HYPER, arg('out', 'work/r1/probe'));
const FAM = arg('family', 'rothschild'), STOPS = arg('stops', '1').split(',').map(Number), TIER = arg('tier', 'ultra'), W = +arg('w', 1527), H = +arg('h', 923), EVAL = arg('eval', '');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': 'application/xml', '.png': 'image/png', '.wasm': 'application/wasm', '.woff2': 'font/woff2' };
const SK = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>';
const srv = http.createServer((q, r) => { const u = decodeURIComponent(new URL(q.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html', f = path.join(OUT, u);
  if (!f.startsWith(OUT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(u === 'favicon.ico' ? 204 : 404); return r.end(); }
  let d = fs.readFileSync(f); if (u === 'index.html') d = Buffer.from(SK + d.toString('utf8') + '</body></html>');
  r.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' }); r.end(d); });
(async () => {
  fs.mkdirSync(DIR, { recursive: true });
  await new Promise(r => srv.listen(0, '127.0.0.1', r)); const BASE = 'http://127.0.0.1:' + srv.address().port + '/';
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); p.setDefaultTimeout(240000); const cons = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') cons.push(m.type() + ' ' + m.text().slice(0, 300)); }); p.on('pageerror', e => cons.push('pageerror ' + e));
  await p.goto(BASE + 'index.html?auto=0&idle=0&tier=' + TIER + '#' + FAM.replace(/_/g, '-')); await p.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed');
  console.log('shaders', JSON.stringify(await p.evaluate(() => hyperApi.shaders())));
  for (const i of STOPS) {
    await p.evaluate(i => { hyperApi.goStop(i); }, i); await p.waitForTimeout(1200);
    await p.waitForFunction(() => !hyperApi.pose().flying && !hyperApi.focusBusy(), null, { timeout: 120000 }); await p.waitForTimeout(600);
   const variants = EVAL ? EVAL.split('||') : [''];
   for (const [vi, ev] of variants.entries()) {
    if (ev) console.log('eval', vi, ev.slice(0, 120), JSON.stringify(await p.evaluate(ev)));
    await p.evaluate(() => hyperApi.freeze(0.25)); await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))));
    const info = await p.evaluate(() => ({ shot: hyperApi.data.tour[hyperApi.stop].shot, safe: hyperApi.safeRect(), sel: hyperApi.sel }));
    const file = path.join(DIR, FAM + '-S' + String(i).padStart(2, '0') + '-' + info.shot.replace(/^S\d\d_/, '') + '-' + TIER + (variants.length > 1 ? '-v' + vi : '') + '.png'); await p.screenshot({ path: file });
    if (process.argv.includes('--ab')) {
      const fb = file.replace(/\.png$/, '-B-nothreads.png');
      await p.evaluate(() => { const g = n => hyperApi.browser.currentScene.getImportedNode(n); window.__abFell = g('FiberCore').uFell; g('FiberCore').uFell = -100000; g('GlowSwitch').whichChoice = -1; });
      await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r))))); await p.waitForTimeout(300);
      await p.screenshot({ path: fb });
      await p.evaluate(() => { const g = n => hyperApi.browser.currentScene.getImportedNode(n); g('FiberCore').uFell = window.__abFell; g('GlowSwitch').whichChoice = 0; });
      const S0 = info.safe; console.log('ab', execFileSync(process.env.LOOM_GATE_PYTHON || 'python3', ['-I', path.join(__dirname, 'scene_stats.py'), '--ab', file + '@' + fb + ':' + [S0.x0, S0.y0, S0.x1, S0.y1].map(Math.round).join(',')], { encoding: 'utf8' }).trim());
    }
    await p.evaluate(() => hyperApi.unfreeze());
    const S = info.safe, st = execFileSync(process.env.LOOM_GATE_PYTHON || 'python3', ['-I', path.join(__dirname, 'scene_stats.py'), file + ':' + [S.x0, S.y0, S.x1, S.y1].map(Math.round).join(',')], { encoding: 'utf8' });
    console.log(path.basename(file), st.trim(), 'sel', JSON.stringify({ pick: info.sel.pick, n: info.sel.line.length, bead: info.sel.bead && info.sel.bead.what }));
   }
  }
  console.log('console', JSON.stringify(cons.slice(0, 6)));
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
