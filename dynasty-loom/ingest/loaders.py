"""Loaders: each input format to the loom claim stream. A claim is one statement one source makes about one subject:
  {kind, subject, predicate, value, locator, quote}   (+ optional quay, cites, slot, pedigree, surname)
The canonical builder adds id, source, grade and prov. Loaders never interpret: an empty `parents` list is recorded as
'stated empty' and the builder decides what that means (open world: not stated, not 'has no parents')."""
import json
import re
from urllib.parse import unquote, urlparse

import gdates
import gedcom7
import jsobj

PLACEHOLDER_HOSTS = {'picsum.photos', 'placehold.co', 'placekitten.com', 'via.placeholder.com', 'dummyimage.com'}
# fact-check records (proto/facts/*.json) add these keys to the Cosmos shape (report 02, section 5)
FACTS_FIELDS = {'spouses', 'qid', 'qid_confidence', 'born_precision', 'died_precision', 'sources', 'confidence'}
COSMOS_FIELDS = {'id', 'name', 'born', 'died', 'generation', 'parents', 'spouse', 'branch', 'note', 'wikipedia', 'imageUrl', 'achievements', 'why',
                 'wikidata', 'wikidata_detail'} | FACTS_FIELDS
GRADES = ('Confirmed', 'Likely', 'Suspected')
QID = re.compile(r'Q[1-9][0-9]*')


def precision_label(raw):
    """A source's precision note to one word: 'uncertain (1743 or 1744)' -> 'uncertain', 'day (baptism 12 July 1730)' -> 'day'."""
    if raw is None:
        return None
    w = str(raw).strip().split(' ')[0].strip('(),;:').lower()
    return w if w in ('day', 'month', 'year', 'circa', 'uncertain', 'unknown') else 'other'


def _sitelink(url):
    u = urlparse(url or '')
    m = re.fullmatch(r'([a-z\-]+)\.wikipedia\.org', u.netloc or '')
    if not m or not u.path.startswith('/wiki/'):
        return None
    return {'site': m.group(1).replace('-', '_') + 'wiki', 'title': unquote(u.path[len('/wiki/'):]), 'url': url}


def cosmos_member_claims(local, rec, path_of, line_of, text):
    """One FamilyMember record (any of the three spellings) to claims. path_of(field) gives the locator path,
    line_of(field) the 1-based line where its value starts; the quote is that verbatim line."""
    out, notes = [], []
    # fact-check keys: the record's grade caps every claim it makes (it can lower, never raise, the source's grade);
    # its cited pages ride on every claim as `cites`
    cap = rec.get('confidence') if rec.get('confidence') in GRADES else None
    cites = [s for s in rec.get('sources') or [] if isinstance(s, str)] or None
    if rec.get('confidence') is not None and cap is None:
        notes.append('%s.confidence: not a grade: %r' % (local, rec['confidence']))

    def C(pred, val, field, **kw):
        ln = line_of(field)
        d = {'kind': 'person', 'subject': local, 'predicate': pred, 'value': val, 'locator': '%s (line %s)' % (path_of(field), ln), 'quote': jsobj.line_text(text, ln) if ln else ''}
        if cap:
            d['cap'] = cap
        if cites:
            d['cites'] = cites
        d.update({k: v for k, v in kw.items() if v is not None}); out.append(d)

    if 'name' in rec:
        C('name', rec['name'], 'name')
    for f, pred in (('born', 'birth'), ('died', 'death')):
        if rec.get(f) is not None:
            try:
                C(pred, gdates.from_year(rec[f]), f, precision=precision_label(rec.get(f + '_precision')), precision_note=rec.get(f + '_precision'))
            except gdates.DateError as e:
                notes.append('%s.%s: %s' % (local, f, e))
    if 'generation' in rec:
        C('generation.stored', rec['generation'], 'generation')
    if 'parents' in rec:
        ps = list(rec['parents'] or [])
        # the fact-check files list the father first wherever the parents' sex is known (checked by ingest.py, gate G29)
        C('parents', ps, 'parents', roles=['father', 'mother'][:len(ps)] if 'spouses' in rec and len(ps) == 2 else None)     # order kept as written; compared as a set
    if isinstance(rec.get('spouses'), list):             # fact-check: one union claim per spouse, replacing the single `spouse`
        for k, s in enumerate(rec['spouses']):
            if isinstance(s, str) and s:
                C('spouse', s, ('spouses', k))
    elif rec.get('spouse'):
        C('spouse', rec['spouse'], 'spouse')
    if rec.get('qid'):
        if QID.fullmatch(str(rec['qid'])):
            C('exid', {'type': gedcom7.EXID_WIKIDATA, 'value': rec['qid']}, 'qid', qcap=rec.get('qid_confidence') if rec.get('qid_confidence') in GRADES else 'Suspected')
        else:
            notes.append('%s.qid: not a QID: %r' % (local, rec['qid']))
    if rec.get('branch'):
        C('branch', rec['branch'], 'branch')
    if rec.get('note'):
        C('note', rec['note'], 'note')
    if rec.get('wikipedia'):
        sl = _sitelink(rec['wikipedia'])
        if sl:
            C('sitelink', sl, 'wikipedia')
        else:
            notes.append('%s.wikipedia: not a Wikipedia article URL: %r' % (local, rec['wikipedia']))
    if rec.get('imageUrl'):
        host = urlparse(rec['imageUrl']).netloc
        C('media', {'url': rec['imageUrl'], 'kind': 'placeholder' if host in PLACEHOLDER_HOSTS else 'image', 'host': host}, 'imageUrl')
    if rec.get('wikidata'):
        if re.fullmatch(r'Q[1-9][0-9]*', str(rec['wikidata'])):
            C('exid', {'type': gedcom7.EXID_WIKIDATA, 'value': rec['wikidata']}, 'wikidata')
        else:
            notes.append('%s.wikidata: not a QID: %r' % (local, rec['wikidata']))
    if rec.get('wikidata_detail'):
        C('wikidata.detail', rec['wikidata_detail'], 'wikidata_detail')   # P22/P25/P26 kept for a later edge check
    if rec.get('why'):
        C('why', rec['why'], 'why')                               # a curated decision's reason (decisions.json only)
    for k, a in enumerate(rec.get('achievements') or []):
        C('achievement', a, 'achievements')
    for k in sorted(set(rec) - COSMOS_FIELDS):
        C('extra', {'field': k, 'value': rec[k]}, k)
        notes.append('%s: unknown field %r kept as extra' % (local, k))
    return out, notes


