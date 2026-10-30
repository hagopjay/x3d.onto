"""GEDCOM 7: a small parser, an importer to the loom claim stream, and an exporter from the canonical graph.

Parser: FamilySearch GEDCOM 7.0 line grammar (Level [Xref] Tag [LineVal]), UTF-8 only, any of CR / LF / CRLF, a leading
BOM, CONT joins (CONC is a 5.5.1 structure and is refused), pointers and @VOID@, a leading "@@" unescaped to "@".
Importer: INDI, FAM, SOUR records to claims of the same shape the Cosmos loaders emit (subject, predicate, value, locator,
quote), so one canonical builder serves both. Exporter: the canonical graph back to GEDCOM 7 with documented extension
tags (HEAD.SCHMA) for what GEDCOM has no slot for: the loom id, the grade, the source sha256.
This is a prototype: it reads the structures listed above and keeps every other structure in `unread` for the gate.
"""
import re

import gdates

LINE = re.compile(r'^(0|[1-9][0-9]*) (?:(@[A-Z0-9_]+@) )?([A-Z][A-Z0-9_]*|_[A-Z0-9_]+)(?: (.*))?$')
POINTER = re.compile(r'^@[A-Z0-9_]+@$')
EXT_URI = 'https://polyxandria.example/genealogy#'
EXT_TAGS = {'_LOOMID': EXT_URI + 'id', '_GRADE': EXT_URI + 'grade', '_SHA256': EXT_URI + 'sha256', '_BRANCH': EXT_URI + 'branch'}
EXID_WIKIDATA = 'http://www.wikidata.org/entity/'
EXID_ENWIKI = 'https://en.wikipedia.org/wiki/'
QUAY_OF_GRADE = {'Confirmed': '3', 'Likely': '2', 'Suspected': '1'}
GRADE_OF_QUAY = {'3': 'Likely', '2': 'Likely', '1': 'Suspected', '0': 'Suspected'}   # an author's QUAY is their judgement, not a check we ran


class GedcomError(ValueError):
    pass


class Node:
    __slots__ = ('level', 'xref', 'tag', 'value', 'ptr', 'children', 'line', 'raw')

    def __init__(self, level, xref, tag, value, ptr, line, raw):
        self.level, self.xref, self.tag, self.value, self.ptr, self.line, self.raw = level, xref, tag, value, ptr, line, raw
        self.children = []

    def first(self, tag):
        return next((c for c in self.children if c.tag == tag), None)

    def all(self, tag):
        return [c for c in self.children if c.tag == tag]


def parse(text):
    """Text to a list of level-0 records (Node trees). Raises GedcomError with the line number on a grammar fault."""
    if text.startswith('﻿'):
        text = text[1:]
    lines = re.split(r'\r\n|\r|\n', text)
    if lines and lines[-1] == '':
        lines.pop()
    stack, records = [], []
    for no, raw in enumerate(lines, 1):
        m = LINE.match(raw)
        if not m:
            raise GedcomError('line %d: not a GEDCOM 7 line: %r' % (no, raw[:80]))
        level, xref, tag, val = int(m.group(1)), m.group(2), m.group(3), m.group(4)
        ptr = None
        if val is not None and POINTER.match(val):
            ptr, val = val, None
        elif val is not None and val.startswith('@'):
            if not val.startswith('@@'):
                raise GedcomError('line %d: payload starting with "@" must be a pointer or escaped as "@@"' % no)
            val = val[1:]
        if tag == 'CONC':
            raise GedcomError('line %d: CONC is not GEDCOM 7' % no)
        if level > len(stack):
            raise GedcomError('line %d: level jumps from %d to %d' % (no, len(stack) - 1, level))
        del stack[level:]
        if tag == 'CONT':
            if not stack:
                raise GedcomError('line %d: CONT without a parent' % no)
            parent = stack[-1]
            parent.value = (parent.value or '') + '\n' + (val or '')
            stack.append(Node(level, None, tag, val, None, no, raw))   # placeholder so deeper levels stay aligned
            continue
        n = Node(level, xref, tag, val, ptr, no, raw)
        if level == 0:
            records.append(n)
        else:
            stack[-1].children.append(n)
        stack.append(n)
    if not records or records[0].tag != 'HEAD':
        raise GedcomError('first record must be HEAD')
    if records[-1].tag != 'TRLR':
        raise GedcomError('last record must be TRLR')
    return records


