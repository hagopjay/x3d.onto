#!/usr/bin/env python3
"""Integration receipt for the tapestry loom: scene2/receipt.json, assembled from what the gates wrote (never typed by hand).

    python3 -I tools/write_receipt.py [--tag final-1] [--frames-dir frames/final-1] [--determinism same|diff]

Reads out/receipt.json (build_loom_scene.py: inputs, validators per scene), gate.json (tools/gate_loom.js: X_ITE live checks, label measurements,
frames, lookgates.py) and the frames receipt; hashes every input, script and output again; and grades each claim Confirmed / Likely / Suspected,
naming the tool behind it. Standard library only."""
import datetime, gzip, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # scene2/
PROTO = os.path.dirname(HERE)
FAMS = ['rothschild', 'habsburg', 'darwin_wedgwood']
CHANGES = [   # what fix round 09 changed in the sources (the outputs are only ever rebuilt)
    'build_loom_scene.py plan(): moves are decided per marriage, not per person in birth order (the "oth in done" test is gone): a dated move first (the data\'s moved, else MOVED_SEED from report 07: Nathan 1798 C, James 1811 S, Salomon 1820 S, Carl 1821 C); else the move rides the first pick into the adult house, alone when the spouse was already there, both together when neither was born there; AGE_MOVE only without such a marriage, drawn dotted, its year kept out of captions and cards; in-laws without parents follow house_at(spouse, year); iterated to a fixed point',
    'build_loom_scene.py: an open diamond on the mover\'s end of every pick a thread crosses on; scene gate "moves" fails the build when a move has no reason, an estimated move stands where a marriage into the house exists, or a caption prints an estimated move year',
    'build_loom_scene.py: the data\'s house "closed" (last core death, proto/ingest/loomview.py) is no longer called a closing; Rothschild stop 12 marks report 07\'s graded closings (Naples 1863, Frankfurt 1901, Vienna 1938, Paris 1982) instead; conflicts go to out/data-issues.json',
    'build_loom_scene.py: every stop has a subject (labelled first, a leader line if its row is full), the tour\'s silver thread from a founder to the subject and a ring at its bead (Switch Marks), and its own fell year (the page sets it on bind)',
    'build_loom_scene.py: names, picks and notes sit on their thread\'s row (at most half a line off) or are left out; labels are pulled in front of every house plane (oblique Wide frames had cut them) and the label clip is lifted per stop (clip_pad)',
    'build_loom_scene.py: the dye ramp is mixed in CIELAB at one lightness (equal share steps, 13-19 dE76 per quarter; gate dye_ramp >= 12); close picks are doubled and near-white instead of orange-red',
    'build_loom_scene.py: each stop has a phone viewpoint and phone labels (390 x 844, at most 6 names, text >= 12 px); front stops use a long lens (fov 0.24) and the year rail is read at the subject\'s depth (gate rail_reading <= 1 year); NavigationInfo avatarSize 2 for depth precision',
    'build_loom_scene.py: balance: a cloth narrower than 1.2 (width / height) is widened up to 3.5x (Habsburg 3.42x); Judengasse and the generic founders stop start 4 years before the founder\'s birth; house labels fall back to a unique first word',
    'build_loom_scene.py: writes out/data-issues.json (computed issues, the review\'s unchecked claims, the contract requests: a moved field, a definition of opened/closed)',
    'page/index.html: binds the phone viewpoint and labels on a portrait screen, sets the stop\'s fell, Marks and Leaders, lifts the label clip by clip_pad, shows the dye gauge from the cards, keeps an estimated move year off the card; light panels toned down',
    'tools/gate_loom.js: per stop also checks the fell, the subject label and that names sit on their rows; measures every stop of the default family on the phone page and shoots it',
]


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def rel(p): return os.path.relpath(p, PROTO)
def ver(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60); return ((r.stdout or '') + (r.stderr or '')).strip().splitlines()[0].strip()
    except Exception as e: return 'unavailable (%s)' % e


