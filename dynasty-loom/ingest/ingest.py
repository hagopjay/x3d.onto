#!/usr/bin/env python3
"""Loom genealogy ingest, the first stage: the Cosmos app's family data (JSON trees, family.ts, the two standalone HTML
pages) or a GEDCOM 7 file, to one canonical genealogy graph, with gates and a receipt.

  python3 -I ingest.py --manifest config/sources.json --src <unpacked upload> --out out [--as-of 2026-10-29]

Writes  out/private/          genealogy.graph.json  genealogy.graph.jsonld  genealogy.ged  genealogy.gedcomx.json  cosmos-datasets.json
        out/public-candidate/ the same five, living or restricted persons redacted, no paths (only if no error gate fails)
        out/derived-tables.json, out/gates.json, out/receipt.json
Nothing under --src is executed: JSON goes through json.loads, TS and HTML literals through jsobj (a data-only reader),
GEDCOM through gedcom7.parse. Files named .env* are refused. Run with python3 -I from outside the source tree."""
import argparse
import hashlib
import re
import importlib.metadata
import json
import os
import platform
import sys
import time
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)        # -I drops the script's directory from sys.path; our modules live here, outside any untrusted tree
import build, exports, gates, gdates, gedcom7, identity, loaders, loomview, merge  # noqa: E402

VERSION = '0.2.0'
MODULES = ['ingest.py', 'build.py', 'loaders.py', 'jsobj.py', 'gdates.py', 'kinship.py', 'gedcom7.py', 'exports.py', 'gates.py', 'identity.py', 'merge.py', 'loomview.py',
           'schema/genealogy-graph.schema.json']
LOOM = os.path.dirname(HERE)    # the proto folder: harvest/, facts/, gates/
OUTPUTS = ['genealogy.graph.json', 'genealogy.graph.jsonld', 'genealogy.ged', 'genealogy.gedcomx.json', 'cosmos-datasets.json']


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dumps(obj, compact=False):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':')) if compact else json.dumps(obj, ensure_ascii=False, indent=1) + '\n'


def read_sources(manifest, src_root, skip_families=()):
    loaded = []
    specs = [x for x in manifest['sources'] if x['family'] not in skip_families]
    for rank, spec in enumerate(specs):
        root = HERE if spec.get('base') == 'proto' else (LOOM if spec.get('base') == 'loom' else os.path.realpath(src_root))
        real = os.path.realpath(os.path.join(root, spec['path']))
        if not real.startswith(root + os.sep) or not os.path.isfile(real):
            raise SystemExit('source is not a file under --src: %s' % spec['path'])
        if os.path.basename(real).startswith('.env'):
            raise SystemExit('refusing to read an env file: %s' % spec['path'])
        b = open(real, 'rb').read()
        copies = []
        for cp in spec.get('copies', []):
            cr = os.path.realpath(os.path.join(root, cp))
            cb = open(cr, 'rb').read() if cr.startswith(root + os.sep) and os.path.isfile(cr) else b''
            copies.append(OrderedDict(path=cp, sha256=sha(cb), identical=sha(cb) == sha(b)))
        text = b.decode('utf-8')
        claims, rep = loaders.load(spec, text)
        src = OrderedDict(id='source:%s/%s' % (spec['dataset'], build.slug(spec['path'])), title=os.path.basename(spec['path']), path=spec['path'], sha256=sha(b),
                          bytes=len(b), parser=spec['parser'], dataset=spec['dataset'], family=spec['family'], rank=rank, default_grade=spec['default_grade'],
                          grade_reason=spec.get('grade_reason') or manifest.get('grade_reason', ''), prov=spec.get('prov', 'doc'), overlay=bool(spec.get('overlay')), role=spec.get('role'), consumer_rule=spec.get('consumer_rule'),
                          records=rep['records'], copies=copies)
        for k in ('id_scope', 'diff_version'):
            if spec.get(k):
                src[k] = spec[k]
        loaded.append((src, claims, rep, text))
    return loaded


