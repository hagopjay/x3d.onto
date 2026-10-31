"""Merge-stage checks and the loom view, called by ingest.py when the manifest has a `merge` block (config/merge.json).

  crosscheck_consanguinity  facts/consanguinity.json against kinship.py: once on the fact-check file's own parent links (the two
                            tools must agree exactly) and once on the merged graph (the harvest may add ancestry: phi can only
                            grow; a smaller phi means a parent link was lost in the merge)
  crosscheck_source_diff    facts/source_diff.json (the fact-check analyst's diff of the app files) against the loaders' claims,
                            and against the gates that should report each difference (G13 contested, G15 name variants, G16 omissions)
  check_roles               the fact-check files' parent order (father first) against every parent whose sex a source states
  run_datagates             proto/gates/datagates.py through the FamilyMember adapter (loomview.family_members)
  blocked_records           which person records the error findings name: they are kept out of the public view
  build_view                loom-view/1"""
import importlib.util
import json
import re
from collections import Counter, OrderedDict, defaultdict
from fractions import Fraction

import gates
import kinship
import loomview


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fsrc(loaded, dataset, family):
    return next((s for s, *_ in loaded if s['dataset'] == dataset and s['family'] == family), None)


# ---------------- consanguinity.json ----------------
def crosscheck_consanguinity(cons, loaded, resolver, graph):
    nodes = {n['id']: n for n in graph['nodes']}
    unions = {}
    for u in graph['nodes']:
        if u['cls'] == 'Union' and len(u['partners']) == 2:
            unions[frozenset(u['partners'])] = u
    rows, findings = [], []
    for ds, block in cons.items():
        src = _fsrc(loaded, ds, 'fact-check')
        if not src:
            findings.append({'dataset': ds, 'problem': 'no fact-check source for this dataset'}); continue
        members = json.loads(next(t for s, _, _, t in loaded if s['id'] == src['id']))['members']
        par = {m['id']: [p for p in m.get('parents') or []] for m in members}
        kin = kinship.Kinship(sorted(par), par)
        for r in block.get('computed_cousin_or_kin_marriages', []):
            mine = kin.phi(r['a'], r['b'])
            a, b = resolver.canon(src['id'], r['a']), resolver.canon(src['id'], r['b'])
            u = unions.get(frozenset((a, b)))
            merged = Fraction((u.get('consanguinity') or {}).get('phi', '0')) if u else None
            row = OrderedDict(dataset=ds, a=r['a'], b=r['b'], names=[r['a_name'], r['b_name']], factcheck_F=r['offspring_inbreeding_F'], kinship_py_on_factcheck=str(mine),
                              agree=abs(float(mine) - r['offspring_inbreeding_F']) <= 5.000001e-6, union=u['id'] if u else None, merged_phi=str(merged) if merged is not None else None,
                              merged_relationship=(u.get('consanguinity') or {}).get('relationship') if u else None)
            if merged is None:
                row['merged_vs_factcheck'] = 'union missing in the merge'
            else:
                row['merged_vs_factcheck'] = 'equal' if merged == mine else ('higher: the merge adds ancestry' if merged > mine else 'LOWER: a parent link was lost')
            rows.append(row)
            if not row['agree']:
                findings.append({'dataset': ds, 'couple': [r['a'], r['b']], 'problem': 'kinship.py gives %s on the fact-check links, consanguinity.json says %s' % (mine, r['offspring_inbreeding_F'])})
            if merged is None or merged < mine:
                findings.append({'dataset': ds, 'couple': [r['a'], r['b']], 'problem': row['merged_vs_factcheck']})
        for key, pc in (block.get('pedigree_collapse') or {}).items():
            mine = kin.inbreeding(key) if key in kin.idx else None
            pid = resolver.canon(src['id'], key)
            mf = (nodes.get(pid, {}).get('metrics') or {}).get('inbreeding_F')
            rows.append(OrderedDict(dataset=ds, person=key, name=pc.get('name'), factcheck_F=pc.get('F_computed'), kinship_py_on_factcheck=str(mine),
                                    agree=mine is not None and abs(float(mine) - pc.get('F_computed', 0)) <= 5.000001e-6, merged_F=mf))
            if mine is None or abs(float(mine) - pc.get('F_computed', 0)) > 5.000001e-6:
                findings.append({'dataset': ds, 'person': key, 'problem': 'pedigree-collapse F differs: kinship.py %s, consanguinity.json %s' % (mine, pc.get('F_computed'))})
    documented = [dict(r, dataset=ds) for ds, block in cons.items() for r in block.get('documented_outside_dataset', [])]
    return rows, documented, findings


