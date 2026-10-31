#!/usr/bin/env python3
"""Run the genealogy DATA gates (and the cross-reference and bundle gates) over every dataset under a source root.

  python3 -I run_gates.py SRC_ROOT OUT_DIR [--asof 2026]

Writes OUT_DIR/findings.jsonl (one finding per line, with a fingerprint that is stable across versions of a lineage),
OUT_DIR/lineage.json (each defect's status in every version: present, fixed, or n/a), OUT_DIR/receipt.json (every input and
every checker file by sha256, the thresholds, the counts and the verdicts). Exit status 1 when any dataset has an error.
Reads data only (see sources.py): nothing under SRC_ROOT is executed or imported."""
import hashlib
import json
import os
import platform
import sys
import time
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)     # -I drops the script's folder from sys.path
import datagates
import sources

TOOL = 'genealogy-gates 0.1'


def fp(lineage, f):
    if f['detail'].get('fp_key'): return hashlib.sha256('|'.join([lineage, f['gate'], f['detail']['fp_key']]).encode()).hexdigest()[:12]
    return hashlib.sha256('|'.join([lineage, f['gate'], f['subject'] or '', ','.join(sorted(f['refs'])), str(f['detail'].get('kind', '')), str(f['detail'].get('field', ''))]).encode()).hexdigest()[:12]


def js_variants(name):
    """the spellings a bundler may use for a name inside a JS string"""
    out = {name}
    if any(ord(c) > 127 for c in name):
        out.add(''.join(c if ord(c) < 128 else '\\u%04x' % ord(c) for c in name))
        out.add(''.join(c if ord(c) < 128 else '\\u%04X' % ord(c) for c in name))
    return out


