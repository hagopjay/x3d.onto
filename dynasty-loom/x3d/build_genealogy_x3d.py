#!/usr/bin/env python3
"""Genealogy loom (prototype): family-tree JSON (the roths/data/trees/*.json schema) -> one X3D 4.0 scene for X_ITE, its anchors and a receipt.
Generated, seeded by nothing (fully deterministic), standard library only. Never hand-edit the .x3d: change this file and rebuild.

    python3 -I build_genealogy_x3d.py TREE.json [TREE.json ...] [--out DIR] [--name genealogy] [--validate] [--x3d-mcp DIR]

Trees that share an `id` are merged: the first file wins for a member it already has, later files only add members (every field that
disagrees is listed in the receipt under data.conflicts). Trees with other ids become further bolts on the same time axis.

THE SPATIAL GRAMMAR (primary: the loom drum)
  * Time is the drum's axis, +X, the same absolute scale for every dataset (TS units per year, YEAR_C at x = 0), so families that lived at the
    same time stand side by side.
  * A house (the `branch` field) is a sector of the drum, at the angle the React orb already gives it (roths3/constants.tsx BRANCH_POSITIONS:
    Frankfurt 0, Vienna 0.4 pi, London 0.8 pi, Naples 1.2 pi, Paris 1.6 pi), so the five brothers' houses keep their directions. 0 faces the
    default camera (+Z).
  * A person is a WARP thread: a bead at birth and a lit thread to death along +X, on a lane of the house's sector. Lanes are interval-scheduled
    (a lane is reused only after its last occupant has died), a spouse takes the lane next to the partner, a child the free lane nearest its parents.
  * Parentage is a LIFT: a gold strand that leaves the parent's thread two years before the child's birth and lands on the child's bead. Within a
    house it is a short S; across houses it arches off the drum (height grows with the angle it crosses), so the founders' sons fan out round the drum.
  * A marriage is a WEFT: a rose pick across the two spouses' threads at the year before their first child in the data (no marriage dates exist in
    the data; with no child the pick is an estimate, drawn translucent and listed in the receipt).
  * A weft that LOOPS BACK: when the spouses share an ancestor (cousins, uncle and niece), the cycle (weft, both spouses' threads, the lifts up to
    the nearest common ancestor and the stretch of that ancestor's thread between the two lifts) is drawn as one ember loop with a pulse running round it.
SECONDARY: generation rings. The same beads slide along the axis to one station per `generation` value (the median birth year of that generation),
    by a scriptless morph (one TimeSensor, one ScalarInterpolator, PositionInterpolators per bead, CoordinateInterpolators per line set). A bead that
    moves against the flow is a person whose `generation` label disagrees with the birth years (Betty, Anselm).

X3D: profile Immersive 4.0; a PersonBead PROTO (bead, thread, name, TouchSensor exported as isActive); Viewpoint stops per house and per bolt; selection
is TouchSensor -> IntegerTrigger -> two Switches (the halo and lineage in the world, the card in a HUD carried by a ProximitySensor); every ROUTE is
written after the nodes it names (X_ITE 16.5.1 drops a ROUTE that comes first, and the fork validator does not catch it: gobbler-demiurge README)."""
import datetime, gzip, hashlib, itertools, json, math, os, re, subprocess, sys
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PI = math.pi

# ---------------------------------------------------------------- parameters (scene units; one unit is nothing physical)
TS = 0.07                  # units per year along +X
YEAR_C = 1875              # the year at x = 0
R_MAIN = 4.5               # drum radius of the largest dataset
R_BOLT = 1.6               # drum radius of the other datasets (the stubs)
LANE_DEG = 7.5             # lane spacing on the drum, degrees (0.59 units on the main drum)
LIFT_YEARS = 2.0           # a lift leaves the parent's thread this long before the child's birth
LANE_GAP = 4               # a lane is free again this many years after its occupant died
N_LIFT, N_WEFT = 16, 9     # samples per lift and per weft (fixed, so the loom and the rings have the same topology for the morph)
MORPH_S = 12.0             # the generation-rings round trip: 3 s out, 6 s held, 3 s back
NEW_LANE_COST = 1.25       # a free lane this much farther from the target still beats opening a new lane (keeps a house compact)
BOLT_GAP = 9.5             # the other datasets' drums hang this far below the main drum (clear of the house stops' frames)
HOUSE_ORDER = 'optimal'    # 'optimal': the circular order of houses that keeps cross-house lifts and wefts shortest (the founders' house in front); 'orb': the React orb's angles

# the React orb's house directions (roths3/constants.tsx BRANCH_POSITIONS), kept so a house sits where the user already looks for it
BRANCH_ANGLES = {'Frankfurt': 0.0, 'Vienna': 0.4 * PI, 'London': 0.8 * PI, 'Naples': 1.2 * PI, 'Paris': 1.6 * PI,
                 'Habsburg': 0.0, 'Darwin': 0.0, 'Wedgwood': PI}
HOUSE_COLORS = {'Frankfurt': (0.93, 0.74, 0.34), 'Vienna': (0.92, 0.42, 0.38), 'London': (0.45, 0.64, 0.98), 'Naples': (0.40, 0.83, 0.58),
                'Paris': (0.76, 0.55, 0.98), 'Habsburg': (0.90, 0.72, 0.52), 'Darwin': (0.38, 0.80, 0.78), 'Wedgwood': (0.58, 0.70, 0.96)}
FALLBACK = [(0.95, 0.60, 0.30), (0.55, 0.85, 0.95), (0.95, 0.55, 0.80), (0.70, 0.90, 0.45), (0.85, 0.85, 0.85)]
GOLD = (0.84, 0.70, 0.36)              # the gobbler's gold (gobbler-demiurge/tools/layers.py GOLD)
LIFT_C = (0.80, 0.64, 0.32)
WEFT_C = (1.0, 0.45, 0.62)             # the React app's spouse colour 0xff6b9d
ODD_C = (0.35, 0.95, 1.0)              # a lift whose generation labels do not step by one turns this colour in the generation rings
LOOP_C = (1.0, 0.52, 0.16)
HI_C = (1.0, 0.95, 0.80)
SKY = '0.057 0.05 0.047'               # the gobbler scenes' warm black


# ---------------------------------------------------------------- small helpers
def fm(x):
    t = '%.5g' % x
    return '0' if t in ('-0', '0', '-0.0') else t


def v3(p): return ' '.join(fm(c) for c in p)
def lerp(a, b, t): return a + (b - a) * t
def smooth(t): return t * t * (3 - 2 * t)


def xa(s):
    """escape for a single-quoted XML attribute"""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;')


def mfs(items):
    """MFString value: each string in double quotes, \\ and \" escaped (X3D XML encoding)"""
    return ' '.join('"%s"' % str(s).replace('\\', '\\\\').replace('"', '\\"') for s in items)


def wrap(text, width):
    out, line = [], ''
    for w in text.split():
        if line and len(line) + 1 + len(w) > width: out.append(line); line = w
        else: line = (line + ' ' + w).strip()
    if line: out.append(line)
    return out


def axis_angle_from_basis(right, up, back):
    """the SFRotation that turns the default frame (X right, Y up, Z back) into the given orthonormal basis"""
    m00, m01, m02 = right[0], up[0], back[0]
    m10, m11, m12 = right[1], up[1], back[1]
    m20, m21, m22 = right[2], up[2], back[2]
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1) * 2; qw = s / 4; qx = (m21 - m12) / s; qy = (m02 - m20) / s; qz = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1 + m00 - m11 - m22) * 2; qw = (m21 - m12) / s; qx = s / 4; qy = (m01 + m10) / s; qz = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1 + m11 - m00 - m22) * 2; qw = (m02 - m20) / s; qx = (m01 + m10) / s; qy = s / 4; qz = (m12 + m21) / s
    else:
        s = math.sqrt(1 + m22 - m00 - m11) * 2; qw = (m10 - m01) / s; qx = (m02 + m20) / s; qy = (m12 + m21) / s; qz = s / 4
    qw = max(-1.0, min(1.0, qw)); sn = math.sqrt(max(0.0, 1 - qw * qw))
    return (0.0, 0.0, 1.0, 0.0) if sn < 1e-9 else (qx / sn, qy / sn, qz / sn, 2 * math.acos(qw))


def norm(a):
    l = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / l for c in a)


def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def sub(a, b): return tuple(x - y for x, y in zip(a, b))


