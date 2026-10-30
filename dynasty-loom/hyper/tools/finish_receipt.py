#!/usr/bin/env python3
"""finish_receipt.py (build 3): adds the gates that run outside the generator to out/receipt.json, after the build and the live gate.

    python3 -I tools/finish_receipt.py [--validate-glob work/validate3-*.json] [--csp csp-gate.json] [--det work/r2/det-a,work/r2/det-b]

static_gates  xmllint (re-run here against x3d-4.0.xsd for every X3D in out/) and the fork validator results read from the JSON files that
              tools/validate_x3d.py wrote (one per X3D);
csp_gate      the strict-CSP Artifact gate's file, its sha256 and its result;
determinism   two scratch builds compared file by file (sha256): the files that differ, which must be publish.json (absolute source paths)
              and receipt.json (publish.json's hash) only;
data_issues   where the data issues are listed (they are not drawn into the scene).
Standard library only; it never edits a generated scene file, only receipt.json."""
import glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT, REC = os.path.join(HERE, 'out'), os.path.join(HERE, 'out', 'receipt.json')
X3D_MCP = os.environ.get('X3D_MCP', '/home/user/hagopjay/x3d_mcp')
XSD = os.path.join(X3D_MCP, 'src', 'validation', 'schemas', 'x3d-4.0.xsd')


def arg(k, d):
    a = [x for x in sys.argv[1:] if x.startswith('--' + k + '=')]
    return a[0].split('=', 1)[1] if a else d


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


rec = json.load(open(REC, encoding='utf-8'))
x3ds = sorted(f for f in os.listdir(OUT) if f.endswith('.x3d'))
lint = {}
for f in x3ds:
    r = subprocess.run(['xmllint', '--noout', '--schema', XSD, os.path.join(OUT, f)], capture_output=True, text=True)
    lint[f] = 'validates' if r.returncode == 0 else (r.stderr.strip().splitlines() or ['failed'])[-1]
fork = {}
for p in sorted(glob.glob(os.path.join(HERE, arg('validate-glob', 'work/validate3-*.json')))):
    name = os.path.basename(p)[len('validate3-'):-len('.json')] + '.x3d'
    try:
        d = json.load(open(p, encoding='utf-8')); txt = json.dumps(d)
        m = re.search(r'Found \d+ error\(s\), \d+ warning\(s\), \d+ info\(s\)', str(d.get('semantic') if isinstance(d, dict) else txt)); sem = m.group(0) if m else txt[:120]
        fork[name] = dict(xsd_valid=d.get('xsd_valid') if isinstance(d, dict) else None, profile_ok=d.get('profile_ok') if isinstance(d, dict) else None, semantic=sem,
                          sha256_of_input=sha(os.path.join(OUT, name)) if os.path.exists(os.path.join(OUT, name)) else None)
    except Exception as e:
        fork[name] = dict(error=str(e))
static = dict(xmllint='%s: %d/%d validate' % (os.path.relpath(XSD, os.path.dirname(X3D_MCP)), sum(v == 'validates' for v in lint.values()), len(lint)), xmllint_files=lint,
              fork_validator='tools/validate_x3d.py via LOOM_FORK_PYTHON (results in hyper/work/validate3-*.json)', fork_validator_files=fork,
              ok=all(v == 'validates' for v in lint.values()) and len(fork) == len(x3ds) and all('0 error(s)' in str(v.get('semantic')) and v.get('profile_ok') for v in fork.values()))
rec['static_gates'] = static
csp = os.path.join(HERE, arg('csp', 'csp-gate.json'))
if os.path.exists(csp):
    c = json.load(open(csp, encoding='utf-8'))
    rec['csp_gate'] = dict(file='hyper/' + os.path.relpath(csp, HERE), sha256=sha(csp), result=c.get('pass', c.get('result', c.get('ok'))), when=c.get('when'))
det = arg('det', 'work/r2/det-a,work/r2/det-b').split(',')
a, b = [os.path.join(HERE, x) for x in det]
if os.path.isdir(a) and os.path.isdir(b):
    fa = {os.path.relpath(os.path.join(r, f), a) for r, _, fs in os.walk(a) for f in fs}
    fb = {os.path.relpath(os.path.join(r, f), b) for r, _, fs in os.walk(b) for f in fs}
    diff = sorted(f for f in fa | fb if f not in fa or f not in fb or sha(os.path.join(a, f)) != sha(os.path.join(b, f)))
    same_as_out = all(sha(os.path.join(a, f)) == sha(os.path.join(OUT, f)) for f in fa if '/' not in f and f not in ('publish.json', 'receipt.json') and os.path.exists(os.path.join(OUT, f)))
    rec['determinism'] = dict(builds=['hyper/' + x for x in det], files=len(fa), differ=diff, deterministic=set(diff) <= {'publish.json', 'receipt.json'}, scratch_equals_out=same_as_out,
                              note='publish.json names absolute source paths (it differs by output folder); receipt.json differs only by publish.json\'s hash')
rec['data_issues'] = 'hyper/work/r1/data-issues.json (not drawn into the scene; unchanged in build 3)'
json.dump(rec, open(REC, 'w', encoding='utf-8'), indent=1, sort_keys=True, ensure_ascii=False)
print(json.dumps(dict(static_ok=static['ok'], csp=rec.get('csp_gate', {}).get('result'), determinism=rec.get('determinism', {}).get('deterministic'), differ=rec.get('determinism', {}).get('differ'))))
