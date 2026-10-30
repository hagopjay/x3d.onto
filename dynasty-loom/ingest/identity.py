"""Identity across sources: which records in which files are one person.

A record is what one scope says about one local id. Scopes come from the manifest (`id_scope` on each source):
  shared   the app files and the analyst decisions of one dataset share their local ids (successive copies of one compilation)
  file     a fact-check file: its ids mean something only inside that file
  harvest  a harvest partition: QIDs are global, `wp:<title>` names an enwiki article, `x:<name>-<year>` is provisional and local

Records are matched, in precedence order, to the person clusters built so far by a fixed ladder, strongest key first:
  1 QID   2 English Wikipedia title   3 folded name (or alias) + the same birth year   4 the same provisional x: id in another
  partition (the slug is itself a folded name + birth year)
Name alone never matches. A match is refused when the birth years are more than `identity_conflict_years` apart, when a
weaker key would join records whose QIDs differ, or when the cluster already holds a record of the same file; every refusal,
and every QID or title disagreement inside an accepted match, is reported. References (parents, spouses, children) resolve
inside their own scope first; a harvest reference may also name a QID, a title or a provisional id held by another partition.
A reference that resolves nowhere keeps a private id that can never collide with a person, so it stays dangling (gate G07)."""
import re
import unicodedata
from collections import OrderedDict, defaultdict

import gedcom7

QID = re.compile(r'Q[1-9][0-9]*')
QUOTED = re.compile(r'\([^)]*\)|"[^"]*"|\'[^\'\s][^\']*\'|‘[^’]*’|“[^”]*”')


PARTICLES = {'von', 'van', 'de', 'der', 'den', 'du', 'des', 'la', 'le', 'zu', 'da', 'di', 'del', 'sir', 'lady', 'lord', 'dame'}


