"""Run the user's x3d_mcp fork validator (XSD + semantic + profile) on X3D files.
Usage: X3D_MCP=<fork checkout> <python with lxml> -I validate_x3d.py FILE.x3d [...]  -> one JSON object per file."""
import sys, os, json
sys.path.insert(0, os.path.join(os.environ.get('X3D_MCP', '/home/user/hagopjay/x3d_mcp'), 'src'))
from validation.validate import validate_xml
from validation.semantic import validate_semantic
from validation.profile import check_profile
from lxml import etree
for f in sys.argv[1:]:
    xml = open(f, encoding='utf-8').read()
    r = {'file': os.path.basename(f)}
    v = validate_xml(xml)
    r['xsd_valid'] = bool(v.get('valid')); r['xsd_errors'] = [str(e) for e in (v.get('errors') or [])][:10]
    r['semantic'] = validate_semantic(xml)
    p = check_profile(etree.fromstring(xml.encode()))
    r['profile_ok'] = getattr(p, 'ok', getattr(p, 'valid', None)); r['profile'] = str(p)
    print(json.dumps(r, indent=1, default=str))
