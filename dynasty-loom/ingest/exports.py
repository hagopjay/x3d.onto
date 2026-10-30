"""Views of the canonical graph: JSON-LD, GEDCOM X JSON, the Cosmos app's FamilyDataset shape, and the public candidate.

JSON-LD follows graph-v3.jsonld (gobbler-v3/tools/build_page.py): the same `name`, `prov`, `grade` terms and px prefix,
nodes as typed resources, every relation a px:Statement with provenance, grade and evidence. Genealogy terms live in
gg:, with schema.org types beside them for outside tools; claims are px:Statements too, each pointing at its source.
"""
import copy
import re
from collections import OrderedDict

GG = 'https://polyxandria.example/genealogy#'
GID = 'https://polyxandria.example/genealogy/id/'
CONF = {'Confirmed': 'http://gedcomx.org/High', 'Likely': 'http://gedcomx.org/Medium', 'Suspected': 'http://gedcomx.org/Low'}
SEX_GX = {'M': 'http://gedcomx.org/Male', 'F': 'http://gedcomx.org/Female', 'X': 'http://gedcomx.org/Intersex', 'U': 'http://gedcomx.org/Unknown'}


def _iri(x):
    return 'gid:' + x.replace(':', '/', 1)


def _xsd(d):
    if not d or d.get('kind') != 'exact' or d.get('calendar') != 'GREGORIAN' or not d.get('edtf'):
        return None
    return {'@value': d['edtf'], '@type': {'year': 'xsd:gYear', 'month': 'xsd:gYearMonth', 'day': 'xsd:date'}[d['precision']]}


def jsonld(g):
    ctx = OrderedDict([('@version', 1.1), ('@vocab', GG), ('gg', GG), ('gid', GID), ('px', 'https://polyxandria.example/kg#'), ('schema', 'http://schema.org/'),
                       ('provo', 'http://www.w3.org/ns/prov#'), ('wd', 'http://www.wikidata.org/entity/'), ('xsd', 'http://www.w3.org/2001/XMLSchema#'),
                       ('name', 'http://schema.org/name'), ('prov', 'px:provenance'), ('grade', 'px:grade'),
                       ('sameAs', {'@id': 'schema:sameAs', '@type': '@id'}), ('partner', {'@id': 'gg:partner', '@type': '@id', '@container': '@list'}),
                       ('child', {'@id': 'gg:child', '@type': '@id'}), ('wasDerivedFrom', {'@id': 'provo:wasDerivedFrom', '@type': '@id'}),
                       ('claims', {'@id': 'gg:claim', '@type': '@id'}), ('value', {'@id': 'px:value', '@type': '@json'})])
    gr = []
    for s in g['sources']:
        gr.append(OrderedDict([('@id', _iri(s['id'])), ('@type', ['gg:Source', 'provo:Entity']), ('name', s['title']), ('gg:sha256', s.get('sha256')),
                               ('gg:sourceFamily', s['family']), ('grade', s['default_grade'])]))
    for n in g['nodes']:
        d = OrderedDict([('@id', _iri(n['id'])), ('name', n['label']), ('prov', n['prov']), ('grade', n['grade'])])
        if n['cls'] == 'Person':
            d['@type'] = ['gg:Person', 'schema:Person']
            for ev, prop in (('birth', 'birthDate'), ('death', 'deathDate')):
                f = (n.get('facts') or {}).get(ev)
                if f and f.get('date'):
                    x = _xsd(f['date'])
                    if x:
                        d['schema:' + prop] = x
                    d['gg:' + prop + 'EDTF'] = f['date']['edtf']
                    d['gg:' + ev + 'Status'] = f['status']
                    d['gg:' + ev + 'Claims'] = [{'@id': 'gid:' + c} for c in f['claims']]
            ids = n.get('ids') or {}
            same = (['https://en.wikipedia.org/wiki/' + ids['enwiki']] if ids.get('enwiki') else []) + (['wd:' + ids['wikidata']] if ids.get('wikidata') else [])
            if same:
                d['sameAs'] = same
            gen = n.get('generation') or {}
            if gen.get('descent'):
                d['gg:generationMin'] = gen['descent']['min']; d['gg:generationMax'] = gen['descent']['max']
            if (n.get('metrics') or {}).get('inbreeding_F') is not None:
                d['gg:inbreedingF'] = n['metrics']['inbreeding_F']
            if n.get('living'):
                d['gg:living'] = n['living']['value']
            if n.get('branch'):
                d['gg:memberOf'] = {'@id': _iri(n['branch'])}
        elif n['cls'] == 'Union':
            d['@type'] = ['gg:Union']
            d['partner'] = [_iri(p) for p in n['partners']]
            d['child'] = [_iri(c) for c in n['children']]
            d['gg:unionType'] = n['type']; d['gg:partnerUnknown'] = n['partner_unknown']
            if n.get('consanguinity', {}).get('related'):
                d['gg:kinship'] = n['consanguinity']['phi']; d['gg:relationship'] = n['consanguinity']['relationship']
        elif n['cls'] == 'Place':
            d['@type'] = ['gg:Place', 'schema:Place']
            if n.get('geo'):
                d['schema:geo'] = OrderedDict([('@type', 'schema:GeoCoordinates'), ('schema:latitude', n['geo']['lat']), ('schema:longitude', n['geo']['lon']), ('grade', n['geo']['grade'])])
            if (n.get('ids') or {}).get('wikidata'):
                d['sameAs'] = ['wd:' + n['ids']['wikidata']]
        elif n['cls'] == 'Branch':
            d['@type'] = ['gg:Branch']
            if n.get('seat'):
                d['gg:seat'] = {'@id': _iri(n['seat'])}
        gr.append(d)
    for k, e in enumerate(g['edges']):
        gr.append(OrderedDict([('@id', 'gid:statement/%d' % k), ('@type', 'px:Statement'), ('px:subject', {'@id': _iri(e['s'])}), ('px:predicate', e['p']),
                               ('px:object', {'@id': _iri(e['t'])}), ('prov', e['prov']), ('grade', e['grade'])] +
                              ([('claims', ['gid:' + c for c in e['claims']])] if e.get('claims') else []) + ([('gg:status', e['status'])] if e.get('status') else [])))
    for c in g['claims']:
        gr.append(OrderedDict([('@id', 'gid:' + c['id']), ('@type', 'px:Statement'), ('px:subject', {'@id': _iri(c['subject'])}), ('px:predicate', c['predicate']),
                               ('value', c['value']), ('prov', c['prov']), ('grade', c['grade']), ('px:evidence', c['quote']), ('gg:locator', c['locator']),
                               ('wasDerivedFrom', _iri(c['source']))]))
    return OrderedDict([('@context', ctx), ('@graph', gr)])


