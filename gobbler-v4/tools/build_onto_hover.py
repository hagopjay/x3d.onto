#!/usr/bin/env python3
"""Trim the X3D Ontology 4.1 and its XSD cross-check to what a hover card needs: per class the ancestry, the ontology's own
definition, the field count, and the XSD 4.1 verdicts on the placements the ontology predicts (accept / reject / inconclusive).

    python3 -I gobbler-v4/tools/build_onto_hover.py [--ontology data/ontology41.json] [--xcheck data/xcheck_all.json]
                                                    [--out gobbler-v4/data/onto-hover.json] [--mcp-commit fa0b389] [--graph data/deep/graph-v3.json]

With --graph only the classes whose name matches a drawn NodeType or Component star are kept (what the viewer can show).

Input rows in xcheck_all.json are [child, parent, property, verdict, note] with verdict A (accepted), R (rejected), I (inconclusive).
Output is deterministic (sorted keys, compact): all 364 classes are about 132 KB raw, 22 KB gzip; with --graph about a third of that.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
DEFN_MAX = 240
SAMPLE = 8


def build(onto, xc, mcp_commit, wanted=None):
    placements = {}
    for child, parent, _prop, verdict, _note in xc['rows']:
        d = placements.setdefault(child, {'A': 0, 'R': 0, 'I': 0, 'ok_parents': []})
        if verdict not in ('A', 'R', 'I'):
            raise SystemExit('unknown verdict %r in row for %s' % (verdict, child))
        d[verdict] += 1
        if verdict == 'A' and parent not in d['ok_parents']:
            d['ok_parents'].append(parent)
    classes, by_lower = {}, {}
    for n in onto['nodes']:
        cid = n['id']
        if wanted is not None and cid.lower() not in wanted:
            continue
        p = placements.get(cid, {'A': 0, 'R': 0, 'I': 0, 'ok_parents': []})
        defn = (n.get('defn') or '').strip()
        if len(defn) > DEFN_MAX:
            defn = defn[:DEFN_MAX - 1].rstrip() + '…'
        rec = {'cp': n.get('comp') or '', 'a': n.get('ancs') or [], 'd': defn, 'nf': n.get('nf', len(n.get('fields') or [])), 'k': n.get('kind') or '',
               'n': p['A'] + p['R'] + p['I'], 'A': p['A'], 'R': p['R'], 'I': p['I'], 'ap': len(p['ok_parents']), 'aps': sorted(p['ok_parents'])[:SAMPLE]}
        classes[cid] = rec
        low = cid.lower()
        if low in by_lower and by_lower[low] != cid:
            raise SystemExit('case collision between %s and %s' % (by_lower[low], cid))
        by_lower[low] = cid
    t = xc['totals']
    return {'meta': {'ontology_sha256': xc['ontology_sha256'], 'ontology_sha256_16': xc['ontology_sha256'][:16], 'xsd': xc['schema'], 'mcp_commit': mcp_commit,
                     'totals': {'A': t['A'], 'R': t['R'], 'I': t['I'], 'rows': xc['pairs']}, 'classes': len(classes)},
            'by_lower': by_lower, 'c': classes}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ontology', default=os.path.join(ROOT, 'data', 'ontology41.json'))
    ap.add_argument('--xcheck', default=os.path.join(ROOT, 'data', 'xcheck_all.json'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'gobbler-v4', 'data', 'onto-hover.json'))
    ap.add_argument('--graph', help='graph-v3.json; keep only classes drawn there as NodeType or Component')
    ap.add_argument('--mcp-commit', default='fa0b389', help='x3d_mcp checkout the XSD verdicts were produced with (data/xcheck_all.json does not record it)')
    a = ap.parse_args()
    onto, xc = json.load(open(a.ontology)), json.load(open(a.xcheck))
    if sum(xc['totals'].values()) != xc['pairs'] or len(xc['rows']) != xc['pairs']:
        raise SystemExit('xcheck totals disagree with its rows')
    wanted = None
    if a.graph:
        g = json.load(open(a.graph))
        wanted = {n['label'].lower() for n in g['nodes'][:g['drawn']] if n['cls'] in ('NodeType', 'Component')}
    out = build(onto, xc, a.mcp_commit, wanted)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(out, f, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    sz = os.path.getsize(a.out)
    print('wrote %s: %d classes, %d bytes' % (os.path.relpath(a.out, ROOT), out['meta']['classes'], sz))


if __name__ == '__main__':
    main()
