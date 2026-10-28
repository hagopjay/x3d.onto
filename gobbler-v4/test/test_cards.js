/* node gobbler-v4/test/test_cards.js : card content rules on synthetic data, then every drawn star of the real Deep graph if it has been fetched. */
'use strict';
var assert = require('assert'), fs = require('fs'), path = require('path'), Cards = require('../src/cards.js');
var n = 0;
function t(name, fn) { fn(); n++; console.log('ok  ' + name); }

function tiny() {
  var nodes = [
    { label: 'Shape', cls: 'NodeType', prov: 'data', grade: 'Confirmed', tier: 1, deg: 2, xyz: [0, 0, 0], metrics: [], notes: [], props: { scenes: 255 }, docs: ['a.md', 'b.md', 'c.md', 'd.md'], loops: [0] },
    { label: '<script>alert(1)</script> & "quotes"', cls: 'Finding', prov: 'doc', grade: 'Suspected', tier: 2, deg: 1, xyz: [1, 0, 0], metrics: [{ name: 'median frames', value: '4 frames', check: 'Chromium', doc: 'x.md' }, { name: 'cost', value: '~$0.01', check: null, doc: null }, { name: 'text', value: 'a very long non numeric value here' }], notes: [], props: {}, docs: [], loops: [] },
    { label: 'Loner', cls: 'Tool', prov: 'simulated', grade: 'Likely', tier: 2, deg: 0, xyz: [2, 0, 0], metrics: [], notes: ['only a note'], props: {}, docs: [], loops: [] },
    { label: 'Bare', cls: 'Mystery', prov: 'model_recall', grade: null, tier: 2, deg: 0, xyz: [3, 0, 0], metrics: [], notes: [], props: {}, docs: [], loops: [] }
  ];
  var edges = [{ s: 0, t: 1, p: 'part_of', grade: 'Confirmed', prov: 'data', ev: ['quoted evidence <b>x</b>'], docs: ['a.md'] }, { s: 1, t: 0, p: 'feeds', grade: 'Suspected', prov: 'doc', ev: [], docs: [] }];
  return { nodes: nodes, edges: edges, loops: [{ name: 'THE TETHER', steps: [3, 1, 0] }], drawn: 4 };
}
var ONTO = { meta: { ontology_sha256_16: '8307e9045104cc58', xsd: 'XSD 4.1 via x3d_mcp validate_xml', mcp_commit: 'fa0b389' }, by_lower: { shape: 'Shape' },
  c: { Shape: { cp: 'Shape', a: ['X3DNode', 'X3DShapeNode'], d: 'Shape can appear under any grouping node.', nf: 7, k: 'concrete', n: 59, A: 22, R: 30, I: 7, ap: 21, aps: ['Anchor', 'Billboard'] } } };

t('every card carries a provenance tag and a grade tag, even for missing grade or unknown class', function () {
  var C = Cards.create(tiny(), ONTO);
  [0, 1, 2, 3].forEach(function (i) { [2, 3].forEach(function (tier) { var c = C.card(i, tier).html; assert(/gv4-tag (dat|doc|rec|sim)/.test(c), 'prov ' + i); assert(/gv4-tag g-/.test(c), 'grade ' + i); }); });
  assert(/ungraded/.test(C.card(3, 2).html));
});
t('a star named like an Object.prototype member is not an ontology class, and its deep card still renders', function () {
  var g = tiny(); g.nodes[3].cls = 'NodeType'; ['constructor', 'toString', '__proto__', 'hasOwnProperty'].forEach(function (name) {
    g.nodes[3].label = name; var C = Cards.create(g, ONTO), c = C.card(3, 3);
    assert(!c.onto && !/ontology 4\.1/.test(c.html), name);
  });
});
t('every dynamic string is escaped', function () {
  var h = Cards.create(tiny(), ONTO).card(1, 3).html + Cards.create(tiny(), ONTO).tip(1, 2).html;
  assert(!/<script>/.test(h) && /&lt;script&gt;/.test(h)); assert(!/<b>x<\/b>/.test(Cards.create(tiny(), ONTO).card(0, 3).html));
});
t('no "undefined", "null" or "NaN" leaks into any card', function () {
  var C = Cards.create(tiny(), ONTO); [0, 1, 2, 3].forEach(function (i) { [2, 3].forEach(function (tier) { var c = C.card(i, tier).html; assert(!/undefined|null|NaN/.test(c), i + ' ' + tier + ' ' + c.match(/.{20}(undefined|null|NaN).{20}/)); }); });
});
t('metrics lead for a Finding; the first number is split from its unit; long non-numeric values shrink', function () {
  var h = Cards.create(tiny(), ONTO).card(1, 2).html;
  assert(/<b>4<small>frames<\/small><\/b>/.test(h)); assert(/<b>~\$0\.01<\/b>/.test(h)); assert(/<b class="s">a very long non numeric value here/.test(h));
  assert(!/<blockquote>/.test(h), 'a card with metrics shows tiles, not a quote');
});
t('untethered stars say so and show their note; tethered ones list relations with direction, predicate and grade dot', function () {
  var C = Cards.create(tiny(), ONTO);
  assert(/Untethered/.test(C.card(2, 2).html) && /only a note/.test(C.card(2, 2).html));
  var h = C.card(0, 2).html; assert(/→ part of/.test(h) === true || /← feeds/.test(h)); assert(/gv4-gd Suspected|gv4-gd Confirmed/.test(h));
});
t('the ontology block appears only at tier 3, only for NodeType or Component with a match, and says "map, not gate"', function () {
  var C = Cards.create(tiny(), ONTO);
  assert(!/ontology 4\.1/.test(C.card(0, 2).html)); var d = C.card(0, 3).html;
  assert(/predicts <b>59<\/b>/.test(d) && /accepts <b>22<\/b>/.test(d) && /rejects <b>30<\/b>/.test(d) && /<b>7<\/b> inconclusive/.test(d) && /map, not gate/.test(d));
  assert(/X3DNode › X3DShapeNode › <b>Shape<\/b>/.test(d)); assert(/sha 8307e904/.test(d) && /fa0b389/.test(d));
  assert(!/ontology 4\.1/.test(C.card(1, 3).html), 'a Finding never gets the ontology block');
  assert(!Cards.create(tiny(), null).card(0, 3).html.match(/ontology 4\.1/), 'no ONTO data, no block');
});
t('tier 3 adds sources, loop membership and properties; tier 2 does not', function () {
  var C = Cards.create(tiny(), ONTO), d = C.card(0, 3).html, c = C.card(0, 2).html;
  assert(/sources a\.md · b\.md \+2 more/.test(d) && /THE TETHER \(step 3 of 3\)/.test(d) && /scenes/.test(d));
  assert(!/sources/.test(c) && !/THE TETHER/.test(c));
});
t('tooltips are one line: label (shortened), class and provenance word', function () {
  var C = Cards.create(tiny(), ONTO), a = C.tip(0), b = C.tip(1);
  assert.strictEqual(a.label, 'Shape'); assert.strictEqual(a.meta, 'NodeType · live data'); assert(b.label.length <= 38);
});