def gedcomx(g):
    """GEDCOM X JSON. GEDCOM X has no union entity: a union becomes a Couple relationship (when both partners are known)
    and one ParentChild relationship per known parent and child. Contested alternatives become extra facts at Low
    confidence, which is how GEDCOM X keeps competing conclusions. What is lost is listed in x-loom-losses."""
    def gid(x):
        return re.sub(r'[^A-Za-z0-9]+', '-', x).strip('-')
    nodes = {n['id']: n for n in g['nodes']}
    claims = {c['id']: c for c in g['claims']}
    out = OrderedDict(persons=[], relationships=[], places=[], sourceDescriptions=[])
    for s in g['sources']:
        out['sourceDescriptions'].append(OrderedDict(id=gid(s['id']), resourceType='http://gedcomx.org/DigitalArtifact', titles=[{'value': s['title']}]))
    wiki = OrderedDict()
    for n in g['nodes']:
        if n['cls'] == 'Place':
            pd = OrderedDict(id=gid(n['id']), names=[{'value': n['label']}])
            if n.get('geo'):
                pd['latitude'] = n['geo']['lat']; pd['longitude'] = n['geo']['lon']
            out['places'].append(pd)
    for n in g['nodes']:
        if n['cls'] != 'Person':
            continue
        p = OrderedDict(id=gid(n['id']))
        if (n.get('sex') or {}).get('value') in SEX_GX:                   # unstated stays unstated (open world)
            p['gender'] = {'type': SEX_GX[n['sex']['value']]}
        p.update(names=[OrderedDict(preferred=(k == 0), nameForms=[{'fullText': nm['value']}]) for k, nm in enumerate(n.get('names', []))] or [{'nameForms': [{'fullText': n['label']}]}])
        facts = []

        def fact(t, date, cl, conf, alt=False, place=None):
            f = OrderedDict(type=t)
            if date:
                f['date'] = OrderedDict(original=date['gedcom'] or date.get('phrase'), formal=date['gedcomx'])
            if place and place in nodes:
                f['place'] = OrderedDict(original=nodes[place]['label'], description='#' + gid(place))
            f['sources'] = [OrderedDict(description='#' + gid(claims[c]['source'])) for c in cl if c in claims][:3]
            if conf in CONF:
                f['confidence'] = CONF[conf]
            f['notes'] = [{'subject': 'locator', 'text': claims[c]['locator']} for c in cl if c in claims][:3] + ([{'subject': 'loom', 'text': 'alternative (contested)'}] if alt else [])
            facts.append(f)
        for ev, t in (('birth', 'http://gedcomx.org/Birth'), ('death', 'http://gedcomx.org/Death')):
            f = (n.get('facts') or {}).get(ev)
            if f:
                fact(t, f.get('date'), f['claims'], f.get('grade'), place=f.get('place'))
                for a in f.get('alternatives', []):
                    fact(t, a['date'], a['claims'], 'Suspected', alt=True)
        if facts:
            p['facts'] = facts
        ids = n.get('ids') or {}
        if ids.get('wikidata'):
            p['identifiers'] = {'http://gedcomx.org/Persistent': ['http://www.wikidata.org/entity/' + ids['wikidata']]}
        if ids.get('enwiki'):
            sid = 'wikipedia-' + gid(ids['enwiki'])
            wiki[sid] = OrderedDict(id=sid, resourceType='http://gedcomx.org/DigitalArtifact', about='https://en.wikipedia.org/wiki/' + ids['enwiki'],
                                    titles=[{'value': 'Wikipedia: ' + ids['enwiki'].replace('_', ' ')}])
            p['sources'] = [{'description': '#' + sid}]
        out['persons'].append(p)
    out['sourceDescriptions'] += list(wiki.values())
    for n in g['nodes']:
        if n['cls'] != 'Union':
            continue
        if len(n['partners']) == 2:
            r = OrderedDict(id=gid(n['id']), type='http://gedcomx.org/Couple', person1={'resource': '#' + gid(n['partners'][0])}, person2={'resource': '#' + gid(n['partners'][1])})
            if n['type'] == 'marriage':
                r['facts'] = [{'type': 'http://gedcomx.org/Marriage'}]
            if n['grade'] in CONF:
                r['confidence'] = CONF[n['grade']]
            out['relationships'].append(r)
        for ch in n['children']:
            for par in n['partners']:
                out['relationships'].append(OrderedDict(id=gid('pc-%s-%s' % (par, ch)), type='http://gedcomx.org/ParentChild',
                                                        person1={'resource': '#' + gid(par)}, person2={'resource': '#' + gid(ch)}))
    out['x-loom-losses'] = ['union nodes (open unions keep only their known parent)', 'loom grade beyond High/Medium/Low', 'generation, kinship, pedigree metrics',
                            'branch membership and seat places', 'claim locators survive only as notes', 'stored generation and its flags']
    return out


