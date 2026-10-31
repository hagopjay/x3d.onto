#!/usr/bin/env python3
"""JSON-LD gate, run with a Python that has PyLD (kept out of ingest.py so the generator needs only the standard library
and jsonschema):  <venv>/bin/python -I check_jsonld.py out/private/genealogy.graph.jsonld [...] > out/jsonld-check.json
Expands each file as JSON-LD 1.1 and converts it to N-Quads; counts triples and flags IRIs with spaces or no scheme."""
import hashlib, json, re, sys
from importlib.metadata import version
from pyld import jsonld

res = {'tool': 'PyLD %s' % version('PyLD'), 'files': []}
for f in sys.argv[1:]:
    b = open(f, 'rb').read()
    doc = json.loads(b)
    r = {'file': f, 'sha256': hashlib.sha256(b).hexdigest()}
    try:
        exp = jsonld.expand(doc)
        nq = jsonld.to_rdf(doc, {'format': 'application/n-quads'})
        lines = [x for x in nq.split('\n') if x.strip()]
        iris = set(re.findall(r'<([^>]*)>', nq))
        r.update(ok=True, expanded_nodes=len(exp), triples=len(lines), subjects=len({x.split(' ', 1)[0] for x in lines}),
                 bad_iris=sorted(i for i in iris if ' ' in i or not re.match(r'^[a-z][a-z0-9+.-]*:', i))[:20],
                 graph_items=len(doc.get('@graph', [])), json_literals=nq.count('rdf-syntax-ns#JSON>'))
        r['ok'] = not r['bad_iris']
    except Exception as e:
        r.update(ok=False, error=repr(e)[:500])
    res['files'].append(r)
res['ok'] = all(x['ok'] for x in res['files'])
print(json.dumps(res, indent=1))
sys.exit(0 if res['ok'] else 1)
