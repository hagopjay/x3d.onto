#!/usr/bin/env python3
"""Two views, one page: scene2/page/loom.html (the tapestry page, unchanged) + proto/hyper/page/index.html (the dynasty hypersphere page)
-> scene2/page/index.html, the page build_loom_scene.py copies to out/ and tools/make_artifact.py ships. Deterministic, standard library only.

    python3 -I tools/merge_views.py [--check]      (--check: build in memory and compare with page/index.html; exit 1 if they differ)

How the two pages become one, and why:
  * One chrome, two engines. Both pages drive the same elements (header, stop rail, caption strip, card, tag, toast, fell slider) by the same ids,
    and both gates (tools/gate_loom.js, hyper/tools/gate_hyper.js) read them by those ids, so the merged page keeps one copy of each, the union of
    the two pages' markup (every id of either page must be present, or the merge stops). View-only parts carry .only-hyper / .only-loom.
  * Each page's script becomes an engine, copied verbatim except at anchored edits (each anchor must occur exactly once, or the merge stops):
    X_ITE loading, the status line, the loaded flag, the family buttons, the #hash and the shared controls move to a small shell; the engine's
    canvas, keys, resize, frame loop and fps monitor run only while its view is active.
  * Each view has its own x3d-canvas (its own X_ITE browser), made when the view is first opened. The hidden one is display:none, and X_ITE then
    stops rendering it by itself (its IntersectionObserver ends the update loop). Switching back is instant and the tapestry is exactly as it was.
  * CSS (v2): the loom's rules, then one themed style sheet for both views from hyper/themes.py (page_css: DEFAULT_THEME, ALT_THEME and the
    PHONE_UI layer), so the loom's chrome takes the theme's type and palette too; the loom's scene colours stay v3's. The hypersphere page's own
    <style> holds only the theme mark. The look is :root[data-look="<slug>"], switched by the header's quiet toggle (#look-t) and remembered in
    this browser only (localStorage, wrapped: the page works without it). The header's measured height is --header-h (the rail and card sit below).
  * The #hash: #hypersphere and #loom name a view, a family name (#rothschild, #habsburg, #darwin-wedgwood) a family, and #loom/habsburg both;
    the page writes #<family> in the hypersphere (the default view) and #loom/<family> in the loom. Switching view keeps the family, the story
    beat (both tours index the same card stops) and a picked person; a hash naming a view and a family switches to both (v2: v3 kept the old family).
Writes page/index.html and page/merge-receipt.json (sha256 of the inputs, this script and the output; the edits applied)."""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # proto/scene2
PROTO = os.path.dirname(HERE)
LOOM = os.path.join(HERE, 'page', 'loom.html')
HYPER = os.path.join(PROTO, 'hyper', 'page', 'index.html')
OUT = os.path.join(HERE, 'page', 'index.html')
EDITS = []
sys.path.insert(0, os.path.join(PROTO, 'hyper'))
import themes as TH   # noqa: E402  (v2: the look table)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rep(src, old, new, label):
    n = src.count(old)
    if n != 1: raise SystemExit('merge: anchor %s occurs %d times, expected once: %r' % (label, n, old[:90]))
    EDITS.append(label); return src.replace(old, new)


def cut(src, start, end, new, label):        # replace from the start anchor through the end anchor (the first after start), both unique
    if src.count(start) != 1: raise SystemExit('merge: start anchor %s occurs %d times' % (label, src.count(start)))
    a = src.index(start); b = src.find(end, a)
    if b < 0: raise SystemExit('merge: end anchor %s not found' % label)
    EDITS.append(label); return src[:a] + new + src[b + len(end):]


def between(s, a, b, label):
    if s.count(a) != 1 or s.count(b) != 1: raise SystemExit('merge: %s: %r / %r not unique' % (label, a, b))
    return s[s.index(a) + len(a):s.index(b)]


# ---------------------------------------------------------------- CSS: scope the hypersphere's rules under body[data-view="hyper"]
SCOPE = '[data-view="hyper"]'


def css_blocks(s):
    out, i = [], 0
    while True:
        j = s.find('{', i)
        if j < 0:
            if s[i:].strip(): raise SystemExit('merge: CSS tail not understood: %r' % s[i:][:60])
            return out
        depth, k = 1, j + 1
        while depth:
            if s[k] == '{': depth += 1
            elif s[k] == '}': depth -= 1
            k += 1
        out.append((s[i:j].strip(), s[j + 1:k - 1])); i = k


def scope_sel(sel):
    sel = sel.strip()
    if sel in ('*', 'html'): return None
    if sel == 'body': return 'body' + SCOPE
    if sel.startswith('body['): return 'body' + SCOPE + sel[4:]
    if sel.startswith(':root'):
        m = re.match(r'(:root(?:\[[^\]]*\]|:not\([^)]*\))*)(.*)$', sel)
        root, rest = m.group(1), m.group(2)
        return (root + ' ' if root != ':root' else '') + 'body' + SCOPE + rest
    return 'body' + SCOPE + ' ' + sel


def scope_css(css, indent='  '):
    lines = []
    for sel, body in css_blocks(css):
        if sel.startswith('@'):
            lines.append(indent + sel + ' {'); lines.append(scope_css(body, indent + '  ')); lines.append(indent + '}'); continue
        sels = [x for x in (scope_sel(p) for p in sel.split(',')) if x]
        if sels: lines.append(indent + ', '.join(sels) + ' { ' + ' '.join(body.split()) + ' }')
    return '\n'.join(lines)