def version(records):
    h = records[0]; g = h.first('GEDC'); v = g.first('VERS') if g else None
    return v.value if v else None


def _name(payload):
    full = re.sub(r'\s+', ' ', (payload or '').replace('/', ' ')).strip()
    sm = re.search(r'/([^/]*)/', payload or '')
    return full, (sm.group(1).strip() if sm and sm.group(1).strip() else None)


def _coord(v):
    m = re.fullmatch(r'([NSEW])(\d+(?:\.\d+)?)', (v or '').strip())
    if not m:
        return None
    x = float(m.group(2))
    return -x if m.group(1) in 'SW' else x


KNOWN_INDI = {'NAME', 'SEX', 'BIRT', 'DEAT', 'FAMS', 'FAMC', 'EXID', 'NOTE', 'RESN', 'SOUR', '_LOOMID', '_BRANCH'}
KNOWN_FAM = {'HUSB', 'WIFE', 'CHIL', 'MARR', 'DIV', '_LOOMID', 'NOTE', 'SOUR'}


def import_claims(records, file_label):
    """GEDCOM records to the loom claim stream. Returns (claims, report). Each claim:
       {kind: person|union|source, subject, predicate, value, locator, quote, quay?, cites?}"""
    claims, unread = [], []
    v = version(records)
    if not (v or '').startswith('7.'):
        raise GedcomError('HEAD.GEDC.VERS is %r; this importer reads GEDCOM 7 only' % v)

    def C(kind, subj, pred, val, node, **kw):
        d = {'kind': kind, 'subject': subj, 'predicate': pred, 'value': val, 'locator': 'L%d %s' % (node.line, node.tag), 'quote': node.raw.strip()}
        d.update({k: x for k, x in kw.items() if x is not None})
        claims.append(d)

    def cites(node):
        out, quay = [], None
        for s in node.all('SOUR'):
            page = s.first('PAGE'); q = s.first('QUAY')
            out.append({'source': (s.ptr or '').strip('@') or None, 'page': page.value if page else None})
            if q is not None:
                quay = q.value if quay is None else min(quay, q.value)
        return out or None, quay

    def event(kind, sid, pred, ev):
        cs, quay = cites(ev)
        if ev.value == 'Y' and not ev.first('DATE'):
            C(kind, sid, pred + '.occurred', True, ev, cites=cs, quay=quay)
        d = ev.first('DATE')
        if d is not None:
            ph = d.first('PHRASE')
            C(kind, sid, pred, gdates.parse_gedcom(d.value, ph.value if ph else None), d, cites=cs, quay=quay)
        p = ev.first('PLAC')
        if p is not None:
            place = {'name': p.value}
            mp = p.first('MAP')
            if mp is not None:
                la, lo = mp.first('LATI'), mp.first('LONG')
                place.update(lat=_coord(la.value if la else None), lon=_coord(lo.value if lo else None))
            C(kind, sid, pred + '.place', place, p, cites=cs, quay=quay)

    for r in records[1:-1]:
        rid = (r.xref or '').strip('@')
        if r.tag == 'INDI':
            for c in r.children:
                if c.tag not in KNOWN_INDI:
                    unread.append('L%d INDI.%s' % (c.line, c.tag))
            for n in r.all('NAME'):
                full, sur = _name(n.value)
                cs, quay = cites(n)
                C('person', rid, 'name', full, n, surname=sur, cites=cs, quay=quay)
            s = r.first('SEX')
            if s is not None:
                C('person', rid, 'sex', s.value, s)
            for tag, pred in (('BIRT', 'birth'), ('DEAT', 'death')):
                for ev in r.all(tag):
                    event('person', rid, pred, ev)
            for x in r.all('EXID'):
                t = x.first('TYPE')
                C('person', rid, 'exid', {'type': t.value if t else None, 'value': x.value}, x)
            for x in r.all('NOTE'):
                C('person', rid, 'note', x.value, x)
            for x in r.all('RESN'):
                C('person', rid, 'restriction', [w.strip() for w in (x.value or '').split(',') if w.strip()], x)
            for x in r.all('_LOOMID'):
                C('person', rid, 'loomid', x.value, x)
            for x in r.all('_BRANCH'):
                C('person', rid, 'branch', x.value, x)
            for x in r.all('FAMC'):
                pedi = x.first('PEDI'); stat = x.first('STAT')
                C('person', rid, 'famc', (x.ptr or '').strip('@'), x, pedigree=(pedi.value if pedi else None), stat=(stat.value if stat else None))
            for x in r.all('FAMS'):
                C('person', rid, 'fams', (x.ptr or '').strip('@'), x)
        elif r.tag == 'FAM':
            for c in r.children:
                if c.tag not in KNOWN_FAM:
                    unread.append('L%d FAM.%s' % (c.line, c.tag))
            for slot in ('HUSB', 'WIFE'):
                for x in r.all(slot):
                    if x.ptr and x.ptr != '@VOID@':
                        C('union', rid, 'partner', x.ptr.strip('@'), x, slot=slot)
            for x in r.all('CHIL'):
                if x.ptr and x.ptr != '@VOID@':
                    C('union', rid, 'child', x.ptr.strip('@'), x)
            for ev in r.all('MARR'):
                C('union', rid, 'marriage', True, ev)
                event('union', rid, 'marriage', ev)
            for ev in r.all('DIV'):
                C('union', rid, 'divorce', True, ev)
            for x in r.all('_LOOMID'):
                C('union', rid, 'loomid', x.value, x)
        elif r.tag == 'SOUR':
            t = r.first('TITL'); a = r.first('AUTH')
            C('source', rid, 'title', t.value if t else rid, r)
            if a is not None:
                C('source', rid, 'author', a.value, a)
        else:
            unread.append('L%d %s record' % (r.line, r.tag))
    return claims, {'version': v, 'records': len(records), 'unread': unread}


