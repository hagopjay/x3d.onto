// shared helpers for the live-scene tests: full Chromium with SwiftShader (the default headless shell crashes on the Deep scene)
const { chromium } = require('playwright');
const BASE = process.env.GV4_BASE || 'http://127.0.0.1:8795/';
const ARGS = ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
async function launch() { return chromium.launch({ executablePath: process.env.GV4_CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ARGS }); }
async function open(browser, query, vp) {
  const page = await browser.newPage({ viewport: vp || { width: 1280, height: 800 } });
  const errs = []; page.on('pageerror', e => errs.push('pageerror ' + e)); page.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text()); });
  await page.goto(BASE + 'index.html' + (query || ''), { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.dataset.v4 === '1', null, { timeout: 170000 });
  page.errs = errs; return page;
}
// wait for a camera pose and the Intro/Dissolve timers to be idle, then a little more for the frames to settle
async function settle(page, ms, noPose) {      // noPose: UI none installs no camera sensor on purpose
  await page.waitForFunction(np => { const s = window.gobbler.state(); return (np || s.havePose) && !s.gate; }, !!noPose, { timeout: 90000 });
  await page.waitForTimeout(ms == null ? 1500 : ms);
}
async function view(page, name) {
  await page.evaluate(n => { const b = document.querySelector('.vp[data-vp="' + n + '"]'); b.click(); }, name);
  await page.waitForTimeout(400); await settle(page, 1500);
}
const rng = seed => { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
let pass = 0, fail = 0; const results = [];
function check(name, ok, detail) { (ok ? pass++ : fail++); results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + detail : '')); }
function note(name, detail) { results.push({ name, ok: null, detail }); console.log('NOTE ' + name + (detail ? '  ' + detail : '')); }     // a measurement that is reported, not judged
module.exports = { launch, open, settle, view, rng, check, note, results, summary: () => ({ pass, fail }), BASE };
