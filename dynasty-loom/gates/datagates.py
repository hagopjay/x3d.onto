"""DATA gates for a genealogy dataset: the layer before any scene is built.

check(members, cfg) -> list of findings. `members` is {id: record} in file order (a TS Record or a JSON tree's array,
normalised by sources.py). A finding is a dict: gate, severity (error | warn | info), subject (a person id), refs (other ids),
message, detail. Severity contract: an error blocks the build (the generator must not draw it), a warn goes to the owner with the
build, an info is recorded in the receipt only.

What the gates can and cannot say: they check the data against itself and against biology (dates, ages, graph shape). They never
say who the right father is; a second witness (a source per relation) is what can say that. Grade every gate verdict Confirmed for
"the file says this"; a historical reading of it is a separate claim with its own grade."""
import re
import unicodedata
from collections import defaultdict

DEFAULTS = dict(
    asof=2026,               # the year the privacy rule is evaluated in (written into the receipt)
    min_parent_age=12,       # a parent younger than this at the child's birth is a data error
    max_parent_age=80,       # older than this: a data error (no sex field, so one bound for mothers and fathers)
    posthumous_tol=1,        # years a child may be born after a parent's death (year-granular data; a father can die ~9 months before)
    living_horizon=110,      # no death year and born within this many years of asof: presumed living
    max_lifespan=122,        # oldest verified human lifespan
)

# fields of FamilyMember in types.ts (all four app variants agree): required and optional, with their JSON types
REQUIRED = {'id': str, 'name': str, 'born': int, 'generation': int, 'parents': list, 'branch': str, 'note': str}
OPTIONAL = {'died': int, 'spouse': str, 'wikipedia': str, 'imageUrl': str, 'achievements': list}
PLACEHOLDER_IMAGE_HOSTS = ('picsum.photos', 'placehold.co', 'via.placeholder.com', 'placekitten.com', 'loremflickr.com',
                           'dummyimage.com', 'source.unsplash.com', 'thispersondoesnotexist.com', 'placeimg.com')
PARTICLES = {'von', 'van', 'de', 'der', 'den', 'du', 'des', 'la', 'le', 'of', 'the', 'da', 'di', 'del', 'zu', 'nee', 'i', 'ii', 'iii', 'iv',
             'baron', 'lord', 'holy', 'roman', 'emperor', 'king', 'queen', 'sir', 'st', '1st', '2nd', '3rd'}
WIKI = re.compile(r'^https://([a-z\-]+)\.(?:m\.)?wikipedia\.org/wiki/([^?#\s]+)$')


def F(gate, severity, subject, message, refs=(), **detail):
    return dict(gate=gate, severity=severity, subject=subject, refs=list(refs), message=message, detail=detail)