# ---------------- export ----------------
def _esc(v):
    return '@' + v if v.startswith('@') else v


def _lines(level, tag, value=None, xref=None, ptr=False):
    """One structure, its payload split on newlines into CONT lines. A pointer payload is written as is; text that
    starts with '@' is escaped as '@@' (GEDCOM 7 lineStr)."""
    head = '%d %s%s' % (level, (xref + ' ') if xref else '', tag)
    if ptr:
        if not POINTER.match(value or ''):
            raise GedcomError('not a pointer: %r' % value)
        return [head + ' ' + value]
    if value is None or value == '':
        return [head]
    parts = str(value).split('\n')
    out = [head + ' ' + _esc(parts[0])]
    out += ['%d CONT%s' % (level + 1, (' ' + _esc(p)) if p else '') for p in parts[1:]]
    return out


def export(graph, generator='loom-genealogy-ingest', gen_version='0.1.0'):
    """Canonical graph to GEDCOM 7 text. Persons are INDI, unions FAM (partners fill HUSB then WIFE in canonical order:
    GEDCOM 7 uses the two slots for partners of any sex), sources SOUR. Grades map to QUAY; the grade itself and the loom
    id ride in documented extension tags so a re-import is lossless for what the gate compares."""
    nodes = {n['id']: n for n in graph['nodes']}
    persons = [n for n in graph['nodes'] if n['cls'] == 'Person']
    unions = [n for n in graph['nodes'] if n['cls'] == 'Union']
    sources = graph.get('sources', [])
    claims = {c['id']: c for c in graph.get('claims', [])}
    px = {p['id']: 'I%d' % (k + 1) for k, p in enumerate(persons)}
    challenged = {}                                               # child -> unions of an alternative (contested) parent
    for e in graph.get('edges', []):
        if e['p'] == 'alt_parent':
            us = [u['id'] for u in unions if e['t'] in u['partners']]
            us.sort(key=lambda x: (len(next(u for u in unions if u['id'] == x)['partners']) != 1, x))   # prefer the parent's open union
            if us and us[0] not in challenged.setdefault(e['s'], []):
                challenged[e['s']].append(us[0])
    fx = {u['id']: 'F%d' % (k + 1) for k, u in enumerate(unions)}
    carriers = []                                                 # (fam xref, loom id, parent, child): a challenged link to a parent who has no open union
    for e in graph.get('edges', []):
        if e['p'] == 'alt_parent' and not any(len(u['partners']) == 1 and e['t'] in u['partners'] for u in unions):
            uid = 'union:%s/alt~%s~%s' % (e['t'].split(':', 1)[1].split('/')[0], e['s'].split('/', 1)[1], e['t'].split('/', 1)[1])
            if uid not in fx:
                fx[uid] = 'F%d' % (len(fx) + 1)
                carriers.append((fx[uid], uid, e['t'], e['s']))
            challenged[e['s']] = [x for x in challenged.get(e['s'], []) if not (x in [u['id'] for u in unions] and e['t'] in next(u for u in unions if u['id'] == x)['partners'])]
            if uid not in challenged[e['s']]:
                challenged[e['s']].append(uid)
    sx = {s['id']: 'S%d' % (k + 1) for k, s in enumerate(sources)}
    out = ['0 HEAD', '1 GEDC', '2 VERS 7.0', '1 SCHMA']
    out += ['2 TAG %s %s' % (t, u) for t, u in sorted(EXT_TAGS.items())]
    out += ['1 SOUR ' + generator, '2 VERS ' + gen_version]
    out += _lines(1, 'NOTE', 'Generated from the loom canonical genealogy graph. Grades map to QUAY (Confirmed 3, Likely 2, Suspected 1); the grade itself is in _GRADE.')

    def cite(level, claim_ids):
        res = []
        for cid in claim_ids or []:
            c = claims.get(cid)
            if not c or c['source'] not in sx:
                continue
            res += _lines(level, 'SOUR', '@%s@' % sx[c['source']], ptr=True)
            res += _lines(level + 1, 'PAGE', c['locator'])
            if c['grade'] in QUAY_OF_GRADE:
                res += _lines(level + 1, 'QUAY', QUAY_OF_GRADE[c['grade']])
            res += _lines(level + 1, '_GRADE', c['grade'])
        return res

    for s in sources:
        out += _lines(0, 'SOUR', None, '@%s@' % sx[s['id']])
        out += _lines(1, 'TITL', s['title'])
        if s.get('sha256'):
            out += _lines(1, '_SHA256', s['sha256'])
        out += _lines(1, '_LOOMID', s['id'])
    for p in persons:
        out += _lines(0, 'INDI', None, '@%s@' % px[p['id']])
        for nm in p.get('names', []):
            out += _lines(1, 'NAME', nm['value'])
            out += cite(2, nm.get('claims', [])[:1])
        if not p.get('names') and p.get('vis') == 'redacted':        # a public-candidate placeholder
            out += _lines(1, 'NAME', 'Withheld' if p.get('label') == 'Withheld record' else 'Living')
        if p.get('restrictions'):
            out += _lines(1, 'RESN', ', '.join(p['restrictions']))
        if (p.get('sex') or {}).get('value'):                          # unstated stays unstated: SEX U would assert 'undetermined'
            out += _lines(1, 'SEX', p['sex']['value'])
        for ev, tag in (('birth', 'BIRT'), ('death', 'DEAT')):
            f = (p.get('facts') or {}).get(ev)
            if f and f.get('date'):
                out += _lines(1, tag)
                if f['date'].get('gedcom'):
                    out += _lines(2, 'DATE', f['date']['gedcom'])
                if f['date'].get('phrase'):
                    out += _lines(3, 'PHRASE', f['date']['phrase'])
                if f.get('place') and f['place'] in nodes:
                    pl = nodes[f['place']]
                    out += _lines(2, 'PLAC', pl['label'])
                    if pl.get('geo'):
                        out += _lines(3, 'MAP')
                        lat, lon = pl['geo']['lat'], pl['geo']['lon']
                        out += _lines(4, 'LATI', ('N' if lat >= 0 else 'S') + ('%g' % abs(lat)))
                        out += _lines(4, 'LONG', ('E' if lon >= 0 else 'W') + ('%g' % abs(lon)))
                out += cite(2, f.get('claims', [])[:2])
                for alt in f.get('alternatives', []):          # competing values: repeated structures, the first is the preferred one
                    out += _lines(1, tag) + _lines(2, 'DATE', alt['date']['gedcom']) + cite(2, alt['claims'][:2])
            elif f and f.get('status') == 'occurred':
                out += _lines(1, tag, 'Y')
        ids = p.get('ids') or {}
        if ids.get('wikidata'):
            out += _lines(1, 'EXID', ids['wikidata']) + _lines(2, 'TYPE', EXID_WIKIDATA)
        if ids.get('enwiki'):
            out += _lines(1, 'EXID', ids['enwiki']) + _lines(2, 'TYPE', EXID_ENWIKI)
        for x in ids.get('other', []):
            out += _lines(1, 'EXID', x['value']) + (_lines(2, 'TYPE', x['type']) if x.get('type') else [])
        for note in p.get('notes', []):
            out += _lines(1, 'NOTE', note['text'])
        if p.get('branch') and p['branch'] in nodes:
            out += _lines(1, '_BRANCH', nodes[p['branch']]['label'])
        out += _lines(1, '_LOOMID', p['id'])
        if p.get('grade'):
            out += _lines(1, '_GRADE', p['grade'])
        for u in unions:
            if p['id'] in u['children']:
                out += _lines(1, 'FAMC', '@%s@' % fx[u['id']], ptr=True)
                ped = (u.get('pedigree') or {}).get(p['id'], 'BIRTH')
                if ped != 'BIRTH':
                    out += _lines(2, 'PEDI', ped)
        for uid in challenged.get(p['id'], []):                   # a contested parent link: GEDCOM 7 FAMC.STAT CHALLENGED
            out += _lines(1, 'FAMC', '@%s@' % fx[uid], ptr=True) + _lines(2, 'STAT', 'CHALLENGED')
        for u in unions:
            if p['id'] in u['partners']:
                out += _lines(1, 'FAMS', '@%s@' % fx[u['id']], ptr=True)
    for xref, uid, par, ch in carriers:                          # one-parent FAM that only carries a challenged link (_LOOMID alt~...)
        out += _lines(0, 'FAM', None, '@%s@' % xref) + _lines(1, 'HUSB', '@%s@' % px[par], ptr=True) + _lines(1, 'CHIL', '@%s@' % px[ch], ptr=True) + _lines(1, '_LOOMID', uid)
    for u in unions:
        out += _lines(0, 'FAM', None, '@%s@' % fx[u['id']])
        for slot, pid in zip(('HUSB', 'WIFE'), u['partners']):
            out += _lines(1, slot, '@%s@' % px[pid], ptr=True)
        for c in u['children'] + [x for x, us in challenged.items() if u['id'] in us and x not in u['children']]:
            out += _lines(1, 'CHIL', '@%s@' % px[c], ptr=True)
        if u.get('type') == 'marriage':
            sub = []
            if u.get('marriage_date'):
                sub += _lines(2, 'DATE', u['marriage_date']['gedcom'])
                if u['marriage_date'].get('phrase'):
                    sub += _lines(3, 'PHRASE', u['marriage_date']['phrase'])
            if u.get('marriage_place') and u['marriage_place'] in nodes:
                sub += _lines(2, 'PLAC', nodes[u['marriage_place']]['label'])
            sub += cite(2, [c for c in u.get('claims', []) if c in claims and claims[c]['predicate'] in ('spouse', 'marriage')][:2])
            out += _lines(1, 'MARR', None if sub else 'Y') + sub      # Y only when nothing else is known
        out += _lines(1, '_LOOMID', u['id'])
    out.append('0 TRLR')
    return '\n'.join(out) + '\n'
