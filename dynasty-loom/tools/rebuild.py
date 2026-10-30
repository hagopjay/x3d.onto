#!/usr/bin/env python3
"""Rebuild the Dynasty Loom Artifact file set from this folder alone and compare it with a frozen release. Standard library only.

    python3 -I dynasty-loom/tools/vendor_xite.py              # once: X_ITE 16.5.1 into x3d/vendor/x_ite and release/v3/x_ite
    python3 -I dynasty-loom/tools/rebuild.py [--out DIR] [--release DIR] [--validate]

Runs the stages in their order, each as its own process with python3 -I (the scripts are unchanged in behaviour):
  1. tapestry/tools/merge_views.py      tapestry/page/loom.html + hyper/page/index.html -> tapestry/page/index.html (in the tree, git-ignored)
  2. tapestry/build_loom_scene.py       data/loom-view.json -> <out>/tapestry (scenes, cards, manifest, page, font, data-issues, receipt)
  3. hyper/build_hypersphere.py         data/loom-view.json + <out>/tapestry cards -> <out>/hyper (host and pocket scenes, .hyper.json, ...)
  4. the Blender plates                 hyper/hero/plates/poster-*-plate.webp -> <out>/hyper (made by hyper/hero, not rebuilt here)
  5. tapestry/tools/make_artifact.py    <out>/tapestry + <out>/hyper -> <out>/artifact (the published file set, with its gates)
  6. compare                            every path in <release>/SHA256SUMS against <out>/artifact by sha256; receipt.json field by field
Default --out is dynasty-loom/build (git-ignored); default --release is dynasty-loom/release/v3. Exit 1 when a published file differs.
The tapestry scenes carry the build date (<meta name='created'>, generator '(YYYY-MM-DD)'): a rebuild on another day differs there only."""
import hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # dynasty-loom/
PY = sys.executable


def arg(k, d):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(cmd):
    print('$', ' '.join(os.path.relpath(c, ROOT) if os.path.isabs(c) and c.startswith(ROOT) else c for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode: sys.exit('stage failed (exit %d): %s' % (r.returncode, ' '.join(cmd)))


def diff(a, b, at=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str): out += diff(a.get(k, '<absent>'), b.get(k, '<absent>'), at + '/' + str(k))
        return out
    return [] if a == b else [at]


def main():
    out = os.path.abspath(arg('--out', os.path.join(ROOT, 'build')))
    rel = os.path.abspath(arg('--release', os.path.join(ROOT, 'release', 'v3')))
    tap, hyp, art = (os.path.join(out, d) for d in ('tapestry', 'hyper', 'artifact'))
    for d in (tap, hyp, art):
        if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(out, exist_ok=True)
    view = os.path.join(ROOT, 'data', 'loom-view.json')
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'tools', 'merge_views.py')])
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'build_loom_scene.py'), view, '--out', tap] + (['--validate'] if '--validate' in sys.argv else []))
    run([PY, '-I', os.path.join(ROOT, 'hyper', 'build_hypersphere.py'), '--view', view, '--cards', tap, '--out', hyp])
    for n in ('poster-wide-plate.webp', 'poster-tall-plate.webp'):
        shutil.copyfile(os.path.join(ROOT, 'hyper', 'hero', 'plates', n), os.path.join(hyp, n))
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'tools', 'make_artifact.py'), '--out', tap, '--hyper', hyp, '--artifact', art])
    sums = {}
    for line in open(os.path.join(rel, 'SHA256SUMS'), encoding='utf-8'):
        h, p = line.rstrip('\n').split('  ', 1); sums[p] = h
    same, differ, missing = [], [], []
    for p, h in sorted(sums.items()):
        f = os.path.join(art, p)
        if not os.path.exists(f): missing.append(p)
        elif sha(f) == h: same.append(p)
        else: differ.append(p)
    extra = sorted(os.path.relpath(os.path.join(d, f), art) for d, _, fs in os.walk(art) for f in fs
                   if os.path.relpath(os.path.join(d, f), art) not in sums and f not in ('publish.json', 'receipt.json'))
    rdiff = diff(json.load(open(os.path.join(rel, 'receipt.json'), encoding='utf-8')), json.load(open(os.path.join(art, 'receipt.json'), encoding='utf-8')))
    pa, pb = (json.load(open(os.path.join(x, 'publish.json'), encoding='utf-8')) for x in (rel, art))
    pdiff = sorted(set(pa) ^ set(pb)) + [k for k in pa if k in pb and pa[k]['contentType'] != pb[k]['contentType']]
    res = dict(release=os.path.relpath(rel, ROOT), out=out, published=len(sums), identical=len(same), differ=differ, missing=missing, extra=extra,
               receipt_fields_differ=rdiff, publish_json_paths_or_types_differ=pdiff)
    json.dump(res, open(os.path.join(out, 'compare.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(res, indent=1))
    if differ or missing or extra or pdiff: sys.exit(1)


if __name__ == '__main__':
    main()
