"""Canonical builder: the claim streams of all sources to one genealogy graph.

Nodes: Person, Union (a couple, or an open union with one unknown partner; children hang on the union as in a GEDCOM
FAM), Branch (a house or line, with a seat Place) and Place; every input file is a Source. Every fact on a node points
at the claims behind it; a claim carries source, locator, verbatim quote, grade and provenance. Contested facts keep
every alternative: the first source in the manifest order gives the accepted value (precedence) and nothing is dropped.
The derived layer (generation from topology, kinship, inbreeding, pedigree collapse, living status) is computed here
with prov 'computed'; its truth is never better than the claims it was computed from.
"""
import hashlib
import json
import re
from collections import OrderedDict, defaultdict

import gdates
import gedcom7
import kinship

GRADE_RANK = {'Confirmed': 3, 'Likely': 2, 'Suspected': 1, 'Illustrative': 0}
DATE_FACTS = ('birth', 'death')
CLAIM_KEYS = ('quay', 'cites', 'slot', 'pedigree', 'surname', 'stat', 'cap', 'qcap', 'precision', 'precision_note', 'roles', 'married', 'ended',
              'stated_relationship', 'alias_type')
CORE_PREDICATES = ('name', 'birth', 'death', 'parents')


def min_grade(a, b):
    return a if GRADE_RANK.get(a, 0) <= GRADE_RANK.get(b, 0) else b


def _iso(s):
    neg = s.startswith('-'); parts = [int(x) for x in s.lstrip('+-').split('-')]
    return (-parts[0] if neg else parts[0],) + tuple(parts[1:])


def compatible(a, b):
    """Two dates agree when their windows overlap ('1744' and '23 FEB 1744'; 'ABT 1225' and '1227'). A date with no window
    (a bare phrase) agrees only with an identical spelling."""
    if a.get('gedcom') and a.get('gedcom') == b.get('gedcom'):
        return True
    w = (a.get('earliest'), a.get('latest'), b.get('earliest'), b.get('latest'))
    if None in w:
        return False
    return _iso(w[0]) <= _iso(w[3]) and _iso(w[2]) <= _iso(w[1])


def date_groups(cs, key=lambda c: c['value']):
    """Claims in precedence order to groups of mutually compatible dates; the first group holds the first claim (precedence).
    Each group's representative is its most precise exact date (a refinement, not a new value)."""
    groups = []
    for c in cs:
        for g in groups:
            if all(compatible(key(c), key(x)) for x in g):
                g.append(c); break
        else:
            groups.append([c])
    reps = [max(g, key=lambda c: (key(c).get('kind') == 'exact', {'day': 3, 'month': 2, 'year': 1}.get(key(c).get('precision'), 0), -g.index(c))) for g in groups]
    return groups, reps


def enwiki_key(title):
    t = (title or '').replace(' ', '_').strip('_')
    return t[:1].upper() + t[1:] if t else None


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')


