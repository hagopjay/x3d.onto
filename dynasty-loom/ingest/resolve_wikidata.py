#!/usr/bin/env python3
"""Wikidata stage (optional, after ingest): enwiki sitelinks to QIDs plus the dates Wikidata states, written as an overlay
source in the Cosmos JSON-tree shape, so ingest.py reads it like any other source (family 'wikidata', prov 'data').

  python3 -I resolve_wikidata.py --graph out/private/genealogy.graph.json --dataset rothschild --out cache/wikidata-rothschild.json
  python3 -I resolve_wikidata.py ... --offline-response saved.json      # parse a saved API response instead of fetching

NOT RUN against the live API in this session: wikidata.org was refused by the egress proxy (HTTP 403 on CONNECT,
2026-10-29). One wbgetentities call per 50 titles (sites=enwiki, props=sitelinks|claims). Kept: the QID; P569 / P570
(birth, death) when precision is year or finer and the calendar is Gregorian (Q1985727) or Julian (Q1985786); P22 / P25
(father, mother) and P26 (spouse) QIDs, for a later edge check. The overlay records the request URLs, the retrieval time
and the sha256 of each response, so the claims it feeds are pinned like every other input. Add it to the manifest with
"family": "wikidata", "prov": "data", "default_grade": "Likely", "overlay": true, after the decisions and before the app data
if Wikidata should win contested dates, after the app data if it should only corroborate.
"""
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request

API = 'https://www.wikidata.org/w/api.php'
UA = 'loom-genealogy-ingest/0.1 (prototype; contact: repository owner)'
CAL = {'http://www.wikidata.org/entity/Q1985727': 'GREGORIAN', 'http://www.wikidata.org/entity/Q1985786': 'JULIAN'}


def chunks(xs, n=50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def url_for(titles):
    return API + '?' + urllib.parse.urlencode({'action': 'wbgetentities', 'sites': 'enwiki', 'titles': '|'.join(titles), 'props': 'sitelinks|claims',
                                               'sitefilter': 'enwiki', 'format': 'json', 'formatversion': '2'})


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _time(claims, prop):
    for st in claims.get(prop, []):
        if st.get('rank') == 'deprecated':
            continue
        dv = ((st.get('mainsnak') or {}).get('datavalue') or {}).get('value') or {}
        t, prec, cal = dv.get('time'), dv.get('precision'), CAL.get(dv.get('calendarmodel'))
        if t and prec is not None and prec >= 9 and cal:
            year = int(t[1:].split('-')[0]) * (-1 if t.startswith('-') else 1)
            return {'year': year, 'precision': {9: 'year', 10: 'month', 11: 'day'}.get(prec, 'day'), 'calendar': cal, 'time': t,
                    'referenced': bool(st.get('references'))}
    return None


def _items(claims, prop):
    out = []
    for st in claims.get(prop, []):
        dv = ((st.get('mainsnak') or {}).get('datavalue') or {}).get('value') or {}
        if dv.get('id'):
            out.append(dv['id'])
    return out


def parse(responses, wanted):
    """responses: list of (url, bytes). wanted: {enwiki title with spaces: local id}. Returns overlay members and a log."""
    members, log = [], []
    for url, body in responses:
        data = json.loads(body)
        log.append({'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
        ents = data.get('entities', {})
        ents = ents.values() if isinstance(ents, dict) else ents
        for e in ents:
            if 'missing' in e or not e.get('id', '').startswith('Q'):
                continue
            title = ((e.get('sitelinks') or {}).get('enwiki') or {}).get('title')
            if title not in wanted:
                continue
            c = e.get('claims') or {}
            m = {'id': wanted[title], 'wikidata': e['id']}
            b, d = _time(c, 'P569'), _time(c, 'P570')
            if b and b['calendar'] == 'GREGORIAN':      # the JSON-tree shape carries Gregorian years; Julian dates go to the log
                m['born'] = b['year']
            if d and d['calendar'] == 'GREGORIAN':
                m['died'] = d['year']
            m['wikidata_detail'] = {'P569': b, 'P570': d, 'P22': _items(c, 'P22'), 'P25': _items(c, 'P25'), 'P26': _items(c, 'P26')}
            members.append(m)
    return members, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--dataset', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--offline-response', action='append', default=[], help='a saved wbgetentities response (repeatable)')
    a = ap.parse_args()
    g = json.load(open(a.graph, encoding='utf-8'))
    wanted = {}
    for n in g['nodes']:
        if n['cls'] == 'Person' and n.get('dataset') == a.dataset and (n.get('ids') or {}).get('enwiki') and not n['ids'].get('wikidata'):
            wanted[n['ids']['enwiki'].replace('_', ' ')] = n['local']
    titles = sorted(wanted)
    if a.offline_response:
        responses = [('offline:' + p, open(p, 'rb').read()) for p in a.offline_response]
    else:
        responses = []
        for part in chunks(titles):
            u = url_for(part); responses.append((u, fetch(u))); time.sleep(1)
    members, log = parse(responses, wanted)
    overlay = {'id': a.dataset, 'name': 'Wikidata via wbgetentities, retrieved %s' % time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'retrieval': log, 'asked': len(titles), 'resolved': len(members), 'members': members}
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(overlay, fh, ensure_ascii=False, indent=1)
    print(json.dumps({'asked': len(titles), 'resolved': len(members), 'out': a.out}))


if __name__ == '__main__':
    main()
