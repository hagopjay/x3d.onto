#!/usr/bin/env python3
"""Tapestry loom, layout v2: a loom-view/1 file (proto/contracts/loom-view.md) -> one X3D 4.0 scene per family, a person-card sidecar per family,
a manifest the page reads, the page itself (copied from page/index.html after a check) and a receipt. Deterministic, standard library only.
Never hand-edit an output: change this script (or the data) and rebuild.

    python3 -I build_loom_scene.py [LOOM_VIEW.json] [--out DIR] [--validate] [--frame-url URL] [--date YYYY-MM-DD]

The build date in each scene's generator and created metas is --date, else SOURCE_DATE_EPOCH (UTC), else today (drum.build_date);
tools/rebuild.py passes the release's date, so a rebuild matches the release on any day.

LOOM_VIEW defaults to data/loom-view.json when it exists, else the development adapter's dev/loom-view.json (adapt_harvest.py).
The merged file is read unchanged.

THE GRAMMAR (reports/07-narrative-ux.md, the cloth on the loom)
  * Time runs UP the cloth (TY units per year from the family's first quarter-century). Houses stand WEST TO EAST by their seat's longitude;
    latitude is a small DEPTH (north is farther from the viewer, KZ units per degree). Generation is a label on the card, never a coordinate.
  * Each life is an upright WARP thread from birth (a bead) to death. It bends only when the person moves: a core member whose parent's
    house (at the birth) differs from their own house starts in the parent's column and moves. A move rides the wedding pick when the spouse
    was already a core member of that house at the wedding (a bride crossing Europe); otherwise it is drawn as a short slant at age 21 or the
    wedding, whichever is first (estimated: the data gives only the adult house).
  * Each marriage is a level WEFT pick at the wedding year, DOUBLED when the couple share founders in the data (close: phi > 0); a pick whose year
    the data does not give is drawn translucent at an estimate (fill_union_years: the year before the first common child, else the younger
    spouse's 25th year, never after the first death), and its labels and card say so.
  * DYE: a thread is undyed ecru mixed toward each dye's colour by the person's share of descent from that dye's founders (founders 1, in-laws 0,
    a child the mean of its parents). A core member with no parent in the data and no share is DASHED (descent not linked in the data), as is a
    life whose death year the data does not give. An in-law's thread is faint until the first wedding (entering at the selvedge).
  * The FELL is the present-year plane: woven cloth below it, the bare warp above it (two ClipPlanes, set by the page).
  * Tour STOPS are report 07's twelve where the data supports them (description = the stop title), plus Wide. Each stop carries its own flat
    labels (at most MAX_NAMES names plus the house and year rails), facing that stop's camera and sized for it, placed and measured here so that
    no two overlap at the design viewport and all sit inside the page's safe area; the gate re-measures them in X_ITE from Text.textBounds.

X3D: profile Immersive 4.0 + Shape 2 (LineProperties) + Rendering 5 (ClipPlane). No Script and no ROUTE: the page drives everything through the
SAI (bind a stop, switch its labels, move the fell, highlight a pick); person cards live in the JSON sidecar, not in the scene. One TouchSensor
over the cloth; the page maps its hitPoint to the nearest thread in the house plane it hit (threads and house panels are coplanar per house)."""
import datetime, gzip, hashlib, json, math, os, re, subprocess, sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(HERE)
X3D_MCP = os.environ.get('X3D_MCP', '/home/user/hagopjay/x3d_mcp')   # the x3d_mcp fork: its XSD and validator (only with --validate)
FORK_PY = os.environ.get('LOOM_FORK_PYTHON', 'python3')               # a Python with the fork's dependencies, for tools/validate_x3d.py
sys.path.insert(0, os.path.join(PROTO, 'x3d'))
import build_genealogy_x3d as drum          # reused from the drum generator: number/XML helpers, look_at basis, static checks, scene counts
fm, v3, xa, mfs = drum.fm, drum.v3, drum.xa, drum.mfs

# ---------------------------------------------------------------- parameters
TY = 0.1                 # units per year, up
LX = 0.32                # lane spacing inside a house column
HOUSE_GAP = 1.5          # gap between house columns
KZ = 0.22                # depth per degree of latitude (north is farther: -z)
LANE_GAP = 3             # a lane is free again this many years after its thread ends
AGE_MOVE = 21            # a move with no record and no marriage into the destination house is drawn at this age, DOTTED, and its year is kept out of captions
MOVE_SLANT = 6           # years such an estimated move slants over (it reads as a guess, not as a level pick)
UNKNOWN_LIFE = 60        # a thread with no death year runs this long, dashed
BEAD = 0.075             # half-size of the birth bead (a flat diamond)
KX_TARGET, KX_MAX = 1.2, 3.5   # a cloth narrower than KX_TARGET (width / height) is widened (lanes and gaps) up to KX_MAX times: Habsburg's 700 years
W, H = 1527, 923         # design viewport (the gate's, the owner's still size)
FOV = 0.72               # the oblique Wide stop (depth reads there)
FOV_FRONT = 0.24         # every front stop: a long lens, so that a thread's year reads true against the year rail whatever its house's depth
SAFE = dict(x0=26, x1=W - 86, y0=80, y1=H - 210)     # index.html: header 64 px, stop rail 74 px at the right, caption strip 200 px at the bottom
PW, PH = 390, 844        # the phone viewport (portrait): each stop has its own phone viewpoint and labels, so names stay >= 12 px there
PSAFE = dict(x0=16, x1=PW - 16, y0=82, y1=PH - 226)  # index.html at max-width 720: header about 70 px, stop rail and caption strip about 220 px
NAME_PX, AXIS_PX = 20.0, 20.0     # nominal font px at the design viewport; X_ITE's drawn cap height is about 0.62 of it, so >= 12 px
MAX_NAMES, MAX_NAMES_PHONE = 12, 6
NEAR_DY = (0.0, 0.55, -0.55)      # a name, pick or note label sits on its thread's row (at most half a line off), or is left out
FAR_DY = (1.35, -1.35, 2.7, -2.7, 4.05, -4.05)   # only a stop's subject may sit farther, and then it gets a leader line to its thread
LEADER_PX = 40.0         # a label box farther than this from its anchor (or more than half a line off its row) needs a leader
AVATAR = 2.0             # NavigationInfo avatarSize[0]: X_ITE's near plane is half of it; the long lens puts cameras far out, so keep depth precision
CHAR_W = 0.5             # Ubuntu Mono (X_ITE's TYPEWRITER) advance, in em
FONT_FILE = 'fonts/UbuntuMono-R.ttf'   # the same Ubuntu Mono as plain TTF, written beside the scenes: X_ITE reads a TTF directly, while its own WOFF2
                                      # needs a decoder it runs through new Function, which a page CSP without 'unsafe-eval' (an Artifact) refuses.
                                      # Listed first in FontStyle.family; "TYPEWRITER" stays as the fallback for any other X3D browser.
CHIP_Y, CHIP_PAD = 0.62, 0.32
NEW_LANE_COST = 1.25

ECRU = (0.89, 0.85, 0.76)
SKY = '0.057 0.05 0.047'
GOLD = (0.84, 0.70, 0.36)
WEFT_C = (0.80, 0.76, 0.68)
CLOSE_C = (0.97, 0.94, 0.86)      # a close pick is doubled and brighter, never a dye colour: an orange-red pick hid the red that returns in the threads
TOUR_C = (0.80, 0.84, 0.90)       # the tour's silver thread: the line of descent from a founder to the stop's subject, and the subject's ring
SUBJ_C = (0.86, 0.92, 1.0)        # the subject's name label
NAME_C = (0.95, 0.92, 0.85)
FOCUS_C = (1.0, 0.98, 0.92)
YEAR_C = (0.74, 0.63, 0.42)
UNION_C = (1.0, 0.70, 0.52)
NOTE_C = (0.98, 0.62, 0.55)
PANEL_C = (0.072, 0.064, 0.058)
BAND_C = (0.098, 0.086, 0.076)
GRID_C = (0.19, 0.155, 0.10)
SEL_C = (1.0, 0.95, 0.78)


def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def mix(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))


def _lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def _gam(c): c = max(0.0, min(1.0, c)); return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
_WP = (0.95047, 1.0, 1.08883)


def lab(rgb):
    """sRGB (0..1) to CIELAB (D65)"""
    r, g, b = [_lin(c) for c in rgb]
    xyz = (0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b, 0.0193 * r + 0.1192 * g + 0.9505 * b)
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (xyz[0] / _WP[0], xyz[1] / _WP[1], xyz[2] / _WP[2])]
    return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))


def lab_rgb(L_, a_, b_, clip=True):
    fy = (L_ + 16) / 116; fx, fz = fy + a_ / 500, fy - b_ / 200
    inv = lambda t: t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787
    X, Y_, Z = inv(fx) * _WP[0], inv(fy) * _WP[1], inv(fz) * _WP[2]
    lin = (3.2406 * X - 1.5372 * Y_ - 0.4986 * Z, -0.9689 * X + 1.8758 * Y_ + 0.0415 * Z, 0.0557 * X - 0.2040 * Y_ + 1.0570 * Z)
    if not clip: return lin
    return tuple(_gam(c) for c in lin)


def delta_e(c1, c2):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(lab(c1), lab(c2))))


DYE_L = 54.0      # every dye is drawn at this lightness at full share: on the near-black cloth a dark dye (Darwin green) would sink, and a pale one would read as ecru


def dye_top_lab(hexc):
    """the dye at full share, in CIELAB: the data's hue, lightness DYE_L, its chroma raised by a fifth and then cut back into the sRGB gamut"""
    L0, a0, b0 = lab(hex_rgb(hexc)); C0 = math.hypot(a0, b0); h = math.atan2(b0, a0); C = C0 * 1.2
    while C > 1:
        if all(-1e-4 <= c <= 1.0001 for c in lab_rgb(DYE_L, C * math.cos(h), C * math.sin(h), clip=False)): break
        C -= 1.0
    return (DYE_L, C * math.cos(h), C * math.sin(h))


def dye_display(hexc):
    """the dye as drawn on the near-black cloth at full share (see dye_top_lab)"""
    return lab_rgb(*dye_top_lab(hexc))


def frac(x, den=128):
    """a share or a kinship exactly: as a fraction when its exact denominator is at most den (they are sums of powers of 1/2), else to 4 decimals
    (the card's format). Never a nearby fraction: Leopold I x Margaret Theresa's phi is 1069/4096, shown 0.2610, not 6/23."""
    f = Fraction(float(x))
    if f.denominator <= den: return str(f.numerator) if f.denominator == 1 else '%d/%d' % (f.numerator, f.denominator)
    return '%.4f' % float(x)


def hue_name(hexc):
    """the colour word for a dye, from its hue (the captions must not call a gold or green dye red)"""
    import colorsys
    hh, ll, ss = colorsys.rgb_to_hls(*hex_rgb(hexc)); d = hh * 360
    if ss < 0.15: return 'grey'
    return next(nm for lim, nm in ((15, 'red'), (40, 'orange'), (65, 'gold'), (170, 'green'), (255, 'blue'), (320, 'purple'), (361, 'red')) if d < lim)


def dye_sentence(F, P, nm):
    ds = list(F['dyes'].items())
    return '; '.join('%s is the share of descent from %s' % (hue_name(d['color']).capitalize() if i == 0 else hue_name(d['color']),
                                                             ' and '.join(nm(f) for f in d['founders'] if f in P) or 'the %s founders' % dk) for i, (dk, d) in enumerate(ds))


def norm(a):
    l = math.sqrt(sum(c * c for c in a)) or 1.0
    return tuple(c / l for c in a)


def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def add(a, b, s=1.0): return tuple(x + s * y for x, y in zip(a, b))
def sha(b): return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- data
def load_view(path):
    raw = open(path, 'rb').read(); v = json.loads(raw.decode('utf-8')); errs, warns = [], []
    if v.get('version') != 'loom-view/1': errs.append('version is %r, not loom-view/1' % v.get('version'))
    for f in v.get('families', []):
        for k in ('key', 'name', 'dyes', 'houses', 'people', 'unions'):
            if k not in f: errs.append('%s: no %s' % (f.get('key'), k))
        hk = {h['key'] for h in f.get('houses', [])}; ids = set()
        for p in f.get('people', []):
            for k in ('id', 'name', 'born', 'house', 'shares', 'core'):
                if k not in p: errs.append('%s/%s: no %s' % (f['key'], p.get('id'), k))
            if p.get('house') not in hk: errs.append('%s/%s: house %r not among the houses' % (f['key'], p.get('id'), p.get('house')))
            if not isinstance(p.get('born'), int): errs.append('%s/%s: born is not an integer' % (f['key'], p.get('id')))
            ids.add(p['id'])
        drop = dict(parents_nulled=[], unions=[], events=[]); f['_dropped'] = drop
        for p in f.get('people', []):
            for k in ('father', 'mother'):
                if p.get(k) and p[k] not in ids:
                    warns.append('%s/%s: %s %s is not in the file (read as null)' % (f['key'], p['id'], k, p[k])); drop['parents_nulled'].append([p['id'], k, p[k]]); p[k] = None
        for u in f.get('unions', []):
            why = 'a spouse is not in the file' if u['a'] not in ids or u['b'] not in ids else 'both ends are the same person' if u['a'] == u['b'] else None
            if why: warns.append('%s: union %s not drawn: %s' % (f['key'], u.get('id'), why)); drop['unions'].append([u.get('id'), why])
        f['unions'] = [u for u in f.get('unions', []) if u['a'] in ids and u['b'] in ids and u['a'] != u['b']]
        for e in f.get('events', []) or []:
            if e.get('grade') not in ('C', 'L'):
                warns.append('%s: event %r graded %r is not drawn (only C and L)' % (f['key'], e.get('label'), e.get('grade'))); drop['events'].append([e.get('year'), e.get('label'), e.get('grade')])
        f['events'] = [e for e in f.get('events', []) or [] if e.get('grade') in ('C', 'L')]
        fill_union_years(f, errs, warns)
    return v, raw, errs, warns


def fill_union_years(f, errs, warns):
    """a union whose year the data does not give (year null, precision unknown) is drawn at an estimate, by the development adapter's rule
    (adapt_harvest.py): the year before the couple's first common child in the file, else the younger spouse's 25th year; here also never after
    the first spouse's death (the year before it, so that a bride's move and the pick share a row). The data's null stays visible: year_precision stays 'unknown' (the pick is drawn translucent, the card says
    'year not in the data (drawn Y)', the stop label carries a '?'), year_data keeps the file's null and year_drawn_rule says how Y was chosen."""
    P = {p['id']: p for p in f.get('people', [])}; n = 0
    for u in f.get('unions', []):
        y = u.get('year')
        if isinstance(y, int) and not isinstance(y, bool): continue
        if y is not None: errs.append('%s: union %s year %r is neither an integer nor null' % (f['key'], u.get('id'), y)); continue
        if u.get('year_precision') != 'unknown':
            warns.append('%s: union %s has no year but precision %r (read as unknown)' % (f['key'], u.get('id'), u.get('year_precision')))
        a, b = P[u['a']], P[u['b']]
        kids = sorted(p['born'] for p in P.values() if {p.get('father'), p.get('mother')} == {u['a'], u['b']})
        if kids: y, rule = kids[0] - 1, 'the year before the first common child in the file (born %d)' % kids[0]
        else: y, rule = max(a['born'], b['born']) + 25, "the younger spouse's 25th year (no common child in the file)"
        deaths = [q['died'] for q in (a, b) if isinstance(q.get('died'), int)]
        if deaths and y >= min(deaths): y, rule = max(max(a['born'], b['born']) + 1, min(deaths) - 1), rule + ', moved back to the year before the first death (%d)' % min(deaths)
        u.update(year=y, year_precision='unknown', year_data=None, year_drawn_rule=rule); n += 1
    f['_estimated_union_years'] = n