# ---------------------------------------------------------------- the engines: each page's script, edited at anchors
def loom_engine(js):
    js = re.sub(r"^  var XITE_\w+ = .*\n", '', js, flags=re.M)
    js = rep(js, "  document.body.dataset.ui = q.get('ui') === 'none' ? 'none' : 'full';\n",
             "  var S = window.dynastyApi, VIEW = 'loom', active = function () { return S.view === VIEW; };   /* merge: the shell owns X_ITE, the hash and the shared chrome */\n", 'loom: shell handle')
    js = rep(js, "  var statusEl = $('status');\n", '', 'loom: status element')
    js = rep(js, "function status(s, err) { statusEl.textContent = s || ''; statusEl.hidden = !s; if (err) statusEl.style.color = 'var(--alert)'; log(s); }",
             "function status(s, err) { S.status(VIEW, s, err); log(s); }", 'loom: status')
    js = cut(js, "  // ---- X_ITE: one script from the pinned CDN path", "  })(0);\n", '', 'loom: X_ITE loader to the shell')
    js = rep(js, "  var el = $('x3d'), browser = null,", "  var el = null, browser = null,", 'loom: canvas from the shell')
    js = rep(js, "  function boot() {\n    browser = A.browser = el.browser;\n",
             "  function boot(canvas, o) {\n    el = canvas; browser = A.browser = el.browser; A.xite = S.xite; boot.o = o || {}; wireCanvas();\n", 'loom: boot')
    js = rep(js, "      m.families.forEach(function (f) { var b = document.createElement('button'); b.textContent = f.name; b.dataset.key = f.key; b.setAttribute('role', 'tab'); b.onclick = function () { loadFamily(f.key, 0); }; nav.appendChild(b); });\n",
             "      S.setFamilies(m.families);\n", 'loom: family buttons')
    js = rep(js, "      var want = q.get('family') || hashFamily(); loadFamily(m.families.some(function (f) { return f.key === want; }) ? want : m.families[0].key, +(q.get('stop') || 0));\n",
             "      var want = S.family, o = boot.o; loadFamily(m.families.some(function (f) { return f.key === want; }) ? want : m.families[0].key, o.stop != null ? o.stop : o.cardStop != null ? o.cardStop : 0, o.pick);\n",
             'loom: first family')
    js = cut(js, "  function hashFamily() {", "  });\n",
             "  function hashFamily(k) { if (manifest && k !== A.family && k !== A.loading && manifest.families.some(function (f) { return f.key === k; })) loadFamily(k, 0); }   /* the shell reads the #hash */\n",
             'loom: hash to the shell')
    js = rep(js, "function fail(e) { A.failed = String(e && e.message || e); document.body.dataset.loaded = 'failed';", "function fail(e) { A.failed = String(e && e.message || e); S.loaded(VIEW, 'failed');", 'loom: fail flag')
    js = rep(js, "  function loadFamily(key, stopIndex) {\n    stopTour(); clearPick(); document.body.dataset.loaded = '0';",
             "  function loadFamily(key, stopIndex, pickId) {\n    stopTour(); clearPick(); S.loaded(VIEW, '0');", 'loom: loading flag')
    js = rep(js, "    var h = '#' + key.replace(/_/g, '-'); if (location.hash !== h) location.hash = h;\n", "    S.noteFamily(VIEW, key);\n", 'loom: hash write')
    m = re.search(r"^      (\$\('sub'\)\.textContent = C\.name .*;)\n", js, flags=re.M)
    if not m: raise SystemExit('merge: loom sub line not found')
    subline = m.group(1); js = rep(js, m.group(0), "      subLine();\n", 'loom: sub line to a function')
    js = rep(js, "status(''); A.ready = true; document.body.dataset.loaded = '1'; }); });",
             "status(''); A.ready = true; if (pickId && C.people[pickId]) pick(pickId); S.loaded(VIEW, '1'); }); });", 'loom: loaded flag')
    js = rep(js, "  $('prev').onclick = function () { stopTour(); step(-1); }; $('next').onclick = function () { stopTour(); step(1); }; $('tour').onclick = toggleTour;",
             "  S.on(VIEW, 'prev', 'click', function () { stopTour(); step(-1); }); S.on(VIEW, 'next', 'click', function () { stopTour(); step(1); }); S.on(VIEW, 'tour', 'click', toggleTour);", 'loom: shared buttons')
    js = rep(js, "  $('fell').oninput = function () { setFell(+this.value); };", "  S.on(VIEW, 'fell', 'input', function () { setFell(+this.value); });", 'loom: shared fell')
    js = rep(js, "  el.addEventListener('pointermove', function (e) { mouse = [e.clientX, e.clientY]; if (!over) $('tag').hidden = true; });",
             "  function wireCanvas() { el.addEventListener('pointermove', function (e) { mouse = [e.clientX, e.clientY]; if (!over) $('tag').hidden = true; }); }", 'loom: canvas listener')
    js = rep(js, "    if (e.metaKey || e.ctrlKey || e.altKey || !C) return;", "    if (e.metaKey || e.ctrlKey || e.altKey || !C || !active()) return;", 'loom: keys while active')
    js = rep(js, "    if (!C || A.stop < 0) return;\n", "    if (!active() || !C || A.stop < 0) return;\n", 'loom: resize while active')
    tail = ("  A.bindStop = bindStop; A.pick = pick; A.clear = clearPick; A.setFell = setFell; A.loadFamily = loadFamily; A.ladder = ladder; A.nearest = nearest;\n")
    js = rep(js, tail, tail + """
  // ---- merge: the engine's side of the view switch (the shell calls these; o = { family, stop, cardStop, pick })
  function subLine() { %s }
  function activate(o) {
    if (!manifest || !C) return;                                   /* still booting: boot() reads the shell's family */
    var k = o.family && manifest.families.some(function (f) { return f.key === o.family; }) ? o.family : A.family;
    if (k !== A.family) { loadFamily(k, o.cardStop != null ? o.cardStop : 0, o.pick); return; }
    buildRail(); gauge(); subLine(); var fell = $('fell'); fell.min = C.layout.Y0; fell.max = C.layout.top;
    document.querySelectorAll('#fams button').forEach(function (b) { b.classList.toggle('on', b.dataset.key === k); b.setAttribute('aria-selected', b.dataset.key === k); });
    bindStop(Math.max(0, Math.min(C.stops.length - 1, o.cardStop != null ? o.cardStop : Math.max(0, A.stop))));   /* the same story beat: both tours index the cards' stops */
    if (o.pick && C.people[o.pick]) pick(o.pick);
    S.loaded(VIEW, A.ready ? '1' : '0');
  }
  function deactivate() { var o = { family: A.family, cardStop: A.stop >= 0 ? A.stop : null, pick: A.picked }; stopTour(); if (A.picked) clearPick(); $('tag').hidden = true; return o; }
  S.engines[VIEW] = { boot: boot, activate: activate, deactivate: deactivate, hashFamily: hashFamily, loadFamily: function (k) { loadFamily(k, 0); }, fail: fail, api: A };
""" % subline, 'loom: engine registration')
    if 'document.body.dataset.loaded' in js or "$('x3d')" in js or 'location.hash' in js: raise SystemExit('merge: loom engine still touches the loaded flag, the canvas id or the hash')
    return js