def build_graph(manifest, loaded, curated, as_of, resolver=None, house_of=None):
    B = build.Builder(manifest, curated, as_of, house_of)
    for src, claims, rep, text in loaded:
        B.add_source(src, claims, resolver)
    nodes, edges, claims = B.build()
    cls = Counter(n['cls'] for n in nodes)
    persons = [n for n in nodes if n['cls'] == 'Person']
    meta = OrderedDict(
        counts=OrderedDict(persons=cls['Person'], unions=cls['Union'], branches=cls['Branch'], places=cls['Place'], edges=len(edges), claims=len(claims), sources=len(loaded)),
        edge_counts=OrderedDict(sorted(Counter(e['p'] for e in edges).items())),
        claim_grades=OrderedDict(sorted(Counter(c['grade'] for c in claims).items())),
        claim_prov=OrderedDict(sorted(Counter(c['prov'] for c in claims).items())),
        node_grades=OrderedDict(sorted(Counter(n['grade'] for n in nodes).items())),
        contested_facts=len(B.issues['conflicts']),
        consanguineous_unions=len(B.issues['consanguinity']),
        persons_with_generation_flags=len(B.issues['generation']),
        living=sum(1 for p in persons if (p.get('living') or {}).get('value') is not False),
        wikidata_resolved=sum(1 for p in persons if (p.get('ids') or {}).get('wikidata')),
        enwiki_sitelinks=sum(1 for p in persons if (p.get('ids') or {}).get('enwiki')))
    g = OrderedDict(schema=OrderedDict(name='loom-genealogy', version='0.1'),
                    build=OrderedDict(kind='private', as_of=as_of, generator='ingest.py %s' % VERSION, policy=manifest['policy']),
                    datasets=manifest['datasets'], sources=[s for s, _, _, _ in loaded], nodes=nodes, edges=edges, claims=claims,
                    conflicts=B.issues['conflicts'], meta=meta)
    return g, B


def core(nodes, edges=()):
    """What a GEDCOM round trip must preserve: persons (names, dates, branch, Wikipedia title), unions (partners in order,
    children), contested alternatives and challenged parent links."""
    by = {n['id']: n for n in nodes}
    P = {}
    for n in nodes:
        if n['cls'] == 'Person':
            f = n.get('facts') or {}
            P[n['id']] = (tuple(x['value'] for x in n['names']), (f.get('birth') or {}).get('date', {}) and f['birth']['date']['gedcom'],
                          (f.get('death') or {}).get('date', {}) and f['death']['date']['gedcom'],
                          tuple(a['date']['gedcom'] for a in (f.get('birth') or {}).get('alternatives', [])),
                          tuple(a['date']['gedcom'] for a in (f.get('death') or {}).get('alternatives', [])),
                          by[n['branch']]['label'] if n.get('branch') else None, (n.get('ids') or {}).get('enwiki'),
                          tuple((x['type'], x['value']) for x in (n.get('ids') or {}).get('other', [])), tuple(n.get('restrictions') or []),
                          (n.get('sex') or {}).get('value'), tuple(by[f['place']]['label'] for f in (n.get('facts') or {}).values() if f.get('place')))
    U = {n['id']: (tuple(n['partners']), tuple(n['children']), n['type'] == 'marriage', tuple(sorted((n.get('pedigree') or {}).items())),
                   (n.get('marriage_date') or {}).get('gedcom'), by[n['marriage_place']]['label'] if n.get('marriage_place') else None)
         for n in nodes if n['cls'] == 'Union'}
    A = sorted((e['s'], e['t']) for e in edges if e['p'] == 'alt_parent')
    return P, U, A


def roundtrip(graph, manifest, curated, as_of):
    text = gedcom7.export(graph)
    claims, rep = gedcom7.import_claims(gedcom7.parse(text), 'roundtrip')
    src = OrderedDict(id='source:roundtrip/genealogy_ged', title='genealogy.ged', sha256=sha(text.encode()), bytes=len(text.encode()), parser='gedcom7', dataset='roundtrip',
                      family='roundtrip', rank=0, default_grade='Suspected', grade_reason='re-import', records=rep['records'])
    B = build.Builder(manifest, curated, as_of)
    B.add_source(src, claims)
    nodes, edges, _ = B.build()
    a, b = core(graph['nodes'], graph['edges']), core(nodes, edges)
    diffs = []
    for name, x, y in (('persons', a[0], b[0]), ('unions', a[1], b[1])):
        for k in sorted(set(x) | set(y)):
            if x.get(k) != y.get(k):
                diffs.append({'what': name, 'id': k, 'before': x.get(k), 'after': y.get(k)})
    if a[2] != b[2]:
        diffs.append({'what': 'alt_parent', 'before': a[2], 'after': b[2]})
    return text, diffs, rep