# ---------------------------------------------------------------- layout
def plan(F, asof):
    """threads (segments per house and the moves between them), lanes, columns and every coordinate the scene and the page need"""
    P = {p['id']: p for p in F['people']}
    order = sorted(P, key=lambda i: (P[i]['born'], i))
    U_of = {}
    for u in F['unions']:
        U_of.setdefault(u['a'], []).append(u); U_of.setdefault(u['b'], []).append(u)
    for k_ in U_of: U_of[k_].sort(key=lambda u: (u['year'], u['id']))
    oth = lambda u, pid: u['b'] if u['a'] == pid else u['a']
    end = {}
    for pid in P:
        p = P[pid]; e = p.get('died') if p.get('died') is not None else p['born'] + UNKNOWN_LIFE
        end[pid] = max(p['born'] + 1, min(asof, e))
    # MOVES (fix round 09): decided per marriage, not per person in birth order. A dated move (the data's 'moved', else report 07's seed) comes
    # first. Otherwise a person whose adult house differs from the house they were born into moves on the pick of their first marriage into
    # that house: alone when the spouse was already there (born there, or moved there earlier), both together when neither was born there.
    # Only a person with no such marriage gets the AGE_MOVE estimate, drawn dotted, its year kept out of captions. An in-law without parents
    # in the file follows the spouse: house_at(spouse, year). Iterated to a fixed point (a child's birth house depends on its parent's move).
    rec = moved_records(F, P)
    parent = {pid: next((x for x in (P[pid].get('father'), P[pid].get('mother')) if x in P), None) for pid in P}
    follower = {pid for pid in P if parent[pid] is None and not P[pid].get('core')}
    nm_ = lambda q: P[q].get('short') or P[q]['name'].split(',')[0]
    start, move, meta, born_in, issues = {pid: P[pid]['house'] for pid in P}, {}, {}, {}, []
    def clamp(pid, y): return max(P[pid]['born'] + 1, min(y, end[pid] - 1))
    for _it in range(16):
        def hat(q, year, st_, mv_): return st_[q] if q in mv_ and year < mv_[q][0] else P[q]['house']
        born_in = {pid: (hat(parent[pid], P[pid]['born'], start, move) if parent[pid] else None) for pid in P}
        nstart, nmove, nmeta, issues = {pid: P[pid]['house'] for pid in P}, {}, {}, []
        for pid in order:
            p = P[pid]; hh = p['house']; bi = born_in[pid]
            if pid in follower or bi is None or bi == hh: continue
            nstart[pid] = bi
            if pid in rec:
                r = rec[pid]; nmove[pid] = (clamp(pid, r['year']), 'record', 'moved in %d (%s: %s)' % (r['year'], r['grade'], r['source']))
                nmeta[pid] = dict(role='record', grade=r['grade'], source=r['source'], origin=r['origin']); continue
            mine = [u for u in U_of.get(pid, []) if P[oth(u, pid)]['house'] == hh]
            if not mine:
                nmove[pid] = (clamp(pid, p['born'] + AGE_MOVE), 'estimated', 'no dated move and no marriage into this house in the data: drawn dotted, near age %d' % AGE_MOVE)
                nmeta[pid] = dict(role='estimated'); continue
            u = mine[0]; s = oth(u, pid); yq = ('%d?' % u['year']) if u.get('year_precision') == 'unknown' else str(u['year'])
            s_in = (rec[s]['year'] <= u['year']) if s in rec else (born_in.get(s) is None or born_in[s] == hh or (s in move and move[s][0] < u['year']))
            if s_in:
                nmove[pid] = (clamp(pid, u['year']), 'wedding', 'crosses on the %s pick: %s was already in this house' % (yq, nm_(s))); nmeta[pid] = dict(role='crosses', uid=u['id'], spouse=s)
            elif s in rec:
                nmove[pid] = (clamp(pid, rec[s]['year']), 'with-spouse', 'moves with %s in %d (%s: %s)' % (nm_(s), rec[s]['year'], rec[s]['grade'], rec[s]['source']))
                nmeta[pid] = dict(role='with', uid=u['id'], spouse=s, grade=rec[s]['grade'], source=rec[s]['source'])
            else:
                nmove[pid] = (clamp(pid, u['year']), 'wedding', 'both spouses cross on the %s pick: neither was born in this house' % yq); nmeta[pid] = dict(role='both', uid=u['id'], spouse=s)
        for pid in order:
            if pid not in follower: continue
            us = U_of.get(pid, []); hh = P[pid]['house']
            if not us: continue
            u = us[0]; s = oth(u, pid)
            if s in follower: continue
            sh = hat(s, u['year'], nstart, nmove)
            if sh == hh: continue
            if s in nmove and nmove[s][0] > u['year'] and P[s]['house'] == hh:
                if nmove[s][0] >= end[pid]:
                    nstart[pid] = sh; issues.append(dict(id=pid, issue='in-law dies (%d) before the spouse %s moves to %s (%d): the thread stays in %s' % (end[pid], s, hh, nmove[s][0], sh))); continue
                k = nmove[s][1]; nstart[pid] = sh
                nmove[pid] = (nmove[s][0], 'follows', 'follows %s: %s' % (nm_(s), nmove[s][2] if k != 'estimated' else 'whose move year is not in the data (drawn dotted)'))
                nmeta[pid] = dict(role='follows', spouse=s, of=k, **{x: nmeta[s][x] for x in ('grade', 'source') if x in nmeta.get(s, {})}); continue
            u2 = next((x for x in us[1:] if hat(oth(x, pid), x['year'], nstart, nmove) == hh), None)
            if u2:
                nstart[pid] = sh; yq = ('%d?' % u2['year']) if u2.get('year_precision') == 'unknown' else str(u2['year'])
                nmove[pid] = (clamp(pid, u2['year']), 'wedding', 'crosses on the %s pick' % yq); nmeta[pid] = dict(role='crosses', uid=u2['id'], spouse=oth(u2, pid))
            else:
                issues.append(dict(id=pid, issue='in-law in house %s, but the spouse %s is in %s at the %d wedding and never moves there: drawn in %s (the data rule says an in-law takes the spouse\'s house at marriage)' % (hh, s, sh, u['year'], hh)))
        same = nstart == start and {k: v[:2] for k, v in nmove.items()} == {k: v[:2] for k, v in move.items()}
        start, move, meta = nstart, nmove, nmeta
        if same and _it > 0: break
    else:
        raise SystemExit('%s: the move plan did not settle in 16 rounds' % F['key'])
    est = lambda pid: pid in move and (move[pid][1] == 'estimated' or (move[pid][1] == 'follows' and meta[pid].get('of') == 'estimated'))
    cross = {}
    for pid, m in meta.items():
        if m.get('role') in ('crosses', 'both') and m.get('uid'): cross.setdefault(m['uid'], []).append(pid)
    segs = {}
    for pid in order:
        p = P[pid]
        if pid in move:
            y = move[pid][0]; y2 = min(end[pid], y + (MOVE_SLANT if est(pid) else 0))
            segs[pid] = [[start[pid], p['born'], y], [p['house'], y2, end[pid]]]
        else:
            segs[pid] = [[start[pid], p['born'], end[pid]]]
    child = start
    # lanes: interval scheduling per house over segments; a spouse beside the partner, a child near its parents
    lane = {}
    houses = sorted({s[0] for v in segs.values() for s in v})
    for h in houses:
        items = sorted(((P[pid]['born'] if k == 0 else s[1], pid, k) for pid, v in segs.items() for k, s in enumerate(v) if s[0] == h), key=lambda t: (t[0], t[1], t[2]))
        busy = {}
        for start, pid, k in items:
            s = segs[pid][k]; target, avoid = 0.0, set()
            sp = [oth(u, pid) for u in U_of.get(pid, [])]
            sl = [lane[(q, j)] for q in sp for j, t in enumerate(segs.get(q, [])) if (q, j) in lane and t[0] == h and t[1] <= max(start, s[2] - 1) and t[2] >= start]
            if sl: target = sl[0] + 0.6; avoid.update(sl)
            else:
                pl = [lane[(q, j)] for q in (P[pid].get('father'), P[pid].get('mother')) if q in P for j, t in enumerate(segs[q]) if (q, j) in lane and t[0] == h]
                if pl: target = sum(pl) / len(pl)
            free = [l for l, until in busy.items() if until + LANE_GAP <= start and l not in avoid]
            new = [max(busy) + 1, min(busy) - 1] if busy else [0]
            best = min([(abs(l - target), abs(l), -l, l) for l in free] + [(abs(l - target) + (NEW_LANE_COST if busy else 0), abs(l), -l, l) for l in new])[3]
            lane[(pid, k)] = best; busy[best] = max(busy.get(best, -1e9), s[2])
    # columns west to east by longitude (ties: north first); depth by latitude
    HS = {h['key']: h for h in F['houses']}
    used = [h for h in sorted(HS, key=lambda k: (HS[k]['lon'] if HS[k].get('lon') is not None else 0.0, -(HS[k].get('lat') or 0.0), k)) if h in houses]
    lats = [HS[h]['lat'] for h in used if HS[h].get('lat') is not None]
    lat_mid = (min(lats) + max(lats)) / 2 if lats else 0.0
    y0 = int(math.floor(min(P[i]['born'] for i in P) / 25.0)) * 25
    top = min(asof, int(math.ceil((max(end.values()) + 5) / 25.0)) * 25)      # the cloth ends at its last thread (or asof), not always at today
    Y = lambda yr: (yr - y0) * TY
    span = {}
    for h in used:
        ls = [l for (pid, k), l in lane.items() if segs[pid][k][0] == h]; span[h] = (min(ls), max(ls))
    w0 = sum((hi - lo + 1) * LX for lo, hi in span.values()) + (len(used) - 1) * HOUSE_GAP
    kx = round(max(1.0, min(KX_MAX, KX_TARGET / max(1e-6, w0 / max(1e-6, Y(top))))), 3)   # balance: a tall narrow cloth (Habsburg) is widened
    lxk, gapk = LX * kx, HOUSE_GAP * kx
    col, x = {}, 0.0
    for h in used:
        lo, hi = span[h]; w = (hi - lo + 1) * lxk
        col[h] = dict(lo=lo, hi=hi, x0=x, x1=x + w, z=-((HS[h].get('lat') or lat_mid) - lat_mid) * KZ); x += w + gapk
    off = -(x - gapk) / 2
    for h in used: col[h]['x0'] += off; col[h]['x1'] += off; col[h]['xc'] = (col[h]['x0'] + col[h]['x1']) / 2
    lx = lambda h, l: col[h]['x0'] + (l - col[h]['lo'] + 0.5) * lxk
    # polylines and anchors
    T = {}
    for pid in order:
        s = segs[pid]; pts, pieces = [], []
        for k, (h, a, b) in enumerate(s):
            xk, zk = lx(h, lane[(pid, k)]), col[h]['z']
            pieces.append(dict(h=h, x=round(xk, 4), z=round(zk, 4), y0=a, y1=b, lane=lane[(pid, k)]))
            pts.append((xk, Y(a), zk)); pts.append((xk, Y(b), zk))
        T[pid] = dict(pieces=pieces, pts=pts)
    def pos_at(pid, yr):
        best = None
        for pc in T[pid]['pieces']:
            if pc['y0'] <= yr <= pc['y1']: return pc['x'], pc['z']
            dd = min(abs(yr - pc['y0']), abs(yr - pc['y1']))
            if best is None or dd < best[0]: best = (dd, pc['x'], pc['z'])
        return best[1], best[2]
    return dict(P=P, order=order, end=end, child=child, move=move, meta=meta, est=est, cross=cross, born_in=born_in, rec=rec, move_issues=issues, segs=segs, lane=lane, col=col, used=used,
                y0=y0, top=top, Y=Y, T=T, pos_at=pos_at, U_of=U_of, oth=oth, HS=HS, kx=kx)


def thread_color(p, dyes):
    """ecru mixed toward each dye by the person's share of descent, IN CIELAB: equal share steps are equal colour steps (about 15-19 dE76 per
    quarter), so a child of a close marriage (3/4) reads redder than an out-marrying cousin (1/2); the gate dye_ramp checks the steps"""
    e = lab(ECRU); tot = 0.0; acc = [0.0, 0.0, 0.0]
    for dk, d in dyes.items():
        s = max(0.0, min(1.0, float(p.get('shares', {}).get(dk, 0.0) or 0.0))); tot += s
        acc = [a + s * x for a, x in zip(acc, dye_top_lab(d['color']))]
    if tot > 1.0: acc = [a / tot for a in acc]; tot = 1.0
    return lab_rgb(*[e[i] * (1 - tot) + acc[i] for i in range(3)])


RAMP = (1.0, 0.75, 0.5, 0.25, 0.125, 0.0)


def dye_ramp(dyes):
    """per dye, the drawn colour at the shares that occur (founder, close child, out-marrying child, ...), and the dE76 between neighbours"""
    out = {}
    for dk, d in dyes.items():
        cs = [thread_color({'shares': {dk: s}}, {dk: d}) for s in RAMP]
        out[dk] = dict(steps=[[frac(s), '#%02x%02x%02x' % tuple(round(c * 255) for c in col)] for s, col in zip(RAMP, cs)],
                       dE76=[round(delta_e(cs[i], cs[i + 1]), 1) for i in range(len(cs) - 1)])
    return out


def style_of(p, dyes):
    founders = {f for d in dyes.values() for f in d.get('founders', [])}
    sh = sum(float(v or 0) for v in p.get('shares', {}).values())
    if p.get('died') is None: return 'dashed', 'death year not in the data'
    if p.get('core') and not p.get('father') and not p.get('mother') and p['id'] not in founders and sh == 0:
        return 'dashed', 'core member whose parents are not in the data: descent not linked'
    return ('core' if p.get('core') else 'inlaw'), None


# ---------------------------------------------------------------- cameras and labels
def basis(back, up_hint=(0.0, 1.0, 0.0)):
    back = norm(back); right = norm(cross(up_hint, back)); up = cross(back, right)
    return right, up, back


def focal(cam):
    """X_ITE: fieldOfView spans the smaller side of the canvas (the height on a desktop, the width on a portrait phone)"""
    vw, vh = cam.get('vw', W), cam.get('vh', H)
    return (min(vw, vh) / 2) / math.tan(cam['fov'] / 2), vw, vh


def project(p, cam):
    C, (right, up, back) = cam['pos'], cam['basis']; f, vw, vh = focal(cam)
    d = add(p, C, -1); cx, cy, cz = dot(d, right), dot(d, up), dot(d, back); depth = -cz
    if depth <= 1e-6: return None
    return (vw / 2 + f * cx / depth, vh / 2 - f * cy / depth, depth)


