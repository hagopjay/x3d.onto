"""python3 -I gobbler-worlds/tools/make_artifact.py OUT_DIR RUNTIME_FILES.json

A flat copy of the worlds page for a host that adds its own document skeleton and cannot serve ../ paths or .gz (the gobbler-demiurge make_artifact.py recipe):
the body of index.html, every file the page asked the server for (test/requests.js) with the gobbler-v4 and gobbler-demiurge files moved up to the same
relative paths, the bird and the graph as base64 text of their gzip (the page inflates them itself), the AAC beds as .mp4, plus the X_ITE licence.
The world files keep their paths (data/worlds/...). Prints the published paths and the total size."""
import base64, json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TITLE = 'Gobbler Worlds Within'
B64 = {'data/bird/gobbler4-worlds.x3d.gz': 'data/bird/bird.b64.txt', 'data/bird/graph-v3.json.gz': 'data/bird/graph.b64.txt'}
CFG = "window.GD_CFG={bird:'data/bird/bird.b64.txt',enc:'b64gz',graph:'data/bird/graph.b64.txt',graphEnc:'b64gz',onto:'data/onto-hover.json',audio:'assets/audio/',audioExt:'mp4'};"
UP = ('../gobbler-v4/', '../gobbler-demiurge/')

def dst_of(rel):
    for u in UP:
        if rel.startswith(u): return rel[len(u):]
    return rel

def page():
    s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    s = re.sub(r'<!doctype html><html[^>]*><head>', '', s, count=1, flags=re.I)
    s = re.sub(r'<meta charset="utf-8">|<meta name="viewport"[^>]*>', '', s)
    s = re.sub(r'<title>.*?</title>', '', s, count=1, flags=re.S)
    s = s.replace('</head>\n<body>', '').replace('</body></html>', '')
    for u in UP: s = s.replace(u, '')
    assert not re.search(r'<head[\s>]|<body[\s>]|</html|</head>|</body>', s), 'skeleton tags left in the page'
    assert '../' not in s
    return '<title>' + TITLE + '</title>\n<script>' + CFG + '</script>\n' + s.strip() + '\n'

def main(out, runtime):
    files = [f for f in json.load(open(runtime)) if f not in ('index.html', 'favicon.ico') and not f.startswith('?')] + ['../gobbler-v4/vendor/x_ite/LICENSE.md']
    if os.path.isdir(out): shutil.rmtree(out)
    os.makedirs(out)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page()); total = os.path.getsize(os.path.join(out, 'index.html')); pub = ['index.html']
    for f in sorted(set(files)):
        src = os.path.normpath(os.path.join(ROOT, f))
        if not os.path.isfile(src): sys.exit('missing runtime file: ' + f)
        d = B64.get(f, dst_of(f)); d = d[:-4] + '.mp4' if d.endswith('.m4a') else d; dst = os.path.join(out, d); os.makedirs(os.path.dirname(dst), exist_ok=True)
        if f in B64: open(dst, 'w').write(base64.b64encode(open(src, 'rb').read()).decode())
        else: shutil.copyfile(src, dst)
        total += os.path.getsize(dst); pub.append(d)
    print(json.dumps({'files': pub, 'count': len(pub), 'bytes': total}, indent=1))

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