def load_json_tree(text, dataset_expected):
    """roths/data/trees/*.json: {id, name, members: [FamilyMember]}. Parsed twice (json and the located reader): both must agree."""
    data = json.loads(text)
    r = jsobj._Reader(text, text.index('{'))
    lit = r.value(()); locs = r.locs
    report = {'parse_agreement': lit == data, 'records': len(data.get('members', [])), 'dataset_id': data.get('id'), 'dataset_name': data.get('name'), 'notes': []}
    if data.get('id') != dataset_expected:
        report['notes'].append('dataset id %r != manifest %r' % (data.get('id'), dataset_expected))
    claims, seen = [], set()
    for i, m in enumerate(data.get('members', [])):
        local = m.get('id')
        if not local or local in seen:
            report['notes'].append('member %d: missing or duplicate id %r' % (i, local)); continue
        seen.add(local)
        cs, notes = cosmos_member_claims(local, m, lambda f, i=i: '/members/%d/%s' % (i, '/'.join(map(str, f if isinstance(f, tuple) else (f,)))),
                                         lambda f, i=i: locs.get(('members', i) + (f if isinstance(f, tuple) else (f,))), text)
        claims += cs; report['notes'] += notes
    return claims, report


# ---------------- harvest partitions (proto/harvest/*.json) ----------------
HARVEST_FIELDS = {'id', 'qid', 'name', 'name_native', 'aka', 'sex', 'born', 'died', 'father', 'mother', 'spouses', 'children', 'family', 'branch', 'core',
                  'living_possible', 'titles', 'occupations', 'places', 'note', 'image', 'wikipedia', 'sources', 'confidence', 'conflicts'}
HDATE = re.compile(r'(\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?')


def harvest_date(v):
    """A harvest date ('1744', '1976-04', '1744-02-23'; precision day|month|year|circa|unknown) to (canonical date or None, label).
    A date with precision 'unknown' and no value means the event is stated without a date (GEDCOM `DEAT Y`)."""
    if not isinstance(v, dict):
        return None, None
    raw, prec = v.get('date'), v.get('precision')
    if raw in (None, ''):
        return None, (prec or 'unknown')
    m = HDATE.fullmatch(str(raw).strip())
    if not m:
        raise gdates.DateError('unreadable date %r' % raw)
    c = {'kind': 'approx' if prec == 'circa' else 'exact', 'calendar': 'GREGORIAN',
         'start': {'y': int(m.group(1)), 'm': int(m.group(2)) if m.group(2) else None, 'd': int(m.group(3)) if m.group(3) else None, 'bce': False}}
    if prec == 'circa':
        c['qualifier'] = 'ABT'
    c = gdates.finish(c)
    return c, (prec if prec in ('day', 'month', 'year', 'circa') else c['precision'])


