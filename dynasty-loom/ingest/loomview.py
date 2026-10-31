"""loom-view/1 (proto/contracts/loom-view.md): the public-candidate view the scene generator reads, computed from the canonical
graph. Everything here is derived (prov computed) and computed on the people the view keeps, so every number in the file can be
recomputed from the file itself:
  shares      exact expected fraction of descent from each dye's founders (founder 1, anyone else with no parent in the view 0,
              child = mean of its parents; an unknown parent counts 0, so a share is a lower bound where a parent is missing)
  generation  [min, max] parent-to-child steps from any founder over all descent paths (kinship.ancestor_depths); people who do
              not descend from a founder are aligned: to a partner's range, else one step above their children, else one below
              their parents, repeated until nothing changes; anyone still unplaced has no generation
  phi         Malecot kinship of the two partners (kinship.Kinship, exact, a lower bound on a truncated pedigree)
  house       a core member's own house label (curated/houses.json); an in-law takes the house of the spouse at marriage (the
              earliest dated union with a core partner); anyone else in a union takes a partner's house; anyone else a parent's
The datagates adapter (family_members) turns the same records into the app's FamilyMember shape for proto/gates/datagates.py."""
import re
from collections import Counter, OrderedDict, defaultdict
from fractions import Fraction
from urllib.parse import quote

import kinship

ROMAN = re.compile(r'^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$')
TITLES = {'sir', 'lady', 'lord', 'baron', 'baroness', 'count', 'countess', 'duke', 'duchess', 'archduke', 'archduchess', 'emperor', 'empress',
          'king', 'queen', 'prince', 'princess', 'saint', 'st', 'dame', 'dr'}
NICK = re.compile(r"[\"'‘“]([A-Z][a-z]+)[\"'’”]")
MALE_T = {'king', 'emperor', 'archduke', 'duke', 'prince', 'count', 'baron', 'sir', 'lord', 'earl', 'baronet', 'margrave', 'elector'}
FEMALE_T = {'queen', 'empress', 'archduchess', 'duchess', 'princess', 'countess', 'baroness', 'lady', 'dame', 'margravine', 'electress', 'née', 'nee'}


def short_name(name):
    """Display label: a quoted nickname if there is one, else the first given name (titles dropped) plus a regnal numeral."""
    m = NICK.search(name or '')
    if m:
        return m.group(1)
    s = re.sub(r'\([^)]*\)', ' ', name or '').split(',')[0]
    toks = [t for t in s.split() if t]
    while len(toks) > 1 and toks[0].lower().strip('.') in TITLES:
        toks.pop(0)
    if not toks:
        return name
    if re.fullmatch(r'[A-Z]\.', toks[0]):                  # 'C. V. Wedgwood': initials are not a name
        return ' '.join(toks)
    return toks[0] + (' ' + toks[1] if len(toks) > 1 and ROMAN.match(toks[1]) else '')


def wiki_url(title):
    return 'https://en.wikipedia.org/wiki/' + quote(title.replace(' ', '_'), safe="_(),'!-.:~") if title else None


def clip(text, n=240):
    if not text or len(text) <= n:
        return text
    cut = text[:n - 1].rsplit(' ', 1)[0].rstrip(',;:')
    return cut + '…'


def year_of(fact):
    d = (fact or {}).get('date')
    return d['start']['y'] if d and d.get('start') else None


