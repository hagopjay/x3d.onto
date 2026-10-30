"""Topology of a family graph: order, generation, kinship, inbreeding, pedigree collapse.

Inputs are plain dicts so the module has no opinion about storage:
  parents_of[child] = [parent, ...]      accepted parent links only (0, 1 or 2 known parents; an unknown parent is simply absent)
  partners_of[p]    = [partner, ...]     known partners from union nodes

Everything is exact (fractions.Fraction). A missing parent is treated as an unrelated founder, so every kinship and
inbreeding value computed from an incomplete pedigree is a LOWER BOUND; `pedigree()` reports how complete it is.
"""
from collections import Counter
from fractions import Fraction

HALF = Fraction(1, 2)


class CycleError(ValueError):
    pass


def topo_order(ids, parents_of):
    """Parents before children (Kahn), ties broken by id so the order is deterministic. Raises CycleError on a loop."""
    ids = sorted(ids)
    kids = {i: [] for i in ids}
    indeg = {i: 0 for i in ids}
    for c in ids:
        for p in parents_of.get(c, []):
            if p in kids:
                kids[p].append(c); indeg[c] += 1
    ready = sorted(i for i in ids if indeg[i] == 0)
    out = []
    while ready:
        x = ready.pop(0); out.append(x)
        for c in sorted(kids[x]):
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(c); ready.sort()
    if len(out) != len(ids):
        raise CycleError('parent links form a cycle among: %s' % ', '.join(sorted(set(ids) - set(out))))
    return out


def generation_ranges(ids, parents_of, partners_of, children_of=None):
    """Generation from topology, as a range. Founders are 1; a child is 1 + its parents' generations, so with pedigree
    collapse (an uncle marrying his niece) the two parents give two answers: min and max are both kept. A person with no
    parents who partners a descendant (married in) takes that partner's range ('partner-aligned')."""
    children_of = children_of or {}
    memo = {}

    def g(x, stack):
        if x in memo:
            return memo[x]
        if x in stack:
            return None
        stack = stack | {x}
        ps = [p for p in parents_of.get(x, []) if p in ids]
        res = None
        if ps:
            rs = [r for r in (g(p, stack) for p in ps) if r]
            if rs:
                res = {'min': 1 + min(r['min'] for r in rs), 'max': 1 + max(r['max'] for r in rs), 'method': 'descent'}
        else:
            linked = sorted(q for q in partners_of.get(x, []) if q in ids and parents_of.get(q))
            if linked:
                rs = [r for r in (g(q, stack) for q in linked) if r]
                if rs:
                    res = {'min': min(r['min'] for r in rs), 'max': max(r['max'] for r in rs), 'method': 'partner-aligned', 'via': linked}
            if res is None:
                has_family = bool(partners_of.get(x)) or bool(children_of.get(x))
                res = {'min': 1, 'max': 1, 'method': 'founder' if has_family else 'isolated'}
        memo[x] = res
        return res

    return {i: g(i, frozenset()) for i in sorted(ids)}


class Kinship:
    """Malecot kinship coefficient phi(a, b) by the recursive (Karigl) method over a topological order."""

    def __init__(self, ids, parents_of):
        self.order = topo_order(ids, parents_of)
        self.idx = {x: k for k, x in enumerate(self.order)}
        self.par = {x: [p for p in parents_of.get(x, []) if p in self.idx] for x in self.order}
        self.memo = {}

    def phi(self, a, b):
        if a is None or b is None:
            return Fraction(0)
        key = (a, b) if a <= b else (b, a)
        if key in self.memo:
            return self.memo[key]
        if a == b:
            ps = self.par[a]
            v = HALF * (1 + (self.phi(ps[0], ps[1]) if len(ps) == 2 else 0))
        else:
            if self.idx[a] < self.idx[b]:
                a, b = b, a                       # expand the later one: it cannot be an ancestor of the other
            v = sum((HALF * self.phi(p, b) for p in self.par[a]), Fraction(0))
        self.memo[key] = v
        return v

    def inbreeding(self, x):
        ps = self.par[x]
        return self.phi(ps[0], ps[1]) if len(ps) == 2 else Fraction(0)


def ancestor_depths(x, parents_of):
    """{ancestor: Counter(depth -> number of distinct paths)} for every ancestor of x (x itself at depth 0)."""
    out = {x: Counter({0: 1})}
    level = Counter({x: 1}); d = 0
    while level:
        d += 1; nxt = Counter()
        for p, n in level.items():
            for q in parents_of.get(p, []):
                nxt[q] += n
        for q, n in nxt.items():
            out.setdefault(q, Counter())[d] += n
        level = nxt
        if d > 200:
            raise CycleError('ancestry deeper than 200: cycle?')
    return out