def look_at(pos, target, up=(0, 1, 0)):
    back = norm(sub(pos, target)); right = norm(cross(up, back)); u = cross(back, right)
    return axis_angle_from_basis(right, u, back)


def wrap_angle(a):
    while a <= -PI: a += 2 * PI
    while a > PI: a -= 2 * PI
    return a


# ---------------------------------------------------------------- data
def load_trees(paths):
    """-> ordered dict of datasets {id: {id, name, members: {id: m}, sources: [...], conflicts: [...]}}"""
    ds = {}
    for p in paths:
        raw = open(p, 'rb').read(); t = json.loads(raw.decode('utf-8'))
        src = dict(file=os.path.basename(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), members=len(t['members']))
        if t.get('provenance'): src['provenance'] = t['provenance']
        d = ds.setdefault(t['id'], dict(id=t['id'], name=t['name'], members={}, sources=[], conflicts=[], added={}))
        d['sources'].append(src); added = 0
        for m in t['members']:
            mid = m['id']
            if mid in d['members']:
                old = d['members'][mid]
                for f in sorted(set(old) | set(m)):
                    if f in ('wikipedia', 'imageUrl', '_src', '_sur'): continue
                    if old.get(f) != m.get(f):
                        d['conflicts'].append(dict(member=mid, field=f, kept=old.get(f), kept_from=old['_src'], other=m.get(f), other_from=src['file']))
                continue
            mm = dict(m); mm['_src'] = src['file']; mm.setdefault('parents', []); d['members'][mid] = mm; added += 1
        d['added'][src['file']] = added
    return ds


def check_data(d):
    """what the data itself says is wrong or missing: dangling references, one-sided marriages, generation labels that disagree with descent"""
    M = d['members']; notes = []
    for m in M.values():
        for p in m['parents']:
            if p not in M: notes.append(dict(kind='dangling-parent', member=m['id'], ref=p))
        if m.get('spouse') and m['spouse'] not in M: notes.append(dict(kind='dangling-spouse', member=m['id'], ref=m['spouse']))
        if m.get('spouse') in M and M[m['spouse']].get('spouse') != m['id']:
            notes.append(dict(kind='one-sided-marriage', member=m['id'], ref=m['spouse']))
        for p in m['parents']:
            if p in M:
                g, gp = m.get('generation'), M[p].get('generation')
                if g is not None and gp is not None and g - gp != 1:
                    notes.append(dict(kind='generation-gap', member=m['id'], generation=g, parent=p, parent_generation=gp))
                if m['born'] <= M[p]['born']: notes.append(dict(kind='born-before-parent', member=m['id'], parent=p))
        if m.get('died') is None: notes.append(dict(kind='no-death-year', member=m['id']))
    return notes


def couples(d):
    """unique marriages (either side naming the other is enough), with the weft year: the year before the first common child in the data,
    else an estimate (the younger spouse's 25th year), flagged"""
    M = d['members']; seen = set(); out = []
    for m in sorted(M.values(), key=lambda m: (m['born'], m['id'])):
        s = m.get('spouse')
        if not s or s not in M: continue
        key = tuple(sorted((m['id'], s)))
        if key in seen: continue
        seen.add(key)
        kids = sorted((c for c in M.values() if set(key) <= set(c['parents'])), key=lambda c: c['born'])
        if kids: year, est = kids[0]['born'] - 1, False
        else: year, est = max(M[key[0]]['born'], M[key[1]]['born']) + 25, True
        out.append(dict(a=key[0], b=key[1], year=year, estimated=est, first_child=kids[0]['id'] if kids else None))
    return out


def ancestors(M, pid):
    """{ancestor id: (depth, child-on-path)} by breadth-first search up the parents"""
    out = {pid: (0, None)}; frontier = [pid]
    while frontier:
        nxt = []
        for c in frontier:
            for p in M[c]['parents']:
                if p in M and p not in out:
                    out[p] = (out[c][0] + 1, c); nxt.append(p)
        frontier = nxt
    return out


def kinship(M, a, b):
    """the nearest common ancestor of a and b (ties: the earlier-born) and the relationship it makes, or None"""
    A, B = ancestors(M, a), ancestors(M, b)
    common = [x for x in A if x in B]
    if not common: return None
    g = min(common, key=lambda x: (A[x][0] + B[x][0], M[x]['born'], x))
    da, db = A[g][0], B[g][0]
    co_anc = sorted((x for x in common if A[x][0] == da and B[x][0] == db), key=lambda x: M[x]['born'])
    if min(da, db) == 1:
        older, younger = (a, b) if da == 1 else (b, a)
        par = M[younger]['parents']; via = next((p for p in par if p in B or p in A), par[0] if par else None)
        rel = '%s is a sibling of %s\'s parent %s (uncle/aunt and niece/nephew)' % (short(M, older), short(M, younger), short(M, via)) if (da, db) in ((1, 2), (2, 1)) else 'lineal (%d, %d)' % (da, db)
    else:
        deg, rem = min(da, db) - 1, abs(da - db)
        ordn = {1: 'first', 2: 'second', 3: 'third'}.get(deg, '%dth' % deg)
        rel = '%s cousins%s' % (ordn, '' if not rem else ' %s removed' % ({1: 'once', 2: 'twice'}.get(rem, '%d times' % rem)))
    return dict(ancestor=g, co_ancestors=co_anc, da=da, db=db, relation=rel)


def short(M, pid):
    """the label: the name without the dataset's dominant surname (and its de/von), and without anything after a comma"""
    if pid is None: return '?'
    n = M[pid]['name'].split(',')[0].strip()
    sur = M[pid].get('_sur')
    if sur:
        n2 = re.sub(r'\s+(?:de\s+|von\s+)?%s$' % re.escape(sur), '', n).strip()
        if n2 and n2 != n: n = n2
    return n


def dominant_surname(M):
    last = {}
    for m in M.values():
        w = m['name'].split(',')[0].split()[-1]; last[w] = last.get(w, 0) + 1
    w, c = max(last.items(), key=lambda kv: kv[1])
    return w if c > len(M) / 2 else None


# ---------------------------------------------------------------- layout
def X(year): return (year - YEAR_C) * TS


def assign_lanes(M, ids, spouse_of):
    """interval scheduling on integer lanes 0, +1, -1, +2, ...: a spouse beside the partner, a child nearest its parents"""
    lane, busy = {}, {}
    for pid in sorted(ids, key=lambda i: (M[i]['born'], i)):
        m = M[pid]; target, avoid = 0.0, set()
        sp = spouse_of.get(pid)
        if sp in lane: target = lane[sp] + 0.6; avoid.add(lane[sp])
        else:
            pl = [lane[p] for p in m['parents'] if p in lane]
            if pl: target = sum(pl) / len(pl)
        free = [l for l, until in busy.items() if until < m['born'] and l not in avoid]
        new = [max(busy) + 1, min(busy) - 1] if busy else [0]
        best = min([(abs(l - target), abs(l), -l, l) for l in free] + [(abs(l - target) + (NEW_LANE_COST if busy else 0), abs(l), -l, l) for l in new])[3]
        lane[pid] = best; busy[best] = (m.get('died') or m['born'] + 80) + LANE_GAP
    return lane


