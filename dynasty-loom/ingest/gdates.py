"""Genealogical dates: one canonical shape, read from and written to GEDCOM 7, EDTF (ISO 8601-2) and GEDCOM X formal dates.

Canonical date (a dict, JSON-ready):
  kind       exact | approx | before | after | between | period | phrase
  qualifier  ABT | CAL | EST (approx only)
  calendar   GREGORIAN | JULIAN | HEBREW | FRENCH_R
  start/end  {y, m, d, bce}: what the source said, in its own calendar (end only for between / period)
  precision  year | month | day (of start)
  phrase     free text (GEDCOM 7 PHRASE), kept verbatim
  earliest / latest   proleptic Gregorian ISO bounds, the window the event lies in (None = open); used by the gates,
                      the timeline filter and the sort. Approximate windows are a policy (APPROX_YEARS), not a standard.
  gedcom / edtf / gedcomx   the same value in each external syntax

A year-only integer from the Cosmos JSON becomes kind=exact, precision=year, window 1 Jan to 31 Dec of that year.
"""
import re

CALENDARS = ('GREGORIAN', 'JULIAN', 'HEBREW', 'FRENCH_R')
MONTHS = {
    'GREGORIAN': ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
    'JULIAN': ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
    'HEBREW': ['TSH', 'CSH', 'KSL', 'TVT', 'SHV', 'ADR', 'ADS', 'NSN', 'IYR', 'SVN', 'TMZ', 'AAV', 'ELL'],
    'FRENCH_R': ['VEND', 'BRUM', 'FRIM', 'NIVO', 'PLUV', 'VENT', 'GERM', 'FLOR', 'PRAI', 'MESS', 'THER', 'FRUC', 'COMP'],
}
APPROX_YEARS = {'ABT': 5, 'EST': 5, 'CAL': 1}      # policy: the window an approximate date is allowed to move in


class DateError(ValueError):
    pass


# ---------- calendar arithmetic (Julian day numbers; astronomical years, 1 BCE = 0) ----------
def _jdn(y, m, d, julian=False):
    a = (14 - m) // 12; y2 = y + 4800 - a; m2 = m + 12 * a - 3
    base = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4
    return base - 32083 if julian else base - y2 // 100 + y2 // 400 - 32045


def _greg(j):
    a = j + 32044; b = (4 * a + 3) // 146097; c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461; e = c - 1461 * d // 4; m = (5 * e + 2) // 153
    return 100 * b + d - 4800 + m // 10, m + 3 - 12 * (m // 10), e - (153 * m + 2) // 5 + 1


def _leap(y, julian):
    return y % 4 == 0 if julian else (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))


def _mdays(y, m, julian):
    return [31, 29 if _leap(y, julian) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]


def _iso(y, m, d):
    ys = ('-%04d' % -y) if y < 0 else ('%04d' % y if y <= 9999 else '+%d' % y)
    return '%s-%02d-%02d' % (ys, m, d)


def _astro(p):
    return 1 - p['y'] if p.get('bce') else p['y']


def _bounds(p, cal):
    """(earliest, latest) ISO Gregorian strings for one date part, or (None, None) for calendars not converted here."""
    if cal not in ('GREGORIAN', 'JULIAN'):
        return None, None
    jl = cal == 'JULIAN'; y = _astro(p)
    m0, m1 = (p['m'], p['m']) if p.get('m') else (1, 12)
    d0 = p['d'] if p.get('d') else 1
    d1 = p['d'] if p.get('d') else _mdays(y, m1, jl)
    lo = _greg(_jdn(y, m0, d0, jl)); hi = _greg(_jdn(y, m1, d1, jl))
    return _iso(*lo), _iso(*hi)


def _shift_year(iso, dy):
    if iso is None:
        return None
    neg = iso.startswith('-'); body = iso[1:] if neg or iso.startswith('+') else iso
    y, m, d = body.split('-'); y = (-int(y) if neg else int(y)) + dy
    if m == '02' and d == '29' and not _leap(y, False):
        d = '28'
    return _iso(y, int(m), int(d))


def precision(p):
    return 'day' if p.get('d') else ('month' if p.get('m') else 'year')


