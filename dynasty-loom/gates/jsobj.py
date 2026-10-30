"""Read a JavaScript / TypeScript object literal as data, without executing anything.

The genealogy sources keep their people in three shapes: JSON trees, a TS module (`export const familyData: Record<...> = {...}`)
and older HTML pages with `const familyData = {...}` inline. This module finds the literal by name, brace-matches it
(string- and comment-aware) and parses it with a small recursive-descent reader. Anything that is not plain data
(a call, a spread, a template with ${}) is a ParseError with a line number: the gate reports it, it never evaluates it.

Duplicate keys are recorded instead of silently overwritten, because JS keeps the last one and the app then shows
one person where the file holds two (gate D07a)."""
import re


class ParseError(ValueError):
    pass


class Obj(dict):
    """A dict that remembers duplicate keys (key, line of the second occurrence) and the line of each key."""
    def __init__(self):
        super().__init__(); self.dups = []; self.lines = {}


_ID = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
_NUM = re.compile(r'-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)')


class _Reader:
    def __init__(self, text, base_line=1):
        self.t, self.i, self.base = text, 0, base_line

    def line(self, i=None):
        return self.base + self.t.count('\n', 0, self.i if i is None else i)

    def err(self, msg):
        raise ParseError('%s at line %d: %r' % (msg, self.line(), self.t[self.i:self.i + 40]))

    def ws(self):
        t = self.t
        while self.i < len(t):
            c = t[self.i]
            if c in ' \t\r\n﻿':
                self.i += 1
            elif t.startswith('//', self.i):
                j = t.find('\n', self.i); self.i = len(t) if j < 0 else j + 1
            elif t.startswith('/*', self.i):
                j = t.find('*/', self.i + 2)
                if j < 0: self.err('unterminated comment')
                self.i = j + 2
            else:
                break

    def string(self):
        q = self.t[self.i]; self.i += 1; out = []
        while True:
            if self.i >= len(self.t): self.err('unterminated string')
            c = self.t[self.i]
            if c == q:
                self.i += 1; return ''.join(out)
            if q == '`' and self.t.startswith('${', self.i): self.err('template expression (code, not data)')
            if c == '\\':
                n = self.t[self.i + 1]; self.i += 2
                if n == 'u':
                    out.append(chr(int(self.t[self.i:self.i + 4], 16))); self.i += 4
                elif n == 'x':
                    out.append(chr(int(self.t[self.i:self.i + 2], 16))); self.i += 2
                else:
                    out.append({'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', '0': '\0', '\n': ''}.get(n, n))
                continue
            if c == '\n' and q != '`': self.err('newline in string')
            out.append(c); self.i += 1

    def value(self):
        self.ws()
        if self.i >= len(self.t): self.err('unexpected end')
        c = self.t[self.i]
        if c == '{': return self.obj()
        if c == '[': return self.arr()
        if c in '"\'`': return self.string()
        m = _NUM.match(self.t, self.i)
        if m and (c.isdigit() or c in '-.'):
            self.i = m.end(); s = m.group(0)
            if s.lower().startswith(('0x', '-0x')): return int(s, 16)
            return float(s) if any(ch in s for ch in '.eE') else int(s)
        m = _ID.match(self.t, self.i)
        if m:
            w = m.group(0)
            if w in ('true', 'false', 'null', 'undefined'):
                self.i = m.end(); return {'true': True, 'false': False, 'null': None, 'undefined': None}[w]
            self.err('identifier %r (code, not data)' % w)
        self.err('unexpected character')

    def key(self):
        self.ws(); c = self.t[self.i]
        if c in '"\'': return self.string()
        if c == '[': self.err('computed key (code, not data)')
        m = _ID.match(self.t, self.i) or re.compile(r'\d+').match(self.t, self.i)
        if not m: self.err('bad key')
        self.i = m.end(); return m.group(0)

    def obj(self):
        o = Obj(); self.i += 1
        while True:
            self.ws()
            if self.t[self.i] == '}': self.i += 1; return o
            if self.t.startswith('...', self.i): self.err('spread (code, not data)')
            kline = self.line(); k = self.key(); self.ws()
            if self.t[self.i] != ':': self.err("expected ':' after key %r" % k)
            self.i += 1; v = self.value()
            if k in o: o.dups.append((k, kline))
            o[k] = v; o.lines.setdefault(k, kline)
            self.ws()
            if self.t[self.i] == ',': self.i += 1
            elif self.t[self.i] != '}': self.err("expected ',' or '}'")

    def arr(self):
        a = []; self.i += 1
        while True:
            self.ws()
            if self.t[self.i] == ']': self.i += 1; return a
            a.append(self.value()); self.ws()
            if self.t[self.i] == ',': self.i += 1
            elif self.t[self.i] != ']': self.err("expected ',' or ']'")


def _match_brace(text, start):
    """index just past the '}' that closes text[start] == '{', skipping strings and comments"""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c in '"\'`':
            q = c; i += 1
            while i < n and text[i] != q:
                i += 2 if text[i] == '\\' else 1
        elif text.startswith('//', i):
            j = text.find('\n', i); i = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2); i = n if j < 0 else j + 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise ParseError('unbalanced braces from offset %d' % start)


def find_literal(text, name):
    """(literal_text, first_line) for `const|let|var|export const NAME[: Type] = { ... }`, or None"""
    m = re.search(r'(?:export\s+)?(?:const|let|var)\s+%s\s*(?::[^=]+)?=\s*\{' % re.escape(name), text)
    if not m: return None
    s = m.end() - 1
    return text[s:_match_brace(text, s)], text.count('\n', 0, s) + 1


def parse_literal(text, base_line=1):
    r = _Reader(text, base_line); v = r.value(); r.ws()
    if r.i != len(r.t): r.err('trailing text')
    return v


def iter_dups(v, path='$'):
    """every duplicate key anywhere in a parsed value: (json-path, key, line)"""
    if isinstance(v, Obj):
        for k, ln in v.dups: yield path, k, ln
        for k, x in v.items(): yield from iter_dups(x, path + '.' + k)
    elif isinstance(v, list):
        for i, x in enumerate(v): yield from iter_dups(x, '%s[%d]' % (path, i))
