"""Unit tests for the loom genealogy ingest prototype.  Run:  python3 -I tests/test_proto.py"""
import json
import os
import subprocess
import sys
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import gdates, gedcom7, jsobj, kinship  # noqa: E402


def wj(path, obj):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=1)


class LiteralReader(unittest.TestCase):
    def test_reads_ts_module_shapes(self):
        src = "import { X } from '../types';\nexport const familyData: Record<string, X> = {\n  // a comment\n  \"a\": { id: 'a', born: 1744, parents: [], note: \"it's\", },\n  b: {id: \"b\", parents: [\"a\",], died: undefined},\n};\n"
        v, locs, line = jsobj.find_literal(src, 'familyData')
        self.assertEqual(v, {'a': {'id': 'a', 'born': 1744, 'parents': [], 'note': "it's"}, 'b': {'id': 'b', 'parents': ['a'], 'died': None}})
        self.assertEqual(locs[('a', 'born')], 4)
        self.assertEqual(line, 2)

    def test_refuses_code(self):
        for bad in ("const familyData = { a: fetch('x') };", "const familyData = { ...other };", "const familyData = { a: b };",
                    "const familyData = { a: `x${y}` };", "const familyData = { [k]: 1 };", "const familyData = { a };"):
            with self.assertRaises(jsobj.JSDataError, msg=bad):
                jsobj.find_literal(bad, 'familyData')

    def test_one_binding_only(self):
        with self.assertRaises(jsobj.JSDataError):
            jsobj.find_literal('const familyData = {}; let familyData = {};', 'familyData')


class Dates(unittest.TestCase):
    def test_round_trip_spellings(self):
        cases = {
            '1744': ('1744', '+1744', '1744-01-01', '1744-12-31'),
            'ABT 1850': ('1850~', 'A+1850', '1845-01-01', '1855-12-31'),
            'BET 1910 AND 1915': ('[1910..1915]', '+1910/+1915', '1910-01-01', '1915-12-31'),
            'BEF 1920': ('[..1920]', '/+1920', None, '1920-12-31'),
            'AFT 1890': ('[1890..]', '+1890/', '1890-01-01', None),
            '3 MAR 1855': ('1855-03-03', '+1855-03-03', '1855-03-03', '1855-03-03'),
            'FROM 1930 TO 1975': ('1930/1975', '+1930/+1975', '1930-01-01', '1975-12-31'),
            'FEB 1900': ('1900-02', '+1900-02', '1900-02-01', '1900-02-28'),
        }
        for g, (edtf, gx, lo, hi) in cases.items():
            d = gdates.parse_gedcom(g)
            self.assertEqual((d['gedcom'], d['edtf'], d['gedcomx'], d['earliest'], d['latest']), (g, edtf, gx, lo, hi), g)

    def test_julian(self):
        d = gdates.parse_gedcom('JULIAN 22 MAR 1459')
        self.assertEqual(d['earliest'], '1459-03-31')        # Julian to Gregorian is +9 days in the 15th century
        self.assertEqual(d['edtf'], '1459-03-31')
        self.assertEqual(d['gedcom'], 'JULIAN 22 MAR 1459')

    def test_bce_and_phrase(self):
        self.assertEqual(gdates.parse_gedcom('44 BCE')['earliest'], '-0043-01-01')
        d = gdates.parse_gedcom('', 'in the year of the great flood')
        self.assertEqual((d['kind'], d['earliest'], d['gedcom']), ('phrase', None, ''))

    def test_rejects(self):
        for bad in ('1744 BC', 'BET 1910', 'ABT', '31 FOO 1900', 'HEBREW 1 JAN 5700'):
            with self.assertRaises(gdates.DateError, msg=bad):
                gdates.parse_gedcom(bad)