def fit_camera(points, back, fov=FOV, safe=None, vw=W, vh=H):
    """a camera looking along -back whose view of the points fills the safe area of a vw x vh page (iterated: scale the distance, recentre)"""
    safe = safe or SAFE
    right, up, back = basis(back); f = (min(vw, vh) / 2) / math.tan(fov / 2)
    xs = [p[0] for p in points]; ys = [p[1] for p in points]; zs = [p[2] for p in points]
    Tg = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    d = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) * 0.6 / math.tan(fov / 2) + 2.0
    sw, sh = safe['x1'] - safe['x0'], safe['y1'] - safe['y0']
    scx, scy = (safe['x0'] + safe['x1']) / 2, (safe['y0'] + safe['y1']) / 2
    cam = None
    for _ in range(40):
        ox, oy = scx - vw / 2, scy - vh / 2
        C = add(add(add(Tg, right, -ox * d / f), up, oy * d / f), back, d)
        cam = dict(pos=C, basis=(right, up, back), fov=fov, target=Tg, dist=d, vw=vw, vh=vh, safe=safe)
        pr = [project(p, cam) for p in points]; pr = [q for q in pr if q]
        bx0, bx1 = min(q[0] for q in pr), max(q[0] for q in pr); by0, by1 = min(q[1] for q in pr), max(q[1] for q in pr)
        sc = max((bx1 - bx0) / sw, (by1 - by0) / sh, 1e-3)
        mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
        cam['frame_w'], cam['frame_h'] = (bx1 - bx0) * d / f, (by1 - by0) * d / f
        if abs(sc - 1) < 2e-4 and abs(mx - scx) < 0.2 and abs(my - scy) < 0.2: break
        Tg = add(add(Tg, right, (mx - scx) * d / f), up, -(my - scy) * d / f)
        d = d * (0.35 + 0.65 * sc)
    cam['rot'] = drum.axis_angle_from_basis(right, up, back)
    return cam


def chip_box(origin, width, s, cam):
    right, up, back = cam['basis']; pts = []
    for xx in (-CHIP_PAD * s, width + CHIP_PAD * s):
        for yy in (-CHIP_Y * s, CHIP_Y * s):
            q = project(add(add(origin, right, xx), up, yy), cam)
            if q is None: return None
            pts.append(q)
    x0, x1 = min(q[0] for q in pts), max(q[0] for q in pts); y0, y1 = min(q[1] for q in pts), max(q[1] for q in pts)
    return (x0, y0, x1 - x0, y1 - y0)


def inside(b, safe=None):
    sa = safe or SAFE
    return b[0] >= sa['x0'] and b[1] >= sa['y0'] and b[0] + b[2] <= sa['x1'] and b[1] + b[3] <= sa['y1']


def hit(a, b, pad=4.0):
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0] or a[1] + a[3] + pad <= b[1] or b[1] + b[3] + pad <= a[1])


def size_for(px, anchor, cam):
    q = project(anchor, cam); f = focal(cam)[0]
    return px * (q[2] if q else cam['dist']) / f


def lift_for(anchor, cam, reach_x, s):
    """how far to pull a label from its anchor toward the camera so that its whole chip lies in front of every house plane: an oblique camera
    turns a flat label away in depth, so a long label's far end needs more than the cloth's depth range (the Wide frames had cut names)"""
    right, up, back = cam['basis']; ray = norm(add(anchor, cam['pos'], -1)); rz = -ray[2]
    worst = abs(right[2]) * (reach_x + 2 * CHIP_PAD * s) + abs(up[2]) * (CHIP_Y + max(abs(d) for d in FAR_DY)) * s
    return max(cam.get('lift', 0.3), (cam.get('zfront', anchor[2] + 0.3) - anchor[2] + worst) / max(0.2, rz))


def place(cands, cam, max_names=MAX_NAMES):
    """cands: dicts {text, anchor, px, color, kind, prio, modes, subject?}. Greedy by priority: the first placement inside the safe area that
    overlaps nothing placed. A name, pick or note sits on its thread's row (NEAR_DY: at most half a line off) or is left out; only a stop's
    subject may go farther (FAR_DY), and then it carries a leader line to its anchor. 'alts' (shorter texts) are tried when the full text
    finds no place. Returns the placed labels with their measured screen boxes and anchors, and the candidates left out with the reason."""
    right, up, back = cam['basis']; out, miss = [], []; safe = cam.get('safe', SAFE)
    for c in cands:
        if c['kind'] == 'name' and sum(1 for o in out if o['kind'] == 'name') >= max_names: miss.append((c, 'name cap (%d per stop)' % max_names)); continue
        q0 = project(c['anchor'], cam); done = False
        for text in [c['text']] + list(c.get('alts') or []):
            s0 = size_for(c['px'], c['anchor'], cam)
            lift = lift_for(c['anchor'], cam, CHAR_W * len(text) * s0 + 0.55 * s0, s0)
            a = add(c['anchor'], norm(add(c['anchor'], cam['pos'], -1)), -lift)
            s = size_for(c['px'], a, cam); gap = 0.55 * s; w = CHAR_W * len(text) * s
            near = NEAR_DY if c['kind'] in ('name', 'union', 'note') else (0.0, -1.35, 1.35, -2.7) if c['kind'] == 'house' else (0.0,)
            for dys, far in [(near, False)] + ([(FAR_DY, True)] if c.get('subject') else []):
                for m in c['modes']:
                    for dy in dys:
                        if m == 'right': o = add(a, right, gap)
                        elif m == 'left': o = add(a, right, -(gap + w))
                        elif m == 'center': o = add(a, right, -w / 2)
                        elif m == 'end': o = add(a, right, -w)
                        else: continue
                        o = add(o, up, dy * s)
                        bx = chip_box(o, w, s, cam)
                        if bx is None or not inside(bx, safe) or any(hit(bx, x['box']) for x in out): continue
                        lead = None
                        if far:
                            ex = add(o, right, -CHIP_PAD * s) if m == 'right' else add(o, right, w + CHIP_PAD * s)
                            lead = [add(a, up, 0.0), ex]
                        out.append(dict(c, text=text, origin=o, size=s, width=w, box=bx, lifted=a, mode=m, leader=lead, at=[round(q0[0], 1), round(q0[1], 1)] if q0 else None))
                        done = True; break
                    if done: break
                if done: break
            if done: break
        if not done: miss.append((c, 'no free place inside the safe area' + (' on its row' if c['kind'] in ('name', 'union', 'note') else '')))
    return out, miss


# ---------------------------------------------------------------- stops
RQ = dict(mayer='Q76988', gutle='Q1557224', nathan='Q547291', james='Q922667', salomon='Q370060', carl='Q63656', amschel='Q63990', betty='Q7044697',
          lionel='Q333605', charlotte='Q5086223', natty='Q334120', walter='Q316669', charles='Q2492200', edmond='Q467167', wilhelm='Q90004', louis='Q87392')
RN = dict(mayer=(r'^Mayer Amschel', 1744), gutle=(r'Gutle', 1753), nathan=(r'^Nathan Mayer Rothschild$', 1777), james=(r'^James (Mayer )?de Rothschild', 1792),
          salomon=(r'^Salomon Mayer', 1774), carl=(r'^Carl Mayer', 1788), amschel=(r'^Amschel Mayer', 1773), betty=(r'^Betty', 1805), lionel=(r'^Lionel de Rothschild', 1808),
          charlotte=(r'^Charlotte', 1819), natty=(r'^Nathan(iel)? Mayer', 1840), walter=(r'^Walter', 1868), charles=(r'^Charles', 1877), edmond=(r'^Edmond James', 1845),
          wilhelm=(r'^Wilhelm Carl', 1828), louis=(r'^Louis', 1882))

# report 07's narration drafts, kept only where the sentence does not depend on this dataset; each with report 07's own grade
NARR = {
    'cloth': [('Two and a half centuries of one family, woven from the bottom up. Each upright thread is a life; each crossing, a marriage.', '≈')],
    'judengasse': [('Mayer Amschel Rothschild is born in Frankfurt\'s Jewish ghetto in 1744, or 1743; the records differ.', 'C ⚑'),
                   ('The name comes from an older family house, zum Roten Schild.', 'C'),
                   ('A coin dealer, he becomes court factor to Crown Prince Wilhelm of Hesse in 1769.', 'C')],
    'no148': [('Gutle Schnapper marries Mayer in 1770 and raises ten children at No. 148.', 'C'), ('Her sons grow rich and urge her to move; she refuses.', 'C')],
    'arrows': [('Four sons leave; one stays.', 'C'),
               ('Nathan goes to Manchester in 1798, then London; James to Paris; Salomon to Vienna; Carl to Naples after the Austrian occupation of 1821.', 'C'),
               ('In 1822 the emperor makes all five barons: five arrows in a clenched fist, Concordia, Integritas, Industria.', 'C')],
    'doubles': [('In 1824 James marries Betty, his brother Salomon\'s daughter; she is nineteen.', 'C'), ('Ingres finishes her portrait in 1848.', 'C')],
    'frankfurt1836': [('Lionel marries his first cousin Charlotte, Carl\'s daughter, two days after her seventeenth birthday.', 'C'),
                      ('Nathan has come to Frankfurt for the wedding; he falls ill and dies there on 28 July.', 'C')],
    'closeweave': [('Of twenty-one Rothschild marriages that century, fifteen were close.', 'L'), ('Watch who moves: the sons stay, and the brides cross Europe.', '≈'),
                   ('By 1900 almost all marry out.', 'C')],
    'seats': [('Lionel is elected for the City of London in 1847 and re-elected three times, but takes his seat only in 1858, once each House may set its own oath.', 'C'),
              ('In 1885 his son Natty becomes the first Jewish peer.', 'C')],
    'naturalists': [('Walter opens his museum at Tring in 1892; the Balfour Declaration of 1917 is a letter to him.', 'C'),
                    ('Charles names the plague flea in 1903 and founds a society for nature reserves in 1912.', 'C')],
    'zikhron': [('From 1882 Edmond buys land in Ottoman Palestine and funds settlements, among them Zikhron Ya\'akov, named for his father, Jacob, that is, James.', 'C'),
                ('He dies in 1934; in 1954 he and Adelheid are reburied at Ramat HaNadiv.', 'C')],
    'ruptures': [('Naples closes in 1863; Frankfurt in 1901, when Wilhelm Carl dies without a son.', 'C'), ('In Vienna in 1938, Louis is imprisoned for a year and freed for a ransom.', 'C'),
                 ('In 1982 the French bank is nationalised.', 'C'), ('The tour skipped most lives. Pull any thread.', '≈')],
}


# dated moves, read only where the person carries no 'moved' {year, grade, source} of its own (proposed for loom-view: see data-issues.json).
# Report 07's grades; Salomon's year is the review's and is not in report 07's text, so it stays S.
MOVED_SEED = {'rothschild': {
    'nathan': dict(year=1798, grade='C', source='report 07, stop 4: "Nathan goes to Manchester in 1798, then London"'),
    'james': dict(year=1811, grade='S', source='report 07, stop 4: "James to Paris (S: 1811)"'),
    'salomon': dict(year=1820, grade='S', source='review 08; not in report 07\'s text, unchecked'),
    'carl': dict(year=1821, grade='C', source='report 07, stop 4 ("Carl to Naples after the Austrian occupation of 1821") and the data note')}}
# report 07's stop 12, graded C: where each house's bank closes or breaks. The data's house 'closed' is NOT this: proto/ingest/loomview.py
# computes it as the last death among the house's core members, so the scene never calls it a closing.
RUPTURES = {'rothschild': [('naples', 1863, 'Naples bank closes 1863'), ('frankfurt', 1901, 'Frankfurt bank closes 1901'),
                           ('vienna', 1938, 'Vienna 1938: Louis imprisoned'), ('paris', 1982, 'Paris bank nationalised 1982')]}
CLOSINGS = {'rothschild': {'naples': 1863, 'frankfurt': 1901}}    # of those, the two the narration calls closings


def moved_records(F, P):
    rec = {}
    for p in F['people']:
        m = p.get('moved')
        if isinstance(m, dict) and isinstance(m.get('year'), int) and not isinstance(m.get('year'), bool):
            rec[p['id']] = dict(year=m['year'], grade=m.get('grade') or 'S', source=m.get('source') or 'loom-view moved', origin='data')
    for key, m in MOVED_SEED.get(F['key'], {}).items():
        pid = resolve_id(F, key)
        if pid and pid in P and pid not in rec: rec[pid] = dict(m, origin='seed (build_loom_scene.py MOVED_SEED)')
    return rec


def resolve_id(F, key):
    q = RQ.get(key)
    if q:
        for p in F['people']:
            if p.get('qid') == q or p['id'] == q: return p['id']
    rx, born = RN.get(key, (None, None))
    if rx:
        c = [p['id'] for p in F['people'] if re.search(rx, p['name']) and abs(p['born'] - born) <= 1]
        if len(c) == 1: return c[0]
    return None


def resolve(F, L, key): return resolve_id(F, key)


def lineage(L, pid):
    """the line of descent drawn for a stop's subject: from the subject up through the parent carrying more dye, to a founder"""
    P = L['P']; chain = [pid]; seen = {pid}; cur = pid
    dye = lambda q: sum(float(v or 0) for v in (P[q].get('shares') or {}).values())
    while True:
        par = [x for x in (P[cur].get('father'), P[cur].get('mother')) if x in P and x not in seen and dye(x) > 0]
        if not par: break
        cur = max(par, key=lambda x: (dye(x), x == P[chain[-1]].get('father'))); chain.append(cur); seen.add(cur)
    return list(reversed(chain))


def label_text(L, pid):
    P = L['P']; p = P[pid]; s = p.get('short') or p['name'].split(',')[0].split()[0]
    if sum(1 for q in P.values() if (q.get('short') or '') == s) > 1: s = '%s %d' % (s, p['born'])
    return s


