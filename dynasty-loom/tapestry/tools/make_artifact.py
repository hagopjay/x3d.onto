#!/usr/bin/env python3
"""Publish stage for the Dynasty Loom Artifact: scene2/out (the two-view page and the loom) + proto/hyper/out (the hypersphere) -> scene2/artifact,
the exact file set a claude.ai Artifact serves. Standard library only.

    python3 -I tools/make_artifact.py [--out DIR] [--hyper DIR] [--artifact DIR] [--hyper-alt DIR] [--portraits DIR]

v2 additions:
  * --hyper-alt DIR: the alternate theme's hypersphere build (build_hypersphere.py --theme ALT_THEME --root-rel ../../); its host and pocket
    scenes and .hyper.json are published under theme/<slug>/ (the page loads them when the header's look switch is on). The cards stay shared.
  * --portraits DIR: tools/build_portraits.py's output: portraits.json and only the files it names (portraits/<id>/...), each checked by sha256.
  * X_ITE: only the components these scenes and the page load (XITE_COMPONENTS: the Immersive profile's separate files plus the X_ITE
    component the page asks for BlendMode); the rest of the 16.5.1 components are left out to keep the set near 16 MB. The live gates fail on
    any request that does not succeed, so a missing component would show there.

What it does, and why:
  * index.html loses its document shell (doctype, html, head, body, charset and viewport metas, the empty icon link): the Artifact host wraps the
    page in its own skeleton. It gains <meta name="loom:xite" content="x_ite/x_ite.min.js">, so the page loads the X_ITE copy shipped beside it
    and only falls back to jsDelivr. The Artifact CSP admits a CDN for scripts only, and X_ITE fetches fonts and images at run time from beside
    its script, so a CDN X_ITE would draw no labels there. Every edit is an exact anchor that must occur once, or the stage stops.
  * X_ITE 16.5.1 is copied from proto/x3d/vendor (tarball-identical): x_ite.min.js, every assets/components/*.min.js (it imports them by profile),
    assets/linetype/linetypes.png (dashed threads), x_ite.css and assets/lib/mikktspace_bg.wasm (both requested at start) and its licence. The scenes' label font is the TTF the generator writes (fonts/), since X_ITE's
    own WOFF2 needs a decoder it runs through new Function.
  * The hypersphere view (the default since the merge, tools/merge_views.py): hyper-manifest.json, each family's host and pocket scenes (the
    GLSL lives inside them as CDATA ShaderParts, so no shader file is shipped), its .hyper.json, and the Blender plates the page shows while the
    first sphere loads (poster-*-plate.webp); X_ITE's PBR lookup tables (assets/lib/lut_*.png) for the PhysicalMaterial rings and bead. Both views
    read the same <family>.cards.json, so the hypersphere's copy must be byte-identical to the loom's, or the stage stops.
  * Gates before anything is written: no secret-shaped strings in any text file, no possibly-living person (born within 110 years of the as-of
    year with no death) in any card file or .hyper.json, every .hyper.json person also in the family's cards, every link host listed. Fails loudly.
  * Writes artifact/publish.json (published path -> source and content type, for the Artifact tool's files map) and artifact/receipt.json (sha256).
"""
import hashlib, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # proto/scene2
PROTO = os.path.dirname(HERE)
XITE = os.path.join(PROTO, 'x3d', 'vendor', 'x_ite')
ASOF, LIVING_YEARS = 2026, 110
SECRET = re.compile(r'AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY|'
                    r'(?i:(?:api[_-]?key|secret|password|token)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,})')
