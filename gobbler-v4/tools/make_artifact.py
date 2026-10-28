"""python3 -I tools/make_artifact.py OUT_DIR RUNTIME_FILES.json

A copy of the page for a host that adds its own document skeleton: the body of index.html (no doctype, html, head or body tags, a plain title),
plus exactly the files the page asked the server for in e2e/requests.js, plus the X_ITE licence. Nothing else is copied.
The scene is published as .xml (the host does not serve .x3d).
Prints the published paths and the total size."""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TITLE = 'Gobbler 4 Live Hover'
EXTRA = ['vendor/x_ite/LICENSE.md']
# the artifact host serves .xml but not .x3d: the scene is published under a .xml name and the page's one reference follows it
RENAME = {'data/deep/gobbler3.x3d': 'data/deep/gobbler3.xml'}


def page():
    s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    s = re.sub(r'<!doctype html><html[^>]*><head>', '', s, count=1, flags=re.I)
    s = re.sub(r'<meta charset="utf-8">|<meta name="viewport"[^>]*>', '', s)
    s = re.sub(r'<title>.*?</title>', '', s, count=1, flags=re.S)
    s = s.replace('</head>\n<body>', '').replace('</body></html>', '')
    assert not re.search(r'<head[\s>]|<body[\s>]|</html|</head>|</body>', s), 'skeleton tags left in the page'
    for a, b in RENAME.items():
        assert s.count("'" + a + "'") == 1, 'expected exactly one reference to ' + a
        s = s.replace("'" + a + "'", "'" + b + "'")
    return '<title>' + TITLE + '</title>\n' + s.strip() + '\n'


def main(out, runtime):
    files = json.load(open(runtime))
    files = [f for f in files if f != 'index.html' and f != 'favicon.ico'] + EXTRA
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page())
    total = os.path.getsize(os.path.join(out, 'index.html'))
    for f in files:
        src = os.path.join(ROOT, f)
        if not os.path.isfile(src):
            sys.exit('missing runtime file: ' + f)
        dst = os.path.join(out, RENAME.get(f, f))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        total += os.path.getsize(dst)
    files = [RENAME.get(f, f) for f in files]
    print(json.dumps({'files': ['index.html'] + files, 'count': len(files) + 1, 'bytes': total}, indent=1))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