def gen_stops(F, L, asof):
    """report 07's stops where the data supports them, in its order, plus Wide; each with frame points, focus, captions"""
    P, Y, col, used = L['P'], L['Y'], L['col'], L['used']
    roth = F['key'] == 'rothschild'
    R = {k: resolve(F, L, k) for k in RQ} if roth else {}
    founders = [f for d in F['dyes'].values() for f in d.get('founders', []) if f in P]
    fhouse = P[founders[0]]['house'] if founders else None
    U = {u['id']: u for u in F['unions']}
    close = sorted((u for u in F['unions'] if u.get('close')), key=lambda u: (u['year'], u['id']))
    kids = lambda a, b: sorted((pid for pid in P if {P[pid].get('father'), P[pid].get('mother')} == {a, b}), key=lambda i: (P[i]['born'], i))
    nm = lambda pid: P[pid]['name'].split(',')[0]
    yr = lambda pid: '%d–%s' % (P[pid]['born'], P[pid]['died'] if P[pid].get('died') is not None else '?')
    def thread_pts(pid, a, b):
        out = []
        for pc in L['T'][pid]['pieces']:
            lo, hi = max(a, pc['y0']), min(b, pc['y1'])
            if lo <= hi: out += [(pc['x'], Y(lo), pc['z']), (pc['x'], Y(hi), pc['z'])]
        return out
    def col_pts(hs, a, b):
        return [(x, Y(yv), col[h]['z']) for h in hs for x in (col[h]['x0'], col[h]['x1']) for yv in (a, b)]
    def union_of(a, b):
        for u in F['unions']:
            if {u['a'], u['b']} == {a, b}: return u
        return None
    stops = []
    def add_stop(n, key, title, years, focus=(), unions=(), houses=None, kind='front', narr=(), comp=(), notes=(), extra=(), subject=None, fell=None):
        a, b = years; pts = []
        for pid in focus: pts += thread_pts(pid, a, b)
        for uid in unions:
            u = U[uid]; xa_, za = L['pos_at'](u['a'], u['year']); xb, zb = L['pos_at'](u['b'], u['year']); pts += [(xa_, Y(u['year']), za), (xb, Y(u['year']), zb)]
        if houses: pts += col_pts(houses, a, b)
        pts += list(extra)
        if not pts: return
        subj = [x for x in (subject if subject is not None else list(focus)[:1]) if x in P]
        fy = max(L['y0'], min(L['top'], fell if fell is not None else (L['top'] if kind in ('cloth', 'wide') else b)))
        stops.append(dict(n=n, key=key, title=title, years=[a, b], focus=[f for f in focus if f], unions=list(unions), houses=houses, kind=kind, pts=pts,
                          subject=subj, fell=fy, lineage={x: lineage(L, x) for x in subj},
                          narration=[dict(text=t, grade=g, src='reports/07-narrative-ux.md') for t, g in narr],
                          computed=[dict(text=t, grade='∑') for t in comp], notes=list(notes)))
    allx = [c for h in used for c in (col[h]['x0'], col[h]['x1'])]
    def mv_txt(s_, frm=False):
        y_, kind_, _ = L['move'][s_]; m_ = L['meta'].get(s_, {}); to_ = L['HS'][P[s_]['house']]['name']; fr_ = L['HS'][L['child'][s_]]['name']
        head = '%s %sto %s' % (P[s_].get('short') or nm(s_), ('from %s ' % fr_) if frm else '', to_)
        if L['est'](s_): return head + ' (year not in the data: drawn dotted)'
        if kind_ == 'record': return head + ', %d (%s)' % (y_, m_.get('grade'))
        if kind_ == 'with-spouse': return head + ', %d, with %s (%s)' % (y_, nm(m_['spouse']), m_.get('grade'))
        if kind_ == 'follows': return head + ', %d, following %s' % (y_, nm(m_['spouse']))
        u_ = U.get(m_.get('uid')); q_ = '%d?' % y_ if u_ and u_.get('year_precision') == 'unknown' else '%d' % y_
        return head + ', on the %s pick%s' % (q_, ' (both spouses cross)' if m_.get('role') == 'both' else '')
    n_close = len(close)
    # 1 Cloth
    add_stop(1, 'cloth', 'Cloth', (L['y0'], L['top']), houses=used, kind='cloth', narr=NARR['cloth'] if roth else [], subject=founders,
             comp=['%d threads, %d picks, %d of them close and doubled; %d houses west to east by longitude: %s.' % (len(P), len(F['unions']), n_close, len(used), ', '.join(L['HS'][h]['name'] for h in used)),
                   '%s; undyed ecru is an in-law; dashed is a gap in the data.' % dye_sentence(F, P, nm)])
    if roth:
        m, g = R.get('mayer'), R.get('gutle')
        if m:
            add_stop(2, 'judengasse', 'Judengasse', (max(L['y0'], P[m]['born'] - 4), P[m]['born'] + 40), focus=[m] + ([g] if g else []), houses=[P[m]['house']], narr=NARR['judengasse'],
                     comp=['Mayer\'s thread: %s (born %s, precision %s), in the %s column; a founder, so fully dyed.' % (yr(m), P[m]['born'], P[m].get('born_precision'), L['HS'][P[m]['house']]['name'])])
        if m and g:
            ch = kids(m, g)
            if ch:
                d_ = sum(1 for c in ch if P[c].get('sex') == 'F'); s_ = sum(1 for c in ch if P[c].get('sex') == 'M')
                add_stop(3, 'no148', 'No. 148', (1765, 1850), focus=[g, m] + ch, houses=[P[g]['house']], narr=NARR['no148'], subject=[g],
                         comp=['Gutle\'s thread: %s, in the %s column. %d children of Mayer and Gutle are in this file, born %d–%d (%d daughters, %d sons).' % (
                             yr(g), L['HS'][P[g]['house']]['name'], len(ch), P[ch[0]]['born'], P[ch[-1]]['born'], d_, s_)])
        sons = [R.get(k) for k in ('nathan', 'james', 'salomon', 'carl') if R.get(k)]
        movers = [s for s in sons if s in L['move']]
        if movers:
            ex = []; ys = []
            for s in movers:
                y, kind, _ = L['move'][s]; ys.append(y)
                pcs = L['T'][s]['pieces']; ex += [(pcs[0]['x'], Y(y), pcs[0]['z']), (pcs[1]['x'], Y(min(pcs[1]['y1'], y + MOVE_SLANT + 4)), pcs[1]['z'])]
            am = R.get('amschel')
            add_stop(4, 'arrows', 'Five Arrows', (min(ys) - 6, max(ys) + 10), focus=movers + ([am] if am else []), narr=NARR['arrows'], extra=ex, subject=movers,
                     comp=['Moves out of %s drawn here: %s.' % (L['HS'][fhouse]['name'] if fhouse else '?', '; '.join(mv_txt(s) for s in movers)),
                         'One stays: %s. The brides cross later, on their wedding picks (an open diamond marks the end that moves).' % ('Amschel, in the %s column' % L['HS'][P[am]['house']]['name'] if am else 'not in this file')])
        if any('waterloo' in (e.get('label') or '').lower() for e in F.get('events', [])):
            e = next(e for e in F['events'] if 'waterloo' in e['label'].lower())
            n_ = R.get('nathan')
            if n_: add_stop(5, 'waterloo', 'Waterloo, told and recorded', (e['year'] - 15, e['year'] + 15), focus=[n_], subject=[n_], comp=['Event in the file: %s (%s).' % (e['label'], e['grade'])])
        j, b = R.get('james'), R.get('betty')
        u = union_of(j, b) if j and b else None
        if u:
            ch = kids(j, b); sh = [float(P[c]['shares'].get('rothschild', 0)) for c in ch]
            add_stop(6, 'doubles', 'The weft doubles back', (u['year'] - 26, u['year'] + 36), focus=[j, b] + ch + [x for x in (P[b].get('father'),) if x], unions=[u['id']], narr=NARR['doubles'], subject=[j, b],
                     comp=['The %d pick: %s and %s, %s, kinship φ = %s%s.' % (u['year'], nm(j), nm(b), u.get('relationship') or 'kin', frac(u.get('phi') or 0), ', drawn doubled' if u.get('close') else ''),
                           ('Their %d children in the file carry dye %s, where an out-marrying line of the same generation carries 1/2.' % (len(ch), frac(sh[0])) if ch and len(set(sh)) == 1
                            else 'Their children carry dye %s.' % ', '.join(frac(x) for x in sh)) if ch else 'No children of theirs in the file.'],
                     notes=[(c, 'dye ' + frac(float(P[c]['shares'].get('rothschild', 0)))) for c in ch[:1]])
        l_, c_, n_ = R.get('lionel'), R.get('charlotte'), R.get('nathan')
        u = union_of(l_, c_) if l_ and c_ else None
        if u and n_:
            hl, hc, mv = P[l_]['house'], P[c_]['house'], L['move'].get(c_)
            where = ('joins the %s and %s columns' % (L['HS'][hl]['name'], L['HS'][hc]['name'])) if hl != hc else ('is in the %s column' % L['HS'][hl]['name'])
            if mv: where += ' (Charlotte\'s thread moves there from the %s column %s)' % (L['HS'][L['child'][c_]]['name'], 'on the pick' if mv[1] == 'wedding' else 'earlier, estimated' if L['est'](c_) else 'in %d' % mv[0])
            add_stop(7, 'frankfurt1836', 'Frankfurt, summer 1836', (u['year'] - 14, u['year'] + 12), focus=[l_, c_, n_], unions=[u['id']], narr=NARR['frankfurt1836'], subject=[l_, c_, n_],
                     comp=['The %d pick %s; Nathan\'s thread ends in %s, in the %s column.' % (u['year'], where, P[n_].get('died'), L['HS'][P[n_]['house']]['name']),
                           ('The pick is doubled: the file links the couple as kin (φ = %s).' % frac(u['phi'])) if u.get('close') else
                           'The pick is drawn single: this file does not link Charlotte to her parents, so the cousin marriage is not computed. The gap is in the data.'])
    # 6 (generic): the closest marriage
    if not roth and close:
        u = max(close, key=lambda u: (u.get('phi') or 0, len(kids(u['a'], u['b'])), -u['year']))
        ch = kids(u['a'], u['b'])
        add_stop(6, 'doubles', 'The weft doubles back', (u['year'] - 26, u['year'] + 36), focus=[u['a'], u['b']] + ch, unions=[u['id']], subject=[u['a'], u['b']],
                 comp=['The %d pick%s: %s and %s, %s, kinship φ = %s, drawn doubled.' % (u['year'], ' (year estimated: not in the data)' if u.get('year_precision') == 'unknown' else '', nm(u['a']), nm(u['b']),
                                                                                         u.get('relationship') or 'kin', frac(u.get('phi') or 0)),
                       ('Their %d children in the file carry the dyes %s.' % (len(ch), '; '.join('%s %s' % (dk, frac(float(P[ch[0]]['shares'].get(dk, 0)))) for dk in F['dyes']))) if ch else 'No children of theirs in the file.'],
                 notes=[(ch[0], ' · '.join('%s %s' % (dk, frac(float(P[ch[0]]['shares'].get(dk, 0)))) for dk in F['dyes']))] if ch else [])
    if not roth and founders:
        f0 = sorted(founders, key=lambda i: (P[i]['born'], i))
        add_stop(2, 'founders', 'The first threads', (max(L['y0'], P[f0[0]]['born'] - 4), P[f0[0]]['born'] + 45), focus=f0, houses=sorted({P[f]['house'] for f in f0}), subject=f0,
                 comp=['Founders of the dye%s: %s.' % ('s' if len(F['dyes']) > 1 else '', '; '.join('%s (%s): %s' % (dk, d['color'], ' and '.join('%s %s' % (nm(f), yr(f)) for f in d['founders'] if f in P)) for dk, d in F['dyes'].items()))])
        ch = sorted({c for f in f0 for c in P if f in (P[c].get('father'), P[c].get('mother'))}, key=lambda i: (P[i]['born'], i))
        if ch:
            add_stop(3, 'children', 'The founders\' children', (P[ch[0]]['born'] - 8, P[ch[-1]]['born'] + 30), focus=f0 + ch, subject=ch[:4],
                     comp=['%d children of the founders are in the file, born %d–%d.' % (len(ch), P[ch[0]]['born'], P[ch[-1]]['born'])])
        movers = sorted((s for s in P if s in L['move']), key=lambda s: (L['move'][s][0], s))[:6]
        if movers:
            ys = [L['move'][s][0] for s in movers]; ex = []
            for s in movers:
                pcs = L['T'][s]['pieces']; y = L['move'][s][0]
                ex += [(pcs[0]['x'], Y(y), pcs[0]['z']), (pcs[1]['x'], Y(min(pcs[1]['y1'], y + MOVE_SLANT + 4)), pcs[1]['z'])]
            add_stop(4, 'arrows', 'The houses part', (min(ys) - 6, max(ys) + 10), focus=movers, extra=ex, subject=movers[:4],
                     comp=['The first moves between houses: %s.' % '; '.join(mv_txt(s, frm=True) for s in movers),
                           'A move rides the wedding pick when the spouse was already in that house; a dotted move has no year in the data.'])
    if close:
        lo, hi = close[0]['year'], close[-1]['year']; n_est_close = sum(1 for u in close if u.get('year_precision') == 'unknown')
        sp = sorted({x for u in close for x in (u['a'], u['b'])}, key=lambda i: (P[i]['born'], i))
        uc = max(close, key=lambda u: (len(kids(u['a'], u['b'])), u.get('phi') or 0, -u['year']))
        sp = [uc['a'], uc['b']] + [x for x in sp if x not in (uc['a'], uc['b'])]
        add_stop(8, 'closeweave', 'The close weave', (lo - 6, max(hi + 8, lo + 30)), focus=sp, unions=[uc['id']] + [u['id'] for u in close if u['id'] != uc['id']], houses=used, narr=NARR['closeweave'] if roth else [],
                 subject=[uc['a'], uc['b']],
                 comp=['%d of the %d picks in this file are close (the couple share founders in the data), %d–%d; each is drawn doubled.' % (n_close, len(F['unions']), lo, hi)
                       + (' %d of those years are not in the data and are drawn at an estimate (marked ?).' % n_est_close if n_est_close else ''),
                       'Kinship φ ranges %s to %s.' % (frac(min(u['phi'] for u in close)), frac(max(u['phi'] for u in close))),
                       'Threads that cross on a close pick (open diamond): %d brides, %d grooms.' % (
                           sum(1 for u in close for x in L['cross'].get(u['id'], []) if P[x].get('sex') == 'F'), sum(1 for u in close for x in L['cross'].get(u['id'], []) if P[x].get('sex') == 'M'))])
    if roth:
        l_, nt = R.get('lionel'), R.get('natty')
        if l_ and nt:
            add_stop(9, 'seats', 'Seats', (1836, 1895), focus=[l_, nt], houses=[P[l_]['house']], narr=NARR['seats'], subject=[l_, nt],
                     comp=['Lionel %s and Natty %s, both in the %s column.' % (yr(l_), yr(nt), L['HS'][P[l_]['house']]['name'])])
        w_, c_ = R.get('walter'), R.get('charles')
        if w_ and c_:
            vic = [p for p in P if P[p].get('father') == c_]
            add_stop(10, 'naturalists', 'Naturalists, and a gap', (1862, 1940), focus=[w_, c_] + vic[:2], houses=[P[w_]['house']], narr=NARR['naturalists'], subject=[w_, c_],
                     comp=['Walter %s and Charles %s carry dye %s and %s.' % (yr(w_), yr(c_), frac(float(P[w_]['shares'].get('rothschild', 0))), frac(float(P[c_]['shares'].get('rothschild', 0)))),
                           ('Charles is in this file, as father of %s.' % ', '.join(nm(v) for v in vic)) if vic else 'Charles has no children in this file.'])
        e_ = R.get('edmond')
        if e_:
            add_stop(11, 'zikhron', 'Zikhron Ya\'akov', (1840, 1940), focus=[e_], houses=[P[e_]['house']], narr=NARR['zikhron'],
                     comp=['Edmond %s, in the %s column, carries dye %s.' % (yr(e_), L['HS'][P[e_]['house']]['name'], frac(float(P[e_]['shares'].get('rothschild', 0))))])
    ends = []
    for h in used:
        last = max(pc['y1'] for pid in P for pc in L['T'][pid]['pieces'] if pc['h'] == h)
        ends.append((h, L['HS'][h].get('closed'), last))
    closed = [e for e in ends if e[1]]
    lo = min([e[1] for e in closed] + [e[2] for e in ends if e[2] < L['top'] - 30] + [L['top'] - 80])
    rup = [(h, y_, t_) for h, y_, t_ in RUPTURES.get(F['key'], []) if h in used]
    if rup: lo = min([lo] + [y_ for _, y_, _ in rup])
    add_stop(12, 'ruptures', 'Ruptures, then the fell', (max(L['y0'], lo - 20), L['top']), houses=used, narr=NARR['ruptures'] if roth else [], subject=[],
             comp=(['Marked on the cloth from the narration (report 07, C): %s.' % '; '.join(t_ for _, _, t_ in rup)] if rup else []) +
                  ['The file has no closing dates. Its "closed" year per house is the last death among the house\'s core members: %s.' % (
                      '; '.join('%s %d' % (L['HS'][h]['name'], c) for h, c, _ in sorted(closed, key=lambda e: e[1])) if closed else 'none, every house still has a presumed-living core member'),
                   'Where that differs from a narrated closing, the data list (data-issues.json) records it; the cloth does not.'],
             notes=[('mark:%s:%d' % (h, y_), t_) for h, y_, t_ in rup] + ([] if rup else [('house:' + h, '%s · last death %d' % (L['HS'][h]['name'], c)) for h, c, _ in closed]))
    add_stop(13, 'wide', 'Wide', (L['y0'], L['top']), houses=used, kind='wide', subject=[],
             comp=['%d people (asof %d) from %s.' % (len(P), asof, os.path.basename(str(F.get('_src') or 'the loom-view file')))])
    stops.sort(key=lambda s: s['n'])
    return stops


