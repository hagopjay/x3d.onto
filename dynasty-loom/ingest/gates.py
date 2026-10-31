"""Gates: each one a check with a severity, a status and its findings. An 'error' gate that fails blocks the public
candidate (ingest.py exits non-zero and writes no public files). Warnings are findings about the data, kept in the receipt.
"""
from collections import OrderedDict

import gdates

CAP = 60   # findings kept per gate in the receipt; the full list is in gates.json


def gate(gid, name, severity, findings, tool='ingest.py', passed=None, note=None):
    fail = bool(findings) if passed is None else not passed
    status = 'pass' if not fail else {'error': 'fail', 'warn': 'warn', 'info': 'info'}[severity]
    d = OrderedDict(id=gid, name=name, severity=severity, status=status, count=len(findings), tool=tool)
    if note:
        d['note'] = note
    d['findings'] = findings
    return d


def renderer_parity(builder, sources):
    """Replay each consumer's spouse-edge rule on the source it loads (rules read from the shipped code, see the manifest):
    react-lt-dataset  `${ds}:${id} < ${ds}:${spouse}` (roths/dist bundle, roths3/components/CosmosScene.tsx)
    html-lt           `id < person.spouse`            (rothsch2.html)
    html-all          every spouse field draws         (rothschilds.html)"""
    out = []
    for s in sources:
        rule = s.get('consumer_rule')
        if not rule:
            continue
        ds = s['dataset']
        recs = builder.records_in[s['id']]
        pairs = OrderedDict()
        drawn = []
        for c in builder.claims:
            if c['source'] != s['id'] or c['predicate'] != 'spouse':
                continue
            a, b = c['_local'], c['value']
            pairs.setdefault(tuple(sorted((a, b))), []).append(a)
            if b not in recs:
                continue
            if rule == 'react-lt-dataset':
                ok = '%s:%s' % (ds, a) < '%s:%s' % (ds, b)
            elif rule == 'html-lt':
                ok = a < b
            else:
                ok = True
            if ok:
                drawn.append(tuple(sorted((a, b))))
        for p, holders in pairs.items():
            n = drawn.count(p)
            if n == 0:
                out.append({'source': s['id'], 'rule': rule, 'couple': list(p), 'field_held_by': holders, 'drawn': 0, 'problem': 'marriage never drawn'})
            elif n > 1:
                out.append({'source': s['id'], 'rule': rule, 'couple': list(p), 'drawn': n, 'problem': 'drawn %d times (overlapping edges)' % n})
    return out


def temporal(graph, policy):
    nodes = {n['id']: n for n in graph['nodes']}
    out = []

    def yb(n, ev):
        f = (n.get('facts') or {}).get(ev)
        return gdates.year_bounds(f['date']) if f and f.get('date') else (None, None)
    for n in nodes.values():
        if n['cls'] != 'Person':
            continue
        (b0, b1), (d0, d1) = yb(n, 'birth'), yb(n, 'death')
        if b0 is not None and d1 is not None and d1 < b0:
            out.append({'person': n['id'], 'severity': 'error', 'problem': 'death before birth'})
        if b1 is not None and d0 is not None and d0 - b1 > policy['max_lifespan']:
            out.append({'person': n['id'], 'severity': 'warn', 'problem': 'lifespan over %d years' % policy['max_lifespan']})
    for u in nodes.values():
        if u['cls'] != 'Union':
            continue
        for ch in u['children']:
            c0, c1 = yb(nodes[ch], 'birth')
            if c0 is None:
                continue
            for p in u['partners']:
                p0, p1 = yb(nodes[p], 'birth'); q0, q1 = yb(nodes[p], 'death')
                if p0 is not None:
                    amin, amax = c0 - p1, c1 - p0
                    if amax < policy['min_parent_age']:
                        out.append({'child': ch, 'parent': p, 'severity': 'error', 'problem': 'parent at most %d at the birth' % amax})
                    elif amax < policy['warn_parent_age_below']:
                        out.append({'child': ch, 'parent': p, 'severity': 'warn', 'problem': 'parent aged %d to %d at the birth' % (max(amin, 0), amax)})
                    elif amin > policy['warn_parent_age_above']:
                        out.append({'child': ch, 'parent': p, 'severity': 'warn', 'problem': 'parent aged %d to %d at the birth: a missing generation?' % (amin, amax)})
                if q1 is not None and c0 > q1 + 1:
                    out.append({'child': ch, 'parent': p, 'severity': 'error', 'problem': 'born more than a year after the parent died'})
    return out


def privacy(public):
    out = []
    for n in public['nodes']:
        if n['cls'] == 'Person' and n.get('vis') != 'public':
            if n.get('names') or n.get('facts') or n.get('notes') or (n.get('ids') or {}).get('enwiki') or n.get('label') not in ('Living or private person', 'Withheld record'):
                out.append({'person': n['id'], 'problem': 'redacted person still carries identity'})
        if n['cls'] == 'Person' and n.get('vis') == 'public' and (n.get('living') or {}).get('value') is not False:
            out.append({'person': n['id'], 'problem': 'public but not shown dead'})
    for s in public['sources']:
        if 'path' in s or 'copies' in s:
            out.append({'source': s['id'], 'problem': 'path left in public candidate'})
    hidden = {n['id'] for n in public['nodes'] if n['cls'] == 'Person' and n.get('vis') != 'public'}
    for e in public['edges']:
        if e['s'] in hidden and e['p'] in ('member_of', 'born_in', 'died_in', 'alt_parent'):
            out.append({'edge': [e['s'], e['p'], e['t']], 'problem': 'edge describes a redacted person'})
    for c in public['claims']:
        if c['subject'] in hidden or any(r['id'] in hidden for r in c.get('refs', [])):
            out.append({'claim': c['id'], 'problem': 'claim about a redacted person'})
    par = {}
    for u in public['nodes']:
        if u['cls'] == 'Union':
            for ch in u['children']:
                par.setdefault(ch, []).extend(u['partners'])
    for n in public['nodes']:
        if n['cls'] == 'Person' and n.get('vis') == 'public' and (n.get('metrics') or {}).get('inbreeding_F') is not None:
            stack, seen = list(par.get(n['id'], [])), set()
            while stack:
                q = stack.pop()
                if q in hidden:
                    out.append({'person': n['id'], 'problem': 'metric computed through a redacted ancestor is published'}); break
                if q not in seen:
                    seen.add(q); stack += par.get(q, [])
    return out


def verbatim(graph, texts):
    out, n = [], 0
    for c in graph['claims']:
        n += 1
        t = texts.get(c['source'])
        if t is None or not c['quote'] or c['quote'] not in t:
            out.append({'claim': c['id'], 'source': c['source'], 'locator': c['locator']})
    return out, n


def calendars(graph):
    out = []
    for n in graph['nodes']:
        if n['cls'] != 'Person':
            continue
        for ev, f in (n.get('facts') or {}).items():
            d = f.get('date')
            if d and d.get('calendar') == 'GREGORIAN' and d.get('start') and d['start']['y'] < 1582:
                out.append({'person': n['id'], 'fact': ev, 'value': d['gedcom'], 'note': 'before the Gregorian reform (1582) with no calendar given: historians normally quote Julian dates; harmless at year precision, wrong at day precision'})
    return out
