"""Fork x3d_mcp validator (branch integration/validator-fixes) on one or more X3D files.
Run with the venv that has the fork installed:
  /tmp/claude-0/-home-claude/dae07dfe-133a-572d-8ebf-054b136e7172/scratchpad/fvenv/bin/python tools/validate.py FILE.x3d [...]
Prints one JSON object per file: xsd_valid, xsd_errors, semantic (report text), profile_ok, profile."""
import sys, os, json
sys.path.insert(0, '/home/user/x3d_mcp/src')
from validation.validate import validate_xml
from validation.semantic import validate_semantic
from validation.profile import check_profile
from lxml import etree
for f in sys.argv[1:]:
    xml = open(f, encoding='utf-8').read()
    r = {'file': os.path.basename(f)}
    v = validate_xml(xml)
    r['xsd_valid'] = bool(v.get('valid')); r['xsd_errors'] = [str(e) for e in (v.get('errors') or [])][:10]
    s = validate_semantic(xml); r['semantic'] = s
    p = check_profile(etree.fromstring(xml.encode()))
    r['profile_ok'] = getattr(p, 'ok', getattr(p, 'valid', None)); r['profile'] = str(p)
    print(json.dumps(r, indent=1))