def hyper_engine(js):
    n = len(re.findall(r"^  var XITE_\w+ = .*\n", js, flags=re.M))
    if n != 3: raise SystemExit('merge: hyper X_ITE constants: %d, expected 3' % n)
    js = re.sub(r"^  var XITE_\w+ = .*\n", '', js, flags=re.M)
    js = rep(js, "  document.body.dataset.ui = q.get('ui') === 'none' ? 'none' : 'full';\n",
             "  var S = window.dynastyApi, VIEW = 'hyper', active = function () { return S.view === VIEW; };   /* merge: the shell owns X_ITE, the hash and the shared chrome */\n", 'hyper: shell handle')
    js = rep(js, "  var statusEl = $('status');\n  function status(s, err) { statusEl.textContent = s || ''; statusEl.hidden = !s; if (err) statusEl.style.color = 'var(--alert)'; if (s) log(s); }",
             "  function status(s, err) { S.status(VIEW, s, err); if (s) log(s); }", 'hyper: status')
    js = cut(js, "  // ---------------------------------------------------------------- X_ITE: the shipped copy", "  })(0);\n", '', 'hyper: X_ITE loader to the shell')
    js = rep(js, "function fail(e) { A.failed = String(e && e.message || e); document.body.dataset.loaded = 'failed';", "function fail(e) { A.failed = String(e && e.message || e); S.loaded(VIEW, 'failed');", 'hyper: fail flag')
    js = rep(js, "  var el = $('x3d'), browser = null,", "  var el = null, browser = null,", 'hyper: canvas from the shell')
    js = rep(js, "  function boot() {\n    browser = A.browser = el.browser; setTimeout(cssFallback, 4000);",
             "  function boot(canvas, o) {\n    el = canvas; browser = A.browser = el.browser; A.xite = S.xite; boot.o = o || {}; wireCanvas(); setTimeout(cssFallback, 4000);", 'hyper: boot')
    js = rep(js, "      m.families.forEach(function (f) { var b = document.createElement('button'); b.textContent = f.name; b.dataset.key = f.key; b.setAttribute('role', 'tab'); b.onclick = function () { loadFamily(f.key, 0); }; navEl.appendChild(b); });\n",
             "      S.setFamilies(m.families);\n", 'hyper: family buttons')
    js = rep(js, "      var want = q.get('family') || hashFamily();\n", "      var want = S.family;\n", 'hyper: first family')
    js = rep(js, "      loadFamily(m.families.some(function (f) { return f.key === want; }) ? want : m.families[0].key, +(q.get('stop') || 0));\n",
             "      loadFamily(m.families.some(function (f) { return f.key === want; }) ? want : m.families[0].key, boot.o.stop != null ? boot.o.stop : 0, boot.o);\n", 'hyper: first load')
    js = cut(js, "  function hashFamily() {", "loadFamily(k, 0); });\n",
             "  function hashFamily(k) { if (manifest && k !== A.family && k !== A.loading && manifest.families.some(function (f) { return f.key === k; })) loadFamily(k, 0); }   /* the shell reads the #hash */\n",
             'hyper: hash to the shell')
    js = rep(js, "  function loadFamily(key, stopIndex) {\n", "  function loadFamily(key, stopIndex, carry) {\n", 'hyper: loadFamily carry')
    js = rep(js, "clearPick(true); document.body.dataset.loaded = '0';", "clearPick(true); S.loaded(VIEW, '0');", 'hyper: loading flag')
    js = rep(js, "    var h = '#' + key.replace(/_/g, '-'); if (location.hash !== h) history.replaceState(null, '', location.pathname + location.search + h);\n",
             "    S.noteFamily(VIEW, key);\n", 'hyper: hash write')
    js = rep(js, "            showStop(clamp(stopIndex || 0, 0, D.tour.length - 1), true);\n",
             "            if (carry && carry.stop == null && carry.cardStop != null && !carry.pick) { var cj = tourIndexOf(carry.cardStop); if (cj >= 0) stopIndex = cj; }   /* merge: the loom's story beat */\n"
             "            showStop(clamp(stopIndex || 0, 0, D.tour.length - 1), true);\n", 'hyper: carried stop')
    js = rep(js, "status(''); A.ready = true; document.body.dataset.loaded = '1'; log('ready ' + key);",
             "status(''); A.ready = true; S.loaded(VIEW, '1'); log('ready ' + key); if (carry && carry.pick && D.people[carry.pick] && C.people[carry.pick]) pick(carry.pick, true);", 'hyper: loaded flag')
    js = rep(js, "  $('fell').oninput = function () { fellAnim = null; setFell(+this.value); };", "  S.on(VIEW, 'fell', 'input', function () { fellAnim = null; setFell(+this.value); });", 'hyper: shared fell')
    js = rep(js, "  $('prev').onclick = function () { lastInput = performance.now(); step(-1); }; $('next').onclick = function () { lastInput = performance.now(); step(1); };",
             "  S.on(VIEW, 'prev', 'click', function () { lastInput = performance.now(); step(-1); }); S.on(VIEW, 'next', 'click', function () { lastInput = performance.now(); step(1); });", 'hyper: shared buttons')
    js = rep(js, "  $('tour').onclick = function () { lastInput = performance.now(); if (tourOn) A.tourStop(); else A.tour(A.stop >= D.tour.length - 1 ? 0 : Math.max(0, A.stop)); };",
             "  S.on(VIEW, 'tour', 'click', function () { lastInput = performance.now(); if (tourOn) A.tourStop(); else A.tour(A.stop >= D.tour.length - 1 ? 0 : Math.max(0, A.stop)); });", 'hyper: shared tour')
    js = rep(js, "  addEventListener('resize', function () { Object.keys(labelCache).forEach(function (k) { labelCache[k]._w = 0; }); layoutLabels(true); });",
             "  addEventListener('resize', function () { Object.keys(labelCache).forEach(function (k) { labelCache[k]._w = 0; }); if (active()) layoutLabels(true); });", 'hyper: resize while active')
    js = rep(js, "  el.addEventListener('pointerdown', function (e) {", "  function wireCanvas() {   /* merge: the canvas exists once the shell has made it */\n  el.addEventListener('pointerdown', function (e) {", 'hyper: canvas listeners (open)')
    js = rep(js, "  el.addEventListener('wheel', function () { lastInput = performance.now(); }, { passive: true, capture: true });\n",
             "  el.addEventListener('wheel', function () { lastInput = performance.now(); }, { passive: true, capture: true });\n  }\n", 'hyper: canvas listeners (close)')
    js = rep(js, "    if (e.metaKey || e.ctrlKey || e.altKey || !D || !A.ready) return;", "    if (e.metaKey || e.ctrlKey || e.altKey || !D || !A.ready || !active()) return;", 'hyper: keys while active')
    js = rep(js, "  function frame(now) {\n", "  function frame(now) {\n    if (!active()) { requestAnimationFrame(frame); return; }   /* merge: the loom is showing */\n", 'hyper: frame loop while active')
    js = rep(js, "      var dt = Math.min((now - last) / 1000, .5); last = now; acc += dt; n++; wait += dt;\n",
             "      if (!active()) { last = now; acc = 0; n = 0; wait = 0; requestAnimationFrame(tick); return; }\n      var dt = Math.min((now - last) / 1000, .5); last = now; acc += dt; n++; wait += dt;\n", 'hyper: fps monitor while active')
    anchor = "  $('auto').onchange = function () { A.auto = this.checked; };\n"
    js = rep(js, anchor, anchor + """
  // ---------------------------------------------------------------- merge: the engine's side of the view switch (o = { family, stop, cardStop, pick })
  function tourIndexOf(ci) { if (!D || ci == null) return -1; for (var j = 0; j < D.tour.length; j++) if (D.tour[j].i === ci) return j; return -1; }
  function activate(o) {
    lastInput = performance.now();
    if (!manifest || !D) return;                                   /* still booting: boot() reads the shell's family */
    var k = o.family && manifest.families.some(function (f) { return f.key === o.family; }) ? o.family : A.family;
    if (k !== A.family || (A.look && A.look !== lookSlug())) { loadFamily(k, o.cardStop != null ? Math.max(0, tourIndexOf(o.cardStop)) : Math.max(0, A.stop), o); return; }   /* v2: or the look changed */
    buildUI(); setFell(A.fell == null ? D.units.top : A.fell); setTier(A.tierIndex < 0 ? 2 : A.tierIndex, false);
    document.querySelectorAll('#fams button').forEach(function (b) { b.classList.toggle('on', b.dataset.key === k); b.setAttribute('aria-selected', b.dataset.key === k); });
    var j = o.pick ? -1 : tourIndexOf(o.cardStop);
    caption(Math.max(0, A.stop));
    if (o.pick && D.people[o.pick] && C.people[o.pick]) pick(o.pick, true);          /* the same person, flown to in this form */
    else if (j >= 0 && j !== A.stop) goStop(j);                                       /* the same story beat */
    S.loaded(VIEW, A.ready ? '1' : '0');
  }
  function deactivate() {
    var o = { family: A.family, cardStop: D && A.stop >= 0 && D.tour[A.stop] ? D.tour[A.stop].i : null, pick: A.picked };
    A.tourStop(); fellAnim = null; if (A.picked) clearPick(); $('tag').hidden = true; return o;
  }
  S.engines[VIEW] = { boot: boot, activate: activate, deactivate: deactivate, hashFamily: hashFamily, loadFamily: function (k) { loadFamily(k, 0); }, fail: fail, api: A,
    look: function () { if (active()) A.setLook(); } };   /* v2: the look switch reloads the sphere in the new theme's scenes (in the loom: on the way back) */
""", 'hyper: engine registration')
    if 'document.body.dataset.loaded' in js or "$('x3d')" in js or 'location.hash' in js: raise SystemExit('merge: hyper engine still touches the loaded flag, the canvas id or the hash')
    return js