# ---------- construction ----------
def from_year(y):
    """A bare year integer (the Cosmos `born` / `died` fields)."""
    if not isinstance(y, int) or isinstance(y, bool):
        raise DateError('year must be an integer, got %r' % (y,))
    return finish({'kind': 'exact', 'calendar': 'GREGORIAN', 'start': {'y': y, 'm': None, 'd': None, 'bce': False}})


def finish(c):
    """Fill precision, bounds and the three external spellings from kind/calendar/start/end."""
    c.setdefault('qualifier', None); c.setdefault('end', None); c.setdefault('phrase', None); c.setdefault('calendar', 'GREGORIAN')
    k, cal, s, e = c['kind'], c['calendar'], c.get('start'), c.get('end')
    c['precision'] = precision(s) if s else None
    lo = hi = None
    if s:
        lo, hi = _bounds(s, cal)
    if k == 'approx':
        w = APPROX_YEARS.get(c['qualifier'], 5); lo, hi = _shift_year(lo, -w), _shift_year(hi, w)
    elif k == 'before':
        lo = None
    elif k == 'after':
        hi = None
    elif k == 'period' and c.get('open_end'):
        hi = None
    elif k in ('between', 'period') and e:
        hi = _bounds(e, c.get('end_calendar', cal))[1]
        if k == 'period' and c.get('open_start'):
            lo = None
    elif k == 'phrase':
        lo = hi = None
    c['earliest'], c['latest'] = lo, hi
    c['gedcom'] = to_gedcom(c); c['edtf'] = to_edtf(c); c['gedcomx'] = to_gedcomx(c)
    return c


# ---------- GEDCOM 7 ----------
def _part(tokens, cal_hint=None):
    t = list(tokens)
    if not t:
        raise DateError('empty date')
    cal = 'GREGORIAN'
    if t[0] in CALENDARS:
        cal = t.pop(0)
    elif t[0].startswith('_'):
        raise DateError('extension calendar %s not supported' % t[0])
    bce = False
    if t and t[-1] == 'BCE':
        bce = True; t.pop()
    if not t or not re.fullmatch(r'\d+', t[-1]):
        raise DateError('year missing in %r' % ' '.join(tokens))
    y = int(t.pop()); m = d = None
    if t:
        mon = t.pop()
        if mon not in MONTHS[cal]:
            raise DateError('month %r not in calendar %s' % (mon, cal))
        m = MONTHS[cal].index(mon) + 1
    if t:
        if not re.fullmatch(r'\d{1,2}', t[-1]):
            raise DateError('bad day %r' % t[-1])
        d = int(t.pop())
    if t:
        raise DateError('unparsed tokens %r' % t)
    if bce and cal not in ('GREGORIAN', 'JULIAN'):
        raise DateError('BCE only with Gregorian or Julian')
    return cal, {'y': y, 'm': m, 'd': d, 'bce': bce}


def parse_gedcom(value, phrase=None):
    """GEDCOM 7 DateValue (with an optional PHRASE) to the canonical shape. Raises DateError on anything outside the grammar."""
    v = (value or '').strip(); t = v.split()
    if not t:
        if phrase:
            return finish({'kind': 'phrase', 'phrase': phrase, 'start': None})
        raise DateError('empty date without PHRASE')
    c = {'phrase': phrase}
    if t[0] in APPROX_YEARS:
        c['kind'] = 'approx'; c['qualifier'] = t[0]; c['calendar'], c['start'] = _part(t[1:])
    elif t[0] in ('BEF', 'AFT'):
        c['kind'] = 'before' if t[0] == 'BEF' else 'after'; c['calendar'], c['start'] = _part(t[1:])
    elif t[0] == 'BET':
        if 'AND' not in t:
            raise DateError('BET without AND')
        k = t.index('AND'); c['kind'] = 'between'
        c['calendar'], c['start'] = _part(t[1:k]); cal2, c['end'] = _part(t[k + 1:])
        if cal2 != c['calendar']:
            c['end_calendar'] = cal2
    elif t[0] == 'FROM':
        c['kind'] = 'period'
        if 'TO' in t:
            k = t.index('TO'); c['calendar'], c['start'] = _part(t[1:k]); _, c['end'] = _part(t[k + 1:])
        else:
            c['calendar'], c['start'] = _part(t[1:]); c['open_end'] = True
    elif t[0] == 'TO':
        c['kind'] = 'period'; c['open_start'] = True; c['calendar'], s = _part(t[1:]); c['start'] = s; c['end'] = s
    else:
        c['kind'] = 'exact'; c['calendar'], c['start'] = _part(t)
    return finish(c)