def load_harvest(text, dataset_expected=None):
    """proto/harvest/*.json: {partition, group, persons[], extra}. Parsed twice (json and the located reader); every claim quotes the
    verbatim line its value starts on. Ids are QIDs (global), `wp:<enwiki title>` or provisional `x:<name>-<year>` (local to the
    file; identity.py decides what they match). Nothing is interpreted here: father/mother become one ordered `parents` claim with
    roles, each spouse a `spouse` claim carrying its marriage and end dates, `children` a list checked later against the parent
    links, `core` a view flag, `living_possible` a privacy flag; the record's `confidence` caps its claims, its `sources` are cited."""
    data = json.loads(text)
    r = jsobj._Reader(text, text.index('{'))
    lit = r.value(()); locs = r.locs
    persons = data.get('persons') or []
    report = {'parse_agreement': lit == data, 'records': len(persons), 'dataset_id': data.get('partition'), 'dataset_name': data.get('group'), 'notes': []}
    claims, seen = [], set()

    for i, p in enumerate(persons):
        local = p.get('id')
        if not local or local in seen:
            report['notes'].append('person %d: missing or duplicate id %r' % (i, local)); continue
        seen.add(local)
        cap = p.get('confidence') if p.get('confidence') in GRADES else 'Suspected'
        if p.get('confidence') not in GRADES:
            report['notes'].append('%s: confidence %r is not a grade; claims capped at Suspected' % (local, p.get('confidence')))
        cites = [s for s in p.get('sources') or [] if isinstance(s, str)] or None

        def C(pred, val, path, i=i, local=local, cap=cap, cites=cites, **kw):
            path = path if isinstance(path, tuple) else (path,)
            ln = locs.get(('persons', i) + path)
            d = {'kind': 'person', 'subject': local, 'predicate': pred, 'value': val, 'locator': '/persons/%d/%s (line %s)' % (i, '/'.join(map(str, path)), ln),
                 'quote': jsobj.line_text(text, ln) if ln else '', 'cap': cap}
            if cites:
                d['cites'] = cites
            d.update({k: v for k, v in kw.items() if v is not None}); claims.append(d)

        if local.startswith('x:'):
            report['notes'].append('%s: provisional id (local to this file)' % local)
        if p.get('name'):
            C('name', p['name'], 'name')
        if p.get('name_native') and p['name_native'] != p.get('name'):
            C('alias', p['name_native'], 'name_native', alias_type='native')
        for k, a in enumerate(p.get('aka') or []):
            if isinstance(a, str) and a:
                C('alias', a, ('aka', k), alias_type='aka')
        if p.get('sex') in ('M', 'F', 'X', 'U'):
            C('sex', p['sex'], 'sex')
        for f, pred in (('born', 'birth'), ('died', 'death')):
            v = p.get(f)
            if not isinstance(v, dict):
                continue
            try:
                d, label = harvest_date(v)
            except gdates.DateError as e:
                report['notes'].append('%s.%s: %s' % (local, f, e)); continue
            if d:
                C(pred, d, (f, 'date'), precision=label)
            elif label == 'unknown' and f == 'died':
                C(pred + '.occurred', True, f, precision='unknown')
            if v.get('place'):
                C(pred + '.place', {'name': v['place'], 'qid': v.get('place_qid')}, (f, 'place'))
        ps, roles = [], []
        for role in ('father', 'mother'):
            if isinstance(p.get(role), str) and p[role]:
                ps.append(p[role]); roles.append(role)
        if ps:
            C('parents', ps, roles[0], roles=roles)
        for k, s in enumerate(p.get('spouses') or []):
            if isinstance(s, dict) and s.get('id'):
                kw = {}
                for key in ('married', 'ended'):
                    if s.get(key):
                        try:
                            kw[key] = harvest_date({'date': s[key], 'precision': None})[0]
                        except gdates.DateError as e:
                            report['notes'].append('%s.spouses[%d].%s: %s' % (local, k, key, e))
                C('spouse', s['id'], ('spouses', k, 'id'), stated_relationship=s.get('relationship'), **kw)
        if p.get('children'):
            C('children.stated', [c for c in p['children'] if isinstance(c, str)], 'children')
        if p.get('family'):
            C('family', p['family'], 'family')
        if p.get('branch'):
            C('branch', p['branch'], 'branch')
        if isinstance(p.get('core'), bool):
            C('core', p['core'], 'core')
        if p.get('living_possible') is True:
            C('living_possible', True, 'living_possible')
        for k, t in enumerate(p.get('titles') or []):
            C('title', t, ('titles', k))
        for k, t in enumerate(p.get('occupations') or []):
            C('occupation', t, ('occupations', k))
        for k, t in enumerate(p.get('places') or []):
            C('place.assoc', t, ('places', k))
        if p.get('note'):
            C('note', p['note'], 'note')
        if p.get('image'):
            host = urlparse(p['image']).netloc
            C('media', {'url': p['image'], 'kind': 'placeholder' if host in PLACEHOLDER_HOSTS else 'image', 'host': host}, 'image')
        if p.get('wikipedia'):
            sl = _sitelink(p['wikipedia'])
            if sl:
                C('sitelink', sl, 'wikipedia')
            else:
                report['notes'].append('%s.wikipedia: not a Wikipedia article URL: %r' % (local, p['wikipedia']))
        if p.get('qid'):
            if QID.fullmatch(str(p['qid'])):
                C('exid', {'type': gedcom7.EXID_WIKIDATA, 'value': p['qid']}, 'qid')
            else:
                report['notes'].append('%s.qid: not a QID: %r' % (local, p['qid']))
        for k, t in enumerate(p.get('conflicts') or []):
            C('source.conflict', t, ('conflicts', k))             # the harvester's own note of disagreeing sources
        for k in sorted(set(p) - HARVEST_FIELDS):
            C('extra', {'field': k, 'value': p[k]}, k)
            report['notes'].append('%s: unknown field %r kept as extra' % (local, k))
    # dated events the harvester recorded beside the persons (extra.events): claims about the partition itself
    for k, ev in enumerate((data.get('extra') or {}).get('events') or []):
        if isinstance(ev, dict) and ev.get('label'):
            ln = locs.get(('extra', 'events', k, 'label'))
            claims.append({'kind': 'source', 'subject': 'events', 'predicate': 'event', 'value': ev, 'locator': '/extra/events/%d (line %s)' % (k, ln),
                           'quote': jsobj.line_text(text, ln) if ln else '', 'cites': [ev['source']] if ev.get('source') else None})
    return claims, report