SHELL_CSS = """
  /* ---- merge: the view switch, the loading still, and what shows in which view (tools/merge_views.py) */
  #views { display: inline-flex; gap: 3px; }
  #views button { padding: 5px 9px; }
  #views button.on { border-color: var(--gold); color: var(--gold); }
  body:not([data-view="loom"]) .only-loom, body:not([data-view="hyper"]) .only-hyper, body:not([data-view="hyper"]) #labels, body:not([data-view="hyper"]) #vignette,
  body:not([data-view="hyper"]) #poster, body:not([data-view="hyper"]) #portrait, body:not([data-view="hyper"]) #lead, body:not([data-view="hyper"]) #grain { display: none !important; }
  #poster { position: fixed; inset: 0; background: #05040b center / cover no-repeat; pointer-events: none; transition: opacity .9s ease; }
  #poster.gone { opacity: 0; }
  #poster .pcap { position: absolute; left: 50%; top: calc(45% + 26px); transform: translateX(-50%); width: min(560px, calc(100vw - 32px)); text-align: center; font: 11px/1.4 var(--mono); color: #b9b0d6; text-shadow: 0 1px 3px #000; }
"""

SHELL_JS = r"""(function () {
  'use strict';
  // ---- the shell (tools/merge_views.py): X_ITE, the two views, the family, the #hash and the shared controls. Each engine below is its page's own
  //      script; the shell boots an engine when its view is first opened and calls activate/deactivate on a switch.
  var XITE_CDN = '%(cdn)s';
  var XITE_LOCAL = '%(local)s';          /* the vendored copy (tests): byte-identical to the npm tarball's dist/x_ite.min.js */
  var XITE_META = document.querySelector('meta[name="loom:xite"]');   /* an Artifact build: X_ITE beside the page, since that CSP refuses X_ITE's runtime fetches from a CDN */
  var XITE_SRI = '%(sri)s';
  var q = new URLSearchParams(location.search), $ = function (id) { return document.getElementById(id); };
  document.body.dataset.ui = q.get('ui') === 'none' ? 'none' : 'full';
  var VIEWS = ['hyper', 'loom'], st = {}, handlers = {}, statusEl = $('status');
  VIEWS.forEach(function (v) { st[v] = { status: 'starting X_ITE', err: false, loaded: '0', ever: false }; });
  var S = window.dynastyApi = { view: null, family: null, families: null, engines: {}, xite: null, log: [], pending: null, look: null };

  // ---- v2 looks (hyper/themes.py): the default theme and one alternate behind a quiet switch in the header; remembered in this browser only
  var LOOKS = /*@LOOK@*/null, LOOK_KEY = 'dynasty-loom:look'; S.looks = LOOKS;
  function storedLook() { try { var v = localStorage.getItem(LOOK_KEY); return v && LOOKS.themes[v] ? v : null; } catch (e) { return null; } }
  S.setLook = function (slug, quiet) {
    if (!LOOKS.themes[slug]) return false;
    var T = LOOKS.themes[slug], alt = LOOKS.order[1], b = $('look-t'); S.look = slug; document.documentElement.dataset.look = slug;
    if (!alt) b.hidden = true;
    else { b.textContent = LOOKS.themes[alt].short; b.setAttribute('aria-pressed', String(slug === alt)); b.title = slug === alt ? 'Back to the ' + LOOKS.themes[LOOKS.default].name + ' look' : 'The ' + LOOKS.themes[alt].name + ' look'; }
    $('brand').firstChild.textContent = T.brand; $('brandsub').textContent = T.brand_sub;
    if (!quiet) { try { localStorage.setItem(LOOK_KEY, slug); } catch (e) { /* private window: the switch still works for this visit */ } }
    Object.keys(S.engines).forEach(function (v) { var E = S.engines[v]; if (E.started && E.look) E.look(slug); });
    log('look ' + slug); measureHeader(); return true;
  };
  // ---- the header's measured height (--header-h): the rail, the card and the toast sit below it, whatever it wraps to (v3: the rail overlapped
  //      a two-row header at 1280x800 and 1366x768)
  function measureHeader() { var h = document.querySelector('header'); if (!h) return; var b = Math.ceil(h.getBoundingClientRect().bottom); document.documentElement.style.setProperty('--header-h', b + 'px'); S.headerH = b; }
  addEventListener('resize', measureHeader);
  try { new ResizeObserver(measureHeader).observe(document.querySelector('header')); } catch (e) { /* resize and the font load still measure */ }
  try { document.fonts.ready.then(measureHeader); } catch (e) {}
  $('look-t').onclick = function () { S.setLook(S.look === LOOKS.order[1] ? LOOKS.default : LOOKS.order[1]); };
  $('more-t').onclick = function () { var c = $('cap'), o = !c.classList.contains('open'); c.classList.toggle('open', o); this.setAttribute('aria-expanded', String(o)); this.textContent = o ? 'Less' : 'Details'; };
  function log(s) { S.log.push((performance.now() / 1000).toFixed(2) + ' s ' + s); }
  function renderStatus() { var x = st[S.view]; statusEl.textContent = x.status; statusEl.hidden = !x.status; statusEl.style.color = x.err ? 'var(--alert)' : ''; }
  S.status = function (v, s, err) { st[v].status = s || ''; st[v].err = !!err; if (v === S.view) renderStatus(); };
  S.loaded = function (v, val) {
    st[v].loaded = val; if (v === S.view) document.body.dataset.loaded = val;
    if (val === '1') { st[v].ever = true; if (v === 'hyper') poster(false); }
    if (val === 'failed' && v === 'hyper' && v === S.view) S.status(v, st[v].status + ' · the Loom view (V) may still work', true);
  };
  S.on = function (v, id, ev, fn) {   /* one listener per shared control, handed to the active view's engine */
    var k = id + ':' + ev;
    if (!handlers[k]) { handlers[k] = {}; $(id).addEventListener(ev, function (e) { var f = handlers[k][S.view]; if (f) f.call(this, e); }); }
    handlers[k][v] = fn;
  };

  // ---- families and the #hash: #hypersphere | #loom | #<family> | #loom/<family>
  S.setFamilies = function (list) {
    if (S.families) return; S.families = list.map(function (f) { return f.key; }); var nav = $('fams');
    list.forEach(function (f) { var b = document.createElement('button'); b.textContent = f.name; b.dataset.key = f.key; b.setAttribute('role', 'tab');
      b.onclick = function () { S.family = f.key; var E = S.engines[S.view]; if (E && E.api.manifest) E.loadFamily(f.key); }; nav.appendChild(b); });
  };
  function parseHash() {
    var h = '', out = {}; try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = ''; }
    h.split('/').forEach(function (t) { t = t.trim().toLowerCase(); if (!t) return;
      if (t === 'hypersphere' || t === 'hyper' || t === 'sphere') out.view = 'hyper'; else if (t === 'loom' || t === 'tapestry') out.view = 'loom'; else out.family = t.replace(/-/g, '_'); });
    if (out.family && S.families && S.families.indexOf(out.family) < 0) delete out.family;
    return out;
  }
  S.writeHash = function () {
    if (!S.family || !S.view) return; var h = '#' + (S.view === 'loom' ? 'loom/' : '') + S.family.replace(/_/g, '-');
    if (location.hash !== h) { try { history.replaceState(null, '', location.pathname + location.search + h); } catch (e) { location.hash = h; } }
  };
  S.noteFamily = function (v, key) { if (v !== S.view) return; S.family = key; S.writeHash(); };
  addEventListener('hashchange', function () {
    var h = parseHash(); log('hash ' + location.hash);
    if (h.view && h.view !== S.view) { S.setView(h.view, h.family ? { family: h.family } : null); return; }   /* v2: the hash's family wins over the old view's */
    var E = S.engines[S.view];
    if (h.family) { if (E && E.api.manifest) E.hashFamily(h.family); else S.family = h.family; } else S.writeHash();
  });

  // ---- X_ITE: one script from the pinned CDN path (or the vendored copy, or an Artifact's own copy then the CDN), with subresource integrity
  var srcs = q.get('local') === '1' ? [XITE_LOCAL] : XITE_META ? [XITE_META.content, XITE_CDN] : [XITE_CDN];
  function loadXite(i) {
    var s = document.createElement('script');
    s.src = srcs[i]; s.integrity = XITE_SRI; s.crossOrigin = 'anonymous';
    s.onerror = function () {
      s.remove(); if (i + 1 < srcs.length) { log('X_ITE did not load from ' + srcs[i] + ', trying ' + srcs[i + 1]); loadXite(i + 1); return; }
      VIEWS.forEach(function (v) { S.engines[v].fail('could not load X_ITE from ' + s.src); });
    };
    s.onload = function () { S.xite = s.src; log('X_ITE from ' + s.src); if (S.pending) { var p = S.pending; S.pending = null; ensure(p[0], p[1]); } };
    document.head.appendChild(s);
  }
  function canvas(v) {   /* one X_ITE browser per view, made when the view is first opened; the hidden one is display:none and X_ITE pauses it */
    var c = $('x3d-' + v); if (c) return c;
    c = document.createElement('x3d-canvas'); c.id = 'x3d-' + v;
    [['splashScreen', 'false'], ['notifications', 'false'], ['contextMenu', 'false'], ['timings', 'false'], ['multisampling', '4']].forEach(function (a) { c.setAttribute(a[0], a[1]); });
    document.body.insertBefore(c, document.body.firstChild); return c;
  }
  function ensure(v, o) {
    var E = S.engines[v];
    if (E.started) { if (E.api.manifest) E.activate(o); return; }
    if (!S.xite) { S.pending = [v, o]; return; }
    E.started = true; var c = canvas(v), n = 0;
    (function wait() { if (c.browser) E.boot(c, o); else if (++n > 400) E.fail('X_ITE could not start (no WebGL?)'); else setTimeout(wait, 50); })();
  }
  function poster(on) {   /* the hero still (Blender Cycles) while the hypersphere first loads; only fetched when that view opens */
    var p = $('poster'); if (!p) return;
    if (on) { if (!p.dataset.src) { p.dataset.src = innerWidth < innerHeight ? 'poster-tall-plate.webp' : 'poster-wide-plate.webp'; p.style.backgroundImage = 'url("' + p.dataset.src + '")'; } p.classList.remove('gone'); p.hidden = false; }
    else if (!p.hidden && !p.classList.contains('gone')) { p.classList.add('gone'); setTimeout(function () { p.hidden = true; }, 950); }
  }

  // ---- the view switch: the family, the story beat and a picked person carry across
  S.setView = function (v, init) {
    if (!S.engines[v] || v === S.view) return false;
    var o = { family: S.family, stop: init && init.stop != null ? init.stop : null, cardStop: null, pick: null }, from = S.view && S.engines[S.view];
    if (from && from.started && from.api.manifest) { var c = from.deactivate() || {}; if (c.family) o.family = S.family = c.family; o.cardStop = c.cardStop; o.pick = c.pick; }
    if (init && init.family) { if (init.family !== o.family) { o.cardStop = null; o.pick = null; } o.family = S.family = init.family; }
    S.view = v; document.body.dataset.view = v; log('view ' + v);
    document.querySelectorAll('#views button').forEach(function (b) { var on = b.dataset.view === v; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    VIEWS.forEach(function (k) { var cv = $('x3d-' + k); if (cv) cv.hidden = k !== v; });
    $('card').hidden = true; $('tag').hidden = true;
    if (!S.engines[v].started) { $('rail').innerHTML = ''; $('capn').textContent = ''; $('capt').textContent = 'Loading'; $('capy').textContent = ''; $('narr').innerHTML = ''; $('comp').innerHTML = ''; }
    renderStatus(); document.body.dataset.loaded = st[v].loaded;
    if (v === 'hyper' && !st.hyper.ever) poster(true);
    S.writeHash(); ensure(v, o);
    return true;
  };
  document.querySelectorAll('#views button').forEach(function (b) { b.onclick = function () { S.setView(b.dataset.view); }; });
  document.addEventListener('keydown', function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey || !S.view) return;
    var t = e.target.tagName; if ((t === 'INPUT' && !/^(range|checkbox)$/.test(e.target.type)) || t === 'SELECT' || t === 'TEXTAREA') return;
    if (e.key === 'v' || e.key === 'V') S.setView(S.view === 'loom' ? 'hyper' : 'loom');
  });
  S.start = function () {
    var darkAlt = LOOKS.order[1] && !LOOKS.themes[LOOKS.order[1]].ink && matchMedia('(prefers-color-scheme: dark)').matches ? LOOKS.order[1] : null;   /* a dark system setting starts on the dark alternate */
    S.setLook(LOOKS.themes[q.get('look')] ? q.get('look') : storedLook() || darkAlt || LOOKS.default, true); measureHeader();
    var h = parseHash(); S.family = q.get('family') || h.family || null;
    loadXite(0); S.setView(h.view || (q.get('view') === 'loom' ? 'loom' : 'hyper'), { stop: q.get('stop') != null ? +q.get('stop') : null });
  };
})();
"""