def _gpart(p, cal):
    out = []
    if cal != 'GREGORIAN':
        out.append(cal)
    if p.get('d'):
        out.append(str(p['d']))
    if p.get('m'):
        out.append(MONTHS[cal][p['m'] - 1])
    out.append(str(p['y']))
    if p.get('bce'):
        out.append('BCE')
    return ' '.join(out)


def to_gedcom(c):
    k, cal = c['kind'], c.get('calendar', 'GREGORIAN')
    if k == 'phrase':
        return ''
    s = _gpart(c['start'], cal)
    if k == 'exact':
        return s
    if k == 'approx':
        return '%s %s' % (c['qualifier'], s)
    if k == 'before':
        return 'BEF ' + s
    if k == 'after':
        return 'AFT ' + s
    if k == 'between':
        return 'BET %s AND %s' % (s, _gpart(c['end'], c.get('end_calendar', cal)))
    if k == 'period':
        if c.get('open_start'):
            return 'TO ' + _gpart(c['end'], cal)
        if c.get('open_end'):
            return 'FROM ' + s
        return 'FROM %s TO %s' % (s, _gpart(c['end'], cal))
    raise DateError(k)


# ---------- EDTF and GEDCOM X ----------
def _epart(p, cal):
    if cal not in ('GREGORIAN', 'JULIAN'):
        return None
    y = _astro(p)
    if cal == 'JULIAN' and p.get('d'):          # EDTF is proleptic Gregorian: convert day-precise Julian dates
        y, m, d = _greg(_jdn(y, p['m'], p['d'], True)); return _iso(y, m, d)
    ys = ('-%04d' % -y) if y < 0 else '%04d' % y
    return ys + ('-%02d' % p['m'] if p.get('m') else '') + ('-%02d' % p['d'] if p.get('d') else '')


def to_edtf(c):
    k, cal = c['kind'], c.get('calendar', 'GREGORIAN')
    if k == 'phrase':
        return None
    s = _epart(c['start'], cal)
    if s is None:
        return None
    if k == 'exact':
        return s
    if k == 'approx':
        return s + '~'
    if k == 'before':
        return '[..%s]' % s
    if k == 'after':
        return '[%s..]' % s
    e = _epart(c['end'], c.get('end_calendar', cal)) if c.get('end') else None
    if k == 'between':
        return '[%s..%s]' % (s, e)
    if k == 'period':
        if c.get('open_start'):
            return '../' + e
        if c.get('open_end'):
            return s + '/..'
        return '%s/%s' % (s, e)
    return None


def _xpart(p, cal):
    e = _epart(p, cal)
    if e is None:
        return None
    return e if e.startswith('-') else '+' + e


def to_gedcomx(c):
    k, cal = c['kind'], c.get('calendar', 'GREGORIAN')
    if k == 'phrase':
        return None
    s = _xpart(c['start'], cal)
    if s is None:
        return None
    if k == 'exact':
        return s
    if k == 'approx':
        return 'A' + s
    if k == 'before':
        return '/' + s
    if k == 'after':
        return s + '/'
    e = _xpart(c['end'], c.get('end_calendar', cal)) if c.get('end') else None
    if k in ('between', 'period'):
        if c.get('open_start'):
            return '/' + e
        if c.get('open_end'):
            return s + '/'
        return '%s/%s' % (s, e)
    return None


def year_bounds(c):
    """(earliest_year, latest_year) as ints or None; for the plausibility gates."""
    def y(iso):
        if iso is None:
            return None
        neg = iso.startswith('-'); body = iso.lstrip('+-')
        v = int(body.split('-')[0]); return -v if neg else v
    return (y(c.get('earliest')), y(c.get('latest'))) if c else (None, None)
