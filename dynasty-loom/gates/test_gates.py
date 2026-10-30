"""python3 -I test_gates.py : both sides of every data gate (a clean family raises nothing; each injected fault is caught),
the parser on hostile input, the thresholds at their edges, and the run end to end on a made-up source tree (bundle privacy)."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datagates as G
import jsobj

W = 'https://en.wikipedia.org/wiki/'
CLEAN = {
    'a': dict(id='a', name='Abel Stone', born=1800, died=1870, generation=1, parents=[], spouse='b', branch='North', note='n', wikipedia=W + 'Abel_Stone'),
    'b': dict(id='b', name='Berta Kalm', born=1805, died=1880, generation=1, parents=[], spouse='a', branch='North', note='n', wikipedia=W + 'Berta_Kalm'),
    'c': dict(id='c', name='Carl Stone', born=1830, died=1900, generation=2, parents=['a', 'b'], spouse='d', branch='North', note='n', wikipedia=W + 'Carl_Stone'),
    'd': dict(id='d', name='Dora Vey', born=1832, died=1890, generation=2, parents=[], spouse='c', branch='North', note='n', wikipedia=W + 'Dora_Vey'),
    'e': dict(id='e', name='Emil Stone', born=1860, died=1930, generation=3, parents=['c', 'd'], branch='North', note='n', wikipedia=W + 'Emil_Stone'),
    'f': dict(id='f', name='Frida Stone', born=1863, died=1940, generation=3, parents=['c', 'd'], branch='North', note='n', wikipedia=W + 'Frida_Stone'),
}


def put(path, text):
    with open(path, 'w', encoding='utf-8') as fh: fh.write(text)


def run(mut=None, **cfg):
    m = copy.deepcopy(CLEAN)
    if mut: mut(m)
    return G.check(m, cfg)


def gates(fs, sev=('error', 'warn')):
    return {f['gate'] for f in fs if f['severity'] in sev}


class Clean(unittest.TestCase):
    def test_clean_family_raises_nothing(self):
        fs = run(); self.assertEqual([f for f in fs if f['severity'] != 'info'], [], json.dumps(fs, indent=1))

    def test_edges_of_the_thresholds_pass(self):
        def m(x): x['d']['born'] = 1830; x['d']['died'] = 1950; x['e']['born'] = 1842; x['f']['born'] = 1901   # both parents 12 at e's birth; f born the year after c died (tolerance 1)
        self.assertEqual(gates(run(m)), set())
        def m2(x): x['e']['born'] = 1910; x['c']['born'] = 1830; x['c']['died'] = 1950; x['d']['born'] = 1840; x['d']['died'] = 1950; x['a']['born'] = 1750; x['a']['died'] = 1840   # c is 80 at e's birth, a is 80 at c's
        self.assertEqual(gates(run(m2)), set())


class Injected(unittest.TestCase):
    def check_caught(self, gate, mut, sev='error', **cfg):
        fs = run(mut, **cfg); hit = [f for f in fs if f['gate'] == gate and f['severity'] == sev]
        self.assertTrue(hit, '%s not raised: %s' % (gate, json.dumps(fs, indent=1)))
        return hit

    def test_D01_dangling_parent(self):
        self.check_caught('D01-dangling-parent', lambda m: m['e']['parents'].append('zed'))

    def test_D02_cycle(self):
        h = self.check_caught('D02-cycle', lambda m: m['a']['parents'].append('e'))
        self.assertIn('->', h[0]['message'])
        self.check_caught('D02-cycle', lambda m: m['a']['parents'].append('a'))

    def test_D03_child_not_younger(self):
        self.check_caught('D03-child-not-younger', lambda m: m['e'].update(born=1825))

    def test_D04_born_after_parent_death(self):
        self.check_caught('D04-born-after-parent-death', lambda m: m['f'].update(born=1902))

    def test_D05_parent_age_both_ends(self):
        self.check_caught('D05-parent-age', lambda m: m['e'].update(born=1841))           # c is 11
        self.check_caught('D05-parent-age', lambda m: (m['c'].update(died=1950), m['d'].update(died=1950, born=1850), m['e'].update(born=1911, died=1980)))   # c is 81

    def test_D06_dates(self):
        self.check_caught('D06-dates', lambda m: m['e'].update(died=1850))
        self.check_caught('D06-dates', lambda m: m['e'].update(died=1990))                # 130 years
        self.check_caught('D06-dates', lambda m: m['e'].update(died=2031))

    def test_D07_duplicates(self):
        self.check_caught('D07-duplicate', lambda m: m.update(g=dict(CLEAN['e'], id='g', name='Emil  Stöne', wikipedia=W + 'Emil_Stone_2', born=1861)), sev='warn')
        self.check_caught('D07-duplicate', lambda m: m['f'].update(wikipedia=m['e']['wikipedia']), sev='warn')

    def test_D08_generation(self):
        self.check_caught('D08-generation', lambda m: m['e'].update(generation=2))           # same as the parent
        self.check_caught('D08-generation', lambda m: (m['e'].update(generation=5), m['f'].update(generation=5)), sev='warn')   # skips two
        self.check_caught('D08-generation', lambda m: m['f'].update(generation=4))           # full siblings differ (and a skip)

    def test_D09_spouse(self):
        h = self.check_caught('D09-spouse', lambda m: m['b'].pop('spouse'), sev='warn')      # a names b, a sorts first: drawn
        self.assertTrue(h[0]['detail']['drawn'])
        h = self.check_caught('D09-spouse', lambda m: m['a'].pop('spouse'))                  # b names a, b sorts after a: never drawn
        self.assertFalse(h[0]['detail']['drawn'])
        self.check_caught('D09-spouse', lambda m: m['d'].update(spouse='a'))                 # conflicting
        self.check_caught('D09-spouse', lambda m: m['e'].update(spouse='nobody'))

    def test_D10_privacy(self):
        self.check_caught('D10-living', lambda m: m.update(g=dict(CLEAN['e'], id='g', name='Gus Livewell', born=1990, generation=4, parents=['e'], wikipedia=W + 'Gus_Livewell', died=None)))
        self.check_caught('D10-living', lambda m: m['a'].pop('died'), sev='warn')            # long dead, no death year: "Present"

    def test_D11_portrait(self):
        self.check_caught('D11-portrait', lambda m: m['a'].update(imageUrl='https://picsum.photos/id/10/400/400'))

    def test_D12_wikipedia(self):
        self.check_caught('D12-wikipedia', lambda m: m['a'].update(wikipedia='http://example.com/Abel'))
        self.check_caught('D12-wikipedia', lambda m: m['a'].update(wikipedia=W + 'Zebra_Crossing'), sev='warn')

    def test_D14_island_and_D15_placeholder(self):
        self.check_caught('D14-island', lambda m: m.update(z=dict(CLEAN['e'], id='z', name='Zoe Alone', parents=[], wikipedia=W + 'Zoe_Alone')), sev='warn')
        self.check_caught('D15-placeholder-text', lambda m: m['a'].update(note='Stub dataset: replace with a richer JSON later.'), sev='warn')

    def test_D00_schema(self):
        self.check_caught('D00-schema', lambda m: m['a'].update(born='1800'))
        self.check_caught('D00-schema', lambda m: m['a'].update(id='aa'))
        self.check_caught('D00-schema', lambda m: [x.pop('note') for x in m.values()], sev='warn')


class Parser(unittest.TestCase):
    TS = """import { X } from '../types';
