/* node docs/v4/mock/render.js [port]
 * Renders the Gobbler v4 UI mock states onto the owner's two stills. Needs the mock served over http
 * (python3 -m http.server 8793 --directory docs/v4/mock) so canvas pixel sampling is not tainted.
 * Output: docs/v4/mock/out/<name>.png  (illustrative layout, real card text). */
'use strict';
var path = require('path'), fs = require('fs');
var chromium = require('playwright').chromium;
var port = process.argv[2] || '8793', out = path.join(__dirname, 'out');
var JOBS = [   /* [still, state, card kind, file name] */
  ['B', 'none',  'shape',   'B-1-none'],
  ['B', 'rest',  'shape',   'B-2-rest'],
  ['B', 'min',   'shape',   'B-3-hover'],
  ['B', 'card',  'shape',   'B-4-card-nodetype'],
  ['B', 'zones', 'shape',   'B-5-placement-map'],
  ['A', 'min',   'finding', 'A-3-hover'],
  ['A', 'card',  'finding', 'A-4-card-finding'],
  ['A', 'zones', 'finding', 'A-5-placement-map']
];
(async function () {
  fs.mkdirSync(out, { recursive: true });
  var browser = await chromium.launch(), log = [];
  for (var i = 0; i < JOBS.length; i++) {
    var j = JOBS[i], url = 'http://127.0.0.1:' + port + '/mock.html?still=' + j[0] + '&state=' + j[1] + '&card=' + j[2];
    var page = await browser.newPage({ viewport: { width: 1600, height: 1100 }, deviceScaleFactor: 1 });
    var errs = [];
    page.on('pageerror', function (e) { errs.push(String(e)); });
    page.on('console', function (m) { if (m.type() === 'error') errs.push(m.text()); });
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(function () { return document.querySelector('#cap').innerHTML.length > 20; }, null, { timeout: 15000 });
    await page.waitForTimeout(250);
    var fb = await (await page.$('#frame')).boundingBox(), cb = await (await page.$('#cap')).boundingBox();
    var file = path.join(out, j[3] + '.png');
    await page.screenshot({ path: file, clip: { x: 0, y: 0, width: Math.ceil(fb.width), height: Math.ceil(cb.y + cb.height) } });
    log.push(j[3] + '.png  ' + Math.round(fb.width) + 'x' + Math.ceil(cb.y + cb.height) + '  ' + (fs.statSync(file).size / 1024).toFixed(0) + ' KB' + (errs.length ? '  ERRORS: ' + errs.join(' | ') : ''));
    await page.close();
  }
  await browser.close();
  console.log(log.join('\n'));
})().catch(function (e) { console.error(e); process.exit(1); });
