"""Read a JavaScript / TypeScript object literal as data. Nothing is evaluated.

The Cosmos app keeps family data in three forms: JSON trees, a TypeScript module (`export const familyData: Record<...> = {...}`)
and an object literal inside two standalone HTML pages (`const familyData = {...}`). This module finds the literal by its
variable name and parses it with a small recursive-descent reader that accepts only data: objects (quoted or bare keys),
arrays, strings, numbers, true/false/null/undefined, comments and trailing commas. Anything else (a call, a spread, an
identifier, a template literal with ${}) is refused with the line number, so code in the file can never run or leak in.

Each parsed value also gets a locator: the 1-based line where it starts, keyed by its path, for per-fact evidence.
"""
import re

NUM = re.compile(r'-?(?:0|[1-9][0-9_]*)(?:\.[0-9_]+)?(?:[eE][+-]?[0-9]+)?')
IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
ESC = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0', '\\': '\\', "'": "'", '"': '"', '`': '`', '\n': ''}


class JSDataError(ValueError):
    pass


class _Reader:
    def __init__(self, text, pos):
        self.s, self.i, self.n = text, pos, len(text)
        self.nl = [m.start() for m in re.finditer('\n', text)]   # newline offsets, for line numbers by bisection
        self.locs = {}

    def line(self, at=None):
        import bisect
        return bisect.bisect_left(self.nl, self.i if at is None else at) + 1

    def fail(self, msg):
        raise JSDataError('%s at line %d' % (msg, self.line()))

    def ws(self):
        while self.i < self.n:
            c = self.s[self.i]
            if c in ' \t\r\n﻿ ':
                self.i += 1
            elif self.s.startswith('//', self.i):
                j = self.s.find('\n', self.i)
                self.i = self.n if j < 0 else j + 1
            elif self.s.startswith('/*', self.i):
                j = self.s.find('*/', self.i + 2)
                if j < 0:
                    self.fail('unterminated comment')
                self.i = j + 2
            else:
                break

    def value(self, path):
        self.ws()
        if self.i >= self.n:
            self.fail('unexpected end of input')
        self.locs[path] = self.line()
        c = self.s[self.i]
        if c == '{':
            return self.obj(path)
        if c == '[':
            return self.arr(path)
        if c in '"\'':
            return self.string(c)
        if c == '`':
            v = self.string('`')
            if '${' in v:
                self.fail('template literal with substitution refused')
            return v
        m = NUM.match(self.s, self.i)
        if m and (c.isdigit() or c == '-'):
            self.i = m.end()
            t = m.group(0).replace('_', '')
            return float(t) if any(x in t for x in '.eE') else int(t)
        m = IDENT.match(self.s, self.i)
        if m:
            word = m.group(0)
            if word in ('true', 'false'):
                self.i = m.end(); return word == 'true'
            if word in ('null', 'undefined'):
                self.i = m.end(); return None
            self.fail('identifier %r is code, not data; refused' % word)
        self.fail('unexpected character %r' % c)

    def string(self, q):
        self.i += 1
        out = []
        while self.i < self.n:
            c = self.s[self.i]
            if c == q:
                self.i += 1
                return ''.join(out)
            if c == '\\':
                nx = self.s[self.i + 1:self.i + 2]
                if nx == 'u':
                    h = self.s[self.i + 2:self.i + 6]
                    if not re.fullmatch(r'[0-9a-fA-F]{4}', h):
                        self.fail('bad \\u escape')
                    out.append(chr(int(h, 16))); self.i += 6; continue
                if nx == 'x':
                    h = self.s[self.i + 2:self.i + 4]
                    out.append(chr(int(h, 16))); self.i += 4; continue
                out.append(ESC.get(nx, nx)); self.i += 2; continue
            if c == '\n' and q != '`':
                self.fail('newline in string')
            out.append(c); self.i += 1
        self.fail('unterminated string')

    def key(self):
        self.ws()
        c = self.s[self.i:self.i + 1]
        if c in ('"', "'"):
            return self.string(c)
        m = IDENT.match(self.s, self.i)
        if m:
            self.i = m.end(); return m.group(0)
        m = NUM.match(self.s, self.i)
        if m:
            self.i = m.end(); return m.group(0)
        if c == '[':
            self.fail('computed key refused')
        if self.s.startswith('...', self.i):
            self.fail('spread refused')
        self.fail('bad key')

    def obj(self, path):
        self.i += 1
        out = {}
        while True:
            self.ws()
            if self.s[self.i:self.i + 1] == '}':
                self.i += 1; return out
            k = self.key()
            self.ws()
            if self.s[self.i:self.i + 1] != ':':
                self.fail('expected ":" after key %r (shorthand properties are code)' % k)
            self.i += 1
            if k in out:
                self.fail('duplicate key %r' % k)
            out[k] = self.value(path + (k,))
            self.ws()
            c = self.s[self.i:self.i + 1]
            if c == ',':
                self.i += 1
            elif c == '}':
                self.i += 1; return out
            else:
                self.fail('expected "," or "}"')

    def arr(self, path):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.s[self.i:self.i + 1] == ']':
                self.i += 1; return out
            out.append(self.value(path + (len(out),)))
            self.ws()
            c = self.s[self.i:self.i + 1]
            if c == ',':
                self.i += 1
            elif c == ']':
                self.i += 1; return out
            else:
                self.fail('expected "," or "]"')


def find_literal(text, var):
    """Return (value, locs, start_line) for `[export] const|let|var <var>[: Type] = <literal>`. Exactly one binding must exist."""
    pat = re.compile(r'(?:export\s+)?(?:const|let|var)\s+' + re.escape(var) + r'\s*(?::\s*[^=;]+?)?=\s*')
    hits = list(pat.finditer(text))
    if len(hits) != 1:
        raise JSDataError('expected exactly one binding of %r, found %d' % (var, len(hits)))
    r = _Reader(text, hits[0].end())
    v = r.value(())
    return v, r.locs, r.line(hits[0].start())


def line_text(text, line):
    """The verbatim source line (1-based), stripped: the evidence quote for a locator."""
    lines = text.split('\n')
    return lines[line - 1].strip() if 0 < line <= len(lines) else ''