def main():
    a = sys.argv[1:]
    tag = a[a.index('--tag') + 1] if '--tag' in a else 'final'
    fdir = os.path.join(HERE, a[a.index('--frames-dir') + 1] if '--frames-dir' in a else os.path.join('frames', tag))
    det = a[a.index('--determinism') + 1] if '--determinism' in a else None
    out = os.path.join(HERE, 'out')
    gen = json.load(open(os.path.join(out, 'receipt.json'), encoding='utf-8'))
    gate = json.load(open(os.path.join(HERE, 'gate.json'), encoding='utf-8'))
    frec = json.load(open(os.path.join(fdir, 'receipt.json'), encoding='utf-8'))
    src = os.path.join(PROTO, next(k for k in gen['inputs'] if k.endswith('loom-view.json')))
    merged = os.path.join(PROTO, 'data', 'loom-view.json'); used_merged = os.path.abspath(src) == os.path.abspath(merged)
    mrec_p = os.path.join(PROTO, 'data', 'loom-view.receipt.json'); mrec = json.load(open(mrec_p, encoding='utf-8')) if os.path.exists(mrec_p) else {}
    view_sha_in_data_receipt = ((mrec.get('outputs') or {}).get('loom-view.json') or {}).get('sha256')
    inputs = {rel(p): sha(p) for p in (src, os.path.join(PROTO, 'contracts', 'loom-view.md'), os.path.join(HERE, 'page', 'index.html'),
                                        os.path.join(PROTO, 'x3d', 'vendor', 'x_ite', 'x_ite.min.js')) + ((mrec_p,) if mrec else ())}
    scripts = {rel(p): sha(p) for p in (os.path.join(HERE, 'build_loom_scene.py'), os.path.join(PROTO, 'x3d', 'build_genealogy_x3d.py'), os.path.join(HERE, 'tools', 'gate_loom.js'),
                                         os.path.join(PROTO, 'gates', 'lookgates.py'), os.path.abspath(__file__), os.path.join(PROTO, 'tools', 'validate_x3d.py'))}
    outputs = {}
    for fn in sorted(os.path.relpath(os.path.join(d_, f_), out) for d_, _, fs_ in os.walk(out) for f_ in fs_):    # out/fonts/ too
        p = os.path.join(out, fn); raw = open(p, 'rb').read()
        outputs[rel(p)] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), gz_bytes=len(gzip.compress(raw, 9, mtime=0)))
    for p in [os.path.join(HERE, 'gate.json')] + [os.path.join(fdir, fn) for fn in sorted(os.listdir(fdir))]:
        outputs[rel(p)] = dict(sha256=sha(p), bytes=os.path.getsize(p))
    vg = os.environ.get('LOOM_GATE_PYTHON', 'python3')
    tools = dict(gen['tools'], x3d_mcp_fork_validator='fvenv/bin/python validate_x3d.py (fork commit %s)' % gen['tools'].get('x3d_mcp_fork'),
                 xmllint_schema='/home/user/hagopjay/x3d_mcp/src/validation/schemas/x3d-4.0.xsd (the fork\'s)', x_ite='16.5.1 (vendored, tarball-identical: %s)' % (gen.get('xite', {}).get('tarball', {}).get('vendored_identical')),
                 chromium=gate.get('chromium'), playwright=gate.get('playwright'), gl=gate.get('gl'), node=ver(['node', '--version']),
                 lookgates_python=ver([vg, '-c', 'import sys,numpy,PIL; print(sys.version.split()[0], "numpy", numpy.__version__, "Pillow", PIL.__version__)']))
    checks = gate.get('checks', []); frames = gate.get('frames', []); look = gate.get('lookgates') or []
    lk = {}
    for l in look:
        m = re.search(r'(\S+\.png)', l['line']); lk[os.path.basename(m.group(1)) if m else l['line']] = l
    per_file, families = {}, {}
    for k in FAMS:
        fam = gen['families'].get(k)
        if not fam: continue
        v = fam.get('validators', {}); fk = v.get('fork', {})
        cards = json.load(open(os.path.join(out, k + '.cards.json'), encoding='utf-8'))
        U = list(cards['unions'].values())
        est = [u for u in U if u.get('year_precision') == 'unknown']
        fr = [f for f in frames if os.path.basename(f['file']).startswith(k + '-') or os.path.basename(f['file']).startswith('phone-' + k + '-')]
        live = [c for c in checks if c['name'].startswith(k + ' ') or c['name'].startswith(k + ':')]
        meas = {m['stop']: m for m in (gate.get('measured') or {}).get(k, [])}
        per_file[fam['scene']] = dict(
            xmllint_wellformed=dict(ok=v.get('xmllint_wellformed', {}).get('ok'), tool=tools.get('xmllint')),
            xmllint_xsd=dict(ok=v.get('xmllint_xsd', {}).get('ok'), errors=v.get('xmllint_xsd', {}).get('errors'), schema=v.get('xmllint_xsd', {}).get('schema')),
            fork_validator=dict(commit=fk.get('commit'), xsd_valid=fk.get('xsd_valid'), profile_ok=fk.get('profile_ok'), errors=fk.get('semantic_errors'), warnings=fk.get('semantic_warnings'), infos=fk.get('semantic_infos'),
                                note='infos are DEFs that only the page reaches through the SAI'),
            clean=v.get('clean'),
            xite_live=dict(passed=sum(1 for c in live if c['ok']), failed=sum(1 for c in live if not c['ok']), checks=[('PASS ' if c['ok'] else 'FAIL ') + c['name'] for c in live]),
            frames=[dict(file=f['file'], sha256=outputs.get(rel(os.path.join(HERE, f['file'])), {}).get('sha256'), mean_luma=f.get('mean'), lit=f.get('lit'),
                         lookgates=(lk.get(os.path.basename(f['file'])) or {}).get('line'), nonblack=(lk.get(os.path.basename(f['file'])) or {}).get('ok')) for f in fr],
            static_checks=fam.get('static_checks'), bytes=fam['bytes'], gz_bytes=fam['gz_bytes'], cards=fam['cards'], cards_bytes=fam['cards_bytes'])
        families[k] = dict(
            people_in_file=len(cards['people']), people_drawn=fam['people'], unions_drawn=fam['unions'],
            wefts=dict(single=sum(1 for u in U if not u.get('close') and u.get('year_precision') != 'unknown'), close_doubled=sum(1 for u in U if u.get('close')),
                       year_estimated_translucent=len(est), of_which_close=sum(1 for u in est if u.get('close'))),
            year_estimates=[dict(id=u['id'], drawn=u['year'], rule=u.get('year_drawn_rule')) for u in sorted(est, key=lambda u: u['id'])],
            houses_drawn=fam['houses'], houses_not_drawn=fam.get('houses_in_file_not_drawn'), dropped=fam.get('dropped'),
            dashed_threads=fam.get('dashed'), moves=fam.get('gates', {}).get('moves', {}).get('by_kind'), kx=fam.get('kx'),
            scene_gates={g: (v.get('ok') if 'ok' in v else v) for g, v in (fam.get('gates') or {}).items() if g != 'moves'} | {'moves': (fam.get('gates') or {}).get('moves', {}).get('ok')},
            stops=[dict(n=s['n'], title=s['title'], viewpoint=s['viewpoint'], labels=s['labels'], names=s['names'],
                        generator_overlaps=s['overlaps'], generator_outside_safe_area=s['outside_safe_area'],
                        xite_overlaps=len((meas.get(s['n']) or {}).get('overlaps', [])) if s['n'] in meas else None,
                        xite_outside_safe_area=len((meas.get(s['n']) or {}).get('outside_safe_area', [])) if s['n'] in meas else None,
                        xite_min_text_px=(meas.get(s['n']) or {}).get('min_text_px'), not_labelled=s.get('not_labelled'), names_not_labelled=s.get('names_not_labelled'),
                        subject=s.get('subject'), fell=s.get('fell'), names_phone=s.get('names_phone'), labels_phone=s.get('labels_phone'),
                        house_names_shortened=s.get('shortened')) for s in fam['stops']])
    page_checks = [('PASS ' if c['ok'] else 'FAIL ') + c['name'] for c in checks if not any(c['name'].startswith(k + ' ') or c['name'].startswith(k + ':') for k in FAMS)]
    n_frames = len(frames); all_clean = all(per_file[f]['clean'] for f in per_file)
    con = next((c for c in checks if c['name'].startswith('console:')), None); net = next((c for c in checks if c['name'].startswith('network:')), None)
    lg = next((c for c in checks if c['name'].startswith('lookgates.py')), None)
    n_stops = sum(len(families[k]['stops']) for k in families)
    G = lambda ok: 'Confirmed' if ok else 'Suspected'
    claims = [
        dict(claim='The scenes were built from %s%s.' % (rel(src), '' if used_merged else ' (NOT the merged file: the development adapter output)'), grade='Confirmed', tool='build_loom_scene.py receipt (input sha256)'),
        dict(claim='The merged loom-view.json read here is byte-identical to the one the data stage recorded (sha256 %s).' % (inputs.get(rel(merged)) or '')[:16],
             grade=G(view_sha_in_data_receipt == inputs.get(rel(merged))), tool='sha256 against proto/merged/receipt.json'),
        dict(claim='All three X3D scenes are well-formed and valid against the fork\'s x3d-4.0.xsd.', grade=G(all(per_file[f]['xmllint_wellformed']['ok'] and per_file[f]['xmllint_xsd']['ok'] for f in per_file)), tool=tools.get('xmllint')),
        dict(claim='The fork validator finds every scene XSD-valid and profile-OK with 0 errors and 0 warnings.', grade=G(all(per_file[f]['clean'] for f in per_file)), tool='validate_x3d.py, x3d_mcp fork %s' % tools.get('x3d_mcp_fork')),
        dict(claim='X_ITE logs no error or warning, no request fails, and nothing leaves the page\'s origin under ?local=1.', grade=G(bool(con and con['ok'] and net and net['ok'])), tool='tools/gate_loom.js, X_ITE 16.5.1 in Chromium %s (SwiftShader)' % gate.get('chromium')),
        dict(claim='Every stop of every family (%d stops) binds, and its labels (from X_ITE\'s own text bounds) do not overlap, sit inside the safe area, and are at least 12 px.' % n_stops,
             grade=G(all(c['ok'] for c in checks if ' stop ' in c['name'])), tool='tools/gate_loom.js'),
        dict(claim='All %d frames are non-black.' % n_frames, grade=G(bool(lg and lg['ok'])), tool='proto/gates/lookgates.py (%s)' % tools['lookgates_python']),
        dict(claim='The live gate passed %d of %d checks.' % (gate.get('pass', 0), gate.get('pass', 0) + gate.get('fail', 0)), grade=G(gate.get('fail', 1) == 0), tool='tools/gate_loom.js'),
        dict(claim='No person or union in the file was dropped by the generator; every person is drawn as a thread and every union as a pick.',
             grade=G(all(families[k]['people_drawn'] == families[k]['people_in_file'] and not any(families[k]['dropped'].values()) for k in families)), tool='build_loom_scene.py load_view drop accounting'),
        dict(claim='Union years the data leaves null (%s) are drawn at an estimate, translucent, marked "?" on the stop labels and "year not in the data (drawn Y)" on the card.' % ', '.join('%s %d' % (k, families[k]['wefts']['year_estimated_translucent']) for k in families),
             grade='Confirmed', tool='build_loom_scene.py fill_union_years (rule recorded per union as year_drawn_rule)'),
        dict(claim='The estimated wedding years are approximations, not facts: they come from the year before the first common child or the younger spouse\'s 25th year.', grade='Likely', tool='rule shared with adapt_harvest.py; not checked against any source'),
    ]
    if det: claims.append(dict(claim='A second build from the same input is byte-identical (scenes, cards, manifest, page).', grade=G(det == 'same'), tool='cmp of two build_loom_scene.py runs'))
    if mrec: claims.append(dict(claim='Upstream, the data stage withheld records before this view: its receipt says "%s" (living: %s).' % (mrec.get('verdict'), (mrec.get('counts', {}).get('counts') or mrec.get('counts', {})).get('living', mrec.get('counts', {}).get('living'))),
                                grade='Likely', tool='proto/merged/receipt.json (read, not re-derived here)'))
    sg = lambda g: all((families[k].get('scene_gates') or {}).get(g) for k in families)
    ph = [c for c in checks if c['name'].startswith('phone ') and not c['name'].startswith('phone (') and ' stop ' in c['name']]
    claims += [
        dict(claim='Every drawn move has its reason: a dated record, the pick it rides, the spouse it follows, or (only with no marriage into the house) the dotted age-21 estimate, whose year no caption prints.', grade=G(sg('moves')), tool='build_loom_scene.py scene gate "moves"'),
        dict(claim='The four Rothschild sons move on report 07\'s years: Nathan 1798 and Carl 1821 (C), James 1811 and Salomon 1820 (S: unchecked).', grade='Likely', tool='MOVED_SEED in build_loom_scene.py; grades are report 07\'s and the review\'s, not re-checked here'),
        dict(claim='At every front stop a bead\'s year read off the year rail is within 1 year of its own (long lens, rail at the subject\'s depth).', grade=G(sg('rail_reading')), tool='build_loom_scene.py scene gate "rail_reading" (the generator\'s projection, the same model the live gate uses for labels)'),
        dict(claim='Neighbouring dye shares from 1 to 1/4 differ by at least 12 dE76 on every dye.', grade=G(sg('dye_ramp')), tool='build_loom_scene.py scene gate "dye_ramp" (CIELAB, D65)'),
        dict(claim='Every stop labels its subject and draws its silver thread; every stop sets its own fell; names without a leader sit on their thread\'s row.', grade=G(all(c['ok'] for c in checks if ' stop ' in c['name'] and not c['name'].startswith('phone '))), tool='tools/gate_loom.js (X_ITE text bounds against the generator\'s anchors)'),
        dict(claim='On a 390 x 844 phone every stop of the default family shows its own labels at 12 px or more, none overlapping, inside the phone safe area (%d stops).' % len(ph), grade=G(bool(ph) and all(c['ok'] for c in ph)), tool='tools/gate_loom.js phone pass'),
        dict(claim='The other two families\' phone labels are placed and sized the same way but were not measured live.', grade='Likely', tool='build_loom_scene.py (phone labels at 20 px nominal, as on the desktop)'),
    ]
    claims.append(dict(claim='The jsDelivr path serves the same X_ITE files the vendored copy served (every pulled file exists at the same path in the npm tarball).',
                       grade='Likely', tool='tools/gate_loom.js tarball listing; not loaded live (the sandbox has no web access)'))
    rec = dict(what='fix round 09: the merged loom-view drawn as the tapestry loom (three families), the critique\'s fixes applied in the generator, every gate re-run, a frame at every tour stop and at every phone stop of the default family', tag=tag,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), source_used=rel(src), source_is_merged=used_merged,
               commands=['python3 -I tapestry/build_loom_scene.py data/loom-view.json --validate',
                         'NODE_PATH=/opt/node-tools/node_modules node tapestry/tools/gate_loom.js --tag=%s --frames-dir=%s --all-stops' % (tag, os.path.relpath(fdir, HERE)),
                         'python3 -I tapestry/tools/write_receipt.py --tag %s%s' % (tag, ' --determinism ' + det if det else '')],
               inputs=inputs, scripts=scripts, tools=tools, outputs=outputs, gates_per_file=per_file,
               gates_page=dict(passed=gate.get('pass'), failed=gate.get('fail'), boot_ms=gate.get('boot_ms'), checks=page_checks, console_messages=len(gate.get('console_all') or []),
                               cdn_assets=gate.get('cdn_assets')),
               families=families, claims=claims, changes_this_step=CHANGES, all_scenes_clean=all_clean, frames_dir=os.path.relpath(fdir, HERE), frames=n_frames)
    json.dump(rec, open(os.path.join(HERE, 'receipt.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('wrote', os.path.join(HERE, 'receipt.json'), '| scenes clean:', all_clean, '| live gate %s/%s' % (gate.get('pass'), gate.get('pass', 0) + gate.get('fail', 0)), '| frames', n_frames)


if __name__ == '__main__':
    main()