NAV_HEAD = '<style media="all">\n  /* nav: the page owns the camera (lib/orbit.js); the Lens toggle and its plain-words chip (hypersphere only, v5: the loom header keeps its one row) */\n  x3d-canvas { touch-action: none; cursor: grab; } x3d-canvas:active { cursor: grabbing; }\n  #lens-t { font-variant: small-caps; letter-spacing: .04em; font-size: 16px; }\n  #lens-t[aria-pressed="true"] { border-bottom-color: var(--accent); color: var(--accent); }\n  #lenschip { flex-basis: 100%; font: italic 13.5px/1.3 var(--ui); color: var(--dim); }\n  @media (max-width: 720px) { #lens-t { font-size: 13px; padding: 4px 2px; } #lenschip { font-size: 12px; } header .brand, #views { order: -2; } #lens-t { order: -1; } }\n  body:not([data-view="loom"]) header .sub { flex: 1 1 480px; min-width: 0; }\n</style><!-- nav -->\n<script src="lib/lens.js"></script><script src="lib/orbit.js"></script><!-- nav: the lens mirror and the orbit camera (lib/) -->\n'   # nav (README, "v5 (Artifact version 5)"): the hypersphere's lens style and its two libraries (lib/). v5 review: on a phone the Lens
                   # button joins the first row (brand, views); on a desktop the sub line may wrap inside its row, so Lens never takes a row of its own