def stop_camera(st, L, phone=False):
    """frame the stop's points plus rails: room at the left for the year labels, below for the house names, at the right for name labels.
    Front stops use a long lens (FOV_FRONT); the phone variant frames the same points for a portrait page."""
    pts = st['pts']; xs, ys, zs = [p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts]
    w_, h_ = max(xs) - min(xs), max(ys) - min(ys); zc = (min(zs) + max(zs)) / 2
    k = 1.6 if phone else 1.0
    ml, mr, mb, mt = max(1.3, 0.10 * k * w_), max(1.1, 0.07 * k * w_), max(0.9, 0.05 * k * h_), max(0.3, 0.02 * h_)
    ext = pts + [(min(xs) - ml, min(ys) - mb, zc), (max(xs) + mr, max(ys) + mt, zc), (min(xs) - ml, max(ys) + mt, zc), (max(xs) + mr, min(ys) - mb, zc)]
    vw, vh, safe = (PW, PH, PSAFE) if phone else (W, H, SAFE)
    if st['kind'] == 'oblique': return fit_camera(ext, (0.0, 0.66, 0.75), FOV, safe, vw, vh)
    if st['kind'] == 'wide': return fit_camera(ext, (0.40, 0.42, 0.81), FOV, safe, vw, vh)
    return fit_camera(ext, (0.0, 0.0, 1.0), FOV_FRONT, safe, vw, vh)


def anchor_of(st, L, pid):
    """where a person's label points: the bead when the birth is in the stop's window, else the middle of the thread's visible part"""
    P, Y = L['P'], L['Y']; a, b = st['years']; p = P[pid]
    for pc in L['T'][pid]['pieces']:
        lo, hi = max(a, pc['y0']), min(b, pc['y1'])
        if lo > hi: continue
        yv = p['born'] if pc['y0'] == p['born'] and a <= p['born'] <= b else (lo + hi) / 2
        return (pc['x'], Y(yv), pc['z'])
    return None


def stop_labels(st, L, F, cam, phone=False):
    P, Y, col = L['P'], L['Y'], L['col']; a, b = st['years']
    cands = []; safe = cam.get('safe', SAFE)
    # house rail at the bottom of the frame, then the year rail at its left
    span_y = st_years_visible(st, L, cam); shorts = house_shorts(L['HS'], L['used'])
    ybot = min(p[1] for p in st['pts'])
    for h in L['used']:
        q = project((col[h]['xc'], ybot, col[h]['z']), cam)
        if not q or not (safe['x0'] <= q[0] <= safe['x1']): continue
        anc = (col[h]['xc'], ybot - 0.45, col[h]['z'])
        short = shorts.get(h)
        first = re.split(r"[\s'/]+", short or L['HS'][h]['name'].upper())[0]
        alts = [x for x in (short, first if sum(1 for k in L['used'] if re.split(r"[\s'/]+", shorts.get(k) or L['HS'][k]['name'].upper())[0] == first) == 1 else None) if x and x != L['HS'][h]['name'].upper()]
        cands.append(dict(text=L['HS'][h]['name'].upper(), alts=list(dict.fromkeys(alts)), anchor=anc, px=AXIS_PX, color=GOLD, kind='house', prio=0, modes=['center'], ref=h))
    step = next((sv for sv in (5, 10, 25, 50, 100, 200) if (span_y[1] - span_y[0]) / sv <= (5 if phone else 7)), 250)
    xl = min(cam_left_x(st, L, cam), min(col[h]['x0'] for h in L['used']) - 0.3) if st['kind'] in ('cloth', 'wide') else cam_left_x(st, L, cam)
    zf = rail_z(st, L)          # read at the depth of the stop's subject (or the cloth's middle): with the long lens, beads read within a year
    for yv in range(int(math.ceil(span_y[0] / step)) * step, int(span_y[1]) + 1, step):
        cands.append(dict(text=str(yv), anchor=(xl, Y(yv), zf), px=AXIS_PX, color=YEAR_C, kind='year', prio=1, modes=['end'], ref=yv))
    # the stop's subject first (always labelled: a leader line if its row is full), then notes, the focus unions, focus people, the rest by weight
    seen = set()
    for pid in st.get('subject', []):
        anc = anchor_of(st, L, pid)
        if anc is None or pid in seen: continue
        seen.add(pid)
        cands.append(dict(text=label_text(L, pid), anchor=anc, px=NAME_PX, color=SUBJ_C, kind='name', prio=2, modes=['right', 'left'], ref=pid, subject=True))
    notes = st['notes'][:2] if phone else st['notes']
    for ref, text in notes:
        if ref.startswith('house:'):
            h = ref[6:]; c = L['HS'][h]['closed']; anc = (col[h]['xc'], Y(c), col[h]['z'])
        elif ref.startswith('mark:'):
            _, h, yv = ref.split(':'); anc = (col[h]['xc'], Y(int(yv)), col[h]['z'])
        else:
            pc = L['T'][ref]['pieces'][-1]; anc = (pc['x'], Y(max(pc['y0'], min(pc['y1'], P[ref]['born'] + 12))), pc['z'])
        cands.append(dict(text=text, anchor=anc, px=NAME_PX, color=NOTE_C, kind='note', prio=3, modes=['right', 'left'], ref=ref))
    for uid in st['unions'][:2 if phone else 4]:
        u = next(x for x in F['unions'] if x['id'] == uid)
        xa_, za = L['pos_at'](u['a'], u['year']); xb, zb = L['pos_at'](u['b'], u['year'])
        ytxt = '%d?' % u['year'] if u.get('year_precision') == 'unknown' else ('c. %d' % u['year'] if u.get('year_precision') == 'circa' else '%d' % u['year'])
        txt = '%s · %s%s' % (ytxt, u.get('relationship') or 'married', ' · doubled' if u.get('close') else '')
        cands.append(dict(text=txt, anchor=((xa_ + xb) / 2, Y(u['year']) + 0.28, max(za, zb)), px=NAME_PX, color=UNION_C, kind='union', prio=4, modes=['center', 'right', 'left'], ref=uid))
    people = []
    for pid in st['focus']:
        if pid in P and pid not in seen: seen.add(pid); people.append((pid, True))
    weight = lambda pid: (-(len([c for c in P if pid in (P[c].get('father'), P[c].get('mother'))]) + 3 * bool(P[pid].get('core')) + 4 * sum(1 for u in L['U_of'].get(pid, []) if u.get('close'))), P[pid]['born'], pid)
    for pid in sorted(P, key=weight):
        if pid not in seen: seen.add(pid); people.append((pid, False))
    for pid, is_focus in people:
        anc = anchor_of(st, L, pid)
        if anc is None: continue
        q = project(anc, cam)
        if not q or not (safe['x0'] <= q[0] <= safe['x1'] and safe['y0'] <= q[1] <= safe['y1']): continue
        cands.append(dict(text=label_text(L, pid), anchor=anc, px=NAME_PX, color=FOCUS_C if is_focus else NAME_C, kind='name', prio=5 if is_focus else 6, modes=['right', 'left'], ref=pid))
    cands.sort(key=lambda c: c['prio'])
    placed, miss = place(cands, cam, MAX_NAMES_PHONE if phone else MAX_NAMES)
    st['label_misses' + ('_phone' if phone else '')] = [dict(kind=c['kind'], text=c['text'], why=why, subject=bool(c.get('subject'))) for c, why in miss]
    return placed


def house_shorts(HS, used):
    """the house rail's fallback when a full house name finds no place: the name before any bracket, slash or hyphen, without a trailing
    LINE / HOUSE / 'S HOUSEHOLD; where two houses would read the same (the Leopoldine lines), the bracketed word instead"""
    cut = lambda n: re.sub(r"('S HOUSEHOLD| LINE| HOUSE)$", '', re.split(r'\s*[(/-]', n)[0]).strip()
    sh = {h: cut(HS[h]['name'].upper()) for h in used}; dup = {v for v in sh.values() if list(sh.values()).count(v) > 1}
    for h in used:
        m = re.search(r'\(([^)]+)\)', HS[h]['name'].upper())
        if sh[h] in dup: sh[h] = m.group(1).strip() if m else None
    return {h: (v if v and v != HS[h]['name'].upper() else None) for h, v in sh.items()}


def st_years_visible(st, L, cam):
    a, b = st['years']
    return (max(a, L['y0']), b)


def cam_left_x(st, L, cam):
    xs = [p[0] for p in st['pts']]
    return min(xs) - 0.35


# ---------------------------------------------------------------- X3D
LABEL_PROTO = """<ProtoDeclare name='Label' appinfo='A flat label for one tour stop: text facing that stop camera, on a dark chip. Placed and measured by the generator.'>
      <ProtoInterface>
        <field accessType='inputOutput' name='translation' type='SFVec3f' value='0 0 0'/>
        <field accessType='inputOutput' name='rotation' type='SFRotation' value='0 0 1 0'/>
        <field accessType='inputOutput' name='scale' type='SFVec3f' value='1 1 1' appinfo='the font size in scene units, on all three axes'/>
        <field accessType='inputOutput' name='string' type='MFString' value='""'/>
        <field accessType='initializeOnly' name='color' type='SFColor' value='0.95 0.92 0.85'/>
        <field accessType='initializeOnly' name='chipAt' type='SFVec3f' value='0 0 -0.02'/>
        <field accessType='initializeOnly' name='chipScale' type='SFVec3f' value='1 1 1'/>
        <field accessType='outputOnly' name='textBounds' type='SFVec2f' appinfo='the drawn text box, for the gate that measures label overlap'/>
        <field accessType='outputOnly' name='origin' type='SFVec3f'/>
      </ProtoInterface>
      <ProtoBody>
        <Transform>
          <IS><connect nodeField='translation' protoField='translation'/><connect nodeField='rotation' protoField='rotation'/><connect nodeField='scale' protoField='scale'/></IS>
          <Shape>
            <Appearance><UnlitMaterial><IS><connect nodeField='emissiveColor' protoField='color'/></IS></UnlitMaterial></Appearance>
            <Text><IS><connect nodeField='string' protoField='string'/><connect nodeField='textBounds' protoField='textBounds'/><connect nodeField='origin' protoField='origin'/></IS><FontStyle family='"@FONT_FILE@" "TYPEWRITER"' size='1' justify='"BEGIN" "MIDDLE"'/></Text>
          </Shape>
          <Transform><IS><connect nodeField='translation' protoField='chipAt'/><connect nodeField='scale' protoField='chipScale'/></IS>
            <Shape><Appearance><UnlitMaterial emissiveColor='0.06 0.052 0.046' transparency='0.12'/></Appearance>
              <IndexedTriangleSet index='0 1 2 0 2 3' solid='false'><Coordinate point='0 -0.62 0 1 -0.62 0 1 0.62 0 0 0.62 0'/></IndexedTriangleSet></Shape>
          </Transform>
        </Transform>
      </ProtoBody>
    </ProtoDeclare>""".replace('@FONT_FILE@', FONT_FILE)


def lines_shape(defname, polylines, colors, width, mat_def, transparency=0.0, coord_def=None, linetype=None, coord_use=None, single=None):
    pts, idx = [], []
    for pl in polylines:
        b = len(pts); pts += pl; idx += list(range(b, b + len(pl))) + [-1]
    lp = "<LineProperties linewidthScaleFactor='%s'%s/>" % (fm(width), " linetype='%d'" % linetype if linetype else '')
    mat = "<UnlitMaterial%s emissiveColor='%s'%s/>" % (" DEF='%s'" % mat_def if mat_def else '', v3(single or (1, 1, 1)), " transparency='%s'" % fm(transparency) if transparency else '')
    coord = "<Coordinate USE='%s'/>" % coord_use if coord_use else "<Coordinate%s point='%s'/>" % (" DEF='%s'" % coord_def if coord_def else '', ' '.join(v3(p) for p in pts))
    col_xml = '' if single else "<Color color='%s'/>" % ' '.join(v3(c) for c in colors)
    return ("<Shape%s><Appearance>%s%s</Appearance><IndexedLineSet colorPerVertex='false' coordIndex='%s'>%s%s</IndexedLineSet></Shape>"
            % (" DEF='%s'" % defname if defname else '', mat, lp, ' '.join(map(str, idx)), col_xml, coord))


def tri_shape(quads, colors, mat_def=None, transparency=0.0):
    """flat quads (4 corners each) as one IndexedTriangleSet with one colour per corner"""
    pts, idx, cols = [], [], []
    for q, c in zip(quads, colors):
        b = len(pts); pts += q; cols += [c] * 4; idx += [b, b + 1, b + 2, b, b + 2, b + 3]
    return ("<Shape><Appearance><UnlitMaterial%s%s/></Appearance><IndexedTriangleSet solid='false' index='%s'><Color color='%s'/><Coordinate point='%s'/></IndexedTriangleSet></Shape>"
            % (" DEF='%s'" % mat_def if mat_def else '', " transparency='%s'" % fm(transparency) if transparency else '', ' '.join(map(str, idx)), ' '.join(v3(c) for c in cols), ' '.join(v3(p) for p in pts)))


def trace_lines(L, chain, dz=-0.015):
    """the tour's silver thread for one subject: each ancestor's thread up to the next one's birth, a level link to that child's bead, and the
    subject's whole thread (through its move)"""
    P, Y = L['P'], L['Y']; out = []
    for i, pid in enumerate(chain):
        top_ = P[chain[i + 1]]['born'] if i + 1 < len(chain) else L['end'][pid]
        pts = []
        for pc in L['T'][pid]['pieces']:
            lo_, hi_ = max(pc['y0'], P[pid]['born']), min(pc['y1'], top_)
            if lo_ <= hi_: pts += [(pc['x'], Y(lo_), pc['z'] + dz), (pc['x'], Y(hi_), pc['z'] + dz)]
        if len(pts) >= 2: out.append(pts)
        if i + 1 < len(chain):
            c = chain[i + 1]; xa_, za = L['pos_at'](pid, P[c]['born']); pc0 = L['T'][c]['pieces'][0]
            out.append([(xa_, Y(P[c]['born']), za + dz), (pc0['x'], Y(P[c]['born']), pc0['z'] + dz)])
    return out


def label_group(defname, labels, rot):
    items = []
    for lb in labels:
        sz = lb['size']; o = lb['origin']
        fv = ["<fieldValue name='translation' value='%s'/>" % v3(o)]
        if abs(rot[3]) > 1e-6: fv.append("<fieldValue name='rotation' value='%s'/>" % v3(rot))
        fv.append("<fieldValue name='scale' value='%s %s %s'/>" % (fm(sz), fm(sz), fm(sz)))
        fv.append("<fieldValue name='string' value='%s'/>" % xa(mfs([lb['text']])))
        if lb['color'] != NAME_C: fv.append("<fieldValue name='color' value='%s'/>" % v3(lb['color']))
        fv.append("<fieldValue name='chipAt' value='%s 0 -0.03'/>" % fm(-CHIP_PAD))
        fv.append("<fieldValue name='chipScale' value='%s 1 1'/>" % fm(CHAR_W * len(lb['text']) + 2 * CHIP_PAD))
        items.append("<ProtoInstance name='Label'>%s</ProtoInstance>" % ''.join(fv))
    return "<Group DEF='%s'>%s</Group>" % (defname, ''.join(items))