# ---------------- source_diff.json ----------------
def _ours(claims, field):
    """The value one app file gives for one field, spelled the way diff_sources.py spells it."""
    pred = {'name': 'name', 'born': 'birth', 'died': 'death', 'parents': 'parents', 'branch': 'branch', 'spouse': 'spouse', 'generation': 'generation.stored',
            'note': 'note', 'wikipedia': 'sitelink', 'imageUrl': 'media'}.get(field)
    cs = [c for c in claims if c['predicate'] == pred]
    if not cs:
        return None
    v = cs[0]['value']
    if field in ('born', 'died'):
        return v['start']['y']
    if field in ('wikipedia', 'imageUrl'):
        return v['url']
    return v


def crosscheck_source_diff(diff, loaded, resolver, graph, issues):
    by_version = {}
    for s, claims, _, _ in loaded:
        if s.get('diff_version'):
            by_version[s['diff_version']] = (s, claims)
    rows, findings = Counter(), []
    expect = Counter()
    conflicts = defaultdict(set)
    for c in issues['conflicts']:
        if c.get('person'):
            conflicts[c['person']].add(c['fact'])
    variants = {v['person'] for v in issues['name-variants']}
    omissions = {o['person'] for o in issues['omissions']}
    for p in diff.get('people', []):
        for field, vals in p.get('differing_fields', {}).items():
            seen = {}
            for label, js in vals.items():
                ver = label.split(' ')[0]
                if ver not in by_version:
                    rows['version not loaded'] += 1; continue
                s, claims = by_version[ver]
                mine = [c for c in claims if c['kind'] == 'person' and c['subject'] == p['id']]
                ours = _ours(mine, field)
                theirs = json.loads(js)
                seen[ver] = theirs
                if ours == theirs or (ours is None and theirs is None):
                    rows['value agrees'] += 1
                else:
                    rows['value differs'] += 1
                    findings.append({'person': p['id'], 'field': field, 'version': ver, 'source_diff': theirs, 'loader': ours})
            pid = None
            for ver in seen:
                s, _ = by_version[ver]
                try:
                    pid = resolver.canon(s['id'], p['id']); break
                except KeyError:
                    continue
            if pid is None:
                continue
            nonnull = [v for v in seen.values() if v not in (None, [], '')]
            if field in ('born', 'died') and len(set(nonnull)) > 1:
                expect['G13 %s' % field] += 1
                if {'born': 'birth', 'died': 'death'}[field] not in conflicts[pid]:
                    findings.append({'person': p['id'], 'field': field, 'problem': 'versions disagree but G13 has no contested %s' % field})
            elif field == 'name' and len(set(nonnull)) > 1:
                expect['G15 name'] += 1
                if pid not in variants:
                    findings.append({'person': p['id'], 'field': field, 'problem': 'names differ but G15 lists no variant'})
            elif field == 'parents' and len(nonnull) < len(seen) and nonnull:
                expect['G16 parents'] += 1
                if pid not in omissions and 'parents' not in conflicts[pid]:
                    findings.append({'person': p['id'], 'field': field, 'problem': 'a version leaves parents empty but G16 has no omission'})
            elif field == 'parents' and len({tuple(sorted(v)) for v in nonnull}) > 1:
                sets = [set(v) for v in nonnull]
                nested = all(a <= b or b <= a for a in sets for b in sets)
                expect['G13 parents' if not nested else 'nested parents (agree)'] += 1
                if not nested and 'parents' not in conflicts[pid]:
                    findings.append({'person': p['id'], 'field': field, 'problem': 'parent sets disagree but G13 has no contested parents'})
    return OrderedDict(values=dict(rows), expected_gate_hits=dict(expect)), findings