def layout(datasets):
    """positions for every person in both layouts, per dataset drum frames, viewpoints"""
    order = sorted(datasets.values(), key=lambda d: -len(d['members']))
    rows = []                                                                                       # bolts below the main drum, stacked when their years overlap
    L = {}
    for k, d in enumerate(order):
        M = d['members']; sur = dominant_surname(M)
        for m in M.values(): m['_sur'] = sur
        ids = list(M)
        born = [M[i]['born'] for i in ids]; died = [M[i].get('died') or M[i]['born'] + 80 for i in ids]
        x0, x1 = X(min(born)), X(max(died))
        R = R_MAIN if k == 0 else R_BOLT
        if k == 0: cy = 0.0
        else:
            row = 0
            while any(r == row and not (x1 + 3 < a or b + 3 < x0) for r, a, b in rows): row += 1
            rows.append((row, x0, x1)); cy = -(R_MAIN + BOLT_GAP + R_BOLT + row * (2 * R_BOLT + 2.2))
        houses = []
        for i in sorted(ids, key=lambda i: (M[i]['born'], i)):
            if M[i]['branch'] not in houses: houses.append(M[i]['branch'])
        lifts_h = [(M[p]['branch'], M[c]['branch']) for c in ids for p in M[c]['parents'] if p in M]
        cpl_h = [(M[c['a']]['branch'], M[c['b']]['branch']) for c in couples(d)]
        ang, order_note = house_angles(houses, lifts_h, cpl_h)
        col = {h: HOUSE_COLORS.get(h, FALLBACK[j % len(FALLBACK)]) for j, h in enumerate(houses)}
        spouse_of = {}
        for c in couples(d): spouse_of[c['a']] = c['b']; spouse_of[c['b']] = c['a']
        sector = 2 * PI / max(1, len(houses)) if len(houses) > 1 else 2 * PI
        lanes = {}; lane_rad = math.radians(LANE_DEG)
        for h in houses:
            lanes[h] = assign_lanes(M, [i for i in ids if M[i]['branch'] == h], spouse_of)
            n = max(lanes[h].values()) - min(lanes[h].values()) + 1
            lane_rad = min(lane_rad, 0.8 * sector / max(1, n))
        P = {}
        for h in houses:
            lo, hi = min(lanes[h].values()), max(lanes[h].values()); mid = (lo + hi) / 2
            for i, l in lanes[h].items(): P[i] = dict(house=h, lane=l, theta=ang[h] + (l - mid) * lane_rad)
        gens = {}
        for i in ids:
            g = M[i].get('generation')
            if g is not None: gens.setdefault(g, []).append(M[i]['born'])
        station = {g: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2 for g, v in gens.items()}
        dup = {}
        for i in sorted(ids, key=lambda i: (M[i]['born'], i)):
            m = M[i]; p = P[i]; p['xb'] = X(m['born']); p['xd'] = X(m.get('died') or m['born'] + 80)
            g = m.get('generation'); key = (g, p['house'], p['lane'])
            p['xg'] = X(station.get(g, m['born'])) + 0.3 * dup.get(key, 0); dup[key] = dup.get(key, 0) + 1
        L[d['id']] = dict(R=R, cy=cy, cz=0.0, x0=x0, x1=x1, houses=houses, ang=ang, col=col, sector=sector, lane_rad=lane_rad, P=P, station=station,
                          ids=ids, couples=couples(d), main=(k == 0), house_order=order_note)
    return order, L


def orb_angles(houses):
    known = [h for h in houses if h in BRANCH_ANGLES]; unknown = [h for h in houses if h not in BRANCH_ANGLES]
    ang = {h: BRANCH_ANGLES[h] for h in known}
    for j, h in enumerate(unknown): ang[h] = 2 * PI * (j + 0.5) / max(1, len(unknown)) + (0.3 if known else 0)
    return ang


def house_angles(houses, lifts_h, cpl_h):
    """the angle of each house. 'orb' keeps the React orb's BRANCH_POSITIONS. 'optimal' keeps the orb's slots (n equal sectors), puts the founders' house
    (the earliest birth) in front at 0 and tries every circular order of the rest, minimising the angle crossed by lifts between houses and by wefts between
    houses (so a kin loop stays inside one wedge of the drum); ties go to the order nearest the orb's."""
    def cost(ang): return sum(abs(wrap_angle(ang[b] - ang[a])) for a, b in lifts_h + cpl_h if a != b)
    orb = orb_angles(houses); n = len(houses)
    note = dict(mode=HOUSE_ORDER, orb_cost_rad=round(cost(orb), 4))
    if HOUSE_ORDER == 'orb' or n <= 2 or n > 8:
        note.update(cost_rad=note['orb_cost_rad'], order=sorted(houses, key=lambda h: orb[h])); return orb, note
    slots = [2 * PI * k / n for k in range(n)]; best = None
    for perm in itertools.permutations(houses[1:]):
        ang = dict(zip((houses[0],) + perm, slots))
        key = (round(cost(ang), 6), round(sum(abs(wrap_angle(ang[h] - orb[h])) for h in houses), 6), perm)
        if best is None or key < best[0]: best = (key, ang)
    note.update(cost_rad=best[0][0], order=sorted(houses, key=lambda h: best[1][h]), angles_deg={h: round(math.degrees(a), 1) for h, a in best[1].items()})
    return best[1], note


def surf(F, x, th, r):
    return (x, F['cy'] + r * math.sin(th), F['cz'] + r * math.cos(th))


def lift_points(F, M, P, parent, child, mode):
    """a parentage strand, N_LIFT points: loom = from the parent's thread (two years before the birth) to the child's bead; rings = bead to bead"""
    pp, cp = P[parent], P[child]; R = F['R']
    if mode == 'loom':
        ya = min(max(M[child]['born'] - LIFT_YEARS, M[parent]['born'] + 0.5), M[parent].get('died') or 9999)
        xa, xc = X(ya), cp['xb']
    else:
        xa, xc = pp['xg'], cp['xg']
    dth = wrap_angle(cp['theta'] - pp['theta']); h = 0.06 + 0.42 * abs(dth)
    out = []
    for k in range(N_LIFT):
        t = k / (N_LIFT - 1)
        out.append(surf(F, lerp(xa, xc, smooth(t)), pp['theta'] + dth * t, R + 0.02 + h * math.sin(PI * t)))
    return out


def weft_points(F, P, c, mode, lift=0.10):
    pa, pb = P[c['a']], P[c['b']]; R = F['R']
    dth = wrap_angle(pb['theta'] - pa['theta'])
    out = []
    for k in range(N_WEFT):
        t = k / (N_WEFT - 1)
        x = X(c['year']) if mode == 'loom' else lerp(pa['xg'], pb['xg'], t)
        out.append(surf(F, x, pa['theta'] + dth * t, R + lift + 0.10 * math.sin(PI * t)))
    return out


def thread_point(F, P, pid, x, mode, r_add=0.0):
    p = P[pid]; return surf(F, x if mode == 'loom' else p['xg'], p['theta'], F['R'] + r_add)


def loop_points(F, M, P, c, kin, mode):
    """the closed cycle of a marriage between kin: weft -> a's thread back to a's birth -> lifts up to the common ancestor -> along the ancestor's
    thread -> lifts down to b -> b's thread to the weft. Same point count in both modes."""
    A, B = ancestors(M, c['a']), ancestors(M, c['b']); g = kin['ancestor']
    def chain(anc, start):                           # start ... g, following the child-on-path links upward
        path = [start]
        while path[-1] != g:
            cur = path[-1]; ups = [p for p in M[cur]['parents'] if p in anc and anc[p][0] == anc[cur][0] + 1]
            ups.sort(key=lambda p: (p != g, M[p]['born'])); path.append(ups[0])
        return path
    ca, cb = chain(A, c['a']), chain(B, c['b'])
    xm = X(c['year'])
    pts = []
    pts.append(thread_point(F, P, c['a'], xm, mode, 0.05))                               # a at the weft
    for i in range(len(ca) - 1):                                                          # a's line upward
        kid, par = ca[i], ca[i + 1]
        pts.append(thread_point(F, P, kid, P[kid]['xb'], mode, 0.05))                     # along kid's thread back to its birth
        pts += [(q[0], q[1], q[2]) for q in reversed(lift_points(F, M, P, par, kid, mode))]
    down = []
    for i in range(len(cb) - 1, 0, -1):                                                   # g ... b downward
        par, kid = cb[i], cb[i - 1]
        down += lift_points(F, M, P, par, kid, mode)
        nxt = cb[i - 2] if i >= 2 else None
        xe = (X(min(max(M[nxt]['born'] - LIFT_YEARS, M[kid]['born'] + 0.5), M[kid].get('died') or 9999)) if nxt else xm)
        down.append(thread_point(F, P, kid, xe, mode, 0.05))
    pts += down
    pts += list(reversed(weft_points(F, P, c, mode, lift=0.13)))[1:]                       # b back to a across the weft
    return pts