def claim_id(source, locator, predicate, value):
    return 'c:' + hashlib.sha256(json.dumps([source, locator, predicate, value], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def best_grade(grades):
    gs = [g for g in grades if g in GRADE_RANK]
    return max(gs, key=lambda g: GRADE_RANK[g]) if gs else None


def local_of(pid):
    return pid.split('/', 1)[1]


class Builder:
    def __init__(self, manifest, curated_places, as_of, house_of=None):
        self.policy = manifest['policy']
        self.house_of = house_of or (lambda ds, label: None)   # (dataset, branch label) -> house key or None (curated/houses.json)
        self.resolved = False                                 # True once a source came through identity.py (the merge build)
        self.places_cur = curated_places
        self.as_of = as_of
        self.as_of_year = int(as_of[:4])
        self.claims = []                      # normalised, in precedence order
        self.cby = {}                         # claim id -> claim
        self.sources = []
        self.issues = defaultdict(list)       # finding kind -> list, read by the gates
        self.records_in = defaultdict(set)    # source id -> person locals that have a record there
        self.place_nodes = OrderedDict()
        self.branch_nodes = OrderedDict()
        self.overlays = set()

    # ---------------- claims ----------------
    def add_source(self, src, raw_claims, resolver=None):
        """Normalise one source's raw claims: canonical subject ids (a _LOOMID from a GEDCOM re-import wins; with a resolver,
        identity.py decides which person a record and each reference are), stable claim ids, grade (source default, capped by
        the record's own confidence and, for a QID, by its qid confidence; Illustrative for placeholder media; an author's
        GEDCOM QUAY where given)."""
        self.sources.append(src)
        if src.get('overlay'):
            self.overlays.add(src['id'])
        if resolver is not None:
            self.resolved = True
        ds = src['dataset']
        loomid = {(c['kind'], c['subject']): c['value'] for c in raw_claims if c['predicate'] == 'loomid'}

        def canon(kind, local):
            if kind == 'person' and resolver is not None:
                return resolver.canon(src['id'], local)
            return loomid.get((kind, local)) or '%s:%s/%s' % (kind, ds, local)

        def ref(local):
            return resolver.ref(src['id'], local) if resolver is not None else canon('person', local)

        for c in raw_claims:
            if c['predicate'] == 'loomid':
                continue
            if c['kind'] == 'person':
                self.records_in[src['id']].add(c['subject'])
            v = c['value']
            refs = None
            if c['predicate'] == 'parents':
                refs = [(p, ref(p)) for p in v]
            elif c['predicate'] in ('spouse', 'partner', 'child'):
                refs = [(v, ref(v))]
            elif c['predicate'] in ('famc', 'fams'):
                refs = [(v, canon('union', v))]
            elif c['predicate'] == 'children.stated':
                refs = [(x, ref(x)) for x in v]
            elif c['predicate'] == 'event':
                refs = [(x, ref(x)) for x in (v.get('persons') or []) if isinstance(x, str)]
            grade = src['default_grade']
            if c['predicate'] == 'media' and isinstance(v, dict) and v.get('kind') == 'placeholder':
                grade = 'Illustrative'
            elif c.get('quay') is not None:
                grade = gedcom7.GRADE_OF_QUAY.get(str(c['quay']), grade)
            if c.get('cap') in GRADE_RANK:
                grade = min_grade(grade, c['cap'])
            if c['predicate'] == 'exid' and c.get('qcap') in GRADE_RANK:
                grade = min_grade(grade, c['qcap'])
            d = OrderedDict(id=claim_id(src['id'], c['locator'], c['predicate'], v), source=src['id'], kind=c['kind'], subject=canon(c['kind'], c['subject']),
                            predicate=c['predicate'], value=v, locator=c['locator'], quote=c['quote'], grade=grade, prov=src.get('prov', 'doc'))
            for k in CLAIM_KEYS:
                if c.get(k) is not None:
                    d[k] = c[k]
            if refs is not None:
                d['refs'] = [{'local': a, 'id': b} for a, b in refs]
            d['_rank'] = src['rank']; d['_seq'] = len(self.claims); d['_ds'] = ds; d['_local'] = c['subject']
            self.claims.append(d); self.cby[d['id']] = d

    def family_of(self, source_id):
        return next(s['family'] for s in self.sources if s['id'] == source_id)

    # ---------------- assembly ----------------
    def build(self):
        ordered = sorted(self.claims, key=lambda c: (c['_rank'], c['_seq']))
        persons, unions_x = OrderedDict(), OrderedDict()
        for c in ordered:
            if c['kind'] == 'person':
                persons.setdefault(c['subject'], []).append(c)
            elif c['kind'] == 'union':
                unions_x.setdefault(c['subject'], []).append(c)
        self.person_ids = set(persons)
        nodes, edges, work = OrderedDict(), [], {}
        for pid, cs in persons.items():
            nodes[pid], w = self.person(pid, cs, edges)
            work[pid] = w
        unions = self.unions(nodes, work, unions_x)
        self.derive(nodes, unions)
        if self.resolved:
            self.check_children(nodes, work)
            self.grade(nodes, unions, work)
        for n in nodes.values():
            for f in n['facts'].values():
                f.pop('_groups', None)
        edges += self.union_edges(nodes, unions, work)
        for g in self.branch_nodes.values():
            if g.get('seat'):
                pl = self.place_nodes[g['seat']]
                edges.append(OrderedDict(s=g['id'], p='seated_at', t=g['seat'], grade=pl['grade'], prov=pl['prov'], claims=[]))
        for pid, n in nodes.items():
            for ev, pred in (('birth', 'born_in'), ('death', 'died_in')):
                f = n['facts'].get(ev)
                if f and f.get('place'):
                    edges.append(OrderedDict(s=pid, p=pred, t=f['place'], grade=f['grade'], prov='doc', claims=f['claims'][-1:]))
        out_nodes = list(nodes.values()) + list(unions.values()) + list(self.branch_nodes.values()) + list(self.place_nodes.values())
        claims = [OrderedDict((k, v) for k, v in c.items() if not k.startswith('_')) for c in ordered]
        return out_nodes, edges, claims

    def person(self, pid, cs, edges):
        by = defaultdict(list)
        for c in cs:
            by[c['predicate']].append(c)
        ds = cs[0]['_ds']
        n = OrderedDict(id=pid, cls='Person', dataset=ds, local=pid.split('/', 1)[1] if self.resolved else cs[0]['_local'])
        names = OrderedDict()
        for c in by.get('name', []):
            names.setdefault(c['value'], []).append(c)
        n['label'] = next(iter(names)) if names else local_of(pid)
        n['names'] = [OrderedDict(value=v, type='preferred' if k == 0 else 'variant', claims=[c['id'] for c in g], sources=sorted({c['source'] for c in g}))
                      for k, (v, g) in enumerate(names.items())]
        if len(names) > 1:
            self.issues['name-variants'].append({'person': pid, 'values': {v: sorted({c['source'] for c in g}) for v, g in names.items()}})
        n['sex'] = OrderedDict(value=by['sex'][0]['value'], claims=[by['sex'][0]['id']]) if by.get('sex') else None
        facts = OrderedDict()
        for ev in DATE_FACTS:
            vals, reps = date_groups(by.get(ev, []))        # compatible dates agree ('1744' and '23 FEB 1744'); only disjoint windows compete
            occurred = by.get(ev + '.occurred', [])
            if not vals and not occurred:
                continue
            f = OrderedDict()
            if vals:
                srcs = sorted({c['source'] for c in vals[0]})
                rp = reps[0]
                f.update(date=rp['value'], claims=[c['id'] for c in vals[0]], sources=srcs,
                         status='contested' if len(vals) > 1 else ('agreed' if len(srcs) > 1 else 'single'),
                         grade=best_grade(c['grade'] for c in vals[0]), independent_families=len({self.family_of(s) for s in srcs}),
                         precision_label=rp.get('precision') or ('circa' if rp['value'].get('kind') == 'approx' else rp['value'].get('precision')))
                f['_groups'] = [[c['id'] for c in g] for g in vals]
                if len(vals) > 1:
                    f['alternatives'] = [OrderedDict(date=r['value'], claims=[c['id'] for c in g], sources=sorted({c['source'] for c in g})) for g, r in zip(vals[1:], reps[1:])]
                    self.issues['conflicts'].append({'person': pid, 'fact': ev, 'accepted': f['date']['gedcom'], 'accepted_by': srcs,
                                                     'alternatives': [{'value': a['date']['gedcom'], 'by': a['sources']} for a in f['alternatives']]})
            else:
                f.update(date=None, claims=[c['id'] for c in occurred], sources=sorted({c['source'] for c in occurred}), status='occurred', grade=best_grade(c['grade'] for c in occurred))
            pl = by.get(ev + '.place', [])
            if pl:
                f['place'] = self.place_for(pl[0]['value'], pl[0]); f['claims'] = f['claims'] + [pl[0]['id']]
            facts[ev] = f
        n['facts'] = facts
        # parents: an empty list means 'not stated' (open world), so it is an omission, not a conflict. Non-empty sets that nest
        # (one source names the father only, another father and mother) agree, and the fuller set stands for the group; sets that
        # do not nest compete: the first by precedence is accepted and every other set is kept as an alternative
        pcl = []; empty_by = []
        for c in by.get('parents', []):
            if c['value']:
                pcl.append(c)
            else:
                empty_by.append(c['source'])
        P = None
        if pcl:
            pk = lambda c: frozenset(r['id'] for r in c['refs'])
            vals = []
            for c in pcl:
                for g in vals:
                    if all(pk(c) <= pk(x) or pk(x) <= pk(c) for x in g):
                        g.append(c); break
                else:
                    vals.append([c])
            reps = [max(g, key=lambda c, g=g: (len(pk(c)), -g.index(c))) for g in vals]
            srcs = sorted({c['source'] for c in vals[0]})
            P = {'claims': vals[0], 'rep': reps[0], 'sources': srcs, 'status': 'contested' if len(vals) > 1 else ('agreed' if len(srcs) > 1 else 'single'),
                 'alternatives': vals[1:], 'alt_reps': reps[1:], 'stated_empty_by': sorted(set(empty_by))}
            if len(vals) > 1:
                self.issues['conflicts'].append({'person': pid, 'fact': 'parents', 'accepted': [r['local'] for r in reps[0]['refs']], 'accepted_by': srcs,
                                                 'alternatives': [{'value': [r['local'] for r in rp['refs']], 'by': sorted({c['source'] for c in g})} for g, rp in zip(vals[1:], reps[1:])]})
            if empty_by:
                self.issues['omissions'].append({'person': pid, 'fact': 'parents', 'stated_by': srcs, 'left_empty_by': sorted(set(empty_by))})
        n['generation'] = OrderedDict(stored=OrderedDict((c['source'], c['value']) for c in by.get('generation.stored', [])),
                                      stored_claims=[c['id'] for c in by.get('generation.stored', [])])
        ids = OrderedDict(wikidata=None, enwiki=None)
        seen_ids = {'wikidata': OrderedDict(), 'enwiki': OrderedDict()}       # every value any source gives, in precedence order
        for c in by.get('sitelink', []):
            if c['value']['site'] == 'enwiki':
                seen_ids['enwiki'].setdefault(enwiki_key(c['value']['title']) if self.resolved else c['value']['title'], []).append(c['source'])
        strong = set()
        for c in by.get('exid', []):
            t, v = c['value'].get('type'), c['value'].get('value')
            if t == gedcom7.EXID_WIKIDATA:
                seen_ids['wikidata'].setdefault(v, []).append(c['source'])
                if GRADE_RANK.get(c['grade'], 0) >= GRADE_RANK['Likely']:
                    strong.add(v)
            elif t == gedcom7.EXID_ENWIKI:
                seen_ids['enwiki'].setdefault(enwiki_key(v) if self.resolved else v, []).append(c['source'])
            else:
                ids.setdefault('other', []).append({'type': t, 'value': v})
        for k in ('wikidata', 'enwiki'):
            vals = list(seen_ids[k].items())
            if k == 'wikidata' and self.resolved and vals:      # a QID below Likely is kept as a candidate, never as the person's id
                vals.sort(key=lambda kv: kv[0] not in strong)
                if vals[0][0] not in strong:
                    ids['wikidata_candidates'] = [v for v, _ in vals]
                    vals = []
            if vals:
                ids[k] = vals[0][0]
            if len(vals) > 1:                                  # one person, two identifiers: kept and reported, never silently dropped
                ids[k + '_alternatives'] = [v for v, _ in vals[1:]]
                self.issues['conflicts'].append({'person': pid, 'fact': k, 'accepted': vals[0][0], 'accepted_by': sorted(set(vals[0][1])),
                                                 'alternatives': [{'value': v, 'by': sorted(set(b))} for v, b in vals[1:]]})
        ids['wikidata_status'] = 'from-source' if ids['wikidata'] else ('resolvable-by-sitelink' if ids['enwiki'] else 'none')
        ids['claims'] = [c['id'] for c in by.get('sitelink', []) + by.get('exid', [])]
        n['ids'] = ids
        br = OrderedDict()
        for c in by.get('branch', []):
            br.setdefault(c['value'], []).append(c)
        n['branch'] = None
        if br:
            # labels that name the same house (or no house: a family label such as 'Darwin') do not compete; a label that names a
            # house is preferred to one that names none (curated/houses.json, read through house_of)
            hk = OrderedDict((b, self.house_of(ds, b)) for b in br)
            bname = next((b for b in br if hk[b]), next(iter(br)))
            bcl = br[bname]
            n['branch'] = self.branch_for(ds, bname)
            edges.append(OrderedDict(s=pid, p='member_of', t=n['branch'], grade=best_grade(c['grade'] for c in bcl), prov='doc', claims=[c['id'] for c in bcl]))
            rivals = [b for b in br if b != bname and (hk[b] or not self.resolved) and hk[b] != hk[bname]]
            if rivals:
                self.issues['conflicts'].append({'person': pid, 'fact': 'branch', 'accepted': bname, 'accepted_by': sorted({c['source'] for c in bcl}),
                                                 'alternatives': [{'value': k, 'by': sorted({c['source'] for c in br[k]})} for k in rivals]})
        notes = OrderedDict()
        for c in by.get('note', []):
            notes.setdefault(c['value'], []).append(c)
        n['notes'] = [OrderedDict(text=t, claims=[c['id'] for c in g], grade=best_grade(c['grade'] for c in g)) for t, g in notes.items()]
        n['media'] = [OrderedDict(url=c['value']['url'], kind=c['value']['kind'], grade=c['grade'], claims=[c['id']]) for c in by.get('media', [])]
        n['achievements'] = [OrderedDict(text=c['value'], claims=[c['id']]) for c in by.get('achievement', [])]
        n['restrictions'] = sorted({r for c in by.get('restriction', []) for r in c['value']})
        n['decisions'] = [OrderedDict(why=c['value'], source=c['source'], grade=c['grade'], prov=c['prov'], claims=[c['id']]) for c in by.get('why', [])]
        n['grade'] = best_grade(c['grade'] for c in by.get('name', [])) or 'Suspected'
        n['prov'] = by['name'][0]['prov'] if by.get('name') else 'doc'
        if self.resolved:                                       # merge-stage fields (harvest and fact-check sources)
            n['aliases'] = list(OrderedDict.fromkeys(c['value'] for c in by.get('alias', []) if c['value'] not in names))
            n['core'] = (True if any(c['value'] is True for c in by.get('core', [])) else False) if by.get('core') else None
            n['family'] = by['family'][0]['value'] if by.get('family') else None
            if len({c['value'] for c in by.get('family', [])}) > 1:
                n['family_alternatives'] = list(OrderedDict.fromkeys(c['value'] for c in by['family'][1:] if c['value'] != n['family']))
            n['living_flag'] = OrderedDict(value=True, by=sorted({c['source'] for c in by['living_possible']})) if by.get('living_possible') else None
            n['sex_by'] = sorted({c['source'] for c in by.get('sex', [])})
            if len({c['value'] for c in by.get('sex', [])}) > 1:
                self.issues['conflicts'].append({'person': pid, 'fact': 'sex', 'accepted': by['sex'][0]['value'],
                                                 'alternatives': [{'value': c['value'], 'by': [c['source']]} for c in by['sex'] if c['value'] != by['sex'][0]['value']]})
            n['titles'] = list(OrderedDict.fromkeys(c['value'] for c in by.get('title', [])))
            n['occupations'] = list(OrderedDict.fromkeys(c['value'] for c in by.get('occupation', [])))
            n['cites'] = list(OrderedDict.fromkeys(u for c in cs for u in (c.get('cites') or [])))
            n['source_conflicts'] = [OrderedDict(text=c['value'], source=c['source'], claim=c['id']) for c in by.get('source.conflict', [])]
        work = {'parents': P, 'spouse': by.get('spouse', []), 'famc': by.get('famc', []), 'fams': by.get('fams', []), 'children': by.get('children.stated', []),
                'by': by}
        return n, work

    def unions(self, nodes, work, unions_x):
        unions, index = OrderedDict(), {}
        challenged = []

        def key(partners):
            return ('pair', tuple(sorted(partners))) if len(partners) == 2 else ('open', partners[0] if partners else None)

        def new(uid, partners, kind):
            u = OrderedDict(id=uid, cls='Union', dataset=uid.split(':', 1)[1].split('/')[0], label=None, partners=list(partners), partner_unknown=len(partners) < 2,
                            children=[], pedigree=OrderedDict(), type=kind, claims=[],
                            evidence=OrderedDict(explicit=False, spouse_claims=0, symmetric_in=[], one_sided_in=[], co_parent_children=0))
            unions[uid] = u
            return u

        for uid, cs in unions_x.items():                                  # explicit unions (GEDCOM FAM)
            partners = [c['refs'][0]['id'] for c in sorted([c for c in cs if c['predicate'] == 'partner'], key=lambda c: c.get('slot', ''))]
            u = new(uid, partners, 'marriage' if any(c['predicate'] == 'marriage' for c in cs) else 'unknown')
            u['evidence']['explicit'] = True
            u['claims'] = [c['id'] for c in cs]
            for c in cs:
                if c['predicate'] == 'child':
                    ch = c['refs'][0]['id']
                    famc = next((f for f in work.get(ch, {}).get('famc', []) if f['refs'][0]['id'] == uid), {})
                    if famc.get('stat') in ('CHALLENGED', 'DISPROVEN'):           # GEDCOM 7 FAMC.STAT: a link kept as an alternative, not as parentage
                        challenged.append((ch, uid, famc['stat'], [c['id'], famc['id']]))
                        continue
                    u['children'].append(ch); u['pedigree'][ch] = famc.get('pedigree') or 'BIRTH'
                elif c['predicate'] == 'marriage' and isinstance(c['value'], dict):
                    u['marriage_date'] = c['value']
                elif c['predicate'] == 'marriage.place':
                    u['marriage_place'] = self.place_for(c['value'], c)
            index.setdefault(key(partners), uid)

        for pid in nodes:                                                 # spouse fields: each side is evidence for one union
            for c in work[pid]['spouse']:
                ref = c['refs'][0]
                in_src = ref['local'] in self.records_in[c['source']]
                if not in_src or ref['id'] not in self.person_ids:
                    self.issues['dangling'].append({'source': c['source'], 'person': pid, 'field': 'spouse', 'ref': ref['local'], 'resolved_in_merge': ref['id'] in self.person_ids})
                if ref['id'] not in self.person_ids:
                    continue
                k = key([pid, ref['id']])
                if k not in index:
                    index[k] = new('union:%s/%s' % (nodes[pid]['dataset'], '+'.join(sorted([local_of(pid), local_of(ref['id'])]))), [pid, ref['id']], 'marriage')['id']
                u = unions[index[k]]
                u['type'] = 'marriage'
                if c['id'] not in u['claims']:
                    u['claims'].append(c['id'])
                u['evidence']['spouse_claims'] += 1
        for u in unions.values():                                         # symmetry of the spouse field, per source
            if len(u['partners']) != 2:
                continue
            said = defaultdict(set)
            for x in u['claims']:
                c = self.cby[x]
                if c['predicate'] == 'spouse':
                    said[c['source']].add(c['subject'])
            for s in sorted(said):
                (u['evidence']['symmetric_in'] if said[s] == set(u['partners']) else u['evidence']['one_sided_in']).append(s)
                if said[s] != set(u['partners']):
                    self.issues['spouse-asymmetry'].append({'source': s, 'union': u['id'], 'stated_by': sorted(said[s])})

        self.alt_parent_edges = []
        for ch, uid, stat, cl in challenged:
            for par in unions[uid]['partners']:
                self.alt_parent_edges.append(OrderedDict(s=ch, p='alt_parent', t=par, grade='Suspected', prov='doc', status='contested', claims=cl, gedcom_stat=stat))
        for uid in [u for u in unions if '/alt~' in u and not unions[u]['children']]:   # a GEDCOM export's carrier of a challenged link only
            del unions[uid]
        for pid in nodes:                                                 # parent sets: children hang on the union of their parents
            P = work[pid]['parents']
            if not P:
                continue
            for c in P['claims'] + [x for g in P['alternatives'] for x in g]:
                if c['source'] in self.overlays:                        # an overlay names people that live in other sources by design
                    continue
                for r in c['refs']:
                    if r['local'] not in self.records_in[c['source']]:
                        self.issues['dangling'].append({'source': c['source'], 'person': pid, 'field': 'parents', 'ref': r['local'], 'resolved_in_merge': r['id'] in self.person_ids})
            ids = []
            for r in P['rep']['refs']:                                    # the author's order, kept for the partner slots
                if r['id'] in self.person_ids and r['id'] not in ids:
                    ids.append(r['id'])
            if not ids:
                continue
            k = key(ids)
            if k not in index:
                uid = 'union:%s/%s' % (nodes[pid]['dataset'], '+'.join(sorted(local_of(i) for i in ids)) + ('+?' if len(ids) == 1 else ''))
                index[k] = new(uid, ids, 'unknown' if len(ids) == 2 else 'open')['id']
            u = unions[index[k]]
            if pid not in u['children']:
                u['children'].append(pid); u['pedigree'][pid] = 'BIRTH'
            u['evidence']['co_parent_children'] += 1
            for c in P['claims']:
                if c['id'] not in u['claims']:
                    u['claims'].append(c['id'])
            for g, rp in zip(P['alternatives'], P['alt_reps']):
                for r in rp['refs']:
                    if r['id'] in self.person_ids and r['id'] not in ids:
                        self.alt_parent_edges.append(OrderedDict(s=pid, p='alt_parent', t=r['id'], grade=rp['grade'], prov='doc', status='contested', claims=[c['id'] for c in g]))

        for pid in nodes:                                                 # GEDCOM FAMC/FAMS must agree with FAM HUSB/WIFE/CHIL
            for c in work[pid]['famc']:
                if c.get('stat') in ('CHALLENGED', 'DISPROVEN'):
                    continue
                u = unions.get(c['refs'][0]['id'])
                if not u or pid not in u['children']:
                    self.issues['gedcom-links'].append({'person': pid, 'pointer': 'FAMC ' + c['refs'][0]['local'], 'problem': 'no matching FAM.CHIL'})
            for c in work[pid]['fams']:
                u = unions.get(c['refs'][0]['id'])
                if not u or pid not in u['partners']:
                    self.issues['gedcom-links'].append({'person': pid, 'pointer': 'FAMS ' + c['refs'][0]['local'], 'problem': 'no matching FAM.HUSB/WIFE'})

        for u in unions.values():                                         # dates and stated relationships carried by spouse claims
            sp = [self.cby[x] for x in u['claims'] if self.cby[x]['predicate'] == 'spouse']
            for key, field in (('married', 'marriage_date'), ('ended', 'end_date')):
                dated = [c for c in sp if c.get(key)]
                if not dated or u.get(field):
                    continue
                groups, reps = date_groups(dated, key=lambda c, key=key: c[key])
                u[field] = reps[0][key]
                u[field + '_claims'] = [c['id'] for c in groups[0]]
                u['_rival_' + key] = sorted({self.family_of(c['source']) for g in groups[1:] for c in g})
                if len(groups) > 1:
                    self.issues['conflicts'].append({'union': u['id'], 'fact': field, 'accepted': reps[0][key]['gedcom'], 'accepted_by': sorted({c['source'] for c in groups[0]}),
                                                     'alternatives': [{'value': r[key]['gedcom'], 'by': sorted({c['source'] for c in g})} for g, r in zip(groups[1:], reps[1:])]})
            rel = [OrderedDict(value=c['stated_relationship'], source=c['source'], claim=c['id']) for c in sp if c.get('stated_relationship')]
            if rel:
                u['stated_relationship'] = rel

        def by_birth(p):
            f = nodes[p]['facts'].get('birth')
            y = gdates.year_bounds(f['date'])[0] if f and f.get('date') else None
            return (y if y is not None else 99999, p)
        for u in unions.values():
            u['children'].sort(key=by_birth)
            u['pedigree'] = OrderedDict((ch, u['pedigree'][ch]) for ch in u['children'])
            u['label'] = ' × '.join([nodes[p]['label'] for p in u['partners']] + (['?'] if u['partner_unknown'] else []))
            u['grade'] = best_grade(self.cby[x]['grade'] for x in u['claims']) or 'Suspected'
            u['prov'] = 'doc'
        return unions

    def derive(self, nodes, unions):
        ids = sorted(nodes)
        parents_of, partners_of, children_of = {}, defaultdict(list), defaultdict(list)
        for u in unions.values():
            for ch in u['children']:
                if u['pedigree'].get(ch, 'BIRTH') == 'BIRTH':
                    parents_of.setdefault(ch, [])
                    parents_of[ch] += [p for p in u['partners'] if p not in parents_of[ch]]
            for p in u['partners']:
                partners_of[p] += [q for q in u['partners'] if q != p]
                children_of[p] += u['children']
        self.parents_of = parents_of
        self.married_by = {}
        for u in unions.values():
            y = gdates.year_bounds(u['marriage_date'])[1] if u.get('marriage_date') else None
            if y is not None:
                for p in u['partners']:
                    self.married_by[p] = min(y, self.married_by.get(p, y))
        try:
            kinship.topo_order(ids, parents_of)
        except kinship.CycleError as e:
            self.issues['cycle'].append(str(e))
            for pid in ids:
                nodes[pid]['living'] = self.living(pid, nodes, children_of, parents_of)
            return
        gens = kinship.generation_ranges(set(ids), parents_of, partners_of, children_of)
        kin = kinship.Kinship(ids, parents_of)
        for pid in ids:
            n, g = nodes[pid], gens[pid]
            gen = n['generation']
            gen['descent'] = OrderedDict((k, g[k]) for k in ('min', 'max', 'method', 'via') if k in g)
            gen['layout'] = g['max']
            gen['layout_grade'] = 'Illustrative'
            gen['flags'] = []
            for s, v in gen['stored'].items():
                if not g['min'] <= v <= g['max']:
                    why = ('stored %d above topology: an intermediate generation is probably missing' % (v - g['max'])) if v > g['max'] else \
                          ('stored %d below topology: placed in a partner\'s cohort rather than by descent' % (g['min'] - v))
                    gen['flags'].append(OrderedDict(source=s, stored=v, derived=[g['min'], g['max']], why=why))
            if gen['flags']:
                self.issues['generation'].append({'person': pid, 'flags': gen['flags']})
            F = kin.inbreeding(pid)
            gaps = sorted(a for a in kinship.ancestor_depths(pid, parents_of) if len(parents_of.get(a, [])) == 1)
            n['metrics'] = OrderedDict(inbreeding_F=str(F), inbreeding_F_float=round(float(F), 6), F_is_lower_bound=bool(gaps), one_parent_gaps=gaps,
                                       pedigree=kinship.pedigree(pid, parents_of), prov='computed', tool='kinship.py')
        for u in unions.values():
            for s in sorted({s for ch in u['children'] for s in nodes[ch]['generation']['stored']}):
                vals = OrderedDict((ch, nodes[ch]['generation']['stored'][s]) for ch in u['children'] if s in nodes[ch]['generation']['stored'])
                if len(set(vals.values())) > 1:
                    self.issues['generation-siblings'].append({'union': u['id'], 'source': s, 'stored': vals})
            if len(u['partners']) == 2:
                ex = kinship.explain(u['partners'][0], u['partners'][1], parents_of, partners_of, kin)
                u['consanguinity'] = OrderedDict(ex, offspring_F=ex['phi'], prov='computed', tool='kinship.py')
                if ex['related']:
                    self.issues['consanguinity'].append({'union': u['id'], 'relationship': ex['relationship'], 'phi': ex['phi']})
        for pid in ids:
            n = nodes[pid]
            n['living'] = self.living(pid, nodes, children_of, parents_of)
            n['vis'] = 'public' if n['living']['value'] is False and not set(n['restrictions']) & {'CONFIDENTIAL', 'PRIVACY'} else 'redacted'

    def union_edges(self, nodes, unions, work):
        out = []
        for u in unions.values():
            for p in u['partners']:
                cl = [x for x in u['claims'] if self.cby[x]['subject'] == p or any(r['id'] == p for r in self.cby[x].get('refs', []))]
                out.append(OrderedDict(s=p, p='partner_in', t=u['id'], grade=u['grade'], prov='doc', claims=cl))
            for ch in u['children']:
                P = work[ch]['parents']
                if P:
                    cl, st = [c['id'] for c in P['claims']], P['status']
                else:
                    cl = [x for x in u['claims'] if self.cby[x]['predicate'] == 'child' and self.cby[x]['refs'][0]['id'] == ch]; st = 'single'
                out.append(OrderedDict(s=ch, p='child_of', t=u['id'], grade=u['grade'], prov='doc', claims=cl, status=st, pedigree=u['pedigree'].get(ch, 'BIRTH')))
        return out + self.alt_parent_edges

    # ---------------- merge stage ----------------
    def check_children(self, nodes, work):
        """A harvest record's children[] read in reverse: each listed child must have the record's person among its accepted
        parents, the way G08 reads spouse fields from both sides. A listed child with no record anywhere is open-world (noted)."""
        alt = {(e['s'], e['t']) for e in self.alt_parent_edges}
        for pid in nodes:
            for c in work[pid]['children']:
                for r in c.get('refs', []):
                    ch = r['id']
                    if ch not in self.person_ids:
                        self.issues['children-unresolved'].append({'source': c['source'], 'person': pid, 'child': r['local']})
                    elif pid not in self.parents_of.get(ch, []):
                        self.issues['children-asymmetry'].append({'source': c['source'], 'person': pid, 'child': ch, 'accepted_parents': self.parents_of.get(ch, []),
                                                                  'kept_as_alternative': (ch, pid) in alt})

    def grade(self, nodes, unions, work):
        """Merge-stage grading. A person is Confirmed only when two independent source families, each at least Likely on its own,
        agree on the birth window, the death window and the parent set, and no family at least Likely states otherwise. A union is
        Confirmed when two such families state the couple (as spouses or as co-parents) and none gives a rival marriage date.
        Otherwise the best claim grade stands, at most Likely (one transcribed source); a parent set contested between families
        at least Likely makes the person Suspected. Claim grades are never raised: they are what one source says."""
        L = GRADE_RANK['Likely']
        for pid, n in nodes.items():
            by, P = work[pid]['by'], work[pid]['parents']
            fam = OrderedDict()
            for pred in CORE_PREDICATES:
                for c in by.get(pred, []):
                    f = self.family_of(c['source'])
                    fam[f] = best_grade([fam[f], c['grade']]) if f in fam else c['grade']
            eligible = [f for f, g in fam.items() if GRADE_RANK.get(g, 0) >= L]

            def families_in(ev):
                out = defaultdict(set)
                for k, g in enumerate((n['facts'].get(ev) or {}).get('_groups') or []):
                    for cid in g:
                        out[self.family_of(self.cby[cid]['source'])].add(k)
                return out
            bg, dg = families_in('birth'), families_in('death')
            acc = frozenset(r['id'] for r in P['rep']['refs']) if P else frozenset()
            acc_ids = {c['id'] for c in P['claims']} if P else set()
            pstate = defaultdict(list)
            for c in by.get('parents', []):
                if c['value']:
                    pstate[self.family_of(c['source'])].append(c)
            anyone = any(pstate.get(f) for f in eligible)

            def agrees(f):
                if bg.get(f) != {0} or dg.get(f) != {0}:
                    return False
                if not anyone:
                    return True                                   # no eligible family names parents: nothing to disagree on
                cl = pstate.get(f) or []
                return bool(cl) and all(c['id'] in acc_ids and frozenset(r['id'] for r in c['refs']) == acc for c in cl)
            ok = [f for f in eligible if agrees(f)]
            rivals = [f for f in eligible if (bg.get(f, set()) - {0}) or (dg.get(f, set()) - {0}) or any(c['id'] not in acc_ids for c in pstate.get(f, []))]
            pc = any(c['id'] not in acc_ids for f in eligible for c in pstate.get(f, []))
            base = min_grade(best_grade(c['grade'] for pred in CORE_PREDICATES for c in by.get(pred, [])) or 'Suspected', 'Likely')
            if len(ok) >= 2 and not rivals:
                g, why = 'Confirmed', 'independent families agree on birth, death and parents: ' + ', '.join(ok)
            elif pc:
                g, why = 'Suspected', 'parents contested between families graded Likely or better'
            elif len(eligible) < 2:
                g, why = base, 'one source family at Likely or better' if eligible else 'no source family above Suspected'
            else:
                g, why = base, 'independent families do not both state the same birth, death and parents' + ('; rival values from ' + ', '.join(rivals) if rivals else '')
            n['grade'] = g
            n['grade_basis'] = OrderedDict(rule=why, families=fam, agreeing=ok, rivals=rivals)
        for u in unions.values():
            fams = OrderedDict()
            for x in u['claims']:
                c = self.cby[x]
                if GRADE_RANK.get(c['grade'], 0) < L:
                    continue
                if c['predicate'] in ('spouse', 'partner') or (c['predicate'] == 'parents' and set(u['partners']) <= {r['id'] for r in c.get('refs', [])}):
                    fams.setdefault(self.family_of(c['source']), set()).add(c['predicate'])
            rival = u.pop('_rival_married', []) + u.pop('_rival_ended', [])
            if len(u['partners']) == 2 and len(fams) >= 2 and not rival:
                u['grade'] = 'Confirmed'
                u['grade_basis'] = OrderedDict(rule='independent families state the couple: ' + ', '.join(fams), families=list(fams))
            else:
                u['grade'] = min_grade(u['grade'], 'Likely')
                u['grade_basis'] = OrderedDict(rule=('a rival marriage or end date from ' + ', '.join(rival)) if rival else ('stated by %d independent famil%s at Likely or better' % (len(fams), 'y' if len(fams) == 1 else 'ies')),
                                               families=list(fams))

    # ---------------- helpers ----------------
    def place_for(self, val, claim):
        pid = 'place:' + slug(val['name'])
        if pid not in self.place_nodes:
            p = OrderedDict(id=pid, cls='Place', label=val['name'], grade=claim['grade'], prov='doc', claims=[claim['id']])
            if val.get('lat') is not None and val.get('lon') is not None:
                p['geo'] = OrderedDict(lat=val['lat'], lon=val['lon'], grade=claim['grade'], prov='doc')
            self.place_nodes[pid] = p
        return pid

    def branch_for(self, ds, bname):
        gid = 'branch:%s/%s' % (ds, slug(bname))
        if gid not in self.branch_nodes:
            g = OrderedDict(id=gid, cls='Branch', dataset=ds, label=bname, grade='Suspected', prov='doc', seat=None)
            cur = self.places_cur.get(bname)
            if cur:
                plid = 'place:' + slug(cur['label'])
                if plid not in self.place_nodes:
                    self.place_nodes[plid] = OrderedDict(id=plid, cls='Place', label=cur['label'], grade=cur['grade'], prov=cur['prov'], claims=[],
                                                         geo=OrderedDict(lat=cur['lat'], lon=cur['lon'], grade=cur['grade'], prov=cur['prov']),
                                                         ids=OrderedDict(wikidata=cur.get('wikidata'), geonames=cur.get('geonames'), grade=cur['ids_grade'], prov=cur['prov']),
                                                         note=cur.get('note'))
                g['seat'] = plid
            self.branch_nodes[gid] = g
        return gid

    def living(self, pid, nodes, children_of, parents_of):
        """Policy (manifest policy.living_years): dead if a death is recorded or asserted; presumed dead if the latest
        possible birth year is more than living_years before as_of, the birth taken from the record or, failing that,
        bounded by a child's birth (a parent is at least min_parent_age older); otherwise living, the safe side."""
        n, P = nodes[pid], self.policy
        d = n['facts'].get('death')
        if d:
            return OrderedDict(value=False, rule='death recorded' if d.get('date') else 'death asserted without a date', grade=d.get('grade'))
        if n.get('living_flag'):                                # harvest living_possible: presumed living unless a death is recorded
            return OrderedDict(value=True, rule='presumed living: flagged living_possible by %s and no death recorded' % ', '.join(n['living_flag']['by']), grade='Suspected')
        b = n['facts'].get('birth')
        latest, how = (gdates.year_bounds(b['date'])[1] if b and b.get('date') else None), 'own birth'
        if latest is None:
            kids = [gdates.year_bounds(nodes[c]['facts']['birth']['date'])[1] for c in children_of.get(pid, []) if (nodes[c]['facts'].get('birth') or {}).get('date')]
            kids = [k for k in kids if k is not None]
            if kids:
                latest, how = min(kids) - P['min_parent_age'], 'bounded by a child\'s birth'
        if latest is None and self.resolved and self.married_by.get(pid) is not None:   # nobody marries before being born
            latest, how = self.married_by[pid], 'bounded by a dated marriage'
        if latest is not None and self.as_of_year - latest > P['living_years']:
            return OrderedDict(value=False, rule='presumed dead: latest possible birth %d is more than %d years before %s (%s)' % (latest, P['living_years'], self.as_of, how), grade='Likely')
        return OrderedDict(value=True, rule='presumed living: no death recorded and not provably born more than %d years before %s' % (P['living_years'], self.as_of), grade='Suspected')
