"""The Loom receipt (SKILL step 9): what made an asset, written beside it, and a check that it still matches. Stdlib only.
  python3 -I tools/loom_receipt.py write ASSET.x3d --script tools/blender_x.py [--bake bake.json] [--blenderio PATH] [--blender VERSION] [--also tools/village_spec.py] [--out receipt.json] [--force]
  python3 -I tools/loom_receipt.py check [RECEIPT.json ...]     (default: every assets/*/receipt*.json)
write records the Blender version (--blender, else bpy if importable, else `blender --version`, else null), the exporter commit (git -C BLENDERIO), the script's sha256 (and of
each --also file, as NAME_sha256, the key the world receipts use for village_spec.py), the file's bytes and sha256, the bake settings from --bake, and per Shape the p5, p50 and
p95 Rec. 709 luminance of its Color or ColorRGBA values (display values as the page draws them; not the pre-albedo light that blender_village.py records as light_stats).
It will not overwrite a receipt unless --force: a receipt is a record of a run, not a cache.
check compares each receipt with the files as they are now: the asset's sha256 and bytes, the script's sha256 and any *_sha256 of a tools/ file. It reads the receipts the
Blender scripts wrote (a top-level file and sha256, or one per entry of variants) and never rewrites them; a drift is to be noted (in the README), as the skill says.
Exit code 1 when any receipt has drifted or names a file that is missing.
"""
import os, re, sys, json, glob, hashlib, subprocess, argparse
import xml.parsers.expat

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
# the receipts the Blender scripts wrote do not name their script; this is which script wrote each folder's receipt (a receipt written by `write` names it under "script")
SCRIPTS = {'earth': 'blender_earth.py', 'feathers': 'blender_feather.py', 'tender': 'blender_tender.py', 'villager': 'blender_tender.py', 'village': 'blender_village.py'}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def pct(xs, q):
    """nearest-rank percentile on a sorted list"""
    if not xs: return None
    return xs[min(len(xs) - 1, max(0, int(round(q / 100.0 * (len(xs) - 1)))))]


def shape_luminance(path):
    """-> {mesh name: {'corners': n, 'lum_p05', 'lum_p50', 'lum_p95'}} for each Shape with a Color or ColorRGBA (name: the geometry's DEF less ME_, else the nearest DEF above)."""
    p = xml.parsers.expat.ParserCreate(); stack = []; out = {}; cur = []
    def start(tag, a):
        stack.append((tag, a.get('DEF')))
        if tag == 'Shape': cur.append(None)
        elif cur and tag in ('IndexedFaceSet', 'IndexedTriangleSet', 'TriangleSet', 'IndexedLineSet', 'LineSet', 'PointSet') and a.get('DEF') and cur[-1] is None:
            cur[-1] = re.sub(r'^ME_', '', a['DEF'])
        elif cur and tag in ('Color', 'ColorRGBA') and a.get('color'):
            w = 4 if tag == 'ColorRGBA' else 3; v = [float(t) for t in a['color'].replace(',', ' ').split()]
            lum = sorted(0.2126 * v[i] + 0.7152 * v[i + 1] + 0.0722 * v[i + 2] for i in range(0, len(v) - w + 1, w))
            name = cur[-1] or next((d for t, d in reversed(stack[:-1]) if d), 'Shape%d' % len(out))
            out[name] = {'corners': len(lum), 'lum_p05': round(pct(lum, 5), 3), 'lum_p50': round(pct(lum, 50), 3), 'lum_p95': round(pct(lum, 95), 3)}
    def end(tag):
        stack.pop()
        if tag == 'Shape': cur.pop()
    p.StartElementHandler, p.EndElementHandler = start, end
    with open(path, 'rb') as fh: p.ParseFile(fh)
    return out


def blender_version(given=None):
    if given: return given
    try:
        import bpy; return bpy.app.version_string
    except Exception: pass
    try:
        o = subprocess.run(['blender', '--version'], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r'Blender\s+(\S+(?:\s+LTS)?)', o); return m.group(1) if m else None
    except Exception: return None