def load_literal(text, var):
    """family.ts or a standalone HTML page: `const familyData = { id: {...}, ... }` read as data (jsobj), never run."""
    lit, locs, start = jsobj.find_literal(text, var)
    if not isinstance(lit, dict):
        raise jsobj.JSDataError('%s is not an object literal' % var)
    report = {'parse_agreement': None, 'records': len(lit), 'binding_line': start, 'notes': []}
    claims = []
    for key, m in lit.items():
        if not isinstance(m, dict):
            report['notes'].append('%s: record is not an object' % key); continue
        if 'id' in m and m['id'] != key:
            report['notes'].append('record key %r != id field %r' % (key, m['id']))
        cs, notes = cosmos_member_claims(key, m, lambda f, k=key: '%s.%s.%s' % (var, k, f), lambda f, k=key: locs.get((k, f)), text)
        claims += cs; report['notes'] += notes
    return claims, report


def load_gedcom(text, label):
    recs = gedcom7.parse(text)
    claims, rep = gedcom7.import_claims(recs, label)
    rep['parse_agreement'] = None
    rep['notes'] = ['unread structure: ' + u for u in rep.pop('unread')]
    return claims, rep


PARSERS = {'json-tree': 'load_json_tree', 'ts-literal': 'load_literal', 'html-literal': 'load_literal', 'gedcom7': 'load_gedcom', 'harvest': 'load_harvest'}


def load(spec, text):
    p = spec['parser']
    if p == 'json-tree':
        return load_json_tree(text, spec.get('expect_id', spec['dataset']))
    if p == 'harvest':
        return load_harvest(text, spec['dataset'])
    if p in ('ts-literal', 'html-literal'):
        return load_literal(text, spec.get('var', 'familyData'))
    if p == 'gedcom7':
        return load_gedcom(text, spec['path'])
    raise ValueError('unknown parser %r' % p)