def cosmos_compat(g, datasets):
    """The FamilyDataset[] the current app loads, regenerated from the canonical graph. `spouse` stays single (the app's
    limit: the first union's other partner); the new fields carry what the app does not read yet. Placeholder images are
    dropped so the app falls back to the Wikipedia thumbnail instead of showing a stock photo as a person."""
    nodes = {n['id']: n for n in g['nodes']}
    unions = [n for n in g['nodes'] if n['cls'] == 'Union']
    out = []
    for ds, meta in datasets.items():
        members = []
        for n in g['nodes']:
            if n['cls'] != 'Person' or n['dataset'] != ds:
                continue
            pars = next(([p for p in u['partners']] for u in unions if n['id'] in u['children']), [])
            mine = [u for u in unions if n['id'] in u['partners']]
            sps = [q for u in mine for q in u['partners'] if q != n['id']]
            b = (n['facts'].get('birth') or {}).get('date'); d = (n['facts'].get('death') or {}).get('date')
            m = OrderedDict(id=n['local'], name=n['label'], born=b['start']['y'] if b and b.get('start') else None)
            if d and d.get('start'):
                m['died'] = d['start']['y']
            m['generation'] = (n.get('generation') or {}).get('layout')
            m['parents'] = [nodes[p]['local'] for p in pars]
            if sps:
                m['spouse'] = nodes[sps[0]]['local']
            if n.get('branch'):
                m['branch'] = nodes[n['branch']]['label']
            m['note'] = n['notes'][0]['text'] if n.get('notes') else ''
            if (n.get('ids') or {}).get('enwiki'):
                m['wikipedia'] = 'https://en.wikipedia.org/wiki/' + n['ids']['enwiki']
            imgs = [x['url'] for x in n.get('media', []) if x['kind'] != 'placeholder']
            if imgs:
                m['imageUrl'] = imgs[0]
            m['spouses'] = [nodes[q]['local'] for q in sps]
            m['unions'] = [u['id'] for u in mine]
            gen = n.get('generation') or {}
            if gen.get('descent'):
                m['generationRange'] = [gen['descent']['min'], gen['descent']['max']]
            m['living'] = (n.get('living') or {}).get('value')
            m['grade'] = n['grade']
            m['contested'] = [k for k, f in n['facts'].items() if f.get('status') == 'contested'] + (['parents'] if any(e['s'] == n['id'] and e['p'] == 'alt_parent' for e in g['edges']) else [])
            if (n.get('metrics') or {}).get('inbreeding_F_float') is not None:
                m['inbreedingF'] = n['metrics']['inbreeding_F_float']
            members.append(m)
        out.append(OrderedDict(id=ds, name=meta['name'], members=members))
    return out