def fold(s):
    """lower case, accents off, punctuation to spaces"""
    s = unicodedata.normalize('NFKD', str(s)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def name_tokens(name):
    return {t for t in fold(re.sub(r'\(.*?\)', ' ', name or '')).split() if t not in PARTICLES and len(t) > 1}


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(members, cfg=None):
    c = dict(DEFAULTS, **(cfg or {})); out = []
    M = members

    # ---- D00 schema: the record shape the app's types.ts promises (a missing note or branch reaches the card as "undefined").
    #      Missing id/note/branch are aggregated per field (the pre-schema HTML pages lack them on every record); type errors stay per record.
    missing = defaultdict(list)
    for k, p in M.items():
        if not isinstance(p, dict):
            out.append(F('D00-schema', 'error', k, 'record is not an object')); continue
        if 'id' not in p:
            missing['id'].append(k)
        elif p['id'] != k:
            out.append(F('D00-schema', 'error', k, 'id %r differs from its key %r' % (p['id'], k), field='id'))
        for f, t in REQUIRED.items():
            if f == 'id': continue
            if f not in p or p[f] is None:
                if f in ('note', 'branch'): missing[f].append(k)
                else: out.append(F('D00-schema', 'error', k, 'required field %s missing' % f, field=f))
            elif (t is int and not _int(p[f])) or (t is not int and not isinstance(p[f], t)):
                out.append(F('D00-schema', 'error', k, 'field %s should be %s, is %r' % (f, t.__name__, p[f]), field=f))
        for f, t in OPTIONAL.items():
            if p.get(f) is not None and ((t is int and not _int(p[f])) or (t is not int and not isinstance(p[f], t))):
                out.append(F('D00-schema', 'error', k, 'field %s should be %s, is %r' % (f, t.__name__, p[f]), field=f))
        extra = sorted(set(p) - set(REQUIRED) - set(OPTIONAL))
        if extra: out.append(F('D00-schema', 'info', k, 'fields outside the schema: %s' % ', '.join(extra), fields=extra))
    for f, ks in missing.items():
        out.append(F('D00-schema', 'warn', None, '%d of %d records have no %s%s' % (len(ks), len(M), f, ' (the key stands in)' if f == 'id' else ' (the card shows "undefined")'),
                     field=f, kind='missing', subjects=ks))

    # ---- D15 placeholder text that would reach a card as a biography or a title
    for k, p in M.items():
        if not isinstance(p, dict): continue
        for f in ('name', 'note'):
            v = p.get(f)
            if isinstance(v, str) and re.search(r'(?i)\b(stub|lorem|todo|tbd|placeholder|replace (?:this|with))\b', v):
                out.append(F('D15-placeholder-text', 'warn', k, '%s reads %r' % (f, v[:80]), field=f))

    born = {k: p.get('born') for k, p in M.items() if isinstance(p, dict) and _int(p.get('born'))}
    died = {k: p.get('died') for k, p in M.items() if isinstance(p, dict) and _int(p.get('died'))}
    gen = {k: p.get('generation') for k, p in M.items() if isinstance(p, dict) and _int(p.get('generation'))}
    par = {k: [x for x in (p.get('parents') or []) if isinstance(x, str)] for k, p in M.items() if isinstance(p, dict)}
    sp = {k: p.get('spouse') for k, p in M.items() if isinstance(p, dict) and isinstance(p.get('spouse'), str)}

    # ---- D01 dangling parent references (the scene drops the edge silently: `if (parentPos) createEdge(...)`)
    # ---- D13 parent-list shape (self, repeats, more than two)
    for k, ps in par.items():
        for x in ps:
            if x == k:
                out.append(F('D02-cycle', 'error', k, 'lists itself as a parent', refs=[k]))
            elif x not in M:
                out.append(F('D01-dangling-parent', 'error', k, 'parent %r is not in the dataset (the edge is silently not drawn)' % x, refs=[x]))
        if len(set(ps)) != len(ps): out.append(F('D13-parents-shape', 'warn', k, 'a parent is listed twice', refs=ps))
        if len(set(ps)) > 2: out.append(F('D13-parents-shape', 'warn', k, '%d parents listed' % len(set(ps)), refs=ps))

    # ---- D02 cycles in the parent graph (someone is their own ancestor): iterative DFS, report each cycle once
    edges = {k: [x for x in ps if x in M and x != k] for k, ps in par.items()}
    colour, seen_cycles = {}, set()
    for root in M:
        if colour.get(root): continue
        stack = [(root, iter(edges.get(root, [])))]; path = [root]; colour[root] = 1
        while stack:
            node, it = stack[-1]; nxt = next(it, None)
            if nxt is None:
                colour[node] = 2; stack.pop(); path.pop(); continue
            if colour.get(nxt) == 1:
                cyc = path[path.index(nxt):]; key = frozenset(cyc)
                if key not in seen_cycles:
                    seen_cycles.add(key); out.append(F('D02-cycle', 'error', min(cyc), 'ancestry cycle: %s' % ' -> '.join(cyc + [nxt]), refs=sorted(cyc)))
            elif not colour.get(nxt):
                colour[nxt] = 1; stack.append((nxt, iter(edges.get(nxt, [])))); path.append(nxt)

    # ---- D03 child not younger than parent, D04 born after a parent's death, D05 parent age out of range
    for k, ps in edges.items():
        for x in ps:
            if k in born and x in born:
                age = born[k] - born[x]
                if age <= 0:
                    out.append(F('D03-child-not-younger', 'error', k, 'born %d, parent %s born %d' % (born[k], x, born[x]), refs=[x], age=age))
                elif age < c['min_parent_age'] or age > c['max_parent_age']:
                    out.append(F('D05-parent-age', 'error', k, 'parent %s was %d at the birth (allowed %d to %d)' % (x, age, c['min_parent_age'], c['max_parent_age']), refs=[x], age=age))
            if k in born and x in died and born[k] > died[x] + c['posthumous_tol']:
                out.append(F('D04-born-after-parent-death', 'error', k, 'born %d, %d years after parent %s died (%d)' % (born[k], born[k] - died[x], x, died[x]), refs=[x], gap=born[k] - died[x]))

    # ---- D06 death before birth, impossible lifespans, dates after asof
    for k in M:
        if k in born and born[k] > c['asof']: out.append(F('D06-dates', 'error', k, 'born %d, after %d' % (born[k], c['asof'])))
        if k in died and died[k] > c['asof']: out.append(F('D06-dates', 'error', k, 'died %d, after %d' % (died[k], c['asof'])))
        if k in born and k in died:
            if died[k] < born[k]: out.append(F('D06-dates', 'error', k, 'died %d before born %d' % (died[k], born[k])))
            elif died[k] - born[k] > c['max_lifespan']: out.append(F('D06-dates', 'error', k, 'lifespan %d years' % (died[k] - born[k])))

    # ---- D07 duplicates: same wikipedia article, or names that fold to the same person within a year of birth
    by_url = defaultdict(list)
    for k, p in M.items():
        if isinstance(p, dict) and isinstance(p.get('wikipedia'), str): by_url[p['wikipedia'].rstrip('/')].append(k)
    for u, ks in by_url.items():
        if len(ks) > 1: out.append(F('D07-duplicate', 'warn', ks[0], 'same wikipedia article for %s' % ', '.join(ks), refs=ks[1:], url=u))
    keys = [k for k in M if isinstance(M[k], dict)]
    for i, a in enumerate(keys):
        ta = name_tokens(M[a].get('name'))
        for b in keys[i + 1:]:
            tb = name_tokens(M[b].get('name'))
            if len(ta & tb) >= 2 and (ta <= tb or tb <= ta) and a in born and b in born and abs(born[a] - born[b]) <= 1:
                out.append(F('D07-duplicate', 'warn', a, 'probably the same person as %s (%r, %r, born %d and %d)' % (b, M[a].get('name'), M[b].get('name'), born[a], born[b]), refs=[b]))

    # ---- D08 generation number against the graph (the layout puts each person on the latitude of their `generation`)
    topo = {}
    def depth(k, guard=()):
        if k in topo: return topo[k]
        if k in guard: return 1
        ps = [x for x in edges.get(k, []) if x in M]
        topo[k] = 1 + max((depth(x, guard + (k,)) for x in ps), default=0); return topo[k]
    for k in M: depth(k)
    for _ in range(len(M)):                                          # a married-in spouse (no parents in the data) takes the partner's depth
        changed = False
        for k in M:
            s = sp.get(k)
            if not [x for x in edges.get(k, []) if x in M] and s in topo and topo[s] > topo[k]:
                topo[k] = topo[s]; changed = True
        for k in M:                                                  # and the children of married-in spouses follow
            ps = [x for x in edges.get(k, []) if x in M]
            if ps:
                d = 1 + max(topo[x] for x in ps)
                if d != topo[k]: topo[k] = d; changed = True
        if not changed: break
    for k, ps in edges.items():
        for x in ps:
            if k in gen and x in gen:
                d = gen[k] - gen[x]
                if d <= 0:
                    out.append(F('D08-generation', 'error', k, 'generation %d, but parent %s is generation %d (a child cannot share or precede a parent\'s generation)' % (gen[k], x, gen[x]), refs=[x], kind='not-below-parent'))
                elif d > 1:
                    out.append(F('D08-generation', 'warn', k, 'generation %d, parent %s is generation %d: %d generation(s) skipped, so an ancestor is probably missing' % (gen[k], x, gen[x], d - 1), refs=[x], kind='skip', skipped=d - 1))
        pg = sorted({gen[x] for x in ps if x in gen})
        if len(pg) > 1: out.append(F('D08-generation', 'info', k, 'parents sit in different generations %s (cross-generation union)' % pg, refs=ps, kind='mixed-parents'))
    sibs = defaultdict(list)                                          # full siblings (the same in-data parent set) must share a generation
    for k, ps in edges.items():
        key = frozenset(x for x in ps if x in M)
        if key and k in gen: sibs[key].append(k)
    for key, ks in sibs.items():
        gs = sorted({gen[k] for k in ks})
        if len(gs) > 1:
            out.append(F('D08-generation', 'error', ks[0], 'full siblings %s (parents %s) carry different generations %s' % (', '.join('%s=%d' % (k, gen[k]) for k in ks), '+'.join(sorted(key)), gs),
                         refs=ks[1:], kind='siblings', fp_key='siblings:' + '+'.join(sorted(key))))
    for k in M:
        if k in gen and k in topo and gen[k] != topo[k]:
            out.append(F('D08-generation', 'info', k, 'generation %d, depth in the graph %d' % (gen[k], topo[k]), kind='topology', topo=topo[k]))

    # ---- D09 spouse symmetry; the scene draws a spouse edge only from the record whose global id sorts first
    #      (`childId < spouseId`), so a one-sided link is drawn or lost depending on how the two ids are spelled
    for k, s in sp.items():
        if s == k:
            out.append(F('D09-spouse', 'error', k, 'spouse of themself', refs=[k])); continue
        if s not in M:
            out.append(F('D09-spouse', 'error', k, 'spouse %r is not in the dataset' % s, refs=[s])); continue
        back = sp.get(s)
        if back is None:
            drawn = k < s
            out.append(F('D09-spouse', 'error' if not drawn else 'warn', k,
                         'names %s as spouse, %s names no spouse: the marriage edge is %s' % (s, s, 'drawn only because %r sorts before %r' % (k, s) if drawn else 'never drawn (%r sorts after %r)' % (k, s)),
                         refs=[s], drawn=drawn))
        elif back != k:
            out.append(F('D09-spouse', 'error', k, 'names %s as spouse, but %s names %s' % (s, s, back), refs=[s, back]))

    # ---- D10 privacy: presumed living people may not reach a public build; long-dead people with no death year read "Present"
    for k, p in M.items():
        if not isinstance(p, dict) or k in died: continue
        if k in born and born[k] > c['asof'] - c['living_horizon']:
            out.append(F('D10-living', 'error', k, 'no death year and born %d: presumed living (horizon %d years); keep out of a public build unless consented' % (born[k], c['living_horizon'])))
        elif k in born:
            out.append(F('D10-living', 'warn', k, 'no death year, born %d: the card will print "%d - Present"' % (born[k], born[k])))

    # ---- D11 portraits: a placeholder photo service is shown as the likeness of a real person
    for k, p in M.items():
        u = p.get('imageUrl') if isinstance(p, dict) else None
        if isinstance(u, str) and any(h in u for h in PLACEHOLDER_IMAGE_HOSTS):
            out.append(F('D11-portrait', 'error', k, 'imageUrl %s is a random placeholder photo, shown as %s' % (u, p.get('name')), url=u))

    # ---- D12 wikipedia links: well-formed, and the article title shares a name token with the person
    for k, p in M.items():
        u = p.get('wikipedia') if isinstance(p, dict) else None
        if not isinstance(u, str): continue
        m = WIKI.match(u)
        if not m:
            out.append(F('D12-wikipedia', 'error', k, 'not a wikipedia article URL: %s' % u, url=u)); continue
        title = fold(m.group(2).replace('_', ' ')); toks = name_tokens(p.get('name'))
        if toks and not (toks & set(title.split())):
            out.append(F('D12-wikipedia', 'warn', k, 'article %r shares no name token with %r' % (m.group(2), p.get('name')), url=u))

    # ---- D14 islands: people joined to nobody (no parent, child or spouse in the data) in a dataset larger than one
    if len(M) > 1:
        adj = defaultdict(set)
        for k, ps in edges.items():
            for x in ps: adj[k].add(x); adj[x].add(k)
        for k, s in sp.items():
            if s in M: adj[k].add(s); adj[s].add(k)
        for k in M:
            if not adj[k]:
                out.append(F('D14-island', 'warn', k, 'connected to no one in the dataset (generation %s): drawn as a lone star with no edge' % gen.get(k)))
    return out


def summarize(findings):
    by = defaultdict(lambda: defaultdict(int))
    for f in findings: by[f['gate']][f['severity']] += 1
    return {g: dict(v) for g, v in sorted(by.items())}