# ---------------------------------------------------------------- X3D
PROTO = """<ProtoDeclare name='PersonBead' appinfo='One person on the loom: a bead at birth, the lit thread (the lifeline) to death along local +X, the short name written along the thread. A touch on any of them comes out as isActive.'>
      <ProtoInterface>
        <field accessType='inputOutput' name='translation' type='SFVec3f' value='0 0 0' appinfo='the birth point on the drum'/>
        <field accessType='inputOutput' name='rotation' type='SFRotation' value='0 0 1 0' appinfo='turns local +Z to the drum normal and local +Y to the house tangent'/>
        <field accessType='inputOutput' name='life' type='SFVec3f' value='1 1 1' appinfo='x is the length of the lifeline in scene units'/>
        <field accessType='initializeOnly' name='color' type='SFColor' value='0.8 0.7 0.4'/>
        <field accessType='initializeOnly' name='glow' type='SFColor' value='0.3 0.25 0.1'/>
        <field accessType='initializeOnly' name='label' type='MFString' value='""'/>
        <field accessType='initializeOnly' name='description' type='SFString' value=''/>
        <field accessType='outputOnly' name='isActive' type='SFBool'/>
      </ProtoInterface>
      <ProtoBody>
        <Transform>
          <IS><connect nodeField='translation' protoField='translation'/><connect nodeField='rotation' protoField='rotation'/></IS>
          <TouchSensor><IS><connect nodeField='description' protoField='description'/><connect nodeField='isActive' protoField='isActive'/></IS></TouchSensor>
          <Shape>
            <Appearance><Material DEF='BeadMat' specularColor='0.35 0.33 0.3' shininess='0.4'><IS><connect nodeField='diffuseColor' protoField='color'/><connect nodeField='emissiveColor' protoField='glow'/></IS></Material></Appearance>
            <Sphere radius='0.15'/>
          </Shape>
          <Transform><IS><connect nodeField='scale' protoField='life'/></IS>
            <Transform translation='0.5 0 0' rotation='0 0 1 -1.570796'>
              <Shape><Appearance><Material USE='BeadMat'/></Appearance><Cylinder radius='0.045' height='1' top='false' bottom='false'/></Shape>
            </Transform>
          </Transform>
          <Transform translation='0.2 0.1 0.06'>
            <Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='0.97 0.93 0.85'/></Appearance><Text><IS><connect nodeField='string' protoField='label'/></IS><FontStyle family='"SANS"' size='0.28' justify='"BEGIN" "FIRST"'/></Text></Shape>
          </Transform>
        </Transform>
      </ProtoBody>
    </ProtoDeclare>"""


class Scene:
    def __init__(self):
        self.out, self.routes, self.morph_targets = [], [], []

    def w(self, s, ind=4): self.out.append(' ' * ind + s)
    def route(self, fn, ff, tn, tf): self.routes.append("<ROUTE fromNode='%s' fromField='%s' toNode='%s' toField='%s'/>" % (fn, ff, tn, tf))


def lines_shape(defname, polylines, color, width, transparency=0.0, coord_def=None, ap_def=None, ap_use=None, mat_def=None):
    pts, idx = [], []
    for pl in polylines:
        b = len(pts); pts += pl; idx += list(range(b, b + len(pl))) + [-1]
    mat = "<Material%s diffuseColor='0 0 0' emissiveColor='%s'%s/>" % (" DEF='%s'" % mat_def if mat_def else '', v3(color), " transparency='%s'" % fm(transparency) if transparency else '')
    ap = ("<Appearance USE='%s'/>" % ap_use) if ap_use else "<Appearance%s>%s<LineProperties linewidthScaleFactor='%s'/></Appearance>" % (" DEF='%s'" % ap_def if ap_def else '', mat, fm(width))
    return ("<Shape%s>%s<IndexedLineSet coordIndex='%s'><Coordinate%s point='%s'/></IndexedLineSet></Shape>"
            % (" DEF='%s'" % defname if defname else '', ap, ' '.join(map(str, idx)), " DEF='%s'" % coord_def if coord_def else '', ' '.join(v3(p) for p in pts)))


def text_shape(strings, size, color, justify='"MIDDLE" "MIDDLE"', fs_def=None, fs_use=None, ap_def=None, ap_use=None):
    ap = "<Appearance USE='%s'/>" % ap_use if ap_use else "<Appearance%s><Material diffuseColor='0 0 0' emissiveColor='%s'/></Appearance>" % (" DEF='%s'" % ap_def if ap_def else '', v3(color))
    fs = "<FontStyle USE='%s'/>" % fs_use if fs_use else "<FontStyle%s family='\"SANS\"' size='%s' justify='%s'/>" % (" DEF='%s'" % fs_def if fs_def else '', fm(size), justify)
    return "<Shape>%s<Text string='%s'>%s</Text></Shape>" % (ap, xa(mfs(strings)), fs)


def morph_keys():
    """eased round trip for the generation-rings morph: out over the first quarter, held, back over the last quarter"""
    ks, vs = [], []
    for i in range(7): t = i / 6; ks.append(0.25 * t); vs.append(smooth(t))
    for i in range(7): t = i / 6; ks.append(0.75 + 0.25 * t); vs.append(1 - smooth(t))
    return ' '.join(fm(k) for k in ks), ' '.join(fm(v) for v in vs)


