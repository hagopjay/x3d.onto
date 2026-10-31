// NODE_PATH=/opt/node-tools/node_modules node hyper/tools/perf_compare.js --a=release/v3 --b=build/v2/artifact [--out=FILE] [--n=24] [--rounds=2]
// Frame times of two release sets of the Dynasty Loom page, side by side, in the same headless Chromium on SwiftShader (software GL), 1527 x 923.
// Each set is served the way the Artifact host does (the page inside a skeleton, .x3d as application/xml). Per family and per quality tier (Fast,
// Ultra) it lands on the Host shot and on the first close stop, freezes the clocks (hyperApi.freeze) and takes the median of hyperApi.bench(n)
// frame intervals (gl.finish each frame). The sets alternate (A, B, A, B) so drift in the machine falls on both. SwiftShader numbers are relative
// only: they rank the two builds on this machine, they are not a GPU's frame rate.
const { chromium } = require('playwright'); const http = require('http'); const fs = require('fs'); const path = require('path');
const ARGV = process.argv.slice(2), arg = (k, d) => (ARGV.find(a => a.startsWith('--' + k + '=')) || '').slice(k.length + 3) || d;
const SETS = { a: path.resolve(arg('a')), b: path.resolve(arg('b')) }, N = +arg('n', 24), ROUNDS = +arg('rounds', 2), W = 1527, H = 923;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.x3d': 'application/xml', '.png': 'image/png', '.webp': 'image/webp', '.ttf': 'font/ttf', '.wasm': 'application/wasm', '.svg': 'image/svg+xml' };
const SK = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>', '</body></html>'];
const serve = dir => new Promise(res => { const s = http.createServer((q, r) => { const u = decodeURIComponent(new URL(q.url, 'http://x').pathname).replace(/^\/+/, '') || 'index.html', f = path.join(dir, u);
  if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); return r.end(); }
  let d = fs.readFileSync(f); if (u === 'index.html') d = Buffer.from(SK[0] + d.toString('utf8') + SK[1]);
  r.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); r.end(d); }); s.listen(0, '127.0.0.1', () => res(s)); });
const sleep = ms => new Promise(r => setTimeout(r, ms)), median = a => { const b = a.slice().sort((x, y) => x - y); return b[Math.floor(b.length / 2)]; };

(async () => {
  const srv = { a: await serve(SETS.a), b: await serve(SETS.b) };
  const br = await chromium.launch({ executablePath: process.env.GEN_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const rows = [];
  for (let round = 0; round < ROUNDS; round++) for (const k of ['a', 'b']) {
    const base = 'http://127.0.0.1:' + srv[k].address().port + '/', man = JSON.parse(fs.readFileSync(path.join(SETS[k], 'hyper-manifest.json'), 'utf8'));
    const p = await br.newPage({ viewport: { width: W, height: H } }); p.setDefaultTimeout(240000);
    await p.goto(base + 'index.html?auto=0&idle=0&tier=fast', { waitUntil: 'load' });
    await p.waitForFunction(() => document.body.dataset.loaded === '1' || document.body.dataset.loaded === 'failed');
    for (const F of man.families) {
      if ((await p.evaluate(() => hyperApi.family)) !== F.key) { await p.evaluate(x => { location.hash = '#' + x.replace(/_/g, '-'); }, F.key); await p.waitForFunction(x => hyperApi.family === x && document.body.dataset.loaded === '1', F.key); }
      const D = JSON.parse(fs.readFileSync(path.join(SETS[k], F.data), 'utf8')), close = D.tour.findIndex((t, i) => i > 0 && /^(CU|MCU)$/.test(D.shots[t.shot].size));
      for (const [where, i] of [['Host', 0], ['close', close]]) {
        await p.evaluate(i => { hyperApi.goStop(i); }, i); await sleep(800);
        await p.waitForFunction(() => !hyperApi.pose().flying, null, { timeout: 120000 }).catch(() => {}); await sleep(1200);
        for (const tier of [0, 2]) {
          const ms = await p.evaluate(async a => { const A = hyperApi; A.setTier(a.tier); A.freeze(0.25); await new Promise(r => setTimeout(r, 500)); const b = await A.bench(a.n); A.unfreeze(); return b.medianMs; }, { tier, n: N });
          rows.push({ set: k, round, family: F.key, where, stop: i, tier: ['fast', 'balanced', 'ultra'][tier], ms });
          console.log(k, round, F.key, where, tier, ms);
        }
      }
    }
    await p.close();
  }
  const keyOf = r => r.family + ' ' + r.where + ' ' + r.tier, keys = [...new Set(rows.map(keyOf))], table = {};
  for (const key of keys) { const a = median(rows.filter(r => r.set === 'a' && keyOf(r) === key).map(r => r.ms)), b = median(rows.filter(r => r.set === 'b' && keyOf(r) === key).map(r => r.ms)); table[key] = { a_ms: a, b_ms: b, ratio: +(b / a).toFixed(3) }; }
  const out = { what: 'median frame interval (ms) per family, shot and tier; SwiftShader, relative only', a: SETS.a, b: SETS.b, chromium: br.version(), viewport: [W, H], n: N, rounds: ROUNDS,
    median_ratio_b_over_a: +median(Object.values(table).map(x => x.ratio)).toFixed(3), table, rows };
  const of = arg('out'); if (of) fs.writeFileSync(of, JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ median_ratio_b_over_a: out.median_ratio_b_over_a, table }, null, 1));
  await br.close(); srv.a.close(); srv.b.close();
})().catch(e => { console.error(e); process.exit(2); });