def exporter_commit(path):
    if not path: return None
    try: return 'x3d-blender-io ' + subprocess.check_output(['git', '-C', path, 'rev-parse', '--short', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return None


def write(a):
    asset = os.path.abspath(a.asset); out = a.out or os.path.join(os.path.dirname(asset), 'receipt.json')
    if os.path.exists(out) and not a.force:
        print('%s exists; a receipt records a run and is not rewritten (pass --force for a new run, or --out another name)' % out, file=sys.stderr); return 1
    rec = {'blender': blender_version(a.blender), 'blenderio': exporter_commit(a.blenderio),
           'script': os.path.relpath(os.path.abspath(a.script), ROOT), 'script_sha256': sha_file(a.script)}
    for f in a.also or []: rec[re.sub(r'\W', '_', os.path.splitext(os.path.basename(f))[0]) + '_sha256'] = sha_file(f)
    if a.bake:
        with open(a.bake, encoding='utf-8') as fh: rec['bake'] = json.load(fh)
    rec['colour_stats'] = shape_luminance(asset)
    rec.update(file=os.path.relpath(asset, os.path.dirname(os.path.abspath(out))), bytes=os.path.getsize(asset), sha256=sha_file(asset))
    with open(out, 'w', encoding='utf-8') as fh: json.dump(rec, fh, indent=1); fh.write('\n')
    print(json.dumps(rec, indent=1)); return 0


def _entries(rec):
    """(label, file, bytes, sha256) for each asset a receipt pins: top level, or one per variant"""
    if 'file' in rec: yield ('', rec['file'], rec.get('bytes'), rec.get('sha256'))
    for k, v in sorted((rec.get('variants') or {}).items()):
        if isinstance(v, dict) and 'file' in v: yield ('variant %s: ' % k, v['file'], v.get('bytes'), v.get('sha256'))


def check_one(path):
    """-> list of (status, message); status is 'ok', 'drift' or 'missing'"""
    with open(path, encoding='utf-8') as fh: rec = json.load(fh)
    d = os.path.dirname(os.path.abspath(path)); res = []
    for label, f, nbytes, sha in _entries(rec):
        p = os.path.join(d, f)
        if not os.path.exists(p): res.append(('missing', '%s%s is missing' % (label, f))); continue
        now, nb = sha_file(p), os.path.getsize(p)
        if sha and now != sha: res.append(('drift', '%s%s sha256 is %s, the receipt says %s (%s bytes now, %s then)' % (label, f, now[:12], sha[:12], nb, nbytes)))
        elif nbytes is not None and nb != nbytes: res.append(('drift', '%s%s is %d bytes, the receipt says %d' % (label, f, nb, nbytes)))
        else: res.append(('ok', '%s%s matches (sha256 %s)' % (label, f, now[:12])))
    script = rec.get('script') or (os.path.join('tools', SCRIPTS[os.path.basename(d)]) if os.path.basename(d) in SCRIPTS else None)
    pins = []
    if 'script_sha256' in rec:
        if script: pins.append((script, rec['script_sha256']))
        else: res.append(('missing', 'script_sha256 is recorded but the receipt does not name its script and the folder is not in SCRIPTS'))
    for k, v in rec.items():
        if k.endswith('_sha256') and k not in ('script_sha256', 'sha256'): pins.append((os.path.join('tools', k[:-len('_sha256')] + '.py'), v))
    for rel, sha in pins:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p): res.append(('missing', '%s is missing' % rel)); continue
        now = sha_file(p)
        res.append(('ok', '%s matches (sha256 %s)' % (rel, now[:12])) if now == sha else
                   ('drift', '%s sha256 is %s, the receipt says %s: the script changed after the run; note it rather than rewrite the receipt' % (rel, now[:12], sha[:12])))
    return res


def check(a):
    paths = a.receipts or sorted(glob.glob(os.path.join(ROOT, 'assets', '*', 'receipt*.json')))
    bad = 0
    for p in paths:
        for st, msg in check_one(p):
            bad += st != 'ok'; print('%s: %s %s' % (os.path.relpath(p, os.getcwd()), st.upper() if st != 'ok' else 'ok', msg))
    print('%d receipts, %d drifted or missing' % (len(paths), bad))
    return 1 if bad else 0


def main(argv):
    ap = argparse.ArgumentParser(description='Loom receipt: write one, or check the committed ones'); sub = ap.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('write'); w.add_argument('asset'); w.add_argument('--script', required=True); w.add_argument('--bake'); w.add_argument('--blenderio'); w.add_argument('--blender')
    w.add_argument('--also', action='append'); w.add_argument('--out'); w.add_argument('--force', action='store_true')
    c = sub.add_parser('check'); c.add_argument('receipts', nargs='*')
    a = ap.parse_args(argv)
    return write(a) if a.cmd == 'write' else check(a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