# ---------------- parent roles ----------------
def check_roles(graph, G):
    nodes = G.nodes
    ok, bad = 0, []
    for c in graph['claims']:
        if c['predicate'] == 'parents' and c.get('roles') and c.get('refs'):
            for r, role in zip(c['refs'], c['roles']):
                n = nodes.get(r['id'])
                sx = ((n or {}).get('sex') or {}).get('value')
                if sx in ('M', 'F'):
                    if (sx == 'M') == (role == 'father'):
                        ok += 1
                    else:
                        bad.append({'claim': c['id'], 'source': c['source'], 'child': c['subject'], 'parent': r['id'], 'role': role, 'stated_sex': sx})
    return ok, bad + [dict(x, problem='two claims give this parent link different roles') for x in G.role_clash]


# ---------------- datagates ----------------
def run_datagates(dg, G, cfg, members_by_ds, founders, asof_year):
    """members_by_ds: {dataset: set of canonical ids}. Returns findings with the dataset and the canonical subject added."""
    out = []
    for ds, M in members_by_ds.items():
        people, unions, _ = loomview.compute(G, ds, cfg['families'][ds], M, founders[ds])
        back = {r['id']: pid for pid, r in people.items()}
        fs = dg.check(loomview.family_members(people, unions), {'asof': asof_year})
        for f in fs:
            f['dataset'] = ds
            f['person'] = back.get(f['subject'])
            f['refs_persons'] = [back.get(x) for x in f['refs']]
        out += fs
    return out


def blocked_records(G, gate_list, dfindings):
    """{person id: [gate ids]} for every error finding that names a person; a list of gate ids whose errors name no record
    (those still block the whole public candidate)."""
    by, unattributed = defaultdict(set), []
    claims = {c['id']: c for c in G.g['claims']}
    for gt in gate_list:
        if gt['severity'] != 'error' or gt['status'] != 'fail':
            continue
        hit = False
        for f in gt['findings']:
            ps = []
            if isinstance(f, dict) and f.get('severity') not in (None, 'error'):
                continue                                        # a gate that mixes severities: only its error findings block
            if isinstance(f, dict):
                if f.get('child'):
                    ps = [f['child']]
                elif f.get('person'):
                    ps = [f['person']]
                elif f.get('claim') and f['claim'] in claims and claims[f['claim']]['kind'] == 'person':
                    ps = [claims[f['claim']]['subject']]
                elif f.get('what') == 'persons':
                    ps = [f['id']]
                elif f.get('what') == 'unions':
                    u = G.nodes.get(f['id'])
                    ps = list(u['partners']) if u else []
            elif isinstance(f, str):
                ps = re.findall(r'person:[^\s,]+', f)
            for p in ps:
                if p in G.nodes:
                    by[p].add(gt['id']); hit = True
        if not hit:
            unattributed.append(gt['id'])
    for f in dfindings:
        if f['severity'] != 'error':
            continue
        ps = [f['person']] if f.get('person') else []
        if f['gate'] == 'D02-cycle':
            ps += [x for x in f['refs_persons'] if x]
        for p in ps:
            by[p].add(f['gate'])
    return OrderedDict((k, sorted(v)) for k, v in sorted(by.items())), unattributed


def datagate_entries(dfindings, gate_fn, cap=None):
    """One gates.json entry per datagates code; each finding keeps its own severity."""
    order = sorted({f['gate'] for f in dfindings})
    out = []
    for code in order:
        fs = [f for f in dfindings if f['gate'] == code]
        sev = 'error' if any(f['severity'] == 'error' for f in fs) else ('warn' if any(f['severity'] == 'warn' for f in fs) else 'info')
        slim = [OrderedDict((k, f[k]) for k in ('severity', 'dataset', 'person', 'subject', 'refs', 'message', 'detail') if k in f) for f in fs]
        g = gate_fn(code, 'datagates %s (via the FamilyMember adapter)' % code, sev, slim, tool='proto/gates/datagates.py', note=', '.join('%s %d' % kv for kv in sorted(Counter(f['severity'] for f in fs).items())))
        out.append(g)
    return out