class Kin(unittest.TestCase):
    def kin(self, parents):
        ids = set(parents) | {p for ps in parents.values() for p in ps}
        return kinship.Kinship(ids, parents)

    def test_reference_values(self):
        # grandparents g1+g2 -> children a, b; a -> x; b -> y (first cousins x, y); a also marries b's daughter y2 (uncle-niece)
        P = {'a': ['g1', 'g2'], 'b': ['g1', 'g2'], 'x': ['a', 'sa'], 'y': ['b', 'sb'], 'kid': ['x', 'y'], 'y2': ['b', 'sb'], 'kid2': ['a', 'y2']}
        k = self.kin(P)
        self.assertEqual(k.phi('a', 'b'), Fraction(1, 4))        # full siblings
        self.assertEqual(k.phi('a', 'x'), Fraction(1, 4))        # parent and child
        self.assertEqual(k.phi('x', 'y'), Fraction(1, 16))       # first cousins
        self.assertEqual(k.phi('a', 'y2'), Fraction(1, 8))       # uncle and niece
        self.assertEqual(k.inbreeding('kid'), Fraction(1, 16))
        self.assertEqual(k.inbreeding('kid2'), Fraction(1, 8))
        self.assertEqual(k.phi('g1', 'g1'), Fraction(1, 2))

    def test_double_first_cousins(self):
        P = {'a': ['p', 'q'], 'b': ['p', 'q'], 'c': ['r', 's'], 'd': ['r', 's'], 'x': ['a', 'c'], 'y': ['b', 'd']}
        self.assertEqual(self.kin(P).phi('x', 'y'), Fraction(1, 8))

    def test_names_and_generation(self):
        self.assertEqual(kinship.relationship_name(2, 2), 'first cousins')
        self.assertEqual(kinship.relationship_name(2, 3), 'first cousins once removed')
        self.assertEqual(kinship.relationship_name(3, 3), 'second cousins')
        self.assertTrue(kinship.relationship_name(1, 2).startswith('uncle/aunt'))
        P = {'s': ['m', 'g'], 'j': ['m', 'g'], 'b': ['s'], 'c': ['j', 'b']}
        gens = kinship.generation_ranges(set('msgjbc'), P, {'m': ['g'], 'g': ['m'], 'j': ['b'], 'b': ['j']}, {})
        self.assertEqual((gens['b']['min'], gens['b']['max']), (3, 3))
        self.assertEqual((gens['c']['min'], gens['c']['max']), (3, 4))   # pedigree collapse: two answers, both kept

    def test_cycle(self):
        with self.assertRaises(kinship.CycleError):
            kinship.topo_order(['a', 'b'], {'a': ['b'], 'b': ['a']})


class Gedcom(unittest.TestCase):
    HEAD = '0 HEAD\n1 GEDC\n2 VERS 7.0\n'

    def test_grammar(self):
        recs = gedcom7.parse(self.HEAD + '0 @I1@ INDI\n1 NOTE @@x\n2 CONT y\n1 FAMS @F1@\n0 TRLR\n')
        indi = recs[1]
        self.assertEqual(indi.first('NOTE').value, '@x\ny')
        self.assertEqual(indi.first('FAMS').ptr, '@F1@')
        for bad in (self.HEAD + '0 @I1@ INDI\n1 NOTE @x\n0 TRLR\n', self.HEAD + '0 @I1@ INDI\n1 NOTE a\n2 CONC b\n0 TRLR\n',
                    self.HEAD + '0 @I1@ INDI\n2 NOTE a\n0 TRLR\n', '0 @I1@ INDI\n0 TRLR\n', self.HEAD + '0 @I1@ INDI\n'):
            with self.assertRaises(gedcom7.GedcomError, msg=bad):
                gedcom7.parse(bad)

    def test_rejects_551(self):
        with self.assertRaises(gedcom7.GedcomError):
            gedcom7.import_claims(gedcom7.parse('0 HEAD\n1 GEDC\n2 VERS 5.5.1\n0 TRLR\n'), 'x')