LABEL_PRIVATE = 'Living or private person'
LABEL_WITHHELD = 'Withheld record'


PRIVATE_TEXT = '[private person]'


def hidden_names(hidden_nodes, public_nodes):
    """Names a hidden person is known by that no public person also carries (5 characters or more), longest first."""
    shown = {x['value'] for n in public_nodes for x in n.get('names') or []} | {a for n in public_nodes for a in n.get('aliases') or []}
    out = {x['value'] for n in hidden_nodes for x in n.get('names') or []} | {a for n in hidden_nodes for a in n.get('aliases') or []}
    return sorted((x for x in out if len(x) >= 5 and x not in shown), key=lambda x: (-len(x), x))


def scrub(obj, pat):
    if isinstance(obj, str):
        return pat.sub(PRIVATE_TEXT, obj)
    if isinstance(obj, list):
        return [scrub(x, pat) for x in obj]
    if isinstance(obj, dict):
        return obj.__class__((k, scrub(v, pat)) for k, v in obj.items())
    return obj


def public_candidate(g, withheld=None):
    """Drop what must not leave: living or restricted persons become opaque placeholders (structure kept, identity gone),
    claims about them and their unions' consanguinity are removed, sources keep a title and a hash but no path. `withheld`
    ({person id: [gate ids]}) names records an error gate blocks from the public view: they are made opaque the same way,
    labelled as withheld. A union that touches an opaque person gets an opaque id too (its id spells the partners' keys)."""
    g = copy.deepcopy(g)
    withheld = withheld or {}
    red = [n for n in g['nodes'] if n['cls'] == 'Person' and (n.get('vis') != 'public' or n['id'] in withheld)]
    private_known_as = [{'names': copy.deepcopy(n.get('names') or []), 'aliases': list(n.get('aliases') or [])} for n in red if n.get('vis') != 'public']
    remap = {n['id']: 'person:%s/private-%d' % (n['dataset'], k + 1) for k, n in enumerate(red)}
    for n in g['nodes']:
        if n['id'] in remap:
            old = n['id']
            held = old in withheld and n.get('vis') == 'public'
            n.clear(); n.update(OrderedDict(id=remap[old], cls='Person', dataset=old.split(':', 1)[1].split('/')[0], local=remap[old].split('/', 1)[1],
                                            label=LABEL_WITHHELD if held else LABEL_PRIVATE,
                                            names=[], sex=None, facts={}, generation={}, ids={}, branch=None, notes=[], media=[], achievements=[], restrictions=[] if held else ['PRIVACY'],
                                            grade='Suspected', prov='doc', vis='redacted', living={'value': None, 'rule': 'redacted in the public candidate'}))
            if held:
                n['withheld'] = OrderedDict(gates=sorted(withheld[old]), rule='an error gate names this record; it is kept out of the public view until fixed at the source')
    uremap = {}
    for n in g['nodes']:
        if n['cls'] == 'Union' and any(p in remap for p in n['partners'] + n['children']):
            uremap[n['id']] = 'union:%s/private-u%d' % (n['id'].split(':', 1)[1].split('/')[0], len(uremap) + 1)
    for n in g['nodes']:
        if n['cls'] == 'Union':
            hit = n['id'] in uremap
            if any(p in remap for p in n['partners']):          # a hidden partner: the couple's dates are theirs too
                for k in ('marriage_date', 'end_date', 'marriage_place'):
                    n.pop(k, None)
            n['id'] = uremap.get(n['id'], n['id'])
            n['partners'] = [remap.get(p, p) for p in n['partners']]
            n['children'] = [remap.get(c, c) for c in n['children']]
            n['pedigree'] = OrderedDict((remap.get(k, k), v) for k, v in n.get('pedigree', {}).items())
            if hit:
                n.pop('consanguinity', None)
                for k in ('stated_relationship', 'marriage_date_claims', 'end_date_claims', 'grade_basis'):
                    n.pop(k, None)
                n['label'] = ' × '.join((next(x['label'] for x in g['nodes'] if x['id'] == p)) for p in n['partners']) + (' × ?' if n['partner_unknown'] else '')
        if n['cls'] == 'Person' and n.get('metrics'):
            n['metrics']['one_parent_gaps'] = [remap.get(x, x) for x in n['metrics']['one_parent_gaps']]
    gone = set(remap)
    # metrics computed through a redacted ancestor (inbreeding, pedigree collapse) would tell what the redaction hides
    par = {}
    for u in g['nodes']:
        if u['cls'] == 'Union':
            for ch in u['children']:
                par.setdefault(ch, []).extend(u['partners'])
    opaque = set(remap.values())

    def has_hidden_ancestor(x, seen=None):
        seen = seen or set()
        for q in par.get(x, []):
            if q in opaque or (q not in seen and (seen.add(q) or has_hidden_ancestor(q, seen))):
                return True
        return False
    for n in g['nodes']:
        if n['cls'] == 'Person' and n.get('vis') == 'public' and n.get('metrics') and has_hidden_ancestor(n['id']):
            n['metrics'] = OrderedDict(withheld='an ancestor is redacted in the public candidate', prov='computed')
    g['conflicts'] = [c for c in g.get('conflicts', []) if c.get('person') not in gone and c.get('union') not in uremap]
    g['claims'] = [c for c in g['claims'] if c['subject'] not in gone and not any(r['id'] in gone for r in c.get('refs', []))]
    live = {c['id'] for c in g['claims']}
    for n in g['nodes']:
        if n['cls'] == 'Union':
            n['claims'] = [c for c in n['claims'] if c in live]
    g['edges'] = [dict(e, s=remap.get(e['s'], e['s']), t=uremap.get(e['t'], remap.get(e['t'], e['t'])), claims=[c for c in e.get('claims', []) if c in live]) for e in g['edges']
                  if not (e['p'] == 'alt_parent' and (e['s'] in gone or e['t'] in gone)) and not (e['p'] in ('member_of', 'born_in', 'died_in') and e['s'] in gone)]
    for s in g['sources']:
        s.pop('path', None); s.pop('copies', None)
    names = hidden_names(private_known_as, [n for n in g['nodes'] if n['cls'] == 'Person' and n.get('vis') == 'public'])
    if names:
        pat = re.compile('|'.join(re.escape(x) for x in names))
        for c in g['claims']:
            v2, q2 = scrub(c['value'], pat), scrub(c['quote'], pat)
            if v2 != c['value'] or q2 != c['quote']:
                c['value'], c['quote'], c['text_redacted'] = v2, q2, True       # verbatim is checked on the private build (G04)
        for n in g['nodes']:
            if n['cls'] == 'Person':
                for k in ('notes', 'achievements', 'source_conflicts', 'decisions'):
                    if n.get(k):
                        n[k] = scrub(n[k], pat)
        g['conflicts'] = scrub(g.get('conflicts', []), pat)
    g['build']['kind'] = 'public-candidate'
    g['build']['redacted_persons'] = len(red)
    return g