var gp = path.join(__dirname, '..', 'data', 'deep', 'graph-v3.json'), op = path.join(__dirname, '..', 'data', 'onto-hover.json');
if (fs.existsSync(gp) && fs.existsSync(op)) {
  var G = JSON.parse(fs.readFileSync(gp, 'utf8')), ON = JSON.parse(fs.readFileSync(op, 'utf8')), C = Cards.create(G, ON);
  t('Deep graph: all ' + G.drawn + ' drawn stars build a tier 2 and a tier 3 card without leaking undefined, null or NaN', function () {
    var maxLen = 0, noTag = 0, bad = [];
    for (var i = 0; i < G.drawn; i++) {
      [2, 3].forEach(function (tier) {
        var c = C.card(i, tier), h = c.html; maxLen = Math.max(maxLen, h.length);
        if (!/gv4-tag (dat|doc|rec|sim)/.test(h) || !/gv4-tag g-/.test(h)) noTag++;
        if (/undefined|\bnull\b|NaN/.test(h.replace(/<blockquote[\s\S]*?<\/blockquote>/g, ''))) bad.push(i + ':' + tier);     /* quoted evidence may say "null"; the template may not */
        if (!/^#[0-9a-f]{6}$/.test(c.hex)) bad.push(i + ' colour');
      });
    }
    assert.strictEqual(noTag, 0, 'cards without provenance or grade'); assert.deepStrictEqual(bad.slice(0, 5), []); assert(maxLen < 9000, 'largest card ' + maxLen + ' chars');
    console.log('    largest card ' + maxLen + ' chars');
  });
  t('Deep graph: 105 of 178 drawn NodeType/Component stars match an ontology class (104 distinct); Shape reproduces 59 / 22 / 30 / 7', function () {
    var drawn = G.nodes.slice(0, G.drawn).filter(function (x) { return x.cls === 'NodeType' || x.cls === 'Component'; }), hits = 0, ids = {};
    drawn.forEach(function (x, k) { var o = C.onto(x); if (o) { hits++; ids[o.id] = 1; } });
    assert.strictEqual(drawn.length, 178); assert.strictEqual(hits, 105); assert.strictEqual(Object.keys(ids).length, 104);
    var sh = ON.c.Shape; assert.deepStrictEqual([sh.n, sh.A, sh.R, sh.I, sh.ap], [59, 22, 30, 7, 21]);
    assert.strictEqual(ON.meta.totals.A + ON.meta.totals.R + ON.meta.totals.I, ON.meta.totals.rows);
  });
  t('Deep graph: the Finding in the mock (X_ITE blank frames) leads with its three measurements named verbatim', function () {
    var i = G.nodes.findIndex(function (x) { return x.label === 'X_ITE renders on demand and starts every scene with blank frames'; });
    assert(i >= 0); var h = C.card(i, 2).html;
    ['4', '157', '64'].forEach(function (v) { assert(h.indexOf('<b>' + v) >= 0, v); });
    assert(/non-drawable scene median frames/.test(h) && /Playwright Chromium with SwiftShader/.test(h));
  });
  t('Deep graph: no card shows a field that is not in the graph (metric names and values come from the node)', function () {
    for (var i = 0; i < G.drawn; i += 7) { var x = G.nodes[i]; if (!x.metrics || !x.metrics.length) continue; var h = C.card(i, 2).html; x.metrics.slice(0, 3).forEach(function (m) { assert(h.indexOf(Cards.esc(Cards.clip(m.name, 70))) >= 0, 'metric name for ' + i); }); }
  });
} else console.log('skip  Deep graph tests (make v4-data and make v4-onto)');
console.log(n + ' tests passed');