class Graph:
    """Read-only helpers over one canonical graph (private build)."""

    def __init__(self, g, houses_cfg):
        self.g = g
        self.nodes = {n['id']: n for n in g['nodes']}
        self.persons = [n for n in g['nodes'] if n['cls'] == 'Person']
        self.unions = [n for n in g['nodes'] if n['cls'] == 'Union']
        self.parents_of, self.partner_unions = defaultdict(list), defaultdict(list)
        for u in self.unions:
            for ch in u['children']:
                if (u.get('pedigree') or {}).get(ch, 'BIRTH') == 'BIRTH':
                    self.parents_of[ch] += [p for p in u['partners'] if p not in self.parents_of[ch]]
            if len(u['partners']) == 2:
                for p in u['partners']:
                    self.partner_unions[p].append(u)
        self.role_of, self.role_sex, self.role_clash = {}, defaultdict(Counter), []
        for c in g['claims']:                                   # precedence order: the first role given for a link stands
            if c['predicate'] == 'parents' and c.get('roles') and c.get('refs'):
                for r, role in zip(c['refs'], c['roles']):
                    k = (c['subject'], r['id'])
                    if k in self.role_of and self.role_of[k] != role:
                        self.role_clash.append({'child': k[0], 'parent': k[1], 'roles': [self.role_of[k], role], 'claim': c['id']})
                    self.role_of.setdefault(k, role)
                    self.role_sex[r['id']]['M' if role == 'father' else 'F'] += 1
        self.hmap = {}
        for ds, fc in houses_cfg['families'].items():
            for h in fc['houses']:
                for lab in h['labels']:
                    self.hmap[(ds, lab)] = h['key']

    def house_of_label(self, ds, label):
        return self.hmap.get((ds, label))

    def sex(self, pid):
        n = self.nodes[pid]
        if n.get('sex') and n['sex'].get('value') in ('M', 'F'):
            return n['sex']['value'], 'stated'
        rs = self.role_sex.get(pid)
        if rs and len(rs) == 1:
            return next(iter(rs)), 'parent role'
        words = {w.lower() for nm in [n['label']] + list(n.get('aliases') or []) for w in re.findall(r'[A-Za-z\u00e9]+', nm)}
        m, f = words & MALE_T, words & FEMALE_T
        if bool(m) != bool(f):
            return ('M' if m else 'F'), 'gendered title in the name'
        said = {x.lower() for nt in n.get('notes') or [] for x in re.findall(r'\b(?:[Gg]rand)?([Ss]on|[Dd]aughter) of\b', nt['text'])}
        if len(said) == 1:                                    # the source's note says 'Son of ...' or 'Daughter of ...'
            return ('M' if said == {'son'} else 'F'), 'note says son or daughter of'
        return None, None

    def vid(self, pid):
        return self.nodes[pid]['local']