MARKUP = """<div id="poster" aria-hidden="true" hidden><span class="pcap">Still: a Blender Cycles render of the Rothschild sphere from the Wide shot, shown while the live X3D scene loads</span></div>
<div id="vignette" aria-hidden="true"></div>
<div id="labels" aria-hidden="true"></div>
<svg id="grain" aria-hidden="true"><filter id="grainf"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#grainf)"/></svg>
<div id="lead" aria-hidden="true"></div>
<figure id="portrait"><div class="frame"><div class="ph"><img id="pimg" alt="" decoding="async" hidden><span class="mono" id="pmono" hidden></span></div></div><figcaption><b id="pname"></b><span id="pyears"></span><span class="plab" id="plab"></span></figcaption></figure>
<header class="panel">
  <span class="brand" id="brand">Dynasty Loom<small id="brandsub"></small></span>
  <span id="views" role="group" aria-label="View"><button data-view="hyper" aria-pressed="false" title="Radius is time: each family as a glass time-sphere (V)">Hypersphere</button><button data-view="loom" aria-pressed="false" title="Time runs up: each family as cloth on a loom (V)">Loom</button></span>
  <span class="sub" id="sub">radius = time · fiber = a life · arc = a marriage · dye = share of descent from the founders</span>
  <nav id="fams" aria-label="Family"></nav>
  <button id="look-t" aria-pressed="false">Night</button>
  <button id="lens-t" class="only-hyper" aria-pressed="false" title="A hyperbolic lens: magnify one place and let the rest recede (L)">Lens</button>
  <span id="lenschip" class="only-hyper" hidden>Lens: the focus is magnified, the rest recedes; distances are not to scale.</span>
</header>
<nav id="rail" aria-label="Tour stops"></nav>
<section id="cap" class="panel" aria-live="polite">
  <div class="head"><span id="capn"></span><b id="capt">Loading</b><span id="capy"></span><span id="shotchip" class="only-hyper"></span><span id="gauge" class="only-loom" aria-label="Dye gauge: thread colour by share of descent"></span><button id="more-t" aria-expanded="false" aria-controls="more">Details</button></div>
  <p id="narr"></p>
  <div class="ctl">
    <button id="prev" aria-label="Previous stop">‹</button><button id="tour" aria-label="Play the tour">Tour ▸</button><button id="next" aria-label="Next stop">›</button>
    <label for="fell">Year <input type="range" id="fell" min="1700" max="2026" step="1" value="2026"><output id="fellv">2026</output></label>
  </div>
  <div id="more">
    <p id="comp"></p>
    <p id="scale" class="only-hyper"></p>
    <div class="ctl">
      <label for="shots" class="only-hyper">Shot <select id="shots" aria-label="Fly to a shot"></select></label>
      <span id="tiers" class="only-hyper" role="group" aria-label="Quality"><button data-tier="0">Fast</button><button data-tier="1">Balanced</button><button data-tier="2">Ultra</button>
        <label class="tick" title="lower the quality when the frame rate falls"><input type="checkbox" id="auto" checked> auto</label></span>
      <span id="fps" class="only-hyper"></span><span id="where" class="only-hyper"></span>
      <span class="keys only-loom">1–8 ladder · T tour · ←/→ stops · [ ] { } year · V view · Esc clear</span>
      <span class="keys only-hyper">drag orbit · Shift-drag free · right-drag pan · wheel zoom · double-click centre · arrows orbit · + − zoom · 0 reset · L lens · T tour · PgUp/PgDn stops · P plunge · W wide · [ ] { } year · Q quality · V view · Esc clear</span>
    </div>
  </div>
</section>
<aside id="card" class="panel" hidden aria-live="polite"></aside>
<div id="tag" class="panel" hidden></div>
<div id="toast" class="panel" role="status"></div>
<div id="status">starting X_ITE</div>
<noscript>This page needs JavaScript: the scenes are X3D drawn by X_ITE.</noscript>
"""


