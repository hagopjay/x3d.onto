#!/usr/bin/env python3
"""Build the Dynasty Loom v2 Artifact file set from this folder and the portraits manifest. Standard library only; each stage is its own process.

    python3 -I dynasty-loom/tools/vendor_xite.py --release DIR_WITH_A_SHA256SUMS   # once: X_ITE 16.5.1 into x3d/vendor/x_ite (see README)
    python3 -I dynasty-loom/tools/build_v2.py --manifest PATH/portraits/manifest.json [--placeholders DIR] [--out DIR] [--artifact DIR] [--date YYYY-MM-DD] [--release DIR]

Stages, in order (the themes come from hyper/themes.py: DEFAULT_THEME, ALT_THEME, PHONE_UI):
  1. tapestry/tools/merge_views.py      the two-view page with the themed style sheet -> tapestry/page/index.html
  2. tapestry/build_loom_scene.py       data/loom-view.json --date D -> <out>/tapestry (loom scenes, cards, manifest, page, label font)
  3. tools/build_portraits.py           --manifest [--placeholders] -> <out>/portraits (portraits.json and only the files it names)
  4. hyper/build_hypersphere.py         the default theme -> <out>/hyper (with the portrait plates)
  5. hyper/build_hypersphere.py         --theme ALT_THEME --root-rel ../../ -> <out>/hyper-alt (published under theme/<slug>/)
  6. the Blender loading plates         hyper/hero/plates -> <out>/hyper
  7. tapestry/tools/make_artifact.py    -> <artifact> (with its gates), then SHA256SUMS and a publish.json whose paths are relative to <artifact>
--release DIR compares the result with DIR/SHA256SUMS (exit 1 on a difference). A fuller portraits manifest needs no code change: run this again.
Default --out is dynasty-loom/build/v2 (git-ignored) and --artifact is <out>/artifact. The date defaults to SOURCE_DATE_EPOCH, else 2026-10-30."""
import datetime, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # dynasty-loom/
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, 'hyper'))
import themes as TH   # noqa: E402


def arg(k, d=None):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(cmd):
    print('$', ' '.join(os.path.relpath(c, ROOT) if os.path.isabs(c) and c.startswith(ROOT) else c for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode: sys.exit('stage failed (exit %d): %s' % (r.returncode, ' '.join(cmd)))


def main():
    man = arg('--manifest')
    if not man: sys.exit(__doc__)
    out = os.path.abspath(arg('--out', os.path.join(ROOT, 'build', 'v2')))
    art = os.path.abspath(arg('--artifact', os.path.join(out, 'artifact')))
    sde = os.environ.get('SOURCE_DATE_EPOCH')
    date = arg('--date') or (datetime.datetime.fromtimestamp(int(sde), datetime.timezone.utc).date().isoformat() if sde else '2026-10-30')
    tap, por, hyp, alt = (os.path.join(out, d) for d in ('tapestry', 'portraits', 'hyper', 'hyper-alt'))
    for d in (tap, por, hyp, alt, art):
        if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(out, exist_ok=True)
    view = os.path.join(ROOT, 'data', 'loom-view.json')
    print('build date %s; looks %s (phone UI %s); manifest %s' % (date, TH.page_slugs(), TH.PHONE_UI, man), flush=True)
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'tools', 'merge_views.py')])
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'build_loom_scene.py'), view, '--out', tap, '--date', date])
    ph = arg('--placeholders')
    run([PY, '-I', os.path.join(ROOT, 'tools', 'build_portraits.py'), '--manifest', man, '--cards', tap, '--out', por] + (['--placeholders', os.path.abspath(ph)] if ph else []))
    pj = os.path.join(por, 'portraits.json')
    run([PY, '-I', os.path.join(ROOT, 'hyper', 'build_hypersphere.py'), '--view', view, '--cards', tap, '--out', hyp, '--theme', TH.DEFAULT_THEME, '--portraits', pj])
    if TH.ALT_THEME and TH.ALT_THEME != TH.DEFAULT_THEME:
        run([PY, '-I', os.path.join(ROOT, 'hyper', 'build_hypersphere.py'), '--view', view, '--cards', tap, '--out', alt, '--theme', TH.ALT_THEME, '--portraits', pj, '--root-rel', '../../'])
    for n in ('poster-wide-plate.webp', 'poster-tall-plate.webp'):
        shutil.copyfile(os.path.join(ROOT, 'hyper', 'hero', 'plates', n), os.path.join(hyp, n))
    run([PY, '-I', os.path.join(ROOT, 'tapestry', 'tools', 'make_artifact.py'), '--out', tap, '--hyper', hyp, '--artifact', art, '--portraits', por]
        + (['--hyper-alt', alt] if os.path.isdir(alt) else []))
    # the release receipts: SHA256SUMS over every published file, and the Artifact files map with paths relative to the artifact folder
    pub = json.load(open(os.path.join(art, 'publish.json'), encoding='utf-8'))
    rel = {p: {'from': p, 'contentType': v['contentType']} for p, v in sorted(pub.items())}
    json.dump(rel, open(os.path.join(art, 'publish.json'), 'w', encoding='utf-8'), indent=1, sort_keys=True)
    paths = ['index.html'] + sorted(pub)
    with open(os.path.join(art, 'SHA256SUMS'), 'w', encoding='utf-8', newline='\n') as f:
        for p in paths: f.write('%s  %s\n' % (sha(os.path.join(art, p)), p))
    sizes = {p: os.path.getsize(os.path.join(art, p)) for p in paths}
    big = max(sizes.items(), key=lambda kv: kv[1])
    shown = lambda d: os.path.relpath(d, ROOT) if d.startswith(ROOT + os.sep) else '.../' + os.path.basename(d)   # no absolute paths in a receipt
    res = dict(artifact=shown(art), build_date=date, looks=TH.page_slugs(), phone_ui=TH.PHONE_UI, files=len(paths), bytes=sum(sizes.values()), largest=dict(path=big[0], bytes=big[1]),
               portraits=json.load(open(pj, encoding='utf-8'))['counts'])
    if res['bytes'] > 16.5 * 2 ** 20: print('warning: the set is over about 16 MB (%d bytes)' % res['bytes'])
    if big[1] > 15 * 2 ** 20: sys.exit('a file is over 15 MB: %s' % big[0])
    rel_dir = arg('--release')
    if rel_dir:
        want = dict(line.rstrip('\n').split('  ', 1)[::-1] for line in open(os.path.join(rel_dir, 'SHA256SUMS'), encoding='utf-8'))
        have = dict(line.rstrip('\n').split('  ', 1)[::-1] for line in open(os.path.join(art, 'SHA256SUMS'), encoding='utf-8'))
        res['compare'] = dict(release=shown(os.path.abspath(rel_dir)), differ=sorted(p for p in want if p in have and want[p] != have[p]), missing=sorted(set(want) - set(have)), extra=sorted(set(have) - set(want)))
    json.dump(res, open(os.path.join(out, 'build-v2.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(res, indent=1))
    if rel_dir and any(res['compare'][k] for k in ('differ', 'missing', 'extra')): sys.exit(1)


if __name__ == '__main__':
    main()