def leader_group(defname, labels):
    """the leader lines of a stop's subject labels that could not sit on their thread's row (a separate Switch, so a label group holds only Labels)"""
    leads = [lb['leader'] for lb in labels if lb.get('leader')]
    return "<Group DEF='%s'>%s</Group>" % (defname, lines_shape(None, leads, None, 1.4, None, single=SUBJ_C) if leads else '')


def clip_pad(st, Y):
    """how far above the stop's fell its label chips reach (an oblique camera lifts a label toward itself, and so upward): the page lifts the
    label clip plane by this much while the stop is bound, so no label of the stop is cut"""
    top_ = -1e9
    for lb in st['labels'] + st['labels_phone']:
        cam = st['cam_phone'] if lb in st['labels_phone'] else st['cam']; right, up, back = cam['basis']; sz = lb['size']
        for xx in (-CHIP_PAD * sz, lb['width'] + CHIP_PAD * sz):
            for yy in (-CHIP_Y * sz, CHIP_Y * sz):
                top_ = max(top_, add(add(lb['origin'], right, xx), up, yy)[1])
    return round(max(0.0, top_ - Y(st['fell']) - 0.05) + 0.02, 3)


def build_family(F, view, asof, frame_url=None):
    L = plan(F, asof); P, Y, col, used = L['P'], L['Y'], L['col'], L['used']
    dyes = F['dyes']; key = F['key']
    x_lo, x_hi = min(col[h]['x0'] for h in used), max(col[h]['x1'] for h in used)
    z_lo, z_hi = min(col[h]['z'] for h in used), max(col[h]['z'] for h in used)
    ytop = Y(L['top'])
    # ---- warp: one polyline per thread (through a dated move); a move with no year in the data is a separate DOTTED segment
    sets = {'core': [], 'inlaw': [], 'dashed': [], 'faint': [], 'moves_est': []}; colors = {k: [] for k in sets}; info = {}
    for pid in L['order']:
        p = P[pid]; c = thread_color(p, dyes); st, why = style_of(p, dyes)
        pcs = L['T'][pid]['pieces']; polys = []
        first_u = min((u['year'] for u in L['U_of'].get(pid, [])), default=None)
        for k, pc in enumerate(pcs):
            ya = pc['y0']
            if k == 0 and st == 'inlaw' and first_u is not None and p['born'] < first_u < pc['y1']:
                sets['faint'].append([(pc['x'], Y(pc['y0']), pc['z']), (pc['x'], Y(first_u), pc['z'])]); colors['faint'].append(c); ya = first_u
            polys.append([(pc['x'], Y(ya), pc['z']), (pc['x'], Y(pc['y1']), pc['z'])])
        if len(pcs) == 2:
            if L['est'](pid):
                sets['moves_est'].append([(pcs[0]['x'], Y(pcs[0]['y1']), pcs[0]['z']), (pcs[1]['x'], Y(pcs[1]['y0']), pcs[1]['z'])]); colors['moves_est'].append(c)
            else: polys = [polys[0] + polys[1]]
        for pl in polys: sets[st].append(pl); colors[st].append(c)
        info[pid] = dict(style=st, why=why, color=[round(x, 3) for x in c])
    # ---- wefts, and an open diamond on the mover's end of each pick a thread crosses on
    wl, wc, wl_close, wl_est = [], [], [], []
    for u in F['unions']:
        xa_, za = L['pos_at'](u['a'], u['year']); xb, zb = L['pos_at'](u['b'], u['year']); y = Y(u['year'])
        if u.get('year_precision') == 'unknown': wl_est.append([(xa_, y, za), (xb, y, zb)])
        elif u.get('close'): wl_close += [[(xa_, y + 0.035, za), (xb, y + 0.035, zb)], [(xa_, y - 0.035, za), (xb, y - 0.035, zb)]]
        else: wl.append([(xa_, y, za), (xb, y, zb)])
        if u.get('close') and u.get('year_precision') == 'unknown': wl_close += [[(xa_, y + 0.035, za), (xb, y + 0.035, zb)], [(xa_, y - 0.035, za), (xb, y - 0.035, zb)]]
    dq = []
    for u in F['unions']:
        for x in L['cross'].get(u['id'], []):
            if L['move'][x][0] != u['year']: continue
            xx, zz = L['pos_at'](x, u['year']); y = Y(u['year']); r = BEAD * 1.8; z = zz + 0.016
            dq.append([(xx, y - r, z), (xx + r, y, z), (xx, y + r, z), (xx - r, y, z), (xx, y - r, z)])
    # ---- beads, panels, grid
    bq, bc = [], []
    for pid in L['order']:
        pc = L['T'][pid]['pieces'][0]; x, y, z = pc['x'], Y(P[pid]['born']), pc['z'] + 0.012
        bq.append([(x, y - BEAD, z), (x + BEAD, y, z), (x, y + BEAD, z), (x - BEAD, y, z)]); bc.append(tuple(min(1.0, v * 1.08) for v in thread_color(P[pid], dyes)))
    pq, pcol = [], []
    for h in used:
        ys = [pc for pid in P for pc in L['T'][pid]['pieces'] if pc['h'] == h]
        a, b = min(pc['y0'] for pc in ys), max(pc['y1'] for pc in ys); z = col[h]['z'] - 0.04
        x0, x1 = col[h]['x0'] - 0.22, col[h]['x1'] + 0.22
        pq.append([(x0, Y(a) - 0.4, z), (x1, Y(a) - 0.4, z), (x1, Y(b) + 0.4, z), (x0, Y(b) + 0.4, z)]); pcol.append(PANEL_C)
        hh = L['HS'][h]; oa = max(a, hh.get('opened') or a); ob = min(b, hh.get('closed') or b)
        if ob > oa:
            pq.append([(x0 + 0.06, Y(oa), z + 0.006), (x1 - 0.06, Y(oa), z + 0.006), (x1 - 0.06, Y(ob), z + 0.006), (x0 + 0.06, Y(ob), z + 0.006)]); pcol.append(BAND_C)
    grid = [[(x_lo - 0.8, Y(yv), z_lo - 0.08), (x_hi + 0.8, Y(yv), z_lo - 0.08)] for yv in range(L['y0'], L['top'] + 1, 25)]
    rail = [[(x_lo - 0.8, 0.0, z_hi), (x_lo - 0.8, ytop, z_hi)]] + [[(x_lo - 0.95, Y(e['year']), z_hi), (x_lo - 0.65, Y(e['year']), z_hi)] for e in F.get('events', [])]
    # ---- stops: a desktop and a phone camera each, their labels, the subject's silver thread, the fell and the label clip allowance
    stops = gen_stops(F, L, asof)
    for st in stops:
        cam = stop_camera(st, L); cam['lift'] = (z_hi - z_lo) + 0.4; cam['zfront'] = z_hi + 0.12; st['cam'] = cam
        st['labels'] = stop_labels(st, L, F, cam)
        camp = stop_camera(st, L, phone=True); camp['lift'] = cam['lift']; camp['zfront'] = cam['zfront']; st['cam_phone'] = camp
        st['labels_phone'] = stop_labels(st, L, F, camp, phone=True)
        st['clip_pad'] = clip_pad(st, Y)
        st['trace'] = [pl for x in st['subject'] for pl in trace_lines(L, st['lineage'][x])]
        st['rings'] = []
        for x in st['subject']:
            pc = L['T'][x]['pieces'][0]; c0 = (pc['x'], Y(P[x]['born']), pc['z'] + 0.02); r = size_for(13.0, c0, cam)
            st['rings'].append([(c0[0] + r * math.cos(2 * math.pi * k / 24), c0[1] + r * math.sin(2 * math.pi * k / 24), c0[2]) for k in range(25)])
    # ---- write
    stamp = drum.build_date().isoformat()
    S = []
    w = lambda s, ind=4: S.append(' ' * ind + s)
    head = ["<?xml version='1.0' encoding='UTF-8'?>",
            "<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>",
            "  <head>", "    <component name='Shape' level='2'/>", "    <component name='Rendering' level='5'/>"]
    dyes_txt = ', '.join('%s (%s)' % (hue_name(d['color']), dk) for dk, d in dyes.items())
    meta = [('title', key + '.x3d'), ('description', 'Tapestry loom (layout v2) for the %s family: time runs up, houses west to east by longitude, latitude as depth; each life an upright warp thread, each marriage a level weft pick (doubled when close), the dye %s the share of descent from the founders. Generated; do not edit.' % (F['name'], dyes_txt)),
            ('generator', 'build_loom_scene.py (' + stamp + ')'), ('created', stamp), ('data', '%s (%s, built by %s)' % (os.path.basename(view['_path']), view['_sha'][:12], view.get('built', {}).get('by'))),
            ('license', 'genealogical facts as harvested (see the cards sidecar for sources per person); scene generated')]
    head += ["    <meta name='%s' content='%s'/>" % (k, xa(v)) for k, v in meta] + ["  </head>", "  <Scene>"]
    w("<WorldInfo title='%s' info='%s'/>" % (xa('Loom · ' + F['name']), xa(mfs(['Warp = lives, weft = marriages, dye = share of descent from the founders: %s.' % dyes_txt, 'Cards and captions: %s.cards.json (read by the page).' % key]))))
    w("<Background skyColor='%s'/>" % SKY)
    w("<NavigationInfo type='\"EXAMINE\" \"ANY\"' avatarSize='%s 1.6 0.75' headlight='false' speed='4' transitionType='\"ANIMATE\"' transitionTime='1.4'/>" % fm(AVATAR))
    w(LABEL_PROTO)
    w("<!-- Tour stops (report 07), bound by the page; the first is bound at load. Then the same stops framed for a portrait phone (_ph). -->")
    for st in stops:
        st['def'] = 'VP_' + st['key']; st['def_phone'] = 'VP_' + st['key'] + '_ph'
    for st, cam, dn in [(st, st['cam'], st['def']) for st in stops] + [(st, st['cam_phone'], st['def_phone']) for st in stops]:
        w("<Viewpoint DEF='%s' description='%s' position='%s' orientation='%s' centerOfRotation='%s' fieldOfView='%s'/>" % (
            dn, xa(st['title']), v3(cam['pos']), v3(cam['rot']), v3(cam['target']), fm(cam['fov'])))
    w("<!-- The cloth: house panels (the touch surface, coplanar with each house's threads), then the woven cloth below the fell. -->")
    w("<Group DEF='Cloth'>")
    w("<TouchSensor DEF='ClothTouch' description='a thread'/>", 6)
    w(tri_shape(pq, pcol), 6)
    w("<Group DEF='Woven'>", 6)
    w("<ClipPlane DEF='FellClip' plane='0 -1 0 %s'/>" % fm(ytop + 0.05), 8)
    w("<!-- Per stop with a subject (Switch whichChoice = the stop's marks index in the cards, set by the page): the tour's silver thread from a founder to the subject, and a ring at its bead. -->", 8)
    mk = []
    for st in stops:
        parts = []
        if st['trace']: parts.append(lines_shape(None, st['trace'], None, 5.0, None, single=TOUR_C))
        if st['rings']: parts.append(lines_shape(None, st['rings'], None, 2.4, None, single=TOUR_C))
        st['marks'] = len(mk) if parts else -1
        if parts: mk.append("<Group DEF='Marks_%s'>%s</Group>" % (st['key'], ''.join(parts)))
    if mk: w("<Switch DEF='Marks' whichChoice='%d'>%s</Switch>" % (stops[0]['marks'], ''.join(mk)), 8)
    widths = {'core': 2.6, 'inlaw': 1.9, 'dashed': 2.2, 'faint': 1.4, 'moves_est': 2.0}
    for k in ('faint', 'inlaw', 'dashed', 'core', 'moves_est'):
        if sets[k]:
            w(lines_shape('Warp_' + k, sets[k], colors[k], widths[k], 'WarpMat_' + k, transparency=0.6 if k == 'faint' else 0.0, coord_def='WarpC_' + k,
                          linetype=2 if k == 'dashed' else 3 if k == 'moves_est' else None), 8)
    if wl: w(lines_shape('Weft', wl, None, 1.8, 'WeftMat', single=WEFT_C), 8)
    if wl_est: w(lines_shape('WeftEst', wl_est, None, 1.6, 'WeftEstMat', transparency=0.55, single=WEFT_C), 8)
    if wl_close: w(lines_shape('WeftClose', wl_close, None, 2.0, 'WeftCloseMat', single=CLOSE_C), 8)
    if dq: w(lines_shape('MoverEnds', dq, None, 1.8, 'MoverMat', single=SEL_C), 8)
    w(tri_shape(bq, bc, mat_def='BeadMat'), 8)
    w("</Group>", 6)
    w("</Group>")
    w("<!-- Above the fell: the bare warp (the same coordinates, dim). -->")
    w("<Group DEF='Ghost'><ClipPlane DEF='GhostClip' plane='0 1 0 %s'/>" % fm(-(ytop + 0.05)))
    for k in ('faint', 'inlaw', 'dashed', 'core', 'moves_est'):
        if sets[k]:
            w(lines_shape(None, sets[k], None, 1.0, 'GhostMat_' + k, transparency=0.55, coord_use='WarpC_' + k, single=(0.42, 0.38, 0.33)), 6)
    w("</Group>")
    w("<Group DEF='Rails'>%s%s</Group>" % (lines_shape(None, grid, None, 1.0, 'GridMat', single=GRID_C), lines_shape(None, rail, None, 1.4, 'RailMat', single=tuple(c * 0.7 for c in GOLD))))
    w("<!-- The fell: the present-year plane the page moves (translation y = the year); each stop sets it to the stop's own year. -->")
    fz0, fz1 = z_lo - 0.6, z_hi + 0.6
    w("<Transform DEF='Fell' translation='0 %s 0'>%s%s</Transform>" % (fm(ytop), tri_shape([[(x_lo - 0.9, 0, fz0), (x_hi + 0.9, 0, fz0), (x_hi + 0.9, 0, fz1), (x_lo - 0.9, 0, fz1)]], [GOLD], mat_def='FellMat', transparency=0.86),
                                                                      lines_shape(None, [[(x_lo - 0.9, 0, fz1), (x_hi + 0.9, 0, fz1)]], None, 2.0, 'FellEdgeMat', single=GOLD)))
    w("<!-- The selection: the page writes the picked thread's points here (no Script, no ROUTE). -->")
    w("<Group DEF='Selection'><Shape><Appearance><UnlitMaterial emissiveColor='%s'/><LineProperties linewidthScaleFactor='4.5'/></Appearance><LineSet DEF='SelLine' vertexCount='2'><Coordinate DEF='SelCoord' point='0 -1000 0 0 -1000 0'/></LineSet></Shape>"
      "<Transform DEF='SelHalo' scale='0 0 0'><Shape><Appearance><UnlitMaterial emissiveColor='%s'/><LineProperties linewidthScaleFactor='3'/></Appearance><IndexedLineSet coordIndex='%s -1'><Coordinate point='%s'/></IndexedLineSet></Shape></Transform></Group>" % (
        v3(SEL_C), v3(SEL_C), ' '.join(str(k) for k in range(25)), ' '.join(v3((0.2 * math.cos(2 * math.pi * k / 24), 0.2 * math.sin(2 * math.pi * k / 24), 0.02)) for k in range(25))))
    w("<!-- Labels: one group per stop for the desktop (Labels) and for a portrait phone (LabelsPhone); the page shows one, by the stop's index. Clipped by the fell like the cloth, lifted by the stop's clip_pad. -->")
    w("<Group DEF='LabelLayer'><ClipPlane DEF='LabelClip' plane='0 -1 0 %s'/>" % fm(ytop + 0.05))
    for sw_, k_, cam_k, which in (('Labels', 'labels', 'cam', 0), ('LabelsPhone', 'labels_phone', 'cam_phone', -1)):
        w("<Switch DEF='%s' whichChoice='%d'>" % (sw_, which), 6)
        for st in stops:
            w(label_group(sw_ + '_' + st['key'], st[k_], st[cam_k]['rot']), 8)
        w("</Switch>", 6)
    for sw_, k_, ik in (('Leaders', 'labels', 'leaders'), ('LeadersPhone', 'labels_phone', 'leaders_phone')):
        gs = []
        for st in stops:
            st[ik] = len(gs) if any(lb.get('leader') for lb in st[k_]) else -1
            if st[ik] >= 0: gs.append(leader_group(sw_ + '_' + st['key'], st[k_]))
        if gs: w("<Switch DEF='%s' whichChoice='%d'>%s</Switch>" % (sw_, stops[0][ik] if ik == 'leaders' else -1, ''.join(gs)), 6)
    w("</Group>")
    w("<!-- Hook for the baked loom frame (proto/bake/out/page/loom.x3d). That bake hangs its warp round the orb (a clearance sphere of radius 43.5),"
      " so it does not compose with a flat cloth; a flat-warp bake can be inlined here (the frame-url option), fitted to the cloth's bounds and loaded lazily. -->")
    if frame_url:
        sx = (x_hi - x_lo + 3.0) / 100.0
        w("<Group DEF='FrameHook'><Transform translation='0 %s %s' scale='%s %s %s'><Inline DEF='FrameInline' load='false' url='%s'/></Transform></Group>" % (
            fm(ytop / 2), fm(z_lo - 1.0), fm(sx), fm(sx), fm(sx), xa(mfs([frame_url]))))
    else:
        w("<!-- FrameHook: empty in this build (no flat-warp bake yet). -->")
    text = '\n'.join(head) + '\n' + '\n'.join(S) + '\n  </Scene>\n</X3D>\n'
    return text, L, stops, info, dict(x=[x_lo, x_hi], z=[z_lo, z_hi], ytop=ytop)