def build():
    EDITS.clear()
    lraw, hraw = open(LOOM, 'rb').read(), open(HYPER, 'rb').read()
    loom, hyper = lraw.decode('utf-8'), hraw.decode('utf-8')
    lcss, hcss = between(loom, '<style>\n', '</style>\n', 'loom style'), between(hyper, '<style>\n', '</style>\n', 'hyper style')
    ljs, hjs = between(loom, '<script>\n', '</script>\n', 'loom script'), between(hyper, '<script>\n', '</script>\n', 'hyper script')
    lbody, hbody = between(loom, '<body>\n', '<script>\n', 'loom markup'), hyper[hyper.index('</style>\n') + 9:hyper.index('<script>\n')]
    ids = lambda s: set(re.findall(r'\bid="([^"]+)"', s))
    missing = sorted((ids(lbody) | ids(hbody)) - ids(MARKUP) - {'x3d'})
    if missing: raise SystemExit('merge: the shared markup lacks ids the pages use: %s' % missing)
    def const(name):
        m = re.search(r"var %s = '([^']+)';" % name, ljs)
        if not m: raise SystemExit('merge: loom constant %s not found' % name)
        return m.group(1)
    hsri = re.search(r"var XITE_SRI = '([^']+)';", hjs).group(1)
    if hsri != const('XITE_SRI'): raise SystemExit('merge: the two pages pin different X_ITE builds (SRI differ)')
    shell = SHELL_JS % dict(cdn=const('XITE_CDN'), local=const('XITE_LOCAL'), sri=const('XITE_SRI'))
    head = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>Dynasty Loom</title>