class Wikidata(unittest.TestCase):
    def test_parse_and_enrich(self):
        import tempfile
        import resolve_wikidata
        resp = json.dumps({'entities': {'Q4115189': {'id': 'Q4115189', 'sitelinks': {'enwiki': {'title': 'Test Person'}},
                           'claims': {'P569': [{'rank': 'normal', 'mainsnak': {'datavalue': {'value': {'time': '+1801-05-02T00:00:00Z', 'precision': 11,
                                      'calendarmodel': 'http://www.wikidata.org/entity/Q1985727'}}}, 'references': [{}]}]}},
                           '-1': {'missing': ''}}}).encode()
        members, log = resolve_wikidata.parse([('offline:x', resp)], {'Test Person': 'tp'})
        self.assertEqual((members[0]['id'], members[0]['wikidata'], members[0]['born']), ('tp', 'Q4115189', 1801))
        self.assertTrue(members[0]['wikidata_detail']['P569']['referenced'])
        with tempfile.TemporaryDirectory() as d:          # the overlay through ingest: QID set, birth corroborated by a second family
            tree = {'id': 'tst', 'name': 'T', 'members': [{'id': 'tp', 'name': 'Test Person', 'born': 1801, 'generation': 1, 'parents': [], 'branch': 'X', 'note': 'n',
                                                           'wikipedia': 'https://en.wikipedia.org/wiki/Test_Person'}]}
            wj(os.path.join(d, 'tree.json'), tree)
            wj(os.path.join(d, 'wd.json'), {'id': 'tst', 'name': 'W', 'members': members})
            with open(os.path.join(ROOT, 'config', 'fixture.json'), encoding='utf-8') as fh:
                policy = json.load(fh)['policy']
            man = {'as_of': '2026-10-29', 'datasets': {'tst': {'name': 'T'}}, 'policy': policy,
                   'grade_reason': 'test', 'curated': [], 'sources': [
                       {'path': 'tree.json', 'parser': 'json-tree', 'dataset': 'tst', 'family': 'app', 'default_grade': 'Suspected'},
                       {'path': 'wd.json', 'parser': 'json-tree', 'dataset': 'tst', 'family': 'wikidata', 'prov': 'data', 'default_grade': 'Likely', 'overlay': True}]}
            wj(os.path.join(d, 'm.json'), man)
            r = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'ingest.py'), '--manifest', os.path.join(d, 'm.json'), '--src', d, '--out', os.path.join(d, 'out')],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-1500:])
            with open(os.path.join(d, 'out', 'private', 'genealogy.graph.json'), encoding='utf-8') as fh:
                g = json.load(fh)
            p = next(n for n in g['nodes'] if n['cls'] == 'Person')
            self.assertEqual(p['ids']['wikidata'], 'Q4115189')
            self.assertEqual((p['facts']['birth']['status'], p['facts']['birth']['independent_families'], p['facts']['birth']['grade']), ('agreed', 2, 'Likely'))


class EndToEnd(unittest.TestCase):
    def run_ingest(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'ingest.py')] + list(args), capture_output=True, text=True)

    def test_fixture_privacy(self):
        out = os.path.join(ROOT, 'out', 'fixture')
        r = self.run_ingest('--manifest', os.path.join(ROOT, 'config', 'fixture.json'), '--src', os.path.join(ROOT, 'fixtures'), '--out', out)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        with open(os.path.join(out, 'public-candidate', 'genealogy.graph.json'), encoding='utf-8') as fh:
            pub = fh.read()
        for name in ('Kit', 'Lee', 'Ida', '1962', '1995'):
            self.assertNotIn(name, pub, name)
        with open(os.path.join(out, 'private', 'genealogy.graph.json'), encoding='utf-8') as fh:
            g = json.load(fh)
        f5 = next(n for n in g['nodes'] if n['id'] == 'union:fixture/F5')
        self.assertEqual((f5['consanguinity']['relationship'], f5['consanguinity']['phi']), ('first cousins', '1/16'))
        jo = next(n for n in g['nodes'] if n['id'] == 'person:fixture/I9')
        self.assertEqual(jo['metrics']['inbreeding_F'], '1/16')
        mx = next(n for n in g['nodes'] if n['id'] == 'person:fixture/I13')
        self.assertEqual(mx['metrics']['inbreeding_F'], '0')       # adopted: not counted as a blood line


