"""Find and load every genealogy dataset under a source root, as data only.

Only these paths are read (an allowlist, so `.env*` and code are never opened as data):
  */data/trees/*.json        JSON trees  {id, name, members: [...]}
  */data/family.ts           TS module   export const familyData: Record<string, FamilyMember> = {...}
  *.html, */collateral/*.html  older pages with an inline `const familyData = {...}`
  */constants.tsx            TOUR_SEQUENCE ids, BRANCH_POSITIONS keys, GENERATION_COLORS keys (regex reads, not evaluated)
  */App.tsx, */data/datasets.ts  which dataset each app variant loads and tours (regex reads)
  */dist/assets/*.js         built bundles, scanned as text for names (parity and privacy)
Identical datasets (same parsed content) are run once and keep every path they came from."""
import glob
import hashlib
import json
import os
import re
from collections import OrderedDict

import jsobj


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def _safe(p):
    assert not os.path.basename(p).startswith('.env'), p
    return p


def _canon(members):
    return hashlib.sha256(json.dumps(members, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_tree_json(path):
    raw = json.load(open(_safe(path), encoding='utf-8'), object_pairs_hook=_pairs)
    members, dups, dup_fields = OrderedDict(), [], []
    for i, m in enumerate(raw.get('members', [])):
        k = m.get('id') if isinstance(m, dict) else None
        if k is None: k = '#%d' % i
        if k in members: dups.append((k, None))
        dup_fields += [(k, f, None) for f in getattr(m, 'dups', [])]
        members[k] = dict(m)
    return dict(dataset_id=raw.get('id'), dataset_name=raw.get('name'), members=members, dup_ids=dups, dup_fields=dup_fields, kind='json-tree')


class _PairsDict(OrderedDict):
    pass


def _pairs(pairs):
    d = _PairsDict(); d.dups = []
    for k, v in pairs:
        if k in d: d.dups.append(k)
        d[k] = v
    return d


def load_literal(path, name='familyData'):
    text = open(_safe(path), encoding='utf-8').read()
    found = jsobj.find_literal(text, name)
    if not found: return None
    lit, line = found
    try:
        v = jsobj.parse_literal(lit, line)
    except jsobj.ParseError as e:
        return dict(members=OrderedDict(), dup_ids=[], dup_fields=[], parse_error=str(e), kind='ts-literal' if path.endswith('.ts') else 'html-inline', literal_line=line)
    dups = [(k, ln) for pth, k, ln in jsobj.iter_dups(v) if pth == '$']
    dup_fields = [(pth.split('.', 1)[1].split('.')[0], k, ln) for pth, k, ln in jsobj.iter_dups(v) if pth.count('.') == 1]
    members = OrderedDict((k, dict(r) if isinstance(r, dict) else r) for k, r in v.items())
    return dict(members=members, dup_ids=dups, dup_fields=dup_fields, kind='ts-literal' if path.endswith('.ts') else 'html-inline', literal_line=line,
                literal_sha256=hashlib.sha256(lit.encode()).hexdigest())


def read_constants(path):
    t = open(_safe(path), encoding='utf-8').read()
    def block(name):
        m = re.search(r'%s[^=]*=\s*([\[{])' % name, t)
        if not m: return ''
        s = m.end() - 1; close = ']' if t[s] == '[' else '}'; depth = 0
        for i in range(s, len(t)):
            depth += t[i] == t[s]; depth -= t[i] == close
            if depth == 0: return t[s:i + 1]
        return ''
    return dict(tour=re.findall(r"id:\s*['\"]([^'\"]+)['\"]", block('TOUR_SEQUENCE')),
                branches=re.findall(r"['\"]?([A-Za-z][\w ]*)['\"]?\s*:", block('BRANCH_POSITIONS')),
                gen_colours=[int(x) for x in re.findall(r'(\d+)\s*:', block('GENERATION_COLORS'))])


def app_datasets(variant_dir):
    """the dataset files an app variant loads, in DATASETS order (the tour reads DATASETS[0] or familyData)"""
    app = os.path.join(variant_dir, 'App.tsx'); ds = os.path.join(variant_dir, 'data', 'datasets.ts')
    if not os.path.exists(app): return []
    a = open(app, encoding='utf-8').read()
    if re.search(r"import\s*\{\s*familyData\s*\}\s*from\s*'./data/family'", a): return [os.path.join(variant_dir, 'data', 'family.ts')]
    if "from './data/datasets'" in a and os.path.exists(ds):
        d = open(ds, encoding='utf-8').read()
        if "from './family'" in d: return [os.path.join(variant_dir, 'data', 'family.ts')]
        imports = dict(re.findall(r"import\s+(\w+)\s+from\s+'\./trees/([\w\-]+\.json)'", d))
        order = re.findall(r'normalizeDataset\(\s*(\w+)', d)
        return [os.path.join(variant_dir, 'data', 'trees', imports[n]) for n in order if n in imports]
    return []


def discover(root):
    root = os.path.abspath(root); found = []
    for p in sorted(glob.glob(os.path.join(root, '*', 'data', 'trees', '*.json'))):
        found.append((p, load_tree_json(p)))
    for p in sorted(glob.glob(os.path.join(root, '*', 'data', 'family.ts'))):
        r = load_literal(p)
        if r: found.append((p, r))
    for p in sorted(glob.glob(os.path.join(root, '*.html')) + glob.glob(os.path.join(root, '*', 'collateral', '*.html'))):
        r = load_literal(p)
        if r: found.append((p, r))
    groups = OrderedDict()                                            # identical content -> one dataset, many paths
    for p, r in found:
        key = _canon(r['members']) + ('|err' if r.get('parse_error') else '')
        g = groups.setdefault(key, dict(r, paths=[], files={}))
        g['paths'].append(os.path.relpath(p, root)); g['files'][os.path.relpath(p, root)] = dict(sha256=sha256_file(p), bytes=os.path.getsize(p), mtime=int(os.path.getmtime(p)))
        g['content_sha256'] = key.split('|')[0]
    datasets = list(groups.values())
    for d in datasets:
        d['mtime'] = min(f['mtime'] for f in d['files'].values())
        ids = set(d['members'])
        d['lineage'] = 'rothschild' if 'mayer' in ids else (d.get('dataset_id') or os.path.splitext(os.path.basename(d['paths'][0]))[0]).replace('_stub', '')
    lin = OrderedDict()
    for d in sorted(datasets, key=lambda d: d['mtime']):
        n = lin.setdefault(d['lineage'], 0) + 1; lin[d['lineage']] = n; d['version'] = 'v%d' % n
        d['label'] = '%s %s (%s)' % (d['lineage'], d['version'], os.path.basename(d['paths'][0]))
    variants = OrderedDict()
    for vd in sorted(glob.glob(os.path.join(root, '*', 'App.tsx'))):
        v = os.path.dirname(vd); name = os.path.relpath(v, root)
        cons = os.path.join(v, 'constants.tsx')
        variants[name] = dict(datasets=[os.path.relpath(x, root) for x in app_datasets(v)],
                              constants=read_constants(cons) if os.path.exists(cons) else None,
                              bundles=[os.path.relpath(b, root) for b in sorted(glob.glob(os.path.join(v, 'dist', 'assets', '*.js')))])
    return root, datasets, variants