TYPES = {'.woff2': 'font/woff2', '.html': 'text/html', '.x3d': 'application/xml', '.json': 'application/json', '.js': 'text/javascript', '.ttf': 'font/ttf', '.png': 'image/png',
         '.txt': 'text/plain', '.md': 'text/markdown', '.css': 'text/css', '.wasm': 'application/wasm', '.svg': 'image/svg+xml', '.gif': 'image/gif', '.jpg': 'image/jpeg', '.webp': 'image/webp'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def strip_shell(html):
    edits = [('<!doctype html>\n', ''), ('<html lang="en">\n', ''), ('<head>\n', ''), ('<meta charset="utf-8">\n', ''),
             ('<meta name="viewport" content="width=device-width,initial-scale=1">\n', ''), ('<link rel="icon" href="data:,">\n', ''),
             ('</head>\n', ''), ('<body>\n', ''), ('</body>\n', ''), ('</html>\n', ''),
             ('<title>Dynasty Loom</title>\n', '<title>Dynasty Loom</title>\n<meta name="loom:xite" content="x_ite/x_ite.min.js">\n')]
    for old, new in edits:
        n = html.count(old)
        if n != 1: raise SystemExit('index.html: anchor %r occurs %d times, expected once' % (old.strip(), n))
        html = html.replace(old, new)
    if not html.lstrip().startswith('<title>'): raise SystemExit('index.html: the page must open with its <title> once the shell is gone')
    return html


XITE_COMPONENTS = ['EventUtilitiesComponent.min.js', 'Geometry2DComponent.min.js', 'Geometry3DComponent.min.js', 'KeyDeviceSensorComponent.min.js',
                   'ScriptingComponent.min.js', 'TextComponent.min.js', 'X_ITEComponent.min.js']   # v2: what the Immersive profile and the page load (gates: no failed request)


def gates(files):
    problems, hosts, living, people, cards = [], {}, [], 0, {}
    for pub, src in files.items():
        if os.path.splitext(pub)[1] not in ('.html', '.x3d', '.json', '.md', '.txt'): continue
        text = open(src, encoding='utf-8').read()
        for m in SECRET.finditer(text): problems.append('%s: secret-shaped string %r' % (pub, m.group(0)[:12] + '...'))
        for u in re.findall(r'https?://[^\s"\'<>)]+', text): hosts[re.sub(r'^https?://([^/]+).*$', r'\1', u)] = hosts.get(re.sub(r'^https?://([^/]+).*$', r'\1', u), 0) + 1
        if pub.endswith('.cards.json') or pub.endswith('.hyper.json') or pub == 'portraits.json':
            ppl = json.loads(text)['people']
            if pub.endswith('.cards.json'): cards[pub[:-len('.cards.json')]] = set(ppl)
            for pid, p in ppl.items():
                people += pub.endswith('.cards.json')
                if isinstance(p.get('born'), int) and p['born'] >= ASOF - LIVING_YEARS and p.get('died') is None: living.append('%s %s (%s)' % (pub, p.get('name'), p['born']))
    for pub, src in files.items():   # the hypersphere draws no one the cards do not hold (the cards passed the possibly-living gate above)
        if pub.endswith('.hyper.json'):
            fam = os.path.basename(pub)[:-len('.hyper.json')]; extra = set(json.load(open(src, encoding='utf-8'))['people']) - cards.get(fam, set())
            if extra: problems.append('%s: %d people not in %s.cards.json: %s' % (pub, len(extra), fam, sorted(extra)[:5]))
    if 'portraits.json' in files:   # v2: every portrait is of someone in the cards, and a face only for status ok
        allp = set().union(*cards.values()) if cards else set()
        for pid, e in json.load(open(files['portraits.json'], encoding='utf-8'))['people'].items():
            if pid not in allp: problems.append('portraits.json: %s is not in any card file' % pid)
            if e['kind'] == 'ai-portrait' and e['status'] != 'ok': problems.append('portraits.json: %s shows a face with status %s' % (pid, e['status']))
            if not (e.get('label') or '').strip(): problems.append('portraits.json: %s has no label' % pid)
            for pub, h in e['sha256'].items():
                if pub not in files or sha(open(files[pub], 'rb').read()) != h: problems.append('portraits.json: %s missing or changed' % pub)
    problems += ['possibly living: ' + x for x in living]
    return problems, dict(sorted(hosts.items(), key=lambda kv: -kv[1])), people


def main():
    a = sys.argv[1:]
    out = os.path.abspath(a[a.index('--out') + 1]) if '--out' in a else os.path.join(HERE, 'out')
    art = os.path.abspath(a[a.index('--artifact') + 1]) if '--artifact' in a else os.path.join(HERE, 'artifact')
    hyp = os.path.abspath(a[a.index('--hyper') + 1]) if '--hyper' in a else os.path.join(PROTO, 'hyper', 'out')
    alt = os.path.abspath(a[a.index('--hyper-alt') + 1]) if '--hyper-alt' in a else None
    por = os.path.abspath(a[a.index('--portraits') + 1]) if '--portraits' in a else None
    man = json.load(open(os.path.join(out, 'loom-manifest.json'), encoding='utf-8'))
    files = {'loom-manifest.json': os.path.join(out, 'loom-manifest.json')}
    for f in man['families']:
        files[f['scene']] = os.path.join(out, f['scene']); files[f['cards']] = os.path.join(out, f['cards'])
    for fn in sorted(os.listdir(os.path.join(out, 'fonts'))): files['fonts/' + fn] = os.path.join(out, 'fonts', fn)
    hman = json.load(open(os.path.join(hyp, 'hyper-manifest.json'), encoding='utf-8'))   # the hypersphere view
    files['hyper-manifest.json'] = os.path.join(hyp, 'hyper-manifest.json')
    for fn in ('orbit.js', 'lens.js'): files['lib/' + fn] = os.path.join(hyp, 'lib', fn)   # nav: the orbit camera and the lens mirror (build_hypersphere.py writes them)
    for f in hman['families']:
        for k in ('host', 'pocket', 'data'): files[f[k]] = os.path.join(hyp, f[k])
        if f['cards'] not in files: raise SystemExit('the hypersphere reads %s, which the loom does not ship' % f['cards'])
        if sha(open(os.path.join(hyp, f['cards']), 'rb').read()) != sha(open(files[f['cards']], 'rb').read()):
            raise SystemExit('%s differs between hyper/out and scene2/out: both views read the one file' % f['cards'])
    looks = [hman.get('theme')]
    if alt:   # v2: the alternate theme's scenes and data under theme/<slug>/ (the cards are the shared ones)
        aman = json.load(open(os.path.join(alt, 'hyper-manifest.json'), encoding='utf-8')); d = 'theme/%s/' % aman['theme']; looks.append(aman['theme'])
        if [f['key'] for f in aman['families']] != [f['key'] for f in hman['families']]: raise SystemExit('the alternate theme has other families')
        for f in aman['families']:
            for k in ('host', 'pocket', 'data'): files[d + f[k]] = os.path.join(alt, f[k])
            if sha(open(os.path.join(alt, f['cards']), 'rb').read()) != sha(open(files[f['cards']], 'rb').read()): raise SystemExit('%s differs in the alternate build' % f['cards'])
    pdoc = None
    if por:   # v2: portraits.json and only the files it names
        pdoc = json.load(open(os.path.join(por, 'portraits.json'), encoding='utf-8')); files['portraits.json'] = os.path.join(por, 'portraits.json')
        for e in pdoc['people'].values():
            for pub in e['sha256']: files[pub] = os.path.join(por, pub)
    for fn in ('poster-wide-plate.webp', 'poster-tall-plate.webp'): files[fn] = os.path.join(hyp, fn)   # the page's loading still (Blender plate)
    for fn in sorted(os.listdir(os.path.join(XITE, 'assets', 'fonts', 'PT_Sans'))):                 # X_ITE's own UI font: the Artifact CSP refuses it (font-src),
        files['x_ite/assets/fonts/PT_Sans/' + fn] = os.path.join(XITE, 'assets', 'fonts', 'PT_Sans', fn)   # harmless; anywhere else (an Inline host, a plain server) it loads instead of a 404
    for fn in sorted(os.listdir(os.path.join(XITE, 'assets', 'lib'))):                              # PhysicalMaterial lookup tables (hypersphere); lut_sheen_E.png
        if re.match(r'lut_(ggx|charlie)\.png$', fn): files['x_ite/assets/lib/' + fn] = os.path.join(XITE, 'assets', 'lib', fn)   # only serves SheenMaterialExtension, which no scene uses
    files['x_ite/x_ite.min.js'] = os.path.join(XITE, 'x_ite.min.js'); files['x_ite/LICENSE.md'] = os.path.join(XITE, 'LICENSE.md')
    files['x_ite/assets/linetype/linetypes.png'] = os.path.join(XITE, 'assets', 'linetype', 'linetypes.png')
    files['x_ite/x_ite.css'] = os.path.join(XITE, 'x_ite.css')                                   # X_ITE links it beside its script (with SRI)
    for fn in sorted(os.listdir(os.path.join(XITE, 'assets', 'images'))):                          # x_ite.css points at these (logo, menu icons)
        files['x_ite/assets/images/' + fn] = os.path.join(XITE, 'assets', 'images', fn)
    files['x_ite/assets/lib/mikktspace_bg.wasm'] = os.path.join(XITE, 'assets', 'lib', 'mikktspace_bg.wasm')   # X_ITE fetches it at start
    for fn in XITE_COMPONENTS: files['x_ite/assets/components/' + fn] = os.path.join(XITE, 'assets', 'components', fn)
    for pub, src in files.items():
        if not os.path.isfile(src): raise SystemExit('missing input %s (%s)' % (pub, src))
    page = strip_shell(open(os.path.join(out, 'index.html'), encoding='utf-8').read())
    problems, hosts, people = gates(dict(files, **{'index.html': os.path.join(out, 'index.html')}))
    if problems: raise SystemExit('artifact gates failed:\n  ' + '\n  '.join(problems[:40]))
    if os.path.isdir(art): shutil.rmtree(art)
    os.makedirs(art)
    open(os.path.join(art, 'index.html'), 'w', encoding='utf-8').write(page)
    publish, rec = {}, dict(stage='make_artifact.py', source=os.path.relpath(out, PROTO), hyper_source=os.path.relpath(hyp, PROTO), hyper_built_by=hman.get('built_by'),
                             views=['hypersphere (default)', 'loom'], looks=looks, hyper_alt_source=alt and os.path.relpath(alt, PROTO), xite_components=XITE_COMPONENTS,
                             portraits=pdoc and dict(manifest=pdoc['manifest'], counts=pdoc['counts'], people={k: dict(kind=v['kind'], status=v['status'], label=v['label']) for k, v in pdoc['people'].items()}),
                             script=sha(open(os.path.abspath(__file__), 'rb').read()),
                             page=dict(file='index.html', sha256=sha(page.encode('utf-8')), from_sha256=sha(open(os.path.join(out, 'index.html'), 'rb').read())),
                             gates=dict(secrets='none', possibly_living='none', people_in_cards=people, link_hosts=hosts), files={})
    for pub, src in sorted(files.items()):
        dst = os.path.join(art, pub); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
        b = open(dst, 'rb').read(); ct = TYPES.get(os.path.splitext(pub)[1], 'application/octet-stream')
        publish[pub] = dict(**{'from': dst}, contentType=ct); rec['files'][pub] = dict(bytes=len(b), sha256=sha(b), type=ct)
    rec['total_bytes'] = sum(v['bytes'] for v in rec['files'].values()) + len(page.encode('utf-8')); rec['count'] = len(files) + 1
    json.dump(publish, open(os.path.join(art, 'publish.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(rec, open(os.path.join(art, 'receipt.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    big = max(rec['files'].items(), key=lambda kv: kv[1]['bytes'])
    if rec['total_bytes'] > 64 * 2 ** 20 or big[1]['bytes'] > 15 * 2 ** 20 or rec['count'] > 255: raise SystemExit('over the Artifact limits (64 MB, 15 MB a file, 255 files)')
    print('wrote %s: %d files, %d bytes (largest %s, %d bytes); %d people in cards, none possibly living; link hosts %s' % (art, rec['count'], rec['total_bytes'], big[0], big[1]['bytes'], people, hosts))


if __name__ == '__main__':
    main()