def _ordinal(n):
    return {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth'}.get(n, '%dth' % n)


def _times(n):
    return {1: 'once', 2: 'twice', 3: 'three times'}.get(n, '%d times' % n)


def relationship_name(n1, n2):
    lo, hi = sorted((n1, n2))
    if lo == 0:
        return 'direct line (%d generation%s apart)' % (hi, '' if hi == 1 else 's')
    if lo == 1 and hi == 1:
        return 'siblings'
    if lo == 1:
        return '%suncle/aunt and %snephew/niece (avuncular)' % ('great-' * (hi - 2), 'great-' * (hi - 2))
    s = '%s cousins' % _ordinal(lo - 1)
    return s + (' %s removed' % _times(hi - lo) if hi > lo else '')


def explain(a, b, parents_of, partners_of, kin):
    """Why phi(a, b) is what it is: the nearest common ancestors, their path lengths and Wright's terms.
    Nearest = a common ancestor none of whose descendants on the way down is also a common ancestor."""
    da, db = ancestor_depths(a, parents_of), ancestor_depths(b, parents_of)
    common = set(da) & set(db)
    if not common:
        return {'related': False, 'phi': '0', 'phi_float': 0.0, 'common_ancestors': [], 'relationship': None}
    anc_of = {c: set(ancestor_depths(c, parents_of)) - {c} for c in common}
    nearest = sorted(c for c in common if not any(c in anc_of[o] for o in common if o != c))
    rows = []
    for c in nearest:
        n1 = min(da[c]); n2 = min(db[c])
        term = sum((HALF ** (i + j + 1) * da[c][i] * db[c][j] * (1 + kin.inbreeding(c)) for i in da[c] for j in db[c]), Fraction(0))
        rows.append({'ancestor': c, 'n1': n1, 'n2': n2, 'paths_a': sum(da[c].values()), 'paths_b': sum(db[c].values()), 'wright_term': str(term)})
    # full vs half: a nearest ancestor whose known partner is also a nearest ancestor at the same distances
    best = min(rows, key=lambda r: (r['n1'] + r['n2'], r['n1'], r['ancestor']))
    pair = [r for r in rows if (r['n1'], r['n2']) == (best['n1'], best['n2'])]
    names = {r['ancestor'] for r in pair}
    full = any(q in names for r in pair for q in partners_of.get(r['ancestor'], []))
    unknown_other = any(not partners_of.get(r['ancestor']) for r in pair)
    rel = relationship_name(best['n1'], best['n2'])
    if best['n1'] and best['n2'] and not full:
        rel = ('half-' if not unknown_other else 'half- or full (other ancestor unknown) ') + rel
    phi = kin.phi(a, b)
    return {'related': True, 'phi': str(phi), 'phi_float': float(phi), 'relationship': rel, 'full': full,
            'common_ancestors': rows, 'wright_sum_nearest': str(sum((Fraction(r['wright_term']) for r in rows), Fraction(0))),
            'note': 'Wright terms over the nearest common ancestors; phi itself is the exact recursive value and is a lower bound when ancestors are missing.'}


def pedigree(x, parents_of, max_depth=12):
    """Pedigree completeness and collapse ('implex') for x: per depth the 2^d slots, how many are filled (with
    multiplicity), how many distinct people fill them; implex = 1 - distinct ancestors / filled slots over all depths."""
    level = Counter({x: 1}); rows = []; seen = set(); filled_total = 0; d = 0
    while level and d < max_depth:
        d += 1; nxt = Counter()
        for p, n in level.items():
            for q in parents_of.get(p, []):
                nxt[q] += n
        if not nxt:
            break
        filled = sum(nxt.values())
        rows.append({'depth': d, 'slots': 2 ** d, 'filled': filled, 'distinct': len(nxt), 'missing': 2 ** d - filled})
        filled_total += filled; seen |= set(nxt); level = nxt
    implex = (1 - Fraction(len(seen), filled_total)) if filled_total else Fraction(0)
    return {'depths': rows, 'distinct_ancestors': len(seen), 'filled_slots': filled_total, 'implex': str(implex), 'implex_float': round(float(implex), 4),
            'complete_to_depth': max([r['depth'] for r in rows if r['missing'] == 0] or [0])}