def compute(G, ds, fam_cfg, members, founders):
    """View records for the people `members` (canonical ids) of dataset ds. founders: {dye: [canonical ids]}."""
    M = set(members)
    placed = {}                                             # child -> (father, mother): only links the view can publish
    for x in M:
        fa = mo = None
        for p in [p for p in G.parents_of.get(x, []) if p in M]:
            r = {'M': 'father', 'F': 'mother'}.get(G.sex(p)[0]) or G.role_of.get((x, p))
            if r == 'father' and fa is None:
                fa = p
            elif r == 'mother' and mo is None:
                mo = p
        placed[x] = (fa, mo)
    unplaced = [OrderedDict(child=G.vid(x), parent=G.vid(p)) for x in sorted(M) for p in G.parents_of.get(x, []) if p in M and p not in placed[x]]
    pv = {x: [p for p in placed[x] if p] for x in M}        # every derived value is computed over the published links only
    kids = defaultdict(list)
    for x in sorted(M):
        for p in pv[x]:
            kids[p].append(x)
    partners = {x: [] for x in M}
    for x in M:
        for u in sorted(G.partner_unions.get(x, []), key=lambda u: (year_of({'date': u.get('marriage_date')}) or 9999, u['id'])):
            q = next(p for p in u['partners'] if p != x)
            if q in M and q not in partners[x]:
                partners[x].append(q)
    order = kinship.topo_order(M, pv)
    kin = kinship.Kinship(sorted(M), pv)
    F = {f for fs in founders.values() for f in fs if f in M}

    # shares (exact)
    shares = {}
    for dye, fs in founders.items():
        sh = {}
        for x in order:
            sh[x] = Fraction(1) if x in fs else sum((sh[p] for p in pv[x]), Fraction(0)) / 2
        shares[dye] = sh

    # generation
    gen, how = {}, {}
    for x in M:
        d = kinship.ancestor_depths(x, pv)
        steps = [k for f in F if f in d for k in d[f]]
        if steps:
            gen[x] = [min(steps), max(steps)]; how[x] = 'founder' if x in F else 'descent'
    changed = True
    while changed:
        changed = False
        for x in sorted(M - set(gen)):
            ps = [gen[q] for q in partners[x] if q in gen]
            cs = [gen[c] for c in kids.get(x, []) if c in gen]
            pa = [gen[p] for p in pv[x] if p in gen]
            if ps:
                gen[x] = [min(r[0] for r in ps), max(r[1] for r in ps)]; how[x] = 'partner-aligned'
            elif cs:
                gen[x] = [min(r[0] for r in cs) - 1, max(r[1] for r in cs) - 1]; how[x] = 'child-aligned'
            elif pa:
                gen[x] = [1 + min(r[0] for r in pa), 1 + max(r[1] for r in pa)]; how[x] = 'parent-aligned'
            else:
                continue
            changed = True

    # core: a source's core flag (any partition saying core), else descent from a founder
    core, core_how = {}, {}
    for x in M:
        n = G.nodes[x]
        if n.get('core') is not None:
            core[x], core_how[x] = n['core'], 'source flag'
        else:
            core[x], core_how[x] = any(shares[d][x] > 0 for d in shares), 'descent from a founder'

    # houses
    own = {}
    for x in M:
        b = G.nodes[x].get('branch')
        own[x] = G.house_of_label(ds, G.nodes[b]['label']) if b else None
    house, house_how = {}, {}
    for x in sorted(M):
        if core[x] and own[x]:
            house[x], house_how[x] = own[x], 'own label (core member)'
    for x in sorted(M):                                     # a core wife joins her core husband's house (patrilocal in all three families)
        if core[x] and G.sex(x)[0] == 'F':
            hs = [q for q in partners[x] if core[q] and G.sex(q)[0] == 'M' and own[q]]
            if hs:
                house[x], house_how[x] = own[hs[0]], 'husband\'s house (core wife of a core husband)'
    for x in sorted(M):
        if x in house or core[x]:
            continue
        sp = [q for q in partners[x] if core[q] and q in house]
        if sp:
            house[x], house_how[x] = house[sp[0]], 'spouse at marriage (in-law)'
        elif own[x]:
            house[x], house_how[x] = own[x], 'own label (in-law, no core spouse with a house)'
    changed = True
    while changed:
        changed = False
        for x in sorted(M - set(house)):
            sp = [q for q in partners[x] if q in house]
            par = [p for p in sorted(pv[x], key=lambda p: G.sex(p)[0] != 'M') if p in house]
            if sp:
                house[x], house_how[x] = house[sp[0]], 'partner\'s house (no house of their own)'
            elif not partners[x] and par:
                house[x], house_how[x] = house[par[0]], 'parent\'s house (no label, no union)'
            else:
                continue
            changed = True

    people = OrderedDict()
    for x in sorted(M, key=lambda x: (year_of(G.nodes[x]['facts'].get('birth')) or 9999, G.nodes[x]['label'])):
        n = G.nodes[x]
        sx, sx_how = G.sex(x)
        fa, mo = placed[x]
        b, d = n['facts'].get('birth') or {}, n['facts'].get('death') or {}
        ids = n.get('ids') or {}
        rec = OrderedDict(id=n['local'], qid=ids.get('wikidata'), name=n['label'], short=short_name(n['label']), sex=sx,
                          born=year_of(b), born_precision=b.get('precision_label') or ('unknown' if b else None),
                          died=year_of(d), died_precision=d.get('precision_label') or ('unknown' if d else None),
                          house=house.get(x), core=core[x], family=family_of(G, x, pv, shares, fam_cfg),
                          father=G.vid(fa) if fa else None, mother=G.vid(mo) if mo else None,
                          shares=OrderedDict((dye, float(shares[dye][x])) for dye in founders),
                          generation=gen.get(x), confidence=n['grade'] if n['grade'] in ('Confirmed', 'Likely', 'Suspected') else 'Suspected',
                          wikipedia=wiki_url(ids.get('enwiki')), note=clip(n['notes'][0]['text']) if n.get('notes') else None,
                          sources=list(n.get('cites') or []))
        people[x] = rec
    unions = []
    for u in G.unions:
        if u.get('dataset') != ds or len(u['partners']) != 2 or not all(p in M for p in u['partners']):
            continue
        a, b = u['partners']
        md = u.get('marriage_date')
        phi = kin.phi(a, b)
        rel = None
        if phi > 0:
            ex = kinship.explain(a, b, pv, partners, kin)
            rel = relationship_label(G, a, b, ex)
        unions.append(OrderedDict(id='U-%s-%s' % (G.vid(a), G.vid(b)), a=G.vid(a), b=G.vid(b), year=md['start']['y'] if md and md.get('start') else None,
                                  year_precision=('circa' if md.get('kind') == 'approx' else 'year') if md and md.get('start') else 'unknown',
                                  close=phi > 0, relationship=rel, phi=float(phi), confidence=u['grade'] if u['grade'] in ('Confirmed', 'Likely', 'Suspected') else 'Suspected',
                                  _union=u['id'], _phi=str(phi)))
    srt = lambda d: OrderedDict(sorted(d.items()))     # key order fixed, so the ledger is byte-stable run to run
    aux = OrderedDict(unplaced_parent_links=unplaced, gen_method=srt(Counter(how.get(x, 'unplaced') for x in M)), core_method=srt(Counter(core_how.values())),
                      house_method=srt(Counter(house_how.get(x, 'none') for x in M)), sex_method=srt(Counter((G.sex(x)[1] or 'unknown') for x in M)),
                      shares_exact=srt({dye: srt({G.vid(x): str(v) for x, v in sh.items() if v}) for dye, sh in shares.items()}),
                      F=srt({G.vid(x): str(kin.inbreeding(x)) for x in M if kin.inbreeding(x) > 0}))
    return people, unions, aux