def cards(F, L, stops, info, bounds, view, asof):
    P = L['P']; HS = L['HS']
    kids = {}
    for pid in P:
        for q in (P[pid].get('father'), P[pid].get('mother')):
            if q in P: kids.setdefault(q, []).append(pid)
    people = {}
    for pid in L['order']:
        p = P[pid]; mv = L['move'].get(pid)
        people[pid] = dict(name=p['name'], label=label_text(L, pid), short=p.get('short'), qid=p.get('qid'), sex=p.get('sex'),
                           born=p['born'], born_precision=p.get('born_precision'), died=p.get('died'), died_precision=p.get('died_precision'),
                           house=p['house'], house_name=HS[p['house']]['name'], core=bool(p.get('core')), family=p.get('family'),
                           grade=p.get('confidence'), note=p.get('note'), sources=p.get('sources') or [], wikipedia=p.get('wikipedia'),
                           shares={k: frac(float(v or 0)) for k, v in (p.get('shares') or {}).items()}, generation=p.get('generation'),
                           father=p.get('father'), mother=p.get('mother'), children=sorted(kids.get(pid, []), key=lambda c: (P[c]['born'], c)),
                           unions=[u['id'] for u in sorted(L['U_of'].get(pid, []), key=lambda u: u['year'])],
                           childhood_house=L['child'].get(pid), born_in=L['born_in'].get(pid),
                           move=dict(year=mv[0], kind=mv[1], why=mv[2], estimated=L['est'](pid), **{k: v for k, v in L['meta'].get(pid, {}).items() if k in ('grade', 'source', 'role', 'uid', 'spouse')}) if mv else None,
                           pieces=[[pc['h'], pc['x'], pc['z'], pc['y0'], pc['y1']] for pc in L['T'][pid]['pieces']], **info[pid])
    unions = {u['id']: dict(u) for u in F['unions']}
    for u in unions.values():
        xa_, za = L['pos_at'](u['a'], u['year']); xb, zb = L['pos_at'](u['b'], u['year']); u['pts'] = [[round(xa_, 4), round(za, 4)], [round(xb, 4), round(zb, 4)]]
    st_out = []
    camj = lambda cam: dict(position=[round(c, 4) for c in cam['pos']], orientation=[round(c, 6) for c in cam['rot']], fov=cam['fov'], target=[round(c, 4) for c in cam['target']], dist=round(cam['dist'], 3),
                            frame_w=round(cam['frame_w'], 3), frame_h=round(cam['frame_h'], 3), viewport=[cam['vw'], cam['vh']], safe_area=cam['safe'])
    labj = lambda ls: [dict(text=l['text'], kind=l['kind'], ref=l['ref'] if not isinstance(l['ref'], (int, float)) else str(l['ref']), box=[round(c, 1) for c in l['box']],
                            **({'at': l['at']} if l.get('at') and l['kind'] in ('name', 'union', 'note') else {}), **({'subject': True} if l.get('subject') else {}), **({'leader': True} if l.get('leader') else {})) for l in ls]
    for i, st in enumerate(stops):
        st_out.append(dict(index=i, n=st['n'], key=st['key'], def_=st['def'], title=st['title'], years=st['years'], focus=st['focus'][:20], unions=st['unions'],
                           subject=st['subject'], lineage=st['lineage'], fell=st['fell'], clip_pad=st['clip_pad'], marks=st['marks'], leaders=st['leaders'],
                           narration=st['narration'], computed=st['computed'], camera=camj(st['cam']), labels=labj(st['labels']),
                           phone=dict(def_=st['def_phone'], camera=camj(st['cam_phone']), labels=labj(st['labels_phone']), leaders=st['leaders_phone'])))
    cols = [dict(key=h, name=HS[h]['name'], lon=HS[h].get('lon'), lat=HS[h].get('lat'), opened=HS[h].get('opened'), closed=HS[h].get('closed'), note=HS[h].get('note'),
                 x0=round(L['col'][h]['x0'], 4), x1=round(L['col'][h]['x1'], 4), z=round(L['col'][h]['z'], 4)) for h in L['used']]
    return dict(version='loom-cards/1', family=F['key'], name=F['name'], asof=asof, dyes={dk: dict(d, hue=hue_name(d['color'])) for dk, d in F['dyes'].items()}, houses=cols,
                layout=dict(TY=TY, Y0=L['y0'], top=L['top'], LX=round(LX * L['kx'], 5), HOUSE_GAP=round(HOUSE_GAP * L['kx'], 5), KX=L['kx'], KZ=KZ, bounds=bounds, design_viewport=[W, H], safe_area=SAFE,
                            phone_viewport=[PW, PH], phone_safe_area=PSAFE),
                ramp=dye_ramp(F['dyes']),
                people=people, unions=unions, events=F.get('events', []), stops=st_out,
                ladder={'1': 'VP_cloth', '2': 'VP_wide', '3': 'fell', '4': next((s['def'] for s in stops if s['key'] == 'arrows'), 'VP_wide'), '5': None, '6': None, '7': 'person', '8': 'fiber'},
                data=dict(file=os.path.basename(view['_path']), sha256=view['_sha'], built_by=view.get('built', {}).get('by')))


# ---------------------------------------------------------------- scene gates (fix round 09) and the data list
# Claims the review made that the file cannot settle: listed for the data stage, never drawn. Grades: S = unchecked here.
DATA_NOTES = {
    'rothschild': [dict(id='james_edouard', grade='S', source='fix round 09, from memory (unchecked)',
                        issue='"James Edouard de Rothschild" 1878-1957, father Alphonse, house Paris, has the years of James Armand de Rothschild (Q6128825, 1878-1957, son of Edmond, also in the file): probably one man recorded twice, once with a wrong parent. Check before merging.')],
    'darwin_wedgwood': [dict(id='Charles Darwin x Emma Darwin (nee Wedgwood)', grade='S', source='review 08', issue='They married in 1839 (the file leaves the year null; drawn 1838?) and moved to Down House in 1842 (no move year in the file).'),
                        dict(id='Robert Darwin x Susannah Darwin (nee Wedgwood)', grade='S', source='review 08', issue='Robert was at The Mount, Shrewsbury, from 1786; Susannah joined him at the 1796 marriage. The file has neither year.'),
                        dict(id='Josiah Wedgwood III', grade='S', source='review 08', issue='He moved to Leith Hill Place in 1847 (not in the file; drawn on the estimated wedding pick).')]}
CONTRACT_REQUESTS = ['loom-view: an optional person field moved = {year, grade, source} (the dated move into the adult house); build_loom_scene.py reads it before its own seed.',
                     'loom-view: define house opened/closed. proto/ingest/loomview.py writes the first birth and last death of the house\'s core members; a reader takes "closed" for a closing date.']


def rail_z(st, L):
    """the depth the stop's year rail is read at: its subject's (or focus's) houses, else the middle of the cloth"""
    col = L['col']; ids = st.get('subject') or st.get('focus') or []
    zs = [pc['z'] for x in ids if x in L['T'] for pc in L['T'][x]['pieces']]
    if st['kind'] in ('cloth', 'wide') or st.get('houses') and len(st['houses']) > 2 or not zs:
        zz = [col[h]['z'] for h in L['used']]; return (min(zz) + max(zz)) / 2
    return (min(zs) + max(zs)) / 2


def year_error(st, L, cam):
    """the perspective error: for every bead visible in the frame within the rail's years, the year a reader takes off the rail minus its own"""
    P, Y = L['P'], L['Y']; zr = rail_z(st, L); xl = cam_left_x(st, L, cam); out = []; sa = cam['safe']; ya, yb = st_years_visible(st, L, cam)
    def rail_year(sy):
        lo, hi = L['y0'] - 400, L['top'] + 400
        for _ in range(50):
            m = (lo + hi) / 2; q = project((xl, Y(m), zr), cam)[1]
            if q > sy: lo = m
            else: hi = m
        return (lo + hi) / 2
    for pid in P:
        if not ya <= P[pid]['born'] <= yb: continue
        pc = L['T'][pid]['pieces'][0]; q = project((pc['x'], Y(P[pid]['born']), pc['z']), cam)
        if not q or not (sa['x0'] <= q[0] <= sa['x1'] and sa['y0'] <= q[1] <= sa['y1']): continue
        out.append(abs(rail_year(q[1]) - P[pid]['born']))
    return round(max(out), 2) if out else 0.0, len(out)


def scene_gates(F, L, stops):
    """hard gates (raise) and measured ones (recorded) on the drawn scene, before anything is written"""
    P = L['P']; U = {u['id']: u for u in F['unions']}; errs, g = [], {}
    # moves: every drawn move has its reason, and an estimated move never stands where a dated reason exists
    mv = []
    for pid, (y, kind, why) in L['move'].items():
        m = L['meta'].get(pid, {}); hh = P[pid]['house']
        mine = [u for u in L['U_of'].get(pid, []) if P[L['oth'](u, pid)]['house'] == hh]
        if kind == 'record' and y != max(P[pid]['born'] + 1, min(L['rec'][pid]['year'], L['end'][pid] - 1)): errs.append('%s: record move drawn %d, record %d' % (pid, y, L['rec'][pid]['year']))
        if kind == 'wedding' and (m.get('uid') not in U or U[m['uid']]['year'] != y): errs.append('%s: wedding move %d is not on its pick' % (pid, y))
        if kind == 'estimated' and mine: errs.append('%s: estimated move at %d although it marries into %s (%s)' % (pid, y, hh, mine[0]['id']))
        if kind == 'estimated' and any(u['year'] < y for u in mine): errs.append('%s: estimated move after a pick into the house' % pid)
        if kind == 'follows' and L['move'].get(m.get('spouse'), (None,))[0] != y: errs.append('%s: follows a spouse who does not move in %d' % (pid, y))
        mv.append(dict(id=pid, name=P[pid]['name'], frm=L['child'][pid], to=hh, year=None if L['est'](pid) else y, drawn=y, kind=kind, estimated=L['est'](pid), **{k: m[k] for k in ('role', 'grade', 'source') if k in m}))
    for st in stops:
        for line in [c['text'] for c in st['computed']]:
            for pid in L['move']:
                if L['est'](pid):
                    nm = P[pid].get('short') or P[pid]['name'].split(',')[0]
                    if re.search(re.escape(nm) + r'[^.;]{0,60}\b%d\b' % L['move'][pid][0], line): errs.append('stop %s prints the estimated move year of %s' % (st['key'], pid))
    loose = []
    for u in F['unions']:
        for x in (u['a'], u['b']):
            if not any(pc['y0'] <= u['year'] <= pc['y1'] for pc in L['T'][x]['pieces']): loose.append([u['id'], x, u['year']])
    g['moves'] = dict(ok=not errs, drawn=len(mv), by_kind={k: sum(1 for m in mv if m['kind'] == k) for k in sorted({m['kind'] for m in mv})}, estimated=sum(1 for m in mv if m['estimated']),
                      picks_with_mover_diamond=sum(len(v) for v in L['cross'].values()), picks_off_a_thread=loose, errors=errs[:20], moves=sorted(mv, key=lambda m: (m['drawn'], m['id'])))
    # the dye ramp: neighbouring shares from 1 down to 1/4 differ by at least 12 dE76 on every dye
    rp = dye_ramp(F['dyes']); g['dye_ramp'] = dict(ok=all(min(r['dE76'][:3]) >= 12 for r in rp.values()), ramp=rp, rule='dE76 >= 12 for 1-3/4, 3/4-1/2, 1/2-1/4')
    # perspective: the year read off the rail for each visible bead, front stops (desktop)
    per = {st['key']: dict(zip(('max_error_years', 'beads'), year_error(st, L, st['cam']))) for st in stops if st['kind'] != 'wide'}
    g['rail_reading'] = dict(ok=all(v['max_error_years'] <= 1.0 for v in per.values()), rule='max |rail year - bead year| <= 1.0 over visible beads, front stops', stops=per)
    # subjects labelled; names on their rows
    sub = {}
    for st in stops:
        for var, ls in (('desktop', st['labels']), ('phone', st['labels_phone'])):
            have = {l['ref'] for l in ls if l['kind'] == 'name'}
            miss = [x for x in st['subject'] if x not in have and anchor_of(st, L, x) is not None]
            if miss: sub.setdefault(var, []).append([st['key'], miss])
    g['subjects_labelled'] = dict(ok=not sub.get('desktop'), missing=sub, rule='every subject with a thread in the window has a label (desktop: hard; phone: recorded)')
    far = []
    for st in stops:
        for var, ls in (('desktop', st['labels']), ('phone', st['labels_phone'])):
            for l in ls:
                if l['kind'] != 'name' or l.get('leader') or not l.get('at'): continue
                bx = l['box']; ax, ay = l['at']; dx = max(bx[0] - ax, 0, ax - (bx[0] + bx[2])); dy = max(bx[1] - ay, 0, ay - (bx[1] + bx[3]))
                if dx > LEADER_PX or dy > 0.5 * bx[3]: far.append([st['key'], var, l['text'], round(dx), round(dy)])
    g['names_on_their_rows'] = dict(ok=not far, far=far[:20], leaders=sum(1 for st in stops for l in st['labels'] + st['labels_phone'] if l.get('leader')),
                                    rule='a name without a leader sits within %d px across and half a chip up or down of its thread anchor' % LEADER_PX)
    g['phone_labels'] = dict(stops=len(stops), names=[sum(1 for l in st['labels_phone'] if l['kind'] == 'name') for st in stops],
                             min_text_px=round(min((l['box'][3] / (2 * CHIP_Y) for st in stops for l in st['labels_phone']), default=0), 1))
    if errs: raise SystemExit('%s: move gate failed:\n  ' % F['key'] + '\n  '.join(errs[:20]))
    return g