def build(datasets, title):
    order, L = layout(datasets)
    S = Scene(); A = dict(persons={}, viewpoints={}, loops=[], datasets={})
    stamp = datetime.date.today().isoformat()
    n_people = sum(len(L[d['id']]['ids']) for d in order)

    # ---------- the people, the lifts, the wefts, the loops: geometry for both layouts
    G = {}
    for d in order:
        F = L[d['id']]; M = d['members']; P = F['P']
        lifts = [(p, c) for c in sorted(F['ids'], key=lambda i: (M[i]['born'], i)) for p in M[c]['parents'] if p in M]
        loops = []
        for c in F['couples']:
            k = kinship(M, c['a'], c['b'])
            if k: c['kin'] = k; loops.append(c)
        G[d['id']] = dict(lifts=lifts, loops=loops)

    # ---------- viewpoints
    main = order[0]; FM = L[main['id']]
    xc = (FM['x0'] + FM['x1']) / 2; span = FM['x1'] - FM['x0']
    vps = []
    def vp_radial(name, desc, F, theta, xmid, dist, fov):
        pos = surf(F, xmid, theta, F['R'] + dist); ori = (1.0, 0.0, 0.0, -theta)
        vps.append((name, desc, pos, ori, surf(F, xmid, theta, 0.0), fov))
    ov_pos = (xc, FM['cy'] + 6.0, FM['cz'] + 23.0)
    vps.append(('VP_Loom', 'The loom', ov_pos, look_at(ov_pos, (xc, FM['cy'] - 0.4, 0)), (xc, FM['cy'], 0), 0.74))
    for h in FM['houses']:
        ids = [i for i in FM['ids'] if FM['P'][i]['house'] == h]
        a, b = min(FM['P'][i]['xb'] for i in ids), max(FM['P'][i]['xd'] for i in ids)
        dist = max(6.5, min(15.0, (b - a + 3.0) / 1.21 - 0.6))
        vp_radial('VP_' + re.sub(r'\W', '', h), h, FM, FM['ang'][h], (a + b) / 2 + 0.6, dist, 0.7)
    for c in G[main['id']]['loops']:
        pts = loop_points(FM, main['members'], FM['P'], c, c['kin'], 'loom')
        xs = [p[0] for p in pts]; ths = [math.atan2(p[1] - FM['cy'], p[2] - FM['cz']) for p in pts]
        mid_th = math.atan2(sum(math.sin(t) for t in ths), sum(math.cos(t) for t in ths))
        c['_vp'] = ('VP_Loop_%s_%s' % (c['a'], c['b']), 'Loop: %s and %s' % (short(main['members'], c['a']), short(main['members'], c['b'])))
        vp_radial(c['_vp'][0], c['_vp'][1], FM, mid_th, (min(xs) + max(xs)) / 2, max(6.5, (max(xs) - min(xs) + 4) / 1.21), 0.72)
    for d in order[1:]:
        F = L[d['id']]
        a, b = F['x0'], F['x1']
        vp_radial('VP_' + re.sub(r'\W', '', d['id']), d['name'], F, 0.25, (a + b) / 2, max(5.5, (b - a + 4) / 1.21), 0.7)

    # ---------- head and scene preamble
    meta = [('title', title + '.x3d'),
            ('description', 'Genealogy loom: every person a thread along a shared time axis, every house a sector of the drum (the React orb\'s directions), parentage as lifts, marriages as wefts, and a marriage between kin as a loop that runs back to the common ancestor. A scriptless morph re-registers the beads to generation rings. Generated; do not edit.'),
            ('generator', 'build_genealogy_x3d.py (prototype, ' + stamp + ')'),
            ('created', stamp),
            ('data', '; '.join('%s: %s' % (d['id'], ', '.join('%s (%s, sha256 %s)' % (s['file'], s['members'], s['sha256'][:12]) for s in d['sources'])) for d in order)),
            ('license', 'data as uploaded by the owner; dates and relations not checked against outside sources')]
    head = ["<?xml version='1.0' encoding='UTF-8'?>",
            "<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>",
            "  <head>", "    <component name='Shape' level='2'/>"] + ["    <meta name='%s' content='%s'/>" % (k, xa(v)) for k, v in meta] + ["  </head>", "  <Scene>"]
    S.w("<WorldInfo title='%s' info='%s'/>" % (xa(title), xa(mfs(['Primary layout: the loom drum (time along +X, houses as sectors).', 'Secondary layout: generation rings, by the morph (MorphClock).', 'Selection: touch a bead or its thread; touch the drum to clear.']))))
    S.w("<Background skyColor='%s'/>" % SKY)
    S.w("<NavigationInfo type='\"EXAMINE\" \"ANY\"' headlight='true' speed='4' transitionType='\"ANIMATE\"' transitionTime='1.6'/>")
    S.w(PROTO)
    S.w("<!-- Camera stops: the loom (bound at load), one per house (looking at the house's sector from outside: time runs left to right, the lanes stack up the screen), one per kin loop, one per bolt. -->")
    for name, desc, pos, ori, cen, fov in vps:
        S.w("<Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'/>" % (name, xa(desc), v3(pos), v3(ori), v3(cen), fm(fov)))
        A['viewpoints'][name] = dict(description=desc, position=[round(c, 5) for c in pos], orientation=[round(c, 6) for c in ori], center=[round(c, 4) for c in cen], fov=fov)
    S.w("<DirectionalLight direction='-0.3 -0.6 -0.75' intensity='0.35' color='1 0.95 0.86'/>")

    # ---------- HUD: the card of the picked person rides in front of the camera (ProximitySensor carries the transform; plain X3D, no Script)
    S.w("<ProximitySensor DEF='HudSense' size='100000 100000 100000'/>")
    card_choices = []
    world_choices = []
    lib = []                                                       # highlight shapes defined once (in a never-drawn Switch), USEd by every pick that needs them
    morph_interps = []                                             # (interpolator def, target def, target field) for the generation morph
    pindex = 0
    beads = []
    years_xml, ring_xml, frame_xml, lines_xml, gen_xml, pulse_xml, label_xml = [], [], [], [], [], [], []
    for d in order:
        F = L[d['id']]; M = d['members']; P = F['P']; did = re.sub(r'\W', '', d['id'])
        R = F['R']; Gd = G[d['id']]
        # drum, dividers, warp, year rings and labels, house labels
        length = F['x1'] - F['x0'] + 2.4; xm = (F['x0'] + F['x1']) / 2
        frame_xml.append("<Transform translation='%s' rotation='0 0 1 -1.570796'><Shape><Appearance><Material diffuseColor='0.10 0.085 0.075' emissiveColor='0.035 0.028 0.022' specularColor='0.08 0.07 0.05'/></Appearance><Cylinder radius='%s' height='%s'/></Shape></Transform>"
                         % (v3((xm, F['cy'], F['cz'])), fm(R - 0.035), fm(length)))
        if len(F['houses']) > 1:
            divs = [[surf(F, F['x0'] - 1.1, F['ang'][h] + s * F['sector'] / 2, R + 0.01), surf(F, F['x1'] + 1.1, F['ang'][h] + s * F['sector'] / 2, R + 0.01)] for h in F['houses'] for s in (-1,)]
            lines_xml.append(lines_shape(None, divs, tuple(c * 0.55 for c in GOLD), 1.0))
        warp = []
        for h in F['houses']:
            ids = [i for i in F['ids'] if P[i]['house'] == h]
            a, b = min(P[i]['xb'] for i in ids) - 0.6, max(P[i]['xd'] for i in ids) + 0.6
            lanes = sorted(set(P[i]['theta'] for i in ids))
            ths = [lanes[0] - F['lane_rad']] + lanes + [lanes[-1] + F['lane_rad']] if len(F['houses']) > 1 else lanes
            for th in ths: warp.append([surf(F, a, th, R + 0.005), surf(F, b, th, R + 0.005)])
            hc = F['col'][h]
            label_xml.append("<Transform translation='%s'><Billboard axisOfRotation='0 0 0'>%s</Billboard></Transform>"
                             % (v3(surf(F, a - 0.25, F['ang'][h], R + 0.4)), text_shape([h.upper()], 0.62 if F['main'] else 0.42, hc, '"END" "MIDDLE"')))
        lines_xml.append(lines_shape(None, warp, tuple(c * 0.38 for c in GOLD), 1.0))
        y0, y1 = int(math.ceil((F['x0'] / TS + YEAR_C) / 50.0)) * 50, int((F['x1'] / TS + YEAR_C) // 50) * 50
        rings = []
        for y in range(y0, y1 + 1, 50):
            rings.append([surf(F, X(y), 2 * PI * k / 72, R + 0.012) for k in range(73)])
            for h in F['houses']:
                th = F['ang'][h] + (0.5 * F['sector'] - 0.12 if len(F['houses']) > 1 else 0.35)
                years_xml.append("<Transform translation='%s' rotation='1 0 0 %s'>%s</Transform>"           # printed on the drum (a Billboard tilts into the solid drum)
                                 % (v3(surf(F, X(y) + 0.06, th, R + 0.03)), fm(-th), text_shape([str(y)], 0.36, None, fs_use='YearFont', ap_use='YearAp')
                                    if years_xml else text_shape([str(y)], 0.3, tuple(c * 0.78 for c in GOLD), '"BEGIN" "MIDDLE"', fs_def='YearFont', ap_def='YearAp')))
        if rings: ring_xml.append(lines_shape(None, rings, tuple(c * 0.75 for c in GOLD), 1.5))
        if not F['main']:                      # a bolt's name at its left end (the main drum is named by the page and by WorldInfo)
            label_xml.append("<Transform translation='%s'><Billboard axisOfRotation='0 0 0'>%s</Billboard></Transform>"
                             % (v3(surf(F, F['x0'] - 0.6, 0.0, R + 0.9)), text_shape([d['name']], 0.42, (0.96, 0.9, 0.78), '"END" "MIDDLE"')))
        # generation stations (secondary layout): labels shown only while the morph runs
        for g, yr in sorted(F['station'].items()):
            gen_xml.append("<Transform translation='%s'><Billboard axisOfRotation='0 0 0'>%s</Billboard></Transform>"
                           % (v3(surf(F, X(yr), 0.0, R + (1.6 if F['main'] else 1.0)) if F['main'] else surf(F, X(yr), 0.0, R + 1.0)),
                              text_shape(['gen. %s' % g], 0.42 if F['main'] else 0.3, (0.75, 0.92, 1.0))))
        # people
        for pid in sorted(F['ids'], key=lambda i: (M[i]['born'], i)):
            m = M[pid]; p = P[pid]; hc = F['col'][p['house']]
            pos = surf(F, p['xb'], p['theta'], R + 0.0); life = max(0.05, p['xd'] - p['xb'])
            pos_r = surf(F, p['xg'], p['theta'], R)
            nm = short(M, pid); dn = '%s, %s-%s, %s' % (m['name'], m['born'], m.get('died') or '', p['house'])
            bead = "P_%s_%s" % (did, re.sub(r'\W', '_', pid))
            beads.append("<ProtoInstance DEF='%s' name='PersonBead'><fieldValue name='translation' value='%s'/><fieldValue name='rotation' value='1 0 0 %s'/><fieldValue name='life' value='%s 1 1'/>"
                         "<fieldValue name='color' value='%s'/><fieldValue name='glow' value='%s'/><fieldValue name='label' value='%s'/><fieldValue name='description' value='%s'/></ProtoInstance>"
                         % (bead, v3(pos), fm(-p['theta']), fm(life), v3(tuple(c * 0.78 for c in hc)), v3(tuple(c * 0.32 for c in hc)), xa(mfs([nm])), xa(dn)))
            beads.append("<PositionInterpolator DEF='%s_at' key='0 1' keyValue='%s, %s'/><PositionInterpolator DEF='%s_len' key='0 1' keyValue='%s 1 1, 0.35 1 1'/>" % (bead, v3(pos), v3(pos_r), bead, fm(life)))
            morph_interps += [(bead + '_at', bead, 'translation'), (bead + '_len', bead, 'life')]
            A['persons'][pid] = dict(index=pindex, dataset=d['id'], name=m['name'], short=nm, house=p['house'], lane=p['lane'], theta=round(p['theta'], 5), bead=[round(c, 5) for c in pos],
                                     born=m['born'], died=m.get('died'), generation=m.get('generation'), rings=[round(c, 5) for c in pos_r], def_=bead)
            # the pick: trigger, card, world highlight
            trig = 'Pick_%d' % pindex
            beads.append("<IntegerTrigger DEF='%s' integerKey='%d'/>" % (trig, pindex))
            S.route(bead, 'isActive', trig, 'set_boolean'); S.route(trig, 'triggerValue', 'PickedWorld', 'set_whichChoice'); S.route(trig, 'triggerValue', 'PickedCard', 'set_whichChoice')
            card_choices.append(card(d, F, M, pid, Gd))
            world_choices.append((d['id'], pid))
            pindex += 1
        # lifts, wefts, loops (both layouts, for the morph)
        odd = lambda a, b: M[a].get('generation') is not None and M[b].get('generation') is not None and M[b]['generation'] - M[a]['generation'] != 1
        for tag, sel in (('Lift', [(a, b) for a, b in Gd['lifts'] if not odd(a, b)]), ('LiftOdd', [(a, b) for a, b in Gd['lifts'] if odd(a, b)])):
            if not sel: continue
            lift_l = [lift_points(F, M, P, a, b, 'loom') for a, b in sel]; lift_r = [lift_points(F, M, P, a, b, 'rings') for a, b in sel]
            mat = '%sMat_%s' % (tag, did) if tag == 'LiftOdd' else None
            lines_xml.append(lines_shape(None, lift_l, LIFT_C, 2.2, coord_def='%sCoord_%s' % (tag, did), mat_def=mat))
            morph_interps.append(coord_interp('%sCoord_%s' % (tag, did), lift_l, lift_r))
            if mat:
                morph_interps.append(["<ColorInterpolator DEF='%sTint_%s' key='0 1' keyValue='%s, %s'/>" % (tag, did, v3(LIFT_C), v3(ODD_C)), '%sTint_%s' % (tag, did), mat, 'set_emissiveColor'])
                A.setdefault('odd_lifts', []).extend(dict(dataset=d['id'], parent=a, child=b, parent_generation=M[a].get('generation'), generation=M[b].get('generation')) for a, b in sel)
        real = [c for c in F['couples'] if not c['estimated']]; est = [c for c in F['couples'] if c['estimated']]
        for grp, tr, tag in ((real, 0.0, 'Weft'), (est, 0.55, 'WeftEst')):
            if not grp: continue
            wl = [weft_points(F, P, c, 'loom') for c in grp]; wr = [weft_points(F, P, c, 'rings') for c in grp]
            lines_xml.append(lines_shape(None, wl, WEFT_C, 4.0, transparency=tr, coord_def='%sCoord_%s' % (tag, did)))
            morph_interps.append(coord_interp('%sCoord_%s' % (tag, did), wl, wr))
        if Gd['loops']:
            ll = [loop_points(F, M, P, c, c['kin'], 'loom') for c in Gd['loops']]; lr = [loop_points(F, M, P, c, c['kin'], 'rings') for c in Gd['loops']]
            lines_xml.append(lines_shape(None, ll, LOOP_C, 4.5, coord_def='LoopCoord_' + did))
            morph_interps.append(coord_interp('LoopCoord_' + did, ll, lr))
            for j, (c, pts) in enumerate(zip(Gd['loops'], ll)):
                pulse_xml.append(pulse('Pulse_%s_%d' % (did, j), pts, 9.0 + 2.0 * j, S))
                knot = weft_points(F, P, c, 'loom')[N_WEFT // 2]
                rel = c['kin']['relation']
                label_xml.append("<Transform translation='%s'><Billboard axisOfRotation='0 0 0'>%s</Billboard></Transform>"
                                 % (v3(surf(F, X(c['year']) + 0.15, P[c['a']]['theta'] - 1.6 * F['lane_rad'], R + 0.45)),
                                    text_shape(['weft loops back:', rel.split(' (')[0] if 'cousins' in rel else 'uncle/aunt and niece/nephew'], 0.24, (1.0, 0.72, 0.42), '"BEGIN" "FIRST"')))
                A['loops'].append(dict(dataset=d['id'], a=c['a'], b=c['b'], year=c['year'], ancestor=c['kin']['ancestor'], co_ancestors=c['kin']['co_ancestors'],
                                       relation=rel, points=len(pts), viewpoint=c.get('_vp', [None])[0]))
        A['datasets'][d['id']] = dict(name=d['name'], R=R, center=[F['x0'], F['cy'], F['cz']], x0=round(F['x0'], 3), x1=round(F['x1'], 3), houses={h: round(F['ang'][h], 4) for h in F['houses']},
                                      lane_deg=round(math.degrees(F['lane_rad']), 3), stations={str(g): y for g, y in F['station'].items()}, couples=[{k: v for k, v in c.items() if not k.startswith('_')} for c in F['couples']])

    # ---------- the highlight library: every lift as a bright line, every lifeline as a bright line; each pick USEs the ones on its lineage
    lib_defs = {}
    for d in order:
        F = L[d['id']]; M = d['members']; P = F['P']; did = re.sub(r'\W', '', d['id'])
        for a, b in G[d['id']]['lifts']:
            nm = 'HL_%s_%s_%s' % (did, re.sub(r'\W', '_', a), re.sub(r'\W', '_', b))
            lib.append(lines_shape(nm, [lift_points(F, M, P, a, b, 'loom')], HI_C, 3.6, **({'ap_use': 'HiAp'} if lib else {'ap_def': 'HiAp'}))); lib_defs[(d['id'], a, b)] = nm
        for pid in F['ids']:
            nm = 'HT_%s_%s' % (did, re.sub(r'\W', '_', pid)); p = P[pid]
            lib.append(lines_shape(nm, [[surf(F, p['xb'], p['theta'], F['R'] + 0.06), surf(F, p['xd'], p['theta'], F['R'] + 0.06)]], HI_C, 3.6, **({'ap_use': 'HiAp'} if lib else {'ap_def': 'HiAp'}))); lib_defs[(d['id'], pid)] = nm
    picks = []
    for did_, pid in world_choices:                       # the lineage of a pick: the person's own thread, every ancestor's and descendant's thread, and the lifts between them
        d = datasets[did_]; F = L[did_]; M = d['members']; P = F['P']
        up = ancestors(M, pid); down = descendants(M, pid)
        uses = ["<Shape USE='%s'/>" % lib_defs[(did_, pid)]]
        uses += ["<Shape USE='%s'/>" % lib_defs[(did_, a, b)] for a, b in G[did_]['lifts'] if (a in up and b in up) or (a in down and b in down)]
        uses += ["<Shape USE='%s'/>" % lib_defs[(did_, x)] for x in sorted((set(up) | down) - {pid})]
        bp = surf(F, P[pid]['xb'], P[pid]['theta'], F['R'])
        picks.append("<Group><Transform translation='%s'><Billboard axisOfRotation='0 0 0'><Shape USE='Halo'/></Billboard></Transform>%s</Group>" % (v3(bp), ''.join(uses)))
    world_choices = picks

    halo_def = "<Shape DEF='Halo'><Appearance><Material diffuseColor='0 0 0' emissiveColor='%s'/><LineProperties linewidthScaleFactor='3'/></Appearance><IndexedLineSet coordIndex='%s -1'><Coordinate point='%s'/></IndexedLineSet></Shape>" % (
        v3(HI_C), ' '.join(str(k) for k in range(41)), ' '.join(v3((0.34 * math.cos(2 * PI * k / 40), 0.34 * math.sin(2 * PI * k / 40), 0)) for k in range(41)))

    S.w("<!-- The fabric: drums (translucent), dividers between houses, the warp, the year rings and their labels. Touch the drum to clear the pick. -->")
    S.w("<Group DEF='Drums'>%s<TouchSensor DEF='DrumTouch' description='clear the pick'/></Group>" % ''.join(frame_xml))
    S.w("<IntegerTrigger DEF='Unpick' integerKey='-1'/>")
    S.route('DrumTouch', 'isActive', 'Unpick', 'set_boolean'); S.route('Unpick', 'triggerValue', 'PickedWorld', 'set_whichChoice'); S.route('Unpick', 'triggerValue', 'PickedCard', 'set_whichChoice')
    S.w("<Group DEF='Fabric'>%s</Group>" % ''.join(lines_xml))
    S.w("<Group DEF='Years'>%s%s</Group>" % (''.join(ring_xml), ''.join(years_xml)))
    S.w("<Group DEF='Labels'>%s</Group>" % ''.join(label_xml))
    S.w("<Group DEF='GenLabels' visible='false'>%s</Group>" % ''.join(gen_xml))
    S.w("<!-- The people: one PersonBead each, its morph interpolators and its pick trigger. -->")
    S.w("<Group DEF='People'>")
    for b in beads: S.w(b, 6)
    S.w("</Group>")
    S.w("<Group DEF='Pulses'>%s</Group>" % ''.join(pulse_xml))
    S.w("<!-- Highlight library: never drawn itself (whichChoice -1); the picks below USE its lines. -->")
    S.w("<Switch DEF='Library' whichChoice='-1'><Group>%s%s</Group></Switch>" % (halo_def, ''.join(lib)))
    S.w("<Switch DEF='PickedWorld' whichChoice='-1'>")
    for c in world_choices: S.w(c, 6)
    S.w("</Switch>")
    S.w("<Transform DEF='Hud'><Transform translation='-1.72 -0.98 -3'><Switch DEF='PickedCard' whichChoice='-1'>")
    for c in card_choices: S.w(c, 6)
    S.w("</Switch></Transform></Transform>")
    S.route('HudSense', 'position_changed', 'Hud', 'set_translation'); S.route('HudSense', 'orientation_changed', 'Hud', 'set_rotation')
    # the morph button and the morph
    FM = L[order[0]['id']]
    bpos = (FM['x1'] + 0.4, FM['cy'] + FM['R'] + 1.4, FM['cz'])
    S.w("<Transform DEF='RingsButton' translation='%s'><Billboard axisOfRotation='0 0 0'><TouchSensor DEF='RingsTouch' description='slide every bead to its generation ring and back'/>%s"
        "<Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='0.10 0.16 0.20' transparency='0.25'/></Appearance><IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1'><Coordinate point='-0.15 -0.32 -0.02 3.45 -0.32 -0.02 3.45 0.42 -0.02 -0.15 0.42 -0.02'/></IndexedFaceSet></Shape></Billboard></Transform>"
        % (v3(bpos), text_shape(['generation rings'], 0.36, (0.75, 0.92, 1.0), '"BEGIN" "MIDDLE"')))
    ks, vs = morph_keys()
    S.w("<TimeSensor DEF='MorphClock' cycleInterval='%s' loop='false'/><ScalarInterpolator DEF='MorphPhase' key='%s' keyValue='%s'/><BooleanFilter DEF='MorphHide'/>" % (fm(MORPH_S), ks, vs))
    for x in morph_interps:
        if isinstance(x, list): S.w(x[0])
    S.route('RingsTouch', 'touchTime', 'MorphClock', 'set_startTime')
    S.route('MorphClock', 'fraction_changed', 'MorphPhase', 'set_fraction')
    S.route('MorphClock', 'isActive', 'MorphHide', 'set_boolean')
    for tgt in ('PickedWorld', 'Pulses', 'Years'): S.route('MorphHide', 'inputNegate', tgt, 'set_visible')
    S.route('MorphClock', 'isActive', 'GenLabels', 'set_visible')
    for x in morph_interps:
        if isinstance(x, tuple): idef, tdef, tf = x
        else: idef, tdef, tf = x[1], x[2], (x[3] if len(x) > 3 else 'set_point')
        S.route('MorphPhase', 'value_changed', idef, 'set_fraction'); S.route(idef, 'value_changed', tdef, tf)

    body = '\n'.join(S.out)
    text = '\n'.join(head) + '\n' + body + '\n    <!-- ROUTEs: all after the nodes they name. -->\n' + '\n'.join('    ' + r for r in S.routes) + '\n  </Scene>\n</X3D>\n'
    A['counts'] = dict(people=n_people, routes=len(S.routes), viewpoints=len(vps), cards=len(card_choices), morph_interpolators=len(morph_interps))
    return text, A, order, L, G


def descendants(M, pid):
    out = {pid}; frontier = [pid]
    while frontier:
        nxt = [c for c in M if any(p in frontier for p in M[c]['parents']) and c not in out]
        out |= set(nxt); frontier = nxt
    return out


def coord_interp(coord_def, loom, rings):
    a = [p for pl in loom for p in pl]; b = [p for pl in rings for p in pl]
    assert len(a) == len(b), (coord_def, len(a), len(b))
    nm = coord_def.replace('Coord', 'Morph')
    return ["<CoordinateInterpolator DEF='%s' key='0 1' keyValue='%s %s'/>" % (nm, ' '.join(v3(p) for p in a), ' '.join(v3(p) for p in b)), nm, coord_def]


def pulse(defname, pts, period, S):
    """a bead of light running round a kin loop (keys by arc length), like the gobbler's flywheel pulses"""
    acc = [0.0]
    for i in range(1, len(pts)): acc.append(acc[-1] + math.dist(pts[i - 1], pts[i]))
    tot = acc[-1] + math.dist(pts[-1], pts[0]); keys = [a / tot for a in acc] + [1.0]; vals = pts + [pts[0]]
    S.route(defname + 'Clock', 'fraction_changed', defname + 'Path', 'set_fraction'); S.route(defname + 'Path', 'value_changed', defname, 'set_translation')
    return ("<Transform DEF='%s' translation='%s'><Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='1 0.9 0.6'/></Appearance><Sphere radius='0.11'/></Shape></Transform>"
            "<TimeSensor DEF='%sClock' cycleInterval='%s' loop='true'/><PositionInterpolator DEF='%sPath' key='%s' keyValue='%s'/>"
            % (defname, v3(pts[0]), defname, fm(period), defname, ' '.join(fm(k) for k in keys), ', '.join(v3(p) for p in vals)))


def card(d, F, M, pid, Gd):
    """the HUD card of one person: a dark panel and lines of text, in HUD units (about 0.05 per line)"""
    m = M[pid]; p = F['P'][pid]
    lines = ['%s-%s  ·  %s  ·  generation %s' % (m['born'], m.get('died') or '', p['house'], m.get('generation', '?'))]
    lines += wrap(m.get('note') or '(no note in the data)', 52)
    par = [short(M, x) for x in m['parents'] if x in M]
    lines.append('parents: ' + (', '.join(par) if par else 'not in the data'))
    for c in F['couples']:
        if pid in (c['a'], c['b']):
            o = c['b'] if c['a'] == pid else c['a']
            lines.append('married %s · weft at %s%s' % (short(M, o), c['year'], ' (estimated)' if c['estimated'] else ' (year before the first child)'))
            if c.get('kin'):
                k = c['kin']; anc = ' and '.join(short(M, x) for x in k['co_ancestors'])
                lines.append(('kin: %s' % k['relation']) if 'sibling' in k['relation'] else 'kin: %s, both descended from %s' % (k['relation'], anc))
    kids = sorted((c for c in M if pid in M[c]['parents']), key=lambda c: M[c]['born'])
    if kids: lines.append('children in the data: ' + ', '.join(short(M, c) for c in kids))
    width = max(len(m['name']) * 0.075 * 0.56, max(len(l) for l in lines) * 0.05 * 0.5) + 0.12
    height = 0.075 * 1.25 + len(lines) * 0.05 * 1.2 + 0.1
    panel = ("<Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='0.045 0.04 0.036' transparency='0.06'/></Appearance><IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1'><Coordinate point='%s'/></IndexedFaceSet></Shape>"
             % ' '.join(v3(q) for q in ((-0.06, -0.06, -0.01), (width, -0.06, -0.01), (width, height - 0.04, -0.01), (-0.06, height - 0.04, -0.01))))
    hc = F['col'][p['house']]
    name = "<Transform translation='0 %s 0'>%s</Transform>" % (fm(height - 0.04 - 0.075 * 1.05), text_shape([m['name']], 0.075, hc, '"BEGIN" "FIRST"'))
    body = "<Transform translation='0 %s 0'>%s</Transform>" % (fm(height - 0.04 - 0.075 * 1.25 - 0.05 * 1.05), text_shape(lines, 0.05, None, fs_use='CardFont', ap_use='CardAp')
                                                              if card.made else text_shape(lines, 0.05, (0.94, 0.9, 0.82), '"BEGIN" "FIRST"', fs_def='CardFont', ap_def='CardAp'))
    card.made = True
    return "<Group>%s%s%s</Group>" % (panel, name, body)
card.made = False


# ---------------------------------------------------------------- static checks (what X_ITE needs and the fork validator may not see)
def static_checks(text):
    """well-formed; DEF names unique in the scene (ProtoBody is its own namespace); every USE after its DEF; every ROUTE after both nodes it names"""
    root = ET.fromstring(text.encode('utf-8')); scene = root.find('Scene'); errs = []
    seen, order = {}, 0
    def walk(el, ns, in_proto):
        nonlocal order
        for ch in el:
            order += 1
            if ch.tag == 'ProtoDeclare':
                walk(ch, {}, True); continue
            if ch.tag == 'ROUTE':
                for k in ('fromNode', 'toNode'):
                    if ch.get(k) not in ns: errs.append('ROUTE %s=%s before (or without) its node' % (k, ch.get(k)))
                continue
            if ch.get('DEF'):
                if ch.get('DEF') in ns: errs.append('DEF %s twice' % ch.get('DEF'))
                ns[ch.get('DEF')] = order
            if ch.get('USE') and ch.get('USE') not in ns: errs.append('USE %s before its DEF' % ch.get('USE'))
            walk(ch, ns, in_proto)
    walk(scene, seen, False)
    return errs, root


def count_scene(root):
    scene = root.find('Scene'); NOT = {'ROUTE', 'field', 'fieldValue', 'IS', 'connect', 'ProtoInterface', 'ProtoBody'}
    els = [e for e in scene.iter() if e is not scene]; nodes = [e for e in els if e.tag not in NOT]
    return dict(profile=root.get('profile'), x3dVersion=root.get('version'), components=[dict(name=c.get('name'), level=int(c.get('level'))) for c in root.iter('component')],
                nodeCount=sum(1 for e in nodes if not e.get('USE')), defCount=sum(1 for e in nodes if e.get('DEF')), useCount=sum(1 for e in nodes if e.get('USE')),
                routeCount=sum(1 for e in els if e.tag == 'ROUTE'), protoInstances=sum(1 for e in els if e.tag == 'ProtoInstance'), viewpoints=sum(1 for e in els if e.tag == 'Viewpoint'),
                textNodes=sum(1 for e in els if e.tag == 'Text'), interpolators=sum(1 for e in nodes if e.tag.endswith('Interpolator') and not e.get('USE')),
                sensors=sorted({e.tag for e in nodes if e.tag.endswith('Sensor')}))


def run_validators(path, mcp):
    """xmllint (well-formed, then the X3D 4.0 XSD from the fork's schemas) and the x3d_mcp fork (XSD, semantic, profile), as the gobbler builds do"""
    out = {}
    r = subprocess.run(['xmllint', '--noout', path], capture_output=True, text=True); out['xmllint_wellformed'] = dict(ok=r.returncode == 0, stderr=r.stderr[-800:])
    xsd = os.path.join(mcp, 'src', 'validation', 'schemas', 'x3d-4.0.xsd')
    if os.path.exists(xsd):
        r = subprocess.run(['xmllint', '--noout', '--schema', xsd, path], capture_output=True, text=True)
        out['xmllint_xsd'] = dict(ok=r.returncode == 0, schema='x3d-4.0.xsd from the fork checkout', errors=[l for l in r.stderr.splitlines() if 'validates' not in l][:12])
    if os.path.exists(os.path.join(mcp, 'src', 'validation', 'validate.py')):
        env = dict(os.environ, X3D_MCP=mcp)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'tools', 'validate_fork.py'), path], capture_output=True, text=True, env=env, timeout=600)
        try:
            data = json.loads(r.stdout); sem = data['semantic']
            mm = re.search(r'Found (\d+) error\(s\), (\d+) warning\(s\), (\d+) info\(s\)', sem)
            errs, warns, infos = (int(x) for x in mm.groups()) if mm else ((0, 0, 0) if 'No semantic issues found' in sem else (None, None, None))
            head = subprocess.run(['git', '-C', mcp, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
            out['fork'] = dict(label='x3d_mcp fork, commit ' + head, commit=head, xsd_valid=data['xsd_valid'], xsd_errors=data['xsd_errors'], profile_ok=data['profile_ok'],
                               profile=data['profile'][:600], semantic_errors=errs, semantic_warnings=warns, semantic_infos=infos,
                               semantic_lines=[l.strip() for l in sem.splitlines() if re.search(r'ERROR|WARN', l)][:20])
        except Exception as e:
            out['fork'] = dict(error=repr(e), stdout=r.stdout[-1500:], stderr=r.stderr[-1500:])
    return out


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith('-'): raise SystemExit(__doc__)
    trees = [x for x in a if x.endswith('.json')]
    opt = lambda k, dflt: a[a.index(k) + 1] if k in a else dflt
    out_dir = os.path.abspath(opt('--out', HERE)); name = opt('--name', 'genealogy'); mcp = opt('--x3d-mcp', os.environ.get('X3D_MCP', '/home/user/x3d_mcp'))
    global HOUSE_ORDER
    HOUSE_ORDER = opt('--house-order', HOUSE_ORDER)
    os.makedirs(out_dir, exist_ok=True)
    datasets = load_trees(trees)
    notes = {k: check_data(d) for k, d in datasets.items()}
    text, A, order, L, G = build(datasets, 'Genealogy loom')
    errs, root = static_checks(text)
    path = os.path.join(out_dir, name + '.x3d'); raw = text.encode('utf-8')
    open(path, 'wb').write(raw); gz = gzip.compress(raw, 9, mtime=0); open(path + '.gz', 'wb').write(gz)
    json.dump(A, open(os.path.join(out_dir, name + '-anchors.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    stats = count_scene(root)
    rec = dict(file=name + '.x3d', bytes=len(raw), gz_bytes=len(gz), sha256=hashlib.sha256(raw).hexdigest(), generated=datetime.date.today().isoformat(),
               generator=dict(file=os.path.basename(__file__), sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest()), **stats,
               static_checks=dict(ok=not errs, errors=errs[:20], checks=['well-formed (ElementTree)', 'DEF unique per namespace', 'USE after DEF', 'ROUTE after both nodes']),
               data=dict(datasets={d['id']: dict(name=d['name'], people=len(d['members']), sources=d['sources'], added_per_source=d['added'],
                                                 conflicts=d['conflicts'], notes=notes[d['id']]) for d in order}),
               layout=dict(primary='loom drum: time along +X (%s units per year, %d at x=0), house = sector at the React orb angle, person = thread born..died' % (TS, YEAR_C),
                           secondary='generation rings by morph (MorphClock %s s round trip)' % MORPH_S, lane_spacing_deg=LANE_DEG, drum_radius=R_MAIN, bolt_radius=R_BOLT,
                           house_order={d['id']: L[d['id']]['house_order'] for d in order}, odd_lifts=A.get('odd_lifts', []), loops=A['loops'], counts=A['counts']))
    print(json.dumps({k: rec[k] for k in ('bytes', 'gz_bytes', 'nodeCount', 'defCount', 'useCount', 'routeCount', 'protoInstances', 'viewpoints', 'textNodes', 'interpolators')}))
    print('static checks:', 'ok' if not errs else errs[:10])
    if '--validate' in a:
        rec['validators'] = run_validators(path, mcp)
        v = rec['validators']; print('xmllint well-formed:', v['xmllint_wellformed']['ok'], '| xmllint XSD:', v.get('xmllint_xsd', {}).get('ok'), v.get('xmllint_xsd', {}).get('errors', [])[:3])
        f = v.get('fork', {}); print('fork:', json.dumps({k: f.get(k) for k in ('label', 'xsd_valid', 'profile_ok', 'semantic_errors', 'semantic_warnings', 'semantic_infos', 'error')}))
        if f.get('semantic_lines'): print('\n'.join(f['semantic_lines'][:12]))
        clean = not errs and v['xmllint_wellformed']['ok'] and v.get('xmllint_xsd', {}).get('ok') and f.get('xsd_valid') and f.get('profile_ok') and f.get('semantic_errors') == 0 and f.get('semantic_warnings') == 0
        rec['gate_static'] = 'clean' if clean else 'NOT CLEAN'
        if not clean: print('NOT CLEAN: receipt written with the failures recorded (receipt.gate_static)')
    json.dump(rec, open(os.path.join(out_dir, name + '-receipt.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('wrote', path, len(raw), 'bytes;', len(gz), 'gzipped')


if __name__ == '__main__':
    main()