class MergeStage(unittest.TestCase):
    """loaders.load_harvest, identity.Resolver and the compatible-date rule (config/merge.json)."""

    def test_harvest_dates(self):
        import loaders
        d, p = loaders.harvest_date({'date': '1744-02-23', 'precision': 'day'})
        self.assertEqual((d['gedcom'], p), ('23 FEB 1744', 'day'))
        d, p = loaders.harvest_date({'date': '1225', 'precision': 'circa'})
        self.assertEqual((d['gedcom'], p), ('ABT 1225', 'circa'))
        self.assertEqual(loaders.harvest_date({'date': None, 'precision': 'unknown'}), (None, 'unknown'))

    def test_compatible_dates_agree(self):
        import build
        y, day, other = gdates.from_year(1744), gdates.parse_gedcom('23 FEB 1744'), gdates.from_year(1743)
        self.assertTrue(build.compatible(y, day))
        self.assertFalse(build.compatible(y, other))
        groups, reps = build.date_groups([{'value': y}, {'value': day}, {'value': other}])
        self.assertEqual([len(g) for g in groups], [2, 1])
        self.assertEqual(reps[0]['value']['gedcom'], '23 FEB 1744')      # the most precise of the agreeing values stands

    def test_identity_ladder_never_name_alone(self):
        import identity
        self.assertEqual(identity.fold("Frances 'Fanny' Mackintosh"), identity.fold('Frances Mackintosh'))
        self.assertEqual(identity.fold('Laura Thérèse von Rothschild'), identity.fold('Laura Therese de Rothschild'))

        def src(i, scope):
            return {'id': 'source:t/s%d' % i, 'dataset': 't', 'rank': i, 'id_scope': scope, 'default_grade': 'Likely'}

        def person(local, name, year, qid=None):
            out = [{'kind': 'person', 'subject': local, 'predicate': 'name', 'value': name}]
            if year:
                out.append({'kind': 'person', 'subject': local, 'predicate': 'birth', 'value': gdates.from_year(year)})
            if qid:
                out.append({'kind': 'person', 'subject': local, 'predicate': 'exid', 'value': {'type': gedcom7.EXID_WIKIDATA, 'value': qid}})
            return out
        loaded = [(src(0, 'file'), person('a', 'Charlotte de Rothschild', 1819) + person('b', 'Anna Smith', 1800, 'Q1'), {}, ''),
                  (src(1, 'harvest'), person('Q7', 'Charlotte von Rothschild', 1825) + person('x:anna-smith-1801', 'Anna Smith', None) +
                   person('Q9', 'Mary Jones', 1800, 'Q9') + person('x:charlotte-1819', 'Charlotte Rothschild', 1819), {}, '')]
        r = identity.Resolver(loaded, {'identity_conflict_years': 10})
        canon = lambda i, l: r.canon('source:t/s%d' % i, l)
        self.assertNotEqual(canon(0, 'a'), canon(1, 'Q7'))                  # same folded name, other birth year: two people
        self.assertNotEqual(canon(0, 'b'), canon(1, 'x:anna-smith-1801'))   # name alone (no birth year) never matches
        self.assertEqual(canon(0, 'a'), canon(1, 'x:charlotte-1819'))       # folded name + the same birth year
        self.assertEqual(r.ref('source:t/s1', 'Q1'), canon(0, 'b'))         # a harvest QID reference resolves across files
        self.assertIn('unresolved~', r.ref('source:t/s0', 'nobody'))       # an unresolved reference can never collide with a person


if __name__ == '__main__':
    unittest.main(verbosity=1)