# ---------------- the view ----------------
def founders_of(cfg, resolver, ds):
    """Dye founders by QID or by a record's local id, resolved to canonical person ids."""
    out = OrderedDict()
    for dye, d in cfg['families'][ds]['dyes'].items():
        ids = []
        for key in d['founders']:
            ci = resolver.idx[(ds, 'qid')].get(key)
            if ci is None:
                ci = next((r['cluster'] for r in resolver.records.values() if r['dataset'] == ds and r['local'] == key), None)
            if ci is None:
                raise SystemExit('dye founder %r of %s not found' % (key, ds))
            ids.append(resolver.clusters[ci]['id'])
        out[dye] = ids
    return out


def events_for(graph, ds, view_ids):
    out = []
    for c in graph['claims']:
        if c['predicate'] != 'event' or c['subject'] != 'source:%s/events' % ds:
            continue
        ev = c['value']
        refs = [r['id'] for r in c.get('refs', [])]
        if any(r.startswith('person:') and '/unresolved~' not in r and r not in view_ids for r in refs):
            continue                                            # names someone the view leaves out
        m = re.match(r'(\d{3,4})', str(ev.get('date') or ''))
        if not m or not ev.get('source'):
            continue
        out.append(OrderedDict(year=int(m.group(1)), label=ev['label'], grade='L', source=ev['source']))
    return sorted(out, key=lambda e: (e['year'], e['label']))


def build_view(G, cfg, manifest, members_by_ds, founders, living_houses, built, scrub_pat=None):
    fams, extra = [], OrderedDict()
    for ds, fc in cfg['families'].items():
        people, unions, aux = loomview.compute(G, ds, fc, members_by_ds[ds], founders[ds])
        if scrub_pat is not None:
            for r in people.values():
                if r['note']:
                    r['note'] = scrub_pat.sub('[private person]', r['note'])
        vid = {pid: r['id'] for pid, r in people.items()}
        fam = OrderedDict(key=ds, name=fc['name'],
                          dyes=OrderedDict((dye, OrderedDict(founders=[vid[f] for f in founders[ds][dye] if f in vid], color=d['color'])) for dye, d in fc['dyes'].items()),
                          houses=loomview.houses_view(fc, people, living_houses.get(ds, set())),
                          people=list(people.values()),
                          unions=[OrderedDict((k, v) for k, v in u.items() if not k.startswith('_')) for u in unions],
                          events=[dict(e, label=scrub_pat.sub('[private person]', e['label'])) if scrub_pat is not None else e for e in events_for(G.g, ds, set(people))])
        fams.append(fam)
        extra[ds] = OrderedDict(aux=aux, unions=unions, people=people)
    view = OrderedDict(version='loom-view/1', asof=int(manifest['as_of'][:4]), built=built, families=fams)
    return view, extra


def redact_text(text, hidden):
    """Replace every identity of a hidden person (canonical id, key, names) in a JSON text by an opaque token."""
    for k, (pid, key, names) in enumerate(hidden):
        tok = 'private-%d' % (k + 1)
        text = text.replace(pid, pid.split('/')[0] + '/' + tok)
        text = re.sub(r'(?<![A-Za-z0-9_:~-])%s(?![A-Za-z0-9_~-])' % re.escape(key), tok, text)
        for nm in sorted(names, key=len, reverse=True):
            if len(nm) > 3:
                text = text.replace(json.dumps(nm, ensure_ascii=False)[1:-1], 'Living or private person')
    return text


PERSON_KEYS = ['id', 'qid', 'name', 'short', 'sex', 'born', 'born_precision', 'died', 'died_precision', 'house', 'core', 'family', 'father', 'mother',
               'shares', 'generation', 'confidence', 'wikipedia', 'note', 'sources']