def main(argv):
    if len(argv) < 3: print(__doc__); return 2
    src, out = argv[1], argv[2]; cfg = {}
    if '--asof' in argv: cfg['asof'] = int(argv[argv.index('--asof') + 1])
    os.makedirs(out, exist_ok=True); t0 = time.time()
    root, datasets, variants = sources.discover(src)
    findings, per_ds = [], OrderedDict()
    for d in datasets:
        fs = []
        if d.get('parse_error'):
            fs.append(datagates.F('D00-schema', 'error', None, 'could not read the literal as data: ' + d['parse_error'], kind='unparseable'))
        else:
            fs += datagates.check(d['members'], cfg)
        for k, ln in d.get('dup_ids', []):
            fs.append(datagates.F('D07-duplicate', 'error', k, 'id %r defined twice%s: the app keeps the last one and loses the first' % (k, ' (second at line %d)' % ln if ln else ''), kind='dup-id'))
        for k, f, ln in d.get('dup_fields', []):
            fs.append(datagates.F('D00-schema', 'error', k, 'field %r given twice%s: the last one wins' % (f, ' (line %d)' % ln if ln else ''), field=f, kind='dup-field'))
        for f in fs:
            f.update(dataset=d['label'], lineage=d['lineage'], version=d['version'], paths=d['paths'], fingerprint=fp(d['lineage'], f))
        findings += fs
        sev = defaultdict(int)
        for f in fs: sev[f['severity']] += 1
        per_ds[d['label']] = dict(paths=d['paths'], kind=d['kind'], content_sha256=d['content_sha256'], members=len(d['members']),
                                  counts=dict(sev), by_gate=datagates.summarize(fs), verdict='fail' if sev['error'] else 'pass')

    # ---- cross-reference gates: what the app variant asks of the data it loads (tour stops, branch angles, generation colours)
    by_path = {p: d for d in datasets for p in d['paths']}
    xfind = []
    for vname, v in variants.items():
        dsets = [by_path[p] for p in v['datasets'] if p in by_path]
        c = v['constants'] or {}
        if not dsets: continue
        toured = dsets[0]
        for stop in c.get('tour', []):
            if stop not in toured['members']:
                xfind.append(datagates.F('X01-tour-stop', 'error', stop, 'tour stop %r is not in %s, the dataset this variant tours: the stop holds for 8 s on nothing' % (stop, toured['label']), variant=vname))
        branches = set(c.get('branches', []))
        for d in dsets:
            used = sorted({m.get('branch') for m in d['members'].values() if isinstance(m, dict) and m.get('branch')})
            for b in used:
                if b not in branches:
                    xfind.append(datagates.F('X02-branch-angle', 'warn', b, 'branch %r (%s) has no BRANCH_POSITIONS entry: placed at angle 0, on top of Frankfurt' % (b, d['label']), variant=vname))
            gens = sorted({m.get('generation') for m in d['members'].values() if isinstance(m, dict) and isinstance(m.get('generation'), int)})
            for g in gens:
                if c.get('gen_colours') and g not in c['gen_colours']:
                    xfind.append(datagates.F('X03-generation-colour', 'warn', str(g), 'generation %d (%s) has no GENERATION_COLORS entry: drawn white' % (g, d['label']), variant=vname))
    for f in xfind: f.update(dataset='app:' + f['detail']['variant'], lineage='app', version='-', paths=[f['detail']['variant']], fingerprint=fp('app', f))
    findings += xfind

    # ---- bundle gates: which data a built bundle carries (parity with the source it should be built from) and no presumed-living name in it
    living = {(f['dataset'], f['subject']) for f in findings if f['gate'] == 'D10-living' and f['severity'] == 'error'}
    bundles = OrderedDict()
    for vname, v in variants.items():
        for b in v['bundles']:
            text = open(os.path.join(root, b), encoding='utf-8', errors='replace').read()
            match = OrderedDict()
            for d in datasets:
                names = [m.get('name') for m in d['members'].values() if isinstance(m, dict) and m.get('name')]
                hit = [n for n in names if any(s in text for s in js_variants(n))]
                match[d['label']] = dict(present=len(hit), of=len(names), missing=[n for n in names if n not in hit][:12])
            want = [by_path[p]['label'] for p in v['datasets'] if p in by_path]
            res = dict(variant=vname, sha256=sources.sha256_file(os.path.join(root, b)), bytes=os.path.getsize(os.path.join(root, b)), should_carry=want, match=match)
            for lbl in want:
                if match[lbl]['present'] < match[lbl]['of']:
                    findings.append(dict(datagates.F('R01-bundle-parity', 'error', lbl, 'bundle %s lacks %d of %d names of %s: built from other data than the source' % (b, match[lbl]['of'] - match[lbl]['present'], match[lbl]['of'], lbl), missing=match[lbl]['missing']),
                                         dataset='bundle:' + b, lineage='bundle', version='-', paths=[b], fingerprint=hashlib.sha256(('R01|' + b + '|' + lbl).encode()).hexdigest()[:12]))
            for dl, k in living:
                d = next(x for x in datasets if x['label'] == dl); n = d['members'][k].get('name')
                if n and any(s in text for s in js_variants(n)):
                    findings.append(dict(datagates.F('R02-bundle-privacy', 'error', k, 'presumed-living %r is inside the built bundle %s' % (n, b)),
                                         dataset='bundle:' + b, lineage='bundle', version='-', paths=[b], fingerprint=hashlib.sha256(('R02|' + b + '|' + k).encode()).hexdigest()[:12]))
            bundles[b] = res

    # ---- lineage: every fingerprint's status in every version of its lineage (the regression corpus is built from this)
    lineage = OrderedDict()
    for lin in OrderedDict.fromkeys(d['lineage'] for d in datasets):
        vers = sorted([d for d in datasets if d['lineage'] == lin], key=lambda d: d['mtime'])
        if len(vers) < 2: continue
        rows = OrderedDict()
        for f in findings:
            if f['lineage'] != lin or f['severity'] == 'info': continue
            r = rows.setdefault(f['fingerprint'], dict(gate=f['gate'], subject=f['subject'], refs=f['refs'], field=f['detail'].get('field'), severity=f['severity'], status=OrderedDict(), first_message=f['message']))
        for fpk, r in rows.items():
            for d in vers:
                hit = any(f['fingerprint'] == fpk and f['dataset'] == d['label'] for f in findings)
                inside = r['subject'] is None or (r['subject'] in d['members'] and all(x in d['members'] for x in r['refs'] if x != r['subject'] and x is not None))
                r['status'][d['label']] = 'present' if hit else ('absent' if inside else 'n/a')
            seq = list(r['status'].values()); labs = list(r['status'])
            r['introduced'] = next((labs[i] for i in range(len(seq)) if seq[i] == 'present' and (i == 0 or seq[i - 1] != 'present')), None)
            r['resolved'] = next((labs[i] for i in range(1, len(seq)) if seq[i] == 'absent' and seq[i - 1] == 'present'), None)
            if r['introduced'] == labs[0]: r['introduced'] = labs[0] + ' (or earlier)'
        lineage[lin] = dict(versions=[dict(label=d['label'], paths=d['paths'], mtime=time.strftime('%Y-%m-%d %H:%M', time.gmtime(d['mtime'])), members=len(d['members'])) for d in vers], defects=rows)

    with open(os.path.join(out, 'findings.jsonl'), 'w', encoding='utf-8') as fh:
        for f in findings: fh.write(json.dumps(f, ensure_ascii=False) + '\n')
    json.dump(lineage, open(os.path.join(out, 'lineage.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    inputs = OrderedDict()
    for d in datasets:
        for p, meta in d['files'].items(): inputs[p] = dict(meta, role=d['kind'], dataset=d['label'])
    for vname, v in variants.items():
        for rel in ([os.path.join(vname, 'constants.tsx')] if v['constants'] is not None else []) + [os.path.join(vname, 'App.tsx')]:
            full = os.path.join(root, rel)
            if os.path.exists(full): inputs[rel] = dict(sha256=sources.sha256_file(full), bytes=os.path.getsize(full), role='app-config (regex read)')
        for b in v['bundles']: inputs[b] = dict(sha256=bundles[b]['sha256'], bytes=bundles[b]['bytes'], role='built bundle (text scan)')
    sev = defaultdict(int)
    for f in findings: sev[f['severity']] += 1
    receipt = OrderedDict(
        tool=TOOL, ran_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t0)), seconds=round(time.time() - t0, 3),
        python=platform.python_version(), thresholds=dict(datagates.DEFAULTS, **cfg),
        checker={os.path.basename(p): sources.sha256_file(p) for p in sorted(os.path.join(HERE, n) for n in ('jsobj.py', 'sources.py', 'datagates.py', 'run_gates.py'))},
        source_root=root, inputs=inputs, datasets=per_ds,
        variants={k: dict(datasets=v['datasets'], tour=(v['constants'] or {}).get('tour'), bundles=v['bundles']) for k, v in variants.items()},
        bundles=bundles, totals=dict(sev), verdict='fail' if any(x['verdict'] == 'fail' for x in per_ds.values()) or any(f['severity'] == 'error' for f in xfind) else 'pass',
        grade='Confirmed for what the files say (computed by this checker over the inputs listed by sha256). Not a claim about who is related to whom: that needs a second witness per relation.',
        limits=['No sex or role field: the mother rule (no birth after her death) and a separate mother age bound cannot be applied; one rule, death + posthumous_tol, covers both parents.',
                'Year-granular dates: same-year cases are given the benefit of the doubt.',
                'Duplicate detection is name tokens plus birth year within 1; it misses renamed or misspelt duplicates.',
                'Bundle parity and privacy are text scans of the minified bundle: a name split or encoded differently is missed.'])
    json.dump(receipt, open(os.path.join(out, 'receipt.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    # ---- console summary
    print('%s  asof %d  %d datasets, %d app variants, %d bundles\n' % (TOOL, receipt['thresholds']['asof'], len(datasets), len(variants), len(bundles)))
    for lbl, r in per_ds.items():
        print('%-50s %3d people  %-4s  err %d  warn %d  info %d   %s' % (lbl, r['members'], r['verdict'], r['counts'].get('error', 0), r['counts'].get('warn', 0), r['counts'].get('info', 0), ', '.join(r['paths'])))
    print()
    for f in findings:
        if f['severity'] in ('error', 'warn'):
            print('%-5s %-28s %-42s %-16s %s' % (f['severity'].upper(), f['gate'], f['dataset'][:42], f['subject'] or '-', f['message']))
    print('\nbundles (names of each dataset found in the built JS, as text):')
    for b, r in bundles.items():
        print('  %s  should carry %s' % (b, ', '.join(r['should_carry'])))
        for lbl, m in r['match'].items():
            if m['present']: print('      %-48s %2d of %2d names' % (lbl, m['present'], m['of']))
    print('\nlineage (error and warn defects across versions):')
    for lin, L in lineage.items():
        labels = [v['label'] for v in L['versions']]
        print('  %s: %s' % (lin, '  ->  '.join('%s [%d]' % (v['label'].split(' (')[0].split(' ')[-1] + ' ' + v['label'].split('(')[1].rstrip(')'), v['members']) for v in L['versions'])))
        for fpk, r in L['defects'].items():
            print('    %-12s %-28s %-15s %s   %s' % (fpk, r['gate'], r['subject'] or '(%s)' % r.get('field', 'all'), '  '.join({'present': 'X', 'absent': '.', 'n/a': '-'}[r['status'][l]] for l in labels),
                                                 ('introduced ' + r['introduced'].split(' (')[0].split(' ', 1)[1] if r['introduced'] else '') + ('; resolved ' + r['resolved'].split(' (')[0].split(' ', 1)[1] if r['resolved'] else '')))
    print('\ntotals', dict(sev), ' verdict', receipt['verdict'], ' (%.2f s)' % receipt['seconds'])
    return 1 if receipt['verdict'] == 'fail' else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