def family_of(G, x, pv, shares, fam_cfg):
    """The birth family: the source's `family` (an in-law's own family; 'in-law:unverified' is no family), else the father's,
    else the mother's when she carries a dye, else none."""
    seen = set()
    while x not in seen:
        seen.add(x)
        n = G.nodes[x]
        f = n.get('family')
        if f:
            f = f.split(':', 1)[1] if f.startswith('in-law:') else f
            return None if f.lower() == 'unverified' else f
        fa = [p for p in pv[x] if G.sex(p)[0] == 'M' or G.role_of.get((x, p)) == 'father']
        mo = [p for p in pv[x] if p not in fa and any(shares[d][p] > 0 for d in shares)]
        if fa:
            x = fa[0]
        elif mo:
            x = mo[0]
        else:
            return None
    return None


def relationship_label(G, a, b, ex):
    """kinship.explain's name, with the avuncular case said the way the contract does ('uncle-niece')."""
    rel = ex['relationship'] or ''
    if 'avuncular' not in rel:
        return rel
    best = min(ex['common_ancestors'], key=lambda r: (r['n1'] + r['n2'], r['n1'], r['ancestor']))
    elder, younger = (a, b) if best['n1'] < best['n2'] else (b, a)
    great = 'great-' * (max(best['n1'], best['n2']) - 2)
    e = {'M': 'uncle', 'F': 'aunt'}.get(G.sex(elder)[0], 'uncle/aunt')
    y = {'M': 'nephew', 'F': 'niece'}.get(G.sex(younger)[0], 'nephew/niece')
    return ('half-' if rel.startswith('half') else '') + great + e + '-' + great + y


def family_members(people, unions):
    """View records to the app's FamilyMember shape (proto/gates/datagates.py): born/died as the published years, generation the
    published max, parents the published father and mother, branch the house, spouse only for a couple where each partner has
    exactly that one union (the single-spouse field cannot hold more; unions are explicit and checked by G08)."""
    part = defaultdict(set)
    for u in unions:
        part[u['a']].add(u['b']); part[u['b']].add(u['a'])
    out = OrderedDict()
    for r in people.values():
        m = OrderedDict(id=r['id'], name=r['name'])
        if r['born'] is not None:
            m['born'] = r['born']
        if r['died'] is not None:
            m['died'] = r['died']
        if r['generation']:
            m['generation'] = r['generation'][1]
        m['parents'] = [p for p in (r['father'], r['mother']) if p]
        if r['house']:
            m['branch'] = r['house']
        if r['note']:
            m['note'] = r['note']
        sp = part.get(r['id'], set())
        if len(sp) == 1:
            q = next(iter(sp))
            if part.get(q) == {r['id']}:
                m['spouse'] = q
        if r['wikipedia']:
            m['wikipedia'] = r['wikipedia']
        out[r['id']] = m
    return out


def houses_view(fc, people, living_core_houses):
    """The family's houses with opened/closed computed from the view: first birth and last death of the house's core members;
    closed stays null while a core member of the house is presumed living (and so not in the view)."""
    out = []
    for h in fc['houses']:
        mem = [r for r in people.values() if r['house'] == h['key']]
        core = [r for r in mem if r['core']] or mem
        if not mem and h['key'] not in living_core_houses:
            continue
        births = [r['born'] for r in core if r['born'] is not None]
        deaths = [r['died'] for r in core if r['died'] is not None]
        open_ = h['key'] in living_core_houses
        out.append(OrderedDict(key=h['key'], name=h['name'], lon=h['lon'], lat=h['lat'], opened=min(births) if births else None,
                               closed=None if open_ or not deaths else max(deaths), note=h['note'] + ' (seat: %s)' % h['seat']))
    return out