def data_issues(F, L, stops):
    P = L['P']; out = dict(family=F['key'], computed=[], from_review=DATA_NOTES.get(F['key'], []))
    for p in F['people']:
        for k in ('father', 'mother'):
            q = P.get(p.get(k))
            if not q: continue
            gap = p['born'] - q['born']; dead = q.get('died') is not None and q['died'] < p['born'] - (1 if k == 'father' else 0)
            if gap < 15 or gap > 60 or dead: out['computed'].append(dict(id=p['id'], grade='∑', issue='%s %s (b. %d) is %d years older%s' % (k, q['id'], q['born'], gap, ', dead before the birth' if dead else '')))
    for h, y_ in CLOSINGS.get(F['key'], {}).items():
        c = L['HS'].get(h, {}).get('closed')
        if c is not None and c != y_: out['computed'].append(dict(id='house:' + h, grade='∑', issue='house "closed" %d is the last death among its core members; the narration (report 07, C) closes the house in %d' % (c, y_)))
    first = lambda q: re.sub(r'[^a-z]', '', (q['name'].split()[0] if q.get('name') else '').lower())
    ppl = sorted(F['people'], key=lambda q: q['id'])
    for i, q in enumerate(ppl):
        for r in ppl[i + 1:]:
            if q['born'] == r['born'] and q.get('died') is not None and q.get('died') == r.get('died') and first(q) == first(r):
                out['computed'].append(dict(id='%s / %s' % (q['id'], r['id']), grade='∑', issue='same first name and the same years (%d-%d): %s and %s, fathers %s and %s; possibly one person twice' % (
                    q['born'], q['died'], q['name'], r['name'], q.get('father'), r.get('father'))))
    for m in L['move_issues']: out['computed'].append(dict(m, grade='∑'))
    for u in F['unions']:
        for x in (u['a'], u['b']):
            if not (P[x]['born'] < u['year'] <= L['end'][x]): out['computed'].append(dict(id=u['id'], grade='∑', issue='union year %s outside the life of %s (%s-%s)' % (u['year'], x, P[x]['born'], P[x].get('died'))))
    est = [u['id'] for u in F['unions'] if u.get('year_precision') == 'unknown']
    if est: out['computed'].append(dict(id='unions', grade='∑', issue='%d of %d union years are null in the file (drawn at an estimate, marked ?)' % (len(est), len(F['unions'])), ids=est))
    out['moves_seeded'] = [dict(id=pid, **{k: v for k, v in r.items()}) for pid, r in sorted(L['rec'].items())]
    return out


# ---------------------------------------------------------------- gates and receipt
def run_validators(path):
    out = {}
    r = subprocess.run(['xmllint', '--noout', path], capture_output=True, text=True); out['xmllint_wellformed'] = dict(ok=r.returncode == 0, stderr=r.stderr[-600:])
    xsd = os.path.join(X3D_MCP, 'src', 'validation', 'schemas', 'x3d-4.0.xsd')
    r = subprocess.run(['xmllint', '--noout', '--schema', xsd, path], capture_output=True, text=True)
    out['xmllint_xsd'] = dict(ok=r.returncode == 0, schema=xsd, errors=[l for l in r.stderr.splitlines() if 'validates' not in l][:12])
    py, va = FORK_PY, os.path.join(PROTO, 'tools', 'validate_x3d.py')
    r = subprocess.run([py, va, path], capture_output=True, text=True, timeout=900)
    try:
        data = json.loads(r.stdout); sem = data['semantic'] if isinstance(data['semantic'], str) else json.dumps(data['semantic'])
        mm = re.search(r'Found (\d+) error\(s\), (\d+) warning\(s\), (\d+) info\(s\)', sem)
        e_, w_, i_ = (int(x) for x in mm.groups()) if mm else ((0, 0, 0) if 'No semantic issues found' in sem else (None, None, None))
        head = subprocess.run(['git', '-C', X3D_MCP, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
        out['fork'] = dict(command='fvenv/bin/python validate_x3d.py FILE', commit=head, xsd_valid=data['xsd_valid'], xsd_errors=data['xsd_errors'], profile_ok=data['profile_ok'],
                           profile=str(data['profile'])[:400], semantic_errors=e_, semantic_warnings=w_, semantic_infos=i_,
                           semantic_lines=[l.strip() for l in sem.splitlines() if re.search(r'ERROR|WARN', l)][:20])
    except Exception as ex:
        out['fork'] = dict(error=repr(ex), stdout=r.stdout[-1200:], stderr=r.stderr[-1200:])
    f = out['fork']
    out['clean'] = bool(out['xmllint_wellformed']['ok'] and out['xmllint_xsd']['ok'] and f.get('xsd_valid') and f.get('profile_ok') and f.get('semantic_errors') == 0 and f.get('semantic_warnings') == 0)
    return out


def tool_versions():
    v = {'python': sys.version.split()[0]}
    r = subprocess.run(['xmllint', '--version'], capture_output=True, text=True); v['xmllint'] = (r.stderr or r.stdout).splitlines()[0].strip()
    v['x3d_mcp_fork'] = subprocess.run(['git', '-C', X3D_MCP, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    return v


def main():
    a = sys.argv[1:]
    src = next((x for x in a if x.endswith('.json')), None)
    if not src:
        merged = os.path.join(PROTO, 'data', 'loom-view.json')
        src = merged if os.path.exists(merged) else os.path.join(HERE, 'dev', 'loom-view.json')
    out_dir = os.path.abspath(a[a.index('--out') + 1]) if '--out' in a else os.path.join(HERE, 'out')
    frame_url = a[a.index('--frame-url') + 1] if '--frame-url' in a else None
    os.makedirs(out_dir, exist_ok=True)
    font_src = os.path.join(PROTO, 'x3d', 'vendor', FONT_FILE)      # converted once from X_ITE 16.5.1's UbuntuMono-R.woff2 (fontTools, flavor None)
    os.makedirs(os.path.join(out_dir, os.path.dirname(FONT_FILE)), exist_ok=True)
    for fsrc, fdst in ((font_src, FONT_FILE), (os.path.join(os.path.dirname(font_src), 'UBUNTU-FONT-LICENCE.txt'), os.path.join(os.path.dirname(FONT_FILE), 'UBUNTU-FONT-LICENCE.txt'))):
        open(os.path.join(out_dir, fdst), 'wb').write(open(fsrc, 'rb').read())
    view, raw, errs, warns = load_view(src)
    if errs: raise SystemExit('loom-view contract errors:\n  ' + '\n  '.join(errs[:30]))
    view['_path'], view['_sha'] = src, sha(raw)
    asof = int(view.get('asof') or drum.build_date().year)
    rec = dict(generated=datetime.date.today().isoformat(), build_date=drum.build_date().isoformat(), contract='proto/contracts/loom-view.md (loom-view/1)',
               inputs={os.path.relpath(src, PROTO): sha(raw)}, scripts={'build_loom_scene.py': sha(open(__file__, 'rb').read()),
                                                                         'x3d/build_genealogy_x3d.py (helpers imported)': sha(open(drum.__file__, 'rb').read())},
               contract_warnings=warns[:40], families={}, outputs={}, tools=tool_versions())
    manifest = dict(version='loom-manifest/1', asof=asof, data=dict(file=os.path.basename(src), sha256=view['_sha'], built_by=view.get('built', {}).get('by')), families=[])
    issues = dict(what='data issues found while drawing (for the data stage; none of them is patched in the scene)', source=os.path.relpath(src, PROTO), source_sha256=view['_sha'],
                  contract_requests=CONTRACT_REQUESTS, families={})
    for F in view['families']:
        F['_src'] = src
        text, L, stops, info, bounds = build_family(F, view, asof, frame_url)
        gates = scene_gates(F, L, stops); issues['families'][F['key']] = data_issues(F, L, stops)
        errs_s, root = drum.static_checks(text)
        path = os.path.join(out_dir, F['key'] + '.x3d'); rawx = text.encode('utf-8'); open(path, 'wb').write(rawx)
        cj = cards(F, L, stops, info, bounds, view, asof)
        cpath = os.path.join(out_dir, F['key'] + '.cards.json'); craw = (json.dumps(cj, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'); open(cpath, 'wb').write(craw)
        stats = drum.count_scene(root)
        fam = dict(scene=os.path.basename(path), bytes=len(rawx), gz_bytes=len(gzip.compress(rawx, 9, mtime=0)), cards=os.path.basename(cpath), cards_bytes=len(craw),
                   people=len(L['P']), unions=len(F['unions']), close=sum(1 for u in F['unions'] if u.get('close')), houses=L['used'],
                   unions_year_estimated=F['_estimated_union_years'], dropped=F['_dropped'],
                   houses_in_file_not_drawn=[h['key'] for h in F['houses'] if h['key'] not in L['used']],
                   stops=[dict(n=s['n'], title=s['title'], viewpoint=s['def'], names=sum(1 for l in s['labels'] if l['kind'] == 'name'), labels=len(s['labels']),
                               overlaps=sum(1 for i, x in enumerate(s['labels']) for y in s['labels'][i + 1:] if hit(x['box'], y['box'], 0.0)),
                               outside_safe_area=sum(1 for l in s['labels'] if not inside(l['box'])), min_text_px=round(min((l['box'][3] / (2 * CHIP_Y) for l in s['labels']), default=0), 1),
                               names_phone=sum(1 for l in s['labels_phone'] if l['kind'] == 'name'), labels_phone=len(s['labels_phone']), subject=s['subject'], fell=s['fell'],
                               not_labelled=[[m['kind'], m['text'], m['why']] for m in s['label_misses'] if m['kind'] != 'name'],
                               names_not_labelled=dict(cap=sum(1 for m in s['label_misses'] if m['kind'] == 'name' and m['why'].startswith('name cap')),
                                                       no_room=sum(1 for m in s['label_misses'] if m['kind'] == 'name' and not m['why'].startswith('name cap'))),
                               shortened=[[l['ref'], l['text']] for l in s['labels'] if l.get('alts') and l['text'] in l['alts']]) for s in stops],
                   kx=L['kx'], gates=gates,
                   dashed=sorted(pid for pid in info if info[pid]['style'] == 'dashed'), static_checks=dict(ok=not errs_s, errors=errs_s[:10]), counts=stats)
        if '--validate' in a: fam['validators'] = run_validators(path)
        rec['families'][F['key']] = fam
        manifest['families'].append(dict(key=F['key'], name=F['name'], scene=os.path.basename(path), cards=os.path.basename(cpath), people=len(L['P']),
                                         stops=[dict(n=s['n'], title=s['title'], def_=s['def']) for s in stops]))
        print('%-16s %6d bytes (%d gz) %3d people %2d stops  static %s  gates %s%s' % (F['key'], len(rawx), fam['gz_bytes'], len(L['P']), len(stops), 'ok' if not errs_s else errs_s[:3],
                                                                           ' '.join('%s=%s' % (g, 'ok' if v.get('ok') else 'FAIL') for g, v in gates.items() if 'ok' in v),
                                                                           ('  validators ' + ('CLEAN' if fam['validators']['clean'] else 'NOT CLEAN ' + json.dumps({k: fam['validators']['fork'].get(k) for k in ('xsd_valid', 'profile_ok', 'semantic_errors', 'semantic_warnings', 'error')}) + ' ' + str(fam['validators']['xmllint_xsd']['errors'][:2]))) if '--validate' in a else ''))
    iraw = (json.dumps(issues, ensure_ascii=False, indent=1) + '\n').encode('utf-8'); open(os.path.join(out_dir, 'data-issues.json'), 'wb').write(iraw)
    rec['scene_gates'] = {k: {g: v.get('ok') for g, v in fam['gates'].items() if 'ok' in v} for k, fam in rec['families'].items()}
    order = ['rothschild', 'habsburg', 'darwin_wedgwood']
    manifest['families'].sort(key=lambda f: (order.index(f['key']) if f['key'] in order else 9, f['key']))
    mraw = (json.dumps(manifest, ensure_ascii=False, indent=1) + '\n').encode('utf-8'); open(os.path.join(out_dir, 'loom-manifest.json'), 'wb').write(mraw)
    page_src = os.path.join(HERE, 'page', 'index.html'); praw = open(page_src, 'rb').read()
    xite = os.path.join(PROTO, 'x3d', 'vendor', 'x_ite', 'x_ite.min.js')
    sri = 'sha384-' + __import__('base64').b64encode(hashlib.sha384(open(xite, 'rb').read()).digest()).decode()
    if sri.encode() not in praw: raise SystemExit('page/index.html does not carry the SRI of the vendored x_ite.min.js (%s)' % sri)
    open(os.path.join(out_dir, 'index.html'), 'wb').write(praw)
    rec['inputs']['scene2/page/index.html'] = sha(praw); rec['inputs']['x3d/vendor/x_ite/x_ite.min.js (16.5.1, tarball-identical)'] = sha(open(xite, 'rb').read())
    rec['xite'] = dict(cdn='https://cdn.jsdelivr.net/npm/x_ite@16.5.1/dist/x_ite.min.js', integrity=sri, local='?local=1 -> ../../x3d/vendor/x_ite/x_ite.min.js')
    tgz = os.path.join(PROTO, 'x3d', 'vendor', 'x_ite-16.5.1.tgz')      # the npm tarball, kept by tools/vendor_xite.py (sha256 pinned there)
    if os.path.exists(tgz):
        import tarfile
        with tarfile.open(tgz) as tf:
            m = tf.extractfile('package/dist/x_ite.min.js').read()
        rec['xite']['tarball'] = dict(file='x3d/vendor/x_ite-16.5.1.tgz', sha256=sha(open(tgz, 'rb').read()), pinned='f93bc35f2eec515ec2e38de9680a5125c3aa5178197763aaf7c603fc26b71be5',
                                      entry='package/dist/x_ite.min.js (served by jsDelivr as /npm/x_ite@16.5.1/dist/x_ite.min.js)', entry_sha256=sha(m),
                                      vendored_identical=sha(m) == sha(open(xite, 'rb').read()))
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith(('.x3d', '.json', '.html')) and fn != 'receipt.json': rec['outputs'][fn] = sha(open(os.path.join(out_dir, fn), 'rb').read())
    rec['outputs'][FONT_FILE] = sha(open(os.path.join(out_dir, FONT_FILE), 'rb').read()); rec['inputs']['x3d/vendor/' + FONT_FILE + ' (from x_ite assets/fonts/Ubuntu/UbuntuMono-R.woff2)'] = sha(open(font_src, 'rb').read())
    rp = os.path.join(out_dir, 'receipt.json')
    if os.path.exists(rp):
        old = json.load(open(rp, encoding='utf-8'))
        for k in ('xite_gate', 'lookgates'):
            if k in old and old.get('outputs') == rec['outputs']: rec[k] = old[k]
    json.dump(rec, open(rp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('wrote', out_dir, '(receipt.json, loom-manifest.json, index.html)')


if __name__ == '__main__':
    main()