<!--@FONTS@-->
<meta name="description" content="Three families, two views. The hypersphere: a glass time-sphere, radius = time from the founders' seed to the glass, houses as sectors west to east, each life a glowing fiber, each marriage an arc on the shell of its year. The loom: time runs up, houses stand west to east, each life a warp thread, each marriage a weft pick. Dye = share of descent from the founders. Standard X3D 4.0 (GLSL shaders in the hypersphere) drawn by X_ITE 16.5.1.">
<!-- GENERATED by scene2/tools/merge_views.py from scene2/page/loom.html (the tapestry page) and proto/hyper/page/index.html (the hypersphere page):
     never edit by hand; edit those two and run the merge. Two views on one chrome: #hypersphere (the default) and #loom; a family name in the hash
     (#rothschild, #habsburg, #darwin-wedgwood) picks the family, #loom/habsburg both. V switches view. The scene files beside the page are generated
     by build_loom_scene.py (the loom: *.x3d, *.cards.json, loom-manifest.json) and build_hypersphere.py (hyper-*.x3d, pocket-*.x3d, *.hyper.json,
     hyper-manifest.json). X_ITE 16.5.1 comes from jsDelivr (pinned, with subresource integrity); ?local=1 loads the vendored copy (tests); an Artifact
     build ships X_ITE beside the page (<meta name="loom:xite">). Other params: ?view=loom ?family= ?stop= ?ui=none, and each view's own (?fell=,
     ?tier=fast|balanced|ultra, ?auto=0, ?extras=0, ?idle=0). Our code never evaluates strings as code and fetches only same-origin files. -->
<style>
"""
    if hcss.strip() != TH.CSS_MARK: raise SystemExit('merge: the hypersphere page\'s <style> must hold only the theme mark (v2)')
    page = (head + lcss + SHELL_CSS + TH.CSS_MARK + '\n</style>\n' + NAV_HEAD + '</head>\n<body>\n'
            + MARKUP + '<script>\n' + shell + loom_engine(ljs) + hyper_engine(hjs) + 'window.dynastyApi.start();\n</script>\n</body>\n</html>\n')
    page = TH.fill_page(page)   # v2: DEFAULT_THEME + ALT_THEME + PHONE_UI: fonts link, style sheet, the look constants (shell and sphere)
    if re.search(r'\beval\s*\(|new\s+Function\b', page): raise SystemExit('merge: eval or new Function in the page')
    if re.search(r"fetch\(\s*['\"]data:", page): raise SystemExit('merge: a data: URL fetch in the page')
    out = page.encode('utf-8')
    rec = dict(stage='merge_views.py', looks=TH.page_slugs(), phone_ui=TH.PHONE_UI, inputs={'scene2/page/loom.html': sha(lraw), 'hyper/page/index.html': sha(hraw), 'hyper/themes.py': sha(open(os.path.join(PROTO, 'hyper', 'themes.py'), 'rb').read())},
               script=sha(open(os.path.abspath(__file__), 'rb').read()), output={'scene2/page/index.html': sha(out)}, bytes=len(out), edits=list(EDITS),
               checks=dict(ids_covered=sorted((ids(lbody) | ids(hbody)) - {'x3d'}), no_eval=True, no_data_url_fetch=True, same_xite_sri=True))
    return out, rec


def main():
    out, rec = build()
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == out
        print('page/index.html is %s the merge of its two sources' % ('exactly' if same else 'NOT')); sys.exit(0 if same else 1)
    open(OUT, 'wb').write(out)
    json.dump(rec, open(os.path.join(HERE, 'page', 'merge-receipt.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('wrote %s: %d bytes, %d anchored edits, sha256 %s' % (OUT, len(out), len(rec['edits']), rec['output']['scene2/page/index.html'][:16]))


if __name__ == '__main__':
    main()
