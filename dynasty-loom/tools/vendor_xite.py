#!/usr/bin/env python3
"""Vendor X_ITE 16.5.1 for Dynasty Loom from the npm registry tarball, hash-checked. Standard library only.

    python3 -I dynasty-loom/tools/vendor_xite.py [--tgz PATH] [--release DIR] [--no-build-copy]

  1. Fetches https://registry.npmjs.org/x_ite/-/x_ite-16.5.1.tgz (or reads --tgz PATH) and checks its sha256 against the pinned
     value below (the same tarball x3d.onto/gobbler-v4 was measured on). Keeps it as x3d/vendor/x_ite-16.5.1.tgz (git-ignored): the
     tapestry generator's receipt and both live gates read it to prove the vendored files are the CDN's files.
  2. Build copy (unless --no-build-copy): package/dist/{x_ite.min.js, x_ite.css, LICENSE.md, assets/**} into x3d/vendor/x_ite/
     (git-ignored). The generators, merge and publish stages and the gates read X_ITE from there.
  3. Release copy: every x_ite/ path listed in <release>/SHA256SUMS (default release/v3) is taken from package/dist/ and written
     under <release>/x_ite/, then each file is checked against SHA256SUMS. Any mismatch or missing file fails the run (exit 1)
     and nothing is left half-written for that file.
Only regular files under package/dist/ are read; member names with '..' or an absolute path are refused."""
import hashlib, io, os, sys, tarfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # dynasty-loom/
VERSION = '16.5.1'
URL = 'https://registry.npmjs.org/x_ite/-/x_ite-%s.tgz' % VERSION
TGZ_SHA256 = 'f93bc35f2eec515ec2e38de9680a5125c3aa5178197763aaf7c603fc26b71be5'
VENDOR = os.path.join(ROOT, 'x3d', 'vendor')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def arg(k, d=None):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'wb') as fh: fh.write(data)
    os.replace(tmp, path)


def main():
    src = arg('--tgz')
    if src:
        raw = open(src, 'rb').read()
    else:
        with urllib.request.urlopen(URL, timeout=120) as r: raw = r.read()
    if sha(raw) != TGZ_SHA256: sys.exit('x_ite-%s.tgz: sha256 %s, expected %s' % (VERSION, sha(raw), TGZ_SHA256))
    keep = os.path.join(VENDOR, 'x_ite-%s.tgz' % VERSION)
    if not (os.path.exists(keep) and sha(open(keep, 'rb').read()) == TGZ_SHA256): write(keep, raw)
    dist = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tf:
        for m in tf.getmembers():
            n = m.name
            if not m.isfile() or not n.startswith('package/dist/'): continue
            rel = n[len('package/dist/'):]
            if rel.startswith('/') or '..' in rel.split('/'): sys.exit('refusing tar member %r' % n)
            dist[rel] = tf.extractfile(m).read()
    if '--no-build-copy' not in sys.argv:
        build = [r for r in dist if r in ('x_ite.min.js', 'x_ite.css', 'LICENSE.md') or r.startswith('assets/')]
        for r in sorted(build): write(os.path.join(VENDOR, 'x_ite', r), dist[r])
        print('build copy: %d files -> %s' % (len(build), os.path.relpath(os.path.join(VENDOR, 'x_ite'), ROOT)))
    rel_dir = os.path.abspath(arg('--release', os.path.join(ROOT, 'release', 'v3')))
    sums = {}
    for line in open(os.path.join(rel_dir, 'SHA256SUMS'), encoding='utf-8'):
        h, p = line.rstrip('\n').split('  ', 1); sums[p] = h
    want = sorted(p for p in sums if p.startswith('x_ite/'))
    bad = []
    for p in want:
        b = dist.get(p[len('x_ite/'):])
        if b is None: bad.append('%s: not in the tarball' % p); continue
        if sha(b) != sums[p]: bad.append('%s: sha256 %s, SHA256SUMS says %s' % (p, sha(b), sums[p])); continue
        write(os.path.join(rel_dir, p), b)
    for p in want:                                                            # re-read what is on disk
        f = os.path.join(rel_dir, p)
        if os.path.exists(f) and sha(open(f, 'rb').read()) != sums[p]: bad.append('%s: on disk differs from SHA256SUMS' % p)
    if bad: sys.exit('vendor_xite: %d problem(s):\n  ' % len(bad) + '\n  '.join(bad))
    print('release copy: %d x_ite files -> %s, all match SHA256SUMS (tarball sha256 %s)' % (len(want), os.path.relpath(os.path.join(rel_dir, 'x_ite'), ROOT), TGZ_SHA256))


if __name__ == '__main__':
    main()