def fold(name):
    """Lower case, accents off, parentheses and quoted nicknames dropped, punctuation to spaces, nobiliary particles and
    honorifics dropped (sources spell the same person 'de' or 'von', with or without 'Sir'):
    "Frances 'Fanny' Mackintosh" and 'Frances Mackintosh' fold alike; 'Emma Darwin (née Wedgwood)' folds to 'emma darwin'."""
    s = QUOTED.sub(' ', name or '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return ' '.join(t for t in re.sub(r'[^a-z0-9]+', ' ', s).split() if t not in PARTICLES)


def title_key(t):
    t = (t or '').replace(' ', '_').strip('_')
    return t[:1].upper() + t[1:] if t else None


class Resolver:
    def __init__(self, loaded, policy):
        self.window = policy['identity_conflict_years']
        self.src = {s['id']: s for s, *_ in loaded}
        self.records = OrderedDict()            # scope key -> record
        self.where = {}                         # (source id, local) -> scope key
        for s, claims, _, _ in loaded:
            for c in claims:
                if c['kind'] != 'person':
                    continue
                sk = self.scope_key(s, c['subject'])
                self.where[(s['id'], c['subject'])] = sk
                r = self.records.get(sk)
                if r is None:
                    r = self.records[sk] = OrderedDict(key=sk, dataset=s['dataset'], local=c['subject'], scope=s.get('id_scope', 'shared'), sources=[], rank=s['rank'],
                                                       qids=[], strong_qids=[], titles=[], names=[], year=None, cluster=None)
                if s['id'] not in r['sources']:
                    r['sources'].append(s['id'])
                v = c['value']
                if c['predicate'] == 'exid' and isinstance(v, dict) and v.get('type') == gedcom7.EXID_WIKIDATA:
                    if v.get('value') not in r['qids']:
                        r['qids'].append(v['value'])
                    g = [s['default_grade'], c.get('cap'), c.get('qcap')]
                    if all(x in (None, 'Likely', 'Confirmed') for x in g) and v['value'] not in r['strong_qids']:
                        r['strong_qids'].append(v['value'])     # a QID at Likely or better may name the person
                elif c['predicate'] == 'sitelink' and v.get('site') == 'enwiki' and title_key(v['title']) not in r['titles']:
                    r['titles'].append(title_key(v['title']))
                elif c['predicate'] in ('name', 'alias') and fold(v) and fold(v) not in r['names']:
                    r['names'].append(fold(v))
                elif c['predicate'] == 'birth' and r['year'] is None and isinstance(v, dict) and v.get('start'):
                    r['year'] = v['start']['y']
        for r in self.records.values():
            if r['scope'] == 'harvest' and r['local'].startswith('wp:') and title_key(r['local'][3:]) not in r['titles']:
                r['titles'].append(title_key(r['local'][3:]))
            if r['scope'] == 'harvest' and r['local'].startswith('x:'):  # the provisional slug is the harvester's own folded name
                slug = fold(re.sub(r'-(?:d?\d{3,4}|unknown)$', '', r['local'][2:]).replace('-', ' '))
                if slug and slug not in r['names']:
                    r['names'].append(slug)
        self.clusters = []
        self.idx = defaultdict(dict)            # (dataset, index name) -> key -> cluster number
        self.report = OrderedDict(matches=[], refused=[], id_conflicts=[], bridges=[], methods=defaultdict(int), provisional=0)
        for r in sorted(self.records.values(), key=lambda r: r['rank']):     # stable: file order inside a source
            self.place(r)
        self.assign_ids()
        self.unresolved = defaultdict(list)

    @staticmethod
    def scope_key(s, local):
        sc = s.get('id_scope', 'shared')
        return ('shared', s['dataset'], local) if sc == 'shared' else (s['id'], local)

    # ---------------- clustering ----------------
    def place(self, r):
        ds = r['dataset']
        cands = []
        for q in r['qids']:
            if q in self.idx[(ds, 'qid')]:
                cands.append(('qid', self.idx[(ds, 'qid')][q], q))
        for t in r['titles']:
            if t in self.idx[(ds, 'title')]:
                cands.append(('enwiki', self.idx[(ds, 'title')][t], t))
        if r['year'] is not None:
            for nm in r['names']:
                k = '%s|%d' % (nm, r['year'])
                if k in self.idx[(ds, 'name')]:
                    cands.append(('name+year', self.idx[(ds, 'name')][k], k))
        if r['scope'] == 'harvest' and r['local'].startswith('x:'):
            self.report['provisional'] += 1
            if r['local'] in self.idx[(ds, 'xid')]:
                cands.append(('provisional-id', self.idx[(ds, 'xid')][r['local']], r['local']))
        chosen = None
        for method, ci, key in cands:
            cl = self.clusters[ci]
            why = None
            if any(set(self.records[x]['sources']) & set(r['sources']) for x in cl['records']):
                why = 'the cluster already holds a record of the same file'
            elif cl['year'] is not None and r['year'] is not None and abs(cl['year'] - r['year']) > self.window:
                why = 'birth years %d and %d are more than %d years apart' % (cl['year'], r['year'], self.window)
            elif method in ('name+year', 'provisional-id') and r['qids'] and cl['qids'] and not set(r['qids']) & cl['qids']:
                why = 'a %s match between records with different QIDs (%s / %s)' % (method, ', '.join(r['qids']), ', '.join(sorted(cl['qids'])))
            if why:
                self.report['refused'].append(OrderedDict(record=self.label(r), cluster=self.label(self.records[cl['records'][0]]), method=method, key=key, why=why))
                continue
            chosen = (method, ci, key)
            break
        if chosen is None:
            ci = len(self.clusters)
            self.clusters.append(OrderedDict(dataset=ds, records=[], qids=set(), titles=set(), year=r['year']))
            method = 'new'
        else:
            method, ci, key = chosen
            cl = self.clusters[ci]
            for kind, mine, theirs in (('wikidata', r['qids'], cl['qids']), ('enwiki', r['titles'], cl['titles'])):
                if mine and theirs and not set(mine) & theirs:
                    self.report['id_conflicts'].append(OrderedDict(kind=kind, record=self.label(r), values=list(mine), cluster=self.label(self.records[cl['records'][0]]),
                                                                   cluster_values=sorted(theirs), matched_by=method))
            self.report['matches'].append(OrderedDict(record=self.label(r), cluster=self.label(self.records[cl['records'][0]]), method=method, key=key))
        self.report['methods'][method] += 1
        cl = self.clusters[ci]
        cl['records'].append(r['key'])
        r['cluster'] = ci
        if cl['year'] is None:
            cl['year'] = r['year']
        for q in r['qids']:
            cl['qids'].add(q)
            other = self.idx[(ds, 'qid')].setdefault(q, ci)
            if other != ci:
                self.report['bridges'].append(OrderedDict(key=q, record=self.label(r), held_by=self.label(self.records[self.clusters[other]['records'][0]])))
        for t in r['titles']:
            cl['titles'].add(t)
            other = self.idx[(ds, 'title')].setdefault(t, ci)
            if other != ci:
                self.report['bridges'].append(OrderedDict(key=t, record=self.label(r), held_by=self.label(self.records[self.clusters[other]['records'][0]])))
        if r['year'] is not None:
            for nm in r['names']:
                self.idx[(ds, 'name')].setdefault('%s|%d' % (nm, r['year']), ci)
        if r['scope'] == 'harvest' and r['local'].startswith('x:'):
            self.idx[(ds, 'xid')].setdefault(r['local'], ci)

    def assign_ids(self):
        """A cluster's id is its first QID in precedence order, else the local id of its first record; never two alike."""
        used = set()
        for cl in self.clusters:
            first = self.records[cl['records'][0]]
            qs = [q for k in cl['records'] for q in self.records[k]['strong_qids']]
            key = qs[0] if qs else first['local']
            if (cl['dataset'], key) in used:
                key = '%s@%s' % (key, first['sources'][0].split('/')[-1])
            used.add((cl['dataset'], key))
            cl['key'] = key
            cl['id'] = 'person:%s/%s' % (cl['dataset'], key)

    def label(self, r):
        return '%s %s' % (r['sources'][0].split(':', 1)[1], r['local'])

    # ---------------- lookups used by build.Builder.add_source ----------------
    def canon(self, source_id, local):
        return self.clusters[self.records[self.where[(source_id, local)]]['cluster']]['id']

    def ref(self, source_id, local):
        s = self.src[source_id]
        sk = self.scope_key(s, local)
        if sk in self.records:
            return self.clusters[self.records[sk]['cluster']]['id']
        ds = s['dataset']
        if s.get('id_scope') == 'harvest':
            hit = None
            if QID.fullmatch(local):
                hit = self.idx[(ds, 'qid')].get(local)
            elif local.startswith('wp:'):
                hit = self.idx[(ds, 'title')].get(title_key(local[3:]))
            elif local.startswith('x:'):
                hit = self.idx[(ds, 'xid')].get(local)
            if hit is not None:
                return self.clusters[hit]['id']
        self.unresolved[source_id].append(local)
        return 'person:%s/unresolved~%s~%s' % (ds, re.sub(r'[^A-Za-z0-9_.-]+', '_', source_id.split('/')[-1]), local)

    def summary(self):
        rep = self.report
        multi = [cl for cl in self.clusters if len(cl['records']) > 1]
        return OrderedDict(records=len(self.records), persons=len(self.clusters), merged_persons=len(multi), methods=OrderedDict(sorted(rep['methods'].items())),
                           provisional_x_ids=rep['provisional'], refused=rep['refused'], id_conflicts=rep['id_conflicts'], bridges=rep['bridges'],
                           unresolved_refs=OrderedDict((k, sorted(set(v))) for k, v in sorted(self.unresolved.items())))