def schema_errors(obj, schema):
    import jsonschema
    v = jsonschema.Draft202012Validator(schema)
    return [{'path': '/'.join(str(p) for p in e.absolute_path), 'error': e.message[:200]} for e in sorted(v.iter_errors(obj), key=lambda e: list(map(str, e.absolute_path)))][:50]


def derived_tables(g, B):
    nodes = {n['id']: n for n in g['nodes']}
    gen = []
    for n in g['nodes']:
        if n['cls'] == 'Person' and n['generation'].get('descent'):
            d = n['generation']['descent']
            gen.append(OrderedDict(person=n['id'], label=n['label'], stored=n['generation']['stored'], derived=[d['min'], d['max']], method=d['method'], flags=[f['why'] for f in n['generation']['flags']]))
    cons = [OrderedDict(union=u['id'], label=u['label'], relationship=u['consanguinity']['relationship'], phi=u['consanguinity']['phi'],
                        common_ancestors=[(nodes[r['ancestor']]['label'], r['n1'], r['n2'], r['wright_term']) for r in u['consanguinity']['common_ancestors']],
                        children=[nodes[c]['label'] for c in u['children']])
            for u in g['nodes'] if u['cls'] == 'Union' and (u.get('consanguinity') or {}).get('related')]
    ped = [OrderedDict(person=n['id'], label=n['label'], F=n['metrics']['inbreeding_F'], F_lower_bound=n['metrics']['F_is_lower_bound'], implex=n['metrics']['pedigree']['implex'],
                       distinct_ancestors=n['metrics']['pedigree']['distinct_ancestors'], filled_slots=n['metrics']['pedigree']['filled_slots'])
           for n in g['nodes'] if n['cls'] == 'Person' and n.get('metrics') and (n['metrics']['inbreeding_F'] != '0' or n['metrics']['pedigree']['implex'] != '0')]
    return OrderedDict(generation=gen, consanguinity=cons, pedigree_collapse=ped, conflicts=B.issues['conflicts'], omissions=B.issues['omissions'],
                       name_variants=B.issues['name-variants'])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--as-of', default=None)
    ap.add_argument('--without-decisions', action='store_true', help='leave out sources of family analyst-decisions (reproduces the blocked first build)')
    a = ap.parse_args()
    t0 = time.time()
    mpath = os.path.abspath(a.manifest)
    manifest = json.load(open(mpath, encoding='utf-8'))
    as_of = a.as_of or manifest['as_of']
    curated = {}
    for c in manifest.get('curated', []):
        curated.update({k: v for k, v in json.load(open(os.path.join(HERE, c), encoding='utf-8')).items() if not k.startswith('_')})
    schema = json.load(open(os.path.join(HERE, 'schema', 'genealogy-graph.schema.json'), encoding='utf-8'))
    MC = manifest.get('merge')                       # the merge stage (config/merge.json): identity, houses, cross-checks, datagates, loom view
    houses = house_of = None
    extra_inputs = OrderedDict()
    if MC:
        hpath = os.path.join(HERE, MC['houses'])
        houses = json.load(open(hpath, encoding='utf-8'))
        hmap = {}
        for ds, fc in houses['families'].items():
            for h in fc['houses']:
                for lab in h['labels']:
                    hmap[(ds, lab)] = h['key']
                    curated.setdefault(lab, {'label': h['seat'], 'lat': h['lat'], 'lon': h['lon'], 'wikidata': None, 'geonames': None,
                                             'grade': houses['grade']['coordinates'], 'ids_grade': 'Suspected', 'prov': houses['grade']['prov']})
        house_of = lambda ds, lab: hmap.get((ds, lab))   # noqa: E731
        for k, rel in list(MC['crosschecks'].items()) + [('datagates', MC['datagates'])]:
            fp = os.path.join(LOOM, rel)
            extra_inputs[rel] = OrderedDict(sha256=sha(open(fp, 'rb').read()), role='cross-check' if k != 'datagates' else 'gate module')

    loaded = read_sources(manifest, a.src, ('analyst-decisions',) if a.without_decisions else ())
    texts = {s['id']: t for s, _, _, t in loaded}
    resolver = identity.Resolver(loaded, manifest['policy']) if MC else None
    graph, B = build_graph(manifest, loaded, curated, as_of, resolver, house_of)
    graph2, _ = build_graph(manifest, loaded, curated, as_of, resolver, house_of)
    det = sha(dumps(graph).encode()) == sha(dumps(graph2).encode())
    ged_text, rt_diffs, rt_rep = roundtrip(graph, manifest, curated, as_of)
    P = manifest['policy']
    temporal = gates.temporal(graph, P)
    verb, nclaims = gates.verbatim(graph, texts)
    persons = [n for n in graph['nodes'] if n['cls'] == 'Person']
    ident = []
    for n in persons:
        for ev, f in n['facts'].items():
            y = gdates.year_bounds(f['date'])[0] if f.get('date') else None
            for alt in f.get('alternatives', []):
                y2 = gdates.year_bounds(alt['date'])[0]
                if y is not None and y2 is not None and abs(y - y2) > P['identity_conflict_years']:
                    ident.append({'person': n['id'], 'fact': ev, 'accepted': f['date']['gedcom'], 'by': f['sources'], 'alternative': alt['date']['gedcom'], 'alt_by': alt['sources']})
    G = [
        gates.gate('G01', 'sources pinned; declared copies byte-identical', 'error', [{'source': s['id'], 'copy': c['path']} for s, *_ in loaded for c in s['copies'] if not c['identical']],
                   note='%d files, %d declared copies' % (len(loaded), sum(len(s['copies']) for s, *_ in loaded))),
        gates.gate('G02', 'JSON parsed twice (json, located reader) agrees', 'error', [{'source': s['id']} for s, _, r, _ in loaded if r.get('parse_agreement') is False]),
        gates.gate('G03', 'loader notes (ids, unknown fields, URLs)', 'warn', [{'source': s['id'], 'note': x} for s, _, r, _ in loaded for x in r['notes']]),
        gates.gate('G04', 'every claim quote found verbatim in its source file', 'error', verb, note='%d claims checked' % nclaims),
        None,                                                                                  # G05 runs once the public candidate exists
        gates.gate('G06', 'parent links form no cycle', 'error', B.issues['cycle'], tool='kinship.topo_order'),
        gates.gate('G07', 'references resolve (per source, then after the merge)', 'warn', B.issues['dangling']),
        gates.gate('G08', 'spouse field stated from both sides', 'warn', B.issues['spouse-asymmetry']),
        gates.gate('G09', 'temporal impossibilities (death before birth, parent under min age, birth after a parent died)', 'error', [t for t in temporal if t['severity'] == 'error']),
        gates.gate('G10', 'temporal oddities (young or old parent, long life)', 'warn', [t for t in temporal if t['severity'] == 'warn']),
        gates.gate('G11', 'stored generation within the range topology allows', 'warn', B.issues['generation']),
        gates.gate('G12', 'children of one union share a stored generation', 'warn', B.issues['generation-siblings']),
        gates.gate('G13', 'contested facts (sources disagree; all values kept, first by precedence accepted)', 'warn', B.issues['conflicts']),
        gates.gate('G14', 'possible conflation (one id, dates more than %d years apart)' % P['identity_conflict_years'], 'warn', ident),
        gates.gate('G15', 'name variants (aliases, not conflicts)', 'info', B.issues['name-variants']),
        gates.gate('G16', 'omissions (a source leaves parents empty where another names them)', 'info', B.issues['omissions']),
        gates.gate('G17', 'consanguineous unions (kinship > 0)', 'info', B.issues['consanguinity'], tool='kinship.py (exact fractions)'),
        gates.gate('G18', 'renderer parity: each consumer\'s spouse-edge rule replayed on its data', 'warn', gates.renderer_parity(B, [s for s, *_ in loaded])),
        gates.gate('G19', 'placeholder media (stock photos standing in for portraits)', 'info',
                   [{'person': n['id'], 'url': m['url']} for n in persons for m in n['media'] if m['kind'] == 'placeholder']),
        gates.gate('G20', 'dates before 1582 without a calendar', 'info', gates.calendars(graph)),
        gates.gate('G21', 'GEDCOM 7 export, re-parse, re-import, rebuild: core unchanged', 'error', rt_diffs, tool='gedcom7.py', note='%d records exported' % rt_rep['records']),
        gates.gate('G22', 'two builds from the same inputs are byte-identical', 'error', [] if det else [{'problem': 'graph bytes differ between two builds'}]),
        None,                                                                                  # G23 runs on the public candidate
        gates.gate('G24', 'GEDCOM FAMC/FAMS agree with FAM HUSB/WIFE/CHIL', 'warn', B.issues['gedcom-links']),
        gates.gate('G25', 'Wikidata QIDs resolved', 'info', [{'person': n['id'], 'enwiki': n['ids']['enwiki']} for n in persons if n['ids'].get('enwiki') and not n['ids'].get('wikidata')],
                   note='resolver (resolve_wikidata.py) not run: wikidata.org refused by the egress proxy (HTTP 403 on CONNECT) on 2026-10-29; sitelinks kept as the resolution key'),
    ]
    withheld, unattributed, view, view_extra, merge_info = OrderedDict(), [], None, None, OrderedDict()
    if MC:
        Gv = loomview.Graph(graph, houses)
        idsum = resolver.summary()
        G.append(gates.gate('G26', 'harvest children[] read in reverse: each listed child has the person among its accepted parents', 'warn', B.issues['children-asymmetry'],
                            note='%d listed children have no record anywhere (open world, not a fault)' % len(B.issues['children-unresolved'])))
        G.append(gates.gate('G27', 'identity: refused matches, two identifiers for one person, keys held by two persons', 'warn',
                            [dict(x, kind='refused') for x in idsum['refused']] + [dict(x, kind='id-conflict') for x in idsum['id_conflicts']] + [dict(x, kind='bridge') for x in idsum['bridges']],
                            tool='identity.py', note='%d records -> %d persons; methods %s; %d provisional x: ids' % (idsum['records'], idsum['persons'], dict(idsum['methods']), idsum['provisional_x_ids'])))
        cons = json.load(open(os.path.join(LOOM, MC['crosschecks']['consanguinity']), encoding='utf-8'))
        crows, documented, cfind = merge.crosscheck_consanguinity(cons, loaded, resolver, graph)
        G.append(gates.gate('G28', 'facts/consanguinity.json against kinship.py (fact-check links exactly; merged graph may only add kinship)', 'warn', cfind, tool='kinship.py',
                            note='%d rows, %d agree exactly on the fact-check links' % (len(crows), sum(1 for r in crows if r['agree']))))
        role_ok, role_bad = merge.check_roles(graph, Gv)
        G.append(gates.gate('G29', 'parent roles (fact-check order father-first, harvest father/mother) against stated sex', 'warn', role_bad,
                            note='%d role statements agree with a stated sex' % role_ok))
        sdiff = json.load(open(os.path.join(LOOM, MC['crosschecks']['source_diff']), encoding='utf-8'))
        dsum, dfind = merge.crosscheck_source_diff(sdiff, loaded, resolver, graph, B.issues)
        G.append(gates.gate('G30', 'facts/source_diff.json against the loaders and against G13/G15/G16', 'warn', dfind, note=json.dumps(dsum, ensure_ascii=False)))
        dg = merge.load_module(os.path.join(LOOM, MC['datagates']), 'datagates')
        founders = OrderedDict((ds, merge.founders_of(houses, resolver, ds)) for ds in houses['families'])
        asof_y = int(as_of[:4])
        everyone = OrderedDict((ds, {n['id'] for n in persons if n['dataset'] == ds}) for ds in houses['families'])
        dfind_all = merge.run_datagates(dg, Gv, houses, everyone, founders, asof_y)
        G += merge.datagate_entries(dfind_all, gates.gate)
        hidden = {n['id'] for n in persons if n.get('vis') != 'public'}
        withheld, unattributed = merge.blocked_records(Gv, [x for x in G if x], dfind_all)
        # the view: public persons minus the records an error names; re-gated until no error is left (a removal can expose another)
        rounds = []
        for _ in range(5):
            members = OrderedDict((ds, {p for p in everyone[ds] if p not in hidden and p not in withheld}) for ds in everyone)
            vf = merge.run_datagates(dg, Gv, houses, members, founders, asof_y)
            errs = [f for f in vf if f['severity'] == 'error']
            rounds.append(OrderedDict(people=sum(len(v) for v in members.values()), errors=len(errs), warnings=sum(1 for f in vf if f['severity'] == 'warn')))
            if not errs:
                break
            for f in errs:
                if f.get('person'):
                    withheld.setdefault(f['person'], []).append(f['gate'] + ' (view)')
        G.append(gates.gate('G31', 'datagates on the published view itself (after withholding): no error left', 'error', [f for f in vf if f['severity'] == 'error'],
                            tool='proto/gates/datagates.py', note='rounds: %s' % json.dumps(rounds)))
        full = OrderedDict()
        for ds in everyone:
            ppl, _, _ = loomview.compute(Gv, ds, houses['families'][ds], everyone[ds], founders[ds])
            full[ds] = ppl
        def presumed_living(n):
            y = loomview.year_of(n['facts'].get('birth'))
            return bool(n.get('living_flag')) or (y is not None and y > asof_y - P['living_years'] and not n['facts'].get('death'))
        living_houses = OrderedDict((ds, {r['house'] for pid, r in full[ds].items() if pid in hidden and r['core'] and r['house'] and presumed_living(Gv.nodes[pid])})
                                    for ds in everyone)
        merge_info = OrderedDict(identity=idsum, consanguinity=crows, documented_kinship=documented, source_diff=dsum, rounds=rounds,
                                 members=OrderedDict((ds, sorted(v)) for ds, v in members.items()), founders=founders,
                                 living_houses=OrderedDict((ds, sorted(v)) for ds, v in living_houses.items()), view_warnings=[f for f in vf if f['severity'] != 'error'])
    public = exports.public_candidate(graph, withheld)
    G[4] = gates.gate('G05', 'graph validates against schema/genealogy-graph.schema.json (private and public)', 'error',
                      [dict(e, build='private') for e in schema_errors(graph, schema)] + [dict(e, build='public') for e in schema_errors(public, schema)],
                      tool='jsonschema %s, Draft 2020-12' % importlib.metadata.version('jsonschema'))
    priv_findings = gates.privacy(public)
    if MC:                                                    # nothing a hidden person is known by may appear in the public text
        ptext = dumps(public)
        hn = set(exports.hidden_names([n for n in persons if n.get('vis') != 'public'], [n for n in persons if n.get('vis') == 'public']))
        for n in persons:
            if n.get('vis') != 'public':
                for token in [n['id'], '"%s"' % n['local']] + [x for x in [y['value'] for y in n['names']] + list(n.get('aliases') or []) if x in hn]:
                    if token in ptext:
                        priv_findings.append({'person': n['id'], 'problem': 'a hidden identity appears in the public text'}); break
    G[22] = gates.gate('G23', 'public candidate: no living or restricted identity, no paths', 'error', priv_findings)
    G = [x for x in G if x]
    blocked = [x['id'] for x in G if x['severity'] == 'error' and x['status'] == 'fail' and (not MC or x['id'] in unattributed or x['id'] in ('G05', 'G22', 'G23', 'G31'))]

    out = os.path.abspath(a.out)
    files = OrderedDict()

    def write(rel, data):
        p = os.path.join(out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        b = data.encode('utf-8')
        open(p, 'wb').write(b)
        files[rel] = OrderedDict(sha256=sha(b), bytes=len(b))

    def views(prefix, g):
        made = [('genealogy.graph.json', dumps(g)), ('genealogy.graph.jsonld', dumps(exports.jsonld(g))), ('genealogy.ged', gedcom7.export(g)),
                ('genealogy.gedcomx.json', dumps(exports.gedcomx(g))), ('cosmos-datasets.json', dumps(exports.cosmos_compat(g, manifest['datasets'])))]
        for name, text in made:                     # all five made in memory first: a crash leaves no half-written view
            write(prefix + name, text)
    views('private/', graph)
    if not blocked:
        public['meta']['public'] = OrderedDict(redacted=public['build']['redacted_persons'], withheld=len([w for w in withheld if w in {n['id'] for n in persons if n.get('vis') == 'public'}]),
                                               rule='living or RESN CONFIDENTIAL/PRIVACY persons, and records an error gate names, replaced by opaque placeholders; claims about them dropped; no paths')
        views('public-candidate/', public)
    else:
        for f in OUTPUTS:
            p = os.path.join(out, 'public-candidate', f)
            if os.path.exists(p):
                os.remove(p)
    view_summary = None
    if MC and not blocked:
        public_ids = {n['id'] for n in persons if n.get('vis') == 'public'}
        errors = sum(x['count'] for x in G if x['severity'] == 'error')
        warns = sum(x['count'] for x in G if x['severity'] == 'warn')
        built = OrderedDict(by='proto/ingest/ingest.py %s (loomview.py)' % VERSION, run_by='merge stage, report 08',
                            inputs=OrderedDict([(s['path'], s['sha256']) for s, *_ in loaded] + [(k, v['sha256']) for k, v in extra_inputs.items()] +
                                               [('ingest/' + MC['houses'], sha(open(os.path.join(HERE, MC['houses']), 'rb').read()))]),
                            gates=OrderedDict(errors=sum(1 for f in merge_info['view_warnings'] if f['severity'] == 'error'), warnings=sum(1 for f in merge_info['view_warnings'] if f['severity'] == 'warn'),
                                              scope='datagates re-run on this view (G31); the whole ledger: %d error and %d warning findings, every error-named record withheld (below)' % (errors, warns)),
                            withheld=[OrderedDict(id=Gv.vid(p), name=Gv.nodes[p]['label'], dataset=Gv.nodes[p]['dataset'], gates=sorted(set(g))) for p, g in withheld.items() if p in public_ids],
                            rules=OrderedDict(
                                privacy='left out: living_possible flag without a recorded death, or no death and the latest possible birth within %d years of %s; unions touching them are left out' % (P['living_years'], as_of),
                                withheld='left out: every record an error finding names (pipeline gates G04/G06/G09/G21/G23, datagates D00-D15 through the FamilyMember adapter), then datagates re-run on the view until no error is left',
                                house='core member: own house label (curated/houses.json maps the source labels; precedence picks the first label that names a house), except that a core wife of a core husband takes his house (as an adult she belonged to it); in-law: house of the spouse at marriage (earliest dated union with a core partner), else own label; anyone else in a union: a partner\'s house; anyone else: a parent\'s house (father first)',
                                core='a source flag (any partition saying core) where one exists, else descent from a dye founder',
                                family='the source family field (in-law:X gives X; unverified gives null), else the father\'s, else a dye-carrying mother\'s',
                                shares='exact expected fraction of descent from each dye\'s founders over the people in this view: founder 1, child = mean of parents, an unknown or left-out parent counts 0 (a lower bound)',
                                generation='[min, max] parent-to-child steps from any dye founder over all descent paths; others aligned to a partner, else one above their children, else one below their parents; null when unplaced',
                                phi='kinship.py (Karigl recursion, exact) over the parents in this view; close = phi > 0; relationship from kinship.explain, avuncular named as in the contract',
                                confidence='Confirmed only when two independent source families (fact-check, harvest), each at least Likely, agree on birth, death and parents and none contradicts; otherwise the best single-source grade (at most Likely); parents contested between such families give Suspected',
                                father_mother='a parent\'s stated sex decides; else the role a source gives (harvest father/mother; fact-check order, father first, checked by G29); else a gendered title in the name or a note saying son or daughter of; otherwise the parent is not placed (null), never guessed, and every derived value is computed over the published links only',
                                years='the accepted date\'s first year; precision is the source\'s (day, month, year, circa, uncertain); compatible dates from different sources agree, the most precise stands',
                                events='only harvest events with one cited secondary source (grade L) that name no one the view leaves out'))
        hn = exports.hidden_names([n for n in persons if n.get('vis') != 'public'], [n for n in persons if n.get('vis') == 'public'])
        view, view_extra = merge.build_view(Gv, houses, manifest, merge_info['members'], merge_info['founders'], merge_info['living_houses'], built,
                                            re.compile('|'.join(re.escape(x) for x in hn)) if hn else None)
        vbad = merge.check_view(view, asof_y, P['living_years'])
        G.append(gates.gate('G32', 'loom-view.json against the loom-view/1 contract (keys, types, references, privacy rule)', 'error', vbad, tool='merge.check_view'))
        if vbad:
            blocked.append('G32')
        else:
            write(MC['view'], json.dumps(view, ensure_ascii=False, indent=1) + '\n')
        merge_info['view_aux'] = OrderedDict((ds, x['aux']) for ds, x in view_extra.items())
        view_summary = OrderedDict((f['key'], OrderedDict(people=len(f['people']), core=sum(1 for p in f['people'] if p['core']), unions=len(f['unions']),
                                                          close=sum(1 for u in f['unions'] if u['close']), houses=len(f['houses']), events=len(f['events']),
                                                          confidence=OrderedDict(sorted(Counter(p['confidence'] for p in f['people']).items()))))
                                   for f in view['families'])
    if MC:
        write('private/derived-tables.json', dumps(derived_tables(graph, B)))
        write('private/gates.json', dumps(G))
        write('private/merge-ledger.json', dumps(merge_info))
        hidden_list = [(n['id'], n['local'], [x['value'] for x in n['names']] + list(n.get('aliases') or [])) for n in persons if n.get('vis') != 'public']
        write('gates.json', merge.redact_text(dumps(G), hidden_list))
    else:
        write('derived-tables.json', dumps(derived_tables(graph, B)))
        write('gates.json', dumps(G))
    rec = OrderedDict(
        generator='ingest.py', version=VERSION, as_of=as_of, run_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        python=platform.python_version(), platform=platform.platform(), jsonschema=importlib.metadata.version('jsonschema'),
        manifest=OrderedDict(path=os.path.relpath(mpath, HERE), sha256=sha(open(mpath, 'rb').read())),
        scripts=OrderedDict((m, sha(open(os.path.join(HERE, m), 'rb').read())) for m in MODULES + manifest.get('curated', []) + ([MC['houses']] if MC else [])),
        inputs=[OrderedDict(path=s['path'], sha256=s['sha256'], bytes=s['bytes'], parser=s['parser'], records=s['records'],
                            copies=[OrderedDict(path=c['path'], identical=c['identical']) for c in s['copies']]) for s, *_ in loaded] +
               [OrderedDict(path=k, sha256=v['sha256'], role=v['role']) for k, v in extra_inputs.items()],
        outputs=files, counts=graph['meta'],
        gates=[OrderedDict((k, x[k]) for k in ('id', 'name', 'severity', 'status', 'count', 'tool')) for x in G],
        verdict=('public candidate written' if not blocked else 'public candidate blocked by ' + ', '.join(blocked)) +
                ('; %d records withheld by error gates' % len(withheld) if MC else ''),
        built_in_s=round(time.time() - t0, 3))
    if view_summary:
        rec['view'] = view_summary
    open(os.path.join(out, 'receipt.json'), 'w', encoding='utf-8').write(dumps(rec))
    summary = OrderedDict((k, rec[k]) for k in ('verdict', 'counts', 'built_in_s'))
    if view_summary:
        summary['view'] = view_summary
    summary['gates'] = ['%s %s %s (%d)' % (x['id'], x['status'], x['name'], x['count']) for x in G]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if blocked else 0


if __name__ == '__main__':
    sys.exit(main())