// a comment with { braces }
export const familyData: Record<string, X> = {
  "p1": { id: "p1", name: 'O\\'Brien { not a brace }', born: 1800, parents: [], note: `multi
line`, },   /* block } comment */
  p2: { id: "p2", born: -5, x: 0x10, y: 1.5e3, ok: true, n: null, },
  "p1": { id: "p1", name: "second p1" },
};
const other = 1;"""

    def test_reads_ts_literal_with_comments_quotes_trailing_commas(self):
        lit, line = jsobj.find_literal(self.TS, 'familyData'); v = jsobj.parse_literal(lit, line)
        self.assertEqual(line, 3); self.assertEqual(v['p2']['x'], 16); self.assertEqual(v['p2']['y'], 1500.0); self.assertIs(v['p2']['ok'], True)
        self.assertEqual(v['p1']['name'], 'second p1')                                       # JS keeps the last ...
        self.assertEqual([(p, k) for p, k, _ in jsobj.iter_dups(v)], [('$', 'p1')])          # ... and the gate is told about the first

    def test_refuses_code(self):
        for bad in ('{a: foo()}', '{a: new THREE.Color(1)}', '{...x}', '{[k]: 1}', '{a: `${x}`}'):
            with self.assertRaises(jsobj.ParseError, msg=bad): jsobj.parse_literal(bad)


class EndToEnd(unittest.TestCase):
    def test_privacy_reaches_the_bundle_gate(self):
        with tempfile.TemporaryDirectory() as d:
            v = os.path.join(d, 'app'); os.makedirs(os.path.join(v, 'data')); os.makedirs(os.path.join(v, 'dist', 'assets'))
            put(os.path.join(v, 'App.tsx'), "import { familyData } from './data/family';\n")
            people = copy.deepcopy(CLEAN); people['g'] = dict(CLEAN['e'], id='g', name='Gus Livewell', born=1990, generation=4, parents=['e'], wikipedia=W + 'Gus_Livewell'); people['g'].pop('died')
            put(os.path.join(v, 'data', 'family.ts'), 'export const familyData: Record<string, M> = ' + json.dumps(people) + ';\n')
            put(os.path.join(v, 'dist', 'assets', 'index.js'), 'var d=' + json.dumps({k: p['name'] for k, p in people.items()}) + ';')
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'run_gates.py'), d, os.path.join(d, 'out')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            with open(os.path.join(d, 'out', 'findings.jsonl')) as fh: fs = [json.loads(x) for x in fh]
            self.assertTrue(any(f['gate'] == 'D10-living' and f['subject'] == 'g' for f in fs))
            self.assertTrue(any(f['gate'] == 'R02-bundle-privacy' and f['subject'] == 'g' for f in fs), r.stdout)
            with open(os.path.join(d, 'out', 'receipt.json')) as fh: rc = json.load(fh)
            self.assertEqual(set(rc['checker']), {'jsobj.py', 'sources.py', 'datagates.py', 'run_gates.py'})
            self.assertTrue(all(len(x['sha256']) == 64 for x in rc['inputs'].values()))


if __name__ == '__main__':
    unittest.main(verbosity=1)