UNION_KEYS = ['id', 'a', 'b', 'year', 'year_precision', 'close', 'relationship', 'phi', 'confidence']


def check_view(view, asof, living_years):
    """loom-view/1 as the contract writes it: keys, types, references, the privacy rule and the house rule's closure."""
    bad = []

    def no(where, what):
        bad.append({'where': where, 'problem': what})
    if view.get('version') != 'loom-view/1' or not isinstance(view.get('asof'), int):
        no('root', 'version or asof')
    for k in ('by', 'inputs', 'gates'):
        if k not in view.get('built', {}):
            no('built', 'missing %s' % k)
    if [f['key'] for f in view['families']] != ['rothschild', 'habsburg', 'darwin_wedgwood']:
        no('families', 'keys %s' % [f['key'] for f in view['families']])
    for f in view['families']:
        ids = [p['id'] for p in f['people']]
        idset = set(ids)
        hk = {h['key'] for h in f['houses']}
        if len(idset) != len(ids):
            no(f['key'], 'duplicate person ids')
        for dye, d in f['dyes'].items():
            if not d['founders'] or any(x not in idset for x in d['founders']) or not re.fullmatch(r'#[0-9a-f]{6}', d['color']):
                no(f['key'], 'dye %s founders or colour' % dye)
        for h in f['houses']:
            if list(h) != ['key', 'name', 'lon', 'lat', 'opened', 'closed', 'note'] or not (-180 <= h['lon'] <= 180 and -90 <= h['lat'] <= 90):
                no(f['key'] + '/' + h['key'], 'house shape')
        for p in f['people']:
            w = '%s/%s' % (f['key'], p['id'])
            if list(p) != PERSON_KEYS:
                no(w, 'person keys'); continue
            if p['qid'] is not None and not re.fullmatch(r'Q[1-9][0-9]*', p['qid']):
                no(w, 'qid')
            if p['sex'] not in ('M', 'F', None) or not isinstance(p['born'], int) or not (p['died'] is None or isinstance(p['died'], int)):
                no(w, 'sex or years')
            if p['died'] is None and p['born'] > asof - living_years:
                no(w, 'presumed living but published')
            if p['house'] not in hk or not isinstance(p['core'], bool):
                no(w, 'house %r not a house of the family, or core not boolean' % p['house'])
            for k in ('father', 'mother'):
                if p[k] is not None and p[k] not in idset:
                    no(w, '%s %s not in the view' % (k, p[k]))
            if list(p['shares']) != list(f['dyes']) or any(not 0 <= v <= 1 for v in p['shares'].values()):
                no(w, 'shares')
            g = p['generation']
            if not (isinstance(g, list) and len(g) == 2 and all(isinstance(x, int) for x in g) and g[0] <= g[1]):
                no(w, 'generation')
            if p['confidence'] not in ('Confirmed', 'Likely', 'Suspected') or (p['note'] and len(p['note']) > 240) or not isinstance(p['sources'], list):
                no(w, 'confidence, note or sources')
        seen = set()
        for u in f['unions']:
            w = '%s/%s' % (f['key'], u['id'])
            if list(u) != UNION_KEYS or u['id'] != 'U-%s-%s' % (u['a'], u['b']) or u['a'] not in idset or u['b'] not in idset or u['id'] in seen:
                no(w, 'union keys, id or partners'); continue
            seen.add(u['id'])
            if u['year_precision'] not in ('year', 'circa', 'unknown') or (u['year'] is None) != (u['year_precision'] == 'unknown'):
                no(w, 'year precision')
            if u['close'] != (u['phi'] > 0) or (u['relationship'] is None) == u['close'] or u['confidence'] not in ('Confirmed', 'Likely', 'Suspected'):
                no(w, 'close, relationship or confidence')
        for e in f['events']:
            if list(e) != ['year', 'label', 'grade', 'source'] or e['grade'] not in ('C', 'L') or not isinstance(e['year'], int):
                no(f['key'], 'event %r' % e.get('label'))
    return bad
